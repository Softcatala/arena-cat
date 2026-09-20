# Prova de competència lingüística

Valorar la competència necessària per jutjar respostes en les quatre categories d’Arena Cat, amb **dues preguntes per categoria i dues generals**. La proposta i el llindar s’han de validar amb col·laboradors de competència coneguda, respectant les variants dialectals normatives.

La implementació s’ha de fer amb **el mínim de codi possible**: reutilitzar els components, l’autenticació i els patrons existents, mantenir les dades al YAML i afegir només la lògica necessària per mostrar, corregir i acreditar la prova. Prioritzar codi simple i llegible, amb les validacions i proves necessàries; evitar dependències noves i abstraccions que no siguin imprescindibles.

## Funcionament

- **Pantalla:** pàgina separada amb un únic formulari de deu preguntes. Cada pregunta té tres opcions (A, B i C), amb selecció única i una sola resposta correcta.
- **Puntuació:** cal respondre les deu preguntes; cada encert val un punt i cada error, zero. El llindar es llegeix del YAML i s’aplica a la nota global; inicialment és **8 encerts de 10**.
- **Resultat:** substituir el formulari pel total d’encerts, el llindar i l’estat de superació, sense mostrar correccions, solucions ni desglossament per categoria. Si se supera, habilitar «Comença a avaluar»; altrament, permetre repetir.
- **Configuració:** les preguntes, les opcions de resposta, les solucions i el llindar es desen a `data/qualification.yaml`. El fitxer tindrà `min_correct: 8` i una llista `questions`; cada pregunta inclourà l’identificador, `category_code` (nul per a les generals), l’enunciat, les tres opcions, la resposta correcta i l’explicació. El backend llegeix aquesta configuració per servir i corregir la prova; les solucions i les explicacions no s’envien al client.
- **Acreditació:** afegir el camp nullable `qualified_at` a la taula `users`, amb migració Alembic i actualització de `docs/db_schema.md`. En superar la prova, el backend hi desa la data i l’hora de superació a la base de dades; mentre no se supera, el valor és `NULL`. En els accessos següents, un valor informat acredita l’usuari i evita repetir la prova. L’acreditació és global i persistent entre sessions. Dirigir els usuaris sense acreditar al formulari i rebutjar els seus vots reals al backend. Les respostes de la prova queden fora del rànquing.
- **Verificació:** comprovar el repartiment 2+2+2+2+2, els casos 7/10 i 8/10 amb el llindar inicial, que canviar `min_correct` al YAML modifica el criteri d’aprovació, una resposta vàlida A/B/C per pregunta, formularis incomplets, repetició, persistència, bloqueig de vots directes a l’API i exclusió de les respostes de prova de les estadístiques.

## Distribució

| Bloc | Preguntes | Competència |
|---|---|---|
| Correcció | 1–2 | Detectar errors i corregir-los conservant el significat. |
| Traducció | 3–4 | Entendre la llengua d’origen: condicions, excepcions i sentit figurat. |
| Reformulació | 5–6 | Preservar el contingut i adaptar el registre demanat. |
| Generació | 7–8 | Valorar el compliment de les instruccions i la coherència del text. |
| Generals | 9–10 | Reconèixer trets del català central, valencià i balear i valorar l’adequació a la varietat demanada. |

En traducció, els textos originals són en **castellà**, com els prompts actuals. Les opcions són interpretacions en català que comproven si l’usuari ha entès l’original.

## Preguntes i solucionari

Les explicacions següents documenten el criteri de correcció del qüestionari i no es mostren en el resultat.

### 1. Correcció: interrogativa indirecta

Corregeix «No sé perquè han ajornat la reunió» per expressar que desconeixem el motiu de l’ajornament.

- **A:** No sé perquè han ajornat la reunió.
- **B:** No sé per què han ajornat la reunió.
- **C:** No sé per que han ajornat la reunió.

**Correcta: B.** «Per què» equival a «per quin motiu»: s’escriu separat i amb accent. A manté l’error i C omet l’accent. [Optimot: perquè, per què i per a què](https://aplicacions.llengua.gencat.cat/llc/AppJava/index.html?action=Principal&method=detall&database=FITXES_PUB&idFont=12663&idHit=12663).

### 2. Correcció: corregir sense alterar el significat

Corregeix «L’universitat ha publicat el calendari provisional» sense canviar-ne el significat.

- **A:** La universitat ha publicat el calendari definitiu.
- **B:** L’universitat ha publicat el calendari provisional.
- **C:** La universitat ha publicat el calendari provisional.

**Correcta: C.** Corregeix l’apòstrof i conserva «provisional». A altera el significat i B manté l’error: «la» no s’apostrofa davant de la u àtona d’«universitat». [Optimot: apostrofació dels articles](https://aplicacions.llengua.gencat.cat/llc/AppJava/index.html?action=Principal&method=detall&database=FITXES_PUB&idFont=16022&idHit=16022).

### 3. Traducció: entendre una condició en la llengua d’origen

Text original: «No hace falta reservar, a menos que el grupo sea de más de seis personas.» Què indica aquest avís?

- **A:** Cal reservar si el grup té més de sis persones.
- **B:** Cal reservar si el grup té sis persones o menys.
- **C:** Cal reservar sempre, independentment del nombre de persones.

**Correcta: A.** «A menos que» introdueix l’excepció: la reserva és necessària quan se superen les sis persones. B inverteix la condició i C converteix l’excepció en una obligació general.

### 4. Traducció: entendre una expressió figurada

Text original: «Cuando le pregunté por el retraso, se fue por las ramas y no respondió.» Què va fer la persona?

- **A:** Va explicar detalladament el motiu del retard.
- **B:** Es va desviar del tema sense respondre la pregunta.
- **C:** Va marxar del lloc sense respondre la pregunta.

**Correcta: B.** «Irse por las ramas» significa desviar-se del tema. A contradiu que no va respondre i C interpreta l’expressió com un desplaçament físic.

### 5. Reformulació: conservar l’abast de la negació

Reformula «No tots els inscrits han confirmat l’assistència» sense alterar-ne el significat.

- **A:** Cap dels inscrits ha confirmat l’assistència.
- **B:** Tots els inscrits han confirmat l’assistència.
- **C:** Hi ha inscrits que no han confirmat l’assistència.

**Correcta: C.** Manté que hi ha persones que no han confirmat. A afirma més del que diu l’original i B el contradiu.

### 6. Reformulació: adaptar el registre sense afegir informació

Reformula en un registre formal: «Ei, no podré venir a la reunió de demà. Em podeu passar l’acta?» Conserva la informació original.

- **A:** Us comunico que no podré assistir a la reunió de demà i us demano que m’envieu l’acta.
- **B:** Us comunico que no podré assistir a la reunió de demà perquè tinc una visita mèdica i us demano que m’envieu l’acta.
- **C:** Ei, demà no podré venir a la reunió; passeu-me l’acta, si us plau.

**Correcta: A.** Adapta el registre i manté el contingut. B inventa el motiu de l’absència i C conserva el to col·loquial.

### 7. Generació: respectar les instruccions

Encàrrec: «Escriu un avís formal de dues frases: la biblioteca tancarà divendres per obres i tornarà a obrir dilluns. No hi afegeixis horaris.» Quina resposta el compleix?

- **A:** La biblioteca romandrà tancada divendres per obres. Tornarà a obrir dilluns.
- **B:** La biblioteca romandrà tancada divendres per obres. Tornarà a obrir dilluns a les nou del matí.
- **C:** La biblioteca romandrà tancada dilluns per obres. Tornarà a obrir divendres.

**Correcta: A.** Respecta el registre, les dues frases i les dades de l’encàrrec. B afegeix un horari i C intercanvia els dies.

### 8. Generació: mantenir la coherència

Continua amb una frase sense contradir aquest inici: «L’últim tren ja havia marxat i aquell dia no en passaria cap més. La Júlia encara havia de tornar a casa.»

- **A:** Va pujar a l’últim tren, que encara era aturat a l’andana.
- **B:** Va trucar a un taxi perquè la portés a casa.
- **C:** Va esperar el tren següent, que arribaria al cap de cinc minuts.

**Correcta: B.** Proposa una continuació compatible amb l’inici. A contradiu que l’últim tren havia marxat i C, que ja no en passarien més aquell dia.

### 9. General: reconèixer les varietats del català

Les formes «jo penso», «jo pense» i «jo pens» s’associen, respectivament, a quines varietats del català?

- **A:** Valencià, català central i balear.
- **B:** Balear, valencià i català central.
- **C:** Català central, valencià i balear.

**Correcta: C.** «Penso» és la forma habitual en català central; «pense», en valencià; i «pens», en balear. Totes tres són normatives: cal valorar-les d’acord amb la varietat demanada. [DIEC: conjugació de pensar](https://dlc.iec.cat/Verbs?IdE=0010638).

### 10. General: respectar la varietat demanada

Un encàrrec demana català balear per a un missatge entre amics de Mallorca. Quina resposta s’hi ajusta pels seus trets lingüístics?

- **A:** Aquesta tarda tinc temps per venir.
- **B:** Avui horabaixa tenc temps per venir.
- **C:** Aquesta vesprada tinc temps per venir.

**Correcta: B.** «Horabaixa» i «tenc» són formes normatives pròpies de Mallorca. A presenta trets del català central i C, del valencià. Les variants d’altres territoris no són errors, però aquí es demana català balear. [UIB: variants del present d’indicatiu](https://blocs.uib.cat/galmic/fitxa/altres-questions-del-present-dindicatiu/), [Optimot: noms de les parts del dia](https://aplicacions.llengua.gencat.cat/llc/AppJava/index.html?database=DIEC&idFont=60572&input_cercar=vesprada&method=detall&numPagina=1&tipusCerca=cerca.tot&titol=vesprada).
