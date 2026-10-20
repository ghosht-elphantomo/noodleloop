/* ================= FQT — PORT : portefeuille personnel (positions, risque, performance, dividendes) =================
   Les positions sont saisies par l'utilisateur et enregistrées dans ce navigateur seulement (localStorage) ;
   tous les calculs partent des cours relevés et des dividendes publiés. */
'use strict';
const PORT_K = 'fqt_port_v1';
const portLoad = () => { try { const o = JSON.parse(localStorage.getItem(PORT_K) || 'null'); if (o && Array.isArray(o.pos)) return o; } catch (e) { /* stockage indisponible */ } return { base: 'XOF', pos: [] }; };
const portSave = P => { try { localStorage.setItem(PORT_K, JSON.stringify(P)); } catch (e) { /* stockage indisponible */ } };
const PORT_ST = { P: null };
const portP = () => PORT_ST.P || (PORT_ST.P = portLoad());

/* série quotidienne de la valeur du portefeuille (composition actuelle) et des indices de référence, convertis dans la devise de base */
async function portSeries(P, days = 400) {
  const ids = [...new Set(P.pos.map(p => p.id).concat(['BRVMC', 'QQQ']))].filter(id => Q.by[id]);
  const S = Object.fromEntries(await Promise.all(ids.map(async id => [id, await series(id).catch(() => null)])));
  const t0 = new Date(Date.now() - days * 864e5), i0 = t0.getUTCFullYear() * 10000 + (t0.getUTCMonth() + 1) * 100 + t0.getUTCDate();
  const xs = [...new Set(Object.values(S).filter(Boolean).flatMap(s => s.x.filter(d => d >= i0)))].sort((a, b) => a - b);
  const ff = s => { const out = []; let j = 0, lv = null; while (j < s.x.length && s.x[j] < xs[0]) { lv = s.c[j]; j++; } for (const d of xs) { while (j < s.x.length && s.x[j] <= d) { lv = s.c[j]; j++; } out.push(lv); } return out; };
  const C = {}; for (const id of ids) { if (!S[id]) continue; const f = await fxFactor(Q.by[id].ccy, P.base, xs).catch(() => null); C[id] = fxApply(ff(S[id]), f); }
  return { xs, C };
}
const rets = a => { const r = []; for (let i = 1; i < a.length; i++) r.push(a[i] != null && a[i - 1] ? a[i] / a[i - 1] - 1 : 0); return r; };
const covar = (a, b) => { const n = Math.min(a.length, b.length); if (n < 3) return null; const ma = U.mean(a.slice(-n)), mb = U.mean(b.slice(-n)); let s = 0; for (let i = 0; i < n; i++) s += (a[a.length - n + i] - ma) * (b[b.length - n + i] - mb); return s / (n - 1); };

PAGES.PORTF = async (m, alive) => {
  setTitle('Portfolio & Risk Analytics'); const P = portP();
  const tab = tabState('PORT', 'p'); setTabs([['p', 'Positions'], ['r', 'Risque'], ['h', 'Performance'], ['d', 'Dividendes']], tab, k => { ST.tab.PORT = k; render(); });
  setActs([{ n: 91, l: 'Exporter (CSV)', run: () => { const csv = 'titre;quantite;prix_de_revient\n' + P.pos.map(p => `${p.id};${p.q};${p.c ?? ''}`).join('\n'); const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = 'portefeuille.csv'; a.click(); } },
    { n: 92, l: 'Importer (coller)', run: () => { const b = $('ptImp'); if (b) b.hidden = !b.hidden; } }, { n: 93, l: 'Vider le portefeuille', run: () => { if (confirm('Supprimer toutes les positions de ce navigateur ?')) { P.pos = []; portSave(P); render(); } } }]);
  const W = await WMKT(); if (!alive()) return; const UF = W && W.fx ? fxUsd(W) : { USD: { now: 1, d: 1 } };
  const conv = (v, ccy, k = 'now') => { if (v == null) return null; if (ccy === P.base) return v; if (ccy === 'XOF' && P.base === 'EUR') return v / XOF_EUR; if (ccy === 'EUR' && P.base === 'XOF') return v * XOF_EUR; const a = UF[ccy], b = UF[P.base]; return a && b && a[k] && b[k] ? v * a[k] / b[k] : null; };
  const rows = P.pos.map(p => { const s = Q.by[p.id]; if (!s) return { p, s: null }; const v = conv(p.q * s.last, s.ccy), v0 = s.prev ? conv(p.q * s.prev, s.ccy, 'd') : null, cost = p.c ? conv(p.q * p.c, s.ccy) : null;
    return { p, s, v, dj: v != null && v0 != null ? v - v0 : null, cost, pl: v != null && cost != null ? v - cost : null, inc: s.dps && s.mkt === 'BRVM' && s.yld != null ? conv(p.q * s.dps, s.ccy) : s.yld ? conv(p.q * s.last * s.yld, s.ccy) : null }; });
  const ok = rows.filter(r => r.v != null), tot = ok.reduce((a, r) => a + r.v, 0), dj = ok.reduce((a, r) => a + (r.dj || 0), 0), cst = ok.filter(r => r.cost != null), pl = cst.reduce((a, r) => a + r.pl, 0), cb = cst.reduce((a, r) => a + r.cost, 0);
  const inc = ok.reduce((a, r) => a + (r.inc || 0), 0), cur = P.base, dec = cur === 'XOF' ? 0 : 2, mny = v => v == null ? '—' : num(v, dec), mnyS = v => v == null ? '—' : `<span class="${cls(v)}">${v > 0 ? '+' : ''}${num(v, dec)}</span>`;
  const head = `<div class="tools ttb"><span class="tlab">Devise de base</span><select class="ofld" id="ptB">${['XOF', 'USD', 'EUR'].map(c => `<option ${c === cur ? 'selected' : ''}>${c}</option>`).join('')}</select>
      <span class="tlab">Titre</span><input class="ofld" id="ptT" placeholder="SNTS, AAPL, QQQ…" autocomplete="off" style="width:150px"><span class="tlab">Quantité</span><input class="ofld" id="ptQ" style="width:90px"><span class="tlab">Prix de revient unitaire</span><input class="ofld" id="ptC" placeholder="facultatif" style="width:100px">
      <button class="tb on" id="ptA">Ajouter / mettre à jour</button><span class="gsp"></span><span class="dm">${P.pos.length} positions · enregistrées dans ce navigateur</span></div>
    <div id="ptImp" class="tools" hidden><textarea class="ofld" id="ptX" rows="4" style="width:420px;height:70px" placeholder="Une position par ligne : TITRE;QUANTITÉ;PRIX_DE_REVIENT&#10;SNTS;100;28000&#10;AAPL;10"></textarea><button class="tb" id="ptXo">Importer</button><span class="dm">Les titres déjà présents sont mis à jour.</span></div>`;
  const kv = `<div class="kv2"><span>Valeur du portefeuille</span><b class="wh">${mny(tot)} ${cur}</b><span>Résultat du jour</span><b>${mnyS(dj)} ${tot ? `(${pc(dj / (tot - dj))})` : ''}</b><span>Plus ou moins-value latente</span><b>${cst.length ? `${mnyS(pl)} (${pc(cb ? pl / cb : null)})` : '<span class="dm">indiquez les prix de revient</span>'}</b>
      <span>Revenu annuel de dividendes</span><b>${inc ? `${mny(inc)} ${cur}` : '—'}</b><span>Rendement du portefeuille</span><b>${tot && inc ? num(inc / tot * 100, 2) + ' %' : '—'}</b><span>Positions</span><b>${ok.length}${rows.length > ok.length ? ` <span class="dm">(${rows.length - ok.length} sans cours ou sans change)</span>` : ''}</b></div>`;
  const bind = () => {
    $('ptB').onchange = e => { P.base = e.target.value; portSave(P); render(); };
    const T = $('ptT'); T.oninput = () => { const L = searchSecs(T.value).slice(0, 10); if (!L.length) { ddClose(); return; } ddOpen(T, L.map(s => ({ code: s.id, l: esc(s.short || s.n), run: () => { T.value = s.id; $('ptQ').focus(); } }))); };
    const add = () => { const id = (Q.by[T.value.trim().toUpperCase()] || searchSecs(T.value)[0] || {}).id, q = parseFloat(String($('ptQ').value).replace(/\s/g, '').replace(',', '.')), c = parseFloat(String($('ptC').value).replace(/\s/g, '').replace(',', '.'));
      if (!id || !isFinite(q) || q <= 0) { T.focus(); return; } const ex = P.pos.find(x => x.id === id); if (ex) { ex.q = q; ex.c = isFinite(c) ? c : ex.c; } else P.pos.push({ id, q, c: isFinite(c) ? c : null }); portSave(P); render(); };
    $('ptA').onclick = add; [$('ptQ'), $('ptC')].forEach(x => x.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); add(); } });
    $('ptXo').onclick = () => { for (const ln of $('ptX').value.split(/\n/)) { const [t, q, c] = ln.split(/[;,\t]/).map(x => (x || '').trim()); const s = Q.by[(t || '').toUpperCase()] || (t ? searchSecs(t)[0] : null), qq = parseFloat(String(q || '').replace(',', '.')), cc = parseFloat(String(c || '').replace(',', '.'));
      if (!s || !(qq > 0)) continue; const ex = P.pos.find(x => x.id === s.id); if (ex) { ex.q = qq; if (isFinite(cc)) ex.c = cc; } else P.pos.push({ id: s.id, q: qq, c: isFinite(cc) ? cc : null }); } portSave(P); render(); };
    m.querySelectorAll('[data-pdel]').forEach(b => b.onclick = e => { e.stopPropagation(); P.pos = P.pos.filter(x => x.id !== b.dataset.pdel); portSave(P); render(); });
    m.querySelectorAll('[data-ped]').forEach(b => b.onclick = e => { e.stopPropagation(); const p = P.pos.find(x => x.id === b.dataset.ped); if (!p) return; T.value = p.id; $('ptQ').value = p.q; $('ptC').value = p.c ?? ''; $('ptQ').focus(); });
  };
  if (!P.pos.length) { m.innerHTML = head + pn('Portefeuille', 'PORTF', `<div class="empty">Aucune position. Saisissez un titre, une quantité et, si vous le souhaitez, votre prix de revient unitaire (dans la devise du titre), puis « Ajouter ». Vous pouvez aussi coller une liste avec 92) Importer.</div>`, { lect: 'Les positions restent dans ce navigateur : elles ne sont envoyées nulle part. Les valeurs, le risque et les dividendes sont calculés à partir des cours relevés toutes les 15 minutes.' }); bind(); return; }
  const grp = k => { const o = {}; for (const r of ok) { const g = k(r); o[g] = (o[g] || 0) + r.v; } return Object.entries(o).sort((a, b) => b[1] - a[1]); };
  const alloc = (title, L) => pn(title, 'PORTF', `<table class="t wcr"><tbody>${L.map(([g, v]) => `<tr><td class="l am">${esc(g)}</td><td class="wh">${num(v / tot * 100, 1)} %</td><td class="wcb" style="width:45%"><i class="p" style="left:0;width:${(v / tot * 100).toFixed(1)}%"></i></td></tr>`).join('')}</tbody></table>`, { np: true });
  /* fractionnements récents ou annoncés sur les titres détenus : quantité et prix de revient à ramener sur les actions nouvelles */
  const todayI = +new Date().toISOString().slice(0, 10).replace(/-/g, ''), i2 = d => +new Date(Date.now() + d * 864e5).toISOString().slice(0, 10).replace(/-/g, '');
  const SPW = P.pos.flatMap(p => ((Q.by[p.id] || {}).split || []).filter(([e]) => e >= i2(-60) && e <= i2(60) && !(p.sp || []).includes(e)).map(([e, k]) => ({ p, e, k })));
  const spBan = SPW.map(x => `<div class="spb"><b>${esc(x.p.id)}</b> : fractionnement ${num(x.k, 0)} actions nouvelles pour 1 ancienne, effectif le ${fd(x.e)}. ${x.e <= todayI ? `Les cours sont désormais sur la base des actions nouvelles : votre quantité devient ${num(x.p.q * x.k, 0)} et votre prix de revient ${x.p.c ? num(x.p.c / x.k, 2) : '—'}. <button class="tb on" data-spl="${esc(x.p.id)}" data-e="${x.e}" data-k="${x.k}">Ajuster ma position et mes alertes</button>` : 'À cette date, il faudra multiplier la quantité et diviser le prix de revient par ce rapport ; un bouton apparaîtra ici.'}</div>`).join('');
  const bindSp = () => m.querySelectorAll('[data-spl]').forEach(b => b.onclick = () => { const p = P.pos.find(x => x.id === b.dataset.spl), k = +b.dataset.k, e = +b.dataset.e; if (!p) return; p.q = p.q * k; if (p.c) p.c = p.c / k; p.sp = (p.sp || []).concat(e); portSave(P);
    const A = maLoad(); A.forEach(a => { if (a.id === p.id && (a.k === 'pxu' || a.k === 'pxd') && a.v) a.v = a.v / k; }); maSave(A); render(); });
  if (tab === 'p') {
    const L = rows.slice().sort((a, b) => (b.v || 0) - (a.v || 0));
    m.innerHTML = head + spBan + `<div class="grid side">${pn(`Positions · valeurs en ${cur}`, 'PORTF', `<div class="tw"><table class="t"><thead><tr><th class="l">Titre</th><th class="l">Nom</th><th>Quantité</th><th>Prix de revient</th><th>Cours</th><th>Var. jour</th><th>Valeur (${cur})</th><th>Poids</th><th>Résultat jour</th><th>+/− latente</th><th>%</th><th>Rdt div.</th><th></th></tr></thead><tbody>
        ${L.map((r, i) => { const s = r.s; if (!s) return `<tr><td class="l"><span class="rn">${i + 1})</span>${esc(r.p.id)}</td><td class="l dm" colspan="11">titre introuvable dans la base</td><td><span class="pdx" data-pdel="${esc(r.p.id)}">✕</span></td></tr>`;
          return `<tr data-sec="${s.id}" data-to="DES" style="cursor:pointer"><td class="l"><span class="rn">${i + 1})</span><b class="wh">${s.id}</b></td><td class="l am">${esc(s.short || s.n)}</td><td>${num(r.p.q, r.p.q % 1 ? 2 : 0)}</td><td>${r.p.c ? px(s, r.p.c) : '<span class="dm">—</span>'}</td><td class="wh">${px(s, s.last)} <span class="dm">${s.ccy}</span></td><td>${pc(s.pct)}</td>
            <td class="wh">${mny(r.v)}</td><td>${r.v != null && tot ? num(r.v / tot * 100, 1) + ' %' : '—'}</td><td>${mnyS(r.dj)}</td><td>${r.pl != null ? mnyS(r.pl) : '—'}</td><td>${r.pl != null && r.cost ? pc(r.pl / r.cost) : '—'}</td><td>${s.yld ? num(s.yld * 100, 2) + ' %' : '—'}</td>
            <td class="l"><span class="pdx" data-ped="${s.id}" title="modifier">✎</span> <span class="pdx" data-pdel="${s.id}" title="supprimer">✕</span></td></tr>`; }).join('')}
        <tr class="sep2"><td class="l wh" colspan="6">Total</td><td class="wh">${mny(tot)}</td><td>100 %</td><td>${mnyS(dj)}</td><td>${cst.length ? mnyS(pl) : '—'}</td><td>${cb ? pc(pl / cb) : '—'}</td><td>${tot && inc ? num(inc / tot * 100, 2) + ' %' : '—'}</td><td></td></tr></tbody></table></div>`,
        { np: true, lect: `Valeurs converties en ${cur} au cours de change du dernier relevé (franc CFA : parité fixe avec l’euro). Prix de revient saisi dans la devise du titre et converti au change du jour comme la valeur : la plus-value latente ne compte donc pas l’effet de change depuis l’achat. Rendement du dividende : dernier dividende publié ÷ cours (BRVM, net) ou rendement indicatif (US). Clic sur une ligne : fiche du titre.` })}
      <div>${pn('Synthèse', 'PORTF', kv)}${alloc('Répartition par secteur', grp(r => r.s.grp || 'Autres'))}${alloc('Répartition par marché et devise', grp(r => `${r.s.mkt === 'BRVM' ? 'BRVM' : r.s.mkt === 'US' ? 'États-Unis' : r.s.mkt || 'Autre'} · ${r.s.ccy}`))}</div></div>`;
    bind(); bindSp(); return;
  }
  m.innerHTML = head + `<div class="empty" id="ptW">Calcul sur les cours quotidiens du dernier an…</div>`; bind();
  const D = await portSeries(P); if (!alive()) return;
  const live = ok.filter(r => D.C[r.p.id]), n = D.xs.length;
  const V = D.xs.map((_, t) => { let s = 0; for (const r of live) { const c = D.C[r.p.id][t]; if (c == null) return null; s += r.p.q * c; } return s; });
  const k0 = V.findIndex(v => v != null), Vx = V.slice(k0), X = D.xs.slice(k0), rp = rets(Vx).slice(-252);
  const RB = D.C.BRVMC ? rets(D.C.BRVMC.slice(k0)).slice(-252) : null, RQ = D.C.QQQ ? rets(D.C.QQQ.slice(k0)).slice(-252) : null;
  if (tab === 'r') {
    const sd = U.std(rp), srt = rp.slice().sort((a, b) => a - b), q5 = U.q(srt, .05), tail = srt.filter(x => x <= q5), cvar = tail.length ? U.mean(tail) : null, Vn = Vx[Vx.length - 1];
    let pk = -Infinity, mdd = 0; for (const v of Vx) { if (v == null) continue; pk = Math.max(pk, v); mdd = Math.min(mdd, v / pk - 1); }
    const beta = R => R && U.std(R) ? covar(rp, R) / (U.std(R) ** 2) : null, corr = R => R && U.std(R) && sd ? covar(rp, R) / (U.std(R) * sd) : null;
    const A = live.map(r => ({ r, x: rets(D.C[r.p.id].slice(k0)).slice(-252), w: r.v / live.reduce((a, z) => a + z.v, 0) }));
    const Sg = A.map(a => A.map(b => covar(a.x, b.x) || 0)), vp = A.reduce((s, a, i) => s + A.reduce((t, b, j) => t + a.w * b.w * Sg[i][j], 0), 0);
    const rc = A.map((a, i) => ({ a, c: vp > 0 ? a.w * A.reduce((t, b, j) => t + b.w * Sg[i][j], 0) / vp : null, vol: Math.sqrt(Sg[i][i] * 252) }));
    const wavgVol = A.reduce((s, a) => s + a.w * Math.sqrt(Sg[A.indexOf(a)][A.indexOf(a)]), 0), dr = Math.sqrt(vp) ? wavgVol / Math.sqrt(vp) : null;
    const cm = A.length <= 14 ? `<table class="t"><thead><tr><th class="l"></th>${A.map(a => `<th>${a.r.s.id}</th>`).join('')}</tr></thead><tbody>${A.map((a, i) => `<tr><td class="l am">${a.r.s.id}</td>${A.map((b, j) => { const c = Sg[i][j] / Math.sqrt(Sg[i][i] * Sg[j][j] || 1); return `<td style="background:${i === j ? '#141414' : c > 0 ? `rgba(255,67,61,${Math.min(.75, Math.abs(c)).toFixed(2)})` : `rgba(50,120,255,${Math.min(.75, Math.abs(c)).toFixed(2)})`}">${i === j ? '—' : num(c, 2)}</td>`; }).join('')}</tr>`).join('')}</tbody></table>` : '<div class="dm" style="padding:6px">Matrice affichée jusqu’à 14 positions.</div>';
    m.innerHTML = head + `<div class="grid c3">${pn('Risque du portefeuille (1 an, quotidien)', 'PORTF', `<div class="kv2"><span>Volatilité annualisée</span><b class="wh">${num(sd * Math.sqrt(252) * 100, 1)} %</b><span>VaR 95 % sur 1 jour (historique)</span><b class="dn">${num(-q5 * 100, 2)} % · ${mny(-q5 * Vn)} ${cur}</b><span>VaR 95 % sur 10 jours (√10)</span><b class="dn">${mny(-q5 * Math.sqrt(10) * Vn)} ${cur}</b><span>Perte moyenne au-delà de la VaR (CVaR)</span><b class="dn">${cvar != null ? num(-cvar * 100, 2) + ' %' : '—'}</b>
          <span>Baisse maximale sur la période</span><b class="dn">${num(mdd * 100, 1)} %</b><span>Bêta contre BRVM Composite</span><b>${beta(RB) != null ? num(beta(RB), 2) : '—'}</b><span>Bêta contre QQQ (Nasdaq-100)</span><b>${beta(RQ) != null ? num(beta(RQ), 2) : '—'}</b><span>Corrélation BRVM / QQQ</span><b>${corr(RB) != null ? num(corr(RB), 2) : '—'} / ${corr(RQ) != null ? num(corr(RQ), 2) : '—'}</b><span>Ratio de diversification</span><b>${dr ? num(dr, 2) : '—'}</b><span>Observations</span><b>${rp.length} séances</b></div>`, { lect: `Calculé sur la composition actuelle et les cours quotidiens convertis en ${cur}. VaR historique : 5e centile des variations quotidiennes. Ratio de diversification : volatilité moyenne pondérée des titres ÷ volatilité du portefeuille (1 = aucune diversification).` })}
        ${pn('Contribution au risque', 'PORTF', `<table class="t wcr"><thead><tr><th class="l">Titre</th><th>Poids</th><th>Volatilité</th><th>Part du risque</th><th class="c"></th></tr></thead><tbody>${rc.sort((a, b) => (b.c || 0) - (a.c || 0)).map(x => `<tr><td class="l"><b class="wh">${x.a.r.s.id}</b></td><td>${num(x.a.w * 100, 1)} %</td><td>${num(x.vol * 100, 1)} %</td><td class="${x.c > x.a.w * 1.25 ? 'dn' : 'wh'}">${x.c != null ? num(x.c * 100, 1) + ' %' : '—'}</td><td class="wcb" style="width:30%"><i class="${x.c >= 0 ? 'p' : 'n'}" style="left:0;right:auto;width:${Math.min(100, Math.abs(x.c || 0) * 100).toFixed(1)}%"></i></td></tr>`).join('')}</tbody></table>`, { np: true, lect: 'Part du risque : contribution de chaque titre à la variance du portefeuille. En rouge : titre qui pèse nettement plus dans le risque que dans le capital.' })}
        ${pn('Corrélations entre positions', 'PORTF', `<div class="tw">${cm}</div>`, { np: true, lect: 'Rouge : les titres évoluent ensemble ; bleu : en sens contraire. Variations quotidiennes sur un an, dans la devise de base.' })}</div>`;
    bind(); return;
  }
  if (tab === 'h') {
    const norm = a => { const b = a.slice(k0); const f = b.find(v => v != null); return b.map(v => v != null && f ? v / f * 100 : null); };
    const perf = (a, days) => { const b = a.slice(k0), t = new Date(Date.now() - days * 864e5), ti = t.getUTCFullYear() * 10000 + (t.getUTCMonth() + 1) * 100 + t.getUTCDate(); let j = X.findIndex(d => d >= ti); if (j < 0) return null; const e = b[b.length - 1]; return b[j] && e ? e / b[j] - 1 : null; };
    const ytd = a => { const b = a.slice(k0), y = Math.floor(X[X.length - 1] / 10000); let j = X.findIndex(d => Math.floor(d / 10000) === y); if (j <= 0) return null; return b[j - 1] ? b[b.length - 1] / b[j - 1] - 1 : null; };
    const PER = [['1 sem.', 7], ['1 mois', 30], ['3 mois', 91], ['6 mois', 182], ['1 an', 365]], L = [['Portefeuille', V], ['BRVM Composite', D.C.BRVMC], ['QQQ', D.C.QQQ]].filter(x => x[1]);
    m.innerHTML = head + `${pn(`Performance de la composition actuelle (base 100, en ${cur})`, 'PORTF', cvb('ptG', 330), { np: true })}
      ${pn('Rendements par période', 'PORTF', `<table class="t"><thead><tr><th class="l"></th>${PER.map(p => `<th>${p[0]}</th>`).join('')}<th>Depuis janv.</th></tr></thead><tbody>${L.map(([l, a]) => `<tr><td class="l am">${l}</td>${PER.map(p => `<td>${pc(perf(a, p[1]))}</td>`).join('')}<td>${pc(ytd(a))}</td></tr>`).join('')}</tbody></table>`, { np: true, lect: `Simulation : valeur qu’auraient eue les quantités actuelles sur la période, dividendes non compris, en ${cur}. Ce n’est pas la performance réelle de vos achats successifs.` })}`;
    new TSChart($('ptG'), { panes: [{ h: 1, fmt: v => num(v, 0) }], grid: 'dot', xticks: bbgTicks }).set({ x: X, series: [{ y: norm(V), color: '#f9a33a', w: 2, label: 'Portefeuille', fmt: v => num(v, 1) }].concat(D.C.BRVMC ? [{ y: norm(D.C.BRVMC), color: '#5fd0ea', w: 1.3, label: 'BRVM Composite', fmt: v => num(v, 1) }] : [], D.C.QQQ ? [{ y: norm(D.C.QQQ), color: '#e6e6e6', w: 1.3, label: 'QQQ', fmt: v => num(v, 1) }] : []) }, [0, X.length - 1]);
    bind(); return;
  }
  /* dividendes */
  const DV = await getJSON('dividends.json').catch(() => []); if (!alive()) return; const today = new Date().toISOString().slice(0, 10);
  const up = (Array.isArray(DV) ? DV : []).filter(x => P.pos.some(p => p.id === x.t) && x.dps && ((x.det && x.det >= today) || (x.pay && x.pay >= today))).sort((a, b) => String(a.det || a.pay).localeCompare(String(b.det || b.pay)));
  m.innerHTML = head + `<div class="grid c2b">${pn(`Revenu annuel de dividendes estimé · ${mny(inc)} ${cur}`, 'PORTF', `<table class="t"><thead><tr><th class="l">Titre</th><th>Quantité</th><th>Dernier dividende / titre</th><th>Exercice</th><th>Revenu (${cur})</th><th>Rendement</th><th>Part du revenu</th></tr></thead><tbody>${ok.slice().sort((a, b) => (b.inc || 0) - (a.inc || 0)).map(r => `<tr><td class="l"><b class="wh">${r.s.id}</b> <span class="am">${esc(r.s.short || r.s.n)}</span></td><td>${num(r.p.q, 0)}</td><td>${r.s.mkt === 'BRVM' && r.s.dps ? px(r.s, r.s.dps) + ' ' + r.s.ccy : r.s.yld ? 'rendement ' + num(r.s.yld * 100, 2) + ' %' : '—'}</td><td class="dm">${r.s.dps_ex || '—'}</td><td class="wh">${r.inc ? mny(r.inc) : '—'}</td><td>${r.s.yld ? num(r.s.yld * 100, 2) + ' %' : '—'}</td><td>${r.inc && inc ? num(r.inc / inc * 100, 1) + ' %' : '—'}</td></tr>`).join('')}</tbody></table>`, { np: true, lect: 'Estimation à dividende inchangé : dernier dividende net publié (BRVM) ou rendement indicatif (US) × quantité détenue. Le dividende futur peut être différent.' })}
    ${pn('Prochains détachements et paiements de vos titres', 'DIVC', up.length ? `<table class="t"><thead><tr><th class="l">Titre</th><th>Dividende</th><th>Détachement</th><th>Paiement</th><th>Montant pour vous</th></tr></thead><tbody>${up.map(x => { const p = P.pos.find(q => q.id === x.t), s = Q.by[x.t]; return `<tr><td class="l wh">${esc(x.t)}</td><td>${num(x.dps, 2)}</td><td>${x.det ? fds(x.det) : '—'}</td><td>${x.pay ? fds(x.pay) : '—'}</td><td class="wh">${s ? mny(conv(p.q * x.dps, s.ccy)) + ' ' + cur : '—'}</td></tr>`; }).join('')}</tbody></table>` : '<div class="empty">Aucun détachement annoncé pour vos titres.</div>', { np: true })}</div>`;
  bind();
};

/* ------------------------------------------------------------------ TECH : analyse technique (tendance, oscillateurs, volatilité, niveaux) —
   indicateurs calculés sur les cours quotidiens publiés ; signaux descriptifs, pas une recommandation */
PAGES.TECH = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Technical Analysis'); const S = await series(s.id).catch(() => null); if (!alive()) return;
  if (!S || S.c.length < 60 || s.f !== 'D') { m.innerHTML = pn('Analyse technique', 'TECH', '<div class="empty">Historique quotidien insuffisant pour ce titre.</div>'); return; }
  const c = S.c, h = S.h, l = S.l, n = c.length, L = n - 1, last = c[L], P = v => px(s, v);
  const sm = k => U.sma(c, k), M20 = sm(20), M50 = sm(50), M100 = sm(100), M200 = sm(200), R = U.rsi(c, 14);
  const e12 = U.ema(c, 12), e26 = U.ema(c, 26), macd = c.map((_, i) => e12[i] - e26[i]), sig = U.ema(macd.map(v => isFinite(v) ? v : NaN), 9, 26), hist = macd.map((v, i) => v - sig[i]);
  const sd20 = (() => { const o = new Float64Array(n).fill(NaN); for (let i = 19; i < n; i++) { let a = 0, b = 0; for (let j = i - 19; j <= i; j++) { a += c[j]; b += c[j] * c[j]; } const mm = a / 20; o[i] = Math.sqrt(Math.max(0, b / 20 - mm * mm)); } return o; })();
  const bu = M20.map((v, i) => v + 2 * sd20[i]), bl = M20.map((v, i) => v - 2 * sd20[i]), pB = (last - bl[L]) / (bu[L] - bl[L]);
  const tr = c.map((v, i) => i ? Math.max(h[i] - l[i], Math.abs(h[i] - c[i - 1]), Math.abs(l[i] - c[i - 1])) : h[i] - l[i]), atr = U.mean(tr.slice(-14));
  const hh14 = Math.max(...h.slice(-14)), ll14 = Math.min(...l.slice(-14)), stK = hh14 > ll14 ? (last - ll14) / (hh14 - ll14) * 100 : null;
  const kS = []; for (let i = L - 2; i <= L; i++) { const H = Math.max(...h.slice(i - 13, i + 1)), Lo = Math.min(...l.slice(i - 13, i + 1)); kS.push(H > Lo ? (c[i] - Lo) / (H - Lo) * 100 : null); } const stD = kS.every(v => v != null) ? U.mean(kS) : null;
  /* variations sur 1, 3, 6 et 12 mois calendaires (même règle que le résumé : dernière séance à la date de départ ou avant) */
  const roc = k => { const i = baseIdx(S.x, backMonths(S.x[L], k)); return i >= 0 && c[i] ? last / c[i] - 1 : null; };
  const lr = c.slice(-61).map((v, i, a) => i ? Math.log(v / a[i - 1]) : 0).slice(1), vol20 = U.std(lr.slice(-20)) * Math.sqrt(252), vol60 = U.std(lr) * Math.sqrt(252);
  const cross = (a, b) => { for (let i = L; i > Math.max(1, L - 750); i--) if (isFinite(a[i]) && isFinite(b[i]) && isFinite(a[i - 1]) && isFinite(b[i - 1]) && Math.sign(a[i] - b[i]) !== Math.sign(a[i - 1] - b[i - 1])) return { i, up: a[i] > b[i] }; return null; };
  const gx = cross(M50, M200), mx = cross(macd, sig);
  const k52 = Math.max(0, idxAtOrBefore(S.x, backMonths(S.x[L], 12)) + 1), hi52 = Math.max(...h.slice(k52)), lo52 = Math.min(...l.slice(k52)), hi20 = Math.max(...h.slice(-20)), lo20 = Math.min(...l.slice(-20));
  /* pivots classiques sur la dernière séance close */
  /* pivots hebdomadaires : plus haut, plus bas et clôture des 5 dernières séances (plus parlants que la seule veille sur les titres peu échangés) */
  const hW = Math.max(...h.slice(-5)), lW = Math.min(...l.slice(-5)), PP = (hW + lW + last) / 3, R1 = 2 * PP - lW, S1 = 2 * PP - hW, R2 = PP + (hW - lW), S2 = PP - (hW - lW);
  const sigs = [['Cours au-dessus de la MM 200', last > M200[L]], ['MM 50 au-dessus de la MM 200', M50[L] > M200[L]], ['Cours au-dessus de la MM 50', last > M50[L]], ['MACD au-dessus de son signal', macd[L] > sig[L]], ['RSI au-dessus de 50', R[L] > 50], ['Rendement 3 mois positif', roc(3) == null ? null : roc(3) > 0], ['Rendement 12 mois positif', roc(12) == null ? null : roc(12) > 0]].filter(x => x[1] != null && (typeof x[1] === 'boolean'));
  const nUp = sigs.filter(x => x[1]).length;
  const row = (a, b, c2 = '') => `<tr><td class="l am">${a}</td><td class="wh">${b}</td><td class="l">${c2}</td></tr>`, yn = (v, a, b) => v ? `<span class="up">${a}</span>` : `<span class="dn">${b}</span>`, dd = i => fd(S.x[i]);
  const ecart = v => isFinite(v) ? pc(last / v - 1) : '—';
  m.innerHTML = `<div class="grid c4 tch">${pn('1) Tendance', 'TECH', `<table class="t"><tbody>${row('Cours', P(last) + ' ' + esc(s.ccy), fd(S.x[L]))}${[['MM 20', M20], ['MM 50', M50], ['MM 100', M100], ['MM 200', M200]].map(([a, A]) => row(a, isFinite(A[L]) ? P(A[L]) : '—', isFinite(A[L]) ? `${ecart(A[L])} ${yn(last > A[L], '▲', '▼')}` : '')).join('')}
        ${row('Croisement MM 50 / MM 200', gx ? (gx.up ? '<span class="up">haussier</span>' : '<span class="dn">baissier</span>') : '—', gx ? 'le ' + dd(gx.i) : 'aucun sur 3 ans')}</tbody></table>`, { np: true })}
    ${pn('2) Oscillateurs', 'TECH', `<table class="t"><tbody>${row('RSI 14', num(R[L], 1), R[L] > 70 ? '<span class="dn">surachat (> 70)</span>' : R[L] < 30 ? '<span class="up">survente (< 30)</span>' : 'zone neutre')}${row('MACD (12, 26)', num(macd[L], 3), `signal ${num(sig[L], 3)}`)}${row('Histogramme MACD', `<span class="${cls(hist[L])}">${num(hist[L], 3)}</span>`, mx ? `${mx.up ? '<span class="up">▲</span>' : '<span class="dn">▼</span>'} ${dd(mx.i).slice(0, 5)}` : '')}
        ${row('Stochastique %K / %D (14, 3)', stK != null ? `${num(stK, 1)} / ${stD != null ? num(stD, 1) : '—'}` : '—', stK > 80 ? 'zone haute' : stK < 20 ? 'zone basse' : '')}${row('Williams %R (14)', stK != null ? num(stK - 100, 1) : '—', '')}
        ${[['1 mois', 1], ['3 mois', 3], ['6 mois', 6], ['12 mois', 12]].map(([a, d]) => row('Variation ' + a, pc(roc(d)), '')).join('')}</tbody></table>`, { np: true })}
    ${pn('3) Volatilité', 'TECH', `<table class="t"><tbody>${row('ATR 14 séances', P(atr), num(atr / last * 100, 2) + ' %')}${row('Bandes de Bollinger (20, 2)', `${P(bl[L])} – ${P(bu[L])}`, `l. ${num((bu[L] - bl[L]) / M20[L] * 100, 1)} %`)}${row('Position dans les bandes (%B)', num(pB * 100, 0) + ' %', pB > 1 ? 'au-dessus de la bande haute' : pB < 0 ? 'sous la bande basse' : '')}
        ${row('Volatilité 20 séances (ann.)', num(vol20 * 100, 1) + ' %', '')}${row('Volatilité 60 séances (ann.)', num(vol60 * 100, 1) + ' %', '')}${row('Position sur 52 semaines', num((last - lo52) / (hi52 - lo52) * 100, 0) + ' %', '')}</tbody></table>`, { np: true })}
    ${pn('4) Niveaux', 'TECH', `<table class="t"><tbody>${row('Résistance 2 (R2)', P(R2), ecart(R2))}${row('Résistance 1 (R1)', P(R1), ecart(R1))}${row('Pivot', P(PP), ecart(PP))}${row('Support 1 (S1)', P(S1), ecart(S1))}${row('Support 2 (S2)', P(S2), ecart(S2))}${row('Plus haut / bas 20 séances', `${P(hi20)} / ${P(lo20)}`, '')}${row('Plus haut / bas 52 semaines', `${P(hi52)} / ${P(lo52)}`, '')}</tbody></table>`, { np: true, lect: `Pivots hebdomadaires : plus haut, plus bas et dernier cours des 5 séances jusqu’au ${fd(S.x[L])}.` })}</div>
    <div class="grid side">${pn(`${esc(ykey(s))} · cours, MM 50 / MM 200, Bollinger ; RSI ; MACD (1 an)`, 'TECH', cvb('teG', 420), { np: true })}
      ${pn(`Synthèse : ${nUp} ${nUp > 1 ? 'signaux haussiers' : 'signal haussier'} sur ${sigs.length}`, 'TECH', `<table class="t"><tbody>${sigs.map(([a, v]) => `<tr><td class="l am">${a}</td><td>${v ? '<span class="up">oui</span>' : '<span class="dn">non</span>'}</td></tr>`).join('')}</tbody></table><div class="tsc"><i style="width:${(nUp / sigs.length * 100).toFixed(0)}%"></i></div>`, { np: true, lect: 'Lecture descriptive de la tendance à partir des cours publiés : ce n’est pas une recommandation d’achat ou de vente. Sur les titres peu échangés, plus haut et plus bas égalent souvent la clôture : ATR et stochastique sont alors moins parlants.' })}</div>`;
  const k0 = Math.max(0, n - 260), sl = a => Array.from(a).slice(k0).map(v => isFinite(v) ? v : null);
  new TSChart($('teG'), { panes: [{ h: 2.2 }, { h: .8, fixed: [0, 100], refs: [{ v: 70, color: CL.dn }, { v: 30, color: CL.up }], title: 'RSI 14' }, { h: .9, title: 'MACD' }], grid: 'dot', xticks: bbgTicks })
    .set({ x: S.x.slice(k0), series: [{ y: sl(c), color: '#ffffff', w: 1.4, label: s.id, fmt: v => P(v) }, { y: sl(M50), color: '#f9a33a', w: 1.1, label: 'MM 50', fmt: v => P(v) }, { y: sl(M200), color: '#ff3d4d', w: 1.1, label: 'MM 200', fmt: v => P(v) },
      { y: sl(bu), color: 'rgba(95,208,234,.55)', w: 1, label: 'Bollinger haute', fmt: v => P(v) }, { y: sl(bl), color: 'rgba(95,208,234,.55)', w: 1, label: 'Bollinger basse', fmt: v => P(v) },
      { pane: 1, y: sl(R), color: '#b69cff', w: 1.2, label: 'RSI', fmt: v => num(v, 1) }, { pane: 2, type: 'bar', y: sl(hist), colorFn: v => v >= 0 ? CL.up : CL.dn, label: 'Histogramme', fmt: v => num(v, 3) }, { pane: 2, y: sl(macd), color: '#5fd0ea', w: 1.1, label: 'MACD', fmt: v => num(v, 3) }, { pane: 2, y: sl(sig), color: '#f9a33a', w: 1, label: 'Signal', fmt: v => num(v, 3) }] }, [0, n - 1 - k0]);
};

/* ------------------------------------------------------------------ EA : écran « Earnings Analysis » — publications de résultats à venir
   (date, moment, consensus du trimestre) et publiées (BPA réel contre consensus, surprise, réaction du cours) ; actions US suivies */
PAGES['CORP RESULT'] = async (m, alive) => {
  setTitle('Earnings Analysis'); const E = await getJSON('ee.json').catch(() => null); if (!alive()) return;
  if (!E) { m.innerHTML = pn('Résultats', 'CORP RESULT', '<div class="empty">Estimations en attente du relevé du soir.</div>'); return; }
  const tab = tabState('CORP RESULT', 'u'); setTabs(FN_TABS['CORP RESULT'], tab, k => { ST.tab['CORP RESULT'] = k; render(); });
  if (tab === 't') return cfView(m, alive, 'u', 'CORP RESULT');
  const us = t => { const x = String(t || '').match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/); return x ? `${x[3]}-${x[1].padStart(2, '0')}-${x[2].padStart(2, '0')}` : null; };
  const today = new Date().toISOString().slice(0, 10), wd = d => new Date(d + 'T12:00:00Z').toLocaleDateString('fr-FR', { weekday: 'short', day: '2-digit', month: '2-digit', timeZone: 'UTC' });
  const st = ST.ea = ST.ea || { q: '' };
  if (tab === 'u') {
    const L = Object.entries(E).map(([id, x]) => { const d = us(x.ed), s = Q.by[id]; if (!d || d < today || !s) return null; const q0 = (x.qr || [])[0] || {}, sur = (x.sur || []).slice().sort((a, b) => (us(b.d) || '').localeCompare(us(a.d) || ''))[0];
      return { id, s, d, when: /after market/i.test(x.ed) ? 'après clôture' : /before market/i.test(x.ed) ? 'avant ouverture' : '—', est: /estimated|algorithm/i.test(x.ed), q: q0.fiscalEnd, eps: q0.consensusEPSForecast, hi: q0.highEPSForecast, lo: q0.lowEPSForecast, nb: q0.noOfEstimates, last: sur }; }).filter(Boolean)
      .filter(r => !st.q || (r.id + ' ' + r.s.n).toLowerCase().includes(st.q.toLowerCase())).sort((a, b) => a.d.localeCompare(b.d) || (b.s.mcap || 0) - (a.s.mcap || 0));
    let cur = '', k = 0; const rows = L.map(r => { const hd = r.d !== cur ? `<tr class="grp"><td class="l" colspan="11">${wd(r.d)}${r.d === today ? ' · aujourd’hui' : ''}</td></tr>` : ''; cur = r.d;
      return hd + `<tr data-sec="${r.id}" data-to="EE" style="cursor:pointer"><td class="l"><span class="rn">${++k})</span><b class="wh">${r.id}</b></td><td class="l am">${esc(r.s.short || r.s.n)}</td><td class="l">${r.when}${r.est ? ' <i class="qd" title="date estimée d’après l’historique de publication">e</i>' : ''}</td><td class="l dm">${esc(r.q || '')}</td><td class="wh">${r.eps != null ? num(r.eps, 2) : '—'}</td><td class="dm">${r.lo != null ? num(r.lo, 2) + ' – ' + num(r.hi, 2) : '—'}</td><td>${r.nb ?? '—'}</td><td>${r.last ? `<span class="${cls(r.last.pct)}">${r.last.pct > 0 ? '+' : ''}${num(r.last.pct, 1)} %</span>` : '—'}</td><td class="wh">${px(r.s, r.s.last)}</td><td>${pc(r.s.pct)}</td><td>${big(r.s.mcap)}</td></tr>`; }).join('');
    m.innerHTML = `<div class="tools ttb"><span class="tnar"><input id="eaQ" class="ofld" value="${esc(st.q)}" placeholder="&lt;Filtrer&gt;"></span><span class="dm">${L.length} publications à venir · actions US suivies</span><span class="gsp"></span><span class="dm">e = date estimée</span></div>
      ${pn('Publications de résultats à venir', 'CORP RESULT', `<div class="tw" style="max-height:calc(100vh - 250px - var(--nwh, 90px))"><table class="t"><thead><tr><th class="l">Titre</th><th class="l">Société</th><th class="l">Moment</th><th class="l">Trimestre</th><th>BPA consensus</th><th>Fourchette</th><th>Analystes</th><th>Dernière surprise</th><th>Cours</th><th>Var. jour</th><th>Capi. ($)</th></tr></thead><tbody>${rows || '<tr><td class="l dm" colspan="11">Aucune publication annoncée.</td></tr>'}</tbody></table></div>`,
        { np: true, lect: 'Dates et consensus du bénéfice par action (BPA) publiés pour le trimestre en cours ; « Dernière surprise » = BPA publié au trimestre précédent contre le consensus d’alors. Clic : estimations du titre (EE). Aucun consensus public pour la BRVM.' })}`;
  } else {
    const t60 = new Date(Date.now() - 60 * 864e5).toISOString().slice(0, 10);
    const L = Object.entries(E).flatMap(([id, x]) => (x.sur || []).map(su => ({ id, s: Q.by[id], d: us(su.d), q: su.q, eps: su.eps, cons: su.cons, pct: su.pct }))).filter(r => r.s && r.d && r.d >= t60 && r.d <= today).sort((a, b) => b.d.localeCompare(a.d));
    m.innerHTML = `<div class="empty">Calcul des réactions de cours…</div>`;
    const react = await Promise.all(L.map(async r => { const S = await series(r.id).catch(() => null); if (!S) return null; const di = +r.d.replace(/-/g, ''); let i = S.x.findIndex(x => x >= di); if (i < 1) return null; const j = Math.min(S.x.length - 1, i + 1); return j > i - 1 ? S.c[j] / S.c[i - 1] - 1 : null; })); if (!alive()) return;
    const beat = L.filter(r => r.pct > 0).length, avg = L.length ? U.mean(L.map(r => r.pct || 0)) : null;
    m.innerHTML = `<div class="tools ttb"><span class="tlab">Publications</span><b class="wh">${L.length}</b><span class="tlab">Au-dessus du consensus</span><b class="up">${beat}</b><span class="dm">(${L.length ? num(beat / L.length * 100, 0) : '—'} %)</span><span class="tlab">Surprise moyenne</span><b class="${cls(avg)}">${avg != null ? num(avg, 1) + ' %' : '—'}</b></div>
      ${pn('Résultats publiés depuis 60 jours', 'CORP RESULT', `<div class="tw" style="max-height:calc(100vh - 250px - var(--nwh, 90px))"><table class="t"><thead><tr><th class="l">Date</th><th class="l">Titre</th><th class="l">Société</th><th class="l">Trimestre</th><th>BPA publié</th><th>Consensus</th><th>Surprise</th><th class="c"></th><th>Réaction (2 séances)</th></tr></thead><tbody>${L.map((r, i) => `<tr data-sec="${r.id}" data-to="SURP" style="cursor:pointer"><td class="l dm">${fds(r.d)}</td><td class="l"><span class="rn">${i + 1})</span><b class="wh">${r.id}</b></td><td class="l am">${esc(r.s.short || r.s.n)}</td><td class="l dm">${esc(r.q)}</td><td class="wh">${num(r.eps, 2)}</td><td>${num(r.cons, 2)}</td><td><span class="${cls(r.pct)}">${r.pct > 0 ? '+' : ''}${num(r.pct, 1)} %</span></td><td class="wcb" style="width:16%;min-width:90px;position:relative"><span class="z" style="position:absolute;left:50%;top:2px;bottom:2px;border-left:1px solid #5a5a5a"></span><i style="position:absolute;top:4px;bottom:4px;${r.pct >= 0 ? 'left:50%;background:#32c74c' : 'right:50%;background:#ff433d'};width:${Math.min(50, Math.abs(r.pct) / 20 * 50).toFixed(1)}%"></i></td><td>${react[i] != null ? pc(react[i]) : '—'}</td></tr>`).join('') || '<tr><td class="l dm" colspan="9">Aucune publication sur la période.</td></tr>'}</tbody></table></div>`,
        { np: true, lect: 'Surprise = (BPA publié − consensus) ÷ |consensus|. Réaction : variation du cours entre la clôture de la veille de la publication et celle du lendemain (couvre une publication avant l’ouverture comme après la clôture). Barre : surprise (échelle ±20 %).' })}`;
  }
  const q = $('eaQ'); if (q) q.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); st.q = q.value.trim(); render(); } };
};

/* ------------------------------------------------------------------ Alertes personnelles (onglet de ALRT) : seuils de cours, de variation,
   de RSI, de moyenne mobile, de plus haut / bas 52 semaines, de rendement ; vérifiées à chaque relevé, enregistrées dans ce navigateur */
const MA_K = 'fqt_alerts_v1';
const maLoad = () => { try { const a = JSON.parse(localStorage.getItem(MA_K) || '[]'); return Array.isArray(a) ? a : []; } catch (e) { return []; } };
const maSave = A => { try { localStorage.setItem(MA_K, JSON.stringify(A)); } catch (e) { /* stockage indisponible */ } };
const MA_T = {
  pxu: ['Cours ≥', s => s.last, (v, t) => v >= t, true], pxd: ['Cours ≤', s => s.last, (v, t) => v <= t, true],
  up: ['Hausse du jour ≥ (%)', s => s.pct != null ? s.pct * 100 : null, (v, t) => v >= t, true], dn: ['Baisse du jour ≥ (%)', s => s.pct != null ? -s.pct * 100 : null, (v, t) => v >= t, true],
  rsiu: ['RSI 14 ≥', s => s.rsi, (v, t) => v >= t, true], rsid: ['RSI 14 ≤', s => s.rsi, (v, t) => v <= t, true],
  mau: ['Cours au-dessus de la MM 200', s => s.sma200 ? (s.last / s.sma200 - 1) * 100 : null, v => v > 0, false], mad: ['Cours sous la MM 200', s => s.sma200 ? (s.last / s.sma200 - 1) * 100 : null, v => v < 0, false],
  hi: ['Nouveau plus haut 52 semaines', s => s.hi52 ? (s.last / s.hi52 - 1) * 100 : null, v => v >= -1e-9, false], lo: ['Nouveau plus bas 52 semaines', s => s.lo52 ? (s.last / s.lo52 - 1) * 100 : null, v => v <= 1e-9, false],
  yld: ['Rendement du dividende ≥ (%)', s => s.yld != null ? s.yld * 100 : null, (v, t) => v >= t, true],
};
function maCheck(notify = true) {
  if (!Q.sum || !Q.by) return; const A = maLoad(); let ch = false, fired = [];
  for (const a of A) { const s = Q.by[a.id], T = MA_T[a.k]; if (!s || !T || a.hit) continue; const v = T[1](s); if (v == null || !isFinite(v)) continue; if (T[2](v, a.v)) { a.hit = Date.now(); a.hv = v; ch = true; fired.push(a); } }
  if (ch) maSave(A);
  if (notify && fired.length && typeof Notification !== 'undefined' && Notification.permission === 'granted') for (const a of fired) { try { new Notification(`Alerte ${a.id}`, { body: `${MA_T[a.k][0]}${MA_T[a.k][3] ? ' ' + num(a.v, 2) : ''} · ${px(Q.by[a.id], Q.by[a.id].last)}` }); } catch (e) { /* notifications refusées */ } }
  const n = A.filter(a => a.hit && !a.seen).length, b = document.getElementById('alB'); if (b) { b.hidden = !n; b.innerHTML = `${ICO.bell} ${n}`; b.title = `${n} alerte(s) déclenchée(s)`; }
}
setInterval(() => maCheck(true), 60000); setTimeout(() => maCheck(false), 4000);
document.addEventListener('click', e => { if (e.target && e.target.id === 'alB') { ST.tab.ALRT = 'mine'; go('ALRT'); } });
const ALRT_OLD = PAGES.ALRT;
PAGES.ALRT = async (m, alive) => {
  const tab = tabState('ALRT', 'sys'); setTabs([['sys', 'Alertes fondamentales'], ['mine', 'Mes alertes']], tab, k => { ST.tab.ALRT = k; render(); });
  if (tab !== 'mine') return ALRT_OLD(m, alive);
  setTitle('Alert Monitor · Mes alertes'); maCheck(false); const A = maLoad(); A.forEach(a => { if (a.hit) a.seen = true; }); maSave(A); maCheck(false);
  const st = ST.ma = ST.ma || { k: 'pxu' };
  m.innerHTML = `<div class="tools ttb"><span class="tlab">Titre</span><input class="ofld" id="maT" placeholder="SNTS, AAPL…" autocomplete="off" style="width:140px"><span class="tlab">Condition</span><select class="ofld" id="maK">${Object.entries(MA_T).map(([k, t]) => `<option value="${k}" ${st.k === k ? 'selected' : ''}>${t[0]}</option>`).join('')}</select>
      <span class="tlab">Seuil</span><input class="ofld" id="maV" style="width:90px" ${MA_T[st.k][3] ? '' : 'disabled placeholder="—"'}><button class="tb on" id="maA">Ajouter l’alerte</button><span class="gsp"></span>
      ${typeof Notification !== 'undefined' && Notification.permission !== 'granted' ? '<button class="tb" id="maN">Activer les notifications du navigateur</button>' : '<span class="dm">notifications du navigateur actives</span>'}</div>
    ${pn(`Mes alertes · ${A.length}`, 'ALRT', A.length ? `<table class="t"><thead><tr><th class="l">Titre</th><th class="l">Nom</th><th class="l">Condition</th><th>Seuil</th><th>Valeur actuelle</th><th>Cours</th><th class="l">État</th><th></th></tr></thead><tbody>${A.map((a, i) => { const s = Q.by[a.id], T = MA_T[a.k]; const v = s && T ? T[1](s) : null;
        return `<tr data-sec="${esc(a.id)}" data-to="GP" style="cursor:pointer"><td class="l"><span class="rn">${i + 1})</span><b class="wh">${esc(a.id)}</b></td><td class="l am">${esc(s ? s.short || s.n : '—')}</td><td class="l">${T ? T[0] : '—'}</td><td>${T && T[3] ? num(a.v, 2) : '—'}</td><td>${v != null ? num(v, 2) + (['up', 'dn', 'mau', 'mad', 'hi', 'lo', 'yld'].includes(a.k) ? ' %' : '') : '—'}</td><td class="wh">${s ? px(s, s.last) : '—'}</td>
          <td class="l">${a.hit ? `<span class="dn">déclenchée</span> <span class="dm">${new Date(a.hit).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>` : '<span class="up">armée</span>'}</td>
          <td class="l">${a.hit ? `<span class="pdx" data-mre="${i}" title="réarmer">↻</span>` : ''} <span class="pdx" data-mdel="${i}" title="supprimer">✕</span></td></tr>`; }).join('')}</tbody></table>` : '<div class="empty">Aucune alerte. Choisissez un titre, une condition et un seuil.</div>',
      { np: true, lect: 'Les alertes sont vérifiées à chaque relevé (toutes les 15 minutes) tant que le terminal est ouvert dans ce navigateur ; une alerte déclenchée allume la cloche en haut à droite et, si vous l’avez permis, envoie une notification. ↻ pour la réarmer. Clic sur une ligne : graphique du titre.' })}`;
  const T = $('maT'); T.oninput = () => { const L = searchSecs(T.value).slice(0, 10); if (!L.length) { ddClose(); return; } ddOpen(T, L.map(s => ({ code: s.id, l: esc(s.short || s.n), run: () => { T.value = s.id; $('maV').focus(); } }))); };
  $('maK').onchange = e => { st.k = e.target.value; render(); };
  const add = () => { const s = Q.by[T.value.trim().toUpperCase()] || searchSecs(T.value)[0], v = parseFloat(String($('maV').value).replace(/\s/g, '').replace(',', '.')); if (!s || (MA_T[st.k][3] && !isFinite(v))) { T.focus(); return; }
    const B = maLoad(); B.push({ id: s.id, k: st.k, v: MA_T[st.k][3] ? v : null, t: Date.now() }); maSave(B); maCheck(false); render(); };
  $('maA').onclick = add; $('maV').onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); add(); } };
  const nb = $('maN'); if (nb) nb.onclick = () => Notification.requestPermission().then(() => render());
  m.querySelectorAll('[data-mdel]').forEach(b => b.onclick = e => { e.stopPropagation(); const B = maLoad(); B.splice(+b.dataset.mdel, 1); maSave(B); maCheck(false); render(); });
  m.querySelectorAll('[data-mre]').forEach(b => b.onclick = e => { e.stopPropagation(); const B = maLoad(), a = B[+b.dataset.mre]; if (a) { a.hit = null; a.seen = false; a.hv = null; } maSave(B); render(); });
};

/* ------------------------------------------------------------------ HS : écran « Historical Spread » — rapport ou écart entre deux titres,
   moyenne et bandes à ±1 et ±2 écarts-types, score z, centile (valeur relative, paires) */
PAGES.HS = async (m, alive) => {
  const s = sec(ST.sec); setTitle('Historical Spread'); const st = ST.hs = ST.hs || {}; if (st.a !== s.id) { st.a = s.id; st.b = benchFor(s); }
  st.mode = st.mode || 'r'; st.y = st.y || 3; st.fx = st.fx ?? true;
  const b = Q.by[st.b] ? st.b : 'BRVMC';
  const [A, B] = await Promise.all([series(s.id).catch(() => null), series(b).catch(() => null)]); if (!alive()) return;
  if (!A || !B) { m.innerHTML = pn('Écart historique', 'HS', '<div class="empty">Historique indisponible.</div>'); return; }
  const sb = Q.by[b], conv = st.fx && sb.ccy !== s.ccy, mb = new Map(B.x.map((d, i) => [d, B.c[i]]));
  const t0 = (() => { const t = new Date(Date.now() - st.y * 365.25 * 864e5); return t.getUTCFullYear() * 10000 + (t.getUTCMonth() + 1) * 100 + t.getUTCDate(); })();
  const X = A.x.filter(d => d >= t0 && mb.has(d)); const f = conv ? await fxFactor(sb.ccy, s.ccy, X).catch(() => null) : null; if (!alive()) return;
  const ma = new Map(A.x.map((d, i) => [d, A.c[i]])), pa = X.map(d => ma.get(d)), pb = X.map((d, i) => mb.get(d) * (f && f[i] ? f[i] : 1));
  const V = X.map((_, i) => st.mode === 'r' ? (pb[i] ? pa[i] / pb[i] : null) : st.mode === 'n' ? null : pa[i] - pb[i]);
  /* mode « n » : performances relatives en base 100 (écart en points) */
  if (st.mode === 'n') { for (let i = 0; i < X.length; i++) V[i] = pa[i] / pa[0] * 100 - pb[i] / pb[0] * 100; }
  const ok = V.filter(v => v != null && isFinite(v)); if (ok.length < 30) { m.innerHTML = pn('Écart historique', 'HS', '<div class="empty">Pas assez de séances communes aux deux titres sur la période.</div>'); return; }
  const mu = U.mean(ok), sd = U.std(ok), cur = ok[ok.length - 1], z = sd ? (cur - mu) / sd : null, pct = ok.filter(v => v <= cur).length / ok.length, mn = Math.min(...ok), mx = Math.max(...ok);
  const ra = [], rb = []; for (let i = 1; i < X.length; i++) if (pa[i - 1] && pb[i - 1]) { ra.push(pa[i] / pa[i - 1] - 1); rb.push(pb[i] / pb[i - 1] - 1); } const cv = covar(ra, rb), corr = cv != null ? cv / (U.std(ra) * U.std(rb)) : null;
  const half = (() => { /* demi-vie du retour à la moyenne (AR(1) sur l'écart) */ const y = ok.slice(1), x0 = ok.slice(0, -1), mx0 = U.mean(x0), my = U.mean(y); let sxy = 0, sxx = 0; for (let i = 0; i < y.length; i++) { sxy += (x0[i] - mx0) * (y[i] - my); sxx += (x0[i] - mx0) ** 2; } const ph = sxx ? sxy / sxx : null; return ph > 0 && ph < 1 ? Math.log(.5) / Math.log(ph) : null; })();
  const fmtV = v => st.mode === 'r' ? num(v, v < 10 ? 4 : 2) : num(v, 2), ML = { r: `Rapport ${s.id} / ${b}`, s: `Écart ${s.id} − ${b}${conv ? ` (en ${s.ccy})` : ''}`, n: `Écart de performance ${s.id} − ${b} (points, base 100)` };
  m.innerHTML = `<div class="tools weic"><span class="tlab">Second titre</span><input class="ofld" id="hsB" value="${esc(b)}" style="width:110px" autocomplete="off"><span class="am">${esc(sb.short || sb.n)}</span>
      <span class="tlab">Mesure</span><select class="ofld" id="hsM"><option value="r" ${st.mode === 'r' ? 'selected' : ''}>Rapport</option><option value="s" ${st.mode === 's' ? 'selected' : ''}>Écart</option><option value="n" ${st.mode === 'n' ? 'selected' : ''}>Écart de performance (base 100)</option></select>
      <span class="tlab">Période</span><select class="ofld" id="hsY">${[1, 2, 3, 5, 10].map(y => `<option value="${y}" ${st.y === y ? 'selected' : ''}>${y} an${y > 1 ? 's' : ''}</option>`).join('')}</select>
      ${sb.ccy !== s.ccy ? `<label class="gck"><input type="checkbox" id="hsF" ${st.fx ? 'checked' : ''}><i></i>Convertir ${sb.ccy} en ${s.ccy}</label>` : ''}</div>
    <div class="grid side">${pn(`${ML[st.mode]} · ${X.length} séances communes`, 'HS', cvb('hsG', 430), { np: true })}
      ${pn('Statistiques', 'HS', `<div class="kv2"><span>Dernier</span><b class="wh">${fmtV(cur)}</b><span>Moyenne</span><b>${fmtV(mu)}</b><span>Écart-type</span><b>${fmtV(sd)}</b><span>Score z</span><b class="${z > 2 ? 'dn' : z < -2 ? 'up' : 'wh'}">${z != null ? num(z, 2) : '—'}</b><span>Centile sur la période</span><b>${num(pct * 100, 0)} %</b><span>Plus haut / plus bas</span><b>${fmtV(mx)} / ${fmtV(mn)}</b>
          <span>Corrélation des variations quotidiennes</span><b>${corr != null ? num(corr, 2) : '—'}</b><span>Demi-vie du retour à la moyenne</span><b>${half ? num(half, 0) + ' séances' : 'pas de retour à la moyenne mesurable'}</b></div>`,
        { lect: `Score z = (dernier − moyenne) ÷ écart-type sur la période : au-delà de ±2, l’écart est inhabituel par rapport à son histoire. Demi-vie : nombre de séances pour que l’écart à la moyenne se réduise de moitié, estimé sur un modèle autorégressif simple. Outil de mesure, pas un signal de transaction.` })}</div>`;
  const XX = X.slice(-V.length), line = v => V.map(() => v);
  new TSChart($('hsG'), { panes: [{ h: 1, fmt: fmtV }], grid: 'dot', xticks: bbgTicks }).set({ x: XX, series: [{ y: V, color: '#ffffff', w: 1.4, label: st.mode === 'r' ? 'Rapport' : 'Écart', fmt: fmtV }, { y: line(mu), color: '#f9a33a', w: 1.1, label: 'Moyenne', fmt: fmtV },
    { y: line(mu + sd), color: 'rgba(95,208,234,.75)', w: 1, label: '+1 σ', fmt: fmtV }, { y: line(mu - sd), color: 'rgba(95,208,234,.75)', w: 1, label: '−1 σ', fmt: fmtV }, { y: line(mu + 2 * sd), color: 'rgba(255,67,61,.8)', w: 1, label: '+2 σ', fmt: fmtV }, { y: line(mu - 2 * sd), color: 'rgba(50,199,76,.8)', w: 1, label: '−2 σ', fmt: fmtV }] }, [0, XX.length - 1]);
  const inp = $('hsB'); inp.oninput = () => { const L = searchSecs(inp.value).slice(0, 10); if (!L.length) { ddClose(); return; } ddOpen(inp, L.map(x => ({ code: x.id, l: esc(x.short || x.n), run: () => { st.b = x.id; render(); } }))); };
  inp.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); const x = Q.by[inp.value.trim().toUpperCase()] || searchSecs(inp.value)[0]; if (x) { st.b = x.id; render(); } } };
  $('hsM').onchange = e => { st.mode = e.target.value; render(); }; $('hsY').onchange = e => { st.y = +e.target.value; render(); }; const hf = $('hsF'); if (hf) hf.onchange = e => { st.fx = e.target.checked; render(); };
};

/* ------------------------------------------------------------------ WEIF : contrats à terme sur indices (indication d'ouverture, écart au comptant) */
PAGES.WEIF = async (m, alive) => {
  setTitle('World Equity Index Futures'); const W = await WMKT(); if (!alive()) return;
  const F = Object.fromEntries(((W && W.cmd) || []).filter(r => r.g === 'IXF').map(r => [r.s, r])), I = Object.fromEntries(((W && W.idx) || []).map(r => [r.s, r]));
  const D = [['@SP.1', 'S&P 500 (CME)', '.SPX'], ['@ND.1', 'Nasdaq-100 (CME)', 'NDX'], ['@DJ.1', 'Dow Jones (CBOT)', '.DJI'], ['@TFS.1', 'Russell 2000 (CME)', '.RUT'], ['@VX.1', 'VIX', '.VIX'], ['@FFI.1', 'FTSE 100 (ICE)', '.FTSE'], ['@NK.1', 'Nikkei 225 (CME, en $)', '.N225']].filter(d => F[d[0]]);
  if (!D.length) { m.innerHTML = pn('Contrats à terme sur indices', 'INDX', '<div class="empty">Contrats en attente du prochain relevé (toutes les 15 minutes).</div>'); return; }
  const spot = k => k === 'NDX' ? (Q.by.NDX ? { last: Q.by.NDX.last, t: null } : null) : I[k];
  const mx = Math.max(1e-6, ...D.map(d => Math.abs(F[d[0]].pct || 0)));
  m.innerHTML = `<div class="grid side">${pn('Contrats à terme sur indices · 1re échéance', 'INDX', `<table class="t wcr"><thead><tr><th class="l">Contrat</th><th class="l">Échéance</th><th>Dernier</th><th>Var.</th><th>Var. %</th><th class="c">Indication</th><th>Heure</th><th>Indice comptant</th><th>Écart (pts)</th><th>Écart %</th></tr></thead><tbody>
      ${D.map(([k, l, ix], i) => { const r = F[k], sp = spot(ix), b = sp && sp.last && k !== '@NK.1' ? r.last - sp.last : null;
        return `<tr><td class="l"><span class="rn">${i + 1})</span><span class="am">${l}</span></td><td class="l dm">${esc(ctr(r.n) || r.exp || '')}</td><td class="wh">${num(r.last, 2)}</td><td class="${cls(r.chg)}">${r.chg != null ? (r.chg > 0 ? '+' : '') + num(r.chg, 2) : '—'}</td><td>${pc(r.pct)}</td>
          <td class="wcb"><span class="z"></span>${r.pct != null ? `<i class="${r.pct >= 0 ? 'p' : 'n'}" style="width:${(Math.abs(r.pct) / mx * 50).toFixed(1)}%"></i>` : ''}</td><td class="dm">${qTime(r.t)}</td><td>${sp && sp.last ? num(sp.last, 2) : '—'}</td><td>${b != null ? `<span class="${cls(b)}">${b > 0 ? '+' : ''}${num(b, 2)}</span>` : '—'}</td><td>${b != null ? pc(b / sp.last) : '—'}</td></tr>`; }).join('')}</tbody></table>`,
      { np: true, lect: 'Var. = variation du contrat depuis le cours de compensation de la veille : avant l’ouverture de New York, c’est l’indication du sens d’ouverture des indices. Écart = contrat − dernier niveau de l’indice au comptant (qui peut dater de la clôture précédente) ; il reflète aussi le portage (taux moins dividendes) jusqu’à l’échéance. Nikkei coté en dollars : écart non calculé.' })}
    ${pn('Lecture', 'INDX', `<div class="kv2">${D.filter(d => ['@SP.1', '@ND.1', '@DJ.1', '@TFS.1'].includes(d[0])).map(([k, l]) => `<span>${l.replace(/ \(.*\)/, '')}</span><b>${pc(F[k].pct)}</b>`).join('')}${F['@VX.1'] ? `<span>VIX à terme</span><b class="wh">${num(F['@VX.1'].last, 2)}</b>` : ''}</div>`, { lect: 'Signe et ampleur attendus à l’ouverture de Wall Street d’après les contrats à terme, hors nouvelles d’ici l’ouverture.' })}</div>`;
};

/* ------------------------------------------------------------------ anticipations de taux de la Fed (onglet 2 de RATES, ex-WIRP) d'après les contrats Fed funds 30 jours
   Calendrier officiel des réunions (relu chaque jour). Méthode de référence du marché : taux effectif de début et de fin de chaque mois de
   réunion tiré des contrats (le mois voisin sans réunion sert d'ancrage), puis probabilités des fourchettes cibles réunion après réunion
   (arbre de mouvements de 25 pb). */
const FED_N = 3; // décisions affichées
const ymAdd = (ym, k) => { let [y, mo] = ym.split('-').map(Number); mo += k; while (mo > 12) { mo -= 12; y++; } while (mo < 1) { mo += 12; y--; } return `${y}-${String(mo).padStart(2, '0')}`; };
function fedPaths(R, FD, eff) {
  const today = new Date().toISOString().slice(0, 10), F = Object.fromEntries(R.map(x => [x.ym, x.imp])), has = ym => FD.some(d => d.slice(0, 7) === ym);
  const out = []; let prevE = null, prevYm = null;
  for (const d of FD.filter(d => d >= today && F[d.slice(0, 7)] != null).sort()) {
    const ym = d.slice(0, 7), [y, mo] = ym.split('-').map(Number), N = new Date(Date.UTC(y, mo, 0)).getUTCDate(), dd = Math.min(+d.slice(8, 10), N), f = F[ym];
    const pv = ymAdd(ym, -1), nx = ymAdd(ym, 1); let S = null, E = null;
    if (prevYm === pv && prevE != null) S = prevE; else if (!has(pv) && F[pv] != null) S = F[pv];     /* début du mois : réunion du mois précédent, ou mois précédent sans réunion */
    if (!has(nx) && F[nx] != null) E = F[nx];                                                          /* fin du mois : mois suivant sans réunion */
    if (S == null && E != null) S = (f - E * (N - dd) / N) / (dd / N);                                /* le nouveau taux s'applique le lendemain de la décision */
    if (S == null) S = prevE != null ? prevE : eff;
    if (E == null) E = N - dd > 0 ? (f - S * dd / N) / ((N - dd) / N) : (F[nx] != null ? F[nx] : S);
    out.push({ d, pre: S, post: E, chg: (E - S) * 100 }); prevE = E; prevYm = ym;
  }
  return out;
}
async function wirpView(m, alive) {
  setTitle('World Interest Rate Probability'); const [W, E] = await Promise.all([WMKT(), ecoLite().catch(() => null)]); if (!alive()) return;
  const FF = ((W && W.cmd) || []).filter(r => r.g === 'FF').sort((a, b) => String(a.exp).localeCompare(String(b.exp)));
  if (FF.length < 3) { m.innerHTML = pn('Anticipations de taux', 'RATES', '<div class="empty">Contrats Fed funds en attente du prochain relevé (toutes les 15 minutes).</div>'); return; }
  const M = E ? Object.fromEntries(E.meta.map(x => [x.id, x])) : {}, eff = M.DFF ? M.DFF.last : 100 - FF[0].last, lo = M.DFEDTARL ? M.DFEDTARL.last : null, hi = M.DFEDTARU ? M.DFEDTARU.last : null;
  const R = FF.map(r => ({ r, ym: String(r.exp).slice(0, 7), imp: 100 - r.last })), FD = (E && E.fomc) || [];
  const meet = fedPaths(R, FD, eff).slice(0, FED_N);
  /* probabilités des fourchettes cibles : à chaque réunion, la variation attendue se répartit entre les deux mouvements de 25 pb qui l'encadrent */
  let dist = { 0: 1 };
  for (const x of meet) { const n = x.chg / 25, k = Math.floor(n + 1e-9), fr = Math.max(0, n - k), nd = {};
    for (const [s0, p] of Object.entries(dist)) { const s = +s0; nd[s + k] = (nd[s + k] || 0) + p * (1 - fr); if (fr > 1e-6) nd[s + k + 1] = (nd[s + k + 1] || 0) + p * fr; }
    x.dist = dist = nd; }
  const steps = [...new Set(meet.flatMap(x => Object.keys(x.dist).filter(s => x.dist[s] >= 5e-4).map(Number)))].sort((a, b) => a - b);
  const rng = s => lo != null && hi != null ? `${num(lo + s * .25, 2)}–${num(hi + s * .25, 2)}` : `${s > 0 ? '+' : ''}${s * 25} pb`;
  const mois = ym => new Date(ym + '-15T12:00:00Z').toLocaleDateString('fr-FR', { month: 'short', year: 'numeric', timeZone: 'UTC' });
  const lect1 = p => { const top = Object.entries(p).sort((a, b) => b[1] - a[1])[0]; const s = +top[0]; return s === 0 ? 'statu quo le plus probable' : `${s < 0 ? 'baisse' : 'hausse'} de ${Math.abs(s) * 25} pb la plus probable`; };
  const tbl = meet.length ? `<table class="t wrp"><thead><tr><th class="l">Décision</th>${steps.map(s => `<th${s === 0 ? ' class="wh"' : ''}>${rng(s)}</th>`).join('')}<th>Taux début</th><th>Taux fin</th><th>Var. (pb)</th><th class="l">Lecture</th></tr></thead><tbody>${meet.map(x => { const mx = Math.max(...Object.values(x.dist));
      return `<tr><td class="l am">${fds(x.d)}</td>${steps.map(s => { const p = x.dist[s] || 0; return `<td class="${p === mx ? 'yl' : p >= .005 ? 'wh' : 'dm'}">${p >= 5e-4 ? num(p * 100, 1) + ' %' : '—'}</td>`; }).join('')}<td>${num(x.pre, 3)} %</td><td class="wh">${num(x.post, 3)} %</td><td>${bpS(x.chg)}</td><td class="l">${lect1(x.dist)}</td></tr>`; }).join('')}</tbody></table>`
    : `<div class="empty">${FD.length ? 'Aucune réunion dans la fenêtre des contrats relevés.' : 'Calendrier des réunions de la Fed en attente du prochain relevé.'}</div>`;
  m.innerHTML = `<div class="tools ttb"><span class="tlab">Banque centrale</span><b class="wh">Réserve fédérale (États-Unis)</b><span class="tlab">Fourchette cible</span><b class="wh">${lo != null && hi != null ? `${num(lo, 2)} – ${num(hi, 2)} %` : '—'}</b><span class="tlab">Taux effectif</span><b class="wh">${num(eff, 2)} %</b><span class="gsp"></span><span class="dm">contrats relevés à ${qTime(FF[0].t)}</span></div>
    ${pn(`Probabilités des fourchettes cibles · ${meet.length} prochaine${meet.length > 1 ? 's' : ''} décision${meet.length > 1 ? 's' : ''} du FOMC`, 'RATES', tbl,
      { np: true, lect: 'Méthode de référence du marché : pour chaque mois de réunion, le taux effectif de début et de fin de mois est tiré des contrats Fed funds 30 jours (le contrat d’un mois voisin sans réunion sert d’ancrage ; le nouveau taux s’applique le lendemain de la décision). La variation attendue se répartit entre les deux mouvements de 25 pb qui l’encadrent, et les réunions s’enchaînent (probabilités cumulées). Dates des réunions : calendrier officiel du FOMC, relu chaque jour.' })}
    <div class="grid c2">${pn('Taux moyen implicite par mois', 'RATES', cvb('wiG', 300), { np: true })}
    ${pn('Contrats Fed funds 30 jours', 'RATES', `<table class="t"><thead><tr><th class="l">Mois</th><th class="l">Échéance</th><th>Prix</th><th>Var.</th><th>Taux implicite</th><th>Écart au taux effectif (pb)</th><th>En mouvements de 25 pb</th></tr></thead><tbody>${R.map((x, i) => { const d = (x.imp - eff) * 100, mt = FD.find(z => z.slice(0, 7) === x.ym);
        return `<tr><td class="l"><span class="rn">${i + 1})</span><span class="am">${mois(x.ym)}</span>${mt ? ` <i class="qd" title="réunion du FOMC le ${fds(mt)}">R</i>` : ''}</td><td class="l dm">${fds(x.r.exp)}</td><td class="wh">${num(x.r.last, 4)}</td><td class="${cls(x.r.chg)}">${x.r.chg != null ? (x.r.chg > 0 ? '+' : '') + num(x.r.chg, 3) : '—'}</td><td class="wh">${num(x.imp, 3)} %</td><td>${bpS(d)}</td><td>${num(d / 25, 2)}</td></tr>`; }).join('')}</tbody></table>`,
      { np: true, lect: 'Taux implicite = 100 − prix du contrat : taux effectif moyen attendu sur le mois. R = mois d’une réunion du FOMC. Un écart négatif signifie que le marché anticipe des baisses de taux.' })}</div>`;
  new TSChart($('wiG'), { panes: [{ h: 1, fmt: v => num(v, 2) + '%', refs: (lo != null ? [{ v: lo, color: 'rgba(200,200,200,.5)' }, { v: hi, color: 'rgba(200,200,200,.5)' }] : []).concat([{ v: eff, color: CL.amber }]) }], grid: 'dot' })
    .set({ x: R.map(x => +x.r.exp.replace(/-/g, '')), series: [{ y: R.map(x => x.imp), color: '#5fd0ea', w: 2, label: 'Taux implicite', fmt: v => num(v, 3) + ' %' }] }, [0, R.length - 1]);
}

/* ------------------------------------------------------------------ BRIEF : synthèse du jour (BRVM, portefeuille, alertes, marchés mondiaux,
   changes et matières, taux, agenda du jour, actualités) — une page de départ pour la séance */
PAGES.BRIEF = async (m, alive) => {
  setTitle('Daily Briefing'); const [W, C, N, DV, E] = await Promise.all([WMKT(), getJSON('calendar.json').catch(() => null), getJSON('news.json').catch(() => null), getJSON('dividends.json').catch(() => []), getJSON('ee.json').catch(() => null)]); if (!alive()) return;
  const today = new Date().toISOString().slice(0, 10), wk = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10);
  const idx = Object.fromEntries(((W && W.idx) || []).map(r => [r.s, r])), cmd = Object.fromEntries(((W && W.cmd) || []).map(r => [r.s, r])), fx = Object.fromEntries(((W && W.fx) || []).map(r => [r.s, r])), rt = Object.fromEntries(((W && W.rt) || []).map(r => [r.s, r]));
  const L = (lab, last, pct, d = 2, fn = '') => `<tr${fn ? ` data-fn="${fn}" style="cursor:pointer"` : ''}><td class="l am">${lab}</td><td class="wh">${last != null ? num(last, d) : '—'}</td><td>${pc(pct)}</td></tr>`;
  const br = secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity' && s.pct != null), up = br.filter(s => s.pct > 0).length, dn = br.filter(s => s.pct < 0).length, mv = br.slice().sort((a, b) => b.pct - a.pct);
  const p1 = pn('1) BRVM', 'BRVM', `<table class="t"><tbody>${['BRVMC', 'BRVM30', 'BRVMPR'].map(id => Q.by[id]).filter(Boolean).map(s => `<tr data-sec="${s.id}" data-to="GP" style="cursor:pointer"><td class="l am">${esc(s.n)}</td><td class="wh">${num(s.last, 2)}</td><td>${pc(s.pct)}</td><td>${pc(s.ytd, 1)}</td></tr>`).join('')}
      <tr class="sep2"><td class="l">Hausses / baisses</td><td class="wh" colspan="3"><span class="up">${up}</span> / <span class="dn">${dn}</span> · montant ${big(br.reduce((a, s) => a + (s.vday || 0), 0))} XOF</td></tr>
      ${mv.slice(0, 3).concat(mv.slice(-3)).map(s => `<tr data-sec="${s.id}" data-to="GP" style="cursor:pointer"><td class="l"><b class="wh">${s.id}</b> <span class="am">${esc(s.short || s.n)}</span></td><td class="wh">${px(s, s.last)}</td><td>${pc(s.pct)}</td><td></td></tr>`).join('')}</tbody></table>`, { np: true });
  const P = portLoad(); let p2 = '';
  if (P.pos.length) { const UF = W && W.fx ? fxUsd(W) : { USD: { now: 1, d: 1 } }; const cv = (v, c, k = 'now') => c === P.base ? v : (c === 'XOF' && P.base === 'EUR') ? v / XOF_EUR : (c === 'EUR' && P.base === 'XOF') ? v * XOF_EUR : UF[c] && UF[P.base] ? v * UF[c][k] / UF[P.base][k] : null;
    const R = P.pos.map(p => { const s = Q.by[p.id]; if (!s) return null; const v = cv(p.q * s.last, s.ccy), v0 = s.prev ? cv(p.q * s.prev, s.ccy, 'd') : null; return v != null ? { s, v, d: v0 != null ? v - v0 : 0 } : null; }).filter(Boolean);
    const tot = R.reduce((a, r) => a + r.v, 0), dj = R.reduce((a, r) => a + r.d, 0), dec = P.base === 'XOF' ? 0 : 2; R.sort((a, b) => Math.abs(b.d) - Math.abs(a.d));
    p2 = pn('2) Votre portefeuille', 'PORTF', `<div class="kv2"><span>Valeur</span><b class="wh">${num(tot, dec)} ${P.base}</b><span>Résultat du jour</span><b><span class="${cls(dj)}">${dj > 0 ? '+' : ''}${num(dj, dec)}</span> (${pc(tot - dj ? dj / (tot - dj) : null)})</b>${R.slice(0, 3).map(r => `<span>${r.s.id}</span><b><span class="${cls(r.d)}">${r.d > 0 ? '+' : ''}${num(r.d, dec)}</span></b>`).join('')}</div>`); }
  else p2 = pn('2) Votre portefeuille', 'PORTF', '<div class="dm" style="padding:6px">Aucune position enregistrée : PORT pour saisir vos titres.</div>');
  const A = maLoad(), hit = A.filter(a => a.hit);
  const p3 = pn(`3) Mes alertes · ${hit.length} déclenchée${hit.length > 1 ? 's' : ''} sur ${A.length}`, 'ALRT', hit.length ? `<table class="t"><tbody>${hit.slice(0, 6).map(a => `<tr data-sec="${esc(a.id)}" data-to="GP" style="cursor:pointer"><td class="l wh">${esc(a.id)}</td><td class="l">${MA_T[a.k] ? MA_T[a.k][0] : ''}${a.v != null ? ' ' + num(a.v, 2) : ''}</td><td class="dm">${new Date(a.hit).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</td></tr>`).join('')}</tbody></table>` : `<div class="dm" style="padding:6px">${A.length ? 'Aucune alerte déclenchée.' : 'Aucune alerte : ALRT, onglet « Mes alertes ».'}</div>`, { np: true });
  const fut = [['@SP.1', 'S&P 500 (contrat)'], ['@ND.1', 'Nasdaq-100 (contrat)']].filter(x => cmd[x[0]]);
  const p4 = pn('4) Marchés mondiaux', 'INDX', `<table class="t"><tbody>${fut.map(([k, l]) => L(l, cmd[k].last, cmd[k].pct, 2, 'WEIF')).join('')}${[['.SPX', 'S&P 500'], ['.IXIC', 'Nasdaq Composite'], ['.STOXX50E', 'Euro Stoxx 50'], ['.FCHI', 'CAC 40'], ['.GDAXI', 'DAX'], ['.FTSE', 'FTSE 100'], ['.N225', 'Nikkei 225'], ['.HSI', 'Hang Seng'], ['.VIX', 'VIX']].filter(x => idx[x[0]]).map(([k, l]) => L(l, idx[k].last, idx[k].pct, 2, 'WEI')).join('')}</tbody></table>`, { np: true });
  const xo = fx['XOF='], eu = fx['EUR='];
  const p5 = pn('5) Changes et matières premières', 'COMMO', `<table class="t"><tbody>${eu ? L('EUR / USD', eu.last, eu.pct, 4, 'WCRS') : ''}${eu ? L('USD / XOF (parité euro)', XOF_EUR / eu.last, eu.pct != null ? 1 / (1 + eu.pct) - 1 : null, 2, 'FX') : xo ? L('USD / XOF', xo.last, xo.pct, 2, 'FX') : ''}${fx['.DXY'] ? L('Indice dollar (DXY)', fx['.DXY'].last, fx['.DXY'].pct, 3, 'WCRS') : ''}
      ${[['@CC.1', 'Cacao ($/t)'], ['@KC.1', 'Café arabica (¢/lb)'], ['@CT.1', 'Coton (¢/lb)'], ['@GC.1', 'Or ($/once)']].filter(x => cmd[x[0]]).map(([k, l]) => L(l, cmd[k].last, cmd[k].pct, 2, 'COMMO')).join('')}</tbody></table>`, { np: true });
  const bpc = r => r && r.chg != null ? `<span class="${cls(r.chg)}">${r.chg > 0 ? '+' : ''}${num(r.chg * 100, 1)} pb</span>` : '—';
  const ff = ((W && W.cmd) || []).filter(r => r.g === 'FF').sort((a, b) => String(a.exp).localeCompare(String(b.exp)));
  const p6 = pn('6) Taux', 'RATES', `<table class="t"><tbody>${[['US2Y', 'Trésor US 2 ans'], ['US10Y', 'Trésor US 10 ans'], ['DE10Y-DE', 'Allemagne 10 ans']].filter(x => rt[x[0]]).map(([k, l]) => `<tr data-fn="WB" style="cursor:pointer"><td class="l am">${l}</td><td class="wh">${num(rt[k].last, 3)} %</td><td>${bpc(rt[k])}</td></tr>`).join('')}
      ${ff.length > 3 ? `<tr data-fn="WIRP" style="cursor:pointer"><td class="l am">Fed funds implicite (${new Date(ff[3].exp + 'T12:00:00Z').toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })})</td><td class="wh">${num(100 - ff[3].last, 3)} %</td><td class="dm">${num((100 - ff[3].last - (100 - ff[0].last)) * 100, 0)} pb vs 1er mois</td></tr>` : ''}</tbody></table>`, { np: true });
  const ev = C && C.rows ? C.rows.map(r => Object.assign({ T: ecoDT(r.d) }, r)).filter(r => r.d.slice(0, 10) === today && r.i >= 0).sort((a, b) => a.d.localeCompare(b.d)) : [];
  const er = E ? Object.entries(E).map(([id, x]) => { const mm = String(x.ed || '').match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/); const d = mm ? `${mm[3]}-${mm[1].padStart(2, '0')}-${mm[2].padStart(2, '0')}` : null; return d && d >= today && d <= wk && Q.by[id] ? { id, d, w: /after market/i.test(x.ed) ? 'après clôture' : /before market/i.test(x.ed) ? 'avant ouverture' : '' } : null; }).filter(Boolean).sort((a, b) => a.d.localeCompare(b.d)) : [];
  const dv = (Array.isArray(DV) ? DV : []).filter(x => x.det && x.det >= today && x.det <= wk).sort((a, b) => a.det.localeCompare(b.det));
  const p7 = pn('7) Agenda', 'NEWS ECO', `<table class="t"><tbody>${ev.slice(0, 10).map(r => `<tr data-fn="NEWS ECO" style="cursor:pointer"><td class="l dm">${r.T.hm}</td><td class="l">${flagSVG(r.c, 16, 10)} ${esc(r.t)}</td><td>${r.f != null ? '<span class="dm">prév.</span> ' + esc(String(r.f)) : ''}${r.a != null ? ' <b class="wh">' + esc(String(r.a)) + '</b>' : ''}</td></tr>`).join('') || '<tr><td class="l dm" colspan="3">Aucune publication importante aujourd’hui.</td></tr>'}
      ${er.length ? `<tr class="grp"><td class="l" colspan="3">Résultats US des 7 prochains jours</td></tr>${er.slice(0, 8).map(r => `<tr data-sec="${r.id}" data-to="EE" style="cursor:pointer"><td class="l dm">${fds(r.d).slice(0, 5)}</td><td class="l"><b class="wh">${r.id}</b> <span class="am">${esc(Q.by[r.id].short || Q.by[r.id].n)}</span></td><td class="dm">${r.w}</td></tr>`).join('')}` : ''}
      ${dv.length ? `<tr class="grp"><td class="l" colspan="3">Détachements de dividendes BRVM (7 jours)</td></tr>${dv.map(x => `<tr data-sec="${x.t}" data-to="DVD" style="cursor:pointer"><td class="l dm">${fds(x.det).slice(0, 5)}</td><td class="l"><b class="wh">${x.t}</b> ${num(x.dps, 2)} XOF net</td><td>${Q.by[x.t] ? num(x.dps / Q.by[x.t].last * 100, 2) + ' %' : ''}</td></tr>`).join('')}` : ''}</tbody></table>`, { np: true });
  const it = (N && N.items ? N.items : []).slice().sort((a, b) => b.t - a.t).filter((x, i, a) => a.findIndex(y => y.ti === x.ti) === i).slice(0, 10);
  const p8 = pn('8) À la une', 'NEWS', `<div>${it.map((x, i) => `<div class="tn" data-u="${esc(x.u || '')}"><span class="no">${i + 1})</span><span class="h">${esc(x.ti)}</span><span class="s">${esc(x.s || '')}</span><span class="t">${new Date(x.t * 1000).toLocaleTimeString('fr-FR', { timeZone: 'Africa/Abidjan', hour: '2-digit', minute: '2-digit' })}</span></div>`).join('')}</div>`, { np: true });
  m.innerHTML = `<div class="grid c3"><div class="grid">${p1}${p2}${p3}</div><div class="grid">${p4}${p5}${p6}</div><div class="grid">${p7}${p8}</div></div>`;
  m.querySelectorAll('[data-fn]').forEach(r => { if (r.tagName === 'TR') r.onclick = () => go(r.dataset.fn); });
  m.querySelectorAll('.tn[data-u]').forEach(r => r.onclick = () => { if (r.dataset.u) window.open(r.dataset.u, '_blank', 'noopener'); });
};

/* ------------------------------------------------------------------ suivi des sociétés (onglets de EVTS) — publications, assemblées, dividendes, opérations
   (BRVM, d'après les avis officiels) ; dates de résultats et objectifs de cours des analystes (US) ; agenda des sociétés à venir */
const CF_REP = ['États financiers', 'Rapport d\'activité', 'Rapport annuel', 'Rapport des commissaires', 'Résultats financiers', 'Publication société'];
const cfPer = ti => { const m = String(ti || '').match(/(1er|2(?:e|ème|eme)|3(?:e|ème|eme)|4(?:e|ème|eme)|premier|deuxième|troisième)\s+(trimestre|semestre)\s+(\d{4})|exercice\s+(\d{4})/i); if (!m) return ''; if (m[4]) return 'Exercice ' + m[4];
  const n = /^(1|premier)/i.test(m[1]) ? 1 : /^(2|deux)/i.test(m[1]) ? 2 : /^(3|trois)/i.test(m[1]) ? 3 : 4; return `${/tri/i.test(m[2]) ? 'T' : 'S'}${n} ${m[3]}`; };
/* vue « suivi des sociétés », affichée comme onglet de EVTS (b = sociétés BRVM, u = sociétés US, a = agenda) */
async function cfView(m, alive, tab, code = 'EVTS') {
  setTitle(code === 'CORP RESULT' ? 'Earnings Analysis · Analyst Price Targets' : 'Corporate Events · Company Filings');
  const [EV, DV, E] = await Promise.all([getJSON('events.json').catch(() => []), getJSON('dividends.json').catch(() => []), getJSON('ee.json').catch(() => null)]); if (!alive()) return;
  const today = new Date().toISOString().slice(0, 10), st = ST.cf = ST.cf || { q: '', sort: 'pub' }, q = st.q.toLowerCase();
  const ev = Array.isArray(EV) ? EV : [], dv = Array.isArray(DV) ? DV : [];
  const usD = t => { const x = String(t || '').match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/); return x ? `${x[3]}-${x[1].padStart(2, '0')}-${x[2].padStart(2, '0')}` : null; };
  const tools = `<div class="tools ttb"><span class="tnar"><input id="cfQ" class="ofld" value="${esc(st.q)}" placeholder="&lt;Filtrer&gt;"></span><span class="gsp"></span><span class="dm">${tab === 'u' ? 'Dates et consensus publiés pour les actions US suivies' : 'D’après les avis officiels'}</span></div>`;
  const bindQ = () => { const x = $('cfQ'); if (x) x.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); st.q = x.value.trim(); render(); } }; m.querySelectorAll('tr[data-u]').forEach(r => r.onclick = e => { if (e.target.closest('[data-sec]') && !e.target.closest('a')) return; }); };
  if (tab === 'b') {
    const S_ = secsWhere(s => s.mkt === 'BRVM' && s.cls === 'Equity' && (!q || (s.id + ' ' + s.n + ' ' + (s.short || '')).toLowerCase().includes(q)));
    const R = S_.map(s => { const E_ = ev.filter(x => x.t === s.id); const rep = E_.filter(x => CF_REP.includes(x.c)).sort((a, b) => (b.d || '').localeCompare(a.d || ''))[0];
      const ag = E_.filter(x => x.c === 'Assemblée générale' && (x.e || '') >= today).sort((a, b) => a.e.localeCompare(b.e))[0], agL = E_.filter(x => x.c === 'Assemblée générale' && (x.e || '') < today).sort((a, b) => b.e.localeCompare(a.e))[0];
      const op = E_.filter(x => ['Fractionnement', 'Actions gratuites', 'Augmentation de capital avec droits', 'Avis sur une opération de capital'].includes(x.c) && (x.e || '') >= today)[0];
      const nd = dv.filter(x => x.t === s.id && ((x.det || '') >= today || (x.pay || '') >= today)).sort((a, b) => (a.det || a.pay).localeCompare(b.det || b.pay))[0];
      return { s, rep, ag, agL, op, nd }; }).sort((a, b) => ((b.rep || {}).d || '').localeCompare((a.rep || {}).d || ''));
    m.innerHTML = tools + pn(`Suivi des sociétés cotées à la BRVM · ${R.length}`, code, `<div class="tw" style="max-height:calc(100vh - 250px - var(--nwh, 90px))"><table class="t cft"><thead><tr><th class="l">Titre</th><th class="l">Société</th><th class="l">Dernière publication</th><th class="l">Période</th><th class="l">Date</th><th class="l">Prochaine AG</th><th class="l">Dernière AG</th><th class="l">Dividende à venir</th><th>Rdt</th><th class="l">Opération annoncée</th></tr></thead><tbody>
      ${R.map((r, i) => `<tr data-sec="${r.s.id}" data-to="CN" style="cursor:pointer"><td class="l"><span class="rn">${i + 1})</span><b class="wh">${r.s.id}</b></td><td class="l am">${esc(r.s.short || r.s.n)}</td>
        <td class="l">${r.rep ? `<a href="${esc(r.rep.u || '#')}" target="_blank" rel="noopener" class="cfl">${esc(r.rep.c)}</a>` : '<span class="dm">—</span>'}</td><td class="l">${r.rep ? cfPer(r.rep.ti) : ''}</td><td class="l dm">${r.rep ? fds(r.rep.d) : ''}</td>
        <td class="l">${r.ag ? `<b class="yl">${fds(r.ag.e)}</b>` : '<span class="dm">—</span>'}</td><td class="l dm">${r.agL ? fds(r.agL.e) : '—'}</td>
        <td class="l">${r.nd ? `${num(r.nd.dps, 2)} XOF · détach. ${fds(r.nd.det)}` : '<span class="dm">—</span>'}</td><td>${r.nd && r.s.last ? num(r.nd.dps / r.s.last * 100, 2) + ' %' : r.s.yld && !(r.s.dps_ex && r.s.dps_ex < new Date().getFullYear() - 2) ? `<span class="dm">${num(r.s.yld * 100, 2)} %</span>` : r.s.yld ? `<span class="dm" title="dernier dividende versé au titre de l’exercice ${r.s.dps_ex}">ancien</span>` : '—'}</td>
        <td class="l">${r.op ? `<span class="dn">${esc(r.op.c)}</span> ${fds(r.op.e)}` : ''}</td></tr>`).join('')}</tbody></table></div>`,
      { np: true, lect: 'Dernière publication = dernier rapport (états financiers, rapport d’activité, rapport annuel, rapport des commissaires aux comptes) annoncé par avis ; clic sur le type : document original. Prochaine AG = date de l’assemblée annoncée. Rendement : dividende annoncé ÷ cours (en gris : dernier dividende versé). Clic sur la ligne : actualités et avis de la société (CN).' });
    m.querySelectorAll('a.cfl').forEach(a => a.onclick = e => e.stopPropagation()); bindQ(); return;
  }
  if (tab === 'u') {
    const S_ = secsWhere(s => s.mkt === 'US' && s.cls === 'Equity' && s.typ !== 'ETF' && E && E[s.id] && (!q || (s.id + ' ' + s.n).toLowerCase().includes(q)));
    const R = S_.map(s => { const x = E[s.id], tp = x.tp || {}, d = usD(x.ed), su = (x.sur || []).slice().sort((a, b) => (usD(b.d) || '').localeCompare(usD(a.d) || ''))[0]; const n = (tp.buy || 0) + (tp.hold || 0) + (tp.sell || 0);
      return { s, d: d && d >= today ? d : null, w: /after market/i.test(x.ed) ? 'après clôture' : /before market/i.test(x.ed) ? 'avant ouverture' : '', est: /estimated|algorithm/i.test(x.ed || ''), tp, n, up: tp.priceTarget && s.last ? tp.priceTarget / s.last - 1 : null, su }; })
      .sort((a, b) => st.sort === 'up' ? (b.up ?? -9) - (a.up ?? -9) : (a.d || '9').localeCompare(b.d || '9'));
    m.innerHTML = tools + pn(`Objectifs de cours des analystes · actions US · ${R.length}`, code, `<div class="tw" style="max-height:calc(100vh - 250px - var(--nwh, 90px))"><table class="t cft"><thead><tr><th class="l">Titre</th><th class="l">Société</th><th class="l" data-cs="d" style="cursor:pointer">Prochains résultats${st.sort !== 'up' ? ' ▲' : ''}</th><th class="l">Moment</th><th>Cours</th><th>Objectif moyen</th><th>Fourchette</th><th data-cs="up" style="cursor:pointer">Potentiel${st.sort === 'up' ? ' ▼' : ''}</th><th>Achat / Cons. / Vente</th><th>Dernière surprise</th></tr></thead><tbody>
      ${R.map((r, i) => `<tr data-sec="${r.s.id}" data-to="ANR" style="cursor:pointer"><td class="l"><span class="rn">${i + 1})</span><b class="wh">${r.s.id}</b></td><td class="l am">${esc(r.s.short || r.s.n)}</td><td class="l">${r.d ? fds(r.d) + (r.est ? ' <i class="qd" title="date estimée">e</i>' : '') : '<span class="dm">—</span>'}</td><td class="l dm">${r.d ? r.w : ''}</td>
        <td class="wh">${num(r.s.last, 2)}</td><td>${r.tp.priceTarget ? num(r.tp.priceTarget, 2) : '—'}</td><td class="dm">${r.tp.lowPriceTarget ? num(r.tp.lowPriceTarget, 0) + ' – ' + num(r.tp.highPriceTarget, 0) : '—'}</td><td>${r.up == null ? '—' : (r.up > .75 || r.up < -.5 || (r.tp.lowPriceTarget && r.tp.highPriceTarget / r.tp.lowPriceTarget > 3)) ? `<span class="dm" title="écart inhabituel entre les objectifs publiés et le cours (objectifs dans une autre devise ou sur une autre base d’action possible) : à vérifier">${num(r.up * 100, 1)} % ?</span>` : pc(r.up, 1)}</td>
        <td>${r.n ? `<span class="up">${r.tp.buy}</span> / ${r.tp.hold} / <span class="dn">${r.tp.sell}</span>` : '—'}</td><td>${r.su ? `<span class="${cls(r.su.pct)}">${r.su.pct > 0 ? '+' : ''}${num(r.su.pct, 1)} %</span> <span class="dm">${esc(r.su.q || '')}</span>` : '—'}</td></tr>`).join('')}</tbody></table></div>`,
      { np: true, lect: 'Objectif de cours moyen, fourchette et répartition achat / conserver / vente : consensus des analystes publié. Potentiel = objectif moyen ÷ dernier cours − 1 ; « ? » en gris : objectifs publiés incohérents avec le cours (écart supérieur à +75 % ou −50 %, ou fourchette très large), à vérifier. e = date de résultats estimée d’après l’historique. Clic : recommandations (ANR).' });
    m.querySelectorAll('[data-cs]').forEach(h => h.onclick = e => { e.stopPropagation(); st.sort = h.dataset.cs; render(); }); bindQ(); return;
  }
  /* agenda : AG, détachements et paiements, opérations sur le capital (BRVM) et résultats (US), à venir sur 60 jours */
  const end = new Date(Date.now() + 60 * 864e5).toISOString().slice(0, 10), A = [];
  for (const x of ev) if (x.t && Q.by[x.t] && (x.e || '') >= today && x.e <= end && ['Assemblée générale', 'Fractionnement', 'Actions gratuites', 'Augmentation de capital avec droits', 'Avis sur une opération de capital'].includes(x.c)) A.push({ d: x.e, t: x.t, k: x.c, ti: x.ti, u: x.u, m: 'BRVM' });
  for (const x of dv) { if (x.t && x.det && x.det >= today && x.det <= end) A.push({ d: x.det, t: x.t, k: 'Détachement du dividende', ti: `${num(x.dps, 2)} XOF net par action (exercice ${x.ex || '—'}), paiement le ${fds(x.pay)}`, m: 'BRVM' }); }
  if (E) for (const [id, x] of Object.entries(E)) { const d = usD(x.ed); if (d && d >= today && d <= end && Q.by[id]) A.push({ d, t: id, k: 'Résultats trimestriels', ti: `${(x.qr || [{}])[0].fiscalEnd || ''} · BPA attendu ${(x.qr || [{}])[0].consensusEPSForecast != null ? num((x.qr || [{}])[0].consensusEPSForecast, 2) : '—'}${/after market/i.test(x.ed) ? ' · après clôture' : /before market/i.test(x.ed) ? ' · avant ouverture' : ''}`, m: 'US' }); }
  const L = A.filter(a => !q || (a.t + ' ' + a.k + ' ' + a.ti).toLowerCase().includes(q)).sort((a, b) => a.d.localeCompare(b.d) || a.t.localeCompare(b.t));
  let cur = ''; const KC = { 'Assemblée générale': '#5fd0ea', 'Détachement du dividende': '#32c74c', 'Résultats trimestriels': '#f9a33a', 'Fractionnement': '#ff7ab2' };
  m.innerHTML = tools + pn(`Agenda des sociétés · 60 prochains jours · ${L.length}`, code, `<div class="tw" style="max-height:calc(100vh - 250px - var(--nwh, 90px))"><table class="t"><tbody>${L.map((a, i) => { const hd = a.d !== cur ? `<tr class="grp"><td class="l" colspan="5">${new Date(a.d + 'T12:00:00Z').toLocaleDateString('fr-FR', { weekday: 'long', day: '2-digit', month: 'long', timeZone: 'UTC' })}</td></tr>` : ''; cur = a.d;
      return hd + `<tr data-sec="${a.t}" data-to="${a.m === 'US' ? 'EE' : 'CN'}" style="cursor:pointer"><td class="l"><span class="rn">${i + 1})</span><b class="wh">${a.t}</b></td><td class="l am">${esc((Q.by[a.t] || {}).short || (Q.by[a.t] || {}).n || '')}</td><td class="l"><b class="evb" style="background:${KC[a.k] || '#8a8a8a'}">${esc(a.k)}</b></td><td class="l">${a.u ? `<a href="${esc(a.u)}" target="_blank" rel="noopener" class="cfl">${esc(a.ti)}</a>` : esc(a.ti)}</td><td class="l dm">${a.m}</td></tr>`; }).join('') || '<tr><td class="l dm">Rien d’annoncé sur la période.</td></tr>'}</tbody></table></div>`,
    { np: true, lect: 'Assemblées et opérations sur le capital : date de l’avis officiel ; dividendes : date de détachement (il faut détenir le titre la veille) ; résultats US : date publiée (estimée quand l’historique sert de base).' });
  m.querySelectorAll('a.cfl').forEach(a => a.onclick = e => e.stopPropagation()); bindQ();
}


/* ------------------------------------------------------------------ EVTS : avis officiels BRVM (vue principale) et, en option, suivi des sociétés */
const EVTS_AVIS = PAGES.EVTS;
PAGES.EVTS = async (m, alive) => {
  if (!FN_TABS.EVTS.some(t => t[0] === ST.tab.EVTS)) ST.tab.EVTS = 'avis';
  const tab = tabState('EVTS', 'avis'); setTabs(FN_TABS.EVTS, tab, k => { ST.tab.EVTS = k; render(); });
  if (tab === 'avis') { setTitle('Corporate Events'); return EVTS_AVIS(m, alive); }
  return cfView(m, alive, tab);
};

/* ------------------------------------------------------------------ RATES (ex-BTMM) : marché monétaire US (vue principale) et, en option, anticipations de la Fed et BONDS (taux souverains mondiaux) */
PAGES.RATES = async (m, alive) => {
  const tab = tabState('RATES', 'm'); setTabs(FN_TABS.RATES, tab, k => { ST.tab.RATES = k; render(); });
  return tab === 'w' ? wbView(m, alive) : tab === 'f' ? wirpView(m, alive) : btmmView(m, alive);
};
