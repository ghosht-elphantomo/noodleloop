"""Usage : python3 qlab3all.py ids48.json <adresse du site local> — QLAB, 48 actions × 3 vues (Valorisation) : erreurs JavaScript et textes suspects."""
import asyncio, re, json, sys
from playwright.async_api import async_playwright
BAD = re.compile(r'\bNaN\b|\bundefined\b|\bInfinity\b|\[object Object\]|\bnull\b')
async def main():
    ids = json.load(open(sys.argv[1])); base = sys.argv[2]
    async with async_playwright() as p:
        br = await p.chromium.launch(); pg = await br.new_page(viewport={'width': 1400, 'height': 900})
        errs = []; cur = {'h': None}
        pg.on('pageerror', lambda e: errs.append((cur['h'], str(e)[:300])))
        pg.on('console', lambda m: errs.append((cur['h'], 'console ' + m.text[:200])) if m.type == 'error' and '404' not in m.text else None)
        await pg.goto(base + '#MONITOR'); await pg.wait_for_timeout(2500)
        bad = []; n = 0
        for t in ids:
            for tab, var, subs in (('v', 'QV', ['val', 'risk', 'q']),):
                await pg.evaluate("([t, tab]) => { ST.tab.QLAB = tab; go('QLAB', t); }", [t, tab]); await pg.wait_for_timeout(600)
                for s in subs:
                    cur['h'] = f'{t}/{tab}/{s}'; n += 1
                    await pg.evaluate(f"{var}.sub='{s}'; render()"); await pg.wait_for_timeout(500)
                    txt = await pg.evaluate("document.getElementById('main').innerText")
                    hits = [l.strip()[:140] for l in txt.splitlines() if BAD.search(l)]
                    if hits: bad.append((t, tab, s, hits[:3]))
                    if len(txt) < 200: bad.append((t, tab, s, 'court: ' + txt[:150]))
        await pg.evaluate("ST.tab.QLAB='s'; go('QLAB','SNTS')"); await pg.wait_for_timeout(2500)
        print('pages', n, 'stats:', (await pg.evaluate("document.getElementById('main').innerText.slice(0,80)")).replace('\n', ' | '))
        print('erreurs JS', errs[:10]); print('textes suspects', len(bad)); [print(b) for b in bad[:30]]
        await br.close()
asyncio.run(main())
