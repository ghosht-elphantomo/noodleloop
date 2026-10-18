"""Données prises à l'extérieur (base BRVMetrics, archives SikaFinance, fiches des sociétés) : une valeur déjà enregistrée
n'est jamais perdue. La copie précédente est fusionnée dans la nouvelle : tout ce que la nouvelle n'a plus (titre, exercice,
séance, avis, champ) est repris de l'ancienne ; une valeur nouvelle ou corrigée l'emporte. Si la source bloque, ne répond
plus ou renvoie moins de données, rien ne disparaît.

Usage : sticky.py base ANCIEN NOUVEAU        dossiers de la base (NOUVEAU complété sur place)
        sticky.py json ANCIEN NOUVEAU        un fichier JSON (fiches, archives) : NOUVEAU complété sur place
        sticky.py instantane SOURCE DOSSIER  copie permanente (branche histo) : SOURCE fusionnée dans DOSSIER
Bibliothèque standard uniquement. Sortie : une ligne de bilan (et une annotation si des données ont été reprises).
"""
import csv, io, json, os, re, shutil, sys

EMPTY = (None, "", [], {})


def load(p):
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def dump(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, p)


def merge_obj(old, new, n):
    """Fusion récursive de dictionnaires : clés absentes ou vides dans le nouveau reprises de l'ancien."""
    if not isinstance(old, dict) or not isinstance(new, dict):
        return new if new not in EMPTY else old
    out = dict(new)
    for k, ov in old.items():
        if k not in out or out[k] in EMPTY:
            if ov not in EMPTY:
                out[k] = ov
                n[0] += 1
        elif isinstance(ov, dict) and isinstance(out[k], dict):
            out[k] = merge_obj(ov, out[k], n)
    return out


def merge_list(old, new, key, n):
    """Listes d'enregistrements : ceux que le nouveau n'a plus (même clé) sont repris, à la fin."""
    seen = {key(x) for x in new if isinstance(x, dict)}
    out = list(new)
    for x in old:
        if isinstance(x, dict) and key(x) not in seen:
            out.append(x)
            seen.add(key(x))
            n[0] += 1
    return out


def rec_key(x):
    return x.get("id") or json.dumps({k: x.get(k) for k in ("ticker", "category", "title", "published_at", "document_url", "exercice", "date_paiement")},
                                     sort_keys=True, ensure_ascii=False)


def merge_json(po, pn, n):
    o, nw = load(po), load(pn)
    if isinstance(o, dict) and isinstance(nw, dict):
        for lk in ("actions", "events", "all"):  # (listes d'enregistrements de la base)
            if isinstance(o.get(lk), list) and isinstance(nw.get(lk), list):
                key = (lambda x: x.get("ticker") or x.get("symbole")) if lk == "actions" else rec_key
                nw[lk] = merge_list(o[lk], nw[lk], key, n)
        res = merge_obj({k: v for k, v in o.items() if k not in ("actions", "events", "all", "_meta")},
                        {k: v for k, v in nw.items() if k not in ("actions", "events", "all", "_meta")}, n)
        for k in ("actions", "events", "all", "_meta"):
            if k in nw:
                res[k] = nw[k]
            elif k in o:
                res[k] = o[k]
        nw = res
    elif isinstance(o, list) and isinstance(nw, list):
        nw = merge_list(o, nw, rec_key, n)
    dump(pn, nw)


def dkey(s):
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s or "")
    return (int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else (9999, 0, 0)


def merge_csv(po, pn, n):
    """Historique de cours (une ligne par séance, date en première colonne) : séances disparues reprises de l'ancien."""
    def read(p):
        with open(p, encoding="utf-8-sig", newline="") as f:
            txt = f.read()
        lines = txt.splitlines()
        return (lines[0] if lines else ""), [ln for ln in lines[1:] if ln.strip()]
    ho, ro = read(po)
    hn, rn = read(pn)
    if ho.strip() != hn.strip():
        shutil.copy2(po, pn + ".ancien")  # (format changé par la source : l'ancien fichier est gardé à côté, rien n'est mélangé)
        return
    have = {ln.split(";", 1)[0] for ln in rn}
    add = [ln for ln in ro if ln.split(";", 1)[0] not in have]
    if not add:
        return
    n[0] += len(add)
    rows = sorted(rn + add, key=lambda ln: dkey(ln.split(";", 1)[0]))
    tmp = pn + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        f.write(hn + "\n" + "\n".join(rows) + "\n")
    os.replace(tmp, pn)


def merge_dir(old, new):
    """Dossier de la base : fichiers JSON et CSV fusionnés, fichiers disparus repris."""
    n, files, kept = [0], 0, 0
    for root, _, fs in os.walk(old):
        for f in fs:
            po = os.path.join(root, f)
            rel = os.path.relpath(po, old)
            if rel.startswith(".git"):
                continue
            pn = os.path.join(new, rel)
            if not os.path.exists(pn):
                os.makedirs(os.path.dirname(pn), exist_ok=True)
                shutil.copy2(po, pn)
                kept += 1
                continue
            files += 1
            try:
                if f.endswith(".json") and f not in ("seance.json", "trading_status.json", "boc.json", "prix_confirmes.json", "prix_ecartes.json"):
                    merge_json(po, pn, n)
                elif f.endswith(".csv"):
                    merge_csv(po, pn, n)
            except Exception as e:  # noqa: BLE001
                print(f"::warning::Fusion impossible de {rel} : {e} (nouveau fichier gardé tel quel)")
    return n[0], files, kept


def main():
    mode, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
    if mode == "base":
        if not os.path.isdir(a):
            print("Pas de copie précédente : rien à fusionner")
            return
        nv, files, kept = merge_dir(a, b)
        msg = f"Base extérieure : {files} fichiers fusionnés avec la copie précédente, {nv} valeurs ou lignes reprises, {kept} fichiers disparus repris"
    elif mode == "json":
        if not os.path.exists(a):
            print("Pas de copie précédente : rien à fusionner")
            return
        if not os.path.exists(b):
            shutil.copy2(a, b)
            nv, msg = -1, f"{os.path.basename(b)} absent : copie précédente reprise en entier"
        else:
            n = [0]
            merge_json(a, b, n)
            nv, msg = n[0], f"{os.path.basename(b)} : {n[0]} valeurs reprises de la copie précédente"
    elif mode == "instantane":
        # copie permanente : le dossier DOSSIER (branche histo) reçoit la source fusionnée avec ce qu'il avait déjà
        os.makedirs(b, exist_ok=True)
        tmp = b + ".nouveau"
        if os.path.exists(tmp):
            shutil.rmtree(tmp)
        shutil.copytree(a, tmp)
        nv, files, kept = merge_dir(b, tmp)
        shutil.rmtree(b)
        os.replace(tmp, b)
        msg = f"Copie permanente : {files} fichiers à jour, {nv} valeurs reprises, {kept} fichiers gardés"
    else:
        raise SystemExit("mode inconnu : " + mode)
    print(("::notice::" if nv else "") + msg)


if __name__ == "__main__":
    main()
