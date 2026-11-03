# Données — Challenge #2 (reconnaissance de boîte)

`data/vision/` n'est pas suivi par git (voir `.gitignore`) : tout ici est régénérable.

## Pourquoi pas un vrai dataset téléchargé

Vérifié avant d'écrire le générateur : il n'existe **aucune source légale de photos de boîtes marocaines** à télécharger ou scraper.

- La vente de médicaments en ligne est **interdite au Maroc** (loi 17-04, article 30) — le ministère de la Santé a averti début 2025 que ces sites opèrent hors cadre légal. Pas de site de pharmacie en ligne marocain à scraper pour des photos de boîtes.
- La BDPM française (ANSM), qui documente des spécialités identiques (Doliprane, Spasfon…), ne publie pas de photos d'emballage téléchargeables — seulement des textes (notice, RCP).
- Les datasets publics existants (Roboflow Universe : *MediTrace Packaging*, *Medicine Box Segmentation*… ; Kaggle : ~372 emballages pharmaceutiques internationaux) portent sur des **marques internationales sans correspondance avec `data/clean/medicaments_reference.csv`**, et sont annotés pour la *détection* de boîte (bounding box), pas pour l'OCR. Inutilisables pour mesurer une accuracy de reconnaissance sur notre base.

## `synthetique/` — généré

`py scripts/generer_boites_synthetiques.py --n 300 --seed 42`

Mockups rendus (Pillow) à partir d'une ligne de `data/clean/medicaments_reference.csv` (nom, dosage, forme, DCI, laboratoire), puis dégradés (rotation légère, flou gaussien, luminosité/contraste, recadrage partiel, compression JPEG) pour imiter les conditions citées par l'énoncé du Challenge #2.

- `images/*.jpg` — les boîtes synthétiques.
- `manifest.csv` — vérité terrain : `fichier, nom, dci, dosage, forme, laboratoire`.
- `evaluation.csv` — généré par `py scripts/evaluer_reconnaissance.py` : prédiction, score, confiance et temps par image.

⚠️ **Limite assumée** : un mockup rendu au clavier n'a ni le graphisme, ni les logos, ni le texte arabe d'une vraie boîte (seul le texte latin du CSV est rendu). Il mesure la **robustesse du pipeline** (OCR + fuzzy matching) au bruit visuel, pas la reconnaissance visuelle d'une vraie photo. L'accuracy qu'il donne est donc une borne optimiste, pas une mesure de performance en conditions réelles.

## `photos_reelles/` — à constituer, non fourni

Pour une mesure réaliste, organiser un petit jeu de vraies photos (boîtes déjà possédées, aucune question légale puisque ce sont des objets personnels — contrairement au scraping de sites de vente) de la même façon que `synthetique/` :

```
photos_reelles/
  images/*.jpg
  manifest.csv   # fichier, nom (le nom exact tel qu'il apparaît dans medicaments_reference.csv)
```

`py scripts/evaluer_reconnaissance.py --dataset data/vision/photos_reelles` fonctionne alors sans modification.
