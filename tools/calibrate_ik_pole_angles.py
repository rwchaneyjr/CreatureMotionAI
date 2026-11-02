"""Search per-leg IK pole angles that preserve the original standing pose."""
import argparse, json, math
from pathlib import Path
import bpy
from mathutils import Vector

LEGS=("Leg_Front.L","Leg_Front.R","Leg_MidFront.L","Leg_MidFront.R","Leg_MidRear.L","Leg_MidRear.R","Leg_Rear.L","Leg_Rear.R")

def err(a,b):
    return sum((a[i][j]-b[i][j])**2 for i in range(4) for j in range(4))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--output',required=True); a=p.parse_args()
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); bpy.context.scene.frame_set(1)
    rows=[]
    for name in LEGS:
        upper=arm.pose.bones.get(name+'_01'); lower=arm.pose.bones.get(name+'_02'); foot=arm.pose.bones.get(name+'_03')
        if not upper or not lower or not foot: rows.append({'leg':name,'status':'missing'}); continue
        original={x.name:x.matrix.copy() for x in (upper,lower,foot)}
        target=bpy.data.objects.new('CMAI_Calibration_Target_'+name,None); bpy.context.scene.collection.objects.link(target); target.empty_display_type='SPHERE'; target.location=arm.matrix_world@foot.tail
        hip=arm.matrix_world@upper.head; knee=arm.matrix_world@upper.tail; end=arm.matrix_world@foot.tail
        incoming=(knee-hip).normalized(); outgoing=(end-knee).normalized(); normal=incoming.cross(outgoing)
        if normal.length<1e-6: normal=Vector((0,0,1))
        pole=bpy.data.objects.new('CMAI_Calibration_Pole_'+name,None); bpy.context.scene.collection.objects.link(pole); pole.location=knee+normal.normalized().cross(incoming).normalized()*0.18
        best=(1e30,0.0,2)
        for chain_count in (2,3):
            con=upper.constraints.new('IK'); con.target=target; con.pole_target=pole; con.chain_count=chain_count
            for i in range(73):
                angle=-math.pi + (2*math.pi*i/72); con.pole_angle=angle; bpy.context.view_layer.update()
                value=sum(err(b.matrix,original[b.name]) for b in (upper,lower,foot))
                if value<best[0]: best=(value,angle,chain_count)
            upper.constraints.remove(con); bpy.context.view_layer.update()
        con=upper.constraints.new('IK'); con.target=target; con.pole_target=pole; con.chain_count=best[2]; con.pole_angle=best[1]; bpy.context.view_layer.update()
        rows.append({'leg':name,'status':'calibrated','chain_count':best[2],'pole_angle_rad':round(best[1],6),'pole_angle_deg':round(math.degrees(best[1]),3),'rest_pose_error':round(best[0],8)})
        upper.constraints.remove(con); bpy.data.objects.remove(target,do_unlink=True); bpy.data.objects.remove(pole,do_unlink=True)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps({'armature':arm.name,'legs':rows,'status':'calibration_only','note':'Angles require visual and collision validation before use.'},indent=2),encoding='utf-8'); print(json.dumps({'output':str(out),'legs':len(rows)}))
if __name__=='__main__': main()
