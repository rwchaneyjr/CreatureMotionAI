import argparse,json
from pathlib import Path
import cv2, numpy as np

C={'hip':(0,0,255),'knee':(0,165,255),'ankle':(0,200,80),'foot':(255,80,0)}
def dist(a,b): return float(np.linalg.norm(np.array(a)-np.array(b)))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('video',type=Path); ap.add_argument('pred',type=Path); ap.add_argument('seeds',type=Path); ap.add_argument('out',type=Path); args=ap.parse_args()
 p=json.loads(args.pred.read_text()); s=json.loads(args.seeds.read_text()); seeds={int(f):v for f,v in s['landmarks'].items() if any(x.get('approval')=='MANUALLY_APPROVED' for x in v.values())}
 frames=sorted(map(int,p['predicted_landmarks'])); cap=cv2.VideoCapture(str(args.video)); results={}; tiles=[]
 for f in frames:
  pts=p['predicted_landmarks'][str(f)]; vals={k:(v['x'],v['y']) for k,v in pts.items() if v.get('x') is not None}; conf=float(np.mean([v.get('confidence',0) for v in pts.values()])) if pts else 0
  lengths=[dist(vals[a],vals[b]) for a,b in [('hip','knee'),('knee','ankle'),('ankle','foot')] if a in vals and b in vals]
  jump=None; nearest=min(seeds,key=lambda x:abs(x-f)) if seeds else None
  if nearest is not None and abs(nearest-f)<=25:
   sp=seeds[nearest]; ds=[dist(vals[k],(sp[k]['x'],sp[k]['y'])) for k in vals if k in sp and sp[k].get('x') is not None]; jump=max(ds) if ds else None
  ratio=max(lengths)/min(lengths) if lengths and min(lengths)>0 else 999
  if conf>=.75 and ratio<3.5 and (jump is None or jump<90): cls='LIKELY_CORRECT'
  elif ratio>4.5 or (jump is not None and jump>150): cls='CLEARLY_INCONSISTENT'
  else: cls='UNCERTAIN'
  results[str(f)]={'classification':cls,'mean_confidence':round(conf,4),'bone_lengths_px':[round(x,2) for x in lengths],'nearest_manual_frame':nearest,'max_seed_distance_px':round(jump,2) if jump is not None else None,'auto_approval':False}
  cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,im=cap.read()
  if ok:
   im=im[:,:im.shape[1]//2]; im=cv2.resize(im,None,fx=1.5,fy=1.5); 
   for k,v in vals.items(): cv2.circle(im,(round(v[0]*1.5),round(v[1]*1.5)),9,C.get(k,(255,255,255)),-1); cv2.putText(im,k,(round(v[0]*1.5)+10,round(v[1]*1.5)),0,.65,(0,0,0),2,cv2.LINE_AA)
   cv2.putText(im,f'Frame {f} | {cls}',(15,28),0,.75,(0,0,255) if cls!='LIKELY_CORRECT' else (0,140,0),2,cv2.LINE_AA); tiles.append((f,im))
 cap.release()
 out={'status':'AUTO_AUDITED_UNVERIFIED','source_video':p['source_video'],'prediction_file':str(args.pred),'manual_seed_file':str(args.seeds),'results':results,'counts':{c:sum(v['classification']==c for v in results.values()) for c in ['LIKELY_CORRECT','UNCERTAIN','CLEARLY_INCONSISTENT']},'manually_approved_added':0}
 args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(out,indent=2))
 if tiles:
  tw=640; th=max(x.shape[0] for _,x in tiles[:8]); sheet=np.full((th,tw*min(8,len(tiles)),3),255,np.uint8)
  for i,(_,im) in enumerate(tiles[:8]): sheet[:im.shape[0],i*tw:i*tw+min(tw,im.shape[1])]=im[:th,:tw]
  cv2.imwrite(str(args.out.with_suffix('.png')),sheet)
 print(json.dumps({'report':str(args.out),'contact_sheet':str(args.out.with_suffix('.png')),'counts':out['counts'],'auto_approved':0},indent=2))
if __name__=='__main__': main()
