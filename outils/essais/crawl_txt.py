"""Parcourt toutes les fonctions (et leurs onglets) du site local et enregistre tout le texte visible + infobulles + liens sortants."""
import asyncio, json, sys
from playwright.async_api import async_playwright
BASE = sys.argv[1]; OUT = sys.argv[2]
TICKERS = sys.argv[3].split(',') if len(sys.argv) > 3 else ['SNTS', 'SGBC', 'AAPL']
JS_GRAB = """() => {
  const out = {text: document.body.innerText, titles: [], links: [], imgs: []};
  document.querySelectorAll('[title]').forEach(e => out.titles.push(e.getAttribute('title')));
  document.querySelectorAll('a[href]').forEach(a => out.links.push([a.getAttribute('href'), a.innerText.slice(0, 80)]));
  document.querySelectorAll('img[src],iframe[src]').forEach(a => out.imgs.push(a.getAttribute('src').slice(0, 200)));
  return out; }"""
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(); pg = await br.new_page(viewport={'width': 1440, 'height': 900})
        errs = []; reqs = set(); cur = {'h': None}
        pg.on('pageerror', lambda e: errs.append((cur['h'], str(e)[:300])))
        pg.on('request', lambda r: reqs.add(r.url.split('?')[0][:160]))
        await pg.goto(BASE + '#MONITOR'); await pg.wait_for_timeout(3000)
        fns = await pg.evaluate("Object.keys(FN)"); tabs = await pg.evaluate("FN_TABS"); secfn = await pg.evaluate("[...SECFN]")
        res = {}
        for f in fns:
            tl = [t[0] for t in tabs.get(f, [])] or [None]
            for s in (TICKERS if f in secfn else [None]):
                for t in tl:
                    h = f + (('~' + s) if s else '') + (('@' + t) if t else ''); cur['h'] = h
                    await pg.evaluate("([f, s, t]) => { if (t) ST.tab[f] = t; go(f, s || undefined); }", [f, s, t])
                    await pg.wait_for_timeout(1300)
                    res[h] = await pg.evaluate(JS_GRAB)
        json.dump({'pages': res, 'errs': errs, 'reqs': sorted(reqs)}, open(OUT, 'w'), ensure_ascii=False)
        print('pages', len(res), 'erreurs JS', len(errs), 'requêtes', len(reqs))
        await br.close()
asyncio.run(main())
