#!/usr/bin/python3
"""
    adapt_morphs can be used to extend hm08 morphs (targets) to a new mesh, when parent mesh is a valid parameter
    in base.json of destination mesh. The program will change the additional helpers according to certain vertices
    defined in hm08_targets.json

    the example in extern/adapt_morph_fantasy is contained in data/base/fantasy folder when fantasy mesh is installed.

    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck
"""
import os
import json
import argparse
import numpy as np
import tempfile

os.environ['MAKEHUMAN2TOOL'] = str(True)

from core.environ import UserEnvironment
from obj3d.object3d import object3d
from core.importfiles import TargetASCII

#
# we need a dummy class for global containing the environment 
# and a logLine function provided in inside environment
#

class globalObjects():
    def __init__(self, env):
        self.env = env

class targetTrans():
    def __init__(self, spath, dpath, newmesh):
        self.stargetpath = spath
        if not os.path.isdir(dpath):
           os.mkdir(dpath)
        self.dtargetpath = os.path.join(dpath, newmesh)
        if not os.path.isdir(self.dtargetpath):
           os.mkdir(self.dtargetpath)
        self.target = None
        self.starget = None
        self.newlines = []

    def changed(self,  watch):
        for elem in watch:
            if elem in self.nums:
                return True
        return False

    def getTrans(self, source):
        if source not in self.nums:
            return ([0.0, 0.0, 0.0])

        i = self.nums.index(source)
        return self.data[i][1]

    def load(self, name):
        self.starget = name
        self.target = os.path.join(self.stargetpath, name)
        at = TargetASCII()
        print("Load: " + str(self.target))
        result, self.data = at.load(self.target)
        if not result:
            print ("Cannot open " + self.target)
            exit(23)
    
        # get a list of changed vertices
        #
        self.nums = [i[0] for i in self.data]

    def stringify(self, vector):
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


    def save(self, name):
        if name is None:
            (dirname, filename) = os.path.split(self.starget)
            dpath = os.path.join(self.dtargetpath, dirname)
            if not os.path.isdir(dpath):
                os.mkdir(dpath)
            name = os.path.join(dpath, filename)
        print ("Save: ", name)
        with open(name, 'w') as f:
            for elem, vector in self.data:
                m = self.stringify(vector)
                if m is not None:
                    f.write (str(elem) + " " + m + "\n")
            for elem, vector in self.newlines:
                m = self.stringify(vector)
                if m is not None:
                    f.write (str(elem) + " " + m + "\n")

    def calcDist(self, item, dst, dim, col, s1, s2):
        f = 1.0
        if item[dst] == 0:
            return f

        p1 = item[dim][0]
        p2 = item[dim][1]
        if p1 in self.nums:
            i = self.nums.index(p1)
            trans1 = self.data[i][1][col]
        else:
            return f
        if p2 in self.nums:
            i = self.nums.index(p2)
            trans2 = self.data[i][1][col]
        else:
            return f
        n1 = item[s1] + trans1
        n2 = item[s2] + trans2
        ndst = n2-n1
        f = ndst / item[dst]
        return f

    def append(self, base, vrange, origin, trans, fx, fy, fz):
        print ("        move by " + str(trans))
        print ("        factor " + key,fx, fy, fz)
        s, e = vrange
        # z is depth
        #
        for v in range (s, e+1):
            diff = base[v] - origin
            dx = diff[0] - (diff[0] * fx)
            dy = diff[1] - (diff[1] * fy)
            dz = diff[2] - (diff[2] * fz)
            self.newlines.append([v, (trans[0] -dx, trans[1] -dy, trans[2] - dz)])

def logLine(level, line):
    if level & 8:
        print (line)

def getBaseInfo(meshconf, param):
    if os.path.isfile(meshconf):
        try:
            with open(meshconf, 'r') as f:
                conf = json.load(f)
                if param not in conf:
                    return None
                return conf[param]
        except:
            print ("Cannot read " + meshconf)
            exit(21)
    else:
        print ("Cannot read " + meshconf)
        exit(21)


def loadBase(glob, name):
    basemesh = object3d(glob, None, "base")
    (res, err) = basemesh.load(name, True)
    if res == 0:
        print (err)
        exit(10)
    return basemesh

if __name__ == '__main__':
    # get predefined environment parameters (standardmesh)
    #

    release_info = os.path.join("data", "makehuman2_version.json")
    if os.path.isfile(release_info):
        with open(release_info, 'r') as f:
            release = json.load(f)


    uenv = UserEnvironment()
    uenv.getPlatform()
    #
    # now add a few additional environment variables
    #
    uenv.logLine = logLine                          # the function we supply directly
    uenv.verbose = 0                                # do not print comments from makehuman2
    uenv.basename = release["standardmesh"]         # the meshname


    conffile = uenv.getUserConfigFilenames()[0]
    userspace = None
    if os.path.isfile(conffile):
        with open(conffile, 'r') as f:
            conf = json.load(f)
            userspace = os.path.join(conf["path_home"], "data")

    systemspace = os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
    description="""Adapt targets. This scripts needs a json file 'hm08_target.json' to read from.
It must be placed in base folder of destination mesh. It also needs base.obj and base.json  in that
base folder. The hm08 base mesh and base.json file are also needed. It also needs the
makehuman2 config file to find home and user paths.

Be aware that also source targets of hm08 are needed.

Best is to install a version of destination mesh first and then overwrite these targets.
Without overwriting it writes to temporary folder.
""")
    parser.add_argument('-o', '--overwrite', action='store_true',  help="Overwrite destination.")
    parser.add_argument('-u', '--usertarget', action='store_true',  help="Create user targets.")
    parser.add_argument("base", type=str, help="new base mesh")
    parser.add_argument("target", nargs='?', type=str, help="only create one target. If omitted create all targets.")

    args = parser.parse_args()

    glob = globalObjects(uenv)

    meshconf = os.path.join(systemspace, "base", args.base, "base.json" )
    if not os.path.isfile(meshconf):
        meshconf = os.path.join(userspace, "base", args.base, "base.json" )
        if not os.path.isfile(meshconf):
            print ("No base.json for " + args.base + " found in:\n" + systemspace + " or " + userspace)
            exit(22)

    parentmesh = getBaseInfo(meshconf, "parentmesh")
    if parentmesh != "hm08":
        print ("'parentmesh must be defined in base.json of " +  args.base + " and must be 'hm08'")
        exit(19)
    print ("'parentmesh' of " +  args.base + " is " + parentmesh)

    targetconf = os.path.join(systemspace, "base", args.base, "hm08_target.json" )
    if not os.path.isfile(targetconf):
        targetconf = os.path.join(userspace, "base", args.base, "hm08_target.json" )
        if not os.path.isfile(targetconf):
            print ("No hm08_target.json for " + args.base + " found in:\n" + systemspace + " or " + userspace)
            exit(22)

    jtarg = None
    with open(targetconf, 'r') as f:
         jtarg = json.load(f)

    
    print ("Reading information of standardmesh: ", uenv.basename)

    # get number of vertices of standard basemesh
    #
    dirname = os.path.abspath(os.path.dirname(__file__))
    datahome = os.path.join(dirname,"data")
    meshconf = os.path.join(datahome, "base", uenv.basename, "base.json" )
    oldnumverts = getBaseInfo(meshconf, "numverts")
    if oldnumverts is None:
        print ("Numbers of vertices not found in " + meshconf)

    # load NEW base-mesh+helper unchanged in x-y-z representation
    #
    print ("Standard mesh contains " + str(oldnumverts) + " vertices.")
    destbase = os.path.join(userspace, "base", args.base, "base.obj" )

    destpath = tempfile.gettempdir()
    if args.overwrite:
        if args.usertarget:
            destpath = os.path.join(userspace, "target" )
        else:
            destpath = os.path.join(userspace, "contarget" )
        compressed = os.path.join(destpath, args.base, "compressedtargets.npz")
        if os.path.isfile(compressed):
            print ("delete compressed file.")
            os.remove(compressed)
    else:
        print ("create targets in: " + destpath)

    basemesh = loadBase(glob, destbase)
    c = basemesh.coord

    # calculate reference points  and coordinates of dest on mesh once
    #
    for key, item in jtarg.items():
        dest = item["dest"]
        jtarg[key]["origin"] = c[dest]
        jtarg[key]["watch"] = []
        jtarg[key]["watch"].append(jtarg[key]["source"])
        if len(item["horizontal"]) == 2:
            mi, ma  = item["horizontal"]
            s = c[ma]-c[mi]
            jtarg[key]["dstx"] = s[0]
            if jtarg[key]["dstx"] < 0:
                print ("Horizontal distance of " + key + "is negative")
                exit(10)
            jtarg[key]["sx1"] = c[mi][0]
            jtarg[key]["sx2"] = c[ma][0]
            jtarg[key]["watch"].append(mi)
            jtarg[key]["watch"].append(ma)
        else:
            jtarg[key]["dstx"] = 0

        if len(item["vertical"]) == 2:
            mi, ma = item["vertical"]
            s = c[ma]-c[mi]
            jtarg[key]["dstz"] = s[1]
            if jtarg[key]["dstz"] < 0:
                print ("Vertical distance of " + key + "is negative")
                exit(10)
            jtarg[key]["sz1"] = c[mi][1]   # z
            jtarg[key]["sz2"] = c[ma][1]
            jtarg[key]["watch"].append(mi)
            jtarg[key]["watch"].append(ma)
        else:
            jtarg[key]["dstz"] = 0

        z = item["depth"]
        if len(item["depth"]) == 2:
            mi, ma = item["depth"]
            s = c[mi]-c[ma]
            jtarg[key]["dsty"] = s[2]       # -y
            if jtarg[key]["dsty"] < 0:
                print ("Depth distance of " + key + "is negative")
                exit(10)
            jtarg[key]["sy1"] = c[mi][2]
            jtarg[key]["sy2"] = c[ma][2]
            jtarg[key]["watch"].append(mi)
            jtarg[key]["watch"].append(ma)
        else:
            jtarg[key]["dsty"] = 0

    #for key, item in jtarg.items():
    #   print(key, item)

    # scan source targets 
    #
    if args.usertarget:
        sourcetargetpath = os.path.join(userspace, "target", "hm08")
    else:
        sourcetargetpath = os.path.join(datahome, "target", "hm08")

    l = len(sourcetargetpath) + 1

    result = []
    for root, dirs, files in os.walk(sourcetargetpath, topdown=True):
        for name in files:
            if name.endswith(".target"):
                fname = os.path.join(root, name)
                shortened = fname[l:]
                if args.target is None or args.target == shortened:
                    result.append(shortened)

    if len(result) == 0:
        print ("No targets found.")
        if args.target is None:
            print ("Target name does not fit to any target.")
        exit (23)

    print (str(len(result)) + " targets to check.")

    for tname in result:
        tt = targetTrans(sourcetargetpath, destpath, args.base)
        tt.load(tname)

        helper_changed = False
        # for each new helper element
        #
        for key, item in jtarg.items():
            source = item["source"]

            # Test if source is changed
            #
            if tt.changed(item["watch"]):
                helper_changed = True

                # get transpose of submesh
                #
                trans = tt.getTrans(source)
                print ("      " + key + ":")

                # resize submesh
                #
                # calculate reference points on target, check availability, if not available factor is 1.0
                #
                fx = tt.calcDist(item, "dstx", "horizontal", 0, "sx1", "sx2")
                fy = tt.calcDist(item, "dstz", "vertical", 1, "sz1", "sz2")
                fz = tt.calcDist(item, "dsty", "depth", 2, "sy1", "sy2")

                if fx == 1.0 and fy == 1.0 and fz == 1.0 and trans[0] == 0.0 and trans[1] == 0.0 and trans[2] == 0.0:
                    print ("      Identity calculated.")
                else:
                    # depth factor must be negative
                    #
                    if fz == 1.0:
                        fz = -1.0
                    tt.append(basemesh.coord, item["vrange"], item["origin"], trans, fx, fy, -fz)
        if helper_changed is False:
            print ("      No change.")
        tt.save(None)

