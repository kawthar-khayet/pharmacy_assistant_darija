# Données de référence — Challenge #1

## Sources médicaments
- **CNOPS** (`ref-des-medicaments-cnops-2014.xlsx`, racine du projet) — liste officielle 2014, 5917 médicaments, avec prix (PPV/PH/PRIX_BR) et taux de remboursement CNOPS.
- **AMMPS** (`data/raw/ammps_medicaments.csv`) — Liste Marocaine des Médicaments, scrapée depuis `ammps.gov.ma` (registre national officiel, données courantes), 9903 médicaments après nettoyage. Champs plus riches : DCI, classe thérapeutique, laboratoire, statut AMM/commercialisation, PPV/PH/PFHT/TVA.
- **DMP** : absorbée par AMMPS (ex-Direction du Médicament et de la Pharmacie), pas de source distincte.
- **CNSS** : liste consultée en ligne (Next.js, données chargées dynamiquement côté client, pas de fichier téléchargeable ni d'API publique trouvée) — non intégrée pour l'instant.

## Source pharmacies (adresse/téléphone/ville)
- **Saydalia** (`data/raw/saydalia_pharmacies.csv`) — 2661 établissements scrapés via l'endpoint interne du widget carte de saydalia.ma (`/api/siteweb_api.php`, découvert en lisant leur JS public, pas une API documentée pour usage tiers). Récupéré via une grille de ~70 points (villes + quartiers des grandes agglomérations), dédupliqué par id. **Usage interne/prototype uniquement** — ce n'est pas un jeu de données ouvert, à ne pas redistribuer commercialement.
- Alternative "officielle" (`ammps.gov.ma/basesdedonnes/pharmacies`) testée mais **indisponible (404)** au moment du scraping.

## Pipeline
1. `scripts/scrape_ammps.py` — scrape les 496 pages de la base AMMPS (nom, dosage, forme, DCI, classe thérapeutique, labo, statut, prix) → `data/raw/ammps_medicaments.csv`.
2. `scripts/clean_merge.py` — nettoie les deux sources médicaments (normalisation texte/accents, parsing des prix, taux de remboursement) et les fusionne sur une clé (nom + dosage + forme normalisés) → `data/clean/`.
3. `scripts/scrape_saydalia.py` — interroge l'API interne de saydalia.ma sur une grille de villes/quartiers, dédup par id → `data/raw/saydalia_pharmacies.csv`.
4. `scripts/clean_pharmacies.py` — nettoie et classe (pharmacie / parapharmacie / laboratoire / autre), déduplique → `data/clean/pharmacies_reference.csv`.

## Fichiers de sortie (`data/clean/`)
- `medicaments_ammps.csv` — AMMPS nettoyé (9903 lignes).
- `medicaments_cnops.csv` — CNOPS nettoyé (5917 lignes).
- `medicaments_reference.csv` — **table de référence unifiée** (15441 lignes) à utiliser pour le matching d'entités du chatbot :
  - `nom`, `dci`, `dosage`, `forme`, `presentation`, `laboratoire`, `classe_therapeutique`
  - `type_produit` (PRINCEPS/GENERIQUE/VACCIN...)
  - `statut_commercialisation`, `statut_amm`
  - `ppv`, `ph`, `pfht`, `tva` (prix, quand disponibles)
  - `code_cnops`, `prix_base_remboursement_cnops`, `taux_remboursement_cnops` (uniquement si le produit existe aussi côté CNOPS)
  - `source` : `ammps`, `cnops`, ou `ammps+cnops`

  ⚠️ `code_cnops` (code-barres 13 chiffres) doit être relu en `dtype=str` pour éviter que pandas ne le convertisse en notation scientifique.

- `merge_report.txt` — statistiques de fusion (taux de correspondance CNOPS↔AMMPS : ~41%, attendu vu l'écart de 10 ans entre les deux sources et les présentations/emballages différents).

- `pharmacies_reference.csv` — **2652 pharmacies/parapharmacies** nettoyées :
  - `id`, `nom`, `type_etablissement` (pharmacie / parapharmacie / laboratoire / autre_point_de_vente), `telephone`, `adresse`, `ville`, `garde` (horaires si établissement de garde, sinon vide)
  - Alimente l'intent `info_pharmacie` du NLU (voir `nlu/schema.json`, entité `PHARMACIE`/`LOCALISATION`).
- `pharmacies_report.txt` — statistiques de nettoyage (doublons supprimés, répartition par type/ville).

## Limites connues
- Le rapprochement CNOPS/AMMPS est fait sur correspondance exacte de texte normalisé (nom+dosage+forme) : pas de fuzzy matching, donc des variantes d'écriture (pluriel, ponctuation) ne matchent pas toujours — acceptable pour un premier jeu de données propre, à améliorer si besoin (ex. rapprochement par DCI + dosage, ou similarité de chaînes).
- CNOPS date de 2014 : des produits retirés du marché depuis, ou de nouveaux produits absents.
- CNSS non intégrée (pas de source exploitable trouvée sans navigateur automatisé/API privée).
- Pharmacies : source non officielle (voir ci-dessus), coordonnées GPS non fiables dans la réponse de l'API (elle renvoie le point d'origine de la requête, pas la position réelle de l'établissement) — seules les données texte (nom/téléphone/adresse/ville) sont exploitées ici. Pas de couverture garantie à 100% du territoire (dépend de la base saydalia elle-même).
