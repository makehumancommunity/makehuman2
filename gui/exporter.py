"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * ExporterValues
    * ExportLeftPanel
    * ExportRightPanel
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QMessageBox, QDialogButtonBox, QCheckBox, QComboBox
    )

from PySide6.QtCore import Qt
from gui.poseactions import AnimMode
from gui.common import DialogBox, ErrorBox, IconButton, MHFileRequest
from core.export_gltf import gltfExport
from core.export_stl import stlExport
from core.export_obj import objExport
from core.export_bvh import bvhExport
from core.blender_communication import blendCom

import os

class ExporterValues():
    """
    class to keep the values, when called again
    """
    def __init__(self, glob):
        self.export_folder = glob.env.stdUserPath("exports")
        self.texture_folder = "textures"
        self.export_type = ".glb"

        self.onground = True     # common preset
        self.scale_index = 0     # rest of the presets are for glb (1st selected icon)
        self.binmode = True
        self.imgmode = False
        self.savehiddenverts = False
        self.helper = False
        self.normals = True
        self.inpose = False
        self.animation = False

class ExportLeftPanel(QVBoxLayout):
    """
    create a form with filename (+ other features later)
    """
    def __init__(self, parent):
        self.parent = parent
        self.glob = parent.glob
        self.env = self.glob.env
        self.bc  = parent.glob.baseClass
        self.animmode = None        # will keep animation mode
        self.values = self.glob.guiPresets["Exporter"]
        etype = self.values.export_type
        super().__init__()
        self.scale_items = [
            [ 0.1, "Meter"],
            [ 1.0, "Decimeter"],
            [ 3.937, "Inch"],
            [ 10.0, "Centimeter"],
            [ 100.0, "Millimeter"]
        ]

        scaletexts = []
        for elem in self.scale_items:
            scaletexts.append(str(elem[0]) + "   " + elem[1])

        # folders
        #
        ilayout = QHBoxLayout()
        self.folderbutton = IconButton(0, os.path.join(self.env.path_sysicon, "files.png"), "Select export folder.",
                self.selectfolder, 16)
        ilayout.addWidget(self.folderbutton)
        ilayout.addWidget(QLabel("Export folder:"))
        self.addLayout(ilayout)

        self.foldername = QLabel(self.values.export_folder)
        self.addWidget(self.foldername)

        self.addWidget(QLabel("\nTexture folder (inside export folder):"))
        self.texfolder = QLineEdit(self.values.texture_folder)
        self.texfolder.setToolTip("Folder name will be converted to lowercase, certain characters replaced by '_'")

        self.texfolder.editingFinished.connect(self.newtexfolder)
        self.addWidget(self.texfolder)

        # filename
        #
        self.addWidget(QLabel("\nFilename:"))
        self.filename = QLineEdit(self.bc.name + etype)
        self.filename.editingFinished.connect(self.newfilename)
        self.addWidget(self.filename)

        self.binsave= QCheckBox("binary mode")
        self.binsave.setLayoutDirection(Qt.LeftToRight)
        self.binsave.toggled.connect(self.changeBinary)
        self.binsave.setChecked(self.values.binmode)
        self.binsave.setToolTip('Some exports offer binary and ASCII modes, binary mode is usually faster and smaller')
        self.addWidget(self.binsave)

        self.binimg= QCheckBox("pack textures into file")
        self.binimg.setLayoutDirection(Qt.LeftToRight)
        self.binimg.toggled.connect(self.changeImg)
        self.binimg.setChecked(self.values.imgmode)
        self.binimg.setToolTip('Some exports offer to embed textures into the binary file, otherwise they will be exported as extra files')
        self.addWidget(self.binimg)

        self.ground= QCheckBox("feet on ground")
        self.ground.setLayoutDirection(Qt.LeftToRight)
        self.ground.toggled.connect(self.changeGround)
        self.ground.setChecked(self.values.onground)
        self.ground.setToolTip('When characters origin is not at the ground, this option corrects the position')
        self.addWidget(self.ground)

        self.posed= QCheckBox("character posed")
        self.posed.setLayoutDirection(Qt.LeftToRight)
        self.posed.toggled.connect(self.changePosed)
        self.posed.setChecked(self.values.inpose)
        self.posed.setToolTip('Export character posed instead of default pose (set pose in animation)')
        self.addWidget(self.posed)

        self.hverts= QCheckBox("save hidden vertices")
        self.hverts.setLayoutDirection(Qt.LeftToRight)
        self.hverts.toggled.connect(self.changeHVerts)
        self.hverts.setChecked(self.values.savehiddenverts)
        self.hverts.setToolTip('Export of hidden vertices is only useful, when destination is able to edit mesh')
        self.addWidget(self.hverts)

        self.anim= QCheckBox("save animation")
        self.anim.setLayoutDirection(Qt.LeftToRight)
        self.anim.toggled.connect(self.changeAnim)
        self.anim.setChecked(self.values.animation)
        self.anim.setToolTip('Append animation to export [also includes corrections]<br>Skeleton and animation must be selected.')
        self.addWidget(self.anim)
        
        self.helperw= QCheckBox("save helper")
        self.helperw.setLayoutDirection(Qt.LeftToRight)
        self.helperw.toggled.connect(self.changeHelper)
        self.helperw.setChecked(self.values.helper)
        self.helperw.setToolTip('For special purposes the invisible helper can be exported, vertices of the body are NOT hidden in this case')
        self.addWidget(self.helperw)

        self.norm= QCheckBox("normals")
        self.norm.setLayoutDirection(Qt.LeftToRight)
        self.norm.toggled.connect(self.changeNormals)
        self.norm.setChecked(self.values.normals)
        self.norm.setToolTip('Some applications need the vertex normals to create a smoothed mesh')
        self.addWidget(self.norm)

        self.addWidget(QLabel("Scaling:"))
        self.scalebox = QComboBox()
        self.scalebox.addItems(scaletexts)
        self.scalebox.currentIndexChanged.connect(self.changeScale)
        self.scalebox.setToolTip('MakeHuman works with decimeter system, destination system usually differs')
        self.addWidget(self.scalebox)

        self.exportbutton=QPushButton("Export")
        self.exportbutton.clicked.connect(self.exportfile)
        self.addWidget(self.exportbutton)
        #
        # start with glb
        #
        self.setExportType(etype)

    def leave(self):
        if self.animmode is not None:
            self.animmode.leave()

    def setExportType(self, etype):
        common = "MakeHuman works with unit decimeter. "
        expAttrib = { ".stl":  {"tip": common + "STL files are unit less. When working with printers 1 unit equals 1 millimeter (preset scale 1:10)",
                "num": 3, "binset": True, "binmode": "both", "imgset": False, "imgmode": False, "hiddenset": True, "hiddenmode": False,
                "animset": False, "animmode": False, "poseset": True, "posemode": False,
                "helpset": False, "helpmode": False, "normset": False, "normmode": False},
            ".glb": { "tip": common + "GLB/GLTF units are usually meters",
                "num": 0, "binset": False, "binmode": True, "imgset": True, "imgmode": "both", "hiddenset": True, "hiddenmode": False,
                "animset": True, "animmode": False, "poseset": False, "posemode": False,
                "helpset": False, "helpmode": False, "normset": False, "normmode": True},
            ".mh2b": { "tip": common + "Blender units are usually meters",
                "num": 0, "binset": False, "binmode": True, "imgset": False, "imgmode": False, "hiddenset": True, "hiddenmode": False,
                "animset": True, "animmode": False, "poseset": False, "posemode": False,
                "helpset": False, "helpmode": False, "normset": False, "normmode": False},
            ".obj": { "tip": common + "Wavefront units are usually meters",
                "num": 0, "binset": False, "binmode": False, "imgset": False, "imgmode": False, "hiddenset": True, "hiddenmode": False,
                "animset": False, "animmode": False, "poseset": False, "posemode": False,
                "helpset": True, "helpmode": False, "normset": True, "normmode": False},
            ".bvh": { "tip": common + "BVH units are usually the same as the internal scale",
                "num": 0, "binset": False, "binmode": False,  "imgset": False, "imgmode": False, "hiddenset": False, "hiddenmode": False,
                "animset": False, "animmode": True, "poseset": False, "posemode": False,
                "helpset": False, "helpmode": False, "normset": False, "normmode": False}
            }


        # set options according to type, only change it, if mode is changed
        #
        attr = expAttrib[etype]

        if self.values.export_type != etype:
            self.values.export_type = etype
            self.values.scale_index = attr["num"]
            if attr["binmode"] != "both":
                self.values.binmode = attr["binmode"]
            if attr["imgmode"] != "both":
                self.values.imgmode = attr["imgmode"]
            self.values.savehiddenverts = attr["hiddenmode"]
            self.values.helper = attr["helpmode"]
            self.values.normals = attr["normmode"]
            self.values.inpose = attr["posemode"]
            self.values.animation = attr["animmode"]

        self.newfilename()
        self.newfoldername()

        self.binsave.setChecked(self.values.binmode)
        self.binsave.setEnabled(attr["binset"])

        self.binimg.setChecked(self.values.imgmode)
        self.binimg.setEnabled(attr["imgset"])
        #
        self.hverts.setChecked(self.values.savehiddenverts)
        self.hverts.setEnabled(attr["hiddenset"])

        self.helperw.setChecked(self.values.helper)
        self.helperw.setEnabled(attr["helpset"])

        self.norm.setChecked(self.values.normals)
        self.norm.setEnabled(attr["normset"])

        if self.bc.bvh is None or self.bc.skeleton is None:
            self.anim.setChecked(False)
            self.anim.setEnabled(False)
            self.values.animation = False
        else:
            self.anim.setChecked(self.values.animation)
            self.anim.setEnabled(attr["animset"])

        self.posed.setChecked(self.values.inpose)
        self.posed.setEnabled(attr["poseset"])

        self.scalebox.setCurrentIndex(self.values.scale_index)
        self.scalebox.setToolTip(attr["tip"])

    def changeScale(self, param):
        self.values.scale_index = param

    def changeBinary(self, param):
        self.values.binmode = param

    def changeImg(self, param):
        self.values.imgmode = param

    def changeHVerts(self, param):
        self.values.savehiddenverts = param

    def changeGround(self, param):
        self.values.onground = param

    def changePosed(self, param):
        if self.animmode is None:
            self.animmode = AnimMode(self.glob)
        else:
            self.animmode.leave()
            self.animmode = None
        self.values.inpose = param

    def changeHelper(self, param):
        self.values.helper = param

    def changeNormals(self, param):
        self.values.normals = param

    def changeAnim(self, param):
        self.values.animation = param

    def selectfolder(self):
        folder = self.foldername.text()
        freq = MHFileRequest(self.glob, "Select export folder", None, folder, save=".")
        name = freq.request()
        if name is not None:
            self.foldername.setText(name)
            self.values.export_folder = name

    def newfoldername(self):
        """
        not empty, but can be changed
        """
        folder = self.foldername.text()
        if folder is None or folder == "":
            folder = self.env.stdUserPath("exports")
            self.foldername.setText(folder)
        self.values.export_folder = folder

    def newfilename(self):
        """
        not empty, always ends with export type
        """
        text = self.filename.text()
        if not text.endswith(self.values.export_type):
            text = os.path.splitext(text)[0]
            self.filename.setText(text + self.values.export_type)

    def newtexfolder(self):
        """
        corrections if sth. does not work
        """
        folder = self.texfolder.text()
        if folder is None or folder == "":
            folder = "textures"
        else:
            folder = self.env.normalizeName(folder)
        self.texfolder.setText(folder)
        self.values.texture_folder = folder

    def exportfile(self):
        """
        path calculation, save file, save icon
        """
        folder = self.foldername.text()
        texfolder = self.texfolder.text()
        path = os.path.join(folder, self.filename.text())
        
        # warn user if file exists
        #
        if os.path.isfile(path):
            dbox = DialogBox("Replace " + path + "?", QDialogButtonBox.Ok)
            confirmed = dbox.exec()
            if confirmed != 1:
                return

        current = self.scalebox.currentIndex()
        scale = self.scale_items[current][0]

        etype = self.values.export_type
        if etype == ".glb":
            gltf = gltfExport(self.glob, folder, texfolder, self.values.imgmode, self.values.savehiddenverts,
                    self.values.onground,  self.values.animation, scale)
            success = gltf.binSave(self.bc, path)

        elif etype == ".stl":
            stl = stlExport(self.glob, folder, self.values.savehiddenverts, scale)
            if self.values.binmode:
                success = stl.binSave(self.bc, path)
            else:
                success = stl.ascSave(self.bc, path)

        elif etype == ".mh2b":
            blcom = blendCom(self.glob, folder, texfolder, self.values.savehiddenverts,
                    self.values.onground, self.values.animation, scale)
            success = blcom.binSave(self.bc, path)

        elif etype == ".obj":
            obj = objExport(self.glob, folder, texfolder, self.values.savehiddenverts,
                    self.values.onground, self.values.helper, self.values.normals, scale)
            success = obj.ascSave(self.bc, path)

        elif etype == ".bvh":
            bvh = bvhExport(self.glob, self.values.onground, scale)
            success = bvh.ascSave(self.bc, path)

        else:
            self.env.logLine(1, "not yet implemented")
            return

        if success:
            QMessageBox.information(self.parent, "Done!", "Character exported as " + path)
        else:
            ErrorBox(self.parent, self.env.last_error)


class ExportRightPanel(QVBoxLayout):
    def __init__(self, parent, connector):
        super().__init__()
        self.parent = parent
        self.glob = parent.glob
        self.env = self.glob.env
        self.leftPanel = connector
        self.exportimages = [
                { "button": None, "icon": "gltf_sym.png", "tip": "export as GLTF2/GLB", "func": self.exportgltf},
                { "button": None, "icon": "stl_sym.png", "tip": "export as STL (Stereolithography)", "func": self.exportstl},
                { "button": None, "icon": "blend_sym.png", "tip": "export as MH2B (Blender)", "func": self.exportmh2b},
                { "button": None, "icon": "wavefront_sym.png", "tip": "export as OBJ (Wavefront)", "func": self.exportobj},
                { "button": None, "icon": "bvh_sym.png", "tip": "export animation/pose as BVH (BioVision Hierarchy)\nOrientation: Y forward, Z up", "func": self.exportbvh}
        ]
        for n, b in enumerate(self.exportimages):
            b["button"] = IconButton(n, os.path.join(self.env.path_sysicon, b["icon"]), b["tip"], b["func"], 130, checkable=True)
            self.addWidget(b["button"])

        self.setCheckedByName(self.leftPanel.values.export_type)
        self.addStretch()

    def setCheckedByName(self, name):
        l = [".glb", ".stl", ".mh2b", ".obj", ".bvh"]
        if name in l:
            self.setChecked(l.index(name))

    def setChecked(self, num):
        for i, elem in enumerate(self.exportimages):
            elem["button"].setChecked(i==num)

    def exportgltf(self):
        self.env.logLine(2, "export GLTF called")
        self.leftPanel.setExportType(".glb")
        self.setChecked(0)

    def exportstl(self):
        self.env.logLine(2, "export STL called")
        self.leftPanel.setExportType(".stl")
        self.setChecked(1)

    def exportmh2b(self):
        self.env.logLine(2, "export MH2B called")
        self.leftPanel.setExportType(".mh2b")
        self.setChecked(2)

    def exportobj(self):
        self.env.logLine(2, "export OBJ called")
        self.leftPanel.setExportType(".obj")
        self.setChecked(3)

    def exportbvh(self):
        self.env.logLine(2, "export BVH called")
        self.leftPanel.setExportType(".bvh")
        self.setChecked(4)

