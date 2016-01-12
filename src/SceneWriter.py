# -*- encoding: utf-8 -*-
import os
import bpy
import time
import mathutils
from ExportException import ExportException
from TextureWriter import TextureWriter
from GeometryWriter import GeometryWriter

from pybamwriter.panda_types import *
from pybamwriter.bam_writer import BamWriter

class SceneWriter:

    """ This class handles the conversion from the blender scene graph to the
    virtual scene graph, to be able to export that converted scene graph to a 
    bam file. """

    def __init__(self):
        """ Creates a new scene writer """
        self._stats_exported_vertices = 0
        self._stats_exported_tris = 0
        self._stats_exported_objs = 0
        self._stats_exported_geoms = 0
        self._stats_duplicated_vertices = 0
        self.material_state_cache = {}
        self.texture_writer = TextureWriter(self)
        self.geometry_writer = GeometryWriter(self)

    def set_filepath(self, filepath):
        """ Sets the filepath used to store the bam file. In future, the writer
        will be able to write to a stream aswell """
        self.filepath = filepath

    def set_context(self, context):
        """ Sets the blender context """
        self.context = context

    def set_objects(self, objects):
        """ Sets the object to export. Usually this is the list of all selected
        objects """
        self.objects = objects

    def set_settings(self, settings):
        """ Sets the handle to the PBEExportSettings structure, stored in the
        scene datablock """
        self.settings = settings

    def write_bam_file(self):
        """ Writes out the bam file, convertin the scene to a virtual scene graph
        first, and then exporting that to a bam file """
        
        # Make the output easier to read - just for debugging
        # os.system("cls")
        start_time = time.time()

        # Create the root of our model. All objects will be parented to this
        self.virtual_model_root = ModelRoot("SceneRoot")

        # Handle all selected objects
        for obj in self.objects:
            self._handle_object(obj)

        writer = BamWriter()
        writer.open_file(self.filepath)
        writer.write_object(self.virtual_model_root)
        writer.close()

        end_time = time.time()
        duration = round(end_time - start_time, 4)

        print("-" * 79)
        print("Export finished in", duration, "seconds.")
        print("Exported", format(self._stats_exported_vertices, ",d"), "Vertices and", format(self._stats_exported_tris, ",d"), "Triangles")
        print("Exported", self._stats_exported_objs, "Objects and", self._stats_exported_geoms, "Geoms")

        if self._stats_duplicated_vertices:
            print("Had to duplicate", format(self._stats_duplicated_vertices, ",d"), "Vertices due to different texture coordinates.")
        
        print("Exported", len(self.material_state_cache.keys()), "materials")
        print("Exported", len(self.texture_writer.textures_cache.keys()), "texture slots, using", len(self.texture_writer.images_cache.keys()), "images")
        print("-" * 79)

    def _handle_camera(self, obj):
        """ Internal method to handle a camera """
        self._handle_empty(obj)

    def _handle_light(self, obj):
         """ Internal method to handle a light """
         pass

    def _handle_empty(self, obj):
        """ Internal method to handle an empty object """

        # Create the transform state based on the object
        transformState = TransformState()
        transformState.mat = obj.matrix_world

        # Create a new panda node with the transform
        virtual_node = PandaNode(obj.name)
        virtual_node.transform = transformState

        self._set_tags(obj, virtual_node)

        # Attach the node to the scene graph
        self.virtual_model_root.add_child(virtual_node)

    def _handle_curve(self, obj):
        """ Internal method to handle a curve """
        print("TODO: Handle curve:", obj.name)

    def _handle_font(self, obj):
        """ Internal method to handle a font """
        print("TODO: Handle font:",obj.name)

    def _handle_lattice(self, obj):
        """ Internal method to handle a lattice """
        print("TODO: Handle lattice:",obj.name)

    def _handle_armature(self, obj):
        """ Internal method to handle a lattice """
        print("TODO: Handle armature:",obj.name)

    def _handle_mesh(self, obj):
        """ Internal method to handle a mesh """
        panda_node = self.geometry_writer.write_mesh(obj)
        self._set_tags(obj, panda_node)
        self.virtual_model_root.add_child(panda_node)

    def _handle_object(self, obj):
        """ Internal method to process an object during the export process """
        print("Exporting object:", obj.name)

        self._stats_exported_objs += 1

        self._check_dupli(obj)

        if obj.type == "CAMERA":
            self._handle_camera(obj)
        elif obj.type == "LAMP":
            self._handle_light(obj)
        elif obj.type == "MESH":
            self._handle_mesh(obj)
        elif obj.type == "EMPTY":
            self._handle_empty(obj)
        elif obj.type == "CURVE":
            self._handle_curve(obj)
        elif obj.type == "FONT":
            self._handle_font(obj)
        elif obj.type == "LATTICE":
            self._handle_lattice(obj)
        elif obj.type == "ARMATURE":
            self._handle_armature(obj)
        else:
            raise ExportException("Object " + obj.name + " has a non implemented type: '" + obj.type + "'")

    def _check_dupli(self, obj):
        """ Checks for a dupli group """
        if obj.dupli_type != "NONE":
            if obj.dupli_type != "GROUP":
                print("Warning: unsupported dupli type:", obj.dupli_type)
                return
            parent_transform = obj.matrix_world
            for sub_obj in obj.dupli_group.objects:
                print("Exporting duplicated object:", sub_obj.name, "for parent", obj.name)
                panda_node = self.geometry_writer.write_mesh(sub_obj, parent_transform)
                self.virtual_model_root.add_child(panda_node)
            return

    def _set_tags(self, obj, panda_node):
        """ Reads all game object tags from the given object handle and applies
        it to the given panda node """
        for prop in obj.game.properties:
            name = prop.name
            val = str(prop.value)
            print("Writing tags", name, val)
            panda_node.tags[name] = val

    def _create_state_from_material(self, material):
        """ Creates a render state based on a material """

        # Check if we already created this material
        if material.name in self.material_state_cache:
            return self.material_state_cache[material.name]

        # Create the render and material state
        virtual_state = RenderState()
        virtual_material = Material()

        # Extract the material properties:
        # In case we use PBS, encode its properties in a special way

        if not self.settings.use_pbs:
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
            virtual_material.base_color = (
                material.diffuse_color[0],
                material.diffuse_color[1],
                material.diffuse_color[2],
                material.alpha)
            virtual_material.metallic = 1.0 if material.pbepbs.metallic else 0.0
            virtual_material.roughness = material.pbepbs.roughness
            virtual_material.refractive_index = material.pbepbs.ior
            print("Writing roughness:", material.pbepbs.roughness)
            virtual_material.emission = (
                material.pbepbs.normal_strength,
                0.0,
                material.pbepbs.translucency,
                material.pbepbs.emissive_factor)

        # Attach the material attribute to the render state
        virtual_state.attributes.append(MaterialAttrib(virtual_material))

        # Iterate over the texture slots and extract the stage nodes
        stage_nodes = []
        for idx, tex_slot in enumerate(material.texture_slots):
            stage_node = self.texture_writer.create_stage_node_from_texture_slot(tex_slot, sort=idx*10)
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

        self.material_state_cache[material.name] = virtual_state

        return virtual_state

    def handle_particle_system(self, obj, particle_system):
        """ Internal method to handle a particle system """

        if particle_system.settings.render_type != "OBJECT":
            print("Skipping particle system", particle_system.name, "since it does not use the OBJECT render type.")
            return

        settings = particle_system.settings
        duplicated_object = settings.dupli_object

        if duplicated_object is None:
            print("Skipping particle system", particle_system.name, "since it has no dupli-object assigned.")
            return

        for particle in particle_system.particles:
            rotation = particle.rotation.to_matrix().to_4x4()
            location = mathutils.Matrix.Translation(particle.location)
            scale = mathutils.Matrix.Scale(particle.size, 3).to_4x4()
            particle_mat = location * rotation * scale

            panda_node = self.geometry_writer.write_mesh(duplicated_object, custom_transform=particle_mat)
            self.virtual_model_root.add_child(panda_node)

        print("Wrote", len(particle_system.particles), "particles for system", particle_system.name)
