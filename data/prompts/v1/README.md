# Prompts v1

## Categoria: correcció (`correccio.yaml`)

10 textos en català amb errors reals que el model ha de corregir i retornar sense explicacions.

| ID | Tipus d'error | Dificultat | Registre |
|---|---|---|---|
| correccio_01 | Castellanismes lèxics (*pero, pues, entonces, o sea, algo, vale*…) | baixa | informal |
| correccio_02 | Accents diacrítics (*se/sé, es/és, si te/sí té, sera/serà*…) | mitjana | formal |
| correccio_03 | Apostrofació (*la escola → l'escola, el autobús → l'autobús, a el → al*…) | baixa | informal |
| correccio_04 | Ús incorrecte de *lo* (*lo que, lo millor, lo important*…) | baixa | col·loquial |
| correccio_05 | Subjuntiu requerit, indicatiu per interferència (*presenta/presenti, oblida/oblidi, acabarà/acabi*…) | alta | formal |
| correccio_06 | Preposicions (*en/amb* per a persona, *per el/pel*, *per/per a* per a beneficiari) | alta | formal |
| correccio_07 | Concordança de gènere i nombre (*la sistema, dificultats inicial, equip… compromesa*) | mitjana | neutre |
| correccio_08 | Registre inadequat en text formal (*bastants problemes, arreglar el tema, com més aviat millor*…) | alta | formal |
| correccio_09 | Ortografia específica del català: punt volat (*col.legi/col·legi*, *il.luminació*…) i accents | mitjana | neutre |
| correccio_10 | Errors mixtos: castellanismes + ortografia + morfologia (*montado, Es, musica, apuntate, hasta, mol*…) | alta | informal |

---

## Plantilla per a una categoria nova

```yaml
- id: <categoria>_01        # <categoria>_NN, numeració seqüencial des de 01
  categoria: <categoria>    # correccio | reformulacio | traduccio
  dificultat: baixa         # baixa | mitjana | alta
  registre: informal        # informal | col·loquial | neutre | formal
  tipus_error: <descripció breu del que s'avalua en aquest prompt>
  prompt: |
    <instrucció curta i directa al model>

    <text de 60-80 paraules>
```
