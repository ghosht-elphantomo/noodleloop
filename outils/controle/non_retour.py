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


@bug("B16", "2026-10-19", "Document rangé sous une autre société",
     "La Bourse dépose parfois un document sous la page d'une autre société (rapport de BOA Sénégal chez Erium, comptes de "
     "Tractafric chez CFAO, rapport de la SGB CI chez SMB…). L'intitulé, puis le nom du fichier, désignent la bonne société "
     "(comptes.doc_company) : recherche MOTS CLES, lecture des comptes et, depuis le 19/10/2026, événements.",
     "aucun événement de events.json rattaché à une autre société que celle que nomment son intitulé ou son fichier")
def b16(ctx):
    sys.path.insert(0, os.path.join(DEPOT, "scripts"))
    from comptes import doc_company, NAME_TOKENS
    E = jl(ctx["D"], "events.json") or []
    out = [f"{x['t']} → {doc_company(x['t'], x.get('ti') or '', (x.get('u') or '').rsplit('/', 1)[-1])} ({x.get('d')})" for x in E
           if x.get("t") in NAME_TOKENS and doc_company(x["t"], x.get("ti") or "", (x.get("u") or "").rsplit("/", 1)[-1]) != x["t"]]
    return ("orange", f"{len(out)} document(s) : " + "; ".join(out[:8])) if out else ("vert", "aucun document mal rangé")


@bug("B18", "2026-10-19", "Taux de distribution calculé sur le BNPA d'un autre exercice",
     "Le payout des tableaux BRVM divisait le dernier dividende par le BNPA du dernier exercice, même quand le dividende était "
     "celui d'un exercice plus ancien (Filtisac 3 516 % au lieu de 88 %, BNBC 4 451 % au lieu de 55 %) ; champ pay calculé "
     "sur le BNPA du même exercice depuis le 19/10/2026.",
     "pour chaque action BRVM, pay = dividende ÷ BNPA de l'exercice du dividende (série de la fiche) ; jamais le rapport à un autre exercice")
def b18(ctx):
    S = jl(ctx["D"], "summary.json") or {}
    F = jl(ctx["D"], "fundamentals.json") or {}
    L = [s for s in S.get("secs") or [] if s.get("mkt") == "BRVM" and s.get("cls") == "Equity"]
    if L and not any("pay" in s for s in L):
        return "orange", "champ pay absent (construction antérieure au 19/10/2026 ?)"
    out = []
    for s in L:
        ex, dps, bn = s.get("dps_ex"), s.get("dps"), s.get("bnpa")
        ser = {int(k): v for k, v in (((F.get(s["id"]) or {}).get("series") or {}).get("bnpa") or {}).items() if v is not None and str(k).isdigit()}
        try:
            ex = int(ex) if ex is not None else None
        except (TypeError, ValueError):
            ex = None
        eps = bn if ex is None or not ser or ex >= max(ser) else ser.get(ex)
        att = dps / eps if dps and eps and eps > 0 else None
        got = s.get("pay")
        if (att is None) != (got is None) or (att is not None and abs(got / att - 1) > 0.01):
            out.append(f"{s['id']} {got} (attendu {att and round(att, 4)})")
    return ("rouge", f"{len(out)} taux faux : " + "; ".join(out[:8])) if out else ("vert", f"{len(L)} actions, taux du même exercice")


@bug("B19", "2026-10-19", "Dividende d'un exercice remplacé par un seul de ses versements (FA)",
     "Dans FA, le dividende par action d'un exercice gardait le dernier versement lu : Filtisac 2024 affichait l'exceptionnel "
     "(564,96) au lieu du dividende annuel (1 161,6) ; acompte et solde n'étaient pas additionnés. Corrigé le 19/10/2026.",
     "pour chaque action BRVM, dividende de FA = somme des versements ordinaires de l'exercice (dividends.json, exceptionnels à part)")
def b19(ctx):
    import collections
    S = jl(ctx["D"], "summary.json") or {}
    D = jl(ctx["D"], "dividends.json") or []
    tot = collections.defaultdict(float)
    for x in D:
        if x.get("t") and x.get("ex") and x.get("dps") and not x.get("exc"):
            tot[(x["t"], int(x["ex"]))] += x["dps"]
    out, n = [], 0
    for s in S.get("secs") or []:
        if s.get("mkt") != "BRVM" or s.get("cls") != "Equity":
            continue
        f = jl(ctx["D"], f"fa/{s['id']}.json")
        Y = (f or {}).get("Y") or {}
        for y, v in zip(Y.get("y") or [], Y.get("dps") or []):
            a = tot.get((s["id"], int(y)))
            if a and v is not None:
                n += 1
                if abs(v / a - 1) > 0.005:
                    out.append(f"{s['id']} {y} : {v:g} (versements {a:g})")
    return ("rouge", f"{len(out)} exercices faux : " + "; ".join(out[:8])) if out else ("vert", f"{n} exercices concordants")


@bug("B20", "2026-10-19", "Adresses /doc/ qui servent n'importe quelle page d'un site tiers",
     "Les adresses /doc/ du terminal relayaient des dossiers entiers de sites tiers : une page HTML de ces sites aurait tourné "
     "comme une page du terminal (accès au portefeuille enregistré dans le navigateur). Depuis le 19/10/2026 : PDF seulement, et "
     "pour le troisième site le seul dossier de fichiers utilisé.",
     "dans vercel.json, chaque réécriture vers un autre site n'accepte que des .pdf ou le dossier afficher-fichier")
def b20(ctx):
    v = jl(DEPOT, "vercel.json")
    if not v:
        return "rouge", "vercel.json illisible"
    bad = [r.get("source") for r in v.get("rewrites") or [] if str(r.get("destination", "")).startswith("http")
           and not (r.get("source", "").endswith("[pP][dD][fF])") or "/afficher-fichier/" in r.get("source", ""))]
    return ("rouge", "réécritures trop larges : " + ", ".join(bad)) if bad else ("vert", "PDF seulement")


@bug("B21", "2026-10-19", "Lien « javascript: » ouvrable depuis le terminal",
     "Un lien d'actualité venu d'un flux extérieur était ouvert tel quel : un lien « javascript: » aurait exécuté du code dans le "
     "terminal. Depuis le 19/10/2026 la collecte ne garde que les liens http(s) et la page refuse d'ouvrir ces adresses.",
     "aucun lien autre que http(s) ou /doc/ dans les actualités publiées ; garde badUrl présente dans la page")
def b21(ctx):
    out = []
    for f in ("news.json", "news_eco.json", "events_recent.json"):
        x = jl(ctx["D"], f)
        items = x if isinstance(x, list) else (x or {}).get("items") or (x or {}).get("news") or []
        for it in items if isinstance(items, list) else []:
            u = (it or {}).get("u") if isinstance(it, dict) else None
            if u and not re.match(r"(https?://|/doc/|/data/|#)", str(u).strip(), re.I):
                out.append(f"{f} : {str(u)[:40]}")
    src = open(os.path.join(DEPOT, "web", "core.js"), encoding="utf8").read()
    if "function badUrl(" not in src or "window.open = function" not in src:
        out.append("garde badUrl absente de web/core.js")
    return ("rouge", "; ".join(out[:6])) if out else ("vert", "aucun lien dangereux, garde en place")


@bug("B22", "2026-10-19", "Démarrage bloqué par une adresse « #constructor » ou « #% »",
     "Une adresse de page finissant par « #% » ou nommant une propriété interne (« #constructor ») bloquait le démarrage du "
     "terminal. Depuis le 19/10/2026, lecture de l'adresse protégée et fonctions ou titres reconnus par own().",
     "fromHash protège decodeURIComponent et n'accepte que les fonctions et titres réels")
def b22(ctx):
    src = open(os.path.join(DEPOT, "web", "core.js"), encoding="utf8").read()
    m = re.search(r"function fromHash\(\) \{[^\n]*", src)
    ok = bool(m) and "try { h = decodeURIComponent" in m.group(0) and "own(FN, f)" in m.group(0) and "own(Q.by, s)" in m.group(0)
    return ("vert", "lecture de l'adresse protégée") if ok else ("rouge", "fromHash sans protection")


@bug("B23", "2026-10-19", "Valeur échangée d'un bulletin lue en milliers",
     "Dans les bulletins officiels, les montants échangés d'un milliard et plus étaient lus sans leur dernier groupe de chiffres "
     "(SONATEL : 1 658 702 au lieu de 1 658 702 000) ; le contrôle les écartait et laissait en place le volume partiel de la base "
     "tierce (3 380 titres au lieu de 37 543 le 15/10/2026). Depuis le 19/10/2026 ces montants sont ramenés en FCFA quand ils "
     "redonnent volume × cours à 2 % près.",
     "pour chaque action BRVM depuis 2015, montant échangé ÷ (volume × cours de clôture) entre 0,5 et 2 (un montant en milliers donne 0,001)")
def b23(ctx):
    S = jl(ctx["D"], "summary.json") or {}
    out, n = [], 0
    for s in S.get("secs") or []:
        if s.get("mkt") != "BRVM" or s.get("cls") != "Equity":
            continue
        x = jl(ctx["D"], f"s/{s['id']}.json") or {}
        for d, c, v, va in zip(x.get("d") or [], x.get("c") or [], x.get("v") or [], x.get("val") or []):
            if d < 20150101 or not (c and v and va):
                continue
            n += 1
            if not .5 < va / (v * c) < 2:
                out.append(f"{s['id']} {d} : {va:,} pour {v:,} titres à {c:g}".replace(",", " "))
    return ("rouge", f"{len(out)} séance(s) : " + "; ".join(out[-8:])) if out else ("vert", f"{n} séances cohérentes depuis 2015")


@bug("B24", "2026-10-20", "Titres US restés sur le cours de la veille (paquets de 25 symboles)",
     "Le service de cours US ne renvoie que 20 symboles par requête ; le relevé en demandait 25 : les 5 derniers de chaque paquet "
     "(33 titres, dont COST, QCOM, ISRG, XLE) gardaient le cours de la veille sans erreur signalée. Paquets de 20 et symboles "
     "manquants redemandés puis signalés depuis le 20/10/2026.",
     "titres US du résumé : séries arrêtées avant la dernière séance US de l'univers (au plus 3 tolérées : titre suspendu)")
def b24(ctx):
    S = jl(ctx["D"], "summary.json") or {}
    L = [x for x in S.get("secs") or [] if x.get("mkt") == "US" and x.get("cls") != "Index"]
    last = {}
    for x in L:
        se = jl(ctx["D"], f"s/{x['id']}.json") or {}
        if se.get("d") and se.get("f", "D") == "D":
            last[x["id"]] = se["d"][-1]
    if not last:
        return "orange", "aucune série US quotidienne lue"
    ref = max(last.values())
    old = sorted(t for t, d in last.items() if d < ref)
    if len(old) > 3:
        return "rouge", f"{len(old)} titre(s) US arrêtés avant le {ref} : " + ", ".join(old[:12])
    return "vert", f"{len(last)} titres US à jour au {ref}" + (f" (en retard : {', '.join(old)})" if old else "")


@bug("B25", "2026-10-20", "Référence du contrôle du matin effacée par la sonde",
     "Les publications de la sonde (probe.yml) et des archives (archives.yml) réécrivaient la branche probe sans le dossier "
     "controle/ : le contrôle suivant n'avait plus de référence et passait au vert sans rien comparer. Depuis le 20/10/2026, les "
     "dossiers controle/ et audit/ sont recopiés avant chaque publication.",
     "probe.yml et archives.yml recopient controle/ et audit/ avant de publier")
def b25(ctx):
    bad = []
    for f in ("probe.yml", "archives.yml"):
        try:
            t = open(os.path.join(DEPOT, ".github", "workflows", f), encoding="utf8").read()
        except OSError:
            continue
        if "for d in controle audit" not in t:
            bad.append(f)
    return ("rouge", "dossier controle/ non recopié par " + ", ".join(bad)) if bad else ("vert", "recopié")


def _web(f):
    try:
        return open(os.path.join(DEPOT, "web", f), encoding="utf8").read()
    except OSError:
        return ""


def _node_periodes():
    """exécute les fonctions de période de web/engine.js pour chaque jour de 2024 à 2027 : dates de départ valides"""
    import subprocess
    js = ("const fs=require('fs'),vm=require('vm');const c={atob:s=>Buffer.from(s,'base64').toString()};vm.createContext(c);"
          "vm.runInContext(fs.readFileSync(process.argv[1],'utf8')+';this.f=perStart;',c);const bad=[];"
          "for(let t=Date.UTC(2024,0,1);t<Date.UTC(2028,0,1);t+=864e5){const d=new Date(t),x=d.getUTCFullYear()*1e4+(d.getUTCMonth()+1)*100+d.getUTCDate();"
          "for(const p of ['1M','3M','6M','YTD','1A','3A','5A','10A']){const s=c.f(x,p),y=Math.floor(s/1e4),m=Math.floor(s/100)%100,j=s%100;"
          "const ok=m>=1&&m<=12&&j>=1&&j<=new Date(Date.UTC(y,m,0)).getUTCDate()&&s<x;if(!ok)bad.push(x+' '+p+' '+s);}}console.log(JSON.stringify(bad.slice(0,5)));")
    r = subprocess.run(["node", "-e", js, os.path.join(DEPOT, "web", "engine.js")], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:200])
    return json.loads(r.stdout.strip() or "[]")


@bug("B26", "2026-10-20", "Périodes 1M / 3M / 6M fausses une partie de l'année (TRA, HP, GP, COMP)",
     "La date de départ des périodes était calculée en retranchant 100, 300 ou 600 au nombre AAAAMMJJ : de janvier à juin la "
     "période « 6M » partait du début de l'année (SNTS +7,7 % au lieu de +12,4 % au 13/02) et HP affichait une date « 15/98/2026 ». "
     "Depuis le 20/10/2026 : fonctions communes backMonths / perStart (web/engine.js), dates calendaires.",
     "dates de départ valides pour chaque jour de 2024 à 2027 et chaque période ; plus aucune soustraction « last - 100/300/600 » dans la page")
def b26(ctx):
    pb = []
    for f in ("pages1.js", "pages4.js", "pages9.js", "pages13.js"):
        t = _web(f)
        if re.search(r"last - (?:100|300|600|10000|30000|50000)\b|'1M': 100|end - yrs \* 10000", t):
            pb.append(f"soustraction sur AAAAMMJJ dans {f}")
    try:
        bad = _node_periodes()
        if bad:
            pb.append("dates invalides : " + "; ".join(bad))
    except Exception as e:  # noqa: BLE001
        pb.append(f"essai des périodes impossible : {e}")
    return ("rouge", "; ".join(pb)) if pb else ("vert", "dates de départ calendaires valides (2024-2027)")


@bug("B27", "2026-10-20", "Rendement d'une période calculé depuis la première séance après la date de départ",
     "TRA, GP, COMP et HP prenaient comme base la première séance après la date de départ (le rendement de cette séance était "
     "perdu) : TRA « YTD » ORAC +47,6 % contre +45,6 % partout ailleurs. Depuis le 20/10/2026 : base = dernière séance à la date "
     "ou avant (baseIdx, idxAtOrBefore), comme le résumé.",
     "YTD et 1 an recalculés avec la règle de la page = ceux du résumé pour 10 actions BRVM (0,05 point près) ; TRA, GP et COMP utilisent la base commune")
def b27(ctx):
    pb = []
    for f, k in (("pages9.js", "baseIdx(x, d)"), ("pages1.js", "idxAtOrBefore(S.x, perStart("), ("pages4.js", "idxAtOrBefore(S.x, start)")):
        if k not in _web(f):
            pb.append(f"base commune absente de {f}")
    S = jl(ctx["D"], "summary.json") or {}
    import bisect
    n = 0
    for s in [x for x in S.get("secs") or [] if x.get("mkt") == "BRVM" and x.get("cls") == "Equity"][:10]:
        x = jl(ctx["D"], f"s/{s['id']}.json") or {}
        d, c = x.get("d") or [], x.get("c") or []
        if len(d) < 300 or s.get("ytd") is None:
            continue
        i = bisect.bisect_right(d, (d[-1] // 10000 - 1) * 10000 + 1231) - 1
        if i >= 0 and abs(c[-1] / c[i] - 1 - s["ytd"]) > .0005:
            pb.append(f"{s['id']} YTD {c[-1] / c[i] - 1:.4f} / résumé {s['ytd']:.4f}")
        n += 1
    return ("rouge", "; ".join(pb[:6])) if pb else ("vert", f"{n} actions : YTD de la page = résumé")


@bug("B28", "2026-10-20", "Calculs d'affichage faux corrigés le 20/10/2026 (audit) : 12 mois en 252 séances, PER US, drawdown 5 ans, rendement absent à 0,00 %, secteurs, prime sur rendement négatif",
     "DES et TECH comptaient « 12 mois » en 252 séances (la BRVM en a 250) ; GF divisait le cours du jour par le BPA de chaque "
     "exercice US ; BETA mesurait le drawdown 5 ans depuis la première clôture de l'historique (UNLC −90,3 % au lieu de −64,9 %) ; "
     "DIVC affichait 0,00 % pour un rendement absent ; le tableau des secteurs comptait 0 % pour un titre sans valeur ; RV donnait "
     "une décote de 1 000 % sur un rendement FCF négatif ; HVT retirait les séances sans écart (Parkinson surestimée).",
     "motifs corrigés absents du code de la page ; aucun « 0,00 % » dans les rendements de DIVC (parcours du site)")
def b28(ctx):
    pb = []
    pats = [("pages8.js", r"tr\[n - 253\]"), ("pages15.js", r"roc\(252\)"), ("pages4.js", r"let pk = S\.c\[0\], mdd = 0; const k5"),
            ("pages2.js", r"\$\{num\(s\.yld \* 100, 2\)\}%"), ("pages1.js", r"w\(s\) \* \(s\.ytd \|\| 0\)"),
            ("pages4.js", r"prem = v != null && md \? \(t === 'p' \? md / v - 1"), ("pages11.js", r"S\.h\[i\] > S\.l\[i\]\) a\.push"),
            ("pages11.js", r"const t = y \* 10000 \+ 1231;")]
    for f, rx in pats:
        if re.search(rx, _web(f)):
            pb.append(f"{f} : {rx[:40]}")
    pages = ctx.get("pages") or {}
    for h, v in pages.items():
        if h.startswith("DIVC") and re.search(r"\b0,00 ?%", (v or {}).get("text") or ""):
            pb.append(f"{h} : rendement « 0,00 % »")
            break
    return ("rouge", "; ".join(pb[:6])) if pb else ("vert", "aucun des motifs corrigés")


@bug("B29", "2026-10-20", "Passage complet lancé en journée traité comme la clôture du soir",
     "Un passage complet déclenché par une modification du code archivait les cours de séance comme clôtures du jour "
     "(seed/brvm_daily.csv : 221 clôtures fausses du 12 au 19/10/2026, réparées depuis les bulletins) et remettait la référence "
     "« veille » des capitalisations mondiales à l'heure du passage (variations du jour fausses). Depuis le 20/10/2026, seule la "
     "base programmée du soir (FQT_CLOSE=1) fait la clôture du jour ; une séance déjà archivée est remplacée par la lecture du soir.",
     "terminal.yml : archive et référence réservées à la base programmée ; archive = bulletin (contrôle « Archive des séances / bulletin officiel ») ; "
     "référence des capitalisations mondiales datée du soir")
def b29(ctx):
    pb = []
    t = open(os.path.join(DEPOT, ".github", "workflows", "terminal.yml"), encoding="utf8").read()
    if "if: steps.mode.outputs.mode == 'eod' && github.event.schedule == '35 22 * * 1-5'" not in t or t.count("FQT_CLOSE:") < 2:
        pb.append("clôture du jour non réservée à la base programmée dans terminal.yml")
    w = jl(ctx["D"], "world.json") or {}
    ref = str(w.get("ref") or "")
    if ref and not re.match(r"\d{4}-\d{2}-\d{2} (2[2-3]|0[0-1]):", ref):
        pb.append(f"référence des capitalisations mondiales datée « {ref} » (attendue avec la base du soir, après 22 h UTC)")
    return ("orange" if pb and not pb[0].startswith("clôture") else "rouge", "; ".join(pb)) if pb else ("vert", "clôture du jour réservée à la base du soir" + (f" ; référence mondiale {ref}" if ref else ""))


def _ser_us(ctx):
    """séries quotidiennes des titres US et Taïwan du résumé : {id: série}"""
    S = jl(ctx["D"], "summary.json") or {}
    out = {}
    for x in S.get("secs") or []:
        if x.get("mkt") in ("US", "TW") and x.get("f", "D") == "D":
            se = jl(ctx["D"], f"s/{x['id']}.json")
            if se and se.get("d"):
                out[x["id"]] = se
    return out


@bug("B30", "2026-10-20", "Liquidité nette de la Fed fausse (unités FRED mélangées)",
     "Le bilan de la Fed (WALCL) est publié en millions de dollars, le compte du Trésor (TGA) et les prises en pension (RRP) en "
     "milliards : la liquidité nette mélangeait les deux unités. Depuis le 20/10/2026 : bilan ÷ 1 000 − TGA − RRP, en milliards, "
     "et valeur écartée si elle sort de ]0 ; bilan[.",
     "eco.json : dernière liquidité nette strictement positive et inférieure au bilan de la Fed exprimé en milliards")
def b30(ctx):
    E = jl(ctx["D"], "eco.json") or {}
    M = {m.get("id"): m for m in E.get("meta") or []}
    nl, wa = M.get("NETLIQ"), M.get("WALCL")
    if not nl or not wa:
        return "orange", "liquidité nette ou bilan de la Fed absent de eco.json"
    b = (wa.get("last") or 0) / 1000
    v = nl.get("last")
    if v is None or not 0 < v < b:
        return "rouge", f"liquidité nette {v} Md$ hors de ]0 ; {b:,.1f}[ (bilan de la Fed)".replace(",", " ")
    return "vert", f"{v:,.1f} Md$ pour un bilan de {b:,.1f} Md$".replace(",", " ")


@bug("B31", "2026-10-20", "Séances de week-end et dividendes en tête des séries US",
     "Des cours datés d'un samedi ou d'un dimanche (relevé après la clôture rattaché au jour du relevé) entraient dans les séries "
     "US et Taïwan, et les dividendes antérieurs au début d'une série étaient posés sur sa première séance. Corrigé le 20/10/2026.",
     "séries quotidiennes US et Taïwan : aucune séance un samedi ou un dimanche, aucun dividende sur la première séance de la fenêtre d'historique")
def b31(ctx):
    import datetime as _dt
    we, d0 = [], []
    L = _ser_us(ctx)
    # début de la fenêtre commune des séries (coupe de l'historique) : un dividende sur cette séance vient d'avant la série ; une
    # série qui commence plus tard peut avoir un vrai détachement le jour de sa première cotation (KDP, 10/07/2018)
    w0 = (collections.Counter(se["d"][0] for se in L.values()).most_common(1) or [(0, 0)])[0][0]
    for sid, se in L.items():
        for d in se["d"][-400:]:
            if _dt.date(d // 10000, d // 100 % 100, d % 100).weekday() >= 5:
                we.append(f"{sid} {d}")
                break
        dv = se.get("div") or []
        if dv and dv[0] and abs(se["d"][0] - w0) <= 7:
            d0.append(f"{sid} ({dv[0]:g} le {se['d'][0]})")
    pb = ([f"{len(we)} série(s) avec une séance de week-end : " + ", ".join(we[:6])] if we else []) + \
         ([f"{len(d0)} dividende(s) sur la première séance : " + ", ".join(d0[:6])] if d0 else [])
    if not L:
        return "orange", "aucune série US ou Taïwan lue"
    return ("rouge", " ; ".join(pb)) if pb else ("vert", f"{len(L)} séries sans séance de week-end ni dividende en tête")


@bug("B32", "2026-10-20", "Bougie du jour incohérente et variation du jour non contrôlée (US, contrats à terme)",
     "Le cours du jour greffé sur les séries donnait des bougies impossibles (plus haut = plus bas = clôture avec une ouverture hors "
     "fourchette) ; la variation US venait parfois d'une clôture précédente non confirmée ou d'un cours après Bourse aberrant ; "
     "après le règlement, les contrats à terme affichaient 0,00 % avec ouverture et plus haut à 0. Corrigé le 20/10/2026.",
     "dernière bougie de chaque série : plus bas ≤ ouverture, clôture ≤ plus haut ; cotations US et Taïwan : variation conforme à la "
     "clôture précédente de la série (0,3 point d'écart toléré) ; aucune cotation à 0,00 % avec ouverture ou plus haut à 0")
def b32(ctx):
    S = jl(ctx["D"], "summary.json") or {}
    mk = {x["id"]: x.get("mkt") for x in S.get("secs") or []}
    PV = {x["id"]: x.get("prev") for x in S.get("secs") or []}
    bc, pc, zr, n = [], [], [], 0
    for x in S.get("secs") or []:
        se = jl(ctx["D"], f"s/{x['id']}.json") or {}
        if not se.get("d") or se.get("f", "D") != "D" or not all(se.get(k) for k in ("o", "h", "l", "c")):
            continue
        o, h, l, c = se["o"][-1], se["h"][-1], se["l"][-1], se["c"][-1]
        if o and h and l and c:
            n += 1
            if not (l <= min(o, c) + 1e-9 and max(o, c) <= h + 1e-9):
                bc.append(f"{x['id']} {se['d'][-1]} (o {o:g} h {h:g} l {l:g} c {c:g})")
    Q = (jl(ctx["D"], "quotes.json") or {}).get("q") or {}
    L = _ser_us(ctx)
    for sid, q in Q.items():
        if not isinstance(q, dict):
            continue
        if q.get("pct") == 0 and (q.get("o") == 0 or q.get("h") == 0):
            zr.append(sid)
        se = L.get(sid)
        if mk.get(sid) not in ("US", "TW") or not se or q.get("pct") is None or not q.get("last") or not q.get("d"):
            continue
        k = int(str(q["d"]).replace("-", ""))
        # clôture précédente affichée : celle du résumé quand la série porte la séance de la cotation (elle tient compte d'une
        # séance manquante dans la série, B41), sinon la dernière clôture de la série avant la cotation
        prev = PV.get(sid) if se["d"][-1] == k and PV.get(sid) else \
            next((c for d, c in zip(reversed(se["d"]), reversed(se["c"])) if d < k and c), None)
        if prev and abs(q["pct"] - (q["last"] / prev - 1)) > 0.003:
            pc.append(f"{sid} {q['pct'] * 100:+.2f} % pour {(q['last'] / prev - 1) * 100:+.2f} %")
    pb = ([f"{len(bc)} bougie(s) impossible(s) : " + "; ".join(bc[:5])] if bc else []) + \
         ([f"{len(pc)} variation(s) US non conformes à la clôture précédente : " + "; ".join(pc[:5])] if pc else []) + \
         ([f"{len(zr)} cotation(s) à 0,00 % avec ouverture ou plus haut à 0 : " + ", ".join(zr[:8])] if zr else [])
    return ("rouge", " ; ".join(pb)) if pb else ("vert", f"{n} dernières bougies cohérentes ; variations US conformes")


@bug("B33", "2026-10-20", "Base du soir annulable par un push en attente",
     "La base programmée de 22 h 35 partageait sa file d'attente avec les passages lancés par un push : GitHub annule un passage en "
     "attente quand un autre arrive dans la même file, et un push arrivé pendant l'attente supprimait la base du soir (ni archive de "
     "la séance, ni données brutes, ni QLAB). Depuis le 20/10/2026 la base programmée a sa propre file (terminal-eod).",
     "terminal.yml : file terminal-eod pour la base programmée ; la dernière séance BRVM (hors séance du jour) est archivée dans "
     "seed/brvm_daily.csv")
def b33(ctx):
    import datetime as _dt
    pb = []
    t = open(os.path.join(DEPOT, ".github", "workflows", "terminal.yml"), encoding="utf8").read()
    if "'terminal-eod'" not in t:
        pb.append("base programmée sans file propre dans terminal.yml")
    x = jl(ctx["D"], "s/BRVMC.json") or {}
    d = x.get("d") or []
    try:
        last = max(l.split(",", 1)[0] for l in open(os.path.join(DEPOT, "seed", "brvm_daily.csv"), encoding="utf8").read().splitlines()[1:] if l[:2] == "20")
    except (OSError, ValueError):
        last = None
    if len(d) >= 2 and last:
        auj = int(_dt.datetime.utcfromtimestamp(ctx.get("maintenant") or 0).strftime("%Y%m%d")) if ctx.get("maintenant") else 0
        att = d[-2] if d[-1] >= auj else d[-1]  # la séance du jour n'est archivée que le soir
        if int(last.replace("-", "")) < att:
            pb.append(f"séance du {att} non archivée (dernière archive {last}) : base du soir absente ou en échec")
    return ("rouge", " ; ".join(pb)) if pb else ("vert", f"file propre ; dernière séance archivée {last}")


@bug("B34", "2026-10-20", "Branche republiée incomplète après une restauration en échec",
     "Les branches raw, boc, comptes et dividendes sont des commits uniques republiés de force : si leur lecture échouait en début de "
     "passage, le passage repartait de zéro et republiait une branche incomplète (et le terminal reprenait l'ancienne branche site, "
     "qui ne contient plus les données). Depuis le 20/10/2026 : 3 essais de lecture, passage arrêté si la branche reste illisible, "
     "publication refusée si la branche perd plus de 10 % de ses fichiers.",
     "nombre et taille des fichiers de chaque branche comparés au contrôle précédent (baisse de plus de 10 % = rouge) ; protections "
     "présentes dans terminal.yml, boc.yml, dividendes.yml et comptes.yml")
def b34(ctx):
    pb = []
    for f, m in (("terminal.yml", "publication refusée"), ("boc.yml", "publication refusée"), ("dividendes.yml", "publication refusée"),
                 ("comptes.yml", "publication refusée"), ("terminal.yml", "présente mais illisible")):
        try:
            if m not in open(os.path.join(DEPOT, ".github", "workflows", f), encoding="utf8").read():
                pb.append(f"{f} sans « {m} »")
        except OSError:
            pass
    if "elif git fetch -q --depth 1 origin site" in open(os.path.join(DEPOT, ".github", "workflows", "terminal.yml"), encoding="utf8").read():
        pb.append("terminal.yml reprend encore la branche site")
    B, RB = ctx.get("branches") or {}, ctx.get("ref_branches") or {}
    for b, v in sorted(B.items()):
        r = RB.get(b) or {}
        if v.get("tronque") or r.get("tronque"):
            continue
        for k, nom in (("n", "fichiers"), ("o", "octets")):
            if r.get(k) and v.get(k) is not None and v[k] < 0.9 * r[k]:
                pb.append(f"branche {b} : {v[k]:,} {nom} au lieu de {r[k]:,}".replace(",", " "))
    if pb:
        return "rouge", " ; ".join(pb[:8])
    if not B:
        return "vert", "protections présentes (taille des branches lue seulement dans le contrôle de GitHub)"
    return "vert", "protections présentes ; " + ", ".join(f"{b} {v.get('n')} fichiers" for b, v in sorted(B.items())) + \
        ("" if RB else " (première mesure, comparée au prochain contrôle)")


@bug("B35", "2026-10-20", "Délais dépassés et sources en échec masqués dans les passages verts",
     "L'étape « Actualités, publications BRVM… » était coupée à 360 s aux passages de l'heure pile (fin de la liste non rafraîchie) "
     "sans signal : passage vert, ancien fichier republié. Depuis le 20/10/2026 : délai de 480 s, et une annotation par source "
     "sans aucune lecture réussie, par étape de plus de 4 minutes et par délai dépassé.",
     "annotations des passages du terminal des dernières 24 h : délais dépassés (exit code 124), refus de publication, sources en échec")
def b35(ctx):
    an = ctx.get("annot")
    if an is None:
        return "vert", "non vérifié ici (seulement dans le contrôle de GitHub)"
    an = [a for a in an if isinstance(a, dict)]
    to = sum(1 for a in an if "exit code 124" in (a.get("message") or ""))
    rf = [a for a in an if (a.get("titre") or "").startswith(("Publication refusée", "Branche raw", "Restauration"))]
    src = collections.Counter((a.get("message") or "").split(" :", 1)[0] for a in an if a.get("titre") == "Source en échec")
    lent = collections.Counter((a.get("message") or "").split(" :", 1)[0] for a in an if a.get("titre") == "Étape lente")
    pb = ([f"{len(rf)} refus ou restauration en échec : " + "; ".join((a.get("message") or "")[:90] for a in rf[:3])] if rf else []) + \
         ([f"{to} délai(s) dépassé(s)"] if to else []) + \
         ([f"sources en échec : " + ", ".join(f"{k} ×{v}" for k, v in src.most_common(8))] if src else []) + \
         ([f"étapes lentes : " + ", ".join(f"{k} ×{v}" for k, v in lent.most_common(6))] if lent else [])
    niv = "rouge" if rf else ("orange" if pb else "vert")
    return niv, " ; ".join(pb) if pb else f"{len(an)} annotation(s), aucun délai dépassé ni source en échec"


# chutes réelles vérifiées (marché, résultats) : pas des opérations sur titres
CHUTES_US_CONNUES = {("IONQ", 20250108): "informatique quantique, −39 %", ("NBIS", 20250127): "séance DeepSeek, −37 %",
                     ("SQQQ", 20250409): "ETF inverse ×3, Nasdaq +12 % ce jour-là", ("DXCM", 20240726): "résultats, −40 %",
                     ("SNPS", 20250910): "résultats, −36 %"}


@bug("B36", "2026-10-20", "Scission Honeywell non ajustée (chute de 51 % dans la série)",
     "HON passait de 464,42 à 227,80 le 29/06/2026 (distribution d'Honeywell Aerospace) sans ajustement des cours antérieurs : "
     "rendement 1 an −45 %, drawdown −58 %, volatilité 76 %. Depuis le 20/10/2026, les scissions US documentées "
     "(seed/scissions_us.json) ajustent les cours et dividendes antérieurs.",
     "séries US et Taïwan des 3 dernières années : aucune baisse d'une séance de plus de 35 % hors chutes réelles vérifiées "
     "(liste CHUTES_US_CONNUES)")
def b36(ctx):
    out = []
    for sid, se in _ser_us(ctx).items():
        d, c = se["d"], se["c"]
        k0 = next((i for i, x in enumerate(d) if x >= d[-1] - 30000), len(d))
        for i in range(max(k0, 1), len(c)):
            if c[i - 1] and c[i] and c[i] / c[i - 1] < 0.65 and (sid, d[i]) not in CHUTES_US_CONNUES:
                out.append(f"{sid} {d[i]} {c[i - 1]:g} → {c[i]:g}")
    return ("rouge", f"{len(out)} chute(s) de plus de 35 % à expliquer (scission, regroupement ?) : " + "; ".join(out[:8])) if out else \
        ("vert", f"aucune chute inexpliquée ({len(CHUTES_US_CONNUES)} chutes réelles connues)")


@bug("B37", "2026-10-20", "Points datés d'un vendredi à venir (séries hebdomadaires)",
     "Les séries ramenées à la semaine étiquetaient la semaine en cours au vendredi suivant : 10 séries macro, la matrice "
     "hebdomadaire et les historiques des fiches FA affichaient un point au 23/10/2026 le 19/10. Depuis le 20/10/2026, la semaine "
     "en cours porte la date de sa dernière observation.",
     "eco.json, weekly.json et fa/*.json : aucune date postérieure au jour du contrôle")
def b37(ctx):
    import datetime as _dt, glob as _gl
    auj = int(_dt.datetime.utcfromtimestamp(ctx.get("maintenant") or __import__("time").time()).strftime("%Y%m%d"))
    out = []
    E = jl(ctx["D"], "eco.json") or {}
    for sid, se in (E.get("s") or {}).items():
        if se and se[0] and max(se[0]) > auj:
            out.append(f"eco {sid} {max(se[0])}")
    w = (jl(ctx["D"], "weekly.json") or {}).get("w") or []
    if w and max(w) > auj:
        out.append(f"weekly {max(w)}")
    n = 0
    for p in sorted(_gl.glob(os.path.join(ctx["D"], "fa", "*.json"))):
        x = jl(os.path.dirname(p), os.path.basename(p)) or {}
        dd = (x.get("mh") or {}).get("d") or []
        if dd and max(dd) > auj:
            n += 1
    if n:
        out.append(f"{n} fiche(s) FA")
    return ("orange", f"dates après le {auj} : " + ", ".join(out[:10])) if out else ("vert", f"aucune date après le {auj}")


@bug("B38", "2026-10-20", "Doublons et cours nuls (Fear & Greed CNN, intervenants, capitalisations mondiales)",
     "fg.json portait deux points CNN le même jour ; l'annuaire des intervenants listait deux fois ORAGROUP SECURITIES et BAOBAB "
     "ASSET MANAGEMENT (doublons dans une même page), avec des courriels contenant des espaces ; les capitalisations mondiales "
     "affichaient un cours de 0 (NBB.BH) et deux « SK Innovation » sans distinction. Corrigé le 20/10/2026.",
     "dates CNN uniques dans fg.json ; aucun nom en double par annuaire dans sgi.json ; aucun cours ≤ 0 ni nom en double dans world.json")
def b38(ctx):
    pb = []
    cn = (((jl(ctx["D"], "fg.json") or {}).get("us") or {}).get("cnn") or {}).get("d") or []
    if len(cn) != len(set(cn)):
        pb.append(f"fg.json : {len(cn) - len(set(cn))} date(s) CNN en double")
    sg = jl(ctx["D"], "sgi.json") or {}
    for k, v in (sg.get("dirs") or {}).items():
        nm = [re.sub(r"\s+", " ", r.get("n") or "").strip().lower() for r in v.get("rows") or []]
        dup = sorted({x for x in nm if nm.count(x) > 1})
        if dup:
            pb.append(f"sgi.json {k} : {', '.join(dup[:3])} en double")
        if any(re.search(r"\s", r.get("mail") or "") for r in v.get("rows") or []):
            pb.append(f"sgi.json {k} : courriel avec espace")
    rows = (jl(ctx["D"], "world.json") or {}).get("rows") or []
    z = [r[0] for r in rows if isinstance(r, list) and len(r) > 4 and not (r[4] or 0) > 0]
    nm = [r[1] for r in rows if isinstance(r, list) and len(r) > 1]
    dn = sorted({x for x in nm if nm.count(x) > 1}) if len(nm) != len(set(nm)) else []
    if z:
        pb.append(f"world.json : cours ≤ 0 pour {', '.join(z[:5])}")
    if dn:
        pb.append(f"world.json : {', '.join(dn[:3])} en double")
    return ("orange", " ; ".join(pb)) if pb else ("vert", "aucun doublon ni cours nul")


@bug("B39", "2026-10-20", "Variation des taux affichée « 0,0 pb » ou contraire au rendement",
     "Quand CNBC renvoyait « UNCH », la variation des taux était vide et l'écran BTMM affichait « 0,0 pb » (US2Y en hausse de "
     "1,7 pb). Depuis le 20/10/2026, une variation absente est recalculée (rendement affiché − clôture précédente de la source) et, "
     "à défaut, s'affiche « — » ; la variation en % des taux (de signe opposé) est retirée.",
     "world_mkt.json : variation de chaque taux présente et égale à rendement − clôture précédente quand les deux diffèrent ; pas de "
     "variation en % ; BTMM sans « bp(r.chg * 100) » non protégé")
def b39(ctx):
    pb = []
    for r in (jl(ctx["D"], "world_mkt.json") or {}).get("rt") or []:
        l_, p_, c_ = r.get("last"), r.get("prev"), r.get("chg")
        if r.get("pct") is not None:
            pb.append(f"{r.get('s')} variation en %")
        if c_ is None and l_ is not None and p_ is not None and abs(l_ - p_) <= 0.5:
            pb.append(f"{r.get('s')} variation vide pour {l_} − {p_}")
        elif c_ is not None and l_ is not None and p_ is not None and abs(l_ - p_) > 1e-9 and abs(c_ - (l_ - p_)) > 0.0011:
            pb.append(f"{r.get('s')} {c_:+.3f} pour {l_} − {p_}")
    if "bp(r.chg * 100)}</td><td class=\"dm\">" in _web("pages14.js"):
        pb.append("pages14.js : variation vide affichée 0,0")
    return ("orange", "; ".join(pb[:8])) if pb else ("vert", "variations des taux conformes")


@bug("B40", "2026-10-20", "Actualités BRVM effacées en 13 heures par le plafond global",
     "news.json gardait les 900 dépêches les plus récentes tous flux confondus : les flux de marché remplissaient tout en 13 heures "
     "et les dépêches BRVM et UEMOA de la veille disparaissaient (5 dépêches BRVM). Depuis le 20/10/2026, les flux BRVM, UEMOA et "
     "banques centrales gardent leurs 45 jours et chaque autre flux 120 dépêches au plus.",
     "news.json : au plus 120 dépêches par flux hors BRVM, UEMOA et banques centrales ; dépêches BRVM présentes au-delà de 24 h")
def b40(ctx):
    import time as _t
    it = (jl(ctx["D"], "news.json") or {}).get("items") or []
    if not it:
        return "orange", "news.json vide ou absent"
    c = collections.Counter(x.get("f") for x in it if x.get("c") not in ("BRVM", "UEMOA", "Banques centrales") and x.get("f") not in ("brvm-rapports", "sec"))
    trop = [f"{k} {v}" for k, v in c.items() if v > 120]
    now = ctx.get("maintenant") or _t.time()
    br = [x["t"] for x in it if x.get("c") == "BRVM" and x.get("t")]
    pb = ([f"flux au-delà de 120 dépêches : {', '.join(trop[:5])}"] if trop else []) + \
         ([f"dépêches BRVM limitées aux dernières {int((now - min(br)) / 3600)} h"] if br and now - min(br) < 86400 and len(br) < 350 else [])
    return ("orange", " ; ".join(pb)) if pb else ("vert", f"{len(it)} dépêches, dont {len(br)} BRVM")


@bug("B41", "2026-10-20", "Séance manquante dans une série US (variation du jour sur deux séances)",
     "La source des séries US n'avait pas la séance du 16/10/2026 pour UBER : la variation du jour du résumé portait sur deux "
     "séances (−1,45 % au lieu de −0,16 %). Depuis le 20/10/2026, le résumé prend la clôture précédente de la cotation quand la "
     "série n'a pas la séance précédente du calendrier (SPY, 0050) ; la série n'est pas complétée (aucune bougie inventée).",
     "séries US et Taïwan : séances du calendrier du marché (SPY, 0050) des 20 dernières séances toutes présentes (orange sinon, "
     "trou de la source) ; variation du résumé conforme à la cotation")
def b41(ctx):
    L = _ser_us(ctx)
    S = jl(ctx["D"], "summary.json") or {}
    mk = {x["id"]: x.get("mkt") for x in S.get("secs") or []}
    out = []
    for m, ref in (("US", "SPY"), ("TW", "0050")):
        cal = (L.get(ref) or {}).get("d") or []
        cal = cal[-20:]
        if not cal:
            continue
        for sid, se in L.items():
            if mk.get(sid) != m or sid == ref:
                continue
            have = set(se["d"][-40:])
            miss = [d for d in cal if d >= se["d"][0] and d not in have and d <= se["d"][-1]]
            if miss:
                out.append(f"{sid} {','.join(map(str, miss[:3]))}")
    return ("orange", f"{len(out)} série(s) avec une séance manquante (source) : " + "; ".join(out[:10])) if out else \
        ("vert", "aucune séance manquante sur 20 séances")


def _div_ctx(ctx):
    """versements (dividends.json) et opérations sur le capital du résumé (split : [[date, facteur], …]) des actions BRVM"""
    S = jl(ctx["D"], "summary.json") or {}
    spl = {s["id"]: s.get("split") or [] for s in S.get("secs") or [] if s.get("mkt") == "BRVM" and s.get("cls") == "Equity"}
    auj = int(S.get("asof")) if str(S.get("asof") or "").isdigit() else 99999999
    return jl(ctx["D"], "dividends.json") or [], spl, auj


def _i(s):
    return int(str(s)[:10].replace("-", ""))


@bug("B42", "2026-10-20", "Dividendes anciens non ajustés des opérations sur le capital (Sonatel, Onatel, BOA CI, BOA Niger, CBI BF)",
     "Les fractionnements ×10 de Sonatel (23/11/2012) et d'Onatel (29/11/2013) n'étaient pas appliqués aux dividendes d'avant "
     "(Sonatel 1998-2004 dix fois trop forts), et les actions gratuites de BOA CI (9 pour 41, 08/06/2016), BOA Niger (1 pour 19, "
     "03/06/2016) et CBI BF (3 pour 125, 21/09/2017) manquaient (cours et dividendes d'avant non ajustés). Depuis le 20/10/2026, ces "
     "opérations sont listées avec la date prouvée par les bulletins (seed/operations_historiques.json).",
     "facteur d'ajustement de chaque versement = produit des opérations postérieures (à 1e-4) ; aucune opération lue dans un avis "
     "et absente de la liste ; aucun saut de base (montant publié stable, montant ajusté ×3) sans opération entre deux exercices")
def b42(ctx):
    D, spl, auj = _div_ctx(ctx)
    if not D:
        return "orange", "dividends.json vide ou absent"
    bad, sauts = [], []
    for x in D:
        ds = x.get("det") or x.get("det0") or x.get("pay") or (f"{x['ex'] + 1}-06-30" if x.get("ex") else None)
        if not ds or x.get("t") not in spl:
            continue
        f = 1.0
        for e, k in spl[x["t"]]:
            if _i(ds) < e <= auj:
                f *= k
        if abs((x.get("adj") or 1.0) / f - 1) > 1e-4:
            bad.append(f"{x['t']} {x.get('ex')} facteur {x.get('adj')} pour {f:.4g}")
    by = collections.defaultdict(lambda: [0.0, 0.0, None])
    for x in D:
        if x.get("exc") or x.get("t") not in spl or not x.get("ex"):
            continue
        r = by[(x["t"], x["ex"])]
        r[0] += x.get("dps0") or x["dps"]
        r[1] += x["dps"]
        r[2] = max(r[2] or 0, _i(x.get("det") or x.get("pay") or f"{x['ex'] + 1}-06-30"))
    for t in spl:
        ex = sorted(e for (t_, e) in by if t_ == t)
        for a, b in zip(ex, ex[1:]):
            p0, a0, d0 = by[(t, a)]
            p1, a1, d1 = by[(t, b)]
            if p0 and a0 and 0.5 <= p1 / p0 <= 2 and not 1 / 3 <= a1 / a0 <= 3 and not any(d0 < e <= d1 for e, _ in spl[t]):
                sauts.append(f"{t} {a}→{b} publié {p0:g}→{p1:g}, ajusté {a0:g}→{a1:g}")
    ost = (jl(ctx["D"], "boc_check.json") or {}).get("ost_non_listees") or []
    pb = ([f"{len(bad)} facteur(s) faux : " + "; ".join(bad[:5])] if bad else []) + \
         ([f"{len(sauts)} saut(s) de base : " + "; ".join(sauts[:4])] if sauts else []) + \
         ([f"{len(ost)} opération(s) lue(s) dans un avis, absente(s) de la liste : " + "; ".join(map(str, ost[:4]))] if ost else [])
    return ("rouge", " ; ".join(pb)) if pb else ("vert", f"{len(D)} versements ajustés des opérations listées")


# dates de dividendes atypiques vérifiées sur document (avis, bulletin) : ne sont pas des erreurs
DATES_DIV_CONNUES = {("SLBC", 2023): "paiement 14/08/2024 avant le détachement du 12/09/2024 (cotation suspendue)",
                     ("CIEC", 2016): "paiement reporté au 20/09/2017 (avis n°161-2017)",
                     ("SNTS", 2020): "détachement le 12/05/2021, marché fermé",
                     ("BICC", 2000): "paiement un samedi, une seule source"}


@bug("B43", "2026-10-20", "Dates de détachement fausses reprises de la base (dimanches, 65 jours avant le paiement)",
     "Trois dates de détachement de la base tombaient un dimanche (BOABF 2016, PRSC 2015 et SGBC 2015, ces deux dernières 65 jours "
     "avant le paiement) ; BOAB et BOABF 2010 étaient payés un jour férié par une lecture concurrente. Depuis le 20/10/2026, une date "
     "de la base sans document officiel est retirée si elle n'est pas un jour de séance ou précède le paiement de plus de 15 jours ; "
     "les dates lues dans un document officiel ne sont jamais retirées.",
     "aucun détachement ni paiement un samedi ou un dimanche ; paiement entre 0 et 10 jours après le détachement ; détachement un "
     "jour de séance (hors dates vérifiées de DATES_DIV_CONNUES)")
def b43(ctx):
    import datetime as _dt
    D, spl, auj = _div_ctx(ctx)
    # calendrier des séances : réunion des dates des séries des actions (l'indice BRVMC a lui-même des trous, 03/05/2023)
    cal = set()
    for t_ in spl:
        cal |= set((jl(ctx["D"], f"s/{t_}.json") or {}).get("d") or [])
    out = []
    for x in D:
        if (x.get("t"), x.get("ex")) in DATES_DIV_CONNUES:
            continue
        for k in ("det", "pay"):
            if x.get(k) and _dt.date.fromisoformat(x[k][:10]).weekday() >= 5:
                out.append(f"{x['t']} {x.get('ex')} {k} {x[k]} (week-end)")
        if x.get("det") and x.get("pay"):
            g = (_dt.date.fromisoformat(x["pay"][:10]) - _dt.date.fromisoformat(x["det"][:10])).days
            if not 0 <= g <= 10:
                out.append(f"{x['t']} {x.get('ex')} paiement {g} j après le détachement")
        if x.get("det") and cal and min(cal) <= _i(x["det"]) <= max(cal) and _i(x["det"]) not in cal:
            out.append(f"{x['t']} {x.get('ex')} détachement {x['det']} hors séance")
    out = sorted(set(out))
    return ("orange", f"{len(out)} date(s) à vérifier : " + "; ".join(out[:8])) if out else \
        ("vert", f"dates cohérentes ({len(DATES_DIV_CONNUES)} cas vérifiés sur document)")


@bug("B44", "2026-10-20", "Événements en double et dates d'événements différentes du versement officiel",
     "events.json gardait 44 paires de quasi-doublons (versions successives du calendrier de paiement, documents « annule et "
     "remplace », documents republiés) et des événements de détachement ou de paiement à une autre date que le versement officiel "
     "(SOGC 2025 un mois plus tôt). Corrigé le 20/10/2026.",
     "au plus 10 paires d'événements de même société, même intitulé et même rubrique à 5 jours près (6 « Transactions sur "
     "dossier » et 4 paires sans preuve) ; aucune date « ex-dividende » un week-end")
def b44(ctx):
    import datetime as _dt
    E = jl(ctx["D"], "events.json") or []
    if not isinstance(E, list) or not E:
        return "orange", "events.json vide ou absent"
    by = collections.defaultdict(list)
    for e in E:
        if e.get("t") and e.get("d") and "annul" not in (e.get("ti") or "").lower():
            by[(e["t"], e.get("c"), re.sub(r"\W+", " ", (e.get("ti") or "").lower()).strip())].append(_dt.date.fromisoformat(e["d"][:10]))
    paires = sum(1 for v in by.values() for a, b in zip(sorted(v), sorted(v)[1:]) if (b - a).days <= 5)
    we = [f"{e['t']} {e['d']}" for e in E if "ex-dividende" in (e.get("c") or "").lower() and e.get("d")
          and _dt.date.fromisoformat(e["d"][:10]).weekday() >= 5]
    pb = ([f"{paires} paires d'événements en double (au plus 10 attendues)"] if paires > 10 else []) + \
         ([f"{len(we)} date(s) ex-dividende un week-end : " + ", ".join(we[:5])] if we else [])
    return ("orange", " ; ".join(pb)) if pb else ("vert", f"{len(E)} événements, {paires} paire(s) proches tolérée(s)")


@bug("B45", "2026-10-20", "Avis de dividendes numérisés comptés « lus » sans texte",
     "Un avis numérisé dont la reconnaissance de caractères n'avait pas abouti (temps du passage épuisé) était marqué « lu » sans "
     "texte et jamais relu : 134 documents, dont 67 avis de paiement de dividendes de 2017-2019 (parmi eux l'avis n°161-2017 du "
     "report du paiement CIE CI). Depuis le 20/10/2026, il est mis « à OCR » et relu au passage suivant (trois échecs au plus).",
     "branche dividendes : nombre d'avis de dividende sans texte en baisse d'un contrôle à l'autre tant qu'il n'est pas nul ; au plus "
     "12 documents lus sans texte")
def b45(ctx):
    dn = ctx.get("div_n")
    if dn is None:
        return "vert", "non vérifié ici (seulement dans le contrôle de GitHub)"
    n, r = dn.get("n") or {}, ctx.get("ref_div_n") or {}
    a, a0, l = n.get("avis_dividende_sans_texte"), r.get("avis_dividende_sans_texte"), n.get("lus_sans_texte")
    if a is None:
        return "orange", "compteurs absents de dividendes.json (lecture des dividendes pas encore passée avec la correction)"
    pb = ([f"{a} avis de dividende sans texte (contrôle précédent : {a0}), aucune relecture : " + ", ".join(x.rsplit('/', 1)[-1] for x in (dn.get('sans_texte') or [])[:3])]
          if a and a0 is not None and a >= a0 else []) + ([f"{l} documents lus sans texte (au plus 12)"] if (l or 0) > 12 else [])
    return ("orange", " ; ".join(pb)) if pb else ("vert", f"{a} avis de dividende sans texte" + (f" (précédent {a0})" if a0 is not None else "") + f", {l or 0} lus sans texte, {n.get('a_ocr', 0)} à relire")


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
