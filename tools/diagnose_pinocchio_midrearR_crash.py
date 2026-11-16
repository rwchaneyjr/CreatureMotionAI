import faulthandler, json, sys
faulthandler.enable()
from pathlib import Path
import numpy as np
import pinocchio as pin

src=Path(sys.argv[1]); d=json.loads(src.read_text()); bones=d['bones']; print('LOAD',flush=True)
model=pin.Model(); parent=0
for i,b in enumerate(bones):
    rest=np.asarray(b['rest_matrix'],float); local=np.asarray(b['parent_relative_rest'],float)
    R=rest[:3,:3] if i==0 else local[:3,:3]; t=np.zeros(3) if i==0 else local[:3,3]
    axis=np.array([1.,0.,0.]); axis/=np.linalg.norm(axis)
    parent=model.addJoint(parent,pin.JointModelRevoluteUnaligned(axis),pin.SE3(R,t),b['name'])
print('MODEL nq',model.nq,'nv',model.nv,flush=True)
data=model.createData(); q=pin.neutral(model)
pin.forwardKinematics(model,data,q); print('REST_FK',data.oMi[parent].translation.tolist(),flush=True)
for i in range(3):
    qt=q.copy(); qt[i]=0.01; pin.forwardKinematics(model,data,qt); print('JOINT',i,'OK',data.oMi[parent].translation.tolist(),flush=True)
target=data.oMi[parent].translation.copy()+np.array([0.,0.,.001]); q=q.copy();
def solve3(A,b):
    a=[[float(A[i][j]) for j in range(3)]+[float(b[i])] for i in range(3)]
    for k in range(3):
        p=max(range(k,3),key=lambda i:abs(a[i][k])); a[k],a[p]=a[p],a[k]
        if abs(a[k][k])<1e-12: return [0.,0.,0.]
        z=a[k][k]; a[k]=[v/z for v in a[k]]
        for i in range(3):
            if i!=k:
                z=a[i][k]; a[i]=[a[i][j]-z*a[k][j] for j in range(4)]
    return [a[i][3] for i in range(3)]
for it in range(10):
    pin.forwardKinematics(model,data,q); now=data.oMi[parent].translation.copy(); err=target-now
    print('ITER',it,'err',float(np.linalg.norm(err)),flush=True)
    J=pin.computeJointJacobian(model,data,q,parent)[:3,:]
    print('J',J.shape,flush=True)
    jl=J.tolist(); ev=[float(x) for x in err]; A=[[sum(jl[r][k]*jl[s][k] for k in range(3))+(1e-8 if r==s else 0.0) for s in range(3)] for r in range(3)]
    y=solve3(A,ev); dq=[sum(jl[r][k]*y[r] for r in range(3)) for k in range(3)]
    for k in range(3): q[k]+=max(-.01,min(.01,dq[k]))
print('DONE',flush=True)
