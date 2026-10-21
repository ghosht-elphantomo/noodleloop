"""Parcours de toutes les fonctions sur plusieurs écrans : erreurs JavaScript, débordement horizontal de la page, textes suspects.

Profils (dans l'ordre) : iPhone 13 (complet, deux titres), puis Android (Pixel 7), iPad (gen 7), petit écran de PC (1 366 × 768),
Mac (1 440 × 900) sur un titre. Moteur : Chromium (celui de Chrome et Edge sur Windows, Mac et Android ; l'iPhone et l'iPad
sont émulés : taille, pointeur tactile, agent). Avec MOBILE_MOTEURS=firefox,webkit (contrôle du matin sur GitHub, navigateurs
installés), le profil iPhone 13 est aussi passé avec WebKit (Safari) et le profil PC avec Firefox.
Résultat : {"pages": {page: {over, bad, len}}, "errs": [...]} pour iPhone 13 (lecture du contrôle), "profils": {nom: idem}."""
import asyncio, json, os, re, sys
from playwright.async_api import async_playwright

BASE = sys.argv[1]
OUT = sys.argv[2]
BAD = re.compile(r'\bNaN\b|\bundefined\b|\bInfinity\b|\[object Object\]')
PROFILS = [("iPhone 13", "iPhone 13", None, ["SNTS", "AAPL"]),
           ("Android (Pixel 7)", "Pixel 7", None, ["SNTS"]),
           ("iPad (gen 7)", "iPad (gen 7)", None, ["SNTS"]),
           ("PC 1366×768", None, {"viewport": {"width": 1366, "height": 768}}, ["SNTS"]),
           ("Mac 1440×900", None, {"viewport": {"width": 1440, "height": 900}}, ["SNTS"])]
MOTEURS = [m.strip() for m in os.environ.get("MOBILE_MOTEURS", "").split(",") if m.strip() in ("firefox", "webkit")]


async def passe(p, br, nom, device, opts, secs):
    ctx = await br.new_context(**(dict(p.devices[device]) if device else {}), **(opts or {}))
    pg = await ctx.new_page()
    errs, cur = [], {'h': None}
    pg.on('pageerror', lambda e: errs.append((cur['h'], str(e)[:300])))
    await pg.goto(BASE + '#MONITOR')
    await pg.wait_for_timeout(3000)
    fns = await pg.evaluate("Object.keys(FN)")
    secfn = await pg.evaluate("[...SECFN]")
    res = {}
    for f in fns:
        for s in (secs if f in secfn else [None]):
            h = f + (('~' + s) if s else '')
            cur['h'] = h
            await pg.evaluate("([f, s]) => go(f, s || undefined)", [f, s])
            await pg.wait_for_timeout(1100)
            r = await pg.evaluate("""() => ({sw: document.documentElement.scrollWidth, iw: window.innerWidth,
                txt: document.body.innerText.slice(0, 200000)})""")
            bad = [l.strip()[:120] for l in r['txt'].splitlines() if BAD.search(l)]
            res[h] = {'over': r['sw'] - r['iw'], 'bad': bad[:3], 'len': len(r['txt'])}
    await ctx.close()
    over = {h: v['over'] for h, v in res.items() if v['over'] > 4}
    print(f'[{nom}] pages', len(res), 'erreurs JS', len(errs), errs[:5])
    print(f'[{nom}] débordement horizontal', len(over), sorted(over.items(), key=lambda x: -x[1])[:20])
    print(f'[{nom}] textes suspects', [(h, v['bad']) for h, v in res.items() if v['bad']][:10])
    print(f'[{nom}] pages vides', [h for h, v in res.items() if v['len'] < 150][:10])
    return {'pages': res, 'errs': errs}


async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch()
        out = {'profils': {}}
        for nom, device, opts, secs in PROFILS:
            try:
                r = await passe(p, br, nom, device, opts, secs)
            except Exception as e:  # noqa: BLE001  (un profil en échec ne retire pas les autres)
                r = {'pages': {}, 'errs': [(nom, f'profil non passé : {type(e).__name__} {str(e)[:200]}')]}
                print(f'[{nom}] profil non passé :', e)
            out['profils'][nom] = r
            if nom == "iPhone 13":
                out['pages'], out['errs'] = r['pages'], r['errs']
            json.dump(out, open(OUT, 'w'), ensure_ascii=False)
        await br.close()
        # autres moteurs (Safari = WebKit, Firefox) quand ils sont installés : iPhone 13 sous WebKit, PC sous Firefox
        for moteur in MOTEURS:
            try:
                b2 = await getattr(p, moteur).launch()
                nom, device, opts, secs = ("Safari (WebKit, iPhone 13)", "iPhone 13", None, ["SNTS"]) if moteur == "webkit" \
                    else ("Firefox (PC 1366×768)", None, {"viewport": {"width": 1366, "height": 768}}, ["SNTS"])
                out['profils'][nom] = await passe(p, b2, nom, device, opts, secs)
                await b2.close()
            except Exception as e:  # noqa: BLE001
                out['profils'][moteur] = {'pages': {}, 'errs': [(moteur, f'moteur non passé : {type(e).__name__} {str(e)[:200]}')]}
                print(f'[{moteur}] moteur non passé :', e)
            json.dump(out, open(OUT, 'w'), ensure_ascii=False)

asyncio.run(main())
