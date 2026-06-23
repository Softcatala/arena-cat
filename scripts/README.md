
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

L'script llegeix el token des de la variable d'entorn `HF_TOKEN`. Exporta-la
amb el mecanisme que prefereixis per al teu entorn:

```bash
export HF_TOKEN=hf_el_teu_token
```

També pots carregar-la amb eines externes com `dotenv`, `direnv`, el teu shell,
CI o Docker. Si fas servir un fitxer `.env`, mantén-lo local i no el versionis.

El fitxer `.env.example` documenta les variables d'entorn esperades:

```bash
cp .env.example .env
```

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

Per sobreescriure el dispositiu definit a la configuració:

```bash
uv run python scripts/inferencia.py --device-map cpu
```

Actualment el CLI només controla `device_map`. Si més endavant cal controlar
altres opcions, com el dtype o la quantització, es poden afegir nous paràmetres
específics.

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
