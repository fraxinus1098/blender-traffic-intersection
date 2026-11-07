// Phase 8 viewer build (cloud container). usage: node p8_build_viewer.mjs <glb> <cameras.json> <out.html>
// Bundles src/main.js (three.js + GLTFLoader + OrbitControls) with esbuild and inlines it, the camera presets
// and the base64 GLB into src/template.html -> one self-contained offline HTML file.
import { build } from 'esbuild';
import fs from 'node:fs';
const [glb, cams, out] = process.argv.slice(2);
const r = await build({ entryPoints: ['src/main.js'], bundle: true, minify: true, format: 'iife', target: 'es2020', write: false, legalComments: 'none' });
const js = r.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
const camJson = JSON.stringify(JSON.parse(fs.readFileSync(cams, 'utf8')));
const b64 = fs.readFileSync(glb).toString('base64');
const html = fs.readFileSync('src/template.html', 'utf8')
  .replace('/*CAMS*/', () => camJson).replace('/*GLB*/', () => b64).replace('/*BUNDLE*/', () => js);
fs.writeFileSync(out, html);
console.log('bundle', (js.length / 1024).toFixed(0), 'KB; glb b64', (b64.length / 1048576).toFixed(2), 'MB; html', (html.length / 1048576).toFixed(2), 'MB');
