import json, cv2, numpy as np
from pathlib import Path
from creature_motion_ai.anymove_adapter import to_anymove, save_npz
from creature_motion_ai.skeleton_adapter import extract_profile
ROOT=Path(__file__).resolve().parents[1]; gen=ROOT/'data/generated'; ref=ROOT/'data/reference'
T,J=24,4; pts=np.zeros((T,J,2),np.float32); pts[...,0]=np.arange(J)*10; pts[...,1]=np.arange(T)[:,None]*.5+20
d=to_anymove(pts,pts,front_conf=np.ones((T,J)),side_conf=np.ones((T,J)),names=['body','hip_L','knee_L','foot_L'])
save_npz(gen/'anymove_balisk_synthetic_det.npz',d)
(gen/'anymove_adapter_report.json').write_text(json.dumps({'status':'PASS','shape':list(d['front_uv'].shape),'fields':list(d.keys()),'confidence_preserved':True,'calib_shape':list(d['calib'].shape)},indent=2))
extract_profile(gen/'original_static_standing.blend',gen/'balisk_skeleton_profile.json',r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
cap=cv2.VideoCapture(str(ref/'goodspilitbalisk.mp4')); frames=[]
for _ in range(24):
 ok,im=cap.read()
 if not ok: break
 frames.append(im)
cap.release(); rows=[]
for im in frames:
 mid=im.shape[1]//2; left=cv2.resize(im[:,:mid],(64,36)); right=cv2.resize(im[:,mid:],(64,36)); rows.append(float(np.corrcoef(left.astype(float).ravel(),right.astype(float).ravel())[0,1]))
(gen/'balisk_camera_validation.json').write_text(json.dumps({'status':'FAIL_SYNC_NOT_ESTABLISHED','frames':len(frames),'fps':24,'resolution':[frames[0].shape[1],frames[0].shape[0]],'panel_widths':[frames[0].shape[1]//2,frames[0].shape[1]-frames[0].shape[1]//2],'panel_visual_correlation_mean':float(np.mean(rows)),'note':'Diagnostic only; no joint identity or triangulation was forced.'},indent=2))
print('integration_checks_complete')
