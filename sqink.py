#coding:utf-8
import sys
pythonVersion= sys.version_info[0] + sys.version_info[1] * 0.1
if pythonVersion < 3.4:
    print("Python 3.4 or later is required")
    sys.exit(1)

from os.path import abspath
from os.path import dirname
from os.path import normpath
from PySide.QtGui import QApplication
from sys import argv
from sys import path
if not hasattr(sys, "frozen"):
    appPath= dirname(abspath(__file__))
    path.append(normpath(appPath + "/lib"))
    path.append(normpath(appPath + "/src"))
else:
    appPath= sys.prefix #hack for py2exe
from crossknight.sqink.ui import Window


def main():
    app= QApplication(argv)
    window= Window(appPath)

    window.show()
    status= app.exec_()
    sys.exit(status)


if __name__ == "__main__":
    main()
