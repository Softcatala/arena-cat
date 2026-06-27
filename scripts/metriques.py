# Mètriques de distància entre sortides de models per a un mateix prompt:
# chrF, cosinus de n-grames de caràcters i distància d'edició normalitzada.

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from itertools import combinations
import math
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


def _ngram_vector(text: str, max_n: int = 4) -> Counter[str]:
    """Vector de freqüències de n-grames de caràcters (n=1..max_n)."""
    vector: Counter[str] = Counter()
    for n in range(1, max_n + 1):
        for ngram, count in _char_ngrams(text, n).items():
            vector[f"{n}:{ngram}"] += count
    return vector


def cosine(text_a: str, text_b: str, max_n: int = 4) -> float:
    """Similitud cosinus entre dues cadenes a partir de n-grames de caràcters.

    Returns:
        Valor entre 0 i 1. Més alt = més semblants.
    """
    if not text_a or not text_b:
        return 0.0
    vec_a = _ngram_vector(text_a, max_n=max_n)
    vec_b = _ngram_vector(text_b, max_n=max_n)
    dot = sum(vec_a[key] * vec_b.get(key, 0) for key in vec_a)
    norm_a = math.sqrt(sum(value * value for value in vec_a.values()))
    norm_b = math.sqrt(sum(value * value for value in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def pairwise_metrics(outputs: dict[str, str]) -> dict[str, Any]:
    """Calcula chrF, cosinus i edit entre totes les parelles, amb mitjana i pitjor cas.

    La parella "pitjor" és la més semblant del trio (chrF/cos màxims, edit mínim):
    indica si dos models continuen sonant igual encara que la mitjana sigui alta.
    """
    pairs = []
    chrf_values: list[float] = []
    cosine_values: list[float] = []
    edit_values: list[float] = []
    for left, right in combinations(sorted(outputs), 2):
        chrf_score = chrf(outputs[left], outputs[right])
        cos_score = cosine(outputs[left], outputs[right])
        edit_score = edit_distance(outputs[left], outputs[right])
        pairs.append(
            {
                "pair": (left, right),
                "chrf": chrf_score,
                "cosine": cos_score,
                "edit": edit_score,
            }
        )
        chrf_values.append(chrf_score)
        cosine_values.append(cos_score)
        edit_values.append(edit_score)

    return {
        "pairs": pairs,
        "chrf_mean": sum(chrf_values) / len(chrf_values),
        "cosine_mean": sum(cosine_values) / len(cosine_values),
        "edit_mean": sum(edit_values) / len(edit_values),
        "chrf_worst": max(chrf_values),
        "cosine_worst": max(cosine_values),
        "edit_worst": min(edit_values),
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
        description="Calcula chrF, cosinus i distància d'edició entre sortides "
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
                f"chrF={pair['chrf']:5.2f}  cos={pair['cosine']:.3f}  "
                f"edit={pair['edit']:.3f}"
            )
        print(
            f"  mitjana   chrF={metrics['chrf_mean']:5.2f}  "
            f"cos={metrics['cosine_mean']:.3f}  edit={metrics['edit_mean']:.3f}"
        )
        print(
            f"  pitjor    chrF={metrics['chrf_worst']:5.2f}  "
            f"cos={metrics['cosine_worst']:.3f}  edit={metrics['edit_worst']:.3f}"
        )
