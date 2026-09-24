# Rànquing i selecció de tasques: criteris estadístics

Aquest document explica la justificació del rànquing i les seves limitacions.
La [descripció del sistema](sistema.md) recull el funcionament de l'aplicació;
el [dimensionament](avaluadors.md), les estimacions de vots i d'esforç humà.

## 1. Responsabilitats

El càlcul es divideix en tres components amb objectius diferents:

| Component | Pregunta | Implementació |
|---|---|---|
| Selecció | Quina comparació oferim a l'avaluador? | [sampler.py](../backend/app/ranking/sampler.py) |
| Rànquing | Quin ordre de preferència indiquen els vots? | [ranking.py](../backend/app/ranking/ranking.py) |
| Confiança | Com varia el resultat quan tornem a mostrejar els prompts? | [confidence.py](../backend/app/ranking/confidence.py) |

La selecció depèn dels recomptes de vots, sense utilitzar les puntuacions dels
models. El rànquing i la confiança es calculen sobre els vots de les
[versions actives dels prompts](sistema.md#versions-actives), globalment o
filtrats per categoria.

## 2. Vots i taxes de victòria

Per a cada parella, la taxa de victòria d'A sobre els vots decisius és:

```text
wins_A / (wins_A + wins_B)
```

Els empats i els vots «cap de les dues» es compten separadament i no entren a
l'ajust Bradley–Terry. Per exemple, 73 victòries d'A i 47 de B donen una taxa
del 60,8% per a A, independentment dels empats registrats.

Aquestes taxes permeten veure les comparacions directes i possibles cicles
(A guanya B, B guanya C, C guanya A), però no defineixen per si soles una
puntuació global. El mòdul calcula estadístiques per parella i detecta cicles
quan hi ha tres models; la resposta pública de l'API publica el rànquing BT,
els recomptes i la confiança. Vegeu els camps a la
[referència de l'API](../backend/README.md#get-apiranking).

## 3. Bradley–Terry

Bradley–Terry assigna a cada model una puntuació `θ`. La probabilitat que A
guanyi B s'expressa com:

```text
P(A guanya B) = exp(θ_A) / (exp(θ_A) + exp(θ_B))
             = sigmoid(θ_A - θ_B)
```

Només importen les diferències: si les puntuacions són iguals, la probabilitat
és 0,5; si `θ_A − θ_B = log(2)`, és 2/3. La implementació ajusta totes les
comparacions decisives amb `scipy.optimize.minimize`, regularització L2
(`alpha=0.01`) i puntuacions centrades perquè sumin zero. La regularització
manté puntuacions finites quan un model sempre guanya o sempre perd.

L'ajust conjunt comparteix informació entre parelles: les comparacions d'A i B
amb un tercer model també contribueixen a estimar les seves puntuacions.
L'estalvi de variància depèn de les dades i del disseny; no és un percentatge
fix garantit pel nombre de models.

L'API ofereix tant un rànquing global com un per categoria. El global agrega
tasques diferents i pot amagar especialitzacions; per això convé consultar
també els resultats de cada categoria. Un únic eix de puntuació tampoc pot
representar fidelment preferències cícliques.

Elo permet actualitzacions incrementals, però la seva regla d'actualització
depèn de l'ordre dels vots i del paràmetre d'aprenentatge. Aquí s'utilitza un
ajust conjunt sobre les respostes precomputades. TrueSkill i OpenSkill no
formen part de la implementació actual. Les referències sobre aquests mètodes
són a la [bibliografia del projecte](projecte.md#referències).

## 4. Selecció de tasques

La unitat de selecció és una combinació de prompt i parella de models. Un
mostreig uniforme entre totes les combinacions pot deixar comparacions amb
molts menys vots que d'altres, especialment amb pressupostos petits.

El selector tria a l'atzar entre les combinacions disponibles amb menys vots.
Això afavoreix la cobertura equilibrada dins de la categoria. No imposa una
quota màxima ni garanteix igualtat entre categories. L'ordre A/B també es
randomitza per reduir el biaix de posició.

Els filtres per usuari, les omissions i l'ordre de les categories es descriuen
a [selecció i registre de tasques](sistema.md#selecció-i-registre-de-tasques).
No hi ha estratègies configurables de mostreig actiu, ponderació per diversitat
ni retirada automàtica de models.

## 5. Confiança del rànquing

### 5.1. Agrupació per prompt

Els vots sobre una mateixa resposta comparteixen les característiques del
prompt. Tractar-los tots com a observacions independents pot infravalorar la
incertesa. Per això el bootstrap torna a mostrejar **prompts sencers**, amb
reemplaçament, i conserva tots els seus vots decisius.

### 5.2. Seguiment del mateix model

Calen almenys dos prompts amb vots decisius i dos models observats per calcular
la confiança. Si no es compleix aquest mínim, `p_best_is_best` i l'interval de
confiança són `null` a l'API i `is_stable` és fals. La interfície mostra
«Dades insuficients» per a la confiança i presenta l'estat que retorna
l'[API](../backend/README.md#get-apiranking), conservant les puntuacions
observades. Els prompts amb només empats o «cap de les dues» no
compten per a aquest mínim.

Primer s'ajusta BT sobre totes les dades i s'identifica el model amb la
puntuació més alta. En cada rèplica es torna a ajustar BT i es calcula:

```text
delta = puntuació del millor original − màxima puntuació dels altres models
```

El model de referència es manté fix. Si un competidor el supera en una rèplica,
`delta` és negatiu. Ordenar cada rèplica i restar simplement el primer del
segon amagaria aquests canvis de lideratge.

Per defecte es fan 1.000 rèpliques. `p_best_is_best` és la fracció amb
`delta > 0`; l'interval utilitza els percentils 2,5 i 97,5. `is_stable` indica
si el límit inferior és positiu. El backend utilitza aquest indicador per
determinar l'estat del rànquing; el selector continua oferint tasques.
No hi ha una regla automàtica d'aturada per pressupost o per confiança.

### 5.3. Limitacions

- El mínim de dos prompts evita remostrejar sempre un únic grup; no garanteix
  una estimació fiable amb mostres petites ni comprova la connexió entre models.
- Amb pocs prompts, la diversitat de mostres del bootstrap és limitada;
  molts vots sobre els mateixos prompts no equivalen a molts prompts diferents.
- L'agrupació actual és per prompt, sense modelar addicionalment la dependència
  entre vots d'un mateix avaluador, tot i que els usuaris estan identificats.
- `is_stable` és un indicador de la mostra actual, no una garantia sobre nous
  prompts, altres poblacions d'avaluadors o futurs models.
- Consultar repetidament l'interval i aturar la recollida quan exclou zero
  requeriria un disseny de prova seqüencial que ara no està implementat.

Les fórmules aproximades de marge d'error i l'anàlisi de sensibilitat a la
correlació són al [dimensionament d'avaluadors](avaluadors.md#impacte-del-nombre-davaluadors-en-el-marge-derror).
