import sys, bpy
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:]
blend=argv[0]; bpy.ops.wm.open_mainfile(filepath=blend)
scene=bpy.context.scene; scene.frame_set(1)
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; pbs=[arm.pose.bones[f'Leg_Front.L_{i:02d}'] for i in (1,2,3)]
def w(pb,end=False): return arm.matrix_world @ (pb.tail if end else pb.head)
end=w(pbs[2],True)
t=bpy.data.objects.new('DBG_Target',None); scene.collection.objects.link(t); t.location=end
con=pbs[0].constraints.new('IK'); con.target=t; con.chain_count=3
for f,loc in [(1,end),(12,end+Vector((0.008,0,0))),(24,end)]:
    scene.frame_set(f); t.location=loc; bpy.context.view_layer.update(); cur=w(pbs[2],True)
    print(f,'target',tuple(loc),'foot',tuple(cur),'err',(cur-loc).length,'rootrot',tuple(pbs[0].rotation_euler))
