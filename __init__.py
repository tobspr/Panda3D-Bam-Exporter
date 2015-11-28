
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
from bpy.props import *
from bpy_extras.io_utils import ExportHelper


# Check if we already imported the libraries
if "PBESceneWriter" not in locals():

    # Add the current path to the sys path. This ensures we can load the modules 
    # from the current directory
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, plugin_dir)

    # Now import the required libs
    import PBEExportException
    import PBESceneWriter
    import PBEPBS

else:
    # If we already imported the libs, just reload them (but don't modify the path again)
    importlib.reload(PBEExportException)
    importlib.reload(PBESceneWriter)
    importlib.reload(PBEPBS)



class PBEExportSettings(bpy.types.PropertyGroup):
    """ This class stores the exporter settings """

    tex_mode =  bpy.props.EnumProperty(
            name="Texture handling",
            description="How to handle textures",
            items=[
                ("ABSOLUTE", "Absolute", "Store absolute paths to the textures"),
                ("RELATIVE", "Relative", "Store relative paths to the textures"),
                ("COPY", "Copy (Recommended)", "Copy the textures to a folder relative to the bam file"),
                ("INCLUDE", "Include", "Include the textures in the bam file"),
                ("KEEP", "Keep", "Use the same texture path settings that blender uses (advanced)"),
            ],
            default="COPY")

    tex_copy_path = bpy.props.StringProperty(
            name="Texture copy path",
            description="The relative path where to copy the textures to",
            default="./tex/")

    use_pbs = bpy.props.BoolProperty(
            name="Use PBS addon",
            description="Whether to use the Physically Based Shading addon. This "
                        "stores the physically based properties of the material in "
                        "the diffuse and specular components to be used in the application "
                        "later on",
            default=True
        )

    def draw(self, layout):
        """ This function is called by the PBEExportOperator, whenever the export-
        screen is rendered. We should draw all available export properties here """

        layout.row().prop(self, 'tex_mode')

        if self.tex_mode == "COPY":
            box = layout.box()
            box.row().prop(self, 'tex_copy_path')

        layout.row().prop(self, 'use_pbs')


class PBEExportOperator(bpy.types.Operator, ExportHelper):
    """ This class is the main export operator, being called whenever the user
    wants to export the model """

    bl_idname = "export.panda3d_bam"  
    bl_label = "Export to Panda3D BAM"

    filename_ext = ".bam"
    # filter_glob = StringProperty(
    #         default="*.bam",
    #         )
    filepath = StringProperty()

    def execute(self, context):
        """ This function is called when the operator is executed. It starts the
        export process """

        objects = bpy.context.selected_objects 
        scene = bpy.context.scene

        # Check if there exists a settings datablock
        if not hasattr(scene, "pbe") or not scene.pbe:
            self.report({'ERROR'}, "Scene has no PBE datablock")
            return {'CANCELLED'}

        # Check if there are active objects
        if len(objects) < 1:
            self.report({'ERROR'}, "No objects selected!")
            return {'CANCELLED'}

        # Try to execute the export process
        try:    
            writer = PBESceneWriter.PBESceneWriter()
            writer.set_context(bpy.context)
            writer.set_settings(scene.pbe)
            writer.set_filepath(self.filepath)
            writer.set_objects(objects)
            writer.write_bam_file()
        except PBEExportException.PBEExportException as err:
            self.report({'ERROR'}, err.message)
            return {'CANCELLED'}

        return {'FINISHED'}
        
    def draw(self, context):
        """ This function is called when the export-screen is drawn. We draw
        our properties here so the user can adjust it """
        context.scene.pbe.draw(self.layout)
        
def PBEExportFuncCallback(self, context):
    self.layout.operator(PBEExportOperator.bl_idname, text="Panda3D (.bam)")



def register():
    print("Registering export properties")
    bpy.utils.register_class(PBEExportSettings)
    bpy.utils.register_class(PBEExportOperator)
    bpy.types.INFO_MT_file_export.append(PBEExportFuncCallback)
    bpy.types.Scene.pbe = PointerProperty(type=PBEExportSettings)
    bpy.types.Material.pbepbs = PointerProperty(type=PBEPBS.PBEPBSMatProps)


def unregister():
    print("Unregistering export properties")
    bpy.utils.unregister_class(PBEExportSettings)
    bpy.utils.unregister_class(PBEExportOperator)
    bpy.utils.unregister_module(PBEPBS)
    bpy.types.INFO_MT_file_export.remove(PBEExportFuncCallback)
    del bpy.types.Scene.pbe
    del bpy.types.Material.pbepbs
