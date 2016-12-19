
import bpy
from bpy_extras.io_utils import ExportHelper

from SceneWriter import SceneWriter
from ExportException import ExportException


class ExportSettings(bpy.types.PropertyGroup):
    """ This class stores the exporter settings """

    tex_mode =  bpy.props.EnumProperty(
            name="Texture handling",
            description="How to handle textures",
            items=[
                ("ABSOLUTE", "Absolute", "Store absolute paths to the textures"),
                ("RELATIVE", "Relative", "Store relative paths to the textures"),
                ("COPY", "Copy (Recommended)", "Copy the textures to a folder relative to the bam file"),
                ("INCLUDE", "Include", "Include the textures in the bam file"),
                ("KEEP", "Keep", "Use the same texture path settings that blender uses (advanced)"),
            ],
            default="COPY")

    tex_copy_path = bpy.props.StringProperty(
            name="Texture copy path",
            description="The relative path where to copy the textures to",
            default="./tex/")

    use_pbs = bpy.props.BoolProperty(
            name="Use PBS addon",
            description="Whether to use the Physically Based Shading addon. This "
                        "stores the physically based properties of the material in "
                        "the diffuse and specular components to be used in the application "
                        "later on",
            default=True
        )

    bam_version = bpy.props.EnumProperty(
        name="Bam Version",
        description="Bam version to write out",
        items=(
            ('6.14', '6.14 (Panda3D 1.5.x / 1.6.x)', 'Writes bams for 1.5.x and (1.6.x'),
            ('6.22', '6.22 (Panda3D 1.7.0)', 'Writes bams for 1.7.0'),
            ('6.24', '6.24 (Panda3D 1.7.1 / 1.7.2)', 'Writes bams for 1.7.1 and 1.7.2'),
            ('6.30', '6.30 (Panda3D 1.8.x)', 'Writes bams for 1.8.x'),
            ('6.37', '6.37 (Panda3D 1.9.x)', 'Writes bams for 1.9.x'),
            ('6.41', '6.41 (Panda3D DEVEL)', 'Writes bams for the devel version (1.10)'),
        ),
        default='6.41')

    def draw(self, layout):
        """ This function is called by the PBEExportOperator, whenever the export-
        screen is rendered. We should draw all available export properties here """

        layout.row().prop(self, 'bam_version')
        layout.row().prop(self, 'tex_mode')

        if self.tex_mode == "COPY":
            box = layout.box()
            box.row().prop(self, 'tex_copy_path')

        layout.row().prop(self, 'use_pbs')


class ExportOperator(bpy.types.Operator, ExportHelper):
    """ This class is the main export operator, being called whenever the user
    wants to export the model """

    bl_idname = "export.panda3d_bam"
    bl_label = "Export to Panda3D BAM"

    filename_ext = ".bam"
    filepath = bpy.props.StringProperty()

    def execute(self, context):
        """ This function is called when the operator is executed. It starts the
        export process """

        objects = bpy.context.selected_objects
        scene = bpy.context.scene

        # Check if there exists a settings datablock
        if not hasattr(scene, "pbe") or not scene.pbe:
            self.report({'ERROR'}, "Scene has no PBE datablock")
            return {'CANCELLED'}

        # Check if there are active objects
        if len(objects) < 1:
            self.report({'ERROR'}, "No objects selected!")
            return {'CANCELLED'}

        # Fix scene properties first
        bpy.ops.pbepbs.set_default_textures()
        bpy.ops.pbepbs.fix_lamp_types()

        # Try to execute the export process
        try:
            writer = SceneWriter()
            writer.set_context(bpy.context)
            writer.set_settings(scene.pbe)
            writer.set_filepath(self.filepath)
            writer.set_objects(objects)
            writer.write_bam_file()
        except ExportException as err:
            self.report({'ERROR'}, err.message)
            return {'CANCELLED'}

        return {'FINISHED'}

    def draw(self, context):
        """ This function is called when the export-screen is drawn. We draw
        our properties here so the user can adjust it """
        context.scene.pbe.draw(self.layout)

def PBEExportFuncCallback(self, context):
    self.layout.operator(ExportOperator.bl_idname, text="Panda3D (.bam)")

# Register the module

def register():
    bpy.utils.register_class(ExportSettings)
    bpy.utils.register_class(ExportOperator)
    bpy.types.INFO_MT_file_export.append(PBEExportFuncCallback)
    bpy.types.Scene.pbe = bpy.props.PointerProperty(type=ExportSettings)

def unregister():
    try:
        del bpy.types.Scene.pbe
    except AttributeError:
        pass
    bpy.utils.unregister_class(ExportSettings)
    bpy.utils.unregister_class(ExportOperator)
    bpy.types.INFO_MT_file_export.remove(PBEExportFuncCallback)
