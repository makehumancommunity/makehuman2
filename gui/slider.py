"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * NoModSlider
    * ScaleComboItem
    * ScalePictureButton
    * ScaleCombo
    * ScaleComboArray
    * SimpleSlider
    * ColorButton
"""

import os
import sys
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QPixmap, QPen, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSlider, QStyle, QStyleOptionSlider, QLabel, QPushButton,
    QSizePolicy, QDoubleSpinBox, QProgressBar, QFrame, QColorDialog
    )
from gui.mapslider import MapBaryCentricCombo
from gui.common import clickableProgressBar

class NoModSlider(QSlider):
    """
    this class of slider allows to use <modifier>-<cursor> to be used as shortcuts
    """
    def keyPressEvent(self, event):
        if event.modifiers():
            event.ignore()
        else:
            super().keyPressEvent(event)


class ScaleComboItem:
    def __init__(self, name, icon):
        self.name = name
        self.icon = icon
        self.tip  = "Select to modify"
        self.selected = False
        self.value = 0.0
        self.default = 0.0
        self.opposite = False # two.directional slider?
        self.displayname = name
        self.group = None

    def callback(self):
        print ("Empty Callback")

    def initialize(self):
        print ("Empty Init")

class ScalePictureButton(QPushButton):
    def __init__(self, name, icon, tip):
        self.icon = icon
        super().__init__(name)
        image = QPixmap(icon)
        self.setPicture(image)
        self.setCheckable(True)
        self.setMaximumSize(image.size())
        self.setToolTip(tip)

    def setPicture(self, icon):
        self.picture = icon
        self.update()

    def sizeHint(self):
        return self.picture.size()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.picture)

class ScaleCombo(QWidget):
    def __init__(self, elem, minimum, maximum, step=1, parent=None, update=None):
        super(ScaleCombo, self).__init__(parent=parent)

        self.parentUpdate = update
        self.resetIcon = parent.resetIcon
        i_units=range(minimum, maximum+step, step)
        self.units=list(zip(i_units,map(str,i_units)))

        self.minwidth = 200     # minimum width for expanded slider
        self.margin = 8
        self.min = minimum
        self.max = maximum
        self.step = step
        self.elem = elem
        self.expanded = False
        self.dSpinBox = None
        self.resetButton = None
        self.slider = None
        self.measure = elem.measure

        self.comboLayout=QVBoxLayout(self)

        if self.expanded:
            self.addExpandedFeatures()
        else:
            self.addNonExpandedFeatures()

        self.ilayout=QHBoxLayout()

        self.image = ScalePictureButton(elem.displayname, elem.icon, elem.tip)
        self.image.setChecked(self.expanded)
        self.image.pressed.connect(self.selectButtonPressed)
        self.ilayout.addWidget(self.image)

        self.label = QLabel(elem.displayname)
        self.rightCol = QVBoxLayout()
        self.rightCol.addWidget(self.label)
        if self.expanded:
            self.rightCol.addLayout(self.spinLayout)
        else:
            self.rightCol.addWidget(self.gvalue)

        self.ilayout.addLayout(self.rightCol)
        self.comboLayout.addLayout(self.ilayout)
        if self.expanded:
            self.comboLayout.addWidget(self.slider)

    def setMeasurement(self, text):
        if self.elem.measure is not None:
            self.label.setText(self.elem.displayname + "\n" + text)

    def addNonExpandedFeatures(self):
        """
        add progress bar as indicator
        """
        self.comboLayout.setContentsMargins(self.margin,0, self.margin,0 )
        self.gvalue = clickableProgressBar(self.selectButtonPressed)
        self.gvalue.setRange(self.min,self.max)
        self.gvalue.setValue(self.elem.value)
        self.gvalue.setMaximumHeight(15)
        self.gvalue.setFormat("%v")

    def addExpandedFeatures(self):
        """
        add double-spin box with reset button
        add slider
        """
        self.comboLayout.setContentsMargins(self.margin,self.margin, self.margin,self.margin +5)
        self.spinLayout = QHBoxLayout()
        self.dSpinBox = QDoubleSpinBox()
        self.dSpinBox.setRange(self.min, self.max)
        self.dSpinBox.setSingleStep(0.01)
        self.dSpinBox.setValue(self.elem.value)
        self.dSpinBox.valueChanged.connect(self.dspinValueChanged)
        self.resetButton = QPushButton()
        self.resetButton.setToolTip("Reset to default")
        self.resetButton.setIcon(self.resetIcon)
        self.resetButton.setMaximumWidth(30)
        self.resetButton.pressed.connect(self.resetButtonPressed)
        self.spinLayout.addWidget(self.dSpinBox)
        self.spinLayout.addWidget(self.resetButton)

        self.slider=NoModSlider(Qt.Horizontal, self)
        self.slider.setMinimum(self.min)
        self.slider.setMaximum(self.max)
        self.slider.setMinimumWidth(self.minwidth)
        self.slider.setValue(self.elem.value)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(self.step)
        self.slider.valueChanged.connect(self.sliderValueChanged)

    def sliderValueChanged(self):
        """
        change dspin-box and element  accordingly
        """
        value = self.slider.value()
        self.dSpinBox.setValue(value)
        self.elem.value = value

    def dspinValueChanged(self):
        """
        change slider and element accordingly 
        """
        value = self.dSpinBox.value()
        self.slider.setValue(value)
        self.elem.value = value
        self.elem.callback()

    def resetButtonPressed(self):
        """
        change sliders and element accordingly
        """
        self.elem.value = self.elem.default
        self.slider.setValue(self.elem.value)
        self.dSpinBox.setValue(self.elem.value)

    def selectButtonPressed(self):
        """
        call parent function to disable other buttons
        call initialize callback
        """
        self.parentUpdate(self)
        self.image.setChecked(not self.expanded)
        self.elem.initialize()

    def comboUpdate(self, expand):
        """
        called from combo array, sliders will be displayed
        or only progress bars according to expanded mode
        """
        if expand is False:
            self.dSpinBox.deleteLater()
            self.resetButton.deleteLater()
            self.spinLayout.deleteLater()
            self.slider.deleteLater()
            self.addNonExpandedFeatures()
            self.rightCol.addWidget(self.gvalue)
            self.expanded = False
            self.image.setChecked(self.expanded)
            self.elem.selected = False
        else:
            self.gvalue.deleteLater()
            self.addExpandedFeatures()
            self.rightCol.addLayout(self.spinLayout)
            self.comboLayout.addWidget(self.slider)
            self.expanded = True
            self.elem.selected = True

    def paintEvent(self, e):
        """
        avoid to paint it when expanded is false
        (could lead to race condition otherwise)
        """
        if self.expanded is False:
            return
        super(ScaleCombo,self).paintEvent(e)
        style=self.slider.style()
        st_slider=QStyleOptionSlider()
        st_slider.initFrom(self.slider)

        slength=style.pixelMetric(QStyle.PM_SliderLength, st_slider, self.slider) // 2
        available=style.pixelMetric(QStyle.PM_SliderSpaceAvailable, st_slider, self.slider)
        ypos=self.rect().bottom()

        painter=QPainter(self)

        for v, v_str in self.units:

            # get the size of the label
            rect=painter.drawText(QRect(), Qt.TextDontPrint, v_str)

            x_loc=QStyle.sliderPositionFromValue(self.min, self.max, v, available)+slength
            xpos=x_loc-rect.width()//2+self.margin

            pos=QPoint(xpos, ypos)
            painter.drawText(pos, v_str)

class ScaleComboArray(QWidget):
    """
    a slider array of all the elements in modelling
    """
    def __init__(self, mainwidget, modelling, filterparam,  sweep, parent=None):
        super(ScaleComboArray, self).__init__(parent=parent)
        self.layout=QVBoxLayout(self)
        self.scaleComboArray = []
        self.resetIcon = QIcon(sweep)
        cnt = 0
        for elem in modelling:
            if filterparam is None or elem.group == filterparam:

                # special case of barycentric slider first
                #
                if hasattr(elem, "barycentric") and elem.barycentric is not None:
                    texts = [d['text'] for d in elem.barycentric]
                    values = [d['value'] for d in elem.barycentric]

                    mapCombo = MapBaryCentricCombo(values, texts, elem.callback)
                    elem.slider = mapCombo.mapBary
                    self.layout.addWidget(mapCombo)
                    cnt +=1 
                    continue

                if elem.opposite is False:
                    scalecombo = ScaleCombo(elem,  0, 100, 10, parent=self, update=self.comboArrayUpdate)
                else:
                    scalecombo = ScaleCombo(elem,  -100, 100, 25, parent=self, update=self.comboArrayUpdate)

                elem.slider = scalecombo
                self.scaleComboArray.append(scalecombo)
                self.layout.addWidget(scalecombo)
                cnt +=1 
        if cnt == 0:
            text = QLabel(self)
            text.setFrameStyle(QFrame.Panel | QFrame.Sunken)
            text.setText("Still no targets realized\nselect another category")
            text.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(text)
        self.layout.addStretch()

    def comboUnexpand(self):
        for scalecombo in self.scaleComboArray:
            if scalecombo.expanded:
                scalecombo.comboUpdate(False)

    def comboArrayUpdate(self, current):
        """
        update all widgets
        """
        if current.expanded:
            current.comboUpdate(False)
        else:
            for elem in self.scaleComboArray:
                if elem != current and elem.expanded:
                    elem.comboUpdate(False)
            current.comboUpdate(True)

class SimpleSlider(QWidget):
    def __init__(self, labeltext, minimum, maximum, callback, parent=None, vertical=False, minwidth=159, ident=None, factor=1.0):
        super().__init__()
        self.labeltext = labeltext
        self.callback = callback
        self.info = QLabel(self)
        self.factor = factor
        self.ident = ident
        if vertical:
            layout = QHBoxLayout()
            layout.setSpacing(1)
            self.slider=NoModSlider(Qt.Vertical, self)
            layout.addWidget(self.slider)
            layout.addWidget(self.info)
            self.slider.setTickPosition(QSlider.TicksRight)
            self.slider.setTickInterval(10)
            self.slider.setMinimumHeight(120)
        else:
            layout = QVBoxLayout()
            layout.setSpacing(1)
            layout.addWidget(self.info)
            self.slider=NoModSlider(Qt.Horizontal, self)
            layout.addWidget(self.slider)
            self.slider.setTickPosition(QSlider.TicksBelow)
            self.slider.setTickInterval(10)
            self.slider.setMinimumWidth(minwidth)
            self.slider.setMaximumHeight(20)
            
        self.slider.setMinimum(minimum)
        self.slider.setMaximum(maximum)
        self.slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.slider.valueChanged.connect(self.sliderChanged)
        self.setLayout(layout)

    def setEnable(self, value):
        self.slider.setEnabled(value)

    def setInfoText(self, value):
        if self.factor == 1.0:
            self.info.setText(self.labeltext + str(round(value)))
        else:
            self.info.setText(self.labeltext + str(round(value) * self.factor))

    def sliderChanged(self):
        value = self.slider.value()
        self.setInfoText(value)
        if self.ident is None:
            self.callback(value * self.factor)
        else:
            self.callback(self.ident, value * self.factor)

    def setSliderValue(self, value):
        self.setInfoText(value)
        self.slider.setValue(value)

    def setLabelText(self, label):
        self.labeltext = label
        value = self.slider.value()
        self.setInfoText(value)

class ColorButton(QWidget):
    def __init__(self, glob, labeltext, callback, parent=None, horizontal=False, ident=None):
        super().__init__()
        self.labeltext = labeltext
        self.callback = callback
        self.ident = ident
        self.glob = glob
        self.info = QLabel(self)
        self.button = QPushButton()
        self.button.setFixedSize(80,20)
        self.button.clicked.connect(self.getColor)
        if horizontal:
            layout = QHBoxLayout()
        else:
            layout = QVBoxLayout()
        layout.setSpacing(1)
        layout.addWidget(self.info)
        layout.addWidget(self.button)
        layout.addStretch()
        self.setLayout(layout)

    def setInfoText(self, color):
        self.info.setText(self.labeltext + color.name())

    def setColorValue(self, color):
        self.setInfoText(color)
        self.button.setStyleSheet("background-color : " + color.name())

    def getColor(self):
        self.glob.openGLWinUpdate = False
        color = QColorDialog.getColor()
        self.glob.openGLWinUpdate = True
        self.setColorValue(color)
        if self.ident is None:
            self.callback(color)
        else:
            self.callback(self.ident, color)

