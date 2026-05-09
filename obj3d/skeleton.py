"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * skeleton
"""

import numpy as np
from PySide6.QtGui import QVector3D
from obj3d.bone import cBone, boneWeights
import core.math as mquat

class skeleton:
    def __init__(self, glob, name):
        self.glob = glob
        self.env  = glob.env
        self.name = name            # maybe replaced by json
        self.filename = None
        self.newSkeleton()

    def newSkeleton(self):
        self.jointVerts = {} # vertices for position (median calculation)
        self.planes = {}
        self.bones = {}      # list of cBones
        self.bWeights = None
        self.root = None     # our skeleton accepts one root bone, not more, name of the root
        self.offset = QVector3D(0, 0, 0) # offset is used for pose skeleton to move root bone
        self.use_offset = False
        self.mesh = self.glob.baseClass.baseMesh
        self.filename = None

    def __str__(self):
        return "Skeleton: " + self.name

    def loadJSON(self, path):
        json = self.env.readJSON(path)
        if json is None:
            return False

        # replace name for internal file
        #
        if "name" in json:
            self.name = json["name"]

        # check for main elements in json file:
        #
        for elem in ["joints", "bones"]:
            if elem not in json:
                self.env.logLine(1, "JSON " + elem + " is missing in " + path)
                return False

        # read joints into a list (avoid wrong types)
        #
        j = json["joints"]
        for name, val in j.items():
            if isinstance(val, list) and len(val) > 0:
                self.jointVerts[name] = val

        # read planes into a list
        #
        if "planes" in json:
            self.planes = json["planes"]

        # integrity test, all bones have a valid parent bone, one bone is root, rotation plane is valid,
        # head, tail are available
        #
        j = json["bones"]
        for bone, val in j.items():
            if "head" not in val:
                self.env.logLine(1, "head is missing for " + bone + " in " + path)
                return False
            if "tail" not in val:
                self.env.logLine(1, "tail is missing for " + bone + " in " + path)
                return False

            if "rotation_plane" in val:
                plane = val["rotation_plane"]
                if plane in self.planes:
                    if self.planes[plane] == [None, None, None]:
                        self.env.logLine(1, "Invalid rotation plane " + plane + " in " + path)
                        return False
                else:
                    self.env.logLine(1, "Rotation plane " + plane + " is missing in " + path)
                    return False

            if "parent" in val and val["parent"] is not None:
                p = val["parent"]
                if p not in j:
                    self.env.logLine(1, "Parent bone of " + bone + ": " + p + " is missing in " + path)
                    return False

            else:
                if self.root is not None:
                    self.env.logLine(1, "Only one root accepted. Found: " + self.root + ", " + bone + " in " + path)
                    return False
                if "parent" not in val:
                    json["bones"][bone]["parent"] = None        # in case it is missing
                self.root = bone

        if self.root is None:
            self.env.logLine(1, "Missing root bone (bone without parent) in " + path)
            return False

        # read weights (either default or own)
        #
        weightname = json["weights_file"] if "weights_file" in json else "default_weights.mhw"
        weightfile = self.env.existDataFile("rigs", self.env.basename, weightname)
        if weightfile is None:
            self.env.logLine(1, "Missing weight file " + weightname)
            return False

        self.bWeights = boneWeights(self.glob, self, self.mesh)
        self.bWeights.loadJSON(weightfile)

        # array with ordered bones
        #
        orderedbones = [self.root]
        pindex = 0

        while pindex < len(j):
            if pindex < len(orderedbones):
                for bone in j:
                    if bone not in orderedbones:
                        val = j[bone]
                        if "parent" in val and val["parent"] == orderedbones[pindex]:
                            orderedbones.append(bone)
            pindex += 1

        for bone in orderedbones:
            val = j[bone]
            rotplane = val["rotation_plane"] if "rotation_plane" in val else 0
            reference = val["reference"] if "reference" in val else None
            weights = val["weights_reference"] if "weights_reference" in val else None
            cbone = cBone(self, bone, val["parent"], val["head"], val["tail"], rotplane, reference, weights)
            self.bones[bone] = cbone

        """
        for bone in  self.bones:
            print (self.bones[bone])
        """
        # in case it cannot calculate inverse binding, just say it here and avoid skeleton
        #
        if self.calcRestMat() is False:
            return False
        self.filename = path
        return True

    def setOffset(self, position):
        self.offset.setX(position[0])
        self.offset.setY(position[1])
        self.offset.setZ(position[2])

    def useOffset(self, b):
        self.use_offset = b

    def copyScaled(self, source, scale, offset, useOrigRotation):
        """
        generate a resized skeleton

        ;param class skeleton source: source skeleton
        ;param float scale: new scale of the charater
        ;param float offset: offset as replacement
        ;param bool useOrigRotation: reset rotation to original (blender only, not gltf)
        """

        self.jointVerts = source.jointVerts
        self.bWeights = source.bWeights

        for bone in source.bones:
            b = source.bones[bone]

            cbone = cBone(self, b.name, b.parentname, b.head, b.tail, b.localplane, b.reference, b.weightref)
            head, tail = b.getJointPos()
            head = np.asarray(head, dtype=np.float32)
            tail = np.asarray(tail, dtype=np.float32)
            head[1] -= offset
            tail[1] -= offset
            cbone.assignJointPos(head * scale , tail * scale)
            self.bones[bone] = cbone

        self.calcRestMat()

        # use the rotations from original skeleton
        #
        if useOrigRotation:
            for bone in source.bones:
                s = source.bones[bone]
                d = self.bones[bone]
                d.matRestGlobal[:3,:3] = s.matRestGlobal[:3,:3]

    def getNormal(self, plane_name):
        """
        planes are used counter-clockwise
        returns normalized vector
        """
        if plane_name in self.planes:
            v = [None, None, None]
            for cnt, jointname in enumerate(self.planes[plane_name][:3]):
                v[cnt] = np.asarray(self.mesh.getMeanPosition(self.jointVerts[jointname]), dtype=np.float32)
            
            diff = v[1]-v[0]
            pvec = diff / np.linalg.norm(diff)
            diff = v[2]-v[1]
            yvec = diff / np.linalg.norm(diff)
            cross = np.cross(yvec, pvec)
            return (cross / np.linalg.norm(cross))
        else:
            return np.asarray([0,1,0], dtype=np.float32)

    def calcRestMat(self):
        for bone in self.bones:
            if self.bones[bone].calcRestMatFromSkeleton() is False:
                return False
        return True

    def newGeometry(self):
        """
        geometry changes, recalculate joint positions + rest matrix
        """
        for bone in  self.bones:
            self.bones[bone].setJointPos()
        self.calcRestMat()

    def calcLocalPoseMat(self, poses):
        for i, bone in  enumerate(self.bones):
            self.bones[bone].calcLocalPoseMat(poses[i])

    def calcGlobalPoseMat(self):
        for bone in  self.bones:
            self.bones[bone].calcGlobalPoseMat()

    def skinBasemesh(self):
        self.skinMesh(self.mesh, self.bWeights)

    def skinMesh(self, mesh, bWeights):
        vmapping = bWeights.bWeights

        coords = np.zeros((mesh.n_origverts,3), float)        # own vector
        l = len(mesh.gl_coord) // 3

        meshCoords = np.ones((l, 4), dtype=np.float32)
        meshCoords[:,:3] = np.reshape(mesh.gl_coord_w, (l,3))

        for bname in vmapping:
            bone = self.bones[bname]

            verts, weights = vmapping[bname]
            vec = np.dot(bone.matPoseVerts, meshCoords[verts].transpose())
            vec *= weights
            coords[verts] += vec.transpose()[:,:3]

        m = coords.flatten()
        mesh.gl_coord[:mesh.n_origverts*3] = m[:]
        mesh.overflowCorrection(mesh.gl_coord)


    def restPose(self, bones_only=False):
        for bone in self.bones:
            self.bones[bone].restPose()
            self.bones[bone].calcGlobalPoseMat()
            self.bones[bone].poseBone()

        # in case of restpose, pose with update function and not with pose function
        #
        if not bones_only:
            self.skinBasemesh()
            self.glob.baseClass.updateAttachedAssets()

    def poseFromRestPose(self, changes, bones_only=False):
        """
        pose the skeleton starting from rest pose for corrections only

        :param joints: changes dictionary
        :param bones_only: if True, no skinning
        """
        # reset to rest pose
        self.restPose(bones_only)

        for elem, bone in self.bones.items():
            # pose each cBone which is mentioned in changes
            #
            if elem in changes:
                bone.calcLocalPoseMat(changes[elem][:3,:3])

            bone.calcGlobalPoseMat()
            bone.poseBone()

        if not bones_only:
            self.skinBasemesh()
            self.glob.baseClass.poseAttachedAssets()

    def pose(self, joints: dict, frame=0, bones_only=False):
        """
        pose the skeleton

        :param joints: BVHJoint dictionary
        :param frame: frame number
        :param bones_only: if True, no skinning
        """
        for elem, bone in self.bones.items():

            # pose each cBone which is mentioned in joints
            #
            if elem in joints:
                bone.calcLocalPoseMat(joints[elem].finalPoses[frame])

            bone.calcGlobalPoseMat()
            bone.poseBone()

        if not bones_only:
            self.skinBasemesh()
            self.glob.baseClass.poseAttachedAssets()

    def poseByReference (self, joints: dict, frame=0):
        """
        pose the skeleton by reference of another skeleton
        either bone is found with the same name in default skeleton 
        or one bone references one or more other bones of default skeleton

        :param joints: BVHJoint dictionary
        :param frame: frame number
        """
        for elem, bone in self.bones.items():

            # pose each cBone reference which is mentioned in joints, multiply pose matrices
            # if root is referenced do not multiply other matrices
            #
            if len(bone.reference) > 0:
                m1 = None
                for ref in bone.reference:
                    if ref in joints:
                        m = joints[ref].finalPoses[frame]
                        if joints[ref].parent is None:
                            m1 = m
                            break
                        if m1 is None:
                            m1 = m
                        else:
                            m2 = np.matmul(m[:3,:3], m1[:3,:3])
                            m1[:3,:3] = m2

                if m1 is not None:
                   bone.calcLocalPoseMat(m1)
            else:
                # in case of no reference, try it directly (skeletons like default-notoes)
                #
                if elem in joints:
                    bone.calcLocalPoseMat(joints[elem].finalPoses[frame])
            
            bone.calcGlobalPoseMat()
            bone.poseBone()


    def rootLowestDistance(self, joints, fromframe=0, toframe=-1):
        """
        get difference between root-bone and floor to calculate distance from ground
        this is an estimation
        """
        if toframe == -1:
            toframe = fromframe+1
        mdiff = 0.0

        for frame in range(fromframe, toframe):
            yroot = 0.0
            ylow  = 1000.0
            for elem, bone in self.bones.items():
                if elem in joints:
                    bone.calcLocalPoseMat(joints[elem].finalPoses[frame])

                bone.calcGlobalPoseMat()
                bone.poseBone()
                if bone.parent is None:
                    yroot = bone.poseheadPos[1]
                else:
                    if bone.poseheadPos[1] < ylow:
                        ylow = bone.poseheadPos[1]
            diff = yroot - ylow
            if diff > mdiff:
                mdiff = diff
        return mdiff

    def posebyBlends(self, blends, mask, bones_only=False):
        """
        function used for expressions, with mask set all unchanged bones will be set to rest position
        """
        changed = []

        if len(blends) == 0:
            return changed

        # check bonewise if blend is used, then use quaternionsSlerpFromMatrix with ratio to pose
        # in case the bone is posed by more than one posemat, multiply quaternion matrices
        #
        found = {}
        for bone, elem in self.bones.items():
            modbone = False
            for blend in blends:
                posemat = blend[0]
                ratio = blend[1] / 100
                if bone in posemat:
                    found[bone] = True
                    if modbone is True:
                        q2 = mquat.quaternionSlerpFromMatrix(posemat[bone], ratio)
                        q1 = mquat.quaternionMult(q1, q2)
                    else:
                        q1 = mquat.quaternionSlerpFromMatrix(posemat[bone], ratio)
                    modbone = True

            if modbone is True:
                mat = mquat.quaternionToRotMatrix(q1)
                elem.calcLocalPoseMat(mat)
                changed.append(bone)

            elem.calcGlobalPoseMat()
            elem.poseBone()

        if mask is not None:
            for bone in mask:
                if bone not in found:
                    self.bones[bone].restPose()
                    self.bones[bone].calcGlobalPoseMat()
                    self.bones[bone].poseBone()

        if not bones_only:
            self.skinBasemesh()
            self.glob.baseClass.poseAttachedAssets()

        return changed

