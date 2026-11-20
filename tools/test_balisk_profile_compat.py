"""Ensure the reusable profile proposer still recognizes the Balisk test rig."""
import importlib.util
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import creature_motion_ai
creature_motion_ai.__path__.insert(0, str(ROOT / "creature_motion_ai"))

spec = importlib.util.spec_from_file_location(
    "creature_motion_ai.rig_profiles", ROOT / "creature_motion_ai" / "rig_profiles.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
from creature_motion_ai import anatomy_profile_ui as ui

arm = next((obj for obj in bpy.data.objects if obj.type == 'ARMATURE'), None)
if arm is None:
    raise RuntimeError("Balisk test file has no armature")
proposal = module.propose_anatomy_profile(arm)
if len(proposal["legs"]) != 8:
    raise AssertionError(f"Expected eight proposed Balisk leg chains, got {len(proposal['legs'])}")
ui.register()
ui.unregister()
print(f"BALISK_PROFILE_COMPAT_PASS armature={arm.name} legs={len(proposal['legs'])} bones={len(arm.data.bones)}")
