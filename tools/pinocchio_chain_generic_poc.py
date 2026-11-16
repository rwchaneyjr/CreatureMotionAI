import json, sys
from pathlib import Path
import numpy as np
import pinocchio as pin

def M(x): return np.asarray(x, dtype=float)

def main():
    src, out = map(Path, sys.argv[1:3])
    d=json.loads(src.read_text()); bones=d['bones']; model=pin.Model(); parent=0
    # Each joint gets its own axis, measured from that bone's rest orientation.
    axes=[]; rel=[]
    for i,b in enumerate(bones):
        rest=M(b['rest_matrix']); local=M(b['parent_relative_rest'])
        R=rest[:3,:3] if i==0 else local[:3,:3]
        t=np.zeros(3) if i==0 else local[:3,3]
        axis=np.asarray(R[:,0],float); axis/=np.linalg.norm(axis)
        axes.append(axis.tolist()); rel.append(local.tolist())
        jid=model.addJoint(parent,pin.JointModelRevoluteUnaligned(axis),pin.SE3(R,t),b['name'])
        parent=jid
    data=model.createData(); q=pin.neutral(model)
    def fk(qv):
        pin.forwardKinematics(model,data,qv)
        points=[]
        for i in range(1, len(bones)+1): points.append(data.oMi[i].translation.copy())
        foot=data.oMi[parent].translation + data.oMi[parent].rotation.dot(np.array([0.,float(bones[-1]['length']),0.]))
        return np.asarray(points), foot
    expected=np.asarray([b['head_armature'] for b in bones],float)-np.asarray(bones[0]['head_armature'],float)
    pts,foot=fk(q); expected_foot=np.asarray(bones[-1]['tail_armature'],float)-np.asarray(bones[0]['head_armature'],float)
    report={'status':'PINOCCHIO_CHAIN_BUILT','leg':d['leg'],'pinocchio_version':pin.__version__,'source_chain':str(src),'axes_per_joint':axes,'rest_joint_error':float(np.max(np.linalg.norm(pts-expected,axis=1))),'rest_foot_error':float(np.linalg.norm(foot-expected_foot)),'rest_pass':bool(np.linalg.norm(foot-expected_foot)<1e-4),'moving_pose_conversion':'NOT_PERFORMED','note':'External FK only; Blender movement conversion is not claimed.'}
    out.write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
