"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * blendCom

    new Blender exchange format similar to glTF, so binary buffers for
    verts, vertex per faces, faces, uvs => to read with from_pydata() in Blender

    definition of structure is in JSON

    this module is used for files and socket API

    so order of buffers is significant to be able to read the file chunk by chunk

    start must be skeleton (if available) to get the restmatrix buffer first,
    then all othter future components not directly associated with a mesh
"""

import os
import json
import struct
import numpy as np
from obj3d.skeleton import skeleton as newSkeleton

class blendCom:
    def __init__(self, glob, exportfolder, imagefolder="textures", hiddenverts=False, onground=True, animation=False, scale =0.1):

        # subfolder for textures
        #
        self.imagefolder = imagefolder
        self.exportfolder = exportfolder
        self.glob = glob
        self.env = glob.env
        self.hiddenverts = hiddenverts
        self.onground = onground
        self.animation = animation
        self.scale = scale
        self.lowestPos = 0.0
        self.rootname = "generic"

        # all constants used
        #
        self.RMAT_BUFFER   = 1  # rest matrix (skeleton)
        self.ANIM_BUFFER   = 2  # animation (skeleton)
        self.POS_BUFFER    = 10 # target: position
        self.VPF_BUFFER    = 11 # vertex per face
        self.FACE_BUFFER   = 12
        self.UV_BUFFER     = 13
        self.OV_BUFFER     = 14
        self.WPV_BUFFER    = 16 # weight per vertex
        self.JOINT_BUFFER  = 17
        self.WEIGHT_BUFFER = 18
        self.MH2B_VERSION = 1
        self.MAGIC = b'MH2B'
        self.JSON = b'JSON'
        self.BIN  = "BIN\x00"

        self.json = {}
        # change asset version to add a name for collection
        self.json["asset"] = {"generator": "makehuman2", "version": "1.0", "mode": 0, "buffersize": 0, "nodes": []  } # mode=0 complete file

        self.json["nodes"] = [] # list of nodes

        self.json["meshes"] = []
        self.mesh_cnt = -1

        self.json["bufferViews"] = []   # list of bufferviews, mode of buffer, length, offset, buffer number
        self.bufferview_cnt = -1

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

        self.bonenames = {}

        # additional block: skeleton

    def __str__(self):
        return (json.dumps(self.json, indent=3))

    def debug(self, text):
        self.env.logLine (2, "blender-communication: " + text)

    def nodeName(self, filename, prefix=False):
        if filename is None:
            name = "generic"
        else:
            name = os.path.basename(filename)
            name = os.path.splitext(name)[0]
        if prefix:
            name = self.rootname + ":" + name
        return(name)

    def addBufferView(self, target, data):
        #
        # buffer + we create one big binary buffer 

        length = len(data)

        self.bufferview_cnt += 1
        self.json["bufferViews"].append({"byteOffset": self.bufferoffset, "byteLength": length, "target": target })
        self.buffers.append(data)
        self.bufferoffset += length
        return(self.bufferview_cnt)

    def addPosBuffer(self, coord):
        if self.scale != 1.0:
            coord = coord * self.scale

        if self.lowestPos != 0.0:
            sub = np.array([0.0, self.lowestPos, 0.0], dtype=np.float32)
            change = np.tile(sub, len(coord)//3)
            coord = coord - change

        data = coord.tobytes()
        return(self.addBufferView(self.POS_BUFFER, data))


    def addTPosBuffer(self, uvcoord):
        data = uvcoord.tobytes()
        return(self.addBufferView(self.UV_BUFFER, data))

    def addOverflowBuffer(self, overflow):
        data = overflow.flatten().tobytes()
        return(self.addBufferView(self.OV_BUFFER, data))

    def addFaceBuffer(self, faces):
        data = faces.tobytes()
        return(self.addBufferView(self.FACE_BUFFER, data))

    def addVPFBuffer(self, vpf):
        data = vpf.tobytes()
        return(self.addBufferView(self.VPF_BUFFER, data))

    def copyImage(self, source, dest):
        self.env.logLine (8, "Copy " + source + " to " + dest)

        if self.env.mkdir(dest) is False:
            return False

        dest = os.path.join(dest, os.path.basename(source))
        return (self.env.copyfile(source, dest))

    def addImage(self, image):
        """
        can copy the image to exportfolder, in case it is not None (API)
        """
        self.image_cnt += 1

        if self.exportfolder is not None:
            destination = os.path.join(self.exportfolder, self.imagefolder)
            okay = self.copyImage(image, destination)
            if not okay:
                return (False, -1)
            uri = os.path.join(self.imagefolder, os.path.basename(image))
        else:
            uri = image
        self.json["images"].append({"uri": uri})
        return(True, self.image_cnt)

    def addMRTexture(self, roughtex):
        self.texture_cnt += 1
        (okay, image) = self.addImage(roughtex)
        if not okay:
            return (None)
        self.json["textures"].append({"sampler": 0, "source": image})
        return({ "index":  self.texture_cnt })

    def pbrMaterial(self, color, metal, rough, roughtex):
        pbr = { "baseColorFactor": [ color[0], color[1], color[2], 1.0 ], "metallicFactor": metal, "roughnessFactor": rough }
        if roughtex is not None:
            rtex = self.addMRTexture(roughtex)
            if rtex is not None:
                pbr["metallicRoughnessTexture"] = rtex
        return (pbr)

    def addDiffuseTexture(self, texture, metal, rough, roughtex):
        self.texture_cnt += 1
        (okay, image) = self.addImage(texture)
        if not okay:
            return (None)
        self.json["textures"].append({"sampler": 0, "source": image})

        pbr = { "baseColorTexture": { "index":  self.texture_cnt}, "metallicFactor": metal, "roughnessFactor": rough }

        if roughtex is not None:
            rtex = self.addMRTexture(roughtex)
            if rtex is not None:
                pbr["metallicRoughnessTexture"] = rtex

        return (pbr)

    def addNormalTexture(self, texture, scale):
        self.texture_cnt += 1
        (okay, image) = self.addImage(texture)
        if not okay:
            return (None)
        self.json["textures"].append({"sampler": 0, "source": image})
        return ({ "index": self.texture_cnt, "scale": scale })

    def addEmissiveTexture(self, texture):
        self.texture_cnt += 1
        (okay, image) = self.addImage(texture)
        if not okay:
            return (None)
        self.json["textures"].append({"sampler": 0, "source": image})
        return ({ "index": self.texture_cnt })

    def addOcclusionTexture(self, texture, strength):
        self.texture_cnt += 1
        (okay, image) = self.addImage(texture)
        if not okay:
            return (None)
        self.json["textures"].append({"sampler": 0, "source": image})
        return ({ "index": self.texture_cnt, "strength": strength })

    def addMaterial(self, material):
        """
        :param material:  material from opengl.material
        TODO: alphaMode, alphaCutoff, doubleSided
        """
        self.material_cnt += 1
        name = material.name if  material.name is not None else "generic"

        roughtex = None
        if hasattr(material, "metallicRoughnessTexture"):
            roughtex = material.metallicRoughnessTexture
            self.debug ("Metallic-Roughness " + roughtex)

        if hasattr(material, "diffuseTexture"):
            self.debug ("Diffuse " + material.diffuseTexture)
            if material.colorationMethod > 0:
                diffusename = material.saveDiffuse()
            else:
                diffusename = material.diffuseTexture

            pbr = self.addDiffuseTexture(diffusename, material.metallicFactor, material.roughnessFactor, roughtex)
        else:   
            pbr = self.pbrMaterial(material.diffuseColor, material.metallicFactor, material.roughnessFactor, roughtex)

        norm = None
        if hasattr(material, "normalmapTexture"):
            self.debug ("Normals " + material.normalmapTexture)
            norm = self.addNormalTexture(material.normalmapTexture, material.normalmapIntensity)

        occl = None
        if hasattr(material, "aomapTexture"):
            self.debug ("Ambient-Occlusion " + material.aomapTexture)
            ao_intensity = min(material.aomapIntensity, 1.0)
            occl = self.addOcclusionTexture(material.aomapTexture, ao_intensity)

        emis = None
        if hasattr(material, "emissiveTexture"):
            self.debug ("Emissive " + material.emissiveTexture)
            emis = self.addEmissiveTexture(material.emissiveTexture)

        if pbr is None:
            return(-1)

        mat = {"name": self.nodeName(name), "pbrMetallicRoughness": pbr}
        if hasattr(material, "diffuseTexture") and material.transparent:
            mat["alphaMode"] = "HASHED" # is not a gltfMode !
            mat["doubleSided"] =  material.backfaceCull

        if norm is not None:
            mat["normalTexture"] = norm

        if occl is not None:
            mat["occlusionTexture"] = occl

        if emis is not None:
            mat["emissiveTexture"] = emis
            mat["emissiveFactor"]  = material.emissiveFactor  # float instead of vector (glTF)
        else:
            if material.emissiveFactor > 0.0 and material.emissiveColor != [0.0, 0.0, 0.0]:
                mat["emissiveColor"] = material.emissiveColor
                mat["emissiveFactor"]= material.emissiveFactor

        self.json["materials"].append(mat)
        return (self.material_cnt)

    def addWeightBuffers(self, coords, bweights, mapping):
        wpvlen = len(coords) // 3   # length of vertex per face derived from flattened coords

        lsize = 0

        vertex = {}
        # TODO: how to deal with empty weights

        if mapping is None:
            for bone, t in bweights.items():
                bonenumber = self.bonenames[bone]
                ind, w = bweights[bone]
                for n, i in enumerate (ind):
                    if i < wpvlen:
                        if i not in vertex:
                            vertex[i] = []
                        vertex[i].append((bonenumber, w[n]))
                        lsize += 1
        else:
            lenmap = len(mapping)
            for bone, t in bweights.items():
                bonenumber = self.bonenames[bone]
                ind, w = bweights[bone]
                for n, i in enumerate (ind):
                    if i < lenmap:
                        i = mapping[i]
                        if i < wpvlen and i != -1:
                            if i not in vertex:
                                vertex[i] = []
                            vertex[i].append((bonenumber, w[n]))
                            lsize += 1

        #print ("Verts:" + str(wpvlen))
        #print ("Weight array:" + str(lsize))
        weightpervertex = np.zeros(wpvlen, dtype=np.dtype('i1'))
        joints =  np.zeros(lsize, dtype=np.dtype('i4'))
        weights = np.zeros(lsize, dtype=np.float32)

        i = 0
        for j in range(0, wpvlen):
            cnt = 0
            if j in vertex:
                for n,w in vertex[j]:
                    joints[i] = n
                    weights[i] = w
                    i += 1
                    cnt += 1
            weightpervertex[j] = cnt

        bufwpv    = self.addBufferView(self.WPV_BUFFER, weightpervertex.tobytes())
        bufjoint  = self.addBufferView(self.JOINT_BUFFER, joints.tobytes())
        bufweight = self.addBufferView(self.WEIGHT_BUFFER, weights.tobytes())

        return bufwpv, bufjoint, bufweight

    def addMesh(self, obj, nodenumber, bweights):
        self.mesh_cnt += 1
        (coords, norm, uvcoords, vpface, faces, overflows, mapping) = obj.getVisGeometry(self.hiddenverts)
        # norm is not used
        pos = self.addPosBuffer(coords)
        face = self.addFaceBuffer(faces)
        vpf = self.addVPFBuffer(vpface)
        texcoord = self.addTPosBuffer(uvcoords)

        attrib = { "POSITION": pos, "VPF": vpf, "FACE": face, "TEXCOORD_0": texcoord }

        # add the overflow
        #
        if len(overflows) > 0:
            overflow = self.addOverflowBuffer(overflows)
            attrib["OVERFLOW"] = overflow

        # add weights in case of skeleton
        #
        if bweights is not None:
            attrib["WPV"], attrib["JOINTS"], attrib["WEIGHTS"] = self.addWeightBuffers(coords, bweights, mapping)

        jmesh = {"primitives": [ {"attributes": attrib, "material": nodenumber }]}

        self.json["meshes"].append(jmesh)
        return (self.mesh_cnt)

    def addBone(self, bone, restmat, num):
        """
        add a bone, here we need to change the position (recalculation like in glTF will not work, since we need all bones heads and tails
        """
        if self.onground:
            head = bone.headPos.copy()
            head[1] -= self.lowestPos
            tail = bone.tailPos.copy()
            tail[1] -= self.lowestPos
        else:
            head = bone.headPos
            tail = bone.tailPos

        entry = {"id": num, "name": bone.name, "head": list(head.astype(float)), "tail": list(tail.astype(float))}
        restmat[num] = bone.matRestGlobal
        if bone.parentname:
            entry["parent"] = bone.parentname
        self.bonenames[bone.name] = num       # keep position as an index in dictionary
        return entry

    def addSkeleton(self, skeleton):
        """
        skeleton definition uses an array of bones + pointer to binary restmatrices
        """
        bones = []

        cnt = len(skeleton.bones)
        restmat = np.zeros((cnt, 4,4), dtype=np.float32)
        n = 0
        for bone in skeleton.bones:
            bones.append(self.addBone(skeleton.bones[bone], restmat, n))
            n += 1
        data = restmat.tobytes()
        buf = self.addBufferView( self.RMAT_BUFFER, data)
        self.json["skeleton"] = {"name": self.rootname, "bones": bones, "RESTMAT": buf}

    def addAnimation(self, skeleton, bvh):
        """
        add 3x3 matrix for location, scale, euler-rotation
        only called, when skeleton is available
        """
        cnt = len(skeleton.bones)

        # corrections will be done for calculation, but here animdata must be changed
        #
        bvh.modCorrections()
        corrections = self.glob.baseClass.posecorrections

        animat = np.zeros((bvh.frameCount, cnt, 3,3), dtype=np.float32)

        # set scale before, if bones are not mentioned in bvh, scale will stay 1.0
        #
        for frame in range(bvh.frameCount):
            for num in range(cnt):
                animat[frame, num, 1, 0] = 1.0
                animat[frame, num, 1, 1] = 1.0
                animat[frame, num, 1, 2] = 1.0

        for frame in range(bvh.frameCount):
            for joint in bvh.bvhJointOrder:
                if joint.nChannels > 0:
                    num = self.bonenames[joint.name]
                    f = joint.animdata[frame]

                    # recalculate animdata for corrections
                    #
                    if joint.name in corrections:
                        f = bvh.poseToAnimdata(joint.finalPoses[frame])

                    # allow dislocation only on root bone
                    #
                    if joint.parent is None:
                        animat[frame, num, 0, 0] = f[0] * self.scale    # location
                        animat[frame, num, 0, 1] = f[1] * self.scale
                        animat[frame, num, 0, 2] = f[2] * self.scale
                    else:
                        animat[frame, num, 0, 0] = 0.0
                        animat[frame, num, 0, 1] = 0.0
                        animat[frame, num, 0, 2] = 0.0
                    animat[frame, num, 2, 0] = f[3]     # rotation
                    animat[frame, num, 2, 1] = f[4]
                    animat[frame, num, 2, 2] = f[5]

        animbuf = self.addBufferView(self.ANIM_BUFFER, animat.tobytes())
        self.json["skeleton"]["ANIMMAT"] = animbuf      
        self.json["skeleton"]["nFrames"] = bvh.frameCount

        # reset
        #
        bvh.identFinal()

    def addNodes(self, baseclass, fname):
        #
        # start with all non-meshes using extra buffers (so skeleton with restmatrix etc.)
        #
        # add the basemesh itself, the other nodes will be children
        # here one node will always have one mesh
        #

        # generate name for 'root-object' (skeleton)
        #
        self.rootname = self.nodeName(fname)
        #print (self.rootname)

        # in case of onground we need a translation
        #
        if self.onground:
            self.lowestPos = baseclass.getLowestPos() * self.scale

        baseweights = None

        # add skeleton, if available, then animation (order is significant)
        #
        if baseclass.skeleton is not None:

            # recalculate weights for different skeleton
            #
            baseweights =  baseclass.default_skeleton.bWeights.transferWeights(baseclass.skeleton)

            # rescaling produces a new skeleton, on ground is done by changing bone positions
            #
            if self.scale != 1.0:
                #print ("get a new skeleton")
                skeleton = newSkeleton(self.glob, "copy")
                skeleton.copyScaled(baseclass.skeleton, self.scale, 0.0, True)
            else:
                skeleton = baseclass.skeleton

            self.addSkeleton(skeleton)
            if self.animation and baseclass.bvh:
                self.addAnimation(baseclass.skeleton, baseclass.bvh)

        skin = baseclass.baseMesh.material

        # add the base object,  in case of a proxy use the proxy as first mesh, get weights for proxy
        #
        if baseclass.proxy:
            proxy = baseclass.attachedAssets[0]
            if baseweights is not None:
                proxy.calculateBoneWeights()
                baseweights = proxy.bWeights.transferWeights(baseclass.skeleton)
            baseobject = proxy.obj
            start = 1
        else:
            baseobject = baseclass.baseMesh
            start = 0
        mat  = self.addMaterial(skin)
        if mat == -1:
            return (False)

        mesh = self.addMesh(baseobject, mat, baseweights)

        self.json["nodes"].append({"name": self.nodeName(baseobject.filename, True), "mesh": mesh,  "children": []  })
        self.json["asset"]["nodes"].append(0)
        children = self.json["nodes"][0]["children"]

        childnum = 1

        for elem in baseclass.attachedAssets[start:]:
            mat =  self.addMaterial(elem.obj.material)
            if mat == -1:
                return (False)
            if baseweights is not None:
                elem.calculateBoneWeights()
                weights = elem.bWeights.transferWeights(baseclass.skeleton)
            else:
                weights = None
            mesh = self.addMesh(elem.obj, mat, weights)
            self.json["nodes"].append({"name": self.nodeName(elem.filename, True), "mesh": mesh })
            children.append(childnum)
            childnum += 1

        # now insert correct lenght of available buffers
        #
        self.json["asset"]["buffersize"] =  self.bufferoffset
        self.env.logLine(32, self)
        return (True)


    def apiGetChar(self):
        self.env.last_error ="okay"
        if self.addNodes(self.glob.baseClass, self.glob.baseClass.name) is False:
            return None
        return self.json

    def apiGetBuffers(self):
        return self.buffers

    def binSave(self, baseclass, filename):
        #
        # binary mh2b is:
        # 4 byte magic, 4 byte version + 4 byte length over all (which is the header)
        # JSON chunk:
        # chunklength 4 Byte, chunk type JSON, chunkData (4 Byte boundaries, padding)
        # BIN chunk:
        # chunklength 4 Byte, chunk type JSON, chunkData (4 Byte boundaries, padding)
        self.env.last_error ="okay"
        if self.addNodes(baseclass, filename) is False:
            return False

        version = struct.pack('<I', self.MH2B_VERSION)
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
        # padding is not needed, we only use uint and float

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

        except IOError as error: 
            self.env.last_error = str(error)
            return False
        return True
