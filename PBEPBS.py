
import bpy
from os.path import join, dirname



class PBEPBSMaterial(bpy.types.Panel):

    """ This is a panel to display the PBS properties of the currently
    selected material """

    bl_idname = "MATERIAL_PT_pbs_material_props"
    bl_label = "Physically Based Shading Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    def draw(self, context):

        row = self.layout.row()
        row.operator("pbepbs.set_default_diffuse")
        row.operator("pbepbs.set_default_metallic")

        self.layout.row().prop(context.material.pbepbs, "basecolor")

        # row = self.layout.row()
        self.layout.row().prop(context.material.pbepbs, "roughness")
        self.layout.row().prop(context.material.pbepbs, "metallic")
        self.layout.row().prop(context.material.pbepbs, "specular")

        self.layout.row().prop(context.material.pbepbs, "bumpmap_strength")

    def draw_header(self, context):
        self.layout.label(text="", icon="MATERIAL")



class PBEPBSMatProps(bpy.types.PropertyGroup):

    """ This is the property group which stores the PBS properties of each
    material """

    roughness = bpy.props.FloatProperty(
        name="Roughness",
        description="The roughness of the material, 0 for perfect flat surfaces, "
                    "1 for complete rough surfaces.",
        subtype="FACTOR",
        default=0.3, min=0.0, max=1.0)

    specular = bpy.props.FloatProperty(
        name="Specular",
        description="Specular factor for the material, should be 0.5 for most "
                    "materials, except in special cases",
        subtype="FACTOR",
        default=0.5, min=0.0, max=1.0)

    metallic = bpy.props.FloatProperty(
        name="Metallic",
        description="Metallic factor, should be either 0 or 1.",
        subtype="FACTOR",
        default=0.0, min=0.0, max=1.0)

    basecolor = bpy.props.FloatVectorProperty(
        name="BaseColor",
        description="Base color of the material. In case of non-metallic materials, "
                    "this denotes the diffuse color. In case of metallic materials, "
                    "this denotes the specular color",
        subtype="COLOR",
        default=[1.0, 1.0, 1.0],
        min=0.0,
        max=1.0)


    bumpmap_strength = bpy.props.FloatProperty(
            name="Bump-Map Strength",
            description="Strength of the Bump Map",
            subtype="FACTOR",
            default=0.0, min=0.0, max=1.0)


class PBEOperatorDefaultDiffuse(bpy.types.Operator):
    """ Operator to set the default diffuse properties on a material """
    bl_idname = "pbepbs.set_default_diffuse"
    bl_label = "Set default diffuse material"
 
    def execute(self, context):
        context.material.pbepbs.basecolor = [1, 1, 1]
        context.material.pbepbs.specular = 0.5
        context.material.pbepbs.metallic = 0.0
        context.material.pbepbs.roughness = 0.3
        context.material.pbepbs.bumpmap_strength = 0.0
        return{'FINISHED'}


class PBEOperatorDefaultMetallic(bpy.types.Operator):
    """ Operator to set the default metallic properties on a material """
    bl_idname = "pbepbs.set_default_metallic"
    bl_label = "Set default metallic material"
 
    def execute(self, context):
        context.material.pbepbs.basecolor = [1, 1, 1]
        context.material.pbepbs.specular = 0.5
        context.material.pbepbs.metallic = 1.0
        context.material.pbepbs.roughness = 0.4
        context.material.pbepbs.bumpmap_strength = 0.0
        return{'FINISHED'}

bpy.utils.register_module(__name__)
