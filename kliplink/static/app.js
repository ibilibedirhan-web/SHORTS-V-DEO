"use strict";
const $ = (s) => document.querySelector(s);
const W = 1080, H = 1920, CAM_H = Math.round(H * 0.42), GAME_H = H - CAM_H, BAR_H = 70;
const CAM_AR = W / CAM_H, GAME_AR = W / GAME_H;
const state = { src: null, cam: [0, 0, 400, 300], game: [0, 0, 1000, 1080], clips: [] };

// ---------- theme ----------
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  $("#theme").textContent = t === "dark" ? "🌙 Koyu" : "☀️ Açık";
  $("#theme").animate?.([{ transform: "rotate(-12deg) scale(.9)" }, { transform: "none" }], { duration: 300, easing: "ease-out" });
  try { localStorage.setItem("kliplink-theme", t); } catch (e) {}
}
applyTheme(document.documentElement.dataset.theme || "dark");
$("#theme").onclick = () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");

// logo -> ana sayfa
$("#home").onclick = (e) => { e.preventDefault(); show("kick"); window.scrollTo({ top: 0, behavior: "smooth" }); };

// kartlarda 3D eğilme (fare ve dokunma)
function tilt(e) {
  const card = e.target.closest && e.target.closest(".card");
  if (!card) return;
  const r = card.getBoundingClientRect(), p = e.touches ? e.touches[0] : e;
  const x = (p.clientX - r.left) / r.width, y = (p.clientY - r.top) / r.height;
  card.style.setProperty("--ry", ((x - .5) * 18).toFixed(2) + "deg");
  card.style.setProperty("--rx", ((.5 - y) * 14).toFixed(2) + "deg");
  card.style.setProperty("--mx", (x * 100).toFixed(1) + "%");
  card.style.setProperty("--my", (y * 100).toFixed(1) + "%");
  card.classList.add("tilt");
}
function untilt(e) {
  const card = e.target.closest && e.target.closest(".card");
  if (!card || (e.relatedTarget && card.contains(e.relatedTarget))) return;
  ["--rx", "--ry"].forEach((v) => card.style.setProperty(v, "0deg"));
  card.classList.remove("tilt");
}
const gridEl = $("#grid");
gridEl.addEventListener("pointermove", tilt);
gridEl.addEventListener("pointerout", untilt);
gridEl.addEventListener("touchmove", tilt, { passive: true });
gridEl.addEventListener("touchend", (e) => { const c = e.target.closest(".card"); if (c) { c.style.setProperty("--rx", "0deg"); c.style.setProperty("--ry", "0deg"); c.classList.remove("tilt"); } });

// ---------- tabs ----------
function show(tab) {
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === tab));
  if (tab === "editor") requestAnimationFrame(layoutBoxes);
  requestAnimationFrame(moveInd);
}
function moveInd() {
  const t = document.querySelector(".tab.active"), ind = document.querySelector(".tab-ind");
  if (!t || !ind) return;
  ind.style.left = t.offsetLeft + "px";
  ind.style.width = t.offsetWidth + "px";
}
window.addEventListener("resize", moveInd);
(document.fonts ? document.fonts.ready : Promise.resolve()).then(moveInd);
setTimeout(moveInd, 300);
document.querySelectorAll(".tab").forEach((b) => (b.onclick = () => show(b.dataset.tab)));

const setStatus = (el, msg, err) => { el.textContent = msg || ""; el.classList.toggle("err", !!err); };
const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
const fmtViews = (n) => (n = +n || 0, n >= 1e6 ? (n / 1e6).toFixed(2).replace(".", ",") + " Mn"
  : n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(".", ",") + "B" : String(n));
async function api(url, opts) {
  const r = await fetch(url, opts);
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error) throw new Error(j.error || r.statusText);
  return j;
}

// ---------- Kick clips ----------
async function loadChannel(ch) {
  const box = $("#chan");
  try {
    const c = await api("/api/channel?channel=" + encodeURIComponent(ch));
    const since = c.started ? Math.max(0, Math.round((Date.now() - Date.parse(c.started.replace(" ", "T") + "Z")) / 60000)) : 0;
    const dur = since >= 60 ? `${Math.floor(since / 60)} sa ${since % 60} dk` : `${since} dk`;
    const avatar = c.avatar ? `<img class="av" src="/api/thumb?u=${encodeURIComponent(c.avatar)}" alt="">` : `<div class="av"></div>`;
    box.innerHTML = `<div class="chan-head">${avatar}<div><div class="cn">${c.name}${c.verified ? " ✔" : ""}</div>
        <div class="m">${fmtViews(c.followers)} takipçi</div></div>
        ${c.live ? `<span class="live">🔴 CANLI · ${fmtViews(c.viewers)} izleyici</span>` : `<span class="off">Şu an yayında değil</span>`}
        <a class="ghost btn" href="https://kick.com/${c.slug}" target="_blank" rel="noopener">Kick'te aç ↗</a></div>` +
      (c.live ? `<div class="live-info"><b></b><span class="m"></span></div>
        <div class="player"><iframe src="https://player.kick.com/${c.slug}?autoplay=true&muted=true" allowfullscreen
          allow="autoplay; fullscreen; picture-in-picture" loading="lazy" title="Canlı yayın"></iframe></div>` : "");
    if (c.live) {
      box.querySelector(".live-info b").textContent = c.title;
      box.querySelector(".live-info .m").textContent = `${c.category} · ${dur} önce başladı`;
    }
    box.hidden = false;
  } catch (e) { box.hidden = true; }
}
async function loadClips() {
  const st = $("#status");
  loadChannel($("#channel").value.trim());
  setStatus(st, "Klipler getiriliyor…");
  $("#grid").innerHTML = "";
  try {
    const q = new URLSearchParams({ channel: $("#channel").value.trim(), time: $("#time").value, sort: $("#sort").value });
    const j = await api("/api/clips?" + q);
    state.clips = j.clips;
    renderClips();
  } catch (e) { setStatus(st, e.message, true); }
}
function renderClips() {
  const rageOnly = $("#rageOnly").checked;
  const list = state.clips.filter((c) => !rageOnly || c.rage);
  setStatus($("#status"), `${list.length} klip` + (rageOnly ? " (tepki / sinir)" : ""));
  const grid = $("#grid");
  grid.innerHTML = "";
  list.forEach((c, idx) => {
    const el = document.createElement("div");
    el.className = "card";
    el.style.setProperty("--i", Math.min(idx, 16));
    el.innerHTML = `<div class="thumb"></div><div class="body"><div class="t"></div>
      <div class="m"></div><div class="acts"><button class="primary e">✂️ Düzenle</button><button class="d">⬇︎ İndir</button></div></div>`;
    const th = el.querySelector(".thumb");
    if (c.thumbnail) th.style.backgroundImage = `url("/api/thumb?u=${encodeURIComponent(c.thumbnail)}")`;
    th.insertAdjacentHTML("beforeend", `<b>${fmtTime(c.duration)}</b>` + (c.rage ? `<b class="fire">🔥</b>` : ""));
    el.querySelector(".t").textContent = c.title || "(başlıksız)";
    el.querySelector(".m").textContent = `${fmtViews(c.views)} izlenme · ${c.created_at.slice(0, 16).replace("T", " ")} · ${c.category}`;
    el.querySelector(".e").onclick = () => importClip(c, el, false);
    el.querySelector(".d").onclick = () => importClip(c, el, true);
    grid.appendChild(el);
  });
}
async function importClip(c, card, download) {
  const btns = card.querySelectorAll("button");
  btns.forEach((b) => (b.disabled = true));
  const st = $("#status");
  setStatus(st, `“${c.title}” indiriliyor…`);
  try {
    const meta = await api("/api/import", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: c.url, id: c.id, channel: c.channel, title: c.title }) });
    setStatus(st, "Hazır.");
    if (download) {
      const a = document.createElement("a");
      a.href = `/api/source/${meta.id}.mp4?dl=${encodeURIComponent(slug(c.channel + "-" + c.title))}`;
      a.click();
    } else openEditor(meta);
  } catch (e) { setStatus(st, e.message, true); }
  btns.forEach((b) => (b.disabled = false));
}
$("#load").onclick = loadClips;
$("#rageOnly").onchange = renderClips;
$("#channel").onkeydown = (e) => { if (e.key === "Enter") loadClips(); };

// ---------- upload ----------
const drop = $("#drop");
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]));
$("#file").onchange = (e) => e.target.files[0] && upload(e.target.files[0]);
async function upload(file) {
  const st = $("#upstatus");
  setStatus(st, `Yükleniyor: ${file.name}…`);
  const fd = new FormData();
  fd.append("file", file);
  try {
    const meta = await api("/api/upload", { method: "POST", body: fd });
    setStatus(st, "Yüklendi.");
    openEditor(meta);
  } catch (e) { setStatus(st, e.message, true); }
}

// ---------- editor ----------
const video = $("#video"), stage = $("#stage");
const slug = (s) => (s || "klip").toLocaleLowerCase("tr").normalize("NFD").replace(/[̀-ͯ]/g, "")
  .replace(/ı/g, "i").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 50) || "klip";

function openEditor(meta) {
  state.src = meta;
  $("#tab-editor").disabled = false;
  $("#ed-title").textContent = "Düzenleyici — " + (meta.name || meta.id);
  video.src = `/api/source/${meta.id}.mp4`;
  $("#dl-src").href = `/api/source/${meta.id}.mp4?dl=${encodeURIComponent(slug((meta.channel || "") + "-" + meta.name))}`;
  $("#start").value = 0;
  $("#end").value = meta.duration.toFixed(1);
  $("#seek").max = meta.duration;
  const ch = (meta.channel || "").toUpperCase();
  if (ch) { $("#bar").value = `KICK.COM/${ch}`; $("#barOn").checked = true; }
  const name = meta.channel ? meta.channel.charAt(0).toUpperCase() + meta.channel.slice(1) : "";
  $("#title").value = name ? `[${name}] ` : "";
  $("#name").value = slug((meta.channel || "") + "-" + meta.name);
  $("#result").innerHTML = "";
  setStatus($("#rstatus"), "");
  updateLen();
  show("editor");
  window.scrollTo(0, 0);
  detect();
}

async function detect() {
  if (!state.src) return;
  const msg = $("#detect-msg");
  msg.textContent = "Kamera aranıyor…";
  try {
    const d = await api(`/api/detect/${state.src.id}`);
    state.cam = d.cam; state.game = d.game;
    $("#layout").value = d.layout;
    msg.textContent = !d.found ? "Yüz bulunamadı — kutuları elle yerleştir."
      : d.layout === "blur" ? "Tam ekran kamera bulundu → tam kare düzen seçildi." : "Kamera bulundu ✔";
    stage.classList.toggle("blur", d.layout === "blur");
    layoutBoxes();
  } catch (e) { msg.textContent = e.message; }
}
$("#detect").onclick = detect;
$("#layout").onchange = () => { stage.classList.toggle("blur", $("#layout").value === "blur"); };

function scale() { return stage.clientWidth / (state.src ? state.src.width : 1920); }
function layoutBoxes() {
  if (!state.src) return;
  const k = scale();
  for (const [key, el] of [["cam", $("#box-cam")], ["game", $("#box-game")]]) {
    const [x, y, w, h] = state[key];
    Object.assign(el.style, { left: x * k + "px", top: y * k + "px", width: w * k + "px", height: h * k + "px" });
  }
}
window.addEventListener("resize", layoutBoxes);
video.addEventListener("loadedmetadata", layoutBoxes);

function clampBox(b) {
  const vw = state.src.width, vh = state.src.height;
  let [x, y, w, h] = b;
  w = Math.min(w, vw); h = Math.min(h, vh);
  x = Math.max(0, Math.min(x, vw - w)); y = Math.max(0, Math.min(y, vh - h));
  return [Math.round(x), Math.round(y), Math.round(w), Math.round(h)];
}
function makeDraggable(el, key, ar) {
  let mode = null, sx, sy, start;
  el.addEventListener("pointerdown", (e) => {
    mode = e.target.classList.contains("h") ? "resize" : "move";
    sx = e.clientX; sy = e.clientY; start = [...state[key]];
    el.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  el.addEventListener("pointermove", (e) => {
    if (!mode) return;
    const k = scale(), dx = (e.clientX - sx) / k, dy = (e.clientY - sy) / k;
    let [x, y, w, h] = start;
    if (mode === "move") { x += dx; y += dy; }
    else {
      w = Math.max(80, w + Math.max(dx, dy * ar));
      const maxW = Math.min(state.src.width - x, (state.src.height - y) * ar);
      w = Math.min(w, maxW); h = w / ar;
    }
    state[key] = clampBox([x, y, w, h]);
    layoutBoxes();
  });
  const end = () => { mode = null; };
  el.addEventListener("pointerup", end);
  el.addEventListener("pointercancel", end);
}
makeDraggable($("#box-cam"), "cam", CAM_AR);
makeDraggable($("#box-game"), "game", GAME_AR);

// playback + trim
$("#play").onclick = () => (video.paused ? video.play() : video.pause());
video.onplay = () => ($("#play").textContent = "⏸ Durdur");
video.onpause = () => ($("#play").textContent = "▶︎ Oynat");
video.ontimeupdate = () => {
  $("#seek").value = video.currentTime;
  $("#time-now").textContent = video.currentTime.toFixed(1) + " sn";
  const end = +$("#end").value;
  if (!video.paused && end > 0 && video.currentTime >= end) { video.currentTime = +$("#start").value; }
};
$("#seek").oninput = (e) => (video.currentTime = +e.target.value);
$("#set-start").onclick = () => { $("#start").value = video.currentTime.toFixed(1); updateLen(); };
$("#set-end").onclick = () => { $("#end").value = video.currentTime.toFixed(1); updateLen(); };
["start", "end"].forEach((id) => ($("#" + id).oninput = updateLen));
function updateLen() {
  const l = +$("#end").value - +$("#start").value;
  $("#len").textContent = `süre: ${l.toFixed(1)} sn`;
}
document.querySelectorAll(".swatches button").forEach((b) => (b.onclick = () => ($("#accent").value = b.dataset.c)));

// ---------- live 9:16 preview ----------
const cv = $("#preview"), ctx = cv.getContext("2d");
function roundRect(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function drawTitle(yTop, centered) {
  const text = $("#title").value.trim();
  if (!text) return;
  const k = cv.width / W, size = 56 * k, padX = size * 0.6, padY = size * 0.38, lh = size * 1.28;
  ctx.font = `800 ${size}px system-ui, sans-serif`;
  // words with accent flag
  const words = []; let acc = false;
  for (let w of text.split(/\s+/)) {
    if (w.startsWith("[")) { acc = true; w = w.slice(1); }
    const closes = w.includes("]"); w = w.replace("]", "");
    words.push({ w, acc }); if (closes) acc = false;
  }
  const limit = cv.width - 2 * cv.width * 0.11 - 2 * padX, sp = ctx.measureText(" ").width;
  const lines = []; let cur = [], cw = 0;
  for (const o of words) {
    const ww = ctx.measureText(o.w).width;
    if (cur.length && cw + sp + ww > limit) { lines.push([cur, cw]); cur = [o]; cw = ww; }
    else { cw += (cur.length ? sp : 0) + ww; cur.push(o); }
  }
  if (cur.length) lines.push([cur, cw]);
  const bw = Math.max(...lines.map((l) => l[1])) + 2 * padX, bh = lines.length * lh + 2 * padY;
  const bx = (cv.width - bw) / 2, by = centered ? yTop - bh / 2 : yTop;
  ctx.fillStyle = "rgba(0,0,0,.27)"; roundRect(bx + 4, by + 5, bw, bh, size * 0.32); ctx.fill();
  ctx.fillStyle = "#fff"; roundRect(bx, by, bw, bh, size * 0.32); ctx.fill();
  ctx.textBaseline = "middle";
  lines.forEach(([ws, lw], i) => {
    let x = (cv.width - lw) / 2; const y = by + padY + lh * i + lh / 2;
    ws.forEach((o, j) => {
      if (j) x += sp;
      ctx.fillStyle = o.acc ? $("#accent").value : "#111";
      ctx.fillText(o.w, x, y); x += ctx.measureText(o.w).width;
    });
  });
}
function drawBar(y) {
  if (!$("#barOn").checked || !$("#bar").value.trim()) return;
  const k = cv.width / W, txt = $("#bar").value.trim().toUpperCase(), word = txt.split(".")[0];
  ctx.fillStyle = "#000"; ctx.fillRect(0, y, cv.width, BAR_H * k);
  ctx.textBaseline = "middle";
  ctx.font = `900 ${46 * k}px system-ui, sans-serif`; const w1 = ctx.measureText(word).width;
  ctx.font = `900 ${34 * k}px system-ui, sans-serif`; const w2 = ctx.measureText(txt).width;
  let x = (cv.width - w1 - 28 * k - w2) / 2;
  ctx.font = `900 ${46 * k}px system-ui, sans-serif`; ctx.fillStyle = $("#barColor").value; ctx.fillText(word, x, y + BAR_H * k / 2);
  ctx.font = `900 ${34 * k}px system-ui, sans-serif`; ctx.fillStyle = "#fff"; ctx.fillText(txt, x + w1 + 28 * k, y + BAR_H * k / 2);
}
function drawPreview() {
  requestAnimationFrame(drawPreview);
  if (!state.src || !$("#editor").classList.contains("active")) return;
  const k = cv.width / W;
  ctx.fillStyle = "#000"; ctx.fillRect(0, 0, cv.width, cv.height);
  if (video.readyState < 2) return;
  let seam;
  if ($("#layout").value === "blur") {
    const fh = cv.width * state.src.height / state.src.width;
    ctx.filter = "blur(16px)";
    const sc = Math.max(cv.width / state.src.width, cv.height / state.src.height);
    ctx.drawImage(video, (cv.width - state.src.width * sc) / 2, (cv.height - state.src.height * sc) / 2, state.src.width * sc, state.src.height * sc);
    ctx.filter = "none";
    seam = (cv.height - fh) / 2;
    ctx.drawImage(video, 0, seam, cv.width, fh);
  } else {
    const [cx, cy, cw, ch] = state.cam, [gx, gy, gw, gh] = state.game;
    ctx.drawImage(video, cx, cy, cw, ch, 0, 0, cv.width, CAM_H * k);
    ctx.drawImage(video, gx, gy, gw, gh, 0, CAM_H * k, cv.width, GAME_H * k);
    seam = CAM_H * k;
  }
  if ($("#barOn").checked && $("#bar").value.trim()) { drawBar(seam); drawTitle(seam + (BAR_H + 12) * k, false); }
  else drawTitle(seam, true);
}
requestAnimationFrame(drawPreview);

// ---------- render ----------
$("#render").onclick = async () => {
  if (!state.src) return;
  const st = $("#rstatus"), btn = $("#render");
  const start = +$("#start").value, end = +$("#end").value;
  if (end - start < 0.5) return setStatus(st, "Bitiş, başlangıçtan en az 0,5 sn sonra olmalı.", true);
  btn.disabled = true;
  st.classList.add("busy");
  setStatus(st, "🎬 Video oluşturuluyor…");
  try {
    const body = {
      id: state.src.id, start, end, layout: $("#layout").value, cam: state.cam, game: state.game,
      title: $("#title").value, accent: $("#accent").value,
      bar: $("#barOn").checked ? $("#bar").value.trim() : "", bar_color: $("#barColor").value,
      captions: $("#caps").checked, lang: $("#lang").value, name: $("#name").value || slug(state.src.name),
    };
    const { job } = await api("/api/render", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    for (;;) {
      await new Promise((r) => setTimeout(r, 1200));
      const j = await api("/api/job/" + job);
      if (j.status === "done") {
        setStatus(st, "Hazır ✔");
        showResult(j.file);
        break;
      }
      if (j.status === "error") throw new Error(j.step);
      setStatus(st, "🎬 Video oluşturuluyor… (" + j.step + ")");
    }
  } catch (e) { setStatus(st, "Hata: " + e.message, true); }
  st.classList.remove("busy");
  btn.disabled = false;
};

// ---------- paylaşım ----------
function makeCaption() {
  const raw = $("#title").value.trim();
  const plain = raw.replace(/[\[\]]/g, "").replace(/\s+/g, " ");
  const name = ((raw.match(/\[([^\]]+)\]/) || [])[1] || (state.src && state.src.channel) || "").trim();
  const tag = (t) => "#" + t.toLocaleLowerCase("tr").replace(/[^\p{L}\p{N}]+/gu, "");
  const en = $("#lang").value === "en" && $("#caps").checked;
  const tags = en ? ["#gta6", name && tag(name), "#gtavi", "#funny", "#gaming", "#kick"]
                  : ["#gta6", name && tag(name), "#gta6türkiye", "#komik", "#kick", "#keşfet"];
  const ask = en ? "Drop a 💀 if you'd do the same 👇" : "Sen olsan ne yapardın? 👇";
  return `${plain}\n${ask}\n\n${[...new Set(tags.filter(Boolean))].join(" ")}`;
}
function showResult(file) {
  const url = `/api/out/${file}`;
  $("#result").innerHTML = `<h3>Sonuç</h3><video controls playsinline src="${url}"></video>
    <h3>Paylaş</h3>
    <label class="wide"><textarea id="caption" rows="5"></textarea></label>
    <div class="row">
      <button class="primary" id="share">📤 Paylaş (TikTok / Instagram / YouTube)</button>
      <button class="ghost" id="copy">📋 Açıklamayı kopyala</button>
      <button class="ghost" id="toClaude">🤖 Claude'a gönder</button>
      <a class="ghost btn" href="${url}?dl=1" download>⬇︎ Videoyu indir</a>
    </div>
    <p class="hint">“Paylaş” telefonun paylaşım menüsünü açar: uygulamayı seç, açıklama panoya kopyalanmış olur, yapıştırman yeterli.
      YouTube'da başlık olarak açıklamanın ilk satırını kullan ve sonuna <code>#shorts</code> ekle.</p>
    <div id="sstatus" class="status"></div>`;
  $("#caption").value = makeCaption();
  const copy = async () => {
    try { await navigator.clipboard.writeText($("#caption").value); }
    catch (e) { $("#caption").select(); document.execCommand("copy"); }
    setStatus($("#sstatus"), "Açıklama kopyalandı ✔");
  };
  $("#copy").onclick = copy;
  $("#toClaude").onclick = async () => {
    const link = new URL(url, location.href).href;
    const msg = `Bu klibi paylaş:\nVideo: ${link}\nAçıklama:\n${$("#caption").value}`;
    try { await navigator.clipboard.writeText(msg); }
    catch (e) { const t = document.createElement("textarea"); t.value = msg; document.body.appendChild(t); t.select(); document.execCommand("copy"); t.remove(); }
    setStatus($("#sstatus"), "Kopyalandı ✔ Claude sohbetine yapıştır, istersen saat de yaz (ör. 20:30). Video sunucuda birkaç saat durur, beklemeden gönder.");
  };
  $("#share").onclick = async () => {
    const st = $("#sstatus");
    await copy();
    try {
      setStatus(st, "Video hazırlanıyor…");
      const blob = await (await fetch(url)).blob();
      const f = new File([blob], file, { type: "video/mp4" });
      if (navigator.canShare && navigator.canShare({ files: [f] })) {
        await navigator.share({ files: [f], text: $("#caption").value });
        setStatus(st, "Paylaşım menüsü açıldı. Açıklama panoda, uygulamada yapıştır.");
      } else {
        setStatus(st, "Bu tarayıcı dosya paylaşımını desteklemiyor: videoyu indirip uygulamadan yükle. Açıklama panoda.", true);
      }
    } catch (e) { setStatus(st, e.name === "AbortError" ? "" : "Paylaşılamadı: " + e.message, e.name !== "AbortError"); }
  };
}

loadClips();
