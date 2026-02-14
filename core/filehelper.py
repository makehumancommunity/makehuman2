"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * FileHelper
"""
import os
import io
import numpy as np
from zipfile import ZipFile

class FileHelper():
    def __init__(self, env):
        self.env = env

    def hasThumb(self, path):
        filename, extension = os.path.splitext(path)
        thumbfile = filename + ".thumb"
        if os.path.isfile(thumbfile):
            return thumbfile
        return None

    def getCacheDataMHCLO(self, path, folder):
        """
        scan MHCLO file

        :param path: path name
        :param folder: folder as category
        :return: data entry for fileCache or None in case of error
        """

        with open(path, 'r') as fp:
            thumbfile = self.hasThumb(path)
            uuid = 0
            name = ""
            obj_file = None
            author = "unknown"
            tags = []
            for line in fp:
                words = line.split()
                if len(words) < 2:
                    continue
                if words[0].isnumeric():
                    break

                if words[0] == "name":          # always last word, one word
                    name = words[1]
                elif words[0] == "uuid":        # always last word, one word
                    uuid = words[1]
                elif words[0] == "obj_file":        # always last word, one word
                    obj_file = words[1]
                elif "author" in line:      # part of the comment, can be author
                    if words[1].startswith("author"):
                        author = " ".join(words[2:])

                elif "tag" in line:         # allow tags with blanks
                    tags.append(" ".join(words[1:]).encode('ascii', 'ignore').lower().decode("utf-8"))
            mtags = "|".join(tags)
            return [name, uuid, path, folder, obj_file, thumbfile, author, mtags]

        return None

    def getCacheDataMHBIN(self, path, folder):
        """
        test of scanner of an mhbin file (without reading complete file)
        """
        with ZipFile(path) as myzip:
            m = myzip.read("header.npy")
            m = io.BytesIO(m)
            with np.load(path) as npzfile:
                tags = []
                if 'header'  in npzfile:
                    header = list(npzfile['header'][0])
                    print (header)
                    thumbfile = self.hasThumb(path)
                    name = header[0].decode("utf-8")
                    uuid = "mhbin_" + name
                    mtags = "|".join(tags)
                    author = "unknown"
                    print (name, uuid, path, folder, None, thumbfile, author, mtags)

    def getCacheDataBVH(self, path, folder):
        """
        scan meta file for BVH, uuid is created from name
        also works without meta file

        :param path: path name
        :param folder: folder as category
        :return: data entry for fileCache always
        """
        filename, extension = os.path.splitext(path)
        metafile = filename + ".meta"
        name = os.path.basename(filename)
        uuid = "bvh_" + name
        author = "unknown"
        thumbfile = self.hasThumb(path)
        tags = []
        if os.path.isfile(metafile):
            with open(metafile, 'r') as fp:
                for line in fp:
                    words = line.split()
                    if len(words) < 2:
                        continue
                    if words[0] == "name":
                        name = "_".join(words[1:]).encode('ascii', 'ignore').lower().decode("utf-8")
                    elif words[0] == "tag":
                        tags.append(" ".join(words[1:]).encode('ascii', 'ignore').lower().decode("utf-8"))
                    elif words[0] == "author":
                        author = " ".join(words[1:]).encode('ascii', 'ignore').lower().decode("utf-8")

        mtags = "|".join(tags)
        return [name, uuid, path, folder, None, thumbfile, author, mtags]


    def getCacheDataJSON(self, path, folder):
        """
        scan json data files for skeleton or poses

        :param path: path name
        :param folder: folder as category
        :return: data entry for fileCache or None in case of error
        """
        json = self.env.readJSON(path)
        if json is None:
            self.logLine (1, "JSON error " + self.last_error)
            return None
        else:
            thumbfile = self.hasThumb(path)
            filename, extension = os.path.splitext(path)
            name = json["name"] if "name" in json else filename
            uuid = extension[3:] + "_"+name
            author = json["author"] if "author" in json else "unknown"
            mtags = "|".join(json["tags"]).encode('ascii', 'ignore').lower().decode("utf-8") if "tags" in json else ""
            return [name, uuid, path, folder, None, thumbfile, author, mtags]


    def getCacheDataMHM(self, path, folder):
        """
        scan MHM files for models

        :param path: path name
        :param folder: folder as category
        :return: data entry for fileCache or None in case of error
        """

        with open(path, 'r') as fp:
            thumbfile = self.hasThumb(path)
            uuid = 0
            name = None
            author = "unknown"
            tags = []
            for line in fp:
                if line.startswith("modifier"):
                    break
                words = line.split()
                if len(words) < 2:
                    continue

                if words[0] == "name":          # last words joined
                    name = " ".join(words[1:])
                if words[0] == "author":        # last words joined
                    author = " ".join(words[1:])
                elif words[0] == "uuid":        # always second word
                    uuid = words[1]
                elif "tags" in line:
                    tags =" ".join(words[1:]).split(";")

            if name is None:                    # worst case take filename for name
                name = os.path.basename(os.path.splitext(path)[0])

            mtags = "|".join(tags)
            return [name, uuid, path, folder, None, thumbfile, author, mtags]

        return None
