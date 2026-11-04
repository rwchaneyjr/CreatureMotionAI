import bpy, json
out=[]
for o in bpy.data.objects:
    out.append({'name':o.name,'type':o.type,'modifiers':[{'name':m.name,'type':m.type,'show':m.show_viewport} for m in o.modifiers], 'rigid_body':bool(o.rigid_body), 'collision':bool(o.collision)})
print(json.dumps(out))
