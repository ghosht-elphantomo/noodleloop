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


def get_json(url):
    """Requête à l'archive web, au rythme accepté par le site (une toutes les 5 s, pause longue s'il demande de ralentir)."""
    import fetch_extra as FX
    txt = FX.get_wb(url).decode("utf8", "replace").strip()
    return json.loads(txt) if txt else []


def cdx_rows(pre, warn):
    """Captures PDF (code 200) d'un préfixe d'adresses, par tranches de 2 000 (clé de reprise de l'archive web)."""
    q = {"url": pre, "matchType": "prefix", "output": "json", "fl": "original,timestamp,length,mimetype,statuscode", "collapse": "urlkey",
         "filter": ["statuscode:200", "mimetype:application/pdf"], "limit": 2000, "showResumeKey": "true"}
    key, n = None, 0
    while n < 200:
        n += 1
        res, err = None, None
        for k_ in range(4):  # (archive surchargée : 504 ou coupure, nouvel essai après une pause)
            try:
                res = get_json(CDX + "?" + urllib.parse.urlencode({**q, **({"resumeKey": key} if key else {})}, doseq=True))
                break
            except Exception as e:  # noqa: BLE001
                err = e
                time.sleep(30 * (k_ + 1))
        if res is None:
            warn.append(f"{pre} (tranche {n}) : {str(err)[:160]}")
            return
        key = None
        if res and res[-1] and len(res) >= 2 and res[-2] == [] and len(res[-1]) == 1:
            key = res[-1][0]  # (tranche suivante)
            res = res[:-2]
        for r in res:
            if r and r[0] != "original":
                yield r
        if not key:
            return


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
    rows, warn = {}, []
    for pre in PREFIXES:
        for r in cdx_rows(pre, warn):
            orig, ts, ln, mt, sc = (list(r) + [None] * 5)[:5]
            if not orig or not (str(mt or "").endswith("pdf") or orig.lower().endswith(".pdf")):
                continue
            k = norm(orig)
            if k not in rows or ts > rows[k]["ts"]:
                rows[k] = {"u": orig, "ts": ts, "taille": int(ln) if str(ln or "").isdigit() else None}
    for w in warn:
        print(f"::warning::Archive web : {w}")
    if not rows:
        # (vérification seulement : un passage sans réponse de l'archive web n'est pas un échec, il est signalé et rien n'est écrit)
        print("::warning::Archive web : aucune capture obtenue (site injoignable ou réponse vide) ; vérification à relancer plus tard")
        sys.exit(0)
    def stem(k):
        n_ = k.rsplit("/", 1)[-1]
        n_ = re.sub(r"\.pdf$", "", n_)
        return re.sub(r"[^a-z0-9]+", "", re.sub(r"_\d$", "", n_))
    known_stems = {stem(k) for k in known}
    out, n_var = [], 0
    for k, r in rows.items():
        if k in known:
            continue
        if stem(k) in known_stems:
            n_var += 1  # (même document déposé sous un nom voisin : doublon d'un document déjà connu, pas un manque)
            continue
        name = k.rsplit("/", 1)[-1]
        n_ = CPT.nrm(name).replace("_", " ").replace("-", " ")
        ms_ = [(t, m_) for t, rx in CPT.NAME_TOKENS.items() for m_ in [re.search(rx, n_)] if m_]
        # (un nom contenu dans un autre, « onatel » dans « sonatel » : le nom le plus long l'emporte)
        ts_ = [t for t, m_ in ms_ if not any(o_ is not m_ and o_.start() <= m_.start() and m_.end() <= o_.end() and (o_.end() - o_.start()) > (m_.end() - m_.start()) for _, o_ in ms_)]
        fy = re.search(r"exercice[_ -]*(19[89]\d|20[0-3]\d)", name) or re.search(r"(?<!\d)(19[89]\d|20[0-3]\d)(?!\d)", name[8:] if re.match(r"\d{8}", name) else name)
        out.append({**r, "t": ts_[0] if len(ts_) == 1 else None, "cat": cat_of(name), "fy": int(fy.group(1)) if fy else None})
    out.sort(key=lambda r: (r["t"] or "~", r["fy"] or 0, r["u"]))
    by_t = collections.Counter(r["t"] or "?" for r in out)
    by_c = collections.Counter(r["cat"] for r in out)
    res = {"ts": int(time.time()), "n_archive": len(rows), "n_connus": len(known), "n_variantes": n_var, "n_inconnus": len(out), "alertes": warn, "par_titre": dict(by_t.most_common()),
           "par_categorie": dict(by_c.most_common()), "docs": out}
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, "archives.json"), "w", encoding="utf8"), ensure_ascii=False, indent=0)
    print(f"::notice::Archive web : {len(rows)} documents PDF de la BRVM ; {n_var} variantes de nom de documents connus ; {len(out)} absents de la liste des publications")
    print(f"::notice::Par catégorie : {dict(by_c.most_common())}")
    print(f"::notice::Par titre : {dict(by_t.most_common(30))}")
    fin = [r for r in out if r["cat"] in ("financial_statements", "annual_report", "company_report", "activity_report", "auditor_report", "financial_results") and r["t"]]
    for r in fin[:40]:
        print(f"::notice::{r['t']} {r['fy']} {r['cat']} {r['u'].rsplit('/', 1)[-1][:90]}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        import traceback
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print(f"::warning::Vérification des archives arrêtée : {type(e).__name__} : {str(e)[:200]} (ligne {tb.lineno}, {tb.name})")
        sys.exit(0)
