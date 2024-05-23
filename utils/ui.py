import bpy
import rna_keymap_ui
from mathutils import Vector
from bpy_extras.view3d_utils import region_2d_to_location_3d, location_3d_to_region_2d
from bl_ui.space_statusbar import STATUSBAR_HT_header as statusbar
from . registration import get_prefs
from time import time

icons = None

def get_icon(name):
    global icons

    if not icons:
        from .. import icons

    return icons[name].icon_id

def get_mouse_pos(self, context, event, hud=True, hud_offset=(20, 20)):
    self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

    if hud:
        scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

        self.HUD_x = self.mouse_pos.x + hud_offset[0] * scale
        self.HUD_y = self.mouse_pos.y + hud_offset[1] * scale

def wrap_mouse(self, context, x=False, y=False):
    width = context.region.width
    height = context.region.height

    mouse = self.mouse_pos.copy()

    if x:
        if mouse.x <= 0:
            mouse.x = width - 10

        elif mouse.x >= width - 1:  # the -1 is required for full screen, where the max region width is never passed
            mouse.x = 10

    if y and mouse == self.mouse_pos:
        if mouse.y <= 0:
            mouse.y = height - 10

        elif mouse.y >= height - 1:
            mouse.y = 10

    if mouse != self.mouse_pos:
        warp_mouse(self, context, mouse)

def warp_mouse(self, context, co2d=Vector(), region=True, hud_offset=(20, 20)):
    coords = get_window_space_co2d(context, co2d) if region else co2d

    context.window.cursor_warp(int(coords.x), int(coords.y))

    self.mouse_pos = co2d if region else get_region_space_co2d(context, co2d)

    if getattr(self, 'last_mouse', None):
        self.last_mouse = self.mouse_pos

    if getattr(self, 'HUD_x', None):
        scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

        self.HUD_x = self.mouse_pos.x + hud_offset[0] * scale
        self.HUD_y = self.mouse_pos.y + hud_offset[1] * scale

def get_window_space_co2d(context, co2d=Vector()):
    return co2d + Vector((context.region.x, context.region.y))

def get_region_space_co2d(context, co2d=Vector()):
    return Vector((context.region.x, context.region.y)) - co2d

def init_cursor(self, event, offsetx=0, offsety=20):
    self.last_mouse_x = event.mouse_x
    self.last_mouse_y = event.mouse_y

    self.region_offset_x = event.mouse_x - event.mouse_region_x
    self.region_offset_y = event.mouse_y - event.mouse_region_y

    self.HUD_x = event.mouse_x - self.region_offset_x + offsetx
    self.HUD_y = event.mouse_y - self.region_offset_y + offsety

def wrap_cursor(self, context, event, x=False, y=False):
    if x:

        if event.mouse_region_x <= 0:
            context.window.cursor_warp(context.region.width + self.region_offset_x - 10, event.mouse_y)

        if event.mouse_region_x >= context.region.width - 1:  # the -1 is required for full screen, where the max region width is never passed
            context.window.cursor_warp(self.region_offset_x + 10, event.mouse_y)

    if y:
        if event.mouse_region_y <= 0:
            context.window.cursor_warp(event.mouse_x, context.region.height + self.region_offset_y - 10)

        if event.mouse_region_y >= context.region.height - 1:
            context.window.cursor_warp(event.mouse_x, self.region_offset_y + 100)

def popup_message(message, title="Info", icon="INFO", terminal=True):
    def draw_message(self, context):
        if isinstance(message, list):
            for m in message:
                self.layout.label(text=m)
        else:
            self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw_message, title=title, icon=icon)

    if terminal:
        if icon == "FILE_TICK":
            icon = "ENABLE"
        elif icon == "CANCEL":
            icon = "DISABLE"
        print(icon, title)

        if isinstance(message, list):
            print(" »", ", ".join(message))
        else:
            print(" »", message)

def get_zoom_factor(context, depth_location, scale=10, ignore_obj_scale=False):
    center = Vector((context.region.width / 2, context.region.height / 2))
    offset = center + Vector((scale, 0))

    try:
        center_3d = region_2d_to_location_3d(context.region, context.region_data, center, depth_location)
        offset_3d = region_2d_to_location_3d(context.region, context.region_data, offset, depth_location)
    except:
        print("exception!")
        return 1

    if not ignore_obj_scale and context.active_object:
        mx = context.active_object.matrix_world.to_3x3()
        zoom_vector = mx.inverted_safe() @ Vector(((center_3d - offset_3d).length, 0, 0))
        return zoom_vector.length
    return (center_3d - offset_3d).length

def get_flick_direction(context, mouse_loc_3d, flick_vector, axes):
    origin_2d = location_3d_to_region_2d(context.region, context.region_data, mouse_loc_3d, default=Vector((context.region.width / 2, context.region.height / 2)))
    axes_2d = {}

    for direction, axis in axes.items():

        axis_2d = location_3d_to_region_2d(context.region, context.region_data, mouse_loc_3d + axis, default=origin_2d)
        if (axis_2d - origin_2d).length:
            axes_2d[direction] = (axis_2d - origin_2d).normalized()

    return min([(d, abs(flick_vector.xy.angle_signed(a))) for d, a in axes_2d.items()], key=lambda x: x[1])[0]

def kmi_to_string(kmi, docs_mode=False):
    kmi_str = f"{kmi.idname}, name: {kmi.name}, active: {kmi.active}, map type: {kmi.map_type}, type: {kmi.type}, value: {kmi.value}, alt: {kmi.alt}, ctrl: {kmi.ctrl}, shift: {kmi.shift}, properties: {str(dict(kmi.properties))}"

    if docs_mode:
        return f"`{kmi_str}`"
    else:
        return kmi_str

def draw_keymap_items(kc, name, keylist, layout):
    drawn = []

    idx = 0

    for item in keylist:
        keymap = item.get("keymap")
        isdrawn = False

        if keymap:
            km = kc.keymaps.get(keymap)

            kmi = None
            if km:
                idname = item.get("idname")

                for kmitem in km.keymap_items:
                    if kmitem.idname == idname:
                        properties = item.get("properties")

                        if properties:
                            if all([getattr(kmitem.properties, name, None) == value for name, value in properties]):
                                kmi = kmitem
                                break

                        else:
                            kmi = kmitem
                            break

            if kmi:
                if idx == 0:
                    box = layout.box()

                if len(keylist) == 1:
                    label = name.title().replace("_", " ")

                else:
                    if idx == 0:
                        box.label(text=name.title().replace("_", " "))

                    label = item.get("label")

                row = box.split(factor=0.25)
                row.label(text=label)

                rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, row, 0)

                infos = item.get("info", [])
                for text in infos:
                    row = box.split(factor=0.20)
                    row.separator()
                    row.label(text=text, icon="INFO")

                isdrawn = True
                idx += 1

        drawn.append(isdrawn)

    return any(d for d in drawn)

def get_keymap_item(name, idname, key=None, alt=False, ctrl=False, shift=False, properties=[]):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user

    km = kc.keymaps.get(name)

    if bpy.app.version >= (3, 0, 0):
        alt = int(alt)
        ctrl = int(ctrl)
        shift = int(shift)

    if km:
        kmi = km.keymap_items.get(idname)

        if kmi:
            found = True if key is None else all([kmi.type == key and kmi.alt is alt and kmi.ctrl is ctrl and kmi.shift is shift])

            if found:
                if properties:
                    if all([getattr(kmi.properties, name, False) == prop for name, prop in properties]):
                        return kmi
                else:
                    return kmi

def init_status(self, context, title='', func=None):
    self.bar_orig = statusbar.draw

    if func:
        statusbar.draw = func
    else:
        statusbar.draw = draw_basic_status(self, context, title)

def draw_basic_status(self, context, title):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text=title)

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finish")

        if context.window_manager.keyconfigs.active.name.startswith('blender'):
            row.label(text="", icon='MOUSE_MMB')
            row.label(text="Viewport")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

    return draw

def finish_status(self):
    statusbar.draw = self.bar_orig

def navigation_passthrough(event, alt=True, wheel=False) -> bool:

    if alt and wheel:
        return event.type in {'MIDDLEMOUSE'} or event.type.startswith('NDOF') or (event.alt and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'PRESS') or event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}
    elif alt:
        return event.type in {'MIDDLEMOUSE'} or event.type.startswith('NDOF') or (event.alt and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'PRESS')
    elif wheel:
        return event.type in {'MIDDLEMOUSE'} or event.type.startswith('NDOF') or event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}
    else:
        return event.type in {'MIDDLEMOUSE'} or event.type.startswith('NDOF')

def init_timer_modal(self, debug=False):
    self.start = time()

    self.countdown = self.time * get_prefs().modal_hud_timeout

    if debug:
        print(f"initiating timer with a countdown of {self.time}s ({self.time * get_prefs().modal_hud_timeout}s)")

def set_countdown(self, debug=False):
    self.countdown = self.time * get_prefs().modal_hud_timeout - (time() - self.start)

    if debug:
        print("countdown:", self.countdown)

def get_timer_progress(self, debug=False):
    progress =  self.countdown / (self.time * get_prefs().modal_hud_timeout)

    if debug:
        print("progress:", progress)

    return progress

def force_ui_update(context, active=None):
    if context.mode == 'OBJECT':
        if active:
            active.select_set(True)

        else:
            visible = context.visible_objects

            if visible:
                visible[0].select_set(visible[0].select_get())

    elif context.mode == 'EDIT_MESH':
        context.active_object.select_set(True)

def get_scale(context):
    return context.preferences.system.ui_scale * get_prefs().modal_hud_scale
