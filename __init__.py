
bl_info = {
    "name": "Panda3D Bam Exporter (PBE)",
    "description": "Import / Export Panda3D bam files",
    "author": "tobspr",
    "version": (1, 0, 1),
    "blender": (2, 76, 0),
    "location": "File > Export > Export to .bam",
    "warning": "",
    "wiki_url": "http://tobspr.me/bam-export/wiki",
    "category": "Import-Export",
}


import os
import sys
import bpy
# import importlib
# from bpy.props import *


# Check if we already imported the libraries
# if "SceneWriter" not in locals():

#     # Add the current path to the sys path. This ensures we can load the modules 
#     # from the current directory
#     plugin_dir = os.path.dirname(os.path.abspath(__file__))
#     sys.path.insert(0, plugin_dir)

#     # Now import the required libs
#     import src.ExportException as ExportException
#     import src.SceneWriter as SceneWriter
#     import src.PBS as PBS

# else:
#     # If we already imported the libs, just reload them (but don't modify the path again)
#     importlib.reload(ExportException)
#     importlib.reload(SceneWriter)
#     importlib.reload(PBS)

plugin_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.join(plugin_dir, "src")
sys.path.insert(0, plugin_dir)
sys.path.insert(0, source_dir)
loaded_modules = []

def register():
    global loaded_modules
    # print("Registering export properties")
    # bpy.utils.register_class(PBEExportSettings)
    # bpy.utils.register_class(PBEExportOperator)
    # bpy.types.INFO_MT_file_export.append(PBEExportFuncCallback)
    # bpy.types.Scene.pbe = PointerProperty(type=PBEExportSettings)
    # bpy.types.Material.pbepbs = PointerProperty(type=PBEPBS.PBEPBSMatProps)
    # pass

    modules = bpy.utils.modules_from_path(source_dir, set("__init__"))
    for module in modules:
        if hasattr(module, "register"):
            module.register()
            loaded_modules.append(module)

def unregister():
    # print("Unregistering export properties")
    # bpy.utils.unregister_class(PBEExportSettings)
    # bpy.utils.unregister_class(PBEExportOperator)
    # bpy.utils.unregister_module(PBEPBS)
    # bpy.types.INFO_MT_file_export.remove(PBEExportFuncCallback)
    # del bpy.types.Scene.pbe
    # del bpy.types.Material.pbepbs
    for module in loaded_modules:
        module.unregister()
