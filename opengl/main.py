"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * OpenGLView
"""

from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QMatrix4x4, QVector3D

# try to keep only constants here
#
import re
import os
from OpenGL import GL as gl
from opengl.info import GLDebug
from opengl.shaders import ShaderRepository
from opengl.buffers import OpenGlBuffers, RenderedObject
from opengl.camera import Camera, Light
from opengl.skybox import OpenGLSkyBox
from opengl.prims import VisMarker
from opengl.scene import Scene

class OpenGLView(QOpenGLWidget):
    def __init__(self, glob):
        self.glob = glob
        self.env = glob.env
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.setMinimumSize(QSize(300, 560))
        self.setMaximumSize(QSize(2000, 2000))
        self.buffers = []
        self.objects = []
        self.objects_invisible = False
        self.xrayed = False
        self.wireframe = False
        self.camera  = None
        self.skybox = None
        self.framefeedback = None
        self.fps = 24
        self.timer1 = QTimer()
        self.timer2 = QTimer()
        self.timer1.timeout.connect(self.nextFrame)
        self.timer2.timeout.connect(self.yRotator)
        self.yangle = 0.0
        self.yrot = 2.0
        self.resetbuttons = None
        self.rotSkyBox = False
        self.blocked = False
        self.glfunc = None
        self.marker = None
        self.scene = None

    def setFPS(self, value, callback=None):
        self.fps = value
        if callback is not None:
            self.resetbuttons = callback
        self.timer1.stop()
        self.timer1.start(1000 / self.fps)

    def setYRotAngle(self, value, callback=None):
        self.yrot = value
        if callback is not None:
            self.resetbuttons = callback

    def setRotSkyBox(self, param):
        self.rotSkyBox = param

    def startTimer(self, framefeedback):
        self.framefeedback = framefeedback
        self.timer1.start(1000 / self.fps)

    def stopTimer(self):
        if self.framefeedback is not None:
            self.framefeedback()
        self.timer1.stop()
        self.blocked = False

    def nextFrame(self):
        if self.blocked:
            return
        self.blocked = True
        skeleton = self.glob.baseClass.pose_skeleton
        bvh = self.glob.baseClass.bvh
        # this slows animation down, better way?
        #if self.framefeedback is not None:
        #    self.framefeedback()
        skeleton.pose(bvh.joints, bvh.currentFrame)
        if bvh.currentFrame < (bvh.frameCount-1):
            bvh.currentFrame += 1
        else:
            bvh.currentFrame = 0
        self.Tweak()
        self.blocked = False

    def startRotate(self):
        self.timer2.start(1000 / 24)

    def stopRotate(self):
        self.timer2.stop()
        self.blocked = False

    def yRotator(self):
        if self.blocked:
            return
        self.blocked = True
        self.yangle = self.yangle + self.yrot
        if self.yangle >= 360.0:
            self.yangle = self.yangle - 360.0
        elif self.yangle < 0.0:
            self.yangle = self.yangle + 360.0
        self.setYRotation(float(self.yangle))
        self.Tweak()
        self.blocked = False

    def stopAnimation(self):
        if self.resetbuttons is not None:
            self.resetbuttons()
            self.resetbuttons = None
        self.stopTimer()
        self.blocked = True
        self.stopRotate()

    def toggleObjects(self, status):
        """
        makes objects invisible and switches skeleton to on
        """
        self.objects_invisible = status
        self.scene.setObjectsInvisible(status)
        if self.glob.baseClass and (self.glob.baseClass.skeleton or self.glob.baseClass.pose_skeleton):
            self.scene.togglePrims("skeleton", self.objects_invisible)
            self.Tweak()

    def toggleTranspAssets(self, status):
        self.xrayed = status
        if self.glob.baseClass is not None:
            self.Tweak()

    def toggleWireframe(self, status):
        self.wireframe = status
        if self.glob.baseClass is not None:
            self.Tweak()

    def toggleSkybox(self, status):
        self.light.skybox = status
        self.Tweak()

    def delMarker(self):
        if self.marker is not None:
            self.marker.delete()
            self.marker = None
            self.Tweak()

    def setMarker(self, coords):
        self.delMarker()
        shader = self.mh_shaders.getShader("fixcolor")
        self.marker = VisMarker(self.context(), shader, "marker", coords)
        self.marker.setVisible(True)
        self.Tweak()

    def modMarker(self, coords):
        if self.marker is not None:
            self.marker.newGeometry(coords)

    def compareBoundingBoxes(self, box1, box2):
        n = 0
        for i in range(0,3):
            if box2[i] < box1[i]:
                n += 1
            if box2[i+3] > box1[i+3]:
                n += 1
        return (n>3)

    def createObject(self, obj):
        """
        creates a rendered object and inserts it to a list according to zdepth and, if equal to bounding box
        """
        glbuffer = OpenGlBuffers()
        glbuffer.GetBuffers(obj.gl_coord, obj.gl_norm, obj.gl_uvcoord)
        self.buffers.append(glbuffer)

        boundingbox = obj.boundingBox()

        cnt = 0
        for elem in self.objects:
            if obj.z_depth < elem.z_depth:
                break
            if obj.z_depth == elem.z_depth:
                if (self.compareBoundingBoxes(elem.boundingbox, boundingbox)) is False:
                    break
            cnt += 1
        obj.openGL = RenderedObject(self, obj, boundingbox, glbuffer, pos=QVector3D(0, 0, 0))
        self.objects.insert(cnt, obj.openGL)

    def deleteObject(self,obj, delproxymat=False):
        if obj.openGL is not None:
            obj.openGL.delete()
            if obj.type != "proxy" or delproxymat is True:
                obj.material.freeTextures()
            self.objects.remove(obj.openGL)
            obj.openGL = None

    def setYRotation(self, angle=0.0):
        self.yangle = angle
        for obj in self.objects:
            obj.setYRotation(angle)
        self.scene.setYRotation(angle)

        if self.skybox is not None and self.rotSkyBox is True:
            self.skybox.setYRotation(angle)

    def newSkin(self, obj):
        self.objects[0].setMaterial(obj.material)

    def initializeGL(self):
        """
        automatically called by PySide6, terminates complete program if shader version < minversion (330) if not OSX
        """
        self.glob.openGLBlock = False
        self.glfunc = self.context().functions()

        if self.env.osindex != 2:
            deb = GLDebug()
            if deb.checkVersion() is False:
                self.env.logLine(1, "Shader version is not sufficient, minimum version is " + str(deb.minVersion() + ". Available languages are:") )
                lang = deb.getShadingLanguages()
                for l in lang:
                    if l != "":
                        self.env.logLine(1, l)
                exit(20)

        baseClass = self.glob.baseClass
        o_size = baseClass.baseMesh.getHeightInUnits() if baseClass is not None else 20

        # initialize shaders
        #
        self.mh_shaders = ShaderRepository(self.glob)
        self.mh_shaders.loadShaders(["phong", "fixcolor", "xray", "litsphere", "pbr", "toon","skybox"])

        self.light = Light(self.mh_shaders, self.glob)
        self.light.setShader()
        self.scene = Scene(self.glob, self, self.mh_shaders, self.Tweak)

        self.camera = Camera(self.glob, o_size, self.width(), self.height())
        self.camera.resizeViewPort(self.width(), self.height())


        if baseClass is not None:
            self.newMesh()
            self.scene.prepareSkeleton()
        self.scene.createPrims(self.light)

        # create environment
        #
        shader = self.mh_shaders.getShader("skybox")
        self.skybox = OpenGLSkyBox(self.glob, shader, self.glfunc)
        if self.skybox.create(self.light.skyboxname) is False:
            self.skybox = None


    def createThumbnail(self):
        image = self.grabFramebuffer()
        return (image.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def customView(self, direction):
        #self.setCameraCenter()  # new calculation of size
        self.camera.customView(direction)
        self.paintGL()
        self.update()

    def getCamera(self):
        return(self.camera)

    def modifyDistance(self, distance):
        self.camera.modifyDistance(distance)
        self.paintGL()
        self.update()

    def togglePerspective(self, mode):
        self.camera.togglePerspective(mode)
        self.paintGL()
        self.update()

    def arcBallCamStart(self, x, y):
        self.camera.setLastMousePosition(x, y)

    def arcBallCamera(self, x, y):
        self.camera.arcBallRotation(x, y)
        self.paintGL()
        self.update()

    def mousePanning(self, x, y):
        self.camera.mousePanning(x,y)
        self.paintGL()
        self.update()

    def keyPanning(self, mx, my):
        self.camera.panning(mx,my)
        self.paintGL()
        self.update()

    def modifyFov(self, value):
        self.camera.setFocalLength(value)
        self.paintGL()
        self.update()

    def paintGL(self):
        if self.glob.openGLBlock:
            # print ("open GL is blocked")
            return 

        c = self.light.glclearcolor
        self.glfunc.glClearColor(c.x(), c.y(), c.z(), c.w())
        self.glfunc.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
       
        proj_view_matrix = QMatrix4x4(self.camera.getProjViewMatrix().copyDataTo())
        campos = self.camera.getCameraPos()
        baseClass = self.glob.baseClass

        showskel = self.objects_invisible is True and self.scene.hasSkeleton()

        if baseClass is not None:
            poseskel =  self.glob.baseClass.pose_skeleton
            if poseskel is None:
                offset = QVector3D(0, 0, 0)
            else:
                offset = poseskel.offset if poseskel.use_offset else QVector3D(0, 0, 0)

            if baseClass.proxy is True:
                body = self.objects[1]
                asset_start = 2
            else:
                body = self.objects[0]
                asset_start = 1
            body.setPosition(offset)
            if self.wireframe:
                body.drawWireframe(proj_view_matrix, campos, self.scene.black, self.scene.white)
            else:
                body.draw(proj_view_matrix, campos, self.light, showskel)

            # either with xray or normal shader draw assets
            #
            for obj in self.objects[asset_start:]:
                obj.setPosition(offset)
                if self.wireframe:
                    obj.drawWireframe(proj_view_matrix, campos, self.scene.black, self.scene.white)
                else:
                    obj.draw(proj_view_matrix, campos, self.light, showskel | self.xrayed)

        if self.light.skybox and self.skybox and self.camera.cameraPers:
            self.skybox.draw(proj_view_matrix)

        # draw all other objects which are in scene
        #
        self.scene.draw(proj_view_matrix, campos, showskel)

        if self.marker is not None:
            self.marker.draw(proj_view_matrix)

    def Tweak(self):
        for glbuffer in self.buffers:
            glbuffer.Tweak()
        self.paintGL()
        self.update()

    def setCameraCenter(self):
        if self.glob.baseClass is not None:
            baseMesh = self.glob.baseClass.baseMesh
            self.camera.setCenter(baseMesh.getCenter(), baseMesh.getHeightInUnits())
        else:
            self.camera.setCenter((0.0, 0.0, 0.0), 20)

    def noGLObjects(self, leavebase=False, delproxymat=False):
        """
        should be called with block
        """
        for elem in self.glob.baseClass.attachedAssets:
            self.deleteObject(elem.obj, delproxymat=delproxymat)

        if leavebase is False:
            self.deleteObject(self.glob.baseClass.baseMesh)

        start = 1 if leavebase else 0
        for glbuffer in self.buffers[start:]:
            glbuffer.Delete()
        self.objects = self.objects[:start]
        self.buffers = self.buffers[:start]

    def addAssets(self):
        """
        add all assets to a basemesh
        """
        for elem in self.glob.baseClass.attachedAssets:
            self.createObject(elem.obj)

    def newMesh(self):
        """
        create of complete new mesh with assets
        """
        self.noGLObjects()
        self.scene.delSkeleton()

        if self.glob.baseClass is not None:
            self.createObject(self.glob.baseClass.baseMesh)
            self.addAssets()
            self.scene.prepareSkeleton(False)
            self.setCameraCenter()
            self.paintGL()
            self.update()

    def resizeGL(self, w, h):
        self.window_width = w
        self.window_height = h
        self.glfunc.glViewport(0, 0, w, h)
        self.camera.resizeViewPort(w, h)
        self.camera.calculateProjMatrix()

    def cleanUp(self):
        self.env.logLine(1, "cleanup openGL")
        self.scene.cleanUp()
        if self.skybox is not None:
            self.skybox.delete()
            self.skybox = None
