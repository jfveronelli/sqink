#coding:utf-8
#Created by: python -m py2exe sqink.py -W build-win32.py
from os import makedirs
from os.path import abspath
from os.path import dirname
from os.path import isdir
from os.path import normpath
from shutil import copy2
from shutil import copytree
from shutil import rmtree
import sys
from time import sleep
sys.path.append(normpath(dirname(abspath(__file__)) + "/src"))
sys.argv.append("py2exe")
import crossknight.sqink

from distutils.core import setup
import py2exe


RT_BITMAP= 2
RT_MANIFEST= 24
DIST_PATH= "dist/win32"
manifest_template= '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="5.0.0.0"
    processorArchitecture="*"
    name="%(prog)s"
    type="win32"
  />
  <description>%(prog)s</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel
            level="%(level)s"
            uiAccess="false">
        </requestedExecutionLevel>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="*"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
  </dependency>
</assembly>
'''


def clean():
    if isdir(DIST_PATH):
        rmtree(DIST_PATH)
        sleep(1)
    makedirs(DIST_PATH, exist_ok=True)


def copyResources():
    copy2("README.md", DIST_PATH)
    copy2("src/dropbox/trusted-certs.crt", DIST_PATH)
    copy2("src/httplib2/cacerts.txt", DIST_PATH)
    copytree("resources/images", DIST_PATH + "/resources/images")
    makedirs(DIST_PATH + "/resources/notes", exist_ok=True)
    copy2("resources/notes/DESCRIPTION.txt", DIST_PATH + "/resources/notes")
    copytree("resources/styles", DIST_PATH + "/resources/styles")
    copytree("python/Lib/site-packages/PySide/plugins/imageformats", DIST_PATH + "/imageformats")


class Target(object):
    '''Target is the baseclass for all executables that are created.
    It defines properties that are shared by all of them.
    '''

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def copy(self):
        return Target(**self.__dict__)

    def __setitem__(self, name, value):
        self.__dict__[name] = value


sqink= Target(
    version= crossknight.sqink.__version__,
    product_name= "Scroll, Quill & INK",
    copyright= "Copyright CrossKnight © 2014",

    script= "sqink.py", #Path of the main script
    #dest_base= "sqink", #Basename of the executable, if different from script name

    icon_resources= [(1, "sqink.ico")],
    other_resources= [(RT_MANIFEST, 1, (manifest_template % dict(prog="sqink", level="asInvoker")).encode("utf-8"))]
    #For bitmap resources, the first 14 bytes must be skipped when reading the file:
    #                    (RT_BITMAP, 1, open("bitmap.bmp", "rb").read()[14:]),
)


# ``zipfile`` and ``bundle_files`` options explained:
# ===================================================
#
# zipfile is the Python runtime library for your exe/dll-files; it
# contains in a ziparchive the modules needed as compiled bytecode.
#
# If 'zipfile=None' is used, the runtime library is appended to the
# exe/dll-files (which will then grow quite large), otherwise the
# zipfile option should be set to a pathname relative to the exe/dll
# files, and a library-file shared by all executables will be created.
#
# The py2exe runtime *can* use extension module by directly importing
# the from a zip-archive - without the need to unpack them to the file
# system.  The bundle_files option specifies where the extension modules,
# the python dll itself, and other needed dlls are put.
#
# bundle_files == 3:
#     Extension modules, the Python dll and other needed dlls are
#     copied into the directory where the zipfile or the exe/dll files
#     are created, and loaded in the normal way.
#
# bundle_files == 2:
#     Extension modules are put into the library ziparchive and loaded
#     from it directly.
#     The Python dll and any other needed dlls are copied into the
#     directory where the zipfile or the exe/dll files are created,
#     and loaded in the normal way.
#
# bundle_files == 1:
#     Extension modules and the Python dll are put into the zipfile or
#     the exe/dll files, and everything is loaded without unpacking to
#     the file system.  This does not work for some dlls, so use with
#     caution.
#
# bundle_files == 0:
#     Extension modules, the Python dll, and other needed dlls are put
#     into the zipfile or the exe/dll files, and everything is loaded
#     without unpacking to the file system.  This does not work for
#     some dlls, so use with caution.
py2exe_options= dict(
    packages= [],
    includes= ["PySide.QtNetwork"],
    #excludes= "tof_specials Tkinter".split(),
    #ignores= "dotblas gnosis.xml.pickle.parsers._cexpat mx.DateTime".split(),
    #dll_excludes= "MSVCP90.dll mswsock.dll powrprof.dll".split(),
    optimize= 0,
    compressed= False, #Uncompressed may or may not have a faster startup
    bundle_files= 3,
    dist_dir=DIST_PATH
)


clean()
copyResources()
setup(name="name", console=[], windows=[sqink], zipfile=None, options={"py2exe": py2exe_options})
