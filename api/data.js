// Relais des données du terminal : le site lit /data/<fichier>.json ; ce relais les prend sur la branche « data »
// du dépôt (réécrite toutes les 15 minutes par GitHub Actions) sans redéployer le site. Cache CDN : 60 s.
// Secours : si GitHub ne répond plus (ou ne connaît plus le dépôt), lecture de la copie de secours quotidienne
// (dépôt privé hors GitHub, clé de lecture seule dans la variable GITLAB_READ_TOKEN de Vercel) ; données au plus d'un jour.
const REPOS = ['ghosht-elphantomo/noodleloop'];
const ORIGINS = [
  ...REPOS.map(r => p => `https://raw.githubusercontent.com/${r}/data/data/${p}?v=${Math.floor(Date.now() / 60000)}`),
  ...REPOS.map(r => p => `https://cdn.jsdelivr.net/gh/${r}@data/data/${p}`),
];
const GL_TOKEN = process.env.GITLAB_READ_TOKEN || '';
const GL_PROJECT = encodeURIComponent(process.env.GITLAB_PROJECT || 'loopvault/archive-vault');
const glUrl = p => `https://gitlab.com/api/v4/projects/${GL_PROJECT}/repository/files/${encodeURIComponent('data/' + p)}/raw?ref=data`;

// GitHub en panne ? (un 404 peut venir d'un fichier absent ou d'un dépôt devenu inaccessible) : un fichier témoin
// toujours présent est vérifié, résultat gardé 5 minutes par instance.
let ghState = { t: 0, down: false };
async function githubDown() {
  if (Date.now() - ghState.t < 300000) return ghState.down;
  let down = true;
  try {
    const r = await fetch(ORIGINS[0]('live.json'), { headers: { 'User-Agent': 'fqt-terminal' }, signal: AbortSignal.timeout(8000) });
    down = !r.ok;
  } catch (e) { down = true; }
  ghState = { t: Date.now(), down };
  return down;
}

// Adresses des documents : remplacées par des adresses du site (/doc/…, servies par vercel.json), pour que le navigateur
// n'affiche ni n'appelle jamais les sites d'origine ; les autres pages d'origine ne sont plus liées.
// documents anciens : chemin d'origine transmis sous forme de jeton (base64url) à api/doc.js, qui va le chercher dans l'archive
const tok = p => { let x = p; try { x = JSON.parse('"' + p + '"'); } catch (e) { /* chemin déjà brut */ } return Buffer.from(x, 'utf8').toString('base64url'); };
const DOC_RW = [
  [/"W(\d{8,14}):https?:\/\/www\.brvm\.org(?::80)?\/([^"]*)"/g, (m, ts, p) => `"/doc/a/${ts}/${tok(p)}"`],
  [/"W(\d{8,14}):https?:\/\/bfin\.brvm\.org(?::80)?\/([^"]*)"/g, (m, ts, p) => `"/doc/c/${ts}/${tok(p)}"`],
  [/https?:\/\/www\.brvm\.org\/sites\/default\/files\//g, '/doc/b/'],
  [/https?:\/\/bfin\.brvm\.org\/boc\/BOC_JOUR\//g, '/doc/f/'],
  [/https?:\/\/(?:www\.)?richbourse\.com\//g, '/doc/r/'],
  // (adresse effacée jusqu'à la fin de l'adresse seulement : jamais au-delà d'un espace ou d'un guillemet échappé, sinon le JSON serait abîmé)
  [/https?:\/\/(?:www\.)?sikafinance\.com\/[^"\\\s]*/g, ''],
  [/https?:\/\/(?:[a-z]+\.)?brvm\.org\/[^"\\\s]*/g, ''],
  // libellés de provenance dans les données (jamais affichés, mais lisibles dans les fichiers)
  [/"src":"(?:bulletin officiel de la cote[^"]*|nasdaq\.com · sec\.gov|[^"]*\bbrvm\.org\b[^"]*)"/g, '"src":""'],
  [/archive SikaFinance/g, 'archive'],
  [/https?:\/\/(?:www\.)?(?:eia\.gov|iea\.org)\/[^"\s)]*/g, ''],
  [/"src":"(?:EIA|AIE|IEA)\b[^"]*"/g, '"src":""'],
  [/ \(EIA, /g, ' ('],
  [/dernière édition EIA/g, 'dernière édition disponible'],
  [/ publiés par l['’](?:AIE|EIA)\b/g, ' publiés'],
  [/Bulletin officiel de la cote/g, 'Bulletin de la cote'],
  [/"c":"Avis de la BRVM"/g, '"c":"Avis officiel"'],
];
const NEWS_RW = [[/"s":"brvm\.org"/g, '"s":"Publication officielle"'], [/"s":"Sika ?Finance"/gi, '"s":""']];
const docRw = (t, p) => (p === 'news.json' ? DOC_RW.concat(NEWS_RW) : DOC_RW).reduce((s, [rx, to]) => s.replace(rx, to), t);
// noms publics de certains fichiers (le site demande l'alias, le relais lit le vrai fichier)
const ALIAS = { 'oil_w.json': 'eia_wpsr.json' };

async function send(res, r, cdn, p) {
  const buf = Buffer.from(docRw(Buffer.from(await r.arrayBuffer()).toString('utf8'), p), 'utf8');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'public, max-age=0, must-revalidate');
  res.setHeader('Vercel-CDN-Cache-Control', cdn);
  res.statusCode = 200; res.end(buf);
}

async function fromGitLab(res, p) {
  if (!GL_TOKEN) return false;
  try {
    const r = await fetch(glUrl(p), { headers: { 'PRIVATE-TOKEN': GL_TOKEN, 'User-Agent': 'fqt-terminal' }, signal: AbortSignal.timeout(15000) });
    if (!r.ok) return false;
    await send(res, r, 'max-age=300, stale-while-revalidate=3600', p);
    return true;
  } catch (e) { return false; }
}

module.exports = async (req, res) => {
  const q = String((req.query && req.query.p) || '').replace(/^\/+/, ''), p = ALIAS[q] || q;
  if (!p || p.includes('..') || !/^[A-Za-z0-9_\-./]+\.json$/.test(p)) { res.statusCode = 400; res.end('bad path'); return; }
  if (String((req.query && req.query.via) || '') === '2') {  // essai du secours seul
    // (lecture de la copie à chaque appel : refusée avec des paramètres en plus, qui contourneraient le cache et épuiseraient la clé
    // de lecture ; clé d'essai exigée si le propriétaire crée la variable SECOURS_KEY dans Vercel)
    const extra = Object.keys(req.query || {}).filter(k => !['p', 'via', 'k', 'path'].includes(k));
    if (extra.length || (process.env.SECOURS_KEY && String(req.query.k || '') !== process.env.SECOURS_KEY)) {
      res.statusCode = 400; res.setHeader('Cache-Control', 'no-store'); res.end('bad request'); return;
    }
    if (await fromGitLab(res, p)) return;
    res.statusCode = 503; res.setHeader('Cache-Control', 'no-store'); res.end('unavailable'); return;
  }
  let last = 502;
  for (const [i, url] of ORIGINS.map((f, i) => [i, f(p)])) {
    try {
      const r = await fetch(url, { headers: { 'User-Agent': 'fqt-terminal' }, signal: AbortSignal.timeout(15000) });
      if (r.status === 404) { last = 404; continue; }
      if (!r.ok) { last = r.status; continue; }
      await send(res, r, i < REPOS.length ? 'max-age=60, stale-while-revalidate=600' : 'max-age=30', p);
      return;
    } catch (e) { last = 504; }
  }
  if (GL_TOKEN && (last !== 404 || await githubDown()) && await fromGitLab(res, p)) return;
  res.statusCode = last; res.setHeader('Cache-Control', 'no-store'); res.end('unavailable');
};
