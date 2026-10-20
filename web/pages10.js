/* ================= FQT — actualités reliées, cartes de chaleur mondiales, macro BCEAO, obligations et courbes UEMOA, carte du pétrole ================= */
'use strict';
const EV_COL = { 'Résultats': '#f9a33a', 'Dividende': '#2fd26a', 'Assemblée': '#5fd0ea', 'Dirigeants': '#b69cff', 'Analystes': '#ff7ab2', 'Notation': '#ffd200', 'Émission': '#3fd3c0', 'Opération': '#ff9e2b', 'Régulation': '#ff3d4d',
  'Banques centrales': '#7fb3ff', 'Macro': '#9a9a9a', 'Matières premières': '#c8a24a', 'Crypto': '#b69cff', 'Marchés': '#6a6a6a' };
const evBadge = ev => ev ? `<b class="evb" style="background:${EV_COL[ev] || '#555'}">${esc(ev)}</b>` : '';
function newsRow2(x, o = {}) {
  const d = new Date(x.t * 1000), tk = (x.tk || []).filter(t => Q.by[t]);
  return `<div class="nw${o.short ? ' s' : ''}"><span class="d">${d.toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span><span class="c">${esc(srcCode(x))}</span><span>${evBadge(x.ev)}<a href="${esc(x.u)}" target="_blank" rel="noopener">${esc(deent(x.ti))}</a> ${hideSrc(x) ? '' : `<span class="src">${esc(deent(x.s || ''))}</span>`}${tk.length ? `<span class="tags">${tk.map(t => `<b data-sec="${t}" data-to="CN" title="${esc(Q.by[t].n)}">${t}</b>`).join('')}</span>` : ''}${x.x && !o.short ? `<small>${esc(deent(x.x))}</small>` : ''}</span></div>`;
}

/* ------------------------------------------------------------------ NEWS (ex-TOP) : fil relié aux titres, typé par événement */
/* PAGES.NEWS : définition remplacée plus loin (version active dans un fichier suivant) — retirée */

/* ------------------------------------------------------------------ CN : actualités de la société + historique des événements */
/* PAGES.CN : définition remplacée plus loin (version active dans un fichier suivant) — retirée */

/* ------------------------------------------------------------------ IMAP : Europe, Royaume-Uni, Asie, Afrique, Moyen-Orient (capitalisations mondiales) */
const WREG = {
  EU: ['Europe (hors R.-U.)', { Germany: 'Allemagne', France: 'France', Netherlands: 'Pays-Bas', Switzerland: 'Suisse', Italy: 'Italie', Spain: 'Espagne', Sweden: 'Suède', Denmark: 'Danemark', Belgium: 'Belgique', Finland: 'Finlande', Norway: 'Norvège', Ireland: 'Irlande', Austria: 'Autriche', Portugal: 'Portugal', Poland: 'Pologne', Luxembourg: 'Luxembourg', Greece: 'Grèce', 'Czech Republic': 'Tchéquie' }, 90],
  UK: ['Royaume-Uni', { 'United Kingdom': 'Royaume-Uni' }, 60],
  ASIA: ['Asie', { Japan: 'Japon', China: 'Chine', 'Hong Kong': 'Hong Kong', Taiwan: 'Taïwan', 'South Korea': 'Corée du Sud', India: 'Inde', Singapore: 'Singapour', Indonesia: 'Indonésie', Thailand: 'Thaïlande', Malaysia: 'Malaisie', Philippines: 'Philippines', Vietnam: 'Viêt Nam' }, 120],
  AFR: ['Afrique', { 'South Africa': 'Afrique du Sud', Nigeria: 'Nigeria', Morocco: 'Maroc', Egypt: 'Égypte', Kenya: 'Kenya', Ghana: 'Ghana', "Cote d'Ivoire": "Côte d'Ivoire", Senegal: 'Sénégal', Mauritius: 'Maurice', Tanzania: 'Tanzanie', Zimbabwe: 'Zimbabwe', Botswana: 'Botswana', Tunisia: 'Tunisie' }, 60],
  ME: ['Moyen-Orient', { 'Saudi Arabia': 'Arabie saoudite', 'United Arab Emirates': 'Émirats arabes unis', Qatar: 'Qatar', Israel: 'Israël', Kuwait: 'Koweït', Turkey: 'Turquie' }, 60] };
const PAGES_IMAP_LOCAL = PAGES.IMAP;
PAGES.MAP = async (m, alive) => {
  const st = ST.imap = ST.imap || { u: 'BRVM', c: 'pct', sz: 'var', z: 1 }; if (!st.z) st.z = 1;
  if (ST.tab.MAP) { st.u = ST.tab.MAP; delete ST.tab.MAP; } if (!FN_TABS.MAP.some(t => t[0] === st.u)) st.u = 'BRVM';
  setTabs(FN_TABS.MAP, st.u, k => { st.u = k; if (k !== 'BRVM' && !IMAP_SZ.some(x => x[0] === st.sz)) st.sz = 'var'; render(); });
  if (st.u === 'US') { setTitle('US Market Overview'); return PAGES.US(m, alive); }
  setTitle('Intraday Market Map');
  if (!WREG[st.u]) { await PAGES_IMAP_LOCAL(m, alive); const tb = m.querySelector('.tools'); if (tb) { const b = [...tb.children]; let i = b.findIndex(x => x.classList && x.classList.contains('tlab') && /Couleur/.test(x.textContent)); if (i > 0) b.slice(0, i).forEach(x => x.remove()); } return; }
  const W = await getJSON('world.json').catch(() => null); if (!alive()) return;
  const [title, CTY, nTop] = WREG[st.u];
  if (!W || !W.rows) { m.innerHTML = pn(`Carte de chaleur · ${title}`, 'MAP', '<div class="empty">Capitalisations mondiales en cours de collecte (relevé toutes les 15 minutes).</div>'); return; }
  const rows = W.rows.filter(r => CTY[r[2]]).slice(0, nTop).map(r => ({ sym: r[0], n: r[1], cty: CTY[r[2]], mc: r[3], px: r[4], p: r[5] }));
  if (!IMAP_SZ.some(x => x[0] === st.sz)) st.sz = 'var'; const eq = st.sz === 'eq';
  const wsz = r => eq ? 1 : st.sz === 'var' ? (r.p == null || !isFinite(r.p) ? 0 : Math.abs(r.p)) + .03 * .12 : r.mc;
  const G = {}; for (const r of rows) (G[r.cty] = G[r.cty] || []).push(r);
  const col = v => v == null || !isFinite(v) ? '#262626' : (() => { const a = Math.min(1, Math.abs(v) / .03); return v >= 0 ? `rgb(${Math.round(30 - 10 * a)},${Math.round(70 + 120 * a)},${Math.round(45 + 30 * a)})` : `rgb(${Math.round(90 + 140 * a)},${Math.round(40 - 10 * a)},${Math.round(40 - 5 * a)})`; })();
  const wavg = a => { let s = 0, w = 0; for (const x of a) if (x.p != null) { s += x.p * x.mc; w += x.mc; } return w ? s / w : null; };
  const sect = Object.entries(G).map(([g, a]) => ({ g, list: a, v: eq ? a.length : a.reduce((t, x) => t + wsz(x), 0), mc: a.reduce((t, x) => t + x.mc, 0), p: wavg(a), n: a.length })).sort((a, b) => b.v - a.v);
  const mov = rows.filter(r => r.p != null).sort((a, b) => b.p - a.p); const hasCh = mov.length > 0;
  m.innerHTML = `<div class="tools" style="border:1px solid var(--line2)">${imapTools(st)}</div><div class="grid">${pn(`Carte de chaleur · ${title} · ${rows.length} premières capitalisations`, 'MAP', `<div id="imM" class="imap" style="height:${imapH()}"></div><div class="imleg">${[-1, -.66, -.33, 0, .33, .66, 1].map(t => `<span style="background:${col(t * .03)}">${t > 0 ? '+' : ''}${num(t * 3, 1)}%</span>`).join('')}</div>`,
      { lect: `Regroupement par pays du siège (des sociétés cotées à New York mais domiciliées en Irlande ou en Suisse, comme Accenture ou Chubb, y figurent) ; taille des cases = ${imapSzLab(st.sz)}${st.sz === 'mcap' ? ' en dollars' : st.sz === 'var' ? ' (une case sans variation garde une petite taille fixe)' : ''} ; ${(st.z || 1) > 1 ? 'carte agrandie : faites-la glisser pour la déplacer ; ' : ''}couleur = variation ${hasCh ? `depuis le relevé de référence du ${esc(W.ref || '')} UTC (cours en dollars : inclut l’effet de change)` : '— <b>non encore disponible</b> : elle se calcule à partir du relevé de référence du soir (22 h 35 UTC)'}. Prix en USD, relevé ${new Date(W.ts * 1000).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}. Ces sociétés ne sont pas des titres suivis par le terminal : pas de fiche ni de graphique.` })}
    <div class="grid imap2">${pn('Pays (pondérés par la capitalisation)', 'MAP', `<table class="t"><thead><tr><th class="l">Pays</th><th>Sociétés</th><th>Capi. ($)</th><th>Var.</th></tr></thead><tbody>${sect.slice().sort((a, b) => b.mc - a.mc).map(x => `<tr><td class="l am">${esc(x.g)}</td><td>${x.n}</td><td>${big(x.mc)}</td><td>${x.p != null ? pc(x.p) : '—'}</td></tr>`).join('')}</tbody></table>`, { np: true })}
      ${hasCh ? pn('Plus fortes hausses et baisses', 'MAP', `<table class="t"><tbody>${mov.slice(0, 6).concat(mov.slice(-6)).map((r, i) => `<tr class="${i === 6 ? 'sep2' : ''}"><td class="l nm">${esc(r.n)}</td><td class="l dm">${esc(r.cty)}</td><td>${pc(r.p)}</td></tr>`).join('')}</tbody></table>`, { np: true }) : ''}</div></div>`;
  imapBind(m, st);
  const host = $('imM'), sf = imapSurface(host, st.z || 1), Wd = sf.W, Hd = sf.H; const boxes = squarify(sect.map(x => ({ ...x })), { x: 0, y: 0, w: Wd, h: Hd }); let html = '';
  for (const b of boxes) { const head = b.h > 40 && b.w > 60 ? 16 : 0; html += `<div class="ims" style="left:${b.x}px;top:${b.y}px;width:${b.w}px;height:${b.h}px">${head ? `<div class="imh">${esc(b.g)} <span>${b.p != null ? (b.p > 0 ? '+' : '') + num(b.p * 100, 2) + '%' : ''}</span></div>` : ''}</div>`;
    for (const t of imapPlace(b.list.map(r => ({ r, v: wsz(r), k: r.p })), { x: b.x + 1, y: b.y + head + 1, w: b.w - 2, h: b.h - head - 2 }, eq)) { const r = t.r;
      html += `<div class="imt" data-w="${esc(r.sym)}" style="left:${t.x}px;top:${t.y}px;width:${Math.max(0, t.w - 1)}px;height:${Math.max(0, t.h - 1)}px;background:${col(r.p)};cursor:default">${t.w > 40 && t.h > 22 ? `<b style="font-size:${U.clamp(Math.sqrt(t.w * t.h) / 7, 9, 18)}px">${esc(r.n.length > 14 && t.w < 120 ? r.sym : r.n.slice(0, 22))}</b>${t.h > 36 ? `<span>${r.p != null ? (r.p > 0 ? '+' : '') + num(r.p * 100, 2) + '%' : ''}</span>` : ''}` : ''}</div>`; } }
  sf.inner.innerHTML = html; const by = new Map(rows.map(r => [r.sym, r]));
  host.onmousemove = e => { if (sf.dragging()) return; const d = e.target.closest('.imt'); if (!d) { untip(); return; } const r = by.get(d.dataset.w); tip(e, `<b>${esc(r.n)}</b> (${esc(r.sym)}) · ${esc(r.cty)}<br>capitalisation ${big(r.mc)} $ · cours ${num(r.px, 2)} $<br>variation ${r.p != null ? pc(r.p) : 'n.d.'}`); };
  host.onmouseleave = untip;
};

/* ------------------------------------------------------------------ UEMOA : tableau de bord BCEAO + indicateurs Banque mondiale */
const PAGES_UEMOA_WB = PAGES.UEMOA;
const MOISF = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
const mLab = k => /^\d{4}-\d{2}$/.test(k) ? MOISF[+k.slice(5) - 1] + ' ' + k.slice(2, 4) : k;
PAGES['UEMOA/DATA'] = async (m, alive) => {
  const tab = tabState('UEMOA/DATA', 'bc'); setTabs(FN_TABS['UEMOA/DATA'], tab, k => { ST.tab['UEMOA/DATA'] = k; render(); });
  if (tab === 'ecst') return PAGES.ECST(m, alive); setTitle('WAEMU Economic Dashboard');
  if (tab === 'wb') return PAGES_UEMOA_WB(m, alive);
  const B = await getJSON('bceao.json').catch(() => null); if (!alive()) return;
  if (!B || !B.infl) { m.innerHTML = pn('BCEAO', 'UEMOA/DATA', '<div class="empty">Bulletin mensuel des statistiques de la BCEAO en attente de la collecte du soir.</div>'); return; }
  const srcL = `Période : ${esc(B.label || '—')} · relevé le ${fds(B.d)}.`;
  if (tab === 'tp') {
    const I = (B.issues || []).slice(); const byC = {}; for (const x of I) if (x.t != null) { const k = x.c.replace(/^la |^le |^l'/i, ''); (byC[k] = byC[k] || []).push(x); }
    const avg = (a, f) => { const v = a.filter(f); const w = v.reduce((s, x) => s + x.amt, 0); return w ? v.reduce((s, x) => s + x.t * x.amt, 0) / w : null; };
    m.innerHTML = `<div class="grid c2">${pn('Émissions par appel public à l’épargne (période du relevé)', 'UEMOA/DATA', `<div class="tw" style="max-height:70vh"><table class="t"><thead><tr><th class="l">Titre</th><th class="l">Émetteur</th><th>Montant (M FCFA)</th><th class="l">Émission</th><th>Durée (mois)</th><th class="l">Échéance</th><th>Taux</th></tr></thead><tbody>
        ${I.map(x => `<tr><td class="l">${esc(x.k)}</td><td class="l nm">${esc(x.c)}</td><td>${num(x.amt, 0)}</td><td class="l">${esc(x.d)}</td><td>${x.mois}</td><td class="l">${esc(x.ech)}</td><td class="yl">${x.t != null ? num(x.t, 2) + ' %' : 'multiples'}</td></tr>`).join('')}</tbody></table></div>`, { np: true, lect: srcL + ' Taux = taux d’intérêt (moyen pondéré) à l’émission publié par la BCEAO.' })}
      ${pn('Taux moyen pondéré par émetteur', 'UEMOA/DATA', `<table class="t"><thead><tr><th class="l">Émetteur</th><th>Émissions</th><th>Montant (Md FCFA)</th><th>Taux moyen</th><th>dont 12 mois</th></tr></thead><tbody>${Object.entries(byC).sort((a, b) => (avg(b[1], () => true) || 0) - (avg(a[1], () => true) || 0)).map(([c, a]) => `<tr><td class="l am">${esc(c)}</td><td>${a.length}</td><td>${num(a.reduce((s, x) => s + x.amt, 0) / 1e3, 1)}</td><td class="yl">${num(avg(a, () => true), 2)} %</td><td>${avg(a, x => x.mois === 12) != null ? num(avg(a, x => x.mois === 12), 2) + ' %' : '—'}</td></tr>`).join('')}</tbody></table>${cvb('ueTP', 240)}`, { np: true, lect: 'Moyenne des taux pondérée par les montants levés. Courbes complètes par pays : <b data-fn="GC" class="am" style="cursor:pointer">GC</b> ; obligations cotées : <b data-fn="UEMOA BONDS" class="am" style="cursor:pointer">SRCH</b>.' })}</div>`;
    const ent = Object.entries(byC).map(([c, a]) => [c, avg(a, () => true)]).sort((a, b) => b[1] - a[1]);
    barChart($('ueTP'), { labels: ent.map(e => e[0].slice(0, 10)), values: ent.map(e => e[1]), fmt: v => num(v, 2) + '%', labelsOnBars: true, pos: '#3d7cc9', padB: 22 });
    return;
  }
  const pol = B.policy || [], pl = pol[pol.length - 1] || {}, home = B.home || {}; const minR = home.min ?? pl.min, pretR = home.pret ?? pl.pret;
  const IU = (B.infl || {}).UEMOA || {}, ik = Object.keys(IU).filter(k => k.length === 7).sort(), il = ik[ik.length - 1];
  const mm = B.mm || [], mml = mm[mm.length - 1] || {}; const CR = B.credit || {}; const crK = k => { const o = CR[k] || {}; const ks = Object.keys(o).filter(x => x.length === 7).sort(); return [o[ks[ks.length - 1]], ks[ks.length - 1]]; };
  const [deb, debM] = crK("credits.taux.Taux d'intérêt moyen (%)"), [cred] = crK("depots.taux.Taux d'intérêt moyen (%)"), MO = (B.money || {}).rows || {};
  const tile = (n, v, sub) => `<div class="tile"><div class="tn">${n}</div><div class="tv">${v}</div><div class="tc">${sub || ''}</div></div>`;
  const cty = Object.keys(B.infl || {}); const months = ik.slice(-8);
  m.innerHTML = `<div class="tiles">${tile('Taux minimum de soumission aux appels d’offres', minR != null ? num(minR, 2) + ' %' : '—', pl.d ? 'depuis le ' + fds(pl.d) : '')}${tile('Taux du guichet de prêt marginal', pretR != null ? num(pretR, 2) + ' %' : '—', pl.d ? 'depuis le ' + fds(pl.d) : '')}
      ${tile('Inflation UEMOA (sur un an)', il ? num(IU[il], 1) + ' %' : '—', il ? mLab(il) : '')}${tile('Taux moyen du marché monétaire', mml.t != null ? num(mml.t, 2) + ' %' : '—', mml.m ? 'adjudications, ' + mLab(mml.m) : '')}
      ${tile('Taux débiteur moyen des banques', deb != null ? num(deb, 2) + ' %' : '—', debM ? 'crédits mis en place, ' + mLab(debM) : '')}${tile('Taux créditeur moyen', cred != null ? num(cred, 2) + ' %' : '—', 'nouveaux dépôts')}
      ${tile('Masse monétaire M2 (Union)', MO['Masse monétaire (M2)'] ? num(MO['Masse monétaire (M2)'].Union / 1e3, 1) + ' T FCFA' : '—', B.money && B.money.asof ? 'fin ' + mLab(B.money.asof) : '')}${tile('Crédit aux autres secteurs (Union)', MO['Créances sur les autres secteurs'] ? num(MO['Créances sur les autres secteurs'].Union / 1e3, 1) + ' T FCFA' : '—', 'créances des banques et de la BCEAO')}</div>
    <div class="grid c2">${pn('Taux directeurs de la BCEAO et inflation de l’UEMOA', 'UEMOA/DATA', cvb('ueR', 290), { lect: 'Paliers = taux directeurs (historique des modifications) ; ligne ambre = inflation sur un an de l’Union (mois connus). ' + srcL })}
      ${pn('Inflation par pays (glissement annuel, %)', 'UEMOA/DATA', `<table class="t"><thead><tr><th class="l">Pays</th>${Object.keys(B.infl[cty[0]] || {}).map(k => `<th>${mLab(k)}</th>`).join('')}</tr></thead><tbody>${cty.map(c => `<tr class="${c === 'UEMOA' ? 'sep2' : ''}"><td class="l am">${esc(c)}</td>${Object.values(B.infl[c]).map(v => `<td style="background:${heatBg(v / 100, .06)}">${num(v, 1)}</td>`).join('')}</tr>`).join('')}</tbody></table>`, { np: true, lect: 'Années = moyennes annuelles ; mois = glissement annuel. Critère de convergence de l’UEMOA : inflation ≤ 3 %.' })}</div>
    <div class="grid c2">${pn('Crédits et dépôts bancaires', 'UEMOA/DATA', `<div class="tw"><table class="t acc"><thead><tr><th class="l"></th>${Object.keys(CR["credits.taux.Taux d'intérêt moyen (%)"] || {}).map(k => `<th>${mLab(k)}</th>`).join('')}</tr></thead><tbody>${Object.entries(CR).map(([k, o]) => { const [sec_, sub, lab] = k.split('.'); return `<tr class="${sub === 'vol' && /Volume/.test(lab) || sec_ === 'marge' ? '' : 'sub'}"><td class="l">${sec_ === 'credits' ? 'Crédits' : sec_ === 'depots' ? 'Dépôts' : ''} ${esc(lab.replace(/\(en milliards de FCFA\)/, '(Md FCFA)'))}</td>${Object.values(o).map(v => `<td>${num(v, 2)}</td>`).join('')}</tr>`; }).join('')}</tbody></table></div>`, { np: true, lect: 'Crédits nouvellement mis en place et nouveaux dépôts : volumes (moyenne mensuelle sur l’année ou mois) et taux d’intérêt moyens. ' + srcL })}
      ${pn('Monnaie et crédit par pays (milliards de FCFA)', 'UEMOA/DATA', `<div class="tw"><table class="t"><thead><tr><th class="l"></th>${Object.keys(MO['Masse monétaire (M2)'] || {}).map(c => `<th>${esc(c.slice(0, 8))}</th>`).join('')}</tr></thead><tbody>${Object.entries(MO).map(([k, o]) => `<tr><td class="l am">${esc(k)}</td>${Object.values(o).map(v => `<td>${num(v, 0)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
        ${B.act ? `<h4 class="sub">Activité (glissement annuel, %)</h4><table class="t"><thead><tr><th class="l"></th>${Object.keys(Object.values(B.act)[0] || {}).map(k => `<th>${mLab(k)}</th>`).join('')}</tr></thead><tbody>${Object.entries(B.act).map(([k, o]) => `<tr><td class="l am">${esc(k)}</td>${Object.values(o).map(v => `<td>${num(v, 1)}</td>`).join('')}</tr>`).join('')}</tbody></table>` : ''}`, { np: true, lect: `Situation à fin ${B.money && B.money.asof ? mLab(B.money.asof) : '—'}. Créances sur les autres secteurs = crédit à l’économie (hors administration centrale). ` + srcL })}</div>`;
  /* graphique : paliers des taux directeurs + inflation */
  const dts = new Set(); const today = new Date().toISOString().slice(0, 10); ik.forEach(k => dts.add(k + '-15')); dts.add(today);
  /* paliers : un point la veille de chaque modification et un point par mois, pour tracer des marches et non des pentes */
  pol.forEach(p => { dts.add(p.d); const v = new Date(p.d + 'T12:00:00Z'); v.setUTCDate(v.getUTCDate() - 1); dts.add(v.toISOString().slice(0, 10)); });
  const y0 = pol.length ? +String(pol[0].d).slice(0, 4) : 2020;
  for (let y = y0; y <= +today.slice(0, 4); y++) for (let mo = 1; mo <= 12; mo++) { const k = `${y}-${String(mo).padStart(2, '0')}-01`; if (k <= today) dts.add(k); }
  const X = [...dts].filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d) && d >= '2016-01-01').sort(); const stepAt = (d, k) => { let v = null; for (const p of pol) if (p.d <= d) v = p[k]; return v; };
  const inflAt = d => { const k = d.slice(0, 7); return d.endsWith('-15') && IU[k] != null ? IU[k] : null; };
  new TSChart($('ueR'), { panes: [{ h: 1, fmt: v => num(v, 1) + '%' }], grid: 'dot', xticks: bbgTicks }).set({ x: X.map(s2i), series: [{ y: X.map(d => stepAt(d, 'pret')), color: '#ff3d4d', w: 1.6, label: 'Prêt marginal', fmt: v => num(v, 2) + '%' }, { y: X.map(d => stepAt(d, 'min')), color: '#5fd0ea', w: 1.6, label: 'Taux minimum de soumission', fmt: v => num(v, 2) + '%' }, { y: X.map(inflAt), color: '#f9a33a', w: 1.4, connect: true, label: 'Inflation UEMOA', fmt: v => num(v, 1) + '%' }] }, [0, X.length - 1]);
};

/* ------------------------------------------------------------------ SRCH : obligations cotées à la BRVM (rendement, duration, sensibilité) */
const CTY_OBL = { TPCI: "Côte d'Ivoire", TPSN: 'Sénégal', TPBJ: 'Bénin', TPBF: 'Burkina Faso', TPML: 'Mali', TPNE: 'Niger', TPTG: 'Togo', TPGB: 'Guinée-Bissau', EOM: 'Mali', EOS: 'Sénégal', SNTS: 'Sénégal' };
const parseFr = d => { const m = String(d || '').match(/(\d{2})\/(\d{2})\/(\d{4})/); return m ? new Date(Date.UTC(+m[3], +m[2] - 1, +m[1])) : null; };
/* Hypothèses explicites : coupon sur le nominal restant (estimé = dernier coupon ÷ taux, semestriel si le cours vaut ~2 fois ce nominal), remboursement in fine du nominal restant
   à la date anniversaire du dernier coupon, l'année d'échéance indiquée dans le nom ; base exact/365, taux actuariel annuel. */
function bondCalc(b, today = new Date()) {
  today = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));  /* date de valeur : le jour (GMT, Abidjan), pas l'heure — sinon le rendement dérive au fil des secondes */
  const o = { ok: false };
  if (!b.cpn || !b.y1 || !b.px) { o.why = b.cpn ? 'échéance ou cours absent' : 'taux variable ou coupon non publié'; return o; }
  const lp = parseFr(b.lp_d); let N = b.lp_v && b.cpn ? b.lp_v / b.cpn : null, f = 1;
  /* un cours se situe entre ~75 % et ~130 % du nominal : un rapport voisin de 2 signale un coupon semestriel */
  if (N) { /* nominal ≤ nominal d'émission usuel (10 000) ; cours entre 75 % et 130 % du nominal */
    const cand = [[N, 1], [2 * N, 2]].filter(([n]) => n <= 10150 && b.px / n >= .75 && b.px / n <= 1.3);
    if (cand.length !== 1) { Object.assign(o, { N, why: 'cours et coupon incohérents avec un nominal unique (amortissement ou cours ancien)' }); return o; }
    [N, f] = cand[0]; if (Math.abs(N - 10000) < 150) N = 10000; }
  if (!N) N = 10000;
  o.amort = N < 9900;
  /* obligation amortissable : l'échéancier (et donc le nominal restant après le dernier amortissement) n'est pas publié — pas de rendement calculé */
  if (o.amort) { Object.assign(o, { N, f, why: 'amortissable : échéancier non publié' }); return o; }
  const day = lp ? [lp.getUTCMonth(), lp.getUTCDate()] : [11, 31]; const T = new Date(Date.UTC(b.y1, day[0], day[1]));
  o.N = N; o.f = f; o.T = T; o.nomEst = !!b.lp_v;
  if (T <= today) { o.why = 'arrivée à échéance'; o.matured = true; return o; }
  const flows = []; let d = new Date(T); while (d > today) { flows.unshift(new Date(d)); d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - 12 / f, d.getUTCDate())); }
  const cf = flows.map((t, i) => ({ t: (t - today) / 864e5 / 365, v: N * b.cpn / f + (i === flows.length - 1 ? N : 0) }));
  const dirty = b.px + (b.cc || 0); const pv = r => cf.reduce((s, c) => s + c.v / Math.pow(1 + r, c.t), 0);
  let lo = -0.5, hi = 1.5; for (let k = 0; k < 120; k++) { const mid = (lo + hi) / 2; if (pv(mid) > dirty) lo = mid; else hi = mid; } const y = (lo + hi) / 2;
  const mac = cf.reduce((s, c) => s + c.t * c.v / Math.pow(1 + y, c.t), 0) / pv(y);
  if (y > .25 || y < 0) { Object.assign(o, { why: 'cours non représentatif (rendement hors norme)' }); return o; }  /* (rendement négatif sur un emprunt de l'UEMOA : dernier cours non représentatif) */
  Object.assign(o, { ok: true, ytm: y, cy: N * b.cpn / b.px, mac, mod: mac / (1 + y), sens: -mac / (1 + y) * b.px / 100, life: (T - today) / 864e5 / 365, cf, par: Math.abs(b.px / N - 1) < .005, pctN: b.px / N });
  return o;
}
PAGES.SRCH = async (m, alive) => {
  const B = await getJSON('bonds.json').catch(() => null); if (!alive()) return; setTitle('Fixed Income Search');
  if (!B || !B.rows) { m.innerHTML = pn('Obligations UEMOA', 'UEMOA BONDS', '<div class="empty">Cotations obligataires de la BRVM en attente du prochain relevé (toutes les 15 minutes).</div>'); return; }
  const st = ST.srch = ST.srch || { t: 'ALL', live: true, sort: 'ytm', dir: -1, sel: null, q: '' };
  setTabs([['ALL', 'Toutes'], ['État', 'États'], ['Régional', 'Organismes régionaux'], ['Privé', 'Émetteurs privés']], st.t, k => { st.t = k; render(); });
  const now = new Date(); const rows = B.rows.map(b => ({ b, c: bondCalc(b, now), cty: CTY_OBL[b.code.split('.')[0]] || (b.typ === 'État' ? '—' : '') }));
  let L = rows.filter(r => (st.t === 'ALL' || r.b.typ === st.t) && (!st.live || !r.c.matured) && (!st.q || (r.b.code + ' ' + r.b.n).toLowerCase().includes(st.q.toLowerCase())));
  const key = { ytm: r => r.c.ytm, cpn: r => r.b.cpn, mat: r => r.c.T ? +r.c.T : null, px: r => r.c.pctN, dur: r => r.c.mod, code: r => r.b.code };
  L.sort((a, b) => { const A = key[st.sort](a), Bv = key[st.sort](b); if (A == null) return 1; if (Bv == null) return -1; return (typeof A === 'string' ? A.localeCompare(Bv) : A - Bv) * st.dir; });
  const sel = rows.find(r => r.b.code === st.sel) || L[0];
  const th = (k, l) => `<th data-k="${k}" class="${st.sort === k ? 'on' : ''}" style="cursor:pointer">${l}</th>`;
  const okN = rows.filter(r => r.c.ok && !r.c.matured);
  m.innerHTML = `<div class="tools"><button class="tb ${st.live ? 'on' : ''}" id="obLive">${st.live ? 'En vie seulement' : 'Toutes, y compris échues'}</button><span class="tlab">Rechercher</span><form id="obF" style="display:inline-flex;gap:4px"><input id="obQ" value="${esc(st.q)}" placeholder="TPCI, BOAD, SONATEL…"><button class="tb">OK</button></form>
      <span class="tlab">${L.length} lignes · relevé ${new Date(B.ts * 1000).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span></div>
    <div class="grid side"><div class="pn"><div class="pt">Obligations cotées à la BRVM<span class="code">SRCH</span></div><div class="tw" style="max-height:calc(100vh - 290px)"><table class="t"><thead><tr>${th('code', 'Code')}<th class="l">Nom</th><th class="l">Type</th>${th('cpn', 'Coupon')}${th('mat', 'Échéance estimée')}${th('px', 'Cours / nominal')}<th>Coupon couru</th>${th('ytm', 'Rendement est.')}<th>Rdt courant</th>${th('dur', 'Sensibilité')}</tr></thead><tbody>
      ${L.map(r => `<tr data-ob="${esc(r.b.code)}" class="${sel && r.b.code === sel.b.code ? 'cur' : ''}" style="cursor:pointer"><td class="l tk">${esc(r.b.code)}</td><td class="l nm" style="max-width:280px;overflow:hidden;text-overflow:ellipsis" title="${esc(r.b.n)}">${esc(r.b.n)}</td><td class="l dm">${esc(r.b.typ || '')}</td><td>${r.b.cpn != null ? num(r.b.cpn * 100, 2) + '%' : '<span class="dm">var.</span>'}</td>
        <td>${r.c.T ? fds(r.c.T.toISOString().slice(0, 10)) : '—'}</td><td>${r.c.pctN ? num(r.c.pctN * 100, 2) + '%' : '—'}</td><td>${num(r.b.cc, 2)}</td><td class="yl">${r.c.ok ? num(r.c.ytm * 100, 2) + '%' : `<span class="dm" title="${esc(r.c.why || '')}">n.d.</span>`}</td><td>${r.c.ok ? num(r.c.cy * 100, 2) + '%' : '—'}</td><td>${r.c.ok ? num(r.c.mod, 2) : '—'}</td></tr>`).join('')}</tbody></table></div>
      <div class="lect"><b>Rendement estimé</b> : la BRVM ne publie ni la date exacte d’échéance ni l’échéancier d’amortissement. Hypothèses : nominal restant = dernier coupon ÷ taux du coupon (× 2 si le cours indique un coupon semestriel), remboursement in fine à la date anniversaire du dernier coupon dans l’année d’échéance du nom, base exact/365. <b>Obligations amortissables</b> (nominal restant inférieur au nominal d’émission) : rendement non calculé, faute d’échéancier publié. Un amortissement futur non connu raccourcit la vraie duration. <strong>Quand le cours égale le nominal, le rendement est égal au coupon</strong> ; beaucoup de lignes cotent au pair faute d’échanges : le rendement reflète alors le coupon d’émission, pas un prix de marché.</div></div>
      <div class="grid" style="align-content:start" id="obD"></div></div>`;
  const yas = r => { if (!r) return ''; const c = r.c, b = r.b;
    return pn(`${esc(b.code)} · ${esc(b.n)}`, 'YAS', `<div class="kv2"><span>Émetteur</span><b>${esc(b.iss || '')}${r.cty ? ' · ' + esc(r.cty) : ''}</b><span>Type</span><b>${esc(b.typ || '—')}</b><span>Coupon</span><b>${b.cpn != null ? num(b.cpn * 100, 2) + ' %' : 'variable'}</b><span>Date d’émission (cotation)</span><b>${esc(b.em || '—')}</b>
      <span>Dernier coupon payé</span><b>${b.lp_d ? esc(b.lp_d) + ' · ' + num(b.lp_v, 2) : '—'}</b><span>Cours (FCFA)</span><b>${num(b.px, 0)}</b><span>Coupon couru</span><b>${num(b.cc, 2)}</b>
      <span class="h">Calcul (hypothèses ci-contre)</span><span>Nominal restant estimé</span><b class="est">${c.N ? num(c.N, 0) : '—'}${c.f === 2 ? ' · coupon semestriel' : ''}${c.amort ? ' · amortissable' : ''}${!b.lp_v ? ' (nominal d’émission usuel supposé)' : ''}</b><span>Échéance estimée</span><b class="est">${c.T ? fds(c.T.toISOString().slice(0, 10)) : '—'}</b><span>Vie résiduelle</span><b>${c.life ? num(c.life, 2) + ' ans' : '—'}</b>
      <span>Rendement actuariel estimé</span><b class="yl">${c.ok ? num(c.ytm * 100, 3) + ' %' : 'n.d. (' + esc(c.why || '') + ')'}</b><span>Rendement courant</span><b>${c.ok ? num(c.cy * 100, 2) + ' %' : '—'}</b><span>Duration de Macaulay</span><b>${c.ok ? num(c.mac, 2) + ' ans' : '—'}</b><span>Sensibilité (duration modifiée)</span><b>${c.ok ? num(c.mod, 2) : '—'}</b>
      <span>Variation du cours pour +1 % de taux</span><b>${c.ok ? num(-c.mod, 2) + ' %' : '—'}</b></div>
      ${c.ok ? `<div class="form" style="margin-top:6px"><label>Rendement visé (%)<input id="ysY" value="${num(c.ytm * 100, 2)}"></label><label>Cours correspondant<input id="ysP" disabled></label></div>` : ''}`, { lect: 'YAS : prix et rendement calculés sur les mêmes flux estimés. ' + (c.par ? 'Cours = nominal restant : le rendement est égal au coupon.' : '') }); };
  const show = code => { const r = rows.find(x => x.b.code === code); st.sel = code; $('obD').innerHTML = yas(r) + pn('Répartition des rendements estimés (lignes en vie)', 'UEMOA BONDS', cvb('obH', 170));
    m.querySelectorAll('[data-ob]').forEach(tr => tr.classList.toggle('cur', tr.dataset.ob === code));
    const y = $('ysY'); if (y && r.c.ok) { const upd = () => { const v = parseFloat(y.value.replace(',', '.')) / 100; if (!isFinite(v)) return; const p = r.c.cf.reduce((s, c) => s + c.v / Math.pow(1 + v, c.t), 0) - (r.b.cc || 0); $('ysP').value = num(p, 0) + ' FCFA (' + num(p / r.c.N * 100, 2) + ' %)'; }; y.oninput = upd; upd(); }
    const ys = okN.map(r_ => r_.c.ytm * 100).filter(v => v > -5 && v < 20); const bins = {}; for (const v of ys) { const k = Math.floor(v * 2) / 2; bins[k] = (bins[k] || 0) + 1; } const ks = Object.keys(bins).map(Number).sort((a, b) => a - b);
    barChart($('obH'), { labels: ks.map(k => num(k, 1)), values: ks.map(k => bins[k]), fmt: v => num(v, 0), pos: '#3d7cc9', extra: i => 'rendement ' + num(ks[i], 1) + ' – ' + num(ks[i] + .5, 1) + ' %' }); };
  m.querySelectorAll('[data-ob]').forEach(tr => tr.onclick = () => show(tr.dataset.ob)); if (sel) show(sel.b.code);
  m.querySelectorAll('th[data-k]').forEach(t => t.onclick = () => { const k = t.dataset.k; st.dir = st.sort === k ? -st.dir : -1; st.sort = k; render(); });
  $('obLive').onclick = () => { st.live = !st.live; render(); }; $('obF').onsubmit = e => { e.preventDefault(); st.q = $('obQ').value.trim(); render(); };
};

/* ------------------------------------------------------------------ GC : courbes des taux souveraines de l'UEMOA (UMOA-Titres) */
/* les fichiers d'UMOA-Titres écrivent le même pays de plusieurs façons (« Côte d'Ivoire », « Cote d'ivoire ») */
const gcNorm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[’`]/g, "'").toLowerCase().trim();
const gcFind = (o, name) => { if (!o) return null; if (o[name]) return o[name]; const k = Object.keys(o).find(x => gcNorm(x) === gcNorm(name)); return k ? o[k] : null; };
const ctyName = c => ({ "Cote d'ivoire": "Côte d'Ivoire", "Cote d'Ivoire": "Côte d'Ivoire", 'Burkina': 'Burkina Faso' })[c] || c;
PAGES.GC = async (m, alive) => {
  const [C, B, OB] = await Promise.all([getJSON('umoa_curves.json').catch(() => null), getJSON('bceao.json').catch(() => null), getJSON('bonds.json').catch(() => null)]); if (!alive()) return; setTitle('Graph Curves');
  if (!C || !C.curves || !Object.keys(C.curves).length) { m.innerHTML = pn('Courbes souveraines', 'GC', '<div class="empty">Courbes souveraines en attente de la collecte du soir.</div>'); return; }
  const ds = Object.keys(C.curves).sort(), dL = ds[ds.length - 1], cur = C.curves[dL].c, ctys = Object.keys(cur);
  const st = ST.gc = ST.gc || { sel: ctys.slice(0, 4), cmp: null, cty: ctys.includes("Cote d'ivoire") ? "Cote d'ivoire" : ctys[0], kind: 3 }; if (!ctys.includes(st.cty)) st.cty = ctys[0];
  const COLS = ['#f9a33a', '#5fd0ea', '#2fd26a', '#ff7ab2', '#b69cff', '#ffd200', '#ff3d4d', '#3fd3c0'];
  const mats = [...new Set(ctys.flatMap(c => cur[c].map(p => p[0])))].sort((a, b) => { const y = s => { const m_ = s.match(/(\d+)\s*(mois|an)/); return m_ ? +m_[1] / (m_[2] === 'mois' ? 12 : 1) : 99; }; return y(a) - y(b); });
  const at = (c, lab, k = st.kind) => { const p = (cur[c] || []).find(q => q[0] === lab); return p ? p[k] : null; };
  setTabs([['c', 'Courbes par pays'], ['h', 'Évolution d’un pays']], tabState('GC', 'c'), k => { ST.tab.GC = k; render(); });
  if (ST.tab.GC === 'h') {
    const lines = ds.map((d, i) => ({ d, c: gcFind(C.curves[d].c, st.cty) })).filter(o => o.c);
    m.innerHTML = `<div class="tools"><span class="tlab">Pays</span><select class="ofld" id="gcC">${ctys.map(c => `<option value="${esc(c)}" ${c === st.cty ? 'selected' : ''}>${esc(ctyName(c))}</option>`).join('')}</select><span class="tlab">Taux</span><button class="tb ${st.kind === 3 ? 'on' : ''}" data-kd="3">Après lissage</button><button class="tb ${st.kind === 2 ? 'on' : ''}" data-kd="2">Zéro-coupon</button></div>
      ${pn(`${esc(ctyName(st.cty))} · courbe au ${esc(C.curves[dL].asof || dL)} et à des dates antérieures`, 'GC', cvb('gcH', 380), { lect: `Courbes hebdomadaires. Dates disponibles : ${lines.map(o => fds(o.d)).join(', ')}.` })}`;
    gcDraw($('gcH'), lines.map((o, i) => ({ lab: fds(o.d), col: i === lines.length - 1 ? '#f9a33a' : `rgba(200,200,200,${.25 + .5 * i / lines.length})`, pts: o.c.map(p => [p[1], p[st.kind]]), w: i === lines.length - 1 ? 2.2 : 1.2 })));
  } else {
    const iss = OB && OB.rows ? OB.rows.filter(b => b.typ === 'État' && b.cpn && b.y0 && b.y1 && b.y1 - b.y0 >= 2).map(b => ({ cty: CTY_OBL[b.code.split('.')[0]], y: b.y0, mat: b.y1 - b.y0, cpn: b.cpn })).filter(x => x.cty) : [];
    m.innerHTML = `<div class="tools"><span class="tlab">Pays affichés</span>${ctys.map((c, i) => `<button class="tb ${st.sel.includes(c) ? 'on' : ''}" data-cy="${esc(c)}"><i class="dot" style="background:${COLS[i % 8]}"></i>${esc(ctyName(c))}</button>`).join('')}<span class="tlab">Taux</span><button class="tb ${st.kind === 3 ? 'on' : ''}" data-kd="3">Après lissage</button><button class="tb ${st.kind === 2 ? 'on' : ''}" data-kd="2">Zéro-coupon</button></div>
      <div class="grid c2">${pn(`Courbes souveraines UEMOA au ${esc(C.curves[dL].asof || dL)}`, 'GC', cvb('gcC', 380), { lect: 'Zéro-coupon et taux après lissage, par État. Abscisse = maturité.' })}
      ${pn('Taux par maturité (%)', 'GC', `<div class="tw"><table class="t"><thead><tr><th class="l">Maturité</th>${ctys.map(c => `<th>${esc(ctyName(c).replace('Guinée-Bissau', 'G.-Bissau').replace('Burkina Faso', 'Burkina').replace("Côte d'Ivoire", 'C. d’Iv.'))}</th>`).join('')}</tr></thead><tbody>${mats.map(l => `<tr><td class="l am">${esc(l)}</td>${ctys.map(c => { const v = at(c, l); return `<td style="background:${v == null ? '' : `hsl(${Math.round(220 - U.clamp((v - .03) / .07, 0, 1) * 220)},55%,22%)`}">${v == null ? '—' : num(v * 100, 2)}</td>`; }).join('')}</tr>`).join('')}</tbody></table></div>`, { np: true, lect: 'Couleur : bleu = taux bas, rouge = taux élevé. Le spread entre États mesure la prime de risque perçue par les investisseurs du marché régional.' })}</div>
      ${iss.length ? pn('Coupons à l’émission des obligations d’État cotées à la BRVM (par année d’émission)', 'GC', cvb('gcI', 260), { lect: `Chaque point = une obligation d’État cotée : coupon fixé à l’émission (donnée publiée) selon l’année d’émission. ${[...new Set(iss.map(x => x.cty))].map((c, i) => `<i class="dot" style="background:${COLS[i % 8]}"></i>${esc(c)}`).join(' ')}. Ce ne sont pas des rendements de marché.` }) : ''}`;
    gcDraw($('gcC'), st.sel.map(c => ({ lab: ctyName(c), col: COLS[ctys.indexOf(c) % 8], pts: (cur[c] || []).map(p => [p[1], p[st.kind]]), w: 1.8 })));
    if (iss.length) { const cc = [...new Set(iss.map(x => x.cty))]; scatterL($('gcI'), { pts: iss.map((x, i) => ({ x: x.y + (i % 7) / 14, y: x.cpn, label: '', color: COLS[cc.indexOf(x.cty) % 8], id: null })), fx: v => String(Math.round(v)), fy: v => num(v * 100, 1) + '%', xlab: 'année d’émission', ylab: 'coupon', tipf: p => num(p.y * 100, 2) + ' %' }); }
    m.querySelectorAll('[data-cy]').forEach(b => b.onclick = () => { const c = b.dataset.cy; st.sel = st.sel.includes(c) ? st.sel.filter(x => x !== c) : st.sel.concat([c]); render(); });
  }
  m.querySelectorAll('[data-kd]').forEach(b => b.onclick = () => { st.kind = +b.dataset.kd; render(); }); if ($('gcC') && $('gcC').tagName === 'SELECT') { } const sc = document.getElementById('gcC'); if (sc && sc.tagName === 'SELECT') sc.onchange = e => { st.cty = st.foc = e.target.value; render(); };
};
function gcDraw(host, lines) {
  const { x, w, h } = setupCanvas(host); const padL = 46, padB = 22, padT = 10, W = w - padL - 12, H = h - padT - padB; const all = lines.flatMap(l => l.pts.map(p => p[1])).filter(v => v != null && isFinite(v));
  if (!all.length) return; let lo = Math.min(...all), hi = Math.max(...all); const pd = (hi - lo) * .1 || .005; lo -= pd; hi += pd;
  const tmax = Math.max(10, ...lines.flatMap(l => l.pts.map(p => p[0]))) * 1.04;
  const X = t => padL + Math.log(t * 12) / Math.log(tmax * 12) * W, Y = v => padT + (hi - v) / (hi - lo) * H; x.font = FNUM;
  x.setLineDash([1, 3]); for (const t of niceTicks(lo * 100, hi * 100, 5)) { const yy = Math.round(Y(t / 100)) + .5; x.strokeStyle = 'rgba(160,160,160,.35)'; x.beginPath(); x.moveTo(padL, yy); x.lineTo(w - 12, yy); x.stroke(); x.fillStyle = '#ddd'; x.textAlign = 'right'; x.fillText(num(t, 1) + '%', padL - 4, yy + 3); }
  const ticks = [[1 / 12, '1M'], [.25, '3M'], [.5, '6M'], [1, '1A'], [2, '2A'], [3, '3A'], [5, '5A'], [7, '7A'], [10, '10A'], [15, '15A'], [20, '20A'], [30, '30A']].filter(t => t[0] <= tmax); for (const [t, l] of ticks) { const xx = Math.round(X(t)) + .5; x.beginPath(); x.moveTo(xx, padT); x.lineTo(xx, padT + H); x.stroke(); x.fillStyle = '#ddd'; x.textAlign = 'center'; x.fillText(l, xx, h - 6); } x.setLineDash([]);
  lines.forEach((l, k) => { x.strokeStyle = l.col; x.lineWidth = l.w || 1.6; x.setLineDash(l.dash || []); x.beginPath(); l.pts.forEach((p, i) => { if (p[1] == null) return; i ? x.lineTo(X(p[0]), Y(p[1])) : x.moveTo(X(p[0]), Y(p[1])); }); x.stroke(); x.setLineDash([]); x.fillStyle = l.col; l.pts.forEach(p => { if (p[1] == null) return; x.beginPath(); x.arc(X(p[0]), Y(p[1]), 2.4, 0, 7); x.fill(); }); });
  let ly = padT + 4; x.font = FUI; x.textAlign = 'left'; for (const l of lines.slice(-9)) { x.fillStyle = 'rgba(0,0,0,.75)'; x.fillRect(padL + 6, ly - 1, x.measureText(l.lab).width + 22, 14); x.fillStyle = l.col; x.fillRect(padL + 9, ly + 3, 8, 6); x.fillStyle = '#e6e6e6'; x.fillText(l.lab, padL + 21, ly + 9); ly += 15; }
  host.onmousemove = e => { const r = host.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top; let best = null, bd = 100; for (const l of lines) for (const p of l.pts) { const d = (X(p[0]) - mx) ** 2 + (Y(p[1]) - my) ** 2; if (d < bd) { bd = d; best = [l, p]; } }
    if (best) tip(e, `<b>${esc(best[0].lab)}</b> · ${best[1][0] < 1 ? num(best[1][0] * 12, 0) + ' mois' : num(best[1][0], 0) + ' an(s)'} : <b>${num(best[1][1] * 100, 2)} %</b>`); else untip(); }; host.onmouseleave = untip;
}

/* ------------------------------------------------------------------ BMAP : carte et tableau de bord du pétrole */
const OIL_COL = { exp: '#ff9e2b', imp: '#5fd0ea' };
const eiv = (D, v) => v == null ? '—' : D && D.unit === 'TWh' ? num(v, 0) + ' TWh' : num(v / 1000, 2) + ' Mb/j';
function oilFacts(CP, OIL, WP, EI) {
  const F = [], cb = OIL && OIL.curve && OIL.curve.BRENT || [], cw = OIL && OIL.curve && OIL.curve.WTI || [];
  if (cb.length > 1) { const m1 = cb[0], mL = cb.find(x => x.k === '@LCO.12') || cb[cb.length - 1], d = m1.last - mL.last;
    F.push(`Courbe du Brent en <b>${d > 0 ? 'déport' : 'report'}</b> : 1er mois ${num(m1.last, 2)} $ contre ${num(mL.last, 2)} $ à 12 mois (${d > 0 ? '+' : ''}${num(d, 2)} $). ${d > 5 ? 'Un déport aussi marqué signale un marché physique très tendu : le baril livrable tout de suite vaut beaucoup plus que le baril futur.' : d < -1 ? 'Le report signale un marché bien approvisionné (stockage rémunéré).' : 'Courbe presque plate : marché équilibré.'}`); }
  if (cb.length && cw.length) F.push(`Écart Brent − WTI : <b>${num(cb[0].last - cw[0].last, 2)} $</b> (Brent ${num(cb[0].last, 2)} $, WTI ${num(cw[0].last, 2)} $).`);
  const P = OIL && OIL.prod || {}; if (P['@RB.1'] && P['@HO.1'] && cw.length) { const c321 = (2 * P['@RB.1'].last * 42 + P['@HO.1'].last * 42 - 3 * cw[0].last) / 3; F.push(`Marge de raffinage 3-2-1 (essence + gazole contre WTI) : <b>${num(c321, 2)} $/b</b>${c321 > 35 ? ', très élevée : les produits raffinés manquent plus que le brut' : ''}.`); }
  const fl = WP && WP.flows || {}; const yy = k => fl[k] && fl[k].v[2] ? fl[k].v[0] / fl[k].v[2] - 1 : null;
  if (fl.crude_exp) F.push(`États-Unis, semaine au ${esc(WP.week || '')} : exportations de brut ${num(fl.crude_exp.v[0], 0)} kb/j (${yy('crude_exp') != null ? (yy('crude_exp') > 0 ? '+' : '') + num(yy('crude_exp') * 100, 0) + ' % sur un an' : ''}), production ${fl.prod ? num(fl.prod.v[0], 0) + ' kb/j' : 'n.d.'}.`);
  const R = WP && WP.rows || {}; const spr = R['Strategic Petroleum Reserve (SPR)']; if (spr) F.push(`Réserve stratégique américaine : <b>${num(spr[0], 1)} Mb</b>, ${num((spr[0] / spr[4] - 1) * 100, 0)} % sur un an.`);
  const k = CP.years.length - 1, by = Object.fromEntries(CP.pts.map(p => [p.k, p.v])), i23 = CP.years.indexOf(2023);
  if (by.BAB && i23 >= 0) F.push(`Bab el-Mandeb : ${num(by.BAB[k], 1)} Mb/j (${CP.years[k]}) contre ${num(by.BAB[i23], 1)} en 2023 (${num((by.BAB[k] / by.BAB[i23] - 1) * 100, 0)} %) après les attaques en mer Rouge ; détour par le cap de Bonne-Espérance : ${num(by.CAP[k], 1)} Mb/j (${num(by.CAP[i23], 1)} en 2023).`);
  if (by.HOR) F.push(`Ormuz : ${num(by.HOR[k], 1)} Mb/j (${CP.years[k]}), soit ${num(by.HOR[k] / CP.world.maritime[k] * 100, 0)} % du commerce maritime mondial de pétrole.`);
  if (EI && EI.prod) { const Y = EI.prod.years, L = Y.length - 1, rows = Object.entries(EI.prod.rows).filter(([n]) => !/world|total|opec|non-opec|of which|europe$|africa$|america$|asia pacific|middle east$|cis$|oecd|european union/i.test(n)).sort((a, b) => (b[1][L] || 0) - (a[1][L] || 0));
    if (rows.length > 2) F.push(`Premiers producteurs de pétrole en ${Y[L]} : ${rows.slice(0, 3).map(([n, v]) => `${esc((CP.cty[n] || [])[2] || n)} ${eiv(EI.prod, v[L])}`).join(', ')}.`); }
  return F;
}
PAGES.BMAP = async (m, alive) => {
  setTitle('Oil Flow Map'); const [G, CP, WP, N, OIL, EI] = await Promise.all([getJSON('geo_world.json').catch(() => null), getJSON('chokepoints.json').catch(() => null), getJSON('oil_w.json').catch(() => null), getJSON('news.json').catch(() => ({ items: [] })), getJSON('oil.json').catch(() => null), getJSON('ei_oil.json').catch(() => null)]); if (!alive()) return;
  if (!G || !CP) { m.innerHTML = pn('Carte du pétrole', 'BMAP', '<div class="empty">Fond de carte en attente du prochain relevé.</div>'); return; }
  const st = ST.bmap = ST.bmap || { y: CP.years.length - 1, lay: { ch: 1, rt: 1, pp: 1, tm: 1, pr: 1 } }; const yi = Math.min(st.y, CP.years.length - 1), yr = CP.years[yi];
  const tab = tabState('BMAP', 'map'); setTabs([['map', 'Carte des flux'], ['mkt', 'Marché et courbes'], ['us', 'Flux des États-Unis'], ['prod', 'Producteurs et consommateurs'], ['chk', 'Détroits : historique']], tab, k => { ST.tab.BMAP = k; render(); });
  const onews = (N.items || []).filter(x => /p[ée]trol(e|i[eè]re?s?)\b|\bbrent\b|\bwti\b|\boil\b|\bcrude\b|opep|opec|baril|barrel|ormuz|hormuz|tanker|raffinerie|refiner/i.test(x.ti)).slice(0, 40);
  const cb = OIL && OIL.curve && OIL.curve.BRENT || [], cw = OIL && OIL.curve && OIL.curve.WTI || [], P = OIL && OIL.prod || {};
  const oilT = OIL ? new Date(OIL.ts * 1000).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '';
  const qrow = (lab, x, nd = 2, u = '') => x ? `<tr title="${esc(x.n || '')}"><td class="l am">${lab} <span class="dm">${esc((x.n || '').replace(/^.*\((.*)\)$/, '$1'))}</span></td><td class="wh">${num(x.last, nd)}${u}</td><td>${x.pct != null ? pc(x.pct) : '—'}</td></tr>` : '';
  const mktPanel = () => { const c321 = P['@RB.1'] && P['@HO.1'] && cw[0] ? (2 * P['@RB.1'].last * 42 + P['@HO.1'].last * 42 - 3 * cw[0].last) / 3 : null, dsl = P['@HO.1'] && cb[0] ? P['@HO.1'].last * 42 - cb[0].last : null, b12 = cb.find(x => x.k === '@LCO.12');
    return pn('Marché pétrolier', 'BMAP', `<table class="t"><thead><tr><th class="l">Contrat</th><th>Dernier</th><th>Var.</th></tr></thead><tbody>${qrow('Brent (ICE)', cb[0])}${qrow('WTI (NYMEX)', cw[0])}${qrow('Essence RBOB ($/gal)', P['@RB.1'], 4)}${qrow('Gazole ULSD ($/gal)', P['@HO.1'], 4)}${qrow('Gaz Henry Hub', P['@NG.1'], 3)}
      ${cb[0] && cw[0] ? `<tr class="sep2"><td class="l am">Écart Brent − WTI</td><td class="wh">${num(cb[0].last - cw[0].last, 2)}</td><td class="dm">$/b</td></tr>` : ''}${cb[0] && b12 ? `<tr><td class="l am">Brent 1er mois − 12 mois</td><td class="wh">${num(cb[0].last - b12.last, 2)}</td><td class="dm">${cb[0].last > b12.last ? 'déport' : 'report'}</td></tr>` : ''}
      ${c321 != null ? `<tr><td class="l am">Marge de raffinage 3-2-1 (WTI)</td><td class="wh">${num(c321, 2)}</td><td class="dm">$/b</td></tr>` : ''}${dsl != null ? `<tr><td class="l am">Marge gazole (Brent)</td><td class="wh">${num(dsl, 2)}</td><td class="dm">$/b</td></tr>` : ''}</tbody></table>`,
      { np: true, lect: OIL ? `Contrats à terme 1er mois (ICE, NYMEX), relevé ${oilT}, différé d’environ 10 min. Marge 3-2-1 = (2 × essence + 1 × gazole − 3 × WTI) ÷ 3, en $ par baril (42 gallons). Clic ailleurs : BRENT, WTI pour les graphiques.` : 'Tableau de bord en attente du prochain relevé (toutes les 15 min).' }); };
  const facts = oilFacts(CP, OIL, WP, EI);
  if (tab === 'map') {
    m.innerHTML = `<div class="grid side"><div class="pn"><div class="pt">Flux pétroliers maritimes · détroits ${yr}<span class="sel">${esc(CP.unit)}</span><span class="code">BMAP</span></div>
      <div class="tools"><span class="tlab">Année</span>${CP.years.map((y, i) => `<button class="tb ${i === yi ? 'on' : ''}" data-yi="${i}">${y}</button>`).join('')}<span class="tlab">Couches</span>${[['ch', 'Détroits'], ['rt', 'Routes'], ['pp', 'Oléoducs'], ['tm', 'Terminaux'], ['pr', 'Producteurs']].map(([k, l]) => `<button class="tb ${st.lay[k] ? 'on' : ''}" data-ly="${k}">${l}</button>`).join('')}</div>
      <div class="cv" id="bmC" style="height:max(440px, calc(100vh - 330px - var(--nwh, 90px)))"></div>
      <div class="lect">Cercles rouges = volumes ${yr} par détroit (édition du ${fds(CP.upd || '')}). Traits ambre = routes principales, <b>schématiques</b>. Pointillés bleus = oléoducs de contournement. Carrés = grands terminaux (ambre : exportation, bleu : importation ; positions approximatives). Bulles vertes = production de pétrole par pays${EI && EI.prod ? ` (${EI.prod.years[EI.prod.years.length - 1]})` : ' (en attente de la collecte du soir)'}. Survol = détails.</div></div>
      <div class="grid" style="align-content:start">${pn('Points clés', 'BMAP', `<div class="lectb">${facts.map(f => `<p>${f}</p>`).join('') || '<p class="dm">En attente des données.</p>'}</div>`)}
      ${mktPanel()}
      ${CP.y2026 ? pn(esc(CP.y2026.title), 'BMAP', `<table class="t"><tbody>${CP.y2026.pts.map(x => `<tr><td class="l am" style="vertical-align:top;white-space:nowrap">${esc(x.d.length === 7 ? mLab(x.d) : x.d)}</td><td class="l" style="white-space:normal">${esc(x.t)}</td></tr>`).join('')}</tbody></table>`, { np: true, lect: esc(CP.y2026.note || '') }) : ''}
      ${pn(`Actualités du pétrole (${onews.length})`, 'NEWS', `<div style="max-height:360px;overflow:auto">${onews.map(x => newsRow2(x, { short: true })).join('') || '<div class="dm">Aucune dépêche récente.</div>'}</div>`)}</div></div>`;
    m.querySelectorAll('[data-yi]').forEach(b => b.onclick = () => { st.y = +b.dataset.yi; render(); }); m.querySelectorAll('[data-ly]').forEach(b => b.onclick = () => { st.lay[b.dataset.ly] = st.lay[b.dataset.ly] ? 0 : 1; render(); });
    bmapDraw($('bmC'), G, CP, yi, st.lay, EI);
    return;
  }
  if (tab === 'mkt') {
    const eq = OIL && OIL.eq || [], maj = eq.filter(x => !['FRO', 'DHT', 'INSW', 'STNG', 'TNK', 'NAT'].includes(x.s)), tank = eq.filter(x => ['FRO', 'DHT', 'INSW', 'STNG', 'TNK', 'NAT'].includes(x.s));
    const eqT = L => `<table class="t"><thead><tr><th class="l">Titre</th><th class="l">Société</th><th>Cours</th><th>Var.</th><th>Plus bas 52 s.</th><th>Plus haut 52 s.</th></tr></thead><tbody>${L.map(x => `<tr><td class="l tk">${esc(x.s)}</td><td class="l nm">${esc(x.n || '')}</td><td class="wh">${num(x.last, 2)}</td><td>${x.pct != null ? pc(x.pct) : '—'}</td><td>${num(x.lo52, 2)}</td><td>${num(x.hi52, 2)}</td></tr>`).join('')}</tbody></table>`;
    m.innerHTML = `<div class="grid c2">${pn('Courbes à terme : Brent et WTI', 'BMAP', cvb('bmK', 300), { lect: `Prix de chaque échéance (abscisse = mois avant livraison). Courbe descendante = <b>déport</b> (backwardation) : le pétrole immédiat est rare. Courbe montante = <b>report</b> (contango). Relevé ${oilT}.` })}
      ${pn('Échéances', 'BMAP', `<table class="t"><thead><tr><th class="l">Échéance</th><th>Brent</th><th>WTI</th><th>Écart</th></tr></thead><tbody>${cb.map((b, i) => { const w = cw[i]; return `<tr><td class="l am">${esc((b.n || '').replace(/^.*\((.*)\)$/, '$1'))}</td><td class="wh">${num(b.last, 2)}</td><td>${w ? num(w.last, 2) : '—'}</td><td>${w ? num(b.last - w.last, 2) : '—'}</td></tr>`; }).join('')}</tbody></table>`, { np: true })}</div>
      <div class="grid c2">${mktPanel()}${pn('Brent et WTI sur un an (contrats 1er mois)', 'BMAP', cvb('bmH', 260))}</div>
      <div class="grid c2">${pn('Grandes compagnies pétrolières (cours en $)', 'BMAP', eqT(maj), { np: true })}${pn('Armateurs de pétroliers : indicateur du fret', 'BMAP', eqT(tank), { np: true, lect: 'Quand les routes s’allongent (détours par le cap de Bonne-Espérance, crise d’Ormuz), les taux de fret montent et ces titres avec. NYSE, différé.' })}</div>`;
    const kx = s_ => { const e = s_.exp ? new Date(s_.exp) : null; return e ? Math.max(0, (e - Date.now()) / 2.63e9) : null; };
    oilCurveDraw($('bmK'), [{ lab: 'Brent', col: '#ff9e2b', pts: cb.map(x => [kx(x), x.last]) }, { lab: 'WTI', col: '#5fd0ea', pts: cw.map(x => [kx(x), x.last]) }]);
    const [B, W] = await Promise.all([series('BRENT').catch(() => null), series('WTI').catch(() => null)]); if (!alive() || !B) return;
    const k0 = Math.max(0, B.x.length - 260), X = B.x.slice(k0), wm = W ? new Map(W.x.map((d, i) => [d, W.c[i]])) : new Map();
    new TSChart($('bmH'), { panes: [{ h: 1, fmt: v => num(v, 0) + ' $' }], grid: 'dot', xticks: bbgTicks }).set({ x: X, series: [{ y: B.c.slice(k0), color: '#ff9e2b', w: 1.5, label: 'Brent', fmt: v => num(v, 2) }, { y: X.map(d => wm.get(d) ?? null), color: '#5fd0ea', w: 1.3, label: 'WTI', fmt: v => num(v, 2), connect: true }] }, [0, X.length - 1]);
    return;
  }
  if (tab === 'us') {
    const fl = WP && WP.flows || {}, R = WP && WP.rows || {};
    const frow = k => { const f = fl[k]; if (!f) return ''; const [a, b, c] = f.v; return `<tr><td class="l am" style="white-space:normal">${esc(f.n)}</td><td class="wh">${num(a, f.u === '%' ? 1 : f.u === 'Mb' ? 1 : 0)}</td><td>${num(b, f.u === '%' ? 1 : f.u === 'Mb' ? 1 : 0)}</td><td class="${cls(a - b)}">${a != null && b != null ? (a - b > 0 ? '+' : '') + num(a - b, f.u === 'kb/j' ? 0 : 1) : '—'}</td><td>${num(c, f.u === '%' ? 1 : f.u === 'Mb' ? 1 : 0)}</td><td>${f.u !== '%' && a != null && c ? pc(a / c - 1, 1) : '—'}</td><td class="dm">${f.u}</td></tr>`; };
    const srow = (k, lab) => R[k] ? `<tr><td class="l am" style="white-space:normal">${lab}</td><td class="wh">${num(R[k][0], 1)}</td><td>${num(R[k][1], 1)}</td><td class="${cls(R[k][2])}">${num(R[k][2], 1)}</td><td>${num(R[k][4], 1)}</td><td>${pc(R[k][6] / 100, 1)}</td><td class="dm">Mb</td></tr>` : '';
    const head = `<thead><tr><th class="l">Semaine au ${esc(WP && WP.week || '—')}</th><th>Dernière</th><th>Précédente</th><th>Var.</th><th>Il y a un an</th><th>Sur un an</th><th class="l">Unité</th></tr></thead>`;
    m.innerHTML = `<div class="grid c2">${pn('États-Unis : production, échanges, raffinage', 'BMAP', `<table class="t">${head}<tbody>${['prod', 'crude_imp', 'crude_exp', 'crude_net', 'prod_exp', 'prod_net', 'tot_exp', 'tot_net', 'ref_in', 'util'].map(frow).join('')}</tbody></table>`, { np: true, lect: `Relevé le ${fds(WP && WP.d)}. kb/j = milliers de barils par jour ; importations nettes négatives = exportateur net. Publication chaque mercredi.` })}
      ${pn('États-Unis : stocks', 'BMAP', `<table class="t">${head}<tbody>${srow('Crude Oil', 'Brut (total)')}${srow('Commercial (Excluding SPR)', 'Brut commercial')}${frow('cush')}${srow('Strategic Petroleum Reserve (SPR)', 'Réserve stratégique')}${srow('Total Motor Gasoline', 'Essence')}${srow('Distillate Fuel Oil', 'Distillats (gazole, fioul)')}${srow('Kerosene-Type Jet Fuel', 'Kérosène')}${srow('Propane/Propylene', 'Propane')}${frow('tot_stk')}</tbody></table>`, { np: true })}</div>
      <div class="grid c2">${pn('Exportations et importations de brut (kb/j)', 'BMAP', cvb('bmU', 230))}${pn('Lecture', 'BMAP', `<div class="lectb">${facts.filter(f => /États-Unis|stratégique/.test(f)).map(f => `<p>${f}</p>`).join('')}</div>`)}</div>`;
    if (fl.crude_exp && fl.crude_imp) barChart($('bmU'), { labels: ['Import. sem.', 'Import. 1 an', 'Export. sem.', 'Export. 1 an'], values: [fl.crude_imp.v[0], fl.crude_imp.v[2], fl.crude_exp.v[0], fl.crude_exp.v[2]], fmt: v => num(v, 0), labelsOnBars: true, pos: '#3d7cc9' });
    return;
  }
  if (tab === 'prod') {
    if (!EI || !EI.prod) { m.innerHTML = pn('Producteurs et consommateurs', 'BMAP', '<div class="empty">Statistiques annuelles en attente de la collecte du soir.</div>'); return; }
    const agg = /world|total|opec|non-opec|of which|europe$|africa$|america$|asia pacific|middle east$|cis$|oecd|european union|other/i;
    const tbl = (D, lab) => { const Y = D.years, L = Y.length - 1, w = (D.rows.World || D.rows['Total World'] || [])[L]; const rows = Object.entries(D.rows).filter(([n]) => !agg.test(n)).sort((a, b) => (b[1][L] || 0) - (a[1][L] || 0)).slice(0, 25);
      return `<table class="t"><thead><tr><th class="l">${lab}</th><th>${Y[L]} (${D.unit === 'TWh' ? 'TWh' : 'Mb/j'})</th><th>Part</th><th>Sur un an</th><th>Sur 10 ans</th><th></th></tr></thead><tbody>${rows.map(([n, v]) => `<tr><td class="l am">${esc((CP.cty[n] || [])[2] || n)}</td><td class="wh">${D.unit === 'TWh' ? num(v[L], 0) : num(v[L] / 1000, 2)}</td><td>${w ? num(v[L] / w * 100, 1) + ' %' : '—'}</td><td>${v[L - 1] ? pc(v[L] / v[L - 1] - 1, 1) : '—'}</td><td>${v[0] ? pc(v[L] / v[0] - 1, 0) : '—'}</td><td>${sparkSVG(v, 80, 16)}</td></tr>`).join('')}${w ? `<tr class="sep2"><td class="l">Monde</td><td class="wh">${D.unit === 'TWh' ? num(w, 0) : num(w / 1000, 2)}</td><td></td><td>${pc(w / (D.rows.World || D.rows['Total World'])[L - 1] - 1, 1)}</td><td></td><td></td></tr>` : ''}</tbody></table>`; };
    m.innerHTML = `<div class="grid c2">${pn('Premiers producteurs de pétrole', 'BMAP', tbl(EI.prod, 'Pays'), { np: true, lect: `Production = brut, condensats, schistes, sables bitumineux et liquides de gaz naturel${EI.prod.unit === 'TWh' ? ', exprimée en énergie (TWh par an ; 1 Mb/j sur un an ≈ 620 TWh)' : ''}.` })}
      ${EI.cons ? pn('Premiers consommateurs de pétrole', 'BMAP', tbl(EI.cons, 'Pays'), { np: true }) : ''}</div>`;
    return;
  }
  /* détroits : historique */
  const k23 = CP.years.indexOf(2023), L = CP.years.length - 1;
  m.innerHTML = `${pn('Détroits stratégiques : volumes par année (Mb/j)', 'BMAP', `<table class="t"><thead><tr><th class="l">Détroit</th>${CP.years.map(y => `<th>${y}</th>`).join('')}<th>Part ${CP.years[L]}</th><th>vs 2023</th><th></th></tr></thead><tbody>${CP.pts.map(p => `<tr><td class="l am">${esc(p.n)}</td>${p.v.map(v => `<td>${num(v, 1)}</td>`).join('')}<td>${num(p.v[L] / CP.world.maritime[L] * 100, 0)} %</td><td>${k23 >= 0 ? pc(p.v[L] / p.v[k23] - 1, 0) : '—'}</td><td>${sparkSVG(p.v, 80, 16)}</td></tr>`).join('')}
    <tr class="sep2"><td class="l">Commerce maritime mondial</td>${CP.world.maritime.map(v => `<td>${num(v, 1)}</td>`).join('')}<td></td><td></td><td></td></tr><tr><td class="l">Offre mondiale de pétrole</td>${CP.world.supply.map(v => `<td>${num(v, 1)}</td>`).join('')}<td></td><td></td><td></td></tr></tbody></table>`, { np: true, lect: `Édition du ${fds(CP.upd || '')} (brut et produits pétroliers ; le canal de Panama est compté par exercice budgétaire d’octobre à septembre). Les attaques en mer Rouge depuis fin 2023 ont fait chuter Bab el-Mandeb et Suez au profit du cap de Bonne-Espérance.` })}
    <div class="grid c2">${pn(`Variation ${CP.years[L]} contre 2023 (Mb/j)`, 'BMAP', cvb('bmD', 260))}${pn('Lecture', 'BMAP', `<div class="lectb">${facts.filter(f => /Bab|Ormuz/.test(f)).map(f => `<p>${f}</p>`).join('')}</div>`)}</div>`;
  if (k23 >= 0) barChart($('bmD'), { labels: CP.pts.map(p => p.n.split(' (')[0].replace('Détroit de ', '').replace("Détroit d'", '').replace('Canal de Suez et oléoduc SUMED', 'Suez + SUMED').replace('Cap de Bonne-Espérance', 'Cap B.-E.')), values: CP.pts.map(p => p.v[L] - p.v[k23]), fmt: v => num(v, 1), labelsOnBars: true, pos: '#2fd26a', neg: '#ff3d4d', padB: 30 });
};
function oilCurveDraw(host, lines) {
  const { x, w, h } = setupCanvas(host); const padL = 46, padB = 22, padT = 10, W = w - padL - 12, H = h - padT - padB; const all = lines.flatMap(l => l.pts.filter(p => p[0] != null).map(p => p[1]));
  if (!all.length) { host.insertAdjacentHTML('beforeend', '<div class="empty" style="position:absolute;inset:0">Courbe en attente du prochain relevé.</div>'); return; }
  let lo = Math.min(...all), hi = Math.max(...all); const pd = (hi - lo) * .1 || 1; lo -= pd; hi += pd; const tmax = Math.max(12, ...lines.flatMap(l => l.pts.map(p => p[0] || 0)));
  const X = t => padL + t / tmax * W, Y = v => padT + (hi - v) / (hi - lo) * H; x.font = FNUM; x.setLineDash([1, 3]);
  for (const t of niceTicks(lo, hi, 5)) { const yy = Math.round(Y(t)) + .5; x.strokeStyle = 'rgba(160,160,160,.35)'; x.beginPath(); x.moveTo(padL, yy); x.lineTo(w - 12, yy); x.stroke(); x.fillStyle = '#ddd'; x.textAlign = 'right'; x.fillText(num(t, 0) + ' $', padL - 4, yy + 3); }
  for (let t = 0; t <= tmax; t += 3) { const xx = Math.round(X(t)) + .5; x.beginPath(); x.moveTo(xx, padT); x.lineTo(xx, padT + H); x.stroke(); x.fillStyle = '#ddd'; x.textAlign = 'center'; x.fillText(t + ' m', xx, h - 6); } x.setLineDash([]);
  lines.forEach(l => { x.strokeStyle = l.col; x.lineWidth = 2; x.beginPath(); l.pts.filter(p => p[0] != null).forEach((p, i) => i ? x.lineTo(X(p[0]), Y(p[1])) : x.moveTo(X(p[0]), Y(p[1]))); x.stroke(); x.fillStyle = l.col; l.pts.forEach(p => { if (p[0] == null) return; x.beginPath(); x.arc(X(p[0]), Y(p[1]), 3, 0, 7); x.fill(); }); });
  let ly = padT + 4; x.font = FUI; x.textAlign = 'left'; for (const l of lines) { x.fillStyle = l.col; x.fillRect(w - 90, ly + 3, 8, 6); x.fillStyle = '#e6e6e6'; x.fillText(l.lab, w - 78, ly + 9); ly += 15; }
}
function bmapDraw(host, G, CP, yi, lay, EI) {
  const cv = document.createElement('canvas'); host.appendChild(cv); const ctx = cv.getContext('2d');
  const byK = Object.fromEntries(CP.pts.map(p => [p.k, p])), vmax = Math.max(...CP.pts.map(p => p.v[yi])); let W = 0, H = 0, dpr = 1, land = null, t0 = performance.now(), hover = null;
  const PJ = (lon, lat) => [(lon + 180) / 360 * W, (72 - lat) / 128 * H];
  const prod = []; if (EI && EI.prod && lay.pr) { const L = EI.prod.years.length - 1; const tw = EI.prod.unit === 'TWh'; for (const [n, v] of Object.entries(EI.prod.rows)) { const c = CP.cty[n]; if (c && v[L] > (tw ? 350 : 600)) prod.push({ n: c[2], lat: c[0], lon: c[1], v: v[L], u: tw ? 'TWh' : 'kb/j', y: EI.prod.years[L] }); } }
  const pmax = Math.max(1, ...prod.map(p => p.v));
  const size = () => { const r = host.getBoundingClientRect(); dpr = Math.min(2, devicePixelRatio || 1); W = r.width; H = r.height; cv.width = W * dpr; cv.height = H * dpr; cv.style.width = W + 'px'; cv.style.height = H + 'px';
    land = document.createElement('canvas'); land.width = cv.width; land.height = cv.height; const g = land.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.fillStyle = '#020b1a'; g.fillRect(0, 0, W, H);
    g.strokeStyle = 'rgba(80,110,150,.18)'; g.lineWidth = 1; for (let lo = -180; lo <= 180; lo += 30) { const [x0] = PJ(lo, 0); g.beginPath(); g.moveTo(x0, 0); g.lineTo(x0, H); g.stroke(); } for (let la = -60; la <= 60; la += 30) { const [, y0] = PJ(0, la); g.beginPath(); g.moveTo(0, y0); g.lineTo(W, y0); g.stroke(); }
    g.fillStyle = '#1b2433'; g.strokeStyle = '#2f3b4f'; g.lineWidth = .7;
    for (const c of G.c) for (const r of c.r) { g.beginPath(); let px0 = null; r.forEach((p, i) => { const [x, y] = PJ(p[0], p[1]); if (i && Math.abs(x - px0) > W / 2) { g.moveTo(x, y); } else i ? g.lineTo(x, y) : g.moveTo(x, y); px0 = x; }); g.closePath(); g.fill(); g.stroke(); } };
  const draw = now => { if (!document.body.contains(cv)) return; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.drawImage(land, 0, 0, W, H); const ph = ((now - t0) / 60) % 24;
    if (lay.pr) for (const p of prod) { const [x, y] = PJ(p.lon, p.lat), r = 3 + 26 * Math.sqrt(p.v / pmax); ctx.fillStyle = p === hover ? 'rgba(47,210,106,.45)' : 'rgba(47,210,106,.22)'; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); ctx.strokeStyle = 'rgba(47,210,106,.7)'; ctx.lineWidth = 1; ctx.stroke();
      if (p.v > pmax * .3) { ctx.font = '460 10.5px ' + MONO; ctx.fillStyle = '#9fe8b9'; ctx.textAlign = 'center'; ctx.fillText(p.n, x, y + r + 11); } }
    if (lay.rt) for (const rt of CP.routes) { const v = Math.max(...rt.via.map(k => byK[k].v[yi])); const lw = 1 + 7 * v / vmax; ctx.strokeStyle = 'rgba(249,163,58,.28)'; ctx.lineWidth = lw; ctx.lineJoin = 'round'; ctx.beginPath(); rt.p.forEach((p, i) => { const [x, y] = PJ(p[0], p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke();
      ctx.strokeStyle = 'rgba(255,214,140,.85)'; ctx.lineWidth = Math.max(1, lw / 3); ctx.setLineDash([3, 21]); ctx.lineDashOffset = -ph; ctx.stroke(); ctx.setLineDash([]); }
    if (lay.pp) for (const pl of CP.pipes || []) { ctx.strokeStyle = pl === hover ? '#9be7ff' : '#5fd0ea'; ctx.lineWidth = 2.2; ctx.setLineDash([5, 4]); ctx.beginPath(); pl.p.forEach((p, i) => { const [x, y] = PJ(p[0], p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke(); ctx.setLineDash([]); }
    if (lay.ch) for (const p of CP.pts) { const [x, y] = PJ(p.lon, p.lat), r = 4 + 22 * Math.sqrt(p.v[yi] / vmax); ctx.fillStyle = p === hover ? 'rgba(255,61,77,.55)' : 'rgba(255,61,77,.35)'; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); ctx.strokeStyle = '#ff3d4d'; ctx.lineWidth = 1.2; ctx.stroke();
      ctx.font = '460 11.5px ' + MONO; ctx.fillStyle = '#fff'; ctx.textAlign = 'left'; ctx.fillText(`${p.n.split(' (')[0].replace(' et oléoduc SUMED', ' + SUMED')} ${num(p.v[yi], 1)}`, x + r + 3, y + 4); }
    if (lay.tm) for (const t of CP.terms || []) { const [x, y] = PJ(t.lon, t.lat); ctx.fillStyle = OIL_COL[t.k] || '#fff'; ctx.fillRect(x - 3, y - 3, 6, 6); ctx.strokeStyle = '#000'; ctx.lineWidth = 1; ctx.strokeRect(x - 3, y - 3, 6, 6); }
    if (CP.y2026 && lay.ch) { const h_ = byK.HOR; if (h_) { const [x, y] = PJ(h_.lon, h_.lat); ctx.font = '700 11px ' + MONO; ctx.fillStyle = '#ffd200'; ctx.textAlign = 'left'; ctx.fillText('2026 : crise d’Ormuz', x + 8, y + 22); } }
    requestAnimationFrame(draw); };
  size(); requestAnimationFrame(draw); new ResizeObserver(() => size()).observe(host);
  const near = (mx, my) => { let b = null, bd = 1e9; const chk = (o, x, y, r) => { const d = (x - mx) ** 2 + (y - my) ** 2; if (d < r * r && d < bd) { bd = d; b = o; } };
    if (lay.tm) for (const t of CP.terms || []) { const [x, y] = PJ(t.lon, t.lat); chk(t, x, y, 8); }
    if (lay.ch) for (const p of CP.pts) { const [x, y] = PJ(p.lon, p.lat); chk(p, x, y, 24); }
    if (lay.pp) for (const pl of CP.pipes || []) for (const q of pl.p) { const [x, y] = PJ(q[0], q[1]); chk(pl, x, y, 12); }
    if (lay.pr) for (const p of prod) { const [x, y] = PJ(p.lon, p.lat); chk(p, x, y, 3 + 26 * Math.sqrt(p.v / pmax)); }
    return b; };
  cv.onmousemove = e => { const r = cv.getBoundingClientRect(); hover = near(e.clientX - r.left, e.clientY - r.top); const o = hover; if (!o) { untip(); return; }
    if (o.v && Array.isArray(o.v)) tip(e, `<b>${esc(o.n)}</b><br>${CP.years.map((y, i) => `${y} : ${num(o.v[i], 1)}`).join(' · ')} Mb/j<br>part du commerce maritime ${CP.years[yi]} : ${num(o.v[yi] / CP.world.maritime[yi] * 100, 0)} %`);
    else if (o.cap) tip(e, `<b>${esc(o.n)}</b> (${esc(o.c)})<br>${esc(o.cap)}`);
    else if (o.k) tip(e, `<b>${esc(o.n)}</b> · ${esc(o.c)}<br>terminal ${o.k === 'exp' ? 'd’exportation' : 'd’importation'} · ${esc(o.z)}`);
    else tip(e, `<b>${esc(o.n)}</b><br>production de pétrole ${o.y} : ${num(o.v, 0)} ${o.u}`); };
  cv.onmouseleave = () => { hover = null; untip(); };
}
