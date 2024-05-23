import bpy
from mathutils import Vector
from . registration import get_addon
from . math import get_sca_matrix
from . mesh import get_bbox

decalmachine = None

def get_last_node(mat):
    if mat.use_nodes:
        tree = mat.node_tree
        output = tree.nodes.get("Material Output")
        if output:
            surf = output.inputs.get("Surface")
            if surf:
                if surf.links:
                    return surf.links[0].from_node

def lighten_color(color, amount):
    def remap(value, new_low):
        old_range = (1 - 0)
        new_range = (1 - new_low)
        return (((value - 0) * new_range) / old_range) + new_low

    return tuple(remap(c, amount) for c in color)

def adjust_bevel_shader(context, debug=False):

    global decalmachine

    if decalmachine is None:
        decalmachine = get_addon('DECALmachine')[0]

    if decalmachine:
        from DECALmachine.utils.material import get_decalgroup_from_decalmat, get_trimsheetgroup_from_trimsheetmat
    else:
        get_decalgroup_from_decalmat = get_trimsheetgroup_from_trimsheetmat = None

    m3 = context.scene.M4

    if debug:
        print("\nadjusting bevel shader")
        print("use bevel:", m3.use_bevel_shader)

    visible_objs = [obj for obj in context.visible_objects if obj.data and getattr(obj.data, 'materials', False) is not False and not any([obj.type == 'GPENCIL', obj.display_type in ['WIRE', 'BOUNDS'], obj.hide_render])]

    white_bevel = bpy.data.materials.get('white bevel')
    white_bevel_objs = []

    visible_mats = {white_bevel} if white_bevel else set()

    if debug:
        print("white bevel mat:", white_bevel)

    if debug:
        print("\nvisible objects")

    for obj in visible_objs:
        mats = [mat for mat in obj.data.materials if mat]

        if obj.data.materials and not mats:
            obj.data.materials.clear()

        if debug:
            print(obj.name, [mat.name for mat in mats])

        if m3.use_bevel_shader and not mats:
            if not white_bevel:
                if debug:
                    print(" creating new white bevel material")

                white_bevel = bpy.data.materials.new('white bevel')
                white_bevel.use_nodes = True

            if debug:
                print(" assigning white bevel material")

            obj.data.materials.append(white_bevel)
            mats.append(white_bevel)

        if obj.data.materials and obj.data.materials[0] == white_bevel:
            white_bevel_objs.append(obj)
        
        visible_mats.update(mats)
        
        if m3.use_bevel_shader:

            if decalmachine and obj.DM.decaltype == 'PANEL' and obj.parent:
                obj.M4.avoid_update = True
                obj.M4.bevel_shader_radius_mod = obj.parent.M4.bevel_shader_radius_mod

            if m3.bevel_shader_use_dimensions:

                if decalmachine and obj.DM.decaltype == 'PANEL' and obj.parent:
                    dimobj = obj.parent

                else:
                    dimobj = obj

                if dimobj.type == 'MESH':
                    
                    dims = Vector(get_bbox(dimobj.data)[2])

                    scalemx = get_sca_matrix(dimobj.matrix_world.to_scale())
                    
                    maxdim = (scalemx @ dims).length
                
                else:
                    maxdim = max(dimobj.dimensions)

                if debug:
                    print(" setting bevel dimensions to:", maxdim)

                obj.M4.bevel_shader_dimensions_mod = maxdim

            else:
                if debug:
                    print(" re-setting bevel dimensions")

                obj.M4.bevel_shader_dimensions_mod = 1

            obj.update_tag()

    if debug:
        print("\nvisible materials")

    for mat in visible_mats:
        if debug:
            print()
            print(mat.name)

        tree = mat.node_tree

        bevel = tree.nodes.get('M4N1tools Bevel')

        math = tree.nodes.get('M4N1tools Bevel Shader Radius Math')
        math2 = tree.nodes.get('M4N1tools Bevel Shader Radius Math2')
        math3 = tree.nodes.get('M4N1tools Bevel Shader Radius Math3')

        global_radius = tree.nodes.get('M4N1tools Bevel Shader Global Radius')

        obj_toggle = tree.nodes.get('M4N1tools Bevel Shader Object Toggle')
        obj_modulation = tree.nodes.get('M4N1tools Bevel Shader Object Radius Modulation')
        dim_modulation = tree.nodes.get('M4N1tools Bevel Shader Dimensions Radius Modulation')

        if debug:
            print(" bevel:", bevel)

            print(" math:", math)
            print(" math2:", math2)
            print(" math3:", math2)

            print(" global_radius:", global_radius)

            print(" obj_toggle:", obj_toggle)
            print(" obj_modulation:", obj_modulation)
            print(" dim_modulation:", dim_modulation)

        if not bevel:
            if debug:
                print()
                print(" no bevel node found")

            last_node = get_last_node(mat)

            if last_node:
                if debug:
                    print("  found last node", last_node.name)

                if last_node.type == 'BSDF_PRINCIPLED':
                    normal_inputs = [last_node.inputs[name] for name in ['Normal', 'Coat Normal'] if last_node.inputs.get(name) and not last_node.inputs[name].links]

                elif decalmachine and (mat.DM.isdecalmat or mat.DM.istrimsheetmat):

                    if mat.DM.isdecalmat and mat.DM.decaltype == 'PANEL':
                        normal_inputs = [last_node.inputs[f"{comp} {name}"] for name in ['Normal', 'Coat Normal'] for comp in ['Material', 'Material 2', 'Subset'] if last_node.inputs.get(f"{comp} {name}")]

                    elif mat.DM.istrimsheetmat:
                        normal_inputs = [last_node.inputs[name] for name in ['Normal', 'Coat Normal'] if last_node.inputs.get(name)]

                    else:
                        continue

                else:
                    normal_inputs = [last_node.inputs[name] for name in ['Normal', 'Coat Normal'] if last_node.inputs.get(name) and not last_node.inputs[name].links]

                if normal_inputs:
                    if debug:
                        print("   has a normal input without links, creating bevel node")

                    bevel, global_radius = create_and_connect_bevel_shader_setup(mat, last_node, normal_inputs, math, math2, math3, global_radius, obj_toggle, obj_modulation, dim_modulation, decalmachine=decalmachine, debug=debug)

                else:
                    continue

            else:
                continue

        if m3.use_bevel_shader:
            samples = bevel.samples
            radius = global_radius.outputs[0].default_value
            if samples != m3.bevel_shader_samples:
                if debug:
                    print(" setting bevel samples to:", m3.bevel_shader_samples)

                bevel.samples = m3.bevel_shader_samples

            if radius != m3.bevel_shader_radius:
                if debug:
                    print(" setting bevel radius to:", m3.bevel_shader_radius)
                
                bevel.inputs[0].default_value = m3.bevel_shader_radius
                global_radius.outputs[0].default_value = m3.bevel_shader_radius

        else:

            if mat == white_bevel:
                if debug:
                    print(" removing white bevel material")

                bpy.data.materials.remove(mat, do_unlink=True)
                
                for obj in white_bevel_objs:
                    obj.data.materials.clear()

                    if debug:
                        print("  clearing material slots on", obj.name)

            else:
                remove_bevel_shader_setup(mat, bevel, math, math2, math3, global_radius, obj_toggle, obj_modulation, dim_modulation, decalmachine, get_decalgroup_from_decalmat, get_trimsheetgroup_from_trimsheetmat, debug)

def create_and_connect_bevel_shader_setup(mat, last_node, normal_inputs, math=None, math2=None, math3=None, global_radius=None, obj_toggle=None, obj_modulation=None, dim_modulation=None, decalmachine=False, debug=False):
    tree = mat.node_tree
    
    bevel = tree.nodes.new('ShaderNodeBevel')
    bevel.name = "M4N1tools Bevel"
    bevel.location.x = last_node.location.x - 250

    y_dim = last_node.dimensions.y

    if y_dim == 0:
        y_dim = 660

        if 'trimsheet' in last_node.name:
            pass

        if decalmachine:
            if mat.DM.isdecalmat:
                if mat.DM.decaltype == 'PANEL':
                    y_dim = 963

    if decalmachine and mat.DM.istrimsheetmat:
        y_dim += 200

    bevel.location.y = last_node.location.y - y_dim + bevel.height

    for i in normal_inputs:
        tree.links.new(bevel.outputs[0], i)

    if not math:
        if debug:
            print("   creating multiply node")

        math = tree.nodes.new('ShaderNodeMath')
        math.name = "M4N1tools Bevel Shader Radius Math"
        math.operation = 'MULTIPLY'

        math.location = bevel.location
        math.location.x = bevel.location.x - 200

        tree.links.new(math.outputs[0], bevel.inputs[0])

    if not math2:
        if debug:
            print("   creating 2nd multiply node")

        math2 = tree.nodes.new('ShaderNodeMath')
        math2.name = "M4N1tools Bevel Shader Radius Math2"
        math2.operation = 'MULTIPLY'

        math2.location = math.location
        math2.location.x = math.location.x - 200

        tree.links.new(math2.outputs[0], math.inputs[0])

    if not math3:
        if debug:
            print("   creating 3rd multiply node")

        math3 = tree.nodes.new('ShaderNodeMath')
        math3.name = "M4N1tools Bevel Shader Radius Math3"
        math3.operation = 'MULTIPLY'

        math3.location = math2.location
        math3.location.x = math2.location.x - 200

        tree.links.new(math3.outputs[0], math2.inputs[0])

    if not global_radius:
        if debug:
            print("   creating global radius node")

        global_radius = tree.nodes.new('ShaderNodeValue')
        global_radius.name = "M4N1tools Bevel Shader Global Radius"
        global_radius.label = "Global Radius"

        global_radius.location = math3.location
        global_radius.location.x = math3.location.x - 200
        global_radius.location.y = math3.location.y

        tree.links.new(global_radius.outputs[0], math3.inputs[0])

    if not obj_toggle:
        if debug:
            print("   creating obj toggle node")

        obj_toggle = tree.nodes.new('ShaderNodeAttribute')
        obj_toggle.name = "M4N1tools Bevel Shader Object Toggle"
        obj_toggle.label = "Obj Toggle"

        obj_toggle.attribute_type = 'OBJECT'
        obj_toggle.attribute_name = 'M3.bevel_shader_toggle'

        obj_toggle.location = global_radius.location
        obj_toggle.location.y = global_radius.location.y - 100

        tree.links.new(obj_toggle.outputs[2], math3.inputs[1])

    if not obj_modulation:
        if debug:
            print("   creating obj modulation node")

        obj_modulation = tree.nodes.new('ShaderNodeAttribute')
        obj_modulation.name = "M4N1tools Bevel Shader Object Radius Modulation"
        obj_modulation.label = "Obj Radius Modulation"

        obj_modulation.attribute_type = 'OBJECT'
        obj_modulation.attribute_name = 'M3.bevel_shader_radius_mod'

        obj_modulation.location = math3.location
        obj_modulation.location.y = math3.location.y - 175

        tree.links.new(obj_modulation.outputs[2], math2.inputs[1])

    if not dim_modulation:
        if debug:
            print("   creating dimensions modulation node")

        dim_modulation = tree.nodes.new('ShaderNodeAttribute')
        dim_modulation.name = "M4N1tools Bevel Shader Dimensions Radius Modulation"
        dim_modulation.label = "Dimensions Radius Modulation"

        dim_modulation.attribute_type = 'OBJECT'
        dim_modulation.attribute_name = 'M3.bevel_shader_dimensions_mod'

        dim_modulation.location = math2.location
        dim_modulation.location.y = math2.location.y - 175

        tree.links.new(dim_modulation.outputs[2], math.inputs[1])

    return bevel, global_radius

def remove_bevel_shader_setup(mat, bevel=None, math=None, math2=None, math3=None, global_radius=None, obj_toggle=None, obj_modulation=None, dim_modulation=None, decalmachine=False, get_decalgroup_from_decalmat=None, get_trimsheetgroup_from_trimsheetmat=None, debug=False):
    tree = mat.node_tree

    if bevel:
        if debug:
            print(" removing bevel node")

        tree.nodes.remove(bevel)

    if math:
        if debug:
            print(" removing math node")

        tree.nodes.remove(math)

    if math2:
        if debug:
            print(" removing math2 node")

        tree.nodes.remove(math2)

    if math3:
        if debug:
            print(" removing math3 node")

        tree.nodes.remove(math3)

    if global_radius:
        if debug:
            print(" removing global radius node")

        tree.nodes.remove(global_radius)

    if obj_toggle:
        if debug:
            print(" removing obj toggle node")

        tree.nodes.remove(obj_toggle)

    if obj_modulation:
        if debug:
            print(" removing obj modulation node")

        tree.nodes.remove(obj_modulation)

    if dim_modulation:
        if debug:
            print(" removing dim modulation node")

        tree.nodes.remove(dim_modulation)

    if decalmachine and (mat.DM.isdecalmat or mat.DM.istrimsheetmat):

        if mat.DM.isdecalmat and mat.DM.decaltype == 'PANEL':
            detail_normal = tree.nodes.get('Detail Normal')
            dg = get_decalgroup_from_decalmat(mat)

            if detail_normal and dg:
                normal_inputs = [dg.inputs[f"{comp} Normal"] for comp in ['Material', 'Material 2', 'Subset']]

                for i in normal_inputs:
                    tree.links.new(detail_normal.outputs[0], i)

        elif mat.DM.istrimsheetmat:
            tiling_normal = tree.nodes.get('Tiling Normal')
            tsg = get_trimsheetgroup_from_trimsheetmat(mat)

            if tiling_normal and tsg:
                normal_inputs = [tsg.inputs[name] for name in ['Normal']]

                for i in normal_inputs:
                    tree.links.new(tiling_normal.outputs[0], i)

        else:
            pass
