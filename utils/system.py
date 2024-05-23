import bpy
import os
import sys
import re
import json
from pprint import pprint
from tempfile import gettempdir
from shutil import rmtree
from . registration import get_prefs
from .. import bl_info

enc = sys.getfilesystemencoding()

def abspath(path):
    return os.path.abspath(bpy.path.abspath(path))

def quotepath(path):
    if " " in path:
        path = '"%s"' % (path)
    return path

def add_path_to_recent_files(path):
    try:
        recent_path = bpy.utils.user_resource('CONFIG', path="recent-files.txt")
        with open(recent_path, "r+", encoding=enc) as f:
            content = f.read()
            f.seek(0, 0)
            f.write(path.rstrip('\r\n') + '\n' + content)

    except (IOError, OSError, FileNotFoundError):
        pass

def get_next_files(filepath, next=True, debug=False):
    current_dir = os.path.dirname(filepath)
    current_file = os.path.basename(filepath)

    blend_files = sorted([f for f in os.listdir(current_dir) if os.path.splitext(f)[1].startswith('.blend')])

    current_idx = blend_files.index(current_file)

    if debug:
        print()
        print("files:")

        for idx, file in enumerate(blend_files):
            if idx == current_idx:
                print(" >", file)
            else:
                print("  ", file)

    next_file = None
    next_backup_file = None

    if next:
        next_blend_files = blend_files[current_idx + 1:]

    else:
        next_blend_files = blend_files[:current_idx]
        next_blend_files.reverse()

    if debug:
        print()
        nextstr = 'next' if next else 'previous'
        print(f"{nextstr} files:")

    for file in next_blend_files:
        if debug:
            print(" ", file)

        ext = os.path.splitext(file)[1]

        if next_file is None and ext== '.blend':
            next_file = file

        if next_backup_file is None and ext.startswith('.blend'):
            next_backup_file = file

        if next_file and next_backup_file:
            break

    if debug:
        print()
        print(f"{nextstr} file:", next_file)
        print(f"{nextstr} file (incl. backups):", next_backup_file)

    return current_dir, next_file, next_backup_file

def get_temp_dir(context):
    temp_dir = context.preferences.filepaths.temporary_directory
    
    if not temp_dir:
        temp_dir = gettempdir()

    return temp_dir

def open_folder(path):
    import platform
    import subprocess

    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        os.system('xdg-open "%s" %s &' % (path, "> /dev/null 2> /dev/null"))  # > sends stdout,  2> sends stderr

def makedir(pathstring):
    if not os.path.exists(pathstring):
        os.makedirs(pathstring)
    return pathstring

def get_incremented_paths(currentblend):
    path = os.path.dirname(currentblend)
    filename = os.path.basename(currentblend)

    filenameRegex = re.compile(r"(.+)\.blend\d*$")

    mo = filenameRegex.match(filename)

    if mo:
        name = mo.group(1)
        numberendRegex = re.compile(r"(.*?)(\d+)$")

        mo = numberendRegex.match(name)

        if mo:
            basename = mo.group(1)
            numberstr = mo.group(2)
        else:
            basename = name + "_"
            numberstr = "000"

        number = int(numberstr)

        incr = number + 1
        incrstr = str(incr).zfill(len(numberstr))
        incrname = basename + incrstr + ".blend"

        return os.path.join(path, incrname), os.path.join(path, name + '_01.blend')

def remove_folder(path):
    if (exists := os.path.exists(path)) and (isfolder := os.path.isdir(path)):
        try:
            rmtree(path)
            return True

        except Exception as e:
            print(f"WARNING: Error while trying to remove {path}: {e}")

    elif exists:
        print(f"WARNING: Couldn't remove {path}, it's not a folder!")
    else:
        print(f"WARNING: Couldn't remove {path}, it doesn't exist!")

    return False

def load_json(pathstring):
    try:
        with open(pathstring, 'r') as f:
            jsondict = json.load(f)
        return jsondict
    except json.decoder.JSONDecodeError:
        return False

def save_json(jsondict, pathstring):
    try:
        with open(pathstring, 'w') as f:
            json.dump(jsondict, f, indent=4)

    except PermissionError:
        pass

def printd(d, name=''):
    print(f"\n{name}")
    pprint(d, sort_dicts=False)

update_files = None

def get_update_files(force=False):
    global update_files

    if update_files is None or force:
        update_files = []

        home_dir = os.path.expanduser('~')

        if os.path.exists(home_dir):
            download_dir = os.path.join(home_dir, 'Downloads')

            home_files = [(f, os.path.join(home_dir, f)) for f in os.listdir(home_dir) if f.startswith(bl_info['name']) and f.endswith('.zip')]
            dl_files = [(f, os.path.join(download_dir, f)) for f in os.listdir(download_dir) if f.startswith(bl_info['name']) and f.endswith('.zip')] if os.path.exists(download_dir) else []

            zip_files = home_files + dl_files

            for filename, path in zip_files:
                split = filename.split('_')

                if len(split) == 2:
                    tail = split[1].replace('.zip', '')
                    s = tail.split('.')

                    if len(s) >= 3:
                        try:
                            version = tuple(int(v) for v in s[:3])

                        except:
                            continue

                        if tail == '.'.join(str(v) for v in bl_info['version']):
                            continue

                        update_files.append((path, tail, version))

        update_files = sorted(update_files, key=lambda x: (x[2], x[1]))

    return update_files

def get_bl_info_from_file(path):
    if os.path.exists(path):
        lines = ""
        
        with open(path) as f:
            for line in f:
                if line := line.strip():
                    lines += (line)
                else:
                    break

        try:
            blinfo = eval(lines.replace('bl_info = ', ''))

        except:
            print(f"WARNING: failed reading bl_info from {path}")
            return

        if 'name' in blinfo and 'version' in blinfo:
            name = blinfo['name']
            version = blinfo['version']

            if name == bl_info['name']:
                if version != bl_info['version']:
                    return blinfo

                else:
                    print(f"WARNING: Versions are identical, an update would be pointless")

            else:
                print(f"WARNING: Addon Mismatch, you can't update {bl_info['name']} to {name}")

    else:
        print(f"WARNING: failed reading bl_info from {path}, path does not exist")

def verify_update():
    path = get_prefs().path
    update_path = os.path.join(path, '_update')

    if os.path.exists(update_path):
        init_path = os.path.join(update_path, bl_info['name'], 'icon.py')

        blinfo = get_bl_info_from_file(init_path)

        if blinfo:
            get_prefs().update_msg = f"{blinfo['name']} {'.'.join(str(v) for v in blinfo['version'])} is ready to be installed."
            get_prefs().show_update = True

        else:
            remove_folder(update_path)

def install_update():
    path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    update_path = os.path.join(path, '_update')

    if os.path.exists(update_path):
        src = os.path.join(update_path, bl_info['name'])

        if os.path.exists(src):
            
            dst = os.path.join(os.path.dirname(path), f"_update_{bl_info['name']}")

            if os.path.exists(dst):
                remove_folder(dst)
            
            os.rename(src, dst)

            remove_folder(path)

            os.rename(dst, path)
