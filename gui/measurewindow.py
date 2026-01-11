"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MHCharMeasWindow

"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QPushButton, QGridLayout
from PySide6.QtGui import QColor

class MHCharMeasWindow(QWidget):
    """
    Message window for logfiles and errors
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.glob = parent.glob
        self.env = parent.env
        self.setWindowTitle("Character Measurement")
        self.measures = {}
        self.values = {}
        self.maxm = 0
        self.eucups = ['AA', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O']
        self.ukcups = ['AA', 'A', 'B', 'C', 'D', 'DD', 'E', 'F', 'FF', 'G', 'GG', 'H', 'HH', 'J', 'JJ', 'K']

        self.resize (500, 600)
        layout = QVBoxLayout()

        self.glayout = QGridLayout()
        self.calculateTargets()
        layout.addLayout(self.glayout)

        hlayout = QHBoxLayout()
        rbutton = QPushButton("Redisplay")
        rbutton.clicked.connect(self.redisplay_call)
        hlayout.addWidget(rbutton)
        button = QPushButton("Close")
        button.clicked.connect(self.close_call)
        hlayout.addWidget(button)

        layout.addLayout(hlayout)
        self.setLayout(layout)

    def addOrReplace(self, val, name, text, tip=None):
        self.values[name] = val
        if name in self.measures:
            self.measures[name].setText(text)
        else:
            self.measures[name] = QLabel(text)
            if tip:
                self.measures[name].setToolTip(tip)
            self.glayout.addWidget(QLabel(name), self.maxm, 0)
            self.glayout.addWidget(self.measures[name], self.maxm, 1)
            self.maxm += 1

    def femaleSpecial(self):
        bratip = "Cup size will be displayed for female character with a minimum age of 8 years only.<br>The cup size is a letter, which is calculated by comparison of bust and underbust values.<br>"
        calcCM = "The number indicates the the best fitting band size (similar to underbust) in cm."
        calcIN = "The number indicates the the best fitting band size (similar to underbust) in inch."

        if "gender" in self.values and self.values["gender"] < 50.0 and "age" in self.values and self.values["age"] > 7:
            if "chest" in  self.values and "underbust" in self.values:
                bust = self.values["chest"] * 10
                underbust = self.values["underbust"] * 10

                mod = int(underbust)%5
                band = underbust - mod if mod < 2.5 else underbust - mod + 5
                eucup = min(max(0, int(round(((bust - underbust - 10) / 2)))), len(self.eucups)-1)
                text1 = str(round(band))+self.eucups[eucup]

                band = underbust * 0.393700787
                band = band + 5 if int(band)%2 else band + 4
                uscup = min(max(0, int(round((bust - underbust - 10) / 2))), len(self.eucups)-1)
                text2 = str(round(band))+self.eucups[uscup]
                ukcup = min(max(0, int(round((bust - underbust - 10) / 2))), len(self.ukcups)-1)
                text3 = str(round(band))+self.ukcups[ukcup]
            else:
                text1 = "undefined"
                text2 = "undefined"
                text3 = "undefined"
        else:
            text1 = "none"
            text2 = "none"
            text3 = "none"
        self.addOrReplace(0.0, "EU cup size", text1, bratip + calcCM)
        self.addOrReplace(0.0, "US cup size", text2, bratip + calcIN)
        self.addOrReplace(0.0, "UK cup size", text3, bratip + calcIN)

    def calculateTargets(self):
        bc = self.glob.baseClass
        bi = bc.baseInfo
        self.maxm = 0
        if "measure" in bi:
            m= bi["measure"]
            for name, key in m.items():
                if key in self.glob.targetRepo:
                    t = self.glob.targetRepo[key]
                    if t.measure:
                        val, coords = bc.baseMesh.getMeasure(t.measure)
                        text = self.env.toUnit(val)
                        self.addOrReplace(val, name, text)
                    elif name == "gender":
                        text = "female" if t.value < 50.0 else "male"  # simple formula
                        self.addOrReplace(t.value, name, text)
                    elif name == "age":
                        if t.virtual_value is not None:
                            val =  t.virtual_value
                        else:
                            val = t.value
                        text = str(val)
                        self.addOrReplace(val, name, text)
                elif name == "size":
                    val=bc.baseMesh.getHeightInUnits()
                    text = self.env.toUnit(val)
                    self.addOrReplace(val, name, text)
        self.femaleSpecial()

    def redisplay_call(self):
        self.calculateTargets()

    def close_call(self):
        self.close()

