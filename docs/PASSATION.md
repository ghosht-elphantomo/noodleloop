# Passation — où en est le travail, ce qui reste

À lire en premier par toute nouvelle session. Mis à jour : 19/10/2026, 17 h 20 (Paris).
Une session qui termine une étape importante met ce fichier à jour (état, reste à faire, pièges).

## Démarrer une session

1. Ajouter ce dépôt (nom donné par le propriétaire au démarrage, accès en écriture), le cloner, puis récupérer les branches de données avec
   `git fetch origin +refs/heads/X:refs/remotes/origin/X` (comptes, dividendes, boc, data, raw, histo, site, probe, export, refs, sonde) : elles sont
   réécrites à chaque passage, un simple `git fetch origin X` ne les met pas à jour.
2. Lire : ce fichier, les règles en tête de `SAUVEGARDES.md`, `docs/GUIDE.md` ; `docs/QLAB3_PREVISIONS.md` et
   `docs/QLAB2_VALORISATION.md` avant de toucher à QLAB.
3. Répondre au propriétaire en français uniquement (jamais d'anglais, même une ligne), de façon concise ; pour une tâche : aller
   jusqu'au bout sans messages d'étape, puis un seul bilan à la fin (répondre normalement à ses questions).
4. Installer les outils de test : `npm install -g terser@5.36.0`, `pip install playwright` (Chromium), puis faire un premier
   parcours de référence du site avant toute modification (`outils/essais/test_site.sh`, voir `docs/GUIDE.md`, « En local »).

## Règles (obligatoires)

- Point de restauration dans `SAUVEGARDES.md` AVANT toute modification (main, site, et branche comptes si la lecture est touchée).
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

0. Vérifier le passage des comptes lancé le 19/10 à 16 h 53 (34 documents de l'archive lus ? exercices ajoutés ? aucun montant
   existant changé ? aucun e-mail d'échec ?) et le passage automatique de la nuit (4 h 17 UTC). La publication du 19/10 est déjà
   vérifiée en production. Une tâche programmée unique fait aussi ce contrôle mardi 20/10 à 9 h (lecture seule).
1. **Contrôles automatiques** : un seul script de vérification (données + parcours du site) lancé avant et après chaque
   modification et chaque nuit par une automatisation qui écrit un rapport vert / orange / rouge sans faire échouer le passage
   (pas d'e-mails d'erreur) : fichiers présents, non vides, frais, nombre de lignes comparé au passage précédent, doublons, valeurs
   aberrantes, cohérence entre fichiers ; site : toutes les fonctions et onglets, QLAB 48 × 6, aucune erreur JavaScript, aucun
   NaN / undefined / null, aucun nom de source, aucun émoji ; instantané des chiffres clés avant / après ; confidentialité ;
   auto-protection (un fichier vide ou anormalement court n'est pas publié, la dernière bonne version est gardée). Partir de
   `outils/essais/`.
2. **Nouvelles fonctions** :
   - BRVM, nouveaux onglets : Saison des résultats ; Publications attendues et retards ; Exposition pays.
   - DIVC, nouveaux onglets : Aristocrates du dividende ; Dividende net et calendrier d'encaissement (retenue à la source de
     chaque pays, taux à vérifier).
   - Nouvelle fonction BANK : tableau de bord des banques (PNB, coefficient d'exploitation, coût du risque, rentabilité, solidité
     du bilan sur 10 ans, toutes les banques côte à côte).
   - PORT : import de relevés (Excel, CSV, PDF, photos) lus dans le navigateur, jamais envoyés ni gardés, écran de contrôle
     avant validation, export et import d'une sauvegarde du portefeuille.
   - Plus aucun émoji sur iPhone (boutons Précédent / Suivant et symboles de l'interface).
   - Descriptions des 48 sociétés (fonction DES) réécrites avec nos propres mots : mêmes faits que la fiche actuelle, jamais mot
     pour mot, chaque fait vérifié sur un document officiel, un fait invérifiable est retiré.
   - Secours BRVM, suite : combler ce que l'essai « sans la base tierce » a montré manquant — séries BPA, dividende et PER,
     fiches des sociétés, cours d'avant décembre 2013.
3. **Fluidité et vitesse** (réglage désactivé par défaut ; ne touche que l'affichage).
4. Audit complet.
5. Seulement quand tout est propre, testé et audité : migration « deux dépôts » (privé + public neutre) avec le propriétaire,
   nettoyage de l'historique (ancien pseudonyme, pages brutes des sources) ; puis kit serveur.

## Tâches programmées

- « QLAB Prévisions : recalage sur tout l'historique » (claude.ai, 7 h 55 et 19 h 55) : démarre le recalage de QLAB 3 dans sa
  propre session dès que tous les documents sont lus (champ « left » à 0 sur les branches comptes, dividendes et boc : c'est le
  cas le 19/10 à 17 h 20, donc premier essai attendu le 19/10 à 19 h 55) et pousse sur main ; elle se désactive une fois
  `docs/QLAB3_RECALAGE.md` marqué « Statut : fait ». Le passage de 7 h 55 le 19/10 a échoué (limite d'utilisation atteinte).
  Elle peut travailler en même temps qu'une session de travail : toujours `git pull --rebase` avant de pousser et ne pas
  modifier les mêmes fichiers QLAB en parallèle.
- « Terminal FQT : contrôle de mardi 9 h » : une seule fois, le 20/10 à 9 h ; lecture seule, compte rendu au propriétaire.

## Comptes utilisateurs (backend)

À faire quand le propriétaire le décidera. Le propriétaire a relié le dépôt GitHub à Supabase (19/10/2026). Exigence : les données de chaque utilisateur le suivent d'un appareil à l'autre (quitter le Mac, se
connecter sur l'iPhone et tout retrouver) — historique de recherche MOTS CLES (90 jours), portefeuille PORT, alertes, listes,
réglages. Aujourd'hui tout est gardé dans le navigateur ; l'historique de recherche passe déjà par trois fonctions
(`kwHistLoad`, `kwHistSave`, `kwHistAdd` dans `web/pages17.js`) à brancher sur le compte, avec la copie du navigateur en secours
hors connexion. Aucune clé dans le dépôt ni dans la conversation : le propriétaire les met lui-même dans les réglages sécurisés
(variables d'environnement Vercel, secrets GitHub) ; aucune donnée d'utilisateur dans le dépôt.
