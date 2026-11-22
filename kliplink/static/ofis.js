"use strict";
/* KLİPLİNK — 3D ajan ofisi (three.js r128) */
const $ = (s) => document.querySelector(s);

// ---------- tema + sekme göstergesi ----------
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  $("#theme").textContent = t === "dark" ? "🌙 Koyu" : "☀️ Açık";
  try { localStorage.setItem("kliplink-theme", t); } catch (e) {}
  if (window.scene3d) scene3d.retheme();
}
$("#theme").onclick = () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
function moveInd() {
  const t = document.querySelector(".tab.active"), ind = document.querySelector(".tab-ind");
  if (t && ind) { ind.style.left = t.offsetLeft + "px"; ind.style.width = t.offsetWidth + "px"; }
}
window.addEventListener("resize", moveInd);
(document.fonts ? document.fonts.ready : Promise.resolve()).then(moveInd);
setTimeout(moveInd, 300);

const fmt = (n) => (n = +n || 0, n >= 1e6 ? (n / 1e6).toFixed(2).replace(".", ",") + " Mn"
  : n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(".", ",") + "B" : String(n));
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---------- ajanlar ----------
const AGENTS = [
  { id: "hunter", name: "Klip Avcısı", emoji: "🎯", color: 0xff3b5c, pos: [-3.2, 0, -2.2] },
  { id: "editor", name: "Kurgucu", emoji: "✂️", color: 0x2f8bff, pos: [3.2, 0, -2.2] },
  { id: "publisher", name: "Yayıncı", emoji: "📤", color: 0x2bd463, pos: [-3.2, 0, 2.4] },
  { id: "analyst", name: "Analist", emoji: "📊", color: 0xb26bff, pos: [3.2, 0, 2.4] },
];
let DATA = null;

// ---------- 3D sahne ----------
const canvas = $("#c3d");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
const YELLOW = 0xffd400;

const hemi = new THREE.HemisphereLight(0xffffff, 0x222222, 0.55); scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffffff, 0.8); sun.position.set(6, 12, 8); sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024); Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12 });
scene.add(sun);

// zemin + ızgara
const floor = new THREE.Mesh(new THREE.CircleGeometry(16, 64), new THREE.MeshStandardMaterial({ color: 0x111111, roughness: .9 }));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
const grid = new THREE.GridHelper(32, 32, YELLOW, YELLOW); grid.material.opacity = 0.12; grid.material.transparent = true; grid.position.y = 0.01; scene.add(grid);
const ring = new THREE.Mesh(new THREE.RingGeometry(15.6, 16, 96), new THREE.MeshBasicMaterial({ color: YELLOW, side: THREE.DoubleSide }));
ring.rotation.x = -Math.PI / 2; ring.position.y = 0.02; scene.add(ring);

// merkez: dönen KLİPLİNK çekirdeği
const core = new THREE.Group(); scene.add(core); core.position.set(0, 2.2, 0);
const coreBox = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.2, 1.2), new THREE.MeshStandardMaterial({ color: YELLOW, emissive: YELLOW, emissiveIntensity: .35, transparent: true, opacity: .85 }));
const coreWire = new THREE.Mesh(new THREE.IcosahedronGeometry(1.25, 1), new THREE.MeshBasicMaterial({ color: YELLOW, wireframe: true, transparent: true, opacity: .45 }));
core.add(coreBox, coreWire);
const coreLight = new THREE.PointLight(YELLOW, 1.2, 9); core.add(coreLight);
const pillar = new THREE.Mesh(new THREE.CylinderGeometry(.5, .8, 1, 24), new THREE.MeshStandardMaterial({ color: 0x1b1b1b, metalness: .4, roughness: .5 }));
pillar.position.y = .5; pillar.castShadow = true; scene.add(pillar);
// yörüngede dönen klip kartları (9:16)
const orbit = new THREE.Group(); core.add(orbit);
for (let i = 0; i < 6; i++) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(.34, .6), new THREE.MeshBasicMaterial({ color: i % 2 ? 0xffffff : YELLOW, side: THREE.DoubleSide }));
  const a = i / 6 * Math.PI * 2; m.position.set(Math.cos(a) * 1.9, Math.sin(a * 2) * .25, Math.sin(a) * 1.9); m.lookAt(0, m.position.y, 0);
  orbit.add(m);
}

// masa + ajan üretici
const pickables = [];
function makeStation(a) {
  const g = new THREE.Group(); g.position.set(...a.pos); g.lookAt(0, 0, 0); scene.add(g);
  const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: .6, ...o });
  // masa
  const top = new THREE.Mesh(new THREE.BoxGeometry(2.4, .12, 1.2), mat(0x2a2a2a)); top.position.set(0, .95, .55); top.castShadow = top.receiveShadow = true;
  const legGeo = new THREE.BoxGeometry(.1, .95, .1);
  [[-1.1, .1], [1.1, .1], [-1.1, 1], [1.1, 1]].forEach(([x, z]) => { const l = new THREE.Mesh(legGeo, mat(0x111111)); l.position.set(x, .47, z); g.add(l); });
  const edge = new THREE.Mesh(new THREE.BoxGeometry(2.42, .03, 1.22), new THREE.MeshBasicMaterial({ color: a.color })); edge.position.set(0, .89, .55);
  g.add(top, edge);
  // monitör
  const mon = new THREE.Mesh(new THREE.BoxGeometry(1.3, .8, .06), mat(0x0b0b0b)); mon.position.set(0, 1.55, .95); mon.castShadow = true;
  const scr = new THREE.Mesh(new THREE.PlaneGeometry(1.2, .7), new THREE.MeshBasicMaterial({ color: a.color })); scr.position.set(0, 1.55, .918); scr.rotation.y = Math.PI;
  const glow = new THREE.PointLight(a.color, .9, 4); glow.position.set(0, 1.5, .6);
  g.add(mon, scr, glow);
  // ajan (karakter)
  const body = new THREE.Group(); body.position.set(0, 0, -.25); g.add(body);
  const chair = new THREE.Mesh(new THREE.BoxGeometry(.8, .1, .8), mat(0x161616)); chair.position.set(0, .55, -.05);
  const back = new THREE.Mesh(new THREE.BoxGeometry(.8, .8, .1), mat(0x161616)); back.position.set(0, .95, -.45);
  const torso = new THREE.Mesh(new THREE.CylinderGeometry(.28, .34, .8, 16), mat(a.color, { roughness: .4 })); torso.position.set(0, 1.05, 0); torso.castShadow = true;
  const head = new THREE.Mesh(new THREE.SphereGeometry(.26, 24, 16), mat(0xf2c9a0)); head.position.set(0, 1.68, .02); head.castShadow = true;
  const cap = new THREE.Mesh(new THREE.SphereGeometry(.27, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), mat(0x111111)); cap.position.copy(head.position).add(new THREE.Vector3(0, .03, 0));
  const visor = new THREE.Mesh(new THREE.BoxGeometry(.3, .04, .22), mat(0x111111)); visor.position.set(0, 1.72, .24);
  const phones = new THREE.Mesh(new THREE.TorusGeometry(.27, .035, 8, 24, Math.PI), mat(YELLOW, { emissive: YELLOW, emissiveIntensity: .3 })); phones.position.set(0, 1.7, .02); phones.rotation.y = Math.PI / 2;
  const eyeG = new THREE.SphereGeometry(.035, 8, 8), eyeM = new THREE.MeshBasicMaterial({ color: 0x111111 });
  const e1 = new THREE.Mesh(eyeG, eyeM), e2 = new THREE.Mesh(eyeG, eyeM); e1.position.set(-.09, 1.7, .24); e2.position.set(.09, 1.7, .24);
  const armG = new THREE.BoxGeometry(.12, .12, .55);
  const armL = new THREE.Mesh(armG, mat(a.color)), armR = new THREE.Mesh(armG, mat(a.color));
  armL.position.set(-.3, 1.08, .3); armR.position.set(.3, 1.08, .3);
  body.add(chair, back, torso, head, cap, visor, phones, e1, e2, armL, armR);
  // tıklama alanı
  const hit = new THREE.Mesh(new THREE.BoxGeometry(2.6, 2.4, 2), new THREE.MeshBasicMaterial({ visible: false })); hit.position.set(0, 1.2, .3);
  hit.userData.agent = a.id; g.add(hit); pickables.push(hit);
  a.obj = { g, scr, glow, body, head, armL, armR, anchor: new THREE.Vector3(0, 2.35, -.25) };
}
AGENTS.forEach(makeStation);

// süzülen parçacıklar
const pts = new THREE.BufferGeometry(); const P = 220, arr = new Float32Array(P * 3);
for (let i = 0; i < P; i++) { arr[i * 3] = (Math.random() - .5) * 28; arr[i * 3 + 1] = Math.random() * 8; arr[i * 3 + 2] = (Math.random() - .5) * 28; }
pts.setAttribute("position", new THREE.BufferAttribute(arr, 3));
const dust = new THREE.Points(pts, new THREE.PointsMaterial({ color: YELLOW, size: .06, transparent: true, opacity: .7 })); scene.add(dust);

// tema renkleri
window.scene3d = {
  retheme() {
    const light = document.documentElement.dataset.theme === "light";
    scene.background = new THREE.Color(light ? 0xf3f3f3 : 0x000000);
    scene.fog = new THREE.Fog(light ? 0xf3f3f3 : 0x000000, 14, 34);
    floor.material.color.set(light ? 0xffffff : 0x0e0e0e);
    grid.material.opacity = light ? .25 : .12;
    hemi.intensity = light ? .9 : .55;
    dust.material.color.set(light ? 0x111111 : YELLOW);
  },
};
scene3d.retheme();

// ---------- kamera: otomatik dönüş + sürükleme ----------
let az = .6, el = .55, dist = 13, auto = true, lastTouch = 0;
let drag = null;
canvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, az, el, moved: false }; auto = false; });
addEventListener("pointermove", (e) => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
  az = drag.az - dx * .006; el = Math.min(1.2, Math.max(.18, drag.el + dy * .004));
});
addEventListener("pointerup", (e) => { if (drag && !drag.moved) pick(e); drag = null; lastTouch = performance.now(); });
canvas.addEventListener("wheel", (e) => { dist = Math.min(22, Math.max(8, dist + e.deltaY * .01)); e.preventDefault(); }, { passive: false });

const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
function pick(e) {
  const r = canvas.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObjects(pickables)[0];
  if (hit) openPanel(hit.object.userData.agent);
}

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  renderer.setSize(w, h, false); camera.aspect = w / h;
  dist = w < 500 ? 23 : w < 900 ? 18 : 13; camera.updateProjectionMatrix();
}
addEventListener("resize", resize); resize();

// ---------- etiketler ----------
const labels = {};
AGENTS.forEach((a) => {
  const d = document.createElement("div"); d.className = "bubble"; d.innerHTML = `<b>${a.emoji} ${a.name}</b><span>yükleniyor…</span>`;
  d.onclick = () => openPanel(a.id); $("#labels").appendChild(d); labels[a.id] = d;
});
function setLabel(id, text, busy) { const d = labels[id]; d.querySelector("span").textContent = text; d.classList.toggle("busy", !!busy); }

// ---------- animasyon döngüsü ----------
const clock = new THREE.Clock(); const v = new THREE.Vector3();
function frame() {
  requestAnimationFrame(frame);
  const t = clock.getElapsedTime();
  if (!auto && performance.now() - lastTouch > 6000 && !drag) auto = true;
  if (auto) az += .0015;
  camera.position.set(Math.sin(az) * dist * Math.cos(el), 1.6 + Math.sin(el) * dist, Math.cos(az) * dist * Math.cos(el));
  camera.lookAt(0, 1.4, 0);
  core.rotation.y = t * .6; coreBox.rotation.x = t * .8; coreWire.rotation.z = -t * .4; orbit.rotation.y = -t * .9;
  core.position.y = 2.2 + Math.sin(t * 1.4) * .15;
  dust.rotation.y = t * .02;
  const busyEditor = DATA && DATA.running > 0;
  AGENTS.forEach((a, i) => {
    const o = a.obj, speed = a.id === "editor" && busyEditor ? 18 : 9;
    o.armL.position.y = 1.08 + Math.max(0, Math.sin(t * speed + i)) * .06;
    o.armR.position.y = 1.08 + Math.max(0, Math.sin(t * speed + i + Math.PI)) * .06;
    o.head.rotation.y = Math.sin(t * .7 + i * 2) * .35;
    o.body.position.y = Math.sin(t * 2 + i) * .015;
    o.glow.intensity = .7 + Math.sin(t * (a.id === "editor" && busyEditor ? 14 : 3) + i) * .25;
    // etiketi ekrana yansıt
    v.copy(o.anchor); o.g.localToWorld(v); v.project(camera);
    const d = labels[a.id];
    if (v.z < 1) {
      const cw = canvas.clientWidth, half = Math.min(d.offsetWidth / 2 + 6, cw / 2);
      d.style.display = "";
      d.style.left = Math.min(cw - half, Math.max(half, (v.x + 1) / 2 * cw)) + "px";
      d.style.top = Math.max(d.offsetHeight + 4, (1 - v.y) / 2 * canvas.clientHeight) + "px";
    }
    else d.style.display = "none";
  });
  renderer.render(scene, camera);
}
frame();

// ---------- veri ----------
async function load() {
  try {
    const r = await fetch("/api/office"); DATA = await r.json();
  } catch (e) { $("#hudline").textContent = "sunucuya ulaşılamadı"; return; }
  const live = DATA.streamers.filter((s) => s.live);
  const plan = DATA.plan || {}, posts = plan.posts || [];
  const today = new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Istanbul" });
  const next = posts.find((p) => !["paylaşıldı", "published"].includes(p.status) && (p.date || today) >= today);
  setLabel("hunter", live.length ? `🔴 ${live.map((s) => s.name).join(", ")} canlı` : "yayıncılar izleniyor", live.length);
  setLabel("editor", DATA.running ? "video kesiliyor…" : DATA.last_file ? "son klip hazır ✔" : "klip bekliyor", DATA.running);
  setLabel("publisher", next ? `${next.time} · ${next.title}` : "sıradaki klibi bekliyor", !!next);
  loadAnalyst();
  $("#hudline").textContent = `${live.length} yayıncı canlı · ${posts.length} zamanlanmış paylaşım`;
  if (!$("#panel").hidden && $("#panel").dataset.agent) openPanel($("#panel").dataset.agent);
}
let AN = null;
async function loadAnalyst() {
  try { AN = await (await fetch("/api/analyst")).json(); }
  catch (e) { setLabel("analyst", "veri alınamadı", false); return; }
  setLabel("analyst", `${AN.tips.length} öneri · ${AN.now}`, true);
  if (!$("#panel").hidden && $("#panel").dataset.agent === "analyst") openPanel("analyst");
}
setInterval(load, 30000); load();
setInterval(() => { $("#clock").textContent = new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul" }); }, 1000);

// ---------- panel ----------
function openPanel(id) {
  const a = AGENTS.find((x) => x.id === id); if (!a) return;
  const p = $("#panel"); p.hidden = false; p.dataset.agent = id;
  $("#p-title").textContent = `${a.emoji} ${a.name}`;
  const d = DATA || { streamers: [], plan: {} }, plan = d.plan || {};
  let html = "";
  if (id === "hunter") {
    html = `<p class="hint">Takip edilen yayıncılar ve bugünün en çok izlenen klipleri. 90 sn'de bir yenilenir.</p><ul>` +
      d.streamers.map((s) => `<li><span class="tag ${s.live ? "live" : "off"}">${s.live ? "CANLI " + fmt(s.viewers) : "kapalı"}</span>
        <b>${esc(s.name || s.slug)}</b>${s.live ? `<div class="m">${esc(s.title)}</div>` : ""}
        ${s.top_clip ? `<div class="m">🔥 Günün klibi: “${esc(s.top_clip)}” · ${fmt(s.top_views)} izlenme</div>` : ""}</li>`).join("") + `</ul>
      <p class="row"><a class="primary btn" href="/">Stüdyoda klipleri aç →</a></p>`;
  } else if (id === "editor") {
    html = `<ul><li><b>Durum:</b> ${d.running ? `video kesiliyor (${esc(d.running_step)})` : "boşta"}</li>
      <li><b>Bu oturumda hazırlanan:</b> ${d.rendered || 0} klip</li>
      ${d.last_file ? `<li><b>Son klip:</b><div class="m">${esc(d.last_file)}</div><a class="btn ghost" href="/api/out/${encodeURIComponent(d.last_file)}" target="_blank">▶︎ İzle</a></li>` : ""}</ul>
      <p class="hint">Format: 9:16, üst %42 kamera / alt %58 oyun, Kick şeridi, renkli isim başlığı.</p>`;
  } else if (id === "publisher") {
    const posts = plan.posts || [];
    html = `<p class="hint">Klibi Stüdyo'da hazırla → “Claude'a gönder” → yapıştır. Saat, açıklama ve hashtag'leri ben seçip TikTok + Instagram'a zamanlarım.</p>
      <p><b>Günlük saatler:</b> ${(plan.slots || []).join(" · ")}</p><ul>` +
      (posts.length ? posts.map((x) => `<li><span class="tag ${x.status === "paylaşıldı" ? "ok" : "wait"}">${esc(x.status || "zamanlandı")}</span>
        <b>${esc(x.time)}</b> — ${esc(x.title)}<div class="m">${(x.platforms || []).map((pl) => `<span class="tag ${pl === "TikTok" ? "tt" : "ig"}">${esc(pl)}</span>`).join("")}</div></li>`).join("")
        : `<li>Henüz zamanlanmış paylaşım yok.</li>`) + `</ul>`;
  } else if (!AN) {
    html = `<p class="hint">Veriler çekiliyor…</p>`; loadAnalyst();
  } else {
    const delta = (c) => c.d ? `<span class="tag ${c.d > 0 ? "ok" : "live"}">${c.d > 0 ? "+" : ""}${fmt(c.d)}</span>` : "";
    html = `<p class="hint">${AN.tiktok_live ? "🟢 Canlı veri" : "🟡 TikTok'a şu an ulaşılamadı, son kayıt gösteriliyor"} · ${esc(AN.now)}
        <button class="ghost" id="an-refresh" style="padding:2px 8px;margin-left:6px">↻ Yenile</button></p>
      <div class="an-cards">${AN.cards.map((c) => `<div class="an-card"><div class="m">${esc(c.k)}</div><b>${fmt(c.v)}</b> ${delta(c)}</div>`).join("")}</div>
      <h4>💡 Öneriler</h4><ul>${AN.tips.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      ${AN.top.length ? `<h4>🏆 En iyi Reels</h4><ul>${AN.top.map((r) => `<li><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>
        <div class="m">${fmt(r.views)} izlenme · %${r.watched} izlenme oranı</div></li>`).join("")}</ul>` : ""}`;
  }
  $("#p-body").innerHTML = html;
}
document.addEventListener("click", (e) => { if (e.target.id === "an-refresh") { AN = null; openPanel("analyst"); } });
$("#close").onclick = () => { $("#panel").hidden = true; $("#panel").dataset.agent = ""; };
