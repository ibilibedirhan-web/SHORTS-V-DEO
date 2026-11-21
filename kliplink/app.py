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

# Çıkış genişliği: bilgisayarda 1080 (1080x1920). Zayıf ücretsiz sunucularda OUT_W=720 ile 720x1280.
W = int(os.environ.get("OUT_W", 1080)) // 2 * 2
H = round(W * 16 / 9 / 2) * 2
K = W / 1080                     # tüm yazı/şerit ölçüleri bu oranla küçülür
CAM_H = round(H * 0.42)          # üst %42 kamera  (1080'de 806 px)
GAME_H = H - CAM_H               # alt %58 oyun    (1080'de 1114 px)
BAR_H = round(70 * K)
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


@app.get("/api/channel")
def channel():
    ch = re.sub(r"[^\w-]", "", request.args.get("channel", "eray").lower()) or "eray"
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://kick.com/api/v2/channels/{ch}", headers=UA),
                                    timeout=30) as r:
            j = json.load(r)
    except Exception as e:
        return jsonify(error=f"Kanal bulunamadı: {e}"), 404
    ls = j.get("livestream") or {}
    user = j.get("user") or {}
    return jsonify(
        slug=j.get("slug", ch), name=user.get("username") or ch, followers=int(j.get("followers_count") or 0),
        avatar=user.get("profile_pic"), verified=bool(j.get("verified")),
        live=bool(ls.get("is_live")), title=ls.get("session_title", ""), viewers=int(ls.get("viewer_count") or 0),
        started=ls.get("start_time", ""), category=((ls.get("categories") or [{}])[0] or {}).get("name", ""),
    )


@app.get("/api/thumb")
def thumb():
    url = request.args.get("u", "")
    if not re.fullmatch(r"https://(clips\.kick\.com|files\.kick\.com)/[\w/.%-]+(\.(webp|jpg|jpeg|png))?(\?[\w=&.-]*)?", url):
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


@app.get("/api/meta/<sid>")
def meta_info(sid):
    sid = re.sub(r"[^\w-]", "", sid)
    if not (SRC / f"{sid}.mp4").exists() or not meta_path(sid).exists():
        abort(404)
    return jsonify(load_meta(sid))


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify(error="Dosya yok"), 400
    sid = "u" + uuid.uuid4().hex[:11]
    raw = SRC / f"{sid}.orig"
    f.save(raw)
    dst = SRC / f"{sid}.mp4"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-threads", "1", "-i", str(raw), "-c:v", "libx264",
                        "-preset", "faster", "-threads", "1", "-x264-params", "rc-lookahead=0:ref=1:bframes=0",
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


DEBUG_CAM = os.environ.get("DEBUG_CAM")


def cam_window(V, Hh, M, face, k):
    """Yüzü içine alan kamera penceresini arar (küçük ölçekte). Döner ((L,T,R,B), skor) ya da (None, 0).
    V/Hh: kareler boyunca sabit kalan dikey/yatay kenar oranı, M: ortalama hareket."""
    sh, sw = V.shape
    Vc = np.vstack([np.zeros((1, sw)), np.cumsum(V, 0)])
    Hc = np.hstack([np.zeros((sh, 1)), np.cumsum(Hh, 1)])
    Mi = cv2.integral(M)
    fx, fy, fw, fh = [v * k for v in face]
    cx, cy = fx + fw / 2, fy + fh / 2
    band = V[int(max(0, fy - fh)):int(min(sh, fy + 2 * fh))].mean(0)
    cband = Hh[:, int(max(0, fx - fw)):int(min(sw, fx + 2 * fw))].mean(1)

    def peaks(p, lo, hi, kmax=8):
        lo, hi = max(1, int(lo)), min(len(p) - 1, int(hi))
        idx = [i for i in range(lo, hi) if p[i] >= p[i - 1] and p[i] >= p[i + 1] and p[i] > 0.15]
        return sorted(idx, key=lambda i: -p[i])[:kmax]

    def msum(x0, y0, x1, y1):
        x0, x1 = max(0, min(sw, x0)), max(0, min(sw, x1))
        y0, y1 = max(0, min(sh, y0)), max(0, min(sh, y1))
        if x1 <= x0 or y1 <= y0:
            return None
        return (Mi[y1, x1] - Mi[y0, x1] - Mi[y1, x0] + Mi[y0, x0]) / ((x1 - x0) * (y1 - y0))

    def contrast(out, inn):                  # dışarısı (oyun) içeriden (kamera) hareketliyse gerçek kenar
        if out is None or inn is None:
            return 0.5
        return float(np.clip((out - inn) / (out + inn + 1e-3), 0, 1))

    def vside(x, t, b):
        return 0.55 if x <= 0 or x >= sw else (Vc[b, x] - Vc[t, x]) / max(1, b - t)

    def hside(y, l, r):
        return 0.55 if y <= 0 or y >= sh else (Hc[y, r] - Hc[y, l]) / max(1, r - l)

    Ls = [0] + peaks(band, cx - fw * 6, fx - fw * 0.2)
    Rs = [sw] + peaks(band, fx + fw * 1.2, cx + fw * 6)
    Ts = [0] + peaks(cband, cy - fh * 5, fy - fh * 0.1)
    Bs = [sh] + peaks(cband, fy + fh * 1.1, cy + fh * 6)
    best, bs, d = None, 0.0, 6
    for L in Ls:
        for R in Rs:
            w = R - L
            if w < fw * 1.8 or w > sw * 0.6 or not 0.07 <= fw / w <= 0.55:
                continue
            for T in Ts:
                for B in Bs:
                    h = B - T
                    if h < fh * 1.6 or not 0.9 <= w / h <= 2.6:
                        continue
                    s = [vside(L, T, B), vside(R, T, B), hside(T, L, R), hside(B, L, R)]
                    c = [contrast(msum(L - d, T, L, B) if L > 0 else None, msum(L, T, L + d, B)),
                         contrast(msum(R, T, R + d, B) if R < sw else None, msum(R - d, T, R, B)),
                         contrast(msum(L, T - d, R, T) if T > 0 else None, msum(L, T, R, T + d)),
                         contrast(msum(L, B, R, B + d) if B < sh else None, msum(L, B - d, R, B))]
                    s = [a + 0.4 * b for a, b in zip(s, c)]
                    sc = 0.5 * np.mean(s) + 0.5 * min(s) + 0.02 * w * h / (sw * sh) - 0.12 * abs(np.log(w / h / 1.78))
                    if sc > bs:
                        bs, best = sc, (L, T, R, B)
    return best, bs


def detect_cam(path, meta):
    """Kameranın yerini bulur. Döner: {layout, cam:[x,y,w,h], window, game:[x,y,w,h], found}"""
    vw, vh, dur = meta["width"], meta["height"], meta["duration"]
    cam_ar, game_ar = W / CAM_H, W / GAME_H
    cap = cv2.VideoCapture(str(path))
    sw = 640
    sh = round(vh * sw / vw)
    k = sw / vw
    det = cv2.FaceDetectorYN.create(str(face_model()), "", (sw, sh), 0.7, 0.3, 50)
    faces, grays = [], []
    V = np.zeros((sh, sw), np.float32)
    Hh = np.zeros((sh, sw), np.float32)
    n = 24
    for i in range(n):
        cap.set(cv2.CAP_PROP_POS_MSEC, 1000 * dur * (i + 0.5) / n)
        ok, fr = cap.read()
        if not ok:
            continue
        small = cv2.resize(fr, (sw, sh))
        g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        e = cv2.Canny(g, 40, 120) > 0
        gx = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0))
        gy = np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1))
        V += e & (gx > gy)
        Hh += e & (gy >= gx)
        grays.append(cv2.GaussianBlur(g, (5, 5), 0).astype(np.float32))
        _, f = det.detect(small)
        for x, y, w, h, *_rest, score in (f if f is not None else []):
            faces.append((x / k, y / k, w / k, h / k))
    cap.release()
    if not faces or len(grays) < 3:
        cw = vw * 0.3
        return {"layout": "split", "found": False, "cam": box(0, 0, cw, cw / cam_ar, vw, vh),
                "game": game_box(vw, vh, None, game_ar)}
    V /= len(grays)
    Hh /= len(grays)
    V = np.maximum(V, np.maximum(np.roll(V, 1, 1), np.roll(V, -1, 1)))
    Hh = np.maximum(Hh, np.maximum(np.roll(Hh, 1, 0), np.roll(Hh, -1, 0)))
    M = np.mean([np.abs(a - b) for a, b in zip(grays, grays[1:])], axis=0)

    # yüz kümeleri (aynı yerde tekrar eden yüzler), en sık görülenden başla
    faces.sort(key=lambda f: -f[2])
    clusters = []
    for f in faces:
        for c in clusters:
            r = c[0]
            if (f[2] > r[2] * 0.6 and abs(f[0] + f[2] / 2 - r[0] - r[2] / 2) < r[2] * 1.5
                    and abs(f[1] - r[1]) < r[3]):
                c[1] += 1
                break
        else:
            clusters.append([f, 1])
    clusters.sort(key=lambda c: -c[1])
    minc = max(2, len(grays) // 6)
    best = None
    for face, cnt in [c for c in clusters if c[0][2] <= vw * 0.2][:4]:
        if cnt < minc and best:
            continue
        # aynı kamerada yan yana oturan kişiler: benzer boyutlu komşu yüzleri tek grup yap
        fx, fy, fw, fh = face
        grp = [c[0] for c in clusters if c[1] >= minc and 0.6 < c[0][2] / fw < 1.6
               and abs(c[0][0] - fx) < fw * 6 and abs(c[0][1] - fy) < fh * 1.5]
        gx0, gy0 = min(g[0] for g in grp + [face]), min(g[1] for g in grp + [face])
        gx1 = max(g[0] + g[2] for g in grp + [face])
        gy1 = max(g[1] + g[3] for g in grp + [face])
        for q in ([face, (gx0, gy0, gx1 - gx0, gy1 - gy0)] if len(grp) > 1 else [face]):
            win, sc = cam_window(V, Hh, M, q, k)
            sc += 0.1 * min(1, cnt / len(grays))
            if DEBUG_CAM:
                print("cam?", [round(v) for v in q], cnt, win, round(sc, 3))
            if win and (best is None or sc > best[1]):
                best = (q, sc, win)
    if best is None or best[1] < 0.55:
        small_faces = [c for c in clusters if c[0][2] <= vw * 0.16 and c[1] >= minc]
        if not small_faces:                  # tam ekran kamera / stüdyo çekimi
            return {"layout": "blur", "found": True, "cam": [0, 0, vw, vh], "game": [0, 0, vw, vh]}
        fx, fy, fw, fh = small_faces[0][0]
        cw = min(vw * 0.5, fw * 2.9)         # kenarsız kamera: yüz çevresinde 16:9, ekran kenarına yasla
        ch = cw / 1.78
        L, T = fx + fw / 2 - cw / 2, fy + fh * 0.45 - ch * 0.45
        if L < fw * 0.6: L = 0
        if L + cw > vw - fw * 0.6: L = vw - cw
        if T < fh * 0.6: T = 0
        if T + ch > vh - fh * 0.6: T = vh - ch
        L, T = max(0, min(L, vw - cw)), max(0, min(T, vh - ch))
        R, B = L + cw, T + ch
        found = False
    else:
        fx, fy, fw, fh = best[0]
        L, T, R, B = [v / k for v in best[2]]
        found = True
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
    return {"layout": "split", "found": found, "cam": cam, "window": win, "game": game_box(vw, vh, win, game_ar)}


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
    f1 = ImageFont.truetype(font, round(46 * K)) if font else ImageFont.load_default(round(46 * K))
    f2 = ImageFont.truetype(font, round(34 * K)) if font else ImageFont.load_default(round(34 * K))
    text = text.upper()
    word = text.split(".")[0]
    im = Image.new("RGBA", (W, BAR_H), (0, 0, 0, 255))
    d = ImageDraw.Draw(im)
    w1, w2 = d.textlength(word, font=f1), d.textlength(text, font=f2)
    gap = 28 * K
    x = (W - w1 - gap - w2) / 2
    d.text((x, BAR_H / 2), word, font=f1, fill=color, anchor="lm")
    d.text((x + w1 + gap, BAR_H / 2 + 1), text, font=f2, fill="white", anchor="lm")
    im.save(path)


def captions_ass(src, start, length, lang, path):
    try:
        from sc import listen, settings, subs
        import faster_whisper  # noqa: F401
    except ImportError:
        raise RuntimeError("Altyazı bu sunucuda kurulu değil (faster-whisper yok). Altyazıyı kapatıp tekrar dene.")
    cfg = settings.load()
    cfg.update(cap_words=2, cap_size=round(92 * K), cap_y=0.76, cap_font="Inter Black", cap_outline=max(2, round(8 * K)),
               width=W, height=H)
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
        inputs = ["-threads", "1", "-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", str(src)]
        n = 1
        if p.get("layout") == "blur":
            seam = (H - round(W * meta["height"] / meta["width"])) // 2
            g = (f"[0:v]fps=30,split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                 f"boxblur=30:2[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2[v0];")
        else:
            cx, cy, cw, ch = [int(v) for v in p["cam"]]
            gx, gy, gw, gh = [int(v) for v in p["game"]]
            if p.get("cam_fit", "full") == "full":   # kameranın tamamı, boşluk bulanık kamera ile dolar
                camf = (f"[s1]crop={cw}:{ch}:{cx}:{cy},split[c1][c2];"
                        f"[c1]scale={W}:{CAM_H}:force_original_aspect_ratio=increase,crop={W}:{CAM_H},boxblur=20:2[cbg];"
                        f"[c2]scale={W}:{CAM_H}:force_original_aspect_ratio=decrease:force_divisible_by=2[cfg];"
                        f"[cbg][cfg]overlay=(W-w)/2:(H-h)/2,setsar=1[cam];")
            else:
                camf = f"[s1]crop={cw}:{ch}:{cx}:{cy},scale={W}:{CAM_H},setsar=1[cam];"
            g = (f"[0:v]fps=30,split[s1][s2];{camf}"
                 f"[s2]crop={gw}:{gh}:{gx}:{gy},scale={W}:{GAME_H},setsar=1[game];[cam][game]vstack[v0];")
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
            last, n, title_y = "v2", n + 1, seam + BAR_H + round(12 * K)
        if p.get("title", "").strip():
            cfg = {"title_size": round(56 * K), "title_bg": "FFFFFF", "title_fg": "111111", "width": W,
                   "title_font_file": None, "title_accent": p.get("accent", "#E5004F").lstrip("#")}
            titlecard.render(p["title"].strip(), cfg, work / "title.png")
            inputs += ["-i", str(work / "title.png")]
            ty = f"{title_y}" if title_y is not None else f"{seam}-h/2"
            g += f"[{n}:v]scale='min(iw,{round(1000 * K)})':-1[t];[{last}][t]overlay=(W-w)/2:{ty}[v3];"
            last, n = "v3", n + 1
        g += f"[{last}]null[vout]"
        name = re.sub(r"[^\w-]+", "-", p.get("name") or sid).strip("-")[:50] or sid
        out = OUT / f"{name}-{jid[:6]}.mp4"
        job["step"] = "video oluşturuluyor"
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_threads", "1", *inputs, "-filter_complex", g,
                            "-map", "[vout]", "-map", "0:a?", "-c:v", "libx264", "-crf", "20", "-preset", "faster",
                            "-threads", "1", "-x264-params", "rc-lookahead=0:ref=1:bframes=0:sync-lookahead=0", "-r", "30",
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
    return jsonify(jobs.get(jid) or {"status": "error",
                                     "step": "Sunucu yeniden başladı, iş kayboldu. Lütfen tekrar 'Videoyu oluştur'a bas."})


@app.get("/api/out/<name>")
def out_file(name):
    if not re.fullmatch(r"[\w.-]+\.mp4", name) or not (OUT / name).exists():
        abort(404)
    return send_file(OUT / name, mimetype="video/mp4", conditional=True,
                     as_attachment=bool(request.args.get("dl")), download_name=name)


@app.get("/")
def index():
    return send_from_directory(HERE / "static", "index.html")


# ---------------------------------------------------------------- 3D ofis
WATCH = ["eray", "rraenee", "wtcn", "hype", "elraenn"]
_office_cache = {"t": 0, "data": None}


def kick_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return json.load(r)


@app.get("/ofis")
def office_page():
    return send_from_directory(HERE / "static", "ofis.html")


@app.get("/api/office")
def office():
    now = time.time()
    if not _office_cache["data"] or now - _office_cache["t"] > 90:
        streamers = []
        for ch in WATCH:
            item = {"slug": ch, "live": False}
            try:
                j = kick_json(f"https://kick.com/api/v2/channels/{ch}")
                ls = j.get("livestream") or {}
                item.update(name=(j.get("user") or {}).get("username") or ch, live=bool(ls.get("is_live")),
                            viewers=int(ls.get("viewer_count") or 0), title=ls.get("session_title", ""))
                c = kick_json(f"https://kick.com/api/v2/channels/{ch}/clips?sort=view&time=day").get("clips") or []
                if c:
                    item.update(top_clip=c[0].get("title", ""), top_views=int(c[0].get("views") or 0))
            except Exception as e:
                item["error"] = str(e)[:80]
            streamers.append(item)
        _office_cache.update(t=now, data=streamers)
    running = [j for j in jobs.values() if j.get("status") == "running"]
    done = sorted((j for j in jobs.values() if j.get("status") == "done"), key=lambda j: j.get("started", 0))
    try:
        plan = json.loads((HERE / "static" / "schedule.json").read_text())
    except Exception:
        plan = {}
    return jsonify(streamers=_office_cache["data"], running=len(running),
                   running_step=running[-1]["step"] if running else "",
                   last_file=done[-1]["file"] if done else "", rendered=len(done), plan=plan)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"KLİPLİNK çalışıyor: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, threaded=True)
