import json, cv2
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]; p=root/'data/generated/two_view_landmark_annotations.json'; report={'status':'UNCERTAIN','frames':{},'reason':'Need at least 8 distinct valid paired correspondences overall.'}; pairs=[]
if p.exists():
 data=json.loads(p.read_text())
 for frame,items in data.get('frames',{}).items():
  valid=[v for v in items.values() if v.get('visible') and len(v.get('front_uv',[]))==2 and len(v.get('side_uv',[]))==2]; report['frames'][frame]={'pairs':len(valid)}; pairs.extend((frame,v) for v in valid)
if len(pairs)>=8:
 a=np.float32([v['front_uv'] for _,v in pairs]); b=np.float32([v['side_uv'] for _,v in pairs])
 if np.linalg.matrix_rank(a-a.mean(0))>=2 and np.linalg.matrix_rank(b-b.mean(0))>=2:
  F,mask=cv2.findFundamentalMat(a,b,cv2.FM_RANSAC,1.5,.99); report.update({'pooled_pairs':len(pairs),'inliers':int(mask.sum()) if mask is not None else 0,'inlier_ratio':float(mask.mean()) if mask is not None else 0.0,'fundamental_matrix':F.tolist() if F is not None else None}); report['decision']='PASS' if report['inlier_ratio']>=.6 else 'UNCERTAIN'
 else: report['reason']='Correspondences are geometrically degenerate.'; report['decision']='UNCERTAIN'
else: report['decision']='UNCERTAIN'
(root/'data/generated/two_view_geometric_consistency_report.json').write_text(json.dumps(report,indent=2))
