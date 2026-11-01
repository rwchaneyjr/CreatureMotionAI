import argparse, cv2

def main():
    p=argparse.ArgumentParser(); p.add_argument('--side',required=True); p.add_argument('--front',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    x=cv2.imread(a.side); y=cv2.imread(a.front)
    if x is None or y is None: raise RuntimeError('Missing camera render')
    y=cv2.resize(y,(x.shape[1],x.shape[0])); out=cv2.hconcat([x,y])
    cv2.putText(out,'CAMERA A - SIDE',(20,35),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,255,255),2)
    cv2.putText(out,'CAMERA B - FRONT',(x.shape[1]+20,35),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,255,255),2)
    cv2.imwrite(a.output,out); print({'output':a.output,'size':list(out.shape[1::-1])})
if __name__=='__main__': main()
