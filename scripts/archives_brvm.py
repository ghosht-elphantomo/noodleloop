"""Archives du site de la BRVM : documents PDF déposés par les sociétés cotées que l'archive web a gardés et que la liste des
publications ne connaît pas (ou plus). Vérification seulement : rien n'est lu ni publié ici ; la liste sert à décider des
documents à ajouter à la lecture des comptes.

Usage : archives_brvm.py --evs cpt_evs.json --out DOSSIER   (cpt_evs.json : fetch_extra.py --only comptes_list)
-> DOSSIER/archives.json : {"n_archive", "n_inconnus", "docs": [{"u", "ts", "taille", "t", "cat", "fy"}], "par_titre": …}
"""
import argparse, collections, json, os, re, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CDX = "https://web.archive.org/cdx/search/cdx"
PREFIXES = ("brvm.org/sites/default/files/", "brvm.org/fr/documentation/", "brvm.org/fr/rapports-societe-cotes/")


def get_json(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; verification)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                txt = r.read().decode("utf8", "replace").strip()
            return json.loads(txt) if txt else []
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(10 * (i + 1))
    return []


def norm(u):
    """Adresse comparable : sans protocole, sans « www. », sans port, sans paramètres, en minuscules, %20 décodés."""
    u = urllib.parse.unquote((u or "").strip())
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    u = re.sub(r"^([^/]+):\d+", r"\1", u)
    return u.split("?", 1)[0].split("#", 1)[0].lower()


def cat_of(name):
    n = name.lower()
    for rx, c in ((r"_-_efp?_|etats?_financ|comptes", "financial_statements"), (r"_-_efa_", "financial_statements"),
                  (r"_-_ra_|rapport_annuel", "annual_report"), (r"_-_rg_|rapport_de_gestion", "company_report"),
                  (r"_-_r[st]\d?_|rapport_d.?activit|semest|trimest", "activity_report"), (r"_-_cac_|commissaire", "auditor_report"),
                  (r"_-_ag[oe]?_|assembl", "ag_meeting"), (r"_-_cm_|communiqu", "communique"), (r"resultat", "financial_results")):
        if re.search(rx, n):
            return c
    return "autre"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import comptes as CPT
    evs = json.load(open(a.evs, encoding="utf8"))
    known = {norm(e.get("document_url")) for e in evs if e.get("document_url")}
    rows = {}
    for pre in PREFIXES:
        q = {"url": pre, "matchType": "prefix", "output": "json", "fl": "original,timestamp,length,mimetype,statuscode", "collapse": "urlkey",
             "filter": "statuscode:200"}
        npages = get_json(CDX + "?" + urllib.parse.urlencode({**q, "showNumPages": "true"}))
        npages = int(npages) if isinstance(npages, (int, float, str)) and str(npages).isdigit() else 1
        for p in range(npages):
            res = get_json(CDX + "?" + urllib.parse.urlencode({**q, "page": p}))
            for r in res[1:] if res and res[0] and res[0][0] == "original" else res:
                orig, ts, ln, mt, sc = (r + [None] * 5)[:5]
                if not orig or not (str(mt or "").endswith("pdf") or orig.lower().endswith(".pdf")):
                    continue
                k = norm(orig)
                if k not in rows or ts > rows[k]["ts"]:
                    rows[k] = {"u": orig, "ts": ts, "taille": int(ln) if str(ln or "").isdigit() else None}
            time.sleep(1)
    out = []
    for k, r in rows.items():
        if k in known:
            continue
        name = k.rsplit("/", 1)[-1]
        n_ = CPT.nrm(name).replace("_", " ").replace("-", " ")
        ts_ = [t for t, rx in CPT.NAME_TOKENS.items() if re.search(rx, n_)]
        fy = re.search(r"exercice[_ -]*(19[89]\d|20[0-3]\d)", name) or re.search(r"(?<!\d)(19[89]\d|20[0-3]\d)(?!\d)", name[8:] if re.match(r"\d{8}", name) else name)
        out.append({**r, "t": ts_[0] if len(ts_) == 1 else None, "cat": cat_of(name), "fy": int(fy.group(1)) if fy else None})
    out.sort(key=lambda r: (r["t"] or "~", r["fy"] or 0, r["u"]))
    by_t = collections.Counter(r["t"] or "?" for r in out)
    by_c = collections.Counter(r["cat"] for r in out)
    res = {"ts": int(time.time()), "n_archive": len(rows), "n_connus": len(known), "n_inconnus": len(out), "par_titre": dict(by_t.most_common()),
           "par_categorie": dict(by_c.most_common()), "docs": out}
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, "archives.json"), "w", encoding="utf8"), ensure_ascii=False, indent=0)
    print(f"::notice::Archive web : {len(rows)} documents PDF de la BRVM, dont {len(out)} absents de la liste des publications")
    print(f"::notice::Par catégorie : {dict(by_c.most_common())}")
    print(f"::notice::Par titre : {dict(by_t.most_common(30))}")
    fin = [r for r in out if r["cat"] in ("financial_statements", "annual_report", "company_report", "activity_report", "auditor_report", "financial_results") and r["t"]]
    for r in fin[:40]:
        print(f"::notice::{r['t']} {r['fy']} {r['cat']} {r['u'].rsplit('/', 1)[-1][:90]}")


if __name__ == "__main__":
    main()
