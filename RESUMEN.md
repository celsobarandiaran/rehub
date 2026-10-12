# ReHub · resumen (12/10/2026)

**Qué es:** la oficina de un restaurante en una web: lee el correo, archiva facturas, tickets, nóminas y cierres, controla proveedores, caducidades, carta, competencia, personal y la caja del dueño. Hecha para practicar y para enseñársela a un amigo con restaurante. Coste: 0 €.

**Dónde está:** https://rehub-os12.onrender.com (contraseña del dueño en `C:\Users\celso\.rehub\claves.env`, línea `REHUB_CONTRASENA`). Se duerme a los 15 min sin uso; tarda ~1 min en despertar. Maquetas en `/maqueta/` (A claro, B verde, C mezcla).

**Cuentas y claves (todas gratis, sin tarjeta):** Gmail laplazarehub@gmail.com (Google Cloud, proyecto ReHub, API de Gmail y cliente OAuth); Supabase (base y archivos, Frankfurt); GitHub `celsobarandiaran/rehub` (código); Render (la app, Frankfurt). Claves solo en `claves.env`. Para publicar cambios: `git push` + `.venv\Scripts\python.exe herramientas\desplegar_render.py` (el push solo no redespliega).

**Pantallas (12):** Bandeja, Documentos, Proveedores, Recepción, Hoy, Cuadro del día, Carta, Competencia, Personal, Dueño, Asistente, Ajustes. Estilo claro (tipo Haddock) con todo plegado al abrir, elegido el 11/10/2026.

**Datos de demo:** Restaurante La Plaza, agosto–octubre de 2026, inventados y cuadrados (`datos_demo/`, `herramientas/generar_demo.py`). 19 pruebas automáticas (`.venv\Scripts\python.exe -m pytest -q`).

**Mercado:** Haddock (con su asistente Fina) ya lee facturas del correo y concilia con el banco mejor; lo que ReHub tiene y ellos no: clientes (reservas, quejas), cocina (etiquetas, albaranes, qué empujar hoy), Mercabarna, personal frente a ventas y el cuadro del dueño. Venderla como producto compitiendo en administración no es buen camino; a medida para un restaurante concreto o como nicho, sí.

**Pendiente:** elegir vista A o B de precios en Proveedores; "Subir tarifa" de proveedores (propuesto); probar Autodestruir en una copia; conectar un TPV real si se usa de verdad.

Detalle completo, en orden: `estado.md`. Guion de la reunión: `GUION_DEMO.md`.
