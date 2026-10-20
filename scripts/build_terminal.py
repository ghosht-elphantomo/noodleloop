#!/usr/bin/env python3
"""Build the terminal's static data set (data/*.json) from public sources. Standard library only.

Sources
  US / Taiwan equities & ETFs : github.com/yennanliu/finance_data (Yahoo Finance daily, refreshed nightly)
  BRVM (48 stocks, 18 indices, fundamentals, dividends, official notices) : github.com/harzat/brvm-data-public
  Macro (gold, S&P 500, CPI, US 10Y, Brent, WTI, natural gas, VIX, FX) : github.com/datasets/*
  Same-day BRVM session (optional --session) : brvm.json written by scrape.py from brvm.org

Usage: build_terminal.py --brvm-src DIR --out DIR [--session brvm.json] [--cache DIR]
"""
import argparse, collections, copy, csv, datetime as dt, io, json, math, os, re, sys, time, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
YN = "https://raw.githubusercontent.com/yennanliu/finance_data/main/data/prices/{}.csv"
DS = "https://raw.githubusercontent.com/datasets/{}"
XOF_PER_EUR = 655.957

US = [  # ticker, name, type, group
    ("QQQ", "Invesco QQQ Trust", "ETF", "Indice"), ("VTI", "Vanguard Total Stock Market", "ETF", "Indice"),
    ("SOXX", "iShares Semiconductor", "ETF", "Semi-conducteurs"), ("SOXQ", "Invesco PHLX Semiconductor", "ETF", "Semi-conducteurs"),
    ("ROBO", "ROBO Global Robotics & Automation", "ETF", "Thématique"),
    ("NVDA", "NVIDIA", "Equity", "Semi-conducteurs"), ("AVGO", "Broadcom", "Equity", "Semi-conducteurs"),
    ("AMD", "Advanced Micro Devices", "Equity", "Semi-conducteurs"), ("TSM", "Taiwan Semiconductor ADR", "Equity", "Semi-conducteurs"),
    ("MU", "Micron Technology", "Equity", "Semi-conducteurs"), ("MRVL", "Marvell Technology", "Equity", "Semi-conducteurs"),
    ("INTC", "Intel", "Equity", "Semi-conducteurs"), ("WDC", "Western Digital", "Equity", "Matériel"), ("SNDK", "Sandisk", "Equity", "Matériel"),
    ("MSFT", "Microsoft", "Equity", "Logiciel"), ("ORCL", "Oracle", "Equity", "Logiciel"), ("PLTR", "Palantir Technologies", "Equity", "Logiciel"),
    ("GOOG", "Alphabet (C)", "Equity", "Communication"), ("META", "Meta Platforms", "Equity", "Communication"),
    ("AMZN", "Amazon.com", "Equity", "Conso. discrétionnaire"), ("TSLA", "Tesla", "Equity", "Automobile"),
    ("UBER", "Uber Technologies", "Equity", "Transport"), ("GRAB", "Grab Holdings", "Equity", "Transport"),
    ("SOFI", "SoFi Technologies", "Equity", "Finance"), ("NU", "Nu Holdings", "Equity", "Finance"),
    ("VST", "Vistra", "Equity", "Énergie"), ("IONQ", "IonQ", "Equity", "Quantique"), ("RKLB", "Rocket Lab", "Equity", "Spatial & défense"),
    ("PL", "Planet Labs", "Equity", "Spatial & défense"), ("KTOS", "Kratos Defense", "Equity", "Spatial & défense"),
    ("AVAV", "AeroVironment", "Equity", "Spatial & défense"), ("ONDS", "Ondas Holdings", "Equity", "Spatial & défense"),
    ("NBIS", "Nebius Group", "Equity", "Logiciel"),
]
TW = [("0050", "0050", "Yuanta Taiwan Top 50", "ETF", "Indice"), ("2330.tw", "2330", "TSMC (Taïwan)", "Equity", "Semi-conducteurs")]
CTY = {"B": "BJ", "BF": "BF", "C": "CI", "M": "ML", "N": "NE", "S": "SN", "T": "TG"}
CTY_NAME = {"CI": "Côte d'Ivoire", "SN": "Sénégal", "BF": "Burkina Faso", "BJ": "Bénin", "ML": "Mali", "NE": "Niger", "TG": "Togo"}


def log(*a):
    print("[build]", *a, flush=True)


def fetch(url, cache=None, tries=3):
    path = os.path.join(cache, re.sub(r"[^A-Za-z0-9._-]", "_", url)[-120:]) if cache else None
    if path and os.path.exists(path) and time.time() - os.path.getmtime(path) < 6 * 3600:
        return open(path, "rb").read()
    err = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                b = r.read()
            if path:
                os.makedirs(cache, exist_ok=True)
                open(path, "wb").write(b)
            return b
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(2 + 3 * k)
    raise err


def di(s):  # 'YYYY-MM-DD' or 'DD/MM/YYYY' or 'YYYY-MM' -> int YYYYMMDD
    s = s.strip().lstrip("﻿")
    if "/" in s:
        d, m, y = s.split("/")
        return int(y) * 10000 + int(m) * 100 + int(d)
    p = s.split("-")
    return int(p[0]) * 10000 + int(p[1]) * 100 + (int(p[2]) if len(p) > 2 else 1)


def fnum(x):
    x = (x or "").replace("\xa0", "").replace(" ", "").replace(" ", "").replace("%", "").replace(",", ".").strip()
    if x in ("", "-", "nan", "null"):
        return None
    try:
        return float(x)
    except ValueError:
        return None


def rnd(v, nd):
    return None if v is None or (isinstance(v, float) and not math.isfinite(v)) else round(v, nd)


# ------------------------------------------------------------------ loaders
def is_wkend(d):
    """Samedi ou dimanche (date entière AAAAMMJJ)."""
    return dt.date(d // 10000, d // 100 % 100, d % 100).weekday() >= 5


def load_yn(sym, cache, text=None):
    """Actions et ETF US et Taïwan (Yahoo, jeu yennanliu). Les lignes datées d'un samedi ou d'un dimanche sont écartées : séance
    fantôme de la source (0050 et 2330 le dimanche 20/09/2026, clôture recopiée de la veille et plus haut à +10 % qui faussait le
    plus haut sur 52 semaines) ; aucune séance réelle n'a lieu le week-end sur ces marchés (les samedis de rattrapage de Taïwan
    sont des jours de règlement sans cotation). Un éventuel dividende porté par une ligne écartée passe à la séance suivante."""
    rows, carry = [], 0
    for r in csv.DictReader(io.StringIO(text if text is not None else fetch(YN.format(sym), cache).decode("utf8"))):
        c = fnum(r.get("close"))
        if not c:
            continue
        d_ = di(r["date"])
        if is_wkend(d_):
            carry += fnum(r.get("div")) or 0
            continue
        rows.append((d_, fnum(r["open"]) or c, fnum(r["high"]) or c, fnum(r["low"]) or c, c, int(fnum(r["volume"]) or 0), (fnum(r.get("div")) or 0) + carry))
        carry = 0
    return rows


def us_div_place(dates, rows, spl, max_days=7):
    """Dividendes US (Nasdaq : [détachement AAAA-MM-JJ, montant, paiement]) placés sur une série à la date de détachement.
    Un détachement un jour sans cotation passe à la première séance suivante, à 7 jours au plus (sinon ignoré). Un détachement
    antérieur à la première séance de la série est ignoré : auparavant, tous ces dividendes étaient cumulés sur la première
    séance (AEP 24,13 $ = 41 trimestres, KDP 117,47 $ = 529 % du cours) et listés comme un seul versement. Renvoie (div, nombre placé)."""
    import bisect
    div, n = [0] * len(dates), 0
    idx = {d: i for i, d in enumerate(dates)}
    for d_, amt, _pay in rows:
        try:
            k = di(d_)
        except Exception:  # noqa: BLE001
            continue
        for sd, ratio in spl:  # montant nominal de l'époque ramené à la base d'actions actuelle (cours déjà ajustés)
            if sd > d_:
                amt = amt / ratio
        i = idx.get(k)
        if i is None:  # détachement un jour sans cotation dans la série : première séance suivante, à 7 jours au plus
            j = bisect.bisect_left(dates, k)
            if not dates or k < dates[0] or j >= len(dates):
                continue
            k_d, n_d = dt.date(k // 10000, k // 100 % 100, k % 100), dt.date(dates[j] // 10000, dates[j] // 100 % 100, dates[j] % 100)
            if (n_d - k_d).days > max_days:
                continue
            i = j
        div[i] = round(div[i] + amt, 4)
        n += 1
    return div, n


# volume du relevé tiré d'un autre contrat que celui de la série : jamais greffé (BRENT : volume ICE de CNBC sur la série
# Yahoo BZ=F du contrat NYMEX, ×7,5)
VOL_OTHER = {"BRENT"}


def vol_ok(hist, x):
    """Volume du jour vraisemblable face aux séances précédentes (hist, la plus récente en dernier) : au plus 5 fois la médiane
    des 60 dernières séances (QQQ 490,8 M, somme des barres de 5 min, contre 45,9 M) et différent de plus de 0,1 % du volume de
    la séance précédente (volume de la veille resservi par la source : AAPL 59 946 370 puis 59 946 749)."""
    if not x or x <= 0:
        return False
    nz = [y for y in (hist or [])[-60:] if y]
    if len(nz) >= 20:
        import statistics
        if x > 5 * statistics.median(nz):
            return False
    p = (hist or [None])[-1]
    return not (p and abs(x - p) / p <= 0.001)


def graft_quote(sid, qt, d, c, o=None, h=None, l=None, v=None, div=None, val=None):
    """Cours du jour (quotes.json) greffé sur une série : nouvelle séance ajoutée ou dernière séance mise à jour.
    Bougie toujours cohérente : plus haut = max(ouverture, cours, plus haut relevé), plus bas = min(ouverture, cours, plus bas
    relevé) (Nasdaq ne donne ni plus haut ni plus bas : la bougie était H = L = C avec une ouverture hors fourchette, et CNBC
    renvoie 0 après le règlement) ; volume greffé seulement s'il est vraisemblable (vol_ok), sinon 0 (inconnu) ou celui de la source."""
    k = di(qt["d"])
    if k > d[-1]:
        # cotation à plus de 4 jours ouvrés de la dernière séance de la série (source arrêtée : change Fed H.10 au 09/10, cotation
        # du 19/10) : pas accolée, la variation et les rendements du résumé porteraient sur plusieurs séances (la page applique
        # elle-même la cotation, avec sa propre clôture précédente)
        a_ = dt.date(d[-1] // 10000, d[-1] // 100 % 100, d[-1] % 100)
        n_ = (dt.date(k // 10000, k // 100 % 100, k % 100) - a_).days
        if sum(1 for i in range(1, n_ + 1) if (a_ + dt.timedelta(days=i)).weekday() < 5) > 4:
            return d, c, o, h, l, v, div, val
    d, c = list(d), list(c)
    o, h, l = (list(o), list(h), list(l)) if o else (None, None, None)
    v = list(v) if v else v
    # clôture du jour confirmée (relevé après 16 h) plutôt que le dernier cours de l'après-bourse : la série garde la clôture
    px_ = qt.get("cl") or qt["last"]
    pos = lambda x: x if isinstance(x, (int, float)) and x > 0 else None  # noqa: E731
    qv = int(qt.get("vol") or 0) if sid not in VOL_OTHER else 0
    if k > d[-1]:
        o_ = pos(qt.get("o")) or c[-1]
        d.append(k)
        c.append(px_)
        if o:
            o.append(o_)
            h.append(max(x for x in (o_, px_, pos(qt.get("h"))) if x))
            l.append(min(x for x in (o_, px_, pos(qt.get("l"))) if x))
        if v is not None:
            v.append(qv if vol_ok(v, qv) else 0)
        if div is not None:
            div = list(div) + [0]
        if val is not None:
            val = list(val) + [0]
    elif k == d[-1]:
        c[-1] = px_
        if o:
            h[-1] = max(x for x in (h[-1], o[-1], px_, pos(qt.get("h"))) if x)
            l[-1] = min(x for x in (l[-1], o[-1], px_, pos(qt.get("l"))) if x)
        if v is not None and vol_ok(v[:-1], qv):
            v[-1] = qv
    return d, c, o, h, l, v, div, val


def trailing_yield(d, div, last):
    """Rendement sur 12 mois = dividendes détachés dans l'année calendaire écoulée (]dernière séance − 1 an ; dernière séance]) ÷
    dernier cours, arrondi à 5 décimales comme pour la BRVM. None si la série couvre moins d'un an ou n'a aucun dividende sur ces
    12 mois (jamais 0 inventé)."""
    d, div = d or [], div or []
    if len(d) < 2 or len(div) != len(d) or not last or last <= 0:
        return None
    e_ = dt.date(d[-1] // 10000, d[-1] // 100 % 100, d[-1] % 100)
    try:
        y0 = e_.replace(year=e_.year - 1)
    except ValueError:  # 29 février
        y0 = e_ - dt.timedelta(days=365)
    y0i = y0.year * 10000 + y0.month * 100 + y0.day
    if d[0] > y0i:
        return None  # série de moins d'un an
    tot = sum(x for dd, x in zip(d, div) if dd > y0i and x)
    return rnd(tot / last, 5) if tot > 0 else None


def fred_csv(extra, sid):
    """Série FRED du dossier brut écrit par fetch_extra.py (fred/<id>.csv) : [(AAAAMMJJ, valeur)] ; [] si absente."""
    p = os.path.join(extra, "fred", sid + ".csv") if extra else None
    out = []
    if p and os.path.exists(p):
        with open(p, encoding="utf8") as f:
            for r in csv.reader(f):
                try:
                    out.append((int(r[0][:10].replace("-", "")), float(r[1])))
                except (ValueError, IndexError):
                    continue  # (en-tête, valeurs manquantes « . »)
    return out


def monthly_avg(daily, min_obs=15):
    """Moyenne mensuelle d'une série quotidienne, datée du 1er du mois ; le mois en cours (dernier mois de la série) et les mois de
    moins de min_obs observations sont exclus : une moyenne partielle n'est jamais publiée comme celle du mois."""
    by = {}
    for d_, v_ in daily:
        by.setdefault(d_ // 100, []).append(v_)
    ms = sorted(by)[:-1]
    return [(m * 100 + 1, round(sum(by[m]) / len(by[m]), 4)) for m in ms if len(by[m]) >= min_obs]


def fred_extend(s, fred, rel=None, absol=None, min_ov=6):
    """Série mensuelle s ([(AAAAMMJJ, v)]) prolongée par les mois FRED postérieurs à son dernier point, seulement si les deux
    sources concordent sur les 12 derniers mois communs (au moins min_ov) : écart relatif ≤ rel ou absolu ≤ absol."""
    if not s or not fred:
        return s
    fm, have = dict(fred), dict(s)
    ov = [k for k in sorted(have) if k in fm][-12:]
    if len(ov) < min_ov:
        return s
    for k in ov:
        if (rel is not None and abs(have[k] / fm[k] - 1) > rel) or (absol is not None and abs(have[k] - fm[k]) > absol):
            return s
    return list(s) + [(k, v) for k, v in sorted(fm.items()) if k > s[-1][0]]


def load_brvm_csv(path):
    """harzat CSVs: real column order is Date;Close;Open;High;Low;Shares;Value;Var (header says otherwise)."""
    rows = {}
    with open(path, encoding="utf-8-sig") as f:
        next(f, None)
        for line in f:
            p = line.rstrip("\n").split(";")
            if len(p) < 5:
                continue
            try:
                d = di(p[0])
            except Exception:  # noqa: BLE001
                continue
            c, o, h, l = fnum(p[1]), fnum(p[2]), fnum(p[3]), fnum(p[4])
            if not c or c <= 0:
                continue
            vals = [x for x in (c, o, h, l) if x]
            o = o or c
            rows[d] = (d, o, max(vals), min(vals), c, int(fnum(p[5]) or 0) if len(p) > 5 else 0, int(fnum(p[6]) or 0) if len(p) > 6 else 0)
    return [rows[k] for k in sorted(rows)]


def series_from_csv(text, date_col, val_col, filt=None):
    out = {}
    for r in csv.DictReader(io.StringIO(text)):
        if filt and not filt(r):
            continue
        v = fnum(r.get(val_col))
        if v is None or v <= 0:
            continue
        out[di(r[date_col])] = v
    return sorted(out.items())


# ------------------------------------------------------------------ metrics
def stats_block(d, c, freq="D", h=None, l=None, v=None, val=None, ann=None):
    n = len(c)
    per_year = ann or (252 if freq == "D" else 12)
    last, prev = c[-1], c[-2] if n > 1 else c[-1]

    def back(k):
        return c[-1 - k] if n > k else None

    # séries quotidiennes : périodes calendaires (1 semaine, 1 mois = même jour du mois précédent, 3 et 6 mois, 1 et 3 ans), comme le
    # terminal Bloomberg ; cours de référence = dernière clôture à cette date ou avant (moins de 10 jours d'écart, sinon pas de
    # rendement). Un titre suspendu ou récemment coté n'a ainsi jamais une « performance 1 an » calculée sur une autre durée.
    dd_ = [dt.date(x // 10000, x // 100 % 100, x % 100) for x in d] if freq == "D" else None

    def back_d(months=0, days=0):
        e = dd_[-1]
        if months:
            y_, m_ = divmod(e.month - 1 - months, 12)
            y_, m_ = e.year + y_, m_ + 1
            import calendar
            t = dt.date(y_, m_, min(e.day, calendar.monthrange(y_, m_)[1]))
        else:
            t = e - dt.timedelta(days=days)
        import bisect
        i = bisect.bisect_right(dd_, t) - 1
        return c[i] if i >= 0 and (t - dd_[i]).days <= 10 and c[i] else None

    def ret(k):
        if freq == "D":
            b = back_d(*k) if isinstance(k, tuple) else None
        else:
            b = back(k)
        return (last / b - 1) if b else None
    wk, mo, q, yr, y3 = ((0, 7), (1,), (3,), (12,), (36,)) if freq == "D" else (None, 1, 3, 12, 36)
    h6 = (6,) if freq == "D" else 6
    ly = d[-1] // 10000 - 1
    base = None
    for i in range(n - 1, -1, -1):
        if d[i] // 10000 <= ly:
            base = c[i]
            break
    # fenêtre d'un an : calendaire pour les séries quotidiennes (volatilité, plus haut et plus bas sur 52 semaines)
    i0 = max(0, n - per_year)
    if freq == "D":
        import bisect
        e_ = dd_[-1]
        try:
            t1 = e_.replace(year=e_.year - 1)
        except ValueError:
            t1 = e_ - dt.timedelta(days=365)
        i0 = bisect.bisect_right(dd_, t1)
    # (volatilité « 1 an » seulement si la série couvre l'année entière : un titre coté depuis quelques semaines n'en a pas)
    full_y = freq != "D" or dd_[0] <= t1
    lr = [math.log(c[i] / c[i - 1]) for i in range(max(1, i0), n) if c[i - 1] > 0 and c[i] > 0]
    mu = sum(lr) / len(lr) if lr else 0
    sd = math.sqrt(sum((x - mu) ** 2 for x in lr) / max(1, len(lr) - 1)) if len(lr) > 2 else 0
    hs_ = [x for x in (h or c)[i0:] if x]
    ls_ = [x for x in (l or c)[i0:] if x]
    hi = max(hs_) if hs_ else last
    lo = min(ls_) if ls_ else last
    sma = lambda k: sum(c[-k:]) / k if n >= k else None  # noqa: E731
    # RSI 14 de Wilder (moyennes lissées, comme le terminal Bloomberg) sur les 300 dernières séances
    rsi = None
    if n > 15:
        cc_ = c[-301:]
        ch_ = [cc_[i] - cc_[i - 1] for i in range(1, len(cc_))]
        ag = sum(max(x, 0) for x in ch_[:14]) / 14
        al = sum(max(-x, 0) for x in ch_[:14]) / 14
        for x in ch_[14:]:
            ag = (ag * 13 + max(x, 0)) / 14
            al = (al * 13 + max(-x, 0)) / 14
        rsi = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    peak = max(c)
    return {"last": rnd(last, 4), "prev": rnd(prev, 4), "pct": rnd(last / prev - 1 if prev else 0, 6), "dt": d[-1], "first": d[0], "nobs": n,
            "r1w": rnd(ret(wk), 5) if wk else None, "r1m": rnd(ret(mo), 5), "r3m": rnd(ret(q), 5), "r6m": rnd(ret(h6), 5), "r1y": rnd(ret(yr), 5), "r3y": rnd(ret(y3), 5),
            "ytd": rnd(last / base - 1, 5) if base else None, "vol": rnd(sd * math.sqrt(per_year), 5) if full_y else None, "hi52": rnd(hi, 4), "lo52": rnd(lo, 4),
            "sma50": rnd(sma(50), 4) if freq == "D" else None, "sma200": rnd(sma(200), 4) if freq == "D" else None, "rsi": rnd(rsi, 2),
            "ath": rnd(peak, 4), "dd": rnd(last / peak - 1, 5), "spark": [rnd(x, 4) for x in c[-60:]],
            "liq": rnd(sum(val[-63:]) / len(val[-63:]), 0) if val and any(val[-63:]) else (rnd(sum(a * b for a, b in zip(v[-63:], c[-63:])) / len(v[-63:]), 0) if v and any(v[-63:]) else None),
            "vday": (val[-1] if val else None) or (rnd(v[-1] * c[-1], 0) if v else None), "shd": v[-1] if v else None}


def weekly(d, c):
    """Friday (week-ending) closes keyed by ISO week end date."""
    out = {}
    for di_, ci in zip(d, c):
        t = dt.date(di_ // 10000, di_ // 100 % 100, di_ % 100)
        fri = t + dt.timedelta(days=(4 - t.weekday()) % 7)
        out[fri.year * 10000 + fri.month * 100 + fri.day] = ci
    return out


def beta_corr(x, y):
    n = len(x)
    if n < 20:
        return None, None
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx <= 0 or syy <= 0:
        return None, None
    return sxy / syy, sxy / math.sqrt(sxx * syy)  # beta of x on y, correlation


# ------------------------------------------------------------------ main
def _nm(x):
    import unicodedata
    x = unicodedata.normalize("NFKD", x or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", x.replace("&", " ")).strip()


AV_GENERIC = re.compile(r"^(avis|brvm|rappel|communique|annonce|bourse regionale)( |$)")


def brvm_avis(items, ev_src, acts, out):
    """Avis lus directement sur brvm.org (secours de la base tierce) : rattachés à un titre par le nom de société tel que brvm.org l'écrit
    (noms appris de la base d'avis, du registre des titres et des pages des sociétés). Renvoie (avis, nombre de sociétés non rattachées)."""
    m = collections.defaultdict(collections.Counter)
    for x in ev_src:
        t, ti = x.get("ticker"), x.get("title") or ""
        if t:
            for k in (x.get("issuer"), x.get("company"), ti.split(" : ")[0] if " : " in ti else None):
                if k and not AV_GENERIC.match(_nm(k)):
                    m[_nm(k)][t] += 1
    for a_ in acts:
        for k in (a_.get("nom"), a_.get("nom_officiel"), a_.get("ticker")):
            if k:
                m[_nm(k)][a_["ticker"]] += 3
    rp = os.path.join(out, "reports.json")
    if os.path.exists(rp):
        for x in (json.load(open(rp, encoding="utf8")).get("issuers") or {}).values():
            if x.get("t") and x.get("n"):
                m[_nm(x["n"])][x["t"]] += 1
    tick = {a_["ticker"] for a_ in acts if a_.get("actif", True) is not False}  # titres radiés exclus

    def find(*names):
        for n in names:
            k = _nm(n)
            if k and k in m and not AV_GENERIC.match(k):
                t_ = m[k].most_common(1)[0][0]
                return t_ if t_ in tick else None  # actions cotées seulement (pas d'obligations, d'États ni de sociétés radiées)
        for n in names:  # ticker cité entre parenthèses, ex. « (BBGC) »
            x = re.search(r"\(([A-Z]{4,5})\)", n or "")
            if x and x.group(1) in tick:
                return x.group(1)
        return None
    res, nomap = [], set()
    for u, r in items.items():
        t = find(r.get("soc"), (r.get("ti") or "").split(" : ")[0] if " : " in (r.get("ti") or "") else None)
        if r.get("soc") and not t:
            nomap.add(r["soc"])
        res.append({**r, "u": u, "t": t})
    return res, nomap


BASE_ITEMS = {"tresorerie": ("tresorerie_actif", "tresorerie_passif"), "dette_nette": ("dettes_financieres", "tresorerie_actif", "tresorerie_passif")}


def base_fix(fund):
    """Trésorerie nette, dette nette, dépôts et crédits de la base tierce (chiffres clés des sociétés) contrôlés exercice par exercice.

    Avec les comptes publiés et vérifiés de la société (cpt, référentiel SYSCOHADA) : trésorerie nette = trésorerie actif - trésorerie
    passif ; dette nette = dettes financières + trésorerie passif - trésorerie actif. Le montant de la base est remplacé par celui des
    comptes publiés quand :
      1. la base suit cette définition au moins trois autres exercices (à 1 % près, postes vérifiés) et s'en écarte cet exercice ;
      2. ou le montant de la base est celui des comptes au signe près (signe inversé), la définition étant suivie au moins une autre année ;
      3. ou le montant de la base est isolé (loin de ses deux voisins) alors que celui des comptes, lu dans au moins deux documents, est
         dans la continuité des années voisines.
    Ensuite, une trésorerie, une dette nette, des dépôts ou des crédits plus grands en valeur absolue que le total du bilan de la même
    année (total lui-même cohérent avec les années voisines) ne peuvent pas exister : retirés plutôt qu'affichés faux.
    Le ratio d'endettement de la base d'un exercice dont la dette nette change est retiré. Rend la liste des changements."""
    import statistics

    def ent(cc, y):
        yy = (cc or {}).get("y") or {}
        return yy.get(y) or yy.get(str(y)) or (yy.get(int(y)) if str(y).isdigit() else None) or {}

    def derived(k, e, strict):
        v, w = e.get("v") or {}, set(e.get("w") or [])
        need = BASE_ITEMS[k] if strict else BASE_ITEMS[k][:-1]
        if any(v.get(i) is None for i in need) or (strict and any(i in w for i in BASE_ITEMS[k])):
            return None
        if k == "tresorerie":
            return v["tresorerie_actif"] - (v.get("tresorerie_passif") or 0)
        return v["dettes_financieres"] + (v.get("tresorerie_passif") or 0) - v["tresorerie_actif"]

    def close(a, b):
        return abs(a - b) <= max(1.0, abs(b) * .01)
    out = []
    for t, f in fund.items():
        if t == "_meta" or not isinstance(f, dict):
            continue
        ser = f.get("series") or {}
        tb = {str(k): v for k, v in (ser.get("total_bilan") or {}).items() if isinstance(v, (int, float)) and v > 0}
        cc = f.get("cpt")
        if cc and cc.get("std") == "syscohada":
            for k in BASE_ITEMS:
                o = ser.get(k)
                if not isinstance(o, dict):
                    continue
                S_ = {y: derived(k, ent(cc, y), True) for y in o}
                L_ = {y: derived(k, ent(cc, y), False) for y in o}
                orig = dict(o)
                for y, x in orig.items():
                    if not isinstance(x, (int, float)):
                        continue
                    others = [(y2, x2) for y2, x2 in orig.items() if y2 != y and isinstance(x2, (int, float))]
                    conf_s = sum(1 for y2, x2 in others if S_[y2] is not None and close(S_[y2], x2))
                    conf_l = sum(1 for y2, x2 in others if L_[y2] is not None and close(L_[y2], x2))
                    cs, cl, new, why = S_[y], L_[y], None, None
                    if cs is not None and not close(cs, x) and conf_s >= 3:
                        new, why = cs, "définition de la base confirmée par les comptes"
                    elif cl is not None and not close(cl, x) and abs(x + cl) <= max(1.0, abs(cl) * .005) and conf_l >= 1:
                        new, why = cl, "signe inversé"
                    elif cs is not None and (ent(cc, y).get("n") or 0) >= 2 and str(y).isdigit():
                        nb = [orig[y2] for y2 in (str(int(y) - 1), str(int(y) + 1)) if isinstance(orig.get(y2), (int, float))]
                        if nb:
                            m, fl = statistics.median(nb), .01 * tb.get(str(y), 0)
                            if abs(x - cs) > .5 * max(abs(cs), fl, 1.0) and abs(x - m) > 2.5 * max(abs(cs - m), fl, 1.0):
                                new, why = cs, "montant isolé contredit par les comptes"
                    if new is not None:
                        o[y] = round(new, 1)
                        if k == "dette_nette":
                            (ser.get("ratio_endettement_net") or {}).pop(y, None)
                        out.append(f"{t} {y} {k} {x:g} -> {o[y]:g} ({why})")
        for k in ("tresorerie", "dette_nette", "depots_clientele", "credits_clientele"):
            o = ser.get(k)
            if not isinstance(o, dict):
                continue
            for y in list(o):
                x, b = o.get(y), tb.get(str(y))
                if not isinstance(x, (int, float)) or not b or abs(x) <= 1.02 * b:
                    continue
                nb = [tb[str(int(y) + d)] for d in (-1, 1) if str(y).isdigit() and str(int(y) + d) in tb]
                if nb and not all(b / 3 <= z <= b * 3 for z in nb):
                    continue  # total du bilan lui-même douteux : rien n'est touché
                o.pop(y)
                if k == "dette_nette":
                    (ser.get("ratio_endettement_net") or {}).pop(y, None)
                out.append(f"{t} {y} {k} {x:g} -> retiré (plus grand que le total du bilan {b:g})")
    return out


def load_corr():
    """Corrections vérifiées sur document (seed/corrections_bnpa.json). Une ligne : titre « t », exercice « ex », champ « champ »
    (poste de la série, « bnpa » par défaut ; ou poste des comptes lus si « cpt » est donné), valeur fautive « avant » (null : poste
    absent), valeur corrigée « apres » (« bnpa » dans les premières lignes ; null : valeur retirée, affichée « — »), document « doc »
    et raison « pourquoi » ; « cpt » = « périmètre/norme » des comptes lus visés (ex. « social/syscohada ») ; « src » = mention de
    l'exercice dans FA. Une correction ne s'applique que si la valeur en place est encore « avant » (sinon signalée à revoir)."""
    try:
        p_ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", "corrections_bnpa.json")
        return json.load(open(p_, encoding="utf8")).get("rows") or []
    except Exception as e:  # noqa: BLE001
        log("corrections vérifiées illisibles :", e)
        return []


def corr_new(c_):
    return c_["apres"] if "apres" in c_ else c_.get("bnpa")


def corr_same(x, y):
    """même valeur, à l'arrondi de lecture près (ou toutes deux absentes)"""
    if x is None or y is None:
        return x is None and y is None
    return abs(x - y) <= max(.02, abs(y) * .001)


def cpt_fix(cons, rows):
    """Postes des comptes lus (comptes.consolidate) corrigés d'après le document cité : lignes de corrections_bnpa.json qui portent
    « cpt » (« périmètre/norme » visé : comptes principaux ou autre référentiel du titre). Un poste corrigé est sûr (prouvé par le
    document) : il quitte la liste des montants « faibles » (w, calc) et remplace donc ensuite le montant de la base tierce dans la
    série. Rend (corrections faites, corrections à revoir, {(titre, exercice, poste)} corrigés)."""
    done, skip, keys = [], [], set()
    for c_ in rows:
        if not c_.get("cpt") or not c_.get("champ"):
            continue
        try:
            per_, std_ = c_["cpt"].split("/")
            cc_ = cons.get(c_["t"]) or {}
            g_ = next((g for g in (cc_, cc_.get("alt") or {}) if g.get("per") == per_ and g.get("std") == std_), None)
            yy_ = (g_ or {}).get("y") or {}
            e_ = yy_.get(int(c_["ex"])) if int(c_["ex"]) in yy_ else yy_.get(str(c_["ex"]))
            lab_ = f'{c_["t"]} {c_["ex"]} {c_["champ"]} ({c_["cpt"]})'
            if e_ is None:
                skip.append(lab_ + " : exercice absent")
                continue
            v_, k_, new_ = e_["v"], c_["champ"], corr_new(c_)
            if not corr_same(v_.get(k_), c_.get("avant")):
                if not corr_same(v_.get(k_), new_):
                    skip.append(f"{lab_} : {v_.get(k_)}")
                continue
            if new_ is None:
                v_.pop(k_, None)
            else:
                v_[k_] = new_
            for kw_ in ("w", "calc"):
                if k_ in (e_.get(kw_) or []):
                    e_[kw_] = [x for x in e_[kw_] if x != k_]
                    if not e_[kw_]:
                        e_.pop(kw_)
            done.append(f'{lab_} {c_.get("avant")} -> {new_}')
            keys.add((c_["t"], str(c_["ex"]), k_))
        except Exception as e:  # noqa: BLE001  (une ligne mal formée est écartée, les suivantes restent appliquées)
            skip.append(f'{c_.get("t")} {c_.get("ex")} : ligne illisible ({type(e).__name__})')
    return done, skip, keys


# ratios de la base tierce qui dépendent d'un chiffre clé de la série : retirés (recalculés dans FA) quand une correction vérifiée
# change ce chiffre ; les autres ratios du même exercice restent (le coût du risque n'entre dans aucun)
CORR_DEP = {"capitaux_propres": ("roe",), "total_bilan": ("roa",), "resultat_net": ("roe", "roa", "marge_nette", "croissance_resultat_net"),
            "ca": ("marge_nette", "marge_exploitation", "croissance_ca"), "ebit": ("marge_exploitation",), "cout_du_risque": ()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brvm-src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--session", default=None, help="brvm.json from scrape.py (same-day official BRVM values)")
    ap.add_argument("--cache", default=None)
    ap.add_argument("--extra", default=None, help="dossier brut écrit par fetch_extra.py (branche quant-raw)")
    ap.add_argument("--fcf", default=None, help="history/fcf.json : flux de trésorerie BRVM lus dans les états financiers")
    ap.add_argument("--quotes", default=None, help="quotes.json du relevé (cours du jour appliqués à toutes les séries)")
    ap.add_argument("--live", action="store_true", help="passage de séance : séries existantes non réécrites, tous les calculs refaits")
    ap.add_argument("--boc", default=None, help="dossier boc_px (branche boc) : tableaux des actions lus dans les bulletins officiels de la cote")
    ap.add_argument("--dividendes", default=None, help="dividendes.json (branche dividendes) : versements lus dans les avis et calendriers de la BRVM")
    ap.add_argument("--comptes", default=None, help="comptes.json (branche comptes) : états financiers publiés à la BRVM, lus et vérifiés")
    ap.add_argument("--search-src", default=None, help="listes de documents des branches comptes et dividendes (index de la recherche MOTS CLES)")
    a = ap.parse_args()
    QUOTES = {}
    if a.quotes and os.path.exists(a.quotes):
        try:
            QUOTES = (json.load(open(a.quotes, encoding="utf8")) or {}).get("q") or {}
        except Exception:  # noqa: BLE001
            QUOTES = {}
    out, sdir = a.out, os.path.join(a.out, "s")
    os.makedirs(sdir, exist_ok=True)
    secs, files = [], {}

    def add(meta, d, c, o=None, h=None, l=None, v=None, val=None, div=None, freq="D", nd=2, ann=None, replace=False):
        sid = meta["id"]
        if replace and sid in files:
            secs[:] = [x for x in secs if x["id"] != sid]
        qt = QUOTES.get(sid) if freq == "D" and meta.get("mkt") != "BRVM" else None
        if qt and qt.get("last") and qt.get("d") and d:
            # cours du jour (Nasdaq, Coinbase, CNBC) : nouvelle séance ajoutée ou dernière séance mise à jour
            d, c, o, h, l, v, div, val = graft_quote(sid, qt, d, c, o, h, l, v, div, val)
        body = {"id": sid, "f": freq, "d": d, "c": [rnd(x, nd) for x in c]}
        if o:
            body.update(o=[rnd(x, nd) for x in o], h=[rnd(x, nd) for x in h], l=[rnd(x, nd) for x in l])
        if v and any(v):
            body["v"] = v
        if val and any(val):
            body["val"] = val
        if div and any(div):
            body["div"] = [rnd(x, 4) for x in div]
        files[sid] = body
        st = stats_block(d, c, freq, h, l, v, val, ann)
        secs.append({**meta, "f": freq, **st})

    # US & Taiwan -----------------------------------------------------------
    for sym, name, typ, grp in US:
        try:
            r = load_yn(sym.lower(), a.cache)
        except Exception as e:  # noqa: BLE001
            log("skip", sym, e)
            continue
        add({"id": sym, "tk": f"{sym} US", "n": name, "cls": "Equity", "typ": typ, "mkt": "US", "grp": grp, "ccy": "USD", "bench": "QQQ"},
            [x[0] for x in r], [x[4] for x in r], [x[1] for x in r], [x[2] for x in r], [x[3] for x in r], [x[5] for x in r], div=[x[6] for x in r])
    for f, sym, name, typ, grp in TW:
        try:
            r = load_yn(f, a.cache)
        except Exception as e:  # noqa: BLE001
            log("skip", sym, e)
            continue
        add({"id": sym, "tk": f"{sym} TT", "n": name, "cls": "Equity", "typ": typ, "mkt": "TW", "grp": grp, "ccy": "TWD", "bench": "0050"},
            [x[0] for x in r], [x[4] for x in r], [x[1] for x in r], [x[2] for x in r], [x[3] for x in r], [x[5] for x in r], div=[x[6] for x in r])

    # BRVM ------------------------------------------------------------------
    src = a.brvm_src
    acts = json.load(open(os.path.join(src, "actions.json"), encoding="utf8"))["actions"]
    # fiche des sociétés gardée par FQT (seed/societes.json : nom court, nom officiel, banque ou non) : prise en premier, la base
    # tierce ne sert qu'en secours (titre absent du fichier) ; les écarts entre les deux sont publiés pour le contrôle du matin
    SOC_DIFF, SOC_NEW = [], []
    try:
        soc_ = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", "societes.json"), encoding="utf8")).get("rows") or {}
    except Exception as e:  # noqa: BLE001
        soc_ = {}
        log("fiche des sociétés FQT illisible :", e)
    for act_ in acts:
        s_ = soc_.get(act_.get("ticker")) if soc_ else None
        if soc_ and not s_:
            SOC_NEW.append(act_.get("ticker"))
            continue
        for k_ in ("nom", "nom_officiel", "banque") if s_ else ():
            if s_.get(k_) is None:
                continue
            b_ = bool(act_.get(k_)) if k_ == "banque" else act_.get(k_)
            if b_ is not None and b_ != s_[k_]:
                SOC_DIFF.append(f"{act_.get('ticker')} {k_} : base « {b_} », FQT « {s_[k_]} »")
            act_[k_] = s_[k_]
    if SOC_DIFF or SOC_NEW:
        log("fiche des sociétés : écarts avec la base", len(SOC_DIFF), "; titres absents du fichier FQT :", ", ".join(SOC_NEW) or "aucun")
    # secteur officiel de la BRVM (sept pages par secteur de brvm.org, lues chaque soir) : source principale du secteur affiché,
    # la fiche ne sert que si la BRVM ne classe pas le titre (décision du propriétaire, 19/10/2026)
    SECT_OFF = {}
    try:
        sp0_ = os.path.join(a.extra, "secteurs_brvm.json") if a.extra else None
        if sp0_ and os.path.exists(sp0_):
            SECT_OFF = json.load(open(sp0_, encoding="utf8")).get("rows") or {}
    except Exception as e:  # noqa: BLE001
        log("secteurs officiels illisibles :", e)
    fund = json.load(open(os.path.join(src, "fundamentals.json"), encoding="utf8"))
    # fraîcheur de la base extérieure (tirée de SikaFinance et de la BRVM) : figée depuis plus de 21 jours = la source ne répond plus
    # ou bloque ; les données déjà prises restent (miroir fusionné, scripts/sticky.py) et le récent vient des sources BRVM
    base_ext = {}
    try:
        g_ = str((fund.get("_meta") or {}).get("generated_at") or (fund.get("_meta") or {}).get("updated") or "")[:10]
        if g_:
            age_ = (dt.date.today() - dt.date.fromisoformat(g_)).days
            base_ext = {"maj": g_, "age_j": age_, "etat": "figée" if age_ > 21 else "à jour"}
            if age_ > 21:
                print(f"::warning::Base extérieure figée depuis {age_} jours (dernière mise à jour {g_}) : chiffres récents pris dans les sources BRVM seulement", flush=True)
    except Exception as e:  # noqa: BLE001
        base_ext = {"etat": f"date illisible ({str(e)[:60]})"}
    # états financiers publiés à la BRVM (branche comptes), lus et vérifiés par les identités comptables : prioritaires sur la base
    # tierce pour les exercices qu'ils couvrent, quand leur périmètre est le même (comptes sociaux ou consolidés)
    cpt_chk = {"t": 0, "y": 0, "set": 0, "fix": 0, "fill": 0, "detail_only": [], "ex": []}
    CORR_ROWS = load_corr()  # corrections vérifiées sur document (comptes lus, puis séries de la fiche)
    ECARTES = []  # éléments mal formés écartés à la construction (publiés dans boc_check.json, listés par le contrôle du matin)
    calc_fill = []  # (titre, poste, exercice, montant) calculés d'après les comptes publiés : comblent les exercices encore vides en dernier
    # exercices plus anciens : pages SikaFinance archivées (web.archive.org) — chiffres publiés (CA, résultat net, BNPA, dividende)
    sh_path = os.path.join(a.extra, "sika_hist.json") if a.extra else None
    hist = {}
    if sh_path and os.path.exists(sh_path):
        sh_ = json.load(open(sh_path, encoding="utf8"))
        for src_ in (sh_.get("old") or {}, sh_.get("t") or {}):  # (lecture précédente conservée tant que la nouvelle n'est pas faite)
            for t, yrs in src_.items():
                hist.setdefault(t, {}).update(yrs)
    # cours USD/FCFA du jour (parité fixe 655,957 FCFA pour 1 euro × cours euro/dollar publié par la Réserve fédérale) : états et
    # dividendes d'une société qui publie en dollars (Ecobank Transnational), convertis au cours du jour de leur publication
    fx_ = None
    try:
        import bisect
        eur_ = series_from_csv(fetch(DS.format("exchange-rates/main/data/daily.csv"), a.cache).decode("utf8"), "Date", "Exchange rate",
                               lambda r: r.get("Country") == "Euro")
        fd_ = [x[0] for x in eur_ if x[1]]
        fv_ = [x[1] * XOF_PER_EUR for x in eur_ if x[1]]

        def fx_(d):
            k_ = int(str(d).replace("-", "")[:8])
            i_ = bisect.bisect_right(fd_, k_) - 1
            return round(fv_[i_], 3) if i_ >= 0 and k_ - fd_[i_] <= 10000 else None  # (dernier cours connu, moins d'un an)
    except Exception as e:  # noqa: BLE001
        log("cours USD/FCFA indisponible (états et dividendes en dollars non convertis) :", e)
    if a.comptes and os.path.exists(a.comptes):
        try:
            import comptes as CPT
            mir = {t: {k_: dict(s_) for k_, s_ in (v.get("series") or {}).items() if isinstance(s_, dict)}
                   for t, v in fund.items() if t != "_meta" and isinstance(v, dict)}  # (copie : la base elle-même n'est pas modifiée ici)
            # la base de recoupement des comptes lus comprend aussi les archives SikaFinance (chiffre d'affaires, résultat net)
            # pour les exercices que la base tierce ne couvre pas : un montant isolé qu'elles contredisent n'est pas retenu
            for t, yrs in hist.items():
                ser_ = mir.setdefault(t, {})
                for y, rec in yrs.items():
                    for k, sk in (("ca", "ca"), ("rn", "resultat_net")):
                        if rec.get(k) is not None and (ser_.get(sk) or {}).get(str(y)) is None:
                            ser_.setdefault(sk, {})[str(y)] = rec[k]
            CONS = CPT.consolidate(json.load(open(a.comptes, encoding="utf8")), mir, fx_)
            # postes des comptes lus corrigés après vérification sur le document (seed/corrections_bnpa.json, lignes « cpt » :
            # unité lue fausse, renvoi de note lu comme montant, montant vérifié écarté face à une base fausse) ; appliqué avant la
            # reprise dans la série, que la correction suit donc d'elle-même (voir cpt_fix)
            cpt_fix_log = cpt_fix(CONS, CORR_ROWS)
            if cpt_fix_log[0]:
                log("comptes publiés corrigés d'après les documents :", "; ".join(cpt_fix_log[0]))
            if cpt_fix_log[1]:
                log("corrections de comptes à revoir (le montant lu a changé depuis la correction) :", "; ".join(cpt_fix_log[1]))
                # (signalées au contrôle du matin : une correction vérifiée qui ne s'applique plus est à revoir sur le document)
                ECARTES.extend(f"correction vérifiée à revoir (seed/corrections_bnpa.json) : {x}" for x in cpt_fix_log[1])
            bank_t = {x.get("symbole") or x.get("ticker"): bool(x.get("banque")) for x in acts}
            MAPC = (("resultat_net", "resultat_net"), ("total_bilan", "total_actif"), ("capitaux_propres", "capitaux_propres"),
                    ("ebit", "resultat_exploitation"), ("ebitda", "ebe"), ("depots_clientele", "b_dettes_clientele"),
                    ("credits_clientele", "b_creances_clientele"))
            DERIVED = ("roe", "roa", "marge_nette", "marge_exploitation", "croissance_ca", "croissance_resultat_net")
            cpt_bad = []
            for t, cc in CONS.items():
                f_bak = copy.deepcopy(fund.get(t))
                try:
                    f = fund.get(t)
                    if not f or not isinstance(f, dict):
                        continue
                    f["cpt"] = cc
                    cpt_chk["t"] += 1
                    # même périmètre et mêmes normes que la base : la plupart des montants communs concordent, et le résultat net aussi
                    # (des écarts isolés sont des erreurs ou des chiffres provisoires de la base, corrigés par les comptes publiés) ;
                    # sinon l'autre référentiel publié par la société, s'il est celui de la base, sert aux chiffres clés
                    def same_basis(g_):
                        return g_["ncmp"] < 3 or (g_["agree"] >= .5 and (g_.get("n_rn", 0) < 2 or (g_.get("agree_rn") or 0) >= .5))
                    usd_t = t in CPT.USD_REPORTERS  # (base convertie à d'autres cours : les comptes publiés, convertis au jour de publication, la remplacent)
                    src_g = cc if same_basis(cc) else (cc["alt"] if cc.get("alt") and cc["alt"].get("ncmp", 0) >= 3 and same_basis(cc["alt"]) else None)
                    if src_g is None:
                        cpt_chk["detail_only"].append(f'{t} ({cc["per"]}, {cc["agree"]:.0%} de {cc["ncmp"]})')
                        continue
                    if src_g is not cc:
                        cpt_chk.setdefault("alt_used", []).append(f'{t} ({src_g["per"]} {src_g["std"]})')
                    ser = f.setdefault("series", {})
                    bank = bank_t.get(t) or any("b_pnb" in r["v"] for r in src_g["y"].values())
                    for y, r in src_g["y"].items():
                        v, ys = r["v"], str(y)
                        corr_y = {k_ for t_, y_, k_ in cpt_fix_log[2] if t_ == t and y_ == ys}  # (postes corrigés d'après le document)
                        cpt_chk["y"] += 1
                        pairs = [("ca", "b_pnb" if bank else "chiffre_affaires")] + list(MAPC)
                        if v.get("resultat_net") is None and v.get("resultat_bilan") is not None:
                            v = dict(v, resultat_net=v["resultat_bilan"])  # (résultat de l'exercice au bilan : même montant publié)
                        # coût du risque (charge comptée positivement) : signe lu d'après le compte de résultat
                        # (résultat brut d'exploitation ± coût du risque = résultat d'exploitation)
                        if bank and v.get("b_cout_risque") is not None and v.get("b_rbe") is not None and v.get("resultat_exploitation") is not None:
                            cr_, rbe_, re_ = v["b_cout_risque"], v["b_rbe"], v["resultat_exploitation"]
                            if abs(rbe_ + cr_ - re_) <= max(1.0, abs(re_) * .002):
                                v = dict(v, _cdr=-cr_)
                            elif abs(rbe_ - cr_ - re_) <= max(1.0, abs(re_) * .002):
                                v = dict(v, _cdr=cr_)
                            if "_cdr" in v:
                                pairs.append(("cout_du_risque", "_cdr"))
                        elif bank and v.get("b_cout_risque") is None and v.get("b_rbe") is not None and v.get("resultat_exploitation") is not None:
                            # coût du risque non lu, mais RBE et résultat d'exploitation publiés : la charge vaut RBE − résultat
                            # d'exploitation. Un coût du risque de la base de signe contraire est faux : son signe est rétabli s'il est
                            # l'opposé de cette différence (signe perdu ; montant de la base gardé, c'est le montant publié : SGBC 2024,
                            # « coût net du risque −36 235 » publié, RBE 163 484 − RE 127 248 = 36 236 à l'arrondi près), retiré sinon
                            d_cr = v["b_rbe"] - v["resultat_exploitation"]
                            x_cr = (ser.get("cout_du_risque") or {}).get(ys)
                            if isinstance(x_cr, (int, float)) and x_cr * d_cr < 0 and abs(d_cr) > max(1.0, abs(v["b_rbe"]) * .01):
                                if abs(x_cr + d_cr) <= max(2.0, abs(d_cr) * .01):
                                    v = dict(v, _cdr=-x_cr)
                                    pairs.append(("cout_du_risque", "_cdr"))
                                    corr_y.add("_cdr")
                                else:
                                    ser["cout_du_risque"].pop(ys, None)
                                    cpt_chk.setdefault("cdr_retire", []).append(f"{t} {ys} {x_cr:g} (RBE − RE = {d_cr:g})")
                        changed = False
                        dep_ = set()  # (ratios de la base à retirer après une correction vérifiée : seulement ceux qui en dépendent)
                        weak_ = set(r.get("w") or ())
                        calc_ = set(r.get("calc") or ())
                        for sk, ck in pairs:
                            if v.get(ck) is None:
                                continue
                            if ck in calc_:
                                # (montant calculé d'après le document : ne comble un exercice vide qu'en dernier, après les archives)
                                calc_fill.append((t, sk, ys, round(v[ck], 1)))
                                continue
                            o = ser.setdefault(sk, {})
                            old = o.get(ys)
                            new = round(v[ck], 1)
                            if old is not None and abs(old - new) <= 0.6:
                                continue  # même montant (arrondi au million près)
                            if old is not None and ck in weak_ and not usd_t:
                                continue  # montant d'un seul document, sans identité vérifiée : ne remplace pas un montant existant
                            if old is None:
                                cpt_chk["fill"] += 1
                            elif abs(old - new) > max(1.0, abs(old) * .005):
                                cpt_chk["fix"] += 1
                                if ck in corr_y:
                                    dep_.update(CORR_DEP.get(sk, DERIVED))
                                else:
                                    changed = True
                                if len(cpt_chk["ex"]) < 25:
                                    cpt_chk["ex"].append(f"{t} {y} {sk} {old:g} -> {new:g}")
                            o[ys] = new
                            cpt_chk["set"] += 1
                        if usd_t and r.get("fx"):
                            dd_ = str(r.get("d") or "")
                            f.setdefault("src_years", {})[ys] = (f"converti : comptes publiés en dollars US, 1 USD = {r['fx']:.2f} FCFA".replace(".", ",")
                                                                 + (f" au {dd_[8:10]}/{dd_[5:7]}/{dd_[:4]} (date de publication)" if dd_ else ""))
                            changed = True
                        if changed or dep_:  # ratios de la base tierce calculés sur les montants corrigés : retirés (recalculés plus loin)
                            for dk in (DERIVED if changed else sorted(dep_)):
                                (ser.get(dk) or {}).pop(ys, None)
                    # exercices plus anciens publiés dans l'autre norme (comptes SYSCOHADA d'avant le passage aux IFRS, même périmètre) :
                    # ajoutés seulement là où rien n'existe, et signalés comme tels (sup « r » dans le FA)
                    alt_g = cc.get("alt") if src_g is cc else cc
                    if alt_g and alt_g.get("y") and alt_g.get("per") == src_g.get("per") and alt_g.get("std") != src_g.get("std"):
                        src_y = f.setdefault("src_years", {})
                        for y, r in alt_g["y"].items():
                            ys = str(y)
                            if ys in {str(y_) for y_ in src_g["y"]}:
                                continue
                            v = r["v"]
                            if v.get("resultat_net") is None and v.get("resultat_bilan") is not None:
                                v = dict(v, resultat_net=v["resultat_bilan"])
                            added = False
                            for sk, ck in [("ca", "b_pnb" if bank else "chiffre_affaires")] + list(MAPC):
                                if v.get(ck) is None:
                                    continue
                                o = ser.setdefault(sk, {})
                                if o.get(ys) is None:  # (comme pour le référentiel principal : un montant d'un seul document ne remplace rien, il complète)
                                    o[ys] = round(v[ck], 1)
                                    added = True
                                    cpt_chk["fill"] += 1
                            if added and not src_y.get(ys):
                                src_y[ys] = "référentiel " + ("IFRS" if alt_g.get("std") == "ifrs" else "SYSCOHADA") + " (la société publie aujourd'hui en " + ("IFRS" if src_g.get("std") == "ifrs" else "SYSCOHADA") + ")"
                except Exception as e:  # noqa: BLE001  (une société en erreur est remise comme avant, les autres continuent)
                    if isinstance(f_bak, dict) and isinstance(fund.get(t), dict):
                        fund[t].clear()
                        fund[t].update(f_bak)
                    calc_fill[:] = [c_ for c_ in calc_fill if c_[0] != t]
                    cpt_bad.append(t)
                    ECARTES.append(f"comptes publiés {t} : {type(e).__name__}")
                    log("comptes publiés écartés pour", t, ":", e)
            if cpt_bad:
                print(f"::warning::Construction : comptes publiés écartés pour {len(cpt_bad)} société(s) (voir le journal)")
            log("comptes publiés BRVM :", {k: v for k, v in cpt_chk.items() if k not in ("ex", "detail_only", "alt_used")},
                ("; périmètre différent de la base, détail seulement : " + ", ".join(cpt_chk["detail_only"])) if cpt_chk["detail_only"] else "",
                ("; chiffres clés pris dans l'autre référentiel publié : " + ", ".join(cpt_chk["alt_used"])) if cpt_chk.get("alt_used") else "")
            if cpt_chk["ex"]:
                log("comptes corrigés d'après les états publiés :", "; ".join(cpt_chk["ex"]))
        except Exception as e:  # noqa: BLE001
            import traceback
            log("comptes publiés BRVM illisibles :", e, traceback.format_exc()[-400:])
            print("::warning::Construction : comptes publiés illisibles (voir le journal)")
    # exercices plus anciens : archives SikaFinance, ajoutées seulement là où la source actuelle n'a rien
    if hist:
        kmap = {"ca": "ca", "rn": "resultat_net", "bnpa": "bnpa", "div": "dividende"}  # (chiffres publiés seulement, pas de ratio)
        for t, yrs in hist.items():
            f = fund.get(t)
            if not f:
                continue
            ser = f.setdefault("series", {})
            src_y = f.setdefault("src_years", {})
            for y, rec in yrs.items():
                added = False
                for k, sk in kmap.items():
                    if rec.get(k) is None:
                        continue
                    o = ser.setdefault(sk, {})
                    if o.get(y) is None:
                        o[y] = rec[k]
                        added = True
                if added and not src_y.get(y):  # (un exercice déjà signalé — autre référentiel, montants convertis — garde sa mention)
                    src_y[y] = "archive SikaFinance " + rec.get("src", "")
    # montants calculés d'après les comptes publiés (produit net bancaire de l'ancien plan bancaire, chiffre d'affaires SYSCOHADA
    # somme des ventes) : seulement pour les exercices restés vides
    # (un montant calculé isolé — plus de 60 % au-dessus ou près de 40 % en dessous de ses DEUX exercices voisins — n'est pas
    # repris : une ligne de ventes propre à la société, absente du plan comptable, manque sans doute à la somme)
    n_calc, rej_calc = 0, []
    cand_ = {}
    for t, sk, ys, val in calc_fill:
        cand_.setdefault((t, sk), {}).setdefault(ys, val)
    for (t, sk), vals in cand_.items():
        f = fund.get(t)
        if not isinstance(f, dict):
            continue
        o = f.setdefault("series", {}).setdefault(sk, {})
        allv = {**{k_: v_ for k_, v_ in vals.items()}, **{k_: v_ for k_, v_ in o.items() if v_ is not None}}
        for ys, val in sorted(vals.items()):
            if o.get(ys) is not None:
                continue
            nb_ = [allv.get(str(int(ys) + d_)) for d_ in (-1, 1)]
            if all(x_ and x_ > 0 for x_ in nb_) and val > 0 and all(val / x_ > 1.6 or val / x_ < 0.62 for x_ in nb_):
                rej_calc.append(f"{t} {ys} {sk} {val:g}")
                continue
            o[ys] = val
            n_calc += 1
            f.setdefault("src_years", {}).setdefault(ys, "calculé d'après les comptes publiés")
    if calc_fill:
        log(f"comptes publiés BRVM : {n_calc} exercices vides comblés par un montant calculé d'après le document ({len(calc_fill)} proposés)"
            + (f" ; écartés (isolés face aux deux exercices voisins) : {', '.join(rej_calc)}" if rej_calc else ""))
    # société cotée dans sa forme actuelle depuis un exercice donné (fusion) : chiffres des exercices antérieurs, ceux d'entités
    # distinctes, retirés de toutes les sources (base tierce, archives) ; les dividendes versés aux actionnaires restent
    try:
        from comptes import FIRST_FY
    except Exception:  # noqa: BLE001
        FIRST_FY = {}
    for t, y0 in FIRST_FY.items():
        f = fund.get(t)
        if not isinstance(f, dict):
            continue
        for k, o in (f.get("series") or {}).items():
            if isinstance(o, dict) and k != "dividende":
                for y in [y for y in o if str(y).isdigit() and int(y) < y0]:
                    o.pop(y)
        for y in [y for y in (f.get("src_years") or {}) if str(y).isdigit() and int(y) < y0]:
            f["src_years"].pop(y)
    # trésorerie nette et dette nette de la base tierce contrôlées par les comptes publiés et vérifiés, montants impossibles retirés
    # (voir base_fix) ; liste dans boc_check.json (« base_rejets »)
    base_rej = base_fix(fund)
    if base_rej:
        log("base tierce corrigée d'après les comptes publiés ou retirée :", "; ".join(base_rej))
    # flux de trésorerie : ceux des états financiers publiés à la BRVM et vérifiés (flux des activités opérationnelles et
    # acquisitions d'immobilisations du même document) ; l'ancienne lecture sans contrôle (pdf_fin.json) n'est plus utilisée
    pdf_cf = {}
    for t, f in fund.items():
        cc = f.get("cpt") if isinstance(f, dict) else None
        for y, r in ((cc or {}).get("y") or {}).items():
            v = r["v"]
            if v.get("flux_operationnels") is not None and (v.get("capex_corp") is not None or v.get("capex_incorp") is not None):
                cap = abs(v.get("capex_corp") or 0) + abs(v.get("capex_incorp") or 0)
                pdf_cf.setdefault(t, {})[str(y)] = {"cfo": v["flux_operationnels"], "capex": round(cap, 3), "fcf": round(v["flux_operationnels"] - cap, 3)}
    divs = json.load(open(os.path.join(src, "dividendes.json"), encoding="utf8"))["all"]
    # avis lus directement sur brvm.org (relevés toutes les 15 min) : secours si la base d'avis tierce s'arrête
    AV = []
    try:
        avp = os.path.join(a.out, "avis_brvm.json")
        if os.path.exists(avp):
            AV, nomap = brvm_avis(json.load(open(avp, encoding="utf8")).get("items") or {}, json.load(open(os.path.join(src, "events.json"), encoding="utf8"))["events"], acts, a.out)
            log("avis brvm.org :", len(AV), "lus" + (", sociétés non rattachées : " + ", ".join(sorted(nomap)) if nomap else ""))
    except Exception as e:  # noqa: BLE001
        log("avis brvm.org illisibles :", e)
    av_chk = {"div": 0, "split": 0, "ev": 0, "ag": 0, "div_fix": 0}
    # montant du dividende lu dans l'avis officiel le plus récent de la BRVM pour chaque titre et exercice (un avis « modification du
    # montant du dividende » remplace le précédent) ; le calendrier de la BRVM n'est pas toujours mis à jour après un rectificatif
    AVD = {}
    for r in AV:
        o = r.get("ocr") or {}
        ex_ = o.get("ex") or r.get("ex")
        if r.get("t") and o.get("net") and o["net"] > 0 and ex_ and (r.get("k") == "div" or r.get("c") == "Modification du dividende"):
            k_ = (r["t"], int(ex_))
            if k_ not in AVD or (r.get("d") or "") > (AVD[k_].get("d") or ""):
                AVD[k_] = {**o, "d": r.get("d"), "u": r["u"], "mod": r.get("c") == "Modification du dividende"}
    if AVD:
        fixes = []
        for x in divs:
            a_ = AVD.get((x.get("ticker"), x.get("exercice")))
            if not a_ or not x.get("dividende"):
                continue
            if not a_["mod"] and re.search(r"rectif|modif", str(x.get("dividende_remarque") or ""), re.I):
                continue  # la base a déjà appliqué un avis rectificatif plus récent que celui qui a été lu
            q_ = a_["net"] / x["dividende"]
            if abs(q_ - 1) > .005 and .2 < q_ < 5:  # lecture plausible et différente : l'avis officiel l'emporte
                fixes.append(f'{x["ticker"]} {x["exercice"]} : {x["dividende"]} -> {a_["net"]}{" (rectificatif)" if a_["mod"] else ""}')
                x["dividende"], x["avis"] = a_["net"], 1
                av_chk["div_fix"] += 1
            for kk, kd in (("date_detachement", "det"), ("date_paiement", "pay")):
                if not x.get(kk) and a_.get(kd):
                    x[kk] = a_[kd]
                    x[kd + "_off"] = 1  # (date lue dans l'avis officiel)
        if fixes:
            log("dividendes d'après les avis officiels :", "; ".join(fixes))
    if AV:  # dividendes annoncés sur brvm.org (montant net, détachement, paiement) absents de la base : ajoutés
      try:
        have = collections.defaultdict(list)
        for x in divs:
            if x.get("ticker"):
                have[x["ticker"]].append(x)

        def near(d1, d2, n=10):
            try:
                return abs((dt.date.fromisoformat(d1[:10]) - dt.date.fromisoformat(d2[:10])).days) <= n
            except (TypeError, ValueError):
                return False
        for r in AV:
            if r.get("k") != "div" or not r.get("t") or not r.get("dps") or not (r.get("det") or r.get("pay")):
                continue
            if any((r.get("ex") and x.get("exercice") == r["ex"] and abs((x.get("dividende") or 0) - r["dps"]) < 0.5)
                   or near(x.get("date_detachement"), r.get("det")) or near(x.get("date_paiement"), r.get("pay")) for x in have[r["t"]]):
                continue
            # montant de la colonne du calendrier brvm.org : net pour certaines sociétés, brut pour d'autres (l'avis PDF précise le net) -> signalé
            a_ = AVD.get((r["t"], r.get("ex")))
            nx = {"ticker": r["t"], "dividende": a_["net"] if a_ else r["dps"], "exercice": r.get("ex"), "date_annonce": r.get("d"), "date_detachement": r.get("det"),
                  "date_paiement": r.get("pay"), "source": "BRVM", **({} if a_ else {"cal": 1}),
                  **({"det_off": 1} if r.get("det") else {}), **({"pay_off": 1} if r.get("pay") else {})}
            divs.append(nx)
            have[r["t"]].append(nx)
            av_chk["div"] += 1
      except Exception as e:  # noqa: BLE001
        log("dividendes brvm.org ignorés :", e)
    # bulletins officiels de la cote (BRVM) : contrôle et secours des cours et des dividendes
    BOC = {}
    boc_milliers_ = []
    if a.boc and os.path.isdir(a.boc):
        cols = ("prev", "o", "c", "var", "vol", "val", "ref", "ytd", "div", "div_d", "yld", "per")
        for fn in sorted(os.listdir(a.boc)):
            if not re.match(r"^\d{4}\.json$", fn):
                continue
            for k, rows_ in json.load(open(os.path.join(a.boc, fn), encoding="utf8")).items():
                for sym, v in rows_.items():
                    rb0_ = dict(zip(cols, v))
                    # valeur échangée imprimée en milliers (montants d'un milliard et plus, lus sans leur dernier groupe de chiffres) :
                    # ramenée en FCFA quand elle redonne volume × cours à 2 % près (même règle que l'archive histo.py)
                    vo_, va_, cl_ = rb0_.get("vol"), rb0_.get("val"), rb0_.get("c") or rb0_.get("ref")
                    if vo_ and va_ and cl_ and not .7 < va_ / (vo_ * cl_) < 1.3 and .98 < va_ * 1000 / (vo_ * cl_) < 1.02:
                        rb0_["val"], rb0_["val_k"] = va_ * 1000, 1
                        boc_milliers_.append(f"{sym} {k}")
                    BOC.setdefault(sym, {})[int(k)] = rb0_
        if boc_milliers_:
            log("bulletins : valeurs échangées lues en milliers ramenées en FCFA :", len(boc_milliers_), "; ".join(boc_milliers_[-8:]))
        log("bulletins officiels :", len(BOC), "titres,", sum(len(v) for v in BOC.values()), "lignes")
    # titre coté au dernier bulletin mais absent de la fiche (nouvelle introduction en bourse que la base n'a pas encore) : signalé
    BOC_NOUV = []
    if BOC:
        kmax_ = max(max(v) for v in BOC.values() if v)
        tk_ = {x.get("ticker") for x in acts}
        BOC_NOUV = sorted(sym for sym, v in BOC.items() if kmax_ in v and sym not in tk_)
        if BOC_NOUV:
            print(f"::warning::Construction : titre(s) du bulletin officiel absent(s) de la fiche : {', '.join(BOC_NOUV)}", flush=True)
    # versements lus dans les documents officiels de la BRVM depuis l'ouverture (avis de paiement, calendriers, avis du Dépositaire
    # central ; branche dividendes) : montant et dates de l'avis (rectificatif compris) à la place de ceux de la base, versements
    # absents ajoutés. Un versement de la base est le même s'il tombe à 10 jours près, ou s'il porte sur le même exercice et le même
    # montant (dates fausses dans la base). Montants tels que publiés (ramenés ensuite sur la base des actions actuelles).
    off_chk = {"same": 0, "amt": 0, "dates": 0, "added": 0, "ex": []}
    if a.dividendes and os.path.exists(a.dividendes):
        try:
            OFF = json.load(open(a.dividendes, encoding="utf8")).get("rows") or []
            listed = {a_["ticker"] for a_ in acts}
            byt = collections.defaultdict(list)
            for x in divs:
                if x.get("ticker"):
                    byt[x["ticker"]].append(x)

            def dd_(d1, d2):
                try:
                    return abs((dt.date.fromisoformat(d1[:10]) - dt.date.fromisoformat(d2[:10])).days)
                except (TypeError, ValueError):
                    return 9999
            used = set()
            # dividende publié seulement en cents de dollar : montant en FCFA du bulletin officiel de la cote (dernier dividende payé,
            # à sa date de paiement : la valeur la plus souvent imprimée dans les bulletins des 60 jours suivants) ; à défaut, cents de
            # dollar convertis au cours du jour de l'avis (figé). Marqué « $ » dans les deux cas
            for o in OFF:
                try:
                    if not o.get("net") and o.get("usd_c"):
                        pd_ = o.get("pay") or o.get("det")
                        seen_ = collections.Counter()
                        if pd_ and BOC.get(o["t"]):
                            p0 = di(pd_)
                            for kb, rb in BOC[o["t"]].items():
                                if p0 - 30 <= kb <= di((dt.date.fromisoformat(pd_[:10]) + dt.timedelta(days=60)).isoformat()) and rb.get("div") and rb.get("div_d") \
                                        and dd_(str(rb["div_d"]), pd_) <= 10:
                                    seen_[float(rb["div"])] += 1
                        if seen_:
                            o["net"], o["boc_fcfa"] = seen_.most_common(1)[0][0], 1
                            off_chk["usd_bulletin"] = off_chk.get("usd_bulletin", 0) + 1
                            continue
                        r_ = fx_(o.get("pub") or o.get("det") or o.get("pay") or "") if fx_ else None
                        if r_:
                            o["net"], o["fx"] = round(o["usd_c"] / 100 * r_, 4), r_
                            off_chk["usd"] = off_chk.get("usd", 0) + 1
                        else:  # (cours indisponible : le montant de la base, en cents de dollar lu comme des FCFA, n'est pas affiché)
                            for x in byt[o["t"]]:
                                if (o.get("det") and dd_(x.get("date_detachement"), o["det"]) <= 10) or (o.get("pay") and dd_(x.get("date_paiement"), o["pay"]) <= 10):
                                    x["dividende"] = None
                            off_chk["usd_sans_cours"] = off_chk.get("usd_sans_cours", 0) + 1
                except Exception as e:  # noqa: BLE001
                    off_chk["bad"] = off_chk.get("bad", 0) + 1
                    ECARTES.append(f"versement officiel {o.get('t')} exercice {o.get('ex')} ({o.get('det') or o.get('pay') or '—'}) : {type(e).__name__}")
                    log("versement officiel écarté :", o.get("t"), o.get("ex"), e)
            for o in sorted(OFF, key=lambda o: (o["t"], o.get("det") or o.get("pay") or "", o.get("kind") == "exceptionnel")):
                try:
                    if o["t"] not in listed or not o.get("net") or o["net"] <= 0 or not (o.get("det") or o.get("pay") or o.get("ex")):
                        continue  # (un versement sans date mais d'exercice connu — revues trimestrielles 1999-2001 — est gardé, hors rendement total)
                    cands = [x for x in byt[o["t"]] if id(x) not in used and x.get("dividende") and (
                        (o.get("det") and dd_(x.get("date_detachement"), o["det"]) <= 10) or (o.get("pay") and dd_(x.get("date_paiement"), o["pay"]) <= 10)
                        or (o.get("ex") and x.get("exercice") == o["ex"] and abs(x["dividende"] / o["net"] - 1) <= .005))]
                    if cands:
                        x = min(cands, key=lambda c_: abs(c_["dividende"] / o["net"] - 1))  # (deux versements le même jour : chacun le sien)
                        used.add(id(x))
                        if abs(x["dividende"] / o["net"] - 1) > .0005:
                            if len(off_chk["ex"]) < 30:
                                off_chk["ex"].append(f'{o["t"]} {o.get("pay") or o.get("det")} : {x["dividende"]:g} -> {o["net"]:g}')
                            x["dividende_base"], x["dividende"] = x["dividende"], o["net"]
                            off_chk["amt"] += 1
                        else:
                            off_chk["same"] += 1
                        if (o.get("det") and x.get("date_detachement") != o["det"]) or (o.get("pay") and x.get("date_paiement") != o["pay"]):
                            off_chk["dates"] += 1
                        x["date_detachement"] = o.get("det") or x.get("date_detachement")
                        if o.get("pub") and (not x.get("date_annonce") or x["date_annonce"] > (o.get("det") or o.get("pay") or "9")):
                            x["date_annonce"] = o["pub"]  # (annonce de la base postérieure au détachement : date de l'avis)
                        x["date_paiement"] = o.get("pay") or x.get("date_paiement")
                        # (dates écrites dans le document officiel : jamais retirées par les contrôles de cohérence plus bas)
                        if o.get("det"):
                            x["det_off"] = 1
                        if o.get("pay"):
                            x["pay_off"] = 1
                        if o.get("ex") and not x.get("exercice"):
                            x["exercice"] = o["ex"]
                        x["source"], x["avis"] = "BRVM", 1
                        if o.get("src") in ("bulletin", "revue trimestrielle"):
                            x["weak"] = 1  # (montant lu dans un ancien bulletin ou une revue : contrôlé plus loin sur le cours du jour)
                        if o.get("fx") or o.get("boc_fcfa"):
                            x["usd_c"], x["fx"] = o["usd_c"], o.get("fx")
                        if o.get("kind") == "exceptionnel":
                            x["exc"] = 1
                        if o.get("brut") and o.get("irvm") is not None:  # (brut et taux de l'impôt écrits dans l'avis ou le calendrier)
                            x["brut_avis"], x["irvm_avis"] = o["brut"], o["irvm"]
                        if o.get("px") and o.get("px_d"):
                            x["px_raw"], x["px_d"] = o["px"], o["px_d"]
                        if o.get("chk"):  # (autres lectures du même versement, avec leur date : montant d'avant une opération)
                            x["chk_off"] = o["chk"]
                    else:
                        nx = {"ticker": o["t"], "dividende": o["net"], "exercice": o.get("ex"), "date_annonce": o.get("pub"),
                              "date_detachement": o.get("det"), "date_paiement": o.get("pay"), "source": "BRVM", "avis": 1,
                              **({"weak": 1} if o.get("src") in ("bulletin", "revue trimestrielle") else {}),
                              **({"usd_c": o["usd_c"], "fx": o.get("fx")} if o.get("fx") or o.get("boc_fcfa") else {}), **({"exc": 1} if o.get("kind") == "exceptionnel" else {}), **({"px_raw": o["px"], "px_d": o["px_d"]} if o.get("px") and o.get("px_d") else {}),
                              **({"brut_avis": o["brut"], "irvm_avis": o["irvm"]} if o.get("brut") and o.get("irvm") is not None else {}),
                              **({"det_off": 1} if o.get("det") else {}), **({"pay_off": 1} if o.get("pay") else {}),
                              **({"chk_off": o["chk"]} if o.get("chk") else {})}
                        divs.append(nx)
                        byt[o["t"]].append(nx)
                        used.add(id(nx))
                        off_chk["added"] += 1
                except Exception as e:  # noqa: BLE001  (un versement mal formé est écarté, les suivants restent lus)
                    off_chk["bad"] = off_chk.get("bad", 0) + 1
                    ECARTES.append(f"versement officiel {o.get('t')} exercice {o.get('ex')} ({o.get('det') or o.get('pay') or '—'}) : {type(e).__name__}")
                    log("versement officiel écarté :", o.get("t"), o.get("ex"), e)
            if off_chk.get("bad"):
                print(f"::warning::Construction : {off_chk['bad']} versement(s) officiel(s) écarté(s) (voir le journal)")
            log("dividendes des documents officiels BRVM :", {k: v for k, v in off_chk.items() if k != "ex"},
                ("; montants corrigés : " + "; ".join(off_chk["ex"])) if off_chk["ex"] else "")
        except Exception as e:  # noqa: BLE001
            log("dividendes officiels illisibles :", e)
            print("::warning::Construction : dividendes officiels illisibles (voir le journal)")
    # dates d'un versement corrigées après vérification sur les documents officiels (seed/corrections_dividendes.json : avis de report
    # pas encore lu, bulletin de la cote) : appliquées seulement si le versement porte encore la valeur notée « avant » ; une valeur
    # déjà différente (avis de report lu depuis) est laissée et signalée
    try:
        cd_ = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", "corrections_dividendes.json"), encoding="utf8"))
        done_, skip_ = [], []
        for c_ in cd_.get("rows") or []:
            kk_ = {"det": "date_detachement", "pay": "date_paiement", "ann": "date_annonce"}[c_["champ"]]
            for x in divs:
                if x.get("ticker") != c_["t"] or x.get("exercice") != c_["ex"] or not x.get("dividende"):
                    continue
                if (x.get(kk_) or None) == c_["avant"]:
                    x[kk_] = c_["apres"]
                    x[c_["champ"] + "_off"] = 1  # (date vérifiée sur le document)
                    x.setdefault("corr", {})[c_["champ"]] = c_["avant"]
                    done_.append(f'{c_["t"]} {c_["ex"]} {c_["champ"]} {c_["avant"]} -> {c_["apres"] or "retirée"}')
                elif (x.get(kk_) or None) != c_["apres"]:
                    skip_.append(f'{c_["t"]} {c_["ex"]} {c_["champ"]} ({x.get(kk_)})')
        if done_:
            log("dates de dividendes corrigées d'après les documents :", "; ".join(done_))
        if skip_:
            log("dates de dividendes à revoir (le versement a changé depuis la correction) :", "; ".join(skip_))
    except Exception as e:  # noqa: BLE001
        log("corrections de dates de dividendes illisibles :", e)
        print("::warning::Construction : corrections de dates de dividendes illisibles (voir le journal)")
    boc_chk = {"n": 0, "diff": 0, "added": 0, "div_added": 0, "by": {}}
    # jours de séance attestés par un bulletin officiel (et nombre de titres dont le cours a varié ce jour-là) ; valeurs des indices
    # lues dans les bulletins récents (relevé du soir, branche raw)
    BOC_DAYS = collections.Counter()
    for sym_, by_ in BOC.items():
        for k_, r_ in by_.items():
            BOC_DAYS[k_] += 1 if r_.get("var") not in (None, 0, 0.0) else 0
    BOC_IDX, BOC_IDXV = {}, {}  # (valeur de l'indice ; montant échangé par les sociétés de l'indice, marché entier pour le BRVM Composite)
    try:
        for k_, r_ in ((json.load(open(os.path.join(a.extra, "boc.json"), encoding="utf8")) if a.extra and os.path.exists(os.path.join(a.extra, "boc.json")) else {}).get("d") or {}).items():
            for code_, v_ in (r_.get("idx") or {}).items():
                if v_ and v_[0]:
                    BOC_IDX.setdefault(code_, {})[int(k_)] = float(v_[0])
                if v_ and len(v_) >= 4 and v_[3] and v_[3] > 0:
                    BOC_IDXV.setdefault(code_, {})[int(k_)] = int(v_[3])
            if r_.get("val") and r_["val"] > 0:
                BOC_IDXV.setdefault("BRVMC", {})[int(k_)] = int(r_["val"])
    except Exception as e:  # noqa: BLE001
        log("indices des bulletins illisibles :", e)

    # titres dont le cours de la base a varié, jour par jour (un jour de séance en compte toujours plusieurs)
    BASE_MOVED = collections.Counter()
    for act_ in acts:
        try:
            rr_ = load_brvm_csv(os.path.join(src, act_["csv"] + ".csv"))
        except Exception:  # noqa: BLE001
            continue
        for j_ in range(1, len(rr_)):
            if rr_[j_][4] != rr_[j_ - 1][4]:
                BASE_MOVED[rr_[j_][0]] += 1

    def no_session(d_):  # jour sans séance : aucun bulletin officiel et aucun titre dont le cours a varié dans la base (férié)
        return d_ not in BOC_DAYS and not BASE_MOVED.get(d_)

    def is_weekend(d_):
        return dt.date(d_ // 10000, d_ // 100 % 100, d_ % 100).weekday() >= 5
    if BOC:  # dividendes payés lus dans les bulletins, ajoutés seulement quand la base n'a aucun versement à ±120 jours
        # (la date du bulletin peut suivre de plusieurs semaines celle de l'avis : un même dividende ne doit pas compter deux fois ;
        # un dividende payé en plusieurs fractions espacées de plus de 4 mois reste compté une fois par fraction)
        have_pay = collections.defaultdict(list)
        have_amt = collections.defaultdict(list)
        for x in divs:
            for kk in ("date_paiement", "date_detachement"):
                if x.get(kk) and x.get("ticker"):
                    try:
                        have_pay[x["ticker"]].append(dt.date.fromisoformat(x[kk][:10]))
                        if x.get("dividende"):
                            have_amt[x["ticker"]].append((dt.date.fromisoformat(x[kk][:10]), float(x["dividende"])))
                    except ValueError:
                        pass
        for sym, days in BOC.items():
            seen = set()
            for k in sorted(days):
                r = days[k]
                if not r.get("div") or not r.get("div_d") or (r["div_d"], r["div"]) in seen:
                    continue
                seen.add((r["div_d"], r["div"]))
                try:
                    pd_ = dt.date.fromisoformat(r["div_d"])
                except ValueError:
                    continue
                if pd_.year < 2008 or any(abs((pd_ - h).days) <= 120 for h in have_pay[sym]) \
                        or any(abs((pd_ - h).days) <= 200 and abs(a_ / r["div"] - 1) < .01 for h, a_ in have_amt[sym]):
                    boc_chk["div_dup"] = boc_chk.get("div_dup", 0) + 1
                    continue
                divs.append({"ticker": sym, "dividende": r["div"], "date_paiement": r["div_d"], "exercice": pd_.year - 1, "source": "BOC"})
                have_pay[sym].append(pd_)
                boc_chk["div_added"] += 1
    # BNPA d'un exercice corrigé après vérification sur le document (seed/corrections_bnpa.json) : appliqué seulement si la
    # fiche donne encore la valeur fautive notée (« avant ») ; une valeur déjà différente est laissée et signalée
    # (même fichier : autres postes de la série — résultat net, capitaux propres, coût du risque… — ; « apres » null retire la
    # valeur ; un chiffre clé corrigé retire les ratios de la base calculés dessus, recalculés plus loin ; les lignes « cpt » ont
    # déjà été appliquées aux comptes lus, voir cpt_fix)
    try:
        done_, skip_ = [], []
        for c_ in CORR_ROWS:
            if c_.get("cpt"):
                continue
            f_c = fund.get(c_["t"]) or {}
            k_c = c_.get("champ") or "bnpa"
            sb_ = (f_c.get("series") or {}).get(k_c)
            y_ = str(c_["ex"])
            new_ = corr_new(c_)
            if sb_ is None or y_ not in sb_:
                continue
            if sb_[y_] is not None and abs(sb_[y_] - c_["avant"]) <= max(.02, abs(c_["avant"]) * .001):
                if new_ is None:
                    sb_.pop(y_)
                else:
                    sb_[y_] = new_
                for dk in CORR_DEP.get(k_c, ()):
                    ((f_c.get("series") or {}).get(dk) or {}).pop(y_, None)
                if c_.get("src"):
                    f_c.setdefault("src_years", {})[y_] = c_["src"]
                done_.append(f'{c_["t"]} {y_}' + (f' ({c_["champ"]})' if c_.get("champ") else ""))
            elif sb_[y_] is not None and (new_ is None or abs(sb_[y_] - new_) > .02):
                skip_.append(f'{c_["t"]} {y_} {k_c} ({sb_[y_]:g})')
        if done_:
            log("données de la fiche corrigées d'après les documents :", ", ".join(done_))
        if skip_:
            log("corrections à revoir (la fiche a changé depuis la correction) :", ", ".join(skip_))
            ECARTES.extend(f"correction vérifiée à revoir (seed/corrections_bnpa.json) : {x}" for x in skip_)
    except Exception as e:  # noqa: BLE001
        log("corrections de la fiche illisibles :", e)
    # Fractionnements (avis BRVM) : cours, dividendes et données par action ramenés sur la base des actions actuelles.
    # Un fractionnement n'est appliqué qu'une fois effectif (date d'effet atteinte par les cours) et seulement s'il manque dans la source.
    SPL = collections.defaultdict(list)
    try:
        EVS_ = json.load(open(os.path.join(src, "events.json"), encoding="utf8"))["events"]
    except Exception as e:  # noqa: BLE001
        EVS_ = []
        log("fractionnements illisibles :", e)
        print("::warning::Construction : liste des opérations sur titres illisible (voir le journal)")
    spl_bad = 0
    for x in EVS_:  # (un avis mal formé est écarté et compté ; les suivants restent lus)
        try:
            dd_ = x.get("details") or {}
            if x.get("category") in ("stock_split", "reverse_split") and x.get("ticker") and x.get("event_at") and dd_.get("ratio_new") and dd_.get("ratio_old"):
                k_ = float(dd_["ratio_new"]) / float(dd_["ratio_old"])
                e_ = di(x["event_at"][:10])
                if k_ > 0 and abs(k_ - 1) > 1e-9 and all(abs(e_ - e0) > 20 for e0, _ in SPL[x["ticker"]]):
                    SPL[x["ticker"]].append((e_, k_))
        except Exception as e:  # noqa: BLE001
            spl_bad += 1
            ECARTES.append(f"fractionnement {x.get('ticker')} du {str(x.get('event_at'))[:10]} : {type(e).__name__}")
            log("fractionnement écarté :", x.get("ticker"), x.get("event_at"), e)
    if spl_bad:
        print(f"::warning::Construction : {spl_bad} avis de fractionnement mal formé(s) écarté(s) (voir le journal)")
    for r in AV:  # fractionnements publiés sur brvm.org (date et parité) absents de la base d'avis
      try:
        if r.get("k") == "frac" and r.get("t") and r.get("e") and r.get("ratio") and r["ratio"][0] and r["ratio"][1]:
            k_, e_ = r["ratio"][0] / r["ratio"][1], di(r["e"][:10])
            if k_ > 0 and abs(k_ - 1) > 1e-9 and all(abs(e_ - e0) > 20 for e0, _ in SPL[r["t"]]):
                SPL[r["t"]].append((e_, k_))
                av_chk["split"] += 1
      except Exception as e:  # noqa: BLE001
        log("fractionnement brvm.org ignoré :", r.get("u"), e)
    # opérations sur le capital vérifiées à la main (seed/operations_historiques.json : parité et date d'effet prouvées par un document
    # ou un bulletin officiel cité) qui manquent à la base d'avis et aux avis brvm.org lus : attributions gratuites de 2016-2017 (la
    # base ne lit que les fractionnements), fractionnements d'avant les bulletins conservés (Sonatel 23/11/2012, Onatel 29/11/2013).
    # Une opération déjà connue à 20 jours près n'est pas ajoutée une seconde fois ; une ligne sans date d'effet n'est pas lue
    OPH, oph_log = {}, []
    i2d_o = lambda x: dt.date(x // 10000, x // 100 % 100, x % 100)  # noqa: E731
    try:
        for o_ in json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", "operations_historiques.json"),
                                encoding="utf8")).get("rows") or []:
            n_, a0_ = (float(v_) for v_ in o_["parite"])
            k_ = (n_ + a0_) / a0_ if o_["type"] == "attribution" else n_ / a0_
            if not (k_ > 0 and abs(k_ - 1) > 1e-9) or not o_.get("date_effet"):
                continue
            e_ = di(o_["date_effet"])
            if all(abs((i2d_o(e_) - i2d_o(e0)).days) > 20 for e0, _ in SPL[o_["t"]]):
                SPL[o_["t"]].append((e_, k_))  # (rapport exact de la parité : 50/41, pas d'arrondi sur les dividendes)
                OPH[(o_["t"], e_)] = o_
                oph_log.append(f'{o_["t"]} {e_} x{k_:.6g}')
            else:
                oph_log.append(f'{o_["t"]} {e_} x{k_:.6g} déjà connue (avis), non ajoutée')
        if oph_log:
            log("opérations sur le capital vérifiées à la main :", "; ".join(oph_log))
    except Exception as e:  # noqa: BLE001
        log("opérations historiques illisibles :", e)
        print("::warning::Construction : seed/operations_historiques.json illisible (voir le journal)")
    split_log, force_write, PX_DATE = [], set(), {}
    bnpa_notes = []  # (exercices dont le BNPA du bulletin, gardé au résumé, n'est pas celui de la série : mention dans FA)
    MIROIR = {}  # valeurs de la fiche et de la BRVM côte à côte (contrôle du matin : écarts signalés, rien de remplacé)
    SPL_DONE = set()  # opérations déduites des paliers du bulletin officiel (cours déjà ajustés par la base)
    SPL_FORCE = set()  # opérations vérifiées à la main que la base de cours n'a pas ajustées (cours antérieurs ramenés même sans saut net)

    def split_factor(t, date_int, upto):
        """Produit des fractionnements effectifs après `date_int` (et au plus tard à `upto`)."""
        f_ = 1.0
        for e_, k_ in SPL.get(t, []):
            if date_int < e_ <= upto:
                f_ *= k_
        return f_
    today_i = int(os.environ.get("FQT_TODAY") or dt.date.today().strftime("%Y%m%d"))

    def adj_divs(tk, only=None):
        """Dividendes publiés par action ancienne ramenés sur la base actuelle (tous les fractionnements, ou seulement `only`)."""
        for x in divs:
            if x.get("ticker") != tk or not x.get("dividende"):
                continue
            ds_ = x.get("date_detachement") or x.get("date_paiement") or (f"{int(x['exercice']) + 1}-06-30" if x.get("exercice") else None)
            if not ds_:
                continue
            d0 = di(ds_[:10])
            f_ = (only[1] if d0 < only[0] <= today_i else 1.0) if only else split_factor(tk, d0, today_i)
            if f_ != 1.0:
                x.setdefault("dividende_publie", x["dividende"])
                x["dividende"] = round(x["dividende"] / f_, 4)
                x["ajust"] = round((x.get("ajust") or 1.0) * f_, 6)

    # versements en double (même titre, même exercice, même montant à 1 % près, dates à 75 jours près ou absentes) : un bulletin de
    # l'ancien site lu avec une date décalée d'un mois, ou un avis et un bulletin pour le même versement — le mieux renseigné est gardé
    # (date de détachement, date d'annonce, source officielle). Les paiements fractionnés (montants différents) ne sont pas concernés.
    # À qualité égale (deux lectures de bulletins), la lecture dont le paiement tombe un jour ouvré l'emporte : « 2-avr-11 », un
    # samedi, est une coquille pour le 2 mai (BOA Bénin et BOA Burkina 2010)
    def wd_(s):
        try:
            return dt.date.fromisoformat(str(s)[:10]).weekday() < 5
        except ValueError:
            return False

    def dq_(x):
        return (bool(x.get("date_detachement")), bool(x.get("date_annonce")), x.get("source") not in ("BOC", None), bool(x.get("date_paiement")),
                wd_(x.get("date_paiement") or x.get("date_detachement") or ""))
    by_ = collections.defaultdict(list)
    for x in divs:
        if x.get("ticker") and x.get("exercice") and x.get("dividende") and not x.get("exc"):
            by_[(x["ticker"], int(x["exercice"]))].append(x)
    drop_, dd_rm = set(), []
    for (t, ex_), xs in by_.items():
        if len(xs) < 2:
            continue
        xs = sorted(xs, key=dq_, reverse=True)
        for i_, a_ in enumerate(xs):
            if id(a_) in drop_:
                continue
            for b_ in xs[i_ + 1:]:
                if id(b_) in drop_ or abs(a_["dividende"] - b_["dividende"]) > .01 * max(a_["dividende"], b_["dividende"]):
                    continue
                da_, db_ = (a_.get("date_paiement") or a_.get("date_detachement")), (b_.get("date_paiement") or b_.get("date_detachement"))
                try:
                    if da_ and db_ and abs((dt.date.fromisoformat(da_[:10]) - dt.date.fromisoformat(db_[:10])).days) > 75:
                        continue
                except ValueError:
                    continue
                drop_.add(id(b_))
                dd_rm.append(f"{t} {ex_} {b_['dividende']:g} ({b_.get('date_paiement') or b_.get('date_detachement') or 'sans date'})")
    if drop_:
        divs[:] = [x for x in divs if id(x) not in drop_]
        log("versements en double retirés :", "; ".join(dd_rm))
    status = json.load(open(os.path.join(src, "trading_status.json"), encoding="utf8"))
    session = json.load(open(a.session, encoding="utf8")) if a.session and os.path.exists(a.session) else None
    sess_rows = {r["t"]: r for r in (session or {}).get("rows", [])}
    sess_d = di(session["asof"]) if session else None
    last_div = {}
    for x in divs:
        t = x.get("ticker")
        if not t or not x.get("dividende") or x.get("exc"):
            continue  # (dividende exceptionnel : hors dividende de référence et rendement indicatif, compté dans le rendement total)
        k = (x.get("exercice") or 0, x.get("date_paiement") or "")
        if t not in last_div or k > last_div[t][0]:
            last_div[t] = (k, x)
    for act in acts:
        t = act["ticker"]
        p = os.path.join(src, act["csv"] + ".csv")
        if not os.path.exists(p):
            log("missing csv", t)
            continue
        rows = load_brvm_csv(p)
        # séances fantômes de la base : week-end, ou jour sans bulletin officiel (férié) où la ligne recopie la veille (même cours,
        # même volume) — retirées, la BRVM n'a pas coté ce jour-là
        n0_ = len(rows)
        rows = [r for j_, r in enumerate(rows) if not (is_weekend(r[0]) or (j_ and no_session(r[0]) and r[4] == rows[j_ - 1][4] and r[5] == rows[j_ - 1][5]))]
        if len(rows) < n0_:
            boc_chk["phantom"] = boc_chk.get("phantom", 0) + n0_ - len(rows)
            boc_chk.setdefault("phantom_by", {})[t] = n0_ - len(rows)
        if BOC.get(t) and rows:  # contrôle des clôtures, puis séances manquantes après la fin de la base complétées par les bulletins
            B_ = BOC[t]
            ck = [(r[4], B_[r[0]]["c"]) for r in rows if r[0] in B_ and B_[r[0]].get("c")]
            nd_ = sum(1 for x, y in ck if abs(x / y - 1) > .005)
            boc_chk["n"] += len(ck)
            boc_chk["diff"] += nd_
            if ck:
                boc_chk["by"][t] = [len(ck), nd_]
            # séances échangées absentes de la base au milieu de l'historique (jour entier manquant, ex. 27/02/2025) : reprises du
            # bulletin officiel, ramenées sur la base de la série (facteur local = rapport médian série / bulletin des séances voisines,
            # seulement s'il est stable) ; volume ramené du même facteur, montant échangé tel quel
            have_ = {r[0] for r in rows}
            gaps_ = [k for k in B_ if rows[0][0] < k < rows[-1][0] and k not in have_ and (B_[k].get("vol") or 0) > 0 and B_[k].get("c")
                     and not is_weekend(k)]
            if gaps_:
                import bisect
                qd_ = sorted((r[0], r[4] / B_[r[0]]["c"]) for r in rows if r[4] and (B_.get(r[0]) or {}).get("c"))
                ks_ = [x[0] for x in qd_]
                ins_ = []
                days_ = [r[0] for r in rows]
                by_day_ = {r[0]: r for r in rows}
                for k in sorted(gaps_):
                    i0 = bisect.bisect_left(ks_, k)
                    win = sorted(q for _, q in qd_[max(0, i0 - 10):i0 + 10])
                    if len(win) < 5:
                        continue
                    m_ = win[len(win) // 2]
                    if sum(1 for q in win if abs(q / m_ - 1) <= .005) < .7 * len(win):
                        continue  # (opération sur titres toute proche : facteur incertain, séance laissée manquante)
                    from fractions import Fraction
                    fr_ = Fraction(m_).limit_denominator(40)
                    if abs(float(fr_) / m_ - 1) < .003:
                        m_ = float(fr_)  # (rapport d'une opération sur titres : 1, 1/2, 2/3… exactement, sans bruit d'arrondi)
                    rb_ = B_[k]
                    c_, o_ = round(rb_["c"] * m_, 2), round((rb_.get("o") or rb_["c"]) * m_, 2)
                    # (séance cohérente avec ses voisines : cours précédent du bulletin = clôture de la veille dans la série, et cours
                    # précédent du bulletin suivant = cette clôture ; un bulletin daté d'un jour férié qui reprend la séance de la veille,
                    # ou une ligne identique à la veille, est écarté)
                    i_s = bisect.bisect_left(days_, k)
                    pv_ = by_day_[days_[i_s - 1]] if i_s > 0 else None
                    nx_k = next((k2 for k2 in sorted(B_) if k2 > k), None)
                    if pv_ and rb_.get("prev") and abs(rb_["prev"] * m_ / pv_[4] - 1) > .01:
                        continue
                    if nx_k and (B_[nx_k].get("prev")) and abs(B_[nx_k]["prev"] * m_ / c_ - 1) > .01:
                        continue
                    if pv_ and abs(pv_[4] - c_) < 1e-9 and pv_[5] == int(round((rb_.get("vol") or 0) / m_)):
                        continue
                    pk_ = next((k2 for k2 in sorted(B_, reverse=True) if k2 < k), None)
                    if pk_ and all(B_[pk_].get(c2) == rb_.get(c2) for c2 in ("prev", "o", "c", "vol", "val")):
                        continue  # (bulletin d'un jour férié qui recopie celui de la veille)
                    nr_ = (k, o_, max(o_, c_), min(o_, c_), c_, int(round((rb_.get("vol") or 0) / m_)), int(rb_.get("val") or 0))
                    ins_.append(nr_)
                    bisect.insort(days_, k)  # (plusieurs séances manquantes de suite : la suivante se raccorde à celle-ci)
                    by_day_[k] = nr_
                if ins_:
                    rows = sorted(rows + ins_, key=lambda r: r[0])
                    boc_chk["gap_fill"] = boc_chk.get("gap_fill", 0) + len(ins_)
                    gfb_ = boc_chk.setdefault("gap_fill_by", {})
                    gfb_[t] = gfb_.get(t, 0) + len(ins_)
            last_d = rows[-1][0]
            for k in sorted(B_):
                if k <= last_d:
                    continue
                r = B_[k]
                c_ = r.get("c") or r.get("ref")
                if not c_:
                    continue
                o_ = r.get("o") or c_
                rows.append((k, o_, max(o_, c_), min(o_, c_), c_, int(r.get("vol") or 0), int(r.get("val") or 0)))
                boc_chk["added"] += 1
        if t in sess_rows and sess_d and rows and sess_d >= rows[-1][0]:
            s = sess_rows[t]
            bar = (sess_d, s.get("o") or s["c"], max(s["c"], s.get("o") or s["c"]), min(s["c"], s.get("o") or s["c"]), s["c"], s.get("vol", 0), int((s.get("vol") or 0) * s["c"]))
            rows = [r for r in rows if r[0] != sess_d] + [bar]
        # volumes et montants échangés : ceux du bulletin officiel de la cote quand il existe (montant jugé lisible s'il est à ±30 % de volume × cours) ;
        # sinon le montant du jour n'est qu'une estimation (volume × cours de clôture), signalée comme telle
        val_est = bool(rows) and rows[-1][0] == sess_d and t in sess_rows
        if BOC.get(t) and rows:
            B_ = BOC[t]
            for i_, r in enumerate(rows):
                b_ = B_.get(r[0])
                if b_ and b_.get("val") and b_.get("vol") and r[4] and 0.7 < b_["val"] / (b_["vol"] * r[4]) < 1.3:
                    # (montant du bulletin imprimé en milliers, égal au montant à l'unité déjà en place : on garde le plus précis)
                    keep_ = b_.get("val_k") and int(b_["vol"]) == r[5] and r[6] and abs(r[6] - b_["val"]) <= 1000
                    if not keep_ and (int(b_["vol"]), int(b_["val"])) != (r[5], r[6]):
                        boc_chk["val_fix"] = boc_chk.get("val_fix", 0) + 1
                    if not keep_:
                        rows[i_] = tuple(r[:5]) + (int(b_["vol"]), int(b_["val"]))
                    if r[0] == rows[-1][0]:
                        val_est = False
        if len(rows) < 3:
            continue
        f = fund.get(t, {})
        shares = f.get("nb_titres")
        bnpa_, dfund_ = f.get("bnpa"), f.get("dividende")
        # fractionnement ou regroupement absent de la base d'avis : sur la BRVM la variation d'une séance est bornée (±7,5 %),
        # un écart égal à un rapport usuel (2, 5, 10…) et confirmé par les deux séances suivantes ne peut être qu'une opération sur titres
        STD_ = [2, 3, 4, 5, 10, 20, 25, 40, 50, 64, 100]
        i2d = lambda x: dt.date(x // 10000, x // 100 % 100, x % 100)  # noqa: E731

        def jump_at(e0, k0):  # le cours saute-t-il du rapport k0 à la date e0 ?
            j0 = next((j for j, r in enumerate(rows) if r[0] >= e0), None)
            return bool(j0 and rows[j0 - 1][4] and rows[j0][4] and abs(math.log((rows[j0 - 1][4] / rows[j0][4]) / k0)) < min(math.log(1.4), abs(math.log(k0)) / 3))
        for i_ in range(1, len(rows) - 1):
            a_, b_ = rows[i_ - 1][4], rows[i_][4]
            if not a_ or not b_ or 0.6 < a_ / b_ < 1.65:
                continue
            r_ = a_ / b_
            k_ = next((float(k) for k in STD_ if abs(math.log(r_ / k)) < math.log(1.12)), None) or next((1.0 / k for k in STD_ if abs(math.log(r_ * k)) < math.log(1.12)), None)
            if not k_ or not (rows[i_ + 1][4] and abs(rows[i_ + 1][4] / b_ - 1) < .25):
                continue  # confirmé par la séance suivante (une erreur de saisie isolée est ignorée)
            e_ = rows[i_][0]
            near = [(e0, k0) for e0, k0 in SPL.get(t, []) if abs((i2d(e0) - i2d(e_)).days) < 400 and abs(k0 - k_) < 1e-6]
            if any(abs((i2d(e0) - i2d(e_)).days) < 45 for e0, _ in near):
                continue  # même opération que l'avis
            if near and not jump_at(near[0][0], near[0][1]):
                # la source des cours a appliqué l'opération à une autre date que l'avis : les cours sont ajustés à la date du saut,
                # les dividendes et données par action restent rattachés à la date d'effet de l'avis
                PX_DATE[(t, near[0][0])] = e_
                split_log.append(f"{t} {e_} x{k_:g} : saut de cours rattaché à l'avis du {near[0][0]}")
            else:
                SPL[t].append((e_, k_))
                split_log.append(f"{t} {e_} x{k_:g} : opération détectée sur les cours (sans avis dans la base)")
        # opérations sur le capital (fractionnements, actions gratuites) que la base de cours a déjà ajustées sans qu'aucun avis lu ne les
        # décrive : le rapport « clôture du bulletin officiel ÷ cours de la série » change alors de palier. Chaque palier durable (plus de
        # 5 %, confirmé sur 10 séances) est une opération : les dividendes antérieurs sont ramenés sur la même base que les cours.
        if BOC.get(t) and rows:
            B_ = BOC[t]
            qs = [(r[0], B_[r[0]]["c"] / r[4]) for r in rows if r[4] and (B_.get(r[0]) or {}).get("c")]
            med = []
            for j in range(len(qs)):
                w_ = sorted(x for _, x in qs[max(0, j - 4):j + 5])
                med.append((qs[j][0], w_[len(w_) // 2]))
            j = 0
            while j < len(med) - 10:
                a0, a1 = med[j][1], med[j + 1][1]
                if a0 > 0 and a1 > 0 and abs(a1 / a0 - 1) > .05 and all(abs(med[j + m][1] / a1 - 1) < .02 for m in range(1, 11)) \
                        and all(abs(med[max(0, j - m)][1] / a0 - 1) < .02 for m in range(0, 6)):
                    k_ = a0 / a1
                    from fractions import Fraction
                    fr_ = Fraction(k_).limit_denominator(10)
                    if abs(float(fr_) / k_ - 1) < .005:
                        k_ = float(fr_)
                    e_ = med[j + 1][0]
                    # (même opération qu'un avis déjà lu, effective quelques semaines après sa date : pas comptée deux fois ; rapport lu
                    # dans l'avis démenti par le palier des cours — base et bulletin ajustés d'un autre rapport — : celui du palier, seulement
                    # si le palier tombe à moins de 60 jours de l'avis ; plus loin, avec un autre rapport, c'est une autre opération)
                    near_ = [(i_, e0, k0) for i_, (e0, k0) in enumerate(SPL.get(t, [])) if abs((i2d(e0) - i2d(e_)).days) < 60]
                    if k_ > 1 and near_ and all(abs(k0 / k_ - 1) >= .05 for _, _, k0 in near_) and len(near_) == 1:
                        i_, e0, k0 = near_[0]
                        SPL[t][i_] = (e0, round(k_, 6))
                        split_log.append(f"{t} {e0} x{k0:g} -> x{k_:g} : rapport corrigé d'après le palier des cours du bulletin officiel")
                    elif k_ > 1 and not any(abs((i2d(e0) - i2d(e_)).days) < 30 or (abs((i2d(e0) - i2d(e_)).days) < 150 and abs(k0 / k_ - 1) < .05)
                                            for e0, k0 in SPL.get(t, [])):
                        SPL[t].append((e_, round(k_, 6)))
                        SPL_DONE.add((t, e_))
                        split_log.append(f"{t} {e_} x{k_:g} : opération sur le capital déduite du bulletin officiel (cours déjà ajustés)")
                    j += 10
                    continue
                j += 1
        # augmentation de capital avec droits préférentiels (ou autre opération sur le capital) que la base de cours n'a pas ajustée :
        # la veille de la cotation ex-droit, la BRVM abaisse le cours de référence nettement sous la clôture (de 10 % à 45 %) sans
        # dividende qui l'explique, et la séance suivante part de ce cours de référence. Les cours antérieurs sont ramenés sur la
        # nouvelle base par le rapport clôture ÷ cours de référence (ex. SAFC 24/04/2026, droits préférentiels de souscription)
        if BOC.get(t) and rows:
            B_ = BOC[t]
            bd_ = sorted(B_)
            for i_, d_ in enumerate(bd_[:-1]):
                rb_, nx_ = B_[d_], B_[bd_[i_ + 1]]
                c_, ref_ = rb_.get("c"), rb_.get("ref")
                if not c_ or not ref_ or not (1.1 < c_ / ref_ < 1.8):
                    continue
                e_ = bd_[i_ + 1]
                if not nx_.get("prev") or abs(nx_["prev"] / ref_ - 1) > .005 or not nx_.get("c") or abs(nx_["c"] / ref_ - 1) > .1:
                    continue  # (séance suivante qui ne part pas du cours de référence : lecture douteuse)
                try:
                    dd_ = nx_.get("div_d")
                    if dd_ and abs((dt.date.fromisoformat(str(dd_)[:10]) - i2d(e_)).days) <= 7:
                        continue  # dividende détaché ce jour-là (bulletin)
                except ValueError:
                    pass
                dv_ = sum((x.get("dividende_publie") or x["dividende"]) for x in divs if x.get("ticker") == t and x.get("dividende")
                          and any(x.get(kk) and abs((i2d(di(x[kk][:10])) - i2d(e_)).days) <= 7 for kk in ("date_detachement", "date_paiement")))
                if dv_ and abs(dv_ / (c_ - ref_) - 1) < .25:
                    continue  # baisse expliquée par le dividende détaché
                if any(abs((i2d(e0) - i2d(e_)).days) < 45 for e0, _ in SPL.get(t, [])):
                    continue  # opération déjà connue (avis, palier des cours)
                SPL[t].append((e_, round(c_ / ref_, 6)))
                split_log.append(f"{t} {e_} x{c_ / ref_:.4f} : opération sur le capital (cours de référence abaissé par la BRVM la veille, sans dividende)")
        # opérations vérifiées à la main (seed/operations_historiques.json) : la base de cours les a-t-elle déjà ajustées ? Le rapport
        # « clôture du bulletin ÷ série » (médiane de 10 séances de part et d'autre de la date d'effet) change du rapport de l'opération
        # si la base a ajusté, reste le même sinon. Déjà ajustées : rien n'est refait sur les cours ; non ajustées : cours antérieurs
        # ramenés (volumes multipliés) même sans saut net. Bulletins absents autour de la date (avant décembre 2013) : le champ « cours »
        # de la ligne décide ; rapport lu ni l'un ni l'autre, ou contraire à ce champ : cours laissés, signalé
        for (t0_, e_), o_ in OPH.items():
            if t0_ != t or e_ > rows[-1][0]:
                continue
            k_ = next((k0 for e0, k0 in SPL.get(t, []) if e0 == e_), None)
            if not k_:
                continue
            B_ = BOC.get(t) or {}
            qb_ = [(r[0], B_[r[0]]["c"] / r[4]) for r in rows if r[4] and (B_.get(r[0]) or {}).get("c")]
            av_ = sorted([q for d_, q in qb_ if d_ < e_][-10:])  # (10 dernières séances avant la date d'effet)
            ap_ = sorted([q for d_, q in qb_ if d_ >= e_][:10])  # (10 premières à partir d'elle)
            tol_ = min(.01, abs(math.log(k_)) / 3)
            decl_ = o_.get("cours")  # (« a_ajuster » ou « deja_ajustes », constaté à la main)
            if len(av_) >= 5 and len(ap_) >= 5:
                q_ = av_[len(av_) // 2] / ap_[len(ap_) // 2]
                lu_ = "a_ajuster" if abs(math.log(q_)) < tol_ else "deja_ajustes" if abs(math.log(q_ / k_)) < tol_ else None
                if lu_ and decl_ in (None, lu_):
                    (SPL_FORCE if lu_ == "a_ajuster" else SPL_DONE).add((t, e_))
                    split_log.append(f"{t} {e_} x{k_:g} : opération vérifiée (seed), cours de la base "
                                     f"{'non ajustés' if lu_ == 'a_ajuster' else 'déjà ajustés'} (rapport bulletin ÷ série {q_:.4f})")
                    continue
                print(f"::warning::Construction : {t} {e_} opération vérifiée x{k_:g}, rapport bulletin ÷ série {q_:.4f} "
                      f"({lu_ or 'incohérent'}, ligne : {decl_}) : cours laissés")
            elif decl_ in ("a_ajuster", "deja_ajustes"):
                (SPL_FORCE if decl_ == "a_ajuster" else SPL_DONE).add((t, e_))
                split_log.append(f"{t} {e_} x{k_:g} : opération vérifiée (seed), sans bulletin autour de la date : cours "
                                 f"{'ramenés' if decl_ == 'a_ajuster' else 'de la base déjà ajustés'} (constat de la ligne)")
                continue
            split_log.append(f"{t} {e_} x{k_:g} : opération vérifiée (seed), cours laissés (rapport bulletin ÷ série non vérifiable)")
            SPL_DONE.add((t, e_))
        # versement payé avant une opération mais lu dans un bulletin qui l'a déjà ramené sur la nouvelle base (« dividendes ajustés
        # par rapport au fractionnement ») : la lecture d'avant l'opération (contrôle « chk » de la branche dividendes, dans le rapport
        # exact de l'opération) est le montant publié, que adj_divs ramène ensuite ; sans cela il serait divisé deux fois (Sonatel 2011 :
        # 13 050 au bulletin du 30/04/2012, 1 305 au bulletin du 31/12/2012, fractionnement du 23/11/2012)
        for x in divs:
            if x.get("ticker") != t or not x.get("dividende") or not x.get("chk_off") or x.get("ajust"):
                continue
            ds_ = x.get("date_detachement") or x.get("date_paiement")
            if not ds_:
                continue
            d0 = di(ds_[:10])
            for s_, a_, dc_ in x["chk_off"]:
                try:
                    dc_i = di(str(dc_)[:10])
                except (TypeError, ValueError):
                    continue
                k0_ = next((k0 for e0, k0 in sorted(SPL.get(t, [])) if d0 < e0 <= today_i and dc_i < e0
                            and abs(float(a_) / (x["dividende"] * k0) - 1) < .005), None)
                if s_ == "bulletin" and k0_:
                    split_log.append(f"{t} {x.get('exercice')} : {x['dividende']:g} déjà ramené par le bulletin, montant publié {float(a_):g} (lecture du {dc_})")
                    x["dividende"] = float(a_)
                    break
        if t in SPL:
            adj_divs(t)
        for e_, k_ in sorted(SPL.get(t, [])):
            if e_ > rows[-1][0]:
                continue  # pas encore effectif
            if (t, e_) in SPL_DONE:
                continue  # (opération lue sur les paliers du bulletin : cours de la base déjà ajustés, données par action aussi)
            ep_ = PX_DATE.get((t, e_), e_)
            i_ = next((j for j, r in enumerate(rows) if r[0] >= ep_), None)
            if i_ and rows[i_ - 1][4] and rows[i_][4] and ((t, e_) in SPL_FORCE or abs(math.log((rows[i_ - 1][4] / rows[i_][4]) / k_)) < min(math.log(1.4), abs(math.log(k_)) / 3)):  # (petit rapport : saut net exigé, sauf opération vérifiée)
                rows = [(r[0], r[1] / k_, r[2] / k_, r[3] / k_, r[4] / k_, int(round(r[5] * k_)), r[6]) if j < i_ else r for j, r in enumerate(rows)]
                split_log.append(f"{t} {e_} x{k_:g} : cours antérieurs ajustés")
                force_write.add(t)
            if (t, e_) in SPL_FORCE:
                continue  # (opération vérifiée à la main, petit rapport : données par action de la fiche laissées à l'étape des BNPA par exercice)
            # données par action de la fiche société : ajustées si elles datent d'avant le fractionnement
            src_d = di(str(f.get("date_source") or "2000-01-01")[:10])
            per_boc = None
            if BOC.get(t):
                kb = max(BOC[t])
                per_boc = BOC[t][kb].get("per") if kb >= e_ else None
            stale = src_d < e_
            if per_boc and bnpa_ and bnpa_ > 0 and rows[-1][4]:
                r_ = (rows[-1][4] / bnpa_) / per_boc
                stale = abs(math.log(r_ * k_)) < math.log(1.4)  # PER calculé ≈ PER officiel ÷ k : BNPA encore par action ancienne
            if stale:
                bnpa_ = bnpa_ / k_ if bnpa_ else bnpa_
                dfund_ = dfund_ / k_ if dfund_ else dfund_
                ser_ = f.get("series") or {}
                for key_ in ("bnpa", "dividende"):
                    for y_, v_ in list((ser_.get(key_) or {}).items()):
                        if v_ is not None and di(f"{int(y_) + 1}-04-30") < e_:
                            ser_[key_][y_] = v_ / k_
                split_log.append(f"{t} {e_} x{k_:g} : BNPA et dividende par action ajustés")
            if shares and not (sess_rows.get(t) or {}).get("sh") and (f.get("provenance_champs") or {}).get("nb_titres") == "fichier_initial" and e_ >= 20250101:
                shares = shares * k_
                f["nb_titres"] = shares
                split_log.append(f"{t} {e_} x{k_:g} : nombre de titres ajusté")
        # dividendes lus dans un bulletin à côté du cours du jour (premier bulletin après le paiement) : le rapport « cours du bulletin
        # ÷ cours de la série le même jour » donne la base d'actions du montant publié (opérations sur le capital antérieures aux
        # bulletins conservés comprises) ; un ajustement qui s'en écarte de plus de 30 % est remplacé par ce rapport (rapport simple)
        import bisect
        dts_ = [r[0] for r in rows]
        miss_k = {}
        for x in divs:
            if x.get("ticker") != t or not x.get("px_raw") or not x.get("px_d") or not x.get("dividende"):
                continue
            ds_ = str(x.get("date_paiement") or x.get("date_detachement") or "")[:10]
            if not ds_:
                continue
            d0 = di(ds_)
            dp_ = di(x["px_d"])
            j_ = bisect.bisect_right(dts_, dp_) - 1
            if j_ < 0 or dp_ - dts_[j_] > 15 or not rows[j_][4]:
                continue  # (pas de séance de la série dans la quinzaine du bulletin : pas de contrôle)
            f_obs = x["px_raw"] / rows[j_][4]
            f_now = x.get("ajust") or 1.0
            if f_obs > 0 and abs(math.log(f_obs / f_now)) > math.log(1.3):
                # (rapport attendu : opérations connues après le paiement, multipliées éventuellement par une opération plus ancienne
                # que les bulletins conservés, de rapport simple)
                aft_ = [k0 for e0, k0 in sorted(SPL.get(t, [])) if d0 < e0 <= today_i]
                prods_ = {1.0} | {math.prod(aft_[i0:]) for i0 in range(len(aft_))}
                cands_ = {p0 * r0 for p0 in prods_ for r0 in (1, 2, 2.5, 3, 4, 5, 10, 20, 25, 50, 100)}
                k_ = min(cands_, key=lambda c_: abs(math.log(f_obs / c_)))
                if abs(math.log(f_obs / k_)) > math.log(1.12) or abs(math.log(k_ / f_now)) < 1e-9:
                    continue
                if k_ > 0:
                    pub_ = x.get("dividende_publie", x["dividende"])
                    x["dividende_publie"], x["dividende"], x["ajust"] = pub_, round(pub_ / k_, 4), round(k_, 6)
                    if abs(k_ - 1) < 1e-9:
                        x.pop("ajust", None)
                    boc_chk.setdefault("div_base", []).append(f"{t} {x.get('exercice')} ÷{k_:g} (avant ÷{f_now:g} ; cours {x['px_raw']:g} / {rows[j_][4]:g} le {dts_[j_]})")
                    miss_k.setdefault(t, []).append((dp_, k_ / f_now))
        # même opération manquante pour les dividendes voisins sans cours lu : un montant antérieur à la dernière observation, dont le
        # rendement au cours du jour serait invraisemblable (plus de 35 %) et redevient normal une fois ramené par ce rapport
        if len({round(k0, 6) for _, k0 in miss_k.get(t, [])}) == 1:
            last_obs, km_ = max(miss_k[t])
            for x in divs:
                if x.get("ticker") != t or x.get("px_raw") or not x.get("dividende"):
                    continue
                ds_ = str(x.get("date_paiement") or x.get("date_detachement") or "")[:10]
                if not ds_:
                    continue
                d0 = di(ds_)
                j_ = bisect.bisect_right(dts_, d0) - 1
                if j_ < 0 or not rows[j_][4] or d0 > last_obs + 20000:
                    continue
                y_ = x["dividende"] / rows[j_][4]
                if y_ > .35 and .002 <= y_ / km_ <= .35:
                    pub_ = x.get("dividende_publie", x["dividende"])
                    f_ = (x.get("ajust") or 1.0) * km_
                    x["dividende_publie"], x["dividende"], x["ajust"] = pub_, round(pub_ / f_, 4), round(f_, 6)
                    boc_chk.setdefault("div_base", []).append(f"{t} {x.get('exercice')} ÷{f_:g} (même opération ; rendement {y_:.0%} sinon)")
        # montant lu dans un ancien bulletin ou une revue (source la plus faible) dont le rendement au cours du jour du paiement reste
        # invraisemblable (moins de 0,1 % ou plus de 50 %) : lecture fautive, versement retiré plutôt qu'affiché faux
        for x in divs:
            if x.get("ticker") != t or not x.get("weak") or not x.get("dividende"):
                continue
            ds_ = str(x.get("date_paiement") or x.get("date_detachement") or "")[:10]
            if not ds_:
                continue
            j_ = bisect.bisect_right(dts_, di(ds_)) - 1
            if j_ >= 0 and rows[j_][4]:
                y_ = x["dividende"] / rows[j_][4]
            elif x.get("px_raw"):  # (paiement antérieur à la série de cours : cours imprimé dans le bulletin, même base d'actions)
                y_ = x.get("dividende_publie", x["dividende"]) / x["px_raw"]
            else:
                continue
            if not (.001 <= y_ <= .5):
                boc_chk.setdefault("div_rejete", []).append(f"{t} {x.get('exercice')} {x.get('dividende_publie', x['dividende']):g} (rendement {y_:.1%})")
                b_ = x.get("dividende_base")  # (montant de la base remplacé par cette lecture : rétabli s'il est, lui, vraisemblable)
                b_adj = b_ / (x.get("ajust") or 1.0) if b_ else None
                x["dividende"] = round(b_adj, 4) if b_adj and j_ >= 0 and rows[j_][4] and .001 <= b_adj / rows[j_][4] <= .5 else None
        # BNPA et dividende par exercice de la fiche : chaque exercice ramené sur la base des actions actuelles. La base de chaque
        # valeur se lit sur le nombre d'actions implicite (résultat net ÷ BNPA) : celui d'aujourd'hui (déjà ajusté), ou celui
        # d'avant une ou plusieurs opérations récentes (montant publié à l'époque, à diviser par le rapport de ces opérations)
        ops_ = sorted((e_, k_) for e_, k_ in SPL.get(t, []) if e_ <= rows[-1][0])
        sh_now = float((sess_rows.get(t) or {}).get("sh") or shares or 0)
        ser_ = f.get("series") or {}
        if ops_ and sh_now and ser_.get("bnpa"):
            for y_, v_ in list(ser_["bnpa"].items()):
                rn_ = (ser_.get("resultat_net") or {}).get(y_)
                if not v_ or not rn_ or (v_ > 0) != (rn_ > 0):
                    continue
                n_y = rn_ * 1e6 / v_
                aft = [k_ for e_, k_ in ops_ if e_ > di(f"{int(y_) + 1}-03-31")]
                cands = {1.0}
                for i_ in range(len(aft)):
                    p_ = math.prod(aft[i_:])
                    cands |= {p_, 1 / p_}
                best = min(cands, key=lambda c_: abs(math.log(n_y * c_ / sh_now)))
                if abs(best - 1) > 1e-6 and abs(math.log(n_y * best / sh_now)) < math.log(1.1) and abs(math.log(n_y / sh_now)) > math.log(1.25):
                    ser_["bnpa"][y_] = v_ / best
                    if (ser_.get("dividende") or {}).get(y_):
                        ser_["dividende"][y_] = ser_["dividende"][y_] / best
                    boc_chk.setdefault("bnpa_base", []).append(f"{t} {y_} ÷{best:g}")
        # cours de clôture officiels (bulletin de la cote) prioritaires : la série reste ajustée des opérations sur titres
        # (facteur local = rapport médian série / bulletin sur les séances voisines) ; une clôture qui s'en écarte de plus de 0,5 %
        # est remplacée par la clôture officielle, si le bulletin est cohérent (cours précédent × variation = clôture)
        if BOC.get(t) and rows:
            B_ = BOC[t]
            qs = [(j, r[4] / B_[r[0]]["c"]) for j, r in enumerate(rows) if r[4] and (B_.get(r[0]) or {}).get("c")]
            for n_q, (j, q) in enumerate(qs):
                win = sorted(x for _, x in qs[max(0, n_q - 10):n_q + 11])
                m_ = win[len(win) // 2]
                # (série non ajustée à cette date — facteur exactement 1 — : toute différence avec la clôture officielle est corrigée ;
                # série ajustée d'une opération sur titres : écart de plus de 0,5 % au facteur local)
                tol_ = 1e-6 if abs(m_ - 1) < 1e-9 else .005
                # (facteur local stable : 70 % des séances voisines au même rapport ; série non ajustée — rapport exactement 1 —
                # 50 % suffisent, plusieurs clôtures fausses de la base pouvant se suivre)
                if abs(q / m_ - 1) <= tol_ or sum(1 for x in win if abs(x / m_ - 1) <= .005) < (.5 if abs(m_ - 1) < 1e-9 else .7) * len(win):
                    continue
                b_ = B_[rows[j][0]]
                if b_.get("prev") and b_.get("var") is not None and abs(b_["prev"] * (1 + b_["var"] / 100) / b_["c"] - 1) > .006:
                    continue  # bulletin incohérent ce jour-là : la série est gardée
                c_new = b_["c"] * m_
                o_new = b_["o"] * m_ if b_.get("o") else rows[j][1]
                r = rows[j]
                rows[j] = (r[0], o_new, max(r[2], o_new, c_new), min(r[3], o_new, c_new), c_new) + tuple(r[5:])
                boc_chk["close_fix"] = boc_chk.get("close_fix", 0) + 1
                cfb_ = boc_chk.setdefault("close_fix_by", {})
                cfb_[t] = cfb_.get(t, 0) + 1
                if not a.live:
                    force_write.add(t)
        # données officielles de la BRVM, prioritaires sur les sites tiers :
        # nombre de titres et capitalisation flottante (page « Capitalisations » de brvm.org), PER et dividende du bulletin officiel de la cote
        so_ = sess_rows.get(t) or {}
        flt_off = None
        if so_.get("sh"):
            shares = float(so_["sh"])
            if so_.get("capf") and so_.get("capg"):
                flt_off = round(so_["capf"] / so_["capg"] * 100, 2)
        bnpa_off = None
        if BOC.get(t):
            for kb in sorted(BOC[t], reverse=True)[:10]:  # dernier PER publié (le bulletin du jour peut manquer)
                rb = BOC[t][kb]
                cb = rb.get("c") or rb.get("ref")
                if rb.get("per") and rb["per"] > 0 and cb:
                    f_split = split_factor(t, kb, rows[-1][0])  # cours du bulletin antérieur à un fractionnement
                    bnpa_off = cb / rb["per"] / f_split
                    break
        if bnpa_off and bnpa_ and bnpa_ > 0 and abs(math.log(bnpa_ / bnpa_off)) > math.log(1.25):
            split_log.append(f"{t} : BNPA de la fiche ({bnpa_:g}) écarté, base officielle {bnpa_off:.2f}")
        MIROIR[t] = {"sh_fiche": f.get("nb_titres"), "sh_brvm": so_.get("sh"), "flt_fiche": f.get("flottant"), "flt_brvm": flt_off,
                     "sect_fiche": act.get("secteur"), "bnpa_fiche": f.get("bnpa"), "bnpa_off": round(bnpa_off, 4) if bnpa_off else None}
        if so_.get("sh"):
            f["nb_titres"] = shares
        if flt_off is not None:
            f["flottant"] = flt_off
        pso_ = "off" if bnpa_off else ("alt" if bnpa_ else None)
        # BNPA du bulletin = cours ÷ PER (PER arrondi à 2 décimales) : le BNPA publié par la société, s'il concorde à 1 % près, est gardé tel quel
        if bnpa_off and not (bnpa_ and bnpa_ > 0 and abs(bnpa_ / bnpa_off - 1) < .01):
            bnpa_ = bnpa_off
        # une seule convention pour le résumé et FA (audit du 20/10/2026, constat I-1) : le BNPA d'un exercice est le résultat net
        # des comptes affichés ÷ nombre de titres. Le bulletin calcule parfois son PER du même exercice sur un autre résultat (comptes
        # IFRS ou consolidés, quand FQT affiche les comptes SYSCOHADA sociaux : CABC, SDCC, TTLS, ONTBF). Quand le résultat net du
        # dernier exercice vient de comptes publiés et vérifiés, que le BNPA de la série en est le quotient par le nombre de titres et
        # que le BNPA du bulletin date de l'année qui suit cet exercice (même exercice), le BNPA de la série est retenu (PER = cours
        # ÷ BNPA, distribution = dividende ÷ BNPA, comme dans FA) et celui du bulletin est gardé à côté (« bnpa_bul »)
        bnpa_bul = None
        try:
            sb_l = {int(y_): v_ for y_, v_ in ((f.get("series") or {}).get("bnpa") or {}).items() if v_ is not None and str(y_).isdigit()}
            sr_l = {int(y_): v_ for y_, v_ in ((f.get("series") or {}).get("resultat_net") or {}).items() if v_ is not None and str(y_).isdigit()}
            y_l = max(sr_l) if sr_l else None
            if bnpa_off and bnpa_ == bnpa_off and y_l and (sb_l.get(y_l) or 0) > 0 and sr_l[y_l] > 0 and shares \
                    and abs(sb_l[y_l] * shares / (sr_l[y_l] * 1e6) - 1) <= .01 and abs(sb_l[y_l] / bnpa_off - 1) > .01:
                cc_l = f.get("cpt") or {}
                ver_ = False
                for g_ in (cc_l, cc_l.get("alt") or {}):
                    yy_ = g_.get("y") or {}
                    e_ = yy_.get(y_l) or yy_.get(str(y_l)) or {}
                    rv_ = (e_.get("v") or {}).get("resultat_net", (e_.get("v") or {}).get("resultat_bilan"))
                    if rv_ is not None and abs(rv_ - sr_l[y_l]) <= .6 and "resultat_net" not in (e_.get("w") or []):
                        ver_ = True
                # (date où le BNPA du bulletin a pris sa valeur actuelle : il se rapporte à l'exercice publié l'année précédente)
                k0_ = None
                for kb in sorted(BOC.get(t) or {}, reverse=True):
                    rb = BOC[t][kb]
                    cb = rb.get("c") or rb.get("ref")
                    if not (rb.get("per") and rb["per"] > 0 and cb):
                        continue
                    if abs(cb / rb["per"] / split_factor(t, kb, rows[-1][0]) / bnpa_off - 1) > .02:
                        break
                    k0_ = kb
                if ver_ and k0_ and k0_ // 10000 == y_l + 1:
                    bnpa_bul, bnpa_, pso_ = bnpa_off, sb_l[y_l], "fqt"
        except Exception as e:  # noqa: BLE001  (en cas de doute, le BNPA du bulletin reste)
            log("BNPA du dernier exercice : contrôle impossible pour", t, e)
        # le BNPA du bulletin reste au résumé (et le PER partout) quand le résultat du dernier exercice de la série n'est pas vérifié
        # (BICB 2025 : comptes IFRS vérifiés au bulletin, SYSCOHADA de la base tierce dans la série) ou quand le bulletin porte encore
        # sur un exercice plus ancien (SEMC : 2023 au bulletin, 2024 de la base tierce dans la série) : les deux BNPA ne sont alors
        # pas ceux d'un même résultat, et la mention de l'exercice dans FA (src_years) le dit, avec le BNPA du bulletin et son origine
        try:
            sb_n = {int(y_): v_ for y_, v_ in ((f.get("series") or {}).get("bnpa") or {}).items() if v_ is not None and str(y_).isdigit()}
            y_n = max(sb_n) if sb_n else None
            if pso_ == "off" and bnpa_off and bnpa_ and y_n and abs(sb_n[y_n] - bnpa_) > .02 * abs(bnpa_):
                k1_ = None  # (date où le BNPA du bulletin a pris sa valeur actuelle, à 1 % près : il porte sur l'exercice de l'année d'avant)
                for kb in sorted(BOC.get(t) or {}, reverse=True):
                    rb = BOC[t][kb]
                    cb = rb.get("c") or rb.get("ref")
                    if not (rb.get("per") and rb["per"] > 0 and cb):
                        continue
                    if abs(cb / rb["per"] / split_factor(t, kb, rows[-1][0]) / bnpa_off - 1) > .01:
                        break
                    k1_ = kb
                y_b = k1_ // 10000 - 1 if k1_ else None
                fr_ = lambda x_, d_=2: f"{x_:,.{d_}f}".replace(",", " ").replace(".", ",")  # noqa: E731
                orig_, ver_n = "", False
                cc_n = f.get("cpt") or {}
                for g_ in (cc_n, cc_n.get("alt") or {}):
                    e_ = (g_.get("y") or {}).get(y_n) or (g_.get("y") or {}).get(str(y_n)) or {}
                    rv_ = (e_.get("v") or {}).get("resultat_net", (e_.get("v") or {}).get("resultat_bilan"))
                    if rv_ is None:
                        continue
                    if abs(rv_ - ((f.get("series") or {}).get("resultat_net") or {}).get(str(y_n), float("nan"))) <= .6 and "resultat_net" not in (e_.get("w") or []):
                        ver_n = True
                    if y_b == y_n and shares and not orig_ and abs(rv_ * 1e6 / shares / bnpa_off - 1) <= .01:
                        orig_ = (f" (comptes {'IFRS' if g_.get('std') == 'ifrs' else 'SYSCOHADA'} {'consolidés' if g_.get('per') == 'conso' else 'sociaux'}"
                                 f" vérifiés : résultat net {fr_(rv_, 0)} M ÷ titres)")
                note_ = None
                if y_b == y_n:
                    note_ = (f"BNPA {y_n} du bulletin officiel (résumé, PER) : {fr_(bnpa_off)} FCFA{orig_}, autre résultat que celui de la série"
                             + ("" if ver_n else " (base tierce, aucun compte de cet exercice vérifié)"))
                elif y_b and y_b < y_n:
                    note_ = (f"exercice pas encore repris par le bulletin officiel : le BNPA du résumé ({fr_(bnpa_off)} FCFA) et le PER portent"
                             f" sur l'exercice {y_b}" + ("" if ver_n else " ; comptes de cet exercice de la base tierce, non vérifiés"))
                if note_ and note_ not in str((f.get("src_years") or {}).get(str(y_n)) or ""):
                    sy_ = f.setdefault("src_years", {})
                    sy_[str(y_n)] = (sy_[str(y_n)] + " ; " + note_) if sy_.get(str(y_n)) else note_
                    bnpa_notes.append(f"{t} {y_n}")
        except Exception as e:  # noqa: BLE001
            log("BNPA du bulletin et de la série : mention impossible pour", t, e)
        cty = "BF" if t.endswith("BF") else CTY.get(t[-1], "CI")
        ld = last_div.get(t, (None, {}))[1]
        last = rows[-1][4]
        # rendement : seulement si le dernier dividende a moins de deux ans (une société qui ne verse plus n'a pas de rendement)
        ld_d = str(ld.get("date_paiement") or ld.get("date_detachement") or (f'{int(ld["exercice"]) + 1}-12-31' if ld.get("exercice") else ""))[:10]
        ld_recent = bool(ld_d) and di(ld_d) >= today_i - 20000
        # dividende de l'exercice : ses versements ordinaires réunis (acompte et solde, dividende complémentaire)
        ld_tot = (sum(x["dividende"] for x in divs if x.get("ticker") == t and x.get("dividende") and not x.get("exc") and x.get("exercice") == ld.get("exercice"))
                  if ld.get("exercice") and ld.get("dividende") else ld.get("dividende"))
        # taux de distribution = dividende ÷ BNPA du MÊME exercice : quand le dernier dividende est plus ancien que le dernier BNPA
        # (pas de dividende au titre du dernier exercice, ou pas encore décidé), le BNPA de son exercice est lu dans la série de la
        # fiche ; le rapport au BNPA d'un autre exercice ne veut rien dire (Filtisac : 1 161,6 ÷ 33,04 = 3 516 % au lieu de 88 %)
        dps_ = rnd(ld_tot, 4) if ld_tot else dfund_
        try:
            ex_ = int(ld.get("exercice")) if ld.get("exercice") is not None else None
        except (TypeError, ValueError):
            ex_ = None
        bser_ = {}
        for y_, v_ in ((f.get("series") or {}).get("bnpa") or {}).items():
            if v_ is not None and str(y_).isdigit():
                bser_[int(y_)] = v_
        eps_ = bnpa_ if ex_ is None or not bser_ or ex_ >= max(bser_) else bser_.get(ex_)
        pay_ = rnd(dps_ / eps_, 4) if dps_ and eps_ and eps_ > 0 else None
        meta = {"id": t, "tk": f"{t} BC", "n": act.get("nom_officiel") or act.get("nom"), "short": act.get("nom"), "cls": "Equity", "typ": "Equity",
                "mkt": "BRVM", "grp": SECT_OFF.get(t) or act.get("secteur"), "ccy": "XOF", "bench": "BRVMC", "cty": cty, "bank": bool(act.get("banque")),
                "shares": shares, "float": flt_off if flt_off is not None else f.get("flottant"), "mcap": rnd(shares * last, 0) if shares else None, "pso": pso_,
                "bnpa": rnd(bnpa_, 2) if bnpa_ else bnpa_, "dps": rnd(ld_tot, 4) if ld_tot else dfund_, "dps_ex": ld.get("exercice"), "dps_pay": ld.get("date_paiement"),
                "dps_adj": ld.get("ajust"), "pay": pay_, "split": [[e_, k_] for e_, k_ in sorted(SPL.get(t, []))] or None,
                "per": rnd(last / bnpa_, 2) if bnpa_ and bnpa_ > 0 else None,
                "yld": rnd(ld_tot / last, 6) if ld_tot and ld_recent else None,
                "susp": (status.get(t) or {}).get("statut") == "suspendue", **({"vde": 1} if val_est else {}),
                **({"bnpa_bul": rnd(bnpa_bul, 2)} if bnpa_bul else {})}
        add(meta, [r[0] for r in rows], [r[4] for r in rows], [r[1] for r in rows], [r[2] for r in rows], [r[3] for r in rows],
            [r[5] for r in rows], [r[6] for r in rows], nd=2)
    # avis de la base sur une opération sur le capital à parité lisible (fractionnement, regroupement, actions gratuites) sans
    # opération de la liste à 30 jours près : signalé, jamais appliqué sans date d'effet prouvée (à vérifier au bulletin — l'effet
    # tombe en général deux séances avant l'arrêté des registres — puis à inscrire dans seed/operations_historiques.json)
    ost_nl = []
    listed_ = {x_.get("ticker") for x_ in acts}
    for x in EVS_:
        try:
            dd_ = x.get("details") or {}
            if x.get("category") not in ("stock_split", "reverse_split", "bonus_issue") or x.get("ticker") not in listed_ or not x.get("event_at") \
                    or not dd_.get("ratio_new") or not dd_.get("ratio_old"):
                continue
            n_, a0_ = float(dd_["ratio_new"]), float(dd_["ratio_old"])
            k_ = (n_ + a0_) / a0_ if x["category"] == "bonus_issue" else n_ / a0_
            e0_ = dt.date.fromisoformat(x["event_at"][:10])
            if abs(k_ - 1) > 1e-9 and not any(abs((dt.date(e1 // 10000, e1 // 100 % 100, e1 % 100) - e0_).days) <= 30 for e1, _ in SPL.get(x["ticker"], [])):
                ost_nl.append(f'{x["ticker"]} {x["event_at"][:10]} x{k_:.6g} ({x.get("category_label") or x["category"]})')
        except Exception:  # noqa: BLE001
            continue
    if ost_nl:
        boc_chk["ost_non_listees"] = ost_nl
        log("opérations sur le capital de la base absentes de la liste :", "; ".join(ost_nl))
        print(f"::warning::Construction : {len(ost_nl)} opération(s) sur le capital de la base sans date d'effet vérifiée, non appliquée(s) : {', '.join(ost_nl[:5])}")
    rep = json.load(open(os.path.join(src, "indices", "indices_report.json"), encoding="utf8"))
    imap = {"BRVM-C": "BRVMC", "BRVM-30": "BRVM30", "BRVM-PRES": "BRVMPR", "BRVM-PRIN": "BRVMPA", "TL": "BRVM-TEL", "CD": "BRVM-CD",
            "SF": "BRVM-SF", "CB": "BRVM-CB", "IN": "BRVM-IN", "EN": "BRVM-EN", "SP": "BRVM-SP"}
    sess_idx = {imap[x["k"]]: x for x in (session or {}).get("idx", []) + (session or {}).get("sect", []) if x.get("k") in imap}
    # jours où le BRVM Composite de la base est figé sur la veille alors que le marché a bougé : relevé de la base périmé ce jour-là,
    # pour tous ses indices (un indice sectoriel de quelques titres peut, lui, être réellement inchangé un autre jour)
    IDX_STALE = set()
    try:
        rc_ = load_brvm_csv(os.path.join(src, "indices", "Indice_BRVMC.csv"))
        IDX_STALE = {r[0] for j_, r in enumerate(rc_) if j_ and r[4] == rc_[j_ - 1][4] and BOC_DAYS.get(r[0], 0) >= 10}
    except Exception as e:  # noqa: BLE001
        log("contrôle des indices impossible :", e)
    for e in rep["entries"]:
        p = os.path.join(src, "indices", e["fichier"])
        if not os.path.exists(p):
            continue
        rows = load_brvm_csv(p)
        code = e["code"]
        # valeurs de la base contrôlées par les bulletins officiels : séance fantôme (week-end, jour férié recopiant la veille)
        # retirée ; valeur figée sur la veille un jour où le marché a bougé (relevé de la base fait avant la publication) remplacée par
        # la valeur du bulletin si elle est lue, sinon retirée (un jour manquant plutôt qu'une valeur fausse) ; valeur différente de
        # celle du bulletin corrigée ; séances du bulletin absentes de la base ajoutées
        OB_ = BOC_IDX.get(code) or {}
        OBV_ = BOC_IDXV.get(code) or {}
        i2d_ = lambda x: dt.date(x // 10000, x // 100 % 100, x % 100)  # noqa: E731
        broad_ = code in ("BRVMC", "BRVM30", "BRVMPR", "BRVMPA", "BRVM10")  # (au moins 12 sociétés : figé un jour où 10 titres ont bougé = relevé périmé)
        out_, n_drop, n_fix, drop_d, doute_ = [], 0, 0, [], []
        for j_, r in enumerate(rows):
            d_ = r[0]
            same_ = j_ and r[4] == rows[j_ - 1][4]
            if d_ in OB_:
                # (écart de plus de 5 % un même jour : base ou lecture du bulletin douteuse, valeur de la base gardée et signalée)
                if abs(OB_[d_] - r[4]) > .0051 and r[4] and abs(OB_[d_] / r[4] - 1) >= .05:
                    doute_.append(d_)
                elif abs(OB_[d_] - r[4]) > .0051:
                    r = (d_, OB_[d_], OB_[d_], OB_[d_], OB_[d_]) + tuple(r[5:])
                    n_fix += 1
            elif is_weekend(d_) or (same_ and no_session(d_)):
                n_drop += 1
                drop_d.append(d_)
                continue
            elif same_ and BOC_DAYS.get(d_, 0) >= 10 and (broad_ or d_ in IDX_STALE):
                n_drop += 1
                drop_d.append(d_)
                continue
            out_.append(r)
        last_b = out_[-1][0] if out_ else 0
        for d_ in sorted(OB_):
            if d_ > last_b and (not sess_d or d_ < sess_d):
                if out_ and out_[-1][4] and abs(OB_[d_] / out_[-1][4] - 1) >= .1 and (i2d_(d_) - i2d_(out_[-1][0])).days <= 7:
                    doute_.append(d_)  # (saut de plus de 10 % d'une séance à la suivante : lecture du bulletin douteuse, séance laissée manquante)
                    continue
                out_.append((d_, OB_[d_], OB_[d_], OB_[d_], OB_[d_], 0, 0))
                n_fix += 1
        # montants échangés : ceux du bulletin officiel quand il les imprime (tableau des indices ; total du marché des actions pour
        # le BRVM Composite)
        n_val = 0
        for j_, r in enumerate(out_):
            vb_ = OBV_.get(r[0])
            if vb_ and (len(r) < 7 or r[6] != vb_):
                out_[j_] = tuple(r[:5]) + ((r[5] if len(r) > 5 else 0), vb_)
                n_val += 1
        if n_drop or n_fix or n_val or doute_:
            boc_chk.setdefault("idx", {})[code] = {"retirees": n_drop, "officielles": n_fix, "montants": n_val, **({"doute": doute_[-20:]} if doute_ else {})}
        if drop_d:
            boc_chk.setdefault("idx_drop", {})[code] = drop_d  # (séances retirées : la base historique les retire aussi)
        rows = out_
        if code in sess_idx and sess_d and rows and sess_d >= rows[-1][0]:
            v = sess_idx[code]["v"]
            # (montant du jour : celui de la base ou du bulletin pour cette séance, sinon inconnu (0) ; jamais celui de la veille)
            vl_ = rows[-1][6] if rows[-1][0] == sess_d else (OBV_.get(sess_d) or 0)
            rows = [r for r in rows if r[0] != sess_d] + [(sess_d, v, v, v, v, 0, vl_)]
        if len(rows) < 30:
            continue
        add({"id": code, "tk": f"{code} Index", "n": e["nom"], "cls": "Index", "typ": "Index", "mkt": "BRVM", "grp": "Indice " + e.get("type", ""), "ccy": "XOF", "bench": "BRVMC"},
            [r[0] for r in rows], [r[4] for r in rows], nd=2, val=[r[6] for r in rows])

    # Macro -----------------------------------------------------------------
    def macro(sid, tk, name, grp, path, dcol, vcol, freq, nd=2, filt=None, ccy="USD", cls="Comdty", more=None):
        try:
            s = series_from_csv(fetch(DS.format(path), a.cache).decode("utf8"), dcol, vcol, filt)
        except Exception as e:  # noqa: BLE001
            log("skip", sid, e)
            return []
        if more and s:  # mois plus récents tirés de FRED (même définition, raccord contrôlé)
            try:
                s = more(s)
            except Exception as e:  # noqa: BLE001
                log(sid, ": prolongement FRED impossible :", e)
        add({"id": sid, "tk": tk, "n": name, "cls": cls, "typ": cls, "mkt": "MACRO", "grp": grp, "ccy": ccy}, [x[0] for x in s], [x[1] for x in s], freq=freq, nd=nd)
        return s
    macro("XAU", "XAU Curncy", "Or (USD/once, mensuel)", "Métaux", "gold-prices/main/data/monthly.csv", "Date", "Price", "M")
    macro("SPXM", "SPX Index (mensuel)", "S&P 500 depuis 1871 (mensuel)", "Actions", "s-and-p-500/main/data/data.csv", "Date", "SP500", "M", cls="Index")
    macro("CAPE", "CAPE Index", "S&P 500 PER de Shiller (CAPE)", "Valorisation", "s-and-p-500/main/data/data.csv", "Date", "PE10", "M", cls="Index")
    # CPI et taux à 10 ans : les jeux github.com/datasets suivent avec un ou deux mois de retard ; les mois suivants sont pris dans
    # FRED (CPIAUCNS, même indice CPI-U non désaisonnalisé depuis 1913 ; moyenne mensuelle des taux quotidiens DGS10, même définition
    # que la série mensuelle) quand les deux sources concordent sur les mois communs, sinon la série reste telle quelle
    macro("CPI", "CPI INDX", "Indice des prix US (CPI-U)", "Inflation", "cpi-us/main/data/cpiai.csv", "Date", "Index", "M", cls="Index",
          more=lambda s: fred_extend(s, fred_csv(a.extra, "CPIAUCNS"), rel=.0005))
    macro("US10Y", "USGG10YR Index", "Taux US 10 ans (%)", "Taux", "bond-yields-us-10y/main/data/monthly.csv", "Date", "Rate", "M", cls="Rate", ccy="%",
          more=lambda s: fred_extend(s, monthly_avg(fred_csv(a.extra, "DGS10")), absol=.05))
    # prix au comptant publiés par l'EIA (J-1) : Brent daté (physique), WTI Cushing, gaz Henry Hub. Les contrats à terme
    # (CO1, CL1, NG1 : ceux d'Investing, TradingView, Bloomberg) sont ajoutés par build_extra.ingest sous BRENT, WTI, NATGAS.
    import build_extra
    fut_dir = os.path.join(a.extra, "futures") if a.extra else None
    for sid, sid_f, tk, name, path, nd_ in (("BRENTS", "BRENT", "EUCRBRDT Index", "Brent daté, prix au comptant (USD/baril)", "oil-prices/main/data/brent-daily.csv", 2),
                                            ("WTIS", "WTI", "USCRWTIC Index", "WTI Cushing, prix au comptant (USD/baril)", "oil-prices/main/data/wti-daily.csv", 2),
                                            ("NGS", "NATGAS", "NGUSHHUB Index", "Gaz Henry Hub, prix au comptant (USD/MMBtu)", "natural-gas/main/data/daily.csv", 3)):
        sp = macro(sid, tk, name, "Énergie", path, "Date", "Price", "D", nd=nd_)
        if sp and not (fut_dir and build_extra.futures_ok(os.path.join(fut_dir, sid_f + ".json"))):
            QUOTES.pop(sid_f, None)  # cours du contrat à terme : jamais greffé sur la série au comptant (ni ici, ni dans la page)
            if a.quotes and os.path.exists(a.quotes):
                qj = json.load(open(a.quotes, encoding="utf8"))
                if (qj.get("q") or {}).pop(sid_f, None) is not None:
                    json.dump(qj, open(a.quotes, "w", encoding="utf8"), separators=(",", ":"), ensure_ascii=False)
            macro(sid_f, tk, name, "Énergie", path, "Date", "Price", "D", nd=nd_)
    macro("VIX", "VIX Index", "Volatilité implicite S&P 500", "Volatilité", "finance-vix/main/data/vix-daily.csv", "DATE", "CLOSE", "D", cls="Index", ccy="pts")
    try:
        fx = fetch(DS.format("exchange-rates/main/data/daily.csv"), a.cache).decode("utf8")
        eur = series_from_csv(fx, "Date", "Exchange rate", lambda r: r.get("Country") == "Euro")
        twd = series_from_csv(fx, "Date", "Exchange rate", lambda r: r.get("Country") == "Taiwan")
        add({"id": "EURUSD", "tk": "EURUSD Curncy", "n": "Euro / Dollar US", "cls": "Curncy", "typ": "Curncy", "mkt": "MACRO", "grp": "Change", "ccy": "USD"},
            [x[0] for x in eur], [1 / x[1] for x in eur], nd=5)
        add({"id": "USDXOF", "tk": "USDXOF Curncy", "n": "Dollar US / Franc CFA (BCEAO)", "cls": "Curncy", "typ": "Curncy", "mkt": "MACRO", "grp": "Change", "ccy": "XOF"},
            [x[0] for x in eur], [x[1] * XOF_PER_EUR for x in eur], nd=3)
        add({"id": "USDTWD", "tk": "USDTWD Curncy", "n": "Dollar US / Dollar taïwanais", "cls": "Curncy", "typ": "Curncy", "mkt": "MACRO", "grp": "Change", "ccy": "TWD"},
            [x[0] for x in twd], [x[1] for x in twd], nd=4)
    except Exception as e:  # noqa: BLE001
        log("skip FX", e)

    # Sources complémentaires : ETF, indices US, Nasdaq-100, CBOE, crypto ----------
    import build_extra
    xinfo = build_extra.ingest(a.extra, add, set(files), log)
    # dividendes US (Nasdaq) ajoutés aux séries à la date de détachement : rendement total, backtests et DVD
    try:
        usd_p = os.path.join(a.extra, "us_divs.json") if a.extra else None
        USDIV = (json.load(open(usd_p, encoding="utf8")).get("s") or {}) if usd_p and os.path.exists(usd_p) else {}
        spl_p = os.path.join(a.extra, "us_splits.json") if a.extra else None
        USSPL = (json.load(open(spl_p, encoding="utf8")).get("s") or {}) if spl_p and os.path.exists(spl_p) else {}
        n_usd = n_ser = 0
        for sid, rows in USDIV.items():
            b = files.get(sid)
            if not b or not rows:
                continue
            if any(b.get("div") or []):
                continue  # série qui porte déjà ses dividendes (Yahoo)
            spl = [(x[0], x[1]) for x in USSPL.get(sid, []) if x[1] and x[1] > 0]
            div, n_ = us_div_place(b["d"], rows, spl)
            # scission (seed/scissions_us.json) : dividendes antérieurs ajustés comme les cours
            for k_, f_ in (xinfo.get("scissions") or {}).get(sid, []):
                div = [x * f_ if d_ < k_ and x else x for d_, x in zip(b["d"], div)]
            n_usd += n_
            b["div"] = div
            n_ser += 1
        log("dividendes US :", n_usd, "versements placés dans", n_ser, "séries (écrits à la base du soir)")
    except Exception as e:  # noqa: BLE001
        log("dividendes US illisibles :", e)
    # rendement des titres US et Taïwan = dividendes détachés sur les 12 derniers mois calendaires (série, après placement) ÷ dernier
    # cours, arrondi comme pour la BRVM ; seulement si la série couvre au moins un an et porte au moins un dividende sur ces 12 mois,
    # sinon vide (jamais 0 inventé : une série sans dividende peut venir d'une source qui ne les donne pas)
    try:
        n_y = 0
        for s in secs:
            if s["mkt"] not in ("US", "TW") or s.get("f") != "D":
                continue
            b = files.get(s["id"]) or {}
            s["yld"] = trailing_yield(b.get("d"), b.get("div"), s.get("last"))
            n_y += s["yld"] is not None
        log("rendements US et Taïwan :", n_y, "titres")
    except Exception as e:  # noqa: BLE001
        log("rendements US impossibles :", e)
    # séance manquante dans une série US ou Taïwan (UBER sans le 16/10/2026 dans la source) : la variation du jour du résumé portait
    # sur deux séances (−1,45 % au lieu de −0,16 %). Quand la cotation du jour donne sa clôture précédente et que la série n'a pas
    # la séance précédente du calendrier du marché (SPY, 0050), le résumé prend cette clôture précédente ; la série n'est pas
    # complétée (aucune bougie inventée) et le trou est signalé chaque matin (contrôle B41)
    try:
        cal_ = {"US": set((files.get("SPY") or {}).get("d") or []), "TW": set((files.get("0050") or {}).get("d") or [])}
        gaps_ = []
        for s in secs:
            if s["mkt"] not in ("US", "TW") or s.get("f") != "D":
                continue
            q_, d_ = QUOTES.get(s["id"]) or {}, (files.get(s["id"]) or {}).get("d") or []
            if not q_.get("prev") or not q_.get("d") or len(d_) < 2 or di(q_["d"]) != d_[-1] or not s.get("last"):
                continue
            miss_ = sorted(x for x in cal_[s["mkt"]] if d_[-2] < x < d_[-1])
            if miss_ and q_["prev"] > 0:
                s["prev"], s["pct"] = q_["prev"], rnd(s["last"] / q_["prev"] - 1, 6)
                gaps_.append(f"{s['id']} {','.join(map(str, miss_))}")
        if gaps_:
            log("séances manquantes dans les séries (variation du jour sur la clôture précédente de la cotation) :", "; ".join(gaps_))
    except Exception as e:  # noqa: BLE001
        log("contrôle des séances manquantes impossible :", e)

    for s in secs:  # métadonnées Nasdaq des titres US déjà suivis
        if s["mkt"] == "US" and s["id"] in xinfo["ndx"]:
            s["ndx"] = True
        sc = xinfo["screener"].get(s["id"]) if s["mkt"] == "US" else None
        if sc:
            s["mcap"] = s.get("mcap") or sc.get("mcap")
            s["sector"] = build_extra.SECT_FR.get(sc.get("sector"), sc.get("sector"))
            s["ind"] = sc.get("ind")

    # Betas / correlations on weekly returns (2 years) ----------------------
    wk = {sid: weekly(b["d"], b["c"]) for sid, b in files.items() if b["f"] == "D"}
    for s in secs:
        bm = s.get("bench")
        if s["f"] != "D" or not bm or bm == s["id"] or bm not in wk:
            continue
        a_, b_ = wk[s["id"]], wk[bm]
        keys = sorted(set(a_) & set(b_))[-105:]
        x = [math.log(a_[keys[i]] / a_[keys[i - 1]]) for i in range(1, len(keys))]
        y = [math.log(b_[keys[i]] / b_[keys[i - 1]]) for i in range(1, len(keys))]
        s["beta"], s["corr"] = (rnd(v, 3) for v in beta_corr(x, y))
    # weekly matrix (10 years) for CORR / PCA
    allw = sorted({k for v in wk.values() for k in v})
    allw = [k for k in allw if k >= allw[-1] - 100000][-530:]
    wm = {"w": allw, "s": {}}
    for sid, ser in wk.items():
        last = None
        col = []
        for k in allw:
            if k in ser:
                last = ser[k]
            col.append(rnd(last, 4) if last is not None else None)
        if sum(1 for v in col if v is not None) > 52:
            wm["s"][sid] = col
    # semaine en cours datée de la dernière séance relevée, jamais d'un vendredi à venir (étiquette seulement)
    dmax = max((b["d"][-1] for b in files.values() if b["f"] == "D" and b["d"]), default=0)
    if allw and dmax and allw[-1] > dmax:
        allw[-1] = dmax

    # BRVM breadth (since 2008) -------------------------------------------
    stocks = [s["id"] for s in secs if s["mkt"] == "BRVM" and s["cls"] == "Equity"]
    days = sorted({d for sid in stocks for d in files[sid]["d"] if d >= 20080101})
    above200, above50, adv, dec, nh, nl = ({} for _ in range(6))
    for sid in stocks:
        b = files[sid]
        d, c = b["d"], b["c"]
        s50 = s200 = 0.0
        for i in range(len(c)):
            s50 += c[i]
            s200 += c[i]
            if i >= 50:
                s50 -= c[i - 50]
            if i >= 200:
                s200 -= c[i - 200]
            if d[i] < 20080101 or i < 1:
                continue
            day = d[i]
            if i >= 199:
                above200.setdefault(day, [0, 0])
                above200[day][1] += 1
                above200[day][0] += c[i] > s200 / 200
            if i >= 49:
                above50.setdefault(day, [0, 0])
                above50[day][1] += 1
                above50[day][0] += c[i] > s50 / 50
            if c[i] > c[i - 1]:
                adv[day] = adv.get(day, 0) + 1
            elif c[i] < c[i - 1]:
                dec[day] = dec.get(day, 0) + 1
            if i >= 251:
                w = c[i - 251:i]
                if c[i] > max(w):
                    nh[day] = nh.get(day, 0) + 1
                elif c[i] < min(w):
                    nl[day] = nl.get(day, 0) + 1
    adl, run = [], 0
    for day in days:
        run += adv.get(day, 0) - dec.get(day, 0)
        adl.append(run)
    breadth = {"d": days, "a200": [rnd(above200[x][0] / above200[x][1], 4) if x in above200 and above200[x][1] >= 10 else None for x in days],
               "a50": [rnd(above50[x][0] / above50[x][1], 4) if x in above50 and above50[x][1] >= 10 else None for x in days],
               "adv": [adv.get(x, 0) for x in days], "dec": [dec.get(x, 0) for x in days], "adl": adl,
               "nh": [nh.get(x, 0) for x in days], "nl": [nl.get(x, 0) for x in days]}

    # BRVM meta: fundamentals, dividends, notices ---------------------------
    keep = ["ca", "resultat_net", "bnpa", "dividende", "per", "capitaux_propres", "roe", "roa", "marge_nette", "marge_exploitation",
            "croissance_ca", "croissance_resultat_net", "total_bilan", "depots_clientele", "credits_clientele", "coefficient_d_exploitation",
            "cout_du_risque", "ratio_endettement_net", "dette_nette", "tresorerie", "ebitda", "ebit"]
    # secteur de la base tierce démenti par la liste des actions (« Banque » pour une société qui n'est pas une banque : SMB CI,
    # société pétrolière) : celui de la liste des actions est retenu
    act_sec = {(x.get("symbole") or x.get("ticker")): (x.get("secteur"), bool(x.get("banque"))) for x in acts}
    for k, v in fund.items():
        if k != "_meta" and isinstance(v, dict) and v.get("secteur") == "Banque" and k in act_sec and not act_sec[k][1] and act_sec[k][0]:
            v["secteur"] = act_sec[k][0]
    fmeta = {k: {"nom": v.get("nom"), "secteur": v.get("secteur"), "shares": v.get("nb_titres"), "float": v.get("flottant"), "ex": v.get("exercice"),
                 "series": {s: v["series"][s] for s in keep if v.get("series", {}).get(s)}}
             for k, v in fund.items() if k != "_meta"}
    # dividende d'un exercice publié dans fundamentals.json (et repris par l'export historique) : la somme de ses versements
    # ordinaires officiels, comme dans FA (audit du 20/10/2026, constat I-3 : la base donnait parfois le versement de l'exercice
    # précédent, l'exceptionnel en plus ou le brut) ; le montant de la base ne reste que pour un exercice sans versement officiel
    # recensé (aucun exercice n'est ajouté ici)
    try:
        dps_off_ = collections.defaultdict(dict)
        for x in divs:
            if x.get("ticker") and x.get("exercice") and x.get("dividende") and not x.get("exc"):
                try:
                    y_ = str(int(x["exercice"]))
                except (TypeError, ValueError):
                    continue  # (exercice illisible : versement ignoré ici, comme dans FA)
                dps_off_[x["ticker"]][y_] = dps_off_[x["ticker"]].get(y_, 0) + x["dividende"]
        div_fix_ = []
        for k, m_ in fmeta.items():
            o_ = (m_.get("series") or {}).get("dividende")
            if not isinstance(o_, dict):
                continue
            n_o = dict(o_)  # (copie : la série de la fiche elle-même n'est pas modifiée)
            for y_, x_ in o_.items():
                n_ = dps_off_.get(k, {}).get(str(y_))
                if n_ and isinstance(x_, (int, float)) and abs(x_ - n_) > max(.01, abs(n_) * .005):
                    n_o[y_] = round(n_, 4)
                    div_fix_.append(f"{k} {y_} {x_:g} -> {n_:g}")
            m_["series"]["dividende"] = n_o
        if div_fix_:
            log(f"dividendes de la fiche remplacés par les versements officiels de l'exercice ({len(div_fix_)}) :", "; ".join(div_fix_))
    except Exception as e:  # noqa: BLE001
        log("dividendes de la fiche : contrôle impossible", e)
    def brut_(x):  # dividende brut et taux de l'impôt de l'avis, cohérents avec le net publié (sinon rien)
        b_, r_, n_ = x.get("brut_avis"), x.get("irvm_avis"), x.get("dividende")
        if not b_ or r_ is None or not n_ or not 0 <= r_ < 50:
            return {}
        b_ = b_ / (x.get("ajust") or 1.0)
        return {"brut": round(b_, 4), "irvm": r_} if abs(b_ * (1 - r_ / 100) - n_) <= max(.6, n_ * .002) else {}
    dmeta = [{"t": x.get("ticker"), "ex": x.get("exercice"), "dps": x.get("dividende"), "ann": x.get("date_annonce"), "det": x.get("date_detachement"),
              "pay": x.get("date_paiement"), "src": x.get("source"), **({"dps0": x["dividende_publie"], "adj": x["ajust"]} if x.get("ajust") else {}),
              **({"cal": 1} if x.get("cal") else {}), **({"usd": x["usd_c"], **({"fx": x["fx"]} if x.get("fx") else {"fxb": 1})} if x.get("usd_c") else {}), **({"exc": 1} if x.get("exc") else {}), **brut_(x),
              **({"corr": x["corr"]} if x.get("corr") else {}), "_do": bool(x.get("det_off")), "_po": bool(x.get("pay_off"))} for x in divs if x.get("ticker")]
    # jour de séance : pas un week-end, et — les mois couverts par les bulletins officiels (au moins 10 bulletins) — un jour de bulletin
    # ou de cours de la base qui varie (hors jour férié) ; avant les bulletins, le seul critère du week-end
    boc_m_ = collections.Counter(d_ // 100 for d_ in BOC_DAYS)

    def seance_(s):
        try:
            d_ = di(str(s)[:10])
            return not is_weekend(d_) and (boc_m_[d_ // 100] < 10 or not no_session(d_))
        except (TypeError, ValueError, IndexError):
            return True  # (date illisible : laissée, d'autres contrôles la signalent)
    # date de détachement qu'aucun document officiel ne donne (reprise de la base tierce) : retirée (le dividende est alors placé à
    # sa date de paiement) si elle ne tombe pas un jour de séance ou précède le paiement de plus de 15 jours (dimanche 01/05/2016,
    # 65 jours avant le paiement : PRSC et SGBC 2015) ; ancienne valeur gardée dans « det0 »
    det_rm, pay_keep = [], []
    for x in dmeta:
        if x.get("det") and not x["_do"]:
            try:
                gap_ = (dt.date.fromisoformat(x["pay"][:10]) - dt.date.fromisoformat(x["det"][:10])).days if x.get("pay") else 0
            except ValueError:
                gap_ = 0
            if not seance_(x["det"]) or gap_ > 15:
                det_rm.append(f'{x["t"]} {x["ex"]} {x["det"]}')
                x["det0"], x["det"] = x["det"], None
    # dates incohérentes entre elles : une annonce postérieure au détachement ou au paiement (date de mise en ligne d'un ancien avis)
    # et un paiement antérieur au détachement (date mal lue) sont retirés plutôt qu'affichés faux ; une date de paiement écrite dans
    # le document officiel n'est jamais retirée : avec un détachement officiel postérieur (cotation suspendue jusqu'au détachement,
    # SLBC 2023 : paiement le 14/08/2024, reprise ex-dividende le 12/09/2024) les deux sont gardées et signalées ; avec un
    # détachement de la base, c'est lui qui est retiré
    for x in dmeta:
        if x.get("ann") and ((x.get("det") and x["ann"] > x["det"]) or (x.get("pay") and x["ann"] > x["pay"])):
            x["ann"] = None
        if x.get("det") and x.get("pay") and x["pay"] < x["det"]:
            if x["_po"] and x["_do"]:
                pay_keep.append(f'{x["t"]} {x["ex"]} (paiement {x["pay"]}, détachement {x["det"]})')
            elif x["_po"]:
                det_rm.append(f'{x["t"]} {x["ex"]} {x["det"]}')
                x["det0"], x["det"] = x["det"], None
            else:
                x["pay"] = None
    DOFF = {}  # (dates écrites dans un document officiel, par versement : alignement des événements plus bas)
    for x in dmeta:
        DOFF[id(x)] = {"det": x.pop("_do", False), "pay": x.pop("_po", False)}
    if det_rm:
        log("dates de détachement de la base retirées (pas un jour de séance, plus de 15 jours avant le paiement, ou après le paiement officiel) :",
            "; ".join(det_rm))
    if pay_keep:
        log("paiement officiel antérieur au détachement officiel, gardé :", "; ".join(pay_keep))
    if split_log:
        log("fractionnements :", "; ".join(split_log[:80]))
    if bnpa_notes:
        log("BNPA du bulletin différent de la série (mention de l'exercice dans FA) :", ", ".join(bnpa_notes))
    ev = json.load(open(os.path.join(src, "events.json"), encoding="utf8"))["events"]
    emeta = [{"d": x.get("published_at") or x.get("event_at"), "e": x.get("event_at"), "t": x.get("ticker"), "c": "Modification du dividende" if x.get("category") == "dividend_amount_change" else x.get("category_label"),
              "ti": x.get("title"), "u": x.get("document_url")} for x in ev if (x.get("published_at") or x.get("event_at"))]
    # même événement présent deux fois dans la base (même société, même date, même nature, même intitulé) : une seule ligne ; si les
    # deux lignes ne donnent pas la même date d'événement, la plus tardive est gardée (une assemblée se tient après sa convocation :
    # la date antérieure est celle du document, pas celle de la réunion)
    by_ev = {}
    for x in emeta:
        k_ = (x["t"], x["d"], x["c"], x["ti"])
        if k_ not in by_ev or (x.get("e") or "") > (by_ev[k_].get("e") or ""):
            by_ev[k_] = x
    emeta = list(by_ev.values())
    try:
        avd = {}
        for r in AV:
            if r.get("k") == "div" and r.get("t"):
                for k_ in (r.get("det"), r.get("pay"), r.get("d")):
                    if k_:
                        avd[(r["t"], k_)] = r["u"]
        for x in emeta:
            if x.get("u") and "brvm.org" not in x["u"] and x.get("t"):
                x["u"] = avd.get((x["t"], x.get("e"))) or avd.get((x["t"], x.get("d"))) or x["u"]
    except Exception as e:  # noqa: BLE001
        log("liens d'avis :", e)
    known_u = {x["u"] for x in emeta if x.get("u")}
    known_k = {(x.get("t"), x.get("c"), x.get("d")) for x in emeta if x.get("t")}
    known_e = {(x.get("t"), x.get("e")) for x in emeta if x.get("t") and x.get("c") in ("Annonce dividende", "Paiement dividende", "Détachement dividende")}

    def dup(r):  # même document, ou même avis déjà repris par la base sous une autre adresse
        if r["u"] in known_u:
            return True
        try:
            d0 = dt.date.fromisoformat(r["d"][:10])
        except (TypeError, ValueError):
            return False
        if r.get("t") and any((r["t"], r.get("c"), (d0 + dt.timedelta(days=k)).isoformat()) in known_k for k in range(-3, 4)):
            return True
        if r.get("k") in ("frac", "capital") and r.get("t"):  # opérations déjà connues sous un autre avis (date d'effet à ±15 jours)
            try:
                e0 = dt.date.fromisoformat((r.get("e") or r["d"])[:10])
                if any(x.get("t") == r["t"] and x.get("c") == r.get("c") and x.get("e") and abs((dt.date.fromisoformat(x["e"][:10]) - e0).days) <= 15 for x in emeta):
                    return True
            except ValueError:
                pass
        return r.get("k") == "div" and r.get("t") and ((r["t"], r.get("det")) in known_e or (r["t"], r.get("pay")) in known_e)
    AV_BOND = re.compile(r"%|\betat\b|emprunt|obligat|fctc|\btp[a-z]{2}\b|diaspora|souscription|sukuk|\bo\d{2,3}\b")
    for r in AV:  # avis brvm.org pas encore dans la base : ajoutés tels que publiés (date de publication ; date de l'AG quand elle a été lue dans la convocation)
        try:
            # même périmètre que la base : actions cotées, et avis de marché généraux (pas les obligations ni les États)
            if not r.get("d") or (not r.get("t") and (r.get("k") != "marche" or AV_BOND.search(_nm(r.get("ti"))))) or dup(r):
                continue
        except Exception:  # noqa: BLE001
            continue
        emeta.append({"d": r["d"], "e": r.get("e") or r["d"], "t": r.get("t"), "c": r.get("c"), "ti": r.get("ti"), "u": r["u"]})
        av_chk["ev"] += 1
        if r.get("k") == "ag" and r.get("ag"):
            emeta.append({"d": r["d"], "e": r["ag"], "t": r.get("t"), "c": "Assemblée générale", "ti": r.get("ti"), "u": r["u"]})
            av_chk["ag"] += 1
    if AV:
        log("avis brvm.org ajoutés :", av_chk)
    emeta.sort(key=lambda x: (x["d"] or "", x.get("u") or ""), reverse=True)
    # même événement repris deux fois (avis publié une seconde fois sous un autre fichier — « …_1.pdf », nom légèrement différent —,
    # ou déjà présent dans la base sous une autre rubrique) : même titre, même société, mêmes dates ; gardé une fois, avec la rubrique
    # la plus précise (« Avis de la BRVM » est la rubrique générale)
    best_ev = {}
    for x in emeta:
        k_ = (x["t"], x["d"], x.get("e"), _nm(x["ti"]))
        if k_ not in best_ev or (best_ev[k_].get("c") in ("Avis de la BRVM", None) and x.get("c") not in ("Avis de la BRVM", None)):
            best_ev[k_] = x
    keep_ = {id(x) for x in best_ev.values()}
    emeta = [x for x in emeta if id(x) in keep_]
    # document déposé sous la page d'une autre société (liste de la Bourse) : l'intitulé, puis le nom du fichier, désignent la
    # bonne société (comptes.doc_company, comme la recherche MOTS CLES et la lecture des comptes) ; rien n'est retiré
    try:
        import comptes as _CPT
        n_mv, ids_brvm = 0, {s_["id"] for s_ in secs if s_.get("mkt") == "BRVM"}
        for x in emeta:
            if x.get("t") in _CPT.NAME_TOKENS:
                t2 = _CPT.doc_company(x["t"], x.get("ti") or "", (x.get("u") or "").rsplit("/", 1)[-1])
                if t2 != x["t"] and t2 in ids_brvm:
                    x["t"] = t2
                    n_mv += 1
        log(f"événements rattachés à la société nommée dans l'intitulé ou le fichier : {n_mv}")
    except Exception as e:  # noqa: BLE001
        log("rattachement des événements : non fait", e)
    # quasi-doublons : même société, même intitulé (mention « annule et remplace » retirée), même rubrique, publiés à 5 jours près
    # (document republié sous un autre nom de fichier, calendrier de paiement des dividendes remis à jour d'un jour à l'autre,
    # convocation « annule et remplace ») : le plus récent est gardé. Deux assemblées de dates différentes restent deux événements,
    # sauf si la plus récente annule et remplace l'autre ; les avis « Transactions sur dossier » et les annulations de transaction
    # sont tous distincts
    # (la base donne souvent le même intitulé générique à deux documents différents — deux nominations, une convocation et des projets
    # de résolutions — : les noms de fichiers, date de tête, numéro de copie « _2 » et mention « annule et remplace » retirés, doivent
    # aussi se ressembler — la moitié des mots en commun, sans les petits mots ni l'apostrophe codée « 27 » (« l27ago »), « 03 » = « 3 »
    # —, sinon les deux événements restent)
    try:
        import urllib.parse as _up
        AR_ = re.compile(r"\bannule (?:et )?remplace(?: le precedent)?(?: publie)?\b")
        MV_ = {"de", "du", "des", "la", "le", "les", "et", "a", "au", "aux", "l", "d", "en"}

        def fmots_(u_):
            b_ = _up.unquote((u_ or "").rsplit("/", 1)[-1]).lower()
            b_ = re.sub(r"\.pdf$", "", b_)
            b_ = re.sub(r"^\d{8}\s*[-_]*", "", b_)
            b_ = re.sub(r"(?<=[a-z])27(?=[a-z])", " ", b_)
            return {w.lstrip("0") or "0" for w in AR_.sub(" ", _nm(b_)).split() if w not in MV_}

        def meme_doc_(a_, b_):
            ma_, mb_ = fmots_(a_.get("u")), fmots_(b_.get("u"))
            return not ma_ or not mb_ or len(ma_ & mb_) >= .5 * len(ma_ | mb_)
        kept_, out_, nd_rm = collections.defaultdict(list), [], []
        for x in emeta:  # (du plus récent au plus ancien)
            n_ti = _nm(x.get("ti"))
            if re.search(r"transactions? sur dossier|annulation de transaction", n_ti) or x.get("c") == "Transaction annulée par la BRVM":
                out_.append(x)
                continue
            try:
                d0_ = dt.date.fromisoformat((x.get("d") or "")[:10])
            except ValueError:
                out_.append(x)
                continue
            k_ = (x.get("t"), re.sub(r"\s+", " ", AR_.sub(" ", n_ti)).strip(), x.get("c"))
            hit_ = None
            for y_, dy_ in kept_[k_]:
                if abs((dy_ - d0_).days) > 5:
                    continue
                if x.get("e") and y_.get("e") and x["e"] != x.get("d") and y_["e"] != y_.get("d") and x["e"] != y_["e"] \
                        and not AR_.search(_nm((y_.get("ti") or "") + " " + (y_.get("u") or ""))):
                    continue  # (deux réunions à des dates différentes, sans « annule et remplace »)
                if not meme_doc_(x, y_):
                    continue  # (deux documents différents sous le même intitulé de la base)
                hit_ = y_
                break
            if hit_ is not None:
                nd_rm.append(f'{x.get("t") or "marché"} {x.get("d")} « {(x.get("ti") or "")[:60]} » (gardé : {hit_.get("d")})')
                continue
            kept_[k_].append((x, d0_))
            out_.append(x)
        if nd_rm:
            emeta = out_
            log(f"événements en double retirés (même société, même intitulé, 5 jours près) : {len(nd_rm)} ;", "; ".join(nd_rm[:60]))
    except Exception as e:  # noqa: BLE001
        log("quasi-doublons d'événements : non traités", e)
    # événements « Détachement » et « Paiement » d'un exercice : date d'effet alignée sur celle du versement du même titre et du même
    # exercice (dividends.json, documents officiels ; versement le plus proche, à 45 jours près) — la base d'avis décale parfois d'un
    # mois ou tombe un week-end ; ancienne date gardée dans « e0 ». Un détachement que le bulletin officiel confirme (cours de référence
    # abaissé du montant du dividende la séance d'avant) alors qu'il n'y confirme pas celui du versement est gardé et signalé
    try:
        byv_ = collections.defaultdict(list)
        for v_ in dmeta:
            if v_.get("t") and v_.get("ex"):
                byv_[(v_["t"], int(v_["ex"]))].append(v_)

        def ex_bulletin(t_, amt_, around):  # séances ex-dividende lues au bulletin (veille : référence abaissée du dividende)
            B_ = BOC.get(t_) or {}
            ks_ = sorted(B_)
            a0_ = dt.date.fromisoformat(around[:10])
            out2_ = set()
            for j_, k2_ in enumerate(ks_[:-1]):
                if abs((dt.date(k2_ // 10000, k2_ // 100 % 100, k2_ % 100) - a0_).days) > 15:
                    continue
                r_ = B_[k2_]
                c_, ref_ = r_.get("c") or r_.get("prev"), r_.get("ref")
                if c_ and ref_ and c_ > ref_ and abs((c_ - ref_) - amt_) <= max(5.5, amt_ * .06):
                    n2_ = ks_[j_ + 1]
                    out2_.add(f"{n2_ // 10000:04d}-{n2_ // 100 % 100:02d}-{n2_ % 100:02d}")
            return out2_
        ev_al, ev_kept, ev_rm, ev_nof = [], [], set(), []
        for x in emeta:
            if x.get("c") not in ("Détachement dividende", "Paiement dividende") or not x.get("t") or not x.get("e"):
                continue
            m_ = re.search(r"exercice\s*((?:19|20)\d\d)", x.get("ti") or "", re.I)
            if not m_:
                continue
            kd_ = "det" if x["c"].startswith("Dét") else "pay"
            try:
                e0_ = dt.date.fromisoformat(x["e"][:10])
                cands_ = [(abs((dt.date.fromisoformat(v_[kd_][:10]) - e0_).days), v_) for v_ in byv_.get((x["t"], int(m_.group(1))), []) if v_.get(kd_)]
            except ValueError:
                continue
            if not cands_:
                # (date ex-dividende de la base reconnue fausse plus haut — pas un jour de séance, ou bien plus de 15 jours avant le
                # paiement — et retirée du versement : l'événement qui ne porte que cette date est retiré aussi)
                if kd_ == "det" and any(v_.get("det0") == x["e"][:10] for v_ in byv_.get((x["t"], int(m_.group(1))), [])):
                    ev_rm.add(id(x))
                continue
            gap_, v_ = min(cands_, key=lambda c2_: c2_[0])
            if gap_ == 0 or gap_ > 45:
                continue
            if not (DOFF.get(id(v_)) or {}).get(kd_):
                ev_nof.append(f'{x["t"]} {m_.group(1)} {kd_} {x["e"][:10]} (versement : {v_[kd_][:10]}, date de la base)')
                continue  # (date du versement reprise de la base, sans document officiel : rien n'est aligné)
            if kd_ == "det":
                xs_ = ex_bulletin(x["t"], v_.get("dps0") or v_["dps"], v_["det"])
                if x["e"][:10] in xs_ and v_["det"][:10] not in xs_:
                    ev_kept.append(f'{x["t"]} {m_.group(1)} détachement {x["e"][:10]} (versement : {v_["det"][:10]})')
                    continue
            ev_al.append(f'{x["t"]} {m_.group(1)} {kd_} {x["e"][:10]} -> {v_[kd_][:10]}')
            x["e0"], x["e"] = x["e"], v_[kd_][:10]
        if ev_rm:
            log("événements « Date ex-dividende » retirés (date reconnue fausse, retirée du versement) :",
                "; ".join(f'{x["t"]} {x["e"]}' for x in emeta if id(x) in ev_rm))
            emeta = [x for x in emeta if id(x) not in ev_rm]
        if ev_al:
            log(f"événements de dividende alignés sur le versement officiel : {len(ev_al)} ;", "; ".join(ev_al))
        if ev_kept:
            log("détachements de la base confirmés par le bulletin, versement à revoir :", "; ".join(ev_kept))
            boc_chk["det_a_revoir"] = ev_kept
        if ev_nof:
            log("événements de dividende différents d'un versement sans date officielle, laissés :", "; ".join(ev_nof))
    except Exception as e:  # noqa: BLE001
        log("alignement des événements de dividende : non fait", e)

    # Calculs dérivés (macro, sentiment, liquidité, comptes, consensus, valorisation BRVM, UEMOA) ----
    # flux de trésorerie : uniquement ceux lus et vérifiés dans les états financiers publiés (pdf_cf). L'ancien fichier de départ
    # (--fcf, lecture sans contrôle d'identités : unités et lignes erronées sur 31 des 32 exercices recoupés) n'est plus utilisé.
    fcf_path = None
    if pdf_cf:
        import tempfile
        fcf_path = os.path.join(tempfile.gettempdir(), "fqt_fcf_verified.json")
        json.dump({"series": pdf_cf}, open(fcf_path, "w", encoding="utf8"))
    log("flux de trésorerie vérifiés :", sum(len(v) for v in pdf_cf.values()), "exercices,", len(pdf_cf), "sociétés")
    build_extra.derive(a.extra, out, files, secs, fund, fcf_path, dmeta, xinfo["ndx"], log)

    # write ------------------------------------------------------------------
    for sid, body in files.items():
        p_ = os.path.join(sdir, sid.replace(".", "_") + ".json")
        if a.live and os.path.exists(p_) and sid not in force_write:
            continue  # séance : la page applique elle-même les cours du jour (quotes.json) aux séries
        with open(p_, "w", encoding="utf8") as fh:
            json.dump(body, fh, separators=(",", ":"))
    asof = max(s["dt"] for s in secs if s["mkt"] in ("US", "BRVM"))
    summ = {"asof": asof, "built": int(time.time()), "secs": secs, "sectors": sorted({s["grp"] for s in secs if s["mkt"] == "BRVM" and s["cls"] == "Equity"}),
            "session": {"asof": session.get("asof"), "label": session.get("session"), "capA": session.get("capA")} if session else None, "cty": CTY_NAME}
    # notations financières (PDF de brvm.org lus le soir) : une ligne par document, dernière note par émetteur
    try:
        rp_ = os.path.join(a.extra, "ratings.json") if a.extra else None
        RT = (json.load(open(rp_, encoding="utf8")).get("docs") or {}) if rp_ and os.path.exists(rp_) else {}
        if RT:
            tick = {s_["id"] for s_ in secs if s_.get("mkt") == "BRVM"}
            ev_t = {x.get("u"): x.get("t") for x in emeta if x.get("u") and x.get("t") in tick}  # avis rattachés à une société cotée
            rows_ = []
            for u_, r_ in RT.items():
                if not (r_.get("lt") or r_.get("st")):
                    continue
                # un fonds de titrisation (FCTC, note « (SF) ») n'est pas la société qui l'a créé : rangé avec les émetteurs d'obligations
                sf_ = "(SF)" in (r_.get("lt") or "") or bool(re.search(r"(?<![a-z])fctc(?![a-z])", ((r_.get("ti") or "") + " " + u_).lower()))
                t_ = None if sf_ else r_.get("t") if r_.get("t") in tick else ev_t.get(u_)
                soc_ = r_.get("soc")
                if not t_ and ":" in (r_.get("ti") or ""):  # émetteur non coté : nom tel qu'il figure dans l'intitulé de l'avis
                    soc_ = r_["ti"].split(":")[0].strip()
                rows_.append({"u": u_, "t": t_, "soc": soc_, "ti": r_.get("ti"), "d": r_.get("d"), "ag": r_.get("ag"), "lt": r_.get("lt"), "lt0": r_.get("lt0"),
                              "st": r_.get("st"), "st0": r_.get("st0"), "out": r_.get("out"), "exp": r_.get("exp"), "val": r_.get("val"), "scale": r_.get("scale")})
            rows_.sort(key=lambda x: x.get("d") or "", reverse=True)
            last_ = {}
            for x in rows_:  # dernière notation connue par société cotée
                if x["t"] and x["t"] not in last_:
                    last_[x["t"]] = x
            for s_ in secs:
                x = last_.get(s_["id"])
                if x:
                    s_["rating"] = {k: x.get(k) for k in ("ag", "lt", "st", "out", "d", "exp")}
            with open(os.path.join(out, "ratings.json"), "w", encoding="utf8") as fh:
                json.dump({"rows": rows_, "n_docs": len(RT), "n_read": len(rows_)}, fh, separators=(",", ":"), ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        log("notations illisibles :", e)
    # annuaires des intervenants (brvm.org)
    try:
        sg_ = os.path.join(a.extra, "sgi.json") if a.extra else None
        if sg_ and os.path.exists(sg_):
            shutil_copy = json.load(open(sg_, encoding="utf8"))
            with open(os.path.join(out, "sgi.json"), "w", encoding="utf8") as fh:
                json.dump(shutil_copy, fh, separators=(",", ":"), ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        log("intervenants illisibles :", e)
    # flottant officiel (avis de la BRVM lu la veille au soir) : publié tel quel, et rattaché à chaque action
    try:
        fp_ = os.path.join(a.extra, "flottant.json") if a.extra else None
        FLO = json.load(open(fp_, encoding="utf8")) if fp_ and os.path.exists(fp_) else None
        if FLO and FLO.get("rows"):
            for s_ in secs:
                r_ = FLO["rows"].get(s_["id"])
                if s_.get("mkt") == "BRVM" and r_:
                    s_["flo"] = r_["pct"]
            with open(os.path.join(out, "flottant.json"), "w", encoding="utf8") as fh:
                json.dump(FLO, fh, separators=(",", ":"), ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        log("flottant officiel illisible :", e)
    try:  # retenue à la source sur les dividendes des sociétés cotées, par pays (taux légaux lus sur les textes officiels, DIVC)
        rt_ = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", "retenues_dividendes.json"), encoding="utf8"))
        with open(os.path.join(out, "retenues.json"), "w", encoding="utf8") as fh:
            json.dump({"d": rt_.get("d"), "rows": [{k: r.get(k) for k in ("pays", "nom", "pp", "pm", "exc_pp", "exc_pm", "texte")} for r in rt_.get("rows") or []]},
                      fh, separators=(",", ":"), ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        log("retenues par pays illisibles :", e)
    try:  # fiche et BRVM côte à côte (nombre de titres, flottant, secteur, BNPA) pour le contrôle du matin
        with open(os.path.join(out, "miroir.json"), "w", encoding="utf8") as fh:
            json.dump({"d": dt.date.today().isoformat(), "rows": MIROIR, "soc_diff": SOC_DIFF, "soc_new": SOC_NEW}, fh, separators=(",", ":"), ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        log("miroir illisible :", e)
    # secteur officiel de chaque action (pages par secteur de brvm.org, lues chaque soir) : secteur affiché (voir SECT_OFF) et
    # publié pour le contrôle du matin, qui liste les titres où la fiche dit autre chose
    try:
        sp_ = os.path.join(a.extra, "secteurs_brvm.json") if a.extra else None
        SEC_ = json.load(open(sp_, encoding="utf8")) if sp_ and os.path.exists(sp_) else None
        if SEC_ and SEC_.get("rows"):
            with open(os.path.join(out, "secteurs.json"), "w", encoding="utf8") as fh:
                json.dump({"d": SEC_.get("d"), "ts": SEC_.get("ts"), "rows": SEC_["rows"]}, fh, separators=(",", ":"), ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        log("secteurs officiels illisibles :", e)
    for name, obj in (("summary", summ), ("weekly", wm), ("breadth", breadth), ("fundamentals", fmeta), ("dividends", dmeta), ("events", emeta),
                      ("events_recent", emeta[:80]), ("boc_check", {**boc_chk, "avis": av_chk, "base_rejets": base_rej, "base_ext": base_ext, "ecartes": ECARTES, "nouveaux": BOC_NOUV, "d": dt.date.today().isoformat()} if BOC else {"n": 0, "avis": av_chk, "base_rejets": base_rej, "base_ext": base_ext, "ecartes": ECARTES})):
        with open(os.path.join(out, name + ".json"), "w", encoding="utf8") as fh:
            json.dump(obj, fh, separators=(",", ":"), ensure_ascii=False)
    # recherche MOTS CLES : index de tous les documents de la BRVM connus du terminal (après les avis, rapports et notations du jour)
    try:
        import build_search
        build_search.build(out, src, a.search_src, a.boc, log, comptes=a.comptes)
    except Exception as e:  # noqa: BLE001
        log("index de recherche non refait :", e)
    # QLAB : moteur de valorisation (passage du soir seulement) ; une erreur laisse en place la dernière estimation valide
    if not a.live:
        try:
            import qlab
            qlab.run(out, a.extra, log)
        except Exception as e:  # noqa: BLE001
            log("QLAB : valorisation non refaite (dernière estimation valide conservée) :", e)
    # QLAB 3 « Prévisions » retiré le 19/10/2026 (demande du propriétaire) : ses anciens fichiers quittent les données publiées
    # (une copie reste dans les données brutes, qlabp/) ; la lecture des publications intermédiaires (comptes.py) est gardée
    _qp = os.path.join(out, "qlabp")
    if os.path.isdir(_qp):
        import shutil as _sh
        _sh.rmtree(_qp, ignore_errors=True)
        log("QLAB Prévisions retiré : dossier qlabp enlevé des données publiées")
    tot = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(out) for f in fs)
    log(f"{len(secs)} securities, {sum(len(b['d']) for b in files.values())} rows, {tot / 1e6:.1f} MB -> {out}")


if __name__ == "__main__":
    sys.exit(main())
