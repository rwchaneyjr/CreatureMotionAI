"""Per-leg IK rest-pose diagnostic; never overwrites the source blend."""
import argparse, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

LEGS = ["Leg_Front.L", "Leg_Front.R", "Leg_MidFront.L", "Leg_MidFront.R", "Leg_MidRear.L", "Leg_MidRear.R", "Leg_Rear.L", "Leg_Rear.R"]

def wp(arm, pb, tail=False):
    return arm.matrix_world @ (pb.tail if tail else pb.head)

def pose_snapshot(arm):
    return {p.name: p.matrix_basis.copy() for p in arm.pose.bones}

def restore_pose(arm, snap):
    for p in arm.pose.bones: p.matrix_basis = snap[p.name]
    bpy.context.view_layer.update()

def points(arm, name):
    return {"hip": wp(arm, arm.pose.bones[name+"_01"], False), "knee": wp(arm, arm.pose.bones[name+"_01"], True), "ankle": wp(arm, arm.pose.bones[name+"_02"], True), "foot": wp(arm, arm.pose.bones[name+"_03"], True)}

def angle(a, b):
    return math.degrees(a.angle(b)) if a.length > 1e-8 and b.length > 1e-8 else 0.0

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); p.add_argument('--tolerance-deg',type=float,default=2.0); p.add_argument('--position-tolerance',type=float,default=0.003); argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=p.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    scene=bpy.context.scene; scene.frame_set(1); arm=next(o for o in scene.objects if o.type=='ARMATURE')
    if len(arm.data.bones)!=38: raise RuntimeError('Expected original 38-bone armature')
    for pb in arm.pose.bones:
        for c in list(pb.constraints): pb.constraints.remove(c)
    bpy.context.view_layer.update(); base_pose=pose_snapshot(arm); baseline={n:points(arm,n) for n in LEGS}
    results=[]; selected={}
    for name in LEGS:
        restore_pose(arm,base_pose); b=baseline[name]; upper=b['knee']-b['hip']; lower=b['ankle']-b['knee']; bend=lower-upper*(lower.dot(upper)/max(upper.length_squared,1e-12)); fallback=False
        if bend.length < 1e-6:
            fallback=True; axis=arm.matrix_world.to_3x3() @ Vector((0,0,1)); bend=axis-(axis.dot(upper.normalized()))*upper.normalized()
        if bend.length < 1e-6: bend=Vector((1,0,0))
        bend.normalize(); pole_distance=max((upper.length+lower.length)*1.5,0.25); pole_pos=b['knee']+bend*pole_distance
        target=bpy.data.objects.new('CMAI_Diagnostic_Target_'+name,None); scene.collection.objects.link(target); target.location=b['foot']
        pole=bpy.data.objects.new('CMAI_Diagnostic_Pole_'+name,None); scene.collection.objects.link(pole); pole.location=pole_pos
        end_pb=arm.pose.bones[name+'_03']; con=end_pb.constraints.new('IK'); con.name='CMAI_Diagnostic_IK_'+name; con.target=target; con.pole_target=pole; con.chain_count=3; con.influence=1.0
        best=None
        for deg in range(-180,181,5):
            restore_pose(arm,base_pose); con.pole_angle=math.radians(deg); bpy.context.view_layer.update(); solved=points(arm,name)
            vec_base=[b['knee']-b['hip'],b['ankle']-b['knee'],b['foot']-b['ankle']]; vec_sol=[solved['knee']-solved['hip'],solved['ankle']-solved['knee'],solved['foot']-solved['ankle']]
            max_ang=max(angle(x,y) for x,y in zip(vec_base,vec_sol)); max_pos=max((solved[k]-b[k]).length for k in b); target_err=(solved['foot']-target.location).length; foot_err=target_err; score=max_ang+max_pos*1000+target_err*1000
            if best is None or score<best['score']: best={'score':score,'pole_angle_deg':deg,'max_angle_deg':max_ang,'max_position_error':max_pos,'target_error':target_err}
        con.pole_angle=math.radians(best['pole_angle_deg']); restore_pose(arm,base_pose); bpy.context.view_layer.update(); solved=points(arm,name); foot_err=(solved['foot']-b['foot']).length; best['foot_position_error']=foot_err; best['passed']=best['max_angle_deg']<=a.tolerance_deg and best['max_position_error']<=a.position_tolerance and best['target_error']<=a.position_tolerance; best.update({'leg':name,'fallback_bend_plane':fallback,'bend_direction':list(bend),'target_world':list(b['foot']),'pole_world':list(pole_pos),'constraint_owner':end_pb.name,'chain_count':con.chain_count,'influence':con.influence,'position_tolerance':a.position_tolerance,'original':{k:list(v) for k,v in b.items()},'solved':{k:list(v) for k,v in solved.items()}}); results.append(best)
        if best['passed']: selected[name]=con
        else: end_pb.constraints.remove(con)
    all_pass=all(x['passed'] for x in results)
    report={'status':'PASS' if all_pass else 'FAIL','blend':str(Path(a.blend).resolve()),'bone_count':len(arm.data.bones),'tolerance_deg':a.tolerance_deg,'all_eight_passed':all_pass,'legs':results,'note':'Temporary diagnostic copy; source blend is not modified.'}
    Path(a.report).write_text(json.dumps(report,indent=2),encoding='utf-8')
    if all_pass: bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve()))
    print(json.dumps({'status':report['status'],'passed':sum(x['passed'] for x in results),'total':len(results),'report':a.report,'output_saved':all_pass}))

if __name__=='__main__': main()
