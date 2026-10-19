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
        "vol": int(sum(b[5] for b in today)), "time": int(meta.get("regularMarketTime") or bars[-1][0]),
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
    have = set()
    if os.path.exists(path):
        with open(path, encoding="utf8") as f:
            have = {line.split(",", 1)[0] for line in f}
    if b["asof"] in have:
        return
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf8") as f:
        if new:
            f.write("date,ticker,close,var_pct,volume,prev\n")
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
    rf = re.search(r"Close:\s*\$?([\d,.]+)", str(d.get("previousInfo") or ""))
    return {"s": kind, "last": last, "d": when, "t": t, "vol": int(vol) if vol else None, "ref": money(rf.group(1)) if rf else None,
            "hi": money(hi.group(1)) if hi else None, "lo": money(lo.group(1)) if lo else None}


# contrats à terme 1er mois (différé ~10 min) : les cours d'Investing, TradingView, Bloomberg (CO1, CL1, NG1, GC1)
FUTS = (("BRENT", "@LCO.1"), ("WTI", "@CL.1"), ("NATGAS", "@NG.1"), ("GOLD", "@GC.1"))


def _fnum(x):
    try:
        return float(str(x).replace(",", "").replace("%", "").replace("+", ""))
    except (TypeError, ValueError):
        return None


def fut_quotes(q):
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
            q[sid] = {"last": last, "prev": prev, "pct": round(last / prev - 1, 6) if prev else None, "d": day.isoformat(),
                      "o": _fnum(r.get("open")), "h": _fnum(r.get("high")), "l": _fnum(r.get("low")), "vol": int(_fnum(r.get("volume")) or 0),
                      "src": "CNBC", "ct": r.get("name"), "exp": r.get("expiration_date")}
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
    def rec(r):
        return {"n": r.get("name"), "last": _fnum(r.get("last")), "chg": _fnum(r.get("change")), "pct": (_fnum(r.get("change_pct")) or 0) / 100 if r.get("change_pct") else None,
                "prev": _fnum(r.get("previous_day_closing")), "exp": r.get("expiration_date"), "t": r.get("last_time"), "ccy": r.get("currencyCode"),
                "hi52": _fnum(r.get("yrhiprice")), "lo52": _fnum(r.get("yrloprice"))}
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
                "pct": (_fnum(r.get("change_pct")) or 0) / 100 if r.get("change_pct") not in (None, "UNCH") else 0.0, "prev": _fnum(r.get("previous_day_closing")),
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
    for k in ("idx", "cmd", "fx"):
        for r in out.get(k, []):
            cs, last, d = r["s"], r.get("last"), str(r.get("t") or "")[:10]
            if not last or not re.match(r"\d{4}-\d{2}-\d{2}$", d):
                continue
            h = H.setdefault(cs, {}); h[d] = last
            if (not r.get("chg")) or (r.get("prev") and abs(r["prev"] - last) < 1e-9):
                older = sorted(x for x in h if x < d)
                if older and h[older[-1]]:
                    pc = h[older[-1]]; r["prev"] = pc; r["chg"] = round(last - pc, 6); r["pct"] = round(last / pc - 1, 6); r["cs"] = older[-1]
    out["h"] = {cs: dict(sorted(v.items())[-12:]) for cs, v in H.items()}
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
                rec = {"last": last, "pct": round(pct / 100, 6) if pct is not None else None}
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
                rec = q[sid]
                ref = ext.pop("ref", None) or (rec.get("prev") if kind == "pre" else rec.get("last"))
                if ref:
                    ext["chg"] = round(ext["last"] - ref, 4)
                    ext["pct"] = round(ext["last"] / ref - 1, 6)
                rec["ext"] = ext
        if nfail:
            ERRORS["nasdaq_ext"] = f"{nfail}/{len(todo)} séances étendues non lues"
        log("séance étendue", kind, sum(1 for v in q.values() if v.get("ext")), "titres")
    elif sess == "CLOSED":
        for sid, rec in q.items():
            old = (prev_q.get(sid) or {}).get("ext")
            if old and old.get("s") == "post":
                rec["ext"] = old
    fut_quotes(q)
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
        if a.mode == "eod":
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
    try:
        for sid, rec in us_batch(out_data).items():
            if sid not in q:
                q[sid] = rec
    except Exception as e:  # noqa: BLE001
        fail("us_batch", e)
    now = int(time.time())
    oil_board(out_data)
    wb = None
    try:
        wb = world_board(out_data)
    except Exception as e:  # noqa: BLE001
        fail("world_board", e)
    # changes du jour pour les séries EURUSD, USDXOF (parité fixe 655,957 FCFA pour 1 euro) et USDTWD
    fxr = {r["s"]: r for r in ((wb or {}).get("fx") or [])}
    eu, tw = fxr.get("EUR="), fxr.get("TWD=")
    if eu and eu.get("last"):
        d_ = str(eu.get("t") or "")[:10] or dt.date.today().isoformat()
        pe = eu.get("prev") or (eu["last"] / (1 + eu["pct"]) if eu.get("pct") is not None else None)
        q["EURUSD"] = {"last": round(eu["last"], 5), "pct": round(eu["last"] / pe - 1, 6) if pe else None, "prev": round(pe, 5) if pe else None, "d": d_, "src": "CNBC"}
        q["USDXOF"] = {"last": round(655.957 / eu["last"], 3), "pct": round(pe / eu["last"] - 1, 6) if pe else None, "prev": round(655.957 / pe, 3) if pe else None, "d": d_, "src": "parité"}
    if tw and tw.get("last"):
        pt = tw.get("prev")
        q["USDTWD"] = {"last": tw["last"], "pct": round(tw["last"] / pt - 1, 6) if pt else None, "prev": pt, "d": str(tw.get("t") or "")[:10] or dt.date.today().isoformat(), "src": "CNBC"}
    dump({"ts": now, "qqq": live, "intraday": intraday, "errors": ERRORS}, os.path.join(out_data, "live.json"))
    dump({"ts": now, "asof": brvm.get("asof") if brvm else None, "q": q}, os.path.join(out_data, "quotes.json"))
    if brvm:
        dump(brvm, os.path.join(out_data, "session.json"))
    log("feed written:", len(q), "quotes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
