#!/usr/bin/env python3
"""Sources complémentaires du terminal FQT, relevées depuis GitHub Actions (bibliothèque standard).

  FRED (Réserve fédérale de St. Louis)  taux, crédit, liquidité, emploi, inflation, activité, stress
  Nasdaq                               ETF (secteurs, facteurs, pays, obligations, matières), indices, Nasdaq-100
  CBOE                                 VIX, VIX9D, VIX3M, VVIX, SKEW
  CNN                                  Fear & Greed officiel et ses 7 composantes
  Coinbase                             BTC, ETH, SOL (quotidien)
  Banque mondiale                      indicateurs des 8 pays de l'UEMOA
  SEC EDGAR (XBRL companyfacts)        comptes trimestriels et annuels des actions US -> flux de trésorerie, ratios

Chaque source est indépendante : une panne n'empêche pas les autres. report.json liste les erreurs.
Le dossier --out (branche quant-raw restaurée) sert aussi de base : on ne relit que les dernières
semaines d'une série déjà présente, sauf si un ajustement (split) est détecté. Un échec laisse l'ancien fichier.

Usage : fetch_extra.py --out RAW_DIR [--only nasdaq,fred,cboe,cnn,crypto,wb,sec,analyst,boc,probe] [--news FILE]
"""
import argparse, collections, csv, datetime as dt, gzip, html as HTML, io, json, math, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_terminal import US  # noqa: E402  (univers US déjà suivi)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
SEC_UA = os.environ.get("SEC_UA") or "Mozilla/5.0 (compatible; FQT-Terminal/1.0; personal market research)"
RESEARCH_UA = "FQT-Terminal research ghosht-elphantomo@users.noreply.github.com"  # certains sites (FRED, MarketScreener) refusent les UA de navigateur depuis le cloud
NQ_H = {"Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/", "Accept": "application/json, text/plain, */*"}
TODAY = dt.date.today()
REPORT = {}

# ---------------------------------------------------------------- univers
ETFS = [  # symbole, nom, groupe
    ("SPY", "SPDR S&P 500", "ETF actions US"), ("DIA", "SPDR Dow Jones Industrial", "ETF actions US"), ("IWM", "iShares Russell 2000", "ETF actions US"),
    ("MDY", "SPDR S&P MidCap 400", "ETF actions US"), ("RSP", "Invesco S&P 500 équipondéré", "ETF actions US"),
    ("MTUM", "iShares MSCI USA Momentum", "ETF facteurs"), ("QUAL", "iShares MSCI USA Quality", "ETF facteurs"), ("USMV", "iShares MSCI USA Min Vol", "ETF facteurs"),
    ("VLUE", "iShares MSCI USA Value", "ETF facteurs"), ("SIZE", "iShares MSCI USA Size", "ETF facteurs"), ("SPHB", "Invesco S&P 500 High Beta", "ETF facteurs"),
    ("SPLV", "Invesco S&P 500 Low Volatility", "ETF facteurs"), ("VIG", "Vanguard Dividend Appreciation", "ETF facteurs"),
    ("XLK", "Technologie (SPDR)", "ETF secteurs US"), ("XLF", "Finance (SPDR)", "ETF secteurs US"), ("XLE", "Énergie (SPDR)", "ETF secteurs US"),
    ("XLV", "Santé (SPDR)", "ETF secteurs US"), ("XLY", "Conso. discrétionnaire (SPDR)", "ETF secteurs US"), ("XLP", "Conso. de base (SPDR)", "ETF secteurs US"),
    ("XLI", "Industrie (SPDR)", "ETF secteurs US"), ("XLB", "Matériaux (SPDR)", "ETF secteurs US"), ("XLU", "Services publics (SPDR)", "ETF secteurs US"),
    ("XLRE", "Immobilier (SPDR)", "ETF secteurs US"), ("XLC", "Communication (SPDR)", "ETF secteurs US"),
    ("SMH", "VanEck Semi-conducteurs", "ETF thématiques"), ("IGV", "iShares Logiciel", "ETF thématiques"), ("XBI", "SPDR Biotech", "ETF thématiques"),
    ("ITA", "iShares Aéronautique & défense", "ETF thématiques"), ("ARKK", "ARK Innovation", "ETF thématiques"), ("KWEB", "KraneShares Internet chinois", "ETF thématiques"),
    ("TQQQ", "ProShares UltraPro QQQ (3x)", "ETF à levier"), ("SQQQ", "ProShares UltraPro Short QQQ (-3x)", "ETF à levier"),
    ("QLD", "ProShares Ultra QQQ (2x)", "ETF à levier"), ("SOXL", "Direxion Semi-conducteurs (3x)", "ETF à levier"), ("SSO", "ProShares Ultra S&P 500 (2x)", "ETF à levier"),
    ("EFA", "iShares MSCI EAFE (pays développés)", "ETF pays"), ("EEM", "iShares MSCI Émergents", "ETF pays"), ("EWJ", "iShares MSCI Japon", "ETF pays"),
    ("EWG", "iShares MSCI Allemagne", "ETF pays"), ("EWU", "iShares MSCI Royaume-Uni", "ETF pays"), ("EWQ", "iShares MSCI France", "ETF pays"),
    ("FXI", "iShares China Large-Cap", "ETF pays"), ("INDA", "iShares MSCI Inde", "ETF pays"), ("EWZ", "iShares MSCI Brésil", "ETF pays"),
    ("EWT", "iShares MSCI Taïwan", "ETF pays"), ("EZA", "iShares MSCI Afrique du Sud", "ETF pays"), ("AFK", "VanEck Afrique", "ETF pays"),
    ("NGE", "Global X MSCI Nigeria", "ETF pays"),
    ("SHY", "iShares Trésor US 1-3 ans", "ETF obligations"), ("IEF", "iShares Trésor US 7-10 ans", "ETF obligations"), ("TLT", "iShares Trésor US 20 ans+", "ETF obligations"),
    ("TIP", "iShares obligations indexées (TIPS)", "ETF obligations"), ("LQD", "iShares crédit catégorie investissement", "ETF obligations"),
    ("HYG", "iShares haut rendement", "ETF obligations"), ("EMB", "iShares dette émergente USD", "ETF obligations"), ("AGG", "iShares obligations US agrégées", "ETF obligations"),
    ("GLD", "SPDR Gold Shares (or)", "ETF matières"), ("SLV", "iShares Silver (argent)", "ETF matières"), ("GDX", "VanEck mines d'or", "ETF matières"),
    ("USO", "United States Oil Fund", "ETF matières"), ("UNG", "United States Natural Gas", "ETF matières"), ("DBC", "Invesco matières premières", "ETF matières"),
    ("DBA", "Invesco agriculture", "ETF matières"), ("CPER", "United States Copper", "ETF matières"),
    ("UUP", "Invesco dollar US haussier", "ETF devises"), ("FXE", "Invesco euro", "ETF devises"), ("FXY", "Invesco yen", "ETF devises"),
    ("VNQ", "Vanguard immobilier coté (REIT)", "ETF immobilier"), ("IBIT", "iShares Bitcoin Trust", "ETF crypto"),
]
INDICES = [("SPX", "SPX", "S&P 500"), ("NDX", "NDX", "Nasdaq-100"), ("COMP", "CCMP", "Nasdaq Composite"), ("RUT", "RTY", "Russell 2000")]
FRED = [  # id, nom, groupe, unité
    ("DGS1MO", "Trésor US 1 mois", "Taux", "%"), ("DGS3MO", "Trésor US 3 mois", "Taux", "%"), ("DGS6MO", "Trésor US 6 mois", "Taux", "%"),
    ("DGS1", "Trésor US 1 an", "Taux", "%"), ("DGS2", "Trésor US 2 ans", "Taux", "%"), ("DGS3", "Trésor US 3 ans", "Taux", "%"),
    ("DGS5", "Trésor US 5 ans", "Taux", "%"), ("DGS7", "Trésor US 7 ans", "Taux", "%"), ("DGS10", "Trésor US 10 ans", "Taux", "%"),
    ("DGS20", "Trésor US 20 ans", "Taux", "%"), ("DGS30", "Trésor US 30 ans", "Taux", "%"), ("DFF", "Taux des Fed funds effectif", "Taux", "%"),
    ("T10Y2Y", "Pente 10 ans - 2 ans", "Taux", "pts"), ("T10Y3M", "Pente 10 ans - 3 mois", "Taux", "pts"),
    ("DFII10", "Taux réel 10 ans (TIPS)", "Taux", "%"), ("T10YIE", "Inflation anticipée 10 ans (point mort)", "Inflation", "%"),
    ("T5YIFR", "Inflation anticipée 5 ans dans 5 ans", "Inflation", "%"), ("MORTGAGE30US", "Taux immobilier 30 ans", "Taux", "%"),
    ("BAMLH0A0HYM2", "Écart haut rendement (OAS)", "Crédit", "%"), ("BAMLC0A0CM", "Écart catégorie investissement (OAS)", "Crédit", "%"),
    ("BAMLH0A3HYC", "Écart CCC et moins (OAS)", "Crédit", "%"), ("BAA10Y", "Écart Moody's Baa - 10 ans", "Crédit", "%"), ("AAA10Y", "Écart Moody's Aaa - 10 ans", "Crédit", "%"),
    ("WALCL", "Bilan de la Fed", "Liquidité", "M$"), ("WTREGEN", "Compte du Trésor à la Fed (TGA)", "Liquidité", "Md$"),
    ("RRPONTSYD", "Prises en pension inversées (RRP)", "Liquidité", "Md$"), ("M2SL", "Masse monétaire M2", "Liquidité", "Md$"),
    ("STLFSI4", "Indice de stress financier (St. Louis)", "Stress", "idx"), ("NFCI", "Conditions financières (Chicago)", "Stress", "idx"),
    ("VIXCLS", "VIX", "Stress", "pts"), ("VXNCLS", "VXN (volatilité Nasdaq-100)", "Stress", "pts"), ("OVXCLS", "OVX (volatilité du pétrole)", "Stress", "pts"),
    ("GVZCLS", "GVZ (volatilité de l'or)", "Stress", "pts"), ("DTWEXBGS", "Dollar US pondéré (large)", "Change", "idx"),
    ("UNRATE", "Taux de chômage", "Emploi", "%"), ("ICSA", "Inscriptions hebdo. au chômage", "Emploi", "k"), ("PAYEMS", "Emplois non agricoles", "Emploi", "k"),
    ("SAHMREALTIME", "Règle de Sahm (temps réel)", "Emploi", "pts"), ("JTSJOL", "Offres d'emploi (JOLTS)", "Emploi", "k"),
    ("CPIAUCSL", "Prix à la consommation (CPI)", "Inflation", "idx"), ("CPILFESL", "CPI hors alimentation et énergie", "Inflation", "idx"),
    ("PCEPILFE", "PCE sous-jacent", "Inflation", "idx"), ("PPIACO", "Prix à la production", "Inflation", "idx"),
    ("GDPC1", "PIB réel", "Activité", "Md$"), ("INDPRO", "Production industrielle", "Activité", "idx"), ("RSAFS", "Ventes au détail", "Activité", "M$"),
    ("HOUST", "Mises en chantier", "Activité", "k"), ("UMCSENT", "Confiance des ménages (Michigan)", "Activité", "idx"),
    ("CSUSHPINSA", "Prix des logements Case-Shiller", "Activité", "idx"), ("USREC", "Récession (NBER)", "Activité", "0/1"),
    ("RECPROUSM156N", "Probabilité de récession (lissée)", "Activité", "%"),
    ("SP500", "S&P 500", "Marchés", "pts"), ("NASDAQCOM", "Nasdaq Composite (depuis 1971)", "Marchés", "pts"),
    ("DCOILWTICO", "Pétrole WTI", "Marchés", "$"), ("DEXUSEU", "Dollar par euro", "Change", "$"),
    # marché monétaire (écran BTMM)
    ("DFEDTARU", "Fed : borne haute de la fourchette cible", "Monétaire", "%"), ("DFEDTARL", "Fed : borne basse de la fourchette cible", "Monétaire", "%"),
    ("IORB", "Rémunération des réserves (IORB)", "Monétaire", "%"), ("DPCREDIT", "Taux d'escompte (crédit primaire)", "Monétaire", "%"),
    ("DPRIME", "Taux de base bancaire (prime rate)", "Monétaire", "%"), ("SOFR", "SOFR (pension au jour le jour garantie)", "Monétaire", "%"),
    ("OBFR", "Taux de financement au jour le jour (OBFR)", "Monétaire", "%"), ("DTB4WK", "Bon du Trésor 4 semaines (escompte)", "Monétaire", "%"),
    ("DTB3", "Bon du Trésor 13 semaines (escompte)", "Monétaire", "%"), ("DTB6", "Bon du Trésor 26 semaines (escompte)", "Monétaire", "%"),
    ("DTB1YR", "Bon du Trésor 52 semaines (escompte)", "Monétaire", "%"), ("DCPF3M", "Billets de trésorerie financiers AA 3 mois", "Monétaire", "%"),
    ("DCPN3M", "Billets de trésorerie non financiers AA 3 mois", "Monétaire", "%"), ("ECBDFR", "BCE : taux de la facilité de dépôt", "Monétaire", "%"),
    ("ECBMRRFR", "BCE : taux des opérations principales de refinancement", "Monétaire", "%"),
]
CBOE = ["VIX", "VIX9D", "VIX3M", "VVIX", "SKEW"]
CRYPTO = [("BTC", "BTC-USD", "2015-07-20"), ("ETH", "ETH-USD", "2016-05-18"), ("SOL", "SOL-USD", "2021-06-01")]
UEMOA = ["BEN", "BFA", "CIV", "GNB", "MLI", "NER", "SEN", "TGO", "SSF", "WLD"]
WB = [  # indicateur, nom, unité
    ("NY.GDP.MKTP.KD.ZG", "Croissance du PIB réel", "%"), ("FP.CPI.TOTL.ZG", "Inflation (prix à la consommation)", "%"),
    ("NY.GDP.MKTP.CD", "PIB (dollars courants)", "$"), ("NY.GDP.PCAP.CD", "PIB par habitant", "$"), ("NY.GDP.PCAP.PP.CD", "PIB par habitant (PPA)", "$"),
    ("SP.POP.TOTL", "Population", "hab."), ("SP.POP.GROW", "Croissance démographique", "%"), ("SP.URB.TOTL.IN.ZS", "Population urbaine", "%"),
    ("GC.DOD.TOTL.GD.ZS", "Dette de l'État central", "% PIB"), ("BN.CAB.XOKA.GD.ZS", "Solde courant", "% PIB"),
    ("BX.KLT.DINV.WD.GD.ZS", "Investissements directs étrangers (entrées)", "% PIB"), ("BX.TRF.PWKR.DT.GD.ZS", "Envois de fonds des migrants", "% PIB"),
    ("NE.EXP.GNFS.ZS", "Exportations", "% PIB"), ("NE.IMP.GNFS.ZS", "Importations", "% PIB"), ("NE.GDI.TOTL.ZS", "Investissement (FBCF + stocks)", "% PIB"),
    ("GC.REV.XGRT.GD.ZS", "Recettes publiques hors dons", "% PIB"), ("FS.AST.PRVT.GD.ZS", "Crédit au secteur privé", "% PIB"),
    ("FM.LBL.BMNY.ZG", "Croissance de la masse monétaire", "%"), ("FR.INR.LEND", "Taux débiteur", "%"),
    ("IT.CEL.SETS.P2", "Abonnements mobiles", "/100 hab."), ("IT.NET.USER.ZS", "Utilisateurs d'internet", "%"), ("EG.ELC.ACCS.ZS", "Accès à l'électricité", "%"),
    ("SL.UEM.TOTL.ZS", "Chômage (OIT)", "%"), ("SI.POV.DDAY", "Pauvreté (2,15 $/jour)", "%"), ("SP.DYN.LE00.IN", "Espérance de vie", "ans"),
    ("NV.AGR.TOTL.ZS", "Agriculture", "% PIB"), ("NV.IND.TOTL.ZS", "Industrie", "% PIB"), ("NV.SRV.TOTL.ZS", "Services", "% PIB"),
]


# ---------------------------------------------------------------- outils
HZ_MIRROR = os.environ.get("FQT_BRVM_MIRROR", "/tmp/raw/brvm_src")


def harzat_json(name):
    """Fichier de la base BRVM publique (harzat) ; à défaut, copie miroir gardée sur la branche raw."""
    try:
        return json.loads(get("https://raw.githubusercontent.com/harzat/brvm-data-public/main/" + name, timeout=60, tries=2))
    except Exception:  # noqa: BLE001
        p_ = os.path.join(HZ_MIRROR, name)
        if os.path.exists(p_):
            log("base BRVM externe injoignable, miroir utilisé :", name)
            return json.load(open(p_, encoding="utf8"))
        raise


def log(*a):
    print("[extra]", *a, flush=True)


def note(src, ok=True, err=None):
    r = REPORT.setdefault(src, {"ok": 0, "err": 0, "errors": []})
    if ok:
        r["ok"] += 1
    else:
        r["err"] += 1
        if len(r["errors"]) < 12:
            r["errors"].append(str(err)[:200])


def get(url, headers=None, tries=3, timeout=60, pause=2.0, ua=None):
    err = None
    for k in range(tries):
        try:
            h = {"User-Agent": ua or UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip"}
            h.update(headers or {})
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b":
                    b = gzip.decompress(b)
                return b
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 403, 404):
                break
            time.sleep(pause * (1 + 2 * k))
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(pause * (1 + 2 * k))
    raise err


def curl(url, timeout=40, ua=None):
    """Téléchargement par curl (certains sites filtrent l'empreinte TLS de Python)."""
    import subprocess
    r = subprocess.run(["curl", "-sSL", "--compressed", "-m", str(timeout), "-A", ua or RESEARCH_UA, "-w", "\n%{http_code}", url], capture_output=True, timeout=timeout + 10)
    body, _, code = r.stdout.rpartition(b"\n")
    if code.strip() != b"200":
        raise urllib.error.HTTPError(url, int(code.strip() or 0), "curl", None, None)
    return body


_WB_LAST = [0.0]


def get_wb(url):
    """web.archive.org : une requête toutes les 5 s, pause longue si le site demande de ralentir (429)."""
    for k in range(3):
        wait = 5 - (time.time() - _WB_LAST[0])
        if wait > 0:
            time.sleep(wait)
        _WB_LAST[0] = time.time()
        try:
            return get(url, tries=1, timeout=60, ua=RESEARCH_UA)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(40 * (k + 1))
    raise urllib.error.HTTPError(url, 429, "Too Many Requests", None, None)


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8") as f:
        json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)


def i2d(i):
    return dt.date(i // 10000, i // 100 % 100, i % 100)


def d2i(d):
    return d.year * 10000 + d.month * 100 + d.day


def prev_series(prev, sid, sub="nasdaq"):
    if not prev:
        return None
    p = os.path.join(prev, sub, sid + ".json")
    try:
        with open(p, encoding="utf8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return None


def find_rows(obj):
    """Premier tableau 'rows' trouvé dans une réponse JSON Nasdaq (la structure varie selon les points d'accès)."""
    if isinstance(obj, dict):
        if isinstance(obj.get("rows"), list):
            return obj["rows"]
        for v in obj.values():
            r = find_rows(v)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_rows(v)
            if r is not None:
                return r
    return None


def money(x):
    if x in (None, "", "N/A", "--"):
        return None
    try:
        return float(str(x).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


# ---------------------------------------------------------------- Nasdaq
def nasdaq_hist(sym, assetclass, start):
    url = (f"https://api.nasdaq.com/api/quote/{urllib.parse.quote(sym)}/historical?assetclass={assetclass}"
           f"&fromdate={start.isoformat()}&limit=9999&todate={TODAY.isoformat()}")
    j = json.loads(get(url, headers=NQ_H, timeout=60))
    rows = find_rows(j.get("data") or {}) or []
    out = {}
    for r in rows:
        try:
            m, d, y = r["date"].split("/")
            k = int(y) * 10000 + int(m) * 100 + int(d)
        except Exception:  # noqa: BLE001
            continue
        c = money(r.get("close"))
        if not c:
            continue
        o, h, l = money(r.get("open")) or c, money(r.get("high")) or c, money(r.get("low")) or c
        v = money(r.get("volume")) or 0
        out[k] = (k, o, max(h, o, c), min(l, o, c), c, int(v))
    return [out[k] for k in sorted(out)]


def nasdaq_series(sid, sym, assetclass, prev):
    """Historique quotidien : 10 ans au premier passage, puis les 3 dernières semaines recollées sur la série publiée."""
    old = prev_series(prev, sid)
    full_start = dt.date(TODAY.year - 11, 1, 1)
    rows = None
    if old and old.get("d") and (TODAY - i2d(old["d"][-1])).days < 40 and len(old["d"]) > 300:
        start = i2d(old["d"][-1]) - dt.timedelta(days=21)
        new = nasdaq_hist(sym, assetclass, start)
        if new:
            od = dict(zip(old["d"], old["c"]))
            overlap = [(od[r[0]], r[4]) for r in new if r[0] in od]
            if overlap and all(abs(n / o - 1) < 0.004 for o, n in overlap if o):
                first = new[0][0]
                keep = [i for i, d in enumerate(old["d"]) if d < first]
                g = lambda k: old.get(k) or old["c"]  # noqa: E731
                rows = [(old["d"][i], g("o")[i], g("h")[i], g("l")[i], old["c"][i], (old.get("v") or [0] * len(old["d"]))[i]) for i in keep] + new
            else:
                log(sid, "ajustement détecté, relecture complète")
    if rows is None:
        rows = nasdaq_hist(sym, assetclass, full_start)
    if len(rows) < 30:
        raise ValueError(f"{sym}: {len(rows)} lignes")
    return {"d": [r[0] for r in rows], "o": [r[1] for r in rows], "h": [r[2] for r in rows], "l": [r[3] for r in rows],
            "c": [r[4] for r in rows], "v": [r[5] for r in rows]}


def run_nasdaq(out, prev):
    meta = {"etf": [], "idx": [], "ndx": [], "screener": {}}
    # Composition du Nasdaq-100 et secteurs (screener complet)
    ndx = []
    try:
        j = json.loads(get("https://api.nasdaq.com/api/quote/list-type/nasdaq100", headers=NQ_H))
        for r in find_rows(j.get("data") or {}) or []:
            s = (r.get("symbol") or "").strip().upper()
            if s:
                ndx.append({"s": s, "n": r.get("companyName") or r.get("name"), "mcap": money(r.get("marketCap"))})
        note("nasdaq-ndx", ok=bool(ndx), err=None if ndx else "liste vide")
    except Exception as e:  # noqa: BLE001
        note("nasdaq-ndx", False, e)
    try:
        j = json.loads(get("https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true", headers=NQ_H, timeout=90))
        want = {x["s"] for x in ndx} | {s for s, *_ in US}
        for r in find_rows(j.get("data") or {}) or []:
            s = (r.get("symbol") or "").strip().upper()
            if s in want:
                meta["screener"][s] = {"n": r.get("name"), "sector": r.get("sector"), "ind": r.get("industry"), "cty": r.get("country"),
                                       "mcap": money(r.get("marketCap")), "ipo": r.get("ipoyear")}
        note("nasdaq-screener", ok=bool(meta["screener"]), err=None if meta["screener"] else "vide")
    except Exception as e:  # noqa: BLE001
        note("nasdaq-screener", False, e)
    if not ndx and prev and os.path.exists(os.path.join(prev, "nasdaq_meta.json")):
        ndx = json.load(open(os.path.join(prev, "nasdaq_meta.json"), encoding="utf8")).get("ndx", [])
        log("composition Nasdaq-100 reprise du site précédent", len(ndx))
    meta["ndx"] = ndx
    if not meta["screener"] and prev and os.path.exists(os.path.join(prev, "nasdaq_meta.json")):
        meta["screener"] = json.load(open(os.path.join(prev, "nasdaq_meta.json"), encoding="utf8")).get("screener", {})
    already = {s for s, *_ in US}
    jobs = [(s, s, "etf", "etf", n, g) for s, n, g in ETFS if s not in already]
    jobs += [(sid, sym, "index", "idx", n, "Indices US") for sym, sid, n in INDICES]
    jobs += [(x["s"], x["s"], "stocks", "ndx", x["n"], None) for x in ndx if x["s"] not in already]

    def one(job):
        sid, sym, ac, kind, name, grp = job
        try:
            ser = nasdaq_series(sid, sym, ac, prev)
            save(os.path.join(out, "nasdaq", sid + ".json"), ser)
            note("nasdaq-" + kind)
            return kind, {"id": sid, "sym": sym, "n": name, "g": grp, "rows": len(ser["d"])}
        except Exception as e:  # noqa: BLE001
            note("nasdaq-" + kind, False, f"{sym}: {e}")
            return kind, None
        finally:
            time.sleep(0.25)
    with ThreadPoolExecutor(4) as ex:
        for kind, r in ex.map(one, jobs):
            if r and kind in ("etf", "idx"):
                meta[kind].append(r)
    save(os.path.join(out, "nasdaq_meta.json"), meta)


# ---------------------------------------------------------------- calendrier des réunions du FOMC (Réserve fédérale)
FOMC_MO = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def fomc_parse(h):
    """Page des calendriers du FOMC -> dates de décision (2e jour) des réunions programmées, années par années."""
    t = HTML.unescape(re.sub(r"<[^>]+>", "\n", h))
    lines = [x.strip() for x in t.splitlines() if x.strip()]
    out, year = set(), None
    for i, x in enumerate(lines):
        m = re.match(r"^(\d{4}) FOMC Meetings$", x, re.I)
        if m:
            year = int(m.group(1))
            continue
        mm = re.match(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?(?:/(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?)?$", x, re.I)
        if not year or not mm or i + 1 >= len(lines):
            continue
        dm = re.match(r"^(\d{1,2})(?:\s*-\s*(\d{1,2}))?\s*\*?\s*(.*)$", lines[i + 1])
        if not dm or re.search(r"unscheduled|notation|conference call|cancel", dm.group(3) or "", re.I):
            continue
        d1, d2 = int(dm.group(1)), int(dm.group(2) or dm.group(1))
        mo = FOMC_MO[mm.group(1).lower()]
        if d2 < d1 and mm.group(2):
            mo = FOMC_MO[mm.group(2).lower()]  # réunion à cheval sur deux mois (« Apr/May 30-1 »)
        try:
            out.add(dt.date(year + (1 if mo < FOMC_MO[mm.group(1).lower()] else 0), mo, d2).isoformat())
        except ValueError:
            continue
    return sorted(out)


def run_fomc(out):
    """Dates de décision du FOMC publiées par la Réserve fédérale (relues au plus une fois par jour ; ancienne liste gardée si la
    page ne répond pas ou change de forme)."""
    p = os.path.join(out, "fomc.json")
    old = json.load(open(p, encoding="utf8")) if os.path.exists(p) else {}
    if old.get("ts") and time.time() - old["ts"] < 20 * 3600:
        return
    try:
        h = get("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", tries=2, timeout=30).decode("utf8", "replace")
        d = fomc_parse(h)
    except Exception as e:  # noqa: BLE001
        note("fomc", False, str(e)[:120])
        return
    y = TODAY.year
    if sum(1 for x in d if x.startswith(str(y))) < 6:
        note("fomc", False, f"calendrier illisible ({len(d)} dates)")
        return
    save(p, {"ts": int(time.time()), "d": d})
    open(os.path.join(out, ".dirty"), "a").write(" fomc")
    note("fomc")


# ---------------------------------------------------------------- FRED, CBOE, CNN, crypto, Banque mondiale
def run_fred(out):
    fails = [0]

    def one(x):
        sid = x[0]
        if fails[0] >= 6:
            note("fred", False, f"{sid}: source injoignable, abandon")
            return
        try:
            b = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=25, tries=2, ua=RESEARCH_UA)
            fails[0] = 0
            txt = b.decode("utf8", "replace")
            if "," not in txt.splitlines()[0]:
                raise ValueError("réponse inattendue")
            os.makedirs(os.path.join(out, "fred"), exist_ok=True)
            open(os.path.join(out, "fred", sid + ".csv"), "w", encoding="utf8").write(txt)
            note("fred")
        except Exception as e:  # noqa: BLE001
            fails[0] += 1
            note("fred", False, f"{sid}: {e}")
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(one, FRED))
    save(os.path.join(out, "fred_meta.json"), [{"id": a, "n": b, "g": c, "u": d} for a, b, c, d in FRED])


def run_cboe(out):
    for s in CBOE:
        try:
            txt = get(f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{s}_History.csv").decode("utf8", "replace")
            os.makedirs(os.path.join(out, "cboe"), exist_ok=True)
            open(os.path.join(out, "cboe", s + ".csv"), "w", encoding="utf8").write(txt)
            note("cboe")
        except Exception as e:  # noqa: BLE001
            note("cboe", False, f"{s}: {e}")


def run_cnn(out):
    h = {"Accept": "application/json, text/plain, */*", "Referer": "https://edition.cnn.com/", "Origin": "https://edition.cnn.com"}
    # relevé de 15 minutes : un seul essai court, pour ne jamais retarder les autres relevés (le soir : essais complets)
    quick = os.environ.get("FQT_MODE", "eod") != "eod"
    for start in (("2020-07-15",) if quick else ("2020-07-15", "2021-01-01", "2023-01-01", None)):
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata" + (f"/{start}" if start else "")
        try:
            j = json.loads(get(url, headers=h, tries=1, timeout=20) if quick else get(url, headers=h, tries=2))
            if j.get("fear_and_greed"):
                save(os.path.join(out, "cnn_fg.json"), j)
                note("cnn")
                return
        except Exception as e:  # noqa: BLE001
            note("cnn", False, f"{start}: {e}")


def run_crypto(out, prev):
    for sid, prod, first in CRYPTO:
        try:
            old = prev_series(prev, sid, "crypto")
            rows = {}
            start = dt.date.fromisoformat(first)
            if old and old.get("d") and len(old["d"]) > 300:
                for i, d in enumerate(old["d"]):
                    rows[d] = (d, old["o"][i], old["h"][i], old["l"][i], old["c"][i], (old.get("v") or [0] * len(old["d"]))[i])
                start = i2d(old["d"][-1]) - dt.timedelta(days=5)
            while start < TODAY:
                end = min(start + dt.timedelta(days=299), TODAY)
                url = (f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=86400"
                       f"&start={start.isoformat()}T00:00:00Z&end={end.isoformat()}T00:00:00Z")
                for t, lo, hi, op, cl, vol in json.loads(get(url, headers={"Accept": "application/json"})):
                    d = d2i(dt.datetime.fromtimestamp(t, dt.timezone.utc).date())
                    if d2i(TODAY) > d:  # jour en cours exclu (bougie incomplète)
                        rows[d] = (d, op, hi, lo, cl, int(vol))
                start = end + dt.timedelta(days=1)
                time.sleep(0.35)
            r = [rows[k] for k in sorted(rows)]
            save(os.path.join(out, "crypto", sid + ".json"), {"d": [x[0] for x in r], "o": [x[1] for x in r], "h": [x[2] for x in r],
                                                              "l": [x[3] for x in r], "c": [x[4] for x in r], "v": [x[5] for x in r]})
            note("coinbase")
        except Exception as e:  # noqa: BLE001
            note("coinbase", False, f"{sid}: {e}")


def run_wb(out):
    res = {"countries": {}, "ind": {}}
    cs = ";".join(UEMOA)
    for code, name, unit in WB:
        try:
            j = json.loads(get(f"https://api.worldbank.org/v2/country/{cs}/indicator/{code}?format=json&per_page=2000&date=1990:{TODAY.year}"))
            vals = {}
            for r in (j[1] if len(j) > 1 and j[1] else []):
                c = r.get("countryiso3code") or r["country"]["id"]
                res["countries"][c] = r["country"]["value"]
                if r.get("value") is not None:
                    vals.setdefault(c, {})[r["date"]] = r["value"]
            res["ind"][code] = {"n": name, "u": unit, "v": vals}
            note("worldbank")
        except Exception as e:  # noqa: BLE001
            note("worldbank", False, f"{code}: {e}")
        time.sleep(0.3)
    if res["ind"]:
        save(os.path.join(out, "worldbank.json"), res)


# ---------------------------------------------------------------- SEC XBRL
FLOW = {  # clé : (concepts us-gaap, concepts ifrs-full) par ordre de préférence
    "rev": (["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax",
             "SalesRevenueNet", "SalesRevenueGoodsNet", "SalesRevenueServicesNet", "RevenuesNetOfInterestExpense"], ["Revenue", "RevenueFromContractsWithCustomers"]),
    "cogs": (["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold", "CostOfServices"], ["CostOfSales"]),
    "gp": (["GrossProfit"], ["GrossProfit"]),
    "opi": (["OperatingIncomeLoss"], ["ProfitLossFromOperatingActivities"]),
    "ni": (["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic", "ProfitLoss"], ["ProfitLossAttributableToOwnersOfParent", "ProfitLoss"]),
    "pti": (["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
             "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
             "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic"], ["ProfitLossBeforeTax"]),
    "tax": (["IncomeTaxExpenseBenefit"], ["IncomeTaxExpenseContinuingOperations"]),
    "int": (["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt", "InterestAndDebtExpense"], ["FinanceCosts", "InterestExpense"]),
    "rnd": (["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"], ["ResearchAndDevelopmentExpense"]),
    "da": (["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet", "DepreciationAndAmortization",
            "DepreciationAmortizationAndOther", "Depreciation"], ["DepreciationAndAmortisationExpense",
                                                                   "AdjustmentsForDepreciationAndAmortisationExpense"]),
    "sbc": (["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"], ["AdjustmentsForSharebasedPayments"]),
    "ocf": (["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
            ["CashFlowsFromUsedInOperatingActivities"]),
    "capex": (["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets", "PaymentsForCapitalImprovements",
               "PaymentsToAcquireOtherPropertyPlantAndEquipment"], ["PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
                                                                     "PurchaseOfPropertyPlantAndEquipment"]),
    "capi": (["PaymentsToAcquireIntangibleAssets"], ["PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities"]),
    "acq": (["PaymentsToAcquireBusinessesNetOfCashAcquired"], ["CashFlowsUsedInObtainingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities"]),
    "div": (["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"], ["DividendsPaidClassifiedAsFinancingActivities"]),
    "buy": (["PaymentsForRepurchaseOfCommonStock"], ["PaymentsToAcquireOrRedeemEntitysShares"]),
}
INST = {
    "assets": (["Assets"], ["Assets"]),
    "ca": (["AssetsCurrent"], ["CurrentAssets"]),
    "cl": (["LiabilitiesCurrent"], ["CurrentLiabilities"]),
    "liab": (["Liabilities"], ["Liabilities"]),
    "eq": (["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], ["EquityAttributableToOwnersOfParent", "Equity"]),
    "cash": (["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash"], ["CashAndCashEquivalents"]),
    "sti": (["MarketableSecuritiesCurrent", "ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"], ["CurrentInvestments"]),
    "ltd": (["LongTermDebt", "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities", "DebtInstrumentCarryingAmount"], []),
    "ltdnc": (["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations", "LongTermNotesPayable", "ConvertibleNotesPayable"],
              ["NoncurrentPortionOfNoncurrentBorrowings", "LongtermBorrowings", "NoncurrentBorrowings"]),
    "dcur": (["DebtCurrent", "LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"], ["CurrentBorrowings", "CurrentPortionOfNoncurrentBorrowings"]),
    "cp": (["CommercialPaper"], []),
    "stb": (["ShortTermBorrowings"], ["ShorttermBorrowings"]),
    "re": (["RetainedEarningsAccumulatedDeficit"], ["RetainedEarnings"]),
    "inv": (["InventoryNet"], ["Inventories"]),
    "ar": (["AccountsReceivableNetCurrent"], ["TradeAndOtherCurrentReceivables"]),
    "gw": (["Goodwill"], ["Goodwill"]),
}
SHARES = (["WeightedAverageNumberOfDilutedSharesOutstanding"], ["WeightedAverageNumberOfSharesOutstandingDiluted", "AdjustedWeightedAverageShares"])
SHARES_OUT = ["EntityCommonStockSharesOutstanding"]


def days(a, b):
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def sec_pick(facts, tax, names, unit_kind):
    """Faits d'une liste de concepts : [(rang, start, end, val, filed)] dans l'unité monétaire dominante."""
    rows, unit = [], None
    node = facts.get(tax) or {}
    for rank, nm in enumerate(names):
        c = node.get(nm)
        if not c:
            continue
        units = c.get("units") or {}
        if unit_kind == "shares":
            u = "shares" if "shares" in units else None
        else:
            cands = [k for k in units if re.fullmatch(r"[A-Z]{3}", k)]
            u = "USD" if "USD" in cands else (max(cands, key=lambda k: len(units[k])) if cands else None)
        if not u:
            continue
        unit = unit or u
        if u != unit:
            continue
        for f in units[u]:
            if f.get("val") is None or not f.get("end"):
                continue
            rows.append((rank, f.get("start"), f["end"], float(f["val"]), f.get("filed", "")))
    return rows, unit


def by_period(rows):
    best = {}
    for rank, s, e, v, filed in rows:
        k = (s, e)
        if k not in best or (rank, -int(filed.replace("-", "") or 0)) < (best[k][0], -int(best[k][2].replace("-", "") or 0)):
            best[k] = (rank, v, filed)
    return {k: v[1] for k, v in best.items()}


def quarterize(per):
    """Valeurs trimestrielles discrètes : trimestres publiés directement, sinon différences des cumuls depuis le début d'exercice."""
    q, annual = {}, {}
    for (s, e), v in per.items():
        if not s:
            continue
        n = days(s, e)
        if 75 <= n <= 105:
            q[e] = v
        if 350 <= n <= 380:
            annual[e] = v
    by_s = {}
    for (s, e), v in per.items():
        if not s:
            continue
        n = days(s, e)
        b = round(n / 91.3)
        if b in (1, 2, 3, 4) and abs(n - b * 91.3) <= 22:
            by_s.setdefault(s, {})[b] = (e, v)
    for s, cum in by_s.items():
        for b in (2, 3, 4):
            if b in cum and b - 1 in cum and cum[b][0] not in q:
                q[cum[b][0]] = cum[b][1] - cum[b - 1][1]
    return q, annual


def ttm(q):
    ends = sorted(q)
    out = {}
    for i in range(3, len(ends)):
        if 250 <= days(ends[i - 3], ends[i]) <= 300:
            out[ends[i]] = q[ends[i - 3]] + q[ends[i - 2]] + q[ends[i - 1]] + q[ends[i]]
    return out


def sec_company(cik, t, facts_json):
    facts = facts_json.get("facts") or {}
    tax = "us-gaap" if "us-gaap" in facts else ("ifrs-full" if "ifrs-full" in facts else None)
    if not tax:
        return None
    ti = 0 if tax == "us-gaap" else 1
    ccy = None
    flows_q, flows_a = {}, {}
    for k, names in FLOW.items():
        rows, u = sec_pick(facts, tax, names[ti], "money")
        if not rows:
            continue
        if k in ("rev", "ni", "ocf"):
            ccy = ccy or u
        q, a = quarterize(by_period(rows))
        flows_q[k], flows_a[k] = q, a
    inst = {}
    for k, names in INST.items():
        rows, _ = sec_pick(facts, tax, names[ti], "money")
        if rows:
            per = by_period(rows)
            inst[k] = {e: v for (s, e), v in per.items()}
    rows, _ = sec_pick(facts, tax, SHARES[ti], "shares")
    shd = {}
    if rows:
        best = {}
        for rank, s, e, v, filed in rows:  # durée la plus courte = trimestre
            n = days(s, e) if s else 999
            key = (rank, n, -int(filed.replace("-", "") or 0))
            if e not in best or key < best[e][0]:
                best[e] = (key, v)
        shd = {e: x[1] for e, x in best.items()}
    rows, _ = sec_pick(facts, "dei", SHARES_OUT, "shares")
    sho = by_period(rows) if rows else {}
    sho_last = None
    if sho:
        e = max(e for (_, e) in sho)
        sho_last = (e, sum(v for (s, ee), v in sho.items() if ee == e))
    ttms = {k: ttm(q) for k, q in flows_q.items()}
    ends = sorted(set(ttms.get("rev", {})) | set(ttms.get("ni", {})) | set(ttms.get("ocf", {})))
    annual_mode = len(ends) < 4
    if annual_mode:  # émetteurs étrangers (20-F) : exercices annuels seulement
        ends = sorted(set(flows_a.get("rev", {})) | set(flows_a.get("ni", {})))
        ttms = flows_a
    ends = ends[-48:]

    def near(m, e, tol=12):
        if e in m:
            return m[e]
        best = None
        for k, v in m.items():
            dd = abs(days(k, e))
            if dd <= tol and (best is None or dd < best[0]):
                best = (dd, v)
        return best[1] if best else None
    res = {"t": t, "cik": cik, "name": facts_json.get("entityName"), "tax": tax, "ccy": ccy or "USD", "annual_only": annual_mode, "q": ends,
           "ttm": {k: [near(m, e, 5) for e in ends] for k, m in ttms.items() if m},
           "bs": {k: [near(m, e) for e in ends] for k, m in inst.items() if m},
           "shd": [near(shd, e, 15) for e in ends] if shd else None, "sho": sho_last}
    ya = sorted(set(flows_a.get("rev", {})) | set(flows_a.get("ni", {})) | set(flows_a.get("ocf", {})))[-16:]
    res["y"] = ya
    res["a"] = {k: [near(m, e, 5) for e in ya] for k, m in flows_a.items() if m}
    res["abs"] = {k: [near(m, e) for e in ya] for k, m in inst.items() if m}
    for blk in ("ttm", "bs", "a", "abs"):
        res[blk] = {k: [None if v is None else round(v) for v in arr] for k, arr in res[blk].items() if any(v is not None for v in arr)}
    if res["shd"]:
        res["shd"] = [None if v is None else round(v) for v in res["shd"]]
    return res


def run_sec(out, prev, max_age_days):
    cache = None
    if os.path.exists(os.path.join(out, "secfacts.json")):
        try:
            cache = json.load(open(os.path.join(out, "secfacts.json"), encoding="utf8"))
        except Exception:  # noqa: BLE001
            cache = None
    nd = os.path.join(out, "nasdaq_meta.json")
    ndx = [x["s"] for x in json.load(open(nd, encoding="utf8")).get("ndx", [])] if os.path.exists(nd) else []
    wanted = sorted({s for s, _, typ, _ in US if typ == "Equity"} | set(ndx))
    if cache and (time.time() - cache.get("ts", 0)) < max_age_days * 86400 and set(wanted) <= set(cache.get("co", {})) | set(cache.get("missing", [])):
        save(os.path.join(out, "secfacts.json"), cache)
        log("SEC : cache récent conservé", len(cache.get("co", {})))
        note("sec-cache")
        return
    h = {"User-Agent": SEC_UA, "Accept-Encoding": "gzip", "Accept": "application/json", "Host": None}
    h.pop("Host")
    cikmap = {}
    seed = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "seed", "sec_cik.json")
    if os.path.exists(seed):  # correspondance ticker -> CIK conservée dans le dépôt (la SEC bloque parfois www.sec.gov depuis le cloud)
        cikmap.update(json.load(open(seed, encoding="utf8")))
    for url in ("https://www.sec.gov/files/company_tickers.json", "https://www.sec.gov/include/ticker.txt"):
        try:
            b = get(url, headers=h, tries=2, timeout=30)
            if url.endswith(".json"):
                for v in json.loads(b).values():
                    cikmap[v["ticker"].upper()] = v["cik_str"]
            else:
                for line in b.decode("utf8", "replace").splitlines():
                    p_ = line.split()
                    if len(p_) == 2 and p_[1].isdigit():
                        cikmap[p_[0].upper()] = int(p_[1])
            note("sec-tickers")
            break
        except Exception as e:  # noqa: BLE001
            note("sec-tickers", False, f"{url}: {e}")
    if not cikmap:
        if cache:
            save(os.path.join(out, "secfacts.json"), cache)
        return
    res = {"ts": int(time.time()), "co": {}, "missing": []}

    names = {s: n for s, n, _, _ in US}
    nm_ = os.path.join(out, "nasdaq_meta.json")
    if os.path.exists(nm_):
        for k, v in (json.load(open(nm_, encoding="utf8")).get("screener") or {}).items():
            names.setdefault(k, v.get("n") or "")
    stop = {"inc", "corp", "corporation", "holdings", "holding", "group", "the", "company", "co", "ltd", "plc", "sa", "nv", "class", "common", "stock", "technologies", "technology", "and"}
    tok = lambda x: {w for w in re.sub(r"[^a-z0-9 ]", " ", (x or "").lower()).split() if len(w) > 2 and w not in stop}  # noqa: E731

    def one(t):
        cik = cikmap.get(t) or cikmap.get(t.replace(".", "-"))
        if not cik:
            return t, None, "CIK introuvable"
        try:
            j = json.loads(get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json", headers=h, timeout=90))
            time.sleep(0.25)
            if names.get(t) and not (tok(names[t]) & tok(j.get("entityName"))):
                return t, None, f"CIK {cik} = {j.get('entityName')} (ne correspond pas à {names[t]})"
            return t, sec_company(cik, t, j), None
        except Exception as e:  # noqa: BLE001
            return t, None, str(e)
    with ThreadPoolExecutor(3) as ex:
        for t, r, err in ex.map(one, wanted):
            if r:
                res["co"][t] = r
                note("sec")
            else:
                res["missing"].append(t)
                note("sec", False, f"{t}: {err}")
                if cache and t in cache.get("co", {}):
                    res["co"][t] = cache["co"][t]
    save(os.path.join(out, "secfacts.json"), res)


# ---------------------------------------------------------------- SikaFinance archivé (web.archive.org) : exercices plus anciens
def sika_table(html_):
    """Tableau « chiffres clés » d'une page société SikaFinance : {année: {ca, rn, bnpa, per, div}} (millions FCFA, FCFA/action)."""
    import html as H
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html_, flags=re.S)
    cells = [re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", c))).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", t, re.S)]
    out = {}
    for i, c in enumerate(cells):
        if re.fullmatch(r"20\d\d", c) and i + 4 < len(cells) and all(re.fullmatch(r"20\d\d", cells[i + k]) for k in range(1, 3)):
            yrs = []
            j = i
            while j < len(cells) and re.fullmatch(r"20\d\d", cells[j]):
                yrs.append(int(cells[j]))
                j += 1
            keys = {"chiffre d'affaires": "ca", "chiffre d’affaires": "ca", "résultat net": "rn", "bnpa": "bnpa", "per": "per", "dividende": "div", "produit net bancaire": "ca"}
            while j < len(cells):
                lab = cells[j].lower()
                k = keys.get(lab)
                if k is None and lab.startswith("croissance"):
                    j += 1 + len(yrs) - 1
                    continue
                if k is None:
                    if re.fullmatch(r"20\d\d", cells[j]):
                        break
                    j += 1
                    continue
                vals = cells[j + 1:j + 1 + len(yrs)]
                for y, v in zip(yrs, vals):
                    x = v.replace(" ", "").replace("\xa0", "").replace(" ", "").replace(",", ".")
                    try:
                        out.setdefault(y, {})[k] = float(x)
                    except ValueError:
                        pass
                j += 1 + len(yrs)
            break
    return out


SIKAH_V = 2


def run_sikah(out):
    """Chiffres clés publiés (chiffre d'affaires, résultat net, BNPA, dividende) des pages société archivées : chaque adresse
    qu'a eue la page (societe.aspx?s=, societe?s=, societe/), une capture par année civile, la plus ancienne de l'année
    (fenêtres de cinq exercices les plus anciennes) ; pour un exercice donné, la capture la plus récente l'emporte."""
    path = os.path.join(out, "sika_hist.json")
    db = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {"t": {}, "miss": {}}
    if db.get("v") != SIKAH_V:  # nouvelle lecture : tous les titres sont repris
        db = {"v": SIKAH_V, "t": {}, "miss": {}, "old": db.get("t", {})}
    try:
        fund = harzat_json("fundamentals.json")
    except Exception as e:  # noqa: BLE001
        note("sikah", False, f"fundamentals: {e}")
        return
    todo = [(t, v.get("source_url")) for t, v in fund.items() if t != "_meta" and v.get("source_url") and t not in db["t"] and db["miss"].get(t, 0) < 3]
    t_end = time.time() + float(os.environ.get("SIKAH_BUDGET", "900"))
    for t, url in todo:
        if time.time() > t_end:
            break
        m_ = re.search(r"societe/([A-Z0-9]+)(\.[a-z]{2})?", url)
        code = (m_.group(1) if m_ else t).upper()
        rows = []
        for pat in (f"sikafinance.com/marches/societe/{code}*", f"sikafinance.com/marches/societe?s={code}*",
                    f"sikafinance.com/marches/societe.aspx?s={code}*"):
            try:
                r_ = json.loads(get_wb("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(pat, safe="*/=") +
                                       "&output=json&fl=timestamp,original,statuscode&filter=statuscode:200&collapse=timestamp:6&limit=200") or b"[]")
                rows += [x for x in r_[1:] if x and re.search(r"(?i)[?/=]" + re.escape(code) + r"(?:\.[a-z]{2})?(?:$|&|/|\?)", x[1])]
            except Exception as e:  # noqa: BLE001
                note("sikah", False, f"{t} cdx: {e}")
                time.sleep(3)
        if not rows:
            db["miss"][t] = db["miss"].get(t, 0) + 1
            note("sikah", False, f"{t}: aucune capture")
            save(path, db)
            continue
        # une capture par année civile : la plus ancienne de l'année (exercices les plus anciens), lues de la plus récente à la
        # plus ancienne (un exercice déjà lu dans une capture plus récente n'est pas remplacé)
        by_y = {}
        for ts, orig, _ in sorted(rows, key=lambda r: r[0]):
            by_y.setdefault(ts[:4], (ts, orig))
        got = {}
        for ts, orig in sorted(by_y.values(), reverse=True):
            if time.time() > t_end + 120:
                break
            try:
                h_ = get_wb(f"http://web.archive.org/web/{ts}id_/{orig}").decode("utf8", "replace")
                tb = sika_table(h_)
                for y, rec in tb.items():
                    if y not in got:
                        got[y] = dict(rec, src=ts[:8])
            except Exception as e:  # noqa: BLE001
                note("sikah", False, f"{t} {ts}: {e}")
        if got:
            db["t"][t] = {str(y): r for y, r in sorted(got.items())}
            note("sikah")
        else:
            db["miss"][t] = db["miss"].get(t, 0) + 1
            note("sikah", False, f"{t}: aucune capture exploitable")
        save(path, db)
    save(path, db)


# ---------------------------------------------------------------- états financiers BRVM (PDF) : comptes des exercices anciens et nouvelles publications
FIN_LAB = [("rev", r"^(chiffre d.affaires( hors taxes)?( et autres produits)?|chiffre d.affaires net|produit net bancaire|total chiffre d.affaires)\b"),
           ("ni", r"^(benifice net|benefice net|resultat net( de l.exercice)?|resultat net \(perte\)|resultat de l.exercice)\b(?!.*(par action|minoritaire))"),
           ("ebitda", r"^excedent brut d.exploitation"), ("ebit", r"^resultat d.exploitation"),
           ("eq", r"^(total )?capitaux propres$|^capitaux propres( et ressources assimilees)?$"), ("assets", r"^total (actif|bilan|general actif)"),
           ("capex_c", r"^(-\s*)?(acquisitions?|decaissements lies aux acquisitions) d.immobilisations corporelles"),
           ("capex_i", r"^(-\s*)?(acquisitions?|decaissements lies aux acquisitions) d.immobilisations incorporelles"),
           ("cfo", r"^flux de tresorerie (provenant|provenants|issus?|nets?) (des|de l.) ?activites? (operationnelles|d.exploitation)")]
FIN_NUM = re.compile(r"^\(?-?\s*\d{1,3}(?:[ . \xa0]\d{3})*(?:,\d+)?\)?$")


def _nrm(x):
    import unicodedata
    return unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower()


def fin_parse(txt):
    """Postes clés d'états financiers (texte pdftotext -layout) : {poste: [N, N-1]}, unité annoncée."""
    lines = txt.splitlines()
    unit = None
    for ln in lines[:250]:
        l_ = _nrm(ln)
        if "millions" in l_ and ("fcfa" in l_ or "f cfa" in l_ or "xof" in l_):
            unit = unit or 1.0
        elif "milliers" in l_ and ("fcfa" in l_ or "f cfa" in l_ or "xof" in l_):
            unit = unit or 1e-3
    found = {}
    for ln in lines:
        segs = [x for x in re.split(r"\s{3,}", ln.strip()) if x]
        i = 0
        while i < len(segs):
            lab = _nrm(segs[i]).strip(" :.-")
            if FIN_NUM.match(segs[i].strip()) or not re.search(r"[a-z]", lab):
                i += 1
                continue
            nums, j = [], i + 1
            while j < len(segs) and FIN_NUM.match(segs[j].strip()) and len(nums) < 4:
                t_ = segs[j].strip()
                neg = t_.startswith("(") or t_.startswith("-")
                try:
                    v = float(re.sub(r"[()\s. \xa0-]", "", t_).replace(",", "."))
                    nums.append(-v if neg else v)
                except ValueError:
                    pass
                j += 1
            lab = re.sub(r"\s+", " ", lab)
            for k, pat in FIN_LAB:
                if k not in found and nums and re.search(pat, lab):
                    found[k] = nums[:2]
            i = j if j > i + 1 else i + 1
    return found, unit


def fin_scale(found, unit, ref):
    """Facteur vers les millions de FCFA : unité annoncée, sinon ordre de grandeur face au chiffre d'affaires de référence."""
    v = (found.get("rev") or found.get("assets") or found.get("ni") or [None])[0]
    if ref and v:
        best = None
        for dv in (1.0, 1e-3, 1e-6):
            r = abs(v * dv) / ref
            sc = abs(math.log10(r)) if r > 0 else 99
            if best is None or sc < best[0]:
                best = (sc, dv)
        if best and best[0] < 0.8:  # à moins d'un facteur ~6 de la référence
            return best[1]
    return unit


def fin_record(found, div_):
    rec = [{}, {}]
    for k, vals in found.items():
        for c in (0, 1):
            if c < len(vals) and vals[c] is not None:
                rec[c][k] = round(vals[c] * div_, 1)
    for r in rec:
        if "capex_c" in r or "capex_i" in r:
            r["capex"] = round(abs(r.pop("capex_c", 0) or 0) + abs(r.pop("capex_i", 0) or 0), 1)
        if "cfo" in r and "capex" in r:
            r["fcf"] = round(r["cfo"] - r["capex"], 1)
    return rec


def run_pdffin(out, budget=600):
    path = os.path.join(out, "pdf_fin.json")
    db = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {"t": {}, "docs": {}}
    try:
        evs = harzat_json("events.json")["events"]
        fund = harzat_json("fundamentals.json")
    except Exception as e:  # noqa: BLE001
        note("pdffin", False, e)
        return
    sh = (json.load(open(os.path.join(out, "sika_hist.json"), encoding="utf8")).get("t", {}) if os.path.exists(os.path.join(out, "sika_hist.json")) else {})

    def ref_ca(t, y):
        ca = dict(((fund.get(t) or {}).get("series") or {}).get("ca") or {})
        for yy, r in (sh.get(t) or {}).items():
            if r.get("ca") and yy not in ca:
                ca[yy] = r["ca"]
        ca = {int(k): v for k, v in ca.items() if v}
        if not ca:
            return None
        return ca[min(ca, key=lambda k: abs(k - y))]
    cand = {}
    for e in evs:
        t, fy, u = e.get("ticker"), e.get("fiscal_year"), e.get("document_url") or ""
        if not t or not fy or e.get("category") != "financial_statements" or not u.lower().endswith(".pdf"):
            continue
        ti = _nrm(e.get("title") or "")
        rank = (0 if ("certifi" in ti or "approuv" in ti or "annule et remplace" in ti) else 1, -(int((e.get("published_at") or "0")[:10].replace("-", "") or 0)))
        cand.setdefault((t, int(fy)), []).append((rank, u))
    todo = [(k, sorted(v)[0][1]) for k, v in cand.items() if k[1] >= 2012 and sorted(v)[0][1] not in db["docs"]]
    todo.sort(key=lambda x: -x[0][1])
    t_end = time.time() + budget
    for (t, fy), u in todo:
        if time.time() > t_end:
            break
        try:
            txt = pdftext(get(u, tries=2, timeout=60))
        except Exception as e:  # noqa: BLE001
            db["docs"][u] = f"erreur {str(e)[:80]}"
            continue
        if len(txt.strip()) < 300:
            db["docs"][u] = "scan sans texte"
            note("pdffin", False, f"{t} {fy}: scan")
            continue
        found, unit = fin_parse(txt)
        div_ = fin_scale(found, unit, ref_ca(t, fy))
        if not found or div_ is None:
            db["docs"][u] = "postes introuvables" if not found else "échelle incertaine"
            note("pdffin", False, f"{t} {fy}: {db['docs'][u]}")
            continue
        cur, prev = fin_record(found, div_)
        tt = db["t"].setdefault(t, {})
        for y, r in ((fy, cur), (fy - 1, prev)):
            if r and (str(y) not in tt or y == fy):
                tt[str(y)] = dict(r, src=u)
        db["docs"][u] = "ok"
        note("pdffin")
    save(path, db)


# ---------------------------------------------------------------- états financiers publiés à la BRVM : textes lus une seule fois
CPT_KW = re.compile(r"bilan|actif|passif|compte de r[ée]sultat|comptes? de r[ée]sultats|tableau des flux|tableau financier|tafire|"
                    r"produit net bancaire|chiffre d.affaires|r[ée]sultat net", re.I)
CPT_AMT = re.compile(r"(?<![\d.,])\d{1,3}(?:[ .,  ]\d{3})+(?![\d])")


OCR_WORKERS = max(1, min(4, os.cpu_count() or 1))  # lectures de pages menées en parallèle (un fil par tesseract)


def cpt_ocr(pdf_path, pages, td, psm=6, dpi=300):
    """Reconnaissance de caractères (gris) des pages données, en français puis en anglais : {"fra": texte, "eng": texte}.
    psm 6 : la page comme un seul bloc ; psm 4 : une colonne de lignes (garde mieux les lignes des tableaux numérisés).
    Une page illisible dans le sens où elle est imprimée (tableau à l'italienne) est relue tournée d'un quart de tour.
    Les pages sont lues plusieurs à la fois (OCR_WORKERS), chaque lecture sur un seul fil ; l'ordre des pages est conservé."""
    import glob, subprocess
    langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, timeout=30).stdout.decode()
    have = [lang for lang in ("fra", "eng") if "\n" + lang in "\n" + langs]
    env = {**os.environ, "OMP_THREAD_LIMIT": "1"}

    def ocr(img, lang):
        return subprocess.run(["tesseract", img, "-", "-l", lang, "--psm", str(psm), "-c", "preserve_interword_spaces=1"],
                              capture_output=True, timeout=400, env=env).stdout.decode("utf8", "replace")

    def score(t):
        return len(CPT_AMT.findall(t)) * 3 + len(re.findall(r"(?i)\b(?:total|capital|resultat|résultat|charges|produits|actif|passif|stocks|dettes|exercice)\b", t))

    def page(pg):
        pre = os.path.join(td, f"o{pg}_")
        try:
            subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-png", "-f", str(pg), "-l", str(pg), pdf_path, pre], capture_output=True, timeout=180)
            imgs = sorted(glob.glob(pre + "*.png"))
            if not imgs or not have:
                return None
            img = imgs[0]
            first = ocr(img, have[0])
            if score(first) < 40:  # page tournée ? essai à +90° et -90°
                try:
                    from PIL import Image
                    best = (score(first), img, first)
                    for ang in (-90, 90):
                        p2 = f"{pre}r{ang}.png"
                        Image.open(img).rotate(ang, expand=True).save(p2)
                        t2 = ocr(p2, have[0])
                        if score(t2) > best[0] * 1.5 + 10:
                            best = (score(t2), p2, t2)
                    img, first = best[1], best[2]
                except Exception:  # noqa: BLE001
                    pass
            res = {have[0]: first}
            for lang in have[1:]:
                res[lang] = ocr(img, lang)
            return res
        finally:
            for f in glob.glob(pre + "*.png"):
                os.remove(f)
    out = {lang: [] for lang in have}
    with ThreadPoolExecutor(OCR_WORKERS) as ex:
        for res in ex.map(page, pages):
            if res:
                for lang in have:
                    out[lang].append(res[lang])
    return {k: "\f".join(v) for k, v in out.items() if v}


def cpt_find_pages(pdf_path, n_pages, td, top=8):
    """Document scanné de plusieurs dizaines de pages : chaque page est lue vite (100 dpi) pour repérer celles des états
    financiers (mots des états et nombre de montants) ; renvoie les numéros des meilleures pages (au plus `top`).
    Les pages sont lues plusieurs à la fois (un fil par lecture)."""
    import glob, subprocess
    env = {**os.environ, "OMP_THREAD_LIMIT": "1"}

    def one(pg):
        pre = os.path.join(td, f"f{pg}_")
        try:
            subprocess.run(["pdftoppm", "-r", "100", "-gray", "-png", "-f", str(pg), "-l", str(pg), pdf_path, pre], capture_output=True, timeout=120)
            imgs = glob.glob(pre + "*.png")
            if not imgs:
                return None
            t = subprocess.run(["tesseract", imgs[0], "-", "-l", "eng", "--psm", "6"], capture_output=True, timeout=120, env=env).stdout.decode("utf8", "replace")
        except Exception:  # noqa: BLE001
            return None
        finally:
            for f in glob.glob(pre + "*.png"):
                os.remove(f)
        s_ = len(re.findall(r"(?i)\b(?:total|actif|passif|capital|r[ée]sultat|charges|produits|bilan|exercice|cr[ée]ances|dettes)\b", t)) \
            + len(re.findall(r"\d[\d .,]{5,}\d", t)) // 2
        return (s_, pg)
    with ThreadPoolExecutor(OCR_WORKERS) as ex:
        sc = [r for r in ex.map(one, range(1, n_pages + 1)) if r]
    best = sorted(sc, reverse=True)[:top]
    return sorted(pg for s_, pg in best if s_ >= 15)


def cpt_events(out):
    """Liste des publications des sociétés cotées (liste tierce + pages « rapports des sociétés cotées » de brvm.org relues
    directement : rien n'échappe à la liste). None si la liste tierce est injoignable."""
    try:
        evs = harzat_json("events.json")["events"]
    except Exception as e:  # noqa: BLE001
        note("comptes", False, f"liste des publications : {e}")
        return None
    try:
        evs = evs + brvm_reports(out, evs)
    except Exception as e:  # noqa: BLE001
        note("comptes", False, f"pages des rapports : {e}")
    return evs


def cpt_cands(evs):
    """Documents PDF de brvm.org rattachés à un titre : {adresse: publication}."""
    cand = {}
    for e in evs:
        u = (e.get("document_url") or "").strip()
        if not e.get("ticker") or not u.lower().endswith(".pdf") or "brvm.org" not in u:
            continue
        cand.setdefault(u, e)
    return cand


def cpt_again(m):
    """Document à reprendre : erreur de téléchargement, ou long scan pas encore lu par reconnaissance de caractères."""
    if str(m.get("st", "")).startswith("erreur"):
        return m.get("n_err", 0) < 3
    if m.get("q", 99) < 40 and not m.get("ocr") and "found" not in m and 0 < (m.get("pages") or 0) <= 120:
        return True
    # couche texte garnie mais rien de vérifiable (police à codes de glyphes, mise en page cassée) : lecture par reconnaissance
    # de caractères pas encore faite
    if m.get("st0") not in (None, "ok") and not m.get("ocr") and "ocr_err" not in m and 0 < (m.get("pages") or 0) <= 120:
        return True
    # document court dont la couche texte n'a rien donné de vérifiable et dont une partie seulement des pages a été lue par
    # reconnaissance de caractères (couche texte garnie mais illisible : police sans table de caractères) : toutes les pages
    return (m.get("st0") not in (None, "ok") and 0 < (m.get("pages") or 0) <= 20 and m.get("ocr") is not None
            and 0 < m["ocr"] < m["pages"] and not m.get("ocr_all"))


def cpt_requeue(m):
    """Document numérisé en attente de sa seconde lecture (400 dpi, ligne par ligne)."""
    return bool(m.get("ocr")) and not m.get("ocr4") and m.get("st") == "lu" and m.get("n_err4", 0) < 2


def cpt_part_of(u, n):
    """Part (0 … n-1) d'un document quand la lecture est répartie sur n machines : d'après son empreinte, toujours la même."""
    import hashlib
    return int(hashlib.sha1(u.encode()).hexdigest()[:16], 16) % max(1, n)


def cpt_left(cand, docs):
    """Documents restant à lire ou à relire."""
    return (sum(1 for u in cand if u not in docs or cpt_again(docs[u]))
            + sum(1 for m in docs.values() if cpt_requeue(m)))


def run_comptes_list(out):
    """Liste des publications écrite une seule fois dans cpt_evs.json, pour une lecture répartie sur plusieurs machines."""
    evs = cpt_events(out)
    if evs is None:
        raise RuntimeError("liste des publications injoignable")
    save(os.path.join(out, "cpt_evs.json"), evs)
    log(f"liste des publications : {len(evs)} ; documents PDF : {len(cpt_cands(evs))}")


def run_comptes(out):
    """États financiers des sociétés cotées publiés sur brvm.org (depuis 1998) : chaque document est téléchargé et lu une seule fois
    (couche texte, sinon reconnaissance de caractères des pages des états), son texte gardé en cache (txt/). La lecture des postes
    et le contrôle des identités comptables sont refaits à chaque passage sur tout le cache par comptes.py.
    Dans la limite de CPT_BUDGET secondes ; états financiers d'abord (les plus récents en premier), puis rapports annuels.
    Lecture répartie (comptes.yml) : CPT_EVS = liste des publications déjà relevée (cpt_evs.json) ; CPT_SHARDS / CPT_SHARD = cette
    machine ne lit que sa part des documents (cpt_part_of) ; CPT_NORE = 1 : pas de seconde lecture (contrôle par relecture)."""
    import hashlib, subprocess, tempfile
    import comptes
    budget = float(os.environ.get("CPT_BUDGET", "1500"))
    n_sh = max(1, int(os.environ.get("CPT_SHARDS") or 1))
    i_sh = int(os.environ.get("CPT_SHARD") or 0)

    def mine(u):
        return n_sh == 1 or cpt_part_of(u, n_sh) == i_sh
    t0 = time.time()
    ip = os.path.join(out, "index.json")
    idx = json.load(open(ip, encoding="utf8")) if os.path.exists(ip) else {"docs": {}}
    docs = idx.setdefault("docs", {})
    os.makedirs(os.path.join(out, "txt"), exist_ok=True)
    if os.environ.get("CPT_EVS"):
        evs = json.load(open(os.environ["CPT_EVS"], encoding="utf8"))
    else:
        evs = cpt_events(out)
        if evs is None:
            return
    # tout ce que les sociétés déposent à la BRVM est lu : états financiers d'abord ; puis communiqués de résultats, rapports des
    # commissaires aux comptes et rapports annuels ; rapports de la société et d'activité ; communiqués, projets de résolutions,
    # assemblées et notations ; enfin tout le reste (avis, calendriers…), dans l'ordre des dates les plus récentes
    cats = {"financial_statements": 0, "financial_results": 1, "auditor_report": 1, "annual_report": 1, "company_report": 2, "activity_report": 2,
            "communique": 3, "resolution_project": 3, "ag_meeting": 3, "rating": 3}
    cand = cpt_cands(evs)
    # (à catégorie égale, les rapports annuels / d'exercice avant les rapports trimestriels, puis les plus récents d'abord)
    todo = sorted(cand.values(), key=lambda e: (cats.get(e["category"], 4),
                                                0 if re.search(r"annuel|exercice|annual", (e.get("document_url") or "").rsplit("/", 1)[-1].lower() + " " + (e.get("title") or "").lower()) else 1,
                                                -int(re.sub(r"\D", "", e.get("published_at") or "0")[:8] or 0)))
    again = cpt_again
    todo = [e for e in todo if (e["document_url"] not in docs or again(docs[e["document_url"]])) and mine(e["document_url"])]
    if not pdf_tools():
        note("comptes", False, "outils PDF absents")
        return
    n_new = n_ocr = 0
    # seconde lecture des documents numérisés encore non vérifiés : un tiers du passage lui est réservé tant qu'il en reste
    try:
        st_ = {u: r.get("st") for u, r in json.load(open(os.path.join(out, "comptes.json"), encoding="utf8")).get("docs", {}).items()}
    except Exception:  # noqa: BLE001
        st_ = {}
    n_re_wait = 0 if os.environ.get("CPT_NORE") else sum(1 for u, m in docs.items() if cpt_requeue(m) and st_.get(u) != "ok" and mine(u))
    budget_new = budget - (min(budget / 3, 300 + 150 * n_re_wait) if n_re_wait else 0)
    for e in todo:
        if time.time() - t0 > budget_new:
            break
        u = e["document_url"]
        h = hashlib.sha1(u.encode()).hexdigest()[:16]
        rec = {"t": e["ticker"], "fy": e.get("fiscal_year"), "ti": (e.get("title") or "")[:200], "d": (e.get("published_at") or "")[:10],
               "cat": e["category"], "h": h, "ts": int(time.time())}
        try:
            b = get(u, tries=2, timeout=120)
        except Exception as ex:  # noqa: BLE001
            rec.update(st=f"erreur {str(ex)[:80]}", n_err=(docs.get(u) or {}).get("n_err", 0) + 1)
            docs[u] = rec
            note("comptes", False, f"{e['ticker']} {u.rsplit('/', 1)[-1][:60]} : {ex}")
            continue
        if b[:4] != b"%PDF":
            rec["st"] = "pas un PDF"
            docs[u] = rec
            continue
        with tempfile.TemporaryDirectory() as td:
            p_ = os.path.join(td, "a.pdf")
            open(p_, "wb").write(b)
            try:
                txt = subprocess.run(["pdftotext", "-layout", p_, "-"], capture_output=True, timeout=180).stdout.decode("utf8", "replace")
            except Exception:  # noqa: BLE001
                txt = ""
            pages = txt.split("\f")
            if pages and not pages[-1].strip():
                pages = pages[:-1]
            rec["pages"] = len(pages)
            keep = list(range(len(pages)))
            if len(pages) > 30:  # rapport annuel : pages des états financiers (et leurs voisines) seulement
                hit = [i for i, pg in enumerate(pages) if len(CPT_KW.findall(pg)) >= 2 and len(CPT_AMT.findall(pg)) >= 15]
                keep = sorted({j for i in hit for j in (i - 1, i, i + 1) if 0 <= j < len(pages)})[:40]
                rec["kept"] = len(keep)
            body = "\f".join(pages[i] for i in keep)
            rec["q"] = len(CPT_AMT.findall(body))
            with gzip.open(os.path.join(out, "txt", h + ".txt.gz"), "wt", encoding="utf8") as f:
                f.write(body)
            ok_text = False
            try:
                r = comptes.read_doc({"txt": (body, False)}, rec)
                ok_text = r.get("st") == "ok" and r.get("n", 0) >= 10
                rec["st0"] = r.get("st")
            except Exception as ex:  # noqa: BLE001
                rec["st0"] = f"lecture : {str(ex)[:60]}"
            # couche texte absente, illisible ou incomplète : reconnaissance de caractères des pages des états
            if not ok_text and time.time() - t0 > budget_new - 240:
                break  # plus le temps de lire ce document par reconnaissance de caractères : il sera repris au passage suivant
            if not ok_text:
                ocr_pages = cpt_ocr_pages(p_, pages, keep, rec, td)
                if ocr_pages:
                    try:
                        o = cpt_ocr(p_, ocr_pages, td)
                        for lang, t_ in o.items():
                            with gzip.open(os.path.join(out, "txt", f"{h}.{lang}.gz"), "wt", encoding="utf8") as f:
                                f.write(t_)
                        rec["ocr"] = len(ocr_pages)
                        n_ocr += 1
                        # première lecture insuffisante : seconde lecture tout de suite (400 dpi, ligne par ligne)
                        r1 = comptes.read_doc({"txt": (body, False), **{k: (v, True) for k, v in o.items()}}, rec)
                        if not (r1.get("st") == "ok" and r1.get("n", 0) >= 15) and time.time() - t0 < budget_new - 120:
                            o4 = cpt_ocr(p_, ocr_pages, td, psm=4, dpi=400)
                            for lang, t_ in o4.items():
                                with gzip.open(os.path.join(out, "txt", f"{h}.{lang}4.gz"), "wt", encoding="utf8") as f:
                                    f.write(t_)
                            rec["ocr4"] = len(ocr_pages)
                    except Exception as ex:  # noqa: BLE001
                        rec["ocr_err"] = str(ex)[:80]
        rec["st"] = "lu"
        docs[u] = rec
        n_new += 1
        note("comptes")
        if n_new % 10 == 0:
            save(ip, idx)
    # seconde lecture des documents numérisés (une fois chacun) : 400 dpi, ligne par ligne (fra4, eng4) ; ceux dont aucun
    # exercice ne se vérifie encore d'abord, les plus récents en premier
    n_re = 0

    def re_q():
        q_ = [u for u, m in docs.items() if cpt_requeue(m) and mine(u)]
        return sorted(q_, key=lambda u: (st_.get(u) == "ok", -int(re.sub(r"\D", "", docs[u].get("d") or "0")[:8] or 0)))
    for u in (re_q() if time.time() - t0 < budget - 300 and not os.environ.get("CPT_NORE") else []):
        if time.time() - t0 > budget - 300:
            break  # (un long document lu à 400 dpi peut prendre plusieurs minutes)
        m = docs[u]
        try:
            b = get(u, tries=2, timeout=120)
            with tempfile.TemporaryDirectory() as td:
                p_ = os.path.join(td, "a.pdf")
                open(p_, "wb").write(b)
                txt = subprocess.run(["pdftotext", "-layout", p_, "-"], capture_output=True, timeout=180).stdout.decode("utf8", "replace")
                pages = txt.split("\f")
                if pages and not pages[-1].strip():
                    pages = pages[:-1]
                keep = list(range(len(pages)))
                if len(pages) > 30:
                    hit = [i for i, pg in enumerate(pages) if len(CPT_KW.findall(pg)) >= 2 and len(CPT_AMT.findall(pg)) >= 15]
                    keep = sorted({j for i in hit for j in (i - 1, i, i + 1) if 0 <= j < len(pages)})[:40]
                ocr_pages = cpt_ocr_pages(p_, pages, keep, m, td)
                if ocr_pages:
                    o = cpt_ocr(p_, ocr_pages, td, psm=4, dpi=400)
                    for lang, t_ in o.items():
                        with gzip.open(os.path.join(out, "txt", f"{m['h']}.{lang}4.gz"), "wt", encoding="utf8") as f:
                            f.write(t_)
                m["ocr4"] = len(ocr_pages) or -1
                n_re += 1
        except Exception as ex:  # noqa: BLE001
            m["n_err4"] = m.get("n_err4", 0) + 1
            note("comptes", False, f"seconde lecture {u.rsplit('/', 1)[-1][:60]} : {str(ex)[:80]}")
        if n_re % 5 == 0:
            save(ip, idx)
    left = sum(1 for e in cand.values() if e["document_url"] not in docs or again(docs[e["document_url"]])) + len(re_q())
    idx.update(v=1, left=left, total=len(cand), last_new=n_new + n_re, ts=int(time.time()))
    save(ip, idx)
    log(f"états financiers : {n_new} documents lus ({n_ocr} par reconnaissance de caractères), {n_re} relus, {left} restent, {len(docs)} en cache")


def run_divhist(out):
    """Dividendes versés depuis l'ouverture de la BRVM (1998) : documents officiels lus une seule fois et gardés en cache (txt/).
      1. liste « Paiement de dividendes » de brvm.org (toutes les pages) et chaque avis de paiement (PDF) qu'elle cite ;
      2. avis du marché (toutes les pages) dont l'intitulé parle de dividende (modification, rectificatif, report) ;
      3. archives de l'ancien site brvm.org (web.archive.org, avant 2014) : avis, bulletins officiels de la cote (colonne du
         dernier dividende payé), publications et revues — avis de dividende d'abord, puis bulletins, puis le reste.
    La lecture des montants (brut, net, impôt, dates, exercice) est faite à chaque passage sur tout le cache par dividendes.py.
    Dans la limite de DIV_BUDGET secondes ; état dans index.json (reprise au passage suivant)."""
    import hashlib, subprocess, tempfile
    budget = float(os.environ.get("DIV_BUDGET", "1500"))
    t0 = time.time()
    ip = os.path.join(out, "index.json")
    idx = json.load(open(ip, encoding="utf8")) if os.path.exists(ip) else {}
    docs = idx.setdefault("docs", {})
    os.makedirs(os.path.join(out, "txt"), exist_ok=True)
    if not pdf_tools():
        note("divhist", False, "outils PDF absents")
        return

    # 1-2. listes de brvm.org (relues entièrement une fois par jour)
    def crawl(path_, key, keep=None, max_pages=150):
        rows_all, pg, empty = [], 0, 0
        while pg < max_pages and time.time() - t0 < budget / 4:
            try:
                html = get("https://www.brvm.org" + path_ + (f"?page={pg}" if pg else ""), tries=2, timeout=40).decode("utf8", "replace")
            except Exception as e:  # noqa: BLE001
                note("divhist", False, f"{key} page {pg} : {str(e)[:80]}")
                break
            rows = views_rows(html)
            if not rows:
                empty += 1
                if empty >= 2:
                    break
            else:
                empty = 0
            for r in rows:
                if keep is None or keep(r):
                    rows_all.append({k: v for k, v in r.items() if v.get("t") or v.get("d") or v.get("u")})
            pg += 1
        return rows_all, pg
    if idx.get("lists_day") != TODAY.isoformat():
        esv, n_pg = crawl("/fr/esv/paiement-de-dividendes", "esv")
        if esv:
            idx["esv"], idx["esv_pages"] = esv, n_pg
        av, n_pg2 = crawl("/fr/marche/avis-et-publications/avis", "avis",
                          keep=lambda r: "dividende" in _nrm(" ".join(v.get("t") or "" for v in r.values()) + " " + " ".join(" ".join(v.get("u") or []) for v in r.values())),
                          max_pages=400)
        if av:
            idx["avis"], idx["avis_pages"] = av, n_pg2
        if esv or av:
            idx["lists_day"] = TODAY.isoformat()
        save(ip, idx)
        log(f"dividendes : liste brvm.org {len(idx.get('esv') or [])} lignes ({idx.get('esv_pages')} pages), avis {len(idx.get('avis') or [])}")

    # 3. archives de l'ancien site (liste une fois, puis documents par ordre de priorité)
    if not idx.get("cdx"):
        cdx = {}
        flt = "&filter=" + urllib.parse.quote("mimetype:application/(pdf|x-pdf|octet-stream).*", safe=":/") + "&to=2014"
        for pat, extra in (("brvm.org", flt),):  # (domaine entier : bfin.brvm.org compris)
            key_ = None
            for _ in range(20):
                url = ("http://web.archive.org/cdx/search/cdx?url=" + pat + "&matchType=domain&output=json&collapse=urlkey&filter=statuscode:200"
                       + extra + "&limit=5000&showResumeKey=true" + (f"&resumeKey={urllib.parse.quote(key_)}" if key_ else ""))
                try:
                    rows = json.loads(get_wb(url) or b"[]")
                except Exception as e:  # noqa: BLE001
                    note("divhist", False, f"cdx {pat} : {str(e)[:80]}")
                    break
                key_ = None
                if rows and rows[-1] and len(rows[-1]) == 1:  # dernière ligne : clé de reprise
                    key_ = rows[-1][0]
                    rows = rows[:-2] if len(rows) >= 2 and not rows[-2] else rows[:-1]
                for r in rows[1:]:
                    if len(r) >= 3 and r[2] not in cdx:
                        cdx[r[2]] = r[1]
                if not key_:
                    break
        if cdx:
            idx["cdx"] = [[u, ts] for u, ts in sorted(cdx.items())]
            save(ip, idx)
        log(f"dividendes : archives de brvm.org, {len(cdx)} documents PDF")

    def prio(u):
        lu = urllib.parse.unquote(u).lower()
        if "divid" in lu:
            return 0
        if "/boc" in lu or "boc_" in lu or "boc2" in lu:
            return 1
        if "/avis/" in lu:
            return 2
        if "revue" in lu or "annee" in lu or "année" in lu or "bilan" in lu or "/documentation/" in lu:
            return 3
        if "linkclick" in lu:
            return 4
        return 5
    jobs = []
    for r in idx.get("esv") or []:
        for u in (r.get("field-avis-dividende-esv") or {}).get("u") or []:
            jobs.append((0, u, None, {"src": "esv", "soc": (r.get("field-emetteur-esv") or {}).get("t"), "ex": (r.get("field-exercice-comptable-esv") or {}).get("t")}))
    for r in idx.get("avis") or []:
        for v in r.values():
            for u in v.get("u") or []:
                if u.lower().endswith(".pdf"):
                    jobs.append((0, u, None, {"src": "avis", "ti": (r.get("title") or {}).get("t")}))
    for u, ts in idx.get("cdx") or []:
        jobs.append((1 + prio(u), u, ts, {"src": "wb"}))
    jobs.sort(key=lambda j: j[0])
    jobs = [j for j in jobs if j[1] not in docs or (str(docs[j[1]].get("st", "")).startswith("erreur") and docs[j[1]].get("n_err", 0) < 3)]
    n_new = n_ocr = 0
    for pr, u, ts, meta in jobs:
        if time.time() - t0 > budget:
            break
        h = hashlib.sha1(u.encode()).hexdigest()[:16]
        rec = {"h": h, **{k: v for k, v in meta.items() if v}, "ts": int(time.time())}
        if ts:
            rec["wb"] = ts
        try:
            b = get_wb(f"http://web.archive.org/web/{ts}id_/{u}") if ts else get(u, tries=2, timeout=90)
        except Exception as ex:  # noqa: BLE001
            rec.update(st=f"erreur {str(ex)[:80]}", n_err=(docs.get(u) or {}).get("n_err", 0) + 1)
            docs[u] = rec
            continue
        if b[:4] != b"%PDF":
            rec["st"] = "pas un PDF"
            docs[u] = rec
            continue
        with tempfile.TemporaryDirectory() as td:
            p_ = os.path.join(td, "a.pdf")
            open(p_, "wb").write(b)
            try:
                txt = subprocess.run(["pdftotext", "-layout", p_, "-"], capture_output=True, timeout=120).stdout.decode("utf8", "replace")
            except Exception:  # noqa: BLE001
                txt = ""
            pages = txt.split("\f")
            if pages and not pages[-1].strip():
                pages = pages[:-1]
            rec["pages"] = len(pages)
            with gzip.open(os.path.join(out, "txt", h + ".txt.gz"), "wt", encoding="utf8") as f:
                f.write(txt)
            # document numérisé (couche texte vide) : reconnaissance de caractères des premières pages
            if len(re.sub(r"\s", "", txt)) < 150 * max(1, len(pages)) and 0 < len(pages) <= 12 and time.time() - t0 < budget - 120:
                try:
                    o = cpt_ocr(p_, list(range(1, min(len(pages), 6) + 1)), td)
                    for lang, t_ in o.items():
                        with gzip.open(os.path.join(out, "txt", f"{h}.{lang}.gz"), "wt", encoding="utf8") as f:
                            f.write(t_)
                    rec["ocr"] = min(len(pages), 6)
                    n_ocr += 1
                except Exception as ex:  # noqa: BLE001
                    rec["ocr_err"] = str(ex)[:80]
        rec["st"] = "lu"
        docs[u] = rec
        n_new += 1
        if n_new % 20 == 0:
            save(ip, idx)
    left = sum(1 for j in jobs if j[1] not in docs)
    idx.update(v=1, left=left, last_new=n_new, ts=int(time.time()))
    save(ip, idx)
    note("divhist")
    log(f"dividendes : {n_new} documents lus ({n_ocr} par reconnaissance de caractères), {left} restent, {len(docs)} en cache")


def brvm_reports(out, evs, budget=420):
    """Pages « rapports des sociétés cotées » de brvm.org relues directement (une page de 20 documents à la fois, jusqu'à ce qu'une
    page n'apporte plus rien de nouveau) : les documents absents de la liste tierce sont ajoutés, rattachés au titre par la page
    de la société et classés d'après leur intitulé. Cache dans brvm_rapports.json."""
    path = os.path.join(out, "brvm_rapports.json")
    db = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {"slug": {}, "docs": {}}
    known = {(e.get("document_url") or "").strip().lower() for e in evs}
    # page de chaque société -> titre (d'après les publications déjà rattachées)
    slug_t = {}
    for e in evs:
        m = re.search(r"/rapports-societe-cotes/([^/?#]+)", e.get("source_page") or "")
        if m and e.get("ticker"):
            slug_t.setdefault(m.group(1), collections.Counter())[e["ticker"]] += 1
    slugs = {sl: c.most_common(1)[0][0] for sl, c in slug_t.items()}
    db["slug"].update(slugs)
    t0 = time.time()
    rx = re.compile(r'href="(https://www\.brvm\.org/sites/default/files/[^"]+\.pdf)"[^>]*>|<a[^>]*href="(/sites/default/files/[^"]+\.pdf)"')
    added = []
    for sl, t in sorted(db["slug"].items()):
        if time.time() - t0 > budget:
            break
        page = 0
        while page < 40 and time.time() - t0 < budget:
            try:
                h_ = get(f"https://www.brvm.org/fr/rapports-societe-cotes/{sl}?page={page}", tries=1, timeout=40).decode("utf8", "replace")
            except Exception as e:  # noqa: BLE001
                note("rapports", False, f"{sl} p{page}: {e}")
                break
            urls = []
            for a, b in rx.findall(h_):
                u = a or ("https://www.brvm.org" + b)
                if u not in urls:
                    urls.append(u)
            # intitulé dans la cellule <strong> qui précède le lien de téléchargement
            titles = {(a or "https://www.brvm.org" + b): ti_ for ti_, a, b in
                      re.findall(r'<strong>\s*([^<]{3,200}?)\s*</strong>.*?href="(?:(https://www\.brvm\.org/sites/default/files/[^"]+\.pdf)|(/sites/default/files/[^"]+\.pdf))"', h_, re.S)}
            new_ = [u for u in urls if u not in db["docs"]]
            for u in new_:
                db["docs"][u] = {"t": t, "sl": sl, "ti": re.sub(r"\s+", " ", HTML.unescape(titles.get(u, ""))).strip()[:200], "seen": TODAY.isoformat()}
            if not urls or not new_:
                break  # (page vide, ou tout y est déjà connu : les pages suivantes aussi)
            page += 1
            time.sleep(0.5)
    save(path, db)
    for u, m in db["docs"].items():
        if u.lower() in known:
            continue
        fn = u.rsplit("/", 1)[-1].lower()
        ti = (m.get("ti") or "") + " " + fn
        tn = nrm_(ti)
        cat = ("financial_statements" if re.search(r"etats? financ|comptes (?:annuels|sociaux|consolides)|bilan", tn) else
               "annual_report" if re.search(r"rapport annuel", tn) else
               "activity_report" if re.search(r"rapport d.activit|trimestre|semestre", tn) else
               "financial_results" if re.search(r"resultats?", tn) else "company_report")
        ti_n = nrm_(m.get("ti") or "")
        m_ = re.search(r"exercice[s]? (?:clos (?:au|le) \d\d?[ /-]\d\d?[ /-])?(20[0-3]\d|19[89]\d)", ti_n) or re.search(r"(?<!\d)(20[0-3]\d|19[89]\d)(?!\d)", ti_n)
        fy = int(m_.group(1)) if m_ else None  # (sinon l'exercice sera lu dans le document)
        d_ = f"{fn[:4]}-{fn[4:6]}-{fn[6:8]}" if re.match(r"20\d{6}_", fn) else m.get("seen")
        added.append({"ticker": m["t"], "category": cat, "title": m.get("ti") or fn, "published_at": d_, "document_url": u, "fiscal_year": fy,
                      "source": "BRVM", "source_page": f"https://www.brvm.org/fr/rapports-societe-cotes/{m['sl']}", "origin": "rapports"})
    if added:
        log(f"rapports des sociétés cotées : {len(added)} documents absents de la liste tierce ajoutés")
    return added


def nrm_(x):
    import unicodedata
    return unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower()


def cpt_ocr_pages(p_, pages, keep, rec, td):
    """Pages à lire par reconnaissance de caractères : toutes (scan court), celles des états repérées à basse résolution (long scan,
    gardées dans rec["found"]), sinon celles de la couche texte qui parlent des états sans être lisibles."""
    q = len(CPT_AMT.findall("\f".join(pages[i] for i in keep)))
    if len(pages) <= 20:  # document court : toutes les pages (une couche texte garnie peut être illisible : police sans table)
        rec["ocr_all"] = 1
        return [i + 1 for i in range(len(pages))]
    if q < 40 and len(pages) <= 120:
        if not rec.get("found"):
            rec["found"] = cpt_find_pages(p_, len(pages), td)  # long document scanné : pages des états repérées à basse résolution
        return rec["found"]
    # document long : pages qui parlent des états, les moins lisibles (couche texte pauvre ou cassée) d'abord
    cand_ = [i for i in keep if CPT_KW.search(pages[i])]
    return [i + 1 for i in sorted(cand_, key=lambda i: (len(CPT_AMT.findall(pages[i])) >= 15, len(pages[i].strip())))][:10]


# ---------------------------------------------------------------- consensus des analystes (Nasdaq)
def us_equities(out):
    nd = os.path.join(out, "nasdaq_meta.json")
    ndx = [x["s"] for x in json.load(open(nd, encoding="utf8")).get("ndx", [])] if os.path.exists(nd) else []
    return sorted({s for s, _, typ, _ in US if typ == "Equity"} | set(ndx))


def run_analyst(out):
    """Résumé (PER prévisionnel, objectif de cours), prévisions de BPA (révisions), surprises, date des résultats.
    Les surprises et les instantanés du consensus s'accumulent d'un jour à l'autre (historique des révisions)."""
    path = os.path.join(out, "analyst.json")
    old = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {}
    today = TODAY.isoformat()

    def one(sym):
        rec = {"ts": today}
        for key, url in (("sum", f"https://api.nasdaq.com/api/quote/{sym}/summary?assetclass=stocks"),
                         ("fc", f"https://api.nasdaq.com/api/analyst/{sym}/earnings-forecast"),
                         ("sur", f"https://api.nasdaq.com/api/company/{sym}/earnings-surprise"),
                         ("ed", f"https://api.nasdaq.com/api/analyst/{sym}/earnings-date"),
                         ("tp", f"https://api.nasdaq.com/api/analyst/{sym}/targetprice")):
            try:
                j = json.loads(get(url, headers=NQ_H, tries=2, timeout=30))
                rec[key] = j.get("data")
            except Exception as e:  # noqa: BLE001
                rec[key] = None
                note("nasdaq-analyst", False, f"{sym} {key}: {e}")
            time.sleep(0.15)
        return sym, rec
    res = {}
    with ThreadPoolExecutor(4) as ex:
        for sym, rec in ex.map(one, us_equities(out)):
            prev = old.get(sym) or {}
            # surprises : on garde tous les trimestres déjà vus
            hist = {r["q"]: r for r in prev.get("surh", [])}
            for r in (find_rows((rec.get("sur") or {}).get("earningsSurpriseTable") or {}) or []):
                q = r.get("fiscalQtrEnd")
                if q:
                    hist[q] = {"q": q, "d": r.get("dateReported"), "eps": money(r.get("eps")), "cons": money(r.get("consensusForecast")),
                               "pct": money(r.get("percentageSurprise"))}
            rec["surh"] = sorted(hist.values(), key=lambda r: r.get("d") or "")
            # instantané quotidien du consensus annuel (pour suivre les révisions)
            snaps = [x for x in prev.get("snap", []) if x[0] != today][-400:]
            yrows = find_rows(((rec.get("fc") or {}).get("yearlyForecast")) or {}) or []
            if yrows:
                snaps.append([today] + [[r.get("fiscalEnd"), money(r.get("consensusEPSForecast")), money(r.get("noOfEstimates"))] for r in yrows[:3]])
            rec["snap"] = snaps
            ok = any(rec.get(k) for k in ("sum", "fc", "sur"))
            if not ok and prev:
                rec = {**prev, "stale": True}
            res[sym] = rec
            note("nasdaq-analyst", ok, None if ok else f"{sym}: vide")
    save(path, res)


# ---------------------------------------------------------------- BRVM : bulletin officiel de la cote (PER du marché)
def pdftext(b):
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(b)
        f.flush()
        r = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, timeout=120)
    return r.stdout.decode("utf8", "replace")


def frnum(tok):
    t = tok.replace("\xa0", " ").replace(" ", " ").strip()
    t = re.sub(r"(?<=\d)[ .](?=\d{3}\b)", "", t).replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


NUMTOK = re.compile(r"-?\d{1,3}(?:[  \xa0.]\d{3})+(?:,\d+)?|-?\d+(?:,\d+)?")


def boc_parse(txt):
    out = {}
    pats = {"per": r"PER moyen du march", "rdt": r"Taux de rendement moyen du march", "rent": r"Taux de rentabilit[ée] moyen du march",
            "prime": r"Prime de risque du march", "cap": r"Capitalisation boursi[èe]re \(FCFA\)\s*\(Actions"}
    lines = txt.splitlines()
    for k, pat in pats.items():
        for i, ln in enumerate(lines):
            m = re.search(pat, ln, re.I)
            if not m:
                continue
            rest = re.sub(r"\(\*+\)", " ", ln[m.end():])
            rest = re.sub(r"\([^)]*\)", " ", rest)
            nums = [frnum(x) for x in NUMTOK.findall(rest)]
            nums = [x for x in nums if x is not None]
            if not nums and i + 1 < len(lines):
                nums = [x for x in (frnum(y) for y in NUMTOK.findall(lines[i + 1])) if x is not None]
            if nums:
                out[k] = nums[0]
                break
    for k, lo, hi in (("per", 2, 80), ("rdt", 0.1, 30), ("rent", 0.1, 40), ("prime", -20, 30)):
        if k in out and not (lo <= out[k] <= hi):
            out.pop(k)
    idx = boc_indices(txt)
    if idx:
        out["idx"] = idx
    return out


# indices publiés dans le bulletin : en-tête (« BRVM COMPOSITE 537,67  BRVM 30 260,32  BRVM PRESTIGE 200,13 ») et tableaux
# des indices par compartiment et sectoriels (« BRVM - TELECOMMUNICATIONS  3  150,72  0,77 % … ») ; codes de la base des cours
BOC_IDX_HEAD = (("BRVMC", r"BRVM\s+COMPOSITE(?!\s+TOTAL)"), ("BRVM30", r"BRVM\s+30\b"), ("BRVMPR", r"BRVM\s+PRESTIGE"), ("BRVM10", r"BRVM\s+10\b"))
BOC_IDX_ROW = (("BRVMPR", r"BRVM\s*-\s*PRESTIGE"), ("BRVMPA", r"BRVM\s*-\s*PRINCIPAL"), ("BRVM-TEL", r"BRVM\s*-\s*T[ÉE]L[ÉE]COMMUNICATIONS"),
               ("BRVM-CD", r"BRVM\s*-\s*CONSOMMATION\s+DISCR[ÉE]TIONNAIRE"), ("BRVM-SF", r"BRVM\s*-\s*SERVICES\s+FINANCIERS"),
               ("BRVM-CB", r"BRVM\s*-\s*CONSOMMATION\s+DE\s+BASE"), ("BRVM-IN", r"BRVM\s*-\s*INDUSTRIELS"), ("BRVM-EN", r"BRVM\s*-\s*[ÉE]NERGIE"),
               ("BRVM-SP", r"BRVM\s*-\s*SERVICES\s+PUBLICS"))


def boc_indices(txt):
    """{code: [valeur, variation du jour en %]} ; une valeur n'est gardée que si elle est lue sans ambiguïté."""
    out = {}
    lines = txt.splitlines()
    head = lines[:25]
    for code, pat in BOC_IDX_HEAD:
        for i, ln in enumerate(head):
            m = re.search(pat + r"\s{2,}(\d{1,3}(?: \d{3})?[,.]\d{2})(?!\d)", ln, re.I)
            if m:
                out[code] = [frnum(m.group(1)), None]
                break
    # (indices sectoriels de 2025 : reconnus à la ligne des télécommunications ; les anciens indices sectoriels, autre base, sont ignorés)
    new_sect = any(re.match(r"^\s*" + BOC_IDX_ROW[2][1], ln, re.I) for ln in lines)
    for code, pat in BOC_IDX_ROW:
        if code.startswith("BRVM-") and not new_sect:
            continue
        for ln in lines:
            m = re.match(r"^\s*" + pat + r"\s*(?:\(\*+\))?\s{2,}(\d{1,3})\s{2,}(\d{1,3}(?: \d{3})?[,.]\d{2})\s{2,}(-?\d+[,.]\d+)\s*%", ln, re.I)
            if m:
                v, var = frnum(m.group(2)), frnum(m.group(3))
                if code in out and abs(out[code][0] - v) > 1e-9:
                    out.pop(code)  # (en-tête et tableau différents : rien n'est retenu pour cet indice)
                    break
                out[code] = [v, var]
                break
    return {k: v for k, v in out.items() if v[0] and 1 <= v[0] <= 100000}


BOC_TOK = re.compile(r"SP|\d{1,2}-[a-zéûA-Z]+\.?-\d{2}|-?\d+(?: \d{3})*,\d+ ?%|-?\d+(?: \d{3})*(?:,\d+)?|,\d+")
BOC_MON = {"janv": 1, "févr": 2, "fevr": 2, "mars": 3, "avr": 4, "mai": 5, "juin": 6, "juil": 7, "août": 8, "aout": 8, "sept": 9, "oct": 10, "nov": 11, "déc": 12, "dec": 12}


BOC_DATE_RX = re.compile(r"^(\d{1,2})-([a-zéûA-Z]+)\.?-(\d{2})$")


def _boc_nb(t):
    t = (t or "").strip().replace("\xa0", " ")
    if t in ("", "NC", "SP", "-", "ND"):
        return None
    t = t.rstrip("%").strip().replace(" ", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def boc_layout_old(txt):
    """Bulletins de 2013 à fin 2017 : colonnes Volume, Valeur, Cours précédent, Ouv., Clôt., Moy., Variation, Variation de l'année,
    Cours de référence, écarts maximaux (bas, haut), dernier dividende (montant net, date), Comp., Rdt net, PER."""
    return bool(re.search(r"\bMoy\.", txt)) and bool(re.search(r"Ecarts maximaux|Écarts maximaux", txt))


def boc_stocks_old(txt):
    out = {}
    for ln in txt.splitlines():
        m = re.match(r"^\s*([A-Z][A-Z0-9]{2,5})\s{2,}(\S.*?)\s{2,}(\S.*)$", ln)
        if not m or m.group(1) in ("TOTAL", "SECTEUR"):
            continue
        cols = [c.strip() for c in re.split(r"\s{2,}", m.group(3).strip()) if c.strip()]
        pct = [i for i, c in enumerate(cols) if c.endswith("%")]
        r = {"n": re.sub(r"\s+", " ", m.group(2)).strip()}
        flags = [i for i, c in enumerate(cols[:6]) if c in ("NC", "SP")]
        if flags:  # pas d'échange (NC) ou titre suspendu (SP) : cours précédent puis trois cases vides
            i0 = flags[0]
            if i0 < 1:
                continue
            r["prev"] = _boc_nb(cols[i0 - 1])
            k = flags[-1] + 1
            if cols[i0] == "SP":
                r["susp"] = 1
        else:
            if not pct or pct[0] < 6:
                continue
            p = pct[0]
            vals = [_boc_nb(c) for c in cols[p - 6:p]]
            if any(v is None for v in vals):
                continue
            r["vol"], r["val"], r["prev"], r["o"], r["c"], r["avg"] = vals
            k = p
        pcs = []
        while k < len(cols) and (cols[k].endswith("%") or cols[k] == "-" and False):
            pcs.append(_boc_nb(cols[k])); k += 1
        if "c" in r and r.get("prev"):
            calc = (r["c"] / r["prev"] - 1) * 100
            if len(pcs) >= 2:
                r["var"], r["ytd"] = pcs[0], pcs[1]
            elif len(pcs) == 1:
                if pcs[0] is not None and abs(pcs[0] - calc) <= 0.06:
                    r["var"] = pcs[0]
                else:
                    r["ytd"] = pcs[0]
        elif pcs:
            r["ytd"] = pcs[-1]
        rest = cols[k:]
        nums = []
        j = 0
        while j < len(rest) and len(nums) < 3 and not BOC_DATE_RX.match(rest[j]):
            v = _boc_nb(rest[j])
            if v is None:
                break
            nums.append(v); j += 1
        if nums:
            r["ref"] = nums[0]
        di = next((i for i, c in enumerate(rest) if BOC_DATE_RX.match(c)), None)
        if di is not None:
            if di >= 1 and di - 1 >= 3:
                r["div"] = _boc_nb(rest[di - 1])
            dm = BOC_DATE_RX.match(rest[di])
            mo = BOC_MON.get(dm.group(2).lower().rstrip(".")[:5]) or BOC_MON.get(dm.group(2).lower()[:4])
            if mo:
                yy = int(dm.group(3))
                r["div_d"] = f"{2000 + yy if yy < 70 else 1900 + yy}-{mo:02d}-{int(dm.group(1)):02d}"
            tail = rest[di + 1:]
            if tail and re.match(r"^\d+(er|e|eme|ème)$", tail[0]):
                tail = tail[1:]
            for t in tail:
                if t.endswith("%"):
                    r["yld"] = _boc_nb(t)
                elif _boc_nb(t) is not None:
                    r["per"] = _boc_nb(t)
        if r.get("c") or r.get("prev") or r.get("ref"):
            out[m.group(1)] = {k_: v for k_, v in r.items() if v is not None}
    return out


def boc_stocks(txt):
    """Tableau des actions du bulletin officiel de la cote : par symbole, cours précédent, ouverture, clôture, variation,
    volume, valeur, cours de référence, variation annuelle, dernier dividende net et sa date, rendement net, PER."""
    if boc_layout_old(txt):  # mise en page 2013-2017 (avec le cours moyen)
        return boc_stocks_old(txt)
    out = {}
    num_ = lambda t: None if t in (None, "SP") else float(t.replace(" ", "").replace("%", "").replace(",", ".")) if t.strip(" %,") else None
    for ln in txt.splitlines():
        m = re.match(r"^\s*(?:[A-Z]{2,4}\s{2,})?([A-Z][A-Z0-9]{2,5})\s{2,}(\S.*?)\s{2,}(\S.*)$", ln)  # code secteur en tête (2024) ou non (2026)
        if not m or m.group(1) == "TOTAL":
            continue
        toks = BOC_TOK.findall(m.group(3))
        pi = [i for i, t in enumerate(toks) if t.endswith("%")]
        di = [i for i, t in enumerate(toks) if re.match(r"\d{1,2}-", t)]
        if not pi or pi[0] < 3:
            continue
        r = {"n": re.sub(r"\s+", " ", m.group(2)).strip(), "prev": num_(toks[0]), "o": num_(toks[1]), "c": num_(toks[2]), "var": num_(toks[pi[0]])}
        mid = [t for t in toks[pi[0] + 1:(pi[1] if len(pi) > 1 else (di[0] if di else len(toks)))] if not t.endswith("%")]
        if len(pi) == 1 and not di and len(mid) == 4:  # ni variation annuelle ni dividende : le dernier nombre est le PER
            r["per"] = num_(mid.pop())
        if len(mid) >= 3:
            r["vol"], r["val"], r["ref"] = num_(mid[0]), num_(mid[1]), num_(mid[2])
        elif mid:
            r["ref"] = num_(mid[-1])
        if len(pi) > 1 and (not di or pi[1] < di[0]):
            r["ytd"] = num_(toks[pi[1]])
        if di:
            k = di[0]
            if k >= 1 and not toks[k - 1].endswith("%"):
                r["div"] = num_(toks[k - 1])
            dm = re.match(r"(\d{1,2})-([a-zéûA-Z]+)\.?-(\d{2})", toks[k])
            mo = BOC_MON.get(dm.group(2).lower().rstrip(".")[:5]) or BOC_MON.get(dm.group(2).lower()[:4])
            if mo:
                yy = int(dm.group(3))
                r["div_d"] = f"{2000 + yy if yy < 70 else 1900 + yy}-{mo:02d}-{int(dm.group(1)):02d}"
            tail = toks[k + 1:]
            for t in tail:
                if t.endswith("%"):
                    r["yld"] = num_(t)
                else:
                    r["per"] = num_(t)
        if r.get("c") or r.get("prev") or r.get("ref"):
            out[m.group(1)] = {k: v for k, v in r.items() if v is not None}
    return out


def run_boc(out):
    import calendar
    path = os.path.join(out, "boc.json")
    db = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {"d": {}, "miss": []}
    miss = set(db.get("miss", []))

    def try_day(d):
        k = d.strftime("%Y%m%d")
        for url in (f"https://bfin.brvm.org/boc/BOC_JOUR/BOC_{k}.pdf", f"https://www.brvm.org/sites/default/files/boc_{k}_2.pdf",
                    f"https://www.brvm.org/sites/default/files/boc_{k}.pdf"):
            try:
                b = get(url, tries=1, timeout=20)
                if b[:4] != b"%PDF":
                    continue
                txt = pdftext(b)
                rec = boc_parse(txt)
                if rec:
                    rec["u"] = url
                    return k, rec, txt
            except Exception:  # noqa: BLE001
                continue
        return k, None, None
    # derniers jours ouvrés ; puis, 12 au plus par passage, les bulletins des 120 derniers jours lus avant la lecture des indices
    latest_txt = None
    old_idx = [d for d in (TODAY - dt.timedelta(days=b) for b in range(8, 121))
               if d.weekday() < 5 and "idx" not in (db["d"].get(d.strftime("%Y%m%d")) or {"idx": 1})][:12]
    for d in [TODAY - dt.timedelta(days=back) for back in range(0, 8)] + old_idx:
        if d.weekday() >= 5 or "idx" in (db["d"].get(d.strftime("%Y%m%d")) or {}):
            continue
        k, rec, txt = try_day(d)
        if rec:
            rec.setdefault("idx", {})  # (indices illisibles dans ce bulletin : pas relu à chaque passage)
            db["d"][k] = rec
            latest_txt = latest_txt or txt
            note("boc")
    # rattrapage : un bulletin par mois (premiers jours ouvrés) depuis 2012, 30 mois par passage
    have_m = {k[:6] for k in db["d"]}
    todo = []
    y, m = 2012, 1
    while (y, m) <= (TODAY.year, TODAY.month):
        km = f"{y}{m:02d}"
        if km not in have_m and km not in miss:
            todo.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    todo = todo[::-1][:14]

    def month(ym):
        y, m = ym
        for day in range(1, min(10, calendar.monthrange(y, m)[1]) + 1):
            d = dt.date(y, m, day)
            if d.weekday() >= 5 or d > TODAY:
                continue
            k, rec, txt = try_day(d)
            if rec:
                return ym, k, rec, txt
        return ym, None, None, None
    with ThreadPoolExecutor(3) as ex:
        for (y, m), k, rec, txt in ex.map(month, todo):
            if rec:
                db["d"][k] = rec
                latest_txt = latest_txt or txt
                note("boc-hist")
            elif (y, m) < (TODAY.year, TODAY.month):
                miss.add(f"{y}{m:02d}")
                note("boc-hist", False, f"{y}-{m:02d}: aucun bulletin lisible")
    db["miss"] = sorted(miss)
    db["d"] = dict(sorted(db["d"].items()))
    save(path, db)
    if latest_txt:
        os.makedirs(os.path.join(out, "debug"), exist_ok=True)
        open(os.path.join(out, "debug", "boc_sample.txt"), "w", encoding="utf8").write(latest_txt[:20000])


# ---------------------------------------------------------------- bulletins officiels de la cote : tableau des 48 actions, jour par jour
BOC_COLS = ("prev", "o", "c", "var", "vol", "val", "ref", "ytd", "div", "div_d", "yld", "per", "avg")
BOC_V = 4  # version du lecteur de bulletins (4 : mise en page 2013-2017 lue colonne par colonne)


def run_bochist(out):
    """Reconstitue, à partir des seuls bulletins officiels de la BRVM, l'historique quotidien de chaque action : cours précédent,
    ouverture, clôture, volume, valeur, cours de référence, variation annuelle, dernier dividende net et sa date, rendement, PER.
    Jours récents d'abord, puis l'archive en remontant jusqu'en 2012, dans la limite de BOC_BUDGET secondes par passage."""
    budget = float(os.environ.get("BOC_BUDGET", "600"))
    t0 = time.time()
    d_dir = os.path.join(out, "boc_px")
    os.makedirs(d_dir, exist_ok=True)
    ip = os.path.join(d_dir, "_index.json")
    idx = json.load(open(ip, encoding="utf8")) if os.path.exists(ip) else {"done": [], "miss": []}
    done, miss, bad = set(idx["done"]), set(idx["miss"]), set(idx.get("bad", []))
    years = {}
    if idx.get("v") != BOC_V:  # lecteur amélioré : tous les jours sans résultat sont retentés
        miss, bad = set(), set()
        if (idx.get("v") or 0) < 4:  # bulletins 2013-2017 relus avec le lecteur de leur mise en page ; les lignes mal lues sont effacées
            done = {k for k in done if k >= "20180101"}
            for y in range(2012, 2018):
                p_ = os.path.join(d_dir, f"{y}.json")
                if os.path.exists(p_):
                    os.remove(p_)

    def year(y):
        if y not in years:
            p_ = os.path.join(d_dir, f"{y}.json")
            years[y] = json.load(open(p_, encoding="utf8")) if os.path.exists(p_) else {}
        return years[y]
    recent = {(TODAY - dt.timedelta(days=k)).strftime("%Y%m%d") for k in range(0, 12)}
    todo, d = [], TODAY
    while d >= dt.date(2012, 1, 2):
        k = d.strftime("%Y%m%d")
        if d.weekday() < 5 and k not in done and (k not in miss or k in recent):
            todo.append(d)
        d -= dt.timedelta(days=1)

    samples = {}

    def one(day):
        k = day.strftime("%Y%m%d")
        got_pdf = False
        for url in (f"https://bfin.brvm.org/boc/BOC_JOUR/BOC_{k}.pdf", f"https://www.brvm.org/sites/default/files/boc_{k}_2.pdf",
                    f"https://www.brvm.org/sites/default/files/boc_{k}.pdf"):
            try:
                b = get(url, tries=1, timeout=25)
                if b[:4] != b"%PDF":
                    continue
                got_pdf = True
                txt = pdftext(b)
                rows = boc_stocks(txt)
                if len(rows) >= 15:
                    return k, rows
                samples.setdefault(k[:4], txt[:40000])  # mise en page à apprendre
            except Exception:  # noqa: BLE001
                continue
        return k, ("bad" if got_pdf else None)
    n_ok = n_miss = 0
    with ThreadPoolExecutor(4) as ex:
        for i in range(0, len(todo), 16):
            if time.time() - t0 > budget:
                break
            for k, rows in ex.map(one, todo[i:i + 16]):
                if isinstance(rows, dict):
                    year(k[:4])[k] = {sym: [r.get(c) for c in BOC_COLS] for sym, r in rows.items()}
                    done.add(k)
                    miss.discard(k)
                    n_ok += 1
                else:
                    miss.add(k)
                    if rows == "bad":
                        bad.add(k)
                    n_miss += 1
    for y, v in years.items():
        save(os.path.join(d_dir, f"{y}.json"), dict(sorted(v.items())))
    for y, t in samples.items():
        os.makedirs(os.path.join(d_dir, "_samples"), exist_ok=True)
        open(os.path.join(d_dir, "_samples", f"{y}.txt"), "w", encoding="utf8").write(t)
    save(ip, {"v": BOC_V, "cols": BOC_COLS, "done": sorted(done), "miss": sorted(miss), "bad": sorted(bad), "first": min(done) if done else None,
              "last": max(done) if done else None, "left": max(0, len(todo) - n_ok - n_miss), "ts": int(time.time())})
    if n_ok:
        note("bochist")
    else:
        note("bochist", False, f"aucun bulletin lu ({n_miss} jours sans bulletin)")
    log(f"bulletins : {n_ok} lus, {n_miss} jours sans bulletin, reste {max(0, len(todo) - n_ok - n_miss)}")


# ---------------------------------------------------------------- sondes (PER prévisionnel, archives SikaFinance)
def run_probe(out):
    """Pages brutes enregistrées dans debug/ pour écrire les analyseurs (sources de PER prévisionnel, archives)."""
    dd = os.path.join(out, "debug")
    os.makedirs(dd, exist_ok=True)
    pages = {
        "ms_search_sonatel": "https://www.marketscreener.com/search/?q=sonatel",
        "ms_sonatel": "https://www.marketscreener.com/quote/stock/SONATEL-SA-6500147/",
        "ms_sonatel_fin": "https://www.marketscreener.com/quote/stock/SONATEL-SA-6500147/finances/",
        "valora_home": "https://www.valora-intelligence.com/",
        "afm_brvm": "https://www.african-markets.com/fr/bourse/brvm",
        "afm_brvm_cos": "https://www.african-markets.com/fr/bourse/brvm/listed-companies",
        "richbourse": "https://www.richbourse.com/common/apprendre/details/per",
        "sika_snts": "https://www.sikafinance.com/marches/societe/SNTS.sn",
        "sika_pro_snts": "https://pro.sikafinance.com/finance/SNTS.sn",
    }
    for k, url in pages.items():
        try:
            b = curl(url) if "marketscreener" in url else get(url, tries=2, timeout=40, headers={"Accept": "text/html,application/xhtml+xml"})
            open(os.path.join(dd, k + ".html"), "wb").write(b[:1_500_000])
            note("probe")
        except Exception as e:  # noqa: BLE001
            note("probe", False, f"{k}: {e}")
    # historique des cours SikaFinance avant novembre 2006 ? (api/general/GetHistos, fenêtres de trois mois au plus)
    for k, (d0, d1) in {"sika_histos_1998": ("1998-09-16", "1998-12-15"), "sika_histos_2002": ("2002-01-02", "2002-03-29"),
                        "sika_histos_2006": ("2006-08-01", "2006-10-31"), "sika_histos_2007": ("2007-01-02", "2007-03-30")}.items():
        try:
            body = json.dumps({"ticker": "SNTS", "datedeb": d0, "datefin": d1, "xperiod": "0"}).encode()
            req = urllib.request.Request("https://www.sikafinance.com/api/general/GetHistos", data=body, method="POST",
                                         headers={"Content-Type": "application/json;charset=UTF-8", "User-Agent": UA, "Accept": "application/json",
                                                  "Referer": "https://www.sikafinance.com/marches/historiques/SNTS.sn", "X-Requested-With": "XMLHttpRequest"})
            with urllib.request.urlopen(req, timeout=40) as r_:
                open(os.path.join(dd, k + ".json"), "wb").write(r_.read()[:400000])
            note("probe")
        except Exception as e:  # noqa: BLE001
            note("probe", False, f"{k}: {e}")
    sec_t = {}
    for ua in (SEC_UA, "FQT Terminal research contact@fqt-terminal.app", "Mozilla/5.0 (compatible; research-bot)", UA):
        try:
            b = get("https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenues.json", headers={"Accept-Encoding": "gzip"}, tries=1, timeout=20, ua=ua)
            sec_t[ua] = f"ok {len(b)}"
        except urllib.error.HTTPError as e:
            sec_t[ua] = f"{e.code} {e.read()[:300]!r}"
        except Exception as e:  # noqa: BLE001
            sec_t[ua] = str(e)
    save(os.path.join(dd, "sec_ua_test.json"), sec_t)
    cdx = {}
    for t in ("SNTS", "SGBC", "ORAC", "SIBC"):
        for pat in (f"sikafinance.com/marches/societe/{t}*", f"sikafinance.com/marches/cotation_{t}*", f"pro.sikafinance.com/finance/{t}*"):
            try:
                url = ("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(pat, safe="*/") +
                       "&output=json&fl=timestamp,original,statuscode&filter=statuscode:200&collapse=timestamp:6&limit=200")
                cdx[pat] = json.loads(get(url, tries=2, timeout=60) or b"[]")
                note("probe-wayback")
            except Exception as e:  # noqa: BLE001
                note("probe-wayback", False, f"{pat}: {e}")
            time.sleep(1)
    save(os.path.join(dd, "wayback_cdx.json"), cdx)
    # échantillon d'états financiers (texte extrait) pour l'analyseur des comptes sur 10 exercices
    try:
        evs = harzat_json("events.json")["events"]
        picks = {}
        for e in evs:
            t, fy, u = e.get("ticker"), e.get("fiscal_year"), e.get("document_url") or ""
            if e.get("category") == "financial_statements" and t in ("SNTS", "ORAC", "SLBC", "PALC", "SPHC", "TTLC", "CIEC", "SGBC", "SIBC", "NTLC") and fy in (2017, 2019) and u.lower().endswith(".pdf"):
                picks.setdefault((t, fy), u)
        for (t, fy), u in list(picks.items())[:14]:
            try:
                txt = pdftext(get(u, tries=2, timeout=60))
                open(os.path.join(dd, f"pdf_{t}_{fy}.txt"), "w", encoding="utf8").write(f"{u}\n" + txt[:120000])
                note("probe-pdf", ok=len(txt.strip()) > 200, err=None if len(txt.strip()) > 200 else f"{t} {fy}: texte vide (scan)")
            except Exception as e:  # noqa: BLE001
                note("probe-pdf", False, f"{t} {fy}: {e}")
    except Exception as e:  # noqa: BLE001
        note("probe-pdf", False, e)
    # un instantané ancien de chaque motif trouvé
    for pat, rows in cdx.items():
        rows = [r for r in rows[1:] if r and r[0][:4] in ("2016", "2017", "2018", "2019", "2020")] if rows else []
        if not rows:
            continue
        ts, orig = rows[len(rows) // 2][0], rows[len(rows) // 2][1]
        try:
            b = get(f"http://web.archive.org/web/{ts}id_/{orig}", tries=2, timeout=60)
            open(os.path.join(dd, "wb_" + re.sub(r"\W", "_", pat)[:40] + f"_{ts}.html"), "wb").write(b[:1_500_000])
        except Exception as e:  # noqa: BLE001
            note("probe-wayback", False, f"snapshot {pat}: {e}")
        time.sleep(1)


# ---------------------------------------------------------------- veille : publications BRVM et dépôts SEC (chaque passage)
def norm_name(x):
    import unicodedata
    x = unicodedata.normalize("NFKD", x or "").encode("ascii", "ignore").decode().lower()
    x = re.sub(r"\b(sa|s\.a\.|ci|cote d.?ivoire|cote divoire|senegal|burkina( faso)?|benin|mali|niger|togo|bf|sn|bn|ml|ng|tg|groupe|group|holding|societe|ste)\b", " ", x)
    return re.sub(r"[^a-z0-9]+", " ", x).strip()


def _doc_date(u):
    """Date AAAAMMJJ en tête du nom de fichier d'une publication brvm.org (…/files/20260805_-_…pdf), sinon None."""
    m = re.search(r"/(20\d{6})[_\-]", u or "")
    return m.group(1) if m else None


def _doc_recent(d8, days=30):
    try:
        return bool(d8) and 0 <= (TODAY - dt.date(int(d8[:4]), int(d8[4:6]), int(d8[6:8]))).days <= days
    except ValueError:
        return False


# rubriques « rapports des sociétés cotées » de brvm.org -> titre coté (rapprochement vérifié à la main ; None = émetteur sans action cotée :
# fonds de titrisation, sociétés radiées). Les rubriques inconnues (nouvelles cotations) passent par le rapprochement des noms.
ISSUER_T = {
    "bank-africa-bf": "BOABF", "bank-africa-bn": "BOAB", "bank-africa-ci": "BOAC", "bank-africa-ml": "BOAM", "bank-africa-ng": "BOAN",
    "bank-africa-sn": "BOAS", "ecobank-ci": "ECOC", "ecobank-tg": "ETIT", "sonatel": "SNTS", "total": "TTLC", "total-senegal-sa": "TTLS",
    "totalenergies-marketing-sn": "TTLS", "air-liquide-ci": "SIVC", "bbgci": "BBGC", "bollore-transport-logistics": "SDSC",
    "crown-siem-ci": "SEMC", "lnb": "LNBB", "nsbc": "NSBC", "sgb-ci": "SGBC", "sgci": "SGBC", "sib": "SIBC", "sodeci": "SDCC", "biic": "BICB",
    "coris-bank-international": "CBIBF", "oragroup": "ORGT", "servair-abidjan-ci": "ABJC", "bici-ci": "BICC", "bernabe-ci": "BNBC",
    "sicable": "CABC", "cfao-motors-ci": "CFAC", "cie-ci": "CIEC", "filtisac-ci": "FTSC", "nei-ceda-ci": "NEIC", "nestle-ci": "NTLC",
    "onatel-bf": "ONTBF", "orange-ci": "ORAC", "palm-ci": "PALC", "tractafric-ci": "PRSC", "safca-ci": "SAFC", "sucrivoire": "SCRC",
    "vivo-energy-ci": "SHEC", "sicor": "SICC", "solibra": "SLBC", "smb": "SMBC", "sogb": "SOGC", "saph-ci": "SPHC", "setao-ci": "STAC",
    "sitab": "STBC", "unilever-ci": "UNLC", "uniwax-ci": "UNXC",
    "fctc-sonatel": None, "societe-ivoirienne-de-raffinage": None, "movis-ci": None, "cote-divoire-telecom": None, "tritraf-ci": None,
}
_ISS_GENERIC = {"bank", "africa", "of", "ci", "sa", "s", "a", "cote", "d", "ivoire", "divoire", "group", "groupe", "banque", "senegal", "sn", "bf", "bn", "ml", "ng", "tg", "de", "la", "le", "et"}


def run_watch(raw, site_data):
    """Nouvelles publications des sociétés cotées (brvm.org) et nouveaux 10-K/10-Q (SEC) : actualités + données à jour."""
    path = os.path.join(site_data, "reports.json")
    st = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {"issuers": {}, "docs": {}, "its": 0}
    summ = json.load(open(os.path.join(site_data, "summary.json"), encoding="utf8")) if os.path.exists(os.path.join(site_data, "summary.json")) else {"secs": []}
    brvm = [x for x in summ.get("secs", []) if x.get("mkt") == "BRVM" and x.get("cls") == "Equity"]
    if not st["issuers"] or time.time() - st.get("its", 0) > 86400:
        iss = {}
        for pg in range(0, 10):  # (30 sociétés par page ; arrêt à la première page vide)
            try:
                html = get("https://www.brvm.org/fr/rapports-societes-cotees" + (f"?page={pg}" if pg else ""), tries=2, timeout=30).decode("utf8", "replace")
            except Exception as e:  # noqa: BLE001
                note("watch-brvm", False, f"liste p{pg}: {e}")
                break
            found = re.findall(r'href="(?:https://www\.brvm\.org)?/fr/rapports-societe-cotes/([a-z0-9\-]+)"[^>]*>([^<]+)</a>', html)
            if not found:
                break
            for slug, name in found:
                iss[slug] = {"n": re.sub(r"\s+", " ", name).strip()}
        if iss:
            st["issuers"], st["its"] = iss, int(time.time())
    known_t = {v for v in ISSUER_T.values() if v}
    for slug, x in st["issuers"].items():  # rapprochement rubrique -> ticker, refait à chaque passage
        x["n"] = re.sub(r"\s+", " ", HTML.unescape(HTML.unescape(x.get("n") or ""))).strip()
        if slug in ISSUER_T:
            x["t"] = ISSUER_T[slug]
            continue
        a = set(norm_name(x["n"] + " " + slug.replace("-", " ")).split()) - _ISS_GENERIC
        best = None
        for s in brvm:
            if s["id"] in known_t:
                continue
            b = set(norm_name((s.get("n") or "") + " " + (s.get("short") or "")).split()) - _ISS_GENERIC
            sc = len(a & b) / max(1, len(a | b))
            if a & b and sc > (best[0] if best else 0.5):
                best = (sc, s["id"])
        x["t"] = best[1] if best else None
    fresh = []

    def one(slug):
        try:
            html = get(f"https://www.brvm.org/fr/rapports-societe-cotes/{slug}", tries=2, timeout=30).decode("utf8", "replace")
        except Exception as e:  # noqa: BLE001
            return slug, None, str(e)
        rows = []
        for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", html, re.S):
            cell = m.group(1)
            u = re.search(r'href="([^"]+\.pdf)"', cell)
            if not u:
                continue
            title = re.sub(r"<[^>]+>", " ", cell)
            title = re.sub(r"\s+", " ", HTML.unescape(HTML.unescape(title))).replace("\xa0", " ").replace("Télécharger", "").strip()
            url = u.group(1) if u.group(1).startswith("http") else "https://www.brvm.org" + u.group(1)
            dm = re.search(r"/(20\d{6})", url)
            rows.append({"d": dm.group(1) if dm else None, "ti": title[:200], "u": url})
        return slug, rows, None
    # une publication n'est « nouvelle » que si son adresse n'a jamais été vue ET si elle est datée de moins de 30 jours
    # (les pages de brvm.org ne sont pas triées : d'anciens rapports y réapparaissent régulièrement)
    seen_u = set(st.get("seen") or [])
    for rows_ in st["docs"].values():  # titres relevés avant le décodage des entités HTML (« d&#039;activités »)
        for r_ in rows_:
            r_["ti"] = re.sub(r"\s+", " ", HTML.unescape(HTML.unescape(r_.get("ti") or ""))).replace("\xa0", " ").strip()
    with ThreadPoolExecutor(8) as ex:
        for slug, rows, err in ex.map(one, list(st["issuers"])):
            if rows is None:
                note("watch-brvm", False, f"{slug}: {err}")
                continue
            note("watch-brvm")
            prev = st["docs"].get(slug)
            known = {r["u"] for r in (prev or [])} | seen_u
            if prev is not None:
                fresh += [dict(r, slug=slug) for r in rows if r["u"] not in known and _doc_recent(r.get("d"))]
            merged = {r["u"]: r for r in (prev or [])}
            merged.update({r["u"]: r for r in rows})
            st["docs"][slug] = sorted(merged.values(), key=lambda r: r.get("d") or "", reverse=True)[:60]
            seen_u.update(r["u"] for r in rows)
    st["seen"] = sorted(seen_u)[-20000:]
    st["ts"] = int(time.time())
    # dépôts SEC récents (10-K, 10-Q, 20-F, 6-K) des sociétés suivies
    sec_new = []
    facts_p = os.path.join(raw, "secfacts.json")
    co = (json.load(open(facts_p, encoding="utf8")).get("co") or {}) if os.path.exists(facts_p) else {}
    cik2t = {int(v["cik"]): t for t, v in co.items() if v.get("cik")}
    seen = set(st.get("sec_seen", []))
    h = {"User-Agent": SEC_UA, "Accept-Encoding": "gzip"}
    for form in ("10-Q", "10-K", "20-F", "6-K", "8-K"):
        try:
            x = get(f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type={form}&company=&dateb=&owner=include&start=0&count=100&output=atom", headers=h, tries=2, timeout=30).decode("utf8", "replace")
        except Exception as e:  # noqa: BLE001
            note("watch-sec", False, f"{form}: {e}")
            continue
        note("watch-sec")
        for ent in re.findall(r"<entry>(.*?)</entry>", x, re.S):
            t_ = re.search(r"<title>([^<]+)</title>", ent)
            l_ = re.search(r'<link[^>]+href="([^"]+)"', ent)
            c_ = re.search(r"\((\d{10})\)", t_.group(1) if t_ else "")
            if not (t_ and c_):
                continue
            cik = int(c_.group(1))
            key = (l_.group(1) if l_ else t_.group(1))
            if cik in cik2t and key not in seen:
                seen.add(key)
                sec_new.append({"t": cik2t[cik], "form": form, "ti": t_.group(1), "u": l_.group(1) if l_ else ""})
    st["sec_seen"] = sorted(seen)[-500:]
    save(path, st)
    # actualités : publications officielles
    np_ = os.path.join(site_data, "news.json")
    news = json.load(open(np_, encoding="utf8")) if os.path.exists(np_) else {"items": [], "feeds": {}}
    now = int(time.time())
    n0 = len(news["items"])  # nettoyage : anciens rapports signalés à tort comme nouveaux
    news["items"] = [x for x in news["items"] if x.get("f") != "brvm-rapports" or _doc_recent(_doc_date(x.get("u")))]
    for r in fresh:
        tk = st["issuers"].get(r["slug"], {}).get("t")
        d8 = r.get("d")
        t_pub = now if d8 and (TODAY - dt.date(int(d8[:4]), int(d8[4:6]), int(d8[6:]))).days <= 1 else int(dt.datetime(int(d8[:4]), int(d8[4:6]), int(d8[6:]), 12, tzinfo=dt.timezone.utc).timestamp())
        news["items"].insert(0, {"t": t_pub, "ti": HTML.unescape(r["ti"]), "u": r["u"], "s": "brvm.org", "c": "BRVM", "f": "brvm-rapports", "x": f"Publication officielle du {d8[6:]}/{d8[4:6]}/{d8[:4]}{(' · ' + tk) if tk else ''}"})
    news["items"].sort(key=lambda x: -(x.get("t") or 0))
    if len(news["items"]) != n0 and not (fresh or sec_new):
        save(np_, news)
    for r in sec_new:
        news["items"].insert(0, {"t": now, "ti": f"Dépôt SEC {r['form']} : {r['ti']}", "u": r["u"], "s": "SEC EDGAR", "c": "Tech US", "f": "sec", "x": r["t"]})
    if fresh or sec_new:
        news["feeds"]["brvm-rapports"], news["feeds"]["sec"] = "brvm.org", "SEC EDGAR"
        save(np_, news)
    # états financiers publiés à l'instant : comptes lus tout de suite (si pdftotext est disponible)
    import shutil
    newfs = [r for r in fresh if re.search(r"etats? financiers", _nrm(r["ti"])) and st["issuers"].get(r["slug"], {}).get("t")]
    if newfs and not shutil.which("pdftotext"):
        os.system("sudo apt-get install -y -qq poppler-utils >/dev/null 2>&1")
    if newfs and shutil.which("pdftotext"):
        pp = os.path.join(raw, "pdf_fin.json")
        db = json.load(open(pp, encoding="utf8")) if os.path.exists(pp) else {"t": {}, "docs": {}}
        for r in newfs:
            t = st["issuers"][r["slug"]]["t"]
            m = re.search(r"(20\d\d)", re.sub(r"^.*exercice", "", _nrm(r["ti"])))
            if not m:
                continue
            fy = int(m.group(1))
            try:
                found, unit = fin_parse(pdftext(get(r["u"], tries=2, timeout=60)))
                tt = db["t"].get(t, {})
                ref = None
                for yy in sorted(tt, reverse=True):
                    if tt[yy].get("rev"):
                        ref = tt[yy]["rev"]
                        break
                div_ = fin_scale(found, unit, ref)
                if found and div_:
                    cur, prev = fin_record(found, div_)
                    db["t"].setdefault(t, {})[str(fy)] = dict(cur, src=r["u"])
                    db["t"][t].setdefault(str(fy - 1), dict(prev, src=r["u"]))
                    db["docs"][r["u"]] = "ok"
                    note("watch-pdf")
            except Exception as e:  # noqa: BLE001
                note("watch-pdf", False, f"{t}: {e}")
        save(pp, db)
        open(os.path.join(raw, ".dirty"), "a").write(" pdf")
    # comptes SEC rafraîchis tout de suite pour les sociétés qui viennent de déposer
    dirty = sorted({r["t"] for r in sec_new if r["form"] in ("10-Q", "10-K", "20-F", "6-K")})
    if dirty and co:
        h2 = {"User-Agent": SEC_UA, "Accept-Encoding": "gzip", "Accept": "application/json"}
        allf = json.load(open(facts_p, encoding="utf8"))
        for t in dirty:
            try:
                cik = allf["co"][t]["cik"]
                j = json.loads(get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json", headers=h2, timeout=90))
                r = sec_company(cik, t, j)
                if r:
                    allf["co"][t] = r
                    note("watch-sec-refresh")
            except Exception as e:  # noqa: BLE001
                note("watch-sec-refresh", False, f"{t}: {e}")
            time.sleep(0.3)
        save(facts_p, allf)
        open(os.path.join(raw, ".dirty"), "w").write(" ".join(dirty))
    log(f"veille : {len(fresh)} publications BRVM, {len(sec_new)} dépôts SEC, comptes rafraîchis : {dirty}")


# ---------------------------------------------------------------- actualités (RSS)
NEWS = [  # id, libellé, url, catégorie
    ("gn-brvm", "Google Actualités", "https://news.google.com/rss/search?q=BRVM&hl=fr&gl=FR&ceid=FR:fr", "BRVM"),
    ("gn-bourse-abidjan", "Google Actualités", "https://news.google.com/rss/search?q=%22Bourse+r%C3%A9gionale%22+OR+%22bourse+d%27Abidjan%22+OR+Sonatel+OR+%22Orange+C%C3%B4te+d%27Ivoire%22+OR+SGBCI+OR+%22Ecobank+Transnational%22&hl=fr&gl=FR&ceid=FR:fr", "BRVM"),
    ("gn-uemoa", "Google Actualités", "https://news.google.com/rss/search?q=BCEAO+OR+UEMOA+OR+%22UMOA-Titres%22&hl=fr&gl=FR&ceid=FR:fr", "UEMOA"),
    ("financialafrik", "Financial Afrik", "https://www.financialafrik.com/feed/", "Afrique"),
    ("allafrica-eco", "allAfrica", "https://fr.allafrica.com/tools/headlines/rdf/business/headlines.rdf", "Afrique"),
    ("ecofin", "Agence Ecofin", "https://news.google.com/rss/search?q=site:agenceecofin.com+finance+OR+banque+OR+bourse&hl=fr&gl=FR&ceid=FR:fr", "Afrique"),  # (flux du site fermé)
    ("gn-marches", "Google Actualités", "https://news.google.com/rss/search?q=%22march%C3%A9s+financiers%22+OR+%22Wall+Street%22+OR+%22CAC+40%22&hl=fr&gl=FR&ceid=FR:fr", "Marchés"),
    ("lesechos", "Les Echos", "https://news.google.com/rss/search?q=site:lesechos.fr+march%C3%A9s+OR+bourse+OR+finance&hl=fr&gl=FR&ceid=FR:fr", "Marchés"),  # (flux du site refusé)
    ("investing-fr", "Investing.com", "https://fr.investing.com/rss/news.rss", "Marchés"),
    ("cnbc-markets", "CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258", "Marchés"),
    ("cnbc-top", "CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "Marchés"),
    ("marketwatch", "MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories", "Marchés"),
    ("yahoo", "Yahoo Finance", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EIXIC,%5EDJI&region=US&lang=en-US", "Marchés"),
    ("gn-tech", "Google Actualités", "https://news.google.com/rss/search?q=Nasdaq+OR+Nvidia+OR+semiconductors+stocks&hl=en-US&gl=US&ceid=US:en", "Tech US"),
    ("fed", "Réserve fédérale", "https://www.federalreserve.gov/feeds/press_all.xml", "Banques centrales"),
    ("ecb", "BCE", "https://www.ecb.europa.eu/rss/press.html", "Banques centrales"),
    ("gn-bceao", "Google Actualités", "https://news.google.com/rss/search?q=BCEAO+taux+directeur+OR+%22politique+mon%C3%A9taire%22+BCEAO&hl=fr&gl=FR&ceid=FR:fr", "Banques centrales"),
    ("gn-matieres", "Google Actualités", "https://news.google.com/rss/search?q=cacao+OR+%22prix+du+p%C3%A9trole%22+OR+%22cours+de+l%27or%22&hl=fr&gl=FR&ceid=FR:fr", "Matières premières"),
]


def parse_feed(b):
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    b = re.sub(rb"^\s+", b"", b)
    root = ET.fromstring(b)
    items = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        g = {}
        for ch in it:
            ct = ch.tag.split("}")[-1]
            if ct == "link" and ch.get("href"):
                g.setdefault("link", ch.get("href"))
            elif ct in ("title", "link", "pubDate", "published", "updated", "date", "description", "summary", "source"):
                g.setdefault(ct, (ch.text or "").strip())
        t = None
        for k in ("pubDate", "published", "updated", "date"):
            if g.get(k):
                try:
                    t = parsedate_to_datetime(g[k])
                except Exception:  # noqa: BLE001
                    try:
                        t = dt.datetime.fromisoformat(g[k].replace("Z", "+00:00"))
                    except Exception:  # noqa: BLE001
                        t = None
                if t:
                    break
        if not g.get("title") or not t:
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=dt.timezone.utc)
        title = re.sub(r"\s+", " ", g["title"])
        src = g.get("source") or ""
        if "news.google" in (g.get("link") or "") and " - " in title:
            head, tail = title.rsplit(" - ", 1)
            if not src or tail.strip() == src.strip():
                title, src = head, src or tail
        desc = re.sub(r"<[^>]+>", " ", g.get("description") or g.get("summary") or "")
        desc = re.sub(r"\s+", " ", desc).strip()[:280]
        items.append({"t": int(t.timestamp()), "ti": title[:300], "u": g.get("link"), "s": src[:60], "x": desc if desc and desc[:60] not in title else ""})
    return items


# flux de secours, sans intervention : si l'adresse directe d'un site ne répond plus (erreur ou flux vide), ses articles sont repris
# par la recherche Google Actualités limitée à ce site
NEWS_FALLBACK = {"financialafrik": ("financialafrik.com", "fr"), "allafrica-eco": ("allafrica.com", "fr"), "investing-fr": ("fr.investing.com", "fr"),
                 "cnbc-markets": ("cnbc.com", "en"), "cnbc-top": ("cnbc.com", "en"), "marketwatch": ("marketwatch.com", "en"),
                 "yahoo": ("finance.yahoo.com", "en"), "fed": ("federalreserve.gov", "en"), "ecb": ("ecb.europa.eu", "en")}


def _gn_site(dom, lang):
    q = urllib.parse.quote(f"site:{dom}")
    return (f"https://news.google.com/rss/search?q={q}&hl=fr&gl=FR&ceid=FR:fr" if lang == "fr"
            else f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en")


def run_news(path):
    old = []
    if os.path.exists(path):
        try:
            old = json.load(open(path, encoding="utf8")).get("items", [])
        except Exception:  # noqa: BLE001
            old = []
    seen, items = set(), []

    def one(f):
        fid, label, url, cat = f
        urls = [url] + ([_gn_site(*NEWS_FALLBACK[fid])] if fid in NEWS_FALLBACK else [])
        err = None
        for u_ in urls:
            try:
                its = parse_feed(get(u_, tries=2, timeout=25, headers={"Accept": "application/rss+xml, application/xml, text/xml, */*"}))
                if not its:
                    raise ValueError("flux vide")
                for x in its:
                    x["c"] = cat
                    x["f"] = fid
                    x["s"] = x["s"] or label
                note("news")
                if u_ != url:
                    note("news-secours", False, f"{fid}: adresse directe en échec ({err}), flux de secours utilisé")
                return its
            except Exception as e:  # noqa: BLE001
                err = e
        note("news", False, f"{fid}: {err}")
        return []
    with ThreadPoolExecutor(6) as ex:
        fresh = [x for lst in ex.map(one, NEWS) for x in lst]
    cutoff = time.time() - 45 * 86400
    import unicodedata
    seen_u = set()
    for x in sorted(fresh + old, key=lambda x: -x["t"]):
        # doublons : même titre (accents composés ou non, entités HTML) ou même article (adresse), titre révisé compris
        x["ti"] = re.sub(r"\s+", " ", HTML.unescape(x.get("ti") or "")).strip()
        k = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", x["ti"]).encode("ascii", "ignore").decode().lower())[:90]
        u = re.sub(r"(?<=[?&])(?:utm_\w+|mod)=[^&]*&?", "", (x.get("u") or "").split("#")[0]).rstrip("?&")  # paramètres de suivi seulement
        if k in seen or (u and u in seen_u) or x["t"] < cutoff or x["t"] > time.time() + 3600:
            continue
        seen.add(k)
        if u:
            seen_u.add(u)
        items.append(x)
    items = tag_news(items[:900], os.path.join(os.path.dirname(path), "summary.json"))
    save(path, {"ts": int(time.time()), "items": items, "feeds": {f[0]: f[1] for f in NEWS}})


# ---------------------------------------------------------------- profils des sociétés BRVM (SikaFinance, page « Société »)
def _sika_profile(h):
    """Description, coordonnées, dirigeants, titres, flottant, actionnaires et chiffres clés d'une page société SikaFinance."""
    import html as H_
    o = {}
    m = re.search(r"\b([A-Z]{2}[0-9A-Z]{9}[0-9])\b - [A-Z]{3,6}", h)
    if m:
        o["isin"] = m.group(1)
    m = re.search(r'id="lstActionnaires"[^>]*>(.*?)</span>', h, re.S)
    if m:
        hold = []
        for part in H_.unescape(m.group(1)).split(";"):
            if "*" in part:
                nm, pc = part.rsplit("*", 1)
                try:
                    hold.append([nm.strip(), float(pc.replace(",", ".").strip())])
                except ValueError:
                    pass
        o["holders"] = hold
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
    t = H_.unescape(re.sub(r"<[^>]+>", "\n", t)).replace("\xa0", " ")
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    flat = re.sub(r"\s*\n\s*", "\n", t)
    one = re.sub(r"\s+", " ", t)
    m = re.search(r"La société :\s*(.*?)\s*(?:Téléphone|Telephone|Adresse|Dirigeants)\s*:", one)
    if m:
        o["desc"] = m.group(1).strip()[:2500]
    for k, lab in (("tel", "Téléphone"), ("fax", "Fax"), ("addr", "Adresse")):
        m = re.search(lab + r"\s*:\s*(.*?)\s*(?:Fax|Adresse|Dirigeants|Nombre de titres)\s*:", one)
        if m and m.group(1).strip():
            o[k] = m.group(1).strip()[:200]
    m = re.search(r"Dirigeants\s*:\s*(.*?)\s*Nombre de titres", flat, re.S)
    if m:
        mg = []
        for line in m.group(1).split("\n"):
            if ":" in line:
                r_, n_ = line.split(":", 1)
                if r_.strip() and n_.strip():
                    mg.append([r_.strip(), n_.strip()])
        if not mg:  # tout sur une ligne
            for r_, n_ in re.findall(r"([A-ZÉ][^:]{3,60}?)\s*:\s*([A-ZÉÈ][A-Za-zÀ-ÿ'’\-\. ]{2,60}?)(?=\s+[A-ZÉ][a-zé]|$)", re.sub(r"\s+", " ", m.group(1))):
                mg.append([r_.strip(), n_.strip()])
        o["mgmt"] = mg[:8]
    def numfr(x):
        try:
            return float(re.sub(r"[^0-9,\-]", "", x).replace(",", "."))
        except ValueError:
            return None
    m = re.search(r"Nombre de titres\s*:\s*([\d  .]+)", one)
    if m:
        o["shares"] = numfr(m.group(1))
    m = re.search(r"Flottant\s*:\s*([\d,]+)\s*%", one)
    if m:
        o["float"] = numfr(m.group(1))
    m = re.search(r"Valorisation de la société\s*:\s*([\d  .]+)\s*MFCFA", one)
    if m:
        o["val_m"] = numfr(m.group(1))
    tb = re.search(r'<table[^>]*tabSociete[^>]*>(.*?)</table>', h, re.S)
    if tb:
        cells = lambda r: [re.sub(r"\s+", " ", H_.unescape(re.sub(r"<[^>]+>", " ", c))).replace("\xa0", " ").strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
        rows = [cells(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tb.group(1), re.S)]
        years = [c for c in (rows[0][1:] if rows else []) if re.fullmatch(r"20\d\d", c)]
        keys = {"Chiffre d'affaires": "ca", "Croissance CA": "g_ca", "Résultat net": "rn", "Croissance RN": "g_rn", "BNPA": "bnpa", "PER": "per", "Dividende": "dps"}
        kf = {}
        for r in rows[1:]:
            k = keys.get(r[0].strip()) if r else None
            if not k:
                continue
            kf[k] = {y: numfr(v.replace(" ", "").replace("%", "")) for y, v in zip(years, r[1:]) if v and v.strip() not in ("-", "")}
            kf[k] = {y: v for y, v in kf[k].items() if v is not None}
        o["kf"] = kf
    return o


def run_prof(out):
    path = os.path.join(out, "profiles.json")
    db = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {}
    try:
        fund = harzat_json("fundamentals.json")
    except Exception as e:  # noqa: BLE001
        note("prof", False, f"fundamentals: {e}")
        return
    todo = [(t, v.get("source_url")) for t, v in fund.items() if t != "_meta" and v.get("source_url") and "sikafinance" in v.get("source_url", "")]
    def one(tu):
        t, url = tu
        url = url.replace("http://", "https://")
        try:
            h = get(url, tries=2, timeout=30, headers={"Accept-Language": "fr-FR,fr;q=0.9"}).decode("utf8", "replace")
        except Exception:  # noqa: BLE001
            try:
                h = curl(url, ua=UA)
                h = h.decode("utf8", "replace") if isinstance(h, bytes) else h
            except Exception as e:  # noqa: BLE001
                return t, None, str(e)
        if "lstActionnaires" not in h and "La société" not in h:
            return t, None, "page sans profil"
        return t, _sika_profile(h), url
    with ThreadPoolExecutor(4) as ex:
        for t, o, info in ex.map(one, todo):
            if o is None:
                note("prof", False, f"{t}: {info}")
                continue
            o["src"] = info
            o["d"] = TODAY.isoformat()
            db[t] = o
            note("prof")
    save(path, db)


def run_profus(out):
    """Fiches des sociétés et ETF US : description et site (Nasdaq), résumé (objectif à 1 an, dividende, encours et frais des ETF),
    principaux détenteurs institutionnels (déclarations 13F agrégées par Nasdaq), adresse et exercice (SEC)."""
    path = os.path.join(out, "profiles_us.json")
    db = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {}
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cik = json.load(open(os.path.join(root, "seed", "sec_cik.json"), encoding="utf8"))
    etfs = [t for t, _, ty, _ in US if ty == "ETF"]
    def dv(d, k):
        v = (d.get(k) or {}).get("value") if isinstance(d.get(k), dict) else None
        return None if v in (None, "", "N/A") else v
    def nq(url):
        return json.loads(get(url, tries=2, timeout=25, headers=NQ_H)).get("data") or {}
    def one(t, kind):
        o = {"d": TODAY.isoformat()}
        try:
            sm = (nq(f"https://api.nasdaq.com/api/quote/{t}/summary?assetclass={kind}").get("summaryData")) or {}
            for k, key in (("OneYrTarget", "tgt"), ("AverageVolume", "avgvol"), ("AnnualizedDividend", "divA"), ("ExDividendDate", "exdiv"), ("DividendPaymentDate", "paydiv"),
                           ("Yield", "yld"), ("Exchange", "exch"), ("Sector", "sector"), ("Industry", "ind"), ("AUM", "aum"), ("ExpenseRatio", "er"), ("Beta", "beta"), ("MarketCap", "mcap")):
                v = dv(sm, k)
                if v is not None:
                    o[key] = v
        except Exception as e:  # noqa: BLE001
            o["err_sum"] = str(e)[:120]
        if kind == "stocks":
            try:
                pr = nq(f"https://api.nasdaq.com/api/company/{t}/company-profile")
                for k, key in (("CompanyDescription", "desc"), ("CompanyUrl", "url"), ("Sector", "sector"), ("Industry", "ind"), ("Region", "region")):
                    v = dv(pr, k)
                    if v is not None:
                        o[key] = v
            except Exception as e:  # noqa: BLE001
                o["err_prof"] = str(e)[:120]
            try:
                ih = nq(f"https://api.nasdaq.com/api/company/{t}/institutional-holdings?limit=15&type=TOTAL&sortColumn=marketValue")
                osum = ih.get("ownershipSummary") or {}
                rows = (((ih.get("holdingsTransactions") or {}).get("table") or {}).get("rows")) or []
                o["inst"] = {"pct": dv(osum, "SharesOutstandingPCT"), "sh_m": dv(osum, "ShareoutstandingTotal"), "n": (ih.get("holdingsTransactions") or {}).get("totalRecords"),
                             "rows": [[r.get("ownerName"), r.get("date"), r.get("sharesHeld"), r.get("sharesChange"), r.get("sharesChangePCT"), r.get("marketValue")] for r in rows[:15]],
                             "pos": [[r.get("positions"), r.get("holders"), r.get("shares")] for r in ((ih.get("activePositions") or {}).get("rows") or [])]}
            except Exception as e:  # noqa: BLE001
                o["err_inst"] = str(e)[:120]
            if t in cik:
                try:
                    sb = json.loads(get(f"https://data.sec.gov/submissions/CIK{int(cik[t]):010d}.json", tries=2, timeout=30, headers={"User-Agent": SEC_UA, "Accept-Encoding": "gzip"}))
                    a_ = (sb.get("addresses") or {}).get("business") or {}
                    o["addr"] = ", ".join(x for x in (a_.get("street1"), a_.get("street2"), a_.get("city"), a_.get("stateOrCountryDescription"), a_.get("zipCode")) if x)
                    o["phone"] = sb.get("phone")
                    o["fye"] = sb.get("fiscalYearEnd")
                    o["sic"] = sb.get("sicDescription")
                    o["inc"] = sb.get("stateOfIncorporation")
                except Exception as e:  # noqa: BLE001
                    o["err_sec"] = str(e)[:120]
        return t, o
    jobs = [(t, "stocks") for t in cik] + [(t, "etf") for t in etfs]
    t_end = time.time() + 540
    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(one, t, k) for t, k in jobs]
        for f in futs:
            try:
                t, o = f.result(timeout=max(1, t_end - time.time()))
            except Exception as e:  # noqa: BLE001
                note("profus", False, str(e)[:100])
                continue
            if any(k in o for k in ("desc", "tgt", "aum", "inst")):
                o["src"] = "nasdaq.com" + (" · sec.gov" if "addr" in o else "")
                db[t] = o
                note("profus")
            else:
                note("profus", False, f"{t}: vide")
    save(path, db)

# ---------------------------------------------------------------- BCEAO : bulletin mensuel des statistiques (PDF), taux directeurs
FR_MON = {"janv": 1, "jan": 1, "fev": 2, "févr": 2, "fevr": 2, "mars": 3, "mar": 3, "avr": 4, "avril": 4, "mai": 5, "juin": 6, "juil": 7, "juillet": 7, "aout": 8, "août": 8,
          "sept": 9, "sep": 9, "oct": 10, "nov": 11, "dec": 12, "déc": 12}


def _frnum(x):
    try:
        return float(x.replace(" ", "").replace("\xa0", "").replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def _mon_key(lab):
    """« août-26 », « juil.-26 », « Mar-2026 », « 2025 » -> AAAA-MM ou AAAA."""
    t = lab.strip().lower().replace(".", "")
    m = re.match(r"^(20\d\d)$", t)
    if m:
        return m.group(1)
    m = re.match(r"^([a-zéû]+)-?\s*(\d{2,4})$", t)
    if m:
        mo = FR_MON.get(m.group(1)[:5]) or FR_MON.get(m.group(1)[:4]) or FR_MON.get(m.group(1)[:3])
        y = int(m.group(2))
        y = y + 2000 if y < 100 else y
        if mo:
            return f"{y}-{mo:02d}"
    return None


def parse_bceao_bulletin(txt):
    """Tables du bulletin mensuel : taux directeurs, inflation par pays, crédits et taux bancaires, agrégats par pays,
    indicateurs d'activité, émissions de titres publics. Valeurs telles que publiées (pourcentages et milliards de FCFA)."""
    L = txt.split("\n")
    out = {}

    def find(pat, start=0):
        for i in range(start, len(L)):
            if re.search(pat, L[i]):
                return i
        return None
    # taux directeurs (historique des modifications)
    i = find(r"2\.2\.1\.1\.? *- *Taux directeurs")
    if i is not None:
        hist = []
        for ln in L[i:i + 60]:
            m = re.match(r"^\s*(20\d\d)\s+(\d{1,2})-([a-zéû]+)\.?\s+(-?\d+,\d+)\s+(-?\d+,\d+)\s+(-?\d+,\d+)\s+(-?\d+,\d+)", ln)
            if m:
                mo = FR_MON.get(m.group(3)[:4]) or FR_MON.get(m.group(3)[:3])
                hist.append({"d": f"{m.group(1)}-{mo:02d}-{int(m.group(2)):02d}" if mo else m.group(1), "pret": _frnum(m.group(4)), "min": _frnum(m.group(6))})
            if hist and re.search(r"Source", ln):
                break
        out["policy"] = hist
    # taux moyens du marché monétaire (adjudications mensuelles)
    i = find(r"2\.2\.1\.2\.? *- *Taux et montants de refinancement")
    if i is not None:
        mm = []
        for ln in L[i:i + 200]:
            m = re.match(r"^\s*([A-Za-zéû]+\.?-20\d\d)\s+(\d+,\d+)\s+([\d  ]+,\d+)", ln)
            if m:
                mm.append({"m": _mon_key(m.group(1).replace("-20", "-")), "t": _frnum(m.group(2)), "ref": _frnum(m.group(3))})
            if re.search(r"^\s*2\.2\.2", ln):
                break
        out["mm"] = mm
    # inflation par pays
    i = find(r"Tableau 2\.3\.2\.1")
    if i is not None:
        hdr = None
        rows = {}
        for ln in L[i + 1:i + 40]:
            toks = ln.split()
            if not hdr and len(toks) >= 5 and all(_mon_key(t) for t in toks):
                hdr = [_mon_key(t) for t in toks]
                continue
            m = re.match(r"^\s*([A-Za-zéèô' \-]+?)\s{2,}(-?\d+,\d.*)$", ln)
            if hdr and m:
                vals = [_frnum(v) for v in m.group(2).split()]
                if len(vals) == len(hdr):
                    rows[m.group(1).strip()] = dict(zip(hdr, vals))
            if rows and re.search(r"Sources?", ln):
                break
        out["infl"] = rows
    # crédits et dépôts bancaires
    i = find(r"Tableau 2\.2\.2\.3\.1")
    if i is not None:
        hdr = None
        rows = {}
        sec_, sub = "credits", "vol"
        for ln in L[i + 1:i + 45]:
            toks = ln.split()
            ks = [_mon_key(t) for t in toks]
            if not hdr and sum(1 for k in ks if k) >= 5:
                hdr = [k for k in ks if k]
                continue
            if re.search(r"Nouveaux dépôts", ln):
                sec_, sub = "depots", "vol"
            if re.search(r"Volume", ln):
                sub = "vol"
            elif re.search(r"Taux d.intérêt moyen", ln):
                sub = "taux"
            elif re.search(r"Durée moyenne", ln):
                sub = "duree"
            elif re.search(r"Marge moyenne", ln):
                sec_, sub = "marge", "taux"
            m = re.match(r"^\s*(.+?)\s{2,}(-?[\d  ]*\d,\d+(?:\s+-?[\d  ]*\d,\d+)+)\s*$", ln)
            if hdr and m:
                vals = re.findall(r"-?\d{1,3}(?: \d{3})*,\d+", m.group(2))
                lab = re.sub(r"^[-(A-B)\s–]+", "", m.group(1)).strip()
                if len(vals) == len(hdr):
                    rows[f"{sec_}.{sub}.{lab}"] = dict(zip(hdr, [_frnum(v) for v in vals]))
            if rows and re.search(r"^Source", ln.strip()):
                break
        out["credit"] = rows
    # agrégats de monnaie par pays
    i = find(r"Tableau 2\.1\.1 – Agrégats de monnaie|2\.1\.1 – Agrégats de monnaie")
    if i is not None:
        cty = ["Bénin", "Burkina", "Côte d'Ivoire", "Guinée-Bissau", "Mali", "Niger", "Sénégal", "Togo", "Union"]
        m0 = re.search(r"à fin ([a-zéû]+) (20\d\d)", " ".join(L[i:i + 3]))
        rows = {}
        for ln in L[i:i + 70]:
            m = re.match(r"^\s*(Masse monétaire \(M2\)|M1|Circulation fiduciaire|Créances sur les autres secteurs|Créances nettes sur l'Administration Centrale|Actifs extérieurs nets|Créances intérieures)\s+(.+)$", ln)
            if m and m.group(1) not in rows:
                vals = re.findall(r"-?\d{1,3}(?: \d{3})*,\d+", m.group(2))
                if len(vals) == 9:
                    rows[m.group(1)] = dict(zip(cty, [_frnum(v) for v in vals]))
        out["money"] = {"asof": f"{m0.group(2)}-{FR_MON.get(m0.group(1)[:4]) or FR_MON.get(m0.group(1)[:3]):02d}" if m0 else None, "rows": rows}
    # activité
    i = find(r"Tableau 2\.3\.1\.1")
    if i is not None:
        hdr = None
        rows = {}
        name = []
        for ln in L[i + 1:i + 40]:
            toks = ln.split()
            ks = [_mon_key(t.replace("(*)", "")) for t in toks if t != "(*)"]
            if not hdr and len(ks) >= 5 and all(ks):
                hdr = ks
                continue
            vals = re.findall(r"-?\d+,\d+", ln)
            lab = re.sub(r"\(\*+\)", "", re.sub(r"-?\d+,\d+", "", ln)).strip()
            if lab and not vals:
                name.append(lab)
            if hdr and len(vals) == len(hdr):
                rows[" ".join(name + ([lab] if lab else [])).strip() or f"ligne {len(rows) + 1}"] = dict(zip(hdr, [_frnum(v) for v in vals]))
                name = []
            if rows and re.search(r"^Source", ln.strip()):
                break
        labs = ["Production industrielle", "Chiffre d'affaires du commerce", "Chiffre d'affaires des services marchands", "Services financiers"]
        out["act"] = {labs[k] if len(rows) == 4 else n: v for k, (n, v) in enumerate(rows.items())}
    # émissions de bons et obligations du Trésor par appel public à l'épargne
    i = find(r"2\.2\.5\.1\.1 – Marché des titres de créances négociables")
    if i is not None:
        em = []
        for ln in L[i:i + 260]:
            m = re.match(r"^\s*- (Bons|Obligations) du Trésor (?:de la |du |de l'|des |d')?(.+?)(?: \((?:simultanée|Simultanée)\s*\))?\s{2,}([\d ]+)\s{2,}(\d{1,2} [a-zéû]+ 20\d\d)\s+(\d+)\s+(\d{1,2} [a-zéû]+ 20\d\d)\s+(\d+,\d+|multiples)", ln)
            if m:
                em.append({"k": m.group(1), "c": m.group(2).strip(), "amt": _frnum(m.group(3)), "d": m.group(4), "mois": int(m.group(5)), "ech": m.group(6), "t": _frnum(m.group(7)) if m.group(7) != "multiples" else None})
            if em and re.search(r"^\s*2\.2\.5\.1\.2", ln):
                break
        out["issues"] = em
    return out


def run_bceao(out):
    path = os.path.join(out, "bceao.json")
    db = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {}
    try:
        home = get("https://www.bceao.int/fr", tries=2, timeout=40).decode("utf8", "replace")
    except Exception as e:  # noqa: BLE001
        note("bceao", False, f"accueil : {e}")
        return
    # taux directeurs affichés sur l'accueil (« Principaux indicateurs et taux directeurs »)
    t = re.sub(r"<[^>]+>", " ", home)
    t = re.sub(r"\s+", " ", t)
    m = re.search(r"Taux minimum de soumission[^0-9]{0,80}(\d+,\d+)\s*%.{0,300}?prêt marginal[^0-9]{0,80}(\d+,\d+)\s*%", t) or re.search(r"(\d+,\d+)\s*%\s*Taux minimum de soumission.{0,200}?(\d+,\d+)\s*%\s*Taux (?:du guichet )?de prêt marginal", t)
    if m:
        db["home"] = {"min": _frnum(m.group(1)), "pret": _frnum(m.group(2)), "d": TODAY.isoformat()}
    m = re.search(r'href="([^"]*Bulletin(?:%20| )mensuel(?:%20| )des(?:%20| )statistiques[^"]*\.pdf)"', home, re.I)
    if not m:
        note("bceao", False, "lien du bulletin introuvable")
        save(path, db)
        return
    url = m.group(1)
    url = url if url.startswith("http") else "https://www.bceao.int" + url
    lab = urllib.parse.unquote(url).rsplit("-", 1)[-1].replace(".pdf", "").strip()
    if db.get("url") == url and db.get("infl"):
        note("bceao")
        save(path, db)
        return
    import subprocess, tempfile
    try:
        pdf = get(url, tries=2, timeout=90)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(pdf)
            f.flush()
            txt = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, timeout=120).stdout.decode("utf8", "replace")
    except Exception as e:  # noqa: BLE001
        note("bceao", False, f"bulletin : {e}")
        save(path, db)
        return
    data = parse_bceao_bulletin(txt)
    # historique de l'inflation : on conserve les mois des bulletins précédents
    hist = db.get("infl_hist") or {}
    for c, row in (data.get("infl") or {}).items():
        for k, v in row.items():
            if len(k) == 7:
                hist.setdefault(c, {})[k] = v
    db.update(data)
    db.update({"url": url, "label": lab, "d": TODAY.isoformat(), "infl_hist": hist})
    save(path, db)
    note("bceao")


# ---------------------------------------------------------------- UMOA-Titres : courbes des taux souveraines (fichiers hebdomadaires)
def _xlsx_rows(blob):
    import zipfile, xml.etree.ElementTree as ET
    z = zipfile.ZipFile(io.BytesIO(blob))
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
            ss.append("".join(x.text or "" for x in si.iter("{%s}t" % ns["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    names = [x.get("name") for x in wb.find("m:sheets", ns)]
    sheets = {}
    for k, nm in enumerate(names, 1):
        try:
            root = ET.fromstring(z.read(f"xl/worksheets/sheet{k}.xml"))
        except KeyError:
            continue
        rows = []
        for row in root.iter("{%s}row" % ns["m"]):
            cells = {}
            for c in row.findall("m:c", ns):
                col = re.match(r"[A-Z]+", c.get("r")).group()
                v = c.find("m:v", ns)
                cells[col] = None if v is None else (ss[int(v.text)] if c.get("t") == "s" else v.text)
            rows.append(cells)
        sheets[nm] = rows
    return sheets


def _umoa_parse(blob):
    out = {}
    asof = None
    for nm, rows in _xlsx_rows(blob).items():
        pts = []
        for r in rows:
            for col, v in r.items():
                if isinstance(v, str) and "COURBE DES TAUX" in v.upper():
                    m = re.search(r"(\d{2}/\d{2}/\d{4})", v)
                    if m:
                        asof = m.group(1)
            vals = list(r.values())
            for j, v in enumerate(vals):
                m = re.match(r"^\s*(\d+)\s*(mois|ans?)\s*$", str(v or ""))
                if m and j + 2 < len(vals):
                    try:
                        zc, ls = float(vals[j + 1]), float(vals[j + 2])
                    except (TypeError, ValueError):
                        continue
                    yrs = int(m.group(1)) / 12 if m.group(2) == "mois" else int(m.group(1))
                    pts.append([v.strip(), round(yrs, 4), round(zc, 6), round(ls, 6)])
        if pts:
            out[nm.strip()] = sorted(pts, key=lambda p: p[1])
    return asof, out


def run_umoa(out):
    path = os.path.join(out, "umoa_curves.json")
    db = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {"curves": {}}
    try:
        page = get("https://www.umoatitres.org/fr/ressources-2/courbe-des-taux/", tries=2, timeout=60).decode("utf8", "replace")
    except Exception as e:  # noqa: BLE001
        note("umoa", False, f"page : {e}")
        return
    links = []
    for u in set(re.findall(r'href="(https?://www\.umoatitres\.org/wp-content/uploads/[^"]+COURBES[^"]+\.xlsx)"', page, re.I)):
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", u)
        if m:
            links.append((f"{m.group(3)}-{m.group(2)}-{m.group(1)}", u))
    links.sort(reverse=True)
    if not links:
        note("umoa", False, "aucun fichier de courbe")
        return
    want = [links[0]]
    d0 = dt.date.fromisoformat(links[0][0])
    for lag in (28, 91, 182, 364):  # comparaisons : 1, 3, 6 et 12 mois
        tgt = d0 - dt.timedelta(days=lag)
        best = min(links, key=lambda x: abs((dt.date.fromisoformat(x[0]) - tgt).days))
        if best not in want:
            want.append(best)
    for d, u in want:
        if d in db["curves"]:
            continue
        try:
            asof, cv = _umoa_parse(get(u, tries=2, timeout=60))
            if cv:
                db["curves"][d] = {"asof": asof, "src": u, "c": cv}
                note("umoa")
        except Exception as e:  # noqa: BLE001
            note("umoa", False, f"{d}: {e}")
    keep = sorted(db["curves"])[-40:]
    db["curves"] = {k: db["curves"][k] for k in keep}
    db["latest"] = links[0][0]
    db["d"] = TODAY.isoformat()
    save(path, db)


# ---------------------------------------------------------------- obligations cotées à la BRVM
def run_obl(out, site_data=None):
    import html as H_
    rows = {}
    for cat, typ in ((20, "État"), (21, "Régional"), (55, "Privé"), (0, None)):
        try:
            h = get(f"https://www.brvm.org/fr/cours-obligations/{cat}", tries=2, timeout=40).decode("utf8", "replace")
        except Exception as e:  # noqa: BLE001
            note("obl", False, f"{cat}: {e}")
            continue
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
            c = [re.sub(r"\s+", " ", H_.unescape(re.sub(r"<[^>]+>", " ", x))).replace("\xa0", " ").strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(c) < 7 or not re.match(r"^[A-Z0-9]+\.O\d+$", c[0]):
                continue
            code = c[0]
            r = rows.get(code) or {"code": code, "n": c[1], "em": c[2], "mat": c[3] or None, "px": (_frnum(c[4]) or None) if c[4] else None, "cc": _frnum(c[5]) if c[5] else None}
            m = re.match(r"(\d{2}/\d{2}/\d{4})\s*/\s*([\d ,]+)", c[6] or "")
            if m:
                r["lp_d"], r["lp_v"] = m.group(1), _frnum(m.group(2))
            if typ and not r.get("typ"):
                r["typ"] = typ
            rows[code] = r
        note("obl")
        time.sleep(.5)
    if not rows:
        return
    for r in rows.values():
        m = re.search(r"(\d+(?:[,.]\d+)?)\s*%", r["n"])
        r["cpn"] = float(m.group(1).replace(",", ".")) / 100 if m else None
        m = re.search(r"(20\d\d)\s*-\s*(20\d\d)", r["n"])
        if m:
            r["y0"], r["y1"] = int(m.group(1)), int(m.group(2))
        r["iss"] = re.sub(r"\s*\(?TX DE BASE.*$|\s*\d+(?:[,.]\d+)?\s*%.*$", "", r["n"]).strip()
    o = {"ts": int(time.time()), "d": TODAY.isoformat(), "src": "brvm.org/fr/cours-obligations", "rows": sorted(rows.values(), key=lambda r: r["code"])}
    save(os.path.join(out, "bonds.json"), o)
    if site_data:
        save(os.path.join(site_data, "bonds.json"), o)


# ---------------------------------------------------------------- capitalisations mondiales (companiesmarketcap.com, CSV)
CAL_CTY = "US,EU,GB,JP,CN,DE,FR,IT,ES,CA,AU,CH,IN,BR,ZA,NG,GH,CI,SN,KE,MA,EG"


def run_cal(out, site_data=None):
    """Calendrier économique (fonction ECO) : publications macro de 22 pays et zones, du jour J-10 à J+24, avec
    prévision (consensus), réel et précédent tels que publiés par le calendrier économique de TradingView.
    Rafraîchi à chaque passage de 15 min : les chiffres « réel » apparaissent dès leur publication."""
    t0 = dt.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    a, b = t0 - dt.timedelta(days=10), t0 + dt.timedelta(days=24)
    u = ("https://economic-calendar.tradingview.com/events?from=" + a.strftime("%Y-%m-%dT00:00:00.000Z") + "&to=" + b.strftime("%Y-%m-%dT00:00:00.000Z")
         + "&countries=" + CAL_CTY)
    j = json.loads(get(u, tries=2, timeout=40, headers={"Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/", "Accept": "application/json, text/plain, */*"}))
    rows = []
    for x in j.get("result") or []:
        if not x.get("date") or not x.get("title"):
            continue
        r = {"d": x["date"][:16], "c": x.get("country"), "i": x.get("importance", -1), "t": x["title"].strip()}
        for k_src, k in (("indicator", "ind"), ("category", "cat"), ("period", "p"), ("actual", "a"), ("forecast", "f"), ("previous", "pr"), ("unit", "u"), ("scale", "sc"), ("source", "src"), ("currency", "cur")):
            v = x.get(k_src)
            if v not in (None, ""):
                r[k] = v
        rows.append(r)
    if len(rows) < 30:
        raise RuntimeError(f"calendrier trop court ({len(rows)} lignes)")
    # même publication listée deux fois (même heure, même pays, même intitulé) : la ligne la plus complète est gardée
    best = {}
    for r in rows:
        k = (r["d"], r["c"], r["t"])
        if k not in best or len(r) > len(best[k]):
            best[k] = r
    rows = list(best.values())
    rows.sort(key=lambda r: (r["d"], -r["i"], r["c"], r["t"]))
    res = {"ts": int(time.time()), "from": a.strftime("%Y-%m-%d"), "to": b.strftime("%Y-%m-%d"), "src": "TradingView (calendrier économique)", "rows": rows}
    save(os.path.join(site_data or out, "calendar.json"), res)
    note("calendar")
    log(f"calendrier : {len(rows)} événements")


def run_cmc(out, site_data=None):
    """Toutes les sociétés cotées classées par capitalisation (USD) avec pays ; variation calculée contre le relevé du soir précédent."""
    path = os.path.join(out, "cmc_eod.json")
    eod = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {}
    try:
        raw = get("https://companiesmarketcap.com/?download=csv", tries=2, timeout=60).decode("utf8", "replace")
    except Exception as e:  # noqa: BLE001
        note("cmc", False, str(e))
        return
    rows = list(csv.reader(io.StringIO(raw)))
    hdr = [h.strip().lower() for h in rows[0]] if rows else []
    if "symbol" not in hdr:
        note("cmc", False, "format inattendu")
        return
    ix = {h: i for i, h in enumerate(hdr)}
    cur = {}
    for r in rows[1:]:
        try:
            sym, mc, pxx = r[ix["symbol"]], float(r[ix["marketcap"]]), float(r[ix["price (usd)"]])
        except (ValueError, IndexError, KeyError):
            continue
        cur[sym] = [HTML.unescape(r[ix["name"]]).strip(), r[ix["country"]], mc, pxx]
    now = int(time.time())
    prev = eod.get("px") or {}
    out_rows = []
    for sym, (nm, cty, mc, pxx) in cur.items():
        if mc < 2e9:
            continue
        p0 = prev.get(sym)
        out_rows.append([sym, nm, cty, round(mc), pxx, round(pxx / p0 - 1, 5) if p0 else None])
    out_rows.sort(key=lambda r: -r[3])
    site = {"ts": now, "ref": eod.get("d"), "src": "companiesmarketcap.com", "rows": out_rows}
    if site_data:
        save(os.path.join(site_data, "world.json"), site)
    if os.environ.get("FQT_MODE") == "eod" or not eod.get("px"):
        save(path, {"d": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "px": {k: v[3] for k, v in cur.items()}})
        open(os.path.join(out, ".dirty"), "w").close()  # relevé de référence à conserver (branche raw)
    note("cmc")


# ---------------------------------------------------------------- Energy Institute, Statistical Review of World Energy : production et consommation de pétrole par pays
EI_URLS = ["https://www.energyinst.org/__data/assets/excel_doc/0008/1656215/EI-Stats-Review-ALL-data.xlsx"]  # édition 2025 (données 2024)


def _xlsx_sheet(blob, want):
    """Lignes (listes de cellules) de la feuille dont le nom correspond à `want` (expression régulière), ou None."""
    import zipfile, xml.etree.ElementTree as ET
    z = zipfile.ZipFile(io.BytesIO(blob))
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid2t = {r.get("Id"): r.get("Target") for r in rels}
    target = None
    for sh in wb.find("m:sheets", ns):
        if re.search(want, sh.get("name") or "", re.I):
            target = rid2t.get(sh.get("{%s}id" % ns["r"]))
            break
    if not target:
        return None
    target = target.lstrip("/")
    target = target if target.startswith("xl/") else "xl/" + target
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
            ss.append("".join(x.text or "" for x in si.iter("{%s}t" % ns["m"])))
    out = []
    for row in ET.fromstring(z.read(target)).iter("{%s}row" % ns["m"]):
        cells = {}
        for c in row.findall("m:c", ns):
            col = re.match(r"[A-Z]+", c.get("r")).group()
            v = c.find("m:v", ns)
            cells[col] = None if v is None else (ss[int(v.text)] if c.get("t") == "s" else v.text)
        out.append(cells)
    return out


def run_ei(out):
    path = os.path.join(out, "ei_oil.json")
    # 1) Our World in Data (données de l'Energy Institute, fichier public sur GitHub) : production et consommation de pétrole en TWh
    try:
        rows = list(csv.DictReader(io.StringIO(get("https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv", tries=2, timeout=120).decode("utf8", "replace"))))
        res = {"src": "Energy Institute, Statistical Review of World Energy, via Our World in Data", "u": "https://github.com/owid/energy-data", "d": TODAY.isoformat()}
        for key, col in (("prod", "oil_production"), ("cons", "oil_consumption")):
            have = [r for r in rows if r.get(col) and (r.get("iso_code") or r["country"] == "World") and not (r.get("iso_code") or "").startswith("OWID_") or (r["country"] == "World" and r.get(col))]
            ymax = max(int(r["year"]) for r in have)
            years = list(range(ymax - 10, ymax + 1))
            data = {}
            for r in have:
                y = int(r["year"])
                if y in years:
                    data.setdefault(r["country"], [None] * len(years))[years.index(y)] = round(float(r[col]), 1)
            res[key] = {"years": years, "unit": "TWh", "rows": data}
        if res["prod"]["rows"].get("United States"):
            save(path, res)
            note("ei")
            return
    except Exception as e:  # noqa: BLE001
        note("ei", False, f"owid: {e}")
    for url in EI_URLS:
        try:
            blob = get(url, tries=2, timeout=120)
            res = {"src": "Energy Institute, Statistical Review of World Energy 2025", "u": url, "d": TODAY.isoformat()}
            for key, pat in (("prod", r"^Oil Production - (barrels|Tonnes)$|^Oil production - barrels"), ("cons", r"^Oil Consumption - barrels")):
                rows = _xlsx_sheet(blob, pat)
                if not rows:
                    continue
                hdr_i = next((i for i, r in enumerate(rows[:10]) if sum(1 for v in r.values() if re.match(r"^(19|20)\d\d$", str(v or ""))) > 10), None)
                if hdr_i is None:
                    continue
                cols = {c: int(v) for c, v in rows[hdr_i].items() if re.match(r"^(19|20)\d\d$", str(v or ""))}
                last = sorted(cols.items(), key=lambda x: x[1])[-11:]
                data = {}
                for r in rows[hdr_i + 1:]:
                    name = (r.get("A") or "").strip()
                    if not name or name.lower().startswith(("total", "of which", "other", "source", "note", "*", "#", "^")):
                        continue
                    vals = []
                    for c, y in last:
                        try:
                            vals.append(round(float(r.get(c)), 1))
                        except (TypeError, ValueError):
                            vals.append(None)
                    if any(v for v in vals if v):
                        data[name] = vals
                res[key] = {"years": [y for _, y in last], "unit": "milliers de barils par jour", "rows": data}
            if res.get("prod") and "US" in res["prod"]["rows"] or res.get("prod") and "United States" in res["prod"]["rows"]:
                save(path, res)
                note("ei")
                return
            note("ei", False, "feuilles introuvables")
        except Exception as e:  # noqa: BLE001
            note("ei", False, str(e))


# ---------------------------------------------------------------- contrats à terme en continu (1er mois) : Brent, WTI, gaz, or
FUT_Y = (("BRENT", "BZ=F"), ("WTI", "CL=F"), ("NATGAS", "NG=F"), ("GOLD", "GC=F"))


def run_fut(out):
    """Historique quotidien des contrats à terme 1er mois (Yahoo Finance), fusionné avec le relevé précédent.
    Ce sont les prix affichés par Investing, TradingView ou Bloomberg (CO1, CL1, NG1, GC1), pas les prix au comptant."""
    for sid, sym in FUT_Y:
        p = os.path.join(out, "futures", sid + ".json")
        old = json.load(open(p, encoding="utf8")) if os.path.exists(p) else None
        if old and len(old.get("d", [])) > 20:  # relevé précédent contenant des points mensuels (range=max) : écarté en entier
            if sum(1 for a_, b_ in zip(old["d"], old["d"][1:]) if (i2d(b_) - i2d(a_)).days > 7) > 5:
                old = None
        p1 = int(time.time()) - 2 * 366 * 86400 if old else 946684800  # 2000-01-01 : quotidien garanti avec period1/period2
        j, err = None, None
        for host in ("query1", "query2"):
            try:
                j = json.loads(get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={p1}&period2={int(time.time())}&interval=1d",
                                   tries=2, timeout=40, headers={"Referer": "https://finance.yahoo.com/", "Origin": "https://finance.yahoo.com"}))
                break
            except Exception as e:  # noqa: BLE001
                err = e
        try:
            if not j:
                raise err or ValueError("aucune réponse")
            res = j["chart"]["result"][0]
            ts, qd, off = res["timestamp"], res["indicators"]["quote"][0], res["meta"].get("gmtoffset", 0)
            rows = {}
            if old:
                for i, d in enumerate(old["d"]):
                    rows[d] = (old["o"][i], old["h"][i], old["l"][i], old["c"][i], old["v"][i])
            for i, t in enumerate(ts):
                c = qd["close"][i]
                if c is None or c <= 0:
                    continue
                d = d2i(dt.datetime.fromtimestamp(t + off, dt.timezone.utc).date())
                o, h, lo, v = qd["open"][i] or c, qd["high"][i] or c, qd["low"][i] or c, qd["volume"][i] or 0
                rows[d] = (round(o, 4), round(max(h, c, o), 4), round(min(lo, c, o), 4), round(c, 4), int(v))
            ks = sorted(rows)
            if len(ks) < 250 or sum(1 for a_, b_ in zip(ks, ks[1:]) if (i2d(b_) - i2d(a_)).days > 7) > 5:
                raise ValueError(f"historique non quotidien ({len(ks)} points)")
            save(p, {"sym": sym, "src": "Yahoo Finance (contrat 1er mois en continu)", "d": ks, "o": [rows[k][0] for k in ks], "h": [rows[k][1] for k in ks],
                     "l": [rows[k][2] for k in ks], "c": [rows[k][3] for k in ks], "v": [rows[k][4] for k in ks]})
            note("fut")
        except Exception as e:  # noqa: BLE001
            note("fut", False, f"{sid}: {e}")
        time.sleep(.5)


# ---------------------------------------------------------------- EIA : stocks hebdomadaires de pétrole des États-Unis (Weekly Petroleum Status Report)
def run_eia(out):
    try:
        raw = get("https://ir.eia.gov/wpsr/table1.csv", tries=2, timeout=40).decode("utf8", "replace")
    except Exception as e:  # noqa: BLE001
        note("eia", False, str(e))
        return
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows or len(rows[0]) < 4:
        note("eia", False, "format")
        return
    hdr = rows[0]
    keep = {}
    for r in rows[1:]:
        if len(r) >= 5 and r[0].strip():
            try:
                keep[r[0].strip()] = [float(x) if x not in ("", "NA") else None for x in r[1:8]]
            except ValueError:
                continue
    flows = {}

    def tab(n):
        try:
            return list(csv.reader(io.StringIO(get(f"https://ir.eia.gov/wpsr/table{n}.csv", tries=2, timeout=40).decode("utf8", "replace"))))
        except Exception as e:  # noqa: BLE001
            note("eia", False, f"table {n}: {e}")
            return []
    fl = lambda x: float(x.replace(",", "")) if re.match(r"^-?[\d,]+(\.\d+)?$", (x or "").strip()) else None

    def put(key, name, unit, r, ci):
        try:
            flows[key] = {"n": name, "u": unit, "v": [fl(r[ci[0]]), fl(r[ci[1]]), fl(r[ci[2]])]}
        except IndexError:
            pass
    t9 = tab(9)  # production, raffinage
    for r in t9[1:]:
        lab = (r[1] if len(r) > 1 else "").strip()
        if lab == "Domestic Production" and "prod" not in flows:
            put("prod", "Production de brut des États-Unis", "kb/j", r, (2, 3, 4))
        elif lab == "Crude Oil Inputs" and "ref_in" not in flows:
            put("ref_in", "Brut traité par les raffineries", "kb/j", r, (2, 3, 4))
        elif lab == "Percent Utilization" and "util" not in flows:
            put("util", "Taux d’utilisation des raffineries", "%", r, (2, 3, 4))
    t7 = tab(7)  # importations, exportations
    sec_ = "tot"
    for r in t7[1:]:
        lab = (r[0] if r else "").strip()
        if lab.startswith("Crude Oil Net Imports"):
            sec_ = "crude"
            put("crude_net", "Importations nettes de brut", "kb/j", r, (1, 2, 4))
        elif lab.startswith("Total Products Net Imports"):
            sec_ = "prod"
            put("prod_net", "Importations nettes de produits", "kb/j", r, (1, 2, 4))
        elif lab.startswith("Net Imports") and sec_ == "tot":
            put("tot_net", "Importations nettes (pétrole et produits)", "kb/j", r, (1, 2, 4))
        elif lab == "Commercial" and sec_ == "crude" and "crude_imp" not in flows:
            put("crude_imp", "Importations de brut", "kb/j", r, (1, 2, 4))
        elif lab == "Exports":
            k = {"tot": "tot_exp", "crude": "crude_exp", "prod": "prod_exp"}[sec_]
            if k not in flows:
                put(k, {"tot_exp": "Exportations totales (brut et produits)", "crude_exp": "Exportations de brut", "prod_exp": "Exportations de produits"}[k], "kb/j", r, (1, 2, 4))
    t4 = tab(4)  # stocks détaillés
    for r in t4[1:]:
        lab = (r[0] if r else "").strip()
        for k, n in (("Cushing", "Stocks de Cushing (point de livraison du WTI)"), ("Total Stocks (Including SPR)", "Stocks totaux de pétrole (réserve stratégique comprise)")):
            if lab == k:
                put("cush" if k == "Cushing" else "tot_stk", n, "Mb", r, (1, 2, 4))
    save(os.path.join(out, "eia_wpsr.json"), {"d": TODAY.isoformat(), "src": "EIA, Weekly Petroleum Status Report (tableaux 1, 4, 7, 9)", "hdr": hdr, "rows": keep,
                                              "week": hdr[1] if len(hdr) > 1 else None, "flows": flows})
    note("eia")

# ---------------------------------------------------------------- actualités reliées aux titres et typées
NEWS_ALIAS = {  # noms usuels des sociétés dans la presse (en plus du nom officiel)
    "SNTS": ["Sonatel"], "ORAC": ["Orange Côte d'Ivoire", "Orange CI"], "SGBC": ["Société Générale Côte d'Ivoire", "SGBCI", "SGCI"],
    "ETIT": ["Ecobank Transnational", "Ecobank TI", "Ecobank", "ETI"], "ECOC": ["Ecobank Côte d'Ivoire", "Ecobank CI"], "SIBC": ["Société Ivoirienne de Banque", "SIB"],
    "CBIBF": ["Coris Bank"], "PALC": ["Palm Côte d'Ivoire", "Palmci"], "SPHC": ["SAPH"], "SOGC": ["SOGB"], "NTLC": ["Nestlé Côte d'Ivoire", "Nestlé CI"],
    "SLBC": ["Solibra"], "UNLC": ["Unilever Côte d'Ivoire"], "TTLC": ["TotalEnergies Marketing Côte d'Ivoire"], "TTLS": ["TotalEnergies Marketing Sénégal"],
    "CIEC": ["Compagnie Ivoirienne d'Electricité", "CIE"], "SDCC": ["SODECI"], "ONTBF": ["Onatel"], "BOAC": ["BOA Côte d'Ivoire", "Bank of Africa Côte d'Ivoire"],
    "BOABF": ["BOA Burkina", "Bank of Africa Burkina"], "BOAB": ["BOA Bénin", "Bank of Africa Bénin"], "BOAS": ["BOA Sénégal", "Bank of Africa Sénégal"],
    "BOAM": ["BOA Mali", "Bank of Africa Mali"], "BOAN": ["BOA Niger", "Bank of Africa Niger"], "NSBC": ["NSIA Banque"], "BICC": ["BICICI", "BICI CI"],
    "SMBC": ["SMB"], "STBC": ["SITAB"], "SDSC": ["Africa Global Logistics", "AGL Côte d'Ivoire"], "ORGT": ["Oragroup"], "SNTS ": [],
    "SAFC": ["Safca"], "SICC": ["SICOR"], "SEMC": ["Eviosys", "SIEM"], "FTSC": ["Filtisac"], "CABC": ["Sicable"], "SIVC": ["Air Liquide Côte d'Ivoire"],
    "PRSC": ["Tractafric Motors"], "BNBC": ["Bernabé"], "SCRC": ["Sucrivoire"], "ABJC": ["Servair Abidjan"], "LNBB": ["Loterie Nationale du Bénin"],
    "BICB": ["BIIC Bénin", "Banque Internationale pour l'Industrie et le Commerce"], "SHEC": ["Vivo Energy Côte d'Ivoire"], "STAC": ["SETAO"], "UNXC": ["Uniwax"],
    "NVDA": ["Nvidia"], "AAPL": ["Apple"], "MSFT": ["Microsoft"], "GOOG": ["Alphabet", "Google"], "GOOGL": ["Alphabet", "Google"], "AMZN": ["Amazon"],
    "META": ["Meta Platforms", "Facebook"], "TSLA": ["Tesla"], "AVGO": ["Broadcom"], "AMD": ["AMD"], "NFLX": ["Netflix"], "COST": ["Costco"], "INTC": ["Intel"],
}
NEWS_STOP = {"meta", "arm", "apple"}  # trop ambigus seuls en minuscules : exigés avec la majuscule
EVENT_RX = [  # (type, motif) — premier qui correspond ; le premier motif repère les comptes rendus de séance
    ("Marchés", r"(live updates|stock market today|stocks? (rise|fall|slip|gain|climb|drop|edge|rall|sink|surge|tumble|jump)|futures (rise|fall|slip|gain|climb|edge|point)|S&P 500 (is|rises|falls|slips|gains|climbs|hits|edges|closes|ends)|Dow (jumps|falls|rises|slips|gains|closes|ends)|Wall Street (ends|closes|opens|finit|termine|ouvre)|la BRVM (termine|cl[ôo]ture|ouvre|progresse|recule)|bourse de (paris|new york))"),
    ("Résultats", r"\b(r[ée]sultats?|b[ée]n[ée]fices?|chiffre d.affaires|earnings|revenue|profit|quarterly|trimestriel|semestriel|annual results|[ée]tats financiers|rapport.{0,4}activit)"),
    ("Dividende", r"\b(dividendes?|dividend|coupon|d[ée]tachement)"),
    ("Assemblée", r"\b(assembl[ée]e g[ée]n[ée]rale|AGO|AGE|shareholder meeting)\b"),
    ("Dirigeants", r"\b(nomm[ée]|nomination|directeur g[ée]n[ée]ral|PDG|CEO|appoint|steps down|d[ée]mission|conseil d.administration)"),
    ("Analystes", r"(potentiel de hausse|r[ée]it[èe]re|abaisse son objectif|rel[èe]ve son objectif|rehausse|mise [àa] niveau|surpond[ée]r|sous-pond[ée]r|d[ée]grade|rel[èe]ve (sa|son)|recommandation|objectif de cours|price target|downgrades?|upgrades?|initiates coverage)"),
    ("Notation", r"\b(notation|note souveraine|moody|fitch|s&p global ratings|bloomfield|WARA|credit rating)\b"),
    ("Émission", r"\b(emprunt obligataire|[ée]mission obligataire|eurobond|bond issue|sukuk|appel public|APE|obligations? du tr[ée]sor|bons du tr[ée]sor|UMOA-Titres|lev[ée]e de fonds)\b"),
    ("Opération", r"\b(acquisition|rachat|fusion|merger|takeover|OPA|OPR|cession|stake|prise de participation|introduction en bourse|IPO|division de (son|l.)action|fractionnement|stock split)\b"),
    ("Régulation", r"\b(AMF-UMOA|CREPMF|SEC (charges|sues|probe)|amende|fined|sanctionn|antitrust|r[ée]gulateur|suspension de (la )?cotation|delisting|radiation)"),
    ("Banques centrales", r"\b(BCEAO|Fed|Federal Reserve|FOMC|BCE|ECB|taux directeurs?|policy rate|rate cut|rate hike|politique mon[ée]taire)\b"),
    ("Macro", r"\b(inflation|PIB|GDP|croissance [ée]conomique|ch[ôo]mage|unemployment|payrolls|CPI|IPC|budget|dette publique|FMI|IMF|Banque mondiale)\b"),
    ("Matières premières", r"\b(p[ée]trole|oil|crude|brent|wti|OPEP|OPEC|gaz naturel|natural gas|l.or|gold|cacao|cocoa|caf[ée]|coton|cotton|anacarde|cashew|uranium|lithium|cuivre|copper)\b"),
    ("Crypto", r"\b(bitcoin|ethereum|crypto\w*|stablecoins?)\b"),
    ("Marchés", r"\b(bourse|BRVM|wall street|nasdaq|s&p 500|dow jones|cac 40|stocks?|indices?|index|rally|selloff|march[ée]s?)\b"),
]


def _fold(t):
    import unicodedata
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def _alias_map(summary_path):
    try:
        secs = json.load(open(summary_path, encoding="utf8")).get("secs", [])
    except Exception:  # noqa: BLE001
        return []
    out = []
    for x in secs:
        if x.get("cls") != "Equity" or x.get("typ") == "ETF":
            continue
        names = set(NEWS_ALIAS.get(x["id"], []))
        n = re.sub(r"\b(SA|S\.A\.|Inc\.?|Corp\.?|Corporation|Holdings?|Ltd|PLC|plc|Group|Class [A-C]|Common Stock|Co\.|N\.V\.|SE)\b", "", x.get("short") or x.get("n") or "")
        n = re.sub(r"[,.]", " ", n).strip()
        n = re.sub(r"\s+", " ", n)
        if len(n) >= 4:
            names.add(n)
        rx = []
        for a in names:
            if not a:
                continue
            if a.isupper() and len(a) <= 5:
                rx.append((0, re.compile(r"(?<![A-Za-z])" + re.escape(a) + r"(?![A-Za-z])")))
            elif a.lower() in NEWS_STOP:
                rx.append((0, re.compile(r"\b" + re.escape(a) + r"\b")))
            else:  # sans accents ni casse : « SENEGAL » = « Sénégal »
                rx.append((1, re.compile(r"\b" + re.escape(_fold(a)) + r"\b")))
        if len(x["id"]) >= 3 and x.get("mkt") == "BRVM":
            rx.append((0, re.compile(r"(?<![A-Za-z])" + re.escape(x["id"]) + r"(?![A-Za-z])")))
        out.append((x["id"], rx))
    return out


def tag_news(items, summary_path):
    """Relie chaque dépêche aux titres cités (tk) et lui donne un type d'événement (ev). Correspondance sur le titre et le résumé."""
    amap = _alias_map(summary_path)
    erx = [(k, re.compile(r, re.I)) for k, r in EVENT_RX]
    for x in items:
        x["ti"] = HTML.unescape(HTML.unescape(x.get("ti") or "")).replace("\xa0", " ").strip()
        if x.get("x"):
            x["x"] = re.sub(r"\s+", " ", HTML.unescape(HTML.unescape(x["x"])).replace("\xa0", " ")).strip()
        if x.get("s"):
            x["s"] = HTML.unescape(x["s"])
        txt = x["ti"] + " " + (x.get("x") or "")
        ftx = _fold(txt)
        tk = [sid for sid, rx in amap if any(r.search(ftx if f else txt) for f, r in rx)]
        if tk:
            x["tk"] = tk[:6]
        else:
            x.pop("tk", None)
        ev = next((k for k, r in erx if r.search(x["ti"])), None)
        if ev:
            x["ev"] = ev
    return items


# ---------------------------------------------------------------- main
# ------------------------------------------------------------------ avis officiels lus directement sur brvm.org
# Secours de la base d'avis du jeu de données tiers : si celle-ci s'arrête, les nouveaux avis, dividendes annoncés et
# fractionnements continuent d'arriver depuis les pages officielles. Fusion (et rapprochement société -> titre) dans build_terminal.py.
AVIS_PAGES = [  # (clé, chemin, catégorie par défaut)
    ("marche", "/fr/marche/avis-et-publications/avis", None),
    ("ag", "/fr/emetteurs/type-annonces/convocations-assemblees-generales", "Convocation / communiqué AG"),
    ("comm", "/fr/emetteurs/type-annonces/communiques", "Communiqué société"),
    ("resol", "/fr/emetteurs/type-annonces/projets-de-resolution", "Projet de résolutions"),
    ("notation", "/fr/emetteurs/type-annonces/notations-financieres", "Notation financière"),
    ("dirig", "/fr/emetteurs/type-annonces/changements-de-dirigeants", "Changement de direction"),
    ("div", "/fr/esv/paiement-de-dividendes", "Annonce dividende"),
    ("frac", "/fr/esv/fractionnement", "Fractionnement"),
    ("capital", "/fr/esv/augmentation-de-capital", None),
]
FR_NUM = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12,
          "quinze": 15, "vingt": 20, "vingt-cinq": 25, "trente": 30, "cinquante": 50, "cent": 100}


def views_rows(html):
    """Lignes des tableaux « views-table » de brvm.org : {champ: {t: texte, d: date ISO, u: [liens]}} (le bloc « Top 5 » de la colonne n'est pas un views-table)."""
    out = []
    for tb in re.findall(r'<table class="views-table[^"]*"[^>]*>(.*?)</table>', html, re.S):
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S):
            cells = {}
            for cls, body in re.findall(r'<td class="views-field views-field-([a-z0-9\-]+)"[^>]*>(.*?)</td>', tr, re.S):
                d = re.search(r'content="(\d{4}-\d{2}-\d{2})', body)
                u = [x if x.startswith("http") else "https://www.brvm.org" + x for x in re.findall(r'href="([^"]+)"', body) if "/node/" not in x and "/edit" not in x]
                t = re.sub(r"\s+", " ", HTML.unescape(re.sub(r"<[^>]+>", " ", body))).replace("Télécharger", "").strip()
                cells[cls] = {"t": t, "d": d.group(1) if d else None, "u": u}
            if cells:
                out.append(cells)
    return out


def fr_parity(txt):
    """« dix (10) actions nouvelles pour une (1) action ancienne » -> (10, 1) ; None si illisible."""
    m = re.search(r"(.+?)\s+actions?\s+nouvelles?\s+pour\s+(.+?)\s+actions?\s+anciennes?", (txt or "").lower())
    if not m:
        return None

    def n_(s_):
        x = re.search(r"\((\d+)\)", s_) or re.search(r"(\d+)\s*$", s_.strip())
        if x:
            return int(x.group(1))
        return FR_NUM.get(s_.strip().split()[-1]) if s_.strip() else None
    a_, b_ = n_(m.group(1)), n_(m.group(2))
    return (a_, b_) if a_ and b_ else None


def _avis_market_cat(ti):
    t = _nrm(ti)
    return ("Modification du dividende" if "dividende" in t and re.search(r"modif|rectif", t) else "Marché fermé (jour férié)" if "ferie" in t else "Composition d'un indice BRVM mise à jour" if "composition" in t and "indice" in t
            else "Valeur théorique publiée" if "valeur theorique" in t else "Transaction annulée par la BRVM" if "annulation de transaction" in t else "Avis de la BRVM")


def _avis_ti_fix(ti, u):
    """Avis de marché dont le titre affiché sur brvm.org n'a aucun mot en commun avec le nom du fichier publié (le site reprend parfois
    le titre de l'avis voisin, ex. « Calendrier de paiement de dividendes » sur l'avis « Transactions sur dossier ») : titre tiré du fichier."""
    slug = re.sub(r"\.pdf$", "", (u or "").rsplit("/", 1)[-1].lower())
    slug = re.sub(r"_\d+$", "", re.sub(r"^\d{8}[_\-]*", "", slug))
    slug = re.sub(r"avis_n(?:deg)?_?\d+_?brvm(?:dg)?", " ", slug)
    stop = {"avis", "brvm", "brvmdg", "exercice", "societe", "pour", "dans", "avec"}
    sw = set(re.findall(r"[a-z]{4,}", slug.replace("_", " "))) - stop
    tw = set(re.findall(r"[a-z]{4,}", _nrm(ti or ""))) - stop
    if len(sw) >= 2 and not (sw & tw):
        w = re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", slug)).strip()
        return "Avis : " + w[:1].upper() + w[1:]
    return ti


def run_avis(site_data):
    if not site_data:
        return
    path = os.path.join(site_data, "avis_brvm.json")
    st = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {"items": {}}
    items = st.setdefault("items", {})
    for u_, r_ in items.items():  # titres déjà enregistrés : même contrôle que pour les nouveaux avis
        if r_.get("k") == "marche" and r_.get("ti"):
            t_ = _avis_ti_fix(r_["ti"], u_)
            if t_ != r_["ti"]:
                r_["ti"], r_["c"] = t_, _avis_market_cat(t_)
    deep = not items or os.environ.get("FQT_MODE") == "eod"  # premier passage ou soir : 3 pages par rubrique, sinon la première

    def pub(u):
        x = re.search(r"/(20\d{2})(\d{2})(\d{2})[_\-]", u or "")
        return f"{x.group(1)}-{x.group(2)}-{x.group(3)}" if x else None

    def one(job):
        key, path_, cat, pg = job
        try:
            html = get("https://www.brvm.org" + path_ + (f"?page={pg}" if pg else ""), tries=2, timeout=30).decode("utf8", "replace")
        except Exception as e:  # noqa: BLE001
            return key, None, str(e)
        recs = []
        for r in views_rows(html):
            g = lambda k: r.get(k) or {"t": "", "d": None, "u": []}  # noqa: E731
            if key == "div":
                soc, u = g("field-emetteur-esv")["t"], (g("field-avis-dividende-esv")["u"] or [None])[0]
                amt = re.search(r"([\d\s \xa0]+(?:[.,]\d+)?)", g("field-montant-du-dividende-net")["t"])
                dps = float(re.sub(r"[\s \xa0]", "", amt.group(1)).replace(",", ".")) if amt and re.sub(r"\D", "", amt.group(1)) else None
                ex = (g("field-exercice-comptable-esv")["d"] or "")[:4] or None
                det, pay = g("field-date-ex-dividende")["d"], g("field-date-de-paiement-esv")["d"]
                if soc and u and (dps or det or pay):
                    recs.append({"k": key, "soc": soc, "c": cat, "u": u, "d": pub(u) or det, "e": det or pay, "ex": int(ex) if ex else None, "dps": dps, "det": det, "pay": pay,
                                 "ti": f"{soc} : dividende" + (f" de l’exercice {ex}" if ex else "") + (f" · {dps:g} FCFA par action" if dps else "") + (f" · détachement le {det[8:]}/{det[5:7]}/{det[:4]}" if det else "") + (f" · paiement le {pay[8:]}/{pay[5:7]}/{pay[:4]}" if pay else "")})
            elif key == "frac":
                soc, par = g("field-emetteur-esv")["t"], g("field-parite-esv")["t"]
                u = (g("field-avis-dividende-esv")["u"] or g("field-communique-esv")["u"] or [None])[0]
                e, rt = g("field-date-de-fractionnement")["d"], fr_parity(par)
                if soc and u and e:
                    recs.append({"k": key, "soc": soc, "c": cat, "u": u, "d": pub(u) or e, "e": e, "ratio": list(rt) if rt else None, "ti": f"{soc} : fractionnement · {par}" if par else f"{soc} : fractionnement"})
            elif key == "marche":
                ti, d, u = g("title")["t"], g("field-date-avis")["d"], (g("field-fichier-avis")["u"] or [None])[0]
                if ti and u:
                    ti = _avis_ti_fix(ti, u)
                    soc = ti.split(" : ")[0].strip() if " : " in ti and not re.match(r"(?i)^(avis|brvm|rappel|communiqu)", ti) else None
                    recs.append({"k": key, "soc": soc, "c": _avis_market_cat(ti), "u": u, "d": d or pub(u), "e": d or pub(u), "ti": ti})
            elif key == "capital":  # rubrique sans exemple vérifié : lecture générique (émetteur, dates, liens)
                soc = g("field-emetteur-esv")["t"]
                links = [x for v in r.values() for x in v["u"]]
                dates = sorted(v["d"] for v in r.values() if v["d"])
                txt = " · ".join(v["t"] for k, v in r.items() if v["t"] and k not in ("field-emetteur-esv",) and not v["d"])
                if soc and links:
                    recs.append({"k": key, "soc": soc, "c": "Actions gratuites" if "gratuit" in _nrm(txt) else "Augmentation de capital avec droits", "u": links[0],
                                 "d": pub(links[0]) or (dates[0] if dates else None), "e": dates[-1] if dates else pub(links[0]), "ti": f"{soc} : {txt}"[:200] if txt else f"{soc} : opération sur le capital"})
            else:  # annonces des émetteurs (AG, communiqués, résolutions, notations, dirigeants)
                ti, d, soc, u = g("title")["t"], g("field-date-annonce")["d"], g("og-group-ref")["t"], (g("field-fichier-annonce")["u"] or [None])[0]
                if ti and u:
                    c = "Projet de résolutions" if key == "ag" and "resolution" in _nrm(ti) else cat
                    recs.append({"k": key, "soc": soc or None, "c": c, "u": u, "d": d or pub(u), "e": d or pub(u), "ti": ti})
        return key, recs, None

    jobs = [(k, p_, c, pg) for k, p_, c in AVIS_PAGES for pg in (range(10 if k == "marche" else 3) if deep else (0,))]
    n_new = 0
    with ThreadPoolExecutor(6) as ex:
        for key, recs, err in ex.map(one, jobs):
            if recs is None:
                note("avis-brvm", False, f"{key}: {err}")
                continue
            note("avis-brvm")
            for r in recs:
                if r["u"] not in items:
                    n_new += 1
                items[r["u"]] = {**items.get(r["u"], {}), **r, "seen": items.get(r["u"], {}).get("seen") or TODAY.isoformat()}
    st["ts"] = int(time.time())
    save(path, st)
    log(f"avis brvm.org : {len(items)} connus, {n_new} nouveaux")



def run_avisocr(site_data):
    """Le soir : lit dans les PDF de la BRVM le montant des dividendes (net, ou brut et IRVM), les rectificatifs « modification du
    montant du dividende » et la date des assemblées. Écrit le résultat dans avis_brvm.json (utilisé par build_terminal.py)."""
    if not site_data:
        return
    path = os.path.join(site_data, "avis_brvm.json")
    if not os.path.exists(path):
        return
    st = json.load(open(path, encoding="utf8"))
    items = st.get("items") or {}
    # avis lus dans le PDF (le soir) : montant du dividende (net, ou brut et IRVM), dates, et rectificatifs « modification du montant du dividende » ;
    # date de l'assemblée dans les convocations. Les avis de la BRVM sont souvent scannés : reconnaissance de caractères si le PDF n'a pas de texte.
    if True:
        divs_ = sorted([r for r in items.values() if (r.get("k") == "div" or r.get("c") == "Modification du dividende") and "ocr" not in r and r.get("d")
                        and _doc_recent(r["d"].replace("-", ""), 500)], key=lambda r: r["d"], reverse=True)
        ags_ = [r for r in items.values() if r.get("k") == "ag" and "convocation" in _nrm(r.get("ti") or "") and "ag" not in r and r.get("d") and _doc_recent(r["d"].replace("-", ""), 90)]
        todo = divs_[:30] + ags_[:15]
        if todo and pdf_tools():
            for r in todo:
                try:
                    txt = avis_text(r["u"])
                except Exception as e:  # noqa: BLE001
                    note("avis-brvm", False, f"lecture {r['u'][-60:]}: {e}")
                    continue
                if r.get("k") == "ag":
                    r["ag"] = ag_date(txt, r["d"]) or ""
                    continue
                prev = [x for x in items.values() if x is not r and x.get("soc") == r.get("soc") and (x.get("ocr") or {}).get("net") and (x.get("d") or "") <= r["d"]]
                old = max(prev, key=lambda x: x["d"])["ocr"]["net"] if prev else r.get("dps")
                o = div_parse(txt, old if r.get("c") == "Modification du dividende" else None) or {}
                o["v"] = 1
                r["ocr"] = o
                log(f"avis lu : {r.get('soc')} {r['u'][-70:]} -> {o}")
    save(path, st)
    log(f"avis lus dans les PDF : {sum(1 for r in items.values() if r.get('ocr'))} dividendes, {sum(1 for r in items.values() if r.get('ag'))} assemblées")


# ------------------------------------------------------------------ flottant officiel des sociétés cotées (avis de la BRVM, tableau scanné)
def flottant_parse(txt, tickers, names=None):
    """Lignes « EMETTEUR CODE titres titres_flottants flottant% Respectée/Non respectée » lues dans l'avis ; une ligne n'est gardée
    que si titres flottants ÷ titres = flottant % (à 0,1 point) : la lecture d'un tableau scanné n'est jamais inventée.
    Si le code est illisible, la ligne est rattachée par le nom de la société (`names` : {code: [noms]}). Seuil : 15 % du capital dans le public."""
    out = {}
    t = re.sub(r"[\u202f\xa0]", " ", txt)
    generic = {"cote", "ivoire", "bank", "africa", "societe", "generale", "group", "international", "ci", "sa"}
    nm = {tk: {w for n in ns if n for w in re.findall(r"[a-z]{4,}", _nrm(n)) if w not in generic} for tk, ns in (names or {}).items()}
    for m in re.finditer(r"([^\n%]{0,70}?)\b([A-Za-z]{3,5})\s+(\d[\d ]{3,}\d)\s+(\d[\d ]{1,}\d)\s+[-—–_ ]*(\d{1,3}[.,]\d{1,2})\s*%", t):
        tk = m.group(2).upper()
        if tk not in tickers:  # code illisible : la société est reconnue à son nom sur la même ligne
            lead = set(re.findall(r"[a-z]{4,}", _nrm(m.group(1) + " " + m.group(2))))
            sc = sorted(((len(ws & lead), k) for k, ws in nm.items() if k not in out and ws & lead), reverse=True)
            if not sc or (len(sc) > 1 and sc[0][0] == sc[1][0]):
                continue
            tk = sc[0][1]
        try:
            sh, fl, pct = int(re.sub(r"\D", "", m.group(3))), int(re.sub(r"\D", "", m.group(4))), float(m.group(5).replace(",", "."))
        except ValueError:
            continue
        if sh <= 0 or fl < 0 or fl > sh or abs(fl / sh * 100 - pct) > 0.1:
            continue
        tail = t[m.end():m.end() + 40].lower()
        ok = (not re.match(r"\s*[^a-z]*non", tail)) if "respect" in tail else pct >= 15
        out[tk] = {"sh": sh, "flt": fl, "pct": round(pct, 2), "ok15": ok}
    return out


def run_flottant(raw, site_data):
    """Dernier avis « Flottant des sociétés cotées » publié sur brvm.org : lu dans le PDF (reconnaissance de caractères), contrôlé ligne à ligne."""
    if not site_data:
        return
    av = os.path.join(site_data, "avis_brvm.json")
    if not os.path.exists(av):
        return
    items = json.load(open(av, encoding="utf8")).get("items") or {}
    cand = sorted([r for r in items.values() if "flottant" in _nrm(r.get("ti") or "") and r.get("d")], key=lambda r: r["d"], reverse=True)
    if not cand:
        return
    r = cand[0]
    path = os.path.join(raw, "flottant.json")
    prev = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {}
    if prev.get("u") == r["u"] and prev.get("rows"):
        note("flottant")
        return  # déjà lu
    summ = os.path.join(site_data, "summary.json")
    secs_ = [x for x in (json.load(open(summ, encoding="utf8")).get("secs") if os.path.exists(summ) else []) if x.get("mkt") == "BRVM" and x.get("cls") == "Equity"]
    tickers = {x["id"] for x in secs_}
    names = {x["id"]: [x.get("n"), x.get("short")] for x in secs_}
    if not tickers or not pdf_tools():
        return
    import glob, subprocess, tempfile
    pdf = get(r["u"], tries=2, timeout=60)
    txt = ""
    with tempfile.TemporaryDirectory() as td:
        p_ = os.path.join(td, "f.pdf")
        open(p_, "wb").write(pdf)
        subprocess.run(["pdftoppm", "-r", "300", "-png", p_, os.path.join(td, "pg")], capture_output=True, timeout=180)
        for f in sorted(glob.glob(os.path.join(td, "pg*.png"))):
            txt += subprocess.run(["tesseract", f, "-", "-l", "eng", "--psm", "6"], capture_output=True, timeout=180).stdout.decode("utf8", "replace") + "\n"
    rows = flottant_parse(txt, tickers, names)
    asof = re.search(r"au (\d{1,2}(?:er)? \w+ \d{4})", txt, re.I)
    save(path, {"u": r["u"], "d": r["d"], "ti": r.get("ti"), "asof": asof.group(1) if asof else None, "rows": rows, "n_univers": len(tickers), "ts": int(time.time())})
    note("flottant", ok=bool(rows), err=None if rows else "aucune ligne lisible")
    log(f"flottant officiel : {len(rows)} sociétés lues sur {len(tickers)} ({r['d']})")


# ------------------------------------------------------------------ notations financières (Bloomfield, WARA / EMR, GCR) publiées sur brvm.org
GRADE = r"(?:AAA|AA\+|AA-|AA|A\+|A-|A|BBB\+|BBB-|BBB|BB\+|BB-|BB|B\+|B-|B|CCC\+|CCC-|CCC|CC|C|D|SD)"
GRADE_ST = r"(?:A1\+|A1-|A1|A2\+|A2-|A2|A3\+|A3-|A3|B|C|D|w-[1-6])"
SUFFIX = r"(?:\s*\((?i:WU|WA|SN|CI|BF|ML|NE|TG|BJ|GW|UEMOA|SF|EL)\)){0,3}"


RATING_PV = 3  # version du lecteur : une fiche lue par une version antérieure est relue


NB_ = r"(?<![\w/'])"  # une note n'est jamais collée à une lettre, une barre (N/A) ou une apostrophe (d'émetteur)
NA_ = r"(?![\w/'])"


def _gnorm(g):
    """« sfAAA(WU) » -> « AAA(WU)(SF) » ; espaces retirés ; suffixe en majuscules."""
    g = re.sub(r"\s+", "", g)
    sf = g.startswith("sf")
    g = re.sub(r"\(([a-zA-Z]+)\)", lambda m: "(" + m.group(1).upper() + ")", g[2:] if sf else g)
    return g + "(SF)" if sf and "(SF)" not in g else g


def _grades(x, g_re):
    """Notes présentes dans un texte, sans confondre une initiale (« Câbles », « Côte », « N/A », « d'… ») avec une note."""
    gs = re.findall(NB_ + "((?:sf)?" + g_re + SUFFIX + ")" + NA_, x)
    return [_gnorm(g) for g in gs if not re.fullmatch(r"(?i)(CFA|SF)", g)]


def rating_parse(txt):
    """Note long terme (et court terme), note précédente, perspective, date d'expiration et agence, lues dans une fiche ou un communiqué de notation.
    Rien n'est déduit : un champ absent du document reste vide."""
    t = re.sub(r"[’‘]", "'", txt)
    n = _nrm(t)
    r = {"pv": RATING_PV}
    ag = ("Bloomfield" if "bloomfield" in n else "WARA" if re.search(r"\bwara\b|west africa rating", n) else "GCR" if re.search(r"\bgcr\b", n)
          else "Moody's" if "moody" in n else "S&P" if re.search(r"standard\s*&\s*poor|s&p global", n) else "Fitch" if "fitch" in n else None)
    if ag:
        r["ag"] = ag
    lines = [re.sub(r"\s+", " ", x).strip() for x in t.splitlines() if x.strip()]
    hdr = next((x for x in lines if re.search(r"note (actu|pr[eé]c)", x, re.I)), "")
    if hdr:
        # fiches (Bloomfield, WARA) : ligne « Long Terme … note1 note2 date perspective » ; l'ordre note actuelle / précédente vient de l'en-tête
        prev_first = bool(re.search(r"actu", hdr, re.I)) and hdr.lower().find("pr") < hdr.lower().find("actu")
        for key, pat in (("lt", r"long\s*terme"), ("st", r"court\s*terme")):
            g_re = GRADE if key == "lt" else GRADE_ST
            for x in lines:
                if not re.search(pat, x, re.I) or re.search(r"^(sur le|notation de|note de) ", x, re.I):
                    continue
                gs = _grades(x, g_re)
                if not gs:
                    continue
                cur, prv = (gs[1], gs[0]) if prev_first and len(gs) > 1 else (gs[0], gs[1] if len(gs) > 1 else None)
                r[key] = cur
                if prv:
                    r[key + "0"] = prv
                d = re.search(r"(\d{2})/(\d{2})/(20\d\d)", x)
                if d:
                    r["exp"] = f"{d.group(3)}-{d.group(2)}-{d.group(1)}"
                o = re.search(r"(stable|positive|n[eé]gative|en (?:cours de )?(?:r[eé]vision|observation)|d[eé]veloppement)", x, re.I)
                if o and "out" not in r:  # perspective de la note long terme (lue en premier)
                    r["out"] = o.group(1).lower().replace("é", "e")
                break
    else:
        # communiqués (GCR, WARA) : la phrase d'action fait foi (« rehausse … de A(WU) à AA-(WU) », « affirme … de A+(WU) »),
        # puis, à défaut, la première ligne du tableau « Emetteur de long terme | Régionale | AA-(WU) | Stable ».
        # Les notes sont en majuscules : les mots « a », « à », « de », « d' » du texte ne peuvent pas être pris pour une note.
        flat = re.sub(r"\s+", " ", t)
        flat = re.sub(r"[«\"']\s*((?:sf)?(?:" + GRADE + "|" + GRADE_ST + ")" + SUFFIX + r")\s*[»\"']", r" \1 ", flat)
        A_, DE_ = r"\s+(?i:à|a)\s+", r"(?i:\bde)\s+"
        VERB = r"(?i:assign|affirm|attribu|rehauss|réhauss|abaiss|r[ée]vis|plac|confirm|maint|retir)"
        if re.search(r"(?i:\bretir)\w*\s+(?i:les notations|la notation|les notes|la note)", flat[:900]):
            return {**r, "lt": "WD", "st": "WD", "out": "retiree"}  # notation retirée (« WD ») : aucune note en vigueur
        # phrase-titre du communiqué (première phrase portant l'action) : la plus fiable, surtout pour les communiqués en colonnes (WARA)
        hl = next((x for x in re.split(r"(?<=[a-zé\)»'])\.\s", flat[:900]) if re.search(VERB, x)), "")
        if hl and not (re.search(r"(?i:court terme)", hl) and not re.search(r"(?i:long terme)", hl)):
            G = NB_ + "((?:sf)?" + GRADE + SUFFIX + ")" + NA_
            one = lambda m, k=1: (_grades(m.group(k), GRADE) or [None])[0]
            m = re.search(DE_ + G + A_ + G, hl)
            if m:
                r["lt0"], r["lt"] = one(m), one(m, 2)
            elif re.search(A_ + G + r"\s+" + DE_ + G, hl):
                m = re.search(A_ + G + r"\s+" + DE_ + G, hl)
                r["lt"], r["lt0"] = one(m), one(m, 2)
            else:
                m = re.search(VERB + r"[^.]{0,140}?(?:" + DE_ + r"|" + A_ + r"|(?i:terme)\s+)" + G, hl)
                if m:
                    r["lt"] = one(m)
                    if re.search(r"(?i:affirm|confirm|maint|plac)", hl):
                        r["lt0"] = r["lt"]
        for key, word, g_re in (("lt", "long", GRADE), ("st", "court", GRADE_ST)):
            if key in r:
                continue
            G = NB_ + "((?:sf)?" + g_re + SUFFIX + ")" + NA_
            head = r"(?i:de " + word + r"\s+terme)[^.]{0,160}?"
            one = lambda m, k=1, g_re=g_re: (_grades(m.group(k), g_re) or [None])[0]
            m = re.search(head + DE_ + G + A_ + G, flat)
            if m:
                r[key + "0"], r[key] = one(m), one(m, 2)
                continue
            m = re.search(head + A_ + G + r"\s+" + DE_ + G, flat)
            if m:
                r[key], r[key + "0"] = one(m), one(m, 2)
                continue
            m = re.search(head + r"(?i:affirm|confirm|maintenu)\w*\s+(?i:à|a)\s+" + G, flat)
            if m:
                r[key] = r[key + "0"] = one(m)
                continue
            m = (re.search(head + DE_ + G, flat) or re.search(head + r"(?i:\best)\s+" + G, flat)
                 or re.search(r"(?i:de " + word + r"\s+terme)\s+" + G, flat) or re.search(head + A_ + G, flat))
            if m:
                r[key] = one(m)
                if re.search(r"(?i:affirm|confirm|maint|plac)[^.]{0,80}" + head, flat):
                    r[key + "0"] = r[key]
                continue
            for x in lines:
                if re.search(r"(?i)(e|é)metteur de " + word + r" terme|note de " + word + r" terme", x) and not re.search(r"(?i)(rehauss|abaiss|affirm|attribu|relev|plac|r[ée]vis)", x):
                    gs = _grades(x, g_re)
                    if gs:
                        r[key] = gs[-1]
                        break
        for k in ("lt", "lt0", "st", "st0"):
            if not r.get(k):
                r.pop(k, None)
    if "out" not in r:  # « la perspective passe de positive à stable » : la nouvelle perspective est la seconde
        m = re.search(r"perspective[^.]{0,60}?passe[^.]{0,30}?(?:\bde|d')\s*\w+\s+a\s+(stable|positive|negative)\b", n) or \
            re.search(r"perspective[^.]{0,80}?\b(stable|positive|negative)\b", n)
        if m:
            r["out"] = m.group(1)
    v = re.search(r"validit[eé]\s*:?\s*([^\n]{6,60})", t, re.I)
    if v and re.search(r"20\d\d", v.group(1)):  # période de validité datée (fiches), pas une phrase du communiqué
        r["val"] = v.group(1).strip()
    if re.search(r"echelle regionale|\(wu\)", n):
        r["scale"] = "régionale"
    elif re.search(r"echelle nationale", n):
        r["scale"] = "nationale"
    return r if "lt" in r or "st" in r else None


def run_ratings(raw, site_data, limit=200):
    """Notices de notation publiées sur brvm.org (sociétés cotées et émetteurs d'obligations) : PDF lus (texte, sinon OCR) et notes extraites.
    Lecture incrémentale : `limit` nouveaux documents par passage ; le reste suit les soirs suivants."""
    path = os.path.join(raw, "ratings.json")
    st = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {"docs": {}}
    docs = st.setdefault("docs", {})
    todo = {}
    try:  # base d'avis tierce (historique depuis 2005)
        for x in harzat_json("events.json")["events"]:
            u = x.get("document_url")
            if x.get("category") == "rating" and u and u.lower().endswith(".pdf"):
                todo[u] = {"t": x.get("ticker"), "soc": x.get("issuer"), "d": x.get("published_at") or x.get("event_at"), "ti": x.get("title")}
    except Exception as e:  # noqa: BLE001
        note("ratings", False, f"base d'avis : {e}")
    av = os.path.join(site_data or "", "avis_brvm.json")
    if site_data and os.path.exists(av):  # avis lus directement sur brvm.org
        for u, r in (json.load(open(av, encoding="utf8")).get("items") or {}).items():
            if r.get("k") == "notation" or r.get("c") == "Notation financière":
                todo.setdefault(u, {"t": None, "soc": r.get("soc"), "d": r.get("d"), "ti": r.get("ti")})
    new = [u for u in sorted(todo, key=lambda u: todo[u].get("d") or "", reverse=True) if u not in docs or (docs[u].get("pv") or 1) < RATING_PV][:limit]
    if new and not pdf_tools():
        return
    n_ok = 0
    for u in new:
        meta = todo[u]
        try:
            txt = avis_text(u)
            r = rating_parse(txt) or {}
            docs[u] = {**meta, **r, "pv": RATING_PV, "read": TODAY.isoformat()}
            n_ok += bool(r)
        except Exception as e:  # noqa: BLE001
            docs[u] = {**meta, "err": str(e)[:120], "pv": RATING_PV, "read": TODAY.isoformat()}
            note("ratings", False, f"{u[-60:]}: {e}")
    for u, meta in todo.items():  # métadonnées (titre, société) tenues à jour
        if u in docs:
            for k in ("t", "soc", "d", "ti"):
                if meta.get(k) and not docs[u].get(k):
                    docs[u][k] = meta[k]
    st["ts"] = int(time.time())
    save(path, st)
    note("ratings")
    log(f"notations : {len(docs)} documents connus, {len(new)} lus ce soir ({n_ok} avec une note), {len(todo) - len(docs)} restants")


# ------------------------------------------------------------------ intervenants du marché (annuaires officiels de brvm.org)
SGI_DIRS = [("sgi", "/fr/intervenants/sgi/tous", "SGI"), ("sgo", "/fr/societes-de-gestion-d-opcvm", "Sociétés de gestion d'OPCVM"),
            ("sgp", "/fr/intervenants/sgp/tous", "Sociétés de gestion de patrimoine"), ("cons", "/fr/intervenants/conservateurs/tous", "Banques teneurs de compte - conservateurs"),
            ("agn", "/fr/autres-acteurs/agences-de-notation", "Agences de notation"), ("gar", "/fr/autres-acteurs/garants", "Garants")]
TEL_CTY = {"221": "Sénégal", "223": "Mali", "225": "Côte d'Ivoire", "226": "Burkina Faso", "227": "Niger", "228": "Togo", "229": "Bénin", "245": "Guinée-Bissau"}


def dir_parse(html):
    """Fiches d'un annuaire brvm.org (nom, pays du drapeau, adresse, boîte postale, courriel, téléphone, fax, site)."""
    i = html.find("view-content")
    seg = html[i:] if i >= 0 else html
    out = []
    for blk in re.split(r'<div class="views-row ', seg)[1:]:
        m = re.search(r'<span class="field-content"><div class="([^"]*)">(.*?)</div>', blk, re.S)
        if not m:
            continue
        pays = HTML.unescape(m.group(1)).strip()
        if pays in ("title", "field-content") or len(pays) > 25:
            pays = ""
        nom = re.sub(r"\s+", " ", HTML.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        if not nom or pays.startswith("bloc"):
            continue
        g = lambda cls: (lambda mm: re.sub(r"\s+", " ", HTML.unescape(re.sub(r"<[^>]+>", " ", mm.group(1)))).strip() if mm else "")(re.search(r'<div class="' + cls + r'[^>]*>(.*?)</div>', blk, re.S))  # noqa: E731
        mail = re.search(r'mailto:([^"]+)"', blk)
        tel = g("tel_sgi")
        if not pays:  # drapeau absent : pays d'après l'indicatif téléphonique officiel
            k = re.search(r"(?:\+|00)?\s*(2[0-9]{2})\b", tel)
            pays = TEL_CTY.get(k.group(1), "") if k else ""
            if pays:
                pays += " *"
        out.append({"n": nom, "pays": pays, "adr": g("adresse_sgi"), "bp": g("bp"), "mail": mail.group(1) if mail else "", "tel": tel, "fax": g("fax_sgi"), "web": g("site_sgi")})
    return out


def run_sgi(raw):
    """Annuaires officiels des intervenants (SGI, SGO, SGP, conservateurs, agences de notation, garants) lus sur brvm.org, toutes pages."""
    res = {}
    for key, path_, label in SGI_DIRS:
        rows, seen = [], set()
        for pg in range(12):
            try:
                html = get("https://www.brvm.org" + path_ + (f"?page={pg}" if pg else ""), tries=2, timeout=30).decode("utf8", "replace")
            except Exception as e:  # noqa: BLE001
                note("sgi", False, f"{key} p{pg}: {e}")
                break
            part = dir_parse(html)
            new = [r for r in part if (r["n"].lower(), r["tel"]) not in seen]
            if not new:
                break
            for r in new:
                seen.add((r["n"].lower(), r["tel"]))
            rows += new
            if f"{path_}?page={pg + 1}" not in html:
                break
        if rows:
            note("sgi")
        res[key] = {"label": label, "u": "https://www.brvm.org" + path_, "rows": rows}
    if any(v["rows"] for v in res.values()):
        save(os.path.join(raw, "sgi.json"), {"ts": int(time.time()), "d": TODAY.isoformat(), "dirs": res})
    log("intervenants :", ", ".join(f"{k} {len(v['rows'])}" for k, v in res.items()))


# ------------------------------------------------------------------ dividendes des actions et ETF US (Nasdaq : date de détachement, montant, paiement)
def run_usdiv(raw):
    """Historique des dividendes de l'univers US suivi (Nasdaq), pour les rendements totaux (dividendes réinvestis) et DVD."""
    path = os.path.join(raw, "us_divs.json")
    st = json.load(open(path, encoding="utf8")) if os.path.exists(path) else {"s": {}}
    syms = [(x[0], "etf" if x[2] == "ETF" else "stocks") for x in US]
    try:
        meta = json.load(open(os.path.join(raw, "nasdaq_meta.json"), encoding="utf8"))
        syms += [(x["s"], "stocks") for x in meta.get("ndx") or [] if x.get("s") and x["s"] not in {a for a, _ in syms}]
    except Exception:  # noqa: BLE001
        pass

    def one(it):
        sym, cls = it
        try:
            j = json.loads(get(f"https://api.nasdaq.com/api/quote/{urllib.parse.quote(sym)}/dividends?assetclass={cls}", headers=NQ_H, tries=2, timeout=40))
            rows = (((j.get("data") or {}).get("dividends") or {}).get("rows")) or []
            out = []
            for r in rows:
                d = r.get("exOrEffDate") or ""
                m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d)
                amt = money(r.get("amount"))
                if not m or not amt or (r.get("type") or "Cash").lower() != "cash":
                    continue
                pm = re.match(r"(\d{2})/(\d{2})/(\d{4})", r.get("paymentDate") or "")
                out.append([f"{m.group(3)}-{m.group(1)}-{m.group(2)}", round(amt, 4), f"{pm.group(3)}-{pm.group(1)}-{pm.group(2)}" if pm else None])
            return sym, sorted(out), None
        except Exception as e:  # noqa: BLE001
            return sym, None, str(e)
    n_ok = 0
    with ThreadPoolExecutor(4) as ex:
        for sym, rows, err in ex.map(one, syms):
            if rows is None:
                note("us-div", False, f"{sym}: {err}")
                continue
            note("us-div")
            st["s"][sym] = rows
            n_ok += 1
    st["ts"] = int(time.time())
    save(path, st)
    log(f"dividendes US : {n_ok} titres lus, {sum(1 for v in st['s'].values() if v)} avec au moins un dividende")


def pdf_tools():
    """Outils de lecture des avis (texte du PDF, images de pages, reconnaissance de caractères), installés à la demande."""
    import shutil
    if not (shutil.which("pdftotext") and shutil.which("pdftoppm") and shutil.which("tesseract")):
        os.system("sudo apt-get install -y -qq poppler-utils tesseract-ocr tesseract-ocr-fra >/dev/null 2>&1")
    return bool(shutil.which("pdftotext") and shutil.which("pdftoppm") and shutil.which("tesseract"))


def avis_text(u):
    """Texte d'un avis PDF : couche texte quand elle existe, sinon reconnaissance de caractères des deux premières pages."""
    import glob, subprocess, tempfile
    pdf = get(u, tries=2, timeout=40)
    with tempfile.TemporaryDirectory() as td:
        p_ = os.path.join(td, "a.pdf")
        open(p_, "wb").write(pdf)
        t = subprocess.run(["pdftotext", "-layout", p_, "-"], capture_output=True, timeout=60).stdout.decode("utf8", "replace")
        if len(t.strip()) > 200:
            return t
        subprocess.run(["pdftoppm", "-r", "200", "-png", "-f", "1", "-l", "2", p_, os.path.join(td, "pg")], capture_output=True, timeout=120)
        langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, timeout=30).stdout.decode()
        lang = "fra" if "\nfra" in langs else "eng"
        return "\n".join(subprocess.run(["tesseract", f, "-", "-l", lang], capture_output=True, timeout=120).stdout.decode("utf8", "replace")
                         for f in sorted(glob.glob(os.path.join(td, "pg*.png"))))


def _amt_fr(x):
    x = re.sub(r"[\s \xa0]", "", x)
    if "," in x:
        x = x.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", x):
        x = x.replace(".", "")
    return float(x)


def div_parse(txt, old=None):
    """Montant du dividende d'un avis de la BRVM : net (« 124 FCFA net par action », « dividende net annuel de 0,9 FCFA »)
    ou brut avec l'IRVM des personnes physiques (« 800 FCFA par action (IRVM applicable de 12 % ...) ») ; exercice, détachement, paiement.
    Pour un rectificatif, `old` = ancien montant : le nouveau montant est le premier montant cité qui en diffère."""
    n = re.sub(r"\s+", " ", _nrm(txt))
    # la reconnaissance de caractères lit souvent « à » comme « 4 » : « s'élève à 229 » -> « s'eleve 4 229 »
    n = re.sub(r"(eleve|elevera|elevait|porte|portee|ramene|ramenee|fixe|fixee|etablit|etablira|passe|passera|egal|egale) [4a] (?=\d)", r"\1 a ", n)
    am = [(m.start(), m.end(), _amt_fr(m.group(1)), m.group(2) or "") for m in re.finditer(r"(\d[\d ., \xa0]*\d|\d)\s*f\s?cfa\s*(net|brut)?", n)]
    am = [a for a in am if "dividende" in n[max(0, a[0] - 220):a[0]] and a[2] > 0]
    if not am:
        return None
    # rectificatif : « Ce montant vient en rectification de celui de 124 FCFA net précédemment communiqué »
    rect = re.search(r"(?:rectification|remplacement|lieu et place|au lieu) (?:de )?(?:celui de )?(\d[\d .,]*\d|\d) ?f ?cfa ?(net|brut)?", n)
    if rect and not old:
        old = _amt_fr(rect.group(1))
    pick = am[0]
    if old:
        diff = [a for a in am if abs(a[2] / old - 1) > .005]
        if diff:
            pick = diff[0]
    st_, en_, amt, kind = pick
    before, after = n[max(0, st_ - 40):st_], n[en_:en_ + 40]
    if not kind and (re.search(r"net (annuel )?de $", before) or after.lstrip().startswith("net")):
        kind = "net"
    if not kind and re.search(r"brut (annuel )?de $", before):
        kind = "brut"
    r = {"amt": amt}
    if old and not kind and not re.search(r"irvm", n[st_:st_ + 260]) and (not rect or (rect.group(2) or "net") == "net"):
        kind = "net"  # rectificatif sans précision : même nature que le montant rectifié (publié net)
    irvm = re.search(r"irvm[^%]{0,60}?(\d{1,2}(?:[.,]\d+)?) ?%", n[st_:st_ + 260])
    if kind == "net":
        r["net"] = amt
    elif irvm:
        r["brut"], r["irvm"] = amt, float(irvm.group(1).replace(",", "."))
        r["net"] = round(amt * (1 - r["irvm"] / 100), 2)
    elif kind == "brut":
        r["brut"] = amt
    ex = re.search(r"exercice (20\d\d)", n)
    r["ex"] = int(ex.group(1)) if ex else None
    mois = "|".join(FR_MOIS)
    for key, pat in (("pay", r"en paiement,? le (?:\w+ )?(\d{1,2})(?:er)? (" + mois + r") (20\d\d)"), ("det", r"ex-? ?dividende a partir du (?:\w+ )?(\d{1,2})(?:er)? (" + mois + r") (20\d\d)")):
        m = re.search(pat, n)
        if m:
            try:
                r[key] = dt.date(int(m.group(3)), FR_MOIS[m.group(2)], int(m.group(1))).isoformat()
            except ValueError:
                pass
    return r

FR_MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}


def ag_date(txt, pub):
    """Date de la réunion dans un avis de convocation : première date écrite en toutes lettres, précédée de peu par
    « assemblée », « se tiendra », « réunion » ou « convoqués », comprise entre la publication et 4 mois après. None sinon."""
    t = _nrm(txt)
    try:
        p0 = dt.date.fromisoformat(pub[:10])
    except (TypeError, ValueError):
        return None
    for m in re.finditer(r"(?:(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+)?(\d{1,2})(?:er)?\s+(" + "|".join(FR_MOIS) + r")\s+(20\d{2})", t):
        try:
            d = dt.date(int(m.group(3)), FR_MOIS[m.group(2)], int(m.group(1)))
        except ValueError:
            continue
        if p0 <= d <= p0 + dt.timedelta(days=120) and re.search(r"assemblee|se tiendra|reunion|convoque", t[max(0, m.start() - 250):m.start()]):
            return d.isoformat()
    return None



# ------------------------------------------------------------------ fractionnements des actions US (Yahoo Finance, événements « split »)
def run_ussplit(raw):
    """Ramène le nombre de titres publié dans les dépôts SEC à la base actuelle quand un fractionnement a eu lieu depuis le dépôt."""
    facts = os.path.join(raw, "secfacts.json")
    syms = sorted((json.load(open(facts, encoding="utf8")).get("co") or {}).keys()) if os.path.exists(facts) else [x[0] for x in US if x[2] != "ETF"]
    out = {}

    def one(sym):
        err = None
        for host in ("query1", "query2"):
            try:
                j = json.loads(get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=15y&interval=3mo&events=split", tries=2, timeout=30,
                                   headers={"Referer": "https://finance.yahoo.com/", "Origin": "https://finance.yahoo.com"}))
                res = ((j.get("chart") or {}).get("result") or [{}])[0] or {}
                ev = (res.get("events") or {}).get("splits") or {}
                return sym, sorted([dt.datetime.fromtimestamp(int(v["date"]), dt.timezone.utc).strftime("%Y-%m-%d"), v["numerator"] / v["denominator"]]
                                   for v in ev.values() if v.get("denominator") and v.get("numerator")), None
            except Exception as e:  # noqa: BLE001
                err = e
        return sym, None, str(err)
    with ThreadPoolExecutor(6) as ex:
        for sym, sp, err in ex.map(one, syms):
            if sp is None:
                note("us-splits", False, f"{sym}: {err}")
                continue
            note("us-splits")
            out[sym] = sp
    if out:
        save(os.path.join(raw, "us_splits.json"), {"ts": int(time.time()), "s": out})
    log(f"fractionnements US : {len(out)} titres, {sum(1 for v in out.values() if v)} avec au moins un fractionnement sur 15 ans")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="dossier brut (branche quant-raw), lu et réécrit sur place")
    ap.add_argument("--only", default="nasdaq,fred,cboe,cnn,crypto,wb,sec,analyst,boc,probe")
    ap.add_argument("--news", default=None, help="fichier news.json à mettre à jour (mode séance)")
    ap.add_argument("--site", default=None, help="dossier data/ du site (veille : reports.json, news.json)")
    ap.add_argument("--sec-max-age-days", type=float, default=6)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    only = set(a.only.split(",")) if a.only else set()
    t0 = time.time()
    steps = [("cal", lambda: run_cal(a.out, a.site)), ("avis", lambda: run_avis(a.site)), ("nasdaq", lambda: run_nasdaq(a.out, a.out)), ("fred", lambda: run_fred(a.out)), ("fomc", lambda: run_fomc(a.out)), ("cboe", lambda: run_cboe(a.out)),
             ("cnn", lambda: run_cnn(a.out)), ("crypto", lambda: run_crypto(a.out, a.out)), ("wb", lambda: run_wb(a.out)),
             ("sec", lambda: run_sec(a.out, a.out, a.sec_max_age_days)), ("analyst", lambda: run_analyst(a.out)),
             ("probe", lambda: run_probe(a.out)), ("boc", lambda: run_boc(a.out)), ("sikah", lambda: run_sikah(a.out)), ("pdffin", lambda: run_pdffin(a.out)), ("comptes", lambda: run_comptes(a.out)), ("comptes_list", lambda: run_comptes_list(a.out)), ("watch", lambda: run_watch(a.out, a.site)), ("prof", lambda: run_prof(a.out)), ("profus", lambda: run_profus(a.out)),
             ("bceao", lambda: run_bceao(a.out)), ("umoa", lambda: run_umoa(a.out)), ("obl", lambda: run_obl(a.out, a.site)), ("cmc", lambda: run_cmc(a.out, a.site)), ("eia", lambda: run_eia(a.out)), ("fut", lambda: run_fut(a.out)), ("bochist", lambda: run_bochist(a.out)), ("divhist", lambda: run_divhist(a.out)), ("ussplit", lambda: run_ussplit(a.out)), ("avisocr", lambda: run_avisocr(a.site)), ("flottant", lambda: run_flottant(a.out, a.site)), ("ratings", lambda: run_ratings(a.out, a.site)), ("sgi", lambda: run_sgi(a.out)), ("usdiv", lambda: run_usdiv(a.out)), ("ei", lambda: run_ei(a.out))]
    if a.news:
        steps.insert(0, ("news", lambda: run_news(a.news)))
        only.add("news")
    rp = os.path.join(a.out, "report_" + "-".join(sorted(only)) + ".json")
    for name, fn in steps:
        if name not in only:
            continue
        t = time.time()
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            note(name, False, f"étape interrompue : {e} {traceback.format_exc()[-300:]}")
        REPORT.setdefault("_steps", {})[name] = round(time.time() - t)
        REPORT["_"] = {"ts": int(time.time()), "secs": round(time.time() - t0)}
        save(rp, REPORT)  # écrit après chaque étape : visible même si le passage est interrompu
        log(f"{name}: {time.time() - t:.0f} s", json.dumps({k: (v['ok'], v['err']) for k, v in REPORT.items() if isinstance(v, dict) and 'ok' in v}))
    log(f"terminé en {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
