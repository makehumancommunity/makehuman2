"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    classes:
    * FileCache

    The sqllite database consists of 2 tables

    table 'filecache':
    name, uuid, path, folder, obj_file, thumbfile, author, tags

    table userinformation:
    uuid, tags

    the index to connect is uuid. User-information can be saved
"""

import sqlite3
import os
import json

class FileCache:
    """
    constructor of FileCache, get time of file

   :param programInfo env: pointer to user-environment
   :param str name: filename of the database
    """
    def __init__(self, env, name: str):
        self.env = env
        self.con = sqlite3.connect(name)
        self.cur = self.con.cursor()
        self.name = name
        self.time = int(os.stat(name).st_mtime)
        self.env.logTime(self.time, "last change repository: " + name)

    def createCache(self, latest: int, subdir=None, force=False):
        """
        creates filecache and userinformation if non existent
        deletes complete filecache entries in case a file is newer
        or filecache entries when subdir is mentioned

        :param int latest: timestamp as integer
        :param str subdir: optional name of a subdirectory
        :param force bool: recreate cache always
        :return: bool, true if changed
        """
        res = self.cur.execute("SELECT name FROM sqlite_master WHERE name='userinformation'")
        if res.fetchone() is None:
            self.env.logLine(8, "Need to create user table")
            self.cur.execute("CREATE TABLE userinformation(uuid, tags)")

        res = self.cur.execute("SELECT name FROM sqlite_master WHERE name='filecache'")
        if res.fetchone() is None:
            self.env.logLine(8, "Need to create filecache table")
            self.cur.execute("CREATE TABLE filecache(name, uuid, path, folder, obj_file, thumbfile, author, tags)")
            return(True)

        if subdir is None:
            if latest > self.time or force:
                self.env.logLine(8, "Delete current filecache completely")
                self.cur.execute("DELETE FROM filecache")
                return (True)
            else:
                return(False)
        else:
            self.env.logLine(8, "Delete folder '" + subdir + "' from filecache")
            self.cur.execute("DELETE FROM filecache where folder = ?", (subdir,))
            self.con.commit()
            return (True)

    def getEditParamInfo(self, uuid):
        return(self.cur.execute("SELECT tags FROM filecache where uuid = ?", (uuid,)))

    def getEditParamUser(self, uuid):
        return(self.cur.execute("SELECT tags FROM userinformation where uuid = ?", (uuid,)))

    def deleteParamUser(self, uuid):
        self.cur.execute("delete FROM userinformation where uuid = ?", (uuid,))
        self.con.commit()

    def insertParamUser(self, uuid, tags):
        self.deleteParamUser(uuid)
        self.cur.execute("insert into userinformation values(?, ?)", (uuid, tags))
        self.con.commit()

    def updateParamInfo(self, uuid, thumbfile):
        self.cur.execute("update filecache set thumbfile = ?  where uuid = ?", (thumbfile, uuid))
        self.con.commit()

    def listCache(self):
        return(self.cur.execute("SELECT * FROM filecache ORDER BY name COLLATE NOCASE ASC"))

    def listUserInfo(self):
        return(self.cur.execute("SELECT * FROM userinformation"))

    def listCacheMatch(self):
        corrected = self.listUserInfo()
        match = {}
        for row in corrected:
            match[row[0]] = row[1]
        rows = self.listCache()
        return (rows, match)

    def insertCache(self, data):
        self.cur.executemany("insert into filecache values(?, ?, ?, ?, ?, ?, ?, ?)", data)
        self.con.commit()
        self.time = int(os.stat(self.name).st_mtime)

    def exportUserInfo(self, filename):
        lines = self.listUserInfo()
        json_db = {}
        for line in lines:
            key = line[0].replace('"', '')
            value = line[1].replace('"', '')
            json_db[key] = value
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_db, f, ensure_ascii=False, indent=4)
        except OSError as error:
            self.env.last_error = str(error)
            return False
        return True

    def importUserInfo(self, filename):
        json = self.env.readJSON(filename)
        if json is None:
            return False
        for key in json:
            if not isinstance(key, str):
                self.env.last_error = "Bad file, UUID must be string"
                return False
            if not isinstance(json[key], str):
                self.env.last_error = "Bad file, tags must be string"
                return False

        self.env.logLine(8, "Delete user information completely")
        self.cur.execute("DELETE FROM userinformation")
        for key in json:
            self.insertParamUser(key, json[key])
        return True
        
    def __del__(self):
        self.cur.close()

