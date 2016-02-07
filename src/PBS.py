
import bpy
import math

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

        if not hasattr(context.material, "pbepbs"):
            self.layout.label("No PBS datablock")
            return

        box = self.layout.box()
        box.row().prop(context.material, "diffuse_color", "Base Color")

        box.row().prop(context.material.pbepbs, "metallic")
        box.row().prop(context.material.pbepbs, "roughness")

        if not context.material.pbepbs.metallic:
            box.row().prop(context.material.pbepbs, "ior")

        box.row().prop(context.material.pbepbs, "normal_strength")
        box.row()

        self.layout.separator()

        box = self.layout.box()
        box.label("Special properties")
        box.row().prop(context.material.pbepbs, "emissive_factor")
        box.row().prop(context.material.pbepbs, "translucency")
        box.row().prop(context.material, "alpha", "Transparency")
        box.row()
        # self.layout.separator()

        self.layout.label("Operators:")
        self.layout.row().operator("pbepbs.set_default_textures")

        self.layout.separator()


    def draw_header(self, context):
        self.layout.label(text="", icon="MATERIAL")



class PBSMatProps(bpy.types.PropertyGroup):

    """ This is the property group which stores the PBS properties of each
    material """

    def update_roughness(self, context):
        if self.roughness <= 0.0:
            context.material.specular_hardness = 511
        else:
            a = self.roughness * self.roughness
            context.material.specular_hardness = min(2 / (a * a) - 2, 511)


    roughness = bpy.props.FloatProperty(
        name="Roughness",
        description="The roughness of the material, 0 for perfect flat surfaces, "
                    "1 for complete rough surfaces.",
        subtype="FACTOR",
        update=update_roughness,
        default=0.3, min=0.0, max=1.0)

    ior = bpy.props.FloatProperty(
        name="IOR",
        description="Index of refraction, usually 1.5 for most materials.",
        subtype="FACTOR",
        default=1.5, min=1.0, max=2.7)

    metallic = bpy.props.BoolProperty(
        name="Metallic",
        description="Controls whether the material is metallic or not.",
        default=False)

    emissive_factor = bpy.props.FloatProperty(
        name="Emissive Factor",
        description="Values > 0.0 make the material emissive, receiving no shading "
                    "but emitting light with a color of the BaseColor instead",
        subtype="FACTOR",
        default=0.0,min=0.0, max=20.0)

    translucency = bpy.props.FloatProperty(
        name="Translucency",
        description="Makes the material translucent, e.g. for skin and foliage.",
        subtype="FACTOR",
        default=0.0,min=0.0, max=1.0)

    normal_strength = bpy.props.FloatProperty(
            name="Normalmap Strength",
            description="Strength of the Normal-Map, a value of 0.0 will cause no "
                        "normal mapping",
            subtype="FACTOR", default=0.0, min=0.0, max=1.0)


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
            if slot is not None and slot.texture is not None:
                print("Skipping used slot #", index)
                continue

            slot = material.texture_slots.create(index)
            texname = "Empty" + slot_name
            default_pth = join(dirname(__file__), "../res/" + texname + ".png")

            image = None
            for img in bpy.data.images:
                if img.filepath == default_pth:
                    # print("FOUND IMG")
                    image = img
                    break
            else:
                # print("LOAD IMG")
                bpy.ops.image.open(filepath=default_pth, relative_path=False)
                image = bpy.data.images[texname + ".png"]
                print("IMAGE=", image)

            texture = None
            for tex in bpy.data.textures:
                if tex.name == texname:
                    texture = tex
                    break
            else:
                texture = bpy.data.textures.new(texname, type="IMAGE")

            print("Setting image:", image)
            texture.image = image

            slot.texture_coords = "UV"
            slot.texture = texture

        return {'FINISHED'}


def register():
    bpy.utils.register_class(OperatorSetDefaultTextures)
    bpy.utils.register_class(PBSMatProps)
    bpy.utils.register_class(PBSMaterial)

    bpy.types.Material.pbepbs = bpy.props.PointerProperty(type=PBSMatProps)

def unregister():
    del bpy.types.Material.pbepbs
    bpy.utils.unregister_class(OperatorSetDefaultTextures)
    bpy.utils.unregister_class(PBSMatProps)
    bpy.utils.unregister_class(PBSMaterial)
