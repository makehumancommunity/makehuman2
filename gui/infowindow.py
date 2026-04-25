"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MHInfoWindow
"""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QScreen
import os

class MHInfoWindow(QWidget):
    """
    splash-window, borderless (mouseclick)
    resize splash image to 95% (MacOS 70%) of the smallest dimension of screen
    (usually height) if bigger than 95 (70) percent
    """
    def __init__(self, glob):
        super().__init__()
        self.glob = glob
        env = glob.env
        rel = env.release_info
        version = ".".join(str(l) for l in env.release_info["version"])
        suffix = " [" + env.release_info["suffix"] + "]" if env.release_info["suffix"] != "" else ""
        text = " ".join([rel["name"], suffix + "    Version:", version, "     Authors:", rel["author"]])
        title = QLabel(text)

        sw, sh = self.glob.app.getScreensize()
        factor = 0.7 if env.osindex == 2 else 0.95
        sw = int(sw * factor)
        sh = int(sh * factor)
        pixmap = QPixmap(os.path.join(env.path_sysicon,"splash.png"))
        pw, ph =  pixmap.size().toTuple()
        if  pw > sw or ph > sh:
            s = sh if sh < sw else sw
            pixmap = pixmap.scaled(s, s, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lbl = QLabel(self)
        lbl.setPixmap(pixmap)
        layout =QVBoxLayout(self)
        layout.addWidget(lbl)
        layout.addWidget(title)
        self.setLayout(layout)
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        #
        # display in screen center
        #
    def show(self):
        super().show()
        self.move(self.glob.app.topLeftCentered(self))

    def mousePressEvent(self, event):
        self.close()

