"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * PreWindow
    * FirstStart
"""

from gui.common import  MHFileRequest, IconButton
from core.environ import  UserEnvironment

from PySide6.QtWidgets import QApplication, QWidget, QLineEdit, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize, Qt

import os

class PreWindow(QMainWindow):
    def __init__(self, osindex, proposal, syspath, results):
        super().__init__()

        fileicon = os.path.join(syspath, "data", "icons", "files.png")
        mh128icon = os.path.join(syspath, "data", "icons", "makehuman2logo128.png")
        self.setWindowTitle("MakeHuman II, Post-Installation")
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.old_homepath = proposal
        self.osindex = osindex
        self.syspath = syspath
        self.results = results
        olayout = QVBoxLayout()
        olayout.setSpacing(20)
        layout = QHBoxLayout()
        imglabel = QLabel()
        imglabel.setPixmap(QPixmap(mh128icon))
        layout.addWidget(imglabel)

        layout.addWidget(QLabel("""
To create a user configuration file, this post-installer needs additional information.
All other preferences may be set later in the program.

Enter the name of your personal folder, which should be used for assets, downloads and files.
Hint: The top folder will always be 'makehuman2'.
        """))
        olayout.addLayout(layout)
        layout = QHBoxLayout()
        self.ql_path_home = QLineEdit(proposal)
        self.ql_path_home.setToolTip('must be different to ' + syspath)
        self.ql_path_home.editingFinished.connect(self.testHomePath)
        self.folderbutton = IconButton(0, fileicon, "Select user folder.", self.selectUserFolder)
        layout.addWidget(self.folderbutton)
        layout.addWidget(self.ql_path_home)
        olayout.addLayout(layout)

        layout = QHBoxLayout()
        abort = QPushButton("Abort")
        abort.clicked.connect(self.abortCall)
        continueb = QPushButton("Save")
        continueb.clicked.connect(self.continueCall)
        layout.addWidget(abort)
        layout.addWidget(continueb)
        olayout.addLayout(layout)

        central_widget = QWidget()
        central_widget.setLayout(olayout)
        self.setCentralWidget(central_widget)

    def abortCall(self):
        self.close()

    def continueCall(self):
        self.results.append(self.old_homepath)
        self.close()

    def fullPath(self, path: str) -> str:
        if self.osindex == 0:
            path = os.path.normcase(path)
        return os.path.expanduser(os.path.normpath(path).replace("\\", "/"))

    def selectUserFolder(self):
        folder = self.old_homepath
        freq = MHFileRequest(None, "Select export folder", None, folder, save=".")
        name = freq.request()
        if name is not None:
            self.testHomePath(name)

    def testHomePath(self, name=None):
        """
        test the pathname, it should not be equal to installation path and longer than 3
        """
        if name is None:
            name = self.ql_path_home.text()
        up = self.fullPath(name)
        sp = self.fullPath(self.syspath)
        if sp == up or len(up) < 3:
            up = self.old_homepath
        if not up.endswith("makehuman2"):
            up = os.path.join(up, "makehuman2")
        self.old_homepath = up
        self.ql_path_home.setText(up)


class FirstStart():
    def __init__(self, syspath):
        self.syspath = syspath
        self.uenv = UserEnvironment()
        self.osindex = self.uenv.getPlatform()[1]
        self.conffile = self.uenv.getUserConfigFilenames(None, True)[0]

    def createConffile(self):
        if os.path.isfile(self.conffile):
            return 0, self.conffile + " exists"

        proposal = self.uenv.getHomePathProposal()
        style = os.path.join(self.syspath,"data", "themes", "makehuman.qss")

        app = QApplication([])

        with open(style, "r") as fh:
            app.setStyleSheet(fh.read())

        results = []
        window = PreWindow(self.osindex, proposal, self.syspath, results)
        window.show()

        app.exec_()
        app.shutdown()      # undocumented

        if len(results) == 0:
            return 2, "Program aborted, nothing changed."

        if self.uenv.writeDefaultConf(self.conffile, results[0]) is False:
            return 21, "Cannot create " + self.conffile
        return 1, "Created: " + self.conffile



