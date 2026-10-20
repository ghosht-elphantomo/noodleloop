# Passation — où en est le travail, ce qui reste

À lire en premier par toute nouvelle session. Mis à jour : 20/10/2026, matin (Paris).
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
- Modifications demandées (règle du propriétaire précisée le 20/10/2026) : quand il en demande plusieurs, ou un cahier des
  charges, les faire toutes d'abord ; après chaque modification, vérifier seulement que ce qui a été demandé fonctionne ; le
  parcours complet du site (418 pages, iPhone, QLAB) se fait une seule fois, à la fin de la liste, avant la publication ;
  signaler tout problème trouvé, même sans lien avec la modification. Le plus important : un point de retour avant chaque
  lot (`SAUVEGARDES.md`), pour revenir en arrière si le résultat ne plaît pas. « Tant que ça ne casse rien, on peut le faire. »
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
  cours de côté dans un commit local non poussé ; la pile `git stash` est partagée avec les copies de travail des agents :
  jamais de `git stash` sans nom).
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
- Les branches de données se récupèrent avec un refspec explicite (`git fetch origin +refs/heads/data:refs/remotes/origin/data`) ;
  sans lui, `origin/data` reste sur une ancienne version (piège constaté le 20/10 : branche `histo` crue en retard).

## État au 20/10/2026 (audit complet de la nuit)

Audit demandé le 19/10 au soir (« ligne par ligne, colonne par colonne, toutes les automatisations, doublons, faux chiffres,
systèmes de correction et de détection, comprendre pourquoi ça revient »), après la fin des travaux en cours (`c28827ca`).
Rapports détaillés de l'audit (cours, dividendes, fondamentaux, affichage, automatisations, données hors BRVM) : gardés dans
l'espace de travail de la session ; chaque constat corrigé a son entrée dans `outils/controle/BUGS_CORRIGES.md` (B24 à B45).

- **Publié** (chaque lot après une construction complète comparée à la précédente et le parcours complet du site : 418 pages
  et onglets, iPhone 100 pages, QLAB 48 × 3, aucune erreur JavaScript) :
  - `ceef8d49` : cours US par paquets de 20 (33 titres restaient sur la veille sans erreur) ; référence du contrôle du matin
    gardée par la sonde ; alerte « base extérieure figée » visible (B24, B25).
  - `7a56f2f1` : calculs d'affichage (périodes 1M/3M/6M calendaires et séance de référence, 12 mois calendaires DES/TECH, PER
    US de GF, drawdown 5 ans, rendements absents, secteurs pondérés, prime RV, Parkinson, unités FA, PORTF, Sharpe hors dollar,
    notations expirées, obligations) ; clôture du jour réservée à la base programmée du soir (`FQT_CLOSE`) ; archive
    `seed/brvm_daily.csv` réparée depuis les bulletins (221 clôtures de séance du 12 au 19/10) (B26 à B29).
  - `bb7166a0`, `0ece6a33`, `40b20be5` : volatilité 1 an seulement sur une année entière ; référence SPY des indices US ; copie
    complète du site ; données hors BRVM (liquidité nette de la Fed en milliards, séances de week-end retirées, dividendes US à
    leur date, bougie du jour cohérente, volume vraisemblable, variation US contre une clôture confirmée, contrats à terme après
    le règlement, rendement US, CPI et taux 10 ans prolongés) (B30 à B32).
- **Lot suivant** (`bdfd8449`, `8df5189b` et les corrections des dividendes, publiés après leur parcours complet) :
  protections des automatisations (lecture des branches en 3 essais, arrêt si une branche existe mais reste illisible,
  republication refusée si une branche perd plus de 10 % de ses fichiers, file `terminal-eod` pour la base du soir, délais
  propres, annotations des sources en échec et des étapes lentes, rapports anciens retirés) ; variation des taux ; actualités
  BRVM gardées 45 jours ; scission Honeywell (`seed/scissions_us.json`) ; semaines datées de leur dernière observation ;
  doublons (Fear & Greed, intervenants, capitalisations mondiales) ; séance manquante d'une série US ; dividendes : opérations
  sur le capital prouvées par les bulletins (Sonatel ×10 au 23/11/2012, Onatel ×10 au 29/11/2013, BOA CI 9 pour 41, BOA Niger
  1 pour 19, CBI BF 3 pour 125), dates de détachement fausses retirées, CIEC 2016 payé le 20/09/2017, avis sans texte relus
  par reconnaissance de caractères, 43 doublons d'événements, archive `histo` (B33 à B45).
- **Pourquoi ça revenait** (causes racines) : un passage complet lancé en journée faisait la clôture du jour ; une source qui
  renvoie moins que demandé (20 symboles) sans erreur ; des étapes coupées par un délai sans signal (passage vert) ; des
  branches réécrites de force sans vérifier ce qu'on publie ; des contrôles qui vérifiaient l'archive contre elle-même et
  jamais la série publiée contre le bulletin ; des unités et des dates de sources différentes mélangées sans table de
  référence. Chaque cause a maintenant sa protection dans le code et son contrôle du matin.
- **Décisions du propriétaire (20/10/2026, matin)** : ORGT, nombre de titres de la page brvm.org gardé ; flottant de l'avis
  officiel n°303 (transcrit dans `seed/flottant_avis.json`) affiché quand la page brvm.org ne concorde pas (24 titres, dont
  BOA Bénin 45,89 % au lieu de 22,61 %, Solibra 18,6 % au lieu de 1,86 %, Sicable 48,70 % concordant) ; BNPA des comptes
  vérifiés au résumé quand le bulletin calcule le même exercice sur un autre résultat (`BNPA_SERIE_AU_RESUME = True` : CABC,
  SDCC, TTLS, ONTBF ; BNPA du bulletin gardé dans « bnpa_bul ») ; réglages de fluidité désactivés par défaut, au choix de
  l'utilisateur ; retenues Burkina et Bénin : « taux constaté sur les documents officiels » demandé, mais les avis ne donnent
  que le net (brut introuvable) : question posée au propriétaire.
- **Demandes du propriétaire du 20/10 (matin), faites** : graphiques, échelle des prix étirée ou resserrée en la tirant (souris
  et doigt, double-clic = automatique, `chart.js`) ; GP ne s'étire plus tout seul sur iPhone (B51) ; tableaux, ligne suivie
  (survol ou toucher), colonne suivie et première colonne figée dans les matrices (CORR) ; info-bulle et menus à la bonne place
  quand l'interface est agrandie (B52) ; UEMOA, donnée de plus de dix ans affichée « — » (dette de la Côte d'Ivoire de 1995,
  B50) ; retenues du Burkina (12,5 %) et du Bénin (5 %) au taux du code des impôts, marquées « à vérifier » (les avis ne
  donnent que le net). EVTS vérifié à jour (dernier avis de la BRVM le 15/10, dernière publication de société le 16/10).
- **FA, deux référentiels (20/10, demande du propriétaire)** : les ratios se calculent aussi sur le second jeu de comptes
  (bouton « Comptes », `R2` dans `fa/*.json` ; PER et distribution seulement sur le principal, le BNPA officiel n'existant que
  pour lui) ; le référentiel principal est SYSCOHADA dès qu'il couvre un des deux derniers exercices (`comptes.py`), IFRS
  seulement pour les sociétés qui ne publient qu'en IFRS (Sonatel et Oragroup : derniers comptes SYSCOHADA en 2015 et 2018 ;
  Ecobank, Orange CI). BIIC (premier exercice IFRS 2025) reste en SYSCOHADA à l'ouverture, IFRS 2024-2025 au second jeu
  (décision du propriétaire). Années anciennes : 73 exercices à trous dans les comptes détaillés, voir « Données manquantes ».
- **Agents** : le propriétaire décide seul de leur emploi (consommation) ; par défaut, travail sans agent.
- **Reste de l'audit** :
  - Dates d'effet des opérations : **fait le 20/10** — CFAO ×100 corrigée au 13/12/2017 (bulletin : dernière séance à
    l'ancienne base le 12/12, cours précédent 375 imprimé le 13/12, première séance nouvelle base le 19/12 ;
    `seed/operations_historiques.json`, champ « date_listee ») ; Alios ×25 (24/12/2018) et SIEM ×40 (20/12/2018) justes
    (titres suspendus entre les deux bases ; le contrôle accepte une date listée pendant la suspension).
  - **Comptes non vérifiés : fait le 20/10 (après-midi)**, en trois points.
    1. *Lecteur corrigé* (`scripts/comptes.py`, quatre défauts trouvés en relisant les documents) : un « 0 » de la colonne des
       notes pris pour un montant (« TOTAL GENERAL 0 14 611 080 094 14 023 255 232 » : l'exercice N perdait ses totaux, Erium
       et Tractafric 2025) ; les rapports des commissaires aux comptes classés IFRS parce qu'ils citent les « normes internationales
       d'audit » (Coris BF 2021-2022, BOA Bénin 2020, SMB, Nestlé, Sicable, Palm…) — désormais seul un titre d'état (ligne
       courte ou en capitales, sans mot de phrase) fait basculer en IFRS ; « le total bilan s'est consolidé » pris pour un
       périmètre consolidé (SIB 2023). Relecture complète de la base (6 065 documents, 21 min) avant /
       après : 13 documents changent, tous en mieux pour les comptes consolidés par titre (aucun résultat, total, chiffre
       d'affaires ni capitaux propres perdu dans les séries principales) ; trois documents lisent moins de postes qu'avant
       (BOA BF 2018, NEI-CEDA 2004, Onatel 2013 : tableaux récapitulatifs du rapport des commissaires fusionnés avec les états),
       sans effet sur les séries. La correction du lecteur prend effet au prochain passage `comptes.yml` (04 h 17 UTC), donc dans
       la base du soir suivante ; le contrôle B53 vérifie que les 25 exercices relus sont bien dans les séries.
    2. *Exercices relus à la main* sur le texte des documents (`seed/corrections_bnpa.json`, lignes « cpt » avec « ajout » :
       exercice créé dans les comptes du titre, marqué « m » dans l'en-tête des comptes de FA) : BOA CI 2022 (confirmation) et
       2025, BOA Niger 2020-2025, BOA Sénégal 2025, Coris BF 2023-2025, Tractafric 2025, CFAO 2025, Loterie du Bénin 2023,
       Servair 2023 (SYSCOHADA : comptes provisoires + colonne 2023 des comptes 2024), Sonatel 2019-2020 (IFRS consolidé,
       présentation des résultats recoupée avec la page lisible des états IFRS et le rapport de gestion), Onatel 2020 (résultat exact
       de la convocation à l'AGO, communiqués), Sucrivoire 2019-2020, SICOR 2022-2023 (rapports annuels) et 2024 (chiffre
       d'affaires seul). Règle suivie : seuls des montants imprimés, confirmés par une identité comptable ou un second document ;
       BIIC 2025 (décision du propriétaire) : la société n'a publié sur brvm.org que des comptes IFRS 2025 (résultat 36 237 M,
       BNPA du bulletin 627,33) ; la série reste en plan comptable bancaire comme les exercices précédents et garde le résultat
       24 182 de la base tierce (instantané ; états PCB remis aux actionnaires, −20 % sur 2024), les deux BNPA sont expliqués
       dans FA et au contrôle B47. À l'avenir, seules les publications de brvm.org alimentent les comptes.
    3. *Reste sans document sur brvm.org* (rien à faire tant que la société ne publie pas) : Bridge Bank (tous), BIIC 2019-2022,
       Air Liquide 2021-2023 (rapports semestriels seulement), Alios 2022, Orange CI 2019-2020 (cotée fin 2022), SIEM 2024-2025,
       Uniwax 2024-2025, SICOR 2025 (le document « exercice 2025 » est le rapport 2024 ; résultat 2024 dans des pages non lues
       du scan), Loterie du Bénin 2019-2022 (cotée fin 2024). Les chiffres clés de ces exercices restent ceux de la base tierce
       (non vérifiés sur document).
  - Relais du métronome en plusieurs essais (R3) : seulement avec un essai en parallèle (règle du propriétaire).
  - Une base complète lancée en journée remplace pendant au plus 15 min des calculs plus récents (V13) : le relevé suivant
    les refait ; séparation complète à faire avec la migration.
  - CAPE figé (source arrêtée, affiché avec sa date) ; PER de Honeywell calculé sur des bénéfices d'avant la scission.
  - UBER : séance du 16/10/2026 absente de la source des séries US (signalée chaque matin par B41 ; variation du jour juste).

## État au 19/10/2026, 22 h 38

- **Publié depuis 19 h 15** (chaque fois après le parcours complet du site : 418 pages et onglets, iPhone 100 pages, QLAB 48 × 3,
  aucune erreur) :
  - `83df9265` : PORTF lit aussi les photos, captures d'écran et PDF scannés (Tesseract.js 7.0.0 et pdf.js 6.3.289 « legacy »,
    gratuits, hébergés sur le site dans `public/lib/ocr/`, rien n'est envoyé ailleurs).
  - `07929702` : contrôles « bugs corrigés : ne doivent jamais revenir » (`outils/controle/non_retour.py`, liste dans
    `outils/controle/BUGS_CORRIGES.md`) ; règle : chaque bug corrigé reçoit son contrôle.
  - `64e9ffb5`, `f7bed61a`, `b84ce361`, `665fd079` : textes du propriétaire sur la migration deux dépôts (section ci-dessous).
  - `eebe3c4f` : événements d'un document déposé sous une autre société rattachés à la bonne (contrôle B16).
  - `49ef8052` : taux de distribution sur le BNPA du même exercice (contrôle B18 ; voir « Reste à faire »).
  - `7ef202c7` : DIVC, brut et retenue de l'avis ; FA, dividende de chaque exercice = versements ordinaires additionnés
    (contrôle B19). Essai complet avant publication : construction locale entière avec l'ancien et le nouveau code sur les
    mêmes données, seuls les champs voulus changent (`pay` sur 48 titres, `brut` et `irvm` sur 43 versements, FA de Filtisac
    et Servair).
  - `6ee60cdc` : corrections de sécurité de l'audit (adresses `/doc/` en PDF seulement, liens « javascript: » refusés,
    démarrage protégé ; contrôles B20 à B22) ; vérifié dans un vrai navigateur (lien piégé bloqué, exports et sauvegarde
    toujours téléchargés) et avec les outils de Vercel (configuration valide, PDF relayés, pages HTML refusées).
  - `81e56253` : suite de l'audit (protection par élément, écritures sûres, relais des documents anciens, restauration PORTF).
  - `c849ac10` : contrôles de cohérence demandés par le propriétaire (fiche / BRVM, bulletin officiel, BNPA, dividendes,
    éléments écartés, valeurs extrêmes) ; secteur affiché = celui de la BRVM ; premiers écarts dans « Reste à faire »,
    Secours BRVM. `93ba3d76` : lecture des secteurs corrigée (le premier passage avait été refusé à raison par la garde).
  - `5dd02c0d` : fluidité et vitesse (réglages « Ouverture rapide » et « Animations douces », désactivés par défaut).
- **Vérifié en production (19/10, soir)** : contrôle du matin lancé à la main à 20:11 UTC avec les nouveaux contrôles :
  séance du 19/10, 48 cours et 48 BNPA identiques au bulletin officiel, 48 capitalisations concordantes, 43 dividendes
  brut / net cohérents, aucun élément écarté ; orange pour les écarts listés dans « Reste à faire » (titres, flottant, BNPA,
  valeurs extrêmes) et B10. Secteurs officiels lus à 20:24 UTC : 48 titres, tous identiques à la fiche.
- **Vérifié** : DES en ligne (48 sur 48) ; `qlabp/` absent des données ; événement SGB CI 2011 rattaché à SGBC en production ;
  déploiements de production réussis. Contrôle du 19/10 (17:50 UTC) : orange seulement à cause de B10 (lecture des comptes en
  échec le 19/10 à 04:43 UTC, déjà corrigée) ; repasse au vert quand ce passage sort de la fenêtre de 24 h.
- **Fluidité et vitesse** (point 3, fait le soir même), précisé par le propriétaire le 19/10 : **les deux** — ouverture plus rapide (écrans et
  données déjà ouverts gardés en mémoire, préchargement) et animations douces (transitions entre écrans, graphiques qui se
  dessinent, chiffres qui défilent), chacune avec son réglage, désactivées par défaut, sans rien changer aux chiffres.

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
   - Fait le 19/10 : PORT, import de relevés et sauvegarde (photos et PDF scannés lus depuis `83df9265`) ; DES, présentations des 48
     sociétés réécrites et vérifiées (en ligne, 48 sur 48, vérifié le 19/10).
   - DIVC, dividende brut et retenue : **fait le 19/10 pour ce que disent les avis** (brut et taux IRVM des personnes physiques
     passés dans `dividends.json` quand l'avis ou le calendrier les écrit et qu'ils redonnent le net ; colonnes « Brut / titre »
     et « Retenue » de l'onglet « Dividende net et encaissements », « — » sinon). Aujourd'hui seules les sociétés ivoiriennes
     (exercices 2024-2025, 43 versements) les ont : les avis des autres pays ne donnent que le net. Reste : taux de chaque pays,
     à vérifier sur un texte officiel (code des impôts de chaque État, taux en vigueur à chaque date) avant tout calcul du brut.
     **Fait le 20/10 (nuit)** : tableau « Retenue à la source sur les dividendes, par pays » dans le même onglet
     (`seed/retenues_dividendes.json` → `data/retenues.json`), taux légaux lus sur les textes officiels : Côte d'Ivoire 12 %
     personnes physiques / 10 % personnes morales (exceptionnel 17 % / 15 %, avis de paiement de la BRVM), Sénégal 10 % (CGI à
     jour de janvier 2025, art. 173-2), Mali 7 % (CGI, art. 42, sociétés cotées), Niger 7 % (CGI, art. 74, sociétés cotées),
     Togo 3 % personnes physiques / 7 % personnes morales (CGI à jour 2025, art. 79, sociétés cotées). Recoupé avec les nets
     publiés (BOA Niger 209,25 = 225 × 0,93 ; BOA Mali 305,04 = 328 × 0,93 ; Sonatel 1 575 = 1 750 × 0,9). Le brut n'est
     toujours affiché que si l'avis le donne (rien de calculé). **Pas encore affichés** : Burkina (CGI édition officielle 2023,
     art. 140 : 12,5 % sans taux réduit pour les sociétés cotées, mais Coris Bank paie 900 nets en 2026, soit 1 000 bruts à
     10 % ? une loi de finances plus récente a pu changer le taux : texte en vigueur à lire) ; Bénin (CGI, loi n° 2021-15,
     art. 86 : 5 % pour les sociétés cotées, mais BOA Bénin paie des nets à 10 % (468 = 520 × 0,9) quand BIIC est à 5 % :
     texte en vigueur à lire). Le texte de chaque recherche est dans `seed/retenues_dividendes.json` (« a_verifier »).
   - Secours BRVM, suite : combler ce que l'essai « sans la base tierce » a montré manquant — séries BPA, dividende et PER,
     fiches des sociétés, cours d'avant décembre 2013.
     Plan expliqué au propriétaire le 19/10 : (1) construire avec et sans la base (copie comprise) et lister chiffre par
     chiffre ce qui manque ; (2) BPA = résultat net des comptes lus ÷ nombre de titres des bulletins, comparé au BPA publié ;
     (3) dividendes des avis et calendriers, combler les années sans avis ; (4) PER = cours ÷ notre BPA, comparé au PER des
     bulletins ; (5) fiches ; (6) cours d'avant décembre 2013 : anciens bulletins des archives web, lus et contrôlés séance par
     séance ; (7) nos lectures deviennent la référence, la base ne fait plus que voter ; essai final sans elle : site identique.
     **Décision du propriétaire (19/10, précisée le soir)** : **la BRVM est la source principale** (bulletins officiels,
     pages et documents de brvm.org) ; la fiche (Sika) ne sert que pour ce qu'on n'a pas pu reconstituer depuis la BRVM (scan
     illisible, document manquant) ; tout écart entre les deux est signalé par le contrôle du matin avec les valeurs côte à
     côte, et vérifié sur le document. Raison : une mauvaise lecture ne passerait pas inaperçue devant les investisseurs.
     **Étape 1 faite le 19/10** (mesure, `outils/secours/mesure.py`, rapport `docs/SECOURS_MESURE.md`) — ce qui ne vient que
     de la base tierce : (a) **cours** : 23 831 séances d'avant le premier bulletin officiel lu (décembre 2013, de 2006 à 2013)
     et 274 séances sans aucun bulletin lu depuis (226 en 2014) ; (b) **fondamentaux** : exercices non couverts par nos
     comptes vérifiés : 30 résultats nets, 55 chiffres d'affaires, 77 capitaux propres, 30 totaux de bilan (surtout 2021-2025
     de BBGC, BOAC, BOAN, CBIBF, LNBB, SIVC… : documents publiés mais pas encore lus ou pas vérifiés ; 4 280 documents « non
     vérifié ») ; BNPA et PER suivent le résultat net ; (c) **dividendes** : tous les 328 versements de la base sont retrouvés
     dans nos avis, calendriers ou bulletins ; (d) **événements** : la liste d'avant 2016 (2 241) ne vient que de la base et de
     l'archive web ; (e) **fiche** : secteur, titres et flottant viennent de brvm.org ; nom, pays et « banque » encore de la base
     (stables, à recopier). Suite : relire les 274 bulletins manquants, lire et vérifier les comptes manquants, retrouver les
     bulletins 2006-2013 dans l'archive web.
     **Étape 2 faite le 20/10 (nuit)** : (a) **montants échangés lus en milliers** dans les bulletins (montants d'un milliard
     et plus) : ramenés en FCFA ; avant, le montant était écarté et le volume partiel de la base restait (SONATEL 15/10/2026 :
     3 380 titres au lieu de 37 543) ; 19 séances corrigées ; contrôles B23 et « Volumes / bulletin officiel » ; (b) **indices** :
     le relevé du soir relit chaque bulletin manquant depuis 2018 (12 par passage, du plus récent au plus ancien) et lit aussi les
     montants échangés (valeur transigée du marché pour le BRVM Composite, colonnes « Volume » et « Valeur » des indices) ; avant,
     un jour absent du relevé n'était jamais rattrapé (01 et 02/10/2026 sans valeur officielle) ; le montant du jour en séance
     n'est plus celui de la veille ; écart de plus de 5 % entre la base et le bulletin : signalé, base gardée ; (c) **fiche des
     sociétés** à nous (`seed/societes.json` : nom, nom officiel, banque ; la base en secours, écarts signalés) ; (d) **nouvelle
     cotation** au bulletin absente de la fiche : signalée chaque matin. Conclusion sur les cours anciens : l'archive web n'a
     presque aucun bulletin d'avant décembre 2014 (2004 : 210 seulement) ; les cours 2006-2013 et janvier-novembre 2014 ne
     peuvent pas être refaits depuis la BRVM : la copie de la base (branche `raw`, base historique, copie de secours) reste la
     protection. Fondamentaux non couverts (comptes scannés que la vérification refuse) : relus à la main le 20/10 (voir
     « Comptes non vérifiés : fait »).
     **Fait le 19/10** : contrôle automatique de ces écarts (`outils/controle/coherence.py`, données
     `miroir.json` et `secteurs.json`, secteurs officiels lus chaque soir sur brvm.org). Nombre de titres et flottant affichés :
     page « Capitalisations » de brvm.org (la fiche seulement si elle manque) ; secteur affiché : celui de la BRVM depuis le
     19/10 (la fiche si la BRVM ne classe pas le titre). **Premiers écarts trouvés (à trancher par le propriétaire, documents à l'appui)** :
     - SAFC : 11 869 750 titres sur brvm.org (affiché, sert à la capitalisation) contre 8 119 750 dans la fiche et dans l'avis
       du flottant ; ORGT : 69 986 131 dans l'avis contre 69 415 031 ailleurs ;
     - flottant : la « capitalisation flottante » de brvm.org (affichée) diffère de l'avis officiel du flottant (n° 303, signé
       le 12/10/2026, chiffres au 31/12/2025) pour 17 sociétés et de la fiche pour 14 (BOA Bénin : 22,61 % sur brvm.org,
       44,69 % dans la fiche, 45,89 % dans l'avis). Sur 48 : 23 où les trois concordent, 7 où l'avis et la fiche concordent
       contre la page (dont Sicable 1,86 % sur la page contre 18,6 %), 8 où la page et la fiche concordent contre l'avis
       (probablement mal lu dans le scan : SMB 51,76 %), 3 où la page et l'avis concordent, 7 sans accord. **Décision du
       propriétaire (19/10)** : la donnée BRVM la plus récemment datée l'emporte, la fiche (Sika) sert de miroir. La page
       « Capitalisations » est datée de chaque séance : elle reste affichée ; l'avis et la fiche servent de miroir et le
       contrôle du matin liste chaque écart. Cas à regarder en priorité : Sicable (facteur 10 ?) ;
     - valeurs extrêmes à revoir : PER de BNBC (549), BOAN (229), SDSC (199), UNLC (646) ; distribution de SDSC (638 %) et
       SIVC (796 %) ; rendement de Filtisac (64 %, réel).
   - **Documents déposés sous la page d'une autre société (vu le 19/10, corrigé le 19/10)** : la Bourse range parfois un
     document sous une autre société (rapport de BOA Sénégal chez Erium, comptes de Tractafric chez CFAO, résultats d'Onatel
     chez Sonatel…). Vérification faite : la recherche MOTS CLES (`build_search.fix_by_file`) et la lecture des comptes
     (`comptes.other_company`, montants rattachés à la bonne société) les traitaient déjà ; seul le registre interne
     (`index.json` de la branche `comptes`) garde la société de la page. Restait 1 événement mal rangé (SGB CI 2011 chez
     SMB) : `build_terminal.py` rattache désormais les événements avec `comptes.doc_company` (intitulé, puis nom du fichier).
     Contrôle B16 du matin. Pour tout outil qui lit le registre : passer par `comptes.doc_company`.
   - **Filtisac, vérifié le 19/10** : l'avis n° 230-2025 dit « dividende annuel de 1 320 FCFA » brut (IRVM 12 %, soit 1 161,6
     net) au titre de 2024 et, à part, « dividende exceptionnel de 680,67 FCFA » brut (IRVM 17 %, soit 564,96 net) : les données
     sont justes, rien à reclasser. Le rendement (dernier dividende annuel net ÷ cours) est vrai par définition ; d'après les comptes
     lus, le résultat net 2024 était de 18 595 M contre 466 M en 2025. **Bug trouvé et corrigé le 19/10** : la distribution (3 516 %) divisait le
     dividende de 2024 par le BNPA de 2025 ; elle se calcule désormais sur le BNPA du même exercice (88 %). Même erreur sur
     12 titres (BNBC 4 451 % au lieu de 55 %, BOAN 1 063 % au lieu de 87 %, UNLC 1 768 % au lieu de rien…) ; contrôle B18.
     **Second bug trouvé et corrigé le 19/10** : FA gardait un seul versement par exercice (Filtisac 2024 affichait
     l'exceptionnel, 564,96, au lieu du dividende annuel ; acompte et solde non additionnés pour Filtisac 2015-2016 et Servair
     2018) ; FA additionne désormais les versements ordinaires ; contrôle B19.
   - **BNPA vérifiés sur les documents et corrigés le 19/10** (`seed/corrections_bnpa.json`) : ORGT 2018 (179,95 au lieu de
     428,92 : référentiel SYSCOHADA mêlé au résultat IFRS), ABJC 2021 (61,40 ; BNPA publié 61), UNLC 2020 (-262,38 au lieu de
     -2 866), SCRC 2019 (signe), BOAM 2015-2018 (BNPA et dividendes de la fiche ÷ 1,5 : attribution gratuite d'août 2024 non
     reportée ; distribution 2017 : 105 % au lieu de 70 %). ETIT : juste (BNPA officiel part du groupe, résultat de la série
     total). **Nouvel écart** : ORGT a 69 986 131 titres dans ses états financiers 2024 et 2025 et dans l'avis du flottant, mais
     la page « Capitalisations » de brvm.org (affichée, source principale) donne encore 69 415 031 : capitalisation affichée
     0,8 % trop basse ; à trancher par le propriétaire. SAFC : écart expliqué (augmentation de capital de juillet 2026, page juste).
     Filtisac 2016 : deux versements, justes (avis n° 006-2018 : « dividendes complémentaires exercice 2016 », 09/01/2018).
     Filtisac 2015 : le second versement (1 500 FCFA avant le fractionnement par 4, soit 375 aujourd'hui, payé le 23/12/2016) est
     **confirmé par le bulletin officiel de la cote** (dernier dividende imprimé et sa date) ; aucun avis retrouvé, l'exercice
     2015 est déduit de la date (vérifié le 19/10). Servair 2018 : deux fractions, justes (avis n° 072 et 148-2019).
     Sauts de cours SAFCA 22/02/2012 (+40 %) et SOGB 01/06/2011 (+43 %) : **impossibles à vérifier** (aucun bulletin de ces
     années dans l'archive web, voir Secours) ; plausibles (titres peu échangés), laissés tels quels et notés ici.
3. **Fluidité et vitesse — fait le 19/10** : réglages « Ouverture rapide » (préchargement des écrans suivants) et « Animations
   douces » (fondu, graphiques qui se dessinent, chiffres qui défilent), désactivés par défaut (menu 98 « Réglages ») ; voir le
   guide. À voir avec le propriétaire : les activer par défaut ou non, une fois essayés.
4. **Audit complet — premier passage fait le 19/10** (code, automatisations et données, lecture seule, par un agent séparé
   qui n'avait pas fait le travail ; rapport détaillé avec fichier et ligne repris ci-dessous). Points sains : aucun secret,
   aucun e-mail ni lien GitHub dans la page, données presque toujours échappées, aucune automatisation lancée par une demande
   de modification. **Corrigé le 19/10** (sans risque, testé) : adresses `/doc/` limitées aux PDF (B20) ; liens
   « javascript: » refusés (B21) ; adresse « #% » ou « #constructor » qui bloquait le démarrage (B22) ; heure QQQ absente ;
   taux de distribution (B18) ; dividende par exercice de FA (B19). **Corrigé ensuite le 19/10** : `build_terminal.py`, une
   protection par élément (fractionnements, dividendes officiels, comptes publiés : un élément mal formé est écarté et signalé
   par un avertissement du passage, les autres continuent ; une société en erreur est remise comme avant) ; écritures sûres
   (fichier temporaire puis remplacement) dans `fetch_extra.py` et `scrape.py` ; `api/doc.js` (erreur passagère jamais gardée en
   cache, `k` contrôlé, réponse venue de l'archive seulement, lecture arrêtée au-delà de la limite, type fixé par le serveur) ;
   PORTF, restauration limitée à 15 Mo et quantités finies. **Fait le 20/10 (nuit)**, reste de la liste « sans risque » :
   - `api/data.js` : l'essai du secours seul (`via=2`) refuse tout paramètre en plus (il aurait contourné le cache et épuisé
     la clé de lecture de la copie) ; si le propriétaire crée la variable Vercel `SECOURS_KEY`, l'essai exige `&k=<clé>` ;
   - valeurs saisies au lancement manuel passées par `env` et contrôlées (nombres seulement) dans `comptes.yml`,
     `dividendes.yml`, `lien.yml` ; `terminal.yml` (choix fermé) et `metronome.yml` (déjà contrôlé) non touchés ;
   - `lien.yml` : l'outil de tunnel est téléchargé par son numéro de version et contrôlé par l'empreinte publiée par GitHub ;
   - `esc()` échappe l'apostrophe (fait le 19/10) ;
   - **vérifiés et laissés** : `window.claude` sert au mode « artefact » de `build.py --artifact` (sur le site, sans effet :
     relevé toutes les 5 minutes) ; l'étape « branche site » de `terminal.yml` garde le repère du site de chaque point de
     `SAUVEGARDES.md` ; pillow n'est installé qu'en secours si l'image de GitHub ne l'a pas.
   **Pour la migration (point 5), décision du propriétaire** : le relais sert tous les fichiers de `data/`, y compris des noms
   de fournisseurs (summary, fg, calendar, quotes, news, ei_oil, umoa_curves, bceao, live) → liste blanche et champs de source
   retirés à la construction ; l'écran FG nomme son fournisseur et le bandeau d'actualités affiche les codes des éditeurs
   (voulu jusqu'ici, à trancher) ; le contrôle des sources ignore les mots de moins de 4 lettres ; noms d'étapes et journaux
   qui citent des sources ; identité dans `LICENSE`, `api/data.js`, `copie.yml`, `fetch_extra.py`, `probe.yml` ; fichiers de
   passage téléchargeables (`comptes.yml`) ; cache lisible depuis une copie du dépôt ; `persist-credentials: false` et
   lecture séparée de la publication ; actions fixées par empreinte ; CSP complète (scripts, connexions : tester l'OCR).
   **Données (à vérifier sur les documents)** : voir ci-dessus (ORGT : nombre de titres) ; Filtisac 2015 confirmé, sauts de
   cours anciens non vérifiables (notés).
5. **Ordre décidé par le propriétaire (19/10)** : la migration se fait AVANT la construction de la base de données (backend) :
   le code et les clés de la base naissent directement dans le dépôt privé (rien à nettoyer dans l'historique public), et le
   relais des données n'est refait qu'une fois, sur l'architecture finale. Migration faite ENSEMBLE avec le propriétaire.
   Seulement quand tout est propre, testé et audité : migration « deux dépôts » (privé + public neutre) avec le propriétaire,
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
4. *Métronome et actualisations* (précision du propriétaire, 19/10/2026) : le Métronome ne doit jamais être arrêté tant que
   son remplaçant n'a pas lancé le Terminal à l'heure pendant plusieurs jours, vérifié en parallèle. Les actualisations toutes
   les 15 minutes ne doivent jamais s'interrompre.

**8. Organisation retenue et règles de la migration** (propriétaire, 20/10/2026, 15 h 15-15 h 30).
- *Deux dépôts.* `noodleloop` (public, l'actuel) devient le **moteur** : il garde les automatisations et le lien Vercel, et à
  la fin ne contient plus qu'elles et la page compilée du site. `bloopface` (privé, créé par le propriétaire le 20/10) devient
  le **coffre** : tous les autres fichiers (code, scripts, docs, `seed/`, branches de données), **sans aucune automatisation
  active** (les fichiers de `.github/` y sont rangés, inertes, sous `automatisations/origine/` ; aucune minute payante).
- *Clés* : jetons GitHub limités au seul dépôt `bloopface`, créés et rangés par le propriétaire (lecture seule pour récupérer le
  code ; écriture pour publier les données ; lecture seule dans Vercel pour le site). Journaux publics neutres : noms d'étapes
  génériques, tout ce qu'écrivent les scripts dans un fichier non publié.
- *Règle absolue* : **rien n'est effacé ni supprimé dans `noodleloop`** (fichiers, branches, historique, réglages) tant que
  le transfert vers `bloopface` n'est pas effectif, vérifié, testé, retesté et validé par le propriétaire.
- *Avant la bascule* : audit complet de toutes les automatisations (déclencheurs, secrets, branches lues et écrites, adresses,
  journaux, dépendances entre elles, métronome, Vercel).
- *Historique de `noodleloop`* : à effacer seulement après la validation (façon à choisir par le propriétaire : nouvelle
  branche `main` sans passé puis demande de purge au support GitHub, ou dépôt supprimé et recréé sous le même nom). Aucune
  copie du dépôt n'existe (0 copie au 20/10).

**9. Avancement (20/10/2026, 18 h 05).**
- *Étape 1, copie* : faite (toutes les branches de `noodleloop` copiées à l'identique dans `bloopface`, vérifiées deux fois ;
  anciennes automatisations rangées sous `automatisations/origine/`, inertes). Outil de recopie fidèle d'une branche :
  `recopier.sh` (session du 20/10 ; à refaire au besoin : commit unique, même arbre, vérification de l'empreinte sur GitHub).
- *Étape 2, moteur* : scripts privés dans `automatisations/moteur/` (un par ancienne automatisation, voir `LISEZMOI.md`),
  fichiers publics génériques dans `automatisations/moteur/publics/` ; version d'essai (`publics/essai/`, générée par
  `vers_essai.py`) copiée dans `.github/workflows/` de `noodleloop` **à côté** des anciennes (rien retiré). Secrets du moteur
  créés par le propriétaire : `K1`, `K2` (jetons GitHub limités au coffre, expirent le 20/10/2027), `D1`, `K4` (clé Vercel
  limitée au projet du site, 1 an). `K3` (secours) : à créer à la bascule.
- *Essais faits le 20/10* (tous verts, écritures seulement dans les branches `-essai` du coffre) : Archive, Lecture A (comptes :
  26 889 fichiers, registre identique à la production), Lecture B, Lecture C, Machines, Outil, Sortie, Accès (lien d'une
  minute, écrit seulement sur la branche `lien-essai`), Mise à jour complète (33 min, données identiques à la production
  hors relevés intermédiaires) et rapide (lancée en parallèle de la production à la même seconde : résultats identiques),
  Vérification (rapport sur `probe-essai`), Publication (voir ci-dessous). Cadence (nouvelle horloge) tourne en parallèle du
  Métronome depuis 14 h 30 UTC et déclenche « Ping » aux mêmes secondes (:00:16, :15:16, :30:17, :45:16) : rodage de quelques
  jours avant de lui confier la mise à jour.
- *Site* : `api/data.js` du coffre lit la branche de données du coffre avec la clé donnée à la version mise en ligne
  (variables `K1`, `D1`, `B1` ; plus aucun nom de dépôt dans le code) ; `vercel.json` du coffre sans mise en ligne par Git.
  **Publication** (`site.sh` + `site_api.py`) : envoi par l'API Vercel (la clé limitée au projet est refusée par l'outil en
  ligne de commande), version vérifiée (page, relais, données récentes, fichier absent, en-têtes, aucun nom de source dans
  live / summary / quotes / news) avant mise à l'adresse du site, retour à la version précédente si le contrôle à l'adresse
  publique échoue (`mybbgterminal.vercel.app` ; l'adresse `-screener3` est protégée par l'hébergeur). Essai : aperçu
  `…-screener3.vercel.app` lisant `data-essai`, vérifié vert deux fois (15 h 48 et 15 h 58 UTC). La mise à jour lance la
  Publication quand le code du site change (production seulement).
- *Corrigé en passant* : nom de source répété en fin d'extrait d'actualité (« … Sika Finance » dans une info-bulle, résumés
  Google Actualités) : producteur et relais corrigés dans les deux dépôts (18 h 00). Contrôle B29 adapté au moteur d'essai.
- *Reste avant la bascule* : rodage de Cadence ; essai de la base du soir en parallèle (Mise à jour d'essai, choix « soir », à
  lancer à 22 h 35 UTC un jour de semaine) ; Secours (`copie.sh`, clé `K3`) ; sonde et archives (Outil tâches 2 et 3) ;
  relecture « en étranger » du moteur public (rien d'identifiable) ; validation du propriétaire.
- *Bascule* (dans l'ordre, accord du propriétaire à chaque pas) : 1) fichiers de production `publics/*.yml` copiés dans le
  moteur, anciennes automatisations **désactivées sans être supprimées** (programmation retirée, fichiers gardés) ; 2)
  Publication tâche 2 (site mis en ligne depuis le coffre) puis tâche 3 (mise en ligne automatique depuis Git débranchée) ;
  3) Cadence remplace le Métronome ; 4) vérification complète comme un étranger ; 5) plus tard, avec l'accord explicite du
  propriétaire : nettoyage de `noodleloop` (façon 1 ou 2 du point 8).

**10. Avancement (21/10/2026, 00 h 10).** Le détail est dans le coffre (`docs/PASSATION.md`, point 10, et les documents qu'il
cite) ; ici seulement l'essentiel, sans rien de sensible.
- *Essai de la base du soir* : tâche programmée une seule fois (01 h 45 Paris, 20/10) lançant la Mise à jour d'essai en mode
  complet avec le choix « soir », en parallèle de la production ; résultat à lire le 21/10 au matin. Cadence toujours en rodage.
- *Branche `brouillon` du coffre* : améliorations préparées pendant le gel du code du site (corrections de chiffres vérifiées sur
  les documents, décisions du propriétaire), chacune vérifiée par une construction locale complète ; intégrées une par une après
  la bascule, avec le test complet après chacune. Rien de tout cela n'est en production.
- *Épuration des chiffres clés* : lot 1a lu en entier (méthode, état et corrections dans le coffre) ; lot 1b à suivre.
- *Audit complet du site* (20/10 au soir) : test complet vert (418 pages, iPhone, QLAB) ; constats et ordre proposé dans le coffre.
- *Reste avant la bascule* (inchangé) : rodage de Cadence, résultat de l'essai du soir, Secours (clé `K3` à créer par le
  propriétaire samedi), relecture « en étranger » du moteur public, validation du propriétaire.

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

Décision du propriétaire (20/10/2026) pour le backend et le système de paiement : **un seul type d'abonnement**, à
**3 999 FCFA par mois**, donnant accès au terminal complet (plus de distinction Particulier / Professionnel : la grille
du 19/10 et la page tarifs de la landing sont à reprendre dans ce sens au moment du backend).
