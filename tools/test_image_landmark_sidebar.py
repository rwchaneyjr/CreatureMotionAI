"""Exercise the image landmark button through Blender's registered sidebar operator."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
import creature_motion_ai

creature_motion_ai.register()
operators = []


class Layout:
    def box(self): return self
    def row(self, **kwargs): return self
    def label(self, **kwargs): pass
    def prop(self, owner, name, **kwargs): assert hasattr(owner, name), name
    def operator(self, identifier, **kwargs):
        operators.append(identifier)
        return SimpleNamespace()


creature_motion_ai.reference_walk_ui.CMAI_PT_reference_walk.draw(
    SimpleNamespace(layout=Layout()), bpy.context)
assert "cmai.compare_image_landmarks" in operators
settings = bpy.context.scene.cmai_walk
settings.project_folder = str(root)
settings.external_python = str(root / ".venv-dlc/Scripts/python.exe")
settings.shared_manifest = sys.argv[-1]
scene_objects = tuple((o.name, o.type) for o in bpy.context.scene.objects)
actions = tuple(a.name for a in bpy.data.actions)
assert bpy.ops.cmai.compare_image_landmarks() == {"FINISHED"}
assert scene_objects == tuple((o.name, o.type) for o in bpy.context.scene.objects)
assert actions == tuple(a.name for a in bpy.data.actions)
result = json.loads(Path(settings.compare_report).read_text())
assert result["camera_alignment"]["fullbody_visible"]
assert result["camera_alignment"]["after"]["iou"] > result["camera_alignment"]["before"]["iou"]
assert result["optimization"]["status"] == "NOT_RUN"
print(json.dumps({"sidebar": "PASS", "camera_iou": result["camera_alignment"]["after"]["iou"],
                  "model_joints": len(result["projected_model_landmarks"]),
                  "verified_pairs": len(result["errors_px"]), "report": settings.compare_report}))
