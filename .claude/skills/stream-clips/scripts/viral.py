"""Render short viral-style 9:16 clips from 16:9 stream clips.
usage: python viral.py <spec.json> <src_dir> <out_dir>
spec: [{name, src, start, end, cam:[x,y,w,h] (px in 1920x1080) or "auto", lang, title, accent?, captions?,
        cam_fit?: "full" (default: whole cam window in the top 42%, gaps filled with blurred cam) | "fill" (zoom/crop)}]
cam "auto" (or no cam) runs KLİPLİNK's facecam detector (kliplink/app.py detect_cam) and also picks layout/game_x.
title: put the streamer's name in [brackets] to colour it with `accent` (hex).
captions default to on, except for Turkish (lang "tr") streams, which get none."""
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
    want_caps = c.get("captions", c["lang"] != "tr")
    words, lang = (listen.transcribe("base", np.frombuffer(pcm, dtype=np.float32), c["lang"])
                   if want_caps else ([], c["lang"]))
    ass = subs.write(words, length, tmp / "subs.ass", cfg, lang or c["lang"])
    title = tmp / "title.png"
    titlecard.render(c["title"], {**cfg, "title_accent": c.get("accent", cfg["title_accent"])}, title)
    bar = tmp / "bar.png"
    if c.get("bar"):        # e.g. "KICK.COM/ERAY": black strip under the cam, platform word in its colour
        from PIL import Image, ImageDraw, ImageFont
        f1 = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Black.otf", 46)
        f2 = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Black.otf", 34)
        word = c["bar"].split(".")[0]
        im = Image.new("RGBA", (W, 70), (0, 0, 0, 255)); d = ImageDraw.Draw(im)
        w1, w2 = d.textlength(word, font=f1), d.textlength(c["bar"], font=f2)
        x = (W - w1 - 28 - w2) / 2
        d.text((x, 35), word, font=f1, fill=c.get("bar_color", "#53FC18"), anchor="lm")
        d.text((x + w1 + 28, 36), c["bar"], font=f2, fill="white", anchor="lm")
        im.save(bar)

    if c.get("cam", "auto") == "auto":
        sys.path.insert(0, "/home/user/SHORTS-V-DEO/kliplink")
        import app as kliplink  # noqa: E402
        srcp = src_dir / c["src"]
        det = kliplink.detect_cam(srcp, kliplink.probe(srcp))
        c["cam"] = det.get("window", det["cam"])
        c.setdefault("layout", det["layout"])
        if det["layout"] != "blur":
            c.setdefault("game_x", det["game"][0])
        print("cam", name, det, flush=True)
    rate = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=avg_frame_rate",
                           "-of", "csv=p=0", str(src_dir / c["src"])], capture_output=True, text=True).stdout.strip()
    try:
        num, den = (rate.split("/") + ["1"])[:2]
        fps = 60 if float(num) / float(den or 1) >= 50 else 30   # keep 60 fps streams smooth
    except ValueError:
        fps = 30
    x, y, w, h = c["cam"]
    full = c.get("cam_fit", "full") == "full"
    top = 806 if full else min(round(W * h / w / 2) * 2, 760)
    ch = round(w * top / W / 2) * 2          # cam crop height for target aspect
    cy = y + max(0, min(h - ch, c.get("cam_dy", 0)))
    gh = H - top
    gw = round(1080 * W / gh / 2) * 2         # gameplay crop width at full source height
    gx = max(0, min(1920 - gw, c.get("game_x", (1920 - gw) // 2)))
    if c.get("layout") == "blur":   # whole 16:9 frame over a blurred copy (cam and game change places)
        top = (H - round(W * 9 / 16)) // 2
        stack = (f"[0:v]fps={fps},split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,"
                 f"crop={W}:{H},boxblur=30:2[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2[st];")
    else:
        camf = (f"[s1]crop={w}:{h}:{x}:{y},split[c1][c2];[c1]scale={W}:{top}:force_original_aspect_ratio=increase,"
                f"crop={W}:{top},boxblur=20:2[cbg];[c2]scale={W}:{top}:force_original_aspect_ratio=decrease:"
                f"force_divisible_by=2[cfg];[cbg][cfg]overlay=(W-w)/2:(H-h)/2,setsar=1[cam];" if full else
                f"[s1]crop={w}:{ch}:{x}:{cy},scale={W}:{top}[cam];")
        # fps=30 once, before splitting: 60 fps / VFR sources otherwise judder (dropped + repeated frames)
        stack = (f"[0:v]fps={fps},split[s1][s2];" + camf +
                 f"[s2]crop={gw}:1080:{gx}:0,scale={W}:{gh},setsar=1[game];[cam][game]vstack[st];")
    graph = (stack + f"[st]ass={ass.name}[sub];"
             + (f"[2:v]null[b];[sub][b]overlay=0:{top}[sb];[1:v]scale='min(iw,1000)':-1[t];"
                f"[sb][t]overlay=(W-w)/2:{top}+70+12[v]" if c.get("bar") else
                f"[1:v]scale='min(iw,1000)':-1[t];[sub][t]overlay=(W-w)/2:{top}-h/2[v]"))
    out = out_dir / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(c["start"]), "-t", str(length),
                    "-i", str(src_dir / c["src"]), "-i", str(title)] + (["-i", str(bar)] if c.get("bar") else []) + ["-filter_complex", graph,
                    "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "19", "-preset", "medium",
                    "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1",
                    "-movflags", "+faststart", str(out)], cwd=tmp, check=True)
    print("done", out, f"{length:.1f}s", flush=True)
