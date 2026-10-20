"""Contrôles de cohérence du contrôle du matin (demandés par le propriétaire le 19/10/2026) : chaque chiffre important est
comparé à une seconde source officielle, ou à lui-même par un autre chemin. Rien n'est corrigé ici : un écart est signalé,
avec les valeurs côte à côte, pour être vérifié sur le document avant de toucher au chiffre affiché.

  1. fiche / BRVM : nombre de titres, flottant, secteur (miroir.json, flottant.json, secteurs.json) ;
  2. capitalisation affichée (cours × titres) / capitalisation publiée par la BRVM (session.json) ;
  3. dernier cours de la série / clôture du bulletin officiel de la cote (même séance) ; volumes des 20 dernières séances /
     bulletin (un volume partiel de la base tierce resté en place se voit ici) ;
  4. BNPA affiché / BNPA du bulletin officiel (cours ÷ PER) ;
  5. BNPA de chaque exercice / résultat net ÷ nombre de titres ;
  6. dividende : brut × (1 − impôt) = net ;
  7. éléments mal formés écartés à la construction ; fiche des sociétés FQT / base, titre nouveau au bulletin, indices douteux ;
  8. valeurs extrêmes à revoir à la main (rendement, distribution, PER).
"""
import json
import os

TOL_SH = 0.005    # nombre de titres : 0,5 %
TOL_FLT = 2.0     # flottant : 2 points
TOL_CAP = 0.02    # capitalisation : 2 %
TOL_PX = 0.001    # cours : 0,1 %
TOL_BNPA = 0.02   # BNPA : 2 %


# écarts déjà expliqués par un document officiel (vérifiés) : rappelés dans le détail, sans faire passer le contrôle à l'orange.
# Clé : (titre, « titres » ou « flottant »). Retirer une ligne dès que les sources concordent à nouveau.
EXPLIQUES = {
    ("SAFC", "titres"): "augmentation de capital avec droits, actions nouvelles admises à la cote le 25/07/2026 (avis BRVM) : "
                        "11 869 750 titres ; l'avis du flottant (chiffres au 31/12/2025) et la fiche sont antérieurs",
    ("SAFC", "flottant"): "même augmentation de capital : l'avis du flottant (au 31/12/2025) et la fiche sont antérieurs",
    ("ETIT", "bnpa"): "BNPA officiel part du groupe (états financiers IFRS : 10,00 FCFA en 2025, 4,56 en 2019), résultat net de la "
                      "série total, intérêts minoritaires compris",
}


def _expl(out, kind, D_):
    """sépare les écarts expliqués (rappelés) des écarts à vérifier"""
    a, e = [], []
    for x in out:
        (e if (x.split(" ", 1)[0], kind) in EXPLIQUES else a).append(x)
    ts = list(dict.fromkeys(x.split(" ", 1)[0] for x in e))  # (un titre une seule fois, avec le nombre d'exercices)
    note = ("" if not e else " ; déjà expliqués : " + "; ".join(
        f"{t} ({EXPLIQUES[(t, kind)]}{'' if sum(x.startswith(t + ' ') for x in e) < 2 else ', ' + str(sum(x.startswith(t + ' ') for x in e)) + ' exercices'})" for t in ts))
    return a, note


def _jl(D, f):
    try:
        with open(os.path.join(D, f), encoding="utf8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return None


def _f(x, nd=2):
    if x is None:
        return "—"
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",") if isinstance(x, float) else f"{x:,}".replace(",", " ")


def _liste(out, n=10):
    return "; ".join(out[:n]) + (f" … (+{len(out) - n})" if len(out) > n else "")


def _boc_dernier(boc):
    """dernière séance lue dans les bulletins officiels (fichiers boc_px/AAAA.json) : (date AAAAMMJJ, {titre: ligne})"""
    if not boc or not os.path.isdir(boc):
        return None, {}
    best = (None, {})
    for f in sorted(os.listdir(boc)):
        if f[:4].isdigit() and f.endswith(".json"):
            y = _jl(boc, f) or {}
            if y:
                k = max(y)
                if best[0] is None or k > best[0]:
                    best = (k, y[k])
    return best


def _boc_recents(boc, n=20):
    """n dernières séances des bulletins officiels : [(date AAAAMMJJ, {titre: ligne})]"""
    if not boc or not os.path.isdir(boc):
        return []
    L = []
    for f in sorted(x for x in os.listdir(boc) if x[:4].isdigit() and x.endswith(".json"))[-2:]:
        L += sorted((_jl(boc, f) or {}).items())
    return L[-n:]


def verifier(R, D, boc=None):
    S = _jl(D, "summary.json") or {}
    L = [s for s in S.get("secs") or [] if s.get("mkt") == "BRVM" and s.get("cls") == "Equity"]
    if not L:
        R.add("Cohérence : actions BRVM", "rouge", "aucune action BRVM dans summary.json")
        return
    by = {s["id"]: s for s in L}
    M = (_jl(D, "miroir.json") or {}).get("rows") or {}
    FL = (_jl(D, "flottant.json") or {}).get("rows") or {}
    SE = {r["t"]: r for r in (_jl(D, "session.json") or {}).get("rows") or [] if r.get("t")}
    SC = _jl(D, "secteurs.json") or {}

    # 1. fiche / BRVM
    if not M:
        R.add("Fiche / BRVM : nombre de titres", "orange", "miroir.json absent (construction antérieure au 19/10/2026 ?)")
    else:
        out = []
        for t in sorted(by):
            m = M.get(t) or {}
            v = {"fiche": m.get("sh_fiche"), "brvm.org": m.get("sh_brvm"), "avis du flottant": (FL.get(t) or {}).get("sh")}
            vv = {k: x for k, x in v.items() if x}
            if len(vv) >= 2 and max(vv.values()) / min(vv.values()) - 1 > TOL_SH:
                out.append(f"{t} " + ", ".join(f"{k} {_f(x)}" for k, x in vv.items()))
        out, note = _expl(out, "titres", D)
        R.add("Fiche / BRVM : nombre de titres", "orange" if out else "vert",
              ((f"{len(out)} écart(s) à vérifier sur les documents : " + _liste(out)) if out else f"{len(by)} actions, fiche, brvm.org et avis concordent") + note)
        out, out2 = [], []
        for t in sorted(by):
            m = M.get(t) or {}
            a, b, c = m.get("flt_fiche"), m.get("flt_brvm"), (FL.get(t) or {}).get("pct")
            if a is not None and b is not None and abs(a - b) > TOL_FLT:
                out.append(f"{t} fiche {_f(a)} %, brvm.org {_f(b)} %")
            if b is not None and c is not None and abs(b - c) > TOL_FLT:
                out2.append(f"{t} brvm.org {_f(b)} %, avis {_f(c)} %")
        out, note = _expl(out, "flottant", D)
        out2, note2 = _expl(out2, "flottant", D)
        R.add("Fiche / BRVM : flottant (fiche / brvm.org)", "orange" if out else "vert",
              ((f"{len(out)} écart(s) : " + _liste(out)) if out else "concordent") + note)
        R.add("Fiche / BRVM : flottant (brvm.org / avis officiel du flottant)", "orange" if out2 else "vert",
              ((f"{len(out2)} écart(s), à vérifier sur l'avis (le flottant affiché est celui de brvm.org) : " + _liste(out2, 12)) if out2 else "concordent") + note2)
    if not SC.get("rows"):
        R.add("Fiche / BRVM : secteur", "orange", "secteurs officiels pas encore lus (lecture chaque soir sur brvm.org)")
    else:
        off = SC["rows"]
        # secteur affiché = celui de la BRVM (la fiche en secours) : écarts entre la fiche et la BRVM, et secteur affiché différent
        out = [f"{t} fiche « {(M.get(t) or {}).get('sect_fiche')} », BRVM « {off[t]} »" for t in sorted(by)
               if off.get(t) and (M.get(t) or {}).get("sect_fiche") and (M.get(t) or {}).get("sect_fiche") != off[t]]
        out += [f"{t} affiché « {by[t].get('grp')} » au lieu de « {off[t]} »" for t in sorted(by) if off.get(t) and by[t].get("grp") != off[t]]
        absent = [t for t in sorted(by) if t not in off]
        det = (f"{len(out)} écart(s) : " + _liste(out)) if out else f"{len(by) - len(absent)} actions concordent"
        if absent:
            det += f" ; absentes des pages de la BRVM : {', '.join(absent[:8])}"
        R.add("Fiche / BRVM : secteur", "orange" if out or absent else "vert", det + f" (lecture du {SC.get('d') or '—'} ; secteur affiché : celui de la BRVM)")

    # 2. capitalisation
    out = []
    for t, s in sorted(by.items()):
        cg = (SE.get(t) or {}).get("capg")
        if s.get("mcap") and cg and abs(s["mcap"] / cg - 1) > TOL_CAP:
            out.append(f"{t} affichée {_f(s['mcap'] / 1e9, 1)} Md, BRVM {_f(cg / 1e9, 1)} Md")
    R.add("Capitalisation / BRVM", "orange" if out else "vert",
          (f"{len(out)} écart(s) de plus de 2 % : " + _liste(out)) if out else f"{sum(1 for t in by if (SE.get(t) or {}).get('capg'))} capitalisations concordent")

    # 3 et 4. bulletin officiel de la cote
    kb, rows = _boc_dernier(boc)
    if not kb:
        R.add("Cours / bulletin officiel", "orange", "bulletins officiels non fournis au contrôle")
    else:
        out, outp, n = [], [], 0
        for t, s in sorted(by.items()):
            r = rows.get(t)
            if not r:
                continue
            x = _jl(D, f"s/{t}.json") or {}
            d, c = x.get("d") or [], x.get("c") or []
            bc = r[2] if len(r) > 2 and r[2] else (r[6] if len(r) > 6 else None)
            if int(kb) in d and bc:
                n += 1
                v = c[d.index(int(kb))]
                if v and abs(v / bc - 1) > TOL_PX:
                    out.append(f"{t} série {_f(v)}, bulletin {_f(bc)}")
            per = r[11] if len(r) > 11 else None
            if per and per > 0 and bc and s.get("bnpa"):
                b = bc / per
                if abs(s["bnpa"] / b - 1) > TOL_BNPA:
                    outp.append(f"{t} BNPA affiché {_f(s['bnpa'])}, bulletin {_f(b)} (PER {_f(per)})")
        dd = f"{kb[6:8]}/{kb[4:6]}/{kb[:4]}"
        R.add("Cours / bulletin officiel", "rouge" if out else "vert",
              (f"séance du {dd} : {len(out)} cours différent(s) du bulletin : " + _liste(out)) if out else f"séance du {dd} : {n} cours identiques au bulletin")
        R.add("BNPA et PER / bulletin officiel", "orange" if outp else "vert",
              (f"{len(outp)} écart(s) de plus de 2 % : " + _liste(outp)) if outp else f"séance du {dd} : BNPA concordants")

    # 3 bis. volumes des dernières séances / bulletin officiel (montant volume × cours, insensible aux fractionnements) : un volume
    # partiel resté en place (relevé de la base pris en cours de séance) se voit ici
    rec = _boc_recents(boc)
    if rec:
        out, n = [], 0
        for t in sorted(by):
            x = _jl(D, f"s/{t}.json") or {}
            ix = {d: i for i, d in enumerate(x.get("d") or [])}
            for k, rows in rec:
                r = rows.get(t)
                i = ix.get(int(k))
                if not r or i is None or len(r) < 5 or not r[4]:
                    continue
                bc = r[2] or (r[6] if len(r) > 6 else None)
                v, c = (x.get("v") or [])[i], (x.get("c") or [])[i]
                if not bc or not c:
                    continue
                n += 1
                if abs((v or 0) * c / (r[4] * bc) - 1) > .01:
                    out.append(f"{t} {k[6:8]}/{k[4:6]} : {_f(v, 0)} titres, bulletin {_f(r[4], 0)}")
        R.add("Volumes / bulletin officiel", "rouge" if out else "vert",
              (f"{len(out)} volume(s) différent(s) du bulletin sur les {len(rec)} dernières séances : " + _liste(out)) if out
              else f"{n} volumes identiques au bulletin sur les {len(rec)} dernières séances")

    # 3 ter. archive des séances BRVM gardée sur main (seed/brvm_daily.csv) / bulletin officiel : des cours de séance archivés en
    # journée (au lieu de la clôture) y étaient restés (corrigé le 20/10/2026)
    if rec:
        import csv as _csv
        pa = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "seed", "brvm_daily.csv")
        try:
            with open(pa, encoding="utf8") as fh:
                arch = list(_csv.DictReader(fh))
        except OSError:
            arch = []
        bk = dict(rec)
        out, n = [], 0
        for r in arch:
            b_ = (bk.get(r["date"].replace("-", "")) or {}).get(r["ticker"])
            if not b_ or len(b_) < 3 or not b_[2]:
                continue
            n += 1
            if abs(float(r["close"]) / b_[2] - 1) > 1e-6:
                out.append(f"{r['ticker']} {r['date'][8:10]}/{r['date'][5:7]} : {_f(float(r['close']))} / bulletin {_f(b_[2])}")
        if arch:
            R.add("Archive des séances / bulletin officiel", "rouge" if out else "vert",
                  (f"{len(out)} clôture(s) archivée(s) différente(s) du bulletin : " + _liste(out)) if out else f"{n} clôtures archivées identiques au bulletin")

    # 5. BNPA de chaque exercice / résultat net ÷ titres
    F = _jl(D, "fundamentals.json") or {}
    out = []
    for t in sorted(by):
        f = F.get(t) or {}
        se, sh = f.get("series") or {}, f.get("shares")
        for y, v in sorted(((se.get("bnpa") or {}).items())):
            rn = (se.get("resultat_net") or {}).get(y)
            if not y.isdigit() or int(y) < 2015 or v is None or rn is None or not sh or abs(rn) < 1:
                continue
            if (v > 0) != (rn > 0):
                out.append(f"{t} {y} BNPA {_f(v)} pour un résultat de {_f(rn, 0)} M (signe)")
            elif v and not (0.8 < rn * 1e6 / v / sh < 1.25):
                out.append(f"{t} {y} BNPA {_f(v)}, résultat ÷ titres {_f(rn * 1e6 / sh)}")
    out, note = _expl(out, "bnpa", D)
    R.add("BNPA / résultat net ÷ titres", "orange" if out else "vert",
          ((f"{len(out)} exercice(s) à vérifier sur les documents : " + _liste(out, 12)) if out else "concordants (exercices depuis 2015)") + note)

    # 6. dividendes : brut × (1 − impôt) = net
    DV = _jl(D, "dividends.json") or []
    out, n = [], 0
    for x in DV:
        if x.get("brut") and x.get("irvm") is not None and x.get("dps"):
            n += 1
            if abs(x["brut"] * (1 - x["irvm"] / 100) - x["dps"]) > max(.6, x["dps"] * .002):
                out.append(f"{x.get('t')} {x.get('ex')} brut {_f(x['brut'])}, impôt {_f(x['irvm'])} %, net {_f(x['dps'])}")
    R.add("Dividendes : brut, impôt et net", "rouge" if out else "vert",
          (f"{len(out)} versement(s) incohérent(s) : " + _liste(out)) if out else f"{n} versements cohérents")

    # 7. éléments mal formés écartés à la construction (avis, versement, comptes) : à corriger sur le document
    bc = _jl(D, "boc_check.json") or {}
    if "ecartes" not in bc:
        R.add("Éléments écartés à la construction", "orange", "liste absente (construction antérieure au 19/10/2026 ?)")
    else:
        ec = bc.get("ecartes") or []
        R.add("Éléments écartés à la construction", "orange" if ec else "vert",
              (f"{len(ec)} élément(s) mal formé(s) écarté(s), à corriger sur le document : " + _liste(ec)) if ec else "aucun")

    # 7 bis. secours BRVM : fiche des sociétés FQT / base tierce, titre nouveau au bulletin, lectures d'indices douteuses
    Mr = _jl(D, "miroir.json") or {}
    if "soc_diff" in Mr:
        out = (Mr.get("soc_diff") or []) + [f"{t} absent de seed/societes.json (nom et banque pris dans la base)" for t in Mr.get("soc_new") or []]
        R.add("Fiche des sociétés : FQT / base tierce", "orange" if out else "vert",
              (f"{len(out)} écart(s), à vérifier puis à reporter dans seed/societes.json : " + _liste(out)) if out else "noms et type (banque) identiques")
    be = bc.get("base_ext") or {}
    if be:
        R.add("Base tierce : fraîcheur", "orange" if (be.get("age_j") or 0) > 21 else "vert",
              f"dernière mise à jour {be.get('maj') or '—'} ({be.get('age_j')} jours)" + (" : figée, le récent vient des seules sources BRVM" if (be.get("age_j") or 0) > 21 else ""))
    if "nouveaux" in bc:
        nv = bc.get("nouveaux") or []
        R.add("Titres du bulletin officiel absents du terminal", "orange" if nv else "vert",
              ("nouvelle(s) cotation(s) au bulletin, pas encore dans la fiche : " + ", ".join(nv)) if nv else "aucun")
    dt_ = {c: v.get("doute") for c, v in (bc.get("idx") or {}).items() if isinstance(v, dict) and v.get("doute")}
    if bc.get("idx"):
        R.add("Indices / bulletin officiel : lectures douteuses", "orange" if dt_ else "vert",
              ("écart de plus de 5 % (ou saut de plus de 10 %) entre la base et le bulletin, valeur de la base gardée : "
               + _liste([f"{c} {', '.join(str(x) for x in v[-4:])}" for c, v in sorted(dt_.items())])) if dt_ else "aucune")

    # 7 ter. séries quotidiennes en retard sur leur marché (plus de 3 jours ouvrés après la dernière séance la plus récente du même
    # marché) : source arrêtée sans erreur (S&P 500 et Russell 2000 en octobre 2026, change de la Fed avec dix jours de trou)
    import datetime as _dt
    def _bd(a_, b_):
        a2, b2 = _dt.date(a_ // 10000, a_ // 100 % 100, a_ % 100), _dt.date(b_ // 10000, b_ // 100 % 100, b_ % 100)
        return sum(1 for i in range(1, (b2 - a2).days + 1) if (a2 + _dt.timedelta(days=i)).weekday() < 5)
    lastd, ref_m = {}, {}
    for s in S.get("secs") or []:
        if s.get("f", "D") != "D" or "(ancien)" in (s.get("n") or "") or s.get("mkt") in ("CRYPTO",):
            continue
        x = _jl(D, f"s/{str(s['id']).replace('.', '_')}.json") or {}
        if x.get("f", "D") == "D" and x.get("d"):
            lastd[s["id"]] = (s.get("mkt"), x["d"][-1])
            ref_m[s.get("mkt")] = max(ref_m.get(s.get("mkt"), 0), x["d"][-1])
            dd_ = x["d"][-10:]  # (trou de plus de 5 jours ouvrés dans les dix derniers points : source arrêtée puis cours du jour accolé)
            gp_ = max((_bd(dd_[i - 1], dd_[i]) for i in range(1, len(dd_))), default=0)
            if gp_ > 5 and s.get("mkt") != "BRVM":
                lastd[s["id"]] = (s.get("mkt"), x["d"][-1], gp_)
    late = sorted(f"{k} ({v[1] % 100:02d}/{v[1] // 100 % 100:02d})" for k, v in lastd.items() if _bd(v[1], ref_m[v[0]]) > 3)
    late += sorted(f"{k} (trou de {v[2]} jours ouvrés)" for k, v in lastd.items() if len(v) > 2)
    R.add("Séries quotidiennes en retard sur leur marché", "orange" if late else "vert",
          (f"{len(late)} série(s) arrêtée(s) depuis plus de 3 jours ouvrés : " + _liste(late, 15)) if late else f"{len(lastd)} séries à jour")

    # 8. valeurs extrêmes à revoir à la main (pas forcément fausses)
    out = []
    for t, s in sorted(by.items()):
        if s.get("yld") and s["yld"] > .25:
            out.append(f"{t} rendement {_f(s['yld'] * 100, 1)} %")
        if s.get("pay") and s["pay"] > 3:
            out.append(f"{t} distribution {_f(s['pay'] * 100, 0)} %")
        if s.get("per") is not None and (s["per"] <= 0 or s["per"] > 150):
            out.append(f"{t} PER {_f(s['per'], 1)}")
    R.add("Valeurs extrêmes à revoir", "orange" if out else "vert",
          (f"{len(out)} valeur(s) à regarder (pas forcément fausses) : " + _liste(out, 12)) if out else "aucune")
