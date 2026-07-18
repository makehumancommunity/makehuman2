import bpy
import json
import os
import struct
from bpy_extras.io_utils import (ImportHelper, ExportHelper)
from mathutils import Vector, Matrix, Euler
from math import radians
from bpy.props import StringProperty
from .materials import MH2B_OT_Material

class MH2B_OT_Loader:
    def __init__(self, context):
        self.context = context
        self.firstnode = 0
        self.firstname = "unknown"
        self.collection = None
        self.bufferoffset = 0
        self.skeleton = None
        self.armature = None
        self.bonelist = {}
        self.bonecorr = {}
        self.subsurf = context.scene.MH2B_subdiv

    def activateObject(self, ob):
        scn = self.context.scene
        for ob1 in scn.collection.objects:
            ob1.select_set(False)
        ob.select_set(True)
        self.context.view_layer.objects.active = ob

    def deleteCollection(self, name):
        if name == "":
            return False

        collection = bpy.data.collections.get(name)
        if collection is None:
            return False

        for obj in collection.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(collection)
        return True

    def createCollection(self, jdata):
        #
        # get collection name from the referenced asset in nodes
        #
        self.firstnode = jdata["asset"]["nodes"][0]
        self.firstname = jdata["nodes"][self.firstnode]["name"]

        # create a new collection and add it to scene
        self.collection  = bpy.data.collections.new(self.firstname)
        self.context.scene.collection.children.link(self.collection )
        return (self.collection )

    def getData(self, inputp, length):
        """
        read data from file or from bytearray
        """
        if isinstance(inputp, bytearray):
            buf = inputp[self.bufferoffset:self.bufferoffset+length]
        else:
            buf = inputp.read(length)
        self.bufferoffset += length
        return buf

    def getBuffers(self, jdata, attrib, fp):
        """
        get all data from buffers
        * sort buffers first to be able to read them without seeking
        * control the buffers
        * read and prepare faces, uvs
        * return all parameters
        """

        binfo = []
        names  = ['FACE', 'JOINTS', 'OVERFLOW', 'POSITION', 'TEXCOORD_0', 'VPF', 'WEIGHTS', 'WPV' ]
        for name in names:
            if name in attrib:
                item = attrib[name]
                binfo.append((name, jdata["bufferViews"][item]["byteOffset"], jdata["bufferViews"][item]["byteLength"]))

        binfo.sort(key=lambda tup: tup[1])  # sort by byteoffset

        # now test if we have gaps
        name, lastpos, lastlen  = binfo[0]
        newpos = lastpos + lastlen
        for name, pos, length in binfo[1:]:
            if pos != newpos:
                return (None)
            newpos = pos + length

        overflow = {}

        faces   = []
        joints  = []
        pos     = []
        texco   = []
        vpf     = []
        weights = []
        wpv     = []

        for name, start, length in binfo:
            print ("read " + str(length) + " bytes for " + name)
            buf = self.getData(fp, length)
            if name == 'FACE':
                m = struct.iter_unpack('<i',  buf)
                for l in m:
                    faces.append(l)

            elif name == 'JOINTS':
                m = struct.iter_unpack('<i',  buf)
                for l in m:
                    joints.append(l[0])

            elif name == 'OVERFLOW':
                m = struct.iter_unpack('<ii',  buf)
                for l in m:
                    overflow[l[1]] = l[0]

            elif name == 'POSITION':
                m = struct.iter_unpack('<fff',  buf)
                for l in m:
                    pos.append((l[0], -l[2], l[1]))

            elif name == 'TEXCOORD_0':
                m = struct.iter_unpack('<ff',  buf)
                for l in m:
                    texco.append(l)

            elif name == 'VPF':
                m = struct.iter_unpack('<B',  buf)
                for l in m:
                    vpf.append(l)

            elif name == 'WEIGHTS':
                m = struct.iter_unpack('<f',  buf)
                for l in m:
                    weights.append(l[0])

            else:   # WPV
                m = struct.iter_unpack('<B',  buf)
                for l in m:
                    wpv.append(l[0])

        print ("calculate faces and uvs")

        maxp =  len(pos)

        bfaces = []
        ufaces = []

        n = 0
        for nfaces in vpf:
            l = nfaces[0]
            c = []
            u = []
            faceok = True
            for i in range(0,l):
                v = faces[n][0]
                n += 1
                u.append(v)
                if v in overflow:
                    v = overflow[v]
                if v >= maxp:
                    faceok = False
                c.append(v)
            if faceok:
                bfaces.append(tuple(c))
                ufaces.append(tuple(u))

        bufarr = [pos, bfaces, texco, ufaces, wpv, joints, weights]
        return (bufarr)
    
    def createVGroups(self, ob, wpv, joints, weights):
        bonenums = {}
        vgroups = []
        for l in joints:
            bonenums[l] = 1

        for l in self.bonelist:
            vgrp = None
            if l in bonenums:
                vgname = self.bonelist[l]
                vgrp = ob.vertex_groups.new(name=vgname)
            vgroups.append(vgrp)
                

        i = 0
        for vn, cnt in enumerate(wpv):
            for l in range(0, cnt):
                jnum = joints[i]
                weight = weights[i]
                vgroups[jnum].add([vn], weight, 'REPLACE')
                i += 1


    def getMesh(self, jdata, name, num, fp, dirname):

        m = jdata["meshes"][num]["primitives"][0]   # only one primitive
        attributes = m["attributes"]
        result = self.getBuffers(jdata, attributes, fp)
        if result is None:
            return None
        print ("dirname: ", dirname)   
        (coords, faces, uvdata, uvfaces, wpv, joints, weights)  = result

        mesh = bpy.data.meshes.new(name)
        nobject = bpy.data.objects.new(name, mesh)
        mesh.from_pydata( coords, [], faces, shade_flat=False)

        mesh.uv_layers.new()
        uvlayer =  mesh.uv_layers[0]
        n=0
        for face in uvfaces:
            for vert in face:
                uvlayer.data[n].uv = (uvdata[vert][0], 1.0 - uvdata[vert][1])
                n += 1

        # create groups
        #
        if self.skeleton:
            print ("Create a skeleton")
            self.createVGroups(nobject, wpv, joints, weights)
            mod = nobject.modifiers.new('ARMATURE', 'ARMATURE')
            mod.use_vertex_groups = True
            mod.use_bone_envelopes = False
            mod.object = self.skeleton


        if "material" in m:
            material =  m["material"]
            mclass = MH2B_OT_Material(self.context, dirname)
            blendmat = mclass.addMaterial(jdata, material)
            nobject.data.materials.append(blendmat)

        if self.subsurf is True:
            modifier = nobject.modifiers.new(name="Subdivision", type='SUBSURF')

        return(nobject)

    def getSkeleton(self, jdata, fp):
        """
        read restmatrix then create skeleton by tail, head, matrix and parent relation-ship
        """
        skel =  jdata["skeleton"]
        restmatnum = skel["RESTMAT"]
        length = jdata["bufferViews"][restmatnum]["byteLength"] 
        print ("restmat need to read " + str(length) + " bytes")
        buf = self.getData(fp, length)
        restmat = list(struct.iter_unpack('<ffffffffffffffff',  buf))

        # prepare skeleton
        #
        amt = bpy.data.armatures.new(skel["name"])
        self.armature = amt
        rig = bpy.data.objects.new(skel["name"], amt)
        setattr(amt, "display_type", 'STICK')
        setattr(rig, "show_in_front" , True)
        self.collection.objects.link(rig)
        self.activateObject(rig)

        # edit bones
        #
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in skel["bones"]:

            # create bone, by head, tail
            #
            eb = amt.edit_bones.new(bone["name"])
            h = bone["head"]
            t = bone["tail"]
            eb.head = Vector((h[0], -h[2], h[1]))
            eb.tail = Vector((t[0], -t[2], t[1]))

            # keep information for vertex groups
            #
            idx = bone["id"]
            self.bonelist[idx] = bone["name"]

            # now create bone orientation by restmatrix
            # change of bone directions (Blender: z up), do not wonder about the order in matrix
            # do not work on eb.matrix directly, copy location in the end (column 3)
            #
            mat = restmat[idx]
            nmat = Matrix()
            nmat.col[0] = [mat[0], -mat[8], mat[4], 0.0]
            nmat.col[1] = [mat[1], -mat[9], mat[5], 0.0]
            nmat.col[2] = [mat[2], -mat[10], mat[6], 0.0]
            nmat.col[3] = eb.matrix.col[3]
            eb.matrix = nmat

            if "parent" in bone:
                eb.parent = amt.edit_bones[bone["parent"]]


        # lock the bones in object mode
        #
        #bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='POSE')
        for bone in skel["bones"]:
            pb = rig.pose.bones[bone["name"]]
            if pb.parent:
                pb.lock_location = [True,True,True]

        for bone in rig.data.bones:
            loc, rot, scale = bone.matrix_local.decompose()
            rmat = rot.to_matrix()
            self.bonecorr[bone.name] = rmat

        bpy.ops.pose.armature_apply()
        bpy.ops.object.mode_set(mode='OBJECT')
        return rig

    def getAnimation (self, jdata, fp):
        """
        read posmatrix and create keyframes
        """
        skel =  jdata["skeleton"]
        bufnum  = skel["ANIMMAT"]
        nframes  = skel["nFrames"]
        length = jdata["bufferViews"][bufnum]["byteLength"] 
        print ("animation need to read " + str(length) + " bytes")
        buf = self.getData(fp, length)

        animdata = list(struct.iter_unpack('<fffffffff',  buf))
        print (nframes, len(animdata), len(animdata)/nframes)

        # in pose mode select all bones
        #
        bpy.ops.object.mode_set(mode='POSE')
        rig = self.skeleton
        self.activateObject(rig)
        for bone in self.armature.edit_bones:
            bone.select = True

        scn = self.context.scene
        scn.frame_start = 1
        scn.frame_end = nframes
        cnt = 0

        for frame in range(nframes):
            scn.frame_set(frame+1)
            for bone in skel["bones"]:
                name = bone["name"]
                pbone = rig.pose.bones.get(name)
                if pbone:
                    m = animdata[cnt]
                    pbone.location = (m[2], m[1], m[0])         # dislocation usually on root bone (because of bvh files)
                    pbone.scale    = (m[3], m[4], m[5])
                    euler = Euler((radians(m[6]), radians(m[7]), radians(m[8])), 'ZYX')
                    if name in self.bonecorr:
                        cmat = self.bonecorr[name]
                        mat = cmat.inverted() @  euler.to_matrix() @ cmat
                        rot = mat.to_euler()
                        pbone.rotation_mode = 'XYZ'
                        pbone.rotation_euler = (rot.x, rot.y, rot.z)

                # keyframe per property
                pbone.keyframe_insert(data_path="location", frame=scn.frame_current)
                pbone.keyframe_insert(data_path="scale", frame=scn.frame_current)
                pbone.keyframe_insert(data_path="rotation_euler", frame=scn.frame_current)
                cnt += 1
        bpy.ops.object.mode_set(mode='OBJECT')


    def createObjects(self, jdata, fp, dirname):
        #
        # start with skeleton if available, then just creates meshes
        # use an array optimized to read the buffer only once
        #
        self.bufferoffset = 0

        if "skeleton" in jdata:
            self.skeleton = self.getSkeleton(jdata, fp)
            if "ANIMMAT" in jdata["skeleton"]:
                self.getAnimation(jdata, fp)

        nodes = []
        n = jdata["nodes"][self.firstnode]
        nodes.append([self.firstname, n["mesh"]])
        lastmesh = n["mesh"]
        children = n["children"]
        for elem in children:
            n = jdata["nodes"][elem]
            name = n["name"]
            mesh = n["mesh"]
            if mesh > lastmesh:
                nodes.append([name, mesh])
                lastmesh = mesh
            else:
                # TODO insert
                pass

        for elem in nodes:
            mesh = self.getMesh(jdata, elem[0], elem[1], fp, dirname)
            if mesh is None:
                return False
            self.collection.objects.link(mesh)
            if self.skeleton:
                mesh.parent = self.skeleton
                mesh.lock_location = (True,True,True)
                mesh.lock_rotation = (True,True,True)
                mesh.lock_scale = (True,True,True)

        return True



    def loadMH2B(self, props):
        with open(props.filepath, 'rb') as f:
            # it starts with a 12 byte header
            #
            magic = f.read(4)
            if magic != b'MH2B':
                f.close()
                return(False, "bad header")
            vers = f.read(4)
            vers = struct.unpack('<I', vers)
            if vers[0] != 1:
                f.close()
                return (False, "bad version number, must be 1")

            filelen = f.read(4)
            filelen = struct.unpack('<I', filelen)[0]

            # then json must be loaded, size + header = 8 byte
            #
            jsonlen = f.read(4)
            jsonlen = struct.unpack('<I', jsonlen)[0]

            jsonmark = f.read(4)
            if jsonmark != b'JSON':
                f.close()
                return (False, "JSON chunk expected")
            jsontext = f.read(jsonlen).decode("ascii")
            jdata = json.loads(jsontext)
            # print(json.dumps(jdata, indent=3))

            lenbin = f.read(4)
            lenbin = struct.unpack('<I', lenbin)
            print ("Binlen = " + str(lenbin))

            magic = f.read(4)
            if magic != b'BIN\x00':
                f.close()
                return(False, "bad binary header")

            self.createCollection(jdata)
            if not self.createObjects(jdata, f, os.path.dirname(props.filepath)):
                f.close()
                return (False, "bad file structure")

        return (True, "okay")

class MH2B_OT_Load(bpy.types.Operator, ImportHelper):
    """Import MH2B file."""
    bl_idname = "mh2b.load"
    bl_label = "Load mh2b"
    bl_options = {'REGISTER'}
    filename_ext = ".mh2b"
    filter_glob: StringProperty(default="*.mh2b", options={'HIDDEN'})

    @classmethod
    def poll(self, context):
        return True

    def execute(self, context):
        mh2b = MH2B_OT_Loader(context)
        res, err = mh2b.loadMH2B(self.properties)
        if res is False:
            self.report({'ERROR'}, "File is not a valid mh2b file. " + err)
        else:
            self.report({'INFO'}, "File loaded.")
        return {'FINISHED'}

