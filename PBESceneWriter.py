
import os
import bmesh


from PBEExportException import PBEExportException
from pybamwriter.panda_types import TransformState, Material

class PBESceneWriter:

    """ This class handles the conversion from the blender scene graph to the
    virtual scene graph, to be able to export that converted scene graph to a 
    bam file. """

    def __init__(self):
        pass

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
        
        # Make the debugging output easier to read - just for debugging!
        os.system("cls")

        print("Export to", self.filepath)

        for obj in self.objects:
            self._handle_object(obj)

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

    def _handle_object(self, obj):
        """ Internal method to process an object during the export process """

        # TODO: Check here if camera or lamp -> if so, call _handle_camera, _handle_lamp
        print("Handle object:", obj.name)
        self._handle_mesh(obj)

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

        print("Active UVMap:", active_uv_name)

        # Group the polygons by their material index. We have to perform this 
        # operation, because we have to create a single geom for each material
        polygons_by_material = self._group_mesh_faces_by_material(mesh)

        # Calculate the per-vertex normals, in case blender did not do that yet.
        mesh.calc_normals()


        # Extract the arrays. This makes accessing faster in the loop
        vertices = mesh.vertices

        # Create the different geoms, 1 per material
        for index, slot in enumerate(obj.material_slots):
            if slot and slot.material:
                

                virtual_material = self._handle_material(slot.material) 
                print(virtual_material.diffuse)







        # Iterate over the mesh polygons (=faces)
        # for polygon in mesh.polygons:
            # print("\n-> Polygon index:", polygon.index, "length:", polygon.loop_total)

            # print ("-> Poly normal:", polygon.normal)
            # print ("-> Poly material:", polygon.material_index)

            # Iterate over the vertices
            # for vtx_index in polygon.vertices:
                # vtx_data = vertices[vtx_index]
                # print(" -> Vertex: ", vtx_index)
                # print("   -> Normal: ", vtx_data.normal)
                # print("   -> Pos: ", vtx_data.co)
                # print("   -> Undeformed pos: ", vtx_data.undeformed_co)

                # if active_uv_layer:
                    # uv_data = active_uv_layer[vtx_index]
                    # print("   -> UV:", uv_data.uv)


        # TODO: Delete mesh
        # mesh.delete() or sth like that.