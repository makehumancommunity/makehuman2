"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * TextureRepo
    * ImageEdit
    * MH_Texture
    * MH_Thumb
"""

from PySide6.QtOpenGL import QOpenGLTexture
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import QSize, Qt
import numpy as np
import os
from math import floor

class TextureRepo():
    """
    texture repo contains information about loaded textures
    key is the filename, values are: [ openGL texture, usage, filedate, mhtex ]
    if filedate is "0" it is a generated texture
    """
    def __init__(self, glob):
        self.glob = glob
        self.textures = {}
        self.systextures = {}

    def getTextures(self):
        return self.textures

    def show(self):
        for k, l in self.textures.items():
            s = ""
            for n in l[4]:
                if n is not None:
                    s = s + n.name + " "
                else:
                    s = s + "None "
            print (k, l[1], s)
        print()

    def add_sys(self, path, texture):
        self.systextures[path] = [texture]

    def add_user(self, path, texture, timestamp, mhtex, obj):
        if path not in self.textures:
            self.textures[path] = [texture, 1, timestamp, mhtex, [obj]]

    def exists(self, path):
        if path in self.textures:
            return self.textures[path][0]

    def inc(self, path, obj):
        if path in self.textures:
            self.textures[path][1] += 1
            self.textures[path][4].append(obj)

    def delete(self, texture, obj):
        """
        find texture path and check if obj is assigned
        if so, delete it and decrement counter
        """
        t = self.textures
        for elem in t:
            m = t[elem]
            if m[0] == texture:
                if obj in m[4]:
                    m[1] -= 1
                    m[4].remove(obj)
                if m[1] == 0:
                    m[0].destroy()
                    del t[elem]
                return

    def refresh(self):
        """
        refresh all textures (to load e.g. a skin under construction
        """
        for name, v in self.textures.items():
            # do not work with filedate 0 (means generated map)
            if v[2] != 0:
                if os.path.isfile(name):
                    timestamp = int(os.stat(name).st_mtime)
                    if timestamp > v[2]:
                        v[0] = v[3].refresh(name)
                        v[2] = timestamp
                else:
                    self.glob.env.logLine(1, name + " does not exist, no reload.")

    def cleanup(self, textype="user"):
        """
        central location to delete textures
        (systextures only by demand)
        """
        t = self.textures
        for elem in t:
            t[elem][0].destroy()

        self.textures = {}

        if textype == "system":
            t = self.systextures
            for elem in t:
                t[elem][0].destroy()




class ImageEdit():
    def __init__(self, glob):
        self.glob = glob

    def modifyToConstantHue(self, image, r, g, b):
        ptr = image.bits()
        mlen = image.width() * image.height()
        myarray = np.ndarray((mlen, 4), buffer=ptr, dtype=np.uint8)

        qcol = QColor()
        qcol.setRgbF(r,g,b)
        hue = qcol.getHsv()[0]   # get "h" from given color in degrees

        nrgb = myarray[:,:3].astype('float') / 256

        # keep value and saturation
        #
        value = np.max(nrgb,1)
        ndelta = value - np.min(nrgb,1)

        # hue is -1 if r, g, b are identical
        #
        if hue == -1:
            sat = np.zeros(mlen)
            hue_index = 0
            p = value
            q = value
            t = value
        else:
            np.seterr(all='ignore')
            sat = np.where(value == 0.0, 0.0, ndelta / value)
            np.seterr(all='print')
            hue60 = hue / 60.0
            hue_index = floor(hue60) % 6
            hue_diff = hue60 - np.floor(hue60)
            p = value * (1.0 - sat)
            q = value * (1.0 - (hue_diff * sat))
            t = value * (1.0 - ((1.0 - hue_diff) * sat))

        if hue_index == 0:
            rgb = np.dstack((p, t, value))
        elif hue_index == 1:
            rgb = np.dstack((p, value, q))
        elif hue_index == 2:
            rgb = np.dstack((t, value, p))
        elif hue_index == 3:
            rgb = np.dstack((value, q, p))
        elif hue_index == 4:
            rgb = np.dstack((value, p, t))
        else:
            rgb = np.dstack((q, p, value))
        myarray[:,:3] = rgb * 256


    def noColor(self, image):
        self.modifyToConstantHue(image, 1.0, 1.0, 1.0)


    def multColor(self, image, r, g, b):
        ptr = image.bits()
        mult = np.array([b, g, r, 1], dtype=np.float32)
        mlen = image.width() * image.height()
        myarray = np.ndarray((mlen, 4), buffer=ptr, dtype=np.uint8)
        myarray2 = myarray.astype(np.float32, copy=True)
        myarray2 *= mult
        myarray[:] = myarray2.astype(np.uint8)[:]

    def greyToColor(self, image, r, g, b):
        self.noColor(image)
        self.multColor(image, r, g, b)

class MH_Texture():
    def __init__(self, glob, textype="user", obj=None):
        self.glob = glob
        self.obj = obj
        self.repo = glob.textureRepo
        self.textype = textype
        self.texture = QOpenGLTexture(QOpenGLTexture.Target2D)

    def create(self, name, image):
        """
        :param image: QImage
        :param name: image path, used in repo to identify object
        """
        self.texture.create()
        self.texture.setData(image)
        self.texture.setMinMagFilters(QOpenGLTexture.Linear, QOpenGLTexture.Linear)
        self.texture.setWrapMode(QOpenGLTexture.ClampToEdge)

        return self.texture

    def destroy(self):
        self.texture.destroy()

    def delete(self):
        if self.textype == "user":
            self.repo.delete(self.texture, self.obj)

    def unicolor(self, rgb = [0.5, 0.5, 0.5]):
        color = QColor.fromRgbF(rgb[0], rgb[1], rgb[2])
        name = "Generated color [" + hex(color.rgb()) + "]"
        texture = self.repo.exists(name)
        if texture is not None:
            self.repo.inc(name, self.obj)
            self.texture = texture
            return texture

        image = QImage(QSize(1,1),QImage.Format_ARGB32)
        image.fill(color)
        self.texture = self.create(name, image)
        if self.textype == "system":
            self.repo.add_sys(name, self.texture)
        else:
            self.repo.add_user(name, self.texture, 0, None, self.obj)
        return self.texture

    def load(self, path, textype="user", modify=True):
        """
        load textures
        """
        if textype == "user":
            texture = self.repo.exists(path)
            if texture is not None:
                if modify:
                    self.repo.inc(path, self.obj)
                self.texture = texture
                return texture

        if not os.path.isfile(path):
            return None

        timestamp = int(os.stat(path).st_mtime)
        image = QImage(path)

        self.glob.env.logLine(8, "Load: " + path + " " + str(image.format()))
        self.create(path, image)
        if textype == "system":
            self.repo.add_sys(path, self.texture)
        else:
            self.repo.add_user(path, self.texture, timestamp, self, self.obj)
        # self.repo.show()
        return self.texture

    def refresh(self, path):
        # print ("refresh: ", path)
        self.destroy()
        image = QImage(path)
        self.create(path, image)
        return self.texture


class MH_Thumb():
    def __init__(self, maxsize=128):
        self.maxsize = maxsize
        self.img = None

    def rescale(self, name):
        self.img = QImage(name)
        size = self.img.size()
        if size.height() > self.maxsize or size.width() > self.maxsize:
            newimage = self.img.scaled(self.maxsize, self.maxsize, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            newimage.save(name, "PNG", -1)

