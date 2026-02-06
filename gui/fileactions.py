"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * BaseSelect
    * SaveMHMForm
"""
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QAbstractItemView, QLineEdit, QLabel,
    QMessageBox, QDialogButtonBox, QCheckBox, QGridLayout
    )

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from gui.imageselector import MHPictSelectable, PicSelectWidget
from gui.materialwindow import  MHMaterialSelect, MHAssetWindow
from gui.common import DialogBox, ErrorBox, IconButton, MHTagEdit
from core.globenv import cacheRepoEntry

import os

class BaseSelect(QVBoxLayout):
    """
    class to select a basemesh
    """
    def __init__(self, parent, callback):
        super().__init__()
        self.parent = parent
        self.glob = parent.glob
        self.env = parent.glob.env
        self.emptyIcon = os.path.join(self.env.path_sysdata, "icons", "empty_material.png")
        self.baseResultList = self.env.getDataDirList("base.obj", "base")

        if self.parent.glob.baseClass is None:
            self.addWidget(QLabel("<h1>Select a base mesh</h1>"))

        self.basewidget = QListWidget()
        self.basewidget.setFixedSize(240, 200)
        self.basewidget.addItems(self.baseResultList.keys())
        self.basewidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.basewidget.itemDoubleClicked.connect(callback)
        if self.env.basename is not None:
            items = self.basewidget.findItems(self.env.basename,Qt.MatchExactly)
            if len(items) > 0:
                self.basewidget.setCurrentItem(items[0])
        self.addWidget(self.basewidget)

        buttons = QPushButton("Select")
        buttons.clicked.connect(callback)
        self.addWidget(buttons)

        gb = QGroupBox("Base material")
        gb.setObjectName("subwindow")
        vlayout = QVBoxLayout()
        path = os.path.join(self.env.path_sysicon, "materials.png" )
        self.materialbutton = IconButton(0, path, "Set material of body (skin).", self.materialCallback)
        vlayout.addWidget(self.materialbutton)

        path = os.path.join(self.env.path_sysicon, "information.png" )
        self.infobutton = IconButton(0, path, "Change skin information", self.assetCallback)
        vlayout.addWidget(self.infobutton)
        self.activateButtons()

        gb.setLayout(vlayout)
        self.addWidget(gb)
        self.addStretch()

    def activateButtons(self):
        enabled = self.parent.glob.baseClass is not None
        self.materialbutton.setEnabled(enabled)
        self.infobutton.setEnabled(enabled)

    def getCurrentMaterial(self):
        return self.parent.glob.baseClass.skinMaterial
        
    def assetCallback(self):
        material = self.getCurrentMaterial()

        if material is None:
            ErrorBox(self.parent, "No materials available")
            return

        # get filename and thumb file, if any
        #
        (folder, name) = os.path.split(material)
        thumb = material[:-6] + ".thumb"
        if not os.path.isfile(thumb):
            thumb =  None

        # create a cacheRepoEntry for skins (there are no skins in repo currently)
        #
        asset = cacheRepoEntry("base", "internal", material, "skins", None, thumb, "makehuman", "")
        proposals = []

        mw = self.glob.getSubwindow("asset")
        if mw is None:
            #
            # called with "skins" there is no change function
            #
            mw = self.glob.showSubwindow("asset", self.parent,  MHAssetWindow, None, asset, self.emptyIcon, proposals)
        else:
            mw.updateWidgets(asset, self.emptyIcon, proposals)
            mw.show()
        mw.activateWindow()

    def materialCallback(self):
        p1 = self.env.stdUserPath("skins")
        p2 = self.env.stdSysPath("skins")
        baseClass = self.parent.glob.baseClass
        basemesh = baseClass.baseMesh
        matfiles = basemesh.material.listAllMaterials(p1)
        matfiles.extend(basemesh.material.listAllMaterials(p2))
        #
        # in case of proxy, change first asset
        # TODO: here skinMaterial seems not to be corrected
        #
        if baseClass.proxy:
            basemesh =  baseClass.attachedAssets[0]
        matimg = []
        oldmaterial = self.getCurrentMaterial()
        if oldmaterial:
            self.env.logLine(1, "Working on: " + oldmaterial)
        for elem in matfiles:
            #print (elem)
            (folder, name) = os.path.split(elem)
            thumb = elem[:-6] + ".thumb"
            if not os.path.isfile(thumb):
                thumb =  os.path.join(self.env.path_sysicon, "empty_material.png" )
            p = MHPictSelectable(name[:-6], thumb, elem, None, [])
            if elem == oldmaterial:
                p.status = 1
            matimg.append(p)

        mw = self.glob.getSubwindow("material")
        if mw is None:
            mw = self.glob.showSubwindow("material", self.parent, MHMaterialSelect, PicSelectWidget, matimg, basemesh)
        else:
            mw.updateWidgets(matimg, basemesh)
            mw.show()
        mw.activateWindow()


    def getSelectedItem(self):
        sel = self.basewidget.selectedItems()
        if len(sel) > 0:
            name = sel[0].text()
            return (name, self.baseResultList[name])

        return (None, None)


class SaveMHMForm(QVBoxLayout):
    """
    create a form with name, tags, uuid, thumbnail, filename
    """
    def __init__(self, parent, view, characterselection, displaytitle):
        self.view = view
        self.parent = parent
        self.glob = parent.glob
        env = self.glob.env
        self.bc  = self.glob.baseClass
        self.displaytitle = displaytitle
        super().__init__()

        # photo
        #
        ilayout = QHBoxLayout()
        ilayout.addWidget(IconButton(1,  os.path.join(env.path_sysicon, "camera.png"), "Thumbnail", self.thumbnail))
        self.imglabel=QLabel()
        self.displayPixmap()
        ilayout.addWidget(self.imglabel, alignment=Qt.AlignRight)
        self.addLayout(ilayout)

        # name and author
        #
        ilayout = QGridLayout()
        ilayout.addWidget(QLabel("Name:"), 0, 0)
        self.editname = QLineEdit(self.bc.name)
        self.editname.editingFinished.connect(self.newname)
        ilayout.addWidget(self.editname, 0, 1)

        ilayout.addWidget(QLabel("Author:"), 1, 0)
        self.authname = QLineEdit(self.bc.author)
        self.authname.editingFinished.connect(self.newauthor)
        ilayout.addWidget(self.authname, 1, 1)
        self.addLayout(ilayout)

        # uuid
        #
        ilayout = QHBoxLayout()
        ilayout.addWidget(QLabel("UUID:"))
        self.regenbutton=QPushButton("Generate UUID")
        self.regenbutton.clicked.connect(self.genuuid)
        ilayout.addWidget(self.regenbutton, alignment=Qt.AlignBottom)
        self.addLayout(ilayout)
        uuid = self.bc.uuid if hasattr(self.bc, "uuid") else ""
        self.uuid = QLineEdit(uuid)
        self.uuid.editingFinished.connect(self.newuuid)
        self.addWidget(self.uuid)

        # tags
        #
        self.tagedit = MHTagEdit(self.glob, self.bc.tags, "\nTags:",
                predefined= characterselection.getTagProposals())
        self.addLayout(self.tagedit)

        # filename
        #
        ilayout = QHBoxLayout()
        ilayout.addWidget(QLabel("Filename:"))
        self.filename = QLineEdit(self.bc.name + ".mhm")
        self.filename.editingFinished.connect(self.newfilename)
        ilayout.addWidget(self.filename)
        self.addLayout(ilayout)

        self.savebutton=QPushButton("Save")
        self.savebutton.clicked.connect(self.savefile)
        self.addWidget(self.savebutton)

    def savefile(self):
        """
        path calculation
        ask if is already exists
        save file, save icon
        """
        path = self.glob.env.stdUserPath("models", self.filename.text())
        self.bc.tags = self.tagedit.getTags()
        if os.path.isfile(path):
            dbox = DialogBox("Replace " + path + "?", QDialogButtonBox.Ok)
            confirmed = dbox.exec()
            if confirmed != 1:
                return

        if self.bc.saveMHMFile(path):
            QMessageBox.information(self.parent, "Done!", "Character saved as " + path)
        else:
            ErrorBox(self.parent, self.glob.env.last_error)
        if self.bc.photo is not None:
            iconpath = path[:-4] + ".thumb"
            self.bc.photo.save(iconpath, "PNG", -1)

    def newfilename(self):
        """
        not empty, always ends with mhm
        """
        text = self.filename.text()
        if len(text) == 0:
            text = self.editname.text()
        if not text.endswith(".mhm"):
            self.filename.setText(text + ".mhm")

    def newname(self):
        """
        when empty, then 'base', create filename in case of no filename available
        """
        text = self.editname.text()
        if len(text) == 0:
            self.editname.setText("base")

        self.bc.name = text
        self.displaytitle(text)
        if self.filename.text() == "":
            self.filename.setText(text + ".mhm")

    def newauthor(self):
        text = self.authname.text()
        if len(text) == 0:
            self.editname.setText("unknown")
        self.bc.author = text

    def genuuid(self):
        self.bc.uuid = self.glob.gen_uuid()
        self.uuid.setText(self.bc.uuid)

    def newuuid(self):
        self.bc.uuid = self.uuid.text()

    def displayPixmap(self):
        if self.bc.photo is None:
            pixmap = QPixmap(os.path.join(self.glob.env.path_sysicon, "empty_models.png"))
        else:
            pixmap = QPixmap.fromImage(self.bc.photo)
        self.imglabel.setPixmap(pixmap)

    def thumbnail(self):
        self.bc.photo = self.view.createThumbnail()
        self.displayPixmap()

    def addDataFromSelected(self, asset):
        """
        copies data from a selected asset to filename
        """
        self.filename.setText(asset.basename)
        self.editname.setText(asset.name)
        #
        # tags: last 3 tags are name, filename, author, tags with ';' only take last element
        #
        tags = []
        for elem in asset.tags[:-3]:
            if ":" in elem:
                elem = elem.split(":")[-1]
            tags.append(elem)
        self.tagedit.newTags(tags, None)

        # generate the icon from selected icon
        #
        if asset.icon is not None:
            pixmap = QPixmap(asset.icon)
            self.bc.photo = pixmap.toImage()
        else:
            self.bc.photo = None
        self.displayPixmap()

