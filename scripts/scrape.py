#!/usr/bin/env python3
"""Live feed for the FQT terminal (standard library only, runs on GitHub Actions every 15 minutes).

Writes into --out/data :
  live.json    QQQ quote + 5-minute bars (Yahoo, falls back to Nasdaq), and any source errors
  quotes.json  latest quotes keyed by terminal id: QQQ, the 48 BRVM stocks and the BRVM indices
  session.json the BRVM session as published on brvm.org (also kept in --state for the next run)
In eod mode the session is appended to seed/brvm_daily.csv (one line per stock per session).
The full history (data/s/*.json, summary.json…) is rebuilt separately by build_terminal.py.
Any source that fails keeps the last good values, so the site never goes blank.
"""
import argparse, csv, datetime as dt, io, json, os, re, shutil, sys, time, urllib.parse, urllib.request
from zoneinfo import ZoneInfo
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "seed")
MARKETS = ["VTI", "SOXX", "NVDA", "MSFT", "AMZN", "GOOG", "META", "TSLA", "AVGO", "AMD", "ORCL",
           "INTC", "MU", "MRVL", "TSM", "PLTR", "UBER", "SOFI", "WDC", "ROBO", "0050"]
YSYM = {"0050": "0050.TW"}
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
FR_MONTHS = {m: i + 1 for i, m in enumerate(["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                                            "août", "septembre", "octobre", "novembre", "décembre"])}
NY = ZoneInfo("America/New_York")
FR_DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


ERRORS = {}


def log(*a):
    print("[scrape]", *a, flush=True)


def fail(key, e):
    ERRORS[key] = f"{type(e).__name__}: {e}"[:300]
    log(key, "failed:", ERRORS[key])


YH_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


def get(url, tries=3, timeout=30, headers=None):
    err = None
    for k in range(tries):
        try:
            if "finance.yahoo.com" in url:  # mêmes en-têtes que la collecte du soir (acceptés par Yahoo, qui renvoie 429 sinon)
                h = {"User-Agent": YH_UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip"}
            else:
                h = {"User-Agent": UA, "Accept": "application/json,text/html,*/*;q=0.8", "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
            h.update(headers or {})
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b":
                    import gzip
                    b = gzip.decompress(b)
                return b
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(2 + 4 * k)
    raise err


def load(name, default=None, folder=None):
    try:
        with open(os.path.join(folder or DATA, name), encoding="utf8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def dump(obj, *paths):
    s = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    for p in paths:  # (fichier temporaire puis remplacement : jamais de fichier à moitié écrit si le passage est coupé)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = f"{p}.tmp{os.getpid()}"
        with open(tmp, "w", encoding="utf8") as f:
            f.write(s)
        os.replace(tmp, p)


# ------------------------------------------------------------------ Yahoo
def chart(sym, rng, interval, events=""):
    err = None
    for host in ("query1", "query2"):
        url = (f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
               f"?range={rng}&interval={interval}&includePrePost=false" + (f"&events={events}" if events else ""))
        try:
            j = json.loads(get(url, headers={"Referer": "https://finance.yahoo.com/", "Origin": "https://finance.yahoo.com"}))
            res = j["chart"]["result"][0]
            if not res.get("timestamp"):
                raise ValueError("no bars")
            return res
        except Exception as e:  # noqa: BLE001
            err = e
    raise err


def day_of(ts, off):
    return dt.datetime.fromtimestamp(ts + off, dt.timezone.utc).date().isoformat()


def session_open(meta, now):
    reg = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
    return bool(reg) and reg.get("start", 0) <= now < reg.get("end", 0)


def live_quote():
    res = chart("QQQ", "5d", "5m")
    meta, off, now = res["meta"], res["meta"].get("gmtoffset", 0), time.time()
    q = res["indicators"]["quote"][0]
    bars = [(t, q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i] or 0)
            for i, t in enumerate(res["timestamp"]) if q["close"][i] is not None and q["open"][i] is not None]
    if not bars:
        raise ValueError("no intraday bars")
    tp = meta.get("currentTradingPeriod") or {}
    within = lambda p: bool(p) and p.get("start", 0) <= now < p.get("end", 0)  # noqa: E731
    state = ("REGULAR" if within(tp.get("regular")) else "PRE" if within(tp.get("pre"))
             else "POST" if within(tp.get("post")) else "CLOSED")
    price = float(meta.get("regularMarketPrice") or bars[-1][4])
    day = day_of(meta.get("regularMarketTime") or bars[-1][0], off)
    today = [b for b in bars if day_of(b[0], off) == day]
    before = [b for b in bars if day_of(b[0], off) < day]
    prev = before[-1][4] if before else float(meta.get("chartPreviousClose") or price)
    r2 = lambda v: round(float(v), 2)  # noqa: E731
    return {
        "price": r2(price), "prev": r2(prev), "chg": round(price / prev - 1, 6), "day": day, "state": state,
        "open": r2(today[0][1]) if today else r2(price),
        "dayHigh": r2(max(b[2] for b in today)) if today else r2(price),
        "dayLow": r2(min(b[3] for b in today)) if today else r2(price),
        # volume du jour : volume quotidien de Yahoo ; la somme des barres de 5 minutes n'est pas fiable (QQQ 490,8 M, ×10,7)
        "vol": int(meta.get("regularMarketVolume") or 0) or None, "time": int(meta.get("regularMarketTime") or bars[-1][0]),
    }, {"t": [b[0] for b in bars], "o": [r2(b[1]) for b in bars], "h": [r2(b[2]) for b in bars],
        "l": [r2(b[3]) for b in bars], "c": [r2(b[4]) for b in bars], "v": [int(b[5]) for b in bars]}


# ------------------------------------------------------------------ Nasdaq fallbacks (no dividends)
NQ_H = {"Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"}


def money(x):
    """« $1,234.56 » -> 1234.56 (format Nasdaq : virgule des milliers, point décimal)."""
    if x in (None, "", "N/A"):
        return None
    try:
        return float(str(x).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def us_session(now=None):
    """Séance US d'après l'heure de New York (jours fériés non gérés : la date des cours le corrige)."""
    t = (now or dt.datetime.now(NY)).astimezone(NY)
    if t.weekday() >= 5:
        return "CLOSED"
    hm = (t.hour, t.minute)
    return "PRE" if (4, 0) <= hm < (9, 30) else "REGULAR" if hm < (16, 0) and hm >= (9, 30) else "POST" if (16, 0) <= hm < (20, 0) else "CLOSED"


def nasdaq_live():
    j = json.loads(get("https://api.nasdaq.com/api/quote/QQQ/chart?assetclass=etf", headers=NQ_H))
    d = j["data"]
    def regular(t):
        lt = dt.datetime.fromtimestamp(t, NY)
        return (9, 30) <= (lt.hour, lt.minute) < (16, 0)
    pts = [(int(p["x"]) // 1000, float(p["y"])) for p in d.get("chart") or [] if p.get("y") is not None]
    pts = [p for p in pts if regular(p[0])] or pts
    if not pts:
        raise ValueError("no chart points")
    price = money(d.get("lastSalePrice")) or pts[-1][1]
    prev = money(d.get("previousClose")) or pts[0][1]
    bars, cur = [], None
    for t, y in pts:
        b = t - t % 300
        if cur and cur[0] == b:
            cur[2], cur[3], cur[4] = max(cur[2], y), min(cur[3], y), y
        else:
            cur = [b, y, y, y, y, 0]
            bars.append(cur)
    day = dt.datetime.fromtimestamp(pts[-1][0], NY).date().isoformat()
    state = us_session()
    if day != dt.datetime.now(NY).date().isoformat() and state == "REGULAR":
        state = "CLOSED"
    r2 = lambda v: round(float(v), 2)  # noqa: E731
    return {"price": r2(price), "prev": r2(prev), "chg": round(price / prev - 1, 6), "day": day, "state": state,
            "open": r2(bars[0][1]), "dayHigh": r2(max(b[2] for b in bars)), "dayLow": r2(min(b[3] for b in bars)),
            "vol": 0, "time": pts[-1][0], "src": "nasdaq"}, \
        {"t": [b[0] for b in bars], "o": [r2(b[1]) for b in bars], "h": [r2(b[2]) for b in bars],
         "l": [r2(b[3]) for b in bars], "c": [r2(b[4]) for b in bars], "v": [0 for _ in bars]}


# ------------------------------------------------------------------ BRVM
class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell, self.text = [], None, None, []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)


def parse(html):
    p = Tables()
    p.feed(html)
    return p.rows, " ".join(" ".join(p.text).split())


def num(x):
    x = (x or "").replace("\xa0", "").replace(" ", "").replace(" ", "").replace("%", "").replace(",", ".").strip()
    try:
        return float(x)
    except ValueError:
        return None


def fr_dates(text):
    out = []
    pat = r"(%s),?\s+(\d{1,2})\s+([a-zéû]+),?\s+(\d{4})" % "|".join(FR_DAYS)
    for m in re.finditer(pat, text, flags=re.I):
        mo = FR_MONTHS.get(m.group(3).lower())
        if mo:
            try:
                out.append(dt.date(int(m.group(4)), mo, int(m.group(2))))
            except ValueError:
                pass
    return out


def scrape_brvm(prev):
    html = get("https://www.brvm.org/fr/cours-actions/0").decode("utf8", "replace")
    rows, text = parse(html)
    out = []
    for r in rows:
        if len(r) >= 7 and re.fullmatch(r"[A-Z]{3,6}", r[0].strip()):
            t, vol, pv, op, cl, var = r[0].strip(), num(r[2]), num(r[3]), num(r[4]), num(r[5]), num(r[6])
            if cl is None or cl <= 0:
                continue
            # After the session brvm.org already shows the new reference price as "cours veille":
            # the published variation is the reliable field, the previous close is derived from it.
            if var is None or abs(var) > 15:  # BRVM daily band is ±7.5 %: anything wider is a parse error
                var = round((cl / pv - 1) * 100, 2) if pv else 0.0
            pv = round(cl / (1 + var / 100), 2) if var > -100 else pv
            out.append({"t": t, "vol": int(vol or 0), "prev": pv, "o": op if op else None, "c": cl, "vj": var})
    if len(out) < 40:
        raise ValueError(f"only {len(out)} BRVM rows parsed")
    # nombre de titres et capitalisations publiés par la BRVM (page « Capitalisations ») : base officielle des calculs par action
    caps = {r["t"]: {k: r[k] for k in ("sh", "capf", "capg") if r.get(k)} for r in (prev or {}).get("rows", []) if r.get("sh")}
    try:
        crows, _ = parse(get("https://www.brvm.org/fr/capitalisations/0").decode("utf8", "replace"))
        for r in crows:
            if len(r) >= 6 and re.fullmatch(r"[A-Z]{3,6}", r[0].strip()):
                sh_, capf_, capg_ = num(r[2]), num(r[4]), num(r[5])
                if sh_ and sh_ > 0:
                    caps[r[0].strip()] = {"sh": int(sh_), "capf": capf_ or 0, "capg": capg_ or 0}
    except Exception as e:  # noqa: BLE001
        fail("brvm_caps", e)
    for r in out:
        r.update(caps.get(r["t"], {}))
    today = dt.date.today()
    ds = [d for d in fr_dates(text) if today - dt.timedelta(days=10) <= d <= today]
    sess = min(ds) if ds else today
    capA, capO = (prev or {}).get("capA"), (prev or {}).get("capO")
    m = re.search(r"Actions?\s*:?\s*([\d][\d\s  \.]{9,})\s*FCFA", text)
    if m:
        capA = num(m.group(1).replace(".", "")) or capA
    m = re.search(r"Obligations?\s*:?\s*([\d][\d\s  \.]{9,})\s*FCFA", text)
    if m:
        capO = num(m.group(1).replace(".", "")) or capO
    idx, sect = (prev or {}).get("idx", []), (prev or {}).get("sect", [])
    try:
        idx, sect = scrape_indices(idx, sect)
    except Exception as e:  # noqa: BLE001
        fail("brvm_indices", e)
    label = f"{FR_DAYS[sess.weekday()]} {sess.day} {[k for k, v in FR_MONTHS.items() if v == sess.month][0]} {sess.year}"
    return {"asof": sess.isoformat(), "session": label, "src": "brvm.org (cours du jour)", "rows": out,
            "idx": idx, "sect": sect, "capA": capA, "capO": capO, "ts": int(time.time())}


IDX_MAP = [("TOTAL RETURN", "BRVM-CTR", "BRVM Composite TR"), ("COMPOSITE", "BRVM-C", "BRVM Composite"),
           ("BRVM-30", "BRVM-30", "BRVM 30"), ("BRVM 30", "BRVM-30", "BRVM 30"), ("PRESTIGE", "BRVM-PRES", "BRVM Prestige"),
           ("PRINCIPAL", "BRVM-PRIN", "BRVM Principal")]
SECT_MAP = [("CONSOMMATION DE BASE", "CB"), ("DISCRETIONNAIRE", "CD"), ("DISCRÉTIONNAIRE", "CD"), ("ENERGIE", "EN"),
            ("ÉNERGIE", "EN"), ("INDUSTRIELS", "IN"), ("SERVICES FINANCIERS", "SF"), ("SERVICES PUBLICS", "SP"),
            ("TELECOMMUNICATIONS", "TL"), ("TÉLÉCOMMUNICATIONS", "TL")]


def scrape_indices(idx_prev, sect_prev):
    rows, _ = parse(get("https://www.brvm.org/fr/indices").decode("utf8", "replace"))
    idx, sect, score = {}, {}, {}
    for r in rows:
        if not r or "BRVM" not in r[0].upper():
            continue
        name = r[0].upper()
        nums = [v for v in (num(c) for c in r[1:]) if v is not None]
        if len(nums) >= 3 and nums[0] > 0 and abs((nums[1] / nums[0] - 1) * 100 - nums[2]) < 0.15:
            close, var, q = nums[1], nums[2], 2          # prev | close | var% (| YTD)
        elif len(nums) >= 2 and nums[0] > 1 and abs(nums[1]) < 25:
            close, var, q = nums[0], nums[1], 1          # close | var%
        else:
            continue
        key = None
        for k, sc in SECT_MAP:
            if k in name:
                key, rec = "s:" + sc, {"k": sc, "v": close, "vj": var}
                break
        else:
            for k, code, label in IDX_MAP:
                if k in name:
                    key, rec = "i:" + code, {"k": code, "n": label, "v": close, "vj": var}
                    break
        if key and q >= score.get(key, 0):
            score[key] = q
            (sect if key[0] == "s" else idx)[key[2:]] = rec
    order = ["BRVM-C", "BRVM-30", "BRVM-PRES", "BRVM-PRIN", "BRVM-CTR"]
    if "BRVM-C" not in idx:
        raise ValueError("composite not found")
    prev = {x["k"]: x for x in idx_prev}
    idx_out = [idx.get(k) or prev.get(k) for k in order if idx.get(k) or prev.get(k)]
    sp = {x["k"]: x for x in sect_prev}
    sect_out = [sect.get(k) or sp.get(k) for k in ["TL", "CD", "SF", "CB", "IN", "EN", "SP"] if sect.get(k) or sp.get(k)]
    return idx_out, sect_out


def archive_brvm(b):
    """Append the session to seed/brvm_daily.csv (one line per stock per session)."""
    path = os.path.join(DATA, "brvm_daily.csv")
    # une séance déjà archivée est remplacée (la dernière lecture, celle du soir, l'emporte)
    keep = []
    if os.path.exists(path):
        with open(path, encoding="utf8") as f:
            keep = [line for line in f if not line.startswith(b["asof"] + ",")]
    with open(path, "w", encoding="utf8") as f:
        f.writelines(keep or ["date,ticker,close,var_pct,volume,prev\n"])
        for r in b["rows"]:
            f.write(f'{b["asof"]},{r["t"]},{r["c"]},{r["vj"]},{r["vol"]},{r["prev"]}\n')
    log("archived BRVM session", b["asof"])


# ------------------------------------------------------------------ main
IDX_CODE = {"BRVM-C": "BRVMC", "BRVM-30": "BRVM30", "BRVM-PRES": "BRVMPR", "BRVM-PRIN": "BRVMPA", "TL": "BRVM-TEL", "CD": "BRVM-CD",
            "SF": "BRVM-SF", "CB": "BRVM-CB", "IN": "BRVM-IN", "EN": "BRVM-EN", "SP": "BRVM-SP"}


MONTHS_EN = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
NQ_SYM = {"CCMP": "COMP", "RTY": "RUT"}


def _nq_rows(chunk):
    """Un paquet watchlist Nasdaq ; en cas d'échec, le paquet est coupé en deux pour isoler le symbole fautif."""
    url = "https://api.nasdaq.com/api/quote/watchlist?" + "&".join("symbol=" + urllib.parse.quote(f"{s.lower()}|{ac}") for _, s, ac in chunk)
    try:
        j = json.loads(get(url, tries=2, headers=NQ_H))
        rows = j.get("data") or []
        if isinstance(rows, dict):
            rows = rows.get("rows") or rows.get("data") or []
    except Exception as e:  # noqa: BLE001
        rows, err = [], e
    else:
        err = None
    if rows or len(chunk) == 1:
        if not rows and err:
            fail("nasdaq_" + chunk[0][1], err)
        return rows
    h = len(chunk) // 2
    time.sleep(0.3)
    return _nq_rows(chunk[:h]) + _nq_rows(chunk[h:])


def _nq_ext(sym, ac, kind):
    """Pré-marché (kind=pre) ou après-bourse (kind=post) d'un titre : dernier échange, volume, plus haut / bas."""
    j = json.loads(get(f"https://api.nasdaq.com/api/quote/{sym}/extended-trading?markettype={kind}&assetclass={ac}&time=0", tries=1, timeout=15, headers=NQ_H))
    d = j.get("data") or {}
    rows = (d.get("infoTable") or {}).get("rows") or []
    if not rows:
        return None
    r = rows[0]
    m = re.match(r"\$?([\d,.]+)", str(r.get("consolidated") or ""))
    if not m:
        return None
    last = money(m.group(1))
    upd = " ".join(d.get("lastUpdateInfo") or [])
    mt = re.search(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4}) (\d{1,2}):(\d{2}) (AM|PM) ET", upd)
    when, t = None, None
    if mt and mt.group(1) in MONTHS_EN:
        hh = int(mt.group(4)) % 12 + (12 if mt.group(6) == "PM" else 0)
        when = f"{mt.group(3)}-{MONTHS_EN[mt.group(1)]:02d}-{int(mt.group(2)):02d}"
        t = f"{hh:02d}:{mt.group(5)} ET"
    vol = num(str(r.get("volume") or "").replace(",", ""))
    hi = re.match(r"\$?([\d,.]+)", str(r.get("highPrice") or ""))
    lo = re.match(r"\$?([\d,.]+)", str(r.get("lowPrice") or ""))
    # clôture précédente (« Previous Close ») et clôture du jour (« Close » seul) : l'ancienne recherche de « Close: » prenait aussi
    # « Previous Close », d'où un après-bourse calculé contre la clôture de la veille (variation du jour affichée comme après-bourse)
    pc_ = cl_ = None
    for m_ in re.finditer(r"(?:([A-Za-z'’.]+)\s+)?Close:\s*\$?([\d,.]+)", str(d.get("previousInfo") or "")):
        w_ = (m_.group(1) or "").lower().rstrip(".")
        if w_ in ("previous", "prev", "prior"):
            pc_ = pc_ or money(m_.group(2))
        elif w_ in ("", "today's", "today’s", "regular", "market", "official"):
            cl_ = cl_ or money(m_.group(2))
    return {"s": kind, "last": last, "d": when, "t": t, "vol": int(vol) if vol else None, "pc": pc_, "cl": cl_,
            "hi": money(hi.group(1)) if hi else None, "lo": money(lo.group(1)) if lo else None}


# ------------------------------------------------------------------ contrôles des cours US (référence de variation, cours aberrants)
TOL_REF = 0.0005  # deux sources d'une même clôture doivent concorder à 0,05 % près


def _hm(t):
    """« 18:01 ET » -> (18, 1) ; None si illisible."""
    m = re.match(r"(\d{1,2}):(\d{2})", str(t or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def confirmed(cands, tol=TOL_REF):
    """Première valeur (par ordre de préférence) confirmée par au moins une autre source à tol près : (valeur, « src1+src2 ») ;
    (None, None) si aucune ne l'est : référence incertaine, pas de variation plutôt qu'une variation fausse."""
    cands = [(k, float(x)) for k, x in cands if isinstance(x, (int, float)) and x > 0]
    for k, x in cands:
        ok = [k2 for k2, y in cands if k2 != k and abs(y / x - 1) <= tol]
        if ok:
            return x, "+".join([k] + ok)
    return None, None


def vol_ok(hist, x):
    """Volume du jour vraisemblable (même règle que build_terminal.vol_ok) : au plus 5 fois la médiane des 60 séances précédentes
    et différent de plus de 0,1 % du volume de la séance précédente (volume de la veille resservi par la source)."""
    if not x or x <= 0:
        return False
    nz = [y for y in (hist or [])[-60:] if y]
    if len(nz) >= 20:
        import statistics
        if x > 5 * statistics.median(nz):
            return False
    p = (hist or [None])[-1]
    return not (p and abs(x - p) / p <= 0.001)


def series_ref(out_data, sid, d):
    """Série publiée (data/s/<id>.json) : dernière séance antérieure à d (AAAA-MM-JJ) -> {c, d, vh (volumes jusqu'à elle)} ;
    None si la série est illisible ou n'a rien avant d."""
    try:
        import bisect
        b = load(sid.replace(".", "_") + ".json", folder=os.path.join(out_data, "s"))
        i = bisect.bisect_left(b["d"], int(d.replace("-", ""))) - 1
        if i < 0:
            return None
        v = b.get("v") or []
        return {"c": b["c"][i], "d": b["d"][i], "vh": v[max(0, i - 59): i + 1] if len(v) == len(b["d"]) else []}
    except Exception:  # noqa: BLE001
        return None


def us_check(sid, rec, old, ser, sess, rng=None, notes=None):
    """Cours US du relevé (Nasdaq) contrôlé avant publication ; renvoie la cotation à publier, ou None (la page garde alors la
    dernière valeur sûre de la série).
      - Référence de variation = clôture officielle de la séance précédente, retenue seulement si deux sources concordent
        (clôture précédente de l'après-bourse, previousClosePrice de Nasdaq, série publiée, et en séance la clôture déduite
        de la variation Nasdaq) ; sinon celle déjà confirmée plus tôt pour la même séance ; sinon aucune : pct = None.
        (Le percentageChange de Nasdaq n'est plus publié tel quel : après 16 h il mesure l'après-bourse, et previousClosePrice
        est alors souvent la clôture d'avant-veille.)
      - Après-bourse : variation calculée contre la clôture du jour (confirmée par deux sources, ou déduite de la variation
        Nasdaq de l'après-bourse) ; pré-marché : contre la clôture précédente ; sinon pas de variation.
      - Cours aberrant (C2) : un dernier cours hors séance qui s'écarte de plus de 3 % de la séance étendue, ou un cours de séance
        hors de la fourchette du jour élargie de 2 % (quand elle est connue), est écarté ; la clôture du jour confirmée ou le
        cours sûr du relevé précédent le remplace, sinon la cotation n'est pas publiée. Le cours étendu reste dans ext.
      - Volume du jour (I2) : retiré s'il n'est pas vraisemblable (vol_ok)."""
    notes = notes if notes is not None else []
    last, d = rec.get("last"), rec.get("d")
    pnq = rec.pop("_pnq", None)
    pc_nq = rec.pop("prev", None)
    old = old if old and d and old.get("d") == d else {}
    ext = rec.get("ext") or {}
    x_pc, x_cl = ext.pop("pc", None), ext.pop("cl", None)
    hm = _hm(rec.get("t"))
    in_reg = hm is not None and (9, 30) <= hm <= (16, 0)
    if not last or not d:
        rec["pct"] = None
        return rec
    # clôture officielle de la séance précédente
    imp = last / (1 + pnq) if pnq is not None and pnq > -1 and sess == "REGULAR" and in_reg and hm < (16, 0) else None
    pc, rf = confirmed([("ext", x_pc), ("nq", pc_nq), ("serie", (ser or {}).get("c")), ("pct", imp)])
    if not pc and old.get("rf") and old.get("prev"):
        pc, rf = old["prev"], old["rf"]
    # clôture du jour (après-bourse) : confirmée par deux sources, ou seulement déduite de la variation Nasdaq de l'après-bourse
    post_print = hm is not None and hm > (16, 0) and sess in ("POST", "CLOSED")
    imp_cl = last / (1 + pnq) if pnq is not None and pnq > -1 and post_print and sess == "POST" else None
    if imp_cl and pc and abs(imp_cl / pc - 1) <= TOL_REF and abs(last / pc - 1) > TOL_REF:
        imp_cl = None  # (variation Nasdaq peut-être mesurée contre la veille : sens douteux, rien n'est déduit)
    t16 = last if hm == (16, 0) else old.get("last") if _hm(old.get("t")) == (16, 0) and not old.get("xl") else None
    cl, _ = confirmed([("ext", x_cl), ("t16", t16), ("pct", imp_cl)])
    cl = cl or old.get("cl")
    # cours aberrant
    def bad(px):
        if ext.get("last") and (hm is None or not in_reg) and abs(px / ext["last"] - 1) > 0.03:
            return f"{px:g} contre {ext['last']:g} en séance étendue"
        if rng and (hm is None or in_reg) and not (rng[0] * 0.98 <= px <= rng[1] * 1.02):
            return f"{px:g} hors de la fourchette du jour {rng[0]:g}-{rng[1]:g}"
        return None
    why = bad(last)
    if why:
        alt = cl or (old.get("last") if old.get("last") and not bad(old["last"]) else None)
        notes.append(f"{sid} {why}" + (f" -> {alt:g}" if alt else " -> non publié"))
        if not alt:
            return None
        rec["last"], rec["xl"], last = round(alt, 4), last, alt
    rec["pct"] = round(last / pc - 1, 6) if pc else None
    if pc:
        rec["prev"], rec["rf"] = round(pc, 4), rf
    if cl:
        rec["cl"] = round(cl, 4)
    # séance étendue : variation contre la clôture du jour (après-bourse) ou la clôture précédente (pré-marché)
    if ext.get("last") and "ref" not in ext:
        ref = pc if ext.get("s") == "pre" else (cl or imp_cl)
        ext["chg"] = round(ext["last"] - ref, 4) if ref else None
        ext["pct"] = round(ext["last"] / ref - 1, 6) if ref else None
        ext["ref"] = round(ref, 4) if ref else None
    if rec.get("vol") and ser is not None and not vol_ok(ser.get("vh"), rec["vol"]):
        rec.pop("vol")
    return rec


# contrats à terme 1er mois (différé ~10 min) : les cours d'Investing, TradingView, Bloomberg (CO1, CL1, NG1, GC1)
FUTS = (("BRENT", "@LCO.1"), ("WTI", "@CL.1"), ("NATGAS", "@NG.1"), ("GOLD", "@GC.1"))


def _fnum(x):
    try:
        return float(str(x).replace(",", "").replace("%", "").replace("+", ""))
    except (TypeError, ValueError):
        return None


def cnbc_reset(r, last, prev):
    """Cotation CNBC remise à zéro après le règlement : variation « UNCH », clôture précédente égale au dernier cours (ou absente).
    La variation publiée (0,00 %) n'est alors pas celle de la séance : elle doit être recalculée contre le règlement précédent."""
    return (str(r.get("change") or "").strip().upper() == "UNCH" or str(r.get("change_pct") or "").strip().upper() == "UNCH"
            or not prev or abs(prev - last) < 1e-9)


def prev_bday(day):
    """Jour ouvré (lundi-vendredi) précédent."""
    day -= dt.timedelta(days=1)
    while day.weekday() >= 5:
        day -= dt.timedelta(days=1)
    return day


def fut_settle(sid, day, ct, prev_q, out_data):
    """Règlement de la séance ouvrée précédant day pour un contrat 1er mois : celui déjà relevé pour la même séance et le même
    contrat (avant la remise à zéro de CNBC), sinon la clôture de la série publiée datée exactement du jour ouvré précédent
    (jamais deux séances en arrière, ni un samedi ou un dimanche) ; (None, None) sinon."""
    old = (prev_q or {}).get(sid) or {}
    if old.get("d") == day.isoformat() and old.get("ct") == ct and old.get("rf") and old.get("prev"):
        return old["prev"], old["rf"]
    if out_data:
        ser = series_ref(out_data, sid, day.isoformat())
        if ser and ser.get("c") and ser.get("d") == int(prev_bday(day).strftime("%Y%m%d")):
            return ser["c"], "serie"
    return None, None


def fut_quotes(q, prev_q=None, out_data=None):
    try:
        u = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=" + urllib.parse.quote("|".join(c for _, c in FUTS))
             + "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json")
        rows = json.loads(get(u, tries=2))["FormattedQuoteResult"]["FormattedQuote"]
        by = {r.get("symbol"): r for r in rows}
        for sid, cs in FUTS:
            r = by.get(cs) or {}
            last, prev = _fnum(r.get("last")), _fnum(r.get("previous_day_closing"))
            if not last or not r.get("last_time"):
                continue
            t = dt.datetime.fromisoformat(re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", r["last_time"])).astimezone(NY)
            day = t.date() + (dt.timedelta(days=1) if t.hour >= 18 else dt.timedelta(0))  # séance CME/ICE : ouverte la veille à 18 h (New York)
            while day.weekday() >= 5:
                day += dt.timedelta(days=1)
            # après le règlement CNBC remet la variation à zéro (prev = last, « UNCH », ouverture / plus haut / plus bas à 0) : la
            # variation est recalculée contre le règlement de la séance ouvrée précédente, ou laissée vide (jamais 0,00 % inventé)
            rf = "cnbc"
            try:
                if cnbc_reset(r, last, prev):
                    prev, rf = fut_settle(sid, day, r.get("name"), prev_q, out_data)
            except Exception as e:  # noqa: BLE001
                prev, rf = None, None
                fail("cnbc_futures_ref_" + sid, e)
            pos = lambda x: x if x and x > 0 else None  # noqa: E731
            q[sid] = {"last": last, "prev": prev, "pct": round(last / prev - 1, 6) if prev else None, "d": day.isoformat(),
                      "o": pos(_fnum(r.get("open"))), "h": pos(_fnum(r.get("high"))), "l": pos(_fnum(r.get("low"))), "vol": int(_fnum(r.get("volume")) or 0) or None,
                      "src": "CNBC", "ct": r.get("name"), "exp": r.get("expiration_date")}
            if rf and prev:
                q[sid]["rf"] = rf
    except Exception as e:  # noqa: BLE001
        fail("cnbc_futures", e)


# tableau de bord pétrolier (CNBC, différé ~10 min) : courbes à terme Brent/WTI, essence et gazole (marges de raffinage), gaz,
# grandes pétrolières et armateurs de pétroliers (indicateur du fret)
OIL_CURVE = {"BRENT": ["@LCO.%d" % i for i in (1, 2, 3, 4, 5, 6, 9, 12, 18, 24)], "WTI": ["@CL.%d" % i for i in (1, 2, 3, 4, 5, 6, 9, 12, 18, 24)]}
OIL_PROD = ["@RB.1", "@HO.1", "@NG.1", "@NG.2", "@GC.1"]
OIL_EQ = ["XOM", "CVX", "SHEL", "BP", "TTE", "COP", "OXY", "EQNR", "PBR", "FRO", "DHT", "INSW", "STNG", "TNK", "NAT"]


def oil_board(out_data):
    syms = sum(OIL_CURVE.values(), []) + OIL_PROD + OIL_EQ
    by = {}
    try:
        for i in range(0, len(syms), 20):
            u = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=" + urllib.parse.quote("|".join(syms[i:i + 20]))
                 + "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json")
            for r in json.loads(get(u, tries=2))["FormattedQuoteResult"]["FormattedQuote"]:
                if r.get("symbol") and r.get("last"):
                    by[r["symbol"]] = r
    except Exception as e:  # noqa: BLE001
        fail("cnbc_oil", e)
        return
    old_by = {}
    try:  # relevé précédent : règlements de référence déjà connus pour la séance
        old_ = load("oil.json", folder=out_data) or {}
        for side in (old_.get("curve") or {}).values():
            for x in side or []:
                old_by[x.get("k")] = x
        for k_, x in (old_.get("prod") or {}).items():
            old_by[k_] = x
    except Exception:  # noqa: BLE001
        old_by = {}
    fut_id = {"@CL.1": "WTI", "@NG.1": "NATGAS", "@LCO.1": "BRENT", "@GC.1": "GOLD"}

    def sess_day(t_):
        t = dt.datetime.fromisoformat(re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", t_)).astimezone(NY)
        day = t.date() + (dt.timedelta(days=1) if t.hour >= 18 else dt.timedelta(0))
        while day.weekday() >= 5:
            day += dt.timedelta(days=1)
        return day

    def rec(r):
        o = {"n": r.get("name"), "last": _fnum(r.get("last")), "chg": _fnum(r.get("change")), "pct": (_fnum(r.get("change_pct")) or 0) / 100 if r.get("change_pct") else None,
             "prev": _fnum(r.get("previous_day_closing")), "exp": r.get("expiration_date"), "t": r.get("last_time"), "ccy": r.get("currencyCode"),
             "hi52": _fnum(r.get("yrhiprice")), "lo52": _fnum(r.get("yrloprice"))}
        # cotation remise à zéro après le règlement (« UNCH », prev = last) : variation recalculée contre le règlement précédent déjà
        # relevé pour la même séance et la même échéance (relevé précédent), ou la série du contrat 1er mois ; sinon laissée vide
        try:
            if o["last"] and str(r.get("symbol") or "").startswith("@") and cnbc_reset(r, o["last"], o["prev"]):
                o["chg"] = o["pct"] = None
                ref, day = None, sess_day(r["last_time"]) if r.get("last_time") else None
                ol = old_by.get(r.get("symbol")) or {}
                if day and ol.get("exp") == o["exp"] and ol.get("t") and sess_day(ol["t"]) == day and ol.get("prev") and ol.get("last") and \
                        (ol.get("rf") or (ol.get("chg") is not None and abs(ol["prev"] - ol["last"]) > 1e-9)):
                    ref = ol["prev"]
                elif day and r.get("symbol") in fut_id:
                    ref, _ = fut_settle(fut_id[r["symbol"]], day, None, None, out_data)
                o["prev"] = ref
                if ref:
                    o["chg"], o["pct"], o["rf"] = round(o["last"] - ref, 6), round(o["last"] / ref - 1, 6), 1
        except Exception as e:  # noqa: BLE001
            o["chg"] = o["pct"] = o["prev"] = None
            fail("cnbc_oil_ref", e)
        return o
    out = {"ts": int(time.time()), "src": "CNBC (ICE, NYMEX, NYSE ; différé)",
           "curve": {k: [dict(rec(by[s_]), k=s_) for s_ in v if s_ in by] for k, v in OIL_CURVE.items()},
           "prod": {s_: rec(by[s_]) for s_ in OIL_PROD if s_ in by}, "eq": [dict(rec(by[s_]), s=s_) for s_ in OIL_EQ if s_ in by]}
    if out["curve"].get("BRENT"):
        dump(out, os.path.join(out_data, "oil.json"))


# marchés mondiaux (CNBC, différé) : indices, matières premières, changes, taux souverains — fonctions WEI, GLCO, WB
WORLD = {
    "idx": [("AM", ".SPX"), ("AM", ".DJI"), ("AM", ".IXIC"), ("AM", ".RUT"), ("AM", ".GSPTSE"), ("AM", ".MXX"), ("AM", ".BVSP"), ("AM", ".MERV"),
            ("EU", ".STOXX50E"), ("EU", ".FTSE"), ("EU", ".GDAXI"), ("EU", ".FCHI"), ("EU", ".FTMIB"), ("EU", ".IBEX"), ("EU", ".AEX"), ("EU", ".SSMI"), ("EU", ".OMXS30"),
            ("MEA", ".TA35"), ("MEA", ".EGX30"),
            ("AS", ".N225"), ("AS", ".HSI"), ("AS", ".SSEC"), ("AS", ".SZI"), ("AS", ".KS11"), ("AS", ".TWII"), ("AS", ".NSEI"), ("AS", ".AXJO"), ("AS", ".STI"), ("AS", ".KLSE"),
            ("VOL", ".VIX")],
    "cmd": [("MET", "@GC.1"), ("MET", "@SI.1"), ("MET", "@HG.1"), ("MET", "@PL.1"), ("MET", "@PA.1"),
            ("AGR", "@CC.1"), ("AGR", "@KC.1"), ("AGR", "@CT.1"), ("AGR", "@SB.1"), ("AGR", "@W.1"), ("AGR", "@C.1"), ("AGR", "@S.1"), ("AGR", "@SM.1"), ("AGR", "@LC.1"),
            ("RTF", "@TU.1"), ("RTF", "@FV.1"), ("RTF", "@TY.1"), ("RTF", "@US.1")] + [("FF", f"@FF.{i}") for i in range(1, 14)] +
           [("IXF", "@SP.1"), ("IXF", "@ND.1"), ("IXF", "@DJ.1"), ("IXF", "@TFS.1"), ("IXF", "@VX.1"), ("IXF", "@FFI.1"), ("IXF", "@NK.1")],
    "fx": [("FX", ".DXY"), ("FX", "EUR="), ("FX", "GBP="), ("FX", "JPY="), ("FX", "CHF="), ("FX", "CNY="), ("FX", "XOF="), ("FX", "NGN="), ("FX", "GHS="), ("FX", "ZAR="),
           ("FX", "CAD="), ("FX", "AUD="), ("FX", "NZD="), ("FX", "SEK="), ("FX", "NOK="), ("FX", "DKK="), ("FX", "MXN="), ("FX", "BRL="), ("FX", "ARS="), ("FX", "ILS="),
           ("FX", "EGP="), ("FX", "MAD="), ("FX", "KES="), ("FX", "HKD="), ("FX", "KRW="), ("FX", "TWD="), ("FX", "INR="), ("FX", "SGD="), ("FX", "MYR="), ("FX", "TRY=")],
    "rt": [("US", "US1M"), ("US", "US3M"), ("US", "US6M"), ("US", "US1Y"), ("US", "US2Y"), ("US", "US5Y"), ("US", "US7Y"), ("US", "US10Y"), ("US", "US20Y"), ("US", "US30Y"),
           ("G", "DE10Y-DE"), ("G", "FR10Y-FR"), ("G", "GB10Y-GB"), ("G", "IT10Y-IT"), ("G", "ES10Y-ES"), ("G", "JP10Y-JP"), ("G", "CN10Y-CN")],
}


# symboles Yahoo des mêmes indices / contrats / devises : clôture de fin d'année précédente (base du « depuis janvier »)
WORLD_YH = {".SPX": "^GSPC", ".DJI": "^DJI", ".IXIC": "^IXIC", ".RUT": "^RUT", ".GSPTSE": "^GSPTSE", ".MXX": "^MXX", ".BVSP": "^BVSP", ".MERV": "^MERV",
            ".STOXX50E": "^STOXX50E", ".FTSE": "^FTSE", ".GDAXI": "^GDAXI", ".FCHI": "^FCHI", ".FTMIB": "FTSEMIB.MI", ".IBEX": "^IBEX", ".AEX": "^AEX", ".SSMI": "^SSMI",
            ".OMXS30": "^OMX", ".TA35": "TA35.TA", ".EGX30": "^CASE30", ".N225": "^N225", ".HSI": "^HSI", ".SSEC": "000001.SS", ".SZI": "399001.SZ", ".KS11": "^KS11",
            ".TWII": "^TWII", ".NSEI": "^NSEI", ".AXJO": "^AXJO", ".STI": "^STI", ".KLSE": "^KLSE", ".VIX": "^VIX",
            "@GC.1": "GC=F", "@SI.1": "SI=F", "@HG.1": "HG=F", "@PL.1": "PL=F", "@PA.1": "PA=F", "@CC.1": "CC=F", "@KC.1": "KC=F", "@CT.1": "CT=F", "@SB.1": "SB=F",
            "@W.1": "ZW=F", "@C.1": "ZC=F", "@S.1": "ZS=F", "@SM.1": "ZM=F", "@LC.1": "LE=F",
            ".DXY": "DX-Y.NYB", "EUR=": "EURUSD=X", "GBP=": "GBPUSD=X", "JPY=": "JPY=X", "CHF=": "CHF=X", "CNY=": "CNY=X", "XOF=": "XOF=X", "NGN=": "NGN=X", "GHS=": "GHS=X", "ZAR=": "ZAR=X",
            "CAD=": "CAD=X", "AUD=": "AUDUSD=X", "NZD=": "NZDUSD=X", "SEK=": "SEK=X", "NOK=": "NOK=X", "DKK=": "DKK=X", "MXN=": "MXN=X", "BRL=": "BRL=X", "ARS=": "ARS=X",
            "ILS=": "ILS=X", "EGP=": "EGP=X", "MAD=": "MAD=X", "KES=": "KES=X", "HKD=": "HKD=X", "KRW=": "KRW=X", "TWD=": "TWD=X", "INR=": "INR=X", "SGD=": "SGD=X", "MYR=": "MYR=X", "TRY=": "TRY=X"}


def year_bases(prev, budget=60):
    """Clôture de la dernière séance de l'année précédente pour chaque symbole (Yahoo, une fois par an, reprise si incomplète)."""
    y = dt.date.today().year
    yb = prev if prev and prev.get("y") == y else {"y": y, "v": {}}
    t0 = time.time()
    a = int(dt.datetime(y - 1, 12, 10, tzinfo=dt.timezone.utc).timestamp()); b = int(dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc).timestamp())
    for cs, ys in WORLD_YH.items():
        if cs in yb["v"] or time.time() - t0 > budget:
            continue
        for host in ("query1", "query2"):
            try:
                j = json.loads(get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ys)}?period1={a}&period2={b}&interval=1d", tries=1, timeout=8,
                                   headers={"Referer": "https://finance.yahoo.com/", "Origin": "https://finance.yahoo.com"}))
                r = j["chart"]["result"][0]; cl = [c for c in r["indicators"]["quote"][0]["close"] if c]
                if cl:
                    yb["v"][cs] = round(cl[-1], 6)
                break
            except Exception:  # noqa: BLE001
                continue
        time.sleep(0.2)
    return yb


def world_board(out_data):
    syms = [s_ for v in WORLD.values() for _, s_ in v]
    by = {}
    try:
        for i in range(0, len(syms), 20):
            u = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=" + urllib.parse.quote("|".join(syms[i:i + 20]))
                 + "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json")
            for r in json.loads(get(u, tries=2))["FormattedQuoteResult"]["FormattedQuote"]:
                if r.get("symbol") and r.get("last") and str(r.get("code")) == "0":
                    by[r["symbol"]] = r
    except Exception as e:  # noqa: BLE001
        fail("cnbc_world", e)
        if not by:
            return
    def rec(g, s_):
        r = by[s_]
        return {"g": g, "s": s_, "n": (r.get("name") or "").strip(), "last": _fnum(str(r.get("last")).replace("%", "")), "chg": _fnum(r.get("change")),
                "pct": (_fnum(r.get("change_pct")) or 0) / 100 if r.get("change_pct") not in (None, "UNCH") else None, "prev": _fnum(r.get("previous_day_closing")),
                "t": r.get("last_time"), "cty": r.get("countryCode"), "hi52": _fnum(r.get("yrhiprice")), "lo52": _fnum(r.get("yrloprice")),
                "exp": r.get("expiration_date"), "open": _fnum(r.get("open")), "hi": _fnum(r.get("high")), "lo": _fnum(r.get("low")), "y": "%" in str(r.get("last"))}
    out = {"ts": int(time.time()), "src": "CNBC (bourses, ICE, CME ; différé)"}
    for k, v in WORLD.items():
        out[k] = [rec(g, s_) for g, s_ in v if s_ in by]
    # Historique quotidien (Yahoo, 1 mois, au plus une fois par jour et par symbole) et bases de début d'année, relevés dans un fil
    # à part plafonné à 60 s : un serveur lent ne doit jamais bloquer le relevé de 15 min.
    prevf = load("world_mkt.json", folder=out_data) or {}
    prev_yb = prevf.get("yb")
    out["yb"] = prev_yb if prev_yb and prev_yb.get("y") == dt.date.today().year else {"y": dt.date.today().year, "v": {}}
    H = prevf.get("h") or {}; seen = prevf.get("hs") or {}
    hst = prevf.get("hst") or 0  # dernier essai d'historique : au plus toutes les 2 h si la source refuse
    need_seed = [cs for cs in WORLD_YH if cs in by and time.time() - (seen.get(cs) or 0) > 20 * 3600] if time.time() - hst > 2 * 3600 else []
    need_yb = len(out["yb"]["v"]) < len(WORLD_YH) and time.time() - (out["yb"].get("try") or 0) > 3600
    if need_seed or need_yb:
        import threading
        box = {"h": {}, "seen": {}}
        def _job():
            t0 = time.time()
            for cs in need_seed:
                if time.time() - t0 > 35:
                    break
                for host in ("query1", "query2"):
                    try:
                        j = json.loads(get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(WORLD_YH[cs])}?range=1mo&interval=1d", tries=1, timeout=8,
                                           headers={"Referer": "https://finance.yahoo.com/", "Origin": "https://finance.yahoo.com"}))
                        r = j["chart"]["result"][0]; off = (r.get("meta") or {}).get("gmtoffset") or 0
                        box["h"][cs] = {dt.datetime.fromtimestamp(t + off, dt.timezone.utc).date().isoformat(): round(c, 6)
                                        for t, c in zip(r.get("timestamp") or [], r["indicators"]["quote"][0]["close"]) if c}
                        box["seen"][cs] = int(time.time())
                        break
                    except Exception:  # noqa: BLE001
                        continue
            if need_yb:
                try:
                    box["yb"] = year_bases(json.loads(json.dumps(out["yb"])), budget=max(5, 50 - (time.time() - t0)))
                except Exception as e:  # noqa: BLE001
                    box["err"] = e
        th = threading.Thread(target=_job, daemon=True); th.start(); th.join(60)
        for cs, d in list(box["h"].items()):
            H.setdefault(cs, {}).update(d)
        seen.update(box["seen"])
        if need_yb:
            out["yb"]["try"] = int(time.time())
            if "yb" in box:
                box["yb"]["try"] = out["yb"]["try"]; out["yb"] = box["yb"]
            else:
                fail("world_yb", box.get("err") or TimeoutError("bases de début d'année : délai dépassé"))
    # variation de la dernière séance pour les places fermées : CNBC remet parfois la variation à zéro (« UNCH ») avant la
    # séance suivante ; on la recalcule alors contre la clôture de la séance précédente (historique quotidien ci-dessus).
    # L'historique ne garde que des jours ouvrés : la cotation d'un contrat relevée après 18 h (New York) appartient à la séance du
    # lendemain (celle du dimanche soir à la séance du lundi), et une date de samedi ou de dimanche n'est jamais écrite (l'or
    # affichait −0,95 % contre la cotation du dimanche soir au lieu de −0,50 % contre le règlement du vendredi). La clôture de
    # référence doit dater d'au plus 4 jours ouvrés avant la séance ; sinon la variation reste vide (jamais 0,00 % inventé).
    def wkday(x):
        try:
            return dt.date.fromisoformat(x).weekday() < 5
        except ValueError:
            return False

    def sess_d(k, t_):
        if k != "cmd":  # indices et changes : date de la cotation, jours ouvrés seulement
            d_ = t_[:10]
            return d_ if re.match(r"\d{4}-\d{2}-\d{2}$", d_) and wkday(d_) else None
        t = dt.datetime.fromisoformat(re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", t_)).astimezone(NY)
        day = t.date() + (dt.timedelta(days=1) if t.hour >= 18 else dt.timedelta(0))
        if day.weekday() == 5:
            return None
        return (day + dt.timedelta(days=1 if day.weekday() == 6 else 0)).isoformat()

    def bdays(a, b):  # jours ouvrés dans ]a ; b]
        a_, b_ = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
        return sum(1 for i in range(1, (b_ - a_).days + 1) if (a_ + dt.timedelta(days=i)).weekday() < 5)
    for k in ("idx", "cmd", "fx"):
        for r in out.get(k, []):
            try:
                cs, last = r["s"], r.get("last")
                d = sess_d(k, str(r.get("t") or "")) if r.get("t") else None
                if not last or not d:
                    continue
                h = H.setdefault(cs, {}); h[d] = last
                if (not r.get("chg")) or (r.get("prev") and abs(r["prev"] - last) < 1e-9):
                    r["chg"] = r["pct"] = None
                    older = sorted(x for x in h if x < d and wkday(x))
                    if older and h[older[-1]] and bdays(older[-1], d) <= 4:
                        pc = h[older[-1]]; r["prev"] = pc; r["chg"] = round(last - pc, 6); r["pct"] = round(last / pc - 1, 6); r["cs"] = older[-1]
                    else:
                        r["prev"] = None
            except Exception as e:  # noqa: BLE001
                fail("world_ref_" + str(r.get("s")), e)
    out["h"] = {cs: dict(sorted((x, y) for x, y in v.items() if wkday(x))[-12:]) for cs, v in H.items()}
    out["hs"] = seen; out["hst"] = int(time.time()) if need_seed else hst
    if out["idx"]:
        dump(out, os.path.join(out_data, "world_mkt.json"))
    return out


def us_batch(out_data):
    """Cours différés de tous les titres US du terminal (actions, ETF, indices) : Nasdaq, par paquets de 25 d'une même classe ;
    pré-marché et après-bourse des actions et ETF quand la séance étendue est ouverte."""
    summ = load("summary.json", folder=out_data) or {}
    prev_q = (load("quotes.json", folder=out_data) or {}).get("q") or {}
    want = []
    for x in summ.get("secs", []):
        if x.get("mkt") != "US":
            continue
        ac = "etf" if x.get("typ") == "ETF" else "index" if x.get("cls") == "Index" else "stocks"
        want.append((x["id"], NQ_SYM.get(x["id"], x["id"]), ac))
    q = {}
    for ac in ("stocks", "etf", "index"):
        part = [w for w in want if w[2] == ac]
        # (le service ne renvoie que 20 symboles par requête : paquets de 20 ; un symbole absent de la réponse est redemandé une
        # fois, puis signalé dans les erreurs du relevé au lieu de garder la veille en silence)
        for k in range(0, len(part), 20):
            chunk = part[k:k + 20]
            by = {sym.upper(): sid for sid, sym, _ in chunk}
            rows_ = _nq_rows(chunk)
            got_ = {str(r.get("symbol", "")).upper() for r in rows_}
            miss_ = [c for c in chunk if c[1].upper() not in got_]
            if miss_ and len(miss_) < len(chunk):
                time.sleep(0.3)
                rows_ = rows_ + _nq_rows(miss_)
                got_ |= {str(r.get("symbol", "")).upper() for r in rows_}
                left_ = [c[1] for c in miss_ if c[1].upper() not in got_]
                if left_:
                    fail("nasdaq_manquants", ", ".join(left_))
            for r in rows_:
                sid = by.get(str(r.get("symbol", "")).upper())
                last = money(r.get("lastSalePrice") or r.get("lastsale"))
                if not sid or not last:
                    continue
                pct = num(str(r.get("percentageChange") or "").replace("%", "").replace("+", ""))
                # (variation Nasdaq gardée à part : elle ne sert qu'à contrôler les références, voir us_check)
                rec = {"last": last, "pct": None, "_pnq": pct / 100 if pct is not None else None}
                m = re.search(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})(?: (\d{1,2}):(\d{2}) (AM|PM))?", str(r.get("lastTradeTimestamp") or ""))
                if m and m.group(1) in MONTHS_EN:
                    rec["d"] = f"{m.group(3)}-{MONTHS_EN[m.group(1)]:02d}-{int(m.group(2)):02d}"
                    if m.group(4):
                        rec["t"] = f"{int(m.group(4)) % 12 + (12 if m.group(6) == 'PM' else 0):02d}:{m.group(5)} ET"
                vol = num(str(r.get("volume") or "").replace(",", ""))
                if vol:
                    rec["vol"] = int(vol)
                for k2, f in (("prev", "previousClosePrice"), ("o", "openingPrice")):
                    v = r.get(f)
                    v = money(v) if isinstance(v, str) else v
                    if isinstance(v, (int, float)) and v > 0:
                        rec[k2] = round(float(v), 4)
                if r.get("marketStatus"):
                    rec["ms"] = str(r["marketStatus"])
                q[sid] = rec
            time.sleep(0.3)
    # séance étendue : relevée pendant le pré-marché (04:00-09:30 ET) et l'après-bourse (16:00-20:00 ET, +15 min de marge) ;
    # le dernier après-bourse est conservé la nuit et le week-end (comme sur le terminal), effacé à l'ouverture.
    now = dt.datetime.now(NY)
    sess = us_session(now)
    late_post = now.weekday() < 5 and (20, 0) <= (now.hour, now.minute) < (20, 15)
    kind = "pre" if sess == "PRE" else "post" if sess == "POST" or late_post else None
    if kind:
        from concurrent.futures import ThreadPoolExecutor
        todo = [(sid, sym, ac) for sid, sym, ac in want if ac in ("stocks", "etf") and sid in q]
        def one(w):
            try:
                return w[0], _nq_ext(w[1], w[2], kind)
            except Exception as e:  # noqa: BLE001
                return w[0], e
        nfail = 0
        with ThreadPoolExecutor(6) as ex:
            for sid, ext in ex.map(one, todo):
                if isinstance(ext, Exception):
                    nfail += 1
                    continue
                if not ext or not ext.get("last"):
                    continue
                q[sid]["ext"] = ext  # (variation de la séance étendue calculée par us_check, contre la bonne clôture)
        if nfail:
            ERRORS["nasdaq_ext"] = f"{nfail}/{len(todo)} séances étendues non lues"
        log("séance étendue", kind, sum(1 for v in q.values() if v.get("ext")), "titres")
    elif sess == "CLOSED":
        for sid, rec in q.items():
            old = (prev_q.get(sid) or {}).get("ext")
            if old and old.get("s") == "post":
                rec["ext"] = old
    # contrôle de chaque cours (référence de variation, cours aberrants, volume) ; une erreur ici ne bloque jamais le relevé :
    # la cotation est alors publiée sans variation plutôt qu'avec celle, non contrôlée, du service
    ee = load("ee.json", folder=out_data) or {}
    notes = []
    for sid in list(q):
        rec = q[sid]
        try:
            rng = None
            e_ = ee.get(sid) if isinstance(ee, dict) else None
            if isinstance(e_, dict) and e_.get("ts") and e_.get("ts") == rec.get("d"):
                hl = re.findall(r"\$?([\d,]+(?:\.\d+)?)", str((e_.get("sum") or {}).get("TodayHighLow") or ""))
                if len(hl) == 2 and money(hl[0]) and money(hl[1]):
                    rng = tuple(sorted((money(hl[0]), money(hl[1]))))
            ser = series_ref(out_data, sid, rec["d"]) if rec.get("d") else None
            r2 = us_check(sid, rec, prev_q.get(sid), ser, sess, rng, notes)
            if r2 is None:
                q.pop(sid)
        except Exception as e:  # noqa: BLE001
            rec.pop("_pnq", None)
            rec["pct"] = None
            if "rf" not in rec:
                rec.pop("prev", None)  # (clôture précédente non contrôlée : jamais publiée)
            for k_ in ("pc", "cl"):
                (rec.get("ext") or {}).pop(k_, None)
            fail("us_check_" + sid, e)
    if notes:
        ERRORS["us_ecartes"] = "; ".join(notes)[:300]
        log("cours écartés :", "; ".join(notes))
    fut_quotes(q, prev_q, out_data)
    for sid, prod in (("BTC", "BTC-USD"), ("ETH", "ETH-USD"), ("SOL", "SOL-USD")):
        try:
            t = json.loads(get(f"https://api.exchange.coinbase.com/products/{prod}/ticker", tries=2))
            st = json.loads(get(f"https://api.exchange.coinbase.com/products/{prod}/stats", tries=2))
            last, op = float(t["price"]), float(st["open"])
            q[sid] = {"last": last, "pct": round(last / op - 1, 6), "d": dt.datetime.now(dt.timezone.utc).date().isoformat(), "src": "coinbase 24h"}
        except Exception as e:  # noqa: BLE001
            fail("coinbase", e)
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["live", "eod"], default="live")
    ap.add_argument("--out", default=os.path.join(ROOT, "_site"))
    ap.add_argument("--state", default=DATA)
    a = ap.parse_args()
    st, out_data = a.state, os.path.join(a.out, "data")
    os.makedirs(st, exist_ok=True)
    os.makedirs(out_data, exist_ok=True)

    live, intraday = None, None
    try:
        live, intraday = live_quote()
        log("QQQ", live["price"], live["state"], live["day"])
    except Exception as e:  # noqa: BLE001
        fail("yahoo_live", e)
        try:
            live, intraday = nasdaq_live()
            log("QQQ (nasdaq)", live["price"], live["state"], live["day"])
        except Exception as e2:  # noqa: BLE001
            fail("nasdaq_live", e2)

    brvm = load("brvm.json", folder=st) or load("brvm.json")
    try:
        fresh = scrape_brvm(brvm)
        log("BRVM", len(fresh["rows"]), "rows", fresh["asof"])
        brvm = fresh
        dump(brvm, os.path.join(st, "brvm.json"))
        # (clôture du jour : seulement la base programmée du soir ; un passage complet lancé en journée archivait des cours de séance)
        if a.mode == "eod" and os.environ.get("FQT_CLOSE") == "1":
            archive_brvm(brvm)
            dump(brvm, os.path.join(DATA, "brvm.json"))
    except Exception as e:  # noqa: BLE001
        fail("brvm", e)

    q = {}
    if live:
        q["QQQ"] = {"last": live["price"], "pct": live["chg"], "d": live["day"], "o": live["open"], "h": live["dayHigh"], "l": live["dayLow"], "vol": live["vol"] or None}
    if brvm:
        for r in brvm.get("rows", []):
            q[r["t"]] = {"last": r["c"], "pct": round(r["vj"] / 100, 6), "d": brvm["asof"], "o": r.get("o"), "vol": r.get("vol"), "val": int((r.get("vol") or 0) * r["c"])}
        for x in brvm.get("idx", []) + brvm.get("sect", []):
            code = IDX_CODE.get(x.get("k"))
            if code and x.get("v"):
                q[code] = {"last": x["v"], "pct": round((x.get("vj") or 0) / 100, 6), "d": brvm["asof"]}
    usq = {}
    try:
        usq = us_batch(out_data)
        for sid, rec in usq.items():
            if sid not in q:
                q[sid] = rec
    except Exception as e:  # noqa: BLE001
        fail("us_batch", e)
    # QQQ (Yahoo) : clôture précédente confirmée par le contrôle Nasdaq quand elle porte sur la même séance ; volume du jour =
    # volume quotidien (Yahoo, sinon Nasdaq), jamais la somme des barres de 5 minutes (490,8 M au lieu d'environ 46 M), et
    # seulement s'il est vraisemblable
    try:
        if "QQQ" in q:
            qq, nq = q["QQQ"], usq.get("QQQ") or {}
            if nq.get("rf") and nq.get("prev") and nq.get("d") == qq.get("d"):
                qq["prev"], qq["pct"] = nq["prev"], round(qq["last"] / nq["prev"] - 1, 6)
            v_ = qq.get("vol") or (nq.get("vol") if nq.get("d") == qq.get("d") else None)
            ser = series_ref(out_data, "QQQ", qq["d"]) if qq.get("d") else None
            qq["vol"] = v_ if v_ and (ser is None or vol_ok(ser.get("vh"), v_)) else None
            if live:
                live["vol"] = qq["vol"]
    except Exception as e:  # noqa: BLE001
        fail("qqq_ref", e)
    now = int(time.time())
    try:
        oil_board(out_data)
    except Exception as e:  # noqa: BLE001
        fail("cnbc_oil", e)
    wb = None
    try:
        wb = world_board(out_data)
    except Exception as e:  # noqa: BLE001
        fail("world_board", e)
    # changes du jour pour les séries EURUSD, USDXOF (parité fixe 655,957 FCFA pour 1 euro) et USDTWD
    fxr = {r["s"]: r for r in ((wb or {}).get("fx") or [])}
    eu, tw = fxr.get("EUR="), fxr.get("TWD=")
    # (clôture précédente prise seulement si la variation est sûre : après une remise à zéro de CNBC, prev = last donnait 0,00 % ;
    # une cotation datée d'un samedi ou d'un dimanche n'est pas publiée : jamais de séance de week-end greffée sur les séries)
    def wkend(x):
        try:
            return dt.date.fromisoformat(x).weekday() >= 5
        except ValueError:
            return False
    try:
        if eu and eu.get("last") and not wkend(str(eu.get("t") or "")[:10]):
            d_ = str(eu.get("t") or "")[:10] or dt.date.today().isoformat()
            pe = (eu.get("prev") or eu["last"] / (1 + eu["pct"])) if eu.get("pct") is not None and eu["pct"] > -1 else None
            q["EURUSD"] = {"last": round(eu["last"], 5), "pct": round(eu["last"] / pe - 1, 6) if pe else None, "prev": round(pe, 5) if pe else None, "d": d_, "src": "CNBC"}
            q["USDXOF"] = {"last": round(655.957 / eu["last"], 3), "pct": round(pe / eu["last"] - 1, 6) if pe else None, "prev": round(655.957 / pe, 3) if pe else None, "d": d_, "src": "parité"}
        if tw and tw.get("last") and not wkend(str(tw.get("t") or "")[:10]):
            pt = tw.get("prev") if tw.get("pct") is not None else None
            q["USDTWD"] = {"last": tw["last"], "pct": round(tw["last"] / pt - 1, 6) if pt else None, "prev": pt, "d": str(tw.get("t") or "")[:10] or dt.date.today().isoformat(), "src": "CNBC"}
    except Exception as e:  # noqa: BLE001
        fail("fx_quotes", e)
    dump({"ts": now, "qqq": live, "intraday": intraday, "errors": ERRORS}, os.path.join(out_data, "live.json"))
    dump({"ts": now, "asof": brvm.get("asof") if brvm else None, "q": q}, os.path.join(out_data, "quotes.json"))
    if brvm:
        dump(brvm, os.path.join(out_data, "session.json"))
    log("feed written:", len(q), "quotes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
