# Estado

Versión publicada: v2.19.0 (v2.20.0 en PR) · Commit de referencia: `4decf1e` · Actualizado: 2026-11-23

## Funciona (comprobado)
- v2.20.0 (PR): Diseño sin huecos muertos (las secciones se empaquetan en filas de 8 px), arrastrar secciones enteras por su asa ✥ a la columna elegida soltar tarjetas en cualquier espacio libre (van a la sección más cercana), crear secciones nuevas de ancho y alto elegidos, marcadores de aguja propios y los de autosuficiencia como tarjetas sueltas. Probado en Chrome sin pantalla a 1735 px con ratón real y con eventos táctiles simulados; falta en la tablet real.
- v2.19.0: Puente de mando con autosuficiencia, sol, temperaturas, persianas y estores. Falta verlo en la casa real.
- v2.19.0 (PR): Puente de mando con marcadores de autosuficiencia (ahora y hoy), salida y puesta del sol, temperatura media de casa con máxima y mínima por estancia y la exterior, y control de persianas y estores por separado. Probado con pytest y Chrome sin pantalla (escritorio y móvil, con y sin entidades, botones y deslizador); hora del sol comparada con astral; falta verlo en la casa real.
- v2.18.0: la pestaña Caldera detecta colisiones del bus eBUS con el Tado (cortes de señal y reinicios de ebusd, confirmados con la conexión del bridge del Tado), avisa por el servicio de notificación y permite hacer pruebas de convivencia por configuración de ebusd. Probado con pytest y Chrome sin pantalla; falta probarlo en la casa real.
- v2.17.1: la barra de pestañas se desliza con el dedo sin cortarse y deja llegar a Configuración (ya no se reconstruye en cada refresco ni mientras se toca). Probado en Chrome sin pantalla antes y después; falta en la tablet real.
- v2.17.0 (PR): la pestaña Caldera solo avisa de lo que se elija en Configuración (por dispositivo; por defecto, solo las averías de la caldera) y no enseña nada si no salta ninguno. Probado en Chrome sin pantalla con presión alta, estado S.41, falta de señal y avería, con selección, recarga y «Ninguno»; falta verlo en la casa real.
- v2.16.1: la pestaña Caldera aguanta lecturas que se pierden un momento (conserva el último valor 15 min), avisa de falta de señal del bus solo si dura más de 5 min y conserva el historial de la llama si falla una lectura. Probado en Chrome sin pantalla con lecturas no disponibles, cortes de señal y fallos del historial; falta verlo en la casa real.
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

**Centro de Control · fix/caldera-cortes-breves · v2.16.1**
- Objetivo: que la pestaña Caldera no vaya y venga entre «con datos» y «sin datos».
- Cambios: `_bs`/`_bn` (conservan la última lectura buena `BOILER_GRACE` = 15 min) y `_boilerStale` en el JS; aviso de falta de señal solo tras `BOILER_SIGNAL_GRACE` = 5 min según `last_changed`; si falla la lectura del historial se conserva el anterior y se reintenta a los 30 s; prueba que impide volver a leer estados sin pasar por `_bs`.
- Pruebas: pytest en verde; Chrome sin pantalla, antes y después, con presión e ida no disponibles (1, 3 y 17 min), señal del bus en off 8 s y 10 min, y fallo del historial.
- Pendientes: verlo en la casa real; si siguen los cortes de señal de verdad, el fondo está en el bus (colisiones por el sondeo de ebusd), no en el panel.

**Centro de Control · feat/caldera-convivencia-tado · v2.18.0**
- Objetivo: detectar colisiones ebusd ↔ Tado y avisar, para saber qué parámetros de ebusd permiten que convivan.
- Cambios: `convivencia.py` (monitor de cortes de señal y reinicios, veredictos), enganche en `manager.py` (listeners, guardado, problemas y notificación), sensor `convivencia_ebus`, servicios `prueba_convivencia_*`, sección en la pestaña Caldera.
- Pruebas: pytest 101 OK; Chrome sin pantalla con cortes, corte largo, prueba en curso e historial.
- Pendientes: probar en la casa real; HA no ve los choques ni los reintentos del Tado, solo la señal de ebusd.

**Centro de Control · feat/puente-sol-temperaturas-persianas · v2.19.0**
- Objetivo: en el Puente de mando, salida y puesta del sol, temperatura media de casa con la máxima y mínima por estancia y la exterior, control de persianas y estores por separado, y marcadores de autosuficiencia de ahora y de hoy.
- Cambios: `sunTimes()` y `_sunToday()`/`sunCard()`, `_outdoorTemp()`/`tempCard()`, `_coverGroups()`/`coverCard()` (servicios `cover.*` y `data-coverpos`), `selfColor()` y marcadores en la cabecera; opciones `persianas`, `estores` y `persianas_excluir`; README, CHANGELOG y traducciones.
- Pruebas: pytest 101 OK; Chrome sin pantalla en escritorio y móvil con persianas, estores, garaje y toldo (excluidos), sin entidades opcionales; llamadas a `cover.open_cover`, `close_cover` y `set_cover_position` comprobadas; sol frente a astral (< 1 min).
- Pendientes: verlo en la casa real; `scripts/make_translations.py` está desfasado frente a los JSON (no incluye lo de la v2.18.0), por eso las traducciones se han tocado a mano; el panel clásico (Lovelace) no tiene estas tarjetas.

## Último cierre
**Centro de Control · feat/diseno-libre · v2.20.0**
- Objetivo: poder mover secciones y tarjetas del modo Diseño a cualquier hueco para aprovechar el espacio (ejemplo: la sección de Persianas/Estores bajo la S1 y la tarjeta HOY bajo la S3).
- Cambios: cuadrícula con filas de 8 px y `_pack()` (cada sección ocupa su alto, con `ResizeObserver`); `--sp`/`--cs` para ancho y columna fija de sección; asa ✥ de sección (`_grabStart/_grabMove/_grabEnd`), guía `.secghost`, `_snapCol`, `_dropSec`; `_nearSec` como destino de soltado de tarjetas; `col` en `centro_control_diseno`; README y CHANGELOG.
- Pruebas: pytest 101 OK; Chrome sin pantalla a 1735 px: sin solapes, arrastre de sección con ratón real (columna y hueco), tarjeta soltada en espacio libre con ratón (HTML5) y con el asa en táctil simulado; sección nueva (ancho, alto, borrar) y marcador propio.
- Pendientes: probar en la tablet real con el dedo; la sección cae en el primer hueco libre de su columna (si hay sitio más arriba, sube); lo que se coloca es por dispositivo y no se comparte entre tablet y PC.
