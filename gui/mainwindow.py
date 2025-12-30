"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MHMainWindow
"""
from PySide6.QtWidgets import ( 
        QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QFrame, QGroupBox, QListWidget, QLabel,
        QAbstractItemView, QSizePolicy, QScrollArea, QDialogButtonBox, QMessageBox
        )
from PySide6.QtGui import QIcon, QCloseEvent, QAction, QDesktopServices
from PySide6.QtCore import QSize, Qt, QUrl
from gui.prefwindow import  MHPrefWindow
from gui.logwindow import  MHLogWindow
from gui.infowindow import  MHInfoWindow
from gui.memwindow import  MHMemWindow
from gui.measurewindow import MHCharMeasWindow
from gui.scenewindow import  MHSceneWindow
from gui.graphwindow import  MHGraphicWindow, NavigationEvent
from gui.randomwindow import RandomForm, RandomValues
from gui.fileactions import BaseSelect, SaveMHMForm, DownLoadImport
from gui.exporter import ExportLeftPanel, ExportRightPanel
from gui.poseactions import AnimPlayer, AnimPlayerValues, AnimMode
from gui.poseeditor import AnimExpressionEdit, AnimPoseEdit
from gui.slider import ScaleComboArray
from gui.imageselector import ImageSelection
from gui.renderer import Renderer, RendererValues
from gui.common import DialogBox, ErrorBox, WorkerThread, MHBusyWindow, MHGroupBox, IconButton, TextBox, MHFileRequest
from gui.qtreeselect import MHTreeView
from core.baseobj import baseClass
from core.apisocket import apiSocket
from core.attached_asset import attachedAsset
from opengl.info import GLDebug

import os

class MHMainWindow(QMainWindow):
    """
    Main Window class
    """
    def __init__(self, glob):
        self.env = glob.env
        env = glob.env
        self.glob = glob

        self.prog_window = None     # will hold the progress bar

        self.leftColumn = None
        self.LeftBox = None         # layouts to fill
        self.lastClass = None       # needed for close functions

        self.rightColumn = None
        self.visRightColumn = None  # QWidget to hide right column
        self.ToolBox = None

        self.graph = None

        self.qTree = None
        self.qtreefilter = None

        self.ButtonBox = None
        self.CategoryBox = None
        self.baseSelector = None

        self.bckproc = None         # background process is running

        self.tool_mode = 0          # 0 = files, 1 = modelling, 2 = equipment, 3 = pose, 4 = render, 10 = information
        self.category_mode = 0      # the categories according to tool_mode

        self.equipment = [
                { "func": None, "menu": None, "name": "clothes", "mode": 1 },
                { "func": None, "menu": None, "name": "hair", "mode": 0 },
                { "func": None, "menu": None, "name": "eyes", "mode": 0 },
                { "func": None, "menu": None, "name": "eyebrows", "mode": 0 },
                { "func": None, "menu": None, "name": "eyelashes", "mode": 0 },
                { "func": None, "menu": None, "name": "teeth", "mode": 0 },
                { "func": None, "menu": None, "name": "tongue", "mode": 0 },
                { "func": None, "menu": None, "name": "proxy", "mode": 0 }
        ]
        self.animation = [
                { "func": None, "menu": None, "name": "rigs", "mode": 0 },
                { "func": None, "menu": None, "name": "poses", "mode": 0 },
                { "func": None, "menu": None, "name": "animation", "mode": 0 },
                { "func": None, "menu": None, "name": "expressions", "mode": 0 },
                { "func": None, "menu": None, "name": "expression editor", "mode": 0 },
                { "func": None, "menu": None, "name": "pose editor", "mode": 0 }
        ]

        self.model_buttons = [ 
                { "button": None, "icon": "reset.png", "tip": "Reset all targets", "func": self.reset_call, "check": False },
                { "button": None, "icon": "symm1.png", "tip": "Symmetry, right to left", "func": self.symRToL, "check": False },
                { "button": None, "icon": "symm2.png", "tip": "Symmetry, left to right", "func": self.symLToR, "check": False },
                { "button": None, "icon": "symm.png", "tip": "Symmetry applied always", "func": self.symSwitch }
        ]

        self.tool_buttons = [ 
                { "button": None, "icon": "files.png", "tip": "Files", "func": self.setCategoryIcons},
                { "button": None, "icon": "sculpt.png", "tip": "Modelling, Change character", "func": self.setCategoryIcons},
                { "button": None, "icon": "equip.png", "tip": "Add equipment", "func": self.setCategoryIcons },
                { "button": None, "icon": "pose.png", "tip": "Pose", "func": self.setCategoryIcons },
                { "button": None, "icon": "render.png", "tip": "Render", "func": self.setCategoryIcons }
        ]
        self.category_buttons = [
            [ 
                { "button": None, "h": False, "icon": "f_newbase.png", "tip": "select basemesh", "func": self.callCategory},
                { "button": None, "h": False, "icon": "f_load.png", "tip": "load character", "func": self.callCategory},
                { "button": None, "h": False, "icon": "f_save.png", "tip": "save character", "func": self.callCategory},
                { "button": None, "h": False, "icon": "f_export.png", "tip": "export character", "func": self.callCategory},
                { "button": None, "h": False, "icon": "f_download.png", "tip": "download assets", "func": self.callCategory}
            ], [ 
                { "button": None, "h": False, "icon": "measurement.png", "tip": "modelling by category", "func": self.callCategory},
                { "button": None, "h": False, "icon": "randomhuman.png", "tip": "randomize", "func": self.callCategory}
            ], [
                { "button": None, "h": False, "ref": "clothes", "icon": "eq_clothes.png", "tip": "Clothes", "func": self.callCategory },
                { "button": None, "h": False, "ref": "hair", "icon": "eq_hair.png", "tip": "Hair", "func": self.callCategory },
                { "button": None, "h": False, "ref": "eyes", "icon": "eq_eyes.png", "tip": "Eyes", "func": self.callCategory },
                { "button": None, "h": False, "ref": "eyebrows", "icon": "eq_eyebrows.png", "tip": "Eyebrows", "func": self.callCategory },
                { "button": None, "h": False, "ref": "eyelashes", "icon": "eq_eyelashes.png", "tip": "Eyelashes", "func": self.callCategory },
                { "button": None, "h": False, "ref": "teeth", "icon": "eq_teeth.png", "tip": "Teeth", "func": self.callCategory },
                { "button": None, "h": False, "ref": "tongue", "icon": "eq_tongue.png", "tip": "Tongue", "func": self.callCategory },
                { "button": None, "h": False, "ref": "proxy", "icon": "eq_proxy.png", "tip": "Topology, Proxies", "func": self.callCategory }
            ], [
                { "button": None, "h": False, "icon": "an_skeleton.png", "tip": "Skeleton", "func": self.callCategory},
                { "button": None, "h": False, "icon": "an_pose.png", "tip": "Load pose or animation", "func": self.callCategory},
                { "button": None, "h": False, "icon": "an_movie.png", "tip": "Play animation", "func": self.callCategory},
                { "button": None, "h": False, "icon": "an_expression.png", "tip": "Expressions", "func": self.callCategory},
                { "button": None, "h": False, "icon": "an_expressedit.png", "tip": "Expression editor", "func": self.callCategory},
                { "button": None, "h": False, "icon": "an_modpose.png", "tip": "Pose editor", "func": self.callCategory}
            ], [
            ]
        ]

        super().__init__()

        s = env.session["mainwinsize"]
        self.resize (s["w"], s["h"])
        
        menu_bar = self.menuBar()

        about_menu = menu_bar.addMenu(QIcon(os.path.join(env.path_sysicon, "makehuman.png")), "&About")
        self.addActCallBack(about_menu, "Info", self.info_call)

        file_menu = menu_bar.addMenu("&File")
        self.addActCallBack(file_menu, "Load Model", self.loadmhm_call)
        self.addActCallBack(file_menu, "Save Model", self.savemhm_call)
        self.addActCallBack(file_menu, "Export Model", self.exportmhm_call)
        self.addActCallBack(file_menu, "Download Assets", self.download_call)
        self.addActCallBack(file_menu, "Quit", self.quit_call)

        set_menu = menu_bar.addMenu("&Settings")
        self.addActCallBack(set_menu, "Preferences", self.pref_call)
        self.addActCallBack(set_menu, "Lights and Scene", self.scene_call)
        self.addActCallBack(set_menu, "Messages", self.log_call)

        binaries = set_menu.addMenu("Create Binaries")
        self.addActCallBack(binaries, "User 3d Objects", self.compress_user3dobjs)
        self.addActCallBack(binaries, "User Targets", self.compress_usertargets)

        if env.admin:
            self.addActCallBack(binaries, "System 3d Objects", self.compress_sys3dobjs)
            self.addActCallBack(binaries, "System Targets", self.compress_systargets)

        set_menu.addSeparator()
        regenerate = set_menu.addMenu("Regenerate all Binaries")
        self.addActCallBack(regenerate, "User 3d Objects", self.regenerate_user3dobjs)

        if env.admin:
            self.addActCallBack(regenerate, "System 3d Objects", self.regenerate_sys3dobjs)

        set_menu.addSeparator()
        self.addActCallBack(set_menu, "Backup User Database", self.exportUserDB)
        self.addActCallBack(set_menu, "Restore User Database", self.importUserDB)

        tools_menu = menu_bar.addMenu("&Tools")
        self.addActCallBack(tools_menu, "Select Basemesh", self.base_call)
        self.addActCallBack(tools_menu, "Change Character", self.morph_call)
        self.addActCallBack(tools_menu, "Randomize Character", self.random_call)

        self.equip = tools_menu.addMenu("Equipment")
        self.animenu = tools_menu.addMenu("Animation")

        act_menu = menu_bar.addMenu("&Activate")

        act = QAction('Diamond skeleton', act_menu, checkable=True)
        act_menu.addAction(act)
        act.triggered.connect(self.dimskel_call)

        act = QAction('Floor instead of grid', act_menu, checkable=True)
        act_menu.addAction(act)
        act.triggered.connect(self.floor_call)

        act = QAction('Socket active', act_menu, checkable=True)
        act_menu.addAction(act)
        act.triggered.connect(self.socket_call)

        act = QAction('Debug camera', act_menu, checkable=True)
        act_menu.addAction(act)
        act.triggered.connect(self.deb_cam)

        info_menu = menu_bar.addMenu("&Information")
        self.addActCallBack(info_menu, "Character Info", self.measure_call)
        self.addActCallBack(info_menu, "Memory Info", self.memory_call)
        self.addActCallBack(info_menu, "Local OpenGL Information", self.glinfo_call)
        self.addActCallBack(info_menu, "Used library versions", self.vers_call)
        self.addActCallBack(info_menu, "License", self.lic_call)

        lics = info_menu.addMenu("3rd Party licenses")
        for elem in ["PySide6", "PyOpenGL", "NumPy"]:
            self.addActCallBack(lics, elem, self.lic_call)

        self.addActCallBack(info_menu, "Credits", self.lic_call)

        if "support_urls" in self.env.release_info:
            for elem in self.env.release_info["support_urls"]:
                urlname = self.env.release_info["support_urls"][elem]
                if urlname in self.env.release_info:
                    self.addActCallBack(info_menu, elem, self.url_info_call)

        help_menu = menu_bar.addMenu("&Help")
        self.addActCallBack(help_menu, "Context Help", self.context_help)
        self.addActCallBack(help_menu, "Navigation", self.nav_help)
        self.addActCallBack(help_menu, "File System", self.fsys_help)

        if self.glob.baseClass is not None:
            self.createImageSelection()

        # generate tool buttons, model_buttons (save ressources)
        #
        for elem in (self.tool_buttons, self.model_buttons):
            for n, b in enumerate(elem):
                c = b["check"] if "check" in b else True
                b["button"] = IconButton(n, os.path.join(self.env.path_sysicon, b["icon"]), b["tip"], b["func"], checkable=c)
        self.markSelectedButtons(self.tool_buttons, self.tool_buttons[0])

        # generate category buttons
        #
        for m, tool in enumerate(self.category_buttons):
            offset = (m + 1) * 100
            for n, b in enumerate(tool):
                if b["h"] is False:
                    b["button"] = IconButton(offset+n, os.path.join(self.env.path_sysicon, b["icon"]), b["tip"], b["func"], checkable=True)
        self.markSelectedButtons(self.category_buttons[0], self.category_buttons[0][0])

        # generate random values
        if self.glob.baseClass is not None:
            self.setPresets()

        self.createCentralWidget()
        self.setWindowTitle("default character")


    def debug(self, text):
        self.env.logLine(2, "MainWindow: " + text)

    def addActCallBack(self, menu, title, callback):
        entry = menu.addAction(title)
        entry.triggered.connect(callback)
        return entry

    def createImageSelection(self):
        binfo = self.glob.baseClass.baseInfo

        self.equip.clear()
        eqrow = self.category_buttons[2]
        equipment = binfo["equipment"] if "equipment" in binfo else ["clothes"]
        for elem in eqrow:
            elem["h"] = not ("ref" in elem and elem["ref"] in equipment)
        for elem in self.equipment:
            if elem["name"] in equipment:
                elem["func"] = ImageSelection(self, self.glob.cachedInfo, elem["name"], elem["mode"], self.equipCallback, doubleclick=True)
                elem["func"].prepare()
                elem["menu"] = self.addActCallBack(self.equip, elem["name"], self.equip_call)

        self.charselect = ImageSelection(self, self.glob.cachedInfo, "models", 0, self.loadByIconCallback, 3, True)
        self.charselect.prepare()

        self.animenu.clear()
        for elem in self.animation:
            elem["func"] = ImageSelection(self, self.glob.cachedInfo, elem["name"], elem["mode"], self.animCallback, doubleclick=True)
            elem["func"].prepare()
            elem["menu"] = self.addActCallBack(self.animenu, elem["name"], self.anim_call)

    def setWindowTitle(self, text):
        title = self.env.release_info["name"] + " (" + text + ")"
        super().setWindowTitle(title)


    def equipCallback(self, selected, eqtype, multi):
        self.glob.project_changed = True
        if isinstance(selected, str):
            self.glob.baseClass.delAsset(selected)
            return
        if selected.status == 0:
            self.glob.baseClass.delAsset(selected.filename)
        elif selected.status == 1:
            self.glob.baseClass.addAndDisplayAsset(selected.filename, eqtype, multi)

    def animCallback(self, selected, eqtype, multi):
        self.glob.project_changed = True
        if eqtype == "rigs":
            if selected.status == 0:
                self.glob.baseClass.delSkeleton(selected.filename)
            else:
                self.glob.baseClass.addSkeleton(selected.name, selected.filename)
        elif eqtype == "poses":
            if selected.status == 0:
                self.glob.baseClass.delPose(selected.filename)
            else:
                if not self.glob.baseClass.addPose(selected.name, selected.filename):
                    ErrorBox(self.central_widget, self.env.last_error)
                else:
                    self.glob.baseClass.corrections = None
            self.graph.view.Tweak()
        elif eqtype == "expressions":
            if selected.status == 0:
                self.glob.baseClass.delExpression(selected.filename)
            else:
                self.glob.baseClass.addExpression(selected.name, selected.filename)
            self.graph.view.Tweak()

    def buttonRow(self, subtool):
        if len(subtool) == 0:
            return (None)

        row=QHBoxLayout()
        row.setSpacing(0)
        for n, b in enumerate(subtool):
            if "h" not in b or b["h"] is False:
                row.addWidget(b["button"])
        row.addStretch()

        return(row)

    def markSelectedButtons(self, row, button):
        sel = button["button"]
        for elem in row:
            b = elem["button"]
            if b is not None:
                b.setChecked(b == sel)
        if self.glob.baseClass is None:
            for elem in row[1:]:
                b = elem["button"]
                if b is not None:
                    b.setEnabled(False)
        else:
            for elem in row:
                b = elem["button"]
                if b is not None:
                    b.setEnabled(True)

    def setCategoryIcons(self):
        s = self.sender()
        self.setToolModeAndPanel(s._funcid, 0)

    def callCategory(self):
        s = self.sender()
        m = s._funcid -100
        self.setToolModeAndPanel(m // 100, m % 100)

    def createCentralWidget(self):
        """
        create central widget containing 3 columns
        """
        env = self.env
        self.central_widget = QWidget()
        self.glob.centralWidget = self.central_widget

        hLayout = QHBoxLayout()         # 3 columns
        hLayout.setSpacing(2)
        hLayout.setContentsMargins(2, 3, 2, 3)

        # left side, two rows of buttons
        # first select tools
        #
        rowgroup1 = QFrame()
        rowgroup1.setObjectName("gboxseltools")
        rowgroup1.setMaximumWidth(400)
        self.ToolSelBox = QVBoxLayout()
        row = self.buttonRow(self.tool_buttons)
        self.ToolSelBox.addLayout(row)
        rowgroup1.setLayout(self.ToolSelBox)

        # second select category
        #
        rowgroup2  = QFrame()
        rowgroup2.setObjectName("gboxnontitle")
        rowgroup2.setMaximumWidth(400)
        self.ButtonBox = QVBoxLayout()
        self.CategoryBox= self.buttonRow(self.category_buttons[0])
        self.ButtonBox.addLayout(self.CategoryBox)
        rowgroup2.setLayout(self.ButtonBox)

        # left side base panel
        #
        self.LeftBox = QVBoxLayout()
        self.leftColumn = MHGroupBox("Base")
        self.leftColumn.setMinimumWidth(300)
        self.leftColumn.setMaximumWidth(400)
        self.drawLeftPanel()

        v2Layout = QVBoxLayout()
        v2Layout.addWidget(rowgroup1)
        v2Layout.addWidget(rowgroup2)
        v2Layout.addLayout(self.leftColumn.MHLayout(self.LeftBox),1)

        hLayout.addLayout(v2Layout)

        # create window for graphical output
        #
        self.glob.midColumn = self.graph = MHGraphicWindow(self.glob)
        gLayout = self.graph.createLayout()
        #
        # keyboard
        #
        self.eventFilter = NavigationEvent(self.graph)
        self.installEventFilter(self.eventFilter)

        # add view in layout
        #
        frame = MHGroupBox("Viewport")
        hLayout.addLayout(frame.MHLayout(gLayout),3)

        # right side, ToolBox, can be hidden by visRightColumn
        #
        self.visRightColumn = QWidget()
        self.ToolBox = QVBoxLayout()
        vis = self.drawRightPanel()
        self.visRightColumn.setVisible(vis)
        self.rightColumn = MHGroupBox("Default")  # default values
        self.rightColumn.setMinimumWidth(300)
        self.visRightColumn.setLayout(self.rightColumn.MHLayout(self.ToolBox))
        hLayout.addWidget(self.visRightColumn, 2)

        #
        self.central_widget.setLayout(hLayout)
        self.setCentralWidget(self.central_widget)

    def drawLeftPanel(self):
        """
        draw left panel
        """
        env = self.env

        # extra code for no basemesh selected
        #
        if (self.tool_mode == 0 and self.category_mode == 0) or env.basename is None:
            self.leftColumn.setTitle("Base mesh :: selection")
            self.baseSelector = BaseSelect(self, self.selectmesh_call)
            self.LeftBox.addLayout(self.baseSelector)
            self.LeftBox.addStretch()
            return

        if self.tool_mode == 0:
            if self.category_mode == 1:
                extra = ["Load complete character", "Load only targets", "Load only head-targets"]
                self.leftColumn.setTitle("Load file :: filter")
                layout = self.charselect.leftPanel(extra)
                self.LeftBox.addLayout(layout)
            elif self.category_mode == 2:
                self.leftColumn.setTitle("Save file :: parameters")
                self.saveForm = SaveMHMForm(self, self.graph.view, self.charselect, self.setWindowTitle)
                self.LeftBox.addLayout(self.saveForm)
            elif self.category_mode == 3:
                self.leftColumn.setTitle("Export file :: parameters")
                self.lastClass = self.exportForm = ExportLeftPanel(self)
                self.LeftBox.addLayout(self.exportForm)
            elif self.category_mode == 4:
                self.leftColumn.setTitle("Import file :: parameters")
                dlform = DownLoadImport(self, self.graph.view, self.setWindowTitle)
                self.LeftBox.addLayout(dlform)
            self.LeftBox.addStretch()
            return

        
        if self.tool_mode == 1:
            if self.glob.targetCategories is None:
                self.env.logLine(1, self.env.last_error )
                return
            if self.category_mode == 0:
                self.leftColumn.setTitle("Modify character :: categories")
                self.qTree = MHTreeView(self.glob.targetCategories, "Modelling", self.redrawNewCategory, None)
                self.qtreefilter = self.qTree.getStartPattern()
                self.LeftBox.addWidget(self.qTree)
                row = self.buttonRow(self.model_buttons)
                self.LeftBox.addLayout(row)
                return
            else:
                self.leftColumn.setTitle("Random character :: parameters")
                self.randForm = RandomForm(self, self.graph.view) 
                self.LeftBox.addLayout(self.randForm)
                return

        elif self.tool_mode == 2:
            self.leftColumn.setTitle("Character equipment :: filter")
            layout = self.equipment[self.category_mode]["func"].leftPanel()
            self.LeftBox.addLayout(layout)

        elif self.tool_mode == 3:
            if self.glob.baseClass.pose_skeleton is None:
                ErrorBox(self.central_widget, "no poseskeleton added")
                return
            if self.category_mode == 0:
                self.leftColumn.setTitle("Rigs :: filter")
                layout = self.animation[self.category_mode]["func"].leftPanel()
                self.LeftBox.addLayout(layout)
            elif self.category_mode == 1:
                self.leftColumn.setTitle("Poses :: filter")
                self.lastClass = AnimMode(self.glob)
                layout = self.animation[self.category_mode]["func"].leftPanel()
                self.LeftBox.addLayout(layout)
            elif self.category_mode == 2:
                self.leftColumn.setTitle("Animation Player")
                self.lastClass = AnimPlayer(self.glob)
                self.lastClass.enter()
                self.LeftBox.addLayout(self.lastClass)
                self.LeftBox.addStretch()
            elif self.category_mode == 3:
                self.leftColumn.setTitle("Expressions :: filter")
                self.lastClass = AnimMode(self.glob)
                layout = self.animation[self.category_mode]["func"].leftPanel()
                self.LeftBox.addLayout(layout)
            elif self.category_mode == 4:
                self.leftColumn.setTitle("Expressions :: editor")
                self.lastClass = AnimExpressionEdit(self, self.glob)
                units = self.glob.baseClass.getFaceUnits()
                filterparam = units.createFilterDict() if units is not None else {}
                self.qTree = MHTreeView(filterparam, "Categories", self.redrawNewExpression, None)
                self.qtreefilter = self.qTree.getStartPattern()
                self.LeftBox.addWidget(self.qTree)
                layout = self.lastClass.addClassWidgets()
                self.LeftBox.addLayout(layout)
            else:
                self.leftColumn.setTitle("Pose :: editor")
                self.lastClass = AnimPoseEdit(self, self.glob)
                units = self.glob.baseClass.getBodyUnits()
                filterparam = units.createFilterDict() if units is not None else {}
                self.qTree = MHTreeView(filterparam, "Categories", self.redrawNewPose, None)
                self.qtreefilter = self.qTree.getStartPattern()
                self.LeftBox.addWidget(self.qTree)
                layout = self.lastClass.addClassWidgets()
                self.LeftBox.addLayout(layout)

        elif self.tool_mode == 4:
            self.leftColumn.setTitle("Rendering :: parameters")
            self.lastClass = Renderer(self, self.glob)
            self.lastClass.enter()
            self.LeftBox.addLayout(self.lastClass)
            self.LeftBox.addStretch()
        else:
            self.leftColumn.setTitle("Not yet implemented") # not reached


    def drawExpressionPanel(self, text="None"):
        if text == "None":
            text = self.qTree.getLastHeadline()
        self.rightColumn.setTitle("Expressions, category: " + text)
        widget = QWidget()
        sweep = os.path.join(self.glob.env.path_sysicon, "sweep.png")
        if self.lastClass is not None:
            expressions = self.lastClass.fillExpressions()
            self.exprArray = ScaleComboArray(widget, expressions, self.qtreefilter, sweep)
            widget.setLayout(self.exprArray.layout)
            scrollArea = QScrollArea()
            scrollArea.setWidget(widget)
            scrollArea.setWidgetResizable(True)
            self.ToolBox.addWidget(scrollArea)

    def drawPosePanel(self, text="None"):
        if text == "None":
            text = self.qTree.getLastHeadline()
        self.rightColumn.setTitle("Poses, category: " + text)
        widget = QWidget()
        sweep = os.path.join(self.glob.env.path_sysicon, "sweep.png")
        if self.lastClass is not None:
            poses = self.lastClass.fillPoses()
            self.poseArray = ScaleComboArray(widget, poses, self.qtreefilter, sweep)
            widget.setLayout(self.poseArray.layout)
            scrollArea = QScrollArea()
            scrollArea.setWidget(widget)
            scrollArea.setWidgetResizable(True)
            self.ToolBox.addWidget(scrollArea)

    def drawMorphPanel(self, text="None"):
        if text == "None":
            text = self.qTree.getLastHeadline()
        self.rightColumn.setTitle("Morph, category: " + text)
        if self.glob.Targets is not None:
            widget = QWidget()
            sweep = os.path.join(self.glob.env.path_sysicon, "sweep.png")
            self.scalerArray = ScaleComboArray(widget, self.glob.Targets.modelling_targets, self.qtreefilter, sweep)
            widget.setLayout(self.scalerArray.layout)
            scrollArea = QScrollArea()
            scrollArea.setWidget(widget)
            scrollArea.setWidgetResizable(True)
            self.ToolBox.addWidget(scrollArea)

    def drawImageSelector(self, category, text, buttonmask=3):
        self.rightColumn.setTitle(text)
        layout = category.rightPanel(buttonmask)
        self.ToolBox.addLayout(layout)

    def drawExportPanel(self, connector, text):
        self.rightColumn.setTitle(text)
        layout = ExportRightPanel(self, connector)
        self.ToolBox.addLayout(layout)

    def drawRightPanel(self, text="None"):
        """
        create panel for right column according to tool_mode and category_mode
        :param text: headline
        :returns: True (to be generated) else False
        """
        if self.glob.baseClass is None:
            return False

        self.glob.openGLWindow.delMarker()

        if self.tool_mode == 0:
            if self.category_mode == 0:
                if self.rightColumn is None:
                    return False
                return False
            elif self.category_mode == 1:
                self.drawImageSelector(self.charselect, "Character MHM Files", 4)
            elif self.category_mode == 2:
                self.drawImageSelector(self.charselect, "Character MHM Files (select to replace file)", 0)
            elif self.category_mode == 3:
                self.drawExportPanel(self.exportForm, "Export character")
            elif self.category_mode == 4:
                return False
            else:
                return False
        elif self.tool_mode == 1:
            if self.category_mode == 0:
                self.drawMorphPanel(text)
            else:
                return False
        elif self.tool_mode == 2:
            mask = 13 if self.category_mode == 7 else 15
            equip = self.equipment[self.category_mode]
            text = "Equipment, category: " + equip["name"]
            self.drawImageSelector(equip["func"], text, mask)
        elif self.tool_mode == 3:
            if self.category_mode == 0 or self.category_mode == 1 or self.category_mode == 3:
                equip = self.animation[self.category_mode]
                text = "Pose and animation, category: " + equip["name"]
                self.drawImageSelector(equip["func"], text, 13)
            elif self.category_mode == 4:
                self.drawExpressionPanel(text)
            elif self.category_mode == 5:
                self.drawPosePanel(text)
            else:
                return False
        else:
            return False
        return True


    def emptyLayout(self, layout):
        if layout is not None and hasattr(layout,"count"):
            #print("-- -- input layout: "+str(layout))
            for i in reversed(range(layout.count())):
                layoutItem = layout.itemAt(i)
                if layoutItem.widget() is not None:
                    widgetToRemove = layoutItem.widget()
                    widgetToRemove.setParent(None)
                    layout.removeWidget(widgetToRemove)
                    #print("found widget: " + str(widgetToRemove))
                elif layoutItem.spacerItem() is not None:
                    layout.removeItem(layoutItem)
                else:
                    layoutToRemove = layout.itemAt(i)
                    self.emptyLayout(layoutToRemove)

    def emptyAll(self):
        self.emptyLayout(self.LeftBox)
        self.emptyLayout(self.ToolBox)
        self.emptyLayout(self.CategoryBox)
        """
        if self.LeftBox.isEmpty():
            print ("LeftBox is empty")
        else:
            print ("LeftBox is NOT  empty")
        if self.ToolBox.isEmpty():
            print ("ToolBox is empty")
        else:
            print ("ToolBox is NOT  empty")
        if self.CategoryBox is not None and self.CategoryBox.isEmpty():
            print ("CategoryBox is empty")
        else:
            print ("CategoryBox is NOT  empty")
        """

    def setToolModeAndPanel(self, tool, category):
        if self.tool_mode != tool or self.category_mode != category:
            if self.lastClass is not None:
                self.lastClass.leave()
                self.lastClass = None
            """
            self.emptyLayout(self.LeftBox)
            self.emptyLayout(self.ToolBox)
            self.emptyLayout(self.CategoryBox)
            """
            self.emptyAll()
            self.tool_mode = tool
            self.category_mode = category
            self.markSelectedButtons(self.tool_buttons, self.tool_buttons[tool])
            buttons = self.category_buttons[tool]
            self.CategoryBox= self.buttonRow(buttons)
            if self.CategoryBox is not None:
                self.ButtonBox.insertLayout(0, self.CategoryBox)
                self.markSelectedButtons(buttons, buttons[category])
            self.drawLeftPanel()
            vis = self.drawRightPanel()
            self.visRightColumn.setVisible(vis)
        else:
            # refresh status
            self.markSelectedButtons(self.tool_buttons, self.tool_buttons[tool])
            buttons = self.category_buttons[tool]
            if len(buttons) > 0:
                self.markSelectedButtons(buttons, buttons[category])

    def setPresets(self):
        self.glob.guiPresets["Randomizer"] = RandomValues(self.glob)
        self.glob.guiPresets["Animplayer"] = AnimPlayerValues(self.glob)
        self.glob.guiPresets["Renderer"] = RendererValues(self.glob)

    def deb_cam(self):
        self.graph.setDebug(self.sender().isChecked())

    def closeEvent(self, event):
        self.quit_call(event)

    def base_call(self):
        self.setToolModeAndPanel(0, 0)

    def morph_call(self):
        if self.glob.baseClass is not None:
            self.setToolModeAndPanel(1, 0)

    def random_call(self):
        if self.glob.baseClass is not None:
            self.setToolModeAndPanel(1, 1)

    def equip_call(self):
        s = self.sender()
        for n, elem in enumerate(self.equipment):
            if elem["menu"] == s:
                self.setToolModeAndPanel(2, n)
                break

    def anim_call(self):
        s = self.sender()
        for n, elem in enumerate(self.animation):
            if elem["menu"] == s:
                self.setToolModeAndPanel(3, n)
                break

    # open sub-windows
    #
    def pref_call(self):
        self.glob.showSubwindow("pref", self, MHPrefWindow)

    def log_call(self):
        self.glob.showSubwindow("log", self, MHLogWindow)

    def memory_call(self):
        self.glob.showSubwindow("memory", self, MHMemWindow)

    def measure_call(self):
        if self.glob.baseClass is not None:
            self.glob.showSubwindow("measure", self, MHCharMeasWindow)

    def info_call(self):
        self.glob.showSubwindow("about", self.glob, MHInfoWindow)

    def scene_call(self):
        self.glob.showSubwindow("scene", self, MHSceneWindow)

    # 
    def changesLost(self, text):
        confirmed = 1
        if self.glob.project_changed:
            dbox = DialogBox(text + ": all recent changes will be lost.\nPress cancel to abort", QDialogButtonBox.Ok)
            confirmed = dbox.exec()
        return(confirmed)

    def parallelLoad(self, bckproc, *args):
        self.glob.baseClass.loadMHMFile(args[0][0], self.prog_window)
        # self.prog_window.setLabelText(elem.folder + ": create binary " + os.path.split(elem.path)[1])

    def finishLoad(self):
        gl = self.graph.view
        gl.setCameraCenter()
        gl.addAssets()
        gl.newSkin(self.glob.baseClass.baseMesh)
        gl.scene.prepareSkeleton()
        if self.prog_window is not None:
            self.prog_window.progress.close()
            self.prog_window = None
        self.glob.openGLBlock = False
        gl.scene.newFloorPosition()
        gl.Tweak()
        self.setWindowTitle(self.glob.baseClass.name)
        self.graph.setSizeInfo()
        self.glob.parallel = None

    def newCharacter(self, filename, mode=0):
        gl = self.graph.view
        if filename is None:
            self.glob.project_changed = False
            return

        if mode !=  0:
            print ("character only modified by targets")
            self.glob.baseClass.loadMHMTargetsOnly(filename, mode)
            gl.setCameraCenter()
            gl.scene.prepareSkeleton()
            gl.scene.newFloorPosition()
            gl.Tweak()
            self.graph.setSizeInfo()

        elif self.glob.parallel is None:
            self.setToolModeAndPanel(0, 0)
            self.glob.openGLBlock = True
            gl.noGLObjects(leavebase=True)
            self.glob.textureRepo.cleanup()
            self.glob.baseClass.reset()
            self.prog_window = MHBusyWindow("Load character", "start")
            self.prog_window.progress.forceShow()
            self.glob.parallel = WorkerThread(self.parallelLoad, filename)
            self.glob.parallel.start()
            self.glob.parallel.finished.connect(self.finishLoad)
            gl.setCameraCenter()
            self.glob.project_changed = False

    def loadmhm_call(self):
        if self.glob.baseClass is not None:
            self.setToolModeAndPanel(0, 1)

    def loadByIconCallback(self, asset, eqtype, multi):

        # in case of save add data into formular only
        #
        if self.category_mode == 2:
            self.saveForm.addDataFromSelected(asset)
            return

        if asset.status != 1:
            return
        if self.changesLost("Load character"):
            self.newCharacter(asset.filename, self.charselect.getExtraIndex())

    def savemhm_call(self):
        if self.glob.baseClass is not None:
            self.setToolModeAndPanel(0, 2)

    def exportmhm_call(self):
        if self.glob.baseClass is not None:
            self.setToolModeAndPanel(0, 3)

    def download_call(self):
        if self.glob.baseClass is not None:
            self.setToolModeAndPanel(0, 4)

    def initParams(self):
        self.graph.getFocusText()

    def reset_call(self):
        if self.glob.Targets is not None:
            if self.changesLost("Reset character"):
                print ("Reset")
                self.glob.Targets.reset(True)
                self.glob.project_changed = False
                self.redrawNewCategory(self.qtreefilter)
                self.glob.baseClass.applyAllTargets()
                self.graph.setSizeInfo()
                self.graph.view.Tweak()

    def symSwitch(self):
        self.scalerArray.comboUnexpand()
        v = not self.glob.Targets.getSym()
        self.glob.Targets.setSym(v)
        self.sender().setChecked(v)

    def symLToR(self):
        self.glob.Targets.makeSym(False)
        self.glob.baseClass.parApplyTargets()
        #self.graph.view.Tweak()

    def symRToL(self):
        self.glob.Targets.makeSym(True)
        self.glob.baseClass.parApplyTargets()
        #self.graph.view.Tweak()

    def loadNewClass(self, basename, filename=None):
        """
        :param str basename: the base name like 'hm08'
        :param str filename: the filename of the obj file
        """
        self.env.logLine(1, "New base " + basename + ", file:" + str(filename))

        base = baseClass(self.glob, basename)
        okay = base.prepareClass()
        if not okay:
            ErrorBox(self.central_widget, self.env.last_error)
            return

        self.glob.openGLBlock = True
        self.graph.view.newMesh()
        self.createImageSelection()
        self.emptyLayout(self.ToolBox)
        vis = self.drawRightPanel()
        self.setPresets()
        self.visRightColumn.setVisible(vis)

        self.ToolBox.update()

        self.emptyLayout(self.LeftBox)
        self.drawLeftPanel()
        self.LeftBox.update()
        self.graph.setSizeInfo()

        self.graph.update()
        self.glob.openGLBlock = False
        self.markSelectedButtons(self.tool_buttons, self.tool_buttons[0])
        self.markSelectedButtons(self.category_buttons[0], self.category_buttons[0][0])

    def selectmesh_call(self):
        (base, filename) = self.baseSelector.getSelectedItem()
        if base is not None:
            #
            if base == self.env.basename:
                return
            if self.changesLost("New basemesh") == 0:
                return
            self.loadNewClass(base, filename)

    def redrawNewCategory(self, category, text=None):
        self.qtreefilter, text = self.qTree.getValidCategory(category, text)
        self.emptyLayout(self.ToolBox)
        self.drawMorphPanel(text)
        self.ToolBox.update()

    def redrawNewExpression(self, category, text=None):
        self.qtreefilter, text = self.qTree.getValidCategory(category, text)
        self.emptyLayout(self.ToolBox)
        self.drawExpressionPanel(text)
        self.ToolBox.update()

    def redrawNewPose(self, category, text=None):
        self.qtreefilter, text = self.qTree.getValidCategory(category, text)
        self.emptyLayout(self.ToolBox)
        self.drawPosePanel(text)
        self.ToolBox.update()

    def finished_bckproc(self):
        if self.prog_window is not None:
            self.prog_window.progress.close()
            self.prog_window = None
        QMessageBox.information(self, "Done!", self.bckproc.finishmsg)
        self.bckproc = None

    def compress_systargets(self):
        if self.glob.Targets is not None and self.bckproc is None:
            self.prog_window = MHBusyWindow("System targets", "compressing ...")
            self.prog_window.progress.forceShow()
            self.bckproc = WorkerThread(self.glob.Targets.saveBinaryTargets, 1)
            self.bckproc.finishmsg = "System targets had been compressed"
            self.bckproc.start()
            self.bckproc.finished.connect(self.finished_bckproc)

    def compress_usertargets(self):
        if self.glob.Targets is not None and self.bckproc is None:
            self.prog_window = MHBusyWindow("User targets", "compressing ...")
            self.prog_window.progress.forceShow()
            self.bckproc = WorkerThread(self.glob.Targets.saveBinaryTargets, 2)
            self.bckproc.finishmsg = "User targets had been compressed"
            self.bckproc.start()
            self.bckproc.finished.connect(self.finished_bckproc)

    def compressObjs(self, bckproc, *args):
        """
        compresses assets (either objects or mhclo)
        :param bck_proc: unused pointer to background process
        :param args: [0][0] True = system, False user
        """
        system = args[0][0]
        force = args[0][1]
        bc = self.glob.baseClass

        # first compress base itself
        #
        syspath =  bc.baseMesh.filename.startswith(self.env.path_sysdata)
        if syspath == system:
            (okay, err) = bc.baseMesh.exportBinary()
            if not okay:
                bckproc.finishmsg = err
                return

        elems_compressed = 0
        elems_untouched = 0
        for elem in self.glob.cachedInfo:

            if elem.folder in ["clothes", "eyebrows", "eyelashes", "eyes", "hair", "proxy", "teeth", "tongue"]:
                syspath = elem.path.startswith(self.env.path_sysdata)
                if syspath == system:
                    okay = False
                    if force or self.env.isSourceFileNewer(elem.mhbin_file, elem.path):
                        self.prog_window.setLabelText(elem.folder + ": create binary " + os.path.split(elem.path)[1])

                        attach = attachedAsset(self.glob, elem.folder)
                        (okay, err) = attach.mhcloToMHBin(elem.path)
                        if not okay:
                            bckproc.finishmsg = err
                            return
                        elems_compressed += 1
                    else:
                        elems_untouched += 1

        bckproc.finishmsg = "Binaries created: " + str(elems_compressed) + "\nEntries up-to-date before: " + str(elems_untouched)
        return

    def compressObjsWorker(self, system, force):
        if self.glob.baseClass is not None and self.bckproc is None:
            objects = "System Objects" if system else "User Objects"
            self.prog_window = MHBusyWindow(objects, "creating binaries ...")
            self.prog_window.progress.forceShow()
            self.bckproc = WorkerThread(self.compressObjs, system, force)
            self.bckproc.start()
            self.bckproc.finished.connect(self.finished_bckproc)

    def compress_sys3dobjs(self):
        self.compressObjsWorker(True, False)

    def compress_user3dobjs(self):
        self.compressObjsWorker(False, False)

    def regenerate_sys3dobjs(self):
        self.compressObjsWorker(True, True)

    def regenerate_user3dobjs(self):
        self.compressObjsWorker(False, True)

    def exportUserDB(self):
        if self.glob.baseClass is None:
            return
        directory = self.env.stdUserPath()
        freq = MHFileRequest(self.glob, "Database export for backup", "Json-files (*.json)", directory, save=".json")
        filename = freq.request()
        if filename is not None:
            if self.env.fileCache.exportUserInfo(filename):
                QMessageBox.information(self.central_widget, "Done!", "User database exported as " + filename)
            else:
                ErrorBox(self.central_widget, self.env.last_error)

    def importUserDB(self):
        if self.glob.baseClass is None:
            return
        directory = self.env.stdUserPath()
        freq = MHFileRequest(self.glob, "Database import to restore tags", "Json-files (*.json)", directory)
        filename = freq.request()
        if filename is not None:
            if self.env.fileCache.importUserInfo(filename):
                QMessageBox.information(self.central_widget, "Done!", "User database restored, please restart program.")
                #self.glob.rescanAssets()
                # TODO: better way?
            else:
                ErrorBox(self.central_widget, self.env.last_error)

    def url_info_call(self):
        """
        open an URL
        """
        s = self.sender().text()
        urlname = self.env.release_info["support_urls"][s]
        if urlname in self.env.release_info:
            QDesktopServices.openUrl(QUrl(self.env.release_info[urlname], QUrl.TolerantMode))

    def lic_call(self):
        """
        open a text box with license
        """
        name =  self.sender().text()
        if name == "License":
            licname = "makehuman_license.txt"
            boxname = "MakeHuman License"
            image = self.env.stdLogo()
        elif name == "Credits":
            licname = "credits.txt"
            boxname = "Credits"
            image = self.env.stdLogo()
        else:
            licname = name.lower() + "-license.txt"
            boxname = name + " License"
            image = None

        text = self.env.convertToRichFile(os.path.join(self.env.path_sysdata, "licenses", licname))
        TextBox(self, boxname, image, text)

    def dimskel_call(self):
        self.graph.view.scene.setDiamondSkeleton(self.sender().isChecked())

    def floor_call(self):
        self.graph.view.scene.setFloor(self.sender().isChecked())

    def socket_call(self):
        if self.sender().isChecked() and self.glob.apiSocket is None:
            self.glob.apiSocket = apiSocket(self.glob)
            self.glob.apiSocket.viewRedisplay.connect(self.socket_finish)
            self.glob.apiSocket.start()
        else:
            if self.glob.apiSocket is not None:
                self.glob.apiSocket.stopListening()
                self.glob.apiSocket.wait()
                self.glob.apiSocket = None

    def socket_finish(self):
        self.glob.Targets.setSkinDiffuseColor()
        self.graph.view.Tweak()

    def context_help(self, filename=None):
        if filename:
            path = os.path.join(self.env.path_sysdata, "help", "help-" + filename + ".txt")
        else:
            path = os.path.join(self.env.path_sysdata, "help",
                "help-" + str(self.tool_mode) + "-" + str(self.category_mode) + ".txt")
        try:
            with open(path) as f:
                text = f.read()
        except IOError as e:
            text = "Error: " + str(e)
        TextBox(self, "Context Help", None, text, modal=False)

    def nav_help(self):
        self.context_help("navigation")

    def fsys_help(self):
        self.context_help("filesystem")

    def vers_call(self):
        text = "Numpy: " + ".".join([str(x) for x in self.env.numpy_version]) + "<br>" + \
                "PyOpenGL: " + self.env.GL_Info + "<br>" + \
                "PySide6: " + ".".join([str(x) for x in self.env.QT_Info["version"]])
        image = self.env.stdLogo()
        TextBox(self, "Used library versions", image, text)

    def glinfo_call(self):
        deb = GLDebug(self.env.osindex)
        text = deb.getTextInfo()
        image = self.env.stdLogo()
        TextBox(self, "Local OpenGL Information", image, text)

    def quit_call(self, event=None):
        """
        save session (if desired)
        also make a check, when project was changed
        """
        if self.glob.closing is True:
            return

        confirmed =  self.changesLost("Exit program")
        if confirmed == 0:
            if isinstance(event,QCloseEvent):
                event.ignore()
                print ("Close event")
            return

        if self.graph is not None:
            self.graph.cleanUp()

        if self.glob.closing is False:
            self.glob.closing = True                # avoid double call by closeAllWindows
            s = self.env.session["mainwinsize"]

            geom = self.screen().availableGeometry() # avoid bigger values than screen size when saving
            s["w"] = min(self.width(), geom.width())
            s["h"] = min(self.height(), geom.height())

            self.env.saveSession()
            if self.glob.apiSocket is not None:
                self.glob.apiSocket.stopListening()
                self.glob.apiSocket.wait()
            self.env.cleanup()
            self.glob.app.closeAllWindows()
            self.glob.app.quit()
