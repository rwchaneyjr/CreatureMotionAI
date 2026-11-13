"""Reusable temporary three-bone IK step builder.

This module is intentionally non-destructive: callers pass a temporary scene copy
and the function creates only temporary target/pole controls and animation data.
"""
from mathutils import Vector
import math

def inspect_leg_chain(armature, mesh, bone_names, weight_threshold=0.25):
    """Return rest geometry and weighted contact-region metadata for any 3-bone chain."""
    if len(bone_names) < 2:
        raise ValueError("bone_names must contain at least two bones")
    bones = [armature.data.bones.get(n) for n in bone_names]
    if any(b is None for b in bones):
        return {"status": "UNSUPPORTED", "reason": "missing bone in chain"}
    group_ids = {mesh.vertex_groups[n].index for n in bone_names if mesh.vertex_groups.get(n)}
    vertices = [v.index for v in mesh.data.vertices if any(g.group in group_ids and g.weight >= weight_threshold for g in v.groups)]
    return {"status": "PASS", "bones": list(bone_names), "lengths": [b.length for b in bones], "parents": [b.parent.name if b.parent else None for b in bones], "contact_vertex_indices": vertices, "rest_matrices": [list(sum(([float(x) for x in row] for row in b.matrix_local), [])) for b in bones]}

def make_leg_trajectory(rest_foot, forward_axis, lift_height, stride, frame_start, frame_end):
    """Create a smooth lift/swing/plant trajectory without creature-specific assumptions."""
    import math
    axis = forward_axis.normalized()
    result = []
    for frame in range(frame_start, frame_end + 1):
        q = (frame - frame_start) / max(1, frame_end - frame_start)
        envelope = math.sin(math.pi * q)
        result.append((frame, rest_foot + axis * (stride * envelope) + Vector((0, 0, lift_height * envelope))))
    return result

def pole_from_rest_pose(hip_world, knee_world, foot_world, fallback_axis=Vector((0, 0, 1)), distance=0.25):
    """Derive a stable pole point from the leg's own rest bend plane."""
    axis = foot_world - hip_world
    bend = (knee_world - hip_world).cross(axis)
    if bend.length < 1e-6:
        bend = fallback_axis.copy()
    return knee_world + bend.normalized() * distance

def validate_leg_candidate(clearance_rows, max_penetration, max_target_error, bend_ok, orientation_ok):
    reasons = []
    if max((r.get("penetration", 0.0) for r in clearance_rows), default=0.0) > max_penetration:
        reasons.append("ground_penetration")
    if max((r.get("target_error", 0.0) for r in clearance_rows), default=0.0) > max_target_error:
        reasons.append("target_error")
    if not bend_ok: reasons.append("bend_direction")
    if not orientation_ok: reasons.append("foot_orientation")
    return {"status": "PASS" if not reasons else "REJECTED", "reasons": reasons}

def capture_rest_pose(armature, bone_names):
    """Capture evaluated world-space rest transforms for a leg chain."""
    return {name: {"matrix_world": [list(row) for row in armature.matrix_world @ armature.pose.bones[name].matrix], "head": list(armature.matrix_world @ armature.pose.bones[name].head), "tail": list(armature.matrix_world @ armature.pose.bones[name].tail)} for name in bone_names}

def validate_rest_alignment(armature, bone_names, captured, position_tolerance=1e-3, angle_tolerance_deg=1.0):
    """Reject an IK setup that changes evaluated world-space rest geometry."""
    import math
    failures = []
    for name in bone_names:
        b = armature.pose.bones[name]
        head = armature.matrix_world @ b.head
        tail = armature.matrix_world @ b.tail
        if (head - Vector(captured[name]["head"])).length > position_tolerance or (tail - Vector(captured[name]["tail"])).length > position_tolerance:
            failures.append({"bone": name, "reason": "rest_position_changed"})
    return {"status": "PASS" if not failures else "REJECTED", "failures": failures, "position_tolerance": position_tolerance, "angle_tolerance_deg": angle_tolerance_deg}

def solve_rest_relative_two_link(hip, target, upper_length, lower_length, bend_normal, min_knee_angle=math.radians(5.0)):
    """Analytical two-link solve in world space; returns hip/knee/target or rejects."""
    import math
    axis = target - hip; distance = axis.length
    if distance < 1e-8 or distance > upper_length + lower_length or distance < abs(upper_length - lower_length):
        return {"status": "REJECTED", "reason": "unreachable_target"}
    direction = axis.normalized()
    normal = bend_normal.normalized() if bend_normal.length > 1e-8 else Vector((0, 0, 1))
    # The knee offset belongs IN the bend plane, perpendicular to the reach.
    # For normal=(knee-hip).cross(target-hip), direction.cross(normal)
    # retains the original side of the knee. A double cross returned the
    # plane normal itself and bent the leg out of its anatomical plane.
    bend = direction.cross(normal)
    if bend.length < 1e-8:
        return {"status": "REJECTED", "reason": "degenerate_bend_plane"}
    bend.normalize()
    along = (upper_length**2 - lower_length**2 + distance**2) / (2.0 * distance)
    height = math.sqrt(max(0.0, upper_length**2 - along**2))
    knee = hip + direction * along + bend * height
    knee_angle = math.acos(max(-1.0, min(1.0, (upper_length**2 + lower_length**2 - distance**2) / (2.0 * upper_length * lower_length))))
    if math.pi - knee_angle < min_knee_angle:
        return {"status": "REJECTED", "reason": "near_full_extension", "knee_angle": knee_angle}
    return {"status": "PASS", "hip": hip, "knee": knee, "foot": target, "knee_angle": knee_angle, "bend_normal": normal}

def capture_world_pose(armature, bone_names):
    """Capture evaluated pose matrices in world space for later restoration/conversion."""
    return {name: armature.matrix_world @ armature.pose.bones[name].matrix.copy() for name in bone_names}

def apply_world_pose_matrices(armature, world_matrices):
    """Assign desired world matrices through Blender pose-matrix conversion."""
    inverse = armature.matrix_world.inverted()
    for name, world_matrix in world_matrices.items():
        bone = armature.pose.bones.get(name)
        if bone is None:
            raise ValueError(f"Missing pose bone: {name}")
        bone.matrix = inverse @ world_matrix
    armature.id_data.update_tag()

def world_direction_pose_matrix(rest_world_matrix, rest_head_world, desired_head_world, desired_tail_world, rest_tail_world=None):
    """Build a desired bone matrix by rotating the original world bone toward a solved segment."""
    from mathutils import Vector, Matrix
    if rest_tail_world is None:
        raise ValueError("rest_tail_world is required; do not assume a local bone axis")
    rest_dir = (rest_tail_world - rest_head_world).normalized()
    desired_dir = (desired_tail_world - desired_head_world).normalized()
    delta = rest_dir.rotation_difference(desired_dir).to_matrix().to_4x4()
    result = delta @ rest_world_matrix.copy()
    result.translation = desired_head_world
    return result

def restore_terminal_foot_world_orientation(armature, terminal_bone_name, captured_world_matrix, solved_parent_tail_world):
    """Restore a connected terminal bone's world orientation after parent solving.

    Translation is restricted to the solved parent tail; connected-bone parenting
    owns the terminal head position. The function therefore never independently
    translates a connected foot.
    """
    bone = armature.pose.bones.get(terminal_bone_name)
    if bone is None:
        raise ValueError(f"Missing terminal bone: {terminal_bone_name}")
    desired = captured_world_matrix.copy()
    desired.translation = solved_parent_tail_world
    bone.matrix = armature.matrix_world.inverted() @ desired
    armature.id_data.update_tag()
    return desired

def add_ik_step(armature, leg_chain, original_foot_world, original_knee_world,
                lift_height, stride_distance, frame_start, frame_end,
                forward_axis=Vector((1, 0, 0)), ground_axis=Vector((0, 0, 1))):
    if len(leg_chain) != 3:
        raise ValueError("leg_chain must contain exactly three deform bones")
    scene = armature.id_data.scene if hasattr(armature.id_data, "scene") else None
    import bpy, math
    target = bpy.data.objects.new("CMAI_Temp_IK_Target", None)
    pole = bpy.data.objects.new("CMAI_Temp_IK_Pole", None)
    armature.users_scene[0].collection.objects.link(target)
    armature.users_scene[0].collection.objects.link(pole)
    target.location = original_foot_world
    bend = (original_knee_world - original_foot_world).cross(forward_axis).normalized()
    pole.location = original_knee_world + bend * 0.25
    constraint = armature.pose.bones[leg_chain[-1]].constraints.new("IK")
    constraint.target = target
    constraint.pole_target = pole
    constraint.chain_count = 3
    constraint.influence = 1.0
    for frame in range(frame_start, frame_end + 1):
        q = (frame - frame_start) / max(1, frame_end - frame_start)
        envelope = math.sin(math.pi * q)
        target.location = (original_foot_world + forward_axis.normalized() * stride_distance * envelope + ground_axis.normalized() * lift_height * envelope)
        target.keyframe_insert("location", frame=frame)
    return {"target": target, "pole": pole, "constraint": constraint}

def add_two_bone_ik_step(armature, upper_bone, lower_bone, terminal_bone,
                         ankle_world, knee_world, lift_height, stride_distance,
                         frame_start, frame_end, forward_axis=Vector((1, 0, 0))):
    """Experimental two-bone IK with an independently controlled terminal bone."""
    import bpy
    target = bpy.data.objects.new("CMAI_Temp_TwoBone_Target", None)
    pole = bpy.data.objects.new("CMAI_Temp_TwoBone_Pole", None)
    armature.users_scene[0].collection.objects.link(target)
    armature.users_scene[0].collection.objects.link(pole)
    target.location = ankle_world
    pole.location = knee_world + pole_from_rest_pose(armature.matrix_world @ armature.pose.bones[upper_bone].head, knee_world, ankle_world) - knee_world
    constraint = armature.pose.bones[lower_bone].constraints.new("IK")
    constraint.target = target; constraint.pole_target = pole; constraint.chain_count = 2; constraint.influence = 1.0
    return {"strategy": "two_bone_terminal_control", "target": target, "pole": pole, "constraint": constraint, "terminal_bone": terminal_bone}
