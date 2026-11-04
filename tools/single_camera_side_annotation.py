import cv2, json, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; VIDEO=ROOT/'data/reference/goodspilitbalisk.mp4'; FRAMES=[1,61,121,181,240]
LOG=ROOT/'data/generated/single_camera_annotation_runtime.log'
LEG_POINTS=['hip','knee','ankle','foot']; CAL_POINTS=['body_center','head_snout','tail_base','ground_contact','body_length_reference']; COLORS={'hip':(255,80,80),'knee':(80,255,80),'ankle':(80,160,255),'foot':(255,80,255),'body_center':(255,80,80),'head_snout':(80,255,80),'tail_base':(80,160,255),'ground_contact':(255,180,40),'body_length_reference':(255,80,255)}
POINTS=LEG_POINTS; OUT=ROOT/'data/generated/single_camera_verified_leg_landmarks.json'; MODE='leg'; REVIEW_FRAMES=FRAMES; status_message=''
state={'video':str(VIDEO),'panel':'left_side','leg_identity':'rear_left','frames':{str(f):{} for f in FRAMES}}; current_frame=0; image=None; points={}; order=[]
if OUT.exists(): state=json.loads(OUT.read_text())
def load(f):
 cap=cv2.VideoCapture(str(VIDEO));cap.set(cv2.CAP_PROP_POS_FRAMES,f-1);ok,img=cap.read();cap.release();return img[:,:img.shape[1]//2] if ok else None
def log(msg):
 LOG.parent.mkdir(parents=True,exist_ok=True); LOG.open('a',encoding='utf-8').write(msg+'\n'); print(msg,flush=True)
def verified_frame_count():
 return sum(1 for row in state.get('frames',{}).values() if sum(1 for p in row.values() if p.get('state')=='manual_verified' and p.get('visible'))==4)
def uv_xy(p):
 uv=p.get('uv',[0,0])
 if isinstance(uv,str): uv=uv.replace(',',' ').split()
 return (int(round(float(uv[0]))),int(round(float(uv[1]))))
def save():
 OUT.write_text(json.dumps(state,indent=2),encoding='utf-8'); msg=f'SAVED path={OUT} verified_frames={verified_frame_count()}'; log(msg); return msg
def approve_frame(frame_points):
 for p in frame_points.values():
  if p.get('visible'): p.update({'state':'manual_verified','source':'user_accepted_suggestion','confidence':1.0})
 return frame_points
def redraw():
 global image
 canvas=image.copy(); h,w=canvas.shape[:2]; cv2.rectangle(canvas,(0,0),(w,58),(255,255,255),-1); nxt=POINTS[len(order)] if len(order)<len(POINTS) else 'complete'; label='CAMERA CALIBRATION' if MODE=='calibration' else ('REVIEW PROPOSALS: REAR_LEFT' if MODE=='suggestions' else 'TRACK LEG: REAR_LEFT'); extra=' | A accept frame' if MODE=='suggestions' else ''; cv2.putText(canvas,f'{label} | Click: {nxt.upper()} | U undo | O occluded | S save | N next | Q quit{extra}',(10,28),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),2)
 for name,p in points.items():
  if p.get('visible'):
   xy=uv_xy(p); cv2.circle(canvas,xy,9,COLORS[name],-1); cv2.putText(canvas,name,xy,cv2.FONT_HERSHEY_SIMPLEX,.6,COLORS[name],2)
 visible=[uv_xy(points[x]) for x in POINTS if x in points and points[x].get('visible')]
 for a,b in zip(visible,visible[1:]): cv2.line(canvas,a,b,(0,220,220),3)
 cv2.putText(canvas,f'Output: {OUT.name} | Verified frames: {verified_frame_count()} | {globals().get("status_message","")}',(10,h-14),cv2.FONT_HERSHEY_SIMPLEX,.43,(0,0,0),1,cv2.LINE_AA); cv2.imshow('CreatureMotionAI - Side View Leg Annotation',canvas)
def mouse(event,x,y,flags,param):
  if event==cv2.EVENT_LBUTTONDOWN and len(order)<len(POINTS):
   name=POINTS[len(order)];points[name]={'uv':[int(x),int(y)],'visible':True,'confidence':1.0,'source':'user_verified'};order.append(name);state['frames'][str(current_frame)]=points.copy();save();redraw()
def main():
 global POINTS,OUT,MODE,state,REVIEW_FRAMES,status_message
 ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['leg','calibration','suggestions'],default='leg'); a=ap.parse_args(); MODE=a.mode
 if MODE=='calibration': POINTS=CAL_POINTS; OUT=ROOT/'data/generated/single_camera_camera_calibration_annotations.json'; state={'video':str(VIDEO),'panel':'left_side','mode':'calibration','frames':{str(f):{} for f in FRAMES}}
 if MODE=='suggestions':
  OUT=ROOT/'data/generated/dlc_training_suggestions.json'; state=json.loads(OUT.read_text()); REVIEW_FRAMES=sorted(int(x) for x in state['frames']); POINTS=LEG_POINTS
 else: POINTS=LEG_POINTS
 if OUT.exists(): state=json.loads(OUT.read_text())
 global current_frame,image,points,order
 log(f'START mode={MODE} output={OUT} cwd={Path.cwd()}')
 cv2.namedWindow('CreatureMotionAI - Side View Leg Annotation',cv2.WINDOW_NORMAL);cv2.resizeWindow('CreatureMotionAI - Side View Leg Annotation',1280,720);cv2.setWindowTitle('CreatureMotionAI - Side View Leg Annotation','CMAI DLC REVIEW - A approve | S save | Q save and quit');cv2.setMouseCallback('CreatureMotionAI - Side View Leg Annotation',mouse)
 for idx,f in enumerate(REVIEW_FRAMES):
  current_frame=f;image=load(f);saved=state['frames'].get(str(f),{});points={k:v for k,v in saved.items()};order=[k for k in POINTS if k in points];redraw();print(f'Frame {f}: click {", ".join(POINTS)}; press O to mark the next point occluded.')
  while True:
   k=cv2.waitKey(0)&255; key=chr(k).lower() if k else ''; log(f'KEY raw={k} key={key} frame={f}')
   if key=='u' and order: points.pop(order.pop(),None);redraw()
   elif key=='a' and MODE=='suggestions':
    points=approve_frame(points); state['frames'][str(f)]=points.copy(); status_message=f'APPROVED frame {f}'; log(status_message); save(); redraw()
   elif key=='o' and len(order)<len(POINTS): name=POINTS[len(order)];points[name]={'visible':False,'confidence':0.0,'source':'user_marked_occluded'};order.append(name);state['frames'][str(f)]=points.copy();save();redraw()
   elif key=='s':
    state['frames'][str(f)]=points.copy(); status_message='SAVED'; save(); redraw()
   elif key=='n': state['frames'][str(f)]=points.copy();save();break
   elif key=='q': state['frames'][str(f)]=points.copy(); status_message='SAVED / EXITING'; save(); cv2.destroyAllWindows(); log('EXIT'); return
 cv2.destroyAllWindows();save()
if __name__=='__main__': main()
