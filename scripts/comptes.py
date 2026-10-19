#!/usr/bin/env python3
"""Lecture des états financiers publiés par les sociétés cotées à la BRVM (texte du PDF ou reconnaissance de caractères).

Plan comptable SYSCOHADA (ancien et révisé), plan comptable bancaire de l'UMOA, normes IFRS.
Chaque poste est reconnu par son libellé normalisé (et par sa référence SYSCOHADA quand elle est imprimée) ; chaque montant est
rattaché à son exercice par la colonne sous l'en-tête des années, ou par la structure du tableau (brut / amortissements / net,
colonne de variation). Les montants sont ramenés en millions de FCFA.
Un exercice n'est retenu que si les identités comptables du document se vérifient (total actif = total passif, résultat du
compte de résultat = résultat du bilan, soldes intermédiaires) : rien n'est deviné ni estimé. Bibliothèque standard uniquement.

Utilisation en ligne de commande : comptes.py --dir DOSSIER  (index.json + txt/ produits par fetch_extra.py --only comptes)
-> DOSSIER/comptes.json
"""
import gzip
import json
import os
import math
import re
import sys
import unicodedata

READER_V = 2

# ---------------------------------------------------------------- postes
# clé : (états où le poste peut figurer, motif sur le libellé normalisé : minuscules, sans accents, sans référence ni formule)
S_ACT, S_PAS, S_CR, S_FLX = "actif", "passif", "cr", "flux"
ITEMS = [
    # ---- bilan actif (SYSCOHADA)
    ("charges_immobilisees", (S_ACT,), r"^charges immobilisees$"),
    ("immo_incorp", (S_ACT,), r"^immobilisations incorporelles(?: nettes)?$"),
    ("immo_corp", (S_ACT,), r"^immobilisations corporelles(?: nettes)?$"),
    ("immo_fin", (S_ACT,), r"^immobilisations financieres(?: nettes)?$"),
    ("actif_immobilise", (S_ACT,), r"^(?:total )?actif immobilise(?: net)?$|^total (?:de l.)?actif immobilise(?: net)?$|^total immobilisations(?: nettes)?$"),
    ("actif_circulant_hao", (S_ACT,), r"^actif circulant h\.?a\.?o\.?$"),
    ("stocks", (S_ACT,), r"^stocks?(?: et en.?cours| de marchandises)?$"),
    ("creances", (S_ACT,), r"^creances et emplois assimiles$|^creances$"),
    ("clients", (S_ACT,), r"^clients(?: et comptes rattaches)?$"),
    ("actif_circulant", (S_ACT,), r"^(?:total )?actif circulant$"),
    ("tresorerie_actif", (S_ACT,), r"^(?:total )?tresorerie ?- ?actif$|^(?:total )?tresorerie actif$|^disponibilites$"),
    ("total_actif", (S_ACT, None), r"^total ?(?:general ?)?(?:de ?l.? ?)?actif$|^total general actif$|^total bilan actif$|^total (?:des )?actifs$|^total assets$|^actif total$"),
    # ---- bilan passif (SYSCOHADA)
    ("capital", (S_PAS,), r"^capital(?: social| souscrit(?: appele)?)?$"),
    ("primes_reserves", (S_PAS,), r"^primes (?:et|&) reserves$"),
    ("primes_capital", (S_PAS,), r"^primes liees au capital social$|^primes d.apport,? d.emission,? de fusion$|^primes d.emission(?: et de fusion)?$"),
    ("ecart_reevaluation", (S_PAS,), r"^ecarts? de reevaluation$"),
    ("reserves_indisponibles", (S_PAS,), r"^reserves indisponibles$"),
    ("reserves_libres", (S_PAS,), r"^reserves libres$"),
    ("autres_cp", (S_PAS,), r"^autres capitaux propres(?: et assimiles)?$"),
    ("subventions", (S_PAS,), r"^subventions d.investissement$"),
    ("provisions_reglementees", (S_PAS,), r"^provisions reglementees(?: et fonds assimiles)?$"),
    ("ecart_conversion_passif", (S_PAS,), r"^ecarts? de conversion ?-? ?passif$"),
    ("autres_passifs_circulants", (S_PAS,), r"^autres passifs? circulants?$"),
    ("reserves", (S_PAS,), r"^reserves$"),
    ("report_nouveau", (S_PAS,), r"^report a nouveau"),
    ("resultat_bilan", (S_PAS, S_ACT, None), r"^resultat de l.exercice au bilan$"),  # (sous-libellé « (bénéfice + ou perte -) » seul sur sa ligne)
    ("capitaux_propres", (S_PAS,), r"^(?:total )?capitaux propres(?: et ressources assimilees| et assimiles)?(?: et)?$|^total des capitaux propres$|^total equity$"),
    ("cp_groupe", (S_PAS,), r"^(?:total )?capitaux propres(?:[ ,-]+part (?:du )?groupe| attribuables aux (?:actionnaires|proprietaires) de la (?:societe|maison)? ?mere| attribuables aux (?:actionnaires|proprietaires) de la societe)$"),
    ("interets_minoritaires", (S_PAS,), r"^(?:capitaux propres attribuables aux |total )?(?:participations|interets) ne donnant pas le controle$|^interets minoritaires$"),
    ("dettes_financieres", (S_PAS,), r"^(?:total )?dettes financieres(?: et ressources assimilees)?(?: et)?$|^total dettes et res\. assimilees$"),
    ("ressources_stables", (S_PAS,), r"^(?:total )?ressources stables$"),
    ("passif_circulant", (S_PAS,), r"^(?:total )?passif circulant$"),
    ("fournisseurs", (S_PAS,), r"^(?:dettes )?fournisseurs(?: d.exploitation| et comptes rattaches)?$"),
    ("dettes_circulantes_hao", (S_PAS,), r"^dettes circulantes h\.?a\.?o\.?$"),
    ("clients_avances", (S_PAS,), r"^clients,? avances recues$"),
    ("dettes_fiscales_sociales", (S_PAS,), r"^dettes fiscales(?: et sociales)?$"),
    ("dettes_sociales", (S_PAS,), r"^dettes sociales$"),
    ("autres_dettes", (S_PAS,), r"^autres dettes$"),
    ("provisions_risques_ct", (S_PAS,), r"^(?:provisions pour )?risques (?:provisionnes|a court terme)$"),
    ("tresorerie_passif", (S_PAS,), r"^(?:total )?tresorerie ?- ?passif$|^(?:total )?tresorerie passif$"),
    ("total_passif", (S_PAS, None), r"^total ?(?:general ?)?(?:du ?)?passif$|^total general passif$|^total bilan passif$|^total (?:des |du )?(?:capitaux propres et (?:des )?passifs?|passifs? et (?:des )?capitaux propres)$|^total liabilities and (?:shareholders. )?equity$|^passif total$|^total capitaux propres et passifs$"),
    ("actif_non_courant", (S_ACT,), r"^total (?:de l.|des )?actifs? non courants?$"),
    ("actif_courant", (S_ACT,), r"^total (?:de l.|des )?actifs? courants?$"),
    ("passif_non_courant", (S_PAS,), r"^total (?:du |des )?passifs? non courants?$"),
    ("passif_courant", (S_PAS,), r"^total (?:du |des )?passifs? courants?$"),
    # ---- compte de résultat (SYSCOHADA)
    ("ventes_marchandises", (S_CR,), r"^ventes? de marchandises$"),
    ("marge_commerciale", (S_CR,), r"^marge (?:commerciale|brute sur marchandises)$"),
    ("ventes_produits", (S_CR,), r"^ventes? de produits fabriques$"),
    ("travaux_services", (S_CR,), r"^travaux,? services (?:vendus|rendus)$"),
    ("produits_accessoires", (S_CR,), r"^produits accessoires$"),
    ("chiffre_affaires", (S_CR, None), r"^(?:total )?chiffre d.affaires(?: hors taxes| net| ht| consolide)?$|^revenue$|^revenus$|^produits des activites ordinaires$"),
    ("valeur_ajoutee", (S_CR,), r"^valeur ajoutee$"),
    ("charges_personnel", (S_CR,), r"^charges (?:de|du) personnel$|^frais de personnel$"),
    ("ebe", (S_CR, S_FLX), r"^excedent brut d.exploitation(?: \(?e\.?b\.?e\.?\)?)?$|^ebe$|^ebitda$"),
    ("dotations", (S_CR,), r"^dotations? aux amortissements(?:,? (?:et|aux) (?:aux )?provisions)?(?: et depreciations)?$"),
    ("resultat_exploitation", (S_CR,), r"^resultat d.exploitation$|^resultat operationnel$"),
    ("revenus_financiers", (S_CR,), r"^revenus financiers(?: et assimiles)?$|^produits financiers$"),
    ("frais_financiers", (S_CR,), r"^frais financiers(?: et charges assimilees)?$|^charges financieres$"),
    ("resultat_financier", (S_CR,), r"^resultat financier$"),
    ("rao", (S_CR,), r"^resultat des activites ordinaires$|^resultat activites ordinaires$"),
    ("rhao", (S_CR,), r"^resultat hors activites? ordinaires?$|^resultat h\.? ?a\.? ?o\.?$"),
    ("participation", (S_CR,), r"^participation des travailleurs$"),
    ("impots_resultat", (S_CR,), r"^impots? [sd]ur (?:le |les )?(?:resultats?|benefices?|societes)$|^impot sur le resultat$|^charges? d.impots?(?: sur le resultat)?$|^impots? exigibles? et differes?$"),
    ("perte_nette", (S_CR,), r"^perte(?: nette)?(?: de l.exercice)?$"),
    ("quote_part_mee", (S_CR,), r"^quote.?part (?:dans |du |des )?(?:le |les )?resultats? (?:net )?(?:des |dans les )?(?:societes|entreprises|entites|participations)(?: mises en(?: equivalence)?| associees| en equivalence)?$"),
    ("resultat_avant_impot", (S_CR,), r"^resultat avant impots?(?: sur le resultat| et participation)?$|^resultat (?:net )?avant impots?$"),
    # « Résultat net » : compte de résultat ou bilan selon l'état où il figure
    ("resultat_net", (S_CR, S_PAS, None), r"^(?:resultat net(?: de l.exercice| l.exercice| de la periode| consolide| comptable| de l.ensemble consolide| total)?|resultat de l.exercice|benefice(?: net)?(?: de l.exercice)?|benefice ou perte|resultat net \(?benefice.*|resultat (?:net )?de l.exercice ?:(?: ?perte entre \( ?\))?|profit for the (?:year|period))$"),
    ("resultat_net_pg", (S_CR,), r"^resultat net[ ,-]+part (?:du )?groupe$|^resultat net attribuable aux (?:actionnaires|proprietaires) de la (?:societe|maison)? ?mere$|^resultat net attribuable aux (?:actionnaires|proprietaires) de la societe$"),
    # ---- flux de trésorerie (TFT révisé) / TAFIRE
    ("cafg", (S_FLX, None), r"^capacite d.autofinancement globale(?: \(?cafg\)?)?$|^cafg$|^capacite d.autofinancement$"),
    ("flux_operationnels", (S_FLX,), r"^flux de tresorerie (?:nets? )?(?:provenant|provenants|issus?|generes?) (?:des|de l.|par les) ?activites? (?:operationnelles|d.exploitation)$"),
    ("capex_incorp", (S_FLX,), r"^(?:decaissements? lies? aux )?acquisitions? d.immobilisations incorporelles$"),
    ("capex_corp", (S_FLX,), r"^(?:decaissements? lies? aux )?acquisitions? d.immobilisations corporelles$"),
    ("flux_investissement", (S_FLX,), r"^flux de tresorerie (?:nets? )?(?:provenant|provenants|issus?|generes?|lies?) (?:des|de l.|aux) ?(?:activites?|operations) d.investissements?$"),
    ("dividendes_verses", (S_FLX,), r"^dividendes verses$|^distribution de dividendes$"),
    ("flux_financement", (S_FLX,), r"^flux de tresorerie (?:nets? )?(?:provenant|provenants|issus?|generes?|lies?) (?:des|de l.|aux) ?(?:activites?|operations) de financement$"),
    ("variation_tresorerie", (S_FLX,), r"^variation de (?:la )?tresorerie(?: nette)?(?: de la periode)?$"),
    ("tresorerie_fin", (S_FLX,), r"^tresorerie nette (?:au 31 decembre|a la cloture|de cloture|fin de periode|en fin de periode|a la fin de l.exercice)$"),
    # ---- banques (plan comptable bancaire UMOA, ancien et révisé)
    ("b_caisse", (S_ACT,), r"^caisse(?:,? banque centrale(?:,? ccp)?)?$"),
    ("b_creances_interbancaires", (S_ACT,), r"^creances interbancaires(?: et assimilees)?$"),
    ("b_creances_clientele", (S_ACT,), r"^creances sur la clientele$"),
    ("b_effets_publics", (S_ACT,), r"^effets publics et valeurs assimilees$"),
    ("b_titres_placement", (S_ACT,), r"^titres de placement$|^obligations et autres titres a revenu fixe$"),
    ("b_dettes_interbancaires", (S_PAS,), r"^dettes interbancaires(?: et assimilees)?$"),
    ("b_dettes_clientele", (S_PAS,), r"^dettes a l.egard de la clientele$"),
    ("b_capital", (S_PAS,), r"^capital (?:ou dotation|appele)$|^capital souscrit$"),
    ("b_resultat_bilan", (S_PAS,), r"^resultat de l.exercice ?\(\+ ?/ ?-\)$"),
    ("b_interets_produits", (S_CR,), r"^interets et produits assimilee?s$"),
    ("b_interets_charges", (S_CR,), r"^interets et charges assimilees$"),
    ("b_commissions_produits", (S_CR,), r"^commissions \(?produits\)?$"),
    ("b_commissions_charges", (S_CR,), r"^commissions \(?charges\)?$"),
    ("b_pnb", (S_CR, None), r"^produit net bancaire$|^net banking income$"),
    ("b_charges_generales", (S_CR,), r"^charges generales d.exploitation$|^frais generaux d.exploitation$|^frais generaux$"),
    ("b_rbe", (S_CR,), r"^resultat brut d.exploitation$"),
    ("b_cout_risque", (S_CR,), r"^cout du risque$"),
]
ITEM_RX = [(k, secs, re.compile(p)) for k, secs, p in ITEMS]
SECS = {k: tuple(x for x in secs if x) for k, secs, _ in ITEMS}
ITEM_KEYS = [k for k, _, _ in ITEMS] + [k for k in ("resultat_bilan",) if k not in {k_ for k_, _, _ in ITEMS}]

# références SYSCOHADA (ancien et révisé) dont le sens ne change pas d'un plan à l'autre
REF_CODES = {"AZ": "actif_immobilise", "BK": "actif_circulant", "BT": "tresorerie_actif", "BZ": "total_actif", "CA": "capital",
             "CP": "capitaux_propres", "DP": "passif_circulant", "DH": "dettes_circulantes_hao", "DI": "clients_avances", "DJ": "fournisseurs",
             "DK": "dettes_fiscales_sociales", "DL": "dettes_sociales", "DM": "autres_dettes", "DN": "provisions_risques_ct",
             "DT": "tresorerie_passif", "DZ": "total_passif", "XA": "marge_commerciale", "XC": "valeur_ajoutee", "XD": "ebe",
             "XE": "resultat_exploitation", "XF": "resultat_financier", "XG": "rao", "XH": "rhao", "XI": "resultat_net"}
# références dont le sens diffère entre l'ancien plan (DF = total des dettes financières, DG = total des ressources stables,
# CI = résultat de l'exercice au bilan) et le plan révisé (DD, DF, CJ) : le libellé tranche, sinon le plan reconnu
REF_CODES_AMBIG = {"DD": ("dettes_financieres", None), "DF": ("ressources_stables", "dettes_financieres"), "DG": (None, "ressources_stables"),
                   "CI": (None, "resultat_bilan"), "CJ": ("resultat_bilan", None)}
# plan révisé (2018 et après) seulement
REF_CODES_REV = {"XB": "chiffre_affaires", "CJ": "resultat_bilan", "RK": "charges_personnel", "RS": "impots_resultat", "RQ": "participation",
                 "TA": "ventes_marchandises", "TB": "ventes_produits", "TC": "travaux_services", "TD": "produits_accessoires",
                 "FA": "cafg", "ZB": "flux_operationnels", "ZC": "flux_investissement", "ZF": "flux_financement", "ZG": "variation_tresorerie",
                 "ZH": "tresorerie_fin", "FF": "capex_incorp", "FG": "capex_corp"}
CODE_SEC = {"A": S_ACT, "B": S_ACT, "C": S_PAS, "D": S_PAS, "T": S_CR, "R": S_CR, "X": S_CR, "F": S_FLX, "Z": S_FLX}

NUM = re.compile(r"\(?[-−–‐‑]?\s?\d{1,3}(?:(?:[    ]|,|\.)\d{3})+(?:,\d{1,3})?\)?(?!\d)|\d{1,2}\.\d{1,2}(?![\d.,])|\(?[-−–‐‑]?\d+(?:,\d{1,3})?\)?")
MOIS = {"janvier": 1, "janv": 1, "jan": 1, "fevrier": 2, "fevr": 2, "fev": 2, "mars": 3, "avril": 4, "avr": 4, "mai": 5, "juin": 6,
        "juillet": 7, "juil": 7, "aout": 8, "septembre": 9, "sept": 9, "sep": 9, "octobre": 10, "oct": 10, "novembre": 11, "nov": 11,
        "decembre": 12, "dec": 12}
# en-têtes de colonnes : 2018, « 31-déc-09 », « 31/12/2010 », « déc-10 », « Exercice N-1 »
HDR_RX = re.compile(r"(?<![\d,.])(?:(?:31|30)[-/. ]?(?:12|06|dec\w*|juin)[-/. ]?)?((?:19[89]\d|20[0-3]\d)|(?<=[-/. ])\d\d)(?![\d,.%])")
SPACE = "   "


def nrm(x):
    x = re.sub(r"[’‘`´ʼ]", "'", x)
    x = re.sub(r"[–—‐‑−]", "-", x)  # tirets typographiques (« N–1 »)
    return unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower()


_COMMA_K = [False]  # document où la virgule sépare les milliers (« 435,697 » = 435 697)
_TOLERANT = [False]  # lecture tolérante des libellés (reconnaissance de caractères) : essayée en second par read_doc
_COMMA_FORCE = [False]  # lecture « virgule des milliers » forcée (seconde lecture d'un document ambigu, voir read_doc)
_NOTE_DOT = [False]  # document à virgule décimale : « 5.3 » est un renvoi de note, pas un montant


def num_val(tok):
    """« 1 400 501 950 », « 1,962,261 », « (26 985) », « -2,579,063 », « 420,3 » -> nombre (None si ce n'est pas un montant)."""
    t = tok.strip()
    neg = t.startswith("(") and t.endswith(")") or t.lstrip("(").startswith(("-", "−", "–", "‐", "‑"))
    t = t.strip("()").lstrip("-−–‐‑").strip()
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", t) and (_COMMA_K[0] or not re.fullmatch(r"\d{1,3},\d{3}", t)):  # virgules = milliers (1,962,261)
        t = t.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", t):  # points = milliers
        t = t.replace(".", "")
    else:
        t = re.sub(r"[ " + SPACE + "]", "", t).replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def unit_of(txt):
    """Unité annoncée des montants : 1 (FCFA), 1e3 (milliers), 1e6 (millions) ; None si rien d'explicite."""
    t = nrm(txt[:40000])
    m = re.search(r"(?:en|donnees en|montants? en|chiffres en|\()\s*(milliards?|millions?|milliers|mxof|kxof|mfcfa|kfcfa|millier|mf|kf|m fcfa|k fcfa|mds?)\b[^\n]{0,25}"
                  r"(?:fcfa|f\.? ?cfa|francs?(?: cfa)?|xof|de francs|de f)", t)
    if m:
        w = m.group(1)
        return 1e9 if w.startswith("milliard") or w.startswith("md") else 1e6 if w.startswith("million") or w in ("mxof", "mfcfa", "mf", "m fcfa") else 1e3
    m = re.search(r"(?:\ben|\(|\{)\s*(k|m) ?(?:fcfa|xof|f\.? ?cfa)\b", t)  # « (chiffres en KFCFA) », « en MFCFA »
    if m:
        return 1e3 if m.group(1) == "k" else 1e6
    if re.search(r"\(?en (?:millions|milliers)\)?", t):
        return 1e6 if re.search(r"\(?en millions\)?", t) else 1e3
    if re.search(r"en (?:francs? cfa|fcfa|f\.? ?cfa|xof)\b|montants? en f\.? ?cfa", t):
        return 1.0
    return None


def capital_stated(txt):
    """Capital social annoncé dans l'en-tête (« au capital de 24 500 000 000 FCFA »), en FCFA."""
    t = nrm(txt[:12000])
    m = re.search(r"capital(?: social)? de\s*(?:f\.?\s?cfa\s*)?([\d][\d ., " + SPACE + r"]{4,}\d)\s*(?:f\.?\s?cfa|francs|fcfa|xof)?", t)
    if not m:
        return None
    v = num_val(re.sub(r"[., " + SPACE + "]", " ", m.group(1)).strip())
    return v if v and v > 1e6 else None


def fiscal_year(txt, hint=None):
    """Exercice du document : date de clôture écrite, sinon la plus récente des années d'en-tête des tableaux (N / N-1),
    sinon « exercice AAAA », sinon l'exercice annoncé par le titre (souvent l'année de publication, d'où la prudence)."""
    t = nrm(txt[:15000])
    rxs = (r"(?:au|clos le|arrete au|exercice clos le|cloture au|clos au)\s+31[ -/.]+(?:decembre|12)[ -/.]+(20\d\d|19\d\d)",
           r"exercice\s+(20\d\d)", r"(?:bilan|comptes? de resultats?|etats financiers)[^\n]{0,40}?\b(20\d\d)\b")
    import datetime
    y_max = datetime.date.today().year + 1
    # (année de clôture impossible — dans le futur, ou à plus de trois ans de l'exercice annoncé : chiffre mal lu, « 2076 » pour 2016)
    ys = [int(y) for y in re.findall(rxs[0], t) if int(y) <= y_max and not (hint and abs(int(y) - hint) > 3)]
    if ys:
        return hint if hint and hint in ys else max(set(ys), key=ys.count)
    hy = {}  # en-têtes de colonnes « N | N-1 » (deux années qui se suivent sur la même ligne) : vote pour N
    for ln in txt.splitlines()[:600]:
        ys_ = sorted({y for _, _, y in _hdr(ln) if isinstance(y, int) and 1995 <= y <= 2040})
        if len(ys_) >= 2 and ys_[-1] - 1 in ys_:
            hy[ys_[-1]] = hy.get(ys_[-1], 0) + 1
    if hy:
        y_h = max(hy, key=lambda y: (hy[y], y))
        if hy[y_h] >= 2 and (not hint or abs(y_h - hint) <= 1):
            return y_h
    for rx in rxs[1:]:
        ys = [int(y) for y in re.findall(rx, t)]
        if ys:
            return hint if hint and hint in ys else max(set(ys), key=ys.count)
    return hint


UNIT_LINE = re.compile(r"(?:\(|\ben\b|(?<![a-z])[a-z]en(?=\s+milli)|montants?|donnees|chiffres|valeurs|unite ?:?)\s*(?:en\s+|de\s+)?(milliards?|millions?|milliers?|mds?|mxof|kxof|mfcfa|kfcfa|"
                       r"francs? cfa|fcfa|f\.? ?cfa|xof)\b")


def line_units(n):
    """Unités annoncées par un en-tête de tableau (« (en millions de FCFA) », « Données en milliers ») : [(position, facteur)].
    Une ligne qui porte des montants n'est pas un en-tête (sauf les années)."""
    rest = re.sub(r"\b(?:19|20)\d\d\b|(?<![\d ,])[12][ ,]0\d\d\b", " ", n)
    if re.search(r"\d{1,3}(?:[ .,]\d{3})+|\b\d{3,}\b|\d,\d", rest) or re.search(r"par action|nominal|dividende|cours", n):
        return []
    out = []
    for m in UNIT_LINE.finditer(n):
        w = m.group(1)
        f = 1e9 if w.startswith("milliard") or w.startswith("md") else 1e6 if w.startswith("million") or w in ("mxof", "mfcfa") \
            else 1e3 if w.startswith("millier") or w in ("kxof", "kfcfa") else 1.0
        out.append((m.start(), f))
    return out


def doc_kind(txt, title=""):
    """Annuel, semestriel ou trimestriel : d'après le titre de la publication d'abord (« 1er semestre 2026 »), sinon d'après
    les dates de clôture des colonnes (30 juin, 31 mars, 30 septembre). Un document qui joint aux comptes annuels l'activité
    du premier trimestre suivant reste annuel."""
    ti = re.sub(r"[_]+", " ", nrm(title or ""))
    annual_t = re.search(r"exercice\s*\d{4}|etats financiers(?: provisoires?| definitifs?| certifies| approuves| annuels)*\s*\d{4}|annuel", ti)
    if re.search(r"semestr|half.year", ti) and not (annual_t and re.search(r"et (?:le |du )?(?:rapport|activite).*semestr", ti)):
        return "semestre"
    if re.search(r"trimestr|quarter", ti) and not annual_t:
        return "trimestre"
    t = nrm(txt[:6000])
    # titre annuel mais colonnes arrêtées au 30 juin (situation semestrielle déposée sous un titre d'exercice) : semestriel
    t30 = nrm(txt[:40000])
    n_juin = len(re.findall(r"(?:^|\s)30 ?(?:juin|/0?6/|-0?6-|\.0?6\.) ?(?:20|19)?\d{2}(?=\s|$)", t30, re.M))
    n_dec = len(re.findall(r"(?:^|\s)3[14] ?(?:decembre|/12/|-12-|\.12\.) ?(?:20|19)?\d{2}(?=\s|$)", t30, re.M))
    if annual_t and n_juin >= 2 and n_juin * 2 >= n_dec:
        return "semestre"
    if annual_t:
        return "annuel"
    if re.search(r"(?:au |clos le |arrete au |situation au )?30 ?(?:juin|/06/|-06-|\.06\.)\s*\d{2,4}|1er semestre|premier semestre|semestriel", t) and not re.search(r"31 ?(?:decembre|/12/|-12-)\s*\d{2,4}", t[:3000]):
        return "semestre"
    if re.search(r"(?:31 ?(?:mars|/03/)|30 ?(?:septembre|/09/))\s*\d{2,4}", t) and not re.search(r"31 ?(?:decembre|/12/|-12-)\s*\d{2,4}", t[:3000]):
        return "trimestre"
    return "annuel"


BROKEN = re.compile(r"(?<![\d,.])(\d{1,3}(?: \d{1,3})+) ?,(\d{1,2})(?![\d])")


def _join_broken(m):
    """« 2 3 09 ,1 » -> « 2309,1 » ; « 1 084,1 » reste « 1 084,1 » (groupes de milliers réguliers)."""
    g = m.group(1).split(" ")
    if all(len(x) == 3 for x in g[1:]) and " ," not in m.group(0):
        return m.group(0)
    return "".join(g) + "," + m.group(2)


GLYPH_DIGITS = {chr(0x3EC + d): str(d) for d in range(10)}
GLYPH_DIGITS.update({"\x03": " ", "\u0372": "-"})
# autre police sans table de caractères : codes de glyphes décalés de 29 (chiffres \x13 à \x1c, espace \x03, tiret \x10, virgule \x0f)
GLYPH_DIGITS2 = {chr(0x13 + d): str(d) for d in range(10)}
GLYPH_DIGITS2.update({"\x03": " ", "\x10": "-", "\x0f": ","})


_SHIFT_ACC = {0x87: "à", 0x80: "Ç", 0x8d: "é", 0x8e: "è", 0x8f: "ê", 0x90: "ë", 0x93: "î", 0x94: "ï", 0x96: "ö", 0x97: "ù", 0x98: "ô", 0x9a: "û",
              0xb6: "'"}
_SHIFT_KW = re.compile(r"\b(?:total|actif|passif|resultat|produits|charges|ventes|achats|dettes|capital|tresorerie|immobilisations|stocks|"
                       r"variation|exercice|impots|autres|fournisseurs|clients|reserves|dotations|services|transports|frais)\b")


def _shift_seg(seg):
    out = []
    for ch in seg:
        o = ord(ch)
        if 3 <= o <= 0x7e and ch not in " \t\n\r\x0c":  # (les espaces de mise en page sont de vraies espaces ; l'espace codée est \x03)
            o += 29
            out.append(_SHIFT_ACC.get(o, chr(o)) if o > 0x7e else chr(o))
        elif ch == "¶":
            out.append("'")
        else:
            out.append(ch)
    return "".join(out)


def _coded(seg):
    if any("\x03" <= ch <= "\x1c" and ch not in "\t\n\r\x0c" for ch in seg):
        return True
    letters = [ch for ch in seg if ch.isalpha()]
    if len(letters) < 4:
        return False
    vow = sum(1 for ch in nrm(seg) if ch in "aeiouy") / len(letters)
    if vow >= 0.25:
        return False  # texte en clair (des voyelles)
    dec = _shift_seg(seg)
    ld = [ch for ch in dec if ch.isalpha()]
    return bool(ld) and sum(1 for ch in nrm(dec) if ch in "aeiouy") / len(ld) >= 0.35 and \
        (bool(_SHIFT_KW.search(nrm(dec))) or sum(1 for ch in dec if ch.islower()) >= 4)


def decode_shift(txt):
    """Police sans table de caractères dont les codes de glyphes valent le caractère moins 29 (« 7$ 9HQWHV GH PDUFKDQGLVHV » =
    « TA Ventes de marchandises », chiffres \x13 à \x1c) : chaque segment de ligne (séparé par deux espaces ou plus) qui porte ces
    codes, ou qui n'a de voyelles qu'une fois décalé, est décodé ; le texte en clair reste tel quel."""
    out = []
    for ln in txt.split("\n"):
        parts = re.split(r"(\s{2,})", ln)
        cod = [bool(p_) and not p_.isspace() and _coded(p_) for p_ in parts]
        if any(cod):  # sur une ligne codée, les courts codes de référence (« 7$ » = TA) le sont aussi
            cod = [c_ or (bool(p_) and not p_.isspace() and len(p_) <= 3 and not re.search(r"[a-z0-9]", p_)) for c_, p_ in zip(cod, parts)]
        out.append("".join(_shift_seg(p_) if c_ else p_ for c_, p_ in zip(cod, parts)))
    return "\n".join(out)


def clean(txt, ocr=False):
    """Caractères parasites de la reconnaissance de caractères (barres, crochets) autour des montants ; montants dont la
    couche texte a cassé les chiffres (« 1 19 9 ,2 ») recollés quand le document en compte beaucoup ; chiffres d'une police
    sans table de caractères (codes de glyphes Ϭ…ϵ pour 0…9) remis en chiffres."""
    if sum(1 for ch in txt[:200000] if "\u03ec" <= ch <= "\u03f5") >= 30:
        txt = "".join(GLYPH_DIGITS.get(ch, ch) for ch in txt)
    if sum(1 for ch in txt[:300000] if "\x13" <= ch <= "\x1c") >= 30:
        txt = decode_shift(txt)
    if len(re.findall(r"\d ,\d|(?<!\d)\d{1,2} \d{1,2} ?,\d", txt)) >= 8:
        txt = BROKEN.sub(_join_broken, txt)
        txt = re.sub(r"(?<=\d) ,(?=\d{1,2}(?!\d))", ",", txt)

    # espaces des milliers perdus ou déplacés (« 1673 272 », « 50 701178 », « 2 05 4 491 ») -> groupes recollés quand ils ne
    # forment pas déjà un montant régulier (1 à 3 chiffres puis groupes de 3) ; toujours après reconnaissance de caractères,
    # et dans la couche texte quand le document en compte plusieurs
    def _irr(g):
        return not (len(g[0]) <= 3 and all(len(x) == 3 for x in g[1:]))

    def _run_reg(m):
        # suite régulière de groupes de trois chiffres trop longue pour un seul montant (« 137 319 985 209 131 081 463 214 ») :
        # coupée en deux montants quand une seule coupure respecte les 13 chiffres au plus (ici 4 + 4 groupes)
        g = m.group(0).split(" ")
        if not _irr(g) and len("".join(g)) > 13:
            cuts = [c for c in range(1, len(g)) if len("".join(g[:c])) <= 13 and len("".join(g[c:])) <= 13]
            if len(cuts) == 1:
                return "".join(g[:cuts[0]]) + "  " + "".join(g[cuts[0]:])
        return m.group(0)

    def _run(m):
        g = m.group(0).split(" ")
        if not _irr(g):
            return _run_reg(m)
        j = "".join(g)
        if len(g) == 2 and len(g[0]) == len(g[1]) >= 4 and len(g[1]) % 3:
            return "  ".join(g)  # deux montants de même ordre écrits sans espace des milliers (« 95725 99149 »), séparés par une seule espace
        if len(j) <= 13:
            return j
        # suite de plusieurs montants dont les groupes de milliers sont mal découpés (« 22372337 396 32 374 022 046 ») : un
        # nouveau montant commence à chaque groupe qui n'a pas trois chiffres
        segs, cur = [], [g[0]]
        for tok in g[1:]:
            # un groupe de trois chiffres poursuit le montant ; deux groupes collés (« 440330 ») aussi, derrière un début régulier
            if len(tok) == 3 or (len(tok) % 3 == 0 and len(cur[0]) <= 3 and len("".join(cur)) + len(tok) <= 13):
                cur.append(tok)
            else:
                segs.append(cur)
                cur = [tok]
        segs.append(cur)
        if len(segs) >= 2 and all(len("".join(sg)) <= 13 for sg in segs):
            return "  ".join("".join(sg) for sg in segs)
        # un montant de plus de 13 chiffres n'existe pas : parmi les découpages possibles (mêmes règles, 13 chiffres au plus par
        # montant ; un groupe de 3k+1 chiffres peut cacher un chiffre parasite en tête ou en queue : « 2341 » = « 234 » + « 1 »),
        # le moins morcelé, puis le plus équilibré (« 353554454 297 251 401 » = 353 554 454 | 297 251 401)
        if any(len("".join(sg)) > 13 for sg in segs) and len(g) <= 24:
            best = []

            def _cont(cur, tok):
                return (len(tok) == 3 or (len(tok) % 3 == 0 and len(cur[0]) <= 3)) and len("".join(cur)) + len(tok) <= 13

            def _walk(i, cur, acc):
                if len(acc) > 6 or len(best) > 400:
                    return
                if i == len(g):
                    best.append(acc + [cur])
                    return
                tok = g[i]
                if _cont(cur, tok):
                    _walk(i + 1, cur + [tok], acc)
                if len(tok) <= 13:
                    _walk(i + 1, [tok], acc + [cur])
                if len(tok) >= 4 and len(tok) % 3 == 1:
                    if _cont(cur, tok[:-1]):
                        _walk(i + 1, [tok[-1]], acc + [cur + [tok[:-1]]])
                    _walk(i + 1, [tok[0], tok[1:]], acc + [cur])
            _walk(1, [g[0]], [])
            if best:
                sg = min(best, key=lambda ss: (len(ss), max(len("".join(x)) for x in ss) - min(len("".join(x)) for x in ss)))
                if len(sg) >= 2 and all(len("".join(x)) <= 13 for x in sg):
                    return "  ".join("".join(x) for x in sg)
        return m.group(0)
    RUN = r"(?<![\d,.])\d+(?: \d+)+(?![\d,.])"

    if not ocr:
        if sum(1 for m in re.finditer(RUN, txt) if _irr(m.group(0).split(" ")) and len(m.group(0).split(" ")[-1]) < 3) >= 5:
            txt = re.sub(RUN, _run, txt)
        else:
            txt = re.sub(RUN, _run_reg, txt)
        return txt
    txt = re.sub(r"[|\[\]{}¦]", " ", txt)
    txt = re.sub(r"(?<![\w~])~ ?(?=\d)", "-", txt)  # (« ~4 302 883 480 » : signe moins lu comme un tilde)
    # point ou virgule lu à la place d'une espace de milliers (« 301 493.038 967 ») : dans un montant à groupes de trois chiffres
    txt = re.sub(r"(?<![\d.,])(\d{1,3}(?: \d{3})+)[.,](\d{3}(?: \d{3})*)(?![\d.,])", r"\1 \2", txt)
    txt = re.sub(r"(?<![\d.,])(\d{1,3})[.,](\d{3}(?: \d{3})+)(?![\d.,])", r"\1 \2", txt)
    txt = re.sub(RUN, _run, txt)
    # parenthèse fermante parasite derrière un montant (barre de tableau lue « ) ») : effacée, sauf celle d'un montant négatif
    # écrit entre parenthèses (« (16 512) »), qui est d'abord mise à l'abri
    txt = re.sub(r"\((\s?-?\d[\d  \u202f.,]*\d|\d)\)", "\u2045\\1\u2046", txt)
    txt = re.sub(r"(?<=\d)[)](?=\s|$)", " ", txt)
    txt = txt.replace("\u2045", "(").replace("\u2046", ")")
    txt = re.sub(r"(?<=\d) ?[.:;](?=\s{2,}|$)", " ", txt)
    return txt


# ---------------------------------------------------------------- découpage d'une ligne
MAX_AMOUNT = 1e13  # aucun montant d'une société cotée n'atteint 10 000 milliards de FCFA (hors ETI, qui publie en dollars)
LINE_CODE = re.compile(r"^(\s*)([A-Z]{2}|[A-Z](?=[0-9A-Z]{0,1}[0-9])[0-9A-Z]{2})(?=\s+\S|\s*$)")
NOT_CODE = {"LE", "LA", "DE", "DU", "ET", "EN", "AU", "OU", "IL", "UN", "NB", "PM", "AG", "CA"}


def _cells(line, skip=()):
    """Découpe une ligne en libellés et montants avec leur position (fin de colonne) ; « - » isolé = case vide.
    Un libellé séparé d'un autre par un grand blanc (deux tableaux côte à côte) forme sa propre cellule.
    Renvoie [(type, valeur, fin, début)] avec type L (libellé), N (montant), D (case vide), X (montant illisible), C (référence)."""
    out, pos = [], 0
    m = LINE_CODE.match(line)
    if m and (m.group(2) not in NOT_CODE or re.match(r"\s*CA\s+(?:capital|\d)", line, re.I)):
        out.append(("C", m.group(2), m.end(), m.start(2)))
        pos = m.end()

    def labels(gap, start, end):
        parts = [(mm.start(), mm.group(0)) for mm in re.finditer(r"\S+(?:\s{1,4}\S+)*", gap)]
        for k, (st_, part) in enumerate(parts):
            if re.fullmatch(r"[-−–—‐‑]+", part.strip()):
                out.append(("D", None, start + st_ + len(part), start + st_))
                continue
            txt_ = re.sub(r"(?<!\S)[-−–‐‑](?!\S)", " ", part)
            txt_ = re.sub(r"^\s*(?:-?\d+(?:[.,]\d+)?\s*%\s*)+", "", txt_).strip()
            if re.search(r"b[eé]n[eé]fice \+ ou perte", txt_, re.I):
                out.append(("L", "resultat de l'exercice au bilan", start + st_ + len(part), start + st_))  # sous-libellé du résultat au bilan
                continue
            if txt_.startswith("(") or re.search(r"\bsomme\b", txt_, re.I) or re.fullmatch(r"[(+\-/=: ]*(?:[A-Z]{1,2}\b[ +\-à=:]*)+\)?", txt_):
                continue  # formule de calcul (« (XB+RA+RB) », « (somme TK à RN) »), renvoi « (1) »
            if re.fullmatch(r"[+\-/ ]+|notes?|\d+|[a-z]", txt_.strip(), re.I):
                continue
            if re.search(r"[A-Za-zÀ-ÿ]{2}", txt_):
                out.append(("L", txt_, start + st_ + len(part), start + st_))
    # dates en toutes lettres (« 31 décembre 2021 ») : ni montant ni libellé
    line = re.sub(r"(?i)(?<![\d,.])\d{1,2}(?:er)? ?(?:[-/.] ?)?(?:janv|f[ée]vr|mars|avr|mai|juin|juil|ao[uû]t|sept|oct|nov|d[ée]c)[a-zéû]*\.?"
                  r"(?: ?(?:[-/.] ?)?(?:19|20)?\d\d(?![\d,.]))?(?![a-z])", lambda m_: " " * len(m_.group(0)), line)
    # renvois de notes à plusieurs niveaux (« 6.3.11 ») : ni montant ni libellé
    line = re.sub(r"(?<![\d.,])\d{1,2}(?:\.\d{1,2}){2,}(?![\d.,])", lambda m_: " " * len(m_.group(0)), line)
    dates = [(m_.start(), m_.end()) for m_ in re.finditer(r"(?<![\d.])\d{1,2}[./]\d{1,2}[./](?:19|20)\d\d(?![\d.])", line)]  # « 07.06.2022 »
    for mm in NUM.finditer(line, pos):
        tok = mm.group(0)
        before = line[max(0, mm.start() - 1):mm.start()]
        after = line[mm.end():mm.end() + 2]
        if (before and (before.isalpha() or before in "/")) or (after[:1] and (after[:1].isalpha() or after[:1] in "%/")) \
                or after.strip()[:1] == "%" or mm.end() in skip or any(a_ <= mm.start() < b_ for a_, b_ in dates):
            continue
        gap = line[pos:mm.start()]
        if _NOTE_DOT[0] and re.fullmatch(r"\d{1,2}\.\d{1,2}", tok.strip()):
            labels(gap, pos, mm.start())
            pos = mm.end()
            continue  # renvoi de note « 5.3 » dans un document où la virgule est le séparateur décimal
        if re.search(r"(?:^|\s)notes?\s*$", gap, re.I) and re.fullmatch(r"\d{1,2}(?:[.,]\d{1,2})?[a-z]?", tok.strip()):
            labels(gap[:re.search(r"(?:^|\s)notes?\s*$", gap, re.I).start()], pos, mm.start())
            pos = mm.end()
            continue  # renvoi de note (« Note 23 »)
        sign = 1
        g2 = gap.rstrip()
        if g2.endswith(("-", "−", "–", "‐", "‑")) and (len(g2) < 2 or g2[-2] == " ") and not tok.lstrip().startswith(("(", "-", "−", "–", "‐", "‑")):
            # (colonne des signes « - » devant un montant non signé ; un montant imprimé avec son propre signe le garde)
            sign = -1
            gap = g2[:-1]
        labels(gap, pos, mm.start())
        v = num_val(tok)
        if v is not None and abs(v) >= MAX_AMOUNT:
            out.append(("X", None, mm.end(), mm.start()))  # 14 chiffres et plus : montants collés par la lecture (jamais un montant en FCFA) : case illisible
        elif v is not None:
            out.append(("N", sign * v, mm.end(), mm.start()))
        pos = mm.end()
    labels(line[pos:], pos, len(line))
    return out


def _hdr(line):
    """Années d'en-tête d'une ligne [(fin, début, année ou ('N', décalage))], si la ligne n'est faite que d'en-têtes."""
    n = nrm(line)
    hs = []
    for m in re.finditer(r"(?<![\d,.])(?:(?:\d{1,2})(?: ?[-/.] ?| {1,2})(?:\d{1,2}|(?:janv?|fevr?|mars|avr|mai|juin|juil|aout|sept?|oct|nov|dec)[a-z]{0,6}\.?)(?: ?[-/.] ?| {1,2}))?((?:19[89]\d|20[0-3]\d)|\d{2})(?![\d%]|[,.]\d)", n):
        y = m.group(1)
        if len(y) == 2:
            if not re.search(r"[-/. ]$", n[:m.start(1)]) or m.start(1) == m.start():
                continue  # « 09 » seul n'est pas une année ; « 31-déc-09 » oui
            y = 2000 + int(y) if int(y) < 50 else 1900 + int(y)
        y = int(y)
        if re.match(r"0?1 ?[-/.] ?0?1(?![0-9])|0?1(?:er)? ?[-/. ]? ?janv", m.group(0)) and not re.match(r"\s*(?:au|to|a|-)\s", n[m.end():]):
            y -= 1  # colonne « 01/01/N » (bilan d'ouverture) : c'est la clôture de l'exercice précédent (sauf « du 01/01/N au 31/12/N »)
        hs.append((m.end(), m.start(), y))
    for m in re.finditer(r"(?<![a-z])(?:janv?|fevr?|mars|avr|mai|juin|juil|aout|sept?|oct|nov|dec)[a-z]*\.?(?: ?[-/] ?| {1,2})(\d{4}|\d{2})(?![\d%,])", n):
        y = int(m.group(1)) if len(m.group(1)) == 4 else 2000 + int(m.group(1))  # « Dec.-24 », « déc. 2024 »
        if m.group(0).startswith("janv") and re.search(r"(?:^|\s)0?1(?:er)?\s*$", n[:m.start()]) and not re.match(r"\s*(?:au|to|a|-)\s", n[m.end():]):
            y -= 1  # « 1er janvier N » (bilan d'ouverture) : clôture de l'exercice précédent (sauf « du 1er janvier N au 31 décembre N »)
        if 1990 <= y <= 2039 and not any(s0 <= m.start() < e0 for e0, s0, _ in hs):
            hs = [h for h in hs if not (m.start() <= h[1] < m.end())]  # (l'année nue déjà relevée dans cette date)
            hs.append((m.end(), m.start(), y))
    for m in re.finditer(r"(?<![\d,.])(?:31|30)[ ./-]?(?:12|06|09|03)[ ./-]?((?:19[89]|20[0-3])\d)(?![\d,.%])", n):  # « 31122004 », « 3112.2003 » (date collée)
        y = int(m.group(1))
        if not any(s0 <= m.start() < e0 or s0 < m.end() <= e0 for e0, s0, _ in hs):
            hs.append((m.end(), m.start(), y))
    for m in re.finditer(r"(?<![\d,.])(19[89]|20[0-3]) (\d)(?![\d,.%])", n):  # « 202 4 » (année coupée par la couche texte)
        y = int(m.group(1) + m.group(2))
        if not any(s0 <= m.start() < e0 for e0, s0, _ in hs):
            hs.append((m.end(), m.start(), y))
    sep_y = []
    for m in re.finditer(r"(?<=[\s(])(\d)[, ](\d{3})(?=\s|$)", n):  # « 2,009 », « 2 013 » (année imprimée avec séparateur de milliers)
        y = int(m.group(1) + m.group(2))
        if 1990 <= y <= 2027:
            sep_y.append((m.end(), m.start(), y))
    # (des montants « 2 030   2 012 » ne sont pas des années : plusieurs de ces années doivent se suivre)
    ys_ = sorted({y for _, _, y in sep_y})
    if sep_y and len(ys_) <= 2 and (len(ys_) == 1 or ys_[1] - ys_[0] == 1):
        hs += sep_y
    hs.sort()
    rest = n
    for e, s, _ in sorted(hs, reverse=True):
        rest = rest[:s] + " " * (e - s) + rest[e:]
    if hs and not re.search(r"\d{3,}", rest) and len(re.findall(r"\d", rest)) <= 4:
        return hs
    if len(hs) >= 2:  # en-tête d'un tableau, avec plus loin sur la même ligne (autre page imprimée à côté) des montants ou un texte daté
        far, near = max(e for e, _, _ in hs) + 15, min(s0 for _, s0, _ in hs) - 15
        if all(m.start() >= far or m.end() <= near for m in re.finditer(r"\d+", rest)):
            return hs
    hn = [(m.end(), m.start(), ("N", -1 if m.group(1) else 0)) for m in re.finditer(r"(?<![a-z0-9])(?:exercice\s+|annee\s+)?n(\s?-\s?1)?(?![a-z0-9])", n)]
    if len(hn) >= 2 and not re.search(r"\d{3,}", n):
        return hn
    return []


def head_sec(p):
    """État annoncé par un titre (ou un titre de colonne) : actif, passif, compte de résultat, flux, hors bilan, bilan."""
    p = re.sub(r"\s+", " ", p).strip()
    if len(p) > 90 or re.search(r"\d{3}", re.sub(r"(?:19|20)\d\d|\d[ ,.]\d{3}", "", p)):
        return None
    p = re.sub(r"\s+", " ", re.sub(r"[^a-z' /-]|(?<![a-z])[-/](?![a-z])", " ", re.sub(r"(?:19|20)\d\d|\d[ ,.]\d{3}", " ", p))).strip()
    if re.search(r"tableau (?:[a-z]+ )?des? flux|flux de tresorerie(?: \(tft\))?$|tableau financier|tafire|tableau (?:des )?emplois|^ressources$|^emplois$|tableau de financement", p):
        return S_FLX
    if re.search(r"compte de resultat|comptes? de resultats|compte d.exploitation|compte des resultats|etat du resultat|income statement|pertes et profits|^produits$|^charges$|^produits ?/ ?charges$|^charges ?/ ?produits$|^debit$|^credit$", p):
        return S_CR
    if re.search(r"hors.?bilan|^engagements|affectation du resultat|projet d.affectation|repartition des benefices|^affectation$", p):
        return "hb"
    if re.search(r"^(?:bilan[^a-z]*)?actifs?(?: du bilan)?(?: consolide)?$|^actif ?:?$|^assets$|^actif (?:[-(:] ?)?(?:en|montants?|donnees)\b|^actif -|"
                 r"^(?:postes? )?(?:rubriques?|postes?) de l.actif$", p):
        return S_ACT
    if re.search(r"^(?:bilan[^a-z]*)?passi ?fs?(?: du bilan)?(?: consolide)?$|^passifs? (?:et )?capitaux propres$|^capitaux propres (?:et )?passifs?$|^liabilities|^passif (?:[-(:] ?)?(?:en|montants?|donnees)\b|^passif -|"
                 r"^(?:postes? )?(?:rubriques?|postes?) du passif$", p):
        return S_PAS
    if re.search(r"^bilan\b|situation financiere|balance sheet", p):
        return "bilan"
    return None


SEC_HEAD = [
    (S_FLX, re.compile(r"tableau des? flux|flux de tresorerie(?: \(tft\))?$|tableau financier|tafire|tableau emplois|tableau des emplois")),
    (S_CR, re.compile(r"compte de resultat|comptes? de resultats|compte d.exploitation|compte des resultats|etat du resultat|income statement|compte de pertes et profits")),
    (S_ACT, re.compile(r"^(?:bilan[^a-z]*)?actif(?: du bilan)?(?: consolide)?$|^actif ?:?$|^assets$")),
    (S_PAS, re.compile(r"^(?:bilan[^a-z]*)?passif(?: du bilan)?(?: consolide)?$|^passif ?:?$|^passif et capitaux propres$|^capitaux propres et passifs$|^liabilities")),
    ("hb", re.compile(r"^hors.?bilan|^engagements")),
    ("bilan", re.compile(r"^bilan\b|^situation financiere|etat de la situation financiere|balance sheet")),
]


def decolumn(txt):
    """Deux pages imprimées côte à côte (bilan et compte de résultat à gauche, TAFIRE à droite…) : la page est coupée à une
    gouttière verticale vide que ne chevauche aucune ligne d'en-tête d'années, avec au moins un en-tête de chaque côté ;
    les lignes de gauche puis celles de droite sont rendues l'une après l'autre. Sans telle gouttière, le texte est inchangé."""
    pages = txt.split("\f")
    out = []
    for pg in pages:
        lines = pg.splitlines()
        dl = _decolumn_lines(lines) if len(lines) >= 8 else lines
        out.append(pg if dl == lines else "\n".join(dl) + "\n")  # (texte inchangé quand la page n'est pas coupée)
    return "\f".join(out)


def _decolumn_lines(lines, depth=0):
    # (en-têtes d'années en clair seulement — « N / N-1 » se lit aussi dans des libellés — ; une seule page imprimée à la fois)
    heads = [(i, h) for i, h in ((i, _hdr(ln)) for i, ln in enumerate(lines)) if h and len({y for _, _, y in h if isinstance(y, int)}) >= 2]
    if len(heads) < 2 or depth > 2 or len(lines) > 150:
        return lines
    W = max(len(ln) for ln in lines)
    busy = [ln for ln in lines if ln.strip()]
    if W < 120 or len(busy) < 8:
        return lines
    occ = [0] * (W + 1)
    for ln in busy:
        for c, ch in enumerate(ln):
            if ch != " ":
                occ[c] += 1
    tol = max(1, len(busy) // 100)
    first = min(len(ln) - len(ln.lstrip()) for ln in busy)
    best = None
    for c in range(first + 20, W - 20):
        if occ[c] > tol or occ[c - 1] > tol or occ[c + 1] > tol:
            continue
        left = [h for _, h in heads if all(e <= c for e, _, _ in h)]
        right = [h for _, h in heads if all(s_ >= c for _, s_, _ in h)]
        if len(left) + len(right) < len(heads) or not left or not right:
            continue  # un en-tête chevauche la coupure (tableaux côte à côte sous un même en-tête), ou tout est d'un côté
        n_r = sum(1 for ln in busy if re.search(r"[a-zA-Z]{3}", ln[c:]))
        if n_r < 4:
            continue
        # la coupure ne doit séparer aucun libellé de ses montants (libellé à gauche, montant à droite, blanc étroit entre eux)
        cut_tbl = False
        for ln in busy:
            lft, rgt = ln[:c].rstrip(), ln[c:]
            gap = (len(ln[:c]) - len(lft)) + (len(rgt) - len(rgt.lstrip()))
            if lft and re.search(r"[a-zA-Z]$", lft) and re.match(r"\s*-?\s*\d", rgt) and gap < 30:
                cut_tbl = True
                break
        if cut_tbl:
            continue
        best = c
        break
    if best is None:
        return lines
    L = [ln[:best].rstrip() for ln in lines]
    R = [ln[best:].rstrip() for ln in lines]
    return _decolumn_lines(L, depth + 1) + [""] + _decolumn_lines(R, depth + 1)


def parse(txt, fy_hint=None, title="", ocr=False):
    """{postes: {poste: {exercice: montant (unité du document)}}, unité, exercice, type, norme, périmètre, période…}"""
    txt = clean(txt, ocr)
    txt = re.sub(r"(?<![A-Za-z0-9])N ?- ?1(?![0-9])", "N-1", txt)  # « T(N) - T(N - 1) » : le « - 1 » n'est pas un montant
    if not ocr:
        txt = decolumn(txt)
    n_k2 = len(re.findall(r"(?<![\d,.])\d{1,3}(?:,\d{3}){2,}(?![\d,])", txt))
    n_k1 = len(re.findall(r"(?<!\d )(?<![\d,.])\d{1,3},\d{3}(?![\d,])", txt))  # « 54,232 » (virgule des milliers, à l'anglaise)
    n_dec = len(re.findall(r"(?<![\d,.])\d+,\d{1,2}(?![\d,])", txt))
    n_sp = len(re.findall(r"\d \d{3},\d", txt))  # « 1 633,5 » (espace des milliers, virgule décimale)
    _COMMA_K[0] = (n_k2 >= 5 and n_dec <= n_k2 // 10) or (n_k1 >= 15 and n_dec <= n_k1 // 10 and n_sp * 10 < n_k1) or _COMMA_FORCE[0]
    _NOTE_DOT[0] = not _COMMA_K[0] and len(re.findall(r"(?<![\d.,])\d{1,3},\d{1,2}(?![\d,.])", txt)) >= 20 and \
        len(re.findall(r"(?<![\d.,])\d{1,2}\.\d{1,2}(?![\d,.])", txt)) < len(re.findall(r"(?<![\d.,])\d{1,3},\d{1,2}(?![\d,.])", txt)) / 2
    # montants en milliards avec une décimale (« 10,0 ») : un tel premier montant n'est un renvoi de note qu'au voisinage d'une colonne « Notes »
    milliards = bool(re.search(r"en milliards", nrm(txt)))
    fy = fiscal_year(txt, fy_hint)
    lines = txt.splitlines()
    # montants à quatre groupes de chiffres ou plus : rares dans un document en millions (sinon le document est en francs)
    grp_ = [len(m_.group(0).split(" ")) for m_ in re.finditer(r"(?<![\d,.])\d{1,3}(?: \d{3})+(?![\d,.])", txt)]
    few_big = bool(grp_) and sum(1 for g_ in grp_ if g_ >= 4) <= max(6, len(grp_) * 0.1)
    nt_ = nrm(txt)
    revised = bool(re.search(r"^\s*xb\s+chiffre d.affaires|^\s*xi\s+resultat net \(xg", nt_, re.M))
    brut_tbl = False
    occ = []  # (poste, état, périmètre, ligne, {année: valeur}, ordre déduit ?)
    heads = []  # [(ligne, [(fin, début, année)])]
    sec, split, perim = None, None, None
    tt_ = nrm(title or "") + " " + nrm(txt[:3000])
    std_cur = "ifrs" if re.search(r"\bifrs\b|normes? internationales?", tt_) and not re.search(r"syscohada", nrm(title or "")) else "syscohada"
    # vocabulaire propre aux normes IFRS et aux comptes consolidés, quand les titres ne le disent pas
    if std_cur == "syscohada" and not re.search(r"syscohada", nt_) and \
            len(re.findall(r"resultat global|ne donnant pas le controle|actifs? non courants?|passifs? non courants?", nt_)) >= 2:
        std_cur = "ifrs"
    conso_hint = bool(re.search(r"ensemble consolide|ne donnant pas le controle|interets minoritaires|perimetre de consolidation", nt_))
    order_votes = []
    pend = []
    single_hint = []
    unit_side, units_seen, unit_at = [None, None], [], -99
    unit_tag = [None, None]  # ligne de l'annonce d'unité en vigueur de chaque côté (identifie le tableau)
    sw_pas = [False]  # passage au passif décidé sur un libellé (sans titre « PASSIF ») : révocable
    hb_aff = [False]  # section « hb » ouverte par un projet d'affectation du résultat (et non par le hors bilan)
    note_at = -999  # dernière ligne d'en-tête avec une colonne « Note(s) »
    for i, ln in enumerate(lines):
        if "\f" in ln:
            ln = ln.replace("\f", "")
        h = _hdr(ln)
        n_ = nrm(ln).strip()
        if re.search(r"(?:^|\s{2})(?:notes?|ref\.? notes?)(?:\s{2}|$)", n_) and not re.search(r"\d{3}", re.sub(r"\b(?:19|20)\d\d\b", "", n_)):
            note_at = i  # (en-tête « Note  2024  2023 » : les années ne sont pas des montants)
        lu_ = line_units(nrm(ln))
        for pos_u, f_u in lu_:  # unité de chaque tableau (de chaque côté quand deux tableaux se font face)
            if split and pos_u >= split[0] - 5:
                unit_side[1], unit_tag[1] = f_u, i
            else:
                unit_side[0], unit_tag[0] = f_u, i
                # (seule annonce de la ligne, rien à droite : en tête d'une nouvelle page, elle vaut pour les deux tableaux)
                if not split or (len(lu_) == 1 and not ln[split[0]:].strip()):
                    unit_side[1], unit_tag[1] = f_u, i
            units_seen.append(f_u)
            unit_at = i
        if h:
            # en-tête sur deux lignes (« EXERCICE 2025 » / « EXERCICE 2024 ») : regroupé avec la précédente
            if len(h) == 1 and heads and i - heads[-1][0] <= 3 and len(heads[-1][1]) == 1 and heads[-1][1][0][2] != h[0][2]:
                heads[-1] = (i, sorted(heads[-1][1] + h))
            else:
                heads.append((i, h))
            if re.search(r"\bbrut\b|amortissements?|amort\.|depreciations", n_):
                brut_tbl = True
        nb_ = nrm(ln)
        for e_, s0_, _ in (h or []):
            nb_ = nb_[:s0_] + " " * (e_ - s0_) + nb_[e_:]
        nl_t = nrm(ln)  # (texte où chercher les titres d'états)
        title_ok = not re.search(r"\d{3}", re.sub(r"(?:19|20)\d\d", "", nb_))
        if not title_ok and split:
            # tableaux côte à côte : le titre d'un nouvel état d'un côté (« TABLEAU DE FLUX DE TRESORERIE ») face aux montants de
            # l'autre côté ; seul le côté sans montants est lu comme titre
            L_, R_ = nb_[:split[0]], nb_[split[0]:]
            if not re.search(r"\d{3}", re.sub(r"(?:19|20)\d\d", "", L_)) and re.search(r"[a-z]{4}", L_):
                nl_t, title_ok = nl_t[:split[0]] + " " * len(nl_t[split[0]:]), True
            elif not re.search(r"\d{3}", re.sub(r"(?:19|20)\d\d", "", R_)) and re.search(r"[a-z]{4}", R_):
                nl_t, title_ok = " " * len(nl_t[:split[0]]) + nl_t[split[0]:], True
        if title_ok:
            # titres d'états et sous-titres (actif / passif côte à côte, consolidé / social)
            if re.search(r"(?:bilan|comptes?|etats?(?: de synthese| financiers)?|compte de resultat|tableau des flux(?: de tresorerie)?|resultats?|situation financiere|"
                         r"etat du resultat global|flux de tresorerie)\s+(?:[a-z']+\s+){0,3}consolid", n_) and not re.search(r"sociaux|individuel", n_):
                perim = "conso"
            elif re.search(r"(?:bilan|comptes?|etats?(?: de synthese| financiers)?|compte de resultat|tableau des flux)\s+(?:[a-z']+\s+){0,2}(?:sociaux|individuels?|social)\b|"
                           r"comptes sociaux", n_):
                perim = "social"
            elif re.search(r"(?:etats? financiers|bilan|comptes? de resultat|comptes|tafire)(?: [a-z'()-]+){0,4} [a-z]+ s\.?a\.?(?:\s|$)", n_) and \
                    not re.search(r"consolid|groupe", n_):
                perim = "social"  # « états financiers résumés Sonatel SA » : comptes de la société seule, après ceux du groupe
            elif re.fullmatch(r"(?:[a-z'&.-]+ ){1,4}s\.?a\.?", n_.strip()) and not re.search(r"consolid|groupe", n_):
                perim = "social"  # ligne « ONATEL SA » en tête des états de la société seule
            if re.search(r"\bifrs\b|normes? internationales?", n_) and not re.search(r"syscohada", n_):
                std_cur = "ifrs"
            elif re.search(r"syscohada", n_) and not re.search(r"\bifrs\b", n_):
                std_cur = "syscohada"
            if re.search(r"\bbruts?\b.*amort|amortissements?.*\bnet|\bbruts?\b.*\bnets?\b", n_):
                brut_tbl = True
            nl = nl_t
            found_s, found_all = [], []
            for mm in re.finditer(r"\S+(?:\s{1,2}\S+)*", nl):
                s_ = head_sec(mm.group(0).strip(" :-"))
                if s_ == "hb":
                    hb_aff[0] = bool(re.search(r"affectation|repartition", mm.group(0)))  # (projet d'affectation du résultat, ou hors bilan)
                if s_:
                    found_all.append((mm.start(), s_))
                if s_ and (not found_s or found_s[-1][1] != s_):
                    found_s.append((mm.start(), s_))
            if i - unit_at > 4:  # nouvel état sans unité annoncée à côté : unité à déterminer (du côté du titre)
                for pos_h, s_h in found_all:
                    if s_h in (S_ACT, S_PAS, S_CR, S_FLX, "bilan"):
                        if split and pos_h >= split[0] - 5:
                            unit_side[1] = None
                        else:
                            unit_side[0] = None
                            if not split:
                                unit_side[1] = None
            if len(found_all) >= 2 and len({x[1] for x in found_all}) == 1 and found_all[0][1] not in ("bilan", "hb"):
                sec, split = found_all[0][1], None  # même état des deux côtés (« PRODUITS … CHARGES »)
            elif len(found_s) >= 2 and found_s[0][1] != found_s[1][1] and found_s[1][1] != "bilan":
                left = [e for e, _, _ in h if e < found_s[1][0]] if h else []
                s0 = S_ACT if found_s[0][1] == "bilan" else found_s[0][1]
                split = [(max(left) + 1) if left else max(0, found_s[1][0] - 12), s0, found_s[1][1], False]
                sec = s0
            elif found_s:
                s_ = found_s[0][1]
                if s_ == "bilan":
                    sec = S_ACT if sec not in (S_ACT, S_PAS) else sec
                elif split and s_ in (S_CR, S_FLX) and set(split[1:3]) <= {S_ACT, S_PAS}:
                    sec, split = s_, None  # nouvel état après le bilan (titre centré sur la page)
                elif split:  # deux tableaux côte à côte : seul le côté du titre change d'état
                    if found_s[0][0] < split[0] - 5:
                        split[1] = sec = s_
                    else:
                        split[2] = s_
                elif s_ != sec or split:
                    sec, split = s_, None
                if s_ == S_PAS:
                    brut_tbl = False
        cells = _cells(ln, skip={e for e, _, _ in h} if h else set())
        # deux colonnes collées par un seul espace (« 99 149 106 898 » dans un tableau en millions) : un montant impossible dans
        # l'unité du tableau (un milliard de millions…) est recoupé en deux montants de même ordre de grandeur
        if not ocr and few_big and any(c[0] == "N" for c in cells):
            cells2 = []
            for c in cells:
                u_c = (unit_side[1] if split and c[3] >= split[0] - 2 else unit_side[0]) or \
                    (max(set(units_seen), key=units_seen.count) if units_seen else None)
                tok = ln[c[3]:c[2]]
                g = re.findall(r"\d+", tok)
                maxg = {1e6: 3, 1e3: 4}.get(u_c)
                if c[0] == "N" and maxg and len(g) > maxg and re.fullmatch(r"\d{1,3}(?: \d{3})+", tok.strip()):
                    best = None
                    for k_ in range(1, len(g)):
                        a_, b_ = int("".join(g[:k_])), int("".join(g[k_:]))
                        if len(g[k_]) == 3 and 1 <= len(g[k_]) and a_ and b_:
                            sc_ = abs(math.log10(a_) - math.log10(b_))
                            if best is None or sc_ < best[0]:
                                best = (sc_, k_, a_, b_)
                    if best and best[0] <= 1.5 and len(" ".join(g[best[1]:])) and str(g[best[1]]).isdigit() and len(g[best[1]]) <= 3:
                        _, k_, a_, b_ = best
                        e1 = c[3] + len(" ".join(g[:k_]))
                        cells2 += [("N", float(a_), e1, c[3]), ("N", float(b_), c[2], e1 + 1)]
                        continue
                cells2.append(c)
            cells = cells2
        code = cells[0][1] if cells and cells[0][0] == "C" else None
        segs = []  # [(code, libellé, [(valeur, fin)], début)]
        illegible = {c_[2] for c_ in cells if c_[0] == "X"}  # fins des cases illisibles (chiffres collés) : leur libellé n'attend pas de montants
        k = 0
        while k < len(cells):
            c = cells[k]
            if c[0] == "C":
                k += 1
                continue
            if c[0] == "L":
                lab = c[1]
                st_ = c[3]
                j = k + 1
                if j + 1 < len(cells) and cells[j][0] == "L" and cells[j + 1][0] in ("N", "D", "X") and \
                        len(re.sub(r"[^A-Za-z]", "", cells[j][1])) <= 3:
                    j += 1  # référence ou bruit de lecture entre le libellé et ses montants (« CHIFFRE D'AFFAIRES  XB  … »)
                vals = []
                while j < len(cells) and cells[j][0] in ("N", "D", "X"):
                    vals.append((cells[j][1], cells[j][2]))
                    j += 1
                segs.append((code if not segs else None, lab, vals, st_))
                k = j
                continue
            # montants sans libellé sur la ligne (libellé sur la ligne précédente ou référence seule)
            j = k
            vals = []
            while j < len(cells) and cells[j][0] in ("N", "D", "X"):
                vals.append((cells[j][1], cells[j][2]))
                j += 1
            segs.append((code if not segs else None, "", vals, c[3]))
            k = j
        if split and split[3] and segs and not ocr:
            # « TOTAL ACTIF  x  y   x  y » : les montants au-delà de la limite appartiennent au tableau de droite (sans libellé)
            segs2 = []
            for code_, lab, vals, st_ in segs:
                lv = [x for x in vals if x[1] < split[0]]
                rv = [x for x in vals if x[1] >= split[0] + 8]
                if st_ is not None and st_ < split[0] - 2 and lab and len(lv) >= 1 and len(rv) >= 2 and len(lv) + len(rv) == len(vals):
                    segs2 += [(code_, lab, lv, st_), (None, "", rv, split[0])]
                else:
                    segs2.append((code_, lab, vals, st_))
            segs = segs2
        new_pend = []
        for si, (code_, lab, vals, st_) in enumerate(segs):
            s_here = sec
            side_ = 0
            if split and st_ is not None:
                if si > 0 and segs[si - 1][2] and st_ > 20:  # libellé qui suit des montants : tableau de droite
                    split[0] = min(split[0], st_) if split[3] else st_  # (la 1re mesure remplace l'estimation tirée du titre)
                    split[3] = True  # limite des deux tableaux vérifiée sur une ligne de montants
                    s_here = split[2]
                    side_ = 1
                else:
                    s_here = split[2] if st_ >= split[0] - 2 else split[1]
                    side_ = 1 if st_ >= split[0] - 2 else 0
            if code_ and re.fullmatch(r"[A-Z]{2}", code_) and code_[0] in CODE_SEC:
                s_here = CODE_SEC[code_[0]]
            labn = re.sub(r"\s+", " ", nrm(lab)).strip(" :.-*•")
            labn = re.sub(r"\b([ldnjs])' +", r"\1'", labn)
            # passif qui enchaîne sous le total de l'actif sans titre « PASSIF » (« Capital social » juste après « TOTAL ACTIF ») :
            # un libellé propre au passif fait passer ce côté de la page au passif
            if s_here == S_ACT and si == 0 and re.match(r"capital(?: social| souscrit)?$|capitaux propres|ressources stables$|passif circulant$|dettes financieres", labn) \
                    and any(v_ is not None for v_, _ in vals) \
                    and (not split or (side_ == 0 and max(e_ for _, e_ in vals) < split[0] + 2) or (side_ == 1 and min(e_ for _, e_ in vals) >= split[0] - 2)):
                s_here = S_PAS
                sw_pas[0] = True
                if split and side_ == 1:
                    split[2] = S_PAS
                elif split:
                    split[1] = S_PAS
                else:
                    sec = S_PAS
            elif s_here == S_PAS and sw_pas[0] and si == 0 and any(v_ is not None for v_, _ in vals) and \
                    re.match(r"immobilisations|stocks|creances|tresorerie ?-? ?actif|actif circulant|actif immobilise|charges immobilisees", labn):
                # (le passage au passif était à tort : un libellé du passif lu à gauche de ses montants, dans un bilan à deux colonnes
                # mal découpé ; les postes de l'actif qui suivent ramènent à l'actif)
                s_here = S_ACT
                sw_pas[0] = False
                if split and side_ == 1:
                    split[2] = S_ACT
                elif split:
                    split[1] = S_ACT
                else:
                    sec = S_ACT
            # mots coupés par la couche texte (« T OTAL », « RESULT AT NET », « CAPIT AUX »)
            labn = re.sub(r"\b(?:t otal|tot al|tota l)\b", "total", labn)
            labn = re.sub(r"\b(?:result at|resul tat|r esultat|resu ltat)\b", "resultat", labn)
            labn = re.sub(r"\b(?:capit aux|capi taux)\b", "capitaux", labn)
            if re.fullmatch(r"\(?\s*\+?\s*benefice \+ ou perte -\s*\)?", labn):
                labn = "resultat net de l'exercice"  # sous-libellé SYSCOHADA du résultat au bilan, seul sur sa ligne (scan)
            labn = re.sub(r"\s*\((?:[a-z]{1,2}|[ivx]+|\d)\)$", "", labn)  # renvoi de note « (1) », « (a) »
            labn = re.sub(r"^(?:[ivx]+|[a-h]|\d{1,2})[-.)] +", "", labn)  # numérotation « I. », « a) »
            labn = re.sub(r"\s*\(?(?:note|notes)\s*\d+[a-z]?\)?$", "", labn)
            labn = re.sub(r"\s+\d{1,2}(?:\.\d)?$", "", labn)  # numéro de note en fin de libellé
            # formule de calcul en fin de libellé (« CHIFFRE D'AFFAIRES (A + B + C + D) », « (somme TK à RN) »)
            labn = re.sub(r"\s*\((?=[^()]*(?:[a-z0-9] ?\+ ?[a-z0-9]|\bsomme\b|\b[a-z]{2} a [a-z]{2}\b))[^)]*\).*$", "", labn)
            if re.search(r"\b(?:t|fdr|bfg|f\.d\.r\.|b\.f\.g\.) ?\(n\)", n_) or re.search(r"\((?:t|fdr|bfg)\)\s*:?$", nrm(lab).strip()):
                continue  # bloc « contrôle » du TAFIRE (variation du FdR, du BFG, de la trésorerie : colonnes emplois / ressources)
            if len(vals) == 4 and vals[0][0] is None and vals[1][0] is not None and float(vals[1][0]).is_integer() \
                    and 0 < abs(vals[1][0]) < 100 and vals[2][0] is not None and vals[3][0] is not None:
                vals = vals[2:]  # colonne des signes (« - »), colonne des notes, puis les deux exercices
            nn_ = [v for v, _ in vals if v is not None]
            if len(nn_) >= 3 and vals[0][0] is not None and not float(vals[0][0]).is_integer() and 0 < abs(vals[0][0]) < 100 \
                    and all(abs(x) >= 1000 * abs(vals[0][0]) for x in nn_[1:]):
                vals = vals[1:]  # ratio ou renvoi (« 4.71 ») devant les montants
                nn_ = nn_[1:]
            # (nombre de colonnes de l'en-tête le plus proche : une ligne qui compte un montant de plus a une colonne de notes)
            ncol_h = len(heads[-1][1]) if heads and 0 <= i - heads[-1][0] < 160 else None
            if len(nn_) >= 2 and vals[0][0] is not None and float(vals[0][0]).is_integer() and 0 < abs(vals[0][0]) < 100 \
                    and ((all(abs(x) >= 10000 for x in nn_[1:]) and (len(nn_) >= 3 or i - note_at < 80 or ocr)) or (len(nn_) >= 3 and all(x == 0 for x in nn_[1:]))
                         or (_NOTE_DOT[0] and all(not float(x).is_integer() for x in nn_[1:3]) and (not milliards or i - note_at < 120)
                             and (ncol_h is None or len(nn_) > ncol_h))):
                vals = vals[1:]  # colonne des notes
            elif len(nn_) == 3 and len(vals) == 3 and vals[0][0] is not None and float(vals[0][0]).is_integer() and 0 < abs(vals[0][0]) < 100 \
                    and i - note_at < 120 and heads and 0 <= i - heads[-1][0] < 160 and len(heads[-1][1]) == 2 \
                    and abs(nn_[0] - nn_[1] - nn_[2]) > 0.5 and abs(nn_[1] - nn_[0] - nn_[2]) > 0.5:  # (N, N-1, variation : pas de note)
                vals = vals[1:]  # colonne des notes devant deux exercices (comptes en millions : « 21  (402)  (391) »)
            if not any(v is not None for v, _ in vals):
                if labn and not any(e_ in illegible for _, e_ in vals):
                    new_pend.append((labn, s_here))
                continue
            cands = []
            if labn:
                cands.append(labn)
                if ocr and _TOLERANT[0]:  # reconnaissance de caractères : débris courts collés au libellé (« li (total ressources stables pa »)
                    toks = labn.split(" ")
                    core = toks[:]
                    while len(core) > 2 and (len(core[0]) <= 4 or not re.search(r"[a-z]", core[0])) and \
                            not re.fullmatch(r"total|autres|dettes|titres|prets|actif|passif|frais|achats|stocks|caisse|effets", core[0]):
                        core = core[1:]
                    while len(core) > 2 and (len(core[-1]) <= 2 or not re.search(r"[a-z]", core[-1])):
                        core = core[:-1]
                    if core != toks:
                        cands.append(" ".join(core).strip(" (.-:="))
            for p_, _ in pend[-2:][::-1]:
                cands.append((p_ + " " + labn).strip())
                if not labn:
                    cands.append(p_)
            key = None
            if code_ and re.fullmatch(r"[A-Z]{2}", code_) and ocr and not labn and all(abs(v_) < 1e4 for v_, _ in vals if v_ is not None):
                code_ = None  # référence seule devant quelques petits nombres : débris de lecture, pas une ligne d'états
            if code_ and re.fullmatch(r"[A-Z]{2}", code_):
                key = REF_CODES.get(code_) or (REF_CODES_REV.get(code_) if revised else None)
                if key is None and code_ in REF_CODES_AMBIG:
                    k_rev, k_old = REF_CODES_AMBIG[code_]
                    for lab_ in cands:  # le libellé tranche entre les deux plans
                        for kk in (k_rev, k_old):
                            if kk and kk != "resultat_bilan" and next(rx for k2, _, rx in ITEM_RX if k2 == kk).search(lab_):
                                key = kk
                                break
                        if key:
                            break
                    if key is None:
                        key = k_rev if revised else k_old
                if key == "resultat_net" and s_here == S_PAS:
                    key = "resultat_bilan"
            if key is None and not labn and si > 0 and s_here == S_PAS and \
                    re.fullmatch(r"total ?(?:general ?)?(?:de l.)?actif", re.sub(r"\s+", " ", nrm(segs[si - 1][1])).strip(" :.-*•")):
                key = "total_passif"  # « TOTAL ACTIF  x  y  |  x  y » : montants sans libellé du tableau du passif
            if key is None:
                for lab_ in cands:
                    for kk, secs, rx in ITEM_RX:
                        if rx.search(lab_) and (s_here in secs or s_here is None or None in secs) and \
                                not (s_here == "hb" and hb_aff[0] and kk in ("resultat_net", "resultat_bilan")):
                            # (le résultat repris dans le projet d'affectation : sa colonne n'est pas datée, il n'est pas retenu)
                            key = kk
                            break
                    if key:
                        break
                if key is None and cands:
                    t0 = cands[0]
                    if re.fullmatch(r"total(?: general| bilan)?|total general \(?[ivx0-9 +]+\)?", t0):
                        key = {S_ACT: "total_actif~", S_PAS: "total_passif~"}.get(s_here, None if s_here in (S_CR, S_FLX) else "_total")
                if key is None:
                    if os.environ.get("CPT_DEBUG2"):
                        print("   nokey", i, s_here, cands[:3], [v for v, _ in vals], split, st_)
                    continue
            if key == "resultat_net" and s_here == S_PAS:
                key = "resultat_bilan"
            if key == "b_resultat_bilan":
                key = "resultat_bilan"
            if len(vals) == 4 and not ocr and st_ is not None and st_ < 60 and all(v_ is not None for v_, _ in vals):
                # deux tableaux côte à côte sous un même en-tête à quatre colonnes (N, N-1 | N, N-1) : un libellé de gauche n'a que les
                # deux premiers montants, les deux autres sont ceux du tableau de droite
                for l_h, hs_h in reversed(heads):
                    if not (0 <= i - l_h < 160):
                        continue
                    hs_h = sorted(hs_h)
                    ys_h = [y_ for _, _, y_ in hs_h if isinstance(y_, int)]
                    if len(ys_h) == 4 and ys_h[:2] == ys_h[2:] and all(abs(hs_h[j][0] - vals[j][1]) <= 25 for j in range(4)):
                        vals = vals[:2]
                        break
            yrs, how = _assign(vals, [] if ocr else heads, i, fy, brut_tbl and s_here == S_ACT)
            if how == "order" and not split and len(vals) > 4:
                continue  # tableau à plusieurs colonnes (par secteur, variation des capitaux propres…) : colonnes inconnues
            if how == "hdr" and not split and len([v_ for v_, _ in vals if v_ is not None]) >= 5 and len(yrs) <= 2:
                continue  # ligne d'une annexe à cinq colonnes ou plus (échéancier, ventilation) dont une colonne tombe sous une année
            if how == "var":
                order_votes.append(yrs)
            if len([v for v, _ in vals if v is not None]) == 1 and not any(v is None for v, _ in vals):
                single_hint.append(1)
            elif len(vals) >= 2:
                single_hint.append(2)
            occ.append((key, s_here, (perim or "_") + ("_ifrs" if std_cur == "ifrs" else ""), i, yrs, how, vals, unit_side[side_], unit_tag[side_]))
            if os.environ.get("CPT_DEBUG"):
                print("   occ", i, key, s_here, perim, how, yrs, [v for v, _ in vals], repr(labn[:40]), code_)
        pend = new_pend[-2:] if new_pend else ([] if segs else pend)
    # sens des colonnes sans en-tête : d'après les colonnes de variation ; sinon N puis N-1
    # sens des colonnes : années d'en-tête qui se suivent (N puis N-1, ou l'inverse), sinon colonnes de variation
    hv = [0, 0]
    for _, hs in heads:
        seq = [y for _, _, y in hs if isinstance(y, int) and fy and y in (fy, fy - 1)]
        if len(seq) >= 2 and seq[0] != seq[1]:
            hv[seq[0] == fy - 1] += 1
    if hv[0] or hv[1]:
        asc = hv[1] > hv[0]
        basis = "entete"
    else:
        asc = sum(1 for o in order_votes if o.get("asc")) > sum(1 for o in order_votes if o.get("desc"))
        basis = "variation" if order_votes else "defaut"
    guess = set()
    single = single_hint.count(1) > 2 * single_hint.count(2)
    found, alt, ranks = {}, {}, {}
    secmap = {}  # état d'où vient chaque poste retenu
    # unités par tableau : un montant prend l'unité annoncée en tête de son tableau ; un tableau sans unité annoncée prend
    # l'unité qui rend son total de bilan plausible (0,3 à 60 000 milliards de FCFA), de préférence celle du document
    norm = bool(units_seen)
    f_unk = {}
    if norm:
        u_doc = unit_of(txt)
        tots, f_stmt = {}, {}
        for key, s_here, per, i, yrs, how, vals, u_occ, _tag in occ:
            if u_occ is None and key in ("total_actif", "total_passif", "_total", "total_actif~", "total_passif~"):
                for v, _ in vals:
                    if v:
                        tots[per] = max(tots.get(per, 0), abs(v))
            elif u_occ and key in ("total_actif", "total_passif") and s_here in (S_ACT, S_PAS):
                f_stmt.setdefault(per, u_occ)  # unité du bilan de ce périmètre
        for per, f_ in f_stmt.items():
            if per not in tots:
                f_unk[per] = f_
        # unité annoncée trop grande pour les montants imprimés (« (en millions FCFA) » pré-imprimé sur un bilan bancaire en francs :
        # 455 293 722 326 millions n'existe pas) : l'unité qui rend le total du bilan plausible la remplace, pour tout le périmètre
        # l'unité retenue vaut pour tout le périmètre quand aucun total n'est plausible dans l'unité annoncée (modèle bancaire
        # pré-imprimé), sinon pour le seul tableau fautif (rapport annuel mêlant tableaux en millions et états en francs)
        tot_u = {}  # (périmètre, unité annoncée) -> {tableau: unité retenue ou None si plausible}
        for key, s_here, per, i, yrs, how, vals, u_occ, tag in occ:
            if u_occ and key in ("total_actif", "total_passif") and s_here in (S_ACT, S_PAS):
                vs = [abs(v) for v, _ in vals if v]
                if not vs:
                    continue
                fix = None
                if all(v * u_occ > 6e13 for v in vs):  # (tous les totaux de la ligne, pas seulement un montant mal découpé)
                    pl = [f for f in (1.0, 1e3, 1e6) if f < u_occ and all(3e8 <= v * f <= 6e13 for v in vs)]
                    fix = pl[-1] if pl else "?"
                tot_u.setdefault((per, u_occ), {}).setdefault(tag, fix)
        over, over_per = {}, {}
        for (per, u_), tags in tot_u.items():
            fixes = [f for f in tags.values() if f not in (None, "?")]
            if fixes and all(f not in (None,) for f in tags.values()):
                over_per[(per, u_)] = fixes[0]
            else:
                for tag, f in tags.items():
                    if f not in (None, "?"):
                        over[(per, tag)] = (u_, f)
        for per, T in tots.items():
            pl = [f for f in (1.0, 1e3, 1e6, 1e9) if 3e8 <= T * f <= 6e13]
            if f_stmt.get(per) in pl:
                f_unk[per] = f_stmt[per]
                continue
            f_unk[per] = (units_seen[0] if units_seen[0] in pl else u_doc if u_doc in pl else pl[0] if len(pl) == 1 else None)
    for key, s_here, per, i, yrs, how, vals, u_occ, tag in occ:
        if norm:
            f_u = u_occ or f_unk.get(per) or (units_seen[0] if per not in f_unk else None)
            if f_u is None:
                continue  # unité introuvable pour ce tableau : montant non retenu
            if (per, tag) in over and f_u == over[(per, tag)][0]:
                f_u = over[(per, tag)][1]
            elif (per, f_u) in over_per:
                f_u = over_per[(per, f_u)]
        else:
            f_u = 1.0
        if how in ("order", "single"):
            nums = [v for v, _ in vals if v is not None]
            if how == "single" and not single:
                continue
            if fy is None:
                continue
            if how == "single":
                yrs = {fy: nums[0]}
            else:
                pair = (vals[0][0], vals[1][0]) if len(vals) == 2 else (nums[0], nums[1])
                yrs = {fy: pair[1], fy - 1: pair[0]} if asc else {fy: pair[0], fy - 1: pair[1]}
                yrs = {y: v for y, v in yrs.items() if v is not None}
                if basis == "defaut":
                    guess.add((per, key))  # sens des colonnes supposé (ni en-tête d'années, ni colonne de variation)
        yrs = {y: v * f_u for y, v in yrs.items() if isinstance(y, int)}
        if not yrs:
            continue
        pk = per
        d = found.setdefault(pk, {})
        if key in ("total_actif", "total_passif", "_total", "total_actif~", "total_passif~"):
            alt.setdefault(pk, {}).setdefault(key, []).append(yrs)
            continue
        rank = 0 if s_here in SECS.get(key, ()) else 1
        if key not in d:
            d[key] = yrs
            ranks[(pk, key)] = rank
            secmap[(pk, key)] = s_here
        elif key == "resultat_net" and "resultat_bilan" not in d and s_here is None:
            d["resultat_bilan"] = yrs
            ranks[(pk, "resultat_bilan")] = 1
        elif rank < ranks.get((pk, key), 1):  # le poste figure dans son état : cette occurrence l'emporte
            d[key] = yrs
            ranks[(pk, key)] = rank
            secmap[(pk, key)] = s_here
        elif rank == ranks.get((pk, key), 1) and all(abs(d[key][y] - v) <= 0.5 for y, v in yrs.items() if y in d[key]) and any(y in d[key] for y in yrs):
            for y, v in yrs.items():  # même poste, mêmes montants : exercices complétés
                d[key].setdefault(y, v)
    for pk, d in found.items():  # « PERTE » (compte de résultat bancaire) : résultat négatif
        for y, v in (d.pop("perte_nette", None) or {}).items():
            if v and not (d.get("resultat_net") or {}).get(y):
                d.setdefault("resultat_net", {})[y] = -abs(v)
    for pk, a in alt.items():  # totaux : le plus grand de l'état (les sous-totaux sont plus petits)
        d = found.setdefault(pk, {})
        tots = a.get("_total", [])
        for key in ("total_actif", "total_passif"):
            ys = {}
            # libellé explicite d'abord, puis « TOTAL » de l'état pour les exercices qui manquent, puis « TOTAL » sans état connu
            # (1re occurrence = actif, 2e = passif)
            for cand in (a.get(key, []), a.get(key + "~", []), ([tots[0]] if key == "total_actif" else [tots[1]]) if len(tots) >= 2 else []):
                ys_c = {}
                for c in cand:
                    for y, v in c.items():
                        if y not in ys_c or abs(v) > abs(ys_c[y]):
                            ys_c[y] = v
                for y, v in ys_c.items():
                    ys.setdefault(y, v)
            if ys:
                d[key] = ys
    # états d'un même document dans des unités différentes (un tableau en milliers, l'autre en millions) : une identité exacte à un
    # facteur 1 000 près remet à l'échelle l'état dont le total n'est pas plausible (bilan) ou le compte de résultat face au bilan
    def plaus(v):
        return v is not None and 3e8 <= abs(v) <= 3e13

    def ratio_f(a_, b_):
        ys_ = [y for y in a_ if y in b_ and a_[y] and b_[y]]
        if not ys_:
            return None, None
        f = next((f for f in (1e3, 1e6, 1e-3, 1e-6) if abs(a_[ys_[0]] / b_[ys_[0]] / f - 1) < 0.002), None)
        return (f, ys_[0]) if f and all(abs(a_[y] / b_[y] / f - 1) < 0.002 for y in ys_) else (None, None)

    def rescale(pk, d, sec_, fac):
        for k_ in list(d):
            if secmap.get((pk, k_)) == sec_ or (k_ == "total_actif" and sec_ == S_ACT) or (k_ == "total_passif" and sec_ == S_PAS):
                d[k_] = {y: v * fac for y, v in d[k_].items()}
    for pk, d in found.items():
        f, y0 = ratio_f(d.get("total_actif") or {}, d.get("total_passif") or {})
        if f:
            ta0, tp0 = d["total_actif"][y0], d["total_passif"][y0]
            if plaus(tp0) and not plaus(ta0):
                rescale(pk, d, S_ACT, 1 / f)
            elif plaus(ta0) and not plaus(tp0):
                rescale(pk, d, S_PAS, f)
        f, y0 = ratio_f(d.get("resultat_net") or {}, d.get("resultat_bilan") or {})
        if f and secmap.get((pk, "resultat_net")) == S_CR and secmap.get((pk, "resultat_bilan")) == S_PAS:
            rn0, rb0 = abs(d["resultat_net"][y0]), abs(d["resultat_bilan"][y0])
            ok_n, ok_b = 1e6 <= rn0 <= 1e12, 1e6 <= rb0 <= 1e12  # (résultat plausible en francs)
            if ok_b and not ok_n:
                rescale(pk, d, S_CR, 1 / f)
            elif ok_n and not ok_b:
                d["resultat_bilan"] = {y: v * f for y, v in d["resultat_bilan"].items()}
    items = found.get("conso") or {}
    perims = {k: v for k, v in found.items() if v}
    for suf in ("", "_ifrs"):  # périmètre non annoncé : comptes de la société (sociaux), sauf vocabulaire des comptes consolidés
        dflt = ("conso" if conso_hint else "social") + suf
        if "_" + suf in perims:
            if dflt not in perims:
                perims[dflt] = perims.pop("_" + suf)
            else:
                for k, v in perims.pop("_" + suf).items():
                    perims[dflt].setdefault(k, v)
    # bilan de synthèse sans ligne de total des capitaux propres : la somme des composantes publiées (capital, primes, réserves,
    # report à nouveau, résultat, autres) est retenue si elle se vérifie par le passif (total - dettes financières - passif
    # circulant - trésorerie passif - écart de conversion)
    CP_PARTS = ("capital", "primes_reserves", "primes_capital", "ecart_reevaluation", "reserves", "reserves_indisponibles", "reserves_libres",
                "report_nouveau", "resultat_bilan", "autres_cp", "subventions", "provisions_reglementees")
    for it_ in perims.values():
        if "capitaux_propres" in it_ or "resultat_bilan" not in it_ or "capital" not in it_:
            continue
        for y_ in list(it_["resultat_bilan"]):
            g_ = lambda k_: (it_.get(k_) or {}).get(y_)  # noqa: E731
            pc_ = g_("passif_circulant")
            if pc_ is None and g_("fournisseurs") is not None and g_("autres_passifs_circulants") is not None:
                pc_ = g_("fournisseurs") + g_("autres_passifs_circulants")  # (bilan de synthèse : fournisseurs + autres passifs circulants)
            if g_("capital") is None or pc_ is None or any(g_(k_) is None for k_ in ("total_passif", "dettes_financieres", "tresorerie_passif")):
                continue
            cp_sum = sum(g_(k_) for k_ in CP_PARTS if g_(k_) is not None)
            cp_der = g_("total_passif") - g_("dettes_financieres") - pc_ - g_("tresorerie_passif") - (g_("ecart_conversion_passif") or 0)
            if cp_sum and abs(cp_sum - cp_der) <= max(2.0, abs(cp_der) * 0.001):
                it_.setdefault("capitaux_propres", {})[y_] = cp_sum
                if g_("passif_circulant") is None:
                    it_.setdefault("passif_circulant", {})[y_] = pc_
    # total du passif circulant illisible (scan) : somme de ses postes (DH à DN), retenue seulement si le passif se vérifie alors
    # (ressources stables + passif circulant + trésorerie passif + écart de conversion = total) — deux jeux de chiffres indépendants
    PC_PARTS = ("dettes_circulantes_hao", "clients_avances", "fournisseurs", "dettes_fiscales_sociales", "dettes_sociales", "autres_dettes",
                "provisions_risques_ct")
    for it_ in perims.values():
        if "passif_circulant" in it_ or "fournisseurs" not in it_:
            continue
        for y_ in list(it_["fournisseurs"]):
            g_ = lambda k_: (it_.get(k_) or {}).get(y_)  # noqa: E731
            parts_ = [g_(k_) for k_ in PC_PARTS if g_(k_) is not None]
            if len(parts_) < 3 or g_("total_passif") is None or g_("tresorerie_passif") is None:
                continue
            rs_ = g_("ressources_stables")
            if rs_ is None and g_("capitaux_propres") is not None and g_("dettes_financieres") is not None:
                rs_ = g_("capitaux_propres") + g_("dettes_financieres")
            if rs_ is None:
                continue
            pc_sum = sum(parts_)
            if abs(rs_ + pc_sum + g_("tresorerie_passif") + (g_("ecart_conversion_passif") or 0) - g_("total_passif")) <= max(2.0, abs(g_("total_passif")) * 0.001):
                it_.setdefault("passif_circulant", {})[y_] = pc_sum
    main = max(perims, key=lambda k: len(perims[k])) if perims else "social"
    items = perims.get(main, {})
    bank = sum(1 for k in items if k.startswith("b_")) >= 3
    unit = 1.0 if norm else unit_of(txt)  # montants déjà ramenés en FCFA par les en-têtes de tableaux
    cap = capital_stated(txt)
    cv = (items.get("capital") or items.get("b_capital") or {})
    cv = cv.get(fy) if fy in cv else (next(iter(cv.values())) if cv else None)
    if cap and cv and not norm:  # le capital du bilan, multiplié par l'unité, doit redonner le capital annoncé
        for u in (1.0, 1e3, 1e6):
            if abs(cv * u / cap - 1) < 0.005:
                unit = u
                break
    elif cap and cv and norm and abs(cv / cap - 1) >= 0.005:
        # unité annoncée en tête de tableau démentie par le capital (« montants en milliards » pour des millions) : corrigée
        for u in (1e-3, 1e-6, 1e3):
            if abs(cv * u / cap - 1) < 0.005:
                unit = u
                break
    nt = nrm(txt[:8000])
    cur = "USD" if re.search(r"(?:milliers|millions) de dollars|en (?:k|m)?usd\b|us\$|\busd ?(?:000|thousand|million)|thousands of us dollars|in thousands of usd", nt) or \
        re.search(r"(?:\ben|\(|exprim\w+ en|unite ?:?|montants? en|chiffres en) ?(?:milliers|millions) de dollars? ?(?:eu|us|americains)|(?:milliers|millions) (?:de )?\$ ?(?:eu|us)\b|(?:milliers|millions) d.us ?\$|en (?:k|m)?us ?\$", nrm(txt)) else "XOF"
    # (une simple mention en dollars dans le texte — capital d'une filiale, prix d'une matière — ne fait pas un document en dollars)
    if cur == "XOF" and re.search(r"\bunites? de compte\b|\bunits? of account\b|\bua\s+ua\b|\(en (?:k|m)?ua\)", nt):
        cur = "UA"  # unité de compte (BOAD, BIDC) : document d'un émetteur non coté
    std = "ifrs" if main.endswith("_ifrs") else "syscohada"
    KEYS_G = ("total_actif", "total_passif", "resultat_net", "chiffre_affaires", "b_pnb", "capitaux_propres", "_total")
    dfl_ = "conso" if conso_hint else "social"
    guess_p = sorted({(dfl_ if p_ == "_" else dfl_ + "_ifrs" if p_ == "__ifrs" else p_) for p_, k_ in guess if k_ in KEYS_G})
    return {"guess": guess_p, "items": items, "perims": perims, "main": main, "unit": unit, "norm": norm, "cap": cap, "fy": fy, "type": "banque" if bank else "entreprise",
            "cur": cur, "per": doc_kind(txt, title), "std": std, "revised": revised, "ocr": bool(ocr)}


def _assign(vals, heads, i, fy, brut):
    """Montants d'une ligne -> {exercice: montant}, et la règle employée."""
    nums = [(v, e) for v, e in vals if v is not None]
    if not nums:
        return {}, None
    if brut and len(vals) >= 3:
        # actif : brut, amortissements, net N, net N-1 (le net se vérifie : brut - amortissements = net)
        v = [x for x, _ in vals]
        z = [0 if x is None else x for x in v]
        if len(v) >= 4 and v[2] is not None and abs(z[0] - abs(z[1]) - z[2]) <= max(2, abs(z[0]) * 1e-6) and fy:
            return ({fy: v[2], fy - 1: v[3]} if v[3] is not None else {fy: v[2]}), "brut"
        if len(v) == 3 and v[2] is not None and abs(z[0] - abs(z[1]) - z[2]) <= max(2, abs(z[0]) * 1e-6) and fy:
            return {fy: v[2]}, "brut"
        if len(v) == 3 and None not in v and v[0] == v[1] and v[0] != 0 and fy:
            return {fy: v[1], fy - 1: v[2]}, "brut"  # colonne des amortissements vide : brut = net, puis net N-1
    recent = [h for h in heads if 0 <= i - h[0] < 160][-4:]
    out = {}
    if recent:
        # l'en-tête retenu est celui dont les colonnes s'alignent le mieux sur tous les montants de la ligne
        # (plusieurs tableaux se suivent avec des mises en page différentes)
        best_h = None
        cand_h = list(reversed(recent))
        for (l1, h1), (l2, h2) in zip(recent, recent[1:]):
            # en-tête réparti sur deux lignes voisines (« 31 Décembre 2025 » au-dessus de « 2024 ») : colonnes réunies
            if l2 - l1 == 1 and not any(abs(a[0] - b[0]) <= 3 for a in h1 for b in h2):
                cand_h.append((-1, sorted(h1 + h2)))  # (-1 : retenu seulement si toutes les colonnes s'alignent)
        for rk, (l_h, hs) in enumerate(cand_h):
            # montants alignés à droite sous des années centrées : affectation dans l'ordre des colonnes, sur la fenêtre
            # de colonnes d'en-tête la plus proche (tableaux côte à côte : les colonnes de l'autre tableau sont ignorées)
            hs_s = sorted(hs)
            k_ = len(nums)
            if 1 <= k_ <= len(hs_s):
                win = None
                for st_w in range(len(hs_s) - k_ + 1):
                    ds = [abs(hs_s[st_w + j][0] - nums[j][1]) for j in range(k_)]
                    if max(ds) <= 25 and (win is None or sum(ds) < win[0]):
                        win = (sum(ds), st_w)
                if win:
                    got = {}
                    for j in range(k_):
                        yr = hs_s[win[1] + j][2]
                        if isinstance(yr, tuple):
                            yr = fy + yr[1] if fy else None
                        if yr is not None and yr not in got:
                            got[yr] = nums[j][0]
                    if got and len(got) == k_:
                        # colonnes bien alignées (écart moyen ≤ 6) : l'en-tête le plus proche au-dessus l'emporte (l'en-tête d'un
                        # tableau précédent, aux colonnes voisines, ne doit pas dater les lignes du tableau suivant)
                        sc = (k_ + 0.5, win[0] / k_ <= 6, -rk, -win[0] / k_)
                        if best_h is None or sc > best_h[0]:
                            best_h = (sc, got)
                        continue
            if l_h == -1:
                continue
            if len(hs) == 1 and len(nums) >= 2:
                continue  # une seule année (titre daté) ne peut pas servir d'en-tête à une ligne de plusieurs montants
            got, dist, dk = {}, [], {}
            for vi_, (v, xe) in enumerate(nums):
                bb = None
                for he, hs_, yr in hs:
                    d = min(abs(he - xe), abs((he + hs_) / 2 - (xe - len(str(abs(int(v)))) * 0.66)))
                    if d <= 12 and (bb is None or d < bb[0]):
                        bb = (d, yr)
                if bb:
                    yr = bb[1]
                    if isinstance(yr, tuple):
                        if not fy:
                            continue
                        yr = fy + yr[1]
                    if yr not in got:
                        got[yr] = v
                        dist.append(bb[0])
                        dk[yr] = (bb[0], len(dist) - 1, vi_)
                    elif bb[0] < dk[yr][0] and vi_ == dk[yr][2] + 1 and float(got[yr]).is_integer() and 0 < abs(got[yr]) < 100 and abs(v) >= 100:
                        got[yr] = v  # renvoi de note juste à gauche du montant : la colonne revient au montant le plus proche
                        dist[dk[yr][1]] = bb[0]
                        dk[yr] = (bb[0], dk[yr][1], vi_)
            if got:
                sc = (len(got), True, -rk, -sum(dist) / len(dist))  # à nombre égal de colonnes, l'en-tête le plus proche au-dessus
                if best_h is None or sc > best_h[0]:
                    best_h = (sc, got)
        out = best_h[1] if best_h else {}
        if out:
            if fy and not any(y in (fy, fy - 1) for y in out):
                return {}, None
            return out, "hdr"
    if len(nums) >= 3:
        a, b, c = nums[0][0], nums[1][0], nums[2][0]
        if abs(a - b - c) <= max(2, abs(a) * 1e-5) and abs(c) > 0:
            return {"desc": 1}, "var"
        if abs(b - a - c) <= max(2, abs(b) * 1e-5) and abs(c) > 0:
            return {"asc": 1}, "var"
    if len(nums) == 2 or (len(nums) >= 2 and len(vals) >= 2):
        return {}, "order"
    if len(nums) == 1 and len(vals) == 2:
        return {}, "order"  # deux colonnes dont une case vide (« - », montant illisible) : le montant garde sa colonne
    if len(nums) == 1 and len(vals) == 1:
        return {}, "single"
    return {}, None


# ---------------------------------------------------------------- contrôle : identités comptables
ACT_PARTS = ("charges_immobilisees", "immo_incorp", "immo_corp", "immo_fin", "actif_circulant_hao", "stocks", "creances", "tresorerie_actif")
STRONG = ("actif = passif", "résultat CR = bilan", "RN = RAO + HAO - impôt", "RN = résultat avant impôt - impôt", "RN = RE + RF + HAO - impôt", "RN = RAO - impôt")


def _gran(*xs):
    """Granularité des montants (1, 10, … 1e6) : des comptes publiés en milliers ou en millions de francs, ramenés en francs,
    s'équilibrent à une ou deux unités de leur arrondi près."""
    g = 1e6
    for x in xs:
        if x is None:
            continue
        while g > 1 and abs(round(x / g) * g - x) > 1e-6:
            g /= 10
    return g


def checks(items, year, bank=False, strict=False):
    """Identités vérifiées pour un exercice : liste de (nom, écart relatif). strict : égalités exactes exigées (reconnaissance de
    caractères : un chiffre changé au milieu d'un total ne doit pas passer pour une vérification)."""
    g = lambda k: (items.get(k) or {}).get(year)  # noqa: E731
    res = []

    def rel(a, b):
        if a is None or b is None:
            return None
        den = max(abs(a), abs(b), 1.0)
        r = abs(a - b) / den
        # égalités exactes dans les comptes publiés : en reconnaissance de caractères, un écart au-delà de l'arrondi (deux unités),
        # même infime (« 2 112 605 834 » face à « 2 112 605 831 »), est un chiffre mal lu et non une vérification (les couches
        # texte gardent la tolérance : des comptes provisoires publiés avec un léger déséquilibre existent)
        if strict and r <= 0.002 and abs(a - b) > 2 * _gran(a, b):
            r = 0.0021
        return r
    for nm, a, b in (("actif = passif", g("total_actif"), g("total_passif")), ("résultat CR = bilan", g("resultat_net"), g("resultat_bilan"))):
        r = rel(a, b)
        if r is not None:
            res.append((nm, r))
    if g("valeur_ajoutee") is not None and g("charges_personnel") is not None and g("ebe") is not None:
        res.append(("EBE = VA - personnel", rel(g("valeur_ajoutee") - abs(g("charges_personnel")), g("ebe"))))
    imp = abs(g("impots_resultat") or 0) + abs(g("participation") or 0)
    # résultat net du compte de résultat, ou à défaut celui du bilan (compte de résultat coupé avant sa dernière ligne)
    rn_ = g("resultat_net") if g("resultat_net") is not None else g("resultat_bilan")
    if g("rao") is not None and g("rhao") is not None and rn_ is not None:
        res.append(("RN = RAO + HAO - impôt", rel(g("rao") + g("rhao") - imp, rn_)))
    elif g("resultat_exploitation") is not None and g("resultat_financier") is not None and g("rhao") is not None and rn_ is not None:
        res.append(("RN = RE + RF + HAO - impôt", rel(g("resultat_exploitation") + g("resultat_financier") + g("rhao") - imp, rn_)))
    if g("rao") is not None and g("rhao") is None and g("impots_resultat") is not None and rn_ is not None:
        r_ = rel(g("rao") - imp, rn_)  # comptes sans éléments hors activités ordinaires (IFRS) : retenue si elle se vérifie
        if r_ is not None and r_ <= 0.001:
            res.append(("RN = RAO - impôt", r_))
    if g("rao") is not None and g("resultat_exploitation") is not None and g("resultat_financier") is not None:
        res.append(("RAO = RE + RF", rel(g("resultat_exploitation") + g("resultat_financier"), g("rao"))))
    if g("resultat_avant_impot") is not None and g("impots_resultat") is not None and rn_ is not None:
        # (quote-part des sociétés mises en équivalence après le résultat avant impôt ; impôt positif : charge imprimée
        # sans signe, ou produit d'impôt)
        rai_, it_, mee_ = g("resultat_avant_impot"), g("impots_resultat"), g("quote_part_mee") or 0
        c_ = [rel(rai_ + m_ - abs(it_), rn_) for m_ in {0, mee_}]
        if it_ > 0:
            c_ += [rel(rai_ + m_ + it_, rn_) for m_ in {0, mee_}]
        res.append(("RN = résultat avant impôt - impôt", min(c_)))
    # sommes des postes du bilan : retenues seulement quand elles se vérifient (elles confirment alors chaque poste lu)
    for nm, tot, parts, need in (("actif = somme des postes", "total_actif", ACT_PARTS, ("immo_corp", "tresorerie_actif")),
                                 ("actif = somme des masses", "total_actif", ("actif_immobilise", "actif_circulant", "tresorerie_actif"), ("actif_immobilise", "actif_circulant", "tresorerie_actif")),
                                 ("passif = somme des masses", "total_passif", ("capitaux_propres", "dettes_financieres", "passif_circulant", "tresorerie_passif"), ("capitaux_propres", "dettes_financieres", "passif_circulant", "tresorerie_passif")),
                                 ("passif = ressources stables + dettes", "total_passif", ("ressources_stables", "passif_circulant", "tresorerie_passif"), ("ressources_stables", "passif_circulant", "tresorerie_passif"))):
        if g(tot) is not None and all(g(k) is not None for k in need):
            r_ = rel(sum(g(k) or 0 for k in parts), g(tot))
            if r_ is not None and r_ <= 0.0005:
                res.append((nm, r_))
    if g("b_pnb") is not None and g("b_charges_generales") is not None and g("b_rbe") is not None:
        res.append(("RBE ≤ PNB", 0.0 if abs(g("b_rbe")) <= abs(g("b_pnb")) else 1.0))
    if g("capitaux_propres") is not None and g("total_passif") is not None and g("capitaux_propres") > 0:
        # (des capitaux propres négatifs peuvent dépasser le total du bilan en valeur absolue)
        res.append(("capitaux propres ≤ total", 0.0 if g("capitaux_propres") <= abs(g("total_passif")) * 1.0001 else 1.0))
    if g("chiffre_affaires") is not None and g("ventes_marchandises") is not None and g("ventes_produits") is not None and g("travaux_services") is not None:
        s_ = g("ventes_marchandises") + g("ventes_produits") + g("travaux_services") + (g("produits_accessoires") or 0)
        r_ = rel(s_, g("chiffre_affaires"))
        if r_ is not None and r_ <= 0.001:  # retenue seulement si elle se vérifie (le chiffre d'affaires publié n'inclut pas toujours tout)
            res.append(("CA = somme des ventes", r_))
    # tableau des flux : variation de trésorerie = flux opérationnels + flux d'investissement + flux de financement
    if all(g(k) is not None for k in ("flux_operationnels", "flux_investissement", "flux_financement", "variation_tresorerie")):
        res.append(("variation = somme des flux", rel(g("flux_operationnels") + g("flux_investissement") + g("flux_financement"), g("variation_tresorerie"))))
    return res


# état que chaque identité, vérifiée, confirme (B : bilan, R : compte de résultat) ; « résultat CR = bilan » rapproche deux lectures
# du seul résultat net et ne confirme aucun état entier
ID_SEC = {"actif = passif": "B", "actif = somme des postes": "B", "actif = somme des masses": "B", "passif = somme des masses": "B",
          "passif = ressources stables + dettes": "B", "capitaux propres ≤ total": "B", "RN = RAO + HAO - impôt": "R",
          "RN = RE + RF + HAO - impôt": "R", "RN = résultat avant impôt - impôt": "R", "RN = RAO - impôt": "R", "RAO = RE + RF": "R",
          "EBE = VA - personnel": "R", "CA = somme des ventes": "R", "RBE ≤ PNB": "R", "variation = somme des flux": "F"}
CONFIRMS = {n for n in ID_SEC if n not in ("capitaux propres ≤ total", "RBE ≤ PNB")}


def _sec_of(k):
    s_ = SECS.get(k, ())
    return "B" if (S_ACT in s_ or S_PAS in s_) else "R" if S_CR in s_ else "F" if S_FLX in s_ else None


def partial(items, year, c, strict=False):
    """Exercice dont une identité forte se vérifie mais une autre échoue : seuls sont gardés les états entièrement confirmés (une
    identité vérifiée, aucune fausse) et les postes des identités vérifiées ; tout doit alors se vérifier de nouveau.
    (postes gardés, contrôles) ou None."""
    fk = dict(IDENT_KEYS, **{"capitaux propres ≤ total": ("capitaux_propres",), "RBE ≤ PNB": ("b_rbe",)})
    ok_n = [n for n, r in c if r is not None and r <= 0.001]
    if not any(n in STRONG for n in ok_n):
        return None
    ok_keys = {k for n in ok_n if n in CONFIRMS or n in STRONG for k in fk.get(n, ())}
    ok_sec = {ID_SEC[n] for n in ok_n if n in CONFIRMS}
    bad_sec = {ID_SEC[n] for n, r in c if r is not None and r > 0.01 and ID_SEC.get(n)}
    keep = {k for k in items if k in ok_keys or (_sec_of(k) in ok_sec and _sec_of(k) not in bad_sec)}
    c2 = checks({k: items[k] for k in keep}, year, strict=strict)
    strong2 = [r for n, r in c2 if n in STRONG and r is not None]
    if strong2 and min(strong2) <= 0.001 and all(r <= 0.01 for _, r in c2 if r is not None):
        return keep, c2
    return None


def validate(parsed, year, items=None):
    """Exercice retenu si au moins une identité forte se vérifie à 0,1 % et qu'aucune ne s'écarte de plus de 1 %."""
    c = checks(items if items is not None else parsed["items"], year, parsed.get("type") == "banque", strict=bool(parsed.get("ocr")))
    strong = [r for n, r in c if n in STRONG]
    # (le tableau des flux est jugé à part : son identité fausse ne discrédite pas le bilan ni le compte de résultat, elle écarte les flux)
    ok = bool(strong) and min(strong) <= 0.001 and all(r <= 0.01 for n, r in c if n != "variation = somme des flux")
    return ok, c


# ---------------------------------------------------------------- consolidation des documents
CHARGES = {"charges_personnel", "dotations", "frais_financiers", "impots_resultat", "participation", "capex_corp", "capex_incorp",
           "dividendes_verses", "b_interets_charges", "b_commissions_charges", "b_charges_generales"}


def unit_choice(P, items, y):
    """Unité des montants : annoncée ou déduite du capital, si l'ordre de grandeur du total du bilan la confirme ;
    sinon la seule unité plausible (total du bilan entre 0,3 et 60 000 milliards de FCFA). None si plusieurs restent possibles."""
    fxk = P.get("fxk") or 1.0  # (montants en dollars : ordre de grandeur en FCFA)
    tot = (items.get("total_actif") or {}).get(y) or (items.get("total_passif") or {}).get(y)
    ca = (items.get("chiffre_affaires") or items.get("b_pnb") or {}).get(y)
    tot, ca = tot and tot * fxk, ca and ca * fxk
    allv = [abs(v[y]) * fxk for k, v in items.items() if y in v]
    bs_v = [abs(v[y]) * fxk for k, v in items.items() if y in v and k not in ("total_actif", "total_passif")
            and set(SECS.get(k, ())) & {S_ACT, S_PAS}]
    ta_, tp_ = (items.get("total_actif") or {}).get(y), (items.get("total_passif") or {}).get(y)
    if tot and bs_v and abs(tot) < max(bs_v) * 0.9 and not (ta_ and tp_ and abs(ta_ - tp_) <= 0.5):
        tot = None  # total plus petit qu'un poste du bilan : mal lu (sauf total égal à l'actif et au passif : c'est le poste qui est faux)
    # (le plus grand bilan de la cote dépasse à peine 15 000 milliards de FCFA, le plus grand chiffre d'affaires 2 000 milliards)
    scales = (1.0, 1e3, 1e6, 1e9) + ((1e-3, 1e-6) if P.get("unit") and P["unit"] < 1 else ())  # (unité annoncée trop grande)
    if tot:
        cands = [u for u in scales if 3e8 <= abs(tot) * u <= 3e13]
    elif ca:
        cands = [u for u in scales if 5e7 <= abs(ca) * u <= 5e12]
    else:
        cands = []
    if allv:  # aucun montant au-delà de 100 000 milliards de FCFA
        cands = [u for u in cands if max(allv) * u <= 1e14]
    if P.get("unit") in cands:
        return P["unit"], cands
    # petite société (bilan de moins de 300 millions de FCFA) : l'unité annoncée par le document l'emporte (montants en milliers
    # annoncés « KFCFA » d'une société en sommeil, par exemple)
    if P.get("unit") and tot and 1e7 <= abs(tot) * P["unit"] < 3e8 and max(allv or [0]) * P["unit"] <= 1e14:
        return P["unit"], [P["unit"]]
    if len(cands) == 1:
        return cands[0], cands
    return None, cands


# libellés des postes (base historique)
LABELS = {
    "charges_immobilisees": "Charges immobilisées", "immo_incorp": "Immobilisations incorporelles", "immo_corp": "Immobilisations corporelles",
    "immo_fin": "Immobilisations financières", "actif_immobilise": "Actif immobilisé", "actif_circulant_hao": "Actif circulant HAO", "stocks": "Stocks",
    "creances": "Créances et emplois assimilés", "clients": "Clients", "actif_circulant": "Actif circulant", "tresorerie_actif": "Trésorerie actif",
    "total_actif": "Total actif", "capital": "Capital", "primes_reserves": "Primes et réserves", "reserves": "Réserves", "report_nouveau": "Report à nouveau",
    "resultat_bilan": "Résultat de l'exercice (bilan)", "capitaux_propres": "Capitaux propres", "cp_groupe": "Capitaux propres part du groupe",
    "interets_minoritaires": "Intérêts minoritaires", "dettes_financieres": "Dettes financières", "ressources_stables": "Ressources stables",
    "primes_capital": "Primes liées au capital", "ecart_reevaluation": "Écarts de réévaluation", "reserves_indisponibles": "Réserves indisponibles",
    "reserves_libres": "Réserves libres", "autres_cp": "Autres capitaux propres", "subventions": "Subventions d'investissement",
    "provisions_reglementees": "Provisions réglementées", "ecart_conversion_passif": "Écart de conversion passif",
    "autres_passifs_circulants": "Autres passifs circulants",
    "passif_circulant": "Passif circulant", "fournisseurs": "Fournisseurs", "tresorerie_passif": "Trésorerie passif", "total_passif": "Total passif",
    "actif_non_courant": "Actifs non courants", "actif_courant": "Actifs courants", "passif_non_courant": "Passifs non courants",
    "passif_courant": "Passifs courants", "ventes_marchandises": "Ventes de marchandises", "marge_commerciale": "Marge commerciale",
    "ventes_produits": "Ventes de produits fabriqués", "travaux_services": "Travaux, services vendus", "produits_accessoires": "Produits accessoires",
    "chiffre_affaires": "Chiffre d'affaires", "valeur_ajoutee": "Valeur ajoutée", "charges_personnel": "Charges de personnel",
    "ebe": "Excédent brut d'exploitation", "dotations": "Dotations aux amortissements et provisions", "resultat_exploitation": "Résultat d'exploitation",
    "revenus_financiers": "Revenus financiers", "frais_financiers": "Frais financiers", "resultat_financier": "Résultat financier",
    "rao": "Résultat des activités ordinaires", "rhao": "Résultat hors activités ordinaires", "participation": "Participation des travailleurs",
    "impots_resultat": "Impôts sur le résultat", "quote_part_mee": "Quote-part des sociétés mises en équivalence",
    "resultat_avant_impot": "Résultat avant impôt", "resultat_net": "Résultat net", "resultat_net_pg": "Résultat net part du groupe",
    "cafg": "Capacité d'autofinancement globale", "flux_operationnels": "Flux des activités opérationnelles",
    "capex_incorp": "Acquisitions d'immobilisations incorporelles", "capex_corp": "Acquisitions d'immobilisations corporelles",
    "flux_investissement": "Flux des activités d'investissement", "dividendes_verses": "Dividendes versés",
    "flux_financement": "Flux des activités de financement", "variation_tresorerie": "Variation de la trésorerie",
    "tresorerie_fin": "Trésorerie nette à la clôture", "b_caisse": "Caisse, banque centrale", "b_creances_interbancaires": "Créances interbancaires",
    "b_creances_clientele": "Créances sur la clientèle", "b_effets_publics": "Effets publics", "b_titres_placement": "Titres de placement",
    "b_dettes_interbancaires": "Dettes interbancaires", "b_dettes_clientele": "Dettes envers la clientèle", "b_capital": "Capital",
    "b_interets_produits": "Intérêts et produits assimilés", "b_interets_charges": "Intérêts et charges assimilées",
    "b_commissions_produits": "Commissions (produits)", "b_commissions_charges": "Commissions (charges)", "b_pnb": "Produit net bancaire",
    "b_charges_generales": "Charges générales d'exploitation", "b_rbe": "Résultat brut d'exploitation", "b_cout_risque": "Coût du risque"}

# postes qui varient peu d'un exercice à l'autre (contrôle des chiffres tronqués par la reconnaissance de caractères)
STABLE = {"chiffre_affaires", "ventes_marchandises", "ventes_produits", "valeur_ajoutee", "charges_personnel", "total_actif", "total_passif",
          "immo_corp", "immo_incorp", "stocks", "creances", "clients", "fournisseurs", "actif_circulant", "passif_circulant", "actif_immobilise",
          "capital", "b_pnb", "b_interets_produits", "b_interets_charges", "b_creances_clientele", "b_dettes_clientele", "b_charges_generales"}

# lectures par reconnaissance de caractères : français et anglais, page lue comme un bloc (fra, eng) ou ligne par ligne
# (fra4, eng4 : mode « colonne de texte » de tesseract, qui garde mieux les lignes des tableaux numérisés)
OCR_SRC = ("fra", "eng", "fra4", "eng4")


# société cotée dans sa forme actuelle depuis un exercice donné : comptes antérieurs d'entités distinctes, jamais montrés comme les
# siens (NEI-CEDA : NEI et CEDA publient chacune leurs comptes jusqu'en 2010 ; la société fusionnée, capital porté de 134 à
# 255 millions, publie ses premiers comptes pour l'exercice 2011)
FIRST_FY = {"NEIC": 2011}
USD_REPORTERS = {"ETIT"}  # Ecobank Transnational : états financiers en dollars américains
# ETI publie ses états en dollars ; depuis l'exercice 2024 (et dans ses chiffres clés), chaque montant est suivi de sa contre-valeur
# en FCFA calculée par la société (« milliers $EU | millions FCFA » pour N puis N-1). Les états entièrement à deux monnaies sont lus
# dans leurs colonnes FCFA (chiffres officiels de la société) ; les autres sont lus en dollars, puis convertis à la consolidation au
# cours USD/FCFA du jour de leur publication (montants figés à cette date).
DUAL_LINE = re.compile(r"(?:\$ ?eu|dollars?\b|us ?\$|\busd\b).{0,90}(?:fcfa|f ?cfa|francs? cfa)", re.I)
DUAL_STMT = re.compile(r"montants? en milliers de dollars? (?:eu|us)\w* et (?:en )?millions de (?:francs? )?cfa")
USD_STMT = re.compile(r"montants? en milliers de dollars? (?:eu|us)\w*(?: americains)? sauf")
_NUMCELL = re.compile(r"\(?-?\d[\d ,.]*\)?|-|—")


def dual_cols(txt, keep):
    """Lignes à deux monnaies d'ETI (« 2,097,113   1,219,618   1,849,700   1,123,045 [variations %] ») : ne garde que les colonnes
    FCFA (keep="fcfa" : 2e et 4e montants) ou dollars (keep="usd" : 1er et 3e). Les en-têtes de colonnes deviennent l'unité unique."""
    out = []
    for l in txt.split("\n"):
        nl = nrm(l)
        if DUAL_LINE.search(nl) and not re.search(r"\d{3}", re.sub(r"\b(?:19|20)\d\d\b", "", nl)):
            ind = re.match(r"\s*", l).group(0)
            out.append(ind + ("(Montants en millions de FCFA)" if keep == "fcfa" else "(Montants en milliers de dollars EU)"))
            continue
        cells = re.split(r"\s{2,}", l.strip())
        nums = [i for i, c in enumerate(cells) if _NUMCELL.fullmatch(c.strip())]
        pct = [i for i, c in enumerate(cells) if c.strip().endswith("%")]
        if len(nums) == 4 and nums[0] > 0 and all(i > nums[-1] for i in pct):
            k = (nums[1], nums[3]) if keep == "fcfa" else (nums[0], nums[2])
            ind = re.match(r"\s*", l).group(0)
            out.append(ind + "   ".join(c for i, c in enumerate(cells) if i < nums[0]) + "        " + "        ".join(cells[i] for i in k))
            continue
        out.append(l)
    return "\n".join(out)


def read_doc(texts, meta):
    """Lecture d'un document (texte, et OCR français / anglais le cas échéant) : exercices vérifiés, montants dans l'unité
    du document (unit = 1, 1e3 ou 1e6 FCFA ; None si l'ordre de grandeur reste à confirmer par une autre source)."""
    fy_hint = meta.get("fy")
    title = meta.get("ti") or ""
    best = None
    parsed = {}
    allres = {}  # exercices vérifiés par lecture (src → {périmètre: {année: (contrôles, postes gardés)}})
    scores = {}
    variants = []
    oc0 = other_company(meta["t"], (meta.get("u") or "").rsplit("/", 1)[-1]) if meta.get("t") else None
    usd_rep = (meta.get("t") if oc0 in (None, "?") else oc0) in USD_REPORTERS
    dual_src = set()
    for src, (txt, ocr) in texts.items():
        if not txt or len(txt.strip()) < 200:
            continue
        if usd_rep:
            nt_ = nrm(txt)
            if DUAL_STMT.search(nt_) and not USD_STMT.search(nt_):
                txt = dual_cols(txt, "fcfa")  # états à deux monnaies : contre-valeur FCFA publiée par la société
                dual_src.update((src, src + "~", src + "!"))
            elif DUAL_LINE.search(nt_):
                txt = dual_cols(txt, "usd")  # chiffres clés à deux monnaies dans un document en dollars : colonnes en dollars
        variants.append((src, txt, ocr, False))
        if ocr:
            variants.append((src + "~", txt, ocr, True))  # (libellés nettoyés de leurs débris : seconde lecture du même texte)
        # virgule ambiguë (« 63,615 » : 63 615 millions ou 63,615 milliards ?) : seconde lecture où la virgule sépare les milliers,
        # la lecture retenue étant celle dont les exercices se vérifient le mieux (dans l'unité annoncée)
        if len(re.findall(r"(?<![\d,.])\d{1,3},\d{3}(?![\d,])", txt)) >= 5:
            variants.append((src + "!", txt, ocr, "comma"))
    for src, txt, ocr, tol in variants:
        _TOLERANT[0] = tol is True
        _COMMA_FORCE[0] = tol == "comma"
        try:
            P = parse(txt, fy_hint=fy_hint, title=title, ocr=ocr)
        except Exception:  # noqa: BLE001
            continue
        finally:
            _TOLERANT[0] = False
            _COMMA_FORCE[0] = False
        if src in dual_src:
            P["cur"], P["dual"] = "XOF", True
        elif usd_rep and P["cur"] == "USD":
            P["fxk"] = 600.0  # (ordre de grandeur du cours, pour la vraisemblance des unités seulement)
        parsed[src] = P
        res = {}
        for per, items in P["perims"].items():
            yrs = sorted({y for v in items.values() for y in v}, reverse=True)
            for y in yrs[:2]:
                ok, c = validate(P, y, items)
                if ok:
                    res.setdefault(per, {})[y] = ([(n, round(r, 5)) for n, r in c], None)
                else:
                    pr = partial(items, y, c, strict=bool(P.get("ocr")))  # une identité vérifiée, une autre fausse : seul ce qui reste sûr est gardé
                    if pr:
                        res.setdefault(per, {})[y] = ([(n, round(r, 5)) for n, r in pr[1]], pr[0])
        # lecture retenue : la plus riche en exercices vérifiés, puis en identités fortes, en postes vérifiés et en postes gardés
        score = len(P["items"]) * 0.01
        for per, yrs_ in res.items():
            items = P["perims"][per]
            for y, (c, keep) in yrs_.items():
                vk_ = {k for n, r in c if r is not None and r <= 0.001 for k in IDENT_KEYS.get(n, ())}
                have = [k for k, v in items.items() if y in v and (keep is None or k in keep)]
                score += 100 + 5 * sum(1 for n, r in c if n in STRONG and r is not None and r <= 0.001) + 3 * len([k for k in have if k in vk_]) + len(have)
                # (à qualité égale, la lecture dont les montants sont plausibles dans l'unité annoncée par le document l'emporte :
                # « 63,615 » lu 63 615 millions plutôt que 63,615 milliards dans un document « en millions »)
                if P.get("unit"):
                    u_, cands_ = unit_choice(P, items, y)
                    if u_ == P["unit"]:
                        score += 20
                    elif cands_ and P["unit"] not in cands_:
                        score -= 20
        allres[src], scores[src] = res, score
        if best is None or score > best[0]:
            best = (score, src, P, res)
    if not best:
        return {"st": "illisible"}
    _, src, P, res = best

    def _rec(Pc, srcc, resc, per, y):
        """Montants retenus d'un exercice vérifié d'une lecture : pour l'OCR, un montant n'est gardé que si une autre lecture
        (autre langue, autre mode) donne le même chiffre, ou s'il entre dans une identité comptable vérifiée."""
        chk, keep = resc[per][y]
        items = Pc["perims"][per]
        basec = srcc.rstrip("~!")
        others = [P_ for s_, P_ in parsed.items() if s_.rstrip("~!") != basec and s_.rstrip("~!") in OCR_SRC]
        ok_id = {k for n, r in chk if r <= 0.001 for k in IDENT_KEYS.get(n, ())}
        rec = {}
        cf = []  # montants lus à l'identique par deux reconnaissances de caractères (hors identités)
        for k, v in items.items():
            if y not in v or (keep is not None and k not in keep):
                continue
            x = v[y]
            if basec in OCR_SRC:
                ovs = [((o_["perims"].get(per) or {}).get(k) or {}).get(y) for o_ in others]
                same = any(ov is not None and abs(ov - x) <= 0.5 for ov in ovs)
                if k in ok_id:
                    # montant vérifié par une identité, mais lu autrement (à moins d'un centième près : un chiffre confondu, 3 pour 9)
                    # par une autre reconnaissance sans qu'aucune ne le confirme : le même chiffre mal lu deux fois (compte de
                    # résultat et bilan) vérifie une identité à tort ; le montant est contesté et n'est pas repris
                    if not same and any(ov is not None and 0.5 < abs(ov - x) <= 0.01 * max(abs(x), 1.0) for ov in ovs):
                        continue
                elif not same:
                    continue
                else:
                    cf.append(k)
                    # chiffres tronqués par la lecture (les deux lectures butent sur la même image) : un poste habituellement stable
                    # vingt fois plus petit que l'autre exercice du même document n'est pas gardé
                    oy = [v_ for y_, v_ in v.items() if y_ != y and v_]
                    if k in STABLE and x and oy and abs(oy[0]) >= 1e6 and abs(x / oy[0]) < 0.05:
                        continue
            rec[k] = abs(x) if k in CHARGES else x
        if any(n == "variation = somme des flux" and r > 0.01 for n, r in chk):
            rec = {k: v for k, v in rec.items() if _sec_of(k) != "F"}  # tableau des flux incohérent : ses montants ne sont pas repris
        unit, cands = unit_choice(Pc, items if keep is None else {k: v for k, v in items.items() if k in keep}, y)
        return rec, chk, keep, ok_id, cf, unit, cands
    base_src = src.rstrip("~!")  # (« fra~ » : même texte que « fra », libellés nettoyés)
    out = {"st": "ok" if res else "non vérifié", "src": base_src, "fy": P["fy"], "per": P["per"], "std": P["std"], "type": P["type"],
           "cur": P["cur"], "main": P["main"], "n": len(P["items"]), "y": {}, "guess": P.get("guess") or []}
    oc_ = other_company(meta["t"], (meta.get("u") or "").rsplit("/", 1)[-1]) if meta.get("t") else None
    t_eff = meta.get("t") if oc_ in (None, "?") else oc_  # (document déposé sous une autre société : voir other_company)
    if t_eff in USD_REPORTERS and P["cur"] == "XOF" and not P.get("dual"):
        # (ni dollars annoncés ni colonnes FCFA de la société : comptes en FCFA d'une filiale, ou tableaux mal lus) : pas repris
        out["st"], out["cur"] = "devise USD", "USD"
        return out
    if P["cur"] == "USD" and t_eff in USD_REPORTERS:
        out["cur"] = "USD"  # converti à la consolidation, au cours du jour de publication
    elif P["cur"] != "XOF":
        out["st"], out["cur"] = "devise " + P["cur"], P["cur"]
        return out
    def _emit(per, y, rec, chk, keep, ok_id, cf, unit, cands, mg=(), alt=None):
        d = {"v": rec, "c": chk, "u": unit, "uc": cands, "vk": sorted(k for k in ok_id if k in rec)}
        if cf:
            d["cf"] = sorted(k for k in cf if k in rec)
        if keep is not None:
            d["part"] = 1  # états partiellement retenus (une identité fausse a écarté un état)
        if mg:
            d["mg"] = sorted(mg)  # postes complétés par une autre lecture du même document (identité vérifiée dans celle-ci)
        if alt:
            d["alt"] = alt  # exercice pris dans une autre lecture du même document (vérifié dans celle-ci seulement)
        out["y"].setdefault(per, {})[str(y)] = d

    for per, yrs in res.items():
        for y in yrs:
            rec, chk, keep, ok_id, cf, unit, cands = _rec(P, src, res, per, y)
            # complément : postes vérifiés par une identité comptable dans une autre lecture du même document (même norme,
            # même unité), lecture cohérente avec celle retenue (au moins un montant commun identique) ; rien n'est remplacé
            mg = []
            for s_, res_ in allres.items():
                if s_ == src or per not in res_ or y not in res_[per]:
                    continue
                P_ = parsed[s_]
                if P_["std"] != P["std"] or P_["fy"] != P["fy"]:
                    continue
                chk_, keep_ = res_[per][y]
                items_ = P_["perims"][per]
                unit_, cands_ = unit_choice(P_, items_ if keep_ is None else {k: v for k, v in items_.items() if k in keep_}, y)
                # (unité non trouvée par cette lecture, la ligne qui l'annonce mal reconnue, mais compatible avec celle retenue :
                # même document, montants communs identiques ci-dessous)
                if unit_ != unit and not (unit_ is None and unit is not None and unit in (cands_ or ())):
                    continue
                relax = unit_ != unit
                vals_ = {k: v[y] for k, v in items_.items() if y in v and (keep_ is None or k in keep_)}
                common = [k for k in rec if k in vals_]
                if not common or not any(abs(abs(vals_[k]) - abs(rec[k])) <= 0.5 for k in common):
                    continue
                if any(n == "variation = somme des flux" and r > 0.01 for n, r in chk_):
                    vals_ = {k: v for k, v in vals_.items() if _sec_of(k) != "F"}
                base_ = s_.rstrip("~!")
                others_ = [P__ for s__, P__ in parsed.items() if s__.rstrip("~!") != base_ and s__.rstrip("~!") in OCR_SRC]
                def _contested(k):
                    # même prudence que pour la lecture retenue : un montant vérifié par une identité mais lu autrement (un
                    # chiffre confondu, 5 pour 6) par une autre reconnaissance, sans qu'aucune ne le confirme, est contesté
                    # (le même chiffre mal lu deux fois, total de l'actif et total du passif, vérifie l'identité à tort)
                    x = vals_.get(k)
                    if x is None:
                        return False
                    ovs = [((o_["perims"].get(per) or {}).get(k) or {}).get(y) for o_ in others_]
                    return not any(ov is not None and abs(ov - x) <= 0.5 for ov in ovs) and \
                        any(ov is not None and 0.5 < abs(ov - x) <= 0.01 * max(abs(x), 1.0) for ov in ovs)
                # (complément permis par l'unité compatible : une identité dont un montant est contesté ne confirme aucun des siens)
                bad_ = {k for n, r in chk_ if r <= 0.001 and relax and base_ in OCR_SRC and any(_contested(k_) for k_ in IDENT_KEYS.get(n, ()))
                        for k in IDENT_KEYS.get(n, ())}
                for k in sorted(k for n, r in chk_ if r <= 0.001 for k in IDENT_KEYS.get(n, ())):
                    if k in rec or k not in vals_ or k in bad_:
                        continue
                    rec[k] = abs(vals_[k]) if k in CHARGES else vals_[k]
                    ok_id.add(k)
                    mg.append(k)
                # et montants de cette lecture lus à l'identique par une autre reconnaissance de caractères (règle « cf »)
                for k in sorted(vals_):
                    if k in rec:
                        continue
                    x = vals_[k]
                    ovs = [((o_["perims"].get(per) or {}).get(k) or {}).get(y) for o_ in others_]
                    if not any(ov is not None and abs(ov - x) <= 0.5 for ov in ovs):
                        continue
                    oy = [v_ for y_, v_ in items_[k].items() if y_ != y and v_]
                    if k in STABLE and x and oy and abs(oy[0]) >= 1e6 and abs(x / oy[0]) < 0.05:
                        continue
                    rec[k] = abs(x) if k in CHARGES else x
                    cf.append(k)
                    mg.append(k)
            _emit(per, y, rec, chk, keep, ok_id, cf, unit, cands, mg)
    # exercices vérifiés dans une autre lecture seulement (même norme, même exercice de référence, année N ou N-1) :
    # repris avec les mêmes règles de prudence, depuis la lecture la mieux notée qui les vérifie
    for s_ in sorted(allres, key=lambda s: -scores[s]):
        if s_ == src:
            continue
        P_ = parsed[s_]
        if P_["std"] != P["std"] or P_["fy"] != P["fy"] or not isinstance(P["fy"], int):
            continue
        for per, yrs in allres[s_].items():
            for y in yrs:
                if str(y) in out["y"].get(per, {}) or y not in (P["fy"], P["fy"] - 1):
                    continue
                rec, chk, keep, ok_id, cf, unit, cands = _rec(P_, s_, allres[s_], per, y)
                if rec:
                    _emit(per, y, rec, chk, keep, ok_id, cf, unit, cands, alt=s_.rstrip("~!"))
    _complete(out, texts, P)
    return out


CA_PARTS = ("ventes_marchandises", "ventes_produits", "travaux_services")
CALC_KEYS = {"chiffre_affaires_calc": "chiffre_affaires", "b_pnb_calc": "b_pnb"}  # poste calculé -> poste publié (voir _complete)
_CA_RX = {k: rx for k, _, rx in ITEM_RX if k in CA_PARTS}


def _empty_lines(t_):
    """Parties du chiffre d'affaires imprimées sans montant (cases vides : la société n'a pas ce type de ventes) : le libellé
    termine sa ligne et n'apparaît nulle part ailleurs avec un montant."""
    txt = t_[0]
    if not txt:
        return set()
    seen, num = set(), set()
    lines = txt.splitlines()
    for li, ln in enumerate(lines):
        segs = [s for s in re.split(r"\s{2,}", ln.strip()) if s]
        for i, s in enumerate(segs):
            lab = re.sub(r"^[a-z]{2}\s+", "", re.sub(r"^[\d\s.,()-]+(?=[a-z])", "", nrm(s)).strip(" .:-"))
            for k, rx in _CA_RX.items():
                if rx.match(lab):
                    nxt = next((x for x in lines[li + 1:li + 3] if x.strip()), "")
                    # (montants renvoyés à la ligne suivante : pas une case vide)
                    if i == len(segs) - 1 and not re.match(r"^\s*(?:[A-Z]{1,2}\d?\s+)?[-(]?\d[\d\s.,()-]*$", nxt):
                        seen.add(k)
                    else:
                        num.add(k)
    return seen - num


def _complete(out, texts, P):
    """Postes calculés d'après le document lui-même, pour les exercices vérifiés seulement (rien n'est estimé) ; ils sont
    listés dans « calc » de l'exercice :
    - chiffre d'affaires SYSCOHADA = ventes de marchandises + ventes de produits fabriqués + travaux, services vendus
      (+ produits accessoires), quand la ligne du total n'est pas imprimée ou pas lue mais que ses parties le sont ;
    - banques, ancien plan comptable bancaire (comptes de résultat sans ligne « produit net bancaire ») : produit net bancaire
      d'après le compte de résultat entier vérifié (comptes_banques.py), années lues dans l'en-tête du tableau et confirmées
      par le résultat de l'exercice lu au bilan (même montant, même échelle) ; le résultat de l'exercice manquant ou lu à
      zéro au bilan est alors repris du compte de résultat."""
    if out.get("st") != "ok" or out.get("std") != "syscohada":
        return
    empty = None
    for per, yrs in out["y"].items():
        for y, d in yrs.items():
            v = d["v"]
            if out.get("type") == "banque" or v.get("chiffre_affaires") is not None or v.get("b_pnb") is not None \
                    or not any(v.get(k) is not None for k in CA_PARTS):
                continue
            miss = [k for k in CA_PARTS if v.get(k) is None]
            if miss:
                if empty is None:
                    empty = _empty_lines(texts.get(out.get("src")) or (None,))
                if not all(k in empty for k in miss):
                    continue
            v["chiffre_affaires_calc"] = sum(v.get(k) or 0 for k in CA_PARTS) + (v.get("produits_accessoires") or 0)
            d.setdefault("calc", []).append("chiffre_affaires")
    if out.get("type") != "banque" or not any(d["v"].get("b_pnb") is None for yrs in out["y"].values() for d in yrs.values()):
        return
    # (produit net bancaire et chiffre d'affaires calculés gardés sous une clé à part, « …_calc » : ils ne participent à aucun
    # contrôle entre documents ni avec la base de référence, et la consolidation ne s'en sert que pour un exercice où le
    # montant publié manque — voir CALC_KEYS)
    import comptes_banques as CB
    order = [out.get("src")] + [s for s in ("txt",) + OCR_SRC if s != out.get("src")]
    for src in order:
        txt = (texts.get(src) or (None,))[0]
        if not txt:
            continue
        try:
            res, _ = CB.pnb(txt)
        except Exception:  # noqa: BLE001
            res = None
        if not res or not all(x.get("y") for x in res.values()):
            continue
        # échelle des montants lus (francs, milliers, millions) d'après le résultat de l'exercice lu au bilan du même document
        applied = False
        for per, yrs in out["y"].items():
            ks = set()
            bad = False
            for x in res.values():
                d = yrs.get(str(x["y"]))
                if not d or not x["rn"]:
                    continue
                rv = next((d["v"][k] for k in ("resultat_net", "resultat_bilan", "b_resultat_bilan") if d["v"].get(k)), None)
                if rv is None:
                    continue
                k_ = next((k for k in (1.0, 1e3, 1e6, 1e-3, 1e-6) if abs(rv - x["rn"] * k) <= max(2 * k, abs(rv) * 2e-5)), None)
                if k_ is None:
                    bad = True  # (résultat du bilan différent de celui du compte : années ou colonnes en cause, rien n'est repris)
                else:
                    ks.add(k_)
            if bad or len(ks) != 1:
                continue
            k_ = ks.pop()
            applied = True
            for x in res.values():
                d = yrs.get(str(x["y"]))
                if not d:
                    continue
                v = d["v"]
                if v.get("b_pnb") is None:
                    v["b_pnb_calc"] = x["pnb"] * k_
                    d.setdefault("calc", []).append("b_pnb")
                if x["rn"] and not v.get("resultat_net") and not v.get("resultat_bilan") and not v.get("b_resultat_bilan"):
                    v["resultat_net"] = x["rn"] * k_
                    d.setdefault("calc", []).append("resultat_net")
                    d["vk"] = sorted(set(d["vk"]) | {"resultat_net"})
        if applied:
            return


IDENT_KEYS = {"actif = passif": ("total_actif", "total_passif"), "résultat CR = bilan": ("resultat_net", "resultat_bilan"),
              "RN = RAO + HAO - impôt": ("rao", "rhao", "impots_resultat", "participation", "resultat_net", "resultat_bilan"),
              "RN = RE + RF + HAO - impôt": ("resultat_exploitation", "resultat_financier", "rhao", "impots_resultat", "participation", "resultat_net", "resultat_bilan"),
              "RN = résultat avant impôt - impôt": ("resultat_avant_impot", "impots_resultat", "resultat_net", "resultat_bilan"),
              "RN = RAO - impôt": ("rao", "impots_resultat", "participation", "resultat_net", "resultat_bilan"),
              "actif = somme des postes": ("total_actif",) + ACT_PARTS,
              "actif = somme des masses": ("total_actif", "actif_immobilise", "actif_circulant", "tresorerie_actif"),
              "passif = somme des masses": ("total_passif", "capitaux_propres", "dettes_financieres", "passif_circulant", "tresorerie_passif"),
              "passif = ressources stables + dettes": ("total_passif", "ressources_stables", "passif_circulant", "tresorerie_passif"),
              "EBE = VA - personnel": ("valeur_ajoutee", "charges_personnel", "ebe"), "RAO = RE + RF": ("rao", "resultat_exploitation", "resultat_financier"),
              "CA = somme des ventes": ("chiffre_affaires", "ventes_marchandises", "ventes_produits", "travaux_services", "produits_accessoires"),
              "variation = somme des flux": ("flux_operationnels", "flux_investissement", "flux_financement", "variation_tresorerie")}


# sommes de postes vérifiées entre documents à la consolidation (parties, total)
SOFT_SUMS = ((("ventes_marchandises", "ventes_produits", "travaux_services", "produits_accessoires"), "chiffre_affaires"),
             (("charges_immobilisees", "immo_incorp", "immo_corp", "immo_fin"), "actif_immobilise"),
             (("actif_circulant_hao", "stocks", "creances"), "actif_circulant"),
             (("actif_immobilise", "actif_circulant", "tresorerie_actif"), "total_actif"),
             (("capitaux_propres", "dettes_financieres"), "ressources_stables"),
             (("ressources_stables", "passif_circulant", "tresorerie_passif"), "total_passif"),
             (("flux_operationnels", "flux_investissement", "flux_financement"), "variation_tresorerie"))


# ---------------------------------------------------------------- consolidation : un jeu de comptes par société et par exercice
# catégories de publications qui contiennent des états financiers (les autres sont lues mais ne servent pas aux comptes)
CAT_STATEMENTS = {"financial_statements", "financial_results", "auditor_report", "annual_report", "company_report", "activity_report",
                  "communique", "resolution_project", "ag_meeting"}
# documents d'une autre entité classés sous le titre : PH-CI (sous Palm CI), SDA CI (sous Bolloré Transport & Logistics CI),
# SARI CI (sous CFAO Motors CI)
OTHER_ENTITY = {"PALC": r"\bph ?ci\b|\bphci\b", "SDSC": r"\bsda\b", "CFAC": r"\bsari\b"}
# nom distinctif de chaque société dans les intitulés de fichiers : un document dont le nom désigne une autre société cotée
# (erreur de classement de la liste) n'est pas rattaché au titre
NAME_TOKENS = {"ABJC": r"servair", "BNBC": r"bernabe", "BICC": r"\bbici", "CABC": r"sicable", "CFAC": r"cfao", "CIEC": r"\bcie\b|\bcie ci\b",
               "FTSC": r"filtisac", "NEIC": r"\bnei\b|nei.ceda", "NSBC": r"nsia", "NTLC": r"nestle", "ONTBF": r"onatel", "ORAC": r"orange",
               "ORGT": r"oragroup", "PALC": r"palm.?ci|\bpalm\b", "PRSC": r"tractafric|peyrissac", "SAFC": r"alios|safca", "SCRC": r"sucrivoire",
               "SDCC": r"sode.?ci|sodeci", "SDSC": r"bollore|africa global|\bagl\b", "SEMC": r"\bsiem\b|crown.?siem", "SGBC": r"\bsgb|societe generale|\bsgci\b",
               "SHEC": r"vivo", "SIBC": r"\bsib\b|\bsib ci\b", "SICC": r"sicor", "SIVC": r"air liquide", "SLBC": r"solibra", "SMBC": r"\bsmb\b",
               "SNTS": r"sonatel", "SOGC": r"\bsogb\b", "SPHC": r"\bsaph\b", "STAC": r"setao", "STBC": r"sitab", "UNLC": r"unilever",
               "UNXC": r"uniwax", "ECOC": r"ecobank ci|ecobank cote", "ETIT": r"ecobank tg|ecobank trans|ecobank togo|\beti\b|\beti tg\b", "CBIBF": r"coris", "LNBB": r"\blnb\b|loterie",
               "BICB": r"\bbiic\b", "BOAB": r"boa bn|boa benin|africa bn|africa benin", "BOABF": r"boa bf|boa burkina|africa bf|africa burkina",
               "BOAC": r"boa ci|boa cote|africa ci|boaci", "BOAM": r"boa ml|boa mali|africa ml|africa mali", "BOAN": r"boa ng|boa niger|africa ng|africa niger",
               "BOAS": r"boa sn|boa senegal|africa sn|africa senegal", "TTLC": r"total ci|total cote|totalenergies marketing ci|totalenergies marketing cote",
               "TTLS": r"total sn|total senegal|totalenergies marketing sn|totalenergies marketing senegal"}


# émetteurs non cotés (obligations) dont des documents sont déposés sous la page d'une société cotée : jamais repris
NON_LISTED = r"\bbidc\b|\bebid\b|\bboad\b|\bbceao\b|\bbhci\b|\bcrrh\b|\bfagace\b|\bshelter afrique\b"


def other_company(t, name):
    """Le nom de fichier désigne-t-il clairement une autre société cotée que t ? Renvoie ce titre (None sinon, ou "?" si
    plusieurs sociétés sont nommées ou si le document est celui d'un émetteur non coté)."""
    n_ = nrm(name).replace("_", " ").replace("-", " ")
    if re.search(NON_LISTED, n_):
        return "?"
    own = NAME_TOKENS.get(t)
    if own and re.search(own, n_):
        return None
    hits = [t2 for t2, rx in NAME_TOKENS.items() if t2 != t and re.search(rx, n_)]
    return hits[0] if len(hits) == 1 else ("?" if hits else None)
def doc_company(t, title, fname):
    """Société d'un document de la liste des publications : l'intitulé fait foi, puis le nom du fichier si l'intitulé ne nomme
    aucune société cotée (document déposé sous la page d'une autre société ; « BOA NG » dans l'intitulé l'emporte sur un fichier
    mal nommé « boa_bn »). Renvoie t si rien ne désigne clairement une autre société."""
    o = other_company(t, title or "")
    if o is None:
        n_ = nrm(title or "").replace("_", " ").replace("-", " ")
        if any(re.search(rx, n_) for rx in NAME_TOKENS.values()):
            return t
        o = other_company(t, fname or "")
    return o if o and o != "?" else t


def _doc_rank(r, y):
    """Préférence entre documents pour un exercice : comptes de l'exercice lui-même (plutôt que la colonne N-1 du suivant),
    définitifs (certifiés, approuvés) plutôt que provisoires, puis le plus récent (un document qui « annule et remplace »)."""
    ti = nrm(r.get("ti") or "")
    own = 1 if r.get("fy") == y else 0
    final = 0 if re.search(r"provisoire|non audite|efp\b|_efp_|- efp -", ti) else 1
    if re.search(r"certifi|approuv|audite|definiti|efa\b|_efa_|- efa -|annule et remplace", ti):
        final = 2
    # rapports (annuels, d'activité), communiqués, résolutions, procès-verbaux : des états y figurent parfois, mais les états
    # financiers publiés comme tels restent préférés à rang égal
    if r.get("cat") not in (None, "financial_statements", "auditor_report") and final == 1 and \
            re.search(r"rapport|communique|resolution|proces.?verbal|assemblee|presentation|activite", ti):
        final = 0.5
    return (own, final, r.get("d") or "")


CA_LIKE = {"chiffre_affaires", "ventes_marchandises", "ventes_produits", "travaux_services", "produits_accessoires", "marge_commerciale",
           "valeur_ajoutee", "achats_marchandises", "achats_matieres", "b_interets_produits", "b_interets_charges", "b_pnb"}


def subtotals(v):
    """Soldes intermédiaires SYSCOHADA manquants, calculés exactement à partir des postes publiés du même exercice, chacun
    seulement s'il est confirmé par un autre total publié (à 0,5 % près) : [(poste, montant)]. Montants en millions de FCFA."""
    g = lambda k: v.get(k)  # noqa: E731
    near = lambda a, b: a is not None and b is not None and abs(a - b) <= max(0.5, abs(b) * 0.005)  # noqa: E731
    out = []
    imp = abs(g("impots_resultat") or 0) + abs(g("participation") or 0)
    rn_ok = lambda rao: g("rhao") is not None and g("impots_resultat") is not None and g("resultat_net") is not None and \
        near(rao + g("rhao") - imp, g("resultat_net"))  # noqa: E731
    re_, rf_, rao_ = g("resultat_exploitation"), g("resultat_financier"), g("rao")
    if rao_ is None and re_ is not None and rf_ is not None and rn_ok(re_ + rf_):
        out.append(("rao", re_ + rf_))
    if rf_ is None and rao_ is not None and re_ is not None and rn_ok(rao_):
        out.append(("resultat_financier", rao_ - re_))
    if re_ is None and rao_ is not None and rf_ is not None and rn_ok(rao_):
        out.append(("resultat_exploitation", rao_ - rf_))
    # EBE et valeur ajoutée : confirmés par le résultat d'exploitation (EBE − dotations nettes = RE) quand il est publié
    va_, pe_, ebe_, dot_ = g("valeur_ajoutee"), g("charges_personnel"), g("ebe"), g("dotations")
    if ebe_ is None and va_ is not None and pe_ is not None and dot_ is not None and re_ is not None and near(va_ - abs(pe_) - abs(dot_), re_):
        out.append(("ebe", va_ - abs(pe_)))
    if va_ is None and ebe_ is not None and pe_ is not None and dot_ is not None and re_ is not None and near(ebe_ - abs(dot_), re_):
        out.append(("valeur_ajoutee", ebe_ + abs(pe_)))
    # capitaux propres : ressources stables − dettes financières, confirmés par le total du passif
    rs_, df_, cp_ = g("ressources_stables"), g("dettes_financieres"), g("capitaux_propres")
    tp_, pc_, trp_ = g("total_passif") or g("total_actif"), g("passif_circulant"), g("tresorerie_passif")
    def cp_ok(c):
        return tp_ is not None and pc_ is not None and trp_ is not None and df_ is not None and \
            near(c + df_ + pc_ + trp_ + (g("ecart_conversion_passif") or 0), tp_)
    if cp_ is None and rs_ is not None and df_ is not None and cp_ok(rs_ - df_):
        out.append(("capitaux_propres", rs_ - df_))
    return out


def consolidate(cj, mirror=None, fx=None):
    """comptes.json (documents lus) -> {titre: {"y": {exercice: {"v": {poste: millions de FCFA}, "n", "d", "own"}}, "per", "std",
    "agree" (part des montants communs égaux à ceux de la base de référence), "ncmp" (nombre de montants comparés)}}.

    Consolidation poste par poste quand plusieurs documents couvrent un même exercice (comptes de l'exercice, colonne N-1 des
    comptes suivants, versions provisoire et définitive, texte ou reconnaissance de caractères) :
      1. un montant qui entre dans une identité vérifiée de son document l'emporte sur un montant non vérifié ;
      2. puis un montant lu dans la couche texte l'emporte sur une reconnaissance de caractères ;
      3. puis le montant donné par le plus de sources concordantes (documents ; la base de référence ne compte que si elle
         reprend des comptes de même rang : jamais des chiffres provisoires contre des comptes définitifs) ;
      4. puis celui du document le plus probant (comptes de l'exercice, définitifs, le plus récent).
    Un montant décalé d'un facteur 1 000 (ou 1 000 000) par rapport à une autre source est une erreur d'unité : écarté.
    Les états par secteur d'activité ne sont pas des comptes de la société : ignorés.

    Société qui publie en dollars (ETI) : contre-valeur FCFA publiée par la société quand elle existe (seule retenue pour l'exercice),
    sinon états en dollars convertis au cours USD/FCFA du jour de leur publication (fx : date « AAAA-MM-JJ » -> FCFA pour 1 USD).
    Seuls ses états financiers consolidés sont repris (rapports annuels et communiqués mêlent comptes de la holding, trimestres
    et semestres) ; la base de référence, convertie à d'autres cours, ne sert pas de recoupement pour elle."""
    recs = []
    if fx:
        mirror = {t_: v_ for t_, v_ in (mirror or {}).items() if t_ not in USD_REPORTERS}
    for u, r in (cj.get("docs") or {}).items():
        if not r.get("y") or r.get("per") != "annuel" or not r.get("t"):
            continue
        rate = None
        if r["t"] in USD_REPORTERS:
            ti_ = nrm(r.get("ti") or "")
            if not re.search(r"etats? financiers", ti_) or re.search(r"rapport annuel|communique|trimestr|semestr|septembre|partie 1", ti_):
                continue
            if r.get("cur", "XOF") == "USD":
                rate = fx(r.get("d")) if fx and r.get("d") else None
                if not rate:
                    continue
        if r.get("cur", "XOF") != "XOF" and not rate:
            continue
        if re.search(r"par secteur|sectoriel|segment|par activite|par pays", nrm((r.get("ti") or "") + " " + u)):
            continue
        # notations, avis et calendriers : résumés ou chiffres arrondis, jamais des états financiers -> pas de consolidation
        if r.get("cat") and r["cat"] not in CAT_STATEMENTS:
            continue
        t_doc = r["t"]
        oc_ = other_company(t_doc, u.rsplit("/", 1)[-1])
        if oc_ == "?":
            continue  # (plusieurs sociétés nommées : document ambigu)
        if oc_:
            t_doc = oc_  # (document d'une autre société cotée rattaché par erreur à ce titre : rendu à la sienne)
        # comptes d'une autre société publiés sous le même titre (filiale, société absorbée) : écartés
        if t_doc in OTHER_ENTITY and re.search(OTHER_ENTITY[t_doc], nrm((r.get("ti") or "") + " " + u.rsplit("/", 1)[-1].replace("_", " "))):
            continue
        # présentations (diapositives) : chiffres arrondis ou mis en forme, colonnes et années mal repérables -> jamais retenues
        if re.search(r"presentation|slides?\b|webinar|roadshow|investor.?day|conference.?(?:des )?analystes", nrm((r.get("ti") or "") + " " + u)):
            continue
        for per, ys in r["y"].items():
            ys = {y: x for y, x in ys.items() if int(y) >= FIRST_FY.get(t_doc, 0)}
            if t_doc in USD_REPORTERS:
                if per not in ("conso", "conso_ifrs"):
                    continue  # (comptes de la holding ou d'une filiale)
                per = "conso_ifrs"  # (ETI ne publie ses comptes de groupe qu'en IFRS)
            for y, x in ys.items():
                v_, vk_ = dict(x.get("v") or {}), set(x.get("vk") or [])
                if v_.get("resultat_net") is None and v_.get("resultat_bilan") is not None:
                    # (bilan seul : le résultat de l'exercice inscrit au passif est le résultat net publié, même montant)
                    v_["resultat_net"] = v_["resultat_bilan"]
                    if "resultat_bilan" in vk_:
                        vk_.add("resultat_net")
                recs.append({"t": t_doc, "y": int(y), "per": per, "std": "ifrs" if per.endswith("_ifrs") else "syscohada", "u": x.get("u"),
                             "uc": x.get("uc") or [], "v": v_, "vk": vk_, "c": x.get("c"), "doc": u,
                             "rank": _doc_rank(r, int(y)), "d": r.get("d"), "ocr": r.get("src") in OCR_SRC, "fy": r.get("fy"),
                             # (communiqué ou rapport numérisé : deux lectures identiques d'un chiffre ne garantissent pas sa ligne ni sa
                             # colonne ; seuls les montants vérifiés par une identité sont gardés)
                             "guess": per in (r.get("guess") or []), "cf": set(x.get("cf") or []) if r.get("cat") in (None, "financial_statements", "auditor_report") else set(),
                             "strong": len({c_[0] for c_ in (x.get("c") or []) if c_[0] in STRONG and c_[1] is not None and c_[1] <= 0.001}),
                             "fx": rate})
    # exercice dont la société publie elle-même la contre-valeur FCFA : les conversions de ses états en dollars sont écartées
    off_ = {(x["t"], x["y"], x["per"]) for x in recs if not x["fx"]}
    recs = [x for x in recs if not x["fx"] or (x["t"], x["y"], x["per"]) not in off_]
    known = {}
    for x in recs:
        if x["u"]:
            for k in ("total_actif", "resultat_net", "chiffre_affaires", "b_pnb", "capitaux_propres"):
                if x["v"].get(k):
                    known.setdefault((x["t"], x["y"], x["per"], x["std"], k), []).append(x["v"][k] * x["u"] * (x["fx"] or 1.0))
    MS = {"total_actif": "total_bilan", "resultat_net": "resultat_net", "chiffre_affaires": "ca", "b_pnb": "ca", "capitaux_propres": "capitaux_propres"}
    for x in recs:
        if x["u"]:
            continue
        # (sans total ni chiffre d'affaires, aucune unité candidate : les unités usuelles sont essayées, retenues seulement si un
        # chiffre clé coïncide avec une autre source à cette échelle)
        no_key = not any(x["v"].get(k) for k in ("total_actif", "total_passif", "chiffre_affaires", "b_pnb"))
        for cand in x["uc"] or ([1.0, 1e3, 1e6] if no_key else []):
            hit = 0
            for k, mk in MS.items():
                v = x["v"].get(k)
                if not v:
                    continue
                for kv in known.get((x["t"], x["y"], x["per"], x["std"], k), []):
                    if abs(v * cand * (x["fx"] or 1.0) - kv) <= abs(kv) * 0.002:
                        hit += 1
                mv = (((mirror or {}).get(x["t"]) or {}).get(mk) or {}).get(str(x["y"]))
                if mv and abs(v * cand / 1e6 - mv) <= abs(mv) * 0.01 + 0.5:
                    hit += 1
            if hit:
                x["u"] = cand
                break
    # unité encore indécise (montants en francs ou en milliers ?) : la taille connue de la société la tranche quand une seule des
    # unités possibles la redonne à moins d'un facteur 10 et que l'autre s'en écarte d'au moins 100 fois de plus
    import math
    import statistics
    scale = {}
    for x in recs:
        if x["u"]:
            for k in ("total_actif", "chiffre_affaires", "b_pnb"):
                if x["v"].get(k) and x["v"][k] > 0:
                    scale.setdefault((x["t"], k), []).append(math.log10(x["v"][k] * x["u"] * (x["fx"] or 1.0) / 1e6))
    for t_, ser_ in (mirror or {}).items():
        for k, mk in (("total_actif", "total_bilan"), ("chiffre_affaires", "ca"), ("b_pnb", "ca")):
            for y_, mv in (ser_.get(mk) or {}).items():
                if mv and mv > 0:
                    scale.setdefault((t_, k), []).append(math.log10(mv))
    for x in recs:
        if x["u"] or len(x["uc"]) < 2:
            continue
        dist = {}
        for cand in x["uc"]:
            ds = [abs(math.log10(x["v"][k] * cand * (x["fx"] or 1.0) / 1e6) - statistics.median(scale[(x["t"], k)]))
                  for k in ("total_actif", "chiffre_affaires", "b_pnb") if x["v"].get(k) and x["v"][k] > 0 and scale.get((x["t"], k))]
            if ds:
                dist[cand] = max(ds)
        if len(dist) >= 2:
            o_ = sorted(dist, key=dist.get)
            if dist[o_[0]] <= 1.0 and dist[o_[1]] - dist[o_[0]] >= 2.0:
                x["u"] = o_[0]
    # unité encore inconnue : (1) celle des autres exercices du même document (une seule unité par document) ; (2) sinon la taille
    # de la société les exercices voisins (moins de 4 ans d'écart), quand une seule unité la redonne à moins d'un facteur 3 et que
    # les autres s'en écartent d'au moins 30 fois plus (les unités possibles diffèrent d'un facteur 1 000)
    u_doc = {}
    for x in recs:
        if x["u"]:
            u_doc.setdefault((x["doc"], x["per"]), set()).add(x["u"])
    near = {}
    for x in recs:
        if x["u"]:
            for k in ("total_actif", "chiffre_affaires", "b_pnb"):
                if x["v"].get(k) and x["v"][k] > 0:
                    near.setdefault((x["t"], k), []).append((x["y"], math.log10(x["v"][k] * x["u"] * (x["fx"] or 1.0) / 1e6)))
    for t_, ser_ in (mirror or {}).items():
        for k, mk in (("total_actif", "total_bilan"), ("chiffre_affaires", "ca"), ("b_pnb", "ca")):
            for y_, mv in (ser_.get(mk) or {}).items():
                if mv and mv > 0 and str(y_).isdigit():
                    near.setdefault((t_, k), []).append((int(y_), math.log10(mv)))
    have_ty = {(x["t"], x["y"]) for x in recs if x["u"]}
    for x in recs:
        if x["u"] or (x["t"], x["y"]) in have_ty:
            continue  # (seulement pour un exercice qui n'a encore aucun compte d'unité connue, quel que soit le référentiel)
        sib = u_doc.get((x["doc"], x["per"]))
        key_ = any(x["v"].get(k) for k in ("total_actif", "total_passif", "chiffre_affaires", "b_pnb"))  # (un chiffre clé, recoupable ensuite)
        if key_ and sib and len(sib) == 1 and (not x["uc"] or next(iter(sib)) in x["uc"]):
            x["u"], x["u_how"] = next(iter(sib)), "document"
            continue
        dist = {}
        for cand in (x["uc"] or [1.0, 1e3, 1e6]):
            ds = []
            for k in ("total_actif", "chiffre_affaires", "b_pnb"):
                v = x["v"].get(k)
                refs = [lv for yy, lv in near.get((x["t"], k), []) if 0 < abs(yy - x["y"]) <= 3]
                if v and v > 0 and refs:
                    ds.append(abs(math.log10(v * cand * (x["fx"] or 1.0) / 1e6) - statistics.median(refs)))
            if ds:
                dist[cand] = max(ds)
        if len(dist) >= 2:
            o_ = sorted(dist, key=dist.get)
            if dist[o_[0]] <= 0.5 and dist[o_[1]] - dist[o_[0]] >= 1.5:
                x["u"], x["u_how"] = o_[0], "voisins"
    recs = [x for x in recs if x["u"]]
    for x in recs:
        x["m"] = {k: round(v * x["u"] * (x["fx"] or 1.0) / 1e6, 3) for k, v in x["v"].items()}
    MK = {"chiffre_affaires": "ca", "b_pnb": "ca", "resultat_net": "resultat_net", "resultat_bilan": "resultat_net", "total_actif": "total_bilan",
          "total_passif": "total_bilan", "capitaux_propres": "capitaux_propres", "resultat_exploitation": "ebit", "ebe": "ebitda"}

    def mirror_v(t, y, k):
        mk = MK.get(k)
        return (((mirror or {}).get(t) or {}).get(mk) or {}).get(str(y)) if mk else None

    def drop_docs(rs, bad_):
        # un jeu d'états dont une partie est fausse (unité, années, ordre de grandeur) n'est plus cru pour rien : tous ses exercices
        # sont écartés (un document qui publie des états SYSCOHADA et IFRS compte pour deux jeux)
        return [x for x in rs if (x["doc"], x["per"]) not in bad_]
    # reconnaissance de caractères vérifiée par une seule identité (souvent « actif = passif ») : seuls les montants de cette identité,
    # ceux lus à l'identique par deux reconnaissances (français, anglais), ou ceux qu'un autre document (ou la base de référence)
    # donne à l'identique, sont gardés
    idx0 = {}
    for x in recs:
        idx0.setdefault((x["t"], x["y"]), []).append(x)
    dels = []
    for x in recs:
        if not x["ocr"] or x["strong"] >= 2:
            continue
        for k, v in x["m"].items():
            if k in x["vk"] or k in x["cf"] or v is None:
                continue
            mv = mirror_v(x["t"], x["y"], k)
            if any(o["doc"] != x["doc"] and o["m"].get(k) is not None and abs(o["m"][k] - v) <= max(0.5, abs(v) * 0.001) for o in idx0[(x["t"], x["y"])]) \
                    or (mv is not None and abs(v - mv) <= max(0.5, abs(mv) * 0.005)):
                continue
            dels.append((x, k))
    for x, k in dels:
        x["m"].pop(k, None)
    recs = [x for x in recs if x["m"]]
    # erreurs d'unité : un poste qui vaut exactement 1 000 fois (ou un millième) la valeur d'une autre source est écarté
    pool = {}
    for x in recs:
        tot_ = x["m"].get("total_actif") or x["m"].get("total_passif")
        for k, v in x["m"].items():
            if v and not (tot_ and abs(v) > abs(tot_) * 20):  # (un montant qui dépasse vingt fois le bilan de son document ne juge personne)
                pool.setdefault((x["t"], x["y"], k), []).append(v)

    def scaled(v, o):
        return any(abs(abs(v / o) - f) <= f * 0.005 for f in (1e3, 1e-3, 1e6, 1e-6))
    bad = set()
    for x in recs:
        # tout l'exercice dans une autre unité que les autres sources (identités vérifiées quelle que soit l'unité) : écarté
        # (seulement face à une valeur confirmée par deux autres sources)
        n_sc = n_eq = 0
        for k in ("total_actif", "total_passif", "resultat_net", "chiffre_affaires", "b_pnb", "capitaux_propres", "rao", "ebe"):
            v = x["m"].get(k)
            os_ = list(pool.get((x["t"], x["y"], k), [])) + ([mirror_v(x["t"], x["y"], k)] if mirror_v(x["t"], x["y"], k) else [])
            if v in os_:
                os_.remove(v)  # (sa propre valeur)
            if not v or not os_:
                continue
            if any(abs(v - o) <= max(0.5, abs(o) * 0.005) for o in os_):
                n_eq += 1
            elif any(scaled(v, o) and sum(1 for o2 in os_ if abs(o2 - o) <= max(0.5, abs(o) * 0.005)) >= 2 for o in os_):
                n_sc += 1
        if n_sc >= 2 and n_eq == 0:
            bad.add((x["doc"], x["per"]))
    recs = drop_docs(recs, bad)
    # ordre de grandeur de la société : un exercice dont le total du bilan (ou le chiffre d'affaires) s'écarte de plus de 300 fois
    # de la médiane de ses autres exercices est une erreur d'unité (milliers annoncés pour des montants en francs, ou l'inverse)
    import math
    import statistics
    by_t_ = {}
    for x in recs:
        by_t_.setdefault(x["t"], []).append(x)
    for t_, xs in by_t_.items():
        for k_ in ("total_actif", "chiffre_affaires", "b_pnb"):
            # (la médiane se calcule sur les documents encore crus : ceux déjà écartés sur le total du bilan ne pèsent plus sur le
            # chiffre d'affaires — deux rapports en milliers pouvaient sinon faire passer les bons documents pour des erreurs)
            xs_ok = [x for x in xs if (x["doc"], x["per"]) not in bad]
            lv = sorted(math.log10(abs(x["m"][k_])) for x in xs_ok if x["m"].get(k_))
            if len(lv) >= 3:
                med = lv[len(lv) // 2]
                bad |= {(x["doc"], x["per"]) for x in xs_ok if x["m"].get(k_) and abs(math.log10(abs(x["m"][k_])) - med) > 2.5}
    recs = drop_docs(recs, bad)
    pool = {}  # (sources encore crues seulement : montant et total du bilan de son document)
    for x in recs:
        tot_ = x["m"].get("total_actif") or x["m"].get("total_passif")
        for k, v in x["m"].items():
            if v:
                pool.setdefault((x["t"], x["y"], k), []).append((v, tot_))

    def outsized(k_, v_, tot_):
        # un montant hors de proportion avec le bilan de son propre document (cinq fois le total ; vingt fois pour les ventes)
        # porte seul l'erreur d'unité : il ne discrédite pas la source qui le donne mille fois plus petit
        return bool(tot_) and abs(v_) > abs(tot_) * (20 if k_ in CA_LIKE else 5)
    for x in recs:
        n_del = 0
        tot_x = x["m"].get("total_actif") or x["m"].get("total_passif")
        for k in list(x["m"]):
            v = x["m"][k]
            if not v or k in x["vk"]:
                continue
            others = [(o, ot) for o, ot in pool.get((x["t"], x["y"], k), []) if o != v]
            mv = mirror_v(x["t"], x["y"], k)
            if mv:
                others.append((mv, None))
            hit = [o for o, ot in others if o and scaled(v, o) and not (outsized(k, o, ot) and not outsized(k, v, tot_x))]
            if hit:
                del x["m"][k]
                n_del += 1
        if n_del >= 2:
            bad.add((x["doc"], x["per"]))  # plusieurs postes dans une autre unité : l'unité du document est en cause
    recs = drop_docs(recs, bad)
    # année de chiffres : un exercice dont les montants sont ceux d'une autre année dans d'autres sources (colonnes inversées)
    # discrédite le document ; un exercice dont le sens des colonnes a été supposé doit être confirmé par une autre source
    KEYC = ("total_actif", "resultat_net", "chiffre_affaires", "b_pnb", "capitaux_propres")
    idx_ty = {}
    for x in recs:
        idx_ty.setdefault((x["t"], x["y"]), []).append(x)

    def same(a_, b_):
        return a_ is not None and b_ is not None and abs(a_ - b_) <= max(0.5, abs(b_) * 0.001)

    def dk(u_):  # (même document déposé deux fois, « …_2004.pdf » et « …_2004_0.pdf » : une seule source)
        return re.sub(r"(?:_\d)?\.pdf$", "", (u_ or "").rsplit("/", 1)[-1].lower())

    # lecture par reconnaissance de caractères démentie par une couche texte pour le même exercice (aucun montant clé commun,
    # au moins deux différents) : ses années sont suspectes, elle ne confirme rien ailleurs (sinon un scan mal daté entraîne
    # avec lui les colonnes d'un autre document : Sonatel 2003-2004)
    def _contradicted(o):
        if not o["ocr"]:
            return False
        for p_ in idx_ty.get((o["t"], o["y"]), []):
            if p_["ocr"] or dk(p_["doc"]) == dk(o["doc"]) or p_["per"] != o["per"]:
                continue  # (même périmètre seulement : comptes sociaux et consolidés diffèrent)
            n_same = n_diff = 0
            for k in KEYC:
                a_, b_ = o["m"].get(k), p_["m"].get(k)
                if a_ is None or b_ is None:
                    continue
                if same(a_, b_):
                    n_same += 1
                else:
                    n_diff += 1
            if n_diff >= 2 and n_same == 0:
                return True
        return False
    contra = {id(o) for o in recs if _contradicted(o)}

    def support(x, y, peers=False):
        n_ = 0
        for k in KEYC:
            v = x["m"].get(k)
            if v is None and k == "resultat_net":
                v = x["m"].get("resultat_bilan")  # (résultat lu au bilan seulement : même montant publié)
            if v is None:
                continue
            # (pour juger un décalage d'années, une lecture par reconnaissance de caractères ne contredit pas une couche texte)
            if any(o is not x and dk(o["doc"]) != dk(x["doc"]) and id(o) not in contra and same(v, o["m"].get(k, o["m"].get("resultat_bilan") if k == "resultat_net" else None))
                   and not (peers and o["ocr"] and not x["ocr"]) for o in idx_ty.get((x["t"], y), [])):
                n_ += 1
            elif same(v, mirror_v(x["t"], y, k)) or (mirror_v(x["t"], y, k) is not None and abs(v - mirror_v(x["t"], y, k)) <= abs(mirror_v(x["t"], y, k)) * 0.005):
                n_ += 1
        return n_
    keep = []
    swapped = {}  # (document, périmètre) -> sens de la permutation des colonnes établi sur un de ses exercices
    pending = []  # exercices au sens supposé, non confirmés : réattribués si l'autre exercice du même document l'a été
    for x in recs:
        s0 = support(x, x["y"])
        sh = max(support(x, x["y"] - 1, True), support(x, x["y"] + 1, True))
        if sh >= 2 and s0 == 0 and not x["guess"] and not x["ocr"]:
            bad.add((x["doc"], x["per"]))  # montants d'une autre année (en-tête lu, donc colonnes inversées : document discrédité)
            continue
        if (x["guess"] or (x["ocr"] and sh >= 2)) and s0 == 0:  # (en-tête d'un scan mal lu : traité comme un sens supposé)
            # sens des colonnes supposé (aucun en-tête lisible) : si les autres sources donnent ces montants pour l'exercice voisin
            # (au moins deux postes) et rien pour celui-ci, les colonnes étaient dans l'autre ordre — l'exercice est réattribué
            dy_ = [dy for dy in (-1, 1) if support(x, x["y"] + dy, True) >= 2]
            if len(dy_) == 1:
                x["y"] += dy_[0]
                x["shifted"] = True
                swapped[(x["doc"], x["per"])] = dy_[0]
                keep.append(x)
            else:
                pending.append(x)
            continue  # sens des colonnes non confirmé
        # poste isolé pris dans la colonne voisine : sa valeur est celle d'une autre année dans une autre source, qui donne pour
        # cette année-ci une valeur différente (communiqué de résultats lu par reconnaissance de caractères, colonnes décalées)
        for k in list(x["m"]):
            v = x["m"][k]
            if v is None or k in x["vk"]:
                continue
            for y2 in (x["y"] - 1, x["y"] + 1):
                o2 = [o["m"].get(k) for o in idx_ty.get((x["t"], y2), []) if o["doc"] != x["doc"]] + [mirror_v(x["t"], y2, k)]
                o0 = [o["m"].get(k) for o in idx_ty.get((x["t"], x["y"]), []) if o["doc"] != x["doc"]] + [mirror_v(x["t"], x["y"], k)]
                if abs(v) > 100 and any(same(v, w) for w in o2) and any(w is not None and not same(v, w) for w in o0) \
                        and not any(same(v, w) for w in o0):
                    del x["m"][k]
                    break
        if x["m"]:
            keep.append(x)
    for x in pending:  # l'autre colonne du document dont les colonnes étaient permutées : décalée en sens inverse
        dy = swapped.get((x["doc"], x["per"]))
        if dy and x["y"] - dy not in {o["y"] for o in keep if o["doc"] == x["doc"] and o["per"] == x["per"]}:
            x["y"] -= dy
            x["shifted"] = True
            keep.append(x)
    # autre colonne d'un document dont une colonne a été réattribuée, restée sur l'exercice de celle-ci (deux colonnes d'un même
    # document pour un même exercice) : colonnes permutées si d'autres sources donnent ses montants pour l'exercice d'où vient
    # l'autre, en-tête décalé d'un an pour toutes les colonnes si elles les donnent l'année suivante ; sinon exercice incertain,
    # colonne écartée (« Etats financiers provisoires - SONATEL SN - Exercice 2004 » lu avec les années 2002-2003)
    for (doc_, per_), dy in swapped.items():
        mine = [o for o in keep if o["doc"] == doc_ and o["per"] == per_]
        taken = {o["y"] for o in mine if o.get("shifted")}
        for o in mine:
            if o.get("shifted") or o["y"] not in taken:
                continue
            s_sw, s_sh = support(o, o["y"] - dy, True), support(o, o["y"] + dy, True)
            if s_sw >= 1 and s_sh == 0:
                o["y"] -= dy
            elif s_sh >= 1 and s_sw == 0 and o["y"] + dy not in taken:
                o["y"] += dy
            else:
                keep.remove(o)
                continue
            o["shifted"] = True
    recs = drop_docs(keep, bad)
    # reconnaissance de caractères vérifiée par une seule identité : un total du bilan qui change de plus de 3 fois d'une colonne à
    # l'autre du même document trahit une lecture fautive
    by_d = {}
    for x in recs:
        if x["ocr"] and x["strong"] < 2 and x["m"].get("total_actif"):
            by_d.setdefault((x["doc"], x["per"]), []).append(x["m"]["total_actif"])
    for dk_, tas in by_d.items():  # (dk_ : ne pas masquer la fonction dk définie plus haut)
        if len(tas) >= 2 and min(tas) > 0 and max(tas) / min(tas) > 3:
            bad.add(dk_)
    recs = drop_docs(recs, bad)
    # cohérence dans le temps : un total du bilan ou un chiffre d'affaires non confirmé par une autre source, plus de 4 fois plus grand
    # (ou plus petit) que ceux des exercices voisins donnés par les autres sources, discrédite le document
    NBK = ("total_actif", "chiffre_affaires", "b_pnb")
    ref_ = {}
    for x in recs:
        for k in NBK:
            v = x["m"].get(k)
            if v and v > 0:
                ref_.setdefault((x["t"], k, x["y"]), []).append((x["doc"], v))

    def ref_vals(x, k, y):
        ws = [w for d_, w in ref_.get((x["t"], k, y), []) if d_ != x["doc"]]
        mv = mirror_v(x["t"], y, k)
        return ws + ([mv] if mv and mv > 0 else [])
    for x in recs:
        for k in NBK:
            v = x["m"].get(k)
            if not v or v <= 0:
                continue
            nb_o = [statistics.median(math.log10(w) for w in ref_vals(x, k, y)) for y in range(x["y"] - 2, x["y"] + 3)
                    if y != x["y"] and ref_vals(x, k, y)]
            if any(abs(w - v) <= max(0.5, w * 0.005) for w in ref_vals(x, k, x["y"])):
                # confirmé par une autre source du même exercice : seule une erreur d'unité commune à ces sources (plus de 30 fois
                # l'ordre de grandeur des exercices voisins) le discrédite
                if len(nb_o) >= 2 and abs(math.log10(v) - statistics.median(nb_o)) > 1.5:
                    bad.add((x["doc"], x["per"]))
                continue
            same_ = ref_vals(x, k, x["y"])
            nb = nb_o + ([statistics.median(math.log10(w) for w in same_)] if same_ else [])
            # (une lecture par reconnaissance de caractères vérifiée par une seule identité : un seul exercice voisin suffit — un chiffre
            # de tête perdu laisse actif et passif égaux, mais dix fois trop petits)
            if (len(nb) >= 2 or (nb and x["ocr"] and x["strong"] < 2)) and abs(math.log10(v) - statistics.median(nb)) > math.log10(4):
                bad.add((x["doc"], x["per"]))
    recs = drop_docs(recs, bad)
    consolidate.bad = bad  # (documents écartés, pour contrôle)
    out = {}
    by_t = {}
    for x in recs:
        by_t.setdefault(x["t"], []).append(x)
    for t, xs in by_t.items():
        # périmètre et norme : ceux qui concordent le mieux avec la base de référence, sinon ceux qui couvrent le plus d'exercices
        groups = {}
        for x in xs:
            groups.setdefault((x["per"], x["std"]), []).append(x)

        def agree(g):
            ok = n = 0
            for x in g:
                for k in ("chiffre_affaires", "b_pnb", "resultat_net", "total_actif"):
                    mv = mirror_v(t, x["y"], k)
                    if mv and x["m"].get(k) is not None:
                        n += 1
                        ok += abs(x["m"][k] - mv) <= abs(mv) * 0.01 + 0.5
            return (ok / n if n else 0, len({x["y"] for x in g}), g[0]["std"] == "syscohada", n)
        def years_of(gk_):
            res = {}
            for y in sorted({x["y"] for x in groups[gk_]}):
                cand = sorted([x for x in groups[gk_] if x["y"] == y], key=lambda x: x["rank"], reverse=True)
                # document principal de l'exercice : en couche texte, ses propres comptes, définitifs de préférence ; ses montants
                # sont gardés ensemble (un exercice cohérent), les autres documents complètent les postes qu'il n'a pas
                prim = max(cand, key=lambda x: (not x["ocr"], x["rank"][0], x["rank"][1], len(x["vk"]), x["rank"][2]))
                # un autre document (comptes au moins aussi définitifs, en couche texte) dont les chiffres clés vérifiés sont repris
                # par plus de sources (documents distincts, base de référence) que ceux du document principal, sans jamais l'être
                # moins : ce sont les chiffres retenus par la société après coup (exercice corrigé) ; il devient le document principal
                def nat(x, k):  # (montant dans la monnaie du document : les états en dollars se comparent en dollars)
                    return x["m"][k] / (x["fx"] or 1.0)

                def votes(x, k):
                    v_ = nat(x, k)
                    n_ = len({o.get("fy") for o in cand if o["m"].get(k) is not None and abs(nat(o, k) - v_) <= max(0.5 / (x["fx"] or 1.0), abs(v_) * 0.001)})
                    mv_ = mirror_v(t, y, k)
                    return n_ + (1 if mv_ is not None and abs(v_ - mv_) <= abs(mv_) * 0.005 + 0.5 else 0)
                better = []
                for x in cand:
                    if x is prim or x["ocr"] or x["rank"][1] < prim["rank"][1]:
                        continue
                    win = lose = 0
                    for k in ("total_actif", "resultat_net", "chiffre_affaires", "b_pnb"):
                        if k not in x["vk"] or k not in prim["vk"] or abs(nat(x, k) - nat(prim, k)) <= max(0.5 / (x["fx"] or 1.0), abs(nat(x, k)) * 0.001):
                            continue
                        if votes(x, k) > votes(prim, k):
                            win += 1
                        elif votes(x, k) < votes(prim, k):
                            lose += 1  # (à égalité de sources, ni gagné ni perdu : un seul chiffre clé mieux repris fait basculer)
                    if win and not lose:
                        better.append(x)
                if better:
                    prim = max(better, key=lambda x: (x["rank"][1], len(x["vk"]), x["rank"][2]))
                if prim.get("fx"):  # (états en dollars : un seul cours par exercice, celui du document principal)
                    cand = [x for x in cand if x.get("fx") == prim["fx"]]
                v, nsrc, over = {}, {}, {}  # (over : postes repris d'un autre document que le principal, chiffre corrigé après coup)
                for k in sorted({k for x in cand for k in x["m"]}):
                    vals = {}
                    for x in cand:
                        if k not in x["m"]:
                            continue
                        val = x["m"][k]
                        key_ = next((z for z in vals if abs(z - val) <= max(0.5, abs(z) * 0.001)), val)
                        o = vals.setdefault(key_, {"ver": False, "txt": False, "n": 0, "rank": (0, 0, ""), "fin": 0, "docs": set()})
                        o["ver"] |= k in x["vk"]
                        o["txt"] |= not x["ocr"]
                        o["docs"].add(x["doc"])
                        o["n"] = len({x_fy for x_fy in (o.setdefault("fys", set()) | {x.get("fy")})})  # (publications distinctes : par exercice
                        o["fys"].add(x.get("fy"))  # d'origine — comptes provisoires et définitifs d'un même exercice comptent une fois)
                        o["rank"] = max(o["rank"], x["rank"])
                        o["fin"] = max(o["fin"], x["rank"][1])
                    mv = mirror_v(t, y, k)
                    fin_ = max(o["rank"][:2] for o in vals.values())
                    for z, o in vals.items():
                        # la base de référence départage des comptes de même rang, mais ne fait préférer ni des comptes
                        # provisoires à des comptes définitifs, ni la colonne N-1 de l'exercice suivant aux comptes de l'exercice
                        o["mr"] = 1 if mv is not None and abs(z - mv) <= abs(mv) * 0.005 + 0.5 else 0  # (un résultat nul de la base compte)
                        o["m"] = o["mr"] if o["rank"][:2] >= fin_ else 0
                    best_v = max(vals, key=lambda z: (vals[z]["ver"], vals[z]["txt"], vals[z]["n"] + vals[z]["m"], vals[z]["rank"]))
                    if k in prim["m"] and k in prim["vk"]:
                        # montant vérifié du document principal : gardé avec les autres membres de ses identités, sauf si un autre
                        # montant vérifié, de comptes au moins aussi définitifs, est donné par plus de sources (documents distincts
                        # et base de référence) : chiffre repris et corrigé dans les publications suivantes
                        zp = next(z for z in vals if abs(z - prim["m"][k]) <= max(0.5, abs(z) * 0.001))
                        sp_ = vals[zp]["n"] + vals[zp]["mr"]
                        alt_ = [z for z, o in vals.items() if z != zp and o["ver"] and o["fin"] >= prim["rank"][1] and o["n"] + o["mr"] > sp_]
                        best_v = max(alt_, key=lambda z: (vals[z]["n"] + vals[z]["mr"], vals[z]["txt"], vals[z]["rank"])) if alt_ else zp
                        if alt_:
                            over[k] = vals[best_v]["docs"]
                    v[k] = best_v
                    nsrc[k] = vals[best_v]["n"]
                # les deux membres d'une identité (total de l'actif et du passif, résultat du compte de résultat et du bilan) viennent
                # d'un même document quand les sources divergent ; sinon le second est retiré
                for a_k, b_k in (("total_actif", "total_passif"), ("resultat_net", "resultat_bilan")):
                    if v.get(a_k) is None or v.get(b_k) is None or abs(v[a_k] - v[b_k]) <= max(0.5, abs(v[a_k]) * 0.001):
                        continue
                    both = [x for x in cand if x["m"].get(a_k) is not None and x["m"].get(b_k) is not None
                            and abs(x["m"][a_k] - x["m"][b_k]) <= max(0.5, abs(x["m"][a_k]) * 0.001)]
                    od = over.get(a_k) or over.get(b_k)
                    if od:  # chiffre corrigé après coup : l'autre membre de l'identité vient du même document corrigé, ou disparaît
                        xo = [x for x in both if x["doc"] in od]
                        if xo:
                            v[a_k], v[b_k] = xo[0]["m"][a_k], xo[0]["m"][b_k]
                        else:
                            del v[b_k if a_k in over else a_k]
                        continue
                    if a_k in prim["m"] and b_k not in prim["m"]:
                        del v[b_k]  # (le document principal n'a que le premier membre)
                    elif both:
                        x0 = max(both, key=lambda x: (x is prim, a_k in x["vk"], not x["ocr"], x["rank"]))
                        v[a_k], v[b_k] = x0["m"][a_k], x0["m"][b_k]
                    else:
                        del v[b_k]
                # contrôle final de l'exercice reconstitué : une identité qui ne se vérifie plus (montants de documents différents)
                # -> les montants du document principal reprennent la main ; les postes d'autres documents encore en cause sont retirés
                def bad_ids(v_):
                    it_ = {k_: {0: val_} for k_, val_ in v_.items()}
                    return [n_ for n_, r_ in checks(it_, 0) if r_ is not None and r_ > 0.002 and n_ in IDENT_KEYS]
                if over:
                    # chiffre corrigé après coup (colonne N-1 des comptes suivants reprise par la base) : les autres membres de ses
                    # identités viennent du même document corrigé, sinon ils sont retirés (pas de mélange de deux versions des comptes)
                    od_all = set().union(*over.values())
                    for n_, keys_ in IDENT_KEYS.items():
                        if not any(k_ in over for k_ in keys_):
                            continue
                        xo = [x for x in cand if x["doc"] in od_all and all(x["m"].get(k_) is not None for k_ in keys_ if k_ in v)]
                        for k_ in keys_:
                            if k_ in v and k_ not in over:
                                if xo:
                                    v[k_] = xo[0]["m"][k_]
                                else:
                                    del v[k_]
                if bad_ids(v):
                    for k_ in prim["m"]:
                        if k_ in v and k_ not in over:
                            v[k_] = prim["m"][k_]
                    for n_ in bad_ids(v):
                        for k_ in IDENT_KEYS[n_]:
                            if k_ in v and k_ not in prim["m"]:
                                del v[k_]
                # sommes de postes (ventes = chiffre d'affaires, immobilisations, masses du bilan, flux) : les membres viennent du même
                # document ; quand des documents différents donnent des découpages différents, les postes étrangers au document
                # principal sont retirés
                def src_of(k_):
                    return {x["doc"] for x in cand if x["m"].get(k_) is not None and abs(x["m"][k_] - v[k_]) <= max(0.5, abs(v[k_]) * 0.001)}
                for parts_, tot_ in SOFT_SUMS:
                    ks_ = [k_ for k_ in parts_ + (tot_,) if v.get(k_) is not None]
                    if v.get(tot_) is None or len(ks_) < 3:
                        continue
                    s_ = sum((-abs(v[k_]) if k_ in CHARGES else v[k_]) for k_ in parts_ if v.get(k_) is not None)
                    if abs(s_ - v[tot_]) <= max(1.0, abs(v[tot_]) * 0.005):
                        continue
                    if v[tot_] == 0 and abs(s_) > 1.0:
                        del v[tot_]  # (un total nul face à des composantes non nulles : tiret lu comme un zéro)
                        continue
                    if set.intersection(*(src_of(k_) for k_ in ks_)):
                        continue  # (tous les membres viennent d'un même document : c'est son découpage, gardé tel quel)
                    if not all(prim["doc"] in src_of(k_) for k_ in ks_):
                        for k_ in ks_:
                            if prim["doc"] not in src_of(k_):
                                del v[k_]
                # solidité de chaque montant retenu : membre d'une identité vérifiée de son document, ou donné à l'identique par au
                # moins deux documents, ou par la base de référence. Un montant isolé qui contredit la base de référence n'est pas
                # affiché (un seul document, rien pour départager)
                weak = []
                for k_ in list(v):
                    if k_ not in v:
                        continue
                    sup_ = [x for x in cand if x["m"].get(k_) is not None and abs(x["m"][k_] - v[k_]) <= max(0.5, abs(v[k_]) * 0.001)]
                    # (une identité vérifiée ne compte que lue dans la couche texte, ou par reconnaissance de caractères avec au moins
                    # deux identités : une page numérisée qui juxtapose plusieurs tableaux peut donner « actif = passif » d'un autre état)
                    if any(k_ in x["vk"] and (not x["ocr"] or x["strong"] >= 2) for x in sup_) or len({x["doc"] for x in sup_}) >= 2:
                        continue
                    mv = mirror_v(t, y, k_)
                    if mv is not None and abs(v[k_] - mv) <= abs(mv) * 0.005 + 0.5:
                        continue
                    if mv and scaled(v[k_], mv) and k_ in ("total_actif", "total_passif", "chiffre_affaires", "b_pnb"):
                        # écart d'un facteur 1 000 : erreur d'unité d'un côté ; l'ordre de grandeur de la société tranche
                        sc_ = scale.get((t, "total_actif" if k_ == "total_passif" else k_), [])
                        if len(sc_) >= 2 and abs(math.log10(abs(v[k_])) - statistics.median(sc_)) <= 1 \
                                and abs(math.log10(abs(mv)) - statistics.median(sc_)) > 2:
                            continue  # (c'est la base qui se trompe d'unité)
                    if mv:  # (un zéro de la base de référence est une donnée manquante)
                        for k2_ in {"total_actif": ("total_passif",), "resultat_net": ("resultat_bilan",)}.get(k_, ()):
                            if v.get(k2_) is not None and abs(v[k2_] - v[k_]) <= max(0.5, abs(v[k_]) * 0.001):
                                del v[k2_]  # (l'autre membre de l'identité, même montant)
                        del v[k_]
                    else:
                        weak.append(k_)
                # vraisemblance entre postes : un montant isolé impossible face aux autres (capitaux propres ou résultat supérieurs au
                # total du bilan, produit net bancaire supérieur à la moitié du bilan, chiffre d'affaires de plus de 20 fois le bilan)
                for k_ in ("chiffre_affaires", "b_pnb", "total_actif", "total_passif", "ventes_marchandises", "ventes_produits", "travaux_services"):
                    if v.get(k_) is not None and v[k_] < 0:
                        del v[k_]  # (un chiffre d'affaires ou un total négatif est une erreur de lecture)
                ta_ = v.get("total_actif") or v.get("total_passif")
                if ta_ and ta_ > 0:
                    for k_, lim_ in (("capitaux_propres", 1.001), ("resultat_net", 1.0), ("b_pnb", 0.5), ("chiffre_affaires", 20.0)):
                        if v.get(k_) is not None and abs(v[k_]) > ta_ * lim_:
                            if k_ in weak or "total_actif" not in v:
                                del v[k_]
                            elif "total_actif" in weak:
                                v.pop("total_actif", None)
                                v.pop("total_passif", None)
                            else:
                                del v[k_]
                    # un poste du bilan (actif ou passif) plus grand que le total du bilan : autre unité ou lecture fautive
                    for k_ in list(v):
                        if k_ in ("total_actif", "total_passif") or v[k_] is None:
                            continue
                        if set(SECS.get(k_, ())) & {S_ACT, S_PAS} and abs(v[k_]) > ta_ * 1.01:
                            del v[k_]
                # postes calculés d'après le document (CALC_KEYS) : seulement là où le montant publié manque, après les mêmes
                # contrôles de vraisemblance ; marqués « faibles » : ils ne remplacent jamais un montant existant
                calc_ = []
                for kc_, kr_ in CALC_KEYS.items():
                    xv_ = v.pop(kc_, None)
                    weak = [k_ for k_ in weak if k_ != kc_]
                    if xv_ is None or v.get(kr_) is not None or xv_ <= 0:
                        continue
                    ta2_ = v.get("total_actif") or v.get("total_passif")
                    if ta2_ and xv_ > ta2_ * (0.5 if kr_ == "b_pnb" else 20.0):
                        continue
                    v[kr_] = xv_
                    weak.append(kr_)
                    calc_.append(kr_)
                # soldes SYSCOHADA manquants, recalculés à l'identique de leurs composantes publiées (définitions du plan
                # comptable : RAO = RE + RF ; EBE = VA − personnel ; capitaux propres = ressources stables − dettes financières),
                # seulement quand un autre total publié du même exercice les confirme ; jamais à la place d'un montant publié
                if gk_[1] == "syscohada" and not any(k_.startswith("b_") for k_ in v):
                    for kk_, f_ in subtotals(v):
                        if v.get(kk_) is None and f_ is not None:
                            v[kk_] = round(f_, 3)
                            weak.append(kk_)
                            calc_.append(kk_)
                weak = [k_ for k_ in weak if k_ in v]
                best = cand[0]
                res[y] = {"v": v, "n": max(nsrc.get(k, 1) for k in ("total_actif", "resultat_net") if k in nsrc) if any(k in nsrc for k in ("total_actif", "resultat_net")) else 1,
                          "d": best["d"], "own": best["rank"][0], "ns": nsrc}
                if best.get("fx"):
                    res[y]["fx"] = round(best["fx"], 4)  # (états en dollars convertis au cours du jour de publication « d »)
                if weak:
                    res[y]["w"] = sorted(weak)
                if calc_:
                    res[y]["calc"] = sorted(calc_)  # (postes calculés d'après le document : ne comblent qu'un exercice vide, en dernier)
            return res
        # référentiel principal : celui qui couvre le mieux les exercices récents, puis qui concorde le mieux avec la base de
        # référence, puis qui couvre le plus d'exercices (comptes SYSCOHADA à égalité) ; l'autre référentiel publié reste proposé
        y_max = max(x["y"] for x in xs)
        main = max(groups, key=lambda k: (len({x["y"] for x in groups[k] if x["y"] >= y_max - 4}),) + agree(groups[k])[:3])
        res = years_of(main)

        # concordance avec la base de référence (même périmètre, mêmes normes ?) : un écart confirmé par au moins deux documents
        # officiels est une erreur de la base, pas un autre périmètre
        def agree_res(res_):
            a_ok = a_n = rn_ok = rn_n = 0
            for y, r in res_.items():
                for k in ("chiffre_affaires", "b_pnb", "resultat_net", "total_actif"):
                    mv = mirror_v(t, y, k)
                    if not mv or r["v"].get(k) is None:
                        continue  # (un zéro de la base de référence est une donnée manquante)
                    ok_ = abs(r["v"][k] - mv) <= abs(mv) * 0.01 + 0.5 or r["ns"].get(k, 1) >= 2
                    a_n += 1
                    a_ok += ok_
                    if k == "resultat_net":
                        rn_n += 1
                        rn_ok += ok_
            return (a_ok / a_n if a_n else 0, a_n, round(rn_ok / rn_n, 3) if rn_n else None, rn_n)
        ag = agree_res(res)
        for r in res.values():
            r.pop("ns", None)
        out[t] = {"y": res, "per": main[0].replace("_ifrs", ""), "std": main[1], "agree": round(ag[0], 3), "ncmp": ag[1],
                  "agree_rn": ag[2], "n_rn": ag[3]}
        alts = [k for k in groups if k != main and len({x["y"] for x in groups[k]}) >= 2]
        if alts:  # autre référentiel publié (comptes sociaux / consolidés, SYSCOHADA / IFRS) : le plus complet
            k2 = max(alts, key=lambda k: (len({x["y"] for x in groups[k] if x["y"] >= y_max - 4}), len({x["y"] for x in groups[k]})))
            r2 = years_of(k2)
            a2 = agree_res(r2)
            for r in r2.values():
                r.pop("ns", None)
            out[t]["alt"] = {"y": r2, "per": k2[0].replace("_ifrs", ""), "std": k2[1], "agree": round(a2[0], 3), "ncmp": a2[1],
                             "agree_rn": a2[2], "n_rn": a2[3]}
    return out


def run_dir(d):
    """Relit tous les textes en cache (index.json, txt/) et écrit comptes.json : documents lus et exercices validés."""
    ip = os.path.join(d, "index.json")
    idx = json.load(open(ip, encoding="utf8")) if os.path.exists(ip) else {"docs": {}}
    docs = {}
    for u, m in idx.get("docs", {}).items():
        h = m.get("h")
        if not h:
            continue
        texts = {}
        for src, ocr in (("txt", False),) + tuple((x, True) for x in OCR_SRC):
            p_ = os.path.join(d, "txt", f"{h}.{src}.gz" if src != "txt" else f"{h}.txt.gz")
            if os.path.exists(p_):
                texts[src] = (gzip.open(p_, "rt", encoding="utf8").read(), ocr)
        if not texts:
            continue
        r = read_doc(texts, {**m, "u": u})
        r.update({"t": m.get("t"), "d": m.get("d"), "ti": m.get("ti"), "cat": m.get("cat")})
        docs[u] = r
    out = {"v": READER_V, "docs": docs}
    # QLAB 3 « Prévisions » : publications intermédiaires (1er trimestre, 1er semestre, 9 mois) lues dans les mêmes textes, chaque
    # ligne contrôlée par la variation publiée ; l'unité est fixée au passage du soir du terminal (scripts/periodiques.py)
    try:
        import periodiques
        out["periodic"] = periodiques.extract_all(d)["docs"]
        print(f"[comptes] publications périodiques lues : {len(out['periodic'])}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[comptes] publications périodiques non lues : {e}", flush=True)
    with open(os.path.join(d, "comptes.json"), "w", encoding="utf8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    n_ok = sum(1 for r in docs.values() if r.get("st") == "ok")
    print(f"[comptes] {len(docs)} documents relus, {n_ok} avec au moins un exercice vérifié", flush=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    run_dir(ap.parse_args().dir)
    sys.exit(0)
