"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * object3d
"""

import numpy as np 
from obj3d.fops_binary import exportObj3dBinary, importObjFromFile
from opengl.material import Material
import os

class object3d:
    def __init__(self, glob, baseinfo, eqtype ):
 
        self.glob = glob
        self.env  = glob.env
        self.type = eqtype      # equipmentype
        self.openGL   = None    # openGL pointer
        self.filename = None    # original file name
        self.name = None    # will contain object name derived from loaded file (identical to asset)
        self.npGrpNames = []  # ordered list of groupnames numpy format

        self.prim    = 0    # will contain number primitives (tris)
        self.n_origverts = 0 # number of vertices after loading
        self.n_verts = 0    # number of vertices
        self.n_faces = 0    # number of faces
        self.n_fuvs  = 0    # number of uv-faces
        self.n_groups= 0    # number of groups
        self.z_depth = 0    # lowest value for z-depth, rendering of basemesh

        self.coord = []     # will contain positions of vertices, array of float32 for openGL
        self.uvs   = []     # will contain coordinates for uvs
        self.fverts  = []   # will contain vertices per face, [verts, 3] array of uint32 for openGL > 2
        self.n_fverts = 0    # number of vertices for open gl
        self.loadedgroups = None # will contain the group after loading from file (also for hidden geometry)
        self.group = []     # will contain pointer to group per face

        self.overflow = None # will contain a table for double used vertices [source, dest]

        self.gl_coord = []    # will contain flattened gl-Buffer (these are coordinates to be changed)
        self.gl_coord_o = []  # will contain a copy of unchanged positions (TODO base mesh only ?)

        self.gl_coord_w = []  # will contain a copy of unchanged positions (working mode with targets) & for posing
        self.gl_coord_mn = []  # will contain buffer for work with macros containing all changes except the macros
        self.gl_coord_mm = []  # will contain buffer for work with macros containing all changes of the macros

        self.gl_uvcoord = []  # will contain flattened gluv-Buffer
        self.gl_norm  = []    # will contain flattended normal buffer
        self.n_glnorm  = 0    # number of normals for open gl

        self.gl_icoord = []     # openGL-Drawarray Index
        self.gl_hicoord = None  # openGL-Drawarray used when parts are hidden

        self.min_index = None   # will contain vertex numbers for min values xyz
        self.max_index = None   # will contain vertex numbers for max values xyz

        self.minpose_index = None   # will contain vertex numbers for min values xyz in posed mode
        self.maxpose_index = None   # will contain vertex numbers for max values xyz in posed mode

        self.material = None    # will contain a material


        if baseinfo is not None:
            self.visible = baseinfo["visible groups"]
            self.is_base = True
        else:
            self.visible = None
            self.is_base = False

    def __str__(self):
        return (self.name + ": Object3d with " + str(self.n_groups) + " group(s)\n" + 
                str(self.n_origverts) + " vertices, " + str(self.n_faces) + " faces (" +
                str(self.n_fuvs) + " uv-faces)\nOpenGL triangles: " +
                str(self.prim) + "\nOpenGL DrawElements: " + str(self.n_verts)) 

    def debug(self, text):
        self.env.logLine (2, "Object3d: " + text)

    def load(self, path, use_obj=False):
        """
        load a mesh either binary or per object
        """
        self.filename = path
        (success, text) = importObjFromFile(path, self, use_obj)
        if success > 0:
            self.initMaterial()
        return (success, text)

    def setZDepth(self, z_depth):
        self.z_depth = z_depth

    def initMaterial(self, filename=None):
        if filename is None:
            filename = self.filename
        self.material = Material(self.glob, os.path.dirname(filename), self.type)

    def listAllMaterials(self):
        if self.material:
            return self.material.listAllMaterials(os.path.dirname(self.filename))
        return []

    def getMaterialPath(self, filename):
        if filename is not None and self.material is not None:
            return(self.material.isExistent(filename))
        return None

    def loadMaterial(self, pathname):
        """
        use a relative path to object
        """
        if pathname is not None and self.material is not None:
            return(self.material.loadMatFile(pathname))
        else:
            return True

    def newMaterial(self, pathname):

        if self.material is not None:
             self.material.freeTextures()
        self.initMaterial()
        return(self.material.loadMatFile(pathname))

    def getMaterialFilename(self):
        if self.material is not None:
            return(self.material.getCurrentMatFilename())
        return None

    def exportBinary(self):
        filename = self.filename[:-4] + ".mhbin" if self.filename.endswith(".obj") else self.filename + ".mhbin"
        return exportObj3dBinary(filename, self)

    def setName(self, name):
        if name is None:
            self.name = "generic"
        else:
            self.name = name

    def setGroupNames(self, names):
        """
        group names in numpy format (usable for binary export)
        """
        nlen = 0
        for name in names:
            l = len(name)
            if l > nlen:
                nlen = l
        self.npGrpNames = np.array(names, dtype='|S'+str(nlen))
        self.n_groups = len(names)

    def getOpenGLIndex(self):
        #print (self.filename +  " deleted verts" if self.gl_hicoord is not None else self.filename + " normal")
        return (self.gl_hicoord if self.gl_hicoord is not None else self.gl_icoord)

    def notHidden(self):
         self.gl_hicoord = None

    def createGLVertPos(self, pos, uvs, overflow, orig):
        self.n_origverts = orig
        self.n_verts = len(pos)
        self.coord = np.asarray(pos, dtype=np.float32)      # positions converted to array of floats
        self.n_uvs = len(uvs)
        self.uvs = np.asarray(uvs, dtype=np.float32)        # positions converted to array of floats
        self.overflow = overflow

    def overflowCorrection(self, arr):
        """
        when the main part of the mesh is directly corrected, handle the overflow
        """
        # numpy: create fancy indices from columns, repeat it 3 times and add values 0, 1, 2
        # simulates this:
        # for (source, dest) in self.overflow:
        #    s = source * 3     # np.repeat
        #    d = dest * 3
        #    arr[d:d+3]   = arr[s:s+3]  (np.tile for d:d+3)

        index = np.tile(np.array([0,1,2]), len(self.overflow))
        src = np.repeat(self.overflow[:,0], 3)*3 + index
        dst = np.repeat(self.overflow[:,1], 3)*3 + index
        arr[dst]   = arr[src]

    def calcNormals(self):
        """
        calculates face-normals and then vertex normals
        returns if geometry is valid (invalid: normal vector cannot be calculated)
        """
        validGeom = True
        self.gi_norm = np.zeros((self.n_verts, 3), dtype=np.float32)

        # set the face normals for each vertex to zero, set the counter to zero
        #
        fa_norm = np.zeros((self.n_verts, 3), dtype=np.float32)
        fa_cnt  = np.zeros(self.n_verts, dtype=np.uint32)

        lfv = len(self.fverts)
        fnorm = np.zeros((lfv,3), dtype=np.float32)

        # numpy: create index to iterate and 3 vectors and put result to fnorm
        # for elem in self.fverts:
        #    v = self.coord[elem]
        #    norm = np.cross(v[0] - v[1], v[1] - v[2])
        #
        ix = np.s_[:lfv]
        fvert = self.coord[self.fverts[ix]]
        v1 = fvert[:,0,:]
        v2 = fvert[:,1,:]
        v3 = fvert[:,2,:]
        va = v1 - v2
        vb = v2 - v3
        fnorm[ix] = np.cross(va, vb)

        # calculate face normal and summarize them with other (for each 3 verts per triangle)
        for ix, elem in enumerate(self.fverts):
            fa_norm[elem[0]] += fnorm[ix]
            fa_norm[elem[1]] += fnorm[ix]
            fa_norm[elem[2]] += fnorm[ix]
            fa_cnt[elem[0]] += 1
            fa_cnt[elem[1]] += 1
            fa_cnt[elem[2]] += 1

        # because part of the faces belong to the overflow buffer add them as well
        #
        #for (source, dest) in self.overflow:
        #    fa_norm[source] += fa_norm[dest]
        #    fa_cnt[source]  += fa_cnt[dest]

        src = self.overflow[:,0]
        dst = self.overflow[:,1]

        fa_cnt[src] += fa_cnt[dst]
        fa_norm[src] += fa_norm[dst]

        # now divide by the number of edges and normalize length with np.linalg.norm
        # ignore zero weights ( fa_norm = fa_norm / fa_cnt), set these to 1.0
        #
        with np.errstate(divide='ignore', invalid='ignore'):
            normsum = np.divide(fa_norm, np.expand_dims(fa_cnt, axis=1))
        normsum = np.nan_to_num(normsum, nan=1.0)

        # calculate norm
        #
        for i in range(0, len(normsum)):
            areanorm = np.linalg.norm(normsum[i])
            if areanorm != 0.0:
                self.gi_norm[i] = normsum[i] / areanorm
            else:
                validGeom = False
                self.gi_norm[i][0] = 1.0
                self.gi_norm[i][1] = 0.0
                self.gi_norm[i][2] = 0.0

        # simply copy for the doubles in the end using overflow
        #
        # for (source, dest) in self.overflow:
        #    self.gi_norm[dest] =  self.gi_norm[source]

        self.gi_norm[dst] = self.gi_norm[src]

        # flatten vector
        #
        self.gl_norm = self.gi_norm.flatten()

        return validGeom

    def calcFaceBufSize(self, mask, overrideignore=False):
        """
        create buffersizes for vertsperface, faceverts buffer

        :param mask: calculates if faces are used
        :param overrideignore: normaly used when the helper as invisible group should also be considered
        """
        numfaces = 0
        numind = 0
        for npelem in self.npGrpNames:
            elem = npelem.decode("utf-8")
            if self.visible is not None and elem not in self.visible and not overrideignore:
                continue
            faces = self.loadedgroups[elem]["v"]
            if mask is None:
                # simple case, just count indices and faces
                #
                for face in faces:
                    numind += len(face)
                numfaces += len(faces)
            else:
                # otherwise we need 3 indices minimum to create a face
                #
                for face in faces:
                    nind = 0
                    for vert in face:
                        if mask[vert] == 1:
                            nind +=1
                    if nind > 2:
                        numind += nind
                        numfaces += 1

        return numind, numfaces

    def fillFaceBuffers(self, vertsperface, faceverts, mask, overrideignore=False):
        """
        fill vertsperface, faceverts buffer

        :param vertsperface: buffer to put the vertices per face
        :param faceverts: buffer for the face vertex numbers
        :param mask: calculates if faces are used
        :param overrideignore: normaly used when the helper as invisible group should also be considered
        """
        finfocnt = 0
        fvertcnt = 0
        highest = 0
        for npelem in self.npGrpNames:
            elem = npelem.decode("utf-8")
            if self.visible is not None and elem not in self.visible and not overrideignore:
                continue
            group = self.loadedgroups[elem]
            faces = group["v"]
            if mask is None:
                for face in faces:
                    for vert in face:
                        if vert < self.n_origverts:
                            if vert > highest:
                                highest = vert
                        faceverts[fvertcnt] = vert
                        fvertcnt += 1
                    vertsperface[finfocnt] = len(face)
                    finfocnt += 1
            else:
                for face in faces:
                    nind = 0
                    for vert in face:
                        if mask[vert] == 1:
                            nind +=1
                    if nind > 2:
                        for vert in face:
                            if mask[vert] == 1:
                                if vert < self.n_origverts:
                                    if vert > highest:
                                        highest = vert
                                faceverts[fvertcnt] = vert
                                fvertcnt += 1
                        vertsperface[finfocnt] = nind
                        finfocnt += 1

        return (highest + 1)

    def unUsedVerts(self, faceind):
        indlen = len(faceind)
        usedmax = len(self.gl_uvcoord) // 2
        ba = np.full((usedmax), 0)
        for cnt in range(0, indlen):
            ba[faceind[cnt]] = 1
        return (ba)

    def shortenOverflow(self, mapping):
        arr = []
        if len(self.overflow) > 0:
            for i, (s,d) in enumerate(self.overflow):
                source = mapping[s]
                dest = mapping[d]
                if source != -1 and dest != -1:
                    arr.append([source, dest])
            return (np.array(arr, dtype=np.uint32))
        else:
            return None

    def getVisGeometry(self, displayhidden, helper=False):
        """
        return flattened vectors with coordinates, norms, uvcoords, vertex-per-face, faces and overflow
        values are deduplicated, used for exports
        """
        mask = self.hiddenMask() if displayhidden is False else None
        mapping = None

        # TODO: still problems with proxy hiding in blender

        # get buffersize
        #
        numind, numfaces = self.calcFaceBufSize(mask, helper)

        vertsperface = np.zeros(numfaces, dtype=np.dtype('i1'))
        faceverts = np.zeros(numind, dtype=np.dtype('i4'))

        mx = self.fillFaceBuffers(vertsperface, faceverts, mask, helper)
        if mask is not None:
            mask = self.unUsedVerts(faceverts)
            usedmax = len(mask)
            mapping, newcoord = self.createMapping(mask)
            coord = np.zeros(newcoord*3,  dtype=np.float32)
            norm = np.zeros(newcoord*3,  dtype=np.float32)
            gl_uvcoord = np.zeros(newcoord*2,  dtype=np.float32)
            for cnt in range(0, usedmax):
                d = mapping[cnt]
                if d != -1:
                    s2 = cnt * 2
                    s3 = cnt * 3
                    d2 = d * 2
                    d3 = d * 3

                    coord[d3] = self.gl_coord[s3]
                    coord[d3+1] = self.gl_coord[s3+1]
                    coord[d3+2] = self.gl_coord[s3+2]

                    norm[d3] = self.gl_norm[s3]
                    norm[d3+1] = self.gl_norm[s3+1]
                    norm[d3+2] = self.gl_norm[s3+2]

                    gl_uvcoord[d2] = self.gl_uvcoord[s2]
                    gl_uvcoord[d2+1] = self.gl_uvcoord[s2+1]

            for i in range(0, len(faceverts)):
                faceverts[i] = mapping[faceverts[i]]

            overflow = self.shortenOverflow(mapping)
            if overflow is not None:
                mx = overflow.min(axis=0)[1]
                coord = np.resize(coord, mx * 3)
                norm = np.resize(norm, mx * 3)
            else:
                overflow   =   self.overflow
        else:
            coord = np.resize(np.copy(self.gl_coord), mx * 3)
            norm  = np.resize(np.copy(self.gl_norm), mx * 3)
            gl_uvcoord = self.gl_uvcoord
            overflow   =   self.overflow

        return (coord, norm, gl_uvcoord, vertsperface, faceverts, overflow, mapping)

    def createGLFaces(self, nfaces, ufaces, prim, groups):
        self.loadedgroups = groups
        self.prim = prim
        self.n_faces = nfaces
        self.n_fuvs =  ufaces
        self.group = np.zeros(nfaces, dtype=np.uint16)

        self.fverts = np.zeros((self.prim, 3), dtype=np.uint32)
        # fill faces and group buffer
        # ( array of numbers per face determining the group-number )

        cnt = 0
        for num, npelem in enumerate (self.npGrpNames):
            elem = npelem.decode("utf-8")
            if self.visible is not None and elem not in self.visible:
                continue
            faces = groups[elem]["v"]
            for face in faces:
                l = len(face)
                self.fverts[cnt] = face[:3]
                cnt += 1
                # rest for quad and n-gons 
                if l > 3:
                    i=2
                    while i < l-1:
                        self.fverts[cnt] = [face[0], face[i], face[i+1]]
                        cnt += 1
                        i += 1

        # resize to visible groups only TODO not sure if it should stay like this
        #
        self.fverts.resize((cnt, 3), refcheck=False)
        self.n_fverts = cnt * 3

        # the indices (icoord) are simply the flattened fverts of the triangles
        #
        self.gl_icoord =  self.fverts.copy().reshape(self.n_fverts) # Numpy 2.1 supports option copy here

        self.gl_coord = self.coord.flatten()
        self.gl_coord_o = self.gl_coord.copy()  # create a copy for original values
        if self.is_base:
            self.gl_coord_w = self.gl_coord.copy()          # basemesh: create another one for working

        # for no UV map, use an empty array
        #
        if self.n_fuvs > 0:
            self.gl_uvcoord = self.uvs.flatten()
        else:
            self.gl_uvcoord = np.zeros(2 * self.n_fverts, dtype=np.float32)


        return self.calcNormals()

    def getPosition(self, num):
        """
        get position of one vertex based on gl_coord
        """
        m = num*3
        return (self.gl_coord[m], self.gl_coord[m+1], self.gl_coord[m+2])

    def getMeanPosition(self, arr):
        """
        used for skeleton mainly, mean postion of an array, based on gl_coord
        """
        mean = [ 0.0, 0.0, 0.0]
        for i in arr:
            m = i*3
            mean[0] += self.gl_coord[m] 
            mean[1] += self.gl_coord[m+1] 
            mean[2] += self.gl_coord[m+2] 
        n = len(arr)
        return ([mean[0] / n, mean[1] / n, mean[2] / n] )

    def resetMesh(self):
        self.gl_coord[:] = self.gl_coord_o[:] # get back the copy

    def createWCopy(self):
        self.gl_coord_w[:] = self.gl_coord[:]

    def resetFromCopy(self):
        self.gl_coord[:] = self.gl_coord_w[:]

    def hideVertices(self, verts):
        numind = len(self.gl_icoord) -2
        w = np.resize(verts, self.n_verts)
        #
        # bool copy to end
        #
        for (source, dest) in self.overflow:
            w[dest] = w[source]
        #
        self.gl_hicoord = np.zeros(len(self.gl_icoord), dtype=np.uint32)
        scnt = 0
        dcnt = 0
        while scnt < numind:

            # if all 3 verts are false, triangle is created
            #
            if not (w[self.gl_icoord[scnt]] and w[self.gl_icoord[scnt+1]] and w[self.gl_icoord[scnt+2]]):
                self.gl_hicoord[dcnt:dcnt+3] = self.gl_icoord[scnt:scnt+3]
                dcnt += 3
            scnt += 3
        self.gl_hicoord.resize(dcnt, refcheck=False)

    def hideApproxVertices(self, asset, base, verts):
        self.gl_hicoord = np.zeros(len(self.gl_icoord), dtype=np.uint32)
        scnt = 0
        dcnt = 0

        w = np.resize(verts, base.n_verts)
        for (source, dest) in base.overflow:
            w[dest] = w[source]

        ref = np.resize(asset.ref_vIdxs,(self.n_verts,3))
        for (source, dest) in self.overflow:
            ref[dest] = ref[source]

        numind = len(self.gl_icoord) -2
        while scnt < numind:
            n1 = self.gl_icoord[scnt]
            n2 = self.gl_icoord[scnt+1]
            n3 = self.gl_icoord[scnt+2]
            if not (  w[ref[n1][0]] and w[ref[n1][1]] and  w[ref[n1][2]] and \
                    w[ref[n2][0]] and w[ref[n2][1]] and  w[ref[n2][2]] and \
                    w[ref[n3][0]] and w[ref[n3][1]] and  w[ref[n3][2]] ):
                self.gl_hicoord[dcnt:dcnt+3] = self.gl_icoord[scnt:scnt+3]
                dcnt += 3
            scnt += 3
        self.gl_hicoord.resize(dcnt, refcheck=False)

    def hiddenMask(self):
        if self.gl_hicoord is None:
            return None

        indlen = len(self.gl_hicoord)

        usedmax = len(self.gl_uvcoord) // 2
        ba = np.full((usedmax), 0)
        for cnt in range(0, indlen):
            ba[self.gl_hicoord[cnt]] = 1

        # nothing deleted?
        if np.all(ba):
            return None

        return (ba)

    def createMapping(self, mask):
        """
        creates a mapping index reduced by hidden coords + highest value
        """
        usedmax = len(mask)
        mapping = np.full(usedmax, -1, dtype=np.int32)
        fill = 0
        for cnt in range(0, usedmax):
            if mask[cnt] == 1:
                mapping[cnt] = fill
                fill +=1
        return(mapping, fill)

    def optimizeHiddenMesh(self, bweights):
        """
        duplicate the mesh for effective saving without hidden vertices
        (e.g. glTF)
        """
        
        # check if we have hidden verts
        #
        self.debug ("Optimizing hidden mesh: " + self.filename)

        mask = self.hiddenMask()
        if mask is None:
            return None, None, None, None, None, None

        # in gl_hicoord there is already a "compressed" index
        # so this creates a shorter version already
        # return self.gl_hicoord, self.gl_coord, self.gl_uvcoord, self.gl_norm

        # create a mapping index reduced by hidden coords
        #
        usedmax = len(mask)
        mapping, newcoord = self.createMapping(mask)

        # we now know size, so create temporary arrays
        #
        indlen = len(self.gl_hicoord)
        gl_index = np.zeros(indlen, dtype=np.uint32)
        gl_coord = np.zeros(newcoord*3,  dtype=np.float32)
        gl_uvcoord = np.zeros(newcoord*2,  dtype=np.float32)
        gl_norm = np.zeros(newcoord*3,  dtype=np.float32)

        # do correction of flattened array
        #
        for cnt in range(0, usedmax):
            d = mapping[cnt]
            if d != -1:
                s2 = cnt * 2
                s3 = cnt * 3
                d2 = d * 2
                d3 = d * 3

                gl_coord[d3] = self.gl_coord[s3]
                gl_coord[d3+1] = self.gl_coord[s3+1]
                gl_coord[d3+2] = self.gl_coord[s3+2]

                gl_uvcoord[d2] = self.gl_uvcoord[s2]
                gl_uvcoord[d2+1] = self.gl_uvcoord[s2+1]

                gl_norm[d3] = self.gl_norm[s3]
                gl_norm[d3+1] = self.gl_norm[s3+1]
                gl_norm[d3+2] = self.gl_norm[s3+2]

        for cnt in range(0,  indlen):
            gl_index[cnt] =  mapping[self.gl_hicoord[cnt]]

        if bweights is not None:

            self.debug("need to optimize weights")

            # create an overflow dictionary
            overflow = {}
            if self.overflow is not None:
                for s,d  in self.overflow:
                    if s not in overflow:
                        overflow[s] = []
                    overflow[s].append(d)

            # vertex numbers of weights index array must be replaced by new numbers,
            # the needed weights will be copied
            #
            nweights = {}
            for elem in bweights:
                narr = []
                warr = []
                m = 0
                for i, n in enumerate(bweights[elem][0]):
                    d = mapping[n]
                    if d != -1:
                        narr.append(d)
                        warr.append(bweights[elem][1][i])
                        m += 1
                    else:
                        if n in overflow:
                            for alts in overflow[n]:
                                d = mapping[alts]
                                if d != -1:
                                    narr.append(d)
                                    warr.append(bweights[elem][1][i])
                                    m += 1

                if m > 0:
                    nweights[elem] = (np.array(narr, dtype=np.uint32), np.array(warr, dtype=np.float32))
        else:
            nweights = None

        overflow = self.shortenOverflow(mapping)

        return gl_index, gl_coord, gl_uvcoord, gl_norm, nweights, overflow

    def getInitialCopyForSlider(self, factor, targetlower, targetupper):
        """
        called when starting work with one slider, a copy without the value
        of this slider is created.
        """
        print ("getInitialCopyForSlider")
        self.createWCopy()
        if factor == 0.0:
            return
        else:
            if factor < 0.0:
                if targetlower is None:
                    return
                verts = targetlower.verts
                data  = targetlower.data
                factor = -factor
            elif factor > 0.0:
                verts = targetupper.verts
                data  = targetupper.data
            for i in range(0, len(verts)):
                x = verts[i] * 3
                self.gl_coord_w[x]   = self.gl_coord[x]   - factor * data[i][0]
                self.gl_coord_w[x+1] = self.gl_coord[x+1] - factor * data[i][1]
                self.gl_coord_w[x+2] = self.gl_coord[x+2] - factor * data[i][2]

        self.overflowCorrection(self.gl_coord_w)
        # self.calcNormals()

    def updateByTarget(self, factor, targetlower, targetupper):
        """
        updates the mesh when slider is moved
        """
        if factor == 0.0:
            self.gl_coord[:] = self.gl_coord_w[:]
            return

        if factor < 0.0:
            if targetlower is None:
                return
            verts = targetlower.verts * 3
            data  = targetlower.data.ravel()
            factor = -factor
        elif factor > 0.0:
            verts = targetupper.verts * 3
            data  = targetupper.data.ravel()

        srcVerts = np.s_[...]
        self.gl_coord[verts] = self.gl_coord_w[verts] + data[srcVerts][::3] * factor
        self.gl_coord[verts+1] = self.gl_coord_w[verts+1] + data[srcVerts][1::3] * factor
        self.gl_coord[verts+2] = self.gl_coord_w[verts+2] + data[srcVerts][2::3] * factor

        # overflow vertices
        #
        self.overflowCorrection(self.gl_coord)

    def setTarget(self, factor, targetlower, targetupper):
        """
        updates from file (all done on basemesh directly)
        no overflow correction
        """
        if factor < 0.0:
            if targetlower is None:
                return
            verts = targetlower.verts * 3
            data  = targetlower.data.ravel()
            factor = -factor
        elif factor > 0.0:
            if targetupper is None:
                return
            verts = targetupper.verts * 3
            data  = targetupper.data.ravel()

        srcVerts = np.s_[...]
        self.gl_coord[verts] += data[srcVerts][::3] * factor
        self.gl_coord[verts+1] += data[srcVerts][1::3] * factor
        self.gl_coord[verts+2] += data[srcVerts][2::3] * factor

    def resetToNonMacroTargets(self):
        """
        reset to original mesh + add all changes of non-macrotargets
        """
        print ("+++ reset mesh and add non macro targets")
        self.resetMesh()
        targets = self.glob.Targets.modelling_targets
        for target in targets:
            if target.value != 0.0 and target.macro is None:
                # print ("Set " + target.name)
                self.setTarget(target.value / 100, target.decr, target.incr)

        # overflow vertices and copy to non-macrobuffer
        #
        self.overflowCorrection(self.gl_coord)
        self.gl_coord_mn =  self.gl_coord.copy()

    def prepareMacroBuffer(self):
        """
        copy original mesh + add all changes of non-macrotargets
        """
        print ("+++ Prepare Buffer")
        self.gl_coord_mn =  self.gl_coord.copy()
        self.gl_coord_mm = np.zeros_like(self.gl_coord)


    def addTargetToMacroBuffer(self, factor, target):
        """
        updates a special buffer for a macro target
        """
        m = target.data.ravel()
        verts = target.verts * 3

        srcVerts = np.s_[...]
        self.gl_coord_mm[verts] += m[srcVerts][::3] * factor
        self.gl_coord_mm[verts+1] += m[srcVerts][1::3] * factor
        self.gl_coord_mm[verts+2] += m[srcVerts][2::3] * factor


    def addMacroBuffer(self):
        """
        after changing a macro it will be added
        make sure to write in same buffer (out will avoid to get a new one)
        """
        print ("+++ Add macro to character")
        np.add(self.gl_coord_mm, self.gl_coord_mn, out=self.gl_coord)  
        self.overflowCorrection(self.gl_coord)
        self.gl_coord_mm = np.zeros_like(self.gl_coord)

    def approxToBasemesh(self, asset, base):
        """
        updates the mesh, barycentric approximation (assets)
        """

        b = base.gl_coord
        w = asset.weights
        o = asset.offsets

        verts = asset.ref_vIdxs * 3 # index (v0, v1, v2)

        """
        i = 0
        j = 0
        for v in verts:
            self.gl_coord[i]   = w[j,0]*b[v[0]]   + w[j,1]*b[v[1]]  +  w[j,2]*b[v[2]]   + o[j,0]
            self.gl_coord[i+1] = w[j,0]*b[v[0]+1] + w[j,1]*b[v[1]+1] + w[j,2]*b[v[2]+1] + o[j,1]
            self.gl_coord[i+2] = w[j,0]*b[v[0]+2] + w[j,1]*b[v[1]+2] + w[j,2]*b[v[2]+2] + o[j,2]
            i += 3
            j += 1

        """
        vlen = len(verts) * 3

        if asset.scaleMat is not None:
            (x, y, z)  = (asset.scaleMat[0,0], asset.scaleMat[1,1], asset.scaleMat[2,2])
            self.gl_coord[:vlen:3]  = w[:,0]*b[verts[:,0]] + w[:,1]*b[verts[:,1]] +  w[:,2]*b[verts[:,2]] + o[:,0] * x
            self.gl_coord[1:vlen:3] = w[:,0]*b[verts[:,0]+1] + w[:,1]*b[verts[:,1]+1] +  w[:,2]*b[verts[:,2]+1] + o[:,1] * y
            self.gl_coord[2:vlen:3] = w[:,0]*b[verts[:,0]+2] + w[:,1]*b[verts[:,1]+2] +  w[:,2]*b[verts[:,2]+2] + o[:,2] * z
        else:
            self.gl_coord[:vlen:3]  = w[:,0]*b[verts[:,0]] + w[:,1]*b[verts[:,1]] +  w[:,2]*b[verts[:,2]] + o[:,0]
            self.gl_coord[1:vlen:3] = w[:,0]*b[verts[:,0]+1] + w[:,1]*b[verts[:,1]+1] +  w[:,2]*b[verts[:,2]+1] + o[:,1]
            self.gl_coord[2:vlen:3] = w[:,0]*b[verts[:,0]+2] + w[:,1]*b[verts[:,1]+2] +  w[:,2]*b[verts[:,2]+2] + o[:,2]

        # do not forget the overflow vertices
        #
        self.overflowCorrection(self.gl_coord)


    def precalculateApproxInRestPose(self, asset, base):
        self.debug("precalculate asset for restpose " + asset.name)
        self.approxToBasemesh(asset, base)
        self.gl_coord_w =  self.gl_coord.copy()

    def _getMinMaxValues(self, coord):
        """
        calculate numbers of vertices, which are on the outside for later use
        do that only for visible groups
        """
        ncoord = np.zeros((self.n_origverts, 3), dtype=np.float32)
        for i in range (0, self.n_fverts):
            cnt = self.gl_icoord[i]
            if cnt < self.n_origverts:
                ncoord[cnt] = coord[cnt]
        return np.argmin(ncoord, axis=0),  np.argmax(ncoord, axis=0)

    def precalculateDimension(self):
        self.min_index, self.max_index = self._getMinMaxValues(self.coord)

    def precalculatePosedDimension(self):
        poscoord = np.reshape(self.gl_coord, (len(self.gl_coord) // 3,3))
        self.minpose_index, self.maxpose_index = self._getMinMaxValues(poscoord)

    def boundingBox(self):
        if self.min_index is None:
            self.precalculateDimension()
        return(self.gl_coord[self.min_index[0]*3], self.gl_coord[self.min_index[1]*3+1], self.gl_coord[self.min_index[2]*3+2], \
            self.gl_coord[self.max_index[0]*3], self.gl_coord[self.max_index[1]*3+1], self.gl_coord[self.max_index[2]*3+2])

    def getCenterWidth(self):
        return ((self.gl_coord[self.max_index[0]*3]+self.gl_coord[self.min_index[0]*3])/2.0)

    def getCenterHeight(self):
        return ((self.gl_coord[self.max_index[1]*3+1]+self.gl_coord[self.min_index[1]*3+1])/2.0)

    def getCenterDepth(self):
        return ((self.gl_coord[self.max_index[2]*3+2]+self.gl_coord[self.min_index[2]*3+2])/2.0)

    def getCenter(self):
        a =  self.gl_coord
        n = [ self.getCenterWidth(),  self.getCenterHeight(), self.getCenterDepth() ]
        return (n)

    def getLowestPos(self, posed=False):
        if posed and self.minpose_index is not None:
            return self.gl_coord[self.minpose_index[1]*3+1]
        else:
            return self.gl_coord[self.min_index[1]*3+1]

    def setNoPose(self):
        self.minpose_index = None
        self.maxpose_index = None

    def getHeightInUnits(self):
        return (self.gl_coord[self.max_index[1]*3+1]-self.gl_coord[self.min_index[1]*3+1])

    def getMeasure(self, vindex):
        """
        create a measurement, results in an array of vertices for presentation and the result (length)
        """
        lx = len(vindex)
        mcoords = np.zeros((lx, 3), dtype=np.float32)
        c = 0
        for i in vindex:
            x = i *3
            mcoords[c] = [self.gl_coord[x], self.gl_coord[x+1], self.gl_coord[x+2] ]
            c += 1

        measure = 0
        ox = 0
        for n in range(1, lx):
            d = mcoords[ox] - mcoords[n]
            measure += np.sqrt(d.dot(d))
            ox = n

        return measure, mcoords

    def calculateAttachedGeom(self, faces):
        """
        get a dictionary of attached facenumbers and edgenumbers per vertex
        for borders, get the next border neighbours (used in loop subdivision)
        """
        attachedFaces = {}
        attachedEdges = {}

        # the neighbours on a border of a single vertex will be two vertices, set them all to -1 before
        # if both entries are not -1 we found the border vertices
        #
        borderneighbour = np.full((self.n_origverts,2), 0xffffffff, dtype=np.uint32)
        for fn, verts in enumerate(faces):
            for i in range(0,3):
                j = (i+1) % 3               # to generate 0, 1, 2, 0
                v = verts[i]

                if v not in attachedFaces:      # create face dictionary
                    attachedFaces[v] = [fn]
                else:
                    attachedFaces[v].append(fn)

                if v > verts[j]:
                    v1, v2 = verts[j], v
                else:
                    v1, v2 = v, verts[j]

                if v1 not in attachedEdges:     # create edge dictionary
                    attachedEdges[v1] = {}
                if v2 not in attachedEdges[v1]:
                    attachedEdges[v1][v2] = [fn, -1, None] # None will hold the future index for gl
                else:
                    attachedEdges[v1][v2][1] = fn

        for v1 in attachedEdges:
            for v2 in attachedEdges[v1]:
                if attachedEdges[v1][v2][1] == -1:
                    if borderneighbour[v1][0] == 0xffffffff:
                        borderneighbour[v1][0] = v2
                    else:
                        borderneighbour[v1][1] = v2

                    if borderneighbour[v2][0] == 0xffffffff:
                        borderneighbour[v2][0] = v1
                    else:
                        borderneighbour[v2][1] = v1

        return attachedFaces, attachedEdges, borderneighbour


    def __del__(self):
        self.env.logLine (4, " -- delete object3d: " + str(self.name))
