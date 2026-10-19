"""Usage : python3 comparer_parcours.py <parcours avant.json> <parcours après.json> — pages ajoutées, retirées et changées
(heures masquées), avec les premières lignes changées de chaque page."""
import json, re, sys, difflib
a, b = json.load(open(sys.argv[1]))["pages"], json.load(open(sys.argv[2]))["pages"]
norm = lambda t: re.sub(r"\d{1,2}:\d{2}(:\d{2})?", "HH:MM", t)
print("pages seulement avant", sorted(set(a) - set(b)))
print("pages seulement après", sorted(set(b) - set(a)))
ch = [k for k in sorted(set(a) & set(b)) if norm(a[k].get("text", "")) != norm(b[k].get("text", ""))]
print("pages changées", len(ch))
for k in ch:
    d = [l for l in difflib.unified_diff(norm(a[k]["text"]).split("\n"), norm(b[k]["text"]).split("\n"), lineterm="", n=0)
         if not l.startswith(("---", "+++", "@@"))]
    print("==", k, len(d)); print("\n".join("   " + x[:160] for x in d[:6]))
