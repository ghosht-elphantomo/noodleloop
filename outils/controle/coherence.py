"""Contrôles de cohérence du contrôle du matin (demandés par le propriétaire le 19/10/2026) : chaque chiffre important est
comparé à une seconde source officielle, ou à lui-même par un autre chemin. Rien n'est corrigé ici : un écart est signalé,
avec les valeurs côte à côte, pour être vérifié sur le document avant de toucher au chiffre affiché.

  1. fiche / BRVM : nombre de titres, flottant, secteur (miroir.json, flottant.json, secteurs.json) ;
  2. capitalisation affichée (cours × titres) / capitalisation publiée par la BRVM (session.json) ;
  3. dernier cours de la série / clôture du bulletin officiel de la cote (même séance) ;
  4. BNPA affiché / BNPA du bulletin officiel (cours ÷ PER) ;
  5. BNPA de chaque exercice / résultat net ÷ nombre de titres ;
  6. dividende : brut × (1 − impôt) = net ;
  7. éléments mal formés écartés à la construction ;
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
