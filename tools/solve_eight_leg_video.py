"""First-pass model-guided eight-legged video solver without DeepLabCut.

Uses silhouette bounds for global alignment and a configurable procedural gait
for the eight leg chains. IK targets stay on a ground plane during stance.
The result is intentionally a one-second diagnostic Action, not a claim of
full markerless anatomical reconstruction.
"""
import argparse, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector, Euler


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True); p.add_argument("--motion", required=True)
    p.add_argument("--output", required=True); p.add_argument("--report", required=True)
    p.add_argument("--stride", type=float, default=0.10); p.add_argument("--lift", type=float, default=0.07)
    p.add_argument("--phase-offset", type=float, default=0.55); p.add_argument("--body-amplitude", type=float, default=0.4)
    p.add_argument("--station-phase", default="0,0,0,0"); p.add_argument("--station-stride", default="1,1,1,1")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = p.parse_args(argv)
    station_phase = [float(x) for x in args.station_phase.split(",")]
    station_stride = [float(x) for x in args.station_stride.split(",")]
    root = Path(args.output).parent
    motion = json.loads(Path(args.motion).read_text(encoding="utf-8"))
    fps = float(motion.get("fps", 24.0))
    observations = motion.get("frames", [])[:24]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=args.model)
    rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    mesh = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    action = bpy.data.actions.new("CMAI_EightLeg_MP4_Solved")
    action.use_fake_user = True; rig.animation_data_create(); rig.animation_data.action = action
    # Four stations x two sides, matching the existing Balisk rig.
    leg_roots = [n for n in rig.data.bones.keys() if n.startswith("Leg_") and n.endswith("_01")]
    leg_roots.sort()
    targets = {}
    for name in leg_roots:
        target = bpy.data.objects.new("CMAI_IK_" + name, None); bpy.context.collection.objects.link(target)
        target.empty_display_type = "SPHERE"; target.empty_display_size = 0.04
        target.location = rig.matrix_world @ rig.data.bones[name].tail_local
        con = rig.pose.bones.get(name.replace("_01", "_03"))
        if con:
            ik = con.constraints.new("IK"); ik.name = "CMAI_FootContact_IK"; ik.target = target; ik.chain_count = 3
        targets[name] = target
    pose_names = [b.name for b in rig.pose.bones]
    for obs in observations:
        f = obs["frame"]; phase = (f - 1) / max(len(observations) - 1, 1)
        landmarks = obs.get("landmarks", {})
        leg_candidates = {item.get("station"): item for item in obs.get("leg_candidates", [])}
        center = landmarks.get("motion_center", [0.5, 0.5, 0.0])
        top = landmarks.get("motion_top", [0.5, 0.25, 0.0])[1]
        bottom = landmarks.get("motion_bottom", [0.5, 0.75, 0.0])[1]
        cx, cy = center[:2]; sx, sy = 0.5, max(bottom - top, 0.01)
        root_bone = rig.pose.bones.get("Root")
        body = rig.pose.bones.get("Body_02") or rig.pose.bones.get("Body_01")
        tail = rig.pose.bones.get("Tail_02")
        if root_bone:
            root_bone.location = ((0.5 - cx) * 0.35, 0, (cy - 0.5) * 0.18); root_bone.keyframe_insert("location", frame=f)
        if body:
            body.rotation_mode = "XYZ"; body.rotation_euler = Euler(((cy - 0.5) * args.body_amplitude, (cx - 0.5) * 0.3, (sx - 0.5) * 0.15), "XYZ"); body.keyframe_insert("rotation_euler", frame=f)
        if tail:
            tail.rotation_mode = "XYZ"; tail.rotation_euler.z = math.sin(phase * math.tau) * 0.12; tail.keyframe_insert("rotation_euler", frame=f)
        for index, name in enumerate(leg_roots):
            station = index // 2; side = index % 2
            gait = math.sin((phase * math.tau) + station * args.phase_offset + station_phase[station] + side * math.pi)
            target = targets[name]; base = rig.matrix_world @ rig.data.bones[name].tail_local
            # Fixed-foot stance: target remains low while swing phase lifts it.
            # Contact-aware interpolation: negative gait is stance (fixed
            # target); positive gait is swing, smoothly interpolated from the
            # contact position to the stride extreme and back.
            if gait <= 0.0:
                swing = 0.0
            else:
                t = min(1.0, gait)
                swing = t * t * (3.0 - 2.0 * t)
            candidate = leg_candidates.get(station, {})
            foot = candidate.get("foot")
            local_y = ((foot[0] - cx) * 0.18) if foot and candidate.get("confidence", 0) > 0.15 else 0.0
            local_z = ((0.65 - foot[1]) * 0.10) if foot and candidate.get("confidence", 0) > 0.15 else 0.0
            target.location = base + Vector((0, swing * args.stride * station_stride[station] + local_y, swing * args.lift + local_z))
            target.keyframe_insert("location", frame=f)
            leg_root_bone = rig.pose.bones.get(name); lower = rig.pose.bones.get(name.replace("_01", "_02"))
            if leg_root_bone:
                leg_root_bone.rotation_mode = "XYZ"; leg_root_bone.rotation_euler.y = gait * 0.22; leg_root_bone.keyframe_insert("rotation_euler", frame=f)
            if lower:
                lower.rotation_mode = "XYZ"; lower.rotation_euler.y = -max(0, gait) * 0.28; lower.keyframe_insert("rotation_euler", frame=f)
    scene = bpy.context.scene; scene.frame_start = 1; scene.frame_end = len(observations); scene.render.fps = int(round(fps))
    scene.render.engine = "BLENDER_WORKBENCH"; scene.render.resolution_x = 1280; scene.render.resolution_y = 720; scene.render.resolution_percentage = 50
    camera_data = bpy.data.cameras.new("CMAI_MP4_Side_Camera"); camera = bpy.data.objects.new("CMAI_MP4_Side_Camera", camera_data); bpy.context.collection.objects.link(camera)
    camera.location = (-2.2, 0, 0.45); camera.rotation_euler = (Vector((0,0,0))-camera.location).to_track_quat("-Z", "Y").to_euler(); camera_data.lens = 55; scene.camera = camera
    render_dir = root / "eight_leg_render"; render_dir.mkdir(exist_ok=True)
    for f in (1, 12, 24):
        if f <= len(observations): scene.frame_set(f); scene.render.filepath = str(render_dir / f"blender_{f:03d}.png"); bpy.ops.render.render(write_still=True)
    rig["cmai_solver"] = "opencv_silhouette_procedural_gait_ik"; rig["cmai_source_motion"] = str(Path(args.motion).resolve()); rig["cmai_existing_actions_used"] = False
    Path(args.report).write_text(json.dumps({"fps": fps, "frames": len(observations), "leg_ik_targets": len(targets), "render_dir": str(render_dir), "comparison_pending": True, "limitations": ["overlapping/hidden legs are not individually observable", "silhouette does not identify anatomical joints"]}, indent=2), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print(json.dumps({"output": args.output, "frames": len(observations), "ik_targets": len(targets)}))


if __name__ == "__main__": main()
