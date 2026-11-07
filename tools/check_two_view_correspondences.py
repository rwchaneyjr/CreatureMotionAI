import argparse, json, cv2, numpy as np
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
    d=json.loads(Path(a.input).read_text(encoding='utf-8')); rows=[]
    for frame,items in d.get('frames',{}).items():
        for x in items:
            if x.get('approval_status')=='manual_verified' and x.get('visible',True): rows.append((int(frame),x))
    result={'status':'UNCERTAIN','input':str(Path(a.input).resolve()),'valid_pairs':len(rows),'frames':sorted(set(f for f,_ in rows)),'fundamental_matrix':None,'inliers':0,'outliers':0,'epipolar_residual_px':None,'note':'At least eight distributed manual pairs are required; a fundamental matrix is only a consistency test, not metric calibration.'}
    if len(rows)>=8:
        p1=np.float32([x['side_px'] for _,x in rows]); p2=np.float32([x['front_px'] for _,x in rows]); F,mask=cv2.findFundamentalMat(p1,p2,cv2.FM_RANSAC,1.0,.99)
        if F is not None and mask is not None:
            result['fundamental_matrix']=F.tolist(); result['inliers']=int(mask.sum()); result['outliers']=int(len(mask)-mask.sum()); result['status']='PASS_CONSISTENCY_CHECK' if result['inliers']>=8 else 'UNCERTAIN'
    Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result))
if __name__=='__main__': main()
