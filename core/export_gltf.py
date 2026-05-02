"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck, Elvaerwyn_MH2

    Classes:
    * gltfExport

    GLTF module:
    Orientation
    + Y = up
    + z = to front
    + x = right
"""

import os
import json
import struct
import numpy as np
from obj3d.skeleton import skeleton as newSkeleton

class gltfExport:
    """Class representation of glTF export function
    Hint: animation is exported with corrections

    :param glob: handle to global object to access base object etc
    :type glob: class: globalObjects
    :param str exportfolder: name of the folder to export textures
    :param bool hiddenverts: if hidden vertices should be exported
    :param bool includetextures: will embed the textures into the binary part
    :param bool onground: if character should stay on ground
    :param bool animation: if animation should be exported
    :param float scale: the scale of the output
    """

    def __init__(self, glob, exportfolder, imagefolder="textures", includetextures=False, hiddenverts=False, onground=True, animation=False, scale =0.1):

        # subfolder for textures
        #
        self.imagefolder = imagefolder
        self.exportfolder = exportfolder
        self.glob = glob
        self.env = glob.env
        self.includetextures = includetextures
        self.hiddenverts = hiddenverts
        self.onground = onground
        self.animation = animation
        self.scale = scale
        self.lowestPos = 0.0
        self.animYoffset = 0.0

        # all constants used
        #
        self.TRIANGLES = 4
        self.UNSIGNED_BYTE = 5121
        self.UNSIGNED_SHORT = 5123
        self.UNSIGNED_INT = 5125
        self.FLOAT = 5126
        self.ARRAY_BUFFER = 34962          # usually positions
        self.ELEMENT_ARRAY_BUFFER = 34963  # usually indices
        self.GLTF_VERSION = 2
        self.MAGIC = b'glTF'
        self.JSON = b'JSON'
        self.BIN  = "BIN\x00"
        #
        # for image and sampler
        self.MAGFILTER = 9729   # Linear Magnification filter
        self.MINFILTER = 9987   # LINEAR_MIPMAP_LINEAR
        self.REPEAT = 10497
        self.IMAGEJPEG = 'image/jpeg'
        self.IMAGEPNG = "image/png"


        self.json = {}
        self.json["asset"] = {"generator": "makehuman2", "version": "2.0" }    # copyright maybe
        self.json["scenes"] = [ {"name": "makehuman2 export", "nodes": [] } ]  # one scene contains all nodes

        self.json["samplers"] = [ { "magFilter": self.MAGFILTER, "minFilter": self.MINFILTER, # fixed sampler (one for all)
            "wrapS": self.REPEAT, "wrapT" : self.REPEAT } ]

        self.json["scene"] = 0 # fixed number (we only have one scene)

        self.json["nodes"] = [] # list of nodes

        self.json["meshes"] = []
        self.mesh_cnt = -1

        self.json["accessors"] = []     # list of accessors (pointer to buffers, size, min, max
        self.accessor_cnt = -1

        self.json["bufferViews"] = []   # list of bufferviews, mode of buffer, length, offset, buffer number
        self.bufferview_cnt = -1

        self.json["buffers"] = []       # at the moment we try one view = one buffer

        # self.json["skins"]            # is defined later only when skeleton is available

        # texture and material
        #
        self.json["materials"] = []
        self.material_cnt = -1

        self.json["textures"] = []
        self.texture_cnt = -1

        self.json["images"] = []
        self.image_cnt = -1

        self.bufferoffset = 0
        self.buffers = []       # will hold the pointers

        self.bonelist = []      # helps to keep the order of the bones
        self.bonenames = {}
        self.bonestart = 0      # used to keep track of first bone in glTF

        self.meshindices = []   # holds meshindices for joints and weights

    def __str__(self):
        return json.dumps(self.json, indent=3)

    def debug(self, text):
        self.env.logLine (2, "gltf-Export: " + text)

    def filedebug(self, text):
        self.env.logLine (8, "gltf-Export: " + text)

    def nodeName(self, filename):
        if filename is None:
            return "generic"

        fname = os.path.basename(filename)
        return os.path.splitext(fname)[0]

    def addBufferView(self, target, data):
        #
        # buffer + we create one big binary buffer, we will keep all buffers 4 byte aligned
        # (byteLength must contain original length, but offset must be corrected)

        length = len(data)
        b = length & 3
        pad = 4-b if b > 0 else 0

        self.bufferview_cnt += 1
        if target is not None:
            self.json["bufferViews"].append({"buffer": 0, "byteOffset": self.bufferoffset, "byteLength": length, "target": target })
        else:
            self.json["bufferViews"].append({"buffer": 0, "byteOffset": self.bufferoffset, "byteLength": length })
        self.buffers.append(data)
        self.bufferoffset += length
        self.bufferoffset += pad

        return self.bufferview_cnt

    def addPosAccessor(self, coord):
        self.accessor_cnt += 1

        cnt = len(coord) // 3

        ncoord = np.copy(coord)

        meshCoords = np.reshape(ncoord, (cnt,3))
        if self.lowestPos != 0.0:
            meshCoords -= [0.0, self.lowestPos, 0.0]

        if self.scale != 1.0:
            ncoord = ncoord * self.scale
        minimum = (meshCoords.min(axis=0) * self.scale).tolist()
        maximum = (meshCoords.max(axis=0) * self.scale).tolist()

        data = ncoord.tobytes()
        buf = self.addBufferView(self.ARRAY_BUFFER, data)

        self.json["accessors"].append({"bufferView": buf, "componentType": self.FLOAT, "count": cnt, "type": "VEC3", "min": minimum, "max": maximum})
        return self.accessor_cnt

    def addNormAccessor(self, norm):
        self.accessor_cnt += 1

        cnt = len(norm) // 3
        meshCoords = np.reshape(norm, (cnt,3))
        minimum = meshCoords.min(axis=0).tolist()
        maximum = meshCoords.max(axis=0).tolist()

        data = norm.tobytes()
        buf = self.addBufferView(self.ARRAY_BUFFER, data)
        self.json["accessors"].append({"bufferView": buf, "componentType": self.FLOAT, "count": cnt, "type": "VEC3", "min": minimum, "max": maximum})
        return self.accessor_cnt

    def addTPosAccessor(self, uvcoord):
        self.accessor_cnt += 1

        cnt = len(uvcoord) // 2
        meshCoords = np.reshape(uvcoord, (cnt,2))
        minimum = meshCoords.min(axis=0).tolist()
        maximum = meshCoords.max(axis=0).tolist()

        data = uvcoord.tobytes()
        buf = self.addBufferView(self.ARRAY_BUFFER, data)

        self.json["accessors"].append({"bufferView": buf, "componentType": self.FLOAT, "count": cnt, "type": "VEC2", "min": minimum, "max": maximum})
        return self.accessor_cnt

    def addIndAccessor(self, icoord):
        self.accessor_cnt += 1
        cnt = len(icoord)
        minimum = int(icoord.min())
        maximum = int(icoord.max())

        data = icoord.tobytes()
        buf = self.addBufferView(self.ELEMENT_ARRAY_BUFFER, data)

        self.json["accessors"].append({"bufferView": buf, "componentType": self.UNSIGNED_INT, "count": cnt, "type": "SCALAR", "min": [minimum], "max": [maximum]})
        return self.accessor_cnt

    def addBindMatAccessor(self, bonelist):
        self.accessor_cnt += 1
        cnt = len(bonelist)
        bindmat = np.zeros((cnt, 4,4), dtype=np.float32)
        n = 0
        for elem in self.bonenames:
            bone = self.bonenames[elem][1]
            bindmat[n], bindinv = bone.getBindMatrix(0, 'y')
            n += 1

        data = bindmat.tobytes()
        buf = self.addBufferView(None, data)

        self.json["accessors"].append({"bufferView": buf, "componentType": self.FLOAT, "count": cnt, "type": "MAT4"})
        return self.accessor_cnt

    def addJointAndWeightAccessor(self, numverts, bweights, overflow):
        self.accessor_cnt += 1

        if len(self.bonelist) > 255:
            joints = np.zeros((numverts, 4), dtype=np.uint16)
            jtype = self.UNSIGNED_SHORT
        else:
            joints = np.zeros((numverts, 4), dtype=np.uint8)
            jtype = self.UNSIGNED_BYTE

        weights = np.zeros((numverts, 4), dtype=np.float32)

        vertex = {}

        #print ("Verts:" + str(numverts))
        maxv = 0
        for elem in bweights:
            # get bone number from list
            #
            bonenumber = self.bonenames[elem][0]
            ind, w = bweights[elem]
            for n, i in enumerate (ind):
                if i > maxv:
                    maxv = i
                if i not in vertex:
                    vertex[i] = []
                vertex[i].append((bonenumber, w[n]))
        #print ("Maxv:" + str(maxv))

        for v in vertex:
            m = vertex[v]
            #
            # get largest 4 values
            #
            if len(m) > 4:
                m = sorted(m, key=lambda elem: elem[1], reverse=True)[:4]
            for i, (n,w) in enumerate(m):
                joints[v][i] = n
                weights[v][i] = w

        # normalize weights (can deal with 0.0 sums)
        #
        sums = weights.sum(axis=1, keepdims=1)
        sums[sums==0.0] = 1.0
        weights = weights/sums

        if overflow is not None:
            for (s,d) in overflow:
                for i in range(0,4):
                    joints[d][i] = joints[s][i]
                    weights[d][i] = weights[s][i]

        data = joints.tobytes()
        buf = self.addBufferView(self.ARRAY_BUFFER, data)
        self.json["accessors"].append({"bufferView": buf, "componentType": jtype, "count": numverts, "type": "VEC4"})

        self.accessor_cnt += 1
        data = weights.tobytes()
        buf = self.addBufferView(self.ARRAY_BUFFER, data)
        self.json["accessors"].append({"bufferView": buf, "componentType": self.FLOAT, "count": numverts, "type": "VEC4"})
        return self.accessor_cnt

    def addAnimInputAccessor(self, frames, framelen):
        self.accessor_cnt += 1
        timestamps = np.zeros(frames, dtype=np.float32)
        timepos = 0.0
        for i in range(frames):
            timestamps[i] = timepos
            timepos += framelen
        maximum = float(timestamps[-1])
        data = timestamps.tobytes()
        buf = self.addBufferView(None, data)
        self.json["accessors"].append({"bufferView": buf, "componentType": self.FLOAT, "count": frames, "min": [ 0.0 ], "max": [maximum],  "type": "SCALAR"})
        return self.accessor_cnt

    def addAnimOutputAccessor(self, values, tlen):
        frames = len(values)
        self.accessor_cnt += 1
        if tlen == 4:
            jtype = "VEC4"
        else:
            jtype = "VEC3"
        data = values.tobytes()
        buf = self.addBufferView(None, data)
        self.json["accessors"].append({"bufferView": buf, "componentType": self.FLOAT, "count": frames, "type": jtype})
        return self.accessor_cnt

    def copyImage(self, source, dest):
        self.filedebug("Need to copy " + source + " to " + dest)

        if self.env.mkdir(dest) is False:
            return False

        dest = os.path.join(dest, os.path.basename(source))
        return self.env.copyfile(source, dest)

    def addImage(self, image):
        self.image_cnt += 1
        if self.includetextures:
            mtype = self.IMAGEJPEG
            if image.endswith(".png"):
                mtype = self.IMAGEPNG
            elif not (image.endswith(".jpeg") or image.endswith(".jpg")):
                self.env.last_error = "Bad image format, only jpeg, jpg or png is allowed to determine mimeType"
                return (False, -1)

            try:
                with open(image, mode="rb") as binfile:
                    data = binfile.read()
            except Exception as error:
                self.env.last_error = "problems while reading image " + image
                return (False, -1)
            buf = self.addBufferView(None, data)
            self.json["images"].append({"bufferView": buf, "mimeType": mtype})
        else:
            destination = os.path.join(self.exportfolder, self.imagefolder)
            okay = self.copyImage(image, destination)
            if not okay:
                return (False, -1)

            uri = self.env.formatPath(os.path.join(self.imagefolder, os.path.basename(image)))
            self.json["images"].append({"uri": uri})
        return (True, self.image_cnt)

    def addMRTexture(self, roughtex):
        self.texture_cnt += 1
        (okay, image) = self.addImage(roughtex)
        if not okay:
            return None
        self.json["textures"].append({"sampler": 0, "source": image})
        return({ "index":  self.texture_cnt })

    def pbrMaterial(self, color, metal, rough, roughtex):
        pbr = { "baseColorFactor": [ color[0], color[1], color[2], 1.0 ], "metallicFactor": metal, "roughnessFactor": rough }
        if roughtex is not None:
            rtex = self.addMRTexture(roughtex)
            if rtex is not None:
                pbr["metallicRoughnessTexture"] = rtex
        return pbr

    def addDiffuseTexture(self, texture, metal, rough, roughtex):
        self.texture_cnt += 1
        (okay, image) = self.addImage(texture)
        if not okay:
            return None
        self.json["textures"].append({"sampler": 0, "source": image})

        pbr = { "baseColorTexture": { "index":  self.texture_cnt}, "metallicFactor": metal, "roughnessFactor": rough }

        if roughtex is not None:
            rtex = self.addMRTexture(roughtex)
            if rtex is not None:
                pbr["metallicRoughnessTexture"] = rtex

        return pbr

    def addNormalTexture(self, texture, scale):
        self.texture_cnt += 1
        (okay, image) = self.addImage(texture)
        if not okay:
            return None
        self.json["textures"].append({"sampler": 0, "source": image})
        return ({ "index": self.texture_cnt, "scale": scale })

    def addEmissiveTexture(self, texture):
        self.texture_cnt += 1
        (okay, image) = self.addImage(texture)
        if not okay:
            return None
        self.json["textures"].append({"sampler": 0, "source": image})
        return ({ "index": self.texture_cnt })

    def addOcclusionTexture(self, texture, strength):
        self.texture_cnt += 1
        (okay, image) = self.addImage(texture)
        if not okay:
            return None
        self.json["textures"].append({"sampler": 0, "source": image})
        return ({ "index": self.texture_cnt, "strength": strength })

    def addMaterial(self, material, assettype):
        """
        :param material:  material from opengl.material
        :param assettype: type of asset, identical with name of folder
        """
        self.material_cnt += 1

        # 1. UNIQUE NAMING: Prevents e.g. Unreal from merging different materials
        # We sanitize the name and append the counter to make it unique in a Asset Registry of destination system

        raw_name = material.name if  material.name is not None else "material"
        name = "{}_{:03d}".format(self.env.normalizeName(raw_name), self.material_cnt)

        roughtex = getattr(material, "metallicRoughnessTexture", None)
        if roughtex is not None:
            self.debug ("Metallic-Roughness " + roughtex)

        # 2. Build Diffuse Material for PBR
        #
        if hasattr(material, "diffuseTexture"):
            self.debug ("Diffuse " + material.diffuseTexture)
            diffusename = material.saveDiffuse() if material.colorationMethod > 0 else material.diffuseTexture
            pbr = self.addDiffuseTexture(diffusename, material.metallicFactor, material.roughnessFactor, roughtex)
        else:   
            pbr = self.pbrMaterial(material.diffuseColor, material.metallicFactor, material.roughnessFactor, roughtex)

        if pbr is None:
            return -1

        mat = {"name": name, "pbrMetallicRoughness": pbr,
                "extras": { "source_material": raw_name, "is_makehuman_material": True, "material_index": self.material_cnt }}

        # 3. Add a Transparency Logic
        #
        doublesided = getattr(material, "backfaceCull", True)
        if hasattr(material, "diffuseTexture"):
            if getattr(material, "transparent", False):
                if assettype == "eyelashes" or assettype == "hair":
                    mat["alphaMode"] = "MASK"
                    mat["alphaCutoff"] = 0.5
                else:
                    mat["alphaMode"] = "BLEND"
                mat["doubleSided"] = True
            else:
                mat["doubleSided"] = doublesided
        else:
            mat["doubleSided"] = doublesided    # for objects with only a diffuse color

        if hasattr(material, "normalmapTexture"):
            self.debug ("Normals " + material.normalmapTexture)
            mat["normalTexture"] = self.addNormalTexture(material.normalmapTexture, material.normalmapIntensity)

        if hasattr(material, "aomapTexture"):
            self.debug ("Ambient-Occlusion " + material.aomapTexture)
            mat["occlusionTexture"] = self.addOcclusionTexture(material.aomapTexture, min(material.aomapIntensity, 1.0))

        if hasattr(material, "emissiveTexture"):
            self.debug ("Emissive " + material.emissiveTexture)
            mat["emissiveTexture"] = self.addEmissiveTexture(material.emissiveTexture)
            emf = getattr(material, "emissiveFactor", 0.0)
            mat["emissiveFactor"]  = [ emf, emf, emf ]

        self.json["materials"].append(mat)

        # returns always last element
        return len(self.json["materials"]) - 1

    def filterMorphDeltas(self, raw_deltas, mapping):
        """
        Filters deltas to match the mesh with hidden vertices
        mapping is an array where -1 = hidden, and any other number = new index
        """
        cnt = np.count_nonzero(mapping != -1)
        filtered_deltas = np.zeros(cnt * 3, dtype=np.float32)

        # Reshape for easier coordinate mapping
        reshaped_deltas = np.reshape(raw_deltas, (-1, 3))

        for old_idx, new_idx in enumerate(mapping):
            if new_idx != -1:
                # Copy the X, Y, Z delta to the new position
                filtered_deltas[new_idx*3 : new_idx*3+3] = reshaped_deltas[old_idx]

        return filtered_deltas

    def addMesh(self, obj, nodenumber, bweights, morph_data=None):
        icoord = None
        mapping = None # will contain vertex map for hidden elements

        if self.hiddenverts is False:
            icoord, coord, uvcoord, norm, nweights, overflow, mapping = obj.optimizeHiddenMesh(bweights)

        self.mesh_cnt += 1
        if icoord is not None:
            pos = self.addPosAccessor(coord)
            texcoord = self.addTPosAccessor(uvcoord)
            norm = self.addNormAccessor(norm)
            ind = self.addIndAccessor(icoord)
            self.meshindices.append((len(coord) // 3, nweights, overflow))
        else:
            pos = self.addPosAccessor(obj.gl_coord)
            texcoord = self.addTPosAccessor(obj.gl_uvcoord)
            norm = self.addNormAccessor(obj.gl_norm)
            ind = self.addIndAccessor(obj.gl_icoord)
            self.meshindices.append((len(obj.gl_coord) // 3, bweights, obj.overflow))

        primitive = {
            "attributes": {
                "POSITION": pos,
                "NORMAL": norm,
                "TEXCOORD_0": texcoord
            },
            "indices": ind,
            "material": nodenumber,
            "mode": self.TRIANGLES
        }

        # Handle Morph Targets (TODO: for later use)
        #
        if morph_data:
            primitive["targets"] = []
            target_names = []

            for name, deltas in morph_data:
                # If mesh contained hidden vertices, we must filter the deltas to match
                if mapping is not None:
                    final_deltas = self.filterMorphDeltas(deltas, mapping)
                else:
                    final_deltas = deltas

                target_idx = self.addTargetPosAccessor(final_deltas)
                primitive["targets"].append({"POSITION": target_idx})
                target_names.append(name)

            mesh_entry = {
                "name": obj.name,
                "primitives": [primitive],
                "extras": {"targetNames": target_names} # Show names in e.g. UE5
            }
        else:
            mesh_entry = {"name": obj.name, "primitives": [primitive]}

        self.json["meshes"].append(mesh_entry)
        return len(self.json["meshes"]) - 1

    def addWeights(self, num, elem, obj):
        self.env.logLine (2, "gltf-Export: Adding weights to " +  self.json["nodes"][num]["name"])
        meshnum = self.json["nodes"][num]["mesh"]
        if elem is not None:
            ( numverts, weights, overflow) = self.meshindices[meshnum]
            weightbuf = self.addJointAndWeightAccessor(numverts, weights, overflow)
            jointbuf = weightbuf -1
            m = self.json["meshes"][meshnum]["primitives"][0]["attributes"]
            m["JOINTS_0"] = jointbuf
            m["WEIGHTS_0"] = weightbuf

    def addSkins(self, name):
        ptr = self.addBindMatAccessor(self.bonelist)
        self.json["skins"].append({ "inverseBindMatrices": ptr, "joints": self.bonelist, "name": name + "_skeleton" })

    def addBones(self, bone, num):
        """
        bone-translations and rotations are fetched from local rest matrix, have to be relative in GLTF
        Order of quaternions in GLTF: X Y Z W
        """

        trans = bone.getRestLocalTransVector().tolist()
        rot   = bone.getRestLocalRotQVector()
        rot[[0, 1, 2, 3]] = rot[[1, 2, 3, 0]]       # change quaternion order (W is last element)
        rot = rot.tolist()

        node = {
            "name": bone.name,
            "translation": trans,
            "rotation": rot,
            "children": [],
            "extras": {
                "bone_index": num,
                "author": "black-punkduck",
                "is_skeletal": True
            }
        }
        self.json["nodes"].append(node)
        self.bonelist.append(num)
        self.bonenames[bone.name] = [ len(self.bonelist) - self.bonestart, bone, None, None] # count from first bone in bonestart
        num += 1
        nextnode = num
        for child in bone.children:
            nextnode = self.addBones(child, num)
            node["children"].append(num)
            num = nextnode
        if len(node["children"]) == 0:
            del node["children"]
        return num

    def addAnimations(self, skeleton, bvh, orig=True):

        # create channels and samplers
        #
        nFrames = bvh.frameCount
        offset = 0.0
        if self.onground:
            #
            # TODO: offset for animation is not yet correct when scale is not 1
            #
            #print (self.lowestPos)
            #print (self.animYoffset)
            if self.scale == 1.0:
                offset = self.animYoffset
                # smaller 1 
                # offset = (self.animYoffset + self.lowestPos) * self.scale

        common_input = self.addAnimInputAccessor(nFrames, bvh.frameTime)

        # generate arrays for translation, rotation
        #
        for key in self.bonenames:
            self.bonenames[key][2] = np.zeros((nFrames, 3), dtype=np.float32)
            self.bonenames[key][3] = np.zeros((nFrames, 4), dtype=np.float32)

        for frame in range(nFrames):

            # bvh.joints are original joints in case of different skeleton, so in that case it will be posed by reference
            #
            if orig:
                skeleton.pose(bvh.joints, frame, True)
            else:
                skeleton.poseByReference(bvh.joints, frame)

            for bonename in self.bonenames:
                bone = skeleton.bones[bonename]
                #
                # for root bone the global vectors are used
                # for other bones translation is calculated by local rest vector (cannot change)
                # rotations are calculated by using inverse parent global Vector multiplied by current global vector
                #
                if bone.parent is None:
                    trans = bone.getPoseGlobalTransVector() * self.scale - [0.0, offset, 0.0]
                    rot   = bone.getPoseGlobalRotQVector()
                else:
                    trans = bone.getRestLocalTransVector()
                    rot   = bone.getPoseRelParentRotQVector()

                # quaternions, W ist last element
                #
                rot[[0, 1, 2, 3]] = rot[[1, 2, 3, 0]]
                self.bonenames[bonename][2][frame][:] = trans[:]
                self.bonenames[bonename][3][frame][:] = rot[:]

        channels = []
        samplers = []
        sampler = 0
        for bonename in self.bonenames:
            node = self.bonenames[bonename][0] + self.bonestart
            channels.append({"sampler": sampler, "target": { "node": node, "path": "translation" }})
            output = self.addAnimOutputAccessor(self.bonenames[bonename][2], 3)
            samplers.append({"input": common_input, "interpolation":"LINEAR", "output": output})
            sampler += 1
            channels.append({"sampler": sampler, "target": {"node": node, "path": "rotation" }})
            output = self.addAnimOutputAccessor(self.bonenames[bonename][3], 4)
            samplers.append({"input": common_input, "interpolation":"LINEAR", "output": output})
            sampler += 1

        self.json["animations"] = []
        self.json["animations"].append({"name": bvh.name, "channels": channels, "samplers": samplers})

    def addNodes(self, baseclass):
        #
        # add the basemesh itself
        # then the skeleton and then the assets all these  nodes will be children
        # here one node will always have one mesh
        #
        skin = baseclass.baseMesh.material

        baseweights = None

        if baseclass.skeleton is not None:

            # recalculate weights for different skeleton
            #
            baseweights =  baseclass.default_skeleton.bWeights.transferWeights(baseclass.skeleton)
            self.json["skins"] = []


        # in case of a proxy use the proxy as first mesh, get weights for proxy
        #
        if baseclass.proxy is not None:
            proxy = baseclass.attachedAssets[0]
            if baseweights is not None:
                proxy.calculateBoneWeights()
                baseweights = proxy.bWeights.transferWeights(baseclass.skeleton)
            baseobject = proxy.obj
            start = 1
        else:
            baseobject = baseclass.baseMesh
            start = 0
        charactername = self.nodeName(baseobject.filename)

        mat  = self.addMaterial(skin, "skin")   # type skin (not a real asset)
        if mat == -1:
            return False

        # in case of onground we need a translation which is then added to the mesh
        #
        if self.onground:
            self.lowestPos = baseclass.getLowestPos()


        mesh = self.addMesh(baseobject, mat, baseweights)

        self.json["nodes"].append({"name": charactername, "mesh": mesh,  "children": []  })
        self.json["scenes"][0]["nodes"].append(0)
        children = self.json["nodes"][0]["children"]

        childnum = 1

        # add skeleton, if baseweights are available
        #
        if baseweights is not None:
            self.json["nodes"][0]["skin"] = 0
            if self.scale != 1.0 or self.onground:
                self.debug("Resizing or repositining, get a new skeleton")
                skeleton = newSkeleton(self.glob, "copy")
                skeleton.copyScaled(baseclass.skeleton, self.scale, self.lowestPos, False)
            else:
                skeleton = baseclass.skeleton

            bonename = list(skeleton.bones)[0]
            bone = skeleton.bones[bonename]

            self.bonestart = childnum
            children.append(childnum)
            childnum = self.addBones(bone, childnum)
            self.addSkins(charactername)

            # now add weights and joints
            #
            self.addWeights(0, skeleton, baseobject)

        # add all assets
        #
        for elem in baseclass.attachedAssets[start:]:

            current_obj = elem.obj

            # 1. Get the Unique Material Index
            mat_idx =  self.addMaterial(current_obj.material, elem.type)
            if mat_idx == -1:
                return False

            # 2. Calculate and Transfer Weights BEFORE adding the mesh
            weights = None
            if baseweights is not None:
                elem.calculateBoneWeights()
                weights = elem.bWeights.transferWeights(baseclass.skeleton)

            # 3. Add the Mesh now using the correctly calculated weights
            mesh_idx = self.addMesh(current_obj, mat_idx, weights)

            # 4. Create the Node
            self.json["nodes"].append({"name": self.nodeName(elem.filename), "mesh": mesh_idx })
            this_node_idx = len(self.json["nodes"]) - 1
            children.append(this_node_idx)

            # 5. Link the Skin
            if baseweights is not None:
                self.json["nodes"][this_node_idx]["skin"] = 0
                self.addWeights(this_node_idx, elem, current_obj)

        # add animation, if any
        #
        if self.animation and baseweights is not None and baseclass.bvh:

            # modify internal bones with corrections
            #
            baseclass.bvh.modCorrections()

            # TODO offset might be used different, when anim editor is completed
            #
            self.animYoffset = baseclass.skeleton.rootLowestDistance(baseclass.bvh.joints, 0, baseclass.bvh.frameCount) + self.lowestPos

            if baseclass.skeleton == baseclass.default_skeleton:
                self.addAnimations(skeleton, baseclass.bvh, True)
            else:
                self.debug ("Animation will be posed by references")
                self.addAnimations(skeleton, baseclass.bvh, False)

            baseclass.bvh.identFinal()

        self.json["buffers"].append({"byteLength": self.bufferoffset})
        self.env.logLine(32, str(self))
        return True


    def binSave(self, baseclass, filename):
        #
        # binary glTF is:
        # 4 byte magic, 4 byte version + 4 byte length over all (which is the header)
        # JSON chunk:
        # chunklength 4 Byte, chunk type JSON, chunkData (4 Byte boundaries, padding)
        # BIN chunk:
        # chunklength 4 Byte, chunk type JSON, chunkData (4 Byte boundaries, padding)
        self.env.last_error ="okay"
        if self.addNodes(baseclass) is False:
            return False

        #TODO do we need an _ExtendedEncoder for JSON?

        version = struct.pack('<I', self.GLTF_VERSION)
        length = 12         # header length (always fix 12 bytes)

        jsondata = json.dumps(self.json, indent=None, allow_nan=False, skipkeys=True, separators=(',', ':')).encode("utf-8")

        # now pad json data to align with 4
        #
        pad = len(jsondata) % 4
        if pad != 0:
            jsondata += b' ' * (4-pad)
        
        lenjson = len(jsondata)
        length += (8 + lenjson) # add header + json-blob to length
        chunkjsonlen = struct.pack('<I', lenjson)

        # now the binary buffer. try to work with pointers here
        # the number of maximum used data is in bufferoffset
        # padding is needed in case of textures

        lenbin = self.bufferoffset

        length += (8 + lenbin) # add header + bin-blob to length
        chunkbinlen = struct.pack('<I', lenbin)

        completelength = struct.pack('<I', length)

        try:
            with open(filename, 'wb') as f:
                f.write(self.MAGIC)
                f.write(version)
                f.write(completelength)
                f.write(chunkjsonlen)
                f.write(self.JSON)
                f.write(jsondata)
                f.write(chunkbinlen)
                f.write(bytes(self.BIN, "utf-8"))
                for elem in self.buffers:
                    f.write(bytes(elem))
                    b = len(elem) & 3
                    if b !=  0:
                        f.write(b'\x00' * (4-b))

        except IOError as error: 
            self.env.last_error = str(error)
            return False
        return True
