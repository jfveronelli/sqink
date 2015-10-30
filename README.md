# sqink

Scroll, Quill & INK is a multiplatform note taking application. Some of its features are:

- Relies on the Markdown format, showing the notes in HTML.
- Can synchronize notes using Dropbox or Google Drive.
- Tagging and favorites.
- Filter list of notes by tag or by any word.
- Able to add a photo per note.

Even though it is was not conceived as a journal application, the Dropbox synchronization feature is compatible with [Narrate] <https://play.google.com/store/apps/details?id=com.datonicgroup.narrate.app> and
Day One <http://dayoneapp.com/>.


## Installation

The application requires Python 3.4 or later.

If the PySide package is not present, you may install it with pip:

    pip install -U PySide

To run the application, execute:

    python sqink.py

If using the binary distribution for Windows, no installation is needed, just unzip and run:

    sqink.exe


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
