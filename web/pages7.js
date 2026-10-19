/* ================= FQT — IMAP : carte de chaleur du marché (BRVM, Nasdaq-100, ETF) ================= */

/* Découpage « squarified » d'un rectangle : items [{v, ...}] -> [{x, y, w, h, ...}] */
function squarify(items, R) {
  const tot = items.reduce((a, b) => a + b.v, 0); if (!tot || R.w <= 0 || R.h <= 0) return [];
  const sc = R.w * R.h / tot, rows = items.map(i => ({ ...i, a: i.v * sc })).sort((a, b) => b.a - a.a), out = []; let rect = { ...R }, row = [];
  const worst = (r, side) => { const s = r.reduce((a, b) => a + b.a, 0); let mx = 0; for (const i of r) mx = Math.max(mx, side * side * i.a / (s * s), s * s / (side * side * i.a)); return mx; };
  const lay = r => { const s = r.reduce((a, b) => a + b.a, 0); if (rect.w >= rect.h) { const cw = s / rect.h; let y = rect.y; for (const i of r) { const ch = i.a / cw; out.push({ ...i, x: rect.x, y, w: cw, h: ch }); y += ch; } rect = { x: rect.x + cw, y: rect.y, w: rect.w - cw, h: rect.h }; }
    else { const ch = s / rect.w; let x0 = rect.x; for (const i of r) { const cw = i.a / ch; out.push({ ...i, x: x0, y: rect.y, w: cw, h: ch }); x0 += cw; } rect = { x: rect.x, y: rect.y + ch, w: rect.w, h: rect.h - ch }; } };
  for (const it of rows) { const side = Math.min(rect.w, rect.h); if (!row.length || worst(row.concat(it), side) <= worst(row, side)) row.push(it); else { lay(row); row = [it]; } }
  if (row.length) lay(row); return out;
}
const IMAP_C = [['pct', 'Jour', .03], ['r1w', '1 semaine', .06], ['r1m', '1 mois', .12], ['r3m', '3 mois', .2], ['ytd', 'Depuis janvier', .4], ['r1y', '1 an', .5], ['sma', 'Écart à la MM200', .25], ['dd', 'Écart au record', .4]];
/* Taille des cases (demande du 19/10/2026) : par défaut selon l'ampleur de la variation choisie en couleur (une case sans
   variation garde une petite taille fixe pour rester visible), ou égale (cases rangées de la plus forte hausse à la plus forte
   baisse), ou selon la capitalisation. Zoom et déplacement de la carte (glisser à la souris ou au doigt). */
const IMAP_SZ = [['var', 'Variation'], ['eq', 'Égale'], ['mcap', 'Capitalisation']];
const IMAP_Z = [[1, '1×'], [1.5, '1,5×'], [2, '2×'], [3, '3×']];
const imapSzLab = sz => ({ var: 'ampleur de la variation', eq: 'égale (rangées de la plus forte hausse à la plus forte baisse)', mcap: 'capitalisation boursière', float: 'capitalisation flottante (capitalisation × flottant)', liq: 'montant moyen échangé sur 3 mois' })[sz] || 'capitalisation boursière';
/* rectangles des cases : égale = grille rangée par valeur décroissante ; sinon découpage « squarified » */
function imapPlace(items, R, eq) {
  if (!eq) return squarify(items, R);
  const it = items.slice().sort((a, b) => (b.k == null ? -Infinity : b.k) - (a.k == null ? -Infinity : a.k)), n = it.length; if (!n || R.w <= 0 || R.h <= 0) return [];
  let cols = Math.max(1, Math.round(Math.sqrt(n * R.w / R.h))); const rows = Math.ceil(n / cols); cols = Math.ceil(n / rows);
  const cw = R.w / cols, ch = R.h / rows; return it.map((x, i) => ({ ...x, x: R.x + (i % cols) * cw, y: R.y + Math.floor(i / cols) * ch, w: cw, h: ch }));
}
/* carte agrandie : surface intérieure z fois plus grande, déplaçable en glissant (souris) ou au doigt (défilement natif) */
function imapSurface(host, z) {
  const r = host.getBoundingClientRect(), W = Math.floor(r.width * z), H = Math.floor(r.height * z);
  host.classList.toggle('imz', z > 1); host.innerHTML = `<div class="imi" style="width:${W}px;height:${H}px"></div>`;
  if (z > 1) { host.scrollLeft = (W - r.width) / 2; host.scrollTop = (H - r.height) / 2; }
  let d = null, moved = false;
  host.onpointerdown = e => { if (z <= 1 || e.pointerType !== 'mouse' || e.button) return; d = { x: e.clientX, y: e.clientY, l: host.scrollLeft, t: host.scrollTop, id: e.pointerId }; moved = false; };
  host.onpointermove = e => { if (!d) return; const dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (!moved && Math.abs(dx) + Math.abs(dy) > 5) { moved = true; host.classList.add('drag'); try { host.setPointerCapture(d.id); } catch (er) { } untip(); }
    if (moved) { host.scrollLeft = d.l - dx; host.scrollTop = d.t - dy; } };
  host.onpointerup = host.onpointercancel = () => { d = null; host.classList.remove('drag'); };
  host.addEventListener('click', e => { if (moved) { e.stopPropagation(); e.preventDefault(); moved = false; } }, true);
  return { inner: host.firstChild, W, H, dragging: () => !!(d && moved) };
}
/* barre commune : taille des cases, zoom, agrandir la fenêtre */
function imapTools(st, extra) {
  return `<span class="tlab">Taille</span>${IMAP_SZ.concat(extra || []).map(([k, l]) => `<button class="tb ${st.sz === k ? 'on' : ''}" data-s="${k}">${l}</button>`).join('')}
    <span class="tlab">Zoom</span>${IMAP_Z.map(([k, l]) => `<button class="tb ${(st.z || 1) === k ? 'on' : ''}" data-z="${k}">${l}</button>`).join('')}
    <button class="tb" data-mx="1" title="Agrandir la fenêtre (plein écran) ; Échap pour revenir">${document.body.classList.contains('maxi') ? 'Réduire' : 'Agrandir'}</button>`;
}
function imapBind(m, st) {
  m.querySelectorAll('[data-s]').forEach(b => b.onclick = () => { st.sz = b.dataset.s; render(); });
  m.querySelectorAll('[data-z]').forEach(b => b.onclick = () => { st.z = +b.dataset.z; render(); });
  m.querySelectorAll('[data-mx]').forEach(b => b.onclick = () => { toggleMaxi(); setTimeout(render, 120); });
}
const imapH = () => innerWidth < 700 ? '560px' : document.body.classList.contains('maxi') ? 'calc(100vh - 150px)' : 'max(480px, calc(100vh - 250px - var(--nwh, 90px)))';
PAGES.IMAP = async (m, alive) => {
  const st = ST.imap = ST.imap || { u: 'BRVM', c: 'pct', sz: 'var', z: 1 }; if (!st.gp) st.gp = 'none'; if (!st.z) st.z = 1;
  const U_ = { BRVM: ['BRVM · 48 actions', s => s.mkt === 'BRVM' && s.cls === 'Equity'], NDX: ['Nasdaq-100', s => s.ndx], ETF: ['ETF US', s => s.mkt === 'US' && s.typ === 'ETF'] };
  if (!U_[st.u]) st.u = 'BRVM'; const [title, flt] = U_[st.u];
  const szOk = IMAP_SZ.map(x => x[0]).concat(st.u === 'BRVM' ? ['float', 'liq'] : []); if (!szOk.includes(st.sz)) st.sz = 'var';
  const L = await (st.sz === 'liq' && st.u === 'BRVM' ? getJSON('liq.json').catch(() => null) : null); if (!alive()) return;
  const lq = L ? new Map(L.rows.map(r => [r.id, r.adv3])) : null;
  const val = s => st.c === 'sma' ? (s.sma200 ? s.last / s.sma200 - 1 : null) : s[st.c];
  const scale = (IMAP_C.find(c => c[0] === st.c) || IMAP_C[0])[2];
  /* poids des moyennes et du tableau des secteurs : capitalisation (ou mesure choisie), jamais la taille « variation » ou « égale » */
  const capw = s => st.sz === 'float' && s.float ? (s.mcap || 0) * s.float / 100 : st.sz === 'liq' ? (lq ? lq.get(s.id) : s.liq) || 0 : st.u === 'ETF' ? (s.liq || 1) : (s.mcap || 0);
  const size = s => { if (st.sz === 'eq') return 1; if (st.sz === 'var') { const v = val(s); return (v == null || !isFinite(v) ? 0 : Math.abs(v)) + scale * .12; } return capw(s); };
  const secs_ = secsWhere(flt).filter(s => size(s) > 0); const grpOf = s => st.u === 'BRVM' ? s.grp : st.u === 'NDX' ? (s.sector || s.grp || 'Autres') : s.grp;
  const eq = st.sz === 'eq';
  /* regroupement par secteur, ou aucun : chaque société directement */
  const G = {}; for (const s of secs_) { const g = st.gp === 'none' ? '' : grpOf(s); (G[g] = G[g] || []).push(s); }
  const col = v => v == null || !isFinite(v) ? '#262626' : v === 0 ? '#3a3a3a' : (() => { const a = Math.min(1, Math.abs(v) / scale); return v > 0 ? `rgb(${Math.round(30 - 10 * a)},${Math.round(70 + 120 * a)},${Math.round(45 + 30 * a)})` : `rgb(${Math.round(90 + 140 * a)},${Math.round(40 - 10 * a)},${Math.round(38 - 8 * a)})`; })();
  const wavg = a => { let s = 0, w = 0; for (const x of a) { const v = val(x); if (v == null || !isFinite(v)) continue; s += v * capw(x); w += capw(x); } return w ? s / w : null; };
  const sect = Object.entries(G).map(([g, a]) => ({ g, list: a, v: eq ? a.length : a.reduce((t, s) => t + size(s), 0), p: wavg(a), n: a.length })).sort((a, b) => b.v - a.v);
  /* tableau des secteurs : toujours par secteur, même quand la carte n'est pas regroupée */
  const GS = {}; for (const s of secs_) (GS[grpOf(s)] = GS[grpOf(s)] || []).push(s);
  const sectT = Object.entries(GS).map(([g, a]) => ({ g, list: a, v: a.reduce((t, s) => t + capw(s), 0), p: wavg(a), n: a.length })).sort((a, b) => b.v - a.v);
  const movers = secs_.filter(s => val(s) != null).sort((a, b) => val(b) - val(a));
  const cl = (IMAP_C.find(c => c[0] === st.c) || [])[1];
  const totT = sectT.reduce((t, y) => t + y.v, 0) || 1;
  m.innerHTML = `<div class="tools" style="border:1px solid var(--line2)"><span class="tlab">Marché</span>${Object.entries(U_).map(([k, [l]]) => `<button class="tb ${st.u === k ? 'on' : ''}" data-u="${k}">${l}</button>`).join('')}
    <span class="tlab">Couleur</span>${IMAP_C.map(([k, l]) => `<button class="tb ${st.c === k ? 'on' : ''}" data-c="${k}">${l}</button>`).join('')}
    ${imapTools(st, st.u === 'BRVM' ? [['float', 'Capitalisation flottante'], ['liq', 'Montant échangé 3 mois']] : [])}
    <span class="tlab">Regroupement</span>${[['none', 'Aucun'], ['sec', 'Par secteur']].map(([k, l]) => `<button class="tb ${st.gp === k ? 'on' : ''}" data-gp="${k}">${l}</button>`).join('')}</div>
    <div class="grid">${pn(`Carte de chaleur · ${title} · ${cl}`, 'MAP', `<div id="imM" class="imap" style="height:${imapH()}"></div><div class="imleg">${[-1, -.66, -.33, 0, .33, .66, 1].map(t => `<span style="background:${col(t * scale)}">${t > 0 ? '+' : ''}${num(t * scale * 100, 0)} %</span>`).join('')}</div>`,
      { lect: `${st.gp === 'none' ? 'Une case par société' : 'Rectangles regroupés par secteur'} ; taille des cases = ${imapSzLab(st.u === 'ETF' && st.sz === 'mcap' ? 'liq' : st.sz)}${st.sz === 'var' ? ` (${cl.toLowerCase()} ; une case sans variation garde une petite taille fixe)` : ''} ; couleur = ${cl.toLowerCase()} (échelle ±${num(scale * 100, 0)} %). ${(st.z || 1) > 1 ? 'Carte agrandie : faites-la glisser pour la déplacer. ' : ''}Clic = menu du titre. ${st.u === 'BRVM' ? 'Séance du jour, relevée toutes les 15 min en séance.' : 'Cours Nasdaq différés.'}` })}
    <div class="grid imap2">${pn('Secteurs (pondérés par la capitalisation)', 'MAP', (() => { const mxp = Math.max(1e-6, ...sectT.map(x => Math.abs(x.p || 0))); return `<table class="t wcr"><thead><tr><th class="l">Secteur</th><th>Titres</th><th>Poids</th><th>${cl}</th><th class="c"></th></tr></thead><tbody>${sectT.map(x => `<tr><td class="l am">${esc(x.g)}</td><td>${x.n}</td><td>${num(x.v / totT * 100, 1)} %</td><td style="background:${col(x.p)}">${pc(x.p, 1)}</td><td class="wcb" style="min-width:90px;width:26%"><span class="z"></span>${x.p == null ? '' : `<i class="${x.p >= 0 ? 'p' : 'n'}" style="width:${(Math.abs(x.p) / mxp * 50).toFixed(1)}%"></i>`}</td></tr>`).join('')}</tbody></table>`; })(), { np: true })}
      ${pn('Plus fortes hausses et baisses', 'MAP', `<table class="t"><tbody>${movers.slice(0, 6).concat(movers.slice(-6)).map((s, i) => `<tr data-sec="${s.id}" data-to="MENU" class="${i === 6 ? 'sep2' : ''}"><td class="l tk">${s.id}</td><td class="l nm">${esc(s.short || s.n)}</td><td class="wh">${px(s, s.last)}</td><td>${pc(val(s), 1)}</td></tr>`).join('')}</tbody></table>`, { np: true })}</div></div>`;
  m.querySelectorAll('[data-u]').forEach(b => b.onclick = () => { st.u = b.dataset.u; if (st.u !== 'BRVM' && !IMAP_SZ.some(x => x[0] === st.sz)) st.sz = 'var'; render(); }); m.querySelectorAll('[data-c]').forEach(b => b.onclick = () => { st.c = b.dataset.c; render(); }); m.querySelectorAll('[data-gp]').forEach(b => b.onclick = () => { st.gp = b.dataset.gp; render(); });
  imapBind(m, st);
  const host = $('imM'), sf = imapSurface(host, st.z || 1), W = sf.W, H = sf.H; const boxes = squarify(sect.map(x => ({ ...x })), { x: 0, y: 0, w: W, h: H }); let html = '';
  for (const b of boxes) { const head = b.g && b.h > 40 && b.w > 60 ? 15 : 0; html += `<div class="ims" style="left:${b.x}px;top:${b.y}px;width:${b.w}px;height:${b.h}px">${head ? `<div class="imh">${esc(b.g)} <span>${b.p != null ? (b.p > 0 ? '+' : '') + num(b.p * 100, 1) + ' %' : ''}</span></div>` : ''}</div>`;
    for (const t of imapPlace(b.list.map(s => ({ s, v: size(s), k: val(s) })), { x: b.x + 1, y: b.y + head + 1, w: b.w - 2, h: b.h - head - 2 }, eq)) { const s = t.s, v = val(s);
      html += `<div class="imt" data-sec="${s.id}" data-to="MENU" data-tt="${esc(s.id)}" style="left:${t.x}px;top:${t.y}px;width:${Math.max(0, t.w - 1)}px;height:${Math.max(0, t.h - 1)}px;background:${col(v)}">${t.w > 36 && t.h > 20 ? `${t.w > 74 && t.h > 58 ? `<i style="font-size:${U.clamp(Math.min(t.w / 13, t.h / 7), 8, 12)}px">${esc(s.short || s.n)}</i>` : ''}<b style="font-size:${U.clamp(Math.min(t.w / 5, t.h / 2.6), 10, 22)}px">${s.id}</b>${t.h > 38 ? `<span>${v != null ? (v > 0 ? '+' : '') + num(v * 100, 1) + ' %' : '—'}</span>` : ''}` : ''}</div>`; } }
  sf.inner.innerHTML = html;
  host.onmousemove = e => { if (sf.dragging()) return; const d = e.target.closest('.imt'); if (!d) { untip(); return; } const s = Q.by[d.dataset.sec]; tip(e, `<b>${s.id}</b> ${esc(s.short || s.n)}<br>${cl} : <b>${pc(val(s), 2)}</b> · cours ${px(s, s.last)}<br>capitalisation ${big(s.mcap)}${s.per ? ' · PER ' + num(s.per, 1) : ''}${s.yld ? ' · rdt ' + num(s.yld * 100, 1) + ' %' : ''}`); };
  host.onmouseleave = untip;
};
