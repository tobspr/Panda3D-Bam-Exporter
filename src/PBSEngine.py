
import os
import bpy
import time
import socket
import pickle
import select
import random
import struct

from ExportException import ExportException
from SceneWriter import SceneWriter

class PBSEngine(bpy.types.RenderEngine):
    bl_idname = "P3DPBS"
    bl_label = "Panda3D PBS"
    bl_use_preview = True

    def render(self, scene):
        """ Renders the given scene using the Render Pipeline """

        render_start = time.time()

        # Get the different required paths
        base_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../rp")
        temp_bam_path = os.path.join(base_path, "preview.bam")
        temp_output_path = os.path.join(base_path, "output.png")
        loading = os.path.join(base_path, "loading.png")

        self.update_progress(0.1)

        scale = scene.render.resolution_percentage / 100.0
        self.size_x = int(scene.render.resolution_x * scale)
        self.size_y = int(scene.render.resolution_y * scale)

        if self.size_x < 64 or self.size_y < 64:
            # This is a preview, skip it, to avoid overhead
            result = self.begin_result(0, 0, self.size_x, self.size_y)
            self.end_result(result)
            return

        objects = []

        # Collect the objects to export
        for obj_name, obj_handle in scene.objects.items():
            if obj_handle.is_visible(scene) or obj_handle.type == "CAMERA":
                objects.append(obj_handle)

        self.update_progress(0.2)

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

        self.update_progress(0.6)

        # Invoke renderer
        renderer_ip = ("127.0.0.1", 62360)
        pingback_port = random.randint(30000, 65000)

        payload = {
            "scene": temp_bam_path,
            "dest": temp_output_path,
            "view_size_x": self.size_x,
            "view_size_y": self.size_y,
            "pingback_port": pingback_port
        }

        message = pickle.dumps(payload, protocol=0)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(message, renderer_ip)
        except Exception as msg:
            sock.close()
            raise msg

        self.update_progress(0.8)

        print("Waiting for response .. ")

        # Wait until the render pipeline responds
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(3.0)

        try:
            sock.bind(("localhost", pingback_port))
        except Exception as msg:
            print("Could not connect to pingback_port - maybe a render result is still waiting?")
            print("Error message:", msg)
            return

        sock.listen(1)

        try:
            conn, addr = sock.accept()
        except socket.timeout:
            print("No render pipeline response within timeout!")
            sock.close()
            return

        sock.close()

        result = self.begin_result(0, 0, 512, 512)
        result.layers[0].load_from_file(temp_output_path)
        self.end_result(result)

        render_dur = (time.time() - render_start) * 1000.0
        print("Finished render in", render_dur, "ms")


def register():
    bpy.utils.register_class(PBSEngine)

    # RenderEngines also need to tell UI Panels that they are compatible
    # Otherwise most of the UI will be empty when the engine is selected.
    # In this example, we need to see the main render image button and
    # the material preview panel.
    # from bl_ui import properties_render
    # properties_render.RENDER_PT_render.COMPAT_ENGINES.add('PBSEngine')
    # del properties_render

    from bl_ui import properties_render
    properties_render.RENDER_PT_bake.COMPAT_ENGINES.add('P3DPBS')

    from bl_ui import properties_scene
    properties_scene.SCENE_PT_unit.COMPAT_ENGINES.add('P3DPBS')

    from bl_ui import properties_data_mesh
    properties_data_mesh.DATA_PT_context_mesh.COMPAT_ENGINES.add('P3DPBS')

    from bl_ui import properties_material
    properties_material.MATERIAL_PT_context_material.COMPAT_ENGINES.add('P3DPBS')
    properties_material.MATERIAL_PT_preview.COMPAT_ENGINES.add('P3DPBS')
    properties_material.MATERIAL_PT_game_settings.COMPAT_ENGINES.add('P3DPBS')

    from bl_ui import properties_texture
    properties_texture.TEXTURE_PT_context_texture.COMPAT_ENGINES.add('P3DPBS')
    properties_texture.TEXTURE_PT_image.COMPAT_ENGINES.add('P3DPBS')
    properties_texture.TEXTURE_PT_image_sampling.COMPAT_ENGINES.add('P3DPBS')
    properties_texture.TEXTURE_PT_image_mapping.COMPAT_ENGINES.add('P3DPBS')
    properties_texture.TEXTURE_PT_mapping.COMPAT_ENGINES.add('P3DPBS')

    from bl_ui import properties_game
    if hasattr( properties_game , 'OBJECT_PT_levels_of_detail'):
        properties_game.OBJECT_PT_levels_of_detail.COMPAT_ENGINES.add('P3DPBS')

    from bl_ui import properties_data_lamp
    properties_data_lamp.DATA_PT_preview.COMPAT_ENGINES.add('P3DPBS')

    from bl_ui import properties_particle
    properties_particle.PARTICLE_PT_context_particles.COMPAT_ENGINES.add('P3DPBS')
    properties_particle.PARTICLE_PT_emission.COMPAT_ENGINES.add('P3DPBS')
    properties_particle.PARTICLE_PT_render.COMPAT_ENGINES.add('P3DPBS')

def unregister():
    bpy.utils.unregister_class(PBSEngine)
