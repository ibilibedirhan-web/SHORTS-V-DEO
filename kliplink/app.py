"""KLİPLİNK — Kick kliplerini ve kendi videolarını 9:16 (üst %42 kamera, alt %58 oyun) klibe çevirir.

Çalıştırma:  python app.py   ->  http://localhost:8000
Gerekenler:  Python 3.10+, ffmpeg, `pip install -r requirements.txt`
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, abort, jsonify, request, send_file, send_from_directory

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SRC, OUT, WORK = DATA / "sources", DATA / "out", DATA / "work"
for d in (SRC, OUT, WORK):
    d.mkdir(parents=True, exist_ok=True)

# Başlık kartı (renkli [isim] + emoji) stream-clips becerisinden gelir.
sys.path.insert(0, str(HERE.parent / ".claude" / "skills" / "stream-clips" / "scripts"))
from sc import titlecard  # noqa: E402

W, H = 1080, 1920
CAM_H = round(H * 0.42)          # 806 px  -> üst %42 kamera
GAME_H = H - CAM_H               # 1114 px -> alt %58 oyun
BAR_H = 70
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36"}
RAGE = re.compile(r"(sinir|rage|kriz|çıldır|cildir|delir|bağır|bagir|kavga|küfür|kufur|noluyo|ne oluyo|amk|aq|"
                  r"yuh|ban|kopt|patla|şok|sok|olamaz|lan\b|!{2,})", re.I)

app = Flask(__name__, static_folder=str(HERE / "static"), static_url_path="/static")
jobs = {}


def ffmpeg_env():
    env = dict(os.environ)
    proxy = env.get("HTTPS_PROXY") or env.get("https_proxy")
    if proxy and not env.get("http_proxy"):
        env["http_proxy"] = proxy          # ffmpeg yalnızca http_proxy okur
    return env


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    return {"width": s["width"], "height": s["height"], "duration": float(j["format"]["duration"])}


def meta_path(sid):
    return SRC / f"{sid}.json"


def save_meta(sid, meta):
    meta_path(sid).write_text(json.dumps(meta, ensure_ascii=False))


def load_meta(sid):
    if not re.fullmatch(r"[\w-]+", sid or "") or not meta_path(sid).exists():
        abort(404)
    return json.loads(meta_path(sid).read_text())


# ---------------------------------------------------------------- Kick
def is_rage(title):
    letters = [c for c in title if c.isalpha()]
    shouting = len(letters) > 3 and all(c == c.upper() for c in letters)
    return bool(RAGE.search(title)) or shouting


@app.get("/api/clips")
def clips():
    ch = re.sub(r"[^\w-]", "", request.args.get("channel", "eray").lower()) or "eray"
    t = request.args.get("time", "week")
    sort = request.args.get("sort", "view")
    url = f"https://kick.com/api/v2/channels/{ch}/clips?sort={sort}&time={t}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            data = json.load(r)
    except Exception as e:
        return jsonify(error=f"Kick'e ulaşılamadı: {e}"), 502
    items = []
    for k in data.get("clips", []):
        title = k.get("title") or ""
        items.append({
            "id": k["id"], "title": title, "views": k.get("views", 0), "duration": k.get("duration", 0),
            "created_at": k.get("created_at", ""), "thumbnail": k.get("thumbnail_url"),
            "url": k.get("clip_url"), "category": (k.get("category") or {}).get("name", ""),
            "rage": is_rage(title), "channel": ch,
        })
    return jsonify(clips=items, channel=ch)


@app.get("/api/thumb")
def thumb():
    url = request.args.get("u", "")
    if not re.fullmatch(r"https://clips\.kick\.com/[\w/.-]+\.(webp|jpg|png)", url):
        abort(400)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            body, ctype = r.read(), r.headers.get("Content-Type", "image/webp")
    except Exception:
        abort(404)
    return body, 200, {"Content-Type": ctype, "Cache-Control": "max-age=86400"}


@app.post("/api/import")
def import_clip():
    j = request.get_json(force=True)
    url, ch, cid = j.get("url", ""), j.get("channel", ""), j.get("id", "")
    if not url.startswith("https://") or "kick.com" not in url:
        return jsonify(error="Geçersiz Kick klip adresi"), 400
    sid = re.sub(r"[^\w-]", "", cid)[:60] or uuid.uuid4().hex[:12]
    dst = SRC / f"{sid}.mp4"
    if not dst.exists():
        tmp = SRC / f"{sid}.part.mp4"
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", url, "-c", "copy", "-bsf:a", "aac_adtstoasc", str(tmp)],
                           capture_output=True, text=True, env=ffmpeg_env())
        if r.returncode != 0:
            return jsonify(error="İndirme başarısız: " + r.stderr[-300:]), 502
        tmp.rename(dst)
    meta = {"id": sid, "name": j.get("title") or sid, "channel": ch, **probe(dst)}
    save_meta(sid, meta)
    return jsonify(meta)


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify(error="Dosya yok"), 400
    sid = "u" + uuid.uuid4().hex[:11]
    raw = SRC / f"{sid}.orig"
    f.save(raw)
    dst = SRC / f"{sid}.mp4"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)],
                       capture_output=True, text=True)
    raw.unlink(missing_ok=True)
    if r.returncode != 0:
        return jsonify(error="Video okunamadı: " + r.stderr[-300:]), 400
    meta = {"id": sid, "name": Path(f.filename or "video").stem, "channel": "", **probe(dst)}
    save_meta(sid, meta)
    return jsonify(meta)


@app.get("/api/source/<sid>.mp4")
def source(sid):
    load_meta(sid)
    dl = request.args.get("dl")
    return send_file(SRC / f"{sid}.mp4", mimetype="video/mp4", conditional=True,
                     as_attachment=bool(dl), download_name=f"{dl or sid}.mp4")


# ---------------------------------------------------------------- facecam
def face_model():
    for p in (HERE / "models" / "face_yunet.onnx", Path.home() / ".streamclips" / "models" / "face_yunet.onnx"):
        if p.exists() and p.stat().st_size > 100_000:
            return p
    p = HERE / "models" / "face_yunet.onnx"
    p.parent.mkdir(exist_ok=True)
    urllib.request.urlretrieve("https://huggingface.co/opencv/face_detection_yunet/resolve/main/"
                               "face_detection_yunet_2023mar.onnx", p)
    return p


def box(x, y, w, h, vw, vh):
    w, h = min(w, vw), min(h, vh)
    x, y = max(0, min(x, vw - w)), max(0, min(y, vh - h))
    return [round(x), round(y), round(w), round(h)]


def game_box(vw, vh, cam, ar):
    gw = min(vw, vh * ar)
    gx = (vw - gw) / 2
    if cam:                                  # kameradan uzaklaş
        cx, _, cw, _ = cam
        if cx + cw / 2 < vw / 2:
            gx = max(gx, min(cx + cw, vw - gw))
        else:
            gx = min(gx, max(0, cx - gw))
    return box(gx, 0, gw, vh, vw, vh)


def detect_cam(path, meta):
    """Kameranın yerini bulur. Döner: {layout, cam:[x,y,w,h], game:[x,y,w,h], found}"""
    vw, vh, dur = meta["width"], meta["height"], meta["duration"]
    cam_ar, game_ar = W / CAM_H, W / GAME_H
    cap = cv2.VideoCapture(str(path))
    sw = 640
    sh = round(vh * sw / vw)
    det = cv2.FaceDetectorYN.create(str(face_model()), "", (sw, sh), 0.7, 0.3, 50)
    faces, gxs, gys = [], [], []
    for i in range(10):
        cap.set(cv2.CAP_PROP_POS_MSEC, 1000 * dur * (i + 0.5) / 10)
        ok, fr = cap.read()
        if not ok:
            continue
        small = cv2.resize(fr, (sw, sh))
        g = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (3, 3), 0).astype(np.float32)
        gxs.append(np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)))
        gys.append(np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1)))
        _, f = det.detect(small)
        for x, y, w, h, *_rest, score in (f if f is not None else []):
            faces.append((x * vw / sw, y * vh / sh, w * vw / sw, h * vh / sh, score))
    cap.release()
    if not faces:
        cw = vw * 0.3
        return {"layout": "split", "found": False, "cam": box(0, 0, cw, cw / cam_ar, vw, vh),
                "game": game_box(vw, vh, None, game_ar)}
    # aynı yerde en sık görülen yüz kümesi
    faces.sort(key=lambda f: -f[2])
    best, best_n = None, 0
    for f in faces:
        n = sum(1 for g in faces if abs(g[0] + g[2] / 2 - f[0] - f[2] / 2) < f[2] and abs(g[1] - f[1]) < f[3])
        if n > best_n:
            best, best_n = f, n
    fx, fy, fw, fh, _ = best
    if fw > vw * 0.16:                       # tam ekran kamera / stüdyo çekimi
        return {"layout": "blur", "found": True, "cam": [0, 0, vw, vh], "game": [0, 0, vw, vh]}

    # Kamera penceresinin kenarları: kareden kareye sabit kalan düz çizgiler (medyan kenar haritası).
    k = sw / vw
    gx_med = np.median(np.stack(gxs), axis=0)
    gy_med = np.median(np.stack(gys), axis=0)
    sfx, sfy, sfw, sfh = fx * k, fy * k, fw * k, fh * k
    r0, r1 = int(max(0, sfy - sfh)), int(min(sh, sfy + 2 * sfh))
    c0, c1 = int(max(0, sfx - sfw * 1.5)), int(min(sw, sfx + sfw * 2.5))
    colstr = gx_med[r0:r1].mean(axis=0)
    rowstr = gy_med[:, c0:c1].mean(axis=1)

    def edge(strength, lo, hi, default, thr):
        lo, hi = max(0, int(lo)), min(len(strength), int(hi))
        if hi - lo < 2:
            return default
        i = lo + int(np.argmax(strength[lo:hi]))
        return i if strength[i] > thr else default

    tc, tr = colstr.mean() * 2.2, rowstr.mean() * 2.2
    left = edge(colstr, sfx - sfw * 4, sfx - sfw * 0.4, 0, tc)
    right = edge(colstr, sfx + sfw * 1.4, sfx + sfw * 5, sw, tc)
    top = edge(rowstr, sfy - sfh * 3, sfy - sfh * 0.3, 0, tr)
    bottom = edge(rowstr, sfy + sfh * 1.5, sfy + sfh * 5, sh, tr)
    if left < sw * 0.02: left = 0
    if right > sw * 0.98: right = sw
    if top < sh * 0.02: top = 0
    if bottom > sh * 0.98: bottom = sh
    L, R, T, B = left / k, right / k, top / k, bottom / k
    if R - L > fw * 7 or B - T > fh * 7:      # kenar bulunamadı -> yüz etrafında tahmin
        cw = min(vw, fw * 4.6)
        ch = cw / cam_ar
        L, T = fx + fw / 2 - cw / 2, fy + fh * 0.45 - ch * 0.42
        R, B = L + cw, T + ch
    # pencereyi %42 alanın oranına (1080x806) uydur, yüzü ortada tut
    ww, hh = R - L, B - T
    if ww / hh > cam_ar:
        cw, ch = hh * cam_ar, hh
        cx, cy = min(max(fx + fw / 2 - cw / 2, L), R - cw), T
    else:
        cw, ch = ww, ww / cam_ar
        cx, cy = L, min(max(fy + fh / 2 - ch * 0.45, T), B - ch)
    cam = box(cx, cy, cw, ch, vw, vh)
    win = [round(L), round(T), round(R - L), round(B - T)]
    return {"layout": "split", "found": True, "cam": cam, "window": win, "game": game_box(vw, vh, win, game_ar)}


@app.get("/api/detect/<sid>")
def detect(sid):
    meta = load_meta(sid)
    return jsonify(detect_cam(SRC / f"{sid}.mp4", meta))


# ---------------------------------------------------------------- render
def bold_font():
    for cand in ("/usr/share/fonts/opentype/inter/Inter-Black.otf", "C:/Windows/Fonts/ariblk.ttf",
                 "/System/Library/Fonts/Supplemental/Arial Black.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(cand).exists():
            return cand
    return None


def make_bar(text, color, path):
    from PIL import Image, ImageDraw, ImageFont
    font = bold_font()
    f1 = ImageFont.truetype(font, 46) if font else ImageFont.load_default(46)
    f2 = ImageFont.truetype(font, 34) if font else ImageFont.load_default(34)
    text = text.upper()
    word = text.split(".")[0]
    im = Image.new("RGBA", (W, BAR_H), (0, 0, 0, 255))
    d = ImageDraw.Draw(im)
    w1, w2 = d.textlength(word, font=f1), d.textlength(text, font=f2)
    x = (W - w1 - 28 - w2) / 2
    d.text((x, BAR_H / 2), word, font=f1, fill=color, anchor="lm")
    d.text((x + w1 + 28, BAR_H / 2 + 1), text, font=f2, fill="white", anchor="lm")
    im.save(path)


def captions_ass(src, start, length, lang, path):
    try:
        from sc import listen, settings, subs
        import faster_whisper  # noqa: F401
    except ImportError:
        raise RuntimeError("Altyazı bu sunucuda kurulu değil (faster-whisper yok). Altyazıyı kapatıp tekrar dene.")
    cfg = settings.load()
    cfg.update(cap_words=2, cap_size=92, cap_y=0.76, cap_font="Inter Black", cap_outline=8)
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(length), "-i", str(src),
                          "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    words, lg = listen.transcribe("base", np.frombuffer(pcm, dtype=np.float32), lang or None)
    subs.write(words, length, path, cfg, lg or lang)


def render_job(jid, p):
    job = jobs[jid]
    try:
        sid = p["id"]
        meta = json.loads(meta_path(sid).read_text())
        src = SRC / f"{sid}.mp4"
        start = max(0.0, float(p.get("start", 0)))
        end = min(meta["duration"], float(p.get("end", meta["duration"])))
        length = max(0.5, end - start)
        work = WORK / jid
        work.mkdir(parents=True, exist_ok=True)
        inputs = ["-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", str(src)]
        n = 1
        if p.get("layout") == "blur":
            seam = (H - round(W * meta["height"] / meta["width"])) // 2
            g = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                 f"boxblur=30:2[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2[v0];")
        else:
            cx, cy, cw, ch = [int(v) for v in p["cam"]]
            gx, gy, gw, gh = [int(v) for v in p["game"]]
            g = (f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={W}:{CAM_H},setsar=1[cam];"
                 f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale={W}:{GAME_H},setsar=1[game];[cam][game]vstack[v0];")
            seam = CAM_H
        last = "v0"
        if p.get("captions"):
            job["step"] = "altyazı çıkarılıyor"
            captions_ass(src, start, length, p.get("lang", ""), work / "subs.ass")
            g += f"[{last}]ass=subs.ass[v1];"
            last = "v1"
        title_y = None
        if p.get("bar"):
            make_bar(p["bar"], p.get("bar_color", "#53FC18"), work / "bar.png")
            inputs += ["-i", str(work / "bar.png")]
            g += f"[{last}][{n}:v]overlay=0:{seam}[v2];"
            last, n, title_y = "v2", n + 1, seam + BAR_H + 12
        if p.get("title", "").strip():
            cfg = {"title_size": 56, "title_bg": "FFFFFF", "title_fg": "111111", "width": W,
                   "title_font_file": None, "title_accent": p.get("accent", "#E5004F").lstrip("#")}
            titlecard.render(p["title"].strip(), cfg, work / "title.png")
            inputs += ["-i", str(work / "title.png")]
            ty = f"{title_y}" if title_y is not None else f"{seam}-h/2"
            g += f"[{n}:v]scale='min(iw,1000)':-1[t];[{last}][t]overlay=(W-w)/2:{ty}[v3];"
            last, n = "v3", n + 1
        g += f"[{last}]null[vout]"
        name = re.sub(r"[^\w-]+", "-", p.get("name") or sid).strip("-")[:50] or sid
        out = OUT / f"{name}-{jid[:6]}.mp4"
        job["step"] = "video oluşturuluyor"
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", g, "-map", "[vout]",
                            "-map", "0:a?", "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-r", "30",
                            "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1", "-movflags", "+faststart",
                            str(out)], cwd=work, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-500:])
        job.update(status="done", step="hazır", file=out.name)
    except Exception as e:
        job.update(status="error", step=str(e))


@app.post("/api/render")
def render():
    p = request.get_json(force=True)
    load_meta(p.get("id", ""))
    jid = uuid.uuid4().hex
    jobs[jid] = {"status": "running", "step": "başlıyor", "started": time.time()}
    threading.Thread(target=render_job, args=(jid, p), daemon=True).start()
    return jsonify(job=jid)


@app.get("/api/job/<jid>")
def job(jid):
    return jsonify(jobs.get(jid) or {"status": "error", "step": "iş bulunamadı"})


@app.get("/api/out/<name>")
def out_file(name):
    if not re.fullmatch(r"[\w.-]+\.mp4", name) or not (OUT / name).exists():
        abort(404)
    return send_file(OUT / name, mimetype="video/mp4", conditional=True,
                     as_attachment=bool(request.args.get("dl")), download_name=name)


@app.get("/")
def index():
    return send_from_directory(HERE / "static", "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"KLİPLİNK çalışıyor: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, threaded=True)
