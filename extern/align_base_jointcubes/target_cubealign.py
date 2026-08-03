#!/usr/bin/python3
"""
this script corrects the cubes of the targets of the mesh

geometry.json should be in "<basedir>/data/base/<type>/geometry.json"
(type is now always hm08, it is the same for fantasy, so it would work)

target_cubealign corrects all targets placed in a certain folder and puts them to /tmp in same structure

python3 target_cubealign.py  data/target/hm08
python3 target_cubealign.py -u ownuserroot data/target/hm08

would change all targets for hm08 ...

in the end copy base.obj to base folder
"""

import sys
import os
import json
import argparse

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

def getJoint(jointranges, ln):
    for key, val in jointranges.items():
        if val[0] <= ln <= val[1]:
            return key, val[0], val[1], val[2]
    return None, 0, 0, 0

def stringify(vector):
    x, y, z = vector
    x = str(round (x, 3))
    y = str(round (y, 3))
    z = str(round (z, 3))

    if x == "0.0" or x == "-0.0":
        x = "0"
    elif x.startswith("-0."):
        x = x.replace("-0", "-")
    elif x.startswith("0."):
        x = x.replace("0.", ".")

    if y == "0.0" or y == "-0.0":
        y = "0"
    elif y.startswith("-0."):
        y = y.replace("-0", "-")
    elif y.startswith("0."):
        y = y.replace("0.", ".")

    if z == "0.0" or z == "-0.0":
        z = "0"
    elif z.startswith("-0."):
        z = z.replace("-0", "-")
    elif z.startswith("0."):
        z = z.replace("0.", ".")

    if (not (x == "0" and y == "0" and z == "0")):
        return x + " " + y + " " + z

    return None


def printCube(fname, cube, num):
    for elem in cube:
        n = stringify(elem)
        if n is not None:
            print(str(num) + " " + stringify(elem), file=fname)
            print(str(num) + " " + stringify(elem))
        num += 1

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
    #print("---", median)

    for elem in cube:
        elem[:] = median[:]

def missingElems(key, diff, cube, where):
    print (key + ": add " + str(diff) + " missing elems " + where, file=sys.stderr)
    csize = 0
    while diff > 0:
        cube.append([0.0, 0.0, 0.0])
        csize += 1
        diff -= 1
    return csize

def correctTarget(targetfile, destfile):
    try:
        f = open(targetfile, 'r', encoding="utf-8")
    except IOError:
        print ("Cannot open file " + targetfile, file=sys.stderr)
        return False

    try:
        d = open(destfile, 'w', encoding="utf-8")
    except IOError:
        f.close()
        print ("Cannot open file " + destfile, file=sys.stderr)
        return False

    magic = "# Makehuman2 modified morph-target (joint-helper cubes aligned)"
    lastkey = None
    last = 0
    lsize = 0
    lstart = 0
    csize = 0
    # read lines

    l = f.readline()
    if l.startswith(magic):
        print (targetfile + " is already converted", file=sys.stderr)
        exit(10)
    else:
        print (magic, file=d)
        if not l.startswith("#"):
            f.seek(0)
    
    for line in f:
        line = line.rstrip()
        words = line.split()


        # print everything not starting with a digit to screen to keep comments
        #
        lwords = len(words) -1
        if lwords <= 0:
            print (line, file=d)
            continue

        ln = words[0]
        if not ln.isdigit():
            print (line, file=d)
            continue
        ln = int(ln)

        # this part now looks awful, since it must deal with missing vertices of the cubes
        # which can be in front, mid and at the end
        #
        if start <= ln <= end:
            key, v1, v2, size = getJoint(jointranges, ln)
            #print (key, v1, v2, size)
            if key != lastkey:
                if lastkey is not None:
                    if csize != 8:
                        diff = 8 - csize
                        if diff != 0:
                            csize += missingElems(lastkey, diff, cube, "at the end")
                    recalcCube (cube, lsize)
                    print (lastkey)
                    printCube(d, cube, lstart)
                # print ("new cube for " + key)
                lstart = v1
                lsize = size
                cube = []
                csize = 0
                if ln != v1:
                    diff = ln - v1
                    if diff != 0:
                        csize += missingElems(key, diff, cube, "in front")
                cube.append([float(words[1]), float(words[2]), float(words[3])])
                csize += 1
                lastkey = key
                last = ln
            else:
                diff = ln - last - 1
                if diff != 0:
                    csize += missingElems(lastkey, diff, cube, "in between")
                cube.append([float(words[1]), float(words[2]), float(words[3])])
                csize += 1
                last = ln
        else:
            # is there still a cube not written?
            #
            if csize != 0:
                diff = 8 - csize
                key, v1, v2, size = getJoint(jointranges, v1)
                if diff != 0:
                    missingElems(key, diff, cube, "at the end")
                recalcCube (cube, lsize)
                print (key)
                printCube(d, cube, lstart)
                csize = 0

            # this outputs all other lines
            #
            print (line, file=d)
        last = ln

    f.close()
    return True


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="change cubes in targets")
    parser.add_argument("--userroot", "-u", type=str, help="own user root")
    parser.add_argument("path", type=str, help="targetpath")
    parser.add_argument("target", nargs='?', type=str, help="only create one target. If omitted create all targets.")

    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    basepath = os.path.abspath(os.path.join(here, os.pardir, os.pardir))
    if args.userroot is not None:
        os.chdir(args.userroot)
    else:
        os.chdir(basepath)

    basepath = os.path.join(basepath, "data", "base")
    jsonobj = readJSON(os.path.join(basepath, "hm08", "geometry.json"))

    if jsonobj is None:
        exit(20)

    joints = jsonobj["geometry-ranges"]["helper-joints"]
    jointranges = jsonobj["joint-ranges"]

    start = joints[0]
    end = joints[1]
    print (start, end, file=sys.stderr)

    rpath = "/tmp/corrected"
    if not os.path.isdir(rpath):
       os.mkdir(rpath)

    l = len(args.path) + 1
    result = []
    for root, dirs, files in os.walk(args.path, topdown=True):
        for name in files:
            if name.endswith(".target"):
                fname = os.path.join(root, name)
                shortened = fname[l:]
                if args.target is None or args.target == shortened:
                    result.append((fname, shortened))

    for source, dest in result:
        if "/" in dest:
            path, fname = dest.split("/")
        dpath = os.path.join(rpath, path)
        fname = os.path.join(rpath, dest)
        if not os.path.isdir(dpath):
            os.mkdir(dpath)
        print(source, fname, file=sys.stderr)
        correctTarget(source, fname)
