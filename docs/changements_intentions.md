# Taxonomie des intentions : changements v1 → v2

Ce document explique toutes les modifications apportées aux intentions de DwaTalk : ce qui a changé, pourquoi, dans quels fichiers, et avec quel effet mesuré.

## En bref

| v1 (7 intentions) | v2 (8 intentions) | Changement |
|---|---|---|
| `disponibilite_medicament` | `disponibilite_medicament` | absorbe l'ancienne `commande_reservation` |
| `commande_reservation` | — | **fusionnée** dans `disponibilite_medicament` |
| `prix_remboursement` | `prix_remboursement` | inchangée |
| — | `alternative_moins_chere` | **nouvelle** : équivalents moins chers |
| `info_pharmacie` | `info_pharmacie` | + avertissement sur les pharmacies de garde |
| `posologie_information` | `posologie_information` | inchangée |
| `autre` | `conseil_medical` | **scindée** : le patient parle de sa santé |
| `autre` | `hors_sujet` | **scindée** : sans rapport avec la pharmacie |
| `salutation` | `salutation` | inchangée |

Le principe qui a guidé chaque décision : **une distinction d'intention ne vaut que si elle change la réponse du système.** Sinon, elle ne fait qu'ajouter des occasions de se tromper.

---

## 1. `autre` scindée en `conseil_medical` et `hors_sujet`

### Le problème

Sur les 9 phrases annotées `autre`, **5 venaient de patients qui parlaient de leur santé** :

```
j'ai mal a la tete, quel medicament je peux prendre ?
3andi sda3, ach ndir?                     (j'ai mal à la tête, je fais quoi ?)
راني مريض بزاف                            (je suis très malade)
est-ce que le coronavirus est dangereux ?
3tini chi wa9t bach nji l tabib           (donne-moi un rendez-vous chez le médecin)
```

Les 4 autres étaient vraiment hors sujet (l'heure, la météo, les actualités, un restaurant). Les deux groupes recevaient la même réponse : « Je n'ai pas bien compris ta demande ». C'était faux pour le premier : le système avait compris, il n'avait simplement pas le droit de répondre.

### Ce qui a changé

- **`conseil_medical`** : le patient décrit un symptôme, dit qu'il est malade ou pose une question médicale. La réponse l'oriente vers un pharmacien ou un médecin et donne les numéros d'urgence :

  > Je ne peux pas donner d'avis médical ni conseiller un traitement à partir de symptômes. Parle à un pharmacien ou à un médecin : eux pourront t'examiner et te conseiller.
  > En cas d'urgence : SAMU 141 - Protection civile 15.
  > Intoxication ou surdosage de médicament : Centre antipoison 0801 000 180.

  Les numéros ont été **vérifiés** sur la page d'urgence de l'ambassade de France au Maroc (ma.diplomatie.gouv.fr/fr/urgence), pas cités de mémoire. Le Centre antipoison y figurait aussi : il a été ajouté, car il est directement utile dans une application de médicaments (surdosage, intoxication).

  **Aucune fiche de médicament n'est affichée**, même si le patient en cite un (« 3andi sda3, doliprane mzyan? ») : répondre à un symptôme par une fiche passerait pour une recommandation. Cette intention est traitée **en premier** dans l'API, avant toute autre.

- **`hors_sujet`** : la réponse présente ce que DwaTalk sait faire (« Je suis un assistant pharmacie : je peux t'aider pour les médicaments… »), au lieu d'un « je n'ai pas compris » qui laissait croire à un échec. Si un médicament a quand même été reconnu, sa fiche est donnée avec une réserve, comme avant.

### Le jeu annoté

- 5 phrases `autre` → `conseil_medical`, 4 → `hors_sujet` ;
- **11 phrases ajoutées** pour atteindre 10 exemples par intention : 5 questions de santé (fièvre d'un enfant, douleur à la poitrine, allergie…) et 6 hors sujet.
- Parmi les hors sujet, **des pièges volontaires** qui ressemblent à des questions de pharmacie : « wach kayn match lyoum? » (même tournure que « wach kayn doliprane? ») et « combien coûte un billet de train… » (même tournure qu'une question de prix). L'un d'eux (`seed_0121`) sert d'exemple dans l'invite.

---

## 2. `commande_reservation` fusionnée dans `disponibilite_medicament`

### Le problème

L'API traitait ces deux intentions **exactement de la même façon** :

```python
STOCK_RELATED_INTENTS = {"disponibilite_medicament", "commande_reservation"}
```

Leur frontière était pourtant la principale source d'erreurs : il avait fallu écrire une règle (« commande seulement avec un verbe de réservation ou d'achat »), corriger 5 étiquettes, et une des 2 erreurs restantes du LLM portait encore dessus (« bghit njib juj boites »). On payait la distinction en erreurs, sans aucun bénéfice dans la réponse.

### Ce qui a changé

- les 8 phrases `commande_reservation` sont devenues `disponibilite_medicament`, qui compte maintenant 40 exemples ;
- la description de `disponibilite_medicament` couvre explicitement l'achat, la réservation et la commande (« wach kayn », « bghit », « n7goz », « je veux commander ») ;
- la règle « bghit » a disparu du schéma, du script de génération et des tests ;
- `STOCK_RELATED_INTENTS` a été supprimé de l'API.

**À savoir** : si un jour DwaTalk peut vraiment réserver (partenariat avec des pharmacies), il faudra recréer une intention de commande, avec un comportement propre (récapitulatif médicament, dosage, quantité, pharmacie).

---

## 3. Nouvelle intention `alternative_moins_chere`

### Pourquoi

C'est une question très courante au Maroc (« kayn chi haja bhal doliprane b taman rkhis ? »), et le référentiel permet d'y répondre. Même molécule, même dosage :

```
paracétamol 500 mg : 41 produits, de 6,5 DH à 130,1 DH
```

### Ce qui a changé

- **nouvelle fonction `equivalents()`** dans `nlu/entity_linking.py` : produits de même composition (DCI identique), même dosage et même voie d'administration, disponibles en officine, du moins cher au plus cher ;
- **nouveau champ `alternatives`** dans la réponse de `/chat` : `{"reference": {...}, "equivalents": [...]}`, ou `null` ;
- **nouveau composant `AlternativesList`** dans l'interface : chaque équivalent avec sa forme, son prix et l'économie réalisée, suivi d'un rappel (« le changement de médicament se fait sur avis de ton pharmacien ») ;
- **11 phrases annotées** en darija latine, darija arabe, français et mixte, dont une sert d'exemple dans l'invite.

### Trois erreurs dangereuses trouvées en testant, et leurs garde-fous

La première version donnait des résultats faux. Chacune de ces erreurs a été corrigée, et un test empêche son retour.

**1. Une association remplacée par une seule molécule.** L'Augmentin (amoxicilline **et** acide clavulanique) donnait NEOMOX, de l'amoxicilline seule en injection. Cause : **la liste CNSS découpe une association en une ligne par molécule**, sous le même code produit. L'Augmentin y apparaît comme « amoxicilline » d'un côté, « acide clavulanique » de l'autre.
→ *Garde-fou* : seules les lignes issues de l'AMMPS (`//`) ou de la CNOPS (`/`), qui donnent la composition complète, sont utilisées pour comparer. L'Augmentin donne maintenant NEOCLAV, LEVAMOX et CO-AMOXICLAV, tous amoxicilline + acide clavulanique.

**2. Une autre voie d'administration.** Le Doliprane 1 g en comprimé donnait un Doliprane en **suppositoire**.
→ *Garde-fou* : un équivalent doit appartenir à la même **famille de forme** : orale solide, orale liquide, poudre orale, injectable, rectale, cutanée, ophtalmique, nasale, inhalée, vaginale, auriculaire. Une forme non classée n'accepte que la même forme exacte.

**3. Des produits introuvables en pharmacie.** Parmi les produits dont le statut est connu, 3 142 sont « Non Commercialisés », 953 « Retirés du Marché », 28 « Suspendus », et d'autres ne sont vendus qu'à l'export ou via des appels d'offres hospitaliers.
→ *Garde-fou* : seuls les produits « Commercialisé » sont proposés, ainsi que les produits sans statut, qui viennent de la liste CNSS actuelle des médicaments remboursables.

Deux réglages complètent ces garde-fous :
- **présentation de référence** : quand le patient ne précise pas le dosage, on part d'une présentation dont le prix est connu, puis d'une forme orale. Sans cela, « Spasfon » était comparé à sa version suppositoire ;
- **les équivalents au même prix sont gardés**, triés par prix. L'économie n'est affichée que lorsqu'elle existe.

### Quand il n'y a pas de réponse fiable

- médicament non cité : « De quel médicament veux-tu un équivalent moins cher ? » ;
- composition inconnue : « Je n'ai pas la composition complète de … : je ne peux pas te proposer d'équivalent fiable » ;
- aucun équivalent (Spasfon, Smecta) : « Je n'ai pas trouvé d'autre médicament commercialisé avec la même composition, le même dosage et la même voie d'administration ».

---

## 4. Pharmacie de garde : un avertissement, pas une nouvelle intention

Le jeu contenait déjà des questions comme « y'a-t-il une pharmacie de garde à Agdal **ce soir** ? ». Créer une intention dédiée aurait promis une réponse que les données ne peuvent pas donner : l'annuaire est un **instantané** récupéré sur saydalia.ma, alors que les gardes changent chaque jour.

La question reste donc dans `info_pharmacie`. Dès qu'une réponse parle de garde (mot « garde » dans la question, ou pharmacie marquée de garde dans les résultats), elle ajoute :

> Les pharmacies de garde changent chaque jour et notre annuaire n'est pas mis à jour en direct : appelle avant de te déplacer pour confirmer.

L'interface affiche cet avertissement sous les fiches de pharmacies.

---

## 5. Robustesse : intentions inconnues ou anciennes

Un modèle peut encore produire une ancienne intention par habitude, ou en inventer une. L'API les rabat désormais :
- `autre` → `hors_sujet` ;
- `commande_reservation` → `disponibilite_medicament` ;
- toute intention absente du schéma → `hors_sujet`.

La règle de repli de l'invite a aussi été réécrite : « si le message parle de santé sans demande sur un médicament précis, utilise `conseil_medical` ; s'il ne concerne ni les médicaments, ni les pharmacies, ni la santé, utilise `hors_sujet` ».

---

## 6. Fichiers modifiés

| Fichier | Modification |
|---|---|
| `nlu/schema.json` | version 0.2, 8 intentions, nouvelles descriptions (elles sont recopiées dans l'invite) |
| `nlu/build_seed_dataset.py` | 13 étiquettes changées, 22 phrases ajoutées, commentaire de la règle « bghit » remplacé |
| `nlu/seed_dataset.jsonl` | régénéré : 99 → 121 phrases |
| `nlu/llm_prototype.py` | exemples de l'invite 9 → 11 (un par intention au moins), règle de repli réécrite |
| `nlu/entity_linking.py` | `equivalents()`, `famille_forme()`, garde-fous composition / voie / commercialisation |
| `api/main.py` | aiguillage des 8 intentions, messages santé et hors sujet, champ `alternatives`, avertissement de garde, rabattement des intentions inconnues |
| `frontend/src/components/AlternativesList.jsx` | **nouveau** : liste des équivalents |
| `frontend/src/components/ChatMessage.jsx` | affichage des équivalents, conservation de l'avertissement de garde, `autre` → `hors_sujet` |
| `frontend/src/pages/Assistant.jsx` | suggestion « Kayn chi dwa bhal doliprane rkhis? » |
| `tests/test_nlu.py` | tests de la règle « bghit » remplacés par ceux de la taxonomie v2 |
| `tests/test_api.py` | 4 tests adaptés, 9 scénarios ajoutés |
| `tests/test_matchers.py` | 13 tests d'équivalents, dont les 3 régressions de sécurité |
| `nlu/README.md`, `api/README.md` | documentation à jour |

---

## 7. Tests

| | Avant | Après |
|---|---|---|
| Tests automatisés | 172 | **221** |

Les nouveaux tests couvrent :
- **la taxonomie** : 8 intentions exactement, plus aucune ancienne étiquette dans le jeu, au moins 8 exemples par intention, les ex-commandes bien rangées en disponibilité ;
- **la santé** : message d'orientation avec les numéros vérifiés, jamais de fiche même quand un médicament est cité ;
- **les équivalents** : tri par prix, même molécule et même dosage, et les trois régressions de sécurité (Augmentin jamais remplacé par une molécule seule, même voie d'administration, jamais de produit retiré ou non commercialisé) ;
- **la robustesse** : intentions anciennes ou inventées rabattues, avertissement de garde.

---

## 8. Résultats de l'évaluation

Mesuré sur les **110 phrases** qui ne servent pas d'exemples au modèle (121 moins les 11 exemples de l'invite), avec gpt-oss-20b à température 0. La baseline classique est évaluée sur les mêmes phrases, en validation croisée à 5 plis.

| | v1 — LLM<br>(90 phrases, 7 intentions) | **v2 — LLM**<br>(110 phrases, 8 intentions) | v2 — baseline |
|---|---|---|---|
| Intentions — exactitude | 97,8 % | **98,2 %** (108/110) | 62,7 % |
| Intentions — F1 macro | 97,3 % | **97,9 %** | 53,8 % |
| Entités — F1 | 98,6 % | **97,6 %** | 95,4 % |

### Par intention (LLM, v2)

| Intention | Correctes |
|---|---|
| `disponibilite_medicament` | 37 / 37 |
| `alternative_moins_chere` | **10 / 10** (nouvelle) |
| `conseil_medical` | **9 / 9** (nouvelle) |
| `hors_sujet` | **9 / 9** (nouvelle, pièges compris) |
| `info_pharmacie` | 12 / 12 |
| `salutation` | 12 / 12 |
| `prix_remboursement` | 11 / 12 |
| `posologie_information` | 8 / 9 |

### Ce que ça montre

- **Les trois nouvelles intentions sont parfaitement reconnues**, y compris les pièges hors sujet qui imitent une question de pharmacie (« wach kayn match lyoum? »).
- **La fusion a fait disparaître l'erreur qu'elle visait** : « bghit njib juj boites », mal classée en v1, est maintenant correcte, et `disponibilite_medicament` fait 37 sur 37.
- **Les 2 erreurs restantes** :
  - « كيفاش ناخد الدواء؟ » (comment je prends le médicament ?), annotée posologie, est classée `conseil_medical`. Sans nom de médicament, les deux lectures se défendent : c'est le nouveau cas limite (voir section 9).
  - « hal amoxicilline mashmoula bi at-ta'min? » (l'amoxicilline est-elle remboursée ?, en arabe standard translittéré) est classée en disponibilité. Elle était déjà ratée en v1, où elle partait en `autre`.
- **La légère baisse sur les entités ne vient pas du changement d'intentions.** Seules 3 phrases diffèrent, dont 2 à cause de l'article élidé : le modèle extrait « l'efferalgan » et « l'amoxicilline » au lieu du seul nom. C'était déjà un défaut connu en v1, et l'une des nouvelles phrases le reproduit. La troisième (« sirop dyal la toux », pris pour un nom de médicament) était déjà en v1. La résolution du médicament retrouve quand même le bon produit malgré l'article.
- **La baseline recule** (67,8 % → 62,7 % sur les intentions) : 8 classes au lieu de 7, avec seulement 9 à 10 exemples pour la plupart, c'est encore plus difficile pour un modèle statistique. L'écart avec le LLM s'agrandit.

### Limites de la comparaison

Les colonnes v1 et v2 ne se comparent pas strictement : le jeu de test a changé (90 → 110 phrases, 7 → 8 intentions, 13 étiquettes modifiées), et sur 110 phrases chaque exemple pèse environ 0,9 point. La conclusion solide est qualitative : **les nouvelles intentions fonctionnent, et la taxonomie v2 n'a pas dégradé la reconnaissance**.

---

## 9. Problèmes découverts et limites

- **Défaut de données CNSS** (découvert en construisant les équivalents) : la liste CNSS découpe les associations de molécules en une ligne par molécule. 1 069 produits sont concernés, soit 2 219 lignes du référentiel. Les équivalents sont protégés par le garde-fou n° 1, mais **les fiches de médicaments peuvent encore afficher une composition incomplète** pour un produit présent uniquement dans la liste CNSS. Correction à faire dans `scripts/clean_merge.py` : regrouper les lignes CNSS par code produit. Elle n'a pas été faite ici, car elle modifie le référentiel et ses chiffres documentés.
- **Frontière posologie / santé** : sans nom de médicament, une question comme « كيفاش ناخد الدواء؟ » (comment je prends le médicament ?) peut relever des deux. C'est un cas limite à trancher, comme l'était « bghit ».
- **Article élidé** : le modèle extrait parfois « l'efferalgan » au lieu de « efferalgan » (2 des 3 écarts d'entités). Piste : ajouter une règle dans l'invite, ou retirer « l' » / « d' » avant la résolution — la baseline le fait déjà.
- **Équivalents limités** : les produits présents uniquement dans la liste CNSS ne sont jamais proposés (composition non fiable), et les associations dont le dosage est écrit différemment entre AMMPS et CNOPS ne sont pas rapprochées. Le système préfère proposer moins d'équivalents plutôt qu'un seul faux.
- **Le rapport Word (`docs/rapport_DwaTalk.docx`) décrit encore la taxonomie v1** et ses chiffres. Il est à mettre à jour avant un rendu.

---

## 10. Reproduire

```
py nlu/build_seed_dataset.py        # regenere le jeu annote
py -m pytest                        # 221 tests
py nlu/evaluate.py                  # evaluation du LLM (110 appels Ollama)
py nlu/compare_baseline.py          # comparaison avec la baseline (sans appel)
```
