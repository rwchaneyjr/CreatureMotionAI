"""Read-only inspection of candidate sole patches in the saved Balisk loop."""
import bpy
import json
import math
import numpy as np
from mathutils import Vector

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers))
chains = {
    'Front.L': ['Leg_Front.L_01', 'Leg_Front.L_02', 'Leg_Front.L_03'],
    'Front.R': ['Leg_Front.R_01', 'Leg_Front.R_02', 'Leg_Front.R_03'],
    'MidFront.L': ['Leg_MidFront.L_01', 'Leg_MidFront.L_02', 'Leg_MidFront.L_03'],
    'MidFront.R': ['Leg_MidFront.R_01', 'Leg_MidFront.R_02', 'Leg_MidFront.R_03'],
    'MidRear.L': ['Leg_MidRear.L_01', 'Leg_MidRear.L_02', 'Leg_MidRear.L_03'],
    'MidRear.R': ['Leg_MidRear.R_01', 'Leg_MidRear.R_02', 'Leg_MidRear.R_03'],
    'Rear.L': ['Leg_Rear.L_01', 'Leg_Rear.L_02', 'Leg_Rear.L_03'],
    'Rear.R': ['Leg_Rear.R_01', 'Leg_Rear.R_02', 'Leg_Rear.R_03'],
}
scene = bpy.context.scene
out = {'source': bpy.data.filepath, 'mesh': mesh.name, 'armature': arm.name, 'legs': {}}
terminal_indices = {leg: mesh.vertex_groups[names[-1]].index for leg, names in chains.items()}
weight_arrays = {leg: np.zeros(len(mesh.data.vertices), dtype=np.float32) for leg in chains}
by_group = {index: leg for leg, index in terminal_indices.items()}
for vertex in mesh.data.vertices:
    for membership in vertex.groups:
        leg = by_group.get(membership.group)
        if leg is not None:
            weight_arrays[leg][vertex.index] = membership.weight
for frame in [1, 11, 21, 31, 41]:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = evaluated.to_mesh()
    coords = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get('co', coords)
    world_matrix = np.array(evaluated.matrix_world)
    coords = coords.reshape(-1, 3) @ world_matrix[:3, :3].T + world_matrix[:3, 3]
    normals = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get('normal', normals)
    normals = normals.reshape(-1, 3) @ np.linalg.inv(world_matrix[:3, :3])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    frame_data = {}
    for leg, names in chains.items():
        points = [arm.matrix_world @ arm.pose.bones[n].head for n in names] + [arm.matrix_world @ arm.pose.bones[names[-1]].tail]
        direction = (points[3] - points[2]).normalized()
        along = (coords - np.array(points[2])) @ np.array(direction)
        mask = (weight_arrays[leg] >= .35) & (along >= .15 * (points[3] - points[2]).length) & (normals[:, 2] < -.25)
        ids = np.flatnonzero(mask)
        if len(ids):
            z = coords[ids, 2]
            low_ids = ids[z <= z.min() + .003]
            frame_data[leg] = {
                'weighted_distal_count': int(len(ids)),
                'candidate_low_count': int(len(low_ids)),
                'candidate_bbox': np.round(np.ptp(coords[low_ids], axis=0), 5).tolist(),
                'candidate_min_clearance_from_ground_object': round(float(coords[low_ids, 2].min() - next((o.location.z for o in scene.objects if o.name == 'CMAI_Ground_Contact'), 0.0)), 6),
                'candidate_median_clearance_from_ground_object': round(float(np.median(coords[low_ids, 2]) - next((o.location.z for o in scene.objects if o.name == 'CMAI_Ground_Contact'), 0.0)), 6),
            }
        else:
            frame_data[leg] = {'weighted_distal_count': 0}
    out['legs'][str(frame)] = frame_data
    evaluated.to_mesh_clear()
print('CONTACT_REGION_INSPECTION ' + json.dumps(out, separators=(',', ':')))
