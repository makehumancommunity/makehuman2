"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MHSceneWindow
"""

from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QPushButton, QRadioButton, QGroupBox, QCheckBox, QSizePolicy,
        QListWidget, QAbstractItemView, QGridLayout, QScrollArea
        )

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from gui.slider import SimpleSlider, ColorButton
from gui.mapslider import MapXYCombo
import numpy as np

class MHSceneWindow(QWidget):
    """
    Message window to display scene setup

    :param parent: parent object of type class OpenGLView (from QOpenGLWidget)
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.env = parent.env
        self.glob = parent.glob
        self.view = self.glob.openGLWindow 
        self.scene = self.view.scene
        self.light = self.view.light
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        y1 = self.light.min_coords[1]
        y2 = self.light.max_coords[1]
        self.setWindowTitle("Scene and Lighting")
        self._volume = 100.0 / (np.array(self.light.max_coords) - np.array(self.light.min_coords))

        self._lastusedskybox = self.light.skyboxname
        self._lastselectedskybox = self.light.skyboxname
        self._lastselectedfloor = self.scene.floortexname
        self._lastfloorsize = self.scene.floorsize.copy()

        # will keep the light widgets
        #
        self.lightsetup = [
                [None, None, None, None, None, None],
                [None, None, None, None, None, None],
                [None, None, None, None, None, None]
        ]

        layout = QVBoxLayout()
        layout.setSpacing(1)

        # main layout, gridlayout + buttons
        #
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scrollContainer = QWidget()

        # Gridlayout, 1st row of 3 columns: Ambient/Phong, Background, Floor
        # light-sources as row 2-x
        #
        glayout = QGridLayout()
        glayout.setSpacing(1)

        l = QGroupBox("Ambient Light")
        l.setObjectName("subwindow")

        vlayout = QVBoxLayout()
        vlayout.setSpacing(1)
        self.ambLuminance = SimpleSlider("Luminance: ", 0, 100, self.ambChanged)
        vlayout.addWidget(self.ambLuminance )

        self.ambColor = ColorButton(self.glob, "Color: ", self.ambColorChanged, horizontal=True)
        vlayout.addWidget(self.ambColor)
        l.setLayout(vlayout)

        glayout.addWidget(l, 0, 0, 1, 1)

        # 2nd row phong specific parameter
        #
        l = QGroupBox("Phong specific")
        l.setObjectName("subwindow")

        vlayout = QVBoxLayout()
        vlayout.setSpacing(1)
        self.specFocus = SimpleSlider("Specular light, Focus: ", 1, 64, self.specFocChanged)
        vlayout.addWidget(self.specFocus )

        vlayout.addStretch()
        self.phong = QRadioButton("Phong")
        self.blinn = QRadioButton("Blinn")
        self.phong.toggled.connect(self.setMethod)
        self.blinn.toggled.connect(self.setMethod)
        vlayout.addWidget(self.phong)
        vlayout.addWidget(self.blinn)
        l.setLayout(vlayout)

        glayout.addWidget(l, 1, 0, 1, 1)

        # 2nd column, background
        #
        l = QGroupBox("Background")
        l.setObjectName("subwindow")
        vlayout = QVBoxLayout()
        vlayout.setSpacing(1)

        self.clearColor = ColorButton(self.glob, "Background color: ", self.clearColorChanged)
        vlayout.addWidget(self.clearColor)

        self.skybox = QPushButton("Skybox")
        self.skybox.setCheckable(True)
        self.skybox.clicked.connect(self.setSkybox)
        vlayout.addWidget(self.skybox)

        self.skyboxlist = self.env.getDataDirList(None, "shaders", "skybox")
        self.skyboxSelect = QListWidget()
        self.skyboxSelect.setFixedSize(240, 100)
        self.skyboxSelect.addItems(self.skyboxlist.keys())
        self.skyboxSelect.setSelectionMode(QAbstractItemView.SingleSelection)
        self.getSkyBoxName()

        vlayout.addWidget(self.skyboxSelect)
        b = QPushButton("Select")
        b.clicked.connect(self.changeSkyboxName)
        vlayout.addWidget(b)

        l.setLayout(vlayout)
        glayout.addWidget(l, 0, 1, 2, 1)


        # 3d column, list of jpg and png for floor pattern
        #
        l = QGroupBox("Floor")
        l.setObjectName("subwindow")

        vlayout = QVBoxLayout()
        vlayout.setSpacing(1)
        vlayout.addWidget(QLabel("Floor geometry:"))

        self.floorSize = SimpleSlider("Floor Size: ", 5, 100, self.floorSizeChanged)
        vlayout.addWidget(self.floorSize )

        self.floorThickness = SimpleSlider("Floor Thickness: ", 1, 100, self.floorThicknessChanged)
        vlayout.addWidget(self.floorThickness )

        vlayout.addWidget(QLabel("Floor texture:"))
        self.floorlist = self.env.getDataFileList("png", "shaders", "floor")
        self.floorlist.update(self.env.getDataFileList("jpg", "shaders", "floor"))
        self.floorSelect = QListWidget()
        self.floorSelect.addItems(self.floorlist.keys())
        self.floorSelect.setSelectionMode(QAbstractItemView.SingleSelection)
        self.getFloorName()
        vlayout.addWidget(self.floorSelect)

        b = QPushButton("Select")
        b.clicked.connect(self.changeFloorName)
        vlayout.addWidget(b)

        l.setLayout(vlayout)
        glayout.addWidget(l, 0, 2, 2, 1)

        # lights in grid layout from row 2 to x, all columns
        #
        for l, widget in enumerate(self.lightsetup):
            lg = QGroupBox("Light Source " + str(l))
            lg.setObjectName("subwindow")
            hlayout = QHBoxLayout()
            hlayout.setSpacing(1)
            vlayout = QVBoxLayout()
            vlayout.setSpacing(1)
            widget[0] = SimpleSlider("Luminance: ", 0, 100, self.lChanged, ident=l)
            vlayout.addWidget(widget[0])

            widget[1] = ColorButton(self.glob, "Color: ", self.lColorChanged, horizontal=True, ident=l)
            vlayout.addWidget(widget[1])
            hlayout.addLayout(vlayout)

            widget[4] = QRadioButton("Directional Light")
            widget[4].toggled.connect(self.lTypeChanged)
            vlayout.addWidget(widget[4])
            widget[5] = QRadioButton("Point Light")
            widget[5].toggled.connect(self.lTypeChanged)
            vlayout.addWidget(widget[5])

            widget[2] = MapXYCombo([0.5,0.5], self.lpos, displayfunc=self.xzdisplay, drawcenter=True, ident=l)
            hlayout.addWidget(widget[2])

            widget[3] = SimpleSlider("Height: ", y1, y2, self.lposh, vertical=True, ident=l)
            hlayout.addWidget(widget[3])

            lg.setLayout(hlayout)
            glayout.addWidget(lg, 2+l, 0, 1, 3)

        scrollContainer.setLayout(glayout)
        scrollArea.setWidget(scrollContainer)
        layout.addWidget(scrollArea)

        hlayout = QHBoxLayout()
        hlayout.setSpacing(1)
        button1 = QPushButton("Cancel")
        button1.clicked.connect(self.cancel_call)
        button2 = QPushButton("Default")
        button2.clicked.connect(self.default_call)
        button3 = QPushButton("Reset")
        button3.clicked.connect(self.reset_call)
        button4 = QPushButton("Use")
        button4.clicked.connect(self.use_call)
        hlayout.addWidget(button1)
        hlayout.addWidget(button2)
        hlayout.addWidget(button3)
        hlayout.addWidget(button4)
        layout.addLayout(hlayout)
        self.setLayout(layout)

        # Set a reasonable maximum height based on available screen geometry
        # Get available screen height and limit window to 90% of it
        screen_geometry = self.glob.app.getScreensize()
        max_height = int(screen_geometry[1] * 0.9)
        self.setMaximumHeight(max_height)

        self.getValues()

    def xzdisplay(self, x,y ):
        x = (x - 0.5 ) * 100 / self._volume[0]
        y = (y - 0.5 ) * 100 / self._volume[2]
        return (f"Position:\nX: {x:.2f}\nZ: {y:.2f}")

    def vec4ToCol(self, vec4):
        color = QColor.fromRgbF(vec4.x(), vec4.y(), vec4.z())
        return(color)

    def changeSkybox(self, name, oldname):
        if name != oldname:
            self.light.skyboxname = name
            self._lastselectedskybox = name
            s = self.light.skybox 
            self.light.skybox = False
            self.view.skybox.delete()
            self.view.skybox.create(name)
            self.light.skybox = s
            self.view.Tweak()

    def changeFloor(self, name, oldname):
        if name != oldname:
            self.scene.modFloorTexture(name)
            self._lastselectedfloor = name
            self.view.Tweak()

    def floorSizeChanged(self, value):
        self.scene.setFloorSize(value)

    def floorThicknessChanged(self, value):
        self.scene.setFloorSize(0.0,  value / 10)

    def changeSkyboxName(self):
        sel = self.skyboxSelect.selectedItems()
        if len(sel) > 0:
            self.changeSkybox(sel[0].text(), self._lastselectedskybox)

    def changeFloorName(self):
        sel = self.floorSelect.selectedItems()
        if len(sel) > 0:
            self.changeFloor(sel[0].text(), self._lastselectedfloor)

    def getSkyBox(self):
        if self.light.skybox:
            self.skybox.setChecked(True)
        else:
            self.skybox.setChecked(False)

    def getSkyBoxName(self):
        items = self.skyboxSelect.findItems(self.light.skyboxname, Qt.MatchExactly)
        if len(items) > 0:
            self.skyboxSelect.setCurrentItem(items[0])

    def getFloorName(self):
        items = self.floorSelect.findItems(self._lastselectedfloor, Qt.MatchExactly)
        if len(items) > 0:
            self.floorSelect.setCurrentItem(items[0])

    def getValues(self):
        if self.light.blinn:
            self.blinn.setChecked(True)
        else:
            self.phong.setChecked(True)

        self.getSkyBox()
        self.getSkyBoxName()
        self.floorSize.setSliderValue(self.scene.floorsize[0])
        self.floorThickness.setSliderValue(self.scene.floorsize[1] * 10.0)

        self.ambLuminance.setSliderValue(self.light.ambientLight.w() * 100)
        self.specFocus.setSliderValue(self.light.lightWeight.y())
        self.clearColor.setColorValue(self.vec4ToCol(self.light.glclearcolor))
        lights = self.light.lights
        self.ambColor.setColorValue(self.vec4ToCol(self.light.ambientLight))

        for l, widget in enumerate(self.lightsetup):

            widget[0].setSliderValue(lights[l]["int"] * 10)
            widget[1].setColorValue(self.vec4ToCol(lights[l]["vol"]))

            # position (top, height)
            #
            widget[2].mapInput.drawValues(lights[l]["pos"].x()* self._volume[l]+ 50, lights[l]["pos"].z()* self._volume[l] + 50)
            widget[3].setSliderValue(lights[l]["pos"].y())

            t = lights[l]["type"]
            if t == 0:
                widget[4].setChecked(True)
            else:
                widget[5].setChecked(True)

    def clearColorChanged(self, color):
        self.light.setClearColor(color)
        self.view.Tweak()

    def ambChanged(self, value):
        self.light.setAmbientLuminance(value / 100.0)
        self.view.Tweak()

    def ambColorChanged(self, color):
        self.light.setAmbientColor(color)
        self.view.Tweak()

    def specFocChanged(self, value):
        self.light.setSpecularFocus(value)
        self.view.Tweak()

    def setMethod(self, value):
        if self.blinn.isChecked():
            self.light.useBlinn(True)
        else:
            self.light.useBlinn(False)
        self.view.Tweak()

    def lChanged(self, ident, value):
        self.light.setLLuminance(ident, value / 10.0)
        self.view.Tweak()

    def lColorChanged(self, ident, color):
        self.light.setLColor(ident, color)
        self.view.Tweak()

    def lTypeChanged(self):
        m = self.sender()
        if m.isChecked():
            for i, widget in enumerate(self.lightsetup):
                if widget[4] is m:
                    self.light.setType(i, 0)
                    self.view.Tweak()
                    return
                if widget[5] is m:
                    self.light.setType(i, 1)
                    self.view.Tweak()
                    return

    def lpos(self, ident):
        m = self.lightsetup[ident][2].mapInput.getValues()
        x = (m[0] - 0.5 ) * 100 / self._volume[0]
        z = (m[1] - 0.5 ) * 100 / self._volume[2]
        self.light.setLPos(ident, x, z)
        self.view.Tweak()

    def lposh(self, ident, value):
        self.light.setHPos(ident, value)
        self.view.Tweak()

    def setSkybox(self):
        self.light.useSkyBox(self.skybox.isChecked())
        self.getSkyBox()
        self.view.Tweak()

    def reset_call(self):
        self.light.fromGlobal(False)
        self.changeSkybox(self._lastusedskybox, self._lastselectedskybox)
        self.scene.setFloorSize(self._lastfloorsize[0], self._lastfloorsize[1])
        self.getValues()
        self.view.Tweak()

    def default_call(self):
        oldname = self.light.skyboxname
        self.light.fromGlobal(True)
        self.changeSkybox(self.light.skyboxname, oldname)
        self.getValues()
        self.view.Tweak()

    def use_call(self):
        self.light.toGlobal()
        self._lastusedskybox = self.light.skyboxname
        self.close()

    def cancel_call(self):
        self.reset_call()
        self.close()


