# Datos de demo · Restaurante La Plaza (inventado)

Del 01/08/2026 al 10/10/2026. El "hoy" de la demo es el 11/10/2026. Todo es inventado.
Se generan con `python herramientas/generar_demo.py` a partir de `herramientas/modelo_demo.py` (una sola fuente: todo cuadra).

| Qué | Cuántos | Carpeta |
|---|---|---|
| Facturas en PDF | 60 (1 duplicada a propósito) | facturas/ |
| Facturas escaneadas (foto) | 10 (1 con el número ilegible) | facturas_escaneadas/ |
| Tickets de gasto (foto) | 20 | tickets/ |
| Nóminas | 12 (4 empleados × julio, agosto y septiembre) | nominas/ |
| Cierres diarios del TPV | 61 (los lunes cierra) | cierres_tpv/ |
| Etiquetas de producto fresco (foto) | 15 | etiquetas/ |
| Extracto del banco | 152 movimientos (Norma 43 y CSV) | banco/ |
| Cartas de 3 competidores | 3 PDF | competencia/ |
| Correos (llegan a la bandeja) | 172: 61 cierre, 4 consulta, 70 factura, 20 gasto, 3 nomina, 8 publicidad, 1 queja, 5 reserva | correos.json |
| Correos para enviar en directo | 15 | envio_en_directo.json, en_directo/ |
| Carta (25 platos + 8 bebidas con receta), productos, cuadrante, eventos, pagos fijos, competidores | — | datos.json |
| Datos correctos para comprobar la extracción | — | verdad.json |

## Cosas puestas a propósito
- Subidas de precio: entrecot de 21,50 a 24,20 €/kg desde el 14/09/2026; lubina de 12,80 a 14,90 €/kg desde el 01/10/2026.
- Factura duplicada: Carnes Vallès del 5/10 reenviada el 9/10.
- Escaneada con el número ilegible: Hortalizas del Prat del 7/10 (debe salir "revisar").
- Descuadres de caja: 22/8 (−35 €) y 10/10 (−20 €).
- Recibos en el banco sin factura: comisiones del datáfono, alarma y cuota de autónomo.

## Cifras de control (con IVA)
- Ventas: agosto 30.513,10 €, septiembre 25.975,70 €, octubre hasta el día 10 9.539,80 €.
- Banco: saldo el 1/8 3.000,00 €, saldo el 10/10 10.528,60 €.

Importante: nombres de empresas, personas, CIF, teléfonos y direcciones son inventados (dominios .example).
