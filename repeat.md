# Baseline de repeticions

Resultats de referència del selector actual per comparar futurs canvis.

## Condicions de la simulació

- 10 usuaris, amb 20 tasques per usuari: 200 tasques en total.
- Mode «Qualsevol categoria».
- 4 categories, 10 textos actius per categoria i 4 models per text.
- 6 parelles de models per text: 60 comparacions per categoria i 240 en total.
- Tots els recomptes de vots inicials a zero.
- 20 rondes; a cada ronda, cada usuari vota una vegada en un ordre aleatori.
- Cada vot actualitza els recomptes compartits abans de seleccionar la tasca següent.
- Sense omissions, canvis de versions ni respostes absents.
- Simulació amb `random.Random(42)`, reproduint les regles del selector:
  categoria aleatòria, exclusió de comparacions ja votades i selecció aleatòria
  entre les comparacions pendents amb menys vots de la comunitat.

És una simulació de la configuració del repositori, no una mesura de producció
ni una execució del backend contra PostgreSQL. El sorteig de la posició A/B
no afecta aquestes mètriques i no s'ha simulat.

## Resultats

El denominador és de **190 tasques**: les 19 posteriors a la primera de cada
usuari. Totes les repeticions es calculen respecte de l'historial del mateix
usuari.

| Situació | Casos | Percentatge | Explicació |
|---|---:|---:|---|
| Mateixa categoria que la tasca anterior | 57 | **30,0%** | Dues tasques consecutives són, per exemple, de correcció. |
| Mateix text que la tasca anterior | 5 | **2,6%** | El text es repeteix immediatament amb una altra parella de models. |
| Alguna resposta idèntica a la tasca anterior | 3 | **1,6%** | Es repeteix el text i almenys una resposta de la tasca anterior. |
| Text ja vist durant la sessió | 41 | **21,6%** | El text havia aparegut en qualsevol tasca anterior. Exemple: primer A–B i més endavant C–D sobre el mateix text. |
| Alguna resposta ja vista durant la sessió | 35 | **18,4%** | Almenys una resposta ja s'havia llegit. Exemple: primer A–B i més endavant A–C; la resposta d'A és idèntica. |
| Mateixa comparació ja votada | 0 | **0%** | Es repeteixen el text i la mateixa parella de models ja votada. El selector ho impedeix. |

Les situacions se superposen i **els percentatges no se sumen**. «Durant la
sessió» inclou qualsevol tasca anterior, no només la immediatament anterior.
Les respostes repetides s'identifiquen pel mateix text i model; no es comparen
les cadenes de text de models diferents.

En cap de les 190 seleccions analitzades, el conjunt de comparacions candidates
amb menys vots estava restringit a un únic text.

Cada usuari va veure entre 13 i 18 textos diferents en les seves 20 tasques.
En aquesta execució, aproximadament una de cada cinc tasques posteriors a la
primera recuperava un text ja llegit. Altres llavors i altres distribucions
inicials de vots poden donar resultats diferents.

## Referències

- [Selecció de categories](backend/app/services/task_service.py).
- [Selecció de comparacions](backend/app/ranking/sampler.py).
- [Configuració dels models](config/inferencia/inferencia_config.yaml).
- [Funcionament del sistema](docs/sistema.md#selecció-i-registre-de-tasques).

## Comparació amb la priorització de prompts menys vistos

La variant considera conjuntament totes les categories i tria les comparacions
pendents segons `(lectures personals del prompt, vots comunitaris de la cel·la)`.
Els empats se sortegen. Cada escenari comença de nou amb llavor 42 i zero vots,
amb els mateixos 10 usuaris; només canvia el nombre de tasques per usuari.
La simulació reprodueix les regles, no els generadors aleatoris del backend.

Cada cel·la mostra **selector anterior → priorització proposada**.

| Situació | 20 tasques/usuari | 50 tasques/usuari | Totes: 240 tasques/usuari |
|---|---:|---:|---:|
| Mateixa categoria que l'anterior | 30,0% → **29,5%** | 25,1% → **25,1%** | 27,9% → **23,1%** |
| Mateix prompt que l'anterior | 2,6% → **0%** | 2,2% → **0,2%** | 2,7% → **0,04%** |
| Alguna resposta idèntica a l'anterior | 1,6% → **0%** | 1,8% → **0,2%** | 2,3% → **0,04%** |
| Prompt ja vist durant la sessió | 21,6% → **0%** | 42,4% → **20,4%** | 83,7% → **83,7%** |
| Alguna resposta ja vista durant la sessió | 18,4% → **0%** | 35,7% → **14,9%** | 80,3% → **80,2%** |
| Mateixa comparació ja votada | 0% → **0%** | 0% → **0%** | 0% → **0%** |

Els denominadors són 190, 490 i 2.390: s'exclou la primera tasca de cada usuari.
Les situacions se superposen. Amb la priorització hi va haver una repetició
immediata de prompt i resposta en les 2.390 transicions de l'escenari complet.

Amb 40 prompts, les primeres 40 tasques no repeteixen prompt. Després de
completar les 240 comparacions, 200 tasques per usuari repeteixen prompt en
totes dues estratègies. La priorització ajorna i espaia les repeticions;
no elimina la reutilització necessària per completar totes les parelles.
