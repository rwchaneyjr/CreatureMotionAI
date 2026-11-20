"""Make a new fly-tuck variant: preserve front tuck, fold rear legs back.

Source is the already generated Fly Feet Tuck copy. The original FLAP action
is sampled for the two rear chains only; the source front pose and wing/body
motion remain unchanged. Writes a distinct .blend and JSON report.
"""
import argparse, json, math, sys
from pathlib import Path

import bpy

REAR = [f"Leg_Rear.{side}_{segment}" for side in ("L", "R") for segment in ("01", "02", "03")]
FRONT = [f"Leg_Front.{side}_{segment}" for side in ("L", "R") for segment in ("01", "02", "03")]

def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--name", default="Fly Feet Tuck Rear Fold Back")
    return p.parse_args(argv)

def assign(rig, action):
    rig.animation_data_create(); rig.animation_data.action = action
    slots = getattr(action, "slots", None)
    if slots and len(slots):
        try: rig.animation_data.action_slot = slots[0]
        except Exception: pass

def capture(rig, action, frame):
    assign(rig, action); bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
    objrot = rig.rotation_quaternion.copy() if rig.rotation_mode == "QUATERNION" else rig.rotation_euler.to_quaternion()
    return {
        "__object__": (rig.location.copy(), objrot, rig.scale.copy()),
        "bones": {b.name: (b.location.copy(), b.rotation_quaternion.copy(), b.scale.copy()) for b in rig.pose.bones},
    }

def main():
    a=args(); src=Path(a.source).resolve(); out=Path(a.output).resolve(); report_path=Path(a.report).resolve()
    if out.exists() or report_path.exists():
        raise FileExistsError("Refusing to overwrite the new Action variant or report")
    out.parent.mkdir(parents=True, exist_ok=True); report_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(src))
    rig=bpy.data.objects.get("CrimsonWingedDragon_Rig")
    if rig is None or rig.type != "ARMATURE" or len(rig.data.bones) != 47:
        raise RuntimeError("Expected original 47-bone dragon rig in the copied file")
    for n in FRONT+REAR:
        if n not in rig.pose.bones: raise RuntimeError(f"Missing leg bone {n}")
    if bpy.data.actions.get(a.name): raise RuntimeError(f"Action already exists: {a.name}")
    base=bpy.data.actions.get("Fly Feet Tuck"); flap=bpy.data.actions.get("FLAP")
    if base is None or flap is None: raise RuntimeError("Need existing Fly Feet Tuck and FLAP Actions")
    count=round(float(base.frame_range[1]-base.frame_range[0]))+1
    flap_start=int(flap.frame_range[0])
    if count > int(flap.frame_range[1]-flap.frame_range[0]+1):
        raise RuntimeError("Base duration exceeds FLAP source")

    new=bpy.data.actions.new(a.name); new.use_fake_user=True; new.slots.new(id_type="OBJECT", name=rig.name)
    assign(rig,new)
    for pb in rig.pose.bones: pb.rotation_mode="QUATERNION"
    rear_tailward=[]; front_max_rot_delta=0.0
    for i in range(count):
        f=i+1
        base_pose=capture(rig,base,int(base.frame_range[0])+i)
        rear_pose=capture(rig,flap,flap_start+i)
        assign(rig,new)
        for pb in rig.pose.bones:
            loc,rot,scale=base_pose["bones"][pb.name]
            if pb.name in REAR: loc,rot,scale=rear_pose["bones"][pb.name]
            pb.location=loc; pb.rotation_mode="QUATERNION"; pb.rotation_quaternion=rot; pb.scale=scale
        oloc, orot, oscale = base_pose["__object__"]
        rig.location=oloc; rig.rotation_mode="QUATERNION"; rig.rotation_quaternion=orot; rig.scale=oscale
        bpy.context.scene.frame_set(f); bpy.context.view_layer.update()
        # Verify front bones are unchanged from the prior Fly Feet Tuck action.
        for name in FRONT:
            q=rig.pose.bones[name].rotation_quaternion
            q0=base_pose["bones"][name][1]
            front_max_rot_delta=max(front_max_rot_delta, math.degrees(q.rotation_difference(q0).angle))
        # Signed rear foot displacement toward tail, using head-to-tail direction.
        head=rig.matrix_world@rig.pose.bones["Head_02"].tail
        tail=rig.matrix_world@rig.pose.bones["Tail_06"].tail
        tailward=(tail-head).normalized()
        for side in ("L","R"):
            hip=rig.matrix_world@rig.pose.bones[f"Leg_Rear.{side}_01"].head
            foot=rig.matrix_world@rig.pose.bones[f"Leg_Rear.{side}_03"].tail
            rear_tailward.append((foot-hip).dot(tailward))
        for pb in rig.pose.bones:
            pb.keyframe_insert("location",frame=f,group=pb.name)
            pb.keyframe_insert("rotation_quaternion",frame=f,group=pb.name)
            pb.keyframe_insert("scale",frame=f,group=pb.name)
        rig.keyframe_insert("location",frame=f,group="Armature Object")
        rig.keyframe_insert("rotation_quaternion",frame=f,group="Armature Object")
        rig.keyframe_insert("scale",frame=f,group="Armature Object")
    for layer in new.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points: key.interpolation="LINEAR"
    scene=bpy.context.scene; scene.frame_start=1; scene.frame_end=count; scene.render.fps=24
    assign(rig,new); scene.frame_set(1); bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    payload={
        "status":"NEW_REAR_FOLDBACK_ACTION_CREATED_VISUAL_REVIEW_REQUIRED",
        "source_blend":str(src),"output_blend":str(out),"action":new.name,
        "rig":rig.name,"bone_count":len(rig.data.bones),"frames":count,"fps":24,
        "front_legs":"Copied frame-for-frame from existing Fly Feet Tuck; max rotation delta during construction %.9f degrees."%front_max_rot_delta,
        "rear_legs":"Both 3-bone rear chains copied frame-for-frame from original FLAP Action, which folds them farther toward the tail than the tucked RUN sample.",
        "rear_foot_tailward_projection_units":{"minimum":min(rear_tailward),"maximum":max(rear_tailward),"mean":sum(rear_tailward)/len(rear_tailward)},
        "wings_body":"Copied frame-for-frame from existing Fly Feet Tuck (original FLAP timing retained).",
        "source_actions_preserved":True,"original_mesh_rest_pose_weights_hierarchy_modified":False,
        "motion_source_note":"Pose reuse from existing Actions, not video-driven per-frame mocap. Reference is used for visual direction only."
    }
    report_path.write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print(json.dumps(payload,indent=2))

if __name__=="__main__": main()
