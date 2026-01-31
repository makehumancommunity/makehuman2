"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MacroTree
    * Modelling
    * Morphtarget
    * Targets
"""

from gui.common import WorkerThread
from gui.slider import ScaleComboItem
from core.targetcat import TargetCategories
from core.importfiles import TargetASCII

import os
import sys
import json
import numpy as np

class MacroTree:
    def __init__(self):
        self.names = [ None, None, None ]
        self.values = [ 0.0, 0.0, 0.0 ]

    def insert(self, name, value):
        for i in range(0, 3):
            if self.names[i] is None:
                self.names[i] = name
                self.values[i] = value
                return

    def __str__(self):
        return (str(self.names) + " " + str(self.values))


class Modelling(ScaleComboItem):
    def __init__(self, glob, name, icon):

        super().__init__(name, icon)    # inherit attributs
        self.glob     = glob
        self.obj      = glob.baseClass

        self.group = ""     # no group
        self.incr = None    # target "incr"
        self.decr = None    # target "decr"
        self.macro = None   # macro target
        self.default = 0.0  # default value
        self.m_influence = []   # all influences
        self.barycentric = None # map slider
        self.opposite = True # change to True
        self.slider = None    # filled by function creating slider or mapslider
        self.sym = None       # symmetric side (left, right)
        self.isRSide = False    # bool for side
        self.measure = None     # is measurement needed?
        self.virtual_val = None # changed value by formula
        self.pattern = "None"

    def __str__(self):
        return (self.name + ": " + str(self.incr) + " | " + str(self.decr))

    def memInfo(self):
        if self.barycentric:
            text = ""
            value = "0"
            if isinstance(self.pattern, list):
                l = self.pattern
                text  = l[0]["name"] + " " + l[1]["name"] + " " + l[2]["name"]
                value = str(l[0]["value"] * 100) + " " + str(l[1]["value"] * 100) + "  " + str(l[2]["value"] * 100)
            t = [self.name, "barycentric", -1, "barycentric", -1, text, value]
        elif self.macro:
            t = [self.name, str(self.macro), -1, str(self.macro), -1, self.pattern, self.value]
        else:
            li = len(self.incr.verts) if self.incr else 0
            ld = len(self.decr.verts) if self.decr else 0
            t = [self.name, str(self.incr), li, str(self.decr), ld, self.pattern, self.value]
        return (t)

    def setFromDict(self, t, targetpath, bintargets):
        if "tip" in t:
            self.tip = t["tip"]
        if "decr" in t:
            self.decr = Morphtarget(self.glob.env, t["decr"])
            self.decr.loadTargetData(targetpath, bintargets)
        if "incr" in t:
            self.incr = Morphtarget(self.glob.env, t["incr"])
            self.incr.loadTargetData(targetpath, bintargets)
        if "rsym" in t:
            self.sym = t["rsym"]
            self.isRSide = False
        elif "lsym" in t:
            self.sym = t["lsym"]
            self.isRSide = True
        if "macro" in t:
            self.macro = t["macro"]
        if "macro_influence" in t:
            self.macro_influence(t["macro_influence"])
        if "barycentric" in t:
            self.macro_barycentric(t["barycentric"])
        if "barycentric_diffuse" in t:
            self.barycentric_diffuse = t["barycentric_diffuse"]
        if "name" in t:
            self.displayname = t["name"]
        if "group" in t:
            self.group = t["group"]
        if "measure" in t:
            self.measure = t["measure"]
        if "display" in t:
            self.textSlot(t["display"])
        if "default" in t:
            self.default = t["default"] * 100

    def macro_influence(self, array):
        #
        self.m_influence = []
        if self.glob.targetMacros is not None:
            cnt = len(self.glob.targetMacros["macrodef"])

            # test boundaries to avoid crashes
            #
            for elem in array:
                if elem < cnt:
                    self.m_influence.append(elem)

    def macro_barycentric(self, val):
        text = ["A", "B", "C"]
        value = [0.0, 0.0, 1.0]
        i = 0
        for x in val:
            text[i] = x.split("/")[1] if "/" in x else x
            i += 1
        self.barycentric = [
                {"name": val[0], "text": text[0], "value": value[0] },
                {"name": val[1], "text": text[1], "value": value[1] },
                {"name": val[2], "text": text[2], "value": value[2] } ]

    def resetValue(self):
        self.value = self.default
        if self.barycentric is not None:
            self.barycentric[0]["value"] = 0.33
            self.barycentric[1]["value"] = 0.33
            self.barycentric[2]["value"] = 0.34

    def set_barycentricFromMapSlider(self):
        val = self.slider.getValues()
        self.barycentric[0]["value"] = val[0]
        self.barycentric[1]["value"] = val[1]
        self.barycentric[2]["value"] = val[2]
        #
        # this is a dummy value for comparison when using parallel processing
        #
        self.value = int(val[0] * 100) * int(val[1] * 100) * int(val[2] * 100)

    def printSlot(self):
        val =self.value / 100
        x =eval(self.formula)
        self.virtual_value = x
        l = self.formatText.format(x)
        return(l)

    def textSlot(self, descr):
        num = descr["slot"]
        self.formatText = descr["text"]
        self.formula = descr["formula"]
        self.glob.setTextSlot(num, self.printSlot)

    def search_pattern(self, user):
        """
        creates a pattern to be found in the target repo,
        for macros it is of a different type
        dual targets will be referenced by dual patterns, the opposites are defined in base.json
        single targets will be referenced by just the name
        user targets will get a "custom/" in front
        """

        if self.barycentric:
            self.pattern = self.barycentric
            self.opposite = False
            return (self.pattern)
        if self.macro:
            self.pattern = self.macro
            self.opposite = False
            return (self.pattern)

        d = str(self.decr)
        i = str(self.incr)

        self.pattern = "None"
        if i == "None":
            return (self.pattern)

        # use target opposites to find pattern (from base.json)
        #
        if "target-opposites" in self.obj.baseInfo:
            test = self.obj.baseInfo["target-opposites"]
            for elem in test:
                if d.endswith("-" + elem) and i.endswith("-" + test[elem]):
                    self.pattern = d + "|" + test[elem]
                    break

        if self.pattern == "None":
            self.pattern = i
            self.opposite = False

        if user == 1:
            self.pattern = "custom/" + self.pattern
        return (self.pattern)

    def displayMeasurement(self, new=False):
        val, coords = self.obj.baseMesh.getMeasure(self.measure)
        if new:
            self.glob.openGLWindow.setMarker(coords)
        else:
            self.glob.openGLWindow.modMarker(coords)
        text = self.glob.env.toUnit(val, True)
        self.slider.setMeasurement(text)

    def initialize(self):
        factor = self.value / 100
        print("init  " + self.name)
        self.glob.openGLWindow.delMarker()
        if self.macro is not None:
            self.obj.baseMesh.resetToNonMacroTargets()
        elif self.incr is not None or self.decr is not None:
            self.obj.getInitialCopyForSlider(factor, self.decr, self.incr)
            if self.measure is not None:
                self.displayMeasurement(True)
            if self.glob.Targets.getSym() is True and self.sym is not None:
                if self.sym in self.glob.targetRepo:
                    key = self.glob.targetRepo[self.sym]
                    self.obj.getInitialCopyForSlider(key.value / 100, key.decr, key.incr)

    def generateAllMacroWeights(self, targetlist, macroname, factor, weights):
        """
        recursive function to generate weights.  Since for example 4 different components will change the character,
        one need to figure out how much each component will be used. Therefore one need to consider the components like a tree
        for the leaf the value itself is added, otherwise we do an recursion
        """
        if len(weights) > 0:
            for i in range(0,3):
                if  weights[0].names[i] is not None:
                    self.generateAllMacroWeights(targetlist, macroname + "-" +  weights[0].names[i], factor * weights[0].values[i], weights[1:])
        else:
            if factor > 0.01:
                targetlist.append ({"name": macroname[1:], "factor": factor})

    def macroCalculation(self, m_influence):
        macros = self.glob.targetMacros
        macrodef = macros["macrodef"]
        components = macros["components"]
        targetlist = []
        for l in m_influence:
            #print ("   " + macrodef[l]["name"])
            comps = macrodef[l]["comp"]
            weightarray = []
            for elem in comps:
                if elem in components:
                    pattern = components[elem]["pattern"]
                    values  = components[elem]["values"]
                    # print ("\t\tPattern:" +  str(pattern) + " " + str(values))

                    if "steps" not in components[elem]:

                        # extra for sum of sliders (human phenotype)
                        #
                        sum = components[elem]["sum"]
                        m = MacroTree()
                        for i,v in enumerate(values):
                            p = pattern +  sum[i]
                            if p not in self.glob.targetRepo:
                                continue
                            current = self.glob.targetRepo[p]
                            b = current.barycentric[i]["value"]
                            if b > 0.001:
                                # print ("\t\tCurrent value " + v + " " + str(b))
                                m.insert(v, b)
                        weightarray.append(m)
                    else:
                        steps = components[elem]["steps"]
                        if pattern not in self.glob.targetRepo:
                            continue
                        current = self.glob.targetRepo[pattern].value / 100
                        # print ("\t\tCurrent " + str(current) + " Divisions: " + str(len(steps)))

                        for i in range(0,len(steps)-1):
                            if current > steps[i+1]:
                                continue
                            else:
                                c = (current - steps[i]) / (steps[i+1] - steps[i])
                                m = MacroTree()
                                if c < 0.999:
                                    m.insert(values[i], 1-c)
                                if c > 0.001:
                                    m.insert(values[i+1], c)
                                weightarray.append(m)
                                break

            self.generateAllMacroWeights(targetlist, "", 1.0, weightarray)

        # The last step is the optimization: Some weightfiles are not existing.
        # So they would be a factor of 0. Sometimes targets are identical.
        # All targets are in memory and there are no duplicates. The calculated
        # target name will be mapped to the targets (using the value "t")
        # So it either add them the new targetname to a list or add the second factor if allready exists.

        sortedtargets = {}
        l = macros["targetlink"]

        for elem in targetlist:
            name = elem["name"]
            if name is not None:
                if name in l and l[name] is not None:
                    if l[name] in sortedtargets:
                        sortedtargets[l[name]] += elem["factor"]
                        #print(" Add: " + name)
                    else:
                        sortedtargets[l[name]] = elem["factor"]
                        #print(" New: " + name)
                else:
                    pass

        # add them to screen first
        #
        for elem in sortedtargets:
            if elem in self.glob.macroRepo:
                print ("  + " + str(round(sortedtargets[elem],2)) + " " + elem)
                self.obj.baseMesh.addTargetToMacroBuffer(sortedtargets[elem], self.glob.macroRepo[elem])
        self.obj.baseMesh.addMacroBuffer()

    def macroCalculationLoad(self):
        m = self.glob.targetMacros['macrodef']
        #
        # create all macros
        #
        m_influence = list(range(0,len(m)))
        self.obj.baseMesh.prepareMacroBuffer()
        self.macroCalculation(m_influence)

    def changeMacroTarget(self, bckproc, args):
        """
        change macros will run as a background process
        """
        self._last_value = self.value

        print (self.m_influence)
        m = self.glob.targetMacros['macrodef']
        m_influence = list(range(0,len(m)))
        self.macroCalculation(m_influence)
        self.obj.updateAttachedAssets()

    def setBaryCentricDiffuse(self):
        if hasattr(self, "barycentric_diffuse"):
            base = self.obj.baseMesh
            if base.openGL is not None and not hasattr(base.material, "diffuseTexture"):
                influence = [self.barycentric[0]["value"], self.barycentric[1]["value"], self.barycentric[2]["value"]]
                texture =base.material.mixColors(self.barycentric_diffuse, influence, self.obj.baseMesh)
                base.openGL.setTexture(texture)

    def postChange(self):
        """
        all actions after change:
        * change size
        * change skeleton
        * mark a change
        """
        self.glob.midColumn.setSizeInfo()
        bc = self.glob.baseClass
        if bc.skeleton is not None:
            bc.skeleton.newGeometry()
        elif bc.default_skeleton is not None:
            bc.default_skeleton.newGeometry()
        self.glob.project_changed = True


    def finished_bckproc(self):
        print ("done")
        self.glob.openGLWindow.Tweak()
        self.glob.parallel = None
        #
        # when still a difference exists, callback should start again

        if self.barycentric is not None:
            self.set_barycentricFromMapSlider()
            self.setBaryCentricDiffuse()

        if self.value != self._last_value:
            self.callback()
        else:
            self.postChange()

    def callback(self):
        """
        callback function, works different for macros (as a thread) and 
        """
        factor = self.value / 100
        if len(self.m_influence) > 0:
            print ("Macro change " +  str(self.m_influence))

            #
            # make sure background process runs only once

            if self.glob.parallel is None:
                #
                # special case barycentric, values will be fetched

                if self.barycentric is not None:
                    self.set_barycentricFromMapSlider()
                self.glob.parallel = WorkerThread(self.changeMacroTarget, None)
                self.glob.parallel.start()
                self.glob.parallel.finished.connect(self.finished_bckproc)

        elif self.incr is not None or self.decr is not None:
            # print("change " + self.name)
            self.obj.updateByTarget(factor, self.decr, self.incr)

            # in case symmetry is switched on, set sym-side + value
            #
            if self.glob.Targets.getSym() is True and self.sym is not None:
                if self.sym in self.glob.targetRepo:
                    key = self.glob.targetRepo[self.sym]
                    self.obj.updateByTarget(factor, key.decr, key.incr)
                    key.value = self.value
                else:
                    print ("Target missing")
            if self.measure is not None:
                self.displayMeasurement()
            self.postChange()
            self.glob.openGLWindow.Tweak()

    #def __del__(self):
    #    print (" -- __del__ Modelling: " + self.name)


class Morphtarget:
    """
    handle a single target
    """
    def __init__(self, env, name):
        self.name = name
        self.raw  = None
        self.verts= []
        self.data = []
        self.env  = env

    def __str__(self):
        return (self.name)

    def loadTargetData(self, path, bintargets=None):
        """
        get Target data either from pre-loaded npz file or from single targets
        """
        if bintargets is not None:
            if self.name in bintargets.files:
                self.env.logLine(8, "Use Data for " + self.name + " from binary file")
                self.raw = bintargets[self.name]
                self.verts = self.raw['index']
                self.data = self.raw['vector']
                return

        filename = os.path.join(path, self.name) + ".target"
        self.env.logLine(8, "Load: " + filename)

        ta = TargetASCII()
        (res, self.raw) = ta.load(filename)
        if res is False:
            self.env.logLine(1, "Cannot load:" + filename)
            return
        self.verts = self.raw['index']
        self.data = self.raw['vector']

    def releaseNumpy(self):
        if self.raw is not None:
            self.verts = None
            self.raw = None
            self.data = []

    def __del__(self):
        self.env.logLine(4, " -- __del__ Morphtarget: " + self.name)


class Targets:
    def __init__(self, glob):
        self.glob =glob
        self.env = glob.env
        self.modelling_targets = []
        glob.Targets = self
        self.collection = None
        self.macrodef = None
        self.target_sysindex = -1
        self.categories = None
        self.baseClass = glob.baseClass
        self.symmetry = False

        self.target_env = [ {
            "targetpath": self.env.stdSysPath("target"),
            "targets": None
            }, {
            "targetpath": self.env.stdUserPath("target"),
            "targets": None
            }, {
            "targetpath": self.env.stdUserPath("contarget"),
            "targets": None
        }]
        self.default_icon = os.path.join(self.env.path_sysicon, "empty_target.png")


    def __str__(self):
        return ("Target-Collection: " + str(self.collection))

    def getSym(self):
        return self.symmetry

    def setSym(self, value):
        print ("Set symmetry " + str(value))
        self.symmetry = value

    def makeSym(self, RtoL):
        if RtoL:
            print ("Make symmetry RToL")
        else:
            print ("Make symmetry LToR")

        for elem in self.modelling_targets:
            if elem.sym is not None and elem.isRSide is RtoL:
                if elem.sym in self.glob.targetRepo:
                    opp = self.glob.targetRepo[elem.sym]
                    if opp.value != elem.value:
                        opp.value = elem.value


    def loadModellingJSON(self):
        """
        load macro.json (if available) will be loaded first from contarget in user section, then from system path
        load modelling.json from contarget in user section, then from system path
        load additional flexible modelling.json from userpath
        """
        s_targetpath = self.env.stdSysPath("target")
        u_targetpath = self.env.stdUserPath("contarget")

        self.macrodef = self.env.readJSON(os.path.join(u_targetpath, "macro.json"))
        if self.macrodef is None:
            self.macrodef = self.env.readJSON(os.path.join(s_targetpath, "macro.json"))
            if self.macrodef is None:
                self.env.logLine(1, "No macros available")
            else:
                self.env.logLine(1, "Using system macros from " + s_targetpath)
            self.target_sysindex = 0
        else:
            self.env.logLine(1, "Using user macros from " + u_targetpath)
            self.target_sysindex = 2

        if self.macrodef is not None:
            l = self.macrodef["targetlink"] = {}
            if "macrodef" in self.macrodef:
                for mtype in self.macrodef["macrodef"]:
                    if "folder" in mtype:
                        folder = mtype["folder"]
                    if "targets" in mtype:
                        for elem in mtype["targets"]:
                            if "name" in elem and "t" in elem:
                                if elem["t"] is not None:
                                    l[elem["name"]] = folder + "/" + elem["t"]  # (need to be written this way for Windows)
                                else:
                                    l[elem["name"]] = None # to support empty or non-existent targets
                        mtype["targets"] = None  # no longer needed
            self.glob.targetMacros = self.macrodef

        # system and user modelling JSON files
        #
        targetjson = self.env.readJSON(os.path.join(u_targetpath, "modelling.json"))
        if targetjson is None:
            targetjson = self.env.readJSON(os.path.join(s_targetpath, "modelling.json"))
            self.env.logLine(1, "Using system modelling.json from " + s_targetpath)
        else:
            if targetjson is None:
                self.env.logLine(1, "No constant modelling.json file")
            else:
                self.env.logLine(1, "Using constant modelling.json from " + u_targetpath)

        targetpath = self.env.stdUserPath("target")
        userjson = self.env.readJSON(os.path.join(targetpath, "modelling.json"))

        if targetjson is None:
            self.env.logLine(1, "User only modelling.json")
            return (userjson)

        if userjson is not None:
            self.env.logLine(1, "Append user modelling.json")
            for elem in userjson:
                targetjson[elem] = userjson[elem]

        return (targetjson)

    def createTarget(self, name, t):
        """
        create a target either from system/user-contarget path or user path
        """
        mode = 1 if "user" in t else self.target_sysindex
        targetpath = self.target_env[mode]["targetpath"]
        bintargets = self.target_env[mode]["targets"]
        iconpath = os.path.join(targetpath, "icons")
        icon = os.path.join(iconpath, t["icon"]) if "icon" in t else self.default_icon

        m = Modelling(self.glob, name, icon)
        m.setFromDict(t, targetpath, bintargets)

        pattern = m.search_pattern(mode)
        if pattern != "None":
            if isinstance(pattern, list):
                for l in pattern:
                    self.glob.targetRepo[l["name"]] = m
            else:
                    self.glob.targetRepo[pattern] = m
        self.modelling_targets.append(m)


    def loadTargets(self):
        """
        loads target categories
        loads macros and modelling json files
        """
        self.collection = self.env.basename

        self.categories= TargetCategories(self.glob)
        self.categories.readFiles()

        targetjson = self.loadModellingJSON()
        if targetjson is None:
            self.env.logLine(1, self.env.last_error )
            return
       
        # load binary targets according to sysindex
        #
        ind = self.target_sysindex

        for i in (ind, 1):
            x = self.target_env[i]
            bintargets = os.path.join(x["targetpath"], "compressedtargets.npz")
            if os.path.exists(bintargets):
                self.env.logLine(8, "Load binary targets: " + bintargets)
                x["targets"] = np.load(bintargets)
            else:
                self.env.logLine(8, "Try to create binary targets: " + bintargets)
                ta = TargetASCII()
                if (ta.allowToWrite(bintargets)):
                    num = ta.compressAllTargets(x["targetpath"], bintargets, 0)
                    if num > 0:
                        self.env.logLine(8, str(num) + " targets compressed. Binary targets will be used on next restart")
                    else:
                        self.env.logLine(8, "No targets for " + bintargets)
                else:
                    self.env.logLine(8, "Writing binary targets: no permission")


        # load macrotargets, use folder, where the macro-defition was found
        #
        if self.macrodef is not None:
            for link in self.macrodef["targetlink"]:
                name = self.macrodef["targetlink"][link]
                if name is not None and name not in self.glob.macroRepo:
                    mt = Morphtarget(self.env, name)
                    mt.loadTargetData(self.target_env[ind]["targetpath"], self.target_env[ind]["targets"])
                    self.glob.macroRepo[name] = mt

        # load targets mentioned in modelling.json
        #
        for name, t in targetjson.items():
            self.createTarget(name, t)

    def saveBinaryTargets(self, bckproc, *args):
        """
        save targets as compressed binary (running as background command)
        also works for contargets
        :parm bck_proc: unused pointer to background process
        :param args: [0][0] 1 = system, 2 = user (3 is both)
        """
        # need to load all targets again
        #
        # TODO; check files ... refresh targets
    
        sys_user = args[0][0]
        ta = TargetASCII()
        if sys_user & 1:
            sourcefolder = self.env.stdSysPath("target")
            destfile = self.env.stdSysPath("target", "compressedtargets.npz")
            self.env.logLine (8, "Compress system targets in " + sourcefolder + " to "+  destfile)
            ta.compressAllTargets(sourcefolder, destfile)

        if sys_user & 2:
            sourcefolder = self.env.stdUserPath("target")
            destfile = self.env.stdUserPath("target", "compressedtargets.npz")
            self.env.logLine (8, "Compress user targets in " + sourcefolder + " to "+  destfile)
            ta.compressAllTargets(sourcefolder, destfile)
            if self.target_sysindex == 2:
                sourcefolder = self.env.stdUserPath("contarget")
                destfile = self.env.stdUserPath("contarget", "compressedtargets.npz")
                self.env.logLine (8, "Compress user constant targets in " + sourcefolder + " to "+  destfile)
                ta.compressAllTargets(sourcefolder, destfile)

    def setSkinDiffuseColor(self):
        for target in self.modelling_targets:
            if target.barycentric:
                target.setBaryCentricDiffuse()

    def reset(self, colors=False):
        for target in self.modelling_targets:
            target.resetValue()
        if colors is True:
            self.setSkinDiffuseColor()

    def isHeadPattern(self, pattern):
        headpattern = self.baseClass.baseInfo["head-pattern"]
        for t in headpattern:
            if pattern.startswith(t):
                return True
        return False

    def isHeadTarget(self, key):
        if key in self.glob.targetRepo:
            t = self.glob.targetRepo[key]
            if self.isHeadPattern(t.group):
                return True
        return False

    def resetHead(self):
        for target in self.modelling_targets:
            if self.isHeadPattern(target.group):
                target.resetValue()

    def setTargetByName(self, key, value):
        """
        set values
        """
        if key in self.glob.targetRepo:
            t = self.glob.targetRepo[key]
            if t.barycentric is not None:
                for l in t.barycentric:
                    if l["name"] == key:
                        l["value"] = float(value)
            else:
                t.value = float(value) * 100.0
        else:
            self.env.logLine (2, "Missing target:" + key)
            self.glob.missingTargets.append(key)

    def modifierPresets(self, presets):
        """
        set presets from base.json
        """
        for elem in presets:
            self.setTargetByName(elem, presets[elem])


    def destroyTargets(self):
        self.env.logLine (2, "destroy Targets:" + str(self.collection))

        for m in self.modelling_targets:
            if m.incr:
                m.incr.releaseNumpy()
            if m.decr:
                m.decr.releaseNumpy()

        self.modelling_targets = []

    def __del__(self):
        if self.collection is not None:
            self.env.logLine (4, " -- __del__ Targets: " + self.collection)

