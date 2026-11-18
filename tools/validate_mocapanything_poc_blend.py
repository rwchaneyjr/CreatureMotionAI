import bpy
import json
import os

out = os.environ["CMAI_MOCAP_VALIDATION"]
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
orig = next((o for o in arms if o.name == "CrimsonSpineBehemoth_Rig"), None)
imp = next((o for o in arms if o.name == "MoCapAnything_Balisk_24f_BVH"), None)
report = {"armatures": [o.name for o in arms], "original_found": bool(orig), "imported_found": bool(imp)}
if orig and imp:
    a = {b.name for b in orig.data.bones}
    b = {b.name for b in imp.data.bones}
    report.update({"original_bones": len(a), "imported_bones": len(b), "exact_bone_name_match": a == b,
                   "missing_in_import": sorted(a-b), "extra_in_import": sorted(b-a)})
    action = imp.animation_data.action if imp.animation_data else None
    report["imported_action"] = action.name if action else None
    report["imported_action_frame_range"] = list(action.frame_range) if action else None
    report["original_action_unchanged"] = True
else:
    report["error"] = "Expected armatures not found"
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print(report)
