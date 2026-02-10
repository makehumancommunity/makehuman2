#!/usr/bin/python3
"""
build a windows version (not yet finished)
"""

import os
import re
import shutil
import sys
import json
import argparse
import tempfile
import subprocess

class winBuilder():
    def __init__(self, tmp, path, verbose):
        self.tmp = tmp
        self.conf = path
        self.verbose= verbose
        self.pynsistcfg = None
        self.pynsistdir = None
        self.reponame = None
        self.name = None
        self.script = None
        self.icon = None
        self.nsifile = None
        self.ignoredirs = []
        self.ignorefiles = []
        #
        # get installer path according to OS
        #
        if not sys.platform.startswith('win'):
            self.makensis = "/usr/bin/makensis"
        else:
            # get windows version
            import winreg
            try:
                nsis_dir = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\NSIS')
            except OSError:
                nsis_dir = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Wow6432Node\\NSIS')
            self.makensis = os.path.join(nsis_dir, "makensis.exe")


    def cleanexit(self, num, text):
        print (text)
        exit(num)

    def readJSON(self, path: str) -> dict:
        if self.verbose:
            print ("+ read " + path)
        try:
            f = open(path, 'r', encoding='utf-8')
        except:
            self.cleanexit (1, "Cannot read JSON " + path)

        try:
            json_object = json.load(f)
        except json.JSONDecodeError as e:
            self.cleanexit (2, "JSON format error in " + path + " > " + str(e))

        return json_object

    def mkdir(self,folder):
        if self.verbose:
            print ("+ check and create folder " + folder)
        if not os.path.isdir(folder):
            if os.path.isfile(folder):
                self.cleanexit(2, "File exists instead of folder " + folder)
            try:
                os.mkdir(folder)
            except OSError as error:
                self.cleanexit(2, str(error))

    def copyfile(self, source, dest):
        if self.verbose:
            print ("+ copy " + source + " to " + dest)
        try:
            shutil.copyfile(source, dest)
        except OSError as error:
            self.cleanexit(2, str(error))
        
    def createPynsistCfg(self, text):
        path = os.path.join(self.pynsistdir, self.pynsistcfg)
        if self.verbose:
            print ("+ write config for pynsist to " + path)
        with open(path, "w") as tfile:
            print(text, file=tfile)

    def evaluatePynsistCfg(self):
        json_object = self.readJSON(self.conf)
        if self.verbose:
            print ("+ evaluate " + self.conf)

        if not os.access(self.makensis, os.X_OK):
            self.cleanexit(1, self.makensis + " is not an executable program")

        if "pynsistfile" not in json_object:
            self.cleanexit(3, "Missing 'pynsistfile' in " + self.conf)
        self.pynsistcfg = json_object["pynsistfile"]

        if "pynsistdir" not in json_object:
            self.cleanexit(3, "Missing 'pynsistdir' in " + self.conf)
        self.pynsistdir = os.path.join(self.tmp, json_object["pynsistdir"])

        if "reponame" not in json_object:
            self.cleanexit(3, "Missing 'reponame' in " + self.conf)
        self.repodir = os.path.join(self.pynsistdir, json_object["reponame"])

        if "ignoredirs" in json_object:
            self.ignoredirs = json_object["ignoredirs"]

        if "ignorefiles" in json_object:
            self.ignorefiles = json_object["ignorefiles"]

        if "mhconfigfile" not in json_object:
            self.cleanexit(3, "Missing 'mhconfigfile' in " + self.conf)

        self.mkdir(self.pynsistdir)
        self.nsifile = os.path.join(self.pynsistdir, "build", "nsis", "installer.nsi")

        mhconfig = json_object["mhconfigfile"]
        mhobject = self.readJSON(mhconfig)

        if "pynsist" not in json_object:
            self.cleanexit(4, "Missing 'pynsist' in " + self.conf)

        pynsist = json_object["pynsist"]

        outtext = ""
        for cat in "Application", "Python", "Include":
            if cat not in pynsist:
                self.cleanexit(3, "Missing " + cat + " in " + self.conf)

            outtext += "\n[" + cat + "]\n"
            if cat == "Application":
                appl = pynsist["Application"]
                for item in ("name", "version", "license_file", "publisher", "script", "icon"):
                    if item not in appl:
                        self.cleanexit(4, "Missing " + item + " in " + cat)

                    if item == "name":
                        if "name" not in mhobject:
                            self.cleanexit(4, "Missing name in " + mhconfig)
                        self.name = mhobject["name"]
                        outtext += "name=" + mhobject["name"] + "\n"

                    elif item == "version":
                        if "version" not in mhobject:
                            self.cleanexit(4, "Missing version in " + mhconfig)
                        outtext += "version=" + ".".join([str(num) for num in mhobject["version"]]) + "\n"

                    elif item == "publisher":
                        if "copyright" not in mhobject:
                            self.cleanexit(4, "Missing copyright in " + mhconfig)
                        outtext += "publisher=" + mhobject["copyright"] + "\n"

                    elif item == "license_file":
                        license_file = os.path.basename(appl[item])
                        self.copyfile(appl[item], os.path.join(self.pynsistdir, license_file))
                        outtext += item + "=" + license_file + "\n"

                    elif item == "icon":
                        self.icon = os.path.basename(appl[item])
                        self.copyfile(appl[item], os.path.join(self.pynsistdir, self.icon))
                        outtext += item + "=" + self.icon + "\n"

                    elif item == "script":
                        self.script = os.path.basename(appl[item])
                        self.copyfile(appl[item], os.path.join(self.pynsistdir, self.script))
                        outtext += item + "=" + self.script + "\n"

                    else:
                        outtext += item + "=" + appl[item] + "\n"

            elif cat == "Python":
                pyth = pynsist["Python"]
                for item in ("version", "bitness", "format"):
                    if item not in pyth:
                        self.cleanexit(4, "Missing " + item + " in " + cat)
                    outtext += item + "=" + str(pyth[item]) + "\n"

            elif cat == "Include":
                incl = pynsist["Include"]
                for item in ("packages", "pypi_wheels", "files"):
                    if item == "pypi_wheels":
                        outtext += "pypi_wheels="
                        for elem in incl["pypi_wheels"]:
                            outtext += " " + elem + "==" + incl["pypi_wheels"][elem] + "\n"
                    elif item == "packages":
                        outtext += "packages="
                        for elem in incl["packages"]:
                            outtext += " " + elem + "\n"
                    elif item == "files":
                        outtext += "\nfiles= "
                        for elem in incl["files"]:
                            if elem == "_REPODIR_":
                                outtext += json_object["reponame"] + "\n"
                            else:
                                outtext += elem + "\n"
        return outtext

    def copyRepo(self):
        source = ".."
        l = len(source)

        self.mkdir(self.repodir)

        for root, dirs, files in os.walk(source, topdown=True):
            if root.startswith(source):
                destdir = os.path.join(self.repodir, root[l+1:])

            for elem in dirs:
                dontcreate = False
                for pat in self.ignoredirs:
                    if re.match(pat, elem):
                        dontcreate = True

                if not dontcreate:
                    self.mkdir(os.path.join(destdir, elem))

            if os.path.isdir(destdir):
                for elem in files:
                    dontcreate = False
                    for pat in self.ignorefiles:
                        if re.match(pat, elem):
                            dontcreate = True

                    if not dontcreate:
                        self.copyfile(os.path.join(root, elem), os.path.join(destdir, elem))

    def compileMeshCall(self, mesh, filename):
        if self.verbose:
            print ("+ calling compile_meshes.py " + mesh + " " + filename)
        try:
            subprocess.call(["./compile_meshes.py", "-b", mesh, "-f", filename], cwd="..")
        except Exception as e:
            self.cleanexit (20, "compile_meshes " + mesh + " " + filename + " failed!")

    def compileAssets(self):
        """
        compile base meshes and assets
        """
        basedirs = os.path.join(self.repodir, "data", "base")
        for base in os.listdir(basedirs):
            fname = os.path.join(basedirs, base, "base.obj")
            self.compileMeshCall(base, fname)

            for folder in ["clothes", "eyebrows", "eyelashes", "eyes", "hair", "proxy", "teeth", "tongue"]:
                absfolder = os.path.join(self.repodir, "data", folder, base)
                if os.path.isdir(absfolder):
                    for root, dirs, files in os.walk(absfolder, topdown=True):
                        for name in files:
                            if name.endswith(".mhclo") or name.endswith(".proxy"):
                                fname = os.path.join(root, name)
                                self.compileMeshCall(base, fname)


    def modifyInstaller(self):
        """
        replace the shortcut
        """
        if self.verbose:
            print ("+ placing desktop shortcut in installer.nsi")
        shortcut = '    CreateShortCut "$DESKTOP\\' + self.name + \
            '.lnk" "$INSTDIR\Python\python.exe" \'"$INSTDIR\\' + self.script + '"\' "$INSTDIR\\' + self.icon + '"\n\n'

        delshortcut = '     Delete "$DESKTOP\MakeHuman II.lnk"\n'

        with open(self.nsifile, 'r') as ifile:
            data = ifile.readlines()

        added = 0
        with open(self.nsifile, 'w') as ifile:
            for l in data:
                if added == 1:
                    added = 2
                    continue
                if "%HOMEDRIVE%\%HOMEPATH%" in l:
                    ifile.write( "  SetOutPath \"$INSTDIR\"\n")
                elif added == 0 and "CreateShortCut" in l:
                    ifile.write(shortcut)
                    if l.endswith("\\\n"):
                        added = 1
                    else:
                        added = 2
                elif ".lnk" in l:
                    ifile.write(delshortcut)
                else:
                    ifile.write(l)

    def pynsistCall(self):
        if self.verbose:
            print ("+ calling pynsist self.pynsistcfg")
        try:
            subprocess.call(["pynsist", "--no-makensis", self.pynsistcfg], cwd=self.pynsistdir)
        except Exception as e:
            self.cleanexit (10, "pynsist --no-makensis " + self.pynsistcfg + " failed!")

    def makensisCall(self):
        if self.verbose:
            print ("+ calling makensis")
        try:
            subprocess.call([self.makensis, self.nsifile], cwd=self.pynsistdir)
        except Exception as e:
            self.cleanexit (11, self.makensis + " " + self.nsifile + " failed!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("builddir", type=str, nargs='?',
            help="where to build the package, default is an autogenerated temporary directory")
    parser.add_argument("--verbose", "-v", action='store_true',  help="verbose")

    args = parser.parse_args()
    if not args.builddir:
        args.builddir = tempfile.gettempdir()
    if args.verbose:
        print ("+ working with " + args.builddir)

    wb = winBuilder(args.builddir, "./build.json", args.verbose)
    outtext = wb.evaluatePynsistCfg()
    wb.createPynsistCfg(outtext)
    wb.copyRepo()
    wb.compileAssets()
    wb.pynsistCall()
    wb.modifyInstaller()
    wb.makensisCall()

exit(0)
