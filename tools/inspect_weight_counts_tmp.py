import bpy, json
bpy.ops.wm.open_mainfile(filepath=r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\seamless\seamless_loop.blend')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH')
for label,names in {'A':['Leg_Rear.R_01','Leg_Rear.R_02','Leg_Rear.R_03'],'B':['Leg_MidRear.R_01','Leg_MidRear.R_02','Leg_MidRear.R_03']}.items():
 ids=[mesh.vertex_groups[n].index for n in names]
 counts={str(t):0 for t in (.05,.2,.35,.5,.7,.9)}
 for v in mesh.data.vertices:
  w=sum(g.weight for g in v.groups if g.group in ids)
  for t in counts:
   if w>=float(t): counts[t]+=1
 print(label,counts)
