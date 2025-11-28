"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * Camera
    * Light
"""
from PySide6.QtGui import QMatrix4x4, QVector3D, QVector4D
import OpenGL
from OpenGL import GL as gl
from math import pi as M_PI, atan, degrees, sqrt

class Camera():
    """
    should always calculate view matrix and projection matrix
    :param glob: global object class
    :param float o_size: height of character
    :param int w: initial width of the viewport
    :param int h: initial height of the viewport
    """
    def __init__(self, glob, o_size, w, h):
        """
        all parameters connected with camera
        """
        self.glob = glob
        self.o_height =  o_size

        self.nearPlane = 0.1                # clipping for near plane
        self.farPlane = 300                 # clipping for far plane
        self.maxDist  = self.farPlane - self.farPlane / 10.0   # max distance, perspective mode
        self.minDist  = 1.1                 # min distance, perspective mode
        self.startDist = 50.0               # initial camera distance
        self.maxOrthoMag = 100.0            # max magnification orthogonal mode
        self.minOrthoMag = 1.1              # min magnification orthogonal mode

        self.focalLength = 50.0             # current focal length, start with a normed focal length
        self.verticalAngle = 0.0            # current vertical angle
        self.ortho_magnification =4.8       # magnification to fill screen in ortho-mode (will be recalculated)
        self.view_width = w                 # current screen size, width
        self.view_height = h                # current screen size, height

        self.last_mousex = 0                # last mouse position in x
        self.last_mousey = 0                # last mouse position in y
        self.deltaAngleX = 0                # movement left to right = 2*PI = 360 deg
        self.deltaAngleY = 0                # movement top to bottom = PI = 180 deg
        self.deltaMoveX = 0                 # movement left to right for panning
        self.deltaMoveY = 0                 # movement top to bottom for panning

        self.view_matrix = QMatrix4x4()         # from world space to camera or view-space
        self.proj_matrix = QMatrix4x4()         # from camera space to clip space
        self.proj_view_matrix = QMatrix4x4()    # precalculated product of proj_matrix and view_matrix, needed to draw objects

        self.cameraPos =  QVector3D()           # the position of the camera
        self.cameraDir =  QVector3D()           # direction of the camera (what is up, x is usually not changed)
        self.lookAt = QVector3D()               # the position to focus
        self.center = QVector3D()               # the center of the object to focus on
        self.lastCamChange =  QVector3D()       # last camera change
        self.resetCamera()
        self.updateViewMatrix()

    def __str__(self):
        x   = self.cameraPos.toTuple()
        pos = list(map(lambda x: round(x,2), x))

        x   = self.lookAt.toTuple()
        lookat = list(map(lambda x: round(x,2), x))

        direct = self.cameraDir.toTuple()
        return ("Pos: " + str(pos) + "\nAim: " + str(lookat) + "\nDir: " +  str(direct) + \
                "\nAng: " + str(round(self.verticalAngle,2)) + "\nMag: " + str(round(self.ortho_magnification,2)))

    def calcOrthoMagFromHeight(self):
        """
        calculate size of the character according to screen height (in units)
        """
        return self.view_height / (self.o_height * 9.5)

    def setOrthoMagFromHeight(self, factor=1.0):
        """
        set ortho_magnification to size of the character according to screen height (in units)
        :param float factor: factor to multiply (used when toggling)
        """
        self.ortho_magnification = factor * self.calcOrthoMagFromHeight()

    def calculateVerticalAngle(self):
        height = self.o_height * 1.05
        self.verticalAngle = 2 * degrees(atan(height/(2*self.focalLength)))
        return self.verticalAngle

    def getCameraDistance(self):
        return (self.cameraPos - self.lookAt).length()

    def getFocalLength(self):
        return self.focalLength

    def setFocalLength(self, value):
        self.focalLength = value
        #
        v = self.cameraPos - self.lookAt
        l = v.length() /value
        self.cameraPos =  (v / l) + self.center
        #
        self.updateViewMatrix()
        self.calculateProjMatrix()

    def getViewMatrix(self):
        return self.view_matrix

    def getProjViewMatrix(self):
        return self.proj_view_matrix

    def getCameraPos(self):
        return self.cameraPos

    def getViewDirection(self):
        return -self.view_matrix.transposed().row(2).toVector3D()

    def getRightVector(self):
        return self.view_matrix.transposed().row(0).toVector3D()

    def updateViewMatrix(self):
        """
        new position of camera
        """
        self.view_matrix.setToIdentity()
        self.view_matrix.lookAt( self.cameraPos, self.lookAt, self.cameraDir)
        self.proj_view_matrix = self.proj_matrix * self.view_matrix

    def calculateOrthoMatrix(self):
        self.proj_matrix.setToIdentity()
        factor = self.o_height* self.ortho_magnification
        w_o = float(self.view_width) / factor
        h_o = float(self.view_height) / factor
        self.proj_matrix.ortho(-w_o, w_o, -h_o, h_o, 0.1, self.farPlane)

    def resetCamera(self):
        self.cameraPers = True
        self.cameraHeight = 0
        self.focalLength = 50.0                # start with a norm focal length
        self.cameraDist = self.startDist       # calculate distance by trigonometric functions later
        self.cameraPos =  QVector3D(0, self.cameraHeight, self.cameraDist)
        self.lookAt =  self.center.__copy__()
        self.cameraDir =  QVector3D(0, 1, 0)
        self.lastCamChange = QVector3D(0, 0, 0)
        self.setOrthoMagFromHeight()

    def setCenter(self, center, size):
        self.o_height = size
        self.calculateVerticalAngle()
        self.setOrthoMagFromHeight()
        self.lookAt = QVector3D(center[0], center[1], center[2])
        self.center = self.lookAt.__copy__()
        self.setFocalLength(50)
        self.cameraHeight = center[1]
        self.cameraDist = self.cameraPos.z()
        self.updateViewMatrix()
        self.glob.env.logLine(1, "Set Center: " + str(center) + ", character size: " + str(size))

    def customView(self, direction):
        """
        the axis 6 views
        :param direction: camera direction as matrix, y is 1 for top view, -1 for bottom, otherwise 0
        """
        diry = direction.y() # front will be 0.0

        h2 = self.o_height / 2
        self.lookAt =  self.center.__copy__()

        if not self.cameraPers:
            self.cameraDist = self.center.z() + self.startDist
            if self.lastCamChange == direction:
                self.cameraPos =  self.center + direction * self.cameraDist
                h = self.cameraHeight
                self.setOrthoMagFromHeight()
            else:
                h = self.cameraPos.y()
                self.cameraPos =  self.center + direction * self.cameraDist
            if diry == 0.0:
                if h > h2:
                    self.cameraPos.setY(h2)
                    self.lookAt.setY(h2)
                elif h < -h2:
                    self.cameraPos.setY(-h2)
                    self.lookAt.setY(-h2)
                else:
                    self.cameraPos.setY(h)
                    self.lookAt.setY(h)
                self.cameraDir =  QVector3D(0, 1, 0)
            else:
                self.cameraDir =  QVector3D(0, 0, 1)
            self.lastCamChange = direction
            self.calculateOrthoMatrix()
            self.updateViewMatrix()
            return

        # double clicked, default views, otherwise change axis only
        #
        if self.lastCamChange == direction:
            self.cameraDist = self.center.z() + self.startDist
            h = self.cameraHeight
            t = self.cameraDist
        else:
            self.cameraDist = self.getCameraDistance()
            h = self.cameraPos.y()
            t = h

        self.cameraPos =  self.center + direction * self.cameraDist

        if diry == 0.0:
            if h > h2:
                self.cameraPos.setY(h2)
                self.lookAt.setY(h2)
            elif h < -h2:
                self.cameraPos.setY(-h2)
                self.lookAt.setY(-h2)
            else:
                self.cameraPos.setY(h)
                self.lookAt.setY(h)

            self.cameraDir =  QVector3D(0, 1, 0)

        elif diry == 1.0:
            if t < self.o_height:
                self.cameraPos.setY(self.o_height)
            self.cameraDir =  QVector3D(0, 0, 1)
        else:
            if -t > -self.o_height:
                self.cameraPos.setY(-self.o_height)
            self.cameraDir =  QVector3D(0, 0, 1)

        self.lastCamChange = direction
        self.updateViewMatrix()

    def modifyDistance(self, direction):
        """
        move one unit on vector (zoom by vector length),
        avoid zooming beyond borders
        :param int direction: factor 1 or -1 for zoom out/in
        """
        if self.cameraPers:
            v = self.cameraPos - self.lookAt
            l = v.length()
            if l > self.maxDist and direction > 0 or \
                l < self.minDist and direction < 0:
                return

            l *= direction
            self.cameraPos += ( v / l)
            self.camereDist = v
            self.updateViewMatrix()
        else:
            if direction > 0 and self.ortho_magnification < self.minOrthoMag or \
                direction < 0 and self.ortho_magnification > self.maxOrthoMag:
                return
            self.ortho_magnification -= (self.ortho_magnification / 20 ) * direction
            self.calculateOrthoMatrix()
            self.updateViewMatrix()

    def togglePerspective(self, mode):
        """
        toggle between perspective and ortho mode. In case change from perspective to ortho,
        magnification is changed. Otherwise camera distance is changed according to
        focal length and the magnification factor from ortho-mode
        :param bool mode: True is perspective mode
        """
        if self.cameraPers:
            self.camereDist = self.getCameraDistance()
            self.setOrthoMagFromHeight(self.focalLength / self.camereDist)
        else:
            # calculate factor current magnification vs. standard
            #
            factor = self.ortho_magnification / self.calcOrthoMagFromHeight()

            # create new camera position from old position using the distance multiplied by factor
            #
            v = self.cameraPos - self.lookAt
            l = (v.length() / self.focalLength) * factor
            self.cameraPos =  (v / l) + self.center
            self.updateViewMatrix()

        # now set new mode and recalculate matrix
        #
        self.cameraPers = mode
        self.calculateProjMatrix()

    def setLastMousePosition(self, x, y):
        """
        used when mouse pressed inside graphics-window to save last mouse position
        :param float x: x position
        :param float y: y position
        """
        self.last_mousex = x 
        self.last_mousey = y 

    def arcBallRotation(self, x, y):
        """
        mouse navigation (rotation with button pressed)
        TODO: no arcball navigation for cos= 1.0
        (top view, bottom view)
        :param float x: x position
        :param float y: y position
        """
        xAngle = (self.last_mousex - x) * self.deltaAngleX
        yAngle = (self.last_mousey - y) * self.deltaAngleY

        # avoid camera direction is identical to up vector
        #
        cosAngle = QVector3D.dotProduct(self.getViewDirection(), self.cameraDir)
        if abs(cosAngle) > .99:
            yangle = 0

        # x rotation
        #
        rotMatrixX = QMatrix4x4()                   # create as identity matrix
        rotMatrixX.rotate(xAngle, self.cameraDir)   # rotate in x
        position = rotMatrixX.map(self.cameraPos - self.lookAt) + self.lookAt

        # y rotation
        #
        rotMatrixY = QMatrix4x4()
        rotMatrixY.rotate(yAngle, self.getRightVector())
        position = rotMatrixY.map(position - self.lookAt) + self.lookAt
        self.cameraPos = position
        self.updateViewMatrix()

    def mousePanning(self, x, y):
        """
        calculate difference and calculate position
        """
        mx = (self.last_mousex - x) * self.deltaMoveX
        my = (self.last_mousey - y) * self.deltaMoveY
        self.setLastMousePosition(x, y)
        self.panning(mx, my)

    def panning(self, mx, my):
        """
        a panning mode, not 100% correct
        """
        frontview = (self.cameraDir.y() != 0.0)
        direct = self.cameraPos - self.center
        xv = direct.x()
        yv = direct.y()
        zv = direct.z()
        lenx = abs(xv)
        leny = abs(yv)
        lenz = abs(zv)

        diffx = mx
        if frontview:
            diffy = my
            if lenx > lenz:
                if lenz > 10.0:
                    diffz = mx * (xv/zv) if zv > 10.0 else -mx * (xv/zv)
                    diffx = mx * (lenx/zv)
                else:
                    diffz = mx if xv > 0 else -mx
                    diffx = 0
            else:
                if lenx > 10.0:
                    diffz = mx * (lenz/xv)
                    diffx = mx * (zv/xv) if xv > 10.0 else -mx * (zv/xv)
                else:
                    if zv < 0:
                        diffx = -mx
                    diffz = 0
        else:
            diffz = my
            if lenx > leny:
                if leny > 10.0:
                    diffy = mx * (xv/yv) if yv > 10.0 else -mx * (xv/yv)
                    diffx = mx * (lenx/yv)
                else:
                    diffy = mx if xv > 0 else -mx
                    diffx = 0
            else:
                if lenx > 10.0:
                    diffy = mx * (leny/xv)
                    diffx = mx * (yv/xv) if xv > 10.0 else -mx * (yv/xv)
                else:
                    if yv > 0:
                        diffx = -mx
                    diffy = 0

        diffx *= 10.0
        diffy *= 10.0
        diffz *= 10.0

        self.lookAt.setX(self.lookAt.x() + diffx)
        self.lookAt.setZ(self.lookAt.z() - diffz)
        self.lookAt.setY(self.lookAt.y() - diffy)
        self.cameraPos.setX(self.cameraPos.x() + diffx)
        self.cameraPos.setZ(self.cameraPos.z() - diffz)
        self.cameraPos.setY(self.cameraPos.y() - diffy)

        self.updateViewMatrix()

    def resizeViewPort(self, w, h):
        """
        called in case of resize of the viewport
        recalculate magnifaction for ortho mode, rotation and panning parameter
        :param int w: new width of the viewport
        :param int h: new height of the viewport
        """
        factor = h / self.view_height
        self.ortho_magnification *= factor
        self.view_width = w
        self.view_height = h
        self.deltaAngleX = 2 * M_PI / w # movement left to right = 2*PI = 360 deg
        self.deltaAngleY = M_PI / h     # movement top to bottom = PI = 180 deg
        self.deltaMoveX = 1 / w         # same for panning
        self.deltaMoveY = 1 / h         # same for panning

    def calculateProjMatrix(self):
        w = float(self.view_width)
        h = float(self.view_height)

        if self.cameraPers:
            va = self.calculateVerticalAngle()
            self.proj_matrix.setToIdentity()
            self.proj_matrix.perspective(va, w / h, self.nearPlane, self.farPlane)
        else:
            self.calculateOrthoMatrix()
        self.proj_view_matrix = self.proj_matrix * self.view_matrix
        return self.proj_view_matrix


class Light():
    """
    can be used to manipulate light in scene, used for up to 3 lights
    """

    def __init__(self, shaders, glob):
        self.glob = glob
        self.shaderInit = glob.shaderInit
        self.shaders = shaders
        self.phong = shaders.getShader("phong")
        self.pbr = shaders.getShader("pbr")
        self.toon = shaders.getShader("toon")
        #
        # volume of scene in units
        #
        self.min_coords = [-25.0, -25.0, -25.0 ]
        self.max_coords = [25.0, 25.0, 25.0 ]

        self.glclearcolor = QVector4D()
        self.ambientLight = QVector4D()
        self.lightWeight = QVector3D()
        self.blinn = False
        self.skybox = True
        self.skyboxname = None

        self.lights = [ 
                { "pos": QVector3D(), "vol": QVector3D(), "int": 0.0, "type": 0 }, 
                { "pos": QVector3D(), "vol": QVector3D(), "int": 0.0, "type": 0 },
                { "pos": QVector3D(), "vol": QVector3D(), "int": 0.0, "type": 0 },
                ]
        self.fromGlobal(False)
    
    def listTo3D(self, v, elems):
        v.setX(elems[0])
        v.setY(elems[1])
        v.setZ(elems[2])

    def listTo4D(self, v, elems):
        v.setX(elems[0])
        v.setY(elems[1])
        v.setZ(elems[2])
        v.setW(elems[3])

    def q3ToList(self, v):
        return (v.x(), v.y(), v.z())

    def q4ToList(self, v):
        return (v.x(), v.y(), v.z(), v.w())

    def fromGlobal(self, load_json):
        if load_json:
            self.shaderInit = self.glob.readShaderInitJSON()
        self.blinn = self.shaderInit["blinn"]
        self.skybox = self.shaderInit["skybox"]
        self.skyboxname = self.shaderInit["skyboxname"]
        self.listTo4D(self.glclearcolor, self.shaderInit["glclearcolor"])
        self.listTo4D(self.ambientLight, self.shaderInit["ambientcolor"])
        self.lightWeight.setY(self.shaderInit["specularfocus"])
        for i, d in enumerate(self.lights):
            s = self.shaderInit["lamps"][i]
            self.listTo3D(d["pos"], s["position"])
            self.listTo3D(d["vol"], s["color"][:3])     # color + intensity are in one array in json
            d["int"] = s["color"][3]
            d["type"] = s["type"]
        self.setShader()

    def toGlobal(self):
        self.shaderInit["blinn"] = self.blinn
        self.shaderInit["glclearcolor"] = self.q4ToList(self.glclearcolor)
        self.shaderInit["ambientcolor"] = self.q4ToList(self.ambientLight)
        self.shaderInit["specularfocus"] =  self.lightWeight.y()
        self.shaderInit["skyboxname"] = self.skyboxname
        for i, s in enumerate(self.lights):
            d = self.shaderInit["lamps"][i]
            d["position"] = self.q3ToList(s["pos"])

            d["color"]    = list(self.q3ToList(s["vol"]))  # recombine array
            d["color"].append(s["int"])

            d["type"] = s["type"]

    def setShader(self):
        for shader in [self.phong, self.pbr, self.toon]:
            self.shaders.bindShader(shader)
            for i, elem in enumerate(self.lights):
                self.shaders.setShaderArrayStruct(shader, "pointLights", i, "position", elem["pos"])
                self.shaders.setShaderArrayStruct(shader, "pointLights", i, "color", elem["vol"])
                self.shaders.setShaderArrayStruct(shader, "pointLights", i, "intensity", elem["int"])
                self.shaders.setShaderArrayStruct(shader, "pointLights", i, "type", elem["type"])
            self.shaders.setShaderUniform(shader, "ambientLight", self.ambientLight)
        
        # next ones are only for phong
        #
        self.shaders.bindShader(self.phong)
        self.shaders.setShaderUniform(self.phong, "blinn", self.blinn)
        self.shaders.setShaderUniform(self.phong, "lightWeight", self.lightWeight)

    def useBlinn(self, value):
        if value != self.blinn:
            self.blinn = value
            self.setShader()

    def useSkyBox(self, value):
        self.skybox = value

    def setAmbientLuminance(self, value):
        self.ambientLight.setW(value)
        self.setShader()

    def setSpecularLuminance(self, value):
        self.lightWeight.setX(value)
        self.setShader()

    def setSpecularFocus(self, value):
        self.lightWeight.setY(value)
        self.setShader()

    def setClearColor(self, value):
        self.glclearcolor.setX(value.redF())
        self.glclearcolor.setY(value.greenF())
        self.glclearcolor.setZ(value.blueF())
        self.glclearcolor.setW(1.0)

    def setAmbientColor(self, value):
        self.ambientLight.setX(value.redF())
        self.ambientLight.setY(value.greenF())
        self.ambientLight.setZ(value.blueF())
        self.setShader()

    def setHPos(self, num, y):
        m =  self.lights[num]["pos"]
        m.setY(y)
        self.setShader()

    def setLPos(self, num, x, z):
        m =  self.lights[num]["pos"]
        m.setX(x)
        m.setZ(z)
        self.setShader()

    def setType(self, num, ltype):
        self.lights[num]["type"] = ltype
        self.setShader()

    def setLLuminance(self, num, value):
        self.lights[num]["int"] = value
        self.setShader()

    def setLColor(self, num, value):
        m =  self.lights[num]["vol"]
        m.setX(value.redF())
        m.setY(value.greenF())
        m.setZ(value.blueF())
        self.setShader()

