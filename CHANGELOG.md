# Registro de cambios

Todas las versiones publicadas están en
[Releases](https://github.com/manu8613/centro-control/releases). Para volver a
una anterior: HACS → Centro de Control → ⋮ → **Volver a descargar** → elige la
versión → reinicia Home Assistant.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
las versiones [SemVer](https://semver.org/lang/es/): `MAYOR.MENOR.PARCHE`.

## [2.7.4] - 2026-11-10

### Añadido
- Solar: junto a la «Intensidad de carga» por red se ve la potencia en vatios (intensidad × tensión de la batería, la de tu banco si la tienes configurada o 51,2 V nominales), también en tiempo real al mover el deslizador o escribir.
- La intensidad de carga por red no puede superar la potencia contratada **menos lo que consume la casa en ese momento** (p. ej. 4,6 kW − 0,6 kW = 4 kW ⇒ 75 A a 52,8 V): el deslizador y la caja se limitan a ese máximo, el panel recorta lo que se escriba y avisa si el inversor ya tiene un valor por encima.

- Carga por red esta noche: junto a lo aconsejado, ahora puedes elegir tú el SOC con el que quieres empezar el día a las 08:00 («Elegir yo el SOC»: deslizador y caja con el valor exacto). Muestra al momento cuánta energía aportaría la red, y la diferencia con lo aconsejado. «Aplicar» usa tu valor, y hay un botón para no cargar por red esta noche. Se recuerda por dispositivo; «Usar lo aconsejado» vuelve al modo automático.

- Solar → Inversor: las tarjetas de Estado, Fallo y Alarma cambian de color según la gravedad: verde si todo es normal, ámbar si es algo a revisar o que se arregla (alarmas, cambio de modo, red, comunicación), rojo si es grave (sobrecorriente, fugas, temperatura excesiva, fallo del inversor) y azul para reposo (standby, autotest). Un fallo desconocido se pinta en rojo por seguridad.

- Nueva pestaña **Enchufes**: enchufes e interruptores de Home Assistant con su estado, el consumo de los que miden (sensor de potencia del mismo dispositivo) y un toque para encender o apagar. Se agrupan por estancia (si Home Assistant las tiene) o en interior/exterior. Opciones nuevas en Configurar → «Luces y enchufes»: lista de enchufes (vacío = todos) y enchufes que no quieres ver.
- Luces y enchufes **dinámicos**: se leen en directo de Home Assistant, así que un dispositivo nuevo aparece solo, sin «Regenerar panel» ni recargar. Se omiten las entidades ocultas, de diagnóstico o de configuración y las de la propia integración y de Solarman.

- Temperaturas, al final de todo: **mapa de nubes y lluvia en tiempo real** (tarjeta Weather Radar Card) y **mapa de rayos en tiempo real** (mapa de Home Assistant con los rayos de Blitzortung), con el contador de rayos y la distancia y dirección del último. Se crean con las tarjetas que ya tienes instaladas, no hace falta configurar nada y se ven bien en la tablet.

### Cambiado
- Programas 1 y 2 del Deye: se quita el deslizador de «Potencia» (en el inversor esa potencia también marca la velocidad de descarga); quedan la hora, el SOC y la carga.

## [2.7.3] - 2026-11-10

### Corregido
- Nubosidad y previsión del cielo: si la previsión no estaba disponible en el primer intento (arranque, recarga de la integración, entidad del tiempo aún no lista), no se volvía a pedir hasta 30 minutos después y la pestaña Solar se quedaba en «Esperando la previsión». Ahora reintenta cada 2 minutos hasta tenerla, y al recibirla actualiza la recomendación al momento.
- Si la entidad del tiempo no ofrece previsión diaria, se prueba la de dos veces al día y la horaria (se promedia por día), y se usa el estado actual para hoy.
- Los días se calculan en hora local (antes una previsión en UTC podía caer en el día anterior).

### Añadido
- Diagnóstico: el sensor «Recomendación de carga por red» lleva el atributo `meteo` (entidad, tipo de previsión, error) y la pestaña Solar muestra el motivo cuando no hay previsión. Un aviso en el registro de Home Assistant lo indica una vez.

## [2.7.2] - 2026-11-10

### Cambiado
- Solar: en los controles numéricos del Deye (potencia y SOC de los programas, intensidad de carga, SOC de inicio) el deslizador ahora va acompañado de una caja con el valor exacto. Se ve el número en tiempo real al arrastrar y se puede escribir a mano; se envía al inversor al soltar, al pulsar Intro o al salir de la caja, respetando los límites de la entidad.

## [2.7.1] - 2026-11-10

### Corregido
- **Aplicar** la recomendación de carga por red trata como programas de
  madrugada los programas 1 y 2 que empiezan antes de las 08:00 (antes dejaba
  el 2 sin carga). Con la programación por franjas activa ya no toca el
  interruptor general de carga por red.

## [2.7.0] - 2026-11-10

### Añadido
- Pestaña **Solar**: controles del inversor Deye. Carga de la batería por la
  red, intensidad de carga, SOC de inicio de la carga por red, programación por
  franjas (interruptor o selector) y programas 1 y 2 (hora, potencia, SOC y
  carga). Nueva pantalla **Configurar → Inversor Deye** para
  elegir las entidades; los valores se limitan al mínimo y máximo del inversor.
- Nubosidad de hoy y de los próximos 5 días con la producción solar estimada
  (entidad `weather` en **Configurar → Solar e inversor**; si la previsión no
  trae `cloud_coverage`, se estima por el estado del cielo).
- Recomendación de carga por red para la noche: prioriza la batería de 08:00 a
  00:00 y compara la producción prevista con tu consumo medio y el SOC. Botón
  **Aplicar** (con confirmación) y sensor `recomendacion_carga_red`.
- Ajustes nuevos: previsión solar de mañana (opcional) y parte del consumo
  entre 08:00 y 00:00 (85 % por defecto).

## [2.6.0] - 2026-11-10

### Añadido
- Botón **Rotar** en la barra: cambia de pestaña automáticamente, pensado para
  la tablet. Si tocas la pantalla espera unos segundos antes de seguir.
- Nueva pestaña **Configuración**: tiempo en cada pestaña, tiempo de espera tras
  un toque y qué pestañas entran en la rotación. Se guarda en cada dispositivo,
  igual que el diseño.

## [2.5.0] - 2026-11-09

### Añadido
- Logo e icono propios (carpeta `brand/`): se ven en Integraciones y en HACS
  con Home Assistant 2026.3 o posterior.
- Capturas de ejemplo en el README, con datos genéricos.

### Corregido
- En el móvil, el título y el botón Diseño ya no tapan las pestañas: en
  pantallas estrechas solo queda el logo y el icono de Diseño.

## [2.4.0] - 2026-11-08

### Añadido
- Botón **Diseño** en la barra del panel: mueve secciones, tarjetas y gráficas
  con flechas y cambia su ancho (⤢). Se guarda en cada dispositivo, así la
  tablet y el PC pueden tener su propio diseño; «Restablecer pestaña» vuelve
  al original.

### Cambiado
- Las secciones que solo tienen gráficas ocupan todo el ancho y ponen dos
  gráficas por fila (una en pantallas estrechas): ya no quedan columnas
  vacías a la derecha.
- La gráfica «Diferencia de SOC 48 h» se calcula con el historial de las dos
  baterías, así que se ve completa desde el primer día.
- Si el sensor de comunicación del BMS está en «desconocido» pero llegan
  datos, se muestra «Comunicando».

## [2.3.0] - 2026-11-08

### Añadido
- Baterías de detalle: opción «Cuenta para el banco» en cada batería. Las que
  no cuentan muestran sus datos (celdas, temperaturas, alarmas, ciclos) sin
  sumarse al SOC, la potencia ni la energía del banco, que pueden venir del
  inversor.
- «Comunicación del BMS» (sensor binario de conectividad) en cada batería: se
  ve en el panel y avisa cuando el BMS deja de contestar.
- Sensor «Diferencia de SOC entre baterías» y marcador en las pestañas
  Batería y Puente de mando, con gráfica de 48 h. Umbrales de aviso (5 puntos)
  y crítico (15) en *Detección de problemas*.
- La API de configuración acepta entidades por su nombre (`"~sensor:BMS 1
  SOC"`) y devuelve las encontradas en `resueltas`.

### Cambiado
- Al aplicar un plan, los elementos con el mismo tipo y título se actualizan
  en su sitio en vez de borrarse y crearse de nuevo: conservan sus entidades,
  su histórico y sus contadores.

## [2.2.0] - 2026-11-06

### Añadido
- La API de configuración acepta `"reiniciar_contadores": true` y
  `"importar_historico": <días>` para empezar de cero y rellenar el histórico
  con las estadísticas de Home Assistant tras aplicar un plan.

### Corregido
- Detección de Gas TUR: «factura» ya no se confunde con «previsión de
  factura» ni con «consumo de la factura».
- Diferencia de celdas en mV por debajo de 1 mV.
- Los sensores del propio Centro de Control no entran en las listas
  automáticas de temperaturas.

## [2.1.1] - 2026-11-06

### Corregido
- Script de Windows: en Windows PowerShell 5.1 usa curl.exe, porque .NET no
  conecta por TLS 1.3 ni con certificados propios (https por IP). Con https por
  IP acepta el certificado de tu Home Assistant sin tener que poner -Inseguro.

## [2.1.0] - 2026-11-06

### Añadido
- **Copias y configuración por API** (solo administradores):
  `/api/centro_control/inventario`, `/api/centro_control/configuracion`
  (leer, simular, aplicar y restaurar; guarda una copia antes de cada cambio)
  y `/api/centro_control/estado`.
- Script de Windows `tools/centro-control.ps1` para exportar, aplicar un plan,
  restaurar y comprobar con un token, con copia completa de Home Assistant
  antes de tocar nada.
- Pestaña **Coste** con luz y gas juntos: total previsto, factura en curso de
  cada uno y previsión del gas (Gas TUR).

### Cambiado
- Panel rehecho: actualiza solo las tarjetas que cambian (sin parpadeos),
  gráficas con valores al pasar el ratón y ejes legibles, celdas en rejilla,
  termostatos con ±, luces con brillo, riego con deslizador y aviso en la
  pestaña Problemas.
- Las gráficas de 24 h leen el historial de tus sensores originales, así que
  muestran lo de siempre aunque Centro de Control sea nuevo.
- Los sensores de servicios meteorológicos (AEMET, Met.no…) y de previsión ya
  no entran en «Temperaturas» ni avisan de frío o calor.

## [2.0.0] - 2026-11-06

### Cambiado
- **Panel propio en JavaScript**: el panel de la barra lateral ya no es un
  panel de Lovelace con tarjetas de HACS, sino un panel independiente que
  trae la integración. Se ve igual en cualquier instalación, con o sin
  card-mod, Mushroom o ApexCharts, y con cualquier tema.
- Flujo de energía animado con el reparto real (solar → casa, batería y red),
  gráficas propias de 24 h, 7 días, 30 días y meses, celdas, ranking de
  consumos, luces con brillo, termostatos con ±, riego y simulador con
  deslizadores. Se adapta a móvil.
- La versión con tarjetas de Lovelace se sigue guardando en
  `config/centro_control/panel_<id>.yaml` para quien la prefiera.

## [1.1.1] - 2026-11-06

### Corregido
- Las barras de las celdas se escalan entre la celda más baja y la más alta,
  para que el desequilibrio se vea (antes todas parecían iguales).
- Barras del ranking de consumos más cortas para que cada circuito quepa en
  una línea.

## [1.1.0] - 2026-11-06

### Añadido
- Importación del histórico de Home Assistant: la primera vez que arranca
  rellena el histórico diario con las estadísticas del recorder (contadores de
  energía y medias de potencia), para que las previsiones usen tu año pasado
  desde el primer día. También con el botón «Importar histórico» y la acción
  `centro_control.importar_historico`. El coste de esos días se estima con el
  precio medio.

### Cambiado
- Las listas automáticas de luces, termostatos, temperaturas y humedades
  ignoran entidades de diagnóstico, ocultas o desactivadas (p. ej. la
  temperatura interna de los enchufes Zigbee).
- Las pilas de los móviles ya no cuentan como «pila baja».
- Los termómetros exteriores no avisan de frío o calor; umbrales por defecto
  10–32 °C.

## [1.0.0] - 2026-11-06

### Añadido
- Integración con pantallas de configuración: red, consumo, solar e inversor,
  tarifa, gas, luces, temperaturas, riego, CO₂ y detección de problemas.
- Strings, baterías, circuitos y zonas de riego como elementos que se añaden,
  editan y borran uno a uno, sin límite.
- Contabilidad de energía propia (hoy, ayer, mes, factura, año, total) con
  histórico diario de 800 días, desde contadores o integrando la potencia.
- Factura de la luz 2.0TD (potencia, energía por periodos o sensor PVPC,
  compensación de excedentes con tope, impuesto eléctrico, alquiler, IVA),
  previsión al cierre y de las tres siguientes, y simulador «¿y si…?».
- CO₂ evitado y emitido (red y gas), equivalencias, autoconsumo y
  autosuficiencia.
- Detección de problemas: fuentes caídas, strings que rinden menos, celdas
  desequilibradas, alarmas del BMS e inversor, temperaturas, tensión de red,
  límite de potencia, consumo sin medir, pilas bajas, fugas, riego atascado,
  gas continuo… con avisos opcionales.
- Riego temporizado con cierre de seguridad y omisión por lluvia.
- Panel futurista de 12 pestañas generado automáticamente.
