# Dades d'inferencia

Aquesta branca actua com un contenidor versionat per a les inferencies generades
per Arena Cat. El codi de la plataforma viu a les branques de desenvolupament;
aqui nomes es desen les sortides preparades per carregar a la base de dades.

## Estructura

```text
data/inferencies/<version>/<model_id>/<prompt_code>.yaml
```

La versio inicial es `v1` i conte inferencies per als models:

- `gemma-3-27b-it`
- `mistral-small-3.2-24b-instruct-2506`
- `qwen-3.5-9b`

Per carregar aquestes dades des del repositori principal, fes-les disponibles en
un directori local i passa'l al carregador amb `INFERENCIES_DIR`.
