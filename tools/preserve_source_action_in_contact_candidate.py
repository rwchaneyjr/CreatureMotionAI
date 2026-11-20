"""Restore the untouched baseline loop Action into the candidate copy."""
import bpy
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "data/generated/balisk_camera_fullbody_walk_02/balisk_seamless_loop.blend"
candidate = root / "data/generated/balisk_camera_fullbody_walk_02/contact_lock_v1/balisk_contact_locked.blend"
required = "CMAI_EightLeg_GroundFitted_reference_walk_refinement_04_SeamlessLoop"
if not bpy.data.actions.get(required):
    with bpy.data.libraries.load(str(source), link=False) as (data_from, data_to):
        if required not in data_from.actions:
            raise RuntimeError(f"Baseline Action not found in source: {required}")
        data_to.actions = [required]
if not bpy.data.actions.get(required):
    raise RuntimeError("Failed to append original baseline Action")
# It is intentionally not assigned to the armature; give it a fake user so
# Blender persists the preserved source Action in the candidate file.
bpy.data.actions[required].use_fake_user = True
bpy.ops.wm.save_as_mainfile(filepath=str(candidate))
print(f"PRESERVED_SOURCE_ACTION {required}", flush=True)
