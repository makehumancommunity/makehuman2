"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck, Elvaerwyn_MH2 2026 V1.2

    * class TextureBox
    * class MHMaterialEditor
"""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QCheckBox, QSizePolicy, QScrollArea, 
        QLineEdit, QMessageBox, QRadioButton
        )
from PySide6.QtGui import QPixmap, QColor
from obj3d.object3d import object3d
from gui.common import MHTagEdit, IconButton, MHFileRequest,  ErrorBox
from gui.slider import SimpleSlider, ColorButton

class TextureBox(QGroupBox):
    """
    texture box with max of 2 sliders and an alternative color
    sliders work different without texture-map, alternative color only visual when no texture

    :param parent: Material-Editor
    :param obj: object
    :param str name: Name of the Box like "Base Color"
    :param str attrib: Name of the textureMap
    :param slider1: list of slider texts for slider 1
    :param slider2: list of slider texts for slider 2
    :param float s1factor: factor for slider 1 (usually 100)
    :param float s2factor: factor for slider 2 (usually 100)
    :param str altcolor: Name of the alternative color if no texture (like diffuseColor)
    """
    def __init__(self, parent, obj, name, attrib, slider1=None, slider2=None, s1factor=100.0, s2factor=100.0, altcolor=None):
        super().__init__(name)
        self.parent = parent
        self.securityCheck = parent.checkLitsphere
        self.updateDep = parent.updateDependencies
        self.emptyIcon = parent.emptyIcon
        self.glob = parent.glob
        self.object = obj
        self.attrib = attrib
        self.material = obj.material
        self.altcolor = altcolor
        self.slider1 = slider1
        self.slider2 = slider2
        self.slider1_factor = s1factor
        self.slider2_factor = s2factor
        self.setObjectName("subwindow")
        self.label = QLabel()
        self.sweep = IconButton(0, parent.sweep, "No texture", self.emptyMap, 32)
        self.map   = IconButton(0, parent.emptyIcon, name + " texture", self.setMap, 128)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.map)
        vlayout = QVBoxLayout()
        h2layout = QHBoxLayout()
        h2layout.addWidget(self.label)
        h2layout.addWidget(self.sweep)
        vlayout.addLayout(h2layout)

        if slider1:
            self.slider1attr = slider1[0]
            self.intensity1 = SimpleSlider("", 0, 100, self.slider1changed, minwidth=250)
            self.slider1text()
            vlayout.addWidget(self.intensity1)
            self.slider1set()
        else:
            self.intensity1 = None

        if slider2:
            self.slider2attr = slider2[0]
            self.intensity2 = SimpleSlider("", 0, 100, self.slider2changed, minwidth=250)
            self.slider2text()
            vlayout.addWidget(self.intensity2)
            self.slider2set()
        else:
            self.intensity2 = None

        if self.altcolor:
            self.colorbutton = ColorButton(self.glob, "Color: ", self.altColorChanged)
            self.setAltColor()
            vlayout.addWidget(self.colorbutton)
            self.colorbutton.setVisible(not hasattr(self.material, self.attrib))

        hlayout.addLayout(vlayout)
        self.setLayout(hlayout)

    def shortenName(self, path):
        if len(path) > 38:
            return "... " + path[len(path)-35:]
        return path

    def setAltColor(self):
        if hasattr(self.material, self.altcolor):
            color = getattr(self.material, self.altcolor)
        else:
            color = [1.0, 1.0, 1.0]
        self.colorbutton.setColorValue(QColor.fromRgbF(*color)) # list to positional args


    def altColorChanged(self, color):
        if hasattr(self.material, self.altcolor):
            newcol = list(color.getRgbF())[:3]
            setattr(self.material, self.altcolor, newcol)
            self.parent.Tweak(False)

    def updateMap(self, obj, redisplay=True):
        """
        needs to accept new object
        """
        self.object = obj
        self.material = obj.material
        if self.altcolor:
            self.colorbutton.setVisible(not hasattr(self.material, self.attrib))
            self.setAltColor()

        if hasattr(self.material, self.attrib):
            self.updateDep(self.attrib, True)
            item = getattr(self.material, self.attrib)
            self.map.newIcon(item)
            self.label.setText(self.shortenName(item))
        else:
            self.updateDep(self.attrib, False)
            self.map.newIcon(self.emptyIcon)
            self.label.setText("None")

        self.slider1text()
        self.slider2text()
        self.slider1set()
        self.slider2set()
        if redisplay:
            self.parent.Tweak(False)

    def emptyMap(self):
        if hasattr(self.material, self.attrib):
            delattr(self.material, self.attrib)

            # delete old texture
            #
            self.material.freeTexture(self.attrib)
            self.securityCheck()
            self.updateMap(self.object)

    def setMap(self):
        directory = self.material.mhmatdir
        freq = MHFileRequest(self.glob, "Texture (PNG/JPG)", "Images (*.png *.jpg *.jpeg)", directory)
        filename = freq.request()
        if filename is not None:

            # delete old texture
            #
            if hasattr(self.material, self.attrib):
                self.updateDep(self.attrib, False)          # needed to delete old base-color
                self.material.freeTexture(self.attrib)

            # add new one
            #
            setattr(self.material, self.attrib, filename)
            self.updateMap(self.object)

    def slider1text(self):
        if self.slider1 is not None:
            if hasattr(self.material, self.attrib):
                self.intensity1.setLabelText(self.slider1[1])
            else:
                self.intensity1.setLabelText(self.slider1[2])

    def slider2text(self):
        if self.slider2 is not None:
            if hasattr(self.material, self.attrib):
                self.intensity2.setLabelText(self.slider2[1])
            else:
                self.intensity2.setLabelText(self.slider2[2])

    def slider1set(self):
        if self.slider1 is not None and hasattr(self.material, self.slider1attr):
            item = getattr(self.material, self.slider1attr)
            self.intensity1.setSliderValue(item * self.slider1_factor)

    def slider2set(self):
        if self.slider2 is not None and hasattr(self.material, self.slider2attr):
            item = getattr(self.material, self.slider2attr)
            self.intensity2.setSliderValue(item * self.slider2_factor)

    def slider1changed(self, value):
        if hasattr(self.material, self.slider1attr):
            setattr(self.material, self.slider1attr, value / self.slider1_factor)
            self.parent.Tweak(False)

    def slider2changed(self, value):
        if hasattr(self.material, self.slider2attr):
            setattr(self.material, self.slider2attr, value / self.slider2_factor)
            self.parent.Tweak(False)


class MHMaterialEditor(QWidget):
    """
    MaterialEditor
    (proxy changes basemesh & proxy, openGL update for both)

    :param parent: parent Window to get environment from
    :param obj: the object what the material is made for
    """
    def __init__(self, parent, obj):
        super().__init__()
        self.parent = parent
        self.env = parent.env
        self.glob = parent.glob
        self.object = obj
        self.material = obj.material
        self.tempcolmethod = 1      # preset coloration method
        self.TBoxes = []

        self.shadertypes = [ 
                [None, "Phong", "phong", "combination of ambient, diffuse and specular reflection"],
                [None, "Litpshere", "litsphere", "IBL (image based lighting), MatCap"],
                [None, "PBR", "pbr", "physical based rendering (openGL)"],
                [None, "Toon", "toon", "a silhouette based shader (openGL)"]
        ]

        self.colorationmethods = [
                [None, "hue-to-color", "keep saturation and value of brightness, change hue to given color"],
                [None, "desaturate + color multiply", "desaturate image and multiply this by given color"],
        ]

        self.factors = [
                ["metallicFactor", "[PBR] Metal map strength: ",     "[PBR] Metallic Factor: "],
                ["roughnessFactor", "[PBR] Roughness map strength: ", "[PBR] Roughness Factor: "],
                ["aomapIntensity", "[PBR/Phong] AO map strength: ",        "[PBR/Phong] Ambient Occlusion: "],
                ["normalmapIntensity", "[PBR/Phong] Normalmap strength: ",  "--- no effect ---: "],
                ["emissiveFactor", "Emission map strength: ",  "Emission value strength: "],
                ["sp_AdditiveShading", "Litsphere additive shading: ",  "--- no effect ---: "]
        ]

        self.glass_factors = [
                ["transmission", "[PBR] Glass Transmission: "],
                ["ior", "[PBR] Index of Refraction (IOR): "],
                ["glassRoughness", "[PBR] Glass Frosted Blur: "]
        ]
        self.setWindowTitle("Material Editor")
        self.resize(600, 750)

        self.emptyIcon = os.path.join(self.env.path_sysdata, "icons", "noidea.png")
        self.sweep = os.path.join(self.env.path_sysdata, "icons", "sweep.png")
        colorwheelicon = os.path.join(self.env.path_sysicon, "colorwheel.png")
        self.colorwheel = IconButton(0, colorwheelicon, "colorate", self.colorate, checkable=True)

        layout = QVBoxLayout()
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("Material name:"))
        self.namebox = QLineEdit(self.material.name)
        hlayout.addWidget(self.namebox)
        layout.addLayout(hlayout)

        self.loadMatButton = QPushButton("Import / Choose .mhmat File...")
        self.loadMatButton.setObjectName("colnum1")
        self.loadMatButton.clicked.connect(self.chooseMaterialFile)
        layout.addWidget(self.loadMatButton)

        scrollContainer = QWidget()
        slayout = QVBoxLayout()

        gb = QGroupBox("OpenGL shader-specific")
        gb.setObjectName("subwindow")
        hlayout = QHBoxLayout()

        # shader buttons
        #
        vlayout = QVBoxLayout()
        #        ["Phong", "phong", "combination of ambient, diffuse and specular reflection", None],
        for shader in self.shadertypes:
            shader[0] = QRadioButton(shader[1])
            shader[0].setToolTip(shader[3])
            shader[0].toggled.connect(self.updateShaderType)
            vlayout.addWidget(shader[0])

        hlayout.addLayout(vlayout)

        vlayout = QVBoxLayout()
        self.transparent = QCheckBox("Material is transparent")
        self.transparent.stateChanged.connect(self.transparentchanged)
        self.backfacecull = QCheckBox("Backface culling")
        self.backfacecull.stateChanged.connect(self.backfacecullchanged)
        self.alphacov = QCheckBox("Alpha to coverage")
        self.alphacov.stateChanged.connect(self.alphacovchanged)
        vlayout.addWidget(self.transparent)
        vlayout.addWidget(self.backfacecull)
        vlayout.addWidget(self.alphacov)
        hlayout.addLayout(vlayout)
        gb.setLayout(hlayout)
        slayout.addWidget(gb)

        # define box coloration

        gb = QGroupBox("Base texture coloration")
        gb.setObjectName("subwindow")
        hlayout = QHBoxLayout()

        self.colorationButton = ColorButton(self.glob, "Color: ", self.colorationChanged)
        hlayout.addWidget(self.colorationButton)

        vlayout = QVBoxLayout()
        for colmeth in self.colorationmethods:
            colmeth[0] = QRadioButton(colmeth[1])
            colmeth[0].setToolTip(colmeth[2])
            colmeth[0].toggled.connect(self.updateColMeth)
            vlayout.addWidget(colmeth[0])
        hlayout.addLayout(vlayout)

        hlayout.addWidget(self.colorwheel)
        gb.setLayout(hlayout)

        t = TextureBox (self, self.object, "Base color / base texture", "diffuseTexture", altcolor="diffuseColor")
        slayout.addWidget(t)
        self.TBoxes.append(t)

        slayout.addWidget(gb) # add coloration

        t = TextureBox (self, self.object, "Normalmap", "normalmapTexture", self.factors[3])
        slayout.addWidget(t)
        self.TBoxes.append(t)

        t = TextureBox (self, self.object, "Ambient occlusion", "aomapTexture", self.factors[2], s1factor=50.0, altcolor="ambientColor")
        slayout.addWidget(t)
        self.TBoxes.append(t)

        t = TextureBox (self, self.object, "Metallic/Roughness", "metallicRoughnessTexture", self.factors[1], self.factors[0])
        slayout.addWidget(t)
        self.TBoxes.append(t)

        t = TextureBox (self, self.object, "Emissive", "emissiveTexture", self.factors[4], altcolor="emissiveColor")
        slayout.addWidget(t)
        self.TBoxes.append(t)

        t = TextureBox (self, self.object, "Litsphere/Matcap", "sp_litsphereTexture", self.factors[5])
        slayout.addWidget(t)
        self.TBoxes.append(t)

        # glass shader
        #
        self.glassGroup = QGroupBox("PBR Glass & Refraction Parameters")
        self.glassGroup.setObjectName("subwindow")
        glassLayout = QVBoxLayout()

        # glass tint bubble
        color_layout = QHBoxLayout()
        glass_color_label = QLabel("Glass Tint Color: ")
        self.glassColorButton = ColorButton(self.glob, "Tint: ", self.glassColorChanged)
        color_layout.addWidget(glass_color_label)
        color_layout.addWidget(self.glassColorButton)
        color_layout.addStretch()
        glassLayout.addLayout(color_layout)

        # create transmission, ior and frosted blurr roughness
        #
        self.transmissionSlider = SimpleSlider(self.glass_factors[0][1], 0, 100, self.transmissionChanged, minwidth=250)
        glassLayout.addWidget(self.transmissionSlider)

        self.iorSlider = SimpleSlider(self.glass_factors[1][1], 100, 250, self.iorChanged, minwidth=250)
        glassLayout.addWidget(self.iorSlider)

        self.glassRoughnessSlider = SimpleSlider(self.glass_factors[2][1], 0, 100, self.glassRoughnessChanged, minwidth=250)
        glassLayout.addWidget(self.glassRoughnessSlider)

        self.glassGroup.setLayout(glassLayout)
        slayout.addWidget(self.glassGroup)

        # specularColor (.obj exporter)
        self.specGroup = QGroupBox("specular color (used for obj exports)")
        self.specGroup.setObjectName("subwindow")
        spec_layout = QHBoxLayout()
        spec_color_label = QLabel("Specular Color: ")
        self.specColorButton = ColorButton(self.glob, "Color: ", self.specColorChanged)
        spec_layout.addWidget(spec_color_label)
        spec_layout.addWidget(self.specColorButton)
        self.specGroup.setLayout(spec_layout)
        slayout.addWidget(self.specGroup)

        scrollContainer.setLayout(slayout)
        scroll = QScrollArea()
        scroll.setWidget(scrollContainer)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        hlayout = QHBoxLayout()
        usebutton = QPushButton("Use")
        usebutton.clicked.connect(self.use_call)
        savebutton = QPushButton("Save")
        savebutton.clicked.connect(self.save_call)
        hlayout.addWidget(usebutton)
        hlayout.addWidget(savebutton)
        self.updateWidgets(obj)
        layout.addLayout(hlayout)
        self.setLayout(layout)

    def Tweak(self, update=False):
        self.object.openGL.setMaterial(self.material, update)
        if self.object.type == "base":
            proxy = self.glob.baseClass.proxy
            if proxy:
                proxy.openGL.setMaterial(proxy.material, update)
        self.glob.openGLWindow.Tweak()

    def setShader(self):
        """
        activate shaderbuttons
        """
        for shader in self.shadertypes:
            shader[0].setChecked(self.material.shader == shader[2])

    def setColMeth(self):
        """
        activate coloration method
        """
        if self.material.colorationMethod > 0:
            self.colorwheel.setChecked(True)
            self.tempcolmethod = self.material.colorationMethod
        else:
            self.colorwheel.setChecked(False)
            self.tempcolmethod = 1
        for m in range(0,len(self.colorationmethods)):
            self.colorationmethods[m][0].setChecked(self.tempcolmethod == (m+1))

    def updateWidgets(self, obj):
        self.object = obj
        self.material = obj.material
        self.namebox.setText(self.material.name)

        self.setShader()

        self.transparent.setChecked(self.material.transparent)
        self.backfacecull.setChecked(self.material.backfaceCull)
        self.alphacov.setChecked(self.material.alphaToCoverage)

        self.transmissionSlider.setSliderValue(self.material.transmission * 100.0)
        self.iorSlider.setSliderValue(self.material.ior * 100.0)
        self.glassRoughnessSlider.setSliderValue(self.material.glassRoughness * 100.0)

        # Pull color floats out of memory data structures and update button bubble UI
        self.glassColorButton.setColorValue(QColor.fromRgbF(*self.material.glassColor))

        # Control sub-panel visibility when moving across different shader profiles
        self.glassGroup.setVisible(self.material.shader == "pbr")

        self.specColorButton.setColorValue(QColor.fromRgbF(*self.material.specularColor))

        for t in self.TBoxes:
            t.updateMap(self.object, False)

        if hasattr(self.material, "colorationColor"):
            color = getattr(self.material, "colorationColor")
        else:
            color = [1.0, 1.0, 1.0]
        self.colorationButton.setColorValue(QColor.fromRgbF(*color)) # list to positional args
        self.setColMeth()
        self.Tweak()

    def updateDependencies(self, texmap, used):
        if texmap == "diffuseTexture":
            self.colorwheel.setEnabled(used)
            self.colorwheel.setToolTip("Colorate base texture" if used else "Select base texture before")
            self.colorationButton.setVisible(used)
            for radbut in self.colorationmethods:
                radbut[0].setVisible(used)

    def updateShaderType(self, _):
        m = self.sender()
        if m.isChecked():
            for shader in self.shadertypes:
                if m is shader[0]:
                    self.material.shader =  shader[2]
                    self.glassGroup.setVisible(shader[2] == "pbr")      # glass only for PBR
        if self.checkLitsphere() is False:
            self.updateWidgets(self.object)
        else:
            self.Tweak()

    def backfacecullchanged(self):
        self.material.backfaceCull = self.backfacecull.isChecked()
        self.Tweak()

    def transparentchanged(self):
        self.material.transparent = self.transparent.isChecked()
        self.Tweak()

    def alphacovchanged(self):
        self.material.alphaToCoverage = self.alphacov.isChecked()
        self.Tweak()

    def checkLitsphere(self):
        if self.material.shader == "litsphere" and not hasattr(self.material, "sp_litsphereTexture"):
            self.material.shader = "phong"
            self.setShader()
            ErrorBox(self, "Litpshere cannot be used without a litsphere texture.")
            return False
        return True

    def colorationChanged(self, color):
        if hasattr(self.material, "colorationColor"):
            newcol = list(color.getRgbF())[:3]
            setattr(self.material, "colorationColor", newcol)
            self.Tweak()

    def getColMeth(self):
        for i,colmeth in enumerate(self.colorationmethods):
            if colmeth[0].isChecked():
                return i+1
        return 0

    def updateColMeth(self, _):
        m = self.sender()
        oldmethod = self.tempcolmethod
        self.tempcolmethod = self.getColMeth()

        if oldmethod != self.tempcolmethod and oldmethod != 0:
            self.material.colorationMethod = 0
            self.material.colorate()
            self.colorwheel.setChecked(False)   # if change, set it back
            self.Tweak()

    # glass callbacks
    def transmissionChanged(self, value):
        self.material.transmission = value / 100.0
        self.Tweak(False)

    def iorChanged(self, value):
        self.material.ior = value / 100.0
        self.Tweak(False)

    def glassRoughnessChanged(self, value):
        self.material.glassRoughness = value / 100.0
        self.Tweak(False)

    def glassColorChanged(self, color):
        self.material.glassColor = list(color.getRgbF())[:3]
        self.Tweak(False)

    def specColorChanged(self, color):
        self.material.specularColor = list(color.getRgbF())[:3]
        self.Tweak(False)

    # coloration
    def colorate(self):
        if self.colorwheel.isChecked():
            method = self.getColMeth()
            if method > 0:
                self.material.colorationMethod = self.tempcolmethod = method
        else:
            self.tempcolmethod = 0
            self.material.colorationMethod = 0

        self.material.colorate()
        self.Tweak()

    def chooseMaterialFile(self):
        directory = self.material.mhmatdir
        freq = MHFileRequest(self.glob, "Material (MHMAT)", "material files (*.mhmat)", directory)
        filename = freq.request()
        if filename is not None:
            # free textures
            for tbox in self.TBoxes:
                if hasattr(self.material, tbox.attrib):
                    self.material.freeTexture(tbox.attrib)

            # for all terms not contained in material file use default
            self.material.default()

            self.material.loadMatFile(filename)
            self.updateWidgets(self.object)

    def save_call(self):
        if self.checkLitsphere() is False:
            return
        directory = self.material.mhmatdir
        freq = MHFileRequest(self.glob, "Material (MHMAT)", "material files (*.mhmat)", directory, save=".mhmat")
        filename = freq.request()
        if filename is not None:
            self.material.name = self.namebox.text()
            self.material.saveMatFile(filename)
            QMessageBox.information(self.parent.central_widget, "Done!", "Material saved as " + filename)

        self.close()

    def use_call(self):
        if self.checkLitsphere() is False:
            return
        self.Tweak()
        self.close()

    def closeEvent(self, event):
        self.checkLitsphere()

