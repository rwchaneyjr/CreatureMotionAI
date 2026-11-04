import cv2, json
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]; video=root/'data/reference/goodspilitbalisk.mp4'; out=root/'data/generated'
cap=cv2.VideoCapture(str(video)); fps=cap.get(cv2.CAP_PROP_FPS); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); pw=w//2
signals=[]; samples=[]; prev=None; i=0
while True:
 ok,frame=cap.read()
 if not ok: break
 left=frame[:,:pw]; right=frame[:,w-pw:]
 gl=cv2.cvtColor(left,cv2.COLOR_BGR2GRAY); gr=cv2.cvtColor(right,cv2.COLOR_BGR2GRAY)
 if prev is not None:
  signals.append({'frame':i,'left_motion':float(cv2.absdiff(gl,prev[0]).mean()),'right_motion':float(cv2.absdiff(gr,prev[1]).mean())})
 prev=(gl,gr)
 if i in [0,60,120,180,239]:
  both=np.hstack([left,right]); cv2.imwrite(str(out/f'goodspilitbalisk_compare_{i+1:04d}.png'),both); samples.append(i+1)
 i+=1
cap.release()
la=np.array([x['left_motion'] for x in signals]); ra=np.array([x['right_motion'] for x in signals]); corr=float(np.corrcoef(la,ra)[0,1]) if len(la)>2 else 0.0
best_offset=0; best=-1
for off in range(-12,13):
 a=la[max(0,off):min(len(la),len(la)+off)]; b=ra[max(0,-off):min(len(ra),len(ra)-off)]
 if len(a)>2:
  c=float(np.corrcoef(a,b)[0,1])
  if c>best:best=c;best_offset=off
report={'video':str(video),'width':w,'height':h,'fps':fps,'frames_decoded':i,'panel_width':pw,'sample_frames':samples,'motion_correlation_zero_offset':corr,'best_fixed_offset_frames':best_offset,'best_offset_motion_correlation':best,'camera_calibration':'NOT_VERIFIED','epipolar_consistency':'NOT_TESTED','decision':'UNCERTAIN','reason':'Both panels are present, but motion timing/identity and calibration are not sufficient for reliable triangulation without manual landmarks and camera measurements.','next_minimum':['annotate body center and 3-4 joints across 5 corresponding frames','measure panel crop/scale and camera intrinsics or provide calibration']}
(out/'goodspilitbalisk_suitability_report.json').write_text(json.dumps(report,indent=2))
