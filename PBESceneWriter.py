
import os
import bmesh
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

        # Create the root of our model. All objects will be parented to this
        self.virtual_model_root = ModelRoot("SceneRoot")

        # Handle all selected objects
        for obj in self.objects:
            self._handle_object(obj)

        writer = BamWriter()
        writer.open_file(self.filepath)
        writer.write_object(self.virtual_model_root)
        writer.close()

        raise PBEExportException("Not implemented yet")


    def _group_mesh_faces_by_material(self, mesh, num_slots = 20):
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

    def _handle_object(self, obj):
        """ Internal method to process an object during the export process """
        print("Handle object:", obj.name)

        if obj.type == "CAMERA":
            self._handle_camera(obj)
        elif obj.type == "LAMP":
            self._handle_light(obj)
        elif obj.type == "MESH":
            self._handle_mesh(obj)
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

        self.gvd_formats['index'] = GeomVertexArrayFormat()
        self.gvd_formats['index'].stride = 4
        self.gvd_formats['index'].total_bytes = self.gvd_formats['index'].stride
        self.gvd_formats['index'].pad_to = 1
        self.gvd_formats['index'].add_column("index", 1, GeomEnums.NT_uint32, 
            GeomEnums.C_index, start = 0, column_alignment = 4)

    def _handle_material(self, material):
        """ Converts a blender material to a panda material """
        virtual_material = Material()
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
            material.emit,
            material.emit,
            material.emit,
            1.0)
        return virtual_material

    def _create_geom_from_polygons(self, mesh, polygons, uv_coordinates = None):
        """ Creates a Geom from a set of polygons. If uv_coordinates is not None,
        texcoords will be written aswell """

        # Create handles to the data, this makes accessing it faster
        vertices = mesh.vertices

        # Store the number of written triangles and vertices
        num_triangles = 0
        num_vertices = 0

        # Create the buffers to store the data inside
        vertex_buffer = array('f')
        index_buffer = array('I')

        # Store the location of each mesh vertex 
        vertex_mappings = [-1 for i in range(len(vertices))] 

        # Iterate over all triangles
        for poly in polygons:

            # Iterate over the 3 vertices of that triangle
            for vertex_index in poly.vertices:

                # If the vertex is already known, just write its index
                if vertex_mappings[vertex_index] >= 0:
                    index_buffer.append(vertex_mappings[vertex_index])

                # If the vertex is not known, store its data and then write its index
                else:
                    vertex = vertices[vertex_index]

                    # Write the vertex object position
                    vertex_buffer.append(round(vertex.co[0], 5))
                    vertex_buffer.append(round(vertex.co[1], 5))
                    vertex_buffer.append(round(vertex.co[2], 5))

                    # Write the vertex normal
                    vertex_buffer.append(round(vertex.normal[0], 5))
                    vertex_buffer.append(round(vertex.normal[1], 5))
                    vertex_buffer.append(round(vertex.normal[2], 5))

                    # Store the vertex index in the triangle data
                    index_buffer.append(num_vertices)

                    # Store the vertex index in the mappings and increment the
                    # vertex counter
                    vertex_mappings[vertex_index] = num_vertices
                    num_vertices += 1

            num_triangles += 1

        print("Triangles=", num_triangles, "Vertices=", num_vertices)

        # Determine the right vertex format
        # TODO: Check wheter an uv-map is active and select a format with texcoords
        # then
        vertex_format = self.gvd_formats['v3n3']

        # Create the vertex array data, to store the per-vertex data
        array_data = GeomVertexArrayData(vertex_format, GeomEnums.UH_static)
        array_data.buffer += vertex_buffer

        # Create the index array data, to store the per-primitive vertex references
        index_array_data = GeomVertexArrayData(self.gvd_formats['index'], GeomEnums.UH_static)
        index_array_data.buffer += index_buffer

        # Create the array container for the per-vertex data
        vertex_data = GeomVertexData("triangle", GeomVertexFormat(vertex_format), GeomEnums.UH_static)
        vertex_data.arrays.append(array_data)

        # Create the primitive container
        triangles = GeomTriangles(GeomEnums.UH_static)
        triangles.vertices = index_array_data
        triangles.first_vertex = 0

        # The number of vertices obviously equals to thrice the amount of triangles
        triangles.num_vertices = num_triangles * 3

        # Create the geom to wrap arround
        geom = Geom(vertex_data)
        geom.primitives.append(triangles)

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
        virtual_geom_node = GeomNode()
        virtual_geom_node.transform = transformState

        # Create the different geoms, 1 per material
        for index, slot in enumerate(obj.material_slots):

            # Skip the material slot if no polygon references it
            if len(polygons_by_material[index]) < 1:
                continue

            # Create a virtual material if the slot contains a material. Otherwise
            # just an empty material
            if slot and slot.material:
                virtual_material = self._handle_material(slot.material)
            else:
                virtual_material = Material()

            polygons = polygons_by_material[index]

            # Create the geom render state
            virtual_render_state = RenderState()
            virtual_render_state.attributes.append(MaterialAttrib(virtual_material))

            virtual_geom = self._create_geom_from_polygons(mesh, polygons, active_uv_layer)

            virtual_geom_node.add_geom(virtual_geom, virtual_render_state)

            # TODO: Add vertices to the geom
            # geom_node = GeomNode("Model")
            # geom_node.add_geom(geom)
            # geom_node.state = RenderState(ColorAttrib(ColorAttrib.T_flat, (1.0, 0.6, 0.2, 1.0)))


        self.virtual_model_root.add_child(virtual_geom_node)







        # TODO: Delete mesh
        # mesh.delete() or sth like that.