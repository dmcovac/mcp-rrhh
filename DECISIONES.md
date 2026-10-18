# Registro de decisiones

Cada decisión importante del proyecto: qué se decidió, por qué y qué alternativa se descartó. Cuando una decisión nació de un error, también se cuenta el error, porque es lo que más enseña.

---

## 1. No usar la cuenta de Zoho de 2017

**Contexto.** Había una cuenta de Zoho Recruit de 2017, de cuando trabajaba como reclutadora, con datos de candidatos reales y desactualizados.

**Decisión.** Crear una cuenta nueva solo para pruebas, con 50 candidatos inventados con Faker.

**Por qué.**
- Conectar el servidor habría hecho pasar datos personales reales por la IA, justo lo contrario de la minimización.
- Esas personas dieron sus datos para un proceso de selección concreto, no para un proyecto de aprendizaje. Usarlos para otra cosa choca con el RGPD.
- Con datos falsos se puede probar sin miedo, incluso cambiar fases o hacer cargas que salgan mal.

**Alternativa descartada.** Usar la cuenta antigua "solo para leer". Seguía exponiendo datos reales a la IA.

**Pendiente.** Revisar si esos datos deben conservarse y, si no, borrarlos desde Zoho.

---

## 2. Que el servidor devuelva solo nombre, puesto y fase

**Contexto.** Cada candidatura que Zoho envía incluye muchos más campos: email, móvil, reclutador asignado (con su email personal), cliente, moneda, fechas…

**Decisión.** La función `minimizar` del servidor se queda solo con **nombre, puesto y fase**.

**Por qué.** Es lo único que necesita la IA para responder sobre el proceso de selección. Todo lo que devuelve una herramienta lo lee la IA y puede acabar en una respuesta.

**Cómo se comprobó.** Se añadieron a Zoho móviles, direcciones y salarios falsos. Zoho sí manda el móvil al servidor, pero en la respuesta del servidor a la IA no aparece ningún móvil, email, salario ni calle.

**Alternativa descartada.** Devolver el registro completo de Zoho y confiar en que la IA no use lo que no necesita.

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

## Otros errores que enseñaron algo

- **`invalid_client` al pedir las llaves.** Las llaves estaban bien, pero la cuenta está en el centro de datos **europeo** (`zoho.eu`), aunque en el navegador apareciera `zoho.com`. Se detectó preguntando a cada región de Zoho con un código falso: solo la europea reconocía las llaves.
- **Zoho dice "hecho" pero no hace el cambio.** Al intentar reabrir por la API una vacante cerrada, Zoho respondía `SUCCESS` y la dejaba igual. Hubo que reabrirlas desde la web. Lección: después de cada cambio, **volver a leer** para comprobar que de verdad se hizo.
- **Probar con el caso que importa.** La prueba con un solo candidato salió bien porque era un *Rechazado*. El problema estaba en los *Contratados*. Lección: la prueba pequeña debe incluir los casos con efectos secundarios.
