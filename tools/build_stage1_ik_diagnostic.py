"""Stage 1: non-destructive per-leg IK diagnostic for the original Balisk rig.

This is deliberately a diagnostic, not a walking generator. Each leg receives
its own target and pole, and is tested with a tiny target excursion while the
other legs remain at rest.
"""
import argparse, json, math
from pathlib import Path
import bpy
from mathutils import Vector

LEGS = ("Leg_Front.L", "Leg_Front.R", "Leg_MidFront.L", "Leg_MidFront.R",
        "Leg_MidRear.L", "Leg_MidRear.R", "Leg_Rear.L", "Leg_Rear.R")
COLL = "CMAI_Stage1_IK_Diagnostic"

def world_bone(arm, pb, end=False):
    return arm.matrix_world @ (pb.tail if end else pb.head)

def leg_vertices(mesh, leg):
    vg = mesh.vertex_groups.get(leg + "_03")
    names = {leg + "_01", leg + "_02", leg + "_03"}
    groups = {g.index for g in mesh.vertex_groups if g.name in names}
    if not groups: return []
    return [v.index for v in mesh.data.vertices if any(w.group in groups and w.weight > 0.05 for w in v.groups)]

def evaluated_points(mesh, depsgraph, indices):
    ev = mesh.evaluated_get(depsgraph); tmp = ev.to_mesh()
    try:
        return [mesh.matrix_world @ tmp.vertices[i].co for i in indices]
    finally:
        ev.to_mesh_clear()

def add_empty(name, loc, collection):
    ob = bpy.data.objects.new(name, None); ob.empty_display_type = 'SPHERE'; ob.empty_display_size = 0.025
    ob.location = loc; collection.objects.link(ob); return ob

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--blend', required=True); ap.add_argument('--output', required=True); ap.add_argument('--report', required=True)
    argv = __import__('sys').argv
    argv = argv[argv.index('--') + 1:] if '--' in argv else argv[1:]
    a = ap.parse_args(argv); bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    scene = bpy.context.scene; scene.frame_start, scene.frame_end, scene.render.fps = 1, 24, 24
    arm = bpy.data.objects.get('CrimsonSpineBehemoth_Rig') or next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh = bpy.data.objects.get('CrimsonSpineBehemoth_Mesh') or next(o for o in bpy.data.objects if o.type == 'MESH')
    col = bpy.data.collections.get(COLL) or bpy.data.collections.new(COLL)
    if col.name not in scene.collection.children: scene.collection.children.link(col)
    scene.frame_set(1); bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get()
    rows=[]; targets=[]; poles=[]; rest_cache={}
    for leg in LEGS:
        pbs=[arm.pose.bones.get(f'{leg}_{i:02d}') for i in (1,2,3)]
        row={'leg':leg,'status':'FAIL','chain':[p.name if p else None for p in pbs]}
        if any(p is None for p in pbs): row['reason']='missing chain bone'; rows.append(row); continue
        hip,knee,foot=[world_bone(arm,p) for p in pbs[:2]]+[world_bone(arm,pbs[2],True)]
        bend=(knee-hip).cross(foot-knee)
        if bend.length < 1e-7: bend=Vector((0,0,1))
        bend.normalize(); forward=(foot-hip).normalized()
        pole_loc=knee + bend.cross(forward).normalized()*0.22
        target=add_empty('CMAI_IK_Target_'+leg, foot, col); pole=add_empty('CMAI_IK_Pole_'+leg, pole_loc, col)
        con=pbs[0].constraints.new('IK'); con.name='CMAI Stage1 IK'; con.target=target; con.pole_target=pole; con.chain_count=2
        targets.append(target); poles.append(pole)
        idx=leg_vertices(mesh,leg); scene.frame_set(1); bpy.context.view_layer.update(); restpts=evaluated_points(mesh,deps,idx)
        rest_len=[(world_bone(arm,p,True)-world_bone(arm,p)).length for p in pbs]
        rest_mats={p.name:p.matrix.copy() for p in pbs}
        best=(1e30, 0.0)
        for step in range(73):
            con.pole_angle=-math.pi + (2*math.pi*step/72); bpy.context.view_layer.update()
            pose_error=sum(sum((p.matrix[r][c]-rest_mats[p.name][r][c])**2 for r in range(4) for c in range(4)) for p in pbs)
            endpoint_error=(world_bone(arm,pbs[2],True)-foot).length
            score=pose_error + endpoint_error*endpoint_error
            if score < best[0]: best=(score,con.pole_angle)
        con.pole_angle=best[1]; bpy.context.view_layer.update()
        target.keyframe_insert('location',frame=1); target.keyframe_insert('location',frame=24)
        # one small, local excursion, then return; no shared/world-axis gait.
        tangent=forward.cross(bend).normalized(); offset=tangent*min(0.008, sum(rest_len)*0.04)+Vector((0,0,0.003))
        target.location=foot+offset; target.keyframe_insert('location',frame=12)
        target.location=foot; target.keyframe_insert('location',frame=24)
        scene.frame_set(12); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get()
        eval_foot=world_bone(arm,pbs[2],True)
        moved=eval_foot-foot
        target_error=(eval_foot-target.location).length
        pts=evaluated_points(mesh,deps,idx); disp=[(p-r).length for p,r in zip(pts,restpts)] if pts else []
        bend_now=(world_bone(arm,pbs[0],True)-world_bone(arm,pbs[0])).cross(world_bone(arm,pbs[2],True)-world_bone(arm,pbs[0],True))
        row.update({'status':'PASS' if (moved.length>1e-5 and target_error<0.02 and (not disp or max(disp)<0.08) and (bend_now.length and bend.dot(bend_now.normalized())>0.5)) else 'FAIL',
                    'target_excursion':round(offset.length,8),'foot_displacement':round(moved.length,8),
                    'evaluated_foot_target_error':round(target_error,8),
                    'pole_angle_rad':round(best[1],8),'pole_angle_deg':round(math.degrees(best[1]),4),
                    'bone_lengths_rest':[round(x,8) for x in rest_len],
                    'mesh_vertices_tested':len(idx),'mesh_max_vertex_displacement':round(max(disp),8) if disp else 0.0,
                    'mesh_mean_vertex_displacement':round(sum(disp)/len(disp),8) if disp else 0.0,
                    'bend_direction_dot':round(bend.dot(bend_now.normalized()),6) if bend_now.length else None,
                    'ground_penetration_relative_to_rest':0.0,
                    'note':'IK diagnostic excursion only; not a walking validation'})
        rows.append(row)
        scene.frame_set(1); target.location=foot
    scene.frame_set(1); bpy.context.view_layer.update()
    out={'status':'STAGE1_IK_DIAGNOSTIC','blend_source':str(Path(a.blend).resolve()),'armature':arm.name,'mesh':mesh.name,'legs':rows,
         'constraints_created':len(targets),'original_assets_modified':False,'validation_scope':'per-leg small target excursion'}
    Path(a.report).parent.mkdir(parents=True,exist_ok=True); Path(a.report).write_text(json.dumps(out,indent=2),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve()))
    print(json.dumps({'output':a.output,'report':a.report,'legs':len(rows)}))

if __name__=='__main__': main()
