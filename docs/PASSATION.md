# Passation — où en est le travail, ce qui reste

À lire en premier par toute nouvelle session. Mis à jour : 19/10/2026, 17 h 20 (Paris).
Une session qui termine une étape importante met ce fichier à jour (état, reste à faire, pièges).

## Démarrer une session

1. Ajouter ce dépôt (nom donné par le propriétaire au démarrage, accès en écriture), le cloner, puis récupérer les branches de données avec
   `git fetch origin +refs/heads/X:refs/remotes/origin/X` (comptes, dividendes, boc, data, raw, histo, site, probe, export, refs, sonde) : elles sont
   réécrites à chaque passage, un simple `git fetch origin X` ne les met pas à jour.
2. Lire : ce fichier, les règles en tête de `SAUVEGARDES.md`, `docs/GUIDE.md` ; `docs/QLAB2_VALORISATION.md` avant de toucher
   à QLAB.
3. Répondre au propriétaire en français uniquement (jamais d'anglais, même une ligne), de façon concise ; pour une tâche : aller
   jusqu'au bout sans messages d'étape, puis un seul bilan à la fin (répondre normalement à ses questions).
4. Installer les outils de test : `npm install -g terser@5.36.0`, `pip install playwright` (Chromium), puis faire un premier
   parcours de référence du site avant toute modification (`outils/essais/test_site.sh`, voir `docs/GUIDE.md`, « En local »).

## Règles (obligatoires)

- Point de restauration dans `SAUVEGARDES.md` AVANT toute modification (main, site, et branche comptes si la lecture est touchée).
- Chaque bug corrigé reçoit, avec sa correction, son contrôle automatique dans `outils/controle/non_retour.py` (entrée `@bug`),
  puis `python3 outils/controle/non_retour.py --liste` régénère `outils/controle/BUGS_CORRIGES.md` : le contrôle du matin
  signale le bug s'il revient (règle du propriétaire, 19/10/2026).
- Après chaque modification : tester TOUT le site et toutes les données ; signaler tout problème trouvé, même sans lien avec la
  modification ; ne publier que si tout est bon. « Tant que ça ne casse rien, on peut le faire. »
- Données : « pas de faux chiffres, en aucun cas » (outil pour professionnels). Tout montant affiché doit être lu dans un document
  officiel et vérifiable ; un montant calculé n'est accepté que si un autre montant publié le confirme ; dans le doute, la case
  reste vide. Une modification de la lecture ou de la consolidation ne doit qu'ajouter : comparer deux constructions
  (`outils/essais/cmp_fund.py`, `fa_ab.py`) et exiger 0 montant changé et 0 retiré, sauf erreur prouvée sur le document.
- Commits auteur `fqt-bot <41898282+github-actions[bot]@users.noreply.github.com>` ; pushes groupés sur main ; aucune
  nouvelle branche ; ne pas toucher aux réglages GitHub ou Vercel qui marchent.
- Rien sur la personne du propriétaire (nom, pseudo, e-mail) dans le dépôt ; jamais l'ancien nom du dépôt ni l'adresse du site
  dans les fichiers ; README.md et LICENSE neutres. Sur le site : aucun nom de source, lien GitHub ou e-mail affiché ; pas de logos
  de sociétés copiés d'autres sites.
- Aucune donnée d'utilisateur dans le dépôt ; ne jamais demander de coller une clé secrète dans la conversation.
- Projet distinct du screener FOFCO BRVM (autre dépôt, autre site) : ne jamais mélanger les deux.
- Ne pas pousser de travail inachevé ou non testé (le contrôle de fin de tour demande de tout valider : mettre le travail en
  cours de côté avec `git stash -u` plutôt que de le publier).
- Le propriétaire ne veut pas d'e-mails d'échec : une automatisation ne doit échouer que pour une vraie panne ; un contrôle qui
  ne passe pas écrit un rapport et garde la dernière bonne version.

## Pièges techniques

- Depuis l'espace de travail de Claude, les journaux et fichiers des passages GitHub ne se téléchargent pas (stockage bloqué) :
  lire les annotations (`gh api repos/{owner}/{repo}/check-runs/<job>/annotations`, lancé dans le clone) et faire publier un résultat
  détaillé sur la branche de diagnostic `probe` (voir `archives.yml`). Le site non plus n'est pas joignable : vérifier par les
  branches `data` et `site` et par les déploiements (`gh api repos/{owner}/{repo}/deployments`). Le relais `gh`
  refuse les adresses par numéro de dépôt : utiliser `gh api repos/{owner}/{repo}/actions/runs/...` plutôt que `gh run view`.
- main reçoit des commits automatiques (« mise à jour … ») : `git pull --rebase origin main` juste avant chaque push.
- Le code publié est compacté par terser (`python3 build.py`) ; `index.html`, `public/index.html` et `public/version.json` sont
  régénérés et publiés avec toute modification de `web/`.
- Test du site : `outils/essais/` (dans le dépôt depuis le 19/10/2026). Construction locale de la base (pour comparer deux
  versions du code) : même commande que l'étape du soir de `terminal.yml` (`build_terminal.py` sans `--live`), avec les branches
  raw (`brvm_src/`, sources), boc, comptes (`comptes.json`) et dividendes ; construire avec le code de main puis avec le code
  modifié, mêmes entrées, puis `cmp_fund.py` et `fa_ab.py`. Les boucles `sleep` sont bloquées dans l'espace de travail : lancer
  les longs calculs en arrière-plan.
- Relecture complète des comptes (`comptes.py`) : ~20 min de calcul ; la répartir sur deux processus en local.
- Automatisations qui lisent des PDF : Ubuntu 24.04 (Ubuntu 26.04 lit autrement une partie des scans).
- L'espace de travail a 2 processeurs : un seul parcours Playwright à la fois.

## État au 19/10/2026, 19 h 15

- **Publié le 19/10/2026 (demandes du propriétaire)**, chaque fois après le parcours complet du site (avant / après) :
  - `0ed87f89` (17 h 50) : QLAB 3 « Prévisions » retiré (onglet, code, cahier des charges ; `qlabp/` quitte les données publiées
    au premier passage du Terminal, copie gardée sur `raw`) ; MAP : taille des cases selon la variation du jour par défaut
    (ou égale, ou capitalisation), zoom 1× à 3× et déplacement, bouton Agrandir, carte sur toute la largeur ; plus aucun
    symbole affiché en émoji sur iPhone (◀ ▶ 🔧 ⚙ 🔔 remplacés par des icônes dessinées, `ICO` dans `web/core.js`).
  - `0866f0b2` (17 h 54) : contrôles automatiques — `controle.yml` (chaque matin 06:10 UTC, rapport vert / orange / rouge sur
    la branche `probe`, dossier `controle/`) et garde des données avant chaque publication (`scripts/garde.py`).
  - `21502169` (18 h 19) : BRVM (Saison des résultats, Publications attendues et retards, Exposition pays), DIVC
    (Aristocrates du dividende, Dividende net et encaissements), nouvelle fonction BANK ; méthodes dans le guide.
  - `f7eb7baf` (18 h 35) : PORTF, import de relevés (CSV, Excel .xlsx, PDF à texte, lignes collées) lus dans le navigateur,
    écran de contrôle avant validation, sauvegarde et restauration du portefeuille en fichier. Non lus : photos et PDF
    scannés (il faudrait un module de lecture d'images ajouté au site : décision du propriétaire).
  - `ab9c9b5b` (19 h 05) : présentations DES des 48 sociétés réécrites (`seed/des_fqt.json`, preuves dans
    `seed/des_fqt_preuves.json`), en ligne après le passage du soir (22:35 UTC) ; page de relecture « Miroir DES » remise au
    propriétaire (texte actuel, notre texte, preuve de chaque fait). 14 textes vérifiés tels quels, 34 corrigés à la relecture
    indépendante, 0 à revoir ; Uniwax et BIIC raccourcis (faits non datés ou non prouvés retirés).
  - `8017ef1d` (19 h 07, déploiement de production réussi) : sécurité sans risque — deux en-têtes sur la page du terminal
    (Content-Security-Policy partielle, Cross-Origin-Opener-Policy), `.gitignore` des fichiers de secrets ; la liste de
    contrôle sécurité du propriétaire (20 points) est gardée pour le backend (le reste en dépend).
  - Vérifié : déploiement de production `0866f0b2` réussi (15:54 UTC), branche site au même code. Le 19/10 de 15 h 30 à
    16 h 10 UTC environ, incident GitHub Actions (passages en attente) : rien à faire, les passages repartent seuls.
- **Lecture des 34 documents de l'archive web** (passage des comptes du 19/10, 16 h 53, publié à 17 h 34) : 34 documents lus
  (21 vérifiés, 6 non vérifiés, 7 illisibles) ; les 6 031 documents déjà lus sont identiques, octet pour octet, avant / après
  (aucun montant changé, aucun retiré). Les exercices ajoutés arrivent dans les données au passage du soir (22:35 UTC).
- Premier contrôle quotidien lancé à la main le 19/10 (en attente à cause de l'incident GitHub) : lire son rapport sur `probe`
  (`controle/rapport.md`) ; attendu : orange tant que `qlabp/` est encore publié, puis vert.

## État au 19/10/2026, 17 h 20

- **Lecture des documents de la BRVM terminée** : 6 033 documents au registre (branche comptes), 1 599 avec au moins un exercice
  vérifié, 0 restant. Lecture répartie sur 6 machines quand il en reste au moins 60, sinon une seule (`comptes.yml`,
  `scripts/comptes_merge.py`). Depuis le 18/10 au soir, chaque passage à une seule machine échouait à la mise en commun (part
  téléchargée sans sous-dossier) : rien n'était publié et un e-mail d'échec partait ; corrigé le 19/10 à 16 h 02 (`247319d8`) et
  vérifié : passage à une machine réussi et publié le 19/10 à 16 h 49 (branche comptes `7e8f9959`, 6 033 documents, 0 restant).
- **Publié le 19/10/2026 à 16 h 42 (commit `12033902`, demandes du propriétaire du jour ; déploiement de production réussi)** :
  - Barre de commande : la fonction est reconnue d'abord, le reste est lu comme un titre (ticker, nom, nom usuel) ; « NSIA FA »,
    « Sogb CN », « Orange CI FA », « SGBCI GP » ouvrent la fonction ; un texte libre n'ouvre plus MOTS CLES (message).
  - MOTS CLES : onglet « Historique de recherche » (90 jours, navigateur seulement).
  - FA : note de méthode retirée (une ligne d'unités et de signes) ; postes et exercices entièrement vides masqués ; cases
    calculées en italique avec infobulle.
  - MAP : une case par société (nom court et variation du jour), réglage « Regroupement : Aucun / Par secteur » (par défaut :
    aucun), pour BRVM, ETF et NDX.
  - Données FA : unité déduite pour les documents sans ligne d'unité (8 exercices : Servair Abidjan 2004-2011, SOGB 2005) et
    sous-totaux SYSCOHADA confirmés par un autre montant publié (116 montants) : +601 cases dans FA, +43 valeurs dans les
    fondamentaux, 0 changé, 0 retiré (construction complète avant / après). QLAB : intervalles de prévision à peine modifiés
    (quelques séries plus longues).
  - Vérifié en production à 17 h 15 : branche data du 19/10 15 h 14 UTC avec Servair Abidjan 2004-2011 (comptes SYSCOHADA,
    fondamentaux et `fa/ABJC.json`) et SOGB 2005 ; branche site et déploiement de production au code du commit `12033902`.
  - 34 documents retrouvés dans l'archive web ajoutés à la lecture (`seed/archives_comptes.json`) : passage de lecture lancé à
    la main le 19/10 à 16 h 53 (comptes.yml), encore en cours de publication à 17 h 20 — vérifier le résultat : documents lus
    (champ « wb » dans index.json de la branche comptes), exercices ajoutés, aucun montant existant changé.
- **Audit du 19/10/2026** : site complet en local avec le nouveau code (421 pages et onglets, 0 erreur JavaScript ; iPhone 13,
  99 pages, 0 débordement ; QLAB 48 × 6, 0 texte suspect ; aucun nom de source ni lien interdit). Concordance avec les archives
  SikaFinance 2014-2025 : 1 711 comparaisons, 238 écarts, tous expliqués, aucune correction : PER (164 ; SikaFinance prend le
  cours du jour de la capture, nous celui de fin d'exercice), BNPA et dividende (56 ; nos séries sont ajustées des
  fractionnements et attributions gratuites, BOA ×2, ×1,6, ×1,5), chiffre d'affaires et résultat (12 ; périmètres de Vivo Energy
  CI et Servair, comptes retraités d'Unilever CI 2019-2020), ETI (conversion des dollars).
- Base tierce : dernière mise à jour 07/10/2026 (12 jours ; « figée » signalée au-delà de 21 jours dans `boc_check.json`).

## Données manquantes (FA) — inventaire et suite

Inventaire du 19/10/2026 (production) : 1 697 cases « poste non publié » dans des exercices vérifiés ; 79 exercices manquants
alors qu'un document existe, 17 sans document. Causes des exercices manquants : unité indéterminée 41 (8 comblés le 19/10),
comptes semestriels 20 (normal : FA est annuel), dollars 16 (ETI ; taux de change de clôture à appliquer), écartés par les
contrôles 13, avant le premier exercice suivi (NEIC) 13, présentations 4, autre entité (CFAO « SARI ») 2.
Lignes les plus souvent vides : capitaux propres 230 (+102 banques), résultat des activités ordinaires 196, résultat financier
136, dettes financières 113, coût du risque 110 et résultat brut d'exploitation 109 des banques, chiffre d'affaires 107.

Suite possible, toujours sans chiffre invérifiable :
- Lecteur des anciens comptes bancaires au format des codes BCEAO (BOA Burkina 2011-2016, etc.) : lecture des scans bruitée
  (traits verticaux « | » pris pour des chiffres) ; 86 documents au format codes, 68 déjà lus.
- Les 13 exercices écartés par les contrôles, un par un sur les documents.
- 45 montants complétés entre deux lectures d'un même scan, lus autrement par une troisième lecture : à revoir sur les documents.
- SUCRIVOIRE 2019 : exercice vérifié mais total du bilan absent des fondamentaux.
- Ruptures à examiner dans les séries (saut anormal d'une année à l'autre) : BOA Sénégal résultat 2014, SMB CI 2019, Solibra 2022,
  SICABLE 2021, BOA Bénin 2006, Onatel 2011, SITAB 2003 — vérifier sur les documents s'il s'agit d'une vraie variation ou d'une
  erreur d'unité ou de lecture.
- Lecteur de documents (`api/doc.js`) : mesurer la taille et la disponibilité des anciens documents servis depuis l'archive web
  (limite 4,4 Mo) ; envisager la lecture en flux pour les gros fichiers.

## Reste à faire

Ordre décidé par le propriétaire (samedi 17/10, revu le 19/10) — commencer à son signal dans la nouvelle session :

0. Vérifier le passage automatique des comptes de la nuit (4 h 17 UTC) et le premier rapport de `controle.yml` (branche `probe`,
   `controle/rapport.md`). Le passage du 19/10 à 16 h 53 est vérifié (voir l'état ci-dessus). Une tâche programmée unique fait
   aussi un contrôle mardi 20/10 à 9 h (lecture seule).
1. **Fait le 19/10** — **Contrôles automatiques** : un seul script de vérification (données + parcours du site) lancé avant et après chaque
   modification et chaque nuit par une automatisation qui écrit un rapport vert / orange / rouge sans faire échouer le passage
   (pas d'e-mails d'erreur) : fichiers présents, non vides, frais, nombre de lignes comparé au passage précédent, doublons, valeurs
   aberrantes, cohérence entre fichiers ; site : toutes les fonctions et onglets, QLAB 48 × 3, aucune erreur JavaScript, aucun
   NaN / undefined / null, aucun nom de source, aucun émoji ; instantané des chiffres clés avant / après ; confidentialité ;
   auto-protection (un fichier vide ou anormalement court n'est pas publié, la dernière bonne version est gardée). Partir de
   `outils/essais/`.
2. **Nouvelles fonctions** :
   - Fait le 19/10 : BRVM (Saison des résultats ; Publications attendues et retards ; Exposition pays) ; DIVC (Aristocrates du
     dividende ; Dividende net et encaissements des positions de PORTF) ; fonction BANK (comparaison du dernier exercice,
     historique sur 10 ans) ; plus aucun émoji sur iPhone.
   - Fait le 19/10 : PORT, import de relevés et sauvegarde (photos non lues, voir ci-dessus) ; DES, présentations des 48
     sociétés réécrites et vérifiées (à vérifier dans DES après le passage du soir du 19/10).
   - Reste pour DIVC : dividende brut et retenue à la source par pays — le net est publié partout ; le brut et l'impôt
     n'existent que sur la branche `dividendes` (avis lus), à faire passer dans `dividends.json` (changement de la
     construction) avant de les afficher ; taux de chaque pays à vérifier sur un texte officiel.
   - Secours BRVM, suite : combler ce que l'essai « sans la base tierce » a montré manquant — séries BPA, dividende et PER,
     fiches des sociétés, cours d'avant décembre 2013.
   - **Problème trouvé le 19/10 (à corriger avant l'audit)** : des documents rangés sous une autre société dans la liste des
     publications (registre de la branche `comptes`, MOTS CLES, CN) — au moins : Erium ← rapport BOA Sénégal T1 2017 ;
     ETI ← états financiers 2017 d'Ecobank CI ; Sonatel ← résultats S1 2017 et rapport T3 2022 d'Onatel ; CFAO ← états
     financiers 2018-2023 de Tractafric ; BOA Burkina ← états financiers 2021 de BOA CI ; BOA Niger ← rapport T1 2019 de
     BOA Sénégal ; Bernabé ← comptes 2006 de CFAO ; ETI ← plusieurs documents d'Ecobank CI. Vérifié : aucun de ces
     montants ne figure dans les chiffres affichés (FA, fondamentaux) ; mais ils sont classés sous la mauvaise société.
     Correction proposée : contrôle du nom de la société dans l'intitulé et le nom du fichier avant de rattacher un
     document (`cpt_events`), liste des exceptions vérifiées à la main, puis relecture des seuls documents concernés.
   - Point à vérifier : Filtisac, dividende de l'exercice 2024 à 1 161,6 FCFA (plus 564,96 exceptionnel) pour un cours de
     1 805 : rendement affiché 64 % et distribution 3 516 % (avis à relire).
3. **Fluidité et vitesse** (réglage désactivé par défaut ; ne touche que l'affichage).
4. Audit complet.
5. Seulement quand tout est propre, testé et audité : migration « deux dépôts » (privé + public neutre) avec le propriétaire,
   nettoyage de l'historique (ancien pseudonyme, pages brutes des sources) ; puis kit serveur.

## Migration deux dépôts : pourquoi et comment

Complément à la passation (texte du propriétaire, 19/10/2026). À lire avant le point 5 du « Reste à faire ». Ne rien
lancer maintenant : la migration se fait seulement quand tout est propre, testé et audité, avec l'accord du propriétaire à
chaque étape.

**1. Aujourd'hui.** Tout est dans un seul dépôt public :
- le code du site et les scripts de lecture des documents ;
- les modèles de calcul (QLAB, ratios) et les sources consultées ;
- les automatisations et les données (branches data, raw, comptes, dividendes, boc, histo) ;
- tout l'historique, où restent l'ancien pseudonyme du propriétaire et des pages brutes des sources.

N'importe qui peut tout voir, tout copier et remonter du site au dépôt.

**2. Pourquoi ça ne peut pas rester comme ça.**
- L'accès au terminal sera vendu par abonnement (tarifs fixés le 19/10). Avec un dépôt public, n'importe qui récupère
  gratuitement le terminal entier, données comprises : l'abonnement ne vaut alors plus rien. Les CGU interdiront la copie,
  mais rien ne l'empêche techniquement.
- Les copieurs ne doivent voir ni les modèles de calcul, ni les sources, ni les automatisations. Aucune source ne doit
  être identifiable, ni par un visiteur ni par une IA, et on ne doit pas pouvoir remonter facilement du site au dépôt.
- Rien sur la personne du propriétaire, même dans un dépôt privé.
- Données de la BRVM : si une licence doit être négociée, mieux vaut que nos données ne soient pas en libre accès.

**3. Pourquoi pas tout en privé : le coût des automatisations.**
- Dépôt public : les automatisations GitHub (machines standard) sont gratuites et illimitées.
- Dépôt privé : le compte gratuit n'a que 2 000 minutes par mois (3 000 avec Pro), puis 0,006 $ la minute.
- Mesure du 19/10 : environ 2 000 minutes par jour (Métronome ~1 000, Terminal ~800 sur 149 passages, comptes ~130),
  soit ~60 000 minutes par mois, donc au moins ~350 $ par mois en privé.
- D'où le partage :
  - tout ce qui a de la valeur passe en privé ;
  - un dépôt public au nom neutre ne garde que le « moteur » des automatisations. Il tourne gratuitement et va chercher le
    code privé avec une clé secrète en lecture seule.

**4. Plan validé le 17/10** (une étape à la fois, point de restauration avant chacune).
- a) Déjà fait :
  - copie de secours chaque nuit vers un dépôt privé hors GitHub (`copie.yml`) ;
  - le site lit cette copie si GitHub ne répond plus (`api/data.js`, `GITLAB_READ_TOKEN`).
- b) Le dépôt actuel passe en privé : code, docs, historique, données. Nouveau dépôt public au nom neutre, sans historique,
  qui ne contient que les fichiers d'automatisation. Chaque passage :
  - récupère le code privé avec une clé en lecture seule, rangée dans les secrets GitHub ;
  - fait le travail ;
  - publie le résultat dans le dépôt privé.
- c) Kit de déménagement vers un serveur (Oracle gratuit ou 5 à 20 € par mois), au cas où GitHub bloquerait un jour.
- d) Plus tard, avec le backend Supabase : données réservées aux utilisateurs connectés.
- e) Nettoyage de l'historique du dépôt privé (ancien pseudonyme, pages brutes des sources). C'est une réécriture
  irréversible : seulement avec l'accord explicite du propriétaire.

**5. Pièges à prévoir avant de migrer.**
- Journaux visibles : dans un dépôt public, tout le monde voit les journaux des passages.
  - Les noms d'étapes doivent être neutres (aujourd'hui ils citent des sources : « FRED, CBOE, CNN… », « PDF de brvm.org »).
  - Rien d'affiché dans les journaux : ni adresse, ni donnée, ni secret.
  - Aucun fichier de passage public (artifacts, caches).
  - Aucune automatisation lancée par une demande de modification (pull request) venue d'un inconnu.
- Lecture des données par le site : aujourd'hui, `api/data.js` lit les données en clair sur GitHub (raw.githubusercontent
  et jsdelivr). Une fois le dépôt privé, jsdelivr ne marchera plus et GitHub demandera une clé de lecture dans les réglages
  Vercel (c'est le propriétaire qui la met). Préparer la bascule pour que le site ne s'arrête jamais.
- Vercel : il est relié au dépôt actuel. Vérifier que les déploiements continuent une fois le dépôt en privé.
- Conditions de GitHub : les automatisations d'un dépôt public doivent servir le projet de ce dépôt. Un dépôt public qui
  ne sert qu'à faire tourner un service privé et payant peut être vu comme un détournement des minutes gratuites, avec un
  risque de blocage. À vérifier avant de migrer et à expliquer simplement au propriétaire, avec les autres solutions (payer
  les minutes, serveur). C'est aussi pour ça que le kit serveur existe.
- Ce qui a déjà été public a pu être copié : la migration protège la suite, pas le passé.
- Tester chaque automatisation dans la nouvelle organisation avant d'arrêter l'ancienne. Jamais deux automatisations qui
  publient la même chose en même temps.

**6. Choix retenu pour le dépôt public** (complément du propriétaire, 19/10/2026 ; ne rien lancer avant le point 5 du
« Reste à faire »).

*Principe.* Le dépôt public doit être un vrai projet, mais réduit au strict minimum : il contient la page du site et les
automatisations qui la construisent et la publient. Rien de ce qu'il contient ne doit permettre de copier le dépôt privé,
de deviner nos sources ou de remonter jusqu'au propriétaire. Pourquoi : les règles de GitHub réservent les minutes
gratuites aux automatisations qui servent le projet du dépôt où elles tournent ; un dépôt public presque vide qui ferait
tourner un projet privé et payant serait risqué. Ce choix réduit le risque sans le supprimer : le kit serveur reste la
solution de secours.

*Dans le dépôt public (et rien d'autre).*
- La page compilée du site (`index.html` et `public/` : icônes, polices, `robots.txt`, `version.json`). Elle est déjà
  visible par tout visiteur, compactée et sans commentaires : aucune exposition en plus.
- Le relais du site (`api/`, `vercel.json`), mais seulement s'il est neutralisé :
  - aujourd'hui il contient des adresses de sources (réécriture des liens de documents, redirections `/doc/…`) ;
  - dans le public, aucune adresse ni aucun nom de source : les adresses d'origine doivent venir de variables Vercel
    secrètes (c'est le propriétaire qui les met), jamais d'un fichier ;
  - si c'est impossible à neutraliser proprement, le relais reste dans le privé et on explique l'autre montage au
    propriétaire.
- Les fichiers d'automatisation (`.github/workflows`), aux noms d'étapes neutres. Chaque passage :
  - récupère le code privé avec une clé en lecture seule, rangée dans les secrets GitHub ;
  - fait le travail ;
  - publie les données dans le dépôt privé ;
  - construit et publie la page du site dans le dépôt public.
- Un README et une LICENSE neutres.

*Jamais dans le dépôt public.*
- le code non compacté (`web/`) ;
- les scripts (lecture des documents, calculs, QLAB, contrôles) et les modèles ;
- les noms et adresses de sources, les données, `seed/` ;
- `docs/`, `SAUVEGARDES.md`, `PASSATION.md`, `outils/` ;
- l'historique actuel (le dépôt public part de zéro) ;
- tout nom de compte, pseudonyme, e-mail, nom du dépôt privé ou du dépôt de secours.

*Journaux et sécurité* (dépôt public = journaux visibles par tous).
- Rien d'affiché dans les journaux : ni adresse, ni donnée, ni secret, ni nom de source.
- Aucun fichier de passage public (artifacts, caches).
- Aucune automatisation lancée par une demande de modification (pull request) d'un inconnu.
- Clés au minimum de droits (lecture seule pour récupérer le code ; écriture seulement là où il faut publier). Le
  propriétaire les crée et les range lui-même : ne jamais lui demander de les coller dans la conversation.

*Site.*
- Une fois privées, les données ne se lisent plus en clair sur GitHub : le relais les lira avec une clé en lecture seule
  dans les réglages Vercel, et la copie de secours reste branchée comme aujourd'hui.
- Préparer la bascule pour que le site ne s'arrête jamais.
- Vérifier que Vercel continue de déployer.

*Avant de commencer.*
1. Faire d'abord un audit.
2. Proposer au propriétaire un plan simple, étape par étape, en disant ce qu'il doit faire lui-même : créer le dépôt, les
   clés, les variables Vercel.
3. Tester chaque automatisation dans la nouvelle organisation avant d'arrêter l'ancienne. Jamais deux automatisations qui
   publient la même chose en même temps.
4. À la fin, vérifier le dépôt public comme le ferait un inconnu : fichiers, journaux, historique. Il ne doit rien révéler.

**7. Exigences complémentaires** (propriétaire, 19/10/2026 ; à intégrer au plan de migration, à son tour, sans rien casser ;
point de restauration avant chaque étape, tout le site testé après, accord du propriétaire avant chaque étape importante).

1. *Dépôt public le plus vague possible, sans jamais casser le site.*
   - Nom de dépôt neutre, sans description ni sujets ; README d'une ligne, neutre.
   - Noms de fichiers, d'automatisations et d'étapes génériques (« préparation », « mise à jour », « publication »), aucun
     commentaire.
   - Rien qui permette à une personne ou à une IA de deviner nos sources, nos calculs, la structure de nos données ou
     l'existence du dépôt privé.
   - Le champ « site web » des réglages du dépôt reste géré comme indiqué dans le guide.
   - Test final : demander à une IA d'analyser le dépôt public et le site comme le ferait un copieur, et vérifier qu'elle
     ne peut retrouver ni sources, ni calculs, ni données.
2. *Données : objectif, une copie du site doit s'afficher vide.*
   - En attendant le backend : le relais refuse tout autre site que le nôtre et limite le nombre de requêtes.
   - Avec le backend : le relais ne sert que les abonnés connectés, vérifiés côté serveur, avec des limites par compte et la
     détection d'aspiration.
3. *Calculs* : faire la liste des calculs qui tournent encore dans la page (navigateur) et proposer de déplacer côté serveur
   ceux qui ont de la valeur, un par un, en vérifiant que les résultats affichés restent identiques avant et après.

## Tâches programmées

- « QLAB Prévisions : recalage sur tout l'historique » : **désactivée le 19/10/2026 à 17 h 24** (QLAB Prévisions retiré à la
  demande du propriétaire). Ne pas la réactiver.
- « Terminal FQT : contrôle de mardi 9 h » : une seule fois, le 20/10 à 9 h ; lecture seule, compte rendu au propriétaire.

## Comptes utilisateurs (backend)

À faire quand le propriétaire le décidera. Le propriétaire a relié le dépôt GitHub à Supabase (19/10/2026). Exigence : les données de chaque utilisateur le suivent d'un appareil à l'autre (quitter le Mac, se
connecter sur l'iPhone et tout retrouver) — historique de recherche MOTS CLES (90 jours), portefeuille PORT, alertes, listes,
réglages. Aujourd'hui tout est gardé dans le navigateur ; l'historique de recherche passe déjà par trois fonctions
(`kwHistLoad`, `kwHistSave`, `kwHistAdd` dans `web/pages17.js`) à brancher sur le compte, avec la copie du navigateur en secours
hors connexion. Aucune clé dans le dépôt ni dans la conversation : le propriétaire les met lui-même dans les réglages sécurisés
(variables d'environnement Vercel, secrets GitHub) ; aucune donnée d'utilisateur dans le dépôt.
