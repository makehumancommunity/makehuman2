"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * referenceVerts
    * attachedAsset
"""

import os
import numpy as np
from core.debug import dumper
from obj3d.fops_binary import exportObj3dBinary, importObjValues
from obj3d.object3d  import object3d
from obj3d.bone import boneWeights

class referenceVerts:
    def __init__(self):
        pass

    def __str__(self):
        return("N:"+ str(self._verts) + " W:" + str(self._weights) + " O:" + str(self._offset))

    def identicalValue(self, words, vnum, vertWeights):
        v0 = int(words[0])
        self._verts = (v0,v0,v0)
        self._weights = (1.0,0.0,0.0)
        self._offset = np.zeros(3, float)
        if v0 in vertWeights:
            vertWeights[v0].append((vnum, 1))
        else:
            vertWeights[v0] = [(vnum,1)]
        return self

    def fromTriple(self, words, vnum, vertWeights):
        v0 = int(words[0])
        v1 = int(words[1])
        v2 = int(words[2])
        w0 = float(words[3])
        w1 = float(words[4])
        w2 = float(words[5])
        if len(words) > 6:
            d0 = float(words[6])
            d1 = float(words[7])
            d2 = float(words[8])
        else:
            (d0,d1,d2) = (0,0,0)

        self._verts = (v0,v1,v2)
        self._weights = (w0,w1,w2)
        self._offset = np.array((d0,d1,d2), float)

        if v0 in vertWeights:
            vertWeights[v0].append((vnum, w0))
        else:
            vertWeights[v0] = [(vnum,w0)]

        if v1 in vertWeights:
            vertWeights[v1].append((vnum, w1))
        else:
            vertWeights[v1] = [(vnum,w1)]

        if v2 in vertWeights:
            vertWeights[v2].append((vnum, w2))
        else:
            vertWeights[v2] = [(vnum,w2)]

        return self


class attachedAsset:
    """
    attached asset represents a mesh added to the base mesh
    num_base_verts is usually set when used from script
    """
    def __init__(self, glob, eqtype, num_base_verts=None):
        self.glob = glob
        self.env = glob.env
        self.type = eqtype          # asset type
        self.tags = []
        self.version = 110
        self.z_depth = 1 if eqtype == "proxy" else 50
        self.obj = None             # will contain the object3d class
        self.vertWeights = {}       # will contain the parent weight
        self.description = ""
        self.license = ""
        self.author = ""
        self.uuid = ""
        self.name = "generic"
        self.meshtype = self.env.basename  # for binary saving
        self.scaleMat = None            # numpy matrix for scaling -or - none

        # numpy arrays, scale (must be saved later in binary form)
        #
        self.scale = np.array([(0, 0, 0.), (0, 0, 0.), (0, 0, 0.)], dtype=[('v1', '<i4'), ('v2', '<i4'), ('dist', '<f4')])

        self.ref_vIdxs = None       # (Vidx1,Vidx2,Vidx3) list with references to human vertex indices, indexed by reference vert
        self.weights = None         # (w1,w2,w3) list, with weights per human vertex (mapped by ref_vIdxs), indexed by reference vert
        self.offsets = None         # (x,y,z) list of vertex offsets, indexed by reference vert
        self.deleteVerts = None     # will contain vertices to delete
        self.material = None        # path material, fully qualified
        self.standard_material = None # path material, fully qualified
        self.vertexboneweights_file = None # path to vbone file
        self.bWeights = None        # bone weights
        self.materialsource = None    # path material, relative
        if num_base_verts is None:
            self.base_verts = self.glob.baseClass.baseMesh.n_origverts
        else:
            self.base_verts = num_base_verts

    def __str__(self):
        return(dumper(self))

    def textLoad(self, filename):
        """
        will usually load an mhclo-file
        structure is a key/value system + rows of verts in the end
        """
        self.env.logLine(8, "Read ASCII asset " + filename)

        try:
            fp = open(filename, "r", encoding="utf-8", errors='ignore')
        except IOError as err:
            return (False, str(err))

        self.filename = filename
        #
        # status = 0, read normal
        #          1, read vertices
        #          2, read delete_verts
        #
        status = 0
        refVerts = [] # local reference for vertices
        vnum   = 0    # will contain the vertex number (counting from 0 to x)
        self.deleteVerts = np.zeros(self.base_verts, bool)

        for line in fp:
            words = line.split()

            # skip white space and comments
            #
            if len(words) == 0 or words[0].startswith('#'):
                continue

            key = words[0]
            key = key[:-1] if key.endswith(":") else key

            if key == "weights":
                fp.close()
                return(False, "weights in mhclo file no longer supported")

            if key == "verts":
                status = 1
                continue
            if key == "delete_verts":
                status = 2
                continue

            if status == 1:
                if key.isnumeric():
                    refVert = referenceVerts()
                    refVerts.append(refVert)
                    if len(words) == 1:
                        value = refVert.identicalValue(words, vnum, self.vertWeights)
                    else:
                        refVert.fromTriple(words, vnum, self.vertWeights)
                    vnum += 1
                    continue

            elif status == 2:

                # delete vertices
                #
                sequence = False
                for v in words:
                    if v == "-":
                        sequence = True
                    else:
                        v1 = int(v)
                        if sequence:
                            for vn in range(v0,v1+1):
                                self.deleteVerts[vn] = True
                            sequence = False
                        else:
                            self.deleteVerts[v1] = True
                        v0 = v1

                continue

            if len(words) < 2:
                continue

            if key in ["name", "uuid", "description", "author", "license", "homepage"]:
                setattr (self, key, " ".join(words[1:]))
            elif key == "tag":
                self.tags.append(" ".join(words[1:]).encode('ascii', 'ignore').lower().decode("utf-8"))
            elif key in ["obj_file", "material", "vertexboneweights_file"]:
                setattr (self, key, words[1])
            elif key in ["version", "z_depth"]:
                setattr (self, key, int(words[1]))

            elif key == 'x_scale':
                self.scale[0]  = self.getScaleData(words)
            elif key == 'y_scale':
                self.scale[1] = self.getScaleData(words)
            elif key == 'z_scale':
                self.scale[2] = self.getScaleData(words)

        fp.close()

        self.env.logLine(16, str(self))

        if self.obj_file is None:
            return(False, "Obj-File is missing")

        self.obj_file = os.path.join(os.path.dirname(filename), self.obj_file)
        if self.material is not None:
            self.standard_material = self.material
            self.material = os.path.normpath(os.path.join(os.path.dirname(filename), self.material))
        else:
            self.standard_material = ""

        self.env.logLine(16, "Material: " + str(self.material))


        # finally create the numpy arrays here
        #
        self.weights = np.asarray([v._weights for v in refVerts], dtype=np.float32)
        self.ref_vIdxs = np.asarray([v._verts for v in refVerts], dtype=np.uint32)
        self.offsets = np.asarray([v._offset for v in refVerts], dtype=np.float32)
        if self.type == "proxy":
            self.z_depth = 1

        # check valid scale matrix:
        if self.scale[0]['dist'] < 0.01 or self.scale[1]['dist'] < 0.01  or  self.scale[2]['dist'] < 0.01:
            self.scale = None

        return (True, "Okay")

    def createScaleMatrix(self, mesh):
        # 
        # try to work with None as well
        #
        if self.scale is None:
            self.env.logLine(16, "No scale matrix")
            self.scaleMat = None
            return
        self.scaleMat = np.identity(3, dtype=np.float32)

        for n in range(3):
            (v1, v2, div) = self.scale[n]
            pos1 = mesh.getPosition(v1)
            pos2 = mesh.getPosition(v2)
            self.scaleMat[n][n] = abs(pos1[n] - pos2[n]) / div

    def getScaleData(self, words):
        return ((int(words[1]), int(words[2]), float(words[3])))

    def importBinary(self, path):
        self.env.logLine(8, "Read binary asset " + path)
        npzfile = np.load(path)
        for elem in ['asset', 'files', 'ref_vIdxs', 'weights']:
            if elem not in npzfile:
                error =  "Malformed file, missing component " + elem
                return (False, error)

        # now get data from binary, asset
        #
        asset = list(npzfile['asset'][0])
        self.name        = asset[0].decode("utf-8")
        self.uuid        = asset[1].decode("utf-8")
        self.author      = asset[2].decode("utf-8")
        self.description = asset[3].decode("utf-8")
        self.meshtype    = asset[4].decode("utf-8")
        nrefverts        = asset[5]
        self.version     = asset[6]
        self.z_depth     = asset[7]
        self.license     = asset[8].decode("utf-8")
        self.tags        = asset[9].decode("utf-8").split("|")

        if nrefverts == 3 and 'offsets' not in npzfile:
            error =  "Malformed file, missing component offsets"
            return (False, error)

        files = list(npzfile['files'][0])
        self.material = files[0].decode("utf-8")
        vwfile        = files[1].decode("utf-8")

        if "scale" in npzfile:
            self.scale = npzfile["scale"]
        else:
            self.scale = None

        if len(vwfile) == 0:
            self.vertexboneweights_file = None
        else:
            self.vertexboneweights_file = vwfile

        if nrefverts == 3:
            self.ref_vIdxs = npzfile["ref_vIdxs"]
            self.offsets   = npzfile["offsets"]
            self.weights   = npzfile["weights"]
        else:
            num_refs = npzfile['ref_vIdxs'].shape[0]
            self.ref_vIdxs = np.zeros((num_refs,3), dtype=np.uint32)
            self.ref_vIdxs[:,0] = npzfile['ref_vIdxs']
            self.offsets = np.zeros((num_refs,3), dtype=np.float32)
            self.weights = np.zeros((num_refs,3), dtype=np.float32)
            self.weights[:,0] = npzfile['weights']

        if "deleteVerts" in npzfile:
            self.deleteVerts = npzfile["deleteVerts"]

        self.obj_file = path
        if self.material is not None:
            self.standard_material = self.material
            self.material = os.path.normpath(os.path.join(os.path.dirname(path), self.material))
        else:
            self.standard_material = ""

        return importObjValues(npzfile, self.obj)

    def calculateBoneWeights(self):
        """
        calculateBoneWeights either import weight from file or calculates weights for
        assets via pose_skeleton weights
        """
        if not hasattr(self.glob, "baseClass"):
            return True, "import"

        if self.glob.baseClass.default_skeleton == None:
            return True, None

        # TODO: No skeleton = no weights, or all weights == 1 to a virtual
        # root bone 

        self.bWeights = boneWeights(self.glob, self.glob.baseClass.default_skeleton, self.obj)

        if self.vertexboneweights_file is not None:
            weightfile =  os.path.normpath(os.path.join(os.path.dirname(self.obj_file), self.vertexboneweights_file))
            if os.path.isfile(weightfile):
                if self.bWeights.loadJSON(weightfile) is False:
                    self.bWeights = None
                    return False, self.env.last_error
        else:
            # calculate weights from pose skeleton
            #
            self.bWeights.approxWeights(self, self.glob.baseClass.pose_skeleton.bWeights)
        return True, None

    def load(self, filename: str, use_ascii=False) -> int:
        """
        load mhclo or mhbin
        if not ASCII must be use and .mhbin is newer than .mhclo load .mhbin
        :param str filename: name of the file to read from
        :param bool use_ascii: determines if ASCII must be used
        :return: int 0 = error, 1 = bad geometry, 2 = okay
        """
        if use_ascii is False and (filename.endswith(".mhclo") or filename.endswith(".proxy")):
            binfile = filename[:-5] + "mhbin"
            newer = self.env.isSourceFileNewer(binfile, filename)

            if not newer and os.path.isfile(binfile):
                #
                # load mhbin
                #
                self.filename = filename
                self.obj = object3d(self.glob, None, self.type)
                (res, err) = self.importBinary(binfile)
                if res == 0:
                    return (res, err)
                self.obj.filename = filename
                self.obj.initMaterial(filename)
                if self.type == "hair":
                    self.z_depth = 255
                self.obj.setZDepth(self.z_depth)
                self.obj.setName(self.name)

                (bwok, err2) = self.calculateBoneWeights()
                if bwok is False:
                    return (0, err2)

                return (res, err)
            use_ascii = True

        # load mhclo file
        #
        (res, err) = self.textLoad(filename)
        if res is True:
            self.env.logLine(16, "Object is:" + self.obj_file)

            # create object and load obj file
            #
            obj = object3d(self.glob, None, self.type)
            (res, err) = obj.load(self.obj_file, use_ascii)
            if res > 0:
                self.obj = obj
                self.obj.setName(self.name)
                self.obj.setZDepth(self.z_depth)

                (bwok, err2) =self.calculateBoneWeights()
                if bwok is False:
                    return (0, err2)

                # now export binary file
                #
                (expok, err2) = self.exportBinary()
                if expok is False:
                    return (0, err2)
                return res, err

        self.env.logLine(1, err )
        return (0, err)

    def exportBinary(self, filename=None):

        filename = self.filename if filename is None  else filename
        if filename.endswith(".mhclo") or filename.endswith(".proxy"):
            filename = filename[:-6] + ".mhbin"
        else:
            filename = filename + ".mhbin"

        content = {}

        # binary structure
        # first header
        mtags = "|".join(self.tags)
        ltags = "|S" + str(len(mtags))

        lname = "|S" + str(len(self.name))
        llics = "|S" + str(len(self.license))
        luuid = "|S" + str(len(self.uuid))
        lauth = "|S" + str(len(self.author))
        ldesc = "|S" + str(len(self.description))
        lmesh = "|S" + str(len(self.meshtype))

        nrefverts = 3 if self.weights[:,1:].any() else 1

        asset_type = np.dtype({'names':('name', 'uuid', 'author', 'description', 'meshtype', 'refverts', 'version', 'zdepth', 'license', 'tags'),
            'formats':(lname, luuid, lauth, ldesc, lmesh, 'i4', 'i4', 'i4', llics, ltags)})
        content["asset"] = np.array([(self.name, self.uuid, self.author, self.description, self.meshtype, nrefverts, self.version,
            self.z_depth, self.license, mtags)], dtype=asset_type)

        if self.material is None:
            matfile = ""
        else:
            matfile = self.material
        lmat = "|S" + str(len(matfile))

        if self.vertexboneweights_file is None:
            vwfile = ""
        else:
            vwfile = self.vertexboneweights_file
        lweight = "|S" + str(len(vwfile))

        files_type = np.dtype({'names':('material', 'weight'), 'formats': (lmat, lweight)})
        content["files"] =  np.array([(self.standard_material, vwfile)], dtype=files_type)

        # save scale if used correctly
        #
        if self.scale is not None:
            content["scale"] = self.scale

        if nrefverts == 3:
            content["ref_vIdxs"] = self.ref_vIdxs
            content["offsets"] = self.offsets
            content["weights"] = self.weights
        else:
            content["ref_vIdxs"] = self.ref_vIdxs[:,0]
            content["weights"] = self.weights[:,0]

        if np.any(self.deleteVerts):
            content["deleteVerts"] = self.deleteVerts

        return exportObj3dBinary(filename, self.obj, content)

    def mhcloToMHBin(self, path):
        return(self.load(path, True))

