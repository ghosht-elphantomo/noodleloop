# Passation — où en est le travail, ce qui reste

À lire en premier par toute nouvelle session. Mis à jour : 18/10/2026, 16 h 30 (Paris).
Une session qui termine une étape importante met ce fichier à jour (état, reste à faire, pièges).

## Démarrer une session

1. Ajouter le dépôt `ghosht-elphantomo/noodleloop` (accès en écriture), le cloner, puis récupérer les branches de données avec
   `git fetch origin +refs/heads/X:refs/remotes/origin/X` (comptes, dividendes, boc, data, raw, histo, site) : elles sont réécrites
   à chaque passage, un simple `git fetch origin X` ne les met pas à jour.
2. Lire : ce fichier, les règles en tête de `SAUVEGARDES.md`, `docs/GUIDE.md` ; `docs/QLAB3_PREVISIONS.md` et
   `docs/QLAB2_VALORISATION.md` avant de toucher à QLAB.
3. Répondre au propriétaire en français uniquement, de façon concise ; pour une tâche : aller jusqu'au bout sans messages
   d'étape, puis un seul bilan à la fin (répondre normalement à ses questions).

## Règles (obligatoires)

- Point de restauration dans `SAUVEGARDES.md` AVANT toute modification (main, site, et branche comptes si la lecture est touchée).
- Après chaque modification : tester TOUT le site et toutes les données ; signaler tout problème trouvé, même sans lien avec la
  modification ; ne publier que si tout est bon. « Tant que ça ne casse rien, on peut le faire. »
- Commits auteur `fqt-bot <41898282+github-actions[bot]@users.noreply.github.com>` ; pushes groupés sur main ; aucune
  nouvelle branche ; ne pas toucher aux réglages GitHub ou Vercel qui marchent.
- Rien sur la personne du propriétaire (nom, pseudo, e-mail) dans le dépôt ; jamais l'ancien nom du dépôt ni l'adresse du site
  dans les fichiers ; README.md et LICENSE neutres. Sur le site : aucun nom de source, lien GitHub ou e-mail affiché.
- Aucune donnée d'utilisateur dans le dépôt ; ne jamais demander de coller une clé secrète dans la conversation.
- Ne pas pousser de travail inachevé ou non testé (le contrôle de fin de tour demande de tout valider : mettre le travail en
  cours de côté avec `git stash -u` plutôt que de le publier).

## Pièges techniques

- Depuis l'espace de travail de Claude, les journaux et fichiers des passages GitHub ne se téléchargent pas (stockage bloqué) :
  lire les annotations (`gh api repos/ghosht-elphantomo/noodleloop/check-runs/<job>/annotations`) et faire publier un résultat
  détaillé sur la branche de diagnostic `probe` (voir `archives.yml`). Le site non plus n'est pas joignable : vérifier par les
  branches `data` et `site` et par les déploiements (`gh api repos/ghosht-elphantomo/noodleloop/deployments`).
- main reçoit des commits automatiques (« mise à jour … ») : `git pull --rebase origin main` juste avant chaque push.
- Le code publié est compacté par terser (`npm install -g terser@5.36.0`, puis `python3 build.py`) ; `index.html`,
  `public/index.html` et `public/version.json` sont régénérés et publiés avec toute modification de `web/`.
- Essais locaux (outils à recréer dans l'espace de travail, rien de tout cela n'est dans le dépôt) : construction du soir de
  `build_terminal.py` avant / après sur les branches data, raw, boc, comptes, dividendes ; site local avec la réécriture du relais
  `api/data.js` appliquée aux données et `eia_wpsr.json` copié en `oil_w.json` ; parcours Playwright de toutes les fonctions et
  de tous les onglets avec plusieurs titres, comparaison des textes avant / après ; QLAB 48 actions × 6 vues ; parcours iPhone 13
  (débordement horizontal) ; recherche de noms de sources dans les textes, infobulles et liens.
- Relecture complète des comptes (`comptes.py`) : ~20 min de calcul ; la répartir sur deux processus en local.
- Automatisations qui lisent des PDF : Ubuntu 24.04 (Ubuntu 26.04 lit autrement une partie des scans).

## État au 18/10/2026 soir

- **Lecture des documents de la BRVM terminée** : 6 033 documents au registre (branche comptes), 1 599 avec au moins un exercice
  vérifié, 0 restant. Lecture répartie sur 6 machines quand il en reste au moins 60 (`comptes.yml`, `scripts/comptes_merge.py`).
  Le recalage de QLAB Prévisions (tâche programmée de 7 h 55 et 19 h 55) peut maintenant démarrer.
- **Corrections du 18/10** (testées sur tout le site, vérifiées en production) : 82 chiffres d'affaires (dont 79 calculés
  d'après les documents : somme des ventes SYSCOHADA ou produit net bancaire de l'ancien plan bancaire), 12 résultats nets
  (SICABLE 2005-2016), BOA Côte d'Ivoire 2011 (-487 millions au lieu de 0), secteur de SMB CI, 76 longs scans qui étaient relus à
  chaque passage, croissance de GF non affichée après un exercice en perte. Montants calculés : seulement pour des exercices vides,
  jamais à la place d'un montant existant (voir `docs/GUIDE.md`).
- **Données extérieures (base tierce, archives SikaFinance, fiches des sociétés)** : une donnée prise n'est jamais perdue
  (`scripts/sticky.py` ; copie permanente quotidienne dans `instantanes/` de la branche histo). Liste des publications : liste
  tierce, sinon son miroir, sinon pages de brvm.org seules (essai : 3 477 documents des 48 sociétés retrouvés sans la liste
  tierce). Décision du propriétaire : la BRVM reste la source principale ; SikaFinance est gardé pour ses usages actuels (chiffres
  clés que la BRVM ne donne pas) mais ne doit jamais devenir une dépendance.
- **Archives de la BRVM** (`archives.yml`, à la demande ; liste complète dans `archives.json` de la branche probe) : 9 873 PDF
  gardés par l'archive web, 1 860 variantes de nom de documents connus, 3 697 absents de la liste (surtout des avis
  d'obligations, des sociétés qui ne sont plus cotées, des rapports de la BRVM). Utiles pour combler des exercices vides :
  Unilever CI 2010-2013 (8 documents : chiffre d'affaires, résultat, bilan absents aujourd'hui), Coris Bank 2017 et 2020,
  Air Liquide CI (états financiers publiés le 26/04/2023), rapport annuel de Palm CI (08/07/2024), états financiers de SITAB
  (année à lire).
- La base tierce n'a pas été mise à jour depuis le 07/10/2026 (11 jours ; signalée « figée » au-delà de 21 jours dans
  `boc_check.json`).

## Reste à faire

Lundi 19/10 (tâches programmées dans la session de travail du 16-18/10) : audit complet à 8 h 30, contrôles à 12 h et 15 h 30,
rappel du plan à 14 h, « c'est l'heure » à 16 h. Les nouveautés commencent à 16 h 01, au signal du propriétaire, dans l'ordre
suivant — et seulement si les documents sont lus (fait) et que l'audit de 8 h 30 n'a rien trouvé de cassé :

1. **Contrôles automatiques** : un seul script de vérification (données + parcours du site) lancé avant et après chaque
   modification et chaque nuit par une automatisation qui écrit un rapport vert / orange / rouge sans faire échouer le passage
   (pas d'e-mails d'erreur) : fichiers présents, non vides, frais, nombre de lignes comparé au passage précédent, doublons, valeurs
   aberrantes, cohérence entre fichiers ; site : toutes les fonctions et onglets, QLAB 48 × 6, aucune erreur JavaScript, aucun
   NaN / undefined / null, aucun nom de source, aucun émoji ; instantané des chiffres clés avant / après ; confidentialité ;
   auto-protection (un fichier vide ou anormalement court n'est pas publié, la dernière bonne version est gardée).
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
     fiches des sociétés, cours d'avant décembre 2013 ; ajouter à la lecture les documents retrouvés dans l'archive (liste
     ci-dessus).
3. **Fluidité et vitesse** (réglage désactivé par défaut ; ne touche que l'affichage).
4. Audit complet.
5. Seulement quand tout est propre, testé et audité : migration « deux dépôts » (privé + public neutre) avec le propriétaire,
   nettoyage de l'historique (ancien pseudonyme, pages brutes des sources) ; puis kit serveur.

À vérifier aussi (trouvé le 18/10, sans urgence) :
- 45 montants complétés entre deux lectures d'un même scan sont lus autrement par une troisième lecture (un chiffre confondu) :
  à revoir un par un sur les documents (règle de prudence déjà appliquée aux nouveaux compléments, pas encore aux anciens).
- SUCRIVOIRE 2019 : exercice vérifié mais total du bilan absent des fondamentaux.
