#!/usr/bin/python3
import os
import json
import argparse
from core.importfiles import UserEnvironment, TargetASCII

if __name__ == '__main__':
    # get environment parameters (standardmesh)
    #
    dirname = os.path.abspath(os.path.dirname(__file__))
    os.chdir(dirname)
    systemhome = os.path.join(dirname,"data", "target")

    release_info = os.path.join("data", "makehuman2_version.json")
    if os.path.isfile(release_info):
        with open(release_info, 'r') as f:
            release = json.load(f)

    mesh  = release["standardmesh"]

    uenv = UserEnvironment()
    uenv.GetPlatform()
    conffile = uenv.GetUserConfigFilenames()[0]
    userspace = None
    if os.path.isfile(conffile):
        with open(conffile, 'r') as f:
            conf = json.load(f)
            userhome = os.path.join(conf["path_home"], "data")

    parser = argparse.ArgumentParser(description="Compile targets to binary form (usually works interactive)")
    parser.add_argument("base", type=str, nargs='?', help="if mentioned, targets of a different base mesh will be compiled, otherwise " + mesh)
    parser.add_argument("-s", action="store_true", help="compile system space targets")
    parser.add_argument("-f", "--file", type=str, help="compile only this file")
    if userhome is not None:
        parser.add_argument("-u", action="store_true", help="compile user space instead of system space")

    parser.add_argument("-n", action="store_true", help="compile non interactive")

    args = parser.parse_args()

    if args.file:
        at = TargetASCII()
        dest = os.path.join(args.file, "compressedtargets.npz")
        at.compressAllTargets(args.file, dest, 1)
        exit(0)

    space = None
    if args.u:
        if userspace is None:
            print ("No user space found")
            exit (2)
        space = userspace
    if args.s:
        space = systemspace

    if args.base:
        test = os.path.join(conf["path_home"], "data", "base", args.base)
        if not os.path.isdir(test):
            print (args.base + " demands a directory called " + test)
            print ("Directory does not exist, Aborted.")
            exit (20)
        mesh = args.base

    userspace = os.path.join(userhome, "target", mesh)
    userspace_con = os.path.join(userhome, "contarget", mesh)

    systemspace = os.path.join(systemhome, mesh)
    print (userspace, systemspace)
    # no decision, ask user
    #
    if space is None:
        print("[1] User   space: " + userspace)
        print("              + : " + userspace_con)
        print("\n[2] System space: " + systemspace)

        okay = False
        while not okay:
            line = input('\nEnter 1, 2 or a to abort: ')
            if line == "a":
                exit (0)
            if line == "1":
                space = [userspace, userspace_con]
                okay = True
            if line == "2":
                space = [systemspace]
                okay = True

    for elem in space:
        print ("Compile targets in: " + elem)
        dest = os.path.join(elem, "compressedtargets.npz")
        print ("Destination file is: " + dest)
    if args.n is False:
        okay = False
        while not okay:
            line = input('Enter a to abort, c to compress: ')
            if line == "a":
                exit (0)
            if line == "c":
                okay = True

    for elem in space:
        at = TargetASCII()
        dest = os.path.join(elem, "compressedtargets.npz")
        at.compressAllTargets(elem, dest, 1)

