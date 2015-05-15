
import bmesh

from .PBEExportException import PBEExportException

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
        
        print("Export to", self.filepath)

        for obj in self.objects:
            self._handle_object(obj)

        raise PBEExportException("Not implemented yet")

    def _handle_object(self, obj):
        """ Internal method to process an object during the export process """

        material_slots = obj.material_slots
        world_matrix = obj.matrix_world

        # TODO: Check here if camera or lamp -> if so, call _handle_camera, _handle_lamp
        print("Handle object:", obj.name)


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

        # Extract the arrays. This makes accessing faster in the loop
        vertices = mesh.vertices

        # Find the active uv layer and its name, in case there is one.
        if mesh.uv_layers.active:
            active_uv_layer = mesh.uv_layers.active.data
            active_uv_name = mesh.uv_layers.active.name
        else:
            active_uv_layer = None
            active_uv_name = ""

        print("Active UVMap:", active_uv_name)

        # Calculate normals
        mesh.calc_normals()

        # Iterate over the mesh polygons (=faces)
        for polygon in mesh.polygons:
            # print("\n-> Polygon index:", polygon.index, "length:", polygon.loop_total)

            # print ("-> Poly normal:", polygon.normal)

            # Iterate over the vertices
            for vtx_index in polygon.vertices:
                vtx_data = vertices[vtx_index]
                # print(" -> Vertex: ", vtx_index)
                # print("   -> Normal: ", vtx_data.normal)
                # print("   -> Pos: ", vtx_data.co)
                # print("   -> Undeformed pos: ", vtx_data.undeformed_co)

                if active_uv_layer:
                    uv_data = active_uv_layer[vtx_index]
                    # print("   -> UV:", uv_data.uv)


        # TODO: Delete mesh
        # mesh.delete() or sth like that.