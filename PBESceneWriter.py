# -*- encoding: utf-8 -*-
import os
import bmesh
import bpy
import time
import shutil
from array import array

from PBEExportException import PBEExportException

from pybamwriter.panda_types import *
from pybamwriter.bam_writer import BamWriter

class PBESceneWriter:

    """ This class handles the conversion from the blender scene graph to the
    virtual scene graph, to be able to export that converted scene graph to a 
    bam file. """

    def __init__(self):
        """ Creates a new scene writer """
        self._create_default_array_formats()
        self._stats_exported_vertices = 0
        self._stats_exported_tris = 0
        self._stats_exported_objs = 0
        self._stats_exported_geoms = 0
        self.material_state_cache = {}
        self.textures_cache = {}
        self.images_cache = {}

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
        
        # Make the output easier to read - just for debugging!
        os.system("cls")
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
        duration = round(end_time - start_time, 2)

        print("Export finished in", duration, "seconds.")
        print("Exported", format(self._stats_exported_vertices, ",d"), "Vertices and", format(self._stats_exported_tris, ",d"), "Triangles")
        print("Exported", self._stats_exported_objs, "Objects and", self._stats_exported_geoms, "Geoms")
        print("Total materials:", len(self.material_state_cache.keys()))
        print("Total texture slots:", len(self.textures_cache.keys()))
        print("Total images:", len(self.images_cache.keys()))

    def _group_mesh_faces_by_material(self, mesh, num_slots = 40):
        """ Iterates over all faces of the given mesh, grouping them by their
        material index """

        polygons = [[] for i in range(num_slots)]

        for polygon in mesh.polygons:
            index = polygon.material_index
            assert index >= 0 and index < num_slots
            polygons[index].append(polygon)

        return polygons

    def _handle_camera(self, obj):
        """ Internal method to handle a camera """
        pass

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

        # Attach the node to the scene graph
        self.virtual_model_root.add_child(virtual_node)

    def _handle_curve(self, obj):
         """ Internal method to handle a curve """
         pass

    def _handle_font(self, obj):
        """ Internal method to handle a font """
        pass

    def _handle_lattice(self, obj):
        """ Internal method to handle a lattice """
        pass

    def _handle_armature(self, obj):
        """ Internal method to handle a lattice """
        pass

    def _handle_object(self, obj):
        """ Internal method to process an object during the export process """
        print("Export object:", obj.name)

        self._stats_exported_objs += 1

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
            raise PBEExportException("Object " + obj.name + " has a non implemented type: '" + obj.type + "'")

    def _create_default_array_formats(self):
        """ Creates the default GeomVertexArrayFormats, so we do not have to 
        recreate them for every geom  """
    
        self.gvd_formats = {}

        self.gvd_formats['v3n3'] = GeomVertexArrayFormat()
        self.gvd_formats['v3n3'].stride = 4 * 3 * 2
        self.gvd_formats['v3n3'].total_bytes = self.gvd_formats['v3n3'].stride
        self.gvd_formats['v3n3'].pad_to = 1
        self.gvd_formats['v3n3'].add_column("vertex", 3, GeomEnums.NT_float32,
                                GeomEnums.C_point, start=0, column_alignment=4)
        self.gvd_formats['v3n3'].add_column("normal", 3, GeomEnums.NT_float32,
                                GeomEnums.C_vector, start=3 * 4, column_alignment=4)

        self.gvd_formats['v3n3t2'] = GeomVertexArrayFormat()
        self.gvd_formats['v3n3t2'].stride = 4 * 3 * 2 + 4 * 2
        self.gvd_formats['v3n3t2'].total_bytes = self.gvd_formats['v3n3t2'].stride
        self.gvd_formats['v3n3t2'].pad_to = 1
        self.gvd_formats['v3n3t2'].add_column("vertex", 3, GeomEnums.NT_float32,
                                GeomEnums.C_point, start=0, column_alignment=4)
        self.gvd_formats['v3n3t2'].add_column("normal", 3, GeomEnums.NT_float32,
                                GeomEnums.C_vector, start=3 * 4, column_alignment=4)
        self.gvd_formats['v3n3t2'].add_column("texcoord", 2, GeomEnums.NT_float32,
                                GeomEnums.C_texcoord, start=2 * 3 * 4, column_alignment=4)

        self.gvd_formats['index16'] = GeomVertexArrayFormat()
        self.gvd_formats['index16'].stride = 2
        self.gvd_formats['index16'].total_bytes = self.gvd_formats['index16'].stride
        self.gvd_formats['index16'].pad_to = 1
        self.gvd_formats['index16'].add_column("index", 1, GeomEnums.NT_uint16, 
            GeomEnums.C_index, start = 0, column_alignment = 1)

        self.gvd_formats['index32'] = GeomVertexArrayFormat()
        self.gvd_formats['index32'].stride = 4
        self.gvd_formats['index32'].total_bytes = self.gvd_formats['index32'].stride
        self.gvd_formats['index32'].pad_to = 1
        self.gvd_formats['index32'].add_column("index", 1, GeomEnums.NT_uint32, 
            GeomEnums.C_index, start = 0, column_alignment = 1)

    def _convert_to_panda_filepath(self, filepath):
        filepath = filepath.replace("\\", "/")
        if ":/" in filepath:
            idx = filepath.index(":/")
            filepath = "/" + filepath[0:idx].lower() + "/" + filepath[idx+2:]

        # Blender indicates relative paths with a double slash
        if filepath.startswith("//"):
            filepath = "./" + filepath[2:]

        return filepath

    def _convert_blender_file_format(self, extension):
        """ Converts a blender format like JPEG to an extension like .jpeg """

        extensions = {
            "BMP": ".bmp",
            "PNG": ".png",
            "JPEG": ".jpg",
            "TARGA": ".tga",
            "TIFF": ".tiff"
        }

        if extension in extensions:
            return extensions[extension]

        # In case we can't find the extension, return png
        print("Warning: Unkown blender file format:", extension)
        return ".png"

    def _save_image(self, image):
        """ Saves an image to the disk """

        # Fetch old filename first
        old_filename = bpy.path.abspath(image.filepath)

        # Extract image name from filepath and create a new filename
        tex_name = bpy.path.basename(old_filename)
        dest_filename = os.path.join(os.path.dirname(self.filepath), str(self.settings.tex_copy_path), tex_name)

        # Check if the target directory exists, and if not, create it
        target_dir = os.path.dirname(dest_filename)

        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        # In case the file is found on disk, just copy it
        if os.path.isfile(old_filename):

            # If there is already a file at the location, delete that first
            if os.path.isfile(dest_filename):

                # If the file source is the file target, just return
                if os.stat(dest_filename) == os.stat(old_filename):
                    return dest_filename

                os.remove(dest_filename)

            shutil.copyfile(old_filename, dest_filename)

        # When its not on disk, try to use the image.save() function
        else:

            # Make a copy of the image and try to save that
            copy = image.copy()

            # Adjust filepath extension
            extension = self._convert_blender_file_format(copy.file_format)
            dest_filename = ".".join(dest_filename.split(".")[:-1]) + extension

            print("save image copy to", dest_filename)
            copy.filepath_raw = dest_filename

            # Finally try to save the image
            try:
                copy.save()
            except Exception as msg:
                raise PBEExportException("Error during image export: " + str(msg))
            finally:
                 bpy.data.images.remove(copy)

        return dest_filename

    def _create_sampler_state_from_texture_slot(self, texture_slot):
        """ Creates a sampler state from a given texture slot """
        state = SamplerState()
        state.wrap_u = SamplerState.WM_repeat
        state.wrap_v = SamplerState.WM_repeat
        state.wrap_w = SamplerState.WM_repeat
        return state

    def _create_texture_from_image(self, image):
        """ Creates a texture object from a given image """

        if image.name in self.images_cache:
            return self.images_cache[image.name]

        mode = str(self.settings.tex_mode)
        texture = Texture(image.name)
        is_packed = image.packed_file is not None
        current_dir = os.path.dirname(self.filepath)


        # In case we store absolute filepaths
        if mode == "ABSOLUTE":

            # When the image is packed, write it to disk first
            if is_packed:
                texture.filename = self._convert_to_panda_filepath(self._save_image(image))

            # Otherwise just convert the filename
            else:
                src = bpy.path.abspath(image.filepath)
                src = self._convert_to_panda_filepath(src)
                texture.filename = src

        elif mode == "RELATIVE":

            # When the image is packed, write it to disk first
            if is_packed:
                abs_filename = self._save_image(image)
                rel_filename = bpy.path.relpath(abs_filename, start=current_dir)
                texture.filename = self._convert_to_panda_filepath(rel_filename)
            
            # Otherwise just convert the filename
            else:
                src = bpy.path.abspath(image.filepath)
                rel_src = bpy.path.relpath(src, start=current_dir)
                texture.filename = self._convert_to_panda_filepath(rel_src)
                        
        elif mode == "COPY":
            
            # When copying textures, we just write all textures to disk
            abs_filename = self._save_image(image)
            rel_filename = bpy.path.relpath(abs_filename, start=current_dir)
            texture.filename = self._convert_to_panda_filepath(rel_filename)

        elif mode == "INCLUDE":
            raise PBEExportException("Texture mode INCLUDE is not supported yet!")
        elif mode == "KEEP":
            raise PBEExportException("Texture mode KEEP is not supported yet!")

        self.images_cache[image.name] = texture

        return texture

    def _create_texture_stage_node_from_texture_slot(self, texture_slot, sort=0):
        """ Creates a panda texture object from a blender texture object """ 


        # Check if the slot is not empty and a texture is assigned
        if not texture_slot or not texture_slot.texture or texture_slot.texture.type == "NONE":
            return None

        # Check if the texture slot was already processed, and if so, return the
        # cached result
        if texture_slot.name in self.textures_cache:
            return self.textures_cache[texture_slot.name]

        # Check if the texture slot mode is supported
        if texture_slot.texture_coords != "UV":
            # raise PBEExportException("Unsupported texture coordinate mode for slot '" + texture_slot.name + "': " + texture_slot.texture_coords)
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
            "STUCCI", "VORONOI", "WOOD"]:
            print("TODO: Handle generated image")
            return None

        else:
            raise PBEExportException("Unsupported texture type for texture '" + texture.name + "': " + texture.type)

        self.textures_cache[texture_slot.name] = stage_node

        return stage_node

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
            virtual_material.emissive = (
                material.emit * material.diffuse_color[0] * material.diffuse_intensity,
                material.emit * material.diffuse_color[1] * material.diffuse_intensity,
                material.emit * material.diffuse_color[2] * material.diffuse_intensity,
                1.0)
        else:
            virtual_material.diffuse = (
                material.pbepbs.basecolor[0],
                material.pbepbs.basecolor[1],
                material.pbepbs.basecolor[2], 1)
            virtual_material.specular = (
                material.pbepbs.specular,
                material.pbepbs.metallic,
                material.pbepbs.roughness,
                material.pbepbs.bumpmap_strength)
            virtual_material.ambient = (0, 0, 0, 1)
            virtual_material.emissive = (0, 0, 0, 1)

        # Attach the material attribute to the render state
        virtual_state.attributes.append(MaterialAttrib(virtual_material))

        # Iterate over the texture slots and extract the stage nodes
        stage_nodes = []
        for idx, tex_slot in enumerate(material.texture_slots):
            stage_node = self._create_texture_stage_node_from_texture_slot(tex_slot, sort=idx*10)
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

            print("Textures: ", len(stage_nodes), len(texture_attrib.on_stage_nodes))

        self.material_state_cache[material.name] = virtual_state

        return virtual_state

    def _create_geom_from_polygons(self, mesh, polygons, uv_coordinates = None):
        """ Creates a Geom from a set of polygons. If uv_coordinates is not None,
        texcoords will be written aswell """

        # Compute the maximum possible amount of vertices for this geom. If it 
        # extends the range of 16 bit, we have to use 32 bit indices
        use_32_bit_indices = False
        max_possible_vtx_count = len(polygons) * 3

        if max_possible_vtx_count >= 2**16 - 1:
            use_32_bit_indices = True
            print("Hint: using 32 bit indices for large geom")


        # Check wheter the object has texture coordinates assigned
        have_texcoords = uv_coordinates is not None

        # Create handles to the data, this makes accessing it faster
        vertices = mesh.vertices

        # Store the number of written triangles and vertices
        num_triangles = 0
        num_vertices = 0

        # Create the buffers to store the data inside
        if use_32_bit_indices:
            index_buffer = array('I') # Unsigned Int
        else:
            index_buffer = array('H') # Unsigned Short

        vertex_buffer = array('f')

        # Store the location of each mesh vertex 
        vertex_mappings = [-1 for i in range(len(vertices))] 

        # Iterate over all triangles
        for poly in polygons:

            # Check if the polygon uses smooth shading
            is_smooth = poly.use_smooth

            # Iterate over the 3 vertices of that triangle
            for idx, vertex_index in enumerate(poly.vertices):

                # If the vertex is already known, just write its index, but only
                # if the polygon does use smooth shading, otherwise all vertices
                # are duplicated anyway.
                if is_smooth and vertex_mappings[vertex_index] >= 0:
                    index_buffer.append(vertex_mappings[vertex_index])

                # If the vertex is not known, store its data and then write its index
                else:
                    vertex = vertices[vertex_index]

                    # Write the vertex object position
                    vertex_buffer.append(vertex.co[0])
                    vertex_buffer.append(vertex.co[1])
                    vertex_buffer.append(vertex.co[2])

                    # Write the vertex normal
                    # When smooth shading is enabled, write per vertex normals,
                    # otherwise write the per-poly normal for all vertices
                    if is_smooth:
                        vertex_buffer.append(vertex.normal[0])
                        vertex_buffer.append(vertex.normal[1])
                        vertex_buffer.append(vertex.normal[2])
                    else:
                        vertex_buffer.append(poly.normal[0])
                        vertex_buffer.append(poly.normal[1])
                        vertex_buffer.append(poly.normal[2])

                    # Add the texcoord
                    if have_texcoords:
                        uv = uv_coordinates[poly.loop_indices[idx]].uv
                        vertex_buffer.append(uv[0])
                        vertex_buffer.append(uv[1])

                    # Store the vertex index in the triangle data
                    index_buffer.append(num_vertices)

                    # Store the vertex index in the mappings and increment the
                    # vertex counter
                    vertex_mappings[vertex_index] = num_vertices
                    num_vertices += 1

            num_triangles += 1

        # Determine the right vertex format
        # TODO: Check wheter an uv-map is active and select a format with texcoords
        # then
        vertex_format = self.gvd_formats['v3n3']
        index_format = self.gvd_formats['index16']

        if use_32_bit_indices:
            index_format = self.gvd_formats['index32']

        if have_texcoords:
            vertex_format = self.gvd_formats['v3n3t2']

        # Create the vertex array data, to store the per-vertex data
        array_data = GeomVertexArrayData(vertex_format, GeomEnums.UH_static)
        array_data.buffer += vertex_buffer

        # Create the index array data, to store the per-primitive vertex references
        index_array_data = GeomVertexArrayData(index_format, GeomEnums.UH_static)
        index_array_data.buffer += index_buffer

        # Create the array container for the per-vertex data
        vertex_data = GeomVertexData("triangle", GeomVertexFormat(vertex_format), GeomEnums.UH_static)
        vertex_data.arrays.append(array_data)

        # Create the primitive container
        triangles = GeomTriangles(GeomEnums.UH_static)
        triangles.vertices = index_array_data
        triangles.first_vertex = 0

        # Make sure to set the correct index type on the primitive, otherwise 
        # it will assume 16 bit indices
        if use_32_bit_indices:
            triangles.index_type = GeomEnums.NT_uint32

        # The number of vertices obviously equals to thrice the amount of triangles
        triangles.num_vertices = num_triangles * 3

        # Create the geom to wrap arround
        geom = Geom(vertex_data)
        geom.primitives.append(triangles)

        self._stats_exported_vertices += num_vertices
        self._stats_exported_tris += num_triangles
        self._stats_exported_geoms += 1

        return geom


    def _handle_mesh(self, obj):
        """ Internal method to process a mesh during the export process """

        # Create the transform state
        transformState = TransformState()
        transformState.mat = obj.matrix_world




        # Convert the object to a mesh, so we can read the polygons
        mesh = obj.to_mesh(self.context.scene, 
            apply_modifiers = True, 
            settings = 'RENDER', 
            calc_tessface = True, 
            calc_undeformed = True)

        # Get a BMesh representation
        b_mesh = bmesh.new()
        b_mesh.from_mesh(mesh)

        # Triangulate the mesh. This makes stuff simpler, and panda can't handle
        # polygons with more than 3 vertices.
        bmesh.ops.triangulate(b_mesh, faces=b_mesh.faces)

        # Copy the bmesh back to the original mesh 
        b_mesh.to_mesh(mesh)

        # Find the active uv layer and its name, in case there is one.
        if mesh.uv_layers.active:
            active_uv_layer = mesh.uv_layers.active.data
            active_uv_name = mesh.uv_layers.active.name
        else:
            active_uv_layer = None
            active_uv_name = ""

        # Group the polygons by their material index. We have to perform this 
        # operation, because we have to create a single geom for each material
        polygons_by_material = self._group_mesh_faces_by_material(mesh)

        # Calculate the per-vertex normals, in case blender did not do that yet.
        mesh.calc_normals()

        # Create a new geom node to store all geoms
        virtual_geom_node = GeomNode(obj.name)
        virtual_geom_node.transform = transformState

        # Extract material slots, but ensure there is always one slot, so objects
        # with no actual material get exported, too
        material_slots = obj.material_slots

        if len(material_slots) == 0:
            material_slots = [None]

        # Create the different geoms, 1 per material
        for index, slot in enumerate(material_slots):

            # Skip the material slot if no polygon references it
            if len(polygons_by_material[index]) < 1:
                continue

            # Create a virtual material if the slot contains a material. Otherwise
            # just an empty material
            if slot and slot.material:
                render_state = self._create_state_from_material(slot.material)
            else:
                render_state = RenderState.empty

            # Extract the per-material polygon list
            polygons = polygons_by_material[index]

            # Create a geom from those polygons
            virtual_geom = self._create_geom_from_polygons(mesh, polygons, active_uv_layer)

            # Add that geom to the geom node
            virtual_geom_node.add_geom(virtual_geom, render_state)

        # Finally attach the geom node to the model root
        self.virtual_model_root.add_child(virtual_geom_node)

        # TODO: Delete mesh
        # mesh.delete() or sth like that.
