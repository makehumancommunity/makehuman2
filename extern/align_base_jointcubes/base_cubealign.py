#!/usr/bin/python3
"""
this script corrects the cubes of a given basemesh

geometry.json should be in "<basedir>/data/base/<type>/geometry.json"
(type is now always hm08, it is the same for fantasy, so it would work)

Output is on screen, can be written to a file

python3 base_cubealign.py hm08  >/tmp/base.obj
python3 base_cubealign.py -u ownuserroot fantasy >/tmp/base.obj

in the end copy base.obj to base folder
"""

import argparse
import sys
import json
import os

def readJSON(path: str) -> dict:
    try:
        f = open(path, 'r', encoding='utf-8')
    except:
        print("Cannot read JSON " + path, file=sys.stderr)
        return None
    with f:
        try:
            json_object = json.load(f)
        except json.JSONDecodeError as e:
            print ("JSON format error in " + path + " > " + str(e), file=sys.stderr)
            return None
        if not json_object:
            print ("Empty JSON file " + path, file=sys.stderr)
            return None
    return json_object

def printJointName(jointranges, ln):
    for key, val in jointranges.items():
        if val[1] == ln:
            print (key, file=sys.stderr)
            return val[2]
    print ("None", file=sys.stderr)
    return 0

def printCube(cube):
    for elem in cube:
        print("v %.4f %.4f %.4f" % (elem[0], elem[1], elem[2]))

def recalcCube(cube, dist):
    # calculate median
    median = [0.0, 0.0, 0.0]
    for elem in cube:
        median[0] += elem[0]
        median[1] += elem[1]
        median[2] += elem[2]
    median[0] /= 8
    median[1] /= 8
    median[2] /= 8

    # precalculate all positions

    x0 = median[0] - dist
    x1 = median[0] + dist
    y0 = median[1] - dist
    y1 = median[1] + dist
    z0 = median[2] - dist
    z1 = median[2] + dist

    # new values according to index (done by blender)
    # [4, 0, 1, 5, 6, 2, 3, 7]
    cube[0] = [ x0, y0, z1]
    cube[1] = [ x0, y0, z0]
    cube[2] = [ x1, y0, z0]
    cube[3] = [ x1, y0, z1]
    cube[4] = [ x0, y1, z1]
    cube[5] = [ x0, y1, z0]
    cube[6] = [ x1, y1, z0]
    cube[7] = [ x1, y1, z1]

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Converts a base mesh to have aligned cubes for joint helpers")
    parser.add_argument("--userroot", "-u", type=str, help="own user root if base mesh is there")
    parser.add_argument("type", type=str, help="type of the mesh, e.g. hm08")

    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    basepath = os.path.abspath(os.path.join(here, os.pardir, os.pardir))

    magic = "# Makehuman2 modified basemesh (joint-helper cubes aligned) "

    # read geometry
    basepath = os.path.join(basepath, "data", "base")

    jsonobj = readJSON(os.path.join(basepath, "hm08", "geometry.json"))

    if jsonobj is None:
        exit(20)

    joints = jsonobj["geometry-ranges"]["helper-joints"]
    jointranges = jsonobj["joint-ranges"]

    start = joints[0]
    end = joints[1]
    print (start, end, file=sys.stderr)

    if args.userroot is not None:
        basefile = os.path.join(args.userroot, "data", "base", args.type, "base.obj")
    else:
        basefile = os.path.join(basepath, args.type, "base.obj")

    # read base
    try:
        f = open(basefile, 'r', encoding="utf-8")
    except IOError:
        print ("Cannot open file " + basefile, file=sys.stderr)

    ln = -1
    cc = 0
    cube = []
    # read lines
    l = f.readline()
    if l.startswith(magic):
        print (basefile + " is already converted", file=sys.stderr)
        exit(10)
    else:
        print (magic + args.type)
    for line in f:
        line = line.rstrip()
        words = line.split()

        lwords = len(words) -1
        if lwords <= 0:
            print (line)
            continue

        command = words[0]

        # when joint helper started
        if command == 'v':
            ln += 1
            if start <= ln <= end:
                cube.append([float(words[1]), float(words[2]), float(words[3])])
                cc += 1

                # get 8 elements
                if cc == 8:
                    size = printJointName(jointranges, ln)
                    #printCube(cube)
                    recalcCube (cube, size)
                    printCube(cube)
                    cc = 0
                    cube = []
            else:
                print (line)
                cc = 0
                cube = []
        else:
            print (line)

