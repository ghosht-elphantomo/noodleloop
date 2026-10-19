"""Index de la recherche MOTS CLES : tous les documents de la BRVM connus du terminal, un par adresse.

Sources (les plus riches d'abord pour les métadonnées) : publications des sociétés cotées (liste de la base des cours, avec
exercice et catégorie), pages « rapports des sociétés cotées » de brvm.org, documents lus pour les états financiers et pour les
dividendes (avis BRVM et DC/BR, calendriers, anciens bulletins et revues de l'ancien site), avis de brvm.org, notations,
bulletins officiels de la cote quotidiens. Documents hébergés par la BRVM seulement (brvm.org, bfin.brvm.org, archives de
l'ancien site brvm.org).

Une ligne : [nature, titre (symbole), exercice, date AAAAMMJJ, intitulé, adresse abrégée, marques]
  nature : ef états financiers, ra rapport d'activité, rann rapport annuel, cac rapport des commissaires aux comptes,
           res résultats, com communiqué, ag assemblée générale, not notation, div dividende, obl obligation,
           ost opération sur titres, dir dirigeants, boc bulletin officiel de la cote, rev revue trimestrielle,
           opcvm OPCVM, seance compte rendu de séance, regl réglementation, avis autre avis
  marques : D Dépositaire central / Banque de règlement, R rectificatif, S semestriel, T trimestriel, C consolidé, A ancien site
  adresse : « B:… » = https://www.brvm.org/sites/default/files/… ; « F:… » = https://bfin.brvm.org/boc/BOC_JOUR/… ;
            « W<horodatage>:… » = archive web.archive.org de l'ancien site.
"""
import datetime as dt
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from dividendes import ticker_of
except Exception:  # noqa: BLE001
    def ticker_of(_):
        return None

B_ = "https://www.brvm.org/sites/default/files/"
F_ = "https://bfin.brvm.org/boc/BOC_JOUR/"

CAT = {"financial_statements": "ef", "activity_report": "ra", "annual_report": "rann", "company_report": "rann", "auditor_report": "cac",
       "financial_results": "res", "communique": "com", "ag_announcement": "ag", "ag_meeting": "ag", "resolution_project": "ag",
       "rating": "not", "dividend_announcement": "div", "dividend_payment": "div", "dividend_ex_date": "div", "dividend_amount_change": "div",
       "management_change": "dir", "stock_split": "ost", "bonus_issue": "ost", "rights_issue": "ost", "rights_delisting": "ost",
       "capital_operation_notice": "ost", "capital_reduction": "ost", "first_listing": "ost", "first_listing_result": "ost",
       "shares_admitted": "ost", "symbol_change": "ost", "trading_suspension": "ost", "trading_resumed": "ost",
       "theoretical_value_notice": "ost", "transaction_cancelled": "avis", "market_closed": "avis", "market_calendar": "avis",
       "index_composition": "avis", "index_change": "avis", "company_notice": "com"}


def nrm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().replace("’", "'")


def kind_of(ti, u, k0=None):
    """Nature d'un document d'après sa catégorie connue, sinon son intitulé et le nom de son fichier."""
    n = nrm(ti) + " " + nrm(urllib.parse.unquote(u.rsplit("/", 1)[-1], encoding="latin-1"))
    tn = nrm(ti)
    # (emprunt obligataire : « TPCI 5,45 % 2026-2031 », « (EOS.O30) », sukuk… quelle que soit la catégorie de la liste)
    if re.search(r"\d+(?:,\d+)? ?% ?(?:19|20)\d\d ?- ?(?:19|20)\d\d|\.o\d+\b|emprunt obligataire|obligataire|sukuk|diaspora bonds", n):
        return "obl"
    # intitulé qui annonce les états financiers avant toute attestation ou tout rapport sur eux : « états financiers », quelle
    # que soit la catégorie de la liste (« SONATEL SN : Etats financiers et attestation des Commissaires Aux Comptes – Exercice 2025 »)
    m_ef = re.search(r"\betats? financiers?|financial statements|\bcomptes (?:annuels|consolides|sociaux|semestriels)", tn)
    m_cac = re.search(r"attestation|commissaires? aux comptes|\bcac\b|rapport (?:general|special) des", tn)
    if re.match(r"(?:[^:]{0,70}:\s*)?(?:attestation|rapports? (?:des|du) (?:cac|commissaires?))", tn) and k0 in (None, "ef", "rann", "ra", "com", "avis", "cac"):
        return "cac"  # (« Attestation des CAC SITAB - 1er semestre 2017 », « Rapport des CAC sur les états financiers »)
    if m_ef and not (m_cac and m_cac.start() < m_ef.start()) and k0 in (None, "cac", "res", "rann", "com", "avis", "ra", "ef"):
        return "ef"
    if m_ef and m_cac and m_cac.start() < m_ef.start() and k0 in (None, "ef", "com", "avis"):
        return "cac"  # (« Attestation de sincérité sur les états financiers »)
    if k0 == "ag" and not re.search(r"assembl|convoc|resolution|vote|pouvoir|meeting|\bag[oem]\b|prorogation d.ag|reunion", tn):
        k0 = None  # (« Obtention d'un prêt de Deutsche Bank AG » : pas une assemblée)
    if k0 == "rann" and re.search(r"financial results?|resultats? financ", tn) and not re.search(r"rapport annuel|annual report", tn):
        return "res"
    if k0 == "rann" and re.search(r"trimestr|semestr|rapport d.activite|rapport de gestion.{0,20}(?:mars|juin|septembre)|activi?ty report|quarter|quater|half|semester", nrm(ti)) and not re.search(r"rapport annuel|examen limite|commissaire|attestation|\bcac\b", nrm(ti)):
        return "ra"  # (ancien site : « Rapport semestriel » rangé avec les rapports annuels)
    if k0 and k0 not in ("avis", "com"):
        return k0
    rules = (("boc", r"bulletin officiel de la cote|\bboc_\d"), ("rev", r"revue trimestrielle"),
             ("div", r"dividende|calendrier de paiement"),
             ("obl", r"obligat|emprunt|sukuk|interets|remboursement (?:partiel|total|anticipe)|amortissement|coupon|titres? de creance"),
             ("ef", r"etats? financiers?|bilan|comptes (?:annuels|consolides|sociaux|semestriels)"),
             ("ra", r"rapport d.activite|rapport (?:semestriel|trimestriel)|activi?ty report"), ("cac", r"commissaires? aux comptes"), ("rann", r"rapport annuel|rapport de gestion"),
             ("res", r"resultats?\b"), ("not", r"notation"), ("ag", r"assemblee|convocation|resolution"),
             ("ost", r"fractionnement|augmentation de capital|attribution gratuite|introduction en bourse|radiation|suspension|"
                     r"reprise de cotation|valeur theorique|offre publique|droits? (?:de souscription|d.attribution)"),
             ("opcvm", r"valeur liquidative|\bfcp\b|opcvm|\bsicav\b"), ("seance", r"seance de cotation|a cloture sa seance"),
             ("regl", r"\binstruction\b|\bdecision n|\breglement\b|\bcirculaire\b"), ("dir", r"nomination|directeur general|dirigeant"))
    for k, rx in rules:
        if re.search(rx, n):
            return k
    return k0 or ("com" if "communiqu" in n else "avis")


def flags_of(ti, u, k):
    n = nrm(ti) + " " + nrm(urllib.parse.unquote(u, encoding="latin-1"))
    f = ""
    if re.search(r"dc ?/ ?br|dcbr|depositaire central", n):
        f += "D"
    if re.search(r"rectif|annule et remplace", n):
        f += "R"
    if re.search(r"semestr|1er semestre|s1\b|\bau 30 juin|30/06/(?:19|20)\d\d|rapport de gestion.{0,20}juin|\bhalf\b|half.year|\bsemester", n):
        f += "S"
    if re.search(r"trimestr|\b[1-4](?:er|e|eme)? trimestre|\bt[1-4]\b|[1-4]t20|\bau 30 septembre|\bau 31 mars|30/09/(?:19|20)\d\d|31/03/(?:19|20)\d\d|rapport de gestion.{0,20}(?:mars|septembre)|\bquar?ter\b|first quarter|\bq[1-4]\b", n) and k != "rev":
        f += "T"
    if re.search(r"consolid", n):
        f += "C"
    return f


def year_of(ti, u):
    n = nrm(ti) + " " + nrm(urllib.parse.unquote(u.rsplit("/", 1)[-1], encoding="latin-1"))
    m = (re.search(r"\b(?:exercice|exo|ex|annee|fy)[\s_\-:]*((?:19|20)\d\d)(?!\d)", n) or re.search(r"(?:semestre|trimestre)[\s_\-]*((?:19|20)\d\d)(?!\d)", n)
         or re.search(r"(?:etats? financiers?|resultats?|rapport annuel|rapport d.activites?|comptes)[^0-9]{0,25}((?:19|20)\d\d)(?!\d)", n))
    return int(m.group(1)) if m else 0


def date_of(*vals):
    for v in vals:
        if not v:
            continue
        s = re.sub(r"\D", "", str(v))[:8]
        if len(s) == 8 and "19900101" <= s <= "20991231":
            return int(s)
    return 0


def url_date(u):
    m = re.search(r"/((?:19|20)\d{6})[_\-]", u or "")
    return m.group(1) if m else None


def canon(u):
    """Adresse ramenée à une forme unique (http/https, port 80, paramètre de téléchargement forcé)."""
    u = (u or "").strip()
    u = re.sub(r"^http://", "https://", u)
    u = u.replace("www.brvm.org:80/", "www.brvm.org/").replace("brvm.org:80/", "brvm.org/")
    u = re.sub(r"[&?]forcedownload=true", "", u, flags=re.I)
    return u


def dkey(cu):
    """clé de doublon : un ancien lien de téléchargement (LinkClick) désigne le même fichier quels que soient l'onglet, le module, la
    langue ou l'encodage du paramètre fileticket"""
    m = re.search(r"LinkClick\.aspx\?(?:.*&)?fileticket=([^&]+)", cu, re.I)
    if m:
        return "linkclick:" + urllib.parse.unquote(m.group(1))
    return cu


def short(u, wb=None):
    if wb:
        return f"W{wb}:" + u
    if u.startswith(B_):
        return "B:" + u[len(B_):]
    if u.startswith(F_):
        return "F:" + u[len(F_):]
    return u


def official(u):
    h = re.sub(r"^https?://([^/]+)/.*", r"\1", u or "").lower()
    return h.endswith("brvm.org")


ACC = {"etats": "états", "assemblee": "assemblée", "generale": "générale", "activites": "activités", "activite": "activité",
       "societes": "sociétés", "cotees": "cotées", "resultats": "résultats", "approuves": "approuvés", "certifies": "certifiés",
       "theorique": "théorique", "a la": "à la", "mise a": "mise à", "brvmdg": "BRVM/DG", "brvm": "BRVM", "dactivites": "d’activités",
       "dactivite": "d’activité", "troisieme": "troisième", "deuxieme": "deuxième", "3eme": "3ème", "2eme": "2ème", "dactions": "d’actions",
       "opcvm": "OPCVM", "ra": "Rapport annuel", "rs": "Rapport semestriel", "efa": "États financiers approuvés",
       "efp": "États financiers provisoires", "efc": "États financiers consolidés", "ef": "États financiers", "cm": "Communiqué"}


def file_title(fn, t, co, name_rx=None):
    """Intitulé refait à partir du nom du fichier (quand la liste de la Bourse rattache le fichier à un autre document)."""
    s = re.sub(r"\.pdf$", "", fn, flags=re.I)
    s = re.sub(r"^\d{6,8}[_-]*", "", s)
    s = re.sub(r"_+\d$", "", s).replace("_-_", " - ").replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip(" -")
    if name_rx:  # (nom de la société retiré du texte : il est mis en tête)
        seg = [x for x in s.split(" - ") if not re.search(name_rx, x, flags=re.I)] or [s]
        s = " - ".join(seg)
        s = re.sub(r"\b(?:" + name_rx + r")(?:\s+\w+)?(?:\s+(?:ci|sn|bf|bn|ml|ne|ng|tg))?\b", "", s, flags=re.I)
        s = re.sub(r"(?:\s+(?:de|du|des|la|le|les|d))+\s*$", "", s.strip(" -"), flags=re.I)
    s = re.sub(r"\bndeg ?(\d)", r"n° \1", s, flags=re.I)
    s = re.sub(r"\b(" + "|".join(sorted(map(re.escape, ACC), key=len, reverse=True)) + r")\b", lambda m: ACC[m.group(1).lower()], s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" -")
    s = s[:1].upper() + s[1:]
    if t:
        names = sorted((n for n in co.get(t, ()) if n and n == n.upper() and len(n) >= 3), key=len)
        if names:
            return f"{names[0]} : {s}"
    return s


def fix_by_file(rows, co, log=print):
    """Le nom du fichier fait foi : un fichier d'une autre société cotée que celle de la liste (« SUCRIVOIRE : États financiers 2024 »
    pointant vers un erratum de SOLIBRA), ou d'un autre type de document (« comptes 2016 » pointant vers un avis sur le flottant),
    est rattaché à la bonne société avec un intitulé refait à partir du fichier ; « Exercice 1998 » sur un fichier « exercice_2001 »
    prend l'année du fichier. Ainsi chaque ligne de la recherche ouvre le document qu'elle annonce."""
    try:
        from comptes import other_company, NAME_TOKENS
    except Exception:  # noqa: BLE001
        other_company, NAME_TOKENS = None, {}
    n = 0
    for r in rows:
        if not (isinstance(r[5], str) and r[5].startswith("B:")):
            continue
        fn = r[5][2:].rsplit("/", 1)[-1]
        nf = nrm(fn).replace("_", " ").replace("-", " ")
        oc = other_company(r[1], fn) if (other_company and r[1]) else None
        oc = oc if oc and oc != "?" else None
        kind_rx = r"valeurs? liquidatives?|flottant des societes"
        wrong_kind = re.search(kind_rx, nf) and not re.search(kind_rx, nrm(r[4]))
        if oc or wrong_kind:
            r[1] = oc or ""
            r[4] = file_title(fn, r[1], co, NAME_TOKENS.get(r[1]))[:180]
            r[0] = kind_of(r[4], B_ + r[5][2:])
            r[2] = year_of(r[4], B_ + r[5][2:])
            n += 1
            continue
        m_f, m_t = re.search(r"exercice ((?:19|20)\d\d)\b", nf), re.search(r"\b[Ee]xercice ((?:19|20)\d\d)\b", r[4])
        if m_f and m_t and r[0] in ("ef", "rann", "cac") and m_f.group(1) != m_t.group(1):
            r[4] = r[4][:m_t.start(1)] + m_f.group(1) + r[4][m_t.end(1):]
            r[2] = int(m_f.group(1))
            n += 1
    log(f"recherche MOTS CLES : {n} intitulés corrigés d'après le nom du fichier")
    return n


def jload(p, default=None):
    try:
        return json.load(open(p, encoding="utf8"))
    except Exception:  # noqa: BLE001
        return default


def build(out, brvm_src, search_src=None, boc_dir=None, log=print, comptes=None):
    t0 = time.time()
    R = {}  # adresse canonique -> ligne

    def add(u, ti, t=None, y=0, d=0, k0=None, wb=None, f0=""):
        if not u or not ti:
            return
        u0 = u
        cu = canon(u)
        if not (official(cu) or wb):
            return
        if not d:
            d = date_of(url_date(cu))  # (date de mise en ligne inscrite dans le nom du fichier : « AAAAMMJJ_-_… »)
        ti = re.sub(r"^[:;\-–— ]+", "", re.sub(r"\s+", " ", str(ti)).strip())[:180]  # (« : Pouvoir - Assemblée… » : nom de la société absent de la liste)
        k = kind_of(ti, cu, k0)
        f = "".join(sorted(set(flags_of(ti, cu, k) + (f0 or "") + ("A" if wb or "LinkClick" in cu or "/fr/marche/" in cu else ""))))
        y = int(y or 0) or year_of(ti, cu)
        r = R.get(dkey(cu))
        if r is None:
            R[dkey(cu)] = [k, t or "", y, d or 0, ti, short(cu if not wb else u0.replace(":80/", "/"), wb), f]
            return
        # (même document vu par plusieurs sources : chaque champ manquant est complété, l'intitulé le plus parlant gardé)
        if not r[1] and t:
            r[1] = t
        if not r[2] and y:
            r[2] = y
        if not r[3] and d:
            r[3] = d
        if r[0] in ("avis", "com") and k not in ("avis", "com"):
            r[0] = k
        if len(ti) > len(r[4]) and not re.search(r"linkclick|fileticket", ti, re.I):
            r[4] = ti
        r[6] = "".join(sorted(set(r[6] + f)))

    # 1. publications des sociétés cotées (catégorie, exercice, date)
    ev = (jload(os.path.join(brvm_src, "events.json"), {}) or {}).get("events") or []
    for e in ev:
        # (date de publication seulement quand elle est lue : nom du fichier, liste officielle, texte ou signature du document)
        d_ = date_of(e.get("published_at")) if e.get("date_source") not in (None, "unknown") else 0
        add(e.get("document_url"), e.get("title"), e.get("ticker"), e.get("fiscal_year"), d_, CAT.get(e.get("category")))
        for doc in e.get("documents") or []:
            add(doc.get("url"), (e.get("title") or "") + (f" ({doc.get('kind')})" if doc.get("kind") else ""), e.get("ticker"), e.get("fiscal_year"),
                d_, CAT.get(e.get("category")))
    # 2. documents lus pour les états financiers et pages « rapports » de brvm.org
    if search_src:
        ci = (jload(os.path.join(search_src, "comptes_index.json"), {}) or {}).get("docs") or {}
        for u, m in ci.items():  # (date seulement si le nom du fichier la porte : sinon c'est le jour où la liste a été relevée)
            add(u, m.get("ti"), m.get("t"), m.get("fy"), date_of(url_date(u)), CAT.get(m.get("cat")), m.get("wb"))
        br = (jload(os.path.join(search_src, "brvm_rapports.json"), {}) or {}).get("docs") or {}
        for u, m in br.items():
            add(u, m.get("ti"), m.get("t"), 0, date_of(url_date(u)))
        # 3. documents lus pour les dividendes (avis BRVM et DC/BR, calendriers, anciens bulletins, revues, ancien site)
        dc = (jload(os.path.join(search_src, "div_catalog.json"), {}) or {}).get("docs") or []
        for x in dc:
            add(x.get("u"), x.get("ti"), x.get("t"), x.get("y"), date_of(x.get("d")), x.get("k") if x.get("k") != "avis" else None, x.get("wb"), x.get("f", ""))
    # 4. pages du terminal : rapports suivis, avis de brvm.org, notations
    rp = jload(os.path.join(out, "reports.json"), {}) or {}
    iss = rp.get("issuers") or {}
    for sl, L in (rp.get("docs") or {}).items():
        for x in L or []:
            add(x.get("u"), x.get("ti"), (iss.get(sl) or {}).get("t"), 0, date_of(x.get("d")))
    AVK = {"comm": "com", "resol": "ag", "ag": "ag", "dirig": "dir", "capital": "ost", "frac": "ost", "notation": "not", "div": "div"}
    for u, x in ((jload(os.path.join(out, "avis_brvm.json"), {}) or {}).get("items") or {}).items():
        add(u, x.get("ti") or x.get("c"), x.get("t") if isinstance(x.get("t"), str) else (ticker_of(x.get("soc") or "") if x.get("soc") else None),
            0, date_of(x.get("d")), AVK.get(x.get("k")))
    for x in (jload(os.path.join(out, "ratings.json"), {}) or {}).get("rows") or []:
        add(x.get("u"), x.get("ti"), x.get("t"), 0, date_of(x.get("d")), "not")
    # 5. bulletins officiels de la cote, un par séance (adresse de bfin.brvm.org)
    bi = jload(os.path.join(boc_dir, "_index.json"), {}) if boc_dir else {}
    for k in (bi or {}).get("done") or []:
        try:
            x = dt.date(int(k[:4]), int(k[4:6]), int(k[6:8]))
        except ValueError:
            continue
        mois = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")
        jours = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
        add(F_ + f"BOC_{k}.pdf", f"Bulletin officiel de la cote du {jours[x.weekday()]} {x.day}{'er' if x.day == 1 else ''} {mois[x.month - 1]} {x.year}",
            None, 0, int(k), "boc")
    # sociétés : noms officiels, noms courants, anciens noms, noms des émetteurs dans les publications (reconnaissance dans la requête)
    co = {}
    acts = (jload(os.path.join(brvm_src, "actions.json"), {}) or {}).get("actions") or []
    for a in acts:
        t = a.get("ticker")
        for n in (a.get("nom"), a.get("nom_officiel")):
            if n:
                co.setdefault(t, set()).add(n)
    def alias(t, n):  # (nom d'émetteur gardé seulement s'il ne désigne pas une autre société : listes parfois mal rattachées ;
        # « Avis », « BRVM » relevés à la place d'un nom : écartés)
        if n and re.fullmatch(r"\W*(?:avis|brvm|communiques?|bulletin|rapport|societe|note|information|annonce|document)\W*", nrm(n)):
            return
        if t and n and ticker_of(n) in (None, t):
            co.setdefault(t, set()).add(n)
    for e in ev:
        alias(e.get("ticker"), e.get("issuer"))
        alias(e.get("ticker"), e.get("company"))
    for sl, x in iss.items():
        alias(x.get("t"), x.get("n"))
        alias(x.get("t"), sl.replace("-", " "))
    # exercice lu dans les comptes annuels par la lecture des états financiers (identités comptables vérifiées) : il prime sur
    # l'intitulé (« Exercice 2013 » des anciennes listes = année de publication : comptes 2012)
    cp = (jload(comptes, {}) or {}).get("docs") or {} if comptes else {}
    sure = set()
    for u, m in cp.items():
        r = R.get(dkey(canon(u)))
        if not (r and m.get("st") == "ok" and m.get("per") == "annuel" and isinstance(m.get("fy"), int) and 1990 <= m["fy"] <= dt.date.today().year):
            continue
        # (l'exercice lu ne l'emporte sur l'intitulé que si celui-ci est muet, ou s'il porte l'année de publication : « Exercice 2013 »
        # publié en février 2013 = comptes 2012 ; un intitulé cohérent avec sa date est gardé, la lecture d'un scan peut se tromper
        # d'année : « Exercice 2004 » de Sonatel lu 2003)
        fy, dy_ = m["fy"], r[3] // 10000
        if not r[2] or fy == r[2] or (dy_ and r[2] == dy_ and fy == dy_ - 1):
            r[2] = fy
            sure.add(id(r))
    this_y = dt.date.today().year
    n_fix = 0
    for r in R.values():
        if r[2] and not 1990 <= r[2] <= this_y + 1:
            r[2] = 0
        if r[0] in ("not", "obl") and r[2] and not re.search(r"exercice", nrm(r[4])):
            r[2] = 0  # (notation, emprunt : « 2020-2025 » est une durée, pas un exercice)
        dy = r[3] // 10000
        if not (r[2] and r[3]) or r[2] < dy:
            continue
        annual = r[0] in ("ef", "rann", "res", "cac") and not re.search(r"[ST]", r[6])
        if annual and id(r) in sure:
            r[3], n_fix = 0, n_fix + 1  # (comptes de l'exercice N datés de l'année N : la date du nom du fichier est fausse)
        elif annual and r[3] % 10000 <= 930:
            r[2], n_fix = 0, n_fix + 1  # (comptes annuels publiés avant la fin de l'exercice annoncé : exercice incertain)
        elif r[2] > dy and r[0] in ("ra", "ef", "rann", "res", "cac"):
            r[3], n_fix = 0, n_fix + 1  # (rapport d'une période postérieure à sa date : date incertaine)
    for r in R.values():  # (« dividende de l’exercice — » : exercice absent de la liste, connu par un autre document)
        r[4] = re.sub(r" de l’exercice — ", f" de l’exercice {r[2]} " if r[2] else " ", r[4])
    rows = sorted(R.values(), key=lambda r: (-r[3], r[4]))
    fix_by_file(rows, co, log)
    # société manquante : reconnue dans l'intitulé (noms des sociétés)
    for r in rows:  # société rattachée par la liste démentie par le nom écrit dans l'intitulé (« … ONATEL-SA » rattaché à Sonatel)
        if r[1]:
            t2 = ticker_of(r[4])
            if t2 and t2 != r[1] and t2 not in ("TTLC", "ORAC", "CIEC") and not re.search(r"\b" + re.escape(r[1].lower()) + r"\b", nrm(r[4])):
                r[1] = t2
    for r in rows:  # (seulement sur l'émetteur écrit en tête de l'intitulé : « UNIWAX CI : … », « … — BOA BENIN — … »)
        if not r[1] and r[0] not in ("boc", "rev", "seance", "regl", "opcvm", "obl"):
            m = re.match(r"([^:—]{3,60}?)\s*[:—]", r[4])
            if m and not re.match(r"\s*(?:avis|communiqu|bulletin|brvm\b|instruction|decision|note)", nrm(m.group(1))):
                r[1] = ticker_of(m.group(1)) or ""
    # document sans société dont l'intitulé porte le nom complet d'une seule société cotée (« … — Bank Of Africa NIGER — Admission
    # des actions nouvelles ») : rattaché à elle (nom d'une seule société, le plus long trouvé ; « NSIA HOLDING » ne désigne pas NSIA Banque)
    SW = {"de", "du", "des", "la", "le", "les", "l", "d", "et", "of", "the", "sa", "s", "a", "en"}
    toks = lambda x: [w for w in re.sub(r"[^a-z0-9]+", " ", nrm(x)).split() if w not in SW]
    phr = {}
    for t, L in co.items():
        for n_ in L:
            tk = tuple(toks(n_))
            if len(tk) >= 2 or (len(tk) == 1 and len(tk[0]) >= 5 and tk[0] not in ("banque", "societe", "groupe", "africa", "bank")):
                phr.setdefault(tk, set()).add(t)
    phr = {k: v for k, v in phr.items() if len(v) == 1}
    # (nom d'un seul mot, « SICOR » : seulement s'il désigne surtout cette société dans les intitulés rattachés ; « total » non)
    tokrows = {}
    for r in rows:
        if r[1]:
            for w in set(toks(r[4])):
                tokrows.setdefault(w, []).append(r[1])
    for k in [k for k in phr if len(k) == 1]:
        t_, L_ = next(iter(phr[k])), tokrows.get(k[0], [])
        if L_ and sum(1 for x in L_ if x == t_) < .8 * len(L_):
            del phr[k]
    n_att = 0
    for r in rows:
        if r[1] or r[0] in ("boc", "rev", "seance", "regl", "opcvm"):
            continue
        tt = toks(r[4])
        best, who = 0, set()
        for k, v in phr.items():
            if len(k) < best:
                continue
            if any(tt[i:i + len(k)] == list(k) for i in range(len(tt) - len(k) + 1)):
                if len(k) > best:
                    best, who = len(k), set(v)
                else:
                    who |= v
        if len(who) == 1:
            r[1] = who.pop()
            n_att += 1
    # même document déposé deux fois (même intitulé, même date, même société) : une seule ligne
    seen_, seen_f, rows2 = set(), {}, []
    for r in sorted(rows, key=lambda r: (bool(re.search(r"_\d\.pdf$", r[5])), "A" in r[6])):
        tk_ = re.sub(r"[^a-z0-9]+", " ", nrm(r[4])).strip()
        key_ = (r[0], r[1], r[3], tk_)
        # même fichier déposé une seconde fois avec un suffixe « _0 », « _1 »… (même adresse une fois le suffixe retiré, même intitulé,
        # même date ou date inconnue pour l'un des deux)
        key2_ = (r[0], r[1], tk_, re.sub(r"_\d(?=\.pdf$)", "", r[5].lower())) if r[5].lower().endswith(".pdf") else None
        ds_ = seen_f.get(key2_) if key2_ else None
        if (key_ in seen_ and r[3]) or (ds_ is not None and (not r[3] or 0 in ds_ or r[3] in ds_)):
            continue
        seen_.add(key_)
        if key2_:
            seen_f.setdefault(key2_, set()).add(r[3])
        rows2.append(r)
    n_dup = len(rows) - len(rows2)
    rows = sorted(rows2, key=lambda r: (-r[3], r[4]))
    res = {"v": 1, "ts": int(time.time()), "n": len(rows), "co": {t: sorted(n for n in v if n) for t, v in co.items() if t},
           "r": rows}
    json.dump(res, open(os.path.join(out, "search.json"), "w", encoding="utf8"), ensure_ascii=False, separators=(",", ":"))
    log(f"recherche MOTS CLES : {len(rows)} documents indexés, {len(sure)} exercices lus dans les comptes, {n_fix} dates ou exercices incohérents écartés, {n_att} documents rattachés par le nom de la société, {n_dup} doublons retirés ({time.time() - t0:.1f} s)")
    return res


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--brvm-src", required=True)
    ap.add_argument("--search-src", default=None)
    ap.add_argument("--boc", default=None)
    ap.add_argument("--comptes", default=None)
    a = ap.parse_args()
    build(a.out, a.brvm_src, a.search_src, a.boc, comptes=a.comptes)
