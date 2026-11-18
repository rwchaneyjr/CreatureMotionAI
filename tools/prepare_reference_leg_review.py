import json, sys
from pathlib import Path
import cv2

root, video, approved, raw, out_dir = map(Path, sys.argv[1:6])
frame = int(sys.argv[6]); out_dir.mkdir(parents=True, exist_ok=True)
cap = cv2.VideoCapture(str(video)); cap.set(cv2.CAP_PROP_POS_FRAMES, frame - 1)
ok, image = cap.read(); cap.release()
if not ok: raise RuntimeError(f'Could not read frame {frame}: {video}')
panel = image[:, :image.shape[1] // 2].copy()
pred = json.loads(raw.read_text())
chosen = [frame]
clear_file = out_dir / 'clear_frames.json'
if clear_file.exists():
    chosen = [int(x['frame']) for x in json.loads(clear_file.read_text()).get('selected_frames', [])] or chosen
points = {}
rows=[]
for selected in chosen:
    cap=cv2.VideoCapture(str(video)); cap.set(cv2.CAP_PROP_POS_FRAMES,selected-1); ok,image=cap.read(); cap.release()
    if not ok: continue
    panel=image[:,:image.shape[1]//2].copy(); item=next(x for x in pred['frames'] if int(x['frame'])==selected); points={}
    for name in ('hip','knee','ankle','foot'):
        xy=item['landmarks_2d'][name]; points[f'Leg_Reference_{name}']={'x':float(xy[0]),'y':float(xy[1]),'visible':True,'state':'model_prediction','confidence':float(item['confidence'].get(name,0.0)),'source':'DeepLabCut_raw'}
    ordered=[points[f'Leg_Reference_{n}'] for n in ('hip','knee','ankle','foot')]
    for a,b in zip(ordered,ordered[1:]): cv2.line(panel,(int(a['x']),int(a['y'])),(int(b['x']),int(b['y'])),(0,180,255),3,cv2.LINE_AA)
    for name,p in zip(('hip','knee','ankle','foot'),ordered):
        q=(int(p['x']),int(p['y'])); cv2.circle(panel,q,8,(0,180,255),-1,cv2.LINE_AA); cv2.putText(panel,f'{name} (UNVERIFIED)',(q[0]+8,q[1]-6),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,80,160),1,cv2.LINE_AA)
    cv2.imwrite(str(out_dir / f'frame_{selected:06d}_camera_A.png'), panel)
    rows.append({'frame':selected,'camera_A':{'landmarks':points}})
payload={'status':'UNVERIFIED_REFERENCE_LEG_REVIEW','source_video':str(video),'panel':'side','frame':frame,'selected_frames':chosen,'identity':'UNVERIFIED','identity_options':['UNVERIFIED','Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R'],'frames':rows,'backup_of':str(approved),'notes':'Raw DLC points are editable. Approval is separate from original approved labels.'}
(out_dir/'reference_leg_review.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
print(out_dir/'reference_leg_review.json')
