# États financiers hors brvm.org : sites officiels des sociétés (22/10/2026)

Session du 22/10/2026 (accès à `noodleloop` seulement, lecture seule sur les données ; le coffre n'était pas joignable).
Demande du propriétaire : revoir un par un les exercices écartés, chercher sur les sites officiels des sociétés (ou de
leur groupe) les états financiers des exercices absents de brvm.org, et vérifier la concordance avec nos chiffres publiés.
Règle rappelée par le propriétaire : « aucun chiffre faux » ; rien n'est pris au détriment de la lecture ni des contrôles.

## 1. Ce qui a été fait

- Un agent de recherche (un seul, en parallèle) a cherché sur les sites officiels : 13 sociétés avec documents, 39 entrées
  titre × exercice dans `docs/sites_officiels_2026-10-22.json` (URL, titre, périmètre, unité, page, lignes recopiées,
  montants en millions, notre valeur, écart). **Ses lectures passent par un résumé automatique : à revérifier sur le texte
  des documents avant tout usage.**
- Les 25 documents ont été téléchargés par la sonde (`probe_urls.txt`, passage « Sonde des sources » du 22/10 08:55 UTC) :
  PDF et texte `pdftotext -layout` sur la branche `probe`, dossier `urls/` (`<nom>.pdf`, `<nom>.pdf.txt`, `_status.txt`).
  Un seul échec : `SIB_RA_2014.pdf` (entreprises.sib.ci, code 000 : site injoignable depuis GitHub).
  Même liste que le fichier JSON ; `brvm.org/sitemap.xml` n'existe pas (404) ; `robots.txt` et la page
  « financial-reports-boa-mali » (liste des PDF BOA Mali 1999-2024) sont aussi dans `urls/`.

## 2. Vérifié sur le texte des documents (par la session, pas par l'agent)

- **NSIA Banque (NSBC), produit net bancaire 2016 et 2017 : nos chiffres (base tierce) sont contredits par les documents
  officiels.** États financiers certifiés 2017 publiés à la BRVM (`20180430_-_etats_financiers_annuels_2017-nsia_banque_ci.pdf`,
  compte de résultat en millions, identité TOTAL = TOTAL 86 162 / 151 123 vérifiée) : total des produits d'exploitation
  bancaire − total des charges d'exploitation bancaire = **84 760 − 26 069 = 58 691 (2016)** et **149 054 − 85 478 = 63 576
  (2017)**. Confirmé par le rapport annuel 2016 (tableau « composantes du PNB », p. 15 : 58 691) et par le rapport d'activité
  2017 déposé à la BRVM (tableau des chiffres clés : « Produit Net Bancaire 63 576 / 58 691 »). Nos séries : 59 439 (2016) et
  62 672 (2017), venues de la base tierce. Le lecteur ne lit pas « b_pnb » dans ce document (le PNB n'est pas imprimé en
  ligne) et un montant calculé ne comble qu'un exercice vide : la valeur fausse de la base reste. À corriger dans le coffre
  (`seed/corrections_bnpa.json`, lignes « cpt ») ; généraliser : pour une banque, PNB = total produits − total charges
  d'exploitation bancaire quand les deux totaux sont vérifiés par l'identité du compte de résultat, et ce montant vérifié
  doit pouvoir remplacer la base tierce (règle « BRVM source principale »). Le rapport annuel 2016 imprime aussi 58 656
  (tableaux de résultats, p. 27) : écart de 35 interne au rapport, sans effet sur la conclusion.
- **Coris Bank BF (CBIBF), PNB 2018** : rapport annuel 2018 (burkina.coris.bank, compte d'exploitation, en millions) :
  **56 705** (2017 : 45 269 ; 2016 : 33 569) ; notre 2018 : 57 545 (base tierce, +1,5 %). Aucun état financier 2018 ni 2019
  de Coris dans notre registre (brvm.org) : seul document officiel pour 2018. À trancher dans le coffre.
- Agent : toutes les autres valeurs déjà présentes concordent à moins de 0,5 % (BOAM 2015, BOAN 2014-2015, ORGT 2015-2016,
  NSBC 2014-2016 hors PNB, CBIBF 2016-2018 hors PNB, TTLS 2014-2015, UNLC 2015-2016, SCRC 2015-2016, SMBC 2016, BBGC
  2021-2025). Non revérifié ligne à ligne par la session.

## 3. Documents présents sur brvm.org mais absents de notre registre (trouvés par recherche web)

À ajouter à `seed/archives_comptes.json` (sans champ « wb » : téléchargement direct, lecture et contrôles habituels au
passage `comptes.yml` suivant) :

```
{"ticker": "SHEC", "document_url": "https://www.brvm.org/sites/default/files/20130712_-_efa_-_vivo_energy_ci_-_exercice_2012.pdf", "category": "financial_statements", "title": "Vivo Energy CI : États financiers approuvés exercice 2012", "fiscal_year": 2012, "published_at": "2013-07-12"}
{"ticker": "SHEC", "document_url": "https://www.brvm.org/sites/default/files/20150526_-_efp_-_vivo_energy_ci_-_exercice_2014.pdf", "category": "financial_statements", "title": "Vivo Energy CI : États financiers provisoires exercice 2014", "fiscal_year": 2014, "published_at": "2015-05-26"}
{"ticker": "TTLS", "document_url": "https://www.brvm.org/sites/default/files/20160616_-_ra_-_total_sn_-_exercice_2015.pdf", "category": "annual_report", "title": "Total Sénégal : Rapport annuel exercice 2015", "fiscal_year": 2015, "published_at": "2016-06-16"}
{"ticker": "SMBC", "document_url": "https://www.brvm.org/sites/default/files/20170419-etas_financiers_provisoires_exercice_2016_-_smb_ci.pdf", "category": "financial_statements", "title": "SMB CI : États financiers provisoires exercice 2016", "fiscal_year": 2016, "published_at": "2017-04-19"}
```

Leçon : la liste des publications (liste tierce + pages « rapports des sociétés cotées ») ne couvre pas tous les PDF de
brvm.org ; une recherche web « site:brvm.org/sites/default/files <société> » par société retrouverait les autres (à faire
une fois, 48 sociétés).

## 4. Exercices avec document lu mais absents de FA : causes trouvées (consolidation rejouée en local)

47 exercices depuis 2000 ont un document lu « ok » et n'apparaissent ni dans les comptes principaux ni dans le second
référentiel de FA. 23 sont sans unité déterminable (anciens rapports annuels 2000-2005, 2 à 4 postes lus) ; 11 sont NEI-CEDA
2000-2010 (avant le premier exercice suivi, voulu) ; 3 Sonatel 2016-2018 (présentations, exclues par règle) ; CFAC 2002 et
2004 (états « SARI », autre entité) ; ETIT 2005 (dollars). Restent 7 cas à regarder sur le document :

- **BOA Niger 2016 et 2017** (`boa-niger_etats_financiers.pdf`, scan, en-tête des colonnes illisible, sens supposé) : colonne 1
  = 2016 (résultat 6 600 103 120 = notre 6 600 M, capital 10 000 M), colonne 2 : résultat 7 284 344 207, capital 13 000 M.
  Le rapport annuel 2018 (certifié) donne 2017 = 6 891 052 103 : la colonne 2 est donc **des comptes provisoires 2017** (ou
  un autre jeu), à ne pas reprendre. Récupérable pour **2016** après lecture de l'image : total du bilan 286 739 148 630,
  fonds propres (capital 10 000 + primes 3 194,5 + réserves 7 804,5 + résultat 6 600,1 ; FRBG 1 811,8 à part). Le rapport
  annuel 2018 lit les montants avec six zéros de trop (`2.06e16` pour un PNB de 20 630 M) : colonnes fusionnées par la
  reconnaissance de caractères ; l'unité reste donc indéterminée et 2017 n'est pas repris (total bilan et fonds propres
  2017 perdus). Les états financiers 2016 et 2017 de BOA Niger existent sans doute sur bank-of-africa.net (page des
  rapports de la filiale, comme BOA Mali) : à sonder.
- **SIB 2016** (`etats_financiers_sib_ci_2017_0.pdf`, scan anglais) : total actif « 2017 » 906 911 M et « 2016 » 995 509 M,
  résultat « 2016 » 22 M : colonnes et montants mal lus (base : total 2017 = 989 868, résultat 2016 = 17 091). Écarté à raison.
  Aucune valeur récupérable sans relecture de l'image.
- **Erium (SIVC) 2023** (`20251205_-_rapport_des_cacs_sur_les_etats_financiers_au_ca_…`, 62 postes lus, colonnes 2024 / 2023) :
  document discrédité par la consolidation (jeu d'états dont une partie est fausse : unité, années ou ordre de grandeur).
  Cause exacte à établir en relisant le texte (`txt/` de la branche comptes) ; 2023 reste sans comptes détaillés.
- **ETI 2016** (`etats_financiers_2017_ecobank_ci.pdf`, 3 postes, rattaché à ETIT) : document d'Ecobank CI pris pour ETI ;
  discrédité, sans conséquence (ETI publie en dollars, comptes consolidés).
- **BOA Bénin 2014** (rapport annuel 2014, 2 postes, sans unité) ; **SETAO 2006** (rapport annuel, total du bilan seul,
  439,6 M, sans autre source) ; **Palm CI 2000** (rapport annuel 2001, 36 postes, unité connue mais exercice sans aucun
  recoupement) : faible valeur, à laisser.

## 5. Reste à faire (session avec le coffre)

1. Décider NSBC PNB 2016-2017 et CBIBF PNB 2018 (point 2) ; règle PNB = produits − charges d'exploitation bancaire vérifiés.
2. Ajouter les 4 documents brvm.org (point 3) ; recherche web par société des autres PDF de brvm.org hors registre.
3. Lire les 25 documents officiels (branche `probe`, `urls/*.pdf.txt`) : exercices manquants BOABF 2012-2016, BOAM 2012-2015,
   BOAN 2015, ORGT 2012-2016, NSBC 2012-2016, CBIBF 2012-2018, SHEC 2012-2014, TTLS 2014-2015, UNLC 2016, SMBC 2015, BBGC
   2021-2025 (note d'information, milliards arrondis : chiffres clés seulement). Deux voies : (a) manuelle, lignes « cpt »
   avec « ajout » dans `seed/corrections_bnpa.json`, montants imprimés confirmés par une identité ou un second document ;
   (b) lecture par le pipeline : autoriser dans `cpt_cands` une liste blanche de domaines officiels et un fichier
   `seed/documents_officiels.json`, lus et contrôlés comme ceux de brvm.org (préférable : identités vérifiées, 0 montant
   recopié à la main). La décision du 20/10 « seules les publications de brvm.org alimentent les comptes » est levée par
   la demande du propriétaire du 22/10 (sites officiels des sociétés), à noter dans la passation du coffre.
4. Introuvables en ligne (agent) : BBGC 2012-2020, BICB 2012-2022, LNBB 2012-2022, ORAC 2012-2020, ECOC 2012-2016, SCRC
   2012-2014, TTLS 2012-2013, UNLC 2014 / 2017-2018 / 2024-2025. Piste : recueils BCEAO « Bilans et comptes de résultat des
   banques et établissements financiers de l'UMOA » (bceao.int, 2011-2018 et après : BIBE/BIIC, Bridge Bank, NSIA, Ecobank
   CI, SIB, Coris, BOA), gros PDF à sonder puis à lire page par page. Non cherchés faute de budget : SEMC 2024-2025, SICC
   2025, SIVC 2021-2022, NEIC 2015, SAFC 2015.
5. Toujours à revoir sur les documents (listes à régénérer, elles n'étaient pas dans le dépôt) : 45 montants complétés entre
   deux lectures d'un même scan ; ruptures BOA Sénégal 2014, SMB CI 2019, Solibra 2022, SICABLE 2021, BOA Bénin 2006,
   Onatel 2011, SITAB 2003 ; valeurs extrêmes BNBC, BOAN, SDSC, UNLC (PER), SDSC, SIVC (distribution) ; SUCRIVOIRE 2019
   (total du bilan absent) ; UNLC 2016 : le document `20170616-etats_financiers_exercice_2016-_unilever_ci.pdf` est lu « ok »
   mais ne donne que la colonne 2015 (unité non écrite, montants en francs) : voir pourquoi la colonne 2016 est perdue.
