"""Read-only inspection of the three saved Balisk walk scenes."""
import json
import sys
from pathlib import Path

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
paths = [Path(item) for item in args]
rows = []
for path in paths:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    camera = scene.camera
    actions = []
    for obj in bpy.data.objects:
        animation = getattr(obj, "animation_data", None)
        if animation and animation.action:
            action = animation.action
            actions.append({"object": obj.name, "action": action.name,
                            "frame_range": list(action.frame_range),
                            "legacy_fcurve_count": (len(action.fcurves)
                                                    if hasattr(action, "fcurves") else None),
                            "layered": bool(getattr(action, "is_action_layered", False)),
                            "layers": [layer.name for layer in getattr(action, "layers", [])]})
    rows.append({
        "blend": str(path),
        "scene": scene.name,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "fps": scene.render.fps,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y,
                       scene.render.resolution_percentage],
        "camera": None if camera is None else {
            "name": camera.name,
            "type": camera.data.type,
            "lens": camera.data.lens,
            "ortho_scale": camera.data.ortho_scale,
            "location": list(camera.location),
            "rotation": list(camera.rotation_euler),
        },
        "armatures": [{"name": obj.name, "bone_count": len(obj.data.bones),
                       "location": list(obj.location), "scale": list(obj.scale)}
                      for obj in armatures],
        "actions": actions,
    })
print(json.dumps(rows, indent=2))
