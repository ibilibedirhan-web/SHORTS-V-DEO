"""Analist ajanı: canlı veri (TikTok profili, Kick yayıncıları) + kayıtlı Instagram verisi → sayılar ve öneriler."""
import datetime as dt
import json
import re
import time
import urllib.request

TZ = dt.timezone(dt.timedelta(hours=3))          # Europe/Istanbul (yaz saati yok)
TIKTOK = "raynaxclips"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130 Safari/537.36")
NAMES = {"eray": "Eray", "rraenee": "RRaenee", "wtcn": "wtcN", "hype": "Hype", "elraenn": "Elraenn",
         "uzi": "Uzi", "sercan": "Sercan Zurna", "speed": "IShowSpeed", "kai": "Kai Cenat"}

_tt = {"t": 0, "data": None, "history": []}


def tiktok_stats():
    """Herkese açık profil sayfasından takipçi / beğeni / video sayısı (10 dk önbellek)."""
    now = time.time()
    if _tt["data"] and now - _tt["t"] < 600:
        return _tt["data"]
    try:
        req = urllib.request.Request(f"https://www.tiktok.com/@{TIKTOK}", headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")
        m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S)
        st = json.loads(m.group(1))["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]["stats"]
        data = {"followers": st.get("followerCount", 0), "likes": st.get("heartCount", 0),
                "videos": st.get("videoCount", 0), "at": dt.datetime.now(TZ).strftime("%H:%M"), "live": True}
        _tt["history"].append((now, data))
        _tt["history"] = _tt["history"][-50:]
    except Exception as e:                      # TikTok bazen sunucu IP'lerini engeller
        data = dict(_tt["data"] or {}, live=False, error=str(e)[:80])
    _tt.update(t=now, data=data)
    return data


def _who(caption):
    c = (caption or "").lower()
    for k, v in NAMES.items():
        if k in c.replace(" ", ""):
            return v
    return "?"


def _slot_dt(day, hhmm):
    h, m = map(int, hhmm.split(":"))
    return dt.datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)


def report(plan, streamers):
    now = dt.datetime.now(TZ)
    tt = tiktok_stats()
    ig = plan.get("instagram") or []
    tips, cards = [], []

    # --- TikTok (canlı) ---
    hist = plan.get("tiktok") or []
    base = hist[-1] if hist else None
    if tt.get("followers") is not None and tt.get("videos") is not None:
        d_f = tt["followers"] - (base or {}).get("followers", tt["followers"])
        d_l = tt["likes"] - (base or {}).get("likes", tt["likes"])
        cards.append({"k": "TikTok takipçi", "v": tt["followers"], "d": d_f, "since": (base or {}).get("t", "")})
        cards.append({"k": "TikTok beğeni", "v": tt["likes"], "d": d_l, "since": (base or {}).get("t", "")})
        cards.append({"k": "TikTok video", "v": tt["videos"]})
        if tt["videos"]:
            per = tt["likes"] / tt["videos"]
            conv = tt["followers"] / max(1, tt["likes"]) * 100
            if conv < 5:
                tips.append(f"TikTok'ta video başı {per:.0f} beğeni var ama takipçiye dönüşüm %{conv:.1f}. "
                            "Açıklamanın sonuna “Devamı için takip 👀” ekle, en iyi 3 klibi profile sabitle.")

    # --- Instagram (son kayıt) ---
    if ig:
        views = sum(r.get("views", 0) for r in ig)
        cards.append({"k": "Instagram izlenme", "v": views, "since": plan.get("instagram_at", "")})
        top = sorted(ig, key=lambda r: -r.get("views", 0))
        best = top[0]
        tips.append(f"En çok izlenen Reel: “{best['title'][:60]}” — {best['views']:,} izlenme, "
                    f"%{best.get('watched', 0):.0f} izlenme oranı. Bu tarz anları öne al.".replace(",", "."))
        short = [r for r in ig if r.get("dur", 99) <= 16]
        long_ = [r for r in ig if r.get("dur", 0) > 16]
        if short and long_:
            a = sum(r.get("watched", 0) for r in short) / len(short)
            b = sum(r.get("watched", 0) for r in long_) / len(long_)
            if a > b + 5:
                tips.append(f"16 sn ve altı klipler ortalama %{a:.0f} izleniyor, uzunlar %{b:.0f}. "
                            "Klipleri 10-16 sn'de tut, ilk saniyede olayı başlat.")
        by = {}
        for r in ig:
            by.setdefault(_who(r.get("title")), []).append(r.get("views", 0))
        ranked = sorted(((sum(v) / len(v), k, len(v)) for k, v in by.items() if k != "?"), reverse=True)
        if len(ranked) >= 2:
            tips.append("Yayıncı başına ortalama izlenme: " +
                        " · ".join(f"{k} {int(avg)} ({n} klip)" for avg, k, n in ranked[:4]) + ".")
        shares = sum(r.get("shares", 0) for r in ig)
        if shares <= len(ig) // 3:
            tips.append(f"{len(ig)} Reel'de toplam {shares} paylaşım var. Keşfet paylaşımla büyür: "
                        "arkadaşına atılacak anları seç ve açıklamada “Arkadaşını etiketle 👇” de.")

    # --- Kick (canlı) ---
    live = [s for s in streamers if s.get("live")]
    for s in sorted(live, key=lambda s: -(s.get("viewers") or 0)):
        tips.insert(0, f"🔴 {s.get('name') or s['slug']} şu an CANLI ({s.get('viewers', 0):,} izleyici). "
                       "Taze klip fırsatı: Stüdyo'da kanalını aç, son 1 saatin kliplerine bak.".replace(",", "."))
    hot = sorted((s for s in streamers if s.get("top_views")), key=lambda s: -s["top_views"])
    if hot:
        s = hot[0]
        tips.append(f"Günün en çok izlenen Kick klibi: {s.get('name') or s['slug']} — “{s['top_clip']}” "
                    f"({s['top_views']:,} izlenme).".replace(",", "."))

    # --- Zamanlama ---
    today = now.strftime("%Y-%m-%d")
    taken = {p.get("time") for p in plan.get("posts", []) if p.get("date", today) == today
             and p.get("platform", "TikTok+IG") != "YouTube"}
    free = [s for s in plan.get("slots", []) if s not in taken and _slot_dt(now, s) > now]
    if free:
        tips.append(f"Bugünün sıradaki boş saati: {free[0]}" + (" (prime time)" if free[0] == "20:30" else "") +
                    ". Klip hazırlarsan o saate zamanlarım.")
    else:
        tips.append("Bugünün tüm saatleri dolu 👍 Yarın 13:00 için klip hazırlanabilir.")

    return {"now": now.strftime("%d.%m %H:%M"), "cards": cards, "tips": tips[:7],
            "tiktok_live": bool(tt.get("live")), "top": [
                {"title": r["title"][:70], "views": r.get("views", 0), "watched": round(r.get("watched", 0)),
                 "url": r.get("url", "")} for r in sorted(ig, key=lambda r: -r.get("views", 0))[:5]]}
