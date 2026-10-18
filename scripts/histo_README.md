# Base historique BRVM

Archive mise à jour chaque soir. Rien n'y est jamais effacé : une valeur qui change est remplacée
et l'ancienne est conservée dans `corrections.csv`. Aucune donnée n'est estimée ni recalculée.

Fichiers CSV en UTF-8, séparateur virgule, décimales avec un point
(Excel : Données › À partir d'un fichier texte/CSV, origine « UTF-8 », délimiteur « virgule »).

| Fichier | Contenu | Clé |
|---|---|---|
| `cours/AAAA.csv` | Cours des actions tels que publiés dans le bulletin officiel de la cote : précédent, ouverture, clôture, variation %, volume, valeur échangée (FCFA), cours de référence, variation annuelle %, dernier dividende, sa date, rendement %, PER, cours moyen (bulletins 2013-2017) | date, titre |
| `indices.csv` | Clôture des indices BRVM (séances terminées), contrôlée sur les bulletins officiels : valeur du bulletin quand il la publie ; jour férié recopiant la veille et valeur figée sur la veille un jour où le marché a bougé retirés | date, indice |
| `dividendes.csv` | Dividendes nets par action, d'après les avis (`avis`) et les bulletins de la cote (`bulletin`) ; montant publié, montant ramené au nombre d'actions actuel et facteur d'ajustement ; dates d'annonce, de détachement et de paiement. Un exercice payé en plusieurs fois (acompte et solde, dividende complémentaire) : versements additionnés, dates du dernier ; dividende exceptionnel sur sa propre ligne (`type` = exceptionnel) | titre, exercice, origine, type |
| `fractionnements.csv` | Fractionnements et regroupements (ratio) | titre, date |
| `evenements.csv` | Avis et publications : assemblées, états financiers, opérations sur titres (`operation_sur_titre` = 1), document PDF | date, titre, catégorie, intitulé, document |
| `resultats.csv` | Comptes annuels : chiffre d'affaires, résultat net, capitaux propres, total bilan, trésorerie, EBIT, EBITDA, dette nette, dépôts et crédits clientèle, coût du risque (millions de FCFA) ; BNPA et dividende (FCFA par action) | titre, exercice |
| `etats_financiers.csv` | États financiers publiés par les sociétés, poste par poste (code et libellé du poste ; bilan, compte de résultat, flux ; millions de FCFA), pour les seuls exercices dont les totaux se vérifient dans le document ; périmètre (comptes sociaux ou consolidés), norme (SYSCOHADA ou IFRS) et nombre de documents qui donnent les mêmes montants | titre, exercice, poste |
| `flottant.csv` | Flottant officiel : titres, titres flottants, flottant %, seuil de 15 % | date de l'avis, titre |
| `notations.csv` | Notations financières : agence, notes long et court terme (et précédentes), perspective, échelle, validité | date, document |
| `corrections.csv` | Journal des corrections : date de constat, fichier, clé, champ, ancienne et nouvelle valeur | — |
| `controles.csv` | Contrôles de cohérence du jour (voir ci-dessous) | — |
| `etat.json` | Date de mise à jour, dernière séance, nombre de lignes par fichier, résumé des contrôles | — |

## Contrôles de cohérence

- `variation_incoherente` : la variation publiée ne correspond pas à clôture / cours précédent.
- `precedent_different` : le cours précédent ne reprend pas la clôture de la séance antérieure, sans dividende détaché ni fractionnement pour l'expliquer.
- `variation_hors_seuil` : variation au-delà de ±7,5 % sans opération sur titres connue.
- `prix_moyen_hors_fourchette` : valeur / volume éloigné des cours du jour (montant mal lu, par exemple en milliers).
- `volume_sans_valeur`, `valeur_sans_volume`, `cloture_absente` : séance incomplète pour un titre.
- `seance_incomplete` : bulletin avec nettement moins de titres que d'habitude.
- `avis_different_bulletin` : dividende d'un même exercice différent entre l'avis et le bulletin.
- `dates_incoherentes` : annonce après détachement, ou détachement après paiement.
- `flottant_incoherent`, `bnpa_signe_oppose` : chiffres contradictoires dans une même ligne.

Une alerte signale un point à vérifier, pas une erreur certaine.

## Limites connues

- Cours : bulletins au format actuel depuis fin 2017. Les bulletins plus anciens ont plusieurs mises en page ;
  seules leurs lignes qui se vérifient d'elles-mêmes sont reprises (`etat.json` indique le nombre de lignes non retenues).
- Un bulletin identique à celui de la veille (publié pour un jour férié, ex. 29/10/2020) n'est pas une séance : il est écarté.
- Montants d'un milliard de FCFA et plus imprimés en milliers dans certains bulletins : remis en FCFA (liste dans `etat.json`).
- Les ratios (marges, ROE…) ne sont pas stockés : ils se recalculent à partir de `resultats.csv` et `etats_financiers.csv`.
- Un exercice pas encore clos (comptes semestriels) n'a pas sa place dans `resultats.csv` : une telle ligne est retirée et consignée.
- `etats_financiers.csv` : un exercice provient de ses propres comptes de préférence (définitifs plutôt que provisoires), sinon de la colonne
  « exercice précédent » des comptes de l'année suivante ; un chiffre repris et corrigé par la société dans une publication ultérieure
  l'emporte. Les états lus par reconnaissance de caractères ne gardent que les montants confirmés par deux lectures ou par une
  identité comptable. Un jeu d'états dont un chiffre est faux (unité, année, ordre de grandeur) est écarté en entier ; les
  présentations de résultats et les notations ne servent jamais de source.
- Société qui publie en dollars US (Ecobank Transnational, ETIT) : quand la société publie elle-même la contre-valeur en FCFA
  (états à deux monnaies « milliers $EU | millions FCFA », depuis les comptes 2024), seules ses colonnes FCFA sont reprises ;
  pour les autres exercices, les états en dollars sont convertis au cours USD/FCFA du jour de leur publication (655,957 FCFA
  pour 1 euro × cours euro/dollar publié par la Réserve fédérale), un seul cours par exercice, figé à cette date (cours et date
  indiqués dans FA). Seuls ses états financiers consolidés sont lus (ses rapports annuels et communiqués mêlent comptes de la
  holding, trimestres et semestres) ; les états en FCFA d'une filiale déposés sous son nom ne sont pas repris.
- Dividendes : chaque versement est repris des documents officiels de la BRVM (branche `dividendes`) : avis de paiement de la
  BRVM (un avis rectificatif remplace le précédent), sinon la dernière version du « calendrier de paiement des dividendes » (un
  calendrier publié après un avis reprend une rectification), sinon l'avis du Dépositaire central. Un montant brut n'est converti
  en net qu'avec le taux d'IRVM écrit dans le document. Les montants restent ceux publiés (par action de l'époque) ; ils sont
  ramenés sur la base des actions actuelles pour les fractionnements et attributions d'actions gratuites connus (avis) ou lus sur
  les paliers du rapport « cours du bulletin ÷ cours ajusté » ; pour les années antérieures aux bulletins conservés, le cours
  imprimé à côté du dividende dans le premier bulletin après le paiement donne la base d'actions du montant (Sonatel, Onatel :
  fractionnements d'avant 2013). Les archives de l'ancien site (avis depuis 2002, bulletins, revues trimestrielles) complètent
  les années que la base ne couvre pas ; dans ces bulletins la virgule sépare les milliers (« 1,800 ») sauf deux décimales
  (« 321,08 ») et le point est décimal (« 1.828 » pour Ecobank Transnational) ; un « 1,828 » ambigu est tranché par l'ordre de
  grandeur du cours de la même ligne. Dividende publié en cents de dollar (Ecobank Transnational, exercice 2021) : montant en
  FCFA imprimé dans le bulletin officiel de la cote (0,90 FCFA), sinon converti au cours du jour de l'avis ; marqué « $ ». Dividende exceptionnel : compté dans le rendement total et le rendement sur
  12 mois, pas dans le dividende de référence ni le rendement indicatif.
- Capitaux propres d'un bilan de synthèse sans ligne de total : somme des composantes publiées (capital, primes, réserves, report à
  nouveau, résultat, autres), retenue seulement si le passif la vérifie (total − dettes financières − passif circulant − trésorerie passif).
- Flux de trésorerie (flux opérationnels, acquisitions d'immobilisations, flux disponible) : uniquement ceux lus dans les états
  financiers publiés et contrôlés par les identités du document. Le fichier de départ `seed/fcf_brvm.json` (lecture sans contrôle,
  31 exercices faux sur 32 recoupés : unités, lignes confondues avec le chiffre d'affaires) a été retiré ; aucun flux n'est estimé.
- Lecture des mises en page particulières : deux pages imprimées côte à côte (bilan et compte de résultat à gauche, TAFIRE à
  droite) sont séparées à leur gouttière avant lecture ; une colonne « 01/01/N » ou « 1er janvier N » (bilan d'ouverture) est
  l'exercice N-1 ; une unité annoncée démentie par le capital social (« montants en milliards » pour des millions) est corrigée ;
  dans un document qui réunit comptes du groupe et comptes de la société (« Sonatel SA », « ONATEL SA »), chaque bloc garde
  son périmètre ; les lignes de contrôle du TAFIRE (variation du FdR, du BFG, de la trésorerie : colonnes emplois / ressources)
  ne sont pas des montants annuels.
- Documents d'émetteurs non cotés déposés sous la page d'une société cotée (BIDC, BOAD…) et états en unités de compte ou en
  dollars (Ecobank Transnational publie en dollars : ses états ne sont pas repris, les chiffres affichés pour ETIT viennent du
  miroir) : jamais retenus.
- Chiffre corrigé après coup : quand la colonne « exercice précédent » des comptes suivants (ou un rapport annuel publié plus
  tard) donne, vérifié par ses identités, un montant différent de celui des comptes de l'exercice, et que la base de recoupement
  (base tierce, archives SikaFinance) le reprend, c'est ce montant corrigé qui est retenu — avec les autres membres de ses
  identités pris dans le même document, jamais un mélange des deux versions (Unilever CI 2021 : résultat retraité ≈ 0 et non
  6 091 ; NSIA Banque 2017 : 10 015 pro forma). Un montant isolé égal à celui d'une autre année dans les autres sources
  (colonne décalée d'un communiqué numérisé) est retiré.
- Documents numérisés : les égalités exactes (actif = passif, résultat du compte de résultat = résultat au bilan) doivent l'être
  au-delà de l'arrondi — un chiffre changé au milieu d'un total n'est pas une vérification ; une référence SYSCOHADA seule devant
  de petits nombres est un débris de lecture ; un libellé encombré de débris (« li (total ressources stables pa ») est relu
  nettoyé ; un point lu à la place d'une espace de milliers (« 301 493.038 967 ») et une suite de montants aux groupes mal
  découpés (« 22372337 396 32 374 022 046 ») sont remis en forme ; une date collée (« 31122004 ») vaut en-tête de colonne.
  Le total du passif circulant illisible est la somme de ses postes (DH à DN) si le passif se vérifie alors. Dans un
  communiqué ou un rapport numérisé, deux lectures identiques d'un chiffre ne suffisent pas : seuls les montants vérifiés par
  une identité sont gardés. Un poste du bilan plus grand que le total du bilan est écarté.
- Colonnes sans en-tête lisible (scan) : leur ordre est supposé (N puis N-1) et doit être confirmé par une autre source ; si les
  autres sources donnent ces montants pour l'exercice voisin, les colonnes étaient permutées et les deux exercices sont réattribués
  (BOA Niger 2018-2020). L'ordre de grandeur d'une société se mesure sur les documents encore crus (deux rapports en milliers
  ne font plus passer les bons documents pour des erreurs) ; une lecture numérisée vérifiée par une seule identité, dix fois
  plus petite que l'exercice voisin, est écartée (chiffre de tête perdu : Ecobank CI 2016).
- Tableau des flux : l'identité « variation de trésorerie = flux opérationnels + investissement + financement » vérifie les
  flux lus ; quand elle est fausse (signe perdu, ligne manquante), les flux du document sont écartés sans toucher au bilan ni au
  compte de résultat. Deux tableaux côte à côte sous un même en-tête à quatre colonnes (N, N-1 | N, N-1) : un libellé de
  gauche n'a que les deux premiers montants.
- Couches texte sans table de caractères : chiffres codés (glyphes grecs ou codes de contrôle), lettres décalées de 29
  (« 7$ 9HQWHV GH PDUFKDQGLVHV » = « TA Ventes de marchandises ») décodés segment par segment ; mots coupés (« T OTAL »,
  « RESULT AT ») recollés ; convention des virgules (milliers à l'anglaise ou décimale) décidée à la majorité des montants. Un
  document dont la couche texte ne donne rien de vérifiable est relu par reconnaissance de caractères.
- Plusieurs lectures d'un même document (texte, reconnaissance de caractères française / anglaise, deux modes) : la lecture
  retenue est la mieux vérifiée (exercices, identités fortes, postes vérifiés), et, à qualité égale, celle dont les montants
  sont plausibles dans l'unité annoncée. Les postes qu'une autre lecture vérifie par une identité, ou que deux reconnaissances
  lisent à l'identique, la complètent (même norme, même unité, au moins un montant commun identique) ; rien n'est remplacé.
  Un exercice vérifié dans une seule lecture est repris d'elle. Un montant vérifié par une identité mais lu autrement par une
  autre reconnaissance (un chiffre confondu, à moins d'un centième près) est contesté et n'est pas repris.
- Égalités exactes pour les documents numérisés, sur toutes les identités : un écart au-delà de l'arrondi des montants publiés
  (une unité en francs, ou l'unité des comptes publiés en milliers ou millions) n'est pas une vérification (Setao 2014 :
  résultat 2 112 605 831 et non …834 ; Uniwax 2024 : −2 188 937 902).
- Aucun montant en FCFA n'atteint 14 chiffres : une suite plus longue est découpée selon les groupes de milliers (chiffre
  parasite en tête ou en queue d'un groupe : « 2341 » = 234 | 1), sinon la case est illisible et le libellé n'attend pas ses
  montants plus bas. Deux montants de même longueur collés par une seule espace (« 95725 99149 ») restent deux montants.
- Signes : un montant entre parenthèses garde son signe négatif même quand la reconnaissance a perdu une parenthèse ailleurs
  (« (4 248 984 403) ») ; la colonne des signes (« - ») ne s'applique qu'aux montants imprimés sans signe (pas de double
  négation : impôt « - -1 037 ») ; un tilde devant un nombre est un signe moins mal lu.
- Unités : une annonce (« en millions FCFA ») pré-imprimée sur un bilan bancaire en francs est corrigée quand aucun total n'est
  plausible dans l'unité annoncée ; une annonce isolée à gauche d'une nouvelle page vaut pour les deux tableaux ; une lettre
  parasite devant « en millions » (« fen millions ») n'empêche pas la lecture ; une virgule ambiguë (« 63,615 » : milliers
  ou décimale) est lue des deux façons et la lecture la mieux vérifiée dans l'unité annoncée l'emporte (SOGB 2008-2009).
- Structure des états : un passif qui enchaîne sous le total de l'actif sans titre (« Capital social ») est reconnu, et cette
  décision est révoquée si des postes de l'actif suivent ; le titre « TABLEAU DE FLUX DE TRESORERIE (TFT) » face aux montants
  de l'autre tableau ouvre bien le tableau des flux ; le résultat du projet d'affectation n'est pas un résultat d'exercice ;
  une colonne de notes devant deux exercices (« 21 (402) (391) ») n'est retirée que si la ligne ne forme pas N, N-1 et leur
  variation ; une année de clôture impossible (« 2076 ») est ignorée.
- Consolidation : le résultat inscrit au passif vaut résultat net quand le document n'a pas de compte de résultat ; un montant
  hors de proportion avec le bilan de son propre document (cinq fois le total) porte seul l'erreur d'unité et ne discrédite
  pas la source qui le donne mille fois plus petit ; un découpage de postes entièrement tiré d'un même document est gardé tel
  quel ; sans total ni chiffre d'affaires, l'unité n'est retenue que si un chiffre clé coïncide avec une autre source.

## instantanes/ — copie permanente des données prises à l'extérieur

Base tierce (dossier `brvm_src/` : registre des titres, chiffres clés, avis, dividendes, cours), archives SikaFinance
(`sika_hist.json`) et fiches des sociétés (`profiles.json`), copiées chaque soir depuis la branche `raw`. Rien n'en disparaît :
ce que la source n'a plus est gardé, une valeur nouvelle ou corrigée l'emporte (`scripts/sticky.py`). Chaque version reste
dans l'historique de cette branche.
