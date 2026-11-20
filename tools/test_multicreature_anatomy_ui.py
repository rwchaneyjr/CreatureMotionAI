"""Blender smoke test for the reusable anatomy profile UI and action analysis."""
import json
import importlib.util
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import creature_motion_ai
creature_motion_ai.__path__.insert(0, str(ROOT / "creature_motion_ai"))
profile_module_path = ROOT / "creature_motion_ai" / "rig_profiles.py"
spec = importlib.util.spec_from_file_location("creature_motion_ai.rig_profiles", profile_module_path)
profile_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = profile_module
spec.loader.exec_module(profile_module)
from creature_motion_ai import anatomy_profile_ui as ui

PROFILE_DIR = ROOT / "data" / "generated" / "dragon_quadruped_compatibility" / "cmai_anatomy_profiles"
profiles = sorted(PROFILE_DIR.glob("CrimsonWingedDragon_Rig_anatomy_*.json"))
PROFILE = profiles[-1] if profiles else Path()
if not PROFILE.is_file():
    raise RuntimeError(f"Confirmed dragon profile not found in {PROFILE_DIR}")

arm = bpy.data.objects.get("CrimsonWingedDragon_Rig")
if arm is None:
    arm = next((obj for obj in bpy.data.objects if obj.type == 'ARMATURE'), None)
if arm is None:
    raise RuntimeError("Dragon test armature not found")
ui.register()
p = bpy.context.scene.cmai_anatomy
p.armature = arm
p.profile_path = str(PROFILE)
p.profile_confirmed = True
p.action_name = "Move_Scissor_Offset"
p.workflow = 'EXISTING'
starting_action = arm.animation_data.action if arm.animation_data else None
starting_frame = bpy.context.scene.frame_current

check = bpy.ops.cmai.multi_creature_workflow_check()
assert check == {'FINISHED'}, check
analysis = bpy.ops.cmai.analyze_existing_action()
assert analysis == {'FINISHED'}, analysis
assert (arm.animation_data.action if arm.animation_data else None) is starting_action
assert bpy.context.scene.frame_current == starting_frame
report = json.loads(Path(bpy.path.abspath(p.report_path)).read_text(encoding="utf-8"))
assert report["action"] == "Move_Scissor_Offset"
assert report["action_modified"] is False
assert len(report["legs"]) == 4
assert all(item["evaluated_frames"] == 73 for item in report["legs"])
print("MULTICREATURE_UI_TEST_PASS", json.dumps({
    "workflow_check": "PASS", "action_analysis": "PASS",
    "profile_legs": len(report["legs"]), "frames": report["frame_range"],
    "report": p.report_path,
}, sort_keys=True))
