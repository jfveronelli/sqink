# sqink

**Scroll, Quill & INK** is a multiplatform note taking application. Some of its features are:

- Relies on the Markdown format, showing the notes in HTML.
- Can synchronize notes using Dropbox or Google Drive.
- Uses tags and stars to classify notes.
- Filters list of notes by tag or by any word.
- Able to add a photo per note.

Even though it is was not conceived as a journal application, the Dropbox synchronization feature is compatible with [Narrate](https://play.google.com/store/apps/details?id=com.datonicgroup.narrate.app) for Android and [Day One](http://dayoneapp.com/) for Mac/iOS.


## Screenshots

![](https://github.com/jfveronelli/sqink/raw/master/docs/screenshots/edit.jpg)

![](https://github.com/jfveronelli/sqink/raw/master/docs/screenshots/view.jpg)

![](https://github.com/jfveronelli/sqink/raw/master/docs/screenshots/fullscreen.jpg)


## Download

Latest version is 1.1.4, released on 2015/10/30.


### Windows binary

Download the latest version from [here](https://www.dropbox.com/s/tuauv6m7124x93h/sqink-1.1.4-setup.exe?dl=1), execute to install the application, and run `sqink.exe` to start.

The application may be run from a USB stick. No other requirements are needed.


### Other platforms

A working [Python 3.4+](https://www.python.org/) environment is required.

The [PySide 1.2+](http://qt-project.org/wiki/PySide) package must be already installed. Usually it can be installed with PIP:

    pip install -U PySide

Download the application from [here](https://www.dropbox.com/s/kr4lmrjta22u8vh/sqink-1.1.4.zip?dl=1) and run as:

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
- py2exe <http://www.py2exe.org/>
- Xiao Icons <http://delacro.deviantart.com/art/Xiao-Icon-84772282>


## License

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
