/* ================= FQT — BRVM : saison des résultats, publications attendues et retards, exposition pays ================= */
'use strict';
/* Obligations d'information périodique des sociétés cotées, telles que la BRVM les publie (exercice clos le 31 décembre) :
   - 1er et 3e trimestres : principaux indicateurs un mois après la fin du trimestre (30 avril, 31 octobre) ;
   - 1er semestre : rapport d'activité certifié quatre mois après la fin du semestre (31 octobre) ;
   - exercice : états financiers au plus tard le 30 avril de l'année suivante.
   Une période compte comme publiée dès le premier document de la société qui la nomme dans son intitulé (rapport d'activités,
   états financiers, rapport annuel ou du conseil, communiqué de résultats, publication de la société). Rien n'est supposé : sans document
   trouvé, la case dit « aucun document trouvé ». */
const PUB_P = {
  A: { lab: 'Exercice', due: y => `${y + 1}-04-30`, rule: 'états financiers de l’exercice : au plus tard le 30 avril de l’année suivante' },
  T1: { lab: '1er trimestre', due: y => `${y}-04-30`, rule: 'principaux indicateurs du 1er trimestre : au plus tard le 30 avril' },
  S1: { lab: '1er semestre', due: y => `${y}-10-31`, rule: 'rapport d’activité du 1er semestre certifié : au plus tard le 31 octobre' },
  T3: { lab: '3e trimestre', due: y => `${y}-10-31`, rule: 'principaux indicateurs du 3e trimestre : au plus tard le 31 octobre' } };
const PUB_CATS = new Set(["Rapport d'activité", 'Rapport d’activité', 'États financiers', 'Rapport annuel', 'Publication société', 'Résultats financiers', 'Communiqué société', 'Rapport des commissaires']);
const pubNorm = s => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
const pubDays = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 864e5);
/* document d'information périodique : catégories ci-dessus, ou rapport du conseil / de gestion / états financiers joints à
   une convocation d'assemblée */
const pubDoc = x => PUB_CATS.has(x.c) || (x.c === 'Convocation / communiqué AG' && /rapport (du conseil|de gestion|annuel)|etats financiers/.test(pubNorm(x.ti)));
/* période nommée dans l'intitulé d'un document : [code, année, année déduite] ou null ; année = la plus récente citée, jamais
   après la date de publication (« 2025 et 2024 » parle de 2025) ; sans année dans l'intitulé, elle est déduite de la date de
   publication (comptes annuels publiés l'année suivante ; semestre et trimestres publiés dans l'année) et signalée */
function pubPeriod(x) {
  const t = pubNorm(x.ti), py = +(x.d || '9999').slice(0, 4), pm = +(x.d || '0000-00').slice(5, 7), ys = (t.match(/\b(19|20)\d\d\b/g) || []).map(Number).filter(y => y <= py);
  let k = null;
  if (/\b(3|3e|3eme|troisieme)\s*trimestre|\b9 mois|neuf mois|30 septembre/.test(t)) k = 'T3';
  else if (/\b(2|2e|2eme|2nd|deuxieme)\s*trimestre/.test(t)) k = 'T2';
  else if (/\b(4|4e|4eme|quatrieme)\s*trimestre/.test(t)) k = 'T4';
  else if (/\b(1|1er|1ere|premier)\s*trimestre|31 mars/.test(t)) k = 'T1';
  else if (/\b(2|2e|2eme|2nd|second|deuxieme)\s*semestre/.test(t)) k = 'S2';
  else if (/semestr|30 juin|six mois|\b6 mois/.test(t)) k = 'S1';
  else if (/exercice|annuel|31 decembre|etats financiers|rapport (du conseil|de gestion)/.test(t) || ['États financiers', 'Rapport annuel', 'Résultats financiers'].includes(x.c)) k = 'A';
  if (!k) return null;
  if (ys.length) return [k, Math.max(...ys), false];
  const y = k === 'A' ? py - 1 : k === 'S1' ? (pm >= 7 ? py : py - 1) : k === 'T3' ? (pm >= 10 ? py : py - 1) : k === 'T1' ? (pm >= 4 ? py : py - 1) : null;
  return y ? [k, y, true] : null;
}
/* première publication de chaque période, par société ; un intitulé dont l'année est manifestement fausse (période déjà
   publiée l'an passé et document paru plus de dix mois après l'échéance) est rattaché à l'année suivante, avec une mention */
function pubIndex(E, ids) {
  const P = {}; for (const id of ids) P[id] = {};
  const L = E.filter(x => P[x.t] && x.d && pubDoc(x)).sort((a, b) => a.d.localeCompare(b.d));
  for (const x of L) {
    const p = pubPeriod(x); if (!p || !PUB_P[p[0]]) continue;
    let [k, y, inf] = p, fix = false;
    if (P[x.t][k + y] && !P[x.t][k + (y + 1)] && pubDays(PUB_P[k].due(y), x.d) > 300) { y += 1; fix = true; }
    const key = k + y; if (!P[x.t][key]) P[x.t][key] = { d: x.d, ti: x.ti, u: x.u, fix, inf };
  }
  return P;
}
/* état d'une période pour une société : à temps, en retard, aucun document (échéance passée), à venir ; null si la société
   n'était pas encore cotée à l'échéance */
function pubState(P, s, k, y, today) {
  const due = PUB_P[k].due(y), first = s.first ? i2s(s.first) : null;
  if (first && first > due) return null;
  const r = P[s.id] && P[s.id][k + y];
  const per = `${PUB_P[k].lab} ${y}`;
  if (r) { const late = pubDays(due, r.d); return { st: late > 0 ? 'late' : 'ok', late, r, due, per }; }
  return today > due ? { st: 'miss', late: pubDays(due, today), due, per } : { st: 'todo', left: pubDays(today, due), due, per };
}
function pubCell(z) {
  if (!z) return '<td class="l dm" title="Pas encore cotée à l’échéance">—</td>';
  const lk = z.r && z.r.u ? ` <a href="${esc(z.r.u)}" target="_blank" rel="noopener" title="${esc(z.r.ti)}">doc.</a>` : '';
  const fx = z.r && z.r.fix ? ' <span class="dm" title="L’intitulé du document porte l’année précédente alors que cette période-là était déjà publiée : rattaché à cette période.">*</span>' : z.r && z.r.inf ? ' <span class="dm" title="L’intitulé du document ne donne pas l’année : déduite de la date de publication.">*</span>' : '';
  if (z.st === 'ok') return `<td class="l up" title="Publié le ${fds(z.r.d)} (échéance ${fds(z.due)})">${fds(z.r.d)}${fx}${lk}</td>`;
  if (z.st === 'late') return `<td class="l am" title="Publié le ${fds(z.r.d)}, ${z.late} jours après l’échéance du ${fds(z.due)}">${fds(z.r.d)} · +${z.late} j${fx}${lk}</td>`;
  if (z.st === 'miss') return `<td class="l dn" title="${z.per} : aucun document trouvé dans les publications de la société ; échéance du ${fds(z.due)} dépassée de ${z.late} jours">aucun document · +${z.late} j</td>`;
  return `<td class="l dm" title="Échéance le ${fds(z.due)}">attendu · J-${z.left}</td>`;
}
/* saison en cours : janvier-avril = exercice précédent et 1er trimestre ; mai-décembre = 1er semestre et 3e trimestre */
function pubSeason(today) { const y = +today.slice(0, 4); return today.slice(5) <= '04-30' ? [['A', y - 1], ['T1', y]] : [['S1', y], ['T3', y]]; }
const pubEq = () => secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity');

async function brvmSaison(m, alive) {
  setTitle('BRVM Earnings Season');
  const E = await getJSON('events.json').catch(() => null); if (!alive()) return;
  if (!Array.isArray(E)) { m.innerHTML = pn('Saison des résultats', 'BRVM', '<div class="empty">Publications indisponibles pour le moment.</div>'); return; }
  const today = i2s(Q.sum.asof), all = pubEq(), P = pubIndex(E, all.map(s => s.id)), SE = pubSeason(today);
  const head = SE.map(([k, y]) => { const Z = all.map(s => pubState(P, s, k, y, today)).filter(Boolean), n = Z.length, pub = Z.filter(z => z.st === 'ok' || z.st === 'late').length, late = Z.filter(z => z.st === 'late').length, due = PUB_P[k].due(y), left = pubDays(today, due);
    return `<div class="kv2"><span>${PUB_P[k].lab} ${y}</span><b>${pub} sur ${n} publiés${late ? ` (${late} en retard)` : ''}</b><span>Échéance</span><b>${fds(due)} ${left >= 0 ? `(J-${left})` : `(passée de ${-left} j)`}</b></div><div class="pbar"><i style="width:${n ? (pub / n * 100).toFixed(1) : 0}%"></i></div>`; }).join('');
  const rows = all.map(s => ({ s, z: SE.map(([k, y]) => pubState(P, s, k, y, today)) }))
    .map(r => ({ ...r, last: r.z.map(z => z && z.r ? z.r.d : '').sort().pop() || '' }))
    .sort((a, b) => b.last.localeCompare(a.last) || a.s.id.localeCompare(b.s.id));
  const firstU = new Set(); for (const [k, y] of SE) for (const s of all) { const r = P[s.id][k + y]; if (r && r.u) firstU.add(r.u); }
  const inSe = x => { const p = pubPeriod(x); return (p && SE.some(([k, y]) => p[0] === k && p[1] === y)) || (x.u && firstU.has(x.u)); };
  const recent = E.filter(x => P[x.t] && x.d && pubDoc(x) && inSe(x)).sort((a, b) => b.d.localeCompare(a.d)).slice(0, 40);
  m.innerHTML = `<div class="grid c2">${pn('Avancement de la saison', 'BRVM', head, { lect: `Échéances fixées par la BRVM pour les sociétés cotées : ${SE.map(([k]) => PUB_P[k].rule).join(' ; ')}. Une période compte comme publiée dès le premier document de la société qui la nomme. Une société cotée après l’échéance n’est pas comptée.` })}
    ${pn('Publications de la saison', 'BRVM', `<div class="tw" style="max-height:260px"><table class="t"><tbody>${recent.map(x => `<tr data-sec="${x.t}" data-to="CN"><td class="l">${fds(x.d)}</td><td class="l tk">${x.t}</td><td class="l nm">${esc(x.ti)}</td><td class="l">${x.u ? `<a href="${esc(x.u)}" target="_blank" rel="noopener">doc.</a>` : ''}</td></tr>`).join('') || '<tr><td class="l dm">Aucune publication pour cette saison.</td></tr>'}</tbody></table></div>`, { np: true })}</div>
    ${pn(`Sociétés · ${SE.map(([k, y]) => PUB_P[k].lab + ' ' + y).join(' et ')}`, 'BRVM', `<div class="tw" style="max-height:60vh"><table class="t"><thead><tr><th class="l">Titre</th><th class="l">Société</th><th class="l">Secteur</th>${SE.map(([k, y]) => `<th class="l">${PUB_P[k].lab} ${y}</th>`).join('')}<th>Cours</th><th>1 sem.</th></tr></thead><tbody>
      ${rows.map(({ s, z }) => `<tr data-sec="${s.id}" data-to="CN"><td class="l tk">${s.id}</td><td class="l nm">${esc(s.short || s.n)}${s.susp ? ' <span class="dn" title="Cotation suspendue">SUSP.</span>' : ''}</td><td class="l dm">${esc(s.grp || '')}</td>${z.map(pubCell).join('')}<td class="wh">${px(s, s.last)}</td><td>${pc(s.r1w, 1)}</td></tr>`).join('')}</tbody></table></div>`,
      { np: true, lect: 'Date de la première publication de chaque période ; « +N j » = jours de retard sur l’échéance ; « aucun document » = rien trouvé dans les publications de la société après l’échéance ; « attendu » = échéance à venir. Clic sur une ligne : actualités de la société.' })}`;
}

async function brvmAttendues(m, alive) {
  setTitle('BRVM Disclosure Calendar');
  const E = await getJSON('events.json').catch(() => null); if (!alive()) return;
  if (!Array.isArray(E)) { m.innerHTML = pn('Publications attendues et retards', 'BRVM', '<div class="empty">Publications indisponibles pour le moment.</div>'); return; }
  const today = i2s(Q.sum.asof), y0 = +today.slice(0, 4), all = pubEq(), P = pubIndex(E, all.map(s => s.id));
  const PER = [['A', y0 - 2], ['T1', y0 - 1], ['S1', y0 - 1], ['T3', y0 - 1], ['A', y0 - 1], ['T1', y0], ['S1', y0], ['T3', y0]];
  const rows = all.map(s => { const z = PER.map(([k, y]) => pubState(P, s, k, y, today)); const late = z.reduce((t, x) => t + (x && (x.st === 'late' || x.st === 'miss') ? x.late : 0), 0), nm = z.filter(x => x && x.st === 'miss').length, nl = z.filter(x => x && x.st === 'late').length; return { s, z, late, nm, nl }; })
    .sort((a, b) => b.nm - a.nm || b.late - a.late || a.s.id.localeCompare(b.s.id));
  const tot = PER.map((p, i) => { const Z = rows.map(r => r.z[i]).filter(Boolean); return { ok: Z.filter(z => z.st === 'ok').length, late: Z.filter(z => z.st === 'late').length, miss: Z.filter(z => z.st === 'miss').length, todo: Z.filter(z => z.st === 'todo').length, n: Z.length }; });
  const nxt = PER.filter(([k, y]) => PUB_P[k].due(y) >= today).map(([k, y], j) => [k, y, rows.filter(r => { const z = pubState(P, r.s, k, y, today); return z && z.st === 'todo'; }).map(r => r.s.id)]);
  m.innerHTML = `${pn('Respect des échéances par période', 'BRVM', `<div class="tw"><table class="t"><thead><tr><th class="l">Période</th><th class="l">Échéance</th><th>Sociétés</th><th>À temps</th><th>En retard</th><th>Aucun document</th><th>À venir</th></tr></thead><tbody>${PER.map(([k, y], i) => `<tr><td class="l am">${PUB_P[k].lab} ${y}</td><td class="l">${fds(PUB_P[k].due(y))}</td><td>${tot[i].n}</td><td class="up">${tot[i].ok}</td><td class="am">${tot[i].late}</td><td class="dn">${tot[i].miss}</td><td class="dm">${tot[i].todo}</td></tr>`).join('')}</tbody></table></div>`,
      { np: true, lect: `Règles de la BRVM (exercice clos le 31 décembre) : ${Object.values(PUB_P).map(p => p.rule).join(' ; ')}. Une société cotée après une échéance n’est pas comptée pour cette période.` })}
    ${nxt.length ? pn('Prochaines échéances', 'BRVM', nxt.map(([k, y, L]) => `<p><b class="am">${PUB_P[k].lab} ${y}</b> · échéance ${fds(PUB_P[k].due(y))} (J-${pubDays(today, PUB_P[k].due(y))}) · encore attendus (${L.length}) : ${L.length ? L.map(t => `<span class="tk" data-sec="${t}" data-to="CN" style="cursor:pointer">${t}</span>`).join(', ') : 'aucun'}</p>`).join('')) : ''}
    ${pn('Publications par société (les plus en retard d’abord)', 'BRVM', `<div class="tw" style="max-height:62vh"><table class="t"><thead><tr><th class="l">Titre</th><th class="l">Société</th>${PER.map(([k, y]) => `<th class="l">${k === 'A' ? 'Ex.' : k} ${y}</th>`).join('')}<th>Retards</th><th>Jours</th></tr></thead><tbody>
      ${rows.map(r => `<tr data-sec="${r.s.id}" data-to="CN"><td class="l tk">${r.s.id}</td><td class="l nm">${esc(r.s.short || r.s.n)}</td>${r.z.map(pubCell).join('')}<td class="${r.nm + r.nl ? 'am' : 'up'}">${r.nm + r.nl}</td><td>${r.late ? num(r.late, 0) : '—'}</td></tr>`).join('')}</tbody></table></div>`,
      { np: true, lect: '« Ex. » = exercice (comptes annuels) ; T1, S1, T3 = 1er trimestre, 1er semestre, 3e trimestre. Retards = périodes publiées après l’échéance ou sans document trouvé ; Jours = total des jours de retard. Astérisque : année absente de l’intitulé (déduite de la date de publication), ou intitulé portant l’année précédente pour une période déjà publiée (rattaché à la période suivante).' })}`;
}

async function brvmPays(m, alive) {
  setTitle('BRVM Country Exposure');
  const all = pubEq(), CN = Q.sum.cty || {}, G = {};
  for (const s of all) (G[s.cty || '—'] = G[s.cty || '—'] || []).push(s);
  const capT = all.reduce((t, s) => t + (s.mcap || 0), 0) || 1, liqT = all.reduce((t, s) => t + (s.liq || 0), 0) || 1;
  const wav = (a, f) => { let s = 0, w = 0; for (const x of a) { const v = f(x); if (v == null || !isFinite(v) || !x.mcap) continue; s += v * x.mcap; w += x.mcap; } return w ? s / w : null; };
  const R = Object.entries(G).map(([c, a]) => {
    const cap = a.reduce((t, s) => t + (s.mcap || 0), 0), fl = a.filter(s => s.mcap && s.float != null);
    const ben = a.filter(s => s.bnpa > 0 && s.shares && s.mcap), ni = ben.reduce((t, s) => t + s.bnpa * s.shares, 0), capNi = ben.reduce((t, s) => t + s.mcap, 0);
    const yl = a.filter(s => s.yld != null && s.mcap), capY = yl.reduce((t, s) => t + s.mcap, 0);
    return { c, n: CN[c] || c, a, cnt: a.length, cap, w: cap / capT, flo: fl.reduce((t, s) => t + s.mcap * s.float / 100, 0), floN: a.length - fl.length, liq: a.reduce((t, s) => t + (s.liq || 0), 0),
      pct: wav(a, s => s.pct), ytd: wav(a, s => s.ytd), r1y: wav(a, s => s.r1y), per: ni ? capNi / ni : null, yld: capY ? yl.reduce((t, s) => t + s.yld * s.mcap, 0) / capY : null };
  }).sort((a, b) => b.cap - a.cap);
  m.innerHTML = `<div class="grid c2">${pn('Poids des pays dans la capitalisation des actions', 'BRVM', cvb('pyW', 230), { lect: 'Pays du siège de la société cotée. Les groupes présents dans plusieurs pays (télécoms, banques) sont comptés dans leur pays de siège : la répartition de leurs activités par pays n’est pas publiée de façon homogène.' })}
    ${pn('Variation du jour par pays', 'BRVM', cvb('pyV', 230), { lect: 'Moyenne des variations du jour pondérée par les capitalisations.' })}</div>
    ${pn('Exposition par pays', 'BRVM', `<div class="tw"><table class="t"><thead><tr><th class="l">Pays</th><th>Sociétés</th><th>Capitalisation</th><th>Poids</th><th>Capi. flottante</th><th>Échangé par jour (3 mois)</th><th>Part des échanges</th><th>Jour</th><th>Depuis janv.</th><th>1 an</th><th>PER agrégé</th><th>Rdt agrégé</th></tr></thead><tbody>
      ${R.map(r => `<tr><td class="l am">${esc(r.n)}</td><td>${r.cnt}</td><td>${big(r.cap)}</td><td class="wh">${num(r.w * 100, 1)} %</td><td title="${r.floN ? r.floN + ' société(s) sans flottant officiel publié, non comptée(s)' : ''}">${big(r.flo)}${r.floN ? ' <span class="dm">*</span>' : ''}</td><td>${big(r.liq)}</td><td>${num(r.liq / liqT * 100, 1)} %</td><td>${pc(r.pct, 2)}</td><td>${pc(r.ytd, 1)}</td><td>${pc(r.r1y, 1)}</td><td>${r.per ? num(r.per, 1) + ' x' : '—'}</td><td>${r.yld != null ? num(r.yld * 100, 2) + ' %' : '—'}</td></tr>`).join('')}</tbody></table></div>`,
      { np: true, lect: 'Montants en FCFA. Capitalisation flottante = capitalisation × flottant officiel (* : une société sans flottant publié n’est pas comptée). PER agrégé = somme des capitalisations ÷ somme des résultats des sociétés bénéficiaires (dernier BNPA publié × nombre de titres). Rendement agrégé = moyenne des rendements pondérée par les capitalisations, sociétés dont le dernier dividende est récent. Variations pondérées par les capitalisations.' })}
    <div class="grid c2b">${R.map(r => pn(`${esc(r.n)} · ${r.cnt} société${r.cnt > 1 ? 's' : ''}`, 'BRVM', `<div class="tw"><table class="t"><tbody>${r.a.slice().sort((a, b) => (b.mcap || 0) - (a.mcap || 0)).map(s => `<tr data-sec="${s.id}" data-to="DES"><td class="l tk">${s.id}</td><td class="l nm">${esc(s.short || s.n)}</td><td class="l dm">${esc(s.grp || '')}</td><td>${big(s.mcap)}</td><td>${pc(s.pct, 1)}</td></tr>`).join('')}</tbody></table></div>`, { np: true })).join('')}</div>`;
  barChart($('pyW'), { labels: R.map(r => r.c), values: R.map(r => r.w * 100), fmt: v => num(v, 1) + ' %', padL: 52, pos: CL.amber, labelsOnBars: true, extra: i => `${esc(R[i].n)} · ${big(R[i].cap)}` });
  barChart($('pyV'), { labels: R.map(r => r.c), values: R.map(r => (r.pct || 0) * 100), fmt: v => (v > 0 ? '+' : '') + num(v, 2) + ' %', axisFmt: v => num(v, 1) + ' %', padL: 52, labelsOnBars: true, extra: i => esc(R[i].n) });
}

const PAGES_BRVM_BASE = PAGES.BRVM;
PAGES.BRVM = async (m, alive) => {
  const tab = tabState('BRVM', 'm');
  if (tab === 'r' || tab === 'a' || tab === 'x') {
    setTabs(FN_TABS.BRVM, tab, k => { ST.tab.BRVM = k; render(); });
    return tab === 'r' ? brvmSaison(m, alive) : tab === 'a' ? brvmAttendues(m, alive) : brvmPays(m, alive);
  }
  return PAGES_BRVM_BASE(m, alive);
};
