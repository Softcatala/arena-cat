# Mètriques de distància entre sortides de models per a un mateix prompt:
# chrF i distància d'edició normalitzada.

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _char_ngrams(text: str, n: int) -> Counter[str]:
    """Compta n-grames de caràcters d'una cadena ignorant espais en blanc."""
    cleaned = "".join(text.split())
    if len(cleaned) < n:
        return Counter()
    return Counter(cleaned[i : i + n] for i in range(len(cleaned) - n + 1))


def chrf(
    hypothesis: str,
    reference: str,
    max_n: int = 6,
    beta: float = 2.0,
) -> float:
    """Calcula chrF (F-score de n-grames de caràcters).

    Returns:
        Valor entre 0 i 100. Més alt = més semblants.
    """
    if not hypothesis or not reference:
        return 0.0

    precisions: list[float] = []
    recalls: list[float] = []
    for n in range(1, max_n + 1):
        hyp_ngrams = _char_ngrams(hypothesis, n)
        ref_ngrams = _char_ngrams(reference, n)
        if not hyp_ngrams or not ref_ngrams:
            continue
        overlap = sum((hyp_ngrams & ref_ngrams).values())
        precisions.append(overlap / sum(hyp_ngrams.values()))
        recalls.append(overlap / sum(ref_ngrams.values()))

    if not precisions:
        return 0.0
    avg_p = sum(precisions) / len(precisions)
    avg_r = sum(recalls) / len(recalls)
    if avg_p + avg_r == 0:
        return 0.0
    beta_sq = beta * beta
    f_score = (1 + beta_sq) * avg_p * avg_r / (beta_sq * avg_p + avg_r)
    return 100.0 * f_score


def edit_distance(text_a: str, text_b: str) -> float:
    """Distància de Levenshtein normalitzada a caràcter.

    Returns:
        Valor entre 0 i 1. 0 = idèntiques, 1 = totalment diferents.
    """
    if not text_a and not text_b:
        return 0.0
    if not text_a or not text_b:
        return 1.0
    len_a, len_b = len(text_a), len(text_b)
    prev = list(range(len_b + 1))
    for i in range(1, len_a + 1):
        curr = [i] + [0] * len_b
        for j in range(1, len_b + 1):
            cost = 0 if text_a[i - 1] == text_b[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[len_b] / max(len_a, len_b)


def pairwise_metrics(outputs: dict[str, str]) -> dict[str, Any]:
    """Calcula chrF i edit entre totes les parelles, com a distàncies 0-1.

    Totes dues mètriques s'expressen en la mateixa direcció (0 = idèntiques,
    1 = totalment diferents). La parella "pitjor" és la més semblant del trio
    (mínim en totes dues): indica si dos models segueixen sonant igual encara
    que la mitjana del grup sigui alta.
    """
    pairs = []
    chrf_dist_values: list[float] = []
    edit_values: list[float] = []
    dist_values: list[float] = []
    for left, right in combinations(sorted(outputs), 2):
        chrf_dist = 1.0 - chrf(outputs[left], outputs[right]) / 100.0
        edit_score = edit_distance(outputs[left], outputs[right])
        dist = (chrf_dist + edit_score) / 2.0
        pairs.append(
            {
                "pair": (left, right),
                "chrf_dist": chrf_dist,
                "edit": edit_score,
                "dist": dist,
            }
        )
        chrf_dist_values.append(chrf_dist)
        edit_values.append(edit_score)
        dist_values.append(dist)

    return {
        "pairs": pairs,
        "chrf_dist_mean": sum(chrf_dist_values) / len(chrf_dist_values),
        "edit_mean": sum(edit_values) / len(edit_values),
        "dist_mean": sum(dist_values) / len(dist_values),
        "chrf_dist_worst": min(chrf_dist_values),
        "edit_worst": min(edit_values),
        "dist_worst": min(dist_values),
    }


def load_answers(
    prompt_id: str,
    model_ids: Iterable[str],
    root: Path = REPO_ROOT,
    inference_subdir: str = "data/inferencies/v1",
) -> dict[str, str]:
    """Llegeix la resposta de cada model per a un prompt donat."""
    answers: dict[str, str] = {}
    base_dir = root / inference_subdir
    for model_id in model_ids:
        path = base_dir / model_id / f"{prompt_id}.yaml"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        answer = data.get("output", {}).get("answer")
        if answer is not None:
            answers[model_id] = answer
    return answers


def _discover_prompt_ids(inferences_dir: Path, model_ids: list[str]) -> list[str]:
    """Tots els prompt_id amb almenys una sortida desada."""
    prompt_ids: set[str] = set()
    for model_id in model_ids:
        for path in (inferences_dir / model_id).glob("*.yaml"):
            prompt_ids.add(path.stem)
    return sorted(prompt_ids)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Calcula chrF i distància d'edició entre sortides "
        "de models per a tots els prompts trobats."
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["qwen-3.5-9b", "salamandra-7b-instruct", "gemma-3-4b-it"],
        help="Llista de model_id a comparar.",
    )
    parser.add_argument(
        "--inferencies",
        default="data/inferencies/v1",
        help="Subdirectori d'inferències.",
    )
    args = parser.parse_args()

    prompt_ids = _discover_prompt_ids(REPO_ROOT / args.inferencies, args.models)
    if not prompt_ids:
        print(f"No s'ha trobat cap sortida a {args.inferencies}")
        raise SystemExit(1)

    for prompt_id in prompt_ids:
        outputs = load_answers(
            prompt_id, args.models, inference_subdir=args.inferencies
        )
        print(f"prompt: {prompt_id}")
        if len(outputs) < 2:
            print(f"  (calen ≥2 sortides; s'han trobat: {sorted(outputs)})")
            continue
        metrics = pairwise_metrics(outputs)
        for pair in metrics["pairs"]:
            left, right = pair["pair"]
            print(
                f"  {left:<28} vs {right:<28} "
                f"chrF_d={pair['chrf_dist']:.3f}  edit={pair['edit']:.3f}  "
                f"dist={pair['dist']:.3f}"
            )
        print(
            f"  mitjana   chrF_d={metrics['chrf_dist_mean']:.3f}  "
            f"edit={metrics['edit_mean']:.3f}  "
            f"dist={metrics['dist_mean']:.3f}"
        )
        print(
            f"  pitjor    chrF_d={metrics['chrf_dist_worst']:.3f}  "
            f"edit={metrics['edit_worst']:.3f}  "
            f"dist={metrics['dist_worst']:.3f}"
        )
