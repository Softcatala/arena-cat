# Avaluadors i dimensionament

## Prova de concepte

### Objectiu d'ús

40 hores de contribucions humanes (~1.200 vots a uns 2 minuts cadascun), amb un marge d'error ≈ **8,5%** per (parella × categoria) sota l'enfocament de *parelles independents* (3 models, 3 categories, 10 *prompts* per categoria, 95% de confiança).

Si cada avaluador respon totes les combinacions (3 parelles de models × 3 categories × 10 *prompts* = 90 vots/usuari), en calen **~14 avaluadors** (1.260 vots, 140 per parella × categoria, ≈ 42 h).

Aquestes xifres coincideixen amb el [simulador](https://softcatala.github.io/arena-cat/simulador/) amb el mètode *Parelles independents* i la restricció d'unicitat activada.

## Com escala el dimensionament

Aquesta secció explica com canvia el volum de feina i la precisió quan variem els paràmetres del disseny. Suposem un grup d'avaluadors fidels que responen **totes** les combinacions (unicitat activada: cada avaluador veu cada *prompt* × parella × categoria una sola vegada). Amb $M$ models, $C$ categories i $P$ prompts per categoria:

- Nombre de parelles: $M(M-1)/2$.
- Vots per avaluador: $M(M-1)/2 \times C \times P$.
- Vots per (parella × categoria) que aporta cada avaluador: $P$.
- Avaluadors necessaris per assolir $V$ vots per (parella × categoria): $\lceil V / P \rceil$.

Punt de partida (prova de concepte): $M=3$, $C=3$, $P=10$, $V=140$ ⇒ 90 vots/avaluador, **14 avaluadors**, 1.260 vots totals (~42 h).

### Afegir més models

El nombre de parelles creix **quadràticament** amb $M$. Com que cada avaluador continua aportant $P$ vots per (parella × categoria), el **nombre d'avaluadors no canvia** per mantenir el mateix marge d'error, però la càrrega individual i el volum total de vots creixen ràpidament:

| Models | Parelles | Vots/avaluador | Hores/avaluador | Avaluadors | Vots totals | Hores totals |
|-------:|---------:|---------------:|----------------:|-----------:|------------:|-------------:|
| 3      | 3        | 90             | ~3 h            | 14         | 1.260       | ~42 h        |
| 4      | 6        | 180            | ~6 h            | 14         | 2.520       | ~84 h        |
| 5      | 10       | 300            | ~10 h           | 14         | 4.200       | ~140 h       |
| 6      | 15       | 450            | ~15 h           | 14         | 6.300       | ~210 h       |

**Coll d'ampolla**: la resistència de l'avaluador. Passar de 90 a 300 vots per persona pot fer inviable el compromís; convé fraccionar sessions o rebaixar la unicitat estricta.

### Afegir més prompts

Augmentar $P$ té l'efecte contrari: cada avaluador aporta **més vots per (parella × categoria)**, així que en calen **menys** per assolir el mateix $V$. La càrrega per persona creix linealment; el total de vots es manté (si $V$ és fix).

| Prompts/cat. | Vots/avaluador | Hores/avaluador | Avaluadors (V=140) | Vots totals |
|-------------:|---------------:|----------------:|-------------------:|------------:|
| 10           | 90             | ~3 h            | 14                 | 1.260       |
| 15           | 135            | ~4,5 h          | 10                 | 1.350       |
| 20           | 180            | ~6 h            | 7                  | 1.260       |
| 30           | 270            | ~9 h            | 5                  | 1.350       |

**Compte**: augmentar $P$ millora la cobertura temàtica però *no* redueix el marge d'error per (parella × categoria) si $V$ es manté. Per reduir el marge cal apujar $V$ (i, per tant, més avaluadors o més prompts respostos per persona).

### Impacte del nombre d'avaluadors en el marge d'error

Amb el mètode de *parelles independents*, el marge d'error d'una proporció al 95% de confiança és aproximadament:

$$\text{ME} \approx 1{,}96 \sqrt{\frac{p(1-p)}{V}}$$

on $V$ és el nombre de vots per (parella × categoria) i $p$ la proporció observada (pitjor cas $p=0{,}5$). Com que $V = N \cdot P$ (essent $N$ el nombre d'avaluadors que responen totes les combinacions i $P$ els *prompts* per categoria), el marge decreix amb $1/\sqrt{N}$: **cal quadruplicar els avaluadors per reduir el marge a la meitat**.

Amb $P=10$ (prova de concepte):

| Avaluadors | Vots/(parella × cat.) | Marge d'error (≈, p=0,5) |
|-----------:|----------------------:|-------------------------:|
| 5          | 50                    | ~13,9%                   |
| 10         | 100                   | ~9,8%                    |
| 14         | 140                   | **~8,3%**                |
| 20         | 200                   | ~6,9%                    |
| 40         | 400                   | ~4,9%                    |
| 100        | 1.000                 | ~3,1%                    |

**Lectura ràpida**:

- Passar de 14 a 40 avaluadors (×2,9) baixa el marge de ~8,3% a ~4,9%.
- Baixar-lo per sota del 3% exigeix diversos centenars d'avaluadors o més *prompts* per categoria.
- Si es prioritza precisió, sovint és més eficient afegir *prompts* (que multiplica els vots sense cansar més gent) que buscar molts més avaluadors.

### Resum

- **+ models** ⇒ mateixos avaluadors, però cada un treballa molt més (quadràtic).
- **+ prompts** ⇒ menys avaluadors per al mateix marge d'error, cadascun treballa una mica més (lineal).
- **+ avaluadors** ⇒ el marge d'error decreix amb $1/\sqrt{N}$: guanys ràpids al principi, cada cop més cars.
- El límit pràctic és la **paciència de l'avaluador**: ~90–120 vots per persona sembla un sostre raonable abans no calgui repartir la feina.
