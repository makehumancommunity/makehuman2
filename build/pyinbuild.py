#!/usr/bin/python3
"""
build a pyinstaller version
"""

import os
import re
import shutil
import sys
import json
import argparse
import tempfile
import subprocess
import time
from datetime import datetime

class pyInstall():
    def __init__(self, tmp, path, verbose, pyname):
        self.tmp = tmp
        self.conf = path
        self.verbose= verbose
        self.pyinstdir = None
        self.pyname = "python3" if pyname is None else pyname
        self.reponame = None
        self.name = None
        self.datadir = None
        self.ignoredirs = []
        self.ignorefiles = []
        self.remove_ascii_targets = False
        self.remove_ascii_meshes = False
        self.isWindows = False
        #
        # get installer path according to OS
        #
        if sys.platform.startswith('win'):
            # get windows version
            self.isWindows = True
   

    def cleanexit(self, num, text):
        print (text)
        exit(num)

    def substitute(self, intext):
        return re.sub(r'[^a-zA-Z0-9\._]', '_', intext)

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

    def removeOldFolder(self):
        if os.path.isdir(self.pyinstdir):
            if self.verbose:
                print ("need to remove " + self.pyinstdir)
            shutil.rmtree(self.pyinstdir)

    def copyfile(self, source, dest):
        if self.verbose:
            print ("+ copy " + source + " to " + dest)
        try:
            shutil.copyfile(source, dest)
        except OSError as error:
            self.cleanexit(2, str(error))

    def evaluateCfg(self):
        json_object = self.readJSON(self.conf)
        if self.verbose:
            print ("+ evaluate " + self.conf)

        if "pyinstdir" not in json_object:
            self.cleanexit(3, "Missing 'pyinstdir' in " + self.conf)
        self.pyinstdir = os.path.join(self.tmp, json_object["pyinstdir"])

        self.removeOldFolder()
        if "reponame" not in json_object:
            self.cleanexit(3, "Missing 'reponame' in " + self.conf)
        self.repodir = os.path.join(self.pyinstdir, json_object["reponame"])
        self.distdir = os.path.join(self.repodir, "dist", "makehuman")
        self.datadir = os.path.join(self.distdir, "data")

        if "ignoredirs" in json_object:
            self.ignoredirs = json_object["ignoredirs"]

        if "ignorepyinstdirs" in json_object:
            self.ignorepyinstdirs = json_object["ignorepyinstdirs"]

        if "ignorefiles" in json_object:
            self.ignorefiles = json_object["ignorefiles"]

        if "mhconfigfile" not in json_object:
            self.cleanexit(3, "Missing 'mhconfigfile' in " + self.conf)

        self.mkdir(self.pyinstdir)

        mhconfig = json_object["mhconfigfile"]
        mhobject = self.readJSON(mhconfig)

        if "remove_ascii_targets" in json_object:
            self.remove_ascii_targets = json_object["remove_ascii_targets"]
        if "remove_ascii_meshes" in json_object:
            self.remove_ascii_meshes = json_object["remove_ascii_meshes"]

        return

    def copyProg(self):
        source = ".."
        l = len(source)

        self.mkdir(self.repodir)
     
        for root, dirs, files in os.walk(source, topdown=True):
            if root.startswith(source):
                destdir = os.path.join(self.repodir, root[l+1:])

            for elem in dirs:
                dontcreate = False
                for pat in self.ignorepyinstdirs:
                    if re.match(pat, elem):
                        dontcreate = True

                if not dontcreate:
                    if os.path.isdir(destdir):
                        self.mkdir(os.path.join(destdir, elem))

            if os.path.isdir(destdir):
                for elem in files:
                    if elem.endswith(".py"):
                        self.copyfile(os.path.join(root, elem), os.path.join(destdir, elem))

             
    def copyRepo(self):
        source = os.path.join("..", "data")
        l = len(source)

        self.mkdir(self.datadir)
    
        for root, dirs, files in os.walk(source, topdown=True):
            if root.startswith(source):
                destdir = os.path.join(self.datadir, root[l+1:])

            for elem in dirs:
                dontcreate = False
                for pat in self.ignoredirs:
                    if re.match(pat, elem):
                        dontcreate = True

                if not dontcreate:
                    if os.path.isdir(destdir):
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
            if self.isWindows:
                subprocess.call([self.pyname, "./compile_meshes.py", "-b", mesh, "-f", filename], cwd="..")
            else:
                subprocess.call(["./compile_meshes.py", "-b", mesh, "-f", filename], cwd="..")
        except Exception as e:
            self.cleanexit (20, "compile_meshes " + mesh + " " + filename + " failed!")

    def compileAssets(self):
        """
        compile base meshes and assets
        """
        basedirs = os.path.join(self.datadir, "base")
        for base in os.listdir(basedirs):

            # handle the base
            #
            fname = os.path.join(basedirs, base, "base.obj")
            self.compileMeshCall(base, fname)
            if self.remove_ascii_meshes:
                if self.verbose:
                    print ("delete", fname)
                os.remove(fname)

            for folder in ["clothes", "eyebrows", "eyelashes", "eyes", "hair", "proxy", "teeth", "tongue"]:
                absfolder = os.path.join(self.datadir, folder, base)
                if os.path.isdir(absfolder):
                    for root, dirs, files in os.walk(absfolder, topdown=True):
                        for name in files:
                            if name.endswith(".mhclo") or name.endswith(".proxy"):
                                fname = os.path.join(root, name)
                                self.compileMeshCall(base, fname)
                                if self.remove_ascii_meshes:
                                    if self.verbose:
                                        print ("delete", fname)
                                    os.remove(fname)
                                    obj = os.path.splitext(fname)[0] + ".obj"
                                    if self.verbose:
                                        print ("delete", obj)
                                    os.remove(obj)


    def compileTargetCall(self, filename):
        if self.verbose:
            print ("+ calling compile_targets.py " + filename)
        try:
            if self.isWindows:
                subprocess.call([self.pyname, "./compile_targets.py", "-f", filename], cwd="..")
            else:
                subprocess.call(["./compile_targets.py", "-f", filename], cwd="..")
        except Exception as e:
            self.cleanexit (20, "compile_target " + filename + " failed!")

    def compileTargets(self):
        """
        compile targets
        """
        basedirs = os.path.join(self.datadir, "target")
        for base in os.listdir(basedirs):
            fname = os.path.join(basedirs, base)
            self.compileTargetCall(fname)

    def removeASCIITargets(self):
        if self.remove_ascii_targets is False:
            return
        basedirs = os.path.join(self.datadir, "target")
        for base in os.listdir(basedirs):
            dname = os.path.join(basedirs, base)
            if self.verbose:
                print ("delete targets in " + dname)
            for root, dirs, files in os.walk(dname, topdown=True):
                for name in files:
                    if name.endswith(".target"):
                        fname = os.path.join(root, name)
                        os.remove(fname)

            walk = list(os.walk(dname))
            for path, _, _ in walk[::-1]:
                if len(os.listdir(path)) == 0:
                    os.rmdir(path)

    def pyinstCall(self):
        if self.verbose:
            print ("+ calling py PyInstaller")
        try:
            if self.isWindows:
                subprocess.call([self.pyname, "-m", "PyInstaller", "--noconsole", "makehuman.py"], cwd=self.repodir)
            else:
                subprocess.call(["pyinstaller", "makehuman.py"], cwd=self.repodir)
        except Exception as e:
            self.cleanexit (10, "PyInstaller failed!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create a pyInstaller packet. Make sure no extra directories are placed in parent, directories starting with '.' are skipped.")
    parser.add_argument("builddir", type=str, nargs='?',
            help="where to build the package, default is an autogenerated temporary directory")
    parser.add_argument("--verbose", "-v", action='store_true',  help="verbose")
    parser.add_argument("--pyname", "-P", type=str, help="Windows only: use a specific name for python3 (e.g. 'py')")

    args = parser.parse_args()
    if not args.builddir:
        args.builddir = tempfile.gettempdir()
    if args.verbose:
        print ("+ working with " + args.builddir)

    wb = pyInstall(args.builddir, "./build.json", args.verbose, args.pyname)
    wb.evaluateCfg()
    wb.copyProg()
    wb.pyinstCall()
    wb.copyRepo()
    wb.compileTargets()
    wb.removeASCIITargets()
    wb.compileAssets()


exit(0)
