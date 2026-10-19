/* ================= FQT — BANK : banques cotées à la BRVM côte à côte ; DIVC : aristocrates du dividende, encaissements ================= */
'use strict';
/* ------------------------------------------------------------------ BANK
   Chiffres des fiches FA (comptes publiés par chaque banque, montants en millions de FCFA) : les mêmes que dans FA, rien n'est
   estimé ; un poste non publié reste vide. Coefficient d'exploitation et ratio de solvabilité : tels que publiés par la banque. */
const BANK_M = [  // [clé, libellé, format (md = montant, p = part), sens (1 = plus haut est meilleur, -1 = plus bas, 0 = neutre), valeur(Y, i)]
  ['pnb', 'PNB', 'md', 0, (Y, i) => Y.rev[i]],
  ['g_pnb', 'Croissance du PNB', 'p', 1, (Y, i) => i > 0 && Y.y[i - 1] === Y.y[i] - 1 && Y.rev[i] > 0 && Y.rev[i - 1] > 0 ? Y.rev[i] / Y.rev[i - 1] - 1 : null],
  ['rn', 'Résultat net', 'md', 0, (Y, i) => Y.ni[i]],
  ['g_rn', 'Croissance du résultat net', 'p', 1, (Y, i) => i > 0 && Y.y[i - 1] === Y.y[i] - 1 && Y.ni[i] != null && Y.ni[i - 1] > 0 ? Y.ni[i] / Y.ni[i - 1] - 1 : null],
  ['rn_pnb', 'Résultat net / PNB', 'p', 1, (Y, i) => Y.rev[i] > 0 && Y.ni[i] != null ? Y.ni[i] / Y.rev[i] : null],
  ['cir', 'Coefficient d’exploitation', 'p', -1, (Y, i) => Y.cir && Y.cir[i] != null ? Y.cir[i] / 100 : null],
  ['cor', 'Coût du risque', 'md', 0, (Y, i) => Y.cor ? Y.cor[i] : null],
  ['cor_l', 'Coût du risque / crédits', 'p', -1, (Y, i) => Y.cor_l ? Y.cor_l[i] : null],
  ['roe', 'ROE', 'p', 1, (Y, i) => Y.roe ? Y.roe[i] : null],
  ['roa', 'ROA', 'p', 1, (Y, i) => Y.assets[i] > 0 && Y.ni[i] != null ? Y.ni[i] / Y.assets[i] : null],
  ['ld', 'Crédits / dépôts', 'p', 0, (Y, i) => Y.ld ? Y.ld[i] : null],
  ['eq_ta', 'Capitaux propres / total bilan', 'p', 1, (Y, i) => Y.assets[i] > 0 && Y.eq[i] > 0 ? Y.eq[i] / Y.assets[i] : null],
  ['solv', 'Ratio de solvabilité', 'p', 1, (Y, i) => Y.solv && Y.solv[i] != null ? Y.solv[i] / 100 : null],
  ['ta', 'Total bilan', 'md', 0, (Y, i) => Y.assets[i]],
  ['dep', 'Dépôts de la clientèle', 'md', 0, (Y, i) => Y.deposits[i]],
  ['cred', 'Crédits à la clientèle', 'md', 0, (Y, i) => Y.loans[i]],
  ['eq', 'Capitaux propres', 'md', 0, (Y, i) => Y.eq[i]]];
const BANK_BY = Object.fromEntries(BANK_M.map(x => [x[0], x]));
const bankFmt = (v, f) => v == null || !isFinite(v) ? '—' : f === 'p' ? num(v * 100, 1) + ' %' : f === 'md' ? num(v / 1e3, 1) : num(v, 2);
function bankSeries(f) { const Y = f.Y || {}, S = {}; if (!Y.y) return S; for (const [k, , , , fn] of BANK_M) { S[k] = {}; Y.y.forEach((y, i) => { const v = fn(Y, i); if (v != null && isFinite(v)) S[k][y] = v; }); } return S; }
/* valeur de l'exercice fy ; à défaut, le dernier chiffre publié des deux exercices précédents (année signalée), sauf pour une
   croissance (elle n'a de sens que pour l'exercice affiché) */
function bankAt(S, k, fy) { const s = S[k] || {}; if (s[fy] != null) return [s[fy], fy]; if (k.startsWith('g_')) return [null, null]; for (const y of [fy - 1, fy - 2]) if (s[y] != null) return [s[y], y]; return [null, null]; }
PAGES.BANK = async (m, alive) => {
  const tab = tabState('BANK', 'c'); setTabs(FN_TABS.BANK, tab, k => { ST.tab.BANK = k; render(); });
  const B = secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity' && s.bank);
  m.innerHTML = '<div class="empty">Chargement des comptes des banques…</div>';
  const F = await Promise.all(B.map(s => getJSON(`fa/${s.id}.json`).catch(() => null))); if (!alive()) return;
  const D = B.map((s, i) => ({ s, f: F[i] })).filter(x => x.f && x.f.Y && x.f.Y.y);
  if (!D.length) { m.innerHTML = pn('Banques cotées', 'BANK', '<div class="empty">Comptes des banques indisponibles pour le moment.</div>'); return; }
  for (const d of D) { d.S = bankSeries(d.f); d.fy = d.f.fy; }
  const st = ST.bank = ST.bank || { sort: { k: 'pnb', dir: -1 }, m: 'roe' };
  if (tab === 'h') {
    setTitle('BRVM Bank Dashboard · 10 Years');
    const mk = BANK_BY[st.m] || BANK_BY.roe, yN = Math.max(...D.map(d => d.fy).filter(isFinite)), YRS = Array.from({ length: 10 }, (_, i) => yN - 9 + i);
    const vals = D.flatMap(d => YRS.map(y => d.S[mk[0]][y])).filter(v => v != null && isFinite(v)).sort((a, b) => a - b);
    const q = p => vals.length ? vals[Math.min(vals.length - 1, Math.floor(p * (vals.length - 1)))] : 0, lo = q(.1), hi = q(.9);
    const colr = v => { if (v == null || !isFinite(v) || !mk[3] || hi === lo) return ''; let a = Math.max(0, Math.min(1, (v - lo) / (hi - lo))); if (mk[3] < 0) a = 1 - a; return `background:${a >= .5 ? `rgba(52,210,110,${((a - .5) * 1.1).toFixed(2)})` : `rgba(255,75,66,${((.5 - a) * 1.1).toFixed(2)})`}`; };
    const rows = D.slice().sort((a, b) => (bankAt(b.S, mk[0], yN)[0] ?? -1e18) - (bankAt(a.S, mk[0], yN)[0] ?? -1e18));
    m.innerHTML = `<div class="tools" style="border:1px solid var(--line2)"><span class="tlab">Indicateur</span>${BANK_M.map(([k, l]) => `<button class="tb ${mk[0] === k ? 'on' : ''}" data-bm="${k}">${l}</button>`).join('')}</div>
      ${pn(`${mk[1]} · ${D.length} banques · ${YRS[0]}-${yN}`, 'BANK', `<div class="tw"><table class="t"><thead><tr><th class="l">Banque</th><th class="l">Pays</th>${YRS.map(y => `<th>${y}</th>`).join('')}</tr></thead><tbody>${rows.map(d => `<tr data-sec="${d.s.id}" data-to="FA"><td class="l nm">${esc(d.s.short || d.s.n)}</td><td class="l dm">${esc(d.s.cty || '')}</td>${YRS.map(y => { const v = d.S[mk[0]][y]; return `<td style="${colr(v)}">${bankFmt(v, mk[2])}</td>`; }).join('')}</tr>`).join('')}</tbody></table></div>`,
        { np: true, lect: `${mk[2] === 'md' ? 'Montants en milliards de FCFA. ' : ''}${mk[3] ? `Couleur : du rouge (moins bon) au vert (meilleur), sur l’ensemble des banques et des années ${mk[3] < 0 ? '(plus bas = meilleur)' : '(plus haut = meilleur)'}. ` : ''}Comptes publiés par chaque banque ; une case vide = exercice ou poste non publié. Clic : analyse financière de la banque (FA).` })}`;
    m.querySelectorAll('[data-bm]').forEach(b => b.onclick = () => { st.m = b.dataset.bm; render(); });
    return;
  }
  setTitle('BRVM Bank Dashboard');
  const COLS = ['pnb', 'g_pnb', 'rn', 'g_rn', 'cir', 'cor_l', 'roe', 'roa', 'ld', 'eq_ta', 'solv'];
  const R = D.map(d => { const r = { id: d.s.id, s: d.s, y: d.fy, short: d.s.short || d.s.n, cty: d.s.cty || '', at: {} }; for (const k of COLS) { const [v, y] = bankAt(d.S, k, d.fy); r[k] = v; r.at[k] = y; } const ni = d.S.rn || {}; r.ns = d.S.g_rn[d.fy] == null && ni[d.fy] != null && ni[d.fy - 1] != null && ni[d.fy - 1] <= 0; r.pb = d.f.pb || null; r.pe = d.f.pe || null; r.dy = d.s.yld != null ? d.s.yld : null; return r; });
  const cols = [['short', 'Banque', 1], ['cty', 'Pays', 1], ['y', 'Ex.'], ['pnb', 'PNB (Md)'], ['g_pnb', 'Var. PNB'], ['rn', 'Résultat (Md)'], ['g_rn', 'Var. RN'], ['cir', 'Coef. d’expl.'], ['cor_l', 'Coût du risque / crédits'], ['roe', 'ROE'], ['roa', 'ROA'], ['ld', 'Crédits / dépôts'], ['eq_ta', 'CP / bilan'], ['solv', 'Solvabilité'], ['pb', 'P/B'], ['pe', 'PER'], ['dy', 'Rdt']];
  const rows = sortRows(R, st.sort);
  const med = k => { const a = R.map(r => r[k]).filter(v => v != null && isFinite(v)).sort((x, y) => x - y); return a.length ? (a.length % 2 ? a[(a.length - 1) / 2] : (a[a.length / 2 - 1] + a[a.length / 2]) / 2) : null; };
  const f = (k, v) => k === 'pb' || k === 'pe' ? (v ? num(v, 1) + ' x' : '—') : k === 'dy' ? (v != null ? num(v * 100, 2) + ' %' : '—') : k === 'y' ? (v || '—') : bankFmt(v, BANK_BY[k][2]);
  const best = {}; for (const k of COLS) { const sens = BANK_BY[k][3]; if (!sens) continue; const a = R.filter(r => r[k] != null && isFinite(r[k])).sort((x, y) => (y[k] - x[k]) * sens); if (a.length > 2) best[k] = [a[0].id, a[a.length - 1].id]; }
  const cell = (k, r) => { if (!BANK_BY[k]) return `<td>${f(k, r[k])}</td>`; if (k === 'g_rn' && r.ns) return '<td class="dm" title="Résultat de l’exercice précédent négatif : variation non significative">n.s.</td>'; const c = best[k] ? (best[k][0] === r.id ? 'up' : best[k][1] === r.id ? 'dn' : '') : '', old = r.at[k] && r.at[k] !== r.y; return `<td class="${c}"${old ? ` title="Dernier chiffre publié : exercice ${r.at[k]}"` : ''}>${f(k, r[k])}${old ? ` <span class="dm">(${r.at[k]})</span>` : ''}</td>`; };
  m.innerHTML = `${pn(`Banques cotées · dernier exercice publié · ${R.length} banques`, 'BANK', `<div class="tw" style="max-height:62vh"><table class="t" id="bkT"><thead><tr>${thSort(cols, st.sort)}</tr></thead><tbody>
      ${rows.map(r => `<tr data-sec="${r.id}" data-to="FA"><td class="l nm">${esc(r.short)}</td><td class="l dm">${esc(r.cty)}</td><td>${r.y || '—'}</td>${cols.slice(3).map(([k]) => cell(k, r)).join('')}</tr>`).join('')}
      <tr class="sep2"><td class="l am">Médiane</td><td></td><td></td>${cols.slice(3).map(([k]) => `<td class="am">${f(k, med(k))}</td>`).join('')}</tr></tbody></table></div>`,
    { np: true, lect: 'Dernier exercice publié par chaque banque ; « (2024) » : chiffre de l’exercice indiqué, celui du dernier exercice n’étant pas publié. Montants en milliards de FCFA ; n.s. = variation non significative (résultat précédent négatif). Coefficient d’exploitation et ratio de solvabilité tels que publiés par la banque ; coût du risque rapporté aux crédits à la clientèle de fin d’exercice ; CP / bilan = capitaux propres ÷ total du bilan ; P/B et PER au dernier cours. Vert = meilleure banque de la colonne, rouge = la moins bonne. Clic : analyse financière (FA).' })}
    <div class="grid c2b">${pn('ROE et coefficient d’exploitation', 'BANK', cvb('bkS', 300), { lect: 'Chaque point est une banque : rentabilité des capitaux propres (vertical) et coefficient d’exploitation (horizontal ; à gauche = plus efficace).' })}
      ${pn('PNB du dernier exercice (milliards de FCFA)', 'BANK', cvb('bkP', 300))}</div>`;
  m.querySelectorAll('#bkT th[data-k]').forEach(th => th.onclick = () => { const k = th.dataset.k; st.sort = { k, dir: st.sort.k === k ? -st.sort.dir : -1 }; render(); });
  const P = R.filter(r => r.pnb).sort((a, b) => b.pnb - a.pnb);
  barChart($('bkP'), { labels: P.map(r => r.id), values: P.map(r => r.pnb / 1e3), fmt: v => num(v, 0), pos: CL.amber, extra: i => esc(P[i].short) });
  const S = R.filter(r => r.roe != null && r.cir != null);
  scatterL($('bkS'), { pts: S.map(r => ({ x: r.cir, y: r.roe, id: r.id, label: r.id })), fx: v => num(v * 100, 0) + ' %', fy: v => num(v * 100, 0) + ' %', xlab: 'coefficient d’exploitation', ylab: 'ROE', to: 'FA',
    tipf: p => { const r = S.find(x => x.id === p.id); return `<b>${p.id}</b> ${esc(r ? r.short : '')}<br>ROE ${num(p.y * 100, 1)} % · coefficient ${num(p.x * 100, 1)} %`; } });
};

/* ------------------------------------------------------------------ DIVC : aristocrates du dividende, encaissements
   Dividende net par action tel que publié dans les avis de paiement (ajusté des fractionnements et attributions gratuites ;
   dividendes exceptionnels exclus). Un exercice absent des avis lus interrompt une série : rien n'est supposé. */
function divArist(DV) {
  const yNow = +i2s(Q.sum.asof).slice(0, 4), by = {};
  for (const x of DV) if (x.t && x.ex && x.dps > 0 && !x.exc) { const b = by[x.t] = by[x.t] || {}; b[x.ex] = (b[x.ex] || 0) + x.dps; }
  return secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity').map(s => {
    const d = by[s.id]; if (!d) return null; const ys = Object.keys(d).map(Number).sort((a, b) => a - b), last = ys[ys.length - 1];
    let paid = 0; for (let y = last; d[y]; y--) paid++;
    let noCut = 0; for (let y = last; d[y] && d[y - 1] && d[y] >= d[y - 1] * 0.999; y--) noCut++;
    let up = 0; for (let y = last; d[y] && d[y - 1] && d[y] > d[y - 1] * 1.001; y--) up++;
    const cg = n => d[last] && d[last - n] ? Math.pow(d[last] / d[last - n], 1 / n) - 1 : null;
    return { s, id: s.id, short: s.short || s.n, last, dps: d[last], fresh: last >= yNow - 2, paid, since: last - paid + 1, noCut, up, g5: cg(5), g10: cg(10), yld: s.yld, payout: +s.dps_ex === last ? payR(s) : null, first: ys[0] };
  }).filter(Boolean);
}
async function divcAristocrates(m, alive) {
  setTitle('Dividend Aristocrats');
  const DV = await getJSON('dividends.json').catch(() => null); if (!alive()) return;
  if (!Array.isArray(DV)) { m.innerHTML = pn('Aristocrates du dividende', 'DIVC', '<div class="empty">Dividendes indisponibles pour le moment.</div>'); return; }
  const st = ST.dvA = ST.dvA || { sort: { k: 'noCut', dir: -1 } };
  const A = divArist(DV), rows = sortRows(A, st.sort);
  const tier = r => !r.fresh ? ['Série arrêtée', 'dm'] : r.noCut >= 10 ? ['Aristocrate (10 ans et plus)', 'up'] : r.noCut >= 5 ? ['Régulier (5 ans et plus)', 'am'] : ['', ''];
  const cols = [['id', 'Titre', 1], ['short', 'Société', 1], ['last', 'Dernier ex.'], ['dps', 'Dernier div. net'], ['paid', 'Années versées'], ['noCut', 'Années sans baisse'], ['up', 'Hausses de suite'], ['g5', 'Croiss. 5 ans'], ['g10', 'Croiss. 10 ans'], ['yld', 'Rendement'], ['payout', 'Distribution']];
  const top = A.filter(r => r.fresh && r.noCut > 0).sort((a, b) => b.noCut - a.noCut || b.paid - a.paid).slice(0, 12);
  const nA = A.filter(r => r.fresh && r.noCut >= 10).length, nR = A.filter(r => r.fresh && r.noCut >= 5 && r.noCut < 10).length;
  m.innerHTML = `${pn(`Aristocrates du dividende · BRVM · ${nA} aristocrate${nA > 1 ? 's' : ''}, ${nR} régulier${nR > 1 ? 's' : ''}`, 'DIVC', `<div class="tw" style="max-height:62vh"><table class="t" id="daT"><thead><tr>${thSort(cols, st.sort)}<th class="l">Statut</th></tr></thead><tbody>
      ${rows.map(r => { const [tl, tc] = tier(r); return `<tr data-sec="${r.id}" data-to="DVD"><td class="l tk">${r.id}</td><td class="l nm">${esc(r.short)}</td><td>${r.last}</td><td class="wh">${num(r.dps, 2)}</td><td>${r.paid} <span class="dm">(depuis ${r.since})</span></td><td class="wh">${r.noCut}</td><td>${r.up}</td><td>${r.g5 != null ? pc(r.g5, 1) + ' /an' : '—'}</td><td>${r.g10 != null ? pc(r.g10, 1) + ' /an' : '—'}</td><td>${r.yld != null ? num(r.yld * 100, 2) + ' %' : '—'}</td><td>${r.payout ? num(r.payout * 100, 0) + ' %' : '—'}</td><td class="l ${tc}">${tl}</td></tr>`; }).join('')}</tbody></table></div>`,
      { np: true, lect: 'Années versées = exercices consécutifs avec un dividende, en remontant depuis le dernier ; années sans baisse = exercices consécutifs où le dividende net par action n’a pas baissé par rapport à l’exercice précédent ; hausses de suite = exercices consécutifs en hausse. Dividende net par action publié dans les avis de paiement, ajusté des fractionnements et attributions gratuites ; dividendes exceptionnels exclus ; acompte et solde d’un même exercice additionnés. Un exercice absent des avis lus interrompt la série. « Série arrêtée » : aucun dividende pour les deux derniers exercices. Rendement au dernier cours (dernier dividende récent seulement). Clic : historique des dividendes (DVD).' })}
    ${pn('Les plus réguliers (séries en cours)', 'DIVC', cvb('daC', 240), { lect: 'Nombre d’exercices consécutifs sans baisse du dividende net par action.' })}`;
  m.querySelectorAll('#daT th[data-k]').forEach(th => th.onclick = () => { const k = th.dataset.k; st.sort = { k, dir: st.sort.k === k ? -st.sort.dir : -1 }; render(); });
  barChart($('daC'), { labels: top.map(r => r.id), values: top.map(r => r.noCut), fmt: v => num(v, 0), pos: CL.amber, labelsOnBars: true, extra: i => `${esc(top[i].short)} · ${top[i].paid} années versées` });
}
/* brut et taux de l'impôt (IRVM, personnes physiques) tels qu'écrits dans l'avis de paiement ; rien d'estimé quand l'avis ne les donne pas */
const brutC = x => x.brut ? `<td>${num(x.brut, 2)}</td><td>${num(x.irvm, x.irvm % 1 ? 1 : 0)} %</td>` : '<td class="dm" title="brut non indiqué dans l’avis (montant net seulement)">—</td><td class="dm">—</td>';
/* retenue à la source sur les dividendes des sociétés cotées, par pays de la société (taux légaux lus sur les textes officiels,
   data/retenues.json) ; un pays dont le texte en vigueur n'a pas été lu n'est pas listé */
const retenuesP = RT => { const L = RT && Array.isArray(RT.rows) ? RT.rows.filter(r => r && r.nom && r.pp != null) : []; if (!L.length) return '';
  const tx = v => v == null ? '<span class="dm">—</span>' : num(v, v % 1 ? 1 : 0) + ' %';
  return pn('Retenue à la source sur les dividendes, par pays', 'DIVC', `<div class="tw"><table class="t"><thead><tr><th class="l">Pays de la société</th><th>Personnes physiques</th><th>Personnes morales</th></tr></thead><tbody>${L.map(r => `<tr><td class="l wh">${esc(r.nom)}</td><td class="wh">${tx(r.pp)}</td><td class="wh">${tx(r.pm)}</td></tr><tr><td class="l dm" colspan="3" style="white-space:normal;padding-bottom:6px">${esc(r.texte || '')}</td></tr>`).join('')}</tbody></table></div>`,
    { np: true, lect: `Taux légaux de l’impôt retenu par la société sur les dividendes qu’elle verse, selon le pays où elle a son siège, lus sur le code des impôts publié par l’administration fiscale du pays ou sur l’avis de paiement de la BRVM (vérifiés le ${fds(RT.d)}). Le taux réellement appliqué à un paiement est celui de l’avis de la société (conventions fiscales, régimes particuliers). Pays absents : taux en vigueur pas encore vérifié sur le texte officiel ; rien n’est estimé.` }); };
async function divcEncaissements(m, alive) {
  setTitle('Dividend Income Calendar');
  const [DV, RT] = await Promise.all([getJSON('dividends.json').catch(() => null), getJSON('retenues.json').catch(() => null)]); if (!alive()) return;
  if (!Array.isArray(DV)) { m.innerHTML = pn('Dividende net et encaissements', 'DIVC', '<div class="empty">Dividendes indisponibles pour le moment.</div>'); return; }
  const today = i2s(Q.sum.asof), P = portLoad(), pos = new Map((P.pos || []).filter(p => Q.by[p.id] && Q.by[p.id].mkt === 'BRVM' && p.q > 0).map(p => [p.id, p.q]));
  const up = DV.filter(x => x.pay && x.pay >= today && x.dps > 0).sort((a, b) => a.pay.localeCompare(b.pay) || a.t.localeCompare(b.t));
  const y1 = `${+today.slice(0, 4) - 1}${today.slice(4)}`, past = DV.filter(x => x.pay && x.pay >= y1 && x.pay < today && x.dps > 0).sort((a, b) => b.pay.localeCompare(a.pay));
  const mine = x => pos.has(x.t) && (!x.det || x.det > today) ? pos.get(x.t) * x.dps : null;
  const tot = up.reduce((t, x) => t + (mine(x) || 0), 0), nMine = up.filter(x => mine(x) != null).length;
  const mo = {}; for (const x of up) { const k = x.pay.slice(0, 7); const o = mo[k] = mo[k] || { n: 0, v: 0 }; o.n++; o.v += mine(x) || 0; }
  const MK = Object.keys(mo).sort();
  const row = (x, fut) => { const s = sec(x.t), q = pos.get(x.t), det = x.det && x.det <= today, v = fut ? mine(x) : null;
    return `<tr data-sec="${x.t}" data-to="DVD"><td class="l">${fds(x.pay)}</td><td class="l tk">${x.t}</td><td class="l nm">${esc(s ? s.short || s.n : '')}</td><td>${x.ex || '—'}</td><td class="wh">${num(x.dps, 2)}</td>${brutC(x)}<td class="l${fut && det ? ' dm' : ''}"${fut && det ? ' title="Déjà détaché : seuls les détenteurs de la veille du détachement reçoivent ce dividende"' : ''}>${fds(x.det)}</td><td>${s && s.last ? num(x.dps / s.last * 100, 2) + ' %' : '—'}</td>${fut ? `<td>${q ? num(q, q % 1 ? 2 : 0) : '—'}</td><td class="wh">${v != null ? num(v, 0) : q && det ? '<span class="dm">déjà détaché</span>' : '—'}</td>` : ''}</tr>`; };
  m.innerHTML = `<div class="grid c2">${pn('À encaisser', 'DIVC', `<div class="kv2"><span>Paiements annoncés à venir</span><b>${up.length}</b><span>Pour vos positions BRVM (PORTF)</span><b class="wh">${pos.size ? (nMine ? num(tot, 0) + ' FCFA nets · ' + nMine + ' paiement' + (nMine > 1 ? 's' : '') : 'aucun paiement annoncé') : 'aucune position saisie'}</b></div>`,
      { lect: 'Dividende net par action : montant versé après l’impôt retenu à la source par la société, tel que publié dans l’avis de paiement. Brut et retenue : montant avant impôt et taux de l’impôt sur le revenu des valeurs mobilières pour les personnes physiques, seulement quand l’avis ou le calendrier officiel les indique (sinon « — », rien n’est estimé ; le taux des personnes morales peut être plus bas). Vos montants = nombre de titres × dividende net, pour les paiements annoncés dont le détachement est à venir (il faut détenir le titre la veille du détachement). Les positions viennent de PORTF et restent dans ce navigateur. Aucun dividende futur non annoncé n’est compté.' })}
    ${pn('Paiements annoncés par mois', 'DIVC', MK.length ? cvb('deM', 200) : '<div class="empty">Aucun paiement annoncé.</div>', { lect: pos.size ? 'Barres : montant net à encaisser pour vos positions ; infobulle : nombre de paiements.' : 'Barres : nombre de sociétés qui paient. Saisissez vos positions dans PORTF pour voir vos montants.' })}</div>
    ${pn('Calendrier des paiements annoncés', 'DIVC', `<div class="tw" style="max-height:50vh"><table class="t"><thead><tr><th class="l">Paiement</th><th class="l">Titre</th><th class="l">Société</th><th>Exercice</th><th>Net / titre</th><th>Brut / titre</th><th>Retenue</th><th class="l">Détachement</th><th>Rdt au cours</th><th>Vos titres</th><th>Vous recevez (FCFA)</th></tr></thead><tbody>${up.map(x => row(x, true)).join('') || '<tr><td class="l dm" colspan="11">Aucun paiement annoncé après le ' + fds(today) + '.</td></tr>'}</tbody></table></div>`, { np: true })}
    ${pn(`Paiements des 12 derniers mois · ${past.length}`, 'DIVC', `<div class="tw" style="max-height:40vh"><table class="t"><thead><tr><th class="l">Paiement</th><th class="l">Titre</th><th class="l">Société</th><th>Exercice</th><th>Net / titre</th><th>Brut / titre</th><th>Retenue</th><th class="l">Détachement</th><th>Rdt au cours</th></tr></thead><tbody>${past.map(x => row(x, false)).join('') || '<tr><td class="l dm" colspan="9">Aucun paiement.</td></tr>'}</tbody></table></div>`, { np: true, lect: 'Rendement rapporté au cours actuel.' })}
    ${retenuesP(RT)}`;
  if (MK.length) barChart($('deM'), { labels: MK.map(mLab), values: MK.map(k => pos.size ? mo[k].v : mo[k].n), fmt: v => num(v, 0), pos: CL.amber, labelsOnBars: true, extra: i => `${mo[MK[i]].n} paiement${mo[MK[i]].n > 1 ? 's' : ''}` });
}
const PAGES_DIVC_BASE = PAGES.DIVC;
PAGES.DIVC = async (m, alive) => {
  const tab = tabState('DIVC', 'c'); setTabs(FN_TABS.DIVC, tab, k => { ST.tab.DIVC = k; render(); });
  if (tab === 'a') return divcAristocrates(m, alive);
  if (tab === 'n') return divcEncaissements(m, alive);
  return PAGES_DIVC_BASE(m, alive);
};
