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
    p.add_argument("--leg-tracks", default="")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = p.parse_args(argv)
    station_phase = [float(x) for x in args.station_phase.split(",")]
    station_stride = [float(x) for x in args.station_stride.split(",")]
    leg_tracks = {}
    if args.leg_tracks:
        track_data = json.loads(Path(args.leg_tracks).read_text(encoding="utf-8"))
        leg_tracks = {item["frame"]: item.get("candidates", []) for item in track_data.get("frames", [])}
    root = Path(args.output).parent
    motion = json.loads(Path(args.motion).read_text(encoding="utf-8"))
    fps = float(motion.get("fps", 24.0))
    observations = motion.get("frames", [])[:24]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=args.model)
    bpy.context.scene.frame_set(1)
    rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    mesh = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    rig.show_in_front = True
    rig.data.display_type = "OCTAHEDRAL"
    rig.data.show_names = True
    mesh.show_wire = False
    mesh.show_all_edges = False
    mesh.display_type = "SOLID"
    for bone in rig.data.bones:
        try:
            if bone.name.startswith("Leg_"):
                bone.color.palette = "THEME04"  # orange/red leg chains
            elif bone.name.startswith("Tail_"):
                bone.color.palette = "THEME03"  # green tail
            else:
                bone.color.palette = "THEME01"  # blue body/head/root
        except AttributeError:
            pass
    rest_pose = {b.name: (b.location.copy(), b.rotation_mode, b.rotation_euler.copy(), b.rotation_quaternion.copy(), b.scale.copy()) for b in rig.pose.bones}
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    action = bpy.data.actions.new("CMAI_EightLeg_MP4_Solved")
    action.use_fake_user = True; rig.animation_data_create(); rig.animation_data.action = action
    # Four stations x two sides, matching the existing Balisk rig.
    leg_roots = [n for n in rig.data.bones.keys() if n.startswith("Leg_") and (n.endswith("_upper") or n.endswith("_01"))]
    leg_roots.sort()
    targets = {}
    poles = {}
    for name in leg_roots:
        target = bpy.data.objects.new("CMAI_IK_" + name, None); bpy.context.collection.objects.link(target)
        target.empty_display_type = "SPHERE"; target.empty_display_size = 0.04
        target.location = rig.matrix_world @ rig.data.bones[name].tail_local
        lower_name = name.replace("_upper", "_lower").replace("_01", "_02")
        ankle_name = name.replace("_upper", "_lower").replace("_01", "_03")
        con = rig.pose.bones.get(ankle_name)
        ik_active = con is not None
        if con:
            ik = con.constraints.new("IK"); ik.name = "CMAI_FootContact_IK"; ik.target = target; ik.chain_count = 2
            ik.influence = 0.0; ik.keyframe_insert("influence", frame=1)
            ik.influence = 1.0; ik.keyframe_insert("influence", frame=2)
            pole = bpy.data.objects.new("CMAI_Pole_" + name, None); bpy.context.collection.objects.link(pole)
            upper = rig.data.bones.get(name); lower = rig.data.bones.get(lower_name)
            if upper and lower:
                knee = (upper.tail_local + lower.tail_local) * 0.5
                pole.location = rig.matrix_world @ (knee + Vector((0.35 if ".L" in name else -0.35, 0.0, 0.25)))
                ik.pole_target = pole; ik.pole_angle = 0.0; poles[name] = pole
        targets[name] = target
    pose_names = [b.name for b in rig.pose.bones]
    for obs_index, obs in enumerate(observations):
        source_frame = obs["frame"]
        f = obs_index + 1
        phase = obs_index / max(len(observations) - 1, 1)
        is_rest_frame = obs_index == 0
        for bone in rig.pose.bones:
            loc, mode, euler, quat, scale = rest_pose[bone.name]
            bone.location = loc; bone.rotation_mode = mode; bone.rotation_euler = euler; bone.rotation_quaternion = quat; bone.scale = scale
        landmarks = obs.get("landmarks", {})
        leg_candidates = {item.get("station"): item for item in obs.get("leg_candidates", [])}
        center = landmarks.get("motion_center", [0.5, 0.5, 0.0])
        top = landmarks.get("motion_top", [0.5, 0.25, 0.0])[1]
        bottom = landmarks.get("motion_bottom", [0.5, 0.75, 0.0])[1]
        cx, cy = center[:2]; sx, sy = 0.5, max(bottom - top, 0.01)
        root_bone = rig.pose.bones.get("Root")
        body = rig.pose.bones.get("Body_02") or rig.pose.bones.get("Body_01")
        tail = rig.pose.bones.get("Tail_02")
        if root_bone and not is_rest_frame:
            root_bone.location = ((0.5 - cx) * 0.35, 0, (cy - 0.5) * 0.18); root_bone.keyframe_insert("location", frame=f)
        if body and not is_rest_frame:
            body.rotation_mode = "XYZ"; body.rotation_euler = Euler(((cy - 0.5) * args.body_amplitude, (cx - 0.5) * 0.3, (sx - 0.5) * 0.15), "XYZ"); body.keyframe_insert("rotation_euler", frame=f)
        if tail and not is_rest_frame:
            tail.rotation_mode = "XYZ"; tail.rotation_euler.z = math.sin(phase * math.tau) * 0.12; tail.keyframe_insert("rotation_euler", frame=f)
        for index, name in enumerate(leg_roots):
            station = index // 2; side = index % 2
            gait = math.sin((phase * math.tau) + station * args.phase_offset + station_phase[station] + side * math.pi)
            target = targets[name]; base = rig.matrix_world @ rig.data.bones[name].tail_local
            # Fixed-foot stance: target remains low while swing phase lifts it.
            # Contact-aware interpolation: negative gait is stance (fixed
            # target); positive gait is swing, smoothly interpolated from the
            # contact position to the stride extreme and back.
            if is_rest_frame:
                swing = 0.0
            elif gait <= 0.0:
                swing = 0.0
            else:
                t = min(1.0, gait)
                swing = t * t * (3.0 - 2.0 * t)
            tracked = leg_tracks.get(source_frame, [])
            candidate = next((item for item in tracked if item.get("leg") == index), {})
            if not candidate:
                candidate = leg_candidates.get(station, {})
            foot = candidate.get("foot")
            local_y = ((foot[0] - cx) * 0.18) if foot and candidate.get("confidence", 0) > 0.15 else 0.0
            local_z = ((0.65 - foot[1]) * 0.10) if foot and candidate.get("confidence", 0) > 0.15 else 0.0
            target.location = base + Vector((0, swing * args.stride * station_stride[station] + local_y, swing * args.lift + local_z))
            target.keyframe_insert("location", frame=f)
            leg_root_bone = rig.pose.bones.get(name)
            lower_name = name.replace("_upper", "_lower").replace("_01", "_02")
            lower = rig.pose.bones.get(lower_name)
            if leg_root_bone and not is_rest_frame:
                leg_root_bone.rotation_mode = "XYZ"; leg_root_bone.rotation_euler.y = gait * 0.22; leg_root_bone.keyframe_insert("rotation_euler", frame=f)
            # IK owns the upper/lower leg rotation. Do not also key the lower
            # bone, which previously caused the ankle/foot to flip upward.
            if lower and not is_rest_frame and not ik_active:
                lower.rotation_mode = "XYZ"; lower.rotation_euler.y = -max(0, gait) * 0.28; lower.keyframe_insert("rotation_euler", frame=f)
    scene = bpy.context.scene; scene.frame_start = 1; scene.frame_end = len(observations); scene.render.fps = int(round(fps))
    scene.render.engine = "BLENDER_WORKBENCH"; scene.render.resolution_x = 1280; scene.render.resolution_y = 720; scene.render.resolution_percentage = 50
    camera_data = bpy.data.cameras.new("CMAI_MP4_Side_Camera"); camera = bpy.data.objects.new("CMAI_MP4_Side_Camera", camera_data); bpy.context.collection.objects.link(camera)
    camera.location = (-2.2, 0, 0.45); camera.rotation_euler = (Vector((0,0,0))-camera.location).to_track_quat("-Z", "Y").to_euler(); camera_data.lens = 55; scene.camera = camera
    render_dir = root / "eight_leg_render"; render_dir.mkdir(exist_ok=True)
    for f in (1, 6, 12, 18, 24):
        if f <= len(observations): scene.frame_set(f); scene.render.filepath = str(render_dir / f"blender_{f:03d}.png"); bpy.ops.render.render(write_still=True)
    rig["cmai_solver"] = "opencv_silhouette_procedural_gait_ik_two_bone_foot_preserving"; rig["cmai_source_motion"] = str(Path(args.motion).resolve()); rig["cmai_existing_actions_used"] = False
    three_data = bpy.data.cameras.new("CMAI_ThreeQuarter_Camera"); three = bpy.data.objects.new("CMAI_ThreeQuarter_Camera", three_data); bpy.context.collection.objects.link(three)
    three.location = (-3.4, -2.4, 1.45); three.rotation_euler = (Vector((0,0,0.05))-three.location).to_track_quat("-Z", "Y").to_euler(); three_data.lens = 55; scene.camera = three
    scene.frame_set(1)
    Path(args.report).write_text(json.dumps({"fps": fps, "frames": len(observations), "leg_ik_targets": len(targets), "render_dir": str(render_dir), "comparison_pending": True, "limitations": ["overlapping/hidden legs are not individually observable", "silhouette does not identify anatomical joints"]}, indent=2), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print(json.dumps({"output": args.output, "frames": len(observations), "ik_targets": len(targets)}))


if __name__ == "__main__": main()
