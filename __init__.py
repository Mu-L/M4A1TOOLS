
bl_info = {
    "name": "M4A1TOOLS",
    "author": "MACHIN3, TitusLVR, AIGODLIKE Community",
    "version": (2, 0, 5),
    "blender": (4, 0, 0),
    "location": "Everywhere",
    "description": "Based on the M3 tool, add more features to make Blender more user-friendly",
    "warning": "",
    "category": "3D View"}

def reload_modules(name):
    import os
    import importlib

    debug = False

    from . import registration, items, colors

    for module in [registration, items, colors]:
        importlib.reload(module)

    utils_modules = sorted([name[:-3] for name in os.listdir(os.path.join(__path__[0], "utils")) if name.endswith('.py')])

    for module in utils_modules:
        impline = f"from . utils import {module}"

        if debug:
            print(f"reloading {name}.utils.{module}")

        exec(impline)
        importlib.reload(eval(module))

    from . import handlers
    
    if debug:
        print("reloading", handlers.__name__)

    importlib.reload(handlers)

    modules = []

    for label in registration.classes:
        entries = registration.classes[label]
        for entry in entries:
            path = entry[0].split('.')
            module = path.pop(-1)

            if (path, module) not in modules:
                modules.append((path, module))

    for path, module in modules:
        if path:
            impline = f"from . {'.'.join(path)} import {module}"
        else:
            impline = f"from . import {module}"

        if debug:
            print(f"reloading {name}.{'.'.join(path)}.{module}")

        exec(impline)
        importlib.reload(eval(module))

if 'bpy' in locals():
    reload_modules(bl_info['name'])

import bpy
from bpy.props import PointerProperty, BoolProperty, EnumProperty
import os
from typing import Tuple
from . properties import M4SceneProperties, M4ObjectProperties
from . utils.registration import get_core, get_prefs, get_tools, get_pie_menus, get_path
from . utils.registration import register_classes, unregister_classes, register_keymaps, unregister_keymaps, register_icons, unregister_icons, register_msgbus, unregister_msgbus
from . utils.system import verify_update, install_update
from . ui.menus import asset_browser_bookmark_buttons, object_context_menu, mesh_context_menu, add_object_buttons, material_pick_button, outliner_group_toggles, extrude_menu, group_origin_adjustment_toggle, render_menu, render_buttons
from . handlers import load_post, undo_pre, depsgraph_update_post, render_start, render_end
from time import time
def update_check():
    def hook(resp, *args, **kwargs):
        if resp:
            if resp.text == 'true':
                get_prefs().update_available = True

            else:
                get_prefs().update_available = False

            if debug:
                print(" received response:", resp.text)

            write_update_check(update_path, time(), debug=debug)

    def init_update_check(debug=False):
        if debug:
            print()
            print("initiating update check for version", bl_info['version'])

        import platform
        import hashlib
        from . modules.requests_futures.sessions import FuturesSession

        machine = hashlib.sha1(platform.node().encode('utf-8')).hexdigest()[0:7]

        headers = {'User-Agent': f"{bl_info['name']}/{'.'.join([str(v) for v in bl_info.get('version')[:3]])} Blender/{'.'.join([str(v) for v in bpy.app.version])} ({platform.uname()[0]}; {platform.uname()[2]}; {platform.uname()[4]}; {machine})"}
        session = FuturesSession()

        try:
            if debug:
                print(" sending update request")

            session.post("https://drum.machin3.io/update", data={'revision': bl_info['revision']}, headers=headers, hooks={'response': hook})
        except:
            pass

    def write_update_check(update_path, update_time, debug=False):
        if debug:
            print()
            print("writing update check data")

        update_available = get_prefs().update_available

        msg = [f"version: {'.'.join(str(v) for v in bl_info['version'][:3])}",
               f"update time: {update_time}",
               f"update available: {update_available}\n"]

        with open(update_path, mode='w') as f:
            f.write('\n'.join(m for m in msg))

        if debug:
            print(" written to", update_path)

        return update_time, update_available

    def read_update_check(update_path, debug=False) -> Tuple[bool, tuple, float, bool]:
        if debug:
            print()
            print(f"reading {bl_info['name']} update check data")

        with open(update_path) as f:
            lines = [l[:-1] for l in f.readlines()]

        if len(lines) == 3:
            version_str = lines[0].replace('version: ', '')
            update_time_str = lines[1].replace('update time: ', '')
            update_available_str = lines[2].replace('update available: ', '')

            if debug:
                print(" fetched update available:", update_available_str)
                print(" fetched update time:", update_time_str)

            try:
                version = tuple(int(v) for v in version_str.split('.'))
            except:
                version = None

            try:
                update_time = float(update_time_str)
            except:
                update_time = None

            try:
                update_available = True if update_available_str == 'True' else False if update_available_str == 'False' else None
            except:
                update_available = None

            if version is not None and update_time is not None and update_available is not None:
                return True, version, update_time, update_available

        return False, None, None, None

    debug = False

    update_path = os.path.join(get_path(), 'update_check')

    if not os.path.exists(update_path):
        if debug:
            print(f"init {bl_info['name']} update check as file does not exist")

        init_update_check(debug=debug)

    else:
        valid, version, update_time, update_available = read_update_check(update_path, debug=debug)

        if valid:

            if debug:
                print(f" comparing stored {bl_info['name']} version:", version, "with bl_info['version']:", bl_info['version'][:3])

            if version != bl_info['version'][:3]:
                if debug:
                    print(f"init {bl_info['name']} update check, as the versions differ due to user updating the addon since the last update check")

                init_update_check(debug=debug)
                return

            now = time()
            delta_time = now - update_time

            if debug:
                print(" comparing", now, "and", update_time)
                print("  delta time:", delta_time)

            if delta_time > 72000:
                if debug:
                    print(f"init {bl_info['name']} update check, as it has been over 20 hours since the last one")

                init_update_check(debug=debug)
                return

            if debug:
                print(f"no {bl_info['name']} update check required, setting update available prefs from stored file")

            get_prefs().update_available = update_available

        else:
            if debug:
                print(f"init {bl_info['name']} update check as fetched file is invalid")

            init_update_check(debug=debug)

#中文翻译
class TranslationHelper():
    def __init__(self, name: str, data: dict, lang='zh_CN'):
        self.name = name
        self.translations_dict = dict()

        for src, src_trans in data.items():
            key = ("Operator", src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans
            key = ("*", src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans

    def register(self):
        try:
            bpy.app.translations.register(self.name, self.translations_dict)
        except(ValueError):
            pass

    def unregister(self):
        bpy.app.translations.unregister(self.name)

from . import zh_CN

M4A1_zh_CN = TranslationHelper('M4A1_zh_CN', zh_CN.data)
M4A1_zh_HANS = TranslationHelper('M4A1_zh_HANS', zh_CN.data, lang='zh_HANS')



def register():
    #翻译
    if bpy.app.version < (4, 0, 0):
        M4A1_zh_CN.register()
    else:
        M4A1_zh_CN.register()
        M4A1_zh_HANS.register()

    #插件
    global classes, keymaps, icons, owner

    core_classes = register_classes(get_core())

    bpy.types.Scene.M4 = PointerProperty(type=M4SceneProperties)
    bpy.types.Object.M4 = PointerProperty(type=M4ObjectProperties)

    bpy.types.WindowManager.M4_screen_cast = BoolProperty()
    bpy.types.WindowManager.M4_asset_catalogs = EnumProperty(items=[])

    tool_classlists, tool_keylists, tool_count = get_tools()
    pie_classlists, pie_keylists, pie_count = get_pie_menus()

    classes = register_classes(tool_classlists + pie_classlists) + core_classes
    keymaps = register_keymaps(tool_keylists + pie_keylists)
    #辣椒工具
    from .aigodlike_tool_reg import reg_and_update
    reg_and_update()


    #tool prop append
    bpy.types.VIEW3D_MT_object_context_menu.prepend(object_context_menu)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(mesh_context_menu)


    bpy.types.VIEW3D_MT_edit_mesh_extrude.append(extrude_menu)
    bpy.types.VIEW3D_MT_mesh_add.prepend(add_object_buttons)
    bpy.types.VIEW3D_MT_editor_menus.append(material_pick_button)
    bpy.types.ASSETBROWSER_MT_editor_menus.append(asset_browser_bookmark_buttons)
    bpy.types.OUTLINER_HT_header.prepend(outliner_group_toggles)

    bpy.types.VIEW3D_PT_tools_object_options_transform.append(group_origin_adjustment_toggle)

    bpy.types.TOPBAR_MT_render.append(render_menu)
    bpy.types.DATA_PT_context_light.prepend(render_buttons)

    icons = register_icons()

    owner = object()
    register_msgbus(owner)

    bpy.app.handlers.load_post.append(load_post)
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_post)

    bpy.app.handlers.render_init.append(render_start)
    bpy.app.handlers.render_cancel.append(render_end)
    bpy.app.handlers.render_complete.append(render_end)

    bpy.app.handlers.undo_pre.append(undo_pre)

    if get_prefs().registration_debug:
        print(f"Registered {bl_info['name']} {'.'.join([str(i) for i in bl_info['version']])} with {tool_count} {'tool' if tool_count == 1 else 'tools'}, {pie_count} pie {'menu' if pie_count == 1 else 'menus'}")

    update_check()

    verify_update()

def unregister():
    #翻译
    if bpy.app.version < (4, 0, 0):
        M4A1_zh_CN.unregister()
    else:
        M4A1_zh_CN.unregister()
        M4A1_zh_HANS.unregister()
    # 插件
    global classes, keymaps, icons, owner

    debug = get_prefs().registration_debug

    bpy.app.handlers.load_post.remove(load_post)

    from . handlers import axesHUD, focusHUD, surfaceslideHUD, screencastHUD

    if axesHUD and "RNA_HANDLE_REMOVED" not in str(axesHUD):
        bpy.types.SpaceView3D.draw_handler_remove(axesHUD, 'WINDOW')

    if focusHUD and "RNA_HANDLE_REMOVED" not in str(focusHUD):
        bpy.types.SpaceView3D.draw_handler_remove(focusHUD, 'WINDOW')

    if surfaceslideHUD and "RNA_HANDLE_REMOVED" not in str(surfaceslideHUD):
        bpy.types.SpaceView3D.draw_handler_remove(surfaceslideHUD, 'WINDOW')

    if screencastHUD and "RNA_HANDLE_REMOVED" not in str(screencastHUD):
        bpy.types.SpaceView3D.draw_handler_remove(screencastHUD, 'WINDOW')

    bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_post)

    bpy.app.handlers.render_init.remove(render_start)
    bpy.app.handlers.render_cancel.remove(render_end)
    bpy.app.handlers.render_complete.remove(render_end)

    bpy.app.handlers.undo_pre.remove(undo_pre)

    unregister_msgbus(owner)

    bpy.types.VIEW3D_MT_object_context_menu.remove(object_context_menu)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(mesh_context_menu)

#辣椒工具
    from .aigodlike_tool_reg import unreg_and_update
    unreg_and_update(True)


    bpy.types.VIEW3D_MT_edit_mesh_extrude.remove(extrude_menu)
    bpy.types.VIEW3D_MT_mesh_add.remove(add_object_buttons)
    bpy.types.VIEW3D_MT_editor_menus.remove(material_pick_button)
    bpy.types.ASSETBROWSER_MT_editor_menus.remove(asset_browser_bookmark_buttons)
    bpy.types.OUTLINER_HT_header.remove(outliner_group_toggles)

    bpy.types.VIEW3D_PT_tools_object_options_transform.remove(group_origin_adjustment_toggle)

    bpy.types.TOPBAR_MT_render.remove(render_menu)
    bpy.types.DATA_PT_context_light.remove(render_buttons)

    unregister_keymaps(keymaps)
    unregister_classes(classes)

    del bpy.types.Scene.M4
    del bpy.types.Object.M4

    del bpy.types.WindowManager.M4_screen_cast
    del bpy.types.WindowManager.M4_asset_catalogs

    unregister_icons(icons)

    if debug:
        print(f"Unregistered {bl_info['name']} {'.'.join([str(i) for i in bl_info['version']])}.")

    install_update()
