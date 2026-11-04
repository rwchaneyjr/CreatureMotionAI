import json, math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
root=Path(r'C:\Users\rober\CreatureMotionAI')
cal=json.loads((root/'data/generated/single_camera_camera_calibration_annotations.json').read_text())
cand=json.loads((root/'data/generated/body_landmark_3d_selected.json').read_text())
names=['body_center','head_snout','tail_base','body_length_reference']
P=np.array([cand['points'][n] for n in names],float); frames=[1,61,121,181,240]
Y=np.array([[cal['frames'][str(f)][n]['uv'] for n in names] for f in frames],float)
def pred(x):
    R=Rotation.from_rotvec(x[:3]).as_matrix(); q=(R@P.T).T; s=math.exp(x[3]); base=q[:,:2]*s; tr=x[4:].reshape(len(frames),2); return base[None,:,:]+tr[:,None,:]
def fun(x): return (pred(x)-Y).ravel()
x0=np.zeros(4+2*len(frames)); x0[3]=math.log(2.0); x0[4::2]=320; x0[5::2]=360
r=least_squares(fun,x0,max_nfev=10000); pr=pred(r.x); errs=np.linalg.norm(pr-Y,axis=2)
report={'status':'MOTION_AWARE_CAMERA_DIAGNOSTIC','used_landmarks':names,'ground_contact_excluded':True,'estimated_camera':{'rotation_vector':r.x[:3].tolist(),'scale':math.exp(r.x[3])},'estimated_frame_translations':{str(f):r.x[4+2*i:6+2*i].tolist() for i,f in enumerate(frames)},'frame_errors':{str(f):{'mean_px':float(e.mean()),'max_px':float(e.max()),'per_landmark_px':e.tolist()} for f,e in zip(frames,errs)},'overall_rms_px':float(np.sqrt(np.mean((pr-Y)**2))),'interpretation':'This separates fixed camera parameters from per-frame body translation; it does not recover per-frame joint pose or metric depth.','leg_fit':'NOT_STARTED'}
(root/'data/generated/motion_aware_camera_fit_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'overall_rms_px':report['overall_rms_px'],'frames':{k:(v['mean_px'],v['max_px']) for k,v in report['frame_errors'].items()}},indent=2))
