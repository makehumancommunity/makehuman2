"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    binary file operations on object3d

    Functions:
    * exportObj3dBinary
    * importObjValues
    * importObj3dBinary
    * importObjFromFile
"""

import numpy as np
import os
from obj3d.fops_wavefront import importWaveFront

def exportObj3dBinary(filename, obj, content = {}):

    # binary structure
    # first header

    lname = len(obj.name)
    header_type = np.dtype({'names':('objname', 'numverts', 'prnt', 'fcnt', 'ucnt'), 'formats':('|S'+str(lname), 'i4', 'i4', 'i4', 'i4')})
    content["header"] = np.array([(obj.name, obj.n_origverts, obj.prim, obj.n_faces, obj.n_fuvs)], dtype=header_type)

    # then all names of the groups
    #
    content["grpNames"] = obj.npGrpNames

    # the xyz coordinates of vertices
    # then uv-coordinates
    #
    content["coord"] = obj.coord
    content["uvs"] = obj.uvs

    # now the overflowbuffer to help OpenGL
    #
    content["overflow"] = obj.overflow 
    ngroups = len(obj.npGrpNames)

    # now the more complex calculation of the faces as
    # index-buffer groups (i4) Element-Start, (i4) NumFaces, and a bool)
    #
    groupinfo = np.zeros(ngroups, dtype=np.dtype('i4,i4,?'))
    allvertnums = 0
    allfaces = 0
    for num, npelem in enumerate (obj.npGrpNames):
        cnt = 0
        elem = npelem.decode("utf-8")
        group = obj.loadedgroups[elem]
        faces = group["v"]
        lfaces = len(faces)
        for face in faces:
            cnt += len(face)
        groupinfo[num] = tuple([allvertnums, lfaces, group["uv"]])
        allvertnums += cnt
        allfaces += lfaces
    
    # two flat arrays for number of verts and position
    #
    vertsperface = np.zeros(allfaces, dtype=np.dtype('i4'))
    faceverts = np.zeros(allvertnums, dtype=np.dtype('i4'))
    finfocnt = 0
    fvertcnt = 0
    for npelem in obj.npGrpNames:
        elem = npelem.decode("utf-8")
        group = obj.loadedgroups[elem]
        faces = group["v"]
        for face in faces:
            for vert in face:
                faceverts[fvertcnt] = vert
                fvertcnt += 1
            vertsperface[finfocnt] = len(face)
            finfocnt += 1

    content["groupinfo"] = groupinfo
    content["vertsperface"] = vertsperface
    content["faceverts"] = faceverts

    obj.env.logLine(8, "Save compressed: " + filename)
    try:
        f = open(filename, "wb")
        np.savez_compressed(f, **content)
        f.close()
    except OSError as error:
        return (False, str(error))

    return(True, None)


def importObjValues(npzfile, obj):
    for elem in ['header', 'grpNames', 'coord', 'uvs', 'overflow', 'groupinfo', 'vertsperface', 'faceverts']:
        if elem not in npzfile:
            error =  "Malformed file, missing component " + elem
            return (0, error)

    # now get data from binary, header
    #
    header = list(npzfile['header'][0])
    obj.name        = header[0].decode("utf-8")
    (obj.n_origverts, prim, fcnt, ucnt) = header[1:]

    # next stuff is identical to npz file, number of elements is mostly added
    #
    obj.npGrpNames = npzfile['grpNames']
    obj.n_groups = len(obj.npGrpNames)

    # xyz coordinates of vertices, uvs and OpenGL overflow buffer
    #
    obj.coord    = npzfile["coord"]
    obj.n_verts = len(obj.coord)
    obj.uvs      = npzfile["uvs"]
    obj.n_uvs   = len(obj.uvs)
    obj.overflow = npzfile["overflow"]

    # regenerate groups from groupinfo, vertsperface, faceverts
    # index-buffer groups (Start, NumFaces, bool)
    #
    verts = npzfile["faceverts"]
    fsize = npzfile["vertsperface"]
    groups = {}
    j = 0
    for num, elem in enumerate(npzfile["groupinfo"]):
        start = elem[0]
        faces = elem[1]
        f = []
        fs = start
        for i in range(faces):
            v = []
            for k in range(0, fsize[j]):
                v.append(verts[fs+k])
            f.append(v)
            fs += fsize[j]
            j += 1

        group =  obj.npGrpNames[num].decode("utf-8")
        groups[group] = { "v": f, "uv": elem[2] }

    validGeom = obj.createGLFaces(fcnt, ucnt, prim, groups)
    if validGeom:
        res = 2
        msg = None
    else:
        res = 1
        msg = "Bad geometry, at least one normal vector of face with size 0 cannot be calculated. " + \
                "This can result in artifacts in certain programs. Makehuman2 can deal with it."

    return (res, msg)

def importObj3dBinary(path, obj):
    obj.env.logLine(8, "Read binary: " + path)
    npzfile = np.load(path)
    return(importObjValues(npzfile, obj))

def importObjFromFile(path, obj, use_obj=False):
    """
    check if binary file exists
    """
    if use_obj is False:
        if obj.filename.endswith(".mhbin"):
            if os.path.isfile(obj.filename):
                return importObj3dBinary(obj.filename, obj)
            else:
                return 0, "cannot load " + obj.filename

        if obj.filename.endswith(".obj"):
            binfile = path[:-3] + "mhbin"
            if os.path.isfile(binfile):
                return importObj3dBinary(binfile, obj)

    # only ASCII
    #
    obj.env.logLine(8, "Load: " + path)
    return importWaveFront(path, obj)


