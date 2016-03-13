
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


plugin_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.join(plugin_dir, "src")
sys.path.insert(0, plugin_dir)
sys.path.insert(0, source_dir)

pbe_loaded_module_list = {}

def unload_modules():
    """ Unregisters all loaded modules """
    global pbe_loaded_module_list
    for module_name, module_handle in pbe_loaded_module_list.items():
        print("Bam-Exporter: Unloading module", module_name)
        module_handle.unregister()
        del sys.modules[module_name]

def register():
    global pbe_loaded_module_list
    unload_modules()

    # Load modules

    importlib.invalidate_caches()

    for mod_name in ["Exporter", "PBS", "PBSEngine"]:
        print("Bam-Exporter: Loading",mod_name, "..")
        mod = __import__(mod_name)
        mod.register()
        pbe_loaded_module_list[mod_name] = mod


def unregister():
    global pbe_loaded_module_list
    unload_modules()
    pbe_loaded_module_list.clear()
