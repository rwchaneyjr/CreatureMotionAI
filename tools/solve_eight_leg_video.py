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
    p.add_argument("--model", default=""); p.add_argument("--blend", default="", help="Preserved Blender baseline; preferred over FBX re-import")
    p.add_argument("--motion", required=True)
    p.add_argument("--output", required=True); p.add_argument("--report", required=True)
    p.add_argument("--stride", type=float, default=0.03); p.add_argument("--lift", type=float, default=0.02)
    p.add_argument("--phase-offset", type=float, default=0.55); p.add_argument("--body-amplitude", type=float, default=0.4)
    p.add_argument("--station-phase", default="0,0,0,0"); p.add_argument("--station-stride", default="1,1,1,1")
    p.add_argument("--leg-tracks", default="")
    p.add_argument("--use-tracks", action="store_true")
    p.add_argument("--fit-manifest", default="", help="Mapped per-frame leg eligibility manifest")
    p.add_argument("--enable-ik", action="store_true", help="Enable IK only after the rig passes the rest-pose IK test")
    p.add_argument("--max-frames", type=int, default=24)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = p.parse_args(argv)
    station_phase = [float(x) for x in args.station_phase.split(",")]
    station_stride = [float(x) for x in args.station_stride.split(",")]
    leg_tracks = {}
    if args.leg_tracks and args.use_tracks:
        track_data = json.loads(Path(args.leg_tracks).read_text(encoding="utf-8"))
        leg_tracks = {item["frame"]: item.get("candidates", []) for item in track_data.get("frames", [])}
    fit_manifest = {}
    if args.fit_manifest:
        manifest = json.loads(Path(args.fit_manifest).read_text(encoding="utf-8"))
        fit_manifest = {int(item["frame"]): item for item in manifest.get("frames", [])}
    root = Path(args.output).parent
    motion = json.loads(Path(args.motion).read_text(encoding="utf-8"))
    fps = float(motion.get("fps", 24.0))
    all_observations = motion.get("frames", [])
    observations = all_observations[:args.max_frames] if args.max_frames > 0 else all_observations
    station_baseline = {}
    for item in observations[:1]:
        for cand in item.get("leg_candidates", []):
            station_baseline[int(cand.get("station", -1))] = cand.get("foot", [0.0, 0.0, 0.0])
    if args.blend:
        bpy.ops.wm.open_mainfile(filepath=str(Path(args.blend).resolve()))
    else:
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
    # Remove only temporary rest-pose diagnostic constraints from the input
    # copy before attaching this solve's moving targets.
    for pb in rig.pose.bones:
        for constraint in list(pb.constraints):
            if constraint.name.startswith("CMAI_Diagnostic_IK_"):
                pb.constraints.remove(constraint)
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
    root_rest_location = rest_pose.get("Root", (Vector((0, 0, 0)),))[0].copy()
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    action = bpy.data.actions.new("CMAI_EightLeg_MP4_Solved")
    action.use_fake_user = True; rig.animation_data_create(); rig.animation_data.action = action
    # Four stations x two sides, matching the existing Balisk rig.
    leg_roots = [n for n in rig.data.bones.keys() if n.startswith("Leg_") and (n.endswith("_upper") or n.endswith("_01"))]
    leg_roots.sort()
    targets = {}
    leg_ik_active = {}
    leg_reach = {}
    poles = {}
    for name in leg_roots:
        target = bpy.data.objects.new("CMAI_IK_" + name, None); bpy.context.collection.objects.link(target)
        target.empty_display_type = "SPHERE"; target.empty_display_size = 0.04
        lower_name = name.replace("_upper", "_lower").replace("_01", "_02")
        ankle_name = name.replace("_upper", "_lower").replace("_01", "_03")
        foot_data_bone = rig.data.bones.get(ankle_name)
        if foot_data_bone:
            target.location = rig.matrix_world @ foot_data_bone.tail_local
        else:
            target.location = rig.matrix_world @ rig.data.bones[name].tail_local
        con = rig.pose.bones.get(ankle_name)
        ik_active = con is not None
        leg_ik_active[name] = ik_active
        upper_bone = rig.data.bones.get(name)
        lower_bone = rig.data.bones.get(lower_name)
        leg_reach[name] = (upper_bone.length if upper_bone else 0.0) + (lower_bone.length if lower_bone else 0.0)
        if con and args.enable_ik:
            ik = con.constraints.new("IK"); ik.name = "CMAI_FootContact_IK"; ik.target = target; ik.chain_count = 3
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
            # Preserve the original FBX/static standing pose in the new
            # Action. Without these baseline keys, assigning a fresh Action
            # makes unkeyed bones fall back to armature rest transforms.
            bone.keyframe_insert("location", frame=f, group=bone.name)
            bone.keyframe_insert("rotation_euler", frame=f, group=bone.name)
            bone.keyframe_insert("rotation_quaternion", frame=f, group=bone.name)
            bone.keyframe_insert("scale", frame=f, group=bone.name)
        landmarks = obs.get("landmarks", {})
        leg_candidates = {item.get("station"): item for item in obs.get("leg_candidates", [])}
        center = landmarks.get("motion_center", [0.5, 0.5, 0.0])
        top = landmarks.get("motion_top", [0.5, 0.25, 0.0])[1]
        bottom = landmarks.get("motion_bottom", [0.5, 0.75, 0.0])[1]
        cx, cy = center[:2]; sx, sy = 0.5, max(bottom - top, 0.01)
        root_bone = rig.pose.bones.get("Root")
        body = rig.pose.bones.get("Body_02") or rig.pose.bones.get("Body_01")
        tail = rig.pose.bones.get("Tail_02")
        # Move the whole creature in its longitudinal local axis to match the
        # reference screen position. This is separate from leg IK and is based
        # on the original root location.
        if root_bone and not is_rest_frame:
            # Keep the original standing height. Silhouette-centre Y is not
            # a reliable depth/height measurement and previously made every
            # foot alternately penetrate or float above the ground.
            root_bone.location = root_rest_location + Vector((0.0, (0.5 - cx) * 0.9, 0.0))
            root_bone.keyframe_insert("location", frame=f)
        if body and not is_rest_frame:
            body.rotation_mode = "XYZ"; body.rotation_euler = Euler(((cy - 0.5) * args.body_amplitude, (cx - 0.5) * 0.3, (sx - 0.5) * 0.15), "XYZ"); body.keyframe_insert("rotation_euler", frame=f)
        if tail and not is_rest_frame:
            tail.rotation_mode = "XYZ"; tail.rotation_euler.z = math.sin(phase * math.tau) * 0.12; tail.keyframe_insert("rotation_euler", frame=f)
        for index, name in enumerate(leg_roots):
            station = index // 2; side = index % 2
            gait = math.sin((phase * math.tau) + station * args.phase_offset + station_phase[station] + side * math.pi)
            frame_policy = fit_manifest.get(int(source_frame), {})
            # A leg without sufficient two-view evidence must not receive an
            # invented gait offset. It remains at the original rest foot.
            if frame_policy and name in set(frame_policy.get("hold_legs", [])):
                gait = 0.0
            target = targets[name]
            foot_data_bone = rig.data.bones.get(name.replace("_upper", "_lower").replace("_01", "_03"))
            base = rig.matrix_world @ (foot_data_bone.tail_local if foot_data_bone else rig.data.bones[name].tail_local)
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
            # Offsets are small and relative to each original foot. They are
            # transformed through the armature object, never copied from pixel
            # coordinates. Clamp to the actual two-bone reach.
            offset_local = Vector((0.0, swing * args.stride * station_stride[station], swing * args.lift))
            # Use the coarse video station only as a small bounded correction.
            # It is not treated as an individual-leg label.
            candidate = leg_candidates.get(station)
            base_video = station_baseline.get(station)
            if candidate and base_video and float(candidate.get("confidence", 0.0)) >= 0.6 and not is_rest_frame:
                foot = candidate.get("foot", base_video)
                video_dx = max(-0.05, min(0.05, float(foot[0]) - float(base_video[0])))
                video_lift = max(0.0, min(0.035, (float(base_video[1]) - float(foot[1])) * 0.12))
                offset_local.y += video_dx * 0.35
                offset_local.z += video_lift
            offset = rig.matrix_world.to_3x3() @ offset_local
            max_offset = max(0.0, leg_reach.get(name, 0.0) * 0.25)
            if offset.length > max_offset and offset.length > 1e-8:
                offset.normalize(); offset *= max_offset
            target.location = base + offset
            target.keyframe_insert("location", frame=f)
            leg_root_bone = rig.pose.bones.get(name)
            lower_name = name.replace("_upper", "_lower").replace("_01", "_02")
            lower = rig.pose.bones.get(lower_name)
            # No direct keying of leg_root_bone: IK owns this chain.
            # IK owns the upper/lower leg rotation. Do not also key the lower
            # bone, which previously caused the ankle/foot to flip upward.
            if lower and not is_rest_frame and not leg_ik_active.get(name, False):
                lower.rotation_mode = "XYZ"; lower.rotation_euler.y = -max(0, gait) * 0.28; lower.keyframe_insert("rotation_euler", frame=f)
    scene = bpy.context.scene; scene.frame_start = 1; scene.frame_end = len(observations); scene.render.fps = int(round(fps))
    ground_points = []
    for root_name in ("Leg_Front.L", "Leg_Front.R", "Leg_MidFront.L", "Leg_MidFront.R", "Leg_MidRear.L", "Leg_MidRear.R", "Leg_Rear.L", "Leg_Rear.R"):
        pb = rig.pose.bones.get(root_name + "_03")
        if pb: ground_points.append((rig.matrix_world @ pb.tail).z)
    if ground_points:
        scene["CMAI_GROUND_Z"] = min(ground_points)
    scene.render.engine = "BLENDER_WORKBENCH"; scene.display.shading.color_type = "TEXTURE"; scene.display.shading.light = "STUDIO"; scene.render.resolution_x = 1280; scene.render.resolution_y = 720; scene.render.resolution_percentage = 50
    camera = bpy.data.objects.get("CMAI_Calibrated_Side_Camera")
    if camera is None:
        camera_data = bpy.data.cameras.new("CMAI_Calibrated_Side_Camera")
        camera = bpy.data.objects.new("CMAI_Calibrated_Side_Camera", camera_data)
        bpy.context.collection.objects.link(camera)
        camera.location = (3.5, -6.0, 2.2)
        target = rig.matrix_world.translation
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.lens = 52
        camera["cmai_fallback_camera"] = True
    scene.camera = camera
    render_dir = root / "eight_leg_render"; render_dir.mkdir(exist_ok=True)
    sample_frames = sorted(set([1, 6, 12, 18, 24, len(observations)]))
    for f in sample_frames:
        if f <= len(observations): scene.frame_set(f); scene.render.filepath = str(render_dir / f"blender_{f:03d}.png"); bpy.ops.render.render(write_still=True)
    rig["cmai_solver"] = "opencv_silhouette_procedural_gait_ik_two_bone_foot_preserving"; rig["cmai_source_motion"] = str(Path(args.motion).resolve()); rig["cmai_existing_actions_used"] = False
    scene.frame_set(1)
    Path(args.report).write_text(json.dumps({"fps": fps, "frames": len(observations), "leg_ik_targets": len(targets), "render_dir": str(render_dir), "comparison_pending": True, "limitations": ["overlapping/hidden legs are not individually observable", "silhouette does not identify anatomical joints"]}, indent=2), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print(json.dumps({"output": args.output, "frames": len(observations), "ik_targets": len(targets)}))


if __name__ == "__main__": main()
