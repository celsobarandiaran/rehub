# ReHub · estado

Última actualización: 11/10/2026, sesión 1 (plan, cuentas y maqueta).

## Hecho
- Plan, reparto en 6 sesiones y lista de cuentas enviados a Celso.
- Maqueta de las 9 pantallas: `maqueta/index.html`. Se ve en PC y en móvil (probado a 375 px de ancho, sin que nada se salga de la pantalla). Abierta en Chrome, en la pantalla de la derecha.
- Cambio pedido por Celso: en Documentos, las carpetas se cambian por un calendario para elegir todo, un año, un mes o un día.
- Cambio pedido por Celso: en Documentos, las facturas se pueden ordenar por proveedor y los gastos por tipo de gasto (también por fecha o importe).
- Cambio pedido por Celso: en el calendario, un día y luego otro eligen el periodo entre los dos (aunque sean de meses distintos), y un mes y luego otro eligen varios meses.
- Cambio pedido por Celso: 'Cargar demo' funciona como una línea de tiempo. Los 71 días (1 ago a 10 oct) entran uno a uno, a 1 día por segundo (se puede pasar a 2 o 5 días por segundo, pausar o ir al final). Las fotos que necesitan IA se leen en segundo plano con el tope gratuito; los PDF con texto entran al momento.
- Cambio pedido por Celso: asistente en todas las pantallas (botón abajo a la derecha). Sabe en qué pantalla estás y propone preguntas de esa pantalla. Responderá con los datos que cada perfil puede ver.
- Arreglado: las pestañas Nóminas, Cierres y Otros de Documentos tienen ya su lista (nóminas por empleado, cierres por semana). El recuadro de líneas de factura solo sale en Facturas.
- Ojo: 4 empleados (unos 9.200 €/mes) no encajan con 62.880 €/mes de ventas ni con un 39,8 % de personal. Hay que cuadrar las cifras de la demo.
- Cambio pedido por Celso: Personal enseña horarios con horas reales (40 h por persona y semana, con avisos si alguien pasa de 9 h en un día o de 40 h en la semana) y una vista hora a hora de un día con las ventas debajo.
- Cambio pedido por Celso: las facturas, ordenadas por proveedor, salen en dos bloques: Comida y bebida (cuenta para el coste de comida) y Local y servicios (alquiler, luz, gas, agua, seguros, limpieza). Cada proveedor llevará marcado su grupo.
- Cambio pedido por Celso: botón Actualizar (aviso arriba cuando hay versión nueva y tarjeta en Ajustes). Carga la última versión, vuelve a leer el correo y recalcula. No borra datos; para empezar de cero sigue estando Reiniciar demo.
- Cambio pedido por Celso: el gráfico de caja a 30 días se ha rehecho para que se entienda (euros en el eje, fechas, pagos grandes numerados y explicados debajo, resumen hoy / punto más bajo / dentro de 30 días).
- Cambio pedido por Celso: apartado Precios (dentro de Platos) que compara lo que cobra cada proveedor con el precio de Mercabarna (fruta, verdura y pescado), con margen razonable editable y ahorro posible al mes.
- Mercabarna: buscador público en https://www.mercabarna.es/serveis/es_estadistiques-productes/ . Se puede consultar por día, semana o mes enviando el formulario (grupo, producto, periodo, fechas). Comprobado el 11/10/2026 con datos de septiembre de 2026. Para la semana de octubre no devolvió datos. Cambio pedido por Celso: botón 'Comparar con Mercabarna' en las líneas de cada factura (Documentos > Facturas). Los bloques Comida y bebida y Local y servicios se pliegan con un clic. Al pulsar una factura salen sus líneas y, al comparar, la diferencia con Mercabarna, lo que cambia en ese pedido y en un mes (según las entregas al mes del proveedor). Cada precio de Mercabarna es un enlace que abre en otra pestaña la consulta oficial de ese producto (se envía el formulario de su web con el código del producto; probado en Chrome, sale la lubina de cultivo a 8,06 euros el kilo). Makro: su web enseña sobre todo precios de menaje, no de comida, y tiene protección contra programas automáticos; no se usa.

- Impuestos y Seguridad Social: la app no se conecta con Hacienda, la Seguridad Social ni el SEPE. Calcula el IVA aproximado con ventas y facturas y lo marca 'aproximado, esperando a la gestoría'; cuando llega el correo de la gestoría pone la cifra exacta y lo marca 'confirmado por la gestoría'.

- 11/10/2026: informe crítico del diseño en `INFORME_DISENO_REHUB_2026-10-11.md`.
- 11/10/2026: maqueta v2 (`maqueta/index.html`; la anterior queda en `maqueta/version1.html`). 11 pantallas: Bandeja, Documentos, Proveedores, Recepción, Hoy, Cuadro del día, Carta, Competencia, Personal, Dueño, Ajustes. Aplicados los cambios del informe: todo sin IVA, cifras coherentes (24.500 €/mes sin IVA con 4 empleados), clasificación de platos por euros, rendimiento en recetas, recuento de cámara, foto al albarán, saldo real del banco, días de apertura, avisos juntos en Hoy, tablas como tarjetas y botones de 44 px en el móvil. Añadidos: Carta con bebidas y competencia, pantalla Competencia, pantalla Proveedores con ficha y precios en el tiempo, Importar histórico y extracto del banco con conciliación. Pendiente del "vale" de Celso.

## Pendiente
- Que Celso dé el "vale" a la maqueta (o pida cambios).
- Cuentas: Gmail nuevo (propuesto laplaza.rehub@gmail.com), Google Cloud con esa cuenta, Hugging Face (con clave "Write") y Supabase (con clave de acceso). Las claves van en `C:\Users\celso\.rehub\claves.env` (HF_TOKEN, SUPABASE_TOKEN).
- Permiso para instalar Git.
- Sesiones 2 a 6, según el plan.

## Decisiones
- App: Hugging Face Spaces (gratis, sin tarjeta). Corre en EE. UU., su código es público y se duerme tras unas 48 h sin uso. Se mantendrá despierta con un aviso automático diario.
- Datos y archivos: Supabase, en Frankfurt.
- IA: Gemini, con la clave de `~\.spotscout\claves.env`, guardada como variable de entorno del alojamiento. Los PDF con texto se leen sin IA, para no gastar el tope diario del plan gratuito.

## Archivos creados
- `ReHub/estado.md`
- `ReHub/maqueta/index.html`

## Cosas creadas en la nube
- Ninguna todavía.

## Cómo se usa, dirección web, despliegue y perfiles
- Pendiente (sesiones 2 a 6).
