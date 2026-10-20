#!/usr/bin/env python3
"""Base historique BRVM : archive cumulative, contrôlée et journalisée.

Lue chaque soir après la mise à jour du terminal, sur la branche `histo` (jamais publiée sur le site).
- Rien n'est jamais effacé : une ligne absente de la source du jour reste dans la base. Exception : dividendes.csv, table dérivée
  de dividends.json, où une clé absente des versements du jour est retirée (et consignée) pour qu'un exercice ne compte qu'une fois.
- Une valeur qui change est remplacée et l'ancienne est consignée dans corrections.csv.
- Les contrôles de cohérence du jour sont écrits dans controles.csv (état courant) ; l'historique git garde les précédents.
Bibliothèque standard Python uniquement.
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boc_regles as BR  # noqa: E402  (règles de lecture des bulletins partagées avec build_terminal.py)

VERSION = 1


def fnum(x):
    """Écriture canonique (identique d'un jour à l'autre) pour comparer sans bruit."""
    if x is None:
        return ""
    if isinstance(x, bool):
        return "1" if x else "0"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            return ""
        if x == int(x) and abs(x) < 1e15:
            return str(int(x))
        return ("%.6f" % x).rstrip("0").rstrip(".")
    return str(x).strip()


def iso(d):
    """20261014 / '20261014' / '2026-10-14' -> '2026-10-14'."""
    if d is None or d == "":
        return ""
    s = str(d)
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s[:10]


def fl(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


class Table:
    """Fichier CSV clé -> ligne, mis à jour sans jamais rien effacer."""

    def __init__(self, root, name, cols, key, sort=None, req=None):
        self.name, self.cols, self.key, self.sort = name, cols, key, sort
        self.req = [key.index(c) for c in (req or key)]
        self.path = os.path.join(root, name)
        self.rows, self.added, self.changed, self.dirty = {}, 0, [], False
        if os.path.exists(self.path):
            with open(self.path, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    r = {c: row.get(c) or "" for c in cols}
                    self.rows[self.k(r)] = r
        self.n0 = len(self.rows)

    def k(self, r):
        return tuple(r.get(c, "") for c in self.key)

    def upsert(self, row):
        r = {c: fnum(row.get(c)) for c in self.cols}
        k = self.k(r)
        if any(k[i] == "" for i in self.req):
            return None
        old = self.rows.get(k)
        if old is None:
            self.rows[k] = r
            self.added += 1
            self.dirty = True
            return "new"
        # une valeur disparue de la source ne remplace jamais une valeur connue
        diff = [(c, old.get(c, ""), r[c]) for c in self.cols if c not in self.key and r[c] != "" and old.get(c, "") != r[c]]
        if not diff:
            return None
        for c, _, n in diff:
            old[c] = n
        self.changed.append((k, diff))
        self.dirty = True
        return "chg"

    def drop(self, pred):
        """Retire les lignes reconnues invalides (jamais une ligne simplement absente de la source) ; renvoie les clés retirées."""
        ks = [k for k, r in self.rows.items() if pred(r)]
        for k in ks:
            del self.rows[k]
        if ks:
            self.dirty = True
        return ks

    def save(self):
        if not self.dirty and os.path.exists(self.path):
            return
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        rows = sorted(self.rows.values(), key=self.sort or self.k)
        tmp = self.path + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=self.cols, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, self.path)


FORMAT_ACTUEL = "2018-01-01"


def lisible(r):
    """Les bulletins antérieurs à 2018 ont plusieurs mises en page dont les colonnes ne sont pas toujours lues au bon endroit.
    Avant 2018, une ligne n'est retenue que si elle se vérifie d'elle-même (clôture / cours précédent = variation publiée),
    ou s'il s'agit d'un titre non coté ce jour-là (cours précédent = cours de référence, sans échange)."""
    if r["date"] >= FORMAT_ACTUEL:
        return True
    c, p, var, ref = fl(r.get("cloture")), fl(r.get("precedent")), fl(r.get("variation_pct")), fl(r.get("reference"))
    if c and p and var is not None:
        return abs((c / p - 1) * 100 - var) <= 0.06
    return bool(not c and p and ref and p == ref and not r.get("volume") and not var)


def load(p, default=None):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


COURS = ["date", "titre", "precedent", "ouverture", "cloture", "variation_pct", "volume", "valeur", "reference",
         "variation_annuelle_pct", "dernier_dividende", "date_dividende", "rendement_pct", "per", "cours_moyen"]
BOC_MAP = {"prev": "precedent", "o": "ouverture", "c": "cloture", "var": "variation_pct", "vol": "volume", "val": "valeur", "ref": "reference",
           "ytd": "variation_annuelle_pct", "div": "dernier_dividende", "div_d": "date_dividende", "yld": "rendement_pct", "per": "per", "avg": "cours_moyen"}
RESULTATS = [("ca", "chiffre_affaires"), ("resultat_net", "resultat_net"), ("bnpa", "bnpa"), ("dividende", "dividende"),
             ("capitaux_propres", "capitaux_propres"), ("total_bilan", "total_bilan"), ("tresorerie", "tresorerie"), ("ebit", "ebit"),
             ("ebitda", "ebitda"), ("dette_nette", "dette_nette"), ("depots_clientele", "depots_clientele"),
             ("credits_clientele", "credits_clientele"), ("cout_du_risque", "cout_du_risque")]
OST = {"Fractionnement", "Actions gratuites", "Augmentation de capital avec droits", "Avis sur une opération de capital",
       "Valeur théorique publiée", "Transaction annulée par la BRVM", "Modification du dividende", "Détachement dividende",
       "Paiement dividende", "Annonce dividende"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="données publiées du terminal (dossier data)")
    ap.add_argument("--boc", required=True, help="archive des bulletins officiels (boc_px)")
    ap.add_argument("--out", required=True, help="dossier de la base historique")
    ap.add_argument("--comptes", default=None, help="comptes.json (états financiers publiés, lus et vérifiés)")
    a = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date().isoformat()
    out = a.out
    os.makedirs(out, exist_ok=True)
    tables = []
    log = []

    # ---------- 1. cours officiels des actions (bulletins de la cote, tels que publiés) ----------
    idx = load(os.path.join(a.boc, "_index.json"), {}) or {}
    bcols = idx.get("cols") or list(BOC_MAP)
    summ = load(os.path.join(a.data, "summary.json"), {}) or {}
    secs = summ.get("secs") or []
    brvm_eq = {s["id"] for s in secs if s.get("mkt") == "BRVM" and s.get("cls") == "Equity"}
    # titres retenus : cotés aujourd'hui, ou anciens titres présents sur au moins 250 séances (radiés, suspendus) ;
    # les autres libellés sont des lignes d'autres tableaux du bulletin, pas des actions
    seen = {}
    for f in glob.glob(os.path.join(a.boc, "[12][0-9][0-9][0-9].json")):
        for rows in (load(f, {}) or {}).values():
            for tk in rows:
                seen[tk] = seen.get(tk, 0) + 1
    keep = brvm_eq | {tk for tk, n in seen.items() if n >= 250}
    years, skipped, n_src = {}, {}, {}
    prev_rows, dup_days, n_mill = None, [], []
    last_boc = ""
    for f in sorted(glob.glob(os.path.join(a.boc, "[12][0-9][0-9][0-9].json"))):
        y = os.path.basename(f)[:4]
        data = load(f, {}) or {}
        if not data:
            continue
        t = years.get(y) or Table(out, f"cours/{y}.csv", COURS, ["date", "titre"])
        n_src[y] = n_src.get(y, 0) + sum(len(v) for v in data.values())
        years[y] = t
        for d, rows in sorted(data.items()):
            di = iso(d)
            # bulletin identique au précédent (jour férié publié sous la date du lendemain, ex. 29/10/2020) : pas une séance
            if prev_rows is not None and rows == prev_rows:
                dup_days.append(di)
                continue
            prev_rows = rows
            last_boc = max(last_boc, di)
            for tk, vals in rows.items():
                if not isinstance(vals, list) or tk not in keep:
                    continue
                r = {"date": di, "titre": tk}
                for c, v in zip(bcols, vals):
                    if c in BOC_MAP:
                        r[BOC_MAP[c]] = iso(v) if c == "div_d" else v
                if lisible(r):
                    # montants d'un milliard et plus (ou volumes de plus de dix millions) imprimés en milliers dans certains bulletins
                    # (Sonatel en 2026, ETI le 17/09/2026) : rétablis, même règle que le terminal (boc_regles.milliers)
                    vol_, val_, q_ = BR.milliers(fl(r.get("volume")), fl(r.get("valeur")), fl(r.get("cloture")), fl(r.get("ouverture")), fl(r.get("precedent")))
                    if q_:
                        r["volume" if q_ == "vol" else "valeur"] = vol_ if q_ == "vol" else val_
                        n_mill.append(f"{di} {tk}" + (" (volume)" if q_ == "vol" else ""))
                    t.upsert(r)
                else:
                    skipped[y] = skipped.get(y, 0) + 1
    tables += [years[y] for y in sorted(years)]

    # ---------- 2. indices BRVM (séances closes uniquement) ----------
    cutoff = today if now.hour >= 18 else (now.date() - dt.timedelta(days=1)).isoformat()
    ti = Table(out, "indices.csv", ["date", "indice", "valeur"], ["date", "indice"])
    for s in secs:
        if s.get("mkt") != "BRVM" or s.get("cls") != "Index":
            continue
        ser = load(os.path.join(a.data, "s", s["id"] + ".json"), {}) or {}
        for d, c in zip(ser.get("d") or [], ser.get("c") or []):
            di = iso(d)
            if di <= cutoff and fl(c):
                ti.upsert({"date": di, "indice": s["id"], "valeur": round(float(c), 2)})
    # séances d'indices reconnues fausses par le terminal (jour férié recopiant la veille, valeur figée un jour où le marché a bougé,
    # contrôlées sur les bulletins officiels) : retirées aussi de l'archive
    bad_idx = {(iso(d), code) for code, ds in ((load(os.path.join(a.data, "boc_check.json"), {}) or {}).get("idx_drop") or {}).items() for d in ds}
    if bad_idx:
        ti.drop(lambda r: (r["date"], r["indice"]) in bad_idx)
    tables.append(ti)

    # ---------- 3. dividendes (avis officiels et bulletins de la cote) ----------
    # (un exercice payé en plusieurs fois — acompte et solde, dividende complémentaire — : versements additionnés, dates du dernier ;
    # dividende exceptionnel sur sa propre ligne, type « exceptionnel »)
    tdv = Table(out, "dividendes.csv", ["titre", "exercice", "origine", "type", "dividende_net", "dividende_ajuste", "facteur_ajustement", "annonce",
                                        "detachement", "paiement"], ["titre", "exercice", "origine", "type"], req=["titre", "exercice", "origine"])
    agg = {}
    det_faux = {}  # date de détachement reconnue fausse par le terminal (« det0 », ou corrigée d'après un avis de report : « corr »)
    for x in load(os.path.join(a.data, "dividends.json"), []) or []:
        if x.get("t") not in brvm_eq or not x.get("dps"):
            continue
        org = "bulletin" if x.get("src") == "BOC" else "avis"
        k = (x["t"], x.get("ex"), org, "exceptionnel" if x.get("exc") else "")
        g = agg.setdefault(k, {"net": 0.0, "adj": 0.0, "f": x.get("adj") or 1, "ann": None, "det": None, "pay": None})
        g["net"] += x.get("dps0") or x.get("dps")
        g["adj"] += x.get("dps")
        if (iso(x.get("pay")) or "") >= (g["pay"] or ""):
            g.update(ann=iso(x.get("ann")) or g["ann"], det=iso(x.get("det")) or g["det"], pay=iso(x.get("pay")) or g["pay"])
        d0_ = x.get("det0") or (x.get("corr") or {}).get("det")
        if d0_ and not x.get("det"):
            det_faux[(fnum(x["t"]), fnum(x.get("ex")), org, k[3])] = iso(d0_)
    for (t_, ex_, org, ty_), g in agg.items():
        tdv.upsert({"titre": t_, "exercice": ex_, "origine": org, "type": ty_, "dividende_net": round(g["net"], 6), "dividende_ajuste": round(g["adj"], 6),
                    "facteur_ajustement": g["f"], "annonce": g["ann"], "detachement": g["det"], "paiement": g["pay"]})
    # (une date vide ne remplace jamais une date connue, sauf une date de détachement que le terminal a reconnue fausse — dimanche, 65
    # jours avant le paiement, avis de report — et retirée : elle est effacée de l'archive, et consignée)
    for k, d0_ in det_faux.items():
        r_ = tdv.rows.get(k)
        if r_ and r_.get("detachement") == d0_:
            r_["detachement"] = ""
            tdv.changed.append((k, [("detachement", d0_, "")]))
            tdv.dirty = True
    # table dérivée de dividends.json : une ligne dont la clé (titre, exercice, origine, type) n'est plus parmi les versements du jour
    # (versement rattaché depuis à un avis plutôt qu'à un bulletin, doublon de lecture retiré, montant mal lu) ferait compter
    # l'exercice deux fois : elle est retirée et consignée dans corrections.csv (seule exception à « rien n'est effacé », voir le
    # README). Rien n'est retiré si les versements du jour manquent ou couvrent nettement moins de clés que l'archive (lecture incomplète),
    # ni pour un titre qui n'a aucun versement du jour (titre radié, ou lecture du jour en échec pour lui)
    keys_ = {(fnum(t_), fnum(ex_), org, ty_) for (t_, ex_, org, ty_) in agg}
    tk_jour = {k[0] for k in keys_}
    div_rm = []
    if keys_ and len(keys_) >= 0.8 * len(tdv.rows):
        div_rm = [(k, dict(r)) for k, r in tdv.rows.items() if k not in keys_ and r["titre"] in tk_jour]
        tdv.drop(lambda r: tdv.k(r) not in keys_ and r["titre"] in tk_jour)
    elif tdv.rows:
        log.append(f"dividendes.csv : versements du jour incomplets ({len(keys_)} clés pour {len(tdv.rows)} archivées), aucune ligne retirée")
    tables.append(tdv)

    # ---------- 4. fractionnements / regroupements ----------
    tsp = Table(out, "fractionnements.csv", ["titre", "date", "ratio"], ["titre", "date"])
    sp_jour = {}
    for s in secs:
        if s["id"] in brvm_eq:
            for d, r in s.get("split") or []:
                tsp.upsert({"titre": s["id"], "date": iso(d), "ratio": r})
                sp_jour.setdefault(s["id"], []).append((iso(d), fl(r)))
    tables.append(tsp)

    # ---------- 5. événements et opérations sur titres (avis publiés) ----------
    tev = Table(out, "evenements.csv", ["date", "titre", "categorie", "intitule", "date_effet", "operation_sur_titre", "document"],
                ["date", "titre", "categorie", "intitule", "document"], req=["date", "titre", "categorie"])
    for x in load(os.path.join(a.data, "events.json"), []) or []:
        tk = x.get("t") or "MARCHE"
        if tk != "MARCHE" and tk not in brvm_eq:
            continue
        tev.upsert({"date": iso(x.get("d")), "titre": tk, "categorie": x.get("c"), "intitule": (x.get("ti") or "").replace("\n", " ")[:300],
                    "date_effet": iso(x.get("e")), "operation_sur_titre": 1 if x.get("c") in OST else 0, "document": x.get("u")})
    tables.append(tev)

    # ---------- 6. résultats financiers (comptes annuels, en millions de FCFA ; BNPA et dividende en FCFA) ----------
    tre = Table(out, "resultats.csv", ["titre", "exercice"] + [n for _, n in RESULTATS], ["titre", "exercice"])
    for tk, x in (load(os.path.join(a.data, "fundamentals.json"), {}) or {}).items():
        if tk not in brvm_eq or not isinstance(x, dict):
            continue
        ser = x.get("series") or {}
        yrs = sorted({y for k, _ in RESULTATS for y in (ser.get(k) or {})})
        for y in yrs:
            r = {"titre": tk, "exercice": y}
            for k, n in RESULTATS:
                v = (ser.get(k) or {}).get(y)
                r[n] = round(v, 2) if isinstance(v, float) else v
            if any(r[n] not in (None, "") for _, n in RESULTATS):
                tre.upsert(r)
    tables.append(tre)

    # ---------- 6 bis. états financiers publiés, poste par poste (millions de FCFA), exercices vérifiés ----------
    tef = Table(out, "etats_financiers.csv", ["titre", "exercice", "perimetre", "norme", "poste", "libelle", "valeur", "documents_concordants"],
                ["titre", "exercice", "poste"])
    if a.comptes and os.path.exists(a.comptes):
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import comptes as CPT
            fund = load(os.path.join(a.data, "fundamentals.json"), {}) or {}
            mir = {t: (v.get("series") or {}) for t, v in fund.items() if isinstance(v, dict)}
            for tk, cc in CPT.consolidate(load(a.comptes, {}) or {}, mir).items():
                if tk not in brvm_eq:
                    continue
                for y, r in sorted(cc["y"].items()):
                    for k, v in sorted(r["v"].items()):
                        tef.upsert({"titre": tk, "exercice": y, "perimetre": cc["per"], "norme": cc["std"], "poste": k,
                                    "libelle": CPT.LABELS.get(k, k), "valeur": round(v, 3),
                                    "documents_concordants": r.get("n")})
        except Exception as e:  # noqa: BLE001
            log.append(f"états financiers illisibles : {e}")
    tables.append(tef)

    # ---------- 7. flottant officiel ----------
    tfl = Table(out, "flottant.csv", ["date_avis", "arrete_au", "titre", "titres", "titres_flottants", "flottant_pct", "seuil_15_respecte"],
                ["date_avis", "titre"])
    F = load(os.path.join(a.data, "flottant.json"), {}) or {}
    for tk, r in (F.get("rows") or {}).items():
        tfl.upsert({"date_avis": iso(F.get("d")), "arrete_au": F.get("asof"), "titre": tk, "titres": r.get("sh"), "titres_flottants": r.get("flt"),
                    "flottant_pct": r.get("pct"), "seuil_15_respecte": r.get("ok15")})
    tables.append(tfl)

    # ---------- 8. notations financières ----------
    tno = Table(out, "notations.csv", ["publie", "titre", "agence", "long_terme", "long_terme_precedent", "court_terme", "court_terme_precedent",
                                       "perspective", "echelle", "validite", "document"], ["publie", "document"])
    for x in (load(os.path.join(a.data, "ratings.json"), {}) or {}).get("rows") or []:
        tno.upsert({"publie": iso(x.get("d")), "titre": x.get("t") or "", "agence": x.get("ag"), "long_terme": x.get("lt"), "long_terme_precedent": x.get("lt0"),
                    "court_terme": x.get("st"), "court_terme_precedent": x.get("st0"), "perspective": x.get("out"), "echelle": x.get("scale"),
                    "validite": iso(x.get("exp")), "document": x.get("u")})
    tables.append(tno)

    # ---------- journal des corrections (cumulatif) ----------
    tco = Table(out, "corrections.csv", ["constate_le", "fichier", "cle", "champ", "ancienne_valeur", "nouvelle_valeur"],
                ["constate_le", "fichier", "cle", "champ"])
    for di in dup_days:  # séance inexistante déjà archivée : retirée, et consignée
        t = years.get(di[:4])
        for k in (t.drop(lambda r, di=di: r["date"] == di) if t else []):
            tco.upsert({"constate_le": today, "fichier": t.name, "cle": " | ".join(k), "champ": "ligne", "ancienne_valeur": "séance archivée",
                        "nouvelle_valeur": "retirée : bulletin identique à celui de la veille (jour sans séance)"})
    for k, r in div_rm:  # versement archivé absent des versements du jour : ligne retirée, et consignée
        tco.upsert({"constate_le": today, "fichier": tdv.name, "cle": " | ".join(k), "champ": "ligne",
                    "ancienne_valeur": f"versement archivé : {r.get('dividende_net') or '—'} net ({r.get('dividende_ajuste') or '—'} ajusté), paiement {r.get('paiement') or '—'}",
                    "nouvelle_valeur": "retirée : absente des versements du jour (dividends.json), l'exercice ne compte qu'une fois"})
    # exercice pas encore clos (comptes semestriels pris pour des comptes annuels par une source) : ligne retirée, et consignée
    for k in tre.drop(lambda r: (r.get("exercice") or "0").isdigit() and int(r["exercice"]) >= now.year):
        tco.upsert({"constate_le": today, "fichier": tre.name, "cle": " | ".join(k), "champ": "ligne", "ancienne_valeur": "exercice archivé",
                    "nouvelle_valeur": "retirée : exercice pas encore clos (comptes semestriels)"})
    # date d'une opération sur titres corrigée par le terminal (date d'effet constatée au bulletin au lieu de celle de l'avis, ex.
    # BOABF 29/08 -> 28/08/2024) : l'ancienne ligne — même titre, même rapport, à 40 jours au plus d'une opération du jour — ferait
    # compter l'opération deux fois ; retirée, et consignée
    def sp_corrigee(r):
        lst = sp_jour.get(r.get("titre")) or []
        if not lst or any(d == r.get("date") for d, _ in lst):
            return False
        try:
            d0, x0 = dt.date.fromisoformat(r["date"]), float(r["ratio"])
            return any(x and abs(x / x0 - 1) < 1e-3 and abs((dt.date.fromisoformat(d) - d0).days) <= 40 for d, x in lst)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return False
    for k in tsp.drop(sp_corrigee):
        tco.upsert({"constate_le": today, "fichier": tsp.name, "cle": " | ".join(k), "champ": "ligne", "ancienne_valeur": "opération archivée",
                    "nouvelle_valeur": "retirée : date corrigée par le terminal (même opération, même rapport)"})
    for t in tables:
        if t.n0 == 0:  # première alimentation du fichier : rien à corriger
            continue
        for k, diff in t.changed:
            for c, o, n in diff:
                if o == "":  # simple complément d'une valeur manquante
                    continue
                tco.upsert({"constate_le": today, "fichier": t.name, "cle": " | ".join(k), "champ": c, "ancienne_valeur": o, "nouvelle_valeur": n})

    # ---------- contrôles de cohérence (état courant) ----------
    ctl = []

    def flag(fichier, titre, date, regle, detail):
        ctl.append({"fichier": fichier, "titre": titre, "date": date, "regle": regle, "detail": detail})

    splits = {}
    for r in tsp.rows.values():
        splits.setdefault(r["titre"], []).append((r["date"], fl(r["ratio"])))
    allc = sorted((r for t in years.values() for r in t.rows.values()), key=lambda r: (r["titre"], r["date"]))
    prev_c = {}
    per_day = {}
    for r in allc:
        tk, d = r["titre"], r["date"]
        per_day[d] = per_day.get(d, 0) + 1
        c, p, o = fl(r["cloture"]), fl(r["precedent"]), fl(r["ouverture"])
        vol, val, var = fl(r["volume"]), fl(r["valeur"]), fl(r["variation_pct"])
        f_ = f"cours/{d[:4]}.csv"
        if not c:
            if (vol or 0) > 0:
                flag(f_, tk, d, "cloture_absente", f"volume {fnum(vol)} sans cours de clôture")
            continue
        pc = prev_c.get(tk)
        # écart expliqué : détachement d'un dividende (référence abaissée du montant) ou fractionnement du titre
        dv = fl(r["dernier_dividende"])
        expl = False
        if pc:
            gap = pc[1] - (p or pc[1])
            if dv and gap > 0 and abs(gap - dv) <= max(0.03 * dv, 1):
                expl = True
            for sd, _ in splits.get(tk, []):
                if pc[0] < sd <= d or abs((dt.date.fromisoformat(sd) - dt.date.fromisoformat(d)).days) <= 7:
                    expl = True
            if r["date_dividende"] and pc[2] and r["date_dividende"] != pc[2] and pc[0] <= r["date_dividende"] <= d:
                expl = True
        if (vol or 0) > 0 and not (val or 0) > 0:
            flag(f_, tk, d, "volume_sans_valeur", f"volume {fnum(vol)} sans valeur échangée")
        if (val or 0) > 0 and not (vol or 0) > 0:
            flag(f_, tk, d, "valeur_sans_volume", f"valeur {fnum(val)} sans volume")
        if (vol or 0) > 0 and (val or 0) > 0:
            pm = val / vol
            if not BR.cours_moyen_ok(vol, val, c, p, o):  # (même règle que le terminal)
                flag(f_, tk, d, "prix_moyen_hors_fourchette", f"valeur/volume = {pm:.2f} pour une clôture à {fnum(c)}")
        base = p if p else (pc[1] if pc else None)
        if c and base and var is not None and abs((c / base - 1) * 100 - var) > 0.06 and not (expl and not p):
            flag(f_, tk, d, "variation_incoherente", f"variation publiée {fnum(var)} % ; calculée {(c / base - 1) * 100:.2f} % (base {fnum(base)})")
        if var is not None and abs(var) > 7.55 and not expl:
            flag(f_, tk, d, "variation_hors_seuil", f"variation de {fnum(var)} % (seuil quotidien ±7,5 %) : à rapprocher d'un avis")
        if pc and p and abs(p / pc[1] - 1) > 0.005 and not expl:
            flag(f_, tk, d, "precedent_different", f"cours précédent {fnum(p)} ≠ clôture du {pc[0]} ({fnum(pc[1])})")
        if c:
            prev_c[tk] = (d, c, r["date_dividende"])
    by_year = {}
    for d, n in per_day.items():
        by_year.setdefault(d[:4], []).append(n)
    for d, n in sorted(per_day.items()):
        med = statistics.median(by_year[d[:4]])
        if n < 0.8 * med:
            flag(f"cours/{d[:4]}.csv", "MARCHE", d, "seance_incomplete", f"{n} titres lus pour {med:g} habituellement")
    # dividendes : dates et rapprochement avis / bulletin
    byk = {}
    for r in tdv.rows.values():
        dps = fl(r["dividende_net"])
        if dps is not None and dps <= 0:
            flag("dividendes.csv", r["titre"], r["exercice"], "montant_invalide", f"dividende {r['dividende_net']}")
        a_, de, pa = r["annonce"], r["detachement"], r["paiement"]
        if de and pa and de > pa:
            flag("dividendes.csv", r["titre"], r["exercice"], "dates_incoherentes", f"détachement {de} après paiement {pa}")
        if a_ and de and a_ > de:
            flag("dividendes.csv", r["titre"], r["exercice"], "dates_incoherentes", f"annonce {a_} après détachement {de}")
        byk.setdefault((r["titre"], r["exercice"], r.get("type") or ""), {})[r["origine"]] = r
    for (tk, ex, _), v in byk.items():
        if "avis" in v and "bulletin" in v:
            x1, x2 = fl(v["avis"]["dividende_ajuste"]), fl(v["bulletin"]["dividende_ajuste"])
            if x1 and x2 and abs(x1 / x2 - 1) > 0.01:
                flag("dividendes.csv", tk, ex, "avis_different_bulletin", f"avis {fnum(x1)} FCFA ; bulletin {fnum(x2)} FCFA")
    for r in tfl.rows.values():
        sh, ft, pct = fl(r["titres"]), fl(r["titres_flottants"]), fl(r["flottant_pct"])
        if sh and ft and (ft > sh or (pct is not None and abs(ft / sh * 100 - pct) > 0.1)):
            flag("flottant.csv", r["titre"], r["date_avis"], "flottant_incoherent", f"{fnum(ft)} / {fnum(sh)} titres ≠ {fnum(pct)} %")
    for r in tre.rows.values():
        rn, bp = fl(r["resultat_net"]), fl(r["bnpa"])
        if rn and bp and (rn > 0) != (bp > 0):
            flag("resultats.csv", r["titre"], r["exercice"], "bnpa_signe_oppose", f"résultat net {fnum(rn)} ; BNPA {fnum(bp)}")
    ctl.sort(key=lambda x: (x["fichier"], x["titre"], x["date"], x["regle"]))
    with open(os.path.join(out, "controles.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["fichier", "titre", "date", "regle", "detail"], lineterminator="\n")
        w.writeheader()
        w.writerows(ctl)

    for t in tables + [tco]:
        t.save()
    rules = {}
    for x in ctl:
        rules[x["regle"]] = rules.get(x["regle"], 0) + 1
    etat = {"version": VERSION, "maj": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "derniere_seance": last_boc,
            "fichiers": {t.name: {"lignes": len(t.rows), "ajoutees": t.added, "corrigees": len(t.changed)} for t in tables},
            "bulletins_lignes_non_retenues": skipped, "bulletins_lignes_lues": n_src, "bulletins_identiques_ecartes": dup_days, "montants_en_milliers_convertis": n_mill,
            "corrections_total": len(tco.rows), "corrections_du_jour": tco.added, "controles": rules}
    with open(os.path.join(out, "etat.json"), "w", encoding="utf-8") as fh:
        json.dump(etat, fh, ensure_ascii=False, indent=1)
    for t in tables:
        if t.added or t.changed:
            log.append(f"{t.name}: +{t.added} / {len(t.changed)} corrigées")
    print("[histo] " + ("; ".join(log) or "aucun changement") + f" ; corrections du jour {tco.added} ; contrôles {len(ctl)} {rules}")


if __name__ == "__main__":
    main()
