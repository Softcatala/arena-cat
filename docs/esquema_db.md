# Esquema de la base de dades

Diagrama ER de l'esquema de dades d'Arena Cat.

> Font: [`backend/app/models.py`](../backend/app/models.py).

```mermaid
erDiagram
    categories {
        integer id PK
        varchar(64) code
        varchar(128) name
        text description
    }

    prompts {
        integer id PK
        varchar(32) version
        varchar(64) code
        integer category_id FK
        text text
        timestamptz created_at
    }

    responses {
        integer id PK
        integer prompt_id FK
        varchar(128) model
        text text
        jsonb inference_metadata
        timestamptz created_at
    }

    votes {
        bigint id PK
        integer prompt_id FK
        integer response_a_id FK
        integer response_b_id FK
        winner winner
        varchar(128) session_id
        numeric(6_2) response_time_s
        timestamptz created_at
    }

    categories ||--o{ prompts : "category_id"
    prompts ||--o{ responses : "prompt_id"
    prompts ||--o{ votes : "prompt_id"
    responses ||--o{ votes : "response_a_id"
    responses ||--o{ votes : "response_b_id"
```

## Restriccions i índexs

| Taula | Tipus | Nom | Definició |
|-------|-------|-----|-----------|
| categories | UNIQUE | — | `(code)` |
| prompts | UNIQUE | `uq_prompts_version_code` | `(version, code)` |
| prompts | FK | — | `category_id → categories.id` |
| responses | UNIQUE | `uq_responses_prompt_model` | `(prompt_id, model)` |
| responses | UNIQUE | `uq_responses_prompt_id_id` | `(prompt_id, id)` |
| responses | FK | — | `prompt_id → prompts.id` `ON DELETE CASCADE` |
| votes | CHECK | `ck_votes_responses_different` | `response_a_id <> response_b_id` |
| votes | FK | — | `prompt_id → prompts.id` |
| votes | FK | `fk_votes_response_a` | `(prompt_id, response_a_id) → responses(prompt_id, id)` |
| votes | FK | `fk_votes_response_b` | `(prompt_id, response_b_id) → responses(prompt_id, id)` |
| votes | INDEX | `ix_votes_prompt_id` | `prompt_id` |
| votes | INDEX | `ix_votes_created_at` | `created_at` |

## Enums

- **`winner`**: `a`, `b`, `tie`, `neither`
