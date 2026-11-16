import bpy, json, sys, math
from pathlib import Path
import numpy as np
import pinocchio as pin
from mathutils import Quaternion

args=sys.argv[sys.argv.index('--')+1:]; blend,chain_path,out_blend,out_report=args[:4]
chain=json.loads(Path(chain_path).read_text()); bones=chain['bones']
model=pin.Model(); parent=0
for i,b in enumerate(bones):
    rest=np.asarray(b['rest_matrix'],float); local=np.asarray(b['parent_relative_rest'],float)
    R=rest[:3,:3] if i==0 else local[:3,:3]; t=np.zeros(3) if i==0 else local[:3,3]
    jid=model.addJoint(parent,pin.JointModelRevoluteUnaligned(np.array([1.,0.,0.])),pin.SE3(R,t),b['name']); parent=jid
data=model.createData(); q0=pin.neutral(model)
def fk(q):
    pin.forwardKinematics(model,data,q); pts=[data.oMi[i].translation.copy() for i in range(1,4)]
    foot=data.oMi[parent].translation+data.oMi[parent].rotation.dot(np.array([0.,float(bones[-1]['length']),0.]))
    return np.asarray(pts),foot
restpts,restfoot=fk(q0); base=np.asarray(bones[0]['head_armature'],float); expected=np.asarray([b['head_armature'] for b in bones],float)-base; expectedfoot=np.asarray(bones[-1]['tail_armature'],float)-base
targets={'knee_lift':expectedfoot+np.array([0,0,0.025]),'forward_swing':expectedfoot+np.array([0,-0.025,0.018]),'landing':expectedfoot+np.array([0,-0.018,0.001])}
def solve(target):
    q=q0.copy()
    for _ in range(500):
        pts,foot=fk(q); err=target-foot
        if np.linalg.norm(err)<1e-8: break
        J=np.zeros((3,3)); eps=1e-6
        for k in range(3):
            qt=q.copy(); qt[k]+=eps; J[:,k]=(fk(qt)[1]-foot)/eps
        q+=np.clip(J.T@np.linalg.solve(J@J.T+1e-8*np.eye(3),err),-.08,.08)
    return q
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve())); scene=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
scene.frame_set(1); bpy.context.view_layer.update()
rows=[]
for label,target in targets.items():
    q=solve(target); 
    for i,b in enumerate(bones):
        p=arm.pose.bones[b['name']]; p.rotation_mode='QUATERNION'; p.rotation_quaternion=Quaternion((1,0,0),float(q[i]))
    bpy.context.view_layer.update(); actual=[]
    for b in bones:
        p=arm.pose.bones[b['name']]; actual.append(np.asarray((arm.matrix_world@p.head),float))
    actual=np.asarray(actual); actual_arm=actual-np.asarray(arm.matrix_world@arm.pose.bones[bones[0]['name']].head,float)
    # Compare in armature space, with root-relative positions.
    predicted,_=fk(q); pred_rel=predicted-predicted[0]
    act_rel=actual_arm[1:]-actual_arm[0]
    rows.append({'pose':label,'q':q.tolist(),'predicted_foot_target':target.tolist(),'evaluated_joint_error_max':float(np.max(np.linalg.norm(pred_rel-act_rel,axis=1))),'evaluated_foot_error':'NOT_MEASURED_ENDPOINT_MARKER','mesh_deformation':'NOT_MEASURED','pass':False})
    for i,b in enumerate(bones):
        p=arm.pose.bones[b['name']]; p.rotation_quaternion=Quaternion((1,0,0),0)
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve()),copy=True)
Path(out_report).write_text(json.dumps({'status':'MIDREARR_MOVING_CONVERSION_DIAGNOSTIC','source_blend':blend,'chain':chain_path,'poses':rows,'note':'Temporary test; no original Action modified.'},indent=2))
print(json.dumps(rows,indent=2))
