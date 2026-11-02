"""Read-only report of original leg axes, lengths, bend plane, and roll."""
import argparse, json, math
from pathlib import Path
import bpy
from mathutils import Vector

LEGS=("Leg_Front.L","Leg_Front.R","Leg_MidFront.L","Leg_MidFront.R","Leg_MidRear.L","Leg_MidRear.R","Leg_Rear.L","Leg_Rear.R")

def vec(v): return [round(float(x),6) for x in v]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--output',required=True); a=p.parse_args()
    arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE'); rows=[]
    for name in LEGS:
        bones=[arm.data.bones.get(name+f'_{i:02d}') for i in (1,2,3)]
        if any(b is None for b in bones): rows.append({'leg':name,'status':'missing_bone'}); continue
        world=[(arm.matrix_world@b.head_local,arm.matrix_world@b.tail_local) for b in bones]
        hip,knee,foot=world[0][0],world[0][1],world[2][1]
        incoming=(knee-hip).normalized(); outgoing=(foot-knee).normalized(); normal=incoming.cross(outgoing)
        rows.append({'leg':name,'status':'ok','bones':[{'name':b.name,'length':round(b.length,6),'roll':round(float(getattr(b,'roll',0.0)),6),'head_local':vec(b.head_local),'tail_local':vec(b.tail_local),'y_axis_local':vec(b.y_axis)} for b in bones],'bend_normal_world':vec(normal.normalized() if normal.length else Vector((0,0,0))),'bend_angle_deg':round(math.degrees(incoming.angle(outgoing)),3)})
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps({'armature':arm.name,'bone_count':len(arm.data.bones),'legs':rows,'note':'read-only original rest pose; use this report to derive IK pole angle'},indent=2),encoding='utf-8'); print(json.dumps({'output':str(out),'legs':len(rows)}))
if __name__=='__main__': main()
