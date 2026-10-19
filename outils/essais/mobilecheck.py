"""Parcours mobile (iPhone 13) de toutes les fonctions : erreurs JavaScript, débordement horizontal de la page, textes suspects."""
import asyncio, json, re, sys
from playwright.async_api import async_playwright

BASE = sys.argv[1]
OUT = sys.argv[2]
BAD = re.compile(r'\bNaN\b|\bundefined\b|\bInfinity\b|\[object Object\]')


async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch()
        ctx = await br.new_context(**p.devices['iPhone 13'])
        pg = await ctx.new_page()
        errs, cur = [], {'h': None}
        pg.on('pageerror', lambda e: errs.append((cur['h'], str(e)[:300])))
        await pg.goto(BASE + '#MONITOR')
        await pg.wait_for_timeout(3000)
        fns = await pg.evaluate("Object.keys(FN)")
        secfn = await pg.evaluate("[...SECFN]")
        res = {}
        for f in fns:
            for s in (['SNTS', 'AAPL'] if f in secfn else [None]):
                h = f + (('~' + s) if s else '')
                cur['h'] = h
                await pg.evaluate("([f, s]) => go(f, s || undefined)", [f, s])
                await pg.wait_for_timeout(1100)
                r = await pg.evaluate("""() => ({sw: document.documentElement.scrollWidth, iw: window.innerWidth,
                    txt: document.body.innerText.slice(0, 200000)})""")
                bad = [l.strip()[:120] for l in r['txt'].splitlines() if BAD.search(l)]
                res[h] = {'over': r['sw'] - r['iw'], 'bad': bad[:3], 'len': len(r['txt'])}
        json.dump({'pages': res, 'errs': errs}, open(OUT, 'w'), ensure_ascii=False)
        over = {h: v['over'] for h, v in res.items() if v['over'] > 4}
        print('pages', len(res), 'erreurs JS', len(errs), errs[:5])
        print('débordement horizontal', len(over), sorted(over.items(), key=lambda x: -x[1])[:20])
        print('textes suspects', [(h, v['bad']) for h, v in res.items() if v['bad']][:10])
        print('pages vides', [h for h, v in res.items() if v['len'] < 150][:10])
        await br.close()

asyncio.run(main())
