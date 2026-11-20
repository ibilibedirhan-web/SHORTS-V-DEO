# KLİPLİNK

Kick kliplerini ve kendi videolarını tek tıkla 9:16 Shorts / TikTok / Reels klibine çevirir.

- **Kick Klipleri:** kanal adı yaz (varsayılan `eray`), en çok izlenen / en yeni klipleri gör, 🔥 ile tepki-sinir anlarını filtrele, klibi indir ya da düzenle.
- **Video Yükle:** kendi videonu sürükle bırak.
- **Düzenleyici:**
  - Kamera otomatik algılanır (yüz + kamera penceresinin kenarları). Kırmızı KAMERA ve mavi OYUN kutularını CapCut gibi sürükleyip köşeden büyütebilirsin.
  - Oranlar kilitli: üst %42 kamera (1080×806), alt %58 oyun (1080×1114).
  - Tam ekran kamera/stüdyo çekimi için "Tam kare (bulanık arka plan)" düzeni.
  - Başlangıç/bitiş kesimi, canlı 9:16 önizleme.
  - Beyaz kutu başlık: `[İsim]` köşeli parantezle yazılan kelime seçtiğin renkte (Eray kırmızı, wtcN mavi, Hype turuncu, Kai mor, Adin yeşil).
  - Kamera ile başlık arasında `KICK  KICK.COM/KANAL` şeridi.
  - Altyazı isteğe bağlı (Türkçe konuşan yayıncılarda kapalı bırak).
- **Açık / Koyu mod:** sağ üstteki düğme. Açık mod beyaz, koyu mod siyah; başlıklar sarı.

## Kurulum (bir kere)

1. **Python 3.10+** kur: https://www.python.org/downloads/ (Windows'ta "Add Python to PATH" kutusunu işaretle).
2. **ffmpeg** kur:
   - Windows: `winget install Gyan.FFmpeg`
   - Mac: `brew install ffmpeg`
3. Bu repoyu indir (GitHub'da **Code → Download ZIP**) ve aç.

## Çalıştırma

- Windows: `kliplink/baslat-windows.bat` dosyasına çift tıkla.
- Mac: `kliplink/baslat-mac.command` dosyasına çift tıkla.

Tarayıcıda http://localhost:8000 açılır. İlk açılışta yüz algılama modeli (~230 KB) otomatik indirilir.

İngilizce altyazı istiyorsan bir kere `pip install faster-whisper` çalıştır.

Oluşturulan videolar `kliplink/data/out/` klasörüne kaydedilir.
