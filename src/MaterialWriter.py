# -*- encoding: utf-8 -*-
import os
import bpy
import time

from ExportException import ExportException

from pybamwriter.panda_types import *


class MaterialWriter(object):

    SHADING_MODELS = [
        "DEFAULT",
        "EMISSIVE",
        "CLEARCOAT",
        "TRANSPARENT_GLASS",
        "SKIN",
        "FOLIAGE",
        "TRANSPARENT_EMISSIVE"
    ]

    def __init__(self, writer):
        self.material_state_cache = {}
        self.writer = writer
        self.make_default_material()

    @property
    def log_instance(self):
        """ Helper to access the log instance """
        return self.writer.log_instance

    def make_default_material(self):
        """ Creates the default material """
        self.default_material = Material()
        self.default_state = RenderState()
        self.default_state.attributes.append(MaterialAttrib(self.default_material))

        self.default_material.base_color = (0.7, 0.7, 0.7, 1.0)
        self.default_material.metallic = 0.0
        self.default_material.roughness = 0.5
        self.default_material.refractive_index = 1.5
        self.default_material.emission = (0, 0, 0, 0)

    def create_state_from_material(self, material):
        """ Creates a render state based on a material """

        if not material:
            return self.default_state

        # Check if we already created this material
        if material.name in self.material_state_cache:
            return self.material_state_cache[material.name]

        # Create the render and material state
        virtual_state = RenderState()
        virtual_material = Material(material.name)

        # Extract the material properties:
        # In case we use PBS, encode its properties in a special way
        if not self.writer.settings.use_pbs:
            virtual_material.diffuse = (
                material.diffuse_color[0] * material.diffuse_intensity,
                material.diffuse_color[1] * material.diffuse_intensity,
                material.diffuse_color[2] * material.diffuse_intensity,
                material.alpha)
            virtual_material.ambient = (
                material.ambient,
                material.ambient,
                material.ambient,
                1.0)
            virtual_material.specular = (
                material.specular_color[0] * material.specular_intensity,
                material.specular_color[1] * material.specular_intensity,
                material.specular_color[2] * material.specular_intensity,
                material.specular_alpha)
            virtual_material.emission = (
                material.emit * material.diffuse_color[0] * material.diffuse_intensity,
                material.emit * material.diffuse_color[1] * material.diffuse_intensity,
                material.emit * material.diffuse_color[2] * material.diffuse_intensity,
                1.0)
        else:
            pbepbs = material.pbepbs

            if pbepbs.shading_model not in self.SHADING_MODELS:
                self.log_instance.warning("Unkown shading model '" + pbepbs.shading_model + "'")
                shading_model_id = 0
            else:
                shading_model_id = self.SHADING_MODELS.index(pbepbs.shading_model)

            # Emissive color contains:
            # (shading_model, normal_strength, arbitrary-0, arbitrary-1)
            # whereas arbitrary depends on the shading model

            if pbepbs.shading_model in ["EMISSIVE", "TRANSPARENT_EMISSIVE"]:
                virtual_material.base_color = (
                    material.diffuse_color[0] * pbepbs.emissive_factor,
                    material.diffuse_color[1] * pbepbs.emissive_factor,
                    material.diffuse_color[2] * pbepbs.emissive_factor,
                    1.0)
                virtual_material.metallic = 0
                virtual_material.roughness = 1
                virtual_material.refractive_index = 1.51

                if pbepbs.shading_model == "EMISSIVE":
                    virtual_material.emission = (shading_model_id, 0, 0, 0)
                else:
                    virtual_material.emission = (shading_model_id, 0, material.alpha, 0)

            else:
                virtual_material.base_color = (
                    material.diffuse_color[0],
                    material.diffuse_color[1],
                    material.diffuse_color[2],
                    1.0)

                if material.pbepbs.metallic and pbepbs.shading_model != "SKIN":
                    virtual_material.metallic = 1.0
                else:
                    virtual_material.metallic = 0.0

                if pbepbs.shading_model == "CLEARCOAT":
                    virtual_material.metallic = 1.0
                    virtual_material.refractive_index = 1.51

                if pbepbs.shading_model == "TRANSPARENT_GLASS":
                    virtual_material.metallic = 1.0

                virtual_material.roughness = material.pbepbs.roughness
                virtual_material.refractive_index = material.pbepbs.ior

                if pbepbs.shading_model in ("DEFAULT", "CLEARCOAT", "SKIN"):
                    arbitrary0, arbitrary1 = 0, 0
                elif pbepbs.shading_model == "FOLIAGE":
                    arbitrary0, arbitrary1 = material.pbepbs.translucency, 0
                elif pbepbs.shading_model == "TRANSPARENT_GLASS":
                    arbitrary0, arbitrary1 = material.alpha, 0

                virtual_material.emission = (
                    shading_model_id,
                    material.pbepbs.normal_strength,
                    arbitrary0,
                    arbitrary1)

        # Attach the material attribute to the render state
        virtual_state.attributes.append(MaterialAttrib(virtual_material))

        # Iterate over the texture slots and extract the stage nodes
        stage_nodes = []
        for idx, tex_slot in enumerate(material.texture_slots):
            use_srgb = idx == 0

            if tex_slot:
                lower_name = tex_slot.name.lower().replace(" ", "")
                if ("diffuse" in lower_name or "albedo" in lower_name or
                        "basecolor" in lower_name):
                    use_srgb = True

                if use_srgb:
                    self.log_instance.info("Detected srgb for texture", tex_slot.name)
                else:
                    self.log_instance.info("Using standard rgb for texture", tex_slot.name)
                stage_node = self.writer.texture_writer.create_stage_node_from_texture_slot(
                    tex_slot, sort=idx * 10, use_srgb=use_srgb)
                if stage_node:
                    stage_nodes.append(stage_node)
                else:
                    self.log_instance.warning("Invalid texture slot '" + tex_slot.name +
                                              "' on material '" + material.name + "', see previous message.")
            else:
                if idx < 4:
                    self.log_instance.warning("Empty required texture slot on material '" + material.name + "'")

        # Check if there is at least one texture, and if so, create a texture attrib
        if len(stage_nodes) > 0:

            texture_attrib = TextureAttrib()

            has_any_transform = False
            tex_mat_attrib = TexMatrixAttrib()

            # Attach the stage to the texture attrib
            for stage in stage_nodes:
                texture_attrib.on_stage_nodes.append(stage)
                tex_mat_attrib.add_stage(stage.stage, stage._pbe_uv_transform, 0)

                if stage._pbe_uv_transform.scale != (1, 1, 1):
                    has_any_transform = True

            virtual_state.attributes.append(texture_attrib)

            if has_any_transform:
                virtual_state.attributes.append(tex_mat_attrib)

        # Handle material type.
        if material.type == 'WIRE':
            virtual_state.attributes.append(RenderModeAttrib.wireframe)

        elif material.type == 'HALO':
            attrib = RenderModeAttrib(RenderModeAttrib.M_point)
            attrib.thickness = material.halo.size
            attrib.perspective = True
            virtual_state.attributes.append(attrib)

        # Check for game settings.
        if material.game_settings:
            if material.type in ('WIRE', 'HALO') or not material.game_settings.use_backface_culling:
                virtual_state.attributes.append(CullFaceAttrib.cull_none)

            mode = material.game_settings.alpha_blend
            attrib = None

            if mode == 'OPAQUE':
                attrib = TransparencyAttrib.none
            elif mode == 'ADD':
                attrib = ColorBlendAttrib.add
            elif mode == 'CLIP':
                attrib = TransparencyAttrib.binary
            elif mode == 'ALPHA':
                attrib = TransparencyAttrib.alpha
            elif mode == 'ALPHA_ANTIALIASING':
                attrib = TransparencyAttrib.multisample_mask

            if attrib:
                virtual_state.attributes.append(attrib)

        self.material_state_cache[material.name] = virtual_state

        return virtual_state
