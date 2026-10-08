# Données de référence — Challenge #1

## Sources médicaments
- **CNOPS** (`ref-des-medicaments-cnops-2014.xlsx`, racine du projet) — liste officielle 2014, 5917 médicaments, avec prix (PPV/PH/PRIX_BR) et taux de remboursement CNOPS.
- **AMMPS** (`data/raw/ammps_medicaments.csv`) — Liste Marocaine des Médicaments, scrapée depuis `ammps.gov.ma` (registre national officiel, données courantes), 9903 médicaments après nettoyage. Champs plus riches : DCI, classe thérapeutique, laboratoire, statut AMM/commercialisation, PPV/PH/PFHT/TVA.
- **DMP** : absorbée par AMMPS (ex-Direction du Médicament et de la Pharmacie), pas de source distincte.
- **CNSS** (`data/raw/cnss_medicaments.csv`) — « Liste des médicaments admis au remboursement », 8991 lignes, avec PPV/PH, prix de base de remboursement (PPV-BR) et taux de remboursement CNSS. La page est en Next.js (contenu chargé côté client, donc rien à télécharger directement), mais elle s'appuie sur une **API JSON publique et sans authentification** (`POST https://www.cnss.ma/api/search`, trouvée en inspectant les appels réseau de la page) — c'est elle qu'interroge `scripts/scrape_cnss.py`. Le total annoncé par le site (8991) correspond exactement au nombre de lignes récupérées : l'extraction est complète.

  ⚠️ La colonne source intitulée « Princeps / Générique » contient les codes `A`/`N`/`C`/`B`, et **ces codes n'encodent pas le statut princeps/générique**. Croisés avec les produits que CNSS partage avec les deux autres sources, ils ne montrent aucune relation : le code `A` couvre 1010 produits que CNOPS classe GENERIQUE et 969 qu'il classe PRINCEPS ; AMMPS ne concorde pas mieux. Le site affiche la lettre brute sans légende. La valeur est donc conservée telle quelle sous un nom qui ne prétend rien (`princeps_generique_code`) et n'alimente jamais `type_produit`.

## Source pharmacies (adresse/téléphone/ville)
- **Saydalia** (`data/raw/saydalia_pharmacies.csv`) — 2661 établissements scrapés via l'endpoint interne du widget carte de saydalia.ma (`/api/siteweb_api.php`, découvert en lisant leur JS public, pas une API documentée pour usage tiers). Récupéré via une grille de ~70 points (villes + quartiers des grandes agglomérations), dédupliqué par id. **Usage interne/prototype uniquement** — ce n'est pas un jeu de données ouvert, à ne pas redistribuer commercialement.
- Alternative "officielle" (`ammps.gov.ma/basesdedonnes/pharmacies`) testée mais **indisponible (404)** au moment du scraping.

## Pipeline
1. `scripts/scrape_ammps.py` — scrape les 496 pages de la base AMMPS (nom, dosage, forme, DCI, classe thérapeutique, labo, statut, prix) → `data/raw/ammps_medicaments.csv`.
2. `scripts/scrape_cnss.py` — interroge l'API JSON publique de cnss.ma page par page (500 par requête, délai poli entre les appels) → `data/raw/cnss_medicaments.csv`.
3. `scripts/clean_merge.py` — nettoie les **trois** sources médicaments (normalisation texte/accents, parsing des prix, taux de remboursement) et les fusionne sur une clé (nom + dosage + forme normalisés) → `data/clean/`.

   CNSS est fusionnée **différemment** de CNOPS, volontairement. CNOPS est jointe par un `merge` outer classique, qui multiplie les lignes dès que la même clé est dupliquée des deux côtés (effet réel et préexistant : 219 clés sont dupliquées à la fois dans AMMPS et CNOPS, le merge produit donc leur produit cartésien). Joindre une troisième source de la même façon aurait aggravé cette explosion. CNSS est donc rattachée en deux temps : ses données de remboursement sont repliées sur les lignes existantes via une table d'une ligne par clé (qui ne peut rien multiplier), puis seuls ses produits inédits sont ajoutés. Résultat : la table passe de 15 441 à 19 974 lignes, soit exactement les 4 533 lignes ajoutées, sans aucune ligne parasite.
4. `scripts/scrape_saydalia.py` — interroge l'API interne de saydalia.ma sur une grille de villes/quartiers, dédup par id → `data/raw/saydalia_pharmacies.csv`.
5. `scripts/clean_pharmacies.py` — nettoie et classe (pharmacie / parapharmacie / laboratoire / autre), déduplique → `data/clean/pharmacies_reference.csv`.

## Fichiers de sortie (`data/clean/`)
- `medicaments_ammps.csv` — AMMPS nettoyé (9903 lignes).
- `medicaments_cnops.csv` — CNOPS nettoyé (5917 lignes).
- `medicaments_cnss.csv` — CNSS nettoyé (8978 lignes, une ligne par présentation). C'est ici que reste le détail par présentation : `prix_base_remboursement_cnss` y est complet, alors que la table unifiée ne le reporte que s'il est non ambigu (voir ci-dessous).
- `medicaments_reference.csv` — **table de référence unifiée** (19974 lignes) à utiliser pour le matching d'entités du chatbot :
  - `nom`, `dci`, `dosage`, `forme`, `presentation`, `laboratoire`, `classe_therapeutique`
  - `type_produit` (PRINCEPS/GENERIQUE/VACCIN...)
  - `statut_commercialisation`, `statut_amm`
  - `ppv`, `ph`, `pfht`, `tva` (prix, quand disponibles)
  - `code_cnops`, `prix_base_remboursement_cnops`, `taux_remboursement_cnops` (uniquement si le produit existe aussi côté CNOPS)
  - `code_cnss`, `prix_base_remboursement_cnss`, `taux_remboursement_cnss` (uniquement si le produit existe aussi côté CNSS)
  - `source` : combinaison de `ammps`, `cnops` et `cnss` (ex. `ammps+cnops+cnss`, `cnops+cnss`, `cnss`)

  ⚠️ `code_cnops` et `code_cnss` (codes-barres 13 chiffres) doivent être relus en `dtype=str` pour éviter que pandas ne les convertisse en notation scientifique.

  ⚠️ `prix_base_remboursement_cnss` n'est reporté ici que pour les clés où CNSS donne une valeur unique. Ce montant dépend de la présentation (boîte de 14 / 28 / 56…) et diffère réellement entre présentations d'un même produit pour 1305 clés : en choisir une arbitrairement reviendrait à rattacher un montant à un conditionnement auquel il ne correspond pas. Le détail complet reste dans `medicaments_cnss.csv`. Le taux, lui, est reporté systématiquement (il est déjà unique pour 6523 des 6591 clés ; les 68 clés divergentes prennent le maximum).

- `merge_report.txt` — statistiques de fusion. Taux de correspondance CNOPS↔AMMPS : ~41%, attendu vu l'écart de 10 ans entre les deux sources et les présentations/emballages différents. Côté CNSS : 51,2% de ses clés produit étaient déjà connues (leur remboursement CNSS est venu enrichir la ligne existante), les 3215 restantes ont apporté 4533 nouvelles lignes. Effet net sur la couverture remboursement de la table : 6879 → 12075 lignes documentées (+76%).

- `pharmacies_reference.csv` — **2652 pharmacies/parapharmacies** nettoyées :
  - `id`, `nom`, `type_etablissement` (pharmacie / parapharmacie / laboratoire / autre_point_de_vente), `telephone`, `adresse`, `ville`, `garde` (horaires si établissement de garde, sinon vide)
  - Source de l'annuaire : complétée par OpenStreetMap dans `pharmacies_fusion.csv`, que le bot utilise (voir plus bas).
- `pharmacies_report.txt` — statistiques de nettoyage (doublons supprimés, répartition par type/ville).

## Sources ajoutées (septembre 2026)

Trois jeux de données complètent la base initiale : positions GPS des pharmacies, classification thérapeutique et informations de sécurité.

### Coordonnées GPS des pharmacies
- **OpenStreetMap / Overpass** (`scripts/fetch_osm_pharmacies.py`) — 6947 pharmacies cartographiées au Maroc → `data/raw/osm_pharmacies.csv`. Licence ODbL, attribution requise.
- **Nominatim** (`scripts/geocode_pharmacies.py`) — géocodage des adresses restantes, 1 requête/seconde comme l'impose la politique d'usage du service.

Quatre colonnes ajoutées à `pharmacies_reference.csv` : `latitude`, `longitude`, `precision_gps`, `source_gps`.

| `precision_gps` | Pharmacies | Signification |
|---|---|---|
| `exacte` | 1278 | position de l'officine |
| `rue` | 108 | la voie, pas le numéro |
| `quartier` | 44 | le quartier seulement |
| `ville` | 1197 | centre-ville, faute de mieux |
| (vide) | 25 | rien de trouvé |

⚠️ **Seule la précision `exacte` désigne l'officine.** Afficher une épingle pour une position `ville` enverrait un patient au mauvais endroit — l'interface ne doit s'en servir que pour cadrer un plan. `source_gps` dit quelle recherche a produit la position (`osm`, `nominatim_nom`, `nominatim_voie`, `nominatim_quartier`, `centre_ville`).

Le rapprochement OSM exige un nom ressemblant à moins de 25 km du centre de la ville, et un écart d'au moins 6 points avec le deuxième candidat : sans cette marge, deux homonymes étaient départagés au hasard. Tout résultat au-delà de ce rayon est rejeté. Une recherche par quartier ne peut jamais produire une précision `exacte`, même quand Nominatim répond par un bâtiment.

### Classification ATC — `dci_atc.csv`
- **RxNav / RxClass** (NIH, API publique sans clé), `scripts/fetch_atc.py` → 2208 DCI sur 2731 classées (80,8 %), 549 codes ATC distincts.
- Colonnes : `dci`, `principe_actif`, `rxcui`, `code_atc`, `groupe_atc`, `libelle_atc`.

⚠️ Plusieurs codes ATC par molécule est la règle : l'ibuprofène est M01AE par voie orale et M02AA en gel. RxNav rattache aussi une molécule aux classes d'**associations** qui la contiennent (l'amoxicilline seule apparaît sous « associations pour éradiquer Helicobacter pylori ») sans dire laquelle est la sienne. Aucune n'est donc élue : pour le code officiel d'une molécule, utiliser `code_atc_notice` de `securite_medicaments.csv`.

Les 523 DCI sans code n'ont pas d'ATC : allergènes, produits de contraste, excipients, solutés de dialyse. Les libellés sont en anglais.

### Informations de sécurité — `securite_medicaments.csv`
- **BDPM** (ANSM, Licence Ouverte), `scripts/fetch_securite_bdpm.py` → 221 molécules sur les 300 les plus répandues au Maroc.
- Fichiers plats `CIS_bdpm.txt` et `CIS_COMPO_bdpm.txt` pour la composition ; notices HTML mises en cache dans `data/raw/bdpm_notices/`, une par seconde.
- Colonnes : `dci`, `principes_actifs`, `nb_produits_maroc`, `cis_bdpm`, `specialite_bdpm`, `code_atc_notice`, `indications`, `contre_indications`, `precautions`, `interactions`, `grossesse_allaitement`, `effets_indesirables`, `source_url`, `date_recuperation`.

| Rubrique | Molécules |
|---|---|
| **indications** (à quoi sert le médicament) | **218** |
| précautions | 217 |
| effets indésirables | 213 |
| grossesse et allaitement | 207 |
| interactions | 205 |
| contre-indications | 193 |
| `code_atc_notice` | 193 |

La rubrique `indications` vient du titre 1 de la notice (« QU'EST-CE QUE X ET DANS QUELS CAS EST-IL UTILISÉ ? »). Elle répond à « chno kaydir had dwa ? », que la base marocaine ne documente pas. La ligne d'en-tête « Classe pharmacothérapeutique — code ATC » en est retirée : elle est reprise à part dans `code_atc_notice`, et elle ouvrirait l'explication sur du jargon.

Pourquoi la BDPM et non openFDA ou DailyMed : les spécialités marocaines viennent de la même filière que les françaises (Doliprane, Spasfon, Augmentin y figurent sous le même nom) et les notices sont déjà en français — aucune traduction, donc aucun risque de déformer une contre-indication.

⚠️ La spécialité de référence doit avoir une composition **strictement identique** à la DCI marocaine. Sans cette égalité, le paracétamol tombait sur ACTRON (paracétamol + aspirine + caféine) et l'amoxicilline sur Augmentin : on aurait affiché les contre-indications de l'aspirine sous une boîte de Doliprane.

⚠️ Le texte décrit la **molécule**, pas la spécialité marocaine : conditionnement, dosage et titulaire peuvent différer. Il est conservé mot pour mot, avec son URL source et sa date de récupération.

#### Résumés en darija — `securite_resumes.json`

`scripts/precalculer_resumes.py` fait produire par le LLM un résumé de trois phrases par molécule et par langue, à partir du **seul** texte officiel. Il sert de porte d'entrée pour un patient qui ne lit pas le français médical ; le texte intégral reste affiché en dessous, et l'interface indique que le résumé est automatique.

Garde-fous, parce qu'une contre-indication reformulée est une erreur de santé et non une maladresse de style :

- le prompt interdit d'ajouter quoi que ce soit, de donner une dose ou un conseil, et autorise le modèle à répondre `RIEN` ;
- il impose de nommer les organes comme le texte les nomme — un premier essai avait écrit « estomac » là où la notice disait « foie » ;
- une réponse dont `finishReason` n'est pas `STOP` est jetée : coupée en plein milieu, une contre-indication peut dire l'inverse de la notice ;
- `thinkingBudget: 0` — sans cela, le modèle dépensait son budget de sortie en raisonnement interne (341 jetons de « pensées » pour 18 de réponse) et l'un des premiers résumés contenait ce raisonnement (« Confidence Score: 1. Simple French? Yes. »).

Les résumés sont mis en cache : une molécule a un texte stable, et le palier gratuit limite les appels par minute.

Les 79 molécules absentes se répartissent en 53 sans équivalent français exact (insuline humaine, concentré pour hémodialyse, produits de diagnostic) et 26 dont la notice n'expose aucune rubrique reconnaissable.

## Données du bot (octobre 2026)

Le moteur `nlp/` lit ces fichiers, préparés une fois par les scripts de `nlp/preparation/` :

- `pharmacies_fusion.csv` — **toutes les pharmacies du Maroc** : OpenStreetMap (commune par commune, position exacte) complété par l'annuaire (adresse, téléphone, garde). Une pharmacie de l'annuaire est fusionnée avec OSM si elle est à moins de 300 m avec un nom ressemblant, ou seule de ce nom dans la même ville ; sinon elle est ajoutée telle quelle. Les pharmacies OSM sans nom sont écartées ; le bot écarte aussi, au chargement, les parapharmacies et drogueries qu'OSM classe en « pharmacy ». Script : `py -m nlp.preparation.pharmacies_fusion` ; rapport et 30 exemples de fusion à relire dans `pharmacies_fusion_report.txt`. Licence ODbL (OSM).
- `quartiers.csv` — 1 854 quartiers OSM géolocalisés, avec leurs noms latins et arabes. Le bot y cherche le quartier cité, puis, à défaut, dans les adresses de l'annuaire (beaucoup de quartiers manquent dans OSM). Script : `py -m nlp.preparation.quartiers`.
- `conseil_symptomes.csv` — liste blanche du conseil pour un symptôme bénin : symptôme, molécule (correspondance exacte de la DCI), durée maximale sans avis médical, signes d'alerte, professionnel vers qui orienter. ⚠️ **À faire relire par un pharmacien.**
- `securite_medicaments.csv` et `securite_resumes.json` — la notice et ses résumés (voir plus haut).

## Limites connues
- Le rapprochement CNOPS/AMMPS est fait sur correspondance exacte de texte normalisé (nom+dosage+forme) : pas de fuzzy matching, donc des variantes d'écriture (pluriel, ponctuation) ne matchent pas toujours — acceptable pour un premier jeu de données propre, à améliorer si besoin (ex. rapprochement par DCI + dosage, ou similarité de chaînes).
- CNOPS date de 2014 : des produits retirés du marché depuis, ou de nouveaux produits absents.
- CNSS : intégrée. Limites propres — le code `A`/`N`/`C`/`B` de la colonne « Princeps / Générique » reste de signification inconnue (voir plus haut) ; `prix_base_remboursement_cnss` est volontairement absent de la table unifiée quand il varie selon la présentation ; le rapprochement avec les deux autres sources utilise la même clé exacte, donc il hérite des mêmes limites de correspondance.
- CNOPS et CNSS sont deux régimes distincts avec leurs propres taux : un produit peut être remboursé par l'un et pas par l'autre. Les deux colonnes sont donc conservées séparément et jamais fusionnées en un taux unique, et l'API nomme le régime dans sa réponse.
- La fusion AMMPS↔CNOPS produit des lignes en trop (produit cartésien sur 219 clés dupliquées des deux côtés) : certaines « variantes » d'un même produit dans la table unifiée sont des artefacts de jointure, pas de vraies présentations. Défaut préexistant, non corrigé ici pour ne pas modifier les chiffres de la fusion historique — à traiter séparément.
- Pharmacies : source non officielle (voir ci-dessus), coordonnées GPS non fiables dans la réponse de l'API (elle renvoie le point d'origine de la requête, pas la position réelle de l'établissement) — seules les données texte (nom/téléphone/adresse/ville) sont exploitées ici. Pas de couverture garantie à 100% du territoire (dépend de la base saydalia elle-même).
