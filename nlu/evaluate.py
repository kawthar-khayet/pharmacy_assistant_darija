"""Evaluate the LLM few-shot NLU prototype against seed_dataset.jsonl.

Runs every example NOT used as a few-shot demonstration through
llm_prototype.run(), then reports:
  - Intent accuracy
  - Entity precision / recall / F1 (exact type+value match, case-insensitive)

Makes one metered API call per evaluation example (Ollama Cloud) -- run
manually once OLLAMA_API_KEY is set. Results are saved to nlu/eval_results.jsonl.
"""
import json
import sys
import time
from pathlib import Path

from llm_prototype import FEW_SHOT_IDS, load_seed_examples, run

HERE = Path(__file__).resolve().parent
RESULTS_PATH = HERE / "eval_results.jsonl"


def normalize_entity(ent: dict) -> tuple[str, str]:
    return (ent["type"], ent["value"].strip().lower())


def score_entities(gold: list[dict], pred: list[dict]) -> tuple[int, int, int]:
    gold_set = {normalize_entity(e) for e in gold}
    pred_set = {normalize_entity(e) for e in pred}
    tp = len(gold_set & pred_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    return tp, fp, fn


def _resultat(ex: dict, out: dict) -> dict:
    pred = out["output"]
    pred_intent = pred.get("intent")
    return {
        "id": ex["id"],
        "text": ex["text"],
        "lang": ex.get("lang"),
        "gold_intent": ex["intent"],
        "pred_intent": pred_intent,
        "intent_correct": pred_intent == ex["intent"],
        "gold_entities": ex["entities"],
        "pred_entities": pred.get("entities", []),
        "validation_errors": out["validation_errors"],
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    examples = load_seed_examples()
    eval_set = [ex for eid, ex in examples.items() if eid not in FEW_SHOT_IDS]

    intent_correct = 0
    total_tp = total_fp = total_fn = 0
    results = []

    # Premier passage, puis un second pour les exemples qui ont echoue : sur le
    # palier gratuit d'Ollama Cloud les surcharges passageres (503) sont
    # frequentes, et un exemple manquant fausserait la comparaison avec la
    # baseline, qui elle est evaluee sur la totalite du jeu.
    a_traiter = list(eval_set)
    for passage in (1, 2):
        echecs = []
        for i, ex in enumerate(a_traiter, start=1):
            try:
                out = run(ex["text"])
            # SystemExit n'herite pas d'Exception : c'est pourtant ce que leve
            # le client LLM sur une surcharge, et sans ce cas explicite une seule
            # surcharge interromprait toute l'evaluation en perdant les resultats.
            except (Exception, SystemExit) as e:
                print(f"[{i}/{len(a_traiter)}] ERREUR sur {ex['id']!r}: {e}")
                echecs.append(ex)
                continue
            results.append(_resultat(ex, out))
            r = results[-1]
            intent_correct += int(r["intent_correct"])
            tp, fp, fn = score_entities(ex["entities"], r["pred_entities"])
            total_tp += tp
            total_fp += fp
            total_fn += fn
            status = "OK" if r["intent_correct"] else "FAIL"
            print(f"[{i}/{len(a_traiter)}] {status} intent={r['pred_intent']!r} "
                  f"(gold={ex['intent']!r}) — {ex['text'][:50]}")
            time.sleep(0.2)

        if not echecs or passage == 2:
            break
        print(f"\n{len(echecs)} exemple(s) en echec, nouvel essai dans 20 s...\n")
        time.sleep(20)
        a_traiter = echecs

    manquants = [ex["id"] for ex in eval_set if ex["id"] not in {r["id"] for r in results}]

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n = len(results)
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print("\n=== Resultats ===")
    print(f"Exemples evalues       : {n}")
    print(f"Intent accuracy        : {intent_correct}/{n} = {intent_correct / n:.1%}" if n else "n/a")
    print(f"Entity precision       : {precision:.1%}")
    print(f"Entity recall          : {recall:.1%}")
    print(f"Entity F1              : {f1:.1%}")
    if manquants:
        print(f"ATTENTION : {len(manquants)} exemple(s) non evalue(s) apres deux passages : {manquants}")
    print(f"\nDetail sauvegarde dans : {RESULTS_PATH}")


if __name__ == "__main__":
    main()
