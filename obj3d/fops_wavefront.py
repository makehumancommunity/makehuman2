"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    file operations, wavefront OBJ

    Functions:
    * importWaveFront
"""

import numpy as np
import math

def importWaveFront(path, obj):
    """
    f  = face
    g  = groups are used to add faces to
    o  = object (name), only one is used
    v  = positions (3d)
    vt = positions (texture)
    usemtl = material (skipped)

    returns: 2 okay, 1 warn, 0 error
    """

    try:
        f = open(path, 'r', encoding="utf-8")
    except IOError:
        return (0, "Cannot open file " + path)
    else:

        verts  = []
        uvs    = []
        groups = {}
        groupnames = [] # to keep the group order
        objname = None
        prim = 0        # number of needed triangles
        ln = 0          # line number
        fcnt = 0        # face-counter
        ucnt = 0        # UV-face counter

        groupnames.append("mh_default")
        g = groups["mh_default"] = {"v": [], "uv": [] }

        for line in f:
            ln += 1
            words = line.split()

            lwords = len(words) -1
            if lwords <= 0:
                continue

            command = words[0]

            # v and vt simply fill buffers (for UV-Map change coordinates)
            #
            if command == 'v':
                verts.append((float(words[1]), float(words[2]), float(words[3])))

            elif command == 'vt':
                uvs.append((float(words[1]), 1 - float(words[2])))

            # f, faces, this data is stored groupwise, index counts from 1
            # a/b ... first one is vertex-index, second one UV
            #
            elif command == 'f':
                vInd  = []
                uvInd = []

                prim += (lwords-2)  # count number of primitives

                for elem in words[1:]:
                    columns = elem.split('/')
                    vindex = int(columns[0]) - 1
                    vInd.append(vindex)

                    if len(columns) > 1 and columns[1] != '':
                        uc = int(columns[1])
                        uvInd.append(uc - 1)

                g["v"].append(vInd)
                fcnt += 1

                if len(uvInd) > 0:
                    g["uv"].append(uvInd)
                    ucnt += 1

            elif command == 'g':
                gname = words[1]
                if gname not in groups:
                    g = groups[gname] = {"v": [], "uv": [] }
                    groupnames.append(gname)

            elif command == 'o':
                objname = words[1]

            else:
                # print ("Ignore: " + line)
                pass
        f.close()

    # delete empty groups
    # must be done in two steps not to destroy iteration, first step can delete empty uvs
    #
    delete = []
    for g in groups:
        if len(groups[g]["v"]) == 0:
            delete.append(g)
            groupnames.remove(g)
        if len(groups[g]["uv"]) == 0:
            del groups[g]["uv"]

    for d in delete:
        del groups[d]

    # let the UV coordinates use the same index as the faces, because
    # glDrawElements means one index for UV-Buffer, Normals and coordinates
    # 
    # classically there are more UVS because of seams, so we need to duplicated coordinates
    # we use a -1 filled vertex_uv-Buffer to be filled with correct indices
    #
    # they should be in overflow-buffer
    # after that we got new uvs, a few more coordinates, and partly a changed index
    # the information about UV is changed to pure bool indicating the availability
    # 
    overflowbuf = {}

    n_origverts = n_verts = len(verts) # number of vertices, start with the number we have, will increased in case we need new ones
    n_uvs = len(uvs)
    vertex_uv = np.full(n_verts, 0xffffffff, dtype=np.uint32)

    uvsize = n_verts*4      # try to find a buffer sufficient for the uv-values
    max_uv = n_uvs * 3 
    if max_uv > uvsize:
        uvsize = max_uv

    uv_values = np.zeros (shape=(uvsize, 2), dtype=np.float32)  # should be sufficient for the longest possible buffer

    for g in groups:
        if "uv" in groups[g] and len(groups[g]["uv"]) > 0:
            gi = groups[g]["v"]
            guv = groups[g]["uv"]

            for num, face in enumerate(gi):
                uvface = guv[num]
                for inum, vert in enumerate(face):
                    uvert = uvface[inum]

                    # if vertex_uv[vert] still is unused, set it to the value which is added, no changed
                    #
                    if vertex_uv[vert] == 0xffffffff:
                        vertex_uv[vert] = uvert
                        uv_values[vert] = uvs[uvert]

                    # in case it is used but different, check if we have the combination already in overflow-buffer
                    # sometimes meshes are not connected, but vertices are identical
                    #
                    elif vertex_uv[vert] != uvert:
                        dx =  math.fabs(uv_values[vert][0] - uvs[uvert][0])
                        dy =  math.fabs(uv_values[vert][1] - uvs[uvert][1])

                        if dx > 0.001 or dy > 0.001:
                            name = str(vert) + "_" + str(uvert)     # mathematically old makehuman uses sth like vert << 32 | uvert, would also work here

                            if name in overflowbuf:
                                # print (name + " allready in overflowbuf")
                                gi[num][inum] = overflowbuf[name]   # we can use it from buffer
                            else:
                                # print ("new one needed:" + name)
                                overflowbuf[name] = n_verts         # we creat a new entry
                                verts.append(verts[vert])           # append identical coords to the end
                                uv_values[n_verts] = uvs[uvert]     # place uv-values there
                                gi[num][inum] = n_verts             # change the index to new appended element
                                n_verts += 1                        # and increment number of elements

            groups[g]["uv"] = True      # the information is now replaced by the bool we need
        else:
            groups[g]["uv"] = False

    overflowtable = np.empty((len(overflowbuf), 2), dtype=np.uint32)

    i = 0
    for key, value in overflowbuf.items():
        (a,b) = key.split("_")
        overflowtable[i] = (a, value)
        i+=1
    overflowtable.view('uint32,uint32').sort(order=['f0'], axis=0) # sort by first column in place

    # print (overflowtable)

    uv_values.resize((n_verts, 2), refcheck=False)          # shorten buffer back to what we really needed.

    del vertex_uv                                           # the helper is no longer necessary

    # sanity test for finding vertices costs too much time
    #
    obj.setName(objname)
    obj.setGroupNames(groupnames)
    obj.createGLVertPos(verts, uv_values, overflowtable, n_origverts)          # TODO consider to recombine createGLVertPos and createGLFaces

    validGeom = obj.createGLFaces(fcnt, ucnt, prim, groups)
    if validGeom:
        res = 2
        msg = None
    else:
        res = 1
        msg = "Bad geometry, at least one normal vector of face with size 0 cannot be calculated. " + \
                "This can result in artifacts in certain programs. Makehuman2 can deal with it."

    del verts
    del uvs

    return (res, msg)
