
def get_assetbrowser_area(context):
    if context.workspace:
        for screen in context.workspace.screens:
            for area in screen.areas:
                if area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS':
                    return area

def get_assetbrowser_space(area):
    for space in area.spaces:
        if space.type == 'FILE_BROWSER':
            return space

def get_3dview_area(context):
    if context.workspace:
        for screen in context.workspace.screens:
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    return area

    else:
        print("WARNING: context has no workspace attribute")

def get_3dview_space(area):
    for space in area.spaces:
        if space.type == 'VIEW_3D':
            return space

def get_window_region_from_area(area):
    for region in area.regions:
        if region.type == 'WINDOW':
            return region, region.data

def is_fullscreen(screen):
    return len(screen.areas) == 1 and 'nonnormal' in screen.name
