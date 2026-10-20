"""Contrôle des données publiées du terminal (et, si fourni, du parcours du site) : rapport vert / orange / rouge.

Usage :
  python3 controle.py <dossier data/> <rapport.json> [--ref <instantané précédent .json>] [--md <rapport.md>]
                      [--site <parcours.json>] [--mobile <mobile.json>] [--qlab <qlab.log>] [--interdits <sortie de mots_interdits>]
                      [--meme-donnees] [--maintenant <horodatage unix>]

- Ne modifie rien : il lit les fichiers et écrit un rapport. Code de sortie toujours 0 (une vérification qui ne passe pas
  donne un rapport orange ou rouge, jamais un échec de l'automatisation).
- --ref : instantané d'un contrôle précédent (champ « instantane » d'un rapport) pour comparer les nombres de lignes et les
  chiffres clés. --meme-donnees : la référence a été faite sur les mêmes données (essai avant / après une modification du
  code) : tout chiffre clé changé est alors signalé.
- Vert : tout va bien. Orange : à regarder (rien de bloquant). Rouge : problème à corriger avant de publier.
"""
import argparse, collections, glob, hashlib, json, math, os, re, sys, time

NIV = {"vert": 0, "orange": 1, "rouge": 2}
ESSENTIELS = ["summary.json", "quotes.json", "live.json", "session.json", "fundamentals.json", "dividends.json", "events.json",
              "events_recent.json", "news.json", "search.json", "fa_index.json", "qlab/index.json", "calendar.json", "bonds.json",
              "boc_check.json", "profiles.json", "ratings.json", "weekly.json", "breadth.json", "world_mkt.json", "eco.json",
              "anomalies.json", "liq.json", "reports.json", "avis_brvm.json", "per.json", "flottant.json"]
INDICES_BRVM = ["BRVMC", "BRVM30", "BRVMPR"]
# Retirés volontairement (ne pas les réclamer) : QLAB Prévisions, retiré le 19/10/2026 à la demande du propriétaire.
RETIRES = ("qlabp/",)
# Noms qui ne doivent jamais apparaître dans la page ni dans les données servies au navigateur : leurs empreintes sont dans
# interdits.sha (les noms eux-mêmes ne sont pas écrits dans le dépôt).
SOURCES = re.compile(r"sika ?finance|richbourse|afribourse|brvmetrics|github|vercel\.app|@gmail|web\.archive\.org|wayback", re.I)
SUSPECT = re.compile(r"\bNaN\b|\bundefined\b|\bInfinity\b|\[object Object\]|\bnull\b")
# Symboles qu'un iPhone peut afficher en émoji (propriété Unicode « Emoji ») lorsqu'ils ne sont pas suivis du sélecteur
# de texte U+FE0E. Les flèches simples ↑ ↓ ← → et les symboles ★ ● ■ ▲ ▼ ne sont pas concernés.
EMOJI = re.compile("(?:[‼⁉ℹ↔-↙↩↪⌚⌛⌨⏏⏩-⏳⏸-⏺"
                   "Ⓜ▪▫▶◀◻-◾☀-☄☎☑☔☕☘☝☠"
                   "☢☣☦☪☮☯☸-☺♀♂♈-♓♟♠♣♥"
                   "♦♨♻♾♿⚒-⚗⚙⚛⚜⚠⚡⚧⚪⚫⚰⚱"
                   "⚽⚾⛄⛅⛈⛎⛏⛑⛓⛔⛩⛪⛰-⛵⛷-⛺⛽"
                   "✂✅✈-✍✏✒✔✖✝✡✨✳✴❄❇❌❎"
                   "❓-❕❗❣❤➕-➗➡➰➿⤴⤵⬅-⬇⬛⬜"
                   "⭐⭕〰〽㊗㊙]|[\U0001F000-\U0001FAFF])(?!︎)")


class Rapport:
    def __init__(self):
        self.v = []

    def add(self, nom, niveau, detail):
        self.v.append({"nom": nom, "niveau": niveau, "detail": detail})

    @property
    def niveau(self):
        return max((x["niveau"] for x in self.v), key=NIV.get, default="vert")


def charge(path):
    try:
        if os.path.getsize(path) == 0:
            return None, "vide"
        with open(path, encoding="utf8") as fh:
            return json.load(fh), None
    except FileNotFoundError:
        return None, "absent"
    except Exception as e:  # noqa: BLE001
        return None, f"illisible ({type(e).__name__})"


def _empreintes():
    """Empreintes des noms interdits, lues dans outils/controle/interdits.sha (une par ligne)."""
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interdits.sha")
    try:
        return {l.strip() for l in open(f, encoding="utf8") if re.fullmatch(r"[0-9a-f]{64}", l.strip())}
    except FileNotFoundError:
        return set()


def interdits_dans(texte, emp):
    if not emp:
        return []
    out = set()
    for tok in re.split(r"[^a-z0-9\-]+", texte.lower()):
        for t in {tok, tok.strip("-")}:
            if len(t) >= 4 and hashlib.sha256(t.encode()).hexdigest() in emp:
                out.add(t[:2] + "…")
    return sorted(out)


def num_ok(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def controle_donnees(D, R, maintenant):
    """Présence, lisibilité, fraîcheur, doublons, valeurs aberrantes, cohérence. Rend l'instantané (comptages, chiffres clés)."""
    J = {}
    # 1) présence et lisibilité
    manquants, illisibles = [], []
    for f in ESSENTIELS:
        d, err = charge(os.path.join(D, f))
        if err:
            (manquants if err == "absent" else illisibles).append(f"{f} ({err})" if err != "absent" else f)
        else:
            J[f] = d
    tous = [p for p in glob.glob(os.path.join(D, "**", "*.json"), recursive=True)]
    for p in tous:
        rel = os.path.relpath(p, D)
        if rel in J or rel.startswith(RETIRES):
            continue
        d, err = charge(p)
        if err:
            illisibles.append(f"{rel} ({err})")
    R.add("Fichiers essentiels présents", "rouge" if manquants else "vert",
          ("absents : " + ", ".join(manquants)) if manquants else f"{len(ESSENTIELS)} fichiers présents")
    R.add("Fichiers lisibles et non vides", "rouge" if illisibles else "vert",
          ("; ".join(illisibles[:15]) + (f" … (+{len(illisibles) - 15})" if len(illisibles) > 15 else "")) if illisibles
          else f"{len(tous)} fichiers JSON lus")
    retires = [os.path.relpath(p, D) for p in tous if os.path.relpath(p, D).startswith(RETIRES)]
    if retires:
        R.add("Fichiers retirés encore publiés", "orange",
              f"{len(retires)} fichiers de QLAB Prévisions (retiré) encore dans les données ; ils partent au prochain passage")

    S = J.get("summary.json") or {}
    secs = S.get("secs") or []
    by = {x.get("id"): x for x in secs}
    brvm = [x for x in secs if x.get("mkt") == "BRVM" and x.get("cls") == "Equity"]

    # 2) fraîcheur (heures)
    def age(ts):
        return (maintenant - ts) / 3600 if num_ok(ts) and ts > 1e9 else None
    fr = []
    for nom, ts, o, r in (("relevé du terminal (live)", (J.get("live.json") or {}).get("ts"), 1.5, 6),
                          ("cours (quotes)", (J.get("quotes.json") or {}).get("ts"), 1.5, 6),
                          ("base (summary)", S.get("built"), 1.5, 6),
                          ("actualités (news)", (J.get("news.json") or {}).get("ts"), 3, 24)):
        a = age(ts)
        if a is None:
            fr.append(("rouge", f"{nom} : date absente"))
        elif a > r:
            fr.append(("rouge", f"{nom} : {a:.1f} h"))
        elif a > o:
            fr.append(("orange", f"{nom} : {a:.1f} h"))
    jd = time.gmtime(maintenant)
    qi = J.get("qlab/index.json") or {}
    for nom, d8, lim in (("séance BRVM (session)", str((J.get("session.json") or {}).get("asof", "")).replace("-", ""), 4),
                         ("valorisation QLAB (soir)", str(qi.get("date", "")), 5)):
        try:
            t = time.mktime(time.strptime(d8[:8], "%Y%m%d"))
            j = (maintenant - t) / 86400
            if j > lim:
                fr.append(("orange", f"{nom} : {d8[:4]}-{d8[4:6]}-{d8[6:8]} ({j:.0f} jours)"))
        except Exception:  # noqa: BLE001
            fr.append(("orange", f"{nom} : date illisible"))
    R.add("Fraîcheur des données", max((x[0] for x in fr), key=NIV.get, default="vert"),
          "; ".join(x[1] for x in fr) if fr else "à jour (cours du " + (time.strftime('%d/%m/%Y %H:%M', time.gmtime((J.get("quotes.json") or {}).get("ts")))
                                                    if num_ok((J.get("quotes.json") or {}).get("ts")) else "—") + " UTC)")

    # 3) comptages
    E = J.get("events.json") or []
    DV = J.get("dividends.json") or []
    N = (J.get("news.json") or {}).get("items") or []
    SR = (J.get("search.json") or {}).get("r") or []
    C = {
        "titres": len(secs), "actions BRVM": len(brvm), "événements": len(E), "dividendes": len(DV), "actualités": len(N),
        "documents (MOTS CLES)": len(SR), "fichiers FA": len(glob.glob(os.path.join(D, "fa", "*.json"))),
        "séries de cours": len(glob.glob(os.path.join(D, "s", "*.json"))),
        "valorisations QLAB": len(qi.get("rows") or []), "obligations": len((J.get("bonds.json") or {}).get("rows") or []),
        "calendrier éco": len((J.get("calendar.json") or {}).get("rows") or []),
        "notations": len((J.get("ratings.json") or {}).get("rows") or []),
        "avis BRVM": len((J.get("avis_brvm.json") or {}).get("items") or {}),
        "fondamentaux": len(J.get("fundamentals.json") or {}), "fiches sociétés": len(J.get("profiles.json") or {}),
    }
    pb = []
    if len(brvm) < 48:
        pb.append(("rouge", f"{len(brvm)} actions BRVM au lieu de 48"))
    absents_idx = [i for i in INDICES_BRVM if i not in by]
    if absents_idx:
        pb.append(("rouge", "indices absents : " + ", ".join(absents_idx)))
    R.add("Univers BRVM complet", max((x[0] for x in pb), key=NIV.get, default="vert"),
          "; ".join(x[1] for x in pb) if pb else "48 actions et 3 indices")

    # 4) doublons
    def dups(it, key):
        c = collections.Counter(key(x) for x in it)
        return sum(v - 1 for v in c.values() if v > 1)
    DU = {
        "événements": dups(E, lambda x: (x.get("t"), x.get("d"), x.get("ti"), x.get("u"))),
        "dividendes": dups(DV, lambda x: (x.get("t"), x.get("ex"), x.get("dps"), x.get("pay"))),
        "actualités": dups(N, lambda x: x.get("u")),
        "documents (MOTS CLES)": dups(SR, lambda r: tuple(r[:5]) if isinstance(r, list) else r),
        "calendrier éco": dups((J.get("calendar.json") or {}).get("rows") or [], lambda x: (x.get("d"), x.get("c"), x.get("t"))),
    }

    # 5) valeurs aberrantes
    ab = []
    for x in secs:
        if not num_ok(x.get("last")) or x["last"] <= 0:
            ab.append(("rouge", f"{x.get('id')} : cours {x.get('last')}"))
        p = x.get("pct")
        if num_ok(p):
            if x in brvm and abs(p) > 0.0751:
                ab.append(("orange", f"{x['id']} : variation {p * 100:+.1f} % (limite BRVM 7,5 %)"))
            elif x.get("mkt") == "US" and abs(p) > 0.4:
                ab.append(("orange", f"{x['id']} : variation {p * 100:+.1f} %"))
    for t, q in ((J.get("quotes.json") or {}).get("q") or {}).items():
        if not num_ok(q.get("last")) or q["last"] <= 0:
            ab.append(("rouge", f"cours relevé {t} : {q.get('last')}"))
    for x in DV:
        if not num_ok(x.get("dps")) or x["dps"] <= 0:
            ab.append(("orange", f"dividende {x.get('t')} {x.get('ex')} : {x.get('dps')}"))
    for x in qi.get("rows") or []:
        if x.get("ok") and (not num_ok(x.get("v")) or x["v"] <= 0):
            ab.append(("orange", f"QLAB {x.get('t')} : valeur {x.get('v')}"))
    R.add("Valeurs aberrantes", max((x[0] for x in ab), key=NIV.get, default="vert"),
          "; ".join(x[1] for x in ab[:12]) + (f" … (+{len(ab) - 12})" if len(ab) > 12 else "") if ab else "aucune")

    # 6) cohérence entre fichiers
    co = []
    sans_serie = [x["id"] for x in secs if x.get("id") and not os.path.exists(os.path.join(D, "s", x["id"] + ".json"))]
    if sans_serie:
        co.append(("orange", f"{len(sans_serie)} titres sans série de cours ({', '.join(sans_serie[:6])})"))
    fa_ids = [r.get("id") for r in (J.get("fa_index.json") or {}).get("rows") or []]
    sans_fa = [i for i in fa_ids if i and not os.path.exists(os.path.join(D, "fa", i + ".json"))]
    if sans_fa:
        co.append(("orange", f"{len(sans_fa)} titres de FA sans fichier ({', '.join(sans_fa[:6])})"))
    sans_q = [r.get("t") for r in qi.get("rows") or [] if r.get("t") and not os.path.exists(os.path.join(D, "qlab", r["t"] + ".json"))]
    if sans_q:
        co.append(("orange", f"{len(sans_q)} valorisations QLAB sans fiche ({', '.join(sans_q[:6])})"))
    ids_brvm = {x["id"] for x in brvm}
    hors = [k for k in (J.get("fundamentals.json") or {}) if k not in ids_brvm]
    if hors:
        co.append(("orange", f"fondamentaux hors des 48 actions : {', '.join(hors[:6])}"))
    sess = {r.get("t") for r in (J.get("session.json") or {}).get("rows") or []}
    if sess and len(sess & ids_brvm) < 48:
        co.append(("orange", f"séance BRVM : {len(sess & ids_brvm)} actions sur 48"))
    ecarts = []
    qd = (J.get("quotes.json") or {}).get("q") or {}
    for i, q in qd.items():
        s = by.get(i)
        if s and num_ok(q.get("last")) and num_ok(s.get("last")) and s["last"] > 0 and q.get("d") and \
                str(s.get("dt")) == q["d"].replace("-", "") and abs(q["last"] / s["last"] - 1) > 0.02:
            ecarts.append(f"{i} {q['last']} / {s['last']}")
    if ecarts:
        co.append(("orange", f"cours relevé ≠ base le même jour : {', '.join(ecarts[:6])}"))
    R.add("Cohérence entre fichiers", max((x[0] for x in co), key=NIV.get, default="vert"),
          "; ".join(x[1] for x in co) if co else "séries, FA, QLAB, fondamentaux et séance concordent")

    # 7) chiffres clés (instantané)
    F = J.get("fundamentals.json") or {}
    K = {}
    for x in brvm:
        i = x["id"]
        k = {"cours": x.get("last")}
        f = F.get(i) or {}
        k["actions"] = f.get("shares")
        for m in ("ca", "resultat_net", "bnpa", "dividende"):
            ser = (f.get("series") or {}).get(m)
            if isinstance(ser, dict) and ser:
                y = max(ser, key=lambda z: str(z))
                k[m] = [y, ser[y]]
            elif isinstance(ser, list) and ser:
                k[m] = ser[-1]
        K[i] = k
    for r in qi.get("rows") or []:
        if r.get("t") in K:
            K[r["t"]]["qlab"] = [r.get("p10"), r.get("v"), r.get("p90")]
    return {"comptages": C, "doublons": DU, "chiffres": K}


def compare(R, inst, ref, meme):
    if not ref:
        R.add("Comparaison avec le contrôle précédent", "vert", "pas de référence (premier contrôle)")
        idp = inst["doublons"]
        R.add("Doublons", "vert", ("relevés : " + ", ".join(f"{k} {v}" for k, v in idp.items() if v) +
                                    " (comparés au prochain contrôle)") if any(idp.values()) else "aucun")
        return
    rc, ic = ref.get("comptages") or {}, inst["comptages"]
    baisses = []
    for k, v in ic.items():
        a = rc.get(k)
        if isinstance(a, int) and a > 0 and v < a:
            b = 1 - v / a
            baisses.append(("rouge" if b > .10 else "orange" if b > .02 else "vert", f"{k} : {a} → {v} ({-b * 100:.1f} %)"))
    hausses = [f"{k} : {rc.get(k)} → {v}" for k, v in ic.items() if isinstance(rc.get(k), int) and v > rc[k]]
    niv = max((x[0] for x in baisses), key=NIV.get, default="vert")
    det = "; ".join(x[1] for x in baisses if x[0] != "vert") or "aucune baisse notable"
    if hausses:
        det += " · en hausse : " + "; ".join(hausses[:8])
    R.add("Nombre de lignes comparé au contrôle précédent", niv, det)
    rd, idp = ref.get("doublons") or {}, inst["doublons"]
    plus = [f"{k} : {rd.get(k, 0)} → {v}" for k, v in idp.items() if v > (rd.get(k) or 0)]
    R.add("Doublons", "orange" if plus else "vert",
          ("nouveaux doublons — " + "; ".join(plus)) if plus else
          "aucun nouveau doublon (" + ", ".join(f"{k} {v}" for k, v in idp.items() if v) + ")" if any(idp.values()) else "aucun")
    rk, ik = ref.get("chiffres") or {}, inst["chiffres"]
    ch = []
    for t, k in ik.items():
        a = rk.get(t) or {}
        for m, v in k.items():
            if m == "cours" and not meme:
                continue
            if m in a and a[m] != v:
                ch.append(f"{t} {m} : {a[m]} → {v}")
        for m in a:
            if m not in k:
                ch.append(f"{t} {m} : {a[m]} → retiré")
    retires = [t for t in rk if t not in ik]
    if retires:
        ch.append("titres disparus : " + ", ".join(retires))
    if meme:
        R.add("Chiffres clés (mêmes données avant / après)", "orange" if ch else "vert",
              ("changés : " + "; ".join(ch[:12]) + (f" … (+{len(ch) - 12})" if len(ch) > 12 else "")) if ch else
              f"{len(ik)} actions : aucun chiffre clé changé")
    else:
        R.add("Chiffres clés depuis le contrôle précédent", "orange" if retires else "vert",
              (f"{len(ch)} changements (nouvelles publications, séance, valorisations)" + (" : " + "; ".join(ch[:6]) if ch else ""))
              if ch else "aucun changement")


def controle_site(R, a):
    if a.site:
        P, err = charge(a.site)
        if err:
            R.add("Parcours du site", "rouge", f"résultat du parcours {err}")
        else:
            pages = P.get("pages") or {}
            errs = P.get("errs") or []
            R.add("Parcours du site : erreurs JavaScript", "rouge" if errs else "vert",
                  (f"{len(errs)} erreurs : " + "; ".join(f"{h} {e[:90]}" for h, e in errs[:6])) if errs else
                  f"{len(pages)} pages et onglets, aucune erreur")
            sus, src, emo, emo_c = [], [], [], collections.Counter()
            emp = _empreintes()
            priv = set()
            for h, v in pages.items():
                blob = "\n".join([v.get("text", "")] + (v.get("titles") or []) + [" ".join(map(str, l)) for l in (v.get("links") or [])])
                for l in blob.splitlines():
                    if SUSPECT.search(l):
                        sus.append(f"{h} | {l.strip()[:100]}")
                    if SOURCES.search(l):
                        src.append(f"{h} | {l.strip()[:100]}")
                    for m in EMOJI.finditer(l):
                        emo_c[m.group(0)] += 1
                        if len(emo) < 8:
                            emo.append(f"{h} | {m.group(0)} U+{ord(m.group(0)[0]):04X}")
                priv.update(interdits_dans(blob, emp))
            R.add("Parcours du site : textes suspects (NaN, undefined, null…)", "rouge" if sus else "vert",
                  ("; ".join(sus[:6]) + (f" … (+{len(sus) - 6})" if len(sus) > 6 else "")) if sus else "aucun")
            R.add("Parcours du site : noms de sources et liens interdits", "rouge" if src else "vert",
                  ("; ".join(src[:6]) + (f" … (+{len(src) - 6})" if len(src) > 6 else "")) if src else "aucun")
            R.add("Parcours du site : symboles affichés en émoji sur iPhone", "orange" if emo_c else "vert",
                  ("; ".join(f"{c} U+{ord(c[0]):04X} ×{n}" for c, n in emo_c.most_common(12))) if emo_c else "aucun")
            R.add("Confidentialité (page)", "rouge" if priv else "vert",
                  ("noms interdits trouvés : " + ", ".join(sorted(priv))) if priv else
                  ("aucun nom interdit" if emp else "liste des noms interdits absente (interdits.sha)"))
    if a.mobile:
        M, err = charge(a.mobile)
        if err:
            R.add("iPhone 13", "orange", f"résultat {err}")
        else:
            P = M.get("pages") or {}
            ov = sorted(((h, v.get("over")) for h, v in P.items() if v.get("over")), key=lambda x: -x[1])
            sus = [(h, v.get("bad")) for h, v in P.items() if v.get("bad")]
            vid = [h for h, v in P.items() if (v.get("len") or 0) < 150]
            ej = M.get("errs") or []
            pb = (["erreurs JavaScript : " + "; ".join(str(e)[:80] for e in ej[:3])] if ej else []) + \
                 (["débordement horizontal : " + ", ".join(f"{h} ({o} px)" for h, o in ov[:6])] if ov else []) + \
                 (["textes suspects : " + ", ".join(f"{h} {b}" for h, b in sus[:4])] if sus else []) + \
                 (["pages vides : " + ", ".join(vid[:6])] if vid else [])
            R.add("iPhone 13 : erreurs, débordements, textes", "rouge" if (ej or sus) else "orange" if (ov or vid) else "vert",
                  "; ".join(pb) if pb else f"{len(P)} pages sans erreur ni débordement")
    if a.qlab:
        try:
            L = open(a.qlab, encoding="utf8").read()
            m1 = re.search(r"erreurs JS (\[.*?\])", L)
            m2 = re.search(r"textes suspects (\d+)", L)
            m3 = re.search(r"pages (\d+)", L)
            ej = m1.group(1) if m1 else "?"
            ns = int(m2.group(1)) if m2 else -1
            R.add("QLAB (48 actions)", "vert" if ej == "[]" and ns == 0 else "rouge",
                  f"{m3.group(1) if m3 else '?'} vues, erreurs JavaScript {ej[:120]}, textes suspects {ns}")
        except FileNotFoundError:
            R.add("QLAB (48 actions)", "orange", "résultat absent")


def ecrire_md(R, inst, path, titre):
    L = [f"# {titre}", "", f"**Résultat : {R.niveau.upper()}**", "", "| Vérification | Résultat | Détail |",
         "|---|---|---|"]
    for x in R.v:
        L.append(f"| {x['nom']} | {x['niveau']} | {str(x['detail']).replace('|', '/')} |")
    L += ["", "Comptages : " + ", ".join(f"{k} {v}" for k, v in inst["comptages"].items())]
    open(path, "w", encoding="utf8").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("out")
    ap.add_argument("--ref"); ap.add_argument("--md"); ap.add_argument("--site"); ap.add_argument("--mobile"); ap.add_argument("--qlab")
    ap.add_argument("--meme-donnees", action="store_true"); ap.add_argument("--maintenant", type=float)
    ap.add_argument("--titre", default="Contrôle du terminal")
    ap.add_argument("--runs", help="passages GitHub des dernières 24 h (JSON), pour les bugs corrigés")
    ap.add_argument("--comptes", help="index.json de la branche comptes, pour les bugs corrigés")
    ap.add_argument("--boc", help="dossier des bulletins officiels de l'année (boc_px), pour les contrôles de cohérence")
    a = ap.parse_args()
    maintenant = a.maintenant or time.time()
    R = Rapport()
    try:
        inst = controle_donnees(a.data, R, maintenant)
    except Exception as e:  # noqa: BLE001
        R.add("Contrôle des données", "rouge", f"contrôle interrompu : {type(e).__name__} {e}")
        inst = {"comptages": {}, "doublons": {}, "chiffres": {}}
    ref = None
    if a.ref:
        d, err = charge(a.ref)
        ref = (d or {}).get("instantane") if d and "instantane" in d else d
        if err:
            R.add("Comparaison avec le contrôle précédent", "orange", f"référence {err}")
    try:
        compare(R, inst, ref, a.meme_donnees)
    except Exception as e:  # noqa: BLE001
        R.add("Comparaison avec le contrôle précédent", "orange", f"comparaison interrompue : {e}")
    # cohérence des chiffres : fiche / BRVM, bulletin officiel, BNPA, dividendes, valeurs extrêmes (outils/controle/coherence.py)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import coherence
        coherence.verifier(R, a.data, a.boc)
    except Exception as e:  # noqa: BLE001
        R.add("Cohérence des chiffres", "orange", f"contrôle interrompu : {type(e).__name__} {e}")
    try:
        controle_site(R, a)
    except Exception as e:  # noqa: BLE001
        R.add("Contrôle du site", "orange", f"contrôle interrompu : {e}")
    # bugs corrigés : ils ne doivent jamais revenir (outils/controle/non_retour.py)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import non_retour
        pages = ((charge(a.site)[0] or {}).get("pages") if a.site else None)
        runs = charge(a.runs)[0] if a.runs else None
        if isinstance(runs, dict):
            runs = runs.get("workflow_runs") or runs.get("runs") or []
        ci = charge(a.comptes)[0] if a.comptes else None
        non_retour.verifier(R, {"D": a.data, "pages": pages, "inst": inst, "maintenant": maintenant, "runs": runs, "comptes": ci})
    except Exception as e:  # noqa: BLE001
        R.add("Bugs corrigés", "orange", f"contrôle interrompu : {type(e).__name__} {e}")
    res = {"niveau": R.niveau, "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(maintenant)), "verifications": R.v,
           "instantane": inst}
    json.dump(res, open(a.out, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    if a.md:
        ecrire_md(R, inst, a.md, a.titre)
    print(f"Contrôle : {R.niveau.upper()}")
    for x in R.v:
        if x["niveau"] != "vert":
            print(f"  [{x['niveau']}] {x['nom']} : {str(x['detail'])[:300]}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"Contrôle impossible : {e}")
        sys.exit(0)
