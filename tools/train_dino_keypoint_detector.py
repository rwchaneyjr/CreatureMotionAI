"""Train a small keypoint head on the validated synthetic dataset.

The DINOv2 backbone is frozen; only the keypoint head is trained. This keeps
the first CPU test small and makes the held-out error measurable.
"""
import argparse, json, math
from pathlib import Path
import torch
from torch import nn
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

class Head(nn.Module):
    def __init__(self, channels, joints):
        super().__init__(); self.net=nn.Sequential(nn.Linear(channels,512),nn.GELU(),nn.Linear(512,joints*2),nn.Sigmoid()); self.joints=joints
    def forward(self,x): return self.net(x)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',required=True); p.add_argument('--model-cache',default='models'); p.add_argument('--output',required=True); p.add_argument('--epochs',type=int,default=3); a=p.parse_args()
    root=Path(a.dataset); rows=[json.loads(x) for x in (root/'labels.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    joints=sorted(rows[0]['cameras']['camera_A']['joints_2d']); cams=['camera_A','camera_B']; items=[(r,c) for r in rows for c in cams]
    g=torch.Generator().manual_seed(8301); perm=torch.randperm(len(items),generator=g).tolist(); cut=int(len(items)*.8); train=[items[i] for i in perm[:cut]]; val=[items[i] for i in perm[cut:]]
    device=torch.device('cpu'); processor=AutoImageProcessor.from_pretrained('facebook/dinov2-base',cache_dir=a.model_cache,local_files_only=True); backbone=AutoModel.from_pretrained('facebook/dinov2-base',cache_dir=a.model_cache,local_files_only=True).to(device).eval()
    for q in backbone.parameters(): q.requires_grad=False
    def embed(batch):
        with torch.no_grad():
            out=backbone(**processor(images=batch,return_tensors='pt').to(device)); x=out.last_hidden_state[:,1:,:]; side=int(math.sqrt(x.shape[1])); return x.transpose(1,2).reshape(len(batch),x.shape[2],side,side)
    cache={}
    def get(items):
        imgs=[]; ys=[]; ws=[]; keys=[]
        for r,c in items:
            i=r['sample']; imgs.append(Image.open(root/c/f'pose_{i:04d}.png').convert('RGB')); pts=r['cameras'][c]['joints_2d']; ys.append([[float(pts[j][0]/256),float(pts[j][1]/144)] for j in joints]); ws.append([1.0 if pts[j][3] else .1 for j in joints]); keys.append((i,c))
        return embed(imgs),torch.tensor(ys),torch.tensor(ws),keys
    xt,yt,wt,_=get(train); xv,yv,wv,kv=get(val); head=Head(xt.shape[1],len(joints)).to(device); opt=torch.optim.AdamW(head.parameters(),lr=2e-3); target_size=xt.shape[-1]
    xt=xt.mean(dim=(2,3)); xv=xv.mean(dim=(2,3)); yt=yt.reshape(len(yt),-1); yv=yv.reshape(len(yv),-1); wt=wt.repeat_interleave(2,dim=1); wv=wv.repeat_interleave(2,dim=1)
    for epoch in range(a.epochs):
        head.train(); pred=head(xt); loss=((pred-yt)**2*wt).mean(); opt.zero_grad(); loss.backward(); opt.step(); print({'epoch':epoch+1,'loss':float(loss)})
    head.eval();
    with torch.no_grad(): pred=head(xv); err=torch.sqrt(((pred[:,0::2]-yv[:,0::2])**2+(pred[:,1::2]-yv[:,1::2])**2))*torch.tensor(200.0)
    # Report mean Euclidean pixel error per joint on held-out synthetic views.
    per={j:float(err[:,k].mean()) for k,j in enumerate(joints)}; report={'dataset':str(root.resolve()),'train_items':len(train),'validation_items':len(val),'joints':joints,'epochs':a.epochs,'device':'cpu','mean_pixel_error':float(err.mean()),'visible_weighted_training':'yes','per_joint_pixel_error':per,'status':'synthetic_detector_coordinate_head_trained','real_video_used':False}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); torch.save({'state_dict':head.state_dict(),'joints':joints},out.with_suffix('.pt')); out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
