# Esquema de la base de dades

Diagrama ER de l'esquema de dades d'Arena Cat.

> Font: [`backend/app/models.py`](../backend/app/models.py) — sincronitzeu el diagrama quan canviï l'esquema.

```mermaid
erDiagram
    prompts {
        integer id PK
        varchar(32) versio
        varchar(64) codi
        categoria_tasca categoria
        text text
        timestamptz creat_a
    }

    respostes {
        integer id PK
        integer prompt_id FK
        varchar(128) model
        text text
        jsonb metadades
        timestamptz creat_a
    }

    vots {
        bigint id PK
        integer prompt_id FK
        integer resposta_a_id FK
        integer resposta_b_id FK
        guanyador guanyador
        varchar(128) sessio_id
        numeric(6_2) temps_resposta_s
        timestamptz creat_a
    }

    prompts ||--o{ respostes : "prompt_id"
    prompts ||--o{ vots : "prompt_id"
    respostes ||--o{ vots : "resposta_a_id"
    respostes ||--o{ vots : "resposta_b_id"
```

## Restriccions i índexs

| Taula | Tipus | Nom | Definició |
|-------|-------|-----|-----------|
| prompts | UNIQUE | `uq_prompts_versio_codi` | `(versio, codi)` |
| respostes | UNIQUE | `uq_respostes_prompt_model` | `(prompt_id, model)` |
| respostes | FK | — | `prompt_id → prompts.id` `ON DELETE CASCADE` |
| vots | CHECK | `ck_vots_respostes_diferents` | `resposta_a_id <> resposta_b_id` |
| vots | FK | — | `prompt_id → prompts.id` |
| vots | FK | — | `resposta_a_id → respostes.id` |
| vots | FK | — | `resposta_b_id → respostes.id` |
| vots | INDEX | `ix_vots_prompt_id` | `prompt_id` |
| vots | INDEX | `ix_vots_creat_a` | `creat_a` |

## Enums

- **`categoria_tasca`**: `correccio`, `reformulacio`, `traduccio`
- **`guanyador`**: `a`, `b`, `empat`, `cap`
