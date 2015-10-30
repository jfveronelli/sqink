#coding:utf-8
from os.path import abspath
from os.path import dirname
from os.path import normpath
from sys import path
import unittest
testpath= dirname(abspath(__file__))
path.append(normpath(testpath + "/../src"))


def load_tests(loader, tests, pattern):
    return loader.discover(testpath, pattern="*test.py")


if __name__ == "__main__":
    unittest.main()
