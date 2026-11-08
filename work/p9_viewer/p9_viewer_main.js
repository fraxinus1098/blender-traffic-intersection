// SH 249 at Spring Cypress – Phase 9 offline viewer (three.js, bundled by esbuild into one HTML file).
// Extends the Phase 8 viewer (work/p8_viewer/p8_viewer_main.js) with plan-sheet overlays, an Existing | Proposed split,
// deep links, an equipment list, a measure / clearance tool, MUTCD 4D cones for the driver views and Mapillary photo overlays.
// Embedded data: GLB (base64) in <script id="glb-data">, camera presets in <script id="cam-data"> (work/p9_cameras.json),
// sheets / photos / cones in <script id="extra-data"> (work/p9_viewer_data.py).
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const TINT = { remove: new THREE.Color(0.85, 0.06, 0.05), new: new THREE.Color(0.10, 0.72, 0.14) }; // Phase 7 change view
const TINT_MIX = 0.6;
const SUN_DIR = new THREE.Vector3(0.765, 0.628, 0.142).normalize(); // 15 Apr 2026 10:00 CDT, scene az 100.5°, el 38.9°
const FT = 0.3048;
const SHEET_Y = 0.17; // plan sheets drape just above the 6-in. curb/island tops

const $ = (id) => document.getElementById(id);
const status = (t) => { $('loading').textContent = t; };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmtFt = (m) => (m / FT).toFixed(1) + ' ft';

// ---------- renderer / scene ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, logarithmicDepthBuffer: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping; // Blender view transform "Standard"
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
$('app').appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.2, 8000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.12;
controls.screenSpacePanning = true;
controls.maxPolarAngle = Math.PI * 0.495;
controls.maxDistance = 3000;

const hemi = new THREE.HemisphereLight(0xdde8f4, 0x8a8577, 2.4);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff6e8, 3.4);
const SUN_CENTER = new THREE.Vector3(20, 0, 0);
sun.position.copy(SUN_CENTER).addScaledVector(SUN_DIR, 600);
sun.target.position.copy(SUN_CENTER);
sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
Object.assign(sun.shadow.camera, { left: -230, right: 230, top: 230, bottom: -230, near: 100, far: 1200 });
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.04;
scene.add(sun, sun.target);

// overlay groups (not part of the GLB; never picked as model objects)
const sheetGroup = new THREE.Group(); const coneGroup = new THREE.Group(); const measureGroup = new THREE.Group(); const photoGroup = new THREE.Group();
scene.add(sheetGroup, coneGroup, measureGroup, photoGroup);

// ---------- state ----------
const state = {
  mode: 'proposed', split: null, preset: null,
  layers: { roadway: true, existing: true, proposed: true, context: true, aerial: true, radar: false, photos: true },
  sheets: 'off', sheetOpacity: 0.85, cones: true, tool: null,
};
const items = []; // {mesh, layer, status, orig: material|material[]}
let root = null, selected = null, boxHelper = null;
const tintCache = new Map();
const EXTRA = JSON.parse($('extra-data').textContent);
const CAMS = JSON.parse($('cam-data').textContent);

function extrasOf(o) { // nearest ancestor carrying sh249_* tags
  for (let p = o; p; p = p.parent) if (p.userData && (p.userData.sh249_status || p.userData.sh249_type)) return p;
  return null;
}
function layerOf(o) {
  const names = [];
  for (let p = o; p; p = p.parent) names.push(p.name);
  if (names.includes('Aerial')) return 'aerial';
  if (names.includes('Context')) return 'context';
  if (names.includes('Engineering')) return 'radar';
  if (names.includes('E_Roadway')) return 'roadway';
  if (names.includes('Existing')) return 'existing';
  if (names.includes('Proposed')) return 'proposed';
  return 'context';
}
function tinted(mat, st) {
  const key = mat.uuid + st;
  if (!tintCache.has(key)) {
    const m = mat.clone();
    if (m.color) m.color.lerp(TINT[st], TINT_MIX);
    if (m.emissive) m.emissive.multiplyScalar(0.4).add(TINT[st].clone().multiplyScalar(0.12));
    tintCache.set(key, m);
  }
  return tintCache.get(key);
}

// visibility + materials for one mode (called once per render pass, so the split view can draw two modes)
function applyVis(mode) {
  for (const it of items) {
    let vis = state.layers[it.layer];
    if (mode === 'existing' && it.status === 'new') vis = false;
    if (mode === 'proposed' && it.status === 'remove') vis = false;
    it.mesh.visible = vis;
    const tint = mode === 'change' && (it.status === 'remove' || it.status === 'new');
    it.mesh.material = tint
      ? (Array.isArray(it.orig) ? it.orig.map((m) => tinted(m, it.status)) : tinted(it.orig, it.status))
      : it.orig;
  }
  const sheetStatus = mode === 'existing' ? 'existing' : 'proposed';
  for (const m of sheetGroup.children) {
    const s = m.userData.sheet;
    m.visible = state.sheets !== 'off' && (state.sheets === 'both' || state.sheets === s.kind) && s.status === sheetStatus;
    m.material.opacity = state.sheetOpacity;
  }
  photoGroup.visible = state.layers.photos;
}
function applyView() {
  applyVis(state.mode);
  document.querySelectorAll('#modes button').forEach((b) => b.classList.toggle('on', b.dataset.mode === state.mode && !state.split));
  $('legend').style.display = state.mode === 'change' && !state.split ? 'block' : 'none';
  $('split-bar').style.display = state.split ? 'block' : 'none';
  $('split-cb').checked = !!state.split;
  if (state.split) $('split-bar').style.left = (state.split * 100) + '%';
  if (selected && !isShown(selected)) select(null);
  updateLink();
}
function isShown(o) { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; }

// ---------- camera presets ----------
const PRESETS = [
  ['Overview', [['Overview (oblique)', 'CAM_Review_Oblique'], ['Top (plan)', 'CAM_Review_Top'],
    ['SB intersection close-up', 'CAM_P5_SB'], ['NB intersection close-up', 'CAM_P5_NB'], ['Radar zones – top', 'CAM_P7_RadarTop'],
    ['SB curb ramps', 'CAM_P5b_SB_Ramps'], ['NB curb ramps', 'CAM_P5b_NB_Ramps']]],
  ["Driver's eye (3.5 ft, at stop bar)", [['SB int. – southbound feeder', 'CAM_P7_Drv_SBint_SB'], ['SB int. – eastbound', 'CAM_P7_Drv_SBint_EB'],
    ['SB int. – westbound', 'CAM_P7_Drv_SBint_WB'], ['NB int. – northbound feeder', 'CAM_P7_Drv_NBint_NB'],
    ['NB int. – eastbound', 'CAM_P7_Drv_NBint_EB'], ['NB int. – westbound', 'CAM_P7_Drv_NBint_WB']]],
  ['Crosswalks (pedestrian eye, 5 ft)', [['SB int. – north leg', 'CAM_P7_Ped_SB_N'], ['SB int. – west leg', 'CAM_P7_Ped_SB_W'],
    ['SB int. – south leg', 'CAM_P7_Ped_SB_S'], ['SB int. – right-turn channel', 'CAM_P7_Ped_SB_CH'],
    ['NB int. – north leg', 'CAM_P7_Ped_NB_N'], ['NB int. – east leg', 'CAM_P7_Ped_NB_E'],
    ['NB int. – south leg', 'CAM_P7_Ped_NB_S'], ['NB int. – right-turn channel', 'CAM_P7_Ped_NB_CH'],
    ['APS push button, pole D', 'CAM_P7_APS_D']]],
];
const TOP_HFOV = 30; // ortho Blender cameras are shown as a high, narrow perspective view of the same width
function presetPose(name) {
  const c = CAMS[name];
  const aspect = camera.aspect;
  const pos = new THREE.Vector3(...c.pos), fwd = new THREE.Vector3(...c.fwd).normalize();
  if (c.type === 'ORTHO') {
    const h = (c.ortho / 2) / Math.tan(THREE.MathUtils.degToRad(TOP_HFOV / 2));
    const target = new THREE.Vector3(pos.x, 0, pos.z);
    const vfov = 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(TOP_HFOV / 2)) / Math.max(aspect, 1));
    return { pos: target.clone().add(new THREE.Vector3(0, h, h * 0.002)), target, fov: THREE.MathUtils.radToDeg(vfov) };
  }
  const hfov = 2 * Math.atan(c.sensor / (2 * c.lens));
  const vfov = aspect >= 1 ? 2 * Math.atan(Math.tan(hfov / 2) / aspect) : hfov;
  let d = 30;
  if (fwd.y < -0.05) d = THREE.MathUtils.clamp(-pos.y / fwd.y, 5, 600);
  return { pos, target: pos.clone().addScaledVector(fwd, d), fov: THREE.MathUtils.radToDeg(vfov) };
}
let anim = null;
function flyPose(p, instant = false) {
  if (instant) { camera.position.copy(p.pos); controls.target.copy(p.target); camera.fov = p.fov; camera.updateProjectionMatrix(); controls.update(); return; }
  anim = { t0: performance.now(), dur: 900, p0: camera.position.clone(), t0v: controls.target.clone(), f0: camera.fov, p };
}
function goto(name, instant = false) {
  if (!CAMS[name]) return;
  $('views').value = name;
  flyPose(presetPose(name), instant);
  state.preset = name;
  showCone(state.cones ? name : null);
  updateLink();
}
function stepAnim(now) {
  if (!anim) return;
  let k = Math.min(1, (now - anim.t0) / anim.dur); k = k * k * (3 - 2 * k);
  camera.position.lerpVectors(anim.p0, anim.p.pos, k);
  controls.target.lerpVectors(anim.t0v, anim.p.target, k);
  camera.fov = anim.f0 + (anim.p.fov - anim.f0) * k; camera.updateProjectionMatrix();
  if (k >= 1) { anim = null; updateLink(); }
}
controls.addEventListener('start', () => { anim = null; if (state.preset) { state.preset = null; $('views').value = ''; } });
controls.addEventListener('end', () => updateLink());

// ---------- DOM labels for 3D points ----------
const labels = []; // {el, pos, group}
function addLabel(text, pos, cls, group) {
  const el = document.createElement('div'); el.className = 'tag ' + (cls || ''); el.innerHTML = text; $('labels').appendChild(el);
  labels.push({ el, pos: pos.clone(), group }); return el;
}
function clearLabels(group) {
  for (let i = labels.length - 1; i >= 0; i--) if (labels[i].group === group) { labels[i].el.remove(); labels.splice(i, 1); }
}
const _v = new THREE.Vector3();
function updateLabels() {
  for (const l of labels) {
    _v.copy(l.pos).project(camera);
    const vis = _v.z < 1 && Math.abs(_v.x) < 1.2 && Math.abs(_v.y) < 1.2 && (l.group !== 'photo' || state.layers.photos);
    l.el.style.display = vis ? 'block' : 'none';
    if (vis) l.el.style.transform = `translate(${((_v.x + 1) / 2) * window.innerWidth}px, ${((1 - _v.y) / 2) * window.innerHeight}px)`;
  }
}

// ---------- picking / measuring ----------
const raycaster = new THREE.Raycaster();
const ndc = new THREE.Vector2();
let down = null;
renderer.domElement.addEventListener('pointerdown', (e) => { down = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5 || !root) return;
  if (state.tool) measureClick(e.clientX, e.clientY); else pickAt(e.clientX, e.clientY);
});
function rayFrom(x, y) {
  ndc.set((x / window.innerWidth) * 2 - 1, -(y / window.innerHeight) * 2 + 1);
  raycaster.setFromCamera(ndc, camera);
}
function modelHits(includeAerial) {
  return raycaster.intersectObject(root, true).filter((h) => isShown(h.object) && layerOf(h.object) !== 'radar' &&
    (includeAerial || layerOf(h.object) !== 'aerial'));
}
function pickAt(x, y) {
  rayFrom(x, y);
  const ph = state.layers.photos ? raycaster.intersectObject(photoGroup, true) : [];
  const hits = raycaster.intersectObject(root, true).filter((h) => isShown(h.object) && layerOf(h.object) !== 'aerial');
  if (ph.length && (!hits.length || ph[0].distance < hits[0].distance)) { openPhoto(ph[0].object.userData.photoId); return 'photo:' + ph[0].object.userData.photoId; }
  const hit = hits.find((h) => extrasOf(h.object));
  select(hit ? extrasOf(hit.object) : null, hit);
  return hit ? extrasOf(hit.object).name : null;
}
const STATUS_TXT = { remove: 'Existing – to be removed', remain: 'Existing – to remain', new: 'Proposed (new)', context: 'Context', engineering: 'Engineering overlay' };
function select(o) {
  selected = o;
  if (boxHelper) { scene.remove(boxHelper); boxHelper.dispose?.(); boxHelper = null; }
  const info = $('info');
  if (!o) { info.style.display = 'none'; return; }
  const u = o.userData;
  if (!(o.isInstancedMesh)) { boxHelper = new THREE.BoxHelper(o, 0xffd400); scene.add(boxHelper); }
  const rows = [];
  const add = (k, v) => { if (v !== undefined && v !== '') rows.push(`<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`); };
  add('Callout', u.sh249_callout);
  add('Status', STATUS_TXT[u.sh249_status] || u.sh249_status);
  add('Type', (u.sh249_type || '').replace(/_/g, ' '));
  add('Sheet', u.sh249_sheet);
  for (const [k, v] of Object.entries(u)) {
    if (!k.startsWith('sh249_') || ['sh249_callout', 'sh249_status', 'sh249_type', 'sh249_sheet', 'sh249_note', 'sh249_phase'].includes(k)) continue;
    add(k.slice(6).replace(/_/g, ' '), typeof v === 'number' ? +v.toFixed(2) : v);
  }
  info.innerHTML = `<button id="info-x" class="x" title="Close">×</button><h3>${esc(o.name.replace(/\.\d+$/, ''))}</h3>` +
    (u.sh249_note ? `<p class="note">${esc(u.sh249_note)}</p>` : '') + `<table>${rows.join('')}</table>`;
  info.style.display = 'block';
  $('info-x').onclick = () => select(null);
}

const measure = { pts: [] };
function setTool(t) {
  state.tool = state.tool === t ? null : t;
  document.querySelectorAll('#tools button[data-tool]').forEach((b) => b.classList.toggle('on', b.dataset.tool === state.tool));
  renderer.domElement.style.cursor = state.tool ? 'crosshair' : '';
  measure.pts = [];
  if (state.tool) { $('measure').style.display = 'block'; $('measure').innerHTML = state.tool === 'dist'
    ? '<b>Distance</b>: click two points.' : '<b>Clearance</b>: click the underside of an object (e.g. a signal head) to measure the vertical clearance to the surface below.'; }
  else { $('measure').style.display = 'none'; clearMeasure(); }
}
function clearMeasure() { measureGroup.clear(); clearLabels('measure'); }
const dotGeo = new THREE.SphereGeometry(0.12, 12, 8);
const dotMat = new THREE.MeshBasicMaterial({ color: 0xffd400, depthTest: false });
function dot(p) { const m = new THREE.Mesh(dotGeo, dotMat); m.position.copy(p); m.renderOrder = 20; measureGroup.add(m); }
function line(a, b, color = 0xffd400) {
  const g = new THREE.BufferGeometry().setFromPoints([a, b]);
  const l = new THREE.Line(g, new THREE.LineBasicMaterial({ color, depthTest: false })); l.renderOrder = 20; measureGroup.add(l);
}
function measureDist(a, b) {
  clearMeasure(); dot(a); dot(b); line(a, b);
  const d = a.distanceTo(b), dv = Math.abs(b.y - a.y), dh = Math.hypot(b.x - a.x, b.z - a.z);
  const txt = `${fmtFt(d)}<small> · horiz. ${fmtFt(dh)} · vert. ${fmtFt(dv)}</small>`;
  addLabel(txt, a.clone().add(b).multiplyScalar(0.5), 'meas', 'measure');
  $('measure').innerHTML = `<b>Distance</b> ${fmtFt(d)}<br>horizontal ${fmtFt(dh)}, vertical ${fmtFt(dv)}<br><span class="muted">Click two more points to measure again.</span>`;
  return { ft: +(d / FT).toFixed(2), horiz_ft: +(dh / FT).toFixed(2), vert_ft: +(dv / FT).toFixed(2) };
}
function clearanceFrom(p, fromObj) {
  raycaster.set(p.clone().add(new THREE.Vector3(0, -0.002, 0)), new THREE.Vector3(0, -1, 0));
  const own = fromObj ? extrasOf(fromObj) : null;
  const hits = modelHits(true).filter((h) => !own || extrasOf(h.object) !== own);
  if (!hits.length) return null;
  const h = hits[0]; const below = h.point;
  clearMeasure(); dot(p); dot(below); line(p, below, 0x00e0ff);
  const name = (extrasOf(h.object) || h.object).name.replace(/\.\d+$/, '');
  addLabel(`${fmtFt(p.y - below.y)}<small> clearance</small>`, p.clone().add(below).multiplyScalar(0.5), 'meas', 'measure');
  const fromName = own ? own.name.replace(/\.\d+$/, '') : 'point';
  $('measure').innerHTML = `<b>Vertical clearance</b> ${fmtFt(p.y - below.y)}<br>from ${esc(fromName)} down to ${esc(name)}<br><span class="muted">Height above pavement level (z = 0): ${fmtFt(p.y)}</span>`;
  return { ft: +((p.y - below.y) / FT).toFixed(2), from: fromName, to: name, above_datum_ft: +(p.y / FT).toFixed(2) };
}
function measureClick(x, y) {
  rayFrom(x, y);
  const h = modelHits(true)[0];
  if (!h) return null;
  if (state.tool === 'clear') return clearanceFrom(h.point, h.object);
  measure.pts.push(h.point.clone());
  if (measure.pts.length === 1) { clearMeasure(); dot(h.point); return null; }
  const r = measureDist(measure.pts[0], measure.pts[1]); measure.pts = []; return r;
}

// ---------- plan sheets ----------
function texFromB64(b64, mime, cb) {
  const img = new Image(); const tex = new THREE.Texture(img);
  tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
  img.onload = () => { tex.needsUpdate = true; cb && cb(img); };
  img.src = `data:${mime};base64,${b64}`;
  return tex;
}
function buildSheets() {
  for (const s of EXTRA.sheets) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(s.corners.flatMap((c) => [c[0], SHEET_Y, c[2]]), 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(s.uv.flat(), 2));
    g.setIndex([0, 1, 2, 0, 2, 3]); g.computeVertexNormals();
    const m = new THREE.MeshBasicMaterial({ map: texFromB64(s.png, 'image/png'), transparent: true, depthWrite: false, side: THREE.DoubleSide,
      polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -16, opacity: state.sheetOpacity });
    const mesh = new THREE.Mesh(g, m); mesh.renderOrder = 5; mesh.userData.sheet = s; mesh.name = 'SHEET_' + s.sheet;
    sheetGroup.add(mesh);
    s.png = null; // free the base64 string
  }
}

// ---------- visibility cones (MUTCD 4D.13) ----------
function showCone(cam) {
  coneGroup.clear(); clearLabels('cone'); $('cone-card').style.display = 'none';
  const c = cam && EXTRA.cones[cam];
  if (!c || !root) return;
  const apex = new THREE.Vector3(...c.apex); const dir = new THREE.Vector3(...c.dir).normalize();
  const g0 = new THREE.Vector3(apex.x, 0.06, apex.z);
  const pts = [g0]; const n = 24, a0 = THREE.MathUtils.degToRad(c.half_deg);
  for (let i = 0; i <= n; i++) { const a = -a0 + (2 * a0 * i) / n; pts.push(g0.clone().addScaledVector(dir.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), a), c.len_m)); }
  const pos = []; for (let i = 1; i <= n; i++) pos.push(...pts[0].toArray(), ...pts[i].toArray(), ...pts[i + 1].toArray());
  const fg = new THREE.BufferGeometry(); fg.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  const fan = new THREE.Mesh(fg, new THREE.MeshBasicMaterial({ color: 0xffd400, transparent: true, opacity: 0.22, depthWrite: false, side: THREE.DoubleSide,
    polygonOffset: true, polygonOffsetFactor: -6, polygonOffsetUnits: -20 }));
  fan.renderOrder = 6; coneGroup.add(fan);
  const edge = (a) => g0.clone().addScaledVector(dir.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), a), c.len_m);
  const lm = new THREE.LineBasicMaterial({ color: 0xc89b00 });
  coneGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([edge(-a0), g0, edge(a0)]), lm));
  // 40-180 ft past the stop line band (apex is 10 ft behind the line)
  const side = new THREE.Vector3(-dir.z, 0, dir.x);
  for (const d of c.long_m) {
    const m0 = g0.clone().addScaledVector(dir, d + 10 * FT); const hw = Math.tan(a0) * (d + 10 * FT);
    coneGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([m0.clone().addScaledVector(side, -hw), m0.clone().addScaledVector(side, hw)]),
      new THREE.LineDashedMaterial({ color: 0xc89b00, dashSize: 1, gapSize: 0.6 })).computeLineDistances());
  }
  const rows = [];
  for (const [hn, h] of Object.entries(c.heads)) {
    const o = root.getObjectByName(hn); if (!o) continue;
    const p = new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3());
    const ok = h.ok_cone && h.ok_long && h.ok_vis; const col = ok ? 0x1ab824 : 0xd90f0d;
    coneGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(p.x, 0.06, p.z), p]), new THREE.LineBasicMaterial({ color: col })));
    coneGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(apex.x, apex.y, apex.z), p]),
      new THREE.LineDashedMaterial({ color: col, dashSize: 0.8, gapSize: 0.5, transparent: true, opacity: 0.8 })).computeLineDistances());
    const letter = hn.split('_')[2];
    addLabel(`${ok ? '✔' : '✘'} ${letter}`, p.clone().add(new THREE.Vector3(0, 0.9, 0)), ok ? 'ok' : 'bad', 'cone');
    rows.push(`<tr><td>${ok ? '<span class="okc">✔</span>' : '<span class="badc">✘</span>'} ${esc(letter)}</td><td>${h.cone_deg > 0 ? '+' : ''}${h.cone_deg}°</td><td>${h.past_stop_ft} ft</td><td>${Math.round(h.vis_min * 100)} %</td></tr>`);
  }
  $('cone-card').innerHTML = `<button class="x" id="cone-x" title="Hide cone">×</button><b>MUTCD 4D.13 cone · ${esc(c.key.replace('_', ' int. '))}</b>
    <div class="muted">20° either side of the approach axis, from 10 ft behind the stop line (eye 3.5 ft). Heads 40–180 ft past the stop line (4D.14).
    Visibility: share of rays clear from every lane at the stop bar and back to ${c.req_ft} ft (${c.speed} mph, Table 4D-2).</div>
    <table><tr><th>Head</th><th>Angle</th><th>Past stop line</th><th>Visible</th></tr>${rows.join('')}</table>`;
  $('cone-card').style.display = 'block';
  $('cone-x').onclick = () => { state.cones = false; $('cones-cb').checked = false; showCone(null); updateLink(); };
}

// ---------- photos (Mapillary overlays) ----------
const photoState = { id: null, layer: 'existing', opacity: 1 };
function buildPhotoMarkers() {
  const geo = new THREE.ConeGeometry(1.1, 2.2, 4); geo.rotateX(-Math.PI / 2); geo.translate(0, 0, 1.1); // points along +z
  const mat = new THREE.MeshBasicMaterial({ color: 0xff7a00 });
  const list = $('photo-list');
  for (const p of EXTRA.photos) {
    const m = new THREE.Mesh(geo, mat); m.position.set(...p.pos); m.position.y = Math.max(p.pos[1], 1.2);
    m.lookAt(m.position.clone().add(new THREE.Vector3(p.fwd[0], 0, p.fwd[2]))); m.userData.photoId = p.id; m.name = 'PHOTO_' + p.id;
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, m.position.y), mat); post.position.set(p.pos[0], m.position.y / 2, p.pos[2]); post.userData.photoId = p.id;
    photoGroup.add(m, post);
    addLabel('📷', m.position.clone().add(new THREE.Vector3(0, 1.6, 0)), 'cam', 'photo');
    const b = document.createElement('button'); b.className = 'photo-btn';
    b.innerHTML = `<img src="data:image/jpeg;base64,${p.photo}" alt=""><span>${esc(p.title)}<br><small>${esc(p.creator)} · ${esc(p.captured_at.slice(0, 10))}</small></span>`;
    b.onclick = () => openPhoto(p.id); list.appendChild(b);
  }
}
function openPhoto(id, layer) {
  const p = EXTRA.photos.find((x) => x.id === id); if (!p) return false;
  photoState.id = id; if (layer) photoState.layer = layer;
  $('ph-img').src = `data:image/jpeg;base64,${p.photo}`;
  $('ph-title').textContent = p.title;
  const nm = (k) => k.replace(/_/g, ' ');
  const used = p.solve.points.map((k) => `${nm(k)} ${p.solve.check[k][1]} ft`).join(', ');
  const other = Object.entries(p.solve.check).filter(([k]) => !p.solve.points.includes(k)).map(([k, v]) => `${nm(k)} ${v[1]} ft`).join(', ');
  $('ph-credit').innerHTML = `Photo: <b>${esc(p.creator)}</b> via <a href="${esc(p.source)}" target="_blank" rel="noopener">Mapillary</a>, ${esc(p.captured_at)}, ${esc(p.licence)}. Overlay (model render from the solved camera): this project, ${esc(p.licence)}.`;
  $('ph-note').innerHTML = `The photo shows the existing street (Nov 2026); the project is not built. Camera solved on the existing pole points and the ${esc(p.solve.lines.map(nm).join(', '))} line(s) (median ${p.solve.line_median_px} px).
    Model vs photo at the solve points: ${esc(used)}. Other existing equipment: ${esc(other)}. The plans' existing heads and signs differ from what stands today (see the build log, Phase 9B).`;
  setPhotoLayer(photoState.layer);
  $('photo').style.display = 'flex';
  updateLink();
  return true;
}
function setPhotoLayer(layer) {
  const p = EXTRA.photos.find((x) => x.id === photoState.id); if (!p) return;
  photoState.layer = layer;
  const ov = $('ph-ov');
  if (layer === 'photo') ov.style.display = 'none';
  else { ov.src = `data:image/png;base64,${p[layer]}`; ov.style.display = 'block'; ov.style.opacity = photoState.opacity; }
  document.querySelectorAll('#ph-layers button').forEach((b) => b.classList.toggle('on', b.dataset.layer === layer));
  $('ph-legend').style.display = layer === 'proposed' ? 'flex' : 'none';
  updateLink();
}
function closePhoto() { photoState.id = null; $('photo').style.display = 'none'; updateLink(); }
function photoIn3D() {
  const p = EXTRA.photos.find((x) => x.id === photoState.id); if (!p) return;
  closePhoto(); showCone(null);
  const pos = new THREE.Vector3(...p.pos); const fwd = new THREE.Vector3(...p.fwd);
  state.mode = photoState.layer === 'proposed' ? 'change' : 'existing'; applyView();
  // match the photo's vertical field of view (scaled to the window's aspect, at the photo's horizontal FOV)
  const hf = THREE.MathUtils.degToRad(p.hfov_deg); const vf = 2 * Math.atan(Math.tan(hf / 2) / camera.aspect);
  flyPose({ pos, target: pos.clone().addScaledVector(fwd, 40), fov: THREE.MathUtils.radToDeg(vf) });
  state.preset = null; $('views').value = '';
}

// ---------- equipment list ----------
const CAT = [['Mast arm poles', /mast arm pole/], ['Signal heads', /signal head/], ['Pedestrian poles', /pedestal|ped/],
  ['Signs', /sign/], ['Radar detectors', /radar detector/], ['Cabinets & power', /cabinet|electrical|service|ground box/]];
function buildEquipment() {
  const groups = {};
  root.traverse((o) => {
    const u = o.userData; if (!u || !/^(E|P)_/.test(o.name) || !['new', 'remove', 'remain'].includes(u.sh249_status)) return;
    const t = u.sh249_type || ''; const cat = CAT.find((c) => c[1].test(t)); if (!cat) return;
    const x = new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3()).x;
    const inter = x < 0 ? 'SB intersection (west)' : 'NB intersection (east)';
    const key = `${inter}|${u.sh249_status}`;
    (groups[key] ||= []).push({ o, cat: CAT.indexOf(cat), catName: cat[0], label: o.name.replace(/\.\d+$/, ''), callout: u.sh249_callout || '' });
  });
  const ST = { new: 'New', remove: 'To be removed', remain: 'To remain' };
  const html = [];
  for (const inter of ['SB intersection (west)', 'NB intersection (east)']) {
    html.push(`<div class="eq-int">${inter}</div>`);
    for (const st of ['new', 'remove', 'remain']) {
      const g = groups[`${inter}|${st}`]; if (!g) continue;
      g.sort((a, b) => a.cat - b.cat || a.label.localeCompare(b.label));
      html.push(`<details><summary><i class="st-${st}"></i>${ST[st]} (${g.length})</summary>` +
        g.map((e) => `<button class="eq" data-name="${esc(e.o.name)}"><b>${esc(e.callout)}</b> ${esc(e.label)}<small>${esc(e.catName)}</small></button>`).join('') + '</details>');
    }
  }
  $('equip').innerHTML = html.join('');
  $('equip').querySelectorAll('button.eq').forEach((b) => (b.onclick = () => flyTo(b.dataset.name)));
}
function flyTo(name) {
  const o = root.getObjectByName(name); if (!o) return false;
  const st = o.userData.sh249_status;
  if (state.mode === 'existing' && st === 'new') state.mode = 'proposed';
  if (state.mode === 'proposed' && st === 'remove') state.mode = 'existing';
  if (state.split) state.split = null;
  const layer = layerOf(o); if (!state.layers[layer]) { state.layers[layer] = true; syncLayerBoxes(); }
  applyView();
  const box = new THREE.Box3().setFromObject(o); const c = box.getCenter(new THREE.Vector3()); const r = Math.max(box.getSize(new THREE.Vector3()).length(), 3);
  const dir = camera.position.clone().sub(controls.target).normalize();
  if (dir.y < 0.25) { dir.y = 0.35; dir.normalize(); }
  flyPose({ pos: c.clone().addScaledVector(dir, Math.max(r * 2.2, 18)), target: c, fov: camera.fov });
  state.preset = null; $('views').value = ''; showCone(null);
  select(o);
  return true;
}

// ---------- deep links ----------
let linkTimer = null; let linkReady = false;
function linkHash() {
  const q = new URLSearchParams();
  if (state.preset) q.set('cam', state.preset);
  else {
    const r = (v) => v.toArray().map((a) => +a.toFixed(2)).join(',');
    q.set('pos', r(camera.position)); q.set('tgt', r(controls.target)); q.set('fov', camera.fov.toFixed(1));
  }
  q.set('mode', state.mode);
  q.set('layers', Object.entries(state.layers).filter(([, v]) => v).map(([k]) => k).join(','));
  if (state.split) q.set('split', state.split.toFixed(3));
  if (state.sheets !== 'off') { q.set('sheets', state.sheets); q.set('op', state.sheetOpacity.toFixed(2)); }
  if (!state.cones) q.set('cones', '0');
  if (photoState.id) { q.set('photo', photoState.id); q.set('pl', photoState.layer); }
  if (selected) q.set('sel', selected.name);
  return '#' + q.toString().replace(/%2C/g, ',');
}
function updateLink() {
  if (!linkReady) return;
  clearTimeout(linkTimer);
  linkTimer = setTimeout(() => { try { history.replaceState(null, '', linkHash()); } catch (e) { /* file:// in some browsers */ } }, 150);
}
function readLink() {
  const q = new URLSearchParams(location.hash.slice(1));
  if (q.has('mode')) state.mode = q.get('mode');
  if (q.has('layers')) { const on = q.get('layers').split(','); for (const k of Object.keys(state.layers)) state.layers[k] = on.includes(k); }
  if (q.has('split')) state.split = THREE.MathUtils.clamp(+q.get('split'), 0.05, 0.95);
  if (q.has('sheets')) state.sheets = q.get('sheets');
  if (q.has('op')) state.sheetOpacity = +q.get('op');
  if (q.get('cones') === '0') state.cones = false;
  return q;
}
function applyLinkCamera(q) {
  if (q.has('cam') && CAMS[q.get('cam')]) goto(q.get('cam'), true);
  else if (q.has('pos') && q.has('tgt')) {
    const v = (s) => new THREE.Vector3(...s.split(',').map(Number));
    flyPose({ pos: v(q.get('pos')), target: v(q.get('tgt')), fov: +(q.get('fov') || 40) }, true);
  } else goto('CAM_Review_Oblique', true);
  if (q.has('sel')) { const o = root.getObjectByName(q.get('sel')); if (o) select(o); }
  if (q.has('photo')) openPhoto(q.get('photo'), q.get('pl') || 'existing');
}
async function copyLink() {
  const url = location.href.split('#')[0] + linkHash();
  let ok = false;
  try { await navigator.clipboard.writeText(url); ok = true; } catch (e) { /* not allowed on file:// in some browsers */ }
  const box = $('link-box'); box.value = url; box.style.display = 'block'; box.select();
  $('link-msg').textContent = ok ? 'Link copied.' : 'Copy the link above (Ctrl+C).';
  return url;
}

// ---------- split view ----------
function setSplit(f) {
  state.split = f == null || f === false ? null : THREE.MathUtils.clamp(f, 0.05, 0.95);
  applyView();
}
(function splitDrag() {
  const bar = $('split-bar'); let drag = false;
  bar.addEventListener('pointerdown', (e) => { drag = true; bar.setPointerCapture(e.pointerId); e.stopPropagation(); });
  bar.addEventListener('pointermove', (e) => { if (drag) { state.split = THREE.MathUtils.clamp(e.clientX / window.innerWidth, 0.05, 0.95); bar.style.left = (state.split * 100) + '%'; } });
  bar.addEventListener('pointerup', () => { drag = false; updateLink(); });
})();

// ---------- UI ----------
function syncLayerBoxes() { document.querySelectorAll('#layers input').forEach((cb) => (cb.checked = state.layers[cb.dataset.layer])); }
function buildUI() {
  document.querySelectorAll('#modes button').forEach((b) => (b.onclick = () => { state.mode = b.dataset.mode; state.split = null; applyView(); }));
  syncLayerBoxes();
  document.querySelectorAll('#layers input').forEach((cb) => (cb.onchange = () => { state.layers[cb.dataset.layer] = cb.checked; applyView(); }));
  const sel = $('views');
  const blank = document.createElement('option'); blank.value = ''; blank.textContent = '(free camera)'; blank.disabled = true; sel.appendChild(blank);
  for (const [group, list] of PRESETS) {
    const g = document.createElement('optgroup'); g.label = group;
    for (const [label, cam] of list) if (CAMS[cam]) { const op = document.createElement('option'); op.value = cam; op.textContent = label; g.appendChild(op); }
    sel.appendChild(g);
  }
  sel.onchange = () => goto(sel.value);
  $('panel-toggle').onclick = () => document.body.classList.toggle('collapsed');
  $('split-cb').onchange = (e) => setSplit(e.target.checked ? 0.5 : null);
  $('sheets').value = state.sheets; $('sheets').onchange = (e) => { state.sheets = e.target.value; applyView(); };
  $('sheet-op').value = state.sheetOpacity; $('sheet-op').oninput = (e) => { state.sheetOpacity = +e.target.value; applyView(); };
  $('cones-cb').checked = state.cones;
  $('cones-cb').onchange = (e) => { state.cones = e.target.checked; showCone(state.cones ? state.preset : null); updateLink(); };
  document.querySelectorAll('#tools button[data-tool]').forEach((b) => (b.onclick = () => setTool(b.dataset.tool)));
  $('copy-link').onclick = copyLink;
  $('ph-x').onclick = closePhoto; $('ph-3d').onclick = photoIn3D;
  document.querySelectorAll('#ph-layers button').forEach((b) => (b.onclick = () => setPhotoLayer(b.dataset.layer)));
  $('ph-op').oninput = (e) => { photoState.opacity = +e.target.value; $('ph-ov').style.opacity = photoState.opacity; };
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (photoState.id) closePhoto(); else if (state.tool) setTool(state.tool); } });
}

// ---------- load ----------
function b64ToBuffer(b64) {
  const bin = atob(b64.trim()); const n = bin.length; const u = new Uint8Array(n);
  for (let i = 0; i < n; i++) u[i] = bin.charCodeAt(i);
  return u.buffer;
}
function prepare(gltf) {
  root = gltf.scene; scene.add(root);
  root.traverse((o) => {
    if (!o.isMesh) return;
    const layer = layerOf(o);
    const ex = extrasOf(o);
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    for (const m of mats) {
      if (m.name === 'MAT_Aerial_NAIP' && !m.userData.fixed) { // Blender emission shader -> unlit
        const basic = new THREE.MeshBasicMaterial({ map: m.emissiveMap, side: THREE.DoubleSide, name: m.name });
        basic.userData.fixed = true;
        o.material = Array.isArray(o.material) ? o.material.map((x) => (x === m ? basic : x)) : basic;
      }
      if (m.name.startsWith('MAT_P7_RZ')) { // radar zones: translucent, no depth write, drawn after markings
        m.depthWrite = false; m.transparent = m.name.endsWith('Fill') || m.name.endsWith('Edge');
        m.polygonOffset = true; m.polygonOffsetFactor = -2; m.polygonOffsetUnits = -8;
      }
      if (m.name.startsWith('MAT_Paint') || m.name.startsWith('MAT_RPM') || m.name === 'MAT_DetectWarn') {
        m.polygonOffset = true; m.polygonOffsetFactor = -1; m.polygonOffsetUnits = -4;
      }
    }
    if (layer === 'radar') o.renderOrder = 10;
    o.castShadow = !['aerial', 'radar'].includes(layer) && !/^(E|P)_MK_/.test(o.name) && !/_MK_/.test(ex?.name || '');
    o.receiveShadow = layer !== 'radar';
    items.push({ mesh: o, layer, status: ex?.userData.sh249_status || null, orig: o.material });
  });
  buildSheets();
  buildPhotoMarkers();
  buildEquipment();
  const q = readLink();
  buildUI();
  applyView();
  applyLinkCamera(q);
  linkReady = true; updateLink();
  $('loading').style.display = 'none';
  window.__viewer.ready = true;
}

status('Decoding model…');
setTimeout(() => {
  const buf = b64ToBuffer($('glb-data').textContent);
  status('Building scene…');
  new GLTFLoader().parse(buf, '', prepare, (e) => status('Could not load the model: ' + e.message));
}, 30);

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
renderer.setAnimationLoop((now) => {
  stepAnim(now);
  controls.update();
  if (boxHelper) boxHelper.update();
  if (state.split && root) {
    const W = renderer.domElement.clientWidth, H = renderer.domElement.clientHeight; const x = Math.round(state.split * W);
    renderer.setScissorTest(true);
    applyVis('existing'); renderer.setScissor(0, 0, x, H); renderer.render(scene, camera);
    applyVis('proposed'); renderer.setScissor(x, 0, W - x, H); renderer.render(scene, camera);
    renderer.setScissorTest(false);
  } else renderer.render(scene, camera);
  updateLabels();
});

// test hook
const V3 = (a) => new THREE.Vector3(...a);
window.__viewer = {
  ready: false,
  setMode: (m) => { state.mode = m; state.split = null; applyView(); },
  setLayer: (k, v) => { state.layers[k] = v; syncLayerBoxes(); applyView(); },
  goto: (n) => goto(n, true),
  look: (p, t, fov) => { anim = null; camera.position.set(...p); controls.target.set(...t); if (fov) { camera.fov = fov; camera.updateProjectionMatrix(); } controls.update(); state.preset = null; $('views').value = ''; showCone(null); updateLink(); },
  pickAt, selectByName: (n) => { const o = root.getObjectByName(n); select(o); return !!o; },
  setSplit, setSheets: (kind, op) => { state.sheets = kind; if (op != null) state.sheetOpacity = op; $('sheets').value = kind; $('sheet-op').value = state.sheetOpacity; applyView(); },
  measure: (a, b) => { if (state.tool !== 'dist') setTool('dist'); return measureDist(V3(a), V3(b)); },
  clearance: (name) => { // from the bottom centre of a named object down to the surface below
    const o = root.getObjectByName(name); if (!o) return null; if (state.tool !== 'clear') setTool('clear');
    const b = new THREE.Box3().setFromObject(o); const c = b.getCenter(new THREE.Vector3()); c.y = b.min.y; return clearanceFrom(c, o);
  },
  where: (name) => { const o = root.getObjectByName(name); if (!o) return null; const b = new THREE.Box3().setFromObject(o); const c = b.getCenter(new THREE.Vector3()); return [c.x, b.min.y, c.z].map((v) => +v.toFixed(3)); },
  measureAt: (x, y) => measureClick(x, y), setTool,
  openPhoto, setPhotoLayer, closePhoto, photoIn3D, photos: () => EXTRA.photos.map((p) => p.id),
  flyTo, equipment: () => [...document.querySelectorAll('#equip button.eq')].map((b) => b.dataset.name),
  cone: (cam) => { state.cones = true; $('cones-cb').checked = true; showCone(cam); return !!EXTRA.cones[cam]; },
  link: linkHash, copyLink,
  stats: () => ({ items: items.length, visible: items.filter((i) => i.mesh.visible).length, info: renderer.info.render, sheets: sheetGroup.children.length }),
};
