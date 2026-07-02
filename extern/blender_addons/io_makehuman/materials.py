"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    blender-addon, material nodes
"""

import bpy
import os
import shutil

class MH2B_OT_Material:
    def __init__(self, context, dirname):
        self.context = context
        self.dirname = dirname
        self.projdir        = context.scene.MH2B_projdir
        self.copylocal      = context.scene.MH2B_copylocal
        self.localtexfolder = context.scene.MH2B_localtexfolder

        self.blendmat = None
        self.nodes = None
        self.glTFOutputName = "glTF Material Output"

    def glTFOutput(self, x, y):
        if self.glTFOutputName  in bpy.data.node_groups:
            group = bpy.data.node_groups[self.glTFOutputName]
        else:
            group = bpy.data.node_groups.new(self.glTFOutputName, 'ShaderNodeTree')
            group.interface.new_socket("Occlusion", socket_type="NodeSocketFloat")
            thicknessFactor  = group.interface.new_socket("Thickness", socket_type="NodeSocketFloat", )
            thicknessFactor.default_value = 0.0
            group.nodes.new('NodeGroupOutput')
            group_input = group.nodes.new('NodeGroupInput')
            group_input.location = -200, 0

        node_gltf_matoutput = self.nodes.new("ShaderNodeGroup")
        node_gltf_matoutput.node_tree = bpy.data.node_groups[group.name]

        node_gltf_matoutput.location = x, y
        return (node_gltf_matoutput)

    def copyTexture(self, path):
        """
        for api dirname and path are absolute,
        return absolute path in case of error
        """
        filename = bpy.path.basename(path)
        destdir  = os.path.join(bpy.path.abspath("//"), self.localtexfolder)
        destpath = os.path.join(destdir, filename)

        if not os.path.isdir(destdir):
            try:
                os.mkdir(destdir)
            except Exception as e:
                bpy.ops.mh2b.infobox('INVOKE_DEFAULT', title="Material", error=str(e))
                return path

        if path != destpath and os.path.isfile(path):
            print ("Copy from: " + path + " to " + destpath)
            try:
                shutil.copyfile(path, destpath)
            except Exception as e:
                bpy.ops.mh2b.infobox('INVOKE_DEFAULT', title="Material", error=str(e))
                return path
            path = os.path.join("//", self.localtexfolder, filename)

        return path

    def addTextureNode(self, path, x, y, noncolor, name):
        node = self.nodes.new('ShaderNodeTexImage')
        print ("Path: ", path)
        if self.dirname is not None:
            path = os.path.join(self.dirname, path)
        if self.copylocal and self.projdir != "NONE":
            img = self.copyTexture(path)
        else:
            img = path
        node.image = bpy.data.images.load(img)
        node.name = name
        node.label = name
        node.location = x,y
        if noncolor:
            node.image.colorspace_settings.name = 'Non-Color'
        return (node)

    def addNodes(self, jdata, texture, alpha, roughness, metallic, normtexture, normscale, \
            aotexture, aoscale, mrtexture, emtexture, emscale, ior, transmission):

        # Add the Principled Shader node
        #
        links = self.blendmat.node_tree.links

        node_principled = self.nodes.new(type='ShaderNodeBsdfPrincipled')
        node_principled.location = 0,0

        # Add the Output node, and link to principled
        #
        node_output = self.nodes.new(type='ShaderNodeOutputMaterial')
        node_output.location = 600, -200


        locy = 300
        # add color, either texture or list
        #
        if isinstance(texture, dict) and "source" in texture:
            img = texture["source"]
            path = jdata["images"][img]["uri"]

            # Add the Image Texture node
            node_tex = self.addTextureNode(path, -600, locy, False, "BASE COLOR")
            locy -= 300

            links.new(node_tex.outputs["Color"], node_principled.inputs["Base Color"])
            if alpha is not None:
                links.new(node_tex.outputs["Alpha"], node_principled.inputs["Alpha"])
        elif isinstance(texture, list):
            node_principled.inputs["Base Color"].default_value = tuple(texture)

        if roughness is not None:
            node_principled.inputs["Roughness"].default_value = roughness

        if metallic is not None:
            node_principled.inputs["Metallic"].default_value = metallic

        if ior is not None:
            node_principled.inputs["IOR"].default_value = ior

        if transmission is not None:
            node_principled.inputs["Transmission Weight"].default_value = transmission

        if normtexture is not None:
            # Add the normal Texture node
            #
            img = normtexture["source"]
            path = jdata["images"][img]["uri"]
            node_normtex = self.addTextureNode(path, -600, locy, True, "NORMAL MAP")

            node_normalmap = self.nodes.new('ShaderNodeNormalMap')
            node_normalmap.location = -300, locy
            node_normalmap.inputs["Strength"].default_value = normscale
            links.new(node_normtex.outputs["Color"], node_normalmap.inputs["Color"])
            links.new(node_normalmap.outputs["Normal"], node_principled.inputs["Normal"])
            locy -= 300

        if mrtexture is not None:
            # add metallic-roughness texture
            #
            img = mrtexture["source"]
            path = jdata["images"][img]["uri"]
            node_mrtex = self.addTextureNode(path, -600, locy, True, "METALLIC ROUGHNESS")
            node_sepcolmr = self.nodes.new('ShaderNodeSeparateColor')
            node_sepcolmr.location = -300, locy

            links.new(node_mrtex.outputs["Color"], node_sepcolmr.inputs["Color"])
            links.new(node_sepcolmr.outputs[2], node_principled.inputs["Metallic"])
            links.new(node_sepcolmr.outputs[1], node_principled.inputs["Roughness"])
            locy -= 300

        if emtexture is not None:
            if isinstance(emtexture, list):
                node_principled.inputs["Emission Color"].default_value = tuple(emtexture)
            else:
                # add emission texture
                #
                img = emtexture["source"]
                path = jdata["images"][img]["uri"]
                node_emtex = self.addTextureNode(path, -600, locy, False, "EMISSION")
                links.new(node_emtex.outputs["Color"], node_principled.inputs["Emission Color"])
                locy -= 300

        if emscale is not None:
            # trick: create logarithmic scale between 0 and 255
            # to make that visible use blooming effect
            #
            em = pow (2, emscale *8)-1
            node_principled.inputs["Emission Strength"].default_value = em

        if aotexture is not None:

            # add ambient occlusion texture, we need a second output node,
            # normal one must be set to cycles
            #
            node_output_eevee = self.nodes.new(type='ShaderNodeOutputMaterial')
            node_output_eevee.location = 600, 0
            node_output_eevee.target = "EEVEE"
            node_output.target = "CYCLES"

            img = aotexture["source"]
            path = jdata["images"][img]["uri"]
            node_aotex = self.addTextureNode(path, -600, locy, True, "OCCLUSION")
            node_sepcol = self.nodes.new('ShaderNodeSeparateColor')
            node_sepcol.location = -300, locy
            node_mixcol = self.nodes.new('ShaderNodeMixRGB')
            node_mixcol.location = -100, locy
            node_mixcol.inputs[0].default_value = aoscale

            node_amboc = self.nodes.new("ShaderNodeAmbientOcclusion")
            node_amboc.location = 100, locy

            node_mixcshader = self.nodes.new("ShaderNodeMixShader")
            node_mixcshader.location = 400, 0

            links.new(node_aotex.outputs["Color"], node_sepcol.inputs["Color"])
            links.new(node_sepcol.outputs[0], node_mixcol.inputs[2])
            links.new(node_mixcol.outputs[0], node_amboc.inputs["Color"])
            links.new(node_amboc.outputs["Color"], node_mixcshader.inputs[0])

            links.new(node_principled.outputs["BSDF"], node_mixcshader.inputs[2])
            links.new(node_mixcshader.outputs[0], node_output_eevee.inputs["Surface"])
            links.new(node_principled.outputs["BSDF"], node_output.inputs["Surface"])

            output = self.glTFOutput(-100, -450)
            links.new(node_sepcol.outputs[0], output.inputs[0])
        else:
            links.new(node_principled.outputs["BSDF"], node_output.inputs["Surface"])


    def addMaterial(self, jdata, material):
        matj = jdata["materials"][material]
        name = matj["name"] if "name" in matj else 'Material'
        alpha = matj["alphaMode"] if "alphaMode" in matj else None
            
        self.blendmat = bpy.data.materials.new(name=name)
        self.blendmat.use_nodes = True
        if alpha:
            self.blendmat.blend_method = alpha
        self.nodes = self.blendmat.node_tree.nodes
        self.nodes.clear()

        ior = matj['ior'] if "ior" in matj else None
        transmission = matj['transmissionFactor'] if "transmissionFactor" in matj else None

        normtexture = None
        normscale = 0.0
        if "normalTexture" in matj:
            textind = matj['normalTexture']["index"]
            normscale = matj['normalTexture']["scale"]
            normtexture = jdata["textures"][textind]

        aotexture = None
        aoscale = 0.0
        if "occlusionTexture" in matj:
            textind = matj['occlusionTexture']["index"]
            aoscale = matj['occlusionTexture']["strength"]
            aotexture = jdata["textures"][textind]

        emtexture = None
        if "emissiveTexture" in matj:
            textind = matj['emissiveTexture']["index"]
            emtexture = jdata["textures"][textind]
        elif "emissiveColor" in matj:
            emtexture = matj['emissiveColor']
            emtexture.append(1.0)

        emscale = None
        if "emissiveFactor" in matj:
            emscale = matj["emissiveFactor"]

        if "pbrMetallicRoughness" in matj:
            pbr = matj["pbrMetallicRoughness"]

            roughness = pbr['roughnessFactor'] if "roughnessFactor" in pbr else None
            metallic  = pbr['metallicFactor'] if "metallicFactor" in pbr else None

            mrtexture = None
            if 'metallicRoughnessTexture' in pbr:
                textind = pbr['metallicRoughnessTexture']["index"]
                mrtexture = jdata["textures"][textind]

            if 'baseColorTexture' in pbr:
                textind = pbr['baseColorTexture']["index"]
                texture = jdata["textures"][textind]
                self.addNodes(jdata, texture, alpha, roughness, metallic, normtexture, normscale, \
                        aotexture, aoscale, mrtexture, emtexture, emscale, ior, transmission)
            elif 'baseColorFactor' in pbr:
                self.addNodes(jdata,  pbr['baseColorFactor'], alpha, roughness, metallic, normtexture, normscale, \
                        aotexture, aoscale, mrtexture, emtexture, emscale, ior, transmission)
        return(self.blendmat)

