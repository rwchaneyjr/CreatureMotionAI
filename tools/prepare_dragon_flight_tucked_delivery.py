import bpy, os

target = os.path.abspath(r"data\generated\dragon_quadruped_compatibility\CrimsonWingedDragon_flight_tucked.blend")
rig = bpy.data.objects.get("CrimsonWingedDragon_Rig")
if rig is None or rig.animation_data is None:
    raise RuntimeError("Dragon rig with animation data is required")
action = bpy.data.actions.get("CMAI_Flight_Tucked_v3")
if action is None:
    raise RuntimeError("Validated tucked-flight candidate action is missing")
action.name = "CMAI_Flight_Tucked"
rig.animation_data.action = action
if hasattr(rig.animation_data, "action_slot") and len(action.slots):
    try: rig.animation_data.action_slot = action.slots[0]
    except Exception: pass
scene = bpy.context.scene
scene.render.fps = 24
scene.render.fps_base = 1.0
scene.frame_start = 1
scene.frame_end = 120
scene.frame_set(1)
os.makedirs(os.path.dirname(target), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=target)
print(f"FLIGHT_TUCK_DELIVERY_BLEND={target}; action={action.name}; duration={120/24:.3f}s")
