import bpy

def adjust_lights_for_rendering(mode='DECREASE', debug=False):
    divider = bpy.context.scene.M4.adjust_lights_on_render_divider

    for light in bpy.data.lights:
        if light.type == 'AREA':

            if mode == 'DECREASE':
                if debug:
                    print("   ", light.name, light.energy, ' > ', light.energy / divider)

                light.energy /= divider

            elif mode == 'INCREASE':
                if debug:
                    print("   ", light.name, light.energy, ' > ', light.energy * divider)

                light.energy *= divider

def get_area_light_poll():
    return [obj for obj in bpy.data.objects if obj.type == 'LIGHT' and obj.data.type == 'AREA']
