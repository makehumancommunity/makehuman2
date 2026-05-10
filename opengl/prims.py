"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * LineElements
    * CoordinateSystem
    * Grid
    * BoneList
    * SimpleObject
    * Cuboid
    * Diamond
    * DiamondSkeleton
    * VisLights
"""

from opengl.buffers import OpenGlBuffers, RenderedLines, RenderedObject, RenderedSimple

from PySide6.QtGui import QVector3D, QMatrix4x4
import numpy as np
import os

from obj3d.object3d import object3d

class LineElements:
    """
    create geometry for gdrawelements
    array of positions, array of colors or one color to be repeated
    """
    def __init__(self, context, shader, name, pos, cols):
        self.name = name
        self.lines = None
        self.glfunc =  context.functions()
        self.shader = shader
        self.width = 1.0
        self.visible = False
        self.gl_coord = np.asarray(pos, dtype=np.float32).flatten()
        if len(cols) > 0 and isinstance(cols[0], list):
            self.gl_cols = np.asarray(cols, dtype=np.float32).flatten()
        else:
            self.gl_cols = np.tile(np.asarray(cols, dtype=np.float32), len(pos))

        self.icoord = np.arange(len(pos), dtype=np.uint32)

        self.glbuffer = OpenGlBuffers()
        self.glbuffer.VertexBuffer(self.gl_coord)
        self.glbuffer.NormalBuffer(self.gl_cols)   # used for color

    def isVisible(self):
        return self.visible

    def setVisible(self, status):
        self.visible = status

    def create(self, width=1.0, infront=False):
        self.width = width
        self.lines = RenderedLines(self.glfunc, self.shader, self.icoord, self.name, self.glbuffer, pos=QVector3D(0, 0, 0), infront=infront)

    def newGeometry(self, pos):
        self.gl_coord[:] = np.asarray(pos, dtype=np.float32).flatten()
        self.glbuffer.Tweak()

    def draw(self, proj_view_matrix):
        if self.lines and self.visible:
            self.glfunc.glLineWidth(self.width)
            self.lines.draw(proj_view_matrix)

    def setYRotation(self, rot):
        self.lines.setYRotation(rot)

    def setPosition(self, pos):
        self.lines.setPosition(pos)

    def delete(self):
        if self.lines:
            self.lines.delete()

class CoordinateSystem(LineElements):
    def __init__(self, context, shader, name, size, width=2.0):
        super().__init__(context, shader, name,
                [[ -size, 0.0, 0.0],  [ size, 0.0, 0.0],  [ 0.0, -size, 0.0], [ 0.0, size, 0.0], [ 0.0, 0.0, -size], [ 0.0, 0.0, size]],
                [[ 1.0, 0.0, 0.0],  [ 1.0, 0.0, 0.0],  [ 0.0, 1.0, 0.0], [ 0.0, 1.0, 0.0], [ 0.0, 0.0, 1.0], [ 0.0, 0.0, 1.0]])
        self.create(width)

class Grid(LineElements):
    def __init__(self, context, shader, name, size, ground, direction):
        lines = []
        cols = []
        self.border = int(size)
        lines = self.setGrid(ground, direction)
        # add colors one time
        #
        if direction == "xy":
            for i in range(-self.border, self.border+1):
                # xy-plane
                cols.extend ([[0.0, 0.0, 0.4], [0.0, 0.0, 0.4], [0.0, 0.0, 0.4], [0.0, 0.0, 0.4]])
        elif direction == "yz":
            for i in range(-self.border, self.border+1):
                # yz-plane
                cols.extend ([[0.4, 0.0, 0.0], [0.4, 0.0, 0.0], [0.4, 0.0, 0.0], [0.4, 0.0, 0.0]])
        else:
            for i in range(-self.border, self.border+1):
                # xz-plane
                cols.extend ([[0.0, 0.4, 0.0], [0.0, 0.4, 0.0], [0.0, 0.4, 0.0], [0.0, 0.4, 0.0]])

        super().__init__(context, shader, name, lines, cols)
        self.create()

    def setGrid(self, ground, direction):
        size = float(self.border)
        lines = []
        if direction == "xy":
            for i in range(-self.border, self.border+1):
                # xy-plane
                lines.extend ([[ -size, float(i), 0.0],  [ size, float(i), 0.0], [ float(i), -size, 0.0],  [ float(i), size, 0.0]])
        elif direction == "yz":
            for i in range(-self.border, self.border+1):
                # yz-plane
                lines.extend ([[ 0.0, float(i), -size],  [ 0.0, float(i), size], [0.0, -size, float(i)],  [ 0.0, size, float(i)]])

        else:
            for i in range(-self.border, self.border+1):
                # xz-plane
                lines.extend ([[ float(i), ground, -size ],  [ float(i), ground, size], [-size, ground, float(i)],  [size, ground, float(i)]])
        return (lines)

    def newGeometry(self,ground, direction):
        self.setGrid(ground, direction)
        super().newGeometry(self.setGrid(ground, direction))

class BoneList(LineElements):
    def __init__(self, context, shader, name, skeleton, col):
        self.skeleton = skeleton
        lines = []
        for bone in skeleton.bones.values():
            lines.extend ([bone.headPos, bone.tailPos])
        super().__init__(context, shader, name, lines, col)
        self.create(3.0, True)

    def newGeometry(self,posed=True):
        skeleton = self.skeleton
        lines = []
        if posed:
            for bone in skeleton.bones.values():
                lines.extend ([bone.poseheadPos, bone.posetailPos])
        else:
            for bone in skeleton.bones.values():
                lines.extend ([bone.headPos, bone.tailPos])
        super().newGeometry(lines)

class VisMarker(LineElements):
    def __init__(self, context, shader, name, coords, width=2.0):
        super().__init__(context, shader, name, coords, [1.0, 1.0, 1.0])
        self.create(width, True)


class SimpleObject():
    """
    create geometry for gdrawelements
    array of positions, array of faces, array of normals
    """
    def __init__(self, context, shaders, name, coords, norm, indices, uv=None, infront=False, transparent=False):
        self.name = name
        self.simple = None
        self.glfunc =  context.functions()
        self.icoord = indices
        self.shaders = shaders
        if uv is None:
            self.uv = np.zeros(len(self.icoord) *2, dtype=np.float32)
        else:
            self.uv = uv
        self.infront = infront
        self.transparent = transparent
        self.glbuffer = OpenGlBuffers()
        self.glbuffer.VertexBuffer(coords)
        self.glbuffer.NormalBuffer(norm)
        self.glbuffer.TexCoordBuffer(self.uv)

    def create(self):
        self.simple = RenderedSimple(self.glfunc, self.shaders, self.icoord, self.name, self.glbuffer, infront=self.infront, transparent=self.transparent)

    def draw(self, proj_view_matrix, texture):
        self.simple.draw(proj_view_matrix, texture)

    def Tweak(self):
        self.glbuffer.Tweak()

    def setScale(self, s):
        self.simple.setScale(s)

    def setPosition(self, pos):
        self.simple.setPosition(pos)

    def setRotation(self, rot):
        self.simple.setRotation(rot)

    def flatShade(self, icoord, coord):
        flatcoord = np.zeros((len(icoord), 3), dtype=np.float32)
        j = 0
        for i in icoord:
            flatcoord[j] = coord[i]
            icoord[j] = j
            j+=1
        return flatcoord

    def calcNorm(self, icoord, coord):
        norm = np.zeros((len(icoord), 3), dtype=np.float32)
        m = len(icoord)
        t = icoord.reshape(m//3, 3)
        j = 0
        for i in t:
            fn = np.cross(coord[i][0]-coord[i][1], coord[i][2]-coord[i][1])
            norm[j] = norm[j+1] = norm[j+2] = fn
            j+=3
        return norm.flatten()

    def delete(self):
        if self.simple:
            self.simple.delete()

class Cuboid(SimpleObject):
    def __init__(self, context, shaders, name, size, position, texture):
        self.texture = texture
        self.context = context
        self.shaders = shaders
        self.name = name
        self.size = size.copy()
        self.position = position
        self.icoord = None
        self.visible = False
        self.created = False

    def calcPositions(self):
        (x, y, z) = self.size
        (ox, oy, oz) = self.position
        self.coord = np.asarray(
            [[-x+ox, -y+oy, -z+oz], [x+ox, -y+oy, -z+oz], [x+ox, y+oy, -z+oz], [-x+ox, y+oy, -z+oz],
            [-x+ox, -y+oy, z+oz], [x+ox, -y+oy, z+oz], [x+ox, y+oy, z+oz], [-x+ox, y+oy, z+oz]],
            dtype=np.float32)

        # we need to keep the original values
        #
        self.icoord = self.scoord.copy()
        self.coord = self.flatShade(self.icoord, self.coord)
        self.norm = self.calcNorm(self.icoord, self.coord)
        self.coord = self.coord.flatten()

    def build(self):
        self.scoord = np.asarray(
            [0, 2, 1,  0, 3, 2,  4, 6, 5,  4, 7, 6,
             4, 0, 1,  4, 1, 5,  7, 3, 2,  7, 2, 6,
             3, 0, 4,  3, 4, 7,  6, 2, 1,  6, 1, 5],
            dtype=np.uint32)
        self.uv = np.asarray(
            [0, 0, 0.1, 1, 0, 1, 0, 0, 0.1, 0, 0.1, 1,
             0, 0, 0.1, 1, 0, 1, 0, 0, 0.1, 0, 0.1, 1,
             0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1,
             0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1,
             1, 0.1, 1, 0, 0, 0, 1, 0.1, 0, 0, 0, 0.1,
             0.1, 1, 0.1, 0, 0, 0, 0.1, 1, 0, 0, 0, 1],
            dtype=np.float32)
        self.calcPositions()
        super().__init__(self.context, self.shaders, self.name, self.coord, self.norm, self.icoord, uv=self.uv, infront=False, transparent=True)
        self.create()
        self.created = True

    def isVisible(self):
        return self.visible

    def setVisible(self, status):
        self.visible = status
        if status is False:
            self.delete()

    def setTexture(self, texture):
        self.texture = texture

    def newGeometry(self, oy):
        self.position[1] = oy - self.size[1]
        if self.created:
            self.delete()
        self.build()

    def draw(self, proj_view_matrix):
        if self.visible:
            self.simple.draw(proj_view_matrix, self.texture)

    def newSize(self, size):
        oheight = self.position[1] + self.size[1]
        if self.created:
            self.delete()
        self.size[:] = size[:]
        self.position[1] = oheight - self.size[1]
        self.build()

class Diamond(SimpleObject):
    def __init__(self, context, shaders, name):
        w = 0.5
        self.coord = np.asarray(
            [[-w, 1.0, 0.0],  [0.0, 1.0, w],  [0.0, 1.0, -w],
             [w, 1.0, 0.0],  [0.0, 4.0, 0.0],  [0.0, 0.0, 0.0]], 
            dtype=np.float32)
        self.icoord = np.asarray(
                [2, 5, 3,  2, 3, 4,  0, 2, 4,  0, 5, 2,
                 3, 1, 4,  3, 5, 1,  1, 0, 4,  1, 5, 0],
            dtype=np.uint32)
        self.coord = self.flatShade(self.icoord, self.coord)
        self.norm = self.calcNorm(self.icoord, self.coord)
        self.coord = self.coord.flatten()
        super().__init__(context, shaders, name, self.coord, self.norm, self.icoord, infront=True)
        self.create()

class DiamondSkeleton(Diamond):
    def __init__(self, context, shaders, name, skeleton, col):
        self.skeleton = skeleton
        self.texture = col
        self.visible = False
        self.y_rotation = 0.0
        super().__init__(context, shaders, name)

    def isVisible(self):
        return self.visible

    def setVisible(self, status):
        self.visible = status

    def setYRotation(self, angle):
        # must be done here
        self.y_rotation = angle

    def newGeometry(self,posed=True):
        # dummy, because geometry consists of multiple parts
        pass

    def draw(self, proj_view_matrix, posed):
        if self.visible is False:
            return
        skeleton = self.skeleton
        view_matrix = QMatrix4x4(proj_view_matrix.copyDataTo())
        if self.y_rotation != 0.0:
            view_matrix.rotate(self.y_rotation, 0.0, 1.0, 0.0)
        if posed:
            for bone in skeleton.bones.values():
                l = bone.posetailPos - bone.poseheadPos
                self.setScale(np.sqrt(l.dot(l)) / 4.0)
                self.setRotation(bone.matPoseGlobal)
                super().draw(view_matrix, self.texture)
        else:
            for bone in skeleton.bones.values():
                l = bone.tailPos - bone.headPos
                self.setScale(np.sqrt(l.dot(l)) / 4.0)
                self.setRotation(bone.matRestGlobal)
                super().draw(view_matrix, self.texture)

    
class VisLights():
    """
    should create symbolic lamps
    """
    def __init__(self, parent, light):
        self.parent = parent
        self.glob =  parent.glob
        self.light = light
        self.lampobj =  object3d(self.glob, None, "system")
        self.obj = []

    def setup(self):
        lampfile = os.path.join(self.glob.env.path_sysdata, "shaders", "meshes", "lampsymbol.obj")
        (success, text) =self.lampobj.load(lampfile)

        if not success:
            self.glob.env.logLine(1, text)
            return False

        glbuffer = OpenGlBuffers()
        glbuffer.GetBuffers(self.lampobj.gl_coord, self.lampobj.gl_norm, self.lampobj.gl_uvcoord)
        boundingbox = self.lampobj.boundingBox()

        for light in self.light.lights:
            l = RenderedObject(self.parent, self.lampobj, boundingbox, glbuffer, pos=light["pos"])
            self.obj.append(l)
        return True

    def draw(self, proj_view_matrix, campos, texture):
        for i, light in enumerate(self.light.lights):
            self.obj[i].setPosition(light["pos"])
            self.obj[i].setTexture(texture)
            self.obj[i].draw(proj_view_matrix, campos, self.light, False)


