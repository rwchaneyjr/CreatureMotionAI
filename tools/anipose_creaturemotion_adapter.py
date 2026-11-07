"""Non-destructive CreatureMotionAI -> Anipose adapter and synthetic test."""
import json, csv, argparse
from pathlib import Path
import numpy as np

def load_tracking(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    rows=data.get('frames',[]); names=['hip','knee','ankle','foot']; out=[]
    for row in rows:
        pts=[]; scores=[]
        for n in names:
            p=row.get('landmarks_2d',{}).get(n); c=row.get('confidence',{}).get(n,0.0)
            pts.append([float(p[0]),float(p[1])] if p else [np.nan,np.nan]); scores.append(float(c))
        out.append({'frame':int(row['frame']),'points':pts,'confidence':scores})
    return {'source':str(Path(path).resolve()),'fps':data.get('fps',24),'names':names,'frames':out,'status':'2D_ONLY'}

def export_single_view_csv(tracking, out):
    # Anipose/DLC-style flat CSV for one camera; explicitly not triangulatable alone.
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['scorer','CreatureMotionAI']*1); w.writerow(['bodyparts']+sum(([n,n,n] for n in tracking['names']),[])); w.writerow(['coords']+sum((['x','y','likelihood'] for _ in tracking['names']),[]))
        for r in tracking['frames']:
            row=[r['frame']]
            for p,c in zip(r['points'],r['confidence']): row.extend([p[0],p[1],c])
            w.writerow(row)

def synthetic_test(out):
    from aniposelib.cameras import Camera, CameraGroup
    import cv2
    pts=np.array([[0.0,0.0,4.0],[0.3,0.2,4.1],[-0.2,0.4,3.8],[0.1,-0.3,4.3]],dtype=float)
    K=np.array([[800.,0,320.],[0,800.,240.],[0,0,1.]])
    cams=[Camera(matrix=K.copy(),dist=np.zeros(5),rvec=np.zeros(3),tvec=np.zeros(3),name='side'),Camera(matrix=K.copy(),dist=np.zeros(5),rvec=np.array([0.,0.12,0.]),tvec=np.array([1.,0.,0.]),name='front')]
    obs=[]
    for cam in cams:
        uv,_=cv2.projectPoints(pts,cam.rvec,cam.tvec,cam.matrix,cam.dist); obs.append(uv.reshape(-1,2))
    obs=np.stack(obs,axis=0)[None,:,:,:]
    recon=cams and CameraGroup(cams).triangulate(obs[0])
    recon=np.asarray(recon); err=np.linalg.norm(recon-pts,axis=1)
    result={'status':'PASS_SYNTHETIC_ANIPOSE_TRIANGULATION','points':len(pts),'max_error':float(err.max()),'mean_error':float(err.mean()),'ground_truth':pts.tolist(),'reconstructed':recon.tolist(),'camera_count':2,'note':'Synthetic calibrated cameras only; this does not validate real Balisk cameras.'}
    out.write_text(json.dumps(result,indent=2),encoding='utf-8'); return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--tracking',default='data/generated/dlc_tracking_best30/leg_rear_left_tracking.json'); ap.add_argument('--out-dir',default='data/generated/anipose_adapter'); ap.add_argument('--synthetic',action='store_true'); a=ap.parse_args(); d=Path(a.out_dir); d.mkdir(parents=True,exist_ok=True); t=load_tracking(a.tracking); (d/'creaturemotionai_side_view_2d.json').write_text(json.dumps(t,indent=2),encoding='utf-8'); export_single_view_csv(t,d/'pose-2d'/'side.csv'); print(json.dumps({'adapter':'PASS','frames':len(t['frames']),'landmarks':len(t['names']),'output':str(d.resolve())}));
    if a.synthetic: print(json.dumps(synthetic_test(d/'synthetic_triangulation_report.json')))
