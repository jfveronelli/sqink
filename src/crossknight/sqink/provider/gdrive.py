#coding:utf-8
from apiclient.discovery import build
from apiclient.http import MediaIoBaseUpload
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
from httplib2 import Http
from httplib2 import HttpLib2Error
from httplib2 import HTTPSConnectionWithTimeout
from httplib2 import ProxyInfo
from httplib2 import SCHEME_TO_CONNECTION
from io import BytesIO
from oauth2client import GOOGLE_TOKEN_URI
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2Credentials
from oauth2client.client import OAuth2WebServerFlow
import sys


_APP_ID= "897700201444-0oju80gfjirsuogns9brqctnnf9tquq6.apps.googleusercontent.com"
_APP_SECRET= "iT8VQkS7QyJKezs6uBJOLtR_"
_SCOPE= "https://www.googleapis.com/auth/drive.appfolder"
_REDIRECT_URI= "urn:ietf:wg:oauth:2.0:oob"
_CA_CERTS= None
if hasattr(sys, "frozen"):
    _CA_CERTS= sys.prefix + "/cacerts.txt" #hack for py2exe


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
        except AccessTokenRefreshError:
            raise TokenExpiredError
    return wrapper


def createHttp(proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
    proxyInfo= None
    if proxyHost:
        proxyInfo= ProxyInfo(3, proxyHost, proxyPort if proxyPort else 80, proxy_user=proxyUser, proxy_pass=proxyPassword)
    return Http(proxy_info=proxyInfo)


class HTTPSProxyConnectionWithTimeout(HTTPSConnectionWithTimeout):

    def __init__(self, host, port=None, key_file=None, cert_file=None, timeout=None, proxy_info=None, ca_certs=None, *args, **kwargs):
        if ca_certs is None:
            ca_certs= _CA_CERTS
        if isinstance(proxy_info, ProxyInfo) and proxy_info.proxy_type == 3 and proxy_info.proxy_host and proxy_info.proxy_port:
            headers = {}
            if proxy_info.proxy_user and proxy_info.proxy_pass:
                credentials= "%s:%s" % (proxy_info.proxy_user, proxy_info.proxy_pass)
                credentials= b64encode(credentials.encode("utf-8")).strip().decode("utf-8")
                headers["Proxy-Authorization"]= "Basic " + credentials
            HTTPSConnectionWithTimeout.__init__(self, proxy_info.proxy_host, port=proxy_info.proxy_port, key_file=key_file,
                    cert_file=cert_file, timeout=timeout, proxy_info=proxy_info, ca_certs=ca_certs, *args, **kwargs)
            self.set_tunnel(host, port if port else 443, headers)
        else:
            HTTPSConnectionWithTimeout.__init__(self, host, port=port, key_file=key_file, cert_file=cert_file, timeout=timeout,
                    proxy_info=proxy_info, ca_certs=ca_certs, *args, **kwargs)


SCHEME_TO_CONNECTION["https"]= HTTPSProxyConnectionWithTimeout #override in httplib2 to support proxies and proxy basic authentication


class GoogleDriveAuthorizator:

    def __init__(self, proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
        self.__http= createHttp(proxyHost, proxyPort, proxyUser, proxyPassword)
        self.__oauth= OAuth2WebServerFlow(_APP_ID, _APP_SECRET, _SCOPE, redirect_uri=_REDIRECT_URI)

    def authorizationUrl(self):
        return self.__oauth.step1_get_authorize_url()

    @online
    def authorize(self, code):
        credentials= self.__oauth.step2_exchange(code, http=self.__http)
        return credentials.refresh_token


class GoogleDriveNoteProvider(RemoteNoteProvider):

    FOLDER_ID= "appfolder"
    NOTE_MIMETYPE= "application/xml"
    NOTE_EXTENSION= ".entry"
    PHOTO_MIMETYPE= "image/jpeg"
    PHOTO_EXTENSION= ".jpg"
    REMOVED_NOTE_MIMETYPE= "application/octet-stream"
    REMOVED_NOTE_EXTENSION= ".deleted"

    def __init__(self, refreshToken, proxyHost=None, proxyPort=None, proxyUser=None, proxyPassword=None):
        self.__noteStatusCache= {}
        self.__credentials= OAuth2Credentials(access_token=None, client_id=_APP_ID, client_secret=_APP_SECRET,
                refresh_token=refreshToken, token_expiry=None, token_uri=GOOGLE_TOKEN_URI, user_agent=None)
        self.__folderId= self.FOLDER_ID
        self.__http= self.__credentials.authorize(createHttp(proxyHost, proxyPort, proxyUser, proxyPassword))
        self.__service= None

    @online
    @expires
    def sync(self):
        noteStatus= {}
        pageToken= None
        while True:
            result= self._service().list(q="'%s' in parents" % self.__folderId, maxResults=1000, pageToken=pageToken,
                    fields="items(id,title,modifiedDate),nextPageToken").execute()
            pageToken= result.get("nextPageToken")

            for item in filter(lambda i: i["title"].endswith(self.NOTE_EXTENSION), result["items"]):
                title= item["title"][:-6]
                if isUuid(title):
                    ns= NoteStatus(title, self.__lastModified(item))
                    ns.noteId= item["id"]
                    noteStatus[title]= ns

            for item in filter(lambda i: i["title"].endswith(self.PHOTO_EXTENSION), result["items"]):
                title= item["title"][:-4]
                if title in noteStatus:
                    ns= noteStatus[title]
                    ns.hasPhoto= True
                    ns.photoId= item["id"]

            for item in filter(lambda i: i["title"].endswith(self.REMOVED_NOTE_EXTENSION), result["items"]):
                title= item["title"][:-8]
                if isUuid(title):
                    ns= NoteStatus(title, self.__lastModified(item), True)
                    ns.noteId= item["id"]
                    if title in noteStatus:
                        nso= noteStatus[title]
                        if ns.lastModified >= nso.lastModified:
                            self.__remove(nso.noteId)
                            if nso.hasPhoto:
                                self.__remove(nso.photoId)
                        else:
                            self.__remove(ns.noteId)
                            continue
                    noteStatus[title]= ns

            if not pageToken:
                break
        self.__noteStatusCache= noteStatus
        return noteStatus

    @online
    @expires
    def get(self, uuid):
        ns= self.__noteStatusCache.get(uuid)
        if not ns or ns.removed:
            raise RuntimeError("Note[uuid=%s] does not exist" % uuid)
        content= self._service().get_media(fileId=ns.noteId).execute()
        note= unmarshalNote(content, ns.lastModified)
        if ns.hasPhoto:
            note.photo= self._service().get_media(fileId=ns.photoId).execute()
        return renderHtml(note)

    @online
    @expires
    def add(self, note):
        uuid= note.uuid
        if uuid in self.__noteStatusCache:
            ns= self.__noteStatusCache[uuid]
            if not ns.removed:
                raise RuntimeError("Note[uuid=%s] already exists" % uuid)
            else:
                self.__remove(ns.noteId)

        metadata= {
            "title": uuid + self.NOTE_EXTENSION,
            "mimeType": self.NOTE_MIMETYPE,
            "parents": [{"id": self.__folderId}],
            "modifiedDate": self.__modifiedDate(note)
        }
        content= MediaIoBaseUpload(BytesIO(marshalNote(note)), mimetype=self.NOTE_MIMETYPE, chunksize=-1, resumable=True)
        response= self._service().insert(body=metadata, media_body=content, fields="parents(id)").execute()
        self.__updateFolderId(response)
        if note.photo:
            self.__uploadPhoto(note)

    @online
    @expires
    def update(self, note):
        uuid= note.uuid
        ns= self.__noteStatusCache.get(uuid)
        if not ns or ns.removed:
            raise RuntimeError("Note[uuid=%s] does not exist" % uuid)
        if ns.hasPhoto:
            self.__remove(ns.photoId)

        content= MediaIoBaseUpload(BytesIO(marshalNote(note)), mimetype=self.NOTE_MIMETYPE, chunksize=-1, resumable=True)
        response= self._service().update(fileId=ns.noteId, newRevision=False, setModifiedDate=True,
                body={"modifiedDate": self.__modifiedDate(note)}, media_body=content, fields="parents(id)").execute()
        self.__updateFolderId(response)
        if note.photo:
            self.__uploadPhoto(note)

    @online
    @expires
    def remove(self, note):
        uuid= note.uuid
        if uuid in self.__noteStatusCache:
            ns= self.__noteStatusCache[uuid]
            self.__remove(ns.noteId)
            if ns.hasPhoto:
                self.__remove(ns.photoId)

        metadata= {
            "title": uuid + self.REMOVED_NOTE_EXTENSION,
            "mimeType": self.REMOVED_NOTE_MIMETYPE,
            "parents": [{"id": self.__folderId}],
            "modifiedDate": self.__modifiedDate(note)
        }
        response= self._service().insert(body=metadata, fields="parents(id)").execute()
        self.__updateFolderId(response)

    def _service(self):
        if self.__service is None:
            self.__service= build("drive", "v2", http=self.__http).files()
        return self.__service

    def __lastModified(self, metadata):
        return datetime.strptime(metadata["modifiedDate"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=0)

    def __modifiedDate(self, note):
        return note.lastModified.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def __updateFolderId(self, metadata):
        if self.__folderId == self.FOLDER_ID:
            parents= metadata["parents"]
            if len(parents) == 1:
                self.__folderId= parents[0]["id"]

    def __uploadPhoto(self, note):
        metadata= {
            "title": note.uuid + self.PHOTO_EXTENSION,
            "mimeType": self.PHOTO_MIMETYPE,
            "parents": [{"id": self.__folderId}],
            "modifiedDate": self.__modifiedDate(note)
        }
        content= MediaIoBaseUpload(BytesIO(note.photo), mimetype=self.PHOTO_MIMETYPE, chunksize=-1, resumable=True)
        self._service().insert(body=metadata, media_body=content, fields="id").execute()

    def __remove(self, fileId):
        self._service().delete(fileId=fileId).execute()
