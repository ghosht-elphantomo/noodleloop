"""Usage : python3 fa_ab.py <construction A> <construction B> — fichiers FA de deux constructions, alignés par année : valeurs ajoutées, changées, retirées (Y, C, C2, R)."""
import json, glob, os, collections, sys
A, B = sys.argv[1], sys.argv[2]
cnt = collections.Counter(); ex = collections.defaultdict(list)
def rows_C(c):
    out = {}
    if not c: return out
    ys = c.get('y') or []
    for sec in c.get('s') or []:
        for r in sec[2]:
            for i, y in enumerate(ys):
                out[(c.get('per'), c.get('std'), r[0], y)] = r[2][i]
    return out
def rows_R(R):
    out = {}
    if not R: return out
    ys = R.get('y') or []
    for g in R.get('g') or []:
        for r in g[1]:
            for i, y in enumerate(ys): out[(g[0], r[0], y)] = r[3][i]
    return out
def rows_Y(Y):
    out = {}
    if not Y: return out
    ys = Y.get('y') or []
    for k, v in Y.items():
        if k == 'y' or not isinstance(v, list): continue
        for i, y in enumerate(ys): out[(k, y)] = v[i] if i < len(v) else None
    return out
for f in sorted(glob.glob(A + '/data/fa/*.json')):
    t = os.path.basename(f)[:-5]; a = json.load(open(f)); b = json.load(open(f.replace(A, B)))
    for part, fn in (('Y', rows_Y), ('C', rows_C), ('C2', rows_C), ('R', rows_R)):
        x, z = fn(a.get(part)), fn(b.get(part))
        for k in set(x) | set(z):
            va, vb = x.get(k), z.get(k)
            if va == vb: continue
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and abs(va - vb) <= 1e-6 * max(1, abs(va)): continue
            kind = 'ajout' if va is None else ('retrait' if vb is None else 'chg')
            cnt[(part, kind)] += 1; ex[(part, kind)].append((t, k, va, vb))
    for k in a:
        if k in ('Y', 'C', 'C2', 'R', 'mh'): continue
        if a.get(k) != b.get(k): cnt[('scal', 'chg')] += 1; ex[('scal', 'chg')].append((t, k, a.get(k), b.get(k)))
for k, v in sorted(cnt.items()): print(k, v)
for k in ex:
    if k[1] != 'ajout' or k[0] in ('Y', 'C2'):
        print('==', k); [print('  ', str(e)[:200]) for e in ex[k][:30]]
