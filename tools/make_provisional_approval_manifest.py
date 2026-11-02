"""Convert stable landmark diagnostics into an explicitly provisional manifest."""
import argparse, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('stable',type=Path); p.add_argument('--output',required=True,type=Path); a=p.parse_args()
    data=json.loads(a.stable.read_text(encoding='utf-8'))
    landmarks={}
    for name,item in data.get('landmarks',{}).items():
        landmarks[name]={**item,'status':'provisional_approved' if item.get('status')=='provisional_stable' else 'uncertain'}
    result={'source':str(a.stable),'status':'provisional_only','final_approval':False,'landmarks':landmarks,'note':'Diagnostic use only; these labels must not be treated as final ground truth.'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(a.output),'provisional':sum(v['status']=='provisional_approved' for v in landmarks.values()),'uncertain':sum(v['status']=='uncertain' for v in landmarks.values())}))
if __name__=='__main__': main()
