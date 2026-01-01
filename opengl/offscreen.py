"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * OffScreenRender
"""

from PySide6.QtGui import QSurfaceFormat, QOffscreenSurface, QOpenGLContext, QImage
from PySide6.QtOpenGL import QOpenGLFramebufferObjectFormat, QOpenGLFramebufferObject

from OpenGL import GL as gl
import numpy as np

class OffScreenRender:
    def __init__(self, glob, view, transparent=False):
        self.glob = glob
        self.view = view
        self.transparent = transparent
        self.framebuffer = None
        self.alphamask = None
        self.width = 0
        self.height = 0
        self.oldheight = self.view.window_height
        self.oldwidth = self.view.window_width
        self.context = None

    def renderObject(self, obj, proj_view_matrix, campos):
        obj.draw(proj_view_matrix, campos, self.view.light)

    def getBuffer(self, width, height):
        self.width = width
        self.height = height
        self.oldheight = self.view.window_height
        self.oldwidth = self.view.window_width

        self.bufformat = QOpenGLFramebufferObjectFormat()

        # use same format for buffer
        #
        sformat = QSurfaceFormat()
        sformat.setDefaultFormat(self.glob.app.getFormat())

        if self.glob.env.noalphacover is False:
            self.bufformat.setSamples(4)
        self.bufformat.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)

        self.context = QOpenGLContext()
        self.context.setFormat(sformat)
        self.context.setShareContext(self.view.context())

        self.surface = QOffscreenSurface()
        self.surface.setFormat(self.view.format())
        self.surface.create()

        if not self.context.create():
            self.env.logLine(1, "OffScreenRender: Failed to create OpenGL context")
            return
        self.context.makeCurrent(self.surface)
        ogl = self.context.functions()

        self.framebuffer = QOpenGLFramebufferObject(width, height, self.bufformat)
        self.framebuffer.bind()

        self.view.camera.resizeViewPort(width, height)
        proj_view_matrix = self.view.camera.calculateProjMatrix()
        ogl.glViewport(0, 0, width, height)

        c = self.view.light.glclearcolor
        if self.transparent:
            ogl.glClearColor(0.0, 0.0, 0.0, 0.0)
        else:
            ogl.glClearColor(c.x(), c.y(), c.z(), 1.0)
        ogl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        campos = self.view.camera.getCameraPos()
        baseClass = self.glob.baseClass
        start = 1 if baseClass.proxy is True else 0

        self.glob.openGLBlock = True

        # the character is never transparent, we need to keep the alpha
        #
        self.renderObject(self.view.objects[start], proj_view_matrix, campos)

        if self.transparent:
            alphamask =  self.framebuffer.toImage()
            ptr = alphamask.constBits()
            mlen = self.height* self.width
            self.alphamask = np.array(ptr).reshape(mlen*4)[3::4]  # Copies only the alpha value
            self.framebuffer.bind()                               # needs to be rebound
        start +=1

        for obj in self.view.objects[start:]:
            self.renderObject(obj, proj_view_matrix, campos)

    def bufferToImage(self):
        if self.glob.env.noalphacover is False:
            img =  self.framebuffer.toImage().copy()

            # to avoid artifacts, we need to copy the image once
            #
            img = QImage(img.constBits(), img.width(), img.height(), QImage.Format_ARGB32).copy()
        else:
            img =  self.framebuffer.toImage().copy()
        self.glob.openGLBlock = False

        # now add alpha of body again, otherwise the character is transparent also, when wearing
        # transparent clothes

        if self.alphamask is not None:
            ptr = img.bits()
            mlen = self.height* self.width
            alphadest = np.array(ptr).reshape(mlen*4)[3::4]  #  Copies only the alpha value
            for x in range(0, self.height* self.width):
                if alphadest[x] < self.alphamask[x]:
                    ptr[x*4+3] = self.alphamask[x]

        imgmode = QImage.Format_RGBA8888 if self.transparent else QImage.Format_RGB888
        img =  img.convertToFormat(imgmode)
        self.context.doneCurrent()
        self.framebuffer.bindDefault()
        return img

    def releaseBuffer(self):
        self.view.resizeGL(self.oldwidth, self.oldheight)
        self.framebuffer.release()
        self.surface.destroy()

