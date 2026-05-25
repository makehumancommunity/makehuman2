"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck, Elvaerwyn_MH2 2026 V 1.2

    (load and store shaders)

    Classes:
    * ShaderFiles
    * ShaderRepository
"""
import os
from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram

class ShaderFiles(QOpenGLShaderProgram):
    """
    class to store 3 connected shaders
    """
    def __init__(self, env, name, path):
        self.uniforms = { "uMvpMatrix": -1, "uModelMatrix": -1, "uNormalMatrix": -1,
                "ambientLight": -1, "lightWeight": -1, "viewPos": -1, "blinn": -1,
                "Texture": -1, "litsphereTexture": -1, "AdditiveShading": -1,
                "AOTexture": -1, "AOMult": -1, "MRTexture": -1, "MeMult": -1, "RoMult": -1,
                "NOTexture": -1, "NoMult": -1, "EMTexture": -1, "EmMult": -1, "skybox": -1, "useSky": -1,
"transmission": -1, "ior": -1, "glassRoughness": -1, "glassColor": -1 
        }
        self.env = env
        self.name = name
        self.frag_id = None
        self.vert_id = None
        self.geom_id = None
        self.path = path
        super().__init__()

    def __str__(self):
        return "Shader Files: "+ self.path

    def loadFragShader(self):
        path = self.path + ".frag"
        self.env.logLine(8, "Load: " + path)
        if self.addShaderFromSourceFile(QOpenGLShader.Fragment, path):
            self.frag_id  = self.shaders()[-1].shaderId()

    def loadVertShader(self):
        path = self.path + ".vert"
        self.env.logLine(8, "Load: " + path)
        if self.addShaderFromSourceFile(QOpenGLShader.Vertex,path):
            self.vert_id = self.shaders()[-1].shaderId()

    def loadGeomShader(self):
        path = self.path + ".geom"
        self.env.logLine(8, "Load: " + path)
        if self.addShaderFromSourceFile(QOpenGLShader.Geometry,path):
            self.geom_id = self.shaders()[-1].shaderId()

    def loadAllShaderTypes(self):
        self.loadFragShader()
        self.loadVertShader()
        if os.path.isfile(self.path + ".geom"):
            self.loadGeomShader()

class ShaderRepository():
    def __init__(self, glob):
        self.glob = glob
        self.env = glob.env
        self._shaders = []          # list of shaders
        self._shadernames = {}      # shaders by name reference to _shaders

        if self.env.osindex == 2:
            self.prefix = "v12_"    # in case of OSX limit the shaders to OpenGL version 1.2
            self.env.logLine(1, "Working with shader prefix: " + self.prefix)
        else:
            self.prefix = ""

    def getShader(self, name):
        """
        return shader by name
        if not known, return default
        """
        shadernum = self._shadernames[name] if name in self._shadernames else 0
        return  self._shaders[shadernum]

    def loadShader(self, filename):
        path = os.path.join (self.env.path_sysdata, "shaders", self.prefix+filename)
        if path in self._shadernames:
            return self._shadernames[path]

        files = ShaderFiles(self.env, filename, path)
        files.loadAllShaderTypes()
        self._shaders.append(files)
        shadernum = len(self._shaders)-1
        self._shadernames[filename] = shadernum
        return shadernum

    def loadShaders(self, filenames):
        """
        load a list of shaders
        """
        for shader in filenames:
            s = self.loadShader(shader)
            self.attribVertShader(s)
            self.getUniforms(s)

    def attribVertShader(self, num=0):
        shader = self._shaders[num]
        shader.bindAttributeLocation("aPosition", 0)
        shader.bindAttributeLocation("aNormal", 1)
        shader.bindAttributeLocation("aTexCoords", 2)
        shader.link()
        shader.bind()

    def bindShader(self, shader):
        shader.bind()

    def getUniforms(self, num=0):
        shader = self._shaders[num]
        for key in shader.uniforms.keys():
            shader.uniforms[key] = shader.uniformLocation(key)
        self.env.logLine(2, "Shader: " + self._shaders[num].name + " " + str(shader.uniforms))

    def setShaderUniform(self, shader, name, var):
        if name in shader.uniforms:
            if shader.uniforms[name] != -1:
                shader.setUniformValue(shader.uniforms[name], var)
            else:
                print (name + " not registered")

    def setShaderArrayStruct(self, shader, name, index, member, var):
        name = name + "[" + str(index) + "]." + member
        loc = shader.uniformLocation(name)
        if loc != -1:
            if isinstance(var, float):
                shader.setUniformValue1f(loc, var)
            else:
                shader.setUniformValue(loc, var)
        else:
            print (name + " not registered")

