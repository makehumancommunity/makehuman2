#!/usr/bin/python3
"""
getpackages.py fetches asset-packs from makehuman fileserver

all names will be found in data/makehuman2_version.json

which are:
    url_fileserver
    url_systemassets (list of dict)
    standardmesh

The destination where to put these files will be taken from either system path or user path_home.
"""

import os
import json
import argparse
from core.environ import UserEnvironment
from core.importfiles import AssetPack

global _LASTVAL

def printProgress(total, l):
    global _LASTVAL
    v = 80 if total == 0 else (l / total) * 80
    if v > _LASTVAL:
        print("*", end="",flush=True)
        _LASTVAL += 1

if __name__ == '__main__':

    # get urls + name of standard mesh
    #
    global _LASTVAL

    release_info = os.path.join("data", "makehuman2_version.json")
    if os.path.isfile(release_info):
        with open(release_info, 'r') as f:
            release = json.load(f)

    (server, mirror, assetpath, standardmesh)  = (release["url_fileserver"], release["url_mirrorserver"],
            release["url_systemassets"], release["standardmesh"])

    # get user data path (if available)
    #
    uenv = UserEnvironment()
    uenv.getPlatform()
    conffile = uenv.getUserConfigFilenames()[0]
    userspace = None
    if os.path.isfile(conffile):
        with open(conffile, 'r') as f:
            conf = json.load(f)
            userspace = os.path.join(conf["path_home"], "data")
    systemspace = os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")

    parser = argparse.ArgumentParser(description="Load packages from asset server " + server + " or mirror " + mirror)
    parser.add_argument("-s", action="store_true", help="store in system space")
    parser.add_argument("-n", action="store_true", help="do not overwrite existent assets")
    if userspace is not None:
        parser.add_argument("-u", action="store_true", help="store in user space instead of system space")

    args = parser.parse_args()

    space = None
    if args.u:
        if userspace is None:
            print ("No user space found")
            exit (2)
        space = userspace
    if args.s:
        space = systemspace

    if space is None:
        print("[1] User   space: " + userspace)
        print("[2] System space: " + systemspace)

        okay = False
        while not okay:
            line = input('Enter 1, 2 or a to abort: ')
            if line == "a":
                exit (0)
            if line == "1":
                space = userspace
                okay = True
            if line == "2":
                space = systemspace
                okay = True

    for descr in assetpath:
        dmesh = descr["base"]
        path =  descr["url"]
        mesh = dmesh if dmesh != "*" else standardmesh
        source  = server + "/" + path
        sourcem = mirror + "/" + path
        print ("Download from: " + source)
        print ("for mesh     : " + mesh)
        print ("to folder    : " + space)
        okay = False
        while not okay:
            line = input('Enter a to abort, d to download: ')
            if line == "a":
                exit (0)
            if line == "d":
                okay = True

        assets = AssetPack()
        tempdir =assets.tempDir()
        filename = os.path.split(path)[1]
        _LASTVAL = 0
        print ("-" * 80)
        (success, message) = assets.getAssetPack(source, tempdir, filename, unzip=True, responsefunc=printProgress)
        if not success:
            print (message)
            print ("Download from mirror (this takes forever, sorry):")
            print (sourcem)
            (success, message) = assets.getAssetPack(sourcem, tempdir, filename, unzip=True, responsefunc=printProgress)
            if not success:
                print ("Giving up, mirror does not get data")
                exit (20)

        assets.copyAssets(tempdir, space, mesh, replace=not args.n)
        assets.cleanupUnzip()

    exit(0)
