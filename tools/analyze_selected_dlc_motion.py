import argparse,json
from pathlib import Path
import numpy as np
try:
 from scipy.signal import find_peaks
except Exception: find_peaks=None

def d(a,b): return float(np.linalg.norm(np.asarray(a)-np.asarray(b)))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('pred',type=Path); ap.add_argument('manual',type=Path); ap.add_argument('out',type=Path); a=ap.parse_args()
 p=json.loads(a.pred.read_text()); m=json.loads(a.manual.read_text()); rows=[]
 for row in p['frames']:
  f=int(row['frame']); pts=row['landmarks_2d']; conf=row['confidence']; vals={k:pts[k] for k in pts}
  ls=[d(vals[x],vals[y]) for x,y in [('hip','knee'),('knee','ankle'),('ankle','foot')] if x in vals and y in vals]
  c=np.mean(list(conf.values())); valid=bool(c>=.6 and len(ls)==3 and max(ls)/max(min(ls),1e-6)<3.5)
  rows.append({'frame':f,'mean_confidence':round(float(c),4),'bone_lengths_px':[round(x,3) for x in ls],'bone_ratio':round(max(ls)/max(min(ls),1e-6),3) if ls else None,'classification':'RELIABLE' if valid else ('UNCERTAIN' if c>=.35 else 'REJECTED'),'points':vals,'confidence':conf})
 reliable=[r for r in rows if r['classification']=='RELIABLE'];
 ranges=[]
 for typ in ('RELIABLE','UNCERTAIN','REJECTED'):
  fs=[r['frame'] for r in rows if r['classification']==typ]; seg=[]
  for f in fs:
   if not seg or f!=seg[-1][-1]+1: seg.append([f])
   else: seg[-1].append(f)
  ranges.append({'classification':typ,'ranges':[[x[0],x[-1]] for x in seg]})
 def extreme(key,fun): return min(reliable,key=lambda r:fun(r['points'][key][0])) if reliable else None
 report={'status':'DLC_MOTION_ANALYSIS','source':str(a.pred),'frames':240,'reliable_count':len(reliable),'uncertain_count':sum(r['classification']=='UNCERTAIN' for r in rows),'rejected_count':sum(r['classification']=='REJECTED' for r in rows),'frame_ranges':ranges,'extremes':{'foot_forward_x_max':max(reliable,key=lambda r:r['points']['foot'][0]) if reliable else None,'foot_backward_x_min':min(reliable,key=lambda r:r['points']['foot'][0]) if reliable else None,'foot_lift_y_min':min(reliable,key=lambda r:r['points']['foot'][1]) if reliable else None,'foot_low_y_max':max(reliable,key=lambda r:r['points']['foot'][1]) if reliable else None,'knee_high_y_min':min(reliable,key=lambda r:r['points']['knee'][1]) if reliable else None,'knee_low_y_max':max(reliable,key=lambda r:r['points']['knee'][1]) if reliable else None},'complete_pose_candidates':[r for r in reliable if all(k in r['points'] for k in ('hip','knee','ankle','foot'))][:40],'manual_seed_frames':[1,25,49,73],'manual_identity':'Front.L remains user-confirmed but not independently proven','metric_3d':'UNAVAILABLE','animation_generated':False}
 a.out.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps({'out':str(a.out),'reliable':len(reliable),'uncertain':report['uncertain_count'],'rejected':report['rejected_count'],'ranges':ranges},indent=2))
if __name__=='__main__': main()
