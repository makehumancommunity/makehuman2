"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Function:
    * ErrorBox
    * HintBox

    Classes:
    * clickableProgressBar
    * IconButton
    * MHGroupBox
    * MHTagEdit
    * WorkerThread
    * DialogBox
    * MHProgWindow
    * MHBusyWindow
    * MHFileRequest
    * TextBox
    * ImageBox
"""

import os
import time
from PySide6.QtWidgets import (
        QLabel, QDialogButtonBox, QVBoxLayout, QDialog, QProgressDialog, QWidget, QApplication, QMessageBox, QFrame,
        QHBoxLayout, QLineEdit, QPushButton, QComboBox, QProgressBar, QScrollArea, QFileDialog
        )
from PySide6.QtGui import QIcon, QPixmap, QFontMetrics, QImage
from PySide6.QtCore import Qt, QThread, Signal, QSize

def ErrorBox(qw, text):
    box = QMessageBox.critical(qw, "An error occured!", text, buttons=QMessageBox.Close)
    QMessageBox()

def HintBox(qw, text):
    box = QMessageBox.information(qw, "Information", text, buttons=QMessageBox.Close)
    QMessageBox()

class clickableProgressBar(QProgressBar):
    """
    progressBar which is clicked can be use to open an active slider
    """
    def __init__(self, callback, parent=None):
        self.callback = callback
        QProgressBar.__init__(self, parent)

    def mousePressEvent(self, event):
        self.callback()

class IconButton(QPushButton):
    def __init__(self, funcid, path, tip, func, fsize=36, checkable=False):
        self._funcid = funcid
        icon  = QIcon(path)
        super().__init__()
        self.setIcon(icon)
        self.setIconSize(QSize(fsize,fsize))
        self.setCheckable(checkable)
        self.setFixedSize(fsize+4,fsize+4)
        self.setToolTip(tip)
        if func is not None:
            self.clicked.connect(func)

    def newIcon(self, path):
        icon  = QIcon(path)
        self.setIcon(icon)

class MHGroupBox(QFrame):
    def __init__(self, title):
        super().__init__()
        self.vlabel = QLabel(title)
        self.vlabel.setObjectName("groupbox")
        self.vlabel.setAlignment( Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.setObjectName("groupbox")

    def MHLayout(self, parentlayout):
        self.setLayout(parentlayout)
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.vlabel)
        layout.addWidget(self)
        return(layout)

    def setTitle(self, title):
        self.vlabel.setText(title)


class MHTagEdit(QVBoxLayout):
    def __init__(self, glob, tags, label, numtags=5, copyfrom=None, predefined=None):
        super().__init__()
        self.edittags = tags
        self.sourcetags = copyfrom
        self.numtags = numtags
        self.setSpacing(0)

        ilayout = QHBoxLayout()
        ilayout.setSpacing(2)
        ilayout.addWidget(QLabel(label))
        sweep = os.path.join(glob.env.path_sysicon, "sweep.png")
        clearbutton = IconButton(0, sweep, "Clear own tags", self.clearTags)

        if copyfrom is not None:
            copy = os.path.join(glob.env.path_sysicon, "redo.png")
            copybutton = IconButton(0, copy, "Copy tags from original asset", self.copyTags)
            ilayout.addWidget(copybutton)

        ilayout.addWidget(clearbutton)
        self.addLayout(ilayout)

        if predefined is not None:
            ilayout = QHBoxLayout()
            ilayout.setSpacing(2)
            self.combobox = QComboBox()
            self.combobox.addItems(predefined)
            ilayout.addWidget(self.combobox)
            plus = os.path.join(glob.env.path_sysicon, "plus.png")
            plusbutton = IconButton(0, plus, "Add predefined tag to own tags", self.addPredefinedTag)
            ilayout.addWidget(plusbutton)
            self.addLayout(ilayout)
        else:
            self.combobox = None

        self.tags  = []
        for l in range(self.numtags):
            self.tags.append(QLineEdit())
            self.tags[l].editingFinished.connect(self.reorderTags)
            self.addWidget(self.tags[l])
        self.displayTags()

    def newPredefinedTags(self, predefined):
        if self.combobox is not None:
            self.combobox.clear()
            self.combobox.addItems(predefined)

    def displayTags(self):
        for l in range(self.numtags):
            tag = self.edittags[l] if l < len(self.edittags) else ""
            self.tags[l].setText(tag)

    def copyTags(self):
        self.edittags=self.sourcetags
        self.displayTags()

    def clearTags(self):
        self.edittags=[]
        for l in range(self.numtags):
            self.tags[l].clear()

    def reorderTags(self):
        self.edittags=[]
        for l in range(self.numtags):
            text = self.tags[l].text()
            if len(text):
                self.edittags.append(text)
        self.displayTags()

    def newTags(self, tags, copyfrom):
        self.edittags = tags
        if copyfrom is not None:
            self.sourcetags = copyfrom
        self.displayTags()

    def addPredefinedTag(self):
        newtag = self.combobox.currentText()
        if newtag not in self.edittags and len(self.edittags) < self.numtags:
            newtag = newtag.split(":")[-1] if ":" in newtag else newtag
            self.edittags.append(newtag)
            self.displayTags()

    def getTags(self):
        return(self.edittags)

class WorkerThread(QThread):
    update_progress = Signal(int)

    def __init__(self, function, *args):
        super().__init__()
        self.mh_function = function
        self.mh_args = args
        self.finishmsg = "Background process completed"

    def run(self):
        self.mh_function(self, self.mh_args)

class DialogBox(QDialog):
    def __init__(self, question, button):
        super().__init__()

        self.setWindowTitle("Dialog")

        QBtn = button | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        message = QLabel(question)
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

class MHProgWindow():
    """
    Progress Window to display progress, more or less a wrapper of
    QProgressDialog
    """
    def __init__(self, title, maximum):
        self.progress = QProgressDialog("started", None, 0, maximum, None)
        self.progress.setWindowTitle(title)
        self.progress.setMinimumWidth(600)
        self.progress.setMinimumDuration(500)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setAttribute(Qt.WA_DeleteOnClose, True)

    def setValueAndText(self, l, text):
        self.progress.setValue(l)
        self.progress.setLabelText(text)

    def setValue(self, l):
        self.progress.setValue(l)

    def setLabelText(self, text):
        self.progress.setLabelText(text)

    def setMaximum(self, l):
        self.progress.setMaximum(l)


class MHBusyWindow(QWidget):
    """
    a small busy window
    """
    def __init__(self, title, text):
        self.progress = QProgressDialog(text, None, 0, 0, None)
        self.progress.setWindowTitle(title)
        self.progress.setMinimumWidth(600)
        self.progress.setMinimumDuration(200)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setAttribute(Qt.WA_DeleteOnClose, True)

    def setLabelText(self, text):
        time.sleep(0.1)     # to avoid blocking (?)
        self.progress.setLabelText(text)

    def setValue(self, l):
        self.progress.setValue(l)

class MHFileRequest(QFileDialog):
    def __init__(self, glob, ftext, pattern, directory, save=None):
        super(MHFileRequest, self).__init__()
        self.save = save
        self.glob = glob

        if pattern is not None:
            self.setNameFilters([pattern, "Any files (*)"])

        if directory is not None:
            self.setDirectory(directory)

        if self.save is None:
            self.setWindowTitle("Load " + str(ftext) + " file")
            self.setFileMode(QFileDialog.FileMode.ExistingFile)
            self.setAcceptMode(QFileDialog.AcceptOpen)
        elif self.save == ".":
            self.setWindowTitle(str(ftext))
            self.setFileMode(QFileDialog.Directory)
            self.setOption(QFileDialog.ShowDirsOnly)
            self.setAcceptMode(QFileDialog.AcceptOpen)
            self.save = None
        else:
            self.setWindowTitle("Save " + str(ftext) + " file")
            self.setFileMode(QFileDialog.FileMode.AnyFile)
            self.setAcceptMode(QFileDialog.AcceptSave)

    def request(self):
        self.glob.openGLWinUpdate = False
        success = self.exec()
        self.glob.openGLWinUpdate = True
        if success:
            filename = self.selectedFiles()[0]

            if self.save is not None:
                # add suffix for save (security check for overwriting is done by request)
                #
                if not filename.endswith(self.save):
                    filename += self.save
            return(filename)
        return (None)


class TextBox(QDialog):
    """
    for e.g. presentation of license or OpenGL info, text is selectable
    no close buttons etc. to avoid bad window error onClose with normal window button
    """
    def __init__(self, parent, title, image, text, modal=True):
        super(TextBox, self).__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        textframe = QLabel(self)
        textframe.setTextInteractionFlags(Qt.TextSelectableByMouse)
        textframe.setWordWrap(True)
        fm = QFontMetrics(textframe.font())
        minwidth = fm.horizontalAdvance("#") * 80

        textframe.setText(text)
        textframe.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        textframe.setStyleSheet("font: 11pt;") # TODO make that flexible?
        textframe.setOpenExternalLinks(True)
        textframe.setTextFormat(Qt.RichText)

        scroll = QScrollArea(self)
        scroll.setWidget(textframe)
        scroll.setWidgetResizable(True)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        buttonBox.accepted.connect(self.close)
        buttonBox.button(QDialogButtonBox.Ok).setDefault(True)

        layout = QVBoxLayout()
        if image is not None:
            imglabel = QLabel()
            imglabel.setPixmap(QPixmap(image))
            layout.addWidget(imglabel)
        layout.addWidget(scroll)
        layout.addWidget(buttonBox)

        self.setLayout(layout)
        if modal:
            self.setWindowModality(Qt.WindowModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMinimumWidth(minwidth)
        self.show()

class ImageBox(QDialog):
    """
    for e.g. presentation of a downloaded render
    """
    def __init__(self, parent, title, image, winframe=True, color=None):
        super(ImageBox, self).__init__(parent)
        self.setWindowTitle(title)
        if isinstance(image, str):
            image = QImage(image)

        size = image.size()
        w = size.width()
        h = size.height()
        scrollbars = (w > 1024) or (h > 768)

        if winframe is False or not scrollbars:
            self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        else:
            self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        buttonBox.accepted.connect(self.close)
        buttonBox.button(QDialogButtonBox.Ok).setDefault(True)

        layout = QVBoxLayout()
        imglabel = QLabel()
        if color is not None:
            col = hex((int(color.x() * 256) <<16) +  (int(color.y() * 256) <<8) + int(color.z() *256))[2:]
            imglabel.setStyleSheet("background-color: #" + col + ";")
        imglabel.setPixmap(QPixmap.fromImage(image))

        if scrollbars:
            scroll = QScrollArea(self)
            scroll.setWidget(imglabel)
            scroll.setWidgetResizable(True)

            layout.addWidget(scroll)
            offset = 50
            w = 1024 if w > 1024-offset else w+offset
            h = 768 if h > 768-offset else h+offset
            self.setMinimumWidth(w)
            self.setMinimumHeight(h)
        else:
            layout.addWidget(imglabel)
        layout.addWidget( buttonBox)

        self.setLayout(layout)
        self.setWindowModality(Qt.WindowModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.show()
