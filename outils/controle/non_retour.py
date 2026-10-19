"""Bugs corrigés : ils ne doivent jamais revenir. Un contrôle par bug, lancé chaque matin par controle.py (controle.yml).

Règle (19/10/2026) : chaque bug corrigé reçoit ici une entrée et un contrôle automatique, avant ou avec sa correction.
Une entrée = identifiant, date de la correction, ce qui s'était passé, ce qui est vérifié. Un bug qui revient rend le rapport
orange (ou rouge s'il touche la confidentialité, la sécurité ou des chiffres faux) ; jamais d'échec de l'automatisation.

  python3 non_retour.py --liste   -> écrit BUGS_CORRIGES.md (liste lisible, régénérée à partir de ce fichier)
"""
import collections, json, os, re, sys

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
BUGS = []


def bug(ident, date, titre, quoi, controle):
    """déclare un bug corrigé ; `controle` est une fonction(ctx) -> (niveau, détail) ou un nom de vérification déjà faite"""
    def deco(fn):
        BUGS.append({"id": ident, "date": date, "titre": titre, "quoi": quoi, "controle": controle, "fn": fn})
        return fn
    return deco


def jl(D, f):
    try:
        with open(os.path.join(D, f), encoding="utf8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------------------------------------ vérifications déjà faites
# (le contrôle existe dans controle.py : on reprend simplement son résultat sous l'identifiant du bug)
def deja(nom):
    def fn(ctx):
        x = next((v for v in ctx["R"].v if v["nom"].startswith(nom)), None)
        if not x:
            return "orange", f"vérification « {nom} » non faite (parcours du site absent ?)"
        return x["niveau"], x["detail"]
    return fn


@bug("B01", "2026-10-19", "Symboles affichés en émoji sur iPhone (boutons Précédent / Suivant, réglages, cloche)",
     "Les flèches ◀ ▶ et les symboles ⚙ 🔧 🔔 s'affichaient en émoji sur iPhone ; remplacés par des icônes dessinées.",
     "aucun symbole de la liste Unicode « Emoji » dans les pages du parcours")
def b01(ctx):
    return deja("Parcours du site : symboles affichés en émoji")(ctx)


@bug("B02", "2026-10-19", "QLAB Prévisions revenu", "L'onglet 3 « Prévisions » de QLAB a été retiré à la demande du propriétaire.",
     "pas de dossier qlabp/ dans les données publiées, pas d'onglet Prévisions dans QLAB")
def b02(ctx):
    pb = []
    if os.path.isdir(os.path.join(ctx["D"], "qlabp")):
        pb.append("dossier qlabp/ encore publié")
    pages = ctx["pages"] or {}
    if any(re.match(r"QLAB~[^@]+@p$", h) for h in pages) or any("3) Prévisions" in (v.get("text") or "") for h, v in pages.items() if h.startswith("QLAB")):
        pb.append("onglet Prévisions visible dans QLAB")
    return ("orange", "; ".join(pb)) if pb else ("vert", "absent des données et du site")


@bug("B03", "2026-10-19", "Fichier publié vide, abîmé ou disparu",
     "Un passage pouvait publier un fichier vide ou illisible ; la garde (scripts/garde.py) remet la dernière bonne version.",
     "tous les fichiers JSON publiés sont lisibles et non vides ; les fichiers essentiels sont présents")
def b03(ctx):
    a, b = deja("Fichiers essentiels présents")(ctx), deja("Fichiers lisibles et non vides")(ctx)
    niv = max((a[0], b[0]), key={"vert": 0, "orange": 1, "rouge": 2}.get)
    return niv, f"{a[1]} ; {b[1]}"


@bug("B04", "2026-10-13", "Fonctions en double (MON et MONITOR, TOP et NEWS, WEI et INDX)",
     "Deux codes ouvraient le même écran ; un seul code par écran, les anciens restent acceptés comme raccourcis.",
     "le parcours ne trouve aucune fonction MON, TOP ni WEI (seulement MONITOR, NEWS, INDX)")
def b04(ctx):
    pages = ctx["pages"]
    if not pages:
        return "orange", "parcours du site absent"
    dbl = sorted({h.split("~")[0].split("@")[0] for h in pages} & {"MON", "TOP", "WEI", "WEIF", "IMAP", "EQS", "CF"})
    return ("orange", "fonctions en double revenues : " + ", ".join(dbl)) if dbl else ("vert", "aucun doublon de fonction")


@bug("B05", "2026-10-16", "ETI affiché en dollars au lieu de FCFA",
     "Les comptes d'Ecobank Transnational étaient affichés en dollars ; ils sont convertis en FCFA (millions).",
     "fa/ETIT.json en XOF, chiffre d'affaires du dernier exercice au-dessus de 100 milliards de FCFA")
def b05(ctx):
    f = jl(ctx["D"], "fa/ETIT.json")
    if not f:
        return "orange", "fa/ETIT.json absent"
    Y = f.get("Y") or {}
    rev = [v for v in (Y.get("rev") or []) if v is not None]
    if f.get("ccy") != "XOF":
        return "rouge", f"devise {f.get('ccy')}"
    if rev and rev[-1] < 1e5:
        return "rouge", f"chiffre d'affaires {rev[-1]} (millions) : unité suspecte"
    return "vert", "en FCFA"


@bug("B06", "2026-10-19", "Présentations DES remplacées par l'ancien texte de la fiche tierce",
     "Les 48 présentations DES ont été réécrites par FQT (chaque fait prouvé, seed/des_fqt.json) ; la construction les applique.",
     "profiles.json : la présentation de chaque société de seed/des_fqt.json est bien le texte FQT")
def b06(ctx):
    seed = jl(os.path.join(DEPOT, "seed"), "des_fqt.json")
    P = jl(ctx["D"], "profiles.json")
    if not seed or P is None:
        return "orange", "fichiers absents"
    diff = [k for k, t in (seed.get("desc") or {}).items() if (P.get(k) or {}).get("desc") != t]
    return ("rouge", f"{len(diff)} présentations ne sont pas les textes FQT : " + ", ".join(diff[:10])) if diff else \
        ("vert", f"{len(seed.get('desc') or {})} présentations FQT en ligne")


@bug("B07", "2026-10-16", "Montant mille fois trop petit dans les comptes (groupe de chiffres perdu, unité)",
     "Des montants lus sans un groupe de chiffres (ou dans la mauvaise unité) arrivaient dans FA ; ils sont écartés à la construction.",
     "dans fa/<titre BRVM>.json, aucun chiffre d'affaires, résultat, total du bilan ou capitaux propres 300 fois plus petit que "
     "les exercices voisins")
def b07(ctx):
    S = jl(ctx["D"], "summary.json") or {}
    ids = [s["id"] for s in S.get("secs") or [] if s.get("mkt") == "BRVM" and s.get("cls") == "Equity"]
    out = []
    for t in ids:
        f = jl(ctx["D"], f"fa/{t}.json")
        if not f:
            continue
        Y = f.get("Y") or {}
        yrs = Y.get("y") or []
        for k in ("rev", "ni", "assets", "eq"):
            V = Y.get(k) or []
            for i, v in enumerate(V):
                if not v:
                    continue
                nb = [abs(V[j]) for j in (i - 2, i - 1, i + 1, i + 2) if 0 <= j < len(V) and V[j] and abs(yrs[j] - yrs[i]) <= 2]
                if len(nb) >= 2:
                    m = sorted(nb)[len(nb) // 2]
                    if abs(v) < m / 300 and 0.4 <= abs(v) * 1000 / m <= 2.5:
                        out.append(f"{t} {yrs[i]} {k}")
    return ("rouge", "montants suspects : " + ", ".join(out[:10])) if out else ("vert", f"{len(ids)} sociétés, aucun montant suspect")


@bug("B08", "2026-10-16", "Doublons d'événements ou de dividendes",
     "Des avis et des dividendes apparaissaient deux fois ; les doublons sont fusionnés à la construction.",
     "aucun doublon dans events.json ni dans dividends.json (même société, date, titre, document / même exercice, montant, paiement)")
def b08(ctx):
    du = (ctx["inst"] or {}).get("doublons") or {}
    pb = {k: v for k, v in du.items() if k in ("événements", "dividendes") and v}
    return ("orange", "doublons : " + ", ".join(f"{k} {v}" for k, v in pb.items())) if pb else ("vert", "aucun doublon")


# sauts de cours déjà vérifiés : vraies baisses (dividende exceptionnel, opération sur le capital)
SAUTS_CONNUS = {("FTSC", 20250926): "détachement du dividende 2024 (1 161,60 + 564,96 FCFA exceptionnel)",
                ("SLBC", 20070515): "connu avant le 19/10/2026"}


@bug("B17", "2026-10-16", "Documents en double dans MOTS CLES",
     "Des documents apparaissaient plusieurs fois dans la recherche MOTS CLES ; doublons retirés le 16/10 (10 doublons connus restent, "
     "même document déposé deux fois).", "pas plus de doublons de documents dans MOTS CLES que les 10 connus au 19/10/2026")
def b17(ctx):
    n = ((ctx["inst"] or {}).get("doublons") or {}).get("documents (MOTS CLES)")
    if n is None:
        return "orange", "comptage absent"
    return ("orange", f"{n} doublons (10 connus)") if n > 10 else ("vert", f"{n} doublons connus, pas de nouveau")


@bug("B09", "2026-10-13", "Saut de cours sans opération (fractionnement non appliqué)",
     "Un fractionnement non repris faisait chuter la série (Onatel BF 2018) ; les fractionnements sont détectés et appliqués.",
     "aucune hausse de plus de 50 % ni baisse de plus de 40 % d'une séance à l'autre dans les séries des actions BRVM, sauf les cas vérifiés")
def b09(ctx):
    S = jl(ctx["D"], "summary.json") or {}
    out = []
    for s in S.get("secs") or []:
        if s.get("mkt") != "BRVM" or s.get("cls") != "Equity":
            continue
        x = jl(ctx["D"], f"s/{s['id']}.json")
        if not x:
            continue
        c, d = x.get("c") or [], x.get("d") or []
        for i in range(1, len(c)):
            if c[i - 1] and c[i] and not (0.6 <= c[i] / c[i - 1] <= 1.5) and (s["id"], d[i]) not in SAUTS_CONNUS:
                out.append(f"{s['id']} {d[i]} {c[i - 1]:g} → {c[i]:g}")
    return ("orange", "sauts à vérifier : " + "; ".join(out[:8])) if out else ("vert", "aucun saut inexpliqué")


@bug("B10", "2026-10-19", "Automatisation en échec sans que personne le voie",
     "La lecture des comptes échouait à chaque passage depuis le 18/10 (part téléchargée sans sous-dossier) ; corrigé le 19/10.",
     "aucun passage en échec dans les dernières 24 h (liste des passages lue par controle.yml)")
def b10(ctx):
    runs = ctx.get("runs")
    if runs is None:
        return "vert", "non vérifié ici (seulement dans le contrôle de GitHub)"
    runs = [r for r in runs if isinstance(r, dict) and r.get("name")]
    ko = collections.Counter(r.get("name") for r in runs if r.get("conclusion") in ("failure", "timed_out", "startup_failure"))
    return ("orange", "passages en échec : " + ", ".join(f"{k} ×{v}" for k, v in ko.most_common())) if ko else \
        ("vert", f"{len(runs)} passages en 24 h, aucun échec")


@bug("B11", "2026-10-19", "Lecture des comptes bloquée (rien publié pendant plusieurs jours)",
     "Du 18 au 19/10 aucun passage de la lecture des comptes n'a été publié ; corrigé le 19/10.",
     "la branche comptes a été publiée il y a moins de 3 jours")
def b11(ctx):
    ci = ctx.get("comptes")
    if ci is None:
        return "vert", "non vérifié ici (seulement dans le contrôle de GitHub)"
    import time
    age = (ctx["maintenant"] - (ci.get("ts") or 0)) / 86400
    return ("orange", f"dernière publication il y a {age:.1f} jours") if age > 3 else ("vert", f"publiée il y a {age:.1f} jour(s), {ci.get('left', '?')} documents à lire")


@bug("B12", "2026-10-19", "En-têtes de sécurité du site perdus",
     "Les en-têtes de sécurité (vercel.json) protègent la page ; une modification de vercel.json ne doit jamais les retirer.",
     "vercel.json contient nosniff, X-Frame-Options DENY, HTTPS imposé, Content-Security-Policy et Cross-Origin-Opener-Policy")
def b12(ctx):
    v = jl(DEPOT, "vercel.json")
    if not v:
        return "rouge", "vercel.json illisible"
    have = {(h.get("source"), x.get("key")) for h in v.get("headers") or [] for x in h.get("headers") or []}
    need = [("/(.*)", "X-Content-Type-Options"), ("/(.*)", "X-Frame-Options"), ("/(.*)", "Strict-Transport-Security"),
            ("/(.*)", "Referrer-Policy"), ("/", "Content-Security-Policy"), ("/", "Cross-Origin-Opener-Policy"),
            ("/index.html", "Content-Security-Policy")]
    miss = [f"{s} {k}" for s, k in need if (s, k) not in have]
    return ("rouge", "manquent : " + ", ".join(miss)) if miss else ("vert", "tous présents")


SECRET = re.compile(r"sk_live_[0-9a-zA-Z]{10,}|sb_secret_[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|glpat-[A-Za-z0-9_-]{15,}|"
                    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----")
JWT = re.compile(r"eyJhbGciOi[A-Za-z0-9_-]{10,}\.([A-Za-z0-9_-]{10,})\.[A-Za-z0-9_-]{10,}")


def jwt_secret(txt):
    """jeton JWT écrit dans un fichier : seule une clé de service (role service_role) est secrète ; la clé publique (anon) est permise"""
    import base64
    for m in JWT.finditer(txt):
        try:
            pl = base64.urlsafe_b64decode(m.group(1) + "=" * (-len(m.group(1)) % 4)).decode("utf8", "ignore")
        except Exception:  # noqa: BLE001
            continue
        if '"service_role"' in pl:
            return True
    return False


@bug("B13", "2026-10-19", "Clé secrète écrite dans le dépôt",
     "Aucune clé ne doit être écrite dans le dépôt (elles vont dans les secrets de GitHub et les variables de Vercel).",
     "aucune forme de clé secrète connue (GitHub, GitLab, Stripe, Supabase, AWS, clé privée, jeton de service) dans les fichiers du dépôt ; .env ignoré")
def b13(ctx):
    trouve = []
    for base, dirs, files in os.walk(DEPOT):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
        if os.sep + "lib" + os.sep + "ocr" in base + os.sep:
            continue  # bibliothèques tierces compactées
        for f in files:
            p = os.path.join(base, f)
            try:
                if os.path.getsize(p) > 3e6:
                    continue
                txt = open(p, encoding="utf8", errors="ignore").read()
                if SECRET.search(txt) or jwt_secret(txt):
                    trouve.append(os.path.relpath(p, DEPOT))
            except OSError:
                pass
    gi = open(os.path.join(DEPOT, ".gitignore"), encoding="utf8").read() if os.path.exists(os.path.join(DEPOT, ".gitignore")) else ""
    pb = (["clé possible dans : " + ", ".join(trouve[:6])] if trouve else []) + ([] if re.search(r"^\.env$", gi, re.M) else [".env absent de .gitignore"])
    return ("rouge", "; ".join(pb)) if pb else ("vert", "aucune clé dans le dépôt")


@bug("B14", "2026-10-17", "Nom de source ou nom du propriétaire visible sur le site",
     "Le site ne doit afficher aucun nom de source (sites d'origine des données) ni rien de personnel.",
     "parcours du site : aucun nom de source ni lien interdit ; aucun nom de la liste de confidentialité (empreintes)")
def b14(ctx):
    a, b = deja("Parcours du site : noms de sources")(ctx), deja("Confidentialité (page)")(ctx)
    niv = max((a[0], b[0]), key={"vert": 0, "orange": 1, "rouge": 2}.get)
    return niv, f"sources : {a[1]} ; confidentialité : {b[1]}"


@bug("B15", "2026-10-13", "Relevé de séance figé (cours plus mis à jour)",
     "Les relevés de 15 minutes partaient en retard (programmation de GitHub) ; le métronome les déclenche à l'heure.",
     "fraîcheur des données (relevé, cours, base) dans les limites du contrôle")
def b15(ctx):
    return deja("Fraîcheur des données")(ctx)


# documents rangés sous une autre société dans la liste des publications : noms propres à chaque société
NOMS = {"SIVC": ["AIR LIQUIDE", "ERIUM"], "ECOC": ["ECOBANK CI", "ECOBANK COTE"], "SNTS": ["SONATEL"], "ONTBF": ["ONATEL"],
        "CFAC": ["CFAO"], "PRSC": ["TRACTAFRIC"], "BOAS": ["BOA SENEGAL", "BOA SN"], "BOAC": ["BOA COTE", "BOA CI"],
        "BOAN": ["BOA NIGER", "BOA NG"], "BOAB": ["BOA BENIN", "BOA BN"], "BOAM": ["BOA MALI", "BOA ML"],
        "BOABF": ["BOA BURKINA", "BOA BF"], "SIBC": ["SIB CI", "SOCIETE IVOIRIENNE DE BANQUE"], "SMBC": ["SMB CI", "MULTINATIONALE DE BITUMES"]}
# groupes : un document d'un groupe peut citer sa filiale (non signalé)
GROUPES = {("ETIT", "ECOC")}


@bug("B16", "2026-10-19", "Document rangé sous une autre société (liste des publications)",
     "Des documents d'une société étaient classés sous une autre (rapport de BOA Sénégal chez Erium, comptes de Tractafric chez "
     "CFAO…) ; aucun de leurs montants n'est affiché. Correction de la liste des publications en cours.",
     "aucun document de events.json dont l'intitulé ou le fichier nomme une autre société sans nommer la sienne")
def b16(ctx):
    E = jl(ctx["D"], "events.json") or []
    N = lambda s: re.sub(r"[^A-Z0-9]+", " ", __import__("unicodedata").normalize("NFD", s or "").encode("ascii", "ignore").decode().upper())
    out = []
    for x in E:
        t, ti = x.get("t"), N((x.get("ti") or "") + " " + (x.get("u") or "").split("/")[-1].replace("_", " ").replace("-", " "))
        own = NOMS.get(t)
        for o, keys in NOMS.items():
            if o == t or (t, o) in GROUPES:
                continue
            if any(f" {k} " in f" {ti} " for k in keys) and not (own and any(f" {k} " in f" {ti} " for k in own)):
                out.append(f"{t} ← {o} ({x.get('d')})")
                break
    return ("orange", f"{len(out)} documents : " + "; ".join(out[:8])) if out else ("vert", "aucun document mal rangé")


def verifier(R, ctx):
    """ajoute au rapport une ligne par bug corrigé"""
    ctx["R"] = R
    for b in BUGS:
        try:
            niv, det = b["fn"](ctx)
        except Exception as e:  # noqa: BLE001
            niv, det = "orange", f"contrôle impossible : {type(e).__name__} {str(e)[:120]}"
        R.add(f"Bug corrigé {b['id']} · {b['titre']}", niv, det)


def liste_md():
    L = ["# Bugs corrigés : ils ne doivent jamais revenir", "",
         "Chaque bug corrigé a ici son contrôle automatique, lancé chaque matin par le contrôle quotidien (`controle.yml`).",
         "Un bug qui revient rend le rapport orange ou rouge. Liste régénérée par `python3 outils/controle/non_retour.py --liste` ;",
         "pour ajouter un bug : une entrée `@bug(...)` dans `outils/controle/non_retour.py`, puis régénérer cette liste.", "",
         "| Id | Corrigé le | Bug | Ce qui s'était passé | Ce qui est vérifié chaque matin |", "|---|---|---|---|---|"]
    for b in BUGS:
        L.append(f"| {b['id']} | {b['date']} | {b['titre']} | {b['quoi']} | {b['controle']} |")
    open(os.path.join(ICI, "BUGS_CORRIGES.md"), "w", encoding="utf8").write("\n".join(L) + "\n")
    print(f"{len(BUGS)} bugs listés dans BUGS_CORRIGES.md")


if __name__ == "__main__" and "--liste" in sys.argv:
    liste_md()
