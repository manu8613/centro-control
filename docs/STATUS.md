# Estado

Versión publicada: v2.7.3 (v2.7.4 en PR) · Commit de referencia: `13aaa82` · Actualizado: 2026-11-10

## Funciona (comprobado)
- Integración HACS con panel propio en JS, CI (pytest, hassfest, HACS) y release automática con ZIP.
- Detecta Gas TUR si está instalado.
- v2.6.0: botón Rotar + pestaña Configuración (rotación de pestañas por dispositivo). Falta probarla en la tablet real.
- v2.7.0: Solar con controles del Deye (carga por red, programas 1 y 2), nubosidad a 5 días y recomendación de carga nocturna. Probado con las opciones reales de un Deye (Solarman).
- v2.7.4 (PR): intensidad de carga por red en vatios y limitada a la potencia contratada menos el consumo de la casa; programas 1 y 2 sin deslizador de potencia; SOC nocturno manual junto al aconsejado; tarjetas Estado/Fallo/Alarma del inversor en verde/ámbar/rojo; pestaña Enchufes y luces/enchufes dinámicos; mapas de nubes (radar) y rayos al final de Temperaturas; ventana emergente del videoportero con imagen en directo y botón de abrir puerta (opcional). Sin probar en el videoportero real.
- v2.7.3: previsión de nubes robusta (reintento cada 2 min, daily/twice_daily/hourly, hora local) y diagnóstico en el sensor y en la pestaña Solar.
- v2.7.2: controles numéricos del Deye con valor exacto en tiempo real y caja editable.
- v2.7.1: «Aplicar» actúa sobre los programas de madrugada (1 y 2 antes de las 08:00).

## En curso
- Poder mover las gráficas del panel (en modo tablet algunas quedan raras).

## Pendiente / por verificar
- Dependabot añadido en este cambio: revisar los primeros PR que abra.

## Últimos cierres
<!-- Pegar aquí el bloque CIERRE de cada tarea (ver CLAUDE.md). Conservar solo los 5 últimos. -->
