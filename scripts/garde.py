"""Auto-protection des données publiées (branche data) : un fichier n'est jamais publié s'il est vide, illisible, disparu ou
anormalement court par rapport à la publication précédente ; la dernière bonne version est remise à sa place.

Usage (étape « Publier les données » de terminal.yml, avant le commit) :
  python3 scripts/garde.py <dossier data/ à publier> <commit de la publication précédente> [rapport.json]

- La publication précédente est lue dans le dépôt courant (`git ls-tree` / `git show` sur le commit donné).
- Fichier disparu, vide ou JSON illisible : la version précédente est remise.
- Anormalement court : seulement pour les fichiers de fond (base, séries, FA, QLAB…) de plus de 20 Ko dont la taille tombe
  sous le quart de la précédente.
- Les dossiers retirés volontairement (RETIRES) ne sont jamais remis.
- Chaque remise en place est signalée dans les annotations du passage (avertissement, jamais une erreur) et dans le rapport.
- Ne fait jamais échouer la publication : en cas de problème du script lui-même, rien n'est touché (code de sortie 0).
"""
import json, os, subprocess, sys

RETIRES = ("data/qlabp/", "data/s/SPX.json")  # QLAB Prévisions, retiré le 19/10/2026 à la demande du propriétaire ; s/SPX.json : ancien nom de la série mensuelle SPXM, orphelin
FOND = ("data/summary.json", "data/fundamentals.json", "data/dividends.json", "data/events.json", "data/search.json",
        "data/fa_index.json", "data/profiles.json", "data/ratings.json", "data/weekly.json", "data/breadth.json", "data/eco.json",
        "data/reports.json", "data/avis_brvm.json", "data/world_mkt.json", "data/calendar.json", "data/bonds.json",
        "data/news.json", "data/s/", "data/fa/", "data/qlab/")
TAILLE_MIN, RATIO = 20000, 0.25


def git(*a, binary=False):
    r = subprocess.run(["git", *a], capture_output=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf8", "replace")[:300])
    return r.stdout if binary else r.stdout.decode("utf8")


def lisible(path):
    if not path.endswith(".json"):
        return True
    try:
        with open(path, encoding="utf8") as fh:
            json.load(fh)
        return True
    except Exception:  # noqa: BLE001
        return False


def main():
    if len(sys.argv) < 3 or not sys.argv[2].strip():
        print("Garde des données : pas de publication précédente connue, rien à comparer")
        return
    dpub, sha = os.path.abspath(sys.argv[1]), sys.argv[2].strip()
    base = os.path.dirname(dpub)  # dossier qui contient data/
    rap = sys.argv[3] if len(sys.argv) > 3 else None
    prev = {}
    for line in git("ls-tree", "-r", "-l", sha, "data").splitlines():
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) >= 4 and parts[1] == "blob":
            prev[path] = int(parts[3]) if parts[3].isdigit() else 0
    remis = []
    for path, taille in prev.items():
        if path.startswith(RETIRES):
            continue
        new = os.path.join(base, path)
        cause = None
        if not os.path.exists(new):
            cause = "disparu"
        elif os.path.getsize(new) == 0 and taille > 0:
            cause = "vide"
        elif not lisible(new):
            cause = "illisible"
        elif path.startswith(FOND) and taille > TAILLE_MIN and os.path.getsize(new) < RATIO * taille:
            cause = f"anormalement court ({os.path.getsize(new)} octets au lieu de {taille})"
        if cause:
            os.makedirs(os.path.dirname(new), exist_ok=True)
            with open(new, "wb") as fh:
                fh.write(git("show", f"{sha}:{path}", binary=True))
            remis.append({"fichier": path, "cause": cause})
    # nouveaux fichiers illisibles (sans version précédente) : signalés seulement
    neufs = []
    for dp, _, fs in os.walk(os.path.join(base, "data")):
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), base)
            if rel not in prev and not rel.startswith(RETIRES) and not lisible(os.path.join(dp, f)):
                neufs.append(rel)
    for r in remis:
        print(f"::warning title=Garde des données::{r['fichier']} {r['cause']} : dernière bonne version gardée")
    for n in neufs:
        print(f"::warning title=Garde des données::nouveau fichier illisible : {n}")
    print(f"Garde des données : {len(prev)} fichiers comparés, {len(remis)} remis à leur dernière bonne version, "
          f"{len(neufs)} nouveaux fichiers illisibles")
    if rap:
        json.dump({"compares": len(prev), "remis": remis, "neufs_illisibles": neufs}, open(rap, "w", encoding="utf8"),
                  ensure_ascii=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=Garde des données::contrôle impossible ({type(e).__name__} : {str(e)[:200]}) ; publication inchangée")
    sys.exit(0)
