"""Compare le LLM few-shot a la baseline classique, sur le meme jeu de test.

Protocole
---------
- Jeu de test : les exemples de seed_dataset.jsonl qui ne servent PAS de
  demonstration few-shot au LLM -- exactement ceux qu'evalue evaluate.py.
- LLM : predictions lues dans eval_results.jsonl (lancer evaluate.py avant).
- Baseline intent : validation croisee stratifiee a 5 plis sur ce jeu. Chaque
  exemple est predit par un modele qui ne l'a jamais vu. Les exemples few-shot
  sont ajoutes a l'entrainement de chaque pli : le LLM les voit aussi, c'est
  donc a information egale.
- Baseline entites : regles et lexiques, sans apprentissage (voir baseline.py).
- Memes metriques que evaluate.py : exactitude des intents, et precision /
  rappel / F1 des entites en correspondance exacte type + valeur (sans casse).

Aucun appel payant : tourne en quelques secondes. Ecrit comparison_results.json.
"""
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold

from baseline import ExtracteurRegles, nouveau_classifieur_intent
from evaluate import RESULTS_PATH, score_entities
from llm_prototype import FEW_SHOT_IDS, load_seed_examples

HERE = Path(__file__).resolve().parent
SORTIE = HERE / "comparison_results.json"
GRAINE = 42


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def entites_par_type(exemples, predictions):
    """P/R/F1 par type d'entite -- montre ou chaque approche peche."""
    compte = defaultdict(lambda: [0, 0, 0])
    for ex, pred in zip(exemples, predictions):
        for type_ in {e["type"] for e in ex["entities"]} | {e["type"] for e in pred}:
            tp, fp, fn = score_entities(
                [e for e in ex["entities"] if e["type"] == type_],
                [e for e in pred if e["type"] == type_],
            )
            compte[type_][0] += tp
            compte[type_][1] += fp
            compte[type_][2] += fn
    return {t: prf(*v) for t, v in sorted(compte.items())}


def bilan(exemples, intents_predits, entites_predites):
    gold = [ex["intent"] for ex in exemples]
    exact = sum(g == p for g, p in zip(gold, intents_predits))

    tp = fp = fn = 0
    for ex, pred in zip(exemples, entites_predites):
        a, b, c = score_entities(ex["entities"], pred)
        tp, fp, fn = tp + a, fp + b, fn + c
    p, r, f = prf(tp, fp, fn)

    par_langue = defaultdict(lambda: [0, 0])
    for ex, pred in zip(exemples, intents_predits):
        par_langue[ex["lang"]][0] += int(pred == ex["intent"])
        par_langue[ex["lang"]][1] += 1

    return {
        "intent_accuracy": exact / len(exemples),
        "intent_macro_f1": f1_score(gold, intents_predits, average="macro", zero_division=0),
        "entity_precision": p,
        "entity_recall": r,
        "entity_f1": f,
        "entity_par_type": {t: {"p": v[0], "r": v[1], "f1": v[2]} for t, v in entites_par_type(exemples, entites_predites).items()},
        "intent_par_langue": {l: {"exactes": c, "total": n, "accuracy": c / n} for l, (c, n) in sorted(par_langue.items())},
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    exemples_par_id = load_seed_examples()
    jeu_test = [ex for eid, ex in exemples_par_id.items() if eid not in FEW_SHOT_IDS]
    few_shot = [exemples_par_id[i] for i in FEW_SHOT_IDS if i in exemples_par_id]

    # ------------------------------------------------------------- LLM
    if not RESULTS_PATH.exists():
        sys.exit("eval_results.jsonl absent : lance d'abord `py nlu/evaluate.py`.")
    llm = {}
    with open(RESULTS_PATH, encoding="utf-8") as f:
        for ligne in f:
            if ligne.strip():
                r = json.loads(ligne)
                llm[r["id"]] = r

    # Des resultats LLM produits avec d'autres labels ou d'autres few-shot ne
    # sont pas comparables : on le verifie au lieu de le supposer.
    ids_test = {ex["id"] for ex in jeu_test}
    perimes = [i for i, r in llm.items() if i in exemples_par_id and r["gold_intent"] != exemples_par_id[i]["intent"]]
    hors_jeu = sorted(set(llm) - ids_test)
    if perimes or hors_jeu:
        sys.exit(
            "eval_results.jsonl ne correspond pas au jeu de test actuel "
            f"(labels changes : {perimes}, ids few-shot : {hors_jeu}). Relance evaluate.py."
        )
    communs = [ex for ex in jeu_test if ex["id"] in llm]
    if len(communs) < len(jeu_test):
        print(f"ATTENTION : le LLM n'a ete evalue que sur {len(communs)}/{len(jeu_test)} exemples ; "
              "la comparaison se fait sur ces exemples communs.\n")

    llm_intents = [llm[ex["id"]]["pred_intent"] for ex in communs]
    llm_entites = [llm[ex["id"]]["pred_entities"] for ex in communs]

    # ------------------------------------------------------- baseline
    t0 = time.perf_counter()
    textes = np.array([ex["text"] for ex in communs])
    labels = np.array([ex["intent"] for ex in communs])
    base_intents = np.empty(len(communs), dtype=object)

    plis = StratifiedKFold(n_splits=5, shuffle=True, random_state=GRAINE)
    for train_idx, test_idx in plis.split(textes, labels):
        clf = nouveau_classifieur_intent()
        x = list(textes[train_idx]) + [ex["text"] for ex in few_shot]
        y = list(labels[train_idx]) + [ex["intent"] for ex in few_shot]
        clf.fit(x, y)
        base_intents[test_idx] = clf.predict(textes[test_idx])

    extracteur = ExtracteurRegles()
    t1 = time.perf_counter()
    base_entites = [extracteur.extraire(ex["text"]) for ex in communs]
    ms_par_phrase = (time.perf_counter() - t1) / len(communs) * 1000
    duree_totale = time.perf_counter() - t0

    # --------------------------------------------------------- bilans
    res_llm = bilan(communs, llm_intents, llm_entites)
    res_base = bilan(communs, list(base_intents), base_entites)

    print(f"Jeu de test : {len(communs)} exemples (hors {len(few_shot)} few-shot)")
    print(f"Repartition : {dict(Counter(str(l) for l in labels))}\n")
    print(f"{'':28}{'LLM few-shot':>14}{'Baseline':>12}")
    for cle, libelle in [
        ("intent_accuracy", "Intent - exactitude"),
        ("intent_macro_f1", "Intent - F1 macro"),
        ("entity_precision", "Entites - precision"),
        ("entity_recall", "Entites - rappel"),
        ("entity_f1", "Entites - F1"),
    ]:
        print(f"{libelle:28}{res_llm[cle]:>14.1%}{res_base[cle]:>12.1%}")

    print("\nF1 entites par type")
    types = sorted(set(res_llm["entity_par_type"]) | set(res_base["entity_par_type"]))
    for t in types:
        a = res_llm["entity_par_type"].get(t, {}).get("f1", 0.0)
        b = res_base["entity_par_type"].get(t, {}).get("f1", 0.0)
        print(f"  {t:26}{a:>14.1%}{b:>12.1%}")

    print("\nExactitude des intents par langue")
    for l in sorted(res_llm["intent_par_langue"]):
        a = res_llm["intent_par_langue"][l]
        b = res_base["intent_par_langue"][l]
        print(f"  {l:10} (n={a['total']:>2}){a['accuracy']:>14.1%}{b['accuracy']:>12.1%}")

    print(f"\nBaseline : entrainement + prediction des 5 plis en {duree_totale:.1f} s, "
          f"extraction d'entites {ms_par_phrase:.1f} ms/phrase, sans reseau ni cout.")

    erreurs_base = [
        {"id": ex["id"], "text": ex["text"], "gold": ex["intent"], "pred": p}
        for ex, p in zip(communs, base_intents) if p != ex["intent"]
    ]
    SORTIE.write_text(json.dumps({
        "protocole": {
            "jeu_test": len(communs),
            "few_shot_exclus": list(FEW_SHOT_IDS),
            "validation_croisee": "StratifiedKFold(5), few-shot ajoutes a chaque entrainement",
            "graine": GRAINE,
        },
        "llm_few_shot": res_llm,
        "baseline": res_base,
        "erreurs_intent_baseline": erreurs_base,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Detail : {SORTIE}")


if __name__ == "__main__":
    main()
