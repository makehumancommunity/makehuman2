#!/usr/bin/python3
"""
build a PPA version (not yet finished)
PPA: Personal Package Archive
"""

import os
import re
import shutil
import sys
import json
import argparse
import tempfile
import subprocess

class ppaBuilder():

    def __init__(self, tmp, path, verbose):
        self.tmp = tmp
        self.conf = path
        self.verbose= verbose
        self.ppadir = None
        self.reponame = None
        self.name = None
        self.applvers = None
        self.script = None
        self.icon = None
        self.ignoredirs = []
        self.ignorefiles = []
        self.remove_ascii_targets = False
        self.remove_ascii_meshes = False

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

    def copyfile(self, source, dest):
        if self.verbose:
            print ("+ copy " + source + " to " + dest)
        try:
            shutil.copyfile(source, dest)
        except OSError as error:
            self.cleanexit(2, str(error))

    def getDescription(self):
        out = ""
        try:
            with open(self.controldesc, 'r') as ifile:
                data = ifile.readlines()
        except:
            self.cleanexit (1, "Cannot open " + self.controldesc)

        l = 0
        for line in data:
            if line.startswith("<p>"):
                line = ".\n"
            line = re.sub("<.+?>", "", line)
            if l > 0:
                out += " " + line
            else:
                out += line
            l += 1
        return out

    def createControlFile(self, name):
        descr = self.getDescription()
        replaces = "" if self.replaces is None else "Replaces: " + self.replaces + "\n"
        text = f"""Section: graphics
Priority: optional
Homepage: {self.url_mhcommunity}
Package: {self.reponame}
Version: {self.applvers}
Maintainer: {self.maintainer}
Depends: {self.dependencies}
Suggests: blender
Provides: makehuman
{replaces}Architecture: all
Description: {descr}
        """
        with open(name, "w") as f:
            f.write(text)

    def createCopyrightFile(self, name):
        text= f"""Files: *
Copyright: {self.copyright}
License: {self.licensetext}
"""
        with open(name, "w") as f:
            f.write(text)

    def createRulesFile(self, name):
        text="#!/usr/bin/make -f\n\n%:\n\tdh $@\n"
        with open(name, "w") as f:
            f.write(text)

    def createFormatFile(self, folder, name):
        self.mkdir(folder)
        fname = os.path.join(folder, name)
        text = "3.0 (quilt)\n"
        with open(fname, "w") as f:
            f.write(text)

    def evaluateConfig(self):
        json_object = self.readJSON(self.conf)
        if self.verbose:
            print ("+ evaluate " + self.conf)

        if "ppadir" not in json_object:
            self.cleanexit(3, "Missing 'ppadir' in " + self.conf)
        self.ppadir = os.path.join(self.tmp, json_object["ppadir"])

        if "reponame" not in json_object:
            self.cleanexit(3, "Missing 'reponame' in " + self.conf)
        self.reponame = json_object["reponame"]
        self.repodir = os.path.join(self.ppadir, self.reponame)

        if "linux-dependencies" not in json_object:
            self.cleanexit(3, "Missing 'linux-dependencies' in " + self.conf)
        self.dependencies = json_object["linux-dependencies"]

        if "ppa-control-desc" not in json_object:
            self.cleanexit(3, "Missing 'ppa-control-desc' in " + self.conf)
        self.controldesc = json_object["ppa-control-desc"]

        if "ppa-replaces" not in json_object:
            self.cleanexit(3, "Missing 'ppa-replaces' in " + self.conf)
        self.replaces = json_object["ppa-replaces"]

        if "ignoredirs" in json_object:
            self.ignoredirs = json_object["ignoredirs"]

        if "ignorefiles" in json_object:
            self.ignorefiles = json_object["ignorefiles"]

        if "mhconfigfile" not in json_object:
            self.cleanexit(3, "Missing 'mhconfigfile' in " + self.conf)

        self.mkdir(self.ppadir)

        mhconfig = json_object["mhconfigfile"]
        mhobject = self.readJSON(mhconfig)

        if "name" not in mhobject:
            self.cleanexit(4, "Missing name in " + mhconfig)
        self.name = mhobject["name"]

        if "version" not in mhobject:
            self.cleanexit(4, "Missing version in " + mhconfig)
        self.applvers = ".".join([str(num) for num in mhobject["version"]])
        if "url_mhcommunity" not in mhobject:
            self.cleanexit(4, "Missing url_mhcommunity in " + mhconfig)
        self.url_mhcommunity = mhobject["url_mhcommunity"]

        if "maintainer" not in mhobject:
            self.cleanexit(4, "Missing maintainer in " + mhconfig)
        self.maintainer = mhobject["maintainer"]
        
        if "copyright" not in mhobject:
            self.cleanexit(4, "Missing copyright in " + mhconfig)
        self.copyright = mhobject["copyright"]

        if "url_license_code" not in mhobject:
            self.cleanexit(4, "Missing url_license_code in " + mhconfig)
        if "url_license_assets" not in mhobject:
            self.cleanexit(4, "Missing url_license_assets in " + mhconfig)

        self.licensetext = "AGPL-3+ with CC0 exception\n " + \
            mhobject["url_license_code"] + "\n " + mhobject["url_license_assets"]

        if "remove_ascii_targets" in json_object:
            self.remove_ascii_targets = json_object["remove_ascii_targets"]
        if "remove_ascii_meshes" in json_object:
            self.remove_ascii_meshes = json_object["remove_ascii_meshes"]

    def copyRepo(self):
        source = ".."
        l = len(source)

        repofolder = os.path.join(self.ppadir,self.reponame + "-" + self.applvers)
        self.mkdir(repofolder)
        debianfolder = os.path.join(repofolder, "debian")
        self.mkdir(debianfolder)
        self.createControlFile(os.path.join(debianfolder, "control"))
        self.createCopyrightFile(os.path.join(debianfolder, "copyright"))
        self.createRulesFile(os.path.join(debianfolder, "rules"))
        self.createFormatFile(os.path.join(debianfolder, "source"), "format")

        for root, dirs, files in os.walk(source, topdown=True):
            if root.startswith(source):
                destdir = os.path.join(repofolder, root[l+1:])

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

            # handle the base
            #
            fname = os.path.join(basedirs, base, "base.obj")
            self.compileMeshCall(base, fname)
            if self.remove_ascii_meshes:
                if self.verbose:
                    print ("delete", fname)
                os.remove(fname)

            for folder in ["clothes", "eyebrows", "eyelashes", "eyes", "hair", "proxy", "teeth", "tongue"]:
                absfolder = os.path.join(self.repodir, "data", folder, base)
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
            subprocess.call(["./compile_targets.py", "-f", filename], cwd="..")
        except Exception as e:
            self.cleanexit (20, "compile_target " + filename + " failed!")

    def compileTargets(self):
        """
        compile targets
        """
        basedirs = os.path.join(self.repodir, "data", "target")
        for base in os.listdir(basedirs):
            fname = os.path.join(basedirs, base)
            self.compileTargetCall(fname)

    def removeASCIITargets(self):
        if self.remove_ascii_targets is False:
            return
        basedirs = os.path.join(self.repodir, "data", "target")
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


if __name__ == '__main__':
    if not sys.platform.startswith('linux'):
        print ("script will only run on a linux system.")
        exit(-1)

    parser = argparse.ArgumentParser()
    parser.add_argument("builddir", type=str, nargs='?',
            help="where to build the package, default is an autogenerated temporary directory")
    parser.add_argument("--verbose", "-v", action='store_true',  help="verbose")

    args = parser.parse_args()
    if not args.builddir:
        args.builddir = tempfile.gettempdir()
    if args.verbose:
        print ("+ working with " + args.builddir)

    ppab = ppaBuilder(args.builddir, "./build.json", args.verbose)
    ppab.evaluateConfig()
    ppab.copyRepo()
    exit(21)
    """
    wb.compileTargets()
    wb.removeASCIITargets()
    wb.compileAssets()
    """

exit(0)
