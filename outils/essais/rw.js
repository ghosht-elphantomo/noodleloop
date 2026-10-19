// applique la réécriture du relais (api/data.js) à une copie des données, comme le ferait Vercel
const fs = require('fs'), path = require('path');
const src = fs.readFileSync(process.argv[2], 'utf8');
const a = src.indexOf('const tok = '), b = src.indexOf('\n', src.indexOf('const ALIAS = '));
const { docRw, ALIAS } = new Function(src.slice(a, b) + '\nreturn { docRw, ALIAS };')();
const [, , , from, to] = process.argv;
let n = 0, ch = 0;
(function walk(d) { for (const f of fs.readdirSync(d)) { const p = path.join(d, f); const st = fs.statSync(p);
  if (st.isDirectory()) { walk(p); continue; }
  const rel = path.relative(from, p), out = path.join(to, rel); fs.mkdirSync(path.dirname(out), { recursive: true });
  if (p.endsWith('.json')) { const t = fs.readFileSync(p, 'utf8'), r = docRw(t, rel); if (r !== t) ch++; JSON.parse(r); fs.writeFileSync(out, r); n++; }
  else fs.copyFileSync(p, out); } })(from);
for (const [al, real] of Object.entries(ALIAS)) fs.copyFileSync(path.join(to, real), path.join(to, al));
console.log('fichiers', n, 'modifiés', ch, '(tous restent du JSON valide)');
