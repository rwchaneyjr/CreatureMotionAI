import json, sys, math
from pathlib import Path
import numpy as np
import pinocchio as pin

src,out=sys.argv[1:3]
d=json.loads(Path(src).read_text()); bones=d['bones']; model=pin.Model(); parent=0
for i,b in enumerate(bones):
    rest=np.asarray(b['rest_matrix'],float); local=np.asarray(b['parent_relative_rest'],float)
    R=rest[:3,:3] if i==0 else local[:3,:3]; t=np.zeros(3) if i==0 else local[:3,3]
    parent=model.addJoint(parent,pin.JointModelRevoluteUnaligned(np.array([1.,0.,0.])),pin.SE3(R,t),b['name'])
data=model.createData(); q0=pin.neutral(model)
def fk(q):
    pin.forwardKinematics(model,data,np.asarray(q,float)); p=np.asarray(data.oMi[parent].translation,float)
    return p+np.asarray(data.oMi[parent].rotation,float).dot(np.array([0.,float(bones[-1]['length']),0.]))
base=fk(q0); rest=base.copy(); targets={'knee_lift':rest+np.array([0.,0.,.025]),'forward_swing':rest+np.array([0.,-.025,.018]),'landing':rest+np.array([0.,-.018,.001])}
def norm(v): return math.sqrt(sum(x*x for x in v))
def solve3(A,b):
    a=[[float(A[i][j]) for j in range(3)]+[float(b[i])] for i in range(3)]
    for k in range(3):
        p=max(range(k,3),key=lambda i:abs(a[i][k])); a[k],a[p]=a[p],a[k]
        if abs(a[k][k])<1e-10:return [0.,0.,0.]
        z=a[k][k]; a[k]=[x/z for x in a[k]]
        for i in range(3):
            if i!=k:
                z=a[i][k]; a[i]=[a[i][j]-z*a[k][j] for j in range(4)]
    return [a[i][3] for i in range(3)]
def jac(q):
    eps=1e-5; j=[[0.,0.,0.] for _ in range(3)]
    for k in range(3):
        qp=list(q); qm=list(q); qp[k]+=eps; qm[k]-=eps; p=fk(qp); m=fk(qm)
        for r in range(3): j[r][k]=float((p[r]-m[r])/(2*eps))
    return j

def solve(target):
    q=list(q0); initial=norm([target[i]-fk(q)[i] for i in range(3)]); hist=[]
    for it in range(200):
        now=fk(q); e=[target[i]-now[i] for i in range(3)]; err=norm(e); hist.append(err)
        if err<1e-6: break
        J=jac(q); A=[[sum(J[r][k]*J[s][k] for k in range(3))+(0.02 if r==s else 0.) for s in range(3)] for r in range(3)]
        y=solve3(A,e); dq=[sum(J[r][k]*y[r] for r in range(3)) for k in range(3)]
        accepted=False
        for scale in (1.,.5,.25,.125,.0625,.03125):
            cand=[max(-1.2,min(1.2,q[k]+scale*dq[k])) for k in range(3)]
            ce=norm([target[i]-fk(cand)[i] for i in range(3)])
            if ce < err: q=cand; accepted=True; break
        if not accepted: break
    final=norm([target[i]-fk(q)[i] for i in range(3)])
    return {'q':q,'initial_error':initial,'final_error':final,'iterations':len(hist),'monotonic':all(hist[i+1]<=hist[i]+1e-12 for i in range(len(hist)-1)),'history':hist,'pass':final<1e-4}

axis_tests=[]
for k in range(3):
    for sign in (-1,1):
        q=list(q0); q[k]=sign*.01; axis_tests.append({'joint':k,'sign':sign,'foot_delta':(fk(q)-base).tolist()})
report={'status':'DAMPED_PINOCCHIO_TEST','pinocchio_version':pin.__version__,'leg':d['leg'],'axis_tests':axis_tests,'poses':{name:solve(target) for name,target in targets.items()},'solver':'pure_python_damped_line_search','numpy_linear_solve_used':False}
Path(out).write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
