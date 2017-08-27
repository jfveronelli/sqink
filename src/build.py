# coding:utf-8
from crossknight.sqink import __version__ as ver
from glob import glob
from os import makedirs
from os import remove
from os import walk
from os.path import exists
from os.path import isdir
from os.path import isfile
from os.path import join
from os.path import normpath
from re import match
from shutil import copy2
from shutil import copytree
from shutil import rmtree
from time import sleep


def version():
    return ver


def src(subpath=None):
    return "src" + (subpath or "")


def lib(subpath):
    return "python/Lib/site-packages" + subpath


def copy(source, destination):
    if isdir(source):
        copytree(source, destination)
    elif isfile(source):
        makedirs(destination, exist_ok=True)
        copy2(source, destination)
    else:
        raise FileNotFoundError


def wipe(path, analyze=False):
    path = normpath(path)
    wildcardsMatch = match(r"(.+)[/\\]\*\*[/\\](.+)", path)
    if wildcardsMatch:
        base, name = wildcardsMatch.groups()
        found = False
        for root, dirs, files in walk(base):
            for file in filter(lambda f: f == name, files):
                found = True
                wipe(join(root, file), analyze)
            for directory in filter(lambda d: d == name, list(dirs)):
                found = True
                dirs.remove(directory)
                wipe(join(root, directory), analyze)
        if not found:
            print("Missed [%s]" % path)
    elif "*" in path:
        files = glob(path)
        if files:
            for file in files:
                wipe(file, analyze)
        else:
            print("Missed [%s]" % path)
    elif isfile(path):
        if not analyze:
            remove(path)
        else:
            print("File   [%s]" % path)
    elif isdir(path):
        if not analyze:
            rmtree(path)
        else:
            print("Folder [%s]" % path)
    else:
        print("Missed [%s]" % path)


def clean(path):
    def _clean():
        if exists(path):
            rmtree(path)
        makedirs(path)
    failed = 0
    while failed < 3:
        try:
            _clean()
            return
        except OSError:
            failed += 1
            sleep(1)
    print("Tried %d times to clean path [%s] and failed!" % (failed, path))
    exit(1)
