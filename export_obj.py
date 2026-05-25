"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck, Elvaerwyn_MH2 2026

    Classes:
    * objExport

    wavefront exporter
"""

import os
import numpy as np

class objExport:
    def __init__(self, glob, exportfolder, imagefolder="textures", hiddenverts=False, onground=True, helper=False, normals=False, scale=0.1):

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
        self.animation = False  # Controlled via UI panel tracking checkboxes

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
        
        # --- REPAIRED: Safely parse multidimensional numpy overflow arrays ---
        overflow = {}
        if ov is not None:
            for l in ov:
                try:
                    # If it's a coordinate pair array [vertex_index, uv_index]
                    if hasattr(l, "__len__") and len(l) >= 2:
                        overflow[int(l[1])] = int(l[0])
                    else:
                        overflow[int(l)] = int(l)
                except (TypeError, ValueError, IndexError):
                    continue
        x = 0

        if self.normals:
            for n in vpf:
                out = "f "
                for i in range(n):
                    uvface = faces[x]
                    face = overflow[uvface] if uvface in overflow else uvface
                    out += "%d/%d/%d " % (face+self.startvert, uvface+self.startuv, face+self.startvert)
                    x += 1
                self.facelines.append(out + "\n")
        else:
            for n in vpf:
                out = "f "
                for i in range(n):
                    uvface = faces[x]
                    face = overflow[uvface] if uvface in overflow else uvface
                    out += "%d/%d " % (face+self.startvert, uvface+self.startuv)
                    x += 1
                self.facelines.append(out + "\n")

        self.startvert += self.obj[num]["lenV"]
        self.startuv   += self.obj[num]["lenUV"]


    def addMaterial(self, num, material):
        # FIX: Explicitly unpack R, G, B array elements to prevent list-type mismatch crashes
        diff = getattr(material, "diffuseColor", [0.8, 0.8, 0.8])
        if hasattr(diff, "__len__") and len(diff) >= 3:
            d_r, d_g, d_b = diff[0], diff[1], diff[2]
        else:
            d_r, d_g, d_b = 0.8, 0.8, 0.8

        spec = getattr(material, "specularColor", [0.8, 0.8, 0.8])
        if hasattr(spec, "__len__") and len(spec) >= 3:
            s_r, s_g, s_b = spec[0], spec[1], spec[2]
        else:
            s_r, s_g, s_b = 0.8, 0.8, 0.8

        emis = getattr(material, "emissiveColor", [0.0, 0.0, 0.0])
        if hasattr(emis, "__len__") and len(emis) >= 3:
            e_r, e_g, e_b = emis[0], emis[1], emis[2]
        else:
            e_r, e_g, e_b = 0.0, 0.0, 0.0

        alpha = 1
        rough = getattr(material, "roughnessFactor", 0.5)
        metal = getattr(material, "metallicFactor", 0.0)

        self.matlines.append("\n")
        self.matlines.append("newmtl " + material.name + "\n")
        # FIX: Pass direct floating point values into the formatter template strings
        self.matlines.append("Kd %.4f %.4f %.4f\n" % (d_r, d_g, d_b))
        self.matlines.append("Ks %.4f %.4f %.4f\n" % (s_r, s_g, s_b))
        self.matlines.append("Ke %.4f %.4f %.4f\n" % (e_r, e_g, e_b))
        self.matlines.append("d %.4f\n" % alpha)
        self.matlines.append("Pr %.4f\n" % rough)
        self.matlines.append("Pm %.4f\n" % metal)

        if hasattr(material, "aomapTexture") and material.aomapTexture:
            if self.addImage("map_Ka", material.aomapTexture) is False: return False
        if hasattr(material, "diffuseTexture") and material.diffuseTexture:
            diffusename = material.saveDiffuse() if getattr(material, 'colorationMethod', 0) > 0 else material.diffuseTexture
            if self.addImage("map_Kd", diffusename) is False: return False
        if hasattr(material, "metallicRoughnessTexture") and material.metallicRoughnessTexture:
            if self.addImage("map_Pr -imfchan g", material.metallicRoughnessTexture) is False: return False
            self.addImage("map_Pm -imfchan b", material.metallicRoughnessTexture, copy=False)
        if hasattr(material, "emissiveTexture") and material.emissiveTexture:
            if self.addImage("map_Ke", material.specularmapTexture) is False: return False
        if hasattr(material, "normalmapTexture") and material.normalmapTexture:
            if self.addImage("map_Bump", material.normalmapTexture) is False: return False
        return True

    def ascSave(self, baseclass, filename):
        # Read layout panel option values passed down from gui/exporter.py
        is_anim_enabled = getattr(self, 'animation', False)
        is_pose_enabled = getattr(self, 'inpose', True) # Set via Character Posed button
        
        has_bvh = baseclass is not None and getattr(baseclass, 'bvh', None) is not None
        skeleton = getattr(baseclass, 'skeleton', None) if baseclass else None

        # PATH A: Export entire animation stack sequence loop
        if is_anim_enabled and has_bvh and skeleton is not None:
            bvh = baseclass.bvh
            nFrames = bvh.frameCount
            base_path, ext = os.path.splitext(filename)
            
            for frame in range(nFrames):
                if skeleton == getattr(baseclass, 'default_skeleton', None):
                    skeleton.pose(bvh.joints, frame, True)
                else:
                    skeleton.poseByReference(bvh.joints, frame)
                
                if hasattr(baseclass.baseMesh, 'updateDeformations'):
                    baseclass.baseMesh.updateDeformations()

                frame_filename = f"{base_path}_{frame:03d}{ext}"
                self.obj, self.coordlines, self.normlines, self.uvlines, self.facelines, self.matlines = [], [], [], [], [], []
                self.startvert, self.startuv = 1, 1
                
                if self._collectSceneGeometry(baseclass, skeleton) is False: return False
                if self._writeSnapshotToDisk(frame_filename) is False: return False
            return True
            
        # PATH B: Export single static snapshot (Posed or Rest Bind)
        else:
            self.obj, self.coordlines, self.normlines, self.uvlines, self.facelines, self.matlines = [], [], [], [], [], []
            self.startvert, self.startuv = 1, 1
            
            # If Posed is unchecked, pass None to export the original rest bind T-pose
            active_skeleton = skeleton if is_pose_enabled else None
            
            if self._collectSceneGeometry(baseclass, active_skeleton) is False: return False
            return self._writeSnapshotToDisk(filename)


    def _writeSnapshotToDisk(self, filename):
        if not self.obj:
            self.env.last_error = "No objects found in the workspace scene to export!"
            return False

        materialfile = filename[:-4] + ".mtl"
        header = "# MakeHuman exported OBJ\nmtllib " + os.path.basename(materialfile) + "\n"
        matheader = "# MakeHuman exported MTL\n"

        for i, obj in enumerate(self.obj): self.addCoords(i, obj["c"])
        if self.normals:
            for i, obj in enumerate(self.obj): self.addNormals(i, obj["no"])
        for i, obj in enumerate(self.obj): self.addUVCoords(i, obj["uv"])
        for i, obj in enumerate(self.obj): self.addFaces(i, obj["name"], obj["mat"], obj["vpf"], obj["f"], obj["o"])
        for i, obj in enumerate(self.obj):
            if self.addMaterial(i, obj["mat"]) is False: return False

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

        try:
            with open(materialfile, 'w', encoding="utf-8") as f:
                f.write(matheader)
                f.writelines(self.matlines)
        except IOError as error:
            self.env.last_error = str(error)
            return False
        return True

    def _collectSceneGeometry(self, baseclass, skeleton=None):
        has_character = baseclass is not None and getattr(baseclass, 'baseMesh', None) is not None
        if self.onground and has_character:
            self.lowestPos = baseclass.getLowestPos() * self.scale
        else:
            self.lowestPos = 0.0

        if has_character:
            if baseclass.proxy is None or self.helper is True:
                obj = baseclass.baseMesh
                hiddenverts = True if self.helper else self.hiddenverts
            else:
                obj = baseclass.attachedAssets.obj if hasattr(baseclass.attachedAssets, 'obj') else baseclass.baseMesh
                hiddenverts = self.hiddenverts

            mat = obj.material

            # 1. Gather baseline character geometry definitions safely
            (baseline_coord, norm, uvcoord, vpface, faces, overflow, mapping) = obj.getVisGeometry(hiddenverts, self.helper)
            
            if vpface is None or (isinstance(vpface, np.ndarray) and vpface.size == 0) or not list(vpface):
                vpface = [3] * (len(faces) // 3)

            # 2. Assign pre-deformed character baseline vertices directly
            coord = baseline_coord

            # 3. Dynamically recalculate clean smooth normals based on active face windings
            if skeleton is not None or self.normals:
                try:
                    verts = coord.reshape(-1, 3)
                    new_normals = np.zeros_like(verts, dtype=np.float32)
                    face_ptr = 0
                    for num_verts in vpface:
                        if face_ptr + num_verts <= len(faces):
                            f_indices = faces[face_ptr : face_ptr + num_verts]
                            face_ptr += num_verts
                            if any(idx >= len(verts) for idx in f_indices): continue
                            
                            if num_verts == 3:
                                f_verts = verts[f_indices]
                                v0 = f_verts[0]
                                v1 = f_verts[1]
                                v2 = f_verts[2]
                                face_normal = np.cross(v1 - v0, v2 - v0)
                                for idx in f_indices:
                                    new_normals[idx] += face_normal
                            elif num_verts == 4:
                                f_verts = verts[f_indices]
                                v0 = f_verts[0]
                                v1 = f_verts[1]
                                v2 = f_verts[2]
                                v3 = f_verts[3]
                                face_normal = np.cross(v1 - v0, v2 - v0) + np.cross(v2 - v0, v3 - v0)
                                for idx in f_indices:
                                    new_normals[idx] += face_normal
                        else:
                            break
                    norms_len = np.linalg.norm(new_normals, axis=1, keepdims=True)
                    safe_len = np.where(norms_len > 0, norms_len, 1.0)
                    norm = (new_normals / safe_len).flatten()
                except Exception as norm_err:
                    print(f"Failed to calculate character smooth normals: {str(norm_err)}")

            self.obj.append({
                "name": "base", 
                "mat": mat, 
                "c": coord, 
                "no": norm, 
                "uv": uvcoord, 
                "vpf": vpface, 
                "f": faces, 
                "o": overflow
            })

            # 4. COLLECT UNIQUE WORKSPACE ASSETS & STUDIO PROPS
            unique_assets = []
            seen_mesh_ids = set()

            # Source A: Check human character attachment containers (clothing, hair, accessories)
            if hasattr(baseclass, 'attachedAssets') and baseclass.attachedAssets is not None:
                raw_clothing = []
                if hasattr(baseclass.attachedAssets, 'getAssets'):
                    raw_clothing = baseclass.attachedAssets.getAssets()
                elif hasattr(baseclass.attachedAssets, 'assets') and baseclass.attachedAssets.assets:
                    raw_clothing = baseclass.attachedAssets.assets if isinstance(baseclass.attachedAssets.assets, list) else list(baseclass.attachedAssets.assets.values())
                
                for elem in raw_clothing:
                    if elem and getattr(elem, 'obj', None) is not None:
                        obj_id = id(elem.obj)
                        if obj_id not in seen_mesh_ids:
                            seen_mesh_ids.add(obj_id)
                            unique_assets.append({"name": getattr(elem, 'name', 'garment'), "obj": elem.obj, "is_prop": False})

            # Source B: Check the Global Studio Props pool (Cubes, Balls, spawned furniture primitives)
            global_pool = None
            if hasattr(self, 'glob') and hasattr(self.glob, 'custom_props_list'):
                global_pool = self.glob.custom_props_list
            elif hasattr(baseclass, 'glob') and hasattr(baseclass.glob, 'custom_props_list'):
                global_pool = baseclass.glob.custom_props_list

            if global_pool:
                for elem in global_pool:
                    if elem and getattr(elem, 'visible', True):
                        mesh_obj = None
                        if hasattr(elem, 'mesh_reference') and elem.mesh_reference:
                            mesh_obj = getattr(elem.mesh_reference, 'obj', None)
                        
                        if mesh_obj is not None:
                            obj_id = id(mesh_obj)
                            if obj_id not in seen_mesh_ids:
                                seen_mesh_ids.add(obj_id)
                                unique_assets.append({
                                    "name": getattr(elem, 'name', 'studio_prop'),
                                    "obj": mesh_obj,
                                    "is_prop": True,
                                    "pos": getattr(elem, 'position', np.array([0., 0., 0.])),
                                    "rot": getattr(elem, 'rotation', np.array([0., 0., 0.])),
                                    "scl": getattr(elem, 'scale', np.array([1., 1., 1.]))
                                })
            # 5. Process and loop over all unified scene items into file buffer
            for item in unique_assets:
                c_obj = item["obj"]
                c_mat = c_obj.material if hasattr(c_obj, 'material') else None
                
                # Fetch raw vertex allocations
                (baseline_a_coord, a_norm, a_uvcoord, a_vpface, a_faces, a_overflow, a_mapping) = c_obj.getVisGeometry(self.hiddenverts, self.helper)
                
                if a_vpface is None or (isinstance(a_vpface, np.ndarray) and a_vpface.size == 0) or not list(a_vpface):
                    a_vpface = [3] * (len(a_faces) // 3)
                
                # Handle Spatial Adjustments for Studio Props
                if item["is_prop"]:
                    prop_verts = baseline_a_coord.copy().reshape(-1, 3)
                    
                    # A. Apply Scale
                    scl = item["scl"]
                    prop_verts *= scl
                    
                    # B. Apply Rotation (Euler Pitch/Yaw/Roll conversion pass)
                    rot_deg = item["rot"]
                    if np.any(rot_deg != 0.0):
                        rad = np.radians(rot_deg)
                        cx, sx = np.cos(rad[0]), np.sin(rad[0])
                        cy, sy = np.cos(rad[1]), np.sin(rad[1])
                        cz, sz = np.cos(rad[2]), np.sin(rad[2])
                        
                        Rx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]])
                        Ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
                        Rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
                        R = Rz @ Ry @ Rx
                        prop_verts = prop_verts @ R.T
                    
                    # C. Apply Translation Position Offset
                    pos = item["pos"]
                    prop_verts += pos
                    
                    a_coord = prop_verts.flatten().astype(np.float32)
                else:
                    a_coord = baseline_a_coord

                # Dynamically recalculate crisp outward normals relative to active world posture position
                if skeleton is not None or self.normals:
                    try:
                        a_verts = a_coord.reshape(-1, 3)
                        new_a_normals = np.zeros_like(a_verts, dtype=np.float32)
                        a_face_ptr = 0
                        for num_verts in a_vpface:
                            if a_face_ptr + num_verts <= len(a_faces):
                                f_indices = a_faces[a_face_ptr : a_face_ptr + num_verts]
                                a_face_ptr += num_verts
                                if any(idx >= len(a_verts) for idx in f_indices): continue
                                
                                if num_verts == 3:
                                    f_verts = a_verts[f_indices]
                                    v0 = f_verts[0]
                                    v1 = f_verts[1]
                                    v2 = f_verts[2]
                                    face_normal = np.cross(v1 - v0, v2 - v0)
                                    for idx in f_indices: 
                                        new_a_normals[idx] += face_normal
                                        
                                elif num_verts == 4:
                                    f_verts = a_verts[f_indices]
                                    v0 = f_verts[0]
                                    v1 = f_verts[1]
                                    v2 = f_verts[2]
                                    v3 = f_verts[3]
                                    face_normal = np.cross(v1 - v0, v2 - v0) + np.cross(v2 - v0, v3 - v0)
                                    for idx in f_indices: 
                                        new_a_normals[idx] += face_normal
                            else:
                                break
                        a_norms_len = np.linalg.norm(new_a_normals, axis=1, keepdims=True)
                        a_safe_len = np.where(a_norms_len > 0, a_norms_len, 1.0)
                        a_norm = (new_a_normals / a_safe_len).flatten()
                    except Exception as prop_norm_err:
                        print(f"Failed to calculate asset smooth normals: {str(prop_norm_err)}")
                        
                self.obj.append({
                    "name": item["name"], 
                    "mat": c_mat, 
                    "c": a_coord, 
                    "no": a_norm, 
                    "uv": a_uvcoord, 
                    "vpf": a_vpface, 
                    "f": a_faces, 
                    "o": a_overflow
                })

            return True




