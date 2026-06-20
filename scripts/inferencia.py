# La canonada (pipeline) d'inferència amb Hugging Face

import os
from pathlib import Path
import yaml
import hashlib
from datetime import UTC, datetime
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]

def carregar_env(path):
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

carregar_env(REPO_ROOT / ".env")

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

def get_git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
        ).decode("ascii").strip()
    except Exception:
        return "not_a_git_repository"

def calcular_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def timestamp_utc():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")

def separar_raonament(text):
    """
    Detecta estructures de pensament tipus <think>...</think> i les separa
    de la resposta final visible per a l'avaluador.
    """
    if "<think>" in text and "</think>" in text:
        parts = text.split("</think>")
        raonament = parts[0].replace("<think>", "").strip()
        resposta_neta = parts[1].strip()
        return raonament, resposta_neta
    return None, text.strip()

def carregar_config(root=REPO_ROOT):
    config_path = Path(os.getenv("INFERENCIA_CONFIG", "config/inferencia_config.yaml"))
    if not config_path.is_absolute():
        config_path = root / config_path

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def resoldre_dir_config(cfg_global, clau, valor_per_defecte, root=REPO_ROOT):
    dir_base = Path(cfg_global.get(clau, valor_per_defecte))
    return dir_base if dir_base.is_absolute() else root / dir_base

def descobrir_prompt_files(cfg_global=None, root=REPO_ROOT):
    if isinstance(cfg_global, (str, Path)):
        root = Path(cfg_global)
        cfg_global = {}
    elif cfg_global is None:
        cfg_global = {}

    dir_prompts = resoldre_dir_config(cfg_global, "dir_prompts", "data/prompts/v1", root)
    return sorted(dir_prompts.glob("*.yaml"))

# TODO: potser es pot simplificar quan el format dels prompts es definit?
def carregar_prompts(prompt_files, root=REPO_ROOT):
    llista_prompts = []
    for pf in prompt_files:
        with pf.open("r", encoding="utf-8") as f:
            dades = yaml.safe_load(f)

        if isinstance(dades, list):
            prompts = dades
        elif isinstance(dades, dict):
            prompts = [dades]
        elif isinstance(dades, str):
            prompts = [{"id": pf.stem, "text": dades}]
        else:
            continue

        for prompt in prompts:
            prompt["_path_origen"] = str(pf.relative_to(root))
            llista_prompts.append(prompt)

    return llista_prompts

def obtenir_model_name(entry_model):
    return entry_model["name"] if "name" in entry_model else entry_model["model_name"]

def obtenir_dtype(torch_dtype):
    dtype_map = {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }

    if torch_dtype not in dtype_map:
        opcions = ", ".join(sorted(dtype_map))
        raise ValueError(f"torch_dtype no suportat: {torch_dtype}. Opcions: {opcions}")

    return dtype_map[torch_dtype]

def carregar_tokenizer(entry_model, hf_token=None, tokenizer_loader=AutoTokenizer.from_pretrained):
    return tokenizer_loader(
        obtenir_model_name(entry_model),
        revision=entry_model["revision"],
        token=hf_token,
    )

def carregar_model(entry_model, hf_token=None, model_loader=AutoModelForCausalLM.from_pretrained):
    dtype = obtenir_dtype(entry_model["torch_dtype"])
    device_map = entry_model["device_map"]
    kwargs = {
        "revision": entry_model["revision"],
        "dtype": dtype,
        "device_map": device_map,
        "token": hf_token,
    }

    quantization = entry_model.get("quantization")
    if quantization == "4bit":
        if isinstance(device_map, dict) and {"cpu", "disk"} & set(device_map.values()):
            raise ValueError("4bit no suporta offload a CPU/disc en aquesta configuracio. Usa device_map: {'': 0}.")
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=dtype,
            bnb_4bit_quant_type=entry_model.get("bnb_4bit_quant_type", "nf4"),
            bnb_4bit_use_double_quant=entry_model.get("bnb_4bit_use_double_quant", True),
        )
    elif quantization not in (None, "none"):
        raise ValueError(f"quantization no suportada: {quantization}. Opcions: 4bit, none")

    return model_loader(obtenir_model_name(entry_model), **kwargs)

def construir_missatges(prompt_text, params_gen):
    missatges = []
    if params_gen.get("system_prompt"):
        missatges.append({"role": "system", "content": params_gen["system_prompt"]})
    missatges.append({"role": "user", "content": prompt_text})
    return missatges

def generar_text(tokenizer, model, prompt_text, params_gen):
    missatges = construir_missatges(prompt_text, params_gen)
    if getattr(tokenizer, "chat_template", None):
        prompt_formatat = tokenizer.apply_chat_template(
            missatges,
            tokenize=False,
            add_generation_prompt=True,
        )
    else:
        prompt_formatat = "\n\n".join(missatge["content"] for missatge in missatges if missatge["content"])

    inputs = tokenizer(prompt_formatat, return_tensors="pt").to(model.device)

    generation_kwargs = {
        "max_new_tokens": params_gen["max_new_tokens"],
        "do_sample": params_gen["temperature"] > 0,
        "remove_invalid_values": True,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if generation_kwargs["do_sample"]:
        generation_kwargs["temperature"] = params_gen["temperature"]
        generation_kwargs["top_p"] = params_gen["top_p"]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            **generation_kwargs,
        )

    input_len = inputs.input_ids.shape[1]
    tokens_generats = outputs[0][input_len:]
    return tokenizer.decode(tokens_generats, skip_special_tokens=True)

def construir_resultat(
    prompt,
    entry_model,
    params_gen,
    cfg_global,
    text_generat,
    timestamp_actual,
    git_commit,
):
    model_name = obtenir_model_name(entry_model)
    raonament, resposta_final = separar_raonament(text_generat)

    return {
        "run": {
            "timestamp": timestamp_actual,
            "git_commit": git_commit,
            "seed": cfg_global["seed"],
        },
        "prompt": {
            "id": prompt["id"],
            "path": prompt["_path_origen"],
            "sha256": calcular_sha256(prompt["text"]),
        },
        "model": {
            "id": entry_model["id"],
            "model_name": model_name,
            "revision": entry_model["revision"],
        },
        "generation": {
            "temperature": params_gen["temperature"],
            "top_p": params_gen["top_p"],
            "max_new_tokens": params_gen["max_new_tokens"],
            "seed": cfg_global["seed"],
        },
        "backend": {
            "engine": cfg_global["backend_preferit"],
            "transformers_version": str(transformers.__version__),
            "torch_version": str(torch.__version__),
        },
        "output": {
            "answer": resposta_final,
        },
        "reasoning": {
            "content": raonament,
        },
    }

def desar_resultat(resultat_yaml, dir_sortida, prompt_id):
    dir_sortida.mkdir(parents=True, exist_ok=True)
    fitxer_desti = dir_sortida / f"{prompt_id}.yaml"
    with fitxer_desti.open("w", encoding="utf-8") as out_f:
        yaml.dump(resultat_yaml, out_f, default_flow_style=False, allow_unicode=True)
    return fitxer_desti

def alliberar_model(model, tokenizer):
    del model
    del tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def executar_prompt(prompt, entry_model, tokenizer, model, params_gen, cfg_global, run_context):
    text_generat = generar_text(tokenizer, model, prompt["text"], params_gen)
    return construir_resultat(
        prompt,
        entry_model,
        params_gen,
        cfg_global,
        text_generat,
        run_context["timestamp"],
        run_context["git_commit"],
    )

def executar_model(
    entry_model,
    llista_prompts,
    params_gen,
    cfg_global,
    run_context,
    root=REPO_ROOT,
    hf_token=None,
    tokenizer_loader=AutoTokenizer.from_pretrained,
    model_loader=AutoModelForCausalLM.from_pretrained,
):
    model_id = entry_model["id"]
    model_name = obtenir_model_name(entry_model)
    print(f"\n--- Carregant model: {model_id} ({model_name}) ---")

    tokenizer = carregar_tokenizer(
        entry_model,
        hf_token=hf_token,
        tokenizer_loader=tokenizer_loader,
    )
    model = carregar_model(
        entry_model,
        hf_token=hf_token,
        model_loader=model_loader,
    )
    dir_sortida = resoldre_dir_config(cfg_global, "dir_sortida", "data/inferencies/v1", root) / model_id

    try:
        for prompt in llista_prompts:
            prompt_id = prompt["id"]
            print(f"Executant prompt {prompt_id}...")
            resultat_yaml = executar_prompt(
                prompt,
                entry_model,
                tokenizer,
                model,
                params_gen,
                cfg_global,
                run_context,
            )
            desar_resultat(resultat_yaml, dir_sortida, prompt_id)
    finally:
        alliberar_model(model, tokenizer)

def executar_pipeline(
    root=REPO_ROOT,
    tokenizer_loader=AutoTokenizer.from_pretrained,
    model_loader=AutoModelForCausalLM.from_pretrained,
):
    config = carregar_config(root)
    cfg_global = config["configuracio_global"]
    params_gen = config["parametres_generacio"]
    hf_token = os.getenv("HF_TOKEN")
    run_context = {
        "git_commit": get_git_commit(),
        "timestamp": timestamp_utc(),
    }

    torch.manual_seed(cfg_global["seed"])

    llista_prompts = carregar_prompts(descobrir_prompt_files(cfg_global, root=root), root=root)
    if len(llista_prompts) == 0:
        print("Error: No s'han trobat prompts")
        return

    print(f"S'han trobat {len(llista_prompts)} prompts per processar.")

    for entry_model in config["models"]:
        executar_model(
            entry_model,
            llista_prompts,
            params_gen,
            cfg_global,
            run_context,
            root=root,
            hf_token=hf_token,
            tokenizer_loader=tokenizer_loader,
            model_loader=model_loader,
        )

if __name__ == "__main__":
    executar_pipeline()
