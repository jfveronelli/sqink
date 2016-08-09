#coding:utf-8
from glob import glob
from os import makedirs
from os import remove
from os import walk
from os.path import isdir
from os.path import isfile
from os.path import join
from os.path import normpath
from re import match
from shutil import copy2
from shutil import copytree
from shutil import rmtree
from time import sleep


DIST_PATH= "dist/other"


def wipe(path, analyze=False):
    path= normpath(path)
    if match(r"\*\*[/\\]", path):
        name= path[3:]
        found= False
        for root, dirs, files in walk("./"):
            for f in filter(lambda f: f == name, files):
                found= True
                wipe(join(root, f), analyze)
            for d in filter(lambda d: d == name, list(dirs)):
                found= True
                dirs.remove(d)
                wipe(join(root, d), analyze)
        if not found:
            print("Missed [%s]" % path)
    elif "*" in path:
        files= glob(path)
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


def clean():
    if isdir(DIST_PATH):
        rmtree(DIST_PATH)
        sleep(1)
    makedirs(DIST_PATH, exist_ok=True)
    wipe("**/__pycache__")


def copyResources():
    copy2("sqink.ico", DIST_PATH)
    copy2("sqink.py", DIST_PATH)
    copy2("README.md", DIST_PATH)
    copytree("src", DIST_PATH + "/lib")
    copytree("resources/images", DIST_PATH + "/resources/images")
    copytree("resources/js", DIST_PATH + "/resources/js")
    makedirs(DIST_PATH + "/resources/notes", exist_ok=True)
    copy2("resources/notes/DESCRIPTION.txt", DIST_PATH + "/resources/notes")
    copytree("resources/styles", DIST_PATH + "/resources/styles")


clean()
copyResources()
