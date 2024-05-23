from . tools import prettify_tool_name
from . system import printd
from . registration import get_addon_operator_idnames

addons = None

addon_abbr_mapping = {'M4N1tools': 'M3',
                      'DECALmachine': 'DM',
                      'MESHmachine': 'MM',
                      'CURVEmachine': 'CM',
                      'HyperCursor': 'HC',
                      'PUNCHit': 'PI'}

def get_last_operators(context, debug=False):
    def get_parent_addon(idname):
        if idname.startswith('hops.'):
            return 'HO'
        elif idname.startswith('bc.'):
            return 'BC'

        for name, idnames in addons.items():
            if idname in idnames:
                return addon_abbr_mapping[name]
        return None

    global addons

    if addons is None:
        addons = {}

        for addon in ['M4N1tools', 'DECALmachine', 'MESHmachine', 'CURVEmachine', 'HyperCursor', 'PUNCHit']:
            addons[addon] = get_addon_operator_idnames(addon)

        if debug:
            printd(addons)

    operators = []

    for op in context.window_manager.operators:
        idname = op.bl_idname.replace('_OT_', '.').lower()
        label = op.bl_label.replace('M4N1: ', '').replace('Macro', '').strip()
        addon = get_parent_addon(idname)
        prop = ''

        if idname.startswith('m4n1.call_'):
            continue

        elif idname == 'm4n1.set_tool_by_name':
            prop = prettify_tool_name(op.properties.get('name', ''))

        elif idname == 'm4n1.switch_workspace':
            prop = op.properties.get('name', '')

        elif idname == 'm4n1.switch_shading':
            toggled_overlays = getattr(op, 'toggled_overlays', False)
            prop = op.properties.get('shading_type', '').capitalize()

            if toggled_overlays:
                label = f"{toggled_overlays} Overlays"

        elif idname == 'm4n1.edit_mode':
            toggled_object = getattr(op, 'toggled_object', False)
            label = 'Object Mode' if toggled_object else 'Edit Mesh Mode'

        elif idname == 'm4n1.mesh_mode':
            shade_type = op.properties.get('mode', '')
            label = f"{shade_type.capitalize()} Mode"

        elif idname == 'm4n1.smart_vert':
            if op.properties.get('slideoverride', ''):
                prop = 'SideExtend'

            elif op.properties.get('vertbevel', False):
                prop = 'VertBevel'

            else:
                modeint = op.properties.get('mode')
                mergetypeint = op.properties.get('mergetype')
                mousemerge = getattr(op, 'mousemerge', False)

                shade_type = 'Merge' if modeint== 0 else 'Connect'
                mergetype = 'AtMouse' if mousemerge else 'AtLast' if mergetypeint == 0 else 'AtCenter' if mergetypeint == 1 else 'Paths'

                if shade_type == 'Merge':
                    prop = shade_type + mergetype
                else:
                    pathtype = getattr(op, 'pathtype', False)
                    prop = shade_type + 'Pathsby' + pathtype.title()

        elif idname == 'm4n1.transform_group':

            if op.is_setting_rest_pose:
                label = "Set Group's Rest Pose"
            elif op.is_recalling_rest_pose:
                label = "Recal Group's Rest Pose"
            else:
                pass

        elif idname == 'm4n1.set_group_pose':
            is_batch = getattr(op, 'batch')

            label = f"Set Group {'Batch ' if is_batch else ''}Pose"

        elif idname == 'm4n1.update_group_pose':
            is_batch = getattr(op, 'is_batch')

            label = f"Update Group's {'Batch ' if is_batch else ''}Pose"

            up = getattr(op, 'update_up', False)
            unlinked = getattr(op, 'update_unlinked', False)

            if up and unlinked:
                prop += 'Update Up and Unlinked too'
            elif up:
                prop += 'Update Up too'
            elif unlinked:
                prop += 'Update Unlinked too'

        elif idname == 'm4n1.retrieve_group_pose':
            is_batch = getattr(op, 'is_batch')

            label = f"Retrieve Group's {'Batch ' if is_batch else ''}Pose"

            up = getattr(op, 'retrieve_up', False)
            unlinked = getattr(op, 'retrieve_unlinked', False)

            if up and unlinked:
                prop += 'Retrieve Up and Unlinked too'
            elif up:
                prop += 'Retrieve Up too'
            elif unlinked:
                prop += 'Retrieve Unlinked too'

        elif idname == 'm4n1.remove_group_pose':
            is_batch = getattr(op, 'is_batch') and getattr(op, 'remove_batch')

            label = f"Remove Group's {'Batch ' if is_batch else ''}Pose"

            up = getattr(op, 'remove_up', False)
            unlinked = getattr(op, 'remove_unlinked', False)

            if up and unlinked:
                prop += 'Remove Up and Unlinked too'
            elif up:
                prop += 'Remove Up too'
            elif unlinked:
                prop += 'Remove Unlinked too'

        elif idname == 'm4n1.smart_edge':
            if op.properties.get('is_knife_project', False):
                prop = 'KnifeProject'

            elif op.properties.get('sharp', False):
                shade_type = getattr(op, 'sharp_mode')

                if shade_type == 'SHARPEN':
                    prop = 'ToggleSharp'
                elif shade_type == 'CHAMFER':
                    prop = 'ToggleChamfer'
                elif shade_type == 'KOREAN':
                    prop = 'ToggleKoreanBevel'

            elif op.properties.get('offset', False):
                prop = 'KoreanBevel'

            elif getattr(op, 'draw_bridge_props'):
                prop = 'Bridge'

            elif getattr(op, 'is_knife'):
                prop = 'Knife'

            elif getattr(op, 'is_connect'):
                prop = 'Connect'

            elif getattr(op, 'is_starconnect'):
                prop = 'StarConnect'

            elif getattr(op, 'is_select'):
                shade_type = getattr(op, 'select_mode')

                if getattr(op, 'is_region'):
                    prop = 'SelectRegion'
                else:
                    prop = f'Select{shade_type.title()}'

            elif getattr(op, 'is_loop_cut'):
                prop = 'LoopCut'

            elif getattr(op, 'is_turn'):
                prop = 'Turn'

        elif idname == 'm4n1.smart_face':
            shade_type = getattr(op, 'mode')

            if shade_type[0]:
                prop = "FaceFromVert"
            if shade_type[1]:
                prop = "FaceFromEdge"
            elif shade_type[2]:
                prop = "MeshFromFaces"

        elif idname == 'm4n1.focus':
            if op.properties.get('method', 0) == 1:
                prop = 'LocalView'

        elif idname == 'm4n1.mirror':
            removeall = getattr(op, 'removeall')

            if removeall:
                label = "Remove All Mirrors"

            else:
                axis = getattr(op, 'axis')
                remove = getattr(op, 'remove')

                if remove:
                    label = "Remove Mirror"

                    across = getattr(op, 'removeacross')
                    cursor = getattr(op, 'removecursor')

                else:
                    cursor = getattr(op, 'cursor')
                    across = getattr(op, 'across')

                if cursor:
                    prop = f'Cursor {axis}'
                elif across:
                    prop = f'Object {axis}'
                else:
                    prop = f'Local {axis}'

        elif idname == 'm4n1.shade':
            shade_type = getattr(op, 'shade_type')

            label = f"Shade {shade_type.title()}"

            incl_children = getattr(op, 'include_children')
            incl_boolean = getattr(op, 'include_boolean_objs')

            if shade_type == 'SMOOTH':
                sharpen = getattr(op, 'sharpen')

                if sharpen:
                    prop += '+Sharpen'

            elif shade_type == 'FLAT':
                clear = getattr(op, 'clear')

                if clear:
                    prop += '+Clear'

            if incl_children:
                prop += ' +incl Children'

            if incl_boolean:
                prop += ' +incl. Boolean'

            prop = prop.strip()

        elif idname == 'm4n1.purge_orphans':
            recursive = getattr(op, 'recursive')
            label = 'Purge Orphans Recursively' if recursive else 'Purge Orphans'

        elif idname == 'm4n1.select_hierarchy':
            direction = getattr(op, 'direction')
            label = f"Select Hiearchy {direction.title()}"

        elif idname == 'm4n1.assetbrowser_bookmark':
            shade_type = 'Save' if getattr(op, 'save_bookmark') else 'Clear' if getattr(op, 'clear_bookmark') else 'Jump to'

            label = f"{shade_type} Assetbrowser Bookmark"
            prop = str(getattr(op, 'index'))

        elif idname == 'm4n1.decal_library_visibility_preset':
            label = f"{label} {op.properties.get('name')}"
            prop = 'Store' if op.properties.get('store') else 'Recall'

        elif idname == 'm4n1.override_decal_materials':
            undo = getattr(op, 'undo')
            label = "Undo Material Override" if undo else "Material Override"

        elif idname == 'm4n1.select':
            if getattr(op, 'vgroup', False):
                prop = 'VertexGroup'
            elif getattr(op, 'faceloop', False):
                prop = 'FaceLoop'
            else:
                prop = 'Loop' if op.properties.get('loop', False) else 'Sharp'

        elif idname == 'm4n1.boolean':
            prop = getattr(op, 'method', False).capitalize()

        elif idname == 'm4n1.symmetrize':

            if getattr(op, 'remove'):
                prop = 'Remove'

            if getattr(op, 'partial'):
                label = 'Selected ' + label

        elif idname == 'm4n1.add_object_at_cursor':
            is_pipe_init = getattr(op, 'is_pipe_init', False)

            if is_pipe_init:
                label = 'Initiate Pipe Creation'

            else:
                objtype = getattr(op, 'type', False)
                label = f"Add {objtype.title()} at Cursor"

        elif idname == 'm4n1.transform_cursor':
            shade_type = getattr(op, 'mode', False).capitalize()
            is_array = getattr(op, 'is_array', False)
            is_macro = getattr(op, 'is_macro', False)
            is_duplicate = getattr(op, 'is_duplicate', False)

            if is_macro:
                geo = 'Mesh Selection' if context.mode == 'EDIT_MESH' else 'Object Selection'

                if is_duplicate:
                    label = f"Duplicate {shade_type} {geo}"

                else:
                    label = f"{shade_type} {geo}"

            elif is_array:

                if shade_type == 'Translate':
                    label = f"Linear Array"
                elif shade_type == 'Rotate':
                    label = f"Radial Array"

            else:
                label = f"{shade_type} Cursor"

        elif idname == 'm4n1.pick_hyper_bevel':
            mirror = getattr(op, 'mirror')

            if mirror:
                label = 'Mirror Hyper Bevel'
            else:
                label = 'Remove Hyper Bevel'

        elif idname == 'm4n1.point_cursor':
            align_y_axis = getattr(op, 'align_y_axis')
            label = 'Point Cursor'
            prop = 'Y' if align_y_axis else 'Z'

        elif idname == 'm4n1.hyper_cursor_object':
            hide_all = getattr(op, 'hide_all_visible_wire_objs')
            sort_modifiers = getattr(op, 'sort_modifiers')
            cycle_object_tree = getattr(op, 'cycle_object_tree')

            if hide_all:
                label = "Hide All Visible Wire Objects"
            elif sort_modifiers:
                label = "Sort Modifiers + Force Gizmo Update"
            elif cycle_object_tree:
                label = "Cycle Object Tree"

        operators.append((addon, label, idname, prop))

    if not operators:
        operators.append((None, 'Undo', 'ed.undo', ''))

    if debug:
        for addon, label, idname, prop in operators:
            print(addon, label, f"({idname})", prop)

    return operators
