# La canonada (pipeline) d'inferència amb Hugging Face

import argparse
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
import hashlib
import os
from pathlib import Path
import subprocess
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path) -> None:
    """Carrega variables d'entorn des d'un fitxer .env local."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


load_env(REPO_ROOT / ".env")

import torch  # noqa: E402
import transformers  # noqa: E402
from transformers import (  # noqa: E402
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)


ConfigDict = dict[str, Any]
Prompt = dict[str, Any]
Loader = Callable[..., Any]


def get_git_commit() -> str:
    """Retorna el commit Git actual o un marcador estable fora d'un repo."""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=REPO_ROOT,
            )
            .decode("ascii")
            .strip()
        )
    except Exception:
        return "not_a_git_repository"


def calculate_sha256(text: str) -> str:
    """Calcula el SHA-256 del text del prompt."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def timestamp_utc() -> str:
    """Genera un timestamp UTC en format ISO-8601 amb sufix Z."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def split_reasoning(text: str) -> tuple[str | None, str]:
    """
    Detecta estructures de pensament tipus <think>...</think> i les separa
    de la resposta final visible per a l'avaluador.
    """
    if "<think>" in text and "</think>" in text:
        parts = text.split("</think>")
        reasoning = parts[0].replace("<think>", "").strip()
        clean_answer = parts[1].strip()
        return reasoning, clean_answer
    return None, text.strip()


def load_config(root: Path = REPO_ROOT) -> ConfigDict:
    """Llegeix la configuració d'inferència activa."""
    config_path = Path(
        os.getenv(
            "INFERENCIA_CONFIG",
            "config/inferencia/inferencia_config.yaml",
        )
    )
    if not config_path.is_absolute():
        config_path = root / config_path

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_device_map_override(
    config: ConfigDict,
    device_map: str | None,
) -> ConfigDict:
    """Sobreescriu el device_map de tots els models si s'ha indicat per CLI."""
    if device_map is None:
        return config

    for model_entry in config["models"]:
        model_entry["device_map"] = device_map

    return config


def resolve_config_dir(
    global_config: ConfigDict,
    key: str,
    default_value: str,
    root: Path = REPO_ROOT,
) -> Path:
    """Resol un directori de configuració relatiu al repo si cal."""
    base_dir = Path(global_config.get(key, default_value))
    return base_dir if base_dir.is_absolute() else root / base_dir


def discover_prompt_files(
    global_config: ConfigDict | str | Path | None = None,
    root: Path = REPO_ROOT,
) -> list[Path]:
    """Descobreix els fitxers YAML de prompts configurats."""
    if isinstance(global_config, (str, Path)):
        root = Path(global_config)
        global_config = {}
    elif global_config is None:
        global_config = {}

    prompts_dir = resolve_config_dir(
        global_config, "dir_prompts", "data/prompts/v1", root
    )
    return sorted(prompts_dir.glob("*.yaml"))


# TODO: potser es pot simplificar quan el format dels prompts es definit?


def load_prompts(
    prompt_files: Iterable[Path],
    root: Path = REPO_ROOT,
) -> list[Prompt]:
    """Carrega prompts YAML acceptant escalares, diccionaris i llistes."""
    prompt_list = []
    for prompt_file in prompt_files:
        with prompt_file.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        if isinstance(data, list):
            prompts = data
        elif isinstance(data, dict):
            prompts = [data]
        elif isinstance(data, str):
            prompts = [{"id": prompt_file.stem, "text": data}]
        else:
            continue

        for prompt in prompts:
            prompt["_path_origen"] = str(prompt_file.relative_to(root))
            prompt_list.append(prompt)

    return prompt_list


def get_model_name(model_entry: ConfigDict) -> str:
    """Obtè el nom Hugging Face del model configurat."""
    return (
        model_entry["name"]
        if "name" in model_entry
        else model_entry["model_name"]
    )


def get_dtype(torch_dtype: str) -> Any:
    """Converteix el nom de dtype configurat al dtype de PyTorch."""
    dtype_map = {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }

    if torch_dtype not in dtype_map:
        options = ", ".join(sorted(dtype_map))
        raise ValueError(
            f"torch_dtype no suportat: {torch_dtype}. Opcions: {options}"
        )

    return dtype_map[torch_dtype]


def load_tokenizer(
    model_entry: ConfigDict,
    hf_token: str | None = None,
    tokenizer_loader: Loader = AutoTokenizer.from_pretrained,
) -> Any:
    """Carrega el tokenizer del model configurat."""
    return tokenizer_loader(
        get_model_name(model_entry),
        revision=model_entry["revision"],
        token=hf_token,
    )


def load_model(
    model_entry: ConfigDict,
    hf_token: str | None = None,
    model_loader: Loader = AutoModelForCausalLM.from_pretrained,
) -> Any:
    """Carrega el model i aplica la quantització si està configurada."""
    dtype = get_dtype(model_entry["torch_dtype"])
    device_map = model_entry["device_map"]
    kwargs = {
        "revision": model_entry["revision"],
        "dtype": dtype,
        "device_map": device_map,
        "token": hf_token,
    }

    quantization = model_entry.get("quantization")
    if quantization == "4bit":
        if isinstance(device_map, dict) and {"cpu", "disk"} & set(
            device_map.values()
        ):
            raise ValueError(
                "4bit no suporta offload a CPU/disc en aquesta configuracio. "
                "Usa device_map: {'': 0}."
            )
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=dtype,
            bnb_4bit_quant_type=model_entry.get("bnb_4bit_quant_type", "nf4"),
            bnb_4bit_use_double_quant=model_entry.get(
                "bnb_4bit_use_double_quant", True
            ),
        )
    elif quantization not in (None, "none"):
        raise ValueError(
            f"quantization no suportada: {quantization}. Opcions: 4bit, none"
        )

    return model_loader(get_model_name(model_entry), **kwargs)


def build_messages(
    prompt_text: str, generation_params: ConfigDict
) -> list[ConfigDict]:
    """Construeix els missatges de xat per al tokenizer."""
    messages = []
    if generation_params.get("system_prompt"):
        messages.append(
            {"role": "system", "content": generation_params["system_prompt"]}
        )
    messages.append({"role": "user", "content": prompt_text})
    return messages


def generate_text(
    tokenizer: Any,
    model: Any,
    prompt_text: str,
    generation_params: ConfigDict,
) -> str:
    """Genera la resposta del model per a un prompt."""
    messages = build_messages(prompt_text, generation_params)
    if getattr(tokenizer, "chat_template", None):
        formatted_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    else:
        formatted_prompt = "\n\n".join(
            message["content"] for message in messages if message["content"]
        )

    inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)

    generation_kwargs = {
        "max_new_tokens": generation_params["max_new_tokens"],
        "do_sample": generation_params["temperature"] > 0,
        "remove_invalid_values": True,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if generation_kwargs["do_sample"]:
        generation_kwargs["temperature"] = generation_params["temperature"]
        generation_kwargs["top_p"] = generation_params["top_p"]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            **generation_kwargs,
        )

    input_len = inputs.input_ids.shape[1]
    generated_tokens = outputs[0][input_len:]
    return tokenizer.decode(generated_tokens, skip_special_tokens=True)


def build_result(
    prompt: Prompt,
    model_entry: ConfigDict,
    generation_params: ConfigDict,
    global_config: ConfigDict,
    generated_text: str,
    current_timestamp: str,
    git_commit: str,
) -> ConfigDict:
    """Construeix el document YAML de sortida d'una inferència."""
    model_name = get_model_name(model_entry)
    reasoning, final_answer = split_reasoning(generated_text)

    return {
        "run": {
            "timestamp": current_timestamp,
            "git_commit": git_commit,
            "seed": global_config["seed"],
        },
        "prompt": {
            "id": prompt["id"],
            "path": prompt["_path_origen"],
            "sha256": calculate_sha256(prompt["text"]),
        },
        "model": {
            "id": model_entry["id"],
            "model_name": model_name,
            "revision": model_entry["revision"],
        },
        "generation": {
            "temperature": generation_params["temperature"],
            "top_p": generation_params["top_p"],
            "max_new_tokens": generation_params["max_new_tokens"],
            "seed": global_config["seed"],
        },
        "backend": {
            "engine": global_config["backend_preferit"],
            "transformers_version": str(transformers.__version__),
            "torch_version": str(torch.__version__),
        },
        "output": {
            "answer": final_answer,
        },
        "reasoning": {
            "content": reasoning,
        },
    }


def save_result(
    result_yaml: ConfigDict,
    output_dir: Path,
    prompt_id: str,
) -> Path:
    """Desa una inferència en YAML i retorna el camí escrit."""
    output_dir.mkdir(parents=True, exist_ok=True)
    target_file = output_dir / f"{prompt_id}.yaml"
    with target_file.open("w", encoding="utf-8") as output_file:
        yaml.dump(
            result_yaml,
            output_file,
            default_flow_style=False,
            allow_unicode=True,
        )
    return target_file


def release_model(model: Any, tokenizer: Any) -> None:
    """Allibera referències del model i buida la cache CUDA si existeix."""
    del model
    del tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def run_prompt(
    prompt: Prompt,
    model_entry: ConfigDict,
    tokenizer: Any,
    model: Any,
    generation_params: ConfigDict,
    global_config: ConfigDict,
    run_context: ConfigDict,
) -> ConfigDict:
    """Executa un prompt i retorna el resultat serialitzable."""
    generated_text = generate_text(
        tokenizer, model, prompt["text"], generation_params
    )
    return build_result(
        prompt,
        model_entry,
        generation_params,
        global_config,
        generated_text,
        run_context["timestamp"],
        run_context["git_commit"],
    )


def run_model(
    model_entry: ConfigDict,
    prompt_list: list[Prompt],
    generation_params: ConfigDict,
    global_config: ConfigDict,
    run_context: ConfigDict,
    root: Path = REPO_ROOT,
    hf_token: str | None = None,
    tokenizer_loader: Loader = AutoTokenizer.from_pretrained,
    model_loader: Loader = AutoModelForCausalLM.from_pretrained,
) -> None:
    """Executa tots els prompts per a un model configurat."""
    model_id = model_entry["id"]
    model_name = get_model_name(model_entry)
    print(f"\n--- Carregant model: {model_id} ({model_name}) ---")

    tokenizer = load_tokenizer(
        model_entry,
        hf_token=hf_token,
        tokenizer_loader=tokenizer_loader,
    )
    model = load_model(
        model_entry,
        hf_token=hf_token,
        model_loader=model_loader,
    )
    output_dir = (
        resolve_config_dir(
            global_config, "dir_sortida", "data/inferencies/v1", root
        )
        / model_id
    )

    try:
        for prompt in prompt_list:
            prompt_id = prompt["id"]
            print(f"Executant prompt {prompt_id}...")
            result_yaml = run_prompt(
                prompt,
                model_entry,
                tokenizer,
                model,
                generation_params,
                global_config,
                run_context,
            )
            save_result(result_yaml, output_dir, prompt_id)
    finally:
        release_model(model, tokenizer)


def run_pipeline(
    root: Path = REPO_ROOT,
    device_map: str | None = None,
    tokenizer_loader: Loader = AutoTokenizer.from_pretrained,
    model_loader: Loader = AutoModelForCausalLM.from_pretrained,
) -> None:
    """Executa la canonada completa d'inferència."""
    config = apply_device_map_override(load_config(root), device_map)
    global_config = config["configuracio_global"]
    generation_params = config["parametres_generacio"]
    hf_token = os.getenv("HF_TOKEN")
    run_context = {
        "git_commit": get_git_commit(),
        "timestamp": timestamp_utc(),
    }

    torch.manual_seed(global_config["seed"])

    prompt_list = load_prompts(
        discover_prompt_files(global_config, root=root),
        root=root,
    )
    if len(prompt_list) == 0:
        print("Error: No s'han trobat prompts")
        return

    print(f"S'han trobat {len(prompt_list)} prompts per processar.")

    for model_entry in config["models"]:
        run_model(
            model_entry,
            prompt_list,
            generation_params,
            global_config,
            run_context,
            root=root,
            hf_token=hf_token,
            tokenizer_loader=tokenizer_loader,
            model_loader=model_loader,
        )


def parse_args() -> argparse.Namespace:
    """Llegeix els paràmetres CLI de la canonada d'inferència."""
    parser = argparse.ArgumentParser(
        description="Executa la canonada d'inferència d'Arena Cat.",
    )
    parser.add_argument(
        "--device-map",
        choices=("auto", "cpu"),
        help=(
            "Sobreescriu el device_map de tots els models. "
            "Si cal més control en el futur, es poden afegir nous paràmetres CLI."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(device_map=args.device_map)
