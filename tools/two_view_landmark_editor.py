"""Interactive two-view correspondence editor for explicit user matches only.

Controls: 1-9 choose an optional identity, left-click side then front, V save
side-only, U undo, O mark occluded, X mark out-of-frame, S save, N next
frame, P previous frame, Q save and quit. Only visible points are requested.
"""
import argparse, json, cv2
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
from creature_motion_ai.pose_library import load as load_library, save as save_library, add_observation
NAMES=['body_center','snout','tail_base','front_hip','front_knee','front_ankle','rear_hip','rear_knee','rear_ankle']
COLORS=[(255,80,80),(80,255,80),(80,160,255),(255,180,40),(255,80,255),(80,255,255),(180,80,255),(80,180,255),(255,180,180)]

def read_frame(cap, number):
    cap.set(cv2.CAP_PROP_POS_FRAMES, number-1); ok,im=cap.read()
    return im if ok else None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--video',default=r'C:\Users\rober\Downloads\2VIEWSBALISK SYNCWALK.mp4'); ap.add_argument('--output',default=str(ROOT/'data/generated/two_view_verified_correspondences.json')); ap.add_argument('--frames',default='1,61,121,181,240'); args=ap.parse_args()
    cap=cv2.VideoCapture(args.video); fps=cap.get(cv2.CAP_PROP_FPS); total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); pw=w//2
    if not cap.isOpened(): raise RuntimeError('Could not open video')
    frames=[int(x) for x in args.frames.split(',')]; out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    state={'status':'USER_VERIFICATION_REQUIRED','video':str(Path(args.video).resolve()),'fps':fps,'resolution':[w,h],'panel_resolution':[pw,h],'frames':{str(f):[] for f in frames},'landmark_names':NAMES,'note':'Explicit clicks may be saved independently per panel; paired clicks are optional.'}
    if out.exists(): state=json.loads(out.read_text(encoding='utf-8'))
    win='CMAI Two-View Correspondence Editor'; cv2.namedWindow(win,cv2.WINDOW_NORMAL); cv2.resizeWindow(win,1280,720)
    fi=0; selected=0; pending_side=None; pending_front=None; current=None
    library_path=ROOT/'data/generated/cmai_pose_library.json'
    def save(): out.write_text(json.dumps(state,indent=2),encoding='utf-8')
    def save_library_observation(item):
        lib=load_library(library_path)
        frame=frames[fi]; conf={item['name']:float(item.get('confidence',1.0))}; status=item.get('approval_status','manual_verified')
        if item.get('side_visible',True) and 'side_px' in item:
            add_observation(lib, source_video=str(Path(args.video).resolve()), frame=frame, view='side', landmarks={item['name']:{'x':item['side_px'][0],'y':item['side_px'][1],'visible':True}}, confidence=conf, approval_status=status)
        if item.get('front_visible',True) and 'front_px' in item:
            add_observation(lib, source_video=str(Path(args.video).resolve()), frame=frame, view='front', landmarks={item['name']:{'x':item['front_px'][0],'y':item['front_px'][1],'visible':True}}, confidence=conf, approval_status=status)
        save_library(library_path,lib)
    def render():
        nonlocal current
        frame=frames[fi]; im=read_frame(cap,frame)
        if im is None: return
        left=im[:,:pw].copy(); right=im[:,pw:].copy(); canvas=cv2.hconcat([left,right]);
        cv2.rectangle(canvas,(0,0),(w,52),(255,255,255),-1); name=NAMES[selected]
        text=f'Frame {frame} | {selected+1}/{len(NAMES)}: {name.upper()} | click either panel; pair optional | V save visible | 1-9 | U undo | S save | N/P | Q'
        cv2.putText(canvas,text,(8,25),cv2.FONT_HERSHEY_SIMPLEX,.42,(0,0,0),2,cv2.LINE_AA)
        cv2.putText(canvas,'Click only visible points. V saves the currently clicked panel alone; O/X record uncertainty.',(8,47),cv2.FONT_HERSHEY_SIMPLEX,.42,(0,0,120),1,cv2.LINE_AA)
        for item in state['frames'].get(str(frame),[]):
            if not item.get('visible',True): continue
            c=COLORS[NAMES.index(item['name'])]; sx,sy=item['side_px']; cv2.circle(canvas,(sx,sy),8,c,-1); cv2.putText(canvas,item['name'],(sx+8,sy),cv2.FONT_HERSHEY_SIMPLEX,.5,c,2)
            if 'front_px' in item:
                fx,fy=item['front_px']; cv2.circle(canvas,(pw+fx,fy),8,c,-1); cv2.putText(canvas,item['name'],(pw+fx+8,fy),cv2.FONT_HERSHEY_SIMPLEX,.5,c,2)
            else:
                cv2.putText(canvas,'SIDE ONLY',(pw+10,60+20*NAMES.index(item['name'])),cv2.FONT_HERSHEY_SIMPLEX,.45,c,1)
        if pending_side: cv2.circle(canvas,pending_side,10,(0,0,0),2)
        cv2.imshow(win,canvas); current=im
    def mouse(event,x,y,flags,param):
        nonlocal pending_side, pending_front
        if event!=cv2.EVENT_LBUTTONDOWN: return
        frame=frames[fi]; items=state['frames'].setdefault(str(frame),[]); name=NAMES[selected]
        if x<pw and pending_side is None: pending_side=(x,y); render(); return
        if x>=pw and pending_front is None: pending_front=(x-pw,y); render(); return
        if pending_side is not None and pending_front is not None:
            existing=[i for i in items if i['name']==name]; [items.remove(i) for i in existing]
            item={'name':name,'side_px':[int(pending_side[0]),int(pending_side[1])],'front_px':[int(pending_front[0]),int(pending_front[1])],'side_norm':[pending_side[0]/pw,pending_side[1]/h],'front_norm':[pending_front[0]/pw,pending_front[1]/h],'visible':True,'confidence':1.0,'approval_status':'manual_verified','rig_bone':None}
            items.append(item); save_library_observation(item); pending_side=None; pending_front=None; save(); render()
    cv2.setMouseCallback(win,mouse)
    render()
    while True:
        k=cv2.waitKey(0)&255; key=chr(k).lower() if k else ''
        if key in '123456789': selected=int(key)-1; pending_side=None; render()
        elif key=='u':
            items=state['frames'].setdefault(str(frames[fi]),[]); [items.pop() for _ in [0] if items]; pending_side=None; save(); render()
        elif key=='v':
            if pending_side is not None or pending_front is not None:
                items=state['frames'].setdefault(str(frames[fi]),[])
                items[:]=[i for i in items if i.get('name')!=NAMES[selected]]
                if pending_side is not None:
                    item={'name':NAMES[selected],'side_px':[int(pending_side[0]),int(pending_side[1])],'side_norm':[pending_side[0]/pw,pending_side[1]/h],'visible':True,'side_visible':True,'front_visible':False,'confidence':1.0,'approval_status':'manual_verified','rig_bone':None}
                else:
                    item={'name':NAMES[selected],'front_px':[int(pending_front[0]),int(pending_front[1])],'front_norm':[pending_front[0]/pw,pending_front[1]/h],'visible':True,'side_visible':False,'front_visible':True,'confidence':1.0,'approval_status':'manual_verified','rig_bone':None}
                items.append(item); save_library_observation(item); pending_side=None; pending_front=None; save(); render()
        elif key=='o':
            state['frames'].setdefault(str(frames[fi]),[]).append({'name':NAMES[selected],'visible':False,'confidence':0.0,'approval_status':'occluded','rig_bone':None}); pending_side=None; save(); render()
        elif key=='x':
            state['frames'].setdefault(str(frames[fi]),[]).append({'name':NAMES[selected],'visible':False,'confidence':0.0,'approval_status':'out_of_frame','rig_bone':None}); pending_side=None; save(); render()
        elif key=='s': save(); render()
        elif key=='n': fi=(fi+1)%len(frames); pending_side=None; render()
        elif key=='p': fi=(fi-1)%len(frames); pending_side=None; render()
        elif key=='q': save(); break
    cv2.destroyAllWindows(); cap.release(); print(json.dumps({'output':str(out.resolve()),'frames':frames,'status':state['status']}))

if __name__=='__main__': main()
