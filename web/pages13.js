/* ================= FQT — HP, DVD, BETA structurés comme les écrans du terminal Bloomberg ================= */
const JOUR2 = ['Di', 'Lu', 'Ma', 'Me', 'Je', 'Ve', 'Sa'];
const dWk = d => { const t = new Date(Date.UTC(Math.floor(d / 10000), Math.floor(d / 100) % 100 - 1, d % 100)); return JOUR2[t.getUTCDay()] + ' ' + fmtD(d).slice(0, 6) + fmtD(d).slice(8); };

/* ------------------------------------------------------------------ HP : tableau des cours historiques (blocs de colonnes + synthèse à droite) */
PAGES.HP = async (m, alive) => {
  const s = sec(ST.sec); const S = await series(s.id); if (!alive()) return; setTitle('Historical Price Table');
  const st = ST.hp2 = ST.hp2 || {}; if (st.id !== s.id) Object.assign(st, { id: s.id, f: S.f === 'M' ? 'M' : 'D', rg: S.f === 'M' ? '5A' : '3M', mk: 'c', v: 'P', d0: null, d1: null, page: 0 });
  /* agrégation hebdomadaire / mensuelle : dernier jour de la période */
  const key = d => st.f === 'D' ? d : st.f === 'W' ? isoWeekKey(d) : Math.floor(d / 100); const R = []; let cur = null;
  for (let i = 0; i < S.x.length; i++) { const k = key(S.x[i]); if (!cur || cur.k !== k) { if (cur) R.push(cur); cur = { k, d: S.x[i], o: S.o[i], h: S.h[i], l: S.l[i], c: S.c[i], v: S.v[i] || 0, val: S.val ? S.val[i] || 0 : 0 }; }
    else { cur.d = S.x[i]; cur.h = Math.max(cur.h, S.h[i]); cur.l = Math.min(cur.l, S.l[i]); cur.c = S.c[i]; cur.v += S.v[i] || 0; if (S.val) cur.val += S.val[i] || 0; } }
  if (cur) R.push(cur);
  const vma = U.sma(R.map(r => r.v), 15); R.forEach((r, i) => { r.vm = vma[i]; r.ch = i ? r.c - R[i - 1].c : null; r.pc = i && R[i - 1].c ? r.c / R[i - 1].c - 1 : null; });
  const last = R[R.length - 1].d;
  /* période effective : 1M / 3M trop courts en hebdomadaire ou mensuel → 1A / 5A, sans écraser le choix (retour en quotidien = période choisie) */
  const rgE = st.f !== 'D' && ['1M', '3M'].includes(st.rg) ? (st.f === 'W' ? '1A' : '5A') : st.rg;
  let d0 = st.d0, d1 = st.d1 || last; if (!d0) d0 = rgE === 'YTD' ? Math.floor(last / 10000) * 10000 + 101 : rgE === 'MAX' ? R[0].d : perStart(last, rgE) + 1;  /* (date calendaire ; le lendemain de la date de départ : même nombre de séances que la période) */
  const W = R.filter(r => r.d >= d0 && r.d <= d1), hasV = W.some(r => r.v > 0), mk = { c: 'Dernier', o: 'Ouverture', h: 'Plus haut', l: 'Plus bas' }[st.mk];
  const V = r => r[st.mk];
  /* synthèse de la période (colonne de droite du terminal) */
  let hi = null, lo = null, sum = 0; for (const r of W) { if (!hi || V(r) > V(hi)) hi = r; if (!lo || V(r) < V(lo)) lo = r; sum += V(r); }
  const first = W[0], lastR = W[W.length - 1], net = first && lastR ? V(lastR) - V(first) : null, avgV = W.length ? W.reduce((a, r) => a + r.v, 0) / W.length : null;
  /* blocs de colonnes : remplit la largeur de l'écran, du plus récent au plus ancien */
  const vw = Math.max(320, (m.getBoundingClientRect().width || 1200) - 300), bw = st.v === 'P' ? (hasV ? 330 : 200) : 560, nb = Math.max(1, Math.floor(vw / bw));
  const rowsPer = Math.max(12, Math.floor((window.innerHeight - 330 - (PREF.nonews ? 0 : 90)) / 19)), per = nb * rowsPer, L = W.slice().reverse(), np = Math.max(1, Math.ceil(L.length / per)); st.page = U.clamp(st.page, 0, np - 1);
  const pg = L.slice(st.page * per, st.page * per + per), blocks = []; for (let b = 0; b < nb; b++) blocks.push(pg.slice(b * rowsPer, b * rowsPer + rowsPer));
  const head = st.v === 'P' ? `<tr><th class="l">Date</th><th>${mk}</th>${hasV ? '<th>Volume</th><th>MMV (15)</th>' : ''}</tr>` : `<tr><th class="l">Date</th><th>Ouverture</th><th>Plus haut</th><th>Plus bas</th><th>Dernier</th><th>Var. %</th>${hasV ? '<th>Volume</th>' : ''}</tr>`;
  const row = r => st.v === 'P' ? `<tr><td class="l">${dWk(r.d)}</td><td class="wh">${px(s, V(r))}</td>${hasV ? `<td>${r.v ? num(r.v, 0) : '—'}</td><td>${r.vm != null && isFinite(r.vm) ? num(r.vm, 0) : '—'}</td>` : ''}</tr>`
    : `<tr><td class="l">${dWk(r.d)}</td><td>${px(s, r.o)}</td><td>${px(s, r.h)}</td><td>${px(s, r.l)}</td><td class="wh">${px(s, r.c)}</td><td>${pc(r.pc)}</td>${hasV ? `<td>${r.v ? num(r.v, 0) : '—'}</td>` : ''}</tr>`;
  setActs([{ n: 1, l: 'Actions', menu: () => [{ l: 'Exporter le tableau (CSV)', run: exportCSV }, { l: 'Ouvrir le graphique (GP)', run: () => go('GP', s.id) }, { l: 'Imprimer', run: () => window.print() }] }]);
  const rg = ['1M', '3M', '6M', 'YTD', '1A', '2A', '5A', '10A', 'MAX'];
  m.innerHTML = `<div class="tools hpt"><span class="tlab">Période</span><input class="ofld dt" id="hpD0" value="${fd(d0)}"><span class="cal">▦</span><span class="dm">–</span><input class="ofld dt" id="hpD1" value="${fd(d1)}"><span class="cal">▦</span>
      ${rg.map(r => `<button class="tb ${!st.d0 && rgE === r ? 'on' : ''}" data-rg="${r}">${r === 'MAX' ? 'Max' : r}</button>`).join('')}
      <span class="tlab">Fréquence</span><select class="ofld dk" id="hpF">${[['D', 'Quotidienne'], ['W', 'Hebdomadaire'], ['M', 'Mensuelle']].filter(([k]) => S.f !== 'M' || k === 'M').map(([k, l]) => `<option value="${k}" ${st.f === k ? 'selected' : ''}>${l}</option>`).join('')}</select>
      <span class="tlab">Donnée</span><select class="ofld" id="hpM">${[['c', 'Dernier cours'], ['o', 'Ouverture'], ['h', 'Plus haut'], ['l', 'Plus bas']].map(([k, l]) => `<option value="${k}" ${st.mk === k ? 'selected' : ''}>${l}</option>`).join('')}</select>
      <span class="tlab">Vue</span><select class="ofld" id="hpV"><option value="P" ${st.v === 'P' ? 'selected' : ''}>Tableau des cours${hasV ? ' et volumes' : ''}</option><option value="O" ${st.v === 'O' ? 'selected' : ''}>Ouverture / haut / bas / dernier</option></select>
      <span class="gsp"></span><span class="tlab">Devise</span><span class="wh">${esc(s.ccy || '')}</span></div>
    <div class="hpg"><div class="hpb" style="grid-template-columns:repeat(${nb},minmax(0,1fr))">${blocks.map(b => `<div>${b.length ? `<table class="t hp"><thead>${head}</thead><tbody>${b.map(row).join('')}</tbody></table>` : ''}</div>`).join('')}</div>
      <div class="hps"><div class="kv2">${[['Plage', `${fd(d0)} – ${fd(d1)}`], ['Période', { D: 'Quotidienne', W: 'Hebdomadaire', M: 'Mensuelle' }[st.f]], ['Devise', esc(s.ccy || '—')], ['Observations', num(W.length, 0)]].map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join('')}
        <span class="h">${esc(mk)}</span>${hi ? [['Plus haut le ' + fd(hi.d), px(s, V(hi))], ['Moyenne', num(sum / W.length, pxd(s) + 2)], ['Plus bas le ' + fd(lo.d), px(s, V(lo))], ['Var. nette', `<span class="${cls(net)}">${net > 0 ? '+' : ''}${px(s, net)}</span>`], ['Var. %', pc(V(first) ? net / V(first) : null)]].map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join('') : ''}
        ${hasV ? `<span class="h">Volume</span><span>Volume moyen</span><b>${num(avgV, 0)}</b><span>Volume total</span><b>${num(W.reduce((a, r) => a + r.v, 0), 0)}</b>` : ''}</div>
        <div class="hpn"><button class="tb" data-p="-1" ${st.page ? '' : 'disabled'}>${ICO.prev} Plus récent</button><span class="dm">Page ${st.page + 1} / ${np}</span><button class="tb" data-p="1" ${st.page < np - 1 ? '' : 'disabled'}>Plus ancien ${ICO.next}</button></div></div></div>
    <div class="lect">MMV (15) = moyenne mobile du volume sur 15 périodes. Semaine = semaine ISO.</div>`;
  m.querySelectorAll('[data-rg]').forEach(b => b.onclick = () => { st.rg = b.dataset.rg; st.d0 = st.d1 = null; st.page = 0; render(); });
  m.querySelectorAll('[data-p]').forEach(b => b.onclick = () => { st.page += +b.dataset.p; render(); });
  $('hpF').onchange = e => { st.f = e.target.value; st.page = 0; render(); };
  $('hpM').onchange = e => { st.mk = e.target.value; render(); }; $('hpV').onchange = e => { st.v = e.target.value; st.page = 0; render(); };
  const dIn = () => { const a = parseDMY($('hpD0').value), b = parseDMY($('hpD1').value); if (!a || !b || b <= a) { toast('Dates au format jj/mm/aaaa, la fin après le début.'); return; } st.d0 = a; st.d1 = b; st.page = 0; render(); };
  ['hpD0', 'hpD1'].forEach(id => { $(id).onchange = dIn; $(id).onkeydown = e => { if (e.key === 'Enter') dIn(); }; });
};

/* ------------------------------------------------------------------ DVD : historique des dividendes au format du terminal (onglet 1), analyse (onglet 2) */
const DVD_ANALYSE = PAGES.DVD;
PAGES.DVD = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Dividend/Split Summary'); const tab = tabState('DVD', 'h');
  setTabs([['h', 'Historique'], ['a', 'Analyse et graphiques']], tab, k => { ST.tab.DVD = k; render(); });
  if (tab === 'a') return DVD_ANALYSE(m, alive);
  const [S, DV, PR] = await Promise.all([series(s.id), isBRVM(s) ? getJSON('dividends.json') : null, isBRVM(s) ? null : getJSON('profiles.json').catch(() => ({}))]); if (!alive()) return;
  const today = new Date().toISOString().slice(0, 10), last = S.c[S.c.length - 1];
  let H = [];
  if (isBRVM(s)) H = DV.filter(x => x.t === s.id && x.dps).map(x => ({ ann: x.ann, det: x.det, pay: x.pay, amt: x.dps, ex: x.ex, ccy: 'XOF', adj: x.adj, dps0: x.dps0, usd: x.usd, fx: x.fx, fxb: x.fxb, cal: x.cal, exc: x.exc }));
  else for (let i = 0; i < S.x.length; i++) if (S.div[i]) H.push({ det: i2s(S.x[i]), amt: S.div[i], ccy: s.ccy || 'USD' });
  H.sort((a, b) => (b.det || b.pay || b.ann || '').localeCompare(a.det || a.pay || a.ann || ''));
  /* fréquence : nombre de versements par an (calculée sur les 3 dernières années complètes) */
  /* (dividende exceptionnel : hors fréquence, dernier dividende, rendement indicatif et croissance ; compté dans le rendement 12 mois) */
  const yrs = {}; H.filter(h => !h.exc).forEach(h => { const y = (h.det || h.pay || '').slice(0, 4); if (y) yrs[y] = (yrs[y] || 0) + 1; }); const cy = +today.slice(0, 4);
  const cnt = [cy - 1, cy - 2, cy - 3].map(y => yrs[y] || 0).filter(Boolean), fq = cnt.length ? Math.round(cnt.reduce((a, b) => a + b, 0) / cnt.length) : 0;
  const fqL = { 1: 'Annuelle', 2: 'Semestrielle', 3: 'Irrégulière', 4: 'Trimestrielle', 12: 'Mensuelle' }[fq] || (fq ? fq + ' par an' : '—');
  const past = H.filter(h => (h.det || h.pay || '') <= today), y1 = new Date(Date.now() - 365 * 864e5).toISOString().slice(0, 10);
  const y2 = new Date(Date.now() - 730 * 864e5).toISOString().slice(0, 10), ttm = past.filter(h => (h.det || h.pay) > y1).reduce((a, h) => a + h.amt, 0), pastR = past.filter(h => !h.exc), ind = !pastR.length || (pastR[0].det || pastR[0].pay || '') < y2 ? null : isBRVM(s) && pastR[0].ex ? pastR.filter(h => h.ex === pastR[0].ex).reduce((a, h) => a + h.amt, 0) : fq ? pastR[0].amt * fq : null;  /* (BRVM : dividende annuel = versements ordinaires du dernier exercice) */  /* (aucun versement depuis deux ans : pas de rendement indicatif) */
  const byY = {}; pastR.forEach(h => { const y = h.ex || +(h.det || h.pay).slice(0, 4); byY[y] = (byY[y] || 0) + h.amt; }); const ys = Object.keys(byY).map(Number).sort((a, b) => a - b).filter(y => isBRVM(s) || y < cy);
  const yL5 = ys[ys.length - 1], g5 = yL5 && byY[yL5 - 5] > 0 && byY[yL5] > 0 ? Math.pow(byY[yL5] / byY[yL5 - 5], 1 / 5) - 1 : null;  /* (sur cinq années : exercice sans dividende cinq ans plus tôt = non calculé) */
  const next = H.filter(h => (h.det || '') > today).slice(-1)[0];
  const net = isBRVM(s) ? 'net' : 'brut';
  /* actions US sans historique de versements dans la source : dernier versement connu (Nasdaq) */
  const NQ = !isBRVM(s) && !H.length && PR && PR[s.id] && PR[s.id].divA ? PR[s.id] : null;
  if (NQ) { const ex = parseNqDate(NQ.exdiv), pay = parseNqDate(NQ.paydiv), dA = nqNum(NQ.divA), y = nqNum(NQ.yld);
    m.innerHTML = `<div class="grid">${pn(`${esc(ykey(s))} · dividendes`, 'DVD', `<div class="dvk">${[['Dividende annualisé (brut)', dA != null ? num(dA, 4) + ' ' + esc(s.ccy || 'USD') : '—'], ['Rendement indicatif (brut)', y != null ? num(y, 2) + ' %' : '—'], ['Dernier détachement', ex ? fd(ex) : '—'], ['Dernier paiement', pay ? fd(pay) : '—']].map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join('')}</div>`)}
      ${pn('Historique des versements', 'DVD', `<table class="t"><thead><tr><th class="l">Annonce</th><th class="l">Détachement</th><th class="l">Enregistrement</th><th class="l">Paiement</th><th>Montant</th><th class="l">Fréquence</th><th class="l">Type</th></tr></thead><tbody><tr><td class="l dm">—</td><td class="l am">${ex ? fd(ex) : '—'}</td><td class="l dm">—</td><td class="l">${pay ? fd(pay) : '—'}</td><td class="dm">n.d.</td><td class="l dm">—</td><td class="l">Dernier versement connu</td></tr></tbody></table>`,
        { np: true, lect: 'Relevé du ' + fds(NQ.d) + ' : seuls le dernier versement et le dividende annualisé sont connus, pas le montant unitaire ni l’historique détaillé. Dividendes par année tirés des comptes publiés : onglet 2.' })}</div>`; return; }
  const kv = [[`Rendement indicatif (${net})`, ind && last ? P1(ind / last, 2) : '—'], [`Rendement 12 mois (${net})`, ttm && last ? P1(ttm / last, 2) : '—'], ['Croissance annuelle 5 ans', P1(g5, 1)], ['Fréquence', fqL],
    ['Dernier dividende', pastR[0] ? `${num(pastR[0].amt, isBRVM(s) ? (Number.isInteger(pastR[0].amt) ? 0 : 2) : 4)} ${pastR[0].ccy}` : '—'], ['Prochain détachement annoncé', next ? fds(next.det) + ' · ' + num(next.amt, isBRVM(s) ? (Number.isInteger(next.amt) ? 0 : 2) : 4) + ' ' + next.ccy : '—']];
  m.innerHTML = `<div class="grid">${pn(`${esc(ykey(s))} · dividendes`, 'DVD', `<div class="dvk">${kv.map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join('')}</div>`, { np: false })}
    ${pn(`Historique des versements (${H.length})`, 'DVD', H.length ? `<div class="tw" style="max-height:calc(100vh - 330px - var(--nwh, 90px))"><table class="t"><thead><tr><th class="l">Annonce</th><th class="l">Détachement</th><th class="l">Enregistrement</th><th class="l">Paiement</th><th>Montant</th><th class="l">Fréquence</th><th class="l">Type</th>${isBRVM(s) ? '<th>Exercice</th>' : ''}</tr></thead><tbody>
      ${H.map(h => `<tr${(h.det || '') > today ? ' class="hl"' : ''}><td class="l">${fds(h.ann)}</td><td class="l am">${fds(h.det)}</td><td class="l dm">—</td><td class="l">${fds(h.pay)}</td><td class="wh">${num(h.amt, isBRVM(s) ? 2 : 4)} ${h.ccy}${adjMark(h)}</td><td class="l">${fqL}</td><td class="l">${isBRVM(s) ? (h.exc ? 'Dividende exceptionnel net' : 'Dividende net') : 'Dividende'}</td>${isBRVM(s) ? `<td>${h.ex || '—'}</td>` : ''}</tr>`).join('')}</tbody></table></div>` : '<div class="empty">Aucun dividende recensé pour ce titre.</div>',
      { np: true, lect: `${isBRVM(s) ? 'Montants nets par action tels qu’annoncés par la société ; a = ramené sur la base des actions actuelles après un fractionnement ou des actions gratuites (montant publié en infobulle) ; $ = publié en cents de dollar : montant officiel en FCFA, sinon converti au cours du jour de sa publication.' : 'Montants par action à la date de détachement ; dates d’annonce et de paiement non publiées pour ce titre.'} En surbrillance : versement à venir. Date d’enregistrement non publiée. Rendement indicatif = ${isBRVM(s) ? 'dividende ordinaire du dernier exercice' : 'dernier dividende × fréquence'} ÷ cours ; rendement 12 mois = dividendes détachés sur 12 mois (exceptionnels compris) ÷ cours. Analyse détaillée : onglet 2.` })}</div>`;
};

/* ------------------------------------------------------------------ BETA : régression (nuage, droite, statistiques) comme l'écran du terminal ; onglet 2 = analyse */
const BETA_ANALYSE = PAGES.BETA;
PAGES.BETA = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Historical Beta'); const tab = tabState('BETA', 'r');
  setTabs([['r', 'Régression'], ['a', 'Fenêtres, pairs et risque']], tab, k => { ST.tab.BETA = k; render(); });
  if (tab === 'a') return BETA_ANALYSE(m, alive);
  const st = ST.beta = ST.beta || {}; if (st.base !== s.id) { st.base = s.id; st.bench = benchFor(s); }
  st.f = st.f || 'W'; st.rg = st.rg || '2A';
  const [S, B] = await Promise.all([series(s.id), series(st.bench)]); if (!alive()) return;
  const end = Math.min(S.x[S.x.length - 1], B.x[B.x.length - 1]), y0 = end - { '1A': 10000, '2A': 20000, '3A': 30000, '5A': 50000 }[st.rg];
  const a = retsBy(S, st.f), b = retsBy(B, st.f), kd = d => st.f === 'D' ? d : st.f === 'W' ? isoWeekKey(d) : Math.floor(d / 100);
  const ks = [...a.keys()].filter(k => b.has(k) && k >= kd(y0)).sort((p, q) => p - q), P = ks.map(k => [(Math.exp(a.get(k)) - 1) * 100, (Math.exp(b.get(k)) - 1) * 100]);
  const o = olsBeta(P); const benches = [...new Set([benchFor(s), st.bench].concat(isBRVM(s) ? ['BRVMC', 'BRVM30', 'SPY', 'QQQ', 'EEM', 'AFK'] : ['SPY', 'QQQ', 'VTI', 'SOXX', 'EEM', 'BRVMC']))];  /* l'indice calculé figure toujours dans la liste */
  let stats = '<div class="empty">Historique commun insuffisant pour cette période.</div>';
  if (o) { const n = o.n, mx = U.mean(P.map(p => p[1])), sxx = P.reduce((t, p) => t + (p[1] - mx) ** 2, 0), res = P.reduce((t, [y, x]) => t + (y - o.a - o.b * x) ** 2, 0), sde = Math.sqrt(res / (n - 2)), sea = sde * Math.sqrt(1 / n + mx * mx / sxx);
    const pval = (() => { const t = Math.abs(o.t), z = t * (1 - 1 / (4 * (n - 2))) / Math.sqrt(1 + t * t / (2 * (n - 2))); const e = Math.exp(-z * z / 2) / Math.sqrt(2 * Math.PI), k = 1 / (1 + .2316419 * z); return 2 * e * k * (.31938153 + k * (-.356563782 + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429)))); })();
    stats = `<div class="kv2 bst">${[['Bêta brut', num(o.b, 3), 'yl'], ['Bêta ajusté', num(o.b * 2 / 3 + 1 / 3, 3), 'yl'], ['Alpha (ordonnée, % par période)', num(o.a, 3)], ['R² (corrélation²)', num(o.r2, 3)], ['R (corrélation)', num(o.r, 3)],
      ['Écart type de l’erreur', num(sde, 3)], ['Erreur type de l’alpha', num(sea, 3)], ['Erreur type du bêta', num(o.se, 3)], ['Test t (bêta)', num(o.t, 3)], ['Significativité (valeur p)', pval < .0001 ? '< 0,0001' : num(pval, 4)], ['Nombre de points', num(n, 0)]]
      .map(([l, v, c]) => `<span>${l}</span><b class="${c || ''}">${v}</b>`).join('')}</div>`; }
  m.innerHTML = `<div class="tools bt1"><span class="tlab">Titre</span><span class="wh">${esc(ykey(s))}</span><span class="tlab">Indice</span><select class="ofld" id="btB">${benches.filter(x => Q.by[x] && x !== s.id).map(x => `<option value="${x}" ${st.bench === x ? 'selected' : ''}>${esc(ykey(Q.by[x]))}</option>`).join('')}</select>
      <span class="tlab">Période</span><select class="ofld dk" id="btF">${[['D', 'Quotidienne'], ['W', 'Hebdomadaire'], ['M', 'Mensuelle']].map(([k, l]) => `<option value="${k}" ${st.f === k ? 'selected' : ''}>${l}</option>`).join('')}</select>
      <span class="tlab">Plage</span>${['1A', '2A', '3A', '5A'].map(r => `<button class="tb ${st.rg === r ? 'on' : ''}" data-rg="${r}">${r}</button>`).join('')}<span class="tlab">Donnée</span><span class="wh">Dernier cours (variation %)</span></div>
    <div class="grid side"><div class="pn"><div class="cv" id="btS" style="height:max(380px, calc(100vh - 300px - var(--nwh, 90px)))"></div></div>${pn('Statistiques de la régression', 'BETA', stats, { lect: `Régression des variations ${{ D: 'quotidiennes', W: 'hebdomadaires', M: 'mensuelles' }[st.f]} (%) de ${esc(s.id)} (axe vertical) sur celles de ${esc(st.bench)} (axe horizontal), ${ks.length ? fd(ks.length && st.f === 'D' ? ks[0] : y0) : ''} – ${fd(end)}. Bêta ajusté = 0,67 × bêta brut + 0,33 (convention Blume). Valeur p &lt; 0,05 = bêta significatif.` })}</div>`;
  $('btB').onchange = e => { st.bench = e.target.value; render(); }; $('btF').onchange = e => { st.f = e.target.value; render(); }; m.querySelectorAll('[data-rg]').forEach(x => x.onclick = () => { st.rg = x.dataset.rg; render(); });
  if (o) scatter($('btS'), { pts: P.map(([y, x]) => [x, y]), line: [o.a, o.b], color: rgba(CL.cyan, .7), lineColor: CL.amber, fx: v => num(v, 1) + ' %', fy: v => num(v, 1) + ' %', xlab: `${st.bench} (%)`, ylab: `${s.id} (%) · y = ${num(o.b, 3)} x ${o.a >= 0 ? '+' : '−'} ${num(Math.abs(o.a), 3)}` });
};

/* ------------------------------------------------------------------ NEWS (ex-TOP) : « Top News » du terminal (sections numérotées, colonne de droite) */
const TOP_PAGES = [['HOME', 'À la une', null], ['AF', 'Afrique, UEMOA et BRVM', x => ['Afrique', 'UEMOA', 'BRVM'].includes(x.c)], ['MKT', 'Marchés', x => x.c === 'Marchés'], ['TECH', 'Tech US', x => x.c === 'Tech US'],
  ['CMD', 'Matières premières', x => x.c === 'Matières premières' || x.ev === 'Matières premières'], ['CB', 'Banques centrales et macro', x => x.c === 'Banques centrales' || ['Banques centrales', 'Macro'].includes(x.ev)],
  ['CO', 'Sociétés citées', x => (x.tk || []).length], ['ERN', 'Résultats et analystes', x => ['Résultats', 'Analystes'].includes(x.ev)]];
PAGES.NEWS = async (m, alive) => {
  const N = await getJSON('news.json').catch(() => null); if (!alive()) return; setTitle('Top News');
  const st = ST.top2 = ST.top2 || { pg: 'HOME', q: '', off: {} };
  if (!N || !N.items || !N.items.length) { m.innerHTML = pn('Top News', 'NEWS', '<div class="empty">Fil d’actualités en cours de constitution.</div>'); return; }
  const q = st.q.trim().toLowerCase(), seenT = new Set(), all = N.items.filter(x => { const k = deent(x.ti || '').toLowerCase().replace(/[^a-z0-9àâçéèêëîïôûùüÿœ]+/g, ' ').trim().slice(0, 70); if (!k || seenT.has(k)) return false; seenT.add(k); return true; })
    .filter(x => !q || (x.ti + ' ' + (x.x || '') + ' ' + (x.s || '') + ' ' + (x.tk || []).join(' ')).toLowerCase().includes(q));
  const hm = t => new Date(t * 1000).toLocaleTimeString('fr-FR', { timeZone: 'Africa/Abidjan', hour: '2-digit', minute: '2-digit' });
  const day = t => new Date(t * 1000).toLocaleDateString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit' }), today = day(Date.now() / 1000);
  let n = 0; const used = new Set();
  const row = x => { n++; used.add(x.u); const tk = (x.tk || []).filter(t => Q.by[t]).slice(0, 3);
    return `<div class="tn" data-n="${n}" data-u="${esc(x.u || '')}"><span class="no">${n})</span><span class="h">${evBadge(x.ev && x.ev !== 'Marchés' ? x.ev : '')}${esc(deent(x.ti))}${tk.map(t => ` <b class="tg" data-sec="${t}" data-to="CN">${t}</b>`).join('')}</span><span class="s">${esc(srcCode(x)) || '—'}</span><span class="t">${day(x.t) === today ? hm(x.t) : day(x.t)}</span></div>`; };
  const sect = (key, title, list, per) => { const off = st.off[key] || 0, np = Math.max(1, Math.ceil(list.length / per)), pg = list.slice(off * per, off * per + per);
    return `<div class="ts"><div class="tsh">${title}${np > 1 ? ` <span class="pgr"><b data-sk="${key}" data-d="-1" title="Précédents">${ICO.prev}</b> ${off + 1} sur ${np} <b data-sk="${key}" data-d="1" title="Suivants">${ICO.next}</b></span>` : ''} <span class="mo" data-pg="${key}">Plus »</span></div>${pg.map(row).join('') || '<div class="dm" style="padding:2px 8px">—</div>'}</div>`; };
  let left = '';
  if (st.pg === 'HOME') {
    const pick = (f, k) => all.filter(x => !used.has(x.u) && f(x)).slice(0, k);
    const top = pick(x => x.ev && !['Marchés'].includes(x.ev) || (x.tk || []).length, 4); left += sect('T', 'Dépêches sélectionnées', top, 4);
    left += sect('AF', 'Afrique, UEMOA et BRVM', all.filter(x => !used.has(x.u) && TOP_PAGES[1][2](x)), 8);
    left += sect('MKT', 'Marchés', all.filter(x => !used.has(x.u) && TOP_PAGES[2][2](x)), 8);
    left += sect('CO', 'Sociétés', all.filter(x => !used.has(x.u) && (x.tk || []).length), 6);
  } else { const P = TOP_PAGES.find(p => p[0] === st.pg); left += sect(st.pg, P[1], all.filter(P[2]), 28); }
  /* colonne de droite : graphique de l'heure (QQQ en séance, sinon BRVM Composite) et « First Word » (dépêches brèves) */
  const fw = all.filter(x => !used.has(x.u) && (x.c === 'Marchés' || x.ev === 'Macro')).slice(0, 9);
  const intra = Q.live && Q.live.intraday && Q.live.intraday.t && Q.live.intraday.t.length > 10;
  m.innerHTML = `<div class="tools ttb"><span class="tnar"><input id="tpQ" value="${esc(st.q)}" placeholder="&lt;Filtrer&gt;"><b>⌕</b></span><button class="tb ${st.pause ? 'on' : ''}" id="tpP">‖ ${st.pause ? 'En pause' : 'Pause'}</button>
      ${TOP_PAGES.map(([k, l]) => `<button class="tb alt ${st.pg === k ? 'on' : ''}" data-pg="${k}">${l}</button>`).join('')}<span class="gsp"></span><span class="dm">${all.length} dépêches · heure GMT (Abidjan) · relevé ${hm(N.ts)}</span></div>
    <div class="grid tpg"><div class="pn tpl">${left}</div>
      <div class="grid" style="align-content:start"><div class="pn"><div class="tsh">Graphique de l’heure <span class="mo" data-fn="${intra ? 'GP' : 'GP'}" data-s="${intra ? 'QQQ' : 'BRVMC'}">Plus »</span></div><div class="tch">${intra ? 'QQQ · séance du jour, 5 minutes (heure de New York)' : 'BRVM Composite · 3 mois'}</div>${cvb('tpC', 190)}</div>
        <div class="pn"><div class="tsh">First Word <span class="mo" data-pg="MKT">Plus »</span></div>${fw.map(x => `<div class="fw" data-u="${esc(x.u || '')}">${esc(deent(x.ti))} <span class="dm">[${hm(x.t)}]</span></div>`).join('') || '<div class="dm" style="padding:4px 8px">—</div>'}</div></div></div>`;
  setActs([{ n: 1, l: 'Toutes les dépêches', run: () => { st.pg = 'HOME'; st.q = ''; render(); } }, { n: 2, l: 'Pages', menu: () => [{ h: 'Pages d’actualités' }].concat(TOP_PAGES.map(([k, l], i) => ({ n: i + 1, l: (st.pg === k ? '● ' : '') + l, run: () => { st.pg = k; render(); } }))) },
    { n: 3, l: 'Recherche', run: () => $('tpQ').focus() }]);
  m.querySelectorAll('[data-u]').forEach(r => r.onclick = e => { if (e.target.closest('[data-sec]')) return; if (r.dataset.u) window.open(r.dataset.u, '_blank', 'noopener'); });
  m.querySelectorAll('[data-pg]').forEach(b => b.onclick = () => { st.pg = b.dataset.pg === 'T' ? 'HOME' : b.dataset.pg; st.off = {}; render(); });
  m.querySelectorAll('[data-sk]').forEach(b => b.onclick = () => { const k = b.dataset.sk; st.off[k] = Math.max(0, (st.off[k] || 0) + +b.dataset.d); render(); });
  $('tpP').onclick = () => { st.pause = !st.pause; render(); };
  $('tpQ').onkeydown = e => { if (e.key === 'Enter') { st.q = e.target.value; st.off = {}; render(); } };
  if (intra) { const I = Q.live.intraday, tt = I.t.map(t => { const d = new Date(t * 1000); return d.getUTCFullYear() * 1e8 + (d.getUTCMonth() + 1) * 1e6 + d.getUTCDate() * 1e4 + d.getUTCHours() * 100 + d.getUTCMinutes(); });
    const ny = t => new Date(t * 1000).toLocaleTimeString('fr-FR', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit' });
    new TSChart($('tpC'), { panes: [{ h: 1, noLegend: true, fmt: v => num(v, 2) }], padR: 56, grid: 'dot', xfmt: v => { const i = tt.indexOf(v); return i >= 0 ? ny(I.t[i]) : ''; } }).set({ x: tt, series: [{ type: 'area', y: I.c, color: '#ffffff', w: 1.1, grad: ['rgba(7,42,82,.97)', 'rgba(3,29,56,.97)'] }] }, [0, tt.length - 1]); }
  else { const S = await series('BRVMC').catch(() => null); if (!alive() || !S) return; const k = Math.max(0, S.x.length - 63);
    new TSChart($('tpC'), { panes: [{ h: 1, noLegend: true, fmt: v => num(v, 1) }], padR: 56, grid: 'dot', xticks: bbgTicks }).set({ x: S.x.slice(k), series: [{ type: 'area', y: S.c.slice(k), color: '#ffffff', w: 1.1, grad: ['rgba(7,42,82,.97)', 'rgba(3,29,56,.97)'] }] }); }
};

/* ------------------------------------------------------------------ MOST : « Most Active » du terminal (classements numérotés, une table) */
PAGES.MOST = async (m, alive) => {
  setTitle('Most Active Securities'); const st = ST.most2 = ST.most2 || { u: 'BRVM', k: 'val' };
  const U0 = st.u === 'BRVM' ? secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity') : st.u === 'NDX' ? secsWhere(s => s.mkt === 'US' && s.ndx) : secsWhere(s => s.mkt === 'US' && s.typ === 'ETF');
  const val = s => s.mkt === 'BRVM' ? (s.vday || 0) : (s.shd || 0) * (s.last || 0), avat = s => s.liq > 0 && val(s) > 0 ? val(s) / s.liq - 1 : null, ccy = st.u === 'BRVM' ? 'XOF' : 'USD';
  const K = [['val', 'Montant échangé (séance)', (a, b) => val(b) - val(a), s => val(s) > 0], ['vol', 'Volume', (a, b) => (b.shd || 0) - (a.shd || 0), s => s.shd > 0], ['up', 'Hausses', (a, b) => b.pct - a.pct, s => s.pct > 0], ['dn', 'Baisses', (a, b) => a.pct - b.pct, s => s.pct < 0],
    ['av', 'Activité inhabituelle', (a, b) => (avat(b) ?? -9) - (avat(a) ?? -9), s => avat(s) != null], ['hi', 'Près du plus haut 52 s.', (a, b) => b.last / b.hi52 - a.last / a.hi52, s => s.hi52 > 0], ['lo', 'Près du plus bas 52 s.', (a, b) => a.last / a.lo52 - b.last / b.lo52, s => s.lo52 > 0]];
  const cur = K.find(x => x[0] === st.k) || K[0], L = U0.filter(s => s.last && cur[3](s)).sort(cur[2]).slice(0, 40), live = U0.filter(s => s.pct != null);
  m.innerHTML = `<div class="tools mst"><span class="tlab">Marché</span><select class="ofld" id="moU">${[['BRVM', 'BRVM · actions'], ['NDX', 'Nasdaq-100'], ['ETF', 'ETF US']].map(([k, l]) => `<option value="${k}" ${st.u === k ? 'selected' : ''}>${l}</option>`).join('')}</select>
      <span class="tlab">Devise</span><span class="wh">${ccy}</span><span class="gsp"></span><span class="dm">${U0.length} titres · ${live.filter(s => s.pct > 0).length} en hausse, ${live.filter(s => s.pct < 0).length} en baisse</span></div>
    ${subTabs(K.map(([k, l]) => [k, l]), st.k, 'data-mk', 1)}
    <div class="grid side">${pn(`${cur[1]} · ${L.length} titres`, 'MOST', `<div class="tw" style="max-height:calc(100vh - 290px - var(--nwh, 90px))"><table class="t"><thead><tr><th class="l">Titre</th><th class="l">Nom</th><th>Dernier</th><th>Var. nette</th><th>Var. %</th><th>Volume</th><th title="Montant échangé pendant la séance du jour">Montant séance (${ccy})</th><th title="Montant de la séance contre la moyenne quotidienne sur 3 mois">Δ moy. 3 mois</th><th>Fourchette 52 s.</th></tr></thead><tbody>
      ${L.map((s, i) => `<tr data-sec="${s.id}" data-to="GP" style="cursor:pointer"><td class="l"><span class="rn">${i + 1})</span><b class="wh">${s.id}</b></td><td class="l am">${esc(s.short || s.n)}</td><td class="wh">${px(s, s.last)}</td><td class="${cls(s.last - s.prev)}">${s.prev ? (s.last - s.prev > 0 ? '+' : '') + px(s, s.last - s.prev) : '—'}</td><td>${pc(s.pct)}</td><td>${s.shd ? num(s.shd, 0) : '—'}</td><td>${val(s) ? valTxt(s, val(s)) : '—'}</td><td>${avat(s) != null ? pc(avat(s), 0) : '—'}</td><td>${rangeBar3(s.last, s.lo52, s.hi52)}</td></tr>`).join('') || '<tr><td class="l dm" colspan="9">Aucun titre pour ce classement.</td></tr>'}</tbody></table></div>`, { np: true, lect: 'Δ moy. 3 mois = montant échangé du jour contre la moyenne quotidienne des trois derniers mois. Montants de la séance du jour. ≈ = montant estimé en séance (volume × cours), remplacé le soir par le montant définitif ; actions US : volume × cours. Clic sur une ligne : graphique du titre.' })}
      ${pn('Largeur du jour', 'MOST', `<div class="kv2"><span>Titres en hausse</span><b class="up">${live.filter(s => s.pct > 0).length}</b><span>Titres en baisse</span><b class="dn">${live.filter(s => s.pct < 0).length}</b><span>Inchangés</span><b>${live.filter(s => !s.pct).length}</b><span>Montant total échangé (séance)</span><b>${U0.some(valEst) ? '≈ ' : ''}${big(U0.reduce((a, s) => a + val(s), 0))} ${ccy}</b><span>Variation médiane</span><b>${pc(U.median ? U.median(live.map(s => s.pct)) : live.map(s => s.pct).sort((a, b) => a - b)[Math.floor(live.length / 2)])}</b></div>${cvb('moH', 200)}`, { lect: 'Répartition des variations du jour (%).' })}</div>`;
  $('moU').onchange = e => { st.u = e.target.value; render(); }; m.querySelectorAll('[data-mk]').forEach(b => b.onclick = () => { st.k = b.dataset.mk; render(); });
  const bins = [-.1, -.05, -.03, -.02, -.01, 0, .01, .02, .03, .05, .1], cnt = new Array(bins.length + 1).fill(0); live.forEach(s => { let i = bins.findIndex(b => s.pct < b); if (i < 0) i = bins.length; cnt[i]++; });
  barChart($('moH'), { labels: ['<-10', '-10/-5', '-5/-3', '-3/-2', '-2/-1', '-1/0', '0/1', '1/2', '2/3', '3/5', '5/10', '>10'], values: cnt, fmt: v => num(v, 0), labelsOnBars: true, colors: cnt.map((_, i) => i < 6 ? '#ff433d' : '#32c74c'), padB: 22 });
};

/* FA : petite icône graphique devant chaque ligne (comme le terminal) → GF sur l'indicateur */
const GF_ICO = '<svg width="11" height="9" viewBox="0 0 11 9"><rect x=".5" y=".5" width="10" height="8" fill="none" stroke="#8a8a8a"/><path d="M2 7V5M4.5 7V3M7 7V4.5M9 7V2" stroke="#ffa028" stroke-width="1.4"/></svg>';
document.addEventListener('click', e => { const g = e.target.closest('[data-gf]'); if (!g) return; e.stopPropagation(); ST.gf = { k: g.dataset.gf, k2: '' }; go('GF', ST.sec); });

/* ------------------------------------------------------------------ RV, onglet 1 : tableau de comparables comme l'écran Relative Valuation */
async function RV_COMPS(m, alive) {
  const s = sec(ST.sec); setTitle('Relative Valuation'); const IDX = await getJSON('fa_index.json').catch(() => null); if (!alive()) return;
  const FI = Object.fromEntries(((IDX && IDX.rows) || []).map(r => [r.id, r]));
  const peers = secsWhere(x => x.id !== s.id && x.mkt === s.mkt && x.cls === 'Equity' && x.typ !== 'ETF' && x.grp === s.grp && !legacy(x)).sort((a, b) => (b.mcap || 0) - (a.mcap || 0)).slice(0, 24);
  const C = [['mcap', 'Capi.', x => x.mcap, v => big(v)], ['last', 'Dernier', x => x.last, (v, x) => px(x, v)], ['pct', 'Var. 1J', x => x.pct, v => pc(v)], ['ytd', 'Var. YTD', x => x.ytd, v => pc(v, 1)],
    ['rev_g', 'Croiss. CA 1 an', x => (FI[x.id] || {}).rev_g, v => pc(v, 1)], ['eps_g', 'Croiss. BPA 1 an', x => (FI[x.id] || {}).eps_g, v => pc(v, 1)], ['pe', 'PER', x => (FI[x.id] || {}).pe ?? x.per, v => num(v, 1)],
    ['pb', 'Cours / actif net', x => (FI[x.id] || {}).pb, v => num(v, 2)], ['ev_ebitda', 'VE / EBITDA', x => (FI[x.id] || {}).ev_ebitda, v => num(v, 1)], ['roe', 'ROE', x => (FI[x.id] || {}).roe, v => P1(v, 1)],
    ['nm', 'Marge nette', x => (FI[x.id] || {}).nm, v => P1(v, 1)], ['dy', 'Rdt div.', x => (FI[x.id] || {}).dy ?? x.yld, v => P1(v, 2)]];
  const st = ST.rvc = ST.rvc || { k: 'mcap', d: -1 }; const sorted = peers.slice().sort((a, b) => { const c = C.find(c => c[0] === st.k), A = c[2](a), B = c[2](b); if (A == null) return 1; if (B == null) return -1; return (A - B) * st.d; });
  const ok = v => v != null && isFinite(v), stat = (f, x) => { const v = peers.concat([s]).map(x).filter(ok).sort((a, b) => a - b); if (!v.length) return null; return f === 'avg' ? v.reduce((a, b) => a + b, 0) / v.length : v[Math.floor((v.length - 1) / 2)] * (v.length % 2 ? 1 : .5) + (v.length % 2 ? 0 : v[v.length / 2] * .5); };
  const cell = (c, x) => { const v = c[2](x); return ok(v) ? c[3](v, x) : '<span class="dm">—</span>'; };
  const sRow = (lab, f) => `<tr class="rvs"><td class="l">${lab}</td><td class="l"></td>${C.map(c => { const v = ['last', 'mcap'].includes(c[0]) ? null : stat(f, c[2]); return `<td>${ok(v) ? c[3](v, s) : ''}</td>`; }).join('')}</tr>`;
  m.innerHTML = `<div class="tools rvt"><span class="tlab">Comparables</span><span class="wh">${esc(s.grp || '—')} · ${s.mkt === 'BRVM' ? 'BRVM' : 'États-Unis'} (${peers.length})</span><span class="tlab">Devise</span><span class="wh">${esc(s.ccy || '')}</span><span class="gsp"></span><span class="dm">Tri : cliquer un en-tête</span></div>
    ${pn(`${esc(ykey(s))} · valorisation relative`, 'RV', `<div class="tw" style="max-height:calc(100vh - 290px - var(--nwh, 90px))"><table class="t rvc"><thead><tr><th class="l">Titre</th><th class="l">Nom</th>${C.map(c => `<th data-rk="${c[0]}" class="${st.k === c[0] ? 'on' : ''}" style="cursor:pointer">${c[1]}${st.k === c[0] ? (st.d > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('')}</tr></thead><tbody>
      <tr class="rvme"><td class="l"><b>${s.id}</b></td><td class="l">${esc(s.short || s.n)}</td>${C.map(c => `<td>${cell(c, s)}</td>`).join('')}</tr>${sRow('Moyenne', 'avg')}${sRow('Médiane', 'med')}
      ${sorted.map((x, i) => `<tr data-sec="${x.id}" data-to="RV" style="cursor:pointer"><td class="l"><span class="rn">${i + 1})</span><b class="wh">${x.id}</b></td><td class="l am">${esc(x.short || x.n)}</td>${C.map(c => `<td>${cell(c, x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`,
      { np: true, lect: `Sociétés du même secteur sur le même marché, classées par capitalisation. Ratios sur le dernier exercice publié ; moyenne et médiane incluent ${esc(s.id)}. Analyse des multiples dans le temps : onglet 2 ; juste valeur : onglet 3.` })}`;
  m.querySelectorAll('[data-rk]').forEach(th => th.onclick = () => { const k = th.dataset.rk; st.d = st.k === k ? -st.d : -1; st.k = k; render(); });
}

/* ------------------------------------------------------------------ SCREN (ex-EQS) : « Equity Screening » du terminal (critères, correspondances, résultats) */
const EQ_F = [ // clé, libellé, catégorie, type (p = %, x = multiple, m = montant, n = nombre), source (f = comptes, s = marché)
  ['mcap', 'Capitalisation boursière', 'Marché', 'm', 's'], ['liq', 'Échanges moyens par séance', 'Marché', 'm', 's'], ['pct', 'Variation du jour', 'Marché', 'p', 's'], ['ytd', 'Performance depuis janvier', 'Marché', 'p', 's'],
  ['r1y', 'Performance sur 1 an', 'Marché', 'p', 's'], ['vol', 'Volatilité sur 1 an', 'Marché', 'p', 's'], ['beta', 'Bêta', 'Marché', 'n', 's'], ['dd', 'Écart au plus haut historique', 'Marché', 'p', 's'], ['rsi', 'RSI 14', 'Marché', 'n', 's'],
  ['pe', 'PER', 'Valorisation', 'x', 'f'], ['fpe', 'PER prévisionnel', 'Valorisation', 'x', 'f'], ['pb', 'Cours / actif net', 'Valorisation', 'x', 'f'], ['ps', 'Cours / chiffre d’affaires', 'Valorisation', 'x', 'f'], ['ev_ebitda', 'VE / EBITDA', 'Valorisation', 'x', 'f'],
  ['fcfy', 'Rendement du free cash-flow', 'Valorisation', 'p', 'f'], ['dy', 'Rendement du dividende', 'Valorisation', 'p', 'f'], ['ey', 'Rendement des bénéfices', 'Valorisation', 'p', 'f'],
  ['roe', 'ROE', 'Rentabilité', 'p', 'f'], ['roic', 'ROIC', 'Rentabilité', 'p', 'f'], ['roa', 'ROA', 'Rentabilité', 'p', 'f'], ['gm', 'Marge brute', 'Rentabilité', 'p', 'f'], ['om', 'Marge d’exploitation', 'Rentabilité', 'p', 'f'], ['nm', 'Marge nette', 'Rentabilité', 'p', 'f'], ['fcfm', 'Marge de free cash-flow', 'Rentabilité', 'p', 'f'],
  ['rev_g', 'Croissance du CA sur 1 an', 'Croissance', 'p', 'f'], ['eps_g', 'Croissance du BPA sur 1 an', 'Croissance', 'p', 'f'], ['fcf_g', 'Croissance du FCF sur 1 an', 'Croissance', 'p', 'f'], ['rev_cagr5', 'TCAM du CA sur 5 ans', 'Croissance', 'p', 'f'], ['eps_cagr5', 'TCAM du BPA sur 5 ans', 'Croissance', 'p', 'f'],
  ['nd_ebitda', 'Dette nette / EBITDA', 'Bilan', 'x', 'f'], ['de', 'Dette / capitaux propres', 'Bilan', 'x', 'f'], ['payout', 'Taux de distribution', 'Bilan', 'p', 'f'], ['fscore', 'Score de Piotroski', 'Bilan', 'n', 'f'], ['altz', 'Z d’Altman', 'Bilan', 'n', 'f']];
const EQ_EX = [['Qualité', [['roic', '>', 15], ['fcfm', '>', 10], ['nd_ebitda', '<', 2]]], ['Valeur', [['pe', 'entre', 0, 12], ['fcfy', '>', 5]]], ['Dividende soutenable', [['dy', '>', 5], ['payout', '<', 80]]],
  ['Croissance', [['rev_g', '>', 15], ['eps_g', '>', 15]]], ['Momentum', [['ytd', '>', 20], ['r1y', '>', 30]]], ['Solidité financière', [['fscore', '>', 6], ['altz', '>', 3]]], ['Liquidité BRVM', [['liq', '>', 50000000]]]];
PAGES.SCREENER = async (m, alive) => {
  setTitle('Equity Screening'); const IDX = await getJSON('fa_index.json').catch(() => null); if (!alive()) return;
  const FI = Object.fromEntries(((IDX && IDX.rows) || []).map(r => [r.id, r]));
  const st = ST.eqs2 = ST.eqs2 || (() => { try { const x = JSON.parse(localStorage.getItem('fqt_eqs_cur') || 'null'); if (x && x.crit) return x; } catch (e) { } return { mkt: 'ALL', sec: 'ALL', cty: 'ALL', crit: [], view: 'b', sort: { k: 'mcap', d: -1 } }; })();
  const save = () => { try { localStorage.setItem('fqt_eqs_cur', JSON.stringify(st)); } catch (e) { } };
  const mine = (() => { try { return JSON.parse(localStorage.getItem('fqt_eqs_my') || '[]'); } catch (e) { return []; } })();
  const F = k => EQ_F.find(f => f[0] === k), val = (s, k) => { const f = F(k); if (!f) return null; const v = f[4] === 's' ? s[k] : (FI[s.id] || {})[k]; return v == null || !isFinite(v) ? null : v; };
  const inp = (f, v) => f[3] === 'p' ? v / 100 : v, out = (f, v) => f[3] === 'p' ? num(v * 100, 1) + ' %' : f[3] === 'x' ? num(v, 1) + ' x' : f[3] === 'm' ? big(v) : num(v, 2);
  const test = (s, c) => { const f = F(c.k), v = val(s, c.k); if (v == null) return false; const a = inp(f, +c.v), b = inp(f, +c.v2); return c.op === '>' ? v > a : c.op === '<' ? v < a : v >= Math.min(a, b) && v <= Math.max(a, b); };
  const U0 = secsWhere(s => s.cls === 'Equity' && s.typ !== 'ETF' && !legacy(s) && (st.mkt === 'ALL' || s.mkt === st.mkt) && (st.sec === 'ALL' || s.grp === st.sec) && (st.cty === 'ALL' || s.cty === st.cty));
  let cur = U0; const steps = st.crit.map(c => { cur = cur.filter(s => test(s, c)); return cur.length; }), R = cur;
  const secsAll = [...new Set(secsWhere(s => s.cls === 'Equity' && s.typ !== 'ETF' && (st.mkt === 'ALL' || s.mkt === st.mkt)).map(s => s.grp).filter(Boolean))].sort();
  const ctys = [...new Set(secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity').map(s => s.cty).filter(Boolean))].sort(), CTY = { CI: 'Côte d’Ivoire', SN: 'Sénégal', BF: 'Burkina Faso', BJ: 'Bénin', ML: 'Mali', NE: 'Niger', TG: 'Togo', GW: 'Guinée-Bissau' };
  const load = (crit, nm) => { st.crit = crit.map(([k, op, v, v2]) => ({ k, op, v, v2 })); st.name = nm; st.view = 'b'; save(); render(); };
  setActs([{ n: 91, l: 'Construire / modifier', run: () => { st.view = 'b'; render(); } },
    { n: 92, l: 'Mes filtres', menu: () => [{ h: 'Mes filtres enregistrés' }].concat(mine.map((x, i) => ({ n: i + 1, l: esc(x.name), run: () => { Object.assign(st, JSON.parse(JSON.stringify(x.st))); st.view = 'r'; save(); render(); } })),
      [{ h: '' }, { l: 'Enregistrer le filtre actuel…', run: () => { const nm = prompt('Nom du filtre :', st.name || 'Mon filtre'); if (!nm) return; const L = mine.filter(x => x.name !== nm); L.unshift({ name: nm, st: JSON.parse(JSON.stringify(st)) }); try { localStorage.setItem('fqt_eqs_my', JSON.stringify(L.slice(0, 20))); } catch (e) { } toast('Filtre « ' + nm + ' » enregistré dans ce navigateur.'); } }]) },
    { n: 93, l: 'Exemples de filtres', menu: () => [{ h: 'Filtres types' }].concat(EQ_EX.map(([nm, c], i) => ({ n: i + 1, l: esc(nm), run: () => load(c, nm) }))) }]);
  const critRows = st.crit.map((c, i) => { const f = F(c.k); return `<tr><td class="l"><span class="rn">${i + 1})</span><span class="am">${esc(f[1])}</span></td><td class="l"><select class="ofld dk" data-op="${i}">${['>', '<', 'entre'].map(o => `<option ${c.op === o ? 'selected' : ''}>${o}</option>`).join('')}</select>
      <input class="ofld eqv" data-v="${i}" value="${esc(c.v)}">${c.op === 'entre' ? ` et <input class="ofld eqv" data-v2="${i}" value="${esc(c.v2 ?? '')}">` : ''} <span class="dm">${f[3] === 'p' ? '%' : f[3] === 'x' ? 'x' : f[3] === 'm' ? (st.mkt === 'US' ? '$' : st.mkt === 'BRVM' ? 'XOF' : 'devise du titre') : ''}</span></td><td class="wh">${steps[i]}</td><td><b class="eqx" data-x="${i}" title="Retirer">✕</b></td></tr>`; }).join('');
  const builder = `<div class="grid eqg"><div class="pn"><div class="tsh">Exemples de filtres</div>${EQ_EX.map(([nm, c], i) => `<div class="eqp" data-ex="${i}"><span class="rn">${i + 1})</span>${esc(nm)}</div>`).join('')}
        ${mine.length ? `<div class="tsh">Mes filtres</div>${mine.map((x, i) => `<div class="eqp" data-my="${i}"><span class="rn">${i + 1})</span>${esc(x.name)}</div>`).join('')}` : ''}</div>
      <div class="pn"><div class="tsh">Critères de filtrage${st.name ? ` · <span class="am">${esc(st.name)}</span>` : ''}</div>
        <div class="eqc"><div><span class="tlab">Marché</span><select class="ofld" id="eqM">${[['ALL', 'BRVM et États-Unis'], ['BRVM', 'BRVM'], ['US', 'États-Unis']].map(([k, l]) => `<option value="${k}" ${st.mkt === k ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
          <div><span class="tlab">Secteur</span><select class="ofld" id="eqSe"><option value="ALL">Tous</option>${secsAll.map(x => `<option ${st.sec === x ? 'selected' : ''}>${esc(x)}</option>`).join('')}</select></div>
          <div><span class="tlab">Pays (BRVM)</span><select class="ofld" id="eqCt"><option value="ALL">Tous</option>${ctys.map(x => `<option value="${x}" ${st.cty === x ? 'selected' : ''}>${esc(CTY[x] || x)}</option>`).join('')}</select></div></div>
        <div class="eqa"><input class="ofld" id="eqAdd" placeholder="Tapez un critère et choisissez-le dans la liste (ex. PER, ROE, dividende)" autocomplete="off"></div>
        <div class="tsh">Critères sélectionnés</div><table class="t eqt"><thead><tr><th class="l">Critère</th><th class="l">Condition</th><th>Correspondances</th><th></th></tr></thead><tbody>
          <tr><td class="l"><span class="am">Univers de titres</span></td><td class="l dm">${st.mkt === 'ALL' ? 'BRVM et États-Unis' : st.mkt}${st.sec !== 'ALL' ? ' · ' + esc(st.sec) : ''}${st.cty !== 'ALL' ? ' · ' + esc(CTY[st.cty] || st.cty) : ''}</td><td class="wh">${U0.length}</td><td></td></tr>${critRows || '<tr><td class="l dm" colspan="4">Aucun critère : ajoutez-en un ci-dessus ou choisissez un exemple.</td></tr>'}</tbody></table>
        <div class="eqb"><button class="tb" id="eqClr">Tout effacer</button><button class="tb on" id="eqGo">Résultats (${R.length}) ${ICO.next}</button></div></div></div>`;
  const cols = [['mcap', 'Capi.'], ...st.crit.map(c => c.k).filter((k, i, a) => a.indexOf(k) === i && k !== 'mcap').map(k => [k, F(k)[1]]), ...[['pe', 'PER'], ['roe', 'ROE'], ['dy', 'Rdt div.'], ['ytd', 'Depuis janv.']].filter(([k]) => !st.crit.some(c => c.k === k))];
  const rs = R.slice().sort((a, b) => { const A = st.sort.k === 'id' ? a.id : val(a, st.sort.k), B = st.sort.k === 'id' ? b.id : val(b, st.sort.k); if (A == null) return 1; if (B == null) return -1; return (typeof A === 'string' ? A.localeCompare(B) : A - B) * st.sort.d; });
  const results = pn(`Résultats · ${R.length} titres${st.name ? ' · ' + esc(st.name) : ''}`, 'SCREENER', `<div class="tw" style="max-height:calc(100vh - 270px - var(--nwh, 90px))"><table class="t"><thead><tr><th class="l" data-sk="id" style="cursor:pointer">Titre</th><th class="l">Nom</th><th class="l">Marché</th><th class="l">Secteur</th>${cols.map(([k, l]) => `<th data-sk="${k}" style="cursor:pointer" class="${st.sort.k === k ? 'on' : ''}">${esc(l)}${st.sort.k === k ? (st.sort.d > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('')}</tr></thead><tbody>
    ${rs.map((s, i) => `<tr data-sec="${s.id}" data-to="DES" style="cursor:pointer"><td class="l"><span class="rn">${i + 1})</span><b class="wh">${s.id}</b></td><td class="l am">${esc(s.short || s.n)}</td><td class="l dm">${s.mkt}</td><td class="l dm">${esc(s.grp || '')}</td>${cols.map(([k]) => { const v = val(s, k); return `<td>${v == null ? '<span class="dm">—</span>' : out(F(k), v)}</td>`; }).join('')}</tr>`).join('') || '<tr><td class="l dm" colspan="9">Aucun titre ne remplit tous les critères.</td></tr>'}</tbody></table></div>`,
    { np: true, lect: 'Ratios du dernier exercice publié ; données de marché du dernier relevé. Clic sur une ligne : fiche DES. Tri : cliquer un en-tête.', tools: `<button class="tb" id="eqBk">${ICO.prev} Modifier les critères</button>` });
  m.innerHTML = st.view === 'r' ? results : builder;
  if (st.view === 'r') { $('eqBk').onclick = () => { st.view = 'b'; save(); render(); }; m.querySelectorAll('[data-sk]').forEach(th => th.onclick = () => { const k = th.dataset.sk; st.sort = { k, d: st.sort.k === k ? -st.sort.d : -1 }; save(); render(); }); return; }
  $('eqM').onchange = e => { st.mkt = e.target.value; st.sec = 'ALL'; save(); render(); }; $('eqSe').onchange = e => { st.sec = e.target.value; save(); render(); }; $('eqCt').onchange = e => { st.cty = e.target.value; save(); render(); };
  $('eqGo').onclick = () => { st.view = 'r'; save(); render(); }; $('eqClr').onclick = () => { st.crit = []; st.name = ''; save(); render(); };
  m.querySelectorAll('[data-ex]').forEach(d => d.onclick = () => load(EQ_EX[+d.dataset.ex][1], EQ_EX[+d.dataset.ex][0]));
  m.querySelectorAll('[data-my]').forEach(d => d.onclick = () => { Object.assign(st, JSON.parse(JSON.stringify(mine[+d.dataset.my].st))); save(); render(); });
  m.querySelectorAll('[data-x]').forEach(b => b.onclick = () => { st.crit.splice(+b.dataset.x, 1); save(); render(); });
  m.querySelectorAll('[data-op]').forEach(sl => sl.onchange = () => { st.crit[+sl.dataset.op].op = sl.value; save(); render(); });
  m.querySelectorAll('[data-v],[data-v2]').forEach(el => el.onchange = () => { const i = +(el.dataset.v ?? el.dataset.v2), v = parseFloat(String(el.value).replace(',', '.').replace(/\s/g, '')); if (!isFinite(v)) { toast('Valeur numérique attendue.'); return; } st.crit[i][el.dataset.v != null ? 'v' : 'v2'] = v; save(); render(); });
  const add = $('eqAdd'); const showF = () => { const q = add.value.trim().toLowerCase(); const L = EQ_F.filter(f => !q || f[1].toLowerCase().includes(q) || f[0].includes(q) || f[2].toLowerCase().includes(q)).slice(0, 14);
    ddOpen(add, [{ h: 'Champs disponibles' }].concat(L.map((f, i) => ({ n: i + 1, code: f[2], l: esc(f[1]), run: () => { st.crit.push({ k: f[0], op: f[3] === 'p' || f[0] === 'fscore' || f[0] === 'altz' || f[3] === 'm' ? '>' : '<', v: { p: 10, x: 15, m: 1e9, n: 1 }[f[3]] }); save(); render(); } })))); };
  add.onfocus = showF; add.oninput = showF;
};

/* ------------------------------------------------------------------ CN : « Company News » du terminal (une liste chronologique numérotée) */
PAGES.CN = async (m, alive) => {
  const s = sec(ST.sec), brvm = isBRVM(s); setTitle('Company News');
  const [N, EV, RP, DV, AN] = await Promise.all([getJSON('news.json').catch(() => ({ items: [] })), brvm ? getJSON('events.json').catch(() => []) : [], brvm ? getJSON('reports.json').catch(() => null) : null, brvm ? getJSON('dividends.json').catch(() => []) : [], getJSON('anomalies.json').catch(() => null)]); if (!alive()) return;
  const al = aliasesOf(s).map(a => a.toLowerCase());
  const its = (N.items || []).filter(x => (x.tk || []).includes(s.id) || (() => { const t = (x.ti + ' ' + (x.x || '')).toLowerCase(); return al.some(a => a === s.id.toLowerCase() ? new RegExp('\\b' + a + '\\b').test(t) : a.length > 3 && t.includes(a)); })());
  const docs = RP ? Object.entries(RP.issuers || {}).filter(([, x]) => x.t === s.id).flatMap(([slug]) => (RP.docs || {})[slug] || []) : [];
  const H = [];  // { ts (tri), d (aaaa-mm-jj), hm, cat, k, t, u, s, x }
  for (const x of its) H.push({ ts: x.t * 1000, cat: 'N', k: x.ev && x.ev !== 'Marchés' ? x.ev : '', t: deent(x.ti), u: x.u, s: srcCode(x), x: deent(x.x || ''), hm: true });
  const evU = new Set();
  for (const e of evMerge(EV.filter(x => x.t === s.id))) { if (e.u) evU.add(e.u); H.push({ ts: Date.parse(e.d + 'T12:00:00Z'), cat: 'A', k: e.c || 'Avis', t: e.ti, u: e.u, s: '' }); }
  for (const d of docs) if (d.d && !evU.has(d.u)) H.push({ ts: Date.parse(i2s(+d.d) + 'T12:00:00Z'), cat: 'P', k: /etats? financiers/i.test(d.ti) ? 'États financiers' : /activit/i.test(d.ti) ? 'Rapport d’activité' : 'Publication', t: d.ti, u: d.u, s: '' });
  for (const x of DV.filter(x => x.t === s.id && x.dps)) if (x.det) H.push({ ts: Date.parse(x.det + 'T12:00:00Z'), cat: 'D', k: 'Dividende', t: `Détachement du dividende de l’exercice ${x.ex} : ${num(x.dps, 2)} FCFA net`, s: '' });
  for (const a of ((AN && AN.by && AN.by[s.id]) || []).filter(a => a.d)) H.push({ ts: Date.parse(i2s(a.d) + 'T12:00:00Z'), cat: 'X', k: 'Anomalie · ' + a.k, t: a.m, s: 'FQT' });
  H.sort((a, b) => b.ts - a.ts);
  const CAT = [['ALL', 'Tout'], ['N', 'Actualités'], ...(brvm ? [['A', 'Avis officiels'], ['P', 'Publications de la société'], ['D', 'Dividendes']] : []), ['X', 'Anomalies']];
  const st = ST.cn2 = ST.cn2 || { c: 'ALL', q: '' }; if (!CAT.some(c => c[0] === st.c)) st.c = 'ALL';
  const q = st.q.toLowerCase(), L = H.filter(h => (st.c === 'ALL' || h.cat === st.c) && (!q || (h.t + ' ' + h.k).toLowerCase().includes(q)));
  const today = new Date().toISOString().slice(0, 10), when = h => { const d = new Date(h.ts); return h.hm && d.toISOString().slice(0, 10) === today ? d.toLocaleTimeString('fr-FR', { timeZone: 'Africa/Abidjan', hour: '2-digit', minute: '2-digit' }) : d.toLocaleDateString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', year: '2-digit' }); };
  const col = h => h.cat === 'X' ? 'var(--dn)' : EV_COL[h.k] || (h.cat === 'A' ? '#5fd0ea' : h.cat === 'P' ? '#f9a33a' : h.cat === 'D' ? '#2fd26a' : '#8a8a8a');
  m.innerHTML = `<div class="tools ttb"><span class="tnar"><input id="cnQ" value="${esc(st.q)}" placeholder="&lt;Filtrer&gt;"><b>⌕</b></span>${CAT.map(([k, l]) => `<button class="tb alt ${st.c === k ? 'on' : ''}" data-cc="${k}">${l} (${k === 'ALL' ? H.length : H.filter(h => h.cat === k).length})</button>`).join('')}<span class="gsp"></span><span class="dm">heure GMT (Abidjan) · mise à jour toutes les 15 min</span></div>
    ${pn(`${esc(ykey(s))} · ${esc(s.short || s.n)} · ${L.length} éléments`, 'CN', `<div class="tw" style="max-height:calc(100vh - 280px - var(--nwh, 90px))">${L.slice(0, 400).map((h, i) => `<div class="tn cnr" data-n="${i + 1}" data-u="${esc(h.u || '')}" title="${esc(h.x || '')}"><span class="no">${i + 1})</span><span class="h">${h.k ? `<b class="evb" style="background:${col(h)}">${esc(h.k.split(' · ')[0])}</b>` : ''}${esc(h.t || '')}</span><span class="s">${esc(h.s || '')}</span><span class="t">${when(h)}</span></div>`).join('') || '<div class="empty">Aucun élément pour ce filtre.</div>'}</div>`,
      { np: true, lect: `Réunit les articles qui citent la société (« ${al.map(esc).join(' », « ')} »)${brvm ? ', ses avis officiels, ses publications et ses détachements de dividendes' : ''} et les anomalies statistiques détectées (ANOM). Clic : ouvre l’article ou le document. Fil général : NEWS.` })}`;
  m.querySelectorAll('[data-cc]').forEach(b => b.onclick = () => { st.c = b.dataset.cc; render(); });
  m.querySelectorAll('.cnr[data-u]').forEach(r => r.onclick = () => { if (r.dataset.u) window.open(r.dataset.u, '_blank', 'noopener'); });
  $('cnQ').onkeydown = e => { if (e.key === 'Enter') { st.q = e.target.value; render(); } };
};
