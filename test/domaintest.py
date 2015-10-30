#coding:utf-8
from crossknight.sqink.domain import isUuid
from crossknight.sqink.domain import uuid
from unittest import TestCase


class ModuleTest(TestCase):

    def testIsUuisShouldReturnTrue(self):
        self.assertTrue(isUuid("ABCDEF0123456789ABCDEF0123456789"))

    def testIsUuisShouldReturnFalse(self):
        self.assertFalse(isUuid("ABCDEf0123456789ABCDEF0123456789"))
        self.assertFalse(isUuid("ABCDEG0123456789ABCDEF0123456789"))
        self.assertFalse(isUuid("ABCDEF0123456789ABCDEF012345678"))
        self.assertFalse(isUuid("ABCDEF0123456789ABCDEF01234567890"))

    def testUuidShouldSucceed(self):
        result= uuid()

        self.assertTrue(isUuid(result))
        self.assertEqual(str, type(result))
