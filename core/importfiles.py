"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * UserEnvironment
    * AssetPack
    * TargetASCII
"""

from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import URLError
from zipfile import ZipFile
from datetime import datetime
import numpy as np
import os
import re
import sys
import shutil
import platform
import tempfile

class UserEnvironment():
    def __init__(self):
        self.osindex= -1

    def GetPlatform(self):
        p =sys.platform
        if p.startswith('win'):
            ostype = "Windows"
            osindex= 0
            platform_version = " ".join(platform.win32_ver())
        elif p.startswith('darwin'):
            ostype = "MacOS"
            osindex= 2
            platform_version = platform.mac_ver()[0]
        else:
            ostype = "Linux"
            osindex= 1
            try:
                platform_version = ' '.join(platform.linux_distribution())
            except AttributeError:
                try:
                    import distro
                    platform_version = ' '.join(distro.linux_distribution())
                except ImportError:
                    platform_version = "Unknown"
        self.osindex = osindex
        return (p, osindex, ostype, platform_version)

    def GetHardware(self):
        return(platform.machine(), platform.processor(), platform.uname()[2])

    def GetUserConfigFilenames(self, osindex=None, create=False):
        """
        gets of creates user config filenames

        :param int osindex: if None self.osindex is used, otherwise 0-2
        :param bool create: should folder be created?

        :return: name of conf-file and session-file - or None when mkdir fails
        """

        # generic subfolder in makehuman2, for apple it should be Makehuman2
        #
        subfolder = "makehuman2"
        if osindex is None:
            osindex = self.osindex
        if osindex == 0:
            path = os.getenv('LOCALAPPDATA', '')
        elif osindex == 1:
            path = os.path.expanduser('~/.config')
        else:
            path = os.path.expanduser('~/Library/Application Support')
            subfolder = "Makehuman2"

        #
        # create of subfolder
        folder = os.path.join(path, subfolder)
        if create is True:
            if not os.path.isdir(folder):
                try:
                    os.mkdir(folder)
                except:
                    return (None, folder)

        return (os.path.join(folder, 'makehuman2.conf'), os.path.join(folder, 'makehuman2_session.conf'))
        

class AssetPack():
    def __init__(self):
        self.unzipdir = None
        self.acceptedfiles = ["obj", "mhclo", "mhmat", "thumb", "mhw_file", "diffuse", "normals",
                "mhpose", "meta", "bvh", "mhskel", "mhw", "obj_file", "file", "mhm" ]

    def titleToFileName(self, title):
        fname = re.sub('[^a-z0-9 ]', '', title.lower()).strip()
        fname = fname.replace(" ", "_")
        return(re.sub('__+', '_', fname))

    def createMaterialsFolder(self, path):
        #
        # if material folder is already selected return path itself
        #
        if path.endswith("materials"):
            return path, "Okay"
        matfolder = os.path.join(path, "materials")
        if not os.path.isdir(matfolder):
            try:
                os.mkdir(matfolder)
            except:
                return (None, "Problems creating new folder: " + matfolder)
        return (matfolder, "Okay")

    def testAssetList(self, path):
        if os.path.isfile(path):
            return datetime.fromtimestamp(os.path.getctime(path)).strftime("%d/%m/%y %H:%M")
        else:
            return None

    def alistReadJSON(self, env, path):
        json = env.readJSON(path)
        if json is not None:
            for key, item in json.items():
                folder = self.titleToFileName(item.get("title"))
                if len(folder) == 0:
                    folder = key

                cat = item.get("category")
                if item["type"] == "target":        # targets need a hint for category
                    cat = self.titleToFileName(cat)
                    item["folder"] = cat + "/" + folder
                else:
                    if cat == "Hair":
                        item["type"] = "hair"
                    elif cat == "Eyes":
                        item["type"] = "eyes"
                    elif cat == "Eyebrows":
                        item["type"] = "eyebrows"
                    elif cat == "Eyelashes":
                        item["type"] = "eyelashes"
                    elif cat == "Teeth":
                        item["type"] = "teeth"

                    item["folder"] = folder

        return(json)

    def alistGetFiles(self, json, key):
        flist = []
        item = json[key]
        mtype = item.get("type")
        if "files" in item:
            for fkey, fname in item["files"].items():
                if fkey in self.acceptedfiles:
                    flist.append(fname)
            return mtype, flist
        else:
            return None, []

    def alistCreateFolderFromTitle(self, path, base, mtype, title):
        if mtype == "expression" or mtype == "pose" or mtype == "model":
            # no subfolder, but name is plural
            #
            folder =os.path.join(path, mtype+"s", base)
            return(folder, "Okay")

        elif mtype == "skin" or mtype == "rig":
            # folder name is plural
            folder =os.path.join(path, mtype+"s", base, title)
        elif mtype == "target":
            # sub folder is part of the name, return if available
            sub = title.split("/")[0]
            folder =os.path.join(path, mtype, base, sub)
            if os.path.isdir(folder):
                return (folder, "Okay")
        else:
            # proxy and all type of clothes
            folder =os.path.join(path, mtype, base, title)

        # subfolder needed
        #
        if os.path.isdir(folder) and  mtype != "target":
            return (None, "Destination folder already existent: " + folder)
        try:
            os.mkdir(folder)
        except:
            return (None, "Problems creating new folder: " + folder)
        return (folder, "Okay")

    def getAssetPack(self, url, save_path, filename, unzip=False):
        """
        get URL and extract zipfile
        :return: bool True if loaded and err or None
        """
        url = url.replace(' ', '%20')
        try:
            req = Request(url)
        except Exception as err:
            return (False, str(err))

        try:
            response = urlopen(req)
        except URLError as e:
            if hasattr(e, 'reason'):
                err = 'URL: ' + url + ' ' +str(e.reason)
                return (False, err)
            elif hasattr(e, 'code'):
                err = 'URL: ' + url + ' Error code: ' + str( e.code)
                return (False, err)
        else:
            if not unzip:
                outpath = os.path.join(save_path, filename) if filename else save_path
                try:
                    with open(outpath, mode="wb") as ifile:
                        ifile.write(response.read())
                except Exception as err:
                    return (False, str(err))
            else:
                with ZipFile(BytesIO(response.read())) as zfile:
                    zfile.extractall(self.unzipdir)

        return (True, None)

    def getUrlFile(self, url, destination):
        return (self.getAssetPack(url, destination, None, unzip=False))

    def tempDir(self):
        self.unzipdir = tempfile.mkdtemp(prefix="mh_")
        return (self.unzipdir)

    def unZip(self, zipfile):
        self.tempDir()
        with ZipFile(zipfile,"r") as zip_ref:
            zip_ref.extractall(self.unzipdir)
        return(self.unzipdir)

    def cleanupUnzip(self):
        if self.unzipdir is not None:
            if os.path.split(self.unzipdir)[1].startswith("mh_"):
                print ("Cleanup " + self.unzipdir)
                shutil.rmtree(self.unzipdir)


    def copyAssets(self, source, dest, mesh, replace=True):
        l = len(source)
        for root, dirs, files in os.walk(source, topdown=True):
            for name in files:
                if root.startswith(source):
                    root = root[l+1:]

                dirs = root.split(os.sep)
                category = dirs[0]
                if category in ["clothes", "eyes", "eyelashes", "eyebrows", "hair", "skins", "teeth", "tongue", "proxymeshes", "rigs", "poses", "expressions"]:
                    # proxy is renamed
                    #
                    if category == "proxymeshes":
                        category = "proxy"
                    folder = os.path.join(dest, category, mesh)

                    # for subfolders we always change that to material
                    #
                    if len(dirs) > 2:
                        dirs[2] = "materials"

                    restdirs = os.sep.join(dirs[1:])
                    destfolder = os.path.join(folder, restdirs)
                    sourcefolder = os.path.join(source, root)
                    if not os.path.isdir(destfolder):
                        print("create " + destfolder)
                        os.makedirs(destfolder, exist_ok = True)
                    sourcename = os.path.join(sourcefolder, name)
                    destname = os.path.join(destfolder, name)
                    if replace is False and os.path.isfile(destname):
                        print (destname + " is already existent")
                    else:
                        print ("copy " + sourcename + " => " + destname)
                        shutil.copyfile(sourcename, destname)
                elif category in ["shader_floor", "shader_litspheres", "shader_skybox"]:
                    subcat = root.split("_")
                    folder = os.path.join(dest, "shaders", subcat[1])
                    restdirs = os.sep.join(dirs[1:])
                    destfolder = os.path.join(folder, restdirs)
                    sourcefolder = os.path.join(source, root)
                    if not os.path.isdir(destfolder):
                        print("create " + destfolder)
                        os.makedirs(destfolder, exist_ok = True)
                    sourcename = os.path.join(sourcefolder, name)
                    destname = os.path.join(destfolder, name)
                    if replace is False and os.path.isfile(destname):
                        print (destname + " is already existent")
                    else:
                        print ("copy " + sourcename + " => " + destname)
                        shutil.copyfile(sourcename, destname)


class TargetASCII():
    """
    the class should also support stand-alone compressor
    """

    def __init__(self):
        pass

    def load(self, filename):
        data = []
        dtype = [('index','u4'),('vector','(3,)f4')]
        try:
            fd = open(filename, 'r', encoding='utf-8')
        except:
            return (False, None)
        else:
            for line in fd:
                line = line.strip()
                if line.startswith('#'):
                    continue
                translationData = line.split()
                if len(translationData) != 4:
                    continue
                vertIndex = int(translationData[0])
                translationVector = (float(translationData[1]), float(translationData[2]), float(translationData[3]))
                data.append((vertIndex, translationVector))
            return(True, np.asarray(data, dtype=dtype))

    def allowToWrite(self, filename):
        try:
            fp = open(filename, "w")
        except PermissionError:
            return False
        else:
            return True

    def saveCompressed(self, filename, content):
        f = open(filename, "wb")
        np.savez_compressed(f, **content)
        f.close()

    def scanDir(self, path):
        result = []
        for root, dirs, files in os.walk(path, topdown=True):
            for name in files:
                if name.endswith(".target"):
                    result.append(os.path.join(root, name))

        return(result)

    def loadAllTargets(self, path, verbose=0):
        content = {}
        l = len(path)
        alltargets = self.scanDir(path)
        for filename in alltargets:
            if verbose >0:
                print ("loading: " + filename)
            (res, arr) = self.load(filename)
            if res is True:
                if filename.startswith(path):
                    name = filename[l+1:]
                    content[name[:-7]] = arr
        return content

    def compressAllTargets(self, sourcefolder, destfile, verbose=0, remove=True):
        content = self.loadAllTargets(sourcefolder, verbose)
        howmany = len(content)
        if howmany > 0:
            if verbose > 0:
                print ("save compressed: " + destfile)
            self.saveCompressed(destfile, content)
        else:
            if verbose > 0:
                print ("No content for: " + destfile)
            if remove:
                if os.path.exists(destfile):
                    os.remove(destfile)
        return howmany

