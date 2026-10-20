/* ================= FQT — données, formats, ligne de commande, chrome Bloomberg, routeur ================= */
'use strict';
const $ = id => document.getElementById(id);
const Q = { base: 'data/', sum: null, by: {}, ser: {}, M: {}, json: {}, live: null, quotes: null };
const ST = { fn: 'MONITOR', sec: 'QQQ', gp: { range: '1A', type: 'bbg', ov: { sma50: false, sma200: false }, st: { vol: true }, log: false, cmp: [] }, corr: { u: 'BRVMW', win: 104, pair: null },
  brvm: { sort: { k: 'mcap', dir: -1 }, sector: 'ALL' }, dvd: { sort: { k: 'yldc', dir: -1 } }, ev: { cat: '', tk: '', q: '', page: 0 }, bt: null, qlab: {}, tab: {}, hist: [], hpos: -1, newsMin: false };

/* Registre des fonctions : code -> [libellé, portée (sec = titre, mkt = marché), groupe, définition courte, titre Bloomberg]
   Les définitions suivent celles de l'autocomplétion Bloomberg (nom anglais de la fonction + ce qu'elle montre). */
const FN = {
  'MOTS CLES': ['Recherche par mots clés', 'mkt', 'Recherche', 'Tous les documents du marché depuis 1998 (états financiers, rapports, avis officiels, bulletins de la cote, dividendes, notations), obligations, titres, fonctions et actualités', 'Keyword Search'],
  BRIEF: ['Synthèse du jour', 'mkt', 'Marchés', 'BRVM, portefeuille, alertes, marchés mondiaux, changes, matières, taux, agenda du jour et actualités sur une page', 'Daily Briefing'],
  MONITOR: ['Moniteur de marchés', 'mkt', 'Marchés', 'Tous les titres suivis, signal SMA 200 de QQQ, séance BRVM, carte des capitalisations', 'Market Monitor'],
  BRVM: ['BRVM', 'mkt', 'Marchés', '48 actions, indices, largeur du marché, secteurs ; en option : flottant officiel, valorisation du marché (PER), saison des résultats, publications attendues et retards, exposition par pays', 'BRVM Overview'],
  MAP: ['Carte de chaleur', 'mkt', 'Marchés', 'BRVM, États-Unis, Europe, Royaume-Uni, Asie, Afrique : surface = variation du jour (ou égale, ou capitalisation), couleur = variation, zoom et déplacement ; en option : marché US (Nasdaq-100, ETF, facteurs, crypto)', 'Intraday Market Map'],
  NEWS: ['Actualités', 'mkt', 'Actualités', 'Fil d’actualités relié aux titres : BRVM, UEMOA, marchés mondiaux, banques centrales', 'Top News'],
  FG: ['Fear & Greed', 'mkt', 'Sentiment', 'Indice peur/avidité : États-Unis (CNN, toutes les 15 minutes) et BRVM (calculé par FQT)', 'Fear & Greed Index'],
  'NEWS ECO': ['Calendrier éco', 'mkt', 'Macro', 'Calendrier économique mondial : publications, prévision du consensus, réel, précédent, importance', 'Economic Calendars'],
  ECWB: ['Macro US', 'mkt', 'Macro', 'Courbe des taux, crédit, liquidité, emploi, inflation, récession', 'US Economic Indicators'],
  'UEMOA/DATA': ['Macro UEMOA', 'mkt', 'Macro', 'Taux directeurs, inflation, croissance, dette, crédit, titres publics des 8 États ; en option : statistiques économiques mondiales', 'WAEMU Economic Dashboard'],
  'UEMOA BONDS': ['Obligations UEMOA', 'mkt', 'Taux', 'Obligations cotées à la BRVM : coupon, échéance, cours, rendement, duration, sensibilité', 'Fixed Income Search'],
  GC: ['Courbes souveraines', 'mkt', 'Taux', 'Courbes des taux zéro-coupon des 8 États de l’UEMOA, écarts, coupons à l’émission', 'Graph Curves'],
  BMAP: ['Carte du pétrole', 'mkt', 'Matières premières', 'Flux pétroliers mondiaux, détroits stratégiques, Brent et WTI, stocks US', 'Oil Flow Map'],
  MACRO: ['Macro & Or', 'mkt', 'Macro', 'Or depuis 1833, krachs, CAPE, inflation, pétrole, VIX', 'Macro & Gold'],
  FX: ['Changes', 'mkt', 'Changes', 'Franc CFA : USD/XOF, effet de change, simulateur ; en option : changes croisés (G10, Afrique, Asie, Amériques), classement mondial des devises', 'FX Monitor'],
  CORR: ['Corrélations', 'mkt', 'Quant', 'Matrice BRVM × monde, paire au choix, ACP', 'Correlation Matrix'],
  RRG: ['Rotation (RRG)', 'mkt', 'Quant', 'Graphe de rotation relative : secteurs, facteurs, pays, BRVM', 'Relative Rotation Graph'],
  PORTF: ['Portefeuille', 'mkt', 'Portefeuille', 'Vos positions BRVM et US : valeur, plus-values, risque (volatilité, VaR, bêta, contributions), performance, dividendes à venir ; import de relevés (Excel, CSV, PDF, photo) avec écran de contrôle, sauvegarde et restauration', 'Portfolio & Risk Analytics'],
  SCREENER: ['Screener', 'mkt', 'Fondamentaux', 'Filtrer US et BRVM par ratios : FCF, croissance, qualité, valorisation, score', 'Equity Screening'],
  LIQ: ['Liquidité BRVM', 'mkt', 'Marchés', 'Montants échangés, jours cotés, Amihud, délai pour constituer une position', 'Market Liquidity'],
  'CORP RESULT': ['Résultats des sociétés', 'mkt', 'Fondamentaux', 'Calendrier des résultats US (date, consensus, dernière surprise), résultats publiés (surprise, réaction du cours) ; en option : objectifs de cours des analystes', 'Earnings Analysis'],
  ALRT: ['Alertes', 'mkt', 'Fondamentaux', 'Marges, FCF, dette, révisions, seuils de valorisation, résultats à venir', 'Alert Monitor'],
  DIVC: ['Calendrier dividendes', 'mkt', 'Fondamentaux', 'BRVM : prochains détachements, classement par rendement, historique ; en option : aristocrates du dividende, dividende net et encaissements de vos positions', 'Dividend Calendar'],
  BANK: ['Banques cotées', 'mkt', 'Fondamentaux', 'Les banques cotées à la BRVM côte à côte : PNB, résultat, coefficient d’exploitation, coût du risque, rentabilité, solidité du bilan ; en option : historique sur 10 ans', 'BRVM Bank Dashboard'],
  NOT: ['Notations financières', 'mkt', 'Taux', 'Notes de crédit (Bloomfield, WARA, GCR) : sociétés cotées, emprunts obligataires et fonds de titrisation, historique', 'Credit Ratings'],
  SGI: ['Intervenants du marché', 'mkt', 'Marchés', 'SGI, sociétés de gestion d’OPCVM et de patrimoine, conservateurs, agences de notation, garants : adresses et contacts', 'Market Intermediaries'],
  EVTS: ['Événements des sociétés', 'mkt', 'Actualités', 'Avis officiels depuis 2000 : AG, dividendes, états financiers ; en option : suivi des sociétés BRVM, agenda des sociétés (BRVM et résultats US)', 'Corporate Events'],
  INDX: ['Indices mondiaux', 'mkt', 'Marchés', 'Indices boursiers des Amériques, d’Europe, d’Afrique et d’Asie : niveau, variation, fourchette 52 semaines ; en option : contrats à terme sur indices (indication d’ouverture)', 'World Equity Indices'],
  COMMO: ['Matières premières', 'mkt', 'Matières premières', 'Énergie, métaux, agriculture (cacao, café, coton) : contrats à terme du jour', 'Global Commodity Prices'],
  RATES: ['Taux : Trésor, monétaire, Fed', 'mkt', 'Taux', 'Taux directeurs (Fed, BCE, BCEAO), SOFR, bons et emprunts du Trésor, contrats à terme, pentes, inflation anticipée ; en option : anticipations de la Fed (Fed funds), BONDS (taux souverains mondiaux : courbe US, 10 ans, UEMOA)', 'Treasury & Money Markets'],
  MOST: ['Plus actives', 'mkt', 'Marchés', 'Plus fortes hausses et baisses, valeurs les plus échangées sur la séance du jour, largeur du marché', 'Most Active Securities'],
  HELP: ['Aide', 'mkt', 'Aide', 'Toutes les fonctions, leurs onglets et les raccourcis', 'Help'],
  MENU: ['Menu du titre', 'sec', 'Titre', 'Toutes les fonctions disponibles pour ce titre, classées par thème', 'Security Menu'],
  DES: ['Description', 'sec', 'Description', 'Profil, émission, ratios, chiffre d’affaires et BPA, secteur : la fiche d’identité du titre', 'Security Description'],
  CN: ['Actualités de la société', 'sec', 'Description', 'Articles qui citent la société, publications officielles, historique des événements', 'Company News'],
  HDS: ['Actionnariat', 'sec', 'Description', 'Principaux actionnaires, répartition du capital et flottant', 'Holdings: Current'],
  'STOCK BONDS': ['Titres liés', 'sec', 'Description', 'Obligations de l’émetteur cotées à la BRVM, indices, sociétés du même secteur', 'Stock & Bonds'],
  CACS: ['Opérations sur titres', 'sec', 'Description', 'Dividendes, assemblées, opérations sur le capital, à venir et passées', 'Corporate Action Calendar'],
  GP: ['Graphique', 'sec', 'Cours', 'Ligne style Bloomberg, bougies, moyennes mobiles, volume, RSI, MACD, comparaison', 'Line Chart'],
  TECH: ['Analyse technique', 'sec', 'Cours', 'Moyennes mobiles, RSI, MACD, stochastique, Bollinger, ATR, pivots, synthèse des signaux', 'Technical Analysis'],
  HVT: ['Volatilité historique', 'sec', 'Cours', 'Volatilité sur 10 à 260 séances, Parkinson, centiles, volatilité glissante', 'Historical Volatility Table'],
  VAP: ['Volume par prix', 'sec', 'Cours', 'Échanges par niveau de cours, prix le plus échangé, zone de valeur, VWAP', 'Volume at Price'],
  GF: ['Graphique des fondamentaux', 'sec', 'Fondamentaux', 'Chiffre d’affaires, résultat, BPA, FCF, dette par exercice, PER historique', 'Graph Fundamentals'],
  ANR: ['Recommandations', 'sec', 'Analystes', 'Achat / conserver / vente, objectifs de cours, potentiel, BPA attendu', 'Analyst Recommendations'],
  MEMB: ['Composition de l’indice', 'sec', 'Indice', 'Valeurs de l’indice, poids, concentration', 'Member Weightings'],
  MOV: ['Contributions à l’indice', 'sec', 'Indice', 'Valeurs qui font monter ou baisser l’indice aujourd’hui, en points', 'Equity Index Movers'],
  HP: ['Historique des cours', 'sec', 'Cours', 'Cours quotidiens, hebdomadaires, mensuels avec variations et volumes', 'Historical Price Table'],
  TRA: ['Rendement total', 'sec', 'Cours', 'Dividendes réinvestis contre cours seul, par période et par année', 'Total Return Analysis'],
  HS: ['Écart historique', 'sec', 'Cours', 'Rapport ou écart entre deux titres : moyenne, bandes ±1 et ±2 écarts-types, score z, centile, demi-vie', 'Historical Spread'],
  COMP: ['Rendements comparés', 'sec', 'Cours', 'Performance contre d’autres titres et un indice, dividendes réinvestis', 'Comparative Returns'],
  SEAS: ['Saisonnalité', 'sec', 'Cours', 'Rendements années × mois, jour de la semaine, « Sell in May »', 'Seasonality Chart'],
  FA: ['Analyse financière', 'sec', 'Fondamentaux', 'Chiffres clés, compte de résultat, bilan, flux et ratios ; BRVM : états financiers publiés poste par poste et une centaine de ratios sur tout l’historique', 'Financial Analysis'],
  RV: ['Valorisation relative', 'sec', 'Fondamentaux', 'Multiples contre pairs du secteur et contre son propre historique, juste valeur', 'Relative Valuation'],
  WACC: ['Coût du capital', 'sec', 'Fondamentaux', 'WACC, ROIC et création de valeur (ROIC − WACC)', 'Weighted Average Cost of Capital'],
  DVD: ['Dividendes', 'sec', 'Fondamentaux', 'Historique, rendement, croissance, taux de distribution, couverture par le FCF', 'Dividend/Split Summary'],
  DDM: ['Modèle de dividendes', 'sec', 'Fondamentaux', 'Gordon-Shapiro, croissance implicite, sensibilité', 'Dividend Discount Model'],
  MODL: ['Scénarios bull/base/bear', 'sec', 'Fondamentaux', 'Simulateur de valorisation : hypothèses modifiables, séparées des données publiées', 'Scenario Valuation Model'],
  EE: ['Estimations', 'sec', 'Analystes', 'Consensus du BPA, révisions, croissance attendue', 'Earnings & Estimates'],
  SURP: ['Surprises de résultats', 'sec', 'Analystes', 'BPA publié contre consensus, réaction du cours', 'Earnings Surprise'],
  SCOR: ['Score multifactoriel', 'sec', 'Quant', 'Note /100 : value, qualité, croissance, momentum, rendement, faible volatilité', 'Multi-Factor Score'],
  LQA: ['Liquidité et coûts', 'sec', 'Quant', 'Échanges 20/60 séances, séances sans échange, coût d’aller-retour, délai de sortie, taille de position', 'Liquidity Assessment'],
  ANOM: ['Anomalies', 'sec', 'Quant', 'Alertes statistiques : cours, volume, tendance, résultats, dividendes, données suspectes', 'Anomaly Monitor'],
  PEER: ['Comparateur de sociétés', 'sec', 'Quant', '2 à 10 sociétés côte à côte, nuage de points sur deux critères', 'Peer Comparison'],
  BETA: ['Bêta historique', 'sec', 'Risque', 'Bêta sur plusieurs fenêtres, volatilité, corrélation, drawdown, pairs', 'Historical Beta'],
  QLAB: ['Laboratoire quant', 'sec', 'Risque', 'Statistiques du cours (distribution, VaR, Hurst, momentum, analogues, probabilité bayésienne) ; valorisation des actions BRVM par sept modèles, risques et alertes, qualité et facteurs', 'Quant Lab'],
  BTST: ['Backtest', 'sec', 'Risque', '8 stratégies, levier, Monte Carlo, durée des drawdowns', 'Backtesting'],
};
/* touches de marché : BRIEF, puis les fonctions de la BRVM et de l'UEMOA, puis les autres marchés */
const MKT_BRVM = ['BRVM', 'MOST', 'LIQ', 'DIVC', 'BANK', 'EVTS', 'NOT', 'MOTS CLES', 'SGI', 'UEMOA BONDS', 'GC', 'UEMOA/DATA'];
const MKT_KEYS = ['BRIEF'].concat(MKT_BRVM, ['PORTF', 'SCREENER', 'ALRT', 'MAP', 'INDX', 'FG', 'NEWS ECO', 'ECWB', 'RATES', 'FX', 'COMMO', 'BMAP', 'MACRO', 'CORR', 'RRG', 'CORP RESULT', 'HELP']);
const MENU_GROUPS = [['Description', ['DES', 'CN', 'HDS', 'STOCK BONDS', 'CACS']], ['Graphiques et cours', ['GP', 'HP', 'TECH', 'TRA', 'COMP', 'HS', 'SEAS', 'HVT', 'VAP']], ['Fondamentaux', ['FA', 'GF', 'RV', 'WACC', 'DVD', 'DDM', 'MODL']],
  ['Analystes', ['ANR', 'EE', 'SURP']], ['Composition de l’indice', ['MEMB', 'MOV']], ['Quant', ['SCOR', 'LQA', 'ANOM', 'PEER']], ['Risque', ['BETA', 'QLAB', 'BTST']]];
const SEC_TABS = MENU_GROUPS.flatMap(g => g[1]);
/* Fonctions associées (menu « Fonctions associées » de la barre d'outils) */
const REL = { GP: ['HP', 'TECH', 'TRA', 'COMP', 'BETA', 'SEAS', 'QLAB'], TECH: ['GP', 'HVT', 'VAP', 'SEAS', 'BTST'], HS: ['COMP', 'CORR', 'BETA', 'GP'], HP: ['GP', 'TRA', 'COMP'], DES: ['GP', 'FA', 'HDS', 'CN', 'DVD', 'RV'], FA: ['RV', 'WACC', 'DVD', 'EE', 'MODL', 'SCOR'], RV: ['FA', 'PEER', 'SCOR', 'MODL', 'DDM'],
  DVD: ['DDM', 'TRA', 'DIVC', 'FA'], TRA: ['GP', 'DVD', 'COMP'], SCOR: ['RV', 'FA', 'LQA', 'ANOM', 'PEER', 'SCREENER'], LQA: ['LIQ', 'SCOR', 'HP'], ANOM: ['GP', 'LQA', 'CN', 'ALRT'], PEER: ['RV', 'SCOR', 'COMP', 'SCREENER'],
  MODL: ['FA', 'RV', 'DDM', 'WACC'], HDS: ['DES', 'CN'], CN: ['DES', 'NEWS', 'EVTS'], BRVM: ['MOST', 'LIQ', 'DIVC', 'MAP', 'SCREENER', 'SGI'], MAP: ['MONITOR', 'INDX', 'BRVM'], 'UEMOA/DATA': ['GC', 'UEMOA BONDS', 'FX'], 'UEMOA BONDS': ['NOT', 'GC', 'UEMOA/DATA'], NOT: ['UEMOA BONDS', 'STOCK BONDS', 'DES'], SGI: ['BRVM', 'NOT', 'HELP'], GC: ['UEMOA BONDS', 'UEMOA/DATA'],
  BMAP: ['COMMO', 'MACRO', 'NEWS ECO', 'NEWS'], NEWS: ['CN', 'EVTS'], INDX: ['MAP', 'MOST', 'RATES', 'COMMO'], COMMO: ['BMAP', 'INDX', 'MACRO'], MOST: ['BRVM', 'LIQ', 'MAP', 'INDX'], LIQ: ['MOST', 'BRVM', 'LQA'], DIVC: ['BRVM', 'EVTS', 'DVD', 'PORTF'], BANK: ['FA', 'PEER', 'BRVM', 'DIVC'], EVTS: ['DIVC', 'NOT', 'NEWS'],
  HVT: ['GP', 'BETA', 'QLAB', 'VAP'], VAP: ['GP', 'HP', 'LQA'], GF: ['FA', 'RV', 'DVD'], ANR: ['EE', 'SURP', 'RV'], 'STOCK BONDS': ['PEER', 'UEMOA BONDS', 'DES'], CACS: ['DVD', 'CN', 'EVTS'], MEMB: ['MOV', 'MAP', 'GP'], MOV: ['MEMB', 'MAP', 'MOST'],
  'NEWS ECO': ['ECWB', 'RATES', 'UEMOA/DATA', 'NEWS'], ECWB: ['NEWS ECO', 'RATES', 'MACRO'], PORTF: ['SCREENER', 'CORR', 'DIVC', 'FX'], 'CORP RESULT': ['EE', 'SURP', 'ANR', 'NEWS ECO'], BRIEF: ['MONITOR', 'PORTF', 'NEWS ECO', 'NEWS'], RATES: ['GC', 'UEMOA BONDS', 'ECWB', 'NEWS ECO'], FX: ['UEMOA/DATA', 'INDX', 'MACRO'], FG: ['MAP', 'INDX', 'BRVM'], SCREENER: ['PORTF', 'BRVM', 'ALRT'] };
const has = c => !!(FN[c] && PAGES[c]);
const SECFN = new Set(Object.keys(FN).filter(k => FN[k][1] === 'sec'));
/* Pourquoi une fonction n'est pas disponible pour un titre (null = disponible). */
function avail(code, s) {
  if (!s) return 'aucun titre';
  const eq = s.cls === 'Equity' && s.typ !== 'ETF', brvm = s.mkt === 'BRVM';
  if (['FA', 'RV', 'WACC', 'MODL'].includes(code)) return eq ? (brvm || s.fa ? null : 'comptes non disponibles pour ce titre') : 'réservé aux actions';
  if (['EE', 'SURP'].includes(code)) return brvm ? 'aucun consensus d’analystes public pour la BRVM' : s.mkt === 'US' && eq ? (s.ee === false ? 'pas de consensus publié pour ce titre' : null) : 'réservé aux actions US';
  if (code === 'DVD' || code === 'DDM') return s.cls === 'Equity' || s.typ === 'ETF' ? null : 'pas de dividende';
  if (code === 'BTST' || code === 'QLAB' || code === 'ANOM') return s.f === 'D' ? null : 'série mensuelle';
  if (code === 'HDS') return eq && (brvm || s.mkt === 'US') ? null : eq ? 'actionnariat non publié pour ce marché' : 'réservé aux actions';
  if (code === 'SCOR' || code === 'PEER') return eq && (brvm || s.fa) ? null : 'réservé aux actions dont les comptes sont disponibles';
  if (code === 'LQA') return s.cls === 'Equity' && s.f === 'D' ? null : 'réservé aux actions et ETF';
  if (code === 'TRA' || code === 'HVT' || code === 'VAP' || code === 'TECH' || code === 'HS') return s.f === 'D' ? null : 'série mensuelle';
  if (code === 'ANR') return s.mkt === 'US' && eq ? null : brvm ? 'aucune recommandation d’analystes publiée pour la BRVM' : 'réservé aux actions US';
  if (code === 'GF') return eq && (brvm || s.fa) ? null : 'réservé aux actions dont les comptes sont disponibles';
  if (code === 'CACS') return s.cls === 'Equity' ? null : 'réservé aux actions et ETF';
  if (code === 'MEMB' || code === 'MOV') return ['BRVMC', 'QQQ', 'NDX'].includes(s.id) ? null : 'composition connue pour le BRVM Composite et le Nasdaq-100 (QQQ)';
  return null;
}
/* « SNTS BC Equity », « XAU Curncy »… : le libellé de la case orange */
function ykey(s) { if (!s) return ''; return /\b(Equity|Index|INDX|Curncy|Comdty|Govt|Corp)\b/.test(s.tk) ? s.tk : s.tk + ' ' + (s.cls === 'Equity' ? 'Equity' : s.cls === 'Crypto' ? 'Curncy' : s.cls === 'Rate' ? 'Index' : s.cls); }

const TRIGGER_ID = '__TRIGGER_ID__';
/* Icônes de l'interface dessinées en SVG : jamais d'émoji (un iPhone affiche les triangles et pictogrammes Unicode en images de couleur). */
const ICO = (() => {
  const s = d => `<svg class="ic" viewBox="0 0 16 16" width="1em" height="1em" aria-hidden="true" focusable="false">${d}</svg>`;
  const ln = 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"';
  return {
    prev: s(`<path d="M10.5 2.5 5 8l5.5 5.5" ${ln}/>`),
    next: s(`<path d="M5.5 2.5 11 8l-5.5 5.5" ${ln}/>`),
    play: s('<path d="M4 2.2v11.6L13.6 8z" fill="currentColor"/>'),
    gear: s('<circle cx="8" cy="8" r="3.4" fill="none" stroke="currentColor" stroke-width="2.2"/>' + [0, 45, 90, 135, 180, 225, 270, 315].map(a => `<rect x="6.9" y=".6" width="2.2" height="3.6" rx=".5" fill="currentColor" transform="rotate(${a} 8 8)"/>`).join('')),
    bell: s('<path d="M8 1.4c-2.6 0-4.1 2-4.1 4.4v2.9L2.4 11v1.1h11.2V11l-1.5-2.3V5.8c0-2.4-1.5-4.4-4.1-4.4z" fill="currentColor"/><circle cx="8" cy="13.7" r="1.5" fill="currentColor"/>')
  };
})();

/* ---------- formats (conventions françaises) ---------- */
const NF = {}; const nf = d => NF[d] || (NF[d] = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: d, maximumFractionDigits: d }));
const num = (v, d = 2) => v == null || !isFinite(v) ? '—' : nf(d).format(v).replace(/ /g, ' ');
const pxd = s => s && (s.ccy === 'XOF' && s.cls === 'Equity') ? 0 : s && s.last < 1 ? 4 : 2;
const px = (s, v) => num(v, pxd(s));
const sgn = (v, d = 2, suf = '%', mul = 100) => v == null || !isFinite(v) ? '<span class="fl">—</span>' : `<span class="${v > 0 ? 'up' : v < 0 ? 'dn' : 'fl'}">${v > 0 ? '+' : ''}${num(v * mul, d)}${suf}</span>`;
const pc = (v, d = 2) => sgn(v, d);
const big = v => { if (v == null || !isFinite(v)) return '—'; const a = Math.abs(v); return a >= 1e12 ? num(v / 1e12, 2) + ' T' : a >= 1e9 ? num(v / 1e9, 1) + ' Md' : a >= 1e6 ? num(v / 1e6, 1) + ' M' : a >= 1e3 ? num(v / 1e3, 1) + ' k' : num(v, 0); };
const fd = d => d ? fmtD(d) : '—';
const fds = s => s ? s.slice(8, 10) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4) : '—';
const i2s = d => `${Math.floor(d / 10000)}-${String(Math.floor(d / 100) % 100).padStart(2, '0')}-${String(d % 100).padStart(2, '0')}`;
const s2i = s => +s.replace(/-/g, '');
const cls = v => v > 0 ? 'up' : v < 0 ? 'dn' : 'fl';
const deent = s => { if (s == null) return ''; s = String(s); if (!/&[#a-z0-9]+;/i.test(s)) return s; const t = document.createElement('textarea'); t.innerHTML = s; return t.value; };

/* ---------- données ---------- */
async function getJSON(path) { pfRec(path); if (!Q.json[path]) Q.json[path] = fetch(Q.base + path, { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error(path + ' ' + r.status); return r.json(); }); return Q.json[path]; }
async function series(id) {
  if (!Q.ser[id]) Q.ser[id] = getJSON('s/' + id.replace('.', '_') + '.json').then(b => {
    const n = b.d.length; const s = { id, f: b.f, x: b.d, d: b.d.map(i2s), c: b.c, o: b.o || b.c, h: b.h || b.c, l: b.l || b.c, v: b.v || new Array(n).fill(0), val: b.val || null, div: b.div || new Array(n).fill(0) };
    applyQuoteToSeries(s); return s; });
  return Q.ser[id];
}
/* marché d'un titre : dividendes de la série ou, pour la BRVM, dividendes nets de la base officielle à la date de détachement */
async function marketDivs(id, s) { let div = s.div && s.div.some(v => v) ? s.div.slice() : new Array(s.c.length).fill(0); const q = Q.by[id];
  if (q && q.mkt === 'BRVM' && q.cls === 'Equity') { const DV = await getJSON('dividends.json').catch(() => []); for (const x of DV) { if (x.t !== id || !x.dps) continue; const d = x.det || x.pay; if (!d) continue; const k = s.x.findIndex(v => v >= s2i(d.slice(0, 10))); if (k > 0) div[k] += x.dps; } }
  return div; }
/* mode : rien = dividendes de la série (inchangé) ; 'nodiv' = cours seul ; 'tr' = rendement total (BRVM : dividendes officiels ajoutés) */
async function market(id, mode) { const key = mode ? id + '|' + mode : id; if (!Q.M[key]) { const s = await series(id); const div = mode === 'nodiv' ? new Array(s.c.length).fill(0) : mode === 'tr' ? await marketDivs(id, s) : s.div; Q.M[key] = buildMarket({ d: s.d, o: s.o, h: s.h, l: s.l, c: s.c, v: s.v, div });
  /* (taux sans risque : Fed funds pour les titres en dollars ; aucun pour les titres en FCFA, plutôt qu'un taux d'une autre devise) */
  if (Q.by[id] && Q.by[id].ccy !== 'USD') Q.M[key].rf = new Float64Array(s.c.length); } return Q.M[key]; }
function sec(id) { return Q.by[id]; }
function secsWhere(f) { return Q.sum.secs.filter(f); }
function applyQuotes() {
  const q = Q.quotes && Q.quotes.q; if (!q) return;
  for (const [id, r] of Object.entries(q)) { const s = Q.by[id]; if (!s || !r.last) continue; const day = r.d ? s2i(r.d) : s.dt;
    if (day > s.dt) { s.prev = r.prev || s.last; s.dt = day; } s.last = r.last; s.pct = s.prev > 0 ? s.last / s.prev - 1 : r.pct != null ? r.pct : null;  /* (variation en % cohérente avec la variation nette : même cours précédent) */ if (r.vol != null) s.shd = r.vol; s.live = true; s.q = r; }
}
function applyQuoteToSeries(s) {
  const q = Q.quotes && Q.quotes.q && Q.quotes.q[s.id]; if (!q || !q.last || !q.d) return; const day = s2i(q.d), n = s.x.length;
  /* (série sans ouverture / plus haut / plus bas : o, h et l sont le tableau des clôtures lui-même, complété une seule fois) */
  if (day > s.x[n - 1]) { s.x.push(day); s.d.push(q.d); s.c.push(q.last); if (s.o !== s.c) s.o.push(q.o || q.last); if (s.h !== s.c) s.h.push(Math.max(q.h || q.last, q.last, q.o || q.last)); if (s.l !== s.c) s.l.push(Math.min(q.l || q.last, q.last, q.o || q.last)); s.v.push(q.vol || 0); s.div.push(0); if (s.val) s.val.push(q.val || 0); s.prov = true; }
  else if (day === s.x[n - 1]) { s.c[n - 1] = q.last; s.h[n - 1] = Math.max(s.h[n - 1], q.last); s.l[n - 1] = Math.min(s.l[n - 1], q.last); if (q.vol != null) s.v[n - 1] = q.vol; }
}

/* ---------- ligne de commande ---------- */
function scoredSecs(qs) {
  const q = qs.trim().toUpperCase(); if (!q) return [];
  const out = []; for (const s of Q.sum.secs) { const id = s.id.toUpperCase(), tk = s.tk.toUpperCase(), n = (s.n || '').toUpperCase(), sh = (s.short || '').toUpperCase();
    const sc = id === q ? 0 : tk.startsWith(q) ? 1 : id.startsWith(q) ? 2 : n.startsWith(q) || sh.startsWith(q) ? 3 : n.includes(q) || sh.includes(q) ? 4 : 9; if (sc < 9) out.push([sc, s]); }
  return out.sort((a, b) => a[0] - b[0] || (b[1].liq || 0) - (a[1].liq || 0));
}
function searchSecs(qs) { return scoredSecs(qs).map(x => x[1]); }
/* noms usuels des sociétés BRVM absents de leur nom officiel (anciens noms, sigles) */
const SEC_ALIAS = { SGBCI: 'SGBC', 'SOCIETE GENERALE': 'SGBC', BICICI: 'BICC', SODECI: 'SDCC', AGL: 'SDSC', BOLLORE: 'SDSC', 'AIR LIQUIDE': 'SIVC', AIRLIQUIDE: 'SIVC', SIEM: 'SEMC', CORIS: 'CBIBF', LNB: 'LNBB', 'ECOBANK TRANSNATIONAL': 'ETIT' };
/* titre désigné par un ticker ou un nom (« NSIA », « Orange CI », « SOGB ») ; { amb: [...] } si plusieurs titres répondent également */
function resolveSec(qs) {
  const q = String(qs || '').trim().toUpperCase(); if (!q) return null;
  const ex = exactSec(q) || (SEC_ALIAS[q] && Q.by[SEC_ALIAS[q]]); if (ex) return ex;
  const sc = scoredSecs(q); if (!sc.length) return null;
  if (sc.length === 1 || sc[0][0] < sc[1][0]) return sc[0][1];
  return { amb: sc.filter(x => x[0] === sc[0][0]).slice(0, 6).map(x => x[1]) };
}
function parseCmd(txt) {
  const toks = txt.trim().toUpperCase().replace(/<GO>|\bGO\b|EQUITY|INDEX|CURNCY|COMDTY/g, ' ').split(/\s+/).filter(Boolean);
  for (let i = 0; i + 1 < toks.length; i++) if (FN[toks[i] + ' ' + toks[i + 1]]) toks.splice(i, 2, toks[i] + ' ' + toks[i + 1]);  // codes à deux mots (STOCK BONDS)
  /* la fonction d'abord (où qu'elle soit), puis le titre désigné par le reste : ticker ou nom de la société */
  let fn = null; const rest = [];
  for (const t0 of toks) { const t = !fn && (FN_ALIAS[t0] || FN_SHORT[t0]) ? fnAlias(t0) : t0; if (!fn && FN[t] && has(t)) { fn = t; continue; } if (!fn && t === 'AIDE') { fn = 'HELP'; continue; } rest.push(t0); }
  const q = rest.join(' '); let s = null, amb = null;
  if (q) { let r = resolveSec(q); if (!r || r.amb) { for (const t of rest) { const r2 = resolveSec(t); if (r2 && !r2.amb) { r = r2; break; } } } if (r && r.amb) amb = r.amb; else if (r) s = r.id; }
  return { fn, s, q, amb };
}
/* « 2 <GO> » : active l'élément numéroté 2 de l'écran (onglet, bouton d'action, section, ligne de menu) */
function numCmd(t) { const el = document.querySelector(`[data-n="${t}"]`); if (el) { el.click(); return true; } return false; }
function runCmd(txt) {
  const t = txt.trim(); if (/^\d{1,3}$/.test(t)) { if (numCmd(t)) return; if (ST.fn === 'MENU') { const it = menuItems(sec(ST.sec))[+t - 1]; if (it) { go(it, ST.sec); return; } } toast('Aucun élément numéroté ' + t + ' sur cet écran.'); return; }
  const mk = t.match(KW_CMD); if (mk) { kwGo(mk[1] == null || !mk[1].trim() ? null : mk[1].trim()); return; }  // (recherche demandée explicitement : « MOTS CLES … »)
  const { fn, s, q, amb } = parseCmd(txt);
  /* la barre n'envoie jamais d'elle-même vers la recherche dans les documents : un texte non reconnu est signalé */
  if (amb && !s) { toast(`« ${kwClean(q)} » : plusieurs titres — ${amb.map(x => x.id + ' (' + (x.short || x.n) + ')').join(', ')}. Précisez le ticker.`); return; }
  if (!fn && !s) { toast(`« ${kwClean(t)} » : aucun titre ni fonction reconnu. Pour chercher dans les documents, ouvrez MOTS CLES.`); return; }
  if (fn && !s && q && FN[fn][1] === 'sec') { toast(`Titre « ${kwClean(q)} » introuvable.`); return; }
  if (fn && FN[fn][1] === 'mkt') { go(fn, s); return; }
  go(fn || 'MENU', s || ST.sec);
}
const KW_CMD = /^(?:mots?[\s-]*cl[eé]s?|motscl[eé]s?|recherche|kw|docs)(?:\s+([\s\S]*))?$/i;
const kwClean = t => String(t || '').replace(/<GO>|\b(?:GO|EQUITY|INDEX|CURNCY|COMDTY)\b/gi, ' ').replace(/\s+/g, ' ').trim();
function kwGo(q) { const k = ST.kw = ST.kw || { q: '', k: '', n: 60, sel: 0 }; if (q != null) Object.assign(k, { q, k: '', n: 60, sel: 0, rec: true }); ST.tab['MOTS CLES'] = 'r'; go('MOTS CLES'); }
function menuItems(s) { return SEC_TABS.filter(has); }
function exactSec(t) { const u = (t || '').toUpperCase(); return Q.by[u] || Q.sum.secs.find(s => s.tk.toUpperCase().split(' ')[0] === u) || null; }
/* Saisie façon Bloomberg : « SNTS » propose les titres ; « SNTS » + espace (ou Tab) liste les fonctions du titre avec leur définition. */
function initCmd() {
  const inp = $('cmd'), ac = $('ac'); let sel = 0, items = [];
  const row = (it, i) => it.k === 'h' ? `<p class="ach">${esc(it.a)}</p>` : `<div class="${i === sel ? 'on' : ''}${it.off ? ' off' : ''}" data-i="${i}" title="${esc(it.tt || '')}"><b>${esc(it.a)}</b><span>${it.b}</span><span>${esc(it.c)}</span></div>`;
  const show = () => {
    const v = inp.value, toks = v.trim().split(/\s+/).filter(Boolean), sp = /\s$/.test(v);
    /* titre désigné par les premiers mots (ticker ou nom : « NSIA », « Orange CI ») ; les mots suivants filtrent ses fonctions */
    let S = null, nS = 0; for (let k = toks.length; k >= 1 && !S; k--) { const r = k === 1 ? (exactSec(toks[0]) || resolveSec(toks[0])) : resolveSec(toks.slice(0, k).join(' ')); if (r && !r.amb && (k < toks.length || sp || k > 1 || exactSec(toks[0]))) { S = r; nS = k; } }
    if (S && (toks.length > nS || sp || nS > 1)) {
      const part = toks.slice(nS).join(' ').toUpperCase();
      const codes = SEC_TABS.filter(has).filter(c => !part || c.startsWith(part) || FN[c][0].toUpperCase().includes(part) || FN[c][4].toUpperCase().includes(part));
      items = [{ k: 'h', a: `${ykey(S)} · ${S.n}` }];
      for (const [g, cs] of MENU_GROUPS) { const gc = cs.filter(c => codes.includes(c)); if (!gc.length) continue; if (!part) items.push({ k: 'h', a: g });
        for (const c of gc) { const why = avail(c, S); items.push({ k: 'sfn', id: c, sec: S.id, a: c, b: `${esc(FN[c][4])} <i>— ${esc(FN[c][3])}</i>`, c: why ? 'n.d.' : FN[c][0], off: !!why, tt: why ? 'Non disponible : ' + why : FN[c][3] }); } }
      if (part && items.length === 1) items.push({ k: 'h', a: `Aucune fonction « ${part} » pour ${S.id}` });
    } else {
      /* « TOTAL FA » : plusieurs titres répondent au nom — chacun proposé avec la fonction tapée */
      const lastT = toks.length > 1 ? toks[toks.length - 1].toUpperCase() : '', al = lastT && (FN_ALIAS[lastT] || FN_SHORT[lastT]);
      const lastFn = lastT && FN[lastT] && has(lastT) ? lastT : al && has(al[0]) ? al[0] : null;
      const pre = lastFn ? resolveSec(toks.slice(0, -1).join(' ')) : null;
      if (pre && pre.amb) { items = [{ k: 'h', a: 'Plusieurs titres répondent à ce nom' }].concat(pre.amb.map(x => { const why = avail(lastFn, x); return { k: 'sfn', id: lastFn, sec: x.id, a: x.id, b: `${esc(x.n)} <i>— ${esc(FN[lastFn][4])}</i>`, c: why ? 'n.d.' : FN[lastFn][0], off: !!why, tt: why ? 'Non disponible : ' + why : FN[lastFn][3] }; })); }
      else if (lastFn && !pre && FN[lastFn][1] === 'sec') { items = [{ k: 'h', a: `Titre « ${toks.slice(0, -1).join(' ')} » introuvable` }]; }
      else {
      const last = toks[toks.length - 1] || '', L = last.toUpperCase();
      const LL = v.trim().toUpperCase(), multi = /\s/.test(LL);
      const fns = Object.keys(FN).filter(k => has(k) && k !== 'MENU' && L && (multi ? k.startsWith(LL) : k.startsWith(L) || FN[k][0].toUpperCase().startsWith(L) || FN[k][4].toUpperCase().startsWith(L)))
        .map(k => ({ k: 'fn', id: k, a: k, b: `${esc(FN[k][4])} <i>— ${esc(FN[k][3])}</i>`, c: FN[k][1] === 'sec' ? 'fonction titre' : 'fonction', tt: FN[k][3] }));
      const ssm = multi ? searchSecs(kwClean(v)).slice(0, 6) : [];  /* (nom en plusieurs mots : « orange ci ») */
      const ss = ssm.concat(searchSecs(last).filter(s => !ssm.includes(s))).slice(0, 12).map(s => ({ k: 'sec', id: s.id, a: ykey(s), b: esc(s.n), c: s.mkt === 'BRVM' ? 'BRVM' : s.mkt === 'US' ? (s.typ === 'ETF' ? 'ETF US' : 'US') : s.cls }));
      /* sections comme l'autocomplétion du terminal : FONCTIONS puis TITRES (ou l'inverse si le texte est un ticker exact) */
      for (const [k, [f, t]] of Object.entries(FN_SHORT)) if (L && (multi ? k.startsWith(LL) : k.startsWith(L)) && has(f)) fns.unshift({ k: 'fn', id: k, a: k, b: `${esc(tabLabel(f, t) || '')} <i>— onglet de ${f}</i>`, c: 'fonction', tt: FN[f][3] });
      for (const [k, [f, t]] of Object.entries(FN_ALIAS)) if (L && (multi ? k.startsWith(LL) : k.startsWith(L)) && has(f)) { const tl = t ? tabLabel(f, t) : null; fns.unshift({ k: 'fn', id: k, a: k, b: `${esc(FN[f][4])} <i>— ${tl ? `désormais dans ${f}, onglet « ${esc(tl)} »` : `s’appelle désormais ${f}`}</i>`, c: 'fonction', tt: FN[f][3] }); }
      const F = fns.slice(0, 8), T = ss.slice(0, 10), secFirst = ss.length && (ss[0].id.toUpperCase() === L || ssm.length > 0);
      const blk = (lab, arr) => arr.length ? [{ k: 'h', a: lab }].concat(arr) : [];
      items = secFirst ? blk('TITRES', T).concat(blk('FONCTIONS', F)) : blk('FONCTIONS', F).concat(blk('TITRES', T));
      /* recherche dans les documents : seulement quand elle est demandée (« MOTS CLES … ») ; jamais proposée d'office */
      const kv = v.trim(), mq = kv.match(KW_CMD), q = mq ? (mq[1] || '').trim() : '';
      if (mq && q.length >= 2) items = blk('RECHERCHE', [{ k: 'kw', id: q, a: 'MOTS CLES', b: `Rechercher « ${esc(q)} » dans tous les documents du marché`, c: 'recherche', tt: FN['MOTS CLES'][3] }]).concat(items);
      else if (!items.length && kv.length >= 2) items = [{ k: 'h', a: 'Aucun titre ni fonction — pour chercher dans les documents, ouvrez MOTS CLES' }];
      }
    }
    sel = Math.max(0, items.findIndex(it => it.k !== 'h' && !it.off)); ac.hidden = !items.length;
    ac.innerHTML = (items.length ? '<p class="ahd"><i>&lt;FLÈCHE HAUT&gt; pour masquer</i><span>Autocomplétion</span></p>' : '') + items.map(row).join('') + (items.length && items.some(it => it.k === 'sec') ? '<p class="hint">Entrée : menu du titre · espace ou Tab : ses fonctions avec leur définition</p>' : items.some(it => it.k === 'sfn') ? '<p class="hint">↑ ↓ puis Entrée · ou tapez le code (ex. FA) · grisé = non disponible pour ce titre</p>' : '');
  };
  const pick = (i, tab) => { const it = items[i]; if (!it || it.k === 'h') return;
    if (it.k === 'sec' && tab) { inp.value = it.id + ' '; show(); return; }
    ac.hidden = true; inp.value = ''; inp.blur();
    if (it.k === 'kw') kwGo(it.id || null); else if (it.k === 'sfn') go(it.id, it.sec); else if (it.k === 'fn') go(it.id, ST.sec); else go('MENU', it.id); };
  const step = d => { let k = sel; for (let j = 0; j < items.length; j++) { k = (k + d + items.length) % items.length; if (items[k].k !== 'h') break; } sel = k;
    [...ac.querySelectorAll('[data-i]')].forEach(c => c.classList.toggle('on', +c.dataset.i === sel)); const d0 = ac.querySelector('div.on'); if (d0) d0.scrollIntoView({ block: 'nearest' }); };
  inp.addEventListener('input', show); inp.addEventListener('focus', () => { if (inp.value) show(); });
  inp.addEventListener('keydown', e => { if (ac.hidden) return;
    if (e.key === 'ArrowUp' && sel === items.findIndex(it => it.k !== 'h' && !it.off)) { e.preventDefault(); ac.hidden = true; return; }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); step(e.key === 'ArrowDown' ? 1 : -1); }
    if (e.key === 'Tab') { e.preventDefault(); pick(sel, true); } if (e.key === 'Escape') { ac.hidden = true; } });
  ac.addEventListener('mousedown', e => { const d = e.target.closest('[data-i]'); if (d) { e.preventDefault(); pick(+d.dataset.i); } });
  $('cmdForm').addEventListener('submit', e => { e.preventDefault(); const v = inp.value.trim();
    if (!ac.hidden && items.length && !/^\d{1,3}$/.test(v)) { const w = v.toUpperCase().split(/\s+/); for (let i = 0; i + 1 < w.length; i++) if (FN[w[i] + ' ' + w[i + 1]]) w.splice(i, 2, w[i] + ' ' + w[i + 1]); const typedFn = w.length === 1 && FN[w[0]] && has(w[0]);
      const it = items[sel]; const typedSecFn = w.length >= 2 && (FN[w[w.length - 1]] && has(w[w.length - 1]) || /^(?:EQUITY|INDEX|CURNCY|COMDTY|GO|<GO>)$/.test(w[w.length - 1])) && (() => { const r = resolveSec(w.slice(0, -1).join(' ')); return r && !r.amb; })();
      if (!typedSecFn && it && (!typedFn || it.a === w[0])) { pick(sel); return; } }
    ac.hidden = true; inp.value = ''; inp.blur(); runCmd(v); });
  inp.addEventListener('blur', () => setTimeout(() => { ac.hidden = true; }, 150));
  /* touches jaunes du clavier Bloomberg : « SNTS » puis F8 (Equity) = « SNTS Equity <GO> » ; F1 = aide, F2 = obligations */
  document.addEventListener('keydown', e => { const fk = { F1: 'HELP', F2: 'GOVT', F8: 'Equity', F9: 'Comdty', F10: 'Index' }[e.key]; if (!fk || e.metaKey || e.ctrlKey || e.altKey) return; e.preventDefault();
    if (fk === 'HELP') { go('HELP'); return; } if (fk === 'GOVT') { go('UEMOA BONDS'); return; } const v = $('cmd').value.trim(); if (v) { $('cmd').value = ''; runCmd(v); } else { $('cmd').focus(); toast('Tapez un ticker puis ' + e.key + ' (' + fk + ').'); } }, true);
  document.addEventListener('keydown', e => { if (e.target.matches('input,select,textarea') || e.metaKey || e.ctrlKey || e.altKey) return; if (/^[a-zA-Z0-9]$/.test(e.key)) { inp.focus(); } if (e.key === 'Escape') { if (!$('ddm').hidden) { ddClose(); return; } if (document.body.classList.contains('maxi')) { toggleMaxi(false); return; } go(SECFN.has(ST.fn) && ST.fn !== 'MENU' ? 'MENU' : 'MONITOR'); } });
}

/* ---------- menus déroulants ---------- */
function ddOpen(anchor, rows) {
  const d = $('ddm'); d.innerHTML = rows.map((r, i) => r.h ? `<div class="dh">${esc(r.h)}</div>` : `<div class="di${r.code ? '' : ' nc'}${r.off ? ' off' : ''}${r.on ? ' on' : ''}" data-di="${i}" title="${esc(r.tt || '')}"><em>${r.n != null ? r.n + ')' : ''}</em>${r.code ? `<b>${esc(r.code)}</b>` : ''}<span>${r.l}</span></div>`).join('');
  d.hidden = false; const a = anchor.getBoundingClientRect(); const w = d.getBoundingClientRect().width;
  d.style.left = Math.max(4, Math.min(window.innerWidth - w - 4, a.left)) + 'px'; d.style.top = (a.bottom + 1) + 'px';
  d.onclick = e => { const x = e.target.closest('[data-di]'); if (!x) return; const r = rows[+x.dataset.di]; ddClose(); if (r && r.run && !r.off) r.run(); };
}
function ddClose() { $('ddm').hidden = true; }
document.addEventListener('mousedown', e => { if (!e.target.closest('#ddm') && !e.target.closest('[data-dd]')) ddClose(); });

/* ---------- chrome : barre d'outils, en-tête du titre, barre rouge, onglets, actualités ---------- */
const PG = { acts: [], tabs: null, title: null };
function setTabs(list, cur, cb, o = {}) {
  const t = $('ptabs'); PG.tabs = list; t.hidden = false;
  t.innerHTML = list.map(([k, l, off], i) => `<button class="ptab${k === cur ? ' on' : ''}${off ? ' off' : ''}" data-n="${i + 1}" data-tab="${esc(k)}" title="${off ? esc(off) : ''}"><em>${i + 1})</em> ${esc(l)}</button>`).join('');
  t.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => cb(b.dataset.tab));
}
/* Sous-onglets bleus (comme « 11) Adj Highlights ») : renvoie le HTML, numérotés à partir de base */
function subTabs(list, cur, attr, base = 11) { return `<div class="stabs2">${list.map(([k, l], i) => `<button class="stab${k === cur ? ' on' : ''}" data-n="${base + i}" ${attr}="${esc(k)}"><em>${base + i})</em> ${esc(l)}</button>`).join('')}</div>`; }
function setActs(acts) { PG.acts = acts || []; renderRbar(); }
function setTitle(t) { PG.title = t; renderRbar(); }
function tabState(fn, def) { if (ST.tab[fn] == null) ST.tab[fn] = def; return ST.tab[fn]; }
/* 96) Actions, 97) Sortie, 98) Réglages : la barre rouge Bloomberg */
/* ---------------------------------------------------------------- fluidité et vitesse (réglages, désactivés par défaut)
   Ouverture rapide : chaque fonction retient les fichiers qu'elle lit (modèle par titre, {t}) ; après chaque écran, pendant que
   l'appareil est libre, et au survol d'un lien de fonction, les fichiers des écrans suivants sont lus à l'avance (mêmes
   fichiers, mêmes chiffres : seul le temps d'ouverture change). Animations douces : apparition des écrans, graphiques qui se
   dessinent, chiffres qui défilent jusqu'à leur valeur exacte (texte d'origine remis à la fin) ; coupées si l'appareil demande
   de réduire les animations. */
function reduceMotion() { try { return matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } }
const PF = (() => { let m = {}; try { m = JSON.parse(localStorage.getItem('fqt_pf') || '{}') || {}; } catch (e) { } return { map: m, busy: false, t: null, cur: null }; })();
const PF_SKIP = /^(live|quotes|news|summary|session|version)\.json$/;
function pfRec(path) {
  if (PF.busy || !PF.cur || PF_SKIP.test(path)) return;
  const s = ST.sec || '', s_ = s.replace('.', '_'); let p = path;
  if (s && path.includes('/' + s_ + '.')) p = path.replace('/' + s_ + '.', '/{t_}.'); else if (s && path.includes('/' + s + '.')) p = path.replace('/' + s + '.', '/{t}.');
  const L = PF.map[PF.cur] = PF.map[PF.cur] || []; if (L.includes(p)) return; L.push(p); if (L.length > 12) L.shift();
  clearTimeout(PF.t); PF.t = setTimeout(() => { try { localStorage.setItem('fqt_pf', JSON.stringify(PF.map)); } catch (e) { } }, 1500);
}
function pfLoad(fn, sid) {
  if (!PREF.fast || !fn) return 0; const L = PF.map[fn] || []; let n = 0; const s = sid || ST.sec || '';
  for (const p of L) {
    if (p.includes('{t') && !s) continue; const path = p.replace('{t_}', s.replace('.', '_')).replace('{t}', s);
    if (Q.json[path]) continue; n++;
    PF.busy = true; try { getJSON(path).catch(() => { delete Q.json[path]; }); } finally { PF.busy = false; } // (échec : relu normalement à l'ouverture)
  }
  return n;
}
function pfIdle() {
  if (!PREF.fast) return; try { if (navigator.connection && navigator.connection.saveData) return; } catch (e) { }
  const run = () => { let n = 0; for (const f of (REL[ST.fn] || []).slice(0, 5)) { if (n >= 10) break; n += pfLoad(f, ST.sec); } };
  if (window.requestIdleCallback) requestIdleCallback(run, { timeout: 2500 }); else setTimeout(run, 800);
}
function countUp(m, seq) {
  if (!document.documentElement.classList.contains('anim')) return;
  const RX = /^([+\u2212-]?)(\d{1,3}(?:[ \u00a0\u202f]\d{3})*|\d+)(?:,(\d+))?(\s?%)?$/;
  const els = [...m.querySelectorAll('.kv2 b')].filter(b => !b.children.length && RX.test(b.textContent.trim())).slice(0, 40); if (!els.length) return;
  const items = els.map(b => { const t0 = b.textContent, x = t0.trim().match(RX), sep = (x[2].match(/[ \u00a0\u202f]/) || [' '])[0], dec = x[3] ? x[3].length : 0;
    return { b, t0, sign: x[1], sep, dec, pct: x[4] || '', v: parseFloat(x[2].replace(/[ \u00a0\u202f]/g, '') + (x[3] ? '.' + x[3] : '')) }; });
  const fmt = (it, v) => { const [a, d] = v.toFixed(it.dec).split('.'); return it.sign + a.replace(/\B(?=(\d{3})+(?!\d))/g, it.sep) + (d ? ',' + d : '') + it.pct; };
  const t0 = performance.now(), D = 550;
  const step = now => { const k = Math.min(1, (now - t0) / D), e = 1 - Math.pow(1 - k, 3);
    for (const it of items) { if (!it.b.isConnected) continue; it.b.textContent = k < 1 ? fmt(it, it.v * e) : it.t0; }
    if (k < 1 && seq === renderSeq) requestAnimationFrame(step); else for (const it of items) if (it.b.isConnected) it.b.textContent = it.t0; };
  requestAnimationFrame(step);
}
const PREF = (() => { try { return JSON.parse(localStorage.getItem('fqt_pref') || '{}'); } catch (e) { return {}; } })();
/* réglages remis aux valeurs de base : texte normal, actualités affichées, ouverture rapide et animations désactivées,
   fenêtre réduite (les onglets ouverts et le portefeuille ne sont pas touchés) */
function resetPref() {
  for (const k of Object.keys(PREF)) delete PREF[k];
  savePref(); applyPref(); if (document.body.classList.contains('maxi')) toggleMaxi(false); render();
  toast('Réglages remis aux valeurs de base : texte normal, actualités affichées, ouverture rapide et animations désactivées.');
}
function savePref() { try { localStorage.setItem('fqt_pref', JSON.stringify(PREF)); } catch (e) { } }
function applyPref() { document.documentElement.classList.toggle('anim', !!PREF.anim && !reduceMotion()); document.documentElement.style.zoom = PREF.zoom && PREF.zoom !== 1 ? PREF.zoom : ''; document.body.classList.toggle('nonews', !!PREF.nonews); if (PREF.nonews) document.documentElement.style.setProperty('--nwh', '0px'); else if (typeof renderNews === 'function') renderNews(); }
function stdActs() {
  return [{ n: 96, l: 'Actions', menu: () => [
    { l: 'Ouvrir dans un nouvel onglet', run: () => wtNew(ST.fn, ST.sec) }, { l: 'Copier le lien de cet écran', run: () => { navigator.clipboard && navigator.clipboard.writeText(location.href).then(() => toast('Lien copié.'), () => toast(location.href)); } },
    { l: 'Recharger les données', run: () => { Q.json = {}; Q.ser = {}; Q.M = {}; pollStatic(); render(); } }, { l: 'Fonctions associées', run: () => { const b = $('ddRel'); b && b.click(); } }] },
  { n: 97, l: 'Sortie', menu: () => [{ l: 'Tableau principal → Excel (CSV)', run: exportCSV }, { l: 'Graphique principal → image PNG', run: exportPNG }, { l: 'Écran → PDF / impression', run: () => window.print() }] },
  { n: 98, l: 'Réglages', menu: () => [{ l: `Taille du texte : normale${!PREF.zoom || PREF.zoom === 1 ? ' ✓' : ''}`, run: () => { PREF.zoom = 1; savePref(); applyPref(); } }, { l: `Taille du texte : grande${PREF.zoom === 1.12 ? ' ✓' : ''}`, run: () => { PREF.zoom = 1.12; savePref(); applyPref(); } },
    { l: `Taille du texte : très grande${PREF.zoom === 1.25 ? ' ✓' : ''}`, run: () => { PREF.zoom = 1.25; savePref(); applyPref(); } }, { l: PREF.nonews ? 'Afficher le panneau des actualités' : 'Masquer le panneau des actualités', run: () => { PREF.nonews = !PREF.nonews; savePref(); applyPref(); } },
    { l: `Ouverture rapide : ${PREF.fast ? 'activée ✓' : 'désactivée'}`, run: () => { PREF.fast = !PREF.fast; savePref(); applyPref(); toast(PREF.fast ? 'Ouverture rapide activée : les données des écrans suivants sont préparées à l’avance.' : 'Ouverture rapide désactivée.'); if (PREF.fast) pfIdle(); } },
    { l: `Animations douces : ${PREF.anim ? 'activées ✓' : 'désactivées'}`, run: () => { PREF.anim = !PREF.anim; savePref(); applyPref(); toast(PREF.anim ? (reduceMotion() ? 'Animations activées, mais votre appareil demande de réduire les animations : elles restent coupées.' : 'Animations douces activées.') : 'Animations désactivées.'); } },
    { l: document.body.classList.contains('maxi') ? 'Réduire la fenêtre' : 'Agrandir la fenêtre (plein écran)', run: () => toggleMaxi() },
    { l: 'Fermer tous les onglets sauf celui-ci', run: () => { WT.list = [WT.list[WT.cur]]; WT.cur = 0; wtSave(); renderWtabs(); } },
    { l: 'Réinitialiser les réglages (valeurs de base)', run: resetPref }] }];
}
function exportPNG() { const c = $('main').querySelector('canvas'); if (!c) { toast('Aucun graphique sur cet écran.'); return; } const a = document.createElement('a'); a.href = c.toDataURL('image/png'); a.download = `FQT_${ST.fn}_${SECFN.has(ST.fn) ? ST.sec + '_' : ''}${new Date().toISOString().slice(0, 10)}.png`; a.click(); }

/* ---------- onglets de fenêtre (comme les onglets du terminal Bloomberg) : un écran par onglet, « + » pour en ouvrir un ---------- */
const WT = (() => { try { const w = JSON.parse(localStorage.getItem('fqt_wtabs') || 'null'); if (w && Array.isArray(w.list) && w.list.length) return w; } catch (e) { } return { list: [{ fn: 'MONITOR', sec: 'QQQ' }], cur: 0 }; })();
function wtSave() { try { localStorage.setItem('fqt_wtabs', JSON.stringify({ list: WT.list.map(t => ({ fn: t.fn, sec: t.sec })), cur: WT.cur })); } catch (e) { } }
function wtLabel(t) { const s = Q.by[t.sec]; return SECFN.has(t.fn) && s ? `${t.fn} ${(s.short || s.n || s.id).toUpperCase()} ${ykey(s).split(' ').pop()}` : `${t.fn} ${FN[t.fn] ? FN[t.fn][4] : ''}`; }
function renderWtabs() {
  const w = $('wtabs'); if (!w) return;
  w.innerHTML = WT.list.map((t, i) => `<div class="wt${i === WT.cur ? ' on' : ''}" data-wt="${i}" title="${esc(wtLabel(t))}"><span><b>${esc(t.fn)}</b> ${esc(wtLabel(t).slice(t.fn.length + 1))}</span>${WT.list.length > 1 ? `<b class="wx" data-wx="${i}" title="Fermer">×</b>` : ''}</div>`).join('') +
    `<button class="wplus" id="wplus" title="Nouvel onglet (puis tapez par exemple ORAC DES)">+</button><span class="wsp"></span><button class="wico" id="wsrch" title="Rechercher un titre ou une fonction">⌕</button><button class="wico" id="wmax" title="${document.body.classList.contains('maxi') ? 'Réduire' : 'Agrandir (plein écran)'}">${document.body.classList.contains('maxi') ? '⤡' : '⤢'}</button><span class="wopt">☰ Options</span>`;
  w.querySelectorAll('[data-wt]').forEach(el => el.onclick = e => { if (e.target.dataset.wx != null) return; wtSwitch(+el.dataset.wt); });
  w.querySelectorAll('[data-wx]').forEach(el => el.onclick = e => { e.stopPropagation(); wtClose(+el.dataset.wx); });
  $('wplus').onclick = () => wtNew('MONITOR', ST.sec, true); $('wsrch').onclick = () => { const c = $('cmd'); c.focus(); }; $('wmax').onclick = () => toggleMaxi();
  w.querySelector('.wopt').onclick = e => ddOpen(e.target, stdActs()[2].menu());
}
/* ⤢ : agrandit l'écran courant (bandeaux masqués, plein écran du navigateur si possible), comme l'agrandissement d'une fenêtre Bloomberg */
function toggleMaxi(on) { const b = document.body, v = on == null ? !b.classList.contains('maxi') : !!on; b.classList.toggle('maxi', v);
  try { if (v && !document.fullscreenElement && document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => { }); if (!v && document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(() => { }); } catch (e) { }
  renderWtabs(); if (ST.fn === 'GP') render(); else setTimeout(() => window.dispatchEvent(new Event('resize')), 80); }
document.addEventListener('fullscreenchange', () => { if (!document.fullscreenElement && document.body.classList.contains('maxi')) toggleMaxi(false); });
function wtSync() { const t = WT.list[WT.cur] || (WT.list[WT.cur] = {}); t.fn = ST.fn; t.sec = ST.sec; t.hist = ST.hist; t.hpos = ST.hpos; wtSave(); renderWtabs(); }
function wtSwitch(i) { if (i === WT.cur || !WT.list[i]) return; wtSync(); WT.cur = i; const t = WT.list[i]; ST.hist = t.hist || []; ST.hpos = t.hpos ?? -1; go(t.fn, t.sec, { nohist: !!(t.hist && t.hist.length) }); }
function wtNew(fn, secId, focus) { if (WT.list.length >= 12) { toast('12 onglets au maximum.'); return; } wtSync(); WT.list.push({ fn, sec: secId, hist: [], hpos: -1 }); WT.cur = WT.list.length - 1; ST.hist = []; ST.hpos = -1; go(fn, secId);
  if (focus) { const c = $('cmd'); if (c) { c.value = ''; c.focus(); } toast('Nouvel onglet : tapez un titre et une fonction, par exemple ORAC DES, puis Entrée.', 4000); } }
function wtClose(i) { if (WT.list.length < 2) return; WT.list.splice(i, 1); if (WT.cur >= WT.list.length || i < WT.cur) WT.cur = Math.max(0, WT.cur - (i <= WT.cur ? 1 : 0)); if (WT.cur >= WT.list.length) WT.cur = WT.list.length - 1;
  const t = WT.list[WT.cur]; ST.hist = t.hist || []; ST.hpos = t.hpos ?? -1; wtSave(); go(t.fn, t.sec, { nohist: true }); }
function exportCSV() {
  const t = $('main').querySelector('table.t'); if (!t) { toast('Aucun tableau sur cet écran.'); return; }
  const rows = [...t.querySelectorAll('tr')].map(tr => [...tr.children].map(c => '"' + c.innerText.replace(/ | /g, ' ').replace(/"/g, '""').trim() + '"').join(';'));
  const blob = new Blob(['﻿' + rows.join('\n')], { type: 'text/csv;charset=utf-8' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `FQT_${ST.fn}_${SECFN.has(ST.fn) ? ST.sec + '_' : ''}${new Date().toISOString().slice(0, 10)}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
function renderRbar() {
  const b = $('rbar'), s = sec(ST.sec), isSec = SECFN.has(ST.fn) && s;
  /* numérotation cohérente : une action de la page remplace l'action standard de même nom ; en cas de numéro déjà pris, l'action standard passe au numéro libre suivant */
  const used = new Set(PG.acts.map(a => a.n)), labs = new Set(PG.acts.map(a => a.l)), std = [];
  for (const a of stdActs()) { if (labs.has(a.l)) continue; let k = a.n; while (used.has(k)) k++; used.add(k); std.push(Object.assign({}, a, { n: k })); }
  const acts = PG.acts.concat(std).sort((a, b) => a.n - b.n);
  b.innerHTML = (isSec ? `<span class="ob" id="obT" title="Changer de titre en gardant la fonction ${ST.fn} : cliquez, tapez le ticker, Entrée">${esc(ykey(s))}</span>` : `<span class="ret">&lt;Menu&gt; pour revenir</span>`) +
    acts.map((a, i) => `<button class="ab${a.menu ? ' mn' : ''}${a.on ? ' on' : ''}" data-n="${a.n}" data-dd="1" data-ai="${i}"><em>${a.n})</em> ${esc(a.l)}</button>`).join('') +
    `<span class="rt">${esc(PG.title || FN[ST.fn][4] || FN[ST.fn][0])}</span>`;
  b.querySelectorAll('[data-ai]').forEach(x => x.onclick = () => { const a = acts[+x.dataset.ai]; if (a.menu) ddOpen(x, a.menu()); else if (a.run) a.run(); });
  b.querySelector('.ret') && (b.querySelector('.ret').onclick = () => go(SECFN.has(ST.fn) ? 'MENU' : 'MONITOR'));
  if ($('obT')) $('obT').onclick = obEdit;
}
/* case orange du titre (comme le champ ambre du terminal) : on y tape un autre ticker, Entrée = même fonction sur ce titre */
function obEdit() {
  const ob = $('obT'); if (!ob || ob.querySelector('input')) return; const fn = ST.fn, old = ob.textContent;
  ob.innerHTML = `<input id="obI" value="${esc(old)}" spellcheck="false" autocomplete="off" aria-label="Changer de titre">`; const inp = $('obI'); inp.focus(); inp.select();
  let list = [], sel = 0;
  const show = () => { const v = inp.value.trim(); list = v && v !== old ? searchSecs(v.replace(/\b(EQUITY|INDEX|CURNCY|COMDTY)\b/gi, '').trim()).slice(0, 10) : [];
    if (!list.length) { ddClose(); return; } sel = Math.min(sel, list.length - 1);
    ddOpen(ob, [{ h: `Ouvrir ${fn} pour…` }].concat(list.map((x, i) => { const why = SECFN.has(fn) && fn !== 'MENU' ? avail(fn, x) : null;
      return { n: i + 1, code: ykey(x), l: esc(x.n) + (why ? ' <i class="dm">(' + esc(fn) + ' non disponible)</i>' : ''), on: i === sel, run: () => pick(x) }; }))); };
  let done = false; const pick = x => { done = true; ddClose(); if (x) go(fn, x.id); else { ob.textContent = old; toast('Titre introuvable.'); } };
  const restore = () => { ddClose(); ob.textContent = old; };
  inp.oninput = () => { sel = 0; show(); };
  inp.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); const v = inp.value.trim().toUpperCase().split(/\s+/)[0]; pick(list[sel] || exactSec(v) || searchSecs(v)[0]); }
    else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); restore(); }
    else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + list.length) % Math.max(1, list.length); show(); } };
  inp.onblur = () => setTimeout(() => { if (!done && document.activeElement !== inp && $('obI')) restore(); }, 450);
}
function renderTbar() {
  const t = $('tbar'), s = sec(ST.sec), isSec = SECFN.has(ST.fn);
  t.innerHTML = `<button class="nv" id="hb" title="Écran précédent" aria-label="Écran précédent" ${ST.hpos > 0 ? '' : 'disabled'}>${ICO.prev}</button><button class="nv" id="hf" title="Écran suivant" aria-label="Écran suivant" ${ST.hpos < ST.hist.length - 1 ? '' : 'disabled'}>${ICO.next}</button>
    <button class="dd" data-dd="1" id="ddSec" title="Titre actif"><span>${esc(s ? (s.short || s.n).toUpperCase() + ' ' + ykey(s).split(' ').pop() : '—')}</span></button>
    <button class="dd" data-dd="1" id="ddFn" title="Fonction"><span>${ST.fn}</span></button>
    <button class="dd rel" data-dd="1" id="ddRel" title="Fonctions associées"><span>Menu des fonctions associées</span></button>
    <span class="sp"></span><div class="feed" id="feed"><i></i><span id="feedTxt">—</span><button id="syncBtn" hidden title="Récupérer tout de suite le dernier relevé">SYNC</button></div><div class="clocks" id="clocks"></div><button class="alb" id="alB" hidden></button><button class="qh" id="qh" title="Aide sur cette fonction">?</button>`;
  $('hb').onclick = () => histGo(-1); $('hf').onclick = () => histGo(1); bindSync();
  if (typeof maCheck === 'function') maCheck(false);
  $('qh').onclick = e => ddOpen(e.currentTarget, [{ h: `${ST.fn} · ${FN[ST.fn][4]}` }, { l: esc(FN[ST.fn][3]) }, { h: '' }, { code: 'HELP', l: 'Toutes les fonctions et la syntaxe des commandes', run: () => go('HELP') }]);
  $('ddSec').onclick = e => { const seen = []; for (let i = ST.hist.length - 1; i >= 0 && seen.length < 12; i--) { const id = ST.hist[i][1]; if (id && Q.by[id] && !seen.includes(id)) seen.push(id); }
    ddOpen(e.currentTarget, [{ h: 'Titres récents' }].concat(seen.map((id, i) => ({ n: i + 1, code: id, l: esc(Q.by[id].n), run: () => go(isSec ? ST.fn : 'MENU', id) })), [{ h: 'Autre titre' }, { l: 'Taper un ticker dans la ligne de commande…', run: () => $('cmd').focus() }])); };
  $('ddFn').onclick = e => { const rows = []; let n = 0;
    if (s) { rows.push({ h: 'Fonctions de ' + ykey(s) }); for (const [g, cs] of MENU_GROUPS) for (const c of cs.filter(has)) { const why = avail(c, s); n++; rows.push({ n, code: c, l: esc(FN[c][4]) + ' · ' + esc(FN[c][0]), off: !!why, tt: why || FN[c][3], run: () => go(c, s.id) }); } }
    rows.push({ h: 'Fonctions de marché' }); for (const c of MKT_KEYS.filter(has)) { n++; rows.push({ n, code: c, l: esc(FN[c][4]) + ' · ' + esc(FN[c][0]), tt: FN[c][3], run: () => go(c) }); }
    ddOpen(e.currentTarget, rows); };
  $('ddRel').onclick = e => { const base = REL[ST.fn] || (MENU_GROUPS.find(g => g[1].includes(ST.fn)) || [0, []])[1].filter(c => c !== ST.fn); const list = (base.length ? base : isSec ? SEC_TABS : MKT_KEYS).filter(has);
    ddOpen(e.currentTarget, [{ h: 'Fonctions associées à ' + ST.fn }].concat(list.map((c, i) => { const why = FN[c][1] === 'sec' ? avail(c, s) : null; return { n: i + 1, code: c, l: esc(FN[c][4]) + ' · ' + esc(FN[c][0]), off: !!why, tt: why || FN[c][3], run: () => go(c, FN[c][1] === 'sec' ? ST.sec : undefined) }; }), [{ h: '' }, { code: 'MENU', l: 'Toutes les fonctions du titre', run: () => go('MENU') }])); };
}
/* En-tête du titre sur deux lignes, comme Bloomberg : ticker, devise, ▲ cours, variation, mini-graphique, pré/post-marché ;
   puis heure, volume, ouverture, plus haut, plus bas, montant échangé. */
function renderSech() {
  const b = $('sech'), s = sec(ST.sec); if (!SECFN.has(ST.fn) || !s) { b.hidden = true; return; } b.hidden = false;
  const q = s.q || {}, ch = s.last - s.prev, c = cls(ch), arr = ch > 0 ? '↑' : ch < 0 ? '↓' : '';
  const brvm = s.mkt === 'BRVM', us = s.mkt === 'US';
  const tm = q.t ? q.t : Q.quotes && Q.quotes.ts && s.live ? new Date(Q.quotes.ts * 1000).toLocaleTimeString('fr-FR', { timeZone: brvm ? 'Africa/Abidjan' : 'Europe/Paris', hour: '2-digit', minute: '2-digit' }) + (brvm ? ' GMT' : '') : null;
  const x = q.ext; const xt = x && x.last ? `<span class="xt"><span class="lb">${x.s === 'pre' ? 'Pré-marché' : 'Après-bourse'}</span><span class="${cls(x.chg)}">${px(s, x.last)} ${x.chg != null ? (x.chg > 0 ? '+' : '') + num(x.chg, 2) : ''} (${x.pct != null ? (x.pct > 0 ? '+' : '') + num(x.pct * 100, 2) + '%' : '—'})</span>${x.t ? ` <span class="ex">${esc(x.t)}</span>` : ''}</span>` : '';
  const kv = (l, v, e) => v == null || v === '' ? '' : `<span><span class="lb">${l}</span> <span class="vl">${v}</span>${e ? `<span class="ex">${e}</span>` : ''}</span>`;
  const sp = s.spark && s.spark.length > 5 ? sparkSVG(s.spark.slice(-40), 110, 16) : '';
  b.innerHTML = `<div class="l1"><i class="mk"></i><span class="tk">${esc(s.tk.split(' ').slice(0, 2).join(' '))}</span><span class="cu">${esc(s.ccy === 'USD' ? '$' : s.ccy || '')}</span>
      <span class="p ${c}">${arr}${px(s, s.last)}</span><span class="${c}">${ch > 0 ? '+' : ''}${px(s, ch)}</span><span class="${c}">${s.pct != null ? (s.pct > 0 ? '+' : '') + num(s.pct * 100, 2) + '%' : ''}</span>${sp}${xt}
      ${s.susp ? '<span class="dn">COTATION SUSPENDUE</span>' : ''}</div>
    <div class="l2"><i class="bars"></i>${kv(s.live ? 'À' : 'Clôt.', s.live && tm ? tm : fd(s.dt), s.live ? ' ' + fd(s.dt).slice(0, 5) : '')}${kv('Vol', s.shd != null ? num(s.shd, 0) : null)}${kv('O', q.o ? px(s, q.o) : null)}${kv('H', q.h ? px(s, q.h) : null)}${kv('L', q.l ? px(s, q.l) : null)}
      ${kv('Val', brvm ? (s.vday || q.val ? valTxt(s, s.vday || q.val) : null) : q.val ? valTxt(s, q.val) : null)}${kv('Préc', px(s, s.prev))}${kv('52s', s.hi52 ? px(s, s.lo52) + ' – ' + px(s, s.hi52) : null)}${s.mcap ? kv('Capi', big(s.mcap), ' ' + (brvm ? 'XOF' : 'USD')) : ''}${s.per ? kv('PER', num(s.per, 1)) : ''}${s.yld ? kv('Rdt', num(s.yld * 100, 2) + '%') : ''}
      ${us && q.ms ? `<span class="ex">${esc(q.ms)}</span>` : ''}</div>`;
}
/* Bandeau d'actualités du bas : les 4 dernières dépêches, numérotées, avec source et heure. */
let NEWS_CACHE = null;
async function renderNews() {
  const p = $('nwp'); let n = null; try { n = await getJSON('news.json'); } catch (e) { }
  const it = (n && (n.items || n)) || []; NEWS_CACHE = it;
  const rows = it.slice(0, 4).map((x, i) => { const d = new Date((x.t || 0) * 1000), tk = (x.tk || []).slice(0, 2).join(' ');
    return `<div class="nr" data-u="${esc(x.u || '')}"><span class="n">${401 + i})</span><span class="s">${esc(srcCode(x))}</span><span class="t">${d.toLocaleTimeString('fr-FR', { timeZone: 'Africa/Abidjan', hour: '2-digit', minute: '2-digit' })}</span><span class="h">${esc(deent(x.ti))}</span><span class="k">${esc(tk)}</span></div>`; }).join('');
  p.className = 'nwp' + (ST.newsMin ? ' min' : '');
  p.innerHTML = `<div class="nh"><span class="nl">Actualités · heure GMT (Abidjan)</span><button data-n="300" id="nwTop">300) Toutes les actualités</button><button data-n="301" id="nwMin">301) ${ST.newsMin ? 'Agrandir' : 'Réduire'} le panneau</button></div>${rows || '<div class="nr"><span></span><span></span><span></span><span class="h">Aucune actualité chargée.</span></div>'}`;
  document.documentElement.style.setProperty('--nwh', (PREF.nonews ? 0 : p.offsetHeight) + 'px');
  $('nwTop').onclick = () => go('NEWS'); $('nwMin').onclick = () => { ST.newsMin = !ST.newsMin; try { localStorage.setItem('fqt.newsMin', ST.newsMin ? '1' : ''); } catch (e) { } renderNews().then(() => window.dispatchEvent(new Event('resize'))); };
  p.querySelectorAll('[data-u]').forEach(r => r.onclick = () => { if (r.dataset.u) window.open(r.dataset.u, '_blank', 'noopener'); });
}
const HIDE_RX = new RegExp(atob('YnJ2bXxzaWth'), 'i');
const hideSrc = x => HIDE_RX.test((x.s || '') + ' ' + (x.f || '') + ' ' + (x.u || ''));
function srcCode(x) { const s = (x.s || x.f || '').toLowerCase(); if (ANON || hideSrc(x)) return '';
  const M = [['sec.gov', 'SEC'], ['edgar', 'SEC'], ['reuters', 'RTRS'], ['bloomberg', 'BBG'], ['zonebourse', 'ZB'], ['boursorama', 'BOURSO'], ['les echos', 'ECHOS'], ['jeune afrique', 'JA'], ['financial afrik', 'FAFRIK'], ['financialafrik', 'FAFRIK'], ['agence ecofin', 'ECOFIN'], ['ecofin', 'ECOFIN'], ['bceao', 'BCEAO'], ['fed', 'FED'], ['cnbc', 'CNBC'], ['marketwatch', 'MW'], ['yahoo', 'YHOO'], ['nasdaq', 'NDAQ'], ['lefigaro', 'FIGARO'], ['le monde', 'MONDE'], ['abidjan', 'ABJ.NET'], ['apa', 'APA'], ['afp', 'AFP']];
  for (const [k, v] of M) if (s.includes(k)) return v; return (x.s || 'WEB').replace(/^www\./, '').split(/[ .]/)[0].toUpperCase().slice(0, 6); }

/* ---------- routeur et historique (écran précédent / suivant) ---------- */
let renderSeq = 0;
/* anciens codes encore acceptés (ligne de commande, liens, onglets enregistrés) : ils ouvrent le nouvel écran, et le bon onglet */
/* écrans à onglets qui regroupent d'anciennes fonctions (onglet 1 = vue principale) : source unique pour les onglets, l'aide et l'autocomplétion */
const FN_TABS = {
  BRVM: [['m', 'Marché'], ['f', 'Flottant officiel'], ['p', 'Valorisation (PER)'], ['r', 'Saison des résultats'], ['a', 'Publications attendues et retards'], ['x', 'Exposition pays']],
  DIVC: [['c', 'Calendrier'], ['a', 'Aristocrates du dividende'], ['n', 'Dividende net et encaissements']],
  BANK: [['c', 'Comparaison'], ['h', 'Historique sur 10 ans']],
  MAP: [['BRVM', 'BRVM'], ['NDX', 'Nasdaq-100'], ['ETF', 'ETF US'], ['EU', 'Europe'], ['UK', 'Royaume-Uni'], ['ASIA', 'Asie'], ['AFR', 'Afrique'], ['ME', 'Moyen-Orient'], ['US', 'Marché US']],
  INDX: [['i', 'Indices mondiaux'], ['f', 'Contrats à terme sur indices']],
  'UEMOA/DATA': [['bc', 'Taux, inflation, crédit'], ['tp', 'Titres publics'], ['wb', 'Indicateurs annuels'], ['ecst', 'Statistiques mondiales']],
  'MOTS CLES': [['r', 'Recherche'], ['h', 'Historique de recherche']],
  NOT: [['c', 'Sociétés cotées'], ['b', 'Obligations et émetteurs'], ['h', 'Historique']],
  SGI: [['sgi', 'SGI'], ['sgo', 'Gestion d’OPCVM'], ['sgp', 'Gestion de patrimoine'], ['cons', 'Conservateurs'], ['agn', 'Agences de notation'], ['gar', 'Garants']],
  EVTS: [['avis', 'Avis BRVM'], ['b', 'Suivi des sociétés BRVM'], ['a', 'Agenda des sociétés']],
  'CORP RESULT': [['u', 'À venir'], ['p', 'Publiés (60 jours)'], ['t', 'Objectifs des analystes']],
  FX: [['x', 'Franc CFA'], ['m', 'Changes croisés'], ['w', 'Classement des devises']],
  RATES: [['m', 'Marché monétaire US'], ['f', 'Anticipations de la Fed'], ['w', 'BONDS · taux souverains mondiaux']],
  QLAB: [['s', 'Statistiques'], ['v', 'Valorisation (actions BRVM)']] };
const tabLabel = (f, t) => ((FN_TABS[f] || []).find(x => x[0] === t) || [])[1];
const FN_ALIAS = { CF: ['EVTS', 'b'], WCRS: ['FX', 'w'], FXC: ['FX', 'm'], EQS: ['SCREENER'], SCREN: ['SCREENER'], RELS: ['STOCK BONDS'], TOP: ['NEWS'], MON: ['MONITOR'], GLCO: ['COMMO'], WIRP: ['RATES', 'f'], WB: ['RATES', 'w'], BTMM: ['RATES', 'm'],
  PORT: ['PORTF'], WEI: ['INDX', 'i'], WEIF: ['INDX', 'f'], IMAP: ['MAP'], US: ['MAP', 'US'], ECO: ['NEWS ECO'], UEMOA: ['UEMOA/DATA'], ECST: ['UEMOA/DATA', 'ecst'], SRCH: ['UEMOA BONDS'], PER: ['BRVM', 'p'], EA: ['CORP RESULT'], 'MOTS CLÉ': ['MOTS CLES'] };
/* raccourcis vers un onglet (ce ne sont pas d'anciens codes) */
const FN_SHORT = { BONDS: ['RATES', 'w'] };
function fnAlias(f) { const a = FN_ALIAS[f] || FN_SHORT[f]; if (!a) return f; if (a[1]) ST.tab[a[0]] = a[1]; return a[0]; }
function go(fn, s, o = {}) {
  fn = fnAlias(fn);
  if (fn && own(FN, fn)) ST.fn = fn; if (s && own(Q.by, s)) ST.sec = s;
  if (!o.nohist) { const cur = [ST.fn, ST.sec]; const last = ST.hist[ST.hpos]; if (!last || last[0] !== cur[0] || (SECFN.has(cur[0]) && last[1] !== cur[1])) { ST.hist = ST.hist.slice(0, ST.hpos + 1); ST.hist.push(cur); if (ST.hist.length > 60) ST.hist.shift(); ST.hpos = ST.hist.length - 1; } }
  try { history.replaceState(null, '', '#' + ST.fn + (SECFN.has(ST.fn) ? '~' + ST.sec : '')); } catch (e) { } ddClose(); wtSync(); render(); window.scrollTo(0, 0);
}
function histGo(d) { const k = ST.hpos + d; if (k < 0 || k >= ST.hist.length) return; ST.hpos = k; const [f, s] = ST.hist[k]; go(f, s, { nohist: true }); }
function fromHash() { let h = ''; try { h = decodeURIComponent(location.hash.slice(1)); } catch (e) { return false; } if (!h) return false; let [f, s] = h.split('~'); const f0 = f; f = fnAlias(f); if (own(FN, f)) ST.fn = f; if (s && own(Q.by, s)) ST.sec = s; return f !== f0; }
/* propriété propre d'un objet (« constructor », « toString »… tapés dans l'adresse ne sont ni une fonction ni un titre) */
function own(o, k) { return !!o && typeof k === 'string' && Object.prototype.hasOwnProperty.call(o, k) && !!o[k]; }
/* adresses : jamais de script (« javascript: ») ni de page « data: » ouverte depuis le terminal — une adresse venue d'un flux
   d'actualités pourrait en contenir ; images et fichiers créés par la page (export, sauvegarde) restent permis */
function badUrl(u) { try { const s = String(u == null ? '' : u).trim(); if (!s) return false; const p = new URL(s, location.href).protocol; return p === 'javascript:' || p === 'vbscript:' || (p === 'data:' && !/^data:image\//i.test(s)); } catch (e) { return true; } }
(() => { const wo = window.open; window.open = function (u, ...a) { return badUrl(u) ? null : wo.call(window, u, ...a); };
  document.addEventListener('click', e => { const a = e.target && e.target.closest ? e.target.closest('a[href]') : null; if (a && badUrl(a.getAttribute('href'))) { e.preventDefault(); e.stopImmediatePropagation(); } }, true); })();
async function render() {
  const seq = ++renderSeq; PF.cur = ST.fn; untip(); PG.acts = []; PG.title = null; $('ptabs').hidden = true; $('ptabs').innerHTML = '';
  renderKeys(); renderTbar(); renderSech(); renderRbar(); renderStatus(); feedState(); clocksTick();
  const m = $('main'); m.innerHTML = '<div class="empty">Chargement…</div>';
  const why = SECFN.has(ST.fn) && ST.fn !== 'MENU' ? avail(ST.fn, sec(ST.sec)) : null;
  if (why) { m.innerHTML = `<div class="pn"><div class="pt">${esc(ykey(sec(ST.sec)))} · ${FN[ST.fn][0]}<span class="code">${ST.fn}</span></div><div class="pb"><div class="empty">Non disponible pour ce titre : ${esc(why)}.<br><br><button class="tb" data-fn="MENU">Voir les fonctions disponibles</button></div></div></div>`; return; }
  if (!PAGES[ST.fn]) { m.innerHTML = '<div class="empty">Fonction en préparation.</div>'; return; }
  try { await PAGES[ST.fn](m, () => seq === renderSeq); if (seq === renderSeq) { countUp(m, seq); pfIdle(); } }
  catch (e) { console.error(e); if (seq === renderSeq) m.innerHTML = `<div class="empty">Impossible d'afficher cette fonction : ${esc(e.message)}</div>`; }
}
/* rangée de touches comme la barre du terminal : GO, F1-F4 (gris), touches vertes du clavier Bloomberg, puis les fonctions de marché */
const BBG_KEYS = [['F1', 'Aide (HELP)', () => go('HELP')], ['F2', 'Govt : obligations (UEMOA BONDS)', () => go('UEMOA BONDS')], ['F3', 'Equity : marché BRVM', () => go('BRVM')], ['F4', 'Index : indices mondiaux (INDX)', () => go('INDX')]];
const BBG_GREEN = [['MONITOR', 'Moniteur de marchés (Market Monitor)', () => go('MONITOR')], ['PRINT', 'Imprimer l’écran', () => window.print()], ['SEARCH', 'Rechercher un titre ou une fonction', () => $('cmd').focus()],
  ['QUOTE', 'Description du titre actif (DES)', () => go('DES', ST.sec)], ['NEWS', 'Actualités (Top News)', () => go('NEWS')], ['MENU', 'Menu des fonctions du titre', () => go('MENU', ST.sec)],
  ['PG BACK', 'Écran précédent', () => histGo(-1)], ['PG FWD', 'Écran suivant', () => histGo(1)]];
function renderKeys() { const f = $('fkeys');
  f.innerHTML = `<button class="fk kgo" data-k="GO" title="Exécuter la commande">GO</button>${BBG_KEYS.map(([k, t]) => `<button class="fk kf" data-k="${k}" title="${esc(t)}">${k}</button>`).join('')}${BBG_GREEN.map(([k, t]) => `<button class="fk${FN[k] && ST.fn === k ? ' on' : ''}" data-k="${k}" title="${esc(t)}"><b>${k}</b></button>`).join('')}<button class="fk kw" data-k="CFG" title="Réglages" aria-label="Réglages">${ICO.gear}</button><i class="fsep"></i>`
    + MKT_KEYS.filter(has).map(k => `<button class="fk ${ST.fn === k ? 'on' : ''}" data-fn="${k}" title="${esc(FN[k][4] + ' — ' + FN[k][3])}"><b>${k}</b><span>${FN[k][0]}</span></button>`).join('');
  f.querySelectorAll('[data-k]').forEach(b => b.onclick = e => { const k = b.dataset.k; if (k === 'GO') { const v = $('cmd').value.trim(); if (v) { $('cmd').value = ''; runCmd(v); } else $('cmd').focus(); return; }
    if (k === 'CFG') { ddOpen(b, stdActs().find(a => a.n === 98).menu()); return; } const a = BBG_KEYS.concat(BBG_GREEN).find(x => x[0] === k); if (a) a[2](); }); }
function renderSecbar() { renderSech(); }
function renderStatus() {
  const L = Q.live && Q.live.qqq, ss = Q.sum.session;
  $('status').innerHTML = `<span>Données au <b>${fd(Q.sum.asof)}</b> · ${Q.sum.secs.length} titres · séance BRVM <b>${ss ? fds(ss.asof) : '—'}</b>${L ? ` · QQQ <b>${num(L.price, 2)}</b> (${L.state === 'REGULAR' ? 'séance' : L.state === 'PRE' ? 'pré-marché' : L.state === 'POST' ? 'après-bourse' : L.state === 'CLOSED' ? 'clôturé' : L.state}${L.time ? `, ${new Date(L.time * 1000).toISOString().slice(11, 16)} UTC` : ''})` : ''}</span>
    <span>Outil d'analyse, pas un conseil en investissement</span>`;
}
let clocksTick = () => { };
function clocks() { const z = [['ABJ', 'Africa/Abidjan'], ['PAR', 'Europe/Paris'], ['NY', 'America/New_York'], ['TYO', 'Asia/Tokyo']];
  clocksTick = () => { const c = $('clocks'); if (c) c.innerHTML = z.map(([k, tz]) => `<span>${k} <b>${new Date().toLocaleTimeString('fr-FR', { timeZone: tz, hour: '2-digit', minute: '2-digit', second: k === 'ABJ' ? '2-digit' : undefined })}</b></span>`).join(''); };
  clocksTick(); setInterval(clocksTick, 1000); }
function feedState() { const L = Q.live && Q.live.qqq, f = $('feed'); if (!f) return; const age = Q.live ? Date.now() / 1000 - (Q.live.ts || 0) : 1e9;
  const live = L && L.state === 'REGULAR' && age < 40 * 60; f.classList.toggle('live', !!live);
  $('feedTxt').textContent = (live ? 'FLUX 15 MIN · ' : '') + (Q.live ? 'MAJ ' + new Date(Q.live.ts * 1000).toLocaleString('fr-FR', { timeZone: 'Africa/Abidjan', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) + ' GMT' : 'EOD ' + fd(Q.sum.asof)); }
function toast(msg, ms = 6000) { const t = $('toast'); t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, ms); }

/* ---------- flux en direct (base de l'artifact écrite par la tâche de synchro) + relecture (hébergement statique) ---------- */
/* ---------- mise à jour silencieuse du terminal : quand une nouvelle version est en ligne, la page se recharge d'elle-même
   au premier moment calme (onglet en arrière-plan, retour sur l'onglet, ou une minute sans action), en gardant l'écran et ses onglets ---------- */
const APP_V = '__APP_V__';
let APP_NEW = false, APP_ACT = Date.now();
function appReload() { try { sessionStorage.setItem('fqt_tabs', JSON.stringify(ST.tab)); } catch (e) { } location.reload(); }
function appMaybe(now) { if (!APP_NEW) return; const a = document.activeElement, typing = a && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) && a.value; if (document.hidden || now || (!typing && Date.now() - APP_ACT > 60000)) appReload(); }
async function appCheck(now) { if (/^__/.test(APP_V) || APP_NEW) { appMaybe(now); return; }
  try { const r = await fetch('version.json?t=' + Date.now(), { cache: 'no-store' }); if (r.ok) { const j = await r.json(); if (j && j.v && j.v !== APP_V) APP_NEW = true; } } catch (e) { } appMaybe(now); }
function initAppUpdate() {
  try { const t = JSON.parse(sessionStorage.getItem('fqt_tabs') || 'null'); if (t) { Object.assign(ST.tab, t); sessionStorage.removeItem('fqt_tabs'); } } catch (e) { }
  ['keydown', 'pointerdown', 'wheel', 'touchstart'].forEach(ev => document.addEventListener(ev, () => { APP_ACT = Date.now(); }, { passive: true, capture: true }));
  document.addEventListener('visibilitychange', () => { if (!document.hidden) appCheck(true); else appMaybe(); });
  setInterval(() => appCheck(false), 5 * 60 * 1000); setInterval(() => appMaybe(false), 20000);
}
async function initFeed() {
  if (!window.claude || !window.claude.use) { setInterval(pollStatic, 5 * 60 * 1000); return; }
  let db = null; try { db = await window.claude.use('db'); } catch (e) { } if (!db) return;
  const apply = () => { applyQuotes(); for (const p of Object.values(Q.ser)) p.then(applyQuoteToSeries); Q.M = {}; feedState(); renderSech(); renderStatus(); if (['MONITOR', 'BRVM', 'MAP'].includes(ST.fn)) render(); };
  try { db.doc('feed/live').onSnapshot(sn => { if (sn.exists) { const d = sn.data(); if (!Q.live || (d.ts || 0) >= (Q.live.ts || 0)) { Q.live = d; apply(); } } }, () => { }); } catch (e) { }
  try { db.doc('feed/quotes').onSnapshot(sn => { if (sn.exists) { const d = sn.data(); if (!Q.quotes || (d.ts || 0) >= (Q.quotes.ts || 0)) { Q.quotes = d; apply(); } } }, () => { }); } catch (e) { }
  try { db.doc('feed/news').onSnapshot(async sn => { if (!sn.exists) return; const d = sn.data(); const cur = await (Q.json['news.json'] || Promise.resolve(null)).catch(() => null);
    if (!cur || (d.ts || 0) > (cur.ts || 0)) { Q.json['news.json'] = Promise.resolve(d); renderNews(); if (['NEWS', 'CN'].includes(ST.fn)) render(); } }, () => { }); } catch (e) { }
}
async function pollStatic() { try { const [l, q] = await Promise.all([fetch(Q.base + 'live.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : null), fetch(Q.base + 'quotes.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : null)]);
  /* nouveau relevé publié (toutes les 15 min) : toutes les données en cache sont relues, la fiche de chaque titre comprise */
  if (!Q.gen && Q.live) Q.gen = Q.live.ts; const fresh = !!(l && l.ts && Q.gen && l.ts !== Q.gen);
  if (fresh) { Q.gen = l.ts; Q.json = {}; try { const S = await fetch(Q.base + 'summary.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : null); if (S && S.secs) { Q.sum = S; Q.json['summary.json'] = Promise.resolve(S); for (const s of S.secs) Q.by[s.id] = s; } } catch (e) { } }
  if (l) Q.live = l; if (q) { Q.quotes = q; applyQuotes(); Q.ser = {}; Q.M = {}; } delete Q.json['news.json']; feedState(); renderSech(); renderStatus(); renderNews();
  const typing = document.activeElement && /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName) && document.activeElement.id !== 'cmd';
  if (!typing && (fresh || ['MONITOR', 'BRVM', 'MAP', 'NEWS', 'BRIEF', 'INDX'].includes(ST.fn)) && !(ST.fn === 'NEWS' && ST.top2 && ST.top2.pause)) render(); } catch (e) { } }
let SYNC_RUN = null;
function bindSync() { const b = $('syncBtn'); if (!b || !SYNC_RUN) return; b.hidden = false; b.onclick = () => SYNC_RUN(b); }
async function initSync() {
  if (!/^trig_/.test(TRIGGER_ID) || !window.claude || !window.claude.use) return; let mcp = null; try { mcp = await window.claude.use('mcp'); } catch (e) { } if (!mcp) return;
  SYNC_RUN = async b => { b.disabled = true; b.textContent = '…';
    try { await mcp.callTool('Claude Code Remote', 'fire_trigger', { trigger_id: TRIGGER_ID }, { cache: false }); toast('Synchronisation lancée : le dernier relevé arrive dans 2 à 4 minutes, sans recharger la page.', 9000); b.textContent = 'OK'; }
    catch (e) { const c = e && e.code; b.textContent = 'SYNC'; toast(c === 'rate_limited' ? 'Trop de demandes rapprochées : réessaie dans quelques minutes.' : c === 'not_granted' || c === 'consent_required' ? 'Autorisation refusée : ouvre le menu Autorisations de la page.' : 'La synchro n’a pas pu être lancée (' + (c || 'erreur') + '). La mise à jour planifiée tourne quand même.', 9000); }
    finally { setTimeout(() => { b.disabled = false; b.textContent = 'SYNC'; }, 60000); } };
  bindSync();
}

/* ---------- mode anonyme (liens temporaires de démonstration) : les noms des fournisseurs de données disparaissent de l'écran ---------- */
const ANON = typeof window !== 'undefined' && !!window.FQT_ANON;
const ANON_RX = [/\b(?:Yahoo Finance|Yahoo|TradingView|CNN|CNBC|MarketWatch|Investing\.com)\b/g];
function anonText(t) { let o = t.replace(/\b(?:Sources?|Calendrier|Consensus publié par|Cotations différées)\s*(?::|\()[^.]*?(?:\.(?=\s|$)|$)/g, ''); for (const rx of ANON_RX) o = o.replace(rx, ''); return o.replace(/\b(Sources?|Calendrier|Données|Consensus publié par)\s*:?\s*(?:[,·;/()]\s*|\s(et|via|ou)\s)*(?=[.;)]|$)/g, '').replace(/\(\s*[,;·/]*\s*\)/g, '').replace(/\s+([,.;])/g, '$1').replace(/([,·;/])\s*(?=[,·;/.)])/g, '').replace(/ {2,}/g, ' '); }
function anonNode(root) { if (!ANON || !root) return; const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); const L = []; while (w.nextNode()) L.push(w.currentNode); for (const n of L) { const v = anonText(n.nodeValue); if (v !== n.nodeValue) n.nodeValue = v; }
  root.querySelectorAll && root.querySelectorAll('[title]').forEach(e => { const v = anonText(e.title); if (v !== e.title) e.title = v; }); }
if (ANON) { document.documentElement.classList.add('anon'); new MutationObserver(ms => { for (const m of ms) for (const n of m.addedNodes) { if (n.nodeType === 1) anonNode(n); else if (n.nodeType === 3) { const v = anonText(n.nodeValue); if (v !== n.nodeValue) n.nodeValue = v; } } }).observe(document.documentElement, { childList: true, subtree: true }); }

/* ---------- démarrage ---------- */
async function boot() {
  readCL(); renderKeysSkeleton(); try { ST.newsMin = localStorage.getItem('fqt.newsMin') === '1'; } catch (e) { }
  try { Q.sum = await getJSON('summary.json'); } catch (e) { $('main').innerHTML = `<div class="empty">Données introuvables (data/summary.json).</div>`; return; }
  for (const s of Q.sum.secs) Q.by[s.id] = s;
  try { Q.live = await getJSON('live.json'); } catch (e) { } try { Q.quotes = await getJSON('quotes.json'); applyQuotes(); } catch (e) { }
  for (const t of WT.list) { const a = FN_ALIAS[t.fn] || FN_SHORT[t.fn]; if (a) t.fn = a[0]; } if (WT.cur >= WT.list.length) WT.cur = 0; const t0 = WT.list[WT.cur]; if (t0 && FN[t0.fn]) { ST.fn = t0.fn; if (Q.by[t0.sec]) ST.sec = t0.sec; }
  initAppUpdate(); fromHash(); initCmd(); clocks(); applyPref();
  // ouverture rapide : au survol (ou au toucher) d'un lien de fonction ou d'une ligne de titre, ses fichiers sont lus à l'avance
  let pfHov = null; const pfHover = e => { if (!PREF.fast || !e.target.closest) return; const f = e.target.closest('[data-fn],[data-sec][data-to]'); if (!f) return;
    clearTimeout(pfHov); pfHov = setTimeout(() => { const x = f.dataset.fn || f.dataset.to, al = FN_ALIAS[x] || FN_SHORT[x], fn = al ? al[0] : x; if (fn && own(FN, fn)) pfLoad(fn, f.dataset.s || f.dataset.sec || ST.sec); }, e.type === 'touchstart' ? 0 : 120); };
  document.addEventListener('mouseover', pfHover, { passive: true }); document.addEventListener('touchstart', pfHover, { passive: true });
  document.addEventListener('click', e => { const f = e.target.closest('[data-fn]'); if (f && !f.closest('#ddm')) { const a = FN_ALIAS[f.dataset.fn] || FN_SHORT[f.dataset.fn]; if (f.dataset.t) ST.tab[a ? a[0] : f.dataset.fn] = f.dataset.t; go(a && f.dataset.t ? a[0] : f.dataset.fn, f.dataset.s); return; }
    const s = e.target.closest('[data-sec]'); if (s && !e.target.closest('a')) { const id = s.dataset.sec; go(s.dataset.to || (SECFN.has(ST.fn) && ST.fn !== 'MENU' && !avail(ST.fn, sec(id)) ? ST.fn : 'MENU'), id); } });
  window.addEventListener('hashchange', () => { const a = ST.fn + ST.sec; const old = fromHash(); if (old || ST.fn + ST.sec !== a) go(ST.fn, ST.sec); });
  go(ST.fn, ST.sec); renderNews(); initFeed(); initSync();
}
function renderKeysSkeleton() { $('fkeys').innerHTML = MKT_KEYS.map(k => `<button class="fk" data-fn="${k}"><b>${k}</b></button>`).join(''); }
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

/* ligne et colonne suivies dans les tableaux : toucher (iPhone) une case marque sa ligne ; dans une matrice (.hm), la colonne de la
   case survolée ou touchée est marquée aussi */
(() => { let rs = null, cs = [];
  const colOf = td => { const tb = td.closest('table.hm'); if (!tb) return []; const k = td.cellIndex; return [...tb.rows].map(r => r.cells[k]).filter(Boolean); };
  const mark = td => { cs.forEach(c => c.classList.remove('csel')); cs = td ? colOf(td) : []; cs.forEach(c => c.classList.add('csel')); };
  document.addEventListener('mouseover', e => { const td = e.target.closest && e.target.closest('table.hm td'); if (td) mark(td); else if (cs.length) mark(null); }, { passive: true });
  document.addEventListener('touchstart', e => { const td = e.target.closest && e.target.closest('table.t td'); if (rs) rs.classList.remove('rsel'); rs = td ? td.parentElement : null; if (rs) rs.classList.add('rsel'); mark(td && td.closest('table.hm') ? td : null); }, { passive: true });
})();
