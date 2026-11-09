import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector

def main():
    blend,out=sys.argv[sys.argv.index('--')+1:]
    bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
    arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig')
    legs=['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
    rows=[]
    for leg in legs:
        names=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]
        per=[]; foot=[]; knee=[]
        for f in (1,7,13,19,24):
            bpy.context.scene.frame_set(f); bpy.context.view_layer.update()
            bs=[arm.pose.bones.get(n) for n in names]
            per.append({'frame':f,'rot':[list(b.rotation_euler) if b.rotation_mode=='XYZ' else list(b.rotation_quaternion) for b in bs]})
            foot.append(list(arm.matrix_world @ bs[2].tail))
            h=arm.matrix_world@bs[0].head; k=arm.matrix_world@bs[0].tail; a=arm.matrix_world@bs[1].tail
            knee.append(math.degrees((h-k).angle(a-k)))
        rows.append({'leg':leg,'bone_rotations':per,'foot_positions':foot,'knee_angles_deg':knee,'knee_change_deg':max(knee)-min(knee),'foot_lift':max(p[2] for p in foot)-min(p[2] for p in foot)})
    Path(out).write_text(json.dumps({'status':'FK_ARTICULATION_MEASURED','blend':str(Path(blend).resolve()),'frames':[1,7,13,19,24],'legs':rows},indent=2),encoding='utf-8')
    print(json.dumps({'output':out,'legs':len(rows)}))
if __name__=='__main__': main()
