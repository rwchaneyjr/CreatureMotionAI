import json, sys
from pathlib import Path
import numpy as np
import pinocchio as pin

src, out = sys.argv[1:3]
d = json.loads(Path(src).read_text()); bones = d['bones']; model = pin.Model(); parent = 0
for i, b in enumerate(bones):
    rest = np.asarray(b['rest_matrix'], float); local = np.asarray(b['parent_relative_rest'], float)
    R = rest[:3,:3] if i == 0 else local[:3,:3]; t = np.zeros(3) if i == 0 else local[:3,3]
    parent = model.addJoint(parent, pin.JointModelRevoluteUnaligned(np.array([1.,0.,0.])), pin.SE3(R,t), b['name'])
data = model.createData(); q0 = pin.neutral(model)
def fk(q):
    pin.forwardKinematics(model, data, q)
    pts = np.asarray([data.oMi[i].translation.copy() for i in range(1,4)])
    foot = data.oMi[parent].translation + data.oMi[parent].rotation.dot(np.array([0.,float(bones[-1]['length']),0.]))
    return pts, foot
rest, foot = fk(q0); base = rest[0]; rest_foot = foot - base
targets = {'standing': rest_foot, 'knee_lift': rest_foot + np.array([0.,0.,.025]), 'forward_swing': rest_foot + np.array([0.,-.025,.018]), 'landing': rest_foot + np.array([0.,-.018,.001])}
def solve(target):
    q = q0.copy()
    for _ in range(600):
        now = fk(q)[1] - base; err = target - now
        if np.linalg.norm(err) < 1e-9: break
        J = np.zeros((3,3)); eps = 1e-6
        for k in range(3):
            qt = q.copy(); qt[k] += eps; J[:,k] = (fk(qt)[1] - fk(q)[1]) / eps
        q += np.clip(J.T @ np.linalg.solve(J@J.T + 1e-8*np.eye(3), err), -.08, .08)
    pts, ft = fk(q)
    return {'q':q.tolist(), 'target':target.tolist(), 'joints':(pts-base).tolist(), 'foot':(ft-base).tolist(), 'error':float(np.linalg.norm(ft-base-target))}
result = {'status':'EXTERNAL_PINOCCHIO_SOLUTIONS','pinocchio_version':pin.__version__,'leg':d['leg'],'chain':str(src),'coordinate_frame':'MidRear.R chain-root armature frame','joint_names':[b['name'] for b in bones],'rest_metadata':{'lengths':[b['length'] for b in bones]},'poses':{n:solve(t) for n,t in targets.items()}}
Path(out).write_text(json.dumps(result,indent=2)); print(out)
