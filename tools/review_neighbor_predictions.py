"""Review optical-flow landmark predictions without changing manual seeds."""
import json, sys, tkinter as tk
from pathlib import Path
import cv2
from PIL import Image, ImageTk

JOINTS=['hip','knee','ankle','foot']; COLORS={'hip':'#f22','knee':'#f90','ankle':'#1c5','foot':'#26f'}

class App:
 def __init__(self,video,pred,out):
  self.video=Path(video); self.pred_path=Path(pred); self.out=Path(out); self.data=json.loads(self.pred_path.read_text()); self.frames=sorted(map(int,self.data['predicted_landmarks']))
  self.cap=cv2.VideoCapture(str(self.video)); self.i=0; self.decisions={}; self.root=tk.Tk(); self.root.title('CreatureMotionAI — Predicted Landmark Review (UNVERIFIED)')
  bar=tk.Frame(self.root); bar.pack(fill='x'); tk.Label(bar,text='Review prediction; approve only if the same leg is clear.').pack(side='left',padx=6)
  for text,cmd in [('Previous',lambda:self.move(-1)),('Next',lambda:self.move(1)),('Approve frame',self.approve),('Reject frame',self.reject),('Save',self.save)]: tk.Button(bar,text=text,command=cmd).pack(side='left',padx=2)
  self.info=tk.Label(self.root); self.info.pack(fill='x'); self.canvas=tk.Canvas(self.root,bg='white'); self.canvas.pack(fill='both',expand=True); self.show(); self.root.mainloop()
 def move(self,d): self.i=max(0,min(len(self.frames)-1,self.i+d)); self.show()
 def current(self): return str(self.frames[self.i])
 def decision(self): return self.decisions.get(self.current(),'UNVERIFIED')
 def approve(self): self.decisions[self.current()]='MANUALLY_APPROVED'; self.show()
 def reject(self): self.decisions[self.current()]='REJECTED'; self.show()
 def show(self):
  f=self.frames[self.i]; self.cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,im=self.cap.read()
  if not ok:return
  im=im[:,:im.shape[1]//2]; s=min(1,1400/im.shape[1],850/im.shape[0]); im=cv2.cvtColor(im,cv2.COLOR_BGR2RGB); pil=Image.fromarray(im).resize((int(im.shape[1]*s),int(im.shape[0]*s))); self.scale=s; self.photo=ImageTk.PhotoImage(pil); self.canvas.config(width=pil.width,height=pil.height); self.canvas.delete('all'); self.canvas.create_image(0,0,anchor='nw',image=self.photo)
  pts=self.data['predicted_landmarks'][str(f)]; coords=[]
  for j,p in pts.items():
   if p.get('x') is None:continue
   x,y=p['x']*s,p['y']*s; self.canvas.create_oval(x-7,y-7,x+7,y+7,fill=COLORS.get(j,'white'),outline='black',width=2); self.canvas.create_text(x+10,y,text=j,anchor='w',fill='black'); coords.append((x,y))
  if len(coords)>1:self.canvas.create_line(*sum(([x,y] for x,y in coords),[]),fill='black',width=3)
  self.info.config(text=f'Frame {f} | {self.decision()} | confidence values preserved; no automatic approval')
 def save(self):
  approved={}; rejected=[]
  for f,d in self.data['predicted_landmarks'].items():
   dec=self.decisions.get(f,'UNVERIFIED')
   if dec=='MANUALLY_APPROVED': approved[f]={k:{**v,'approval':'MANUALLY_APPROVED','review_source':'prediction_review'} for k,v in d.items()}
   elif dec=='REJECTED': rejected.append(int(f))
  out={'status':'REVIEWED_PREDICTIONS','source_video':self.data['source_video'],'panel':'side','approved_predictions':approved,'rejected_frames':rejected,'remaining_unverified_frames':[f for f in self.frames if str(f) not in self.decisions],'prediction_file':str(self.pred_path)}
  self.out.parent.mkdir(parents=True,exist_ok=True); self.out.write_text(json.dumps(out,indent=2)); self.info.config(text=f'Saved {self.out}')
if __name__=='__main__':
 if len(sys.argv)!=4: raise SystemExit('Usage: python review_neighbor_predictions.py VIDEO PREDICTIONS APPROVED_OUTPUT_JSON')
 App(*sys.argv[1:])
