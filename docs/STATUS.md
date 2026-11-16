# Estado

Versión publicada: v2.16.0 (v2.16.1 en PR) · Commit de referencia: `8d90495` · Actualizado: 2026-11-16

## Funciona (comprobado)
- v2.16.1 (PR): la pestaña Caldera aguanta lecturas que se pierden un momento (conserva el último valor 15 min), avisa de falta de señal del bus solo si dura más de 5 min y conserva el historial de la llama si falla una lectura. Probado en Chrome sin pantalla con lecturas no disponibles, cortes de señal y fallos del historial; falta verlo en la casa real.
- v2.16.0: pestaña Caldera con las entidades de ebusd (detección automática en el registro, plataforma MQTT, circuito «bai»): indicadores de aguja, estado S.xx, ciclo de quemado de 24 h con avisos y peligro, contadores y gráficas. Probada en Chrome sin pantalla con valores reales de una caldera e historial simulado; falta verla en la casa real.
- v2.15.0 (PR, sobre la rama de la v2.14.0): modo Diseño con arrastre con el dedo (asa ✥), ocultar tarjetas y títulos, y «Añadir» indicadores y gráficas de cualquier entidad en cualquier pestaña. Probado con toques simulados en Chrome sin pantalla; falta en la tablet real.
- v2.14.0 (PR): botón «Probar ventana de llamada» en Configuración, con lista en vivo (sensor, vídeo, audio, abrir, colgar). Probado con cámara simulada; falta en el videoportero real.
- v2.13.0: ventana del videoportero con botones «Activar audio» y «Colgar» además de «Abrir puerta». Probada con llamada simulada en Chrome sin pantalla; falta en el videoportero real (que el flujo de la cámara traiga sonido y qué entidad cuelga la llamada).
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
- Nada.

## Pendiente / por verificar
- Dependabot añadido en este cambio: revisar los primeros PR que abra.

## Últimos cierres
<!-- Pegar aquí el bloque CIERRE de cada tarea (ver CLAUDE.md). Conservar solo los 5 últimos. -->

**Centro de Control · feat/videoportero-audio-colgar · v2.13.0**
- Objetivo: que la ventana de llamada del videoportero tenga vídeo, botón de audio y botones de abrir y colgar, sobre cualquier pestaña.
- Cambios: botones «Activar audio» (quita el silencio del vídeo) y «Colgar» (cierra y, opcional, llama a la entidad `timbre_colgar` elegida en Configuración del panel); botones táctiles más grandes.
- Pruebas: pytest en verde; Chrome sin pantalla con llamada simulada en Resumen, Solar y Configuración (aparece, audio, doble toque de abrir, colgar, no reaparece).
- Pendientes: probar en el videoportero real; `timbre_colgar` solo se configura por dispositivo (no en las opciones de la integración); la ventana solo sale con el panel Centro de Control abierto; el audio es solo de escucha.

**Centro de Control · feat/videoportero-prueba · v2.14.0**
- Objetivo: botón en Configuración para comprobar la ventana del videoportero (apertura, vídeo, audio y colgar) sin esperar a una llamada.
- Cambios: `_bellTest` y lista de comprobación en vivo (`_bellTestRows`), detección de sonido en el flujo (`_bellHasSound`), la ventana de prueba no se cierra sola y «Colgar» avisa de lo que ha hecho antes de cerrar.
- Pruebas: pytest en verde; Chrome sin pantalla con cámara simulada, con y sin entidades y con y sin sonido.
- Pendientes: probar en el videoportero real; el aviso de «sin sonido» depende de lo que informe el navegador de la tablet.

**Centro de Control · feat/diseno-personalizable · v2.15.0**
- Objetivo: diseño totalmente personalizable: mover tarjetas, gráficas y títulos donde se quiera (también con el dedo) y añadir indicadores y gráficas propios a la pantalla principal.
- Cambios: asa ✥ con eventos de puntero (`_grabStart/_grabMove/_grabEnd`), `_dropAt` común a ratón y dedo, `hide` y `custom` en `centro_control_diseno`, diálogo «Añadir» (`_addOpen/_addOk`), `_customCards`; títulos movibles; corregido el resaltado del botón Diseño.
- Pruebas: pytest en verde; Chrome sin pantalla con toques simulados (arrastrar tarjeta y título, ocultar, añadir indicador y gráfica, recargar, restablecer, eliminar).
- Pendientes: probar en la tablet real; los botones de dentro de una tarjeta se mueven con su tarjeta, no sueltos; lo añadido se guarda por dispositivo (no se comparte entre tablet y PC).

**Centro de Control · feat/pestana-caldera · v2.16.0**
- Objetivo: pestaña Caldera con los datos de ebusd: indicadores de aguja, gráficas, marcadores y comprobación del ciclo de quemado con aviso y alerta de peligro.
- Cambios: `ebusd_key`/`EBUSD_KEYS` y `caldera_entities()` en `manager.py`; `caldera` en el contexto y en la configuración del panel; `v_caldera`, `_boilerChecks`, `_boilerCycles`, `_boilerLoad` y series `onoff` en el JS; insignia en la barra; vista Caldera en el panel clásico; README y CHANGELOG.
- Pruebas: pytest 77 OK; Chrome sin pantalla (escritorio y móvil) con un caso correcto y otro con avería, presión alta, bloqueo y encendidos fallidos.
- Pendientes: probar en la casa real; los avisos solo se ven con el panel abierto (no llegan a la pestaña Problemas ni como notificación); la llama se lee por sondeo, así que los ciclos más cortos que el intervalo de sondeo no se ven; los límites (presión, temperatura, ciclos cortos) son fijos, no configurables.

## Último cierre
**Centro de Control · fix/caldera-cortes-breves · v2.16.1**
- Objetivo: que la pestaña Caldera no vaya y venga entre «con datos» y «sin datos».
- Cambios: `_bs`/`_bn` (conservan la última lectura buena `BOILER_GRACE` = 15 min) y `_boilerStale` en el JS; aviso de falta de señal solo tras `BOILER_SIGNAL_GRACE` = 5 min según `last_changed`; si falla la lectura del historial se conserva el anterior y se reintenta a los 30 s; prueba que impide volver a leer estados sin pasar por `_bs`.
- Pruebas: pytest en verde; Chrome sin pantalla, antes y después, con presión e ida no disponibles (1, 3 y 17 min), señal del bus en off 8 s y 10 min, y fallo del historial.
- Pendientes: verlo en la casa real; si siguen los cortes de señal de verdad, el fondo está en el bus (colisiones por el sondeo de ebusd), no en el panel.
