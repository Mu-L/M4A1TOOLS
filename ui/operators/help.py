import bpy
import os
import sys
import socket
from ... utils.registration import get_path, get_prefs
from ... utils.system import makedir, open_folder
from ... import bl_info

enc = sys.getdefaultencoding()

class GetSupport(bpy.types.Operator):
    bl_idname = "m4n1.get_m4n1tools_support"
    bl_label = "M4N1: Get M4N1tools Support"
    bl_description = "Generate Log Files and Instructions for a Support Request."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        logpath = makedir(os.path.join(get_path(), "logs"))
        resourcespath = makedir(os.path.join(get_path(), "resources"))

        is_url_open = bpy.app.version >= (4, 1, 0) or bpy.app.version < (3, 6, 0)

        sysinfopath = os.path.join(logpath, "system_info.txt")
        bpy.ops.wm.sysinfo(filepath=sysinfopath)

        self.extend_system_info(context, sysinfopath)

        src = os.path.join(resourcespath, "readme.html")
        readmepath = os.path.join(logpath, "readme.html")

        with open(src, "r") as f:
            html = f.read()

        html = html.replace("VERSION", ".".join((str(v) for v in bl_info['version'])))

        if is_url_open:
            folderurl = "file://" + logpath
            html = html.replace("FOLDER", f'<a href="{folderurl}">M4N1tools/logs</a>')

        else:
            html = html.replace("FOLDER", "M4N1tools/logs")

        with open(readmepath, "w") as f:
            f.write(html)

        if is_url_open:
            readmeurl = "file://" + readmepath
            bpy.ops.wm.url_open(url=readmeurl)

        open_folder(logpath)

        return {'FINISHED'}

    def extend_system_info(self, context, sysinfopath):
        if os.path.exists(sysinfopath):
            with open(sysinfopath, 'r+', encoding=enc) as f:
                lines = f.readlines()
                newlines = lines.copy()

                for line in lines:
                    if all(string in line for string in ['version:', 'branch:', 'hash:']):
                        idx = newlines.index(line)
                        newlines.pop(idx)
                        newlines.insert(idx, line.replace(', type:', f", revision: {bl_info['revision']}, type:"))

                    elif line.startswith('M4N1tools'):
                        idx = newlines.index(line)

                        new = []

                        prefs = get_prefs()

                        tools = []
                        pies = []

                        for p in dir(prefs):
                            if p.startswith('activate_'):
                                status = getattr(prefs, p, None)

                                if p.endswith('_pie'):
                                    name = p.replace('activate_', '').replace('_pie', '').title() + " Pie"
                                    pies.append((name, status))

                                else:
                                    name = p.replace('activate_', '').replace('_', ' ').title()

                                    if not 'Tools' in name:
                                        name += " Tool"

                                    tools.append((name, status))

                        new.append("Tools")

                        for tool, status in tools:
                            icon = "✔ " if status else "❌"

                            new.append(f"  {icon} {tool}")

                        new.append("")
                        new.append("Pies")

                        for pie, status in pies:
                            icon = "✔ " if status else "❌"

                            new.append(f"  {icon} {pie}")

                        for n in new:
                            idx += 1
                            newlines.insert(idx, f"  {n}\n")

                f.seek(0)
                f.writelines(newlines)
