#coding:utf-8
from crossknight.sqink.domain import Note
from plistlib import dump
from plistlib import dumps
from plistlib import load
from plistlib import loads


_AGENT_NAME= "sqink"


def _asPlist(note):
    creator= {}
    creator["Device Agent"]= _AGENT_NAME
    creator["Generation Date"]= note.createdOn
    creator["Host Name"]= _AGENT_NAME
    creator["OS Agent"]= "Desktop"
    creator["Software Agent"]= _AGENT_NAME

    plist= {}
    plist["UUID"]= note.uuid
    plist["Creation Date"]= note.createdOn
    plist["Creator"]= creator
    plist["Entry Text"]= note.title + "\n" + note.text
    plist["Starred"]= note.starred
    plist["Time Zone"]= "Argentina Time"
    plist["Tags"]= note.tags
    return plist


def writeNote(note, fileObj):
    dump(_asPlist(note), fileObj)


def marshalNote(note):
    return dumps(_asPlist(note))


def _asNote(plist, lastModified, skipContent):
    uuid= plist["UUID"]
    createdOn= plist["Creation Date"]
    lines= plist["Entry Text"].splitlines()
    title= lines[0]
    tags= plist["Tags"]
    starred= plist["Starred"]
    textStartIndex= 1 if lines[1] else 2 #Narrate sometimes used a blank line as divider
    text= "\n".join(lines[textStartIndex:]) if not skipContent else None
    return Note(uuid=uuid, lastModified=lastModified, createdOn=createdOn, title=title, tags=tags, starred=starred, text=text)


def readNote(fileObj, lastModified, skipContent=False):
    return _asNote(load(fileObj), lastModified, skipContent)


def unmarshalNote(data, lastModified, skipContent=False):
    return _asNote(loads(data), lastModified, skipContent)
