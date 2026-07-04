# Avaluadors i dimensionament

## Context

El disseny d'aquest pla parteix de la idea d'**avaluadors fidels**: persones del nucli de col·laboradors habituals de Softcatalà que es comprometen a completar **totes** les combinacions de *prompt* × categoria × parella de models. No perseguim una gran participació puntual, sinó un grup reduït i constant que garanteixi cobertura completa i comparabilitat entre respostes.

Esperem reunir-ne **al voltant de 20 avaluadors fidels**, xifra que dona prou marge sobre el mínim per la prova de concepte (~14 avaluadors) per absorbir abandonaments i mantenir el marge d'error objectiu.

Aquesta hipòtesi condiciona tot el que ve a continuació: les xifres de la prova de concepte i les taules d'escalada assumeixen que cada avaluador respon totes les combinacions (unicitat activada). L'hem dissenyat així per assegurar-nos que som capaços de tirar-no cap endavant, després òbviament hi haurà una combinació d'avaluadors fidels i esporàdics, el sistema admet qualsevol configuració.

També assumim que **incorporem un model nou cada mes** al rànquing. Cada nou model afegit obliga a fer noves comparacions contra els models ja existents (amb *parelles independents*, $M-1$ parelles noves per cada model afegit; amb Elo/BT, l'esforç pot concentrar-se en un subconjunt dels aparellaments més informatius). Això vol dir que la feina dels avaluadors fidels no és un esforç puntual, sinó un **compromís sostingut**: cal preveure una càrrega recurrent i mecanismes perquè els avaluadors es puguin incorporar o rellevar sense trencar la comparabilitat.

Si cada tasca (comparar dues respostes i votar) triga ~**2 minuts**, la càrrega individual per avaluador segons el nombre de models (amb 3 categories i 10 *prompts* per categoria) es la que és descriu a la taula següent.

#### Projecció a un any

| Nombre de models | Parelles de models | Vots totals per avaluador | Temps estimat per avaluador (2 min/vot) |
| --- | --- | --- | --- |
| 3 models (sep 2026) | 3 parelles | 90 vots | ~3 hores |
| 5 models (nov 2026) | 10 parelles | 300 vots | ~10 hores |
| 10 models (abr 2027) | 45 parelles | 1.350 vots | ~45 hores |
| 15 models (set 2027) | 105 parelles | 3.150 vots | ~105 hores |

La progressió és **quadràtica** amb el nombre de models: passar de 3 a 10 models multiplica per 15 la feina de cada avaluador, cosa que fa inviable el compromís individual complet a partir d'unes poques desenes de models.

Per contenir la càrrega caldrà **retirar models antics** (versions superades pel mateix proveïdor) o **congelar-ne la puntuació** (deixen d'entrar al sampler però conserven l'skill Elo/BT ancorat pels vots ja rebuts). Preferim la segona: manté el rànquing històric i aprofita la informació acumulada sense generar feina nova.

### Com hi ajuda Elo / Bradley-Terry

Amb el mètode de **parelles independents** analitzem cada parella per separat. Un model d'habilitat com **Elo** o **Bradley-Terry** (BT) assigna una única puntuació de skill a cada model a partir de totes les comparacions, i **comparteix informació entre parelles**: si el model $A$ guanya al $B$ i el $B$ al $C$, aquesta evidència també actualitza la nostra creença sobre $A$ vs $C$.

En termes pràctics, això es tradueix en una **reducció de la variància** de les estimacions (no en un canvi d'ordre de creixement — segueix sent quadràtic amb el nombre de models, però amb un factor constant més petit). L'estalvi de variància respecte a les taxes brutes és aproximadament:

| Nombre de models | Estalvi de variància amb BT |
|-----------------:|----------------------------:|
| 3                | ~21%                        |
| 5                | ~42%                        |
| 10               | ~63%                        |
| 20               | ~77%                        |

Per a la prova de concepte ($M=3$) l'estalvi és modest (~21%), i les taxes brutes per parella són prou informatives i molt més fàcils de comunicar. A partir d'una desena de models, l'estalvi ja és substancial i BT esdevé l'eina natural per publicar un rànquing global. Reduir de veritat el nombre de vots (passar el creixement de quadràtic a aproximadament lineal amb $M$) requereix una eina addicional: **sampling actiu** — concentrar les comparacions en els aparellaments infra-mostrejats i d'alta variància (Chiang et al. 2024). No l'activem a la prova de concepte, però queda a l'abast per a fites posteriors.

## Prova de concepte

### Objectiu d'ús

40 hores de contribucions humanes (~1.200 vots a uns 2 minuts cadascun), amb un marge d'error nominal ≈ **8,5%** per (parella × categoria) sota l'enfocament de *parelles independents* (3 models, 3 categories, 10 *prompts* per categoria, 95% de confiança).

Si cada avaluador respon totes les combinacions (3 parelles de models × 3 categories × 10 *prompts* = 90 vots/usuari, **~3 h per avaluador** a 2 min/vot), en calen **~14 avaluadors** (1.260 vots, ~133 per parella × categoria, ≈ 42 h en total).

Aquestes xifres coincideixen amb el [simulador](https://softcatala.github.io/arena-cat/simulador/) amb el mètode *Parelles independents* i la restricció d'unicitat activada.

> **⚠️ El 8,5% és una fita optimista.** Aquest càlcul assumeix que els vots dins d'un mateix *prompt* són independents, però en realitat estan **correlacionats** (un prompt fàcil o difícil arrossega tots els vots que rep). Aplicant el design effect de Kish amb una correlació intra-*prompt* $\rho$ plausible entre 0,1 i 0,5, el marge honest per (parella × categoria) és **del 13–23%**. Vegeu [`T7_ranking_design.md`](T7_ranking_design.md) §5 per als detalls, i tracteu el 8,5% com el pitjor cas *si* $\rho=0$.

## Com escala el dimensionament

Aquesta secció explica com canvia el volum de feina i la precisió quan variem els paràmetres del disseny. Suposem un grup d'avaluadors fidels que responen **totes** les combinacions (unicitat activada: cada avaluador veu cada *prompt* × parella × categoria una sola vegada). Amb $M$ models, $C$ categories i $P$ prompts per categoria:

- Nombre de parelles: $M(M-1)/2$.
- Vots per avaluador: $M(M-1)/2 \times C \times P$.
- Vots per (parella × categoria) que aporta cada avaluador: $P$.
- Avaluadors necessaris per assolir $V$ vots per (parella × categoria): $\lceil V / P \rceil$.

Punt de partida (prova de concepte): $M=3$, $C=3$, $P=10$, $V \approx 133$ ⇒ 90 vots/avaluador, **14 avaluadors**, 1.260 vots totals (~42 h).

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

Amb el mètode de *parelles independents*, el marge d'error **nominal** d'una proporció al 95% de confiança és aproximadament:

$$\text{ME} \approx 1{,}96 \sqrt{\frac{p(1-p)}{V}}$$

on $V$ és el nombre de vots per (parella × categoria) i $p$ la proporció observada (pitjor cas $p=0{,}5$). Com que $V = N \cdot P$ (essent $N$ el nombre d'avaluadors que responen totes les combinacions i $P$ els *prompts* per categoria), el marge decreix amb $1/\sqrt{N}$: **cal quadruplicar els avaluadors per reduir el marge a la meitat**.

Aquesta fórmula assumeix vots independents. En la pràctica els vots dins d'un mateix *prompt* estan correlacionats i el marge honest és aproximadament $\sqrt{1 + (k-1)\rho}$ vegades més gran (design effect de Kish, on $k$ són vots per *prompt* i $\rho$ la correlació intra-*prompt*). Les xifres de la taula següent són, doncs, un **sostre optimista**.

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
