"""Usage : python3 cmp_fund.py <construction A> <construction B> — fundamentals.json et boc_check.json de deux constructions : séries changées par société et par poste."""
import json, sys, collections
A, B = sys.argv[1], sys.argv[2]
fa, fb = json.load(open(A + "/data/fundamentals.json")), json.load(open(B + "/data/fundamentals.json"))
add, chg, rem = collections.Counter(), collections.Counter(), collections.Counter()
ex = collections.defaultdict(list)
for t in sorted(set(fa) | set(fb)):
    a, b = fa.get(t) or {}, fb.get(t) or {}
    if not isinstance(a, dict) or not isinstance(b, dict):
        continue
    sa, sb = a.get("series") or {}, b.get("series") or {}
    for k in set(sa) | set(sb):
        xa, xb = sa.get(k) or {}, sb.get(k) or {}
        if not isinstance(xa, dict) or not isinstance(xb, dict):
            continue
        for y in set(xa) | set(xb):
            va, vb = xa.get(y), xb.get(y)
            if va == vb:
                continue
            if va is None:
                add[k] += 1; ex["+" + k].append(f"{t} {y} {vb}")
            elif vb is None:
                rem[k] += 1; ex["-" + k].append(f"{t} {y} {va}")
            elif isinstance(va, (int, float)) and isinstance(vb, (int, float)) and abs(va - vb) <= max(0.05, abs(va) * 1e-6):
                continue
            else:
                chg[k] += 1; ex["~" + k].append(f"{t} {y} {va} -> {vb}")
print("ajoutés", dict(add)); print("changés", dict(chg)); print("retirés", dict(rem))
for k in sorted(ex):
    if k[0] != "+" or k[1:] in ("ca", "resultat_net"):
        print(k, len(ex[k]), ex[k][:14])
ca, cb = json.load(open(A + "/data/boc_check.json")), json.load(open(B + "/data/boc_check.json"))
for k in sorted(set(ca) | set(cb)):
    if ca.get(k) != cb.get(k):
        print("boc_check", k, str(ca.get(k))[:300], "=>", str(cb.get(k))[:300])
