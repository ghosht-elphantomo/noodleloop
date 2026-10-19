/* ================= FQT — QLAB : onglet « Valorisation » (moteur QLAB-V) =================
   Fichier autonome de la fonction QLAB : l'onglet « Statistiques » existant (pages2.js) est repris tel quel ; l'onglet
   « Valorisation » affiche les estimations calculées chaque soir après la clôture par scripts/qlab.py (données data/qlab/),
   en trois sous-onglets : Valorisation (valeur de chacun des sept modèles), Risques et alertes, Qualité et facteurs.
   Styles propres à cet onglet injectés ici (préfixe qv-) : aucun fichier partagé n'est modifié. */
const QLAB_STATS = PAGES.QLAB;
const QV = { sub: 'val' };
(function qvStyle() {
  if (document.getElementById('qv-style')) return;
  const st = document.createElement('style'); st.id = 'qv-style';
  st.textContent = `
.qv-head{display:flex;flex-wrap:wrap;gap:4px 18px;align-items:baseline;padding:5px 8px;background:#0b0b0b;border:1px solid var(--line);margin-bottom:4px}
.qv-head .v{font-size:20px;color:var(--white)}.qv-head .l{color:var(--amber);font-size:11.5px;margin-right:4px}
.qv-warn{padding:3px 8px;margin:0 0 4px;border-left:3px solid var(--dn);background:#1a0606;color:#ffc9c6;font-size:12px}
.qv-info{padding:3px 8px;margin:0 0 4px;border-left:3px solid var(--amber);background:#160f02;color:#ffd9a6;font-size:12px}
.qv-rng{position:relative;height:46px;margin:6px 10px 2px}
.qv-rng .ax{position:absolute;left:0;right:0;top:22px;height:1px;background:var(--line2)}
.qv-rng .b1{position:absolute;top:15px;height:15px;background:rgba(77,167,253,.18)}
.qv-rng .b2{position:absolute;top:15px;height:15px;background:rgba(77,167,253,.38)}
.qv-rng .c{position:absolute;top:9px;width:2px;height:27px;background:var(--white)}
.qv-rng .p{position:absolute;top:5px;width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-top:9px solid var(--yel);margin-left:-6px}
.qv-rng .m{position:absolute;top:19px;width:7px;height:7px;border-radius:50%;margin-left:-3px;border:1px solid #000}
.qv-rng .t{position:absolute;top:33px;font-size:10.5px;color:var(--dim);transform:translateX(-50%);white-space:nowrap}
.qv-kind{display:inline-block;font-size:10.5px;padding:0 4px;border:1px solid currentColor;border-radius:2px;line-height:14px}
.qv-bar{display:inline-block;height:9px;background:var(--cyan);vertical-align:middle}
.qv-tor{display:grid;grid-template-columns:minmax(120px,220px) 1fr;gap:2px 8px;font-size:12px;align-items:center}
.qv-tor .tr{position:relative;height:13px;background:#141414}
.qv-tor .tr i{position:absolute;top:1px;height:11px;background:var(--cyan)}
.qv-tor .tr b{position:absolute;top:-2px;bottom:-2px;width:1px;background:var(--yel)}
.qv-hist{display:flex;align-items:flex-end;gap:1px;height:130px;padding:4px 6px 0;position:relative}
.qv-hist i{flex:1;background:var(--cyan);min-height:1px}
.qv-hist .pm{position:absolute;top:0;bottom:0;width:2px;background:var(--yel)}
.qv-hist .cm{position:absolute;top:0;bottom:0;width:2px;background:var(--white)}
.qv-sel{display:flex;gap:4px;flex-wrap:wrap;align-items:center;padding:3px 0}
.qv-sel select{background:var(--org);color:#000;border:0;font:var(--fw) 12px var(--mono);height:20px}
.qv-note{padding:3px 8px;margin:0 0 4px;border-left:3px solid var(--line2);background:#0d0d0d;color:#bdbdbd;font-size:12px}
.qv-ok{color:var(--up)}.qv-no{color:var(--dim)}
.qv-disc{color:var(--dim);font-size:11.5px;padding:6px 2px;line-height:1.45}
.qv-svg{width:100%;height:220px;display:block}
@media(max-width:700px){.qv-head .v{font-size:17px}.qv-tor{grid-template-columns:110px 1fr}.qv-mt th:nth-child(5),.qv-mt tr>td:nth-child(5):not([colspan]){display:none}.qv-mt td{white-space:normal!important}}`;
  document.head.appendChild(st);
})();

const qvP = (v, d = 1) => v == null || !isFinite(v) ? '—' : num(v * 100, d) + ' %';
const qvS = (v, d = 1) => v == null || !isFinite(v) ? '<span class="fl">—</span>' : `<span class="${v > 0 ? 'up' : v < 0 ? 'dn' : ''}">${v > 0 ? '+' : ''}${num(v * 100, d)} %</span>`;
const qvN = (v, d = 0) => v == null || !isFinite(v) ? '—' : num(v, d);
const qvF = v => v == null || !isFinite(v) ? '—' : num(v, Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2);
const qvD = d => d ? fmtD(+String(d).replace(/-/g, '').slice(0, 8)) : '—';
const qvM = (v) => v == null || !isFinite(v) ? '—' : num(v / 1e3, Math.abs(v) >= 1e5 ? 0 : 1) + ' Md';
const QV_KIND = { fait: ['Fait', 'up'], estimation: ['Estimation', 'cyan'], 'hypothèse': ['Hypothèse', 'am'] };
const QV_SUBS = [['val', 'Valorisation'], ['risk', 'Risques et alertes'], ['q', 'Qualité et facteurs']];
const QV_DISC = '<div class="qv-disc">QLAB est un outil d’analyse : les valeurs estimées dépendent d’hypothèses explicites et ne prédisent pas le cours futur. Elles ne garantissent aucune performance et ne constituent pas, à elles seules, une recommandation personnalisée d’investissement. Valeurs en francs CFA par action, sur la base du nombre d’actions actuel.</div>';

PAGES.QLAB = async (m, alive) => {
  const s = sec(ST.sec);
  const okV = !!(s && s.mkt === 'BRVM' && s.cls === 'Equity');
  const tabs = [['s', 'Statistiques'], ['v', 'Valorisation', okV ? '' : 'Réservé aux actions de la BRVM']];
  // ancien onglet « Prévisions » (retiré le 19/10/2026) gardé en mémoire par le navigateur : retour à Statistiques
  let tab = tabState('QLAB', 's'); if (tab !== 's' && tab !== 'v') tab = ST.tab.QLAB = 's'; if (tab === 'v' && !okV) tab = ST.tab.QLAB = 's';
  setTabs(tabs, tab, k => { if (k === 'v' && !okV) { toast('La valorisation QLAB est réservée aux actions de la BRVM.'); return; } ST.tab.QLAB = k; render(); });
  if (tab === 's') return QLAB_STATS(m, alive);
  return qvPage(m, alive, s);
};

async function qvPage(m, alive, s) {
  setTitle(`QLAB Valorisation · ${(s.short || s.n || s.id).toUpperCase()}`);
  m.innerHTML = '<div class="empty">Chargement de la valorisation…</div>';
  const [IX, C] = await Promise.all([getJSON('qlab/index.json').catch(() => null), getJSON(`qlab/${s.id}.json`).catch(() => null)]); if (!alive()) return;
  if (!IX) { m.innerHTML = pn('Valorisation QLAB', 'QLAB', '<div class="empty">Le moteur de valorisation n’a pas encore produit de résultats. Il est calculé chaque soir après la clôture.</div>'); return; }
  const sub = QV_SUBS.some(x => x[0] === QV.sub) ? QV.sub : (QV.sub = 'val');
  const bar = subTabs(QV_SUBS, sub, 'data-qv');
  const bind = () => m.querySelectorAll('[data-qv]').forEach(b => b.onclick = () => { QV.sub = b.dataset.qv; qvPage(m, alive, s); });
  if (!C || !C.cur) {
    const why = C && C.fail && C.fail.length ? C.fail[C.fail.length - 1].err.join(' ; ') : 'aucune estimation n’a encore été produite pour ce titre';
    m.innerHTML = bar + pn('Valorisation QLAB', 'QLAB', `<div class="empty">Pas d’estimation publiée pour ${esc(s.short || s.n)} : ${esc(why)}.<br>Le moteur ne publie une estimation que si les modèles applicables donnent un résultat cohérent ; sinon il le signale ici plutôt que d’afficher un chiffre peu fiable, et refait l’essai automatiquement à chaque passage du soir.</div>`) + QV_DISC;
    bind(); return;
  }
  const A = C.cur.a;
  const body = sub === 'val' ? qvVal(C, A, IX) : sub === 'risk' ? qvRiskAll(C, A) : qvQualAll(C, A);
  m.innerHTML = bar + qvHead(C, IX) + body + QV_DISC; bind();
}

/* en-tête commun : valeur, fourchette, cours, confiance, version, avertissements */
function qvHead(C, IX) {
  const A = C.cur.a, K = C.mkt || {};
  const nx = IX.next_cycle ? qvD(IX.next_cycle) : '—';
  return `<div class="qv-head"><span><span class="l">Dernier cours</span><span class="v">${qvF(K.price)}</span> FCFA <span class="dm">(${qvD(K.pdate)})</span></span>
    <span><span class="l">${esc(C.cur.type_n)}</span>${qvD(A.date)} <span class="dm">(comptes ${A.fy})</span></span><span><span class="l">Prochaine réévaluation complète</span>${nx}</span></div>
    ${(K.k && Math.abs(K.k - 1) > 1e-6) ? `<div class="qv-info">Valeurs par action ajustées du fractionnement intervenu depuis l’évaluation (×${num(1 / K.k, 2)}).</div>` : ''}`;
}

/* 11) Valorisation : la valeur de chacun des sept modèles, sans synthèse */
const QV_NM = { dcf: 'DCF probabiliste', ddm: 'Actualisation des dividendes (DDM)', ri: 'Résultat résiduel', mult_own: 'Multiples historiques de la société', mult_peer: 'Multiples des sociétés comparables' };
function qvVal(C, A, IX) {
  const K = C.mkt || {}, k = K.k || 1, M = A.mc;
  const row = (no, n, v, rng) => `<tr><td class="l am">${no}</td><td class="l wh">${n}</td><td><b>${v}</b></td><td>${rng}</td></tr>`;
  const vrow = (no, id) => { const x = A.models.find(z => z.id === id);
    return x && x.ok ? row(no, esc(QV_NM[id]), qvF(x.v * k), `${qvF(x.p10 * k)} – ${qvF(x.p90 * k)}`) : row(no, esc(QV_NM[id]), '<span class="qv-no">non applicable</span>', `<span class="qv-no">${esc(x ? x.why : 'données insuffisantes')}</span>`); };
  const mm = M && A.models.find(z => z.id === M.main && z.ok);
  const mcr = mm ? row(2, `Simulation Monte-Carlo <span class="dm">(${qvN(M.n)} trajectoires, ${esc(QV_NM[M.main] || M.main)})</span>`, qvF(mm.p50 * k), `${qvF(mm.p10 * k)} – ${qvF(mm.p90 * k)}`)
    : row(2, 'Simulation Monte-Carlo', '<span class="qv-no">non applicable</span>', '<span class="qv-no">aucun modèle intrinsèque applicable</span>');
  const th = (A.rev && A.rev.thr || [])[0];
  const rvr = row(7, 'DCF inversé <span class="dm">(hypothèse contenue dans le cours)</span>', th ? `${esc(th.n)} : ${qvP(th.v)}` : '<span class="qv-no">non calculable</span>', '—');
  const tbl = `<div class="tw"><table class="t"><thead><tr><th class="l">N°</th><th class="l">Modèle</th><th>Valeur par action</th><th>Fourchette 10-90 %</th></tr></thead><tbody>
    ${vrow(1, 'dcf')}${mcr}${vrow(3, 'ddm')}${vrow(4, 'mult_own')}${vrow(5, 'mult_peer')}${vrow(6, 'ri')}${rvr}</tbody></table></div>`;
  return pn('Valorisation par modèle', 'QLAB', tbl, { lect: `Valeurs en francs CFA par action ; fourchette : 10e et 90e centiles des simulations. Dernier cours : ${qvF(K.price)} FCFA.` });
}

/* sensibilités, régimes et seuils (partie de « Risques et alertes ») */
function qvRisk(C, A) {
  const k = (C.mkt && C.mkt.k) || 1, price = C.mkt && C.mkt.price, SE = A.sens;
  if (!SE) return pn('Sensibilités', 'QLAB', '<div class="empty">Sensibilités indisponibles : aucun modèle intrinsèque applicable.</div>');
  const cell = v => { if (v == null) return '<td class="fl">—</td>'; const r = price ? v * k / price - 1 : 0; return `<td style="background:${heatBg(r, .6)}">${qvF(v * k)}</td>`; };
  const g = SE.grid, xp = g.xlbl.includes('relatif') ? (x => (x > 0 ? '+' : '') + num(x * 100, 0) + ' %') : (x => (x > 0 ? '+' : '') + num(x * 100, 0) + ' pt');
  const grid = `<div class="tw"><table class="t hm"><thead><tr><th class="l">Coût des fonds propres \\ ${esc(g.xlbl)}</th>${g.x.map(x => `<th>${xp(x)}</th>`).join('')}</tr></thead><tbody>${g.ke.map((a, i) => `<tr><td class="l am">${a > 0 ? '+' : ''}${num(a * 100, 0)} pt</td>${g.v[i].map(cell).join('')}</tr>`).join('')}</tbody></table></div>`;
  const g2 = SE.grid2, grid2 = `<div class="tw"><table class="t hm"><thead><tr><th class="l">Croissance de long terme \\ rentabilité</th>${g2.x.map(x => `<th>${x > 0 ? '+' : ''}${num(x * 100, 0)} %</th>`).join('')}</tr></thead><tbody>${g2.glt.map((a, i) => `<tr><td class="l am">${a > 0 ? '+' : ''}${num(a * 100, 1)} pt</td>${g2.v[i].map(cell).join('')}</tr>`).join('')}</tbody></table></div>`;
  const T = SE.tornado, all = T.flatMap(t => [t.lo, t.hi]).concat(price ? [price / k] : []), lo = Math.min(...all), hi = Math.max(...all), X = v => (v - lo) / (hi - lo || 1) * 100;
  const torn = `<div class="qv-tor">${T.map(t => `<span>${esc(t.n)}</span><div class="tr"><i style="left:${X(t.lo)}%;width:${Math.max(.5, X(t.hi) - X(t.lo))}%"></i>${price ? `<b style="left:${X(price / k)}%"></b>` : ''}</div>`).join('')}</div>
    <div class="dm" style="font-size:11px;margin-top:3px">barres : valeur du modèle principal quand l’hypothèse passe de son 10e à son 90e centile, les autres restant centrales ; trait jaune : cours. Bornes : ${qvF(lo * k)} – ${qvF(hi * k)}</div>`;
  const glob = A.glob.length ? `<div class="qv-tor">${A.glob.map(r => `<span>${esc(r.n)}</span><div class="tr"><i style="left:${r.rho < 0 ? 50 + r.rho * 50 : 50}%;width:${Math.abs(r.rho) * 50}%;background:${r.rho < 0 ? 'var(--dn)' : 'var(--up)'}"></i><b style="left:50%;background:#666"></b></div>`).join('')}</div>` : '';
  const thr = (A.rev.thr || []).length ? `<div class="kv2">${A.rev.thr.map(t => `<span>${esc(t.n)}</span><b>${qvP(t.v)}</b>`).join('')}</div>` : '<div class="dm">Aucun seuil calculable dans les bornes testées.</div>';
  const reg = `<div class="tw"><table class="t"><thead><tr><th class="l">Régime économique</th><th class="l">Hypothèse pour ce type d’entreprise</th><th>Effet sur la valeur</th><th>Valeur</th></tr></thead><tbody>${A.reg.map(r => `<tr><td class="l am" title="${esc(r.desc)}">${esc(r.n)}</td>
    <td class="l dm" style="white-space:normal">${esc(r.desc)} : croissance ${r.hyp.dg > 0 ? '+' : ''}${num(r.hyp.dg, 1)} pt, rentabilité ${r.hyp.dprof > 0 ? '+' : ''}${num(r.hyp.dprof * 100, 0)} %, rendement exigé ${r.hyp.dke > 0 ? '+' : ''}${num(r.hyp.dke, 1)} pt, ${r.hyp.dur ? r.hyp.dur + ' ans' : 'durable'}${r.eff ? ' — ' + esc(r.eff) : ''}</td><td>${qvS(r.dv, 0)}</td><td>${qvF(r.v * k)}</td></tr>`).join('')}</tbody></table></div>`;
  return `<div class="grid c2"><div>${pn('Sensibilité croisée : coût des fonds propres × ' + esc(g.xlbl.split(' (')[0]), 'QLAB', grid, { lect: 'Valeur du modèle principal pour des variations simultanées de deux hypothèses. Vert : au-dessus du cours, rouge : en dessous.' })}
    ${pn('Sensibilité croisée : croissance de long terme × rentabilité', 'QLAB', grid2)}
    ${pn('Régimes économiques', 'QLAB', reg, { lect: 'Les régimes n’ont pas le même effet sur toutes les entreprises : les effets supposés dépendent du modèle économique (hypothèses de travail affichées, pas des probabilités).' })}</div>
    <div>${pn('Hypothèses les plus influentes (une à la fois)', 'QLAB', torn)}${pn('Influence globale (simulation, interactions comprises)', 'QLAB', glob, { lect: 'Corrélation de rang entre chaque hypothèse tirée et la valeur simulée : elle tient compte des variations simultanées de toutes les hypothèses.' })}
    ${pn('Seuils : où la conclusion change', 'QLAB', thr)}${pn('Risques propres au modèle économique', 'QLAB', `<div class="lectb"><p>${A.profile.risks.map(esc).join('<br>')}</p></div>`)}</div></div>`;
}

/* facteurs de qualité et qualité des données */
function qvQual(C, A) {
  const F = C.fac || { scores: {}, raw: {}, def: [] }, raw = F.raw || {};
  const fmtR = (id, v) => v == null ? '—' : id === 'F6' ? num(v, 0) : id === 'F10' ? esc(raw.F10_txt || '') : ['F2', 'F4'].includes(id) ? num(v, 2) : id === 'F5' && !A.profile.arch_n.match(/Banque|bancaire|financier/) ? num(-v, 2) + ' ×' : id === 'F9' ? num(v * 100, 0) + ' %' : qvP(v);
  const tbl = `<div class="tw"><table class="t"><thead><tr><th class="l">Facteur</th><th class="l">Définition</th><th>Valeur</th><th class="l">Rang parmi les sociétés de la BRVM (0-100)</th></tr></thead><tbody>${F.def.map(d => { const s = F.scores[d.id];
    return `<tr><td class="l am">${d.id} ${esc(d.n)}</td><td class="l dm" style="white-space:normal">${esc(d.d)}</td><td>${d.id === 'F10' ? esc(raw.F10_txt || 'non notée') : fmtR(d.id, raw[d.id])}</td><td class="l">${s == null ? '<span class="fl">non mesurable</span>' : `<span class="qv-bar" style="width:${s}px;background:${s >= 60 ? 'var(--up)' : s <= 30 ? 'var(--dn)' : 'var(--amber)'}"></span> ${s}`}</td></tr>`; }).join('')}
    <tr><td class="l am">Gouvernance</td><td class="l dm" colspan="3" style="white-space:normal">${esc(F.gov || '')}</td></tr></tbody></table></div>`;
  const D = A.dq;
  const dq = `<div class="kv2"><span>Dernier exercice publié</span><b>${D.fy}</b><span>Exercices de résultat disponibles</span><b>${D.years}</b><span>Part des 5 derniers exercices vérifiés</span><b>${qvP(D.vshare, 0)}</b>
    <span>Dernier cours</span><b>${qvD(A.pdate)}</b></div><div class="lectb" style="margin-top:4px"><p><b>Exercices vérifiés</b> : ${D.verified.join(', ') || 'aucun'}.</p>
    ${D.missing.length ? `<p><b>Données manquantes</b> : ${D.missing.map(esc).join(' ; ')} (les modèles qui en dépendent sont désactivés ou moins pondérés).</p>` : ''}${D.warn.map(w => `<p class="am">${esc(w)}</p>`).join('')}</div>`;
  return `<div class="grid c2">${pn('Facteurs de qualité et de risque', 'QLAB', tbl, { lect: 'Chaque facteur est défini et mesuré sur les données publiées ; le rang compare la société aux autres sociétés de la BRVM (100 = la plus favorable). Les facteurs servent à l’interprétation et au niveau de confiance ; ils ne modifient pas la valeur.' })}${pn('Qualité des données', 'QLAB', dq)}</div>`;
}

/* 12) Risques et alertes */
function qvRiskAll(C, A) {
  const K = C.mkt || {}, k = K.k || 1, st = C.status || { warn: [] }, pr = K.pr || {}, liq = A.liq || {}, D = A.dq || { warn: [], missing: [] };
  const today = +new Date().toISOString().slice(0, 10).replace(/-/g, ''), ago = d => { try { return (Date.now() - Date.parse(String(d).replace(/^(\d{4})(\d\d)(\d\d)$/, '$1-$2-$3'))) / 864e5; } catch (e) { return 1e9; } };
  const AL = [];
  if (st.ok === false) AL.push(['alarme', 'Réévaluation complète non réalisée : la dernière valorisation valide est conservée.']);
  (st.warn || []).forEach(w => AL.push([/inférieure|supérieure|inférieures|supérieures/.test(w) ? 'alarme' : 'alerte', w]));
  (pr.warn || []).forEach(w => AL.push(['alerte', 'Cours : ' + w]));
  if (A.syn.conf < 35) AL.push(['alarme', `Les modèles divergent fortement ou les données sont fragiles (score de fiabilité ${A.syn.conf}/100) : les valeurs indiquent un ordre de grandeur.`]);
  else if (A.syn.conf < 55) AL.push(['alerte', `Fiabilité limitée des valeurs (score ${A.syn.conf}/100).`]);
  if (liq.zero != null && liq.zero >= .3) AL.push(['alerte', `Titre peu échangé : aucune transaction lors de ${qvP(liq.zero, 0)} des séances de l’année ; le cours peut être peu représentatif et difficile à traiter.`]);
  const F = (C.fail || []).slice(-1)[0]; if (F && ago(F.d) <= 10) AL.push(['alerte', `Tentative de réévaluation refusée le ${qvD(F.d)} : ${(F.err || []).join(' ; ')} — valorisation précédente conservée, nouvel essai automatique chaque soir.`]);
  const E = (C.events || []).slice().reverse(), e0 = E[0];
  if (e0 && ago(e0.d_detect) <= 30) AL.push([e0.lvl === 2 ? 'alarme' : 'info', `Documents examinés le ${qvD(e0.d_detect)} (${(e0.titles || []).slice(0, 2).map(esc).join(' ; ')}) : ${e0.dec}`]);
  (D.warn || []).forEach(w => AL.push(['info', w]));
  if ((D.missing || []).length) AL.push(['info', 'Données manquantes : ' + D.missing.join(' ; ') + ' (les modèles qui en dépendent sont désactivés ou moins pondérés).']);
  const CL = { alarme: ['Alarme', 'qv-warn'], alerte: ['Alerte', 'qv-info'], info: ['Information', 'qv-note'] };
  const al = AL.length ? AL.map(a => `<div class="${CL[a[0]][1]}"><b>${CL[a[0]][0]}</b> — ${esc(a[1])}</div>`).join('') : '<div class="qv-note"><b>Aucune alerte</b> — données à jour, cours fiable, modèles cohérents.</div>';
  const V = (C.vers || []).slice().reverse();
  const vt = `<div class="tw"><table class="t"><thead><tr><th class="l">Version</th><th class="l">Type</th><th>Date</th><th>Exercice</th><th>Cours à la date</th><th class="l">Motif</th></tr></thead><tbody>${V.map(v => `<tr${v.id === C.cur.id ? ' class="cur"' : ''}><td class="l">${esc(v.id)}</td><td class="l">${esc(v.type_n)}</td><td>${qvD(v.date)}</td><td>${v.fy}</td><td>${qvF(v.price)}</td><td class="l dm" style="white-space:normal">${esc(v.reason)}</td></tr>`).join('')}</tbody></table></div>`;
  const ev = E.length ? `<div class="tw"><table class="t"><thead><tr><th>Détection</th><th class="l">Documents examinés</th><th>Niveau</th><th class="l">Décision</th><th class="l">Critères mesurés</th></tr></thead><tbody>${E.slice(0, 30).map(e => `<tr><td>${qvD(e.d_detect)}</td>
    <td class="l" style="white-space:normal;max-width:320px">${(e.titles || []).map(esc).join('<br>')}</td><td>${e.lvl === 2 ? '<b class="am">2</b>' : '1'}</td><td class="l" style="white-space:normal;max-width:300px">${esc(e.dec)}</td>
    <td class="l dm" style="white-space:normal">${(e.crit || []).map(c => `${c.hit ? '<b class="am">' : ''}${esc(c.n)} : ${esc(c.txt)}${c.thr != null ? ` (seuil ${num(Math.abs(c.thr) * 100, 0)} %)` : ''}${c.hit ? '</b>' : ''}`).join('<br>')}</td></tr>`).join('')}</tbody></table></div>`
    : '<div class="dm" style="padding:6px">Aucun document nouveau examiné depuis la version en vigueur.</div>';
  const lq = pn('Liquidité (distincte de l’incertitude sur la valeur)', 'QLAB', `<div class="kv2"><span>Séances sans échange (1 an)</span><b>${qvP(liq.zero, 0)}</b><span>Montant échangé moyen par séance (1 an)</span><b>${liq.adv1y ? num(liq.adv1y / 1e6, 1) + ' M FCFA' : '—'}</b>
      <span>Séances pour vendre 10 / 50 / 100 M FCFA</span><b>${['d10', 'd50', 'd100'].map(x => liq.d && liq.d[x] != null ? num(liq.d[x], 1) : '—').join(' / ')}</b><span>Prime d’illiquidité estimée</span><b>${qvP(liq.lp, 2)}</b></div>`, { lect: 'Un cours stable n’est pas forcément un risque faible : le titre peut simplement être peu échangé. La prime d’illiquidité indique ce qu’exigerait un investisseur qui veut être rémunéré pour la difficulté à vendre ; elle n’est pas déduite des valeurs.' });
  return `${pn('Alarmes et alertes', 'QLAB', al, { lect: '<b>Alarme</b> : point qui peut invalider les valeurs ou les rend très incertaines. <b>Alerte</b> : point à surveiller (cours, liquidité, réévaluation refusée). <b>Information</b> : contexte des données. Les alertes sont recalculées chaque soir.' })}
    ${qvRisk(C, A)}
    <div class="grid c2"><div>${lq}${pn('Révisions des valorisations', 'QLAB', vt, { lect: 'Chaque version est conservée telle qu’elle a été publiée (données utilisées, hypothèses, résultats des modèles), horodatée et chaînée à la précédente par une empreinte : aucune valorisation passée n’est réécrite.' })}</div>
    <div>${pn('Événements examinés', 'QLAB', ev, { lect: '<b>Niveau 1</b> : vérification, recalcul de contrôle ; les valorisations publiées ne changent pas. <b>Niveau 2</b> : réévaluation exceptionnelle complète, seulement si un seuil est franchi (valeur intrinsèque ≥ 10 %, bénéfice ≥ 15 %, nombre d’actions ≥ 5 %, dividende réduit de plus de moitié, dégradation de notation d’au moins deux crans). Les variations du cours ne déclenchent jamais, à elles seules, une réévaluation.' })}</div></div>`;
}

/* 13) Qualité et facteurs, avec les ratios et les comptes utilisés */
function qvQualAll(C, A) {
  const Hh = A.hist, ys = Hh.y.slice(-12), off = Hh.y.length - ys.length;
  const R = [['Chiffre d’affaires (PNB pour les banques)', 'rev', 'm'], ['Résultat d’exploitation', 'ebit', 'm'], ['EBITDA', 'ebitda', 'm'], ['Résultat net', 'ni', 'm'], ['Fonds propres', 'eq', 'm'],
    ['Flux de trésorerie d’exploitation', 'ocf', 'm'], ['Investissements', 'capex', 'm'], ['Dette nette', 'nd', 'm'], ['Dépôts de la clientèle', 'deposits', 'm'], ['Crédits à la clientèle', 'loans', 'm'], ['Coût du risque', 'cor', 'm'],
    ['Rentabilité des fonds propres', 'roe', 'p'], ['Marge nette', 'nm', 'p'], ['Marge d’exploitation', 'om', 'p'], ['Dividende ordinaire par action', 'dps', 'd'], ['Taux de distribution', 'pay', 'p']]
    .filter(r => Hh[r[1]] && Hh[r[1]].slice(off).some(v => v != null));
  const hist = `<div class="tw"><table class="t"><thead><tr><th class="l">Millions FCFA</th>${ys.map((y, i) => `<th title="${Hh.ver[off + i] ? 'comptes vérifiés dans les états financiers publiés' : 'non vérifié'}">${y}${Hh.ver[off + i] ? '' : '*'}</th>`).join('')}</tr></thead><tbody>
    ${R.map(r => `<tr><td class="l am">${r[0]}</td>${Hh[r[1]].slice(off).map(v => `<td>${v == null ? '<span class="fl">—</span>' : r[2] === 'p' ? qvP(v) : r[2] === 'd' ? num(v, 2) : qvN(v, 0)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const Ra = A.ratios;
  const rat = `<div class="kv2"><span>PER (dernier exercice)</span><b>${qvF(Ra.pe)}</b><span>Cours / fonds propres</span><b>${qvF(Ra.pb)}</b><span>Rendement du dernier dividende</span><b>${qvP(Ra.dy)}</b>
    <span>Rentabilité des fonds propres (médiane 3 ans)</span><b>${qvP(Ra.roe3)}</b><span>Marge nette (médiane 3 ans)</span><b>${qvP(Ra.nm3)}</b><span>Croissance annuelle du chiffre d’affaires 5 / 10 ans</span><b>${qvP(Ra.cagr_rev5)} / ${qvP(Ra.cagr_rev10)}</b>
    <span>Croissance annuelle du résultat 5 ans</span><b>${qvP(Ra.cagr_ni5)}</b><span>Flux d’exploitation / résultat net (médiane)</span><b>${Ra.conv == null ? '—' : num(Ra.conv, 2)}</b><span>Taux de distribution (médiane 5 ans)</span><b>${qvP(Ra.pay5)}</b>
    <span>Exercices avec dividende sur 10 ans / baisses de plus de 10 %</span><b>${Ra.div10} / ${Ra.cuts}</b><span>Variabilité du résultat (5 ans)</span><b>${Ra.cv_ni == null ? '—' : num(Ra.cv_ni, 2)}</b>
    <span>Volatilité du cours (3 ans) / plus forte baisse (5 ans)</span><b>${qvP(Ra.vol3)} / ${qvP(Ra.mdd5)}</b><span>Bénéfice / fonds propres par action</span><b>${qvF(Ra.eps0)} / ${qvF(Ra.bvps0)}</b></div>`;
  const P = A.profile, fmtH = h => h.fmt === 'num' ? num(h.v, 2) : h.fmt === 'm' ? qvN(h.v, 0) + ' M FCFA' : qvP(h.v, 2);
  const hy = `<div class="tw"><table class="t"><thead><tr><th class="l">Hypothèse</th><th>Valeur</th><th class="l">Statut</th><th class="l">Justification</th></tr></thead><tbody>${A.hyp.map(h => { const kd = QV_KIND[h.kind] || [h.kind, 'dm'];
    return `<tr><td class="l am">${esc(h.n)}</td><td>${fmtH(h)}</td><td class="l"><span class="qv-kind ${kd[1]}">${kd[0]}</span></td><td class="l" style="white-space:normal;min-width:240px">${esc(h.why)}</td></tr>`; }).join('')}</tbody></table></div>`;
  return qvQual(C, A) + `<div class="grid c2">${pn('Comptes utilisés (exercice ' + A.fy + ' et antérieurs)', 'QLAB', hist, { lect: '* exercice non vérifié dans les états financiers publiés (données de secours). Les banques publient un produit net bancaire à la place du chiffre d’affaires.' })}${pn('Principaux ratios', 'QLAB', rat)}</div>
    <div class="grid c2">${pn('Hypothèses des modèles', 'QLAB', hy, { lect: '<b>Fait</b> : donnée publiée. <b>Estimation</b> : grandeur mesurée sur les données. <b>Hypothèse</b> : choix de modélisation documenté. Aucune donnée manquante n’est complétée par un chiffre inventé : un modèle qui en a besoin est désactivé.' })}
    ${pn('Profil de la société', 'QLAB', `<div class="lectb"><p><b>${esc(A.name)}</b> — ${esc(P.act)}.</p><p>Modèle économique retenu : <b>${esc(P.arch_n)}</b> ; ${esc(P.fw_txt)}.</p>${P.notes.length ? `<p>${P.notes.map(esc).join(' · ')}</p>` : ''}<p><b>Moteurs</b> : ${P.drivers.map(esc).join(' ; ')}.</p></div>`)}</div>`;
}

