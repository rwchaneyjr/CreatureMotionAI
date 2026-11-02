"""Create a semi-automatic two-view leg identity review and correction package.

The page is intentionally review-first: rig projections and detector proposals are
shown as proposals, while dragged points are exported as manual corrections. No
point is promoted to a confirmed observation until the user reviews it.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path


def image_data(path: Path) -> str:
    if not path.exists():
        return ""
    ext = path.suffix.lower().lstrip(".") or "png"
    return f"data:image/{'jpeg' if ext in ('jpg', 'jpeg') else ext};base64," + base64.b64encode(path.read_bytes()).decode()


def pick_image(samples: Path, frame: int, camera: str) -> str:
    patterns = [
        f"frame_{frame:06d}_{camera}.png",
        f"frame_{frame:06d}_{camera}.jpg",
        f"frame_{frame:06d}_camera_{camera[-1]}.png",
    ]
    for name in patterns:
        p = samples / name
        if p.exists():
            return image_data(p)
    return ""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--proposals", type=Path, required=True)
    p.add_argument("--identity-map", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--samples-dir", type=Path, required=True)
    p.add_argument("--frames", type=int, nargs="+", default=[1, 6, 12, 18, 24])
    args = p.parse_args()
    proposals = json.loads(args.proposals.read_text(encoding="utf-8"))
    identities = json.loads(args.identity_map.read_text(encoding="utf-8"))
    by_frame = {int(row.get("frame", 0)): row for row in proposals.get("frames", [])}
    legs = []
    identity_rows = identities.get("legs", {})
    if isinstance(identity_rows, list):
        identity_rows = {row.get("name", str(row.get("id"))): row for row in identity_rows}
    for root, leg in identity_rows.items():
        names = leg["landmarks"]
        # The review exposes hip, knee, and the distal foot endpoint even when
        # the identity map also contains the intermediate foot head.
        selected = [names[0], names[1], names[-1]] if len(names) >= 3 else names
        legs.append({"id": root, "landmarks": selected, "color": leg.get("color", "#ffffff")})
    cards = []
    initial = {"status": "unreviewed", "source": str(args.proposals.resolve()), "frames": []}
    for frame in args.frames:
        row = by_frame.get(frame, {})
        points = []
        for leg in legs:
            for name in leg["landmarks"]:
                item = None
                for camera in ("camera_A", "camera_B"):
                    candidate = row.get(camera, {}).get("landmarks", {}).get(name)
                    if candidate and candidate.get("rig_gate") == "accepted":
                        item = candidate
                        break
                points.append({"name": name, "leg": leg["id"], "x": float((item or {}).get("x", 0)), "y": float((item or {}).get("y", 0)), "state": "proposal" if item else "estimated", "confidence": float((item or {}).get("confidence", 0.0))})
        initial["frames"].append({"frame": frame, "points": points})
        cards.append({"frame": frame, "a": pick_image(args.samples_dir, frame, "camera_A"), "b": pick_image(args.samples_dir, frame, "camera_B"), "points": points})
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "initial_landmarks.json").write_text(json.dumps(initial, indent=2), encoding="utf-8")
    payload = json.dumps(cards).replace("</", "<\\/")
    html = r'''<!doctype html><meta charset="utf-8"><title>CreatureMotionAI Leg Identity Review</title>
<style>body{font:14px sans-serif;background:#202124;color:#eee;margin:16px}h1{font-size:20px}.card{border:1px solid #555;margin:14px 0;padding:10px}.views{display:flex;gap:12px;flex-wrap:wrap}.view{position:relative;width:640px;max-width:48vw}.view img{width:100%;display:block;background:#333}.pts{position:absolute;inset:0;pointer-events:none}.pt{position:absolute;width:18px;height:18px;border-radius:50%;border:2px solid #fff;transform:translate(-50%,-50%);cursor:grab;box-sizing:border-box;color:#fff;font:bold 10px sans-serif;text-align:center;line-height:14px;text-shadow:0 0 2px #000;pointer-events:auto;touch-action:none}.pt:before,.pt:after{content:'';position:absolute;background:#fff;opacity:.9}.pt:before{width:26px;height:2px;left:-6px;top:6px}.pt:after{width:2px;height:26px;left:6px;top:-6px}.pt span{position:relative;z-index:2}.legend{display:flex;gap:8px;flex-wrap:wrap;position:sticky;top:0;background:#202124;padding:8px 0;z-index:3}.legend span{padding:4px 8px;border-radius:4px;color:#111;font-weight:bold}.help{color:#bbb}.bad{outline:2px solid #e66}</style>
<h1>CreatureMotionAI — Eight-Leg Landmark Review</h1><p class="help">Only visible detector-supported proposals are shown. Hidden or uncertain joints are kept in the exported data as uncertain, but are not drawn as dots. Drag visible points to the matching hip, knee, or foot.</p><div class="legend" id="legend"></div><div id="root"></div><button id="export">Download reviewed landmarks</button>
<script>const cards=__CARDS__;const colors={};let reviewed={status:'reviewed_in_browser',frames:[]};
function abbr(leg){return {'Leg_Front.L':'FL','Leg_Front.R':'FR','Leg_MidFront.L':'MFL','Leg_MidFront.R':'MFR','Leg_MidRear.L':'MRL','Leg_MidRear.R':'MRR','Leg_Rear.L':'RL','Leg_Rear.R':'RR'}[leg]||leg.slice(-2)}
function jointAbbr(name){return name.includes('_01_')?'H':name.includes('_02_')?'K':'F'}
function render(){const root=document.querySelector('#root');cards.forEach((c,ci)=>{const box=document.createElement('section');box.className='card';box.innerHTML='<h2>Frame '+c.frame+'</h2><div class="views"><div class="view"><b>Camera A / side</b><img src="'+c.a+'" data-camera="A"><div class="pts"></div></div><div class="view"><b>Camera B / front</b><img src="'+c.b+'" data-camera="B"><div class="pts"></div></div></div>';root.appendChild(box);const frame={frame:c.frame,points:[]};c.points.forEach((p,pi)=>{if(!colors[p.leg])colors[p.leg]=palette(Object.keys(colors).length);if(p.state!=='estimated'){['A','B'].forEach((cam,vi)=>{const holder=box.querySelectorAll('.pts')[vi];const el=document.createElement('div');el.className='pt';el.style.background=colors[p.leg];el.style.left=(p.x/640*100)+'%';el.style.top=(p.y/720*100)+'%';el.innerHTML='<span>'+abbr(p.leg)+'-'+jointAbbr(p.name)+'</span>';el.title=p.leg+' / '+jointAbbr(p.name)+' / '+p.state;el.dataset.x=p.x;el.dataset.y=p.y;el.dataset.name=p.name;el.onpointerdown=e=>drag(e,el,holder);holder.appendChild(el);});}frame.points.push({name:p.name,leg:p.leg,abbreviation:abbr(p.leg)+'-'+jointAbbr(p.name),state:p.state,confidence:p.confidence,camera_A:{x:p.x,y:p.y},camera_B:{x:p.x,y:p.y}})});reviewed.frames.push(frame)});Object.entries(colors).forEach(([k,v])=>{const s=document.createElement('span');s.style.background=v;s.textContent=abbr(k)+' = '+k+' | H hip, K knee, F foot';legend.appendChild(s)})}
function palette(i){return ['#e6194b','#f58231','#ffe119','#3cb44b','#42d4f4','#4363d8','#911eb4','#f032e6'][i%8]}
function drag(ev,el,holder){ev.preventDefault();const move=e=>{const r=holder.getBoundingClientRect();const x=Math.max(0,Math.min(r.width,e.clientX-r.left));const y=Math.max(0,Math.min(r.height,e.clientY-r.top));el.style.left=x/r.width*100+'%';el.style.top=y/r.height*100+'%';el.dataset.x=Math.round(x/r.width*640);el.dataset.y=Math.round(y/r.height*720);el.title=el.dataset.name+' / manual_correction'};const up=()=>{el.releasePointerCapture?.(ev.pointerId);el.onpointermove=null;el.onpointerup=null};el.setPointerCapture?.(ev.pointerId);el.onpointermove=move;el.onpointerup=up}
document.querySelector('#export').onclick=()=>{reviewed.frames.forEach(f=>f.points.forEach(p=>{const box=[...document.querySelectorAll('.card')].find(x=>x.querySelector('h2').textContent.includes(f.frame));const els=[...box.querySelectorAll('.pt')].filter(x=>x.dataset.name===p.name);if(els.length){p.camera_A={x:+els[0].dataset.x,y:+els[0].dataset.y};p.camera_B={x:+els[1].dataset.x,y:+els[1].dataset.y};p.state='manual_reviewed'}}));const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(reviewed,null,2)],{type:'application/json'}));a.download='leg_identity_reviewed.json';a.click()};render();</script>'''.replace("__CARDS__", payload)
    (args.output / "review_leg_identity.html").write_text(html, encoding="utf-8")
    print(json.dumps({"output": str(args.output), "frames": args.frames, "legs": len(legs), "instructions": "Open review_leg_identity.html in a browser; drag points, then click Download reviewed landmarks."}, indent=2))


if __name__ == "__main__":
    main()
