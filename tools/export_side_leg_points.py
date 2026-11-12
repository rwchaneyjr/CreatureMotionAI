import bpy, json, sys
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
blend,out=args[:2]
bpy.ops.wm.open_mainfile(filepath=blend); s=bpy.context.scene; s.frame_set(1)
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; legs=['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
outd={}
for leg in legs:
    names=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]
    pts=[]
    for n in names:
        pb=arm.pose.bones.get(n)
        if pb: pts.append({'name':n,'head':list(arm.matrix_world@pb.head),'tail':list(arm.matrix_world@pb.tail)})
    outd[leg]=pts
json.dump({'blend':blend,'projection':'-X side uses world Y/Z','legs':outd},open(out,'w'),indent=2)
print(out)
