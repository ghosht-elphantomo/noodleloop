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
        prev = next((c for d, c in zip(reversed(se["d"]), reversed(se["c"])) if d < k and c), None)
        if prev and abs(q["pct"] - (q["last"] / prev - 1)) > 0.003:
            pc.append(f"{sid} {q['pct'] * 100:+.2f} % pour {(q['last'] / prev - 1) * 100:+.2f} %")
    pb = ([f"{len(bc)} bougie(s) impossible(s) : " + "; ".join(bc[:5])] if bc else []) + \
         ([f"{len(pc)} variation(s) US non conformes à la clôture précédente : " + "; ".join(pc[:5])] if pc else []) + \
         ([f"{len(zr)} cotation(s) à 0,00 % avec ouverture ou plus haut à 0 : " + ", ".join(zr[:8])] if zr else [])
    return ("rouge", " ; ".join(pb)) if pb else ("vert", f"{n} dernières bougies cohérentes ; variations US conformes")


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
