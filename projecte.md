# Arena Cat: explicació del projecte

> Aquest document recull la **motivació** i la **metodologia** del projecte. Per al pla concret de cada fita, consulta el [README](README.md#full-de-ruta).

## Continguts

- [1. Motivació](#1-motivació)
    - [1.1. Per què cal una avaluació humana específica per al català](#11-per-què-cal-una-avaluació-humana-específica-per-al-català)
- [2. Proposta](#2-proposta)
    - [2.1. Categories de tasques](#21-categories-de-tasques)
- [3. Com funciona el procés d'avaluació](#3-com-funciona-el-procés-davaluació)
    - [3.1. Exemple](#31-exemple)
- [4. Què cal avaluar](#4-què-cal-avaluar)
    - [4.1. Quantes comparacions calen?](#41-quantes-comparacions-calen)
    - [4.2. Reducció amb rànquing global](#42-reducció-amb-rànquing-global)
- [5. Qui fa l'avaluació](#5-qui-fa-lavaluació)
    - [5.1. Test de qualificació](#51-test-de-qualificació)
    - [5.2. Registre d'usuaris](#52-registre-dusuaris)
- [6. Resultats del projecte](#6-resultats-del-projecte)
    - [6.1. Rànquing públic de models](#61-rànquing-públic-de-models)
    - [6.2. Conjunt de dades obertes de preferències](#62-conjunt-de-dades-obertes-de-preferències)
- [Referències](#referències)
    - [Articles](#articles)
    - [Webs de projectes similars](#webs-de-projectes-similars)
    - [Biblioteques rellevants](#biblioteques-rellevants)

# 1. Motivació

Actualment podem [mesurar el rendiment](https://www.softcatala.org/la-intelligencia-artificial-al-vostre-ordinador-personal/models-dintelligencia-artificial-en-catala-per-usar-en-local/) dels models en català, però a part d'una valoració objectiva basada en mètriques d'IA, s'acostuma a donar també molta importància a com d'útils són els models en tasques reals avaluades per humans.

El que succeeix és que l'obsessió actual dels laboratoris que creen els sistemes d'IA per lluir en les mètriques fa que hi hagi una desconnexió important entre el que mostren les mètriques i l'experiència real dels usuaris. Hi ha un **[sobreajustament](https://ca.wikipedia.org/wiki/Sobreajustament_(overfitting))** a les mètriques.

## 1.1. Per què cal una avaluació humana específica per al català

- Les mètriques agregades poden amagar errors específics de la llengua (ortografia, registre, varietats dialectals, referències culturals).
- L'experiència real dels usuaris catalanoparlants no està reflectida en els *benchmarks* globals.
- No existeix un rànquing públic de models segons la preferència humana en català.

---

# 2. Proposta

Proposem fer una **variació del concepte de Chatbot Arena** adaptada al nostre cas:

- Chatbot Arena avalua els *prompts* que els usuaris volen; nosaltres volem focalitzar-nos només en la **competència dels models en llengua catalana**.
- Aquests sistemes funcionen en temps real: l'usuari proposa una pregunta i dos LLMs responen al moment.
    - Això no ho podem fer perquè ens representa molt cost.
    - En comptes d'això, **generem prèviament les tasques i les respostes** dels models.
    - **Limitació**: cada model genera una sola resposta per *prompt* (una passada d'inferència). No mostregem múltiples respostes per a una mateixa entrada, per la qual cosa no captem la variabilitat estocàstica del model.

## 2.1. Categories de tasques

Generem sintèticament 5 tasques representatives:

| Categoria | Descripció |
|---|---|
| Correcció | Corregeix aquest text |
| Traducció | Tradueix aquest text |
| Resum | Resumeix aquest text |
| Cultura | Contesta una pregunta de cultura catalana |
| Generació | Genera un text |

> A la fita 1 només cobrim 3 d'aquestes categories (correcció, cultura i traducció). Vegeu el [full de ruta](README.md#full-de-ruta).

---

# 3. Com funciona el procés d'avaluació

Demanem a l'usuari que valori quina parella de models ho fa millor per a una tasca concreta.

## 3.1. Exemple

![Exemple d'avaluació: prompt de traducció amb dues respostes (model A i model B) i les quatre opcions de vot](images/exemple-avaluacio.png)

> **Avaluació cega**: els models s'avaluen de forma cega: l'usuari **no sap** quin model està avaluant en cada cas, per evitar biaixos.

---

# 4. Què cal avaluar

El volum d'avaluacions necessari s'obté de tres factors:

- Els **models** que volem comparar
- Les **tasques** en què els posem a prova
- La **robustesa estadística** que volem assolir

## 4.1. Quantes comparacions calen?

1. **Nombre de parelles de models**: $C(n, 2) = n \times (n-1) / 2$. Per a 3 models, són **3 parelles**.
2. **Nombre de categories de tasca**: 5 (correcció, traducció, resum, cultura, generació). Cada parella s'avalua en cada categoria, donant $3 \times 5 = 15$ combinacions úniques.
3. **Variacions per categoria**: 10 prompts diferents per categoria, per capturar varietat de dificultat i estil. Això vol dir 50 prompts en total i $3 \times 50 = 150$ ítems d'avaluació únics (parella × prompt).
4. **Repeticions per combinació**: amb un marge d'error del 5% i un 95% de confiança, calen **385 vots** per cada (parella × categoria) per poder afirmar amb solidesa quin model va millor en aquella tasca.

> **Sostre conservador (cel·les independents)**: 15 × 385 = 5.775 avaluacions humanes. Cada *prompt* individual rebrà ~38 vots de mitjana, repartits entre les diferents parelles que el toquin.
>
> Si cada vot requereix uns 2 minuts: $5.775 \times 2 / 60 \approx 192$ hores.
>
> Aquest càlcul tracta cada (parella × categoria) com a independent. A la pràctica utilitzarem un model de rànquing global (vegeu [§4.2](#42-reducció-amb-rànquing-global)) que redueix considerablement aquest pressupost.

## 4.2. Reducció amb rànquing global

Si fem servir un sistema de rànquing global tipus **[Bradley-Terry](https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model)** o **[Elo](https://ca.wikipedia.org/wiki/Sistema_de_puntuaci%C3%B3_Elo)** (com fa LMSYS Chatbot Arena), el sistema aprofita la transitivitat: si sabem que A > B i B > C, ja tenim informació indirecta sobre A vs C.

Això:

- Redueix significativament els vots necessaris per obtenir un rànquing estable: com a regla heurística, l'estalvi escala amb $\log_2(n)/(n-1)$ respecte al sostre de 4.1. Per a 3 models, això redueix el total de **5.775 → ~4.575 vots** (~152 h). Vegeu el [simulador](https://softcatala.github.io/arena-cat/simulador/) per ajustar els paràmetres.
- Permet treballar amb dades **desbalancejades**: no cal que totes les parelles tinguin el mateix nombre de votacions.

---

# 5. Qui fa l'avaluació

La idea és muntar una **web participativa** dins del lloc de Softcatalà on els usuaris ens ajudin a fer aquest procés. Seria similar al que vam fer amb [Common Voice](https://commonvoice.mozilla.org/), on la gent contribuïa una estona a fer tasques.

## 5.1. Test de qualificació

Abans que un usuari pugui començar a contribuir, la primera vegada haurà de fer un **petit test de 5 preguntes** per comprovar que té criteri per fer l'avaluació.

## 5.2. Registre d'usuaris

Per evitar el vandalisme i garantir la qualitat, mantindrem un **registre d'usuaris** amb nom i contrasenya.

> **Inspiració**: l'enfocament participatiu segueix la línia de [Common Voice](https://commonvoice.mozilla.org/) i [VoiceArena](https://voicearena.com/): contribucions petites i acumulables d'una comunitat àmplia.

---

# 6. Resultats del projecte

El projecte generaria dos resultats principals:

## 6.1. Rànquing públic de models

Mantenir un **rànquing dels millors models per al català** segons preferència humana, actualitzat a mesura que arriben nous vots i nous models.

## 6.2. Conjunt de dades obertes de preferències

Un cop acabat el procés, es publicarà en obert el **conjunt de dades de preferències** amb l'estructura:

```
Prompt + Resposta A + Resposta B + Guanyador
```

> **Per què importa**: aquest conjunt de dades permetria a altres investigadors fer **RLHF** (*Reinforcement Learning from Human Feedback*) específic per al català, contribuint a millorar la qualitat dels models de la llengua a llarg termini.

---

# Referències

## Articles

1. Chiang, W.-L. et al. (2024). *Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference*. arXiv:2403.04132. <https://arxiv.org/abs/2403.04132>
2. Zheng, L. et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. NeurIPS 2023. arXiv:2306.05685. <https://arxiv.org/abs/2306.05685>
3. Bradley, R. A. & Terry, M. E. (1952). *Rank Analysis of Incomplete Block Designs: I. The Method of Paired Comparisons*. Biometrika, 39(3/4), 324–345. <https://doi.org/10.2307/2334029>

## Webs de projectes similars

Plataformes col·laboratives on els usuaris contribueixen activament amb vots o dades:

- **[LMSYS Chatbot Arena](https://lmarena.ai/)** — la referència directa: els usuaris voten a cegues entre dues respostes de LLMs i el rànquing es calcula amb Bradley-Terry/Elo.
- **[VoiceArena](https://voicearena.com/)** — versió equivalent per a models de síntesi de veu; els usuaris comparen mostres d'àudio per parelles.
- **[Common Voice](https://commonvoice.mozilla.org/)** — projecte de Mozilla on els voluntaris donen i validen mostres de veu per crear corpus oberts. Inspiració per al flux de contribució petita i acumulable.

## Biblioteques rellevants

- **[FastChat](https://github.com/lm-sys/FastChat)** — codi obert de LMSYS que implementa Chatbot Arena (interfície de votació, recollida de preferències, càlcul de rànquing). Punt de partida natural per no reinventar la roda.
- **[choix](https://github.com/lucasmaystre/choix)** — biblioteca Python per a inferència en models de comparacions per parelles (Bradley-Terry, Plackett-Luce). Útil per al càlcul del rànquing global.
- **[OpenSkill](https://github.com/vivekjoshy/openskill.py)** — alternativa moderna a Elo/TrueSkill amb implementació Python neta; valida resultats del Bradley-Terry.
