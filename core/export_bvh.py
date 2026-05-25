"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * bvhExport

    bvh exporter

    in export we use order XYZ always
    blender: y-forward, z-up
    atm only rotation is used for all bones except root

    Options:

    * on ground is used on each frame for root bone
    * scale must be for offsets and positions in frames
"""
import os
import numpy as np
from obj3d.animation import BVH

class bvhExport:
    """Class representation of BVH export function
    Hint: animation is exported with corrections

    :param glob: handle to global object to access base object etc
    :type glob: :class: globalObjects
    :param bool onground: if character should stay on ground
    :param float scale: the scale of the output
    """

    def __init__(self, glob, onground=False, scale =1.0):

        self.glob = glob
        self.env = glob.env
        self.onground = onground
        self.scale = scale
        self.animYoffset = 0.0
        self.z_up = False
        self.bvh = BVH(glob, "export")
        self.skeldef = []
        self.motion = []
        self.bvhorder = []

    def debug(self, text):
        self.env.logLine (2, "bvh-Export: " + text)

    def calcJoints(self, bones):
        for name, bone in bones.items():
            if bone.parent is None:
                joint = self.bvh.addJoint(name, None)
                joint.offset = bone.headPos
                joint.calculateRestMat()
                joint.channels = ["Xposition", "Yposition", "Zposition", "Xrotation", "Yrotation", "Zrotation"]
            else:
                joint = self.bvh.addJoint(name, self.bvh.joints[bone.parent.name])
                joint.offset = bone.headPos - bone.parent.headPos
                joint.calculateRestMat()
                joint.channels = ["Xrotation", "Yrotation", "Zrotation"]
            if len(bone.children) == 0:
                joint = self.bvh.addJoint("", self.bvh.joints[name])
                joint.offset = bone.tailPos - bone.headPos
                joint.calculateRestMat()
                joint.channels = None

    def calcOffset(self, param):
        if self.z_up:
            return np.array([param[0], -param[2], param[1]], dtype=np.float32)
        else:
            return param

    def writeJoint(self, joint, l):
        """
        write a line with one joint in the bvh header

        :param joint: joint to add
        :type joint: :class: BVHJoint
        :param int l: ident level
        """
        name = joint.name
        l1 = l+1
        offset = self.calcOffset(joint.offset) * self.scale
        if name == "":
            self.skeldef.append("\t" * l1 + "End Site\n" + "\t" * l1 + "{\n")
            self.skeldef.append("\t" * (l1+1) + "OFFSET %f %f %f\n" % (offset[0], offset[1], offset[2]) + "\t" * l1 + "}\n")
            return

        if joint.parent is None:
            # root bone
            #
            self.skeldef.append("ROOT " + name + "\n{\n")
        else:
            self.skeldef.append("\t" * l + "JOINT " + name + "\n" + "\t" * l + "{\n")
        self.bvhorder.append(joint)

        self.skeldef.append("\t" * l1 + "OFFSET %f %f %f\n" % (offset[0], offset[1], offset[2]))
        self.skeldef.append("\t" * l1 + 'CHANNELS %s %s\n' % (len(joint.channels), " ".join(joint.channels)))

        for b in joint.children:
            self.writeJoint(b, l1)
        self.skeldef.append("\t" * l + "}\n")

    def writeMotion(self, skeleton, destbvh, sourcebvh, orig=True):
        """
        create the animation
        - create a mapping from source to dest, works with less bones (no toes) and different skeletons

        :param skeleton: skeleton to get the bones from
        :param destbvh:  destination bvh
        :param sourcebvh: source bvh
        :param bool orig: True is original skeleton
        """
        #
        # create a mapping from source to dest 
        # atm just to deal with different order amd channel number
        # and less bones, also accepts renaming
        #
        jointtable = []
        jointmap = {}
        refmap = {}
        notfound = {}

        sourcebvh.modCorrections()
        corrections = self.glob.baseClass.posecorrections

        # collect all new joints and save index in dict
        #
        cnt = 0
        for joint in self.bvhorder:
            jointtable.append([joint, None])
            jointmap[joint.name] = cnt
            cnt += 1

        # create a reference map for different skeletons
        #
        if orig is False:
            for bone in skeleton.bones.values():
                if len(bone.reference) < 1:
                    refmap[bone.name] = bone.name
                else:
                    refmap[bone.reference[0]] = bone.name

        # now assign internal animation (replace None in jointtable)
        #
        for joint in sourcebvh.bvhJointOrder:
            if joint.name is not None:
                if joint.name in jointmap:
                    jointtable[jointmap[joint.name]][1] = joint
                else:
                    if orig is False:
                        if joint.name in refmap:
                            ref = refmap[joint.name]
                            if ref in jointmap:
                                jointtable[jointmap[ref]][1] = joint

                    else:
                        self.debug(joint.name + " not found")

        for frame in range(0, sourcebvh.frameCount):

            line = ""

            for cnt, (destjoint, sourcejoint)  in enumerate(jointtable):

                # get animdata from source, if sourcejoint is not found, write error only once
                #
                channels = len(destjoint.channels)
                if sourcejoint is None:
                    if destjoint.name not in notfound:
                        self.debug ("No source joint for " + destjoint.name)
                        notfound[destjoint.name] = True
                    line += ("0 " * channels)
                else:
                    # write short output in case a bone is not changed
                    #
                    f = sourcejoint.animdata[frame].copy()

                    # recalculate animdata for corrections
                    #
                    if sourcejoint.name in corrections:
                        f = sourcebvh.poseToAnimdata(sourcejoint.finalPoses[frame])

                    if channels == 3:
                        for c in [3, 4, 5]:
                            if f[c] == 0.0:
                                line += "0 "
                            else:
                                line += ("%f " % f[c])
                    else:
                        pos = f * self.scale
                        if cnt == 0 and self.onground:
                            line += ("%f %f %f " % (pos[0], pos[1], pos[2] + self.animYoffset))
                        else:
                            line += ("%f %f %f " % (pos[0], pos[1], pos[2]))

                        for c in [3, 4, 5]:
                            if f[c] == 0.0:
                                line += "0 "
                            else:
                                line += ("%f " % f[c])

            # replace last blank with newline (empty lines are not allowed)
            #
            if len(line) > 0 and line[-1] == ' ':
                line = line[:-1] + '\n'
                self.motion.append(line)

    def ascSave(self, baseclass, filename):

        if baseclass.skeleton is None:
            self.env.last_error = "No skeleton selected"
            return False

        if baseclass.bvh is None:
            self.env.last_error = "No animation loaded"
            return False

        if self.onground:
            self.animYoffset = baseclass.skeleton.rootLowestDistance(baseclass.bvh.joints, 0, baseclass.bvh.frameCount) * self.scale

        self.z_up = baseclass.bvh.z_up
        bones = baseclass.skeleton.bones
        self.calcJoints(bones)

        header ="HIERARCHY\n"
        self.bvhorder = []
        self.writeJoint(self.bvh.bvhJointOrder[0], 0)

        frameheader = "MOTION\nFrames: %s\nFrame Time: %f\n" % (baseclass.bvh.frameCount, baseclass.bvh.frameTime)

        if baseclass.skeleton == baseclass.default_skeleton:
            self.writeMotion(baseclass.skeleton, self.bvh, baseclass.bvh, True)
        else:
            self.debug ("Animation will be posed by references")
            self.writeMotion(baseclass.skeleton, self.bvh, baseclass.bvh, False)

        try:
            with open(filename, 'w', encoding="utf-8") as f:
                f.write(header)
                for line in self.skeldef:
                    f.write(line)
                f.write(frameheader)
                for line in self.motion:
                    f.write(line)

        except IOError as error:
            self.env.last_error = str(error)
            return False

        return True
                               

