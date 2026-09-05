# Pla: categories en YAML

## Objectiu

Fer que un YAML sigui la font de les categories, mantenint la categoria de cada prompt
deduïda del nom del fitxer, i exposar-les a la UI mitjançant l'API.

```text
categories.yaml → carregador → PostgreSQL → API → frontend
```

## Implementació

1. Crear `data/prompts/categories.yaml`:

   ```yaml
   categories:
     - code: correccio
       name: Correcció
       description: Corregeix aquest text.
     - code: reformulacio
       name: Reformulació
       description: Reformula aquest text.
     - code: traduccio
       name: Traducció
       description: Tradueix aquest text.
   ```

2. Ampliar `scripts/carrega_inferencies.py` perquè:

   - Llegeixi i validi el YAML abans de carregar els prompts.
   - Insereixi categories noves i actualitzi `name` o `description` si canvien.
   - No elimini categories absents del YAML, perquè poden tenir dades històriques.
   - Continuï deduint la categoria: `correccio_1.txt` → `correccio`.
   - Rebutgi categories deduïdes que no estiguin definides al catàleg.
   - Accepti `--categories-file`, amb `data/prompts/categories.yaml` per defecte.

3. Mantenir el seed i la migració inicial com a bootstrap, sense canviar `setup` ni Docker.
   El YAML se sincronitza quan s'executa `make load_inferences`.

4. Afegir l'endpoint públic `GET /api/categories`, que consulti PostgreSQL i retorni les
   categories ordenades per `code`:

   ```json
   {
     "categories": [
       {
         "code": "correccio",
         "name": "Correcció",
         "description": "Corregeix aquest text."
       }
     ]
   }
   ```

5. Adaptar `frontend/` perquè usi l'endpoint:

   - `types.ts`: afegir el tipus `Category`, convertir `CategoryCode` en `string` i eliminar
     la constant hardcoded `CATEGORIES`.
   - `api.ts`: afegir `api.categories()` per cridar `GET /categories`.
   - `App.tsx`: carregar les categories una sola vegada i passar-les a les vistes.
   - `TaskView.tsx` i `RankingView.tsx`: construir els filtres i les etiquetes amb les
     categories rebudes, mostrant un estat de càrrega o error quan calgui.

   «Qualsevol categoria» i «Global» continuaran sent opcions pròpies de la UI; no les
   retornarà el backend.

## Criteri de mínims canvis

- No modificar la taula `categories`: els camps actuals són suficients.
- Mantenir els prompts com a `.txt` i no afegir-hi `category_code`.
- Ampliar el carregador existent, sense crear serveis innecessaris.
- Mantenir la lògica especial de presentació de `correccio`.

## Tests i verificació

Cobrir la validació del YAML, la càrrega idempotent, l'actualització de metadades, la deducció
de categoria, els noms invàlids i la resposta de l'endpoint. Adaptar `conftest.py` perquè
carregui les categories des del YAML.

Executar:

```bash
make test
make check
make frontend-check
```
