# Registro de decisiones

Cada decisión importante del proyecto: qué se decidió, por qué y qué alternativa se descartó. Cuando una decisión nació de un error, también se cuenta el error, porque es lo que más enseña.

---

## 1. Solo datos inventados, nunca datos de candidatos reales

**Decisión.** Trabajar con una cuenta de Zoho Recruit solo para pruebas, con 50 candidatos inventados con Faker.

**Por qué.**
- No se pueden usar datos de candidatos reales: esas personas dieron sus datos para un proceso de selección concreto, no para un proyecto de aprendizaje. Usarlos para otra cosa choca con el RGPD (limitación de la finalidad).
- Conectar el servidor a datos reales habría hecho pasar datos personales por la IA, justo lo contrario de la minimización.
- Con datos falsos se puede probar sin miedo, incluso cambiar fases o hacer cargas que salgan mal.

**Alternativa descartada.** Usar datos reales "solo para leer". Seguía exponiéndolos a la IA.

---

## 2. Que el servidor devuelva solo nombre, puesto y fase

**Contexto.** Cada candidatura que Zoho envía incluye muchos más campos: email, móvil, reclutador asignado (con su email personal), cliente, moneda, fechas…

**Decisión.** La función `minimizar` del servidor se queda solo con **nombre, puesto y fase**.

**Por qué.** Es lo único que necesita la IA para responder sobre el proceso de selección. Todo lo que devuelve una herramienta lo lee la IA y puede acabar en una respuesta.

**Cómo se comprobó.** Se añadieron a Zoho móviles, direcciones y salarios falsos. Zoho sí manda el móvil al servidor, pero en la respuesta del servidor a la IA no aparece ningún móvil, email, salario ni calle.

**Alternativa descartada.** Devolver el registro completo de Zoho y confiar en que la IA no use lo que no necesita.

**Actualización.** Desde la decisión 11, el nombre tampoco sale: se sustituye por un código.

---

## 3. Llaves propias y mínimas para el servidor

**Contexto.** Para la carga inicial hicieron falta llaves con permisos amplios (`ZohoRecruit.modules.ALL` y `ZohoRecruit.settings.ALL`), que incluso pueden borrar.

**Decisión.** El servidor usa otras llaves que solo pueden **leer candidaturas** y **cambiar el estado de un candidato**.

**Por qué.** Si la IA se equivoca o alguien abusa del servidor, no puede borrar ni ver nada más. La minimización no es solo de datos, también de permisos.

**Cómo se comprobó.** `comprobar_permisos.py` intenta cada operación (las escrituras con datos vacíos o ids que no existen, para no cambiar nada). Zoho niega a las llaves del servidor leer fichas de candidatos, leer vacantes, editar vacantes y borrar.

**Matiz.** El permiso de leer candidaturas deja al servidor **recibir** también email y móvil, porque vienen dentro de cada candidatura. Por eso hace falta además la decisión 2: las dos capas se complementan.

---

## 4. Anular las llaves de carga al terminar

**Decisión.** Cuando terminó la carga de datos, las llaves amplias se anularon en Zoho y se quitaron de `.env`.

**Por qué.** Unas llaves con mucho poder solo deben existir mientras hacen falta. Es minimización aplicada al tiempo.

**Consecuencia.** `cargar_en_zoho.py` y `actualizar_datos_zoho.py` ya no funcionan tal cual. Si hiciera falta otra carga, se generan llaves nuevas con `obtener_token.py` y se anulan al acabar.

---

## 5. Confirmación obligatoria escrita en el código

**Decisión.** `cambiar_fase` sin `confirmar=True` nunca cambia nada: solo devuelve "esto cambiaría a X de A a B". El cambio exige una segunda llamada, después de que la persona lo apruebe.

**Por qué.** Así, un malentendido de la IA no se convierte en un cambio real. La regla está en el servidor, no depende de que la IA "se porte bien".

**Alternativa descartada.** Confiar solo en que Claude pida permiso antes de usar la herramienta. Es útil, pero no garantiza el paso de "primero enseño qué cambiaría".

**Refuerzos.** Si el nombre coincide con varias personas (por ejemplo, "Hierro"), o la fase no existe, la herramienta se niega y pide concretar.

---

## 6. Avisar, en vez de bloquear, al marcar a alguien como contratado

**Contexto (error).** En la primera carga, al marcar a un candidato como *Contratado*, Zoho dio la vacante por cubierta (tenía 1 puesto), la cerró, archivó a los demás candidatos en proceso y bloqueó la vacante. 27 candidatos no se pudieron cargar y 15 quedaron archivados. Había además una regla en Zoho que cierra la vacante al contratar.

**Cómo se arregló.** Se reabrieron las 5 vacantes y se subió su número de puestos a 10. Se comprobó con un solo candidato que marcar *Contratado* ya no cerraba la vacante. Después se recuperaron los archivados (cambiarles el estado los saca del archivo) y se cargó el resto, **dejando a los contratados para el final**. `cargar_en_zoho.py` ahora hace eso siempre y se para si una vacante fuera a llenarse.

**Decisión para el servidor.** Antes de confirmar un *Contratado*, `cambiar_fase` **avisa** de que la vacante podría cerrarse.

**Por qué avisar y no bloquear.** Para bloquear, el servidor tendría que leer el número de puestos de cada vacante, y eso exige darle permiso para leer vacantes. Se eligió no ampliar permisos.

**Alternativa descartada (de momento).** Añadir el permiso de leer vacantes y bloquear. Es un equilibrio entre seguridad (evitar el error) y minimización (menos permisos). Se puede revisar.

---

## 7. Sacar los archivos de datos de la carpeta del proyecto

**Contexto (error).** Probando desde Claude Code, se preguntó por el email de un candidato. El servidor no lo da, así que Claude fue a buscarlo por su cuenta en `candidatos.json`, que seguía en la carpeta y estaba desactualizado. En la misma carpeta estaba `candidatos_zoho.csv`, con los emails.

**Decisión.** Mover `candidatos.json` y `candidatos_zoho.csv` a `~/developer/mcp-rrhh-datos`, fuera del proyecto y de git.

**Por qué.** La minimización del servidor sirve de poco si la IA tiene otra puerta abierta a los mismos datos. Hay que mirar **todos** los caminos por los que la IA puede llegar a los datos, no solo el conector.

**Matiz.** Las versiones antiguas de esos archivos siguen en el historial de git (son datos falsos y el repositorio es privado). Con datos reales, nunca deben llegar a git: borrarlos después no los quita del historial.

---

## 8. Probar la minimización desde el Chat, no desde Claude Code

**Decisión.** Claude Code se usa para programar el servidor. Las pruebas "como usuaria de RRHH" se hacen desde el Chat de la app de escritorio.

**Por qué.** En Claude Code, Claude también puede leer archivos y ejecutar comandos, así que no es una prueba limpia de lo que el servidor deja ver. En el Chat solo tiene las herramientas del servidor.

**Matiz.** El Chat tiene permiso para acceder a la carpeta `developer/GitHub`. Por eso fue importante que los datos estén en `developer/mcp-rrhh-datos`, fuera de ella.

---

## 9. Registrar cada llamada al servidor

**Decisión.** Cada uso de una herramienta queda anotado en `~/developer/mcp-rrhh-datos/registro_mcp.csv`: fecha, herramienta, qué se pidió (incluido si se pidió con confirmación) y qué se devolvió.

**Por qué.** Da trazabilidad: se puede comprobar qué hizo la IA y demostrar que la confirmación se respetó.

**Matiz.** El registro contiene nombres de candidatos, así que sigue la misma regla que los demás datos: fuera del proyecto y de git. Las llamadas anteriores a esta decisión no quedaron registradas; solo los cambios de fase dejaron rastro en Zoho (pestaña *Timeline*, comentario "Cambiado desde el servidor MCP").

---

## 10. Usar los estados de Zoho en lugar de inventar los nuestros

**Contexto.** Los candidatos de prueba tenían 6 fases propias (*Criba curricular, Entrevista RRHH, Entrevista técnica, Oferta enviada, Contratado, Descartado*). Zoho tiene sus propios estados por candidatura, en el *Hiring Pipeline*.

**Decisión.** Traducir a los estados de Zoho (*En revisión, Entrevista programada, Oferta realizada, Contratado, Rechazado*) y que el servidor trabaje con ellos.

**Por qué.** Es como se encontraría en cualquier empresa real, y evita mantener dos listas. Los valores se tomaron de la API (que usa nombres internos en inglés, como `Interview-Scheduled`), no de las pantallas, porque la traducción de Zoho al español tiene errores (por ejemplo, dos etapas que aparecen como "Contratado").

**Consecuencia.** *Entrevista RRHH* y *Entrevista técnica* acabaron en el mismo estado, *Entrevista programada*.

---

## 11. Seudonimizar: la IA solo ve códigos

**Decisión.** `listar_candidatos` y `buscar_candidatos` devuelven un código estable por candidato (C-0001…) en lugar del nombre. `cambiar_fase` recibe el código, no el nombre.

**Por qué.**
- El nombre no hace falta para responder sobre el proceso. Con el código, la IA puede trabajar igual.
- Si `cambiar_fase` aceptara nombres, la IA los escribiría en sus peticiones y viajarían al modelo igualmente.

**Cómo se hizo.** La clave de la tabla es el ID de candidato de Zoho: no cambia si se corrige el nombre y no mezcla a dos personas que se llamen igual. La tabla (`codigos_candidatos.json`) vive con los demás datos, fuera del proyecto y de git, y nunca se devuelve a la IA.

**Alternativa descartada.** Un hash del nombre. Se puede revertir probando nombres comunes (lo explica la guía de la AEPD sobre el hash).

---

## 12. Reidentificar solo fuera de la IA

**Contexto.** Al probar el agente, apareció el problema contrario: la IA cambió la fase de C-0042, pero yo no tenía forma de saber quién era C-0042 en Zoho.

**Decisión.** `quien_es.py` traduce un código a nombre. Se usa en la Terminal y **no** es una herramienta del servidor, así que la IA no puede usarla.

**Por qué.** La seudonimización tiene dos direcciones: la IA no debe poder volver al nombre; la persona responsable sí. El RGPD lo prevé: la información que permite reidentificar se guarda aparte y solo la usan quienes están autorizados.

---

## 13. Un agente propio con un hook que pregunta a una persona

**Decisión.** `agente.py` habla con Claude por la API y usa el servidor como única vía de acceso a los datos. Antes de ejecutar cualquier `cambiar_fase` con `confirmar=True`, un hook para y pregunta en la Terminal "¿Confirmas el cambio? (s/n)".

**Por qué.** La decisión 5 dejó la regla en el servidor, pero el valor de `confirmar` lo rellena la IA. Si se equivoca o la manipulan, se confirma sola. El hook vive en el código del agente, fuera del alcance del modelo.

**Error que enseñó algo.** La primera versión solo aceptaba "s". Respondí "si" y lo trató como un no. Fue un fallo seguro (no cambió nada), pero inútil. Ahora acepta "s", "si" y "sí"; cualquier otra cosa sigue siendo un no.

**Lo que se vio en la prueba real.** Tras el rechazo, escribí "si, adelante" como mensaje normal. El agente no reintentó el cambio por su cuenta: pidió una autorización explícita. Con el hook corregido, el cambio llegó a Zoho (pestaña *Timeline*, 19:25 del 31 de octubre) y después se devolvió a su fase.

**Modelo.** Claude Haiku 5.5. La privacidad no depende del modelo, así que se elige por coste: una consulta costó unos 0,0004 dólares.

---

## 14. Registrar cada decisión humana

**Decisión.** Cada "sí" o "no" en el hook queda en `registro_decisiones.csv`, fuera de git.

**Por qué.** La nota de la AEPD sobre sistemas algorítmicos en el ámbito laboral (7 de octubre de 2026) pide que la supervisión humana sea real y que quede constancia de los desacuerdos. Una persona que nunca dice que no puede estar aprobando sin mirar.

---

## 15. Pruebas deterministas en lugar de un LLM como juez

**Decisión.** 26 pruebas en `tests/` comprueban la privacidad con tres candidaturas falsas fijas, sin Zoho ni la API de Claude.

**Por qué.** Dan siempre el mismo resultado, no cuestan nada y no envían datos a nadie. Un LLM como juez sería más caro, variable y enviaría datos a un tercero. Si una prueba intentara escribir en Zoho, falla a propósito.

**Error que enseñó algo.** La primera ejecución dio 24 de 25: el fallo era de la propia prueba (una variable con el mismo nombre que una función), no del servidor. Las pruebas también hay que probarlas.

---

## Otros errores que enseñaron algo

- **`invalid_client` al pedir las llaves.** Las llaves estaban bien, pero la cuenta está en el centro de datos **europeo** (`zoho.eu`), aunque en el navegador apareciera `zoho.com`. Se detectó preguntando a cada región de Zoho con un código falso: solo la europea reconocía las llaves.
- **Zoho dice "hecho" pero no hace el cambio.** Al intentar reabrir por la API una vacante cerrada, Zoho respondía `SUCCESS` y la dejaba igual. Hubo que reabrirlas desde la web. Lección: después de cada cambio, **volver a leer** para comprobar que de verdad se hizo.
- **Probar con el caso que importa.** La prueba con un solo candidato salió bien porque era un *Rechazado*. El problema estaba en los *Contratados*. Lección: la prueba pequeña debe incluir los casos con efectos secundarios.
