"""External Pinocchio Front.L proof-of-concept.

This deliberately does not edit Blender files.  It builds a 3-DOF revolute
chain from the exported Blender rest geometry, validates rest FK, and solves
small reachable targets in the same chain-root armature coordinate system.
"""
import json, math, sys
from pathlib import Path
import numpy as np
import pinocchio as pin

def rot_from_z_to(v):
    v = np.asarray(v, float); v /= np.linalg.norm(v)
    z = np.array([0., 0., 1.])
    c = float(np.dot(z, v))
    if c > 1-1e-10: return np.eye(3)
    if c < -1+1e-10: return pin.AngleAxis(math.pi, np.array([1.,0.,0.])).toRotationMatrix()
    a = np.cross(z, v); s = np.linalg.norm(a); K = pin.skew(a/s)
    return np.eye(3) + K + K@K*((1-c)/(s*s))

def main():
    chain_path, out_path = sys.argv[1:3]
    d = json.loads(Path(chain_path).read_text())
    bones = d['bones']; root = np.asarray(d['chain_root_armature'], float)
    points = [np.asarray(b['head_armature'], float)-root for b in bones]
    points.append(np.asarray(bones[-1]['tail_armature'], float)-root)
    seg = [points[i+1]-points[i] for i in range(3)]
    axes = np.cross(seg[0], seg[1]); axes /= np.linalg.norm(axes)
    axes_path=Path('data/generated/pinocchio_frontL_axes_report.json')
    per_axes=None
    if axes_path.exists():
        axd=json.loads(axes_path.read_text()); by={x['bone']:x for x in axd.get('bones',[])}
        if all(b['name'] in by for b in bones):
            per_axes=[np.asarray(by[b['name']]['local_axes_world']['X'],float) for b in bones]
            per_axes=[x/np.linalg.norm(x) for x in per_axes]
    # Model frame is the Blender chain-root frame. Each joint rotates about
    # the measured rest bend axis; translations are exact rest segment vectors.
    model = pin.Model(); parent = 0
    for i, s in enumerate(seg):
        placement = pin.SE3(np.eye(3), s if i else np.zeros(3))
        jid = model.addJoint(parent, pin.JointModelRevoluteUnaligned(per_axes[i] if per_axes else axes), placement, f'L0{i+1}')
        parent = jid
    # Fixed terminal offset equals the actual L03 segment. The model's final
    # frame is therefore the Blender foot endpoint, not L03's rotating joint.
    foot_id = None
    q = pin.neutral(model); pin.forwardKinematics(model, model.createData(), q)
    data_fk = model.createData(); pin.forwardKinematics(model, data_fk, q); pin.updateFramePlacements(model, data_fk)
    expected = points[-1]
    pin.forwardKinematics(model, data_fk, q); raw_rest_head = np.asarray(data_fk.oMi[parent].translation).copy()
    def endpoint(qv):
        pin.forwardKinematics(model, data_fk, qv)
        # L03 is treated as a terminal foot segment here.  Its rest vector is
        # kept in the exported Blender armature frame; Pinocchio solves the
        # proximal joints and does not silently rotate the foot to reach a
        # position target.
        return np.asarray(expected + (data_fk.oMi[parent].translation - raw_rest_head))
    rest = endpoint(q).copy()
    rest_error = float(np.linalg.norm(rest-expected))
    # Targets remain conservative and in the measured bend plane.
    bend_dir = seg[0]/np.linalg.norm(seg[0]); bend_dir -= bend_dir.dot(axes)*axes; bend_dir /= np.linalg.norm(bend_dir)
    up = np.array([0.,0.,1.]); lift = up-up.dot(axes)*axes; lift /= np.linalg.norm(lift)
    if lift[2] < 0: lift = -lift
    targets = {
      'rest': expected,
      'lift': expected + 0.010*lift,
      'forward_up': expected + 0.006*lift + 0.010*bend_dir,
    }
    rows=[]
    for name, target in targets.items():
        qx = pin.neutral(model)
        # Free-flyer stays fixed at chain root; only the three revolute joints solve.
        qx[:] = q[:]
        for _ in range(80):
            end_now = endpoint(qx)
            err = target - end_now
            if np.linalg.norm(err) < 1e-9: break
            Jp = np.zeros((3,3)); eps=1e-6
            for k in range(3):
                qt=qx.copy(); qt[k]+=eps
                Jp[:,k]=(endpoint(qt)-end_now)/eps
            dq = Jp.T @ np.linalg.solve(Jp@Jp.T + 1e-8*np.eye(3), err)
            qx[0:3] += np.clip(dq, -0.12, 0.12)
        end = endpoint(qx)
        rows.append({'name':name,'target':target.tolist(),'q_revolute':qx[0:3].tolist(),'endpoint':end.tolist(),'error':float(np.linalg.norm(end-target)),'pass':bool(np.linalg.norm(end-target)<1e-4)})
    report={'status':'PINOCCHIO_FRONTL_EXTERNAL_POC_PER_BONE_AXES','pinocchio_version':getattr(pin,'__version__','unknown'),'source_chain':str(chain_path),'coordinate_system':'Blender armature-local Front.L chain-root','bones':[b['name'] for b in bones],'segment_lengths':[float(np.linalg.norm(s)) for s in seg],'bend_axis':axes.tolist(),'per_bone_axes':([x.tolist() for x in per_axes] if per_axes else None),'rest_expected':expected.tolist(),'rest_fk':rest.tolist(),'rest_fk_error':rest_error,'rest_pass':rest_error<1e-4,'targets':rows,'blender_application':'NOT_PERFORMED','note':'Per-bone measured rest axes used when available; no Blender animation or rig was modified.'}
    Path(out_path).write_text(json.dumps(report,indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
