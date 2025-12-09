"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * Scene
"""
from opengl.material import Material
from opengl.prims import CoordinateSystem, Grid, BoneList, VisLights, DiamondSkeleton, Cuboid

class Scene():
    """
    Class to hold additional objects and common elements

    :param globalObjects glob: pointer to global objects
    :param OpenGLView parent: parent QOpenGLWidget widget
    :param ShaderRepository shaders: pointer to shader repository
    :param function update: the parent update function to redraw elements
    """
    def __init__(self, glob, parent, shaders, update):

        self.glob = glob
        self.parent = parent
        self.context = parent.context()
        self.shaders = shaders
        self.update = update
        self.env = glob.env

        # floor
        #
        self.floor = False
        self.floortex = None
        self.floorsize = [10.0, 0.2, 10.0]
        self.floortexname = "default.png"

        # scene components
        #
        self.sysmaterials = []
        self.prims = {}
        self.visLights = None
        self.diamondskel = False
        self.other_objects_invisible = False

        # create system uni-colored materials
        #

        for name in ("black", "white", "orange", "red", "normal", "floor"):
            m = Material(self.glob, name, "system")
            self.sysmaterials.append(m)

        self.black = self.sysmaterials[0].uniColor([0.0, 0.0, 0.0])
        self.white = self.sysmaterials[1].uniColor([1.0, 1.0, 1.0])
        self.orange= self.sysmaterials[2].uniColor([1.0, 0.5, 0.0])
        self.red   = self.sysmaterials[3].uniColor([1.0, 0.5, 0.5])
        self.normal= self.sysmaterials[4].uniColor([0.5, 0.5, 1.0])

        # and floor texture
        self.floorTexture(self.floortexname)


    def lowestPos(self, posed=False):
        if self.glob.baseClass is not None:
            return self.glob.baseClass.getLowestPos(posed)
        else:
            return 20

    def createPrims(self, light):
        """
        create all primitives, axes, floor, light

        :param Light light: light class
        """
        shader = self.shaders.getShader("fixcolor")
        self.prims["axes"] = CoordinateSystem(self.context, shader, "axes", 10.0)
        lowestPos = self.lowestPos()

        self.prims["xygrid"] = Grid(self.context, shader, "xygrid", 10.0, lowestPos, "xy")
        self.prims["yzgrid"] = Grid(self.context, shader, "yzgrid", 10.0, lowestPos, "yz")
        self.prims["xzgrid"] = Grid(self.context, shader, "xzgrid", 10.0, lowestPos, "xz")
        self.prims["floorcuboid"] = Cuboid(self.context, self.shaders, "floorcuboid", self.floorsize, [0.0, -8.0, 0.0], self.floortex)


        # visualization of lamps (if obj is not found, no lamps are presented)
        #
        self.visLights = VisLights(self.parent, light)
        success =self.visLights.setup()
        if not success:
            self.visLights = None

    def togglePrims(self, name, status):
        """
        toggle a primitive, floor can be the cuboid or a grid, skeleton is presented in pose color or normal color

        :param str name: name of the primitive
        :param bool status: currenct status
        """
        if name == "floor":
            name = "floorcuboid" if self.floor else "xzgrid"
        if name in self.prims:
            if status is True:
                if name == "floorcuboid":
                    self.prims[name].newGeometry(self.lowestPos())
                elif name.endswith("grid"):
                    direction = name[:2]
                    self.prims[name].newGeometry(self.lowestPos(), direction)
                elif name == "skeleton":
                    posed = (self.glob.baseClass.bvh is not None) or (self.glob.baseClass.expression is not None)
                    self.prims[name].newGeometry(posed)
            self.prims[name].setVisible(status)
            self.update()

    # floor
    #
    def setFloor(self, v):
        """
        sets floor, also changes between cuboid or xzgrid

        :param bool v: currenct status
        """
        self.floor = v
        if self.glob.baseClass is not None:
            if v and self.prims["xzgrid"].isVisible():
                self.togglePrims("xzgrid", False)
                self.togglePrims("floorcuboid", True)
            elif not v and self.prims["floorcuboid"].isVisible():
                self.togglePrims("floorcuboid", False)
                self.togglePrims("xzgrid", True)
            self.update()

    def setFloorSize(self, sq=0.0, d=0.0):
        """
        sets the size of the floor

        :param float sq: size of the plane (x, z)
        :param float d: density/height of the floor
        """
        if self.glob.baseClass is not None:
            if sq != 0.0:
                self.floorsize[0] = self.floorsize[2] = sq
            if d != 0.0:
                self.floorsize[1] = d
            self.prims["floorcuboid"].newSize(self.floorsize)
            self.update()

    def hasFloor(self):
        """
        returns if scene has a floor
        """
        if self.glob.baseClass is not None:
            return self.prims["xzgrid"].isVisible() or self.prims["floorcuboid"].isVisible()
        return False

    def floorTexture(self, name):
        """
        sets a floor texture (if available)

        :param str name: name of the texture in shaders folder
        """
        floorpath = self.env.existDataFile("shaders", "floor", name)
        self.floortex = self.sysmaterials[5].setDiffuse(floorpath, self.red, None )
        self.floortexname = name

    def modFloorTexture(self, name):
        """
        sets a new Floor-Texture

        :param str name: name of the texture in shaders folder
        """
        self.floorTexture(name)
        self.prims["floorcuboid"].setTexture(self.floortex)


    def newFloorPosition(self, posed=False):
        """
        sets a new floor position to fit under character

        :param bool posed: if character is posed
        """
        if self.glob.baseClass.floorCalcMethod == 0:
            floorpos = self.lowestPos(posed)
        else:
            floorpos = 0.0
        self.prims["floorcuboid"].newGeometry(floorpos)
        self.prims["xzgrid"].newGeometry(floorpos, "xz")

    # skeleton
    #
    def setObjectsInvisible(self, value):
        self.other_objects_invisible = value

    def prepareSkeleton(self, posed=False):
        """
        prepare graphical presentation of skeleton
        posed mode: orange, normal mode white, internal=no skeleton red

        :param bool posed: if character is posed
        """

        # delete old one
        #
        self.delSkeleton()

        bc = self.glob.baseClass

        # really no skeleton
        #
        if bc is None or (bc.skeleton is None and bc.default_skeleton is None):
            return

        if posed:
            skeleton = bc.pose_skeleton
            col = [1.0, 0.5, 0.0]
            coltex= self.orange
        else:
            skeleton = bc.skeleton
            col = [1.0, 1.0, 1.0]
            coltex= self.white

        if skeleton is None:
            skeleton = bc.default_skeleton
            col = [1.0, 0.5, 0.5]
            coltex= self.red

        shader = self.shaders.getShader("fixcolor")
        if self.diamondskel:
            self.prims["skeleton"] = DiamondSkeleton(self.context, self.shaders, "diamondskel", skeleton, coltex)
        else:
            self.prims["skeleton"] = BoneList(self.context, shader, "skeleton", skeleton, col)
        if self.other_objects_invisible is True:
            self.togglePrims("skeleton", True)
        self.update()

    def hasSkeleton(self):
        """
        returns if a skeleton is available
        """
        return "skeleton" in self.prims

    def delSkeleton(self):
        """
        deletes the skeleton, if available
        """
        if "skeleton" in self.prims:
            self.prims["skeleton"].delete()
            del self.prims["skeleton"]

    def setDiamondSkeleton(self, v):
        """
        toggles between diamond and stick-skeleton
        """
        self.diamondskel = v
        if self.glob.baseClass is not None:
            self.prepareSkeleton(self.glob.baseClass.in_posemode)
            self.update()

    # drawing & modification
    #

    def setYRotation(self, angle):
        """
        set y rotation (only skeleton rotates)

        :param float angle: angle of rotation
        """
        if "skeleton" in self.prims:
            self.prims["skeleton"].setYRotation(angle)

    def draw(self, proj_view_matrix, campos, showskel):
        """
        draws the assets

        :param QMatrix4x4 proj_view_matrix: view-matrix
        :param QVector3D campos: camera position
        :param bool showskel: if the skeleton should be drawn
        """
        bc = self.glob.baseClass

        if self.visLights is not None and self.prims["axes"].isVisible():
            self.visLights.draw(proj_view_matrix, campos, self.white)

        for name in self.prims:
            if name == "skeleton":
                if showskel:
                    if self.diamondskel:
                        self.prims[name].draw(proj_view_matrix, bc.in_posemode)
                    else:
                        self.prims[name].newGeometry(bc.in_posemode)
                        self.prims[name].draw(proj_view_matrix)
            else:
                self.prims[name].draw(proj_view_matrix)

    def cleanUp(self):
        for m in self.sysmaterials:
            m.freeTextures()

