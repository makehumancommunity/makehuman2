"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * BVHJoint
    * BVH
    * MHPose
    * MHPoseFaceConverter
    * PosePrims
"""
import numpy as np
import core.math as mquat
import math

class BVHJoint():
    def __init__(self, name):
        self.name = name
        self.end = name is None
        self.parent = None
        self.nChannels = 0
        self.children = []
        self.animdata = None            # used to store animation data from BVH

        # which channels are used, will contain index [-1, -1, -1, 0, 1, 2] = Xrotation, Yrotation, Zrotation
        #
        self.channelorder = [-1,-1,-1,-1,-1,-1]

        # offset
        #
        self.offset = np.zeros(3,dtype=np.float32)  # fixed relative offset
        self.position = np.zeros(3,dtype=np.float32)  # global position
        self.matRestLocal = None
        self.matRestGlobal = None

        self.matrixPoses = None         # array of local location/rotation matrices for complete animation
        self.finalPoses  = None         # used for combination

    def setDefaultData(self, number):
        """
        set default channels
        """
        if number == 3:
            self.nChannels = number
            self.channelorder = [-1, -1, -1, 0, 1, 2]
        elif number == 6:
            self.nChannels = number
            self.channelorder = [0, 1, 2, 3, 4, 5]

    def initFrames(self, count: int):
        self.animdata = np.zeros(shape=(count, 6), dtype=np.float32)
        self.matrixPoses = np.zeros((count,3,4), dtype=np.float32)
        self.matrixPoses[:,:3,:3] = np.identity(3, dtype=np.float32)

    def identFinal(self):
        self.finalPoses  = self.matrixPoses     # just copy pointer

    def cloneToFinal(self):
        self.finalPoses = np.copy(self.matrixPoses)

    def resetFinal(self, count: int):
        self.finalPoses = np.zeros((count,3,4), dtype=np.float32)
        self.finalPoses[:,:3,:3] = np.identity(3, dtype=np.float32)

    def modCorrections(self, corr, parent, count:int):
        self.finalPoses = np.zeros((count,3,4), dtype=np.float32)
        if parent is not None:
            self.finalPoses[:,:3,:3] = np.matmul(self.matrixPoses[:,:3,:3], corr[:3,:3])
        else:
            for i in range (0, count):
                self.finalPoses[i,:3,:4] = np.matmul(self.matrixPoses[i], corr)[:3,:4]

    def calculateRestMat(self):
        """
        calculates the rest matrix
        """
        # Calculate absolute joint position
        if self.parent:
            self.position = np.add(self.parent.position, self.offset)
        else:
            self.position = self.offset[:]

        # Create relative rest matrix for joint (only translation)
        self.matRestLocal = np.identity(4, dtype=np.float32)
        self.matRestLocal[:3,3] = self.offset

        # Create world rest matrix for joint (only translation)
        self.matRestGlobal = np.identity(4, dtype=np.float32)
        self.matRestGlobal[:3,3] = self.position


    def __repr__(self):
        output = self.name if self.name is not None else "end-site"
        return output + " " + str(self.channelorder) + " " + str(self.animdata)

class BVH():
    """
    BVH class
    * it will not accept a changing rotation order
    """
    def __init__(self, glob, name):
        self.glob = glob
        self.env = glob.env
        self.name = name
        self.filename = None

        self.skeleton = self.glob.baseClass.pose_skeleton   # pose skeleton used for animation

        self.bvhJointOrder = []
        self.joints = {}
        self.frameCount = 1       # one frame at least (could be rest pose), will contain number of frames
        self.frameTime = 0.041667 # preset that to 1/24 sec
        self.currentFrame = 0  # is used for animplayer
        self.pi_mult = math.pi / 180.0

        #
        # channels and rotations
        #
        self.channelname = {"Xposition":0, "Yposition":1, "Zposition":2, "Xrotation":3, "Yrotation":4, "Zrotation":5}

        self.dislocation = False        # allow dislocation of bones (usually only root can be moved), also face has no dislocation
        self.z_up = True                # read in different direction
        self.rotationorder = "yzx"      # usually it would be zyx, but z-up it is zyx (first rotation is used last)

    def createDefaultAnimation(self):
        """
        a one frame default animation created from pose skeleton
        """
        for name, bone in self.skeleton.bones.items():
            if bone.parent is not None:
                boneptr = self.joints[bone.parent.name]
            else:
                boneptr = None
            self.addJoint(name, boneptr)

        # add additional values (channels) and copy rest matrix from skeleton
        #
        for elem in self.bvhJointOrder:
            elem.setDefaultData(3 if elem.parent is not None else 6)
            sourcebone = self.skeleton.bones[elem.name]
            elem.matRestLocal = sourcebone.matRestLocal
            elem.matRestGlobal = sourcebone.matRestGlobal

        # and create one frame
        #
        self.frameCount = 1
        self.initFrames()
        self.identFinal()

    def keyParam(self, key, fp):
        param = fp.readline().split()
        if param[0] != key:
            self.env.last_error = key + " expected in line " + " ".join(param)
            return None
        return param[1:]

    def addJoint(self, name, parent):
        joint = BVHJoint(name)
        if name is not None:
            self.joints[name] = joint
        self.bvhJointOrder.append(joint)
        joint.parent = parent
        if parent is not None:
            parent.children.append(joint)
        return joint

    def getChannelOrder(self, joint, fp):
        param = self.keyParam('CHANNELS', fp)
        if param is None:
            return False

        nChannels = int(param[0])
        if nChannels != len(param)-1:
            self.env.last_error = "BVH-File: channels indicated and number of channels differ"
            return False

        if nChannels == 0:
            self.env.last_error = "BVH-File: joints with 0 channels not yet supported"
            return False

        for cnt, channel in enumerate(param[1:]):
            if channel in self.channelname:
                joint.channelorder[self.channelname[channel]] = cnt
        joint.nChannels = nChannels
        return True

    def getOffset(self, param):
        if self.z_up:
            return ([float(param[0]), float(param[2]), -float(param[1])])
        else:
            return ([float(param[0]), float(param[1]), float(param[2])])

    def readJointHierarchy(self, joint, fp):
        if self.keyParam('{', fp) is None:
            return False

        param = self.keyParam('OFFSET', fp)
        if param is None:
            return False

        # Calculate position from offset
        #
        joint.offset = self.getOffset(param)
        if self.getChannelOrder(joint, fp) is False:
            return False

        # Read child joints
        while True:
            line = fp.readline()
            words = line.split()

            if words[0] == 'JOINT':
                child = self.addJoint(words[1], joint)
                if self.readJointHierarchy(child, fp) is False:
                    return False

            elif words[0] == 'End': # Site
                child = self.addJoint(None, joint)
                if self.keyParam('{', fp) is None:
                    return False

                param = self.keyParam('OFFSET', fp)
                if param is None:
                    return False

                child.offset = self.getOffset(param)
                if self.keyParam('}', fp) is None:
                    return False

            elif words[0] == '}':
                break
            else:
                self.env.last_error = "BVH-File: unexpected end of file."
                return False

        return True

    def initFrames(self):
        for joint in self.bvhJointOrder:
            joint.initFrames(self.frameCount)

    def identFinal(self):
        """
        copies pointers only
        """
        for joint in self.bvhJointOrder:
            joint.identFinal()

    def cloneToFinal(self):
        """
        clones animation
        """
        for joint in self.bvhJointOrder:
            joint.cloneToFinal()

    def calcLocRotMat(self, frame, data):
        """
        calculation is done once after loading the file
        it is always order yzx since it only works for z_up (and order is already sorted)

        :param frame: frame number
        :param data:  array of bvh data
        """
        i = 0
        for joint in self.bvhJointOrder:
            if joint.nChannels > 0:
                for j, m in enumerate(joint.channelorder):
                    if m>=0:
                        r = data[i+m]
                        if -0.0001 < r < 0.0001:
                            r = 0.0
                        joint.animdata[frame, j ] = r
                i += joint.nChannels
                x = self.pi_mult * joint.animdata[frame, 3]
                #
                if self.z_up:
                    y = -self.pi_mult * joint.animdata[frame, 4]
                else:
                    y = self.pi_mult * joint.animdata[frame, 4]
                z = self.pi_mult * joint.animdata[frame, 5]

                joint.matrixPoses[frame,:3,:3] = mquat.eulerMatrix(z, y, x, self.rotationorder)[:3,:3]
                #
                if joint.parent is None or self.dislocation:
                    joint.matrixPoses[frame,:3,3] = [joint.animdata[frame, 0], joint.animdata[frame, 2], joint.animdata[frame, 1]]

    def poseToAnimdata(self, matrixPose):
        """
        calculate corrected animdata for Blender output from matrixPose (finalPose)
        """
        animdata = np.zeros(6, dtype=np.float32)
        x, y, z = mquat.eulerMatrixYZXToDegrees(matrixPose[:3,:3])
        animdata[:] = [matrixPose[0,3],matrixPose[2,3], matrixPose[1,3], z, -y, x]
        return animdata

    def noFaceAnimation(self):
        bc = self.glob.baseClass
        if bc.faceunits is not None:
            for joint in self.bvhJointOrder:
                if joint.name in bc.faceunits.bonemask:
                    joint.resetFinal(self.frameCount)

    def modCorrections(self, corrections=None, positioncorrection=None):
        if corrections is None:
            corrections = self.glob.baseClass.posecorrections
        if positioncorrection is None:
            positioncorrection = self.glob.baseClass.positioncorrection

        self.skeleton.setOffset(positioncorrection)
        if corrections is not None:
            for joint in self.bvhJointOrder:
                if joint.name in corrections:
                    # print ("Need to change", joint.name)
                    joint.modCorrections(corrections[joint.name], joint.parent, self.frameCount)
                else:
                    # also allow face animation again
                    joint.identFinal()

            # this is done to allow corrections on non-mentioned bones of animation
            for bname in corrections:
                if bname not in self.joints:
                    if bname in self.skeleton.bones:
                        bone = self.skeleton.bones[bname]
                        bone.calcLocalPoseMat(corrections[bname][:3,:3])
                        bone.calcGlobalPoseMat()
                        bone.poseBone()

    def MHPoseToAnimation(self, mhpose):
        #if pos is not None:
        #    self.skeleton.setOffset(pos)
        corrections = {}
        changed = self.skeleton.posebyBlends(mhpose.blends, None)

        if len(changed) > 0:
            for bone in changed:
                elem = self.skeleton.bones[bone]
                corrections[bone] = elem.getRelativeCorrection()
            self.modCorrections(corrections)
        else:
            # no blends at all, reset
            #
            self.identFinal()


    def debugChanged(self, num):
        """
        print a frame (pose) for debugging
        in case of location vector is 0, only rotation is printed

        :param num: frame number
        """
        np.set_printoptions(precision=3, suppress=True)
        restmatrix= np.zeros((3,4), dtype=np.float32)
        restmatrix[:3,:3] = np.identity(3, dtype=np.float32)
        print ("Frame: " + str(num))
        for joint in self.bvhJointOrder:
            m = joint.matrixPoses[num]
            if not np.array_equiv(m,restmatrix):
                s = m[:3,:3].flatten().astype(float).tolist()
                s = [round(x, 3) for x in s]
                if np.count_nonzero(m[:,3]) == 0:
                    print("\"" + joint.name + "\": " + str(s))
                else:
                    d = m[:3,3].flatten().astype(float).tolist()
                    d = [round(x, 3) for x in d]
                    print("\"" + joint.name + "\": " + str(s) + " d=" + str(d))

    def debugJoints(self, name):
        for joint in self.bvhJointOrder:
            if joint.name == name:
                print (joint.name)
                print (joint.offset)
                print (joint.position)
                print (joint.matRestLocal)
                print (joint.matRestGlobal)
                print (joint.animdata)
                print (joint.matrixPoses)


    def calcBVHRestMat(self):
        for joint in self.bvhJointOrder:
            joint.calculateRestMat()

    def load(self, filename):
        self.filename = filename
        self.env.logLine(8, "Load bvh " + filename)
        with open(filename, "r", encoding='utf-8') as fp:
            # starts with HIERARCHY 
            # ROOT
            if self.keyParam('HIERARCHY', fp) is None:
                return False

            param = self.keyParam('ROOT', fp)
            if param is None:
                return False

            root = self.addJoint(param[0], None)   # add root joint
            if self.readJointHierarchy(root, fp) is False:
                return False

            # calculate BVH rest matrix and offset
            #
            self.calcBVHRestMat()

            if self.keyParam('MOTION', fp) is None:
                return False

            param = self.keyParam('Frames:', fp)
            if param is None:
                return False
            self.frameCount = int(param[0])

            param = self.keyParam('Frame', fp) # Time:
            if param is None:
                return False
            self.frameTime = float(param[1])

            self.initFrames()

            for i in range(self.frameCount):
                words = fp.readline().split()
                data = [float(word) for word in words]
                self.calcLocRotMat(i, data)
                if self.env.verbose & 32:
                    self.debugChanged(i)

        # make a copy of the pointers
        self.identFinal()
        return True

class MHPose():
    """
    class for combined poses and expressions
    """
    def __init__(self, glob, units, name):
        self.glob = glob
        self.env = glob.env
        self.name = name
        self.description =""
        self.license =""
        self.author =""
        self.filename = None
        self.units = units.units
        self.blends = []
        self.tags = []
        self.poses = {}

    def load(self, filename, convert=None):
        self.filename = filename
        pose = self.env.readJSON(filename)
        if pose is None:
            return False, self.env.last_error

        if convert:
            pose = convert(pose)

        for elem, weight in pose["unit_poses"].items():
            self.poses[elem] = weight
            if elem in self.units:
                if weight < 0.0:
                    if "reverse" in self.units[elem]:
                        m = self.units[elem]["reverse"]
                        self.blends.append([m, -weight * 100])
                else:
                    if "bones" in self.units[elem]:
                        m = self.units[elem]["bones"]
                        self.blends.append([m, weight * 100])

        for elem in ("name", "author", "description", "tags", "license"):
            if elem in pose:
                setattr (self, elem, pose[elem])
            else:
                setattr (self, elem, "")
        return True, "Okay"

    def save(self, filename, json):
        json["name"] = self.name
        return self.env.writeJSON(filename, json)


class MHPoseFaceConverter():
    """
    class to convert old Pose-files to use double-sided sliders
    """
    def __init__(self):
        self.reverse = {
                "LeftUpperLidOpen": "LeftUpperLidClosed",
                "RightUpperLidOpen": "RightUpperLidClosed",
                "LeftEyeturnLeft": "LeftEyeturnRight",
                "RightEyeturnLeft": "RightEyeturnRight",
                "LeftEyeUp": "LeftEyeDown",
                "RightEyeUp": "RightEyeDown",
                "ChinRight": "ChinLeft",
                "lowerLipUp": "lowerLipDown",
                "lowerLipBackward": "lowerLipForward",
                "UpperLipBackward": "UpperLipForward",
                "MouthMoveRight": "MouthMoveLeft",
                "MouthLeftPullDown": "MouthLeftPullUp",
                "MouthRightPullDown": "MouthRightPullUp",
                "TongueRight": "TongueLeft",
                "TongueDown": "TongueUp",
                "TonguePointDown": "TonguePointUp"
        }
        self.rename = {
                "LeftEyeturnRight": "LeftEyeturn",
                "RightEyeturnRight": "RightEyeturn",
                "LeftEyeDown": "LeftEyeVertical",
                "RightEyeDown": "RightEyeVertical",
                "ChinLeft": "ChinRotate",
                "lowerLipDown": "lowerLipVertical",
                "lowerLipForward": "lowerLipDepth",
                "UpperLipForward": "UpperLipDepth",
                "MouthMoveLeft": "MouthMove",
                "MouthLeftPullUp": "MouthLeftPullVertical",
                "MouthRightPullUp": "MouthRightPullVertical",
                "TongueLeft": "TongueHorizontal",
                "TongueDown": "TongueVertical",
                "TonguePointDown": "TonguePointVertical"
        }

    def convert(self, json):
        deletes = []
        newones = {}
        u = json["unit_poses"]

        # pass1 : replacement, avoids also contradictions
        #
        for key, val in u.items():
            if key in self.reverse:
                contrary = self.reverse[key]
                if contrary in u:
                    u[contrary] -= val
                    deletes.append(key)
                else:
                    deletes.append(key)
                    newones[contrary] = -val

        # changes pass 1
        #
        for key in deletes:
            del u[key]
        for key, val in newones.items():
            u[key] = val

        # pass2 : renaming
        #
        deletes = []
        newones = {}
        for key, val in u.items():
            if key in self.rename:
                newname = self.rename[key]
                deletes.append(key)
                newones[newname] = val

        # changes pass 2
        #
        for key in deletes:
            del u[key]
        for key, val in newones.items():
            u[key] = val
        return json

class PosePrims():
    def __init__(self, glob):
        self.glob = glob
        self.env = glob.env
        self.units = None
        self.filterparam = None
        self.groups   = []
        self.bonemask = []

    def __str__(self):
        return str(self.units.keys())

    def getInfo(self):
        return self.units

    def createFilterDict(self):
        self.filterparam = []
        for elem in self.groups:
            self.filterparam.append(elem)
        return self.filterparam

    def load(self, name):
        filename =self.env.existDataFile("base", self.env.basename, name)
        if filename is None:
            return False, name + " is not existent"

        prims = self.env.readJSON(filename)
        if prims is None:
            return False, self.env.last_error

        # create a bone mask and collect groups,
        # in the dictionary the values are replaced by 3x3 posematrices instead of the array

        for val in prims.values():
            if "group" in val:
                g = val["group"]
                if g not in self.groups:
                    self.groups.append(g)

            if "position" in val:
                continue

            if "bones" in val:
                g = val["bones"]
                for bone in g:
                    g[bone] = np.asarray(g[bone], dtype=np.float32).reshape(3,3)
                    if bone not in self.bonemask:
                        self.bonemask.append(bone)

            if "reverse" in val:
                g = val["reverse"]
                for bone in g:
                    g[bone] = np.asarray(g[bone], dtype=np.float32).reshape(3,3)

        self.units = prims
        return True, "Okay"

