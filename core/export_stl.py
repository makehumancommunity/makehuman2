"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * stlExport

    stl exporter

    posed can be achieved by setting the option to pose

ASCII STL just contains zillions of triangles without any order + normals on these triangles

solid name

facet normal ni nj nk
  outer loop
    vertex v1x v1y v1z
    vertex v2x v2y v2z
    vertex v3x v3y v3z
  endloop
endfacet

endsolid

Binary STL starts a bit odd ===================

80 bytes of something (usually full of 0-bytes but sometimes different)
Uint32 number of triangles

then per triangle:
REAL32[3] – Normal vector
REAL32[3] – Vertex 1
REAL32[3] – Vertex 2
REAL32[3] – Vertex 3
UINT16    – Attribute byte count  (which can be used for everything but mostly is zero)
"""

import struct

class stlExport:
    def __init__(self, glob, exportfolder, hidden=False, scale=1.0):
        self.exportfolder = exportfolder
        self.env = glob.env
        self.scale = scale
        self.hidden = hidden

    def ascMesh(self, f, obj):
        hiddenmask = obj.hiddenMask() if self.hidden is False else None
        norm = obj.gl_norm
        coord = obj.gl_coord * self.scale
        for elem in obj.fverts:
            if hiddenmask is not None:
                if (hiddenmask[elem[0]] & hiddenmask[elem[1]] & hiddenmask[elem[2]]) == 0:
                    continue
            (p1, p2, p3) = (elem[0] *3, elem[1] *3, elem[2] *3)
            xnorm = (norm[p1] + norm[p2] + norm[p3]) / 3
            ynorm = (norm[p1+1] + norm[p2+1] + norm[p3+1]) / 3
            znorm = (norm[p1+2] + norm[p2+2] + norm[p3+2]) / 3
            f.write("facet normal " + str(xnorm) + " "  + str(ynorm) + " " + str(znorm) + "\n" + \
                "\touter loop\n\t\tvertex " + str(coord[p1]) + " "  + str(coord[p1 +1]) + " " + str(coord[p1+2]) + "\n" + \
                "\t\tvertex " + str(coord[p2]) + " "  + str(coord[p2 +1]) + " " + str(coord[p2+2]) + "\n" + \
                "\t\tvertex " + str(coord[p3]) + " "  + str(coord[p3 +1]) + " " + str(coord[p3+2]) + "\n" + \
                "\tendloop\nendfacet\n")

    def binMesh(self, f, obj):
        hiddenmask = obj.hiddenMask() if self.hidden is False else None
        if hiddenmask is not None:
            print ("Is hidden")
        norm = obj.gl_norm
        coord = obj.gl_coord * self.scale
        cnt = 0
        for elem in obj.fverts:
            if hiddenmask is not None:
                if (hiddenmask[elem[0]] & hiddenmask[elem[1]] & hiddenmask[elem[2]]) == 0:
                    continue
            (p1, p2, p3) = (elem[0] *3, elem[1] *3, elem[2] *3)
            xnorm = (norm[p1] + norm[p2] + norm[p3]) / 3
            ynorm = (norm[p1+1] + norm[p2+1] + norm[p3+1]) / 3
            znorm = (norm[p1+2] + norm[p2+2] + norm[p3+2]) / 3

            f.write(struct.pack(b'<ffffffffffffH', xnorm, ynorm, znorm,
                coord[p1], coord[p1 +1], coord[p1+2],
                coord[p2], coord[p2 +1], coord[p2+2],
                coord[p3], coord[p3 +1], coord[p3+2], 0))
            cnt += 1
        return(cnt)

    def ascSave(self, baseclass, filename):
        self.env.last_error ="okay"
        solid =  baseclass.name.replace(' ','_')
        has_proxy = (baseclass.proxy is not None)

        try:
            with open(filename, 'w', encoding="utf-8") as f:
                f.write('solid %s\n' % solid)
                if has_proxy is None:
                    self.ascMesh(f, baseclass.baseMesh)
                for asset in baseclass.attachedAssets:
                    self.ascMesh(f, asset.obj)
                f.write('endsolid %s\n' % solid)

        except IOError as error:
            self.env.last_error = str(error)
            return False

        return True

    def binSave(self, baseclass, filename):
        self.env.last_error ="okay"
        has_proxy = (baseclass.proxy is not None)

        try:
            count = 0
            with open(filename, 'wb') as f:
                f.write(b'\x00' * 80)
                f.write(struct.pack(b'<I', count))
                if has_proxy is None:
                    count += self.binMesh(f, baseclass.baseMesh)
                for asset in baseclass.attachedAssets:
                    count += self.binMesh(f, asset.obj)
                f.seek(80)
                f.write(struct.pack('<I', count))

        except IOError as error:
            self.env.last_error = str(error)
            return False

        return True

