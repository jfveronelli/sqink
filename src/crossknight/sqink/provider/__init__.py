# coding:utf-8
from abc import ABC
from abc import abstractmethod
from datetime import timedelta


class AConnectionError(Exception):
    pass


class InvalidProxyError(Exception):
    pass


class TokenExpiredError(Exception):
    pass


class RemoteNoteProvider(ABC):

    @staticmethod
    def requiresReverseUpdate():
        return False

    @abstractmethod
    def sync(self):
        pass

    @abstractmethod
    def get(self, uuid):
        pass

    @abstractmethod
    def add(self, note):
        pass

    @abstractmethod
    def update(self, note):
        pass

    @abstractmethod
    def remove(self, note):
        pass


class LocalNoteProvider(RemoteNoteProvider):

    @abstractmethod
    def list(self):
        pass

    @abstractmethod
    def search(self, alphanum):
        pass

    def close(self):
        pass


class Synchronizer(object):

    def __init__(self, noteProviderA, noteProviderB):
        self.__noteProviderA = noteProviderA
        self.__noteProviderB = noteProviderB

    def sync(self):
        noteStatusDictA = self.__noteProviderA.sync()
        noteStatusDictB = self.__noteProviderB.sync()
        self.__applyChanges(noteStatusDictA, self.__noteProviderA, noteStatusDictB, self.__noteProviderB)
        self.__applyChanges(noteStatusDictB, self.__noteProviderB, noteStatusDictA, self.__noteProviderA)

    def __applyChanges(self, fromNoteStatusDict, fromNoteProvider, toNoteStatusDict, toNoteProvider):
        for fromNoteStatus in fromNoteStatusDict.values():
            uuid = fromNoteStatus.uuid
            toNoteStatus = toNoteStatusDict.get(uuid)
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

    @staticmethod
    def __isUpdatedLater(noteStatus, otherNoteStatus):
        return noteStatus.lastModified - otherNoteStatus.lastModified >= timedelta(seconds=1)

    @staticmethod
    def __addNote(noteProvider, uuid, sourceNoteProvider):
        note = sourceNoteProvider.get(uuid)
        noteProvider.add(note)
        if noteProvider.requiresReverseUpdate():
            sourceNoteProvider.update(note)

    @staticmethod
    def __updateNote(noteProvider, uuid, sourceNoteProvider):
        note = sourceNoteProvider.get(uuid)
        noteProvider.update(note)
        if noteProvider.requiresReverseUpdate():
            sourceNoteProvider.update(note)

    @staticmethod
    def __removeNote(noteProvider, noteStatus, sourceNoteProvider):
        note = noteStatus.asNote()
        noteProvider.remove(note)
        if noteProvider.requiresReverseUpdate():
            sourceNoteProvider.remove(note)
