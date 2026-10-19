/* ================= FQT — PORTF : import de relevés (CSV, Excel, PDF à texte, lignes collées), sauvegarde et restauration ================= */
'use strict';
/* Tout est lu dans ce navigateur : le fichier n'est envoyé nulle part et n'est pas gardé. Rien n'est enregistré avant l'écran de
   contrôle : seules les lignes validées deviennent des positions (comme une saisie à la main). */
const IMP_MAX = 15e6;
const impN = s => String(s == null ? '' : s).normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9]+/g, ' ').trim();
/* nombre écrit à la française ou à l'anglaise (« 1 234,50 », « 1.234,50 », « 1,234.50 ») ; null si ce n'est pas un nombre */
function impNum(v) {
  if (v == null || v === '') return null; if (typeof v === 'number') return isFinite(v) ? v : null;
  let s = String(v).replace(/[  \s']/g, '').replace(/(F\s?CFA|XOF|CFA|EUR|USD|€|\$)$/i, '');
  if (!/^[-+]?\d[\d.,]*$/.test(s)) return null;
  const lc = s.lastIndexOf(','), ld = s.lastIndexOf('.');
  if (lc >= 0 && ld >= 0) s = lc > ld ? s.replace(/\./g, '').replace(',', '.') : s.replace(/,/g, '');
  else if (lc >= 0) s = s.split(',').length > 2 || (s.length - lc - 1 === 3 && !/^[-+]?0,/.test(s)) ? s.replace(/,/g, '') : s.replace(',', '.');
  else if (ld >= 0) { const p = s.split('.'); if (p.length > 2 || (p[1].length === 3 && !/^[-+]?0$/.test(p[0]))) s = s.replace(/\./g, ''); }
  const n = parseFloat(s); return isFinite(n) ? n : null;
}
/* ---------- lecture des fichiers ---------- */
function impSplit(l, sp) { const out = []; let cur = '', q = false; for (let i = 0; i < l.length; i++) { const ch = l[i]; if (q) { if (ch === '"') { if (l[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += ch; } else if (ch === '"') q = true; else if (ch === sp) { out.push(cur.trim()); cur = ''; } else cur += ch; } out.push(cur.trim()); return out; }
function impText(txt) {
  const L = String(txt).replace(/\r\n?/g, '\n').split('\n').filter(l => l.trim()), head = L.slice(0, 40);
  let sp = null, best = 0; for (const s of [';', '\t', '|', ',']) { const n = head.filter(l => impSplit(l, s).length >= 2).length; if (n > best) { best = n; sp = s; } }
  return L.map(l => sp ? impSplit(l, sp) : l.trim().split(/\s{2,}/));
}
async function impInflate(u8, raw) { const st = new Blob([u8]).stream().pipeThrough(new DecompressionStream(raw ? 'deflate-raw' : 'deflate')); return new Uint8Array(await new Response(st).arrayBuffer()); }
async function impUnzip(buf, want) {
  const b = new Uint8Array(buf), dv = new DataView(buf); let e = -1;
  for (let i = b.length - 22; i >= Math.max(0, b.length - 66000); i--) if (dv.getUint32(i, true) === 0x06054b50) { e = i; break; }
  if (e < 0) throw new Error('fichier Excel illisible');
  const n = dv.getUint16(e + 10, true), out = {}; let p = dv.getUint32(e + 16, true);
  for (let k = 0; k < n && p + 46 <= b.length; k++) {
    if (dv.getUint32(p, true) !== 0x02014b50) break;
    const meth = dv.getUint16(p + 10, true), csz = dv.getUint32(p + 20, true), nl = dv.getUint16(p + 28, true), xl = dv.getUint16(p + 30, true), cl = dv.getUint16(p + 32, true), lho = dv.getUint32(p + 42, true);
    const name = new TextDecoder().decode(b.subarray(p + 46, p + 46 + nl)); p += 46 + nl + xl + cl;
    if (!want(name)) continue;
    const st = lho + 30 + dv.getUint16(lho + 26, true) + dv.getUint16(lho + 28, true), data = b.subarray(st, st + csz);
    out[name] = meth === 0 ? data : meth === 8 ? await impInflate(data, true) : null;
  }
  return out;
}
const impCol = ref => { const m = /^([A-Z]+)/.exec(ref || ''); if (!m) return -1; let n = 0; for (const ch of m[1]) n = n * 26 + ch.charCodeAt(0) - 64; return n - 1; };
async function impXlsx(buf) {
  const Z = await impUnzip(buf, n => /^xl\/(sharedStrings\.xml|workbook\.xml|_rels\/workbook\.xml\.rels|worksheets\/[^/]+\.xml)$/.test(n));
  const td = new TextDecoder(), X = u => new DOMParser().parseFromString(td.decode(u), 'application/xml'), T = (d, t) => [...d.getElementsByTagNameNS('*', t)];
  const ss = Z['xl/sharedStrings.xml'] ? T(X(Z['xl/sharedStrings.xml']), 'si').map(si => T(si, 't').map(t => t.textContent).join('')) : [];
  const sheets = Object.keys(Z).filter(k => k.startsWith('xl/worksheets/') && Z[k]).sort((a, b) => (parseInt(a.replace(/\D/g, '')) || 0) - (parseInt(b.replace(/\D/g, '')) || 0));
  return sheets.map(k => T(X(Z[k]), 'row').map(r => { const cells = []; for (const c of T(r, 'c')) { const t = c.getAttribute('t'), v0 = T(c, 'v')[0], col = impCol(c.getAttribute('r'));
    let v = t === 's' ? ss[+(v0 ? v0.textContent : -1)] ?? '' : t === 'inlineStr' ? T(c, 't').map(x => x.textContent).join('') : v0 ? v0.textContent : '';
    if (t !== 's' && t !== 'inlineStr' && t !== 'str' && v !== '' && isFinite(+v)) v = +v;
    if (col >= 0) cells[col] = v; else cells.push(v); } return Array.from(cells, x => x ?? ''); }));
}
/* PDF : texte des pages quand il est écrit en clair (relevés produits par un logiciel) ; un scan ou une police codée n'est pas lu */
function impPdfStr(s, i) { let out = '', d = 1; i++; for (; i < s.length && d; i++) { const ch = s[i]; if (ch === '\\') { const nx = s[++i]; if (/[0-7]/.test(nx)) { let o = nx; while (o.length < 3 && /[0-7]/.test(s[i + 1])) o += s[++i]; out += String.fromCharCode(parseInt(o, 8)); } else out += { n: '\n', r: '\r', t: '\t', b: '', f: '' }[nx] ?? (nx === '\n' || nx === '\r' ? '' : nx); } else if (ch === '(') { d++; out += ch; } else if (ch === ')') { if (--d) out += ch; } else out += ch; } return [out, i]; }
function impPdfOps(c, items, st) {
  let i = 0, x = 0, y = 0, lx = 0, ly = 0, lead = 0; const nums = [], strs = [], n = c.length;
  const show = t => { if (t.trim()) items.push({ p: st.p, x, y, t }); };
  while (i < n) {
    const ch = c[i];
    if (ch === '(') { const [t, j] = impPdfStr(c, i); strs.push(t); i = j; continue; }
    if (ch === '<' && c[i + 1] !== '<') { const j = c.indexOf('>', i); const h = c.slice(i + 1, j).replace(/\s/g, ''); strs.push(h.length % 4 === 0 && /^00/.test(h) ? '\u0000' : h.replace(/(..)/g, (m, a) => String.fromCharCode(parseInt(a, 16)))); i = j + 1; continue; }
    if (ch === '[') { strs.push('['); i++; continue; }
    if (ch === ']') { const k = strs.lastIndexOf('['); const parts = strs.splice(k); parts.shift(); strs.push(parts.join('')); i++; continue; }
    if (/[-+.\d]/.test(ch)) { const m = /^[-+]?(\d+\.?\d*|\.\d+)/.exec(c.slice(i, i + 32)); if (m) { nums.push(+m[0]); i += m[0].length; if (strs.length && strs[strs.length - 1] !== '[' && +m[0] < -180 && strs.lastIndexOf('[') >= 0) strs[strs.length - 1] += ' '; continue; } }
    if (/[A-Za-z'"*]/.test(ch)) { const m = /^[A-Za-z'"*]+/.exec(c.slice(i, i + 8)); const op = m[0]; i += op.length;
      if (op === 'BT') { x = lx = 0; y = ly = 0; } else if (op === 'Tm' && nums.length >= 6) { x = lx = nums[nums.length - 2]; y = ly = nums[nums.length - 1]; }
      else if ((op === 'Td' || op === 'TD') && nums.length >= 2) { lx += nums[nums.length - 2]; ly += nums[nums.length - 1]; x = lx; y = ly; if (op === 'TD') lead = -nums[nums.length - 1]; }
      else if (op === 'TL' && nums.length) lead = nums[nums.length - 1];
      else if (op === 'T*') { ly -= lead || 12; x = lx; y = ly; }
      else if (op === 'Tj' || op === 'TJ') { const t = strs.pop(); if (t != null) show(t); }
      else if (op === "'" || op === '"') { ly -= lead || 12; x = lx; y = ly; const t = strs.pop(); if (t != null) show(t); }
      else if (op === 'ET') { /* fin du bloc de texte */ }
      nums.length = 0; if (op !== 'TJ' && op !== 'Tj') strs.length = 0; continue; }
    i++;
  }
}
/* ASCII85 (filtre /ASCII85Decode) */
function impA85(u8) { const s = String.fromCharCode.apply(null, u8).replace(/\s/g, '').replace(/^<~/, ''), e = s.indexOf('~>'), t = e >= 0 ? s.slice(0, e) : s, out = []; let g = [];
  for (let i = 0; i < t.length; i++) { const ch = t[i]; if (ch === 'z' && !g.length) { out.push(0, 0, 0, 0); continue; } g.push(ch.charCodeAt(0) - 33); if (g.length === 5) { let v = 0; for (const d of g) v = v * 85 + d; out.push(v >>> 24 & 255, v >>> 16 & 255, v >>> 8 & 255, v & 255); g = []; } }
  if (g.length) { const n = g.length; while (g.length < 5) g.push(84); let v = 0; for (const d of g) v = v * 85 + d; const b = [v >>> 24 & 255, v >>> 16 & 255, v >>> 8 & 255, v & 255]; out.push(...b.slice(0, n - 1)); }
  return new Uint8Array(out); }
async function impPdf(buf) {
  const b = new Uint8Array(buf); let s = ''; for (let i = 0; i < b.length; i += 65536) s += String.fromCharCode.apply(null, b.subarray(i, i + 65536));
  const items = [], st = { p: 0 }; let pos = 0, bad = 0;
  while ((pos = s.indexOf('stream', pos)) >= 0) {
    if (s.slice(pos - 3, pos) === 'end') { pos += 6; continue; }
    let a = pos + 6; if (s[a] === '\r') a++; if (s[a] === '\n') a++;
    const e = s.indexOf('endstream', a); if (e < 0) break;
    const dict = s.slice(Math.max(0, s.lastIndexOf('obj', pos)), pos); pos = e + 9;
    if (/\/(Image|XRef|ObjStm|Metadata|FontFile|Length1|Length2|EmbeddedFile)\b/.test(dict) || /\/Subtype\s*\/(Image|Type1C|CIDFontType0C|OpenType)/.test(dict)) continue;
    let data = b.subarray(a, e); if (/\/(DCTDecode|JPXDecode|CCITTFaxDecode|JBIG2Decode|LZWDecode|RunLengthDecode)/.test(dict)) continue;
    if (/\/ASCII85Decode/.test(dict)) data = impA85(data);
    if (/\/FlateDecode/.test(dict)) { try { data = await impInflate(data, false); } catch (err) { try { data = await impInflate(data.subarray(0, data.length - 2), false); } catch (err2) { bad++; continue; } } }
    let c = ''; for (let i = 0; i < data.length; i += 65536) c += String.fromCharCode.apply(null, data.subarray(i, i + 65536));
    if (!/\bBT\b/.test(c) || !/T[jJ]\b/.test(c)) continue;
    st.p++; impPdfOps(c, items, st);
  }
  const txt = items.filter(o => o.t !== '\u0000');
  if (txt.length < 5) return null;
  /* lignes : même page, même hauteur (à 2 points près) ; cellules dans l'ordre horizontal */
  const rows = [], by = new Map();
  for (const o of txt) { const k = o.p + ':' + Math.round(o.y / 2); if (!by.has(k)) { by.set(k, []); rows.push({ p: o.p, y: o.y, c: by.get(k) }); } by.get(k).push(o); }
  rows.sort((a, b) => a.p - b.p || b.y - a.y);
  const R = rows.map(r => r.c.sort((a, b) => a.x - b.x).map(o => ({ t: o.t.replace(/\s+/g, ' ').trim(), x: o.x })).filter(o => o.t));
  const T = R.map(r => r.map(o => o.t)); T.xs = R.map(r => r.map(o => o.x)); return T;
}
/* ---------- reconnaissance des lignes ---------- */
const IMP_SKIP = /\b(TOTAL|SOUS TOTAL|SOLDE|ESPECES|LIQUIDITES|CASH|TOTAUX|REPORT|PAGE)\b/;
const IMP_HQ = /QUANTIT|\bQTE\b|\bQTY\b|NOMBRE|\bNB\b|QUANTITY|SHARES|UNITS|\bPOSITION\b/, IMP_HC = /PRIX (DE )?REVIENT|\bPRU\b|\bCMP\b|COUT (UNITAIRE )?MOYEN|PRIX MOYEN|COURS MOYEN|PRIX D ?ACHAT|COURS D ?ACHAT|AVERAGE COST|AVG COST|COST BASIS|UNIT COST/;
const IMP_HNO = /VALEUR (DE )?(MARCHE|BOURSIERE|TOTALE|ACTUELLE)|VALORISATION|MONTANT|PLUS|MOINS|VARIATION|POIDS|%/;
function impDict(isin) {
  const D = []; const add = (k, s, w) => { k = impN(k); if (k.length >= 3) D.push([` ${k} `, s, w]); };
  for (const s of Q.sum.secs) { if (s.cls !== 'Equity' && s.cls !== 'ETF' && s.cls !== 'Fund') continue; for (const nm of [s.short, s.n]) if (nm) { add(nm, s, 2); const v = impN(nm); if (/\bCI\b/.test(v)) add(v.replace(/\bCI\b/, 'COTE D IVOIRE'), s, 2); if (/^BOA\b/.test(v)) add(v.replace(/^BOA\b/, 'BANK OF AFRICA'), s, 2); } }
  for (const [k, id] of Object.entries(SEC_ALIAS)) if (Q.by[id]) add(k, Q.by[id], 1);
  return D;
}
function impSec(cells, ctx) {
  const txt = cells.filter(c => typeof c === 'string' && impNum(c) == null);
  for (const c of txt) { const m = String(c).toUpperCase().match(/\b[A-Z]{2}[A-Z0-9]{9}\d\b/); if (m && ctx.isin[m[0]] && Q.by[ctx.isin[m[0]]]) return { s: Q.by[ctx.isin[m[0]]], how: 'ISIN' }; }
  for (const c of txt) { const u = String(c).trim().toUpperCase(); if (Q.by[u] && u.length >= 2) return { s: Q.by[u], how: 'code' }; }
  const all = ` ${impN(txt.join(' '))} `;
  for (const w of all.trim().split(' ')) if (w.length >= 4 && Q.by[w] && Q.by[w].mkt === 'BRVM') return { s: Q.by[w], how: 'code' };
  let best = 0, hit = new Map(); for (const [k, s, wgt] of ctx.dict) if (all.includes(k)) { const sc = k.length + wgt; if (sc > best) { best = sc; hit = new Map([[s.id, s]]); } else if (sc === best) hit.set(s.id, s); }
  if (hit.size === 1) return { s: [...hit.values()][0], how: 'nom' };
  if (hit.size > 1) return { amb: [...hit.values()] };
  const r = txt.length ? resolveSec(txt.join(' ')) : null; if (r && !r.amb) return { s: r, how: 'nom' }; if (r && r.amb) return { amb: r.amb };
  return null;
}
function impRows(table, ctx) {
  let hq = -1, hc = -1, hr = -1;
  for (let i = 0; i < Math.min(table.length, 40) && hr < 0; i++) { const H = table[i].map(impN); const q = H.findIndex(h => IMP_HQ.test(h) && !IMP_HNO.test(h)); if (q >= 0) { hr = i; hq = q; hc = H.findIndex(h => IMP_HC.test(h)); } }
  const out = []; let skipped = 0, hx = hr >= 0 && table.xs ? table.xs[hr] : null;
  table.forEach((cells0, i) => {
    if (i <= hr) return;
    /* PDF : chaque morceau de texte est rangé dans la colonne d'en-tête la plus proche (les cases vides ne sont pas écrites) */
    let cells = cells0; if (hx && table.xs[i]) { cells = Array(table[hr].length).fill(''); cells0.forEach((t, j) => { const x = table.xs[i][j]; let k = 0; hx.forEach((h, n) => { if (Math.abs(h - x) < Math.abs(hx[k] - x)) k = n; }); cells[k] = cells[k] ? cells[k] + ' ' + t : t; }); } const all = impN(cells.join(' ')); if (!all) return;
    const nums = cells.map(impNum);
    if (IMP_SKIP.test(` ${all} `) || !nums.some(v => v != null)) { skipped++; return; }
    const sc = impSec(cells, ctx);
    let q = hq >= 0 ? nums[hq] : null, c = hc >= 0 ? nums[hc] : null, guess = false;
    const ne = cells.filter(x => x !== '' && x != null);
    if (hq < 0 && ne.length >= 2 && ne.length <= 3 && impNum(ne[0]) == null && ne.slice(1).every(x => impNum(x) != null)) { q = impNum(ne[1]); c = ne.length === 3 ? impNum(ne[2]) : null; }
    else if (hq < 0) { const k = nums.findIndex((v, j) => v != null && v > 0 && !(typeof cells[j] === 'string' && /\b[A-Z]{2}[A-Z0-9]{9}\d\b/.test(cells[j]))); q = k >= 0 ? nums[k] : null; guess = q != null; }
    if (!sc && q == null) { skipped++; return; }
    out.push({ src: cells.filter(x => x !== '').join(' · ').slice(0, 140), s: sc && sc.s ? sc.s.id : '', how: sc && sc.s ? sc.how : '', amb: sc && sc.amb ? sc.amb.map(x => x.id) : [], q: q != null && q > 0 ? q : null, c: c != null && c > 0 ? c : null, guess, on: !!(sc && sc.s && q > 0) });
  });
  return { rows: out, skipped, head: hr >= 0 };
}
async function impCtx() { const PR = await getJSON('profiles.json').catch(() => null), isin = {}; if (PR) for (const [id, p] of Object.entries(PR)) if (p && p.isin) isin[String(p.isin).toUpperCase()] = id; return { isin, dict: impDict(isin) }; }
async function impFile(f) {
  if (!f) return; if (f.size > IMP_MAX) { toast('Fichier trop volumineux (plus de 15 Mo).'); return; }
  const nm = f.name || 'fichier', ext = (nm.split('.').pop() || '').toLowerCase(), I = { name: nm, rows: [], mode: 'maj', msg: '' };
  try {
    if (/^image\//.test(f.type) || /^(jpe?g|png|heic|heif|webp|gif)$/.test(ext)) { I.msg = 'Les photos de relevés ne sont pas encore lues par le terminal (il faudrait un module de lecture d’images ajouté au site). En attendant : téléchargez le relevé en Excel, CSV ou PDF depuis l’espace client de votre SGI, ou copiez les lignes et collez-les (action « Importer (coller) »).'; }
    else {
      const buf = await f.arrayBuffer(), h = new Uint8Array(buf.slice(0, 8)); const ctx = await impCtx(); let tables = [];
      if (h[0] === 0x50 && h[1] === 0x4b) { if (typeof DecompressionStream === 'undefined') throw new Error('ce navigateur ne sait pas ouvrir les fichiers Excel : mettez-le à jour ou utilisez un fichier CSV'); tables = await impXlsx(buf); }
      else if (h[0] === 0xd0 && h[1] === 0xcf) throw new Error('ancien format Excel (.xls) : enregistrez le fichier au format .xlsx ou .csv');
      else if (h[0] === 0x25 && h[1] === 0x50 && h[2] === 0x44 && h[3] === 0x46) { if (typeof DecompressionStream === 'undefined') throw new Error('ce navigateur ne sait pas ouvrir les PDF : mettez-le à jour ou utilisez un fichier CSV'); const t = await impPdf(buf); if (!t) throw new Error('ce PDF ne contient pas de texte lisible (document scanné ou police codée) : téléchargez le relevé en Excel ou CSV, ou collez les lignes'); tables = [t]; }
      else { let txt = new TextDecoder('utf-8', { fatal: false }).decode(buf); if (txt.includes('�')) txt = new TextDecoder('windows-1252').decode(buf); tables = [impText(txt)]; }
      let best = null; for (const t of tables) { const r = impRows(t, ctx); if (!best || r.rows.filter(x => x.on).length > best.rows.filter(x => x.on).length) best = r; }
      Object.assign(I, best || { rows: [], skipped: 0 });
      if (!I.rows.length) I.msg = 'Aucune ligne de position reconnue dans ce fichier. Vérifiez qu’il s’agit bien du relevé des titres (une ligne par titre avec sa quantité).';
    }
  } catch (e) { I.msg = 'Lecture impossible : ' + esc(e.message || String(e)) + '.'; }
  ST.portImp = I; ST.tab.PORT = 'p'; go('PORTF');
}
function impPasted(txt) { impCtx().then(ctx => { const r = impRows(impText(txt), ctx); ST.portImp = { name: 'lignes collées', mode: 'maj', msg: r.rows.length ? '' : 'Aucune ligne de position reconnue.', ...r }; render(); }); }
function impBackup(P) {
  const d = new Date().toISOString().slice(0, 10), o = { format: 'FQT-portefeuille', v: 1, date: new Date().toISOString(), base: P.base, pos: P.pos };
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(o, null, 1)], { type: 'application/json' })); a.download = `portefeuille-fqt-${d}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
async function impRestore(f) {
  if (!f) return; const I = { name: f.name || 'sauvegarde', rows: [], mode: 'rempl', msg: '', bk: true };
  try { const o = JSON.parse(await f.text()); if (!o || o.format !== 'FQT-portefeuille' || !Array.isArray(o.pos)) throw new Error('ce fichier n’est pas une sauvegarde du portefeuille FQT');
    I.base = ['XOF', 'EUR', 'USD'].includes(o.base) ? o.base : null; I.date = o.date;
    I.rows = o.pos.filter(p => p && typeof p.id === 'string').map(p => ({ src: `${p.id} · ${p.q}${p.c != null ? ' · ' + p.c : ''}`, s: Q.by[p.id] ? p.id : '', how: Q.by[p.id] ? 'sauvegarde' : '', amb: [], q: +p.q > 0 ? +p.q : null, c: +p.c > 0 ? +p.c : null, sp: Array.isArray(p.sp) ? p.sp : undefined, on: !!(Q.by[p.id] && +p.q > 0) }));
  } catch (e) { I.msg = 'Restauration impossible : ' + esc(e.message || String(e)) + '.'; }
  ST.portImp = I; ST.tab.PORT = 'p'; go('PORTF');
}
const impPick = (accept, fn) => { const f = document.createElement('input'); f.type = 'file'; f.accept = accept; f.style.display = 'none'; document.body.appendChild(f); f.onchange = () => { const x = f.files && f.files[0]; f.remove(); fn(x); }; f.click(); };
/* ---------- écran de contrôle ---------- */
function impScreen(m) {
  const I = ST.portImp, P = portLoad(), have = new Map(P.pos.map(p => [p.id, p]));
  setTitle('Portfolio Import');
  const fin = () => { ST.portImp = null; render(); };
  const ok = () => I.rows.filter(r => r.on && r.s && Q.by[r.s] && r.q > 0);
  const apply = () => {
    const L = ok(); if (!L.length) { toast('Aucune ligne cochée avec un titre et une quantité.'); return; }
    const agg = new Map(); for (const r of L) { const a = agg.get(r.s) || { id: r.s, q: 0, cq: 0, cv: 0, sp: r.sp }; a.q += r.q; if (r.c) { a.cq += r.q; a.cv += r.q * r.c; } agg.set(r.s, a); }
    const NP = I.mode === 'rempl' ? { base: I.base || P.base, pos: [] } : P;
    for (const a of agg.values()) { const c = a.cq === a.q && a.cq ? a.cv / a.cq : null, ex = NP.pos.find(x => x.id === a.id); if (ex) { ex.q = a.q; if (c) ex.c = c; } else NP.pos.push({ id: a.id, q: a.q, c, ...(a.sp ? { sp: a.sp } : {}) }); }
    portSave(NP); ST.portImp = null; toast(`${agg.size} position${agg.size > 1 ? 's' : ''} ${I.mode === 'rempl' ? 'enregistrée' + (agg.size > 1 ? 's' : '') + ' (portefeuille remplacé)' : 'importée' + (agg.size > 1 ? 's' : '')}.`); render();
  };
  setActs([{ n: 91, l: 'Valider l’import', run: apply }, { n: 92, l: 'Annuler', run: fin }]);
  const opts = r => { const ids = [...new Set([r.s, ...r.amb].filter(Boolean))], rest = Q.sum.secs.filter(s => (s.cls === 'Equity' || s.cls === 'ETF') && !ids.includes(s.id)).sort((a, b) => (a.mkt === 'BRVM' ? 0 : 1) - (b.mkt === 'BRVM' ? 0 : 1) || a.id.localeCompare(b.id));
    return `<option value="">${r.amb.length && !r.s ? '— choisir —' : '— non reconnu —'}</option>${ids.map(id => `<option value="${id}"${id === r.s ? ' selected' : ''}>${id} · ${esc(Q.by[id].short || Q.by[id].n)}</option>`).join('')}<option disabled>──────────</option>${rest.map(s => `<option value="${s.id}">${s.id} · ${esc(s.short || s.n)}</option>`).join('')}`; };
  const state = r => { const s = r.s && Q.by[r.s]; if (!s) return r.amb.length ? '<span class="am">plusieurs titres possibles : choisir</span>' : '<span class="dn">titre non reconnu</span>'; if (!(r.q > 0)) return '<span class="dn">quantité manquante</span>';
    const ex = have.get(r.s), how = r.how ? `reconnu par ${r.how === 'ISIN' ? 'le code ISIN' : r.how === 'code' ? 'le code' : r.how === 'nom' ? 'le nom' : 'la sauvegarde'}` : 'choisi';
    return `<span class="up">${how}</span>${r.guess ? ' <span class="am" title="Le fichier n’a pas d’en-tête « Quantité » : premier nombre de la ligne pris comme quantité">· quantité à vérifier</span>' : ''}${I.mode !== 'rempl' && ex ? ` <span class="dm">· en portefeuille : ${num(ex.q, ex.q % 1 ? 2 : 0)}</span>` : ''}`; };
  const nOk = ok().length;
  const body = I.msg && !I.rows.length ? `<div class="empty" style="text-align:left;white-space:normal">${I.msg}</div>` : `<div class="tw" style="max-height:62vh"><table class="t" id="imT"><thead><tr><th class="l">Prendre</th><th class="l">Titre · état · ligne lue</th><th>Quantité</th><th>Prix de revient unitaire</th></tr></thead><tbody>
    ${I.rows.map((r, i) => `<tr data-i="${i}"><td class="l"><input type="checkbox" data-k="on" ${r.on ? 'checked' : ''}></td><td class="l"><select class="ofld" data-k="s">${opts(r)}</select><div class="imst">${state(r)}</div><div class="dm imsrc">${esc(r.src)}</div></td>
      <td><input class="ofld" data-k="q" value="${r.q != null ? r.q : ''}" style="width:90px;text-align:right" inputmode="decimal"></td><td><input class="ofld" data-k="c" value="${r.c != null ? r.c : ''}" placeholder="facultatif" style="width:100px;text-align:right" inputmode="decimal"></td></tr>`).join('')}</tbody></table></div>`;
  m.innerHTML = pn(`Import · ${esc(I.name)}${I.rows.length ? ` · ${I.rows.length} ligne${I.rows.length > 1 ? 's' : ''} de position` : ''}${I.skipped ? ` · ${I.skipped} ligne${I.skipped > 1 ? 's' : ''} ignorée${I.skipped > 1 ? 's' : ''} (en-têtes, totaux, espèces)` : ''}`, 'PORTF', body,
    { np: true, tools: `<span class="tlab">Mode</span><button class="tb ${I.mode !== 'rempl' ? 'on' : ''}" data-mode="maj">Mettre à jour le portefeuille</button><button class="tb ${I.mode === 'rempl' ? 'on' : ''}" data-mode="rempl">Remplacer tout le portefeuille</button><span class="gsp"></span><button class="tb on" id="imOk">Valider l’import (${nOk} ligne${nOk > 1 ? 's' : ''})</button><button class="tb" id="imNo">Annuler</button>`,
      lect: `${I.bk ? `Sauvegarde du ${I.date ? fds(String(I.date).slice(0, 10)) : '—'}${I.base ? ', devise de référence ' + I.base : ''}. ` : ''}Contrôlez chaque ligne avant de valider : titre, quantité, prix de revient unitaire (facultatif, dans la devise du titre). « Mettre à jour » ajoute les nouveaux titres et remplace la quantité des titres déjà présents ; « Remplacer » efface d’abord les positions actuelles. Un titre présent sur plusieurs lignes est additionné. Le fichier a été lu dans ce navigateur : il n’est envoyé nulle part et n’est pas gardé ; rien n’est enregistré avant « Valider ».` });
  const row = el => I.rows[+el.closest('tr').dataset.i];
  m.querySelectorAll('#imT [data-k]').forEach(el => { el.onclick = e => e.stopPropagation(); el.onchange = () => { const r = row(el), k = el.dataset.k;
    if (k === 'on') r.on = el.checked; else if (k === 's') { r.s = el.value; r.how = ''; if (r.s && r.q > 0) r.on = true; } else { const v = impNum(el.value); r[k] = v != null && v > 0 ? v : null; if (k === 'q' && r.q > 0 && r.s) r.on = true; r.guess = false; }
    impScreen(m); }; });
  m.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => { I.mode = b.dataset.mode; impScreen(m); });
  $('imOk').onclick = apply; $('imNo').onclick = fin;
}
const PAGES_PORTF_BASE = PAGES.PORTF;
PAGES.PORTF = async (m, alive) => {
  if (ST.portImp) { $('ptabs').hidden = true; return impScreen(m); }
  await PAGES_PORTF_BASE(m, alive); if (!alive()) return;
  const P = portLoad();
  PG.acts = (PG.acts || []).concat([{ n: 94, l: 'Importer un relevé (Excel, CSV, PDF)', run: () => impPick('.csv,.txt,.tsv,.xlsx,.pdf,image/*,text/csv,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', impFile) },
    { n: 95, l: 'Sauvegarder le portefeuille (fichier)', run: () => impBackup(P) }, { n: 89, l: 'Restaurer une sauvegarde', run: () => impPick('.json,application/json', impRestore) }]);
  renderRbar();
  const b = $('ptXo'); if (b) b.onclick = () => impPasted($('ptX').value);
};
