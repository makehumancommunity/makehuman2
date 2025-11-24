"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MakeHumanModel
    * loadEquipment
    * baseClass
"""

import os
from core.target import Targets
from core.attached_asset import attachedAsset
from obj3d.object3d import object3d
from obj3d.skeleton import skeleton
from obj3d.animation import BVH, MHPose, PosePrims, MHPoseFaceConverter
from core.debug import memInfo, dumper
from core.target import Modelling
from gui.common import WorkerThread, ErrorBox

class MakeHumanModel():
    def __init__(self):
        self.name = None
        self.author = "unknown"
        self.uuid = None
        self.version = None
        self.skinMaterial = None
        self.skeleton = None
        self.modifiers = []
        self.attached = []
        self.materials = []
        self.tags = []

    def __str__(self):
        return dumper(self)

class loadEquipment():
    """
    class to hold equipment while loading mhm to calculate absolute pathes and materials
    """
    def __init__(self, eqtype, name, uuid, path, materialpath, relmaterial):
        self.type =  eqtype
        self.name =  name
        self.uuid =  uuid
        self.path =  path
        self.material =  materialpath
        self.relmaterial =  relmaterial

    def __str__(self):
        return dumper(self)

class baseClass():
    """
    get the environment for a base
    """
    def __init__(self, glob, name):
        self.env = glob.env
        self.glob = glob
        self.baseMesh = None
        self.baseInfo = None
        self.attachedAssets = []
        self.env.logLine(2, "New baseClass: " + name)
        self.env.basename = name
        self.name = name                # will hold the character name
        self.pose_skeleton = None
        self.default_skeleton = None
        self.floorCalcMethod = 0
        self.reset()
        memInfo()

    def __str__(self):
        return(dumper(self))

    def reset(self):
        self.skinMaterialName = None
        self.skinMaterial = None
        self.proxy = None
        self.tags = [] 
        self.photo = None
        self.author = "unknown"
        self.uuid = None
        self.skeleton = None
        self.in_posemode = False
        self.pose_skelpath = None
        self.bvh = None             # indicates that object is posed
        self.posemodifier = None    # indicates that posemodifiers are used
        self.expression = None      # indicates that expressions are used
        self.faceunits  = None      # indicates that face-units are initalized
        self.faceposes = []
        self.bodyunits  = None      # indicates that body-units are initalized
        self.faceunitsinfo  = None  # contains link to face-units dictionary
        self.bodyunitsinfo  = None  # contains link to body-units dictionary
        self.posecorrections = {}   # value of pose corections for body and face
        self.positioncorrection = [0.0, 0.0, 0.0]
        self.bodyposes = []
        self.hide_verts = True      # hide vertices
        self.getFaceUnits()         # get face-units to use the bone mask
        self.getBodyUnits()         # get body-units to use the bone mask

    def setPoseMode(self):
        self.baseMesh.createWCopy()
        self.restPose()
        self.precalculateAssetsInRestPose()
        self.pose_skeleton.newGeometry()
        gl = self.glob.openGLWindow
        gl.scene.prepareSkeleton(True)
        gl.Tweak()
        self.in_posemode = True

    def setStandardMode(self):
        self.baseMesh.resetFromCopy()
        self.restPose()
        self.updateAttachedAssets()
        self.in_posemode = False
        if self.pose_skeleton is not None:
            self.pose_skeleton.useOffset(False)
        gl = self.glob.openGLWindow
        gl.scene.prepareSkeleton(False)
        gl.scene.newFloorPosition(posed=False)
        gl.Tweak()

    def loadMHMFile(self, filename, verbose=None):
        """
        will usually load an mhm-file
        after load all filenames are absolute paths
        :param str filename: name of the file
        :param verbose: pointer to output messages
        """

        self.env.logLine(8, "Load: " + filename)
        try:
            fp = open(filename, "r", encoding="utf-8", errors='ignore')
        except IOError as err:
            return (False, str(err))

        self.attachedAssets = []
        self.baseMesh.setNoPose()

        if verbose is not None:
            verbose.setLabelText("Load " + filename)

        loaded = MakeHumanModel()
        for line in fp:
            words = line.split()

            # skip white space and comments
            #
            if len(words) == 0 or words[0].startswith('#'):
                continue

            key = words[0]
            if key in ["version", "uuid", "skinMaterial", "skeleton"]:
                setattr (loaded, key, words[1])
            elif key == "name":
                loaded.name = " ".join(words[1:])
            elif key == "author":
                loaded.author = " ".join(words[1:])
            elif key == "tags":
                loaded.tags = " ".join(words[1:]).split(";")
            elif key == "modifier":
                loaded.modifiers.append(" ".join(words[1:]))
            elif key == "material":
                loaded.materials.append([words[1],  words[2], words[3]])
            elif key in ["clothes", "eyebrows", "eyelashes", "eyes", "hair", "teeth", "tongue", "proxy"]:

                # attached assets consists of name, type and uuid (material)
                #
                loaded.attached.append(loadEquipment(key, words[1], words[2], None, None, None))
            else:
                print (key + " is still unknown")

        fp.close()

        # get filename via mapping and connect relative material path to attached assets
        # set used assets in mapping
        #
        self.glob.noAssetsUsed()
        for elem in loaded.attached:
            found = False
            for mapping in self.glob.cachedInfo:
                if elem.name == mapping.name and elem.uuid == mapping.uuid:
                    elem.path = mapping.path
                    mapping.used = True
                    found = True

            # try without uuid
            #
            if found is False:
                for mapping in self.glob.cachedInfo:
                    if elem.name == mapping.name:
                        elem.path = mapping.path
                        mapping.used = True
                        self.env.logLine(8, elem.name  + " fallback used, uuid does not match")

            for mat in loaded.materials:
                if mat[0] == elem.name and mat[1] == elem.uuid:
                    elem.relmaterial = mat[2]
                    break

        del loaded.materials

        # set absolute path for material
        #
        for elem in loaded.attached:
            # print (self.env.basename, elem.type, elem.name, elem.relmaterial, elem.path)
            if elem.path is None:
                self.env.logLine(8, elem.name  + " no path avialable")
            elif elem.relmaterial is not None:
                matfilename = self.env.existFileInBaseFolder(self.env.basename, elem.type, elem.path, elem.relmaterial)
                if matfilename is not None:
                    elem.material = matfilename
                else:
                    self.env.logLine(8, elem.relmaterial  + " not found")

        if loaded.name is not None:
            self.name = loaded.name
        self.tags = loaded.tags
        self.uuid = loaded.uuid
        if loaded.author is not None:
            self.author = loaded.author

        if loaded.skinMaterial is not None:
            self.skinMaterialName = loaded.skinMaterial
            matfilename = self.baseMesh.getMaterialPath(self.skinMaterialName)  # different method (check in "skins")
            if matfilename is not None:
                self.baseMesh.loadMaterial(matfilename)
                self.skinMaterial = matfilename
                if verbose is not None:
                    verbose.setLabelText("Load " + matfilename)
            else:
                self.env.logLine(8, self.skinMaterialName + " not found")

        # print(loaded)

        # now load attached meshes
        #
        for elem in loaded.attached:
            if elem.path is not None:
                if verbose is not None:
                    verbose.setLabelText("Attach " + elem.path)
                self.addAsset(elem.path, elem.type, elem.material, elem.relmaterial)
            else:
                self.env.logLine(8, "Cannot attach " + elem.name)

        # reset all targets and mesh, reset missing targets
        #
        self.glob.Targets.reset()
        self.glob.missingTargets = []
        for elem in loaded.modifiers:
            name, value = elem.split()
            self.glob.Targets.setTargetByName(name, value)

        if verbose is not None:
            verbose.setLabelText("Apply Targets")
        self.applyAllTargets()

        # skeleton after applying targets
        #
        if loaded.skeleton is not None:
            skelpath = self.env.existDataFile("rigs", self.env.basename, loaded.skeleton)
            if skelpath is not None:
                if self.pose_skelpath == skelpath:  # reuse pose-skeleton
                    self.skeleton = self.pose_skeleton
                    self.glob.markAssetByFileName(skelpath, True)
                else:
                    if verbose is not None:
                        verbose.setLabelText("Load: " + skelpath)
                    self.skeleton = skeleton(self.glob, loaded.skeleton)
                    if self.skeleton.loadJSON(skelpath):
                        self.glob.markAssetByFileName(skelpath, True)
                    else:
                        self.skeleton = None

        # recalculate pose-skeleton
        #
        if self.pose_skeleton is not None:
            self.pose_skeleton.newGeometry()

        # finally mark MHM as used
        #
        self.glob.markAssetByFileName(filename, True)
        return (True, "okay")

    def loadMHMTargetsOnly(self, filename, mode):
        """
        :param str filename: name of the file
        :param int mode: 1 = load only targets, 2 = load only head-targets
        """

        # head targets will be ignored if no head-groups are mentioned
        #
        if "head-pattern" not in self.baseInfo:
            mode = 1

        modifiers = []
        self.env.logLine(8, "Load targets only: " + filename)
        try:
            fp = open(filename, "r", encoding="utf-8", errors='ignore')
        except IOError as err:
            return (False, str(err))

        self.baseMesh.setNoPose()
        for line in fp:
            words = line.split()

            # skip white space and comments
            #
            if len(words) == 0 or words[0].startswith('#'):
                continue

            key = words[0]
            if key == "modifier":
                modifiers.append(" ".join(words[1:]))
        fp.close()

        if mode == 1:
            self.glob.Targets.reset()
        else:
            self.glob.Targets.resetHead()

        self.glob.missingTargets = []
        for elem in modifiers:
            name, value = elem.split()
            if mode == 1:
                self.glob.Targets.setTargetByName(name, value)
            else:
                if self.glob.Targets.isHeadTarget(name):
                    self.glob.Targets.setTargetByName(name, value)

        self.applyAllTargets()

        # recalculate pose-skeleton
        #
        if self.pose_skeleton is not None:
            self.pose_skeleton.newGeometry()

    def saveMHMFile(self, filename):
        """
        self the MHM file and keep names in UNIX encoding
        """

        self.env.logLine(8, "Save: " + filename)
        try:
            fp = open(filename, "w", encoding="utf-8", errors='ignore')
        except IOError as err:
            self.env.last_error = str(err)
            return (False)

        # create version as string, name from self.name or filename
        #
        vers = ".".join(map(str,self.env.release_info["version"]))
        name = self.name if  self.name != "" else os.path.split(filename[:-4])[-1]

        fp.write("# MakeHuman2 Model File\nversion v" + vers + "\nname " + name + "\nauthor " + self.author + "\n")

        # tags and uuid if available
        #
        if self.uuid is not None and self.uuid != "":
            fp.write ("uuid " + self.uuid + "\n")
        if len(self.tags) > 0:
            fp.write ("tags " + ";".join(self.tags) + "\n")

        # write targets
        #
        if self.glob.Targets is not None:
            for target in self.glob.Targets.modelling_targets:
                if target.value != target.default and target.pattern != "None":
                    fp.write ("modifier " + target.pattern + " " + str(round(target.value / 100, 6)) + "\n")

        # assets
        #
        for elem in self.attachedAssets:
            fp.write (elem.type + " " + elem.name + " " +  elem.uuid + "\n")

        # skinmaterial
        if self.skinMaterialName:
            matpath = self.env.formatPath(self.skinMaterialName)
            fp.write ("skinMaterial " + matpath + "\n")

        # materials (elem.materialsource is None if material is unchanged, so no save)
        #
        for elem in self.attachedAssets:
            if  elem.materialsource is not None:
                matpath = self.env.formatPath(elem.materialsource)
                fp.write ("material " + elem.name + " " +  elem.uuid + " " + matpath + "\n")
 
        # skeleton
        #
        if self.skeleton is not None:
            fp.write ("skeleton " + os.path.basename(self.skeleton.filename) + "\n")

        fp.close()
        return (True)

    def calculateDeletedVerts(self):
        if self.hide_verts is False:
            for elem in self.attachedAssets:
                elem.obj.notHidden()
            self.baseMesh.notHidden()
            return

        verts = None
        for elem in reversed(self.attachedAssets):
            if elem.deleteVerts is not None:
                if verts is None:
                    self.env.logLine(2, "DelVerts, First: " + elem.name)
                    verts = elem.deleteVerts.copy()
                    elem.obj.notHidden()
                else:
                    self.env.logLine(2, "DelVerts, new delete verts: " + elem.name)
                    elem.obj.hideApproxVertices(elem, self.baseMesh, verts)
                    verts |= elem.deleteVerts
            else:
                if verts is not None:
                    self.env.logLine(2, "DelVerts, no new delete verts: " + elem.name)
                    elem.obj.hideApproxVertices(elem, self.baseMesh, verts)
                else:
                    elem.obj.notHidden()

        # start with base mesh only
        #
        if verts is None:
            self.baseMesh.notHidden()
        else:
            self.baseMesh.hideVertices(verts)

    def setNoPose(self):
        self.baseMesh.setNoPose()
        for elem in (self.attachedAssets):
            elem.obj.setNoPose()

    def recalcLowestPosePos(self):
        self.baseMesh.precalculatePosedDimension()
        for elem in (self.attachedAssets):
            elem.obj.precalculatePosedDimension()

    def getLowestPos(self, posed=False):
        """
        lowest position of whole character for exports and grid
        """
        lowest = self.baseMesh.getLowestPos(posed)
        for elem in (self.attachedAssets):
            m = elem.obj.getLowestPos(posed)
            if m < lowest:
                lowest = m
        return(lowest)

    def isLinkedByFilename(self, filename):
        elem = self.getAttachedByFilename(filename)
        if elem is not None:
            return (elem)
        if self.bvh:
            if filename == self.bvh.filename:
                return (self.bvh)
        if self.posemodifier:
            if filename == self.posemodifier.filename:
                return (self.posemodifier)
        if self.expression:
            if filename == self.expression.filename:
                return (self.expression)
        if self.skeleton:
            if filename == self.skeleton.filename:
                return (self.skeleton)
        return(None)

    def getAttachedByFilename(self, filename):
        for elem in self.attachedAssets:
            if elem.filename == filename:
                return(elem)
        return (None)

    def countAttachedByType(self, itype):
        cnt = 0
        for elem in self.attachedAssets:
            if elem.type == itype:
                cnt += 1
        return (cnt)

    def delAsset(self, filename):
        elem = self.getAttachedByFilename(filename)
        if elem is None:
            return

        self.glob.openGLWindow.deleteObject(elem.obj, delproxymat=True)
        self.glob.openGLWindow.Tweak()
        self.attachedAssets.remove(elem)
        self.glob.markAssetByFileName(filename, False)

        if elem.deleteVerts is not None or elem.type == "proxy":
            self.env.logLine(2, "DelAsset, need to recalculate base and other meshes because vertices are visible again")
            self.calculateDeletedVerts()
            if elem.type == "proxy":
                self.proxy  = None

    def addAsset(self, path, eqtype, materialpath=None, materialsource=None):
        # print ("Attach: " + path + " of " + eqtype)
        attach = attachedAsset(self.glob, eqtype)
        (res, err) = attach.load(path)
        if res == 0:
            ErrorBox(self.glob.centralWidget, err)
            return (None)
        if res == 1:
            ErrorBox(self.glob.centralWidget, err)

        self.glob.markAssetByFileName(path, True)
        if eqtype == "proxy":
            attach.material = self.skinMaterial
            attach.materialsource = materialsource
            self.proxy = True
        elif materialpath is not None:
            attach.material = materialpath
            attach.materialsource = materialsource
        if attach.material is not None:
            attach.obj.loadMaterial(attach.material)

        if eqtype != "proxy":           # TODO check if correct her
            attach.createScaleMatrix(self.baseMesh)

        # insert according to z-depth
        cnt = 0
        for elem in self.attachedAssets:
            if attach.z_depth < elem.z_depth:
                break
            cnt += 1
        self.attachedAssets.insert(cnt, attach)

        # do that always?
        #if attach.deleteVerts is not None:
        self.calculateDeletedVerts()

        return(attach)


    def addAndDisplayAsset(self, path, eqtype, multi):
        """
        attach an asset and propagate to OpenGL
        """
        # avoid same asset (should not happen)
        #
        if self.getAttachedByFilename(path) is not None:
            return

        if multi is False:
            for elem in self.attachedAssets:
                if elem.type == eqtype:
                    self.env.logLine(2, "Unconnect asset: " + elem.filename)
                    self.delAsset(elem.filename)

        asset = self.addAsset(path, eqtype)
        if asset is not None:
            asset.obj.approxToBasemesh(asset, self.baseMesh)
            self.glob.openGLWindow.createObject(asset.obj)
            self.glob.openGLWindow.Tweak()

    def addSkeleton(self, name, path):
        """
        first delete old skeleton, then add new one
        """
        if self.skeleton is not None:
            self.glob.markAssetByFileName(self.skeleton.filename, False)
            self.glob.openGLWindow.scene.delSkeleton()

        # reuse pose-skeleton in case of identical selection
        if self.pose_skelpath == path:
            self.skeleton = self.pose_skeleton
            self.glob.markAssetByFileName(path, True)
        else:
            self.skeleton = skeleton(self.glob, name)
            if self.skeleton.loadJSON(path):
                self.glob.markAssetByFileName(path, True)
            else:
                self.skeleton = None
        self.glob.openGLWindow.scene.prepareSkeleton()
        self.glob.midColumn.setSizeInfo()

    def delSkeleton(self, path):
        self.skeleton = None
        self.glob.markAssetByFileName(path, False)
        self.glob.openGLWindow.scene.prepareSkeleton()
        self.glob.openGLWindow.Tweak()
        self.glob.midColumn.setSizeInfo()

    def restPose(self):
        self.pose_skeleton.restPose()

    def showPose(self):
        if self.bvh:
            self.pose_skeleton.pose(self.bvh.joints, self.bvh.currentFrame)
            #self.bvh.debugChanged(self.bvh.currentFrame)
        elif self.posemodifier:
            self.showPoseModifiers()
        self.glob.openGLWindow.Tweak()

    def showExpression(self):
        self.pose_skeleton.posebyBlends(self.expression.blends, self.faceunits.bonemask )

    def showPoseModifiers(self):
        self.pose_skeleton.posebyBlends(self.posemodifier.blends, self.bodyunits.bonemask )

    def showPoseAndExpression(self):
        if self.bvh:
            self.pose_skeleton.pose(self.bvh.joints, self.bvh.currentFrame)
        elif self.posemodifier:
            self.restPose()
            self.showPoseModifiers()
        if self.expression:
            self.showExpression()

    def addPose(self, name, path):
        if self.pose_skeleton is None:
            return True

        # reset poses
        #
        if self.bvh is not None:
            self.restPose()
            self.glob.markAssetByFileName(self.bvh.filename, False)
            self.bvh = None

        if self.posemodifier is not None:
            self.restPose()
            self.glob.markAssetByFileName(self.posemodifier.filename, False)
            self.posemodifier = None

        mtype = "mhpose" if path.endswith(".mhpose") else "bvh"
        if mtype == "bvh":
            self.bvh = BVH(self.glob, name)
            loaded  = self.bvh.load(path)
            if not loaded:
                self.env.logLine(1, "BVH: " + path + " " + self.env.last_error)
            else:
                self.showPoseAndExpression()
                self.glob.markAssetByFileName(path, True)
                self.recalcLowestPosePos()
                self.glob.openGLWindow.scene.newFloorPosition(posed=True)
            return loaded

        if self.getBodyUnits() is None:
           return False

        self.posemodifier = MHPose(self.glob, self.bodyunits, name)
        loaded, msg  = self.posemodifier.load(path)
        if not loaded:
            self.env.logLine(1, "mhpose: " + path + " " + msg)
        else:
            self.showPoseAndExpression()
            self.glob.markAssetByFileName(path, True)
            self.recalcLowestPosePos()
            self.glob.openGLWindow.scene.newFloorPosition(posed=True)
        return loaded

    def delPose(self, path):
        """
        set bvh and posemodifier to none
        """
        self.bvh = None
        self.posemodifier = None
        self.glob.markAssetByFileName(path, False)
        self.restPose()
        self.showPoseAndExpression()
        self.setNoPose()
        self.glob.openGLWindow.scene.newFloorPosition()
        self.glob.openGLWindow.Tweak()

    def getFaceUnits(self):
        if self.faceunits is None:
            m = PosePrims(self.glob)
            loaded, msg = m.load("face-poses.json")
            if not loaded:
                self.env.logLine(1, "faceUnits: " + msg)
                return None
            self.faceunits = m
            self.faceunitsinfo = m.getInfo()
        return self.faceunits

    def getBodyUnits(self):
        if self.bodyunits is None:
            m = PosePrims(self.glob)
            loaded, msg = m.load("body-poses.json")
            if not loaded:
                self.env.logLine(1, "bodyUnits: " + msg)
                return None
            self.bodyunits = m
            self.bodyunitsinfo = m.getInfo()
        return self.bodyunits
 
    def addExpression(self, name, path):
        if self.pose_skeleton is None:
            return

        if self.getFaceUnits() is None:
           return

        if self.expression is not None:
            self.glob.markAssetByFileName(self.expression.filename, False)
            self.restPose()

        self.expression = MHPose(self.glob, self.faceunits, name)
        converter = MHPoseFaceConverter()
        loaded, msg  = self.expression.load(path, converter.convert)
        if not loaded:
            self.env.logLine(1, "mhpose: " + path + " " + msg)
        else:
            self.showPoseAndExpression()
            self.glob.markAssetByFileName(path, True)

    def delExpression(self, path):
        self.expression = None
        self.glob.markAssetByFileName(path, False)
        self.restPose()
        self.showPoseAndExpression()
        self.glob.openGLWindow.Tweak()

    def prepareClass(self, modelfile=None):
        self.env.logLine(2, "Prepare class called with: " + self.env.basename)

        okay = self.glob.generateBaseSubDirs(self.env.basename)
        if not okay:
            self.env.logLine(1, self.env.last_error )
            return (False)

        filename = self.env.existDataFile("base", self.env.basename, "base.json")
        self.baseInfo = self.env.readJSON(filename)
        if self.baseInfo is None:
            self.env.logLine(1, self.env.last_error )
            return (False)
        self.env.initFileCache()

        name = self.env.existDataFile("base", self.env.basename, "base.obj")

        self.baseMesh = object3d(self.glob, self.baseInfo, "base")
        (res, err) = self.baseMesh.load(name)
        if res == 0:
            del self.baseMesh
            self.baseMesh = None
            self.env.last_error = err
            self.env.logLine(1, err )
            return (False)

        if res == 1:
            self.env.last_error = err
            self.env.logLine(1, err )

        if self.glob.Targets is not None:
            self.glob.Targets.destroyTargets()

        if self.glob.baseClass is not None:
            self.env.logLine(2, "class before: " + str(self.glob.baseClass.baseMesh))
            self.glob.reset()
            del self.glob.baseClass
        self.glob.baseClass = self
        self.glob.rescanAssets()

        self.baseMesh.precalculateDimension()
        target = Targets(self.glob)
        target.loadTargets()
        self.attachedAssets = []

        # load preselected skeleton as pose-skeleton only
        #
        if "pose-skeleton" in self.baseInfo:
            skelname = self.baseInfo["pose-skeleton"]
            self.pose_skelpath = self.env.existDataFile("rigs", self.env.basename, skelname)
            if self.pose_skelpath is not None:
                self.pose_skeleton = skeleton(self.glob, skelname)
                if self.pose_skeleton.loadJSON(self.pose_skelpath):
                    self.default_skeleton = self.pose_skeleton
                else:
                    self.pose_skeleton = None

        # set here or/and in mhm
        #
        if "modifier-presets" in self.baseInfo:
            target.modifierPresets (self.baseInfo["modifier-presets"])
        
        self.glob.openGLBlock = True
        if modelfile is not None:
            self.loadMHMFile(modelfile)
        elif "mhm" in self.baseInfo:
            mhmfile = self.env.existDataFile("base", self.env.basename, self.baseInfo["mhm"])
            self.loadMHMFile(mhmfile)
        else:
            self.baseMesh.loadMaterial(None)
        self.glob.openGLBlock = False

        memInfo()
        return (True)

    def getInitialCopyForSlider(self, factor, decr, incr):
        """
        get initial atm is only need for base, because the rest is done identically
        """
        self.baseMesh.getInitialCopyForSlider(factor, decr, incr)

    def updateNormals(self):
        self.baseMesh.calcNormals()
        for asset in self.attachedAssets:
            asset.obj.calcNormals()

    def updateAttachedAssets(self):
        for asset in self.attachedAssets:
            asset.obj.approxToBasemesh(asset, self.baseMesh)

    def precalculateAssetsInRestPose(self):
        for asset in self.attachedAssets:
            asset.obj.precalculateApproxInRestPose(asset, self.baseMesh)

    def poseAttachedAssets(self):
        for asset in self.attachedAssets:
            if asset.bWeights is not None:
                self.pose_skeleton.skinMesh(asset.obj, asset.bWeights)
            else:
                asset.obj.approxToBasemesh(asset, self.baseMesh)

    def updateByTarget(self, factor, decr, incr):
        """
        update all meshes by target
        """
        self.baseMesh.updateByTarget(factor, decr, incr)
        self.updateAttachedAssets()

    def applyAllTargets(self, bckproc=None, args=None):
        """
        applies all targets and corrects attached assets
        """
        targets = self.glob.Targets.modelling_targets
        self.baseMesh.resetToNonMacroTargets()

        if self.glob.targetMacros is not None:
            #
            # TODO: this dummy class method is not that good 
            #
            mo = Modelling(self.glob, "dummy", None)
            mo.macroCalculationLoad()
        self.updateAttachedAssets()


    def finishApply(self):
        if self.pose_skeleton is not None:
            self.pose_skeleton.newGeometry()
        self.glob.openGLWindow.Tweak()
        self.glob.midColumn.setSizeInfo()
        self.glob.parallel = None

    def parApplyTargets(self):
        """
        background process for applyAllTargets
        """
        if self.glob.parallel is None:
            self.glob.parallel = WorkerThread(self.applyAllTargets, None)
            self.glob.parallel.start()
            self.glob.parallel.finished.connect(self.finishApply)

    def nonParApplyTargets(self):
        """
        non graphical process for API
        """
        self.applyAllTargets()
        if self.pose_skeleton is not None:
            self.pose_skeleton.newGeometry()
        self.glob.midColumn.setSizeInfo()

    def __del__(self):
        self.env.logLine (4, " -- __del__ baseClass " + self.name)
