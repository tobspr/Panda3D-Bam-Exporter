
import os
import bpy

from ExportException import ExportException
from SceneWriter import SceneWriter

class PBSEngine(bpy.types.RenderEngine):
    bl_idname = "P3DPBS"
    bl_label = "Panda3D PBS"
    bl_use_preview = True

    def render(self, scene):
        """ Renders the given scene using the Render Pipeline """

        # Get the different required paths
        base_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../rp")
        temp_bam_path = os.path.join(base_path, "preview.bam")
        temp_output_path = os.path.join(base_path, "output.png")
        generator_path = os.path.join(base_path, "generate.py")
        loading = os.path.join(base_path, "loading.png")

        scale = scene.render.resolution_percentage / 100.0
        self.size_x = int(scene.render.resolution_x * scale)
        self.size_y = int(scene.render.resolution_y * scale)
        
        # Load a temporary loading screen
        result = self.begin_result(0, 0, self.size_x, self.size_y)
        result.layers[0].load_from_file(loading, 0, 0)
        self.end_result(result)

        objects = []

        # Collect the objects to export
        for obj_name, obj_handle in scene.objects.items():
            if obj_handle.type == "CAMERA" or obj_handle.is_visible(scene):
                objects.append(obj_handle)

        # Export the scene as .bam file
        try:    
            writer = SceneWriter()
            writer.set_context(bpy.context)
            writer.set_settings(scene.pbe)
            writer.set_filepath(temp_bam_path)
            writer.set_objects(objects)
            writer.write_bam_file()
        except ExportException as err:
            print("Error during preview export:", err.message)
            return {'CANCELLED'}

        # Invoke renderer
        cmd = 'python "' + generator_path + '" {} {}'.format(self.size_x, self.size_y)
        os.system(cmd)

        # Write result
        result = self.begin_result(0, 0, self.size_x, self.size_y)
        result.layers[0].load_from_file(temp_output_path, 0, 0)
        self.end_result(result)

def register():
    bpy.utils.register_class(PBSEngine)

    # RenderEngines also need to tell UI Panels that they are compatible
    # Otherwise most of the UI will be empty when the engine is selected.
    # In this example, we need to see the main render image button and
    # the material preview panel.
    # from bl_ui import properties_render
    # properties_render.RENDER_PT_render.COMPAT_ENGINES.add('PBSEngine')
    # del properties_render

    from bl_ui import properties_material
    #properties_material.MATERIAL_PT_context_material.COMPAT_ENGINES.add('P3DPBS')
    properties_material.MATERIAL_PT_preview.COMPAT_ENGINES.add('P3DPBS')
    properties_material.MATERIAL_PT_game_settings.COMPAT_ENGINES.add('P3DPBS')
    del properties_material

def unregister():
    bpy.utils.unregister_class(PBSEngine)
