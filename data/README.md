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
  - Alimente l'intent `info_pharmacie` du NLU (voir `nlu/schema.json`, entité `PHARMACIE`/`LOCALISATION`).
- `pharmacies_report.txt` — statistiques de nettoyage (doublons supprimés, répartition par type/ville).

## Limites connues
- Le rapprochement CNOPS/AMMPS est fait sur correspondance exacte de texte normalisé (nom+dosage+forme) : pas de fuzzy matching, donc des variantes d'écriture (pluriel, ponctuation) ne matchent pas toujours — acceptable pour un premier jeu de données propre, à améliorer si besoin (ex. rapprochement par DCI + dosage, ou similarité de chaînes).
- CNOPS date de 2014 : des produits retirés du marché depuis, ou de nouveaux produits absents.
- CNSS : intégrée. Limites propres — le code `A`/`N`/`C`/`B` de la colonne « Princeps / Générique » reste de signification inconnue (voir plus haut) ; `prix_base_remboursement_cnss` est volontairement absent de la table unifiée quand il varie selon la présentation ; le rapprochement avec les deux autres sources utilise la même clé exacte, donc il hérite des mêmes limites de correspondance.
- CNOPS et CNSS sont deux régimes distincts avec leurs propres taux : un produit peut être remboursé par l'un et pas par l'autre. Les deux colonnes sont donc conservées séparément et jamais fusionnées en un taux unique, et l'API nomme le régime dans sa réponse.
- La fusion AMMPS↔CNOPS produit des lignes en trop (produit cartésien sur 219 clés dupliquées des deux côtés) : certaines « variantes » d'un même produit dans la table unifiée sont des artefacts de jointure, pas de vraies présentations. Défaut préexistant, non corrigé ici pour ne pas modifier les chiffres de la fusion historique — à traiter séparément.
- Pharmacies : source non officielle (voir ci-dessus), coordonnées GPS non fiables dans la réponse de l'API (elle renvoie le point d'origine de la requête, pas la position réelle de l'établissement) — seules les données texte (nom/téléphone/adresse/ville) sont exploitées ici. Pas de couverture garantie à 100% du territoire (dépend de la base saydalia elle-même).
