"""Manual, unverified Front.L landmark review for the selected side video.

Run with the project DLC Python. Points are never approved automatically.
Click a joint button, click the image, then use Approve only after confirming
that the visible leg is Front.L. Hidden/uncertain points can be recorded.
"""
import json, sys, tkinter as tk
from pathlib import Path
import cv2
from PIL import Image, ImageTk

JOINTS = ["hip", "knee", "ankle", "foot"]
COLORS = {"hip":"#ff3030", "knee":"#ff9f1c", "ankle":"#20bf55", "foot":"#2463eb"}
FRAMES = [1, 25, 49, 73, 97]

class Reviewer:
    def __init__(self, video, out):
        self.video, self.out = Path(video), Path(out)
        self.cap = cv2.VideoCapture(str(self.video))
        self.frames = {}
        for f in FRAMES:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, f-1)
            ok, im = self.cap.read()
            if ok: self.frames[f] = im[:, :im.shape[1]//2].copy()
        self.cap.release()
        if not self.frames: raise RuntimeError("Could not read selected video frames")
        self.i, self.selected, self.points, self.status = 0, None, {}, {}
        self.root = tk.Tk(); self.root.title("CreatureMotionAI — Front.L Landmark Review (UNVERIFIED)")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        bar = tk.Frame(self.root); bar.pack(fill="x")
        tk.Label(bar, text="Select a joint, click the visible point, then Approve only if this is Front.L.").pack(side="left", padx=8)
        for j in JOINTS:
            tk.Button(bar, text=j.title(), command=lambda x=j:self.choose(x), fg=COLORS[j]).pack(side="left")
        tk.Button(bar, text="Hidden / uncertain", command=self.uncertain).pack(side="left", padx=5)
        tk.Button(bar, text="Undo", command=self.undo).pack(side="left")
        tk.Button(bar, text="Previous Frame", command=lambda:self.move(-1)).pack(side="left")
        tk.Button(bar, text="Next Frame", command=lambda:self.move(1)).pack(side="left")
        tk.Button(bar, text="Approve visible points", command=self.approve).pack(side="left", padx=5)
        tk.Button(bar, text="Save", command=self.save).pack(side="left")
        self.info=tk.Label(self.root,text="Frame 1 | UNVERIFIED | choose a joint")
        self.info.pack(fill="x")
        self.canvas=tk.Canvas(self.root, bg="white", cursor="crosshair"); self.canvas.pack(fill="both",expand=True)
        self.canvas.bind("<Button-1>", self.click)
        self.show()
        self.root.mainloop()

    def choose(self,j): self.selected=j; self.info.config(text=f"Frame {FRAMES[self.i]} | selected {j.upper()} | click image")
    def key(self): return str(FRAMES[self.i])
    def click(self,e):
        if not self.selected: return
        self.points.setdefault(self.key(),{})[self.selected]={"x":round(e.x/self.scale,6),"y":round(e.y/self.scale,6),"visibility":"visible","approval":"UNVERIFIED"}
        self.show()
    def uncertain(self):
        if not self.selected: return
        self.points.setdefault(self.key(),{})[self.selected]={"x":None,"y":None,"visibility":"uncertain","approval":"UNVERIFIED"}; self.show()
    def undo(self):
        d=self.points.get(self.key(),{})
        if self.selected: d.pop(self.selected,None); self.show()
    def approve(self):
        for p in self.points.get(self.key(),{}).values():
            if p.get("visibility")=="visible": p["approval"]="MANUALLY_APPROVED"
        self.show()
    def move(self,d): self.i=max(0,min(len(FRAMES)-1,self.i+d)); self.selected=None; self.show()
    def show(self):
        im=self.frames[FRAMES[self.i]]; maxw,maxh=1400,850; self.scale=min(maxw/im.shape[1],maxh/im.shape[0],1.0)
        rgb=cv2.cvtColor(im,cv2.COLOR_BGR2RGB); pil=Image.fromarray(rgb).resize((int(im.shape[1]*self.scale),int(im.shape[0]*self.scale)))
        self.photo=ImageTk.PhotoImage(pil)
        self.canvas.config(width=pil.width,height=pil.height, scrollregion=(0,0,pil.width,pil.height))
        self.root.geometry(f"{pil.width}x{min(pil.height+95,950)}")
        self.canvas.delete("all"); self.canvas.create_image(0,0,anchor="nw",image=self.photo)
        d=self.points.get(self.key(),{}); coords=[]
        for j in JOINTS:
            p=d.get(j); 
            if p and p.get("x") is not None:
                x,y=p["x"]*self.scale,p["y"]*self.scale; self.canvas.create_oval(x-7,y-7,x+7,y+7,fill=COLORS[j],outline="white",width=2); self.canvas.create_text(x+10,y,anchor="w",text=j,fill="white"); coords.append((x,y))
        if len(coords)>1:
            self.canvas.create_line(*sum(([x,y] for x,y in coords),[]),fill="#ffffff",width=3)
        self.info.config(text=f"Frame {FRAMES[self.i]} | {'UNVERIFIED' if not any(p.get('approval')=='MANUALLY_APPROVED' for p in d.values()) else 'APPROVED'} | click a visible point; hidden joints may be skipped")
    def save(self):
        payload={"status":"MANUAL_REVIEW","source_video":str(self.video),"panel":"side","frames":FRAMES,"landmarks":self.points,"identity":"Front.L","identity_confirmation":"USER_REQUIRED","notes":"Only user-approved visible points are approved; hidden/uncertain points remain unverified."}
        self.out.parent.mkdir(parents=True,exist_ok=True); self.out.write_text(json.dumps(payload,indent=2),encoding="utf-8"); self.info.config(text=f"Saved {self.out} | approval is explicit per visible point")

if __name__ == '__main__':
    if len(sys.argv)!=3: raise SystemExit('Usage: python review_frontl_landmarks.py VIDEO OUTPUT_JSON')
    Reviewer(sys.argv[1],sys.argv[2])
