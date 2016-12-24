
import bpy
import bmesh
from array import array
from pybamwriter.panda_types import *


class GeometryWriter:

    """ Helper class to write out the actual vertices """

    def __init__(self, writer):
        self._create_default_array_formats()
        self.writer = writer
        self.geom_cache = {}

    @property
    def log_instance(self):
        """ Helper to access the log instance """
        return self.writer.log_instance

    def _group_mesh_faces_by_material(self, mesh, num_slots=40):
        """ Iterates over all faces of the given mesh, grouping them by their
        material index """
        polygons = [[] for i in range(num_slots)]

        for polygon in mesh.polygons:
            index = polygon.material_index

            # Should never happen, there can't be more than 40 slots I think.
            # So if we don't really need it, we don't use it, to save performance
            # assert index >= 0 and index < num_slots
            polygons[index].append(polygon)

        return polygons

    def _create_default_array_formats(self):
        """ Creates the default GeomVertexArrayFormats, so we do not have to
        recreate them for every geom  """
        self.gvd_formats = {}

        # Standard format, Vertex + Normal
        self.gvd_formats['v3n3'] = GeomVertexArrayFormat()
        self.gvd_formats['v3n3'].stride = 4 * 3 * 2
        self.gvd_formats['v3n3'].total_bytes = self.gvd_formats['v3n3'].stride
        self.gvd_formats['v3n3'].pad_to = 1
        self.gvd_formats['v3n3'].add_column("vertex", 3, GeomEnums.NT_float32,
                                            GeomEnums.C_point, start=0, column_alignment=4)
        self.gvd_formats['v3n3'].add_column("normal", 3, GeomEnums.NT_float32,
                                            GeomEnums.C_normal, start=3 * 4, column_alignment=4)

        # Standard format with texcoords, Vertex + Normal + Texcoord (UV)
        self.gvd_formats['v3n3t2'] = GeomVertexArrayFormat()
        self.gvd_formats['v3n3t2'].stride = 4 * 3 * 2 + 4 * 2
        self.gvd_formats['v3n3t2'].total_bytes = self.gvd_formats['v3n3t2'].stride
        self.gvd_formats['v3n3t2'].pad_to = 1
        self.gvd_formats['v3n3t2'].add_column("vertex", 3, GeomEnums.NT_float32,
                                              GeomEnums.C_point, start=0, column_alignment=4)
        self.gvd_formats['v3n3t2'].add_column("normal", 3, GeomEnums.NT_float32,
                                              GeomEnums.C_normal, start=3 * 4, column_alignment=4)
        self.gvd_formats['v3n3t2'].add_column("texcoord", 2, GeomEnums.NT_float32,
                                              GeomEnums.C_texcoord, start=2 * 3 * 4, column_alignment=4)

        # Vertex index format, using 16 bit indices
        self.gvd_formats['index16'] = GeomVertexArrayFormat()
        self.gvd_formats['index16'].stride = 2
        self.gvd_formats['index16'].total_bytes = self.gvd_formats['index16'].stride
        self.gvd_formats['index16'].pad_to = 1
        self.gvd_formats['index16'].add_column("index", 1, GeomEnums.NT_uint16,
                                               GeomEnums.C_index, start=0, column_alignment=1)

        # Vertex index format, using 32 bit indices, used for geoms with more than
        # 2 ** 16 vertices.
        self.gvd_formats['index32'] = GeomVertexArrayFormat()
        self.gvd_formats['index32'].stride = 4
        self.gvd_formats['index32'].total_bytes = self.gvd_formats['index32'].stride
        self.gvd_formats['index32'].pad_to = 1
        self.gvd_formats['index32'].add_column("index", 1, GeomEnums.NT_uint32,
                                               GeomEnums.C_index, start=0, column_alignment=1)

    def _create_geom_from_polygons(self, mesh, polygons, uv_coordinates=None):
        """ Creates a Geom from a set of polygons. If uv_coordinates is not None,
        texcoords will be written as well """

        # Compute the maximum possible amount of vertices for this geom. If it
        # extends the range of 16 bit, we have to use 32 bit indices
        use_32_bit_indices = False
        max_possible_vtx_count = len(polygons) * 3

        if max_possible_vtx_count >= 2**16 - 1:
            use_32_bit_indices = True
            self.log_instance.warning("Using 32 bit indices for large geom '" + mesh.name + "' - consider splitting it")

        # Check wheter the object has texture coordinates assigned
        have_texcoords = uv_coordinates is not None

        # Create handles to the data, this makes accessing it faster
        vertices = mesh.vertices

        # Store the number of written triangles and vertices
        num_triangles = 0
        num_vertices = 0
        num_duplicated = 0

        # Create the buffers to store the data inside
        if use_32_bit_indices:
            index_buffer = array('I')  # Unsigned Int
        else:
            index_buffer = array('H')  # Unsigned Short

        vertex_buffer = array('f')

        # Store the location of each mesh vertex
        vertex_mappings = [-1 for i in range(len(vertices))]
        vertex_uvs = [0.0 for i in range(len(vertices))]

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

                    # Store wheter we can reuse the vertex data
                    can_reuse = True

                    if have_texcoords:
                        # Check if the vertex texcoord matches. This might not be
                        # the cases on corners
                        u, v = uv_coordinates[poly.loop_indices[idx]].uv.to_2d()
                        uv_key = u * 10000.0 + v
                        if abs(vertex_uvs[vertex_index] - uv_key) > 0.0001:
                            # Vertex uv does *not* match. Most likely we are on an
                            # edge, so duplicate the vertex
                            can_reuse = False
                            num_duplicated += 1

                    # If we can reuse the vertex data, just reference it
                    if can_reuse:
                        index_buffer.append(vertex_mappings[vertex_index])
                        continue

                # If the vertex is not known, store its data and then write its index
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
                    u, v = uv_coordinates[poly.loop_indices[idx]].uv.to_2d()
                    vertex_buffer.append(u)
                    vertex_buffer.append(v)
                    vertex_uvs[vertex_index] = u * 10000.0 + v

                # Store the vertex index in the triangle data
                index_buffer.append(num_vertices)

                # Store the vertex index in the mappings and increment the
                # vertex counter
                vertex_mappings[vertex_index] = num_vertices
                num_vertices += 1

            num_triangles += 1

        # Determine the right vertex format
        vertex_format = self.gvd_formats['v3n3']
        index_format = self.gvd_formats['index16']

        # If we run out of indices, use 32 bit indices
        if use_32_bit_indices:
            index_format = self.gvd_formats['index32']

        # If we use texcoords, use a format which supports them
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

        # Increment statistics
        self.writer._stats_exported_vertices += num_vertices
        self.writer._stats_exported_tris += num_triangles
        self.writer._stats_duplicated_vertices += num_duplicated
        self.writer._stats_exported_geoms += 1

        return geom

    def write_mesh(self, obj, parent):
        """ Internal method to process a mesh during the export process """

        for modifier in obj.modifiers:
            if modifier.type == "PARTICLE_SYSTEM":
                particle_system = modifier.particle_system
                self.writer.handle_particle_system(obj, parent, particle_system)

        # Check if we alrady have the geom node cached
        if obj.data.name in self.geom_cache:
            virtual_geom_node = self.geom_cache[obj.data.name]

        else:

            # Create a new geom node to store all geoms
            virtual_geom_node = GeomNode(obj.data.name)

            # Convert the object to a mesh, so we can read the polygons
            mesh = obj.to_mesh(self.writer.context.scene,
                               apply_modifiers=True,
                               settings='PREVIEW',
                               calc_tessface=True,
                               calc_undeformed=True)

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
                # just use an empty material
                if slot:
                    render_state = self.writer.material_writer.create_state_from_material(slot.material)
                else:
                    render_state = RenderState.empty

                # Extract the per-material polygon list
                polygons = polygons_by_material[index]

                # Create a geom from those polygons
                virtual_geom = self._create_geom_from_polygons(mesh, polygons, active_uv_layer)

                # Add that geom to the geom node
                virtual_geom_node.add_geom(virtual_geom, render_state)

            bpy.data.meshes.remove(mesh)

            self.geom_cache[obj.data.name] = virtual_geom_node

        parent.add_child(virtual_geom_node)
