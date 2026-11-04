import json, cv2
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]; p=root/'data/generated/two_view_landmark_annotations.json'; report={'status':'UNCERTAIN','frames':{},'reason':'Need at least 8 valid paired correspondences per frame for robust fundamental-matrix testing.'}
if p.exists():
 data=json.loads(p.read_text())
 for frame,items in data.get('frames',{}).items():
  pairs=[v for v in items.values() if v.get('visible') and len(v.get('front_uv',[]))==2 and len(v.get('side_uv',[]))==2]
  if len(pairs)>=8:
   a=np.float32([x['front_uv'] for x in pairs]); b=np.float32([x['side_uv'] for x in pairs]); F,mask=cv2.findFundamentalMat(a,b,cv2.FM_RANSAC,1.5,.99); report['frames'][frame]={'pairs':len(pairs),'inliers':int(mask.sum()) if mask is not None else 0,'inlier_ratio':float(mask.mean()) if mask is not None else 0.0,'fundamental_matrix':F.tolist() if F is not None else None}
  else: report['frames'][frame]={'pairs':len(pairs),'status':'INSUFFICIENT_CORRESPONDENCES'}
report['decision']='PASS' if report['frames'] and all(x.get('inlier_ratio',0)>=.6 for x in report['frames'].values() if 'inlier_ratio' in x) and all(x.get('pairs',0)>=8 for x in report['frames'].values()) else 'UNCERTAIN'
(root/'data/generated/two_view_geometric_consistency_report.json').write_text(json.dumps(report,indent=2))
