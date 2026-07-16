# Arena Cat

**Avaluació humana de models d'IA en català.**

Plataforma participativa, inspirada en [LMSYS Chatbot Arena](https://lmarena.ai/), centrada exclusivament a mesurar la **competència en llengua catalana** dels models de llenguatge gran (LLMs). A diferència de les avaluacions automàtiques, aquí són persones les que comparen, a cegues, les respostes de dos models davant d'una mateixa tasca i decideixen quina és millor. Si l'experiència té èxit, la plataforma es podria **generalitzar a altres llengües** que també necessitin una avaluació humana pròpia.

Per a una explicació detallada del projecte (motivació i metodologia), consulta **[projecte.md](docs/projecte.md)**.

🧮 **Dimensionament**: estimem els vots i hores humanes necessaris amb un [simulador](docs/simulador.md). Vegeu els detalls a [avaluadors](docs/avaluadors.md).

## Vols col·laborar-hi? T'estem buscant

La primera fita del projecte, **Prova de concepte**, té **dues parts** i necessitem persones per a totes dues.

**Part 1: construcció de la plataforma.** Estem **arrencant el projecte** i busquem perfils tècnics per posar-la en marxa:

- 🤖 **Aprenentatge automàtic / IA**: per crear les canonades d'avaluació: executar la inferència dels models, gestionar els *prompts* i preparar les dades que veuran els avaluadors humans.
- 📊 **Estadística**: per dimensionar el volum d'avaluacions, validar la metodologia (Bradley-Terry / Elo) i garantir la robustesa dels rànquings.
- ⚙️ **Python**: per construir la canonada d'inferència, el *backend* (FastAPI + PostgreSQL) i la integració amb la web de Softcatalà.
- 📚 **Lingüística**: per definir els *prompts* d'avaluació de manera que cobreixin bé les dificultats reals del català (ortografia, registre, varietats dialectals, referències culturals) i fixar criteris clars per als avaluadors.

No cal que dominis totes les àrees: si t'hi veus en alguna, **escriu-nos**.

**Part 2: avaluadors voluntaris.** Un cop la plataforma estigui en marxa, **caldran moltes persones catalanoparlants** per fer les avaluacions: comparar respostes a cegues i votar quina és millor. Cada vot dura uns 2 minuts i, només per a la prova de concepte, en calen al voltant de 1.200 (vegeu el [full de ruta](#full-de-ruta)). Si tens criteri lingüístic en català i vols ajudar-nos amb una estoneta, també et volem.

Per a ajudar, envia un correu a **Jordi Mas** <jmas@softcatala.org> explicant **com pots col·laborar** i el teu **identificador de Telegram**.

## Full de ruta

El projecte avançarà per fites. La **Fita 1: Prova de concepte** (a sota) té un abast reduït (3 models, 3 categories) per provar la mecànica i la interfície. La **Fita 2: Expansió del concepte** ampliarà el nombre de models avaluats, i fites posteriors creixeran també en categories, *prompts* per categoria i objectiu de vots fins a assolir robustesa estadística.

### Fita 1: Prova de concepte

La fita té **dues parts**: primer construir la plataforma i, tot seguit, demanar a voluntaris que facin les avaluacions.

#### Part 1: Construcció de la plataforma

> Per al desglossament tècnic de les versions v1, v2 i v3, vegeu **[pla_detallat.md](docs/pla_detallat.md)**.

**Abast**

Models (3):

- Qwen 3.5 9B
- Salamandra 7B
- Gemma 4 26B A4B

Categories (3): 3 models × 3 categories prioritàries (**correcció**, **reformulació** i **traducció**), les més específiques de català, on els models globals tendeixen a fallar més, × 10 *prompts* = **30 prompts**.

Per (parella × categoria) tenim aproximadament $1.200 / 9 \approx 133$ vots. Marge ≈ **8,5%**.

> **Compromís**: sacrifiquem **amplitud** per **profunditat** en aquesta primera fita.

**Components a desenvolupar**

| Component | Detall |
|---|---|
| Preparació de les dades | 30 tasques: 10 exemples per cadascuna de les 3 categories. |
| Canonada de pre-processament | Inferència dels models seleccionats i desat en fitxers de metadades. |
| Registre d'usuaris | Alta amb consentiment explícit, verificació d'email, inici de sessió i **baixa compatible amb el RGPD** (s'esborra l'email però es preserva l'`ID` per no perdre els vots emesos). |
| Gestió d'usuaris | Test de qualificació i persistència de dades. |
| Interfície d'usuari | Pàgina a la web de Softcatalà per **registrar-se** i **avaluar**, amb indicador de l'**objectiu** i del progrés. |
| Backend | FastAPI amb endpoints d'autenticació (alta, verificació, sessió, baixa, exportació), obtenció d'una tasca aleatòria, registre d'un vot i consulta d'estadístiques. |
| Persistència | PostgreSQL + model de dades. |

**Estimació**

> **Esforç**: punt mig realista, **~120 hores de desenvolupament**.

#### Part 2: Avaluació amb voluntaris

Un cop la plataforma estigui en marxa, obrirem la convocatòria a la comunitat de Softcatalà i a les xarxes per recollir els vots necessaris.

- **Objectiu d'ús**: 40 hores de contribucions humanes (~1.200 vots), amb marge d'error ≈ **8,5%** per parella × categoria; calen **~14 avaluadors** que responguin les 90 combinacions. Detalls a [avaluadors](docs/avaluadors.md).
- **Difusió**: llançament intern dins de Softcatalà i creixement a través de xarxes socials i la web.
- **Resultat**: rànquing públic de la prova de concepte i primer lot del conjunt de dades obert de preferències.

### Fita 2: Expansió del concepte

Un cop validada la mecànica amb la prova de concepte, ampliarem l'abast incorporant **més models** a l'avaluació, mantenint la mateixa plataforma i metodologia.

## Col·laboradors

<!-- readme: contributors -start -->
<table>
	<tbody>
		<tr>
            <td align="center">
                <a href="https://github.com/jordimas">
                    <img src="https://avatars.githubusercontent.com/u/309265?v=4" width="100;" alt="jordimas"/>
                    <br />
                    <sub><b>Jordi Mas</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/ganlub">
                    <img src="https://avatars.githubusercontent.com/u/1272617?v=4" width="100;" alt="ganlub"/>
                    <br />
                    <sub><b>Albert Casanovas</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/carmencampo04">
                    <img src="https://avatars.githubusercontent.com/u/243333619?v=4" width="100;" alt="carmencampo04"/>
                    <br />
                    <sub><b>Carmen C. L.</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/bytesontherocks">
                    <img src="https://avatars.githubusercontent.com/u/44874065?v=4" width="100;" alt="bytesontherocks"/>
                    <br />
                    <sub><b>bytesontherocks</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/estevecastells">
                    <img src="https://avatars.githubusercontent.com/u/14035230?v=4" width="100;" alt="estevecastells"/>
                    <br />
                    <sub><b>Esteve Castells</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/gerardmartinezcanelles">
                    <img src="https://avatars.githubusercontent.com/u/22821004?v=4" width="100;" alt="gerardmartinezcanelles"/>
                    <br />
                    <sub><b>Gerard Martínez Canelles</b></sub>
                </a>
            </td>
		</tr>
		<tr>
            <td align="center">
                <a href="https://github.com/AntoniBrosa">
                    <img src="https://avatars.githubusercontent.com/u/125493479?v=4" width="100;" alt="AntoniBrosa"/>
                    <br />
                    <sub><b>AntoniBrosa</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/isaacnicolas">
                    <img src="https://avatars.githubusercontent.com/u/72254818?v=4" width="100;" alt="isaacnicolas"/>
                    <br />
                    <sub><b>Isaac Nicolas</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/santo0">
                    <img src="https://avatars.githubusercontent.com/u/30506769?v=4" width="100;" alt="santo0"/>
                    <br />
                    <sub><b>Martí</b></sub>
                </a>
            </td>
		</tr>
	<tbody>
</table>
<!-- readme: contributors -end -->

## Llicència

Vegeu [LICENSE](LICENSE).
