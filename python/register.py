#coding:utf-8
#
# script to register Python 2.0 or later for use with win32all
# and other extensions that require Python registry settings
#
# written by Joakim Löw for Secret Labs AB / PythonWare
#
# source:
# http://www.pythonware.com/products/works/articles/regpy20.htm
import sys
from winreg import *


version= sys.version[:3]
installpath= sys.prefix

regpath= "SOFTWARE\\Python\\Pythoncore\\%s\\" % version
installkey= "InstallPath"
pythonkey= "PythonPath"
pythonpath= "%s\\Lib;%s\\DLLs" % (installpath, installpath)


def RegisterPy():
  try:
    reg= OpenKey(HKEY_LOCAL_MACHINE, regpath)
  except EnvironmentError:
    try:
      reg= CreateKey(HKEY_LOCAL_MACHINE, regpath)
      SetValue(reg, installkey, REG_SZ, installpath)
      SetValue(reg, pythonkey, REG_SZ, pythonpath)
      CloseKey(reg)
    except:
      print("*** Unable to register!")
      return
    print("--- Python %s is now registered!" % version)
    return
  if (QueryValue(reg, installkey) == installpath and QueryValue(reg, pythonkey) == pythonpath):
    CloseKey(reg)
    print("=== Python %s is already registered!" % version)
    return
  CloseKey(reg)
  print("*** Unable to register!")
  print("*** You probably have another Python installation!")


def UnRegisterPy():
  try:
    reg= OpenKey(HKEY_LOCAL_MACHINE, regpath)
  except EnvironmentError:
    print("*** Python not registered?!")
    return
  try:
    DeleteKey(reg, installkey)
    DeleteKey(reg, pythonkey)
    DeleteKey(HKEY_LOCAL_MACHINE, regpath)
  except:
    print("*** Unable to un-register!")
  else:
    print("--- Python %s is no longer registered!" % version)


if __name__ == "__main__":
  RegisterPy()
