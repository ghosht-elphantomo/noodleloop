"""Comptes de résultat de l'ancien plan comptable bancaire de l'UMOA (avant 2018) : deux tableaux (charges, produits), l'un
sous l'autre ou côte à côte, avec ou sans les codes de poste de la BCEAO (R01 … T85, V01 … X85), sans ligne « produit net
bancaire ». Lu par comptes.py (read_doc) pour le produit net bancaire et le résultat de l'exercice.

PNB = produits d'exploitation bancaire − charges d'exploitation bancaire (intérêts, crédit-bail, commissions, opérations
financières, divers : les cinq premiers postes de chaque tableau), définition du plan comptable bancaire. Rien n'est rendu si
tout le compte de résultat ne se vérifie pas, colonne par colonne : somme des postes de premier niveau = total de chaque
tableau, total des charges = total des produits, et total d'exploitation bancaire imprimé = somme de ses cinq postes.
Les années des colonnes sont lues dans l'en-tête du tableau. Bibliothèque standard uniquement."""
import re
import unicodedata


def nrm(x):
    x = re.sub(r"[’‘`´ʼ]", "'", x)
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower()
    x = re.sub(r"[^a-z0-9'/(). -]", " ", x)
    return re.sub(r"\s+", " ", x).strip()


# postes de premier niveau (codes de la BCEAO, puis libellés) ; les cinq premiers : exploitation bancaire
TOP_C = [("R01", r"^interets et charges assimilees"), ("R5E", r"^charges (?:sur |/ ?)(?:operations de )?credit.?-? ?bail"),
         ("R06", r"^commissions"), ("R4A", r"^charges (?:sur |/ ?)operations financieres"),
         ("R6U", r"^charges div(?:erses|\.)? d.? ?exploitation bancaire"), ("R8G", r"^achats? de marchandises"), ("R8J", r"^stocks? vendus"),
         ("R8L", r"^variations? de stocks"), ("S01", r"^frais generaux d.? ?exploitation"), ("T51", r"^dotations? (?:aux )?amort"),
         ("T6A", r"^solde en perte?s? de(?:s)? correct"), ("T01", r"^excedent (?:des )?dotations? (?:sur|/) ?(?:les )?reprises"),
         ("T80", r"^charges exception ?nelles"), ("T81", r"^pertes (?:sur|/) ?exercices anterieurs"),
         ("T82", r"^impots? (?:sur )?(?:le |les )?benefices?"), ("T83", r"^benefice(?! a repartir)|^resultat$|^resultat(?: net)?(?: de l.exercice)? ?\(? ?benefice")]
TOP_P = [("V01", r"^interets et produits assimile"), ("V5G", r"^produits (?:sur |/ ?)(?:operations de )?credit.?-? ?bail"),
         ("V06", r"^commissions"), ("V4A", r"^produits (?:sur |/ ?)operations financier"),
         ("V6T", r"^(?:produits divers|divers produits) d.? ?exploitation bancaire"), ("V8B", r"^marges? commerciales?"),
         ("V8C", r"^ventes? de marchandises"), ("V8D", r"^variations? de stocks"), ("W4R", r"^produits generaux d.? ?exploitation"),
         ("X51", r"^reprises? d.? ?amort"), ("X6A", r"^solde en benefice de(?:s)? correct"),
         ("X01", r"^excedent (?:des )?reprises? (?:sur|/) ?(?:les )?dotations"), ("X80", r"^produits exceptionnels"),
         ("X81", r"^(?:profits|produits) (?:sur|/) ?exercices anterieurs"), ("X83", r"^pertes?(?: de l.exercice| nette)?$|^resultat$|^resultat(?: net)?(?: de l.exercice)? ?\(? ?perte")]
CODE_C = {c: i for i, (c, _) in enumerate(TOP_C)}
CODE_P = {c: i for i, (c, _) in enumerate(TOP_P)}
TOT_C, TOT_P = ("T84", "T85"), ("X84", "X85")
RX_TOT_C = re.compile(r"^total(?: general)?(?: des charges| \( ?debit)?(?! des charges d)(?! d)")
RX_TOT_P = re.compile(r"^total(?: general)?(?: des produits| \( ?credit)?(?! des produits d)(?! d)")
RX_TBC = re.compile(r"^total (?:des )?charges d.? ?exploitation bancaire")
RX_TBP = re.compile(r"^total (?:des )?produits d.? ?exploitation bancaire")
CODE_RX = re.compile(r"^[RSTVWX][0-9][0-9A-Z]$")
NUM_RX = re.compile(r"^\(?-?\s?\d{1,3}(?:[ .,  ]\d{3})*\)?$|^-$")
SEG_RX = re.compile(r"\S+(?: \S+)*")


def _num(s):
    if s == "-":
        return 0
    neg = s.startswith("(") or s.startswith("-")
    v = int(re.sub(r"\D", "", s) or 0)
    return -v if neg else v


def entries(txt):
    """Postes lus ligne à ligne : (code, libellé, [(montant, colonne de fin)], ligne, rang dans la ligne, colonne de début)."""
    out = []
    pend = ""
    lines = txt.splitlines()
    for li, raw in enumerate(lines):
        # montant collé au libellé suivant (« 15 237 Intérêts et produits… ») ou libellé collé au montant : séparés
        raw = re.sub(r"(\d)\s(?=[A-Za-zÀ-ÿ])", r"\1  ", raw)
        raw = re.sub(r"([A-Za-zÀ-ÿ)'’.])\s(?=\(?-?\d)", r"\1  ", raw)
        segs = []
        for m in SEG_RX.finditer(raw):
            g, a, b = m.group(0), m.start(), m.end()
            mc = re.match(r"^([RSTVWX][0-9][0-9A-Z]) (\S.*)$", g)  # code collé au libellé
            if mc:
                segs.append((mc.group(1), a, a + 3))
                g, a = mc.group(2), a + 4
            mt = re.match(r"^(.*?[A-Za-z)'’.])\s((?:\(?-?\d{1,3}(?:[ .,  ]\d{3})+\)?|\d{1,3}))$", g)  # montant collé au libellé
            if mt:
                segs.append((mt.group(1), a, a + len(mt.group(1))))
                segs.append((mt.group(2), b - len(mt.group(2)), b))
            else:
                segs.append((g, a, b))
        cur, line_e = None, []
        for s, a, b in segs:
            if CODE_RX.match(s) and (cur is None or cur["nums"]):
                if cur:
                    line_e.append(cur)
                cur = {"code": s, "lab": "", "nums": [], "a": a}
            elif NUM_RX.match(s) and not re.match(r"^(?:19|20)\d\d$", s):
                if cur is None:
                    cur = {"code": None, "lab": "", "nums": [], "a": a}
                cur["nums"].append((_num(s), b))
            else:
                if cur is not None and cur["nums"]:
                    line_e.append(cur)
                    cur = None
                if cur is None:
                    cur = {"code": None, "lab": "", "nums": [], "a": a}
                cur["lab"] = (cur["lab"] + " " + s).strip()
        if cur:
            line_e.append(cur)
        for k, e in enumerate(line_e):
            e["lab"] = nrm(re.sub(r"^[-–•]\s*", "- ", e["lab"]))
            e["li"], e["k"], e["n"] = li, k, len(line_e)
            if not e["nums"]:
                pend = e
                e["skip"] = True
            else:
                e["prev"] = pend if pend and li - pend["li"] <= 2 and pend.get("k") == k else None
                pend = ""
            out.append(e)
    return [e for e in out if not e.get("skip") or e.get("code")]


def _top(e, side):
    tops = TOP_C if side == "c" else TOP_P
    codes = CODE_C if side == "c" else CODE_P
    if e.get("code") in codes:
        return codes[e["code"]]
    labs = [e["lab"]]
    if e.get("prev"):
        labs += [(e["prev"]["lab"] + " " + e["lab"]).strip(), e["prev"]["lab"]]
    for lab in labs:
        if lab.startswith("-"):
            continue
        for i, (_, rx) in enumerate(tops):
            if re.match(rx, lab):
                return i
    return None


def header_years(txt, i_line, ncol):
    """Années des colonnes d'après l'en-tête le plus proche au-dessus du premier poste (« 31/12/2007  31/12/2008 »,
    « 2 012  2 013 », « 2012  2013 ») : liste de ncol années, ou None."""
    lines = txt.splitlines()
    for li in range(i_line, max(-1, i_line - 25), -1):
        ln = lines[li]
        ys = [int(m.group(1)) for m in re.finditer(r"(?:3[01][/.-]12[/.-]|dec(?:embre)?[ -]?)?((?:19[89]|20[0-3])\d|(?<=[/.-])\d\d)(?![\d])", ln.replace("2 0", "20").replace("1 9", "19"))]
        ys = [y + 2000 if y < 100 else y for y in ys]
        ys = [y for y in ys if 1990 <= y <= 2035]
        if len(ys) >= ncol:
            ys = ys[:ncol] if len(set(ys[:ncol])) == ncol else None
            if ys and all(abs(a - b) == 1 for a, b in zip(ys, ys[1:])):
                return ys
    return None


def pnb(txt):
    """{colonne: {"pnb", "rn", "tc", "tp"}} si le compte de résultat se vérifie entièrement, sinon (None, raison)."""
    E = entries(txt)
    # repérage des tableaux : premier poste « intérêts et charges / produits assimilés »
    i_c = next((i for i, e in enumerate(E) if e.get("code") == "R01" or re.match(TOP_C[0][1], e["lab"])), None)
    i_p = next((i for i, e in enumerate(E) if e.get("code") == "V01" or re.match(TOP_P[0][1], e["lab"])), None)
    if i_c is None or i_p is None:
        return None, "blocs"
    side_by_side = E[i_c]["li"] == E[i_p]["li"]
    rows = {"c": [], "p": []}
    tot = {"c": None, "p": None}
    tb = {"c": None, "p": None}
    start = min(i_c, i_p)
    for idx_e in range(start, len(E)):
        e = E[idx_e]
        if not e["nums"]:
            continue
        if e.get("code"):
            side = "c" if e["code"][0] in "RST" else "p"
        elif side_by_side:
            side = "c" if e["k"] == 0 and e["n"] == 2 else ("p" if e["n"] == 2 else ("c" if e["a"] < E[i_p]["a"] - 5 else "p"))
        else:
            side = "c" if (idx_e < i_p) == (i_c < i_p) else "p"
        lab = e["lab"]
        if e.get("code") in (TOT_C if side == "c" else TOT_P) or (not e.get("code") and (RX_TOT_C if side == "c" else RX_TOT_P).match(lab)):
            nn = len(e["nums"])
            if side_by_side and e["n"] == 1 and nn >= 4 and nn % 2 == 0 and tot["c"] is None and tot["p"] is None:
                # une seule ligne TOTAL pour les deux tableaux côte à côte : charges puis produits
                tot["c"] = dict(e, nums=e["nums"][:nn // 2])
                tot["p"] = dict(e, nums=e["nums"][nn // 2:])
            elif tot[side] is None:
                tot[side] = e
            continue
        if (RX_TBC if side == "c" else RX_TBP).match(lab):
            tb[side] = e
            continue
        if tot[side] is None:
            rows[side].append(e)
        if tot["c"] is not None and tot["p"] is not None:
            break
    if tot["c"] is None or tot["p"] is None:
        return None, "totaux"
    res = {}
    ncol = min(len(tot["c"]["nums"]), len(tot["p"]["nums"]))
    if ncol < 1 or ncol > 3:
        return None, "colonnes"
    for side in ("c", "p"):
        ends = [b for _, b in tot[side]["nums"]][-ncol:]
        tot[side]["cols"] = [v for v, _ in tot[side]["nums"]][-ncol:]
        for e in rows[side] + ([tb[side]] if tb[side] else []):
            d = {}
            nums = e["nums"]
            if len(nums) > ncol:  # tiret suivi d'un montant : signe moins (« 911   -   2,301 »)
                mg, k_ = [], 0
                while k_ < len(nums):
                    v, b = nums[k_]
                    if v == 0 and k_ + 1 < len(nums) and nums[k_ + 1][0] != 0 and nums[k_ + 1][1] - b <= 14:
                        mg.append((-nums[k_ + 1][0], nums[k_ + 1][1]))
                        k_ += 2
                    else:
                        mg.append((v, b))
                        k_ += 1
                if len(mg) == ncol:
                    nums = mg
            if len(nums) > ncol:  # (tirets « - » des cases vides : ignorés s'il reste assez de montants)
                nd = [(v, b) for v, b in nums if not (v == 0 and b - 1 >= 0)]
                nums = nd if len(nd) >= 1 else nums
            if len(nums) == ncol:
                d = {j: v for j, (v, _) in enumerate(nums)}
            else:
                best = {}
                for v, b in nums:
                    j = min(range(ncol), key=lambda i: abs(ends[i] - b))
                    if abs(ends[j] - b) <= 8 and (j not in best or abs(ends[j] - b) < best[j][1]):
                        best[j] = (v, abs(ends[j] - b))
                d = {j: v for j, (v, _) in best.items()}
            e["cols"] = d
    for j in range(ncol):
        s_, b_, got = {}, {}, {}
        for side in ("c", "p"):
            seen = {}
            for e in rows[side]:
                i = _top(e, side)
                if i is None or i in seen:
                    continue
                seen[i] = e["cols"].get(j, 0)
            got[side] = seen
            s_[side] = sum(seen.values())
            b_[side] = sum(v for i, v in seen.items() if i < 5)
        tc, tp = tot["c"]["cols"][j], tot["p"]["cols"][j]
        tol = max(3, abs(tc) * 1e-5)
        if not (abs(s_["c"] - tc) <= tol and abs(s_["p"] - tp) <= tol and abs(tc - tp) <= tol):
            return None, f"sommes (colonne {j + 1} : charges {s_['c']} / {tc}, produits {s_['p']} / {tp})"
        for side in ("c", "p"):  # total d'exploitation bancaire imprimé : doit être la somme de ses cinq postes
            if tb[side] and j in tb[side]["cols"] and abs(tb[side]["cols"][j] - b_[side]) > tol:
                return None, "total d'exploitation bancaire"
        res[j] = {"pnb": b_["p"] - b_["c"], "pg": got["p"].get(8, 0), "rn": got["c"].get(15, 0) - got["p"].get(14, 0), "tc": tc, "tp": tp,
                  "n": (len(got["c"]), len(got["p"]))}
    hy = header_years(txt, min(E[i_c]["li"], E[i_p]["li"]), ncol)
    for j in res:
        res[j]["y"] = hy[j] if hy else None
    return res, "ok"
