# -*- encoding: utf-8 -*-
import os
import bpy
import time
import math
import mathutils
from ExportException import ExportException
from TextureWriter import TextureWriter
from GeometryWriter import GeometryWriter
from MaterialWriter import MaterialWriter

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
        self.texture_writer = TextureWriter(self)
        self.geometry_writer = GeometryWriter(self)
        self.material_writer = MaterialWriter(self)

        self.characters = {}

    def set_log_instance(self, log_instance):
        """ Sets the export logger instance, used for reporting warnings and errors
        during the export """
        self.log_instance = log_instance

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
        virtual_model_root = ModelRoot("SceneRoot")

        # First import all armatures.
        for armature in bpy.data.armatures:
            self.characters[armature] = self._handle_armature(armature, virtual_model_root)

        # Handle all selected objects
        for obj in self.objects:
            try:
                if obj.type != 'ARMATURE':
                    self._handle_object(obj, virtual_model_root)
            except Exception as msg:
                self.log_instance.error("Exception while exporting object '{}': {}".format(obj.name, msg))
                raise

        writer = BamWriter()
        writer.file_version = tuple(int(i) for i in self.settings.bam_version.split("."))
        writer.open_file(self.filepath)
        writer.write_object(virtual_model_root)
        writer.close()

        end_time = time.time()
        duration = round(end_time - start_time, 4)

        self.log_instance.info("-" * 50)
        self.log_instance.info("Wrote out bam with the version", writer.file_version)
        self.log_instance.info("Export finished in", duration, "seconds.")
        self.log_instance.info("Exported", format(self._stats_exported_vertices, ",d"),
                               "Vertices and", format(self._stats_exported_tris, ",d"), "Triangles")
        self.log_instance.info("Exported", self._stats_exported_objs,
                               "Objects and", self._stats_exported_geoms, "Geoms")

        if self._stats_duplicated_vertices:
            self.log_instance.info("Had to duplicate", format(self._stats_duplicated_vertices, ",d"),
                                   "Vertices due to different texture coordinates.")

        self.log_instance.info("Exported", len(self.material_writer.material_state_cache), "materials")
        self.log_instance.info("Exported", len(self.texture_writer.textures_cache),
                               "texture slots, using", len(self.texture_writer.images_cache), "images")
        self.log_instance.info("-" * 50)

    def _handle_camera(self, obj, parent):
        """ Internal method to handle a camera """
        pass

    def _handle_light(self, obj, parent):
        """ Internal method to handle a light """
        print("Exporting light", obj.name, "of type", obj.data.type)
        if obj.data.type == "POINT":
            light_node = SphereLight(obj.name)
            light_node.radius = obj.data.pbepbs.sphere_radius

        elif obj.data.type == "SPOT":
            light_node = Spotlight(obj.name)
            light_node.exponent = obj.data.spot_size

        elif obj.data.type == "AREA":
            light_node = RectangleLight(obj.name)
            size_x = obj.data.size
            size_y = size_x
            if obj.data.shape != "SQUARE":
                size_y = obj.data.size_y

            parent.transform.mat *= mathutils.Matrix(
                ((0, size_x, 0, 0),
                 (0, 0, size_y, 0),
                 (1, 0, 0, 0),
                 (0, 0, 0, 1)))
        else:
            self.log_instance.warning("TODO: Support light type:", obj.data.type)
            return

        color = obj.data.color
        if obj.data.pbepbs.use_temperature:
            color = obj.data.pbepbs.color_preview

        light_node.color = list(color) + [obj.data.energy]
        light_node.specular_color = light_node.color
        light_node.shadow_caster = obj.data.use_shadow
        light_node.sb_xsize = int(obj.data.pbepbs.shadow_map_res)
        light_node.sb_ysize = light_node.sb_ysize

        if obj.data.type in ("SPOT", "POINT"):
            light_node.attenuation = (0, 0, 1)
            profile = obj.data.pbepbs.ies_profile
            if profile != "none":
                light_node.tags["ies_profile"] = profile

        light_node.max_distance = obj.data.distance
        parent.add_child(light_node)

    def _handle_empty(self, obj, parent):
        """ Internal method to handle an empty object """
        pass

    def _handle_curve(self, obj, parent):
        """ Internal method to handle a curve """
        self.log_instance.warning("TODO: Handle curve:", obj.name)

    def _handle_font(self, obj, parent):
        """ Internal method to handle a font """
        self.log_instance.warning("TODO: Handle font:", obj.name)

    def _handle_lattice(self, obj, parent):
        """ Internal method to handle a lattice """
        self.log_instance.warning("TODO: Handle lattice:", obj.name)

    def _handle_armature(self, obj, parent):
        """ Internal method to handle an armature """

        char = Character(obj.name)
        bundle = char.bundles[0]
        skeleton = PartGroup(bundle, '<skeleton>')
        for bone in obj.bones:
            if bone.parent is None:
                self._handle_bone(bone, char, bundle, skeleton)

        parent.add_child(char)
        return char

    def _handle_bone(self, obj, char, root, parent):
        """ Internal method to handle a bone """

        matrix = obj.matrix_local
        if obj.parent:
            matrix = obj.parent.matrix_local.inverted() * matrix

        joint = CharacterJoint(char, root, parent, obj.name, matrix)
        joint.initial_net_transform_inverse = obj.matrix_local.inverted()

        for bone in obj.children:
            self._handle_bone(bone, char, root, joint)

    def _handle_mesh(self, obj, parent):
        """ Internal method to handle a mesh """
        self.geometry_writer.write_mesh(obj, parent)

    def _handle_lod(self, obj, lod_node):
        """ Internal method to handle LOD levels """

        distances = [level.distance for level in obj.lod_levels]
        distances.append(float('inf'))

        for i, level in enumerate(obj.lod_levels):
            lod_node.add_switch(distances[i + 1], distances[i])

            if level.use_mesh:
                self._handle_object_data(level.object, lod_node)
            else:
                self._handle_object_data(object, lod_node)

    def _handle_object(self, obj, parent):
        """ Internal method to process an object during the export process """
        print("Exporting object:", obj.name)

        self._stats_exported_objs += 1
        transform = TransformState()
        transform.mat = obj.matrix_world

        # Create a new panda node with the transform
        if hasattr(obj, 'lod_levels') and len(obj.lod_levels) > 0:
            node = LODNode(obj.name)
            node.transform = transform
            self._handle_lod(obj, node)
        else:
            node = PandaNode(obj.name)
            node.transform = transform
            self._handle_object_data(obj, node)

        # Attach the node to the scene graph
        parent.add_child(node)

        self._set_tags(obj, node)

        self._check_dupli(obj, node)
        self._check_billboard(obj, node)

    def _handle_object_data(self, obj, parent):
        """ Internal method to process an object datablock """

        if obj.type == "CAMERA":
            self._handle_camera(obj, parent)
        elif obj.type == "LAMP":
            self._handle_light(obj, parent)
        elif obj.type == "MESH":
            self._handle_mesh(obj, parent)
        elif obj.type == "EMPTY":
            self._handle_empty(obj, parent)
        elif obj.type == "CURVE":
            self._handle_curve(obj, parent)
        elif obj.type == "FONT":
            self._handle_font(obj, parent)
        elif obj.type == "LATTICE":
            self._handle_lattice(obj, parent)
        elif obj.type == "ARMATURE":
            pass
        else:
            self.log_instance.warning("Skipping object '" + obj.name + "' with unkown type: '" + str(obj.type) + "'")

    def _check_dupli(self, obj, parent):
        """ Checks for a dupli group """
        if obj.dupli_type != "NONE":
            if obj.dupli_type != "GROUP":
                self.log_instance.warning("Unsupported dupli type:", obj.dupli_type)
                return

            for sub_obj in obj.dupli_group.objects:
                self.log_instance.info("Exporting duplicated object:", sub_obj.name, "for parent", obj.name)
                self._handle_object(sub_obj, parent)
            return

    def _check_billboard(self, obj, node):
        """ Checks for a billboard """
        if not obj.active_material or not obj.active_material.game_settings:
            return

        orient = obj.active_material.game_settings.face_orientation
        if orient not in ('HALO', 'BILLBOARD'):
            return

        # Extract the rotation from the transform.  We do need to rotate it
        # by 90 degrees since Blender makes it look in the X axis, Panda in Y.
        loc, rot, scale = obj.matrix_world.decompose()
        node.transform.mat = mathutils.Matrix.Translation(loc) \
            * mathutils.Matrix(((0, scale[1], 0, 0),
                                (-scale[0], 0, 0, 0),
                                (0, 0, scale[2], 0),
                                (0, 0, 0, 1)))

        if orient == 'HALO':
            node.effects = RenderEffects.billboard_point_eye
        elif orient == 'BILLBOARD':
            node.effects = RenderEffects.billboard_axis

    def _set_tags(self, obj, panda_node):
        """ Reads all game object tags from the given object handle and applies
        it to the given panda node """
        for prop in obj.game.properties:
            name = prop.name
            val = str(prop.value)
            self.log_instance.info("Writing tags", name, val)
            panda_node.tags[name] = val

    def handle_particle_system(self, obj, parent, particle_system):
        """ Internal method to handle a particle system """

        if particle_system.settings.render_type != "OBJECT":
            self.log_instance.error("Skipping particle system '" + particle_system.name +
                                    "' since it does not use the OBJECT render type.")
            return

        settings = particle_system.settings
        duplicated_object = settings.dupli_object

        if duplicated_object is None:
            self.log_instance.error("Skipping particle system '" + particle_system.name +
                                    "' since it has no dupli-object assigned.")
            return

        particle_transform = obj.matrix_world.inverted()

        if settings.use_global_dupli:
            # Take object transform into account
            particle_transform *= duplicated_object.matrix_local

        for i, particle in enumerate(particle_system.particles):
            rotation = particle.rotation.to_matrix().to_4x4()
            location = mathutils.Matrix.Translation(particle.location)
            scale = mathutils.Matrix.Scale(particle.size, 3).to_4x4()
            particle_mat = particle_transform * (location * rotation * scale)
            node = PandaNode("Particle-" + str(i))
            node.transform = TransformState()
            node.transform.mat = particle_mat
            parent.add_child(node)
            self.geometry_writer.write_mesh(duplicated_object, node)

        self.log_instance.info("Wrote", len(particle_system.particles), "particles for system", particle_system.name)
