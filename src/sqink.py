# coding:utf-8
from locale import LC_ALL
from locale import setlocale
from os.path import abspath
from os.path import dirname
from os.path import isdir
from os.path import normpath
import sys


def checkPythonVersion():
    pythonVersion = sys.version_info[0] + sys.version_info[1] * 0.1
    if pythonVersion != 3.4:
        print("Python 3.4 is required")
        sys.exit(1)


def checkPySide():
    try:
        import PySide.QtGui
    except ImportError:
        PySide = "PySide must be installed by running:\n" +\
                 "    python -m pip install PySide"
        print(PySide)
        sys.exit(1)


def getAppPath():
    if hasattr(sys, "frozen"):  # running from Windows executable
        return sys.prefix
    modulePath = normpath(dirname(abspath(__file__)))
    libPath = normpath(modulePath + "/lib")
    if isdir(libPath):  # running from installed source
        sys.path.insert(0, libPath)
    else:  # running from source code
        sys.path.insert(0, modulePath)
        sys.path.insert(0, normpath(modulePath + "/../python/Lib/site-packages"))
    return modulePath


def main():
    checkPythonVersion()
    checkPySide()
    appPath = getAppPath()

    import crossknight.sqink.ui
    import PySide.QtGui
    app = PySide.QtGui.QApplication(sys.argv)
    setlocale(LC_ALL, "C")
    window = crossknight.sqink.ui.Window(appPath)

    window.show()
    status = app.exec_()
    sys.exit(status)


if __name__ == "__main__":
    main()
