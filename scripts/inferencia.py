# La canonada (pipeline) d'inferència amb Hugging Face

import argparse
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
import hashlib
import logging
import os
from pathlib import Path
import subprocess
import time
from typing import Any

import torch
import transformers
import yaml
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ConfigDict = dict[str, Any]
Prompt = dict[str, Any]
Loader = Callable[..., Any]
ENV_HF_TOKEN = "HF_TOKEN"
DEFAULT_INFERENCIA_CONFIG = "config/inferencia/inferencia_config.yaml"
LOGGER = logging.getLogger(__name__)


# Utilitats generals
def get_git_commit() -> str:
    """Retorna el commit Git actual.

    Returns:
        Hash del commit actual o un marcador estable si el directori no és un
        repositori Git.
    """
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


def timestamp_utc() -> str:
    """Genera el timestamp UTC actual.

    Returns:
        Timestamp en format ISO-8601 amb sufix ``Z``.
    """
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


# Configuració
def load_config(
    root: Path = REPO_ROOT,
    config_path: str | Path = DEFAULT_INFERENCIA_CONFIG,
) -> ConfigDict:
    """Llegeix la configuració d'inferència activa.

    Args:
        root: Arrel del repositori usada per resoldre camins relatius.
        config_path: Fitxer YAML de configuració.

    Returns:
        Configuració carregada des del YAML actiu.
    """
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = root / config_path

    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def apply_device_map_override(
    config: ConfigDict,
    device_map: str | None,
) -> ConfigDict:
    """Aplica una sobreescriptura de ``device_map`` a tots els models.

    Args:
        config: Configuració d'inferència carregada.
        device_map: Valor CLI que substitueix el ``device_map`` de cada model,
            o ``None`` si cal mantenir la configuració.

    Returns:
        La mateixa configuració, amb els models actualitzats si escau.
    """
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
    """Resol un directori configurat.

    Args:
        global_config: Bloc global de configuració.
        key: Clau del directori dins del bloc global.
        default_value: Valor per defecte si la clau no existeix.
        root: Arrel del repositori usada per camins relatius.

    Returns:
        Camí absolut o relatiu resolt contra l'arrel del repositori.
    """
    base_dir = Path(global_config.get(key, default_value))
    return base_dir if base_dir.is_absolute() else root / base_dir


# Prompts
def discover_prompt_files(
    global_config: ConfigDict | str | Path | None = None,
    root: Path = REPO_ROOT,
) -> list[Path]:
    """Descobreix els fitxers de prompts.

    Args:
        global_config: Configuració global o arrel antiga acceptada per
            compatibilitat amb tests.
        root: Arrel del repositori usada per resoldre camins relatius.

    Returns:
        Llista ordenada de fitxers de prompt (``*.txt``).
    """
    if isinstance(global_config, (str, Path)):
        root = Path(global_config)
        global_config = {}
    elif global_config is None:
        global_config = {}

    prompts_dir = resolve_config_dir(
        global_config, "dir_prompts", "data/prompts/v1", root
    )
    return sorted(prompts_dir.glob("*.txt"))


def load_prompts(
    prompt_files: Iterable[Path],
    root: Path = REPO_ROOT,
) -> list[Prompt]:
    """Carrega prompts des de fitxers de text pla.

    Cada fitxer és un ``.txt`` on el nom (sense extensió) és l'identificador i
    el contingut sencer és el text del prompt.

    Args:
        prompt_files: Fitxers de prompt a llegir.
        root: Arrel usada per guardar el camí relatiu d'origen.

    Returns:
        Llista de prompts amb el camp ``_path_origen``.
    """
    prompt_list = []
    for prompt_file in prompt_files:
        text = prompt_file.read_text(encoding="utf-8")
        prompt_list.append(
            {
                "id": prompt_file.stem,
                "text": text,
                "_path_origen": str(prompt_file.relative_to(root)),
            }
        )
    return prompt_list


# Models
def get_model_name(model_entry: ConfigDict) -> str:
    """Obtè el nom Hugging Face d'un model.

    Args:
        model_entry: Configuració d'un model.

    Returns:
        Nom del model compatible amb Hugging Face.
    """
    return (
        model_entry["name"]
        if "name" in model_entry
        else model_entry["model_name"]
    )


def get_dtype(torch_dtype: str) -> Any:
    """Converteix el nom de dtype configurat al dtype de PyTorch.

    Args:
        torch_dtype: Nom del dtype configurat.

    Returns:
        Dtype de PyTorch corresponent.

    Raises:
        ValueError: Si el dtype configurat no està suportat.
    """
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
    """Carrega el tokenizer del model configurat.

    Args:
        model_entry: Configuració d'un model.
        hf_token: Token de Hugging Face, si n'hi ha.
        tokenizer_loader: Funció injectable per carregar tokenitzadors.

    Returns:
        Tokenitzador carregat.
    """
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
    """Carrega el model configurat.

    Args:
        model_entry: Configuració d'un model.
        hf_token: Token de Hugging Face, si n'hi ha.
        model_loader: Funció injectable per carregar models.

    Returns:
        Model carregat.

    Raises:
        ValueError: Si la quantització o el ``torch_dtype`` no estan suportats.
    """
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


def release_model(model: Any, tokenizer: Any) -> None:
    """Allibera recursos del model.

    És útil sobretot amb GPU i múltiples models, perquè redueix el risc
    d'esgotar la memòria CUDA abans de carregar el model següent.

    Args:
        model: Model carregat.
        tokenizer: Tokenitzador carregat.
    """
    del model
    del tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# Generació
def build_messages(
    prompt_text: str, generation_params: ConfigDict
) -> list[ConfigDict]:
    """Construeix els missatges de xat.

    Args:
        prompt_text: Text del prompt d'usuari.
        generation_params: Paràmetres de generació.

    Returns:
        Missatges en format compatible amb plantilles de xat.
    """
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
    """Genera text per a un prompt.

    Args:
        tokenizer: Tokenitzador del model.
        model: Model carregat.
        prompt_text: Text del prompt.
        generation_params: Paràmetres de generació.

    Returns:
        Text generat pel model.
    """
    messages = build_messages(prompt_text, generation_params)
    if getattr(tokenizer, "chat_template", None):
        try:
            formatted_prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
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


# Resultats
def calculate_sha256(text: str) -> str:
    """Calcula el SHA-256 d'un text.

    Args:
        text: Text d'entrada.

    Returns:
        Hash SHA-256 codificat en hexadecimal.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_reasoning(text: str) -> tuple[str | None, str]:
    """Separa el raonament intern de la resposta final.

    Args:
        text: Text generat pel model.

    Returns:
        Tupla amb el raonament detectat, si existeix, i la resposta final
        visible per a l'avaluador.
    """
    if "<think>" in text and "</think>" in text:
        parts = text.split("</think>")
        reasoning = parts[0].replace("<think>", "").strip()
        clean_answer = parts[1].strip()
        return reasoning, clean_answer
    return None, text.strip()


def build_result(
    prompt: Prompt,
    model_entry: ConfigDict,
    generation_params: ConfigDict,
    global_config: ConfigDict,
    generated_text: str,
    current_timestamp: str,
    git_commit: str,
) -> ConfigDict:
    """Construeix el document de sortida d'una inferència.

    Args:
        prompt: Prompt executat.
        model_entry: Configuració del model.
        generation_params: Paràmetres de generació.
        global_config: Configuració global.
        generated_text: Text generat pel model.
        current_timestamp: Timestamp de l'execució.
        git_commit: Commit Git de l'execució.

    Returns:
        Diccionari serialitzable a YAML.
    """
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
    """Desa una inferència en YAML.

    Args:
        result_yaml: Resultat serialitzable.
        output_dir: Directori de sortida.
        prompt_id: Identificador del prompt.

    Returns:
        Camí del fitxer escrit.
    """
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


# Execució
def run_prompt(
    prompt: Prompt,
    model_entry: ConfigDict,
    tokenizer: object,
    model: object,
    generation_params: ConfigDict,
    global_config: ConfigDict,
    run_context: ConfigDict,
) -> ConfigDict:
    """Executa un prompt amb un model carregat.

    Args:
        prompt: Prompt a executar.
        model_entry: Configuració del model.
        tokenizer: Tokenitzador carregat.
        model: Model carregat.
        generation_params: Paràmetres de generació.
        global_config: Configuració global.
        run_context: Metadades de l'execució.

    Returns:
        Resultat serialitzable del prompt.
    """
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
) -> float | None:
    """Executa tots els prompts per a un model configurat.

    Args:
        model_entry: Configuració del model.
        prompt_list: Prompts a executar.
        generation_params: Paràmetres de generació.
        global_config: Configuració global.
        run_context: Metadades de l'execució.
        root: Arrel del repositori.
        hf_token: Token de Hugging Face, si n'hi ha.
        tokenizer_loader: Funció injectable per carregar tokenitzadors.
        model_loader: Funció injectable per carregar models.

    Returns:
        Temps mitjà d'inferència per prompt en segons, o ``None`` si no s'ha
        executat cap prompt.
    """
    model_id = model_entry["id"]
    model_name = get_model_name(model_entry)
    LOGGER.info("Carregant model: %s (%s)", model_id, model_name)

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

    inference_times: list[float] = []
    try:
        for prompt in prompt_list:
            prompt_id = prompt["id"]
            LOGGER.info("Executant prompt %s", prompt_id)
            start_time = time.perf_counter()
            result_yaml = run_prompt(
                prompt,
                model_entry,
                tokenizer,
                model,
                generation_params,
                global_config,
                run_context,
            )
            inference_times.append(time.perf_counter() - start_time)
            save_result(result_yaml, output_dir, prompt_id)
    finally:
        release_model(model, tokenizer)

    if not inference_times:
        return None
    return sum(inference_times) / len(inference_times)


class InferencePipeline:
    """Orquestra l'execució completa de la canonada d'inferència.

    Args:
        root: Arrel del repositori.
        config_path: Fitxer YAML de configuració.
        device_map: Valor opcional per sobreescriure el ``device_map`` dels
            models configurats.
        tokenizer_loader: Funció injectable per carregar tokenitzadors.
        model_loader: Funció injectable per carregar models.
    """

    def __init__(
        self,
        root: Path = REPO_ROOT,
        config_path: str | Path = DEFAULT_INFERENCIA_CONFIG,
        device_map: str | None = None,
        tokenizer_loader: Loader = AutoTokenizer.from_pretrained,
        model_loader: Loader = AutoModelForCausalLM.from_pretrained,
    ) -> None:
        """Inicialitza la canonada d'inferència.

        Args:
            root: Arrel del repositori.
            config_path: Fitxer YAML de configuració.
            device_map: Valor opcional per sobreescriure el ``device_map``.
            tokenizer_loader: Funció injectable per carregar tokenitzadors.
            model_loader: Funció injectable per carregar models.
        """
        self.root = root
        self.config_path = config_path
        self.device_map = device_map
        self.tokenizer_loader = tokenizer_loader
        self.model_loader = model_loader

    def run(self) -> None:
        """Executa la canonada d'inferència.

        Carrega la configuració, descobreix prompts i executa cada model
        configurat.
        """
        config = apply_device_map_override(
            load_config(self.root, self.config_path), self.device_map
        )
        global_config = config["configuracio_global"]
        generation_params = config["parametres_generacio"]
        hf_token = os.getenv(ENV_HF_TOKEN, None)
        run_context = {
            "git_commit": get_git_commit(),
            "timestamp": timestamp_utc(),
        }

        torch.manual_seed(global_config["seed"])

        prompt_list = load_prompts(
            discover_prompt_files(global_config, root=self.root),
            root=self.root,
        )
        if len(prompt_list) == 0:
            LOGGER.error("No s'han trobat prompts")
            return

        LOGGER.info("S'han trobat %s prompts per processar.", len(prompt_list))

        avg_times: dict[str, float] = {}
        for model_entry in config["models"]:
            avg_time = run_model(
                model_entry,
                prompt_list,
                generation_params,
                global_config,
                run_context,
                root=self.root,
                hf_token=hf_token,
                tokenizer_loader=self.tokenizer_loader,
                model_loader=self.model_loader,
            )
            if avg_time is not None:
                avg_times[model_entry["id"]] = avg_time

        if avg_times:
            LOGGER.info("Temps mitjà d'inferència per model:")
            for model_id, avg_time in avg_times.items():
                LOGGER.info("  %s: %.2f s/prompt", model_id, avg_time)


def run_pipeline(
    root: Path = REPO_ROOT,
    config_path: str | Path = DEFAULT_INFERENCIA_CONFIG,
    device_map: str | None = None,
    tokenizer_loader: Loader = AutoTokenizer.from_pretrained,
    model_loader: Loader = AutoModelForCausalLM.from_pretrained,
) -> None:
    """Executa la canonada completa d'inferència.

    Args:
        root: Arrel del repositori.
        config_path: Fitxer YAML de configuració.
        device_map: Valor opcional per sobreescriure el ``device_map`` dels
            models configurats.
        tokenizer_loader: Funció injectable per carregar tokenitzadors.
        model_loader: Funció injectable per carregar models.
    """
    InferencePipeline(
        root=root,
        config_path=config_path,
        device_map=device_map,
        tokenizer_loader=tokenizer_loader,
        model_loader=model_loader,
    ).run()


# CLI
def parse_args() -> argparse.Namespace:
    """Llegeix els paràmetres CLI.

    Returns:
        Namespace amb els paràmetres de la línia d'ordres.
    """
    parser = argparse.ArgumentParser(
        description="Executa la canonada d'inferència d'Arena Cat.",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_INFERENCIA_CONFIG,
        help="Fitxer YAML de configuració d'inferència.",
    )
    parser.add_argument(
        "--device-map",
        choices=("auto", "cpu"),
        help=(
            "Sobreescriu el device_map de tots els models. "
            "Si cal més control en el futur, es poden afegir nous paràmetres CLI."
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Nivell mínim dels missatges de logging.",
    )
    return parser.parse_args()


def main() -> None:
    """Executa el punt d'entrada CLI de la canonada."""
    args = parse_args()
    logging.basicConfig(
        level=args.log_level, format="%(levelname)s:%(name)s:%(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    run_pipeline(config_path=args.config, device_map=args.device_map)


if __name__ == "__main__":
    main()
