"""Evaluate the trained detector on held-out synthetic views with known truth."""
import argparse, json, math
from pathlib import Path
import torch
from torch import nn
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

class Head(nn.Module):
    def __init__(self, channels, joints):
        super().__init__(); self.net=nn.Sequential(nn.Linear(channels,512),nn.GELU(),nn.Linear(512,joints*2),nn.Sigmoid())
    def forward(self,x): return self.net(x)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',required=True); p.add_argument('--weights',required=True); p.add_argument('--model-cache',default='models'); p.add_argument('--output',required=True); a=p.parse_args()
    root=Path(a.dataset); rows=[json.loads(x) for x in (root/'labels.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]; joints=sorted(rows[0]['cameras']['camera_A']['joints_2d']); items=[(r,c) for r in rows for c in ('camera_A','camera_B')]; g=torch.Generator().manual_seed(8301); perm=torch.randperm(len(items),generator=g).tolist(); val=[items[i] for i in perm[int(len(items)*.8):]]
    proc=AutoImageProcessor.from_pretrained('facebook/dinov2-base',cache_dir=a.model_cache,local_files_only=True); bb=AutoModel.from_pretrained('facebook/dinov2-base',cache_dir=a.model_cache,local_files_only=True).eval(); head=Head(bb.config.hidden_size,len(joints)); head.load_state_dict(torch.load(a.weights,map_location='cpu')['state_dict']); head.eval()
    errs=[]; vis_err=[]; occ_err=[]; per={j:[] for j in joints}
    for r,c in val:
        img=Image.open(root/c/f"pose_{r['sample']:04d}.png").convert('RGB')
        with torch.no_grad(): feat=bb(**proc(images=img,return_tensors='pt')).last_hidden_state[:,1:,:].mean(1); pred=head(feat)[0].reshape(len(joints),2)
        for k,j in enumerate(joints):
            q=r['cameras'][c]['joints_2d'][j]; e=float(torch.linalg.vector_norm((pred[k]-torch.tensor([q[0]/256,q[1]/144])))*200); errs.append(e); per[j].append(e)
            (vis_err if q[3] else occ_err).append(e)
    report={'validation_views':len(val),'mean_error_all_px':sum(errs)/len(errs),'mean_error_visible_px':sum(vis_err)/max(len(vis_err),1),'mean_error_occluded_px':sum(occ_err)/max(len(occ_err),1),'per_joint_error_px':{j:sum(v)/len(v) for j,v in per.items()},'threshold_visible_px':20.0,'pass':sum(vis_err)/max(len(vis_err),1)<=20.0,'real_video_used':False,'status':'synthetic_detector_exam'}
    Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
