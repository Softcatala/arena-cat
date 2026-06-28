# Distàncies entre sortides de models (chrF i Levenshtein) per a un mateix prompt.

from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.distance import Levenshtein
from sacrebleu.metrics import CHRF

REPO_ROOT = Path(__file__).resolve().parents[1]
_CHRF = CHRF(char_order=6, word_order=0, beta=2)


def chrf(hypothesis: str, reference: str) -> float:
    """chrF entre 0 i 100 (més alt = més semblants)."""
    if not hypothesis or not reference:
        return 0.0
    return _CHRF.sentence_score(hypothesis, [reference]).score


def edit_distance(text_a: str, text_b: str) -> float:
    """Distància de Levenshtein normalitzada (0 = idèntiques, 1 = totalment diferents)."""
    if not text_a and not text_b:
        return 0.0
    return Levenshtein.normalized_distance(text_a, text_b)


def pairwise_metrics(outputs: dict[str, str]) -> dict[str, Any]:
    """chrF_d i edit entre totes les parelles, com a distàncies 0-1.

    "Pitjor" és la parella MÉS semblant del grup (mínim): indica si dos
    models segueixen sonant igual encara que la mitjana sigui alta.
    """
    pairs = []
    for left, right in combinations(sorted(outputs), 2):
        chrf_dist = 1.0 - chrf(outputs[left], outputs[right]) / 100.0
        edit_score = edit_distance(outputs[left], outputs[right])
        pairs.append(
            {
                "pair": (left, right),
                "chrf_dist": chrf_dist,
                "edit": edit_score,
                "combinat": (chrf_dist + edit_score) / 2.0,
            }
        )
    chrf_vals = [p["chrf_dist"] for p in pairs]
    edit_vals = [p["edit"] for p in pairs]
    combinat_vals = [p["combinat"] for p in pairs]
    return {
        "pairs": pairs,
        "chrf_dist_mean": sum(chrf_vals) / len(chrf_vals),
        "edit_mean": sum(edit_vals) / len(edit_vals),
        "combinat_mean": sum(combinat_vals) / len(combinat_vals),
        "chrf_dist_worst": min(chrf_vals),
        "edit_worst": min(edit_vals),
        "combinat_worst": min(combinat_vals),
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
