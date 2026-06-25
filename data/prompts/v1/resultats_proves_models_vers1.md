Proves dels 10 prompts de traducció castellà→català contra els tres models comercials principals: **Gemini Flash 3.5**, **GPT 5.5** i **Claude 4.8**.

## Prompt 1 — Central (IEC), Col·loquial

**Gemini Flash 3.5**

> Fa tres dies que li demano al meu pare que truqui a la companyia perquè l'internet va lentíssim. Ell diu que ja ho ha fet, però jo m'ho confio ben poc, la veritat, perquè ahir se'm va penjar fins i tot el grup de classe tres vegades. Si això segueix així, em planto a la botiga i m'emporto el tècnic de les orelles.

**GPT 5.5**

> Fa tres dies que li demano al meu pare que truqui a la companyia perquè l'internet va lentíssim. Ell diu que ja ho ha fet, però jo en dubto bastant, la veritat, perquè ahir se'm va quedar penjat fins i tot el grup de classe tres vegades. Si això continua així, em planto a la botiga i arrossego jo mateixa el tècnic.

**Claude 4.8**

> Fa tres dies que li demano al meu pare que truqui a la companyia perquè internet va lentíssim. Ell diu que ja ho ha fet, però jo ho dubto força, la veritat, perquè ahir se'm va penjar fins i tot el grup de classe tres cops. Si això segueix així, em planto a la botiga i arrossego jo mateixa el tècnic fins aquí.

*Notes de Claude:* ha fet servir "se'm va penjar" i "cops" en lloc de "vegades" per sonar més de WhatsApp, i "força" en lloc de "bastant". Ha mantingut "jo mateixa" perquè qui parla és una noia. Oferia ajustar-ho encara més desenfadat amb abreviatures tipus "pq".

\---

## Prompt 2 — Central (IEC), Jurídic

**Gemini Flash 3.5**

> Es comunica a tots els propietaris que, en la reunió celebrada el dia 14 de maig, la comunitat va acordar per majoria simple aprovar el llevat extraordinari per a la reparació de la façana. Si no s'abona l'import en el termini estipulat, es procedirà de conformitat amb la normativa de propietat horitzontal vigent.

**GPT 5.5**

> Es comunica a tots els propietaris que, en la reunió celebrada el dia 14 de maig, la comunitat va acordar, per majoria simple, aprovar una derrama extraordinària destinada a la reparació de la façana. En cas que l'import no sigui abonat dins el termini establert, s'actuarà d'acord amb la normativa vigent en matèria de propietat horitzontal.

**Claude 4.8**

> Es comunica a tots els propietaris que, en la reunió celebrada el dia 14 de maig, la comunitat va acordar per majoria simple aprovar la derrama extraordinària per a la reparació de la façana. En cas que no s'aboni l'import en el termini convingut, s'actuarà de conformitat amb la normativa de propietat horitzontal vigent.

*Notes de Claude:* justifica "termini convingut" en lloc de calcar "tiempo convenido", i la construcció "en cas que" + subjuntiu com a pròpia del registre jurídic.

> \\\\\\\*\\\\\\\*Observació:\\\\\\\*\\\\\\\* Gemini tradueix "derrama" per \\\\\\\*\\\\\\\*"llevat"\\\\\\\*\\\\\\\*, terme que normalment significa "rent" (de pa) — sembla un error, no una variant vàlida. GPT i Claude mantenen "derrama extraordinària".

\---

## Prompt 3 — Central (IEC), Infantil

**Gemini Flash 3.5**

> El somni de la petita puça. Un petit poll tenia moltes ganes de volar i ho desitjava tant, de tot cor, que va cridar totes les mosques que tenia a prop. Des d'aquell dia, el poll es va convertir en el rei dels viatges pels aires!

**GPT 5.5**

> Hi havia una vegada un poll petit que volia volar. Ho desitjava tan i tan fort que, de cop, va fer venir totes les mosques que tenia al seu voltant. Des d'aquell dia, el poll es va fer molt important i va tenir un munt de mosques que l'ajudaven a viatjar per l'aire. Per això, tothom deia que era el rei dels viatges voladors.

**Claude 4.8**

> Hi havia una vegada un poll molt petit que volia volar. I ho desitjava tant, tant, tant, que va cridar totes les mosques que tenia al voltant perquè vinguessin. I saps què va passar? Doncs que des d'aquell dia el poll es va convertir en el rei dels viatges per l'aire!

*Notes de Claude:* ha afegit recursos narratius típics de conte ("Hi havia una vegada", "I saps què va passar?") i ha convertit "magnate del transporte aéreo" en "el rei dels viatges per l'aire" per adequar-ho a un nen.

> \\\\\\\*\\\\\\\*Observació:\\\\\\\*\\\\\\\* els tres models convergeixen cap a la mateixa idea ("rei dels viatges..."), confirmant el risc de baixa entropia en aquest prompt.

\---

## Prompt 4 — Valencià (AVL), Col·loquial

**Gemini Flash 3.5**

> Hola, xics! Ja sabeu que el divendres fem pont, així que, què vos pareix si anem prompte per a agafar un bon lloc abans que s'ompli la platja de gent? Si algú vol portar els xiquets, hi ha una zona de jocs prop. Jo porte l'ombrel·la i les cervesetes, però algú s'ha d'encarregar del menjar. Qui s'anima?

**GPT 5.5**

> Hola, xics! Ja sabeu que divendres fem pont, així que què vos pareix si anem prompte per agafar un bon lloc abans que la platja s'òmpliga de gent? Si algú vol portar els menuts, hi ha una zona de jocs a prop. Jo porte el para-sol i les cervesetes, però algú s'haurà d'encarregar del menjar. Qui s'anima?

**Claude 4.8**

> Bon dia, xics! Ja sabeu que el divendres fem pont, així que, què vos pareix si anem ben enjorn per a agarrar un bon lloc abans que s'òmpliga la platja de gent? Si algú vol portar els xicotets, hi ha una zona de jocs a prop. Jo porte el para-sol i les cervesetes, però algú s'ha d'encarregar del menjar. Qui s'anima?

*Notes de Claude:* destaca l'ús de "vos", "porte", "pareix" (morfologia valenciana), "xics"/"xicotets", "ben enjorn" per "tempranito" i "agarrar" per "pillar".

> \\\\\\\*\\\\\\\*Observació:\\\\\\\*\\\\\\\* GPT no usa cap forma de tractament "xiquets/menuts" diferenciada de Gemini/Claude (usa "menuts", més neutre); Gemini i Claude trien "xiquets"/"xicotets" (més marcadament valencians).

\---

## Prompt 5 — Valencià (AVL), Jurídic

**Gemini Flash 3.5**

> Notificació sobre l'estat de l'enviament. Per la present, us informem que la lliurament de la vostra comanda patirà un retard a causa de problemes logístics. Si la demora es perllongara més de huit dies, tindreu dret a cancel·lar la comanda sense cap cost, de conformitat amb el que establixen les nostres Condicions Generals de Venda.

**GPT 5.5**

> Per la present, l'informem que la seua comanda patirà un retard en l'entrega a causa de problemes logístics. En cas que el retard es prolongara més de huit dies, vosté tindrà dret a cancel·lar la seua comanda sense cap cost, de conformitat amb el que establixen les nostres Condicions Generals de Venda.

**Claude 4.8**

> Per la present, l'informem que la seua comanda patirà una demora en el lliurament a causa de problemes logístics. En cas que el retard es prolongara més de huit dies, vosté tindrà dret a cancel·lar la comanda sense cap cost, de conformitat amb el que estableixen les nostres Condicions Generals de Venda.

*Notes de Claude:* destaca l'ús de "la seua" i "vosté" (formes pròpies del valencià formal) i "huit" amb grafia AVL.

> \\\\\\\*\\\\\\\*Observació:\\\\\\\*\\\\\\\* Gemini manté el tractament "vostè/vostra" (us informem, vostra comanda, tindreu), mentre que GPT i Claude usen "vosté/seua" (formes pròpies valencianes). Diferència real i detectable.

\---

## Prompt 6 — Valencià (AVL), Infantil

**Gemini Flash 3.5**

> Per què plou? Quan el cel es posa trist, els seus núvols s'omplin d'aigua i ja no poden aguantar-la més. Llavors deixen caure les seues gotetes, i això és el que anomenem pluja. Quan s'acaba, el sol torna a eixir i ho seca tot amb la seua llumeta.

**GPT 5.5**

> Quan el cel es posa trist, els seus núvols s'omplin d'aigua i ja no poden aguantar-ne més. Aleshores deixen caure les seues gotetes, i això és el que anomenem pluja. Quan la pluja s'acaba, el sol torna a eixir i eixuga cada raconet amb la seua llum.

**Claude 4.8**

> Saps què passa quan el cel es posa tristet? Doncs que els seus núvols s'omplin d'aigua, i tanta n'arrepleguen que ja no poden aguantar més! Llavors deixen caure les seues gotetes, i això és el que nosaltres anomenem pluja. I quan acaba, el sol torna a eixir i ho asseca tot, tot, tot, rincó a rincó, amb la seua llumeta.

*Notes de Claude:* assenyala que "rincó" és castellanisme i que la forma normativa valenciana seria "racó".

> \\\\\\\*\\\\\\\*Observació:\\\\\\\*\\\\\\\* els tres mantenen "seus/seues" (possessiu valencià), i "eixir" en lloc de "sortir" — bons marcadors consistents.

\---

## Prompt 7 — Balear (IEC), Col·loquial

**Gemini Flash 3.5**

> Al·lots, si cercau on dinar aquest cap de setmana, vos recoman un lloc nou devora \\\\\\\*\\\\\\\*el port\\\\\\\*\\\\\\\*, prop de \\\\\\\*\\\\\\\*la plaça\\\\\\\*\\\\\\\*. El menú no és gens barat, però val cada euro que costa. Això sí, s'ha de reservar. Hi anam?

**GPT 5.5**

> Al·lots, si cercau on anar a menjar aquest cap de setmana, vos recoman un lloc nou devora \\\\\\\*\\\\\\\*es port\\\\\\\*\\\\\\\*, prop de \\\\\\\*\\\\\\\*sa plaça\\\\\\\*\\\\\\\*. Es menú no és gens barat, però val cada euro que costa. Això sí, s'ha de reservar. Hi anam?

**Claude 4.8**

> Al·lots, si cercau on menjar aquest cap de setmana, vos recoman un lloc nou devora \\\\\\\*\\\\\\\*es port\\\\\\\*\\\\\\\*, prop de \\\\\\\*\\\\\\\*sa plaça\\\\\\\*\\\\\\\*. Es menú no és gens barat, però val cada euro que costa. Això sí, s'ha de reservar. Hi anam?

*Notes de Claude:* destaca l'article salat ("es port", "sa plaça", "es menú") i "devora" com a tret balear genuí.

> \\\\\\\*\\\\\\\*Observació important:\\\\\\\*\\\\\\\* \\\\\\\*\\\\\\\*Gemini Flash 3.5 NO aplica l'article salat\\\\\\\*\\\\\\\* ("el port", "la plaça" — article literari), mentre que GPT i Claude sí ("es port", "sa plaça").

\---

## Prompt 8 — Balear (IEC), Jurídic

**Gemini Flash 3.5**

> Clàusula de pagament de la renda. El llogater es compromet a abonar la quantitat de 600 euros en concepte de lloguer abans del dia cinc de cada mes. En cas d'impagament, el propietari podrà reclamar els diners deguts juntament amb els interessos corresponents, de conformitat amb el que s'estableix en el contracte d'arrendament.

**GPT 5.5**

> L'arrendatari es compromet a abonar la quantitat de 600 euros en concepte de lloguer abans del dia cinc de cada mes. En cas d'impagament, l'arrendador podrà reclamar la quantitat deguda, juntament amb els interessos corresponents, d'acord amb el que estableix el contracte d'arrendament.

**Claude 4.8**

> El llogater es compromet a abonar la quantitat de 600 euros en concepte de lloguer abans del dia cinc de cada mes. En cas d'impagament, el propietari podrà reclamar els diners deguts juntament amb els interessos corresponents, de conformitat amb el que estableix el contracte d'arrendament.

*Notes de Claude:* explica que en textos jurídics balears NO s'usa l'article salat (queda reservat a la parla col·loquial), per això manté "el llogater", "el propietari" en literari — coherent amb el que s'havia previst per a aquest prompt.

> \\\\\\\*\\\\\\\*Observació:\\\\\\\*\\\\\\\* GPT tria "arrendatari/arrendador" (terminologia més general/castellanitzant), mentre que Gemini i Claude trien "llogater/propietari" (més habituals en català).

\---

## Prompt 9 — Balear (IEC), Infantil

**Gemini Flash 3.5**

> S'hora d'anar a dormir. Quan arriba la nit, la nina es posa es seu pijama preferit i es fica dins es llit amb es seu osset de peluix. Des de la finestra es veu es cel ple d'estels i un d'ells li canta una bressola amb una veu molt baixeta, perquè pugui dormir ben d'hora.

**GPT 5.5**

> Quan arriba la nit, sa nina es posa es seu pijama preferit i se fica dins es llit amb es seu osset de peluix. Des de sa finestra es veu es cel ple d'estrelles, i una d'elles li canta una cançó de bressol amb una veu molt fluixeta, perquè pugui dormir ben tranquil·la.

**Claude 4.8**

> Saps què passa quan arriba sa nit? Idò que sa nina es posa es pijama que més li agrada i s'afica dins es llit amb so seu osset de peluix. I des de sa finestra es veu es cel ple d'estels, i un d'aquests estels li canta una cançoneta ben fluixet, ben fluixet, perquè pugui dormir bé i tengui bons somnis.

*Notes de Claude:* destaca "idò", "nina", "afica", "tengui" (morfologia balear) i la combinació "amb so seu" (article salat + possessiu).

> \\\\\\\*\\\\\\\*Observació:\\\\\\\*\\\\\\\* Gemini no aplica l'article salat a "la nina" (hi manté article literari a l'inici), però sí a la resta del text ("es seu pijama", "es llit") — aplicació inconsistent dins del mateix model.

\---

## Prompt 10 — Central (IEC), Col·loquial (sense anglicismes)

**Gemini Flash 3.5**

> Des que vaig a córrer de bon matí em trobo molt millor, tot i que al principi em va costar agafar el ritme. Ara vaig al gimnàs tres dies a la setmana per fer manteniment. La meva entrenadora diu que, si continuo així, en un mes notaré un canvi brutal.

**GPT 5.5**

> Des que surto a córrer als matins em trobo molt millor, tot i que al principi em va costar agafar el ritme. Ara vaig al gimnàs tres dies a la setmana per fer exercici físic. La meva entrenadora diu que, si continuo així, d'aquí a un mes notaré un canvi espectacular.

**Claude 4.8**

> D'ençà que surto a córrer al matí em sento molt millor, encara que al principi em va costar agafar el ritme. Ara vaig al gimnàs tres dies a la setmana per posar-me en forma. La meva entrenadora diu que, si segueixo així, d'aquí a un mes notaré un canvi bestial.

*Notes de Claude:* explica les tres solucions triades per a "footing" ("sortir a córrer"), "gym" ("gimnàs") i "fitness" ("posar-me en forma"), i justifica el canvi de "brutal" per "bestial".

> \\\\\\\*\\\\\\\*Observació:\\\\\\\*\\\\\\\* "fitness" genera tres solucions diferents (manteniment / exercici físic / posar-me en forma) — bon punt de discrepància. Tots tres eviten correctament els anglicismes.

\---

## Resum de troballes

1. **Problema de disseny (prompts 1 i 7):** la instrucció "tractament de tu" no es pot comprovar al prompt 1 (no hi ha interlocutor explícit) i entra en contradicció amb el text al prompt 7 (els tres models usen "vos", plural, perquè el text s'adreça a un grup).
2. **Article salat balear (prompts 7 i 9):** discrimina bé entre models — Gemini no l'aplica de manera fiable, GPT i Claude sí.
3. **Possible error de Gemini (prompt 2):** tradueix "derrama" per "llevat", terme amb un significat diferent ("rent" de pa).
4. **Convergència confirmada (prompt 3):** els tres models arriben a variacions mínimes d'una mateixa solució per a "magnate del transporte aéreo".
5. **Notes explicatives de Claude:** Claude afegeix notes i oferiments d'ajust a la pràctica totalitat de les respostes — cal afegir una instrucció explícita als prompts per evitar-ho i mantenir la cegesa de la comparació.

