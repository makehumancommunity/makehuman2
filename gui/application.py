"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MHApplication

    Functions:
    * QTVersion
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QScreen, QImageReader, QSurfaceFormat
from PySide6.QtCore import qVersion, QCoreApplication
import os

def QTVersion(uenv):
    qversion = {}
    qversion["version"] = [ int(x) for x in qVersion().split(".")]
    formats = [ s.data().decode(encoding='utf-8').lower() for s in QImageReader.supportedImageFormats() ]
    qversion["jpg_support"] = "jpg" in formats
    qversion["plugin_path"] = os.path.pathsep.join( [uenv.pathToUnicode(p) for p in QCoreApplication.libraryPaths()])
    qversion["plugin_path_env"] = uenv.pathToUnicode(os.environ['QT_PLUGIN_PATH'] if 'QT_PLUGIN_PATH' in os.environ else "")
    #
    # qt.conf is no longer tested (reason: other versions like qt6.conf etc. can be used
    #
    return (qversion)

class MHApplication(QApplication):
    """
    class to maintain QT parameters
    """
    def __init__(self, glob, argv):
        self.env = glob.env
        super().__init__(argv)

        # Alphacover (if available), is used to use more than one alpha-layer
        #
        self.sformat = QSurfaceFormat()
        if self.env.noalphacover is False:
            self.sformat.setSamples(4)
        self.sformat.setDefaultFormat(self.sformat)

    def getFormat(self):
        return self.sformat

    def setStyles(self, theme):
        if theme is None:
            return (False)
        try:
            with open(theme, "r") as fh:
                self.setStyleSheet(fh.read())
            return (True)
        except:
            self.env.last_error("cannot read " + theme)
            return (False)

    def getScreensize(self):
         return QScreen.availableGeometry(self.primaryScreen()).size().toTuple()

    def getCenter(self):
        return QScreen.availableGeometry(self.primaryScreen()).center()

    def topLeftCentered(self, widget):
        screen_center =  self.getCenter()
        geom = widget.frameGeometry()
        geom.moveCenter(screen_center)
        return(geom.topLeft())
