
## Executar la canonada d'inferència

El projecte fa servir [`uv`](https://docs.astral.sh/uv/) per gestionar l'entorn Python i les dependències.

### 1. Instal·lar `uv`

Si no el tens instal·lat:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Crear l'entorn i instal·lar dependències

Des de l'arrel del repositori:

```bash
uv sync
```

Això crea l'entorn virtual `.venv/` i instal·la les dependències definides a `pyproject.toml`.

### 3. Configurar el token de Hugging Face

Crea un fitxer local `.env` a partir de l'exemple:

```bash
cp .env.example .env
```

Edita `.env` i afegeix-hi el teu token:

```env
HF_TOKEN=hf_el_teu_token
```

El fitxer `.env` és local i no s'ha de versionar.

### 4. Executar els tests

```bash
uv run python -m unittest discover -s tests
```

Els tests fan servir dobles de prova (*mocks/stubs*) per al model i el tokenitzador, de manera que no descarreguen models de Hugging Face.

### 5. Executar la inferència

Abans d'executar-la, revisa `config/inferencia/inferencia_config.yaml` i comprova que els models, els paràmetres de generació i els prompts són els esperats.

```bash
uv run python scripts/inferencia.py
```

Els resultats es desen a `data/inferencies/v1/<model_id>/`.

### 6. Prova local amb un model molt petit

Per comprovar el flux complet sense carregar cap model gran, pots usar la configuració local:

```bash
INFERENCIA_CONFIG=config/inferencia/inferencia_local_config.yaml uv run python scripts/inferencia.py
```

Aquesta configuració fa servir `hf-internal-testing/tiny-random-gpt2`, un model de prova molt petit. Serveix per validar que la descàrrega, la càrrega del model, la generació i l'escriptura dels YAML funcionen, però no per avaluar qualitat lingüística.

### 7. Prova local en CPU amb 16 GB de RAM

Per provar el flux amb un model petit però real:

```bash
INFERENCIA_CONFIG=config/inferencia/inferencia_cpu_config.yaml uv run python scripts/inferencia.py
```

Aquesta configuració fa servir `Qwen/Qwen2.5-0.5B-Instruct` en CPU, sense quantització `bitsandbytes`.
