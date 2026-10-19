# FQT — terminal de marché (BRVM, US, macro)

> Documentation complète du projet. Elle était dans README.md ; elle est ici pour que la page d'accueil du dépôt reste neutre.
> Règle : ne jamais remettre de description du projet, de nom de site, d'adresse ni de marque dans README.md, LICENSE
> ou la description du dépôt.
>
> Nouvelle session : lire d'abord [docs/PASSATION.md](PASSATION.md) (où en est le travail, ce qui reste, pièges), puis les
> règles en tête de SAUVEGARDES.md.

Terminal façon Bloomberg : ligne de commande, touches de fonction, tableaux denses, graphiques interactifs. Projet autonome (séparé du screener FOFCO BRVM).

Tapez un ticker ou une fonction puis Entrée : `SNTS GP`, `SNTS QLAB`, `QQQ BTST`, `MACRO`, `EVTS`. Cliquer sur n'importe quel titre ouvre ses écrans. La fonction **HELP** liste toutes les fonctions, leurs onglets et les raccourcis.

**Barre de commande** (`web/core.js` : `parseCmd`, `resolveSec`, `SEC_ALIAS`) : la fonction est cherchée d'abord (dernier mot ou groupe de mots), puis le reste est lu comme un titre — ticker, nom de la société ou nom usuel (`NSIA FA`, `Sogb CN`, `Orange CI FA`, `SGBCI GP`). Un nom qui désigne plusieurs sociétés (`TOTAL FA`) affiche la liste des candidats, chacune avec la fonction (Entrée prend la première). Un texte libre qui n'est ni un titre ni une fonction n'ouvre plus la recherche par mots clés : un message renvoie vers MOTS CLES, où l'on cherche directement (ou `MOTS CLES <texte>` dans la barre).

## Règles de travail (obligatoires)

Avant toute modification : point de restauration dans `SAUVEGARDES.md`. Après toute modification : test complet de TOUT le site et des données (erreurs, données manquantes, doublons, chiffres inchangés quand ils doivent l'être), en signalant tout problème trouvé, même sans lien avec la modification. On ne publie que si tout est bon, sinon retour au point de restauration. Détail : voir le haut de `SAUVEGARDES.md`.

## Fonctions (66)

### Fonctions de marché

| Code | Contenu |
|---|---|
| BRIEF | Synthèse du jour — BRVM, portefeuille, alertes, marchés mondiaux, changes, matières, taux, agenda du jour et actualités sur une page |
| BRVM | BRVM — 48 actions, indices, largeur du marché, secteurs ; en option : flottant officiel, valorisation du marché (PER), saison des résultats, publications attendues et retards, exposition par pays |
| MOST | Plus actives — Plus fortes hausses et baisses, valeurs les plus échangées sur la séance du jour, largeur du marché |
| LIQ | Liquidité BRVM — Montants échangés, jours cotés, Amihud, délai pour constituer une position |
| DIVC | Calendrier dividendes — BRVM : prochains détachements, classement par rendement, historique ; en option : aristocrates du dividende, dividende net et encaissements de vos positions |
| BANK | Banques cotées — Les banques cotées à la BRVM côte à côte : PNB, résultat, coefficient d’exploitation, coût du risque, rentabilité, solidité du bilan ; en option : historique sur 10 ans |
| EVTS | Événements des sociétés — Avis officiels depuis 2000 : AG, dividendes, états financiers ; en option : suivi des sociétés BRVM, agenda des sociétés (BRVM et résultats US) |
| NOT | Notations financières — Notes de crédit (Bloomfield, WARA, GCR) : sociétés cotées, emprunts obligataires et fonds de titrisation, historique |
| MOTS CLES | Recherche par mots clés — Tous les documents de la BRVM depuis 1998 (états financiers, rapports, avis de la BRVM et du DC/BR, bulletins de la cote, dividendes, notations), obligations, titres, fonctions et actualités ; onglet Historique de recherche (recherches des 90 derniers jours, gardées dans le navigateur de l'utilisateur seulement, jamais envoyées) |
| SGI | Intervenants du marché — SGI, sociétés de gestion d’OPCVM et de patrimoine, conservateurs, agences de notation, garants : adresses et contacts |
| UEMOA BONDS | Obligations UEMOA — Obligations cotées à la BRVM : coupon, échéance, cours, rendement, duration, sensibilité |
| GC | Courbes souveraines — Courbes des taux zéro-coupon des 8 États de l’UEMOA, écarts, coupons à l’émission |
| UEMOA/DATA | Macro UEMOA — Taux directeurs, inflation, croissance, dette, crédit, titres publics des 8 États ; en option : statistiques économiques mondiales |
| PORTF | Portefeuille — Vos positions BRVM et US : valeur, plus-values, risque (volatilité, VaR, bêta, contributions), performance, dividendes à venir ; import de relevés (Excel, CSV, PDF, photo) avec écran de contrôle, sauvegarde et restauration |
| SCREENER | Screener — Filtrer US et BRVM par ratios : FCF, croissance, qualité, valorisation, score |
| ALRT | Alertes — Marges, FCF, dette, révisions, seuils de valorisation, résultats à venir |
| MAP | Carte de chaleur — BRVM, États-Unis, Europe, Royaume-Uni, Asie, Afrique : surface = variation du jour (ou égale, ou capitalisation), couleur = variation, zoom et déplacement ; en option : marché US (Nasdaq-100, ETF, facteurs, crypto) |
| INDX | Indices mondiaux — Indices boursiers des Amériques, d’Europe, d’Afrique et d’Asie : niveau, variation, fourchette 52 semaines ; en option : contrats à terme sur indices (indication d’ouverture) |
| FG | Fear & Greed — Indice peur/avidité : États-Unis (CNN, toutes les 15 minutes) et BRVM (calculé par FQT) |
| NEWS ECO | Calendrier éco — Calendrier économique mondial : publications, prévision du consensus, réel, précédent, importance |
| ECWB | Macro US — Courbe des taux, crédit, liquidité, emploi, inflation, récession |
| RATES | Taux : Trésor, monétaire, Fed — Taux directeurs (Fed, BCE, BCEAO), SOFR, bons et emprunts du Trésor, contrats à terme, pentes, inflation anticipée ; en option : anticipations de la Fed (Fed funds), BONDS (taux souverains mondiaux : courbe US, 10 ans, UEMOA) |
| FX | Changes — Franc CFA : USD/XOF, effet de change, simulateur ; en option : changes croisés (G10, Afrique, Asie, Amériques), classement mondial des devises |
| COMMO | Matières premières — Énergie, métaux, agriculture (cacao, café, coton) : contrats à terme du jour |
| BMAP | Carte du pétrole — Flux pétroliers mondiaux, détroits stratégiques, Brent et WTI, stocks US |
| MACRO | Macro & Or — Or depuis 1833, krachs, CAPE, inflation, pétrole, VIX |
| CORR | Corrélations — Matrice BRVM × monde, paire au choix, ACP |
| RRG | Rotation (RRG) — Graphe de rotation relative : secteurs, facteurs, pays, BRVM |
| CORP RESULT | Résultats des sociétés — Calendrier des résultats US (date, consensus, dernière surprise), résultats publiés (surprise, réaction du cours) ; en option : objectifs de cours des analystes |
| HELP | Aide — Toutes les fonctions, leurs onglets et les raccourcis |

### Fonctions par titre (ticker puis code, ex. SNTS DES)

**Description**

| Code | Contenu |
|---|---|
| DES | Description — Profil, émission, ratios, chiffre d’affaires et BPA, secteur : la fiche d’identité du titre |
| CN | Actualités de la société — Articles qui citent la société, publications officielles, historique des événements |
| HDS | Actionnariat — Principaux actionnaires, répartition du capital et flottant |
| STOCK BONDS | Titres liés — Obligations de l’émetteur cotées à la BRVM, indices, sociétés du même secteur |
| CACS | Opérations sur titres — Dividendes, assemblées, opérations sur le capital, à venir et passées |

**Graphiques et cours**

| Code | Contenu |
|---|---|
| GP | Graphique — Ligne style Bloomberg, bougies, moyennes mobiles, volume, RSI, MACD, comparaison |
| HP | Historique des cours — Cours quotidiens, hebdomadaires, mensuels avec variations et volumes |
| TECH | Analyse technique — Moyennes mobiles, RSI, MACD, stochastique, Bollinger, ATR, pivots, synthèse des signaux |
| TRA | Rendement total — Dividendes réinvestis contre cours seul, par période et par année |
| COMP | Rendements comparés — Performance contre d’autres titres et un indice, dividendes réinvestis |
| HS | Écart historique — Rapport ou écart entre deux titres : moyenne, bandes ±1 et ±2 écarts-types, score z, centile, demi-vie |
| SEAS | Saisonnalité — Rendements années × mois, jour de la semaine, « Sell in May » |
| HVT | Volatilité historique — Volatilité sur 10 à 260 séances, Parkinson, centiles, volatilité glissante |
| VAP | Volume par prix — Échanges par niveau de cours, prix le plus échangé, zone de valeur, VWAP |

**Fondamentaux**

| Code | Contenu |
|---|---|
| FA | Analyse financière — Chiffres clés, compte de résultat, bilan, flux et ratios ; BRVM : états financiers publiés poste par poste et une centaine de ratios sur tout l’historique |
| GF | Graphique des fondamentaux — Chiffre d’affaires, résultat, BPA, FCF, dette par exercice, PER historique |
| RV | Valorisation relative — Multiples contre pairs du secteur et contre son propre historique, juste valeur |
| WACC | Coût du capital — WACC, ROIC et création de valeur (ROIC − WACC) |
| DVD | Dividendes — Historique, rendement, croissance, taux de distribution, couverture par le FCF |
| DDM | Modèle de dividendes — Gordon-Shapiro, croissance implicite, sensibilité |
| MODL | Scénarios bull/base/bear — Simulateur de valorisation : hypothèses modifiables, séparées des données publiées |

**Analystes**

| Code | Contenu |
|---|---|
| ANR | Recommandations — Achat / conserver / vente, objectifs de cours, potentiel, BPA attendu |
| EE | Estimations — Consensus du BPA, révisions, croissance attendue |
| SURP | Surprises de résultats — BPA publié contre consensus, réaction du cours |

**Composition de l’indice**

| Code | Contenu |
|---|---|
| MEMB | Composition de l’indice — Valeurs de l’indice, poids, concentration |
| MOV | Contributions à l’indice — Valeurs qui font monter ou baisser l’indice aujourd’hui, en points |

**Quant**

| Code | Contenu |
|---|---|
| SCOR | Score multifactoriel — Note /100 : value, qualité, croissance, momentum, rendement, faible volatilité |
| LQA | Liquidité et coûts — Échanges 20/60 séances, séances sans échange, coût d’aller-retour, délai de sortie, taille de position |
| ANOM | Anomalies — Alertes statistiques : cours, volume, tendance, résultats, dividendes, données suspectes |
| PEER | Comparateur de sociétés — 2 à 10 sociétés côte à côte, nuage de points sur deux critères |

**Risque**

| Code | Contenu |
|---|---|
| BETA | Bêta historique — Bêta sur plusieurs fenêtres, volatilité, corrélation, drawdown, pairs |
| QLAB | Laboratoire quant — Statistiques du cours (distribution, VaR, Hurst, momentum, analogues, probabilité bayésienne) ; valorisation des actions BRVM par sept modèles, risques et alertes, qualité et facteurs |
| BTST | Backtest — 8 stratégies, levier, Monte Carlo, durée des drawdowns |

**Autres**

| Code | Contenu |
|---|---|
| MONITOR | Moniteur de marchés — Tous les titres suivis, signal SMA 200 de QQQ, séance BRVM, carte des capitalisations |
| NEWS | Actualités — Fil d’actualités relié aux titres : BRVM, UEMOA, marchés mondiaux, banques centrales |
| MENU | Menu du titre — Toutes les fonctions disponibles pour ce titre, classées par thème |

## QLAB (laboratoire quant)

| Onglet | Contenu | État |
|---|---|---|
| Statistiques | distribution des rendements, VaR/CVaR, cône de volatilité, autocorrélation, exposant de Hurst, momentum, analogues k-NN + DTW, probabilité bayésienne | en ligne |
| Valorisation (actions BRVM) | **Valorisation** : valeur et fourchette de chacun des sept modèles (DCF probabiliste, simulation Monte-Carlo, actualisation des dividendes, multiples historiques, multiples des comparables, résultat résiduel, DCF inversé), sans synthèse ; **Risques et alertes** : alarmes, sensibilités, régimes économiques, liquidité, révisions et événements ; **Qualité et facteurs** : facteurs de qualité et de risque, qualité des données, comptes et ratios utilisés. Aucune projection du cours. | en ligne (moteur QLAB-V, recalcul chaque soir) |

Méthode de la valorisation : [docs/QLAB2_VALORISATION.md](QLAB2_VALORISATION.md).

L'onglet « Prévisions » (QLAB 3, prévision des résultats) a été retiré le 19/10/2026 à la demande du propriétaire : son code, ses données et son cahier des charges restent dans l'historique du dépôt (point de restauration du 19/10/2026, 17 h 30) et une copie de ses dernières prévisions dans les données brutes (`qlabp/` de la branche `raw`). La lecture des publications intermédiaires (`scripts/periodiques.py`, appelée par `comptes.py`) est gardée.

## Méthodes : saison des résultats, aristocrates, banques, import du portefeuille, présentations DES (depuis le 19/10/2026)

- **BRVM, Saison des résultats et Publications attendues et retards** (`web/pages20.js`) : échéances de la BRVM pour un exercice clos le 31 décembre — 1er et 3e trimestres le 30 avril et le 31 octobre, 1er semestre (rapport certifié) le 31 octobre, états financiers de l'exercice le 30 avril de l'année suivante. Une période est publiée dès le premier document de la société qui la nomme dans son intitulé (rapport d'activités, états financiers, rapport annuel ou du conseil, rapport des commissaires, communiqué de résultats ; fichier `events.json`). Année = la plus récente citée dans l'intitulé, jamais après la date de publication ; sans année, déduite de la date de publication et marquée d'un astérisque ; un intitulé portant l'année précédente pour une période déjà publiée, paru plus de 300 jours après l'échéance, est rattaché à la période suivante (astérisque). Le « 2e semestre » n'est pas compté comme semestre. Société cotée après l'échéance : non comptée. Sans document : « aucun document » (rien n'est supposé). Vérifié sur la presse (retards des états financiers 2025 : BOA Côte d'Ivoire 43 jours, NSIA Banque 13, CIE 20).
- **BRVM, Exposition pays** : pays du siège (`cty`) ; capitalisation flottante = capitalisation × flottant officiel ; PER agrégé = Σ capitalisations ÷ Σ résultats des sociétés bénéficiaires (dernier BNPA × titres) ; rendement agrégé = moyenne des rendements pondérée par les capitalisations.
- **DIVC, Aristocrates du dividende** (`web/pages21.js`) : dividende net par action des avis (`dividends.json`, ajusté des fractionnements, exceptionnels exclus, acompte et solde additionnés) ; années versées, années sans baisse, hausses de suite comptées en remontant depuis le dernier exercice ; un exercice absent interrompt la série ; aristocrate = 10 ans et plus sans baisse, régulier = 5 ans et plus ; série arrêtée = rien depuis deux exercices.
- **DIVC, Dividende net et encaissements** : paiements déjà annoncés seulement ; montant pour les positions de PORTF (navigateur) = titres × dividende net, si le détachement est à venir.
- **PORTF, import de relevés** (`web/pages22.js`) : tout est lu dans le navigateur (le fichier n'est ni envoyé ni gardé) — CSV / texte (séparateur deviné, accents Windows), Excel .xlsx (lu sans bibliothèque : archive et feuilles XML), PDF dont le texte est écrit en clair (filtres Flate et ASCII85 ; cellules rangées sous les colonnes d'en-tête par leur position), lignes collées (`TITRE;QUANTITÉ;PRIX`). Titre reconnu par le code ISIN (`profiles.json`), le code, puis le nom (noms courts et officiels, variantes « Côte d'Ivoire », « Bank of Africa », noms usuels) ; plusieurs titres possibles : choix sur l'écran. Quantité et prix de revient pris sous les en-têtes reconnus ; sans en-tête, premier nombre = quantité (signalé « à vérifier »). Lignes de totaux, espèces et en-têtes ignorées. Rien n'est enregistré avant « Valider » ; « Mettre à jour » ou « Remplacer tout le portefeuille » ; un titre sur plusieurs lignes est additionné. Photos, captures d'écran et PDF scannés ou à police codée (depuis le 19/10/2026) : lus dans le navigateur par Tesseract.js 7.0.0 (lecture du français, modèle `fra` 4.0.0_best_int) et pdf.js 6.3.289 (version compatible « legacy »), bibliothèques gratuites et libres hébergées sur le site (`public/lib/ocr/`, 15 Mo, licences dans `LISEZMOI.txt`), téléchargées seulement à la première image importée puis gardées par le navigateur ; une image est agrandie (petite capture) ou réduite (grande photo) avant lecture ; deux nombres collés par la lecture sont séparés (« 26 500 21 350,50 ») ; l'écran de contrôle avertit qu'il faut vérifier chaque chiffre. Sans le module (copie hors ligne, lien temporaire), un message l'indique. Non lu : ancien format .xls. Sauvegarde : fichier JSON `portefeuille-fqt-AAAA-MM-JJ.json` (positions, prix de revient, devise de référence), restaurée par le même écran de contrôle.
- **DES, présentation des sociétés BRVM** (`seed/des_fqt.json`, depuis le 19/10/2026) : 48 textes écrits par FQT avec nos propres mots (jamais mot pour mot la fiche tierce) ; chaque fait est prouvé par une citation exacte d'un document officiel — documents publiés par la société à la BRVM, site officiel de la société ou de son groupe, avis de la BRVM ; jamais la fiche tierce, la presse ou une encyclopédie — puis relu par une seconde vérification indépendante (affirmations non prouvées retirées). Preuves (document, adresse, date, citation) dans `seed/des_fqt_preuves.json`. La BRVM ne publie pas de texte de présentation des sociétés (seulement coordonnées et documents). Le texte remplace celui de la fiche tierce dans `profiles.json` à la construction du soir (`build_extra.profiles`) ; une société absente du fichier garde l'ancien texte. Pour changer un texte : modifier les deux fichiers ensemble, avec la preuve. À suivre : Uniwax (activité textile non prouvée par un document lisible ; changement d'actionnaire en 2026), Unilever CI (cession annoncée en avril 2025 à un consortium mené par la SDTM), actionnariats de BICICI et d'Oragroup, nouveau contrat de la SODECI (2026).
- **BANK** (`web/pages21.js`) : séries des fiches FA (`fa/<banque>.json`, Y, montants en millions de FCFA), les mêmes que FA ; coefficient d'exploitation et ratio de solvabilité tels que publiés par la banque ; coût du risque ÷ crédits de fin d'exercice ; un chiffre absent du dernier exercice est pris dans l'un des deux précédents avec l'année affichée (jamais pour une croissance) ; croissance du résultat après un résultat négatif : « n.s. ».

## Données et automatisations

Tout est automatique (GitHub Actions) ; aucune intervention manuelle n'est nécessaire.

| Tâche | Rythme | Rôle | Écrit |
|---|---|---|---|
| Terminal (`terminal.yml`) | toutes les 15 min, jour et nuit ; base complète chaque soir de semaine (22:35 UTC) | cours BRVM, US, crypto, actualités, avis, obligations ; le soir : toute la base, comptes, valorisation QLAB | branches `data`, `raw`, `site` ; archive de la séance sur `main` |
| Métronome (`metronome.yml`) | en continu, relancé chaque heure | déclenche le relevé pile à :00, :15, :30, :45 (la programmation de GitHub est parfois retardée) | — |
| Bulletins officiels (`boc.yml`) | toutes les 2 h | lecture des bulletins officiels de la cote (cours, dividendes, opérations sur le capital) | `boc` |
| Comptes des sociétés cotées (`comptes.yml`) | chaque jour, puis passages enchaînés tant qu'il reste des documents | lecture de tous les documents déposés par les sociétés (états financiers, rapports, communiqués), contrôle des identités comptables ; lecture répartie sur 6 machines tant qu'il reste au moins 60 documents (voir ci-dessous) | `comptes` |
| Dividendes BRVM (`dividendes.yml`) | chaque jour, passages enchaînés si besoin | avis et calendriers de paiement des dividendes | `dividendes` |
| Base historique (`histo.yml`) | chaque soir | archive cumulative contrôlée (cours, indices, dividendes, événements, états financiers) | `histo` |
| Export complet (`export.yml`) | chaque nuit | copie autonome du site et de ses données, ouvrable sans connexion | `export` |
| Copie de secours (`copie.yml`) | chaque nuit (03:38 UTC) | copie complète de toutes les branches (code et données) vers un dépôt privé hors GitHub ; ne supprime jamais rien côté secours ; alerte un mois avant l'expiration de sa clé (17/10/2027) | dépôt de secours |
| Lien temporaire (`lien.yml`) | à la demande | lien d'accès au terminal qui expire tout seul | — |
| Sonde, Références (`probe.yml`, `refs.yml`) | à la demande (développement) | tests de sources, documents de référence | `probe`, `refs` |
| Archives BRVM (`archives.yml`) | à la demande | vérification : documents PDF du site de la BRVM gardés par l'archive web et absents de la liste des publications (`scripts/archives_brvm.py`) ; ne lit, n'écrit et ne publie rien (liste gardée 7 jours dans les fichiers du passage) | — |
| Essai des machines (`essai.yml`) | à la demande | avant tout changement de machine (version d'Ubuntu chez GitHub, serveur de secours) ou du calcul de la base : relit un échantillon de documents déjà lus (comptes, scans, dividendes, bulletins) sur Ubuntu 24.04 et 26.04 et compare chaque montant au cache, fait un passage du Terminal sans rien publier et liste les chiffres clés qui changent | — |
| Contrôle quotidien (`controle.yml`) | chaque matin (06:10 UTC) et à la demande | contrôle complet : données publiées (fichiers essentiels présents, lisibles et frais, univers BRVM complet, nombres de lignes comparés au contrôle précédent, doublons, valeurs aberrantes, cohérence entre fichiers, chiffres clés des 48 actions) et parcours du site (toutes les fonctions et tous les onglets, iPhone 13, QLAB, erreurs JavaScript, textes suspects, noms de sources, symboles affichés en émoji sur iPhone, confidentialité) ; rapport vert / orange / rouge dans le résumé du passage ; ne fait jamais échouer le passage (aucun e-mail d'échec) | `probe` (dossier `controle/` : `rapport.md`, `rapport.json`, historique des 30 derniers contrôles) |

**Garde des données avant chaque publication** (`scripts/garde.py`, appelé dans l'étape « Publier les données » de `terminal.yml`, depuis le 19/10/2026) : chaque fichier de la publication précédente (celle lue au début du passage) est comparé au nouveau ; un fichier disparu, vide ou illisible, ou un fichier de fond (base, séries, FA, QLAB, dividendes, événements, actualités…) de plus de 20 Ko tombé sous le quart de sa taille précédente, reprend sa dernière bonne version. Chaque remise en place est un avertissement dans le passage, jamais un échec ; un problème du script lui-même ne touche à rien. Les dossiers retirés volontairement (`qlabp/`, QLAB Prévisions) ne sont jamais remis.

**Lecture répartie des comptes** (`comptes.yml`, `scripts/comptes_merge.py`, depuis le 18/10/2026) : tant qu'il reste au moins 60 documents, la lecture est faite par 6 machines Ubuntu 24.04 en même temps (sinon une seule). Chaque document appartient à une seule part, fixée par son adresse (`cpt_part_of`) : aucun document n'est lu deux fois. Chaque machine lit sa part dans sa propre copie de la branche `comptes` et ne rend que ce qu'elle a lu ; une seule machine met tout en commun puis contrôle avant de publier : (1) registre complet — aucun document perdu, aucun document lu par deux parts ou par une autre part que la sienne, aucun fichier de texte sans document, nombre = avant + nouveaux ; (2) relecture seule, à l'ancienne façon, de deux documents de ce passage (un scan, un document à couche texte) : textes identiques exigés ; (3) lecture des postes (`comptes.json`) identique, avant / après, pour tous les documents qui n'ont pas été lus pendant ce passage. Un contrôle en échec : rien n'est publié et le passage suivant reprend sur une seule machine (`shards=1`). Une machine de lecture en échec : ses documents restent à lire au passage suivant. Essai du 18/10/2026 (250 documents réels, 13 documents synthétiques, 3 parts) : registre et textes identiques, octet pour octet, à la lecture sur une seule machine. Lancer à la main : `workflow_dispatch` avec `shards` (vide = automatique).

**Longs scans sans page des états** (`fetch_extra.py`, `cpt_again`, `SCAN_V`) : un scan de plus de 20 pages dont la recherche rapide (100 dpi) ne trouve aucune page des états est cherché une seconde fois plus finement (150 dpi, français, seuil plus bas), une seule fois ; s'il n'y a toujours rien, il n'est plus repris (avant le 18/10/2026, 76 documents étaient retéléchargés et relus à chaque passage et le compte des documents restant à lire ne pouvait jamais arriver à zéro). Une couche texte lue et vérifiée, même avec peu de montants, n'est plus reprise non plus.

**Lectures d'un même document** (`comptes.py`, `read_doc`) : les montants vérifiés par une identité dans une autre lecture du même scan (autre langue, autre résolution) complètent la lecture retenue, y compris quand cette autre lecture n'a pas trouvé la ligne qui annonce l'unité (unité compatible, montants communs identiques) ; dans ce dernier cas, une identité dont un montant est lu autrement par une troisième lecture (un chiffre confondu, 5 pour 6) ne confirme aucun de ses montants (Sicable 2017-2018 : résultat d'exploitation, valeur ajoutée, excédent brut repris ; BOA Côte d'Ivoire 2021 : total du bilan lu 714 609 par une lecture et 714 509 par une autre, non repris).

**Postes calculés d'après le document** (`comptes.py`, `_complete`, `CALC_KEYS` ; `scripts/comptes_banques.py`) — seulement pour un exercice dont le bilan s'est vérifié ; rien n'est estimé :
- *Produit net bancaire de l'ancien plan comptable bancaire* (avant 2018 : comptes de résultat en deux tableaux, charges puis produits, sans ligne « produit net bancaire ») : produits d'exploitation bancaire − charges d'exploitation bancaire (intérêts, crédit-bail, commissions, opérations financières, divers), seulement si tout le compte de résultat se vérifie colonne par colonne (somme des postes = total de chaque tableau, total des charges = total des produits, total d'exploitation bancaire imprimé = somme de ses postes), années lues dans l'en-tête du tableau et confirmées par le résultat de l'exercice lu au bilan (même montant, même échelle). Les chiffres que les banques communiquent ajoutent parfois leurs produits généraux d'exploitation (écart de 0 à 4 %).
- *Chiffre d'affaires SYSCOHADA* = ventes de marchandises + ventes de produits fabriqués + travaux, services vendus (+ produits accessoires), quand la ligne du total manque ; une partie imprimée sans montant (case vide) compte pour zéro.
- *Résultat de l'exercice* d'une banque manquant ou lu à zéro au bilan : repris du compte de résultat vérifié (BOA Côte d'Ivoire 2011 : perte de 487 millions, et non 0).
- *Sous-totaux SYSCOHADA absents du document* (`subtotals`, depuis le 19/10/2026) : un sous-total n'est calculé que si un autre montant publié du même exercice le confirme à 0,5 % près — résultat des activités ordinaires = résultat d'exploitation + résultat financier, résultat financier ou d'exploitation par différence (confirmés par résultat net = RAO + HAO − impôts − participation) ; excédent brut d'exploitation = valeur ajoutée − charges de personnel et l'inverse (confirmés par EBE − dotations ≈ résultat d'exploitation) ; capitaux propres = ressources stables − dettes financières (confirmés par le total du passif). Essai du 19/10/2026 : 116 montants ajoutés, aucun montant existant changé ni retiré.
Ces montants calculés ne participent à aucun contrôle entre documents ; ils ne comblent qu'un exercice resté vide, en dernier (après la base tierce et les archives), et ne remplacent jamais un montant existant (`calc` dans `comptes.json` consolidé ; mention « calculé d'après les comptes publiés » dans `src_years`). Dans FA (onglets des comptes détaillés), ces cases sont en italique avec l'infobulle « Total recalculé à partir des postes publiés de l'exercice » (`cx` dans les lignes de `fa/<titre>.json`) ; un poste ou un exercice entièrement vide n'est pas affiché.

**Unité d'un document sans ligne d'unité** (`comptes.py`, `consolidate`, depuis le 19/10/2026) : seulement pour un exercice vérifié qu'aucune autre lecture ne couvre (aucun document d'unité connue pour cette année, quel que soit le périmètre) : unité unique des autres exercices du même document et du même périmètre, avec un chiffre clé (total du bilan, chiffre d'affaires, produit net bancaire) ; sinon unité des exercices voisins (±3 ans) quand une seule échelle est à moins d'un demi-ordre de grandeur et la suivante au moins 1,5 ordre plus loin. Essai du 19/10/2026 : 8 exercices ajoutés (Servair Abidjan 2004-2011 en SYSCOHADA, SOGB 2005), aucun montant existant changé ni retiré.

**Documents retrouvés dans l'archive web** (`seed/archives_comptes.json`, `cpt_archived` dans `fetch_extra.py`) : documents de la BRVM qui ne sont plus sur son site mais gardés par l'archive web (liste de `archives.yml`), ajoutés à la lecture des comptes avec leur horodatage (`wb`, `wb_u`) ; téléchargés depuis la copie de l'archive (`get_wb`, au rythme de l'archive) ; dans MOTS CLES, le lien passe par le relais des anciens documents (`/doc/a/…`). 34 documents au 19/10/2026 : Unilever CI 2010-2013, Coris Bank 2017, 2020, 2021 et 1er semestre 2024, Air Liquide CI / Erium (26/04/2023), rapport annuel de Palm CI (08/07/2024), SITAB, Sucrivoire 2019 et 2024, Vivo Energy CI 2016, ETI 2018 et 2022, Oragroup 2020, BOA Bénin 2019, BOA Sénégal 2017, BOA Mali 1er semestre 2021, SIB 1ers semestres 2022 et 2025, SMB CI 2022, rapport annuel d'Uniwax 2018. Un document de cette liste déjà présent dans la liste des publications n'est pas ajouté une seconde fois ; un même fichier déposé deux fois (suffixe « _0 ») n'apparaît qu'une fois dans MOTS CLES.

**Données prises à l'extérieur : une donnée prise n'est jamais perdue** (`scripts/sticky.py`, décision du 18/10/2026) — la base tierce (BRVMetrics, elle-même tirée de SikaFinance et de la BRVM), les archives SikaFinance (`sika_hist.json`) et les fiches des sociétés (`profiles.json`) servent de copie pour les chiffres que la BRVM ne donne pas ; la BRVM reste la source principale. À chaque passage du Terminal, le miroir de la base tierce (branche `raw`, `brvm_src/`) est fusionné dans la nouvelle copie : un titre, un exercice, une séance, un avis ou un champ que la source n'a plus est repris (une valeur nouvelle ou corrigée l'emporte ; un fichier dont le format change est gardé à côté, « .ancien », sans mélange). Un champ qu'une fiche société n'a plus garde sa valeur précédente. Chaque soir, la base historique (branche `histo`, dossier `instantanes/`) en garde une copie permanente (même fusion), dont chaque version reste dans l'historique de la branche et dans la copie de secours. Base tierce injoignable : miroir utilisé (déjà en place) ; base figée depuis plus de 21 jours : signalée (`boc_check.json`, « base_ext ») et le récent vient des sources BRVM (comptes lus, avis, bulletins de la cote, cours en séance). Liste des publications des sociétés (lecture des comptes, `cpt_events`) : liste tierce, sinon son miroir (branche `raw`), sinon les seules pages « rapports des sociétés cotées » de brvm.org (pages des 48 sociétés gardées dans `brvm_rapports.json`) ; le registre des documents déjà lus n'est jamais réduit.

**Machines (Ubuntu)** : les automatisations qui lisent des PDF (`terminal.yml` pour le relevé, `comptes.yml`, `dividendes.yml`, `boc.yml`, `probe.yml`) restent sur Ubuntu 24.04, comme `controle.yml` (Chromium de Playwright, pour le parcours du site, y est pris en charge), les autres passent sur Ubuntu 26.04. Raison (essai du 17/10/2026 sur 130 comptes, 42 dividendes, 9 bulletins) : sur Ubuntu 26.04 les outils de lecture plus récents (pdftotext 26.01, tesseract 5.5) donnent les mêmes montants pour 128 documents de comptes sur 130 et 42 dividendes sur 42, mais lisent autrement 6 % des couches texte et la moitié des scans, et ont mal lu un montant (report à nouveau multiplié par 1 000) que les contrôles comptables ne voyaient pas ; Ubuntu 24.04 relit tout à l'identique du cache. GitHub garde deux versions d'Ubuntu : 24.04 reste disponible jusqu'à la version suivante (vers 2028-2029). Avant d'y passer ces automatisations, relancer `essai.yml` : on ne bascule que si les montants relus sont identiques. Même règle pour le serveur de secours (mêmes versions des outils de lecture).

**Contrôles automatiques des données (calcul de la base, `scripts/build_terminal.py`)** — chaque correction est listée dans `boc_check.json` et dans le journal du passage :
- *Trésorerie nette et dette nette de la base tierce* (`base_fix`) : comparées aux comptes publiés et vérifiés (trésorerie actif − trésorerie passif ; dettes financières + trésorerie passif − trésorerie actif, référentiel SYSCOHADA). Le montant de la base est remplacé par celui des comptes quand la base suit cette définition au moins trois autres exercices, quand il n'en diffère que par le signe, ou quand il est isolé alors que les comptes (au moins deux documents) sont dans la continuité des années voisines. Une trésorerie, une dette nette, des dépôts ou des crédits plus grands que le total du bilan sont retirés. Liste : `base_rejets`.
- *Séances manquantes au milieu de l'historique* (jour entier absent de la base, ex. 27/02/2025) : reprises du bulletin officiel de la cote, ramenées sur la base de la série (facteur local stable des séances voisines), seulement si le bulletin est cohérent avec la veille et le lendemain (un bulletin daté d'un jour férié qui reprend la veille est écarté). Nombre : `gap_fill`, `gap_fill_by`.
- *Clôtures fausses de la base* : remplacées par la clôture officielle quand le bulletin est cohérent (`close_fix`).
- *Opérations sur le capital non ajustées* : fractionnements (avis, paliers du bulletin) et augmentations de capital avec droits préférentiels (cours de référence abaissé par la BRVM la veille de l'ex-droit, sans dividende qui l'explique, ex. SAFC 24/04/2026) : cours antérieurs, dividendes et données par action ramenés sur la base actuelle par le rapport clôture ÷ cours de référence. Les variations annuelles publiées par la BRVM, elles, ne sont pas ajustées des droits.
- *Versements de dividendes en double* (même exercice, même montant à 1 % près, dates à 75 jours près) : le mieux renseigné est gardé. Les paiements fractionnés (montants différents) restent.
- *Événements en double* (même titre, même société, mêmes dates, autre fichier) : gardés une fois, avec la rubrique la plus précise.

**Lecture des avis de dividendes** (`scripts/dividendes.py`) : une date dont l'année est mal lue ou mal imprimée (date ex-dividende, paiement, fermeture des registres ou signature) prend l'année du numéro de l'avis quand elle tombe alors à moins de 60 jours des autres dates ; le catalogue des documents (recherche MOTS CLES) n'intitule « Avis … paiement de dividendes » que les vrais avis (convocations, états financiers, décisions et communiqués gardent leur propre intitulé, en-têtes et adresses écartés).

Le site publié lit ses données en direct sur la branche `data` (`api/data.js`) ; la branche `site` ne contient que la page et n'est redéployée que si le code change. Les branches de données ne sont jamais déployées (`vercel.json`).

**Documents** : le site n'affiche jamais l'adresse d'origine d'un document. Le relais remplace les adresses dans les données par des adresses du site, et `vercel.json` les sert à la volée (rien n'est stocké) :

| Adresse du site | Document servi |
|---|---|
| `/doc/b/<fichier>` | documents publiés (états financiers, rapports, avis) |
| `/doc/f/<fichier>` | bulletins de la cote du jour |
| `/doc/a/<horodatage>/<jeton>` | anciens documents (archive web, copie à la date indiquée ; jeton = chemin d'origine en base64url) : servis par `api/doc.js`, qui suit les redirections de l'archive, ne renvoie que des documents (jamais une page de l'archive) et affiche « Document indisponible » sinon ; limite 4,4 Mo |
| `/doc/c/<horodatage>/<jeton>` | anciens bulletins (même archive, même fonction) |
| `/doc/r/<chemin>` | quelques documents d'un site d'information boursière |

La recherche MOTS CLES contrôle chaque ligne contre le nom de son fichier (`fix_by_file` dans `scripts/build_search.py`) : un fichier d'une autre société ou d'un autre type que l'intitulé est rattaché à la bonne société, avec un intitulé refait d'après le fichier.

### Secours si GitHub ne répond plus

- **Copie** : `copie.yml` envoie chaque nuit tout le dépôt vers un dépôt privé hors GitHub (secret GitHub `GITLAB_TOKEN`, droits lecture et écriture du dépôt uniquement).
- **Lecture par le site** : si GitHub ne répond plus (ou ne connaît plus le dépôt), `api/data.js` lit les données dans la copie (variable Vercel partagée `GITLAB_READ_TOKEN`, lecture seule, reliée au projet). Le site reste alors utilisable avec des données d'au plus un jour. Essai du secours seul : `/api/data?p=qlab/index.json&via=2`.
- **Clés** : les deux clés expirent le 17/10/2027. Alertes sans intervention : e-mail de GitLab quelques jours avant l'expiration, et la copie de secours échoue exprès à partir du 17/09/2027 (e-mail d'échec de GitHub).
- **Renouveler les clés (une fois par an, avant l'expiration, environ 10 minutes)** :
  1. GitLab (compte de la copie) → la page des jetons d'accès où les clés ont été créées (Settings → Access tokens du projet de la copie, ou Preferences → Access tokens du compte) → bouton **Rotate** sur chacune des deux clés (mêmes droits, nouvelle date d'expiration) ; copier chaque nouvelle valeur au moment où elle s'affiche (elle n'est montrée qu'une fois). Ne jamais coller une clé dans une conversation ni dans un fichier du dépôt.
  2. Clé d'écriture → GitHub : dépôt qui lance les automatisations → Settings → Secrets and variables → Actions → `GITLAB_TOKEN` → Update.
  3. Clé de lecture → Vercel : projet du site → Settings → Environment Variables → `GITLAB_READ_TOKEN` → Edit → Save, puis **Redeploy** du dernier déploiement de production (une variable modifiée ne sert qu'après un redéploiement).
  4. Vérifier : Actions → « Copie de secours » → Run workflow (doit réussir) ; puis ouvrir `/api/data?p=qlab/index.json&via=2` sur le site (doit afficher des données).
  5. Reporter la nouvelle date d'expiration ici et dans le contrôle d'échéance de `copie.yml` (date du 17/09 de l'année suivante).
- **Page du dépôt** : le champ « site web » du dépôt doit rester rempli avec l'adresse du dépôt lui-même — s'il est vide, Vercel y remet automatiquement l'adresse du site à chaque mise en ligne.
- **Plan B complet** (à préparer) : kit d'installation d'un serveur qui reprendrait les automatisations et écrirait dans la copie.

## Sécurité du site (état au 19/10/2026)

- En-têtes (`vercel.json`) : toutes les adresses — pas d'indexation, `nosniff`, aucun référent envoyé, page jamais intégrée dans un autre site (`X-Frame-Options: DENY`), caméra, micro et position refusés, HTTPS imposé (`Strict-Transport-Security`) ; page du terminal seulement (`/`, `/index.html`, depuis le 19/10/2026) — `Content-Security-Policy: object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'` (aucun plugin, aucune balise `base` injectée, aucun formulaire envoyé ailleurs) et `Cross-Origin-Opener-Policy: same-origin` (une page ouverte depuis le terminal ne peut pas le piloter). Les documents (`/doc/…`) et les données (`/data/…`) ne reçoivent pas ces deux en-têtes (lecteur PDF des navigateurs).
- Relais (`api/data.js`, `api/doc.js`) : adresses demandées contrôlées (liste de caractères, pas de `..`), réponses d'erreur courtes sans détail, aucun en-tête CORS (seul le site lui-même peut lire les données depuis un navigateur), clé de lecture de la copie de secours dans les variables de Vercel.
- Aucun secret dans le dépôt (`.gitignore` : `.env`, `.env.*`, `*.pem`, `*.key`, `.vercel/`) ; clés dans les secrets de GitHub et les variables de Vercel.
- Aucune bibliothèque tierce chargée par le site (tout le code est dans `index.html`) ; outils de construction et de test à version fixe (terser 5.36.0, Playwright 1.56.0).
- Import du portefeuille : fichiers lus dans le navigateur seulement, 15 Mo au plus, type vérifié par le contenu (et non par l'extension).
- Sauvegardes automatiques : copie complète chaque nuit vers le dépôt de secours, export autonome, base historique.
- Le reste de la liste (connexion, mots de passe, sessions, RLS, webhooks, e-mail confirmé, limitation des requêtes) concerne le backend (comptes, abonnements, paiements), à faire au feu vert du propriétaire.

## Fichiers

```
index.html                 page générée : python3 build.py (assemble web/ ; code compacté sans commentaires par terser, obligatoire)
web/                       style.css, body.html, core.js (fonctions, navigation), engine.js (moteur quant), chart.js, pages*.js
api/data.js                lecture des données publiées (branche data) ; adresses des documents remplacées par /doc/… et
                           libellés de provenance retirés au passage ; alias de certains fichiers (ALIAS)
scripts/scrape.py          relevé de séance
scripts/fetch_extra.py     sources complémentaires, avis, comptes et documents de la BRVM
scripts/build_terminal.py  construction de toute la base data/ (puis QLAB le soir)
scripts/build_search.py    index de la recherche MOTS CLES
scripts/comptes.py         lecture et contrôle des états financiers publiés
scripts/comptes_merge.py   lecture des comptes répartie : mise en commun et contrôles avant publication
scripts/comptes_banques.py produit net bancaire des comptes de résultat de l'ancien plan bancaire (lu par comptes.py)
scripts/sticky.py          données extérieures : fusion avec la copie précédente (une donnée prise n'est jamais perdue)
scripts/archives_brvm.py   vérification : documents de la BRVM gardés par l'archive web et absents de la liste
scripts/dividendes.py      avis et calendriers de dividendes
scripts/qlab.py, qlab_core.py, qlab_backtest.py   moteur de valorisation QLAB (versions, événements, validation)
scripts/periodiques.py     lecture des publications intermédiaires (trimestres, semestres), appelée par comptes.py
docs/                      cahiers des charges et méthodes de QLAB ; PASSATION.md (état du travail entre deux sessions)
seed/archives_comptes.json documents de la BRVM retrouvés dans l'archive web, ajoutés à la lecture des comptes
seed/des_fqt.json         présentations des sociétés BRVM (DES) écrites par FQT ; des_fqt_preuves.json : preuve de chaque fait
public/lib/ocr/            Tesseract.js et pdf.js (lecture des photos et des PDF scannés de l'import PORTF), licences dans LISEZMOI.txt
outils/essais/             test complet du site en local et comparaisons de deux constructions (voir « En local »)
outils/controle/           contrôle complet (données et site) : controle.py, verifier.sh ; interdits.sha (empreintes des noms
                           qui ne doivent jamais apparaître sur le site, sans les noms eux-mêmes)
scripts/garde.py           garde des données avant chaque publication (dernière bonne version d'un fichier abîmé)
SAUVEGARDES.md             points de restauration (retour arrière possible à chaque étape)
```

## En local

```bash
npm install -g terser@5.36.0                        # une fois : build.py s'arrête sans lui
python3 build.py                                    # assemble index.html
git fetch origin data && git archive origin/data | tar -x -C /tmp/qsite
cp index.html /tmp/qsite/ && python3 -m http.server -d /tmp/qsite 8000   # http://localhost:8000
# (en local, les données ne passent pas par le relais : adresses d'origine et noms de fichiers réels)
```

**Test complet du site** (`outils/essais/`, à lancer avant et après chaque modification ; Playwright avec Chromium et terser requis) :

```bash
git fetch origin +refs/heads/data:refs/remotes/origin/data && mkdir -p /tmp/d && git archive origin/data | tar -x -C /tmp/d
bash outils/essais/test_site.sh /tmp/d/data /tmp/essai_apres 8841      # ~15 min : toutes les fonctions et tous les onglets,
                                                                     # iPhone 13, QLAB 48 × 3, mots interdits
python3 outils/essais/comparer_parcours.py /tmp/essai_avant/parcours.json /tmp/essai_apres/parcours.json
python3 outils/essais/cmp_fund.py <construction A> <construction B>  # fondamentaux de deux constructions (dossiers contenant data/)
python3 outils/essais/fa_ab.py <construction A> <construction B>     # fichiers FA alignés par année : ajoutés / changés / retirés
bash outils/controle/verifier.sh /tmp/d/data /tmp/ctl [rapport.json précédent] [--meme-donnees] [--sans-site]
                                                                     # contrôle complet (celui de controle.yml) : rapport.md et
                                                                     # rapport.json vert / orange / rouge ; --meme-donnees : avant /
                                                                     # après un changement de code, tout chiffre clé changé est signalé
```

`test_site.sh` construit la page (`build.py`), applique aux données la réécriture du relais (`rw.js`, comme `api/data.js`),
sert le site en local puis lance `crawl_txt.py` (texte, infobulles, liens, erreurs JavaScript de chaque fonction et onglet),
`mobilecheck.py` (iPhone 13 : débordement horizontal, textes suspects), `qlab3all.py` (QLAB Valorisation, 48 actions × 3 vues) et
`mots_interdits.py` (NaN, undefined, null, noms de sources, liens interdits).

Outil d'analyse personnel, pas un conseil en investissement. Les données de marché restent la propriété de leurs émetteurs.
