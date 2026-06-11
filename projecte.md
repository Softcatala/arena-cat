# Arena Cat — Explicació del projecte


## Continguts

- [1. Introducció](#1-introducció)
    - [1.1. En poques paraules](#11-en-poques-paraules)
- [2. Motivació](#2-motivació)
    - [2.1. Per què cal una avaluació humana específica per al català](#21-per-què-cal-una-avaluació-humana-específica-per-al-català)
- [3. Proposta](#3-proposta)
    - [3.1. Objectiu inicial](#31-objectiu-inicial)
        - [Models a avaluar](#models-a-avaluar)
        - [Categories de tasques](#categories-de-tasques)
- [4. Com funciona el procés d'avaluació](#4-com-funciona-el-procés-davaluació)
    - [4.1. Exemple](#41-exemple)
- [5. Què cal avaluar](#5-què-cal-avaluar)
    - [5.1. Quantes comparacions calen?](#51-quantes-comparacions-calen)
    - [5.2. Reducció amb rànquing global](#52-reducció-amb-rànquing-global)
- [6. Qui fa l'avaluació](#6-qui-fa-lavaluació)
    - [6.1. Test de qualificació](#61-test-de-qualificació)
    - [6.2. Registre d'usuaris](#62-registre-dusuaris)
- [7. Què cal fer](#7-què-cal-fer)
    - [7.1. Tasques d'avaluació](#71-tasques-davaluació)
    - [7.2. Plataforma](#72-plataforma)
- [8. Resultats del projecte](#8-resultats-del-projecte)
    - [8.1. Rànquing públic de models](#81-rànquing-públic-de-models)
    - [8.2. Conjunt de dades obertes de preferències](#82-conjunt-de-dades-obertes-de-preferències)

> **Full de ruta i abast de la versió 1.0**: consulta el [README](README.md#full-de-ruta).

# 1. Introducció
    
    
**Avaluació humana de models d'IA en català.**

Volem desenvolupar una plataforma participativa, inspirada en [LMSYS Chatbot Arena](https://lmarena.ai/), centrada exclusivament a mesurar la **competència en llengua catalana** dels models de llenguatge gran (LLMs).

A diferència de les [avaluacions automàtiques basades en mètriques](https://www.softcatala.org/la-intelligencia-artificial-al-vostre-ordinador-personal/models-dintelligencia-artificial-en-catala-per-usar-en-local/), aquí són persones les que comparen, a cegues, les respostes de dos models davant d'una mateixa tasca i decideixen quina és millor.
    

## 1.1. En poques paraules

- **Què**: rànquing de models LLM segons preferència humana en tasques en català.
- **Com**: comparació cega de parelles de respostes generades prèviament (no en temps real).
- **Qui**: comunitat de Softcatalà, amb un test de qualificació previ.
- **Resultat**: rànquing públic més un conjunt de dades obertes de preferències per a RLHF en català.

# 2. Motivació

Actualment podem [mesurar el rendiment](https://www.softcatala.org/la-intelligencia-artificial-al-vostre-ordinador-personal/models-dintelligencia-artificial-en-catala-per-usar-en-local/) dels models en català, però a part d'una valoració objectiva basada en mètriques d'IA, s'acostuma a donar també molta importància a com d'útils són els models en tasques reals avaluades per humans.

El que succeeix és que l'obsessió actual dels laboratoris que creen els sistemes d'IA per lluir en les mètriques fa que hi hagi una desconnexió important entre el que mostren les mètriques i l'experiència real dels usuaris. Hi ha un **[sobreajustament](https://ca.wikipedia.org/wiki/Sobreajustament_(overfitting))** a les mètriques.

## 2.1. Per què cal una avaluació humana específica per al català

- Les mètriques agregades poden amagar errors específics de la llengua (ortografia, registre, varietats dialectals, referències culturals).
- L'experiència real dels usuaris catalanoparlants no està reflectida en els *benchmarks* globals.
- No existeix un rànquing públic de models segons la preferència humana en català.

---

# 3. Proposta

Proposem fer una **variació del concepte de Chatbot Arena** adaptada al nostre cas:

- Chatbot Arena avalua els *prompts* que els usuaris volen; nosaltres volem focalitzar-nos només en la **competència dels models en llengua catalana**.
- Aquests sistemes funcionen en temps real: l'usuari proposa una pregunta i dos LLMs responen al moment.
    - Això no ho podem fer perquè ens representa molt cost.
    - En comptes d'això, **generem prèviament les tasques i les respostes** dels models.
    - **Limitació**: cada model genera una sola resposta per *prompt* (una passada d'inferència). No mostregem múltiples respostes per a una mateixa entrada, per la qual cosa no captem la variabilitat estocàstica del model.

## 3.1. Objectiu inicial

Començaríem amb un objectiu modest:

### Models a avaluar

- Qwen 3.5 9B
- Salamandra 7B
- Gemma 4 26B A4B

### Categories de tasques

Generem sintèticament 5 tasques representatives:

| Categoria | Descripció |
|---|---|
| Correcció | Corregeix aquest text |
| Traducció | Tradueix aquest text |
| Resum | Resumeix aquest text |
| Cultura | Contesta una pregunta de cultura catalana |
| Generació | Genera un text |

---

# 4. Com funciona el procés d'avaluació

Demanem a l'usuari que valori quina parella de models ho fa millor per a una tasca concreta.

## 4.1. Exemple

![Exemple d'avaluació: prompt de traducció amb dues respostes (model A i model B) i les quatre opcions de vot](images/exemple-avaluacio.png)

> **Avaluació cega**: els models s'avaluen de forma cega: l'usuari **no sap** quin model està avaluant en cada cas, per evitar biaixos.

---

# 5. Què cal avaluar

El volum d'avaluacions necessari s'obté de tres factors:

- Els **models** que volem comparar
- Les **tasques** en què els posem a prova
- La **robustesa estadística** que volem assolir

## 5.1. Quantes comparacions calen?

1. **Nombre de parelles de models**: $C(n, 2) = n \times (n-1) / 2$. Per a 3 models, són **3 parelles**.
2. **Nombre de categories de tasca**: 5 (correcció, traducció, resum, cultura, generació). Cada parella s'avalua en cada categoria, donant $3 \times 5 = 15$ combinacions úniques.
3. **Variacions per categoria**: 10 prompts diferents per categoria, per capturar varietat de dificultat i estil. Això vol dir 50 prompts en total i $3 \times 50 = 150$ ítems d'avaluació únics (parella × prompt).
4. **Repeticions per combinació**: amb un marge d'error del 5% i un 95% de confiança, calen **385 vots** per cada (parella × categoria) per poder afirmar amb solidesa quin model va millor en aquella tasca.

> **Sostre conservador (cel·les independents)**: 15 × 385 = 5.775 avaluacions humanes. Cada *prompt* individual rebrà ~38 vots de mitjana, repartits entre les diferents parelles que el toquin.
>
> Si cada vot requereix uns 2 minuts: $5.775 \times 2 / 60 \approx 192$ hores.
>
> Aquest càlcul tracta cada (parella × categoria) com a independent. A la pràctica utilitzarem un model de rànquing global (vegeu [§5.2](#52-reducció-amb-rànquing-global)) que redueix considerablement aquest pressupost.

## 5.2. Reducció amb rànquing global

Si fem servir un sistema de rànquing global tipus **[Bradley-Terry](https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model)** o **[Elo](https://ca.wikipedia.org/wiki/Sistema_de_puntuaci%C3%B3_Elo)** (com fa LMSYS Chatbot Arena), el sistema aprofita la transitivitat: si sabem que A > B i B > C, ja tenim informació indirecta sobre A vs C.

Això:

- Redueix significativament els vots necessaris per obtenir un rànquing estable: com a regla heurística, l'estalvi escala amb $\log_2(n)/(n-1)$ respecte al sostre de 5.1. Per a 3 models, això redueix el total de **5.775 → ~4.575 vots** (~152 h). Vegeu el [simulador](https://softcatala.github.io/arena-cat/simulador/) per ajustar els paràmetres.
- Permet treballar amb dades **desbalancejades** — no cal que totes les parelles tinguin el mateix nombre de votacions.

---

# 6. Qui fa l'avaluació

La idea és muntar una **web participativa** dins del lloc de Softcatalà on els usuaris ens ajudin a fer aquest procés. Seria similar al que vam fer amb [Common Voice](https://commonvoice.mozilla.org/), on la gent contribuïa una estona a fer tasques.

## 6.1. Test de qualificació

Abans que un usuari pugui començar a contribuir, la primera vegada haurà de fer un **petit test de 5 preguntes** per comprovar que té criteri per fer l'avaluació.

## 6.2. Registre d'usuaris

Per evitar el vandalisme i garantir la qualitat, mantindrem un **registre d'usuaris** amb nom i contrasenya.

> **Inspiració**: l'enfocament participatiu segueix la línia de [Common Voice](https://commonvoice.mozilla.org/) i [VoiceArena](https://voicearena.com/) — contribucions petites i acumulables d'una comunitat àmplia.

---

# 7. Què cal fer

Llista de feines necessàries per posar en marxa el projecte.

## 7.1. Tasques d'avaluació

- [ ] **Crear les tasques a avaluar**
    - Han de representar tasques **reals** i tenir **diferents nivells de complexitat**.
    - No és senzill: estaria bé demanar *feedback* públicament abans de tancar-les.

## 7.2. Plataforma

- [ ] **Desenvolupar l'aplicació** d'avaluació o adaptar-ne alguna d'existent.
- [ ] **Llançar el procés internament** dins de Softcatalà.
- [ ] **Fer-lo créixer** a través de xarxes socials i la web.

---

# 8. Resultats del projecte

El projecte generaria dos resultats principals:

## 8.1. Rànquing públic de models

Mantenir un **rànquing dels millors models per al català** segons preferència humana, actualitzat a mesura que arriben nous vots i nous models.

## 8.2. Conjunt de dades obertes de preferències

Un cop acabat el procés, es publicarà en obert el **conjunt de dades de preferències** amb l'estructura:

```
Prompt + Resposta A + Resposta B + Guanyador
```

> **Per què importa**: aquest conjunt de dades permetria a altres investigadors fer **RLHF** (*Reinforcement Learning from Human Feedback*) específic per al català, contribuint a millorar la qualitat dels models de la llengua a llarg termini.

---


