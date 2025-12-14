"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * Material
"""

import os
import numpy
from core.debug import dumper
from opengl.texture import MH_Texture, ImageEdit
from PySide6.QtGui import QColor

class Material:
    def __init__(self, glob, objdir, eqtype):
        self.glob = glob
        self.env = glob.env
        self.mhmatdir = objdir
        self.type = eqtype
        self.tags = []
        self.default()
        self.name = None
        self.filename = None

    def __str__(self):
        return(dumper(self))

    def default(self):
        self.tex_diffuse = None
        self.tex_litsphere = None
        self.tex_aomap = None
        self.tex_nomap = None
        self.tex_mrmap = None
        self.tex_emmap = None
        self.colorationOldColor = [1.0, 1.0, 1.0 ]
        self.colorationOldMethod= 0
        self.colorationMethod = 0 # 0: off, 1: hue-to-fixed, 2: desaturate + color multiply
        self.colorationColor = [1.0, 1.0, 1.0 ]
        self.ambientColor = [1.0, 1.0, 1.0 ]
        self.diffuseColor = [1.0, 1.0, 1.0 ]
        self.specularColor = [0.5, 0.5, 0.5 ]
        self.emissiveColor = [0.0, 0.0, 0.0 ]
        self.metallicFactor = 0.0
        self.roughnessFactor = 0.0
        self.mr_found = False
        self.emissiveFactor = 0.0
        self.transparent = False
        #
        self.alphaToCoverage = False
        self.backfaceCull = False
        #
        self.shader = "phong"
        self.sp_AdditiveShading = 0.0

        self.description = None
        self.aomapIntensity = 1.0
        self.normalmapIntensity = 1.0

    def isExistent(self, filename):
        """
        concatenate / check same folder (mhmatdir ends with the start of filename)
        """
        path = os.path.join(self.mhmatdir, filename)
        if os.path.isfile(path):
            return (path)

        # try if we are in materials
        #
        if self.mhmatdir.endswith("materials"):
            path = os.path.join(self.mhmatdir[:-10], filename)
            if os.path.isfile(path):
                return (path)

        # try to get rid of first directory of filename (notation: unicode)
        #
        if "/" in filename:
            fname = "/".join (filename.split("/")[1:])
            path = os.path.join(self.mhmatdir, fname)
            if os.path.isfile(path):
                return (path)


        # try an "absolute" method when it starts with the type name like "clothes"
        # then delete clothes 
        # in both cases try directly in asset folders
        # for base mesh default is skins
        #
        itype = "skins" if self.type == "base" else self.type

        if filename.startswith(itype):
            if "/" in filename:
                filename = "/".join (filename.split("/")[1:])

        path = os.path.join(self.env.stdSysPath(itype), filename)
        if os.path.isfile(path):
            return (path)

        path = os.path.join(self.env.stdUserPath(itype), filename)
        if os.path.isfile(path):
            return (path)
        
        self.env.logLine(8, "unknown texture " + filename)
            
        return None

    def loadMatFile(self, path):
        """
        mhmat file loader, TODO; cleanup in the end
        """
        self.filename = path
        self.mhmatdir = os.path.dirname(path)

        self.env.logLine(8, "Loading material " + path)
        try:
            f = open(path, "r", encoding="utf-8", errors="ignore")
        except OSError as error:
            self.env.last_error = str(error)
            return (False)

        for line in f:
            words = line.split()
            if len(words) == 0:
                continue
            key = words[0]
            if key in ["#", "//"]:
                continue

            # * if commands make no sense, they will be skipped ... 
            # * check textures and set an absolut path

            if key in ["diffuseTexture", "normalmapTexture", "aomapTexture", "metallicRoughnessTexture", "emissiveTexture"]:
                abspath = self.isExistent(words[1])
                if abspath is not None:
                    setattr (self, key, abspath)

            elif key in ["name", "description"]:
                setattr (self, key, " ".join(words[1:]))
            elif key == "tag":
                self.tags.append( " ".join(words[1:]).lower() )

            # shader is shadertype, old path is replaced by last term. default is phong
            #
            elif key == "shader":
                arg = words[1]
                if "/" in arg:
                    arg = arg.split("/")[-1]
                self.shader = arg

            # simple bools:
            #
            elif key in [ "transparent", "alphaToCoverage", "backfaceCull" ]:
                setattr (self, key, words[1].lower() in ["yes", "enabled", "true"])

            elif key in [ "colorationMethod" ]:
                try:
                    val = int(words[1])
                except:
                    val = 0
                if val > 2:
                    val = 0
                setattr (self, key, val)

            # colors
            #
            elif key in ["ambientColor", "diffuseColor", "emissiveColor", "specularColor", "colorationColor" ]:
                setattr (self, key, [float(w) for w in words[1:4]])

            # intensities (all kind of floats)
            #
            elif key in ["normalmapIntensity", "roughnessFactor", "metallicFactor", "emissiveFactor" ]:
                setattr (self, key, max(0.0, min(1.0, float(words[1]))))
                if key == "roughnessFactor":
                    self.mr_found = True

            # aomap is used different to intensify light
            #
            elif key == "aomapIntensity":
                setattr (self, key, max(0.0, min(2.0, float(words[1]))))

            # shaderparam will be prefixed by sp_, search for litsphere
            #
            elif key == "shaderParam":
                if words[1] == "litsphereTexture":
                    path = self.env.existDataFile("shaders", "litspheres", os.path.basename(words[2]))
                    if path is not None:
                        setattr (self, "sp_litsphereTexture", path)
                    else:
                        self.env.logLine(1, "missing litsphereTexture: " + words[2] + " (phong shading will be used)")
                elif words[1] == "AdditiveShading":
                    setattr (self, "sp_" + words[1], float(words[2]))
                else:
                    setattr (self, "sp_" + words[1], words[2])

            # shaderconfig no longer supported, done by testing availability of filenames
            #
            elif key == "shaderConfig":
                pass

        if self.mr_found is False:
            self.roughnessFactor = 1.0 - sum(self.specularColor) / 3

        if self.name is None:
            self.name = os.path.basename(path)
        if self.description is None:
            self.description = self.name + " material"

        # avoid empty litsphere textures (switch back to phong)
        #
        if self.shader == "litsphere" and not hasattr(self, "sp_litsphereTexture"):
            self.shader = "phong"

        # print(self)
        return (True)

    def textureRelName(self, path):
        """
        path name always in URI syntax, needed as a base
        """
        path = self.env.formatPath(path)
        fobjdir = self.env.formatPath(self.mhmatdir)

        if path.startswith(fobjdir):
            relpath = path[len(fobjdir)+1:]
            return(relpath)

        test = self.env.formatPath(self.env.stdSysPath(self.type))
        rest = None
        if fobjdir.startswith(test):
            rest = fobjdir[len(test)+1:]
        
        test = self.env.formatPath(self.env.stdUserPath(self.type))
        if fobjdir.startswith(test):
            rest = fobjdir[len(test)+1:]

        # URI syntax
        if rest:
            asset = rest.split("/")[0]
            relpath = self.type + "/" + asset + "/" + os.path.basename(path)
        else:
            relpath = os.path.basename(path)
        return(self.env.formatPath(relpath))

    def roundColor(self, color):
        for i, elem in enumerate(color):
            color[i] = round(elem, 4)

    def saveMatFile(self, path):
        self.env.logLine(8, "Saving material " + path)

        # avoid too many digits
        #
        self.roundColor(self.ambientColor)
        self.roundColor(self.diffuseColor)
        self.roundColor(self.specularColor)
        self.roundColor(self.emissiveColor)

        if hasattr(self, "diffuseTexture"):
            diffuse = "diffuseTexture " + self.textureRelName(self.diffuseTexture) + "\n"
        else:
            diffuse = ""

        if hasattr(self, "normalmapTexture"):
            normal = "normalmapTexture " + self.textureRelName(self.normalmapTexture) + \
                "\nnormalmapIntensity " + str(self.normalmapIntensity) + "\n"
        else:
            normal = ""

        if hasattr(self, "aomapTexture"):
            occl = "aomapTexture " + self.textureRelName(self.aomapTexture) + \
                "\naomapIntensity " + str(self.aomapIntensity) + "\n"
        else:
            occl = "aomapIntensity " + str(self.aomapIntensity) + "\n"

        if hasattr(self, "metallicRoughnessTexture"):
            metrough = "metallicRoughnessTexture " + self.textureRelName(self.metallicRoughnessTexture) + "\n"
        else:
            metrough = ""

        if hasattr(self, "emissiveTexture"):
            emissive = "emissiveTexture " + self.textureRelName(self.emissiveTexture) + \
                "\nemissiveFactor " + str(self.emissiveFactor) + "\n"
        else:
            emissive = ""

        # for litsphere save only name to avoid trouble
        #
        if hasattr(self, "sp_litsphereTexture"):
            litsphere = "shaderParam litsphereTexture " + os.path.basename(self.sp_litsphereTexture)
        else:
            litsphere = ""

        shader = "shader " + self.shader + "\n"

        if self.colorationMethod != 0:
            self.roundColor(self.colorationColor)
            coloration = "colorationMethod " + str(self.colorationMethod) + \
                    f"\ncolorationColor  {self.colorationColor[0]} {self.colorationColor[1]} {self.colorationColor[2]}\n"
        else:
            coloration = ""

        try:
            fp = open(path, "w", encoding="utf-8", errors='ignore')
        except IOError as err:
            self.env.last_error = str(err)
            return (False)

        text = f"""# MakeHuman2 Material definition for {self.name}
name {self.name}
description {self.description}

ambientColor {self.ambientColor[0]} {self.ambientColor[1]} {self.ambientColor[2]}
diffuseColor {self.diffuseColor[0]} {self.diffuseColor[1]} {self.diffuseColor[2]}
specularColor {self.specularColor[0]} {self.specularColor[1]} {self.specularColor[2]}
emissiveColor {self.emissiveColor[0]} {self.emissiveColor[1]} {self.emissiveColor[2]}
metallicFactor {self.metallicFactor}
roughnessFactor {self.roughnessFactor}

transparent {self.transparent}
alphaToCoverage {self.alphaToCoverage}
backfaceCull {self.backfaceCull}

{diffuse}{normal}{occl}{metrough}{emissive}{coloration}

{shader}{litsphere}

"""
        
        fp.write(text)
        fp.close()
        return True

    def getCurrentMatFilename(self):
        return self.filename

    def listAllMaterials(self, objdir = None):
        if objdir is None:
            objdir = self.mhmatdir
        
        materialfiles=[]
        for (root, dirs, files) in  os.walk(objdir):
            for name in files:
                if name.endswith(".mhmat"):
                    materialfiles.append(os.path.join(root, name))

        # second way is a parallel materials folder for common materials
        #
        if len( materialfiles) == 0:
            objdir = os.path.join(os.path.dirname(objdir), "materials")
            for (root, dirs, files) in  os.walk(objdir):
                for name in files:
                    if name.endswith(".mhmat"):
                        materialfiles.append(os.path.join(root, name))

        return(materialfiles)

    def colorate(self):
        if not hasattr(self, "diffuseTexture"):
            return

        if self.tex_diffuse.getTexture() is None:
            return
        if self.colorationColor == self.colorationOldColor and self.colorationMethod == self.colorationOldMethod:
            return
        self.tex_diffuse.refresh() # reset
        image = self.tex_diffuse.getImage()
        ie = ImageEdit(self.glob)
        if self.colorationMethod == 1:
            ie.multColor(image, *self.colorationColor)
            self.tex_diffuse.refresh_image()
        elif self.colorationMethod ==2:
            ie.greyToColor(image, *self.colorationColor)
            self.tex_diffuse.refresh_image()

        self.colorationOldColor = self.colorationColor.copy()
        self.colorationOldMethod= self.colorationMethod

    def colorToName(self, rgb):
        color = QColor.fromRgbF(rgb[0], rgb[1], rgb[2])
        return "Generated color [" + hex(color.rgb()) + "]"

    def mixColors(self, colors, values, obj=None):
        """
        generates a texture from a number of colors (e.g. ethnic slider)
        """
        col = numpy.asarray(colors)
        newcolor = numpy.array([0.0, 0.0, 0.0])
        for n, elem in enumerate(col):
            newcolor += elem * values[n]
        self.freeTexture("diffuseTexture")
        self.tex_diffuse = MH_Texture(self.glob, obj=obj)
        return self.tex_diffuse.unicolor(newcolor, self.colorToName(newcolor))

    def uniColor(self, rgb, obj=None):
        self.freeTexture("diffuseTexture")
        self.tex_diffuse = MH_Texture(self.glob, self.type, obj=obj)
        return self.tex_diffuse.unicolor(rgb, self.colorToName(rgb))

    def mapChanged(self, mapname, maptexture):
        oldname = "" if maptexture is None else maptexture.getName()
        if hasattr(self, mapname):
            newname = getattr(self, mapname)
            return oldname == newname
        return False

    def colorChanged(self, colname, maptexture):
        oldname = "" if maptexture is None else maptexture.getName()
        if hasattr(self, colname):
            newname = getattr(self, colname)
            name = self.colorToName(newname)
            return oldname == name
        return False

    def loadLitSphere(self, modify, obj):
        if self.mapChanged('sp_litsphereTexture', self.tex_litsphere):
            return self.tex_litsphere.getTexture()

        self.freeTexture("sp_litsphereTexture")
        self.tex_litsphere = MH_Texture(self.glob, obj=obj)
        return self.tex_litsphere.load(self.sp_litsphereTexture, modify=modify)

    def loadAOMap(self, white, modify, obj):
        if self.mapChanged('aomapTexture', self.tex_aomap):
            return self.tex_aomap.getTexture()

        if hasattr(self, 'aomapTexture'):
            self.freeTexture("aomapTexture")
            self.tex_aomap = MH_Texture(self.glob, obj=obj)
            return self.tex_aomap.load(self.aomapTexture,  modify=modify)

        if self.colorChanged('ambientColor', self.tex_aomap):
           return self.tex_aomap.getTexture()

        self.freeTexture("aomapTexture")
        if hasattr(self, 'ambientColor'):
            self.tex_aomap = MH_Texture(self.glob, obj=obj)
            return self.tex_aomap.unicolor(self.ambientColor, self.colorToName(self.ambientColor))

        return white

    def loadNOMap(self, nocolor, modify, obj):
        if self.mapChanged('normalmapTexture', self.tex_nomap):
            return self.tex_nomap.getTexture()

        self.freeTexture("normalmapTexture")
        if hasattr(self, 'normalmapTexture'):
            self.tex_nomap = MH_Texture(self.glob, obj=obj)
            return self.tex_nomap.load(self.normalmapTexture, modify=modify)

        return nocolor

    def loadEMMap(self, nocolor, modify, obj):
        if self.mapChanged('emissiveTexture', self.tex_emmap):
            return self.tex_emmap.getTexture()

        if hasattr(self, 'emissiveTexture'):
            self.freeTexture("emissiveTexture")
            self.tex_emmap = MH_Texture(self.glob, obj=obj)
            return self.tex_emmap.load(self.emissiveTexture, modify=modify)

        if hasattr(self, 'emissiveColor'):
            if self.emissiveColor != [0.0, 0.0, 0.0]:
                if self.colorChanged('emissiveColor', self.tex_emmap):
                    return self.tex_emmap.getTexture()

                self.freeTexture("emissiveTexture")
                self.tex_emmap = MH_Texture(self.glob, obj=obj)
                return self.tex_emmap.unicolor(self.emissiveColor, self.colorToName(self.emissiveColor))
        
        self.freeTexture("emissiveTexture")
        return nocolor

    def loadMRMap(self, white, modify, obj):
        if self.mapChanged('metallicRoughnessTexture', self.tex_mrmap):
            return self.tex_mrmap.getTexture()

        self.freeTexture("metallicRoughnessTexture")
        if hasattr(self, 'metallicRoughnessTexture'):
            self.tex_mrmap = MH_Texture(self.glob, obj=obj)
            return self.tex_mrmap.load(self.metallicRoughnessTexture, modify=modify)

        return white


    def setDiffuse(self, name, alternative, obj=None):
        """
        used for additional objects only
        """
        if name is None:
            return alternative
        self.diffuseTexture = name
        self.tex_diffuse = MH_Texture(self.glob, obj=obj)
        texture = self.tex_diffuse.load(self.diffuseTexture, self.type)
        if texture is not None:
            return texture
        return alternative

    def loadDiffuse(self, modify, obj):
        if self.mapChanged('diffuseTexture', self.tex_diffuse):
            return self.tex_diffuse.getTexture()

        if hasattr(self, 'diffuseTexture'):
            self.freeTexture("diffuseTexture")
            self.tex_diffuse = MH_Texture(self.glob, obj=obj)
            ogl_texture = self.tex_diffuse.load(self.diffuseTexture, modify=modify)
        else:
            if self.colorChanged('diffuseColor', self.tex_diffuse):
               return self.tex_diffuse.getTexture()

            self.freeTexture("diffuseTexture")
            if hasattr(self, 'diffuseColor'):
                self.tex_diffuse = MH_Texture(self.glob, obj=obj)
                ogl_texture = self.tex_diffuse.unicolor(self.diffuseColor, self.colorToName(self.diffuseColor))
            else:
                ogl_texture = self.tex_diffuse.stdcolor()   # grey
        return ogl_texture

    def saveDiffuse(self):
        if hasattr(self, 'diffuseTexture') and self.tex_diffuse:
            filename = self.tex_diffuse.save_png(self.colorationColor)
            self.env.logLine(8, "temporary file saved to " + filename)
            return filename
        return None

    def freeTexture(self, attrib):
        """
        free only one texture (for material editor)
        """
        if attrib == "normalmapTexture":
            if self.tex_nomap:
                self.tex_nomap.delete()
                self.tex_nomap = None
        elif attrib == "diffuseTexture":
            if self.tex_diffuse:
                self.tex_diffuse.delete()
                self.tex_diffuse = None
        elif attrib == "aomapTexture":
            if self.tex_aomap:
                self.tex_aomap.delete()
                self.tex_aomap = None
        elif attrib == "metallicRoughnessTexture":
            if self.tex_mrmap:
                self.tex_mrmap.delete()
                self.tex_mrmap = None
        elif attrib == "emissiveTexture":
            if self.tex_emmap:
                self.tex_emmap.delete()
                self.tex_emmap = None
        elif attrib == "sp_litsphereTexture":
            if self.tex_litsphere:
                self.tex_litsphere.delete()
                self.tex_litsphere = None

    def freeTextures(self):
        # in case of system, cleanup is done in the end
        #
        if self.tex_diffuse:
            if self.type != "system":
                self.tex_diffuse.delete()
            else:
                self.tex_diffuse.destroy()

        for elem in [self.tex_litsphere, self.tex_aomap, self.tex_mrmap, self.tex_nomap, self.tex_emmap]:
            if elem:
                elem.delete()

