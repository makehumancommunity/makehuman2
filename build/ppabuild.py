#!/usr/bin/python3
"""
build a PPA version
PPA: Personal Package Archive

A debian package is a Unix ar archive.
It includes two tar archives: one containing the control information and another with the program data to be installed.

ar -r xxx.deb debian-binary control.tar.xz data.tar.xz

The paths of the tar data-archive are starting like absolute paths + "." in front to make them relative
./usr/share/makehuman2

tar is done by:
tar -C dataworkdir -cJvf databuilddir/data.tar.xz .

In the control archive there are simply files (control, changelog, md5sums).

compression can be gz or xz
"""

import os
import re
import shutil
import sys
import json
import argparse
import hashlib
import tempfile
import subprocess
import time

class ppaBuilder():

    def __init__(self, tmp, path, verbose):
        self.tmp = tmp
        self.conf = path
        self.verbose= verbose
        self.ppadir = None
        self.ppadest = None
        self.ppalogo = None
        self.repofolder = None # root folder
        self.datatarfolder = None # top folder to create data.tar.xz
        self.debianfolder = None # top folder to create control.tar.xz
        self.linuxstarter = None
        self.desktopstarter = None
        self.builddir = None
        self.reponame = None
        self.name = None
        self.applvers = None
        self.headlinedesc = ""
        self.ignoredirs = []
        self.ignorefiles = []
        self.md5array = []
        self.remove_ascii_targets = False
        self.remove_ascii_meshes = False
        self.basepath = os.path.abspath(os.path.dirname(__file__))

    def cleanexit(self, num, text):
        print (text)
        exit(num)

    def removeOldFolder(self):
        if os.path.isdir(self.ppadir):
            if self.verbose:
                print ("need to remove " + self.ppadir)
            shutil.rmtree(self.ppadir)

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
                if line.strip():
                    out += " " + line
            else:
                self.headlinedesc = line.strip()
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
Description: {descr}"""
        with open(name, "w") as f:
            f.write(text)

    def createDebianBinary(self, folder, name):
        fname = os.path.join(folder, name)
        text = "2.0\n"
        with open(fname, "w") as f:
            f.write(text)

    def createDesktopFile(self, name):
        logo = os.path.join(self.ppadest, self.ppalogo)
        text = f"""[Desktop Entry]
Name={self.reponame} {self.applvers}
Comment={self.headlinedesc}
Exec={self.mh2start}
Terminal=false
Type=Application
Icon={logo}
Categories=Graphics"""
        with open(name, "w") as f:
            f.write(text)

    def createChangeLogFile(self, folder, name):
        rname = os.path.join(self.basepath, name)
        dname = os.path.join(folder, name)
        try:
            with open(rname, "r") as f:
                lines = f.readlines()
        except Exception as e:
            self.cleanexit (20, str(e))
        lines.append( " -- build: " + time.strftime('%a %d %b %Y, %I:%M%p') + "\n")
        with open(dname, "w") as f:
            for l in lines:
                f.write(l)

    def createMD5File(self, folder, name):
        fname = os.path.join(folder, name)
        with open(fname, "w") as f:
            for elem in self.md5array:
                f.write(elem)

    def evaluateConfig(self):
        json_object = self.readJSON(self.conf)
        if self.verbose:
            print ("+ evaluate " + self.conf)

        if "ppadir" not in json_object:
            self.cleanexit(3, "Missing 'ppadir' in " + self.conf)
        self.ppadir = os.path.join(self.tmp, json_object["ppadir"])

        self.removeOldFolder()

        if "reponame" not in json_object:
            self.cleanexit(3, "Missing 'reponame' in " + self.conf)
        self.reponame = json_object["reponame"]

        if "linux-dependencies" not in json_object:
            self.cleanexit(3, "Missing 'linux-dependencies' in " + self.conf)
        self.dependencies = ",".join(map(str, json_object["linux-dependencies"]))   # make a comma separated list

        if "ppa-control-desc" not in json_object:
            self.cleanexit(3, "Missing 'ppa-control-desc' in " + self.conf)
        self.controldesc = json_object["ppa-control-desc"]

        if "ppa-replaces" not in json_object:
            self.cleanexit(3, "Missing 'ppa-replaces' in " + self.conf)
        self.replaces = json_object["ppa-replaces"]

        if "ppa-destdir" not in json_object:
            self.cleanexit(3, "Missing 'ppa-destdir' in " + self.conf)
        self.ppadest = json_object["ppa-destdir"]

        if "ppa-logo" not in json_object:
            self.cleanexit(3, "Missing 'ppa-logo' in " + self.conf)
        self.ppalogo = json_object["ppa-logo"]

        if "ppa-desktopstarter" not in json_object:
            self.cleanexit(3, "Missing 'ppa-desktopstarter' in " + self.conf)
        self.ppadesk = json_object["ppa-desktopstarter"]

        if "makehuman2start" not in json_object:
            self.cleanexit(3, "Missing 'makehuman2start' in " + self.conf)
        self.mh2start = json_object["makehuman2start"]

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

        self.repofolder = os.path.join(self.ppadir,self.reponame + "-" + self.applvers)
        self.mkdir(self.repofolder)
        self.debianfolder = os.path.join(self.repofolder, "debian")
        self.mkdir(self.debianfolder)
        self.createControlFile(os.path.join(self.debianfolder, "control"))
        self.createChangeLogFile(self.debianfolder, "changelog")

        self.buildfolder = os.path.join(self.repofolder, "build")
        self.mkdir(self.buildfolder)
        self.createDebianBinary(self.buildfolder, "debian-binary")

        p = self.repofolder
        self.datatarfolder = p = os.path.join(p, "data")
        self.mkdir(p)

        for d in self.ppadest.split("/"):
            if d != "":
                p = os.path.join(p,d)
                self.mkdir(p)
        self.repodir = os.path.join(p, self.reponame)
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

        # create starter
        #
        p = self.datatarfolder
        for d in self.mh2start.split("/")[:-1]:
            if d != "":
                p = os.path.join(p,d)
                self.mkdir(p)
        sname = os.path.join(self.basepath, "linuxstart")
        self.linuxstarter = os.path.join(self.datatarfolder, self.mh2start[1:])
        self.copyfile(sname, self.linuxstarter)
        os.chmod(self.linuxstarter, 0o755)

        # create desktop starter
        #
        p = self.datatarfolder
        desk = os.path.join(self.ppadest, self.ppadesk)
        for d in desk.split("/")[:-1]:
            if d != "":
                p = os.path.join(p,d)
                self.mkdir(p)
        self.desktopstarter = os.path.join(self.datatarfolder, desk[1:])
        self.createDesktopFile(self.desktopstarter)

    def md5sum(self, fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def createMD5Sums(self):
        if self.verbose:
            print ("+ create md5sums of " + self.datatarfolder)

        l =len(self.datatarfolder) + 1

        # starter and desktop first
        #
        md5 = self.md5sum(self.linuxstarter)
        self.md5array.append (md5 + "  " + self.linuxstarter[l:] + "\n")

        md5 = self.md5sum(self.desktopstarter)
        self.md5array.append (md5 + "  " + self.desktopstarter[l:] + "\n")

        for root, dirs, files in os.walk(self.repodir, topdown=True):
            if len(dirs) == 0:
                for elem in files:
                    fname = os.path.join(root, elem)
                    md5 = self.md5sum(fname)
                    self.md5array.append (md5 + "  " + fname[l:] + "\n")
        self.createMD5File(self.debianfolder, "md5sums")

    def createDataTarBall(self):
        destination = os.path.join(self.buildfolder, "data.tar.xz")
        verbose = "-cJvf" if self.verbose else "-cJf"
        command = ["/bin/tar", "-C", self.datatarfolder, "--owner=0", "--group=0", verbose, destination, "."]
        if self.verbose:
            print ("+ create data tar ball of " + self.datatarfolder + " to " + destination)
        try:
            subprocess.call(command)
        except Exception as e:
            self.cleanexit (20, "tar command for data.tar.xz failed!")

    def createControlTarBall(self):
        files = os.listdir(self.debianfolder)
        destination = os.path.join(self.buildfolder, "control.tar.xz")
        verbose = "-cJvf" if self.verbose else "-cJf"
        command = ["/bin/tar", "--owner=0", "--group=0", verbose, destination]
        command.extend(files)
        if self.verbose:
            print ("+ create control tar ball of " + self.debianfolder + " to " + destination)
        try:
            subprocess.call(command, cwd=self.debianfolder)
        except Exception as e:
            self.cleanexit (20, "tar command for control.tar.xz failed!")

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

    def createDebArchive(self):
        
        # keep this order
        #
        files = ["debian-binary", "control.tar.xz", "data.tar.xz"]
        fnames = []
        for elem in files:
            fnames.append(os.path.join(self.buildfolder, elem))
        destination = os.path.join(self.repofolder, self.reponame + "_" + self.applvers + ".deb")
        command = ["/usr/bin/ar", "-r", destination]
        command.extend(fnames)
        if self.verbose:
            print ("+ create debian archive " + destination)
        try:
            subprocess.call(command)
        except Exception as e:
            self.cleanexit (20, "ar failed!")

if __name__ == '__main__':
    if not sys.platform.startswith('linux'):
        print ("script will only run on a linux system.")
        exit(-1)

    parser = argparse.ArgumentParser()
    parser.add_argument("builddir", type=str, nargs='?',
            help="where to build the package, default is an autogenerated temporary directory")
    parser.add_argument("--verbose", "-v", action='store_true',  help="verbose")
    parser.add_argument("--develop", "-d", action='store_true',  help="development version, no binary targets and meshes")

    args = parser.parse_args()
    if not args.builddir:
        args.builddir = tempfile.gettempdir()
    if args.verbose:
        print ("+ working with " + args.builddir)

    ppab = ppaBuilder(args.builddir, "./build.json", args.verbose)
    ppab.evaluateConfig()
    ppab.copyRepo()
    if not args.develop:
        ppab.compileTargets()
        ppab.removeASCIITargets()
        ppab.compileAssets()
    ppab.createMD5Sums()
    ppab.createDataTarBall()
    ppab.createControlTarBall()
    ppab.createDebArchive()

exit(0)
