/* ================= FQT — fonctions d'un titre : FA, RV, WACC, DVD, DDM, COMP, BETA, HP, CN ================= */

/* comptes publiés : seulement pour les actions (ni ETF, ni indice, ni Taïwan, dont les comptes ne sont pas collectés) */
const faJSON = id => { const s = Q.by[id]; if (s && (s.cls !== 'Equity' || s.typ === 'ETF' || s.mkt === 'TW' || (s.mkt === 'US' && !s.fa))) return Promise.reject(new Error('comptes non collectés')); return getJSON('fa/' + id.replace('.', '_') + '.json'); };
const P1 = (v, d = 1) => v == null || !isFinite(v) ? '—' : num(v * 100, d) + ' %';
const NDc = (why = '') => `<span class="dm" title="${esc(why)}">n.d.</span>`;
const yLab = d => String(Math.floor(d / 10000));
const isBRVM = s => s && s.mkt === 'BRVM';
/* indice de référence d'un titre : jamais le titre lui-même (BRVMC → BRVM 30, SPY → QQQ) */
const benchFor = s => [s.bench, isBRVM(s) ? 'BRVMC' : 'SPY', isBRVM(s) ? 'BRVM30' : 'QQQ', 'QQQ', 'SPY'].find(id => id && id !== s.id && Q.by[id]) || 'QQQ';
/* montant échangé du jour : officiel (bulletin de la cote) ou estimation volume × cours, signalée « ≈ » */
const valEst = s => !!s && (s.mkt !== 'BRVM' || !!s.vde);
const valTxt = (s, v) => v ? `${valEst(s) ? '<span class="dm" title="Estimation en séance : volume × cours ; montant définitif le soir.">≈</span> ' : ''}${big(v)}` : '—';
/* Unités des comptes : US en millions de dollars, BRVM en milliards de FCFA (sources en millions). */
const unitOf = F => F.mkt === 'BRVM' ? { k: 1e-3, lab: 'Md FCFA', d: 1 } : { k: 1e-6, lab: 'M$', d: 0 };
function gr(a, i) { const p = a[i - 1], c = a[i]; return p != null && c != null && p > 0 ? c / p - 1 : null; }
function cagrA(a, n) { const idx = a.map((v, i) => v != null ? i : -1).filter(i => i >= 0); if (!idx.length) return null; const L = idx[idx.length - 1], j = L - n; if (j < 0 || a[j] == null || a[j] <= 0 || a[L] <= 0) return null; return Math.pow(a[L] / a[j], 1 / n) - 1; }

/* Lignes du tableau des comptes (clé, libellé, type). Types : m montant, p ratio (0-1), q pourcentage déjà en %, x multiple, e par action, s actions, g croissance de la ligne précédente. */
function accRows(F) {
  if (F.mkt === 'US') return [['rev', 'Chiffre d’affaires', 'm'], ['rev', 'croissance', 'g'], ['gm', 'Marge brute', 'p'], ['ebitda', 'EBITDA', 'm'], ['opi', 'Résultat d’exploitation', 'm'], ['om', 'Marge d’exploitation', 'p'],
    ['ni', 'Résultat net', 'm'], ['nm', 'Marge nette', 'p'], ['eps', 'BPA dilué ($)', 'e'], ['eps', 'croissance', 'g'], ['ocf', 'Flux de trésorerie d’exploitation', 'm'], ['capex', 'Investissements (capex)', 'm'],
    ['fcf', 'Free cash-flow', 'm', 'hl'], ['fcfm', 'Marge FCF', 'p'], ['fcf', 'croissance FCF', 'g'], ['sbc', 'Rémunération en actions', 'm'], ['div', 'Dividendes versés', 'm'], ['buy', 'Rachats d’actions', 'm'],
    ['cashx', 'Trésorerie et placements', 'm'], ['debt', 'Dette financière', 'm'], ['nd', 'Dette nette', 'm'], ['eq', 'Capitaux propres', 'm'], ['roe', 'ROE', 'p'], ['roic', 'ROIC (impôt 21 %)', 'p'], ['sh', 'Actions diluées (millions)', 's']];
  if (F.bank) return [['rev', 'Produit net bancaire', 'm'], ['rev', 'croissance', 'g'], ['ni', 'Résultat net', 'm'], ['nm', 'Marge nette', 'p'], ['eps', 'BNPA (FCFA)', 'e'], ['eps', 'croissance', 'g'],
    ['dps', 'Dividende net / action (FCFA)', 'e'], ['payout', 'Taux de distribution', 'p'], ['eq', 'Capitaux propres', 'm'], ['assets', 'Total bilan', 'm'], ['deposits', 'Dépôts de la clientèle', 'm'], ['loans', 'Crédits à la clientèle', 'm'],
    ['ld', 'Crédits / dépôts', 'p'], ['cir', 'Coefficient d’exploitation', 'q'], ['cor', 'Coût du risque', 'm'], ['cor_l', 'Coût du risque / crédits', 'p'], ['roe', 'ROE', 'p'], ['roa_s', 'ROA', 'q'], ['solv', 'Ratio de solvabilité', 'q']];
  return [['rev', 'Chiffre d’affaires', 'm'], ['rev', 'croissance', 'g'], ['ebitda', 'Excédent brut d’exploitation (EBE)', 'm'], ['ebit', 'Résultat d’exploitation', 'm'], ['om', 'Marge d’exploitation', 'p'], ['ni', 'Résultat net', 'm'], ['nm', 'Marge nette', 'p'],
    ['eps', 'BNPA (FCFA)', 'e'], ['eps', 'croissance', 'g'], ['dps', 'Dividende net / action (FCFA)', 'e'], ['payout', 'Taux de distribution', 'p'], ['ocf', 'Flux de trésorerie d’exploitation', 'm'], ['capex', 'Investissements (capex)', 'm'],
    ['fcf', 'Free cash-flow', 'm', 'hl'], ['fcfm', 'Marge FCF', 'p'], ['fcf', 'croissance FCF', 'g'], ['fpay', 'Dividendes / FCF', 'p'], ['eq', 'Capitaux propres', 'm'], ['nd', 'Dette nette', 'm'], ['cash', 'Trésorerie', 'm'],
    ['assets', 'Total bilan', 'm'], ['roe', 'ROE', 'p'], ['roic', 'ROIC (impôt légal)', 'p'], ['nd_ebitda', 'Dette nette / EBE', 'x']];
}
function yDerived(F) {
  const Y = F.Y, n = Y.y.length, dv = (a, b) => a.map((v, i) => v != null && b[i] ? v / b[i] : null);
  if (F.mkt === 'US') { Y.gm = Y.gm && Y.gm.length ? dv(Y.gp, Y.rev) : Y.gm; Y.om = dv(Y.opi, Y.rev); Y.nm = dv(Y.ni, Y.rev); Y.fcfm = dv(Y.fcf, Y.rev); if (!Y.cashx) Y.cashx = new Array(n).fill(null); }
  return Y;
}
function cellFmt(t, v, U) {
  if (v == null || !isFinite(v)) return null;
  return t === 'm' ? num(v * U.k, U.d) : t === 'p' ? num(v * 100, 1) : t === 'q' ? num(v, 1) : t === 'x' ? num(v, 2) : t === 'e' ? num(v, 2) : t === 's' ? num(v / 1e6, 0) : num(v, 2);
}
/* Tableau des comptes sur N exercices (10 par défaut), colonnes manquantes marquées n.d. avec la raison. */
function accountsTable(F, nY = 10, opts = {}) {
  const Y = yDerived(F), U = unitOf(F), rows = accRows(F);
  const have = Y.y.filter((y, i) => rows.some(([k]) => Y[k] && Y[k][i] != null)).map(y => F.mkt === 'US' ? Math.floor(y / 10000) : y);
  const last = have.length ? Math.max(...have) : new Date().getFullYear() - 1; const cols = []; for (let y = last - nY + 1; y <= last; y++) cols.push(y);
  const ix = y => Y.y.indexOf(F.mkt === 'US' ? Y.y.find(d => Math.floor(d / 10000) === y) : y);
  const firstData = have.length ? Math.min(...have) : null;
  const why = y => F.mkt === 'BRVM' ? (firstData && y < firstData ? `aucun compte disponible avant ${firstData}` : 'non publié') : 'absent des comptes publiés';
  const cg = (k, n) => { const a = cols.map(y => { const i = ix(y); return i >= 0 ? Y[k][i] : null; }); return cagrA(a, n); };
  const srcOf = y => { const i = ix(y); return i >= 0 && Y.src ? Y.src[i] : null; };
  /* en-tête sur deux lignes comme FA : « FY 2024 » puis la date de clôture de l'exercice (quand la source la donne) */
  const endOf = y => { const i = ix(y); return i >= 0 && F.mkt === 'US' && Y.y[i] > 99999 ? fd(Y.y[i]) : ''; };
  const srMark = sr => !sr ? ['', ''] : /^référentiel/.test(sr) ? ['r', 'Comptes publiés dans l’autre ' + sr] : /^converti/.test(sr) ? ['$', sr.replace(/^converti : /, 'Montants convertis : ')] : ['a', 'Exercice complété à partir des comptes publiés de la société'];
  const head = `<tr><th class="l">${U.lab}</th>${cols.map(y => { const [m, ti] = srMark(srcOf(y)); return `<th title="${esc(ti)}">FY ${y}${m ? `<sup class="am">${m}</sup>` : ''}</th>`; }).join('')}${opts.cagr ? '<th class="tc" title="taux de croissance annuel moyen sur 3 ans">TCAM<br>3 ans</th><th class="tc" title="taux de croissance annuel moyen sur 5 ans">TCAM<br>5 ans</th><th class="tc" title="taux de croissance annuel moyen sur 10 ans">TCAM<br>10 ans</th>' : ''}</tr>`
    + (F.mkt === 'US' ? `<tr class="h2"><th class="l">12 mois clos le</th>${cols.map(y => `<th>${endOf(y)}</th>`).join('')}${opts.cagr ? '<th></th><th></th><th></th>' : ''}</tr>` : '');
  const body = rows.filter(([k]) => Y[k] && (!opts.only || opts.only.has(k))).map(([k, l, t, hl]) => {
    const vals = cols.map(y => { const i = ix(y); if (i < 0) return null; return t === 'g' ? gr(Y[k], i) : Y[k][i]; });
    if (vals.every(v => v == null) && t !== 'g') return '';
    const tds = vals.map((v, j) => { if (v == null) return `<td>${NDc(why(cols[j]))}</td>`; if (t === 'g') return `<td>${sgn(v, 1)}</td>`; return `<td class="${hl ? 'yl' : 'wh'}">${cellFmt(t, v, U)}</td>`; }).join('');
    const cc = opts.cagr && ['m', 'e'].includes(t) ? [3, 5, 10].map(n => `<td>${sgn(cg(k, n), 1)}</td>`).join('') : opts.cagr ? '<td></td><td></td><td></td>' : '';
    const gfk = t !== 'g' && typeof GF_M !== 'undefined' && GF_M.some(x => x[0] === k) ? k : null;
    return `<tr class="${t === 'g' ? 'sub' : ''}"><td class="l ${t === 'g' ? 'dm' : 'am'}">${gfk ? `<i class="gfi" data-gf="${gfk}" title="Graphique de cette ligne (GF)">${GF_ICO}</i>` : '<i class="gfi0"></i>'}${t === 'g' ? '&nbsp;&nbsp;' + l : l}${t === 'p' || t === 'q' ? ' %' : ''}</td>${tds}${cc}</tr>`;
  }).join('');
  return `<div class="tw"><table class="t acc"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
}
function faSrcNote(F) {
  return F.mkt === 'US' ? `Comptes publiés (${F.annual_only ? 'rapports annuels' : 'rapports annuels et trimestriels'}), devise ${F.ccy || 'USD'}. FCF = flux d’exploitation − acquisitions d’immobilisations corporelles. Dette financière hors obligations locatives.`
    : `Millions de FCFA. <sup class="am">a</sup> = exercice présenté d’après ses chiffres clés publiés ; <sup class="am">r</sup> = comptes publiés dans l’autre norme (SYSCOHADA ou IFRS).${F.Y && F.Y.src && F.Y.src.some(x => /^converti/.test(x || '')) ? ' <sup class="am">$</sup> = comptes publiés en dollars US, convertis en FCFA (cours au survol de l’année).' : ''} FCF = flux d’exploitation − acquisitions d’immobilisations.${F.bank ? ' Banque : pas de FCF ni de valeur d’entreprise.' : ''}`;
}

/* Comptes publiés détaillés (BRVM) : postes des états financiers et ratios, sur tous les exercices lus.
   Années continues : un exercice sans comptes lisibles reste visible (n.d.). Montants en millions de FCFA. */
function cptYears(F, all) { const ys = F.C.y; if (!ys.length) return []; const hi = ys[ys.length - 1], lo = all ? ys[0] : Math.max(ys[0], hi - 9); const o = []; for (let y = lo; y <= hi; y++) o.push(y); return o; }
/* exercices et lignes sans aucun chiffre : masqués (« 10 derniers » = les 10 derniers exercices qui ont des chiffres) */
function cptKeep(rows, years, ix, all) { const V = r => Array.isArray(r[2]) ? r[2] : r[3], ok = (r, y) => { const i = ix(y); return i >= 0 && V(r)[i] != null && isFinite(V(r)[i]); };
  let cols = years.filter(y => rows.some(r => ok(r, y))); if (!all) cols = cols.slice(-10); return { cols, rows: rows.filter(r => cols.some(y => ok(r, y))) }; }
function cptTable(F, sk, all) {
  const S = (F.C.s || []).find(x => x[0] === sk || x[0] === 'b' + sk); if (!S) return '<div class="empty">Poste non disponible dans les comptes lus.</div>';
  const ix = y => F.C.y.indexOf(y), K = cptKeep(S[2], F.C.y, ix, all), cols = K.cols;
  if (!cols.length) return '<div class="empty">Aucun chiffre publié pour cet état.</div>';
  const fxT = y => { const q = F.C.fx && F.C.fx[y]; return q ? `Comptes publiés en dollars US, convertis au cours de 1 USD = ${num(q[0], 2)} FCFA du ${q[1] ? fds(q[1]) : '—'} (date de publication)` : ''; };
  const head = `<tr><th class="l">M FCFA</th>${cols.map(y => `<th${fxT(y) ? ` title="${esc(fxT(y))}"` : ''}>FY ${y}${fxT(y) ? '<sup class="am">$</sup>' : ''}</th>`).join('')}</tr>`;
  const strong = new Set(['chiffre_affaires', 'b_pnb', 'valeur_ajoutee', 'ebe', 'resultat_exploitation', 'b_rbe', 'rao', 'resultat_net', 'actif_immobilise', 'actif_circulant', 'total_actif', 'capitaux_propres', 'passif_circulant', 'total_passif', 'cafg', 'flux_operationnels']);
  const body = K.rows.map(([k, lab, vals, cx]) => `<tr><td class="l ${strong.has(k) ? 'yl' : 'am'}">${esc(lab)}</td>${cols.map(y => { const i = ix(y), v = i >= 0 ? vals[i] : null;
    return v == null ? `<td>${NDc('poste non publié pour cet exercice')}</td>` : `<td class="${strong.has(k) ? 'yl' : 'wh'}${cx && cx.includes(i) ? ' cx' : ''}"${cx && cx.includes(i) ? ' title="Total recalculé à partir des postes publiés de l’exercice"' : ''}>${num(v, Math.abs(v) < 100 ? 1 : 0)}</td>`; }).join('')}</tr>`).join('');
  return `<div class="tw"><table class="t acc"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
}
function ratioFmt(f, v) { if (v == null || !isFinite(v)) return null; return f === 'p' ? num(v * 100, 1) + ' %' : f === 'x' ? num(v, 2) + ' x' : f === 'j' ? num(v, 0) + ' j' : f === 'm' ? num(v, 0) : f === 'e' ? num(v, Math.abs(v) < 100 ? 2 : 0) : num(v, 2); }
function ratioTable(F, all) {
  const R = F.R; if (!R || !R.g || !R.g.length) return '<div class="empty">Ratios non calculables (comptes insuffisants).</div>';
  const ix = y => R.y.indexOf(y), allRows = R.g.flatMap(([g, rows]) => rows), cols = cptKeep(allRows, R.y, ix, all).cols; let n = 0;
  const live = r => cols.some(y => { const i = ix(y), v = i >= 0 ? r[3][i] : null; return v != null && isFinite(v); });
  const kf = new Set(R.k || []), head = `<tr><th class="l">Ratio</th>${cols.map(y => `<th>FY ${y}${kf.has(y) ? '<sup>a</sup>' : ''}</th>`).join('')}</tr>`;
  const body = R.g.map(([g, rows0]) => { const rows = rows0.filter(live); return rows.length ? `<tr class="sec"><td class="l" colspan="${cols.length + 1}">${esc(g)}</td></tr>` + rows.map(([k, lab, f, vals]) => { n++;
    return `<tr><td class="l am">${esc(lab)}${f === 'm' ? ' <span class="dm">(M FCFA)</span>' : ''}</td>${cols.map(y => { const i = ix(y), t = i >= 0 ? ratioFmt(f, vals[i]) : null; return `<td class="${t == null ? '' : (f === 'p' && vals[i] < 0) || (f === 'm' && vals[i] < 0) ? 'dn' : 'wh'}">${t == null ? '<span class="dm">—</span>' : t}</td>`; }).join('')}</tr>`; }).join('') : ''; }).join('');
  return { html: `<div class="tw"><table class="t acc"><thead>${head}</thead><tbody>${body}</tbody></table></div>`, n };
}

/* ------------------------------------------------------------------ FA */
PAGES.FA = async (m, alive) => {
  const s = sec(ST.sec); const F = await faJSON(s.id).catch(() => null); if (!alive()) return;
  if (!F) { m.innerHTML = pn(s.tk + ' · analyse financière', 'FA', '<div class="empty">Comptes non disponibles pour ce titre.</div>'); return; }
  const st = ST.fa = ST.fa || { v: 'A' }; const qtr = F.mkt === 'US' && F.H && F.H.q && F.H.q.length > 4 && !F.annual_only; if (!qtr) st.v = 'A';
  const Y = yDerived(F), U = unitOf(F), x = Y.y.map(y => F.mkt === 'US' ? y : y * 10000 + 1231);
  const kpi = [['Chiffre d’affaires', F.mkt === 'US' ? 'rev_g' : 'rev_g', 'croissance sur 1 an'], ['Free cash-flow', 'fcf_g', 'croissance sur 1 an'], ['Marge FCF', 'fcfm', ''], ['ROE', 'roe', ''], ['ROIC', 'roic', ''], ['Dette nette / EBITDA', 'nd_ebitda', '']];
  const tab = tabState('FA', 'k'); setTabs([['k', 'Chiffres clés'], ['is', 'Compte de résultat'], ['bs', 'Bilan'], ['cf', 'Flux de trésorerie'], ['r', 'Ratios']], tab, k => { ST.tab.FA = k; render(); });
  setActs([{ n: 97, l: 'Sortie', menu: () => [{ l: 'Exporter le tableau (CSV)', run: exportCSV }, { l: 'Imprimer / PDF', run: () => window.print() }] }]);
  if (tab !== 'k' && isBRVM(F) && F.C && F.C.y && F.C.y.length) {
    const refL = C => `${C.per === 'conso' ? 'Consolidés' : 'Sociaux'} ${C.std === 'ifrs' ? 'IFRS' : 'SYSCOHADA'}`;
    const F0 = F, useAlt = !!(st.alt && F.C2 && tab !== 'r'), Fv = useAlt ? Object.assign({}, F, { C: F.C2 }) : F;
    const all = !!st.all, y0 = Fv.C.y[0], per = Fv.C.per === 'conso' ? 'consolidés' : 'sociaux', std = Fv.C.std === 'ifrs' ? 'IFRS' : 'SYSCOHADA';
    const tools = `<div class="tools" style="border:1px solid var(--line2)"><span class="tlab">Exercices</span><button class="tb ${all ? '' : 'on'}" data-all="0">10 derniers</button><button class="tb ${all ? 'on' : ''}" data-all="1">Tout l’historique (depuis ${y0})</button>${F0.C2 && tab !== 'r' ? `<span class="tlab" style="margin-left:14px">Comptes</span><button class="tb ${useAlt ? '' : 'on'}" data-alt="0">${refL(F0.C)}</button><button class="tb ${useAlt ? 'on' : ''}" data-alt="1">${refL(F0.C2)}</button>` : ''}</div>`;
    const lect = `Comptes ${per} (${std}), en millions de FCFA.${Fv.C.fx ? ' <sup class="am">$</sup> = comptes publiés en dollars US, convertis en FCFA (cours et date au survol de l’année).' : ''}`;
    if (tab === 'r') { const T = ratioTable(F, all); m.innerHTML = tools + pn(`${esc(s.tk)} · ${T.n || ''} ratios calculés sur les comptes publiés`, 'FA', T.html || T, { np: true, lect: '<sup>a</sup> = ratios de l’exercice calculés sur ses chiffres clés publiés. Moyennes = (début + fin d’exercice) / 2 ; PER et rendement au dernier cours de chaque exercice. ' + lect }); }
    else { const lab = { is: 'Compte de résultat', bs: 'Bilan', cf: 'Flux de trésorerie' }[tab]; m.innerHTML = tools + pn(`${esc(s.tk)} · ${lab} · comptes publiés`, 'FA', cptTable(Fv, tab, all), { np: true, lect }); }
    m.querySelectorAll('[data-all]').forEach(b => b.onclick = () => { st.all = b.dataset.all === '1'; render(); });
    m.querySelectorAll('[data-alt]').forEach(b => b.onclick = () => { st.alt = b.dataset.alt === '1'; render(); });
    return; }
  if (tab !== 'k') { const ONLY = F.bank ? { is: ['rev', 'ni', 'nm', 'eps', 'dps', 'payout', 'cir', 'cor'], bs: ['eq', 'assets', 'deposits', 'loans', 'ld', 'solv'], cf: ['dps', 'payout'], r: ['roe', 'roa_s', 'nm', 'ld', 'cir', 'cor_l', 'solv', 'payout'] }[tab]
      : { is: ['rev', 'gm', 'ebitda', 'opi', 'ebit', 'om', 'ni', 'nm', 'eps', 'dps', 'payout'], bs: ['cashx', 'cash', 'debt', 'nd', 'eq', 'assets', 'sh'], cf: ['ocf', 'capex', 'fcf', 'fcfm', 'sbc', 'div', 'buy', 'fpay'], r: ['om', 'nm', 'fcfm', 'roe', 'roic', 'nd_ebitda', 'payout', 'fpay'] }[tab];
    const lab = { is: 'Compte de résultat', bs: 'Bilan', cf: 'Flux de trésorerie', r: 'Ratios' }[tab];
    m.innerHTML = `${subTabs([['A', 'Annuel']], 'A', 'data-v')}${pn(`${esc(s.tk)} · ${lab} · 10 exercices`, 'FA', accountsTable(F, 10, { cagr: tab !== 'r', only: new Set(ONLY) }), { np: true, lect: faSrcNote(F) + (F.bank && tab === 'cf' ? ' Banques : pas de tableau de flux exploitable dans les sources (le passif est l’outil de production).' : '') })}`;
    return; }
  const tools = qtr ? `<span class="tlab">Vue</span><button class="tb ${st.v === 'A' ? 'on' : ''}" data-v="A">Annuelle (10 exercices)</button><button class="tb ${st.v === 'Q' ? 'on' : ''}" data-v="Q">Trimestrielle (12 mois glissants)</button>` : '<span class="tlab">Vue annuelle' + (F.mkt === 'BRVM' ? ' · les sociétés BRVM publient des comptes annuels (et semestriels non publiés)' : '') + '</span>';
  const kv = `<div class="kv2">${[['Exercice de référence', F.fy || (F.asof_q ? fd(F.asof_q) : '—')], ['Croissance du CA', pc(F.rev_g, 1)], ['Croissance du résultat', pc(F.ni_g, 1)], ['Croissance du BPA', pc(F.eps_g, 1)], ['Croissance du FCF', pc(F.fcf_g, 1)],
    ['TCAM CA 3 / 5 / 10 ans', `${P1(F.rev_cagr3)} · ${P1(F.rev_cagr5)} · ${P1(F.rev_cagr10)}`], ['TCAM FCF 3 / 5 / 10 ans', `${P1(F.fcf_cagr3)} · ${P1(F.fcf_cagr5)} · ${P1(F.fcf_cagr10)}`], ['TCAM BPA 3 / 5 / 10 ans', `${P1(F.eps_cagr3)} · ${P1(F.eps_cagr5)} · ${P1(F.eps_cagr10)}`],
    ['Marge d’exploitation', P1(F.om)], ['Marge FCF', P1(F.fcfm)], ['FCF / résultat net', F.conv != null ? num(F.conv, 2) + ' x' : '—'], ['ROE', P1(F.roe)], ['ROIC', P1(F.roic)], ['Dette nette / EBITDA', F.nd_ebitda != null ? num(F.nd_ebitda, 2) + ' x' : '—'],
    ['Score de Piotroski', F.fscore != null ? `${F.fscore} / ${F.fscore_n} critères` : '—'], F.altz != null ? ['Z d’Altman', num(F.altz, 2) + (F.altz < 1.8 ? ' <span class="dn">zone de détresse</span>' : F.altz > 3 ? ' <span class="up">zone saine</span>' : ' zone grise')] : null].filter(Boolean).map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join('')}</div>`;
  let main;
  if (st.v === 'Q') {
    const H = F.H, n = H.q.length, k0 = Math.max(0, n - 12), qs = H.q.slice(k0);
    const R = [['rev', 'Chiffre d’affaires (12 m.)', 'm'], ['ebitda', 'EBITDA', 'm'], ['ni', 'Résultat net', 'm'], ['eps', 'BPA (12 m.)', 'e'], ['ocf', 'Flux d’exploitation', 'm'], ['capex', 'Capex', 'm'], ['fcf', 'Free cash-flow', 'm'], ['sbc', 'Rémunération en actions', 'm'], ['nd', 'Dette nette', 'm'], ['roe', 'ROE', 'p'], ['roic', 'ROIC', 'p']];
    main = `<div class="tw"><table class="t acc"><thead><tr><th class="l">${U.lab} · trimestre clos</th>${qs.map(q => `<th>${fd(q)}</th>`).join('')}</tr></thead><tbody>${R.map(([k, l, t]) => `<tr><td class="l am">${l}${t === 'p' ? ' %' : ''}</td>${qs.map((_, j) => { const v = H[k][k0 + j]; return `<td class="${k === 'fcf' ? 'yl' : 'wh'}">${v == null ? NDc() : cellFmt(t, v, U)}</td>`; }).join('')}</tr>`).join('')}</tbody></table></div>`;
  } else main = accountsTable(F, 10, { cagr: true });
  m.innerHTML = `<div class="tools" style="border:1px solid var(--line2)">${tools}</div>
    <div class="grid side">${pn(`${s.tk} · comptes ${st.v === 'Q' ? 'trimestriels (cumul 12 mois)' : 'sur 10 exercices'}`, 'FA', main, { np: true, lect: faSrcNote(F) })}${pn('Synthèse', 'FA', kv, { lect: 'TCAM = taux de croissance annuel moyen. Piotroski : 9 critères de solidité (rentabilité, flux, levier, liquidité, dilution, marges, rotation) ; seuls les critères calculables sont comptés.' })}</div>
    <div class="grid c3">${pn('Chiffre d’affaires et résultat net', 'FA', cvb('fa1', 210))}${pn('Free cash-flow et résultat net', 'FA', cvb('fa2', 210))}${pn('Marges', 'FA', cvb('fa3', 210))}</div>
    <div class="grid c3">${pn('Rentabilité : ROE et ROIC', 'FA', cvb('fa4', 200))}${pn('Dette nette', 'FA', cvb('fa5', 200))}${pn(F.mkt === 'US' ? 'Nombre d’actions (dilution / rachats)' : 'BNPA et dividende (FCFA)', 'FA', cvb('fa6', 200))}</div>`;
  m.querySelectorAll('[data-v]').forEach(b => b.onclick = () => { st.v = b.dataset.v; render(); });
  const useQ = st.v === 'Q', X = useQ ? F.H.q : x, D = useQ ? F.H : Y, xf = useQ ? fmtD : yLab;
  const mk = (id, panes, series) => { if (!X.length) return; new TSChart($(id), { panes, padR: 54, xfmt: useQ ? null : (d => yLab(d)), xfull: xf, minBars: 2 }).set({ x: X, series }, [0, X.length - 1]); };
  const sc = a => (a || []).map(v => v == null ? null : v * U.k), fm = v => num(v, U.d) + ' ' + U.lab;
  mk('fa1', [{ h: 1, fmt: v => num(v, 0), zero: true }], [{ type: 'bar', y: sc(D.rev), color: rgba(CL.cyan, .55), label: 'CA', fmt: fm }, { type: 'bar', y: sc(D.ni), color: CL.amber, label: 'Résultat net', fmt: fm }]);
  mk('fa2', [{ h: 1, fmt: v => num(v, 0), refs: [{ v: 0, color: CL.dim2, dash: [] }] }], [{ type: 'bar', y: sc(D.fcf), color: CL.up, label: 'FCF', fmt: fm }, { y: sc(D.ni), color: CL.amber, label: 'Résultat net', fmt: fm }, { y: sc(D.ocf), color: CL.dim, label: 'Flux d’exploitation', fmt: fm }]);
  const dv = (a, b) => (a || []).map((v, i) => v != null && b && b[i] ? v / b[i] : null);
  const mg = F.mkt === 'US' ? [{ y: dv(D.gp, D.rev), color: CL.cyan, label: 'brute' }, { y: dv(D.opi, D.rev), color: CL.white, label: 'exploitation' }, { y: dv(D.ni, D.rev), color: CL.amber, label: 'nette' }, { y: dv(D.fcf, D.rev), color: CL.up, label: 'FCF' }]
    : [{ y: Y.ebitdam, color: CL.cyan, label: 'EBITDA' }, { y: Y.om, color: CL.white, label: 'exploitation' }, { y: Y.nm, color: CL.amber, label: 'nette' }, { y: Y.fcfm, color: CL.up, label: 'FCF' }];
  mk('fa3', [{ h: 1, fmt: fmtPctAxis }], mg.map(o => ({ ...o, fmt: v => P1(v) })));
  mk('fa4', [{ h: 1, fmt: fmtPctAxis, refs: [{ v: 0, color: CL.dim2, dash: [] }] }], [{ y: D.roe, color: CL.amber, label: 'ROE', fmt: v => P1(v) }, { y: D.roic, color: CL.cyan, label: 'ROIC', fmt: v => P1(v) }]);
  mk('fa5', [{ h: 1, fmt: v => num(v, 0), refs: [{ v: 0, color: CL.dim2, dash: [] }] }], [{ type: 'bar', y: sc(D.nd), color: CL.red || CL.dn, label: 'Dette nette (négatif = trésorerie nette)', fmt: fm }]);
  if (F.mkt === 'US') mk('fa6', [{ h: 1, fmt: v => num(v / 1e6, 0) + ' M' }], [{ y: D.sh, color: CL.white, label: 'Actions diluées', fmt: v => num(v / 1e6, 1) + ' M' }]);
  else mk('fa6', [{ h: 1, fmt: v => num(v, 0) }], [{ type: 'bar', y: Y.eps, color: rgba(CL.cyan, .6), label: 'BNPA', fmt: v => num(v, Math.abs(v) < 10 ? 2 : 0) }, { type: 'bar', y: Y.dps, color: CL.amber, label: 'Dividende', fmt: v => num(v, Math.abs(v) < 10 ? 2 : 0) }]);
};

/* ------------------------------------------------------------------ RV */
const MULT = [['pe', 'PER', 'x', 'bas = bon marché'], ['fpe', 'PER prévisionnel', 'x', 'consensus 12 mois'], ['ev_ebitda', 'VE / EBITDA', 'x', ''], ['ev_sales', 'VE / CA', 'x', ''], ['pb', 'Cours / actif net (P/B)', 'x', ''], ['fcfy', 'Rendement FCF', 'p', 'haut = bon marché'], ['dy', 'Rendement du dividende', 'p', '']];
function peersOf(s, IDX) {
  const rows = IDX.rows; let P = rows.filter(r => r.mkt === s.mkt && r.grp === s.grp), lab = s.grp;
  if (P.length < 5 && s.mkt === 'BRVM') { P = rows.filter(r => r.mkt === 'BRVM' && !!r.bank === !!s.bank); lab = s.bank ? 'banques BRVM' : `BRVM hors banques (secteur ${s.grp} trop petit)`; }
  if (P.length < 5 && s.mkt === 'US') { const sc = s.sector || s.grp; P = rows.filter(r => r.mkt === 'US' && (Q.by[r.id] || {}).sector === sc); lab = sc; if (P.length < 5) { P = rows.filter(r => r.mkt === 'US'); lab = 'actions US suivies'; } }
  if (!P.some(r => r.id === s.id)) { const me = rows.find(r => r.id === s.id); if (me) P.push(me); }
  P.label = lab; return P;
}
const qtl = (a, q) => { const v = a.filter(x => x != null && isFinite(x)).sort((p, r) => p - r); if (!v.length) return null; const i = (v.length - 1) * q, lo = Math.floor(i); return v[lo] + (v[Math.min(v.length - 1, lo + 1)] - v[lo]) * (i - lo); };
const med = a => { const v = a.filter(x => x != null && isFinite(x)).sort((p, q) => p - q); return v.length ? (v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2) : null; };
const pctRank = (a, v) => { const o = a.filter(x => x != null && isFinite(x)); return o.length && v != null ? o.filter(x => x <= v).length / o.length : null; };
async function RV_main(m, alive) {
  const s = sec(ST.sec); const [IDX, F] = await Promise.all([getJSON('fa_index.json'), faJSON(s.id).catch(() => null)]); if (!alive()) return;
  const me = IDX.rows.find(r => r.id === s.id); if (!me || !F) { m.innerHTML = pn(s.tk + ' · valorisation relative', 'RV', '<div class="empty">Comptes non disponibles.</div>'); return; }
  const st = ST.rv = ST.rv || { mh: 'pe', yrs: 5, sx: 'roe', sy: 'pe' }; if (st.base !== s.id) { st.base = s.id; if (s.bank || me.bank) { st.sx = 'roe'; st.sy = 'pb'; } } const P = peersOf(s, IDX);
  const MH = F.mh || { d: [] }; const k0 = MH.d.length ? MH.d.findIndex(d => d >= MH.d[MH.d.length - 1] - st.yrs * 10000) : 0;
  const hist = k => { const a = (MH[k] || []).slice(Math.max(0, k0)).filter(v => v != null && isFinite(v) && v > 0 && v < (k === 'fcfy' || k === 'dy' ? 1 : 500)); if (a.length < 20) return null; const mu = U.mean(a), sd = U.std(a); return { mu, sd, n: a.length, last: a[a.length - 1], pr: pctRank(a, a[a.length - 1]) }; };
  const rows = MULT.filter(([k]) => k !== 'fpe' || s.mkt === 'US').map(([k, l, t, hint]) => {
    const v = me[k], peers = P.map(r => r[k]).filter(x => x != null && isFinite(x) && (t !== 'x' || x > 0)), md = med(peers), H = hist(k), f = t === 'p' ? x => P1(x, 2) : x => x == null ? '—' : num(x, 1) + ' x';
    const prem = v != null && md ? (t === 'p' ? md / v - 1 : v / md - 1) : null;
    return `<tr><td class="l am">${l}</td><td class="yl">${v != null ? f(v) : NDc(k === 'fpe' ? 'pas de consensus' : 'non calculable (résultat négatif ou donnée absente)')}</td><td>${f(md)}</td><td>${peers.length > 3 ? f(qtl(peers, .25)) + ' – ' + f(qtl(peers, .75)) : '—'}</td>
      <td>${prem == null ? '—' : `<span class="${prem > 0 ? 'dn' : 'up'}">${prem > 0 ? 'prime ' : 'décote '}${num(Math.abs(prem) * 100, 0)} %</span>`}</td><td>${v != null ? num(pctRank(peers, v) * 100, 0) + 'e pct' : '—'}</td>
      <td>${H ? f(H.mu) : '—'}</td><td>${H ? f(H.mu - H.sd) + ' – ' + f(H.mu + H.sd) : '—'}</td><td>${H ? num(H.pr * 100, 0) + 'e pct' : '—'}</td><td class="l dm">${hint}</td></tr>`; }).join('');
  const cols = [['id', 'Titre', 'l'], ['mcap', 'Capi.'], ['pe', 'PER'], ...(s.mkt === 'US' ? [['fpe', 'PER prév.']] : []), ['ev_ebitda', 'VE/EBITDA'], ['ev_sales', 'VE/CA'], ['pb', 'P/B'], ['fcfy', 'Rdt FCF'], ['dy', 'Rdt div.'], ['roe', 'ROE'], ['rev_g', 'Crois. CA'], ['nm', 'Marge nette']];
  const fmtc = (k, v) => v == null ? '—' : k === 'mcap' ? big(v) : ['fcfy', 'dy', 'roe', 'rev_g', 'nm'].includes(k) ? P1(v, 1) : num(v, 1);
  const peerT = `<div class="tw" style="max-height:44vh"><table class="t"><thead><tr>${cols.map(c => `<th class="${c[2] || ''}">${c[1]}</th>`).join('')}</tr></thead><tbody>
    ${P.slice().sort((a, b) => (b.mcap || 0) - (a.mcap || 0)).map(r => `<tr data-sec="${r.id}" data-to="RV" class="${r.id === s.id ? 'cur' : ''}">${cols.map(([k, , c]) => k === 'id' ? `<td class="l tk">${r.id}</td>` : `<td class="${c || ''}">${fmtc(k, r[k])}</td>`).join('')}</tr>`).join('')}
    <tr class="sec"><td class="l">Médiane</td>${cols.slice(1).map(([k]) => `<td>${fmtc(k, med(P.map(r => r[k]).filter(v => v != null && (!['pe', 'ev_ebitda', 'pb', 'fpe'].includes(k) || v > 0))))}</td>`).join('')}</tr></tbody></table></div>`;
  const mhOpts = MULT.filter(([k]) => MH[k] && MH[k].some(v => v != null)).map(([k, l]) => `<button class="tb ${st.mh === k ? 'on' : ''}" data-mh="${k}">${l}</button>`).join('');
  const SX = [['roe', 'ROE'], ['rev_g', 'Croissance du CA'], ['roic', 'ROIC'], ['fcfm', 'Marge FCF'], ['nm', 'Marge nette']], SY = [['pe', 'PER'], ['ev_ebitda', 'VE/EBITDA'], ['pb', 'P/B'], ['fcfy', 'Rendement FCF']];
  m.innerHTML = `<div class="grid c2 rvg">${pn(`${s.tk} · multiples contre ${P.length - 1} pairs (${esc(P.label)})`, 'RV', `<div class="tw"><table class="t"><thead><tr><th class="l">Multiple</th><th>${s.id}</th><th>Médiane pairs</th><th>1er – 3e quartile</th><th>Prime / décote</th><th>Rang pairs</th><th>Moy. ${st.yrs} ans</th><th>± 1 écart-type</th><th>Rang historique</th><th class="l"></th></tr></thead><tbody>${rows}</tbody></table></div>`,
      { np: true, lect: `Prime = le titre est plus cher que la médiane de ses pairs (multiple plus élevé, ou rendement plus faible). Rang historique = position du multiple actuel dans son propre historique hebdomadaire sur ${st.yrs} ans (100e = le plus cher). ${s.mkt === 'BRVM' ? 'BRVM : multiples calculés sur le dernier exercice publié ; pas de consensus prévisionnel public.' : 'PER prévisionnel : consensus des analystes.'}` })}
    ${pn('Valorisation contre qualité', 'RV', `<div class="tools">${SX.map(([k, l]) => `<button class="tb ${st.sx === k ? 'on' : ''}" data-sx="${k}">${l}</button>`).join('')}<span class="tlab">contre</span>${SY.map(([k, l]) => `<button class="tb ${st.sy === k ? 'on' : ''}" data-sy="${k}">${l}</button>`).join('')}</div>${cvb('rvS', 300)}`, { lect: 'Chaque point est un pair (valeurs extrêmes écartées). Une valeur au-dessus de la droite paie plus que ce que sa qualité justifie en moyenne dans le groupe ; en dessous, elle est relativement bon marché. Clic = ouvrir le titre.' })}
    ${pn(`Historique du multiple · ${s.id}`, 'RV', `<div class="tools">${mhOpts}<span class="tlab">Période</span>${[5, 10].map(y => `<button class="tb ${st.yrs === y ? 'on' : ''}" data-yr="${y}">${y} ans</button>`).join('')}</div>${cvb('rvH', 260)}`, { lect: '<span id="rvL"></span>' })}
    ${pn('Pairs', 'RV', peerT, { np: true })}</div>`;
  m.querySelectorAll('[data-mh]').forEach(b => b.onclick = () => { st.mh = b.dataset.mh; render(); }); m.querySelectorAll('[data-yr]').forEach(b => b.onclick = () => { st.yrs = +b.dataset.yr; render(); });
  m.querySelectorAll('[data-sx]').forEach(b => b.onclick = () => { st.sx = b.dataset.sx; render(); }); m.querySelectorAll('[data-sy]').forEach(b => b.onclick = () => { st.sy = b.dataset.sy; render(); });
  const yv = P.map(r => r[st.sy]).filter(v => v != null && isFinite(v)), yq1 = qtl(yv, .1), yq9 = qtl(yv, .9), span = (yq9 - yq1) || 1;
  const pts = P.map(r => ({ x: r[st.sx], y: r[st.sy], id: r.id, label: r.id, hi: r.id === s.id, color: r.id === s.id ? CL.yel : rgba(CL.cyan, .8) })).filter(p => p.x != null && p.y != null && (st.sy === 'fcfy' || p.y > 0) && p.y <= yq9 + span && p.y >= yq1 - span && Math.abs(p.x) < 3);
  let line = null; if (pts.length > 4) { const mx = U.mean(pts.map(p => p.x)), my = U.mean(pts.map(p => p.y)); const b = pts.reduce((a, p) => a + (p.x - mx) * (p.y - my), 0) / (pts.reduce((a, p) => a + (p.x - mx) ** 2, 0) || 1); line = [my - b * mx, b]; }
  const lx = SX.find(x => x[0] === st.sx)[1], ly = SY.find(x => x[0] === st.sy)[1];
  scatterL($('rvS'), { pts, line, fx: fmtPctAxis, fy: st.sy === 'fcfy' ? fmtPctAxis : v => num(v, 0) + 'x', xlab: lx, ylab: ly, to: 'RV', tipf: p => `<b>${p.id}</b> ${esc((Q.by[p.id] || {}).short || (Q.by[p.id] || {}).n || '')}<br>${lx} ${P1(p.x)} · ${ly} ${st.sy === 'fcfy' ? P1(p.y) : num(p.y, 1) + ' x'}` });
  const arr = MH[st.mh] || []; const k1 = Math.max(0, k0); const xs = MH.d.slice(k1), ys = arr.slice(k1).map(v => v != null && isFinite(v) && v > 0 && v < 500 ? v : null); const H = hist(st.mh);
  if (xs.length && H) { const isP = st.mh === 'fcfy' || st.mh === 'dy'; const f = isP ? v => P1(v, 1) : v => num(v, 1) + ' x';
    new TSChart($('rvH'), { panes: [{ h: 1, fmt: isP ? fmtPctAxis : v => num(v, 0) + 'x', refs: [{ v: H.mu, color: CL.amber, label: 'moyenne' }, { v: H.mu + H.sd, color: CL.dim, label: '+1σ' }, { v: Math.max(0, H.mu - H.sd), color: CL.dim, label: '−1σ' }] }] })
      .set({ x: xs, series: [{ y: ys, color: CL.cyan, label: MULT.find(x => x[0] === st.mh)[1], fmt: f }] }, [0, xs.length - 1]);
    $('rvL').innerHTML = `Multiple hebdomadaire calculé avec les résultats connus à chaque date (${s.mkt === 'US' ? 'trimestre clos + 45 jours' : 'exercice publié fin avril'}). Actuel <strong>${f(H.last)}</strong>, moyenne ${st.yrs} ans <strong>${f(H.mu)}</strong> : ${H.pr > .8 ? 'dans le haut de sa fourchette historique' : H.pr < .2 ? 'dans le bas de sa fourchette historique' : 'dans sa zone habituelle'} (${num(H.pr * 100, 0)}e percentile).`;
  } else $('rvH').innerHTML = '<div class="empty">Historique insuffisant pour ce multiple.</div>';
};

/* ------------------------------------------------------------------ WACC */
PAGES.WACC = async (m, alive) => {
  const s = sec(ST.sec); const [F, E, PER] = await Promise.all([faJSON(s.id).catch(() => null), ecoLite().catch(() => null), getJSON('per.json').catch(() => null)]); if (!alive()) return;
  if (!F) { m.innerHTML = pn(s.tk + ' · création de valeur', 'WACC', '<div class="empty">Comptes non disponibles.</div>'); return; }
  const us = F.mkt === 'US', t10 = E && E.meta ? E.meta.find(x => x.id === 'DGS10') : null;
  const st = ST.wacc && ST.wacc.id === s.id ? ST.wacc : (ST.wacc = { id: s.id, rf: us ? (t10 ? t10.last / 100 : .042) : .065, erp: us ? .045 : .095, beta: s.beta != null ? .67 * s.beta + .33 : 1, kd: null, tax: F.tax != null ? F.tax : us ? .21 : .25 });
  const debt = us ? (F.H && F.H.debt ? F.H.debt[F.H.debt.length - 1] : null) : (F.nd != null ? Math.max(0, F.nd) : null), mcap = F.mcap || s.mcap;
  if (st.kd == null) { const it = us && F.Y && F.Y.int ? F.Y.int[F.Y.int.length - 1] : null; st.kd = it && debt ? U.clamp(it / debt, st.rf, st.rf + .08) : st.rf + .02; }
  const compute = () => { const ke = st.rf + st.beta * st.erp, D = debt || 0, Ev = mcap || 0, wE = Ev / ((Ev + D) || 1), wD = 1 - wE, w = wE * ke + wD * st.kd * (1 - st.tax); return { ke, wE, wD, w }; };
  const Y = F.Y, roicA = Y.roic || [], yrs = Y.y.map(y => F.mkt === 'US' ? Math.floor(y / 10000) : y);
  const icA = us ? Y.y.map((_, i) => Y.eq && Y.eq[i] != null ? (Y.debt[i] || 0) + Y.eq[i] - (Y.cashx[i] || 0) : null) : Y.y.map((_, i) => Y.eq[i] != null && Y.nd[i] != null ? (Y.eq[i] + Y.nd[i]) * 1e6 : null);
  const form = `<form class="form" id="wF">${[['rf', 'Taux sans risque', us ? `Trésor US 10 ans : ${t10 ? num(t10.last, 2) + ' % au ' + fd(t10.dl) : 'n.d.'}` : 'hypothèse : emprunts d’État UEMOA 7-10 ans, à ajuster'], ['erp', 'Prime de risque du marché', us ? 'hypothèse : 4 à 5 % (ordre de grandeur des études de prime implicite)' : 'hypothèse : prime mature (~4,5 %) + prime pays UEMOA (~5 %)'],
    ['beta', 'Bêta (ajusté Blume)', `bêta brut ${num(s.beta, 2)} sur 2 ans hebdo contre ${s.bench || '—'} ; ajusté = 0,67 × brut + 0,33${isBRVM(s) ? ' — les bêtas BRVM sont écrasés par le manque de liquidité' : ''}`], ['kd', 'Coût de la dette (avant impôt)', us ? 'charges d’intérêts ÷ dette financière (borné entre taux sans risque et +8 pts)' : 'hypothèse : taux sans risque + 2 pts'], ['tax', 'Taux d’impôt', us ? 'taux effectif (impôt ÷ résultat avant impôt)' : 'taux légal du pays']]
    .map(([k, l, h]) => `<label><span>${l}</span><input data-k="${k}" type="number" step="0.1" value="${num(st[k] * (k === 'beta' ? 1 : 100), 2).replace(/\s/g, '').replace(',', '.')}"><small>${k === 'beta' ? '' : '%'} ${esc(h)}</small></label>`).join('')}</form>`;
  m.innerHTML = `<div class="grid side">${pn(`${s.tk} · coût du capital et rentabilité des capitaux investis`, 'WACC', `<div class="grid c2b"><div class="kv2" id="wK"></div><div class="cv" id="wC" style="height:240px"></div></div>`, { lect: '<span id="wL"></span>' })}
    ${pn('Hypothèses (modifiables)', 'WACC', form, { lect: 'WACC = poids des fonds propres × (taux sans risque + bêta × prime de risque) + poids de la dette × coût de la dette × (1 − impôt). Poids : capitalisation boursière et dette financière comptable. Ce sont des <b>estimations</b>, pas des données publiées.' })}</div>
    <div class="grid c2">${pn('Écart ROIC − WACC par exercice', 'WACC', cvb('wS', 220))}${pn('Profit économique (EVA) = écart × capitaux investis', 'WACC', cvb('wE', 220))}</div>`;
  const draw = () => {
    const c = compute(), roic = F.roic; const spread = roic != null ? roic - c.w : null;
    $('wK').innerHTML = [['Coût des fonds propres', P1(c.ke, 2)], ['Coût de la dette après impôt', P1(st.kd * (1 - st.tax), 2)], ['Poids fonds propres / dette', `${num(c.wE * 100, 0)} % / ${num(c.wD * 100, 0)} %`], ['<b class="yl">WACC</b>', `<b class="yl">${P1(c.w, 2)}</b>`],
      ['ROIC (dernier)', P1(roic, 1)], ['Écart ROIC − WACC', spread == null ? '—' : sgn(spread, 1)], ['Capitalisation', big(mcap) + (us ? ' $' : ' FCFA')], [us ? 'Dette financière' : 'Dette nette (si positive)', debt != null ? big(debt) : '—']].map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join('');
    const sp = roicA.map(r => r == null ? null : r - c.w), lab = yrs.map(String);
    barChart($('wS'), { labels: lab, values: sp.map(v => v == null ? NaN : v * 100), fmt: v => num(v, 1) + ' pts', axisFmt: v => num(v, 0), labelsOnBars: true });
    const eva = sp.map((v, i) => v == null || icA[i] == null ? NaN : v * icA[i] * (us ? 1e-6 : 1e-9)); barChart($('wE'), { labels: lab, values: eva, fmt: v => num(v, us ? 0 : 1) + (us ? ' M$' : ' Md'), axisFmt: v => num(v, 0), labelsOnBars: true });
    const pos = sp.filter(v => v != null && v > 0).length, tot = sp.filter(v => v != null).length;
    $('wL').innerHTML = spread == null ? 'ROIC non calculable (résultat d’exploitation ou capitaux investis absents).' : `Avec ces hypothèses, ${s.id} ${spread > 0 ? '<b class="up">crée de la valeur</b>' : '<b class="dn">détruit de la valeur</b>'} : chaque franc investi rapporte ${P1(roic, 1)} contre un coût de ${P1(c.w, 1)}. Sur ${tot} exercices mesurés, l’écart est positif ${pos} fois. ROIC = résultat d’exploitation après impôt ÷ (capitaux propres + dette nette)${isBRVM(s) ? ', impôt au taux légal' : ''}.`;
    const ch = new TSChart($('wC'), { panes: [{ h: 1, fmt: fmtPctAxis, refs: [{ v: c.w, color: CL.amber, label: 'WACC ' + P1(c.w, 1), scale: true }] }], xfmt: d => yLab(d), xfull: d => yLab(d), minBars: 2 });
    ch.set({ x: yrs.map(y => y * 10000 + 1231), series: [{ type: 'bar', y: roicA, color: rgba(CL.cyan, .7), label: 'ROIC', fmt: v => P1(v, 1) }] }, [0, yrs.length - 1]);
  };
  draw(); $('wF').addEventListener('input', e => { const k = e.target.dataset.k; if (!k) return; const v = parseFloat(e.target.value); if (!isFinite(v)) return; st[k] = k === 'beta' ? v : v / 100; draw(); });
};

/* ------------------------------------------------------------------ DVD (titre) */
PAGES.DVD = async (m, alive) => {
  const s = sec(ST.sec); const [S, F, DV] = await Promise.all([series(s.id), faJSON(s.id).catch(() => null), getJSON('dividends.json')]); if (!alive()) return;
  let rows = [];
  if (isBRVM(s)) {
    const my = DV.filter(x => x.t === s.id && x.dps).sort((a, b) => (a.ex || 0) - (b.ex || 0));
    const pxAt = ds => { if (!ds) return null; const d = s2i(ds.slice(0, 10)); let k = S.x.findIndex(x => x >= d); if (k < 0) k = S.x.length - 1; return S.c[k]; };
    /* un exercice = la somme de ses versements ordinaires (acompte et solde, dividende complémentaire) ; le dividende exceptionnel
       est indiqué à part, hors variation, rendement et taux de distribution */
    const by = {}; for (const x of my) { if (!x.ex) continue; const r = by[x.ex] = by[x.ex] || { y: x.ex, dps: 0, exc: 0, det: null, pay: null };
      if (x.exc) r.exc += x.dps; else { r.dps += x.dps; r.det = x.det || r.det; r.pay = x.pay || r.pay; } }
    rows = Object.values(by).sort((a, b) => a.y - b.y).map(r => ({ ...r, dps: r.dps || null, px: pxAt(r.det || r.pay) }));
  } else {
    const by = {}; for (let i = 0; i < S.x.length; i++) if (S.div[i]) { const y = Math.floor(S.x[i] / 10000); by[y] = (by[y] || 0) + S.div[i]; }
    if (!Object.keys(by).length && F && F.Y && F.Y.div) F.Y.y.forEach((d, i) => { const dv = F.Y.div[i], sh = F.Y.sh[i]; if (dv && sh) by[Math.floor(d / 10000)] = dv / sh; });
    const cy = new Date().getFullYear(); rows = Object.entries(by).map(([y, v]) => ({ y: +y, dps: v, partial: +y === cy })).sort((a, b) => a.y - b.y);
    rows.forEach(r => { const k = S.x.findIndex(x => Math.floor(x / 10000) === r.y + (r.partial ? 0 : 1)); r.px = k >= 0 ? S.c[k] : S.c[S.c.length - 1]; });
  }
  const Y = F ? F.Y : null, yI = y => Y ? Y.y.findIndex(d => (F.mkt === 'US' ? Math.floor(d / 10000) : d) === y) : -1;
  rows.forEach((r, i) => { const p = rows[i - 1]; r.g = p && p.dps && r.dps && !r.partial ? r.dps / p.dps - 1 : null; r.yld = r.px && r.dps ? r.dps / r.px : null; const k = yI(r.y);
    if (k >= 0 && r.dps) { const eps = Y.eps ? Y.eps[k] : null; r.payout = eps && eps > 0 ? r.dps / eps : null; const fcf = Y.fcf ? Y.fcf[k] : null; const sh = F.mkt === 'US' ? (Y.sh || [])[k] : s.shares; r.fpay = fcf && fcf > 0 && sh ? r.dps * sh / (fcf * (F.mkt === 'US' ? 1 : 1e6)) : null; } });
  const flags = []; rows.forEach((r, i) => { const p = rows[i - 1]; if (p && r.g != null && r.g < -.05) flags.push(['dn', `${r.y} : dividende réduit de ${num(-r.g * 100, 0)} %`]); if (p && r.y - p.y > 1) flags.push(['dn', `${p.y + 1}${r.y - p.y > 2 ? '–' + (r.y - 1) : ''} : aucun dividende (suspension)`]);
    if (r.payout != null && r.payout > 1) flags.push(['am', `${r.y} : distribution supérieure au bénéfice (${num(r.payout * 100, 0)} %)`]); if (r.fpay != null && r.fpay > 1) flags.push(['am', `${r.y} : dividende non couvert par le FCF (${num(r.fpay * 100, 0)} % du FCF)`]); });
  const rr0 = rows.filter(r => !r.partial && r.dps), last = rr0.slice(-1)[0];
  const g5 = rr0.length ? cagrA(Array.from({ length: last.y - rr0[0].y + 1 }, (_, i) => (rr0.find(r => r.y === rr0[0].y + i) || {}).dps ?? null), 5) : null;  /* (années consécutives : une année sans dividende n'est pas sautée) */
  const streak = (() => { let k = 0; const rr = rows.filter(r => !r.partial && r.dps); for (let i = rr.length - 1; i > 0; i--) { if (rr[i].dps >= rr[i - 1].dps * .995 && rr[i].y - rr[i - 1].y === 1) k++; else break; } return k; })();
  const cur = s.yld != null ? s.yld : !isBRVM(s) && last && S.c.length ? last.dps / S.c[S.c.length - 1] : null;  /* (BRVM : pas de rendement sans versement depuis deux ans) */
  m.innerHTML = `<div class="grid side">${pn(`${s.tk} · dividendes par ${isBRVM(s) ? 'exercice' : 'année civile'}`, 'DVD', `<div class="tw" style="max-height:52vh"><table class="t"><thead><tr><th class="l">${isBRVM(s) ? 'Exercice' : 'Année'}</th><th>Dividende / action</th><th>Variation</th>${isBRVM(s) ? '<th class="l">Détachement</th><th class="l">Paiement</th>' : ''}<th>Cours de réf.</th><th>Rendement</th><th>Distribution (BPA)</th><th>Dividendes / FCF</th></tr></thead><tbody>
      ${rows.slice().reverse().map(r => `<tr><td class="l am">${r.y}${r.partial ? ' (en cours)' : ''}</td><td class="wh">${num(r.dps, isBRVM(s) && r.dps >= 10 ? 0 : 2)}${r.exc ? ` <span class="am" title="dividende exceptionnel net versé en plus, hors variation, rendement et distribution">+ ${num(r.exc, r.exc >= 10 ? 0 : 2)} exc.</span>` : ''}</td><td>${sgn(r.g, 1)}</td>${isBRVM(s) ? `<td class="l">${fds(r.det)}</td><td class="l">${fds(r.pay)}</td>` : ''}<td>${r.px ? px(s, r.px) : '—'}</td><td>${r.yld != null ? P1(r.yld, 2) : '—'}</td><td class="${r.payout > 1 ? 'dn' : ''}">${r.payout != null ? P1(r.payout, 0) : '—'}</td><td class="${r.fpay > 1 ? 'dn' : ''}">${r.fpay != null ? P1(r.fpay, 0) : NDc(isBRVM(s) ? 'FCF non lu pour cet exercice' : 'FCF négatif ou absent')}</td></tr>`).join('') || '<tr><td class="l dm" colspan="9">Aucun dividende recensé.</td></tr>'}</tbody></table></div>`,
      { np: true, lect: isBRVM(s) ? 'Rendement = dividende net ÷ cours au détachement. Distribution = dividende ÷ BNPA de l’exercice ; Dividendes / FCF = dividende × nombre de titres ÷ free cash-flow.' : 'Dividendes versés ou, à défaut, dividendes payés des comptes ÷ actions diluées. Rendement = dividendes de l’année ÷ cours de début d’année suivante.' })}
    ${pn('Synthèse', 'DVD', `<div class="kv2">${[['Rendement actuel', P1(cur, 2)], ['Dernier dividende', last ? num(last.dps, isBRVM(s) && last.dps >= 10 ? 0 : 2) + ' (' + last.y + ')' : '—'], ['Croissance annuelle 5 ans', P1(g5, 1)], ['Hausses ou maintiens consécutifs', streak + ' an' + (streak > 1 ? 's' : '')],
      ['Distribution (dernier BPA)', P1(last && last.payout, 0)], ['Couverture par le FCF', last && last.fpay ? num(1 / last.fpay, 2) + ' x' : '—']].map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join('')}</div>
      <h4 class="sub">Points d’attention</h4>${flags.length ? flags.slice(-10).reverse().map(([c, t]) => `<div class="flag ${c}">${t}</div>`).join('') : '<div class="dm">Aucune baisse, suspension ni dividende non couvert détecté.</div>'}`)}</div>
    <div class="grid c2">${pn('Dividende par action', 'DVD', cvb('dv1', 220))}${pn('Rendement et taux de distribution', 'DVD', cvb('dv2', 220))}</div>`;
  const rr = rows.filter(r => !r.partial && r.dps);
  if (rr.length) { barChart($('dv1'), { labels: rr.map(r => String(r.y)), values: rr.map(r => r.dps), fmt: v => num(v, isBRVM(s) ? 0 : 2), pos: CL.amber, labelsOnBars: true, extra: i => rr[i].g != null ? 'variation ' + num(rr[i].g * 100, 1) + ' %' : '' });
    new TSChart($('dv2'), { panes: [{ h: 1, fmt: fmtPctAxis }], xfmt: d => yLab(d), xfull: d => yLab(d), minBars: 2 }).set({ x: rr.map(r => r.y * 10000 + 1231), series: [{ type: 'bar', y: rr.map(r => r.payout), color: rgba(CL.cyan, .5), label: 'Distribution', fmt: v => P1(v, 0) }, { y: rr.map(r => r.yld), color: CL.amber, label: 'Rendement', fmt: v => P1(v, 2) }] }, [0, rr.length - 1]); }
};

/* ------------------------------------------------------------------ DDM */
PAGES.DDM = async (m, alive) => {
  const s = sec(ST.sec); const [S, F, E, DV] = await Promise.all([series(s.id), faJSON(s.id).catch(() => null), ecoLite().catch(() => null), getJSON('dividends.json')]); if (!alive()) return;
  const us = !isBRVM(s), price = s.last; let d0 = null, hist = [];
  if (!us) { const byE = {}; DV.filter(x => x.t === s.id && x.dps && x.ex && !x.exc).forEach(x => { byE[x.ex] = (byE[x.ex] || 0) + x.dps; }); const yE = Object.keys(byE).map(Number).sort((a, b) => a - b); hist = yE.length ? Array.from({ length: yE[yE.length - 1] - yE[0] + 1 }, (_, i) => byE[yE[0] + i] ?? null) : [];  /* (dividendes ordinaires, un total par exercice) */ d0 = s.dps || hist[hist.length - 1]; }
  else { const by = {}; for (let i = 0; i < S.x.length; i++) if (S.div[i]) { const y = Math.floor(S.x[i] / 10000); by[y] = (by[y] || 0) + S.div[i]; } const ys = Object.keys(by).sort(); const cy = String(new Date().getFullYear()); hist = ys.filter(y => y !== cy).map(y => by[y]); d0 = hist[hist.length - 1];
    if (!d0 && F && F.Y && F.Y.div) { const i = F.Y.div.length - 1; d0 = F.Y.div[i] && F.Y.sh[i] ? F.Y.div[i] / F.Y.sh[i] : null; } }
  if (!d0) { m.innerHTML = pn(s.tk + ' · valeur par les dividendes', 'DDM', '<div class="empty">Ce titre ne verse pas de dividende recensé : le modèle ne s’applique pas.</div>'); return; }
  const t10 = E && E.meta ? E.meta.find(x => x.id === 'DGS10') : null, rf = us ? (t10 ? t10.last / 100 : .042) : .065, erp = us ? .045 : .095, beta = s.beta != null ? .67 * s.beta + .33 : 1;
  const gh = cagrA(hist, Math.min(5, hist.length - 1));
  const st = ST.ddm && ST.ddm.id === s.id ? ST.ddm : (ST.ddm = { id: s.id, d0, r: rf + beta * erp, g1: U.clamp(gh != null ? gh : .03, -.05, .15), n: 5, g2: us ? .025 : .03 });
  m.innerHTML = `<div class="grid side">${pn(`${s.tk} · modèle d’actualisation des dividendes`, 'DDM', `<div class="grid c2b"><div class="kv2" id="dK"></div><div><h4 class="sub">Sensibilité de la valeur (deux étapes) · rendement exigé × croissance finale</h4><div id="dT"></div></div></div>`, { lect: '<span id="dL"></span>' })}
    ${pn('Hypothèses (modifiables)', 'DDM', `<form class="form" id="dF">${[['d0', 'Dernier dividende annuel', `${us ? 'dividendes de la dernière année civile' : 'dernier dividende net'} : ${num(d0, 2)}`, 1], ['r', 'Rendement exigé (coût des fonds propres)', `taux sans risque ${P1(rf, 2)} + bêta ajusté ${num(beta, 2)} × prime ${P1(erp, 1)} (hypothèses)`],
      ['g1', 'Croissance phase 1', `historique du dividende : ${gh != null ? P1(gh, 1) + ' par an' : 'n.d.'}`], ['n', 'Durée de la phase 1 (ans)', '', 1], ['g2', 'Croissance à perpétuité', us ? 'au plus la croissance nominale de long terme (~2-3 %)' : 'au plus l’inflation UEMOA + croissance réelle de long terme']]
      .map(([k, l, h, raw]) => `<label><span>${l}</span><input data-k="${k}" type="number" step="${raw ? (k === 'n' ? 1 : 0.01) : 0.1}" value="${raw ? st[k] : num(st[k] * 100, 2).replace(/\s/g, '').replace(',', '.')}"><small>${raw ? '' : '%'} ${esc(h)}</small></label>`).join('')}</form>`,
      { lect: 'Modèle de Gordon-Shapiro à deux étapes : dividendes croissant à g₁ pendant n ans puis à g₂ pour toujours, actualisés au rendement exigé. Résultat = <b>estimation</b> sensible aux hypothèses, pas une donnée publiée.' })}</div>`;
  const val = (r, g1, n, g2, D0) => { if (r <= g2) return null; let v = 0, D = D0; for (let t = 1; t <= n; t++) { D *= 1 + g1; v += D / Math.pow(1 + r, t); } const TV = D * (1 + g2) / (r - g2); return v + TV / Math.pow(1 + r, n); };
  const draw = () => {
    const V = val(st.r, st.g1, Math.round(st.n), st.g2, st.d0), G = st.r > st.g2 ? st.d0 * (1 + st.g2) / (st.r - st.g2) : null, gi = st.r - st.d0 * (1 + st.g2) / price, ri = st.d0 * (1 + st.g2) / price + st.g2;
    $('dK').innerHTML = [['Cours', px(s, price)], ['<b class="yl">Valeur (deux étapes)</b>', `<b class="yl">${V ? px(s, V) : '—'}</b>`], ['Potentiel', V ? sgn(V / price - 1, 1) : '—'], ['Valeur (Gordon, une étape)', G ? px(s, G) : '—'],
      ['Croissance implicite dans le cours', P1(gi, 2)], ['Rendement implicite (si croissance g₂)', P1(ri, 2)], ['Rendement du dividende', P1(st.d0 / price, 2)]].map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join('');
    const rs = [-.02, -.01, 0, .01, .02].map(d => st.r + d), gs = [-.01, -.005, 0, .005, .01].map(d => st.g2 + d);
    $('dT').innerHTML = `<table class="t"><thead><tr><th class="l">r \\ g₂</th>${gs.map(g => `<th>${P1(g, 1)}</th>`).join('')}</tr></thead><tbody>${rs.map(r => `<tr><td class="l am">${P1(r, 1)}</td>${gs.map(g => { const v = val(r, st.g1, Math.round(st.n), g, st.d0); return `<td style="background:${v ? heatBg(v / price - 1, .6) : 'transparent'}" class="${r === st.r && g === st.g2 ? 'yl' : ''}">${v ? px(s, v) : '—'}</td>`; }).join('')}</tr>`).join('')}</tbody></table>`;
    $('dL').innerHTML = `Au cours actuel, le marché anticipe une croissance perpétuelle du dividende de <strong>${P1(gi, 1)}</strong> par an si l’on exige ${P1(st.r, 1)} de rendement. ${gi > st.g2 ? 'C’est plus que l’hypothèse retenue : le cours intègre une croissance forte.' : 'C’est moins que l’hypothèse retenue : le cours est prudent au regard du dividende.'}`;
  };
  draw(); $('dF').addEventListener('input', e => { const k = e.target.dataset.k; if (!k) return; const v = parseFloat(e.target.value); if (!isFinite(v)) return; st[k] = ['d0', 'n'].includes(k) ? v : v / 100; draw(); });
};

/* ------------------------------------------------------------------ COMP */
async function trSeries(s, S) {
  /* indice de rendement total : dividendes réinvestis à la date de détachement (BRVM) ou de versement (US, Yahoo) */
  let div = S.div && S.div.some(v => v) ? S.div.slice() : null;
  if (isBRVM(s) && s.cls === 'Equity') { const DV = await getJSON('dividends.json'); div = new Array(S.x.length).fill(0); for (const x of DV) { if (x.t !== s.id || !x.dps) continue; const d = x.det || x.pay; if (!d) continue; const k = S.x.findIndex(v => v >= s2i(d.slice(0, 10))); if (k > 0) div[k] += x.dps; } }
  if (!div) return null; const tr = [S.c[0]]; for (let i = 1; i < S.c.length; i++) tr.push(tr[i - 1] * (S.c[i] + (div[i] || 0)) / S.c[i - 1]); return tr;
}
PAGES.COMP = async (m, alive) => {
  const s = sec(ST.sec); const st = ST.comp = ST.comp || {}; if (st.base !== s.id) { st.base = s.id; st.ids = [s.id]; st.bench = benchFor(s); st.per = '3A'; st.tr = true;
    const peers = secsWhere(x => x.id !== s.id && x.mkt === s.mkt && x.grp === s.grp && x.cls === s.cls).sort((a, b) => (b.mcap || 0) - (a.mcap || 0)).slice(0, 3); st.ids.push(...peers.map(x => x.id)); }
  const ids = [...new Set(st.ids.concat([st.bench]))].filter(id => Q.by[id]); const SS = await Promise.all(ids.map(id => series(id))); if (!alive()) return;
  const TR = st.tr ? await Promise.all(ids.map((id, i) => trSeries(Q.by[id], SS[i]))) : ids.map(() => null); if (!alive()) return;
  const yrs = { '1A': 1, '3A': 3, '5A': 5, '10A': 10 }[st.per]; const end = Math.max(...SS.map(S => S.x[S.x.length - 1])), start = end - yrs * 10000;
  const grid = SS[ids.indexOf(st.bench)].x.filter(d => d >= start); const cols = ['#ffd200', '#4fc3f7', '#ff7043', '#ab47bc', '#66bb6a', '#ec407a', '#90a4ae'];
  const lines = ids.map((id, i) => { const S = SS[i], val = TR[i] || S.c, f = ffillJS(S.x, val, grid); const b0 = f.find(v => v != null); return { id, y: f.map(v => v != null && b0 ? v / b0 * 100 : null), tr: !!TR[i], S, val }; });
  const stat = L => { const S = L.S, k0 = S.x.findIndex(d => d >= start); if (k0 < 0) return null; const v = L.val.slice(k0), x = S.x.slice(k0); const r = []; for (let i = 1; i < v.length; i++) r.push(v[i] / v[i - 1] - 1);
    let pk = v[0], dd = 0; for (const p of v) { pk = Math.max(pk, p); dd = Math.min(dd, p / pk - 1); } const ret = v[v.length - 1] / v[0] - 1, ann = Math.pow(1 + ret, 1 / yrs) - 1; return { ret, ann, vol: U.std(r) * Math.sqrt(S.f === 'D' ? 252 : 12), dd, r, x }; };
  const SB = stat(lines[ids.indexOf(st.bench)]);
  const rows = lines.map((L, i) => { const a = stat(L); if (!a) return ''; let te = null, ir = null, beta = null, corr = null;
    if (SB && L.id !== st.bench) { const mb = new Map(SB.x.map((d, j) => [d, SB.r[j - 1]])); const pr = []; a.x.forEach((d, j) => { if (j && mb.get(d) != null) pr.push([a.r[j - 1], mb.get(d)]); });
      if (pr.length > 30) { const ex = pr.map(p => p[0] - p[1]); te = U.std(ex) * Math.sqrt(252); ir = te ? (a.ann - SB.ann) / te : null; const mx = U.mean(pr.map(p => p[1])), my = U.mean(pr.map(p => p[0])); const cv = U.mean(pr.map(p => (p[0] - my) * (p[1] - mx))), vx = U.mean(pr.map(p => (p[1] - mx) ** 2)), vy = U.mean(pr.map(p => (p[0] - my) ** 2)); beta = cv / vx; corr = cv / Math.sqrt(vx * vy); } }
    const q = Q.by[L.id]; return `<tr data-sec="${L.id}" data-to="COMP"><td class="l"><i class="dot" style="background:${cols[i % cols.length]}"></i><span class="tk">${L.id}</span>${L.id === st.bench ? ' <span class="dm">indice</span>' : ''}</td><td class="l nm">${esc(q.short || q.n)}</td><td>${pc(a.ret, 1)}</td><td>${yrs > 1 ? pc(a.ann, 1) : '—'}</td><td>${L.id === st.bench ? '—' : sgn(a.ann - SB.ann, 1)}</td><td>${num(a.vol * 100, 1)} %</td><td>${pc(a.dd, 1)}</td><td>${beta != null ? num(beta, 2) : '—'}</td><td>${corr != null ? num(corr, 2) : '—'}</td><td>${te != null ? num(te * 100, 1) + ' %' : '—'}</td><td>${ir != null ? num(ir, 2) : '—'}</td><td class="dm">${L.tr ? 'oui' : 'non'}</td>
      <td>${L.id !== s.id && L.id !== st.bench ? `<button class="tb" data-rm="${L.id}">×</button>` : ''}</td></tr>`; }).join('');
  m.innerHTML = `<div class="tools" style="border:1px solid var(--line2)"><span class="tlab">Période</span>${['1A', '3A', '5A', '10A'].map(p => `<button class="tb ${st.per === p ? 'on' : ''}" data-per="${p}">${p}</button>`).join('')}
    <button class="tb ${st.tr ? 'on' : ''}" data-tr="1">Dividendes réinvestis</button><form class="pairf" id="coF" style="border:0;padding:0 0 0 10px"><span class="tlab">Ajouter</span><input list="coL" id="coI" placeholder="TICKER" spellcheck="false"><span class="tlab">Indice de référence</span><input list="coL" id="coB" value="${st.bench}" spellcheck="false"><button class="tb">OK</button>
    <datalist id="coL">${Q.sum.secs.filter(x => x.f === 'D').map(x => `<option value="${x.id}">${esc(x.short || x.n)}</option>`).join('')}</datalist></form></div>
    ${pn(`Performance comparée · base 100 au ${fd(grid[0])}${st.tr ? ' · dividendes réinvestis quand disponibles' : ''}`, 'COMP', cvb('coC', 360))}
    ${pn('Statistiques sur la période', 'COMP', `<div class="tw"><table class="t"><thead><tr><th class="l">Titre</th><th class="l">Nom</th><th>Perf.</th><th>Annualisée</th><th>Écart annuel / indice</th><th>Volatilité</th><th>Drawdown max</th><th>Bêta</th><th>Corrélation</th><th>Écart de suivi</th><th>Ratio d’information</th><th>Div. réinv.</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`,
      { np: true, lect: `Indice de référence : <b>${st.bench}</b>. Bêta et corrélation sur rendements quotidiens communs. Ratio d’information = surperformance annuelle ÷ écart de suivi. « Div. réinv. » = non : dividendes non disponibles pour ce titre, performance de prix seule.` })}`;
  new TSChart($('coC'), { panes: [{ h: 1, log: true, fmt: v => num(v, 0) }] }).set({ x: grid, series: lines.map((L, i) => ({ y: L.y, color: cols[i % cols.length], label: L.id, fmt: v => num(v, 1) })) }, [0, grid.length - 1]);
  m.querySelectorAll('[data-per]').forEach(b => b.onclick = () => { st.per = b.dataset.per; render(); }); m.querySelector('[data-tr]').onclick = () => { st.tr = !st.tr; render(); };
  m.querySelectorAll('[data-rm]').forEach(b => b.onclick = e => { e.stopPropagation(); st.ids = st.ids.filter(x => x !== b.dataset.rm); render(); });
  $('coF').onsubmit = e => { e.preventDefault(); const a = $('coI').value.trim().toUpperCase(), b = $('coB').value.trim().toUpperCase(); if (a && Q.by[a] && !st.ids.includes(a)) st.ids.push(a); if (b && Q.by[b]) st.bench = b; render(); };
};
function ffillJS(dates, vals, grid) { const out = []; let j = 0, last = null; for (const g of grid) { while (j < dates.length && dates[j] <= g) { last = vals[j]; j++; } out.push(last); } return out; }

/* ------------------------------------------------------------------ BETA */
function olsBeta(pairs) { const n = pairs.length; if (n < 20) return null; const mx = U.mean(pairs.map(p => p[1])), my = U.mean(pairs.map(p => p[0])); let sxy = 0, sxx = 0, syy = 0; for (const [y, x] of pairs) { sxy += (x - mx) * (y - my); sxx += (x - mx) ** 2; syy += (y - my) ** 2; }
  const b = sxy / sxx, a = my - b * mx, r = sxy / Math.sqrt(sxx * syy), res = pairs.reduce((s_, [y, x]) => s_ + (y - a - b * x) ** 2, 0), se = Math.sqrt(res / (n - 2) / sxx); return { b, a, r, r2: r * r, se, t: b / se, n }; }
function retsBy(S, f) {
  const out = new Map(); if (f === 'D') { for (let i = 1; i < S.x.length; i++) if (S.c[i - 1] > 0) out.set(S.x[i], Math.log(S.c[i] / S.c[i - 1])); return out; }
  const key = d => f === 'W' ? isoWeekKey(d) : Math.floor(d / 100), ends = [];
  for (let i = 0; i < S.x.length; i++) { const k = key(S.x[i]); if (ends.length && ends[ends.length - 1][0] === k) ends[ends.length - 1][1] = S.c[i]; else ends.push([k, S.c[i]]); }
  for (let j = 1; j < ends.length; j++) if (ends[j - 1][1] > 0) out.set(ends[j][0], Math.log(ends[j][1] / ends[j - 1][1])); return out;
}
function isoWeekKey(d) { const t = new Date(Date.UTC(Math.floor(d / 10000), Math.floor(d / 100) % 100 - 1, d % 100)); const day = (t.getUTCDay() + 6) % 7; t.setUTCDate(t.getUTCDate() - day + 4); return t.getUTCFullYear() * 100 + Math.ceil(((t - Date.UTC(t.getUTCFullYear(), 0, 1)) / 864e5 + 1) / 7); }
PAGES.BETA = async (m, alive) => {
  const s = sec(ST.sec); const st = ST.beta = ST.beta || {}; if (st.base !== s.id) { st.base = s.id; st.bench = benchFor(s); }
  const [S, B] = await Promise.all([series(s.id), series(st.bench)]); if (!alive()) return;
  const end = S.x[S.x.length - 1]; const win = [['6 mois', 'D', 126], ['1 an', 'D', 252], ['2 ans', 'W', 104], ['5 ans', 'M', 60]];
  const rs = { D: [retsBy(S, 'D'), retsBy(B, 'D')], W: [retsBy(S, 'W'), retsBy(B, 'W')], M: [retsBy(S, 'M'), retsBy(B, 'M')] };
  const pairsOf = (f, n, lag) => { const [a, b] = rs[f]; const keys = [...a.keys()].filter(k => b.has(k)).sort((p, q) => p - q).slice(-n); const out = []; keys.forEach((k, j) => { if (lag) { const kp = keys[j - 1], kn = keys[j + 1]; if (kp == null || kn == null) return; out.push([a.get(k), b.get(k) + b.get(kp) + b.get(kn)]); } else out.push([a.get(k), b.get(k)]); }); return out; };
  const R = win.map(([l, f, n]) => ({ l, f, n, o: olsBeta(pairsOf(f, n)), d: f === 'D' ? olsBeta(pairsOf(f, n, true)) : null }));
  const dr = rs.D[0]; const rr = [...dr.values()].slice(-252); const vol = U.std(rr) * Math.sqrt(252), down = Math.sqrt(U.mean(rr.map(v => Math.min(0, v) ** 2))) * Math.sqrt(252);
  const so = rr.slice().sort((a, b) => a - b), var95 = so[Math.floor(so.length * .05)];
  let pk = S.c[0], mdd = 0; const k5 = S.x.findIndex(d => d >= end - 50000); for (let i = Math.max(0, k5); i < S.c.length; i++) { pk = Math.max(pk, S.c[i]); mdd = Math.min(mdd, S.c[i] / pk - 1); }
  const pd = pairsOf('D', 504); const bear = olsBeta(pd.filter(p => p[1] < 0)), bull = olsBeta(pd.filter(p => p[1] > 0));
  const peers = secsWhere(x => x.mkt === s.mkt && x.grp === s.grp && x.cls === s.cls && x.f === 'D').sort((a, b) => (b.mcap || 0) - (a.mcap || 0)).slice(0, 12);
  const benches = isBRVM(s) ? ['BRVMC', 'BRVM30', 'SPY', 'QQQ', 'EEM', 'AFK'] : ['SPY', 'QQQ', 'VTI', 'SOXX', 'EEM', 'BRVMC'];
  m.innerHTML = `<div class="tools" style="border:1px solid var(--line2)"><span class="tlab">Indice de référence</span>${benches.filter(b => Q.by[b] && b !== s.id).map(b => `<button class="tb ${st.bench === b ? 'on' : ''}" data-bm="${b}">${b}</button>`).join('')}</div>
    <div class="grid c2">${pn(`${s.tk} · bêta contre ${st.bench}`, 'BETA', `<table class="t"><thead><tr><th class="l">Fenêtre</th><th class="l">Fréquence</th><th>Bêta</th><th>± erreur type</th><th>t</th><th>R²</th><th>Corrélation</th><th>Alpha annuel</th><th>Obs.</th>${isBRVM(s) ? '<th>Bêta Dimson</th>' : ''}</tr></thead><tbody>
      ${R.map(x => x.o ? `<tr><td class="l am">${x.l}</td><td class="l">${{ D: 'quotidienne', W: 'hebdomadaire', M: 'mensuelle' }[x.f]}</td><td class="yl">${num(x.o.b, 2)}</td><td>${num(x.o.se, 2)}</td><td>${num(x.o.t, 1)}</td><td>${num(x.o.r2, 2)}</td><td>${num(x.o.r, 2)}</td><td>${pc(x.o.a * { D: 252, W: 52, M: 12 }[x.f], 1)}</td><td>${x.o.n}</td>${isBRVM(s) ? `<td>${x.d ? num(x.d.b, 2) : '—'}</td>` : ''}</tr>` : `<tr><td class="l am">${x.l}</td><td colspan="9" class="l dm">historique commun insuffisant</td></tr>`).join('')}</tbody></table>`,
      { lect: `Bêta = pente de la régression des rendements de ${s.id} sur ceux de ${st.bench} (moindres carrés). Une erreur type élevée ou un t inférieur à 2 = estimation peu fiable. ${isBRVM(s) ? 'Bêta Dimson : ajoute les rendements de l’indice de la veille et du lendemain, pour corriger les cotations non synchrones des titres peu échangés.' : ''} Alpha = rendement non expliqué par l’indice, annualisé.` })}
    ${pn('Risque', 'BETA', `<div class="kv2">${[['Volatilité 1 an', P1(vol, 1)], ['Volatilité à la baisse', P1(down, 1)], ['VaR 95 % (1 jour, historique)', P1(var95, 2)], ['Drawdown max 5 ans', P1(mdd, 1)], ['Bêta en baisse de l’indice', bear ? num(bear.b, 2) : '—'], ['Bêta en hausse de l’indice', bull ? num(bull.b, 2) : '—']].map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join('')}</div>`,
      { lect: 'Bêtas de baisse / hausse : régression sur les seules séances où l’indice recule / progresse (2 ans). Un bêta de baisse supérieur au bêta de hausse = le titre amplifie surtout les chutes.' })}</div>
    <div class="grid c2">${pn('Bêta et corrélation glissants (1 an, quotidien)', 'BETA', cvb('bR', 240))}${pn(`Comparaison avec les pairs (${esc(s.grp || '')})`, 'BETA', '<div id="bP"><div class="empty">Calcul…</div></div>', { np: true })}</div>`;
  m.querySelectorAll('[data-bm]').forEach(b => b.onclick = () => { st.bench = b.dataset.bm; render(); });
  const [a, b] = rs.D; const keys = [...a.keys()].filter(k => b.has(k)).sort((p, q) => p - q); const xs = [], be = [], co = [];
  for (let j = 252; j < keys.length; j += 2) { const o = olsBeta(keys.slice(j - 252, j).map(k => [a.get(k), b.get(k)])); xs.push(keys[j]); be.push(o ? o.b : null); co.push(o ? o.r : null); }
  if (xs.length) new TSChart($('bR'), { panes: [{ h: 1, refs: [{ v: 1, color: CL.dim2 }] }, { h: .6, fixed: [-1, 1], refs: [{ v: 0, color: CL.dim2 }] }] }).set({ x: xs, series: [{ y: be, color: CL.amber, label: 'Bêta', fmt: v => num(v, 2) }, { pane: 1, y: co, color: CL.cyan, label: 'Corrélation', fmt: v => num(v, 2) }] });
  const PS = await Promise.all(peers.map(p => series(p.id).catch(() => null))); if (!alive()) return;
  const pr = peers.map((p, i) => { const S2 = PS[i]; if (!S2) return null; const a2 = retsBy(S2, 'W'), b2 = rs.W[1]; const ks = [...a2.keys()].filter(k => b2.has(k)).sort((x, y) => x - y).slice(-104); const o = olsBeta(ks.map(k => [a2.get(k), b2.get(k)])); const d = [...retsBy(S2, 'D').values()].slice(-252); return { p, o, vol: U.std(d) * Math.sqrt(252) }; }).filter(Boolean);
  $('bP').innerHTML = `<table class="t"><thead><tr><th class="l">Titre</th><th class="l">Nom</th><th>Bêta 2 ans</th><th>R²</th><th>Volatilité 1 an</th><th>Drawdown actuel</th></tr></thead><tbody>${pr.map(x => `<tr data-sec="${x.p.id}" data-to="BETA" class="${x.p.id === s.id ? 'cur' : ''}"><td class="l tk">${x.p.id}</td><td class="l nm">${esc(x.p.short || x.p.n)}</td><td>${x.o ? num(x.o.b, 2) : '—'}</td><td>${x.o ? num(x.o.r2, 2) : '—'}</td><td>${num(x.vol * 100, 1)} %</td><td>${pc(x.p.dd, 1)}</td></tr>`).join('')}</tbody></table>`;
};

/* ------------------------------------------------------------------ HP */
/* PAGES.HP : définition remplacée plus loin (version active dans un fichier suivant) — retirée */

/* ------------------------------------------------------------------ CN */
function aliasesOf(s) {
  const out = new Set([s.id]); const n = (s.short || s.n || '').replace(/\b(SA|S\.A\.|Inc\.?|Corp\.?|Corporation|Holdings?|Ltd|PLC|Group|Class [A-C]|Common Stock|Co\.|ADR|Sponsored|Ordinary Shares)\b/gi, '').replace(/[,.]/g, ' ').trim(); if (n.length > 3) out.add(n);
  const extra = { TSM: ['TSMC', 'Taiwan Semiconductor'], SNTS: ['Sonatel'], ORAC: ['Orange Côte d', 'Orange CI'], SGBC: ['Société Générale Côte', 'SGBCI', 'SGCI'], ETIT: ['Ecobank Transnational', 'ETI '], ECOC: ['Ecobank Côte'], SIBC: ['Société Ivoirienne de Banque', 'SIB '], CBIBF: ['Coris Bank'], PALC: ['Palm C'], SPHC: ['SAPH'], SOGC: ['SOGB'], NTLC: ['Nestlé C'], SLBC: ['Solibra'], UNLC: ['Unilever C'], TTLC: ['TotalEnergies Marketing C', 'Total CI'], CIEC: ['CIE '], SDCC: ['SODECI'], ONTBF: ['Onatel'], BOAC: ['BOA Côte', 'Bank of Africa Côte'], NSBC: ['NSIA Banque'], BICC: ['BICICI', 'BICI CI'], SMBC: ['SMB '], STBC: ['SITAB'], SDSC: ['AGL ', 'Africa Global Logistics'], ORGT: ['Oragroup'], NVDA: ['Nvidia'], AAPL: ['Apple'], MSFT: ['Microsoft'], GOOG: ['Alphabet', 'Google'], GOOGL: ['Alphabet', 'Google'], AMZN: ['Amazon'], META: ['Meta '], TSLA: ['Tesla'], AVGO: ['Broadcom'], AMD: ['AMD'] };
  (extra[s.id] || []).forEach(a => out.add(a)); return [...out].filter(a => a.length >= 3);
}
function newsRow(x) { return `<div class="nw"><span class="d">${new Date(x.t * 1000).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span><span class="c">${esc(x.c || '')}</span><span><a href="${esc(x.u)}" target="_blank" rel="noopener">${esc(x.ti)}</a> ${hideSrc(x) ? '' : `<span class="src">${esc(x.s || '')}</span>`}${x.x ? `<small>${esc(x.x)}</small>` : ''}</span></div>`; }
/* PAGES.CN : définition remplacée plus loin (version active dans un fichier suivant) — retirée */
