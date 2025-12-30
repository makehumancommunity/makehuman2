"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MapInputWidget
    * MapInputWidgetXY
    * MapInputWidgetBaryCentric
    * MapBaryCentricCombo
    * MapXYCombo
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QHBoxLayout, QVBoxLayout, QFrame
from PySide6.QtCore import Qt, QObject, QEvent, QPointF
from PySide6.QtGui import QPainter, QPainterPath, QPixmap, QPaintEvent, QPen, QBrush, QColor, QFont, QFontMetrics

class MapInputWidget(QFrame):
    def __init__(self, size, framewidth, info, initialValue, callback, displayfunc=None, drawcenter=False, ident=None):
        super().__init__()
        self.dimension = size
        self.info = info
        self.ident = ident
        self.displayfunc = displayfunc
        self.drawcenter = drawcenter
        self.callback = callback
        self.framewidth = framewidth
        self.canvassize = size + framewidth * 2
        self.setFixedSize(self.canvassize, self.canvassize)

        self.values= [ initialValue[0], initialValue[1]]

        self.x = self.dimension * initialValue[0]
        self.y = self.dimension * initialValue[1]

        # create pixmap and Pens for Mask and Cursor
        #
        self.colmask = QColor(0,0,0)
        colpen = QColor(0xd7801a)
        colback = QColor(0x414141)

        self.pixmap = QPixmap(self.size())
        self.pixmap.fill(colback)
        self.pen_c   = QPen(colpen, 10, Qt.SolidLine, Qt.RoundCap)
        self.pen_mid = QPen(self.colmask, 10, Qt.SolidLine, Qt.RoundCap)
        self.pen_m = QPen(self.colmask, self.framewidth, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
        if info:
            self.displayInfo()

    def getValues(self):
        return self.values

    def DrawMask(self, painter):
        pass

    def paintEvent(self, event: QPaintEvent):
        f = self.framewidth
        d = self.dimension

        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)

        painter.setPen(self.pen_m)
        painter.drawRect(f/2 , f/2, d+f, d+f)

        self.DrawMask(painter)

        if self.drawcenter:
            painter.setPen(self.pen_mid)
            center = d / 2 +f
            painter.drawPoint(center, center)

        painter.setPen(self.pen_c)
        painter.drawPoint(self.x + f, self.y + f)

        painter.end()

    def maskAndSetValues(self, x,y):
        """
        no mask in default case
        """
        self.values[0] = x / self.dimension
        self.values[1] = y / self.dimension
        return (x,y)

    def drawValues(self, x,y):
        self.maskAndSetValues(x,y)
        self.x = x
        self.y = y
        if self.info is not None:
            self.displayInfo()
        self.update()

    def displayInfo(self):
        x = self.values[0]
        y = self.values[1]
        if self.displayfunc is not None:
            self.info.setText(self.displayfunc(x,y))
        else:
            self.info.setText(f"X: {x:.2f}\nY: {y:.2f}")

    def mouseMoveEvent(self,event):
        f = self.framewidth
        d = self.dimension

        x = event.position().x()
        y = event.position().y()
        if x < f:
            x = f
        elif x > d+f:
            x =  d+f
        if y < f:
            y = f
        elif y > d+f:
            y =  d+f
        (self.x, self.y ) = self.maskAndSetValues(x-f, y-f)
        if self.info is not None:
            self.displayInfo()
        if self.callback is not None:
            if self.ident is None:
                self.callback()
            else:
                self.callback(self.ident)
        self.update()


class MapInputWidgetXY(MapInputWidget):
    def __init__(self, size, framewidth, info=None, initialValue=None, callback=None, displayfunc=None, drawcenter=False, ident=None):
        if initialValue is None:
            initialValue = [ 0.5, 0.5 ]
        super().__init__(size, framewidth, info, initialValue, callback, displayfunc, drawcenter, ident)

class MapInputWidgetBaryCentric(MapInputWidget):
    def __init__(self, size, framewidth, info=None, initialValue=None, texts=None, callback=None):
        self.barycentric = [ 1/3, 1/3, 1/3 ]
        if initialValue is not None:
            self.barycentric = initialValue

        self._baryTexts = [ "A", "B", "C" ]
        if texts is not None:
            self._baryTexts = texts

        (self.x, self.y) = self.toBaryCentric()
        self.font = QFont("helvetica",11)
        self.pen_t = QPen(QColor(0xffffff))
        fm = QFontMetrics(self.font)
        self._pix1 = fm.horizontalAdvance(self._baryTexts[0])
        self._pix2 = -5
        self._pix3 = fm.horizontalAdvance(self._baryTexts[2]) + 5
        super().__init__(size, framewidth, info, [self.x, self.y], callback)

    def getValues(self):
        return self.barycentric

    def toBaryCentric(self):
        v = self.barycentric
        x = 1 - v[0]/2 - v[1]
        y = v[1] + v[2]
        return (x,y)

    def maskAndSetValues(self, x,y):
        """
        additional mask for barycentric version
        simplified for the triangle x1/y1, x2/y2, x3/y3
        we are looking for the barycentric coordinates of x/y (xs/ys)
        which will be m1, m2, m3

        Algorithm:
        N = (x2-x1)*(y3-y2)-(y2-y1)*(x3-x2)
        m1= ((x2 - xs)*(y3-ys) - (x3-xs)*(y2-ys)) / N
        m2 = ((x3 - xs)*(y1-ys) - (x1-xs)*(y3-ys)) /N
        m3 = 1 -m1 -m2

        (the simplification results from a bunch of 0s and the symmetry of the triangle)
        we also do not accept values from outside the triangle (negative barycentric coordinates)

        return corrected coordinates and calculate barycentric value
        """
        d = self.dimension

        m1= 1 - y / d
        m3 = (0.5 * y + x )/d  - 0.5
        m2 = (0.5 * y - x )/d  + 0.5
        if m1 < 0:
            m1 = 0
        if m2 < 0:
            m2 = 0
        if m3 < 0:
            m3 = 0
            m2 = 1 -m1 -m3
        else:
            m3 = 1 -m1 -m2

        self.barycentric = [ m1, m2, m3]

        # correct the x/y value to stay in triangle
        #
        (x,y ) = self.toBaryCentric()
        return (x*d,y*d)

    def displayInfo(self):
        """
        Output in extra box if info is not None
        """
        t = self._baryTexts
        b = self.barycentric
        b1 = int (b[0] * 100)
        b2 = int (b[1] * 100)
        b3 = 100 - b1 - b2
        self.info.setText(f"{b1}% {t[0]}\n{b2}% {t[1]}\n{b3}% {t[2]}")

    def DrawMask(self, painter):
        """
        draw a triangle masks + texts
        """
        f = self.framewidth
        d = self.dimension
        path = QPainterPath()
        path.moveTo(d/2 + f, f)
        path.lineTo(f, f)
        path.lineTo(f, d+f)
        path.lineTo(d/2 + f, f)
        painter.fillPath(path, QBrush(self.colmask))
        path = QPainterPath()
        path.moveTo(d/2 + f, f)
        path.lineTo(f+d, f)
        path.lineTo(f+d, f+d)
        path.lineTo(d/2 + f, f)
        painter.fillPath(path, QBrush(self.colmask))

        painter.setFont(self.font)
        painter.setPen(self.pen_t)
        painter.drawText(QPointF(d/2 + f - self._pix1/2, f -5), self._baryTexts[0])
        painter.drawText(QPointF(5, d + 2 *f + self._pix2 ), self._baryTexts[1])
        painter.drawText(QPointF(self.canvassize-self._pix3, d + 2 *  f -5 ), self._baryTexts[2])


class MapBaryCentricCombo(QWidget):
    def __init__(self, initial, texts, callback, parent=None):
        super(MapBaryCentricCombo, self).__init__(parent=parent)

        self.info = QLabel(self)
        self.info.setGeometry(10, 10, 200, 50)
        self.info.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        hLayout = QHBoxLayout()
        self.mapBary = MapInputWidgetBaryCentric(100, 20, info=self.info, initialValue=initial, texts=texts, callback=callback)
        hLayout.addWidget(self.mapBary)
        hLayout.addWidget(self.info)
        self.setLayout(hLayout)

class MapXYCombo(QWidget):
    def __init__(self, initial, callback, parent=None, displayfunc=None, drawcenter=False, ident=None):
        super(MapXYCombo, self).__init__(parent=parent)

        self.info = QLabel(self)
        self.info.setGeometry(10, 10, 200, 50)
        self.info.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        hLayout = QHBoxLayout()
        self.mapInput = MapInputWidgetXY(100, 20, info=self.info, initialValue=initial, callback=callback, displayfunc=displayfunc, drawcenter=drawcenter, ident=ident)
        hLayout.addWidget(self.mapInput)
        hLayout.addWidget(self.info)
        self.setLayout(hLayout)

