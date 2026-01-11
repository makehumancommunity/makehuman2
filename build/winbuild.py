#!/usr/bin/python3
"""
build a windows version (not yet finished)
"""

import os
import re
import shutil
import json
import argparse
import tempfile

class winBuilder():
    def __init__(self, tmp, path, verbose):
        self.tmp = tmp
        self.conf = path
        self.verbose= verbose
        self.pynsistcfg = None
        self.pynsistdir = None
        self.reponame = None
        self.ignoredirs = []
        self.ignorefiles = []

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
        self.mkdir(self.pynsistdir)
        path = os.path.join(self.pynsistdir, self.pynsistcfg)
        if self.verbose:
            print ("+ write config for pynsist to " + path)
        with open(path, "w") as tfile:
            print(text, file=tfile)

    def evaluatePynsistCfg(self):
        json_object = self.readJSON(self.conf)
        if self.verbose:
            print ("+ evaluate " + self.conf)

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
                for item in ("name", "version", "publisher", "script", "icon"):
                    if item not in appl:
                        self.cleanexit(4, "Missing " + item + " in " + cat)

                    if item == "name":
                        if "name" not in mhobject:
                            self.cleanexit(4, "Missing name in " + mhconfig)
                        outtext += "name=" + mhobject["name"] + "\n"

                    elif item == "version":
                        if "version" not in mhobject:
                            self.cleanexit(4, "Missing version in " + mhconfig)
                        outtext += "version=" + ".".join([str(num) for num in mhobject["version"]]) + "\n"

                    elif item == "publisher":
                        if "copyright" not in mhobject:
                            self.cleanexit(4, "Missing copyright in " + mhconfig)
                        outtext += "publisher=" + mhobject["copyright"] + "\n"

                    elif item == "icon":
                        icon = os.path.basename(appl[item])
                        self.copyfile(appl[item], os.path.join(self.pynsistdir, icon))
                        outtext += item + "=" + icon + "\n"

                    elif item == "script":
                        script = os.path.basename(appl[item])
                        self.copyfile(appl[item], os.path.join(self.pynsistdir, script))
                        outtext += item + "=" + script + "\n"

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
                        outtext += "pypi_wheels= "
                        for elem in incl["pypi_wheels"]:
                            outtext += elem + "==" + incl["pypi_wheels"][elem] + "\n"
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
            print (root, dirs, files)
            if root.startswith(source):
                destdir = os.path.join(self.repodir, root[l+1:])
            print (destdir)

            for elem in dirs:
                print (elem)
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

exit(0)
