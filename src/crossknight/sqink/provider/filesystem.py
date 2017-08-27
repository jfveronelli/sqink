# coding:utf-8
from crossknight.sqink.domain import isUuid
from crossknight.sqink.domain import NoteStatus
from crossknight.sqink.markdown import renderHtml
from crossknight.sqink.plist import readNote
from crossknight.sqink.plist import writeNote
from crossknight.sqink.provider import LocalNoteProvider
from datetime import datetime
from datetime import timezone
from os import listdir
from os import remove
from os import utime
from os.path import exists
from os.path import getmtime
from os.path import isfile
from os.path import normpath
import re


def getModifiedOn(path):
    return datetime.utcfromtimestamp(int(getmtime(path)))


def getTimestamp(lastModified):
    return lastModified.replace(tzinfo=timezone.utc).timestamp()


def inflateNote(notePath, photoPath=None, withoutText=False):
    with open(notePath, "rb") as file:
        note = readNote(file, getModifiedOn(notePath), withoutText)
    if photoPath and isfile(photoPath):
        with open(photoPath, "rb") as file:
            note.photo = file.read()
    return renderHtml(note)


def flattenNote(note, notePath, photoPath):
    with open(notePath, "wb") as file:
        writeNote(note, file)
    timestamp = getTimestamp(note.lastModified)
    utime(notePath, (timestamp, timestamp))
    savePhoto(note, photoPath)


def savePhoto(note, path):
    if note.photo is not None:
        with open(path, "wb") as file:
            file.write(note.photo)
        timestamp = getTimestamp(note.lastModified)
        utime(path, (timestamp, timestamp))
    elif isfile(path):
        remove(path)


class FilesystemNoteProvider(LocalNoteProvider):

    def __init__(self, narratePath):
        self.__notesPath = normpath(narratePath + "/entries")
        self.__removedNotesPath = normpath(narratePath + "/entries/deleted")
        self.__photosPath = normpath(narratePath + "photos")

    def list(self):
        names = listdir(self.__notesPath)
        return [inflateNote(self.__notePath(name), withoutText=True) for name in names if isUuid(name)]

    def search(self, alphanum):
        regexs = list(map(lambda t: re.compile(re.escape(t)), filter(lambda t: len(t) > 0, alphanum.split(" "))))
        uuids = []
        for name in listdir(self.__notesPath):
            if isUuid(name):
                note = inflateNote(self.__notePath(name))
                if all(map(lambda r: r.search(note.title) or r.search(note.tags) or r.search(note.text), regexs)):
                    uuids.append(note.uuid)
        return uuids

    def sync(self):
        notes = {}
        for name in listdir(self.__notesPath):
            if isUuid(name):
                hasPhoto = isfile(self.__photoPath(name))
                notes[name] = NoteStatus(name, getModifiedOn(self.__notePath(name)), hasPhoto=hasPhoto)
        for name in listdir(self.__removedNotesPath):
            if isUuid(name):
                removedNote = NoteStatus(name, getModifiedOn(self.__removedNotePath(name)), True)
                # Clean inconsistent files
                if name in notes:
                    if removedNote.lastModified >= notes[name].lastModified:
                        remove(self.__notePath(name))
                        if notes[name].hasPhoto:
                            remove(self.__photoPath(name))
                    else:
                        remove(self.__removedNotePath(name))
                        continue
                notes[name] = removedNote
        return notes

    def get(self, uuid):
        return inflateNote(self.__notePath(uuid), self.__photoPath(uuid))

    def add(self, note):
        uuid = note.uuid
        notePath = self.__notePath(uuid)
        if exists(notePath):
            raise RuntimeError("Note[uuid=%s] already exists" % uuid)
        flattenNote(note, notePath, self.__photoPath(uuid))
        removedNotePath = self.__removedNotePath(uuid)
        if exists(removedNotePath):
            remove(removedNotePath)

    def update(self, note):
        uuid = note.uuid
        notePath = self.__notePath(uuid)
        if not exists(notePath):
            raise RuntimeError("Note[uuid=%s] does not exist" % uuid)
        flattenNote(note, notePath, self.__photoPath(uuid))

    def remove(self, note):
        uuid = note.uuid
        notePath = self.__notePath(uuid)
        if exists(notePath):
            remove(notePath)
        photoPath = self.__photoPath(uuid)
        if exists(photoPath):
            remove(photoPath)

        removedNotePath = self.__removedNotePath(uuid)
        open(removedNotePath, "wb").close()
        timestamp = getTimestamp(note.lastModified)
        utime(removedNotePath, (timestamp, timestamp))

    def __notePath(self, uuid):
        return normpath(self.__notesPath + "/" + uuid)

    def __removedNotePath(self, uuid):
        return normpath(self.__removedNotesPath + "/" + uuid)

    def __photoPath(self, uuid):
        return normpath(self.__photosPath + "/" + uuid + ".jpg")
