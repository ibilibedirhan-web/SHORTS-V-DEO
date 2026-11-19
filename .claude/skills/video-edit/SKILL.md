---
name: video-edit
description: Kullanıcının kestiği veya ham videosuna brief'e göre logo, arama sahnesi, sayaç, çerçeve vurgusu, ekran görüntüsü, yakınlaştırma, altyazı ve müzik ekler; yatay ekran kaydını takip eden kadrajla dikey (9:16) Shorts/Reels'e çevirebilir. Remotion ile şeffaf katman üretir, ffmpeg ile birleştirir. Brief geldiğinde, `materyaller/<video>/brief.md` gösterildiğinde veya "videoyu edit et", "efekt ekle", "logo/sayaç/arama sahnesi ekle" denince kullan. Kaynak: github.com/omergocmen/ai-video-edit-workflow (MIT).
---

# Video edit

Bu akışın tüm dosyaları repo kökündeki `video-edit-workflow/` klasöründedir.
`WF` = o klasör (`<repo>/video-edit-workflow`). Bütün komutları `WF` içinde çalıştır
(`cd video-edit-workflow`); betikler `materyaller/`, `out/`, `public/`, `src/` yollarını oraya göre kullanır.

1. `WF/CLAUDE.md` dosyasındaki genel kuralları oku ve uy.
2. Akışın tamamı `WF/talimat/video-edit.md` dosyasındadır. Önce onu oku, adımları sırayla uygula.
   Küçük/zayıf model kullanılıyorsa önce `WF/talimat/adim-adim.md` dosyasını oku.
3. Kullanıcı genellikle `WF/materyaller/<video>/brief.md` dosyasını işaret eder. Brief yoksa ve kullanıcı
   sadece bir video verdiyse, videoyu `WF/materyaller/<video>/video/` altına koy ve makul varsayımlarla devam et;
   varsayımları raporda söyle.
4. `node_modules` yoksa `WF` içinde `npm install` çalıştır. Gerekenler: Node.js, ffmpeg/ffprobe, Python (Whisper için `faster-whisper`).
   Linux/bulut ortamında `baslat.bat`/`kur.ps1` yerine bu araçları doğrudan kullan.
5. Kapılar (`node scripts/kontrol.mjs ...`) geçmeden teslim yok. Çıktı `WF/out/` altında olur.

Bu repodaki diğer becerilerle birlikte kullanılabilir: ham konuşma videosunu önce `ai-video-editor` ile kesip
sonra bu akışla efekt eklemek, ya da `stream-clips` çıktısına efekt katmanı eklemek gibi.
