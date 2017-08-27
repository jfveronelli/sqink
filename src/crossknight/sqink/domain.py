# coding:utf-8
from binascii import hexlify
from re import compile
from uuid import uuid4


_UUID = compile(r"^[0-9A-F]{32}\Z")


def newUuid():
    return hexlify(uuid4().bytes).upper().decode("ascii")


def isUuid(name):
    return bool(_UUID.match(name))


def listTags(notes):
    result = []
    for note in notes:
        for tag in note.tags:
            if tag not in result:
                result.append(tag)
    result.sort(key=str.lower)
    return result


class Note:

    def __init__(self, uuid=None, lastModified=None, createdOn=None, title=None, tags=None, starred=False, text=None,
                 html=None, photo=None):
        self.uuid = uuid
        self.lastModified = lastModified
        self.createdOn = createdOn
        self.title = title
        self.tags = tags if tags is not None else []
        self.starred = starred
        self.text = text
        self.html = html
        self.photo = photo

    def __repr__(self):
        return "crossknight.sqink.domain.Note(\n" +\
                "  uuid=" + repr(self.uuid) + ",\n" +\
                "  lastModified=" + repr(self.lastModified) + ",\n" +\
                "  createdOn=" + repr(self.createdOn) + ",\n" +\
                "  title=" + repr(self.title) + ",\n" +\
                "  tags=" + repr(self.tags) + ",\n" +\
                "  starred=" + repr(self.starred) + ",\n" +\
                "  text=" + repr(self.text) + ",\n" +\
                "  html=" + repr(self.html) + ",\n" +\
                "  photo=" + repr(self.photo) + ")"

    def hasTag(self, tag):
        return tag in self.tags

    def copy(self):
        return Note(self.uuid, self.lastModified, self.createdOn, self.title, self.tags[:], self.starred, self.text,
                    self.html, self.photo)


class NoteStatus:

    def __init__(self, uuid, lastModified, removed=False, hasPhoto=False):
        self.uuid = uuid
        self.lastModified = lastModified
        self.removed = removed
        self.hasPhoto = hasPhoto

    def __repr__(self):
        return "crossknight.sqink.domain.NoteStatus(\n" +\
                "  uuid=" + repr(self.uuid) + ",\n" +\
                "  lastModified=" + repr(self.lastModified) + ",\n" +\
                "  removed=" + repr(self.removed) + ",\n" +\
                "  hasPhoto=" + repr(self.hasPhoto) + ")"

    def asNote(self):
        return Note(self.uuid, self.lastModified)
