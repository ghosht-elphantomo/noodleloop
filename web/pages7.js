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
PAGES.IMAP = async (m, alive) => {
  const st = ST.imap = ST.imap || { u: 'BRVM', c: 'pct', sz: 'mcap' }; if (!st.gp) st.gp = 'none';
  const U_ = { BRVM: ['BRVM · 48 actions', s => s.mkt === 'BRVM' && s.cls === 'Equity'], NDX: ['Nasdaq-100', s => s.ndx], ETF: ['ETF US', s => s.mkt === 'US' && s.typ === 'ETF'] };
  if (!U_[st.u]) st.u = 'BRVM'; const [title, flt] = U_[st.u]; const L = await (st.sz === 'liq' && st.u === 'BRVM' ? getJSON('liq.json').catch(() => null) : null); if (!alive()) return;
  const lq = L ? new Map(L.rows.map(r => [r.id, r.adv3])) : null;
  const val = s => st.c === 'sma' ? (s.sma200 ? s.last / s.sma200 - 1 : null) : s[st.c];
  const size = s => st.sz === 'float' && s.float ? (s.mcap || 0) * s.float / 100 : st.sz === 'liq' ? (lq ? lq.get(s.id) : s.liq) || 0 : st.u === 'ETF' ? (s.liq || 1) : (s.mcap || 0);
  const secs_ = secsWhere(flt).filter(s => size(s) > 0); const grpOf = s => st.u === 'BRVM' ? s.grp : st.u === 'NDX' ? (s.sector || s.grp || 'Autres') : s.grp;
  /* regroupement par secteur, ou aucun : chaque société directement à la taille de sa capitalisation */
  const G = {}; for (const s of secs_) { const g = st.gp === 'none' ? '' : grpOf(s); (G[g] = G[g] || []).push(s); }
  const scale = (IMAP_C.find(c => c[0] === st.c) || IMAP_C[0])[2];
  const col = v => v == null || !isFinite(v) ? '#262626' : v === 0 ? '#3a3a3a' : (() => { const a = Math.min(1, Math.abs(v) / scale); return v > 0 ? `rgb(${Math.round(30 - 10 * a)},${Math.round(70 + 120 * a)},${Math.round(45 + 30 * a)})` : `rgb(${Math.round(90 + 140 * a)},${Math.round(40 - 10 * a)},${Math.round(38 - 8 * a)})`; })();
  const wavg = a => { let s = 0, w = 0; for (const x of a) { const v = val(x); if (v == null || !isFinite(v)) continue; s += v * size(x); w += size(x); } return w ? s / w : null; };
  const sect = Object.entries(G).map(([g, a]) => ({ g, list: a, v: a.reduce((t, s) => t + size(s), 0), p: wavg(a), n: a.length })).sort((a, b) => b.v - a.v);
  /* tableau des secteurs : toujours par secteur, même quand la carte n'est pas regroupée */
  const GS = {}; for (const s of secs_) (GS[grpOf(s)] = GS[grpOf(s)] || []).push(s);
  const sectT = Object.entries(GS).map(([g, a]) => ({ g, list: a, v: a.reduce((t, s) => t + size(s), 0), p: wavg(a), n: a.length })).sort((a, b) => b.v - a.v);
  const movers = secs_.filter(s => val(s) != null).sort((a, b) => val(b) - val(a));
  const cl = (IMAP_C.find(c => c[0] === st.c) || [])[1];
  m.innerHTML = `<div class="tools" style="border:1px solid var(--line2)"><span class="tlab">Marché</span>${Object.entries(U_).map(([k, [l]]) => `<button class="tb ${st.u === k ? 'on' : ''}" data-u="${k}">${l}</button>`).join('')}
    <span class="tlab">Couleur</span>${IMAP_C.map(([k, l]) => `<button class="tb ${st.c === k ? 'on' : ''}" data-c="${k}">${l}</button>`).join('')}
    <span class="tlab">Taille</span>${[['mcap', 'Capitalisation'], ...(st.u === 'BRVM' ? [['float', 'Capitalisation flottante'], ['liq', 'Montant échangé 3 mois']] : [])].map(([k, l]) => `<button class="tb ${st.sz === k ? 'on' : ''}" data-s="${k}">${l}</button>`).join('')}
    <span class="tlab">Regroupement</span>${[['none', 'Aucun'], ['sec', 'Par secteur']].map(([k, l]) => `<button class="tb ${st.gp === k ? 'on' : ''}" data-gp="${k}">${l}</button>`).join('')}</div>
    <div class="grid side">${pn(`Carte de chaleur · ${title} · ${cl}`, 'MAP', `<div id="imM" class="imap" style="height:${innerWidth < 700 ? '520px' : 'max(420px, calc(100vh - 300px - var(--nwh, 90px)))'}"></div><div class="imleg">${[-1, -.66, -.33, 0, .33, .66, 1].map(t => `<span style="background:${col(t * scale)}">${t > 0 ? '+' : ''}${num(t * scale * 100, 0)} %</span>`).join('')}</div>`,
      { lect: `${st.gp === 'none' ? 'Une case par société' : 'Rectangles regroupés par secteur'} ; surface = ${st.sz === 'float' ? 'capitalisation flottante (capitalisation × flottant)' : st.sz === 'liq' ? 'montant moyen échangé sur 3 mois' : st.u === 'ETF' ? 'montant moyen échangé' : 'capitalisation boursière'} ; couleur = ${cl.toLowerCase()} (échelle ±${num(scale * 100, 0)} %). Clic = menu du titre. ${st.u === 'BRVM' ? 'Séance du jour, relevée toutes les 15 min en séance.' : 'Cours Nasdaq différés.'}` })}
    <div class="grid" style="align-content:start">${pn('Secteurs (pondérés)', 'MAP', (() => { const mxp = Math.max(1e-6, ...sectT.map(x => Math.abs(x.p || 0))); return `<table class="t wcr"><thead><tr><th class="l">Secteur</th><th>Titres</th><th>Poids</th><th>${cl}</th><th class="c"></th></tr></thead><tbody>${sectT.map(x => `<tr><td class="l am">${esc(x.g)}</td><td>${x.n}</td><td>${num(x.v / sectT.reduce((t, y) => t + y.v, 0) * 100, 1)} %</td><td style="background:${col(x.p)}">${pc(x.p, 1)}</td><td class="wcb" style="min-width:90px;width:26%"><span class="z"></span>${x.p == null ? '' : `<i class="${x.p >= 0 ? 'p' : 'n'}" style="width:${(Math.abs(x.p) / mxp * 50).toFixed(1)}%"></i>`}</td></tr>`).join('')}</tbody></table>`; })(), { np: true })}
      ${pn('Plus fortes hausses et baisses', 'MAP', `<table class="t"><tbody>${movers.slice(0, 6).concat(movers.slice(-6)).map((s, i) => `<tr data-sec="${s.id}" data-to="MENU" class="${i === 6 ? 'sep2' : ''}"><td class="l tk">${s.id}</td><td class="l nm">${esc(s.short || s.n)}</td><td class="wh">${px(s, s.last)}</td><td>${pc(val(s), 1)}</td></tr>`).join('')}</tbody></table>`, { np: true })}</div></div>`;
  m.querySelectorAll('[data-u]').forEach(b => b.onclick = () => { st.u = b.dataset.u; if (st.u !== 'BRVM') st.sz = 'mcap'; render(); }); m.querySelectorAll('[data-c]').forEach(b => b.onclick = () => { st.c = b.dataset.c; render(); }); m.querySelectorAll('[data-s]').forEach(b => b.onclick = () => { st.sz = b.dataset.s; render(); }); m.querySelectorAll('[data-gp]').forEach(b => b.onclick = () => { st.gp = b.dataset.gp; render(); });
  const host = $('imM'), W = host.getBoundingClientRect().width, H = host.getBoundingClientRect().height; const boxes = squarify(sect.map(x => ({ ...x })), { x: 0, y: 0, w: W, h: H }); let html = '';
  for (const b of boxes) { const head = b.g && b.h > 40 && b.w > 60 ? 15 : 0; html += `<div class="ims" style="left:${b.x}px;top:${b.y}px;width:${b.w}px;height:${b.h}px">${head ? `<div class="imh">${esc(b.g)} <span>${b.p != null ? (b.p > 0 ? '+' : '') + num(b.p * 100, 1) + ' %' : ''}</span></div>` : ''}</div>`;
    for (const t of squarify(b.list.map(s => ({ s, v: size(s) })), { x: b.x + 1, y: b.y + head + 1, w: b.w - 2, h: b.h - head - 2 })) { const s = t.s, v = val(s);
      html += `<div class="imt" data-sec="${s.id}" data-to="MENU" data-tt="${esc(s.id)}" style="left:${t.x}px;top:${t.y}px;width:${Math.max(0, t.w - 1)}px;height:${Math.max(0, t.h - 1)}px;background:${col(v)}">${t.w > 36 && t.h > 20 ? `${t.w > 74 && t.h > 58 ? `<i style="font-size:${U.clamp(Math.min(t.w / 13, t.h / 7), 8, 12)}px">${esc(s.short || s.n)}</i>` : ''}<b style="font-size:${U.clamp(Math.min(t.w / 5, t.h / 2.6), 10, 22)}px">${s.id}</b>${t.h > 38 ? `<span>${v != null ? (v > 0 ? '+' : '') + num(v * 100, 1) + ' %' : '—'}</span>` : ''}` : ''}</div>`; } }
  host.innerHTML = html;
  host.onmousemove = e => { const d = e.target.closest('.imt'); if (!d) { untip(); return; } const s = Q.by[d.dataset.sec]; tip(e, `<b>${s.id}</b> ${esc(s.short || s.n)}<br>${cl} : <b>${pc(val(s), 2)}</b> · cours ${px(s, s.last)}<br>capitalisation ${big(s.mcap)}${s.per ? ' · PER ' + num(s.per, 1) : ''}${s.yld ? ' · rdt ' + num(s.yld * 100, 1) + ' %' : ''}`); };
  host.onmouseleave = untip;
};
