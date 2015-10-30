#coding:utf-8
from crossknight.sqink.domain import Note
from crossknight.sqink.markdown import renderHtml
from unittest import TestCase


class ModuleTest(TestCase):

    def testRenderHtmlShouldSucceed(self):
        note= Note(title="Some title", tags=["one", "two"], text="Hello, **world**!")

        renderHtml(note)

        self.assertIn("<p>Hello, <strong>world</strong>!</p>", note.html)
