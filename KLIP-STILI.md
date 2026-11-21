# Raynax Clips — klip stili (kullanıcı tercihleri)

Instagram, TikTok ve YouTube Shorts için yayıncı klipleri. Bu kurallar her yeni klipte geçerli.

## Kaynak
- Yayıncıların son 24-48 saatte **en çok izlenen** Kick/Twitch kliplerinden başla
  (`https://kick.com/api/v2/channels/<kanal>/clips?sort=view&time=day|week`,
  Twitch için `yt-dlp --flat-playlist "https://www.twitch.tv/<kanal>/clips?filter=clips&range=7d"`).
- Hedef: komik, absürt, saçma, izleyeni şaşırtan anlar. Stüdyoda sadece oturup konuşma sahneleri zayıf.
- Ünlü yayıncılar (500B+ takipçi): RRaenee, Elraenn, Eray, Hype, Ebonivon (+ wtcN, Jahrein); yabancı: Kai Cenat, Adin Ross, IShowSpeed.
- Çıplaklık / cinsel içerik içeren klipleri ele (YouTube ihlal atar). Mecbursa yoğun blur.
- Başlıkta iddia edilen şey görüntüde gerçekten olmalı; kimin videoda olduğunu doğrula.

## Süre ve kurgu
- Sabit süre yok: **olay örgüsüne göre** kes — kurulum (ör. "polis geldi") → patlama → tepki.
  Genelde 10-25 sn; ilk saniyede olay başlamış olsun, son tepkiden hemen sonra kes.
- Düzen: üstte yayıncı kamerası, altta oyun (9:16). Kamera ve oyun yer değiştiriyorsa blur düzeni.

## Görünüm
- Kamera ile başlık arasında siyah platform şeridi: yeşil `KICK` + `KICK.COM/<KANAL>`.
- Beyaz kutu başlık, haber tarzı cümle ("X GTA 6'da … yaptı, … oldu 😭"), vurgu kelimeleri BÜYÜK.
- Yayıncı adı başlıkta kendi renginde (`[İsim]`): Eray/Uzi kırmızı, wtcN mavi, Hype turuncu,
  Kai mor, Adin yeşil.
- Türk yayıncılarda başlık Türkçe; yabancı yayıncılarda (Kai vb.) her şey İngilizce.
- **Türkçe konuşan yayıncılarda altyazı yok.** İngilizce kliplerde 1-2 kelimelik altyazı.

## Paylaşım
- Her klip için TikTok/Instagram açıklaması + 5-7 hashtag ver (YouTube başlığına #shorts).
- Algoritma için hacim önemli: günde 5-10 klip, aralıklarla.

## Araç
`.claude/skills/stream-clips/scripts/viral.py <spec.json> <kaynak_klasör> <çıkış_klasör>`
spec alanları: name, src, start, end, cam [x,y,w,h], lang, title, accent, bar, layout, game_x.

## Hesaplar ve yayınlama (vidIQ üzerinden bağlı)
- TikTok: Raynax Clips — herkese açık, yorumlar açık (müzik kullanım onayı verildi).
- Instagram: @raynaxclips (profesyonel hesap).
- YouTube: @raynaxclips — kullanıcı kendisi planlı paylaşıyor; şimdilik **yabancı yayıncı** içerikleri buraya.
- Kullanıcının kendi paylaştığı videolara dokunma; her yayından önce taslağı göster, onay al.

## KLİPLİNK sitesi
- Canlı: https://shorts-v-deo.onrender.com (Render ücretsiz, 512 MB) — orada çıktı 720x1280 (`OUT_W=720`).

## Otomatik paylaşım akışı (kullanıcı: "hepsini sen ayarla")
- Kullanıcı klibi KLİPLİNK'te hazırlar → "Claude'a gönder" → sohbete yapıştırır.
- Saat seçimi bende: günlük slotlar 13:00 · 18:30 · 20:30 · 23:00 (Europe/Istanbul); saat yazılmadıysa sıradaki boş slot.
  En güçlü klip 20:30'a. Aynı gün içinde paylaş (sıcaklık önemli).
- Açıklama + 5-7 hashtag bende (kullanıcı yazdıysa onu kullan). TikTok: herkese açık, yorumlar açık. Instagram: Reels.
- YouTube'a gönderme (kullanıcı yönetiyor; yabancı içerik).
- Video linkini alır almaz vidIQ'ya yükle (Render dosyaları sunucu uyuyunca siliniyor).
- Zamanladıktan sonra `kliplink/static/schedule.json` → posts listesine ekle (3D Ofis'te Yayıncı ajanı gösterir).
