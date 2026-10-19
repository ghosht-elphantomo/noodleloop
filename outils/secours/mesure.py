"""Secours BRVM, étape 1 : mesurer ce qui ne vient que de la base tierce (lecture seule).

Pour chaque famille de données de la base tierce, cherche une source à nous, lue sur les documents de la BRVM :
  - cours quotidiens : bulletins officiels de la cote (branche boc, boc_px/AAAA.json) ;
  - fondamentaux (chiffre d'affaires, résultat net, capitaux propres, total du bilan) : comptes publiés lus (branche comptes) ;
    BNPA et PER : calculables quand le résultat net et le nombre de titres sont à nous ;
  - dividendes : avis et calendriers lus (branche dividendes) et dividendes imprimés dans les bulletins ;
  - événements : avis relevés sur brvm.org (avis_brvm.json) ;
  - fiche : secteur et nombre de titres et flottant (pages de brvm.org), nom.
Écrit un rapport Markdown : ce qui est couvert, ce qui ne l'est pas, titre par titre.

Usage : mesure.py --base DOSSIER --boc DOSSIER --comptes comptes.json --dividendes dividendes.json --data DOSSIER_data [--raw DOSSIER] > rapport.md
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os


def jl(p, d=None):
    try:
        with open(p, encoding="utf8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return d


def ddmmyyyy(s):
    try:
        return int(dt.datetime.strptime(s.strip(), "%d/%m/%Y").strftime("%Y%m%d"))
    except ValueError:
        return None


def periodes(ds):
    """liste de dates AAAAMMJJ -> texte court (première – dernière, nombre)"""
    if not ds:
        return "—"
    ds = sorted(ds)
    f = lambda x: f"{x % 100:02d}/{x // 100 % 100:02d}/{x // 10000}"  # noqa: E731
    return f"{f(ds[0])} – {f(ds[-1])} ({len(ds)})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--boc", required=True)
    ap.add_argument("--comptes", required=True)
    ap.add_argument("--dividendes", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--raw")
    a = ap.parse_args()
    out = []
    P = out.append

    acts = (jl(os.path.join(a.base, "actions.json"), {}) or {}).get("actions") or []
    tick = {x["ticker"]: x for x in acts if x.get("ticker")}
    P("# Secours BRVM, étape 1 : ce qui ne vient que de la base tierce")
    P("")
    P(f"Mesure du {dt.date.today().strftime('%d/%m/%Y')} (lecture seule, `outils/secours/mesure.py`). Titres de la base : {len(tick)}.")
    P("")

    # 1. cours quotidiens
    boc = collections.defaultdict(set)
    bdiv = collections.defaultdict(list)
    for f in sorted(os.listdir(a.boc)):
        if f[:4].isdigit() and f.endswith(".json"):
            for d, rows in (jl(os.path.join(a.boc, f), {}) or {}).items():
                for t, r in rows.items():
                    if r and (r[2] or r[0]):
                        boc[t].add(int(d))
                    if r and len(r) > 9 and r[8] and r[9]:
                        bdiv[t].append((int(d), r[8], r[9]))
    first_boc = min((min(v) for v in boc.values() if v), default=None)
    tot_avant = tot_trous = 0
    lignes, jours_base = [], set()
    jours_boc = set().union(*boc.values()) if boc else set()
    for t, x in sorted(tick.items()):
        p = os.path.join(a.base, (x.get("csv") or "") + ".csv")
        ds = []
        try:
            with open(p, encoding="utf-8-sig") as fh:
                for r in csv.reader(fh, delimiter=";"):
                    d = ddmmyyyy(r[0]) if r else None
                    if d:
                        ds.append(d)
        except OSError:
            pass
        b = boc.get(t, set())
        b0 = min(b) if b else None
        avant = [d for d in ds if b0 is None or d < b0]
        trous = [d for d in ds if b0 is not None and d >= b0 and d not in b]
        jours_base.update(d for d in ds if first_boc and d >= first_boc)
        tot_avant += len(avant)
        tot_trous += len(trous)
        lignes.append(f"| {t} | {periodes(ds)} | {periodes(sorted(b))} | {len(avant)} | {len(trous)} |")
    P("## 1. Cours quotidiens")
    P("")
    P(f"Bulletins officiels lus depuis le {periodes([first_boc])[:10] if first_boc else '—'}. Séances de la base sans bulletin à nous : "
      f"**{tot_avant}** avant le premier bulletin du titre, **{tot_trous}** après (bulletins manquants ou titre absent du bulletin).")
    P("")
    sans = sorted(jours_base - jours_boc)
    par_an = collections.Counter(d // 10000 for d in sans)
    P(f"Séances de bourse depuis le premier bulletin sans aucun bulletin lu par nous : **{len(sans)}** ("
      + ", ".join(f"{y} : {n}" for y, n in sorted(par_an.items())) + ") ; le reste des trous = titre absent du bulletin lu ce jour-là.")
    P("")
    P("| Titre | Base tierce | Bulletins officiels | Séances avant | Trous après |")
    P("|---|---|---|---|---|")
    out.extend(lignes)
    P("")

    # 2. fondamentaux
    F = jl(os.path.join(a.base, "fundamentals.json"), {}) or {}
    C = (jl(a.comptes, {}) or {}).get("docs") or {}
    own = collections.defaultdict(lambda: collections.defaultdict(set))  # titre -> champ -> {exercices}
    MAP = {"ca": ("chiffre_affaires", "b_pnb"), "resultat_net": ("resultat_net", "resultat_bilan"), "capitaux_propres": ("capitaux_propres",),
           "total_bilan": ("total_actif",)}
    for d in C.values():
        if d.get("st") not in ("ok",) or d.get("per") != "annuel" or not d.get("t"):
            continue
        for main, yy in (d.get("y") or {}).items():
            if not isinstance(yy, dict):
                continue
            for y, r in yy.items():
                v = (r or {}).get("v") if isinstance(r, dict) else None
                if not isinstance(v, dict):
                    continue
                for k, ks in MAP.items():
                    if any(v.get(k2) is not None for k2 in ks):
                        own[d["t"]][k].add(str(y))
    P("## 2. Fondamentaux par exercice")
    P("")
    P("Couvert = montant lu par nous dans des comptes publiés vérifiés (contrôles comptables passés). BNPA calculable = résultat net à nous "
      "(÷ nombre de titres des bulletins ou de brvm.org) ; PER calculable = cours ÷ BNPA.")
    P("")
    P("| Champ | Valeurs de la base | Couvertes par nous | Seulement dans la base |")
    P("|---|---|---|---|")
    manque = collections.defaultdict(list)
    for k in ("ca", "resultat_net", "capitaux_propres", "total_bilan", "bnpa", "per"):
        n = c = 0
        for t, f in F.items():
            if t == "_meta" or not isinstance(f, dict):
                continue
            for y, v in ((f.get("series") or {}).get(k) or {}).items():
                if v is None:
                    continue
                n += 1
                kk = "resultat_net" if k in ("bnpa", "per") else k
                if y in own[t][kk]:
                    c += 1
                else:
                    manque[k].append(f"{t} {y}")
        P(f"| {k} | {n} | {c} | {n - c} |")
    P("")
    for k in ("resultat_net", "ca", "capitaux_propres", "total_bilan"):
        par = collections.defaultdict(list)
        for x in manque[k]:
            t, y = x.split()
            par[t].append(y)
        P(f"**{k}, exercices seulement dans la base** : " + ("; ".join(f"{t} {min(v)}-{max(v)} ({len(v)})" for t, v in sorted(par.items())) or "aucun"))
        P("")

    # 3. dividendes
    D = (jl(os.path.join(a.base, "dividendes.json"), {}) or {}).get("all") or []
    O = (jl(a.dividendes, {}) or {}).get("rows") or []
    off = {(r["t"], r.get("ex")) for r in O if r.get("t") and r.get("net")}
    offd = collections.defaultdict(list)
    for r in O:
        for k in ("det", "pay"):
            if r.get(k):
                offd[r["t"]].append(r[k][:10])
    for t, L in bdiv.items():
        for d, v, dd in L:
            offd[t].append(str(dd)[:10])

    def near(t, d):
        if not d:
            return False
        try:
            d0 = dt.date.fromisoformat(d[:10])
        except ValueError:
            return False
        for x in offd.get(t, []):
            try:
                if abs((dt.date.fromisoformat(x) - d0).days) <= 15:
                    return True
            except ValueError:
                continue
        return False
    seul = [x for x in D if x.get("ticker") and x.get("dividende") and (x["ticker"], x.get("exercice")) not in off
            and not near(x["ticker"], x.get("date_paiement") or x.get("date_detachement"))]
    par = collections.defaultdict(list)
    for x in seul:
        par[x["ticker"]].append(str(x.get("exercice")))
    P("## 3. Dividendes")
    P("")
    P(f"Versements de la base : {len(D)} ; retrouvés dans nos avis, calendriers ou bulletins officiels : {len(D) - len(seul)} ; "
      f"**seulement dans la base : {len(seul)}**" + (" : " + "; ".join(f"{t} {', '.join(sorted(v))}" for t, v in sorted(par.items())) if seul else "") + ".")
    P("")

    # 4. événements
    E = (jl(os.path.join(a.base, "events.json"), {}) or {}).get("events") or []
    AV = (jl(os.path.join(a.data, "avis_brvm.json"), {}) or {}).get("items") or {}
    d_av = min((x.get("d") for x in AV.values() if x.get("d")), default=None)
    an = collections.Counter(str(x.get("published_at") or x.get("event_at") or "")[:4] for x in E if (x.get("published_at") or x.get("event_at")))
    avant = sum(v for k, v in an.items() if d_av and k and k < d_av[:4])
    P("## 4. Événements et publications")
    P("")
    P(f"Événements de la base : {len(E)} (depuis {min(an) if an else '—'}). Avis relevés par nous sur brvm.org : {len(AV)} (depuis le "
      f"{d_av or '—'}). Les documents eux-mêmes (rapports, états financiers, avis) sont relus par nous sur brvm.org (branches comptes et "
      f"dividendes) ; la liste des publications d'avant {d_av[:4] if d_av else '—'} ({avant} événements) ne vient que de la base et de "
      "l'archive web.")
    P("")

    # 5. fiche
    raw = a.raw or ""
    sec = (jl(os.path.join(raw, "secteurs_brvm.json"), {}) or {}).get("rows") or (jl(os.path.join(a.data, "secteurs.json"), {}) or {}).get("rows") or {}
    sess = {r["t"]: r for r in (jl(os.path.join(a.data, "session.json"), {}) or {}).get("rows") or [] if r.get("t")}
    P("## 5. Fiche des sociétés")
    P("")
    P(f"- Secteur : lu sur brvm.org pour {sum(1 for t in tick if t in sec)} titres sur {len(tick)}.")
    P(f"- Nombre de titres et flottant : page « Capitalisations » de brvm.org pour {sum(1 for t in tick if (sess.get(t) or {}).get('sh'))} titres sur {len(tick)}.")
    P(f"- Présentation (DES) : textes FQT vérifiés sur documents (`seed/des_fqt.json`) pour {len((jl('seed/des_fqt.json', {}) or {}).get('desc') or {})} titres.")
    soc = (jl("seed/societes.json", {}) or {}).get("rows") or {}
    P(f"- Nom, nom officiel, banque ou non : fichier FQT `seed/societes.json` pour {sum(1 for t in tick if t in soc)} titres sur {len(tick)} "
      "(la base en secours, écarts signalés chaque matin) ; pays : déduit du symbole.")
    P("")
    print("\n".join(out))


if __name__ == "__main__":
    main()
