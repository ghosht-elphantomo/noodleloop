/* ================= FQT — DES (fiche Bloomberg en 5 onglets + performances) et HDS (actionnariat) ================= */
'use strict';
/* éléments communs aux fiches façon Bloomberg */
const dsec = (n, title, fn, s) => `<div class="dsec"${n ? ` data-n="${n}"` : ''}${fn ? ` data-fn="${fn}"${s ? ` data-s="${s}"` : ''}` : ''}>${n ? n + ') ' : ''}${title}${fn ? ' | ' + fn + ' »' : ''}</div>`;
const dkv = rows => `<div class="dkv">${rows.filter(Boolean).map(([a, b, t]) => `<span title="${esc(t || '')}">${a}</span><b>${b == null || b === '' ? '<i>n.d.</i>' : b}</b>`).join('')}</div>`;
const pctS = (v, d = 2) => v == null || !isFinite(v) ? null : `<span class="${cls(v)}">${v > 0 ? '+' : ''}${num(v * 100, d)}%</span>`;
const nOr = (v, d = 2, suf = '') => v == null || !isFinite(v) ? null : num(v, d) + suf;
const xMul = v => v == null || !isFinite(v) ? null : num(v, 1) + 'x';
function hiLo52(S) { const n = S.c.length, k0 = Math.max(0, n - 252); let hi = -Infinity, lo = Infinity, hiI = n - 1, loI = n - 1; for (let i = k0; i < n; i++) { if (S.h[i] > hi) { hi = S.h[i]; hiI = i; } if (S.l[i] < lo) { lo = S.l[i]; loI = i; } } return { hi, lo, hiD: S.x[hiI], loD: S.x[loI] }; }
function ytdBase(S) { const y = Math.floor(S.x[S.x.length - 1] / 10000); let k = S.x.findIndex(d => Math.floor(d / 10000) === y); return k > 0 ? S.c[k - 1] : S.c[0]; }
function miniBbg(host, S, n = 252) { const k = Math.max(0, S.x.length - n); const c = new TSChart(host, { panes: [{ h: 1, noLegend: true }], padR: 52, padB: 16, grid: 'dot', xticks: bbgTicks });
  c.set({ x: S.x.slice(k), series: [{ type: 'area', y: S.c.slice(k), color: '#ffffff', w: 1.1, grad: ['rgba(7,42,82,.97)', 'rgba(3,29,56,.97)'] }] }); return c; }
const MON_EN = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
const enDate = t => { const m = String(t || '').match(/([A-Z][a-z]{2}) (\d{1,2}), (\d{4})/); return m && MON_EN[m[1]] ? `${m[2].padStart(2, '0')}/${String(MON_EN[m[1]]).padStart(2, '0')}/${m[3]}` : (t || null); };
const usDate = t => { const m = String(t || '').match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/); return m ? `${m[2].padStart(2, '0')}/${m[1].padStart(2, '0')}/${m[3]}` : null; };
const nqNum2 = v => { if (v == null) return null; const x = parseFloat(String(v).replace(/[$,%\s]/g, '')); return isFinite(x) ? x : null; };

/* ------------------------------------------------------------------ DES */
PAGES.DES = async (m, alive) => {
  const s = sec(ST.sec), eq = s.cls === 'Equity' && s.typ !== 'ETF', etf = s.typ === 'ETF', brvm = isBRVM(s);
  const tabs = eq ? [['p', 'Profil'], ['i', 'Émission'], ['r', 'Ratios'], ['e', 'CA & BPA'], ['s', 'Secteur'], ['h', 'Performances']] : [['p', 'Profil'], ['h', 'Performances']];
  let tab = tabState('DES', 'p'); if (!tabs.some(t => t[0] === tab)) tab = ST.tab.DES = 'p';
  setTabs(tabs, tab, k => { ST.tab.DES = k; render(); });
  setTitle(`Page ${tabs.findIndex(t => t[0] === tab) + 1}/${tabs.length} Security Description: ${eq ? 'Equity' : etf ? 'ETF' : s.cls}`);
  setActs([{ n: 90, l: 'Rapport', run: () => window.print() }]);
  const [S, PR, F, EEall, DV, IDX] = await Promise.all([series(s.id), getJSON('profiles.json').catch(() => ({})), eq && (brvm || s.fa) ? faJSON(s.id).catch(() => null) : null,
    s.mkt === 'US' ? getJSON('ee.json').catch(() => ({})) : {}, getJSON('dividends.json').catch(() => []), eq ? getJSON('fa_index.json').catch(() => null) : null]); if (!alive()) return;
  const P = PR[s.id] || {}, E = EEall[s.id] || null, n = S.c.length, ccy = s.ccy;
  const shares = s.shares || P.shares || (F && F.mcap && F.price ? F.mcap / F.price : null), flt = s.float != null ? s.float : P.float;
  const head = `<div class="desh"><b>${esc((s.n || '').toUpperCase())}</b><span>${P.isin ? 'ISIN ' + esc(P.isin) : esc(ykey(s))}</span></div>`;
  if (tab === 'h') { await desPerf(m, s, S); return; }
  if (tab === 'p') {
    const L = hiLo52(S), yb = ytdBase(S), last = S.c[n - 1], tr = eq || etf ? await trSeries(s, S).catch(() => null) : null; if (!alive()) return;
    /* rendement total sur 12 mois calendaires (base : dernière séance à la date d'il y a un an ou avant, comme le résumé) */
    const i12 = baseIdx(S.x, backMonths(S.x[n - 1], 12)), tr12 = tr && i12 >= 0 ? tr[n - 1] / tr[i12] - 1 : s.r1y;
    const myDv = DV.filter(x => x.t === s.id && x.dps).sort((a, b) => (b.ex || 0) - (a.ex || 0) || (b.pay || '').localeCompare(a.pay || ''));
    let dps = null, dpsG5 = null, lastDv = null, divLab = brvm ? 'Rendement net' : 'Rendement brut indicatif';
    if (brvm && eq) { lastDv = myDv.find(x => !x.exc) || null;  /* (dividende exceptionnel : hors dividende de référence) */ const ldD = lastDv ? (lastDv.pay || lastDv.det || (lastDv.ex ? (lastDv.ex + 1) + '-12-31' : '')) : '';
      dps = lastDv && ldD >= new Date(Date.now() - 730 * 864e5).toISOString().slice(0, 10) ? myDv.filter(x => !x.exc && x.ex === lastDv.ex).reduce((a, x) => a + x.dps, 0) : null;  /* (versements ordinaires de l'exercice réunis) */  /* (plus de versement depuis deux ans : pas de rendement) */ const byEx = {}; for (const x of myDv.filter(x => !x.exc)) byEx[x.ex] = (byEx[x.ex] || 0) + x.dps; const ys = Object.keys(byEx).map(Number).sort(); const yL = ys[ys.length - 1]; if (yL && byEx[yL - 5] > 0) dpsG5 = Math.pow(byEx[yL] / byEx[yL - 5], 1 / 5) - 1; }
    else if (E && E.sum) { dps = nqNum2(E.sum.AnnualizedDividend); }
    else if (P.divA) dps = nqNum2(P.divA);
    if (!brvm && F && F.Y && F.Y.div && F.Y.sh) { const dpsY = F.Y.div.map((v, i) => v != null && F.Y.sh[i] ? Math.abs(v) / F.Y.sh[i] : null); const L2 = dpsY.length - 1; if (dpsY[L2] > 0 && dpsY[L2 - 5] > 0) dpsG5 = Math.pow(dpsY[L2] / dpsY[L2 - 5], 1 / 5) - 1; }
    const yld = dps && last ? dps / last : brvm && eq ? null : s.yld;
    // estimations (US : consensus Nasdaq/Zacks ; BRVM : aucun consensus public)
    let est = null; if (E && E.yr && E.yr.length) { const fy = E.yr[0], fy2 = E.yr[1]; const ttm = F && F.H && F.H.eps ? F.H.eps[F.H.eps.length - 1] : null; /* H = séries glissantes 12 mois par trimestre */
      const edm = String(E.ed || '').match(/(\d{1,2}\/\d{1,2}\/\d{4})/); const g = fy2 && fy.consensusEPSForecast > 0 ? fy2.consensusEPSForecast / fy.consensusEPSForecast - 1 : null; const epe = fy.consensusEPSForecast > 0 ? last / fy.consensusEPSForecast : null;
      est = { date: edm ? usDate(edm[1]) : null, pe: F && F.pe, epe, ttm, eeps: fy.consensusEPSForecast, fyl: fy.fiscalEnd, peg: epe && g > 0 ? epe / (g * 100) : null, tp: E.tp }; }
    const mg = P.mgmt || [];
    const inst = P.inst, hold = P.holders;
    m.innerHTML = `<div class="pn">${head}
      <div class="desh" style="font-size:12.5px;padding-top:0;justify-content:flex-end;gap:14px"><span class="am">${P.sector || s.grp ? 'Classification' : ''}</span><span>${esc(brvm ? (s.grp || '') + (s.bank ? ' · banque' : '') : (P.sector ? P.sector + (P.ind ? ' · ' + P.ind : '') : s.grp || ''))}</span></div>
      <div class="desd" id="desD">${P.desc ? esc(P.desc) : eq ? `<span class="dm">Description non encore collectée (fiche relevée chaque soir).</span>` : esc(s.n) + ' · ' + esc(s.cls) + (s.grp ? ' · ' + esc(s.grp) : '')}</div>
      <div class="dcols">
        <div>${dsec(1, 'Graphique des cours', 'GP', s.id)}<div class="cv" id="desG" style="height:150px"></div>
          ${dkv([[`Cours / var. 1J (${esc(ccy)})`, `${px(s, last)} / ${pctS(s.pct) || '—'}`], [`Plus haut 52s (${fd(L.hiD).slice(0, 8)}${fd(L.hiD).slice(8)})`, px(s, L.hi)], [`Plus bas 52s (${fd(L.loD).slice(0, 8)}${fd(L.loD).slice(8)})`, px(s, L.lo)],
            ['Var. depuis le 1er janv. / %', `${px(s, last - yb)} / ${pctS(last / yb - 1) || '—'}`], eq || etf ? [`Capitalisation (${esc(ccy)})`, s.mcap ? big(s.mcap) : P.mcap ? big(nqNum2(P.mcap)) : null] : null,
            eq ? ['Titres / flottant', shares ? `${big(shares)}${flt != null ? ' / ' + num(flt, 2) + '%' : ''}` : null] : null, etf ? ['Encours (AUM)', P.aum ? big(nqNum2(P.aum) * 1e3) + ' USD' : null, 'en milliers de dollars'] : null, etf ? ['Frais de gestion', P.er || null] : null,
            ['Échanges moyens / séance', s.liq ? big(s.liq) + ' ' + ccy : null, 'montant moyen échangé par séance sur 3 mois'], ['Volatilité 1 an', s.vol != null ? num(s.vol * 100, 1) + '%' : null]])}</div>
        <div>${eq ? dsec(2, 'Estimations', 'EE', s.id) + (est ? dkv([['Prochaine publication', est.date && NA_RX.test(est.date) ? 'non annoncée' : est.date], ['PER (12 mois)', xMul(est.pe)], [`PER estimé (${esc(est.fyl)})`, xMul(est.epe)], ['BPA 12 mois glissants', nOr(est.ttm)], [`BPA estimé (${esc(est.fyl)})`, nOr(est.eeps)], ['PEG estimé', nOr(est.peg)],
              est.tp ? ['Objectif de cours moyen', `${num(est.tp.priceTarget, 2)} (${num(est.tp.lowPriceTarget, 0)}–${num(est.tp.highPriceTarget, 0)})`] : null, est.tp ? ['Achat / Conserver / Vente', `${est.tp.buy} / ${est.tp.hold} / ${est.tp.sell}`] : null])
              : dkv([['PER (dernier exercice)', xMul(s.per || (F && F.pe))], ['BPA dernier exercice', s.bnpa ? num(s.bnpa, 0) + ' ' + ccy : null], ['PER estimé', null, 'aucun consensus d’analystes publié pour la BRVM'], ['BPA estimé', null, 'aucun consensus d’analystes publié pour la BRVM']]) + `<div class="src">${brvm ? 'BRVM : aucun consensus d’analystes public — rien n’est estimé ici.' : 'Pas de consensus publié pour ce titre.'}</div>`) : ''}
          ${eq || etf ? dsec(eq ? 3 : 2, 'Dividende', 'DVD', s.id) + dkv([[divLab, yld ? num(yld * 100, 2) + '%' : null, brvm ? 'dernier dividende net ÷ cours' : 'dividende annualisé ÷ cours'], ['Croissance sur 5 ans (TCAM)', pctS(dpsG5, 2), 'taux de croissance annuel moyen du dividende par action'],
              brvm && lastDv ? [`Dernier : ${lastDv.ex} (paiement ${fds(lastDv.pay)})`, num(myDv.filter(x => !x.exc && x.ex === lastDv.ex).reduce((a, x) => a + x.dps, 0), 2) + ' ' + ccy] : dps ? ['Dividende annualisé', num(dps, 2) + ' ' + ccy] : null, !brvm && (E && E.sum && E.sum.ExDividendDate || P.exdiv) ? ['Date de détachement', esc(enDate((E && E.sum && E.sum.ExDividendDate) || P.exdiv))] : null]) : ''}
          ${dsec(eq ? 4 : etf ? 3 : 2, 'Rendement et risque', 'BETA', s.id)}${dkv([['Rendement total 12 mois', pctS(tr12), 'dividendes réinvestis'], [`Bêta vs ${esc(s.bench || '—')}`, nOr(s.beta, 2), 'hebdomadaire, 2 ans'], ['Écart au plus haut historique', pctS(s.dd, 1)], ['Première donnée', fd(s.first)]])}</div>
        <div>${eq ? dsec(5, 'Société', '') + dkv([P.url ? ['Site', `<a href="${esc(P.url)}" target="_blank" rel="noopener">${esc(P.url.replace(/^https?:\/\/(www\.)?/, ''))}</a>`] : null, ['Adresse', P.addr ? esc(P.addr) : null], ['Téléphone', P.tel || P.phone ? esc(P.tel || P.phone) : null], brvm ? ['Pays', esc(Q.sum.cty[s.cty] || s.cty)] : ['Exercice clos le', P.fye ? P.fye.slice(2) + '/' + P.fye.slice(0, 2) : null],
              ['Place de cotation', brvm ? 'BRVM (Abidjan)' : esc(P.exch || 'États-Unis')]]) : ''}
          ${eq ? dsec(6, 'Dirigeants', '') + (mg.length ? dkv(mg.slice(0, 5).map(([r, nm]) => [esc(r), esc(nm)])) : `<div class="src">${brvm ? 'Non publiés.' : 'Non collectés pour les sociétés US.'}</div>`) : ''}
          ${eq ? dsec(7, 'Actionnariat', 'HDS', s.id) + (hold && hold.length ? dkv(hold.slice(0, 4).map(([nm, p]) => [esc(nm), num(p, 2) + '%'])) : inst && inst.pct ? dkv([['Détention institutionnelle', esc(inst.pct)], ['Nombre d’institutions', inst.n ? num(+inst.n, 0) : null], inst.rows && inst.rows[0] ? ['1er détenteur', esc(inst.rows[0][0])] : null]) : '<div class="src">Actionnariat non encore collecté.</div>') : ''}</div>
      </div>
      <div class="src">${brvm ? (P.d ? 'Fiche relevée le ' + fds(P.d) : 'Fiche société') : 'Fiche société'} · cours ${fd(s.dt)}${s.live ? ' (séance en cours)' : ''}.</div></div>`;
    miniBbg($('desG'), S);
    return;
  }
  if (!F) { m.innerHTML = `<div class="pn">${head}<div class="empty">Comptes non disponibles pour ce titre.</div></div>`; return; }
  const peersAll = IDX ? peersOf(s, IDX) : []; const med = k => { const v = peersAll.map(r => r[k]).filter(x => x != null && isFinite(x)); return v.length >= 3 ? U.median(v) : null; };
  if (tab === 'i') {
    /* BRVM : séances du marché (calendrier du BRVM Composite, comme LQA) ; un jour sans ligne dans la série = séance sans échange */
    const CAL = brvm ? await series('BRVMC').catch(() => null) : null; if (!alive()) return;
    const hv = new Map(S.x.map((d, i) => [d, i])), cal = CAL ? CAL.x.filter(d => d >= S.x[0] && d <= S.x[S.x.length - 1]) : S.x;
    const at = (k, f) => cal.slice(-k).map(d => hv.has(d) ? f(hv.get(d)) || 0 : 0);
    const zero = at(60, i => S.v[i]).filter(v => !v).length;
    const v20 = at(20, i => S.v[i]).reduce((a, b) => a + b, 0) / 20, val60 = S.val ? at(60, i => S.val[i]).reduce((a, b) => a + b, 0) / 60 : null;
    const idxs = brvm ? ['BRVM Composite', 'BRVM 30 (si membre)', 'indice sectoriel ' + (s.grp || '')] : [s.ndx ? 'Nasdaq-100' : null].filter(Boolean);
    m.innerHTML = `<div class="pn">${head}<div class="dcols">
      <div>${dsec(1, 'Identification', '')}${dkv([['Code', esc(s.id)], ['Ticker', esc(ykey(s))], ['ISIN', P.isin ? esc(P.isin) : null], ['Place', brvm ? 'BRVM' : esc(P.exch || 'États-Unis')], ['Devise', esc(ccy)], ['Catégorie', 'Action ordinaire'], ['Pays', brvm ? esc(Q.sum.cty[s.cty] || s.cty) : esc(P.inc ? 'Constituée : ' + P.inc : 'États-Unis')], ['Statut', s.susp ? '<span class="dn">Cotation suspendue</span>' : 'Coté']])}</div>
      <div>${dsec(2, 'Capital', 'HDS', s.id)}${dkv([['Nombre de titres', shares ? num(shares, 0) : null], ['Flottant', flt != null ? num(flt, 2) + '%' : null], ['Titres flottants', shares && flt != null ? num(shares * flt / 100, 0) : null], [`Capitalisation (${esc(ccy)})`, s.mcap ? big(s.mcap) : null], ['Capitalisation flottante', s.mcap && flt != null ? big(s.mcap * flt / 100) : null], ['Valeur d’entreprise', F.ev ? big(F.ev) : null], P.val_m ? ['Valorisation (fiche société)', big(P.val_m * 1e6)] : null])}
        ${dsec(3, 'Indices', '')}${dkv(idxs.map(x => [esc(x), '✓']))}</div>
      <div>${dsec(4, 'Négociation', 'LQA', s.id)}${dkv([['Première donnée de cours', fd(s.first), 'début de l’historique disponible, pas la date d’introduction'], ['Volume moyen 20 séances', v20 ? num(v20, 0) : null], ['Montant moyen 60 séances', val60 ? big(val60) + ' ' + ccy : s.liq ? big(s.liq) + ' ' + ccy : null], ['Séances sans échange (60)', S.v.length >= 60 ? `${zero} / 60` : null], ['Volatilité 1 an', s.vol != null ? num(s.vol * 100, 1) + '%' : null], ['Plage 52 semaines', `${px(s, s.lo52)} – ${px(s, s.hi52)}`]])}</div></div>
      </div>`;
    return;
  }
  if (tab === 'r') {
    const R = (lab, k, f, why) => [lab, f(F[k]), f(med(k)), why];
    const groups = [['Valorisation', [R('PER', 'pe', xMul), R('Cours / actif net (P/B)', 'pb', xMul), R('Cours / CA', 'ps', xMul), F.bank ? null : R('VE / EBITDA', 'ev_ebitda', xMul), F.bank ? null : R('VE / CA', 'ev_sales', xMul), R('Rendement bénéficiaire', 'ey', v => P1(v, 2)), R('Rendement FCF', 'fcfy', v => P1(v, 2)), R('Rendement du dividende', 'dy', v => P1(v, 2))]],
      ['Rentabilité', [R('ROE', 'roe', P1), R('ROA', 'roa', v => P1(v, 2)), F.bank ? null : R('ROIC', 'roic', P1), F.gm != null ? R('Marge brute', 'gm', P1) : null, F.bank ? null : R('Marge d’exploitation', 'om', P1), R('Marge nette', 'nm', P1), F.bank ? null : R('Marge EBITDA', 'ebitdam', P1), R('Marge FCF', 'fcfm', P1)]],
      ['Structure financière', F.bank ? [R('Crédits / dépôts', 'ld', P1), R('Coefficient d’exploitation', 'cir', v => v == null ? null : num(v, 1) + '%'), R('Coût du risque / crédits', 'cor_l', v => P1(v, 2))] : [R('Dette nette / EBITDA', 'nd_ebitda', v => nOr(v, 2, 'x')), R('Dette nette / capitaux propres', 'de', v => nOr(v, 2, 'x')), F.icov != null ? R('Couverture des intérêts', 'icov', v => nOr(v, 1, 'x')) : null, F.cur != null ? R('Liquidité générale', 'cur', v => nOr(v, 2)) : null]],
      ['Croissance', [R('CA, 1 an', 'rev_g', v => pctS(v, 1)), R('Résultat net, 1 an', 'ni_g', v => pctS(v, 1)), R('BPA, 1 an', 'eps_g', v => pctS(v, 1)), R('CA, TCAM 3 ans', 'rev_cagr3', v => pctS(v, 1)), R('CA, TCAM 5 ans', 'rev_cagr5', v => pctS(v, 1)), R('BPA, TCAM 5 ans', 'eps_cagr5', v => pctS(v, 1))]],
      ['Distribution et qualité', [R('Taux de distribution', 'payout', P1), R('Dividendes / FCF', 'fpay', P1), ['Score de Piotroski', F.fscore != null ? `${F.fscore} / ${F.fscore_n}` : null, null, 'critères calculables seulement'], F.altz != null ? R('Altman Z', 'altz', v => nOr(v, 2)) : null]]];
    const tbl = g => `<table class="t acc"><thead><tr><th class="l">${g[0]}</th><th>${esc(s.id)}</th><th>Médiane pairs</th></tr></thead><tbody>${g[1].filter(Boolean).map(([l, a, b, w]) => `<tr><td class="l" title="${esc(w || '')}">${l}</td><td>${a == null ? NDc(w || 'non calculable') : a}</td><td class="dm">${b == null ? '—' : b}</td></tr>`).join('')}</tbody></table>`;
    m.innerHTML = `<div class="pn">${head}<div class="grid c3" style="padding:4px">${groups.map(g => `<div>${tbl(g)}</div>`).join('')}</div>
      <div class="src">Exercice ${esc(F.fy || (F.asof_q ? 'glissant au ' + fd(F.asof_q) : ''))} · pairs : ${esc(peersAll.label || '')} (${peersAll.length} sociétés). Détail et historique : <b data-fn="FA" data-s="${s.id}" class="am" style="cursor:pointer">FA</b> · comparaison : <b data-fn="RV" data-s="${s.id}" class="am" style="cursor:pointer">RV</b>. ${faSrcNote(F)}</div></div>`;
    return;
  }
  if (tab === 'e') {
    const Y = yDerived(F), U = unitOf(F), yl = Y.y.map(y => F.mkt === 'US' ? yLab(y) : String(y)); const k0 = Math.max(0, yl.length - 10);
    const rev = Y.rev.slice(k0), eps = Y.eps.slice(k0), labs = yl.slice(k0);
    const q = F.H && F.H.q ? { q: F.H.q.slice(-12), rev: F.H.rev.slice(-12), eps: F.H.eps.slice(-12) } : null;
    m.innerHTML = `<div class="pn">${head}<div class="grid c2b" style="padding:4px">
      <div>${dsec(1, `Chiffre d’affaires (${U.lab})`, 'FA', s.id)}<div class="cv" id="desR" style="height:210px"></div></div>
      <div>${dsec(2, `BPA (${esc(ccy)})`, 'FA', s.id)}<div class="cv" id="desE" style="height:210px"></div></div></div>
      <div class="tw"><table class="t acc"><thead><tr><th class="l">Exercice</th>${labs.map(l => `<th>${l}</th>`).join('')}</tr></thead><tbody>
        <tr><td class="l">Chiffre d’affaires</td>${rev.map(v => `<td>${v == null ? NDc() : num(v * U.k, U.d)}</td>`).join('')}</tr>
        <tr class="sub"><td class="l">croissance</td>${rev.map((v, i) => `<td>${pctS(i ? gr(rev, i) : null, 1) || ''}</td>`).join('')}</tr>
        <tr><td class="l">Résultat net</td>${Y.ni.slice(k0).map(v => `<td>${v == null ? NDc() : num(v * U.k, U.d)}</td>`).join('')}</tr>
        <tr><td class="l">BPA</td>${eps.map(v => `<td>${v == null ? NDc() : num(v, 2)}</td>`).join('')}</tr>
        <tr class="sub"><td class="l">croissance</td>${eps.map((v, i) => `<td>${pctS(i ? gr(eps, i) : null, 1) || ''}</td>`).join('')}</tr>
</tbody></table></div>
      ${E && E.yr ? `<div style="padding:4px">${dsec(3, 'Consensus du BPA (estimations, pas des résultats publiés)', 'EE', s.id)}<table class="t"><thead><tr><th class="l">Exercice</th><th>BPA estimé</th><th>Bas</th><th>Haut</th><th>Analystes</th></tr></thead><tbody>${E.yr.map(r => `<tr><td class="l est">${esc(r.fiscalEnd)}</td><td class="est">${num(r.consensusEPSForecast, 2)}</td><td>${num(r.lowEPSForecast, 2)}</td><td>${num(r.highEPSForecast, 2)}</td><td>${r.noOfEstimates}</td></tr>`).join('')}</tbody></table></div>` : ''}
      ${q ? `<div style="padding:4px">${dsec(4, 'BPA sur 12 mois glissants, trimestre par trimestre', 'FA', s.id)}<div class="cv" id="desQ" style="height:170px"></div></div>` : ''}
      <div class="src">${faSrcNote(F)}${brvm ? ' BRVM : aucun consensus d’analystes publié.' : ' Estimations : consensus des analystes, en bleu clair.'}</div></div>`;
    barChart($('desR'), { labels: labs.map(l => l.slice(2)), values: rev.map(v => v == null ? NaN : v * U.k), fmt: v => num(v, U.d), labelsOnBars: true, pos: '#3d7cc9' });
    barChart($('desE'), { labels: labs.map(l => l.slice(2)), values: eps.map(v => v == null ? NaN : v), fmt: v => num(v, 2), labelsOnBars: true, pos: '#f9a33a' });
    if (q) barChart($('desQ'), { labels: q.q.map(d => String(d).slice(2, 4) + '/' + String(d).slice(4, 6)), values: q.eps.map(v => v == null ? NaN : v), fmt: v => num(v, 2), labelsOnBars: true, pos: '#f9a33a', extra: i => 'CA 12 mois ' + num((q.rev[i] || 0) * U.k, U.d) + ' ' + U.lab });
    return;
  }
  if (tab === 's') {
    const rows = peersAll.slice().sort((a, b) => (b.mcap || 0) - (a.mcap || 0)); const capS = rows.reduce((a, r) => a + (r.mcap || 0), 0); const rank = rows.findIndex(r => r.id === s.id) + 1;
    const pf = r => Q.by[r.id] || {};
    m.innerHTML = `<div class="pn">${head}<div class="dcols" style="grid-template-columns:minmax(0,1fr) minmax(0,2.2fr)">
      <div>${dsec(1, 'Classification', '')}${dkv([['Secteur', esc(brvm ? s.grp : P.sector || s.grp)], ['Industrie', P.ind ? esc(P.ind) : brvm ? esc(s.grp) : null], ['Groupe de pairs', esc(peersAll.label || '')], ['Rang par capitalisation', rank ? `${rank} / ${rows.length}` : null], ['Poids dans le groupe', s.mcap && capS ? num(s.mcap / capS * 100, 1) + '%' : null]])}
        ${dsec(2, 'Le titre face au groupe', 'RV', s.id)}${dkv([['PER / médiane', `${xMul(F.pe) || '—'} / ${xMul(med('pe')) || '—'}`], ['P/B / médiane', `${xMul(F.pb) || '—'} / ${xMul(med('pb')) || '—'}`], ['ROE / médiane', `${P1(F.roe)} / ${P1(med('roe'))}`], ['Rendement / médiane', `${P1(F.dy, 2)} / ${P1(med('dy'), 2)}`], ['1 an / médiane', `${pctS(s.r1y, 1) || '—'} / ${pctS((() => { const v = rows.map(r => pf(r).r1y).filter(x => x != null).sort((a, b) => a - b); return v.length ? v[Math.floor(v.length / 2)] : null; })(), 1) || '—'}`]])}</div>
      <div>${dsec(3, 'Sociétés du groupe', 'PEER', s.id)}<div class="tw" style="max-height:60vh"><table class="t"><thead><tr><th class="l">Titre</th><th class="l">Société</th><th>Capi</th><th>Var.%</th><th>YTD</th><th>1 an</th><th>PER</th><th>P/B</th><th>ROE</th><th>Rdt</th></tr></thead><tbody>
        ${rows.map(r => `<tr data-sec="${r.id}" data-to="DES" class="${r.id === s.id ? 'cur' : ''}"><td class="l tk">${r.id}</td><td class="l nm">${esc(pf(r).short || pf(r).n || '')}</td><td>${big(r.mcap)}</td><td>${pc(pf(r).pct)}</td><td>${pc(pf(r).ytd, 1)}</td><td>${pc(pf(r).r1y, 1)}</td><td>${xMul(r.pe) || '—'}</td><td>${xMul(r.pb) || '—'}</td><td>${P1(r.roe)}</td><td>${P1(r.dy, 2)}</td></tr>`).join('')}</tbody></table></div></div></div>
      <div class="src">Groupe de pairs : ${esc(peersAll.label || '')}. Multiples calculés sur le dernier exercice publié et le cours du jour.</div></div>`;
    return;
  }
};
async function desPerf(m, s, S) {
  const n = S.c.length, yrs = {}; for (let i = 1; i < n; i++) { const y = Math.floor(S.x[i] / 10000); (yrs[y] = yrs[y] || []).push(i); }
  const yearRows = Object.entries(yrs).map(([y, ix]) => { const i0 = ix[0] - 1, i1 = ix[ix.length - 1]; let pk = S.c[i0], mdd = 0; const lr = [];
    for (const i of ix) { pk = Math.max(pk, S.c[i]); mdd = Math.min(mdd, S.c[i] / pk - 1); lr.push(Math.log(S.c[i] / S.c[i - 1])); }
    return { y: +y, ret: S.c[i1] / S.c[i0] - 1, mdd, vol: U.std(lr) * Math.sqrt(S.f === 'D' ? 252 : 12), best: Math.exp(Math.max(...lr)) - 1, worst: Math.exp(Math.min(...lr)) - 1, nobs: ix.length, last: S.c[i1] }; }).reverse();
  const eps = []; { let pk = S.c[0], pi = 0, tr = 0, ti = 0, inDD = false;
    for (let i = 1; i < n; i++) { if (S.c[i] >= pk) { if (inDD && 1 - tr / pk >= .05) eps.push({ p: pi, t: ti, r: i, depth: tr / pk - 1 }); pk = S.c[i]; pi = i; tr = pk; inDD = false; } else { inDD = true; if (S.c[i] < tr || !tr) { tr = S.c[i]; ti = i; } } }
    if (inDD && 1 - tr / pk >= .05) eps.push({ p: pi, t: ti, r: null, depth: tr / pk - 1 }); }
  const topDD = eps.sort((a, b) => a.depth - b.depth).slice(0, 10), unit = S.f === 'D' ? 'séances' : 'mois';
  m.innerHTML = `<div class="grid c2">${pn('Performances annuelles', 'DES', `<div class="tw" style="max-height:62vh"><table class="t"><thead><tr><th class="l">Année</th><th>Clôture</th><th>Perf.</th><th>Max DD</th><th>Vol.</th><th>Meilleure</th><th>Pire</th><th>Obs.</th></tr></thead><tbody>
    ${yearRows.map(r => `<tr><td class="l am">${r.y}</td><td class="wh">${px(s, r.last)}</td><td>${pc(r.ret, 1)}</td><td>${pc(r.mdd, 1)}</td><td>${num(r.vol * 100, 1)}%</td><td>${pc(r.best, 1)}</td><td>${pc(r.worst, 1)}</td><td>${r.nobs}</td></tr>`).join('')}</tbody></table></div>`, { np: true })}
    <div class="grid" style="align-content:start">${pn('Rendement par année', 'DES', cvb('desYr', 190))}${pn('Drawdowns majeurs (≥ 5 %)', 'DES', `<table class="t"><thead><tr><th class="l">Sommet</th><th class="l">Creux</th><th>Baisse</th><th>Durée</th><th class="l">Retour</th><th>Totale</th></tr></thead><tbody>
    ${topDD.map(e => `<tr><td class="l">${fd(S.x[e.p])}</td><td class="l">${fd(S.x[e.t])}</td><td>${pc(e.depth, 1)}</td><td>${e.t - e.p} ${unit}</td><td class="l">${e.r ? fd(S.x[e.r]) : '<span class="am">en cours</span>'}</td><td>${(e.r || n - 1) - e.p} ${unit}</td></tr>`).join('')}</tbody></table>`, { np: true, lect: 'Baisses du sommet au creux, classées par profondeur. La durée totale va du sommet au retour à ce niveau.' })}</div></div>`;
  const yr = yearRows.slice().reverse(); barChart($('desYr'), { labels: yr.map(r => String(r.y).slice(2)), values: yr.map(r => r.ret * 100), fmt: v => num(v, 0) + '%', extra: i => 'max DD ' + num(yr[i].mdd * 100, 1) + '%' });
}

/* ------------------------------------------------------------------ HDS : actionnariat (BRVM : principaux actionnaires ; US : détenteurs institutionnels 13F) */
/* chiffres Nasdaq (« 1,426,283,914 », « 1.919% », « $480,144,217 ») remis au format français */
const nqv = x => { if (x == null) return null; const v = parseFloat(String(x).replace(/[$,%\s]/g, '')); return isFinite(v) ? v : null; };
const nqf = (x, d) => { const v = nqv(x); return v == null ? '—' : num(v, d); };
const HDS_POS = { 'Increased Positions': 'Positions renforcées', 'Decreased Positions': 'Positions réduites', 'Held Positions': 'Positions inchangées', 'Total Institutional Shares': 'Total des titres détenus',
  'New Positions': 'Nouvelles positions', 'Sold Out Positions': 'Positions soldées' };
PAGES.HDS = async (m, alive) => {
  const s = sec(ST.sec), brvm = isBRVM(s); const PR = await getJSON('profiles.json').catch(() => ({})); if (!alive()) return; const P = PR[s.id] || {};
  setTitle('Holdings: Current');
  if (brvm) {
    const H = (P.holders || []).slice().sort((a, b) => b[1] - a[1]); const tot = H.reduce((a, h) => a + h[1], 0), shares = s.shares || P.shares;
    const isPub = nm => /public|brvm|divers|flottant|bourse/i.test(nm);
    setTabs([['c', 'Répartition du capital']], 'c', () => { });
    m.innerHTML = `<div class="grid c2">${pn(`${esc(s.n)} · principaux actionnaires`, 'HDS', H.length ? `<table class="t"><thead><tr><th class="l">#</th><th class="l">Actionnaire</th><th>% du capital</th><th>Titres (calculés)</th><th>Valeur au cours</th><th class="l">Type</th></tr></thead><tbody>
        ${H.map((h, i) => `<tr><td class="l">${i + 1})</td><td class="l nm">${esc(h[0])}</td><td>${num(h[1], 2)}%</td><td>${shares ? num(shares * h[1] / 100, 0) : '—'}</td><td>${s.mcap ? big(s.mcap * h[1] / 100) + ' XOF' : '—'}</td><td class="l dm">${isPub(h[0]) ? 'Public / flottant' : /etat|état|republique|république|gouvernement|tresor/i.test(h[0]) ? 'État' : /employ|salari|personnel/i.test(h[0]) ? 'Salariés' : 'Investisseur'}</td></tr>`).join('')}
        <tr class="sep2"><td></td><td class="l">Total publié</td><td>${num(tot, 2)}%</td><td></td><td></td><td></td></tr></tbody></table>` : '<div class="empty">Répartition du capital non encore collectée (fiche relevée chaque soir).</div>',
      { np: true, lect: `${P.d ? 'Fiche relevée le ' + fds(P.d) + '. ' : ''}La BRVM ne publie pas de registre des actionnaires : seuls les principaux détenteurs déclarés par la société sont connus. Titres et valeurs = pourcentage × nombre de titres (${shares ? num(shares, 0) : 'n.d.'}) × cours du jour.` })}
      ${pn('Répartition', 'HDS', '<div class="cv" id="hdsC" style="height:300px"></div>', { lect: `Flottant déclaré : <strong>${P.float != null ? num(P.float, 2) + ' %' : 'n.d.'}</strong>. ${P.float != null && H.some(h => isPub(h[0])) ? 'La ligne « public » de la répartition peut différer du flottant si la date de mise à jour n’est pas la même.' : ''}` })}</div>`;
    if (H.length) barChart($('hdsC'), { labels: H.map(h => h[0].slice(0, 12)), values: H.map(h => h[1]), fmt: v => num(v, 1) + '%', labelsOnBars: true, pos: '#3d7cc9', padB: 22 });
    return;
  }
  const I = P.inst; setTabs([['i', 'Institutionnels']], 'i', () => { });
  if (!I) { m.innerHTML = pn(`${esc(s.n)} · détenteurs`, 'HDS', '<div class="empty">Détenteurs non encore collectés (relevé chaque soir).</div>'); return; }
  m.innerHTML = `<div class="grid c2">${pn(`${esc(s.n)} · principaux détenteurs institutionnels`, 'HDS', `<div class="tw"><table class="t"><thead><tr><th class="l">#</th><th class="l">Détenteur</th><th class="l">Déclaration</th><th>Titres</th><th>Variation</th><th>Var. %</th><th>Valeur (k$)</th></tr></thead><tbody>
      ${(I.rows || []).map((r, i) => { const ch = nqv(r[3]), pv = nqv(r[4]); return `<tr><td class="l">${i + 1})</td><td class="l nm">${esc(r[0])}</td><td class="l">${usDate(r[1]) || esc(r[1] || '')}</td><td>${nqf(r[2], 0)}</td><td class="${cls(ch)}">${ch != null ? (ch > 0 ? '+' : '') + num(ch, 0) : '—'}</td><td>${pv != null ? sgn(pv / 100, 2) : '—'}</td><td>${nqf(r[5], 0)}</td></tr>`; }).join('')}</tbody></table></div>`,
      { np: true, lect: `Déclarations 13F des gérants institutionnels (relevé du ${fds(P.d)}). Les dates de déclaration diffèrent selon les institutions ; seuls les gérants de plus de 100 M$ déclarent.` })}
    ${pn('Synthèse', 'HDS', dkv([['Détention institutionnelle', nqv(I.pct) != null ? num(nqv(I.pct), 2) + ' %' : '—'], ['Institutions déclarantes', I.n ? num(+I.n, 0) : null], ['Titres en circulation (M)', nqf(I.sh_m, 0)]].concat((I.pos || []).map(r => [esc(HDS_POS[r[0]] || r[0]), `${nqf(r[1], 0)} inst. · ${nqf(r[2], 0)} titres`]))))}</div>`;
};
