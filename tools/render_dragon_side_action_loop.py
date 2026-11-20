"""Render a fixed side-camera Action loop to PNG frames, preserving the blend."""
import argparse, math, os, re, sys
import shutil
from pathlib import Path
import bpy
from mathutils import Vector


def args_from_cli():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--action", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--resolution-x", type=int, default=1000)
    p.add_argument("--resolution-y", type=int, default=700)
    p.add_argument("--percentage", type=int, default=65)
    p.add_argument("--camera-side", type=int, choices=(-1, 1), default=1)
    p.add_argument("--hold-pose", action="store_true",
                   help="Render one pose once and duplicate the still across the requested duration")
    p.add_argument("--coarse-bounds", action="store_true",
                   help="Sample five evenly spaced frames to estimate the animation camera bounds")
    return p.parse_args(argv)


def main():
    a=args_from_cli(); scene=bpy.context.scene
    rig=bpy.data.objects.get("CrimsonWingedDragon_Rig")
    if rig is None or rig.animation_data is None: raise RuntimeError("Dragon rig missing")
    action=bpy.data.actions.get(a.action)
    if action is None: raise RuntimeError(f"Action missing: {a.action}")
    meshes=[o for o in scene.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object==rig for m in o.modifiers)]
    if not meshes: raise RuntimeError("No mesh is skinned to the dragon rig")

    old={"camera":scene.camera,"frame":scene.frame_current,"path":scene.render.filepath,
         "engine":scene.render.engine,"res":(scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage),
         "fps":scene.render.fps,"fps_base":scene.render.fps_base,"transparent":scene.render.film_transparent,
         "action":rig.animation_data.action,"slot":getattr(rig.animation_data,"action_slot",None)}
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    cam_data=bpy.data.cameras.new("CMAI_TempLoopSideCamera"); cam_data.type="ORTHO"
    cam=bpy.data.objects.new("CMAI_TempLoopSideCamera",cam_data); scene.collection.objects.link(cam)
    lights=[]
    try:
        rig.animation_data.action=action
        if hasattr(rig.animation_data,"action_slot") and len(action.slots):
            try: rig.animation_data.action_slot=action.slots[0]
            except Exception: pass
        start,end=map(int,action.frame_range)
        # Union evaluated bounds across the loop, so tips and tail remain framed.
        lows=[float("inf")]*3; highs=[float("-inf")]*3
        if a.hold_pose:
            bounds_frames = (start,)
        elif a.coarse_bounds:
            bounds_frames = sorted(set(round(start + (end - start) * i / 4) for i in range(5)))
        else:
            bounds_frames = range(start, end + 1)
        for frame in bounds_frames:
            scene.frame_set(frame); bpy.context.view_layer.update()
            deps=bpy.context.evaluated_depsgraph_get()
            for obj in meshes:
                ev=obj.evaluated_get(deps); me=ev.to_mesh()
                for vert in me.vertices:
                    q=ev.matrix_world@vert.co
                    for k in range(3): lows[k]=min(lows[k],q[k]); highs[k]=max(highs[k],q[k])
                ev.to_mesh_clear()
        center=Vector(tuple((lows[k]+highs[k])*0.5 for k in range(3)))
        span=Vector(tuple(highs[k]-lows[k] for k in range(3)))
        cam_data.ortho_scale=max(span.y,span.z)*(a.resolution_x/a.resolution_y)*1.14
        cam.location=center+Vector((a.camera_side*max(span)*3.0,0,0))
        cam.rotation_euler=(center-cam.location).to_track_quat("-Z","Y").to_euler()
        scene.camera=cam
        for name,offset,power,size in (("CMAI_Key",(-2.8,0,3.4),1450,4.0),("CMAI_Fill",(-2,2,.3),750,3.0),("CMAI_Rim",(2.5,0,2.2),1100,3.0)):
            d=bpy.data.lights.new(name,"AREA"); d.energy=power; d.shape="DISK"; d.size=size
            ob=bpy.data.objects.new(name,d); scene.collection.objects.link(ob)
            ob.location=center+Vector(offset); ob.rotation_euler=(center-ob.location).to_track_quat("-Z","Y").to_euler(); lights.append((ob,d))
        if scene.world:
            scene.world.use_nodes=True
            bg=scene.world.node_tree.nodes.get("Background")
            if bg:
                bg.inputs["Color"].default_value=(0.22,0.25,0.29,1)
                bg.inputs["Strength"].default_value=0.7
        scene.render.engine="BLENDER_EEVEE"
        scene.render.resolution_x=a.resolution_x; scene.render.resolution_y=a.resolution_y
        scene.render.resolution_percentage=a.percentage; scene.render.film_transparent=False
        scene.render.image_settings.file_format="PNG"; scene.render.use_file_extension=True
        scene.render.fps=a.fps; scene.render.fps_base=1.0
        count=round(a.seconds*a.fps); src=end-start+1
        # 120 action frames at 24 FPS make one exact 5-second cycle.
        rendered_still = None
        for i in range(count):
            frame_path = out/f"frame_{i+1:04d}.png"
            if a.hold_pose and rendered_still is not None:
                shutil.copyfile(rendered_still, frame_path)
                continue
            scene.frame_set(start+(i%src))
            scene.render.filepath=str(frame_path)
            bpy.ops.render.render(write_still=True)
            if a.hold_pose:
                rendered_still = frame_path
    finally:
        rig.animation_data.action=old["action"]
        if old["slot"] is not None and hasattr(rig.animation_data,"action_slot"):
            try: rig.animation_data.action_slot=old["slot"]
            except Exception: pass
        scene.camera=old["camera"]; scene.frame_set(old["frame"]); scene.render.filepath=old["path"]
        scene.render.engine=old["engine"]
        scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=old["res"]
        scene.render.fps=old["fps"]; scene.render.fps_base=old["fps_base"]; scene.render.film_transparent=old["transparent"]
        for ob,d in lights:
            bpy.data.objects.remove(ob,do_unlink=True); bpy.data.lights.remove(d)
        bpy.data.objects.remove(cam,do_unlink=True); bpy.data.cameras.remove(cam_data)
    print(f"SIDE_ACTION_LOOP_RENDER action={a.action} frames={count} fps={a.fps} duration={count/a.fps:.3f}s hold_pose={a.hold_pose} dir={out}")


if __name__=="__main__": main()
