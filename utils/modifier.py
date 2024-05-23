import bpy
from math import radians
from .. items import mirror_props

def add_triangulate(obj):
    mod = obj.modifiers.new(name="Triangulate", type="TRIANGULATE")
    mod.keep_custom_normals = True
    mod.quad_method = 'FIXED'
    mod.show_expanded = True
    return mod

def add_shrinkwrap(obj, target):
    mod = obj.modifiers.new(name="Shrinkwrap", type="SHRINKWRAP")

    mod.target = target
    mod.show_on_cage = True
    mod.show_expanded = False
    return mod

def add_surface_slide(obj, target):
    mod = add_shrinkwrap(obj, target)
    mod.name = 'Surface Slide'
    return mod

def add_mods_from_dict(obj, modsdict):
    for name, props in modsdict.items():
        mod = obj.modifiers.new(name=name, type=props['type'])

        for pname, pvalue in props.items():
            if pname != 'type':
                setattr(mod, pname, pvalue)

def add_bevel(obj, method='WEIGHT'):
    mod = obj.modifiers.new(name='Bevel', type='BEVEL')
    mod.limit_method = method

    mod.show_expanded = False
    return mod

def add_boolean(obj, operator, method='DIFFERENCE', solver='FAST'):
    boolean = obj.modifiers.new(name=method.title(), type="BOOLEAN")

    boolean.object = operator
    boolean.operation = 'DIFFERENCE' if method == 'SPLIT' else method
    boolean.show_in_editmode = True

    if method == 'SPLIT':
        boolean.show_viewport = False

    boolean.solver = solver

    return boolean

def add_auto_smooth(obj, angle=20):
    with bpy.context.temp_override(object=obj):
        bpy.ops.object.modifier_add_node_group(asset_library_type='ESSENTIALS', asset_library_identifier="", relative_asset_identifier="geometry_nodes/smooth_by_angle.blend/NodeTree/Smooth by Angle")

        mod = get_auto_smooth(obj)

        if mod:
            mod.show_expanded = False
            mod.name = "Auto Smooth"

            mod['Input_1'] = radians(angle)
            mod.node_group.interface_update(bpy.context)
            return mod

        elif (ng := bpy.data.node_groups.get('Smooth by Angle')) and (mods := [mod for mod in obj.modifiers if mod.type == 'NODES' and not mod.node_group]):
            print("WARNING: Blender says: 'Warning: Asset loading is unfinished' (probably)")
            print("         But empty geo node mod is present, and 'Smooth by Angle' node group is present in the file already too")

            mod = mods[0]
            mod.node_group = ng

            mod.show_expanded = False
            mod.name = "Auto Smooth"

            mod['Input_1'] = radians(angle)
            mod.node_group.interface_update(bpy.context)
            return mod

        else:
            print("WARNING: Blender says: 'Warning: Asset loading is unfinished' (probably)")
            ng = bpy.data.node_groups.get('Smooth by Angle')
            mods = [mod for mod in obj.modifiers if mod.type == 'NODES' and not mod.node_group]

            print("         node group:", ng)
            print("empty geo node mods:", mods)
            print("                     TODO!")

def get_auto_smooth(obj):
    if (mod := obj.modifiers.get('Auto Smooth', None)) and mod.type == 'NODES':
        return mod

    elif (mod := obj.modifiers.get('Smooth by Angle', None)) and mod.type == 'NODES':
        return mod
    
    else:
        mods = [mod for mod in obj.modifiers if mod.type == 'NODES' and (ng := mod.node_group) and ng.name.startswith('Smooth by Angle')]

        if mods:
            return mods[0]

def get_surface_slide(obj):
    mods = [mod for mod in obj.modifiers if mod.type == 'SHRINKWRAP' and 'SurfaceSlide' in mod.name]

    if mods:
        return mods[0]

def remove_mod(mod):
    obj = mod.id_data

    if isinstance(mod, bpy.types.Modifier):
        obj.modifiers.remove(mod)

    elif isinstance(mod, bpy.types.GpencilModifier):
        obj.grease_pencil_modifiers.remove(mod)

    else:
        print(f"WARNING: Could not remove modiifer {mod.name} of type {mod.type}")

def remove_triangulate(obj):
    lastmod = obj.modifiers[-1] if obj.modifiers else None

    if lastmod and lastmod.type == 'TRIANGULATE':
        obj.modifiers.remove(lastmod)
        return True

def get_mod_as_dict(mod, skip_show_expanded=False):
    d = {}

    if mod.type == 'MIRROR':
        for prop in mirror_props:
            if skip_show_expanded and prop == 'show_expanded':
                continue

            if prop in ['use_axis', 'use_bisect_axis', 'use_bisect_flip_axis']:
                d[prop] = tuple(getattr(mod, prop))
            else:
                d[prop] = getattr(mod, prop)

    return d

def get_mods_as_dict(obj, types=[], skip_show_expanded=False):
    mods = []

    for mod in obj.modifiers:
        if types:
            if mod.type in types:
                mods.append(mod)

        else:
            mods.append(mod)

    modsdict = {}

    for mod in mods:
        modsdict[mod.name] = get_mod_as_dict(mod, skip_show_expanded=skip_show_expanded)

    return modsdict

def apply_mod(modname):
    bpy.ops.object.modifier_apply(modifier=modname)

def get_mod_obj(mod):
    if mod.type in ['BOOLEAN', 'HOOK', 'LATTICE', 'DATA_TRANSFER', 'GP_MIRROR']:
        return mod.object
    elif mod.type == 'MIRROR':
        return mod.mirror_object
    elif mod.type == 'ARRAY':
        return mod.offset_object

def move_mod(mod, index=0):
    obj = mod.id_data
    current_index = list(obj.modifiers).index(mod)

    if current_index != index:
        obj.modifiers.move(current_index, index)

def sort_mod(mod):
    def is_mirror(mod):
        return mod.type == 'MIRROR'

    def is_array(mod):
        return mod.type == 'ARRAY'

    def is_auto_smooth(mod):
        return mod.type == 'NODES' and mod.node_group and 'Smooth by Angle' in mod.node_group.name

    def should_preceed(mod, prev_mod):
        if is_auto_smooth(mod):
            return any([is_mirror(prev_mod), is_array(prev_mod)])

    if is_auto_smooth(mod):
        obj = mod.id_data
        mods = list(obj.modifiers)

        if len(mods) > 1:

            move_mod(mod, len(mods) - 1)

            index = len(mods) - 1

            while index:
                index -= 1
                prev_mod = obj.modifiers[index]

                if should_preceed(mod, prev_mod):

                    if index == 0:
                        move_mod(mod, index)
                    continue

                else:
                    move_mod(mod, index + 1)
                    break
