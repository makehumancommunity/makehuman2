"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * globalObjects
    * cacheRepoEntry
    * programInfo
"""
import sys
import os
import re
import locale
import time
import json
import glob
import shutil
from uuid import uuid4
from gui.application import QTVersion
from core.debug import dumper
from core.importfiles import UserEnvironment
from core.sql_cache  import FileCache
from opengl.info import GLDebug
from opengl.texture import TextureRepo

class globalObjects():
    def __init__(self, env):
        self.env = env
        self.app = None
        self.shaderInit = None
        self.subwindows = {}
        self.openGLWindow = None
        self.openGLBlock  = True
        self.openGLWinUpdate = True
        self.midColumn    = None
        self.centralWidget= None
        self.baseClass = None
        self.closing = False

        # set default keys, this makes sure all keys are there
        #
        self.keyDict = {
            "Top": "Num+9", "Left": "Num+4", "Right": "Num+6", "Front": "Num+2",
            "Back": "Num+8", "Bottom": "Num+7", "Zoom-In": "Num++", "Zoom-Out": "Num+-",
            "Pan-Left": "Shift+Left", "Pan-Right": "Shift+Right", "Pan-Down": "Shift+Down", "Pan-Up": "Shift+Up",
            "Rotate-Left": "Ctrl+Left", "Rotate-Right": "Ctrl+Right", "Rotate-Down": "Ctrl+Down", "Rotate-Up": "Ctrl+Up",
            "Stop Animation": "Esc", "Toggle Perspective": "Num+0"
            }

        # now get own keys if available and replace elements
        # 
        if "keys" in self.env.config:
            k = self.env.config["keys"]
            for elem in k:
                self.keyDict[elem] = k[elem]

        self.guiPresets = {"Randomizer": None, "Animplayer": None, "Renderer": None }

        self.textureRepo = TextureRepo(self)
        self.apiSocket = None              # will contain socket for applications
        self.reset()

    def reset(self):
        self.project_changed = False        # will contain if sth. has changed
        self.textureRepo.cleanup()
        self.cachedInfo = []                # cached data 
        self.Targets = None                 # is a pointer to target objects
        self.targetCategories = None        # will contain the category object
        self.targetMacros     = None        # will contain macrodefinitions (JSON structure, if available)
        self.targetRepo       = {}          # will contain a dictionary of available targets
        self.macroRepo        = {}          # will contain a dictionary of available macros
        self.missingTargets = []            # will contain a list of missing targets after load
        self.parallel = None                # for parallel processing. Should avoid more than one process at the time
        self.lastdownload = None            # will contain the filename of last downloaded file
        self.textSlot = [None, None, None, None, None] # text slots for graphical window

    def showSubwindow(self, name, parent, mclass, *params):
        if name not in self.subwindows:
            self.subwindows[name] = mclass(parent, *params)
        s = self.subwindows[name]
        s.show()
        s.raise_()
        return s

    def getSubwindow(self, name):
        if name in self.subwindows:
            return self.subwindows[name]
        return None

    def closeSubwindow(self, name):
        if name in self.subwindows:
            self.subwindows[name].close()

    def getCacheData(self):
        """
        gets data from cache, user-settings in match will overwrite standard tags
        """
        objectnames=[]
        self.cachedInfo = []
        rows, match = self.env.fileCache.listCacheMatch()
        for row in rows:
            key = row[0]+str(row[1])
            if key in objectnames:
                self.env.logLine(2, row[3] + " asset " + row[0] + " is duplicated. (ignored)")
            else:
                objectnames.append(key)
                tags = (match[row[1]] if row[1] in match else row[7]).split("|")
                self.cachedInfo.append(cacheRepoEntry(row[0], row[1], row[2], row[3], row[4], row[5], row[6], tags))

    def noAssetsUsed(self):
        for elem in self.cachedInfo:
            elem.used = False

    def getAssetByFilename(self, path):
        for elem in self.cachedInfo:
            if elem.path == path:
                return (elem)
        return(None)

    def hasAssetFolder(self, folder):
        for elem in self.cachedInfo:
            if elem.folder == folder:
                return True
        return False

    def rescanAssets(self, asset_type=None):
        if asset_type != "models":
            self.env.fileScanFoldersAttachObjects(asset_type)
        if asset_type is None or  asset_type  == "models":
            self.env.fileScanFolderMHM()
        self.getCacheData()
        return(self.cachedInfo)

    def markAssetByFileName(self, path, value):
        for elem in self.cachedInfo:
            if elem.path == path:
                elem.used = value
                return

    def gen_uuid(self):
        return(str(uuid4()))

    def readShaderInitJSON(self):
        shaderfile = os.path.join(self.env.path_sysdata, "shaders", "shader.json")
        self.shaderInit = self.env.readJSON(shaderfile)
        return (self.shaderInit)

    def setApplication(self, app):
        self.app = app

    
    def setTextSlot(self, num, target):
        if 0 < num <=5:
            self.textSlot[num-1] = target

    def generateBaseSubDirs(self, basename):
        for name in self.env.basefolders + ["exports", "skins", "models", "target", "contarget", "dbcache", "downloads"]:
            folder = os.path.join(self.env.path_userdata, name, basename)
            if self.env.mkdir(folder) is False:
                return (False)
        return (True)

class cacheRepoEntry():
    def __init__(self, name, uuid, path, folder, obj_file, thumbfile, author, tag):
        self.name = name
        self.uuid = uuid
        self.folder = folder
        self.path = path
        self.thumbfile = thumbfile
        self.author = author
        self.tag = tag
        self.used = False

        if obj_file is not None:
            self.obj_file = os.path.join(os.path.dirname(path), obj_file)
        else:
            self.obj_file = None

        # calculate expected mhbin
        #
        if path.endswith(".mhclo"):
            self.mhbin_file = path[:-5] + "mhbin"
        else:
            self.mhbin_file = path + ".mhbin"

    def __str__(self):
        return(dumper(self))

class programInfo():
    """
    this class should contain 'global parameters'
    especially:
    * all pathnames
    * converter functions
    * JSON reader/writer + integrity test
    """
    def __init__(self, frozen: bool, path_sys: str, args):
        """
        init: set all global parameters
        evaluates system path, platform in ostype and osindex.
        """

        # all folders that belong to a basemesh
        #
        self.basefolders = [ "clothes", "eyebrows", "eyelashes", "eyes", "hair", "teeth", "tongue", "proxy", "rigs", "poses", "expressions" ]

        self.basename = None
        self.fileCache = None
        self.last_error = None

        self.verbose = args.verbose
        self.admin = args.admin
        self.noalphacover = args.nomultisampling    # in reality it means not to use alpha to coverage
        self.recreate_repo = args.repository
        self.uselog  = args.l
        self.frozen  = frozen
        self.path_sys = path_sys
 
        uenv = UserEnvironment()
        (self.sys_platform, self.osindex, self.ostype, self.platform_version) = uenv.GetPlatform()
        (self.platform_machine, self.platform_processor, self.platform_release) = uenv.GetHardware()

        # create user configfolder if not there, if that is impossible terminate
        #
        (self.path_userconf, self.path_usersess) = uenv.GetUserConfigFilenames(create=True)
        if self.path_userconf is None:
            print("cannot create folder " + self.path_usersess)
            exit(21)

        #
        # a lot of information for later use
        #
        self.default_encoding    = sys.getdefaultencoding()
        self.filesystem_encoding = sys.getfilesystemencoding()
        self.stdout_encoding     = sys.stdout.encoding
        self.preferred_encoding  = locale.getpreferredencoding()
        self.sys_path = os.path.pathsep.join( [self.pathToUnicode(p) for p in sys.path] )
        self.bin_path = self.pathToUnicode(os.environ['PATH'])
        self.sys_version = re.sub(r"[\r\n]"," ", sys.version)

        self.sys_executable = sys.executable

        from numpy import __version__ as numpvers
        self.numpy_version = [int(x) for x in numpvers.split('.')]
        if self.numpy_version[0] <= 1 and self.numpy_version[1] < 6:
            print ("MakeHuman requires at least numpy version 1.6")
            exit (20)

        self.QT_Info = QTVersion(self)
        gdebug = GLDebug(self.osindex, False) # not yet initialized
        self.GL_Info = gdebug.getOpenGL_LibVers()

    def __str__(self):
        """
        print debug information, should contain all information
        """
        return  json.dumps(self.__dict__, indent=4, sort_keys=True)

    def setVerboseBit(self, bit):
        self.verbose |= bit

    def resetVerboseBit(self, bit):
        self.verbose &= ~bit

    def helpVerbose(self):
        verbosedefinition = [(1, "low log level"), (2, "mid log level"), (4, "memory management"),
            (8, "file access"), (16, "high level and numpy runtime error messages"),
            (32, "JSON (e.g glTF) or to get lines for face or body poses when loading bvh file")]
        return verbosedefinition

    def showVersion(self):
        print (self.release_info["name"] + " Version " + ".".join(str(x) for x in self.release_info["version"]))
        print ("Status: " + self.release_info["status"])
        print ("Copyright: " + self.release_info["copyright"])
        print ("URL: " + self.release_info["url_mhcommunity"])
        if hasattr(self, "path_userconf"):
            print ("\nUser configuration file is: " + self.path_userconf)
            if self.osindex == 0:
                print("\nWindows python:\n" + os.path.realpath(self.path_userconf))
        else:
            print ("\nNo user configuration available.")

    def pathToUnicode(self, path: str) -> str:
        """
        Unicode representation of the filename.
        Bytes is decoded with the codeset used by the filesystem of the operating system.
        Unicode representations of paths are fit for use in GUI.
        """

        if isinstance(path, bytes):
            # Approach for bytes string type
            try:
                return str(path, 'utf-8')
            except UnicodeDecodeError:
                pass
            try:
                return str(path, self.filesystem_encoding)
            except UnicodeDecodeError:
                pass
            try:
                return str(path, self.default_encoding)
            except UnicodeDecodeError:
                pass
            try:
                return str(path, self.preferred_encoding)
            except UnicodeDecodeError:
                return path
        else:
            return path

    def formatPath(self, path: str) -> str:
        if path is None:
            return None
        return self.pathToUnicode(os.path.normpath(path).replace("\\", "/"))

    def fullPath(self, path: str) -> str:
        if self.osindex == 0:
            path = os.path.normcase(path)
        return os.path.expanduser(os.path.normpath(path).replace("\\", "/"))

    def normalizeName(self, path: str) -> str:
        """
        change a name to lower case, only allow a-z 0-9 - + _ =
        used to create filenames compatible for Windows and Linux
        """
        path = path.lower()
        return re.sub('[^a-z0-9_+=-]', "_", path)


    def mkdir(self,folder):
        if not os.path.isdir(folder):
            if os.path.isfile(folder):
                self.last_error = "File exists instead of folder " + folder
                return (False)
            try:
                os.mkdir(folder)
            except OSError as error:
                self.last_error = str(error)
                return (False)
        return True

    def copyfile(self, source, dest):
        try:
            shutil.copyfile(source, dest)
        except IOError as error:
            self.last_error = "Unable to copy file. " + str(error)
            return False
        
        return (True)


    def readJSON(self, path: str) -> dict:
        """
        JSON reader, will return JSON object or None
        in case of error, self.last_error will be set
        """
        try:
            f = open(path, 'r', encoding='utf-8')
        except:
            self.last_error =   "Cannot read JSON " + path
            return None
        with f:
            try:
                self.logLine(8, "Load '" + path + "'")
                json_object = json.load(f)
            except json.JSONDecodeError as e:
                self.last_error = "JSON format error in " + path + " > " + str(e)
                self.logLine(1, self.last_error)
                return None
            if not json_object:
                self.last_error =  "Empty JSON file " + path
                self.logLine(1, self.last_error)
                return None
        return (json_object)
            
    def writeJSON(self, path: str, json_object: dict) -> bool:
        """
        JSON writer, will return False in case of error
        in case of error, self.last_error will be set
        """
        self.logLine(8, "Write '" + path + "'")

        try:
            f = open(path, 'w', encoding='utf-8')
        except:
           self.last_error =   "Cannot write JSON " + path
           return False
        with f:
            try:
                json.dump(json_object, f, indent=4, sort_keys=True)
            except:
                self.last_error = "Cannot write JSON " + path
                return False
        return True

    def environment(self) -> bool:
        """
        Read the configuration

        * environment in MH_HOME_LOCATION
        * a name of a folder in a configuration file
        * using the DOCUMENTS folder or home folder according to registry (Windows) or XDG-file (Linux)

        returns True (all okay) or False (system cannot start)
        """

        # default entries (will be used when not in user or system config)
        #
        defaultconf = {
            "basename": None,
            "noSampleBuffers": False,
            "redirect_messages": True,
            "remember_session": False,
            "theme": "makehuman.qss",
            "units": "metric",
            "apihost": "127.0.0.1",
            "apiport": 12345
        }

        # system paths
        #
        self.path_sysdata = os.path.join(self.path_sys,  "data")
        self.path_sysicon = os.path.join(self.path_sysdata, "icons")
        self.path_version = os.path.join(self.path_sysdata, "makehuman2_version.json")
        self.path_sysconf = os.path.join(self.path_sysdata, "makehuman2_default.conf")

        # read json files with additional information, home-path can be changed
        #
        self.config = {}
        self.path_home = None
        self.writeconf = False          # in case of first time or in case of missing parameter, config file needs to rewritten

        if os.path.isfile(self.path_version):
            c = self.readJSON(self.path_version)
            if c is None:
                return False
        else:
            self.last_error = self.path_version + " not found!"
            return False
        self.release_info = c

        if os.path.isfile(self.path_userconf):
            c = self.readJSON(self.path_userconf)
            if c is None:
                return False

            self.config = c
            self.path_home = c["path_home"] if "path_home" in c else None
        else:
            c = self.readJSON(self.path_sysconf)
            if c is None:
                return False
            self.writeconf = True
            self.config = c

        # integrity test (avoid missing keys)
        #
        if self.dictFillGaps(defaultconf, self.config):
            self.writeconf = True

        # calculate path_home
        # method: overwrite path_home by environment
        #
        path = os.environ.get("MH_HOME_LOCATION", '')
        if os.path.isdir(path):
            path = self.formatPath(path)

            if path is not None:
                self.path_home = path

        # in case of first time get home path from system if not already set
        #
        if self.path_home is None:

            # Windows (ask in registry)
            #
            if self.osindex == 0:
                import winreg
                keyname = r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
                #name = 'Personal'
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyname) as k:
                    try:
                        value, type_ = winreg.QueryValueEx(k, 'Personal')
                    except FileNotFoundError:
                        value, type_ = "%USERPROFILE%\\Documents", winreg.REG_EXPAND_SZ
                    if type_ == winreg.REG_EXPAND_SZ:
                        self.path_home = self.formatPath(winreg.ExpandEnvironmentStrings(value))
                    elif type_ == winreg.REG_SZ:
                        self.path_home = self.formatPath(value)

            # Linux
            #
            elif self.osindex == 1:
                path = os.path.expanduser('~/.config/user-dirs.dirs')
                if os.path.isfile(path):
                    with open(path, 'r', encoding='utf-8') as file:
                        for line in file:
                            if line and line.startswith('XDG_DOCUMENTS_DIR'):
                                line = line.strip()
                                key, value = line.split('=')
                                key = key.split('_')[1]
                                value = os.path.expandvars(value.strip('"'))
                                if os.path.isdir(value):
                                    self.path_home = value

                if self.path_home is None:
                    self.path_home = self.pathToUnicode(os.path.expanduser('~'))

            # MacOS
            #
            else:
                self.path_home = os.path.expanduser('~')
            self.path_home = os.path.join(self.path_home, "makehuman2")
            self.config["path_home"] = self.path_home
            self.writeconf = True

        if self.path_home is None:
            self.last_error = "Cannot not determine user folder!"
            return False

        # set data paths
        #
        self.path_userdata = os.path.join(self.path_home, "data")

        # add own system path for windows
        #
        if self.frozen:
            # Make sure we load packaged DLLs instead of those present on the system
            os.environ["PATH"] = '.' + os.path.pathsep + self.path_sys + os.path.pathsep + os.environ["PATH"]

        # error files for redirection
        #
        if "path_error" not in self.config:
            self.config["path_error"] = self.path_error = os.path.join(self.path_home, "log")
        else:
            self.path_error = self.config["path_error"]

        # generate all (still missing) folders
        #
        if self.generateFolders() is False:
            return(False)

        self.reDirect(self.uselog)     # redirect error messages

        # in case of first start or missing parameter write configuration
        #
        if self.writeconf:
            if self.writeJSON(self.path_userconf, self.config) == False:
                return False

        # set further parameters from configuration
        #
        self.basename = self.config["basename"]

        # read last session on demand
        #
        self.loadSession()
        return True

    def generateFolders(self):
        """
        create folders, return false if problem, write results to logfile
        in case of error set last_error
        """
        for folder in [self.path_home, self.path_error, self.path_userdata]:
            if self.mkdir(folder) is False:
                return False
            self.logLine(2, folder + " created or already available")

        userdata = self.path_userdata

        # subfolder inside userdata, so usually base folder + special ones
        #
        for name in self.basefolders + ["themes", "exports","skins", "models", "target", "contarget", "dbcache", "downloads", "shaders", "grab"]:
            folder = os.path.join(userdata, name)
            if self.mkdir(folder) is False:
                return (False)

        # and private litsphere/skybox/floor folders
        #
        for name in ["litspheres", "skybox", "floor"]:
            folder = os.path.join(userdata, "shaders", name)
            if self.mkdir(folder) is False:
                return (False)

        return (True)

    def initFileCache(self):
        dbname = self.stdUserPath("dbcache", "repository.db")
        self.fileCache = FileCache(self, dbname)

    def reDirect(self, log=False):
        """
        redirection of stderr and stdout to files path_stdout and path_stderr
        """
        if self.config["redirect_messages"] or log is True:
            self.path_stdout = os.path.join(self.path_error, "makehuman-out.txt")
            sys.stdout = open(self.path_stdout, "w", encoding=self.preferred_encoding, errors="replace")
            self.path_stderr = os.path.join(self.path_error, "makehuman-err.txt")
            sys.stderr = open(self.path_stderr, "w", encoding=self.preferred_encoding, errors="replace")
        else:
            self.path_stdout= None
            self.path_stderr= None

    def stdSysPath(self, category, filename=None):
        if self.basename is not None:
            if filename:
                return(os.path.join(self.path_sysdata, category, self.basename, filename))
            else:
                return(os.path.join(self.path_sysdata, category, self.basename))
        return None

    def stdUserPath(self, category=None, filename=None):
        if category is None:
            return (self.path_userdata)

        if self.basename is not None:
            if filename:
                return(os.path.join(self.path_userdata, category, self.basename, filename))
            else:
                return(os.path.join(self.path_userdata, category, self.basename))
        return None

    def stdLogo(self):
        return os.path.join(self.path_sysicon, "makehuman2logo128.png")

    def isSourceFileNewer(self, destination, source):
        """
        should return true when: destination is not there
        destination is older
        """
        if not os.path.isfile(destination):
            return (True)
        sourcedate = int(os.stat(source).st_mtime)
        destdate   = int(os.stat(destination).st_mtime)
        return (sourcedate > destdate)

    def getFileList(self, dirname, pattern):
        """
        get a file list with an extension
        """
        pattern = os.path.join(glob.escape(dirname), pattern)
        return(glob.glob(pattern))

    def getDataFileList(self, ext, *subdirs):
        """
        get filelist from system datapath or userdata + subdirectories
        """
        filebase = {}
        for path in [self.path_sysdata, self.path_userdata]:
            test = os.path.join(path, *[sdir for sdir in subdirs])
            if os.path.isdir(test):
                files = self.getFileList(test, "*." + ext)
                for filename in files:
                    directory, fname = os.path.split(filename)
                    filebase[fname] = filename
        return(filebase)

    def getDataDirList(self, search, *subdirs):
        """
        get filelist from system datapath or userdata + subdirectories
        """
        filebase = {}
        for path in [self.path_sysdata, self.path_userdata]:
            test = os.path.join(path, *[sdir for sdir in subdirs])
            files = self.getFileList(test, "*")
            for dirname in files:
                if os.path.isdir(dirname):
                    if search is not None:
                        filename = os.path.join(dirname, search)
                        if os.path.isfile(filename):
                            directory, fname = os.path.split(dirname)
                            filebase[fname] = filename
                    else:
                        directory, fname = os.path.split(dirname)
                        filebase[fname] = directory
        return(filebase)

    def getParentDirName(self, name):
        """
        return parent directory needed for all assets
        """
        parts = name.replace('\\', '/').split('/')
        if len(parts) > 2:
            return parts[-2]
        return ""

    def existDataFile(self, *names):
        """
        check in both datapaths, if a file exists, first personal one is used
        in case it is not found last_error will mention the file name 
        """
        self.last_error = None
        for path in [self.path_userdata, self.path_sysdata]:
            test = os.path.join(path, *[name for name in names])
            # print ("Test: " +  test)
            if os.path.isfile(test):
                return(test)
        self.last_error = "/".join([name for name in names]) + " not found"
        return None

    def existFileInBaseFolder(self, base, subfolder, objpath, filename):
        """
        special check for assets
        """
        parentobj = self.getParentDirName(objpath)
        abspath = self.existDataFile(subfolder, base, parentobj, filename)
        if abspath is None:
            if "/" in filename:
                filename = "/".join (filename.split("/")[1:])
            abspath = self.existDataFile(subfolder, base, filename)
        return (abspath)

    def existDataDir(self, *names):
        """
        check in both datapaths, if a directory  exists, first personal one is used
        in case it is not found last_error will mention the directory name 
        """
        for path in [self.path_userdata, self.path_sysdata]:
            test = os.path.join(path, *[name for name in names])
            if os.path.isdir(test):
                return(test)
        self.last_error = "/".join([name for name in names]) + " not found"
        return None

    def getDataDirs(self, *names):
        """
        get an array of directories,
        return user data first
        """
        result = []
        for path in [self.path_userdata, self.path_sysdata]:
            test = os.path.join(path, *[name for name in names])
            if os.path.isdir(test):
                result.append(test)
        return result

    def subDirsBaseFolder(self, pattern, subdir=None):
        """
        classical all folders for objects may have 2 levels
        """
        filenames = []
        latest = 0
        basefolders = self.basefolders if subdir is None else [subdir]
        for path in [self.path_userdata, self.path_sysdata]:
            for folder in basefolders:
                test = os.path.join(path, folder, self.basename)
                if os.path.isdir(test):
                    mod = int(os.stat(test).st_mtime)
                    if mod > latest:
                        latest = mod

                    files = os.listdir(test)
                    for fname1 in files:
                        aname1 = os.path.join(test, fname1)
                        if os.path.isdir(aname1):
                            files2 = os.listdir(os.path.join(test,aname1))
                            for fname2 in files2:
                                if fname2.endswith(pattern):
                                    cname = os.path.join(aname1, fname2)
                                    mod = int(os.stat(cname).st_mtime)
                                    if mod > latest:
                                        latest = mod
                                    filenames.append([folder, cname])
                        if fname1.endswith(pattern):
                            mod = int(os.stat(aname1).st_mtime)
                            if mod > latest:
                                latest = mod
                            filenames.append([folder, aname1])

        if self.verbose & 8:
            scanned = "all subdirs" if subdir is None else subdir
            self.logTime(latest, "Last change: " + scanned)
        return(latest, filenames)

    def fileScanFoldersAttachObjects(self, subdir=None):
        """
        scanner for mhclo/proxy files checks in all basefolders + subdirs (only 1 level)
        (.mhclo, .proxy, .mhskel)
        """
        if subdir is None:
            assetdirs = [[ ".proxy", "proxy"], [ ".mhskel", "rigs" ], [".mhpose", "expressions"], [".bvh", "poses"], [".mhpose", "poses"]]

            (latest, files) = self.subDirsBaseFolder(".mhclo", None)
            for elem in assetdirs:
                (l, f) = self.subDirsBaseFolder(elem[0], elem[1])
                if len(f) > 0:
                    files.extend(f)
                    if l > latest:
                        latest = l

        elif subdir == "proxy":
            (latest, files) = self.subDirsBaseFolder(".proxy", "proxy")
        elif subdir == "rigs":
            (latest, files) = self.subDirsBaseFolder(".mhskel", "rigs")
        elif subdir == "expressions":
            (latest, files) = self.subDirsBaseFolder(".mhpose", "expressions")
        elif subdir == "poses":
            (latest, files) = self.subDirsBaseFolder(".bvh", "poses")
        else:
            (latest, files) = self.subDirsBaseFolder(".mhclo", subdir)

        # check date of repository db, after force reset parameter
        #
        reread = self.fileCache.createCache(latest, subdir, self.recreate_repo)
        self.recreate_repo = False
        if reread is True:
            self.logLine (1, "Recreate repo is " + str(reread))
            data = []
            for (folder, path) in files:
                #print (path)
                (filename, extension) = os.path.splitext(path)
                thumbfile = filename + ".thumb"
                if not os.path.isfile(thumbfile):
                    thumbfile = None

                if extension == ".mhskel" or extension == ".mhpose":
                    json = self.readJSON(path)
                    if json is None:
                        self.logLine (1, "JSON error " + self.last_error)
                    else:
                        name = json["name"] if "name" in json else filename
                        uuid = extension[3:] + "_"+name
                        author = json["author"] if "author" in json else "unknown"
                        mtags = "|".join(json["tags"]).encode('ascii', 'ignore').lower().decode("utf-8") if "tags" in json else ""
                        data.append([name, uuid, path, folder, None, thumbfile, author, mtags])
                    continue

                elif extension == ".bvh":
                    metafile = filename + ".meta"
                    name = os.path.basename(filename)
                    uuid = "bvh_" + name
                    author = "unknown"
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
                    data.append([name, uuid, path, folder, None, thumbfile, author, mtags])
                    continue


                with open(path, 'r') as fp:
                    uuid = 0
                    name = ""
                    obj_file = None
                    author = "unknown"
                    tags = []
                    for line in fp:
                        #if line.startswith("verts"):
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
                    data.append([name, uuid, path, folder, obj_file, thumbfile, author, mtags])
            self.fileCache.insertCache(data)


    def fileScanFolderMHM(self):
        """
        scanner for mhm files checks in models folder
        """
        namematch = []
        subdir = "models"
        (latest, files) = self.subDirsBaseFolder(".mhm", subdir)
        reread = self.fileCache.createCache(latest, subdir)
        if reread is True:
            data = []
            for (folder, path) in files:
                self.logLine(8, "Check '" + path + "'")
                (filename, extension) = os.path.splitext(path)
                thumbfile = filename + ".thumb"
                if not os.path.isfile(thumbfile):
                    thumbfile = None

                # skip directories
                if not os.path.isfile(path):
                    continue

                with open(path, 'r') as fp:
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

                    if name is None:
                        name = os.path.basename(filename)

                    mtags = "|".join(tags)
                    data.append([name, uuid, path, subdir, None, thumbfile, author, mtags])
            self.fileCache.insertCache(data)

    def getCacheData(self):
        """
        gets data from cache, user-settings in match will overwrite standard tags
        """
        data = []
        rows, match = self.fileCache.listCacheMatch()
        for row in rows:
            tags = (match[row[1]] if row[1] in match else row[7]).split("|")
            data.append(cacheRepoEntry(row[0], row[1], row[2], row[3], row[4], row[5], row[6], tags))
        return (data)

    def dictFillGaps(self, standard, testdict):
        """
        recursively add elements from standard if dictionaries have missing data
        """
        changed = False
        for element in standard.keys():
            if element not in testdict:
                testdict[element] = standard[element]
                return True
            else:
                if isinstance(standard[element], dict):
                    changed = self.dictFillGaps(standard[element], testdict[element])
        return (changed)

    def toUnit(self, value, inchonly=False):
        """
        for metrical, centimeter is used, otherwise feet & inches
        """
        if "units" in self.config and self.config["units"] == "imperial":
            inch = value * (10 / 2.54)
            if inchonly:
                return (str(round(inch, 2)) + " in")
            ft = inch // 12
            inch = round(inch - ft*12, 2)
            return(str(round(ft)) + " ft  "+ str(inch) + " in")
        return (str(round(value*10, 2)) + " cm")

    def logLine(self, level, line):
        """
        write to logfile
        """
        if self.verbose & level:
            print ("[" + str(level) + "] " + line)

    def logTime(self, ctime, line):
        """
        write time to logfile
        """
        if self.verbose & 8:
            outtime = time.strftime("%Y/%m/%d %H:%M:%S ", time.localtime(ctime))
            print ("[8] " + outtime + line)

    def dateFileName(self, prefix, postfix):
        return prefix + time.strftime("%Y%m%d-%H%M%S", time.localtime()) + postfix

    def loadSession(self):
        """
        load last saved session
        """
        default = { "mainwinsize": 
                { "w": 1200, "h": 800 }
        }
        self.session = None
        if self.config["remember_session"] is True:
            name = self.path_usersess
            self.logLine (2, "Read session from " + name)
            self.session = self.readJSON(name)
            if self.session is None:
                self.logLine (1, "JSON error " + self.last_error)

        if self.session is None:
            self.session = default
            self.logLine (2, "using standard session")
        else:
            # integrity test
            #
            self.dictFillGaps(default, self.session)

    def saveSession(self):
        """
        save last session (if desired)
        """
        if self.config["remember_session"] is True:
            name = self.path_usersess
            self.logLine(2, "Save session to " + name)
            if self.writeJSON(name, self.session) is False:
                self.logLine(1, self.last_error)
        else:
            self.logLine(2, "No need to save session")

    def convertToRichFile(self, filename):
        lines = []
        with open(filename, 'r', encoding='utf-8', errors='ignore') as infile:
            for line in infile:
                line = line.strip()
                if line.startswith("=="):
                    search=line[2:]
                    if search in self.release_info:
                        if search.startswith("url_"):
                            line = '<a href="' + self.release_info[search] + '" style="color: #ffa02f;">' + search[4:].upper() + '</a>'
                        else:
                            line = self.release_info[search]

                lines.append(line.strip())
        text = "<br>".join(lines)
        return (text)

    def cleanup(self):
        """
        all code for cleanup
        * close files
        """
        if self.path_stdout:
            sys.stdout.close()
        if self.path_stderr:
            sys.stderr.close()

