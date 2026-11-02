"""Build a local HTML review page for landmark overlays and quality metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("overlays", type=Path)
    parser.add_argument("quality", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    quality = json.loads(args.quality.read_text(encoding="utf-8"))
    images = sorted(args.overlays.glob("*_landmarks.png"))
    low = quality.get("lowest_quality_first", [])[:20]
    rows = "".join(f"<tr><td>{x['name']}</td><td>{x['visible_rate']:.3f}</td><td>{x['mean_confidence']:.3f}</td></tr>" for x in low)
    imgs = "".join(f'<figure><img src="{p.name}"><figcaption>{p.stem}</figcaption></figure>' for p in images)
    controls = "".join(f'<label><input type="checkbox" data-name="{x["name"]}"> approve {x["name"]}</label><br>' for x in low)
    html = f'''<!doctype html><meta charset="utf-8"><title>CreatureMotionAI Landmark Review</title>
<style>body{{font-family:Arial;background:#202124;color:#eee;margin:24px}} img{{max-width:900px;border:1px solid #666}} figure{{display:inline-block;vertical-align:top;margin:8px}} table{{border-collapse:collapse}}td,th{{border:1px solid #777;padding:6px}}button{{padding:8px;margin:8px 0}}</style>
<h1>Landmark review</h1><p>Orange points are detector proposals, not approved labels.</p>
<h2>Lowest-quality landmarks</h2><table><tr><th>Landmark</th><th>Visible rate</th><th>Mean confidence</th></tr>{rows}</table>
<h2>Approval</h2><p>Approve only landmarks that are visibly correct in the overlays.</p><div>{controls}</div><button onclick="downloadManifest()">Download approval manifest</button>
<h2>Overlay frames</h2>{imgs}'''
    html += '''<script>function downloadManifest(){const items={};document.querySelectorAll('input[data-name]').forEach(x=>items[x.dataset.name]={status:x.checked?'approved':'needs_review',correction:null});const out={status:'reviewed_in_browser',approval_rule:'Only approved landmarks may be triangulated.',landmarks:items};const blob=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='landmark_approval_manifest.json';a.click();}</script>'''
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(json.dumps({"output": str(args.output), "images": len(images), "flagged_landmarks": len(low)}, indent=2))


if __name__ == "__main__":
    main()
