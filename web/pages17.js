/* ================= FQT — MOTS CLES : recherche dans tous les documents du marché, les titres, les fonctions, les obligations et les actualités ================= */
'use strict';
/* Natures de documents : libellé, couleur de la pastille */
const KW_KIND = {
  ef: ['États financiers', 'var(--up)'], ra: ['Rapport d’activité', 'var(--teal)'], rann: ['Rapport annuel', 'var(--teal)'], cac: ['Commissaires aux comptes', 'var(--teal)'],
  res: ['Résultats', 'var(--up)'], com: ['Communiqué', 'var(--cyan)'], ag: ['Assemblée générale', 'var(--violet)'], not: ['Notation', 'var(--pink)'],
  div: ['Dividende', 'var(--amber)'], obl: ['Obligation', 'var(--yel)'], oblc: ['Obligation cotée', 'var(--yel)'], ost: ['Opération sur titres', 'var(--violet)'],
  dir: ['Dirigeants', 'var(--cyan)'], boc: ['Bulletin de la cote', 'var(--dim)'], rev: ['Revue trimestrielle', 'var(--dim)'], opcvm: ['OPCVM', 'var(--dim)'],
  seance: ['Séance', 'var(--dim)'], regl: ['Réglementation', 'var(--dim)'], avis: ['Avis', 'var(--cyan)'], news: ['Actualité', 'var(--dim)'] };
/* Mots de la requête → natures cherchées (principales, voisines) et marques (D DC/BR, R rectificatif, S semestriel, T trimestriel, C consolidé).
   Les expressions les plus longues d'abord ; les mots sont comparés sans accents ni majuscules. */
const KW_SYN = [
  ['etats financiers', ['ef'], ['rann', 'cac', 'res']], ['etat financier', ['ef'], ['rann', 'cac', 'res']], ['etats financier', ['ef'], ['rann', 'cac', 'res']], ['etat financiers', ['ef'], ['rann', 'cac', 'res']],
  ['comptes annuels', ['ef'], ['rann', 'cac']], ['comptes consolides', ['ef'], ['rann'], 'C'], ['compte de resultat', ['ef'], ['res']], ['financial statements', ['ef'], ['rann']],
  ['etats de synthese', ['ef'], []], ['bilan', ['ef'], ['rann']], ['bilans', ['ef'], ['rann']], ['comptes', ['ef'], ['rann', 'cac']], ['ef', ['ef'], ['rann']], ['liasse', ['ef'], []],
  ['rapports d activites', ['ra'], ['rann']], ['rapport d activites', ['ra'], ['rann']], ['rapport d activite', ['ra'], ['rann']], ['rapports d activite', ['ra'], ['rann']],
  ['rapport activite', ['ra'], ['rann']], ['rapport activites', ['ra'], ['rann']], ['activite', ['ra'], ['rann']], ['activites', ['ra'], ['rann']],
  ['rapport semestriel', ['ra', 'rann'], ['ef'], 'S'], ['rapport trimestriel', ['ra'], ['rann'], 'T'],
  ['rapport annuel', ['rann'], ['ra', 'ef']], ['rapports annuels', ['rann'], ['ra', 'ef']], ['annual report', ['rann'], ['ra']], ['rapport de gestion', ['rann'], ['ra']],
  ['commissaires aux comptes', ['cac'], ['ef']], ['commissaire aux comptes', ['cac'], ['ef']], ['cac', ['cac'], ['ef']], ['audit', ['cac'], ['ef']],
  ['rapport', ['ra', 'rann', 'cac'], ['ef']], ['rapports', ['ra', 'rann', 'cac'], ['ef']],
  ['communique de resultats', ['res'], ['com', 'ef']], ['resultats', ['res'], ['com', 'ef', 'ra']], ['resultat', ['res'], ['com', 'ef', 'ra']], ['chiffre d affaires', ['res', 'ra'], ['com']],
  ['communiques', ['com'], ['res']], ['communique', ['com'], ['res']],
  ['assemblee generale', ['ag'], []], ['assemblees generales', ['ag'], []], ['assemblee', ['ag'], []], ['convocation', ['ag'], []], ['projet de resolutions', ['ag'], []], ['resolutions', ['ag'], []],
  ['ago', ['ag'], []], ['age', ['ag'], []], ['agm', ['ag'], []], ['ag', ['ag'], []],
  ['notation financiere', ['not'], []], ['notations', ['not'], []], ['notation', ['not'], []], ['rating', ['not'], []], ['bloomfield', ['not'], []], ['wara', ['not'], []], ['gcr', ['not'], []],
  ['calendrier de paiement', ['div'], []], ['dividendes', ['div'], ['ost']], ['dividende', ['div'], ['ost']], ['dividend', ['div'], []], ['dpa', ['div'], []],
  ['emprunts obligataires', ['obl', 'oblc'], []], ['emprunt obligataire', ['obl', 'oblc'], []], ['obligations', ['obl', 'oblc'], []], ['obligation', ['obl', 'oblc'], []],
  ['obligataire', ['obl', 'oblc'], []], ['emprunt', ['obl', 'oblc'], []], ['emprunts', ['obl', 'oblc'], []], ['bonds', ['obl', 'oblc'], []], ['bond', ['obl', 'oblc'], []],
  ['sukuk', ['obl', 'oblc'], []], ['coupon', ['obl'], ['div']], ['interets', ['obl'], []], ['remboursement', ['obl'], []],
  ['bulletin officiel de la cote', ['boc'], []], ['bulletin de la cote', ['boc'], []], ['bulletin officiel', ['boc'], []], ['bulletins', ['boc'], []], ['bulletin', ['boc'], []], ['boc', ['boc'], []], ['cote officielle', ['boc'], []],
  ['revue trimestrielle', ['rev'], []], ['revues', ['rev'], []], ['revue', ['rev'], []],
  ['operations sur titres', ['ost'], []], ['operation sur titres', ['ost'], []], ['fractionnement', ['ost'], []], ['split', ['ost'], []], ['augmentation de capital', ['ost'], []],
  ['actions gratuites', ['ost'], []], ['introduction en bourse', ['ost', 'obl'], []], ['introduction', ['ost', 'obl'], []], ['premiere cotation', ['ost', 'obl'], []], ['nouvelle cotation', ['ost', 'obl'], []], ['ipo', ['ost'], []], ['radiation', ['ost'], []], ['suspension', ['ost'], []], ['ost', ['ost'], []],
  ['changement de direction', ['dir'], []], ['nomination', ['dir'], []], ['dirigeants', ['dir'], []], ['dirigeant', ['dir'], []], ['directeur general', ['dir'], []],
  ['valeur liquidative', ['opcvm'], []], ['opcvm', ['opcvm'], []], ['fcp', ['opcvm'], []], ['sicav', ['opcvm'], []],
  ['compte rendu de seance', ['seance'], []], ['seance', ['seance', 'boc'], []],
  ['reglementation', ['regl'], []], ['instruction', ['regl'], []], ['reglement', ['regl'], []], ['circulaire', ['regl'], []],
  ['actualites', ['news'], []], ['actualite', ['news'], []], ['news', ['news'], []], ['presse', ['news'], []], ['article', ['news'], []], ['articles', ['news'], []],
  ['avis', ['avis', 'div', 'ost', 'obl'], ['ag', 'dir'], '', 'avis'],
  ['depositaire central', [], [], 'D'], ['banque de reglement', [], [], 'D'], ['dc br', [], [], 'D'], ['dcbr', [], [], 'D'], ['dc', [], [], 'D'],
  ['premier semestre', [], [], 'S'], ['1er semestre', [], [], 'S'], ['semestriels', [], [], 'S'], ['semestriel', [], [], 'S'], ['semestre', [], [], 'S'], ['s1', [], [], 'S'], ['h1', [], [], 'S'],
  ['trimestriels', [], [], 'T'], ['trimestriel', [], [], 'T'], ['trimestre', [], [], 'T'], ['t1', [], [], 'T'], ['t2', [], [], 'T'], ['t3', [], [], 'T'], ['q1', [], [], 'T'], ['q2', [], [], 'T'], ['q3', [], [], 'T'],
  ['rectificatif', [], [], 'R'], ['erratum', [], [], 'R'], ['annule et remplace', [], [], 'R'], ['consolides', [], [], 'C'], ['consolide', [], [], 'C']];
/* expressions qui fixent la nature et dont l'intitulé doit aussi parler (l'une des formes au moins) : « sukuk » = les emprunts sukuk,
   pas toutes les obligations ; « fractionnement » = aussi « dix actions nouvelles pour une ancienne » */
const KW_IPO = ['introduction', 'premiere cotation', 'admission', 'nouvelle cotation', 'inscription a la cote', 'offre publique de vente'];
const KW_ALT = { sukuk: [], fractionnement: ['split', 'actions nouvelles pour', 'nouvelles actions pour', 'nouvelles pour une'], split: ['fractionnement', 'actions nouvelles pour', 'nouvelles actions pour'],
  radiation: [], suspension: ['suspendu', 'suspendue'], 'introduction en bourse': KW_IPO, introduction: KW_IPO, ipo: KW_IPO, 'premiere cotation': KW_IPO, 'nouvelle cotation': KW_IPO,
  'augmentation de capital': ['augmentation du capital'], 'actions gratuites': ['gratuite', 'incorporation'],
  nomination: ['nomme', 'nommee', 'changement', 'direction'], 'directeur general': ['direction', 'dg', 'nomination'], 'changement de direction': ['direction', 'nomination'],
  convocation: ['convoques', 'avis de reunion'], coupon: ['interet', 'coupons'], interets: ['interet', 'coupon'], remboursement: ['amortissement'],
  bloomfield: [], wara: [], gcr: [], 'valeur liquidative': ['valeurs liquidatives'], fcp: ['fonds commun'], sicav: [], 'projet de resolutions': ['projet de resolution', 'resolutions'],
  resolutions: ['resolution'], circulaire: [], instruction: [], erratum: ['rectificatif'], liasse: [], audit: ['commissaires', 'cac', 'attestation'],
  'chiffre d affaires': ['ca'], 'compte de resultat': ['comptes de resultat'], 'calendrier de paiement': ['calendrier'] };
const KW_FLAG = { D: 'Dépositaire central (DC/BR)', R: 'Rectificatif', S: 'Semestriel', T: 'Trimestriel', C: 'Consolidé' };
const KW_GEO = new Set('cote ivoire ci senegal sn benin bn burkina faso bf mali ml niger ng togo tg guinee bissau abidjan dakar lome ouagadougou bamako niamey cotonou afrique africa'.split(' '));
/* mots de raison sociale trop courants pour désigner une société dans un intitulé */
const KW_GENERIC = new Set('societe societes banque bank cote ivoire ivoirienne ivoiriennes generale general nationale national compagnie industrie industrielle commerce groupe group holding energies energie marketing transport transports distribution internationale international africaine africain afrique africa ouest gestion services finance financiere capital'.split(' '));
/* mots qui ne désignent pas une société à eux seuls (pays, villes, « banque ») mais départagent (« boa benin », « nsia banque ») */
const KW_WEAK = new Set([...KW_GEO, ...'societe societes banque bank compagnie groupe group holding internationale international africaine africain ouest capital finance services gestion'.split(' ')]);
const KW_STOP = new Set('de des du la le les l d et a au aux en pour sur par un une the of and to in exercice exercices annee annees document documents pdf fichier fichiers sa'.split(' '));
const kwN = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[’'`]/g, ' ').replace(/[^a-z0-9]+/g, ' ').trim();
const kwToks = s => kwN(s).split(' ').filter(Boolean);
/* distance d'édition (fautes de frappe), arrêtée dès qu'elle dépasse max */
function kwLev(a, b, max) {
  if (Math.abs(a.length - b.length) > max) return max + 1; let p = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) { const c = [i]; let lo = i; for (let j = 1; j <= b.length; j++) { const v = Math.min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)); c.push(v); if (v < lo) lo = v; } if (lo > max) return max + 1; p = c; }
  return p[b.length];
}
const kwUrl = u => !u ? '' : u.startsWith('/doc/') ? u : u.startsWith('B:') ? '/doc/b/' + u.slice(2) : u.startsWith('F:') ? '/doc/f/' + u.slice(2) : /^W\d{8,14}:/.test(u) ? '' : u;
/* les mots tapés se suivent-ils dans l'intitulé (mots vides ignorés, début de mot accepté) ? */
const kwSeq = (ti, ws) => { const T = kwToks(ti).filter(x => !KW_STOP.has(x)); for (let i = 0; i + ws.length <= T.length; i++) if (ws.every((w, j) => T[i + j] === w || (w.length >= 3 && T[i + j].startsWith(w)))) return true; return false; };
/* « 2004–2011, 2014, 2023–2025 » */
const kwRange = ys => { const a = [...new Set(ys)].filter(Boolean).sort((x, y) => x - y), o = []; for (let i = 0; i < a.length;) { let j = i; while (j + 1 < a.length && a[j + 1] === a[j] + 1) j++; o.push(j > i ? a[i] + '–' + a[j] : '' + a[i]); i = j + 1; } return o.join(', '); };
const kwDate = d => { const s = String(d || ''); return s.length === 8 ? s.slice(6, 8) + '/' + s.slice(4, 6) + '/' + s.slice(0, 4) : '—'; };

/* Chargement unique : documents, actualités, obligations cotées, puis index inversé des mots */
let KW_DB = null;
async function kwLoad() {
  if (KW_DB) return KW_DB;
  const [S, N, B] = await Promise.all([getJSON('search.json').catch(() => null), getJSON('news.json').catch(() => null), getJSON('bonds.json').catch(() => null)]);
  const E = [];
  for (const r of (S && S.r) || []) E.push({ k: r[0], t: r[1] || '', y: r[2] || 0, d: r[3] || 0, ti: r[4], u: r[5], f: r[6] || '' });
  for (const x of (N && N.items) || []) { const dd = new Date(x.t * 1000); E.push({ k: 'news', t: (x.tk || [])[0] || '', y: 0, d: +dd.toISOString().slice(0, 10).replace(/-/g, ''), ti: x.ti + (x.s ? ' — ' + x.s : ''), u: x.u, f: '' }); }
  for (const b of (B && B.rows) || []) E.push({ k: 'oblc', t: '', y: b.y1 || 0, d: 0, ti: `${b.n} (${b.code})${b.iss ? ' — ' + b.iss : ''}`, u: 'bond:' + b.code, f: '', iss: b.iss || '' });
  /* sociétés : noms officiels, courants, anciens, symboles ; poids d'un mot = rareté parmi les sociétés */
  const CO = {}, add = (t, n) => { if (!t || !n) return; (CO[t] = CO[t] || new Set()).add(n); };
  for (const [t, L] of Object.entries((S && S.co) || {})) L.forEach(n => { if (!/^\W*(avis|brvm|communiques?|bulletin|rapport|societe|note|information|annonce|document)\W*$/i.test(kwN(n))) add(t, n); });
  for (const s of Q.sum.secs) if (s.mkt === 'BRVM' && s.cls === 'Equity') { add(s.id, s.short); add(s.id, s.n); }
  const COTOK = {}, DF = {};
  for (const [t, L] of Object.entries(CO)) { const set = new Set([t.toLowerCase()]); L.forEach(n => kwToks(n).forEach(w => { if (w.length > 1 && !KW_STOP.has(w)) set.add(w); })); COTOK[t] = set; }
  /* sigles des noms de société (« AGL », « BTL ») : gardés s'ils ne désignent pas déjà autre chose dans les intitulés */
  const tokOf = new Map(); E.forEach((e, i) => { for (const w of new Set(kwToks(e.ti))) { let a = tokOf.get(w); if (!a) tokOf.set(w, a = []); a.push(e.t || ''); } });
  for (const [t, L] of Object.entries(CO)) for (const n of L) {
    const ws = kwToks(n).filter(w => w.length > 2 && !KW_STOP.has(w) && !/^\d/.test(w) && !(KW_GEO.has(w) && w !== 'africa' && w !== 'afrique')); if (ws.length < 3) continue;
    const acr = ws.map(w => w[0]).join(''); if (acr.length < 3 || acr.length > 5 || COTOK[t].has(acr)) continue;
    const seen = tokOf.get(acr) || []; if (seen.filter(x => x && x !== t).length > seen.filter(x => x === t).length) continue;
    COTOK[t].add(acr);
  }
  const TT = new Map();
  for (const e of E) for (const w of new Set(kwToks(e.ti))) if (w.length >= 4 && !/\d/.test(w) && !KW_STOP.has(w)) { let m = TT.get(w); if (!m) TT.set(w, m = new Map()); m.set(e.t || '', (m.get(e.t || '') || 0) + 1); }
  /* (documents sans société non comptés : archives, avis de marché) */
  for (const [w, m] of TT) { let tot = 0, bt = '', bn = 0; for (const [t, n] of m) { if (!t) continue; tot += n; if (n > bn) { bn = n; bt = t; } } if (bt && COTOK[bt] && bn >= 3 && bn >= .75 * tot && !KW_GENERIC.has(w)) COTOK[bt].add(w); }
  for (const set of Object.values(COTOK)) set.forEach(w => { DF[w] = (DF[w] || 0) + 1; });
  const NCO = Object.keys(COTOK).length || 1;
  /* index : mot -> entrées (intitulé, symbole) */
  const IDX = new Map();
  E.forEach((e, i) => { e.tok = new Set(kwToks(e.ti)); if (e.t) e.tok.add(e.t.toLowerCase()); e.tok.forEach(w => { let a = IDX.get(w); if (!a) IDX.set(w, a = []); a.push(i); }); });
  KW_DB = { E, CO, COTOK, DF, NCO, IDX, VOC: [...IDX.keys()], n: (S && S.n) || 0, ts: S && S.ts };
  return KW_DB;
}

/* Lecture de la requête : sociétés, natures, marques, années, mots restants */
function kwParse(q, db) {
  let w = kwToks(q); const P = { co: new Map(), kinds: new Set(), near: new Set(), flags: new Set(), years: [], free: [], alts: [], avis: false, used: { co: [], kind: [], year: [] } };
  /* années (1990 à 2049), plages « 2015-2018 » */
  const ys = []; w = w.filter(x => { if (/^(199\d|20[0-4]\d)$/.test(x)) { ys.push(+x); P.used.year.push(x); return false; } return true; });
  if (ys.length === 2 && Math.abs(ys[1] - ys[0]) <= 30) { const [a, b] = ys.sort((x, y) => x - y); for (let y = a; y <= b; y++) P.years.push(y); } else P.years = ys;
  /* natures et marques : expressions les plus longues d'abord */
  const syn = KW_SYN.map(s => [s[0].split(' '), s]).sort((a, b) => b[0].length - a[0].length);
  for (let i = 0; i < w.length;) {
    const hit = syn.find(([ph]) => ph.every((p, j) => w[i + j] === p));
    if (hit) { const [ph, s] = hit; s[1].forEach(k => P.kinds.add(k)); (s[2] || []).forEach(k => P.near.add(k)); for (const c of s[3] || '') P.flags.add(c); if (s[4] === 'avis') P.avis = true; P.used.kind.push(ph.join(' ')); if (KW_ALT[s[0]]) P.alts.push([s[0], ...KW_ALT[s[0]]].map(a => a.split(' ').filter(x => !KW_STOP.has(x)))); w.splice(i, ph.length); continue; }
    i++;
  }
  /* sociétés : chaque mot cherché parmi les mots des noms de sociétés (exact, début de mot, faute de frappe) ;
     un nom de pays ou de ville ne désigne pas une société à lui seul (« etat du senegal »), il départage (« boa benin », « total senegal ») */
  const score = {}, geo = {}, best = [], thr = Math.log(1 + db.NCO / 8);
  w.forEach((x, i) => {
    best[i] = 0; if (x.length < 2 || KW_STOP.has(x)) return;
    for (const [t, set] of Object.entries(db.COTOK)) {
      let m = 0;
      for (const tok of set) {
        let v = 0;
        if (tok === x) v = 1; else if (x.length >= 4 && tok.startsWith(x)) v = .85; else if (x.length >= 5 && tok.length >= 5 && kwLev(x, tok, x.length >= 8 ? 2 : 1) <= (x.length >= 8 ? 2 : 1)) v = .75;
        if (v) { const idf = Math.log(1 + db.NCO / db.DF[tok]); if (v * idf > m) m = v * idf; }
      }
      if (m) { const S = KW_WEAK.has(x) ? geo : score; S[t] = (S[t] || 0) + m; if (m > best[i]) best[i] = m; }
    }
  });
  const nonGeo = Math.max(0, ...w.map((x, i) => KW_WEAK.has(x) ? 0 : best[i]));
  if (nonGeo >= thr) {
    const tot = {}; for (const [t, v] of Object.entries(score)) tot[t] = v + (geo[t] || 0);
    const top = Math.max(...Object.values(tot)); for (const [t, v] of Object.entries(tot)) if (v >= .8 * top) P.co.set(t, v);
  } else if (Object.keys(geo).length) {  /* (seulement des mots faibles : « bank of africa mali » désigne une société, « etat du senegal » non) */
    const top = Math.max(...Object.values(geo)), C = Object.entries(geo).filter(([, v]) => v >= .8 * top);
    if (top >= 2 * thr && C.length <= 2) C.forEach(([t, v]) => P.co.set(t, v));
  }
  const inCo = x => [...P.co.keys()].some(t => db.COTOK[t].has(x));
  w.forEach((x, i) => {
    const used = P.co.size && (KW_WEAK.has(x) ? inCo(x) : (best[i] >= thr || inCo(x)));
    if (used) P.used.co.push(x); else if (!KW_STOP.has(x) && x.length > 0) P.free.push(x);
  });
  return P;
}

/* Correspondance d'un mot avec le vocabulaire (exact, début, faute de frappe) -> Map(mot du vocabulaire -> poids) */
function kwVocab(x, db) {
  const M = new Map(); if (db.IDX.has(x)) M.set(x, 1);
  if (x.length >= 2) for (const v of db.VOC) {
    if (v === x) continue;
    if (v.startsWith(x)) { if (x.length >= 3 || /^\d/.test(x)) M.set(v, Math.max(M.get(v) || 0, .7)); }
    else if (x.length >= 5 && Math.abs(v.length - x.length) <= 2 && v[0] === x[0] && kwLev(x, v, x.length >= 8 ? 2 : 1) <= (x.length >= 8 ? 2 : 1)) M.set(v, Math.max(M.get(v) || 0, .55));
  }
  return M;
}

function kwSearch(q, db, kindFilter) {
  const P = kwParse(q, db), E = db.E, N = E.length, sc = new Float32Array(N), nfree = P.free.length;
  const anyQ = P.co.size || P.kinds.size || P.flags.size || P.years.length || nfree || P.alts.length;
  if (!anyQ) return { P, R: [], counts: {} };
  /* sociétés : entrées rattachées, ou dont l'intitulé porte le nom distinctif de la société */
  /* (mot surtout présent dans les documents de ces sociétés ; documents sans société non comptés) */
  const coHit = new Uint8Array(N), own = v => { let o = 0, n = 0; for (const i of db.IDX.get(v) || []) if (E[i].t) { n++; if (P.co.has(E[i].t)) o++; } return o >= .8 * n; };
  for (const t of P.co.keys()) {
    E.forEach((e, i) => { if (e.t === t) coHit[i] = 2; });
    /* (intitulé portant un nom distinctif de la société, « FCTC SONATEL », sauf mot courant ailleurs comme « générale ») */
    for (const w of db.COTOK[t]) if (w.length >= 4 && db.DF[w] <= 2 && !/^\d/.test(w) && !KW_GEO.has(w) && !KW_GENERIC.has(w) && own(w)) for (const i of db.IDX.get(w) || []) if (!coHit[i] && !E[i].t) coHit[i] = 1;
  }
  /* (documents sans société seulement : un document rattaché à une autre société parle d'elle) */
  if (P.co.size) for (const x of P.used.co) if (!KW_GEO.has(x) && !KW_GENERIC.has(x)) for (const [v] of kwVocab(x, db)) if (v.length >= 4 && own(v)) for (const i of db.IDX.get(v) || []) if (!coHit[i] && !E[i].t) coHit[i] = 1;
  /* mots libres */
  /* formes attendues dans l'intitulé (« sukuk », « première cotation »…) : un mot de 5 lettres ou plus vaut aussi pour ses dérivés */
  const tokDocs = new Map(), docsOf = tok => { let a = tokDocs.get(tok); if (a) return a; a = new Uint8Array(N);
    for (const v of tok.length >= 5 ? db.VOC.filter(v => v === tok || v.startsWith(tok)) : [tok]) for (const i of db.IDX.get(v) || []) a[i] = 1; tokDocs.set(tok, a); return a; };
  const altHit = P.alts.map(g => { const a = new Uint8Array(N); for (const ph of g) { const L = ph.map(docsOf); for (let i = 0; i < N; i++) if (!a[i] && L.every(x => x[i])) a[i] = 1; } return a; });
  const freeM = P.free.map(x => kwVocab(x, db)), hits = P.free.map(() => new Float32Array(N));
  freeM.forEach((M, j) => { for (const [v, wgt] of M) for (const i of db.IDX.get(v) || []) if (wgt > hits[j][i]) hits[j][i] = wgt; });
  /* palier de pertinence (critères de la requête remplis), puis le plus récent d'abord dans chaque palier */
  const yset = new Set(P.years), kinds = P.kinds, near = P.near, nowK = +new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const tierOf = (i, hard) => {
    const e = E[i]; let t = 0;
    if (P.co.size) t += coHit[i] === 2 ? 8 : coHit[i] === 1 ? 7 : hard ? -100 : -8;
    if (kinds.size) t += kinds.has(e.k) ? 6 : (P.avis && /\bavis\b/i.test(e.ti)) ? 4 : near.has(e.k) ? 2 : hard ? -100 : -6;
    for (const f of P.flags) t += e.f.includes(f) ? 4 : -6;
    if (!P.flags.has('S') && !P.flags.has('T') && (kinds.has('ef') || kinds.has('rann')) && /[ST]/.test(e.f)) t -= 1;  /* (comptes annuels avant les semestriels) */
    if (yset.size) { const dy = e.d ? Math.floor(e.d / 10000) : 0, y = e.y || (e.k === 'boc' || e.k === 'news' ? dy : 0);
      t += y && yset.has(y) ? 5 : !e.y && dy && yset.has(dy) ? 4 : y && (yset.has(y - 1) || yset.has(y + 1)) ? 0 : -3; }
    let allF = nfree > 1; for (let j = 0; j < nfree; j++) { const h = hits[j][i]; t += h >= .7 ? 3 : h ? 2 : -4; if (!h) allF = false; }
    if (allF && kwSeq(e.ti, P.free)) t += 2;  /* (mots tapés qui se suivent dans l'intitulé) */
    for (const a of altHit) t += a[i] ? 3 : -4;
    if (e.k === 'news' && !kinds.has('news')) t -= 1;  /* (publications officielles avant la presse) */
    return t;
  };
  /* date de tri : publication ; sinon exercice (publié l'année suivante) ; obligation cotée vivante : aujourd'hui */
  const when = e => e.d || (e.k === 'oblc' ? (e.y >= Math.floor(nowK / 10000) ? nowK : e.y * 10000 + 1231) : e.y ? (e.y + 1) * 10000 + 101 : 0);
  let R = [];
  for (const hard of [true, false]) {
    let top = -1e9; for (let i = 0; i < N; i++) { const t = tierOf(i, hard); sc[i] = t; if (t > top) top = t; }
    const floor = Math.max(-1e8, top - 6);
    R = []; for (let i = 0; i < N; i++) if (sc[i] >= floor && sc[i] > 0) R.push(i);  /* (au moins un critère rempli) */
    if (R.length) break;  /* (rien avec la société et la nature exactes : critères assouplis) */
  }
  R.sort((a, b) => sc[b] - sc[a] || when(E[b]) - when(E[a]) || (E[a].ti < E[b].ti ? -1 : 1));
  const counts = {}; R.forEach(i => { counts[E[i].k] = (counts[E[i].k] || 0) + 1; });
  return { P, R: kindFilter ? R.filter(i => E[i].k === kindFilter) : R, counts, all: R.length };
}

/* Titres et fonctions correspondant à la requête (accès direct) */
function kwQuick(q, P) {
  const out = [], seen = new Set(), n = kwN(q);
  for (const t of [...P.co.keys()].slice(0, 6)) if (Q.by[t] && !seen.has(t)) { seen.add(t); out.push({ s: Q.by[t] }); }
  if (!P.co.size && n.length >= 2 && !P.kinds.size) for (const s of searchSecs(q).slice(0, 4)) if (!seen.has(s.id)) { seen.add(s.id); out.push({ s }); }
  const fns = [], ws = n.split(' ').filter(x => x.length > 1 && !KW_STOP.has(x));
  if (ws.length) for (const [c, f] of Object.entries(FN)) {
    if (!has(c) || c === 'MOTS CLES') continue; const lab = kwN(f[0] + ' ' + f[4]), cn = kwN(c);
    let v = ws.includes(cn) || cn === n ? 10 : 0; ws.forEach(x => { if (x.length >= 4 && (' ' + lab + ' ').includes(' ' + x)) v += 3; });
    if (v >= 3 + (ws.length > 1 ? 3 : 0) || v >= 10) fns.push([v, c]);
  }
  fns.sort((a, b) => b[0] - a[0]);
  return { secs: out.slice(0, 6), fns: fns.slice(0, 5).map(x => x[1]) };
}

function kwHighlight(ti, P) {
  const words = new Set([...P.free, ...P.used.co, ...P.used.year, ...P.alts.flat(2)]); if (!words.size) return esc(ti);
  return esc(ti).replace(/[A-Za-zÀ-ÿ0-9]+/g, w => { const n = kwN(w); for (const x of words) if (n === x || (x.length >= 3 && n.startsWith(x))) return `<mark>${w}</mark>`; return w; });
}

/* historique des recherches (90 derniers jours) : gardé sur cet appareil seulement, jamais envoyé */
const KWH_K = 'fqt_kw_hist_v1', KWH_DAYS = 90;
function kwHistLoad() { try { const a = JSON.parse(localStorage.getItem(KWH_K) || '[]'); const lim = Date.now() - KWH_DAYS * 864e5; return Array.isArray(a) ? a.filter(x => x && x.q && x.t >= lim) : []; } catch (e) { return []; } }
function kwHistSave(a) { try { localStorage.setItem(KWH_K, JSON.stringify(a.slice(0, 1000))); } catch (e) { } }
function kwHistAdd(q, n) {
  q = String(q || '').replace(/\s+/g, ' ').trim(); if (q.length < 2) return; const a = kwHistLoad(), now = Date.now(), key = q.toLowerCase();
  /* (la même recherche relancée dans les 10 minutes met à jour la ligne au lieu d'en ajouter une) */
  const i = a.findIndex(x => x.q.toLowerCase() === key && now - x.t < 6e5); if (i >= 0) a.splice(i, 1);
  a.unshift({ q, t: now, n: n == null ? null : n }); kwHistSave(a);
}
function kwHistPage(m) {
  setTitle('Keyword Search History');
  const draw = () => {
    const a = kwHistLoad(), f = (($('kwhF') || {}).value || '').trim().toLowerCase(), L = f ? a.filter(x => x.q.toLowerCase().includes(f)) : a;
    const day = t => new Date(t).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    let last = '', rows = '';
    for (const x of L) { const d = day(x.t); if (d !== last) { rows += `<tr class="sub"><td class="l am" colspan="4">${esc(d.charAt(0).toUpperCase() + d.slice(1))}</td></tr>`; last = d; }
      rows += `<tr><td class="l">${new Date(x.t).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</td><td class="l"><a href="#" data-kwhq="${esc(x.q)}">${esc(x.q)}</a></td><td>${x.n == null ? '—' : num(x.n, 0)}</td><td><button class="tb alt" data-kwhx="${x.t}" title="Retirer cette recherche de l’historique">×</button></td></tr>`; }
    $('kwhR').innerHTML = L.length ? `<table class="t"><thead><tr><th class="l">Heure</th><th class="l">Recherche</th><th>Résultats</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
      : `<div class="empty">${a.length ? 'Aucune recherche ne contient ce texte.' : 'Aucune recherche ces 90 derniers jours.'}</div>`;
    $('kwhN').textContent = num(a.length, 0) + (a.length > 1 ? ' recherches' : ' recherche');
  };
  m.innerHTML = pn('Historique de recherche · 90 derniers jours', 'MOTS CLES', `<div class="kw"><div class="kwbar"><input id="kwhF" type="search" autocomplete="off" spellcheck="false" placeholder="Filtrer l’historique"><span id="kwhN" class="dm"></span><button class="tb alt" id="kwhC">Effacer l’historique</button></div><div id="kwhR"></div></div>`,
    { np: true, lect: 'Recherches faites dans MOTS CLES sur cet appareil ces 90 derniers jours (gardées dans ce navigateur seulement). Cliquer une recherche la relance.' });
  $('kwhF').oninput = draw;
  $('kwhC').onclick = () => { if (confirm('Effacer tout l’historique de recherche de cet appareil ?')) { kwHistSave([]); draw(); } };
  m.onclick = ev => {
    const q = ev.target.closest('[data-kwhq]'); if (q) { ev.preventDefault(); kwGo(q.dataset.kwhq); return; }
    const x = ev.target.closest('[data-kwhx]'); if (x) { kwHistSave(kwHistLoad().filter(y => String(y.t) !== x.dataset.kwhx)); draw(); }
  };
  draw();
}
PAGES['MOTS CLES'] = async (m, alive) => {
  const tab = tabState('MOTS CLES', 'r'); setTabs(FN_TABS['MOTS CLES'], tab, k => { ST.tab['MOTS CLES'] = k; render(); });
  if (tab === 'h') return kwHistPage(m);
  setTitle('Keyword Search');
  const st = ST.kw = ST.kw || { q: '', k: '', n: 60 };
  m.innerHTML = pn('Recherche par mots clés', 'MOTS CLES', `<div class="kw"><div class="kwbar"><input id="kwQ" type="search" autocomplete="off" spellcheck="false" placeholder="ex. : états financiers sonatel 2017 · rapport d'activité servair 2008 · obligation tpci · avis dcbr dividende · bulletin 15 octobre 2026" value="${esc(st.q)}"><span class="kwn" id="kwN"></span></div>
    <div id="kwI" class="kwi"></div><div id="kwA" class="kwa"></div><div id="kwF" class="chips kwf"></div><div id="kwR" class="kwr"><div class="empty">Chargement de l’index…</div></div></div>`,
    { np: true, lect: 'Tous les documents du marché connus du terminal, depuis 1998 : états financiers, rapports d’activité et annuels, rapports des commissaires aux comptes, résultats, communiqués, assemblées, notations, avis officiels, dividendes, obligations, opérations sur titres, bulletins de la cote, revues trimestrielles, documents anciens ; plus les titres, les fonctions, les obligations cotées et les actualités. Tapez une société (nom, ancien nom ou symbole), une nature de document, une année ou n’importe quel mot ; les fautes de frappe sont tolérées. Résultats du plus pertinent au moins pertinent, et dans chaque groupe du plus récent au plus ancien. Un document s’ouvre en cliquant sur son intitulé (nouvel onglet).' });
  const inp = $('kwQ'); inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length);
  const db = await kwLoad(); if (!alive()) return;
  $('kwN').textContent = num(db.n, 0) + ' documents';
  let res = null, timer = null;
  const open = e => {
    if (!e) return; if (e.u && e.u.startsWith('bond:')) { const code = e.u.slice(5); ST.srch2 = { f: { live: '', typ: 'ALL', cty: 'ALL', iss: e.iss || '', c0: '', c1: '', y0: '', y1: '', r0: '', par: 'ALL' }, sort: 'mat', dir: 1, sel: code }; go('UEMOA BONDS'); return; }
    window.open(kwUrl(e.u), '_blank', 'noopener');
  };
  const draw = () => {
    const E = db.E; st.q = inp.value;
    res = kwSearch(st.q, db, st.k); if (st.k && !res.counts[st.k]) { st.k = ''; res = kwSearch(st.q, db, ''); } const P = res.P;
    /* ce que la recherche a compris (cliquer pour retirer) */
    const chips = [];
    for (const t of P.co.keys()) chips.push([`Société : ${Q.by[t] ? esc(Q.by[t].short || Q.by[t].n) + ' (' + t + ')' : t}`, 'co']);
    const kl = [...P.kinds].filter(k => KW_KIND[k]).map(k => KW_KIND[k][0]); if (kl.length) chips.push([`Nature : ${esc(kl.join(', '))}`, 'kind']);
    for (const f of P.flags) chips.push([KW_FLAG[f], 'kind']);
    if (P.years.length) chips.push([P.years.length > 2 ? `Années ${P.years[0]}–${P.years[P.years.length - 1]}` : `Exercice ou année ${P.years.join(', ')}`, 'year']);
    if (P.free.length) chips.push([`Mots : ${esc(P.free.join(' '))}`, null]);
    $('kwI').innerHTML = chips.length ? '<span class="dm">Compris :</span> ' + chips.map(([l, k]) => `<span class="kwc"${k ? ` data-kwx="${k}" title="Retirer ce critère"` : ''}>${l}${k ? ' ×' : ''}</span>`).join('') : '';
    /* accès direct : titres et fonctions */
    const QK = st.q.trim() ? kwQuick(st.q, P) : { secs: [], fns: [] };
    $('kwA').innerHTML = (QK.secs.length || QK.fns.length) ? QK.secs.map(({ s }) => `<span class="kws"><b class="tk" data-sec="${s.id}" data-to="DES">${esc(s.id)}</b> ${esc(s.short || s.n)} ${['DES', 'GP', 'FA', 'DVD'].filter(c => has(c) && !avail(c, s)).map(c => `<button class="tb alt" data-kwsec="${s.id}" data-kwfn="${c}">${c}</button>`).join('')}</span>`).join('')
      + QK.fns.map(c => `<button class="tb" data-fn="${c}" title="${esc(FN[c][3])}"><em>${esc(c)}</em>${esc(FN[c][0])}</button>`).join('') : '';
    /* filtres par nature */
    const ks = Object.entries(res.counts).sort((a, b) => b[1] - a[1]);
    $('kwF').innerHTML = res.all ? `<button class="tb ${st.k ? 'alt' : 'on'}" data-kwk="">Tout <em>${num(res.all, 0)}</em></button>` + ks.map(([k, n]) => `<button class="tb ${st.k === k ? 'on' : 'alt'}" data-kwk="${k}">${esc((KW_KIND[k] || [k])[0])} <em>${num(n, 0)}</em></button>`).join('') : '';
    /* résultats */
    const R = res.R;
    if (!st.q.trim()) {
      const recent = E.map((e, i) => i).filter(i => E[i].k !== 'boc' && E[i].k !== 'news' && E[i].d).sort((a, b) => E[b].d - E[a].d).slice(0, 25);
      $('kwR').innerHTML = `<div class="kwh">Exemples : ${['états financiers sonatel 2017', 'rapport d’activité servair 2008', 'obligation tpci', 'avis dcbr dividende 2016', 'bulletin de la cote 2 août 2017', 'notation boa', 'fractionnement', 'assemblée générale orange 2024'].map(x => `<button class="tb alt" data-kwq="${esc(x)}">${esc(x)}</button>`).join(' ')}</div>
        <table class="t kwt"><thead><tr><th class="l">Date</th><th class="l">Nature</th><th class="l">Société</th><th class="l">Derniers documents publiés</th><th>Exercice</th></tr></thead><tbody>${recent.map(i => kwRow(E[i], i, null)).join('')}</tbody></table>`;
      res.R = recent; return;
    }
    const e0 = R.length ? E[R[0]] : null, y0 = e0 ? (e0.y || Math.floor((e0.d || 0) / 10000)) : 0;
    /* (le premier résultat ne répond pas à tout : on le dit) */
    const yOk = !P.years.length || P.years.includes(y0), kOk = !P.kinds.size || P.kinds.has(e0 && e0.k), cOk = !P.co.size || (e0 && P.co.has(e0.t));
    const what = [P.kinds.size ? '« ' + [...P.kinds].filter(k => KW_KIND[k]).map(k => KW_KIND[k][0]).slice(0, 2).join(' / ') + ' »' : 'document',
      P.years.length ? (P.years.length > 2 ? P.years[0] + '–' + P.years[P.years.length - 1] : P.years.join(', ')) : '',
      P.co.size ? 'de ' + [...P.co.keys()].map(t => Q.by[t] ? (Q.by[t].short || Q.by[t].n) : t).join(', ') : ''].filter(Boolean).join(' ');
    let note = e0 && !(yOk && kOk && cOk) ? `<div class="kwh">Aucun ${esc(what)} parmi les documents connus du terminal : voici les plus proches.</div>` : '';
    if (P.co.size === 1 && P.kinds.has('ef')) {  /* (exercices dont les états financiers sont publiés sous ce nom, et où trouver les autres) */
      const t = [...P.co.keys()][0], D = E.filter(e => e.t === t && e.y && !/[ST]/.test(e.f)), efY = new Set(D.filter(e => e.k === 'ef').map(e => e.y));
      const alt = k => kwRange(D.filter(e => e.k === k && !efY.has(e.y)).map(e => e.y)), nm = Q.by[t] ? (Q.by[t].short || Q.by[t].n) : t;
      note += `<div class="kwh">États financiers annuels de ${esc(nm)} déposés à la BRVM : ${efY.size ? 'exercices ' + kwRange([...efY]) : 'aucun sous ce nom'}`
        + (alt('rann') ? ` · autres exercices dans les rapports annuels : ${alt('rann')}` : '') + (alt('res') ? ` · dans les résultats annuels publiés : ${alt('res')}` : '') + '.</div>';
    }
    $('kwR').innerHTML = note + (R.length ? `<table class="t kwt"><thead><tr><th class="l">Date</th><th class="l">Nature</th><th class="l">Société</th><th class="l">Intitulé</th><th>Exercice</th></tr></thead><tbody>${R.slice(0, st.n).map(i => kwRow(E[i], i, P)).join('')}</tbody></table>`
      + (R.length > st.n ? `<div class="pager"><button class="tb alt" id="kwMore">Afficher ${num(Math.min(60, R.length - st.n), 0)} de plus</button><span>${num(st.n, 0)} sur ${num(R.length, 0)}</span></div>` : '')
      : `<div class="empty">Aucun document ne correspond. Essayez moins de mots, un autre nom de la société ou une autre année.</div>`);
    const mb = $('kwMore'); if (mb) mb.onclick = () => { st.n += 60; draw(); };
  };
  const kwRow = (e, i, P) => `<tr data-kwi="${i}"><td class="l">${kwDate(e.d)}</td><td class="l"><span class="kwk" style="--c:${(KW_KIND[e.k] || ['', 'var(--dim)'])[1]}">${esc((KW_KIND[e.k] || [e.k])[0])}</span>${e.f.includes('D') ? ' <span class="dm" title="Dépositaire central / Banque de règlement">DC/BR</span>' : ''}${e.f.includes('A') ? ' <span class="dm" title="Document ancien">archive</span>' : ''}</td>
    <td class="l tk"${e.t && Q.by[e.t] ? ` data-sec="${e.t}" data-to="DES"` : ''}>${e.t || '—'}</td><td class="l kwti"><a href="${esc(e.u && e.u.startsWith('bond:') ? '#UEMOA BONDS' : kwUrl(e.u))}" target="_blank" rel="noopener" data-kwo="${i}">${P ? kwHighlight(e.ti, P) : esc(e.ti)}</a></td><td>${e.y || '—'}</td></tr>`;
  let htimer = null; const rec = () => { clearTimeout(htimer); if (st.q && st.q.trim()) kwHistAdd(st.q, res && res.R ? res.R.length : null); };
  inp.oninput = () => { st.n = 60; clearTimeout(timer); timer = setTimeout(draw, 90); clearTimeout(htimer); htimer = setTimeout(rec, 2500); };
  /* Entrée lance la recherche (aucun document ne s'ouvre seul : on clique sur l'intitulé) */
  inp.onkeydown = ev => {
    if (ev.key === 'Enter') { ev.preventDefault(); clearTimeout(timer); draw(); rec(); try { if (matchMedia('(pointer: coarse)').matches) inp.blur(); } catch (e) { } }
    else if (ev.key === 'Escape') { inp.value = ''; draw(); }
  };
  m.onclick = ev => {
    const a = ev.target.closest('[data-kwo]'); if (a) { rec(); const e = db.E[+a.dataset.kwo]; if (e && e.u && e.u.startsWith('bond:')) { ev.preventDefault(); open(e); } return; }
    const k = ev.target.closest('[data-kwk]'); if (k) { st.k = k.dataset.kwk; st.n = 60; draw(); return; }
    const qx = ev.target.closest('[data-kwq]'); if (qx) { inp.value = qx.dataset.kwq; st.k = ''; draw(); rec(); inp.focus(); return; }
    const x = ev.target.closest('[data-kwx]'); if (x && res) { const P = res.P, drop = new Set(x.dataset.kwx === 'co' ? P.used.co : x.dataset.kwx === 'kind' ? P.used.kind.flatMap(p => p.split(' ')) : P.used.year);
      inp.value = kwToks(inp.value).filter(w => !drop.has(w)).join(' '); st.k = ''; draw(); inp.focus(); return; }
    const sf = ev.target.closest('[data-kwfn]'); if (sf) { go(sf.dataset.kwfn, sf.dataset.kwsec); }
  };
  draw(); if (st.rec) { st.rec = false; rec(); }
};
