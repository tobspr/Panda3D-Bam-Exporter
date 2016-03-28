
import bpy
import os
import shutil

from Util import convert_blender_file_format, convert_to_panda_filepath

from ExportException import ExportException
from pybamwriter.panda_types import *

class TextureWriter(object):

    """ This class handles the writing of textures, either generated ones
    or from the disk """

    def __init__(self, writer):
        self.textures_cache = {}
        self.images_cache = {}
        self.writer = writer

    def _save_image(self, image):
        """ Saves an image to the disk """

        # Fetch old filename first
        old_filename = bpy.path.abspath(image.filepath)
        if old_filename == "":
            # Empty texture, rename it to the textures name
            old_filename = image.name + ".png"

        # Extract image name from filepath and create a new filename
        tex_name = bpy.path.basename(old_filename)
        dest_filename = os.path.join(
            os.path.dirname(self.writer.filepath), str(self.writer.settings.tex_copy_path), tex_name)


        # Check if the target directory exists, and if not, create it
        target_dir = os.path.dirname(dest_filename)

        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        # In case the file is found on disk, just copy it
        if os.path.isfile(old_filename):

            # If there is already a file at the location, delete that first
            if os.path.isfile(dest_filename):

                # If the file source is equal to the file target, just return,
                # no copying needed
                if os.stat(dest_filename) == os.stat(old_filename):
                    return dest_filename

                os.remove(dest_filename)

            shutil.copyfile(old_filename, dest_filename)

        # When its not on disk, try to use the image.save() function
        else:

            # Make a copy of the image and try to save that
            copy = image.copy()

            # Adjust filepath extension
            extension = convert_blender_file_format(copy.file_format)
            dest_filename = ".".join(dest_filename.split(".")[:-1]) + extension

            print("Save image copy to", dest_filename)
            copy.filepath_raw = dest_filename

            # Finally try to save the image
            try:
                copy.save()
            except Exception as msg:
                raise ExportException("Error during image export: " + str(msg))
            finally:
                 bpy.data.images.remove(copy)

        return dest_filename

    def _create_sampler_state_from_texture_slot(self, texture_slot):
        """ Creates a sampler state from a given texture slot """
        state = SamplerState()

        tex_handle = texture_slot.texture
        if tex_handle:

            # Process texture settings

            # Mipmapping
            if hasattr(tex_handle, "use_mipmap") and tex_handle.use_mipmap:
                state.minfilter = SamplerState.FT_linear_mipmap_linear
            else:
                if hasattr(tex_handle, "use_interpolation") and not tex_handle.use_interpolation:
                    state.minfilter = SamplerState.FT_nearest
                else:
                    state.minfilter = SamplerState.FT_linear

            state.magfilter = SamplerState.FT_linear

            # Texture wrap modes
            wrap_modes = {
                "EXTEND": SamplerState.WM_clamp,
                "CLIP": SamplerState.WM_border_color,
                "CLIP_CUBE": SamplerState.WM_border_color,
                "REPEAT": SamplerState.WM_repeat,
                "CHECKER": SamplerState.WM_repeat
            }

            if hasattr(tex_handle, "extension"):
                if tex_handle.extension in wrap_modes:
                    wrap_mode = wrap_modes[tex_handle.extension]
                    state.wrap_u, state.wrap_v, state.wrap_w = [wrap_mode] * 3
                else:
                    print("Unkown texture extension:", tex_handle.extension)

            # Improve texture sharpness
            state.anisotropic_degree = 16

        return state

    def _create_texture_from_image(self, image):
        """ Creates a texture object from a given image """

        # Check if we already wrote the image
        if image.name in self.images_cache:
            return self.images_cache[image.name]

        mode = str(self.writer.settings.tex_mode)
        texture = Texture(image.name)

        if image.depth == 8:
            texture.num_components = 1
        # No case for 16bits, could be one or two channel
        elif image.depth == 24:
            texture.num_components = 3
        elif image.depth == 32:
            texture.num_components = 4
        else:
            print("WARNING: Cannot determine component count of", image.name, ", assuming 3")
            texture.num_components = 3
        is_packed = image.packed_file is not None
        current_dir = os.path.dirname(self.writer.filepath)

        # In case we store absolute filepaths
        if mode == "ABSOLUTE":

            # When the image is packed, write it to disk first
            if is_packed:
                texture.filename = convert_to_panda_filepath(self._save_image(image))

            # Otherwise just convert the filename
            else:
                src = bpy.path.abspath(image.filepath)
                src = convert_to_panda_filepath(src)
                texture.filename = src

        elif mode == "RELATIVE":

            # When the image is packed, write it to disk first
            if is_packed:
                abs_filename = self._save_image(image)
                rel_filename = bpy.path.relpath(abs_filename, start=current_dir)
                texture.filename = convert_to_panda_filepath(rel_filename)

            # Otherwise just convert the filename
            else:
                src = bpy.path.abspath(image.filepath)
                rel_src = bpy.path.relpath(src, start=current_dir)
                texture.filename = convert_to_panda_filepath(rel_src)

        elif mode == "COPY":

            # When copying textures, we just write all textures to disk
            abs_filename = self._save_image(image)
            rel_filename = bpy.path.relpath(abs_filename, start=current_dir)
            texture.filename = convert_to_panda_filepath(rel_filename)

        elif mode == "INCLUDE":
            raise ExportException("Texture mode INCLUDE is not supported yet!")
        elif mode == "KEEP":
            raise ExportException("Texture mode KEEP is not supported yet!")

        self.images_cache[image.name] = texture

        return texture

    def create_stage_node_from_texture_slot(self, texture_slot, sort=0, use_srgb=False):
        """ Creates a panda texture object from a blender texture object """

        # Check if the slot is not empty and a texture is assigned
        if not texture_slot or not texture_slot.texture or texture_slot.texture.type == "NONE":
            return None

        cache_key = texture_slot.name + "-sort:" + str(sort)

        # Check if the texture slot was already processed, and if so, return the
        # cached result
        if cache_key in self.textures_cache:
            return self.textures_cache[cache_key]

        # Check if the texture slot mode is supported
        if texture_slot.texture_coords != "UV":
            print("Unsupported texture coordinate mode for slot '" + texture_slot.name + "': " + texture_slot.texture_coords)
            return None

        # Create sampler state
        stage_node = TextureAttrib.StageNode()
        stage_node.sampler = self._create_sampler_state_from_texture_slot(texture_slot)
        stage_node.texture = None
        stage_node.stage = TextureStage(texture_slot.name + "-" + str(sort))

        # Store uv scale
        stage_node._pbe_uv_transform = TransformState()
        stage_node._pbe_uv_transform.scale = (texture_slot.scale[0], texture_slot.scale[1], texture_slot.scale[2])

        # Set texture stage sort
        stage_node.stage.sort = sort
        stage_node.stage.default = False
        stage_node.stage.priority = 0

        texture = texture_slot.texture

        # Check if the texture type is supported
        if texture.type == "IMAGE":

            # Extract the image
            image = texture.image

            try:
                stage_node.texture = self._create_texture_from_image(image)
            except Exception as msg:
                print("Could not extract image:", msg)
                return None
            stage_node.texture.default_sampler = stage_node.sampler

        elif texture.type in ["BLEND", "CLOUDS", "DISTORTED_NOISE", "ENVIRONMENT_MAP",
            "MAGIC", "MARBLE", "MUSGRAVE", "NOISE", "OCEAN", "POINT_DENSITY",
            "STUCCI", "VORONOI", "VOXEL_DATA", "WOOD"]:
            print("TODO: Handle generated image")
            return None

        else:
            raise ExportException("Unsupported texture type for texture '" + texture.name + "': " + texture.type)

        formats = [None, Texture.F_luminance, Texture.F_luminance_alpha, Texture.F_rgb, Texture.F_rgba]
        stage_node.texture.format = formats[stage_node.texture.num_components]

        if use_srgb:
            if stage_node.texture.num_components == 3:
                stage_node.texture.format = Texture.F_srgb
            elif stage_node.texture.num_components == 4:
                stage_node.texture.format = Texture.F_srgb_alpha
            else:
                print("WARNING: Cannot set srgb on less than 3 channel texture:", stage_node.texture.name)

        self.textures_cache[cache_key] = stage_node
        return stage_node
