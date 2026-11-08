"""Phase 9 headless viewer test (from p8_shoot_viewer.py; uses Playwright's bundled Chromium with SwiftShader WebGL).
usage: .venv/bin/python work/p9_shoot_viewer.py <viewer.html> <outdir> '<json list of shots>' [WxH] [hash]
Each shot: {"name": ..., "js": ["window.__viewer....", ...], "wait": ms, "click": [x, y] (optional)}.
Prints the return value of every js call, the viewer stats, every request that is not file:/data:/blob: (must be none)
and the console messages (errors must be none)."""
import asyncio, sys, json, os
from playwright.async_api import async_playwright
HTML = os.path.abspath(sys.argv[1]); OUTDIR = sys.argv[2]; SHOTS = json.loads(sys.argv[3])
W, H = map(int, (sys.argv[4] if len(sys.argv) > 4 else '1600x900').split('x')); HASH = sys.argv[5] if len(sys.argv) > 5 else ''
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        logs = []; pg.on('console', lambda m: logs.append(m.type + ': ' + m.text)); pg.on('pageerror', lambda e: logs.append('ERR ' + str(e)))
        reqs = []; pg.on('request', lambda r: reqs.append(r.url[:80]) if not r.url.startswith(('file:', 'data:', 'blob:')) else None)
        await pg.goto('file://' + HTML + HASH)
        await pg.wait_for_function('window.__viewer && window.__viewer.ready', timeout=300000)
        await pg.wait_for_timeout(1500)
        for s in SHOTS:
            for js in s.get('js', []):
                r = await pg.evaluate(js)
                if r is not None: print(s['name'], '->', json.dumps(r)[:400])
            if 'click' in s: await pg.mouse.click(*s['click'])
            await pg.wait_for_timeout(s.get('wait', 2500))
            await pg.screenshot(path=f"{OUTDIR}/{s['name']}.png")
        print('stats', await pg.evaluate('JSON.stringify(window.__viewer.stats())'))
        print('hash', await pg.evaluate('location.hash'))
        print('external requests:', reqs); print('\n'.join(logs[:30]))
        await b.close()
asyncio.run(main())
