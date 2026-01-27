"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MHPictSelectable
    * PictureButton
    * PicFlowLayout
    * PicSelectWidget
    * InformationBox
    * FilterTree
    * editBox
    * ImageSelection
"""
import sys
import typing
import os
from PySide6.QtCore import Qt, QPoint, QRect, QSize, QTimer, Signal, QEvent
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QStandardItemModel, QStandardItem

from PySide6.QtWidgets import (
        QWidget, QLayout, QLayoutItem, QStyle, QSizePolicy, QPushButton, QAbstractButton, QRadioButton, QCheckBox,
        QGroupBox, QVBoxLayout, QLabel, QLineEdit, QTreeView, QAbstractItemView, QScrollArea, QPlainTextEdit, QHBoxLayout,
        QComboBox
        )

from gui.materialwindow import MHMaterialSelect, MHAssetWindow
from gui.common import IconButton
from core.taglogic import tagLogic

class MHPictSelectable:
    def __init__(self, name: str, icon: str, filename: str, author: str, tags: list):
        self.name = name
        self.filename = filename
        self.author = author
        self.basename = os.path.split(filename)[1].lower()
        self.icon = icon
        self.newTags(tags)
        #
        # append filename, author and  name as tags as well
        #
        self.status = 0

    def newTags(self, tags):
        self.tags = tags if len(tags) > 0 and len(tags[0]) != 0 else []
        self.tags.append(self.name.lower())
        self.tags.append(self.basename)    # only name, not path
        if self.author is not None:
            self.tags.append(self.author.lower())

    def newIcon(self, icon):
        self.icon = icon

    def __str__(self):
        return('\n'.join("%s: %s" % item for item in vars(self).items()))

class PictureButton(QPushButton):
    """
    tri-state picture button
    holds state in asset.status to be be reachable from outside
    supports double click
    :param MHPictSelectable asset: asset to be shown (used for name)
    :param float scale: scale of the icon
    :param str emptyicon: name of the thumbfile when there is no thumb
    :param bool acceptdouble: double click action available
    """
    pressed = Signal()
    doubleclick = Signal()

    def __init__(self, asset: MHPictSelectable, scale, emptyicon, acceptdouble):

        self.asset = asset
        self.scale = scale
        self.acceptdouble = acceptdouble
        self.icon = None

        super().__init__()

        if self.acceptdouble:
            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.setInterval(250)
            self.timer.timeout.connect(self.timeout)
            self.doubleclick.connect(self.doubleclick_event)

        self.is_double = False
        self.is_click = True

        self.installEventFilter(self)

        if asset.icon is None:                 # will not be constant
            self.icon = emptyicon
            self.picture_added = False
        else:
            self.picture_added = True
            self.icon = asset.icon
        self.setCheckable(True)
        self.framecol  = (Qt.black, Qt.yellow, Qt.green)
        self.setToolTip(asset.name + "\n" + asset.basename)
        self.update()

    def update(self):
        self.picture = QPixmap(self.icon).scaled(self.scale,self.scale, Qt.AspectRatioMode.KeepAspectRatio)
        super().update()

    def setScale(self, scale):
        self.scale=scale
        self.update()

    def sizeHint(self):
        return self.picture.size()

    def eventFilter(self, obj, event):
        if not hasattr(event, "type"):
            return False

        if self.acceptdouble:

            if event.type() == QEvent.MouseButtonPress:
                if not self.timer.isActive():
                    self.timer.start()

                self.is_click = False
                if event.button() == Qt.LeftButton:
                    self.is_click = True

                return True

            elif event.type() == QEvent.MouseButtonDblClick:
                self.is_double = True
                return True

            return False
        else:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.pressed.emit()
                    return True
            return False

    def doubleclick_event(self):
        pass

    def timeout(self):
        if self.is_double:
            self.doubleclick.emit()
        else:
            if self.is_click:
                self.pressed.emit()

        self.is_double = False

    def paintEvent(self, e):
        if self.asset.status > 2:
            return

        painter = QPainter(self)
        if self.asset.status != 0:
            painter.setOpacity(1)
            painter.drawPixmap(0, 0, self.picture)
            pen = QPen()
            pen.setColor(self.framecol[self.asset.status])
            pen.setWidth(5)

            painter.setPen(pen)
            painter.drawRect(self.rect())
        else:
            painter.setOpacity(0.4)
            painter.drawPixmap(0, 0, self.picture)

        if self.picture_added is False:
            painter.setPen(Qt.black)
            painter.drawText(5, 15, self.asset.name)

        painter.end()

class PicFlowLayout(QLayout):
    """
    parent.selmode: multiple selection, will change refresh method
    """
    def __init__(self, parent, assets, callback, printinfo, margin: int=-1, hSpacing: int=-1, vSpacing: int=-1, doubleclick=False):

        super().__init__()
        self.itemList = list()
        self.wList = list()
        self.m_hSpace = hSpacing
        self.m_vSpace = vSpacing
        self.selmode = parent.selmode
        self.debug = parent.debug
        self.imagescale = parent.imagescale
        self.empty = parent.emptyIcon
        self.callback = callback
        self.printinfo = printinfo
        self.assetlist = assets
        self.doubleclick = doubleclick
        self.filter = None
        self.ruleset = None
        self.setContentsMargins(margin, margin, margin, margin)

    """
    def __del__(self):
        # copied for consistency, not sure this is needed or ever called
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)
    """

    def addItem(self, item: QLayoutItem):
        self.itemList.append(item)

    def addWidget(self, widget: QWidget):
        self.wList.append(widget)
        super().addWidget(widget)

    def removeAllWidgets(self):
        while ((child := self.takeAt(0)) != None):
            if child.widget() is not None:
                child.widget().deleteLater()
        self.itemList = list()
        self.wList = list()

    def refreshAllWidgets(self):
        for widget in self.wList:
            widget.update()

    def deselectAllWidgets(self):
        for widget in self.wList:
             widget.asset.status = 0
             widget.update()

    def horizontalSpacing(self) -> int:
        if self.m_hSpace >= 0:
            return self.m_hSpace
        else:
            return self.smartSpacing(QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self) -> int:
        if self.m_vSpace >= 0:
            return self.m_vSpace
        else:
            return self.smartSpacing(QStyle.PM_LayoutVerticalSpacing)

    def count(self) -> int:
        return len(self.itemList)

    def itemAt(self, index: int) -> typing.Union[QLayoutItem, None]:
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        else:
            return None

    def takeAt(self, index: int) -> typing.Union[QLayoutItem, None]:
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        else:
            return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def smartSpacing(self, pm: QStyle.PixelMetric) -> int:
        parent = self.parent()
        if not parent:
            return -1
        elif parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        else:
            return parent.spacing()

    def doLayout(self, rect: QRect, testOnly: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(+left, +top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.horizontalSpacing()
            if spaceX == -1:
                spaceX = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = self.verticalSpacing()
            if spaceY == -1:
                spaceY = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + bottom

    def singleClickAction(self):
        current = self.sender()
        self.debug(current.asset.name + " update")

        if current.asset.status == 0 or current.asset.status == 2:
            current.asset.status = 1
            if self.printinfo is not None:
                self.printinfo(current.asset)
        else:
            current.asset.status = 0
        self.callback(current.asset)
        self.refreshAllWidgets()

    def doubleClickAction(self):
        current = self.sender()
        if current.asset.status != 0:
            current.asset.status = 4
            self.debug(current.asset.name + " attach")
        else:
            if self.printinfo is not None:
                self.printinfo(current.asset)
            current.asset.status = 3
            self.debug(current.asset.name + " detach")

        # change cursor since that can take time
        #
        current.setCursor(Qt.WaitCursor)
        self.callback(current.asset)
        current.unsetCursor()
        self.refreshAllWidgets()

    def redisplayWidgets(self, ruleset=None, filtfunc=None):
        self.removeAllWidgets()
        self.populate(ruleset, filtfunc)

    def setImageScale(self, scale):
        self.imagescale = scale
        self.redisplayWidgets(self.ruleset, self.filter)

    def getSelected(self):
        for widget in self.wList:
            if widget.asset.status & 1:
                return(widget.asset)
        return(None)
    
    def newAssetList(self, assets):
        self.assetlist = assets
        
    def populate(self, ruleset, filtertext):
        """
        :assetlist: complete asset list to be considered
        :ruleset: list for comparison or None
        :param filtertext: additional filter text or None
        """
        if filtertext == "":
            filtertext = None

        self.filter = filtertext
        self.ruleset = ruleset

        for asset in self.assetlist:
            #
            # when ruleset in not empty or none check rules per base
    
            if ruleset is not None and bool(ruleset) == True :
                display = True
                for tagelem in asset.tags:
                    basedisplay = False
                    if ":" in tagelem:
                        [base, rest]= tagelem.split(":", 1)
                        if base in ruleset:
                            for rule in ruleset[base]:
                                #
                                # rule as a string is found

                                if rest.startswith(rule):
                                    basedisplay = True
                        else:
                            # no base tag given in rules
                            #
                            basedisplay = True
                    else:
                        # no ':' in tag, no test (should be for wildcards later)
                        #
                        basedisplay = True

                    # all bases form the summary
                    #
                    display = basedisplay & display

            else:
                display = True

            if filtertext is not None:
                fdisplay = False
                for tagelem in asset.tags:
                    if filtertext in tagelem:
                        fdisplay = True
                display = fdisplay & display

            # create the picture buttons which are left
            #
            if display:
                button = PictureButton(asset, self.imagescale, self.empty, self.doubleclick)
                button.pressed.connect(self.singleClickAction)
                if self.doubleclick:
                    button.doubleclick.connect(self.doubleClickAction)
                self.addWidget (button)

class PicSelectWidget(QWidget):
    """
    PicSelectWidget is a PicFlowLayout embedded in a QGroupBox with a QScrollArea
    addWidget will add a button to the PicFlowLayout
    :param parent: for empty image, selection-mode
    :param callback: function to call when clicked
    """
    def __init__(self, parent, assets, callback, printinfo, doubleclick=False):
        self.parent = parent
        self.layout = PicFlowLayout(parent, assets, callback, printinfo, doubleclick=doubleclick)
        super().__init__()

    def __del__(self):
        """
        this is a must, otherwise the widgets will use up complete memory
        avoid it while closing
        """
        if not self.parent.glob.closing:
            self.layout.removeAllWidgets()

    def refreshAllWidgets(self):
        self.layout.refreshAllWidgets()

    def deselectAllWidgets(self):
        self.layout.deselectAllWidgets()

    def populate(self, ruleset, filtertext):
        self.layout.populate(ruleset, filtertext)

    def getSelected(self):
        return(self.layout.getSelected())

    def addWidget(self, button):
        self.layout.addWidget (button)

    def setImageScale(self, scale):
        self.layout.setImageScale(scale)

    def redisplayWidgets(self):
        self.layout.redisplayWidgets()

class InformationBox(QWidget):
    def __init__(self, layout):
        super().__init__()
        self.layout = layout
        self.selectedName = QLabel("Name:\nAuthor:")
        self.layout.addWidget(self.selectedName)
        self.layout.addWidget(QLabel("Tags:"))
        self.tagbox = QPlainTextEdit()
        self.tagbox.setPlainText("")
        self.tagbox.setReadOnly(True)
        self.tagbox.setFixedHeight(120)
        self.layout.addWidget(self.tagbox)

    def setInformation(self, asset):
        self.selectedName.setText("Name: " + asset.name + "\n" + "Author: " + asset.author)
        self.tagbox.setPlainText("\n".join(l.replace(":", " \u23f5 ") for l in asset.tags)) # triangle as arrow

class FilterTree(QTreeView):

    def  __init__(self, assets, searchByFilterText, s_iconpath, u_iconpath):
        self.assets = assets
        self.searchByFilterText = searchByFilterText
        self.flowLayout = None
        self.s_iconpath = s_iconpath
        self.u_iconpath = u_iconpath
        self.shortcut = []
        self.shortcutbutton = []
        self.blockfilter = False

        super().__init__()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.model = QStandardItemModel()
        self.setHeaderHidden(True)
        self.setModel(self.model)
        self.setUniformRowHeights(True)
        self.setFirstColumnSpanned(1, self.rootIndex(), True)

    def setPicLayout(self, layout):
        self.flowLayout = layout

    def addTree(self, subtree, layer=None, base="", search=""):
        """
        recursively try to create a tree from definition, could change depending on structure
        """
        for elem in subtree:
            #
            # set base when layer is None, otherwise keep old one and create substring by appending layer
            find = elem.lower()
            if find == "shortcut":
                for subelem in subtree[elem]:
                    self.shortcut.append(subelem)
                continue
            if find in ( "translate", "guessname"):
                continue
            if base == "":
                substring = ""
                nbase = find
            else:
                nbase = base
                substring = find if search =="" else  search + ":" + find

            if type(elem) is dict:
                self.addTree(elem, layer, nbase, substring)
            else:
                child = QStandardItem(elem)
                if layer is None:
                    child.setSelectable(False)
                    self.model.appendRow([child])
                    child.searchbase = None
                    child.searchpattern = None
                else:
                    layer.appendRow([child])
                    child.searchbase = nbase
                    child.searchpattern = substring
                if type(subtree) is dict:
                    self.addTree(subtree[elem], child, nbase, substring)

    def markSelectedButtons(self, funcid):
        for elem in self.shortcutbutton:
            elem.setChecked(elem._funcid == funcid)

    def shortCutPressed(self):
        """
        create a ruleset by a macro from button, so for an icon lingerie one has:
            gender:female&slot:top:layer1:bra|slot:bottom:layer1:panties
        what creates:
            {'gender': ['female'], 'slot': ['top:layer1:bra', 'bottom:layer1:panties']}
        """
        funcid = self.sender()._funcid
        text = self.shortcut[funcid][1]
        print ("Shortcut pressed: " + text)
        andOps = text.split("&")
        ruleset = {}
        for aelem in andOps:
            orOps = aelem.split("|")
            for oelem in orOps:
                layers = oelem.split(":")
                if len(layers) > 1:
                    key = layers[0]
                    if key in ruleset:
                        ruleset[key].append(":".join(layers[1:]))
                    else:
                        ruleset[key] = [ ":".join(layers[1:]) ]

        self.clearSelection()
        self.blockfilter = True
        self.setSelectedByRuleset(ruleset)
        self.blockfilter = False
        self.markSelectedButtons(funcid)
        self.flowLayout.removeAllWidgets()
        self.flowLayout.populate(ruleset, "")


    def addShortCuts(self):
        numicons = len(self.shortcut)
        if numicons == 0:
            return None
        i_per_row = 7

        layout=QVBoxLayout() if numicons > i_per_row else None
        row=QHBoxLayout()
        cnt = 0
        for funcid, elem in enumerate(self.shortcut):
            if elem[0].startswith("u:"):
                path = os.path.join(self.u_iconpath, elem[0][2:])
            else:
                path = os.path.join(self.s_iconpath, elem[0])
            button = IconButton(funcid, path, elem[2], self.shortCutPressed, checkable=True)
            row.addWidget(button)
            self.shortcutbutton.append(button)
            cnt += 1
            if cnt == i_per_row and layout is not None:
                row.addStretch()
                layout.addLayout(row)
                row =QHBoxLayout()
                cnt = 0
        if cnt != 0:
            row.addStretch()
            if layout is not None:
                layout.addLayout(row)

        return ( layout if numicons > i_per_row else row)

    def setSelectedByRuleset(self, ruleset, root=None):
        if root is None:
            root = self.model.invisibleRootItem()
            base = None
        else:
            base = root.searchbase
        if root.hasChildren():
            for index in range (root.rowCount()):
                child = root.child(index,0)
                if base is None:
                    base = child.searchbase
                if base is not None:
                    # must match base:
                    if base in ruleset:
                        if child.searchpattern in ruleset[base]:
                            cindex = self.model.indexFromItem(child)
                            self.setCurrentIndex(cindex)

                self.setSelectedByRuleset(ruleset, child)

    def removeAllFilters(self):
        """
        enable clearing of filter when entry field is cleared or all other filter are cleared
        """
        self.blockfilter = True
        self.clearSelection()
        self.blockfilter = False
        self.filterChanged()


    def filterChanged(self):
        """
        create a ruleset from selected items and repopulate the flow-Layout
        blocking must be used not to call filter 5 times for same menu
        """
        if self.flowLayout is None or self.blockfilter is True:
            return

        self.blockfilter = True
        ruleset = {}
        for ix in self.selectedIndexes():
            item = self.model.itemFromIndex(ix)
            base = item.searchbase
            if base not in ruleset:
                ruleset[base] = []
            ruleset[base].append(item.searchpattern)
        filtertext = self.searchByFilterText.text().lower()
        self.markSelectedButtons(-1)
        self.flowLayout.removeAllWidgets()
        self.flowLayout.populate(ruleset, filtertext)
        self.blockfilter = False

class editBox(QLineEdit):
    def  __init__(self, slayout, sweep):
        super().__init__()
        self.changeFilter = None
        self.empty = IconButton(0, sweep, "Clear filter", self.clearEditBox)
        slayout.addWidget(QLabel("Filter:"))
        slayout.addWidget(self)
        slayout.addStretch()
        slayout.addWidget(self.empty)
        self.setMaximumWidth(170)
        self.setFixedWidth(190)

    def addConnect(self, changeFilter, removeAllFilters):
        """
        connect functions to change the filter
        :param changeFilter: function to get a new filter
        :param removeAllFilters: function to remove all filters
        """
        self.changeFilter = changeFilter
        self.removeAllFilters = removeAllFilters
        self.returnPressed.connect(changeFilter)

    def clearEditBox(self):
        self.clear()
        if self.removeAllFilters is not None:
            self.removeAllFilters()

class ImageSelection():
    """
    class ImageSelection consists of left and right panel, display filter on left side and images on right side
    when an icon is selected, callback ist called.
    """
    def __init__(self, parent, assetrepo, eqtype, selmode, callback, scale=2, doubleclick=False):
        self.parent = parent
        self.env = parent.glob.env
        self.glob = parent.glob
        self.assetrepo = assetrepo
        self.type = eqtype
        self.selmode = selmode
        self.callback = callback
        self.infobox = None
        self.taglogic = None
        self.filterjson = None
        self.picwidget = None
        self.filterview = None
        self.scales = [48, 64, 96, 128]
        self.emptyIcon = os.path.join(self.env.path_sysdata, "icons", "empty_" + self.type + ".png")
        self.scaleindex = scale
        self.imagescale = self.scales[scale]
        self.rightpanelbuttons = []
        self.button_none = None
        self.button_info = None
        self.button_add = None
        self.button_delete = None
        self.button_mat = None
        self.extra_selection = None
        self.doubleclick = doubleclick

        if not os.path.isfile(self.emptyIcon):
            self.emptyIcon = os.path.join(self.env.path_sysdata, "icons", "noidea.png")

    def debug(self, text):
        self.env.logLine(2, "ImageSelection: " + text)

    def prepareRepo(self):
        self.asset_category = []
        for elem in self.assetrepo:
            if elem.folder == self.type:
                elem.tag = self.taglogic.completeTags(elem.name, elem.tag)
                self.asset_category.append(MHPictSelectable(elem.name, elem.thumbfile, elem.path,  elem.author, elem.tag))

    def prepare(self):
        """
        load filter from file according to base mesh and type, the filter in user folder can replace system folder
        then create an asset-category repo for this folder and convert it by taglogic
        """
        path = self.env.stdUserPath(self.type, "selection_filter.json")
        self.filterjson = self.env.readJSON(path)
        if self.filterjson is None:
            path = self.env.stdSysPath(self.type, "selection_filter.json")
            self.filterjson = self.env.readJSON(path)
            if self.filterjson is None:
                self.filterjson =  {}

        self.taglogic = tagLogic(self.filterjson)
        self.taglogic.create()
        self.prepareRepo()

    def getTagProposals(self):
        return(self.taglogic.proposals())

    def changeStatus(self):
        checked = []
        for elem in self.assetrepo:
            if elem.folder == self.type and elem.used is True:
                checked.append(elem.path)

        on = 2 if self.selmode == 1 else 1

        for elem in self.asset_category:
            elem.status = 2 if elem.filename in checked else 0

    def picButtonChanged(self, selectable):
        multi = (self.selmode == 1)
        # print ("picButtonChanged, Selectable status", selectable.status)

        if selectable.status == 0:

            # deselect
            #
            found = self.parent.glob.baseClass.getAttachedByFilename(selectable.filename)
            if multi is True:
                selectable.status = 2 if found is not None else 0
            else:
                if found:
                    self.callback(selectable, self.type, multi)

        elif selectable.status == 1:

            # yellow, preselected
            #
            self.materialCallback(update=True)
            self.assetCallback(selectable=selectable, update=True)

            # set all yellow ones back to green or nothing
            #
            self.changeStatus()
            selectable.status = 1
            self.picwidget.refreshAllWidgets()

        elif selectable.status == 3:

            # double click, change status to 1 and add asset
            #
            selectable.status = 1
            self.callback(selectable, self.type, multi)
            self.changeStatus()
            selectable.status = 1
            self.picwidget.refreshAllWidgets()

        elif selectable.status == 4:

            # double click, change status to 0 and delete asset
            #
            selectable.status = 0
            self.callback(selectable, self.type, multi)


        self.refreshButtons()

        if self.type == "models":
            if self.button_add is None:
                self.debug("Models. add is none")
                self.callback(selectable, self.type, False)

    def scaleImages(self):
        # toggle through 4 scales
        self.scaleindex = (self.scaleindex + 1) % 4
        self.imagescale = self.scales[self.scaleindex]
        self.picwidget.setImageScale(self.imagescale)

    def rescanFolder(self):
        """
        rescan folder:
        - get new assetrepo (only for type)
        - remove widgets
        - prepare new Repo (tags), send new repo and populate widget
        """
        self.assetrepo = self.parent.glob.rescanAssets(self.type)
        self.picwidget.layout.removeAllWidgets()
        self.parent.glob.baseClass.markAllAttachedAssets()
        self.prepareRepo()
        self.picwidget.layout.newAssetList(self.asset_category)
        self.picwidget.populate(None, None)
        self.changeStatus()

    def getSelectFromAttachedAssets(self):
        selected = self.picwidget.getSelected()
        if selected is not None:
            elem = self.parent.glob.baseClass.getAttachedByFilename(selected.filename)
            if elem is not None:
                return(elem, selected)

        return(None, None)

    def getSelectedFromRepo(self):
        selected = self.picwidget.getSelected()
        if selected is not None:
            elem = self.parent.glob.getAssetByFilename(selected.filename)
            if elem is not None:
                return(elem, selected)
        return(None, None)

    def loadCallback(self):
        (elem, asset) = self.getSelectedFromRepo()
        multi = (self.selmode == 1)
        self.callback(asset, self.type, multi)
        self.changeStatus()
        asset.status = 1
        self.refreshButtons()
        self.picwidget.refreshAllWidgets()

    def deleteCallback(self):
        (elem, asset) = self.getSelectedFromRepo()
        if asset is None:
            return
        asset.status = 0
        multi = (self.selmode == 1)
        self.callback(asset, self.type, multi)
        self.changeStatus()
        self.refreshButtons()
        self.picwidget.refreshAllWidgets()

    def noneCallback(self):
        (elem, asset) = self.getSelectedFromRepo()
        multi = (self.selmode == 1)
        if multi is True:
            names = []
            for elem in self.parent.glob.baseClass.attachedAssets:
                if elem.type == self.type:
                    names.append(elem.filename)

            for name in names:
                self.callback(name, self.type, multi)  # for clothes all clothes
        else:
            if asset is None:
                return
            self.debug("noneCallback, " + asset.filename)
            asset.status = 0
            self.callback(asset, self.type, multi)
        self.refreshButtons()
        self.picwidget.deselectAllWidgets()

    def materialCallback(self, status=False, update=False):
        """
        status is internal from PushButton
        """

        # without window visible no update
        #
        mw = self.glob.getSubwindow("material")
        if update and (mw is None or mw.isVisible() is False):
            return

        found, dummy = self.getSelectFromAttachedAssets()
        if found is None:
            if mw is not None and mw.isVisible():
                mw.updateWidgets([], None)
            return

        matimg = []
        oldmaterial = self.env.formatPath(found.material)
        matfiles = found.obj.listAllMaterials()
        for elem in matfiles:
            elem = self.env.formatPath(elem)
            (folder, name) = os.path.split(elem)

            thumb = elem[:-6] + ".thumb"
            if not os.path.isfile(thumb):
                # second guess in parent folder
                #
                (folder, dummy) = os.path.split(found.obj.filename)
                thumb = os.path.join(folder, name[:-6] + ".thumb")

                if not os.path.isfile(thumb):
                    thumb = None

            p = MHPictSelectable(name[:-6], thumb, elem, None, [])
            if elem == oldmaterial:
                p.status = 1
            matimg.append(p)

        if mw is None:
            mw = self.glob.showSubwindow("material", self.parent, MHMaterialSelect, PicSelectWidget, matimg, found)
        else:
            mw.updateWidgets(matimg, found)
            mw.show()
        mw.activateWindow()

    def changeTags(self, asset, iconpath):
        for elem in self.asset_category:
            if elem.filename == asset.path:
                newtags= self.taglogic.completeTags(elem.name, asset.tags)
                elem.newTags(newtags)
                self.infobox.setInformation(elem)
                if iconpath is not None:
                    elem.newIcon(iconpath)
                    self.picwidget.setImageScale(self.imagescale)

    def assetCallback(self, status=False, update=False, selectable=None):
        """
        function creates a subwindow with asset information, it is called by:
        * info button (with a status), no update and no selectable, in this case the selectable is evaluated
        * by changing icons with an update function and 'selectable' which is able to search directlly

        changing icons does not open a window, in case it was not open
        when asset is not found, asset editor is blank
        """

        mw = self.glob.getSubwindow("asset")
        if update and (mw is None or mw.isVisible() is False):                  # update without window
            return

        if selectable is None:
            asset, dummy  = self.getSelectedFromRepo()                          # called by button
        else:
            asset = self.parent.glob.getAssetByFilename(selectable.filename)    # called by icon

        if asset is None:
            if mw is not None and mw.isVisible():
                mw.updateWidgets(None, self.emptyIcon)  # blank window
                mw.show()
            return

        # get a new window or update current one
        #
        if mw is None:
            mw = self.glob.showSubwindow("asset", self.parent, MHAssetWindow, self.changeTags, asset, self.emptyIcon, self.taglogic.proposals())
            mw.activateWindow()
        else:
            mw.updateWidgets(asset, self.emptyIcon, self.taglogic.proposals())
            mw.show()


    def leftPanel(self, extra=None):
        """
        leftPanel is always called before rightPanel
        """
        # system icons are found in e.g. clothes/icons
        # user icons in clothes/<mesh>/icons

        s_iconpath = os.path.join(self.env.path_sysdata, self.type, "icons")
        u_iconpath = os.path.join(self.env.stdUserPath(self.type), "icons")
        
        v1layout = QVBoxLayout()    # this is for searching
        if extra is not None:
            self.extra_selection = QComboBox()
            self.extra_selection.addItems(extra)
            v1layout.addWidget(self.extra_selection)

        self.infobox = InformationBox(v1layout)

        slayout = QHBoxLayout()  # layout for textbox + empty button
        filteredit = editBox(slayout, os.path.join(self.env.path_sysicon, "sweep.png" ))
        self.filterview = FilterTree(self.asset_category, filteredit, s_iconpath, u_iconpath)
        self.filterview.addTree(self.filterjson)
        self.filterview.selectionModel().selectionChanged.connect(self.filterview.filterChanged)
        shortcuts = self.filterview.addShortCuts()
        filteredit.addConnect(self.filterview.filterChanged, self.filterview.removeAllFilters)

        v1layout.addWidget(self.filterview)
        if shortcuts is not None:
            v1layout.addLayout(shortcuts)
        v1layout.addLayout(slayout)

        return(v1layout)

    def getExtraIndex(self):
        return self.extra_selection.currentIndex() if self.extra_selection is not None else 0

    def rightPanelButtons(self, bitmask):
        hlayout = QHBoxLayout()
        yellow1 = " (click on asset, yellow frame must be visible)"
        yellow2 = " (click on asset, yellow frame must be visible and asset must be added)"

        if bitmask & 4:
            path = os.path.join(self.env.path_sysicon, "use.png" )
            self.button_add = IconButton(0, path, "Load/Use asset" + yellow1, self.loadCallback)
            hlayout.addWidget(self.button_add )
        else:
            self.button_add = None

        if bitmask & 8:
            if self.selmode == 1:
                path = os.path.join(self.env.path_sysicon, "none.png" )
                self.button_none = IconButton(0, path, "Drop all assets", self.noneCallback)
                hlayout.addWidget(self.button_none)

            path = os.path.join(self.env.path_sysicon, "delete.png" )
            self.button_delete = IconButton(0, path, "Drop this asset" + yellow2, self.deleteCallback)
            hlayout.addWidget(self.button_delete)
        else:
            self.button_none = None
            self.button_delete = None

        if bitmask & 1:
            path = os.path.join(self.env.path_sysicon, "information.png" )
            self.button_info = IconButton(0, path, "Change asset information" + yellow1, self.assetCallback)
            hlayout.addWidget(self.button_info )
        else:
            self.button_info = None

        if bitmask & 2:
            path = os.path.join(self.env.path_sysicon, "materials.png" )
            self.button_mat = IconButton(0, path, "Change material" + yellow2, self.materialCallback)
            hlayout.addWidget(self.button_mat)
        else:
            self.button_mat = None

        hlayout.addStretch()

        resize = os.path.join(self.env.path_sysicon, "resize.png" )
        sizebutton = IconButton(0, resize, "Resize thumbnails", self.scaleImages)
        hlayout.addWidget(sizebutton)

        rescan = os.path.join(self.env.path_sysicon, "rescan.png" )
        rescanbutton = IconButton(0, rescan, "Rescan folder", self.rescanFolder)
        hlayout.addWidget(rescanbutton)

        return (hlayout)

    def refreshButtons(self):

        # none button: enabled when one asset is supplied
        #
        if self.button_none:
            cnt = self.parent.glob.baseClass.countAttachedByType(self.type)
            self.button_none.setEnabled(cnt != 0)

        # must be yellow (selected) for add and info
        #
        selected = self.picwidget.getSelected()
        if self.button_info:
            self.button_info.setEnabled(selected is not None)

        # must be selected and supplied for delete, material
        # reuse selected

        if self.selmode == 1:
            if self.button_add:
                self.button_add.setEnabled(selected is not None)

        used = False
        if selected is not None:
            if self.parent.glob.baseClass.isLinkedByFilename(selected.filename) is not None:
                used  = True

        if self.selmode == 0:
            if self.button_add:
                self.button_add.setEnabled((selected is not None)  and not used)

        if self.button_delete:
            self.button_delete.setEnabled(used)

        if self.button_mat:
            self.button_mat.setEnabled(used)


    def rightPanel(self, bitmask=3):
        """
        draw right Panel
        """
        layout = QVBoxLayout()
        layout.addLayout(self.rightPanelButtons(bitmask))

        widget = QWidget()
        infocallback = self.infobox.setInformation if self.infobox is not None else None
        self.picwidget = PicSelectWidget(self, self.asset_category, self.picButtonChanged, infocallback, doubleclick=self.doubleclick)
        if infocallback is not None:
            self.filterview.setPicLayout(self.picwidget.layout)
        self.picwidget.populate(None, None)
        self.changeStatus()
        widget.setLayout(self.picwidget.layout)
        scrollArea = QScrollArea()
        scrollArea.setWidget(widget)
        scrollArea.setWidgetResizable(True)
        scrollArea.setHorizontalScrollBarPolicy( Qt.ScrollBarAlwaysOff )
        layout.addWidget(scrollArea)
        (elem, asset) = self.getSelectedFromRepo()
        self.refreshButtons()
        return(layout)

