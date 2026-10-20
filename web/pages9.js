/* ================= FQT — quant appliqué à la BRVM (et aux actions US) : SCOR, LQA, TRA, ANOM, MODL, PEER ================= */
'use strict';
/* univers de comparaison : les 47-48 actions BRVM, ou les actions US dont les comptes SEC sont disponibles */
function uniOf(s) { return isBRVM(s) ? secsWhere(x => x.mkt === 'BRVM' && x.cls === 'Equity' && !legacy(x)) : secsWhere(x => x.mkt === 'US' && x.cls === 'Equity' && x.typ !== 'ETF' && x.fa); }
function prank(arr, v, dir = 1) { if (v == null || !isFinite(v)) return null; const a = arr.filter(x => x != null && isFinite(x)); if (a.length < 4) return null; let lt = 0, eq = 0; for (const x of a) { if (x < v) lt++; else if (x === v) eq++; } const p = (lt + .5 * eq) / a.length * 100; return dir > 0 ? p : 100 - p; }
const medA = a => U.median(a);
const lsGet = (k, d) => { try { const v = localStorage.getItem('fqt.' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } };
const lsSet = (k, v) => { try { localStorage.setItem('fqt.' + k, JSON.stringify(v)); } catch (e) { } };
const fmtM = (t, v) => v == null || !isFinite(v) ? null : t === 'pct' ? num(v * 100, 1) + '%' : t === 'x' ? num(v, 2) + 'x' : t === 'int' ? num(v, 0) : num(v, 2);
const scoreCol = v => v == null ? '#1a1a1a' : `hsl(${Math.round(v * 1.2)},70%,${22 + Math.abs(v - 50) / 50 * 10}%)`;

/* ------------------------------------------------------------------ SCOR : score multifactoriel /100
   Chaque mesure est classée en centile dans l'univers (banques comparées aux banques pour la valorisation et la qualité) ;
   un facteur = moyenne des centiles disponibles ; le score = moyenne pondérée des facteurs (poids modifiables). */
const SC_F = [
  ['V', 'Value', [['ey', 'Rendement bénéficiaire (1/PER)', 1, 'pct', 'peer'], ['pb', 'Cours / actif net (P/B)', -1, 'x', 'peer'], ['fcfy', 'Rendement du free cash-flow', 1, 'pct', 'peer', 'corp']]],
  ['Q', 'Qualité', [['roe', 'ROE', 1, 'pct', 'peer'], ['roic', 'ROIC', 1, 'pct', 'peer', 'corp'], ['nm', 'Marge nette', 1, 'pct', 'peer'], ['om', 'Marge d’exploitation', 1, 'pct', 'peer', 'corp'], ['nd_ebitda', 'Dette nette / EBITDA', -1, 'x', 'peer', 'corp'], ['ni_cv', 'Instabilité du résultat (CV 5-6 ans)', -1, 'num', 'peer'], ['ni_dec', 'Années de baisse du résultat', -1, 'int', 'peer']]],
  ['G', 'Croissance', [['rev_cagr3', 'CA, TCAM 3 ans', 1, 'pct', 'peer'], ['eps_cagr3', 'BPA, TCAM 3 ans', 1, 'pct', 'peer'], ['rev_g', 'CA, 1 an', 1, 'pct', 'peer'], ['ni_g', 'Résultat net, 1 an', 1, 'pct', 'peer']]],
  ['M', 'Momentum', [['r3m', 'Performance 3 mois', 1, 'pct', 'all'], ['r6m', 'Performance 6 mois', 1, 'pct', 'all'], ['r1y', 'Performance 12 mois', 1, 'pct', 'all']]],
  ['Y', 'Rendement', [['dy', 'Rendement du dividende', 1, 'pct', 'all'], ['div_n10', 'Années avec dividende (10 ans)', 1, 'int', 'all'], ['div_cut', 'Baisses de dividende (10 ans)', -1, 'int', 'all']]],
  ['L', 'Faible volatilité', [['vol', 'Volatilité 1 an', -1, 'pct', 'all'], ['beta', 'Bêta', -1, 'num', 'all']]]];
const SC_W0 = { V: 1, Q: 1, G: 1, M: 1, Y: 1, L: 1 };
async function scoreUniverse(s) {
  const IDX = await getJSON('fa_index.json'); const U0 = uniOf(s), byFa = new Map(IDX.rows.map(r => [r.id, r]));
  const rows = U0.map(x => { const r = byFa.get(x.id) || {}; return { id: x.id, s: x, bank: !!(x.bank || r.bank), grp: x.grp, ey: r.ey != null ? r.ey : r.pe ? 1 / r.pe : null, pb: r.pb > 0 ? r.pb : null, fcfy: r.fcfy, roe: r.roe, roic: r.roic, nm: r.nm, om: r.om,
    nd_ebitda: r.nd_ebitda, ni_cv: r.ni_cv, ni_dec: r.ni_dec, rev_cagr3: r.rev_cagr3, eps_cagr3: r.eps_cagr3, rev_g: r.rev_g, ni_g: r.ni_g, r3m: x.r3m, r6m: x.r6m, r1y: x.r1y, dy: r.dy != null ? r.dy : x.yld, div_n10: r.div_n10, div_cut: r.div_cut,
    vol: x.vol, beta: x.beta, hasFa: byFa.has(x.id) }; });
  const W = lsGet('scorW', SC_W0);
  for (const r of rows) { r.f = {}; r.m = {};
    for (const [fk, , ms] of SC_F) { const ps = [];
      for (const [k, , dir, , scope, only] of ms) { if (only === 'corp' && r.bank) continue; const peers = scope === 'peer' && isBRVM(s) ? rows.filter(q => q.bank === r.bank) : rows;
        const p = prank(peers.map(q => q[k]), r[k], dir); r.m[k] = p; if (p != null) ps.push(p); }
      r.f[fk] = ps.length ? ps.reduce((a, b) => a + b, 0) / ps.length : null; }
    let sw = 0, sv = 0; for (const [fk] of SC_F) if (r.f[fk] != null && W[fk] > 0) { sw += W[fk]; sv += W[fk] * r.f[fk]; } r.total = sw ? sv / sw : null; r.nf = SC_F.filter(([fk]) => r.f[fk] != null).length; }
  const ranked = rows.filter(r => r.total != null).sort((a, b) => b.total - a.total); ranked.forEach((r, i) => r.rank = i + 1);
  return { rows, ranked, W };
}
PAGES.SCOR = async (m, alive) => {
  const s = sec(ST.sec); const tab = tabState('SCOR', 's'); setTabs([['s', 'Score du titre'], ['c', 'Classement'], ['w', 'Pondérations et méthode']], tab, k => { ST.tab.SCOR = k; render(); });
  const SU = await scoreUniverse(s); if (!alive()) return; const me = SU.rows.find(r => r.id === s.id), N = SU.ranked.length, U0 = isBRVM(s) ? 'BRVM' : 'actions US suivies';
  if (tab === 'c') {
    const st = ST.scs = ST.scs || { k: 'total', dir: -1 }; const rows = SU.rows.slice().sort((a, b) => { const A = st.k === 'total' ? a.total : a.f[st.k], B = st.k === 'total' ? b.total : b.f[st.k]; return (A == null) - (B == null) || (B - A) * -st.dir; });
    const cell = v => `<td style="background:${scoreCol(v)};color:#fff">${v == null ? '—' : num(v, 0)}</td>`;
    m.innerHTML = pn(`Score multifactoriel · ${U0} · ${N} titres classés`, 'SCOR', `<div class="tw" style="max-height:70vh"><table class="t"><thead><tr><th class="l">Rang</th><th class="l">Titre</th><th class="l">Société</th><th class="l">Secteur</th><th data-k="total" class="${st.k === 'total' ? 'on' : ''}">Score</th>${SC_F.map(([fk, l]) => `<th data-k="${fk}" class="${st.k === fk ? 'on' : ''}">${l}</th>`).join('')}<th>Facteurs</th></tr></thead><tbody>
      ${rows.map(r => `<tr data-sec="${r.id}" data-to="SCOR" class="${r.id === s.id ? 'cur' : ''}"><td class="l">${r.rank || '—'}</td><td class="l tk">${r.id}</td><td class="l nm">${esc(r.s.short || r.s.n)}</td><td class="l dm">${esc(r.grp || '')}${r.bank ? ' (banque)' : ''}</td>${cell(r.total)}${SC_F.map(([fk]) => cell(r.f[fk])).join('')}<td class="dm">${r.nf}/6</td></tr>`).join('')}</tbody></table></div>`,
      { np: true, lect: 'Centiles dans l’univers (0 = le plus faible, 100 = le meilleur) ; pour la BRVM, valorisation, qualité et croissance des banques sont comparées aux seules banques. Cliquer un en-tête trie, une ligne ouvre le score du titre. Score calculé, pas un conseil.' });
    m.querySelectorAll('th[data-k]').forEach(th => th.onclick = () => { st.k = th.dataset.k; render(); });
    return;
  }
  if (tab === 'w') {
    const W = SU.W;
    m.innerHTML = `<div class="grid c2">${pn('Pondération des facteurs', 'SCOR', `<div class="form">${SC_F.map(([fk, l]) => `<label>${l}<input type="number" min="0" max="5" step=".5" data-w="${fk}" value="${W[fk]}"></label>`).join('')}<button class="run" id="scW">Appliquer</button><button class="tb" id="scW0" style="grid-column:1/-1">Revenir à des poids égaux</button></div>`, { lect: 'Poids relatifs (0 = facteur ignoré). Enregistrés dans ce navigateur.' })}
      ${pn('Méthode', 'SCOR', `<div class="lectb">${SC_F.map(([fk, l, ms]) => `<p><b>${l}</b> : ${ms.map(([, ml, dir, , scope, only]) => `${ml} (${dir > 0 ? 'plus haut = mieux' : 'plus bas = mieux'}${scope === 'peer' ? ', comparé au groupe banques / hors banques' : ''}${only === 'corp' ? ', hors banques' : ''})`).join(' ; ')}.</p>`).join('')}
        <p>Chaque mesure est convertie en centile (0-100) dans l’univers ${U0}. Une mesure absente n’est pas remplacée : le facteur est la moyenne des mesures disponibles, et un facteur sans aucune mesure est exclu du score. Le nombre de facteurs disponibles est indiqué.</p>
        <p>Les ratios sont calculés sur le dernier exercice publié.</p></div>`)}</div>`;
    $('scW').onclick = () => { const w = {}; m.querySelectorAll('[data-w]').forEach(i => w[i.dataset.w] = Math.max(0, +i.value || 0)); lsSet('scorW', w); toast('Pondérations enregistrées.'); render(); };
    $('scW0').onclick = () => { lsSet('scorW', SC_W0); render(); };
    return;
  }
  if (!me || me.total == null) { m.innerHTML = pn(`${esc(s.tk)} · score`, 'SCOR', '<div class="empty">Pas assez de données pour noter ce titre.</div>'); return; }
  const fac = SC_F.map(([fk, l, ms]) => ({ fk, l, v: me.f[fk], med: medA(SU.rows.map(r => r.f[fk])), ms }));
  const detail = SC_F.map(([fk, l, ms]) => `<tr class="sec"><td class="l" colspan="5">${l} · ${me.f[fk] == null ? 'n.d.' : num(me.f[fk], 0) + ' / 100'}</td></tr>` + ms.map(([k, ml, dir, t, scope, only]) => {
    if (only === 'corp' && me.bank) return `<tr><td class="l dm">${ml}</td><td colspan="4" class="l dm">sans objet pour une banque</td></tr>`;
    const peers = scope === 'peer' && isBRVM(s) ? SU.rows.filter(q => q.bank === me.bank) : SU.rows; const vals = peers.map(q => q[k]).filter(x => x != null && isFinite(x));
    const rk = me[k] != null ? vals.filter(x => dir > 0 ? x > me[k] : x < me[k]).length + 1 : null;
    return `<tr><td class="l">${ml}</td><td>${fmtM(t, me[k]) || NDc('donnée absente')}</td><td>${fmtM(t, medA(vals)) || '—'}</td><td style="background:${scoreCol(me.m[k])};color:#fff">${me.m[k] == null ? '—' : num(me.m[k], 0)}</td><td>${rk ? rk + ' / ' + vals.length : '—'}</td></tr>`; }).join('')).join('');
  m.innerHTML = `<div class="grid c2"><div class="grid" style="align-content:start">
      ${pn(`${esc(s.tk)} · score multifactoriel`, 'SCOR', `<div style="display:flex;gap:18px;align-items:center;padding:4px 2px"><div style="font-size:46px;line-height:1;color:${me.total >= 60 ? 'var(--up)' : me.total <= 40 ? 'var(--dn)' : 'var(--amber)'}">${num(me.total, 0)}<small style="font-size:16px;color:var(--dim)"> /100</small></div>
        <div class="kv2" style="flex:1"><span>Rang</span><b>${me.rank} / ${N}</b><span>Univers</span><b>${U0}${isBRVM(s) ? (me.bank ? ' · groupe banques' : ' · groupe hors banques') : ''}</b><span>Facteurs disponibles</span><b>${me.nf} / 6</b><span>Pondération</span><b>${Object.values(SU.W).every(v => v === 1) ? 'égale' : 'personnalisée'}</b></div></div>
        <div class="cv" id="scB" style="height:220px"></div>`, { lect: 'Barres = score de chaque facteur (centile 0-100) ; trait = médiane de l’univers. Un score élevé dit que le titre se classe bien <b>par rapport aux autres</b> sur ces critères, pas qu’il montera.' })}
      ${pn('Meilleurs scores', 'SCOR', `<table class="t"><tbody>${SU.ranked.slice(0, 10).map(r => `<tr data-sec="${r.id}" data-to="SCOR" class="${r.id === s.id ? 'cur' : ''}"><td class="l">${r.rank}</td><td class="l tk">${r.id}</td><td class="l nm">${esc(r.s.short || r.s.n)}</td><td style="background:${scoreCol(r.total)};color:#fff">${num(r.total, 0)}</td></tr>`).join('')}</tbody></table>`, { np: true })}</div>
    ${pn('Détail des mesures', 'SCOR', `<table class="t"><thead><tr><th class="l">Mesure</th><th>${esc(s.id)}</th><th>Médiane</th><th>Centile</th><th>Rang</th></tr></thead><tbody>${detail}</tbody></table>`, { np: true, lect: `Valorisation, qualité et croissance comparées ${isBRVM(s) ? (me.bank ? 'aux banques de la BRVM' : 'aux sociétés de la BRVM hors banques') : 'aux actions US suivies'} ; momentum, rendement et volatilité comparés à tout le marché. Données : comptes du dernier exercice publié, cours et dividendes du jour. n.d. = donnée non publiée, jamais estimée.` })}</div>`;
  barChart($('scB'), { labels: fac.map(f => f.l), values: fac.map(f => f.v == null ? NaN : f.v), fmt: v => num(v, 0), labelsOnBars: true, colors: fac.map(f => f.v == null ? '#333' : f.v >= 60 ? '#2fd26a' : f.v <= 40 ? '#ff3d4d' : '#f9a33a'), refs: [{ v: 50, color: '#5e5e5e', label: '' }] });
};

/* ------------------------------------------------------------------ LQA : liquidité et coûts de transaction */
function rollSpread(c) { const d = []; for (let i = 1; i < c.length; i++) d.push(c[i] - c[i - 1]); let cv = 0, n = 0; const m1 = U.mean(d.slice(1)), m0 = U.mean(d.slice(0, -1)); for (let i = 1; i < d.length; i++) { cv += (d[i] - m1) * (d[i - 1] - m0); n++; } cv /= Math.max(1, n - 1); const p = U.mean(c); return cv < 0 ? 2 * Math.sqrt(-cv) / p : null; }
function csSpread(h, l) { const out = []; for (let i = 1; i < h.length; i++) { if (!(h[i] > 0 && l[i] > 0 && h[i - 1] > 0 && l[i - 1] > 0)) continue; const b = Math.log(h[i] / l[i]) ** 2 + Math.log(h[i - 1] / l[i - 1]) ** 2, g = Math.log(Math.max(h[i], h[i - 1]) / Math.min(l[i], l[i - 1])) ** 2;
  const k = 3 - 2 * Math.SQRT2, a = (Math.sqrt(2 * b) - Math.sqrt(b)) / k - Math.sqrt(g / k), s_ = 2 * (Math.exp(a) - 1) / (1 + Math.exp(a)); out.push(Math.max(0, s_)); } return out.length >= 10 ? U.mean(out) : null; }
PAGES.LQA = async (m, alive) => {
  const s = sec(ST.sec), brvm = isBRVM(s), ccy = s.ccy; setTitle('Liquidity Assessment');
  const [S, CAL] = await Promise.all([series(s.id), brvm ? series('BRVMC') : series(s.bench && Q.by[s.bench] ? s.bench : 'QQQ')]); if (!alive()) return;
  const P = lsGet('lqa.' + (brvm ? 'b' : 'u'), { q: brvm ? 10e6 : 1e6, p: 20, fee: '', days: 5 });
  const n = S.c.length, valOf = i => S.val && S.val[i] ? S.val[i] : (S.v[i] || 0) * S.c[i];
  const cal = CAL.x.filter(d => d > S.x[Math.max(0, n - 400)]); const have = new Map(S.x.map((d, i) => [d, i]));
  const win = k => { const ds = cal.slice(-k); const vals = ds.map(d => have.has(d) ? valOf(have.get(d)) : 0); return { ds, vals, zero: vals.filter(v => !v).length, traded: vals.filter(v => v > 0) }; };
  const W20 = win(20), W60 = win(60), W250 = win(250);
  const mean = a => a.length ? a.reduce((x, y) => x + y, 0) / a.length : null;
  const adv20 = mean(W20.vals), adv60 = mean(W60.vals), med60 = medA(W60.vals), medT60 = medA(W60.traded), freq = W250.traded.length / Math.max(1, W250.vals.length);
  const cv60 = W60.traded.length > 5 ? U.std(W60.traded) / mean(W60.traded) : null;
  const k60 = Math.max(1, n - 60), lr = []; for (let i = k60; i < n; i++) if (S.c[i - 1] > 0) lr.push(Math.log(S.c[i] / S.c[i - 1])); const sd = U.std(lr);
  const roll = rollSpread(S.c.slice(-61)), cs = csSpread(S.h.slice(-61), S.l.slice(-61)), spr = [roll, cs].filter(x => x != null && isFinite(x)); const sprE = spr.length ? spr.reduce((a, b) => a + b, 0) / spr.length : null;
  let ami = 0, an = 0; for (let i = k60; i < n; i++) { const v = valOf(i); if (v > 0 && S.c[i - 1] > 0) { ami += Math.abs(S.c[i] / S.c[i - 1] - 1) / v; an++; } } ami = an ? ami / an * 1e6 : null;
  const U0 = uniOf(s), liqRank = U0.filter(x => (x.liq || 0) > (s.liq || 0)).length + 1, liqPct = prank(U0.map(x => x.liq), s.liq, 1);
  const fee = P.fee === '' || P.fee == null ? null : +P.fee / 100, part = P.p / 100, base = medT60 || med60 || adv60;
  const cost = Q_ => { const imp = sd && base ? sd * Math.sqrt(Q_ / base) : null; const half = sprE != null ? sprE / 2 : null; return { imp, half, rt: imp != null && half != null ? 2 * (half + imp) + (fee != null ? 2 * fee : 0) : null }; };
  const daysTo = Q_ => base ? Q_ / (part * base) / Math.max(.05, freq) : null;
  const recSize = base ? P.days * part * base * freq : null;
  const sizes = (brvm ? [1e6, 5e6, 1e7, 5e7, 1e8, 5e8] : [1e5, 1e6, 1e7, 1e8, 1e9]).concat([P.q]).sort((a, b) => a - b).filter((v, i, a) => a.indexOf(v) === i);
  const C = cost(P.q);
  m.innerHTML = `<div class="tools gpr"><span class="tlab">Position (${esc(ccy)})</span><input class="ofld" id="lqQ" style="width:130px" value="${num(P.q, 0)}"><span class="tlab">Part max. du volume / séance</span><input class="ofld ma" id="lqP" value="${P.p}">%
      <span class="tlab">Frais de courtage par ordre</span><input class="ofld ma" id="lqF" value="${P.fee}" placeholder="%" title="Barème de votre SGI / courtier, en % ; vide = non inclus">%<span class="tlab">Sortie visée en</span><input class="ofld ma" id="lqD" value="${P.days}">séances<button class="tb rd" id="lqGo">Calculer</button></div>
    <div class="grid c2"><div class="grid" style="align-content:start">
      ${pn(`${esc(s.tk)} · liquidité`, 'LQA', `<div class="kv2"><span class="h">Montants échangés</span><span>Moyenne 20 séances</span><b>${big(adv20)} ${ccy}</b><span>Moyenne 60 séances</span><b>${big(adv60)} ${ccy}</b><span>Médiane 60 séances (jours avec échange)</span><b>${big(medT60)} ${ccy}</b>
        <span>Tendance (moy. 20 / moy. 60)</span><b>${adv60 ? pctS(adv20 / adv60 - 1, 0) : '—'}</b><span>Dispersion (coef. de variation 60 s.)</span><b>${cv60 != null ? num(cv60, 2) : '—'}</b>
        <span class="h">Fréquence</span><span>Séances sans échange (20 / 60 / 250)</span><b>${W20.zero} / ${W60.zero} / ${W250.zero}</b><span>Taux de cotation sur 250 séances</span><b>${num(freq * 100, 0)}%</b>
        <span class="h">Coûts implicites (estimations)</span><span>Fourchette estimée (Roll)</span><b>${roll != null ? num(roll * 100, 2) + '%' : '<i class="dm">n.d.</i>'}</b><span>Fourchette estimée (Corwin-Schultz)</span><b>${cs != null ? num(cs * 100, 2) + '%' : '<i class="dm">n.d.</i>'}</b>
        <span>Illiquidité d’Amihud (|r| par M ${ccy})</span><b>${ami != null ? num(ami * 100, 3) + '%' : '—'}</b><span>Volatilité quotidienne (60 s.)</span><b>${num(sd * 100, 2)}%</b>
        <span class="h">Classement</span><span>Rang de liquidité</span><b>${liqRank} / ${U0.length}</b><span>Score de liquidité (centile)</span><b>${liqPct != null ? num(liqPct, 0) + ' / 100' : '—'}</b></div>`,
        { lect: `Séances comptées sur le calendrier ${brvm ? 'du BRVM Composite' : 'de ' + esc(CAL.id)} ; une séance sans ligne de cotation = sans échange. Fourchettes : estimateurs statistiques tirés des cours (Roll 1984 ; Corwin-Schultz 2012 sur plus haut / plus bas), pas des fourchettes affichées.` })}
      ${pn('Montant échangé par séance (250 séances)', 'LQA', cvb('lqC', 190))}</div>
      <div class="grid" style="align-content:start">
      ${pn(`Position de ${num(P.q, 0)} ${ccy}`, 'LQA', `<div class="kv2"><span>Part du volume quotidien médian</span><b>${base ? num(P.q / base * 100, 1) + '%' : '—'}</b><span>Délai de sortie à ${P.p} % du volume</span><b class="${daysTo(P.q) > P.days ? 'dn' : 'up'}">${daysTo(P.q) != null ? num(daysTo(P.q), 1) + ' séances' : '—'}</b>
        <span>Demi-fourchette estimée</span><b>${C.half != null ? num(C.half * 100, 2) + '%' : '—'}</b><span>Impact de marché estimé</span><b>${C.imp != null ? num(C.imp * 100, 2) + '%' : '—'}</b><span>Frais (saisis)</span><b>${fee != null ? num(fee * 100, 2) + '% × 2' : '<i class="dm">non saisis</i>'}</b>
        <span>Coût aller-retour estimé</span><b class="yl">${C.rt != null ? num(C.rt * 100, 2) + '% · ' + big(C.rt * P.q) + ' ' + ccy : '—'}</b>
        <span class="h">Taille de position conseillée</span><span>Sortie en ${P.days} séances à ${P.p} % du volume</span><b class="yl">${recSize ? big(recSize) + ' ' + ccy : '—'}</b></div>`,
        { lect: '<b>Hypothèses</b> (modifiables ci-dessus) : impact = volatilité quotidienne × √(taille ÷ volume médian) — modèle « racine carrée » usuel, coefficient 1 ; délai = taille ÷ (part du volume × volume médian) corrigé du taux de cotation. Ce sont des ordres de grandeur, pas des coûts garantis.' })}
      ${pn('Délai et coût selon la taille', 'LQA', `<table class="t"><thead><tr><th>Taille (${ccy})</th><th>% vol. médian</th><th>Délai (séances)</th><th>Impact</th><th>Aller-retour</th></tr></thead><tbody>${sizes.map(q => { const c = cost(q), d = daysTo(q); return `<tr class="${q === P.q ? 'cur' : ''}"><td>${big(q)}</td><td>${base ? num(q / base * 100, 1) + '%' : '—'}</td><td class="${d > P.days ? 'dn' : ''}">${d != null ? num(d, 1) : '—'}</td><td>${c.imp != null ? num(c.imp * 100, 2) + '%' : '—'}</td><td>${c.rt != null ? num(c.rt * 100, 2) + '%' : '—'}</td></tr>`; }).join('')}</tbody></table>`, { np: true })}</div></div>`;
  const vv = W250.vals; barChart($('lqC'), { labels: W250.ds.map(d => fd(d).slice(0, 5)), values: vv, fmt: v => big(v), colors: vv.map(v => v ? '#3d7cc9' : '#ff3d4d'), axisFmt: v => big(v), padL: 62 });
  $('lqGo').onclick = () => { const pq = +$('lqQ').value.replace(/[\s ,]/g, '').replace(/[^\d.]/g, ''); const np = { q: pq > 0 ? pq : P.q, p: Math.min(100, Math.max(1, +$('lqP').value || 20)), fee: $('lqF').value.trim().replace(',', '.'), days: Math.max(1, +$('lqD').value || 5) }; lsSet('lqa.' + (brvm ? 'b' : 'u'), np); render(); };
};

/* ------------------------------------------------------------------ TRA : rendement total (dividendes réinvestis) contre cours seul */
/* BRVM : dividendes officiels (avis, dates exactes) complétés par les dividendes par exercice des comptes quand la date
   de détachement n'est pas recensée : placés à la date habituelle de la société (estimation signalée). */
async function trSeriesX(s, S) {
  if (!isBRVM(s) || s.cls !== 'Equity') { const tr = await trSeries(s, S); const k = S.div ? S.div.findIndex(v => v > 0) : -1; return { tr, est: [], cov: null, covY: k >= 0 ? Math.floor(S.x[k] / 10000) : null }; }
  const [DV, F] = await Promise.all([getJSON('dividends.json'), faJSON(s.id).catch(() => null)]);
  const mine = DV.filter(x => x.t === s.id && x.dps && (x.det || x.pay)); const div = new Array(S.x.length).fill(0), est = [];
  const put = (d, v) => { const k = S.x.findIndex(x => x >= d); if (k > 0) div[k] += v; };
  for (const x of mine) put(s2i((x.det || x.pay).slice(0, 10)), x.dps);
  const md = mine.length ? medA(mine.map(x => +(x.det || x.pay).slice(5, 7) * 100 + +(x.det || x.pay).slice(8, 10))) : 615;
  const known = new Set(mine.map(x => +x.ex)); const firstKnown = mine.length ? Math.min(...mine.map(x => +x.ex)) : null;
  if (F && F.Y && F.Y.dps) F.Y.y.forEach((y, i) => { const v = F.Y.dps[i]; if (v > 0 && !known.has(+y) && (!firstKnown || +y < firstKnown)) { put((+y + 1) * 10000 + md, v); est.push(+y); } });
  const tr = [S.c[0]]; for (let i = 1; i < S.c.length; i++) tr.push(tr[i - 1] * (S.c[i] + div[i]) / S.c[i - 1]);
  const yrsAll = est.concat(mine.map(x => +x.ex)); const covY = yrsAll.length ? Math.min(...yrsAll) + 1 : null; /* 1re année où un dividende est compté */
  return { tr, est: est.sort(), cov: firstKnown, md, covY };
}
PAGES.TRA = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Total Return Analysis'); const S = await series(s.id); if (!alive()) return;
  const TX = await trSeriesX(s, S); if (!alive()) return; const TR = TX.tr; const n = S.c.length, x = S.x, last = x[n - 1];
  const bId = s.bench && Q.by[s.bench] && s.bench !== s.id ? s.bench : null; const B = bId ? await series(bId) : null; if (!alive()) return;
  const BTR = B ? await trSeries(Q.by[bId], B).catch(() => null) : null; const bMap = B ? new Map(B.x.map((d, i) => [d, i])) : null;
  /* base = dernière séance à la date de départ ou avant (comme le résumé) ; période pas couverte par la série : ligne absente */
  const at = d => baseIdx(x, d);
  const per = ['1M', '3M', '6M', 'YTD', '1A', '3A', '5A', '10A'].map(p => [p, perStart(last, p)]).concat([['Origine', 0]]);
  const yrsOf = (i0) => (x.length && i0 < n - 1 ? (Date.UTC(last / 10000 | 0, (last / 100 | 0) % 100 - 1, last % 100) - Date.UTC(x[i0] / 10000 | 0, (x[i0] / 100 | 0) % 100 - 1, x[i0] % 100)) / 31557600000 : 0);
  const bAt = (d, A) => { if (!B) return null; const j = idxAtOrBefore(B.x, d); if (j < 0) return null; return A ? A[B.x.length - 1] / A[j] - 1 : B.c[B.c.length - 1] / B.c[j] - 1; };
  const rows = per.map(([l, d]) => { const i0 = d ? at(d) : 0; if (i0 < 0 || i0 >= n - 1) return null; const pr = S.c[n - 1] / S.c[i0] - 1, tr = TR ? TR[n - 1] / TR[i0] - 1 : pr, y = yrsOf(i0); const ann = v => y >= .98 ? Math.pow(1 + v, 1 / y) - 1 : null;
    return { l, i0, pr, tr, dv: tr - pr, apr: ann(pr), atr: ann(tr), b: bAt(x[i0]), btr: bAt(x[i0], BTR), y }; }).filter(Boolean);
  const yrs = {}; for (let i = 1; i < n; i++) { const y = Math.floor(x[i] / 10000); (yrs[y] = yrs[y] || []).push(i); }
  const DV = isBRVM(s) ? (await getJSON('dividends.json')).filter(d => d.t === s.id && d.dps) : []; if (!alive()) return;
  const yRows = Object.entries(yrs).map(([y, ix]) => { const i0 = ix[0] - 1, i1 = ix[ix.length - 1]; const pr = S.c[i1] / S.c[i0] - 1, tr = TR ? TR[i1] / TR[i0] - 1 : pr;
    const dps = isBRVM(s) ? DV.filter(d => (d.det || d.pay || '').slice(0, 4) === y).reduce((a, d) => a + d.dps, 0) : ix.reduce((a, i) => a + (S.div[i] || 0), 0);
    const e = TX.est.includes(+y - 1); return { y, pr, tr, dps, e, yi: dps / S.c[i0] }; }).reverse();
  const st = ST.tra = ST.tra || { r: '5A' }; const r0 = per.find(p => p[0] === st.r) || per[6]; const i0 = r0[1] ? Math.max(0, idxAtOrBefore(x, r0[1])) : 0;
  m.innerHTML = `<div class="grid c2"><div class="grid" style="align-content:start">
      ${pn(`${esc(s.tk)} · rendement total contre cours seul`, 'TRA', `<table class="t"><thead><tr><th class="l">Période</th><th>Cours seul</th><th>Rendement total</th><th>Apport des dividendes</th><th>Annualisé (cours)</th><th>Annualisé (total)</th>${B ? `<th>${esc(bId)} (cours)</th>` : ''}</tr></thead><tbody>
        ${rows.map(r => { const und = TX.covY && x[r.i0] < TX.covY * 10000; return `<tr><td class="l am">${r.l}</td><td>${pc(r.pr, 1)}</td><td class="yl">${pc(r.tr, 1)}${und ? ' <span class="am" title="dividendes non recensés avant ' + TX.covY + ' : sous-estimé">*</span>' : ''}</td><td>${pc(r.dv, 1)}</td><td>${r.apr != null ? pc(r.apr, 1) : '—'}</td><td>${r.atr != null ? pc(r.atr, 1) : '—'}</td>${B ? `<td>${pc(r.b, 1)}</td>` : ''}</tr>`; }).join('')}</tbody></table>`,
        { np: true, lect: `Rendement total : dividendes réinvestis à la date de détachement${isBRVM(s) ? ' (montants nets)' : ''}, sans frais ni impôt.${TX.covY ? ` <b>*</b> = période commençant avant ${TX.covY} : les dividendes antérieurs ne sont pas recensés, le rendement total est sous-estimé.` : ''}${TX.est.length ? ` <b>Dividendes des exercices ${TX.est.join(', ')}</b> : montants des comptes, placés à la date habituelle de détachement de la société (${String(TX.md).padStart(4, '0').slice(2)}/${String(TX.md).padStart(4, '0').slice(0, 2)}) faute de date publiée — estimation.` : ''} ${isBRVM(s) ? 'Le BRVM Composite est un indice de prix (dividendes non inclus) : la BRVM publie depuis le 2 janvier 2026 un BRVM Composite Total Return, non encore relevé ici.' : ''}` })}
      ${pn('Par année', 'TRA', `<div class="tw" style="max-height:380px"><table class="t"><thead><tr><th class="l">Année</th><th>Cours seul</th><th>Rendement total</th><th>Dividendes / action</th><th>Rendement en début d’année</th></tr></thead><tbody>${yRows.map(r => `<tr><td class="l am">${r.y}</td><td>${pc(r.pr, 1)}</td><td class="yl">${pc(r.tr, 1)}${r.e ? ' <span class="est" title="dividende placé à une date estimée">e</span>' : ''}</td><td>${r.dps ? num(r.dps, 2) : r.e ? '<span class="est">comptes</span>' : '—'}</td><td>${r.dps ? num(r.yi * 100, 2) + '%' : '—'}</td></tr>`).join('')}</tbody></table></div>`, { np: true })}</div>
    <div class="pn"><div class="tools">${per.map(([l]) => `<button class="tb ${st.r === l ? 'on' : ''}" data-tr="${l}">${l}</button>`).join('')}</div><div class="cv" id="trC" style="height:max(360px, calc(100vh - 330px - var(--nwh, 90px)))"></div></div></div>`;
  m.querySelectorAll('[data-tr]').forEach(b => b.onclick = () => { st.r = b.dataset.tr; render(); });
  const base = S.c[i0], baseT = TR ? TR[i0] : base; const pr = S.c.map((v, i) => i < i0 ? null : v / base * 100), tr = TR ? TR.map((v, i) => i < i0 ? null : v / baseT * 100) : null;
  const ser = [{ type: 'area', y: pr, color: '#ffffff', w: 1.2, grad: ['rgba(34,78,146,.7)', 'rgba(3,20,54,.6)'], label: 'Cours seul (base 100)', fmt: v => num(v, 1) }];
  if (tr) ser.push({ y: tr, color: '#f9a33a', w: 1.6, label: 'Rendement total (base 100)', fmt: v => num(v, 1) });
  if (B) { const bb = x.map(d => bMap.has(d) ? B.c[bMap.get(d)] : null); let lv = null; const bf = bb.map(v => (v != null ? (lv = v) : lv)); const b0 = bf[i0] || bf.find((v, i) => i >= i0 && v); ser.push({ y: bf.map((v, i) => i < i0 || !b0 || v == null ? null : v / b0 * 100), color: '#5fd0ea', w: 1, label: bId + ' (cours)', fmt: v => num(v, 1) }); }
  new TSChart($('trC'), { panes: [{ h: 1 }], grid: 'dot', xticks: bbgTicks }).set({ x, series: ser }, [i0, n - 1]);
};

/* ------------------------------------------------------------------ ANOM : anomalies statistiques (calculées chaque relevé, anomalies.json) */
PAGES.ANOM = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Anomaly Monitor'); const tab = tabState('ANOM', 't'); setTabs([['t', 'Ce titre'], ['m', 'Tout le marché']], tab, k => { ST.tab.ANOM = k; render(); });
  const A = await getJSON('anomalies.json').catch(() => null); if (!alive()) return;
  if (!A) { m.innerHTML = pn('Anomalies', 'ANOM', '<div class="empty">Analyse en cours de calcul (premier relevé après la mise à jour du terminal).</div>'); return; }
  const SEV = { 3: ['forte', 'dn'], 2: ['à vérifier', 'am'], 1: ['info', 'up'] };
  const row = a => `<div class="flag ${SEV[a.sv][1]}"><b class="${SEV[a.sv][1]}">${esc(SEV[a.sv][0].toUpperCase())}</b> · <span class="am">${esc(a.k)}</span> · ${a.d ? fd(a.d) + ' · ' : ''}${esc(a.m)}${a.v != null ? ` <span class="dm">(${esc(a.vl || '')})</span>` : ''}</div>`;
  const note = `Alertes <b>statistiques</b> à vérifier, pas des preuves : un écart peut avoir une explication (dividende, opération sur titre, publication). Calcul du ${A.ts ? new Date(A.ts * 1000).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'} sur les cours, volumes, comptes et dividendes. Seuils : rendement > 4 écarts robustes (MAD 60 séances), montant échangé > 5 × la médiane 60, écart à la moyenne 200 au-delà du 2e/98e centile de 3 ans, cours inchangé ≥ 10 séances…`;
  if (tab === 'm') {
    const all = Object.entries(A.by || {}).flatMap(([id, L]) => L.map(a => ({ ...a, id }))).filter(a => Q.by[a.id]).sort((a, b) => b.sv - a.sv || (b.d || 0) - (a.d || 0));
    const st = ST.anm = ST.anm || { mk: 'BRVM' }; const L = all.filter(a => (Q.by[a.id].mkt === 'BRVM') === (st.mk === 'BRVM'));
    m.innerHTML = pn(`Anomalies · ${st.mk === 'BRVM' ? 'BRVM' : 'États-Unis'} · ${L.length}`, 'ANOM', `<div class="tw" style="max-height:72vh"><table class="t"><thead><tr><th class="l">Niveau</th><th class="l">Titre</th><th class="l">Société</th><th class="l">Type</th><th class="l">Date</th><th class="l">Constat</th></tr></thead><tbody>
      ${L.map(a => `<tr data-sec="${a.id}" data-to="ANOM"><td class="l ${SEV[a.sv][1]}">${SEV[a.sv][0]}</td><td class="l tk">${a.id}</td><td class="l nm">${esc(Q.by[a.id].short || Q.by[a.id].n)}</td><td class="l am">${esc(a.k)}</td><td class="l">${a.d ? fd(a.d) : '—'}</td><td class="l" style="white-space:normal">${esc(a.m)}</td></tr>`).join('') || '<tr><td class="l dm" colspan="6">Aucune anomalie détectée.</td></tr>'}</tbody></table></div>`,
      { np: true, tools: `<button class="tb ${st.mk === 'BRVM' ? 'on' : ''}" data-mk="BRVM">BRVM</button><button class="tb ${st.mk === 'US' ? 'on' : ''}" data-mk="US">États-Unis</button>`, lect: note });
    m.querySelectorAll('[data-mk]').forEach(b => b.onclick = () => { st.mk = b.dataset.mk; render(); });
    return;
  }
  const L = (A.by || {})[s.id] || [];
  const S = await series(s.id); if (!alive()) return; const n = S.c.length, k0 = Math.max(0, n - 250);
  m.innerHTML = `<div class="grid c2">${pn(`${esc(s.tk)} · anomalies détectées (${L.length})`, 'ANOM', L.length ? L.map(row).join('') : '<div class="empty">Aucune anomalie statistique détectée sur ce titre.</div>', { lect: note })}
    ${pn('Cours et montants échangés (250 séances)', 'ANOM', cvb('anC', 330))}</div>`;
  const marks = L.filter(a => a.d).map(a => ({ i: S.x.indexOf(a.d), v: S.c[S.x.indexOf(a.d)], up: a.sv < 2 })).filter(o => o.i >= 0);
  const vals = S.x.map((_, i) => S.val && S.val[i] ? S.val[i] : (S.v[i] || 0) * S.c[i]);
  new TSChart($('anC'), { panes: [{ h: 2 }, { h: .8, zero: true }], grid: 'dot', xticks: bbgTicks }).set({ x: S.x, series: [{ type: 'area', y: S.c, color: '#fff', w: 1.1, grad: ['rgba(34,78,146,.9)', 'rgba(3,20,54,.85)'], label: s.id, fmt: v => px(s, v) }, { type: 'marks', m: marks }, { pane: 1, type: 'bar', y: vals, colorFn: () => 'rgba(215,215,215,.75)', label: 'Montant', fmt: v => big(v) }] }, [k0, n - 1]);
};

/* ------------------------------------------------------------------ MODL : scénarios bull / base / bear (hypothèses séparées des données publiées) */
PAGES.MODL = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Scenario Valuation Model'); const [F, S] = await Promise.all([faJSON(s.id).catch(() => null), series(s.id)]); if (!alive()) return;
  if (!F || !F.Y) { m.innerHTML = pn('Scénarios', 'MODL', '<div class="empty">Comptes non disponibles.</div>'); return; }
  const Y = yDerived(F), us = F.mkt === 'US', Uu = unitOf(F); const idx = Y.y.map((y, i) => i).filter(i => Y.rev[i] != null && Y.ni[i] != null);
  if (!idx.length) { m.innerHTML = pn('Scénarios', 'MODL', '<div class="empty">Pas d’exercice complet (CA et résultat) dans les sources.</div>'); return; }
  const L = idx[idx.length - 1], yr0 = us ? Math.floor(Y.y[L] / 10000) : Y.y[L], rev0 = Y.rev[L], ni0 = Y.ni[L], eps0 = Y.eps[L], sh = eps0 ? ni0 / eps0 : null, price = s.last;
  const mult = us ? 1 : 1e6; /* BRVM : comptes en millions de FCFA */
  const pay0 = us ? (Y.div && Y.div[L] != null && ni0 > 0 ? Math.abs(Y.div[L]) / ni0 : 0) : (Y.payout && Y.payout[L] != null ? Y.payout[L] : (s.dps && eps0 ? s.dps / eps0 : 0));
  const g5 = cagrA(Y.rev.slice(0, L + 1), 5) ?? cagrA(Y.rev.slice(0, L + 1), 3) ?? .05, nm0 = ni0 / rev0;
  const peH = (F.mh && F.mh.pe || []).filter(v => v > 0 && v < 200).slice(-260); const peMed = peH.length > 20 ? medA(peH) : null; const peNow = F.pe > 0 ? F.pe : peMed || 10; const pe0 = peNow;
  const cl = (v, a, b) => Math.max(a, Math.min(b, v));
  const def = { N: 5, sc: { bear: { g: cl(g5 - .04, -.1, .2), m: Math.max(0, nm0 - .02), p: pay0, pe: Math.min(peNow * .8, peMed || peNow * .8) }, base: { g: cl(g5, -.05, .15), m: nm0, p: pay0, pe: peNow }, bull: { g: cl(g5 + .04, -.02, .25), m: nm0 + .02, p: pay0, pe: peNow * 1.2 } } };
  const key = 'modl.' + s.id; let H = lsGet(key, null); if (!H || !H.sc) H = def;
  const run = h => { const out = {}; for (const k of ['bear', 'base', 'bull']) { const p = h.sc[k]; let rev = rev0, cum = 0; const yrs = [];
      for (let t = 1; t <= h.N; t++) { rev *= 1 + p.g; const ni = rev * p.m, eps = sh ? ni / sh : null, dps = eps != null ? eps * p.p : null; cum += dps || 0; yrs.push({ y: yr0 + t, rev, ni, eps, dps }); }
      const eN = yrs[h.N - 1].eps, target = eN != null ? eN * p.pe * (us ? 1 : mult) : null; const tgt = us ? target : (eN != null ? eN * p.pe : null);
      const tot = tgt != null ? (tgt + cum) / price : null; out[k] = { yrs, tgt, cum, ann: tot > 0 ? Math.pow(tot, 1 / h.N) - 1 : null, annPx: tgt > 0 ? Math.pow(tgt / price, 1 / h.N) - 1 : null, annDv: cum && price ? Math.pow(1 + cum / price, 1 / h.N) - 1 : null }; } return out; };
  const R = run(H), C = { bear: '#ff3d4d', base: '#f9a33a', bull: '#2fd26a' }, LB = { bear: 'Bear', base: 'Base', bull: 'Bull' };
  const hist = idx.slice(-4);
  const inp = (k, f, v, d) => `<input class="ofld ma" style="width:56px;background:#ffd84d" data-k="${k}" data-f="${f}" value="${num(v, d)}">`;
  const money = v => v == null ? '—' : num(v * Uu.k, Uu.d);
  m.innerHTML = `<div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">${['bull', 'base', 'bear'].map(k => `<div class="pn"><div class="pt" style="background:${C[k]};color:#000">${LB[k]} · ${H.N} ans</div><div class="kv2" style="padding:4px 7px"><span>Rendement annuel attendu</span><b class="${cls(R[k].ann)}">${R[k].ann != null ? pc(R[k].ann, 1) : '—'}</b><span>dont cours</span><b>${R[k].annPx != null ? pc(R[k].annPx, 1) : '—'}</b><span>dont dividendes</span><b>${R[k].annDv != null ? pc(R[k].annDv, 1) : '—'}</b><span>Cours théorique (exercice ${yr0 + H.N})</span><b>${R[k].tgt != null ? px(s, R[k].tgt) : '—'}</b></div></div>`).join('')}</div>
    <div class="pn"><div class="pt">Cours (5 ans) et trajectoires des scénarios<span class="sel">cours actuel ${px(s, price)} ${esc(s.ccy)} · horizon ${yr0 + H.N}</span></div><div class="cv" id="moC" style="height:300px"></div></div>
    ${pn(`${esc(s.tk)} · comptes publiés et hypothèses (${esc(Uu.lab)}, par action en ${esc(s.ccy)})`, 'MODL', `<div class="tw"><table class="t acc"><thead><tr><th class="l"></th>${hist.map(i => `<th>${us ? yLab(Y.y[i]) : Y.y[i]}<br><span class="dm">publié</span></th>`).join('')}${['bear', 'base', 'bull'].map(k => `<th style="background:${C[k]}33">${yr0 + H.N}<br><span style="color:${C[k]}">${LB[k]}</span></th>`).join('')}</tr></thead><tbody>
      <tr><td class="l">Chiffre d’affaires</td>${hist.map(i => `<td>${money(Y.rev[i])}</td>`).join('')}${['bear', 'base', 'bull'].map(k => `<td>${money(R[k].yrs[H.N - 1].rev)}</td>`).join('')}</tr>
      <tr><td class="l">Croissance annuelle du CA</td>${hist.map(i => `<td class="dm">${i ? pctS(gr(Y.rev, i), 1) || '' : ''}</td>`).join('')}${['bear', 'base', 'bull'].map(k => `<td class="est-b">${inp(k, 'g', H.sc[k].g * 100, 1)} %</td>`).join('')}</tr>
      <tr><td class="l">Marge nette</td>${hist.map(i => `<td>${P1(Y.ni[i] / Y.rev[i])}</td>`).join('')}${['bear', 'base', 'bull'].map(k => `<td class="est-b">${inp(k, 'm', H.sc[k].m * 100, 1)} %</td>`).join('')}</tr>
      <tr><td class="l">Résultat net</td>${hist.map(i => `<td>${money(Y.ni[i])}</td>`).join('')}${['bear', 'base', 'bull'].map(k => `<td>${money(R[k].yrs[H.N - 1].ni)}</td>`).join('')}</tr>
      <tr><td class="l">BPA</td>${hist.map(i => `<td>${num(Y.eps[i], 2)}</td>`).join('')}${['bear', 'base', 'bull'].map(k => `<td>${num(R[k].yrs[H.N - 1].eps, 2)}</td>`).join('')}</tr>
      <tr><td class="l">Taux de distribution</td>${hist.map(i => `<td>${us ? P1(Y.div && Y.div[i] != null && Y.ni[i] > 0 ? Math.abs(Y.div[i]) / Y.ni[i] : null) : P1(Y.payout ? Y.payout[i] : null)}</td>`).join('')}${['bear', 'base', 'bull'].map(k => `<td class="est-b">${inp(k, 'p', H.sc[k].p * 100, 0)} %</td>`).join('')}</tr>
      <tr><td class="l">PER (fin de période)</td>${hist.map(i => { const ye = (us ? Y.y[i] : Y.y[i] * 10000 + 1231); let k = -1; for (let j = S.x.length - 1; j >= 0; j--) if (S.x[j] <= ye) { k = j; break; } return `<td>${k >= 0 && Y.eps[i] > 0 ? num(S.c[k] / Y.eps[i], 1) + ' x' : '—'}</td>`; }).join('')}${['bear', 'base', 'bull'].map(k => `<td class="est-b">${inp(k, 'pe', H.sc[k].pe, 1)} x</td>`).join('')}</tr>
      <tr><td class="l">Dividendes cumulés / action</td>${hist.map(() => '<td></td>').join('')}${['bear', 'base', 'bull'].map(k => `<td>${num(R[k].cum, 2)}</td>`).join('')}</tr></tbody></table></div>
      <div class="tools"><span class="tlab">Horizon</span><input class="ofld ma" id="moN" value="${H.N}"> ans<button class="tb rd" id="moGo">Recalculer</button><button class="tb" id="moR">Hypothèses par défaut</button></div>`,
      { np: true, lect: `<b>Cases jaunes = hypothèses</b> (modifiables, enregistrées dans ce navigateur), <b>colonnes « publié » = comptes publiés</b>. Par défaut : croissance base = TCAM du CA sur 5 ans (${P1(g5)}) bornée, marge = dernière marge publiée, distribution = dernier taux, PER base = PER actuel (${num(peNow, 1)} x, sans changement de multiple), bull = +20 %, bear = le plus bas entre −20 % et la médiane de ses 5 dernières années${peMed ? ' (' + num(peMed, 1) + ' x)' : ''} ; bull/bear = ±4 points de croissance, ±2 points de marge. Rendement = (cours théorique + dividendes cumulés non réinvestis) ÷ cours actuel, annualisé. Actions en circulation supposées constantes. Ce sont des scénarios, pas des prévisions.` })}`;
  $('moGo').onclick = () => { const h = JSON.parse(JSON.stringify(H)); m.querySelectorAll('[data-k]').forEach(i => { const v = parseFloat(i.value.replace(/\s| /g, '').replace(',', '.')); if (isFinite(v)) h.sc[i.dataset.k][i.dataset.f] = i.dataset.f === 'pe' ? v : v / 100; }); h.N = Math.max(1, Math.min(15, +$('moN').value || 5)); lsSet(key, h); render(); };
  $('moR').onclick = () => { lsSet(key, null); render(); };
  /* axe hebdomadaire : 5 ans d'historique, puis l'horizon des scénarios à la même échelle */
  const n = S.c.length, k0 = Math.max(0, n - 1300), wk = new Map(); for (let i = k0; i < n; i++) wk.set(isoWeekKey(S.x[i]), i); const wi = [...wk.values()];
  const xs = wi.map(i => S.x[i]), cs = wi.map(i => S.c[i]), last = S.x[n - 1], fut = [];
  for (let t = 1; t <= H.N * 52; t++) { const d = new Date(Date.UTC(last / 10000 | 0, (last / 100 | 0) % 100 - 1, last % 100 + 7 * t)); fut.push(d.getUTCFullYear() * 10000 + (d.getUTCMonth() + 1) * 100 + d.getUTCDate()); }
  const X = xs.concat(fut), np = xs.length;
  const path = k => X.map((_, i) => i < np - 1 ? null : R[k].tgt == null ? null : price * Math.pow(R[k].tgt / price, (i - (np - 1)) / fut.length));
  new TSChart($('moC'), { panes: [{ h: 1 }], grid: 'dot', xticks: bbgTicks }).set({ x: X, series: [{ type: 'area', y: cs.concat(fut.map(() => null)), color: '#fff', w: 1.1, grad: ['rgba(34,78,146,.85)', 'rgba(3,20,54,.8)'], label: 'Cours (hebdo)', fmt: v => px(s, v) },
    ...['bull', 'base', 'bear'].map(k => ({ y: path(k), color: C[k], w: 1.6, label: LB[k], fmt: v => px(s, v) }))] }, [0, X.length - 1]);
};

/* ------------------------------------------------------------------ PEER : comparateur de 2 à 10 sociétés + nuage de points */
const PEER_M = [['pe', 'PER', 'x'], ['pb', 'P/B', 'x'], ['ev_ebitda', 'VE/EBITDA', 'x'], ['dy', 'Rendement dividende', 'pct'], ['fcfy', 'Rendement FCF', 'pct'], ['roe', 'ROE', 'pct'], ['roic', 'ROIC', 'pct'], ['nm', 'Marge nette', 'pct'],
  ['rev_cagr3', 'CA TCAM 3 ans', 'pct'], ['eps_cagr3', 'BPA TCAM 3 ans', 'pct'], ['nd_ebitda', 'Dette nette/EBITDA', 'x'], ['ytd', 'Perf. YTD', 'pct'], ['r1y', 'Perf. 1 an', 'pct'], ['r3m', 'Perf. 3 mois', 'pct'], ['vol', 'Volatilité 1 an', 'pct'], ['beta', 'Bêta', 'num'], ['liq', 'Échanges moyens/j', 'big'], ['mcap', 'Capitalisation', 'big'], ['score', 'Score SCOR', 'int']];
PAGES.PEER = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Peer Comparison'); const tab = tabState('PEER', 't'); setTabs([['t', 'Tableau'], ['x', 'Nuage de points']], tab, k => { ST.tab.PEER = k; render(); });
  const [IDX, SU] = await Promise.all([getJSON('fa_index.json'), scoreUniverse(s)]); if (!alive()) return;
  const byFa = new Map(IDX.rows.map(r => [r.id, r])), sc = new Map(SU.rows.map(r => [r.id, r.total]));
  const val = (id, k) => { const x = Q.by[id], r = byFa.get(id) || {}; return k === 'score' ? sc.get(id) : ['ytd', 'r1y', 'r3m', 'vol', 'beta', 'liq', 'mcap'].includes(k) ? (x[k] != null ? x[k] : r[k]) : k === 'dy' ? (r.dy != null ? r.dy : x.yld) : r[k]; };
  const f = (t, v) => v == null || !isFinite(v) ? '—' : t === 'pct' ? num(v * 100, 1) + '%' : t === 'x' ? num(v, 1) + 'x' : t === 'big' ? big(v) : t === 'int' ? num(v, 0) : num(v, 2);
  const st = ST.peer = ST.peer || {}; if (st.base !== s.id) { st.base = s.id; const P = peersOf(s, IDX).filter(r => r.id !== s.id).sort((a, b) => (b.mcap || 0) - (a.mcap || 0)).slice(0, 5); st.list = [s.id].concat(P.map(r => r.id)); st.x = st.x || 'roe'; st.y = st.y || 'pb'; }
  const add = `<span class="tlab">Ajouter</span><input id="peIn" placeholder="ticker" title="2 à 10 sociétés">${st.list.map(id => `<button class="tb alt on" data-rm="${id}" title="Retirer">${id} ✕</button>`).join('')}`;
  if (tab === 't') {
    const L = st.list.filter(id => Q.by[id]);
    const body = PEER_M.map(([k, l, t]) => { const vs = L.map(id => val(id, k)), ok = vs.filter(v => v != null && isFinite(v)); const hi = ok.length > 1 ? Math.max(...ok) : null, lo = ok.length > 1 ? Math.min(...ok) : null;
      const better = ['pe', 'pb', 'ev_ebitda', 'nd_ebitda', 'vol', 'beta'].includes(k) ? -1 : 1;
      return `<tr><td class="l">${l}</td>${vs.map(v => `<td class="${v == null ? '' : (better > 0 ? v === hi : v === lo) ? 'up' : (better > 0 ? v === lo : v === hi) ? 'dn' : ''}">${f(t, v)}</td>`).join('')}<td class="dm">${f(t, medA(ok))}</td></tr>`; }).join('');
    m.innerHTML = pn(`Comparateur · ${L.length} sociétés`, 'PEER', `<div class="tw"><table class="t acc"><thead><tr><th class="l">Mesure</th>${L.map(id => `<th data-sec="${id}" data-to="DES" style="cursor:pointer" title="${esc(Q.by[id].n)}">${id}</th>`).join('')}<th>Médiane</th></tr></thead><tbody>
      <tr><td class="l">Société</td>${L.map(id => `<td class="nm" style="white-space:normal">${esc(Q.by[id].short || Q.by[id].n)}</td>`).join('')}<td></td></tr><tr><td class="l">Secteur</td>${L.map(id => `<td class="dm">${esc(Q.by[id].grp || '')}</td>`).join('')}<td></td></tr>${body}</tbody></table></div>`,
      { np: true, tools: add, lect: 'Vert = meilleure valeur du groupe, rouge = moins bonne (PER, P/B, dette, volatilité : plus bas = mieux). Attention : comparer une banque et une société industrielle sur le PER seul n’a pas de sens — utiliser P/B face au ROE pour les banques (RV). Base : comptes du dernier exercice, cours du jour.' });
  } else {
    const U0 = uniOf(s).filter(x => byFa.has(x.id) || ['ytd', 'r1y', 'r3m', 'vol', 'beta', 'liq', 'mcap'].includes(st.x) && ['ytd', 'r1y', 'r3m', 'vol', 'beta', 'liq', 'mcap'].includes(st.y));
    const sel = k => `<select class="ofld" data-ax="${k}">${PEER_M.map(([mk, l]) => `<option value="${mk}" ${st[k] === mk ? 'selected' : ''}>${l}</option>`).join('')}</select>`;
    const tX = PEER_M.find(p => p[0] === st.x)[2], tY = PEER_M.find(p => p[0] === st.y)[2];
    const pts = U0.map(x => ({ id: x.id, label: x.id, x: val(x.id, st.x), y: val(x.id, st.y), hi: st.list.includes(x.id), color: x.bank ? 'rgba(95,208,234,.85)' : 'rgba(249,163,58,.85)' })).filter(p => p.x != null && p.y != null && isFinite(p.x) && isFinite(p.y));
    const clip = (k, arr) => { const v = arr.map(p => p[k]).sort((a, b) => a - b); return [v[Math.floor(v.length * .02)], v[Math.ceil(v.length * .98) - 1]]; };
    const [xl, xh] = clip('x', pts), [yl, yh] = clip('y', pts); const P2 = pts.filter(p => p.hi || (p.x >= xl && p.x <= xh && p.y >= yl && p.y <= yh));
    const sorted = P2.slice().sort((a, b) => b.x - a.x);
    m.innerHTML = `<div class="tools"><span class="tlab">X</span>${sel('x')}<span class="tlab">Y</span>${sel('y')}<span class="tsep"></span>${add}</div>
      <div class="grid c2">${pn(`Nuage · ${isBRVM(s) ? 'BRVM' : 'actions US'} · ${P2.length} sociétés`, 'PEER', '<div class="cv" id="peS" style="height:max(420px, calc(100vh - 330px - var(--nwh, 90px)))"></div>', { lect: `${isBRVM(s) ? 'Bleu = banques, orange = autres sociétés. ' : ''}Cerclés = sociétés du comparateur. Valeurs extrêmes (2 % de chaque côté) masquées sauf sélection. Survol = détail, clic = fiche.` })}
      ${pn('Classement', 'PEER', `<div class="tw" style="max-height:calc(100vh - 330px)"><table class="t"><thead><tr><th class="l">Titre</th><th class="l">Société</th><th>${esc(PEER_M.find(p => p[0] === st.x)[1])}</th><th>${esc(PEER_M.find(p => p[0] === st.y)[1])}</th></tr></thead><tbody>${sorted.map(p => `<tr data-sec="${p.id}" data-to="PEER" class="${p.hi ? 'cur' : ''}"><td class="l tk">${p.id}</td><td class="l nm">${esc(Q.by[p.id].short || Q.by[p.id].n)}</td><td>${f(tX, p.x)}</td><td>${f(tY, p.y)}</td></tr>`).join('')}</tbody></table></div>`, { np: true })}</div>`;
    const fa = t => v => t === 'pct' ? num(v * 100, 0) + '%' : t === 'big' ? big(v) : num(v, 1);
    scatterL($('peS'), { pts: P2, fx: fa(tX), fy: fa(tY), xlab: PEER_M.find(p => p[0] === st.x)[1], ylab: PEER_M.find(p => p[0] === st.y)[1], labels: P2.length <= 60, to: 'DES', tipf: p => `<b>${esc(p.id)}</b> ${esc(Q.by[p.id].short || '')} · X ${f(tX, p.x)} · Y ${f(tY, p.y)}` });
    m.querySelectorAll('[data-ax]').forEach(e => e.onchange = () => { st[e.dataset.ax] = e.value; render(); });
  }
  const pin = $('peIn'); if (pin) pin.onkeydown = e => { if (e.key !== 'Enter') return; const r = searchSecs(pin.value).find(x => x.cls === 'Equity'); if (!r) { toast('Titre introuvable.'); return; } if (st.list.includes(r.id)) return; if (st.list.length >= 10) { toast('10 sociétés au maximum.'); return; } st.list.push(r.id); render(); };
  m.querySelectorAll('[data-rm]').forEach(b => b.onclick = () => { if (st.list.length <= 2) { toast('2 sociétés au minimum.'); return; } st.list = st.list.filter(x => x !== b.dataset.rm); render(); });
};

/* ------------------------------------------------------------------ RV : onglets (pairs et historique / juste valeur et marge de sécurité) */
PAGES.RV = async (m, alive) => {
  const s = sec(ST.sec); const tab = tabState('RV', 'c'); setTabs([['c', 'Comparables'], ['p', 'Pairs et historique'], ['f', 'Juste valeur']], tab, k => { ST.tab.RV = k; render(); });
  if (tab === 'c') return RV_COMPS(m, alive);
  if (tab === 'p') return RV_main(m, alive);
  const [F, IDX] = await Promise.all([faJSON(s.id).catch(() => null), getJSON('fa_index.json')]); if (!alive()) return;
  if (!F || !F.Y) { m.innerHTML = pn('Juste valeur', 'RV', '<div class="empty">Comptes non disponibles.</div>'); return; }
  const Y = yDerived(F), us = F.mkt === 'US', L = Y.y.map((_, i) => i).filter(i => Y.ni[i] != null && Y.eps[i] != null && Y.eq && Y.eq[i] != null).pop();
  if (L == null) { m.innerHTML = pn('Juste valeur', 'RV', '<div class="empty">Capitaux propres ou BPA absents des sources.</div>'); return; }
  const eps = Y.eps[L], sh = Y.ni[L] / eps, bvps = Y.eq[L] / sh, price = s.last, bank = !!(s.bank || F.bank);
  const roes = (Y.roe || []).slice(Math.max(0, L - 4), L + 1).filter(v => v != null && isFinite(v)); const roeAvg = roes.length ? roes.reduce((a, b) => a + b, 0) / roes.length : Y.ni[L] / Y.eq[L];
  const pay = us ? (Y.div && Y.div[L] != null && Y.ni[L] > 0 ? Math.abs(Y.div[L]) / Y.ni[L] : 0) : (Y.payout && Y.payout[L] != null ? Y.payout[L] : 0);
  const g5 = cagrA(Y.eps.slice(0, L + 1), 5); const rf = us && Q.by.US10Y ? Q.by.US10Y.last / 100 : null;
  const def = { r: us ? (rf != null ? +(rf + .05).toFixed(3) : .09) : .12, g: Math.max(0, Math.min(.05, g5 != null ? g5 : .03)), roe: roeAvg };
  const key = 'fv.' + s.id; const H = Object.assign({}, def, lsGet(key, {}));
  const P = peersOf(s, IDX), medP = k => med(P.filter(r => r.id !== s.id).map(r => r[k]).filter(v => v != null && v > 0 && v < 200));
  const peH = (F.mh && F.mh.pe || []).filter(v => v > 0 && v < 200).slice(-260), peHist = peH.length > 20 ? med(peH) : null;
  const just = (roe, g, r) => r > g ? bvps * (roe - g) / (r - g) : null, gord = (g, r) => r > g && eps > 0 ? eps * pay * (1 + g) / (r - g) : null;
  const ebitda = Y.ebitda && Y.ebitda[L], nd = Y.nd && Y.nd[L];
  const rows = [['P/B justifié : (ROE − g) ÷ (r − g)', just(H.roe, H.g, H.r), `ROE ${P1(H.roe)}, g ${P1(H.g)}, r ${P1(H.r)} → P/B ${num((H.roe - H.g) / (H.r - H.g), 2)} x`],
    ['Gordon : BPA × distribution × (1 + g) ÷ (r − g)', gord(H.g, H.r), `distribution ${P1(pay)}, g ${P1(H.g)}, r ${P1(H.r)}`],
    ['PER médian des pairs', eps > 0 && medP('pe') ? eps * medP('pe') : null, `${num(medP('pe'), 1)} x × BPA ${num(eps, 2)} (${esc(P.label)})`],
    ['P/B médian des pairs', medP('pb') ? bvps * medP('pb') : null, `${num(medP('pb'), 2)} x × actif net ${num(bvps, 0)} par action`],
    bank ? null : ['VE/EBITDA médian des pairs', ebitda > 0 && medP('ev_ebitda') ? (ebitda * medP('ev_ebitda') - (nd || 0)) / sh : null, `${num(medP('ev_ebitda'), 1)} x × EBITDA − dette nette`],
    ['PER médian de son historique (5 ans)', eps > 0 && peHist ? eps * peHist : null, `${num(peHist, 1)} x × BPA`]].filter(Boolean);
  const mos = v => v == null || v <= 0 ? null : 1 - price / v;
  const ok = rows.map(r => r[1]).filter(v => v != null && v > 0); const mid = ok.length ? med(ok) : null;
  const gs = [0, .01, .02, .03, .04, .05, .06], rs = [-.05, -.025, 0, .025, .05].map(d => Math.max(.01, H.roe + d));
  const mcol = v => v == null ? '' : v > .3 ? 'background:#0f5b2a' : v > 0 ? 'background:#0b3a1d' : v > -.3 ? 'background:#4a1212' : 'background:#6e0a12';
  m.innerHTML = `<div class="tools gpr"><span class="tlab">Rendement exigé r</span><input class="ofld ma" id="fvR" value="${num(H.r * 100, 1)}">%<span class="tlab">Croissance de long terme g</span><input class="ofld ma" id="fvG" value="${num(H.g * 100, 1)}">%<span class="tlab">ROE durable</span><input class="ofld ma" id="fvE" value="${num(H.roe * 100, 1)}">%<button class="tb rd" id="fvGo">Calculer</button><button class="tb" id="fvD">Par défaut</button></div>
    <div class="grid c2">${pn(`${esc(s.tk)} · valeur selon plusieurs méthodes (cours ${px(s, price)} ${esc(s.ccy)})`, 'RV', `<table class="t"><thead><tr><th class="l">Méthode</th><th>Valeur / action</th><th>Marge de sécurité</th><th class="l">Hypothèses</th></tr></thead><tbody>
        ${rows.map(([l, v, h]) => `<tr><td class="l am">${l}</td><td class="yl">${v != null && v > 0 ? px(s, v) : NDc('non calculable (résultat négatif, r ≤ g ou donnée absente)')}</td><td class="${cls(mos(v))}">${mos(v) != null ? num(mos(v) * 100, 0) + ' %' : '—'}</td><td class="l dm" style="white-space:normal">${h}</td></tr>`).join('')}
        <tr class="sep2"><td class="l">Médiane des méthodes</td><td class="yl">${mid ? px(s, mid) : '—'}</td><td class="${cls(mos(mid))}">${mos(mid) != null ? num(mos(mid) * 100, 0) + ' %' : '—'}</td><td class="l dm">${ok.length} méthode(s)</td></tr></tbody></table>`,
        { np: true, lect: `Marge de sécurité = 1 − cours ÷ valeur (positive = le cours est sous la valeur estimée). Données publiées : BPA ${num(eps, 2)}, actif net par action ${num(bvps, 0)}, distribution ${P1(pay)}, exercice ${us ? yLab(Y.y[L]) : Y.y[L]}. <b>Hypothèses</b> (cases orange) : r = ${us ? 'taux à 10 ans US + 5 points de prime de risque' : '12 % (rendement exigé sur une action BRVM, à ajuster)'}, g = croissance du BPA sur 5 ans bornée entre 0 et 5 %, ROE = moyenne des 5 derniers exercices. ${bank ? 'Banque : la méthode P/B face au ROE est la plus adaptée ; le PER seul ne suffit pas.' : 'Société non financière : comparer de préférence VE/EBITDA et rendement FCF entre sociétés du même secteur.'} Estimations, pas des objectifs de cours.` })}
      ${pn('Sensibilité du P/B justifié (valeur par action)', 'RV', `<table class="t"><thead><tr><th class="l">ROE \\ g</th>${gs.map(g => `<th>${num(g * 100, 0)} %</th>`).join('')}</tr></thead><tbody>${rs.map(roe => `<tr><td class="l am">${num(roe * 100, 1)} %</td>${gs.map(g => { const v = just(roe, g, H.r); return `<td style="${mcol(mos(v))}">${v != null && v > 0 ? px(s, v) : '—'}</td>`; }).join('')}</tr>`).join('')}</tbody></table>`,
        { np: true, lect: `r = ${P1(H.r)}. Vert = valeur au-dessus du cours (marge positive), rouge = en dessous. Lecture : quel couple rentabilité / croissance le cours actuel suppose-t-il ? P/B implicite au cours : <strong>${num(price / bvps, 2)} x</strong> ; ROE implicite (g = ${P1(H.g)}) : <strong>${P1(H.g + price / bvps * (H.r - H.g))}</strong>.` })}</div>`;
  const rd = id => { const v = parseFloat($(id).value.replace(',', '.')); return isFinite(v) ? v / 100 : null; };
  $('fvGo').onclick = () => { const h = { r: rd('fvR') ?? H.r, g: rd('fvG') ?? H.g, roe: rd('fvE') ?? H.roe }; if (h.r <= h.g) { toast('Le rendement exigé doit dépasser la croissance.'); return; } lsSet(key, h); render(); };
  $('fvD').onclick = () => { lsSet(key, {}); render(); };
};
