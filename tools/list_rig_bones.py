import bpy
arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig')
print([b.name for b in arm.data.bones])
