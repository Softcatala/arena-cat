# Genera results.txt amb les distàncies entre sortides de cada model i el
# rang dels prompts segons com de discriminants són (com més divergents les
# sortides, més discriminant és el prompt).

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402

from scripts.lib.inference_metrics import load_answers, pairwise_metrics  # noqa: E402

RECOMMENDED_THRESHOLD = 0.40

config_path = REPO_ROOT / "config/inferencia/inferencia_config.yaml"
config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
MODEL_DISPLAY = {m["id"]: m["model_name"] for m in config["models"]}
MODEL_IDS = list(MODEL_DISPLAY)


def _category(prompt_id: str) -> str:
    return prompt_id.split("_", 1)[0]


def _discover_prompt_ids(inferences_dir: Path) -> list[str]:
    ids = {p.stem for m in MODEL_IDS for p in (inferences_dir / m).glob("*.yaml")}
    return sorted(ids)


def _load_original_prompt(inferences_dir: Path, prompt_id: str) -> str:
    """Llegeix el prompt original referenciat per qualsevol de les inferències."""
    for model_id in MODEL_IDS:
        inf_path = inferences_dir / model_id / f"{prompt_id}.yaml"
        if not inf_path.is_file():
            continue
        rel = (yaml.safe_load(inf_path.read_text("utf-8")) or {}).get("prompt", {}).get(
            "path"
        )
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


def _category_summary(entries: list[dict]) -> list[dict]:
    rows = {}
    for e in entries:
        category = _category(e["prompt_id"])
        score = e["metrics"]["combinat_worst"]
        row = rows.setdefault(
            category,
            {
                "category": category,
                "total": 0,
                "valid": 0,
                "invalid": 0,
                "worst": score,
                "mean_worst": 0.0,
            },
        )
        row["total"] += 1
        row["worst"] = min(row["worst"], score)
        row["mean_worst"] += score
        if score >= RECOMMENDED_THRESHOLD:
            row["valid"] += 1
        else:
            row["invalid"] += 1

    for row in rows.values():
        row["mean_worst"] /= row["total"]
        row["valid_pct"] = row["valid"] * 100 / row["total"]
        row["invalid_pct"] = row["invalid"] * 100 / row["total"]
    return sorted(rows.values(), key=lambda s: s["category"])


def _print_category_summary(category_summary: list[dict]) -> None:
    print("\nResum de revisió per categoria")
    print(f"Cal revisar = combinat_worst < {RECOMMENDED_THRESHOLD:.2f}")
    print("worst = mínim de combinat_worst dels prompts de la categoria.")
    print("mean_worst = mitjana de combinat_worst dels prompts de la categoria.")
    print(
        f"{'categoria':<16}{'total':>7}{'acceptables':>13}{'cal revisar':>13}"
        f"{'% acceptables':>15}{'% cal revisar':>15}{'worst':>10}"
        f"{'mean_worst':>12}"
    )
    for row in category_summary:
        print(
            f"{row['category']:<16}{row['total']:>7}{row['valid']:>13}"
            f"{row['invalid']:>13}{row['valid_pct']:>14.1f}%"
            f"{row['invalid_pct']:>14.1f}%{row['worst']:>10.4f}"
            f"{row['mean_worst']:>12.4f}"
        )


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
        entries.append({
            "prompt_id": prompt_id,
            "prompt_text": _load_original_prompt(inferences_dir, prompt_id),
            "outputs": outputs,
            "metrics": pairwise_metrics(outputs),
            "missing": [m for m in MODEL_IDS if m not in outputs],
        })

    entries.sort(key=lambda e: e["metrics"]["combinat_mean"], reverse=True)
    category_summary = _category_summary(entries)
    if category_summary:
        _print_category_summary(category_summary)

    env = Environment(loader=FileSystemLoader(Path(__file__).parent))
    rendered = env.get_template("results.txt.j2").render(
        inferencies=args.inferencies,
        models=MODEL_IDS,
        models_display=[MODEL_DISPLAY[m] for m in MODEL_IDS],
        models_display_map=MODEL_DISPLAY,
        recommended_threshold=RECOMMENDED_THRESHOLD,
        category_summary=category_summary,
        entries=entries,
    )

    target = REPO_ROOT / "results.txt"
    target.write_text(rendered, encoding="utf-8")
    print(f"Escrit: {target}")


if __name__ == "__main__":
    main()
