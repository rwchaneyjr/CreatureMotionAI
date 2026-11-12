import json, math, sys
from pathlib import Path
import numpy as np
import pinocchio as pin

def mat(x): return np.asarray(x,float)
def main():
    src,out=sys.argv[1:3]; d=json.loads(Path(src).read_text()); bones=d['bones']; root=np.asarray(d['chain_root_armature'],float)
    # Parent-relative rest matrices are the authoritative Blender transforms.
    rel=[mat(b['parent_relative_rest']) for b in bones]
    absolute_r01=mat(bones[0]['rest_matrix'])[:3,:3]
    lengths=[float(b['length']) for b in bones]
    model=pin.Model(); parent=0
    for i in range(3):
        R=(absolute_r01 if i==0 else rel[i][:3,:3]); t=np.zeros(3) if i==0 else rel[i][:3,3]
        # Blender's measured joint tests show local X is the effective
        # articulated axis for this chain; rest roll is retained in placement.
        jid=model.addJoint(parent,pin.JointModelRevoluteUnaligned(np.array([1.,0.,0.])),pin.SE3(R,t),f'L0{i+1}')
        parent=jid
    data_fk=model.createData(); q=pin.neutral(model)
    def endpoint(qv):
        pin.forwardKinematics(model,data_fk,qv)
        return np.asarray(data_fk.oMi[parent].translation + data_fk.oMi[parent].rotation.dot(np.array([0.,lengths[2],0.])))
    world_delta=np.asarray(bones[-1]['tail_armature'],float)-np.asarray(bones[0]['head_armature'],float)
    # The Pinocchio model output is expressed in the chain-root armature
    # frame with the L01 rest orientation already in its first placement.
    rest_expected=world_delta
    # With parent-relative placements the endpoint is chain-root relative.
    rest=endpoint(q); rest_error=float(np.linalg.norm(rest-rest_expected))
    # Targets are deliberately local to the corrected chain-root frame.
    lift=np.array([0.,0.,0.010]); forward=np.array([0.,-0.010,0.])
    targets={'rest':rest_expected,'lift':rest_expected+lift,'forward_up':rest_expected+lift*0.6+forward}
    rows=[]
    for name,target in targets.items():
        qx=q.copy()
        for _ in range(150):
            now=endpoint(qx); err=target-now
            if np.linalg.norm(err)<1e-9: break
            J=np.zeros((3,3)); eps=1e-6
            for k in range(3):
                qt=qx.copy(); qt[k]+=eps; J[:,k]=(endpoint(qt)-now)/eps
            dq=J.T@np.linalg.solve(J@J.T+1e-9*np.eye(3),err); qx+=np.clip(dq,-0.1,0.1)
        end=endpoint(qx); rows.append({'name':name,'target':target.tolist(),'q_revolute':qx.tolist(),'endpoint':end.tolist(),'error':float(np.linalg.norm(end-target)),'pass':bool(np.linalg.norm(end-target)<1e-4)})
    sweep=[]
    for frac in [0.25,0.5,0.75,1.0]:
        target=rest_expected+lift*0.6+forward*frac; starts=[q.copy(),np.array([0.1,-0.1,0.1]),np.array([-0.2,0.2,-0.2])]
        trials=[]
        for start in starts:
            qx=start.copy()
            for _ in range(250):
                now=endpoint(qx); err=target-now
                if np.linalg.norm(err)<1e-9: break
                J=np.zeros((3,3)); eps=1e-6
                for k in range(3):
                    qt=qx.copy(); qt[k]+=eps; J[:,k]=(endpoint(qt)-now)/eps
                qx += np.clip(J.T@np.linalg.solve(J@J.T+1e-9*np.eye(3),err),-0.1,0.1)
            trials.append({'start':start.tolist(),'q':qx.tolist(),'endpoint':endpoint(qx).tolist(),'error':float(np.linalg.norm(endpoint(qx)-target)),'pass':bool(np.linalg.norm(endpoint(qx)-target)<1e-4)})
        sweep.append({'forward_fraction':frac,'target':target.tolist(),'trials':trials})
    grid=[]
    for lift_h in [0.0,0.003,0.006,0.009]:
        for frac in [0.25,0.5,0.75,1.0]:
            target=rest_expected+lift*lift_h/0.006+forward*frac
            qx=q.copy()
            for _ in range(300):
                now=endpoint(qx); err=target-now
                if np.linalg.norm(err)<1e-9: break
                J=np.zeros((3,3)); eps=1e-6
                for k in range(3):
                    qt=qx.copy(); qt[k]+=eps; J[:,k]=(endpoint(qt)-now)/eps
                qx += np.clip(J.T@np.linalg.solve(J@J.T+1e-9*np.eye(3),err),-0.1,0.1)
            grid.append({'lift_height':lift_h,'forward_fraction':frac,'target':target.tolist(),'q':qx.tolist(),'endpoint':endpoint(qx).tolist(),'error':float(np.linalg.norm(endpoint(qx)-target)),'pass':bool(np.linalg.norm(endpoint(qx)-target)<1e-4)})
    report={'status':'PINOCCHIO_PARENT_RELATIVE_REACH_GRID','source_chain':src,'pinocchio_version':getattr(pin,'__version__','unknown'),'translations':[r[:3,3].tolist() for r in rel],'rest_expected':rest_expected.tolist(),'rest_fk':rest.tolist(),'rest_fk_error':rest_error,'rest_pass':rest_error<1e-4,'tests':rows,'forward_sweep':sweep,'reach_grid':grid,'forward_vector':forward.tolist(),'blender_application':'NOT_PERFORMED','note':'Root transformation preserved; no rig or animation modified.'}
    Path(out).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
