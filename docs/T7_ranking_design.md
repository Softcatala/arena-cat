# T7 — Biblioteca de rànquing i selecció de parelles: proposta de disseny

> Esborrany. Redactat per Gerard Martínez Canelles. Document previ a la implementació de la [issue #7](https://github.com/Softcatala/arena-cat/issues/7). Branch: `feature/T7_ranking`.

Aquest document té **dos públics**:

1. **Revisors** (Jordi, l'equip) — les seccions 1, 6, 7 i 8 són el resum executiu, la proposta de separació en mòduls, les preguntes obertes i el pla.
2. **Gerard** (jo, aprenent) — les seccions 2–5 són un recorregut pedagògic pels algorismes amb exemples pràctics. Salta-les si ja coneixes Bradley-Terry / Elo / bootstrap i intervals de confiança.

---

## Continguts

1. [Resum executiu](#1-resum-executiu)
2. [Què demana realment la issue?](#2-què-demana-realment-la-issue)
3. [Crash course: com funcionen els algorismes de rànquing](#3-crash-course-com-funcionen-els-algorismes-de-rànquing)
   - [3.1. Taxes de victòria pairwise brutes](#31-taxes-de-victòria-pairwise-brutes)
   - [3.2. Bradley-Terry](#32-bradley-terry)
   - [3.3. Elo](#33-elo)
   - [3.4. TrueSkill / OpenSkill](#34-trueskill--openskill)
   - [3.5. Comparativa cara a cara](#35-comparativa-cara-a-cara)
4. [Selecció de tasques (corregint una lectura inicial errònia)](#4-selecció-de-tasques-corregint-una-lectura-inicial-errònia)
5. [Com sabem que "tenim prou vots"?](#5-com-sabem-que-tenim-prou-vots)
6. [Disseny proposat](#6-disseny-proposat)
7. [Preguntes obertes per a l'equip](#7-preguntes-obertes-per-a-lequip)
8. [Pla de treball](#8-pla-de-treball)

---

## 1. Resum executiu

La issue #7 demana una biblioteca que respongui tres preguntes:

1. Quina parella de models ha d'avaluar el proper usuari?
2. Quin és el rànquing actual?
3. Hem recollit prou vots per confiar en el rànquing?

Després de llegir la documentació del projecte i la issue, la meva recomanació és:

| Pregunta | Recomanació per a la Fita 1 (n=3 models) |
|---|---|
| **Q1 — propera parella** | **Randomització amb quota equilibrada** sobre (categoria, prompt, parella no ordenada, costat). Tria uniformement entre les cel·les que encara no han arribat al quota. Darrere d'un protocol `TaskSampler` per poder canviar a sampling actiu més endavant. |
| **Q2 — rànquing** | **Estadístiques pairwise brutes com a artefacte públic principal**, amb **Bradley-Terry per categoria** com a resum secundari. BT ajustat amb un solver propi d'unes ~30 línies amb `scipy.optimize`, validat contra `choix` als unit tests. |
| **Q3 — confiança** | **Bootstrap de clusters de prompts amb labels fixos** de l'ajust original. Reportem P(el millor és realment el millor), CI del gap entre el millor actual i el competidor més fort, i la distribució de rànquings del bootstrap. |
| **Regla de parada** | `FixedBudgetRule` per defecte a la Fita 1 (necessitem el dataset complet per al llançament públic). `AdaptiveStoppingRule` implementada però no activada — cal correcció de testing seqüencial abans de posar-la en producció. |
| **Estimació de ρ** | Degradada de la lògica de parada a **anàlisi de sensibilitat** (un slider al simulador, no un paràmetre ajustat). Amb 10 prompts × 13 vots, un MLE beta-binomial és inestable. |
| **Elecció de biblioteca** | Ajust de BT directe amb `scipy.optimize` en producció; `choix` només com a referència de validació als tests. TrueSkill/OpenSkill no s'usen — estan optimitzats per a matchmaking online, no per a inferència offline transparent que tingui en compte l'agrupació per prompt. |

**Per què les estadístiques pairwise brutes són l'artefacte principal, no BT:** per a n=3 models amb ~133 vots per cel·la, la reducció de variància de BT sobre pairwise brut és d'un ~33% en el cas simètric i cau fins al 5% quan un model domina. La comunicació pública també és més neta: "Gemma va guanyar Qwen en 73 de 120 vots decisius (61%, IC 95% [52%, 69%])" no requereix cap model. BT és una verificació secundària útil i comença a compensar a la Fita 2+ quan n creix.

**Per què randomització amb quota equilibrada, i no iid uniforme:** iid uniforme sobre 90 cel·les (categoria × prompt × parella) amb 1.200 vots dona una variància de Poisson per cel·la (≈3,6 SD sobre una mitjana de 13,3). Després de queixar-nos de l'agrupació, acceptar aquest nivell de desequilibri entre cel·les és autodestructiu. La randomització amb quota equilibrada **no** és outcome-adaptive — només depèn dels comptadors acumulats, no de qui va guanyant —, així que no dispara la crítica del *Leaderboard Illusion*.

**Per què TrueSkill/OpenSkill no encaixen (versió precisa):** ambdues biblioteques són prou configurables per posar el drift a zero — l'afirmació forta "sempre inflen la variància" és falsa. La crítica real és que estan **dissenyades per a rànquing online i matchmaking en jocs**, no per a inferència offline transparent sobre un disseny d'avaluació fix. No gestionen de forma natural l'agrupació per prompt, la semàntica d'empat/cap, ni el sampling amb quotes fixes — les coses que realment ens importen.

La contribució substantiva d'aquesta tasca **no és l'elecció de biblioteca** — és la combinació de **sampling amb quota equilibrada** (per mantenir les cel·les equilibrades) i **bootstrap de clusters de prompts amb labels fixos** (per obtenir estimacions honestes d'incertesa). El marge de ±8,5% del simulador actual és un càlcul de sensibilitat condicional a un ρ assumit; amb valors plausibles de ρ (0,1–0,5), el marge per cel·la és plausiblement del 13–23% (vegeu [analysis/dimensioning.py](../analysis/dimensioning.py)).

---

## 2. Què demana realment la issue?

El text complet de la tasca a la [issue #7](https://github.com/Softcatala/arena-cat/issues/7):

> Implementa una biblioteca que respongui:
> - Quina és la propera parella de models que ha d'avaluar l'usuari?
> - Quin és el rànquing actual dels models?
> - Quina confiança tenim en el rànquing actual / hem arribat a prou avaluacions (per categoria)?
>
> Avaluar utilitzant openskill, trueskill o similar. Crear scripts de simulació.

Si ho llegim amb atenció, veiem que són **dos temes diferents encabits en una sola issue**:

| Tema | Tipus | Impacte |
|---|---|---|
| **Selecció de parelles** (Q1) | Online, s'executa a cada petició API | Baix — una mala tria biaixa lleugerament el sampling |
| **Rànquing + confiança** (Q2, Q3) | Offline / periòdic, corre sobre el dataset complet | Alt — determina el rànquing públic i la decisió de parada |

Han de ser **dos mòduls**, no un. Tenen necessitats de test diferents, freqüències d'actualització diferents, i no cal que comparteixin biblioteca.

---

## 3. Crash course: com funcionen els algorismes de rànquing

Aquesta secció és el recorregut pedagògic llarg. Salta-la si ja coneixes aquests algorismes.

### 3.1. Taxes de victòria pairwise brutes

**El més simple possible.** Per a cada (model_A, model_B, categoria), compta quantes vegades ha guanyat A i divideix pel total de vots.

#### Exemple pràctic (categoria correcció)

Suposem que després d'un cert nombre de vots tenim:

| Enfrontament | Vots per A | Vots per B | Empats |
|---|---|---|---|
| Qwen vs Salamandra | 73 | 47 | 10 |
| Qwen vs Gemma | 60 | 60 | 10 |
| Salamandra vs Gemma | 30 | 90 | 10 |

(Ignorem els empats per simplicitat: moltes formulacions de BT els descarten.)

Taxes de victòria brutes:
- Qwen vs Salamandra: 73 / (73 + 47) = **60,8%** per Qwen
- Qwen vs Gemma: 60 / 120 = **50,0%** (empat a nivell poblacional)
- Salamandra vs Gemma: 30 / 120 = **25,0%** per Salamandra (Gemma domina)

**Què té de bo això:** és transparent, no assumeix cap model, i és fàcil posar-hi un interval de confiança binomial per parella.

**Què té de dolent:**
1. **No dona rànquing global.** Tenim tres comparacions independents; combinar-les en una única puntuació de skill és informal.
2. **No comparteix transitivitat.** Si Qwen guanya Salamandra i Salamandra perd contra Gemma, aquesta evidència no actualitza la nostra creença sobre Qwen vs Gemma.
3. **No hi ha IC combinats entre parelles.** Pots posar un IC a cada parella, però combinar-los en "el rànquing és fiable" requereix un altre pas.

#### Interval de confiança (Wilson, el correcte)

Per a una única parella amb `wins` sobre `n` vots:

```python
p_hat = wins / n
ci_low, ci_high = wilson_ci(wins, n, confidence=0.95)
```

Això és el que està calculant el `simulador/index.html` (aproximadament). El problema és que **n aquí són vots, no prompts** — així que l'IC és massa estret quan els vots dins d'un prompt estan correlacionats. Vegeu la secció 5.

---

### 3.2. Bradley-Terry

**La idea:** assignem a cada model un únic número — el seu **skill** `θ_i`. La probabilitat que el model A guanyi el model B és:

```
P(A beats B) = exp(θ_A) / (exp(θ_A) + exp(θ_B))
            = sigmoid(θ_A - θ_B)
```

Això és simplement **regressió logística amb la identitat del model com a única feature**. Si has fet classificació en Python, ja saps com funciona. Si `θ_A = θ_B`, P(A guanya) = 0,5. Si `θ_A − θ_B = log(2) ≈ 0,69`, A guanya 2/3 de les vegades. Si el gap és `log(9) ≈ 2,2`, A guanya el 90% de les vegades.

#### Exemple pràctic: ajustant BT a ull

Amb les dades de la §3.1, BT assignaria skills com:

| Model | Skill `θ` (il·lustratiu) | Interpretació |
|---|---|---|
| Gemma | +0,6 | el més fort |
| Qwen | +0,2 | intermedi |
| Salamandra | −0,8 | el més fluix |

Aquests valors no tenen significat absolut — només compten les **diferències** (BT és invariant a translacions). El que importa és `θ_Gemma − θ_Salamandra = 1,4`, que correspon a una probabilitat de `sigmoid(1,4) ≈ 80%` que Gemma guanyi, coherent amb el 90/120 = 75% observat.

#### Com s'ajusta BT a la pràctica

Màxima verosimilitud, normalment per **algorismes iteratius** (MM, Newton, o simplement gradient descent amb PyTorch). La biblioteca `choix` ens ho fa:

```python
import choix

# Build a list of (winner_id, loser_id) pairs, ignoring ties.
data = [(qwen, salamandra)] * 73 + [(salamandra, qwen)] * 47 + ...

# Fit BT
skills = choix.ilsr_pairwise(n_models, data, alpha=0.01)
# → array like [0.2, -0.8, 0.6] for [qwen, salamandra, gemma]
```

`ilsr_pairwise` = Iterative Luce Spectral Ranking, un solver eficient. `alpha` és un regularitzador petit per mantenir l'estabilitat quan un model té 0 victòries o 0 derrotes.

#### L'argument de la transitivitat (per què BT és "millor que brut")

Imaginem que tenim 100 vots a (Qwen vs Salamandra) i 100 a (Salamandra vs Gemma), però **només 5 a (Qwen vs Gemma)** perquè el sampler aleatori encara no hi ha caigut gaire.

- **Aproximació bruta:** per a (Qwen vs Gemma), tenim un IC basat en n=5. Molt ampli.
- **Aproximació BT:** fins i tot amb només 5 vots directes, els skills `θ_Qwen` i `θ_Gemma` estan tots dos *ancorats* pels 200 vots que involucren Salamandra. La probabilitat implícita de (Qwen vs Gemma) queda molt millor estimada que si només tinguéssim aquests 5 vots.

Això és l'"estalvi de transitivitat" que menciona el README. L'estalvi creix com `log₂(n)/(n−1)`:

| n models | Factor de reducció BT | Estalvi |
|---|---|---|
| 2 | 1,00 | 0% |
| 3 | 0,79 | 21% |
| 5 | 0,58 | 42% |
| 10 | 0,37 | 63% |
| 20 | 0,23 | 77% |

Per a la **Fita 1 (n=3), BT ens dona una reducció del 21%**. A la Fita 2+ amb 10+ models, l'estalvi es fa molt més valuós.

#### Quan BT falla

BT assumeix un **únic eix global** de skill. Si la realitat és "Gemma és molt millor en correcció però Qwen és molt millor en traducció", un BT global únic ho barrejarà tot. **És precisament per això que ajustem BT per categoria, no globalment** — vegeu §6.

---

### 3.3. Elo

**El mateix model que BT, però ajustat online amb una regla d'actualització simple.**

Cada model comença per exemple a 1500. Després d'una partida on A guanya B:

```
expected_A = 1 / (1 + 10^((rating_B - rating_A) / 400))
rating_A += K * (1 - expected_A)
rating_B += K * (0 - expected_B)
```

On K és una "taxa d'aprenentatge" (típicament 16–32 als escacs).

**Exemple pràctic:**
- Tots dos a 1500. A guanya B.
- `expected_A = 1 / (1 + 10^0) = 0,5`.
- `rating_A += K * (1 - 0,5) = 0,5K`. Amb K=32, A puja a 1516 i B baixa a 1484.

**Per què Elo no és l'eina principal correcta per a nosaltres:**

1. **Depèn de l'ordre.** Si reprodueixes els mateixos 200 vots en un altre ordre, obtens ratings finals diferents. BT (ajustat en batch) és independent de l'ordre.
2. **El paràmetre K és arbitrari.** Massa alt → ratings sorollosos. Massa baix → els ratings no segueixen les dades. No hi ha una manera principiada de fixar K per a una avaluació d'una instantània.
3. **El scaling de 400 és una convenció escacs.** El model subjacent és el mateix que BT, només amb una parametrització diferent (`log(10) / 400`).

**On Elo ens és útil:** com a **estimació online barata** per a la selecció de parelles durant la votació, computable al vol sense refit del model BT complet. Però el rànquing públic hauria d'usar BT offline.

LMSYS Chatbot Arena reporta tots dos — vegeu el seu post explicant la metodologia.

---

### 3.4. TrueSkill / OpenSkill

**Extensió bayesiana d'Elo on cada jugador té una (mitjana, variància) en comptes d'un únic rating.**

- TrueSkill: Microsoft, dissenyat per al matchmaking d'Xbox Live.
- OpenSkill: reemplaçament open-source, API similar.

La mitjana és l'estimació; la variància es redueix a mesura que s'observen més partides. Un jugador nou comença amb una variància alta ("no ho sabem"). Després de les partides, la variància disminueix.

**El problema per a nosaltres:** ambdues biblioteques modelen **skill dinàmic** — assumeixen que el skill real d'un jugador va derivant amb el temps, i tenen paràmetres com "dynamics factor" o "tau" que governen quanta variància es *torna a afegir* després de cada partida per evitar que el sistema es torni massa confiat.

Però els nostres models són **instantànies congelades**. El skill de Salamandra 7B en correcció no deriva. Afegir soroll dinàmic no és només innecessari — és directament perjudicial: infla la variància i dona intervals de confiança més amplis del que les dades justifiquen.

**Conclusió:** TrueSkill/OpenSkill resolen un problema que no tenim. La suggerència de la issue d'usar-los probablement reflecteix quines biblioteques són més conegudes, no quina encaixa millor amb el context estadístic.

---

### 3.5. Comparativa cara a cara

| Propietat | Win rates brutes | Bradley-Terry | Elo | TrueSkill/OpenSkill |
|---|---|---|---|---|
| Rànquing global | ❌ | ✅ | ✅ | ✅ |
| Comparteix transitivitat | ❌ | ✅ | ✅ | ✅ |
| Independent de l'ordre | ✅ | ✅ | ❌ | ❌ |
| Actualitzacions online | n/a | costós (refit) | barat | barat |
| Modela skill dinàmic | n/a | ❌ | dèbilment | ✅ |
| IC fàcil per bootstrap | ✅ | ✅ | més complicat | més complicat |
| Encaixa amb el nostre context | parcial | **el millor** | acceptable per online | excessiu |

---

## 4. Selecció de tasques (corregint una lectura inicial errònia)

Quan un usuari obre l'app, el servidor ha de triar una **tasca** — una tupla de `(categoria, prompt, parella_de_models_no_ordenada, assignació_de_costat)` — per mostrar-l'hi. La unitat no és només una parella de models: el prompt, la categoria i quin model es mostra a l'esquerra vs a la dreta importen tots.

### 4.1. Tres candidats

| Estratègia | Com tria | Pros | Contres |
|---|---|---|---|
| **Aleatori iid uniforme** | Mostreja uniformement entre les 90 cel·les (categoria × prompt × parella), randomitza el costat | Simple, no esbiaixat | iid crea variància de Poisson en el comptador per cel·la — algunes cel·les tindran 5 vots i altres 25, sobre un pressupost de 13. Autodestructiu donada la nostra preocupació per l'agrupació. |
| **Aleatori amb quota equilibrada** | Mostreja uniformement entre les cel·les que estan per sota del comptador objectiu, randomitza el costat. Evita mostrar la mateixa cel·la a la mateixa sessió dues vegades. | Les mateixes propietats estadístiques que uniforme en esperança; els comptadors per cel·la convergeixen a exactament iguals. | Una mica més d'estat al sampler. |
| **Sampling actiu (regla de Chiang 2024)** | Probabilitat ∝ `√(σ²/n) − √(σ²/(n+1))` — afavoreix parelles infra-avaluades i d'alta variància | Estalvi de vots de ~30%+; és el que recomanen tant Chiang com Singh. | Requereix una estimació de BT en el moment del sampling; requereix disclosure. |

### 4.2. El paper del Leaderboard Illusion: què diu realment

He llegit Singh et al. 2025 amb atenció. **El meu enquadrament inicial en aquest document era erroni.** La crítica del paper **no és** "el sampling adaptatiu és dolent". És:

> *"undisclosed sampling rates that systematically over-represent a handful of proprietary providers"* (Secció 4.1, parafrasejat).

La **Recomanació 4** del paper és **implementar** la regla de sampling actiu de Chiang et al. 2024 (FastChat Secció 5, Eq. 9), argumentant que "prioritza efectivament parelles infra-avaluades i d'alta variància, alineant el sampling amb l'objectiu de reduir ràpidament la incertesa en els rànquings". El paper critica Chatbot Arena per **afirmar** que ho fa però no desplegar-ho realment.

Per tant, el sampling adaptatiu és acceptable si: (a) es basa en incertesa / infra-mostratge, no en proximitat de rànquing per si mateixa, i (b) l'estratègia es fa pública.

### 4.3. Recomanació

**Per a la Fita 1: randomització amb quota equilibrada, darrere d'un protocol `TaskSampler`.** Motius:
- Elimina essencialment de franc el problema de desequilibri iid-uniforme.
- No és adaptativa en cap sentit i no comporta cap càrrega de disclosure.
- L'estalvi del sampling actiu amb n=3 i un pressupost fix de 1.200 vots és modest. Val més gastar la complexitat en la correcció del bootstrap.

**Per a la Fita 2+: el sampling actiu esdevé atractiu.** La regla de Chiang et al. s'implementa com a segona estratègia (`UncertaintyDrivenSampler`) i es pot activar via config, amb l'estratègia declarada a la pàgina pública del rànquing.

```python
# task_sampler.py

class TaskSampler(Protocol):
    """Estratègia per triar la propera tasca completa: (categoria, prompt, parella, costat)."""
    def select_next_task(self, session: Session) -> Task: ...


class QuotaBalancedSampler:
    """Tria uniformement entre cel·les (categoria, prompt, parella) que encara no han
    arribat al quota. Estratègia per defecte a la Fita 1."""

class UncertaintyDrivenSampler:
    """Implementa la regla de Chiang et al. 2024 (FastChat §5, eq. 9):
    P(a) ∝ √(σ²/n_a) − √(σ²/(n_a+1))
    Requereix una estimació actual de skills. Cal disclosure pública si s'activa."""

class DiversityWeightedSampler:
    """Quota-balanced però amb pesos dels prompts segons la diversitat dels outputs
    (vegeu §11.1). Els pesos són pre-calculats i no depenen de cap rànquing."""
```

**La randomització del costat és obligatòria per a totes les estratègies** per evitar el biaix de posició. El sampler tria `side_assignment ∈ {A, B}` uniformement per tasca i no canonitza l'ordre a la BD.

---

## 5. Com sabem que "tenim prou vots"?

Aquesta és la part **més infra-especificada** de la issue #7, i on l'estadística curosa importa més.

### 5.1. La resposta ingènua (el que fa el simulador)

Per a cada cel·la (parella × categoria), computa un IC binomial sobre la taxa de victòries:

```python
margin = z * sqrt(0.25 / n_votes)  # worst case at p=0.5
```

Per a 133 vots → marge del 8,5%. **Paràm quan el marge < objectiu.**

Això és incorrecte quan els vots dins d'un prompt estan correlacionats, que és el nostre cas.

### 5.2. La resposta que té en compte l'agrupació

La fórmula del design effect de Kish:

```
N_effective = N_raw / (1 + (k − 1) * ρ)
```

- `k` = vots per prompt
- `ρ` = correlació intra-prompt (fins a quin punt el prompt determina el veredicte)

Per a la Fita 1 amb ρ ≈ 0,3, el marge per cel·la és **plausiblement del 18%, no del 8,5%** — però cal notar que això és un càlcul de sensibilitat condicional a un ρ assumit, no una veritat empírica. Amb només 10 clusters de prompt per categoria, fins i tot amb el design effect ben aplicat, el nombre reduït de clusters limita la precisió de qualsevol estimació d'incertesa. L'aproximació asimptòtica z = 1,96 també és optimista amb només 10 clusters.

Vegeu l'anàlisi completa a [analysis/dimensioning.py](../analysis/dimensioning.py) i les quatre gràfiques a `analysis/out/`. La manera correcta de comunicar-ho públicament és **"sota ρ plausible ∈ [0,1, 0,5], el marge és del 13–23%"**, no "el marge real és 18%".

### 5.3. Regla operativa de confiança (i correcció d'un bug)

**La pregunta real que volem respondre per categoria:** "El model actualment millor és fiablement millor que el següent competidor?"

Això *no és* el mateix que "és gran el gap entre el rank 1 i el rank 2?", perquè els ranks 1 i 2 poden intercanviar-se entre les rèpliques del bootstrap. Un esborrany anterior d'aquest document tenia un bug aquí: ordenar els skills dins de cada rèplica del bootstrap força que el gap sigui no negatiu per construcció, cosa que declara falsament estabilitat fins i tot quan el rànquing és inestable.

**El bootstrap de clusters amb labels fixos (versió correcta):**

```python
# Original: 10 prompts per category (each with many votes)
# Step 1: Fit BT once on the full data to identify the *current* best.
theta_hat = fit_bt(all_votes_in_category)
best_model = argmax(theta_hat)
competitor_models = [m for m in models if m != best_model]

# Step 2: Resample whole prompts with replacement, refit BT each time,
# track the SAME model's gap (not the resampled rank 1).
deltas = []
for _ in range(n_bootstrap):
    sampled_prompts = random.choices(prompts_in_category, k=len(prompts_in_category))
    sampled_votes = flatten(p.votes for p in sampled_prompts)
    theta_b = fit_bt(sampled_votes)
    delta_b = theta_b[best_model] - max(theta_b[m] for m in competitor_models)
    deltas.append(delta_b)  # CAN BE NEGATIVE — that's the point

# Step 3: Two complementary summaries.
ci_lo, ci_hi = np.percentile(deltas, [2.5, 97.5])
p_best_is_best = np.mean([d > 0 for d in deltas])
ranking_is_stable = ci_lo > 0
```

**Per què funciona:** si el millor actual és genuïnament millor, la majoria de rèpliques del bootstrap el continuaran mostrant al davant → `p_best_is_best` proper a 1 i `ci_lo > 0`. Si el millor actual va tot just per davant i el rànquing és fràgil, moltes rèpliques mostraran un altre model al davant → `delta_b` es tornarà negatiu en aquelles rèpliques → `ci_lo < 0` i `p_best_is_best` proper a 0,5.

**Dos números complementaris, no un:**
- `p_best_is_best` — fàcil de comunicar. "Gemma és el millor model en correcció amb un 87% de confiança."
- `ci_lo, ci_hi` — IC formal sobre el gap de skill. S'utilitza a la regla de parada.

**Advertiments importants** (val la pena marcar-los en qualsevol comunicació pública):
1. Amb **només 10 clusters de prompt**, el bootstrap de clusters és més honest que el bootstrap iid, però no és màgia — el bootstrap de clusters amb pocs clusters té problemes coneguts de mostra petita.
2. El bootstrap només té en compte la **dependència a nivell de prompt**. La **dependència a nivell de sessió** (un voluntari que fa molts vots) és una font de correlació separada de la qual hauríem d'informar, però sense ficar-la al bootstrap fins a v2 (quan tinguem usuaris).
3. La regla "**Pr(el millor actual és el millor) > 95%**" *no és* el mateix que "**hem detectat un gap estadísticament significatiu**" — cal anar amb compte a la comunicació pública.

### 5.4. ρ no forma part del relat públic de confiança

`ρ` es queda com a **slider de sensibilitat** al simulador i com a diagnòstic intern. **No** ajustem un ρ únic a partir de les dades ni publiquem una afirmació de confiança que en depengui — amb 10 prompts × 13 vots, l'MLE beta-binomial és inestable i un ρ únic amagaria diverses fonts diferents de dependència (dificultat del prompt, interacció model-prompt, efectes de sessió, biaix de posició, ambigüitat de categoria). Tracta ρ com una eina de "què passaria si...", no com un paràmetre a estimar.

---

## 6. Disseny proposat

### 6.1. Separació en mòduls

```
backend/app/ranking/
    __init__.py
    task_sampler.py     # Q1: pick next (category, prompt, pair, side) — quota-balanced default
    ranking.py          # Q2: raw pairwise stats + per-category BT (scipy.optimize, ~30 LOC)
    confidence.py       # Q3: fixed-label cluster bootstrap, P(best is best), stopping rules
    types.py            # dataclasses, kept free of SQLAlchemy
```

**Restricció de disseny:** els tipus i funcions del nucli consumeixen dataclasses o dataframes plans, no files ORM de SQLAlchemy. La capa API és responsable de traduir les files ORM als tipus del nucli. Això manté la matemàtica testable de forma aïllada i evita acoblar la lògica de rànquing a la sessió de BD.

Més els scripts de simulació sota `scripts/`:

```
scripts/
    simulate_ranking.py     # Drive the full pipeline end-to-end on synthetic data
    benchmark_methods.py    # Compare BT vs raw win rates on real-ish data
```

### 6.2. API pública (esbós)

#### Task sampler — patró Strategy

Per evitar deute tècnic més endavant, exposem un protocol `TaskSampler` amb tres implementacions intercanviables. El microservei en tria una a l'arrencada via configuració. Comencem amb `QuotaBalancedSampler` per a la Fita 1 i podem canviar a weighted o active sampling més endavant sense canvis d'API.

```python
# task_sampler.py

class TaskSampler(Protocol):
    """Estratègia per triar la propera tasca completa:
    (categoria, prompt, parella, costat_A_o_B)."""
    def select_next_task(self, session_id: str | None) -> Task: ...


class QuotaBalancedSampler:
    """Tria uniformement entre cel·les (categoria, prompt, parella) per sota del quota.
    Randomitza el costat (A/B). Evita repetir la mateixa cel·la per a una sessió.
    Estratègia per defecte a la Fita 1."""

class DiversityWeightedSampler:
    """Quota-balanced, però amb pesos pre-calculats segons la diversitat
    dels outputs dels models per a aquell prompt (vegeu §11.1).
    Els pesos són fixos durant la campanya — no depenen dels vots acumulats."""

class UncertaintyDrivenSampler:
    """Implementa la regla d'active sampling de Chiang et al. 2024 (FastChat §5, eq. 9):
    P(a) ∝ √(σ²/n_a) − √(σ²/(n_a+1))
    Recomanat per Singh et al. 2025 com a remei a les biaixos de sampling.
    Requereix una estimació actual de skills; cal disclosure pública si s'activa."""


# ranking.py
@dataclass
class CategoryRanking:
    category_code: str
    bt_skills: dict[str, float]              # model → BT skill
    raw_win_rates: dict[tuple[str, str], float]  # (a, b) → P(a beats b)
    n_votes: int
    n_prompts: int

def compute_rankings(session: Session) -> list[CategoryRanking]:
    """Fit BT i calcula les estadístiques per cada categoria."""
    ...

# confidence.py
# Hi ha dues maneres d'usar la confiança:
#   - "report-only": col·lectar votes fins al budget i reportar la confiança final.
#   - "stopping rule": parar quan el CI bootstrap sobre el gap rank1-rank2 exclou zero.
# Implementem totes dues; la microservei tria via configuració.
@dataclass
class ConfidenceReport:
    category_code: str
    rank1_vs_rank2_skill_gap_ci: tuple[float, float]
    is_ranking_stable: bool
    estimated_rho: float
    naive_margin: float
    clustered_margin: float

def assess_confidence(
    session: Session,
    category_code: str,
    n_bootstrap: int = 1000,
) -> ConfidenceReport:
    """Bootstrap clustered per categoria; estima ρ a partir de les dades."""
    ...


class StoppingRule(Protocol):
    """Decideix si una categoria ha rebut prou vots."""
    def should_stop(self, session: Session, category_code: str) -> bool: ...


class FixedBudgetRule:
    """Para quan s'arriba a `votes_target` per cel·la. Estratègia per defecte a la Fita 1.
    Permet alliberar un dataset complet i comparable entre categories."""
    def __init__(self, votes_target_per_cell: int = 133): ...

class AdaptiveStoppingRule:
    """Para una categoria quan el CI bootstrap sobre rank1-rank2 exclou zero.
    Més eficient en hores humanes; introdueix biaix de 'peeking' si no es controla
    amb correcció seqüencial (alpha-spending) — implementació posterior si cal."""
    def __init__(self, min_votes_per_cell: int = 50, alpha: float = 0.05): ...
```

### 6.3. Dependències a afegir

```toml
[project.dependencies]
numpy = "^1.26"
scipy = "^1.11"             # BT MLE via scipy.optimize.minimize; Wilson CIs; bootstrap stats

[project.optional-dependencies]
dev = [
    "choix = ^0.3",         # Reference BT implementation; used only in unit tests
]
```

**Per què scipy en producció i choix només als tests.** La log-versemblança de BT són ~30 línies en scipy pur amb una restricció sum-to-zero i un paràmetre L2 explícit `alpha` amb un significat inequívoc. `choix` és excel·lent però la semàntica del seu `alpha` depèn de l'algorisme (pseudo-comptadors pairwise als solvers MM, L2/gaussià als basats en scipy), cosa que el fa lleugerament menys transparent per al nostre cas d'ús. L'usem als unit tests per validar el nostre ajust scipy contra una implementació independent sobre dades sintètiques amb skills coneguts.

**Protecció contra separació completa.** Si un model guanya 0 o totes les comparacions decisives contra un altre model en alguna categoria (possible amb dades escasses), el MLE de BT sense regularització divergeix. La regularització L2 ho gestiona amb gràcia; ho testem explícitament.

Cap canvi al frontend. Cap canvi a la BD (l'esquema actual a `models.py` és suficient).

### 6.4. Pla de TDD

Seguint la convenció del projecte (`AGENTS.md`), els tests van primer. Identificadors en anglès, docstrings en català:

```python
# tests/test_pair_selector.py
def test_select_next_task_returns_two_distinct_models():
    """Comprova que la parella retornada té dos models diferents."""

def test_select_next_task_is_uniform_over_pairs():
    """Sobre molts mostratges, la distribució de parelles és aproximadament uniforme."""

# tests/test_ranking.py
def test_bt_recovers_planted_skills():
    """Amb dades sintètiques generades amb skills coneguts, BT els recupera dins l'error."""

def test_bt_handles_tie_votes():
    """Els empats no fan petar el solver; opcionalment es descompten o es divideixen."""

# tests/test_confidence.py
def test_clustered_bootstrap_wider_than_naive():
    """Quan ρ > 0, el CI clusteritzat és més ampli que el binomial."""

def test_stable_ranking_with_decisive_data():
    """Si un model guanya el 90% de votes a tots els altres, is_ranking_stable=True."""

def test_unstable_ranking_with_coin_flip_data():
    """Si totes les parelles són 50/50, is_ranking_stable=False."""
```

### 6.5. Per què aquest disseny supera la lectura literal de la issue #7

| Què diu la issue #7 | Què proposem | Per què |
|---|---|---|
| "Utilitzar openskill / trueskill" | Ajust directe amb scipy BT + choix com a referència de test | openskill / trueskill estan afinats per matchmaking online, no per a inferència offline transparent |
| Una sola biblioteca | Tres mòduls (sampler, ranking, confidence) | Impactes diferents, patrons de test diferents. El sampler no depèn de BT; BT no depèn del bootstrap. |
| "Confiança en el rànquing" | Bootstrap de clusters **amb labels fixos** sobre `θ_best − max(θ_others)`, més P(el millor és el millor) | La versió anterior de "ordenar i agafar el gap del top-2" tenia un bug de signe; aquesta versió permet deltes negatius i reflecteix correctament la inestabilitat del rànquing |
| Implícit: sampling iid uniforme | Randomització amb quota equilibrada | iid crea desequilibri de Poisson a les cel·les amb pressupostos petits; el quota-balanced no dispara el Leaderboard Illusion tampoc |
| Scripts de simulació | Més benchmark BT vs raw + casos adversarials | Mostrem empíricament que l'estalvi de BT és del ~33% en el cas simètric a n=3, caient fins al ~5% quan un model domina |

### 6.6. Altres consideracions de producte / metodologia

| Preocupació | Com es gestiona |
|---|---|
| **Biaix de posició (costat A vs B)** | El sampler randomitza el costat per tasca. Mètrica d'auditoria: diferència de win-rate A vs B per model, reportada a les sortides de `confidence.py`. |
| **Agrupació a nivell de sessió** | `session_id` es tracta i es reporta com a mètrica de concentració (màxim de vots per sessió, índex de Herfindahl). No s'incorpora al bootstrap fins que v2 introdueixi usuaris. |
| **Empat vs cap** | Es reporten com a taxes **separades**. Per a l'entrada de BT: es descarten totes dues. Per a les estadístiques brutes: mig punt per l'empat, s'exclou "cap" (no mig punt, perquè "cap" vol dir "cap dels dos és acceptable" i no "són equivalents"). |
| **Immutabilitat dels codis de categoria** | `cultura → reformulacio` (commit `439463a`) és un rename real. Els **codis** de categoria han de ser immutables per a l'anàlisi longitudinal; els noms per mostrar poden canviar. Marquem aquesta convenció a `AGENTS.md` i al README del mòdul. |
| **Versionatge de model a les sortides públiques** | El rànquing públic exporta `model + inference_metadata.{seed, temperature, top_p, quantization, model_version}` perquè el resultat no es pugui atribuir retroactivament a un checkpoint diferent. Les dades ja hi són a l'esquema (`Response.inference_metadata`). |
| **Detecció de cicles** | Amb n=3 el pairwise brut pot produir un cicle (A>B>C>A) que BT suavitza. Reportem-lo quan passi — és un senyal significatiu sobre l'heterogeneïtat, no un bug. |

---

## 7. Preguntes obertes per a l'equip

Abans que comenci la implementació, m'agradaria confirmar:

**Q1.** Volem rànquings **per categoria**, **globals**, o **tots dos**? El README suggereix per categoria però no ho diu explícitament.
> **La meva recomanació:** per categoria és la pregunta de producte. El global és un "estaria bé tenir-ho".

**Q2.** L'equip està d'acord amb la selecció de parella **aleatòria uniforme**, o preferiu adaptativa? Argumento fortament per l'aleatòria — vegeu §4.
> **La meva recomanació:** implementar **totes dues** darrere d'un protocol `PairSelector` (§6.2) i llençar `UniformRandomSelector` com a default a la Fita 1. Així podem canviar a adaptativa més endavant via config sense un nou PR. L'adaptativa requerirà disclosure pública per evitar la crítica del Leaderboard Illusion (vegeu `leaderboard_illusion_response.md`).

**Q3.** Com gestionem els **empats i els vots de "cap"**? Tres opcions:
- (a) Descartar-los del tot.
- (b) Comptar un empat com a mig punt per a cada costat.
- (c) Modelar els empats explícitament amb un paràmetre de "llindar d'empat" (extensió Rao-Kupper de BT).
> **La meva recomanació:** (b) per a les taxes brutes, (a) per a BT (és el que és estàndard).

**Q4.** Quin és el **criteri de parada** per a la Fita 1? Arribar als 1.200 vots objectiu sí o sí, o parar aviat per categoria si el rànquing s'estabilitza?
> **La meva recomanació:** implementar **totes dues** darrere d'un protocol `StoppingRule` (§6.2) i llençar `FixedBudgetRule` com a default de la Fita 1 — volem el dataset complet per al llançament públic (`projecte.md` §6.2). `AdaptiveStoppingRule` queda cablejada per a ús futur, però requereix correccions de testing seqüencial (alpha-spending) abans de posar-la en producció per evitar el biaix de "peeking".

**Q5.** La preocupació del "Leaderboard Illusion" a la bibliografia — la resposta d'Arena Cat a cada crítica està documentada a [`leaderboard_illusion_response.md`](leaderboard_illusion_response.md).

---

## 8. Pla de treball

### Fase 0 — Alineació (aquest document + revisió)
- ✅ Branch `feature/T7_ranking` creada.
- ⏳ Publicar aquest document com a comentari a la issue #7 i demanar feedback al Jordi.
- ⏳ Resoldre les 5 preguntes obertes de §7.

### Fase 1 — Validació sintètica (encara sense codi de producció)
- Escriure `scripts/simulate_ranking.py` que generi vots sintètics a partir de skills coneguts amb un ρ donat.
- Confirmar que el bootstrap de clusters recupera l'amplada d'IC correcta.
- Reproduir empíricament l'estalvi del 21% de BT per a n=3 models.
- Aquesta és la feina que ens permetrà dir "aquest disseny funciona" *abans* que ningú l'utilitzi.

### Fase 2 — Implementació (TDD, PRs petits)
- PR 1: `pair_selector.py` + tests. Trivial; obre la porta.
- PR 2: `ranking.py` (BT per categoria + estadístiques brutes) + tests.
- PR 3: `confidence.py` (bootstrap de clusters, estimació de ρ, regla de parada) + tests.
- PR 4: Test d'integració que connecta els tres mòduls sobre dades amb seed.

### Fase 3 — Integració amb el microservei (issue #6)
- Un cop existeixi el servei FastAPI de la issue #6, exposem tres endpoints:
  - `GET /api/task` crida `pair_selector.select_next_task`.
  - `GET /api/stats` crida `ranking.compute_rankings` + `confidence.assess_confidence`.
  - El `POST /api/vote` ja existeix segons `pla_detallat.md`; només escriu a la BD.
- Aquesta fase és **fora d'abast d'aquesta tasca** però l'API està dissenyada per encaixar-hi netament.

### Fase 4 — Documentació
- Actualitzar `docs/db_schema.md` si calen taules/views noves (ara mateix crec que podem calcular-ho tot a partir de `votes` + `responses` + `prompts` + `categories`).
- Afegir un `backend/app/ranking/README.md` curt que expliqui els tres mòduls.

### Estimació d'esforç

| Fase | Hores |
|---|---|
| Fase 0 (alineació) | ~3 |
| Fase 1 (validació sintètica) | ~8 |
| Fase 2 (implementació, 4 PRs) | ~20 |
| Fase 3 (cablejat amb FastAPI) | depèn de #6 |
| Fase 4 (docs) | ~2 |
| **Total (excloent-ne la dependència de #6)** | **~33 hores** |

Cap dins el pressupost de ~120 hores de la Fita 1 marcat al [README.md](../README.md#fita-1-prova-de-concepte).

---

## 11. Actualitzacions després del rebase sobre main (2026-06-27)

La branch s'ha rebasat sobre `origin/main` i s'ha tornat a revisar la llista d'issues / PRs. Dos commits havien aterrat a main des que es va redactar el document; cap dels dos afecta aquest disseny directament:

- `00c5228` — desactivat el reasoning a `scripts/inferencia.py`, afegit el tracking del temps d'inferència per model.
- `39bd981` — eliminat el workflow `contributors-readme-action`.

Tres punts oberts al repositori mereixen menció perquè toquen el nostre abast.

### 11.1. PR #18 — "Càlcul de diversitat dels prompts" (obert, Jordi)

Afegeix dos scripts:
- `scripts/metriques.py` — computa les distàncies pairwise entre les sortides dels tres models sobre el mateix prompt, usant **chrF** (similitud d'n-grames de caràcters) i **Levenshtein**, tots dos normalitzats a una distància 0–1.
- `scripts/analitza_inferencies.py` — produeix un `results.txt` que ordena els 30 prompts per com de *discriminatoris* són (els prompts on els tres models produeixen sortides més divergents pugen més).

**Per què això importa per al nostre selector de parelles.** Si dos models produeixen sortides gairebé idèntiques per a un prompt determinat, un avaluador humà no pot preferir-ne un de manera significativa. El vot es converteix en soroll gairebé 50/50, cosa que:
- Malbarata temps humà.
- Infla la correlació intra-prompt `ρ` que ens preocupava a §5, perquè el soroll aleatori domina el senyal dins del prompt.

Això és genuïnament **informació prèvia útil** i computable offline, abans que es reculli cap vot.

**Dues maneres d'aprofitar-ho (totes dues compatibles amb la postura de "no Leaderboard Illusion" de §4):**

| Aproximació | Què fa | Compromís |
|---|---|---|
| **A — Filtre** | Descartar els prompts on la similitud pairwise de sortides superi un llindar (per exemple, `chrF_d < 0,15`) | Estadístiques més netes; dataset més petit |
| **B — Random sampling ponderat** | Ponderar cap avall (però no excloure) els prompts poc discriminatoris al sampler aleatori | Manté tots els prompts; esbiaixa cap als informatius |

**Important — per què això NO és sampling adaptatiu en el sentit perjudicial.** Els pesos de diversitat són:
- Computats **una sola vegada** a partir de les sortides pre-generades dels models.
- **Congelats** abans que comenci la votació.
- **Independents** de l'estimació actual del rànquing.

La crítica del Leaderboard Illusion apunta a samplers que esbiaixen cap a parelles amb rànquings actualment propers *basant-se en dades de vot acumulades*. Un prior congelat sobre la informativitat dels prompts no fa això — és la mateixa lògica que l'anàlisi de potència per a la selecció de tests, que és pràctica estàndard.

**La meva recomanació:** Un cop el PR #18 estigui merged, usar `DiversityWeightedSampler` (la tercera estratègia de §6.2) com a config opcional — randomització amb quota equilibrada, però amb els prompts dins de cada cel·la (categoria, parella) mostrejats en proporció als seus scores de diversitat pre-calculats. Implementació a `task_sampler.py`:

```python
# Per (category × pair) cell, pick prompts according to diversity-weighted quota.
# Weights are computed once at startup from PR #18's output, frozen for the campaign.
```

Si el PR #18 no es fa merge, tornem al `QuotaBalancedSampler` a seques (uniforme entre les cel·les infra-quota). Cap canvi de codi.

**Pregunta oberta per a l'equip:** és acceptable l'aproximació B, o preferiu uniforme estricte per màxima transparència? La meva preferència feble és B perquè aprofita millor el pressupost de voluntaris.

### 11.2. La issue #6 (microservei) està assignada a Isaac Nicolas

És el consumidor downstream de la nostra biblioteca. Val la pena coordinar-se un cop hàgim aterrat la Fase 1 perquè l'API sigui la que ell necessita. **Encara no verificat:** si l'Isaac ha començat, si existeix un esborrany de contracte d'API.

**Acció:** parlar amb l'Isaac abans de tancar les signatures de `pair_selector.select_next_task` i `ranking.compute_rankings`.

### 11.3. La issue #14 (loader idempotent de BD, sense assignar) no és un bloquejant

Sense la #14 no hi ha vots reals a la BD contra els quals fer tests, però la **Fase 1 (validació sintètica)** no els necessita — generem els vots a partir de skills sintètics. La integració amb la BD real correspon a la Fase 2 / Fase 3.

### 11.4. Efecte net sobre el disseny

Cap canvi trencador. Dues actualitzacions al pla:

- **§4** — afegir una línia de seguiment: "Si el PR #18 es fa merge abans de la Fase 2, canviar el sampler a random ponderat basat en els scores de diversitat. L'argument contra el sampling adaptatiu no aplica als priors congelats sobre la diversitat dels prompts (vegeu §11.1)."
- **§6.4 (pla de tests)** — afegir un test: `test_select_next_task_respects_diversity_weights()` si es pren l'aproximació B.

---

---

## 12. Registre post-revisió (2026-06-27)

Una revisió adversarial externa (enviada a ChatGPT Pro) va trobar un bug real i diversos punts on el disseny original era menys curós del que hauria de ser. Aquesta secció registra què ha canviat i per què.

### 12.1. Bug corregit

El codi bootstrap original de §5.3 ordenava els skills dins de cada rèplica i agafava `sorted[0] - sorted[1]`, cosa que és no negativa per construcció. Això **declara falsament l'estabilitat** quan el millor model s'intercanvia amb el segon entre rèpliques del bootstrap. Correcció: identificar el millor actual a partir de l'ajust amb totes les dades i, després, seguir el gap del **mateix** model (amb signe, pot ser negatiu) en cada rèplica. Codi nou a §5.3.

### 12.2. Canvis de disseny confirmats i incorporats

| Canvi | Motiu |
|---|---|
| Aleatori iid → sampling **amb quota equilibrada** | La variància de Poisson de iid trenca l'anàlisi d'agrupació amb un pressupost de 13 vots/cel·la |
| Rename de mòdul: `pair_selector.py` → `task_sampler.py` | Mostregem (categoria, prompt, parella, costat), no només una parella |
| Biblioteca: `choix` només als tests, ajust directe amb scipy en producció | La semàntica de l'`alpha` de `choix.ilsr_pairwise` depèn de l'algorisme; scipy amb L2 explícit és més transparent per a ~30 línies |
| `ρ` degradat de paràmetre estimat a slider de sensibilitat | L'MLE beta-binomial és inestable sobre 10 prompts × 13 vots; un ρ únic amaga múltiples fonts diferents de dependència |
| Llenguatge del marge públic suavitzat | "Sota ρ plausible ∈ [0,1, 0,5], marge ≈ 13–23%" substitueix "el marge real és 18%" |
| Crítica a TrueSkill/OpenSkill afinada | L'afirmació forta "inflen la variància" era errònia (el drift es pot configurar); el motiu precís és que estan afinades per matchmaking online |
| Estadístiques pairwise brutes promocionades a **artefacte públic principal** | A n=3 amb ~133 vots/cel·la, l'estalvi de variància de BT és del ~33% en el cas simètric, baixa al ~5% quan un model domina. La comunicació pública també és més neta sense BT. |
| Empat/cap gestionats per separat | Empat = "tots dos comparables"; cap = "tots dos han fallat". Senyals diferents, taxes separades. |
| Biaix de posició / agrupació de sessions / detecció de cicles afegits a §6.6 | Fonts independents de dependència de les quals hem d'informar com a mínim |

### 12.3. El paper del Leaderboard Illusion — correcció a la meva lectura inicial

Havia emmarcat el sampling adaptatiu com si caigués en la mateixa crítica que Chatbot Arena. Després de llegir Singh et al. 2025 directament (Secció 6, Recomanació 4): **el paper recomana adoptar** la regla de sampling actiu de Chiang et al. 2024, argumentant que "prioritza efectivament parelles infra-avaluades i d'alta variància". La crítica va contra **taxes de sampling no revelades que sobre-representen sistemàticament proveïdors propietaris**, no contra el sampling adaptatiu en si.

Això vol dir que `UncertaintyDrivenSampler` (la regla de Chiang) és una estratègia perfectament defensable si s'activa més endavant — amb disclosure pública. [`leaderboard_illusion_response.md`](leaderboard_illusion_response.md) s'ha actualitzat en conseqüència.

### 12.4. Estimació de temps revisada

Les ~33 hores originals eren optimistes. Estimació realista després de la revisió:

| Fase | Hores |
|---|---|
| Fase 0 (aquest document de disseny + revisió) | ~4 (ja gastades) |
| Fase 1 (validació sintètica, incloent-hi tests de correcció del bootstrap) | ~10 |
| Fase 2 (implementació, 4 PRs) | ~25 |
| Fase 4 (docs) | ~2 |
| **Total (excloent-ne la dependència de #6)** | **~40** |

On és probable que s'estiri: semàntica d'empat/cap amb l'equip, gestió de separació completa, sortides scipy deterministes entre plataformes, comptabilitat del costat A/B, els casos límit del bootstrap de clusters (molt pocs clusters, cicles).

### 12.5. Fora d'abast, però mereixerà un ticket futur

- **Model multinivell** per als efectes aleatoris prompt × model (terme `u_{p,i}`). Més net conceptualment però requereix PyMC/Stan, driven per priors amb 10 prompts.
- **Model d'empat de Davidson** per a la probabilitat d'empat explícita a BT. El mig punt és una convenció d'scoring; Davidson és un model de verosimilitud. Ho ajornem a la Fita 2+ quan tinguem prou dades per identificar el paràmetre d'empat.
- **Defenses contra vot adversarial** més enllà del rate limiting per sessió. La secció de limitacions del paper de Singh ho marca com a crític per als benchmarks comunitaris; ho ajornem a v2 (quan tinguem usuaris).

---

## Referències

- Documents del projecte: [`README.md`](../README.md), [`projecte.md`](../projecte.md), [`pla_detallat.md`](../pla_detallat.md), [`AGENTS.md`](../AGENTS.md)
- Issue: [#7 Biblioteca de rànquing i selecció de parelles](https://github.com/Softcatala/arena-cat/issues/7)
- Relacionats oberts: [#6 microservei (Isaac)](https://github.com/Softcatala/arena-cat/issues/6), [#14 càrrega idempotent](https://github.com/Softcatala/arena-cat/issues/14), [PR #18 diversitat de prompts](https://github.com/Softcatala/arena-cat/pull/18)
- Esquema: [`backend/app/models.py`](../backend/app/models.py), [`docs/db_schema.md`](db_schema.md)
- Anàlisi de dimensionament de mostra: [`analysis/dimensioning.py`](../analysis/dimensioning.py) i quatre gràfiques a `analysis/out/`
- Extern: [documentació de choix](https://choix.lum.li/en/latest/), [Bradley-Terry a Wikipedia](https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model), [paper del Leaderboard Illusion](https://arxiv.org/abs/2504.20879)
