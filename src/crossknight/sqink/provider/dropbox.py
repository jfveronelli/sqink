# coding:utf-8
from crossknight.sqink import createLogger
from crossknight.sqink.domain import isUuid
from crossknight.sqink.domain import NoteStatus
from crossknight.sqink.markdown import renderHtml
from crossknight.sqink.plist import marshalNote
from crossknight.sqink.plist import unmarshalNote
from crossknight.sqink.provider import AConnectionError
from crossknight.sqink.provider import InvalidProxyError
from crossknight.sqink.provider import RemoteNoteProvider
from crossknight.sqink.provider import TokenExpiredError
from dropbox import create_session
from dropbox import Dropbox
from dropbox.exceptions import ApiError
from dropbox.exceptions import InternalServerError
from dropbox.files import FileMetadata
from dropbox.files import WriteMode
from dropbox.oauth import DropboxOAuth2FlowNoRedirect
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError
from requests.exceptions import ProxyError


_LOG = createLogger("dbox")


def _proxies(proxyHost, proxyPort, proxyUser, proxyPassword):
    proxies = {}
    if proxyHost:
        proxy = proxyHost + ":" + str(proxyPort or 80)
        if proxyUser:
            proxy = proxyUser + ":" + (proxyPassword or "") + "@" + proxy
        proxies["http"] = proxy
        proxies["https"] = proxy
    return proxies


def online(f):
    """Raises InvalidProxyError when a HTTP proxy is required, or AConnectionError when connection fails."""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ProxyError:
            raise InvalidProxyError
        except ConnectionError:
            raise AConnectionError
    return wrapper


def expires(f):
    """Raises TokenExpiredError when authorization token is expired or revoked."""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except InternalServerError:
            raise TokenExpiredError
    return wrapper


class SyncFolder:

    DayOne = "/apps/Day One/journal.dayone"
    Narrate = "/apps/Narrate"


class DropboxAuthorizator:
    __APP_KEY = "tngl6ocsui0btpf"
    __APP_SECRET = "fr369k833umjgie"

    def __init__(self, proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
        self.__proxies = _proxies(proxyHost, proxyPort, proxyUser, proxyPassword)
        self.__oauth = DropboxOAuth2FlowNoRedirect(self.__APP_KEY, self.__APP_SECRET)
        self.__oauth.requests_session.proxies = self.__proxies

    def authorizationUrl(self):
        return self.__oauth.start()

    @online
    def authorize(self, code):
        try:
            return self.__oauth.finish(code.strip()).access_token
        except HTTPError:
            raise TokenExpiredError

    def checkFolder(self, accessToken, folder):
        try:
            client = Dropbox(accessToken, session=create_session(proxies=self.__proxies))
            self.__createFolder(client, folder + "/entries/deleted")
            self.__createFolder(client, folder + "/photos/deleted")
        except ApiError:
            return False
        return True

    @staticmethod
    def __createFolder(client, path):
        _LOG.info("Creating folder: %s", path)
        try:
            client.files_create_folder(path)
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_conflict() and e.error.get_path().get_conflict().is_folder():
                _LOG.info("Folder %s already exists", path)
            else:
                raise e


class FileEntry:

    def __init__(self, folder, name, lastModified):
        self.folder = folder
        self.name = name
        self.lastModified = lastModified

    @staticmethod
    def fromMetadata(metadata):
        if isinstance(metadata, FileMetadata):
            tokens = metadata.path_display.rsplit("/", 1)
            folder, name = (tokens[0] or "/", tokens[1]) if len(tokens) == 2 else ("/", tokens[0])
            return FileEntry(folder, name, metadata.client_modified)
        return None


class DropboxNoteProvider(RemoteNoteProvider):

    __DAY_ONE_EXTENSION = ".doentry"

    def __init__(self, accessToken, folder, proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
        proxies = _proxies(proxyHost, proxyPort, proxyUser, proxyPassword)
        self.__token = accessToken
        self.__basePath = folder
        self.__notesPath = folder + "/entries"
        self.__removedNotesPath = self.__notesPath + "/deleted"
        self.__photosPath = folder + "/photos"
        self.__client = Dropbox(self.__token, session=create_session(proxies=proxies))
        self.__notesCache = {}
        self.__dayOneFlavor = folder == SyncFolder.DayOne

    @online
    @expires
    def sync(self):
        _LOG.info("Listing all notes and photos")
        folder = self.__client.files_list_folder(self.__basePath, recursive=True)
        files = list(filter(lambda e: e is not None, map(FileEntry.fromMetadata, folder.entries)))
        while folder.has_more:
            folder = self.__client.files_list_folder_continue(folder.cursor)
            files.extend(filter(lambda e: e is not None, map(FileEntry.fromMetadata, folder.entries)))

        notes = {}
        for file in filter(lambda f: f.folder == self.__notesPath and isUuid(self.__normalizeNoteName(f.name)), files):
            uuid = self.__normalizeNoteName(file.name)
            notes[uuid] = NoteStatus(uuid, file.lastModified)

        for file in filter(lambda f: f.folder == self.__photosPath and f.name.endswith(".jpg"), files):
            uuid = file.name[:-4]
            if uuid in notes:
                notes[uuid].hasPhoto = True

        for file in filter(lambda f: f.folder == self.__removedNotesPath and isUuid(self.__normalizeNoteName(f.name)),
                           files):
            uuid = self.__normalizeNoteName(file.name)
            if uuid in notes:
                if file.lastModified >= notes[uuid].lastModified:
                    _LOG.warning("Sync integrity check deleting note: %s", uuid)
                    try:
                        self.__client.files_delete(self.__notePath(uuid))
                    except ApiError:
                        _LOG.warning("Note %s not found", uuid)
                    if notes[uuid].hasPhoto:
                        _LOG.warning("Sync integrity check deleting photo: %s", uuid)
                        try:
                            self.__client.files_delete(self.__photoPath(uuid))
                        except ApiError:
                            _LOG.warning("Photo %s not found", uuid)
                    del notes[uuid]
                else:
                    _LOG.warning("Sync integrity check deleting REMOVED note: %s", uuid)
                    try:
                        self.__client.files_delete(self.__removedNotePath(uuid))
                    except ApiError:
                        _LOG.warning("REMOVED note %s not found", uuid)
                    continue
            notes[uuid] = NoteStatus(uuid, file.lastModified, True)

        self.__notesCache = notes
        return notes

    @online
    @expires
    def get(self, uuid):
        _LOG.info("Getting note: %s", uuid)
        metadata, response = self.__client.files_download(self.__notePath(uuid))
        with response:
            note = unmarshalNote(response.content, metadata.client_modified)
        if uuid not in self.__notesCache or self.__notesCache[uuid].hasPhoto:
            _LOG.info("Getting photo: %s", uuid)
            try:
                with self.__client.files_download(self.__photoPath(uuid))[1] as response:
                    note.photo = response.content
            except ApiError as e:
                if e.error.is_path() and e.error.get_path().is_not_found():
                    _LOG.warning("Photo %s does not exist", uuid)
                else:
                    raise e
        return renderHtml(note)

    @online
    @expires
    def add(self, note):
        uuid = note.uuid
        _LOG.info("Adding note: %s", uuid)
        self.__uploadFile(self.__notePath(uuid), note.lastModified, marshalNote(note), overwrite=False)

        if note.photo:
            _LOG.info("Adding photo: %s", uuid)
            self.__uploadFile(self.__photoPath(uuid), note.lastModified, note.photo)
        elif uuid in self.__notesCache and self.__notesCache[uuid].hasPhoto:
            _LOG.info("Deleting photo: %s", uuid)
            try:
                self.__client.files_delete(self.__photoPath(uuid))
            except ApiError:
                _LOG.warning("Photo %s not found", uuid)

        # Clean removed note if exists
        if uuid in self.__notesCache and self.__notesCache[uuid].removed:
            _LOG.info("Deleting REMOVED note: %s", uuid)
            try:
                self.__client.files_delete(self.__removedNotePath(uuid))
            except ApiError:
                _LOG.warning("REMOVED note %s not found", uuid)

    @online
    @expires
    def update(self, note):
        uuid = note.uuid
        # Check if note exists
        if self.__notesCache and (uuid not in self.__notesCache or self.__notesCache[uuid].removed):
            raise RuntimeError("Note[uuid=%s] does not exist" % uuid)

        # Dropbox does not update the client_modifed date when the content hasn't changed. So the note is removed first.
        _LOG.info("Trying to delete old note before updating: %s", uuid)
        try:
            self.__client.files_delete(self.__notePath(uuid))
        except ApiError:
            pass

        _LOG.info("Updating note: %s", uuid)
        self.__uploadFile(self.__notePath(uuid), note.lastModified, marshalNote(note))

        if note.photo:
            _LOG.info("Updating photo: %s", uuid)
            self.__uploadFile(self.__photoPath(uuid), note.lastModified, note.photo)
        elif uuid not in self.__notesCache or self.__notesCache[uuid].hasPhoto:
            _LOG.info("Deleting photo: %s", uuid)
            try:
                self.__client.files_delete(self.__photoPath(uuid))
            except ApiError:
                _LOG.warning("Photo %s not found", uuid)

    @online
    @expires
    def remove(self, note):
        uuid = note.uuid

        # Remove note if exists
        if uuid in self.__notesCache and not self.__notesCache[uuid].removed:
            _LOG.info("Deleting note: %s", uuid)
            try:
                self.__client.files_delete(self.__notePath(uuid))
            except ApiError:
                _LOG.warning("Note %s not found", uuid)

        # Remove photo if exists
        if uuid in self.__notesCache and self.__notesCache[uuid].hasPhoto:
            _LOG.info("Deleting photo: %s", uuid)
            try:
                self.__client.files_delete(self.__photoPath(uuid))
            except ApiError:
                _LOG.warning("Photo %s not found", uuid)

        _LOG.info("Adding REMOVED note: %s", uuid)
        self.__uploadFile(self.__removedNotePath(uuid), note.lastModified, b"")

    def __uploadFile(self, path, lastModified, content, overwrite=True):
        mode = WriteMode.overwrite if overwrite else WriteMode.add
        self.__client.files_upload(content, path, mode=mode, client_modified=lastModified)

    def __normalizeNoteName(self, name):
        if self.__dayOneFlavor and name.endswith(self.__DAY_ONE_EXTENSION):
            name = name[:-(len(self.__DAY_ONE_EXTENSION))]
        return name

    def __buildNotePath(self, parentPath, uuid):
        path = parentPath + "/" + uuid
        if self.__dayOneFlavor:
            path += self.__DAY_ONE_EXTENSION
        return path

    def __notePath(self, uuid):
        return self.__buildNotePath(self.__notesPath, uuid)

    def __removedNotePath(self, uuid):
        return self.__buildNotePath(self.__removedNotesPath, uuid)

    def __photoPath(self, uuid):
        return self.__photosPath + "/" + uuid + ".jpg"
