"""Create a clean static standing-pose copy directly from the original FBX."""
import argparse, json, sys
from pathlib import Path
import bpy
from mathutils import Vector

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True); p.add_argument('--render',required=True); a=p.parse_args(argv if (argv:=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]) else None)
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.fbx(filepath=a.input); bpy.context.scene.frame_set(1)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    pose={b.name:(b.location.copy(),b.rotation_mode,b.rotation_euler.copy(),b.rotation_quaternion.copy(),b.scale.copy()) for b in rig.pose.bones}
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    action=bpy.data.actions.new('CMAI_Static_Original_Standing'); action.use_fake_user=True; rig.animation_data_create(); rig.animation_data.action=action
    for b in rig.pose.bones:
        loc,mode,euler,quat,scale=pose[b.name]; b.location=loc; b.rotation_mode=mode; b.rotation_euler=euler; b.rotation_quaternion=quat; b.scale=scale; b.keyframe_insert('location',frame=1); b.keyframe_insert('rotation_euler',frame=1); b.keyframe_insert('rotation_quaternion',frame=1); b.keyframe_insert('scale',frame=1)
    rig.show_in_front=True; rig.data.display_type='OCTAHEDRAL'; rig.data.show_names=True; mesh.show_wire=False; mesh.show_all_edges=False; mesh.display_type='TEXTURED'
    for b in rig.data.bones:
        try: b.color.palette='THEME04' if b.name.startswith('Leg_') else 'THEME03' if b.name.startswith('Tail_') else 'THEME01'
        except AttributeError: pass
    scene=bpy.context.scene; scene.frame_start=1; scene.frame_end=1; scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.color_type='TEXTURE'; scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=75
    cam_data=bpy.data.cameras.new('CMAI_Static_ThreeQuarter_Camera'); cam=bpy.data.objects.new('CMAI_Static_ThreeQuarter_Camera',cam_data); bpy.context.collection.objects.link(cam); cam.location=(-3.4,-2.4,1.45); cam.rotation_euler=(Vector((0,0,0.05))-cam.location).to_track_quat('-Z','Y').to_euler(); cam_data.lens=55; scene.camera=cam
    Path(a.render).parent.mkdir(parents=True,exist_ok=True); scene.render.filepath=a.render; bpy.ops.render.render(write_still=True); scene.frame_set(1); bpy.ops.wm.save_as_mainfile(filepath=a.output)
    print(json.dumps({'output':a.output,'render':a.render,'bones':len(rig.data.bones),'actions':[x.name for x in bpy.data.actions]}))
if __name__=='__main__': main()
