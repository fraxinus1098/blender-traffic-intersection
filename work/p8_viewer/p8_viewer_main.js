// SH 249 at Spring Cypress – Phase 8 offline viewer (three.js, bundled by esbuild into one HTML file).
// The GLB is embedded as base64 in <script id="glb-data">; camera presets in <script id="cam-data"> (from work/p8_cameras.json).
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const TINT = { remove: new THREE.Color(0.85, 0.06, 0.05), new: new THREE.Color(0.10, 0.72, 0.14) }; // Phase 7 change view
const TINT_MIX = 0.6;
const SUN_DIR = new THREE.Vector3(0.765, 0.628, 0.142).normalize(); // 15 Apr 2026 10:00 CDT, scene az 100.5°, el 38.9°

const $ = (id) => document.getElementById(id);
const status = (t) => { $('loading').textContent = t; };

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

// ---------- state ----------
const state = { mode: 'proposed', layers: { roadway: true, existing: true, proposed: true, context: true, aerial: true, radar: false } };
const items = []; // {mesh, layer, status, orig: material|material[]}
let root = null, selected = null, boxHelper = null;
const tintCache = new Map();

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

function applyView() {
  const mode = state.mode;
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
  document.querySelectorAll('#modes button').forEach((b) => b.classList.toggle('on', b.dataset.mode === mode));
  $('legend').style.display = mode === 'change' ? 'block' : 'none';
  if (selected && !isShown(selected)) select(null);
}
function isShown(o) { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; }

// ---------- camera presets ----------
const CAMS = JSON.parse($('cam-data').textContent);
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
function goto(name, instant = false) {
  const p = presetPose(name);
  $('views').value = name;
  if (instant) { camera.position.copy(p.pos); controls.target.copy(p.target); camera.fov = p.fov; camera.updateProjectionMatrix(); controls.update(); return; }
  anim = { t0: performance.now(), dur: 900, p0: camera.position.clone(), t0v: controls.target.clone(), f0: camera.fov, p };
}
function stepAnim(now) {
  if (!anim) return;
  let k = Math.min(1, (now - anim.t0) / anim.dur); k = k * k * (3 - 2 * k);
  camera.position.lerpVectors(anim.p0, anim.p.pos, k);
  controls.target.lerpVectors(anim.t0v, anim.p.target, k);
  camera.fov = anim.f0 + (anim.p.fov - anim.f0) * k; camera.updateProjectionMatrix();
  if (k >= 1) anim = null;
}

// ---------- picking ----------
const raycaster = new THREE.Raycaster();
const ndc = new THREE.Vector2();
let down = null;
renderer.domElement.addEventListener('pointerdown', (e) => { down = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5 || !root) return;
  pickAt(e.clientX, e.clientY);
});
function pickAt(x, y) {
  ndc.set((x / window.innerWidth) * 2 - 1, -(y / window.innerHeight) * 2 + 1);
  raycaster.setFromCamera(ndc, camera);
  const hits = raycaster.intersectObject(root, true).filter((h) => isShown(h.object) && layerOf(h.object) !== 'aerial');
  const hit = hits.find((h) => extrasOf(h.object));
  select(hit ? extrasOf(hit.object) : null, hit);
  return hit ? extrasOf(hit.object).name : null;
}
const STATUS_TXT = { remove: 'Existing – to be removed', remain: 'Existing – to remain', new: 'Proposed (new)', context: 'Context', engineering: 'Engineering overlay' };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function select(o, hit) {
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
  info.innerHTML = `<button id="info-x" title="Close">×</button><h3>${esc(o.name.replace(/\.\d+$/, ''))}</h3>` +
    (u.sh249_note ? `<p class="note">${esc(u.sh249_note)}</p>` : '') + `<table>${rows.join('')}</table>`;
  info.style.display = 'block';
  $('info-x').onclick = () => select(null);
}

// ---------- UI ----------
function buildUI() {
  document.querySelectorAll('#modes button').forEach((b) => (b.onclick = () => { state.mode = b.dataset.mode; applyView(); }));
  document.querySelectorAll('#layers input').forEach((cb) => {
    cb.checked = state.layers[cb.dataset.layer];
    cb.onchange = () => { state.layers[cb.dataset.layer] = cb.checked; applyView(); };
  });
  const sel = $('views');
  for (const [group, list] of PRESETS) {
    const g = document.createElement('optgroup'); g.label = group;
    for (const [label, cam] of list) if (CAMS[cam]) { const op = document.createElement('option'); op.value = cam; op.textContent = label; g.appendChild(op); }
    sel.appendChild(g);
  }
  sel.onchange = () => goto(sel.value);
  $('panel-toggle').onclick = () => document.body.classList.toggle('collapsed');
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
  buildUI();
  applyView();
  goto('CAM_Review_Oblique', true);
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
  renderer.render(scene, camera);
});

// test hook
window.__viewer = {
  ready: false,
  setMode: (m) => { state.mode = m; applyView(); },
  setLayer: (k, v) => { state.layers[k] = v; document.querySelector(`#layers input[data-layer="${k}"]`).checked = v; applyView(); },
  goto: (n) => goto(n, true),
  look: (p, t) => { camera.position.set(...p); controls.target.set(...t); controls.update(); },
  pickAt, selectByName: (n) => { const o = root.getObjectByName(n); select(o); return !!o; },
  stats: () => ({ items: items.length, visible: items.filter((i) => i.mesh.visible).length, info: renderer.info.render }),
};
