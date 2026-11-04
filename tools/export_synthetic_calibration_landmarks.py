"""Export exact Blender camera matrices and projected same-frame rig landmarks."""
import argparse, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector


def camera_projection(cam, width, height):
    data = cam.data
    fx = data.lens / data.sensor_width * width
    fy = fx
    cx, cy = width / 2.0, height / 2.0
    K = [[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]]
    Rb = cam.matrix_world.to_3x3().transposed()
    R = [[float(Rb[0][0]), float(Rb[0][1]), float(Rb[0][2])],
         [-float(Rb[1][0]), -float(Rb[1][1]), -float(Rb[1][2])],
         [-float(Rb[2][0]), -float(Rb[2][1]), -float(Rb[2][2])]]
    c = cam.matrix_world.translation
    t = [-(R[0][0]*c.x + R[0][1]*c.y + R[0][2]*c.z),
         -(R[1][0]*c.x + R[1][1]*c.y + R[1][2]*c.z),
         -(R[2][0]*c.x + R[2][1]*c.y + R[2][2]*c.z)]
    P = [[sum(K[i][k] * (R[k][j] if j < 3 else t[k]) for k in range(3)) for j in range(4)] for i in range(3)]
    return {"location": list(c), "rotation_euler": list(cam.rotation_euler), "lens": data.lens, "sensor_width": data.sensor_width, "resolution": [width, height], "K": K, "R_world_to_camera": R, "t_world_to_camera": t, "projection_3x4": P}


def project(P, point):
    q = [sum(P[i][j] * (list(point) + [1.0])[j] for j in range(4)) for i in range(3)]
    if q[2] <= 1e-8:
        return None
    return {"x": q[0] / q[2], "y": q[1] / q[2], "visible": True, "confidence": 1.0, "state": "synthetic_projected"}


def main():
    p = argparse.ArgumentParser(); p.add_argument("--blend", required=True); p.add_argument("--calibration", required=True); p.add_argument("--observations", required=True); p.add_argument("--frames", type=int, default=240); argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:]; a = p.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    s = bpy.context.scene; rig = next(o for o in s.objects if o.type == "ARMATURE")
    if len(rig.data.bones) != 38: raise RuntimeError("Expected original 38-bone armature")
    cams = {"A_side": bpy.data.objects["CMAI_Synchronized_Side_Camera"], "B_front": bpy.data.objects["CMAI_Synchronized_Front_Camera"]}
    W, H = 640, 360
    cal = {"fps": 24, "panel_resolution": [W, H], "frames": a.frames, "source_blend": str(Path(a.blend).resolve()), "cameras": {k: camera_projection(v, W, H) for k, v in cams.items()}}
    joint_bones = {"body_center": ("Body_02", "head"), "head": ("Head_02", "head"), "tail_base": ("Tail_01", "head"), "tail_tip": ("Tail_08", "tail")}
    for i, station in enumerate(("Front", "MidFront", "MidRear", "Rear"), 1):
        for side in ("L", "R"):
            prefix=f"Leg_{station}.{side}"; joint_bones[f"{prefix}_hip"]=(prefix+"_01", "head"); joint_bones[f"{prefix}_knee"]=(prefix+"_02", "head"); joint_bones[f"{prefix}_ankle"]=(prefix+"_03", "head"); joint_bones[f"{prefix}_foot"]=(prefix+"_03", "tail")
    frames=[]
    for f in range(1, a.frames+1):
        s.frame_set(f); views={}
        for key, cam in cams.items():
            landmarks={}; P=cal["cameras"][key]["projection_3x4"]
            for name,(bone_name,part) in joint_bones.items():
                b=rig.pose.bones.get(bone_name); point=rig.matrix_world @ (b.head if part == "head" else b.tail) if b else None
                val=project(P, point) if point else None
                landmarks[name]=val or {"visible":False,"confidence":0.0,"state":"uncertain"}
            views[key.replace("A_side","camera_A").replace("B_front","camera_B")]={"landmarks":landmarks}
        frames.append({"frame":f, **views})
    Path(a.calibration).write_text(json.dumps(cal, indent=2), encoding="utf-8")
    Path(a.observations).write_text(json.dumps({"fps":24,"frame_count":a.frames,"panel_resolution":[W,H],"joint_names":list(joint_bones),"frames":frames,"status":"synthetic_projected_ground_truth","note":"Generated from the same Blender scene and Action; not real camera observations."}, indent=2), encoding="utf-8")
    print(json.dumps({"calibration":a.calibration,"observations":a.observations,"frames":len(frames),"joints":len(joint_bones)}))


if __name__ == "__main__": main()
