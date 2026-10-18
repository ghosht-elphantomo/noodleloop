/* ================= FQT — fonctions Bloomberg supplémentaires : WEI, COMMO, taux mondiaux (RATES), MOST, MOV, MEMB, HVT, VAP, ANR, RELS, CACS, GF ================= */
'use strict';
const rangeBar3 = (v, lo, hi) => (v == null || lo == null || hi == null || hi <= lo) ? '' : `<span class="rgb" title="plus bas ${num(lo, 2)} · plus haut ${num(hi, 2)}"><i style="left:${U.clamp((v - lo) / (hi - lo) * 100, 0, 100).toFixed(1)}%"></i></span>`;
const qTime = t => { if (!t) return '—'; if (String(t).length === 10) return String(t).slice(8, 10) + '/' + String(t).slice(5, 7); const d = new Date(t); if (isNaN(d)) return esc(t); return Date.now() - d < 20 * 3600e3 ? d.toLocaleTimeString('fr-FR', { timeZone: 'Africa/Abidjan', hour: '2-digit', minute: '2-digit' }) : d.toLocaleDateString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit' }); };
const ctr = n => (n || '').match(/\(([^)]+)\)\s*$/) ? (n.match(/\(([^)]+)\)\s*$/)[1]) : '';
const WMKT = () => getJSON('world_mkt.json').catch(() => null);
/* derniers chiffres FRED et courbe du Trésor (sans les historiques : 100 Ko au lieu de 1,8 Mo) */
const ecoLite = () => getJSON('eco_lite.json').catch(() => getJSON('eco.json'));
/* paires cotées « devise / USD » (dollars pour une unité) ; toutes les autres sont cotées « USD / devise » */
const FX_INV = new Set(['EUR=', 'GBP=', 'AUD=', 'NZD=']);

/* ------------------------------------------------------------------ WEI : indices boursiers mondiaux */
const IDX_FR = { '.SPX': 'S&P 500', '.DJI': 'Dow Jones Industrial', '.IXIC': 'Nasdaq Composite', '.RUT': 'Russell 2000', '.GSPTSE': 'S&P/TSX (Canada)', '.MXX': 'S&P/BMV IPC (Mexique)', '.BVSP': 'Bovespa (Brésil)', '.MERV': 'Merval (Argentine)',
  '.STOXX50E': 'Euro Stoxx 50', '.FTSE': 'FTSE 100 (R.-U.)', '.GDAXI': 'DAX (Allemagne)', '.FCHI': 'CAC 40 (France)', '.FTMIB': 'FTSE MIB (Italie)', '.IBEX': 'IBEX 35 (Espagne)', '.AEX': 'AEX (Pays-Bas)', '.SSMI': 'SMI (Suisse)', '.OMXS30': 'OMX Stockholm 30',
  '.TA35': 'TA-35 (Israël)', '.EGX30': 'EGX 30 (Égypte)', '.N225': 'Nikkei 225 (Japon)', '.HSI': 'Hang Seng (Hong Kong)', '.SSEC': 'Shanghai Composite', '.SZI': 'Shenzhen Component', '.KS11': 'KOSPI (Corée)', '.TWII': 'TAIEX (Taïwan)',
  '.NSEI': 'Nifty 50 (Inde)', '.AXJO': 'S&P/ASX 200 (Australie)', '.STI': 'Straits Times (Singapour)', '.KLSE': 'FTSE Bursa KLCI (Malaisie)', '.VIX': 'VIX (volatilité S&P 500)' };
PAGES.INDX = async (m, alive) => {
  const it = tabState('INDX', 'i'); setTabs(FN_TABS.INDX, it, k => { ST.tab.INDX = k; render(); });
  if (it === 'f') return PAGES.WEIF(m, alive);
  const W = await WMKT(); if (!alive()) return; setTitle('World Equity Indices');
  if (!W || !W.idx) { m.innerHTML = pn('Indices mondiaux', 'INDX', '<div class="empty">Cotations mondiales en attente du prochain relevé (toutes les 15 minutes).</div>'); return; }
  const tab = tabState('WEI', 'tbl'), wo = ST.weio = ST.weio || { mov: false, vol: true };
  /* rangée de réglages comme le terminal : vue « Standard ▾ », cases Movers / Volatilité */
  const ctl = `<div class="tools weic"><select class="ofld" id="weV">${[['tbl', 'Standard'], ['bar', 'Variations du jour'], ['rng', 'Position sur 52 semaines']].map(([k, l]) => `<option value="${k}" ${tab === k ? 'selected' : ''}>${l}</option>`).join('')}</select>
    <label class="gck"><input type="checkbox" id="weM" ${wo.mov ? 'checked' : ''}><i></i>Mouvements (classés par variation)</label><label class="gck"><input type="checkbox" id="weVo" ${wo.vol ? 'checked' : ''}><i></i>Volatilité</label>
    <span class="gsp"></span><span class="tlab">% depuis janv.</span><span class="wh">devise locale et USD</span></div>`;
  const bindCtl = () => { $('weV').onchange = e => { ST.tab.WEI = e.target.value; render(); }; $('weM').onchange = e => { wo.mov = e.target.checked; render(); }; $('weVo').onchange = e => { wo.vol = e.target.checked; render(); }; };
  const brvm = ['BRVMC', 'BRVM30', 'BRVMPR'].map(id => Q.by[id]).filter(Boolean).map(s => ({ g: 'MEA', s: s.id, n: s.n, last: s.last, chg: s.prev ? s.last - s.prev : null, pct: s.pct, t: i2s(s.dt), hi52: s.hi52, lo52: s.lo52, ytd: s.ytd, loc: true }));
  const YB = W.yb && W.yb.v || {}; W.idx.forEach(r => { if (r.ytd == null && YB[r.s] && r.last) r.ytd = r.last / YB[r.s] - 1; });
  const rows = W.idx.concat(brvm), REG = [['AM', 'Amériques'], ['EU', 'Europe'], ['MEA', 'Moyen-Orient et Afrique'], ['AS', 'Asie-Pacifique']].concat(wo.vol ? [['VOL', 'Volatilité']] : []);
  const nm = r => r.loc ? r.n : IDX_FR[r.s] || r.n;
  if (tab === 'bar') {
    const L = rows.filter(r => r.g !== 'VOL' && r.pct != null).sort((a, b) => b.pct - a.pct);
    m.innerHTML = ctl + pn(`Indices mondiaux classés par variation du jour (${L.length})`, 'INDX', cvb('weB', Math.max(380, L.length * 17)), { lect: `Cotations différées, relevé ${new Date(W.ts * 1000).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}. Les marchés d’Asie et d’Europe affichent leur dernière séance close.` });
    bindCtl(); hbars($('weB'), L.map(r => nm(r)), L.map(r => r.pct * 100), v => (v > 0 ? '+' : '') + num(v, 2) + '%'); return;
  }
  /* % depuis janvier en dollars (colonne « %YtdCur » du terminal) : indices cotés en EUR, GBP, CHF, JPY, CNY, XOF */
  const FXR = Object.fromEntries((W.fx || []).map(r => [r.s, r.last])), IXC = { '.STOXX50E': 'EUR=', '.GDAXI': 'EUR=', '.FCHI': 'EUR=', '.FTMIB': 'EUR=', '.IBEX': 'EUR=', '.AEX': 'EUR=', '.FTSE': 'GBP=', '.SSMI': 'CHF=', '.N225': 'JPY=', '.SSEC': 'CNY=', '.SZI': 'CNY=', BRVMC: 'XOF=', BRVM30: 'XOF=', BRVMPR: 'XOF=',
    '.GSPTSE': 'CAD=', '.MXX': 'MXN=', '.BVSP': 'BRL=', '.MERV': 'ARS=', '.OMXS30': 'SEK=', '.TA35': 'ILS=', '.EGX30': 'EGP=', '.HSI': 'HKD=', '.KS11': 'KRW=', '.TWII': 'TWD=', '.NSEI': 'INR=', '.AXJO': 'AUD=', '.STI': 'SGD=', '.KLSE': 'MYR=' };
  const usdF = r => { const US = ['.SPX', '.DJI', '.IXIC', '.RUT']; if (US.includes(r.s)) return 1; let f = IXC[r.s]; if (f === 'XOF=' && FXR['EUR='] && YB['EUR=']) f = 'EUR='; /* FCFA : parité fixe avec l'euro */ if (!f || !FXR[f] || !YB[f]) return null; return FX_INV.has(f) ? FXR[f] / YB[f] : YB[f] / FXR[f]; };
  const today = new Date().toISOString().slice(0, 10), stale = t => t && String(t).slice(0, 10) < today;
  let rn = 0; const sec_ = ([g, lab], gi) => { const L = rows.filter(r => r.g === g); if (wo.mov) L.sort((a, b) => (b.pct ?? -9) - (a.pct ?? -9)); if (!L.length) return '';
    return `<tr class="grp"><td class="l" colspan="8"><span class="rn">${gi + 1})</span>${lab}</td></tr>${L.map(r => { const f = r.ytd != null ? usdF(r) : null, yc = f != null ? (1 + r.ytd) * f - 1 : null;
      return `<tr ${r.loc ? `data-sec="${r.s}" data-to="GP" style="cursor:pointer"` : ''}><td class="l am"><span class="rn">${++rn})</span>${esc(nm(r).toUpperCase())}</td><td class="wh">${num(r.last, 2)}<i class="qd">${r.loc ? '' : 'd'}</i></td><td class="${cls(r.chg)}">${r.chg != null ? (r.chg > 0 ? '+' : '') + num(r.chg, 2) : '—'}</td><td>${pc(r.pct)}</td><td class="dm">${qTime(r.t)}<i class="qd">${stale(r.t) ? 'c' : ''}</i></td><td>${r.ytd != null ? pc(r.ytd) : '<span class="dm">—</span>'}</td><td>${yc != null ? pc(yc) : '<span class="dm">—</span>'}</td><td>${rangeBar3(r.last, r.lo52, r.hi52)}</td></tr>`; }).join('')}`; };
  if (tab === 'rng') {
    const L = rows.filter(r => r.hi52 && r.lo52 && r.hi52 > r.lo52 && r.g !== 'VOL').map(r => ({ r, p: (r.last - r.lo52) / (r.hi52 - r.lo52) })).sort((a, b) => b.p - a.p);
    m.innerHTML = ctl + pn('Position dans la fourchette des 52 dernières semaines (0 % = plus bas, 100 % = plus haut)', 'INDX', cvb('weR', Math.max(380, L.length * 17)), { lect: 'Les indices en haut de la liste sont au voisinage de leur plus haut annuel.' });
    bindCtl(); hbars($('weR'), L.map(x => nm(x.r)), L.map(x => x.p * 100), v => num(v, 0) + ' %', 50); return;
  }
  m.innerHTML = ctl + `${pn('Indices boursiers mondiaux', 'INDX', `<div class="tw"><table class="t wei"><thead><tr><th class="l">Indice</th><th>Valeur</th><th>Var. nette</th><th>Var. %</th><th>Heure</th><th>% depuis janv.</th><th>% janv. (USD)</th><th>Fourchette 52 s.</th></tr></thead><tbody>${REG.map(sec_).join('')}</tbody></table></div>`,
    { np: true, lect: `Cotations différées, relevé ${new Date(W.ts * 1000).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })} ; BRVM : séance du jour. d = cotation différée ; heure GMT de la dernière cotation, c = clôture d’une séance précédente (date) : la variation affichée est alors celle de cette séance, calculée contre la clôture d’avant. « % depuis janv. » = dernier cours ÷ clôture de fin d’année précédente ; « (USD) » = même calcul converti en dollars.` })}`;
  bindCtl();
};
/* barres horizontales (classements) */
function hbars(host, labels, values, fmt, mid = 0) {
  const { x, w, h } = setupCanvas(host); const n = values.length; if (!n) return; const padL = Math.min(260, Math.max(...labels.map(l => l.length)) * 7.2 + 10), padR = 70, rowH = (h - 10) / n;
  let lo = Math.min(mid, ...values), hi = Math.max(mid, ...values); if (lo === hi) hi = lo + 1; const X = v => padL + (v - lo) / (hi - lo) * (w - padL - padR);
  x.font = FUI; x.textBaseline = 'middle';
  values.forEach((v, i) => { const y = 5 + i * rowH, x0 = X(mid), x1 = X(v); x.fillStyle = v >= mid ? 'rgba(47,210,106,.85)' : 'rgba(255,61,77,.85)'; x.fillRect(Math.min(x0, x1), y + rowH * .18, Math.abs(x1 - x0) || 1, rowH * .64);
    x.fillStyle = '#f9a33a'; x.textAlign = 'right'; x.fillText(labels[i], padL - 6, y + rowH / 2); x.fillStyle = '#e6e6e6'; x.textAlign = v >= mid ? 'left' : 'right'; x.fillText(fmt(v), v >= mid ? x1 + 4 : x1 - 4, y + rowH / 2); });
  x.strokeStyle = 'rgba(200,200,200,.5)'; x.beginPath(); x.moveTo(Math.round(X(mid)) + .5, 4); x.lineTo(Math.round(X(mid)) + .5, h - 4); x.stroke();
}

/* ------------------------------------------------------------------ COMMO (ex-GLCO) : matières premières mondiales */
const CMD_U = { '@GC.1': '$/once', '@SI.1': '$/once', '@HG.1': '$/livre', '@PL.1': '$/once', '@PA.1': '$/once', '@CC.1': '$/tonne', '@KC.1': '¢/livre', '@CT.1': '¢/livre', '@SB.1': '¢/livre', '@W.1': '¢/boisseau', '@C.1': '¢/boisseau', '@S.1': '¢/boisseau', '@SM.1': '$/tonne courte', '@LC.1': '¢/livre',
  '@LCO.1': '$/baril', '@CL.1': '$/baril', '@NG.1': '$/MMBtu', '@RB.1': '$/gallon', '@HO.1': '$/gallon' };
const CMD_FR = { '@GC.1': 'Or (COMEX)', '@SI.1': 'Argent (COMEX)', '@HG.1': 'Cuivre (COMEX)', '@PL.1': 'Platine (NYMEX)', '@PA.1': 'Palladium (NYMEX)', '@CC.1': 'Cacao (ICE New York)', '@KC.1': 'Café arabica (ICE)', '@CT.1': 'Coton (ICE)', '@SB.1': 'Sucre n° 11 (ICE)',
  '@W.1': 'Blé (CBOT)', '@C.1': 'Maïs (CBOT)', '@S.1': 'Soja (CBOT)', '@SM.1': 'Tourteau de soja (CBOT)', '@LC.1': 'Bovins vivants (CME)', '@LCO.1': 'Pétrole Brent (ICE)', '@CL.1': 'Pétrole WTI (NYMEX)', '@NG.1': 'Gaz naturel Henry Hub (NYMEX)', '@RB.1': 'Essence RBOB (NYMEX)', '@HO.1': 'Gazole ULSD (NYMEX)' };
PAGES.COMMO = async (m, alive) => {
  const [W, O] = await Promise.all([WMKT(), getJSON('oil.json').catch(() => null)]); if (!alive()) return; setTitle('Global Commodity Prices');
  if (!W || !W.cmd) { m.innerHTML = pn('Matières premières', 'COMMO', '<div class="empty">Cotations en attente du prochain relevé (toutes les 15 minutes).</div>'); return; }
  const en = O ? [['@LCO.1', O.curve.BRENT && O.curve.BRENT[0]], ['@CL.1', O.curve.WTI && O.curve.WTI[0]], ['@NG.1', O.prod['@NG.1']], ['@RB.1', O.prod['@RB.1']], ['@HO.1', O.prod['@HO.1']]].filter(x => x[1]).map(([s_, r]) => ({ ...r, s: s_, g: 'EN' })) : [];
  const rows = en.concat(W.cmd.filter(r => r.g === 'MET' || r.g === 'AGR')); const G = [['EN', 'Énergie'], ['MET', 'Métaux'], ['AGR', 'Agriculture et élevage']];
  const tbl = `<table class="t"><thead><tr><th class="l">Contrat</th><th class="l">Échéance</th><th>Dernier</th><th>Var. nette</th><th>Var. %</th><th class="l">Unité</th><th>Fourchette 52 s.</th><th>Heure GMT</th></tr></thead><tbody>${G.map(([g, lab]) => { const L = rows.filter(r => r.g === g); return L.length ? `<tr class="grp"><td class="l" colspan="8">${lab}</td></tr>${L.map(r => `<tr${['@CC.1', '@KC.1', '@CT.1'].includes(r.s) ? ' class="hl"' : ''}><td class="l am">${esc(CMD_FR[r.s] || r.n)}</td><td class="l dm">${esc(ctr(r.n))}</td><td class="wh">${num(r.last, r.last < 10 ? 4 : 2)}</td><td class="${cls(r.chg)}">${r.chg != null ? (r.chg > 0 ? '+' : '') + num(r.chg, r.last < 10 ? 4 : 2) : '—'}</td><td>${pc(r.pct)}</td><td class="l dm">${CMD_U[r.s] || ''}</td><td>${rangeBar3(r.last, r.lo52, r.hi52)}</td><td class="dm">${qTime(r.t)}</td></tr>`).join('')}` : ''; }).join('')}</tbody></table>`;
  const L = rows.filter(r => r.pct != null).sort((a, b) => b.pct - a.pct);
  m.innerHTML = `<div class="grid side">${pn('Matières premières mondiales : contrats à terme 1er mois', 'COMMO', tbl, { np: true, lect: `Cotations différées, relevé ${new Date(W.ts * 1000).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}. En surbrillance : cacao, café et coton, premières exportations agricoles de l’UEMOA (la Côte d’Ivoire est le 1er producteur mondial de cacao). Pétrole en détail : BMAP.` })}
    ${pn('Classement du jour', 'COMMO', cvb('glB', Math.max(320, L.length * 18)))}</div>`;
  hbars($('glB'), L.map(r => (CMD_FR[r.s] || r.n).replace(/ \(.*\)$/, '')), L.map(r => r.pct * 100), v => (v > 0 ? '+' : '') + num(v, 2) + '%');
};

/* ------------------------------------------------------------------ taux souverains mondiaux : BONDS, onglet 3 de RATES (ex-WB) */
async function wbView(m, alive) {
  const [W, C] = await Promise.all([WMKT(), getJSON('umoa_curves.json').catch(() => null)]); if (!alive()) return; setTitle('World Bond Markets');
  if (!W || !W.rt) { m.innerHTML = pn('Taux souverains', 'RATES', '<div class="empty">Taux en attente du prochain relevé.</div>'); return; }
  const us = W.rt.filter(r => r.g === 'US'), g10 = W.rt.filter(r => r.g === 'G'), mat = s_ => { const x = s_.match(/US(\d+)([MY])/); return x ? +x[1] / (x[2] === 'M' ? 12 : 1) : null; };
  const nmG = { 'DE10Y-DE': 'Allemagne', 'FR10Y-FR': 'France', 'GB10Y-GB': 'Royaume-Uni', 'IT10Y-IT': 'Italie', 'ES10Y-ES': 'Espagne', 'JP10Y-JP': 'Japon', 'CN10Y-CN': 'Chine' };
  const de = g10.find(r => r.s === 'DE10Y-DE');
  const bp = r => r.chg != null ? `<span class="${cls(r.chg)}">${r.chg > 0 ? '+' : ''}${num(r.chg * 100, 1)} pb</span>` : '—';
  let cur = null, uem = []; if (C && C.curves) { const ds = Object.keys(C.curves).sort(), c = C.curves[ds[ds.length - 1]]; cur = c; for (const [cty, pts] of Object.entries(c.c)) { const p = pts.find(q => q[1] === 10) || pts.filter(q => q[1] <= 10).slice(-1)[0]; if (p) uem.push([ctyName(cty), p[1], p[3]]); } }
  m.innerHTML = `<div class="grid c2">${pn('Courbe des taux du Trésor américain', 'RATES', cvb('wbU', 280), { lect: `Rendements des emprunts d’État américains (cotation différée), relevé à ${us.length ? qTime(us[us.length - 1].t) : '—'}. pb = points de base (0,01 %).` })}
    ${pn('Trésor américain', 'RATES', `<table class="t"><thead><tr><th class="l">Maturité</th><th>Rendement</th><th>Var.</th><th>Fourchette 52 s.</th></tr></thead><tbody>${us.map(r => `<tr><td class="l am">${(() => { const mm = String(r.s).match(/^US(\d+)([MY])$/); return mm ? `${mm[1]} ${mm[2] === 'M' ? 'mois' : +mm[1] > 1 ? 'ans' : 'an'}` : esc(r.n); })()}</td><td class="wh">${num(r.last, 3)} %</td><td>${bp(r)}</td><td>${rangeBar3(r.last, r.lo52, r.hi52)}</td></tr>`).join('')}
      ${(() => { const a = us.find(r => r.s === 'US2Y'), b = us.find(r => r.s === 'US10Y'), c3 = us.find(r => r.s === 'US3M'); return (a && b ? `<tr class="sep2"><td class="l">Pente 10 ans − 2 ans</td><td class="wh">${num((b.last - a.last) * 100, 0)} pb</td><td></td><td></td></tr>` : '') + (c3 && b ? `<tr><td class="l">Pente 10 ans − 3 mois</td><td class="wh">${num((b.last - c3.last) * 100, 0)} pb</td><td></td><td></td></tr>` : ''); })()}</tbody></table>`, { np: true })}</div>
    <div class="grid c2">${pn('Emprunts d’État à 10 ans', 'RATES', `<table class="t"><thead><tr><th class="l">Pays</th><th>Rendement</th><th>Var.</th><th>Écart vs Allemagne</th><th>Fourchette 52 s.</th></tr></thead><tbody>${[us.find(r => r.s === 'US10Y')].filter(Boolean).concat(g10).map(r => `<tr><td class="l am">${esc(nmG[r.s] || 'États-Unis')}</td><td class="wh">${num(r.last, 3)} %</td><td>${bp(r)}</td><td>${de && r.s !== 'DE10Y-DE' ? num((r.last - de.last) * 100, 0) + ' pb' : '—'}</td><td>${rangeBar3(r.last, r.lo52, r.hi52)}</td></tr>`).join('')}</tbody></table>`, { np: true })}
    ${uem.length ? pn(`UEMOA : taux à 10 ans (courbes souveraines au ${esc(cur.asof || '')})`, 'GC', `<table class="t"><thead><tr><th class="l">État</th><th>Maturité</th><th>Taux</th><th>Écart vs Trésor US 10 ans</th></tr></thead><tbody>${uem.sort((a, b) => b[2] - a[2]).map(([c, mt, v]) => { const u10 = us.find(r => r.s === 'US10Y'); return `<tr data-fn="GC" style="cursor:pointer"><td class="l am">${esc(c)}</td><td>${mt} ans</td><td class="wh">${num(v * 100, 2)} %</td><td>${u10 ? num((v * 100 - u10.last) * 100, 0) + ' pb' : '—'}</td></tr>`; }).join('')}</tbody></table>`, { np: true, lect: 'Taux après lissage des courbes souveraines (marché régional, en FCFA). Détail : GC.' }) : ''}</div>`;
  const pts = us.map(r => [mat(r.s), r.last / 100]).filter(p => p[0]);
  if (pts.length) gcDraw($('wbU'), [{ lab: 'Trésor US', col: '#f9a33a', pts, w: 2 }]);
}

/* ------------------------------------------------------------------ MOST : valeurs les plus actives, hausses, baisses */
/* PAGES.MOST : définition remplacée plus loin (version active dans un fichier suivant) — retirée */

/* ------------------------------------------------------------------ MEMB / MOV : composition et contributions d'un indice */
const IDX_MEMBERS = { BRVMC: () => secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity' && s.mcap), QQQ: () => secsWhere(s => s.mkt === 'US' && s.ndx && s.mcap), NDX: () => secsWhere(s => s.mkt === 'US' && s.ndx && s.mcap) };
function idxContrib(s) {
  const mem = IDX_MEMBERS[s.id](); const prevCap = x => x.mcap / (1 + (x.pct || 0)); const tot = mem.reduce((a, x) => a + prevCap(x), 0), tot1 = mem.reduce((a, x) => a + x.mcap, 0);
  const iPrev = s.prev || s.last / (1 + (s.pct || 0));
  return { mem: mem.map(x => ({ s: x, w: x.mcap / tot1, c: iPrev * prevCap(x) / tot * (x.pct || 0) })), est: tot1 / tot - 1, act: s.pct, iPrev };
}
PAGES.MEMB = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Member Weightings'); const R = idxContrib(s); const L = R.mem.sort((a, b) => b.w - a.w);
  m.innerHTML = `<div class="grid side">${pn(`${esc(ykey(s))} · composition (${L.length} valeurs)`, 'MEMB', `<div class="tw" style="max-height:72vh"><table class="t"><thead><tr><th class="l">#</th><th class="l">Titre</th><th class="l">Nom</th><th>Poids</th><th>Cours</th><th>Var. %</th><th>Contribution (pts)</th><th>Capitalisation</th></tr></thead><tbody>${L.map((x, i) => `<tr data-sec="${x.s.id}" data-to="DES" style="cursor:pointer"><td class="l dm">${i + 1}</td><td class="l tk">${x.s.id}</td><td class="l nm">${esc(x.s.short || x.s.n)}</td><td class="wh">${num(x.w * 100, 2)} %</td><td>${px(x.s, x.s.last)}</td><td>${pc(x.s.pct)}</td><td class="${cls(x.c)}">${x.c > 0 ? '+' : ''}${num(x.c, 2)}</td><td>${big(x.s.mcap)}</td></tr>`).join('')}</tbody></table></div>`,
      { np: true, lect: `Poids estimés au prorata des capitalisations boursières ${s.id === 'BRVMC' ? '(le BRVM Composite pondère toutes les actions cotées par leur capitalisation)' : '(le Nasdaq-100 utilise une pondération modifiée : poids réels légèrement différents)'}.` })}
    ${pn('Concentration', 'MEMB', `<div class="kv2"><span>Premier poids</span><b>${esc(L[0].s.short || L[0].s.id)} ${num(L[0].w * 100, 1)} %</b><span>5 premiers</span><b>${num(L.slice(0, 5).reduce((a, x) => a + x.w, 0) * 100, 1)} %</b><span>10 premiers</span><b>${num(L.slice(0, 10).reduce((a, x) => a + x.w, 0) * 100, 1)} %</b><span>Nombre effectif de valeurs (1/Σw²)</span><b>${num(1 / L.reduce((a, x) => a + x.w * x.w, 0), 1)}</b></div>${cvb('mbW', 300)}`)}</div>`;
  const top = L.slice(0, 15); barChart($('mbW'), { labels: top.map(x => x.s.id), values: top.map(x => x.w * 100), fmt: v => num(v, 1) + '%', labelsOnBars: true, pos: '#f9a33a', padB: 22 });
};
PAGES.MOV = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Equity Index Movers'); const R = idxContrib(s); const pos = R.mem.filter(x => x.c > 0).sort((a, b) => b.c - a.c).slice(0, 12), neg = R.mem.filter(x => x.c < 0).sort((a, b) => a.c - b.c).slice(0, 12);
  const tot = R.mem.reduce((a, x) => a + x.c, 0);
  const t = (title, L) => pn(title, 'MOV', `<table class="t"><thead><tr><th class="l">Titre</th><th class="l">Nom</th><th>Var. %</th><th>Poids</th><th>Contribution (pts)</th></tr></thead><tbody>${L.map(x => `<tr data-sec="${x.s.id}" data-to="GP" style="cursor:pointer"><td class="l tk">${x.s.id}</td><td class="l nm">${esc(x.s.short || x.s.n)}</td><td>${pc(x.s.pct)}</td><td>${num(x.w * 100, 2)} %</td><td class="${cls(x.c)}">${x.c > 0 ? '+' : ''}${num(x.c, 2)}</td></tr>`).join('') || '<tr><td class="l dm" colspan="5">Aucun.</td></tr>'}</tbody></table>`, { np: true });
  m.innerHTML = `${pn(`${esc(ykey(s))} · ${num(s.last, 2)} (${pc(s.pct)}) · variation expliquée par les valeurs`, 'MOV', cvb('mvB', 300), { lect: `Contribution de chaque valeur = niveau de la veille × poids de la veille × variation du titre, en points d’indice (poids estimés par les capitalisations). Somme des contributions : <b>${tot > 0 ? '+' : ''}${num(tot, 2)} pts</b>, contre une variation publiée de <b>${s.prev ? (s.last - s.prev > 0 ? '+' : '') + num(s.last - s.prev, 2) : '—'} pts</b>.` })}
    <div class="grid c2">${t('Contributions positives', pos)}${t('Contributions négatives', neg)}</div>`;
  const L = pos.slice(0, 10).concat(neg.slice(0, 10).reverse()); hbars($('mvB'), L.map(x => `${x.s.id} ${num(x.s.pct * 100, 2)}%`), L.map(x => x.c), v => (v > 0 ? '+' : '') + num(v, 2));
};

/* ------------------------------------------------------------------ HVT : volatilité historique */
PAGES.HVT = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Historical Volatility Table'); const S = await series(s.id); if (!alive()) return;
  const ann = s.mkt === 'CRYPTO' ? 365 : 252, c = S.c, lr = c.map((v, i) => i && c[i - 1] > 0 && v > 0 ? Math.log(v / c[i - 1]) : null);
  const vol = (n, end = c.length) => { const a = lr.slice(Math.max(1, end - n), end).filter(x => x != null); if (a.length < n * .6) return null; const mu = U.mean(a); return Math.sqrt(a.reduce((t, x) => t + (x - mu) ** 2, 0) / (a.length - 1) * ann); };
  const park = n => { const a = []; for (let i = Math.max(0, c.length - n); i < c.length; i++) if (S.h[i] > 0 && S.l[i] > 0 && S.h[i] > S.l[i]) a.push(Math.log(S.h[i] / S.l[i]) ** 2); return a.length > n * .6 ? Math.sqrt(a.reduce((t, x) => t + x, 0) / (4 * Math.log(2) * a.length) * ann) : null; };
  const W = [10, 20, 30, 60, 90, 120, 180, 260]; const roll = n => { const out = new Array(c.length).fill(null); let s1 = 0, s2 = 0, k = 0; const q = [];
    for (let i = 1; i < c.length; i++) { const x = lr[i]; q.push(x); if (x != null) { s1 += x; s2 += x * x; k++; } if (q.length > n) { const o = q.shift(); if (o != null) { s1 -= o; s2 -= o * o; k--; } } if (q.length === n && k > n * .6) out[i] = Math.sqrt(Math.max(0, (s2 - s1 * s1 / k) / (k - 1)) * ann); } return out; };
  const R20 = roll(20), R60 = roll(60), R260 = roll(260); const hist = R20.filter(x => x != null), pctl = v => v == null ? null : hist.filter(x => x <= v).length / hist.length;
  const rows = W.map(n => { const v = vol(n), r = roll(n).filter(x => x != null); return { n, v, p: park(n), mn: r.length ? Math.min(...r) : null, mx: r.length ? Math.max(...r) : null, pc_: v != null && r.length ? r.filter(x => x <= v).length / r.length : null }; });
  m.innerHTML = `<div class="grid c2">${pn(`${esc(ykey(s))} · volatilité historique annualisée`, 'HVT', `<table class="t"><thead><tr><th class="l">Fenêtre</th><th>Clôture à clôture</th><th>Parkinson (haut-bas)</th><th>Minimum historique</th><th>Maximum historique</th><th>Centile actuel</th></tr></thead><tbody>${rows.map(r => `<tr><td class="l am">${r.n} séances</td><td class="wh">${r.v != null ? num(r.v * 100, 1) + ' %' : '—'}</td><td>${r.p != null ? num(r.p * 100, 1) + ' %' : '—'}</td><td>${r.mn != null ? num(r.mn * 100, 1) + ' %' : '—'}</td><td>${r.mx != null ? num(r.mx * 100, 1) + ' %' : '—'}</td><td>${r.pc_ != null ? num(r.pc_ * 100, 0) + ' %' : '—'}</td></tr>`).join('')}</tbody></table>`,
      { np: true, lect: `Écart-type des rendements logarithmiques quotidiens × √${ann}. Parkinson utilise l’écart entre plus haut et plus bas du jour (plus précis si ces données sont fiables). Centile = position de la volatilité actuelle dans tout l’historique de la même fenêtre${s.mkt === 'BRVM' ? ' ; à la BRVM, les séances sans échange réduisent la volatilité mesurée' : ''}.` })}
    ${pn('Lecture', 'HVT', `<div class="lectb"><p>Volatilité sur 20 séances : <b>${R20[R20.length - 1] != null ? num(R20[R20.length - 1] * 100, 1) + ' %' : '—'}</b>, au ${num((pctl(R20[R20.length - 1]) || 0) * 100, 0)}e centile de son historique depuis ${fd(S.x[0])}.</p><p>Variation quotidienne « normale » (1 écart-type) : ±${R20[R20.length - 1] != null ? num(R20[R20.length - 1] / Math.sqrt(ann) * 100, 2) : '—'} %, soit environ ±${R20[R20.length - 1] != null ? px(s, s.last * R20[R20.length - 1] / Math.sqrt(ann)) : '—'} ${esc(s.ccy || '')} par séance.</p></div>`)}</div>
    ${pn('Volatilité glissante (20, 60 et 260 séances)', 'HVT', cvb('hvG', 300))}`;
  const k0 = Math.max(0, c.length - 1300), X = S.x.slice(k0);
  new TSChart($('hvG'), { panes: [{ h: 1, fmt: v => num(v * 100, 0) + '%' }], grid: 'dot', xticks: bbgTicks }).set({ x: X, series: [{ y: R20.slice(k0), color: '#f9a33a', w: 1.2, label: '20 séances', fmt: v => num(v * 100, 1) + '%' }, { y: R60.slice(k0), color: '#5fd0ea', w: 1.4, label: '60 séances', fmt: v => num(v * 100, 1) + '%' }, { y: R260.slice(k0), color: '#ffffff', w: 1.6, label: '260 séances', fmt: v => num(v * 100, 1) + '%' }] }, [0, X.length - 1]);
};

/* ------------------------------------------------------------------ VAP : volume par niveau de prix */
PAGES.VAP = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Volume at Price'); const S = await series(s.id); if (!alive()) return; const st = ST.vap = ST.vap || { p: 126 };
  setTabs([['21', '1 mois'], ['63', '3 mois'], ['126', '6 mois'], ['252', '1 an'], ['756', '3 ans']], String(st.p), k => { st.p = +k; render(); });
  const n = S.c.length, k0 = Math.max(0, n - st.p), useVal = !!(S.val && S.val.some(v => v > 0)); const C = S.c.slice(k0), V = (useVal ? S.val : S.v).slice(k0);
  if (!V.some(v => v > 0)) { m.innerHTML = pn('Volume par niveau de prix', 'VAP', '<div class="empty">Pas de volumes publiés pour ce titre.</div>'); return; }
  const lo = Math.min(...C), hi = Math.max(...C), B = 28, step = (hi - lo) / B || 1, bins = new Array(B).fill(0);
  C.forEach((p, i) => { const b = Math.min(B - 1, Math.floor((p - lo) / step)); bins[b] += V[i] || 0; });
  const tot = bins.reduce((a, b) => a + b, 0), poc = bins.indexOf(Math.max(...bins)), vwap = C.reduce((a, p, i) => a + p * (V[i] || 0), 0) / (V.reduce((a, v) => a + (v || 0), 0) || 1);
  let lo_i = poc, hi_i = poc, acc = bins[poc]; while (acc < tot * .7 && (lo_i > 0 || hi_i < B - 1)) { const a = lo_i > 0 ? bins[lo_i - 1] : -1, b = hi_i < B - 1 ? bins[hi_i + 1] : -1; if (b >= a) { hi_i++; acc += bins[hi_i]; } else { lo_i--; acc += bins[lo_i]; } }
  const mid = i => lo + (i + .5) * step;
  m.innerHTML = `<div class="grid side">${pn(`${esc(ykey(s))} · ${useVal ? 'montants échangés' : 'volumes'} par niveau de prix, ${st.p} dernières séances`, 'VAP', cvb('vpC', 520))}
    ${pn('Repères', 'VAP', `<div class="kv2"><span>Dernier cours</span><b>${px(s, s.last)}</b><span>Prix le plus échangé (POC)</span><b class="am">${px(s, mid(poc))}</b><span>Zone de valeur (70 % des échanges)</span><b>${px(s, lo + lo_i * step)} – ${px(s, lo + (hi_i + 1) * step)}</b><span>Prix moyen pondéré (VWAP)</span><b>${px(s, vwap)}</b><span>Écart au VWAP</span><b>${pc(s.last / vwap - 1, 1)}</b><span>Total ${useVal ? 'échangé' : 'volume'}</span><b>${big(tot)}${useVal ? ' ' + esc(s.ccy || '') : ''}</b></div>`, { lect: 'Barres = quantité échangée à chaque niveau de cours (cours de clôture de chaque séance). Les niveaux très échangés agissent souvent comme supports ou résistances.' })}</div>`;
  const { x, w, h } = setupCanvas($('vpC')); const padL = 70, padR = 10, rowH = (h - 10) / B, mx = Math.max(...bins);
  for (let i = 0; i < B; i++) { const y = h - 5 - (i + 1) * rowH, bw = (w - padL - padR) * bins[i] / mx; x.fillStyle = i === poc ? '#f9a33a' : i >= lo_i && i <= hi_i ? 'rgba(61,124,201,.95)' : 'rgba(61,124,201,.45)'; x.fillRect(padL, y + 1, bw, rowH - 2);
    if (i % 2 === 0) { x.fillStyle = '#ddd'; x.font = FNUM; x.textAlign = 'right'; x.textBaseline = 'middle'; x.fillText(num(mid(i), pxd(s)), padL - 6, y + rowH / 2); } }
  const yP = p => h - 5 - (p - lo) / (hi - lo || 1) * (h - 10); [[s.last, '#ffffff', 'Dernier'], [vwap, '#2fd26a', 'VWAP']].forEach(([p, col, lab]) => { const yy = yP(p); x.strokeStyle = col; x.setLineDash([4, 3]); x.beginPath(); x.moveTo(padL, yy); x.lineTo(w - padR, yy); x.stroke(); x.setLineDash([]); x.fillStyle = col; x.textAlign = 'right'; x.font = FUI; x.fillText(`${lab} ${num(p, pxd(s))}`, w - padR - 2, yy - 6); });
};

/* ------------------------------------------------------------------ ANR : recommandations des analystes (US) */
PAGES.ANR = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Analyst Recommendations'); const E = await getJSON('ee.json').catch(() => null); if (!alive()) return; const e = E && E[s.id];
  if (!e || !e.tp) { m.innerHTML = pn('Recommandations', 'ANR', '<div class="empty">Pas de recommandations publiées pour ce titre.</div>'); return; }
  const T = e.tp, n = (T.buy || 0) + (T.hold || 0) + (T.sell || 0), up = T.priceTarget && s.last ? T.priceTarget / s.last - 1 : null, score = n ? (T.buy * 5 + T.hold * 3 + T.sell * 1) / n : null;
  m.innerHTML = `<div class="grid c2">${pn(`${esc(ykey(s))} · consensus des analystes`, 'ANR', `<div class="kv2"><span>Analystes</span><b>${n}</b><span>Achat</span><b class="up">${T.buy || 0} (${n ? num(T.buy / n * 100, 0) : 0} %)</b><span>Conserver</span><b class="am">${T.hold || 0} (${n ? num(T.hold / n * 100, 0) : 0} %)</b><span>Vente</span><b class="dn">${T.sell || 0} (${n ? num(T.sell / n * 100, 0) : 0} %)</b><span>Note de consensus (1 = vente, 5 = achat)</span><b>${score != null ? num(score, 2) : '—'}</b>
      <span>Objectif de cours moyen à 12 mois</span><b class="yl">${num(T.priceTarget, 2)} $</b><span>Potentiel contre le dernier cours</span><b>${up != null ? pc(up, 1) : '—'}</b><span>Objectif le plus bas / le plus haut</span><b>${num(T.lowPriceTarget, 2)} / ${num(T.highPriceTarget, 2)} $</b><span>Dernier cours</span><b>${px(s, s.last)} $</b></div>${up != null && (up > .75 || up < -.5 || (T.lowPriceTarget && T.highPriceTarget / T.lowPriceTarget > 3)) ? '<div class="spb" style="margin:6px">Objectifs publiés incohérents avec le cours (écart inhabituel ou fourchette très large) : ils sont peut-être exprimés dans une autre devise ou sur une autre base d’action (ADR). À vérifier avant de s’en servir.</div>' : ''}${cvb('anB', 150)}`, { lect: `Consensus des analystes, relevé le ${fds(e.ts)}.` })}
    ${pn('Objectifs de cours', 'ANR', cvb('anT', 230), { lect: 'Fourchette des objectifs (plus bas, moyen, plus haut) comparée au dernier cours.' })}</div>
    ${e.yr && e.yr.length ? pn('BPA attendu par exercice', 'ANR', `<table class="t"><thead><tr><th class="l">Exercice</th><th>Consensus</th><th>Plus bas</th><th>Plus haut</th><th>Analystes</th><th>Révisions à la hausse / baisse (4 sem.)</th><th>PER implicite</th></tr></thead><tbody>${e.yr.map(y => `<tr><td class="l am">${esc(y.fiscalEnd)}</td><td class="wh">${num(y.consensusEPSForecast, 2)}</td><td>${num(y.lowEPSForecast, 2)}</td><td>${num(y.highEPSForecast, 2)}</td><td>${y.noOfEstimates}</td><td><span class="up">${y.up || 0}</span> / <span class="dn">${y.down || 0}</span></td><td>${y.consensusEPSForecast > 0 ? num(s.last / y.consensusEPSForecast, 1) : '—'}</td></tr>`).join('')}</tbody></table>`, { np: true, lect: 'Détail des estimations : EE.' }) : ''}`;
  barChart($('anB'), { labels: ['Achat', 'Conserver', 'Vente'], values: [T.buy || 0, T.hold || 0, T.sell || 0], fmt: v => num(v, 0), labelsOnBars: true, pos: '#3d7cc9' });
  const { x, w, h } = setupCanvas($('anT')); const vals = [T.lowPriceTarget, T.priceTarget, T.highPriceTarget, s.last].filter(v => v != null); const lo = Math.min(...vals) * .95, hi = Math.max(...vals) * 1.05, X = v => 40 + (v - lo) / (hi - lo) * (w - 80), y = h / 2;
  x.strokeStyle = '#555'; x.lineWidth = 6; x.beginPath(); x.moveTo(X(T.lowPriceTarget), y); x.lineTo(X(T.highPriceTarget), y); x.stroke(); x.lineWidth = 1;
  /* plus bas / plus haut au-dessus de la barre, moyen et dernier cours en dessous sur deux lignes (jamais superposés) */
  [[T.lowPriceTarget, '#ff3d4d', 'plus bas', -16], [T.highPriceTarget, '#2fd26a', 'plus haut', -16], [T.priceTarget, '#ffd200', 'objectif moyen', 28], [s.last, '#ffffff', 'dernier cours', 48]].forEach(([v, col, lab, dy]) => { if (v == null) return; x.fillStyle = col; x.strokeStyle = col;
    if (lab === 'dernier cours') { x.fillRect(X(v) - 1, y - 12, 2, 24); x.setLineDash([2, 3]); x.beginPath(); x.moveTo(X(v), y + 12); x.lineTo(X(v), y + dy - 12); x.stroke(); x.setLineDash([]); }
    else { x.beginPath(); x.arc(X(v), y, 6, 0, 7); x.fill(); if (dy > 0) { x.setLineDash([2, 3]); x.beginPath(); x.moveTo(X(v), y + 6); x.lineTo(X(v), y + dy - 12); x.stroke(); x.setLineDash([]); } }
    x.font = FUI; x.textAlign = X(v) < 90 ? 'left' : X(v) > w - 90 ? 'right' : 'center'; x.fillText(`${lab} ${num(v, 2)}`, X(v), y + dy); });
};

/* ------------------------------------------------------------------ STOCK BONDS (ex-RELS) : titres liés (obligations de l'émetteur, indices, pairs) */
PAGES['STOCK BONDS'] = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Stock & Bonds'); const OB = s.mkt === 'BRVM' ? await getJSON('bonds.json').catch(() => null) : null; if (!alive()) return;
  const key = (s.short || s.n || '').split(/[ (]/)[0].toUpperCase(), bonds = OB && OB.rows ? OB.rows.filter(b => b.code.split('.')[0].replace(/^F/, '') === s.id || (key.length > 3 && (b.n || '').toUpperCase().includes(key))) : [];
  const peers = secsWhere(x => x.id !== s.id && x.mkt === s.mkt && x.cls === s.cls && x.grp === s.grp).sort((a, b) => (b.mcap || 0) - (a.mcap || 0)).slice(0, 15);
  const idx = s.mkt === 'BRVM' ? ['BRVMC', 'BRVM30', 'BRVMPR', 'BRVMPA'].concat(secsWhere(x => x.mkt === 'BRVM' && x.cls === 'Index' && /BRVM-/.test(x.id)).map(x => x.id)).map(id => Q.by[id]).filter(Boolean) : ['QQQ', 'SPY', 'NDX'].map(id => Q.by[id]).filter(Boolean);
  const now = new Date();
  m.innerHTML = `<div class="grid c2r">${s.mkt === 'BRVM' ? pn(`Obligations de l’émetteur cotées à la BRVM (${bonds.length})`, 'STOCK BONDS', bonds.length ? `<table class="t"><thead><tr><th class="l">Code</th><th class="l">Nom</th><th>Coupon</th><th>Cours</th><th>Rendement estimé</th></tr></thead><tbody>${bonds.map(b => { const c = typeof bondCalc === 'function' ? bondCalc(b, now) : {}; return `<tr data-fn="UEMOA BONDS" style="cursor:pointer"><td class="l tk">${esc(b.code)}</td><td class="l nm">${esc(b.n)}</td><td>${b.cpn ? num(b.cpn * 100, 2) + ' %' : '—'}</td><td>${num(b.px, 0)}</td><td class="yl">${c.ok ? num(c.ytm * 100, 2) + ' %' : '<span class="dm">n.d.</span>'}</td></tr>`; }).join('')}</tbody></table>` : '<div class="empty">Aucune obligation de cet émetteur n’est cotée.</div>', { np: true, lect: 'Rendement estimé : hypothèses détaillées dans UEMOA BONDS.' }) : ''}
    ${pn('Indices', 'STOCK BONDS', `<div class="tw"><table class="t"><thead><tr><th class="l">Indice</th><th>Niveau</th><th>Var.</th><th>YTD</th><th title="Corrélation des rendements quotidiens sur 250 séances communes">Corr. 1 an</th><th title="Bêta sur 250 séances communes">Bêta</th></tr></thead><tbody>${idx.map(x => `<tr data-sec="${x.id}" data-to="GP" style="cursor:pointer"><td class="l am">${esc(x.n)}</td><td class="wh">${num(x.last, 2)}</td><td>${pc(x.pct)}</td><td>${pc(x.ytd, 1)}</td><td id="rc_${x.id}" class="dm">…</td><td id="rb_${x.id}" class="dm">…</td></tr>`).join('')}</tbody></table></div>`, { np: true, lect: 'Corrélation et bêta des rendements quotidiens du titre contre chaque indice, 250 dernières séances communes.' })}</div>
    ${pn(`Sociétés du même secteur : ${esc(s.grp || '—')} (${peers.length})`, 'STOCK BONDS', `<table class="t"><thead><tr><th class="l">Titre</th><th class="l">Nom</th><th>Cours</th><th>Var. %</th><th>Depuis janv.</th><th>Capitalisation</th><th>PER</th><th>Rendement</th></tr></thead><tbody>${peers.map(x => `<tr data-sec="${x.id}" data-to="DES" style="cursor:pointer"><td class="l tk">${x.id}</td><td class="l nm">${esc(x.short || x.n)}</td><td>${px(x, x.last)}</td><td>${pc(x.pct)}</td><td>${pc(x.ytd, 1)}</td><td>${big(x.mcap)}</td><td>${x.per ? num(x.per, 1) : '—'}</td><td>${x.yld ? num(x.yld * 100, 2) + ' %' : '—'}</td></tr>`).join('')}</tbody></table>`, { np: true, lect: 'Comparaison détaillée : PEER ; valorisation relative : RV.' })}`;
  /* corrélation / bêta calculés à la volée sur les séries quotidiennes */
  const A = await series(s.id).catch(() => null); if (!alive() || !A) return;
  const ra = new Map(); for (let i = 1; i < A.x.length; i++) if (A.c[i - 1] > 0 && A.c[i] > 0) ra.set(A.x[i], Math.log(A.c[i] / A.c[i - 1]));
  for (const x of idx) { const B = await series(x.id).catch(() => null); if (!alive()) return; const c = $('rc_' + x.id), b = $('rb_' + x.id); if (!c) continue;
    const P = []; if (B) for (let i = B.x.length - 1; i > 0 && P.length < 250; i--) { const r = ra.get(B.x[i]); if (r != null && B.c[i - 1] > 0 && B.c[i] > 0) P.push([r, Math.log(B.c[i] / B.c[i - 1])]); }
    if (P.length < 60) { c.textContent = b.textContent = '—'; continue; }
    const n = P.length, ma = P.reduce((t, p) => t + p[0], 0) / n, mb = P.reduce((t, p) => t + p[1], 0) / n; let sab = 0, saa = 0, sbb = 0; for (const [u, v] of P) { sab += (u - ma) * (v - mb); saa += (u - ma) ** 2; sbb += (v - mb) ** 2; }
    const r = saa && sbb ? sab / Math.sqrt(saa * sbb) : null; c.textContent = r != null ? num(r, 2) : '—'; b.textContent = sbb ? num(sab / sbb, 2) : '—'; c.className = b.className = r != null && r > .5 ? 'yl' : ''; }
};

/* ------------------------------------------------------------------ CACS : opérations sur titres */
PAGES.CACS = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Corporate Action Calendar'); const brvm = s.mkt === 'BRVM';
  const [DV, EV, S] = await Promise.all([brvm ? getJSON('dividends.json').catch(() => []) : [], brvm ? getJSON('events.json').catch(() => []) : [], series(s.id).catch(() => null)]); if (!alive()) return;
  const A = [];
  if (brvm) { for (const x of DV.filter(x => x.t === s.id && x.dps)) A.push({ d: x.det || x.pay || x.ann, k: 'Dividende', t: `Dividende net${x.ex ? ' de l’exercice ' + x.ex : ''} : ${num(x.dps, 2)} FCFA${x.det ? ' · détachement ' + fds(x.det) : ''}${x.pay ? ' · paiement ' + fds(x.pay) : ''}`, fut: (x.det || x.pay || '') > new Date().toISOString().slice(0, 10) });
    for (const e of EV.filter(e => e.t === s.id && /assembl|capital|fraction|division|split|offre|introduction|radiation|suspension|émission|augmentation/i.test((e.c || '') + ' ' + (e.ti || '')))) A.push({ d: e.d, k: e.c || 'Avis', t: e.ti, u: e.u }); }
  else if (S) { for (let i = 0; i < S.x.length; i++) if (S.div[i]) A.push({ d: S.d[i], k: 'Dividende', t: `Dividende de ${num(S.div[i], 4)} $ par action (date de détachement)` }); }
  A.sort((a, b) => (b.d || '').localeCompare(a.d || ''));
  const kinds = [...new Set(A.map(a => a.k))]; const st = ST.cacs = ST.cacs || { k: 'ALL' }; if (st.k !== 'ALL' && !kinds.includes(st.k)) st.k = 'ALL'; const L = A.filter(a => st.k === 'ALL' || a.k === st.k);
  m.innerHTML = pn(`${esc(ykey(s))} · opérations sur titres (${A.length})`, 'CACS', `<div class="tw" style="max-height:75vh"><table class="t"><thead><tr><th class="l">Date</th><th class="l">Type</th><th class="l">Opération</th></tr></thead><tbody>${L.map(a => `<tr${a.fut ? ' class="hl"' : ''}><td class="l">${fds(a.d)}</td><td class="l am">${esc(a.k)}</td><td class="l" style="white-space:normal">${a.u ? `<a href="${esc(a.u)}" target="_blank" rel="noopener" style="color:var(--white)">${esc(a.t || '')}</a>` : esc(a.t || '')}</td></tr>`).join('') || '<tr><td class="l dm" colspan="3">Aucune opération recensée.</td></tr>'}</tbody></table></div>`,
    { np: true, tools: `<span class="tlab">Type</span><select class="ofld" id="caK"><option value="ALL">Tous</option>${kinds.map(k => `<option ${st.k === k ? 'selected' : ''}>${esc(k)}</option>`).join('')}</select>`, lect: `Dividendes${brvm ? ', assemblées générales, opérations sur le capital et avis officiels' : ' (dates de détachement)'} ; en surbrillance : opérations à venir. Historique des dividendes : DVD.` });
  if ($('caK')) $('caK').onchange = e => { st.k = e.target.value; render(); };
};

/* ------------------------------------------------------------------ GF : graphique des fondamentaux */
const GF_M = [['rev', 'Chiffre d’affaires', 'm'], ['ni', 'Résultat net', 'm'], ['eps', 'BPA', 'e'], ['ebitda', 'EBITDA', 'm'], ['fcf', 'Free cash-flow', 'm'], ['ocf', 'Flux d’exploitation', 'm'], ['eq', 'Capitaux propres', 'm'], ['nd', 'Dette nette', 'm'], ['div', 'Dividendes versés', 'm'], ['deposits', 'Dépôts (banques)', 'm'], ['loans', 'Crédits (banques)', 'm']];
PAGES.GF = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Graph Fundamentals'); const F = await getJSON('fa/' + s.id + '.json').catch(() => null); if (!alive()) return;
  if (!F || !F.Y || !F.Y.y) { m.innerHTML = pn('Fondamentaux', 'GF', '<div class="empty">Comptes non disponibles pour ce titre.</div>'); return; }
  const Y = F.Y, ms = GF_M.filter(([k]) => Y[k] && Y[k].some(v => v != null)); const st = ST.gf = ST.gf || { k: 'rev', k2: 'ni' }; if (!Y[st.k]) st.k = ms[0][0]; if (!Y[st.k2]) st.k2 = '';
  const S = await series(s.id).catch(() => null); if (!alive()) return;
  const pxAt = y => { if (!S) return null; const t = y * 10000 + 1231; let v = null; for (let i = 0; i < S.x.length && S.x[i] <= t; i++) v = S.c[i]; return v; };
  const per = Y.eps ? Y.y.map((y, i) => Y.eps[i] > 0 && pxAt(y) ? pxAt(y) / Y.eps[i] : null) : null;
  const sel = id => `<select class="ofld" id="${id}">${id === 'gf2' ? '<option value="">(aucune)</option>' : ''}${ms.map(([k, l]) => `<option value="${k}" ${st[id === 'gf1' ? 'k' : 'k2'] === k ? 'selected' : ''}>${l}</option>`).join('')}</select>`;
  const lab = k => (GF_M.find(x => x[0] === k) || [k, k])[1], unit = k => (GF_M.find(x => x[0] === k) || [])[2] === 'e' ? (s.ccy || '') : (s.mkt === 'BRVM' ? 'M FCFA' : 'M$');
  const sc = k => (GF_M.find(x => x[0] === k) || [])[2] === 'm' ? (s.mkt === 'BRVM' ? 1 : 1e-6) : 1;
  const cg = (a, i) => i && a[i - 1] > 0 && a[i] != null ? a[i] / a[i - 1] - 1 : null; // (exercice précédent en perte ou nul : croissance non significative, comme dans FA)
  m.innerHTML = `<div class="tools"><span class="tlab">Indicateur</span>${sel('gf1')}<span class="tlab">Comparer à</span>${sel('gf2')}</div>
    <div class="grid c2">${pn(`${esc(ykey(s))} · ${lab(st.k)} (${unit(st.k)})`, 'GF', cvb('gfA', 280))}${st.k2 ? pn(`${lab(st.k2)} (${unit(st.k2)})`, 'GF', cvb('gfB', 280)) : per && per.some(v => v) ? pn('PER historique (cours de fin d’année ÷ BPA)', 'GF', cvb('gfP', 280)) : ''}</div>
    ${pn('Valeurs par exercice', 'GF', `<div class="tw"><table class="t"><thead><tr><th class="l"></th>${Y.y.map(y => `<th>${y}</th>`).join('')}</tr></thead><tbody>${[st.k, st.k2].filter(Boolean).map(k => `<tr><td class="l am">${lab(k)}</td>${Y[k].map(v => `<td>${v == null ? '—' : num(v * sc(k), (GF_M.find(x => x[0] === k) || [])[2] === 'e' ? 2 : 0)}</td>`).join('')}</tr><tr class="sub"><td class="l">croissance</td>${Y[k].map((v, i) => `<td>${cg(Y[k], i) != null ? pc(cg(Y[k], i), 0) : ''}</td>`).join('')}</tr>`).join('')}${per ? `<tr><td class="l am">PER (fin d’année)</td>${per.map(v => `<td>${v ? num(v, 1) : '—'}</td>`).join('')}</tr>` : ''}</tbody></table></div>`, { np: true, lect: 'Exercices publiés ; détail complet des comptes : FA.' })}`;
  const draw = (id, k) => barChart($(id), { labels: Y.y.map(String), values: Y[k].map(v => v == null ? 0 : v * sc(k)), fmt: v => num(v, (GF_M.find(x => x[0] === k) || [])[2] === 'e' ? 2 : 0), labelsOnBars: Y.y.length <= 12, pos: '#3d7cc9', neg: '#ff3d4d', padB: 22 });
  draw('gfA', st.k); if (st.k2) draw('gfB', st.k2); else if ($('gfP')) barChart($('gfP'), { labels: Y.y.map(String), values: per.map(v => v || 0), fmt: v => num(v, 1), labelsOnBars: Y.y.length <= 12, pos: '#f9a33a', padB: 22 });
  $('gf1').onchange = e => { st.k = e.target.value; render(); }; $('gf2').onchange = e => { st.k2 = e.target.value; render(); };
};

/* ------------------------------------------------------------------ MENU : menu des fonctions façon Bloomberg (fil d'Ariane, deux colonnes numérotées) */
PAGES.MENU = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Security Menu'); let n = 0;
  const cat = s.cls === 'Index' ? 'Indices' : s.typ === 'ETF' ? 'Fonds (ETF)' : s.cls === 'Equity' ? 'Actions cotées' : s.cls === 'Crypto' ? 'Crypto-actifs' : s.cls === 'Comdty' ? 'Matières premières' : s.cls === 'Curncy' ? 'Devises' : 'Marchés';
  const blk = ([g, codes]) => { const its = codes.filter(c => FN[c]).map(c => { n++; const why = avail(c, s); return `<div class="bm-it${why ? ' off' : ''}" ${why ? '' : `data-fn="${c}"`} data-n="${n}" title="${esc(FN[c][0] + ' — ' + (why ? 'non disponible : ' + why : FN[c][3]))}"><span class="ar">${why ? '' : '⬈'}</span><span class="no">${n})</span><b>${c}</b><span class="nm">${esc(FN[c][4])}</span></div>`; }).join('');
    return `<div class="bm-g"><div class="bm-h">${esc(g)} <span>›</span></div>${its}</div>`; };
  /* répartition par nombre de lignes (en-tête + fonctions), pas par nombre de groupes */
  const wt = MENU_GROUPS.map(([, c]) => 1 + c.filter(x => FN[x]).length), tot = wt.reduce((a, b) => a + b, 0), G = MENU_GROUPS.length;
  let pick = 1, best = 1e9;  /* le premier groupe reste à gauche ; l'ordre est conservé dans chaque colonne */
  for (let k = 1; k < 1 << G; k += 2) { let a = 0; for (let i = 0; i < G; i++) if (k >> i & 1) a += wt[i]; const d = Math.abs(tot - 2 * a); if (d < best) { best = d; pick = k; } }
  const L = MENU_GROUPS.filter((_, i) => pick >> i & 1), R = MENU_GROUPS.filter((_, i) => !(pick >> i & 1));
  const kv = [['Dernier', `${px(s, s.last)} ${s.ccy || ''}`], ['Variation', pc(s.pct)], ['1 mois', pc(s.r1m, 1)], ['Depuis janv.', pc(s.ytd, 1)], ['1 an', pc(s.r1y, 1)], ['Plus haut / bas 52 s.', `${px(s, s.hi52)} / ${px(s, s.lo52)}`], ['Volatilité 1 an', s.vol != null ? num(s.vol * 100, 1) + ' %' : '—'],
    s.mcap ? ['Capitalisation', big(s.mcap)] : null, s.per ? ['PER', num(s.per, 1)] : null, s.yld ? ['Rendement', num(s.yld * 100, 2) + ' %'] : null].filter(Boolean);
  m.innerHTML = `<div class="grid side"><div class="bmenu"><div class="bm-top"><span class="bm-cancel" id="bmX">&lt;Annuler&gt; X</span></div>
      <div class="bm-crumb"><span class="hm">⌂</span> <a data-fn="HELP">Menu principal des fonctions</a> › <a data-fn="${s.mkt === 'BRVM' ? 'BRVM' : s.mkt === 'US' ? 'US' : 'MONITOR'}">${cat}</a> › <i>Analyser ${esc((s.n || s.id).toUpperCase())} ${esc(ykey(s).split(' ').pop())}</i></div>
      <div class="bm-cols"><div>${L.map(blk).join('')}</div><div>${R.map(blk).join('')}</div></div>
      <div class="bm-foot"><span>Cliquez une fonction ou tapez son numéro puis &lt;GO&gt;.</span><span>MenuId : ${(s.id.split('').reduce((a, c) => a * 31 + c.charCodeAt(0), 7) % 9000) + 1000}</span></div></div>
    ${pn('Aperçu', s.id, `<div class="kv2">${kv.map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join('')}</div><div class="cv" id="mnS" style="height:130px;margin-top:8px"></div>`, { lect: `${esc(s.n)}${s.grp ? ' · ' + esc(s.grp) : ''}` })}</div>`;
  $('bmX').onclick = () => histGo(-1);
  const S = await series(s.id); if (!alive()) return; const k = Math.max(0, S.c.length - 260);
  new TSChart($('mnS'), { panes: [{ h: 1, noLegend: true }], padR: 50, padB: 16, grid: 'dot', xticks: bbgTicks }).set({ x: S.x.slice(k), series: [{ type: 'area', y: S.c.slice(k), color: '#ffffff', w: 1.1, grad: ['rgba(7,42,82,.97)', 'rgba(3,29,56,.97)'] }] });
};
