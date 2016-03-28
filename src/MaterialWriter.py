# -*- encoding: utf-8 -*-
import os
import bpy
import time

from ExportException import ExportException

from pybamwriter.panda_types import *

class MaterialWriter(object):

    def __init__(self, exporter):
        self.material_state_cache = {}
        self.exporter = exporter

        self.make_default_material()

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
        virtual_material = Material()

        # Extract the material properties:
        # In case we use PBS, encode its properties in a special way
        if not self.exporter.settings.use_pbs:
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
            shading_model_id = (
                "DEFAULT", "EMISSIVE", "CLEARCOAT", "TRANSPARENT",
                "SKIN", "FOLIAGE").index(pbepbs.shading_model)

            # Emissive color contains:
            # (shading_model, normal_strength, arbitrary-0, arbitrary-1)
            # whereas arbitrary depends on the shading model

            if pbepbs.shading_model == "EMISSIVE":
                virtual_material.base_color = (
                    material.diffuse_color[0] * pbepbs.emissive_factor,
                    material.diffuse_color[1] * pbepbs.emissive_factor,
                    material.diffuse_color[2] * pbepbs.emissive_factor,
                    1.0)
                virtual_material.metallic = 0
                virtual_material.roughness = 1
                virtual_material.refractive_index = 1.0
                virtual_material.emission = (shading_model_id, 0, 0, 0)

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

                virtual_material.roughness = material.pbepbs.roughness
                virtual_material.refractive_index = material.pbepbs.ior

                if pbepbs.shading_model in ("DEFAULT", "CLEARCOAT", "SKIN"):
                    arbitrary0, arbitrary1 = 0, 0
                elif pbepbs.shading_model == "FOLIAGE":
                    arbitrary0, arbitrary1 = material.pbepbs.translucency, 0
                elif pbepbs.shading_model == "TRANSPARENT":
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
            stage_node = self.exporter.texture_writer.create_stage_node_from_texture_slot(
                tex_slot, sort=idx*10, use_srgb=use_srgb)
            if stage_node:
                stage_nodes.append(stage_node)

        # Check if there is at least one texture, and if so, create a texture attrib
        if len(stage_nodes) > 0:

            texture_attrib = TextureAttrib()

            has_any_transform = False
            tex_mat_attrib = TexMatrixAttrib()

            # Attach the stage to the texture attrib
            for stage in stage_nodes:
                texture_attrib.on_stage_nodes.append(stage)
                tex_mat_attrib.add_stage(stage.stage, stage._pbe_uv_transform, 0)

                if stage._pbe_uv_transform.scale != (1,1,1):
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
