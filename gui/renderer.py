"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck, Elvaerwyn_MH2

    Classes:
    * RendererValues
    * Renderer
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLineEdit, QGridLayout, QLabel, QMessageBox,  QCheckBox, QHBoxLayout, QComboBox

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
        self.rendermode = 0
        self.showafter = True
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
        self.bvh = self.bc.bvh
        self.lastimgview = None

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
        glayout.addWidget(QLabel("Render to canvas of size:"), 0, 0, 1, 2)
        glayout.addWidget(QLabel("Width"), 1, 0)
        self.width = QLineEdit()
        self.width.editingFinished.connect(self.acceptIntegers)
        glayout.addWidget(self.width, 1, 1)

        glayout.addWidget(QLabel("Height"), 2, 0)
        self.height = QLineEdit()
        self.height.editingFinished.connect(self.acceptIntegers)
        glayout.addWidget(self.height, 2, 1)
        glayout.addWidget(QLabel("Foreground limits: w=" + str(self.view.maximumWidth()) + ", h=" + str(self.view.maximumHeight())), 3, 0, 1, 2)
        self.addLayout(glayout)

        self.addWidget(QLabel("Render Mode:"))
        self.viewBox = QComboBox()
        self.viewBox.addItems(["Foreground: extended viewport", "Background: unicolored canvas", "Background: transparent canvas"])
        self.viewBox.currentIndexChanged.connect(self.changeRenderMode)
        self.viewBox.setToolTip('Rendermode')
        self.addWidget(self.viewBox)

        # corrections now work for standard pose as well
        #
        self.corrAnim = QCheckBox("overlay corrections")
        self.corrAnim.setLayoutDirection(Qt.LeftToRight)
        self.corrAnim.toggled.connect(self.changeCorr)
        self.addWidget(self.corrAnim)

        posed, frames = self.bc.hasPoses()
        if posed:
            self.posedButton = IconButton(1,  os.path.join(self.env.path_sysicon, "an_pose.png"), "character posed", self.changePosed, checkable=True)
            ilayout = QHBoxLayout()
            ilayout.addWidget(self.posedButton)

            if frames > 1:
                self.frameSlider = SimpleSlider("Frame number: ", 0, frames-1, self.frameChanged, minwidth=250)
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
        glayout = QGridLayout()
        glayout.addWidget(QLabel("Show rendered image:"), 0, 0)
        self.showAfter = QCheckBox("show result automatically")
        self.showAfter.setLayoutDirection(Qt.LeftToRight)
        self.showAfter.toggled.connect(self.changeShowAfter)
        glayout.addWidget(self.showAfter, 1,0)
        glayout.addWidget(self.viewButton, 0, 1, 2, 1)
        glayout.addWidget(QLabel("Save rendered image:"), 2, 0)
        glayout.addWidget(self.saveButton, 2, 1)
        self.addLayout(glayout)


    def enter(self):
        self.image = None
        poseskel = self.bc.pose_skeleton

        poseskel.useOffset(self.values.doCorrections)

        posed, frames = self.bc.hasPoses()
        if posed:
            if self.values.posed:
                self.bc.setPoseMode()
                self.setFrame(0)

        if posed is False and self.values.doCorrections:
            self.bc.setPoseMode()
            self.correctionsOnly()

        self.glob.midColumn.renderView(True)
        self.glob.midColumn.animViews(True)
        self.view.scene.newFloorPosition(posed=True)
        self.setButtons()
        self.view.Tweak()

    def rotChanged(self, value):
        self.values.angle = value
        self.view.setYRotation(float(value))
        self.view.Tweak()

    def setUnsubdivided(self):
        self.subdivbutton.setChecked(False)
        self.unSubdivide()

    def correctionsOnly(self):
        self.bc.setPoseMode()
        poseskel = self.bc.pose_skeleton
        blends = self.bc.posecorrections
        position = self.bc.positioncorrection

        if position is not None:
            poseskel.setOffset(position)
        if len(blends) > 0:
            poseskel.poseFromRestPose(blends, False)

    def leave(self):
        self.setUnsubdivided()

        posed, frames = self.bc.hasPoses()

        if posed and self.values.posed:
            self.setFrame(0)
            self.bc.setStandardMode()

        if posed is False and self.values.doCorrections:
            self.bc.setStandardMode()

        self.view.setYRotation(0.0)
        self.view.Tweak()
        self.glob.midColumn.renderView(False)
        self.glob.midColumn.animViews(False)

    def setFrame(self, value):
        if self.bvh is None:    # should not be possible
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

    def changeShowAfter(self, param):
        self.values.showafter = param

    def changeRenderMode(self, param):
        self.values.rendermode = param

    def changePosed(self, param):
        self.setUnsubdivided()
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
        self.viewBox.setCurrentIndex(self.values.rendermode)
        self.width.setText(str(self.values.imwidth))
        self.height.setText(str(self.values.imheight))
        self.showAfter.setChecked(self.values.showafter)

        self.corrAnim.blockSignals(True)    # avoid these buttons to change
        self.corrAnim.setChecked(self.values.doCorrections)
        self.corrAnim.blockSignals(False)

        posed, frames = self.bc.hasPoses()
        if posed:
            self.corrAnim.setEnabled((len(self.bc.posecorrections) > 0 or len(self.bc.faceposes) > 0) and self.values.posed)

            self.posedButton.blockSignals(True)
            self.posedButton.setChecked(self.values.posed)
            self.posedButton.blockSignals(False)

            if frames > 1:
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

    def changeCorr(self):
        self.setUnsubdivided()
        self.values.doCorrections = self.corrAnim.isChecked()
        poseskel = self.bc.pose_skeleton
        if self.values.doCorrections:
            poseskel.useOffset(True)

            if self.bvh:
                self.bvh.modCorrections()
            else:
                self.bc.setPoseMode()
                self.correctionsOnly()
        else:
            poseskel.useOffset(False)
            if self.bvh:
                self.bvh.identFinal()
            else:
                self.bc.setStandardMode()
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
            self.subdiv = True
            self.glob.parallel = None

    def parSubdivide(self):
        if self.subdiv is True:
            return
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
        if self.subdiv is False:
            return

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
        self.subdiv = False
        self.glob.openGLBlock = False
        self.view.setYRotation(float(self.values.angle))
        self.view.Tweak()

    def toggleSmooth(self):
        b = self.sender()
        subdiv = b.isChecked()
        if subdiv:
            self.parSubdivide()
        else:
            self.unSubdivide()

    def render(self):
        width  = int(self.width.text())
        height = int(self.height.text())

        if self.values.rendermode == 0:
            # 2. Save the current window size
            orig_size = self.view.size()
            try:
                # 2. Force the 3D view to the target shape
                # This is the "magic" that fixes the perspective stretching
                self.view.resize(width, height)
                self.view.Tweak()
                self.view.update()

                # 3. Capture the now-perfectly-shaped pixels
                pixmap = self.view.grab()
                self.image = pixmap.toImage()

            except Exception as e:
                self.env.logLine(2, f"Render Error: {e}")

            finally:
                # 4. ALWAYS restore the window size so the UI isn't broken
                self.view.resize(orig_size)
                self.view.Tweak()
        else:
            pix = OffScreenRender(self.glob, self.view, self.values.rendermode == 2)
            pix.getBuffer(width, height)
            self.image = pix.bufferToImage()
            pix.releaseBuffer()

        self.setButtons()
        if self.values.showafter:
            self.viewImage()

    def viewImage(self):
        self.lastimgview = ImageBox(self.parent, "Viewer", self.image, color=self.view.light.glclearcolor)

    def saveImage(self):
        directory = os.path.join(self.env.stdUserPath(), "render")
        freq = MHFileRequest(self.glob, "Image (PNG)", "image files (*.png)", directory, save=".png")
        filename = freq.request()
        if filename is not None:
            self.image.save(filename, "PNG", -1)
            QMessageBox.information(self.parent.central_widget, "Done!", "Image saved as " + filename)


