import bpy
from .. utils.draw import draw_fading_label
from .. utils.ui import get_mouse_pos, warp_mouse, get_window_space_co2d
from .. utils.system import printd
from .. utils.registration import get_prefs
from .. utils.workspace import is_fullscreen
from .. utils.asset import get_asset_import_method, get_asset_library_reference, get_registered_library_references, set_asset_import_method, set_asset_library_reference
from .. colors import red, yellow, green

supress_assetbrowser_toggle = False

class ToggleVIEW3DRegion(bpy.types.Operator):
    bl_idname = "m4n1.toggle_view3d_region"
    bl_label = "M4N1: Toggle 3D View Region"
    bl_description = "Toggle 3D View Region based on Mouse Position"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        self.initiate_asset_browser_area_settings(context, debug=False)

        areas = self.get_areas(context, debug=False)

        regions = self.get_regions(context.area, debug=False)

        get_mouse_pos(self, context, event, hud=False)

        region_type = self.get_region_type_from_mouse(context, debug=False)

        area = self.toggle_region(context, areas, regions, region_type, debug=False)

        if area and get_prefs().region_warp_mouse_to_asset_border:
            self.warp_mouse_to_border(context, area, region_type)

        return {'FINISHED'}

    def get_areas(self, context, debug=False):
        active_area = context.area

        if debug:
            print()
            print("active area:", active_area.x, active_area.y, active_area.width, active_area.height)

        areas = {'TOP': None,
                 'BOTTOM': None,
                 'ACTIVE': active_area}

        for area in context.screen.areas:
            if area == active_area:
                continue
            else:
                if debug:
                    print(" ", area.type)
                    print("  ", area.x, area.y, area.width, area.height)

                if area.x == active_area.x and area.width == active_area.width:
                    location = 'BOTTOM' if area.y < active_area.y else 'TOP'

                    if debug:
                        print(f"   area is in the same 'column' and located at the {location}")

                    if areas[location]:
                        if location == 'BOTTOM' and area.y > areas[location].y:
                            areas[location] = area

                        elif location == 'TOP' and area.y < areas[location].y:
                            areas[location] = area

                    else:
                        areas[location] = area

        if debug:
            for location, area in areas.items():
                print(location)

                if area:
                    print("", area.type)

        return areas

    def get_regions(self, area, debug=False):
        regions = {}

        for region in area.regions:
            if region.type in ['TOOLS', 'TOOL_HEADER', 'TOOL_PROPS', 'UI', 'HUD', 'ASSET_SHELF', 'ASSET_SHELF_HEADER']:
                regions[region.type] = region

        if debug:
            printd(regions)

        return regions

    def get_region_type_from_mouse(self, context, debug=False):
        prefer_left_right = get_prefs().region_prefer_left_right
        close_range = get_prefs().region_close_range

        if context.region.type in ['WINDOW', 'HEADER', 'TOOL_HEADER']:
            area = context.area

            x_pct = (self.mouse_pos.x / area.width) * 100
            y_pct = (self.mouse_pos.y / area.height) * 100

            is_left = x_pct < 50
            is_bottom = y_pct < 50

            if prefer_left_right:
                side = 'LEFT' if is_left else 'RIGHT'

                if y_pct <= close_range:
                    side = 'BOTTOM'

                elif y_pct >= 100 - close_range:
                    side = 'TOP'

            else:
                side = 'BOTTOM' if is_bottom else 'TOP'

                if x_pct <= close_range:
                    side = 'LEFT'

                elif x_pct >= 100 - close_range:
                    side = 'RIGHT'

            if debug:

                print()
                print(f"side: {side}")

            if side == 'LEFT':
                return 'TOOLS'

            elif side == 'RIGHT':
                return 'UI'

            elif side == 'BOTTOM':
                return 'ASSET_BOTTOM'

            elif side == 'TOP':
                return 'ASSET_TOP'

        else:
            return context.region.type

    def get_asset_shelf(self, regions, debug=False):
        shelf = regions.get('ASSET_SHELF', None)
        header = regions.get('ASSET_SHELF_HEADER', None)

        if shelf and header:
            if debug:
                print()

            if header.height > 1:
                if debug:
                    print("asset shelf available!")

                if shelf.height > 1:
                    if debug:
                        print(" shelf is open")

                else:
                    if debug:
                        print(" shelf is collapsed")

                if debug:
                    print(" alignment:", shelf.alignment)

                return shelf

            else:
                if debug:
                    print("asset shelf not available!")

        else:
            if debug:
                print("asset shelf not supported in this Blender version")

    def is_close_area_of_type(self, area, area_type='ASSET_BROWSER'):  
        if area_type == 'ASSET_BROWSER':
            return area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS'

        else:
            return area.type == area_type

    def get_area_split_factor(self, context, total_height, stored_asset_browser_height, is_bottom, debug=False):
        if debug:
            print()
            print("total height:", total_height)
            print("  percentage:", stored_asset_browser_height / total_height)

        if is_bottom:
            if debug:
                print("bottom split")

            if context.preferences.system.ui_scale >= 2:
                if debug:
                    print(" big ui scale")

                if stored_asset_browser_height / total_height <= 0.12:
                    area_height = stored_asset_browser_height + 3

                    if debug:
                        print("  smaller than 37.5%, compensating with", 3, "pixels")

                elif stored_asset_browser_height / total_height <= 0.375:
                    area_height = stored_asset_browser_height + 2

                    if debug:
                        print("  smaller than 37.5%, compensating with", 2, "pixels")

                else:
                    area_height = stored_asset_browser_height + 1

                    if debug:
                        print("  bigger than 37.5% compensating with", 1, "pixels, capped at 45%")

            else:
                if debug:
                    print(" normal ui scale")

                if stored_asset_browser_height / total_height <= 0.25:
                    area_height = stored_asset_browser_height + 1

                    if debug:
                        print("  smaller than 25%, compensating with", 1, "pixels")

                else:
                    area_height = stored_asset_browser_height

                    if debug:
                        print("  using original height, capped at 45%")

        else:
            if context.preferences.system.ui_scale >= 2:
                if debug:
                    print(" big ui scale")

                if stored_asset_browser_height / total_height <= 0.12:
                    area_height = stored_asset_browser_height + 4

                    if debug:
                        print("  smaller than 12%, compensating with", 4, "pixels")

                elif stored_asset_browser_height / total_height <= 0.375:
                    area_height = stored_asset_browser_height + 3

                    if debug:
                        print("  smaller than 37.5%, compensating with", 3, "pixels")

                else:
                    area_height = stored_asset_browser_height + 2

                    if debug:
                        print("  bigger than 37.5% compensating with", 2, "pixels, capped at 45%")

            else:
                if debug:
                    print(" normal ui scale")

                if stored_asset_browser_height / total_height <= 0.25:
                    area_height = stored_asset_browser_height + 2

                    if debug:
                        print("  smaller than 25%, compensating with", 2, "pixels")

                else:
                    area_height = stored_asset_browser_height + 1

                    if debug:
                        print("  bigger than 25% compensating with", 1, "pixels, capped at 45%")

        area_split_factor = min(0.45, area_height / total_height)

        return area_split_factor, area_height 

    def warp_mouse_to_border(self, context, area, region_type):
        if area and region_type in ['ASSET_BOTTOM', 'ASSET_TOP']:
            mouse = get_window_space_co2d(context, self.mouse_pos)
            if region_type == 'ASSET_BOTTOM':
                mouse.y = area.y + area.height

            else:
                mouse.y = area.y

            warp_mouse(self, context, mouse, region=False)

    def initiate_asset_browser_area_settings(self, context, debug=False):
        if not context.scene.M4.get('asset_browser_prefs', False):
            context.scene.M4['asset_browser_prefs'] = {}

            if debug:
                print("initiating asset browser prefs on scene object")

        self.prefs = context.scene.M4.get('asset_browser_prefs')

        if context.screen.name not in self.prefs:
            if debug:
                print("initiating asset browser prefs for screen", context.screen.name)

            empty = {'area_height': 250,

                     'libref': 'ALL',
                     'catalog_id': '00000000-0000-0000-0000-000000000000',
                     'import_method': 'FOLLOW_PREFS',
                     'display_size': 96 if bpy.app.version >= (4, 0, 0) else 'SMALL',

                     'header_align': 'TOP',

                     'show_region_toolbar': True,
                     'show_region_tool_props': False,

                     'filter_search': '',
                     'filter_action': True,
                     'filter_group': True,
                     'filter_material': True,
                     'filter_node_tree': True,
                     'filter_object': True,
                     'filter_world': True,
                     }

            self.prefs[context.screen.name] = {'ASSET_TOP': empty,
                                               'ASSET_BOTTOM': empty.copy()}

        if debug:
            printd(self.prefs.to_dict())

    def store_asset_browser_area_settings(self, context, area, region_type, screen_name):
        for space in area.spaces:
            if space.type == 'FILE_BROWSER':
                if space.params:
                    libref = get_asset_library_reference(space.params)
                    import_method = get_asset_import_method(space.params)

                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['area_height'] = area.height

                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['libref'] = libref
                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['import_method'] = import_method
                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['catalog_id'] = space.params.catalog_id
                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['display_size'] = space.params.display_size

                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['show_region_toolbar'] = space.show_region_toolbar
                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['show_region_tool_props'] = space.show_region_tool_props

                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['filter_search'] = space.params.filter_search
                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['filter_action'] = space.params.filter_asset_id.filter_action
                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['filter_group'] = space.params.filter_asset_id.filter_group
                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['filter_material'] = space.params.filter_asset_id.filter_material
                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['filter_node_tree'] = space.params.filter_asset_id.filter_node_tree
                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['filter_object'] = space.params.filter_asset_id.filter_object
                    context.scene.M4['asset_browser_prefs'][screen_name][region_type]['filter_world'] = space.params.filter_asset_id.filter_world

        for region in area.regions:
            if region.type == 'HEADER':
                context.scene.M4['asset_browser_prefs'][screen_name][region_type]['header_align'] = region.alignment

    def apply_asset_browser_area_settings(self, context, area, space, params, screen_name, region_type):
        if screen_name in self.prefs:

            libref = self.prefs[screen_name][region_type]['libref']

            if libref in get_registered_library_references(context):
                import_method = self.prefs[screen_name][region_type]['import_method']
                catalog_id = self.prefs[screen_name][region_type]['catalog_id']
                display_size = self.prefs[screen_name][region_type]['display_size']

                if bpy.app.version >= (4, 0, 0) and isinstance(display_size, str):
                    print("WARNING: discovered legacy string value of asset browser display_size prop, resetting to size 96")
                    display_size = 96

                elif bpy.app.version < (4, 0, 0) and isinstance(display_size, int):
                    print("WARNING: discovered new string value of asset browser display_size prop, in legacy Blender version, resetting to size SMALL")
                    display_size = 'SMALL'

                show_region_toolbar = self.prefs[screen_name][region_type]['show_region_toolbar']
                show_region_tool_props = self.prefs[screen_name][region_type]['show_region_tool_props']

                filter_search = self.prefs[screen_name][region_type]['filter_search']
                filter_action = self.prefs[screen_name][region_type]['filter_action']
                filter_group = self.prefs[screen_name][region_type]['filter_group']
                filter_material = self.prefs[screen_name][region_type]['filter_material']
                filter_node_tree = self.prefs[screen_name][region_type]['filter_node_tree']
                filter_object = self.prefs[screen_name][region_type]['filter_object']
                filter_world = self.prefs[screen_name][region_type]['filter_world']

                set_asset_library_reference(params, libref)
                set_asset_import_method(params, import_method)
                params.catalog_id = catalog_id
                params.display_size = display_size

                space.show_region_toolbar = show_region_toolbar

                space.show_region_tool_props = show_region_tool_props

                params.filter_search = filter_search
                params.filter_asset_id.filter_action = filter_action
                params.filter_asset_id.filter_group = filter_group
                params.filter_asset_id.filter_material = filter_material
                params.filter_asset_id.filter_node_tree = filter_node_tree
                params.filter_asset_id.filter_object = filter_object
                params.filter_asset_id.filter_world = filter_world

                for region in area.regions:
                    if region.type == 'HEADER':
                        if region.alignment != self.prefs[screen_name][region_type]['header_align']:
                            with context.temp_override(area=area, region=region):
                                bpy.ops.screen.region_flip()

                return True

            return f"Library '{libref}' can not longer be found among registered asset libraries!"

        return f"Screen name '{screen_name}' can't be found in previously stored settings!"

    def toggle_region(self, context, areas, regions, region_type='TOOLS', debug=False):

        space = context.space_data
        region = regions[region_type] if region_type in regions else None
        screen_name = context.screen.name
        region_overlap = context.preferences.system.use_region_overlap

        toggle_asset_shelf = get_prefs().region_toggle_assetshelf
        toggle_asset_top = get_prefs().region_toggle_assetbrowser_top
        toggle_asset_bottom = get_prefs().region_toggle_assetbrowser_bottom

        scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

        if region_type == 'TOOLS':
            space.show_region_toolbar = not space.show_region_toolbar

        elif region_type == 'UI':
            space.show_region_ui = not space.show_region_ui

            if region:

                if (region_overlap and region.width == 1) or (not region_overlap and space.show_region_ui and region.width == 1):

                    text = ["Can't toggle the Sidebar",
                            "Insufficient View Space"]

                    draw_fading_label(context, text=text, y=100, center=True, size=12, color=red, alpha=1, time=1.2, delay=0.3, cancel='')

        elif region_type == 'HUD':
            space.show_region_hud = not space.show_region_hud

        elif region_type in ['ASSET_SHELF', 'ASSET_SHELF_HEADER']:
            space.show_region_asset_shelf = not space.show_region_asset_shelf

        elif region_type in ['ASSET_BOTTOM', 'ASSET_TOP']:

            shelf = self.get_asset_shelf(regions)

            if shelf and toggle_asset_shelf:

                if region_type == 'ASSET_BOTTOM' and shelf.alignment == 'BOTTOM' or region_type == 'ASSET_TOP' and shelf.alignment == 'TOP':
                    space.show_region_asset_shelf = not space.show_region_asset_shelf

                    return

            if is_fullscreen(context.screen):
                coords = (context.region.width / 2, 100 * scale if region_type == 'ASSET_BOTTOM' else context.region.height - 100 * scale)
                draw_fading_label(context, text="We can't Split this Area in Fullscreen ;(", y=100 if region_type == 'ASSET_BOTTOM' else context.region.height - 100, color=red, time=2)

            else:
                if region_type == 'ASSET_BOTTOM' and  toggle_asset_bottom or region_type == 'ASSET_TOP' and toggle_asset_top:
                    return self.toggle_area(context, areas, region_type, screen_name, scale)

    def toggle_area(self, context, areas, region_type, screen_name, scale):

        below_area_split = 'ASSET_BROWSER'
        top_area_split = 'ASSET_BROWSER'
        is_bottom = region_type == 'ASSET_BOTTOM'

        close_area = areas['BOTTOM' if is_bottom else 'TOP']

        if close_area and self.is_close_area_of_type(close_area, 'ASSET_BROWSER'):
            self.store_asset_browser_area_settings(context, close_area, region_type, screen_name)

            with context.temp_override(area=close_area):
                bpy.ops.screen.area_close()

        else:

            total_height = areas['ACTIVE'].height
            area_height = self.prefs[screen_name][region_type]['area_height']

            area_split_factor, _ = self.get_area_split_factor(context, total_height, area_height, is_bottom)

            global supress_assetbrowser_toggle

            if is_bottom:
                if self.mouse_pos.y <= area_height:
                    supress_assetbrowser_toggle = True

            else:
                if self.mouse_pos.y >= total_height - area_height:
                    supress_assetbrowser_toggle = True

            all_areas = [area for area in context.screen.areas]

            bpy.ops.screen.area_split(direction='HORIZONTAL', factor=area_split_factor if is_bottom else 1 - area_split_factor)

            new_areas = [area for area in context.screen.areas if area not in all_areas]

            if new_areas:
                new_area = new_areas[0]
                new_area.type = 'FILE_BROWSER'
                new_area.ui_type = 'ASSETS'

                for new_space in new_area.spaces:
                    if new_space.type == 'FILE_BROWSER':

                        if new_space.params:
                            ret = self.apply_asset_browser_area_settings(context, new_area, new_space, new_space.params, screen_name, region_type)

                            if ret is not True:
                                text = ["Couldn't apply asset browser settings"]
                                text.append(ret)

                                draw_fading_label(context, text=text, y=100 if region_type == 'ASSET_BOTTOM' else context.region.height - (80 + context.region.height * area_split_factor), color=[red, yellow])

                        else:

                            text = ["WARNING: Assetbrowser couldn't be set up yet, due to Blender shenanigans.",
                                    "This is normal on a new 3D View!",
                                    "TO FIX IT, DO THIS: Change THIS 3D View into an Asset browser, and back again",
                                    "Then save the blend file, for the change to stick"]

                            draw_fading_label(context, text=text, y=100 if region_type == 'ASSET_BOTTOM' else context.region.height - (200 + context.region.height * area_split_factor), color=[red, green, yellow])

                return new_area

class ToggleASSETBROWSERRegion(bpy.types.Operator):
    bl_idname = "m4n1.toggle_asset_browser_region"
    bl_label = "M4N1: Toggle Asset Browser Region"
    bl_description = "Toggle Asset Browser Region based on Mouse Position"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'FILE_BROWSER' and context.area.ui_type == 'ASSETS'

    def invoke(self, context, event):
        global supress_assetbrowser_toggle

        if supress_assetbrowser_toggle:
            supress_assetbrowser_toggle = False

            return {'CANCELLED'}

        ToggleVIEW3DRegion.initiate_asset_browser_area_settings(self, context, debug=False)

        areas = ToggleVIEW3DRegion.get_areas(self, context, debug=False)

        self.view3d_above =  areas['TOP'] if areas['TOP'] and areas['TOP'].type == 'VIEW_3D' else None
        self.view3d_below =  areas['BOTTOM'] if areas['BOTTOM'] and areas['BOTTOM'].type == 'VIEW_3D' else None

        can_close = bool(self.view3d_above or self.view3d_below)

        get_mouse_pos(self, context, event, hud=False)

        region_type = self.get_region_type_from_mouse(context, can_close, debug=False)

        self.toggle_region(context, areas, region_type, debug=False)

        return {'FINISHED'}

    def get_region_type_from_mouse(self, context, can_close, debug=False):
        close_range = get_prefs().region_close_range if can_close else 50

        if context.region.type in ['WINDOW', 'HEADER']:
            area = context.area
            region_width = 0

            for region in area.regions:
                if region.type == 'TOOLS':
                    if context.region.type == 'WINDOW':
                        region_width = region.width

                    break

            x_pct = ((self.mouse_pos.x + region_width)/ area.width) * 100

            if x_pct <= close_range:
                side = 'LEFT'

            elif x_pct >= 100 - close_range:
                side = 'RIGHT'

            else:
                side = 'CENTER'

            if debug:
                print()
                print("area width:", area.width)
                print("tools region width:", region_width)
                print("mouse pos, corrected:", self.mouse_pos.x + region_width)

                print()
                print("mouse.x in %", x_pct)

                print()
                print(f"side: {side}")

            if side == 'LEFT':
                return 'TOOLS'

            elif side == 'RIGHT':
                return 'TOOL_PROPS'

            elif side == 'CENTER':
                return 'CLOSE'

        else:
            return context.region.type

    def toggle_region(self, context, areas, region_type='TOOLS', debug=False):

        if region_type == 'CLOSE':

            area = areas['ACTIVE']
            region_type = 'ASSET_BOTTOM' if self.view3d_above else 'ASSET_TOP'
            screen_name = context.screen.name

            ToggleVIEW3DRegion.store_asset_browser_area_settings(self, context, area, region_type, screen_name)

            bpy.ops.screen.area_close()

        else:
            space = context.space_data

            if region_type == 'TOOLS':
                space.show_region_toolbar = not space.show_region_toolbar

            elif region_type == 'TOOL_PROPS':
                  space.show_region_tool_props = not space.show_region_tool_props

class ToggleSIDEBar(bpy.types.Operator):
    bl_idname = "m4n1.toggle_side_bar"
    bl_label = "M4N1: Toggle Toolbar or Sidebar (Any Region)"
    bl_description = "Toggle Toolbar or Sidebar (Any Region)"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type in ['NODE_EDITOR', 'IMAGE_EDITOR']

    def invoke(self, context, event):
        get_mouse_pos(self, context, event, hud=False)

        region_type = self.get_region_type_from_mouse(context, debug=False)

        self.toggle_region(context, region_type, debug=False)

        return {'FINISHED'}

    def get_region_type_from_mouse(self, context, debug=False):

        if context.region.type in ['WINDOW', 'HEADER']:
            area = context.area
            region_width = 0

            x_pct = ((self.mouse_pos.x + region_width)/ area.width) * 100

            if x_pct <= 50:
                side = 'LEFT'

            else:
                side = 'RIGHT'

            if debug:
                print()
                print("area width:", area.width)
                print("tools region width:", region_width)
                print("mouse pos, corrected:", self.mouse_pos.x + region_width)

                print()
                print("mouse.x in %", x_pct)

                print()
                print(f"side: {side}")

            if side == 'LEFT':
                return 'TOOLS'

            elif side == 'RIGHT':
                return 'UI'

        else:
            return context.region.type

    def toggle_region(self, context, region_type='TOOLS', debug=False):
        space = context.space_data

        if debug:
            print()
            print("toggling:", region_type)

        if region_type == 'TOOLS':
            space.show_region_toolbar = not space.show_region_toolbar

        elif region_type == 'UI':
            space.show_region_ui = not space.show_region_ui

class AreaDumper(bpy.types.Operator):
    bl_idname = "m4n1.area_dumper"
    bl_label = "M4N1: Area Dumper"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        print()
        print("spaces")

        for space in context.area.spaces:
            print("", space.type)

            if space.type == 'FILE_BROWSER':
                for d in dir(space):
                    print("", d, getattr(space, d))

                if space.params:
                    print()
                    print("params")

                    for d in dir(space.params):
                        print("", d, getattr(space.params, d))

        return {'FINISHED'}
