# Registro de cambios

Todas las versiones publicadas están en
[Releases](https://github.com/manu8613/centro-control/releases). Para volver a
una anterior: HACS → Centro de Control → ⋮ → **Volver a descargar** → elige la
versión → reinicia Home Assistant.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
las versiones [SemVer](https://semver.org/lang/es/): `MAYOR.MENOR.PARCHE`.

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
