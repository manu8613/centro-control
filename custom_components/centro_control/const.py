"""Constants for Centro de Control.

No entity ids, IPs or names of any real installation live here: everything is
chosen by the user in the configuration screens and stored only in their Home
Assistant.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "centro_control"
NAME: Final = "Centro de Control"
AUTHOR: Final = "manu8613"
AUTHOR_URL: Final = "https://github.com/manu8613"
REPO_URL: Final = "https://github.com/manu8613/centro-control"
VERSION: Final = "2.5.0"

DEFAULT_TITLE: Final = "Centro de Control"
DASHBOARD_URL: Final = "centro-control"
DASHBOARD_ICON: Final = "mdi:monitor-dashboard"

STORAGE_VERSION: Final = 1
STORAGE_MINOR_VERSION: Final = 1
SAVE_DELAY: Final = 60

TICK: Final = timedelta(seconds=10)
PROBLEMS_TICK: Final = timedelta(seconds=30)
MAX_INTEGRATION_GAP: Final = 120.0  # s; longer gaps are not integrated
HISTORY_DAYS: Final = 800
ATTR_HISTORY_DAYS: Final = 62

# ---------------------------------------------------------------- subentries
SUB_STRING: Final = "string"
SUB_BATTERY: Final = "bateria"
SUB_CIRCUIT: Final = "circuito"
SUB_ZONE: Final = "zona_riego"
SUBENTRY_TYPES: Final = (SUB_STRING, SUB_BATTERY, SUB_CIRCUIT, SUB_ZONE)

# ---------------------------------------------------------------- general
CONF_CREATE_DASHBOARD: Final = "crear_panel"
CONF_BILLING_DAY: Final = "dia_factura"
CONF_NOTIFY_SERVICE: Final = "notificar_servicio"
CONF_NOTIFY_LEVEL: Final = "notificar_nivel"

# ---------------------------------------------------------------- grid
CONF_GRID_POWER: Final = "red_potencia"
CONF_GRID_SIGN: Final = "red_signo"
CONF_GRID_IMPORT_ENERGY: Final = "red_energia_importada"
CONF_GRID_EXPORT_ENERGY: Final = "red_energia_exportada"
CONF_GRID_VOLTAGE: Final = "red_tension"
CONF_GRID_FREQUENCY: Final = "red_frecuencia"
CONF_CONTRACTED_P1: Final = "potencia_contratada_p1"
CONF_CONTRACTED_P2: Final = "potencia_contratada_p2"
GRID_POSITIVE_IMPORT: Final = "positivo_importa"
GRID_POSITIVE_EXPORT: Final = "positivo_exporta"

# ---------------------------------------------------------------- load
CONF_LOAD_POWER: Final = "consumo_potencia"
CONF_LOAD_ENERGY: Final = "consumo_energia"

# ---------------------------------------------------------------- solar / inverter
CONF_PV_POWER: Final = "solar_potencia"
CONF_PV_ENERGY: Final = "solar_energia"
CONF_PV_FORECAST: Final = "solar_prevision_hoy"
CONF_PV_PEAK: Final = "solar_pico_wp"
CONF_INV_TEMP: Final = "inversor_temperatura"
CONF_INV_TEMP2: Final = "inversor_temperatura_dc"
CONF_INV_STATUS: Final = "inversor_estado"
CONF_INV_FAULT: Final = "inversor_fallo"
CONF_INV_ALARM: Final = "inversor_alarma"

# ---------------------------------------------------------------- tariff
CONF_PRICE_MODE: Final = "precio_modo"
PRICE_SENSOR: Final = "sensor"
PRICE_PERIODS: Final = "periodos"
PRICE_FLAT: Final = "unico"
CONF_PRICE_SENSOR: Final = "precio_sensor"
CONF_PRICE_P1: Final = "precio_p1"
CONF_PRICE_P2: Final = "precio_p2"
CONF_PRICE_P3: Final = "precio_p3"
CONF_PRICE_FLAT: Final = "precio_unico"
CONF_EXPORT_MODE: Final = "excedentes_modo"
EXPORT_NONE: Final = "ninguna"
EXPORT_FIXED: Final = "precio_fijo"
EXPORT_SENSOR: Final = "sensor"
CONF_EXPORT_PRICE: Final = "excedentes_precio"
CONF_EXPORT_SENSOR: Final = "excedentes_sensor"
CONF_EXPORT_CAP: Final = "excedentes_tope"
CONF_POWER_PRICE_P1: Final = "potencia_precio_p1"
CONF_POWER_PRICE_P2: Final = "potencia_precio_p2"
CONF_ELECTRICITY_TAX: Final = "impuesto_electrico"
CONF_VAT: Final = "iva"
CONF_METER_RENTAL: Final = "alquiler_contador"
CONF_OTHER_FIXED: Final = "otros_fijos"

# ---------------------------------------------------------------- gas
CONF_GAS_AUTO: Final = "gas_auto"
CONF_GAS_METER: Final = "gas_lectura"
CONF_GAS_FACTOR: Final = "gas_factor"
CONF_GAS_COST_TODAY: Final = "gas_coste_hoy"
CONF_GAS_COST_MONTH: Final = "gas_coste_mes"
CONF_GAS_BILL: Final = "gas_factura"
CONF_GAS_FLOW: Final = "gas_caudal"

# ---------------------------------------------------------------- lights
CONF_LIGHTS: Final = "luces"
CONF_LIGHTS_EXCLUDE: Final = "luces_excluir"
CONF_OUTDOOR_PATTERN: Final = "patron_exterior"

# ---------------------------------------------------------------- climate
CONF_TEMPERATURES: Final = "temperaturas"
CONF_HUMIDITIES: Final = "humedades"
CONF_CLIMATES: Final = "climas"
CONF_OUTDOOR_TEMP: Final = "temperatura_exterior"
CONF_TEMP_EXCLUDE_PATTERN: Final = "patron_excluir_temperaturas"
CONF_TEMP_MAX: Final = "temperatura_max"
CONF_TEMP_MIN: Final = "temperatura_min"
CONF_HUMIDITY_MAX: Final = "humedad_max"

# ---------------------------------------------------------------- irrigation
CONF_RAIN_SENSOR: Final = "lluvia_sensor"
CONF_SOIL_MIN: Final = "humedad_suelo_min"

# ---------------------------------------------------------------- co2
CONF_CO2_FACTOR: Final = "co2_factor_red"
CONF_CO2_SENSOR: Final = "co2_sensor"
CONF_CO2_GAS: Final = "co2_factor_gas"
CONF_CO2_TREE: Final = "co2_arbol"
CONF_CO2_CAR: Final = "co2_coche_km"

# ---------------------------------------------------------------- problems
CONF_STRING_TOLERANCE: Final = "tolerancia_strings"
CONF_CELL_DELTA_WARN: Final = "delta_celdas_aviso"
CONF_CELL_DELTA_CRIT: Final = "delta_celdas_critico"
CONF_CELL_MIN: Final = "celda_min"
CONF_CELL_MAX: Final = "celda_max"
CONF_BATTERY_TEMP_MAX: Final = "bateria_temp_max"
CONF_SOC_MIN: Final = "soc_min"
CONF_SOC_DIFF_WARN: Final = "diferencia_soc_aviso"
CONF_SOC_DIFF_CRIT: Final = "diferencia_soc_critico"
CONF_INV_TEMP_WARN: Final = "inversor_temp_aviso"
CONF_INV_TEMP_CRIT: Final = "inversor_temp_critico"
CONF_VOLTAGE_MIN: Final = "tension_min"
CONF_VOLTAGE_MAX: Final = "tension_max"
CONF_CHECK_DEVICE_BATTERIES: Final = "revisar_baterias"
CONF_DEVICE_BATTERY_MIN: Final = "bateria_dispositivo_min"
CONF_CHECK_SAFETY: Final = "revisar_seguridad"
CONF_UNMEASURED_MAX: Final = "no_medido_max"
CONF_CHECK_GRID_WITH_BATTERY: Final = "revisar_red_con_bateria"
CONF_GAS_FLOW_HOURS: Final = "gas_horas_continuo"

# ---------------------------------------------------------------- subentry keys
CONF_NAME: Final = "nombre"
CONF_POWER: Final = "potencia"
CONF_ENERGY: Final = "energia"
CONF_VOLTAGE: Final = "tension"
CONF_CURRENT: Final = "corriente"
CONF_PEAK: Final = "pico_wp"
CONF_GROUP: Final = "grupo"
CONF_SOC: Final = "soc"
CONF_BATTERY_SIGN: Final = "signo"
BAT_POSITIVE_DISCHARGE: Final = "positivo_descarga"
BAT_POSITIVE_CHARGE: Final = "positivo_carga"
CONF_TEMPERATURE: Final = "temperatura"
CONF_CAPACITY: Final = "capacidad_kwh"
CONF_CELLS: Final = "celdas"
CONF_CELL_LOW: Final = "celda_minima"
CONF_CELL_HIGH: Final = "celda_maxima"
CONF_CELL_DIFF: Final = "diferencia_celdas"
CONF_ALARMS: Final = "alarmas"
CONF_CYCLES: Final = "ciclos"
CONF_LINK: Final = "comunicacion"
CONF_BANK: Final = "suma_al_banco"
CONF_PARENT: Final = "padre"
CONF_IN_TOTAL: Final = "suma_en_total"
CONF_ICON: Final = "icono"
CONF_VALVE: Final = "valvula"
CONF_SOIL: Final = "humedad_suelo"
CONF_MINUTES: Final = "minutos"
CONF_MAX_MINUTES: Final = "minutos_max"

# ---------------------------------------------------------------- defaults
# Sources (checked 6 Nov 2026):
#  * Peajes 2026 2.0TD potencia P1 23,324952 / P2 0,443770 €/kW·año and cargos
#    P1 4,379461 / P2 0,281653 €/kW·año (MITECO).
#  * Impuesto especial sobre la electricidad 5,11269632 % and IVA 21 % since
#    1 June 2026.
#  * Alquiler de contador monofásico 0,81 €/mes; financiación bono social
#    9,011295 €/año por CUPS (2026).
#  * Factor de emisión: 0,102 kg CO2/kWh (CNMC, mix nacional 2024);
#    gas natural 0,182 kg CO2/kWh PCS (MITECO 2025).
DEFAULTS: Final[dict[str, object]] = {
    CONF_CREATE_DASHBOARD: True,
    CONF_BILLING_DAY: 1,
    CONF_NOTIFY_SERVICE: "",
    CONF_NOTIFY_LEVEL: "critico",
    CONF_GRID_SIGN: GRID_POSITIVE_IMPORT,
    CONF_CONTRACTED_P1: 4.6,
    CONF_CONTRACTED_P2: 4.6,
    CONF_PV_PEAK: 0,
    CONF_PRICE_MODE: PRICE_PERIODS,
    CONF_PRICE_P1: 0.20,
    CONF_PRICE_P2: 0.13,
    CONF_PRICE_P3: 0.09,
    CONF_PRICE_FLAT: 0.14,
    CONF_EXPORT_MODE: EXPORT_FIXED,
    CONF_EXPORT_PRICE: 0.05,
    CONF_EXPORT_CAP: True,
    CONF_POWER_PRICE_P1: round((23.324952 + 4.379461) / 365, 6),
    CONF_POWER_PRICE_P2: round((0.443770 + 0.281653) / 365, 6),
    CONF_ELECTRICITY_TAX: 5.11269632,
    CONF_VAT: 21.0,
    CONF_METER_RENTAL: round(0.81 * 12 / 365, 6),
    CONF_OTHER_FIXED: round(9.011295 / 365, 6),
    CONF_GAS_AUTO: True,
    CONF_GAS_FACTOR: 11.0,
    CONF_OUTDOOR_PATTERN: "porche|patio|jard[ií]n|terraza|fachada|exterior|piscina|foco|calle",
    CONF_TEMP_EXCLUDE_PATTERN: "bms|inversor|inverter|cpu|mos|celda|cell|dc_|bateria|battery|nevera|frigo|congelador|device_temperature|chip|soc_temp|forecast|previsi[oó]n|pron[oó]stico|aemet",
    CONF_TEMP_MAX: 32.0,
    CONF_TEMP_MIN: 10.0,
    CONF_HUMIDITY_MAX: 75.0,
    CONF_SOIL_MIN: 20.0,
    CONF_CO2_FACTOR: 0.102,
    CONF_CO2_GAS: 0.182,
    CONF_CO2_TREE: 22.0,
    CONF_CO2_CAR: 0.12,
    CONF_STRING_TOLERANCE: 30.0,
    CONF_CELL_DELTA_WARN: 0.05,
    CONF_CELL_DELTA_CRIT: 0.10,
    CONF_CELL_MIN: 2.90,
    CONF_CELL_MAX: 3.60,
    CONF_BATTERY_TEMP_MAX: 45.0,
    CONF_SOC_MIN: 10.0,
    CONF_SOC_DIFF_WARN: 5.0,
    CONF_SOC_DIFF_CRIT: 15.0,
    CONF_INV_TEMP_WARN: 60.0,
    CONF_INV_TEMP_CRIT: 70.0,
    CONF_VOLTAGE_MIN: 207.0,
    CONF_VOLTAGE_MAX: 253.0,
    CONF_CHECK_DEVICE_BATTERIES: True,
    CONF_DEVICE_BATTERY_MIN: 15.0,
    CONF_CHECK_SAFETY: True,
    CONF_UNMEASURED_MAX: 800.0,
    CONF_CHECK_GRID_WITH_BATTERY: True,
    CONF_GAS_FLOW_HOURS: 6.0,
}

LEVELS: Final = ("critico", "aviso", "info")

# Spanish national holidays with a fixed date (2.0TD treats them as valley).
FIXED_HOLIDAYS: Final = ((1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 8), (12, 25))

# Relative monthly solar production in mainland Spain (annual mean = 1).
SOLAR_SEASON: Final = (0.55, 0.70, 0.92, 1.03, 1.17, 1.27, 1.33, 1.24, 1.04, 0.82, 0.60, 0.50)

PERIODS: Final = ("hoy", "ayer", "mes", "factura", "ano", "total")
METRICS: Final = (
    "solar",
    "importada",
    "exportada",
    "consumo",
    "bateria_carga",
    "bateria_descarga",
    "coste_energia",
    "compensacion",
    "importada_p1",
    "importada_p2",
    "importada_p3",
    "co2_evitado",
    "co2_red",
    "gas_m3",
    "co2_gas",
)
