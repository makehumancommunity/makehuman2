"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck, Elvaerwyn_MH2 2026 V1.2

    Classes:
    * objExport

    wavefront exporter
"""

import os
import numpy as np

class objExport:
    def __init__(self, glob, exportfolder, imagefolder="textures", hiddenverts=False, onground=True, helper=False,
            normals=False, animation=False, saveprops=False, scale=0.1):

        self.imagefolder = imagefolder
        self.exportfolder = exportfolder
        self.glob = glob
        self.env = glob.env
        self.hiddenverts = hiddenverts
        self.onground = onground
        self.scale = scale
        self.lowestPos = 0.0
        self.normals = normals
        self.helper = helper
        self.animation = animation
        self.saveprops = saveprops

        self.coordlines = []
        self.normlines = []
        self.uvlines = []
        self.facelines = []
        self.matlines = []

        self.startvert = 1
        self.startuv = 1

        self.obj = []


    def copyImage(self, source, dest):
        self.env.logLine(8, "Need to copy " + source + " to " + dest)

        if self.env.mkdir(dest) is False:
            return False

        dest = os.path.join(dest, os.path.basename(source))
        return (self.env.copyfile(source, dest))

    def addImage(self, typeid, image, copy=True):
        destination = os.path.join(self.exportfolder, self.imagefolder)
        if copy:
            okay = self.copyImage(image, destination)
            if not okay:
                return False

        name = os.path.join(self.imagefolder, os.path.basename(image))
        self.matlines.append(typeid + " " + name + "\n")
        return True

    def addCoords(self, num, coords):
        mcoord = np.reshape(coords, (len(coords)//3, 3))
        for co in mcoord:
            self.coordlines.append("v %.4f %.4f %.4f\n" % (co[0]*self.scale, co[1]*self.scale - self.lowestPos, co[2]*self.scale))
        self.obj[num]["lenV"] = len(mcoord)

    def addNormals(self, num, values):
        mvalues = np.reshape(values, (len(values)//3, 3))
        for val in mvalues:
            self.normlines.append("vn %.6f %.6f %.6f\n" % tuple(val))

    def addUVCoords(self, num, coords):
        mcoord = np.reshape(coords, (len(coords)//2, 2))
        for co in mcoord:
            self.uvlines.append("vt %.6f %.6f\n" % (co[0], 1.0 - co[1]))
        self.obj[num]["lenUV"] = len(mcoord)

    def addFaces(self, num, name, material, vpf, faces, ov):
        self.facelines.append("usemtl " + material.name + "\n")
        self.facelines.append("g " + name + "\n")

        # --- overflow array is defined as pairs
        overflow = {}
        if ov is not None:
            for l in ov:
                overflow[l[1]] = l[0]
        x = 0

        last= self.startvert + self.obj[num]["lenV"]
        if self.normals:
            for n in vpf:
                out = "f "
                saveit = True
                for i in range(n):
                    uvface = faces[x]
                    face = overflow[uvface] if uvface in overflow else uvface
                    if (face + self.startvert) >= last:
                        saveit = False

                    out += "%d/%d/%d " % (face+self.startvert, uvface+self.startuv, face+self.startvert)
                    x += 1
                if saveit:
                    self.facelines.append(out + "\n")
        else:
            for n in vpf:
                out = "f "
                saveit = True
                for i in range(n):
                    uvface = faces[x]
                    face = overflow[uvface] if uvface in overflow else uvface
                    if (face + self.startvert) >= last:
                        saveit = False

                    out += "%d/%d " % (face+self.startvert, uvface+self.startuv)
                    x += 1
                if saveit:
                    self.facelines.append(out + "\n")

        self.startvert += self.obj[num]["lenV"]
        self.startuv   += self.obj[num]["lenUV"]

    def addMaterial(self, num, material):
        """
        :param num: not used
        :param material: class material
            material is a class and the definition (defaults) prevents wrong values.
            If this is not given all openGL processes would immediately crash
        """

        diff = material.diffuseColor
        d_r, d_g, d_b = diff[0], diff[1], diff[2]
        spec = material.specularColor
        s_r, s_g, s_b = spec[0], spec[1], spec[2]
        emis = material.emissiveColor
        e_r, e_g, e_b = emis[0], emis[1], emis[2]

        alpha = 1

        rough = getattr(material, "roughnessFactor", 0.5)
        metal = getattr(material, "metallicFactor", 0.0)

        self.matlines.append("\n")
        self.matlines.append("newmtl " + material.name + "\n")

        # --- Pass direct unpacked floating point values into the templates ---
        self.matlines.append("Kd %.4f %.4f %.4f\n" % (d_r, d_g, d_b))
        self.matlines.append("Ks %.4f %.4f %.4f\n" % (s_r, s_g, s_b))
        self.matlines.append("Ke %.4f %.4f %.4f\n" % (e_r, e_g, e_b))
        self.matlines.append("d %.4f\n" % alpha)
        self.matlines.append("Pr %.4f\n" % rough)
        self.matlines.append("Pm %.4f\n" % metal)

        # --- TEXTURE MAP CHANNELS  ---
        if hasattr(material, "aomapTexture") and material.aomapTexture:
            if self.addImage("map_Ka", material.aomapTexture) is False:
                return False

        if hasattr(material, "diffuseTexture") and material.diffuseTexture:
            diffusename = material.saveDiffuse() if getattr(material, 'colorationMethod', 0) > 0 else material.diffuseTexture
            if self.addImage("map_Kd", diffusename) is False:
                return False

        # Metallic Roughness Texture Splitting
        if hasattr(material, "metallicRoughnessTexture") and material.metallicRoughnessTexture:
            if self.addImage("map_Pr -imfchan g", material.metallicRoughnessTexture) is False:
                return False
            self.addImage("map_Pm -imfchan b", material.metallicRoughnessTexture, copy=False)

        if hasattr(material, "emissiveTexture") and material.emissiveTexture:
            if self.addImage("map_Ke", material.emissiveTexture) is False:
                return False

        # Normal Map Mapping Check
        if hasattr(material, "normalmapTexture") and material.normalmapTexture:
            if self.addImage("map_Bump", material.normalmapTexture) is False:
                return False

        return True

    def ascSave(self, baseclass, filename):

        materialfile = filename[:-4]+".mtl"
        header = "# MakeHuman exported OBJ\n# www.makehumancommunity.org\n\n" + \
            "mtllib " + os.path.basename(materialfile) + "\n"

        matheader = "# MakeHuman exported MTL\n# www.makehumancommunity.org\n\n"

        # collect objects:
        #
        if self.onground:
            self.lowestPos = baseclass.getLowestPos() * self.scale

        if baseclass.proxy is None or self.helper is True:
            obj = baseclass.baseMesh
            mat = obj.material

            # in case of helper NO verts on body are hidden
            #
            hiddenverts = True if self.helper else self.hiddenverts
            (coords, norms, uvcoords, vpface, faces, overflow, mapping) = obj.getVisGeometry(hiddenverts, self.helper)
            self.obj.append ({"name": "base", "mat": mat, "c": coords, "no": norms, "uv": uvcoords, "vpf": vpface, "f": faces, "o": overflow })

        for elem in baseclass.attachedAssets:
            mat = elem.obj.material
            (coords, norms, uvcoords, vpface, faces, overflow, mapping) = elem.obj.getVisGeometry(self.hiddenverts)
            self.obj.append ({"name": elem.obj.name, "mat": mat, "c": coords, "no": norms, "uv": uvcoords, "vpf": vpface, "f": faces, "o": overflow })

        # vertices
        #
        for i, obj in enumerate(self.obj):
            self.addCoords(i, obj["c"])

        # normals in case they are selected
        #
        if self.normals:
            for i, obj in enumerate(self.obj):
                self.addNormals(i, obj["no"])

        # UVs
        #
        for i, obj in enumerate(self.obj):
            self.addUVCoords(i, obj["uv"])

        # faces
        #
        for i, obj in enumerate(self.obj):
            self.addFaces(i, obj["name"], obj["mat"], obj["vpf"], obj["f"], obj["o"])

        # materials
        #
        for i, obj in enumerate(self.obj):
            if self.addMaterial(i, obj["mat"]) is False:
                return False

        try:
            with open(filename, 'w', encoding="utf-8") as f:
                f.write(header)
                f.writelines(self.coordlines)
                f.writelines(self.normlines)
                f.writelines(self.uvlines)
                f.writelines(self.facelines)
        except IOError as error:
            self.env.last_error = str(error)
            return False

        # save material extra
        try:
            with open(materialfile, 'w', encoding="utf-8") as f:
                f.write(matheader)
                f.writelines(self.matlines)

        except IOError as error:
            self.env.last_error = str(error)
            return False

        return True

