from pathlib import Path
import json
import bpy

ROOT = Path(r"C:\Users\rober\CreatureMotionAI")
SRC = ROOT / "data" / "generated" / "original_static_standing.blend"
OUT = ROOT / "data" / "generated" / "cmai_balisk_pose_working.blend"
VIDEO = Path(r"C:\Users\rober\Downloads\SIDEbalaskWALK.mp4")
LIB = ROOT / "data" / "generated" / "cmai_pose_library.json"

if not SRC.is_file():
    raise FileNotFoundError(SRC)
bpy.ops.wm.open_mainfile(filepath=str(SRC))
scene = bpy.context.scene
scene["cmai_video"] = str(VIDEO)
scene["cmai_pose_library_data"] = str(LIB)
scene["cmai_project_root"] = str(ROOT)
scene["cmai_working_copy"] = True

if not LIB.exists():
    LIB.parent.mkdir(parents=True, exist_ok=True)
    LIB.write_text(json.dumps({"schema": "cmai_pose_library_v1", "observations": [], "approved_poses": []}, indent=2), encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print(json.dumps({"output": str(OUT), "video": str(VIDEO), "pose_library": str(LIB), "animation_generated": False}))
