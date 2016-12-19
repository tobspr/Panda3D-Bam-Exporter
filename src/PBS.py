
import bpy
import math
import mathutils

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

        pbepbs = context.material.pbepbs

        box = self.layout.box()
        box.row().prop(pbepbs, "shading_model")
        box.row().prop(context.material, "diffuse_color", "Base Color")

        if pbepbs.shading_model != "EMISSIVE":

            if pbepbs.shading_model not in ("SKIN", "FOLIAGE", "CLEARCOAT"):
                box.row().prop(pbepbs, "metallic")

            if not pbepbs.metallic and  pbepbs.shading_model not in ("CLEARCOAT"):
                    box.row().prop(pbepbs, "ior", "Index of Refraction")

            box.row().prop(pbepbs, "roughness")


            box.row().prop(pbepbs, "normal_strength")
            box.row()

        self.layout.separator()

        if pbepbs.shading_model not in ("DEFAULT", "FOLIAGE", "CLEARCOAT", "SKIN"):
            box = self.layout.box()
            box.label("Shading model properties")
            if pbepbs.shading_model == "EMISSIVE":
                box.row().prop(pbepbs, "emissive_factor")
            elif pbepbs.shading_model == "TRANSLUCENT":
                box.row().prop(pbepbs, "translucency")
            elif pbepbs.shading_model == "TRANSPARENT":
                box.row().prop(context.material, "alpha", "Transparency")
            box.row()

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

    def update_specular(self, context):
        f0 = (self.ior - 1) / (self.ior + 1)
        f0 *= f0
        context.material.specular_intensity = f0

    shading_model = bpy.props.EnumProperty(
        name="Shading Model",
        description="The shading model to use",
        items=(
            ("DEFAULT", "Default", "Default shading model"),
            ("EMISSIVE", "Emissive", "Emissive material"),
            ("CLEARCOAT", "Clear Coat", "Clearcoat shading model e.g. for car paint"),
            ("TRANSPARENT", "Transparent", "Transparent material"),
            ("SKIN", "Skin", "Skin material"),
            ("FOLIAGE", "Foliage (Vegetation)", "Two-Sided foliage"),
        ),
        default="DEFAULT"
        )

    roughness = bpy.props.FloatProperty(
        name="Roughness",
        description="The roughness of the material, 0 for perfect flat surfaces, "
                    "1 for complete rough surfaces.",
        subtype="FACTOR",
        update=update_roughness,
        default=0.3, min=0.0, max=1.0)

    ior = bpy.props.FloatProperty(
        name="Index of Refraction",
        description="Index of refraction, usually 1.5 for most materials.",
        subtype="FACTOR",
        update=update_specular,
        default=1.5, min=1.001, max=2.4)

    metallic = bpy.props.BoolProperty(
        name="Metallic",
        description="Controls whether the material is metallic or not.",
        default=False)

    emissive_factor = bpy.props.FloatProperty(
        name="Emissive Factor",
        description="Values > 0.0 make the material emissive, receiving no shading "
                    "but emitting light with a color of the BaseColor instead",
        subtype="FACTOR",
        default=0.0, min=0.0, max=1.0)

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
    bl_label = "Fill all materials with default PBS textures"

    def execute(self, context):
        # if not hasattr(context, "material"):
            # return {'CANCELLED'}

        print("Executing default texture operator")
        # material = context.material
        for material in bpy.data.materials:
            print("Processing material", material)
            for index, slot_name in enumerate(["basecolor", "normal", "specular", "roughness"]):
                slot = material.texture_slots[index]
                if slot is not None and slot.texture is not None:
                    continue

                slot = material.texture_slots.create(index)
                texname = "empty_" + slot_name
                default_pth = join(dirname(__file__), "../res/" + texname + ".png")

                image = None
                for img in bpy.data.images:
                    if img.filepath == default_pth:
                        image = img
                        break
                else:
                    bpy.ops.image.open(filepath=default_pth, relative_path=False)
                    for key in bpy.data.images.keys():
                        if (texname + ".png") in key:
                            image = bpy.data.images[key]
                            break
                    else:
                        raise Exception("Loaded " + texname + " from '" + default_pth + "' but it was not loaded into bpy.data.images!")

                texture = None
                for tex in bpy.data.textures:
                    if tex.name == texname:
                        texture = tex
                        break
                else:
                    texture = bpy.data.textures.new(texname, type="IMAGE")

                texture.image = image

                try:
                    slot.texture_coords = "UV"
                except Exception as msg:
                    print("FAILED to set texture slot, due to the following error:")
                    print(msg)
                    slot.texture_coords = "GLOBAL"
                slot.texture = texture
        
        print("Done.")

        return {'FINISHED'}

class OperatorFixLampTypes(bpy.types.Operator):
    """ Operator to set use_sphere on all lights """

    bl_idname = "pbepbs.fix_lamp_types"
    bl_label = "Fix PBS Lamp types"

    def execute(self, context):

        for lamp in bpy.data.lamps:
            if lamp.type == "POINT":
                lamp.use_sphere = True


        return {'FINISHED'}

class PBSDataPanel(bpy.types.Panel):

    """ This is a panel to display the PBS properties of the currently
    selected object """

    bl_idname = "MATERIAL_PT_pbs_light_props"
    bl_label = "Physically Based Shading Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    def draw(self, context):

        if not context.object:
            self.layout.label("No object selected")
            return

        obj = context.object

        if obj.type == "LAMP":
            if not hasattr(obj.data, "pbepbs"):
                self.layout.label("Lamp has no PBS datablock")
                return

            obj_data = obj.data
            pbs_data = obj_data.pbepbs

            box = self.layout.box()
            box.row().prop(obj.data, "type", "Light type")

            if obj.data.type not in ("POINT", "SPOT"):
                box.row().label("Type not supported yet!")
                return

            if obj.data.type == "POINT":            
                box.row().prop(pbs_data, "sphere_radius")


            box.row().prop(pbs_data, "use_temperature")

            if pbs_data.use_temperature:
                box.row().prop(pbs_data, "color_temperature")
                box.row().prop(pbs_data, "color_preview")
            else:
                box.row().prop(obj.data, "color", "Color")


            box.row().prop(obj.data, "distance", "Radius")
            box.row().prop(obj.data, "energy", "Brightness")

            box.row().prop(obj.data, "use_shadow", "Enable Shadows")

            if obj.data.use_shadow:
                box.row().prop(pbs_data, "shadow_map_res")

                if int(pbs_data.shadow_map_res) > 512:
                    box.row().label("WARNING: Very high shadow map resolution!")

            if obj.data.type == "SPOT":
                box.row().prop(obj.data, "spot_size")

# Matrix to convert from xyz to rgb
xyz_to_rgb = mathutils.Matrix((
    (3.2406, -0.9689, 0.0557),
    (-1.5372, 1.8758, -0.2050),
    (-0.4986, 0.0415, 1.0570)
)).transposed()


def get_temperature_color_preview(lamp_props):
    """ Returns a preview color for the lamp data when a color temperature is used """
    temperature = lamp_props.color_temperature

    mm = 1000.0 / temperature
    mm2 = mm ** 2
    mm3 = mm2 * mm
    x, y = 0, 0

    if temperature < 4000:
        x = -0.2661239 * mm3 - 0.2343580 * mm2 + 0.8776956 * mm + 0.179910
    else:
        x = -3.0258469 * mm3 + 2.1070379 * mm2 + 0.2226347 * mm + 0.240390

    x2 = x**2
    x3 = x2 * x
    if temperature < 2222:
        y = -1.1063814 * x3 - 1.34811020 * x2 + 2.18555832 * x - 0.20219683
    elif temperature < 4000:
        y = -0.9549476 * x3 - 1.37418593 * x2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x3 - 5.87338670 * x2 + 3.75112997 * x - 0.37001483

    # xyY to XYZ, assuming Y=1.
    xyz = mathutils.Vector((x / y, 1, (1 - x - y) / y))
    return xyz_to_rgb * xyz


class PBSLampProps(bpy.types.PropertyGroup):

    """ This is the property group which stores the PBS properties of each
    lamp """

    def update_shadow_resolution(self, context):
        if context.object:
            context.object.data.shadow_buffer_size = int(context.object.data.pbepbs.shadow_map_res)

    def update_color_temperature(self, context):
        if context.object:
            if context.object.data.pbepbs.use_temperature:
                context.object.data.color = get_temperature_color_preview(context.object.data.pbepbs)

    shadow_map_res = bpy.props.EnumProperty(
        name="Shadow Resolution",
        description="Resolution of the shadow map in pixels",
        items=(
            ("128", "128 px", "128 Pixel Resolution"),
            ("256", "256 px", "256 Pixel Resolution"),
            ("512", "512 px", "512 Pixel Resolution"),
            ("1024", "1024 px", "1024 Pixel Resolution"),
            ("2048", "2048 px", "2048 Pixel Resolution")
        ),
        default="128",
        update=update_shadow_resolution
    )

    use_temperature = bpy.props.BoolProperty(
        name="Use Color Temperature",
        default=True,
        description="Whether to set the lights color via a color temperature",
        update=update_color_temperature
    )

    color_temperature = bpy.props.FloatProperty(
        name="Color Temperature",
        description="Color teperature of the light in Kelvin",
        default=6500.0,
        precision=0,
        step=500,
        min=1400.0, max=25000.0,
        update=update_color_temperature
    )

    color_preview = bpy.props.FloatVectorProperty(
        name="Color Preview",
        description="Color preview of the temperature",
        subtype="COLOR",
        size=3,
        default=(1, 1, 1),
        min=0.0, max=1.0,
        set=None,
        get=get_temperature_color_preview
    )

    sphere_radius = bpy.props.FloatProperty(
        name="Sphere Radius",
        default=1.0,
        description="Spherical Area Light Sphere radius",
        min=0.05,
        max=100.0
    )


def register():
    bpy.utils.register_class(OperatorSetDefaultTextures)
    bpy.utils.register_class(OperatorFixLampTypes)
    bpy.utils.register_class(PBSMatProps)
    bpy.utils.register_class(PBSLampProps)
    bpy.utils.register_class(PBSMaterial)
    bpy.utils.register_class(PBSDataPanel)

    bpy.types.Material.pbepbs = bpy.props.PointerProperty(type=PBSMatProps)
    bpy.types.Lamp.pbepbs = bpy.props.PointerProperty(type=PBSLampProps)


def unregister():
    del bpy.types.Material.pbepbs
    bpy.utils.unregister_class(OperatorSetDefaultTextures)
    bpy.utils.unregister_class(OperatorFixLampTypes)
    bpy.utils.unregister_class(PBSMatProps)
    bpy.utils.unregister_class(PBSLampProps)
    bpy.utils.unregister_class(PBSMaterial)
    bpy.utils.unregister_class(PBSDataPanel)
