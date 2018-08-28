# coding:utf-8
from base64 import b64encode
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
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from httplib2 import Http
from httplib2 import HttpLib2Error
from httplib2 import HTTPSConnectionWithTimeout
from httplib2 import ProxyInfo
from httplib2 import SCHEME_TO_CONNECTION
from io import BytesIO
from oauth2client import GOOGLE_TOKEN_URI
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import FlowExchangeError
from oauth2client.client import OAuth2Credentials
from oauth2client.client import OAuth2WebServerFlow


_LOG = createLogger("gdrive")


def online(f):
    """Raises InvalidProxyError when a HTTP proxy is required, or AConnectionError when connection fails."""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (ConnectionError, TimeoutError, HttpLib2Error):
            raise AConnectionError
        except OSError as e:
            if "407" in str(e):
                raise InvalidProxyError
            raise e
    return wrapper


def expires(f):
    """Raises TokenExpiredError when authorization token is expired or revoked."""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (AccessTokenRefreshError, FlowExchangeError):
            raise TokenExpiredError
    return wrapper


def createHttp(proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
    proxyInfo = None
    if proxyHost:
        proxyInfo = ProxyInfo(3, proxyHost, proxyPort if proxyPort else 80, proxy_user=proxyUser,
                              proxy_pass=proxyPassword)
    return Http(proxy_info=proxyInfo)


class HTTPSProxyConnectionWithTimeout(HTTPSConnectionWithTimeout):

    def __init__(self, host, port=None, key_file=None, cert_file=None, timeout=None, proxy_info=None, *args, **kwargs):
        if isinstance(proxy_info, ProxyInfo) and proxy_info.proxy_type == 3 and proxy_info.proxy_host\
                and proxy_info.proxy_port:
            headers = {}
            if proxy_info.proxy_user and proxy_info.proxy_pass:
                credentials = "%s:%s" % (proxy_info.proxy_user, proxy_info.proxy_pass)
                credentials = b64encode(credentials.encode("utf-8")).strip().decode("utf-8")
                headers["Proxy-Authorization"] = "Basic " + credentials
            HTTPSConnectionWithTimeout.__init__(self, proxy_info.proxy_host, port=proxy_info.proxy_port,
                                                key_file=key_file, cert_file=cert_file, timeout=timeout,
                                                proxy_info=proxy_info, *args, **kwargs)
            self.set_tunnel(host, port if port else 443, headers)
        else:
            HTTPSConnectionWithTimeout.__init__(self, host, port=port, key_file=key_file, cert_file=cert_file,
                                                timeout=timeout, proxy_info=proxy_info, *args, **kwargs)


# override in httplib2 to support proxies and proxy basic authentication
SCHEME_TO_CONNECTION["https"] = HTTPSProxyConnectionWithTimeout


class GoogleDriveAuthorizator:
    __APP_ID = "897700201444-0oju80gfjirsuogns9brqctnnf9tquq6.apps.googleusercontent.com"
    __APP_SECRET = "iT8VQkS7QyJKezs6uBJOLtR_"
    __SCOPE = "https://www.googleapis.com/auth/drive.appdata"
    __REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

    def __init__(self, proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
        self.__http = createHttp(proxyHost, proxyPort, proxyUser, proxyPassword)
        self.__oauth = OAuth2WebServerFlow(self.__APP_ID, self.__APP_SECRET, self.__SCOPE,
                                           redirect_uri=self.__REDIRECT_URI)

    def authorizationUrl(self):
        return self.__oauth.step1_get_authorize_url()

    @online
    @expires
    def authorize(self, code):
        credentials = self.__oauth.step2_exchange(code, http=self.__http)
        token = credentials.refresh_token
        _LOG.info("Acquired token: %s", token)
        return token

    @classmethod
    def tokenToCredentials(cls, refreshToken):
        return OAuth2Credentials(client_id=cls.__APP_ID, client_secret=cls.__APP_SECRET, token_uri=GOOGLE_TOKEN_URI,
                                 refresh_token=refreshToken, access_token=None, token_expiry=None, user_agent=None)


class GoogleDriveNoteProvider(RemoteNoteProvider):

    FOLDER = "appDataFolder"
    NOTE_MIMETYPE = "application/xml"
    NOTE_EXTENSION = ".entry"
    PHOTO_MIMETYPE = "image/jpeg"
    PHOTO_EXTENSION = ".jpg"
    REMOVED_NOTE_MIMETYPE = "application/octet-stream"
    REMOVED_NOTE_EXTENSION = ".deleted"

    def __init__(self, refreshToken, proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
        self.__noteStatusCache = {}
        self.__credentials = GoogleDriveAuthorizator.tokenToCredentials(refreshToken)
        self.__http = self.__credentials.authorize(createHttp(proxyHost, proxyPort, proxyUser, proxyPassword))
        self.__service = None

    @online
    @expires
    def sync(self):
        noteStatus = {}
        pageToken = None
        while True:
            _LOG.info("Listing all notes and photos")
            fields = "files(id,name,modifiedTime),nextPageToken"
            result = self._service().list(spaces=self.FOLDER, fields=fields, pageSize=1000, pageToken=pageToken)\
                .execute()
            pageToken = result.get("nextPageToken")

            for item in filter(lambda i: i["name"].endswith(self.NOTE_EXTENSION), result["files"]):
                name = item["name"][:-6]
                if isUuid(name):
                    ns = NoteStatus(name, self.__lastModified(item))
                    ns.noteId = item["id"]
                    noteStatus[name] = ns

            for item in filter(lambda i: i["name"].endswith(self.PHOTO_EXTENSION), result["files"]):
                name = item["name"][:-4]
                if name in noteStatus:
                    ns = noteStatus[name]
                    ns.hasPhoto = True
                    ns.photoId = item["id"]

            for item in filter(lambda i: i["name"].endswith(self.REMOVED_NOTE_EXTENSION), result["files"]):
                name = item["name"][:-8]
                if isUuid(name):
                    ns = NoteStatus(name, self.__lastModified(item), True)
                    ns.noteId = item["id"]
                    if name in noteStatus:
                        nso = noteStatus[name]
                        if ns.lastModified >= nso.lastModified:
                            _LOG.warning("Sync integrity check deleting note: %s", name)
                            self.__remove(nso.noteId)
                            if nso.hasPhoto:
                                _LOG.warning("Sync integrity check deleting photo: %s", name)
                                self.__remove(nso.photoId)
                        else:
                            _LOG.warning("Sync integrity check deleting REMOVED note: %s", name)
                            self.__remove(ns.noteId)
                            continue
                    noteStatus[name] = ns

            if not pageToken:
                break
        self.__noteStatusCache = noteStatus
        return noteStatus

    @online
    @expires
    def get(self, uuid):
        ns = self.__noteStatusCache.get(uuid)
        if not ns or ns.removed:
            raise RuntimeError("Note[uuid=%s] does not exist" % uuid)
        _LOG.info("Getting note: %s", uuid)
        content = self._service().get_media(fileId=ns.noteId).execute()
        note = unmarshalNote(content, ns.lastModified)
        if ns.hasPhoto:
            _LOG.info("Getting photo: %s", uuid)
            note.photo = self._service().get_media(fileId=ns.photoId).execute()
        return renderHtml(note)

    @online
    @expires
    def add(self, note):
        uuid = note.uuid
        if uuid in self.__noteStatusCache:
            ns = self.__noteStatusCache[uuid]
            if not ns.removed:
                raise RuntimeError("Note[uuid=%s] already exists" % uuid)
            else:
                _LOG.info("Deleting REMOVED note: %s", uuid)
                self.__remove(ns.noteId)

        metadata = {
            "name": uuid + self.NOTE_EXTENSION,
            "modifiedTime": self.__modifiedTime(note),
            "mimeType": self.NOTE_MIMETYPE,
            "parents": [self.FOLDER]
        }
        content = MediaIoBaseUpload(BytesIO(marshalNote(note)), mimetype=self.NOTE_MIMETYPE)
        _LOG.info("Adding note: %s", uuid)
        self._service().create(body=metadata, media_body=content, fields="id").execute()
        if note.photo:
            self.__uploadPhoto(note)

    @online
    @expires
    def update(self, note):
        uuid = note.uuid
        ns = self.__noteStatusCache.get(uuid)
        if not ns or ns.removed:
            raise RuntimeError("Note[uuid=%s] does not exist" % uuid)
        if ns.hasPhoto:
            _LOG.info("Deleting photo: %s", uuid)
            self.__remove(ns.photoId)

        _LOG.info("Updating note: %s", uuid)
        metadata = {"modifiedTime": self.__modifiedTime(note)}
        content = MediaIoBaseUpload(BytesIO(marshalNote(note)), mimetype=self.NOTE_MIMETYPE)
        self._service().update(fileId=ns.noteId, body=metadata, media_body=content, fields="id").execute()
        if note.photo:
            self.__uploadPhoto(note)

    @online
    @expires
    def remove(self, note):
        uuid = note.uuid
        if uuid in self.__noteStatusCache:
            ns = self.__noteStatusCache[uuid]
            _LOG.info("Deleting note: %s", uuid)
            self.__remove(ns.noteId)
            if ns.hasPhoto:
                _LOG.info("Deleting photo: %s", uuid)
                self.__remove(ns.photoId)

        metadata = {
            "name": uuid + self.REMOVED_NOTE_EXTENSION,
            "modifiedTime": self.__modifiedTime(note),
            "mimeType": self.REMOVED_NOTE_MIMETYPE,
            "parents": [self.FOLDER]
        }
        _LOG.info("Adding REMOVED note: %s", uuid)
        self._service().create(body=metadata, fields="id").execute()

    def _service(self):
        if self.__service is None:
            self.__service = build("drive", "v3", http=self.__http).files()
        return self.__service

    @staticmethod
    def __lastModified(metadata):
        return datetime.strptime(metadata["modifiedTime"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=0)

    @staticmethod
    def __modifiedTime(note):
        return note.lastModified.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def __uploadPhoto(self, note):
        _LOG.info("Adding photo: %s", note.uuid)
        metadata = {
            "name": note.uuid + self.PHOTO_EXTENSION,
            "mimeType": self.PHOTO_MIMETYPE,
            "modifiedTime": self.__modifiedTime(note),
            "parents": [self.FOLDER]
        }
        content = MediaIoBaseUpload(BytesIO(note.photo), mimetype=self.PHOTO_MIMETYPE)
        self._service().create(body=metadata, media_body=content, fields="id").execute()

    def __remove(self, fileId):
        self._service().delete(fileId=fileId).execute()
