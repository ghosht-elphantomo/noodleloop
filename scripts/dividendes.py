#!/usr/bin/env python3
"""Dividendes des sociétés cotées à la BRVM depuis 1998, lus dans les documents officiels.

Sources (par ordre de preuve) :
  1. avis de la BRVM « paiement de dividendes » (montant brut, impôt, net par action, date ex-dividende, date de paiement) ;
  2. bulletins officiels de la cote (dernier dividende net payé et sa date) ;
  3. documents des sociétés déposés à la BRVM (dividende brut / net par action proposé ou décidé par l'assemblée) ;
  4. miroirs (SikaFinance, BRVMetrics) : seulement pour signaler un écart ou combler un exercice sans document officiel.
Aucun montant n'est calculé pour combler un manque ; un montant net n'est déduit d'un brut que si l'avis donne le taux d'impôt.

Usage : dividendes.py --dir DOSSIER   (index.json et txt/ écrits par fetch_extra.py --only divhist) -> DOSSIER/dividendes.json
"""
import argparse, collections, datetime as dt, gzip, json, os, re, unicodedata, urllib.parse

FR_MOIS = {"janvier": 1, "janv": 1, "fevrier": 2, "fevr": 2, "fev": 2, "mars": 3, "avril": 4, "avr": 4, "mai": 5, "juin": 6, "juillet": 7, "juil": 7,
           "aout": 8, "septembre": 9, "sept": 9, "octobre": 10, "oct": 10, "novembre": 11, "nov": 11, "decembre": 12, "dec": 12}
MOIS_RX = "janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre"


def nrm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return s.replace("’", "'").replace("\xa0", " ").replace(" ", " ")


def amt(x):
    """« 2 606 », « 2.293,28 », « 1 553,847 », « 145,3214 », « 0,9 » -> nombre ; None si illisible. Avis et documents en
    français : la virgule est toujours décimale, l'espace ou le point sépare les milliers."""
    x = re.sub(r"[\s\u202f\xa0\u2009]", "", x or "")
    if not x:
        return None
    if "," in x:
        x = x.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", x):
        x = x.replace(".", "")
    try:
        return float(x)
    except ValueError:
        return None


def fr_date(s):
    m = re.search(r"(\d{1,2})(?:er)?\s+(" + MOIS_RX + r")\s+((?:19|20)\d\d)", s)
    if m:
        try:
            return dt.date(int(m.group(3)), FR_MOIS[m.group(2)], int(m.group(1))).isoformat()
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-]((?:19|20)\d\d)", s)
    if m:
        try:
            return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None
    return None


NUM = r"(\d{1,3}(?:[ . \xa0]\d{3})+(?:,\d+)?|\d+(?:[,.]\d+)?)"


def parse_company(txt, fy=None):
    """Dividende par action dans un document de société (rapport annuel, états financiers, résolutions) :
    [{"ex", "brut", "net", "q"}] ; q = qualité (2 : brut et net cohérents dans la même phrase ; 1 : un seul montant par action)."""
    t = re.sub(r"[ \t]+", " ", nrm(txt))
    t = re.sub(r"\bf\.? ?cfa\b|\bfcfa\b|\bf cfa\b|\bxof\b", " fcfa", t)
    out = []
    ex_doc = None
    m = re.search(r"(?:au titre de l'exercice|exercice clos le 31 decembre|exercice) ((?:19|20)\d\d)", t)
    if m:
        ex_doc = int(m.group(1))
    for m in re.finditer(r"dividende(?:s)? brut(?:s)?[^.;\n]{0,60}?(?:de|a|:)\s*(?:fcfa\s*)?" + NUM + r"\s*(?:fcfa)?\s*(?:par action|/ ?action|brut par action)"
                         r"(?:[^.;\n]{0,80}?dividende(?:s)? net(?:s)?[^.;\n]{0,30}?(?:de|a|:)\s*(?:fcfa\s*)?" + NUM + r")?", t):
        b, n = amt(m.group(1)), amt(m.group(2)) if m.group(2) else None
        if b and (n is None or n <= b):
            ctx = t[max(0, m.start() - 200):m.end() + 120]
            e = re.search(r"exercice ((?:19|20)\d\d)", ctx)
            out.append({"ex": int(e.group(1)) if e else (ex_doc or fy), "brut": b, "net": n, "q": 2 if n else 1, "s": t[m.start():m.end()][:160]})
    for m in re.finditer(r"dividende(?:s)? net(?:s)?(?: par action)?[^.;\n]{0,40}?(?:de|a|:)\s*(?:fcfa\s*)?" + NUM + r"\s*(?:fcfa)?\s*(?:par action|/ ?action)", t):
        n = amt(m.group(1))
        if n and not any(abs((o.get("net") or -1) - n) < .01 for o in out):
            ctx = t[max(0, m.start() - 200):m.end() + 120]
            e = re.search(r"exercice ((?:19|20)\d\d)", ctx)
            out.append({"ex": int(e.group(1)) if e else (ex_doc or fy), "brut": None, "net": n, "q": 1, "s": t[m.start():m.end()][:160]})
    return out


DATE_RX = r"(?:(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+)?(\d{1,2})(?:er)?\s+(" + MOIS_RX + r")\s+((?:19|20)\d\d)"


def _d(m, i=1):
    try:
        return dt.date(int(m.group(i + 2)), FR_MOIS[m.group(i + 1)], int(m.group(i))).isoformat()
    except (ValueError, KeyError):
        return None


NOT_AVIS = re.compile(r"^boc[_\-]|bulletin|manuel|regles|reglement|instruction|jbc|rapport|etats?[_ %20\-]*fin")


def parse_avis(txt):
    """Avis de la BRVM (ou du Dépositaire central) sur un paiement de dividendes.
    Renvoie [] si l'avis ne porte pas sur un dividende, sinon une liste d'un élément :
      {"num", "org", "sym", "soc", "ex", "pay", "det", "parts": [{"kind", "brut", "net", "irvm", "irvm_pm"}],
       "net_total", "rect_old", "rect", "frac", "s"}
    kind : « annuel », « exceptionnel », « acompte », « solde », « fraction » ; net : montant net par action pour une personne
    physique, écrit dans l'avis ou déduit du brut et du taux d'IRVM des personnes physiques donné par l'avis."""
    t = nrm(txt)
    t = re.sub(r"\bf\.? ?c\.? ?f\.? ?a\b|\bfcfa\b|\bf cfa\b", "fcfa", t)
    f = re.sub(r"\s+", " ", t)
    if "dividende" not in f:
        return []
    r = {}
    m = re.search(r"avis n ?[°o]? ?(\d{1,3}) ?[-–_]? ?((?:19|20)\d\d)? ?/ ?(brvm|dc ?/ ?br)", f)
    if m:
        r["num"], r["org"] = int(m.group(1)), "DC/BR" if "dc" in m.group(3) else "BRVM"
        if m.group(2):
            r["yr"] = int(m.group(2))
    m = re.search(r"symbole ?: ?([a-z]{3,6})\b", f)
    r["sym"] = m.group(1).upper() if m else None
    m = re.search(r"(?:la societe|que la|que le|que l'|du dividende annuel de la societe|de la societe)\s+([a-z0-9&'().\- ]{2,70}?)\s*(?:\(([a-z]{3,6})\)\s*)?(?:mettra|procedera|a decide|va proceder|paiera|versera|au titre|,)", f)
    if m:
        r["soc"] = m.group(1).strip(" .,-")
        if m.group(2) and not r["sym"]:
            r["sym"] = m.group(2).upper()
    m = re.search(r"(?:mettra en paiement|sera mis en paiement|seront mis en paiement|sera verse|seront verses|a payer|paiement interviendra)[^.]{0,60}?le " + DATE_RX, f)
    r["pay"] = _d(m) if m else None
    m = re.search(r"ex ?-? ?(?:dividende|coupon) a (?:partir|compter) du " + DATE_RX, f)
    r["det"] = _d(m) if m else None
    m = re.search(r"fermeture des registres? (?:etant )?fixee au " + DATE_RX, f)
    r["rec"] = _d(m) if m else None  # (date d'arrêté des registres : jour du paiement dans les avis récents)
    m = re.search(r"fait a abidjan,? le " + DATE_RX, f)
    r["pub"] = _d(m) if m else None
    # date dont l'année est mal lue ou mal imprimée (« mardi 26 mai 2005 » dans un avis n° 46-2009 aux registres fermés le 28 mai 2009 ;
    # « paiement le 30 mai 2024 » ou « fait à Abidjan le 15 mai 2024 » dans un avis n° 107-2025) : année de référence = celle du
    # numéro de l'avis, sinon celle que partagent la majorité des dates de l'avis ; une date d'une autre année, à plus de 200 jours
    # d'une date de l'année de référence, prend cette année si elle tombe alors à moins de 60 jours d'elle (un avis de décembre pour
    # un détachement en janvier n'est pas touché : ses dates sont proches)
    ds_ = {k: dt.date.fromisoformat(r[k]) for k in ("det", "pay", "rec", "pub") if r.get(k)}
    y_ref = r.get("yr")
    if not y_ref and ds_:
        cy_ = collections.Counter(v.year for v in ds_.values()).most_common()
        y_ref = cy_[0][0] if len(cy_) == 1 or cy_[0][1] > cy_[1][1] else None
    if y_ref:
        ref_ds = [v for v in ds_.values() if v.year == y_ref]
        for k, v in ds_.items():
            if v.year == y_ref or not ref_ds:
                continue
            try:
                v2 = v.replace(year=y_ref)
            except ValueError:
                continue
            if any(abs((v2 - w).days) <= 60 and abs((v - w).days) > 200 for w in ref_ds):
                r[k] = v2.isoformat()
    # exercice : celui que l'avis annonce (« au titre de l'exercice 2002 », titre « Exercice 2002 ») ; une coquille (« exercice 2008 »
    # dans un avis de juillet 2004) est écartée : l'exercice précède l'année du détachement d'un ou deux ans
    ref_y = int((r.get("det") or r.get("rec") or r.get("pay") or r.get("pub") or "0")[:4])
    cand = [int(x) for x in re.findall(r"exercice(?: social)? ((?:19|20)\d\d)", f)]
    ok_ = [y for y in cand if not ref_y or ref_y - 2 <= y <= ref_y]
    r["ex"] = ok_[0] if ok_ else (cand[0] if cand and not ref_y else None)
    parts = []
    for m in re.finditer(r"(dividende(?: net)?(?: annuel| exceptionnel| ordinaire)?(?: net)?|acompte sur (?:le )?dividende|solde du dividende)(?: net)?(?: annuel)?(?: effectif)?(?: par action)?[^.;]{0,40}?(?:de|a|:) "
                         + NUM + r" ?fcfa( net)?(?: : )?(?: par action)?( net)?(?:[^.;]{0,15}?\(irvm applicable de (\d{1,2}(?:[.,]\d+)?) ?% pour les personnes physiques(?: et (\d{1,2}(?:[.,]\d+)?) ?% pour les personnes morales)?)?", f):
        a = amt(m.group(2))
        if not a or re.search(r"global|total|capital", m.group(0)):
            continue  # (montant global distribué, pas un montant par action)
        lab = m.group(1)
        kind = "exceptionnel" if "exception" in lab else "acompte" if "acompte" in lab else "solde" if "solde" in lab else "annuel"
        is_net = bool(m.group(3) or m.group(4) or " net" in lab)
        irvm = float(m.group(5).replace(",", ".")) if m.group(5) else None
        part = {"kind": kind}
        if is_net:
            part["net"] = a
        elif irvm is not None:
            part["brut"], part["irvm"] = a, irvm
            part["net"] = round(a * (1 - irvm / 100), 4)
            if m.group(6):
                part["irvm_pm"] = float(m.group(6).replace(",", "."))
        else:
            part["amt"] = a
        if not any(abs((p_.get("net") or p_.get("amt") or 0) - (part.get("net") or part.get("amt") or 0)) < 1e-6 and p_["kind"] == kind for p_ in parts):
            parts.append(part)
    # paiement fractionné : « fixé à 164,96 FCFA net par action sera versé en deux étapes ... à payer le 27 mai 2019 sera de 123,717 »
    m = re.search(r"dividende[^.;]{0,30}? de " + NUM + r" ?cents? de dollars?", f)
    if m:
        parts = [{"kind": "annuel", "usd_cents": amt(m.group(1))}]  # (montant en dollars : la contre-valeur FCFA vient du calendrier)
    m = re.search(r"fixe a " + NUM + r" ?fcfa net par action", f)
    if m:
        r["net_total"] = amt(m.group(1))
    m = re.search(r"(?:montant du dividende net a payer|dividende net a payer)[^.]{0,40}?sera de " + NUM + r" ?fcfa", f)
    if m:
        r["frac"] = amt(m.group(1))
        parts = [{"kind": "fraction", "net": r["frac"]}]
    m = re.search(r"(?:dividende net par action|soit un dividende net par action) de " + NUM + r" ?fcfa", f)
    if m and not parts:
        parts.append({"kind": "annuel", "net": amt(m.group(1))})
    # rectificatif : « s'élève à 237,15 FCFA. Ce montant vient en rectification de celui de 237,5 FCFA »
    m = re.search(r"s'eleve a " + NUM + r" ?fcfa( net)?([^.]*)\. ce montant vient en rectification de celui de " + NUM, f)
    if m:
        r["rect"] = True
        r["rect_old"] = amt(m.group(4))
        a_ = amt(m.group(1))
        ir_ = re.search(r"irvm applicable de (\d{1,2}(?:[.,]\d+)?) ?%", m.group(3) or "")
        if ir_ and not m.group(2):  # (montant brut, impôt donné : net des personnes physiques)
            irv = float(ir_.group(1).replace(",", "."))
            parts = [{"kind": "annuel", "brut": a_, "irvm": irv, "net": round(a_ * (1 - irv / 100), 4)}]
        else:
            parts = [{"kind": "annuel", "net": a_}]
    if re.search(r"annule et remplace|rectificati|modification du (?:montant du )?dividende", f):
        r["rect"] = True
    r["parts"] = parts
    r["s"] = f[:400]
    return [r]


# ---------------------------------------------------------------- calendriers de paiement des dividendes (BRVM, depuis 2018)
# « BOA BURKINA FASO   397   072-2026 BRVMDG   31/03/2026   22/04/2026 23/04/2026 » : montant net (ou brut si « (*) », impôt donné en
# note), numéro de l'avis, publication de l'avis au BOC, date ex-dividende, date de paiement. Les noms longs tiennent sur deux lignes.
CAL_ROW = re.compile(r"(?:(\d{1,3}(?:[ \u00a0\u202f\u2009]\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*(\(\*\))?\s*)?(\d{3})\s*-\s*((?:19|20)\d\d)\s*/?\s*(?:brvm\s*/?\s*dg|brvmdg|brvm|dc\s*/\s*br)", re.I)
DMY = re.compile(r"\b(\d{2})/(\d{2})/((?:19|20)\d\d)\b")


def _dmy(m):
    try:
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return None


def parse_calendar(txt):
    """Calendrier de paiement des dividendes : [{"name", "amt", "gross", "usd_cents", "num", "yr", "pub", "det", "pay"}] et le taux
    d'IRVM des personnes physiques donné en note pour les montants bruts (« (*) Dividende brut ; IRVM applicable de 12 % … »)."""
    L = txt.split("\n")
    nt = nrm(txt)
    m = re.search(r"\(\*\)\s*dividende brut\s*;?\s*irvm applicable de (\d{1,2}(?:[.,]\d+)?) ?%", nt)
    irvm = float(m.group(1).replace(",", ".")) if m else None
    rows = []
    for i, l in enumerate(L):
        mm = CAL_ROW.search(l)
        if not mm:
            continue
        ds = [_dmy(x) for x in DMY.finditer(l[mm.end():])]
        ds = [x for x in ds if x]
        if len(ds) < 2:
            continue
        amt_s, star = mm.group(1), bool(mm.group(2))
        pre = l[:mm.start()]
        cents = False
        if not amt_s:  # montant sur la ligne précédente (« 0,16 cents de » / « dollars »)
            pv = L[i - 1] if i > 0 else ""
            mx = re.search(r"(\d+(?:,\d+)?)\s*cents?", pv, re.I)
            if mx:
                amt_s, cents = mx.group(1), True
                pre = pv[:mx.start()]
        if amt_s is None:
            continue
        if re.search(r"cents?", l[:mm.start()] + (L[i - 1] if i else ""), re.I) and re.search(r"dollar", " ".join(L[max(0, i - 1):i + 2]), re.I):
            cents = True
        name = re.sub(r"cents?\s*de|\(\*\)", " ", pre, flags=re.I).strip()
        if "(*)" in pre:
            star = True
        # nom sur deux lignes : la ligne précédente et/ou suivante sans montant ni date
        def free(x):
            return x.strip() and not CAL_ROW.search(x) and not DMY.search(x) and not re.search(r"dividende brut|siege social|montant du|titres", nrm(x))
        split_ = not re.search(r"[a-z]{3}", nrm(name))  # (nom absent de la ligne du montant : écrit sur les lignes voisines)
        if i > 0 and free(L[i - 1]) and split_:
            name = (re.sub(r"\d+(?:,\d+)?\s*cents?\s*de|\(\*\)", " ", L[i - 1], flags=re.I).strip() + " " + name).strip()
        if split_ and i + 1 < len(L) and free(L[i + 1]) and len(L[i + 1].strip()) < 40 and len(L[i + 1]) - len(L[i + 1].lstrip()) < 20:
            nx = L[i + 1].strip()
            if "(*)" in nx:
                star = True
            name = (name + " " + re.sub(r"dollars?|\(\*\)", " ", nx, flags=re.I)).strip()
        name = re.sub(r"\s+\d{1,2}$", "", re.sub(r"\s+", " ", name).strip(" -"))  # (renvoi « 1 » en fin de nom)
        a_ = float(re.sub(r"[ \u00a0\u202f\u2009]", "", amt_s).replace(",", "."))  # (virgule décimale, espace des milliers)
        rows.append({"name": name, "amt": a_, "gross": star, "usd_cents": cents, "num": int(mm.group(3)), "yr": int(mm.group(4)),
                     "pub": ds[0] if len(ds) >= 3 else None, "det": ds[-2], "pay": ds[-1]})
    return rows, irvm


# ---------------------------------------------------------------- bulletins officiels de la cote de l'ancien site (2002-2012)
# « SNTS  SONATEL SN  …  5,085  6-juil-05  67,015  87,000 » : dernier dividende net payé et sa date de paiement, sur la ligne du titre.
MOIS_ABR = {"janv": 1, "jan": 1, "fevr": 2, "fev": 2, "feb": 2, "mars": 3, "mar": 3, "avr": 4, "apr": 4, "mai": 5, "may": 5, "juin": 6, "jun": 6,
            "juil": 7, "jul": 7, "aout": 8, "aug": 8, "sept": 9, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
BOC_DIV = re.compile(r"(?<![\d.,])(\d{1,3}(?:[ ,]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)\s+(\d{1,2})-([a-z]{3,5})\.?-(\d{2})\b")


def _boc_old_amt(tok, px):
    """Montant d'une colonne « dernier dividende » : virgule de milliers (« 1,800 ») ou décimale (« 321,08 », « 1,57 »),
    point décimal (« 1.828 », « 299.7 ») ; un « 1,828 » ambigu est tranché par l'ordre de grandeur du cours lu sur la même ligne
    (dividende net entre 0,05 % et 60 % du cours). None si aucune lecture n'est plausible."""
    t = tok.replace(" ", "")
    cands = []
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", t):
        cands.append(float(t.replace(",", "")))  # (milliers séparés par des virgules, décimales éventuelles après le point)
        if re.fullmatch(r"\d{1,3},\d{3}", t):
            cands.append(float(t.replace(",", ".")))  # (ou virgule décimale à trois chiffres)
    elif re.fullmatch(r"\d+,\d+", t):
        cands.append(float(t.replace(",", ".")))
    elif re.fullmatch(r"\d+(?:\.\d+)?", t):
        cands.append(float(t))
    if not px:
        return cands[0] if cands else None  # (sans cours sur la ligne : virgule de milliers, l'usage de ces bulletins)
    ok = [c for c in cands if 0.0005 <= c / px <= 0.6]
    return ok[0] if ok else None


BOC_EN_MOIS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
                                            "november", "december"), 1)}


_BOILER = re.compile(r"bourse regionale des valeurs|siege social|\btel\b|t[eé]l ?:|fax|e-?mail|site internet|antennes|\bb\.?p\.?\b|"
                     r"depositaire central|banque de reglement|www\.|@|\brc \d|\brc abidjan|rccm|r.?gistre du commerce|agrement|"
                     r"^(?:societe anonyme|s\.? ?a\.? avec)|societe anonyme.{0,40}capital|\bau capital de\b.*\d{3}|capital social|"
                     r"zone industrielle|\bimmeuble\b|\bpage \d+\b|\d\d?:\d\d|afrique de (?:l.? ?)?p?ouest\s*$|"
                     r"^\W*r.publique\b[^,;:]{0,30}$|\brc n|\bs\.?\s?a\.? au capital|^\W*prendre contact|"
                     r"^(?!.*(?:ordre|seance|cotation|transaction)).*\b[bge]?o?urse\b.*(?:mob|nob|valeu|valeh|regon|regional|\brer\b)|"
                     r"regional stock exchange|national offices|union mon.taire ouest africaine|conseil r.gional de l.?.pargne|"
                     r"^\W*(?:et )?des march.s financiers\W*$|^\W*le pr.sident\W*$|\brue\b|\bimmeuble\b|\b\d+(?:er|e|eme)? etage\b|\bzone \d+\b", re.I)


def _head_title(t):
    """Intitulé d'un document sans titre connu : ligne « Avis n° … / Communiqué … » et les deux lignes suivantes, sinon les deux
    premières lignes de texte (en-tête et coordonnées de l'émetteur écartés)."""
    L = []
    for l in t.split("\n")[:80]:
        l = re.sub(r"\s{2,}", " ", l).strip(" |=-—_*")
        n = nrm(l)
        if len(re.findall(r"[a-z]", n)) < 4 or _BOILER.search(n) or len(re.findall(r"[a-z]", n)) < 0.5 * len(n.replace(" ", "")) \
                or re.search(r"(?:[\s(][+\-]?\d[\d.,]*\s?%?\)?){3,}\s*$", l) or len(re.findall(r"\d[\d.,]*\s?(?:MF\b|%)", l)) >= 3 \
                or (not re.match(r"\W*(?:avis|communiqu)", n) and len(re.findall(r"[a-z]+", n)) >= 3
                    and sum(len(w) <= 2 for w in re.findall(r"[a-z]+", n)) > 0.6 * len(re.findall(r"[a-z]+", n))
                    and sum(len(w) >= 5 for w in re.findall(r"[a-z]+", n)) <= 1):  # (tableau chiffré, bruit de lecture)
            continue
        L.append(l)
    if not L:
        return None
    i = next((i for i, l in enumerate(L[:15]) if re.match(r"(avis|communiqu|note|decision|instruction|resultat|cotation hebdo)", nrm(l))), None)
    parts = L[i:i + 3] if i is not None else L[:2]
    return " — ".join(p[:90] for p in parts)


def _fallback_title(t):
    """Intitulé de secours d'un document dont le texte tient sur une seule ligne (en-tête de l'émetteur collé au corps) : nom de
    l'émetteur avant « Société anonyme… » et nature du document (convocation, projet de résolutions, résultats, communiqué, bilan),
    sinon la première phrase."""
    n = re.sub(r"\s+", " ", t[:1500]).strip()
    m = re.match(r"(.{4,90}?)\s+(?:soci[eé]t[eé] anonyme|s\.?a\.? avec|au capital|capital social|si[eè]ge social)", n, re.I)
    head = m.group(1).strip(" -—|") if m else ""
    kinds = (("convocation", "Convocation à l'assemblée générale"), ("projet de r[eé]solution", "Projet de résolutions"),
             (r"publication des r[eé]sultats|r[eé]sultats (?:annuels|trimestriels|semestriels|au \d)", "Résultats"),
             ("communiqu", "Communiqué"), (r"\bbilan\b", "États financiers"))
    kind = next((lab for rx, lab in kinds if re.search(rx, n[:1200], re.I)), None)
    if head:
        return head + (f" — {kind}" if kind else "")
    first = re.split(r"\s*[:.]\s", n, maxsplit=1)[0][:90].strip()
    return first if len(re.findall(r"[a-zA-Z]", first)) >= 8 else kind


FR_MOIS_LONG = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")


def _fr_long(iso):
    try:
        x = dt.date.fromisoformat(iso[:10])
        return f"{x.day}{'er' if x.day == 1 else ''} {FR_MOIS_LONG[x.month - 1]} {x.year}"
    except (TypeError, ValueError):
        return iso


def _boc_date(txt):
    """Date de la séance d'un bulletin (« mardi 8 mai 2012 », « Tuesday, May 8, 2012 »), ou None."""
    n = nrm(txt[:4000])
    m = re.search(r"(\d{1,2})(?:er)? (" + MOIS_RX + r") ((?:19|20)\d\d)", n)
    try:
        if m:
            return dt.date(int(m.group(3)), FR_MOIS[m.group(2)], int(m.group(1))).isoformat()
        m = re.search(r"(" + "|".join(BOC_EN_MOIS) + r") (\d{1,2}), ((?:19|20)\d\d)", n)
        if m:
            return dt.date(int(m.group(3)), BOC_EN_MOIS[m.group(1)], int(m.group(2))).isoformat()
    except (ValueError, KeyError):
        return None
    return None


def parse_boc_old(txt):
    """[(titre, montant, date de paiement, ordre de grandeur du cours ce jour-là)] lus sur les lignes des actions d'un bulletin de
    l'ancien site (le cours, sur la même base d'actions que le montant, permet de ramener le dividende sur la base actuelle)."""
    out = []
    for l in txt.split("\n"):
        m = re.match(r"\s*([A-Z]{3,5})\s{2,}\S", l)
        if not m or re.match(r"\s*[A-Z]{3,5}\.", l):
            continue  # (lignes des obligations « SGBC.O1 » : coupons)
        hits = list(BOC_DIV.finditer(nrm(l)))
        if not hits:
            continue
        h = hits[-1]
        mo = MOIS_ABR.get(h.group(3))
        if not mo:
            continue
        try:
            d = dt.date(2000 + int(h.group(4)), mo, int(h.group(2))).isoformat()
        except ValueError:
            continue
        # ordre de grandeur du cours : médiane des nombres entiers de la ligne (cours précédent, ouverture, clôture, plus haut,
        # plus bas, cours de référence…), hors dividende et date ; contrôle de vraisemblance du montant
        nl = nrm(l)
        rest = nl[:h.start()] + " " + nl[h.end():]
        nums = sorted(float(re.sub(r"[ ,]", "", x)) for x in re.findall(r"(?<![\d.,])(\d{1,3}(?:[ ,]\d{3})+|\d+)(?![\d.,%])", rest))
        nums = [x for x in nums if x >= 10]
        px_ = nums[len(nums) // 2] if len(nums) >= 3 else None
        a = _boc_old_amt(h.group(1), px_)
        if a and a > 0:
            out.append((m.group(1), a, d, px_))
    return out


# ---------------------------------------------------------------- revues trimestrielles de la BRVM (1999-2002)
# tableaux « Paiement de dividendes sur action — Exercice 1999 » (titre, symbole, dividende net, date de mise en paiement) et
# « DPA 1999 | date de paiement | cours | rendement » : premiers exercices de la BRVM, qu'aucun avis conservé ne couvre.
REV_DATE = re.compile(r"(\d{1,2})(?:er)?[ -]([a-z]{3,9})\.?[ -]((?:19|20)?\d\d)$")


def _rev_amt(c):
    c = c.strip()
    if re.fullmatch(r"\d{1,3}(?:[ ,]\d{3})+|\d+", c):
        return float(re.sub(r"[ ,]", "", c))
    if re.fullmatch(r"\d+,\d{1,2}", c):
        return float(c.replace(",", "."))
    return None


def parse_revue(txt, tick):
    """[(titre, exercice, montant net, date de paiement ou None)] des tableaux de dividendes d'une revue trimestrielle."""
    L = txt.split("\n")
    out, ex, on, n_on, dpa = [], None, False, 0, 0
    for l in L:
        nl = nrm(l)
        if re.search(r"paiement de dividendes? (?:sur|par) action", nl) and "...." not in nl and "…" not in l:
            on, n_on, ex = True, 0, None
        elif re.search(r"\bdpa\b", nl) and "...." not in nl:
            on, n_on, ex, dpa = True, 0, None, 4
        if not on:
            continue
        n_on += 1
        if n_on > 70 or re.search(r"nouvelle composition|repertoires|liste des (?:obligations|droits)|societes inscrites|criteres de selection", nl):
            on = False
            continue
        m = re.search(r"\bexercice\s+((?:19|20)\d\d)\b|\bex\s+((?:19|20)\d\d)\b", nl)
        if m:
            ex = int(m.group(1) or m.group(2))
        elif dpa:
            dpa -= 1
            m = re.fullmatch(r"\s*((?:19|20)\d\d)\s*", nl) or re.search(r"\s((?:19|20)\d\d)\s{3,}", " " + nl)
            if m and ex is None:
                ex = int(m.group(1))
        cells = re.split(r"\s{2,}", l.strip())
        si = next((i for i, c in enumerate(cells) if c.strip() in tick and i > 0), None)
        if si is None or ex is None:
            continue
        a = None
        for j in range(si + 1, len(cells)):
            a = _rev_amt(cells[j])
            if a is not None or re.fullmatch(r"nd|n\.d\.|\*|-", cells[j].strip().lower()):
                break
        if not a:
            continue  # (0, ND ou « * » : pas de dividende ou montant non communiqué)
        d = None
        for c in cells[j + 1:j + 2]:
            m = REV_DATE.search(nrm(c).strip())
            mo = m and (FR_MOIS.get(m.group(2)) or MOIS_ABR.get(m.group(2)))
            if m and mo:
                y = int(m.group(3)) if len(m.group(3)) == 4 else 2000 + int(m.group(3))
                try:
                    d = dt.date(y, mo, int(m.group(1))).isoformat()
                except ValueError:
                    d = None
        if d and not (ex < int(d[:4]) <= ex + 2):
            d = None  # (date incohérente avec l'exercice)
        out.append((cells[si].strip(), ex, a, d))
    return out


# noms des sociétés dans les avis et calendriers -> titre (motifs sur le nom normalisé, du plus précis au plus général)
ALIAS = [
    (r"\bboa\b.*(?:burkina|\bbf\b)|bank of africa.*(?:burkina|\bbf\b)", "BOABF"), (r"\bboa\b.*(?:benin|\bbn\b)|bank of africa.*(?:benin|\bbn\b)", "BOAB"),
    (r"\bboa\b.*(?:cote d.?ivoire|\bci\b)|bank of africa.*(?:cote|\bci\b)", "BOAC"), (r"\bboa\b.*(?:mali|\bml\b)|bank of africa.*(?:mali|\bml\b)", "BOAM"),
    (r"\bboa\b.*(?:niger|\bng\b)|bank of africa.*(?:niger|\bng\b)", "BOAN"), (r"\bboa\b.*(?:senegal|\bsn\b)|bank of africa.*(?:senegal|\bsn\b)", "BOAS"),
    (r"ecobank transnational|\beti\b|ecobank trans\b|ecobank (?:tg|togo|group)\b", "ETIT"), (r"ecobank", "ECOC"), (r"sonatel", "SNTS"), (r"onatel", "ONTBF"), (r"orange", "ORAC"),
    (r"coris", "CBIBF"), (r"palm ?ci|palmci|palm cote", "PALC"), (r"\bbici|bicici", "BICC"), (r"biic", "BICB"),
    (r"total(?:energies)?(?: marketing)? (?:senegal|sn)\b|total senegal", "TTLS"), (r"total", "TTLC"), (r"\bcie\b|compagnie ivoirienne d.electricite", "CIEC"),
    (r"solibra", "SLBC"), (r"societe ivoirienne de banque|\bsib\b", "SIBC"), (r"loterie nationale|\blnb\b", "LNBB"), (r"nsia", "NSBC"),
    (r"sogb", "SOGC"), (r"societe generale|\bsgb ?ci\b|\bsgbci\b", "SGBC"), (r"sicable", "CABC"), (r"bollore|africa global logistics|\bagl\b", "SDSC"),
    (r"servair", "ABJC"), (r"cfao", "CFAC"), (r"filtisac", "FTSC"), (r"nestle", "NTLC"), (r"oragroup", "ORGT"), (r"\bsaph\b", "SPHC"),
    (r"setao", "STAC"), (r"\bsitab\b", "STBC"), (r"\bsmb\b|societe multinationale de bitumes", "SMBC"), (r"sodeci|\bsode\b", "SDCC"),
    (r"sucrivoire", "SCRC"), (r"tractafric|\bprosuma\b", "PRSC"), (r"uniwax", "UNXC"), (r"vivo energy|shell", "SHEC"), (r"nei.?ceda", "NEIC"),
    (r"bernabe", "BNBC"), (r"unilever", "UNLC"), (r"sicor", "SICC"), (r"safca", "SAFC"), (r"air liquide|erium", "SIVC"), (r"crown siem|eviosys|sonoco|siem", "SEMC"),
    (r"bridge bank", "BBGC"), (r"movis", None), (r"trituraf", None),
]


def ticker_of(name):
    n = nrm(name or "")
    n = re.sub(r"[’'`]", "'", n)
    for rx, t in ALIAS:
        if re.search(rx, n):
            return t
    return None


def read_text(d, h):
    """Texte d'un document : couche texte, sinon lecture française par reconnaissance de caractères."""
    for suf in (".txt.gz", ".fra.gz", ".eng.gz"):
        p = os.path.join(d, "txt", h + suf)
        if os.path.exists(p):
            t = gzip.open(p, "rt", encoding="utf8").read()
            if len(re.sub(r"\s", "", t)) > 100:
                return t, suf != ".txt.gz"
    return "", False


def _pubdate(u, r=None):
    """Date de publication : celle de l'avis (« Fait à Abidjan, le … »), sinon celle du nom du fichier (AAAAMMJJ_…)."""
    if r and r.get("pub"):
        return r["pub"]
    m = re.search(r"/((?:19|20)\d\d)(\d\d)(\d\d)[_\-]", u or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def _days(a, b):
    try:
        return abs((dt.date.fromisoformat(a[:10]) - dt.date.fromisoformat(b[:10])).days)
    except (TypeError, ValueError):
        return 9999


def consolidate(cal_rows, avis, boc_old=None, revue=None):
    """Un versement par titre et date (détachement ou paiement à 5 jours près). Montant retenu : l'avis individuel le plus récent
    de la BRVM (un avis rectificatif remplace le précédent ; le calendrier n'est pas toujours mis à jour après un rectificatif),
    sinon la dernière version du calendrier de la BRVM, sinon l'avis du Dépositaire central. Montant brut seul : net déduit
    seulement avec le taux d'IRVM des personnes physiques écrit dans le document. Chaque source lue est gardée (« chk »)."""
    ev = []
    for r in cal_rows:
        net = None if r["gross"] or r["usd_cents"] else r["amt"]
        if r["gross"] and r.get("irvm") is not None:
            net = round(r["amt"] * (1 - r["irvm"] / 100), 4)
        ev.append({"t": r["t"], "det": r["det"], "pay": r["pay"], "net": net, "brut": r["amt"] if r["gross"] else None, "ex": r.get("ex"),
                   "irvm": r.get("irvm") if r["gross"] else None, "num": r["num"], "yr": r["yr"], "src": "calendrier", "u": r["u"], "d": r["cd"], "ann": r.get("pub"),
                   "rank": 1, **({"usd_c": r["amt"]} if r["usd_cents"] and not r["gross"] else {})})
    for r in avis:
        # (montant net publié en cents de dollar, sans contre-valeur FCFA : gardé tel quel, converti au cours du jour de l'avis par le terminal)
        nets = [p_ for p_ in r["parts"] if p_.get("net") or p_.get("usd_cents")]
        if not r.get("t") or not nets or not (r.get("det") or r.get("pay") or r.get("rec")):
            continue
        for p_ in nets:
            ev.append({"t": r["t"], "det": r.get("det"), "pay": r.get("pay") or r.get("rec"), "net": p_.get("net"), "brut": p_.get("brut"),
                       "irvm": p_.get("irvm"), "kind": p_["kind"], "ex": r.get("ex"), "num": r.get("num"), "yr": r.get("yr"),
                       "src": "avis BRVM" if r.get("org") != "DC/BR" else "avis DC/BR", "u": r["u"], "d": _pubdate(r["u"], r), "ann": _pubdate(r["u"], r),
                       "rank": 2 if r.get("org") != "DC/BR" else 0, "rect": bool(r.get("rect")), **({"usd_c": p_["usd_cents"]} if p_.get("usd_cents") else {})})
    # bulletins de l'ancien site : un versement par titre et date de paiement, le montant affiché le plus souvent (une ligne mal
    # imprimée un jour ne l'emporte pas) ; source la plus faible, retenue seulement sans avis ni calendrier pour ce versement
    for (t, d), x in (boc_old or {}).items():
        amts = x["a"]
        a, n = max(amts.items(), key=lambda kv: kv[1])
        if n >= 2 or len(amts) == 1:
            pxs = sorted(p_ for p_ in (x.get("px") or []) if p_[2] == a)
            ev.append({"t": t, "det": None, "pay": d, "net": a, "src": "bulletin", "u": x["u"], "d": d, "rank": -1, "ex": int(d[:4]) - 1, "nb": n,
                       **({"px": pxs[0][1], "px_d": pxs[0][0]} if pxs else {})})  # (premier bulletin après le paiement)
    # revues trimestrielles : le même tableau repris d'une revue à l'autre ; un montant daté est un versement (rang entre bulletin
    # et Dépositaire central) ; un montant sans date n'est gardé que si toutes les revues donnent le même et qu'aucun autre document
    # ne couvre cet exercice
    undated = []
    for (t, ex), vals in (revue or {}).items():
        dated = {(a, d) for a, d, _ in vals if d}
        for a, d in sorted(dated):
            u_ = next(x for a2, d2, x in vals if a2 == a and d2 == d)
            ev.append({"t": t, "det": None, "pay": d, "net": a, "src": "revue trimestrielle", "u": u_, "d": d, "rank": -0.5, "ex": ex})
        if not dated and len({a for a, _, _ in vals}) == 1:
            undated.append({"t": t, "ex": ex, "net": vals[0][0], "u": vals[0][2]})
    out = []
    for t in sorted({e["t"] for e in ev}):
        es = sorted([e for e in ev if e["t"] == t], key=lambda e: (e.get("det") or e.get("pay") or ""))
        groups = []
        for e in es:
            # (même versement : une date de détachement ou de paiement à 7 jours près d'une date de l'autre document)
            de_ = [v for v in (e.get("det"), e.get("pay")) if v]
            g = next((g for g in groups if any(_days(a_, b_) <= 7 for x in g for a_ in de_ for b_ in (x.get("det"), x.get("pay")) if b_)), None)
            (g.append(e) if g is not None else groups.append([e]))
        for g in groups:
            # avis rectificatif de la BRVM (le plus récent) ; sinon la publication la plus récente entre avis de la BRVM et calendrier
            # (un calendrier publié après l'avis reprend une rectification) ; sinon l'avis du Dépositaire central. Fraction et solde
            # payés le même jour : l'avis le plus récent décrit le versement de ce jour.
            gn = [e for e in g if e.get("net") is not None]
            if not gn:
                # montant publié seulement en cents de dollar (Ecobank Transnational) : le plus récent des documents de la BRVM ;
                # un montant en FCFA publié pour le même versement l'emporte toujours (branche ci-dessus)
                gu = [e for e in g if e.get("usd_c")]
                if gu:
                    bu = max(gu, key=lambda e: (e["rank"] >= 1, e.get("d") or "", e["rank"]))
                    out.append({"t": t, "ex": next((e["ex"] for e in sorted(gu, key=lambda e: -e["rank"]) if e.get("ex")), None), "net": None,
                                "usd_c": bu["usd_c"], "brut": None, "irvm": None,
                                "det": bu.get("det") or next((e["det"] for e in g if e.get("det")), None),
                                "pay": bu.get("pay") or next((e["pay"] for e in g if e.get("pay")), None),
                                "kind": bu.get("kind") or "annuel", "src": bu["src"], "u": bu["u"], "num": bu.get("num"), "yr": bu.get("yr"),
                                "pub": next((e["ann"] for e in sorted(gu, key=lambda e: e.get("ann") or "9") if e.get("ann") and e["rank"] >= 1), None) or bu.get("ann"),
                                "chk": [["usd_c", e["usd_c"], e.get("d") or ""] for e in gu if abs(e["usd_c"] - bu["usd_c"]) > 1e-9]})
                continue
            rect_ = [e for e in gn if e["rank"] == 2 and e.get("rect")]
            main_ = [e for e in gn if e["rank"] >= 1]
            dcbr_ = [e for e in gn if e["rank"] == 0]
            best = max(rect_ or main_ or dcbr_ or gn, key=lambda e: (e.get("d") or "", e["rank"]))
            ex_ = next((e["ex"] for e in sorted(g, key=lambda e: -e["rank"]) if e.get("ex")), None)
            if ex_ is None and best.get("yr") and (best.get("det") or best.get("pay")):
                ex_ = None  # (l'année de l'avis n'est pas l'exercice ; exercice laissé vide plutôt que deviné)
            # dividende ordinaire et dividende exceptionnel versés le même jour (un seul avis, deux montants) : deux versements
            sib = [e for e in gn if e is not best and e.get("u") and e["u"] == best.get("u") and e.get("kind") and e.get("kind") != best.get("kind")]
            for e in sib:
                out.append({"t": t, "ex": e.get("ex") or best.get("ex"), "net": e["net"], "brut": e.get("brut"), "irvm": e.get("irvm"),
                            "det": best.get("det"), "pay": best.get("pay"), "kind": e["kind"], "src": e["src"], "u": e["u"], "num": e.get("num"),
                            "yr": e.get("yr"), "pub": e.get("ann"), "chk": []})
            g = [e for e in g if not any(e is x for x in sib)]
            chk = sorted({(e["src"], e.get("net"), e.get("d") or "") for e in g}, key=lambda x: x[2])
            out.append({"t": t, "ex": ex_, "net": best["net"], "brut": best.get("brut"), "irvm": best.get("irvm"),
                        "det": best.get("det") or next((e["det"] for e in g if e.get("det")), None),
                        "pay": best.get("pay") or next((e["pay"] for e in g if e.get("pay")), None),
                        "kind": best.get("kind") or "annuel", "src": best["src"], "u": best["u"], "num": best.get("num"), "yr": best.get("yr"),
                        "pub": next((e["ann"] for e in sorted(g, key=lambda e: e.get("ann") or "9") if e.get("ann") and e["rank"] >= 1), None) or best.get("ann"), "chk": [list(c) for c in chk if c[1] is not None and abs(c[1] - best["net"]) > 1e-6],
                        # (cours lu dans un bulletin à côté du même montant : même base d'actions que le dividende publié)
                        **next(({"px": e["px"], "px_d": e["px_d"]} for e in [best] + g if e.get("px") and e.get("net") and abs(e["net"] / best["net"] - 1) < .005), {})})
    have = {(o["t"], o.get("ex")) for o in out}
    for x in undated:
        if (x["t"], x["ex"]) not in have:
            out.append({"t": x["t"], "ex": x["ex"], "net": x["net"], "brut": None, "irvm": None, "det": None, "pay": None, "kind": "annuel",
                        "src": "revue trimestrielle", "u": x["u"], "num": None, "yr": None, "pub": None, "chk": []})
    return out


def run(d):
    idx = json.load(open(os.path.join(d, "index.json"), encoding="utf8"))
    cal_rows, avis, n_boc = [], [], 0
    boc_old, revue = {}, {}
    tick = {t_ for _, t_ in ALIAS if t_}
    cat = []  # catalogue des documents lus (recherche MOTS CLES du terminal) : intitulé, nature, date, société, exercice
    # documents sans texte lisible : « à OCR » (numérisés, reconnaissance de caractères pas encore faite, relus par fetch_extra au
    # passage suivant ; leur couche texte partielle, s'il y en a une, est lue comme avant) et « lu » sans texte (ni couche texte ni
    # reconnaissance) : comptés et signalés, jamais ignorés en silence
    a_ocr, sans_txt = [], []
    for u, m in (idx.get("docs") or {}).items():
        if m.get("st") not in ("lu", "à OCR"):
            continue
        t, ocr = read_text(d, m["h"])
        if m.get("st") == "à OCR":
            a_ocr.append(u)
        if not t:
            if m.get("st") == "lu":
                sans_txt.append(u)
            continue
        c_ = {"u": u, **({"wb": m["wb"]} if m.get("wb") else {})}
        cat.append(c_)
        # (bulletin de la cote : titre en tête du document ; une décision ou un avis qui cite le bulletin plus loin n'en est pas un)
        if re.search(r"bulletin officiel de la cote", nrm(t[:1200])) and not re.search(r"\bdecision n", nrm(t[:800])):
            n_boc += 1
            bd_ = _boc_date(t)
            c_.update(k="boc", d=bd_, ti="Bulletin officiel de la cote" + (f" du {_fr_long(bd_)}" if bd_ else ""))
            for tk, a, dd, px_ in parse_boc_old(t):
                if tk in tick and dd <= "2013-12-31":  # (bulletins récents : lus par ailleurs, base des cours)
                    x = boc_old.setdefault((tk, dd), {"a": {}, "u": u, "px": []})
                    x["a"][a] = x["a"].get(a, 0) + 1
                    if px_ and bd_ and dd <= bd_ <= (dt.date.fromisoformat(dd) + dt.timedelta(days=120)).isoformat():
                        x["px"].append((bd_, px_, a))  # (cours du jour du bulletin, dans les quatre mois suivant le paiement)
            continue
        if re.search(r"revue trimestrielle", nrm(t[:1500])):
            mq = re.search(r"(\d)\s*(?:er|e|eme|ème)?\s+trimestre\s+((?:19|20)\d\d)", nrm(t[:3000]))
            q_, y_ = (int(mq.group(1)), int(mq.group(2))) if mq else (None, None)
            mf = re.search(r"(janv\w*|avril|juil\w*|oct\w*)[_\-]\w+?[_\-]((?:19|20)\d\d)", nrm(urllib.parse.unquote(u.rsplit("/", 1)[-1])).replace(" ", "_"))
            if not mq and mf:  # (« revue_trim_avril_juin_2000.pdf » : 2e trimestre 2000)
                q_, y_ = {"j": 1, "a": 2, "o": 4}.get(mf.group(1)[0], 3) if not mf.group(1).startswith("juil") else 3, int(mf.group(2))
            c_.update(k="rev", y=y_,  # (période couverte ; la date de parution n'est pas connue)
                      ti="Revue trimestrielle de la BRVM" + (f" — {q_}{'er' if q_ == 1 else 'e'} trimestre {y_}" if q_ else ""))
            for tk, ex_, a, dd in parse_revue(t, tick):
                revue.setdefault((tk, ex_), []).append((a, dd, u))
            continue
        if re.search(r"calendrier de paiement des dividendes", nrm(t[:3000])):
            rows, irvm = parse_calendar(t)
            cd = _pubdate(u) or ""
            mx = re.search(r"exercice[\s_\-]*((?:19|20)\d\d)", nrm(u.rsplit("/", 1)[-1]) + " " + nrm(t[:1500]))
            ex_cal = int(mx.group(1)) if mx else None  # (« calendrier de paiement des dividendes de l'exercice 2017 »)
            c_.update(k="div", d=cd or None, y=ex_cal, ti="BRVM : calendrier de paiement des dividendes" + (f" — exercice {ex_cal}" if ex_cal else ""))
            for r in rows:
                tk = ticker_of(r["name"])
                if tk:
                    cal_rows.append({**r, "t": tk, "u": u, "cd": cd, "irvm": irvm,
                                     "ex": ex_cal if ex_cal and r.get("pay") and int(r["pay"][:4]) - 2 <= ex_cal < int(r["pay"][:4]) else None})
            continue
        for r in parse_avis(t):
            fn_ = nrm(u.rsplit("/", 1)[-1])
            if re.search(r"dc.?br|dcbr", fn_) or re.search(r"depositaire central", nrm(t[:600])):
                r["org"] = "DC/BR"
            if re.search(r"rectif|modifi|annule", fn_):
                r["rect"] = True
            tk = r.get("sym") if r.get("sym") and any(t_ == r["sym"] for _, t_ in ALIAS) else None
            tk = tk or ticker_of(r.get("soc") or "") or ticker_of(m.get("soc") or "") or ticker_of(u.rsplit("/", 1)[-1].replace("_", " "))
            avis.append({**r, "t": tk, "u": u, "ocr": ocr})
            # (un bulletin de la cote, un manuel, un règlement ou une instruction cite des paiements de dividendes sans être un avis :
            # son intitulé est tiré plus loin de la liste, du nom du fichier ou de l'en-tête du document)
            # (avis de paiement seulement : numéro d'avis, formule de la BRVM ou du Dépositaire central, ou mise en paiement annoncée en
            # tête ; une convocation d'assemblée, des états financiers ou une décision qui citent un dividende gardent leur propre intitulé)
            is_avis_ = bool(r.get("num")) or bool(re.search(r"porte a la connaissance|paiement (?:de|du|des) dividende|mise en paiement|mettra en paiement",
                                                             nrm(t[:1500])))
            if "k" not in c_ and tk and not is_avis_:
                c_.setdefault("t", tk)  # (société reconnue : gardée pour la recherche, l'intitulé vient du document)
            if "k" not in c_ and not NOT_AVIS.search(fn_) and is_avis_:
                org_ = "DC/BR" if r.get("org") == "DC/BR" else "BRVM"
                num_ = f" n° {r['num']}" + (f"-{r['yr']}" if r.get("yr") else "") if r.get("num") else ""
                soc_ = (r.get("soc") or m.get("soc") or "").strip().upper()
                if re.match(r"(LUNDI|MARDI|MERCREDI|JEUDI|VENDREDI|SAMEDI|DIMANCHE)\b|\d", soc_):
                    soc_ = ""  # (date lue à la place de la société)
                ex_ok = str(r.get("ex") or "").isdigit() and 1995 <= int(r["ex"]) <= dt.date.today().year  # (« exercice 1975 » : lecture fautive)
                c_.update(k="div", t=tk, y=int(r["ex"]) if ex_ok else None, d=_pubdate(u, r),
                          f="D" if org_ == "DC/BR" else "", ti=f"Avis{num_} {org_} : {'report du ' if re.search(r'report', nrm(u.rsplit('/', 1)[-1])) else ''}paiement de dividendes{' (rectificatif)' if r.get('rect') else ''}"
                                                              + (f" — {soc_}" if soc_ else "") + (f" — exercice {r['ex']}" if ex_ok else ""))
    for c_ in cat:
        if not c_.get("d"):  # (ancien site : « …/avis/2002/juillet/… » : premier jour du mois)
            mp = re.search(r"/((?:19|20)\d\d)/(" + MOIS_RX + r")/", nrm(urllib.parse.unquote(c_["u"], encoding="latin-1")))
            if mp:
                c_["d"] = f"{mp.group(1)}-{FR_MOIS[mp.group(2)]:02d}-01"
    for c_ in cat:  # (autres documents : intitulé tiré de la liste de brvm.org, du nom du fichier ou de l'en-tête du document)
        if "k" not in c_:
            m = idx["docs"][c_["u"]]
            fn_ = urllib.parse.unquote(c_["u"].rsplit("/", 1)[-1], encoding="latin-1")
            ti_ = m.get("ti")
            if not ti_ and not re.search(r"linkclick|fileticket", fn_, re.I):
                ti_ = re.sub(r"\s+", " ", re.sub(r"\.pdf$|[_]+", " ", fn_, flags=re.I)).strip()
            t, _ = read_text(d, m["h"])
            ti_ = ti_ or _head_title(t or "") or _fallback_title(t or "")
            if not ti_:
                continue
            c_.update(k="avis", ti=ti_[:160], d=c_.get("d") or _pubdate(c_["u"]) or (fr_date(nrm((t or "")[:2500])) if t else None))
    for c_ in cat:  # (date lue dans le texte d'une archive : gardée seulement si elle précède de moins de 3 ans la capture de l'archive)
        if c_.get("d") and c_.get("wb") and not (str(int(c_["wb"][:4]) - 3) <= c_["d"][:4] and c_["d"].replace("-", "") <= c_["wb"][:8]):
            c_["d"] = None
    cat = [c_ for c_ in cat if c_.get("ti")]
    json.dump({"v": 1, "docs": [{k: v for k, v in c_.items() if v not in (None, "")} for c_ in cat]},
              open(os.path.join(d, "catalog.json"), "w", encoding="utf8"), ensure_ascii=False, separators=(",", ":"))
    rows = consolidate(cal_rows, avis, boc_old, revue)
    # (avis de paiement de dividendes parmi les documents sans texte : nom du fichier ; liste gardée pour le contrôle du matin)
    div_sans = sorted(u for u in a_ocr + sans_txt if re.search(r"divid", urllib.parse.unquote(u.rsplit("/", 1)[-1]).lower()))
    json.dump({"v": 2, "ts": int(dt.datetime.now().timestamp()), "rows": rows,
               "n": {"calendriers": len({r["u"] for r in cal_rows}), "lignes_calendrier": len(cal_rows), "avis": len(avis), "bulletins": n_boc, "versements_bulletins": len(boc_old), "revues": len(revue),
                     "a_ocr": len(a_ocr), "lus_sans_texte": len(sans_txt), "avis_dividende_sans_texte": len(div_sans)},
               "sans_texte": div_sans[:300]},
              open(os.path.join(d, "dividendes.json"), "w", encoding="utf8"), ensure_ascii=False, separators=(",", ":"))
    print(f"[dividendes] {len(rows)} versements ({len(cal_rows)} lignes de calendrier, {len(avis)} avis, {n_boc} bulletins anciens, {len(boc_old)} versements lus dans les bulletins)")
    if a_ocr or sans_txt:
        print(f"[dividendes] documents sans texte : {len(a_ocr)} à relire par reconnaissance de caractères, {len(sans_txt)} lus sans texte"
              f" (dont {len(div_sans)} avis de dividende)")
    if div_sans:  # (un avis de dividende illisible peut annoncer un report ou un rectificatif : signalé tant qu'il n'est pas lu)
        print(f"::warning::Dividendes : {len(div_sans)} avis de dividende sans texte (à relire par reconnaissance de caractères) : "
              f"leurs montants et dates ne sont pas encore pris en compte ({', '.join(u.rsplit('/', 1)[-1][:50] for u in div_sans[:3])}…)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    run(ap.parse_args().dir)


# ---------------------------------------------------------------- bulletins officiels de la cote (2013 → aujourd'hui)
def boc_events(boc_dir, factors=None):
    """Dividendes payés lus dans les bulletins quotidiens : {titre: [{"pay", "vals": [{"v", "first", "last", "n", "adj", "pub"}]}]}.
    Chaque valeur affichée l'est sur la base des actions du jour où elle paraît (les bulletins ramènent un dividende passé sur le
    nombre d'actions issu d'un fractionnement ou d'actions gratuites) : « adj » = valeur ÷ facteur cumulé de ce jour (base
    actuelle), « pub » = valeur ramenée sur la base du jour du paiement (montant publié). Valeurs vues moins de 3 jours alors que
    d'autres le sont longtemps : défauts de lecture, écartées. Plusieurs valeurs de même base : la plus durable est la correction."""
    import glob
    ip = os.path.join(boc_dir, "_index.json")
    cols = json.load(open(ip, encoding="utf8"))["cols"]
    ci, cd = cols.index("div"), cols.index("div_d")
    obs = {}
    for f in sorted(glob.glob(os.path.join(boc_dir, "[12][0-9][0-9][0-9].json"))):
        for day, rows in sorted(json.load(open(f, encoding="utf8")).items()):
            for sym, r in rows.items():
                if r[ci] and r[cd]:
                    o = obs.setdefault(sym, {}).setdefault(r[cd], {})
                    x = o.setdefault(r[ci], [day, day, 0])
                    x[1], x[2] = day, x[2] + 1
    out = {}
    for sym, by in obs.items():
        fs = (factors or {}).get(sym)
        evs = []
        for pay, vals in sorted(by.items()):
            tot = sum(v[2] for v in vals.values())
            vs = []
            for a, (f0, f1, n) in sorted(vals.items(), key=lambda kv: kv[1][0]):
                if n < 3 and tot >= 6:
                    continue
                fx = factor_at(fs, int(f0)) if fs else None
                fp = factor_at(fs, int(pay.replace("-", ""))) if fs else None
                vs.append({"v": a, "first": f0, "last": f1, "n": n, "adj": round(a / fx, 4) if fx else None,
                           "pub": round(a * fp / fx, 4) if fx and fp else None})
            if vs:
                evs.append({"pay": pay, "vals": vs})
        out[sym] = evs
    return out


def price_factors(boc_dir, series_dir):
    """Facteur cumulé des opérations sur le capital (fractionnements, actions gratuites) à chaque date : cours publié dans le
    bulletin ÷ cours ajusté de la série (base des actions actuelles). {titre: [(jour, facteur)]} (jours où les deux existent)."""
    import glob
    cols = json.load(open(os.path.join(boc_dir, "_index.json"), encoding="utf8"))["cols"]
    ic = cols.index("c")
    raw = {}
    for f in sorted(glob.glob(os.path.join(boc_dir, "[12][0-9][0-9][0-9].json"))):
        for day, rows in json.load(open(f, encoding="utf8")).items():
            for sym, r in rows.items():
                if r[ic]:
                    raw.setdefault(sym, {})[int(day)] = r[ic]
    out = {}
    for sym, rr in raw.items():
        p = os.path.join(series_dir, sym + ".json")
        if not os.path.exists(p):
            continue
        s = json.load(open(p, encoding="utf8"))
        adj = dict(zip(s["d"], s["c"]))
        out[sym] = sorted((d, rr[d] / adj[d]) for d in rr if adj.get(d))
    return out


def factor_at(fs, day):
    """Facteur cumulé au jour donné : celui du jour même s'il est connu, sinon la médiane des 5 séances suivantes (une valeur
    affichée à partir d'un jour l'est sur la base de ce jour), sinon des 5 précédentes ; None hors de la période couverte
    par les bulletins (plus d'un an d'écart)."""
    import bisect
    if not fs:
        return None
    ds = [d for d, _ in fs]
    i = bisect.bisect_left(ds, day)
    if i < len(ds) and ds[i] == day:
        return fs[i][1]
    win = [f for d, f in fs[i:i + 5] if d - day < 10000] or [f for d, f in fs[max(0, i - 5):i] if day - d < 10000]
    if not win:
        return None
    win.sort()
    return win[len(win) // 2]


def boc_paid(ev, fs):
    """Montant publié d'un paiement lu dans les bulletins (base des actions du jour du paiement) et montant ramené sur la base
    actuelle. Règle : la première valeur durable (vue au moins 3 jours) affichée avant toute opération sur le capital postérieure
    au paiement est le montant publié ; sinon la valeur durable la plus ancienne, ramenée à la base du paiement par le rapport des
    facteurs. Renvoie {"pub", "adj", "f_pay", "ok"} ; ok = False si les valeurs successives ne se recoupent pas."""
    pay = int(ev["pay"].replace("-", ""))
    f_pay = factor_at(fs, pay) if fs else None
    vals = [v for v in ev["vals"] if v["n"] >= 3] or ev["vals"]
    nxt = None  # première opération sur le capital après le paiement (changement du facteur de plus de 5 %)
    if fs and f_pay:
        for d, f in fs:
            if d > pay and abs(f / f_pay - 1) > .05:
                nxt = d
                break
    pre = [v for v in vals if nxt is None or int(v["first"]) < nxt - 3]
    if pre:
        pub = pre[0]["v"]
        if len(pre) > 1 and pre[0]["n"] < 20 and max(pre, key=lambda v: v["n"])["n"] > 100 and abs(max(pre, key=lambda v: v["n"])["v"] / pub - 1) > .005:
            pub = max(pre, key=lambda v: v["n"])["v"]  # (valeur corrigée par la BRVM quelques jours après : la plus durable)
    else:
        v0 = vals[0]
        fx = factor_at(fs, int(v0["first"])) if fs else None
        pub = round(v0["v"] * f_pay / fx, 4) if f_pay and fx else None
    adj = round(pub / f_pay, 4) if pub and f_pay else None
    # recoupement : chaque valeur durable affichée ensuite vaut le montant ramené sur la base de son jour (à 1 % près ou à
    # l'unité arrondie), ou bien le cumul de l'exercice (acompte et solde) ; sinon le paiement est signalé
    ok = True
    if adj and fs:
        for v in vals:
            fx = factor_at(fs, int(v["first"]) + 3)
            if fx and not (abs(v["v"] - adj * fx) <= max(1.0, adj * fx * .01) or v["v"] > adj * fx * 1.05):
                ok = False
    return {"pub": pub, "adj": adj, "f_pay": f_pay, "ok": ok}
