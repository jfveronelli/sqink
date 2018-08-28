# coding:utf-8
from configparser import ConfigParser
from crossknight.sqink import __version__ as version
from crossknight.sqink.domain import listTags
from crossknight.sqink.domain import newUuid
from crossknight.sqink.domain import Note
from crossknight.sqink.markdown import renderHtml
from crossknight.sqink.provider import AConnectionError
from crossknight.sqink.provider import InvalidProxyError
from crossknight.sqink.provider import Synchronizer
from crossknight.sqink.provider import TokenExpiredError
from crossknight.sqink.provider.dropbox import DropboxAuthorizator
from crossknight.sqink.provider.dropbox import DropboxNoteProvider
from crossknight.sqink.provider.dropbox import SyncFolder
from crossknight.sqink.provider.gdrive import GoogleDriveAuthorizator
from crossknight.sqink.provider.gdrive import GoogleDriveNoteProvider
from crossknight.sqink.provider.sqlite import SqliteNoteProvider
from datetime import datetime
from os.path import normpath
from PySide.QtCore import QRegExp
from PySide.QtCore import Qt
from PySide.QtCore import QUrl
from PySide.QtCore import Signal
from PySide.QtGui import *
from PySide.QtNetwork import QNetworkProxy
from PySide.QtWebKit import QWebPage
from PySide.QtWebKit import QWebView


class ResourceCache:

    def __init__(self, resourcePath):
        self.__resourcePath = resourcePath
        self.__pixmapCache = {}
        self.__iconCache = {}

    def url(self):
        return QUrl.fromLocalFile(self.__resourcePath + "/")

    def pixmap(self, name):
        if name in self.__pixmapCache:
            return self.__pixmapCache[name]
        pixmap = QPixmap(normpath(self.__resourcePath + "/images/" + name))
        self.__pixmapCache[name] = pixmap
        return pixmap

    def icon(self, name):
        if name in self.__iconCache:
            return self.__iconCache[name]
        icon = QIcon(self.pixmap(name))
        self.__iconCache[name] = icon
        return icon


rc = None


class Config:

    __GROUP = "sqink"
    __DEFAULTS = {
        __GROUP: {
            "proxy.host": None,
            "proxy.port": None,
            "proxy.user": None,
            "proxy.password": None,
            "dropbox.enabled": False,
            "dropbox.folder": SyncFolder.Narrate,
            "dropbox.token": None,
            "googledrive.enabled": False,
            "googledrive.token": None
        }
    }

    def __init__(self, appPath):
        self.__filePath = normpath(appPath + "/sqink.ini")
        self.__configParser = ConfigParser(interpolation=None, allow_no_value=True)
        self.__configParser.read_dict(self.__DEFAULTS)
        self.__configParser.read(self.__filePath)

    def getProxyHost(self):
        return self.__configParser.get(self.__GROUP, "proxy.host")

    def setProxyHost(self, value):
        self.__set("proxy.host", value)

    def getProxyPort(self):
        value = self.__configParser.get(self.__GROUP, "proxy.port")
        return int(value) if value else 0

    def setProxyPort(self, value):
        self.__set("proxy.port", value)

    def getProxyUser(self):
        return self.__configParser.get(self.__GROUP, "proxy.user")

    def setProxyUser(self, value):
        self.__set("proxy.user", value)

    def getProxyPassword(self):
        return self.__configParser.get(self.__GROUP, "proxy.password")

    def setProxyPassword(self, value):
        self.__set("proxy.password", value)

    def isDropboxEnabled(self):
        return self.__configParser.get(self.__GROUP, "dropbox.enabled") == "True"

    def setDropboxEnabled(self, value):
        self.__set("dropbox.enabled", value)

    def getDropboxFolder(self):
        return self.__configParser.get(self.__GROUP, "dropbox.folder")

    def setDropboxFolder(self, value):
        self.__set("dropbox.folder", value)

    def getDropboxToken(self):
        return self.__configParser.get(self.__GROUP, "dropbox.token")

    def setDropboxToken(self, value):
        self.__set("dropbox.token", value)

    def isGoogleDriveEnabled(self):
        return self.__configParser.get(self.__GROUP, "googledrive.enabled") == "True"

    def setGoogleDriveEnabled(self, value):
        self.__set("googledrive.enabled", value)

    def getGoogleDriveToken(self):
        return self.__configParser.get(self.__GROUP, "googledrive.token")

    def setGoogleDriveToken(self, value):
        self.__set("googledrive.token", value)

    def save(self):
        with open(self.__filePath, "wt") as file:
            self.__configParser.write(file)

    def __set(self, key, value):
        value = str(value) if value is not None else ""
        self.__configParser.set(self.__GROUP, key, value)


class ValidationError(Exception):
    pass


class TagLineEdit(QLineEdit):

    backspacePressedAtStart = Signal()

    def __init__(self):
        QLineEdit.__init__(self)
        self.setFrame(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace and self.cursorPosition() == 0 and event.count() == 1 \
                and not event.isAutoRepeat():
            # noinspection PyUnresolvedReferences
            self.backspacePressedAtStart.emit()
        QLineEdit.keyPressEvent(self, event)


class TagsEditor(QFrame):

    SEPARATOR = ";"

    def __init__(self, parentWindow):
        QFrame.__init__(self)
        self.setObjectName("tagsEditor")
        self.setStyleSheet("QFrame#tagsEditor {border:1px solid #828790; background-color:#ffffff;}")
        self.__tags = []
        self.__tagWidgets = []

        self.__layout = QHBoxLayout()
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(1)
        self.setLayout(self.__layout)

        self.__txtTag = TagLineEdit()
        # noinspection PyUnresolvedReferences
        self.__txtTag.textEdited.connect(self.__onTextEdited)
        # noinspection PyUnresolvedReferences
        self.__txtTag.backspacePressedAtStart.connect(self.__onBackspacePressedAtStart)
        self.__layout.addWidget(self.__txtTag)

        self.__completer = QCompleter(self)
        self.__completer.setModelSorting(QCompleter.CaseInsensitivelySortedModel)
        self.__completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.__txtTag.setCompleter(self.__completer)

        parentWindow.tagsChanged.connect(self.__onTagsChanged)

    def isModified(self):
        return self.__txtTag.isModified()

    def setModified(self, value):
        self.__txtTag.setModified(value)

    def tags(self):
        tags = self.__tags[:]
        text = self.__txtTag.text().strip()
        if text:
            tags.append(text)
        return tags

    def setTags(self, tags):
        self.__tags = []
        for widget in self.__tagWidgets:
            self.__layout.removeWidget(widget)
            widget.setParent(None)
        self.__tagWidgets = []
        self.__txtTag.setText("")

        for tag in tags:
            self.__addTag(tag)

    def __addTag(self, tag):
        self.__tags.append(tag)
        label = QLabel(tag)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        label.setStyleSheet("border:1px solid #ffffff; border-radius:0.5em; background-color:#ffc400; padding:0 0.1em;")
        self.__layout.insertWidget(len(self.__tagWidgets), label)
        self.__tagWidgets.append(label)

    def __onTextEdited(self, text):
        if self.SEPARATOR in text:
            tags = text.split(self.SEPARATOR)
            lastTag = tags.pop().lstrip()

            for tag in filter(lambda t: len(t) > 0, map(lambda t: t.strip(), tags)):
                if tag not in self.__tags:
                    self.__addTag(tag)
            self.__txtTag.setText(lastTag)
            self.setModified(True)

    def __onBackspacePressedAtStart(self):
        if self.__tags:
            del self.__tags[-1]
            widget = self.__tagWidgets[-1]
            self.__layout.removeWidget(widget)
            widget.setParent(None)
            del self.__tagWidgets[-1]
            self.setModified(True)

    def __onTagsChanged(self, tags):
        self.__completer.setModel(QStringListModel(tags))


class StarButton(QPushButton):

    def __init__(self):
        QPushButton.__init__(self)
        self.__sIcon = rc.icon("star-16x16.png")
        self.__sToolTip = "Star note"
        self.__uIcon = rc.icon("star-hollow-16x16.png")
        self.__uToolTip = "Remove star"
        self.__modified = False
        self.__starred = False
        self.setStarred(False)
        # noinspection PyUnresolvedReferences
        self.clicked.connect(self.__toggle)

    def setModified(self, value):
        self.__modified = value

    def isModified(self):
        return self.__modified

    def setStarred(self, value):
        self.setModified(False)
        self.__starred = value
        self.setIcon(self.__uIcon if value else self.__sIcon)
        self.setToolTip(self.__uToolTip if value else self.__sToolTip)

    def isStarred(self):
        return self.__starred

    def __toggle(self):
        self.setStarred(not self.isStarred())
        self.setModified(True)


class PhotoButton(QPushButton):

    def __init__(self):
        QPushButton.__init__(self)
        self.__pIcon = rc.icon("photo-16x16.png")
        self.__pToolTip = "Add image"
        self.__nIcon = rc.icon("photo-delete-16x16.png")
        self.__nToolTip = "Remove image"
        self.__modified = False
        self.__photo = None
        self.setPhoto(None)
        # noinspection PyUnresolvedReferences
        self.clicked.connect(self.__toggle)

    def setModified(self, value):
        self.__modified = value

    def isModified(self):
        return self.__modified

    def setPhoto(self, value):
        self.setModified(False)
        self.__photo = value
        self.setIcon(self.__nIcon if value is not None else self.__pIcon)
        self.setToolTip(self.__nToolTip if value is not None else self.__pToolTip)

    def photo(self):
        return self.__photo

    def __toggle(self):
        if self.photo() is None:
            # noinspection PyCallByClass
            path, selectedFilter = QFileDialog.getOpenFileName(self, "Add image", filter="Image File (*.jpg)")
            if not path:
                return
            with open(path, "rb") as file:
                self.setPhoto(file.read())
        else:
            self.setPhoto(None)
        self.setModified(True)


class Editor(QWidget):

    def __init__(self, parentWindow, confirmCallback, cancelCallback):
        QWidget.__init__(self)
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        lblTitle = QLabel()
        lblTitle.setPixmap(rc.pixmap("title-16x16.png"))
        lblTitle.setToolTip("Title")
        layout.addWidget(lblTitle, 0, 0)

        self.__txtTitle = QLineEdit()
        layout.addWidget(self.__txtTitle, 0, 1)

        self.__btnSave = QPushButton()
        self.__btnSave.setIcon(rc.icon("confirm-16x16.png"))
        self.__btnSave.setToolTip("Save note (CTRL + S)")
        # noinspection PyUnresolvedReferences
        self.__btnSave.clicked.connect(self.__onConfirm)
        self.__btnSave.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_S))
        layout.addWidget(self.__btnSave, 0, 2)

        self.__btnCancel = QPushButton()
        self.__btnCancel.setIcon(rc.icon("cancel-16x16.png"))
        self.__btnCancel.setToolTip("Cancel changes (ESC)")
        # noinspection PyUnresolvedReferences
        self.__btnCancel.clicked.connect(self.__onCancel)
        self.__btnCancel.setShortcut(QKeySequence(Qt.Key_Escape))
        layout.addWidget(self.__btnCancel, 0, 3)

        lblTags = QLabel()
        lblTags.setPixmap(rc.pixmap("tag-16x16.png"))
        lblTags.setToolTip("Tags (separated by " + TagsEditor.SEPARATOR + ")")
        layout.addWidget(lblTags, 1, 0)

        self.__txtTags = TagsEditor(parentWindow)
        layout.addWidget(self.__txtTags, 1, 1)

        self.__btnStar = StarButton()
        layout.addWidget(self.__btnStar, 1, 2)

        self.__btnPhoto = PhotoButton()
        layout.addWidget(self.__btnPhoto, 1, 3)

        self.__txtContent = QPlainTextEdit()
        layout.addWidget(self.__txtContent, 2, 0, 1, 4)

        self.setTabOrder(self.__txtTitle, self.__txtTags)
        self.setTabOrder(self.__txtTags, self.__btnStar)
        self.setTabOrder(self.__btnStar, self.__btnPhoto)
        self.setTabOrder(self.__btnPhoto, self.__txtContent)
        self.setTabOrder(self.__txtContent, self.__btnSave)
        self.setTabOrder(self.__btnSave, self.__btnCancel)

        self.__confirmCallback = confirmCallback
        self.__cancelCallback = cancelCallback

        self.__note = None

    def edit(self, note):
        self.__note = note
        self.__txtTitle.setText(note.title)
        self.__btnStar.setStarred(note.starred)
        self.__btnPhoto.setPhoto(note.photo)
        self.__txtTags.setTags(note.tags)
        self.__txtContent.setPlainText(note.text)
        self.__txtTitle.setFocus()

    def isAllowedToChange(self):
        if self.__txtTitle.isModified() or self.__txtTags.isModified() or self.__btnStar.isModified() \
                or self.__btnPhoto.isModified() or self.__txtContent.document().isModified():
            # noinspection PyCallByClass
            choice = QMessageBox.warning(self, "Note changed", "Changes will be lost. Do you wish to continue?",
                                         buttons=QMessageBox.Ok | QMessageBox.Cancel, defaultButton=QMessageBox.Cancel)
            if choice != QMessageBox.Ok:
                return False
        return True

    def __onConfirm(self):
        note = self.__note.copy()
        note.lastModified = datetime.utcnow().replace(microsecond=0)
        note.title = self.__txtTitle.text().strip()
        note.tags = self.__txtTags.tags()
        note.starred = self.__btnStar.isStarred()
        note.photo = self.__btnPhoto.photo()
        note.text = self.__txtContent.toPlainText().lstrip()
        note.html = None
        try:
            self.__confirmCallback(note)
            self.__note = note
            self.__txtTitle.setModified(False)
            self.__txtTags.setModified(False)
            self.__btnStar.setModified(False)
            self.__btnPhoto.setModified(False)
            self.__txtContent.document().setModified(False)
        except ValidationError:
            self.__txtTitle.setFocus()

    def __onCancel(self):
        if self.isAllowedToChange():
            self.__cancelCallback()


class ViewerEditor(QStackedWidget):

    def __init__(self, parentWindow):
        QStackedWidget.__init__(self)
        self.__parentWindow = parentWindow
        self.__note = Note()

        self.__webNote = QWebView()
        webPage = self.__webNote.page()
        webPage.settings().setObjectCacheCapacities(0, 0, 0)
        webPage.action(QWebPage.Reload).setVisible(False)
        webPage.networkAccessManager().proxyAuthenticationRequired.connect(self.__onProxyAuthenticationRequired)
        self.updateProxy()
        # noinspection PyUnresolvedReferences
        self.__webNote.loadFinished.connect(self.updateHighlight)
        self.addWidget(self.__webNote)

        self.__editorNote = Editor(parentWindow, self.__onConfirm, self.__onCancel)
        self.addWidget(self.__editorNote)

    def noteUuid(self):
        return self.__note.uuid

    def view(self, note):
        self.__parentWindow.clearError()
        self.setCurrentIndex(0)
        self.__webNote.setHtml(note.html, rc.url())
        self.__note = note

    def edit(self, note=None):
        self.__parentWindow.clearError()
        if note:
            self.__note = note
        self.setCurrentIndex(1)
        self.__editorNote.edit(self.__note)

    def isAllowedToChange(self):
        return self.__editorNote.isAllowedToChange() if self.currentIndex() == 1 else True

    def updateProxy(self):
        config = self.__parentWindow.config()
        if config.getProxyHost():
            proxy = QNetworkProxy(QNetworkProxy.HttpProxy, config.getProxyHost(), config.getProxyPort())
        else:
            proxy = QNetworkProxy()
        self.__webNote.page().networkAccessManager().setProxy(proxy)

    def updateHighlight(self):
        if self.currentIndex() != 0:
            return
        self.__webNote.findText(None, QWebPage.HighlightAllOccurrences)
        highlight = self.__parentWindow.textFilter()
        if highlight:
            for word in filter(lambda w: len(w) > 0, highlight.split(" ")):
                self.__webNote.findText(word, QWebPage.HighlightAllOccurrences)

    def __onConfirm(self, note):
        parent = self.__parentWindow
        if not note.title:
            parent.showError("A title is required")
            raise ValidationError

        noteProvider = parent.noteProvider()
        if note.uuid:
            noteProvider.update(renderHtml(note))
        else:
            note.uuid = newUuid()
            note.createdOn = note.lastModified
            noteProvider.add(renderHtml(note))
        self.__note = note
        parent.reload(True, True)
        parent.showStatus("Note saved")

    def __onCancel(self):
        self.view(self.__note)

    # noinspection PyUnusedLocal
    def __onProxyAuthenticationRequired(self, proxy, authenticator):
        config = self.__parentWindow.config()
        if config.getProxyUser():
            authenticator.setUser(config.getProxyUser())
            authenticator.setPassword(config.getProxyPassword())


class ListWidget(QListWidget):

    def __init__(self, deleteCallback):
        QListWidget.__init__(self)
        self.__deleteCallback = deleteCallback

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.__deleteCallback()
            return
        QListWidget.keyPressEvent(self, event)


class ListItem(QListWidgetItem):

    def __init__(self, note, listWidget):
        if note.starred:
            QListWidgetItem.__init__(self, rc.icon("star-16x16.png"), note.title, listWidget)
        else:
            QListWidgetItem.__init__(self, note.title, listWidget)
        self.setToolTip("; ".join(note.tags))
        self.__note = note

    def note(self):
        return self.__note


class ListItemDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):
        option.decorationPosition = QStyleOptionViewItem.Right
        QStyledItemDelegate.paint(self, painter, option, index)


class Window(QWidget):

    tagsChanged = Signal(list)

    def __init__(self, appPath):
        QWidget.__init__(self)
        global rc
        rc = ResourceCache(normpath(appPath + "/resources"))

        self.__config = Config(appPath)
        self.__noteProvider = SqliteNoteProvider(normpath(appPath + "/resources/notes/notes.db"))
        self.__remoteNoteProvider = None
        self.__notes = []
        self.__tags = []

        self.setWindowTitle("Scroll, Quill & INK   " + version)
        self.setMinimumSize(400, 240)
        self.resize(800, 600)

        icon = QIcon()
        icon.addPixmap(rc.pixmap("sqink-16x16.png"))
        icon.addPixmap(rc.pixmap("sqink-32x32.png"))
        self.setWindowIcon(icon)

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 2)
        self.setLayout(layout)

        splitter = QSplitter()
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # noinspection PyCallByClass,PyTypeChecker
        splitter.setStyle(QStyleFactory.create("Cleanlooks"))
        layout.addWidget(splitter)

        self.__statusBar = QStatusBar()
        self.__statusBar.setSizeGripEnabled(False)
        layout.addWidget(self.__statusBar)

        self.__lblNotesCount = QLabel()
        self.__lblNotesCount.setStyleSheet("border:1px solid #b2dfdb; border-radius:0.5em; background-color:#b2dfdb;" +\
                                           " padding:0 0.5em;")
        self.__statusBar.addPermanentWidget(self.__lblNotesCount)

        self.__lblError = QLabel()
        self.__lblError.setStyleSheet("border-radius:0.5em; background-color:#f36c60; padding:0 0.5em;")
        self.__lblError.setVisible(False)
        self.__statusBar.addWidget(self.__lblError)

        panelA = QWidget()
        splitter.addWidget(panelA)
        layoutA = QGridLayout()
        layoutA.setContentsMargins(0, 0, 0, 0)
        panelA.setLayout(layoutA)

        barButtons = QWidget()
        layoutButtons = QHBoxLayout()
        layoutButtons.setContentsMargins(0, 0, 0, 0)
        barButtons.setLayout(layoutButtons)
        layoutA.addWidget(barButtons, 0, 0, 1, 2)

        btnNew = QPushButton()
        btnNew.setIcon(rc.icon("note-new-16x16.png"))
        btnNew.setToolTip("New note (CTRL + N)")
        # noinspection PyUnresolvedReferences
        btnNew.clicked.connect(self.__onNewNoteClicked)
        btnNew.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_N))
        layoutButtons.addWidget(btnNew)

        self.__btnEdit = QPushButton()
        self.__btnEdit.setIcon(rc.icon("note-edit-16x16.png"))
        self.__btnEdit.setToolTip("Edit note (CTRL + E)")
        # noinspection PyUnresolvedReferences
        self.__btnEdit.clicked.connect(self.__onEditNoteClicked)
        self.__btnEdit.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_E))
        layoutButtons.addWidget(self.__btnEdit)

        self.__btnDelete = QPushButton()
        self.__btnDelete.setIcon(rc.icon("note-delete-16x16.png"))
        self.__btnDelete.setToolTip("Delete note (CTRL + L)")
        # noinspection PyUnresolvedReferences
        self.__btnDelete.clicked.connect(self.__onDeleteNoteClicked)
        self.__btnDelete.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_L))
        layoutButtons.addWidget(self.__btnDelete)

        layoutButtons.addStretch(1)

        self.__btnSync = QPushButton()
        self.__btnSync.setIcon(rc.icon("sync-16x16.png"))
        self.__btnSync.setToolTip("Sync (CTRL + I)")
        # noinspection PyUnresolvedReferences
        self.__btnSync.clicked.connect(self.__onSyncClicked)
        self.__btnSync.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_I))
        layoutButtons.addWidget(self.__btnSync)

        btnConfig = QPushButton()
        btnConfig.setIcon(rc.icon("preferences-16x16.png"))
        btnConfig.setToolTip("Preferences")
        # noinspection PyUnresolvedReferences
        btnConfig.clicked.connect(self.__onPreferencesClicked)
        layoutButtons.addWidget(btnConfig)

        lblSearch = QLabel()
        lblSearch.setPixmap(rc.pixmap("search-16x16.png"))
        lblSearch.setToolTip("Find (CTRL + F)")
        layoutA.addWidget(lblSearch, 1, 0)

        self.__txtSearch = QLineEdit()
        self.__txtSearch.setValidator(QRegExpValidator(QRegExp("[A-ZÁÉÍÓÚÜÑa-záéíóúüñ0-9 @:/#&=\.\-\?\\\\]+")))
        # noinspection PyUnresolvedReferences
        self.__txtSearch.textEdited.connect(self.__onSearchEdited)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_F), self.__txtSearch, self.__txtSearch.setFocus)
        layoutA.addWidget(self.__txtSearch, 1, 1)

        lblTag = QLabel()
        lblTag.setPixmap(rc.pixmap("tag-16x16.png"))
        lblTag.setToolTip("Filter by tag (CTRL + T)")
        layoutA.addWidget(lblTag, 2, 0)

        self.__cmbTag = QComboBox()
        # noinspection PyUnresolvedReferences
        self.__cmbTag.activated.connect(self.__onTagFilterSelectionChanged)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_T), self.__cmbTag, self.__onTagFilterShortcutPressed)
        layoutA.addWidget(self.__cmbTag, 2, 1)

        self.__lstNotes = ListWidget(self.__onDeleteNoteClicked)
        self.__lstNotes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.__lstNotes.setItemDelegate(ListItemDelegate())
        # noinspection PyUnresolvedReferences
        self.__lstNotes.itemSelectionChanged.connect(self.__onNoteSelectionChanged)
        layoutA.addWidget(self.__lstNotes, 3, 0, 1, 2)

        self.__viewerEditor = ViewerEditor(self)
        splitter.addWidget(self.__viewerEditor)

        self.configureSync()
        self.reload()
        self.__txtSearch.setFocus()

    def closeEvent(self, event):
        self.__noteProvider.close()
        QWidget.closeEvent(self, event)

    def config(self):
        return self.__config

    def noteProvider(self):
        return self.__noteProvider

    def remoteNoteProvider(self):
        return self.__remoteNoteProvider

    def textFilter(self):
        return self.__txtSearch.text().strip()

    def configureSync(self):
        config = self.config()
        if config.isDropboxEnabled():
            self.__remoteNoteProvider = DropboxNoteProvider(config.getDropboxToken(), config.getDropboxFolder(),
                                                            config.getProxyHost(), config.getProxyPort(),
                                                            config.getProxyUser(), config.getProxyPassword())
            self.__btnSync.setDisabled(False)
        elif config.isGoogleDriveEnabled():
            self.__remoteNoteProvider = GoogleDriveNoteProvider(config.getGoogleDriveToken(), config.getProxyHost(),
                                                                config.getProxyPort(), config.getProxyUser(),
                                                                config.getProxyPassword())
            self.__btnSync.setDisabled(False)
        else:
            self.__remoteNoteProvider = None
            self.__btnSync.setDisabled(True)

    def disableSync(self):
        config = self.config()
        if config.isDropboxEnabled():
            config.setDropboxEnabled(False)
            config.setDropboxToken(None)
        else:
            config.setGoogleDriveEnabled(False)
            config.setGoogleDriveToken(None)
        config.save()
        self.configureSync()

    def updateProxy(self):
        self.__viewerEditor.updateProxy()

    def showStatus(self, message, seconds=5, immediate=False):
        self.clearError()
        self.__statusBar.showMessage(message, timeout=seconds * 1000)
        if immediate:
            self.__statusBar.repaint()

    def showError(self, message):
        self.__statusBar.clearMessage()
        self.__lblError.setText(message)
        self.__lblError.setVisible(True)

    def clearError(self):
        self.__lblError.setVisible(False)

    def reload(self, selectNoteOnViewerEditor=False, skipViewerEditor=False):
        self.__notes = sorted(self.noteProvider().list(), key=lambda n: n.title.lower())
        self.__tags = listTags(self.__notes)
        self.__refreshTagCombo()
        self.__refreshNoteList(selectNoteOnViewerEditor)
        self.__lblNotesCount.setText("%d notes" % len(self.__notes))

        if not skipViewerEditor:
            self.__refreshNoteViewerEditor()

        self.__refreshNoteButtons()
        # noinspection PyUnresolvedReferences
        self.tagsChanged.emit(self.__tags)

    def __setSelectedItem(self, uuid=None):
        self.__lstNotes.setDisabled(True)

        if self.__selectedItem():
            self.__selectedItem().setSelected(False)

        if uuid:
            for i in range(self.__lstNotes.count()):
                item = self.__lstNotes.item(i)
                if item.note().uuid == uuid:
                    item.setSelected(True)
                    break

        self.__lstNotes.setDisabled(False)

    def __selectedItem(self):
        selectedItems = self.__lstNotes.selectedItems()
        return selectedItems[0] if selectedItems else None

    def __refreshNoteButtons(self):
        disableButtons = not self.__viewerEditor.noteUuid()
        self.__btnEdit.setDisabled(disableButtons)
        self.__btnDelete.setDisabled(disableButtons)

    def __refreshTagCombo(self):
        tags = self.__tags[:]
        tags.insert(0, "")

        currentTag = self.__cmbTag.currentText()
        self.__cmbTag.clear()
        self.__cmbTag.addItems(tags)

        if currentTag and currentTag in tags:
            self.__cmbTag.setCurrentIndex(tags.index(currentTag))

    def __refreshNoteList(self, selectNoteOnViewerEditor=False):
        notes = self.__notes

        searchText = self.textFilter()
        if searchText:
            uuids = self.noteProvider().search(searchText)
            notes = list(filter(lambda n: n.uuid in uuids, notes))

        currentTag = self.__cmbTag.currentText()
        if currentTag:
            notes = list(filter(lambda n: n.hasTag(currentTag), notes))

        selectUuid = None
        if selectNoteOnViewerEditor:
            selectUuid = self.__viewerEditor.noteUuid()
        elif self.__selectedItem():
            selectUuid = self.__selectedItem().note().uuid
        elif len(notes) > 0:
            selectUuid = notes[0].uuid

        self.__lstNotes.setDisabled(True)
        self.__lstNotes.clear()
        selectedNoteItem = None
        for note in notes:
            item = ListItem(note, self.__lstNotes)
            if selectUuid == note.uuid:
                item.setSelected(True)
                selectedNoteItem = item
        if selectedNoteItem:
            self.__lstNotes.setCurrentItem(selectedNoteItem)
        self.__lstNotes.setDisabled(False)

    def __refreshNoteViewerEditor(self):
        if self.__selectedItem():
            note = self.noteProvider().get(self.__selectedItem().note().uuid)
        else:
            note = renderHtml(Note())
        self.__viewerEditor.view(note)

    def __onNewNoteClicked(self):
        if self.__viewerEditor.isAllowedToChange():
            self.__lstNotes.setCurrentItem(None)
            self.__viewerEditor.edit(renderHtml(Note()))
            self.__refreshNoteButtons()

    def __onEditNoteClicked(self):
        if self.__viewerEditor.isAllowedToChange():
            self.__viewerEditor.edit()

    def __onDeleteNoteClicked(self):
        # noinspection PyCallByClass
        choice = QMessageBox.question(self, "Delete note", "Are you ABSOLUTELY sure?",
                                      buttons=QMessageBox.Yes | QMessageBox.No, defaultButton=QMessageBox.No)
        if choice != QMessageBox.Yes:
            return

        note = Note(self.__viewerEditor.noteUuid(), datetime.utcnow().replace(microsecond=0))
        self.noteProvider().remove(note)
        self.__setSelectedItem()

        self.reload()
        self.showStatus("Note deleted")
        self.__lstNotes.setFocus()

    def __onSyncClicked(self):
        if self.remoteNoteProvider() and self.__viewerEditor.isAllowedToChange():
            self.showStatus("Starting synchronization, please wait...", immediate=True)
            try:
                Synchronizer(self.noteProvider(), self.remoteNoteProvider()).sync()
                self.reload(True)
                self.showStatus("Synchronization finished")
            except TokenExpiredError:
                self.showError("Authentication expired. Synchronization account must be configured again")
                self.disableSync()
            except AConnectionError:
                self.showError("Failed to connect to server")
            except InvalidProxyError:
                self.showError("Proxy settings are invalid")

    def __onPreferencesClicked(self):
        Preferences(self).show()

    def __onSearchEdited(self):
        self.__refreshNoteList(True)
        self.__viewerEditor.updateHighlight()

    def __onTagFilterSelectionChanged(self):
        self.__refreshNoteList(True)

    def __onTagFilterShortcutPressed(self):
        self.__cmbTag.setFocus()
        self.__cmbTag.showPopup()

    def __onNoteSelectionChanged(self):
        if self.__lstNotes.isEnabled() and self.__selectedItem():
            if self.__viewerEditor.isAllowedToChange():
                note = self.noteProvider().get(self.__selectedItem().note().uuid)
                self.__viewerEditor.view(note)
                self.__refreshNoteButtons()
            else:
                self.__setSelectedItem(self.__viewerEditor.noteUuid())


class Preferences(QDialog):

    def __init__(self, parentWindow):
        QDialog.__init__(self, parentWindow, Qt.WA_DeleteOnClose)
        config = parentWindow.config()

        self.setWindowTitle("Preferences")
        self.setModal(True)
        layout = QVBoxLayout()
        self.setLayout(layout)

        grpProxy = QGroupBox("Proxy")
        layoutProxy = QGridLayout()
        grpProxy.setLayout(layoutProxy)
        layout.addWidget(grpProxy)

        layoutProxy.addWidget(QLabel("Host:"), 0, 0)
        self.__txtHost = QLineEdit()
        self.__txtHost.setFixedWidth(130)
        self.__txtHost.setText(config.getProxyHost())
        layoutProxy.addWidget(self.__txtHost, 0, 1)
        layoutProxy.addWidget(QLabel("Port:"), 0, 2)
        self.__txtPort = QLineEdit()
        self.__txtPort.setFixedWidth(50)
        self.__txtPort.setValidator(QIntValidator(1, 65535))
        if config.getProxyPort():
            self.__txtPort.setText(str(config.getProxyPort()))
        layoutProxy.addWidget(self.__txtPort, 0, 3)

        layoutProxy.addWidget(QLabel("User:"), 1, 0)
        self.__txtUser = QLineEdit()
        self.__txtUser.setFixedWidth(130)
        self.__txtUser.setText(config.getProxyUser())
        layoutProxy.addWidget(self.__txtUser, 1, 1)
        layoutProxy.addWidget(QLabel("Password:"), 1, 2)
        self.__txtPassword = QLineEdit()
        self.__txtPassword.setEchoMode(QLineEdit.Password)
        self.__txtPassword.setFixedWidth(50)
        self.__txtPassword.setText(config.getProxyPassword())
        layoutProxy.addWidget(self.__txtPassword, 1, 3)

        grpDropbox = QGroupBox("Dropbox")
        layoutDropbox = QGridLayout()
        grpDropbox.setLayout(layoutDropbox)
        layout.addWidget(grpDropbox)

        self.__chkDropbox = QCheckBox("Use Dropbox to synchronize notes.")
        self.__chkDropbox.setCheckState(Qt.Checked if config.isDropboxEnabled() else Qt.Unchecked)
        # noinspection PyUnresolvedReferences
        self.__chkDropbox.stateChanged.connect(self.__onDropboxChanged)
        layoutDropbox.addWidget(self.__chkDropbox, 0, 0, 1, 3)

        layoutDropbox.addWidget(QLabel("Folder:"), 1, 0)
        self.__cmbFolder = QComboBox()
        self.__cmbFolder.addItems(["Narrate", "Day One", "Custom"])
        # noinspection PyUnresolvedReferences
        self.__cmbFolder.activated.connect(self.__onFolderChanged)
        layoutDropbox.addWidget(self.__cmbFolder, 1, 1)
        self.__txtFolder = QLineEdit()
        layoutDropbox.addWidget(self.__txtFolder, 1, 2)

        grpGDrive = QGroupBox("Google Drive")
        layoutGDrive = QGridLayout()
        grpGDrive.setLayout(layoutGDrive)
        layout.addWidget(grpGDrive)

        self.__chkGDrive = QCheckBox("Use Google Drive to synchronize notes.")
        self.__chkGDrive.setCheckState(Qt.Checked if config.isGoogleDriveEnabled() else Qt.Unchecked)
        # noinspection PyUnresolvedReferences
        self.__chkGDrive.stateChanged.connect(self.__onGoogleDriveChanged)
        layoutGDrive.addWidget(self.__chkGDrive, 0, 0)

        layoutButtons = QHBoxLayout()
        layout.addLayout(layoutButtons)

        btnAccept = QPushButton("OK")
        # noinspection PyUnresolvedReferences
        btnAccept.clicked.connect(self.__onAcceptClicked)
        layoutButtons.addWidget(btnAccept)

        btnCancel = QPushButton("Cancel")
        # noinspection PyUnresolvedReferences
        btnCancel.clicked.connect(self.close)
        layoutButtons.addWidget(btnCancel)

        self.__onDropboxChanged()
        self.__initFolder(config.getDropboxFolder())

    def __initFolder(self, folder):
        if folder == SyncFolder.Narrate:
            self.__cmbFolder.setCurrentIndex(0)
            self.__onFolderChanged(0)
        elif folder == SyncFolder.DayOne:
            self.__cmbFolder.setCurrentIndex(1)
            self.__onFolderChanged(1)
        else:
            self.__cmbFolder.setCurrentIndex(2)
            self.__onFolderChanged(2)
            self.__txtFolder.setText(folder)

    def __validate(self):
        config = self.parentWidget().config()
        proxyHost = self.__txtHost.text().strip()
        proxyPort = self.__txtPort.text().strip()
        proxyUser = self.__txtUser.text().strip()
        proxyPassword = self.__txtPassword.text()
        dropboxEnabled = self.__chkDropbox.isChecked()
        dropboxFolder = self.__txtFolder.text().lstrip().rstrip(" \t/")
        dropboxToken = config.getDropboxToken()
        googleDriveEnabled = self.__chkGDrive.isChecked()
        googleDriveToken = config.getGoogleDriveToken()

        if dropboxEnabled:
            if not dropboxFolder or dropboxFolder[0] != "/":
                return self.__criticalMessage("Preferences Error", "Dropbox folder is not valid.", self.__txtFolder)
            if not dropboxToken:
                authorizator = DropboxAuthorizator(proxyHost, int(proxyPort) if proxyPort else None, proxyUser,
                                                   proxyPassword)
                msg = "To link your Dropbox account, visit this address and authorize the application. " +\
                      "Press [OK] when finished."
                temp, accept = self.__inputMessage("Dropbox Authorization", msg, authorizator.authorizationUrl())
                if not accept:
                    return False
                msg = "Please enter the authorization code given by Dropbox:"
                code, accept = self.__inputMessage("Dropbox Authorization", msg)
                if not accept:
                    return False
                try:
                    dropboxToken = authorizator.authorize(code)
                except InvalidProxyError:
                    return self.__criticalMessage("Dropbox Error", "Proxy settings are invalid.", self.__txtHost)
                except AConnectionError:
                    return self.__criticalMessage("Dropbox Error", "Connection failed.", self.__chkDropbox)
                except TokenExpiredError:
                    return self.__criticalMessage("Dropbox Error", "Invalid token.", self.__chkDropbox)
                if not authorizator.checkFolder(dropboxToken, dropboxFolder):
                    return self.__criticalMessage("Dropbox Error", "Folder could not be created.", self.__cmbFolder)
        elif googleDriveEnabled:
            if not googleDriveToken:
                proxyPortInt = int(proxyPort) if proxyPort else None
                authorizator = GoogleDriveAuthorizator(proxyHost, proxyPortInt, proxyUser, proxyPassword)
                msg = "To link your Google Drive account, visit this address and authorize the application. " +\
                      "Press [OK] when finished."
                temp, accept = self.__inputMessage("Google Drive Authorization", msg, authorizator.authorizationUrl())
                if not accept:
                    return False
                msg = "Please enter the authorization code given by Google Drive:"
                code, accept = self.__inputMessage("Google Drive Authorization", msg)
                if not accept:
                    return False
                try:
                    googleDriveToken = authorizator.authorize(code)
                except InvalidProxyError:
                    return self.__criticalMessage("Google Drive Error", "Proxy settings are invalid.", self.__txtHost)
                except AConnectionError:
                    return self.__criticalMessage("Google Drive Error", "Connection failed.", self.__chkGDrive)
                except TokenExpiredError:
                    return self.__criticalMessage("Google Drive Error", "Invalid token.", self.__chkGDrive)

        config.setProxyHost(proxyHost)
        config.setProxyPort(proxyPort)
        config.setProxyUser(proxyUser)
        config.setProxyPassword(proxyPassword)
        config.setDropboxEnabled(dropboxEnabled)
        config.setDropboxFolder(dropboxFolder)
        config.setDropboxToken(dropboxToken)
        config.setGoogleDriveEnabled(googleDriveEnabled)
        config.setGoogleDriveToken(googleDriveToken)
        return True

    def __criticalMessage(self, title, message, widget):
        # noinspection PyCallByClass
        QMessageBox.critical(self, title, message, buttons=QMessageBox.Ok)
        widget.setFocus()
        return False

    def __inputMessage(self, title, message, value=""):
        # noinspection PyCallByClass
        return QInputDialog.getText(self, title, message, text=value)

    # noinspection PyUnusedLocal
    def __onDropboxChanged(self, arg=None):
        if self.__chkDropbox.isChecked() and self.__chkGDrive.isChecked():
            self.__chkGDrive.setChecked(False)

    def __onFolderChanged(self, index):
        if index == 0:
            self.__txtFolder.setText(SyncFolder.Narrate)
            self.__txtFolder.setReadOnly(True)
        elif index == 1:
            self.__txtFolder.setText(SyncFolder.DayOne)
            self.__txtFolder.setReadOnly(True)
        else:
            self.__txtFolder.setText("")
            self.__txtFolder.setReadOnly(False)

    # noinspection PyUnusedLocal
    def __onGoogleDriveChanged(self, arg):
        if self.__chkDropbox.isChecked() and self.__chkGDrive.isChecked():
            self.__chkDropbox.setChecked(False)

    def __onAcceptClicked(self):
        if not self.__validate():
            return
        parent = self.parentWidget()
        parent.config().save()
        parent.configureSync()
        parent.updateProxy()
        parent.showStatus("Preferences saved")
        self.close()
