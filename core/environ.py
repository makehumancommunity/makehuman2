"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * UserEnvironment
"""

import os
import sys
import json
import locale
import platform

class UserEnvironment():
    def __init__(self):
        self.osindex= -1
        self.default_encoding    = sys.getdefaultencoding()
        self.filesystem_encoding = sys.getfilesystemencoding()
        self.preferred_encoding  = locale.getpreferredencoding()

        # default entries (will be used when not in user or system config)
        #
        self.defaultconf = {
            "basename": None,
            "noSampleBuffers": False,
            "redirect_messages": False,
            "remember_session": False,
            "theme": "makehuman.qss",
            "units": "metric",
            "apihost": "127.0.0.1",
            "apiport": 12345
        }

    def getDefaultConf(self):
        return self.defaultconf

    def writeDefaultConf(self, path: str, docpath: str) -> bool:
        self.defaultconf["path_home"] = docpath
        self.defaultconf["path_error"] = os.path.join(docpath, "log")
        try:
            f = open(path, 'w', encoding='utf-8')
        except:
           return False
        with f:
            try:
                json.dump(self.defaultconf, f, indent=4, sort_keys=True)
            except:
                return False
        return True


    def getEncoding(self):
        return [self.preferred_encoding, self.default_encoding, self.filesystem_encoding]

    def getPlatform(self):
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
        return p, osindex, ostype, platform_version

    def getHardware(self):
        return platform.machine(), platform.processor(), platform.uname()[2]

    def getUserConfigFilenames(self, osindex=None, create=False):
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
                    return None, folder

        return os.path.join(folder, 'makehuman2.conf'), os.path.join(folder, 'makehuman2_session.conf')


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

    def getHomePathProposal(self) -> str:
        """
        calculate default home path according to operating system
        :return: default path
        """

        # Windows (ask in registry)
        #
        if self.osindex == 0:
            import winreg
            keyname = r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyname) as k:
                try:
                    value, type_ = winreg.QueryValueEx(k, 'Personal')
                except FileNotFoundError:
                    value, type_ = "%USERPROFILE%\\Documents", winreg.REG_EXPAND_SZ
                if type_ == winreg.REG_EXPAND_SZ:
                    path = self.formatPath(winreg.ExpandEnvironmentStrings(value))
                elif type_ == winreg.REG_SZ:
                    path = self.formatPath(value)

        # Linux
        #
        elif self.osindex == 1:
            cpath = os.path.expanduser('~/.config/user-dirs.dirs')
            if os.path.isfile(cpath):
                with open(cpath, 'r', encoding='utf-8') as cfile:
                    for line in cfile:
                        if line and line.startswith('XDG_DOCUMENTS_DIR'):
                            line = line.strip()
                            key, value = line.split('=')
                            key = key.split('_')[1]
                            value = os.path.expandvars(value.strip('"'))
                            if os.path.isdir(value):
                                path = value

            if path is None:
                path = self.pathToUnicode(os.path.expanduser('~'))

        # MacOS
        #
        else:
            path = os.path.expanduser('~')

        # append makehuman2
        #
        path = os.path.join(path, "makehuman2")

        return path

    def getExecutableInfos(self):
        sys_path = os.path.pathsep.join( [self.pathToUnicode(p) for p in sys.path] )
        bin_path = self.pathToUnicode(os.environ['PATH'])
        return sys_path, bin_path, sys.executable

