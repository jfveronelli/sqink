# coding:utf-8
from cx_Freeze import Executable
from cx_Freeze import setup
from os.path import abspath
from os.path import dirname
from os.path import normpath

import sys
sys.argv.append("build")
sys.path.append(normpath(dirname(abspath(__file__)) + "/src"))
if True:
    from build import clean
    from build import copy
    from build import src
    from build import version
    from build import wipe


def dist(subpath=None):
    return "dist/win32" + (subpath or "")


def build(ver, script, icon, target):
    name = "Scroll, Quill & INK"
    params = {
        "build_exe": target,
        "packages": ["pkg_resources"],
        "includes": ["idna.idnadata", "queue"],
        "excludes": ["distutils", "lib2to3", "multiprocessing", "pydoc_data", "unittest", "win32com"]}
    executable = Executable(script, base="Win32GUI", icon=icon, copyright="Copyright CrossKnight © 2014")
    setup(name=name, version=ver, description=name, options={"build_exe": params}, executables=[executable])


clean(dist())

copy("README.md", dist())
copy(src("/resources/images"), dist("/resources/images"))
copy(src("/resources/js"), dist("/resources/js"))
copy(src("/resources/notes/DESCRIPTION.txt"), dist("/resources/notes"))
copy(src("/resources/styles"), dist("/resources/styles"))

build(version(), src("/sqink.py"), src("/sqink.ico"), dist())

wipe(dist("/imageformats/*d4.dll"))
wipe(dist("/PySide/docs"))
wipe(dist("/PySide/examples"))
wipe(dist("/PySide/imports"))
wipe(dist("/PySide/include"))
wipe(dist("/PySide/plugins"))
wipe(dist("/PySide/scripts"))
wipe(dist("/PySide/translations"))
wipe(dist("/PySide/typesystems"))
wipe(dist("/PySide/*.exe"))
wipe(dist("/PySide/phonon*"))
wipe(dist("/PySide/Qt3*"))
wipe(dist("/PySide/QtCLucene*"))
wipe(dist("/PySide/QtDeclarative*"))
wipe(dist("/PySide/QtDesigner*"))
wipe(dist("/PySide/QtHelp*"))
wipe(dist("/PySide/QtMultimedia*"))
wipe(dist("/PySide/QtOpenGL*"))
wipe(dist("/PySide/QtScript*"))
wipe(dist("/PySide/QtSql*"))
wipe(dist("/PySide/QtSvg*"))
wipe(dist("/PySide/QtTest*"))
wipe(dist("/PySide/QtUiTools*"))
wipe(dist("/PySide/QtXml*"))
