#!/usr/bin/env python3
"""Sources complémentaires (dossier brut écrit par fetch_extra.py) et calculs dérivés du terminal FQT.

ingest(...)   ajoute les titres : ETF, indices US, Nasdaq-100, volatilité CBOE, crypto
derive(...)   écrit eco.json (FRED), fg.json (Fear & Greed US et BRVM), liq.json (liquidité BRVM),
              fa/<ID>.json + fa_index.json (comptes et ratios US/BRVM), ee.json (consensus), per.json
              (valorisation du marché BRVM), uemoa.json (Banque mondiale)
Bibliothèque standard uniquement. Toute source absente est simplement ignorée (la page l'indique).
"""
import bisect, collections, csv, datetime as dt, io, json, math, os, re, statistics

def clean_name(n):
    import re as _re
    n = _re.sub(r"\s*\((DE|The)\)", "", n or "")
    for pat in (r"\s+(Class [A-C] )?(Common|Ordinary) (Stock|Shares)( \(.*\))?$", r"\s+American Depositary Shares.*$", r"\s+New York Registry Shares$", r"\s+Depositary Shares.*$", r"\s+Subordinate Voting Shares$", r"\s+Common Units$"):
        n = _re.sub(pat, "", n)
    return n.strip().rstrip(",")


SECT_FR = {"Technology": "Technologie", "Telecommunications": "Télécoms", "Health Care": "Santé", "Consumer Discretionary": "Conso. discrétionnaire",
           "Consumer Staples": "Conso. de base", "Industrials": "Industrie", "Energy": "Énergie", "Utilities": "Services publics", "Finance": "Finance",
           "Real Estate": "Immobilier", "Basic Materials": "Matériaux", "Miscellaneous": "Divers"}
TAX_BRVM = {"CI": .25, "SN": .30, "BF": .275, "BJ": .30, "ML": .30, "NE": .30, "TG": .27}  # impôt sur les sociétés (taux légal)


def jload(path, default=None):
    try:
        with open(path, encoding="utf8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def jsave(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8") as f:
        json.dump(obj, f, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def r_(v, nd=4):
    return None if v is None or (isinstance(v, float) and not math.isfinite(v)) else round(v, nd)


def i2d(i):
    return dt.date(i // 10000, i // 100 % 100, i % 100)


def d2i(d):
    return d.year * 10000 + d.month * 100 + d.day


def addays(i, n):
    return d2i(i2d(i) + dt.timedelta(days=n))


def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


# ------------------------------------------------------------------ titres
def futures_ok(path):
    """Historique de contrat à terme exploitable : au moins 250 séances et pas de points mensuels."""
    b = jload(path) if path and os.path.exists(path) else None
    if not b or len(b.get("d", [])) < 250:
        return None
    d = b["d"]
    gap = [(dt.date(y // 10000, y // 100 % 100, y % 100) - dt.date(x // 10000, x // 100 % 100, x % 100)).days > 7 for x, y in zip(d, d[1:])]
    if sum(gap) <= 5:
        return b
    k = max(i for i, g in enumerate(gap) if g) + 1  # points mensuels en tête : on garde la partie quotidienne
    if len(d) - k < 250:
        return None
    return {key: (v[k:] if isinstance(v, list) and len(v) == len(d) else v) for key, v in b.items()}


def ingest(extra, add, have, log):
    """Ajoute ETF, indices, Nasdaq-100, CBOE et crypto. Renvoie les métadonnées utiles aux calculs."""
    info = {"ndx": set(), "screener": {}, "ndx_mcap": {}}
    if not extra or not os.path.isdir(extra):
        return info
    meta = jload(os.path.join(extra, "nasdaq_meta.json"), {}) or {}
    scr = meta.get("screener", {}) or {}
    info["screener"] = scr
    for x in meta.get("ndx", []):
        info["ndx"].add(x["s"])
        info["ndx_mcap"][x["s"]] = x.get("mcap")

    def body(sub, sid):
        b = jload(os.path.join(extra, sub, sid + ".json"))
        return b if b and len(b.get("d", [])) > 30 else None
    n0 = [0]
    add0 = add

    def add(*a, **k):  # noqa: F811
        n0[0] += 1
        return add0(*a, **k)
    for e in meta.get("etf", []):
        b = body("nasdaq", e["id"])
        if not b or e["id"] in have:
            continue
        add({"id": e["id"], "tk": f"{e['id']} US", "n": e["n"], "cls": "Equity", "typ": "ETF", "mkt": "US", "grp": e.get("g") or "ETF", "ccy": "USD", "bench": "SPY"},
            b["d"], b["c"], b["o"], b["h"], b["l"], b["v"])
    for e in meta.get("idx", []):
        b = body("nasdaq", e["id"])
        if not b or e["id"] in have:
            continue
        add({"id": e["id"], "tk": f"{e['id']} Index", "n": e["n"], "cls": "Index", "typ": "Index", "mkt": "US", "grp": "Indices US", "ccy": "pts", "bench": "SPX"},
            b["d"], b["c"], b["o"], b["h"], b["l"])
    for s in sorted(info["ndx"]):
        if s in have:
            continue
        b = body("nasdaq", s)
        if not b:
            continue
        sc = scr.get(s, {})
        add({"id": s, "tk": f"{s} US", "n": clean_name(sc.get("n")) or s, "cls": "Equity", "typ": "Equity", "mkt": "US", "grp": SECT_FR.get(sc.get("sector"), sc.get("sector") or "Nasdaq-100"),
             "ind": sc.get("ind"), "ccy": "USD", "bench": "QQQ"}, b["d"], b["c"], b["o"], b["h"], b["l"], b["v"])
    names = {"VIX": "Volatilité implicite S&P 500 (VIX)", "VIX9D": "VIX 9 jours", "VIX3M": "VIX 3 mois", "VVIX": "Volatilité du VIX (VVIX)", "SKEW": "Indice SKEW (risque extrême)"}
    for s, n in names.items():
        p = os.path.join(extra, "cboe", s + ".csv")
        if not os.path.exists(p):
            continue
        rows = {}
        for r in csv.DictReader(open(p, encoding="utf8")):
            try:
                m, d, y = (r.get("DATE") or r.get("Date")).split("/")
                k = int(y) * 10000 + int(m) * 100 + int(d)
                c = float(r.get("CLOSE") or r.get("Close") or r.get(s))
                o = float(r.get("OPEN") or c)
                h = float(r.get("HIGH") or c)
                lo = float(r.get("LOW") or c)
            except Exception:  # noqa: BLE001
                continue
            if c > 0:
                rows[k] = (k, o, max(h, c, o), min(lo, c, o), c)
        rr = [rows[k] for k in sorted(rows)]
        if len(rr) < 100:
            continue
        if s in have:  # VIX des datasets remplacé par la source officielle CBOE
            have.discard(s)
        add({"id": s, "tk": f"{s} Index", "n": n, "cls": "Index", "typ": "Index", "mkt": "MACRO", "grp": "Volatilité", "ccy": "pts", "src": "CBOE"},
            [x[0] for x in rr], [x[4] for x in rr], [x[1] for x in rr], [x[2] for x in rr], [x[3] for x in rr], replace=True)
    # contrats à terme 1er mois : remplacent les prix au comptant des datasets sous les mêmes codes (copie au comptant : BRENTS, WTIS, NGS)
    for sid, tk, n, grp, nd in (("BRENT", "CO1 Comdty", "Pétrole Brent, contrat à terme ICE 1er mois (USD/baril)", "Énergie", 2),
                                ("WTI", "CL1 Comdty", "Pétrole WTI, contrat à terme NYMEX 1er mois (USD/baril)", "Énergie", 2),
                                ("NATGAS", "NG1 Comdty", "Gaz naturel Henry Hub, contrat à terme NYMEX 1er mois (USD/MMBtu)", "Énergie", 3),
                                ("GOLD", "GC1 Comdty", "Or, contrat à terme COMEX 1er mois (USD/once)", "Métaux", 2)):
        b = futures_ok(os.path.join(extra, "futures", sid + ".json"))
        if not b:
            continue
        if sid in have:
            have.discard(sid)
        add({"id": sid, "tk": tk, "n": n, "cls": "Comdty", "typ": "Comdty", "mkt": "MACRO", "grp": grp, "ccy": "USD", "src": "ICE / NYMEX via Yahoo Finance et CNBC"},
            b["d"], b["c"], b["o"], b["h"], b["l"], b["v"], nd=nd, replace=True)
    for sid, n in (("BTC", "Bitcoin"), ("ETH", "Ether"), ("SOL", "Solana")):
        b = body("crypto", sid)
        if not b:
            continue
        add({"id": sid, "tk": "XBTUSD Curncy" if sid == "BTC" else f"{sid}USD Curncy", "n": n + " (USD)", "cls": "Crypto", "typ": "Crypto", "mkt": "CRYPTO", "grp": "Crypto",
             "ccy": "USD", "bench": "BTC"}, b["d"], b["c"], b["o"], b["h"], b["l"], b["v"], ann=365)
    log(f"sources complémentaires : {n0[0]} titres ajoutés")
    return info


# ------------------------------------------------------------------ outils séries
def ffill(dates, vals, grid):
    """Valeur connue à chaque date de la grille (dernière observation antérieure ou égale)."""
    out, j, last = [], 0, None
    for g in grid:
        while j < len(dates) and dates[j] <= g:
            last = vals[j]
            j += 1
        out.append(last)
    return out


def sma_list(x, n):
    out, s, q = [], 0.0, collections.deque()
    for v in x:
        if v is None:
            out.append(None)
            continue
        q.append(v)
        s += v
        if len(q) > n:
            s -= q.popleft()
        out.append(s / n if len(q) == n else None)
    return out


def ema_list(x, n):
    a, out, e = 2 / (n + 1), [], None
    for v in x:
        if v is None:
            out.append(e)
            continue
        e = v if e is None else e + a * (v - e)
        out.append(e)
    return out


def roll_ext(x, n, fn):
    """Maximum (fn=max) ou minimum glissant sur n valeurs, en O(len)."""
    out, q = [], collections.deque()
    better = (lambda a, b: a >= b) if fn is max else (lambda a, b: a <= b)
    for i, v in enumerate(x):
        while q and better(v, x[q[-1]]):
            q.pop()
        q.append(i)
        if q[0] <= i - n:
            q.popleft()
        out.append(x[q[0]] if i >= n - 1 else None)
    return out


def zscore_scores(x, n=252, invert=False, minp=120):
    """Score 0-100 : position de la valeur dans sa propre distribution sur n séances (z-score -> loi normale)."""
    out, q, s, ss = [], collections.deque(), 0.0, 0.0
    for v in x:
        if v is None or not math.isfinite(v):
            out.append(None)
            continue
        q.append(v)
        s += v
        ss += v * v
        if len(q) > n:
            o = q.popleft()
            s -= o
            ss -= o * o
        k = len(q)
        if k < minp:
            out.append(None)
            continue
        mu = s / k
        var = max(ss / k - mu * mu, 1e-18)
        z = (v - mu) / math.sqrt(var)
        z = max(-3.5, min(3.5, z))
        out.append(100 * phi(-z if invert else z))
    return out


def rsi_last(c, n=14):
    out, ag, al = [None] * len(c), None, None
    for i in range(1, len(c)):
        ch = c[i] - c[i - 1]
        g, l_ = max(ch, 0), max(-ch, 0)
        if i <= n:
            ag = (ag or 0) + g / n
            al = (al or 0) + l_ / n
            if i == n:
                out[i] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
            continue
        ag = (ag * (n - 1) + g) / n
        al = (al * (n - 1) + l_) / n
        out[i] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def ret_n(c, n):
    return [None if i < n or not c[i - n] else c[i] / c[i - n] - 1 for i in range(len(c))]


def brvm_breadth(files, ids, grid, shares, W=20):
    """BRVM (titres peu liquides) : part des actions ayant touché un plus haut 52 sem. dans les W dernières séances − part ayant
    touché un plus bas (sans exiger une hausse le jour même : beaucoup de titres ne cotent pas tous les jours) ;
    part de la capitalisation au-dessus de la moyenne 50 séances (la cote est très concentrée : Sonatel et Orange CI)."""
    n = len(grid)
    pos = {g: i for i, g in enumerate(grid)}
    nh, nl, el, a50c, capt, n50 = ([0.0] * n for _ in range(6))
    for sid in ids:
        b = files.get(sid)
        if not b or len(b["c"]) < 60:
            continue
        d, c = b["d"], b["c"]
        mx, mn, s50 = roll_ext(c, 252, max), roll_ext(c, 252, min), sma_list(c, 50)
        sh = shares.get(sid) or 0
        lastH = lastL = -10 ** 9
        for i in range(1, len(c)):
            if mx[i] is not None:
                if c[i] >= mx[i] and c[i] > mn[i]:
                    lastH = i
                if c[i] <= mn[i] and c[i] < mx[i]:
                    lastL = i
            k = pos.get(d[i])
            if k is None:
                continue
            if mx[i] is not None:
                el[k] += 1
                nh[k] += (i - lastH) < W
                nl[k] += (i - lastL) < W
            if s50[i] is not None:
                n50[k] += 1
                if sh:
                    capt[k] += sh * c[i]
                    a50c[k] += sh * c[i] * (c[i] > s50[i])
    return {"nhl": [(nh[i] - nl[i]) / el[i] if el[i] >= 8 else None for i in range(n)],
            "a50c": [a50c[i] / capt[i] if capt[i] > 0 and n50[i] >= 8 else None for i in range(n)]}


def universe_stats(files, ids, grid, want_flux=False):
    """Largeur d'un univers de titres sur la grille de dates : plus hauts/bas 52 sem., part au-dessus de la MM50,
    volume des hausses moins des baisses, RSI > 70 / < 30, flux de capitaux."""
    n = len(grid)
    pos = {g: i for i, g in enumerate(grid)}
    nh, nl, elig, a50, n50, up_v, dn_v, rs_hi, rs_lo, nrs, fl_up, fl_dn, fl_tot = ([0.0] * n for _ in range(13))
    for sid in ids:
        b = files.get(sid)
        if not b or len(b["c"]) < 60:
            continue
        d, c = b["d"], b["c"]
        v = b.get("v") or [0] * len(c)
        val = b.get("val")
        mx, mn, s50, rs = roll_ext(c, 252, max), roll_ext(c, 252, min), sma_list(c, 50), rsi_last(c)
        for i in range(1, len(c)):
            k = pos.get(d[i])
            if k is None:
                continue
            if mx[i] is not None:
                elig[k] += 1
                if c[i] >= mx[i] and c[i] > c[i - 1]:
                    nh[k] += 1
                elif c[i] <= mn[i] and c[i] < c[i - 1]:
                    nl[k] += 1
            if s50[i] is not None:
                n50[k] += 1
                a50[k] += c[i] > s50[i]
            if rs[i] is not None:
                nrs[k] += 1
                rs_hi[k] += rs[i] > 70
                rs_lo[k] += rs[i] < 30
            vol = (v[i] or 0) * c[i] if not val else (val[i] or 0)
            if c[i] > c[i - 1]:
                up_v[k] += vol
            elif c[i] < c[i - 1]:
                dn_v[k] += vol
            fl_tot[k] += vol
    return {"nh": nh, "nl": nl, "elig": elig, "a50": [a50[i] / n50[i] if n50[i] >= 8 else None for i in range(n)],
            "nhl": [(nh[i] - nl[i]) / elig[i] if elig[i] >= 8 else None for i in range(n)],
            "uv": up_v, "dv": dn_v, "tot": fl_tot, "rsi": [(rs_hi[i] - rs_lo[i]) / nrs[i] if nrs[i] >= 8 else None for i in range(n)]}


def compose(comps, grid, need=4):
    out = []
    for i in range(len(grid)):
        v = [c["s"][i] for c in comps.values() if c["s"][i] is not None]
        out.append(sum(v) / len(v) if len(v) >= need else None)
    return out


def label(s):
    return None if s is None else "peur extrême" if s < 25 else "peur" if s < 45 else "neutre" if s <= 55 else "avidité" if s <= 75 else "avidité extrême"


# ------------------------------------------------------------------ FRED
def fred_load(extra):
    meta = jload(os.path.join(extra, "fred_meta.json"), []) or []
    out = {}
    for m in meta:
        p = os.path.join(extra, "fred", m["id"] + ".csv")
        if not os.path.exists(p):
            continue
        d, v = [], []
        rows = list(csv.reader(open(p, encoding="utf8")))
        for r in rows[1:]:
            if len(r) < 2 or r[1].strip() in ("", "."):
                continue
            try:
                v.append(float(r[1]))
                d.append(int(r[0][:10].replace("-", "")))
            except ValueError:
                continue
        if len(d) > 5:
            out[m["id"]] = (m, d, v)
    return out


def freq_of(d):
    if len(d) < 3:
        return "M"
    gaps = sorted((i2d(d[i]) - i2d(d[i - 1])).days for i in range(max(1, len(d) - 60), len(d)))
    g = gaps[len(gaps) // 2]
    return "D" if g <= 3 else "W" if g <= 8 else "M" if g <= 40 else "Q"


def to_weekly(d, v):
    out = {}
    for a, b in zip(d, v):
        t = i2d(a)
        fri = t + dt.timedelta(days=(4 - t.weekday()) % 7)
        out[d2i(fri)] = b
    k = sorted(out)
    return k, [out[x] for x in k]


def eco(extra, out, log):
    F = fred_load(extra)
    if not F:
        return None
    res = {"meta": [], "s": {}}
    for sid, (m, d, v) in F.items():
        f = freq_of(d)
        dd, vv = (to_weekly(d, v) if f == "D" else (d, v))
        last, dl = v[-1], d[-1]
        y1 = None
        for i in range(len(d) - 1, -1, -1):
            if d[i] <= addays(dl, -365):
                y1 = v[i]
                break
        res["meta"].append({"id": sid, "n": m["n"], "g": m["g"], "u": m["u"], "f": f, "last": r_(last, 4), "dl": dl, "prev": r_(v[-2], 4) if len(v) > 1 else None, "y1": r_(y1, 4),
                            "first": d[0]})
        res["s"][sid] = [dd, [r_(x, 4) for x in vv]]
    # récessions NBER
    if "USREC" in F:
        _, d, v = F["USREC"]
        rec, st = [], None
        for a, b in zip(d, v):
            if b >= 1 and st is None:
                st = a
            elif b < 1 and st is not None:
                rec.append([st, a])
                st = None
        if st:
            rec.append([st, d[-1]])
        res["rec"] = rec
    # liquidité nette de la Fed = bilan - compte du Trésor - prises en pension inversées (Md$)
    if all(k in F for k in ("WALCL", "WTREGEN", "RRPONTSYD")):
        w = F["WALCL"]
        g = w[1]
        tg = ffill(F["WTREGEN"][1], F["WTREGEN"][2], g)
        rp = ffill(F["RRPONTSYD"][1], F["RRPONTSYD"][2], g)
        res["s"]["NETLIQ"] = [g, [r_(w[2][i] / 1000 - (tg[i] or 0) - (rp[i] or 0), 1) if tg[i] is not None else None for i in range(len(g))]]
        res["meta"].append({"id": "NETLIQ", "n": "Liquidité nette de la Fed (bilan − TGA − RRP)", "g": "Liquidité", "u": "Md$", "f": "W", "last": res["s"]["NETLIQ"][1][-1], "dl": g[-1]})
    if "BAMLH0A0HYM2" in F and "BAMLC0A0CM" in F:
        a, b = F["BAMLH0A0HYM2"], F["BAMLC0A0CM"]
        g = a[1]
        ib = ffill(b[1], b[2], g)
        dd, vv = to_weekly(g, [a[2][i] - ib[i] if ib[i] is not None else None for i in range(len(g))])
        res["s"]["HYIG"] = [dd, [r_(x, 3) for x in vv]]
        res["meta"].append({"id": "HYIG", "n": "Écart haut rendement − catégorie investissement", "g": "Crédit", "u": "%", "f": "W", "last": res["s"]["HYIG"][1][-1], "dl": dd[-1]})
    # courbe des taux
    ten = [("DGS1MO", "1M", 1 / 12), ("DGS3MO", "3M", .25), ("DGS6MO", "6M", .5), ("DGS1", "1A", 1), ("DGS2", "2A", 2), ("DGS3", "3A", 3), ("DGS5", "5A", 5),
           ("DGS7", "7A", 7), ("DGS10", "10A", 10), ("DGS20", "20A", 20), ("DGS30", "30A", 30)]
    ten = [t for t in ten if t[0] in F]
    if "DGS10" in F and len(ten) >= 6:
        base = [x for x in F["DGS10"][1] if x >= 19900101]
        cols = {t[0]: ffill(F[t[0]][1], F[t[0]][2], base) for t in ten}
        daily = [i for i, x in enumerate(base) if x >= addays(base[-1], -365 * 3)]
        months = []
        for i, x in enumerate(base):
            if i + 1 == len(base) or base[i + 1] // 100 != x // 100:
                months.append(i)
        res["curve"] = {"ten": [t[1] for t in ten], "mat": [t[2] for t in ten],
                        "d": [base[i] for i in daily], "v": [[r_(cols[t[0]][i], 3) for t in ten] for i in daily],
                        "md": [base[i] for i in months], "mv": [[r_(cols[t[0]][i], 3) for t in ten] for i in months]}
    # dates de décision du FOMC publiées par la Fed (relevées chaque jour)
    fo = jload(os.path.join(extra, "fomc.json"), {})
    if fo.get("d"):
        res["fomc"] = fo["d"]
    jsave(os.path.join(out, "eco.json"), res)
    # version légère (sans les historiques) pour les écrans qui n'affichent que les derniers chiffres et la courbe
    jsave(os.path.join(out, "eco_lite.json"), {k: res[k] for k in ("meta", "rec", "curve", "fomc") if k in res})
    log(f"eco.json : {len(res['s'])} séries FRED")
    return F


# ------------------------------------------------------------------ Fear & Greed
def fg(extra, out, files, ndx, us_ids, brvm_ids, dmeta, shares, F, log):
    res = {}
    # ---- États-Unis (méthode CNN : 7 indicateurs, chacun situé dans sa distribution sur un an)
    base_id = "SPX" if "SPX" in files else "SPY" if "SPY" in files else None
    cnn = jload(os.path.join(extra, "cnn_fg.json")) if extra else None
    if base_id:
        B = files[base_id]
        grid = [d for d in B["d"] if d >= 20140101]
        k0 = B["d"].index(grid[0])
        c = B["c"][k0:]
        sma125 = sma_list(B["c"], 125)[k0:]
        comps = {}
        comps["mom"] = {"n": f"Momentum : {base_id} contre sa moyenne 125 séances", "src": "Nasdaq", "raw": [c[i] / sma125[i] - 1 if sma125[i] else None for i in range(len(grid))]}
        uni = sorted((set(ndx) | set(us_ids)) & set(files))
        U = universe_stats(files, uni, grid)
        comps["str"] = {"n": f"Force : plus hauts − plus bas 52 sem. ({len(uni)} actions)", "src": "Nasdaq / Yahoo", "raw": U["nhl"]}
        r = [(U["uv"][i] - U["dv"][i]) / (U["uv"][i] + U["dv"][i]) if U["uv"][i] + U["dv"][i] > 0 else None for i in range(len(grid))]
        osc = [a - b if a is not None and b is not None else None for a, b in zip(ema_list(r, 19), ema_list(r, 39))]
        summ, acc = [], 0.0
        for v in osc:
            acc += v or 0
            summ.append(acc if v is not None else None)
        comps["brd"] = {"n": "Largeur : volume McClellan (hausses − baisses, cumulé)", "src": "Nasdaq / Yahoo", "raw": summ}
        vix = files.get("VIX")
        if vix:
            vs = sma_list(vix["c"], 50)
            vv = [vix["c"][i] / vs[i] - 1 if vs[i] else None for i in range(len(vix["c"]))]
            comps["vix"] = {"n": "Volatilité : VIX contre sa moyenne 50 séances", "src": "CBOE", "inv": True, "raw": ffill(vix["d"], vv, grid)}
        bond = files.get("TLT") or files.get("IEF")
        if bond:
            sr = ret_n(c, 20)
            br = ffill(bond["d"], ret_n(bond["c"], 20), grid)
            comps["sh"] = {"n": "Valeur refuge : actions − obligations du Trésor sur 20 séances", "src": "Nasdaq", "raw": [a - b if a is not None and b is not None else None for a, b in zip(sr, br)]}
        jb = None
        if F and "BAMLH0A0HYM2" in F and "BAMLC0A0CM" in F:
            a, b = F["BAMLH0A0HYM2"], F["BAMLC0A0CM"]
            ib = ffill(b[1], b[2], a[1])
            sp = [x - y if y is not None else None for x, y in zip(a[2], ib)]
            jb = ffill(a[1], sp, grid)
            if sum(1 for x in jb if x is not None) < len(grid) * .6:
                jb = None
        if jb:
            comps["jb"] = {"n": "Obligations à haut rendement : écart HY − IG", "src": "FRED (ICE BofA)", "inv": True, "raw": jb}
        elif files.get("HYG") and files.get("IEF"):
            hr = ffill(files["HYG"]["d"], ret_n(files["HYG"]["c"], 20), grid)
            ir = ffill(files["IEF"]["d"], ret_n(files["IEF"]["c"], 20), grid)
            comps["jb"] = {"n": "Obligations à haut rendement : HYG − IEF sur 20 séances", "src": "Nasdaq", "raw": [a - b if a is not None and b is not None else None for a, b in zip(hr, ir)]}
        if cnn and cnn.get("put_call_options", {}).get("data"):
            pts = sorted((d2i(dt.datetime.utcfromtimestamp(p["x"] / 1000).date()), p["y"]) for p in cnn["put_call_options"]["data"] if p.get("y") is not None)
            if len(pts) > 150:
                comps["pc"] = {"n": "Options : ratio put/call (moyenne 5 jours)", "src": "CNN (CBOE)", "inv": True, "raw": ffill([p[0] for p in pts], [p[1] for p in pts], grid)}
                first = pts[0][0]
                comps["pc"]["raw"] = [v if g >= first else None for v, g in zip(comps["pc"]["raw"], grid)]
        for k, cdef in comps.items():
            cdef["s"] = zscore_scores(cdef["raw"], 252, cdef.get("inv", False))
        score = compose(comps, grid, 4)
        us = {"d": grid, "score": [r_(x, 1) for x in score], "comp": {}}
        for k, cdef in comps.items():
            us["comp"][k] = {"n": cdef["n"], "src": cdef["src"], "inv": cdef.get("inv", False), "raw": [r_(x, 5) for x in cdef["raw"]], "s": [r_(x, 1) for x in cdef["s"]]}
        if cnn and cnn.get("fear_and_greed_historical", {}).get("data"):
            pts = sorted((d2i(dt.datetime.utcfromtimestamp(p["x"] / 1000).date()), p["y"]) for p in cnn["fear_and_greed_historical"]["data"] if p.get("y") is not None)
            us["cnn"] = {"d": [p[0] for p in pts], "v": [r_(p[1], 1) for p in pts]}
            fgn = cnn.get("fear_and_greed", {})
            us["cnn_now"] = {k: fgn.get(k) for k in ("score", "rating", "timestamp", "previous_close", "previous_1_week", "previous_1_month", "previous_1_year")}
            cc = {}
            for k in ("market_momentum_sp500", "stock_price_strength", "stock_price_breadth", "put_call_options", "market_volatility_vix", "junk_bond_demand", "safe_haven_demand"):
                x = cnn.get(k) or {}
                cc[k] = {"score": x.get("score"), "rating": x.get("rating")}
            us["cnn_comp"] = cc
            m = dict(zip(us["cnn"]["d"], us["cnn"]["v"]))
            pairs = [(m[g], s) for g, s in zip(grid, score) if g in m and s is not None]
            if len(pairs) > 60:
                xa, ya = [p[0] for p in pairs], [p[1] for p in pairs]
                us["vs_cnn"] = {"n": len(pairs), "corr": r_(statistics.correlation(xa, ya), 3), "mad": r_(sum(abs(a - b) for a, b in pairs) / len(pairs), 1)}
        res["us"] = us
    # ---- BRVM (méthode identique, indicateurs adaptés à un marché frontière peu liquide)
    if "BRVMC" in files:
        B = files["BRVMC"]
        grid = [d for d in B["d"] if d >= 20090101]
        k0 = B["d"].index(grid[0])
        c = B["c"][k0:]
        sma125 = sma_list(B["c"], 125)[k0:]
        comps = {"mom": {"n": "Momentum : BRVM Composite contre sa moyenne 125 séances", "src": "BRVM", "raw": [c[i] / sma125[i] - 1 if sma125[i] else None for i in range(len(grid))]}}
        mx52 = roll_ext(B["c"], 252, max)[k0:]
        comps["top"] = {"n": "Sommet : BRVM Composite contre son plus haut 52 semaines", "src": "BRVM", "raw": [c[i] / mx52[i] - 1 if mx52[i] else None for i in range(len(grid))]}
        U = universe_stats(files, brvm_ids, grid)
        UB = brvm_breadth(files, brvm_ids, grid, shares)
        comps["str"] = {"n": f"Force : plus hauts − plus bas 52 sem. touchés en 20 séances ({len(brvm_ids)} actions)", "src": "BRVM", "raw": UB["nhl"]}
        comps["brd"] = {"n": "Largeur : part de la capitalisation au-dessus de sa moyenne 50 séances", "src": "BRVM", "raw": UB["a50c"]}
        fl = []
        for i in range(len(grid)):
            a, b = max(0, i - 19), i + 1
            up, dn, tot = sum(U["uv"][a:b]), sum(U["dv"][a:b]), sum(U["tot"][a:b])
            fl.append((up - dn) / tot if tot > 0 and i >= 19 else None)
        comps["flux"] = {"n": "Flux : montants échangés en hausse − en baisse sur 20 séances", "src": "BRVM", "raw": fl}
        # volatilité baissière (semi-écart des seules baisses) : une forte hausse n'est pas un signe de peur
        lr = [math.log(B["c"][i] / B["c"][i - 1]) if i and B["c"][i - 1] > 0 else 0 for i in range(len(B["c"]))]
        dsd = [math.sqrt(sum(min(x, 0) ** 2 for x in lr[i - 19:i + 1]) / 20) if i >= 19 else None for i in range(len(lr))]
        d250 = sma_list(dsd, 250)
        vr = [dsd[i] / d250[i] - 1 if dsd[i] is not None and d250[i] else None for i in range(len(lr))][k0:]
        comps["vol"] = {"n": "Volatilité baissière : 20 séances contre sa moyenne 250 séances", "src": "BRVM", "inv": True, "raw": vr}
        comps["rsi"] = {"n": "Surachat : part RSI > 70 − part RSI < 30", "src": "BRVM", "raw": U["rsi"]}
        # rendement du dividende du marché (12 mois glissants, pondéré par les capitalisations)
        ev = collections.defaultdict(list)
        for x in dmeta:
            dd_ = x.get("det") or x.get("pay")
            if x.get("t") and x.get("dps") and dd_:
                try:
                    ev[x["t"]].append((int(dd_[:10].replace("-", "")), float(x["dps"])))
                except ValueError:
                    pass
        if ev:
            num_ = [0.0] * len(grid)
            den = [0.0] * len(grid)
            for sid in brvm_ids:
                b = files.get(sid)
                sh = shares.get(sid)
                if not b or not sh:
                    continue
                px = ffill(b["d"], b["c"], grid)
                evs = sorted(ev.get(sid, []))
                for i, g in enumerate(grid):
                    if px[i] is None:
                        continue
                    lo = addays(g, -365)
                    dsum = sum(v for d_, v in evs if lo < d_ <= g)
                    num_[i] += sh * dsum
                    den[i] += sh * px[i]
            first = min((d_ for v in ev.values() for d_, _ in v), default=99999999)
            yl = [num_[i] / den[i] if den[i] > 0 and grid[i] >= addays(first, 365) else None for i in range(len(grid))]
            comps["yld"] = {"n": "Valorisation : rendement du dividende du marché (12 mois)", "src": "BRVM (dividendes)", "inv": True, "raw": yl}
        for k, cdef in comps.items():  # marché aux cycles longs (baisse 2016-2020, hausse 2021-2026) : distribution sur 10 ans
            cdef["s"] = zscore_scores(cdef["raw"], 2500, cdef.get("inv", False))
        score = compose(comps, grid, 4)
        res["brvm"] = {"d": grid, "win": 2500, "score": [r_(x, 1) for x in score],
                       "comp": {k: {"n": cd["n"], "src": cd["src"], "inv": cd.get("inv", False), "raw": [r_(x, 5) for x in cd["raw"]], "s": [r_(x, 1) for x in cd["s"]]} for k, cd in comps.items()}}
    if res:
        jsave(os.path.join(out, "fg.json"), res)
        log("fg.json : " + ", ".join(f"{k} {v['score'][-1]}" for k, v in res.items()))


# ------------------------------------------------------------------ liquidité BRVM
def liq(out, files, secs_by, brvm_ids, log):
    rows = []
    for sid in brvm_ids:
        b = files.get(sid)
        s = secs_by.get(sid)
        if not b or not s:
            continue
        c, v = b["c"], b.get("v") or [0] * len(b["c"])
        val = b.get("val") or [x * y for x, y in zip(v, c)]
        n = min(252, len(c) - 1)
        if n < 40:
            continue
        cc, vv, vl = c[-n - 1:], v[-n - 1:], val[-n - 1:]
        traded = [i for i in range(1, n + 1) if (vv[i] or 0) > 0]
        rets = [cc[i] / cc[i - 1] - 1 for i in range(1, n + 1) if cc[i - 1] > 0]
        zero = sum(1 for x in rets if x == 0) / len(rets)
        vals = sorted(vl[i] or 0 for i in range(1, n + 1))
        med = vals[len(vals) // 2]
        am = [abs(cc[i] / cc[i - 1] - 1) / vl[i] for i in traded if vl[i] and vl[i] > 0 and cc[i - 1] > 0]
        dp = [cc[i] - cc[i - 1] for i in range(1, n + 1)]
        cov = sum((dp[i] - statistics.fmean(dp)) * (dp[i - 1] - statistics.fmean(dp)) for i in range(1, len(dp))) / (len(dp) - 1) if len(dp) > 10 else 0
        roll = 2 * math.sqrt(-cov) / statistics.fmean(cc) if cov < 0 else None
        tot = sum(vl[1:])
        mcap = s.get("mcap")
        adv3 = sum(val[-63:]) / 63
        rows.append({"id": sid, "adv3": r_(adv3, 0), "adv1y": r_(tot / n, 0), "med": r_(med, 0), "traded": r_(len(traded) / n, 3), "zero": r_(zero, 3),
                     "amihud": r_(statistics.fmean(am) * 1e8, 4) if am else None, "turn": r_(tot / mcap, 4) if mcap else None,
                     "fturn": r_(tot / (mcap * s["float"] / 100), 4) if mcap and s.get("float") else None, "roll": r_(roll, 4),
                     "cap20": r_(0.2 * med * 20, 0), "d10": r_(10e6 / (0.2 * med), 1) if med > 0 else None, "d50": r_(50e6 / (0.2 * med), 1) if med > 0 else None,
                     "d100": r_(100e6 / (0.2 * med), 1) if med > 0 else None, "d500": r_(500e6 / (0.2 * med), 1) if med > 0 else None})
    # montants échangés sur tout le marché, par mois
    mon = collections.defaultdict(float)
    days = collections.defaultdict(set)
    for sid in brvm_ids:
        b = files.get(sid)
        if not b:
            continue
        val = b.get("val") or []
        for d_, x in zip(b["d"], val):
            if d_ >= 20080101 and x:
                mon[d_ // 100] += x
                days[d_ // 100].add(d_)
    ks = sorted(mon)
    jsave(os.path.join(out, "liq.json"), {"rows": rows, "m": ks, "val": [r_(mon[k], 0) for k in ks], "nd": [len(days[k]) for k in ks]})
    log(f"liq.json : {len(rows)} titres")


# ------------------------------------------------------------------ comptes et ratios
def div0(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def cagr(a, b, years):
    if a is None or b is None or a <= 0 or b <= 0 or years <= 0:
        return None
    return (b / a) ** (1 / years) - 1


def grow(a, b):
    return b / a - 1 if a not in (None, 0) and b is not None and a > 0 else None


def weekly_px(b, since):
    out = {}
    for d_, c in zip(b["d"], b["c"]):
        if d_ < since:
            continue
        t = i2d(d_)
        fri = t + dt.timedelta(days=(4 - t.weekday()) % 7)
        out[d2i(fri)] = c
    k = sorted(out)
    return k, [out[x] for x in k]


_SPLIT_B = [1.5, 2, 3, 4, 5, 6, 7, 8, 10, 15, 20, 25, 30, 40, 50]
SPLIT_C = sorted({1.0} | set(_SPLIT_B) | {a * b for a in _SPLIT_B for b in _SPLIT_B if a * b <= 400} | {1 / x for x in _SPLIT_B})
# sauts d'actions dus à des fusions (pas des divisions) : séries laissées telles quelles
SPLIT_EXCLUDE = {"KDP", "TMUS", "LIN", "FANG"}
# certificats américains (ADR / ADS) : nombre d'actions ordinaires par certificat coté à New York (les dépôts SEC comptent les actions ordinaires)
ADR_RATIO = {"TSM": 5, "PDD": 4}
US_SPL = {}  # fractionnements récents par titre (raw/us_splits.json), chargés par fundamentals()


def split_adjust(sh, q=None, first=None):
    """Actions diluées ramenées à la base actuelle. Les dépôts XBRL mélangent des trimestres retraités après une division d'actions
    et d'autres non : chaque période est comparée à la suivante déjà ajustée ; un écart proche d'un rapport de division
    (2:1, 4:1, 10:1, 4×10, regroupement 1:2…) est corrigé, les autres écarts (émissions, rachats) sont conservés.
    Les trimestres antérieurs à la cotation (introductions, SPAC) ne sont pas ajustés."""
    out, nxt, ev = list(sh), None, []
    for j in range(len(sh) - 1, -1, -1):
        v = sh[j]
        if not v:
            continue
        c = 1.0
        recent = first and first > int((dt.date.today() - dt.timedelta(days=int(365.25 * 9.5))).strftime("%Y%m%d"))
        listed = not (recent and q and q[j] < first + 200)  # historique de cours tronqué ≠ introduction en bourse
        if nxt and listed:
            r = nxt / v
            best = min(SPLIT_C, key=lambda k: abs(math.log(r / k)))
            if best != 1.0 and abs(math.log(r / best)) < math.log(1.08) and abs(math.log(r)) > math.log(1.35):
                c = best
                ev.append((j, round(c, 3)))
        out[j] = v * c
        nxt = out[j]
    return out, ev


def us_company(co, b, s, fx):
    """Ratios d'une société US à partir des faits XBRL (TTM trimestriels + exercices annuels)."""
    q = [int(x.replace("-", "")) for x in co["q"]]
    T, Bs = co.get("ttm", {}), co.get("bs", {})
    n = len(q)
    if n == 0:
        return None
    g = lambda blk, k, i: (blk.get(k) or [None] * n)[i] if 0 <= i < n else None  # noqa: E731
    shd = co.get("shd") or [None] * n
    if co.get("t") not in SPLIT_EXCLUDE and (s or {}).get("id") not in SPLIT_EXCLUDE:
        shd, _ev = split_adjust(shd, q, (b or {}).get("d", [None])[0] if b else None)

    def gp(i):
        v = g(T, "gp", i)
        if v is None and g(T, "rev", i) is not None and g(T, "cogs", i) is not None:
            v = g(T, "rev", i) - g(T, "cogs", i)
        return v

    def debt(i):
        ltd = g(Bs, "ltd", i)
        cp, stb = g(Bs, "cp", i) or 0, g(Bs, "stb", i) or 0
        if ltd is not None:
            return ltd + cp + stb
        a, c_ = g(Bs, "ltdnc", i), g(Bs, "dcur", i)
        if a is None and c_ is None and not cp and not stb:
            return None
        return (a or 0) + (c_ or 0) + cp + stb

    def cash(i):
        a, b_ = g(Bs, "cash", i), g(Bs, "sti", i)
        return None if a is None and b_ is None else (a or 0) + (b_ or 0)

    def sh(i):
        for j in range(i, max(-1, i - 3), -1):
            if j >= 0 and shd[j]:
                return shd[j]
        return co["sho"][1] if co.get("sho") else None
    L = n - 1
    while L > 0 and g(T, "rev", L) is None and g(T, "ni", L) is None:
        L -= 1
    P = L - 4 if L >= 4 else None
    k_fx = fx.get(co.get("ccy") or "USD")  # unités de la devise des comptes pour 1 dollar
    price = b["c"][-1] if b else None
    # nombre de titres actuel : le plus récent entre la page de garde du dépôt (dei) et la moyenne diluée du dernier trimestre,
    # ramené aux fractionnements intervenus depuis (le cours coté en tient déjà compte), puis en certificats pour les ADR
    cand = []
    if co.get("sho") and co["sho"][1]:
        cand.append((int(str(co["sho"][0]).replace("-", "")), co["sho"][1]))
    if sh(L):
        cand.append((q[L], sh(L)))
    shares = None
    if cand:
        d0, shares = max(cand)
        if (s or {}).get("id") not in SPLIT_EXCLUDE:
            for d_, r_ in US_SPL.get(co.get("t") or (s or {}).get("id"), []):
                if int(d_.replace("-", "")) > d0 and r_ > 0:
                    shares *= r_
        shares /= ADR_RATIO.get(co.get("t") or (s or {}).get("id"), 1)
    mcap_usd = price * shares if price and shares else None
    mcap = mcap_usd * k_fx if mcap_usd and k_fx else None  # dans la devise des comptes (ratios homogènes)
    if s is not None and mcap_usd:
        s["mcap"] = round(mcap_usd)  # même capitalisation partout (en-tête, DES, US, RV, SCREN)

    def m(i):  # mesures TTM au trimestre i
        if i is None or i < 0:
            return {}
        rev, ni, ocf, cap = g(T, "rev", i), g(T, "ni", i), g(T, "ocf", i), g(T, "capex", i)
        opi, da = g(T, "opi", i), g(T, "da", i)
        fcf = ocf - (cap or 0) if ocf is not None else None
        ebitda = opi + da if opi is not None and da is not None else None
        pti, tax = g(T, "pti", i), g(T, "tax", i)
        t = div0(tax, pti)
        t = min(.35, max(0, t)) if t is not None and pti and pti > 0 else .21
        eq, assets, dbt, csh = g(Bs, "eq", i), g(Bs, "assets", i), debt(i), cash(i)
        ic = (dbt or 0) + eq - (csh or 0) if eq is not None else None
        return {"rev": rev, "gp": gp(i), "opi": opi, "ebitda": ebitda, "ni": ni, "ocf": ocf, "capex": cap, "fcf": fcf, "sbc": g(T, "sbc", i), "rnd": g(T, "rnd", i),
                "div": g(T, "div", i), "buy": g(T, "buy", i), "int": g(T, "int", i), "tax_rate": t, "nopat": opi * (1 - t) if opi is not None else None,
                "eq": eq, "assets": assets, "debt": dbt, "cash": csh, "nd": (dbt or 0) - (csh or 0) if dbt is not None or csh is not None else None, "ic": ic,
                "ca": g(Bs, "ca", i), "cl": g(Bs, "cl", i), "liab": g(Bs, "liab", i), "re": g(Bs, "re", i), "ltd": g(Bs, "ltd", i) or g(Bs, "ltdnc", i), "sh": sh(i),
                "eps": div0(ni, sh(i))}
    now, ago = m(L), m(P)
    avg = lambda k: (now.get(k) + ago[k]) / 2 if now.get(k) is not None and ago.get(k) is not None else now.get(k)  # noqa: E731
    rev, ni, fcf, ocf = now.get("rev"), now.get("ni"), now.get("fcf"), now.get("ocf")
    ev = mcap + (now.get("debt") or 0) - (now.get("cash") or 0) if mcap else None
    r = {"src": "SEC EDGAR (XBRL)", "ccy": co.get("ccy"), "annual_only": co.get("annual_only"), "asof_q": q[L], "mcap": mcap, "mcap_usd": mcap_usd, "ev": ev, "price": price,
         "pe": div0(mcap, ni) if ni and ni > 0 else None, "ps": div0(mcap, rev), "pb": div0(mcap, now.get("eq")) if (now.get("eq") or 0) > 0 else None,
         "ev_ebitda": div0(ev, now.get("ebitda")) if (now.get("ebitda") or 0) > 0 else None, "ev_sales": div0(ev, rev), "ev_ebit": div0(ev, now.get("opi")) if (now.get("opi") or 0) > 0 else None,
         "fcfy": div0(fcf, mcap), "fcfy_sbc": div0(fcf - (now.get("sbc") or 0), mcap) if fcf is not None else None, "ey": div0(now.get("opi"), ev),
         "dy": div0(now.get("div"), mcap), "by": div0(now.get("buy"), mcap), "shy": div0((now.get("div") or 0) + (now.get("buy") or 0), mcap),
         "gm": div0(now.get("gp"), rev), "om": div0(now.get("opi"), rev), "nm": div0(ni, rev), "fcfm": div0(fcf, rev), "ebitdam": div0(now.get("ebitda"), rev),
         "capex_s": div0(now.get("capex"), rev), "sbc_s": div0(now.get("sbc"), rev), "rnd_s": div0(now.get("rnd"), rev),
         "roe": div0(ni, avg("eq")) if (avg("eq") or 0) > 0 else None, "roa": div0(ni, avg("assets")), "roic": div0(now.get("nopat"), avg("ic")) if (avg("ic") or 0) > 0 else None,
         "conv": div0(fcf, ni) if ni and ni > 0 else None, "tax": now.get("tax_rate"),
         "rev_g": grow(ago.get("rev"), rev), "ni_g": grow(ago.get("ni"), ni), "fcf_g": grow(ago.get("fcf"), fcf), "eps_g": grow(ago.get("eps"), now.get("eps")),
         "ocf_g": grow(ago.get("ocf"), ocf), "sh_chg": grow(ago.get("sh"), now.get("sh")),
         "nd": now.get("nd"), "nd_ebitda": div0(now.get("nd"), now.get("ebitda")) if (now.get("ebitda") or 0) > 0 else None, "de": div0(now.get("debt"), now.get("eq")) if (now.get("eq") or 0) > 0 else None,
         "cur": div0(now.get("ca"), now.get("cl")), "icov": div0(now.get("opi"), now.get("int")) if (now.get("int") or 0) > 0 else None,
         "payout": div0(now.get("div"), ni) if ni and ni > 0 else None, "fpay": div0(now.get("div"), fcf) if fcf and fcf > 0 else None,
         "accr": div0((ni or 0) - (ocf or 0), avg("assets")) if ni is not None and ocf is not None else None,
         "gpa": div0(now.get("gp"), avg("assets")), "om_chg": None, "nd_chg": grow(ago.get("nd"), now.get("nd")) if (ago.get("nd") or 0) > 0 else None}
    if r["om"] is not None and ago.get("rev") and ago.get("opi") is not None:
        r["om_chg"] = r["om"] - ago["opi"] / ago["rev"]
    if r["rev_g"] is not None and r["fcfm"] is not None:
        r["r40"] = r["rev_g"] + r["fcfm"]
    # Piotroski (TTM contre TTM un an plus tôt)
    if ago:
        crit = []
        roa1, roa0 = div0(ni, now.get("assets")), div0(ago.get("ni"), ago.get("assets"))
        crit.append(roa1 > 0 if roa1 is not None else None)
        crit.append(ocf > 0 if ocf is not None else None)
        crit.append(roa1 > roa0 if roa1 is not None and roa0 is not None else None)
        crit.append(ocf > ni if ocf is not None and ni is not None else None)
        l1, l0 = div0(now.get("ltd"), now.get("assets")), div0(ago.get("ltd"), ago.get("assets"))
        crit.append(l1 <= l0 if l1 is not None and l0 is not None else None)
        c1, c0 = div0(now.get("ca"), now.get("cl")), div0(ago.get("ca"), ago.get("cl"))
        crit.append(c1 > c0 if c1 is not None and c0 is not None else None)
        crit.append(now["sh"] <= ago["sh"] * 1.005 if now.get("sh") and ago.get("sh") else None)
        g1, g0 = div0(now.get("gp"), rev), div0(ago.get("gp"), ago.get("rev"))
        crit.append(g1 > g0 if g1 is not None and g0 is not None else None)
        t1, t0 = div0(rev, now.get("assets")), div0(ago.get("rev"), ago.get("assets"))
        crit.append(t1 > t0 if t1 is not None and t0 is not None else None)
        known = [x for x in crit if x is not None]
        r["fscore"], r["fscore_n"], r["fcrit"] = sum(known), len(known), [None if x is None else int(x) for x in crit]
    ta, liab = now.get("assets"), now.get("liab") or ((now.get("assets") or 0) - (now.get("eq") or 0) if now.get("assets") else None)
    if ta and now.get("ca") is not None and now.get("cl") is not None and now.get("re") is not None and now.get("opi") is not None and rev and mcap and liab:
        r["altz"] = 1.2 * (now["ca"] - now["cl"]) / ta + 1.4 * now["re"] / ta + 3.3 * now["opi"] / ta + 0.6 * mcap / liab + 1.0 * rev / ta
    # séries trimestrielles (TTM)
    H = {"q": q}
    for k in ("rev", "gp", "opi", "ebitda", "ni", "ocf", "capex", "fcf", "sbc", "div", "buy", "eq", "debt", "cash", "nd", "eps", "sh", "ic", "nopat", "assets"):
        H[k] = []
    for i in range(n):
        mi = m(i)
        for k in list(H):
            if k != "q":
                H[k].append(mi.get(k))
    H["roe"] = [div0(H["ni"][i], H["eq"][i]) if (H["eq"][i] or 0) > 0 else None for i in range(n)]
    H["roic"] = [div0(H["nopat"][i], H["ic"][i]) if (H["ic"][i] or 0) > 0 else None for i in range(n)]
    # exercices annuels
    A, Ab = co.get("a", {}), co.get("abs", {})
    ya = [int(x.replace("-", "")) for x in co.get("y", [])]
    na = len(ya)
    ga = lambda blk, k, i: (blk.get(k) or [None] * na)[i]  # noqa: E731
    Y = {"y": ya}
    for k in ("rev", "gp", "opi", "ni", "ocf", "capex", "sbc", "div", "buy", "da", "int", "rnd"):
        Y[k] = [ga(A, k, i) for i in range(na)]
    Y["gp"] = [Y["gp"][i] if Y["gp"][i] is not None else (Y["rev"][i] - ga(A, "cogs", i) if Y["rev"][i] is not None and ga(A, "cogs", i) is not None else None) for i in range(na)]
    Y["ebitda"] = [Y["opi"][i] + Y["da"][i] if Y["opi"][i] is not None and Y["da"][i] is not None else None for i in range(na)]
    Y["fcf"] = [Y["ocf"][i] - (Y["capex"][i] or 0) if Y["ocf"][i] is not None else None for i in range(na)]
    shm = {q[i]: shd[i] for i in range(n) if shd[i]}
    Y["sh"] = [shm.get(ya[i]) or next((shm[k] for k in sorted(shm, reverse=True) if abs((i2d(k) - i2d(ya[i])).days) < 20), None) for i in range(na)]
    Y["eps"] = [div0(Y["ni"][i], Y["sh"][i]) for i in range(na)]
    for k in ("eq", "assets", "cash", "sti", "ltd", "ltdnc", "dcur", "cp", "stb"):
        Y["b_" + k] = [ga(Ab, k, i) for i in range(na)]
    Y["debt"] = [(Y["b_ltd"][i] + (Y["b_cp"][i] or 0) + (Y["b_stb"][i] or 0)) if Y["b_ltd"][i] is not None else
                 ((Y["b_ltdnc"][i] or 0) + (Y["b_dcur"][i] or 0) + (Y["b_cp"][i] or 0) if Y["b_ltdnc"][i] is not None or Y["b_dcur"][i] is not None else None) for i in range(na)]
    Y["cashx"] = [(Y["b_cash"][i] or 0) + (Y["b_sti"][i] or 0) if Y["b_cash"][i] is not None else None for i in range(na)]
    Y["nd"] = [Y["debt"][i] - Y["cashx"][i] if Y["debt"][i] is not None and Y["cashx"][i] is not None else None for i in range(na)]
    Y["eq"], Y["assets"] = Y["b_eq"], Y["b_assets"]
    for k in [k for k in Y if k.startswith("b_")]:
        del Y[k]
    Y["roe"] = [div0(Y["ni"][i], Y["eq"][i]) if (Y["eq"][i] or 0) > 0 else None for i in range(na)]
    Y["roic"] = [div0(Y["opi"][i] * (1 - .21), (Y["debt"][i] or 0) + Y["eq"][i] - (Y["cashx"][i] or 0)) if Y["opi"][i] is not None and Y["eq"][i] and ((Y["debt"][i] or 0) + Y["eq"][i] - (Y["cashx"][i] or 0)) > 0 else None for i in range(na)]
    for key, nm in (("rev", "rev"), ("ni", "ni"), ("fcf", "fcf"), ("eps", "eps"), ("ocf", "ocf")):
        vals = Y[nm]
        for yrs in (3, 5, 10):
            if na > yrs:
                r[f"{key}_cagr{yrs}"] = cagr(vals[-1 - yrs], vals[-1], yrs)
    # multiples historiques (hebdomadaires) : cours du vendredi / dernier TTM publié (trimestre clos + 45 jours)
    if b and mcap:
        wd, wc = weekly_px(b, 20140101)
        avail = [addays(x, 45) for x in q]
        pe, ps, pb, eve, fy = [], [], [], [], []
        for d_, c_ in zip(wd, wc):
            j = bisect.bisect_right(avail, d_) - 1
            if j < 0:
                pe.append(None); ps.append(None); pb.append(None); eve.append(None); fy.append(None)  # noqa: E702
                continue
            mi = m(j)
            mc = c_ * (mi.get("sh") or shares) / (k_fx or 1)
            e = mc + (mi.get("debt") or 0) - (mi.get("cash") or 0)
            pe.append(div0(mc, mi.get("ni")) if (mi.get("ni") or 0) > 0 else None)
            ps.append(div0(mc, mi.get("rev")))
            pb.append(div0(mc, mi.get("eq")) if (mi.get("eq") or 0) > 0 else None)
            eve.append(div0(e, mi.get("ebitda")) if (mi.get("ebitda") or 0) > 0 else None)
            fy.append(div0(mi.get("fcf"), mc))
        r["mh"] = {"d": wd, "pe": pe, "ps": ps, "pb": pb, "ev_ebitda": eve, "fcfy": fy}
    # exercices seulement : certains dépôts étiquettent des cumuls trimestriels comme annuels (AMZN, CDNS…) ;
    # on garde les dates du mois de clôture (celui où le CA annuel est publié)
    if Y.get("y"):
        from collections import Counter
        mo = Counter(str(y)[4:6] for y, v in zip(Y["y"], Y.get("rev") or []) if v is not None) or Counter(str(y)[4:6] for y in Y["y"])
        fm = mo.most_common(1)[0][0]
        keep = [i for i, y in enumerate(Y["y"]) if str(y)[4:6] == fm or abs(int(str(y)[4:6]) - int(fm)) == 1 and str(y)[6:8] in ("01", "02", "03", "04", "05", "06") and False]
        seen, keep2 = set(), []
        for i in reversed(keep):
            yy = str(Y["y"][i])[:4]
            if yy not in seen:
                seen.add(yy)
                keep2.append(i)
        keep2.sort()
        if len(keep2) < len(Y["y"]):
            Y = {k: ([v[i] for i in keep2] if isinstance(v, list) and len(v) == len(Y["y"]) else v) for k, v in Y.items()}
    r["H"], r["Y"] = H, Y
    return r


# ---------------------------------------------------------------- comptes détaillés et ratios (états financiers publiés à la BRVM)
CPT_ROWS = {  # postes présentés, dans l'ordre des états (clé, libellé)
    "is": [("chiffre_affaires", "Chiffre d’affaires"), ("ventes_marchandises", "Ventes de marchandises"), ("marge_commerciale", "Marge commerciale"),
           ("ventes_produits", "Ventes de produits fabriqués"), ("travaux_services", "Travaux, services vendus"), ("produits_accessoires", "Produits accessoires"),
           ("valeur_ajoutee", "Valeur ajoutée"), ("charges_personnel", "Charges de personnel"), ("ebe", "Excédent brut d’exploitation"),
           ("dotations", "Dotations aux amortissements et provisions"), ("resultat_exploitation", "Résultat d’exploitation"),
           ("revenus_financiers", "Revenus financiers"), ("frais_financiers", "Frais financiers"), ("resultat_financier", "Résultat financier"),
           ("rao", "Résultat des activités ordinaires"), ("rhao", "Résultat hors activités ordinaires"), ("participation", "Participation des travailleurs"),
           ("resultat_avant_impot", "Résultat avant impôt"), ("quote_part_mee", "Quote-part des sociétés mises en équivalence"),
           ("impots_resultat", "Impôts sur le résultat"), ("resultat_net", "Résultat net"), ("resultat_net_pg", "Résultat net part du groupe")],
    "bis": [("b_interets_produits", "Intérêts et produits assimilés"), ("b_interets_charges", "Intérêts et charges assimilées"),
            ("b_commissions_produits", "Commissions (produits)"), ("b_commissions_charges", "Commissions (charges)"), ("b_pnb", "Produit net bancaire"),
            ("b_charges_generales", "Charges générales d’exploitation"), ("dotations", "Dotations aux amortissements"), ("b_rbe", "Résultat brut d’exploitation"),
            ("b_cout_risque", "Coût du risque"), ("resultat_exploitation", "Résultat d’exploitation"), ("resultat_avant_impot", "Résultat avant impôt"),
            ("impots_resultat", "Impôts sur les bénéfices"), ("resultat_net", "Résultat net")],
    "bs": [("charges_immobilisees", "Charges immobilisées"), ("immo_incorp", "Immobilisations incorporelles"), ("immo_corp", "Immobilisations corporelles"),
           ("immo_fin", "Immobilisations financières"), ("actif_immobilise", "Actif immobilisé"), ("actif_non_courant", "Actifs non courants"),
           ("actif_circulant_hao", "Actif circulant HAO"), ("stocks", "Stocks"), ("creances", "Créances et emplois assimilés"), ("clients", "Clients"),
           ("actif_circulant", "Actif circulant"), ("tresorerie_actif", "Trésorerie actif"), ("actif_courant", "Actifs courants"), ("total_actif", "Total actif"),
           ("capital", "Capital"), ("primes_capital", "Primes liées au capital"), ("primes_reserves", "Primes et réserves"), ("ecart_reevaluation", "Écarts de réévaluation"),
           ("reserves", "Réserves"), ("reserves_indisponibles", "Réserves indisponibles"), ("reserves_libres", "Réserves libres"), ("report_nouveau", "Report à nouveau"),
           ("resultat_bilan", "Résultat de l’exercice"), ("autres_cp", "Autres capitaux propres"), ("subventions", "Subventions d’investissement"),
           ("provisions_reglementees", "Provisions réglementées"), ("capitaux_propres", "Capitaux propres"), ("cp_groupe", "dont part du groupe"),
           ("interets_minoritaires", "Intérêts minoritaires"), ("dettes_financieres", "Dettes financières"), ("ressources_stables", "Ressources stables"),
           ("passif_non_courant", "Passifs non courants"), ("dettes_circulantes_hao", "Dettes circulantes HAO"), ("clients_avances", "Clients, avances reçues"),
           ("fournisseurs", "Fournisseurs"), ("dettes_fiscales_sociales", "Dettes fiscales et sociales"), ("dettes_sociales", "Dettes sociales"),
           ("autres_dettes", "Autres dettes"), ("provisions_risques_ct", "Provisions pour risques à court terme"),
           ("autres_passifs_circulants", "Autres passifs circulants"), ("passif_circulant", "Passif circulant"),
           ("passif_courant", "Passifs courants"), ("tresorerie_passif", "Trésorerie passif"), ("ecart_conversion_passif", "Écart de conversion passif"),
           ("total_passif", "Total passif")],
    "bbs": [("b_caisse", "Caisse, banque centrale"), ("b_effets_publics", "Effets publics"), ("b_creances_interbancaires", "Créances interbancaires"),
            ("b_creances_clientele", "Créances sur la clientèle"), ("b_titres_placement", "Titres de placement"), ("immo_corp", "Immobilisations corporelles"),
            ("total_actif", "Total actif"), ("b_dettes_interbancaires", "Dettes interbancaires"), ("b_dettes_clientele", "Dettes envers la clientèle"),
            ("capital", "Capital"), ("b_capital", "Capital"), ("reserves", "Réserves"), ("resultat_bilan", "Résultat de l’exercice"),
            ("capitaux_propres", "Capitaux propres"), ("cp_groupe", "dont part du groupe"), ("interets_minoritaires", "Intérêts minoritaires"),
            ("total_passif", "Total passif")],
    "cf": [("cafg", "Capacité d’autofinancement globale"), ("flux_operationnels", "Flux des activités opérationnelles"),
           ("capex_incorp", "Acquisitions d’immobilisations incorporelles"), ("capex_corp", "Acquisitions d’immobilisations corporelles"),
           ("flux_investissement", "Flux des activités d’investissement"), ("dividendes_verses", "Dividendes versés"),
           ("flux_financement", "Flux des activités de financement"), ("variation_tresorerie", "Variation de la trésorerie"),
           ("tresorerie_fin", "Trésorerie nette à la clôture")],
}


def brvm_ratios(cc, bank, eps_y, dps_y, px_y):
    """Une centaine de ratios par exercice, calculés à partir des seuls postes publiés (et vérifiés) des états financiers,
    du BNPA et du dividende publiés, et du dernier cours de l'exercice. Aucun ratio n'est calculé quand un poste manque.
    Renvoie (années, [[groupe, [[clé, libellé, format, [valeurs]]]]]) ; formats : p (part), x (multiple), j (jours), m (millions), e (FCFA)."""
    Ys = sorted(int(y) for y in (cc.get("y") or {}))
    if not Ys:
        return [], []
    V = {y: (cc["y"].get(y) or cc["y"].get(str(y)) or {}).get("v", {}) for y in Ys}

    def g(k, y):
        v_ = V.get(y, {})
        if k == "resultat_net" and v_.get(k) is None:
            return v_.get("resultat_bilan")  # (résultat de l'exercice au bilan : même montant publié)
        return v_.get(k)

    def ratio(a, b_, pos=False):
        if a is None or b_ in (None, 0):
            return None
        if pos and b_ <= 0:
            return None
        return a / b_

    def avg(k, y):
        a, b_ = g(k, y), g(k, y - 1)
        return (a + b_) / 2 if a is not None and b_ is not None else None

    def sub(*ks, y=None):
        vals = [g(k, y) for k in ks]
        return None if any(v is None for v in vals) else vals[0] - sum(vals[1:])

    def summ(*ks, y=None, need=1):
        vals = [g(k, y) for k in ks if g(k, y) is not None]
        return sum(vals) if len(vals) >= need else None
    def grow_(k, y):  # croissance non significative quand un des deux exercices est négatif ou nul
        a_, b_ = g(k, y - 1), g(k, y)
        return b_ / a_ - 1 if a_ is not None and b_ is not None and a_ > 0 and b_ >= 0 else None
    ca = (lambda y: g("b_pnb", y)) if bank else (lambda y: g("chiffre_affaires", y))
    absn = lambda v: abs(v) if v is not None else None  # noqa: E731

    def taux_impot(y):
        imp, rn = absn(g("impots_resultat", y)), g("resultat_net", y)
        base = (rn + imp + (absn(g("participation", y)) or 0)) if rn is not None and imp is not None else None
        r_ = ratio(imp, base, True)
        return r_ if r_ is not None and 0 <= r_ <= 1 else None  # résultat avant impôt nul ou négatif : taux non significatif

    def dette_nette(y):
        d_, ta, tp = g("dettes_financieres", y), g("tresorerie_actif", y), g("tresorerie_passif", y)
        return d_ + tp - ta if None not in (d_, ta, tp) else None

    def capex(y):
        a, b_ = g("capex_corp", y), g("capex_incorp", y)
        return (abs(a or 0) + abs(b_ or 0)) if (a is not None or b_ is not None) else None

    def fcf(y):
        fo, cx = g("flux_operationnels", y), capex(y)
        return fo - cx if fo is not None and cx is not None else None

    def per_share(y):
        return eps_y.get(y), dps_y.get(y), px_y.get(y)

    def cdr(y):  # coût du risque compté positivement quand c'est une charge (signe lu d'après RBE ± coût du risque = résultat d'exploitation)
        cr_, rbe_, re_ = g("b_cout_risque", y), g("b_rbe", y), g("resultat_exploitation", y)
        if cr_ is None:
            return None
        if rbe_ is not None and re_ is not None:
            if abs(rbe_ + cr_ - re_) <= max(1.0, abs(re_) * .002):
                return -cr_
            if abs(rbe_ - cr_ - re_) <= max(1.0, abs(re_) * .002):
                return cr_
        return None
    R = []
    if bank:
        R.append(["Croissance", [
            ["g_pnb", "Produit net bancaire", "p", [grow_("b_pnb", y) for y in Ys]],
            ["g_rn", "Résultat net", "p", [grow_("resultat_net", y) for y in Ys]],
            ["g_ta", "Total bilan", "p", [grow_("total_actif", y) for y in Ys]],
            ["g_dep", "Dépôts de la clientèle", "p", [grow_("b_dettes_clientele", y) for y in Ys]],
            ["g_cred", "Crédits à la clientèle", "p", [grow_("b_creances_clientele", y) for y in Ys]],
            ["g_cp", "Capitaux propres", "p", [grow_("capitaux_propres", y) for y in Ys]]]])
        R.append(["Exploitation", [
            ["cir", "Coefficient d’exploitation (charges générales + dotations / PNB)", "p",
             [ratio(summ("b_charges_generales", "dotations", y=y, need=2) if g("dotations", y) is not None else None, ca(y), True) for y in Ys]],
            ["cir0", "Charges générales / PNB", "p", [ratio(absn(g("b_charges_generales", y)), ca(y), True) for y in Ys]],
            ["rbe_pnb", "Résultat brut d’exploitation / PNB", "p", [ratio(g("b_rbe", y), ca(y), True) for y in Ys]],
            ["cr_pnb", "Coût du risque / PNB", "p", [ratio(cdr(y), ca(y), True) for y in Ys]],
            ["re_pnb", "Résultat d’exploitation / PNB", "p", [ratio(g("resultat_exploitation", y), ca(y), True) for y in Ys]],
            ["rn_pnb", "Résultat net / PNB", "p", [ratio(g("resultat_net", y), ca(y), True) for y in Ys]],
            ["int_pnb", "Marge d’intérêts / PNB", "p", [ratio(sub("b_interets_produits", "b_interets_charges", y=y) if g("b_interets_charges", y) is not None else None, ca(y), True) for y in Ys]],
            ["com_pnb", "Commissions nettes / PNB", "p", [ratio(sub("b_commissions_produits", "b_commissions_charges", y=y), ca(y), True) for y in Ys]],
            ["tax", "Taux d’impôt effectif", "p", [taux_impot(y) for y in Ys]]]])
        R.append(["Rentabilité", [
            ["roe", "ROE (résultat net / capitaux propres)", "p", [ratio(g("resultat_net", y), g("capitaux_propres", y), True) for y in Ys]],
            ["roe_m", "ROE sur capitaux propres moyens", "p", [ratio(g("resultat_net", y), avg("capitaux_propres", y), True) for y in Ys]],
            ["roa", "ROA (résultat net / total bilan)", "p", [ratio(g("resultat_net", y), g("total_actif", y), True) for y in Ys]],
            ["roa_m", "ROA sur total bilan moyen", "p", [ratio(g("resultat_net", y), avg("total_actif", y), True) for y in Ys]],
            ["pnb_ta", "PNB / total bilan", "p", [ratio(ca(y), g("total_actif", y), True) for y in Ys]],
            ["nim", "Marge d’intérêts / total bilan", "p", [ratio(sub("b_interets_produits", "b_interets_charges", y=y) if g("b_interets_charges", y) is not None else None, g("total_actif", y), True) for y in Ys]]]])
        R.append(["Bilan et risque", [
            ["ld", "Crédits / dépôts", "p", [ratio(g("b_creances_clientele", y), g("b_dettes_clientele", y), True) for y in Ys]],
            ["l_ta", "Crédits / total bilan", "p", [ratio(g("b_creances_clientele", y), g("total_actif", y), True) for y in Ys]],
            ["d_ta", "Dépôts / total bilan", "p", [ratio(g("b_dettes_clientele", y), g("total_actif", y), True) for y in Ys]],
            ["eq_ta", "Capitaux propres / total bilan", "p", [ratio(g("capitaux_propres", y), g("total_actif", y), True) for y in Ys]],
            ["eq_l", "Capitaux propres / crédits", "p", [ratio(g("capitaux_propres", y), g("b_creances_clientele", y), True) for y in Ys]],
            ["cor_l", "Coût du risque / crédits moyens", "p", [ratio(cdr(y), avg("b_creances_clientele", y), True) for y in Ys]],
            ["y_l", "Intérêts reçus / crédits moyens", "p", [ratio(g("b_interets_produits", y), avg("b_creances_clientele", y), True) for y in Ys]],
            ["c_d", "Intérêts versés / dépôts moyens", "p", [ratio(absn(g("b_interets_charges", y)), avg("b_dettes_clientele", y), True) for y in Ys]]]])
    else:
        R.append(["Croissance", [
            ["g_ca", "Chiffre d’affaires", "p", [grow_("chiffre_affaires", y) for y in Ys]],
            ["g_va", "Valeur ajoutée", "p", [grow_("valeur_ajoutee", y) for y in Ys]],
            ["g_ebe", "Excédent brut d’exploitation", "p", [grow_("ebe", y) for y in Ys]],
            ["g_re", "Résultat d’exploitation", "p", [grow_("resultat_exploitation", y) for y in Ys]],
            ["g_rn", "Résultat net", "p", [grow_("resultat_net", y) for y in Ys]],
            ["g_cp", "Capitaux propres", "p", [grow_("capitaux_propres", y) for y in Ys]],
            ["g_ta", "Total bilan", "p", [grow_("total_actif", y) for y in Ys]],
            ["g_cafg", "Capacité d’autofinancement", "p", [grow_("cafg", y) for y in Ys]]]])
        R.append(["Marges", [
            ["mc", "Taux de marge commerciale (marge / ventes de marchandises)", "p", [ratio(g("marge_commerciale", y), g("ventes_marchandises", y), True) for y in Ys]],
            ["va_ca", "Valeur ajoutée / CA", "p", [ratio(g("valeur_ajoutee", y), ca(y), True) for y in Ys]],
            ["ebe_ca", "Marge d’EBE (EBE / CA)", "p", [ratio(g("ebe", y), ca(y), True) for y in Ys]],
            ["re_ca", "Marge d’exploitation (résultat d’exploitation / CA)", "p", [ratio(g("resultat_exploitation", y), ca(y), True) for y in Ys]],
            ["rao_ca", "Résultat des activités ordinaires / CA", "p", [ratio(g("rao", y), ca(y), True) for y in Ys]],
            ["rn_ca", "Marge nette (résultat net / CA)", "p", [ratio(g("resultat_net", y), ca(y), True) for y in Ys]],
            ["cafg_ca", "Capacité d’autofinancement / CA", "p", [ratio(g("cafg", y), ca(y), True) for y in Ys]]]])
        R.append(["Charges", [
            ["pers_ca", "Charges de personnel / CA", "p", [ratio(absn(g("charges_personnel", y)), ca(y), True) for y in Ys]],
            ["pers_va", "Charges de personnel / valeur ajoutée", "p", [ratio(absn(g("charges_personnel", y)), g("valeur_ajoutee", y), True) for y in Ys]],
            ["dot_ca", "Dotations aux amortissements / CA", "p", [ratio(absn(g("dotations", y)), ca(y), True) for y in Ys]],
            ["ff_ca", "Frais financiers / CA", "p", [ratio(absn(g("frais_financiers", y)), ca(y), True) for y in Ys]],
            ["ff_ebe", "Frais financiers / EBE", "p", [ratio(absn(g("frais_financiers", y)), g("ebe", y), True) for y in Ys]],
            ["icov", "Couverture des frais financiers (résultat d’exploitation / frais financiers)", "x", [ratio(g("resultat_exploitation", y), absn(g("frais_financiers", y)), True) for y in Ys]],
            ["tax", "Taux d’impôt effectif", "p", [taux_impot(y) for y in Ys]]]])
        R.append(["Rentabilité", [
            ["roe", "ROE (résultat net / capitaux propres)", "p", [ratio(g("resultat_net", y), g("capitaux_propres", y), True) for y in Ys]],
            ["roe_m", "ROE sur capitaux propres moyens", "p", [ratio(g("resultat_net", y), avg("capitaux_propres", y), True) for y in Ys]],
            ["roa", "ROA (résultat net / total bilan)", "p", [ratio(g("resultat_net", y), g("total_actif", y), True) for y in Ys]],
            ["roa_m", "ROA sur total bilan moyen", "p", [ratio(g("resultat_net", y), avg("total_actif", y), True) for y in Ys]],
            ["re_ta", "Rentabilité économique (résultat d’exploitation / total bilan)", "p", [ratio(g("resultat_exploitation", y), g("total_actif", y), True) for y in Ys]],
            ["ebe_ta", "EBE / total bilan", "p", [ratio(g("ebe", y), g("total_actif", y), True) for y in Ys]],
            ["roce", "ROCE (résultat d’exploitation après impôt / (capitaux propres + dettes financières))", "p",
             [ratio(g("resultat_exploitation", y) * (1 - taux_impot(y)) if g("resultat_exploitation", y) is not None and taux_impot(y) is not None else None,
                    summ("capitaux_propres", "dettes_financieres", y=y, need=2), True) for y in Ys]],
            ["cafg_cp", "Capacité d’autofinancement / capitaux propres", "p", [ratio(g("cafg", y), g("capitaux_propres", y), True) for y in Ys]]]])
        R.append(["Structure financière", [
            ["auto", "Autonomie financière (capitaux propres / total bilan)", "p", [ratio(g("capitaux_propres", y), g("total_passif", y) or g("total_actif", y), True) for y in Ys]],
            ["gear", "Dettes financières / capitaux propres", "x", [ratio(g("dettes_financieres", y), g("capitaux_propres", y), True) for y in Ys]],
            ["nd_cp", "Endettement net / capitaux propres", "x", [ratio(dette_nette(y), g("capitaux_propres", y), True) for y in Ys]],
            ["nd", "Endettement net (dettes financières + trésorerie passif − trésorerie actif)", "m", [dette_nette(y) for y in Ys]],
            ["nd_ebe", "Endettement net / EBE", "x", [ratio(dette_nette(y), g("ebe", y), True) for y in Ys]],
            ["df_cafg", "Capacité de remboursement (dettes financières / CAFG, en années)", "x", [ratio(g("dettes_financieres", y), g("cafg", y), True) for y in Ys]],
            ["cov_imm", "Ressources stables / actif immobilisé", "x", [ratio(g("ressources_stables", y), g("actif_immobilise", y), True) for y in Ys]],
            ["fr", "Fonds de roulement (ressources stables − actif immobilisé)", "m", [sub("ressources_stables", "actif_immobilise", y=y) for y in Ys]],
            ["bfr", "Besoin en fonds de roulement (actif circulant − passif circulant)", "m", [sub("actif_circulant", "passif_circulant", y=y) for y in Ys]],
            ["tn", "Trésorerie nette (trésorerie actif − trésorerie passif)", "m", [sub("tresorerie_actif", "tresorerie_passif", y=y) for y in Ys]],
            ["fr_j", "Fonds de roulement en jours de CA", "j", [ratio(sub("ressources_stables", "actif_immobilise", y=y) * 360 if sub("ressources_stables", "actif_immobilise", y=y) is not None else None, ca(y), True) for y in Ys]],
            ["bfr_j", "BFR en jours de CA", "j", [ratio(sub("actif_circulant", "passif_circulant", y=y) * 360 if sub("actif_circulant", "passif_circulant", y=y) is not None else None, ca(y), True) for y in Ys]]]])
        R.append(["Liquidité et activité", [
            ["liq_g", "Liquidité générale ((actif circulant + trésorerie) / (passif circulant + trésorerie passif))", "x",
             [ratio(summ("actif_circulant", "tresorerie_actif", y=y, need=2), summ("passif_circulant", "tresorerie_passif", y=y, need=2), True) for y in Ys]],
            ["liq_r", "Liquidité réduite (hors stocks)", "x",
             [ratio(summ("actif_circulant", "tresorerie_actif", y=y, need=2) - g("stocks", y) if summ("actif_circulant", "tresorerie_actif", y=y, need=2) is not None and g("stocks", y) is not None else None,
                    summ("passif_circulant", "tresorerie_passif", y=y, need=2), True) for y in Ys]],
            ["liq_i", "Liquidité immédiate (trésorerie actif / dettes à court terme)", "x", [ratio(g("tresorerie_actif", y), summ("passif_circulant", "tresorerie_passif", y=y, need=2), True) for y in Ys]],
            ["rot", "Rotation de l’actif (CA / total bilan)", "x", [ratio(ca(y), g("total_actif", y), True) for y in Ys]],
            ["stk_j", "Stocks en jours de CA", "j", [ratio(g("stocks", y) * 360 if g("stocks", y) is not None else None, ca(y), True) for y in Ys]],
            ["cli_j", "Créances en jours de CA", "j", [ratio((g("creances", y) if g("creances", y) is not None else g("clients", y)) * 360 if (g("creances", y) if g("creances", y) is not None else g("clients", y)) is not None else None, ca(y), True) for y in Ys]],
            ["frs_j", "Fournisseurs en jours de CA", "j", [ratio(g("fournisseurs", y) * 360 if g("fournisseurs", y) is not None else None, ca(y), True) for y in Ys]],
            ["imm_ta", "Actif immobilisé / total bilan", "p", [ratio(g("actif_immobilise", y), g("total_actif", y), True) for y in Ys]],
            ["imm_ca", "Intensité capitalistique (actif immobilisé / CA)", "x", [ratio(g("actif_immobilise", y), ca(y), True) for y in Ys]]]])
        R.append(["Flux de trésorerie", [
            ["cafg", "Capacité d’autofinancement globale", "m", [g("cafg", y) for y in Ys]],
            ["cafg_rn", "Capacité d’autofinancement / résultat net", "x", [ratio(g("cafg", y), g("resultat_net", y), True) for y in Ys]],
            ["fo_ca", "Flux opérationnels / CA", "p", [ratio(g("flux_operationnels", y), ca(y), True) for y in Ys]],
            ["fo_rn", "Flux opérationnels / résultat net", "x", [ratio(g("flux_operationnels", y), g("resultat_net", y), True) for y in Ys]],
            ["capex", "Investissements (acquisitions d’immobilisations)", "m", [capex(y) for y in Ys]],
            ["capex_ca", "Investissements / CA", "p", [ratio(capex(y), ca(y), True) for y in Ys]],
            ["capex_dot", "Investissements / dotations aux amortissements", "x", [ratio(capex(y), absn(g("dotations", y)), True) for y in Ys]],
            ["fcf", "Flux de trésorerie disponible (flux opérationnels − investissements)", "m", [fcf(y) for y in Ys]],
            ["fcf_ca", "Flux disponible / CA", "p", [ratio(fcf(y), ca(y), True) for y in Ys]],
            ["div_rn", "Dividendes versés / résultat net de l’exercice précédent", "p", [ratio(absn(g("dividendes_verses", y)), g("resultat_net", y - 1), True) for y in Ys]],
            ["div_fo", "Dividendes versés / flux opérationnels", "p", [ratio(absn(g("dividendes_verses", y)), g("flux_operationnels", y), True) for y in Ys]]]])
    def tcam(k, y, n):
        a_, b_ = (ca(y - n), ca(y)) if k == "_ca" else (g(k, y - n), g(k, y))
        return cagr(a_, b_, n)
    base = [("_ca", "PNB" if bank else "Chiffre d’affaires"), ("resultat_net", "Résultat net")] + \
        ([("b_dettes_clientele", "Dépôts de la clientèle"), ("b_creances_clientele", "Crédits à la clientèle")] if bank else [("ebe", "EBE"), ("capitaux_propres", "Capitaux propres")])
    R.append(["Croissance annuelle moyenne", [[f"tc{n}_{k}", f"{lab} sur {n} ans", "p", [tcam(k, y, n) for y in Ys]] for k, lab in base for n in (3, 5, 10)]])

    def mean3(fn, y):
        v = [fn(y - j) for j in range(3)]
        return sum(v) / 3 if all(x is not None for x in v) else None
    roe_f = lambda y: ratio(g("resultat_net", y), g("capitaux_propres", y), True)  # noqa: E731
    nm_f = lambda y: ratio(g("resultat_net", y), ca(y), True)  # noqa: E731
    R.append(["Moyennes sur 3 exercices", [["roe3", "ROE moyen sur 3 ans", "p", [mean3(roe_f, y) for y in Ys]],
                                           ["nm3", ("Résultat net / PNB" if bank else "Marge nette") + " moyenne sur 3 ans", "p", [mean3(nm_f, y) for y in Ys]],
                                           ["ebe3", "Marge d’EBE moyenne sur 3 ans", "p", [None if bank else mean3(lambda z: ratio(g("ebe", z), ca(z), True), y) for y in Ys]]]])
    ps = [per_share(y) for y in Ys]

    def n_impl(i):  # nombre d'actions implicite : résultat net publié ÷ BNPA publié (même base que les cours ajustés)
        y, e_ = Ys[i], ps[i][0]
        rn = g("resultat_net", y)
        return rn * 1e6 / e_ if rn and e_ and (rn > 0) == (e_ > 0) else None

    def per_sh(k, i):
        n_ = n_impl(i)
        v = g(k, Ys[i]) if k != "_ca" else ca(Ys[i])
        return v * 1e6 / n_ if v is not None and n_ else None

    def ev(i):
        n_, px_ = n_impl(i), ps[i][2]
        nd_ = dette_nette(Ys[i])
        return px_ * n_ / 1e6 + nd_ if n_ and px_ and nd_ is not None and not bank else None
    R.append(["Par action et marché", [
        ["bvps", "Actif net par action (FCFA)", "e", [per_sh("capitaux_propres", i) for i in range(len(Ys))]],
        ["cfps", "Capacité d’autofinancement par action (FCFA)", "e", [per_sh("cafg", i) for i in range(len(Ys))]],
        ["sps", ("PNB" if bank else "Chiffre d’affaires") + " par action (FCFA)", "e", [per_sh("_ca", i) for i in range(len(Ys))]],
        ["pb", "Cours / actif net par action (P/B)", "x", [ratio(ps[i][2], per_sh("capitaux_propres", i), True) for i in range(len(Ys))]],
        ["pcf", "Cours / capacité d’autofinancement par action", "x", [ratio(ps[i][2], per_sh("cafg", i), True) for i in range(len(Ys))]],
        ["ev_ebe", "Valeur d’entreprise / EBE", "x", [ratio(ev(i), g("ebe", Ys[i]), True) for i in range(len(Ys))]],
        ["ev_ca", "Valeur d’entreprise / CA", "x", [ratio(ev(i), ca(Ys[i]), True) for i in range(len(Ys))]],
        ["eps", "BNPA publié (FCFA)", "e", [p_[0] for p_ in ps]],
        ["dps", "Dividende net par action (FCFA)", "e", [p_[1] for p_ in ps]],
        ["payout", "Taux de distribution (dividende / BNPA)", "p", [ratio(p_[1], p_[0], True) for p_ in ps]],
        ["px", "Dernier cours de l’exercice (FCFA)", "e", [p_[2] for p_ in ps]],
        ["pe", "PER au dernier cours de l’exercice", "x", [ratio(p_[2], p_[0], True) for p_ in ps]],
        ["dy", "Rendement du dividende au dernier cours de l’exercice", "p", [ratio(p_[1], p_[2], True) for p_ in ps]],
        ["g_eps", "Croissance du BNPA", "p", [grow(ps[i - 1][0], ps[i][0]) if i and Ys[i - 1] == Ys[i] - 1 and (ps[i][0] or 0) >= 0 else None for i in range(len(Ys))]],
        ["g_dps", "Croissance du dividende", "p", [grow(ps[i - 1][1], ps[i][1]) if i and Ys[i - 1] == Ys[i] - 1 else None for i in range(len(Ys))]]]])
    out = []
    for grp, rows in R:
        for r in rows:  # multiples au-delà de 100 (dénominateur presque nul) : non significatifs
            if r[2] == "x":
                r[3] = [None if v is not None and abs(v) > 100 else v for v in r[3]]
        rows = [r for r in rows if any(v is not None for v in r[3])]
        if rows:
            out.append([grp, rows])
    return Ys, out


def brvm_company(sid, s, fd_, fcf, dps_hist, b, tax):
    """Ratios d'une société BRVM : comptes SikaFinance (5 exercices), flux de trésorerie SYSCOHADA lus dans les états financiers."""
    S = (fd_ or {}).get("series", {})
    bank = bool(s.get("bank"))
    yrs = sorted({int(y) for k in ("ca", "resultat_net", "bnpa", "capitaux_propres") for y in (S.get(k) or {})} | {int(y) for y in (fcf or {})} | {int(y) for y in dps_hist})
    cc = (fd_ or {}).get("cpt") or {}
    yrs = [y for y in yrs if y >= 2010 or str(y) in (cc.get("y") or {}) or y in (cc.get("y") or {})]
    gv = lambda k, y: (S.get(k) or {}).get(str(y))  # noqa: E731
    M = 1e6
    Y = {"y": yrs}
    for k, src in (("rev", "ca"), ("ni", "resultat_net"), ("eps", "bnpa"), ("ebit", "ebit"), ("ebitda", "ebitda"), ("eq", "capitaux_propres"), ("nd", "dette_nette"),
                   ("cash", "tresorerie"), ("assets", "total_bilan"), ("opex", "charges_exploitation"), ("deposits", "depots_clientele"), ("loans", "credits_clientele"),
                   ("cir", "coefficient_d_exploitation"), ("cor", "cout_du_risque"), ("solv", "ratio_de_solvabilite"), ("tier1", "ratio_tier_i"), ("roe_s", "roe"), ("roa_s", "roa"),
                   ("nm_s", "marge_nette"), ("om_s", "marge_exploitation")):
        Y[k] = [gv(src, y) for y in yrs]
    # flux de trésorerie (états financiers) : contrôle d'échelle face au chiffre d'affaires (millions de FCFA attendus)
    ca_y = {y: v for y, v in zip(yrs, Y["rev"]) if v}
    Y["ocf"], Y["capex"], Y["fcf"] = [], [], []
    for y in yrs:
        rec = (fcf or {}).get(str(y)) or {}
        cfo, cap, f_ = rec.get("cfo"), rec.get("capex"), rec.get("fcf")
        ref = ca_y.get(y) or (ca_y[min(ca_y, key=lambda k: abs(k - y))] if ca_y else None)
        div_ = None
        if cfo is not None and ref:
            for dv in (1.0, 1e-3, 1e-6):
                if 0.003 <= abs(cfo * dv) / ref <= 1.5:
                    div_ = dv
                    break
        if div_ is None:
            cfo = cap = f_ = None
        else:
            cfo, cap, f_ = cfo * div_, (cap or 0) * div_, (f_ * div_ if f_ is not None else None)
        Y["ocf"].append(cfo)
        Y["capex"].append(cap if cfo is not None else None)
        Y["fcf"].append(f_)
    # contrôles de vraisemblance des séries publiées (une donnée douteuse est retirée, jamais remplacée par un chiffre inventé) :
    # un zéro de la base est une donnée manquante ; un BPA de signe contraire au résultat net a perdu son signe à la lecture
    # (parenthèses) ; un montant environ mille fois plus petit que les exercices voisins a perdu un groupe de chiffres
    for k in ("rev", "ni", "eps", "ebit", "ebitda", "eq", "assets", "deposits", "loans", "opex"):
        Y[k] = [None if v == 0 else v for v in Y[k]]
    Y["eps"] = [(-e if (e is not None and n is not None and e * n < 0) else e) for e, n in zip(Y["eps"], Y["ni"])]
    for k in ("rev", "ni", "eq"):
        vals = Y[k]
        for i, v in enumerate(vals):
            if v is None:
                continue
            nb = [abs(vals[j]) for j in (i - 2, i - 1, i + 1, i + 2) if 0 <= j < len(vals) and vals[j] and abs(yrs[j] - yrs[i]) <= 2]
            if len(nb) >= 2:
                m_ = sorted(nb)[len(nb) // 2]
                if abs(v) < m_ / 300 and 0.4 <= abs(v) * 1000 / m_ <= 2.5:
                    vals[i] = None
    Y["dps"] = [dps_hist.get(y) or gv("dividende", y) for y in yrs]
    Y["src"] = [(fd_ or {}).get("src_years", {}).get(str(y)) for y in yrs]
    Y["payout"] = [div0(Y["dps"][i], Y["eps"][i]) if Y["eps"][i] and Y["eps"][i] > 0 else None for i in range(len(yrs))]
    sh = s.get("shares")
    Y["fpay"] = [div0((Y["dps"][i] or 0) * sh / M, Y["fcf"][i]) if Y["dps"][i] and sh and Y["fcf"][i] and Y["fcf"][i] > 0 else None for i in range(len(yrs))]
    Y["nm"] = [div0(Y["ni"][i], Y["rev"][i]) for i in range(len(yrs))]
    Y["om"] = [div0(Y["ebit"][i], Y["rev"][i]) for i in range(len(yrs))]
    Y["ebitdam"] = [div0(Y["ebitda"][i], Y["rev"][i]) for i in range(len(yrs))]
    Y["fcfm"] = [div0(Y["fcf"][i], Y["rev"][i]) for i in range(len(yrs))]
    Y["roe"] = [div0(Y["ni"][i], Y["eq"][i]) if (Y["eq"][i] or 0) > 0 else None for i in range(len(yrs))]
    Y["roic"] = [None if bank else (div0(Y["ebit"][i] * (1 - tax), Y["eq"][i] + Y["nd"][i]) if Y["ebit"][i] is not None and Y["eq"][i] and Y["nd"][i] is not None and Y["eq"][i] + Y["nd"][i] > 0 else None) for i in range(len(yrs))]
    Y["nd_ebitda"] = [div0(Y["nd"][i], Y["ebitda"][i]) if (Y["ebitda"][i] or 0) > 0 else None for i in range(len(yrs))]
    Y["ld"] = [div0(Y["loans"][i], Y["deposits"][i]) for i in range(len(yrs))]
    Y["cor_l"] = [div0(Y["cor"][i], Y["loans"][i]) for i in range(len(yrs))]
    # dernier exercice disponible (comptes)
    L = max([i for i in range(len(yrs)) if Y["ni"][i] is not None or Y["rev"][i] is not None] or [len(yrs) - 1])
    price = b["c"][-1] if b else s.get("last")
    mcap = price * sh if price and sh else None
    li = lambda k: Y[k][L] if yrs else None  # noqa: E731

    def lastv(k):
        for i in range(len(yrs) - 1, -1, -1):
            if Y[k][i] is not None:
                return Y[k][i]
        return None
    fi = max([i for i in range(len(yrs)) if Y["fcf"][i] is not None] or [-1])
    ev = mcap + li("nd") * M if mcap and li("nd") is not None and not bank else None
    eps = li("eps")
    r = {"src": "bulletin officiel de la cote BRVM (PER, dividende) · brvm.org (nombre de titres) · états financiers BRVM · SikaFinance en secours (comptes)", "ccy": "XOF", "bank": bank, "fy": yrs[L] if yrs else None, "mcap": mcap, "ev": ev, "price": price,
         "pe": (s.get("per") if s.get("pso") == "off" and s.get("per") else (div0(price, eps) if eps and eps > 0 else None)), "pb": div0(mcap, li("eq") * M) if mcap and (li("eq") or 0) > 0 else None,
         "ps": div0(mcap, li("rev") * M) if mcap and li("rev") else None,
         "ev_ebitda": div0(ev, li("ebitda") * M) if ev and (li("ebitda") or 0) > 0 else None, "ev_sales": div0(ev, li("rev") * M) if ev and li("rev") else None,
         "ev_ebit": div0(ev, li("ebit") * M) if ev and (li("ebit") or 0) > 0 else None, "ey": div0(li("ebit") * M, ev) if ev and li("ebit") is not None else None,
         "fcf": Y["fcf"][fi] if fi >= 0 else None, "fcf_fy": yrs[fi] if fi >= 0 else None,
         "fcfy": div0(Y["fcf"][fi] * M, mcap) if fi >= 0 and mcap and not bank and yrs[fi] >= yrs[L] - 1 else None, "dy": s.get("yld"),
         "gm": None, "om": li("om"), "nm": li("nm"), "ebitdam": li("ebitdam"), "fcfm": Y["fcfm"][fi] if fi >= 0 else None,
         "roe": li("roe"), "roa": div0(li("ni"), li("assets")), "roic": li("roic"), "tax": tax,
         "conv": div0(Y["fcf"][fi], Y["ni"][fi]) if fi >= 0 and Y["ni"][fi] and Y["ni"][fi] > 0 else None,
         "nd": li("nd") * M if li("nd") is not None else None, "nd_ebitda": li("nd_ebitda"), "de": div0(li("nd"), li("eq")) if li("nd") is not None and (li("eq") or 0) > 0 else None,
         "payout": li("payout"), "fpay": Y["fpay"][fi] if fi >= 0 else None, "ld": lastv("ld"), "cir": lastv("cir"), "cor_l": lastv("cor_l"), "solv": lastv("solv")}
    if L >= 1:
        r["rev_g"] = grow(Y["rev"][L - 1], Y["rev"][L])
        r["ni_g"] = grow(Y["ni"][L - 1], Y["ni"][L])
        r["eps_g"] = grow(Y["eps"][L - 1], Y["eps"][L])
        if Y["om"][L] is not None and Y["om"][L - 1] is not None:
            r["om_chg"] = Y["om"][L] - Y["om"][L - 1]
        if Y["nd"][L] is not None and Y["nd"][L - 1] and Y["nd"][L - 1] > 0:
            r["nd_chg"] = grow(Y["nd"][L - 1], Y["nd"][L])
    fy_idx = [i for i in range(len(yrs)) if Y["fcf"][i] is not None]
    if len(fy_idx) >= 2 and fy_idx[-1] - fy_idx[-2] == 1:
        r["fcf_g"] = grow(Y["fcf"][fy_idx[-2]], Y["fcf"][fy_idx[-1]])
    for key in ("rev", "ni", "eps", "fcf"):
        idx = [i for i in range(len(yrs)) if Y[key][i] is not None]
        if not idx:
            continue
        last = idx[-1]
        for n_ in (3, 5, 10):
            j = last - n_
            if j >= 0 and Y[key][j] is not None:
                r[f"{key}_cagr{n_}"] = cagr(Y[key][j], Y[key][last], n_)
    # Piotroski simplifié (données annuelles disponibles)
    if L >= 1 and not bank:
        crit = [Y["ni"][L] > 0 if Y["ni"][L] is not None else None,
                Y["ocf"][L] > 0 if Y["ocf"][L] is not None else None,
                (div0(Y["ni"][L], Y["assets"][L]) or 0) > (div0(Y["ni"][L - 1], Y["assets"][L - 1]) or 0) if Y["ni"][L] is not None and Y["ni"][L - 1] is not None and Y["assets"][L] and Y["assets"][L - 1] else None,
                Y["ocf"][L] > Y["ni"][L] if Y["ocf"][L] is not None and Y["ni"][L] is not None else None,
                (Y["nd"][L] or 0) <= (Y["nd"][L - 1] or 0) if Y["nd"][L] is not None and Y["nd"][L - 1] is not None else None,
                None, None,
                Y["om"][L] > Y["om"][L - 1] if Y["om"][L] is not None and Y["om"][L - 1] is not None else None,
                div0(Y["rev"][L], Y["assets"][L]) > div0(Y["rev"][L - 1], Y["assets"][L - 1]) if Y["rev"][L] and Y["rev"][L - 1] and Y["assets"][L] and Y["assets"][L - 1] else None]
        known = [x for x in crit if x is not None]
        r["fscore"], r["fscore_n"], r["fcrit"] = sum(known), len(known), [None if x is None else int(x) for x in crit]
    # multiples historiques : cours / dernier exercice publié (disponible fin avril de l'année suivante)
    if b and yrs:
        wd, wc = weekly_px(b, 20140101)
        pe, pb, eve, fy, dy = [], [], [], [], []
        for d_, c_ in zip(wd, wc):
            yy = d_ // 10000 - (1 if d_ % 10000 >= 430 else 2)
            i = yrs.index(yy) if yy in yrs else None
            ep = Y["eps"][i] if i is not None else None
            eq_ = Y["eq"][i] if i is not None else None
            eb = Y["ebitda"][i] if i is not None else None
            nd_ = Y["nd"][i] if i is not None else None
            f_ = Y["fcf"][i] if i is not None else None
            dp = Y["dps"][i] if i is not None else None
            mc = c_ * sh if sh else None
            pe.append(div0(c_, ep) if ep and ep > 0 else None)
            pb.append(div0(mc, eq_ * M) if mc and eq_ and eq_ > 0 else None)
            eve.append(div0(mc + nd_ * M, eb * M) if mc and nd_ is not None and eb and eb > 0 and not bank else None)
            fy.append(div0(f_ * M, mc) if mc and f_ is not None and not bank else None)
            dy.append(div0(dp, c_) if dp else None)
        r["mh"] = {"d": wd, "pe": pe, "pb": pb, "ev_ebitda": eve, "fcfy": fy, "dy": dy}
    r["Y"] = Y
    # états financiers publiés (postes vérifiés) et ratios détaillés, sur tous les exercices lus
    if cc.get("y"):
        Ys = sorted(int(y) for y in cc["y"])
        def sections(cc_, Ys_):
            secs = []
            for sk, title in ((("bis" if bank else "is"), "Compte de résultat"), (("bbs" if bank else "bs"), "Bilan"), ("cf", "Flux de trésorerie")):
                rows = []
                seen = set()
                for k, lab in CPT_ROWS[sk]:
                    yv_ = [(cc_["y"].get(y) or cc_["y"].get(str(y)) or {}) for y in Ys_]
                    vals = [(x.get("v") or {}).get(k) for x in yv_]
                    if any(v is not None for v in vals) and lab not in seen:
                        seen.add(lab)
                        # (indices des exercices où le poste est un total recalculé de ses composantes publiées)
                        cx = [i for i, x in enumerate(yv_) if vals[i] is not None and k in (x.get("calc") or ())]
                        rows.append([k, lab, vals] + ([cx] if cx else []))
                if rows:
                    secs.append([sk, title, rows])
            return secs
        secs_ = sections(cc, Ys)
        eps_y = {int(y): v for y, v in (S.get("bnpa") or {}).items() if v is not None}
        dps_y = {int(y): v for y, v in (S.get("dividende") or {}).items() if v}
        dps_y.update({int(y): v for y, v in dps_hist.items() if v})
        px_y = {}
        if b:
            for d_, c_ in zip(b["d"], b["c"]):
                if c_:
                    px_y[d_ // 10000] = c_
            last_y = b["d"][-1] // 10000
            px_y.pop(last_y, None)  # exercice en cours : pas de « dernier cours de l'exercice »
        # exercices sans comptes détaillés lus : ratios calculés sur les chiffres clés publiés (marqués comme tels)
        KF = (("ca", "b_pnb" if bank else "chiffre_affaires"), ("resultat_net", "resultat_net"), ("total_bilan", "total_actif"),
              ("capitaux_propres", "capitaux_propres"), ("ebit", "resultat_exploitation"), ("ebitda", "ebe"),
              ("depots_clientele", "b_dettes_clientele"), ("credits_clientele", "b_creances_clientele"))
        ccr, yk = {"y": {str(y): v for y, v in cc["y"].items()}}, []
        for y in yrs:
            if str(y) in ccr["y"]:
                continue
            v_ = {ck: (S.get(sk) or {}).get(str(y)) for sk, ck in KF}
            v_ = {k: x for k, x in v_.items() if x is not None}
            if len(v_) >= 2:
                ccr["y"][str(y)] = {"v": v_}
                yk.append(y)
        Yr, groups = brvm_ratios(ccr, bank, eps_y, dps_y, px_y)
        r["C"] = {"y": Ys, "per": cc.get("per"), "std": cc.get("std"), "s": secs_}
        fxy = {str(y): [x["fx"], x.get("d")] for y, x in cc["y"].items() if x.get("fx")}
        if fxy:  # (états publiés en dollars, convertis au cours du jour de publication : cours et date par exercice)
            r["C"]["fx"] = fxy
        r["R"] = {"y": Yr, "g": groups, "k": [y for y in yk if y in Yr]}
        alt = cc.get("alt") or {}
        if len(alt.get("y") or {}) >= 2:  # l'autre référentiel publié par la société (sociaux / consolidés, SYSCOHADA / IFRS)
            Ya = sorted(int(y) for y in alt["y"])
            r["C2"] = {"y": Ya, "per": alt.get("per"), "std": alt.get("std"), "s": sections(alt, Ya)}
    return r


def rnd_tree(o, nd=6):
    if isinstance(o, float):
        if not math.isfinite(o):
            return None
        if o == 0:
            return 0
        mag = math.floor(math.log10(abs(o)))
        return round(o, max(0, nd - 1 - mag)) if mag < nd else round(o)
    if isinstance(o, dict):
        return {k: rnd_tree(v, nd) for k, v in o.items()}
    if isinstance(o, list):
        return [rnd_tree(v, nd) for v in o]
    return o


def stability(r, dps_by_year=None):
    """Régularité des résultats et des dividendes (5 à 10 derniers exercices) pour le score multifactoriel."""
    Y = r.get("Y") or {}
    o = {}
    ni = [v for v in (Y.get("ni") or []) if v is not None][-6:]
    if len(ni) >= 4:
        m = sum(ni) / len(ni)
        sd = (sum((x - m) ** 2 for x in ni) / (len(ni) - 1)) ** .5
        o["ni_cv"] = sd / abs(m) if m > 0 else None
        o["ni_dec"] = sum(1 for a, b in zip(ni, ni[1:]) if b < a)
        o["ni_n"] = len(ni)
    roe = [v for v in (Y.get("roe") or []) if v is not None][-5:]
    if len(roe) >= 3:
        m = sum(roe) / len(roe)
        o["roe_sd"] = (sum((x - m) ** 2 for x in roe) / (len(roe) - 1)) ** .5
    if dps_by_year:
        ys = sorted(dps_by_year)
        last = ys[-1]
        win = [dps_by_year.get(y) for y in range(last - 9, last + 1)]
        o["div_n10"] = sum(1 for v in win if v)
        o["div_cut"] = sum(1 for a, b in zip(win, win[1:]) if a and b and b < a * .95)
    elif Y.get("div") and Y.get("sh"):
        d = [abs(v) / s_ if v is not None and s_ else None for v, s_ in zip(Y["div"], Y["sh"])][-10:]
        o["div_n10"] = sum(1 for v in d if v)
        o["div_cut"] = sum(1 for a, b in zip(d, d[1:]) if a and b and b < a * .95)
    return o


def fundamentals(extra, out, files, secs_by, fund, fcf_path, dmeta, analyst, log):
    sec = jload(os.path.join(extra, "secfacts.json"), {}) if extra else {}
    US_SPL.clear()
    US_SPL.update(((jload(os.path.join(extra, "us_splits.json"), {}) or {}).get("s") or {}) if extra else {})
    fcf = (jload(fcf_path, {}) or {}).get("series", {}) if fcf_path else {}
    fx = {"USD": 1.0}
    if "EURUSD" in files:
        fx["EUR"] = 1 / files["EURUSD"]["c"][-1]
    if "USDTWD" in files:
        fx["TWD"] = files["USDTWD"]["c"][-1]
    idx = []
    os.makedirs(os.path.join(out, "fa"), exist_ok=True)
    keep = ("mcap", "ev", "pe", "fpe", "fpe_fy", "ps", "pb", "ev_ebitda", "ev_sales", "ev_ebit", "ey", "fcfy", "fcfy_sbc", "dy", "by", "shy", "gm", "om", "nm", "fcfm", "ebitdam", "roe", "roa", "roic",
            "conv", "rev_g", "ni_g", "fcf_g", "eps_g", "sh_chg", "nd", "nd_ebitda", "de", "cur", "icov", "payout", "fpay", "accr", "gpa", "fscore", "fscore_n", "altz", "r40",
            "rev_cagr3", "rev_cagr5", "rev_cagr10", "fcf_cagr3", "fcf_cagr5", "fcf_cagr10", "eps_cagr3", "eps_cagr5", "eps_cagr10", "ni_cagr3", "ni_cagr5",
            "om_chg", "nd_chg", "capex_s", "sbc_s", "rnd_s", "ld", "cir", "cor_l", "fcf", "fcf_fy", "fy", "asof_q", "bank", "annual_only")
    # États-Unis
    for t, co in (sec.get("co") or {}).items():
        s = secs_by.get(t)
        if not s:
            continue
        try:
            r = us_company(co, files.get(t), s, fx)
        except Exception as e:  # noqa: BLE001
            log("fa", t, e)
            continue
        if not r:
            continue
        an = (analyst or {}).get(t) or {}
        sm = {k: (v or {}).get("value") for k, v in ((an.get("sum") or {}).get("summaryData") or {}).items()}
        fpe = None
        try:
            fpe = float(str(sm.get("ForwardPE1Yr") or "").replace(",", "")) or None
        except ValueError:
            fpe = None
        if not fpe:  # Nasdaq ne publie plus ce ratio : cours ÷ BPA consensuel du premier exercice non publié (tableau annuel des prévisions)
            fr = (((an.get("fc") or {}).get("yearlyForecast") or {}).get("rows") or [])
            e1 = fr[0].get("consensusEPSForecast") if fr else None
            try:
                e1 = float(e1)
            except (TypeError, ValueError):
                e1 = None
            if e1 and e1 > 0 and s.get("last"):
                fpe, r["fpe_fy"] = round(s["last"] / e1, 2), fr[0].get("fiscalEnd")
        r["fpe"] = fpe
        s["fa"] = True
        jsave(os.path.join(out, "fa", t + ".json"), rnd_tree({"id": t, "mkt": "US", **r}))
        idx.append({"id": t, "mkt": "US", "grp": s.get("grp"), **{k: r.get(k) for k in keep}, **({"mcap": r["mcap_usd"]} if r.get("mcap_usd") else {}), **stability(r)})
    # BRVM
    # dividende de chaque exercice : ses versements ordinaires additionnés (acompte et solde, dividende complémentaire), sans
    # l'exceptionnel (avant le 19/10/2026, le dernier versement lu remplaçait les autres : Filtisac 2024 affichait l'exceptionnel)
    dps = collections.defaultdict(dict)
    for x in dmeta:
        if x.get("t") and x.get("ex") and x.get("dps") and not x.get("exc"):
            dps[x["t"]][int(x["ex"])] = dps[x["t"]].get(int(x["ex"]), 0) + x["dps"]
    for sid, s in secs_by.items():
        if s.get("mkt") != "BRVM" or s.get("cls") != "Equity":
            continue
        fd_ = fund.get(sid)
        if not fd_:
            continue
        try:
            r = brvm_company(sid, s, fd_, fcf.get(sid), dps.get(sid, {}), files.get(sid), TAX_BRVM.get(s.get("cty"), .25))
        except Exception as e:  # noqa: BLE001
            log("fa", sid, e)
            continue
        s["fa"] = True
        jsave(os.path.join(out, "fa", sid + ".json"), rnd_tree({"id": sid, "mkt": "BRVM", **r}))
        idx.append({"id": sid, "mkt": "BRVM", "grp": s.get("grp"), **{k: r.get(k) for k in keep}, **stability(r, dps.get(sid))})
    jsave(os.path.join(out, "fa_index.json"), rnd_tree({"rows": idx, "fx": fx}))
    log(f"fa : {len(idx)} sociétés ({sum(1 for x in idx if x['mkt'] == 'US')} US)")
    return idx


def ee(extra, out, secs_by, files, log):
    A = jload(os.path.join(extra, "analyst.json"), {}) if extra else {}
    res = {}
    for t, a in (A or {}).items():
        if t not in secs_by:
            continue
        sm = {k: (v or {}).get("value") for k, v in ((a.get("sum") or {}).get("summaryData") or {}).items()}
        fc = a.get("fc") or {}
        yr = ((fc.get("yearlyForecast") or {}).get("rows")) or []
        qr = ((fc.get("quarterlyForecast") or {}).get("rows")) or []
        tp = (a.get("tp") or {}).get("consensusOverview") or {}
        ed = a.get("ed") or {}
        res[t] = {"ts": a.get("ts"), "stale": a.get("stale", False), "sum": sm, "yr": yr, "qr": qr, "sur": a.get("surh", []), "snap": a.get("snap", [])[-260:],
                  "tp": tp, "ed": ed.get("reportText") or ed.get("announcement") or ed.get("earningsDate") or None}
        secs_by[t]["ee"] = bool(yr or a.get("surh"))
    if res:
        jsave(os.path.join(out, "ee.json"), res)
        log(f"ee.json : {len(res)} sociétés")


def per_brvm(extra, out, files, secs_by, fund, log):
    """PER du marché BRVM : bulletin officiel (historique), calcul FQT pondéré par les capitalisations, sources prévisionnelles."""
    boc = jload(os.path.join(extra, "boc.json"), {}) if extra else {}
    d = sorted((boc or {}).get("d", {}).items())
    res = {"boc": {"d": [int(k) for k, _ in d], **{f: [v.get(f) for _, v in d] for f in ("per", "rdt", "rent", "prime", "cap")}}}
    # PER agrégé FQT : somme des capitalisations / somme des résultats nets du dernier exercice publié
    ids = [s for s, x in secs_by.items() if x.get("mkt") == "BRVM" and x.get("cls") == "Equity"]
    grid = files["BRVMC"]["d"] if "BRVMC" in files else []
    grid = [g for g in grid if g >= 20190101][::5]
    pe, cov = [], []
    for g in grid:
        mc = ni = 0.0
        k = 0
        yy = g // 10000 - (1 if g % 10000 >= 430 else 2)
        for sid in ids:
            sh = secs_by[sid].get("shares")
            r = ((fund.get(sid) or {}).get("series") or {}).get("resultat_net") or {}
            b = files.get(sid)
            if not sh or not b or str(yy) not in r:
                continue
            j = bisect.bisect_right(b["d"], g) - 1
            if j < 0:
                continue
            mc += b["c"][j] * sh
            ni += r[str(yy)] * 1e6
            k += 1
        pe.append(r_(mc / ni, 2) if ni > 0 and k >= 30 else None)
        cov.append(k)
    res["fqt"] = {"d": grid, "pe": pe, "n": cov, "method": "Σ capitalisations ÷ Σ résultats nets du dernier exercice publié (disponible fin avril)"}
    res["sources"] = jload(os.path.join(extra, "fpe_sources.json"), []) if extra else []
    jsave(os.path.join(out, "per.json"), res)
    log(f"per.json : {len(d)} bulletins, PER FQT {pe[-1] if pe else None}")


def uemoa(extra, out, secs_by, cty_name, log):
    wb = jload(os.path.join(extra, "worldbank.json")) if extra else None
    if not wb:
        return
    cap = collections.defaultdict(float)
    nb = collections.Counter()
    iso = {"CI": "CIV", "SN": "SEN", "BF": "BFA", "BJ": "BEN", "ML": "MLI", "NE": "NER", "TG": "TGO"}
    for s in secs_by.values():
        if s.get("mkt") == "BRVM" and s.get("cls") == "Equity" and s.get("cty"):
            cap[iso.get(s["cty"], s["cty"])] += s.get("mcap") or 0
            nb[iso.get(s["cty"], s["cty"])] += 1
    wb["brvm"] = {"cap": dict(cap), "n": dict(nb)}
    jsave(os.path.join(out, "uemoa.json"), wb)
    log(f"uemoa.json : {len(wb.get('ind', {}))} indicateurs")


def profiles(extra, out, secs_by, log):
    """Fiches sociétés (SikaFinance pour la BRVM ; Nasdaq/SEC pour les US) -> data/profiles.json, lu par DES et HDS."""
    if not extra:
        return
    P = {}
    for src in ("profiles.json", "profiles_us.json"):
        P.update({k: v for k, v in (jload(os.path.join(extra, src), {}) or {}).items() if k in secs_by})
    # présentation des sociétés BRVM écrite par FQT (seed/des_fqt.json, depuis le 19/10/2026) : chaque fait vérifié sur un
    # document officiel de la société (preuves dans seed/des_fqt_preuves.json) ; elle remplace le texte de la fiche tierce
    fq = jload(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", "des_fqt.json"), {}) or {}
    n_fq = 0
    for k, t in (fq.get("desc") or {}).items():
        if k in secs_by and isinstance(t, str) and t.strip():
            P.setdefault(k, {})["desc"] = t.strip()
            n_fq += 1
    if n_fq:
        log("présentations FQT", n_fq)
    if P:
        jsave(os.path.join(out, "profiles.json"), P)
        log("profils", len(P))


def anomalies(out, files, secs_by, log):
    """Détection d'anomalies statistiques (alertes à vérifier, pas des preuves) pour toutes les actions BRVM et US :
    variation de cours hors norme (écarts robustes MAD), montants échangés anormaux, écart extrême à la tendance, cours figé,
    absence d'échange, trous de données, variations inhabituelles de résultat ou de dividende, incohérences de données."""
    import time as _t
    fa = {r["id"]: r for r in (jload(os.path.join(out, "fa_index.json"), {}) or {}).get("rows", [])}
    dv = jload(os.path.join(out, "dividends.json"), []) or []
    by_dv = collections.defaultdict(list)
    for x in dv:
        if x.get("t") and x.get("dps"):
            by_dv[x["t"]].append(x)
    cal = files.get("BRVMC") or {}
    cal_d = cal.get("d") or []
    res = {}

    def mad(a):
        m = statistics.median(a)
        return m, statistics.median([abs(x - m) for x in a]) * 1.4826

    for sid, s in secs_by.items():
        if s.get("cls") != "Equity" or s.get("typ") == "ETF" or s.get("mkt") not in ("BRVM", "US"):
            continue
        b = files.get(sid)
        if not b or len(b.get("c") or []) < 80:
            continue
        d, c = b["d"], b["c"]
        v = b.get("v") or [0] * len(c)
        val = b.get("val") or [x * y for x, y in zip(v, c)]
        n = len(c)
        L = []
        brvm = s.get("mkt") == "BRVM"
        exd = {}
        for x in by_dv.get(sid, []):
            k = (x.get("det") or x.get("pay") or "")[:10]
            if k:  # (deux versements détachés le même jour, annuel et exceptionnel : leur somme)
                exd[int(k.replace("-", ""))] = exd.get(int(k.replace("-", "")), 0) + x["dps"]
        r = [c[i] / c[i - 1] - 1 if c[i - 1] else 0 for i in range(1, n)]
        # 1. variations de cours hors norme (10 dernières séances), seuil BRVM de ±7,5 %
        for i in range(max(61, n - 10), n):
            ri = r[i - 1]
            base = r[i - 61:i - 1]
            med, sd = mad(base)
            if sd <= 0:
                sd = statistics.pstdev(base) or 1e-9
            z = (ri - med) / sd
            divi = next((exd[k] for k in exd if 0 <= (i2d(d[i]) - i2d(k)).days <= 3), None)
            if ri <= -0.4:
                L.append({"k": "Possible division d'action", "sv": 3, "d": d[i], "v": round(ri, 4), "vl": f"{ri * 100:+.1f} % en une séance", "m": f"baisse de {ri * 100:.0f} % en une séance : vérifier une division ou une opération sur titre avant toute analyse"})
            elif abs(z) >= 4 and abs(ri) >= .03:
                why = f" ; détachement d'un dividende de {divi:g} ce jour-là" if divi else ""
                L.append({"k": "Variation de cours anormale", "sv": 1 if divi else (3 if abs(z) >= 8 else 2), "d": d[i], "v": round(ri, 4), "vl": f"{z:+.1f} écarts robustes", "m": f"{ri * 100:+.2f} % sur la séance, contre une variation habituelle de ±{sd * 100:.2f} %{why}"})
            if brvm and abs(ri) >= .0745 and not divi:
                L.append({"k": "Seuil de variation", "sv": 1, "d": d[i], "v": round(ri, 4), "vl": "seuil BRVM ±7,5 %", "m": f"cours au seuil journalier de variation ({ri * 100:+.2f} %)"})
        # 2. montants échangés anormaux
        for i in range(max(61, n - 10), n):
            prev = [x for x in val[i - 60:i] if x and x > 0]
            if len(prev) < 20 or not val[i]:
                continue
            md = statistics.median(prev)
            if md > 0 and val[i] / md >= 5:
                q = val[i] / md
                L.append({"k": "Montant échangé anormal", "sv": 3 if q >= 10 else 2, "d": d[i], "v": round(q, 1), "vl": f"× {q:.1f} la médiane 60 séances", "m": f"{val[i]:,.0f} échangés contre une médiane de {md:,.0f}".replace(",", " ")})
        # 3. écart extrême à la moyenne 200 séances (centiles sur 3 ans)
        if n > 260:
            dev = []
            sm = sum(c[:200])
            for i in range(200, n):
                if i > 200:
                    sm += c[i] - c[i - 200]
                dev.append(c[i] / (sm / 200) - 1)
            hist = sorted(dev[-756:-1])
            if len(hist) > 100:
                lo, hi = hist[int(len(hist) * .02)], hist[int(len(hist) * .98)]
                if dev[-1] > hi or dev[-1] < lo:
                    L.append({"k": "Écart de tendance extrême", "sv": 1, "d": d[-1], "v": round(dev[-1], 4), "vl": f"{dev[-1] * 100:+.1f} % de la moyenne 200", "m": f"cours {'au-dessus' if dev[-1] > 0 else 'au-dessous'} de sa moyenne 200 séances de {abs(dev[-1]) * 100:.1f} %, au-delà de {hi * 100 if dev[-1] > 0 else lo * 100:+.1f} % (centile {'98' if dev[-1] > 0 else '2'} sur 3 ans)"})
        # 4. cours figé, absence d'échange, trous de données (calendrier BRVM Composite)
        k = 0
        for i in range(n - 1, 0, -1):
            if c[i] == c[i - 1]:
                k += 1
            else:
                break
        if k >= 10:
            L.append({"k": "Cours figé", "sv": 2, "d": d[-1], "v": k, "vl": f"{k} séances", "m": f"cours inchangé depuis {k} séances cotées : prix peu informatif"})
        if brvm and cal_d:
            last_cal = cal_d[-1]
            gap = sum(1 for x in cal_d[-60:] if x > d[-1])
            if gap >= 5:
                L.append({"k": "Pas d'échange récent", "sv": 2, "d": d[-1], "v": gap, "vl": f"{gap} séances", "m": f"aucune transaction depuis {gap} séances (dernier cours le {i2d(d[-1]).strftime('%d/%m/%Y')}) : le cours affiché est ancien"})
            have = set(d[-400:])
            run = mx = 0
            for x in cal_d[-250:]:
                run = run + 1 if x not in have and x <= d[-1] else 0
                mx = max(mx, run)
            if mx >= 5:
                L.append({"k": "Trou de données", "sv": 1, "d": None, "v": mx, "vl": f"{mx} séances", "m": f"jusqu'à {mx} séances consécutives sans ligne de cotation sur un an (suspension ou absence d'échange)"})
        # 5. résultats et dividendes
        f = fa.get(sid) or {}
        ng = f.get("ni_g")
        if ng is not None and abs(ng) >= .5:
            L.append({"k": "Résultat : variation inhabituelle", "sv": 2 if abs(ng) >= 1 else 1, "d": None, "v": round(ng, 3), "vl": f"{ng * 100:+.0f} % sur un an", "m": f"résultat net {ng * 100:+.0f} % sur le dernier exercice : vérifier un élément exceptionnel"})
        if f.get("payout") is not None and f["payout"] > 1:
            L.append({"k": "Dividende supérieur au bénéfice", "sv": 2, "d": None, "v": round(f["payout"], 3), "vl": f"distribution {f['payout'] * 100:.0f} %", "m": "le dividende dépasse le résultat par action : prélevé sur les réserves, peu durable s'il se répète"})
        ys = collections.defaultdict(float)
        for x in by_dv.get(sid, []):
            if x.get("ex"):
                ys[int(x["ex"])] += x["dps"]
        yy = sorted(ys)
        if len(yy) >= 2 and yy[-1] - yy[-2] == 1 and ys[yy[-2]] > 0:
            ch = ys[yy[-1]] / ys[yy[-2]] - 1
            if abs(ch) >= .3:
                L.append({"k": "Dividende : variation inhabituelle", "sv": 2 if ch < 0 else 1, "d": None, "v": round(ch, 3), "vl": f"{ch * 100:+.0f} %", "m": f"dividende de l'exercice {yy[-1]} : {ys[yy[-1]]:g} contre {ys[yy[-2]]:g} ({ch * 100:+.0f} %)"})
        # 6. incohérences de données
        if s.get("per") and s.get("bnpa") and s.get("last"):
            pe2 = s["last"] / s["bnpa"]
            if pe2 > 0 and abs(s["per"] / pe2 - 1) > .15:
                L.append({"k": "Incohérence de données", "sv": 1, "d": None, "v": None, "m": f"PER publié {s['per']:.1f} contre cours ÷ BNPA = {pe2:.1f} : BNPA ou nombre de titres à vérifier"})
        if brvm and s.get("mcap") and s.get("shares") and s.get("last"):
            mc2 = s["shares"] * s["last"]
            if abs(s["mcap"] / mc2 - 1) > .05:
                L.append({"k": "Incohérence de données", "sv": 1, "d": None, "v": None, "m": f"capitalisation {s['mcap'] / 1e9:,.0f} Md contre titres × cours = {mc2 / 1e9:,.0f} Md".replace(",", " ")})
        if L:
            res[sid] = sorted(L, key=lambda a: (-a["sv"], -(a["d"] or 0)))
    fr = lambda t: re.sub(r"(\d)\.(\d)", r"\1,\2", t) if isinstance(t, str) else t  # noqa: E731  (décimales à la française)
    for L in res.values():
        for a in L:
            a["m"], a["vl"] = fr(a.get("m")), fr(a.get("vl"))
    jsave(os.path.join(out, "anomalies.json"), {"ts": int(_t.time()), "by": res})
    log("anomalies", sum(len(v) for v in res.values()), "alertes sur", len(res), "titres")


def derive(extra, out, files, secs, fund, fcf_path, dmeta, ndx, log):
    secs_by = {s["id"]: s for s in secs}
    us_ids = [s["id"] for s in secs if s["mkt"] == "US" and s["typ"] == "Equity"]
    brvm_ids = [s["id"] for s in secs if s["mkt"] == "BRVM" and s["cls"] == "Equity"]
    shares = {s["id"]: s.get("shares") for s in secs if s["mkt"] == "BRVM"}
    F = None
    for name, fn in (("eco", lambda: eco(extra, out, log) if extra else None),):
        try:
            F = fn()
        except Exception as e:  # noqa: BLE001
            log("échec", name, e)
    steps = [("fg", lambda: fg(extra, out, files, ndx, us_ids, brvm_ids, dmeta, shares, F, log)),
             ("liq", lambda: liq(out, files, secs_by, brvm_ids, log)),
             ("ee", lambda: ee(extra, out, secs_by, files, log)),
             ("fa", lambda: fundamentals(extra, out, files, secs_by, fund, fcf_path, dmeta, jload(os.path.join(extra, "analyst.json"), {}) if extra else {}, log)),
             ("per", lambda: per_brvm(extra, out, files, secs_by, fund, log)),
             ("uemoa", lambda: uemoa(extra, out, secs_by, None, log)),
             ("prof", lambda: profiles(extra, out, secs_by, log)),
             ("anom", lambda: anomalies(out, files, secs_by, log)),
             ("macro", lambda: [jsave(os.path.join(out, f), jload(os.path.join(extra, f))) for f in ("bceao.json", "umoa_curves.json", "eia_wpsr.json", "ei_oil.json") if extra and os.path.exists(os.path.join(extra, f))]),
             ("seed", lambda: [jsave(os.path.join(out, f), jload(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", f))) for f in ("geo_world.json", "chokepoints.json")])]
    for name, fn in steps:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            log("échec", name, e, traceback.format_exc()[-600:])
