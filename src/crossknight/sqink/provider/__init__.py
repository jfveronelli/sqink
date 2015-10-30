#coding:utf-8
from datetime import timedelta


class AConnectionError(Exception):
    pass


class InvalidProxyError(Exception):
    pass


class TokenExpiredError(Exception):
    pass


class RemoteNoteProvider:

    def requiresReverseUpdate(self):
        return False

    def sync(self):
        raise NotImplementedError

    def get(self, uuid):
        raise NotImplementedError

    def add(self, note):
        raise NotImplementedError

    def update(self, note):
        raise NotImplementedError

    def remove(self, note):
        raise NotImplementedError


class LocalNoteProvider(RemoteNoteProvider):

    def list(self):
        raise NotImplementedError

    def search(self, alphanum):
        raise NotImplementedError

    def close(self):
        pass


class Synchronizer:

    def __init__(self, noteProviderA, noteProviderB):
        self.__noteProviderA= noteProviderA
        self.__noteProviderB= noteProviderB

    def sync(self):
        noteStatusDictA= self.__noteProviderA.sync()
        noteStatusDictB= self.__noteProviderB.sync()
        self.__applyChanges(noteStatusDictA, self.__noteProviderA, noteStatusDictB, self.__noteProviderB)
        self.__applyChanges(noteStatusDictB, self.__noteProviderB, noteStatusDictA, self.__noteProviderA)

    def __applyChanges(self, fromNoteStatusDict, fromNoteProvider, toNoteStatusDict, toNoteProvider):
        for fromNoteStatus in fromNoteStatusDict.values():
            uuid= fromNoteStatus.uuid
            toNoteStatus= toNoteStatusDict.get(uuid)
            if toNoteStatus is None:
                if fromNoteStatus.removed:
                    self.__removeNote(toNoteProvider, fromNoteStatus, fromNoteProvider)
                else:
                    self.__addNote(toNoteProvider, uuid, fromNoteProvider)
            elif self.__isUpdatedLater(fromNoteStatus, toNoteStatus):
                if fromNoteStatus.removed:
                    self.__removeNote(toNoteProvider, fromNoteStatus, fromNoteProvider)
                elif toNoteStatus.removed:
                    self.__addNote(toNoteProvider, uuid, fromNoteProvider)
                else:
                    self.__updateNote(toNoteProvider, uuid, fromNoteProvider)
            elif fromNoteStatus.removed and not toNoteStatus.removed:
                self.__removeNote(toNoteProvider, fromNoteStatus, fromNoteProvider)

    def __isUpdatedLater(self, noteStatus, otherNoteStatus):
        return noteStatus.lastModified - otherNoteStatus.lastModified >= timedelta(seconds=1)

    def __addNote(self, noteProvider, uuid, sourceNoteProvider):
        note= sourceNoteProvider.get(uuid)
        noteProvider.add(note)
        if noteProvider.requiresReverseUpdate():
            sourceNoteProvider.update(note)

    def __updateNote(self, noteProvider, uuid, sourceNoteProvider):
        note= sourceNoteProvider.get(uuid)
        noteProvider.update(note)
        if noteProvider.requiresReverseUpdate():
            sourceNoteProvider.update(note)

    def __removeNote(self, noteProvider, noteStatus, sourceNoteProvider):
        note= noteStatus.asNote()
        noteProvider.remove(note)
        if noteProvider.requiresReverseUpdate():
            sourceNoteProvider.remove(note)
