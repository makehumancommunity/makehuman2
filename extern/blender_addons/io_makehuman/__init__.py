#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Author: black-punkduck

bl_info = {
    "name": "MakeHuman2-IO",
    "author": "black-punkduck",
    "version": (0,0,2),
    "blender": (4,5,0),
    "location": "View3D > Properties > MakeHuman2-IO",
    "description": "MakeHuman2 communication.",
    "category": "MakeHuman"}

import bpy
from bpy.utils import register_class, unregister_class
from bpy.props import BoolProperty, StringProperty, IntProperty, EnumProperty


from .panel import MH2B_PT_Panel
from .load import MH2B_OT_Load
from .api import MH2B_OT_Hello, MH2B_OT_GetChar, MH2B_OT_Randomize, MH2B_OT_AssignProject
from .infobox import MH2B_OT_InfoBox,MH2B_OT_WarningBox

MH2B_CLASSES = [
    MH2B_OT_Load,
    MH2B_PT_Panel,
    MH2B_OT_InfoBox,
    MH2B_OT_WarningBox,
    MH2B_OT_Hello,
    MH2B_OT_GetChar,
    MH2B_OT_Randomize,
    MH2B_OT_AssignProject
]


def register():
    scn = bpy.types.Scene
    _scales = [ ("0.1", "Meter", "Meter scale", 1), ("1.0", "Decimeter", "Decimeter scale", 2), \
        ("3.937", "Inch", "Inch scale", 3), ("10.0", "Centimeter", "Centimeter scale", 4), \
        ("100.0", "Millimeter", "Millimeter scale", 5) ]

    _randommodes = [("0", "Linear", "Linear random values between 0 and 1", 0), \
            ("1", "Gauss", "Truncated gaussian random values between 0 and 1", 1)]

    scn.MH2B_subdiv = BoolProperty(name="Subdivision",
            description="After loading a subdivision surface modifier will be added.", default=False)
    scn.MH2B_apihost = StringProperty(name="API hostname", description="Makehuman server hostname", default="127.0.0.1")
    scn.MH2B_apiport = IntProperty(name="API Port", description="Socket port number", default=12345, min=1024, max=49151)
    scn.MH2B_copylocal = BoolProperty(name="TextureCopy", description="Copy to local material folder", default=False)
    scn.MH2B_localtexfolder = StringProperty(name="API texturefolder", description="Local material folder", default="textures")
    scn.MH2B_projdir = StringProperty(name="API projectdir", description="Project folder", default="NONE")
    scn.MH2B_feetonground =  BoolProperty(name="API FeetOnGround", description="Place character on ground", default=True)
    scn.MH2B_gethiddenverts = BoolProperty(name="API GetHiddenVerts", description="Get invisible vertices", default=False)
    scn.MH2B_getanimation = BoolProperty(name="API GetAnimation", description="Get attached animation", default=False)
    scn.MH2B_getscale = EnumProperty(items=_scales, name="", description="Scale of character")
    scn.MH2B_replacechar = BoolProperty(name="API ReplaceCharacter", description="Replace last character imported by API", default=False)
    scn.MH2B_lastchar = StringProperty(name="API LastCharacterName", description="Name of last character imported by API", default="")
    scn.MH2B_getrandom = EnumProperty(items=_randommodes, name="", description="Random mode")

    for cls in MH2B_CLASSES:
        register_class(cls)

def unregister():
    for cls in reversed(MH2B_CLASSES):
        unregister_class(cls)

if __name__ == "__main__":
    register()
    print("module loaded")


