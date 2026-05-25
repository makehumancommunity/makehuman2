"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck, Elvaerwyn_MH2 2026 V1.2

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
        self.save_props = True
        self.force_ue_axis = False   # Placeholder for Unreal +Z Up
        self.merge_meshes = False    # Placeholder for Mesh Merger


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
            scaletexts.append(str(elem[1]) + "   = factor " + str(elem[0]))

        # folders
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
        self.addWidget(QLabel("\nFilename:"))
        self.filename = QLineEdit(self.bc.name + etype)
        self.filename.editingFinished.connect(self.newfilename)
        self.addWidget(self.filename)

        self.binsave= QCheckBox("binary mode")
        self.binsave.setLayoutDirection(Qt.LeftToRight)
        self.binsave.toggled.connect(self.changeBinary)
        self.binsave.setChecked(self.values.binmode)
        self.binsave.setToolTip('Unchecked = readable text-based .gltf, Checked = packed self-contained binary .glb archive')
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

        self.props_toggle = QCheckBox("save custom studio props")
        self.props_toggle.setLayoutDirection(Qt.LeftToRight)
        self.props_toggle.toggled.connect(self.changePropsToggle)
        self.props_toggle.setChecked(self.values.save_props)
        self.props_toggle.setToolTip('Include custom scene props and room layout assets in your final 3D file export')
        self.addWidget(self.props_toggle)
        
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

# === NEW GAME ENGINE STUDIO TOGGLES HERE ===
        self.ueaxisw = QCheckBox("force +Z up (unreal engine)")
        self.ueaxisw.setLayoutDirection(Qt.LeftToRight)
        self.ueaxisw.toggled.connect(self.changeUEAxis)
        self.ueaxisw.setChecked(self.values.force_ue_axis)
        self.ueaxisw.setToolTip('Flips orientation coordinates from right-handed (+Y Up) to match Unreal Engines left-handed coordinate grid layout (+Z Up).')
        self.addWidget(self.ueaxisw)

        self.mergew = QCheckBox("merge all attached meshes")
        self.mergew.setLayoutDirection(Qt.LeftToRight)
        self.mergew.toggled.connect(self.changeMergeMeshes)
        self.mergew.setChecked(self.values.merge_meshes)
        self.mergew.setToolTip('Combines the body skin, clothing, hair, and studio props into a single optimized model layer to reduce engine draw calls.')
        self.addWidget(self.mergew)
        # =================================================

        self.addWidget(QLabel("Scaling:"))
        self.scalebox = QComboBox()
        self.scalebox.addItems(scaletexts)
        self.scalebox.currentIndexChanged.connect(self.changeScale)
        self.scalebox.setToolTip('MakeHuman works with decimeter system, destination system usually differs')
        self.addWidget(self.scalebox)

        self.exportbutton=QPushButton("Export")
        self.exportbutton.clicked.connect(self.exportfile)
        self.addWidget(self.exportbutton)

        self.setExportType(etype)

    def changePropsToggle(self, param):
        self.values.save_props = param

    def leave(self):
        if self.animmode is not None:
            self.animmode.leave()

    def setExportType(self, etype):
        common = "MakeHuman works with unit decimeter. "
        expAttrib = { 
            ".stl":  {"tip": common + "STL files are unit less. When working with printers 1 unit equals 1 millimeter (preset scale 1:10)",
                "num": 3, "binset": True, "binmode": "both", "imgset": False, "imgmode": False, "hiddenset": True, "hiddenmode": False,
                "animset": False, "animmode": False, "poseset": True, "posemode": False,
                "helpset": False, "helpmode": False, "normset": False, "normmode": False,
                "ue_axis_set": False, "merge_mesh_set": False}, # STL overrides hidden

            ".glb": { "tip": common + "glTF binary or text format",
                "num": 0, "binset": True, "binmode": "both", "imgset": True, "imgmode": False, "hiddenset": True, "hiddenmode": False,
                "animset": True, "animmode": False, "poseset": True, "posemode": False,
                "helpset": True, "helpmode": False, 
                "normset": True, "normmode": True,  # UNLOCKED: Let users include or drop custom vertex normals
                "ue_axis_set": True, "merge_mesh_set": True}, # UNLOCKED: Game Engine optimization toggles ready

            ".mh2b": { "tip": common + "Blender units are usually meters",
                "num": 0, "binset": False, "binmode": True, "imgset": False, "imgmode": False, "hiddenset": True, "hiddenmode": False,
                "animset": True, "animmode": False, "poseset": True, "posemode": False,
                "helpset": False, "helpmode": False, "normset": False, "normmode": False,
                "ue_axis_set": False, "merge_mesh_set": False},

            ".obj": { "tip": common + "Wavefront units are usually meters",
                "num": 0, "binset": False, "binmode": False, "imgset": False, "imgmode": False, "hiddenset": True, "hiddenmode": False,
                "animset": True, "animmode": False, "poseset": True, "posemode": False,
                "helpset": True, "helpmode": False, 
                "normset": True, "normmode": True,  # UNLOCKED: Retain tracking parameters safely
                "ue_axis_set": True, "merge_mesh_set": True}, 

            ".bvh": { "tip": common + "BVH units are usually the same as the internal scale",
                "num": 0, "binset": False, "binmode": False,  "imgset": False, "imgmode": False, "hiddenset": False, "hiddenmode": False,
                "animset": False, "animmode": True, "poseset": False, "posemode": False,
                "helpset": False, "helpmode": False, "normset": False, "normmode": False,
                "ue_axis_set": False, "merge_mesh_set": False}
        }

        if etype == ".gltf": etype = ".glb"
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
            if attr["animset"]:
                self.anim.setChecked(self.values.animation)
                self.anim.setEnabled(True)
            else:
                self.anim.setChecked(False)
                self.anim.setEnabled(False)
                self.values.animation = False

        self.posed.setChecked(self.values.inpose)
        self.posed.setEnabled(attr["poseset"])

        self.scalebox.setCurrentIndex(self.values.scale_index)
        self.scalebox.setToolTip(attr["tip"])

        if hasattr(self, 'props_toggle'):
            self.props_toggle.setChecked(self.values.save_props)
            self.props_toggle.setEnabled(etype in [".glb", ".obj"])

        # === AUTOMATIC DISCOVERY SYNCHRONIZERS ===
        if hasattr(self, 'ueaxisw'):
            self.ueaxisw.setChecked(self.values.force_ue_axis)
            self.ueaxisw.setEnabled(attr.get("ue_axis_set", False))

        if hasattr(self, 'mergew'):
            self.mergew.setChecked(self.values.merge_meshes)
            self.mergew.setEnabled(attr.get("merge_mesh_set", False))

    def changeScale(self, param):
        self.values.scale_index = param

    def changeBinary(self, param):
        self.values.binmode = param
        self.newfilename()

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

    def changeUEAxis(self, param):
        self.values.force_ue_axis = param

    def changeMergeMeshes(self, param):
        self.values.merge_meshes = param

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
        folder = self.foldername.text()
        if folder is None or folder == "":
            folder = self.env.stdUserPath("exports")
            self.foldername.setText(folder)
        self.values.export_folder = folder

    def newfilename(self):
        text = self.filename.text()
        base = os.path.splitext(text)[0]
        if self.values.export_type in [".glb", ".gltf"]:
            target_ext = ".glb" if self.values.binmode else ".gltf"
            self.filename.setText(base + target_ext)
        else:
            self.filename.setText(base + self.values.export_type)

    def newtexfolder(self):
        folder = self.texfolder.text()
        if folder is None or folder == "":
            folder = "textures"
        else:
            folder = self.env.normalizeName(folder)
        self.texfolder.setText(folder)
        self.values.texture_folder = folder

    def exportfile(self):
        folder = self.foldername.text()
        texfolder = self.texfolder.text()
        
        base_name = os.path.splitext(self.filename.text())[0]
        etype = self.values.export_type
        
        if etype in [".glb", ".gltf"]:
            actual_ext = ".glb" if self.values.binmode else ".gltf"
            path = os.path.join(folder, base_name + actual_ext)
        else:
            path = os.path.join(folder, base_name + etype)
        
        if os.path.isfile(path):
            dbox = DialogBox("Replace " + path + "?", QDialogButtonBox.Ok)
            confirmed = dbox.exec()
            if confirmed != 1:
                return

        current = self.scalebox.currentIndex()
        scale = float(self.scale_items[current][0])

        if self.bc is None or getattr(self.bc, 'baseMesh', None) is None:
            from types import SimpleNamespace
            export_target = SimpleNamespace(
                baseMesh=None, proxy=None, attachedAssets=[], skeleton=None, bvh=None,
                name="Standalone_Workspace_Props", getLowestPos=lambda: 0.0
            )
        else:
            export_target = self.bc

        if etype in [".glb", ".gltf"]:
            is_text_mode = not self.values.binmode
            
            gltf = gltfExport(self.glob, folder, texfolder, is_text_mode, self.values.savehiddenverts,
                    self.values.onground, self.values.animation, scale)
            
            # Send the new advanced tracking data attributes down to the core layout
            gltf.save_props = self.values.save_props
            gltf.force_ue_axis = self.values.force_ue_axis
            gltf.merge_meshes = self.values.merge_meshes
            
            success = gltf.binSave(export_target, path)

        elif etype == ".stl":
            if export_target.baseMesh is None:
                self.env.last_error = "STL exporter requires a mesh surface."
                success = False
            else:
                stl = stlExport(self.glob, folder, self.values.savehiddenverts, scale)
                if self.values.binmode:
                    success = stl.binSave(export_target, path)
                else:
                    success = stl.ascSave(export_target, path)

        elif etype == ".mh2b":
            if export_target.baseMesh is None:
                self.env.last_error = "Blender link requires a character mesh."
                success = False
            else:
                blcom = blendCom(self.glob, folder, texfolder, self.values.savehiddenverts,
                        self.values.onground, self.values.animation, scale)
                success = blcom.binSave(export_target, path)

        elif etype == ".obj":
            obj = objExport(self.glob, folder, texfolder, self.values.savehiddenverts,
                    self.values.onground, self.values.helper, self.values.normals, scale)
            obj.animation = self.values.animation
            obj.inpose = self.values.inpose
            obj.save_props = self.values.save_props
            success = obj.ascSave(export_target, path)

        elif etype == ".bvh":
            if export_target.skeleton is None:
                self.env.last_error = "BVH requires a skeleton."
                success = False
            else:
                bvh = bvhExport(self.glob, self.values.onground, scale)
                success = bvh.ascSave(export_target, path)
        else:
            return

        if success:
            QMessageBox.information(self.parent, "Done!", "Scene assets successfully exported to: " + path)
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
                { "button": None, "icon": "stl_sym.png", "tip": "export as STL", "func": self.exportstl},
                { "button": None, "icon": "blend_sym.png", "tip": "export as MH2B", "func": self.exportmh2b},
                { "button": None, "icon": "wavefront_sym.png", "tip": "export as OBJ", "func": self.exportobj},
                { "button": None, "icon": "bvh_sym.png", "tip": "export as BVH", "func": self.exportbvh}
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
        self.leftPanel.setExportType(".glb")
        self.setChecked(0)

    def exportstl(self):
        self.leftPanel.setExportType(".stl")
        self.setChecked(1)

    def exportmh2b(self):
        self.leftPanel.setExportType(".mh2b")
        self.setChecked(2)

    def exportobj(self):
        self.leftPanel.setExportType(".obj")
        self.setChecked(3)

    def exportbvh(self):
        self.leftPanel.setExportType(".bvh")
        self.setChecked(4)





