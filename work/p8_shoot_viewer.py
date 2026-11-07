import asyncio, sys, json
from playwright.async_api import async_playwright
HTML = sys.argv[1]; OUTDIR = sys.argv[2]; SHOTS = json.loads(sys.argv[3])
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width':1600,'height':900})
        logs=[]; pg.on('console', lambda m: logs.append(m.type+': '+m.text)); pg.on('pageerror', lambda e: logs.append('ERR '+str(e)))
        reqs=[]; pg.on('request', lambda r: reqs.append(r.url[:60]) if not r.url.startswith(('file:','data:','blob:')) else None)
        await pg.goto('file://'+HTML)
        await pg.wait_for_function('window.__viewer && window.__viewer.ready', timeout=180000)
        for s in SHOTS:
            for js in s.get('js', []): 
                r = await pg.evaluate(js)
                if r is not None: print(s['name'], '->', r)
            await pg.wait_for_timeout(s.get('wait', 2500))
            await pg.screenshot(path=f"{OUTDIR}/{s['name']}.png")
        print('stats', await pg.evaluate('JSON.stringify(window.__viewer.stats())'))
        print('external requests:', reqs); print('\n'.join(logs[:20]))
        await b.close()
asyncio.run(main())
