import os
from os.path import dirname, join
from pathlib import Path

import bpy.utils.previews
previews_icons={}

thumbnail_suffix = ['.png', '.jpg']  # 缩略图后缀列表


def get_icon(name='None'):
    """
    load icon
    :param name:
    :return:
    """

    return previews_icons['ah'][name].icon_id


def preload_icons():
    """预加载图标，在启动 Blender 或启用插件时加载图标"""
    global previews_icons
    previews_icons['ah'] = bpy.utils.previews.new()  # 用于存所有的缩略图
    # 获取当前文件的目录路径
    folder_path = Path(__file__).parent

    # 遍历目录中的所有文件
    for file_path in folder_path.iterdir():
        if file_path.is_file() and file_path.suffix in thumbnail_suffix:
            # print('文件名',file_path.stem)
            previews_icons['ah'].load(
                file_path.stem,  # 使用文件名（无后缀）作为键名
                str(file_path),  # 转换为字符串路径以供 `load` 使用
                'IMAGE'
            )

def register():
    preload_icons()

def unregister():
    global previews_icons
    for pcoll in previews_icons.values():
        # print('对齐',pcoll)
        bpy.utils.previews.remove(pcoll)

    previews_icons.clear()
