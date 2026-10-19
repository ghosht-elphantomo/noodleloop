/* ================= FQT — pages: MONITOR, BRVM, GP, DES, HELP ================= */
'use strict';
const codeAttr = code => { const c0 = String(code || '').trim(); if (FN[c0]) return c0 === ST.fn ? '' : ` data-fn="${c0}"`; const w = c0.split(/\s+/); const f = w[w.length - 1]; if (!FN[f] || f === ST.fn && (w.length < 2 || w[0] === ST.sec)) return ''; return ` data-fn="${f}"${w.length > 1 && Q.by[w[0]] ? ` data-s="${w[0]}"` : ''}`; };
/* dividende par action : marqué « a » quand il a été ajusté d'un fractionnement ou d'actions gratuites (montant publié en infobulle),
   « $ » quand il a été publié en cents de dollar (montant officiel en FCFA, sinon converti au cours du jour de publication) */
const adjMark = x => (x && x.adj ? `<i class="qd" title="montant publié : ${num(x.dps0, x.dps0 < 10 ? 4 : 2)} par action ancienne ; ajusté des opérations sur le capital (1 action ancienne = ${num(x.adj, Number.isInteger(+x.adj) ? 0 : 2)} actions actuelles)">a</i>` : '')
  + (x && x.usd ? `<i class="qd" title="publié en dollars : ${num(x.usd, 2)} cent de dollar par action ; ${x.fx ? `converti au cours du jour de sa publication (${num(x.fx, 2)} FCFA pour 1 dollar)` : 'montant officiel en FCFA'}">$</i>` : '')
  + (x && x.cal ? '<i class="qd" title="montant du calendrier officiel des dividendes (net ou brut selon la société) : l’avis officiel détaille le net">c</i>' : '');
const pn = (title, code, body, o = {}) => `<div class="pn" ${o.id ? `id="${o.id}"` : ''} ${o.style ? `style="${o.style}"` : ''}><div class="pt">${title}${o.sel ? `<span class="sel">${o.sel}</span>` : ''}<span class="code"${codeAttr(code)}>${code || ''}</span></div>${o.tools ? `<div class="tools">${o.tools}</div>` : ''}<div class="pb ${o.np ? 'np' : ''}">${body}</div>${o.lect ? `<div class="lect">${o.lect}</div>` : ''}</div>`;
const cvb = (id, h) => `<div class="cv" id="${id}" style="height:${h}px"></div>`;
const rangeBar = s => { if (!(s.hi52 > s.lo52)) return ''; const f = U.clamp((s.last - s.lo52) / (s.hi52 - s.lo52), 0, 1); return `<span class="rng" title="${px(s, s.lo52)} – ${px(s, s.hi52)}"><i style="left:${(f * 68).toFixed(0)}px"></i></span>`; };
const freqLab = s => s.f === 'M' ? 'mens.' : '';
const legacy = s => /ancien/i.test(s.n);
function sortRows(rows, sort) { const { k, dir } = sort; return rows.slice().sort((a, b) => { const A = a[k], B = b[k]; if (A == null && B == null) return 0; if (A == null) return 1; if (B == null) return -1; return (typeof A === 'string' ? A.localeCompare(B) : A - B) * dir; }); }
function thSort(cols, sort) { return cols.map(([k, l, left]) => `<th data-k="${k}" class="${left ? 'l' : ''} ${sort.k === k ? 'on' : ''}">${l}${sort.k === k ? (sort.dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join(''); }
function lastCross(c, s) { const n = c.length; const above = c[n - 1] > s[n - 1]; let k = n - 1; while (k > 0 && isFinite(s[k - 1]) && (c[k - 1] > s[k - 1]) === above) k--; return { above, k }; }

/* ------------------------------------------------------------------ MONITOR (ex-MON) */
PAGES.MONITOR = async (m, alive) => {
  const G = [['Indices & ETF · États-Unis', s => s.mkt === 'US' && s.typ === 'ETF'], ['Actions · États-Unis', s => s.mkt === 'US' && s.typ !== 'ETF'], ['Taïwan', s => s.mkt === 'TW'],
    ['Indices BRVM', s => s.mkt === 'BRVM' && s.cls === 'Index' && !legacy(s)], ['Matières premières', s => s.cls === 'Comdty'], ['Taux · volatilité · macro', s => s.mkt === 'MACRO' && (s.cls === 'Index' || s.cls === 'Rate')], ['Change', s => s.cls === 'Curncy']];
  const row = s => `<tr data-sec="${s.id}"><td class="l tk">${s.tk}</td><td class="l nm ns" title="${esc(s.n)}">${esc(s.short || s.n)}</td><td class="wh">${px(s, s.last)}</td><td>${sgn(s.last - s.prev, pxd(s), '', 1)}</td><td>${pc(s.pct)}</td>
    <td>${s.f === 'D' ? pc(s.r1w, 1) : '<span class="fl">—</span>'}</td><td>${pc(s.r1m, 1)}</td><td>${pc(s.ytd, 1)}</td><td>${pc(s.r1y, 1)}</td><td class="w16">${num(s.vol * 100, 1)}</td><td class="w14">${rangeBar(s)}</td><td class="w16">${sparkSVG(s.spark)}</td><td class="dm">${s.f === 'M' ? fd(s.dt).slice(3) : fd(s.dt).slice(0, 5)}</td></tr>`;
  const body = G.map(([t, f]) => { const ss = secsWhere(f); return ss.length ? `<tr class="sec"><td class="l" colspan="13">${t} · ${ss.length}</td></tr>` + ss.map(row).join('') : ''; }).join('');
  const br = secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity');
  const up = br.slice().sort((a, b) => b.pct - a.pct).slice(0, 7), dn = br.slice().sort((a, b) => a.pct - b.pct).slice(0, 7), vo = br.slice().sort((a, b) => (b.vday || 0) - (a.vday || 0)).slice(0, 7);
  const mini = (rs, v) => `<table class="t"><tbody>${rs.map(s => `<tr data-sec="${s.id}"><td class="l tk">${s.id}</td><td class="wh">${px(s, s.last)}</td><td>${v(s)}</td></tr>`).join('')}</tbody></table>`;
  const nUp = br.filter(s => s.pct > 0).length, nDn = br.filter(s => s.pct < 0).length;
  m.innerHTML = `<div class="grid c2">
    ${pn('Marchés · vue d’ensemble', 'MONITOR', `<div class="tw" style="max-height:calc(100vh - 128px)"><table class="t mon"><thead><tr><th class="l">Titre</th><th class="l ns">Nom</th><th>Dernier</th><th>Var.</th><th>Var.%</th><th>1 sem.</th><th>1 mois</th><th>YTD</th><th>1 an</th><th class="w16">Vol. 1A %</th><th class="w14">Plage 52 sem.</th><th class="w16">60 dernières</th><th>Date</th></tr></thead><tbody>${body}</tbody></table></div>`, { np: true, sel: `${Q.sum.secs.filter(s => !legacy(s)).length} titres · cliquer une ligne pour ouvrir le graphique` })}
    <div class="grid" style="align-content:start">
      ${pn('QQQ · règle SMA 200 → TQQQ', 'QQQ GP', `<div class="grid c2b" style="gap:8px"><div class="kv2" id="sigKv"></div>${cvb('sigCv', 150)}</div>`, { lect: '<span id="sigLect">…</span>' })}
      ${pn('BRVM · séance', 'BRVM', `<div class="grid c3" style="gap:6px"><div><div class="am" style="font-size:11px;margin-bottom:2px">Plus fortes hausses</div>${mini(up, s => pc(s.pct))}</div><div><div class="am" style="font-size:11px;margin-bottom:2px">Plus fortes baisses</div>${mini(dn, s => pc(s.pct))}</div><div><div class="am" style="font-size:11px;margin-bottom:2px">Plus gros échanges</div>${mini(vo, s => valTxt(s, s.vday))}</div></div>`,
        { sel: Q.sum.session ? Q.sum.session.label : fd(Q.sum.asof), lect: `<b>Largeur</b> : <strong>${nUp}</strong> hausses, <strong>${nDn}</strong> baisses, ${br.length - nUp - nDn} stables sur ${br.length} titres. Montants échangés en XOF.` })}
      ${pn('Avis officiels · derniers publiés', 'EVTS', '<div id="monEv" style="max-height:260px;overflow:auto">…</div>')}
    </div></div>
    ${pn('BRVM · carte des capitalisations', 'BRVM', '<div class="tmap" id="tmap"></div>', { sel: 'taille = capitalisation boursière · couleur = variation du jour', lect: 'Chaque rectangle est une société cotée, proportionnel à sa capitalisation (cours × nombre de titres). <b>Vert</b> = hausse du jour, <b>rouge</b> = baisse ; l’intensité suit l’ampleur (saturée à ±4 %). Cliquer ouvre le graphique.' })}`;
  const tm = br.filter(s => s.mcap).map(s => ({ id: s.id, v: s.mcap, label: s.id, sub: (s.pct > 0 ? '+' : '') + num(s.pct * 100, 2) + '%', color: s.pct === 0 || !isFinite(s.pct) ? '#1f1f1f' : heatBg(s.pct, .04).replace(/,(0\.\d+|0)\)$/, (m0, a) => ',' + Math.max(.22, +a).toFixed(2) + ')'), title: `${s.n} · capi ${big(s.mcap)} XOF` }));
  treemap($('tmap'), tm, 250);
  getJSON('events_recent.json').then(ev => { if (!alive()) return; $('monEv').innerHTML = evMerge(ev).slice(0, 40).map(e => `<div class="ev"><span class="d">${fds(e.d)}</span><span class="tk" data-sec="${e.t}" data-to="DES">${e.t || ''}</span><span><span class="c">${esc(e.c || '')}</span><a href="${esc(e.u)}" target="_blank" rel="noopener">${esc(e.ti || '')}</a></span></div>`).join(''); }).catch(() => { $('monEv').textContent = 'Avis indisponibles.'; });
  const M = await market('QQQ'); if (!alive()) return; const S = await series('QQQ');
  const n = M.n, last = M.c[n - 1], s200 = M.sma200[n - 1], { above, k } = lastCross(M.c, M.sma200), L = Q.live && Q.live.qqq;
  const lp = L && L.price ? L.price : last;
  $('sigKv').innerHTML = `<span>Clôture ${fds(M.d[n - 1])}</span><b>${num(last, 2)}</b><span>SMA 200</span><b>${num(s200, 2)}</b><span>Écart</span><b>${pc(last / s200 - 1)}</b>
    <span>Régime</span><b class="${above ? 'up' : 'dn'}">${above ? 'LONG TQQQ' : 'CASH'}</b><span>Depuis</span><b>${fds(M.d[k])} · ${n - 1 - k} s.</b><span>Vol. 20 j</span><b>${num(M.vol20[n - 1] * 100, 1)}%</b><span>RSI 14</span><b>${num(M.rsi14[n - 1], 1)}</b>
    ${L ? `<span>Dernier (flux)</span><b>${num(L.price, 2)} ${pc(L.chg)}</b>` : ''}`;
  $('sigLect').innerHTML = above ? `QQQ clôture <strong>${num((last / s200 - 1) * 100, 1)} %</strong> au-dessus de sa moyenne 200 jours depuis le ${fds(M.d[k])} : la règle reste investie. Il faudrait une baisse de <strong>${num((1 - s200 / lp) * 100, 1)} %</strong> pour passer sous la SMA 200 (signal de sortie à la clôture).`
    : `QQQ est <strong>${num((1 - last / s200) * 100, 1)} %</strong> sous sa SMA 200 depuis le ${fds(M.d[k])} : la règle est en cash. Retour au-dessus à partir de <strong>${num(s200, 2)}</strong>.`;
  const ch = new TSChart($('sigCv'), { panes: [{ h: 1 }], padR: 46 });
  ch.set({ x: S.x, series: [{ y: M.c, color: CL.white, label: 'QQQ' }, { y: Array.from(M.sma200), color: CL.amber, label: 'SMA200' }] }, [n - 252, n - 1]);
};

/* ------------------------------------------------------------------ BRVM */
/* taux de distribution : dividende ÷ BNPA du même exercice (champ pay calculé à la construction) ; à défaut (titres hors BRVM) dividende ÷ BNPA */
const payR = s => s.pay !== undefined ? s.pay : (s.dps && s.bnpa > 0 ? s.dps / s.bnpa : null);
PAGES.BRVM = async (m, alive) => {
  const tab = tabState('BRVM', 'm'); setTabs(FN_TABS.BRVM, tab, k => { ST.tab.BRVM = k; render(); });
  if (tab === 'f') return brvmFloat(m, alive);
  if (tab === 'p') { setTitle('BRVM Market Valuation'); return PAGES.PER(m, alive); }
  const all = secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity'), sectors = [...new Set(all.map(s => s.grp))].sort();
  const idx = secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Index').sort((a, b) => legacy(a) - legacy(b));
  const st = ST.brvm, rows0 = st.sector === 'ALL' ? all : all.filter(s => s.grp === st.sector);
  const rows = sortRows(rows0.map(s => ({ ...s, d200: s.sma200 ? s.last / s.sma200 - 1 : null, payout: payR(s) })), st.sort);
  const cols = [['id', 'Titre', 1], ['short', 'Société', 1], ['grp', 'Secteur', 1], ['cty', 'Pays', 1], ['last', 'Cours'], ['pct', 'Var.%'], ['r1w', '1 sem.'], ['r1m', '1 mois'], ['ytd', 'YTD'], ['r1y', '1 an'], ['r3y', '3 ans'],
    ['vol', 'Vol. 1A'], ['beta', 'Bêta'], ['mcap', 'Capi (Md)'], ['per', 'PER'], ['yld', 'Rdt %'], ['payout', 'Payout'], ['rsi', 'RSI'], ['d200', '/SMA200'], ['liq', 'Échanges 3M/j'], ['dd', 'Depuis + haut']];
  const tr = s => `<tr data-sec="${s.id}"><td class="l tk">${s.id}</td><td class="l nm">${esc(s.short || s.n)}${s.susp ? ' <span class="dn">SUSP.</span>' : ''}</td><td class="l dm">${esc(s.grp || '')}</td><td class="l dm">${s.cty || ''}</td>
    <td class="wh">${px(s, s.last)}</td><td>${pc(s.pct)}</td><td>${pc(s.r1w, 1)}</td><td>${pc(s.r1m, 1)}</td><td>${pc(s.ytd, 1)}</td><td>${pc(s.r1y, 1)}</td><td>${pc(s.r3y, 0)}</td><td>${num(s.vol * 100, 1)}</td><td>${num(s.beta, 2)}</td>
    <td>${s.mcap ? num(s.mcap / 1e9, 0) : '—'}</td><td>${s.per ? num(s.per, 1) : '—'}</td><td>${s.yld ? num(s.yld * 100, 2) : '—'}</td><td>${s.payout ? num(s.payout * 100, 0) + '%' : '—'}</td><td>${num(s.rsi, 0)}</td><td>${pc(s.d200, 1)}</td><td>${big(s.liq)}</td><td>${pc(s.dd, 0)}</td></tr>`;
  const secAgg = sectors.map(g => { const ss = all.filter(s => s.grp === g), cap = ss.reduce((a, s) => a + (s.mcap || 0), 0), w = s => (s.mcap || 0) / (cap || 1);
    const med = a => { const v = a.filter(x => x != null && isFinite(x)).sort((x, y) => x - y); return v.length ? v[Math.floor(v.length / 2)] : null; };
    return { g, n: ss.length, cap, pct: ss.reduce((a, s) => a + w(s) * s.pct, 0), ytd: ss.reduce((a, s) => a + w(s) * (s.ytd || 0), 0), r1y: ss.reduce((a, s) => a + w(s) * (s.r1y || 0), 0), per: med(ss.map(s => s.per)), yld: med(ss.map(s => s.yld)) }; }).sort((a, b) => b.cap - a.cap);
  const capTot = all.reduce((a, s) => a + (s.mcap || 0), 0);
  m.innerHTML = `
    ${pn('BRVM · indices', 'BRVM', `<div class="tw"><table class="t"><thead><tr><th class="l">Indice</th><th class="l">Nom</th><th>Niveau</th><th>Var.%</th><th>1 mois</th><th>YTD</th><th>1 an</th><th>3 ans</th><th>Vol. 1A</th><th>Depuis</th><th>60 séances</th></tr></thead><tbody>
      ${idx.map(s => `<tr data-sec="${s.id}"><td class="l tk">${s.id}</td><td class="l nm">${esc(s.n)}</td><td class="wh">${num(s.last, 2)}</td><td>${pc(s.pct)}</td><td>${pc(s.r1m, 1)}</td><td>${pc(s.ytd, 1)}</td><td>${pc(s.r1y, 1)}</td><td>${pc(s.r3y, 0)}</td><td>${num(s.vol * 100, 1)}</td><td class="dm">${fd(s.first)}</td><td>${sparkSVG(s.spark)}</td></tr>`).join('')}</tbody></table></div>`, { np: true, sel: 'indices sectoriels « ancien » arrêtés fin 2025' })}
    ${pn('BRVM · 48 actions', 'BRVM', `<div class="tw" style="max-height:62vh"><table class="t" id="brT"><thead><tr>${thSort(cols, st.sort)}</tr></thead><tbody>${rows.map(tr).join('')}</tbody></table></div>`,
      { np: true, sel: `capitalisation totale ${big(capTot)} XOF · tri : cliquer un en-tête`, tools: `<span class="tlab">Secteur</span>${['ALL', ...sectors].map(g => `<button class="tb alt ${st.sector === g ? 'on' : ''}" data-sector="${esc(g)}">${g === 'ALL' ? 'Tous' : esc(g)}</button>`).join('')}`,
        lect: '<b>Rdt</b> = dernier dividende net ÷ cours. <b>Payout</b> = dividende ÷ BNPA du même exercice. <b>Bêta</b> = sensibilité hebdomadaire au BRVM Composite sur 2 ans. <b>Échanges 3M/j</b> = montant moyen échangé par séance sur 3 mois (liquidité). <b>/SMA200</b> = écart du cours à sa moyenne 200 séances.' })}
    <div class="grid c2">
      ${pn('BRVM · largeur du marché depuis 2008', 'BRVM', cvb('brB', 380), { lect: '<b>Haut</b> : BRVM Composite (échelle log). <b>Milieu</b> : part des actions au-dessus de leur moyenne 200 séances (ambre) et 50 séances (cyan) — au-delà de 70 %, la hausse est généralisée ; sous 30 %, le marché est en repli large. <b>Bas</b> : nouveaux plus hauts 52 semaines moins nouveaux plus bas, par séance.' })}
      ${pn('BRVM · secteurs', 'BRVM', `<table class="t"><thead><tr><th class="l">Secteur</th><th>Titres</th><th>Capi (Md)</th><th>Poids</th><th>Var.%</th><th>YTD</th><th>1 an</th><th>PER méd.</th><th>Rdt méd.</th></tr></thead><tbody>
        ${secAgg.map(a => `<tr><td class="l nm">${esc(a.g)}</td><td>${a.n}</td><td>${num(a.cap / 1e9, 0)}</td><td>${num(a.cap / capTot * 100, 1)}%</td><td>${pc(a.pct)}</td><td>${pc(a.ytd, 1)}</td><td>${pc(a.r1y, 1)}</td><td>${num(a.per, 1)}</td><td>${a.yld ? num(a.yld * 100, 2) + '%' : '—'}</td></tr>`).join('')}</tbody></table>`,
        { np: true, lect: 'Variations pondérées par la capitalisation. PER et rendement : médianes des sociétés du secteur.' })}
    </div>`;
  m.querySelectorAll('[data-sector]').forEach(b => b.onclick = () => { st.sector = b.dataset.sector; render(); });
  m.querySelectorAll('#brT th[data-k]').forEach(th => th.onclick = () => { const k = th.dataset.k; st.sort = { k, dir: st.sort.k === k ? -st.sort.dir : (['id', 'short', 'grp', 'cty', 'per'].includes(k) ? 1 : -1) }; render(); });
  const [B, C] = await Promise.all([getJSON('breadth.json'), series('BRVMC')]); if (!alive()) return;
  const map = new Map(C.x.map((d, i) => [d, C.c[i]])); let lastv = null; const cy = B.d.map(d => { if (map.has(d)) lastv = map.get(d); return lastv; });
  const hl = B.nh.map((v, i) => v - B.nl[i]);
  const ch = new TSChart($('brB'), { panes: [{ h: 1.4, log: true, title: 'BRVM COMPOSITE' }, { h: 1, fixed: [0, 1], fmt: fmtPctAxis, refs: [{ v: .7, color: CL.up }, { v: .3, color: CL.dn }], title: '% > SMA200 / SMA50' }, { h: .7, title: 'NOUV. PLUS HAUTS − PLUS BAS' }] });
  ch.set({ x: B.d, series: [{ y: cy, color: CL.white, label: 'BRVMC' }, { pane: 1, y: B.a200, color: CL.amber, label: '>SMA200', fmt: fmtPctAxis }, { pane: 1, y: B.a50, color: CL.cyan, label: '>SMA50', w: 1, fmt: fmtPctAxis }, { pane: 2, type: 'bar', y: hl, colorFn: v => v >= 0 ? CL.up : CL.dn, label: 'H−B', fmt: v => num(v, 0) }] }, [B.d.length - 1260, B.d.length - 1]);
};

/* ------------------------------------------------------------------ BRVM · flottant officiel (avis de la BRVM, dernier publié) */
async function brvmFloat(m, alive) {
  setTitle('BRVM Overview · Free Float');
  const F = await getJSON('flottant.json').catch(() => null); if (!alive()) return;
  if (!F || !F.rows) { m.innerHTML = pn('Flottant officiel', 'BRVM', '<div class="empty">Aucun avis de flottant lu pour l’instant (lecture chaque soir des avis officiels).</div>'); return; }
  const all = secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity'), st = ST.flo = ST.flo || { sort: { k: 'pct', dir: -1 } };
  const R = all.map(s => { const r = F.rows[s.id]; const mc = r && s.last ? r.flt * s.last : null;
    return { id: s.id, short: s.short || s.n, grp: s.grp, sh: r ? r.sh : null, flt: r ? r.flt : null, pct: r ? r.pct : null, ok15: r ? r.ok15 : null, shnow: s.shares, fnow: s.float, capf: mc, last: s.last, nd: !r }; });
  const rk = sortRows(R, st.sort), nd = R.filter(x => x.nd), nok = R.filter(x => x.ok15 === false);
  const capF = R.reduce((a, x) => a + (x.capf || 0), 0), capT = all.reduce((a, s) => a + (s.mcap || 0), 0);
  const cols = [['id', 'Titre', 1], ['short', 'Société', 1], ['grp', 'Secteur', 1], ['sh', 'Titres (avis)'], ['flt', 'Titres flottants'], ['pct', 'Flottant %'], ['ok15', 'Seuil 15 %'], ['fnow', 'Flottant du jour %'], ['capf', 'Capi. flottante (Md)']];
  m.innerHTML = `<div class="grid side">
    ${pn(`Flottant officiel des sociétés cotées${F.asof ? ' au ' + esc(F.asof) : ''}`, 'BRVM', `<div class="tw" style="max-height:62vh"><table class="t" id="floT"><thead><tr>${thSort(cols, st.sort)}</tr></thead><tbody>
      ${rk.map(x => `<tr data-sec="${x.id}" data-to="DES" class="${x.ok15 === false ? 'hl' : ''}"><td class="l tk">${x.id}</td><td class="l nm">${esc(x.short)}</td><td class="l dm">${esc(x.grp || '')}</td>
        <td>${x.sh != null ? num(x.sh, 0) : '<span class="dm" title="ligne illisible dans l’avis">n.d.</span>'}</td><td>${x.flt != null ? num(x.flt, 0) : '<span class="dm">n.d.</span>'}</td><td class="wh">${x.pct != null ? num(x.pct, 2) + ' %' : '<span class="dm">n.d.</span>'}</td>
        <td>${x.ok15 == null ? '<span class="dm">—</span>' : x.ok15 ? '<span class="up">respecté</span>' : '<span class="dn">non respecté</span>'}</td><td class="dm">${x.fnow != null ? num(x.fnow, 2) + ' %' : '—'}</td><td>${x.capf ? num(x.capf / 1e9, 1) : '—'}</td></tr>`).join('')}</tbody></table></div>`,
      { np: true, sel: `avis publié le ${fds(F.d)} · ${R.length - nd.length} sociétés lues sur ${R.length}`, tools: F.u ? `<a href="${esc(F.u)}" target="_blank" rel="noopener" class="tb alt">Avis officiel (PDF)</a>` : '',
        lect: `Flottant = part du capital détenue par le public, déclarée par les émetteurs et les SGI registraires (Instruction n° 01-2022/BRVM/DG) ; le seuil réglementaire est de 15 % du capital. <b>Flottant du jour</b> = capitalisation flottante ÷ capitalisation globale de la séance. <b>Capi. flottante</b> = titres flottants de l’avis × dernier cours. ${nd.length ? 'Lignes <b>n.d.</b> : illisibles dans le document scanné (' + nd.map(x => x.id).join(', ') + ') — rien n’est estimé.' : ''}` })}
    <div class="grid" style="align-content:start">
      ${pn('Synthèse', 'BRVM', `<div class="kv2"><span>Sociétés sous le seuil de 15 %</span><b class="${nok.length ? 'dn' : ''}">${nok.length}${nok.length ? ' · ' + nok.map(x => x.id).join(', ') : ''}</b><span>Flottant médian</span><b>${(() => { const v = R.map(x => x.pct).filter(x => x != null).sort((a, b) => a - b); return v.length ? num(v[Math.floor(v.length / 2)], 1) + ' %' : '—'; })()}</b><span>Capitalisation flottante totale</span><b>${big(capF)} XOF</b><span>Capitalisation totale du marché</span><b>${big(capT)} XOF</b><span>Flottant global pondéré</span><b>${capT ? num(capF / capT * 100, 1) + ' %' : '—'}</b></div>`)}
      ${pn('Flottant par société (%)', 'BRVM', cvb('floB', Math.max(300, R.length * 15)))}
    </div></div>`;
  m.querySelectorAll('#floT th[data-k]').forEach(th => th.onclick = () => { const k = th.dataset.k; st.sort = { k, dir: st.sort.k === k ? -st.sort.dir : -1 }; render(); });
  const L = R.filter(x => x.pct != null).sort((a, b) => b.pct - a.pct);
  hbars($('floB'), L.map(x => x.id), L.map(x => x.pct), v => num(v, 1) + ' %', 15);
}

/* ------------------------------------------------------------------ GP (style Bloomberg par défaut : aire bleu nuit, ligne blanche, cartouche
   Dernier / Plus haut / Moyenne / Plus bas sur la période affichée, volume en dessous ; bougies, ligne, aire et études toujours disponibles) */
const MOIS_AX = ['Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc'];
function bbgTicks(xs, i0, i1, span, W) {
  const mode = span > 2600 ? 'Y' : span > 800 ? 'Q' : span > 80 ? 'M' : span > 24 ? 'W' : 'D'; const out = []; let pk = null;
  for (let i = Math.max(0, i0); i <= i1; i++) { const d = xs[i], y = Math.floor(d / 10000), mo = Math.floor(d / 100) % 100, dd = d % 100; let key, lab;
    if (mode === 'Y') { key = y; lab = String(y); } else if (mode === 'Q') { key = y * 10 + Math.floor((mo - 1) / 3); lab = mo <= 3 ? String(y) : MOIS_AX[mo - 1]; }
    else if (mode === 'M') { key = y * 100 + mo; lab = mo === 1 ? String(y) : MOIS_AX[mo - 1]; } else if (mode === 'W') { key = isoWeekKey(d); lab = String(dd).padStart(2, '0') + '/' + String(mo).padStart(2, '0'); }
    else { key = d; lab = String(dd).padStart(2, '0') + '/' + String(mo).padStart(2, '0'); }
    if (pk !== null && key !== pk) out.push([i, lab]); pk = key; }
  const room = Math.max(2, Math.floor((W || 800) / 64)); if (out.length <= room) return out;
  /* trop de repères : priorité aux années, puis espacement minimal (en séances) entre étiquettes retenues */
  const gap = (i1 - i0) / room, keep = [];
  const tryAdd = o => { if (keep.every(k => Math.abs(k[0] - o[0]) >= gap)) keep.push(o); };
  out.filter(o => /^\d{4}$/.test(o[1])).forEach(tryAdd); out.filter(o => !/^\d{4}$/.test(o[1])).forEach(tryAdd);
  return keep.sort((a, b) => a[0] - b[0]);
}
/* agrégation hebdomadaire / mensuelle (comme le menu « Daily ▾ » de GP) */
function aggOHLC(S, per, tr) {
  if (per === 'D') return { x: S.x, o: S.o, h: S.h, l: S.l, c: S.c, v: S.v, tr };
  const key = d => per === 'W' ? isoWeekKey(d) : Math.floor(d / 100); const R = { x: [], o: [], h: [], l: [], c: [], v: [], tr: tr ? [] : null }; let k0 = null;
  for (let i = 0; i < S.x.length; i++) { const k = key(S.x[i]); const j = R.x.length - 1;
    if (k !== k0) { R.x.push(S.x[i]); R.o.push(S.o[i]); R.h.push(S.h[i]); R.l.push(S.l[i]); R.c.push(S.c[i]); R.v.push(S.v[i] || 0); if (tr) R.tr.push(tr[i]); k0 = k; }
    else { R.x[j] = S.x[i]; R.h[j] = Math.max(R.h[j], S.h[i]); R.l[j] = Math.min(R.l[j], S.l[i]); R.c[j] = S.c[i]; R.v[j] += S.v[i] || 0; if (tr) R.tr[j] = tr[i]; } }
  return R;
}
const dmy = d => fmtD(d); const dmyShort = d => fmtD(d).slice(0, 6) + fmtD(d).slice(8);
function parseDMY(t) { const m = String(t || '').trim().match(/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})$/); if (!m) return null; let y = +m[3]; if (y < 100) y += 2000; return y * 10000 + (+m[2]) * 100 + (+m[1]); }
/* conversion de devise (champ « Devise » du GP) : facteurs alignés sur les dates, XOF / EUR à la parité fixe de 655,957 */
const XOF_EUR = 655.957, FX_SER = { XOF: 'USDXOF', EUR: 'EURUSD', TWD: 'USDTWD' };
const FX_OK = s => s && ['XOF', 'USD', 'EUR', 'TWD'].includes(s.ccy) && !['Rate', 'Curncy'].includes(s.cls) && !/%/.test(s.ccy || '');  /* (une paire de devises convertie dans l'une de ses devises n'a pas de sens) */
async function fxFactor(from, to, xs) {
  if (!from || !to || from === to) return null;
  if (from === 'XOF' && to === 'EUR') return xs.map(() => 1 / XOF_EUR); if (from === 'EUR' && to === 'XOF') return xs.map(() => XOF_EUR);
  const al = async id => { if (!Q.by[id]) return null; const F = await series(id).catch(() => null); if (!F) return null; const mp = new Map(F.x.map((d, i) => [d, F.c[i]])); let lv = null, j = 0; const out = [];
    for (const d of xs) { while (j < F.x.length && F.x[j] <= d) { lv = F.c[j]; j++; } out.push(mp.has(d) ? mp.get(d) : lv); } return out; };
  /* dollars par unité de devise, date par date */
  const usdPer = async c => { if (c === 'USD') return xs.map(() => 1);
    if (c === 'XOF') { const u = await al('USDXOF'); if (u) return u.map(v => v ? 1 / v : null); const e = await al('EURUSD'); return e ? e.map(v => v ? v / XOF_EUR : null) : null; }
    if (c === 'EUR') { const e = await al('EURUSD'); if (e) return e; const u = await al('USDXOF'); return u ? u.map(v => v ? XOF_EUR / v : null) : null; }
    if (c === 'TWD') { const t = await al('USDTWD'); return t ? t.map(v => v ? 1 / v : null) : null; } return null; };
  const a = await usdPer(from), b = await usdPer(to); if (!a || !b) return null; return a.map((v, i) => v != null && b[i] ? v / b[i] : null);
}
const fxApply = (arr, f) => f ? arr.map((v, i) => v == null || f[i] == null ? null : v * f[i]) : arr;

/* icônes de type de graphique (barre d'outils GP) */
const GP_ICO = { bbg: '<svg width="16" height="12" viewBox="0 0 16 12"><path d="M0 11 L4 6 L7 8 L11 2 L16 5 L16 12 L0 12Z" fill="#2e5a9c"/><path d="M0 11 L4 6 L7 8 L11 2 L16 5" stroke="#fff" fill="none" stroke-width="1.2"/></svg>',
  line: '<svg width="16" height="12" viewBox="0 0 16 12"><path d="M0 10 L4 5 L7 7 L11 1 L16 4" stroke="#fff" fill="none" stroke-width="1.3"/></svg>',
  area: '<svg width="16" height="12" viewBox="0 0 16 12"><path d="M0 10 L4 5 L7 7 L11 1 L16 4 L16 12 L0 12Z" fill="#666"/><path d="M0 10 L4 5 L7 7 L11 1 L16 4" stroke="#fff" fill="none" stroke-width="1.1"/></svg>',
  candle: '<svg width="16" height="12" viewBox="0 0 16 12"><path d="M3 0V12M8 2V10M13 1V11" stroke="#bbb"/><rect x="1.5" y="3" width="3" height="6" fill="#2fd26a"/><rect x="6.5" y="4" width="3" height="4" fill="#ff3d4d"/><rect x="11.5" y="2" width="3" height="7" fill="#2fd26a"/></svg>' };
const GP_EVC = { D: ['#2fd26a', 'Dividende'], R: ['#f9a33a', 'Résultats / états financiers'], A: ['#b48cff', 'Assemblée générale'], S: ['#5fd0ea', 'Fractionnement'] };

PAGES.GP = async (m, alive) => {
  const s = sec(ST.sec), g = ST.gp; g.ma = g.ma || ['', '', '']; g.per = g.per || 'D'; g.px = g.px || 'last'; if (g.volOn == null) g.volOn = true; if (g.ev == null) g.ev = true;
  if (g.ccySec !== s.id) { g.ccySec = s.id; g.ccy = ''; }
  const S0r = await series(ST.sec); if (!alive()) return;
  const intra = ST.sec === 'QQQ' && Q.live && Q.live.intraday && Q.live.intraday.t && Q.live.intraday.t.length > 10;
  const monthly = S0r.f === 'M'; if (monthly) g.per = 'D';
  const ranges = monthly ? ['5A', '10A', '20A', '50A', 'MAX'] : ['1M', '3M', '6M', 'YTD', '1A', '3A', '5A', '10A', 'MAX'];
  if (!ranges.includes(g.range) && !(intra && g.range === '1J')) g.range = monthly ? '20A' : '1A';
  if (g.range === '1J' && !intra) g.range = '1A';
  let TR = null; if (g.px === 'tr') { TR = await trSeries(s, S0r); if (!alive()) return; if (!TR) { g.px = 'last'; toast('Pas de dividende recensé pour ce titre : rendement total = cours.'); } }
  /* devise d'affichage */
  const ccyL = s.ccy || '', ccyOpts = FX_OK(s) ? [...new Set([ccyL, 'USD', 'EUR', 'XOF'])] : [ccyL]; if (!ccyOpts.includes(g.ccy)) g.ccy = '';
  const ccyT = g.ccy || ccyL; let FXF = null;
  if (g.ccy && g.ccy !== ccyL) { FXF = await fxFactor(ccyL, g.ccy, S0r.x); if (!alive()) return; if (!FXF) { g.ccy = ''; toast('Conversion indisponible : cours de change manquant.'); } }
  const S0 = FXF ? Object.assign({}, S0r, { o: fxApply(S0r.o, FXF), h: fxApply(S0r.h, FXF), l: fxApply(S0r.l, FXF), c: fxApply(S0r.c, FXF) }) : S0r; if (TR && FXF) TR = fxApply(TR, FXF);
  const S = aggOHLC(S0, g.per, TR), n = S.x.length, Y0 = g.px === 'tr' && S.tr ? S.tr : S.c;
  const bbg = g.type === 'bbg', hasVol = S0.v.slice(-260).filter(v => v > 0).length > 120;
  const dec = FXF ? (g.ccy === 'XOF' ? 0 : 2) : pxd(s), fmtP = v => num(v, dec);
  const MA_DEF = ['50', '200', '']; const maOn = !!g.maOn; const MAS = maOn ? g.ma.map((v, j) => v || (g.ma.every(x => !x) ? MA_DEF[j] : '')) : ['', '', ''];
  setTitle(g.cmp.length ? 'Comparative Returns' : g.type === 'candle' ? 'Candle Chart' : g.type === 'area' ? 'Mountain Chart' : 'Line Chart');
  const peers = secsWhere(x => x.id !== s.id && x.mkt === s.mkt && x.cls === s.cls && x.grp === s.grp && !legacy(x)).sort((a, b) => (b.liq || 0) - (a.liq || 0)).slice(0, 6);
  const bench = s.bench && Q.by[s.bench] && s.bench !== s.id ? s.bench : null;
  const editMenu = () => [{ h: 'Style du graphique' }, ...[['bbg', 'Bloomberg (aire bleue, ligne blanche)'], ['line', 'Ligne'], ['area', 'Aire'], ['candle', 'Bougies']].map(([k, l]) => ({ l: (g.type === k ? '● ' : '○ ') + l, run: () => { g.type = k; render(); } })),
    { h: 'Affichage' }, { l: (g.log ? '● ' : '○ ') + 'Échelle logarithmique', run: () => { g.log = !g.log; render(); } }, { l: (g.volOn ? '● ' : '○ ') + 'Volume', run: () => { g.volOn = !g.volOn; render(); } },
    { l: (g.maOn ? '● ' : '○ ') + 'Moyennes mobiles', run: () => { g.maOn = !g.maOn; render(); } }, { l: (g.ev ? '● ' : '○ ') + 'Événements clés (dividendes, résultats, AG)', run: () => { g.ev = !g.ev; render(); } },
    { l: (g.tbl ? '● ' : '○ ') + 'Tableau des cours', run: () => { g.tbl = !g.tbl; render(); } }, { l: document.body.classList.contains('maxi') ? 'Réduire la fenêtre' : 'Agrandir la fenêtre (plein écran)', run: () => toggleMaxi() }];
  const relMenu = () => [{ h: 'Études' }, ...[['o', 'boll', 'Bandes de Bollinger (20, 2σ)'], ['s', 'rsi', 'RSI (14)'], ['s', 'macd', 'MACD (12, 26, 9)'], ['s', 'dd', 'Drawdown depuis le plus haut']].map(([t, k, l]) => ({ l: ((t === 'o' ? g.ov[k] : g.st[k]) ? '● ' : '○ ') + l, run: () => { if (t === 'o') g.ov[k] = !g.ov[k]; else g.st[k] = !g.st[k]; render(); } })),
    { h: 'Données' }, { l: (g.px === 'tr' ? '● ' : '○ ') + 'Rendement total (dividendes réinvestis)', run: () => { g.px = g.px === 'tr' ? 'last' : 'tr'; render(); } }, { l: (g.maOn ? '● ' : '○ ') + 'Moyennes mobiles', run: () => { g.maOn = !g.maOn; render(); } },
    hasVol ? { l: (g.volOn ? '● ' : '○ ') + 'Volume', run: () => { g.volOn = !g.volOn; render(); } } : null, { l: (g.ev ? '● ' : '○ ') + 'Événements clés', run: () => { g.ev = !g.ev; render(); } },
    bench ? { h: 'Comparer' } : null, bench ? { code: bench, l: 'Indice de référence · ' + esc(Q.by[bench].n), run: () => { if (!g.cmp.includes(bench)) g.cmp.push(bench); render(); } } : null].filter(Boolean);
  const suggest = () => [{ h: 'Graphiques suggérés' },
    { l: 'Cours et moyennes mobiles 50 / 200 séances (1 an)', run: () => { Object.assign(g, { type: 'bbg', range: '1A', per: 'D', px: 'last', maOn: true, ma: ['50', '200', ''], cmp: [] }); render(); } },
    s.cls !== 'Curncy' && !monthly ? { l: 'Bougies quotidiennes (6 mois)', run: () => { Object.assign(g, { type: 'candle', range: '6M', per: 'D', px: 'last', cmp: [] }); render(); } } : null,
    { l: 'Rendement total, dividendes réinvestis (5 ans)', run: () => { Object.assign(g, { type: 'bbg', range: '5A', px: 'tr', cmp: [] }); render(); } },
    bench ? { l: 'Performance comparée à ' + esc(Q.by[bench].n) + ' (1 an)', run: () => { Object.assign(g, { range: '1A', cmp: [bench] }); render(); } } : null,
    { l: 'Historique complet, échelle logarithmique, mensuel', run: () => { Object.assign(g, { type: 'bbg', range: 'MAX', per: monthly ? 'D' : 'M', log: true, cmp: [] }); render(); } },
    { l: 'Cours, RSI et MACD (1 an)', run: () => { Object.assign(g, { type: 'line', range: '1A', per: 'D', cmp: [] }); g.st.rsi = true; g.st.macd = true; render(); } },
    { h: 'Autres fonctions graphiques' }, ...['HVT', 'VAP', 'SEAS', 'COMP', 'TRA'].filter(c => FN[c] && !avail(c, s)).map(c => ({ code: c, l: esc(FN[c][4]), run: () => go(c, s.id) }))].filter(Boolean);
  setActs([{ n: 94, l: 'Graphiques suggérés', menu: suggest },
    { n: 95, l: 'Comparer', menu: () => [{ h: 'Ajouter à la comparaison' }].concat(bench ? [{ code: bench, l: 'Indice de référence · ' + esc(Q.by[bench].n), run: () => { if (!g.cmp.includes(bench)) g.cmp.push(bench); render(); } }] : [],
      peers.map(p => ({ code: p.id, l: esc(p.short || p.n), run: () => { if (!g.cmp.includes(p.id)) g.cmp.push(p.id); render(); } })),
      [{ l: 'Autre titre : taper son code dans « Ajouter des données »', run: () => { const i = $('cmpIn'); if (i) i.focus(); } }], g.cmp.length ? [{ l: 'Effacer les comparaisons', run: () => { g.cmp = []; render(); } }] : []) },
    { n: 97, l: 'Édition', menu: editMenu }]);
  const tb = (k, l, on, t) => `<button class="tb ${on ? 'on' : ''}" data-gp="${k}"${t ? ` title="${esc(t)}"` : ''}>${l}</button>`;
  const ck = (id, on, l, t) => `<label class="gck" title="${esc(t || '')}"><input type="checkbox" id="${id}" ${on ? 'checked' : ''}><i></i>${l}</label>`;
  const row1 = `<div class="tools gpr"><input class="ofld dt" id="gpD0" title="Début (jj/mm/aaaa)"><span class="cal">▦</span><span class="dm">–</span><input class="ofld dt" id="gpD1" title="Fin (jj/mm/aaaa)"><span class="cal">▦</span>
      <select class="ofld" id="gpPx" title="Donnée tracée"><option value="last" ${g.px === 'last' ? 'selected' : ''}>Dernier cours</option><option value="tr" ${g.px === 'tr' ? 'selected' : ''}>Rendement total</option></select>
      <select class="ofld" id="gpCcy" title="Devise d'affichage" ${ccyOpts.length < 2 ? 'disabled' : ''}>${ccyOpts.map(c => `<option value="${c === ccyL ? '' : c}" ${(g.ccy || ccyL) === c ? 'selected' : ''}>${c === ccyL ? 'Devise locale' + (c ? ' (' + c + ')' : '') : c}</option>`).join('')}</select>
      ${ck('gpMaOn', maOn, 'Moy. mobiles', 'Moyennes mobiles (50 et 200 séances par défaut)')}${maOn ? `<span class="gmas">${g.ma.map((v, i) => `<input class="ofld ma" data-ma="${i}" value="${esc(v || (g.ma.every(x => !x) ? MA_DEF[i] : ''))}" placeholder="—" title="Période de la moyenne mobile ${i + 1}">`).join('')}</span>` : `<span class="gpen" id="gpMaEd" title="Choisir les périodes">✎</span>`}
      ${ck('gpEv', g.ev, 'Événements clés', 'Dividendes (D), résultats, états financiers et rapports d’activité (R), assemblées générales (A)')}<span class="gsp"></span><button class="tb gmx" id="gpMx" title="${document.body.classList.contains('maxi') ? 'Réduire' : 'Agrandir (plein écran)'}">${document.body.classList.contains('maxi') ? '⤡ Réduire' : '⤢ Agrandir'}</button></div>`;
  const row2 = `<div class="tools gpr2">${(intra ? ['1J'] : []).concat(ranges).map(r => tb('r:' + r, r === 'MAX' ? 'Max' : r, g.range === r, r === '1J' ? 'Séance du jour, barres de 5 minutes (heure de New York)' : '')).join('')}
      ${!monthly ? `<select class="ofld dk" id="gpPer"><option value="D" ${g.per === 'D' ? 'selected' : ''}>Quotidien</option><option value="W" ${g.per === 'W' ? 'selected' : ''}>Hebdomadaire</option><option value="M" ${g.per === 'M' ? 'selected' : ''}>Mensuel</option></select>` : ''}
      <span class="gico">${['bbg', 'line', 'area'].concat(s.cls !== 'Curncy' && !monthly ? ['candle'] : []).map(k => `<button class="tb ico ${g.type === k ? 'on' : ''}" data-gp="t:${k}" title="${{ bbg: 'Montagne Bloomberg', line: 'Ligne', area: 'Aire', candle: 'Bougies' }[k]}">${GP_ICO[k]}</button>`).join('')}</span>
      <button class="tb ${g.tbl ? 'on' : ''}" id="gpTb" title="Tableau des cours de la période affichée">Tableau</button>
      <span class="gsp"></span><button class="tb gdd" id="gpRel" title="Études et données liées">+ Données liées ▾</button><input id="cmpIn" class="gadd" placeholder="Ajouter des données" title="Comparer : tapez un code (ex. BRVMC, NVDA) puis Entrée">${g.cmp.map(c => `<button class="tb alt on" data-gp="x:${c}" title="Retirer">${c} ✕</button>`).join('')}
      <button class="tb gdd" id="gpEd" title="Modifier le graphique">« Modifier ${ICO.gear}</button></div>`;
  const sugg = (s.cls === 'Index' ? ['MEMB', 'MOV', 'HVT'] : s.cls === 'Equity' ? ['HVT', 'VAP', 'DVD'] : s.cls === 'Comdty' ? ['HVT', 'SEAS', 'BMAP'] : ['HVT', 'SEAS', 'CORR']).filter(c => FN[c] && (FN[c][1] === 'mkt' || !avail(c, s))).slice(0, 2);
  const sugBar = `<div class="gpsug"><span class="gl">Fonctions suggérées</span>${sugg.map(c => `<span class="gi" data-fn="${c}"><b>${c}</b>${esc(FN[c][3] || FN[c][4])}</span>`).join('')}</div>`;
  const showSide = !document.body.classList.contains('maxi') || g.tbl;
  m.innerHTML = `<div class="grid ${showSide ? 'side' : ''} gpg">
    <div class="pn gpm">${row1}${row2}<div class="gpcw"><div class="gpbar"><span id="gpZ" title="Zoom avant sur le centre (molette : zoom libre)">⌕ Zoom</span><span id="gpRs" title="Revenir à la période choisie (double-clic)">⟲ Vue initiale</span></div><div class="cv" id="gpCv" style="height:420px"></div></div>${sugBar}</div>
    ${showSide ? `<div class="grid gpside" style="align-content:start">${g.tbl ? pn('Tableau des cours', 'GP', '<div class="tw" id="gpTbl" style="max-height:calc(100vh - 230px)"></div>', { np: true, sel: esc(ccyT) }) : `${pn('Statistiques', '', '<div class="kv2" id="gpKv"></div>')}<div id="gpSide"></div>`}</div>` : ''}</div>`;
  /* hauteur : le graphique remplit la fenêtre (bandeau d'actualités déduit sauf en plein écran) */
  const fit = () => { const cv = $('gpCv'); if (!cv) return; const top = cv.getBoundingClientRect().top, nw = document.body.classList.contains('maxi') || PREF.nonews ? 0 : ($('nwp') ? $('nwp').offsetHeight : 0), sg = m.querySelector('.gpsug');
    cv.style.height = Math.max(340, Math.floor(window.innerHeight - top - nw - (sg ? sg.offsetHeight : 0) - 10)) + 'px'; };
  fit(); window.onresize = () => { if (ST.fn === 'GP') fit(); };
  const inp = $('cmpIn'); inp.onkeydown = e => { if (e.key === 'Enter') { const r = searchSecs(inp.value)[0]; if (r && r.id !== ST.sec && !g.cmp.includes(r.id)) { g.cmp.push(r.id); render(); } else if (!r) toast('Titre introuvable.'); } };
  m.querySelectorAll('[data-gp]').forEach(b => b.onclick = () => { const [k, v] = b.dataset.gp.split(':');
    if (k === 'r') { g.range = v; if (v === '1J' || chart.intra || g.cmp.length) render(); else chart.setView(...rangeView(v)); m.querySelectorAll('[data-gp^="r:"]').forEach(x => x.classList.toggle('on', x === b)); return; }
    if (k === 't') g.type = v; if (k === 'x') g.cmp = g.cmp.filter(c => c !== v); render(); });
  $('gpPx').onchange = e => { g.px = e.target.value; render(); }; $('gpCcy').onchange = e => { g.ccy = e.target.value; render(); }; if ($('gpPer')) $('gpPer').onchange = e => { g.per = e.target.value; render(); };
  $('gpMaOn').onchange = e => { g.maOn = e.target.checked; render(); }; if ($('gpMaEd')) $('gpMaEd').onclick = () => { g.maOn = true; render(); }; $('gpEv').onchange = e => { g.ev = e.target.checked; render(); };
  $('gpTb').onclick = () => { g.tbl = !g.tbl; render(); }; $('gpRel').onclick = e => ddOpen(e.currentTarget, relMenu()); $('gpEd').onclick = e => ddOpen(e.currentTarget, editMenu()); $('gpMx').onclick = () => toggleMaxi();
  m.querySelectorAll('[data-ma]').forEach(el => el.onchange = () => { const v = el.value.trim(); g.ma = [...m.querySelectorAll('[data-ma]')].map(x => /^\d{1,3}$/.test(x.value.trim()) && +x.value.trim() > 1 ? x.value.trim() : ''); if (g.ma.every(x => !x)) g.maOn = false; render(); });
  const rangeView = r => { const last = S.x[n - 1], y = Math.floor(last / 10000); const back = { '1M': 100, '3M': 300, '6M': 600, '1A': 10000, '3A': 30000, '5A': 50000, '10A': 100000, '20A': 200000, '50A': 500000 }[r];
    let from = r === 'YTD' ? y * 10000 + 101 : r === 'MAX' ? 0 : last - back; let i0 = S.x.findIndex(d => d >= from); if (i0 < 0) i0 = 0; return [Math.min(i0, Math.max(0, n - 5)), n - 1]; };
  /* tableau des cours de la période affichée (comme « Table » du GP) */
  let tblRaf = 0; const fillTbl = (i0, i1) => { const t = $('gpTbl'); if (!t) return; cancelAnimationFrame(tblRaf); tblRaf = requestAnimationFrame(() => { const rows = []; for (let i = i1; i >= Math.max(i0, i1 - 600); i--) { const p = Y0[i], q = i > 0 ? Y0[i - 1] : null, ch = p != null && q ? p - q : null;
      rows.push(`<tr><td class="l">${fd(S.x[i])}</td><td class="wh">${fmtP(p)}</td><td class="${cls(ch)}">${ch != null ? (ch > 0 ? '+' : '') + fmtP(ch) : '—'}</td><td>${ch != null ? pc(ch / q) : '—'}</td>${hasVol ? `<td>${S.v[i] ? big(S.v[i]) : '—'}</td>` : ''}</tr>`); }
    t.innerHTML = `<table class="t"><thead><tr><th class="l">Date</th><th>${g.px === 'tr' ? 'Rdt total' : 'Dernier'}</th><th>Var.</th><th>Var. %</th>${hasVol ? '<th>Volume</th>' : ''}</tr></thead><tbody>${rows.join('')}</tbody></table>`; }); };
  const setDates = (i0, i1) => { const a = $('gpD0'), b = $('gpD1'); if (a && document.activeElement !== a) a.value = dmy(S.x[Math.max(0, i0)]); if (b && document.activeElement !== b) b.value = dmy(S.x[Math.min(n - 1, i1)]); if (g.tbl) fillTbl(i0, i1); };
  const panes = [{ h: 3, log: g.log && !g.cmp.length, fmt: g.cmp.length ? fmtPctAxis : null, noLegend: bbg && !g.cmp.length }]; const ser = []; let pi = 0; let chart;
  const MA_COL = ['#ffd200', '#ff5fd2', '#5fd0ea'];
  /* événements clés : dividendes (date de détachement), résultats / états financiers et AG (BRVM), dividendes versés (US) */
  const EV = []; if (g.ev && !g.cmp.length && !(g.range === '1J' && intra)) {
    const at = d => { let lo = 0, hi = n - 1; if (d > S.x[hi] || d < S.x[0]) return -1; while (lo < hi) { const mid = (lo + hi) >> 1; if (S.x[mid] < d) lo = mid + 1; else hi = mid; } return lo; };
    if (isBRVM(s) && s.cls === 'Equity') { const [DV, EVS] = await Promise.all([getJSON('dividends.json').catch(() => []), getJSON('events.json').catch(() => [])]); if (!alive()) return;
      for (const x of DV) if (x.t === s.id && x.dps && (x.det || x.pay)) { const i = at(s2i((x.det || x.pay).slice(0, 10))); if (i >= 0) EV.push({ i, k: 'D', t: `Dividende ${x.ex ? 'de l’exercice ' + x.ex : ''} : ${num(FXF ? x.dps * (FXF[S0.x.indexOf(S.x[i])] || 0) : x.dps, FXF ? 2 : 0)} ${ccyT}${x.det ? ' · détachement ' + fds(x.det) : ''}` }); }
      const seen = new Set(); for (const e of EVS) { if (e.t !== s.id || !e.d) continue; const k = /États financiers|Résultats financiers|Rapport des commissaires|Rapport d'activité|Rapport annuel/.test(e.c) ? 'R' : /^Assemblée générale$/.test(e.c) ? 'A' : /Fractionnement/.test(e.c) ? 'S' : null; if (!k) continue;
        const i = at(s2i(e.d.slice(0, 10))); if (i < 0 || seen.has(k + i)) continue; seen.add(k + i); EV.push({ i, k, t: `${GP_EVC[k][1]} · ${fds(e.d)} : ${e.ti || ''}` }); } }
    else if (S0r.div && S0r.div.some(v => v)) { for (let j = 0; j < S0r.x.length; j++) if (S0r.div[j]) { const i = at(S0r.x[j]); if (i >= 0) EV.push({ i, k: 'D', t: `Dividende de ${num(S0r.div[j] * (FXF ? FXF[j] || 0 : 1), 4)} ${ccyT} par action · ${fd(S0r.x[j])}` }); } } }
  if (g.range === '1J' && intra) {
    const I = Q.live.intraday, tt = I.t.map(t => { const d = new Date(t * 1000); return d.getUTCFullYear() * 1e8 + (d.getUTCMonth() + 1) * 1e6 + d.getUTCDate() * 1e4 + d.getUTCHours() * 100 + d.getUTCMinutes(); });
    const ny = t => new Date(t * 1000).toLocaleTimeString('fr-FR', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit' });
    chart = new TSChart($('gpCv'), { panes: [{ h: 3 }, { h: .8 }], grid: bbg ? 'dot' : null, xfmt: (v) => { const i = tt.indexOf(v); return i >= 0 ? ny(I.t[i]) : ''; } }); chart.intra = true;
    chart.set({ x: tt, series: [bbg ? { type: 'area', y: I.c, color: '#ffffff', w: 1.3, grad: ['rgba(7,42,82,.97)', 'rgba(3,29,56,.97)'], label: 'QQQ 5 min (heure NY)' } : { type: 'candle', o: I.o, h: I.h, l: I.l, c: I.c, label: 'QQQ 5 min (heure NY)' }, { pane: 1, type: 'bar', y: I.v, colorFn: (v, i) => I.c[i] >= I.o[i] ? rgba(CL.up, .6) : rgba(CL.dn, .6), label: 'Vol' }] }, [0, tt.length - 1]);
    ['gpD0', 'gpD1'].forEach(id => { const e = $(id); if (e) e.disabled = true; });
  } else {
    if (g.cmp.length) {
      const [i0] = rangeView(g.range), base = Y0[i0]; ser.push({ y: Y0.map((v, i) => i < i0 || v == null ? null : v / base - 1), color: CL.white, w: 1.6, label: s.id + (FXF ? ' (' + ccyT + ')' : ''), fmt: fmtPctAxis });
      const colors = [CL.amber, CL.cyan, CL.violet, CL.pink, CL.teal];
      for (const [k, cid] of g.cmp.entries()) { const C = await series(cid); if (!alive()) return; const cs = Q.by[cid]; const F2 = FXF && FX_OK(cs) && cs.ccy !== ccyT ? await fxFactor(cs.ccy, ccyT, C.x) : null; if (!alive()) return; const Cc = F2 ? fxApply(C.c, F2) : C.c;
        const mp = new Map(C.x.map((d, i) => [d, Cc[i]])); let lv = null; const al = S.x.map(d => { if (mp.has(d)) lv = mp.get(d); else if (C.f === 'M') { const mk = Math.floor(d / 100) * 100 + 1; if (mp.has(mk)) lv = mp.get(mk); } return lv; });
        const b = al[i0] || al.find((v, i) => i >= i0 && v != null); ser.push({ y: al.map((v, i) => i < i0 || v == null || !b ? null : v / b - 1), color: colors[k % colors.length], label: cid + (F2 ? ' (' + ccyT + ')' : ''), fmt: fmtPctAxis }); }
    } else {
      if (g.type === 'candle' && !monthly && s.cls !== 'Curncy' && g.px === 'last') ser.push({ type: 'candle', o: S.o, h: S.h, l: S.l, c: S.c, label: s.id, fmt: fmtP });
      else if (bbg) ser.push({ type: 'area', y: Y0, color: '#ffffff', w: 1.25, grad: ['rgba(7,42,82,.97)', 'rgba(3,29,56,.97)'], label: g.px === 'tr' ? 'Rendement total' : 'Dernier cours', fmt: fmtP });
      else ser.push({ type: g.type === 'area' ? 'area' : 'line', y: Y0, color: CL.white, label: s.id + (g.px === 'tr' ? ' (rendement total)' : ''), fmt: fmtP, fill: rgba(CL.white, .07) });
      MAS.forEach((v, j) => { if (v) ser.push({ y: Array.from(U.sma(Y0, +v)), color: MA_COL[j], w: 1.1, label: 'MM ' + v, fmt: fmtP }); });
      if (g.ov.boll) { const mm = U.sma(Y0, 20), sd = U.rollStd(Y0, 20), up = [], dn = []; for (let i = 0; i < n; i++) { const a = mm[i], v = sd[i]; up.push(isFinite(a) && isFinite(v) ? a + 2 * v : null); dn.push(isFinite(a) && isFinite(v) ? a - 2 * v : null); }
        ser.push({ type: 'band', y1: up, y2: dn, fill: rgba(CL.violet, .1), noScale: true }, { y: up, color: rgba(CL.violet, .7), w: 1, noScale: true }, { y: dn, color: rgba(CL.violet, .7), w: 1, noScale: true }); }
    }
    if (g.volOn && hasVol) { pi++; const vma = U.sma(S.v, 15); panes.push({ h: .75, title: bbg ? '' : 'VOLUME', zero: true, noLegend: bbg });
      ser.push({ pane: pi, type: 'bar', y: S.v, colorFn: bbg ? () => 'rgba(215,215,215,.78)' : (v, i) => S.c[i] >= S.o[i] ? rgba(CL.up, .55) : rgba(CL.dn, .55), label: 'Volume', fmt: v => big(v) });
      if (bbg) ser.push({ pane: pi, y: Array.from(vma), color: '#ffd200', w: 1, label: 'Moy. mob. (15)', fmt: v => big(v) }); }
    if (g.st.rsi) { pi++; panes.push({ h: .8, fixed: [0, 100], refs: [{ v: 70, color: CL.dn }, { v: 30, color: CL.up }], title: 'RSI 14' }); ser.push({ pane: pi, y: Array.from(U.rsi(S.c, 14)), color: CL.amber, label: 'RSI', fmt: v => num(v, 1) }); }
    if (g.st.macd) { pi++; const e12 = U.ema(S.c, 12), e26 = U.ema(S.c, 26), mac = S.c.map((_, i) => e12[i] - e26[i]), sig = U.ema(mac, 9); panes.push({ h: .8, title: 'MACD 12-26-9', refs: [{ v: 0, color: CL.dim2, dash: [] }] });
      ser.push({ pane: pi, type: 'bar', y: mac.map((v, i) => v - sig[i]), colorFn: v => v >= 0 ? rgba(CL.up, .6) : rgba(CL.dn, .6), label: 'Hist' }, { pane: pi, y: mac, color: CL.cyan, w: 1, label: 'MACD' }, { pane: pi, y: Array.from(sig), color: CL.amber, w: 1, label: 'Signal' }); }
    if (g.st.dd) { pi++; let pk = -Infinity; const dd = Y0.map(v => { if (v != null) pk = Math.max(pk, v); return v == null ? null : v / pk - 1; }); panes.push({ h: .8, fmt: fmtPctAxis, title: 'DRAWDOWN DEPUIS LE PLUS HAUT', max: 0 }); ser.push({ pane: pi, type: 'area', y: dd, color: CL.dn, fill: rgba(CL.dn, .2), label: 'DD', fmt: fmtPctAxis, base: 0 }); }
    /* cartouche Bloomberg : Dernier, plus haut (date), moyenne, plus bas (date) sur la période affichée ; étiquette blanche du dernier cours sur l'axe ; marqueurs d'événements */
    let EVPOS = [];
    const after = (x, o) => { EVPOS = []; if (g.cmp.length) return; const L = o.layout[0]; let hi = -Infinity, lo = Infinity, hiI = o.i0, loI = o.i0, sum = 0, k = 0;
      for (let i = o.i0; i <= o.i1; i++) { const v = Y0[i]; if (v == null || !isFinite(v)) continue; if (v > hi) { hi = v; hiI = i; } if (v < lo) { lo = v; loI = i; } sum += v; k++; }
      if (!k) return; const lastV = Y0[o.i1];
      const rows = [['■', (g.px === 'tr' ? 'Rendement total' : 'Dernier cours') + (FXF ? ' (' + ccyT + ')' : ''), fmtP(lastV)], ['⊤', 'Plus haut le ' + dmyShort(S.x[hiI]), fmtP(hi)], ['+', 'Moyenne', num(sum / k, dec + 2)], ['⊥', 'Plus bas le ' + dmyShort(S.x[loI]), fmtP(lo)]];
      MAS.forEach((v, j) => { if (v) { const a = U.sma(Y0, +v)[o.i1]; rows.push(['─', 'MM ' + v, isFinite(a) ? fmtP(a) : '—', MA_COL[j]]); } });
      x.font = '460 12px ' + MONO; x.textBaseline = 'middle'; const w1 = Math.max(...rows.map(r => x.measureText(r[1]).width)), w2 = Math.max(...rows.map(r => x.measureText(r[2]).width)), W = 26 + w1 + 14 + w2 + 10, H = rows.length * 16 + 6;
      x.fillStyle = 'rgba(0,0,0,.82)'; x.fillRect(8, L.top + 6, W, H); x.strokeStyle = '#3d3d3d'; x.strokeRect(8.5, L.top + 6.5, W - 1, H - 1);
      rows.forEach((r, j) => { const yy = L.top + 14 + j * 16; x.fillStyle = r[3] || (j === 0 ? '#ffffff' : '#bfbfbf'); x.textAlign = 'center'; x.fillText(r[0], 20, yy); x.fillStyle = '#e6e6e6'; x.textAlign = 'left'; x.fillText(r[1], 30, yy); x.fillStyle = '#ffffff'; x.textAlign = 'right'; x.fillText(r[2], 30 + w1 + 14 + w2, yy); });
      if (bbg) { const lv = Y0[n - 1], yy = L.Y(lv); if (yy >= L.top && yy <= L.bot) { x.fillStyle = '#ffffff'; x.fillRect(o.W + 1, yy - 8, 62, 16); x.fillStyle = '#000'; x.textAlign = 'left'; x.font = '460 11px ' + MONO; x.fillText(fmtP(lv), o.W + 4, yy); } }
      if (bbg && o.layout[1] && g.volOn && hasVol) { const V = o.layout[1], vv = S.v[o.i1], txt = 'Volume ' + big(vv), t2 = 'Moy. mob. (15) ' + big(U.sma(S.v, 15)[o.i1]); x.font = '460 11.5px ' + MONO; const ww = Math.max(x.measureText(txt).width, x.measureText(t2).width) + 26;
        x.fillStyle = 'rgba(0,0,0,.82)'; x.fillRect(8, V.top + 3, ww, 34); x.strokeStyle = '#3d3d3d'; x.strokeRect(8.5, V.top + 3.5, ww - 1, 33); x.textAlign = 'left'; x.fillStyle = 'rgba(215,215,215,.9)'; x.fillRect(14, V.top + 9, 7, 7); x.fillStyle = '#e6e6e6'; x.fillText(txt, 26, V.top + 13); x.fillStyle = '#ffd200'; x.fillRect(14, V.top + 26, 7, 2); x.fillStyle = '#e6e6e6'; x.fillText(t2, 26, V.top + 28); }
      /* marqueurs : petite étiquette carrée au pied du graphique principal, empilée si plusieurs le même jour */
      const stack = {}; for (const e of EV) { if (e.i < o.i0 || e.i > o.i1) continue; const px = Math.round(o.X(e.i)), lvl = stack[px] = (stack[px] || 0) + 1, yy = L.bot - 4 - lvl * 15;
        x.fillStyle = 'rgba(0,0,0,.85)'; x.fillRect(px - 6, yy, 13, 13); x.strokeStyle = GP_EVC[e.k][0]; x.strokeRect(px - 5.5, yy + .5, 12, 12); x.fillStyle = GP_EVC[e.k][0]; x.font = '700 10px ' + MONO; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(e.k, px + .5, yy + 7); EVPOS.push({ x: px, y: yy, e }); } };
    chart = new TSChart($('gpCv'), { panes, grid: bbg ? 'dot' : null, xticks: bbg ? bbgTicks : null, padR: 66, after, onView: setDates });
    chart.set({ x: S.x, series: ser }, rangeView(g.range));
    const cvEl = $('gpCv'); cvEl.addEventListener('mousemove', e => { if (!EVPOS.length) return; const r = cvEl.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top; const hit = EVPOS.filter(p => Math.abs(p.x - mx) <= 7 && my >= p.y - 1 && my <= p.y + 14);
      if (hit.length) tip(e, hit.map(h => `<b style="color:${GP_EVC[h.e.k][0]}">${h.e.k}</b> ${esc(h.e.t)}`).join('<br>')); else untip(); });
    cvEl.addEventListener('mouseleave', untip);
    const dateIn = () => { const d0 = parseDMY($('gpD0').value), d1 = parseDMY($('gpD1').value); if (!d0 || !d1 || d1 <= d0) { toast('Dates au format jj/mm/aaaa, la fin après le début.'); return; }
      let i0 = S.x.findIndex(d => d >= d0), i1 = S.x.length - 1; for (let i = n - 1; i >= 0; i--) if (S.x[i] <= d1) { i1 = i; break; } if (i0 < 0) i0 = 0; if (i1 - i0 < 3) { toast('Période trop courte.'); return; }
      chart.setView(i0, i1); m.querySelectorAll('[data-gp^="r:"]').forEach(x => x.classList.remove('on')); };
    ['gpD0', 'gpD1'].forEach(id => $(id).onkeydown = e => { if (e.key === 'Enter') dateIn(); }); ['gpD0', 'gpD1'].forEach(id => $(id).onchange = dateIn);
    $('gpRs').onclick = () => { chart.setView(...rangeView(g.range)); }; $('gpZ').onclick = () => { const a = chart.v0, b = chart.v1, mid = (a + b) / 2, half = (b - a) / 4; chart.setView(Math.round(mid - half), Math.round(mid + half)); };
  }
  if (g.tbl || !$('gpKv')) return;
  // statistiques (en devise locale)
  const c = S0r.c, nn = c.length, lr = []; for (let i = Math.max(1, nn - 252); i < nn; i++) lr.push(Math.log(c[i] / c[i - 1]));
  const best = Math.max(...lr), worst = Math.min(...lr), upd = lr.filter(x => x > 0).length / lr.length; const M = !monthly && nn > 210 ? await market(ST.sec) : null; if (!alive()) return;
  let atr = null; if (!monthly && nn > 20) { let a = 0; for (let i = nn - 14; i < nn; i++) a += Math.max(S0r.h[i] - S0r.l[i], Math.abs(S0r.h[i] - c[i - 1]), Math.abs(S0r.l[i] - c[i - 1])); atr = a / 14 / c[nn - 1]; }
  const v3 = S0r.v.slice(-63).reduce((a, b) => a + b, 0) / 63;
  $('gpKv').innerHTML = `<span>Dernier</span><b>${px(s, c[nn - 1])} ${s.ccy}</b><span>Variation</span><b>${pc(s.pct)}</b>
    ${!monthly ? `<span>Ouv. / haut / bas</span><b>${px(s, S0r.o[nn - 1])} / ${px(s, S0r.h[nn - 1])} / ${px(s, S0r.l[nn - 1])}</b>` : ''}
    <span class="h">Performances</span>${!monthly ? `<span>1 semaine</span><b>${pc(s.r1w, 2)}</b>` : ''}<span>1 mois</span><b>${pc(s.r1m, 2)}</b><span>3 mois</span><b>${pc(s.r3m, 2)}</b><span>Depuis le 1er janv.</span><b>${pc(s.ytd, 2)}</b><span>1 an</span><b>${pc(s.r1y, 2)}</b><span>3 ans</span><b>${pc(s.r3y, 1)}</b>
    <span class="h">Risque (1 an)</span><span>Volatilité annualisée</span><b>${num(s.vol * 100, 1)}%</b>${atr ? `<span>ATR 14 / cours</span><b>${num(atr * 100, 2)}%</b>` : ''}<span>Meilleure / pire ${monthly ? 'mois' : 'séance'}</span><b>${sgn(Math.exp(best) - 1, 1)} / ${sgn(Math.exp(worst) - 1, 1)}</b>
    <span>${monthly ? 'Mois' : 'Séances'} en hausse</span><b>${num(upd * 100, 0)}%</b><span>Écart au record</span><b>${pc(s.dd, 1)}</b>${s.beta != null ? `<span>Bêta / corr. ${s.bench}</span><b>${num(s.beta, 2)} / ${num(s.corr, 2)}</b>` : ''}
    ${M ? `<span class="h">Technique</span><span>MM50 · écart</span><b>${px(s, M.sma50[nn - 1])} · ${pc(c[nn - 1] / M.sma50[nn - 1] - 1, 1)}</b><span>MM200 · écart</span><b>${px(s, M.sma200[nn - 1])} · ${pc(c[nn - 1] / M.sma200[nn - 1] - 1, 1)}</b><span>RSI 14</span><b>${num(M.rsi14[nn - 1], 1)}</b>` : ''}
    <span>Plage 52 semaines</span><b>${px(s, s.lo52)} – ${px(s, s.hi52)}</b>${v3 > 0 && hasVol ? `<span>Volume moyen 3 mois</span><b>${big(v3)}</b>` : ''}${s.liq ? `<span>Échanges moyens / j</span><b>${big(s.liq)} ${s.ccy}</b>` : ''}
    <span class="h">Historique</span><span>Première donnée</span><b>${fd(S0r.x[0])}</b><span>Observations</span><b>${num(nn, 0)}</b>`;
  const side = $('gpSide');
  if (s.mkt === 'BRVM' && s.cls === 'Equity') {
    const [dv, ev] = await Promise.all([getJSON('dividends.json'), getJSON('events.json')]); if (!alive()) return;
    const d1 = dv.filter(x => x.t === s.id).sort((a, b) => (b.ex || 0) - (a.ex || 0)).slice(0, 6), e1 = ev.filter(x => x.t === s.id).slice(0, 8);
    side.innerHTML = pn('Dividendes', 'DVD', `<table class="t"><thead><tr><th class="l">Exercice</th><th>Net</th><th>Paiement</th></tr></thead><tbody>${d1.map(x => `<tr><td class="l">${x.ex || '—'}</td><td class="wh">${num(x.dps, 2)}${adjMark(x)}</td><td>${fds(x.pay)}</td></tr>`).join('') || '<tr><td class="l dm" colspan="3">Aucun</td></tr>'}</tbody></table>`, { np: true })
      + pn('Avis récents', 'EVTS', e1.map(e => `<div class="ev" style="grid-template-columns:84px 1fr"><span class="d">${fds(e.d)}</span><span><span class="c">${esc(e.c || '')}</span><a href="${esc(e.u)}" target="_blank" rel="noopener">${esc(e.ti || '')}</a></span></div>`).join('') || '<div class="dm">Aucun avis.</div>');
  }
};

/* ------------------------------------------------------------------ HELP */
/* PAGES.HELP : définition remplacée plus loin (version active dans un fichier suivant) — retirée */
