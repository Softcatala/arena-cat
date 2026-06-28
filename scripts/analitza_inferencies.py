# Genera results.txt amb les distàncies entre sortides de cada model i el
# rang dels prompts segons com de discriminants són (com més divergents les
# sortides, més discriminant és el prompt).

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import yaml  # noqa: E402

from metriques import load_answers, pairwise_metrics  # noqa: E402

MODEL_DISPLAY = {
    "qwen-3.5-9b": "Qwen/Qwen3.5-9B",
    "salamandra-7b-instruct": "BSC-LT/salamandra-7b-instruct",
    "gemma-3-4b-it": "google/gemma-3-4b-it",
}
MODEL_IDS = list(MODEL_DISPLAY)


def _discover_prompt_ids(inferences_dir: Path) -> list[str]:
    ids = {p.stem for m in MODEL_IDS for p in (inferences_dir / m).glob("*.yaml")}
    return sorted(ids)


def _load_original_prompt(inferences_dir: Path, prompt_id: str) -> str:
    """Llegeix el prompt original referenciat per qualsevol de les inferències."""
    for model_id in MODEL_IDS:
        inf_path = inferences_dir / model_id / f"{prompt_id}.yaml"
        if not inf_path.is_file():
            continue
        rel = (yaml.safe_load(inf_path.read_text("utf-8")) or {}).get("prompt", {}).get("path")
        prompt_path = REPO_ROOT / rel if rel else None
        if not prompt_path or not prompt_path.is_file():
            continue
        raw = prompt_path.read_text("utf-8")
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError:
            data = None
        return (data["text"] if isinstance(data, dict) and "text" in data else raw).strip()
    return "(prompt original no trobat)"


def _format_section(
    prompt_id: str,
    prompt_text: str,
    outputs: dict,
    metrics: dict,
    rank: int,
) -> str:
    lines = [
        "=" * 80,
        f"PROMPT {prompt_id}",
        "=" * 80,
        f"Rang (0 = més discriminant): {rank}",
        f"Puntuació (combinat mitjà, més alt = més divergent): {metrics['combinat_mean']:.4f}",
        "",
        "--- PROMPT ORIGINAL ---",
        prompt_text,
        "",
        "--- MÈTRIQUES PARELLA A PARELLA ---",
    ]
    for pair in metrics["pairs"]:
        left, right = pair["pair"]
        lines.append(
            f"  {left:<28} vs {right:<28} "
            f"chrF_d={pair['chrf_dist']:.3f}  edit={pair['edit']:.3f}  "
            f"combinat={pair['combinat']:.3f}"
        )
    lines.append(
        f"  chrF_d mitjà : {metrics['chrf_dist_mean']:.3f}    "
        f"edit mitjà : {metrics['edit_mean']:.3f}    "
        f"combinat mitjà : {metrics['combinat_mean']:.3f}"
    )
    lines.append(
        f"  chrF_d pitjor: {metrics['chrf_dist_worst']:.3f}    "
        f"edit pitjor: {metrics['edit_worst']:.3f}    "
        f"combinat pitjor: {metrics['combinat_worst']:.3f}"
    )
    missing = [m for m in MODEL_IDS if m not in outputs]
    if missing:
        lines.append(f"  Sortides absents: {', '.join(missing)}")
    lines.append("")
    lines.append("--- SORTIDES DELS MODELS ---")
    for model_id in MODEL_IDS:
        lines.append(f"[{MODEL_DISPLAY[model_id]}]")
        lines.append(outputs.get(model_id, "(SENSE SORTIDA)").strip())
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calcula mètriques de distància entre sortides de models "
        "per als prompts d'un directori d'inferències."
    )
    parser.add_argument(
        "--inferencies",
        default="data/inferencies/v1",
        help="Subdirectori d'inferències (relatiu al repo).",
    )
    args = parser.parse_args()

    inferences_dir = REPO_ROOT / args.inferencies
    entries = []
    for prompt_id in _discover_prompt_ids(inferences_dir):
        outputs = load_answers(prompt_id, MODEL_IDS, inference_subdir=args.inferencies)
        if len(outputs) < 2:
            print(f"avís: {prompt_id} té només {len(outputs)} sortida(es), s'omet")
            continue
        prompt_text = _load_original_prompt(inferences_dir, prompt_id)
        entries.append((prompt_id, prompt_text, outputs, pairwise_metrics(outputs)))

    entries.sort(key=lambda e: e[3]["combinat_mean"], reverse=True)

    lines = [
        "RESULTATS - Distàncies entre sortides de models per prompt",
        "",
        f"Inferències:   {args.inferencies}",
        f"Models:        {', '.join(MODEL_DISPLAY[m] for m in MODEL_IDS)}",
        "",
        "Mètriques (0 = idèntiques, 1 = totalment diferents):",
        "  - chrF_d:   distància chrF",
        "  - edit:     distància de Levenshtein normalitzada",
        "  - combinat: mitjana de chrF_d i edit",
        "",
        "Rang 0 = prompt MÉS DISCRIMINANT (sortides més divergents entre models).",
        "",
        "RESUM DE RANGS",
        "-" * 80,
        f"{'rang':<6}{'prompt':<35}{'chrF_d mitjà':<16}{'edit mitjà':<14}combinat",
    ]
    for rank, (prompt_id, _, _, m) in enumerate(entries):
        lines.append(
            f"{rank:<6}{prompt_id:<35}"
            f"{m['chrf_dist_mean']:<16.3f}{m['edit_mean']:<14.3f}{m['combinat_mean']:.4f}"
        )
    lines.append("")
    for rank, (prompt_id, prompt_text, outputs, metrics) in enumerate(entries):
        lines.append(_format_section(prompt_id, prompt_text, outputs, metrics, rank))
        lines.append("")

    target = REPO_ROOT / "results.txt"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"Escrit: {target}")


if __name__ == "__main__":
    main()
