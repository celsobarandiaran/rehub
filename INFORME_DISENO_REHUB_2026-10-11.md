# Informe crítico del diseño de ReHub

**Fecha:** 11 de octubre de 2026
**Qué se ha revisado:** la maqueta (`maqueta/index.html`, vista en PC y en móvil de 375 px), el plan de 6 sesiones, `estado.md` y el encargo original con todas las pantallas y cálculos. Todavía no hay código ni datos de demo, así que se analiza solo el diseño.
**Cómo leerlo:** opinan tres expertos: **Consultor** (gestión de restaurantes), **Analista** (datos de hostelería) y **Programador** (aplicaciones en la nube). Todas las cifras de los ejemplos son de un restaurante inventado (los datos de la maqueta de "La Plaza"), salvo los precios de Mercabarna, que son reales (media de septiembre de 2026, consultada en su web el 11/10/2026). Lo que no he podido comprobar está marcado como **sin comprobar**.

---

## a) Resumen en una página

### Notas

| Experto | Nota | En una frase |
|---|---|---|
| Consultor de restaurantes | **6 / 10** | Ataca los problemas de verdad (coste de comida, compras, caja), pero le pide demasiado trabajo al personal y le faltan cosas que el dueño usaría cada día (pedidos, inventario, alérgenos). |
| Analista de datos | **4 / 10** | Varios cálculos clave están mal planteados (IVA dentro de los precios, clasificación de platos, coste de comida con compras en vez de consumo, caja sin saldo del banco) y las cifras de la maqueta no cuadran entre sí. |
| Programador | **4 / 10** para venderla (**7 / 10** como demo) | Para una demo gratis vale. Para venderla, el alojamiento gratuito, la IA gratuita y los datos de nóminas en EE. UU. no sirven, y no está pensada para varios restaurantes a la vez. |

### Las 5 cosas más importantes

1. **Los precios llevan el IVA dentro y eso falsea márgenes y ratios.** El arroz negro se vende a 16,50 € con IVA, pero al restaurante le quedan 15,00 €. La maqueta dice que deja 12,60 € (76 %), y en realidad deja 11,10 € (74 %). El coste de comida del mes pasa de 36,2 % a **39,8 %** si se calcula bien. Todo debe calcularse **sin IVA**.
2. **La clasificación de platos (estrella, vaca, puzle, perro) está mal en 2 de los 7 platos de la maqueta.** Se ha hecho por % de margen, y el método correcto usa **euros de margen** y unidades vendidas. Las bravas no son "estrella", son "vaca" (dejan 4,81 € por ración, menos que la media). El entrecot no es "vaca", es "estrella". Si el dueño sube el precio de un plato por esto, se equivoca.
3. **La caja a 30 días y el coste de comida necesitan datos que el diseño no recoge.** Falta el **saldo del banco** (sin él la caja es inventada) y falta un **recuento de inventario** (sin él el coste de comida mezcla lo que se compra con lo que se gasta: 36,2 % frente a 33,8 % en el ejemplo).
4. **Le pide al personal demasiadas fotos.** Hacer una foto a la etiqueta de cada producto fresco al descargar el pedido no se va a cumplir en un servicio real. Mejor una foto al **albarán** y solo fotos de etiqueta para pescado y carne, que además sirven para la trazabilidad que pide Sanidad.
5. **Para venderla hay que cambiar la base y diferenciarse.** Alojamiento en Europa de pago, IA de pago con contrato de protección de datos, varios restaurantes separados, y una razón para elegir ReHub frente a **Haddock** (Barcelona), que ya lee facturas con una foto y calcula el coste de los platos. La diferencia podría estar en lo que Haddock no enseña en sus fuentes públicas: caja a 30 días, precios de referencia de Mercabarna, turnos frente a ventas y un asistente que habla claro.

---

## b) Las 9 pantallas

Nota de 1 (no sirve) a 5 (muy útil y bien planteada).

| Pantalla | Para qué le sirve al dueño | Qué decisión le ayuda a tomar | Datos que necesita y de dónde salen | Nota | Qué falla en el diseño |
|---|---|---|---|---|---|
| **Bandeja** | No perder correos ni facturas y contestar rápido a clientes | Qué contestar a reservas y quejas; qué factura revisar | Correo (Gmail). Existe en cualquier restaurante | **4** | Bien planteada. Faltan las facturas que **no llegan por correo** (papel, portal del proveedor, WhatsApp) y un aviso "esto es raro" para documentos que no sabe clasificar. Las reservas suelen llegar por plataformas (TheFork, Google, Covermanager), no por correo. |
| **Documentos** | Encontrar cualquier factura en segundos y ver cuánto se gasta en cada proveedor | Qué proveedor revisar o renegociar; qué factura no pagar (duplicada) | Facturas en PDF o foto, nóminas, cierres de caja | **4** | Muy completa en PC. En el móvil, 2 tablas obligan a moverse de lado. Falta casar **factura con albarán** (lo que pidió, lo que llegó y lo que cobra), que es donde se pierde dinero. El comparador con Mercabarna es un buen gancho. |
| **Recepción** | Saber qué hay en cámara y qué caduca | Qué gastar hoy; qué reclamar al proveedor | Fotos de etiquetas en cada entrega | **2** | El dato **no va a existir**: nadie hace 15 fotos mientras descarga un pedido en la puerta. La verdura a granel no lleva etiqueta. Sin recuento real, el "stock teórico" se aleja de la realidad cada día. |
| **Hoy** | Saber qué recomendar y cuánto se va a vender | Qué platos empujar; cuánta gente poner | Ventas pasadas (cierres de la caja registradora), eventos, caducidades | **3** | Buena idea y fácil de entender. Pero con 3 meses de datos la previsión es floja: "+18 % por la feria" es un número inventado si nunca hubo feria en los datos. Debe dar **un margen** ("entre 2.200 y 2.900 €"), no una cifra exacta. |
| **Cuadro del día** | Cerrar la caja de ayer y ver avisos | Buscar el dinero que falta; no pagar dos veces | Cierre de la caja registradora (en la maqueta, PDF), tickets de gasto | **4** | Útil y rápido. Pero las cajas registradoras suelen dar el cierre en Excel o por conexión, no en PDF, y leer un PDF con IA es frágil. Falta el **datáfono**: lo cobrado con tarjeta llega al banco 1 o 2 días después y con comisión. |
| **Platos** | Saber qué plato gana y cuál pierde dinero | Subir precios, cambiar raciones, quitar platos | Recetas con cantidades (no existen en la mayoría de restaurantes pequeños: hay que crearlas), precios de compra, unidades vendidas | **3** | Es lo más valioso, pero: (1) usa precios con IVA, (2) clasifica por % en vez de por euros, (3) no tiene en cuenta lo que se pierde al limpiar (una lubina entera da la mitad en filete), (4) cargar 25 recetas lleva horas y nadie lo prevé. |
| **Personal** | Ver si sobra o falta gente en cada franja | Cambiar turnos | Cuadrante, coste por hora (de las nóminas), ventas por franja | **3** | Cálculo correcto en la idea. Pero con 4 personas fijas el margen de maniobra es pequeño, y mover turnos tiene límites legales y del convenio. Falta el **coste por hora** de cada persona a la vista y el **fichaje** (registro de jornada, obligatorio en España). |
| **Dueño** | Ver en una pantalla si el negocio gana o pierde | Qué gasto atacar primero; cuándo va a faltar dinero | Ventas, compras, nóminas, gastos fijos, saldo del banco | **3** | La pantalla que vende la app, pero hoy tiene fallos de cálculo (IVA, coste de comida con compras, punto de equilibrio sin días de apertura, caja sin saldo real) y cifras que no cuadran (4 empleados no cuestan 25.026 €/mes). |
| **Ajustes** | Configurar y hacer la demo | Ninguna de negocio | — | **3** | Bien para la demo. Para venderla: "Autodestruir" debe ser "Exportar mis datos y darme de baja" (lo pide la ley de protección de datos). Falta la configuración de cada restaurante: días que abre, IVA de cada producto, margen objetivo y mínimo de caja. |

**En el móvil** (comprobado en la maqueta a 375 px): la página no se sale de la pantalla, pero **112 de 146 botones y chips miden menos de 36 px de alto**. Lo recomendable para el dedo es unos 44 px, y en cocina, con las manos mojadas, más. Hay **65 textos de menos de 12 px**, 5 tablas que obligan a moverse de lado (2 en Documentos, 2 en Platos, 1 en Personal) y la pantalla Platos ocupa **4,7 pantallas de móvil** de largo. De pie en la barra solo son cómodas **Recepción, Hoy y Cuadro del día**.

---

## c) Qué quitaría y por qué

1. **La foto de la etiqueta de cada producto fresco.** No se va a hacer en la realidad. La cambiaría por una foto al albarán y fotos de etiqueta solo para pescado y carne (por trazabilidad).
2. **La "previsión" con un número exacto** ("2.640 €, +18 %"). Con 3 meses de datos da una falsa seguridad. Mejor un margen y el motivo ("normal de domingo: 2.200 a 2.900 €; hay feria, puede ir arriba").
3. **El "stock teórico" como cifra fiable.** Sin recuentos, a las pocas semanas no se parece a lo que hay en la cámara. Lo mantendría, pero obligando a un **recuento corto semanal** de los productos caros.
4. **"Autodestruir" en la versión para vender.** Para la demo está bien; para un cliente es peligroso. Lo cambiaría por "Exportar todo y darme de baja".
5. **El botón "Actualizar" a la vista del dueño.** Las aplicaciones en la nube se actualizan solas. Para el cliente, como mucho, un aviso "hay novedades".
6. **La comparación con proveedores que no son del restaurante (Makro y similares).** Ya descartada: no hay precios públicos fiables de comida.

---

## d) Qué añadiría (ordenado por lo que vale para el restaurante)

| # | Propuesta | Qué decisión ayuda a tomar | Dificultad | ¿Datos que el diseño aún no prevé? |
|---|---|---|---|---|
| 1 | **Coste de comida real frente al teórico** (lo que debería haberse gastado según lo vendido, frente a lo que se gastó de verdad) | Dónde se pierde dinero: raciones grandes, mermas o robos | Media | Sí: recuento de inventario semanal o mensual |
| 2 | **Pedido sugerido al proveedor** (lo que hay, lo que se va a vender y lo que hay que pedir), enviado por correo o WhatsApp con un clic | Cuánto pedir para no tirar ni quedarse corto | Media | Sí: stock mínimo por producto y días de reparto de cada proveedor |
| 3 | **Factura contra albarán** (lo que llegó frente a lo que se cobra) | Qué reclamar al proveedor | Media | Sí: foto del albarán al recibir |
| 4 | **Alérgenos automáticos** a partir de las recetas, con la carta lista para imprimir | Cumplir la ley de alérgenos sin hacerlo a mano | Baja | Sí: alérgenos de cada ingrediente (una vez) |
| 5 | **Saldo del banco** (escrito a mano cada semana, o conexión al banco más adelante) | Si la caja de los próximos días es real o no | Baja (a mano) / Alta (conexión) | Sí |
| 6 | **Rendimiento de cada producto** (lo que queda tras limpiar o cocinar) en las recetas | Coste de plato real y precio correcto | Baja | Sí: % de rendimiento por producto |
| 7 | **Resumen semanal por correo** al dueño (3 alertas y 3 acciones) | Qué hacer esta semana sin abrir la app | Baja | No |
| 8 | **Precio objetivo de cada plato** ("para dejar un 70 % debería costar X €") | A qué precio poner un plato nuevo o subido | Baja | No |
| 9 | **Reseñas de Google** en la Bandeja, con respuesta propuesta | Contestar reseñas para atraer clientes | Media | Sí: acceso a la ficha de Google |
| 10 | **Registro de jornada (fichaje)** y horas extra en Personal | Cumplir la ley y controlar el coste real de horas | Media | Sí: fichajes |
| 11 | **Controles sanitarios del día** (temperaturas de cámaras, limpieza, recepción): la lista de la parte sanitaria obligatoria | Cumplir Sanidad y tener papeles ante una inspección | Baja | Sí: lista de controles del local |
| 12 | **Comparación entre locales** si el cliente tiene más de uno | Qué local va peor y por qué | Alta | Sí: varios restaurantes |
| 13 | **Ticket medio y cubiertos por franja** (cuánto gasta cada cliente) | Si conviene un menú, una oferta o subir precios | Baja | No (sale del cierre de caja si trae cubiertos) |

---

## e) Qué cambiaría de lo ya diseñado

### Cálculos mal planteados (con ejemplo)

**1. Quitar el IVA antes de calcular.** Un restaurante cobra un 10 % de IVA que no es suyo.
- Arroz negro: 16,50 € de precio en carta, que son **15,00 € sin IVA**. Coste de 3,90 €.
- La maqueta: margen 12,60 € (76 %), coste de comida 23,6 %.
- Bien calculado: margen **11,10 € (74 %)**, coste de comida **26,0 %**.
- En el mes (Dueño): 62.880 € con IVA son **57.164 € sin IVA**. El coste de comida pasa de 36,2 % a **39,8 %**, que ya no es ámbar sino rojo.
- Lo mismo con las compras: siempre la **base** de la factura, sin IVA.

**2. Clasificar los platos por euros de margen, no por %.** El método habitual (llamado "ingeniería de menú") compara el **margen en euros** de cada plato con la media ponderada por unidades vendidas, y las **unidades** con el 70 % de lo que vendería cada plato si todos se vendieran igual. Con los 7 platos de la maqueta (2.425 raciones, sin IVA):
- Margen medio: 7,89 €. Raciones que marcan "se vende mucho": 0,7 × 2.425 / 7 = 242.
- **Patatas bravas:** deja 4,81 €, por debajo de la media, y se venden 890 → **vaca** (la maqueta dice estrella).
- **Entrecot:** deja 10,20 €, por encima, y se venden 365 → **estrella** (la maqueta dice vaca).
- El resto coincide. Que un plato deje un 83 % no lo convierte en estrella si en euros deja poco.

**3. Coste de comida con lo que se gasta, no con lo que se compra.**
- Ejemplo de septiembre: compras de comida de 22.762 €, había 3.000 € en cámara el día 1 y quedan 4.500 € el día 30.
- Gastado de verdad: 3.000 + 22.762 − 4.500 = **21.262 €**, un **33,8 %** de las ventas (con IVA, como la maqueta), frente al 36,2 % que da usar solo las compras.
- Sin recuento, el dato sube o baja según cuándo llega el pedido grande y el dueño toma decisiones con ruido. Hace falta un **recuento a fin de mes** (o semanal de lo caro).

**4. Coste del plato con rendimiento.**
- Lubina entera a 14,90 €/kg. Limpia rinde más o menos la mitad (rendimiento del 50 %, **ejemplo**), así que el kilo limpio cuesta 29,80 €.
- Ración de 180 g de filete: **5,36 €**, no 2,68 €. Sin rendimiento, todos los platos de pescado y carne parecen el doble de rentables.

**5. Punto de equilibrio con los días que abre.**
- Septiembre (maqueta): gastos fijos = personal 25.026 + alquiler 2.420 + luz y gas 1.648 + otros 7.809 = **36.903 €**. La comida es el 36,2 % de las ventas, así que de cada euro vendido quedan 0,638 € para pagar los fijos.
- Hay que vender 36.903 / 0,638 = **57.841 € al mes**.
- Si abre 30 días son **1.928 € al día**; si cierra un día a la semana (26 días), **2.225 € al día**. La maqueta pone 1.985 € sin decir cómo sale. Hay que pedir los días de apertura en Ajustes y enseñar la cuenta.
- (Y otra vez: esto debe hacerse sin IVA.)

**6. Caja a 30 días con datos reales.**
- La app no sabe cuánto dinero hay en el banco. Necesita que alguien lo escriba (una vez por semana basta) o una conexión al banco (de pago).
- Lo cobrado con tarjeta llega al banco 1 o 2 días después y con comisión; el efectivo va a la caja, no al banco. El diseño los trata igual.
- Ejemplo: si el sábado se cobran 2.395 € con tarjeta con un 0,5 % de comisión (**ejemplo**), al banco llegan unos 2.383 € el lunes, no el sábado.

**7. Coste de personal por franja con el coste por hora real.**
- Rosa cuesta 2.630 €/mes a la empresa por 40 h/semana (unas 173 h/mes): **15,17 €/h**. Óscar: **12,14 €/h**.
- Viernes de 16 a 19 h, con Óscar e Iván (6 horas en total, unos 75 €) y unas ventas de 120 € (**ejemplo**): el personal se come el 62 % de lo vendido en esa franja.
- Bien planteado, pero hay que enseñar el coste por hora y recordar que **con contratos fijos no se puede quitar horas sin más**: la acción real es mover turnos dentro de lo que permiten el convenio y la ley.

**8. Las cifras de la maqueta no cuadran entre sí.** Con 4 empleados, el personal cuesta unos **9.244 €/mes** (suma del coste empresa de sus nóminas), que es un **14,7 %** de 62.880 €. La maqueta pone 25.026 € (39,8 %). Un dueño lo detecta enseguida y deja de fiarse. Hay que generar los datos de demo desde una sola fuente para que todo cuadre (ventas de unos 27.000 €/mes con 4 personas, como ya se propuso).

### Pantallas que sobran, se repiten u orden del menú
- **Hoy debería ser la primera pantalla.** Es la única que todos (dueño, oficina, cocina) abren cada día. El orden propuesto: **Hoy, Bandeja, Cuadro del día, Recepción, Platos (con Precios), Personal, Dueño, Documentos, Ajustes.**
- **Cuadro del día y Dueño repiten cosas** (ventas, avisos de precio y duplicada). Los avisos deberían estar en un solo sitio (Hoy) y Dueño quedarse con el mes.
- **Precios** está escondido dentro de Platos; para vender es de lo más llamativo y merece entrada propia en el menú.

### Textos que no se entienden en 10 segundos
- "Estrella / vaca / puzle / perro": a un dueño hay que explicárselo. Mejor "Gana y se vende / Se vende pero gana poco / Gana pero no se vende / Ni gana ni se vende", con el dibujo al lado.
- "Stock teórico", "punto de equilibrio", "margen razonable del proveedor": cada uno necesita una frase al lado ("lo que hay que vender cada día para no perder dinero").
- "Coste de comida 36,2 %": añadir "de cada 100 € que vendes, 36 € son comida".

### Botones que faltan
- **"Escribir el saldo del banco"** (Dueño).
- **"Hacer recuento"** (Recepción).
- **"Pedir a [proveedor]"** (Recepción y Precios).
- **"No es una factura"** o **"Esto es raro"** (Bandeja), para documentos que no encajan.
- **"Marcar como pagada"** en las facturas.
- **"Añadir receta"** guiado, plato a plato (Platos).

---

## f) Riesgos técnicos del plan y cómo evitarlos

| Riesgo | Qué puede pasar | Cómo evitarlo |
|---|---|---|
| **Alojamiento gratuito (Hugging Face)** | Código público, servidor en EE. UU., se duerme tras unas 48 h sin uso, tiene fallos de arranque conocidos en su foro. | Vale para la demo. Para clientes: alojamiento de pago en Europa (unos 5-25 €/mes, **sin comprobar** para cada proveedor) con copia de seguridad diaria. |
| **Base de datos gratuita (Supabase)** | Se pausa tras 7 días sin uso; límite de 500 MB de datos y 1 GB de archivos. Con fotos y PDF de un año se llena. | El aviso diario automático ya previsto evita la pausa. Para clientes, plan de pago (25 $/mes según fuentes de terceros) y fotos comprimidas. |
| **IA gratuita (Gemini)** | Tope diario bajo y cambiante. Google puede usar lo que se le manda para mejorar su IA: **nóminas y facturas reales no pueden ir por el plan gratuito**. | Demo: datos inventados y PDF con texto leídos sin IA. Clientes: plan de pago con contrato de protección de datos y datos en Europa. |
| **Leer fotos** | Fotos movidas, tickets arrugados, fechas mal leídas. Un error en un precio cambia el coste de varios platos. | Nunca inventar: todo lo dudoso queda "por revisar". Comprobar que base + IVA = total. Avisar si un precio cambia más de un 30 % de golpe (seguramente es un error de lectura). |
| **Correo (Gmail)** | El permiso de una app sin verificar puede caducar o dar avisos; Google revisa mucho las apps que leen el correo. | Para clientes, verificar la app con Google (proceso largo, **sin comprobar** cuánto) o usar una dirección propia de ReHub a la que el restaurante reenvía las facturas. |
| **Caja registradora (TPV)** | Cada marca exporta distinto; un PDF es lo más frágil. | Empezar por exportación en Excel o CSV de las 2 o 3 marcas más usadas por los clientes objetivo. Si un día no llega el cierre: aviso "falta el cierre de ayer" y casilla para escribirlo a mano. |
| **Rendimiento** | "Cargar demo" con 150 documentos y recálculos a cada clic. | Calcular de noche y guardar los totales; recalcular solo lo que cambia. |
| **Varios restaurantes** | El diseño es para uno. Al vender a varios, mezclar datos sería gravísimo. | Separar los datos de cada restaurante desde la primera línea de código, aunque la demo tenga uno. |
| **Ley de protección de datos** | Nóminas, salarios y datos de clientes son datos personales. | Contrato de encargado de tratamiento con cada restaurante, datos en Europa, exportar y borrar a petición, registro de quién ve qué. |
| **Factura electrónica** | España va a obligar a las empresas a intercambiar facturas electrónicas entre ellas (Ley Crea y Crece). Fechas exactas **sin comprobar**. | Es una oportunidad: esas facturas se leen sin IA y sin errores. Preparar la lectura de los formatos oficiales más adelante. |

**Flujo de un día con la app (estimado):**
- **Oficina, por la mañana, unos 10 minutos:** abrir Hoy (avisos), revisar en Bandeja lo "por revisar" (2-3 documentos), aprobar respuestas, contar el efectivo en Cuadro del día.
- **Cocina, al recibir pedidos, 30 segundos por pedido:** foto del albarán, y foto de la etiqueta solo en pescado y carne.
- **Camareros, antes del servicio, 1 minuto:** los 3 platos a empujar.
- **Si falla algo:** documento raro, a "por revisar" con una frase de por qué. Si falta el cierre de caja, aviso y casilla manual. Si el correo no funciona, botón "subir a mano". Si se acaba el tope de la IA, las fotos quedan en cola y se leen al día siguiente, sin inventar nada.

**Flujo de un mes:** recuento de inventario el último día (30-45 minutos en un restaurante pequeño, **estimado**), apuntar el saldo del banco, revisar el resumen del mes en Dueño y comprobar con la gestoría el IVA y las nóminas.

---

## g) Los 10 cambios prioritarios antes de programar

| Orden | Cambio | Dificultad | Sesión |
|---|---|---|---|
| 1 | Calcular todo **sin IVA** (ventas y compras) y decirlo en pantalla | Baja | 2 (base de datos y cálculos) |
| 2 | Generar los datos de demo **desde una sola fuente** para que todo cuadre (4 empleados con unos 27.000 €/mes de ventas) | Media | 3 |
| 3 | Clasificación de platos **por euros de margen** y nombres que se entiendan | Baja | 4 |
| 4 | **Rendimiento** de cada producto en las recetas | Baja | 4 |
| 5 | **Recuento de inventario** (corto, mensual o semanal) y coste de comida real frente al teórico | Media | 4 |
| 6 | Recepción con **foto al albarán**, y foto de la etiqueta solo en pescado y carne | Media | 4 |
| 7 | **Saldo del banco** a mano y tarjeta con 1-2 días de retraso en la caja a 30 días | Baja | 5 |
| 8 | Punto de equilibrio con **días de apertura** y la cuenta a la vista | Baja | 5 |
| 9 | **Hoy primero** en el menú, avisos solo en Hoy, Precios con entrada propia | Baja | 2 (diseño) |
| 10 | **Móvil de pie**: botones de al menos 44 px, tablas convertidas en tarjetas, letra de 13 px o más | Media | Repartida en 2-6 |

**Para cuando se quiera vender** (no hace falta para la demo): alojamiento e IA de pago en Europa, varios restaurantes separados, "Exportar y darme de baja" y conexión con 2-3 cajas registradoras. Eso es una sesión 7 o más.

---

## h) Tres preguntas antes de seguir

1. **¿Qué caja registradora (TPV) usan los restaurantes a los que quieres vender?** Esto decide cómo entran las ventas, que es la base de todo.
2. **¿Cuánto pensabas cobrar al mes y quién lo instala y lo mantiene?** Con IA y alojamiento de pago en Europa hay un coste fijo por cliente; si quieres cobrar muy poco, hay que recortar funciones.
3. **Para la demo, ¿prefieres pocas pantallas con cálculos impecables, o todas aunque alguna sea más floja?** Mi recomendación: impecables Platos, Precios, Cuadro del día y Dueño; Personal y la previsión de Hoy, más sencillas.

---

### Fuentes consultadas
- Mercabarna, estadísticas de productos (precios reales de septiembre de 2026): https://www.mercabarna.es/serveis/es_estadistiques-productes/
- Haddock (lectura de facturas con una foto y escandallos): https://elreferente.es/startups/haddock-la-gestion-de-tu-restaurante-a-una-foto/
- Gstock (compras, inventario y escandallos): https://www.alimarket.es/restauracion/noticia_amp/165613/ya-esta-lista--g-stock---la-herramienta-destinada-al-control-de-compras-para-restaurantes
- Límites del plan gratuito de Supabase (fuente de terceros): https://automationatlas.io/answers/supabase-free-tier-limits-2026/
- Hugging Face Spaces, funcionamiento y suspensión: https://huggingface.co/docs/hub/spaces-overview

**No he podido comprobar:** las funciones exactas y los precios actuales de Haddock y Gstock (solo noticias y fichas públicas), los precios de alojamientos de pago en Europa, las fechas de la factura electrónica obligatoria, cuánto tarda Google en verificar una app que lee el correo, ni la comisión real del datáfono de un restaurante concreto.
