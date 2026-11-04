import json, math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

root=Path(r'C:\Users\rober\CreatureMotionAI')
cal=json.loads((root/'data/generated/single_camera_camera_calibration_annotations.json').read_text())
cand=json.loads((root/'data/generated/body_landmark_3d_candidates.json').read_text())
leg=json.loads((root/'data/generated/single_camera_verified_leg_landmarks.json').read_text())
names=['body_center','head_snout','tail_base','body_length_reference']
P=np.array([cand['points'][n] for n in names],float)
frames=[1,61,121,181,240]
Y={f:np.array([cal['frames'][str(f)][n]['uv'] for n in names],float) for f in frames}

def project(x, pts=P):
    R=Rotation.from_rotvec(np.array(x[:3])).as_matrix()
    q=(R@pts.T).T
    s=math.exp(x[3])
    return q[:,:2]*s+np.array(x[4:6])

def fun(x): return (project(x)-Y[1]).ravel()
best=None
for seed in range(12):
    x0=np.array([0.0,0.0,0.0,math.log(2.0),320.0,360.0])
    x0[:3]=np.random.default_rng(seed).normal(0,.3,3)
    r=least_squares(fun,x0,max_nfev=5000)
    if best is None or np.linalg.norm(r.fun)<np.linalg.norm(best.fun): best=r
x=best.x
per={}
for f in frames:
    pred=project(x); err=np.linalg.norm(pred-Y[f],axis=1)
    per[str(f)]={'observed_uv':Y[f].tolist(),'predicted_uv':pred.tolist(),'per_landmark_px':err.tolist(),'mean_px':float(err.mean()),'max_px':float(err.max())}
report={'status':'CALIBRATION_DIAGNOSTIC','used_landmarks':names,'excluded_landmark':'ground_contact','model':'fixed orthographic projection with rotation vector, scale, and 2D translation','estimated':{'rotation_vector':x[:3].tolist(),'scale':float(math.exp(x[3])),'translation_uv':x[4:6].tolist()},'assumptions':['rig-derived candidate points are treated as fixed world points for the diagnostic','orthographic side-view model','no body pose change is modeled'],'frame_errors':per,'frame1_rms_px':float(np.sqrt(np.mean(best.fun**2))),'frame1_max_px':float(np.max(np.linalg.norm(best.fun.reshape(-1,2),axis=1))),'independence_note':'Four points provide eight scalar observations, but the fit is still sensitive to collinearity and body-motion/model-point uncertainty. Cross-frame residuals test that assumption.','leg_fit':'BLOCKED pending camera usability; ground-contact constraint excluded'}
(root/'data/generated/four_point_camera_fit_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'frame1_rms_px':report['frame1_rms_px'],'frame_errors':{k:(v['mean_px'],v['max_px']) for k,v in per.items()}},indent=2))
