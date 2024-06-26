from . utils.math import tween

def mix(color1, color2, factor=0.5):
    r = tween(color1[0], color2[0], factor)
    g = tween(color1[1], color2[1], factor)
    b = tween(color1[2], color2[2], factor)

    return (r, g, b)

black = (0, 0, 0)
white = (1, 1, 1)
grey = (0.5, 0.5, 0.5)
red = (1, 0.25, 0.25)
green = (0.25, 1, 0.25)
blue = (0.2, 0.6, 1)
yellow = (1, 0.9, 0.2)
normal = (0.5, 0.5, 1)
orange = (1, 0.6, 0.2)
light_red = (1, 0.65, 0.65)
light_green = (0.75, 1, 0.75)

group_colors = [(0.65, 0.2, 0.04),
                (0.76, 0.47, 0.01),
                (0.3, 0.96, 0.21),
                (0.04, 0.48, 0.17),
                (0.05, 0.54, 0.95),
                (0.06, 0.21, 0.94),
                (0.23, 0.15, 0.66),
                (0.65, 0.12, 0.12),
                (0.11, 0.24, 0.09),
                (0.12, 0.25, 0.24),
                (0.05, 0.19, 0.26),
                (0.11, 0.16, 0.31),
                (0.05, 0.06, 0.11)]
