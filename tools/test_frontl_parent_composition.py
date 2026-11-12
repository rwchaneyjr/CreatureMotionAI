import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector, Quaternion, Matrix

blend, out = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']
names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']
s.frame_set(1); bpy.context.view_layer.update(); baseline={p.name:p.matrix.copy() for p in arm.pose.bones}
d=json.loads(Path('data/generated/ikpy_frontL_chain.json').read_text())
p=[Vector(b['head_armature']) for b in d['bones']]+[Vector(d['bones'][-1]['tail_armature'])]
seg=[p[i+1]-p[i] for i in range(3)]; axis=seg[0].cross(seg[1]).normalized(); angle=0.1

def reset():
    for n,m in baseline.items(): arm.pose.bones[n].matrix=m.copy()
    bpy.context.view_layer.update()

def expected(qs):
    r=[Matrix.Identity(3)]
    r1=Matrix.Rotation(qs[0],3,axis); r2=r1@Matrix.Rotation(qs[1],3,axis); r3=r2@Matrix.Rotation(qs[2],3,axis)
    j0=p[0]; j1=j0+r1@seg[0]; j2=j1+r2@seg[1]; j3=j2+r3@seg[2]
    return [(j0,j1),(j1,j2),(j2,j3)]

tests=[('rest',[0,0,0]),('L01',[angle,0,0]),('L02',[0,angle,0]),('L03',[0,0,angle]),('L01_L02',[angle,angle,0]),('L01_L02_L03',[angle,angle,angle])]
rows=[]
for label,qs in tests:
    reset()
    for i,n in enumerate(names):
        if qs[i]:
            pb=arm.pose.bones[n]; rb=arm.data.bones[n]
            parent=rb.parent
            parent_rot = parent.matrix_local.to_3x3() if parent else Matrix.Identity(3)
            local=(parent_rot.inverted()@axis).normalized()
            pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=Quaternion(local,qs[i])
    bpy.context.view_layer.update()
    exp=expected(qs); errs=[]
    for i,n in enumerate(names):
        pb=arm.pose.bones[n]
        errs.append({'bone':n,'head_error':float((pb.head-exp[i][0]).length),'tail_error':float((pb.tail-exp[i][1]).length),'head_armature':list(pb.head),'tail_armature':list(pb.tail),'expected_head':list(exp[i][0]),'expected_tail':list(exp[i][1])})
    rows.append({'test':label,'angles':qs,'joints':errs})
payload={'angle_rad':angle,'coordinate_space':'armature-local','axis_armature':list(axis),'results':rows}
Path(out).write_text(json.dumps(payload,indent=2)); print(json.dumps(payload,indent=2))
