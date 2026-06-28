
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

Per sobreescriure el dispositiu (device-map) definit a la configuració:

```bash
uv run python scripts/inferencia.py --device-map cpu
```
Si més endavant cal controlar altres opcions adicionals, com el dtype o la quantització,
es poden afegir nous paràmetres específics.


Per fer servir un fitxer de configuració alternatiu:

```bash
uv run python scripts/inferencia.py --config config/inferencia/inferencia_local_config.yaml
```

Els missatges de progrés fan servir `logging` i es poden reduir ajustant el
nivell de logging.


Per veure només avisos i errors:

```bash
uv run python scripts/inferencia.py --log-level WARNING
```

Els resultats es desen a `data/inferencies/v1/<model_id>/`.

### 6. Mètriques de distància entre sortides

`scripts/metriques.py` calcula com de diferents són les sortides dels diferents
models per a un mateix prompt. Serveix per detectar prompts on els models
generen respostes massa semblants — i, per tant, on un avaluador humà no podrà
distingir-les fàcilment.

Per a cada parella de models imprimeix dues mètriques **normalitzades a
distància** (0 = sortides idèntiques, 1 = totalment diferents) i la seva
mitjana:

- **chrF_d**: `1 − chrF/100` (n-grames de caràcters).
- **edit**: Levenshtein normalitzat a caràcter.
- **combinat**: mitjana de les dues anteriors, com a resum d'un cop d'ull.

A més de la mitjana de les parelles, mostra la **parella pitjor** (la més
semblant del trio, mínim de les distàncies), que delata si dos models continuen
sonant igual encara que la mitjana sigui alta.

```bash
uv run python scripts/metriques.py
uv run python scripts/metriques.py --inferencies data/inferencies/hypotheses
```

### 7. Prova local amb un model molt petit

Per comprovar el flux complet sense carregar cap model gran, pots usar la configuració local:

```bash
uv run python scripts/inferencia.py --config config/inferencia/inferencia_local_config.yaml
```

Aquesta configuració fa servir `hf-internal-testing/tiny-random-gpt2`, un model de prova molt petit. Serveix per validar que la descàrrega, la càrrega del model, la generació i l'escriptura dels YAML funcionen, però no per avaluar qualitat lingüística.
