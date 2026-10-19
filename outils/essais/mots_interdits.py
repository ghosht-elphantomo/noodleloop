"""Usage : python3 mots_interdits.py <parcours.json> — textes suspects (NaN, undefined, null…) et noms de sources ou liens interdits
sur le site (texte visible, infobulles, liens)."""
import json, re, sys
P = json.load(open(sys.argv[1]))["pages"]
BAD = re.compile(r"\bNaN\b|\bundefined\b|\bInfinity\b|\[object Object\]|\bnull\b")
SRC = re.compile(r"sika|richbourse|afribourse|brvmetrics|github|vercel|@gmail|wayback|web\.archive", re.I)
n = 0
for h, v in P.items():
    blob = "\n".join([v.get("text", "")] + (v.get("titles") or []) + [" ".join(map(str, l)) for l in (v.get("links") or [])])
    for l in blob.splitlines():
        if BAD.search(l) or SRC.search(l):
            n += 1
            if n <= 30: print("  ", h, "|", l.strip()[:160])
print("mots interdits ou suspects :", n)
