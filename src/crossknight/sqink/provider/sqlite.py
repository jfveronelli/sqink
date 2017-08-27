# coding:utf-8
from crossknight.sqink.domain import Note
from crossknight.sqink.domain import NoteStatus
from crossknight.sqink.provider import LocalNoteProvider
from crossknight.sqink.provider.filesystem import savePhoto
from os import listdir
from os import remove
from os.path import dirname
from os.path import isfile
from sqlite3 import connect
from sqlite3 import PARSE_DECLTYPES


class SqliteNoteProvider(LocalNoteProvider):

    def __init__(self, dbPath):
        self.__connection = connect(dbPath, detect_types=PARSE_DECLTYPES)
        with self.__connection:
            self.__connection.execute("CREATE TABLE IF NOT EXISTS Note (" +
                                      "uuid TEXT PRIMARY KEY, " +
                                      "lastModified TIMESTAMP NOT NULL, " +
                                      "active INTEGER NOT NULL, " +
                                      "createdOn TIMESTAMP, " +
                                      "title TEXT, " +
                                      "tags TEXT, " +
                                      "starred INTEGER, " +
                                      "text TEXT, " +
                                      "html TEXT);")
        self.__photosPath = dirname(dbPath)

    def list(self):
        cursor = self.__connection.cursor()
        cursor.execute("SELECT uuid, lastModified, createdOn, title, tags, starred FROM Note WHERE active = 1;")
        return [Note(row[0], row[1], row[2], row[3], self.__inflate(row[4]), bool(row[5])) for row in cursor]

    def search(self, alphanum):
        tokens = list(filter(lambda t: len(t) > 0, alphanum.split(" ")))
        query = "SELECT uuid FROM Note WHERE (title LIKE ? OR tags LIKE ? OR text LIKE ?)"
        token = self.__likenize(tokens[0])
        params = [token, token, token]

        for token in tokens[1:]:
            query += " AND (title LIKE ? OR tags LIKE ? OR text LIKE ?)"
            token = self.__likenize(token)
            params.extend([token, token, token])

        cursor = self.__connection.cursor()
        cursor.execute(query, tuple(params))
        return [row[0] for row in cursor]

    def sync(self):
        noteStatuses = {}
        for row in self.__connection.execute("SELECT uuid, lastModified, active FROM Note;"):
            noteStatuses[row[0]] = NoteStatus(row[0], row[1], not row[2])
        for name in listdir(self.__photosPath):
            if name.endswith(".jpg"):
                name = name[:-4]
                if name in noteStatuses:
                    noteStatuses[name].hasPhoto = True
        return noteStatuses

    def get(self, uuid):
        query = "SELECT uuid, lastModified, createdOn, title, tags, starred, text, html FROM Note WHERE active = 1 " +\
                "AND uuid = ?;"
        cursor = self.__connection.cursor()
        cursor.execute(query, (uuid,))
        row = cursor.fetchone()
        note = Note(row[0], row[1], row[2], row[3], self.__inflate(row[4]), bool(row[5]), row[6], row[7])

        if isfile(self.__photoPath(uuid)):
            with open(self.__photoPath(uuid), "rb") as file:
                note.photo = file.read()

        return note

    def add(self, note):
        uuid = note.uuid
        tags = self.__flatten(note.tags)
        starred = 1 if note.starred else 0
        params = (uuid, note.lastModified, note.createdOn, note.title, tags, starred, note.text, note.html)
        with self.__connection:
            self.__connection.execute("DELETE FROM Note WHERE uuid = ? AND active = 0;", (uuid,))
            self.__connection.execute("INSERT INTO Note VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?);", params)
        savePhoto(note, self.__photoPath(uuid))

    def update(self, note):
        uuid = note.uuid
        tags = self.__flatten(note.tags)
        starred = 1 if note.starred else 0
        query = "UPDATE Note SET lastModified = ?, createdOn = ?, title = ?, tags = ?, starred = ?, text = ?, " +\
                "html = ? WHERE uuid = ? AND active = 1;"
        params = (note.lastModified, note.createdOn, note.title, tags, starred, note.text, note.html, uuid)
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        if cursor.rowcount != 1:
            self.__connection.rollback()
            raise RuntimeError("Note[uuid=%s] does not exist" % uuid)
        self.__connection.commit()

        photoPath = self.__photoPath(uuid)
        savePhoto(note, photoPath)

    def remove(self, note):
        uuid = note.uuid
        with self.__connection:
            self.__connection.execute("DELETE FROM Note WHERE uuid = ?;", (uuid,))
            self.__connection.execute("INSERT INTO Note VALUES (?, ?, 0, NULL, NULL, NULL, NULL, NULL, NULL);",
                                      (uuid, note.lastModified))

        photoPath = self.__photoPath(uuid)
        if isfile(photoPath):
            remove(photoPath)

    @staticmethod
    def __flatten(tags):
        if not tags:
            return None
        txt = tags[0]
        for i in range(1, len(tags)):
            txt += "\n" + tags[i]
        return txt

    @staticmethod
    def __inflate(tags):
        return tags.split("\n") if tags else []

    @staticmethod
    def __likenize(text):
        return "%" + text + "%"

    def __photoPath(self, uuid):
        return self.__photosPath + "/" + uuid + ".jpg"

    def close(self):
        self.__connection.close()
