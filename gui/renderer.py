"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * RendererValues
    * Renderer
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLineEdit, QGridLayout, QLabel, QMessageBox,  QCheckBox, QHBoxLayout

from gui.common import IconButton, MHFileRequest, MHBusyWindow, WorkerThread, ImageBox
from gui.slider import SimpleSlider

from opengl.offscreen import OffScreenRender
from core.loopapproximation import LoopApproximation

import os

class RendererValues():
    """
    class to keep the values, when called again
    """
    def __init__(self, glob):
        self.doCorrections = False
        self.transparent = False
        self.posed = False
        self.imwidth  = 1000
        self.imheight = 1000
        self.angle = 0

class Renderer(QVBoxLayout):
    """
    Render screen
    """
    def __init__(self, parent, glob):
        super().__init__()
        self.parent = parent
        self.glob = glob
        self.env = glob.env
        self.view = glob.openGLWindow
        self.bc  = glob.baseClass
        self.mesh = self.bc.baseMesh
        self.posemod = self.bc.posemodifier
        self.bvh = self.bc.bvh
        self.blockchange = False

        self.image = None
        self.subdiv = False
        self.values = self.glob.guiPresets["Renderer"]

        self.prog_window = None     # progressbar
        #
        # close subwindows just in case because they cannot work on mesh copies
        #
        self.glob.closeSubwindow("materialedit")
        self.glob.closeSubwindow("material")
        self.glob.closeSubwindow("asset")

        # store used n_objects (used for unsubdividing)
        #
        self.n_objects = []
        if self.bc.proxy is None:
            self.n_objects.append(self.bc.baseMesh)
        for elem in self.glob.baseClass.attachedAssets:
            self.n_objects.append(elem.obj)

        # subdivided objects
        self.s_objects = []

        glayout = QGridLayout()
        glayout.addWidget(QLabel("Render to offscreen canvas of size:"), 0, 0, 1, 2)
        glayout.addWidget(QLabel("Width"), 1, 0)
        self.width = QLineEdit()
        self.width.editingFinished.connect(self.acceptIntegers)
        glayout.addWidget(self.width, 1, 1)

        glayout.addWidget(QLabel("Height"), 2, 0)
        self.height = QLineEdit()
        self.height.editingFinished.connect(self.acceptIntegers)
        glayout.addWidget(self.height, 2, 1)
        self.addLayout(glayout)

        self.transButton = QCheckBox("transparent canvas")
        self.transButton.setLayoutDirection(Qt.LeftToRight)
        self.transButton.toggled.connect(self.changeTransparency)
        self.addWidget(self.transButton)

        if self.bvh:
            self.corrAnim = QCheckBox("overlay corrections")
            self.corrAnim.setLayoutDirection(Qt.LeftToRight)
            self.corrAnim.toggled.connect(self.changeAnim)
            self.addWidget(self.corrAnim)

        if self.bvh or self.posemod:
            self.posedButton = IconButton(1,  os.path.join(self.env.path_sysicon, "an_pose.png"), "character posed", self.changePosed, checkable=True)
            ilayout = QHBoxLayout()
            ilayout.addWidget(self.posedButton)

            if self.bvh and self.bvh.frameCount > 1:
                self.frameSlider = SimpleSlider("Frame number: ", 0, self.bvh.frameCount-1, self.frameChanged, minwidth=250)
                self.frameSlider.setSliderValue(self.bvh.currentFrame)
                ilayout.addWidget(self.frameSlider)
            else:
                ilayout.addStretch()

            self.addLayout(ilayout)

        self.angSlider = SimpleSlider("Rotation: ", -180, 180, self.rotChanged, minwidth=250)
        self.angSlider.setSliderValue(self.values.angle)
        self.addWidget(self.angSlider)

        self.subdivbutton = QPushButton("Smooth (subdivided)")
        self.subdivbutton.clicked.connect(self.toggleSmooth)
        self.subdivbutton.setCheckable(True)
        self.subdivbutton.setChecked(False)
        self.subdivbutton.setToolTip("select all other options before using subdivision!")
        self.addWidget(self.subdivbutton)

        button = QPushButton("Render")
        button.clicked.connect(self.render)
        self.addWidget(button)

        self.saveButton = IconButton(1,  os.path.join(self.env.path_sysicon, "f_save.png"), "save rendered image", self.saveImage)
        self.viewButton = IconButton(2,  os.path.join(self.env.path_sysicon, "render.png"), "show rendered image", self.viewImage)
        self.addWidget(self.viewButton)
        self.addWidget(self.saveButton)


    def enter(self):
        self.image = None
        if self.bvh or self.posemod:
            if self.values.posed:
                self.bc.setPoseMode()
                self.setFrame(0)
        self.glob.midColumn.renderView(True)
        self.view.scene.newFloorPosition(posed=True)
        self.setButtons()

    def rotChanged(self, value):
        self.values.angle = value
        self.view.setYRotation(float(value))
        self.view.Tweak()

    def setUnsubdivided(self):
        self.subdivbutton.setChecked(False)
        if self.subdiv:
            self.unSubdivide()
            self.subdiv = False

    def leave(self):
        self.setUnsubdivided()

        if (self.bvh or self.posemod) and self.values.posed:
            self.setFrame(0)
            self.bc.setStandardMode()

        self.view.setYRotation(0.0)
        self.view.Tweak()
        self.glob.midColumn.renderView(False)

    def setFrame(self, value):
        if self.posemod:
            self.bc.showPose()
            return

        if self.bvh is None:
            print ("No file loaded")
            return

        if value < 0:
            return

        if value >= self.bvh.frameCount:
            return

        self.bvh.currentFrame = value
        if self.bvh.frameCount > 1:
            self.frameSlider.setSliderValue(value)
        self.bc.showPose()

    def frameChanged(self, value):
        self.setUnsubdivided()
        self.setFrame(int(value))

    def changeTransparency(self, param):
        self.values.transparent = param

    def changePosed(self, param):
        if self.blockchange:
            return
        if self.subdiv:
            self.unSubdivide()
        if self.values.posed:
            self.leave()
            self.values.posed = param
            self.setButtons()
        else:
            self.setUnsubdivided()
            self.values.posed = param
            self.enter()

    def setButtons(self):
        self.saveButton.setEnabled(self.image is not None)
        self.viewButton.setEnabled(self.image is not None)
        self.transButton.setChecked(self.values.transparent)
        self.width.setText(str(self.values.imwidth))
        self.height.setText(str(self.values.imheight))
        if self.bvh or self.posemod:
            self.corrAnim.setEnabled((len(self.bc.bodyposes) > 0 or len(self.bc.faceposes) > 0) and self.values.posed)

            # avoid signal for posedButton
            #
            self.blockchange = True
            self.posedButton.setChecked(self.values.posed)
            self.blockchange = False

            self.corrAnim.setChecked(self.values.doCorrections)
            if self.bvh.frameCount > 1:
                self.frameSlider.setEnabled(self.values.posed)

    def acceptIntegers(self):
        m = self.sender()
        try:
            i = int(m.text())
        except ValueError:
            m.setText("1000")
            i = 1000
        else:
            if i < 64:
                i = 64
            elif i > 8192:
                i = 8192
            m.setText(str(i))
        if m == self.width:
            self.values.imwidth = i
        else:
            self.values.imheight = i

    def changeAnim(self):
        if self.subdiv:
            self.unSubdivide()
        self.values.doCorrections = self.corrAnim.isChecked()
        if self.values.doCorrections:
            self.bvh.modCorrections()
        else:
            self.bvh.identFinal()
        self.bc.showPose()


    def Subdivide(self, bckproc, *args):
        """
        replaces meshes
        """
        self.s_objects = []
        if self.bc.proxy is None:
            self.prog_window.setLabelText("Subdiving basemesh")
            sobj = LoopApproximation(self.glob, self.bc.baseMesh)
            self.bc.baseMesh = sobj.doCalculation()
            self.s_objects.append(self.bc.baseMesh)

        for elem in self.glob.baseClass.attachedAssets:
            self.prog_window.setLabelText("Subdiving " + elem.obj.name)
            sobj = LoopApproximation(self.glob, elem.obj)
            elem.obj = sobj.doCalculation()
            self.s_objects.append(elem.obj)


    def finishSubdivide(self):
        if self.prog_window is not None:
            self.prog_window.progress.close()
            self.prog_window = None
            for obj in self.s_objects:
                self.view.createObject(obj)

            self.glob.openGLBlock = False
            self.view.setYRotation(float(self.values.angle))
            self.view.Tweak()
            self.glob.parallel = None

    def parSubdivide(self):
        if self.glob.parallel is None:
            self.prog_window = MHBusyWindow("Subdivision", "start")
            self.prog_window.progress.forceShow()
            self.glob.openGLBlock = True
            if self.bc.proxy is None:
                self.view.noGLObjects(delMaterial=False)
            else:
                self.view.noGLObjects(leavebase=True,  delMaterial=False)
            self.glob.parallel = WorkerThread(self.Subdivide)
            self.glob.parallel.start()
            self.glob.parallel.finished.connect(self.finishSubdivide)


    def unSubdivide(self):
        """
        replaces meshes back to normal
        """
        self.glob.openGLBlock = True

        if self.bc.proxy is None:
            self.view.noGLObjects(delMaterial=False)
            self.bc.baseMesh = self.n_objects[0]
            self.view.createObject(self.bc.baseMesh)
            n = 1
        else:
            self.view.noGLObjects(leavebase=True, delMaterial=False)
            n = 0

        for elem in self.glob.baseClass.attachedAssets:
            elem.obj = self.n_objects[n]
            self.view.createObject(elem.obj)
            n +=1
        self.glob.openGLBlock = False
        self.view.setYRotation(float(self.values.angle))
        self.view.Tweak()

    def toggleSmooth(self):
        b = self.sender()
        self.subdiv = b.isChecked()
        if self.subdiv:
            self.parSubdivide()
        else:
            self.unSubdivide()

    def render(self):
        width  = int(self.width.text())
        height = int(self.height.text())

        pix = OffScreenRender(self.glob, self.view, self.values.transparent)
        pix.getBuffer(width, height)
        self.image = pix.bufferToImage()
        pix.releaseBuffer()
        self.setButtons()

    def viewImage(self):
        ImageBox(self.parent, "Viewer", self.image, color=self.view.light.glclearcolor)

    def saveImage(self):
        directory = self.env.stdUserPath()
        freq = MHFileRequest(self.glob, "Image (PNG)", "image files (*.png)", directory, save=".png")
        filename = freq.request()
        if filename is not None:
            self.image.save(filename, "PNG", -1)
            QMessageBox.information(self.parent.central_widget, "Done!", "Image saved as " + filename)


