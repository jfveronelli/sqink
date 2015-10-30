#coding:utf-8
from crossknight.sqink.provider.filesystem import FilesystemNoteProvider
from os.path import dirname
from os.path import normpath
from unittest import TestCase


class FilesystemNoteProviderTest(TestCase):

    def testListShouldSucceed(self):
        path= normpath(dirname(__file__) + "/resources")

        provider= FilesystemNoteProvider(path)
        notes= provider.list()

        self.assertEqual(1, len(notes))
        self.assertEqual("Probando 1,2,3...", notes[0].title)
