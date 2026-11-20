import bpy, json
from pathlib import Path

rig = bpy.data.objects.get("CrimsonWingedDragon_Rig")
scene = bpy.context.scene
out = {}
for action_name, frame in (("Land", 120), ("Fly", 1)):
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    out[action_name] = {
        bone.name: {
            "head": list(rig.matrix_world @ bone.head),
            "tail": list(rig.matrix_world @ bone.tail),
            "quat": list(bone.rotation_quaternion),
        }
        for bone in rig.pose.bones
        if bone.name.startswith(("Wing.", "Leg_", "Body_"))
    }
Path(bpy.path.abspath("//debug_pose_endpoints.json")).write_text(json.dumps(out, indent=2))
print("POSE_ENDPOINTS", json.dumps({k: {n: v for n, v in values.items() if n.startswith("Wing.")} for k, values in out.items()}))
