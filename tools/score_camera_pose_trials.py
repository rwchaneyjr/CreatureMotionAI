import json,sys
from pathlib import Path
import cv2,numpy as np
out=Path(sys.argv[1]); data=json.loads((out/'pose_trials.json').read_text())
for row in data['trials']:
 row['views']={}
 for view in ('side','front'):
  if not (out/(view+'_reference_mask.png')).exists(): continue
  ref=cv2.imread(str(out/(view+'_reference_mask.png')),0)>0
  model=cv2.imread(str(out/f'pose_{row["candidate"]}_{view}.png'),0)>100
  iou=float((ref&model).sum()/max(1,(ref|model).sum()))
  row['views'][view]={'full_silhouette_iou':iou,'joint_reprojection_error':None,'joint_correspondence':'UNVERIFIED'}
base=data['trials'][0]
for row in data['trials']:
 row['side_iou_delta']=row['views']['side']['full_silhouette_iou']-base['views']['side']['full_silhouette_iou']
data.update(status='NOT ACCEPTED',best_by_side_silhouette=max(data['trials'],key=lambda x:x['views']['side']['full_silhouette_iou'])['candidate'],mesh_collisions='NOT TESTED; no candidate accepted',ground_contact='NOT VALIDATED',reason='Bounded IK hypotheses rendered. Silhouette alone cannot establish joint identity or a safe reconstruction. Reference frames treated independently; front pose compatibility unverified.')
(out/'pose_comparison_report.json').write_text(json.dumps(data,indent=2)); print(json.dumps(data,indent=2))
