"""Render short viral-style 9:16 clips from 16:9 stream clips.
usage: python viral.py <spec.json> <src_dir> <out_dir>
spec: [{name, src, start, end, cam:[x,y,w,h] (px in 1920x1080), lang, title}]"""
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, "/home/user/SHORTS-V-DEO/.claude/skills/stream-clips/scripts")
from sc import listen, settings, subs, titlecard  # noqa: E402

spec, src_dir, out_dir = json.load(open(sys.argv[1])), Path(sys.argv[2]), Path(sys.argv[3])
out_dir.mkdir(parents=True, exist_ok=True)
cfg = settings.load()
cfg.update(cap_words=2, cap_size=92, cap_y=0.74, cap_font="Inter Black", cap_outline=8, captions=True)
W, H = 1080, 1920

for c in spec:
    name, length = c["name"], c["end"] - c["start"]
    tmp = out_dir / f"{name}.work"
    tmp.mkdir(exist_ok=True)
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(c["start"]), "-t", str(length), "-i",
                          str(src_dir / c["src"]), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    import numpy as np
    words, lang = listen.transcribe("base", np.frombuffer(pcm, dtype=np.float32), c["lang"])
    ass = subs.write(words, length, tmp / "subs.ass", cfg, lang or c["lang"])
    title = tmp / "title.png"
    titlecard.render(c["title"], cfg, title)

    x, y, w, h = c["cam"]
    top = min(round(W * h / w / 2) * 2, 760)
    ch = round(w * top / W / 2) * 2          # cam crop height for target aspect
    cy = y + max(0, min(h - ch, c.get("cam_dy", 0)))
    gh = H - top
    gw = round(1080 * W / gh / 2) * 2         # gameplay crop width at full source height
    gx = c.get("game_x", (1920 - gw) // 2)
    graph = (f"[0:v]crop={w}:{ch}:{x}:{cy},scale={W}:{top}[cam];"
             f"[0:v]crop={gw}:1080:{gx}:0,scale={W}:{gh}[game];"
             f"[cam][game]vstack[st];[st]ass={ass.name}[sub];"
             f"[1:v]scale='min(iw,1000)':-1[t];[sub][t]overlay=(W-w)/2:{top}-h/2[v]")
    out = out_dir / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(c["start"]), "-t", str(length),
                    "-i", str(src_dir / c["src"]), "-i", str(title), "-filter_complex", graph,
                    "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "19", "-preset", "medium",
                    "-r", "30", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1",
                    "-movflags", "+faststart", str(out)], cwd=tmp, check=True)
    print("done", out, f"{length:.1f}s", flush=True)
