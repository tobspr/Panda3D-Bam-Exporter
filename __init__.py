
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
import importlib
from types import ModuleType
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

pbe_loaded_module_list = []

def unload_modules():
    """ Unregisters all loaded modules """
    global pbe_loaded_module_list
    for module_handle in pbe_loaded_module_list:
        print("Unregistering module", module_handle.__name__)
        module_handle.unregister()

def register():
    global pbe_loaded_module_list
    unload_modules()

    # Load modules

    importlib.invalidate_caches()

    exporter = __import__("Exporter")
    pbs = __import__("PBS")

    exporter = importlib.reload(exporter)
    pbs = importlib.reload(pbs)

    pbe_loaded_module_list = [exporter, pbs]

    for handle in pbe_loaded_module_list:
        print("Registering", handle.__name__)
        handle.register()

def unregister():
    global pbe_loaded_module_list
    unload_modules()