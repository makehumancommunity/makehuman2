"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * OpenGlBuffers
    * RenderedObject
    * RenderedLines
    * RenderedSimple
"""
import time
import numpy as np
from PySide6.QtGui import QVector3D, QMatrix4x4

from PySide6.QtOpenGL import (QOpenGLBuffer, QOpenGLShader,
                              QOpenGLShaderProgram, QOpenGLTexture)
# from opengl.info import openGLError

# Constants from OpenGL GL_TRIANGLES, GL_FLOAT
# 

from OpenGL import GL as gl

class OpenGlBuffers():
    def __init__(self):
        self.vert_pos_buffer = None
        self.normal_buffer = None
        self.tex_coord_buffer = None
        self.memory_pos = None
        self.len_memory = 0

    def VertexBuffer(self, pos):
        vbuffer = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        vbuffer.create()
        vbuffer.bind()
        vbuffer.setUsagePattern(QOpenGLBuffer.DynamicDraw)
        self.len_memory = len(pos) * 4
        self.memory_pos = pos
        vbuffer.allocate(pos, self.len_memory)
        self.vert_pos_buffer = vbuffer

    def NormalBuffer(self, pos):
        vbuffer = QOpenGLBuffer()
        vbuffer.create()
        vbuffer.bind()
        vbuffer.allocate(pos, len(pos) * 4)
        self.normal_buffer = vbuffer

    def TexCoordBuffer(self, pos):
        vbuffer = QOpenGLBuffer()
        vbuffer.create()
        vbuffer.bind()
        vbuffer.allocate(pos, len(pos) * 4)
        self.tex_coord_buffer = vbuffer

    def GetBuffers(self, pos, norm, tpos):
        self.VertexBuffer(pos)
        self.NormalBuffer(norm)
        self.TexCoordBuffer(tpos)

    def BindBuffersToShader(self, shader):
        """
        VAO, bind the position-buffer, normal-buffer and texture-coordinates to attribute 0, 1, 2
        must be done on each render cycle
        """
        self.vert_pos_buffer.bind()
        shader.setAttributeBuffer(0, gl.GL_FLOAT, 0, 3)     # OpenGL = glVertexAttribPointer
        shader.enableAttributeArray(0)                      # OpenGL = glEnableVertexAttribArray

        self.normal_buffer.bind()
        shader.setAttributeBuffer(1, gl.GL_FLOAT, 0, 3)
        shader.enableAttributeArray(1)
        
        # allow none textured objects (e.g. lines, they use normal buffer as color buffer and no texture)
        #
        if  self.tex_coord_buffer is not None:
            self.tex_coord_buffer.bind()
            shader.setAttributeBuffer(2, gl.GL_FLOAT, 0, 2)
            shader.enableAttributeArray(2)

    def Tweak(self):
        self.vert_pos_buffer.bind()
        self.vert_pos_buffer.write(0,self.memory_pos, self.len_memory )

    def Delete(self):
        if self.vert_pos_buffer is not None:
            self.vert_pos_buffer.destroy()
        if self.normal_buffer is not None:
            self.normal_buffer.destroy()
        if self.tex_coord_buffer is not None:
            self.tex_coord_buffer.destroy()

class RenderedObject:
    """
    class to render an object like body or clothes
    also used to draw the lamps

    :param parent: parent object of type class  OpenGLView (from QOpenGLWidget)
    :param obj: the object to render
    :param boundingbox: boundingbox to be assigned
    :param glbuffers: OpenGlBuffers for this object
    :param pos: position of the object as QVector3D
    """
    def __init__(self, parent, obj, boundingbox, glbuffers, pos):

        self.parent = parent
        self.glob = parent.glob
        self.env = self.glob.env
        self.object = obj
        self.boundingbox = boundingbox
        self.glbuffers = glbuffers
        self.position = pos

        self.functions = parent.context().functions()
        self.shaders = parent.mh_shaders

        self.texture = None
        self.litsphere = None
        self.aomap = None
        self.nomap = None
        self.mrmap = None
        self.emmap = None
        self.mefac = 0.0

        self.z_depth = obj.z_depth  # used for comparision
        self.name = obj.filename
        self.getindex = obj.getOpenGLIndex

        self.scale = QVector3D(1, 1, 1)
        self.y_rotation = 0.0
        self.mvp_matrix = QMatrix4x4()
        self.model_matrix = QMatrix4x4()
        self.normal_matrix = QMatrix4x4()

        self.setMaterial(obj.material)


    def __str__(self):
        return("GL Object " + str(self.name))

    def setFunctions(self, functions):
        self.functions = functions

    def delete(self):
        self.glbuffers.Delete()

    def setMaterial(self, material, modify=True):
        """
        set shader and creates textures from material according to shader
        all shaders use a diffuse texture
        """
        self.material = material
        self.texture = self.material.loadDiffuse(modify, self.object)

        if material.shader == "litsphere":
            self.shader = self.shaders.getShader("litsphere")
            self.litsphere = self.material.loadLitSphere(modify, self.object)
        elif material.shader == "pbr":
            self.shader = self.shaders.getShader("pbr")
            self.aomap = self.material.loadAOMap(self.parent.scene.white, modify, self.object)
            self.mrmap = self.material.loadMRMap(self.parent.scene.white, modify, self.object)
            self.emmap = self.material.loadEMMap(self.parent.scene.black, modify, self.object)
            self.nomap = self.material.loadNOMap(self.parent.scene.normal, modify, self.object)
            self.mefac = material.metallicFactor if hasattr(self, 'metallicRoughnessTexture') else 1.0 - material.metallicFactor
        elif material.shader == "toon":
            self.shader = self.shaders.getShader("toon")
        else:
            self.shader = self.shaders.getShader("phong")
            self.aomap = self.material.loadAOMap(self.parent.scene.white, modify, self.object)

    def setTexture(self, texture):
        # only used for colors
        self.texture = texture
    
    def setPosition(self, pos):
        self.position = pos

    def setYRotation(self, rot):
        self.y_rotation = rot

    def geomToShader(self, shader, proj_view_matrix, campos):
        """
        create geometry
        """
        self.mvp_matrix_location = shader.uniforms["uMvpMatrix" ]
        self.model_matrix_location = shader.uniforms["uModelMatrix"]
        self.normal_matrix_location = shader.uniforms["uNormalMatrix"]
        self.viewpos_location = shader.uniforms["viewPos"]

        shader.bind()

        self.glbuffers.BindBuffersToShader(shader)  # VAO etc.

        self.model_matrix.setToIdentity()
        self.model_matrix.translate(self.position)
        if self.y_rotation != 0.0:
            self.model_matrix.rotate(self.y_rotation, 0.0, 1.0, 0.0)
        self.model_matrix.scale(self.scale)
        self.mvp_matrix = proj_view_matrix * self.model_matrix

        self.normal_matrix = self.model_matrix.inverted()
        self.normal_matrix = self.normal_matrix[0].transposed()

        # now set uMvpMatrix, uModelMatrix, uNormalMatrix

        shader.setUniformValue(self.mvp_matrix_location, self.mvp_matrix)
        if self.model_matrix_location != -1:
            shader.setUniformValue(self.model_matrix_location, self.model_matrix)
        if self.normal_matrix_location != -1:
            shader.setUniformValue(self.normal_matrix_location, self.normal_matrix)
        if self.viewpos_location != -1:
            shader.setUniformValue(self.viewpos_location, campos)

    def glReset(self):
        functions = self.functions
        functions.glDisable(gl.GL_CULL_FACE)
        functions.glDisable(gl.GL_SAMPLE_ALPHA_TO_COVERAGE)
        functions.glDisable(gl.GL_BLEND)
        functions.glDisable(gl.GL_MULTISAMPLE)
        functions.glDisable(gl.GL_DEPTH_TEST)
        functions.glActiveTexture(gl.GL_TEXTURE0)

    def drawObject(self):
        indices = self.getindex()
        self.functions.glDrawElements(gl.GL_TRIANGLES, len(indices), gl.GL_UNSIGNED_INT, indices)

    def draw(self, proj_view_matrix, campos, light, xrayed = False):
        """
        :param QMatrix4x4 proj_view_matrix: view-matrix
        :param QVector3D campos: camera position
        :param camera.Light light: pointer to light to reference skybox and other parameters
        :param bool xrayed: if xrayed mode is used
        """
        functions = self.functions
        functions.glEnable(gl.GL_DEPTH_TEST)

        # do xrayed first, since it is a special form
        #
        if xrayed:
            shader = self.shaders.getShader("xray")
            self.geomToShader(shader, proj_view_matrix, campos)
            functions.glEnable(gl.GL_BLEND)
            functions.glEnable(gl.GL_CULL_FACE)
            functions.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            self.drawObject()
            self.glReset()
            return

        shader = self.shader
        self.geomToShader(shader, proj_view_matrix, campos)

        if self.material.roughnessFactor is not None:
            lightWeight = QVector3D(1.0 - self.material.roughnessFactor, light.lightWeight.y(), 0)
        else:
            lightWeight = QVector3D(0.5, light.lightWeight.y(), 0)
        shader.setUniformValue("lightWeight", lightWeight)

        # alphaCoverage demands samples buffers, so if these are not given
        # do not use alphaToCoverage, use BLEND instead

        alphaCover = self.material.alphaToCoverage and not self.env.noalphacover

        if self.material.transparent:
            if alphaCover:
                functions.glEnable(gl.GL_MULTISAMPLE)
                functions.glEnable(gl.GL_SAMPLE_ALPHA_TO_COVERAGE)
                functions.glDisable(gl.GL_BLEND)
            else:
                functions.glEnable(gl.GL_BLEND)

            functions.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        else:
            functions.glBlendFunc(gl.GL_ONE, gl.GL_ZERO)

        if self.material.backfaceCull:
            functions.glEnable(gl.GL_CULL_FACE)
        else:
            functions.glDisable(gl.GL_CULL_FACE)

        functions.glUniform1i(shader.uniforms['Texture'], 0)
        functions.glActiveTexture(gl.GL_TEXTURE0)
        self.texture.bind()

        if self.material.shader == "litsphere":
            functions.glUniform1f(shader.uniforms['AdditiveShading'], self.material.sp_AdditiveShading)

            functions.glUniform1i(shader.uniforms['litsphereTexture'], 1)
            functions.glActiveTexture(gl.GL_TEXTURE1)
            self.litsphere.bind()

        elif self.material.shader == "phong":
            functions.glUniform1f(shader.uniforms['AOMult'], self.material.aomapIntensity)

            functions.glUniform1i(shader.uniforms['AOTexture'], 1)
            functions.glActiveTexture(gl.GL_TEXTURE1)
            self.aomap.bind()

        elif self.material.shader == "pbr":
            functions.glUniform1f(shader.uniforms['AOMult'], self.material.aomapIntensity)

            functions.glUniform1i(shader.uniforms['AOTexture'], 1)
            functions.glActiveTexture(gl.GL_TEXTURE1)
            self.aomap.bind()

            functions.glUniform1f(shader.uniforms['MeMult'], self.mefac)
            functions.glUniform1f(shader.uniforms['RoMult'], self.material.roughnessFactor)

            functions.glUniform1i(shader.uniforms['MRTexture'], 2)
            functions.glActiveTexture(gl.GL_TEXTURE2)
            self.mrmap.bind()

            functions.glUniform1f(shader.uniforms['EmMult'], self.material.emissiveFactor)
            functions.glUniform1i(shader.uniforms['EMTexture'], 3)
            functions.glActiveTexture(gl.GL_TEXTURE3)
            self.emmap.bind()

            if self.material.tex_nomap is None:
                functions.glUniform1f(shader.uniforms['NoMult'], 0.0)
            else:
                functions.glUniform1f(shader.uniforms['NoMult'], self.material.normalmapIntensity)
            functions.glUniform1i(shader.uniforms['NOTexture'], 4)
            functions.glActiveTexture(gl.GL_TEXTURE4)
            self.nomap.bind()

            if light.skybox is True and self.parent.skybox is not None:
                functions.glUniform1i(shader.uniforms['useSky'], True)
                functions.glUniform1i(shader.uniforms['skybox'], 5)
                functions.glActiveTexture(gl.GL_TEXTURE5)
                self.parent.skybox.getTexture().bind()
            else:
                functions.glUniform1i(shader.uniforms['useSky'], False)

        self.drawObject()
        self.glReset()

    def drawWireframe(self, proj_view_matrix, campos, black, white):
        """
        creates a wireframe model

        :param QMatrix4x4 proj_view_matrix: view-matrix
        :param QVector3D campos: camera position
        :param black: black 1x1 pixel texture
        :param white: white 1x1 pixel texture
        """
        shader = self.shaders.getShader("phong")
        self.geomToShader(shader, proj_view_matrix, campos)
        functions = self.functions

        oldtexture = self.texture
        self.setTexture(black)
        t1 = shader.uniforms['Texture']
        functions.glUniform1i(t1, 0)
        functions.glActiveTexture(gl.GL_TEXTURE0)
        self.texture.bind()

        functions.glUniform1f(shader.uniforms['AOMult'], 1.0)

        indices = self.getindex()

        functions.glLineWidth(1)
        functions.glEnable(gl.GL_DEPTH_TEST)
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
        functions.glDrawElements(gl.GL_TRIANGLES, len(indices), gl.GL_UNSIGNED_INT, indices)

        functions.glEnable(gl.GL_CULL_FACE)
        functions.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        functions.glPolygonOffset(1.0, 1.0)

        self.setTexture(white)
        functions.glActiveTexture(gl.GL_TEXTURE0)
        self.texture.bind()

        functions.glUniform1i(shader.uniforms['AOTexture'], 1)
        functions.glActiveTexture(gl.GL_TEXTURE1)
        self.texture.bind()

        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)

        functions.glDrawElements(gl.GL_TRIANGLES, len(indices), gl.GL_UNSIGNED_INT, indices)

        functions.glDisable(gl.GL_POLYGON_OFFSET_FILL)
        functions.glDisable(gl.GL_CULL_FACE)

        self.setTexture(oldtexture)
        functions.glDisable(gl.GL_DEPTH_TEST)
        functions.glActiveTexture(gl.GL_TEXTURE0)


class RenderedLines:
    def __init__(self, functions, shader, indices, name, glbuffers, pos, infront=False):
        self.functions = functions
        self.shader = shader
        self.name = name
        self.infront = infront
        self.position = QVector3D(0, 0, 0)
        self.scale = QVector3D(1, 1, 1)
        self.y_rotation = 0.0
        self.mvp_matrix = QMatrix4x4()
        self.model_matrix = QMatrix4x4()
        self.normal_matrix = QMatrix4x4()
        self.glbuffers = glbuffers
        self.indices = indices

        self.mvp_matrix_location = shader.uniforms["uMvpMatrix" ]
        self.model_matrix_location = shader.uniforms["uModelMatrix"]

        self.position = pos

    def __str__(self):
        return("GL Lines " + str(self.name))

    def delete(self):
        self.glbuffers.Delete()

    def setYRotation(self, rot):
        self.y_rotation = rot

    def draw(self, proj_view_matrix):
        """
        :param shaderprog: QOpenGLShaderProgram
        """
        self.shader.bind()

        self.glbuffers.BindBuffersToShader(self.shader)  # VAO etc.

        self.model_matrix.setToIdentity()
        self.model_matrix.translate(self.position)
        self.model_matrix.scale(self.scale)
        if self.y_rotation != 0.0:
            self.model_matrix.rotate(self.y_rotation, 0.0, 1.0, 0.0)
        self.mvp_matrix = proj_view_matrix * self.model_matrix

        # now set uMvpMatrix, uModelMatrix

        self.functions.glEnable(gl.GL_BLEND)
        if self.infront:
            self.functions.glDisable(gl.GL_DEPTH_TEST)
        else:
            self.functions.glEnable(gl.GL_DEPTH_TEST)
        self.shader.setUniformValue(self.mvp_matrix_location, self.mvp_matrix)
        self.shader.setUniformValue(self.model_matrix_location, self.model_matrix)

        indices = self.indices
        self.functions.glDrawElements(gl.GL_LINES, len(indices), gl.GL_UNSIGNED_INT, indices)
        self.functions.glDisable(gl.GL_BLEND)
        self.functions.glDisable(gl.GL_DEPTH_TEST)

class RenderedSimple:
    """
    class to render a simple object like floor or a bone

    :param functions: openGL funtions pointer
    :param shaders: openGL shader array
    :param indices: the indices for the opengl object used in glDrawElements
    :param str name: name of the object
    :param glbuffers: OpenGlBuffers for this object
    :param bool infront: if the object should be drawn in front of all others
    :param bool transparent: if transparency of object is allowed
    """
    def __init__(self, functions, shaders, indices, name, glbuffers, infront=False, transparent=False):
        self.functions = functions
        self.name = name
        self.scale = QVector3D(1, 1, 1)
        self.mvp_matrix = QMatrix4x4()
        self.model_matrix = QMatrix4x4()
        self.normal_matrix = QMatrix4x4()
        self.rotation = QMatrix4x4()
        self.glbuffers = glbuffers
        self.indices = indices
        self.infront = infront
        self.transparent = transparent

        self.shader = shaders.getShader("phong")
        self.mvp_matrix_location = self.shader.uniforms["uMvpMatrix" ]
        self.model_matrix_location = self.shader.uniforms["uModelMatrix"]
        self.normal_matrix_location = self.shader.uniforms["uNormalMatrix"]

    def __str__(self):
        return("GL Simple " + str(self.name))

    def setScale(self, s):
        self.scale = QVector3D(s, s, s)

    def setRotation(self, rot):
        self.rotation = QMatrix4x4(rot.flatten().tolist())

    def delete(self):
        self.glbuffers.Delete()

    def draw(self, proj_view_matrix, texture):
        shader = self.shader
        shader.bind()

        self.glbuffers.BindBuffersToShader(self.shader)  # VAO etc.

        self.model_matrix.setToIdentity()
        self.model_matrix = self.model_matrix * self.rotation
        self.model_matrix.scale(self.scale)
        self.mvp_matrix = proj_view_matrix * self.model_matrix

        self.normal_matrix = self.model_matrix.inverted()
        self.normal_matrix = self.normal_matrix[0].transposed()

        # now set uMvpMatrix, uModelMatrix, uNormalMatrix

        shader.setUniformValue(self.mvp_matrix_location, self.mvp_matrix)
        shader.setUniformValue(self.model_matrix_location, self.model_matrix)
        shader.setUniformValue(self.normal_matrix_location, self.normal_matrix)
        self.texture = texture
        t1 = shader.uniforms['Texture']
        self.functions.glActiveTexture(gl.GL_TEXTURE0)
        self.functions.glUniform1i(t1, 0)
        self.texture.bind()

        self.functions.glUniform1f(shader.uniforms['AOMult'], 2.0)
        self.functions.glUniform1i(shader.uniforms['AOTexture'], 1)
        self.functions.glActiveTexture(gl.GL_TEXTURE1)
        self.texture.bind()

        if self.infront:
            self.functions.glDisable(gl.GL_DEPTH_TEST)
        else:
            self.functions.glEnable(gl.GL_DEPTH_TEST)

        if self.transparent:
            self.functions.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        else:
            self.functions.glBlendFunc(gl.GL_ONE, gl.GL_ZERO)
        self.functions.glEnable(gl.GL_BLEND)

        self.functions.glDrawElements(gl.GL_TRIANGLES, len(self.indices), gl.GL_UNSIGNED_INT, self.indices)
        self.functions.glDisable(gl.GL_BLEND)
        self.functions.glDisable(gl.GL_DEPTH_TEST)
        self.functions.glActiveTexture(gl.GL_TEXTURE0)

