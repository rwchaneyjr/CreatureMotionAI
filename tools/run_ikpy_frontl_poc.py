import json,sys,math
from pathlib import Path
import numpy as np
from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

def main():
    src,out=sys.argv[1:3]
    lift_scale=float(sys.argv[3]) if len(sys.argv)>3 else 0.01
    forward_scale=float(sys.argv[4]) if len(sys.argv)>4 else 0.01
    d=json.loads(Path(src).read_text()); b=d['bones']
    root=np.array(d['chain_root_armature'],float)
    p=[np.array(x['head_armature'],float)-root for x in b]+[np.array(b[-1]['tail_armature'],float)-root]
    seg=[p[i+1]-p[i] for i in range(3)]
    # IKPy chain in the measured Blender world basis.  Each link preserves the
    # measured rest translation; the bend axis is derived from the rest chain.
    n=np.cross(seg[0],seg[1]); n=n/np.linalg.norm(n)
    # IKPy expects the terminal link to be a fixed end-effector.  The prior
    # version marked the third revolute link as terminal/active, which makes
    # IKPy 4.4.x build malformed bounds during optimization.
    links=[OriginLink(),
           URDFLink('FrontL_01',seg[0],np.zeros(3),rotation=n,bounds=(-math.pi,math.pi)),
           URDFLink('FrontL_02',seg[1],np.zeros(3),rotation=n,bounds=(-math.pi,math.pi)),
           URDFLink('FrontL_03',seg[2],np.zeros(3),rotation=n,bounds=(-math.pi,math.pi)),
           URDFLink('FrontL_end',np.zeros(3),np.zeros(3),joint_type='fixed',bounds=(0.0,0.0))]
    chain=Chain(links,active_links_mask=[False,True,True,True,False],name='CMAI_FrontL_IKPy')
    rest_target=p[-1]
    # A three-bone planar chain cannot reach an arbitrary world-Z offset if
    # world Z has a component outside its anatomical bend plane.  Use the
    # normalized projection of Blender up into that plane for the reachable
    # lift test, while recording the exact displacement vector.
    up=np.array([0.0,0.0,1.0]); plane_n=n/np.linalg.norm(n)
    lift=up-np.dot(up,plane_n)*plane_n
    if np.linalg.norm(lift)<1e-8: raise RuntimeError('Blender world up is perpendicular to the Front.L bend plane; no planar upward target exists')
    lift=lift/np.linalg.norm(lift)
    if lift[2]<0: lift=-lift
    targets={
        'lift': rest_target+lift*lift_scale,
        'high_lift': rest_target+lift*lift_scale*1.5,
    }
    # Forward motion is constrained to the measured anatomical bend plane.
    forward=seg[0]/np.linalg.norm(seg[0])
    forward=forward-np.dot(forward,plane_n)*plane_n
    forward=forward/np.linalg.norm(forward)
    targets['forward_up']=rest_target+lift*lift_scale+forward*forward_scale
    targets['forward_down']=rest_target+forward*0.003
    neutral=chain.inverse_kinematics(rest_target)
    target=targets['lift']
    moved=chain.inverse_kinematics(target,initial_position=neutral)
    neutral_all=np.asarray(chain.forward_kinematics(neutral,full_kinematics=True)); moved_all=np.asarray(chain.forward_kinematics(moved,full_kinematics=True))
    neutral_fk=neutral_all[-1,:3,3]; moved_fk=moved_all[-1,:3,3]
    tests=[]
    rest_fk=np.asarray(chain.forward_kinematics(neutral,full_kinematics=True))
    rest_rot=rest_fk[-1,:3,:3]
    # Endpoint-only IK can leave the proximal joint at zero and rotate the
    # terminal segment. Solve position and terminal orientation together,
    # with a narrow configurable terminal orientation allowance.
    def constrained_solution(target, initial):
        def residual(q):
            fk=np.asarray(chain.forward_kinematics(q,full_kinematics=True))
            pos=(fk[-1,:3,3]-target)/0.01
            rel=rest_rot.T @ fk[-1,:3,:3]
            ori=Rotation.from_matrix(rel).as_rotvec()/0.03
            prior=np.array([q[1], q[2], q[3]])*0.05
            return np.r_[pos, ori, prior]
        return least_squares(residual, initial, bounds=([-1e-9,-1.5,-1.5,-0.15,-1e-9],[1e-9,1.5,1.5,0.15,1e-9]), max_nfev=500).x
    for name,t in targets.items():
        sol=constrained_solution(t, chain.inverse_kinematics(t,initial_position=neutral))
        mats=np.asarray(chain.forward_kinematics(sol,full_kinematics=True))
        endpoint=mats[-1,:3,3]
        tests.append({'name':name,'target':t.tolist(),'solution':sol.tolist(),'joint_matrices':mats.tolist(),'fk_endpoint':endpoint.tolist(),'error':float(np.linalg.norm(endpoint-t)),'pass':bool(np.linalg.norm(endpoint-t)<0.0001)})
    report={'status':'IKPY_NUMERICAL_MULTI_TARGET_POC','chain':'Front.L','coordinate_system':'armature-local chain-root','chain_root_armature':root.tolist(),'bones':[x['name'] for x in b],'bend_plane_normal':plane_n.tolist(),'lift_direction':lift.tolist(),'forward_direction':forward.tolist(),'rest_target':rest_target.tolist(),'neutral_solution':neutral.tolist(),'neutral_joint_matrices':neutral_all.tolist(),'neutral_error':float(np.linalg.norm(neutral_fk-rest_target)),'tests':tests,'fk_tolerance':0.0001,'note':'Each target has an independent IKPy solution and forward-kinematics validation.'}
    Path(out).write_text(json.dumps(report,indent=2)); print(json.dumps(report))
if __name__=='__main__': main()
