# Raynax Clips — klip stili (kullanıcı tercihleri)

Instagram, TikTok ve YouTube Shorts için yayıncı klipleri. Bu kurallar her yeni klipte geçerli.

## Kaynak
- Yayıncıların son 24-48 saatte **en çok izlenen** Kick/Twitch kliplerinden başla
  (`https://kick.com/api/v2/channels/<kanal>/clips?sort=view&time=day|week`,
  Twitch için `yt-dlp --flat-playlist "https://www.twitch.tv/<kanal>/clips?filter=clips&range=7d"`).
- **Tazelik önce:** 5 yayıncının hepsini her çalışmada tara (`sort=date&time=day` + `sort=view&time=day`);
  son birkaç saatte oluşturulan klipler öncelikli (yeni klip daha çok izleniyor). Aynı olayı başka sayfalar
  zaten paylaştıysa geç kalmışız demektir — daha taze olanı seç.
- **Dağılım: çoğunluk Eray, sonra RRaenee.** Her çalışmada en az 1 klip Eray'dan (iyi aday yoksa RRaenee);
  günlük 4 klibin ~3'ü Eray + RRaenee, ~1'i wtcN / Hype / Elraenn'den (farklılık için).
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
spec alanları: name, src, start, end, cam [x,y,w,h] **veya "auto"**, lang, title, accent, bar, layout, game_x, cam_fit.
- Kamerayı elle ölçme: `"cam": "auto"` ver — KLİPLİNK'in algılayıcısı (`kliplink/app.py` → `detect_cam`) kamera
  penceresini bulur, düzeni (split/blur) ve oyun kesitini de seçer (test setinde ortalama %95 isabet).
- `cam_fit` varsayılan `"full"`: kameranın **tamamı** üst %42'de görünür, kenar boşlukları bulanık kamerayla dolar.
  `"fill"` sadece yayıncı tek kişiyse ve yakın plan istenirse.
- Render sonrası bir kareye bakıp kameranın tam ve doğru yerde olduğunu kontrol et; yanlışsa cam'i elle düzelt.

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

## Analist (her çalışmada)
- Instagram: `vidiq_instagram_owner_insights` (ücretsiz, video başı izlenme/izlenme oranı).
- TikTok: herkese açık profil sayfası `https://www.tiktok.com/@raynaxclips` → `__UNIVERSAL_DATA_FOR_REHYDRATION__`
  içindeki `userInfo.stats` (takipçi, toplam beğeni, video sayısı). `schedule.json` → `tiktok` listesine ekle, önceki
  kayıtla karşılaştır (son çalışmadan beri +takipçi, +beğeni). Video başı izlenme yok (vidIQ kredisi 0, 19 Aralık'ta yenilenir);
  kullanıcı TikTok Analiz ekran görüntüsü atarsa onu oku.
- Bulguları `analyst` maddelerine yaz (3-5 madde, sayılarla) ve klip seçimini buna göre ayarla.
- **Her çalışmada** `vidiq_instagram_owner_insights` (reels) sonucunu `schedule.json` → `instagram` listesine yaz
  (code, title, views, watched, skip, shares, saves, dur, url) + `instagram_at`. 3D Ofis'teki Analist (`/api/analyst`)
  TikTok ve Kick'i canlı çeker, Instagram'ı bu listeden okur ve önerileri kendisi üretir (`kliplink/analyst.py`).
- `posts` girdilerine `date` (YYYY-MM-DD) ekle; Analist boş saati buna göre bulur.

## Onay ve müdahale (kullanıcı kurguyu değiştirebilir)
- Her taslakla birlikte **✏️ Düzenle** bağlantısı gönder: `python kliplink/draftlink.py '<json>'`
  (url = Kick klip m3u8, id, channel, start, end, t = başlık, accent, bar, cam, game, cam_fit, layout, name, draft).
  Kullanıcı bağlantıyı telefonda açar → KLİPLİNK ajanın kurgusuyla açılır → değiştirir → "Claude'a gönder".
  Gelen mesajda "Değişikliklerim" listesi olur.
- Kullanıcı sohbette de yazabilir: "onayla", "başlığı şöyle yap: …", "2 sn kısalt", "kamerayı büyüt", "bunu atma" vb.
  İsteneni uygula, yeniden render et, tekrar göster.
- **Her düzeltmeden sonra** kalıcı olacak kuralı aşağıdaki "Öğrenilen stil" bölümüne tek satır ekle
  (tarih + kural, ör. "2026-11-21 · başlıklar 6 kelimeyi geçmesin"), commit + push. Sonraki kurgular buna uyar.
  Tek seferlik değişiklikleri (ör. belirli bir klibin kesim saniyesi) kural yapma; tekrar edenleri kural yap.

## Öğrenilen stil (kullanıcı düzeltmelerinden)
- 2026-11-21 · (TikTok verisi) İzlenmenin %87'si aramadan: başlık ve açıklamanın İLK satırı aranan kelimelerle
  başlasın: yayıncı adı + "GTA 6" + oyundaki karakter/olay (Lucia, Jason, Vice City, polis kovalamacası…).
  Hashtag'lerde de: #eray #gta6 #gta6türkiye + karakter adı (#lucia).
- 2026-11-21 · İzleyicinin çoğu 1. saniyede çıkıyor: ilk kare tepki/aksiyon olsun, kurulumu 1 sn'yi geçmesin;
  sinematik/durgun açılış kareyle başlama. 10-15 sn ideal (11 sn klip %61 izlendi).
- 2026-11-21 · Yorum 0, takipçi dönüşümü çok düşük: açıklamada tartışma açan soru ("Eray haklı mı? 👇"),
  seri başlık kalıbı ("Eray GTA 6'da …" serisi) ve sonda "devamı profilde".
- 2026-11-21 · (2 video karşılaştırması) Aramadan gelen klip 20 saat boyunca izlenmeye devam etti (7K); sadece
  keşfetten gelen klip 4 saatte durdu (1,5K). Her başlıkta "GTA 6" + en çok aranan isim (Eray) olsun; misafir
  ismini ayrı ve doğru yaz ("Sercan Zurna", asla "SercanZurna"). Ör: "[Eray] GTA 6'da Sercan Zurna ile polisten kaçarken…"
- 2026-11-21 · Paylaşım = keşfet itişi: 0 paylaşımlı klip söndü. İzleyicinin arkadaşına atacağı anları seç
  (ilişki, utanç, absürt kaza, "tam bizim grup" anları).
- 2026-11-21 · Kullanıcı sıradan oyun çatışmasını (3 yıldız polis kaçışı) BEĞENMEDİ. Tercih: yayıncıların
  gülmekten yarıldığı, tepki verdiği anlar (kahkaha, şok, utanç) + absürt NPC tepkileri (Hype panik atak klibi seçildi).
  Kahkaha bulmak için: klip başlığında klavye ezmesi (ASDFG…) + kamera karelerinde açık ağız/el kaldırma; Whisper kahkahayı yazmıyor.
- 2026-11-21 · Kullanıcı paylaşım aralığına dikkat ediyor ("algoritmaya göre"): aynı hesaba arka arkaya atma, en az ~3 saat ara.
- 2026-11-21 · Facecam küçük pencere olarak görünüyorsa (oyun/drone/başka görüntü üzerinde) HER ZAMAN üst düzen:
  kamera penceresi (içindeki herkes) üstte, görüntü altta. Tam ekran "bulanık arka plan" düzenini sadece kamera hiç yoksa kullan.
  Klip içinde yayın düzeni değişip kamera kayarsa o noktadan önce kes.
- 2026-11-21 · Yabancı yayıncılar (Kai, Speed, Adin) SADECE YouTube @raynaxclips'e gider (TikTok/IG'ye değil),
  ABD prime time'a planlanır. Kaynakta yayının kendi altyazısı varsa bizim altyazıyı ekleme ("captions": false).
  Başlık kutusu küçük olsun (title_size 44, en fazla 3 satır) ki ekran görünsün.
- 2026-11-21 · Kullanıcı Kai'nin karanlık/net olmayan Skunk Ape klibini beğenmedi: olay görüntüde net görünmeli.
- 2026-11-22 · Kullanıcı Eray'ın oyun içi "uzaylı buldu" klibini beğenmedi; yayına ünlü konuk gelince
  (ör. Deniz Aksoy) konuğun olduğu komik anı tercih ediyor. Ünlü adı başlık + hashtag'e (aranan isim).
- 2026-11-22 · 114K'lık klip analizi: 24 sn'de izleyicinin %62'si sona gelmedi → yeni klipler 18-20 sn hedef.
  (Kullanıcı sadece bunu onayladı; pin/yorum/seri/"devamı profilde" önerilerini İSTEMEDİ — önerme.)
- 2026-11-22 · Kullanıcı TikTok'u VE Instagram'ı KENDİSİ paylaşıyor. Ajan hiçbir platformda zamanlama yapmaz;
  klip dosyasını + kopyalanabilir açıklamayı (TikTok ve Instagram için) gönderir, saat önerir. Paylaşımdan sonra kontrol eder.
- 2026-11-22 · 🚀 İLK VİRAL: Deniz Aksoy + Eray araba klibi TikTok'ta 3,5 saatte 42.8K izlenme, 186 paylaşım.
  Ünlü konuklu yayınlar EN ÖNCELİKLİ kaynak. Açıklama kısa: tek satır olay + soru + #yayındankesitler (kullanıcının yazdığı format).
- 2026-11-22 · Kullanıcı 28 sn'lik kuaför (Lucia'yı Deniz'e benzetme) klibini "uzun ve tutmaz" buldu. Konuk klipleri
  ≤20 sn, tek bir punchline'a giden diyalog olsun (soru → ters köşe cevap → tepki); gerekirse ortadaki boşluğu kes.
- 2026-11-22 · Kullanıcının istediği komik an tipi: yayıncı oyun oynarken yanındaki konuk/ünlü yüzünden
  heyecanlanıyor, utanıyor, lafı karışıyor, oyunu unutuyor (ör. Eray, Deniz Aksoy yanında kulübe gitmeye utandı).
  Bunu bulmak için VOD'un konuklu bölümünü 360p indir, Whisper ile dök, "gitmeyelim / niye gülüyorsunuz / konsantre
  olamıyorum / utandım" gibi anları ara, kamerada tepkiyi doğrula, 1080p60'tan kes. Gerekirse 2-3 parçayı birleştir.
- 2026-11-22 · Kick klibi olayın ortasında bitebilir (kullanıcı: "güldüğü kısım yok"). Punchline/gülme klipte
  yoksa VOD'dan devamını al: `api/v2/clips/<id>` → `vod_starts_at` + `vod.id`, `api/v1/video/<vod.id>` → `source` m3u8,
  `ffmpeg -ss <vod_starts_at-5> -t 70`. Klibi soruyla başlat, tepkiyle bitir.
- 2026-11-21 · Kitle %50 kadın, 18-34 yaş, %92 Türkiye: ilişki/drama/Lucia hikâyeleri ve RRaenee iyi gider.
- Torpil/havai fişek/patlayıcı gibi tehlikeli hareket içeren klipleri SEÇME: torpil klibi (23.11 12:00) 4 saatte 377 izlenmede kaldı, aynı hafta konuklu oyun klipleri 190-330K yaptı. TikTok bu tür içeriği önermeyebilir.
- 2026-11-23 · Komik an bulma yöntemi: Kick VOD sohbet kaydı (api/v2/channels/<id>/messages?start_time=ISO, 5 sn'lik sayfalar) → KEKW/LULW/klavye ezme yoğunluğunu 20 sn pencerelerde say; chat yayını ~5 sn geriden izliyor, an = zirve - 5 sn. Zirvenin 20-25 sn öncesinden kes.
- 2026-11-24 · Eray yayınından her klipte başlıkta MUTLAKA [Eray] yazsın ve renkli (accent) olsun; konuk kim olursa olsun renkli isim Eray. (Sercan havuz klibi bu yüzden reddedildi.)
- 2026-11-24 · Eray'ın izlediği video (react) klipleri: kamera üstte, izlediği video altta TAM; BAŞLIK YOK, sadece KICK.COM/ERAY bandı + bandın altında yarı saydam, hafif hareketli @raynaxclips filigranı. İzlenen videonun tamamı gösterilebilir (20 sn kuralı bunda esnek). 2026-11-25: @raynaxclips animasyonlu filigranı TÜM kliplerde KICK bandının hemen altına koy (başlık varsa başlığı biraz aşağı al).
