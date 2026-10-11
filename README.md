---
title: ReHub
emoji: 🍽️
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# ReHub

Demo de una aplicación para la oficina de un restaurante: lee el correo, clasifica y archiva facturas, tickets, nóminas y cierres de caja, controla lo que entra y caduca, analiza la carta plato a plato y enseña al dueño cómo va el negocio.

Todos los datos de la demo (Restaurante La Plaza) son inventados. Las claves se configuran como variables de entorno del alojamiento; nunca están en el código.

- Arranque local: `.venv\Scripts\python.exe -u herramientas\iniciar_local.py` (puerto 8510).
- Pruebas: `.venv\Scripts\python.exe -m pytest -q`.
- Estado del proyecto: `estado.md`.
