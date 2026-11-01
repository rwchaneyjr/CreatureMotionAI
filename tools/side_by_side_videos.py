import argparse, cv2

def main():
    p=argparse.ArgumentParser(); p.add_argument('--reference',required=True); p.add_argument('--result',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    r=cv2.VideoCapture(a.reference); b=cv2.VideoCapture(a.result)
    fps=r.get(cv2.CAP_PROP_FPS) or 24.0; w=int(r.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(r.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer=cv2.VideoWriter(a.output,cv2.VideoWriter_fourcc(*'mp4v'),fps,(w*2,h))
    count=0
    while count < int(fps*5):
        ok1,x=r.read(); ok2,y=b.read()
        if not ok1 or not ok2: break
        y=cv2.resize(y,(w,h)); frame=cv2.hconcat([x,y])
        cv2.putText(frame,'REFERENCE 8leggedBalisk.mp4',(20,42),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,255),2)
        cv2.putText(frame,'CURRENT BLENDER RESULT',(w+20,42),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,255),2)
        writer.write(frame); count+=1
    r.release(); b.release(); writer.release(); print({'frames':count,'seconds':count/fps,'output':a.output})
if __name__=='__main__': main()
