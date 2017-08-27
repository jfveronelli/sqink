# coding:utf-8
from os.path import abspath
from os.path import dirname
from os.path import normpath

import sys
sys.path.append(normpath(dirname(abspath(__file__)) + "/src"))
if True:
    from build import clean
    from build import copy
    from build import lib
    from build import src
    from build import wipe


def dist(subpath=None):
    return "dist/linux" + (subpath or "")


clean(dist())

copy("README.md", dist())
copy(src("/crossknight"), dist("/lib/crossknight"))
copy(src("/resources/images"), dist("/resources/images"))
copy(src("/resources/js"), dist("/resources/js"))
copy(src("/resources/notes/DESCRIPTION.txt"), dist("/resources/notes"))
copy(src("/resources/styles"), dist("/resources/styles"))
copy(src("/sqink.ico"), dist())
copy(src("/sqink.py"), dist())

copy(lib("/apiclient"), dist("/lib/apiclient"))
copy(lib("/certifi"), dist("/lib/certifi"))
copy(lib("/chardet"), dist("/lib/chardet"))
copy(lib("/dropbox"), dist("/lib/dropbox"))
copy(lib("/googleapiclient"), dist("/lib/googleapiclient"))
copy(lib("/httplib2"), dist("/lib/httplib2"))
copy(lib("/idna"), dist("/lib/idna"))
copy(lib("/markdown"), dist("/lib/markdown"))
copy(lib("/mistune"), dist("/lib/mistune"))
copy(lib("/mistune.py"), dist("/lib"))
copy(lib("/oauth2client"), dist("/lib/oauth2client"))
copy(lib("/pyasn1"), dist("/lib/pyasn1"))
copy(lib("/pyasn1_modules"), dist("/lib/pyasn1_modules"))
copy(lib("/rsa"), dist("/lib/rsa"))
copy(lib("/requests"), dist("/lib/requests"))
copy(lib("/six.py"), dist("/lib"))
copy(lib("/uritemplate"), dist("/lib/uritemplate"))
copy(lib("/urllib3"), dist("/lib/urllib3"))

wipe(dist("/**/__pycache__"))
