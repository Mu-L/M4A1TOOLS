import bpy
from typing import Tuple, Union
from mathutils import Matrix, Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_origin_3d, region_2d_to_vector_3d

def set_xray(context):
    x = (context.scene.M4.pass_through, context.scene.M4.show_edit_mesh_wire)
    shading = context.space_data.shading

    shading.show_xray = True if any(x) else False

    if context.scene.M4.show_edit_mesh_wire:
        shading.xray_alpha = 0.1

    elif context.scene.M4.pass_through:
        shading.xray_alpha = 1 if context.active_object and context.active_object.type == "MESH" else 0.5

def reset_xray(context):
    shading = context.space_data.shading

    shading.show_xray = False
    shading.xray_alpha = 0.5

def update_local_view(space_data, states):
    if space_data.local_view:
        for obj, local in states:
            if obj:
                obj.local_view_set(space_data, local)

def reset_viewport(context, disable_toolbar=False):
    for screen in context.workspace.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        r3d = space.region_3d

                        r3d.view_distance = 10
                        r3d.view_matrix = Matrix(((1, 0, 0, 0),
                                                  (0, 0.2, 1, -1),
                                                  (0, -1, 0.2, -10),
                                                  (0, 0, 0, 1)))

                        if disable_toolbar:
                            space.show_region_toolbar = False

def sync_light_visibility(scene):

    for view_layer in scene.view_layers:
        lights = [obj for obj in view_layer.objects if obj.type == 'LIGHT']

        for light in lights:
            hidden = light.hide_get(view_layer=view_layer)

            if light.hide_render != hidden:
                light.hide_render = hidden

def get_loc_2d(context, loc):
    loc_2d = location_3d_to_region_2d(context.region, context.region_data, loc)
    return loc_2d if loc_2d else Vector((-1000, -1000))

def get_view_origin_and_dir(context, coord=None) -> Tuple[Vector, Vector]:
    if not coord:
        coord = Vector((context.region.width / 2, context.region.height / 2))

    view_origin = region_2d_to_origin_3d(context.region, context.region_data, coord)
    view_dir = region_2d_to_vector_3d(context.region, context.region_data, coord)

    return view_origin, view_dir

def ensure_visibility(context, obj: Union[bpy.types.Object, list[bpy.types.Object]], unhide=True):
    view = context.space_data

    objects = obj if type(obj) in [list, set] else [obj]

    if view.local_view:
        for obj in objects:
            obj.local_view_set(view, True)

    if unhide:
        for obj in objects:
            if not obj.visible_get():
                obj.hide_set(False)

def get_location_2d(context, co3d, default=(0, 0), debug=False):
    co2d = Vector(round(i) for i in location_3d_to_region_2d(context.region, context.region_data, co3d, default=default))
    if debug:
        print(tuple(co3d), "is", tuple(co2d))

    return co2d
