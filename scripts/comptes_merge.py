"""Lecture des comptes répartie sur plusieurs machines (comptes.yml) : mise en commun et contrôles avant publication.

Chaque machine lit sa part des documents (fetch_extra.py, CPT_SHARDS / CPT_SHARD : la part d'un document dépend de son
adresse et ne change jamais, aucun document n'est lu deux fois) dans sa propre copie de la branche `comptes`, puis
`pack` ne garde que ce qu'elle a lu ou relu. `merge` rassemble les parts dans la branche restaurée et refuse tout mélange :
document lu par une autre part que la sienne, document présent dans deux parts, fichier de texte sans document. `sample`
choisit quelques documents lus pendant ce passage, que la machine de publication relit seule, à l'ancienne façon ; `compare`
exige des textes identiques. `check` exige que la lecture des postes de tous les documents qui n'ont pas été touchés reste
exactement la même (comptes.json avant / après). Un contrôle en échec = rien n'est publié (comptes.yml).
"""
import argparse, gzip, hashlib, json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load(p, default=None):
    try:
        with open(p, encoding="utf8") as f:
            return json.load(f)
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def dump(p, obj):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def h_of(u):
    return hashlib.sha1(u.encode()).hexdigest()[:16]


def txt_files(d, h):
    t = os.path.join(d, "txt")
    return sorted(f for f in (os.listdir(t) if os.path.isdir(t) else []) if f.startswith(h + "."))


def note(kind, msg):
    """Annotation GitHub (lisible dans le résumé du passage) et ligne de journal."""
    print(f"::{kind}::{msg}" if kind in ("error", "warning", "notice") else msg, flush=True)


def cmd_pack(a):
    """Ce que cette machine a lu ou relu : les fiches du registre qui ont changé et leurs fichiers de texte."""
    new = load(os.path.join(a.dir, "index.json"), {"docs": {}}).get("docs", {})
    old = load(a.orig, {"docs": {}}).get("docs", {})
    touched = {u: m for u, m in new.items() if old.get(u) != m}
    os.makedirs(os.path.join(a.out, "txt"), exist_ok=True)
    n_f = 0
    for u, m in touched.items():
        for f in txt_files(a.dir, m.get("h") or h_of(u)):
            shutil.copy2(os.path.join(a.dir, "txt", f), os.path.join(a.out, "txt", f))
            n_f += 1
    dump(os.path.join(a.out, "part.json"), {"shard": a.shard, "shards": a.shards, "docs": touched})
    note("notice", f"Part {a.shard + 1}/{a.shards} : {len(touched)} documents lus ou relus, {n_f} fichiers de texte")


def cmd_merge(a):
    import fetch_extra as fx
    ip = os.path.join(a.dir, "index.json")
    idx = load(ip, {"docs": {}})
    docs = idx.setdefault("docs", {})
    before = {u: dict(m) for u, m in docs.items()}
    errs, seen, got = [], {}, []
    parts = sorted(p for p in (os.listdir(a.parts) if os.path.isdir(a.parts) else []) if os.path.isfile(os.path.join(a.parts, p, "part.json")))
    for p in parts:
        pd_ = os.path.join(a.parts, p)
        pj = load(os.path.join(pd_, "part.json"))
        sh, n = pj.get("shard"), pj.get("shards")
        if n != a.shards or not isinstance(sh, int) or not 0 <= sh < n:
            errs.append(f"{p} : part {sh}/{n} inattendue (attendu {a.shards} parts)")
            continue
        got.append(sh)
        hs = {}
        for u, m in pj.get("docs", {}).items():
            if fx.cpt_part_of(u, n) != sh:
                errs.append(f"{p} : document d'une autre part lu ici ({u.rsplit('/', 1)[-1][:60]})")
            if u in seen:
                errs.append(f"document lu par deux parts ({seen[u]} et {sh}) : {u.rsplit('/', 1)[-1][:60]}")
            seen[u] = sh
            if m.get("h") != h_of(u):
                errs.append(f"{p} : empreinte inattendue pour {u.rsplit('/', 1)[-1][:60]}")
            hs[m.get("h")] = u
        for f in sorted(os.listdir(os.path.join(pd_, "txt")) if os.path.isdir(os.path.join(pd_, "txt")) else []):
            if f.split(".", 1)[0] not in hs:
                errs.append(f"{p} : fichier de texte sans document ({f})")
    if len(got) != len(set(got)):
        errs.append(f"part présente deux fois : {sorted(got)}")
    if not got:
        errs.append("aucune part reçue des machines de lecture")
    if errs:
        for e in errs[:30]:
            note("error", f"Mise en commun refusée : {e}")
        sys.exit(2)
    missing = sorted(set(range(a.shards)) - set(got))
    if missing:
        note("warning", f"Parts absentes (machine en échec) : {[m + 1 for m in missing]} ; leurs documents seront lus au passage suivant")
    touched = {}
    for p in parts:
        pd_ = os.path.join(a.parts, p)
        for f in sorted(os.listdir(os.path.join(pd_, "txt")) if os.path.isdir(os.path.join(pd_, "txt")) else []):
            shutil.copy2(os.path.join(pd_, "txt", f), os.path.join(a.dir, "txt", f))
        touched.update(load(os.path.join(pd_, "part.json")).get("docs", {}))
    docs.update(touched)
    # contrôles : aucun document perdu ; chaque document du registre a ses textes ; nombre = avant + nouveaux
    lost = [u for u in before if u not in docs]
    new_u = [u for u in touched if u not in before]
    if lost or len(docs) != len(before) + len(new_u):
        note("error", f"Registre incohérent après mise en commun : {len(lost)} documents perdus, {len(docs)} ≠ {len(before)} + {len(new_u)}")
        sys.exit(2)
    no_txt = [u for u, m in touched.items() if m.get("st") == "lu" and not txt_files(a.dir, m.get("h"))]
    if no_txt:
        note("error", f"{len(no_txt)} documents lus sans fichier de texte : {[u.rsplit('/', 1)[-1][:50] for u in no_txt[:5]]}")
        sys.exit(2)
    import time
    cand = fx.cpt_cands(load(a.evs))
    left = fx.cpt_left(cand, docs)
    idx.update(v=1, left=left, total=len(cand), last_new=len(touched), ts=int(time.time()))
    dump(ip, idx)
    # documents lus pendant ce passage (et non seulement relus à 400 dpi) : candidats au contrôle par relecture
    fresh = [u for u, m in touched.items() if (u not in before or fx.cpt_again(before[u])) and m.get("st") == "lu" and 0 < (m.get("pages") or 0) <= 20]
    ocr_ = sorted((u for u in fresh if touched[u].get("ocr")), key=lambda u: (touched[u].get("pages") or 0, u))
    txt_ = sorted((u for u in fresh if not touched[u].get("ocr")), key=lambda u: (touched[u].get("pages") or 0, u))
    pick = (ocr_[:1] + txt_[:1] + ocr_[1:2] + txt_[1:2])[:a.sample]
    dump(a.report, {"shards": a.shards, "parts": [g + 1 for g in sorted(got)], "missing": [m + 1 for m in missing], "before": len(before),
                    "after": len(docs), "new": len(new_u), "touched": sorted(touched), "left": left, "total": len(cand),
                    "sample": [{"u": u, "h": touched[u]["h"], "ocr": bool(touched[u].get("ocr"))} for u in pick]})
    dump(a.sample_evs, [cand[u] for u in pick if u in cand])
    note("notice", f"Mise en commun : {len(parts)}/{a.shards} parts, {len(touched)} documents lus ou relus ({len(new_u)} nouveaux), "
                   f"{len(before)} → {len(docs)} au registre, {left} restent à lire")


def gz_text(p):
    with gzip.open(p, "rt", encoding="utf8") as f:
        return f.read()


def cmd_compare(a):
    """Textes lus par les machines de lecture contre la relecture seule, document par document : identiques."""
    rep = load(a.report)
    bad, ok = [], 0
    for s in rep.get("sample", []):
        h = s["h"]
        f1 = {f[len(h) + 1:]: os.path.join(a.dir, "txt", f) for f in txt_files(a.dir, h)}
        f2 = {f[len(h) + 1:]: os.path.join(a.vdir, "txt", f) for f in txt_files(a.vdir, h)}
        if not f2:
            note("warning", f"Relecture impossible (téléchargement ?) : {s['u'].rsplit('/', 1)[-1][:60]}")
            continue
        need = {"txt.gz"} | ({"fra.gz", "eng.gz"} if s.get("ocr") else set())
        common = set(f1) & set(f2)
        if not need <= common:
            bad.append(f"{s['u'].rsplit('/', 1)[-1][:60]} : textes manquants {sorted(need - common)}")
            continue
        diff = [k for k in sorted(common) if gz_text(f1[k]) != gz_text(f2[k])]
        if diff:
            bad.append(f"{s['u'].rsplit('/', 1)[-1][:60]} : textes différents {diff}")
        else:
            ok += 1
            note("notice", f"Relecture identique : {s['u'].rsplit('/', 1)[-1][:60]} ({', '.join(sorted(common))})")
    for b in bad:
        note("error" if a.strict else "warning", f"Relecture différente : {b}")
    note("notice", f"Contrôle par relecture : {ok} identiques, {len(bad)} différents, sur {len(rep.get('sample', []))} documents")
    if bad and a.strict:
        sys.exit(3)


def cmd_check(a):
    """Lecture des postes (comptes.json) : inchangée pour tous les documents qui n'ont pas été lus ou relus pendant ce passage."""
    rep = load(a.report)
    touched = set(rep.get("touched", []))
    b, c = load(a.before), load(a.after)
    db, dc = b.get("docs", {}), c.get("docs", {})
    lost = [u for u in db if u not in dc]
    chg = [u for u in db if u in dc and u not in touched and db[u] != dc[u]]
    pb, pc = b.get("periodic"), c.get("periodic")
    chg_p = []
    if isinstance(pb, dict) and isinstance(pc, dict):
        chg_p = [u for u in pb if u not in touched and pb[u] != pc.get(u)]
    elif pb != pc and not touched:
        chg_p = ["(publications périodiques)"]
    for u in (lost + chg + chg_p)[:20]:
        note("error", f"Lecture changée pour un document non touché : {u.rsplit('/', 1)[-1][:70]}")
    n_ok_b = sum(1 for r in db.values() if r.get("st") == "ok")
    n_ok_c = sum(1 for r in dc.values() if r.get("st") == "ok")
    note("notice", f"Lecture des postes : {len(db)} → {len(dc)} documents, {n_ok_b} → {n_ok_c} vérifiés ; "
                   f"{len(lost)} perdus, {len(chg)} changés hors passage, {len(chg_p)} publications périodiques changées hors passage")
    if lost or chg or chg_p:
        sys.exit(4)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("pack")
    p.add_argument("--dir", required=True)
    p.add_argument("--orig", required=True)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shards", type=int, required=True)
    p.add_argument("--out", required=True)
    p = sp.add_parser("merge")
    p.add_argument("--dir", required=True)
    p.add_argument("--parts", required=True)
    p.add_argument("--shards", type=int, required=True)
    p.add_argument("--evs", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--sample-evs", required=True)
    p.add_argument("--sample", type=int, default=2)
    p = sp.add_parser("compare")
    p.add_argument("--dir", required=True)
    p.add_argument("--vdir", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--strict", action="store_true")
    p = sp.add_parser("check")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--report", required=True)
    a = ap.parse_args()
    {"pack": cmd_pack, "merge": cmd_merge, "compare": cmd_compare, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
