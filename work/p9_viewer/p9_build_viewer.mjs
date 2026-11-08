// Phase 9 viewer build. usage (in a folder with src/main.js, src/template.html and node_modules, see docs/BUILD.md):
//   node p9_build_viewer.mjs <glb> <cameras.json> <viewer_data.json> <out.html>
// Bundles src/main.js (three.js + GLTFLoader + OrbitControls) with esbuild and inlines it, the camera presets,
// the extra data (plan sheets, photos, cones from work/p9_viewer_data.py) and the base64 GLB into src/template.html
// -> one self-contained offline HTML file.
import { build } from 'esbuild';
import fs from 'node:fs';
const [glb, cams, data, out] = process.argv.slice(2);
const r = await build({ entryPoints: ['src/main.js'], bundle: true, minify: true, format: 'iife', target: 'es2020', write: false, legalComments: 'none' });
const js = r.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
const camJson = JSON.stringify(JSON.parse(fs.readFileSync(cams, 'utf8')));
const dataJson = fs.readFileSync(data, 'utf8').replace(/<\//g, '<\\/');
const b64 = fs.readFileSync(glb).toString('base64');
const html = fs.readFileSync('src/template.html', 'utf8')
  .replace('/*CAMS*/', () => camJson).replace('/*DATA*/', () => dataJson).replace('/*GLB*/', () => b64).replace('/*BUNDLE*/', () => js);
fs.writeFileSync(out, html);
console.log('bundle', (js.length / 1024).toFixed(0), 'KB; data', (dataJson.length / 1048576).toFixed(2), 'MB; glb b64', (b64.length / 1048576).toFixed(2), 'MB; html', (html.length / 1048576).toFixed(2), 'MB');
