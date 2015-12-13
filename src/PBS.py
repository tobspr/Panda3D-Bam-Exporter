
import bpy

from os.path import join, dirname, abspath


class PBSMaterial(bpy.types.Panel):

    """ This is a panel to display the PBS properties of the currently
    selected material """

    bl_idname = "MATERIAL_PT_pbs_material_props"
    bl_label = "Physically Based Shading Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    def draw(self, context):

        self.layout.label("PBS Material Properties:")

        box = self.layout.box()
        box.row().prop(context.material.pbepbs, "basecolor")

        # row = self.layout.row()
        box.row().prop(context.material.pbepbs, "roughness")
        box.row().prop(context.material.pbepbs, "metallic")
        box.row().prop(context.material.pbepbs, "specular")

        box.row().prop(context.material.pbepbs, "bumpmap_strength")

        self.layout.separator()

        self.layout.label("Material options:")

        self.layout.row().operator("pbepbs.set_default_diffuse")
        self.layout.row().operator("pbepbs.set_default_metallic")
        self.layout.row().operator("pbepbs.set_default_textures")


    def draw_header(self, context):
        self.layout.label(text="", icon="MATERIAL")



class PBSMatProps(bpy.types.PropertyGroup):

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


class OperatorSetDefaultTextures(bpy.types.Operator):
    """ Operator to fill the empty texture slots on a material with default textures """

    bl_idname = "pbepbs.set_default_textures"
    bl_label = "Fill default PBS textures"

    def execute(self, context):

        if not hasattr(context, "material"):
            return {'CANCELLED'}
        print("Executing default texture operator")
        material = context.material

        for index, slot_name in enumerate(["BaseColor", "Normal", "Specular", "Roughness"]):
            slot = material.texture_slots[index]
            # print("SLOT = ", slot)
            if slot is not None and slot.texture is not None:
                print("Skipping used slot #", index)
                continue

            slot = material.texture_slots.create(index)
            texname = "Empty" + slot_name 
            default_pth = join(dirname(__file__), "../res/" + texname + ".png")
                
            image = None
            for img in bpy.data.images:
                if img.filepath == default_pth:
                    print("FOUND IMG")
                    image = img
                    break
            else:
                print("LOAD IMG")
                bpy.ops.image.open(filepath=default_pth, relative_path=False)
                image = bpy.data.images[texname + ".png"]
                print("IMAGE=", image)

            texture = None
            for tex in bpy.data.textures:
                if tex.name == texname:
                    print("FOUND TEX")
                    texture = tex
                    break
            else:
                print("LOAD TEX")
                texture = bpy.data.textures.new(texname, type="IMAGE")

            print("Setting image:", image)
            texture.image = image

            slot.texture_coords = "UV"
            slot.texture = texture

        return {'FINISHED'}


class OperatorDefaultDiffuse(bpy.types.Operator):
    """ Operator to set the default diffuse properties on a material """
    bl_idname = "pbepbs.set_default_diffuse"
    bl_label = "Set default PBS diffuse material"
 
    def execute(self, context):
        context.material.pbepbs.basecolor = [1, 1, 1]
        context.material.pbepbs.specular = 0.5
        context.material.pbepbs.metallic = 0.0
        context.material.pbepbs.roughness = 0.3
        context.material.pbepbs.bumpmap_strength = 0.0
        return {'FINISHED'}


class OperatorDefaultMetallic(bpy.types.Operator):
    """ Operator to set the default metallic properties on a material """
    bl_idname = "pbepbs.set_default_metallic"
    bl_label = "Set default PBS metallic material"
 
    def execute(self, context):
        context.material.pbepbs.basecolor = [1, 1, 1]
        context.material.pbepbs.specular = 0.5
        context.material.pbepbs.metallic = 1.0
        context.material.pbepbs.roughness = 0.4
        context.material.pbepbs.bumpmap_strength = 0.0
        return {'FINISHED'}


def register():
    bpy.utils.register_module(__name__)
    bpy.types.Material.pbepbs = bpy.props.PointerProperty(type=PBSMatProps)

def unregister():
    del bpy.types.Material.pbepbs
    bpy.utils.unregister_module(__name__)
