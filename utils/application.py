import bpy

def delay_execution(func, delay=0, persistent=False):
    if bpy.app.timers.is_registered(func):
        bpy.app.timers.unregister(func)

    bpy.app.timers.register(func, first_interval=delay, persistent=persistent)
