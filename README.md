# sqink
[![release](https://img.shields.io/github/release/jfveronelli/sqink.svg)](https://github.com/jfveronelli/sqink/releases/latest)
[![status](https://travis-ci.org/jfveronelli/sqink.svg?branch=master)](https://travis-ci.org/jfveronelli/sqink)
[![coverage](https://codecov.io/gh/jfveronelli/sqink/branch/master/graph/badge.svg)](https://codecov.io/gh/jfveronelli/sqink)

**Scroll, Quill & INK** is a multiplatform note taking application. Some of its features are:

- Relies on the Markdown format, showing the notes in HTML.
- Can synchronize notes using Dropbox or Google Drive.
- Uses tags and stars to classify notes.
- Filters list of notes by tag or by any word.
- Able to add a photo per note.


## Screenshots

![](https://github.com/jfveronelli/sqink/raw/master/docs/screenshots/edit.jpg)

![](https://github.com/jfveronelli/sqink/raw/master/docs/screenshots/view.jpg)

![](https://github.com/jfveronelli/sqink/raw/master/docs/screenshots/fullscreen.jpg)


## Download

Latest version is 1.2.0, released on 2017/09/01.


### Windows binary

Download the latest version from [here](https://github.com/jfveronelli/sqink/releases/download/v1.2.0/sqink-1.2.0-win32.exe), execute the file to extract the application, and the run `sqink.exe` to start.

The application may be run from a USB stick. No other requirements are needed.


### Other platforms

A working [Python 3.4](https://www.python.org/) environment is required.

The [PySide 1.2](http://qt-project.org/wiki/PySide) package must be already installed. Usually it can be installed with PIP:

    python -m pip install -U PySide

Download the application from [here](https://github.com/jfveronelli/sqink/releases/download/v1.2.0/sqink-1.2.0-linux.tar.gz), unpack file, and run as:

    python sqink.py


## Author

Julio Francisco Veronelli <julio.veronelli@crossknight.com.ar>


## Thanks

This application would not be possible without the following libraries and resources:

- Python <https://www.python.org/>
- PySide <http://qt-project.org/wiki/PySide>
- mistune <https://github.com/lepture/mistune>
- Python-Markdown <http://pythonhosted.org/Markdown/>
- Dropbox Core API for Python <https://www.dropbox.com/developers/core>
- Google APIs Client Library for Python <https://developers.google.com/api-client-library/python/>
- cx_Freeze <https://anthony-tuininga.github.io/cx_Freeze/>
- mermaid <http://knsv.github.io/mermaid/>
- Xiao Icons <http://delacro.deviantart.com/art/Xiao-Icon-84772282>


## MIT License

Copyright (c) 2014 CrossKnight

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
