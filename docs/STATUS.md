# Estado

Versión publicada: v2.11.0 (v2.12.0 en PR) · Commit de referencia: `f46e247` · Actualizado: 2026-11-13

## Funciona (comprobado)
- Integración HACS con panel propio en JS, CI (pytest, hassfest, HACS) y release automática con ZIP.
- Detecta Gas TUR si está instalado.
- v2.6.0: botón Rotar + pestaña Configuración (rotación de pestañas por dispositivo). Falta probarla en la tablet real.
- v2.7.0: Solar con controles del Deye (carga por red, programas 1 y 2), nubosidad a 5 días y recomendación de carga nocturna. Probado con las opciones reales de un Deye (Solarman).
- v2.9.1 (PR): indicador «Hucha restante» en la pestaña Luz.
- v2.9.0: importar facturas de luz en PDF desde la pestaña Luz (necesita Factusol 0.2.0). Probado con datos simulados; falta con la casa real.
- v2.8.0: pestaña Luz junto a Gas con los datos de Factusol (detección por registro de entidades) e importación de CSV de la distribuidora, calibración, reconstrucción del historial y registro de facturas. Probada con estados simulados y pytest; falta probarla en la casa real.
- v2.7.6: la barra de pestañas va en una línea con deslizamiento y flechas ‹ › en vez de quedar tapada por Rotar/Diseño.
- v2.7.5: pestañas visibles/ocultas por dispositivo en Configuración (las ocultas no rotan).
- v2.7.4: intensidad de carga por red en vatios y limitada a la potencia contratada menos el consumo de la casa; programas 1 y 2 sin deslizador de potencia; SOC nocturno manual junto al aconsejado; tarjetas Estado/Fallo/Alarma del inversor en verde/ámbar/rojo; pestaña Enchufes y luces/enchufes dinámicos; mapas de nubes (radar) y rayos al final de Temperaturas; ventana emergente del videoportero con imagen en directo y botón de abrir puerta (opcional). Sin probar en el videoportero real.
- v2.7.3: previsión de nubes robusta (reintento cada 2 min, daily/twice_daily/hourly, hora local) y diagnóstico en el sensor y en la pestaña Solar.
- v2.7.2: controles numéricos del Deye con valor exacto en tiempo real y caja editable.
- v2.7.1: «Aplicar» actúa sobre los programas de madrugada (1 y 2 antes de las 08:00).

## En curso
- Poder mover las gráficas del panel (en modo tablet algunas quedan raras).

## Pendiente / por verificar
- Dependabot añadido en este cambio: revisar los primeros PR que abra.

## Últimos cierres
<!-- Pegar aquí el bloque CIERRE de cada tarea (ver CLAUDE.md). Conservar solo los 5 últimos. -->

**Centro de Control · feat/pestana-luz-factusol · v2.8.0**
- Objetivo: pestaña Luz junto a Gas con todos los datos de Factusol y su importación/calibración.
- Cambios: `manager.luz_entities()` (registro, plataforma `factusol`), `ctx.luz`, `v_luz` en el JS, vista Luz condicional en el panel YAML, estilos de formulario; README y CHANGELOG.
- Pruebas: pytest 74 OK (nuevo test de la vista Luz); humo del JS con estados simulados (node).
- Verificado: no se tocó la detección de Gas TUR; sin Factusol la pestaña muestra un aviso.
- Pendientes: probar en la casa real (CSV real y registro de factura); Factusol ≥ 0.1.1 necesario.
- Próximo paso: fusionar con CI en verde y actualizar desde HACS.

**Centro de Control · feat/luz-factura-pdf · v2.9.0**
- Objetivo: importar facturas de luz en PDF desde la pestaña Luz sin teclear datos.
- Cambios: tarjeta «Importar factura en PDF» (lee el fichero en el navegador, lo envía en base64 a `factusol.importar_factura_pdf` y lo quita del selector), campo «primer día» en el formulario manual; CHANGELOG.
- Pruebas: pytest 74 OK; prueba de la acción con Node y un servicio simulado.
- Pendientes: probar con una factura real tras actualizar Factusol a 0.2.0.

## Último cierre
**Centro de Control · feat/arrastrar-tarjetas · v2.12.0**
- Objetivo: poder desanclar las tarjetas y moverlas con el ratón a otra sección (diseño 100 % personalizable).
- Cambios: en modo Diseño las tarjetas y gráficas se arrastran dentro de su sección o a otra; el movimiento se guarda por pestaña y dispositivo (`move` en `centro_control_diseno`); secciones vacías ocultas fuera del modo edición.
- Pruebas: pytest en verde, pruebas de Node (reubicar, orden, vaciar/ocultar sección, volver a la original, no-op) y arrastre simulado en Chrome headless.
- Pendientes: probar con ratón real en el PC; en táctil siguen las flechas.
