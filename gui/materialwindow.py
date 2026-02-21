"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MHMaterialSelect
    * MHAssetWindow
"""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QCheckBox, QSizePolicy, QScrollArea, 
        QPlainTextEdit
        )
from PySide6.QtGui import QPixmap
from obj3d.object3d import object3d
from gui.common import MHTagEdit, IconButton
from gui.materialeditor import MHMaterialEditor


class MHMaterialSelect(QWidget):
    """
    select materials
    """
    def __init__(self, parent, PicSelectWidget, materials, asset):
        super().__init__()
        self.parent = parent
        self.debug = parent.debug
        self.env = parent.env
        self.glob = parent.glob
        self.materials = materials
        self.oldmaterial = asset.material
        self.asset = asset

        self.setWindowTitle("Material Selection")
        self.resize(360, 500)

        layout = QVBoxLayout()
        self.selmode = 0
        self.imagescale = 128
        self.emptyIcon = os.path.join(self.env.path_sysdata, "icons", "noidea.png")

        self.picwidget = PicSelectWidget(self, materials, self.picButtonChanged, None)
        self.picwidget.populate(None, None)
        widget = QWidget()
        widget.setLayout(self.picwidget.layout)
        scrollArea = QScrollArea()
        scrollArea.setWidget(widget)
        scrollArea.setWidgetResizable(True)
        scrollArea.setHorizontalScrollBarPolicy( Qt.ScrollBarAlwaysOff )
        layout.addWidget(scrollArea)

        hlayout = QHBoxLayout()
        usebutton = QPushButton("Use")
        usebutton.clicked.connect(self.use_call)
        hlayout.addWidget(usebutton)
        editbutton = QPushButton("Edit")
        editbutton.clicked.connect(self.edit_call)
        hlayout.addWidget(editbutton)
        layout.addLayout(hlayout)
        self.setLayout(layout)


    def picButtonChanged(self, matelem):
        if matelem.status == 1:

            if matelem.filename != self.oldmaterial:
                obj = self.asset.obj

                self.asset.material = matelem.filename
                self.asset.materialsource = self.env.relMatFileName(matelem.filename, obj.type)

                obj.newMaterial(matelem.filename)
                #
                # TODO: atm only changing material

                obj.openGL.setMaterial(obj.material)
                self.glob.openGLWindow.Tweak()
                self.oldmaterial = matelem.filename

        self.picwidget.layout.deselectAllWidgets()
        matelem.status = 1
        self.picwidget.layout.refreshAllWidgets()

    def updateWidgets(self, materials, asset):
        self.materials = materials
        self.asset = asset
        self.picwidget.layout.removeAllWidgets()
        if asset is not None:
            self.oldmaterial = asset.material
            self.picwidget.layout.newAssetList(materials)
            self.picwidget.populate(None, None)

    def use_call(self):
        self.close()

    def edit_call(self):
        if isinstance(self.asset, object3d):
            obj = self.asset
        else:
            obj = self.asset.obj

        mw = self.glob.showSubwindow("materialedit", self.parent, MHMaterialEditor, obj)
        mw.updateWidgets(obj)
        mw.activateWindow()
        self.close()

class MHAssetWindow(QWidget):
    """
    AssetWindow
    """
    def __init__(self, parent, changefunc, asset, empty, proposals=[]):
        super().__init__()
        self.parent = parent
        self.changefunc = changefunc
        self.env = parent.env
        self.glob = parent.glob
        self.asset = asset
        self.view = self.parent.graph.view
        self.emptyIcon = empty
        self.matPath = None
        self.icon = None
        self.thumb = asset.thumbfile
        self.origtags = ""
        self.origlist = []
        self.owntags = []

        self.currentMatPath(asset.path)

        layout = QVBoxLayout()
        self.nameLabel = QLabel()
        self.setName()
        layout.addWidget(self.nameLabel)

        # photo
        #
        ilayout = QHBoxLayout()
        ilayout.addWidget(IconButton(1,  os.path.join(self.env.path_sysicon, "camera.png"), "Thumbnail", self.thumbnail))
        self.imglabel=QLabel()
        self.displayPixmap()
        ilayout.addWidget(self.imglabel, alignment=Qt.AlignRight)
        layout.addLayout(ilayout)

        self.setWindowTitle("Asset Editor")
        self.resize(360, 500)
        self.tagsFromDB()

        layout.addWidget(QLabel("Original tags:"))
        self.tagbox = QPlainTextEdit()
        self.tagbox.setPlainText(self.origtags)
        self.tagbox.setReadOnly(True)

        layout.addWidget(self.tagbox)

        self.tagedit = MHTagEdit(self.glob, self.owntags, "Use own tags:", copyfrom=self.origlist, predefined = proposals)
        layout.addLayout(self.tagedit)

        hlayout = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.use_call)
        hlayout.addWidget(save)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.cancel_call)
        hlayout.addWidget(cancel)

        layout.addLayout(hlayout)
        self.setLayout(layout)

    def guessThumbNailPath(self):
        """
        calculate thumbnail path and evaluate if it already exists
        fallback is the asset-path, otherwise a material path is used
        eyes always use the materialpath
        """

        # calculate fallback
        #
        assetthumb, extension = os.path.splitext(self.asset.path)
        assetthumb += ".thumb"

        # special for eyes
        #
        if self.asset.folder == "eyes":
            if self.matPath.endswith(".mhmat"):
                matthumb = self.matPath[:-6] + ".thumb"
                return matthumb, True
            return assetthumb, False

        # now for all others check if available
        #
        if self.matPath is not None and self.matPath.endswith(".mhmat"):
            matthumb = self.matPath[:-6] + ".thumb"
            print ("looking for", matthumb)

            # check thumb
            if not os.path.isfile(matthumb):
                guess = os.path.basename(matthumb)

                if self.asset.thumbfile is None:
                    return assetthumb, False

                orig  = os.path.basename(self.asset.thumbfile)

                # this should avoid two icons for standard material
                #
                if guess == orig:
                    return self.asset.thumbfile, True

                return matthumb, False

            return matthumb, True

        # if thumbfile is there, use it
        #
        if self.asset.thumbfile is not None:
            return self.asset.thumbfile, os.path.isfile(self.asset.thumbfile)

        # otherwise use assetpath
        #
        return assetthumb, False

    def displayPixmap(self):
        """
        calculate expected path first
        """
        self.thumb, exists = self.guessThumbNailPath()

        # always add the (expected) path name as a tool tip
        #
        tooltip = "no icon" if self.thumb is None else self.thumb
        if self.icon is None:
            if not exists:
                pixmap = QPixmap(self.emptyIcon)
            else:
                pixmap = QPixmap(self.thumb)
        else:
            pixmap = QPixmap.fromImage(self.icon)
        self.imglabel.setPixmap(pixmap)
        self.imglabel.setToolTip(tooltip)

    def thumbnail(self):
        self.icon = self.view.createThumbnail()
        self.displayPixmap()

    def setName(self):
        name = self.asset.name if self.asset is not None else "none"
        if self.matPath is not None:
            self.nameLabel.setText("Name: " + name + "\nMaterial: " +  os.path.basename(self.matPath))
        else:
            self.nameLabel.setText("Name: " + name)

    def tagsFromDB(self):
        rows = self.env.fileCache.getEditParamInfo(self.asset.uuid)
        self.origtags = ""
        for row in rows:
            self.origlist = row[0].split("|")
            self.origtags= "\n".join(self.origlist)

        rows = self.env.fileCache.getEditParamUser(self.asset.uuid)
        self.owntags = []
        for row in rows:
            self.owntags =row[0].split("|")

    def currentMatPath(self, filename):
        #
        # special case for proxy first, proxies have no own material
        #
        if self.asset.folder == "proxy":
            self.matPath = None
            return

        attached = self.glob.baseClass.getAttachedByFilename(filename)
        if attached is not None:
            self.matPath = attached.obj.getMaterialFilename()
        else:
            self.matPath = None

    def updateWidgets(self, asset, empty, proposals=[]):
        self.asset = asset
        self.emptyIcon = empty
        self.currentMatPath(asset.path)
        self.icon = None
        if asset is None:
            self.origtags = ""
            self.tagedit.clearTags()
            self.thumb = None
        else:
            self.tagsFromDB()
            self.tagedit.newTags(self.owntags, self.origlist)
            self.thumb = asset.thumbfile
        self.tagedit.newPredefinedTags(proposals)
        self.setName()
        self.tagbox.setPlainText(self.origtags)
        self.displayPixmap()

        self.currentMatPath(asset.path)

    def use_call(self):
        """
        asset is None: nothing should be done
        skins are only saving a new icon
        materials are using the material path
        """
        if self.asset is None:
            self.close()
            return

        newtags = self.tagedit.getTags()
        if len(newtags) == 0:
            print ("Delete own entry")
            self.env.fileCache.deleteParamUser(self.asset.uuid)
            self.asset.tags = self.origlist
        else:
            insert = "|".join(newtags)
            self.env.fileCache.insertParamUser(self.asset.uuid, insert)
            self.asset.tags = newtags
        iconpath = None
        if self.icon is not None:
            #
            # decide if material path
            iconpath = self.thumb
            self.env.logLine(8, "Save icon as " + iconpath)
            self.icon.save(iconpath, "PNG", -1)

            # only update database when object icon was changed (not material)
            #
            if self.matPath is None:
                self.env.fileCache.updateParamInfo(self.asset.uuid, iconpath)
        if self.matPath is None:
            self.changefunc(self.asset, iconpath)

        self.close()

    def cancel_call(self):
        self.close()

