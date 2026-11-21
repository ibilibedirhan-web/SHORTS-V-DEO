"""Ajan taslağı için KLİPLİNK düzenleme bağlantısı üretir.
usage: python draftlink.py '<json>'   (alanlar: url=Kick klip m3u8, id, channel, clip, start, end, t=başlık,
       accent, bar, cam, game, cam_fit, layout, name, draft)  → https://shorts-v-deo.onrender.com/#edit=..."""
import base64, json, sys

BASE = "https://shorts-v-deo.onrender.com/"


def link(d, base=BASE):
    raw = json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode()
    return base + "#edit=" + base64.urlsafe_b64encode(raw).decode().rstrip("=")


if __name__ == "__main__":
    print(link(json.loads(sys.argv[1]), *(sys.argv[2:3])))
