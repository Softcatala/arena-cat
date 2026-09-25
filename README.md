# Arena Cat

**Avaluació humana de models d'IA en català.**

Plataforma participativa, inspirada en [LMSYS Chatbot Arena](https://lmarena.ai/), centrada exclusivament a mesurar la **competència en llengua catalana** dels models de llenguatge gran (LLMs). A diferència de les avaluacions automàtiques, aquí són persones les que comparen, a cegues, les respostes de dos models davant d'una mateixa tasca i decideixen quina és millor. Si l'experiència té èxit, la plataforma es podria **generalitzar a altres llengües** que també necessitin una avaluació humana pròpia.

🧮 **Dimensionament**: estimem els vots, les hores humanes i els usuaris necessaris si cadascun ho avalua tot amb un [simulador](https://softcatala.github.io/arena-cat/simulador/). Vegeu els detalls a [avaluadors](docs/avaluadors.md).

## Documentació

| Document | Contingut |
|---|---|
| [Projecte](docs/projecte.md) | Motivació i metodologia d'avaluació |
| [Sistema](docs/sistema.md) | Arquitectura, dades, models, versionatge, votació, rànquing i desplegament |
| [Backend](backend/README.md) | Entorn de desenvolupament, API, proves i migracions |
| [Frontend](frontend/README.md) | Execució i configuració de la interfície web |
| [Canonada d'inferència](scripts/README.md) | Generació, anàlisi i càrrega de respostes |

## Posada en marxa local

Requisits: Docker i Docker Compose. Revisa la configuració de
[`.env.example`](.env.example); `make run` la copia a `.env` si encara no existeix.

Des de l'arrel del repositori:

```bash
make run  # arrenca PostgreSQL, aplica les migracions i inicia l'API i la interfície
```

L'API queda disponible a `http://127.0.0.1:8000` i la interfície a
`http://127.0.0.1:5173`. Els canvis al codi de l'API i de la interfície es
recarreguen automàticament. Les dependències del frontend s'instal·len en un
volum de Docker.

En una altra terminal, carrega les dades de referència (requereix
[`uv`](https://docs.astral.sh/uv/)):

```bash
make load_reference_inferences  # carrega les dades de la branca dades_inferencia
```

La interfície permet completar la qualificació abans de votar. Per executar
proves del backend a l'amfitrió, prepara l'entorn amb `make setup`. Per executar
la interfície fora de Docker, consulta la [guia del frontend](frontend/README.md).

`make run` deixa els serveis en primer pla. Per aturar-los, prem `Ctrl+C`; per
eliminar els contenidors aturats, executa `docker compose down`.

Per generar inferències pròpies, consulta la [guia de la canonada](scripts/README.md).
La configuració dels serveis i la càrrega en producció es descriuen a
[execució i desplegament](docs/sistema.md#execució-i-desplegament).

També hi ha objectius per a tasques habituals:

```bash
make test     # executa els tests del backend
make check    # executa Ruff
make format   # formata el codi del backend amb Ruff

make frontend-check  # comprova tipus i format del frontend
```

## Vols col·laborar-hi? T'estem buscant

Busquem persones per mantenir i ampliar la plataforma i per participar en les avaluacions.

**Desenvolupament i dades.** Hi pots contribuir des de diferents àmbits:

- 🤖 **Aprenentatge automàtic / IA**: per crear les canonades d'avaluació: executar la inferència dels models, gestionar els *prompts* i preparar les dades que veuran els avaluadors humans.
- 📊 **Estadística**: per dimensionar el volum d'avaluacions, validar la metodologia (Bradley-Terry / Elo) i garantir la robustesa dels rànquings.
- ⚙️ **Python**: per millorar la canonada d'inferència i el *backend* (FastAPI + PostgreSQL).
- 📚 **Lingüística**: per definir els *prompts* d'avaluació de manera que cobreixin bé les dificultats reals del català (ortografia, registre, varietats dialectals, referències culturals) i fixar criteris clars per als avaluadors.

No cal que dominis totes les àrees: si t'hi veus en alguna, **escriu-nos**.

**Avaluadors voluntaris.** Necessitem persones catalanoparlants per comparar respostes a cegues i votar quina és millor. Cada vot dura aproximadament 2 minuts; vegeu les estimacions al [dimensionament d'avaluadors](docs/avaluadors.md). Si tens criteri lingüístic en català i vols ajudar-nos amb una estoneta, també et volem.

Per a ajudar, envia un correu a **Jordi Mas** <jmas@softcatala.org> explicant **com pots col·laborar** i el teu **identificador de Telegram**.

## Full de ruta

Amb la prova de concepte completada, la propera fita és ampliar el nombre de models avaluats. Les fites posteriors ampliaran també les categories, els *prompts* per categoria i l’objectiu de vots fins a assolir robustesa estadística.

### Fita 2: Expansió del concepte

Ampliarem l'abast incorporant **més models** a l'avaluació, mantenint la mateixa plataforma i metodologia.

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
            <td align="center">
                <a href="https://github.com/NoOPeEKS">
                    <img src="https://avatars.githubusercontent.com/u/73296276?v=4" width="100;" alt="NoOPeEKS"/>
                    <br />
                    <sub><b>Arnau Berenguer Jiménez</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/lequims">
                    <img src="https://avatars.githubusercontent.com/u/98519?v=4" width="100;" alt="lequims"/>
                    <br />
                    <sub><b>Miquel Piulats</b></sub>
                </a>
            </td>
		</tr>
	</tbody>
</table>
<!-- readme: contributors -end -->

## Llicència

Vegeu [LICENSE](LICENSE).
