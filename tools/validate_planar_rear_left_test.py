"""Validate and render the saved planar Leg_Rear.L experiment."""
import argparse, json, math, sys
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--blend',required=True); ap.add_argument('--report',required=True); ap.add_argument('--render-dir',required=True)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
    import bpy
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    scene=bpy.context.scene; arm=next(o for o in scene.objects if o.type=='ARMATURE'); mesh=next(o for o in scene.objects if o.type=='MESH')
    # Use a fixed temporary side camera for this planar diagnostic. The source
    # blend's three-quarter camera is intentionally not reused for comparison.
    cam=bpy.data.objects.get('CMAI_Planar_Side_Camera')
    if cam is None:
        data=bpy.data.cameras.new('CMAI_Planar_Side_Camera'); cam=bpy.data.objects.new('CMAI_Planar_Side_Camera',data); scene.collection.objects.link(cam)
    cam.location=(-3.35,0.0,0.42); cam.data.type='ORTHO'; cam.data.ortho_scale=2.15
    target=Vector((0.0,0.0,0.18)); direction=target-cam.location; cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler(); scene.camera=cam
    names=['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03']; scene.frame_set(1); bpy.context.view_layer.update()
    rest_m={n:arm.matrix_world@arm.pose.bones[n].matrix.copy() for n in names}
    rest_foot=arm.matrix_world@arm.pose.bones[names[2]].tail
    rest_knee=arm.matrix_world@arm.pose.bones[names[0]].tail; rest_hip=arm.matrix_world@arm.pose.bones[names[0]].head
    rest_normal=(rest_knee-rest_hip).cross(rest_foot-rest_hip).normalized()
    groups={mesh.vertex_groups[n].index for n in names if mesh.vertex_groups.get(n)}
    vidx=[v.index for v in mesh.data.vertices if any(g.group in groups for g in v.groups)]
    def sample():
        ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=ev.to_mesh(); mw=ev.matrix_world
        pts=[mw@me.vertices[i].co for i in vidx]; ev.to_mesh_clear();
        p={n:{'head':list(arm.matrix_world@arm.pose.bones[n].head),'tail':list(arm.matrix_world@arm.pose.bones[n].tail)} for n in names}
        return p,pts
    scene.frame_set(1); bpy.context.view_layer.update(); rest_pose,rest_pts=sample(); ground=min(p.z for p in rest_pts)
    rows=[]; max_disp=0.0; max_pen=0.0; max_ori=0.0
    render_dir=Path(a.render_dir); render_dir.mkdir(parents=True,exist_ok=True)
    scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.color_type='TEXTURE'; scene.render.resolution_x=640; scene.render.resolution_y=360; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'
    for f in range(1,25):
        scene.frame_set(f); bpy.context.view_layer.update(); pose,pts=sample();
        disp=max((p-q).length for p,q in zip(pts,rest_pts)); minz=min(p.z for p in pts); pen=max(0.0,ground-minz)
        q=(arm.matrix_world@arm.pose.bones[names[2]].matrix).to_quaternion(); rq=rest_m[names[2]].to_quaternion(); ori=math.degrees(q.rotation_difference(rq).angle)
        bend=(Vector(pose[names[0]]['tail'])-Vector(pose[names[0]]['head'])).cross(Vector(pose[names[2]]['tail'])-Vector(pose[names[0]]['head']))
        bend_dot=float(bend.normalized().dot(rest_normal)) if bend.length>1e-8 else 0.0
        max_disp=max(max_disp,disp); max_pen=max(max_pen,pen); max_ori=max(max_ori,ori)
        scene.render.filepath=str(render_dir/f'frame_{f:03d}.png'); bpy.ops.render.render(write_still=True)
        rows.append({'frame':f,'foot_endpoint':list(arm.matrix_world@arm.pose.bones[names[2]].tail),'max_weighted_vertex_displacement':disp,'min_weighted_vertex_z':minz,'penetration_vs_rest_ground':pen,'foot_orientation_deviation_deg':ori,'bend_alignment_dot':bend_dot})
    report={'status':'PASS_WITH_LIMITATIONS' if max_pen<=0.005 and max_disp>1e-4 and all(r['bend_alignment_dot']>0 for r in rows) else 'FAIL','action_evaluated':bool(arm.animation_data and arm.animation_data.action and arm.animation_data.action.name in {'CMAI_RearL_Planar_Test_24F','CMAI_RearL_Reference_Guided_24F'}),'action_name':arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None,'mesh_deformed':max_disp>1e-4,'foot_moved':(Vector(rows[-1]['foot_endpoint'])-Vector(rows[0]['foot_endpoint'])).length>1e-4,'ground_reference_z':ground,'max_weighted_mesh_displacement':max_disp,'max_ground_penetration':max_pen,'max_foot_orientation_deviation_deg':max_ori,'self_collision':'UNVERIFIED','approximate_2d_reprojection':'UNVERIFIED','frames':rows,'render_dir':str(render_dir.resolve()),'limitations':['fixed armature-local planar projection','depth held at rest','low-confidence points held/clamped','not verified 3D motion capture']}
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.blend).resolve()))
    Path(a.report).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))

if __name__=='__main__': main()
