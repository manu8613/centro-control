# Registro de cambios

Todas las versiones publicadas están en
[Releases](https://github.com/manu8613/centro-control/releases). Para volver a
una anterior: HACS → Centro de Control → ⋮ → **Volver a descargar** → elige la
versión → reinicia Home Assistant.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
las versiones [SemVer](https://semver.org/lang/es/): `MAYOR.MENOR.PARCHE`.

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
