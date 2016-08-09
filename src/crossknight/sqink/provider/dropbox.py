#coding:utf-8
from base64 import b64encode
from crossknight.sqink.domain import isUuid
from crossknight.sqink.domain import NoteStatus
from crossknight.sqink.markdown import renderHtml
from crossknight.sqink.plist import marshalNote
from crossknight.sqink.plist import unmarshalNote
from crossknight.sqink.provider import AConnectionError
from crossknight.sqink.provider import InvalidProxyError
from crossknight.sqink.provider import RemoteNoteProvider
from crossknight.sqink.provider import TokenExpiredError
from datetime import datetime
from datetime import timezone
from dropbox.client import DropboxClient
from dropbox.oauth import DropboxOAuth2FlowNoRedirect
from dropbox.rest import ErrorResponse
from dropbox.rest import RESTClientObject
from dropbox.rest import TRUSTED_CERT_FILE
from ssl import CERT_REQUIRED
from ssl import PROTOCOL_TLSv1
from urllib3 import ProxyManager
from urllib3.exceptions import MaxRetryError
from urllib3.exceptions import ProtocolError
from urllib3.exceptions import ProxyError


_APP_KEY= "tngl6ocsui0btpf"
_APP_SECRET= "fr369k833umjgie"


def _restClient(proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
    return ProxyRESTClient(proxyHost, proxyPort, proxyUser, proxyPassword) if proxyHost else None


def getLastModified(metadata):
    lastModified= datetime.strptime(metadata["modified"], "%a, %d %b %Y %H:%M:%S %z")
    if lastModified.tzinfo is not None:
        if lastModified.tzinfo != timezone.utc:
            lastModified= lastModified.astimezone(timezone.utc)
        lastModified= lastModified.replace(tzinfo=None)
    return lastModified


def online(f):
    """Raises InvalidProxyError when a HTTP proxy is required, or AConnectionError when connection fails."""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except MaxRetryError as e:
            if isinstance(e.reason, ProtocolError):
                raise AConnectionError
            if isinstance(e.reason, ProxyError):
                raise InvalidProxyError
            raise e
    return wrapper


def expires(f):
    """Raises TokenExpiredError when authorization token is expired or revoked."""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ErrorResponse as e:
            if e.status == 401:
                raise TokenExpiredError
            raise e
    return wrapper


class SyncFolder:

    DayOne= "/apps/Day One/journal.dayone"
    Narrate= "/apps/Narrate"


class ProxyRESTClient(RESTClientObject):

    def __init__(self, proxyHost, proxyPort=None, proxyUser=None, proxyPassword=None):
        if not proxyPort:
            proxyPort= 80
        proxy= "http://%s:%d" % (proxyHost, proxyPort)

        proxyHeaders= {}
        if proxyUser:
            proxyAuth= proxyUser + ":" + proxyPassword
            proxyAuth= b64encode(proxyAuth.encode("ascii")).decode("ascii")
            proxyHeaders["Proxy-Authorization"]= "Basic " + proxyAuth

        self.mock_urlopen= None
        self.pool_manager= ProxyManager(proxy, proxy_headers=proxyHeaders, num_pools=4, maxsize=8, block=False,
                timeout=60.0, cert_reqs=CERT_REQUIRED, ca_certs=TRUSTED_CERT_FILE, ssl_version=PROTOCOL_TLSv1)


class DropboxAuthorizator:

    def __init__(self, proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
        self.__restClient= _restClient(proxyHost, proxyPort, proxyUser, proxyPassword)
        self.__oauth= DropboxOAuth2FlowNoRedirect(_APP_KEY, _APP_SECRET, rest_client=self.__restClient)

    def authorizationUrl(self):
        return self.__oauth.start()

    @online
    def authorize(self, code):
        accessToken, userId= self.__oauth.finish(code.strip())
        return accessToken

    def checkFolder(self, accessToken, folder):
        try:
            client= DropboxClient(accessToken, rest_client=self.__restClient)
            self.__createFolder(client, folder + "/entries/deleted")
            self.__createFolder(client, folder + "/photos/deleted")
        except:
            return False
        return True

    def __createFolder(self, client, path):
        try:
            client.file_create_folder(path)
        except ErrorResponse as e:
            if e.status == 403: #Folder already exists
                pass
            else:
                raise e


class DropboxNoteProvider(RemoteNoteProvider):

    __DAY_ONE_EXTENSION= ".doentry"

    def __init__(self, accessToken, folder, proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
        self.__token= accessToken
        self.__notesPath= folder + "/entries"
        self.__removedNotesPath= self.__notesPath + "/deleted"
        self.__photosPath= folder + "/photos"
        self.__removedPhotosPath= self.__photosPath + "/deleted"
        self.__client= DropboxClient(self.__token, rest_client=_restClient(proxyHost, proxyPort, proxyUser, proxyPassword))
        self.__notesCache= {}
        self.__dayOneFlavor= folder == SyncFolder.DayOne

    def requiresReverseUpdate(self):
        return True

    @online
    @expires
    def sync(self):
        notes= self.__list(self.__notesPath, False)
        removedNotes= self.__list(self.__removedNotesPath, True)
        #Clean inconsistent files
        for uuid in list(notes.keys()):
            if uuid in removedNotes:
                if removedNotes[uuid].lastModified >= notes[uuid].lastModified:
                    self.__client.file_delete(self.__notePath(uuid))
                    if notes[uuid].hasPhoto:
                        self.__client.file_delete(self.__photoPath(uuid))
                    del notes[uuid]
                else:
                    self.__client.file_delete(self.__removedNotePath(uuid))
                    del removedNotes[uuid]
        notes.update(removedNotes)
        self.__notesCache= notes
        return notes

    @online
    @expires
    def get(self, uuid):
        response, metadata= self.__client.get_file_and_metadata(self.__notePath(uuid))
        with response:
            note= unmarshalNote(response.read(), getLastModified(metadata))
        if uuid not in self.__notesCache or self.__notesCache[uuid].hasPhoto:
            try:
                with self.__client.get_file(self.__photoPath(uuid)) as response:
                    note.photo= response.read()
            except ErrorResponse as e:
                if e.status == 404: #Photo does not exist
                    pass
                else:
                    raise e
        return renderHtml(note)

    @online
    @expires
    def add(self, note):
        """
        The note lastModified time is updated from Dropbox when the operations succeeds (unfortunately there's no way to
        set the modified time in Dropbox).
        """
        uuid= note.uuid
        result= self.__client.put_file(self.__notePath(uuid), marshalNote(note))
        if len(result["path"]) != len(self.__notePath(uuid)):
            try:
                self.__client.file_delete(result["path"])
            except ErrorResponse:
                pass
            raise RuntimeError("Note[uuid=%s] already exists" % uuid)
        note.lastModified= getLastModified(result)

        if note.photo:
            self.__client.put_file(self.__photoPath(uuid), note.photo, overwrite=True)
        elif uuid in self.__notesCache and self.__notesCache[uuid].hasPhoto:
            try:
                self.__client.file_delete(self.__photoPath(uuid))
            except ErrorResponse:
                pass
        renderHtml(note)

        #Clean removed note if exists
        if uuid in self.__notesCache and self.__notesCache[uuid].removed:
            try:
                self.__client.file_delete(self.__removedNotePath(uuid))
            except ErrorResponse:
                pass

    @online
    @expires
    def update(self, note):
        """
        The note lastModified time is updated from Dropbox when the operations succeeds (unfortunately there's no way to
        set the modified time in Dropbox).
        """
        uuid= note.uuid
        #Check if note exists
        if self.__notesCache and (uuid not in self.__notesCache or self.__notesCache[uuid].removed):
            raise RuntimeError("Note[uuid=%s] does not exist" % uuid)

        result= self.__client.put_file(self.__notePath(uuid), marshalNote(note), overwrite=True)
        note.lastModified= getLastModified(result)

        if note.photo:
            self.__client.put_file(self.__photoPath(uuid), note.photo, overwrite=True)
        elif uuid not in self.__notesCache or self.__notesCache[uuid].hasPhoto:
            try:
                self.__client.file_delete(self.__photoPath(uuid))
            except ErrorResponse:
                pass
        renderHtml(note)

    @online
    @expires
    def remove(self, note):
        """
        The note lastModified time is updated from Dropbox when the operations succeeds (unfortunately there's no way to
        set the modified time in Dropbox).
        """
        uuid= note.uuid

        #Remove note if exists
        if uuid in self.__notesCache and not self.__notesCache[uuid].removed:
            try:
                self.__client.file_delete(self.__notePath(uuid))
            except ErrorResponse:
                pass

        #Remove photo if exists
        if uuid in self.__notesCache and self.__notesCache[uuid].hasPhoto:
            try:
                self.__client.file_delete(self.__photoPath(uuid))
            except ErrorResponse:
                pass

        result= self.__client.put_file(self.__removedNotePath(uuid), b"", overwrite=True)
        note.lastModified= getLastModified(result)

    def __list(self, path, removed):
        folder= self.__client.metadata(path)
        if not folder["is_dir"]:
            raise RuntimeError("Path is not a folder")

        notes= {}
        pos= len(path) + 1
        for file in folder["contents"]:
            if not file["is_dir"]:
                name= self.__fileUuid(file["path"][pos:])
                if isUuid(name):
                    notes[name]= NoteStatus(name, getLastModified(file), removed)

        if not removed:
            folder= self.__client.metadata(self.__photosPath)
            if not folder["is_dir"]:
                raise RuntimeError("Path is not a folder")

            pos= len(self.__photosPath) + 1
            for file in folder["contents"]:
                name= file["path"][pos:]
                if not file["is_dir"] and name.endswith(".jpg"):
                    name= name[:-4]
                    if name in notes:
                        notes[name].hasPhoto= True

        return notes

    def __fileUuid(self, filename):
        if self.__dayOneFlavor and filename.endswith(self.__DAY_ONE_EXTENSION):
            return filename[:-(len(self.__DAY_ONE_EXTENSION))]
        return filename

    def __buildNotePath(self, parentPath, uuid):
        path= parentPath + "/" + uuid
        if self.__dayOneFlavor:
            path+= self.__DAY_ONE_EXTENSION
        return path

    def __notePath(self, uuid):
        return self.__buildNotePath(self.__notesPath, uuid)

    def __removedNotePath(self, uuid):
        return self.__buildNotePath(self.__removedNotesPath, uuid)

    def __photoPath(self, uuid):
        return self.__photosPath + "/" + uuid + ".jpg"
