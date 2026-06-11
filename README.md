# Arena Cat

**Avaluació humana de models d'IA en català.**

Plataforma participativa, inspirada en [LMSYS Chatbot Arena](https://lmarena.ai/), centrada exclusivament a mesurar la **competència en llengua catalana** dels models de llenguatge gran (LLMs). A diferència de les avaluacions automàtiques, aquí són persones les que comparen, a cegues, les respostes de dos models davant d'una mateixa tasca i decideixen quina és millor.

Per a una explicació detallada del projecte (motivació i metodologia), consulta **[projecte.md](projecte.md)**.

🧮 **[Simulador de dimensionament](https://softcatala.github.io/arena-cat/simulador/)**: calcula quants vots i hores humanes calen segons el nombre de models, categories, marge d'error i mètode d'agregació (parelles independents o Bradley-Terry / Elo).

## Vols col·laborar-hi? T'estem buscant

El projecte té **dues fases** i necessitem persones per a totes dues.

**Fase 1: construcció de la plataforma.** Estem **arrencant el projecte** i busquem perfils tècnics per posar-la en marxa:

- 🤖 **Aprenentatge automàtic / IA**: per crear les canonades d'avaluació: executar la inferència dels models, gestionar els *prompts* i preparar les dades que veuran els avaluadors humans.
- 📊 **Estadística**: per dimensionar el volum d'avaluacions, validar la metodologia (Bradley-Terry / Elo) i garantir la robustesa dels rànquings.
- ⚙️ **Python**: per construir la canonada d'inferència, el *backend* (FastAPI + PostgreSQL) i la integració amb la web de Softcatalà.
- 📚 **Lingüística**: per definir els *prompts* d'avaluació de manera que cobreixin bé les dificultats reals del català (ortografia, registre, varietats dialectals, referències culturals) i fixar criteris clars per als avaluadors.

No cal que dominis totes les àrees: si t'hi veus en alguna, **escriu-nos**.

**Fase 2: avaluadors voluntaris.** Un cop la plataforma estigui en marxa, **caldran moltes persones catalanoparlants** per fer les avaluacions: comparar respostes a cegues i votar quina és millor. Cada vot dura uns 2 minuts i, només per a la fita 1.0, en calen al voltant de 1.200 (vegeu el [full de ruta](#full-de-ruta)). Si tens criteri lingüístic en català i vols ajudar-nos amb una estoneta, també et volem.

Per a ajudar, envia un correu a **Jordi Mas** <jmas@softcatala.org> explicant **com pots col·laborar** i el teu **identificador de Telegram**.

## Full de ruta

El projecte avançarà per fites. La **Fita 1.0: Validació del concepte** (a sota) té un abast reduït (3 models, 3 categories) per provar la mecànica i la interfície. En *fites posteriors* ampliarem models, categories, *prompts* per categoria i objectiu de vots fins a assolir robustesa estadística.

### Fita 1.0: Validació del concepte

**Objectiu d'ús**: 40 hores de contribucions humanes.

#### Abast

**Models (3)**

- Qwen 3.5 9B
- Salamandra 7B
- Gemma 4 26B A4B

**Categories (3)**

3 models × 3 categories prioritàries (**correcció**, **cultura** i **traducció**), les més específiques de català, on els models globals tendeixen a fallar més, × 10 *prompts* = **30 prompts**.

Per (parella × categoria) tenim aproximadament $1.200 / 9 \approx 133$ vots. Marge ≈ **8,5%**.

> **Compromís**: sacrifiquem **amplitud** per **profunditat** en aquesta primera fita.

#### Components a desenvolupar

| Component | Detall |
|---|---|
| Preparació de les dades | 30 tasques: 10 exemples per cadascuna de les 3 categories. |
| Canonada de pre-processament | Inferència dels models seleccionats i desat en fitxers de metadades. |
| Gestió d'usuaris | Test de qualificació i persistència de dades. |
| Interfície d'usuari | Pàgina a la web de Softcatalà per **registrar-se** i **avaluar**, amb indicador de l'**objectiu** i del progrés. |
| Backend | FastAPI amb tres endpoints: obtenir una tasca aleatòria, registrar un vot i consultar estadístiques. |
| Persistència | PostgreSQL + model de dades. |

#### Estimació

> **Esforç**: punt mig realista, **~120 hores de desenvolupament**.

## Llicència

Vegeu [LICENSE](LICENSE).
