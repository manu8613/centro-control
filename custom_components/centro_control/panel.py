"""Lovelace dashboard of Centro de Control (pure data, no Home Assistant imports).

Twelve tabs with a dark, neon "control room" look. Needs, from HACS:
Mushroom, ApexCharts card, card-mod and Power Flow Card Plus.

``build_panel`` receives the real entity ids (ours and the user's) and returns
the dashboard as a dict; nothing here is specific to any installation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import AUTHOR, AUTHOR_URL, NAME, REPO_URL, VERSION

# ---------------------------------------------------------------------- palette
CYAN = "#00e5ff"
AMBER = "#ffc400"
GREEN = "#00e676"
PINK = "#ff4fd8"
VIOLET = "#b388ff"
BLUE = "#40c4ff"
ORANGE = "#ff9100"
RED = "#ff1744"
LIME = "#c6ff00"
GOLD = "#ffd740"
TEXT = "#e6f7ff"
MUTED = "#8fb3c9"

BACKGROUND = (
    "radial-gradient(1200px 600px at 8% -10%, rgba(0,229,255,.16), transparent 60%), "
    "radial-gradient(900px 500px at 110% 0%, rgba(255,79,216,.10), transparent 60%), "
    "repeating-linear-gradient(0deg, rgba(0,229,255,.035) 0 1px, transparent 1px 44px), "
    "repeating-linear-gradient(90deg, rgba(0,229,255,.035) 0 1px, transparent 1px 44px), "
    "linear-gradient(180deg, #030712 0%, #060d20 100%) fixed"
)

CARD_STYLE = """ha-card {{
  background: linear-gradient(150deg, rgba(10,20,44,.92) 0%, rgba(3,8,20,.94) 100%) !important;
  border: 1px solid {c}55 !important;
  border-radius: 16px !important;
  box-shadow: inset 0 0 0 1px {c}14, 0 0 22px {c}26, 0 8px 24px rgba(0,0,0,.45) !important;
  --primary-text-color: {text};
  --secondary-text-color: {muted};
  --ha-card-header-color: {c};
  --card-background-color: transparent;
  color: {text};
  font-variant-numeric: tabular-nums;
  letter-spacing: .2px;
  overflow: hidden;
}}
ha-card::before {{
  content: ""; position: absolute; inset: 0 0 auto 0; height: 2px;
  background: linear-gradient(90deg, transparent, {c}, transparent); opacity: .85;
}}
"""

TITLE_STYLE = """ha-card {{
  background: transparent !important; border: none !important; box-shadow: none !important;
  --primary-text-color: {c};
  color: {c};
}}
ha-card h2, ha-card h1 {{
  text-transform: uppercase; letter-spacing: 3px; font-weight: 600;
  text-shadow: 0 0 10px {c}aa, 0 0 22px {c}55; margin: 0;
}}
"""

PERIOD_LABELS = "{'hoy':'Hoy','ayer':'Ayer','mes':'Este mes','factura':'Factura en curso','ano':'Este año','total':'Total'}"

MACROS = """{%- macro n(x, d=1) -%}{{ ('%.' ~ d ~ 'f') | format(x | float(0)) | replace('.', ',') }}{%- endmacro -%}
{%- macro w(x) -%}{%- set v = x | float(0) -%}{%- if v | abs >= 1000 -%}{{ n(v / 1000, 2) }} kW{%- else -%}{{ n(v, 0) }} W{%- endif -%}{%- endmacro -%}
{%- macro bar(v, vmax, c, width=18) -%}{%- set k = ((v | float(0)) / (vmax | float(1)) * width) | round(0, 'floor') | int if vmax | float(0) > 0 else 0 -%}{%- set k = [[k, 0] | max, width] | min -%}<font color="{{ c }}">{{ '█' * k }}</font><font color="#1d2d4a">{{ '█' * (width - k) }}</font>{%- endmacro -%}
"""


# ---------------------------------------------------------------------- context
@dataclass
class Light:
    entity: str
    name: str
    outdoor: bool
    dimmable: bool


@dataclass
class PanelContext:
    """Everything the panel needs to know."""

    title: str
    ids: dict[str, str]  # our entities: key -> entity_id ("<sub_id>:<key>" for subentries)
    settings: dict[str, Any]
    strings: list[dict[str, Any]] = field(default_factory=list)  # id, name, power, voltage, current, peak_wp
    batteries: list[dict[str, Any]] = field(
        default_factory=list
    )  # id, name, soc, power, voltage, current, temperatures, cells, cycles, positive_charge
    circuits: list[dict[str, Any]] = field(default_factory=list)  # id, name, power, group, icon, in_total
    zones: list[dict[str, Any]] = field(default_factory=list)  # id, name, valve, soil
    lights: list[Light] = field(default_factory=list)
    climates: list[str] = field(default_factory=list)
    temperatures: list[str] = field(default_factory=list)
    humidities: list[str] = field(default_factory=list)
    gas: dict[str, str] = field(default_factory=dict)  # Gas TUR / manual gas entities

    def s(self, key: str) -> Any:
        value = self.settings.get(key)
        return None if value in ("", None, []) else value


# ---------------------------------------------------------------------- card helpers


def neon(color: str) -> dict[str, Any]:
    return {"style": CARD_STYLE.format(c=color, text=TEXT, muted=MUTED)}


def md(content: str, color: str = CYAN, columns: int | str | None = None, **extra: Any) -> dict[str, Any]:
    card: dict[str, Any] = {"type": "markdown", "content": content, "card_mod": neon(color), **extra}
    if columns is not None:
        card["grid_options"] = {"columns": columns}
    return card


def title(text: str, subtitle: str = "", icon: str = "mdi:hexagon-outline", color: str = CYAN) -> dict[str, Any]:
    sub = f'\n<font color="{MUTED}">{subtitle}</font>' if subtitle else ""
    return {
        "type": "markdown",
        "content": f'## <ha-icon icon="{icon}"></ha-icon> {text}{sub}',
        "card_mod": {"style": TITLE_STYLE.format(c=color)},
        "grid_options": {"columns": "full"},
    }


def tpl(
    entity: str | None,
    primary: str,
    secondary: str,
    icon: str,
    color: str,
    columns: int | str = 6,
    tap: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    card: dict[str, Any] = {
        "type": "custom:mushroom-template-card",
        "primary": primary,
        "secondary": secondary,
        "icon": icon,
        "color": color,
        "multiline_secondary": True,
        "tap_action": tap or ({"action": "more-info"} if entity else {"action": "none"}),
        "card_mod": neon(color),
        "grid_options": {"columns": columns},
        **extra,
    }
    if entity:
        card["entity"] = entity
    return card


def tile(
    entity: str,
    name: str | None = None,
    color: str = CYAN,
    icon: str | None = None,
    features: list[dict[str, Any]] | None = None,
    columns: int | str = 6,
    **extra: Any,
) -> dict[str, Any]:
    card: dict[str, Any] = {
        "type": "tile",
        "entity": entity,
        "color": color,
        "card_mod": neon(color),
        "grid_options": {"columns": columns},
        **extra,
    }
    if name:
        card["name"] = name
    if icon:
        card["icon"] = icon
    if features:
        card["features"] = features
        card["features_position"] = "bottom"
    return card


def press(entity: str, name: str, icon: str, color: str, confirm: str | None = None, columns: int | str = 6) -> dict[str, Any]:
    action: dict[str, Any] = {"action": "perform-action", "perform_action": "button.press", "target": {"entity_id": entity}}
    if confirm:
        action["confirmation"] = {"text": confirm}
    return {
        "type": "button",
        "entity": entity,
        "name": name,
        "icon": icon,
        "show_state": False,
        "tap_action": action,
        "icon_height": "34px",
        "card_mod": neon(color),
        "grid_options": {"columns": columns},
    }


def gauge(
    entity: str,
    name: str,
    minimum: float,
    maximum: float,
    color: str,
    severity: dict[str, float] | None = None,
    columns: int | str = 6,
    unit: str | None = None,
) -> dict[str, Any]:
    card: dict[str, Any] = {
        "type": "gauge",
        "entity": entity,
        "name": name,
        "min": minimum,
        "max": maximum,
        "needle": True,
        "card_mod": neon(color),
        "grid_options": {"columns": columns},
    }
    if severity:
        card["severity"] = severity
    if unit:
        card["unit"] = unit
    return card


def apex(
    header: str,
    series: list[dict[str, Any]],
    color: str = CYAN,
    span: str = "24h",
    height: int = 260,
    columns: int | str = "full",
    stacked: bool = False,
    span_cfg: dict[str, Any] | None = None,
    yaxis: list[dict[str, Any]] | None = None,
    extra_apex: dict[str, Any] | None = None,
) -> dict[str, Any]:
    apex_config: dict[str, Any] = {
        "chart": {"height": height, "background": "transparent", "foreColor": MUTED, "stacked": stacked, "toolbar": {"show": False}},
        "theme": {"mode": "dark"},
        "grid": {"borderColor": "#1b2a44", "strokeDashArray": 3},
        "legend": {"show": True, "position": "bottom", "labels": {"colors": MUTED}},
        "tooltip": {"theme": "dark"},
        "xaxis": {"axisBorder": {"color": "#1b2a44"}, "axisTicks": {"color": "#1b2a44"}},
        "dataLabels": {"enabled": False},
    }
    if extra_apex:
        apex_config.update(extra_apex)
    card: dict[str, Any] = {
        "type": "custom:apexcharts-card",
        "graph_span": span,
        "header": {"show": True, "title": header, "show_states": False},
        "apex_config": apex_config,
        "series": series,
        "card_mod": neon(color),
        "grid_options": {"columns": columns},
    }
    if span_cfg:
        card["span"] = span_cfg
    if yaxis:
        card["yaxis"] = yaxis
    return card


def serie(entity: str, name: str, color: str, kind: str = "line", group: str | None = "5min", **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"entity": entity, "name": name, "color": color, "type": kind, "stroke_width": 2, **extra}
    if kind == "area":
        item.setdefault("opacity", 0.22)
    if group:
        item["group_by"] = {"func": "avg", "duration": group}
    return item


def history_serie(
    entity: str, field_name: str, name: str, color: str, source: str = "dias", kind: str = "column", scale: str = ""
) -> dict[str, Any]:
    """Series built from the daily/monthly history kept in the 'historico' sensor."""
    key = "fecha" if source == "dias" else "mes"
    suffix = "T12:00:00" if source == "dias" else "-15T12:00:00"
    js = f"return (entity.attributes.{source} || []).map(d => [new Date(d.{key} + '{suffix}').getTime(), (d['{field_name}'] || 0){scale}]);"
    return {"entity": entity, "name": name, "color": color, "type": kind, "data_generator": js, "show": {"in_header": False}}


def section(cards: list[dict[str, Any]], span: int | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"type": "grid", "cards": cards}
    if span:
        out["column_span"] = span
    return out


def view(name: str, path: str, icon: str, sections: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "title": name,
        "path": path,
        "icon": icon,
        "type": "sections",
        "max_columns": 4,
        "background": BACKGROUND,
        "sections": sections,
    }


def nav(path: str) -> dict[str, Any]:
    return {"action": "navigate", "navigation_path": path}


class Templates:
    """Replaces ``@key`` placeholders with our real entity ids."""

    def __init__(self, ids: dict[str, str]) -> None:
        self.keys = sorted(ids, key=len, reverse=True)
        self.ids = ids

    def __call__(self, text: str) -> str:
        for key in self.keys:
            text = text.replace(f"@{key}", self.ids[key])
        return text


# ====================================================================== views


def build_panel(ctx: PanelContext, base_path: str = "centro-control") -> dict[str, Any]:
    t = Templates(ctx.ids)
    views = [
        _overview(ctx, t, base_path),
        _grid(ctx, t),
        _solar(ctx, t),
        _battery(ctx, t),
        _consumption(ctx, t),
        _problems(ctx, t),
        _cost(ctx, t),
        _co2(ctx, t),
        _gas(ctx, t),
        _lights(ctx, t),
        _climate(ctx, t),
        _irrigation(ctx, t),
    ]
    return {"title": ctx.title, "views": views}


def _credit() -> dict[str, Any]:
    return md(
        f'<center><font color="{MUTED}"><ha-icon icon="mdi:atom-variant"></ha-icon> {NAME} v{VERSION} · creado por '
        f'<a href="{AUTHOR_URL}">{AUTHOR}</a> · <a href="{REPO_URL}">código</a></font></center>',
        CYAN,
        "full",
        card_mod={"style": TITLE_STYLE.format(c=MUTED)},
    )


def _period_tile(t: Templates, color: str = CYAN) -> dict[str, Any]:
    return tile(t("@periodo"), "Periodo", color, "mdi:calendar-range", [{"type": "select-options"}], columns=12)


def _empty(text: str, color: str = MUTED) -> dict[str, Any]:
    return md(f'<ha-alert alert-type="info">{text}</ha-alert>', color, "full")


# ---------------------------------------------------------------------- 1. resumen


def _overview(ctx: PanelContext, t: Templates, base: str) -> dict[str, Any]:
    flow: dict[str, Any] = {
        "type": "custom:power-flow-card-plus",
        "entities": {
            "grid": {"entity": t("@potencia_red"), "name": "Red", "color_circle": True},
            "home": {"entity": t("@potencia_consumo"), "name": "Casa"},
        },
        "base_decimals": 0,
        "kilo_decimals": 2,
        "kilo_threshold": 1000,
        "clickable_entities": True,
        "card_mod": neon(CYAN),
        "grid_options": {"columns": "full"},
    }
    if ctx.strings or ctx.s("solar_potencia"):
        flow["entities"]["solar"] = {"entity": t("@potencia_solar"), "name": "Solar", "display_zero": True}
    if ctx.batteries:
        flow["entities"]["battery"] = {
            "entity": t("@potencia_bateria"),
            "state_of_charge": t("@soc_bateria"),
            "invert_state": True,  # ours: + discharge; the card: + charge
            "name": "Batería",
        }
    individual = [c for c in ctx.circuits if c["in_total"]][:4]
    if individual:
        palette = [PINK, VIOLET, ORANGE, BLUE]
        flow["entities"]["individual"] = [
            {"entity": c["power"], "name": c["name"], "icon": c["icon"], "color": palette[i]} for i, c in enumerate(individual)
        ]

    status = t(
        MACROS
        + """{%- set p = state_attr('@problemas','lista') or [] -%}
{%- set crit = p | selectattr('nivel','eq','critico') | list | count -%}
{%- set warn = p | selectattr('nivel','eq','aviso') | list | count -%}
## <ha-icon icon="mdi:atom-variant"></ha-icon> """
        + ctx.title.upper()
        + """
<font color="#8fb3c9">{{ now().strftime('%d/%m/%Y · %H:%M') }} · periodo {{ states('@periodo_tarifario') }} · {{ n(states('@precio_actual'), 4) }} €/kWh</font>

{% if crit %}<font color="#ff1744">◉ {{ crit }} crítico{{ 's' if crit > 1 }}</font>{% elif warn %}<font color="#ffc400">◉ {{ warn }} aviso{{ 's' if warn > 1 }}</font>{% else %}<font color="#00e676">◉ Todo en orden</font>{% endif %}"""
    )
    header = md(status, CYAN, "full", card_mod={"style": TITLE_STYLE.format(c=CYAN)})

    kpis = [
        tpl(
            t("@potencia_solar"),
            t(MACROS + "{{ w(states('@potencia_solar')) }}"),
            t(MACROS + "Solar · {{ n(states('@energia_solar'), 1) }} kWh hoy"),
            "mdi:solar-power-variant",
            AMBER,
            tap=nav("solar"),
        ),
        tpl(
            t("@potencia_consumo"),
            t(MACROS + "{{ w(states('@potencia_consumo')) }}"),
            t(MACROS + "Consumo · {{ n(states('@energia_consumo'), 1) }} kWh hoy"),
            "mdi:home-lightning-bolt",
            PINK,
            tap=nav("consumos"),
        ),
        tpl(
            t("@potencia_red"),
            t(MACROS + "{%- set g = states('@potencia_red') | float(0) -%}{{ w(g | abs) }} {{ '↓' if g > 0 else '↑' if g < 0 else '' }}"),
            t(
                MACROS
                + "{%- set g = states('@potencia_red') | float(0) -%}{{ 'Importando' if g > 0 else 'Vertiendo' if g < 0 else 'Red en reposo' }}"
            ),
            "mdi:transmission-tower",
            CYAN,
            tap=nav("red"),
        ),
        tpl(
            t("@autosuficiencia_ahora"),
            t(MACROS + "{{ n(states('@autosuficiencia_ahora'), 0) }} %"),
            t(MACROS + "Autosuficiencia · hoy {{ n(states('@autosuficiencia'), 0) }} %"),
            "mdi:shield-sun",
            LIME,
            tap=nav("co2"),
        ),
    ]
    if ctx.batteries:
        kpis.insert(
            3,
            tpl(
                t("@soc_bateria"),
                t(MACROS + "{{ n(states('@soc_bateria'), 0) }} %"),
                t(
                    MACROS
                    + "{%- set b = states('@potencia_bateria') | float(0) -%}Batería · {{ 'descargando ' ~ w(b) if b > 30 else 'cargando ' ~ w(-b) if b < -30 else 'en reposo' }}"
                ),
                "mdi:battery-charging-high",
                GREEN,
                tap=nav("bateria"),
            ),
        )
    kpis.append(
        tpl(
            t("@coste_energia"),
            t(MACROS + "{{ n(states('@coste_energia'), 2) }} €"),
            t(MACROS + "Coste hoy · ahorro solar {{ n(state_attr('@ahorro_solar','hoy'), 2) }} €"),
            "mdi:currency-eur",
            GOLD,
            tap=nav("coste"),
        )
    )

    today = md(
        t(
            MACROS
            + """{%- set per = states('@periodo') -%}{%- set P = """
            + PERIOD_LABELS
            + """ -%}
### <ha-icon icon="mdi:chart-donut-variant"></ha-icon> {{ P[per] }}
| | |
|:--|--:|
| <font color="#ffc400">☀ Producción</font> | **{{ n(state_attr('@energia_solar', per), 2) }} kWh** |
| <font color="#ff4fd8">⌂ Consumo</font> | **{{ n(state_attr('@energia_consumo', per), 2) }} kWh** |
| <font color="#00e5ff">↓ Importado</font> | {{ n(state_attr('@energia_importada', per), 2) }} kWh |
| <font color="#00e5ff">↑ Vertido</font> | {{ n(state_attr('@energia_exportada', per), 2) }} kWh |
| <font color="#ffd740">€ Coste energía</font> | {{ n(state_attr('@coste_energia', per), 2) }} € |
| <font color="#ffd740">€ Ahorro solar</font> | {{ n(state_attr('@ahorro_solar', per), 2) }} € |
| <font color="#c6ff00">♻ CO₂ evitado</font> | {{ n((state_attr('@co2_evitado', per) or {}).get('evitado_kg', 0), 1) }} kg |
"""
        ),
        CYAN,
        "full",
    )

    top = t(
        """{%- set p = state_attr('@problemas','lista') or [] -%}
{%- if p | count == 0 -%}<ha-alert alert-type="success">Sin problemas detectados.</ha-alert>
{%- else -%}{%- for x in p[:3] -%}
<ha-alert alert-type="{{ 'error' if x.nivel == 'critico' else 'warning' if x.nivel == 'aviso' else 'info' }}" title="{{ x.titulo }}">{{ x.detalle }}</ha-alert>
{%- endfor -%}{%- if p | count > 3 %}
<font color="#8fb3c9">… y {{ p | count - 3 }} más</font>{% endif -%}{%- endif -%}"""
    )
    problems = md(top, RED, "full")

    series = [
        serie(t("@potencia_solar"), "Solar", AMBER, "area"),
        serie(t("@potencia_consumo"), "Consumo", PINK),
        serie(t("@potencia_red"), "Red", CYAN),
    ]
    if ctx.batteries:
        series.append(serie(t("@potencia_bateria"), "Batería", GREEN))
    chart = apex("Últimas 24 h (W)", series, CYAN, height=280)

    return view(
        "Puente de mando",
        "resumen",
        "mdi:view-dashboard-variant",
        [
            section([header, flow], span=2),
            section([*kpis, _period_tile(t), today]),
            section([title("Alertas", "", "mdi:alert-decagram", RED), problems, chart]),
            section([_credit()], span=4),
        ],
    )


# ---------------------------------------------------------------------- 2. red


def _grid(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    live = [
        gauge(t("@uso_potencia_contratada"), "Potencia contratada", 0, 110, CYAN, {"green": 0, "yellow": 75, "red": 90}, unit="%"),
        tpl(
            t("@potencia_importada"),
            t(MACROS + "{{ w(states('@potencia_importada')) }}"),
            "Importando de la red",
            "mdi:transmission-tower-import",
            CYAN,
        ),
        tpl(
            t("@potencia_exportada"),
            t(MACROS + "{{ w(states('@potencia_exportada')) }}"),
            "Vertiendo a la red",
            "mdi:transmission-tower-export",
            LIME,
        ),
        tpl(
            t("@precio_actual"),
            t(MACROS + "{{ n(states('@precio_actual'), 4) }} €/kWh"),
            t("Periodo {{ states('@periodo_tarifario') }} · excedentes {{ states('@precio_excedentes') }} €/kWh"),
            "mdi:cash-clock",
            GOLD,
        ),
    ]
    for key, label, icon in (("red_tension", "Tensión", "mdi:sine-wave"), ("red_frecuencia", "Frecuencia", "mdi:waveform")):
        if ctx.s(key):
            live.append(tile(ctx.s(key), label, CYAN, icon, columns=6))
    energy = md(
        t(
            MACROS
            + """{%- set per = states('@periodo') -%}{%- set P = """
            + PERIOD_LABELS
            + """ -%}
### {{ P[per] }}
| | Importado | Vertido |
|:--|--:|--:|
| Energía | **{{ n(state_attr('@energia_importada', per), 2) }} kWh** | **{{ n(state_attr('@energia_exportada', per), 2) }} kWh** |
| Importe | {{ n(state_attr('@coste_energia', per), 2) }} € | {{ n(state_attr('@compensacion_excedentes', per), 2) }} € |
"""
        ),
        CYAN,
        "full",
    )
    price_sensor = ctx.s("precio_sensor") if ctx.s("precio_modo") == "sensor" else None
    charts = [
        apex(
            "Red 24 h (W)",
            [serie(t("@potencia_importada"), "Importado", CYAN, "area"), serie(t("@potencia_exportada"), "Vertido", LIME, "area")],
            CYAN,
        ),
        apex(
            "Últimos 30 días (kWh)",
            [history_serie(t("@historico"), "importada", "Importado", CYAN), history_serie(t("@historico"), "exportada", "Vertido", LIME)],
            CYAN,
            span="30d",
            span_cfg={"end": "day"},
        ),
    ]
    if price_sensor:
        js = (
            "const a = entity.attributes; const d = new Date(); d.setHours(0,0,0,0); const out = [];"
            "for (let h = 0; h < 24; h++) { const k = 'price_' + String(h).padStart(2,'0') + 'h'; if (a[k] !== undefined) out.push([d.getTime() + h*3600e3, a[k]]); }"
            "for (let h = 0; h < 24; h++) { const k = 'price_next_day_' + String(h).padStart(2,'0') + 'h'; if (a[k] !== undefined) out.push([d.getTime() + (24+h)*3600e3, a[k]]); }"
            "return out;"
        )
        charts.insert(
            0,
            apex(
                "Precio hoy y mañana (€/kWh)",
                [{"entity": price_sensor, "name": "Precio", "color": GOLD, "type": "column", "data_generator": js}],
                GOLD,
                span="48h",
                span_cfg={"start": "day"},
                extra_apex={"plotOptions": {"bar": {"columnWidth": "80%"}}},
            ),
        )
    return view(
        "Red",
        "red",
        "mdi:transmission-tower",
        [
            section([title("Red eléctrica", "Importación, vertido y potencia contratada", "mdi:transmission-tower", CYAN), *live]),
            section([title("Energía", "", "mdi:counter", CYAN), _period_tile(t), energy]),
            section(charts, span=2),
        ],
    )


# ---------------------------------------------------------------------- 3. solar


def _solar(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    if not ctx.strings and not ctx.s("solar_potencia"):
        return view(
            "Solar",
            "solar",
            "mdi:solar-power-variant",
            [
                section(
                    [
                        title("Solar", "", "mdi:solar-power-variant", AMBER),
                        _empty("Añade la potencia solar en Configurar → Solar, o cada string en «Añadir string»."),
                    ]
                )
            ],
        )
    peak = float(ctx.s("solar_pico_wp") or 0) or sum(float(s.get("peak_wp") or 0) for s in ctx.strings) or 5000
    head = [
        gauge(
            t("@potencia_solar"),
            "Producción",
            0,
            round(peak),
            AMBER,
            {"red": 0, "yellow": round(peak * 0.15), "green": round(peak * 0.45)},
            unit="W",
        ),
        tpl(
            t("@energia_solar"),
            t(MACROS + "{{ n(states('@energia_solar'), 2) }} kWh"),
            t(
                MACROS
                + "Hoy · mes {{ n(state_attr('@energia_solar','mes'), 0) }} kWh · año {{ n(state_attr('@energia_solar','ano'), 0) }} kWh"
            ),
            "mdi:solar-power-variant-outline",
            AMBER,
        ),
        tpl(
            t("@potencia_solar"),
            t(MACROS + "{{ n(state_attr('@potencia_solar','rendimiento_pct'), 0) }} %"),
            f"Rendimiento sobre {peak:.0f} Wp",
            "mdi:speedometer",
            AMBER,
        ),
        tpl(
            t("@autoconsumo"),
            t(MACROS + "{{ n(states('@autoconsumo'), 0) }} %"),
            t(MACROS + "Autoconsumo hoy · mes {{ n(state_attr('@autoconsumo','mes'), 0) }} %"),
            "mdi:home-import-outline",
            LIME,
        ),
    ]
    if ctx.s("solar_prevision_hoy"):
        fc = ctx.s("solar_prevision_hoy")
        head.append(
            tpl(
                fc,
                MACROS + "{{ n(states('" + fc + "'), 1) }} kWh",
                t(
                    MACROS
                    + "Previsión hoy · llevas el {{ n(100 * states('@energia_solar') | float(0) / ([states('"
                    + fc
                    + "') | float(0), 0.01] | max), 0) }} %"
                ),
                "mdi:weather-sunny-alert",
                AMBER,
            )
        )
    inverter = []
    for key, label, icon in (
        ("inversor_temperatura", "Inversor", "mdi:thermometer"),
        ("inversor_temperatura_dc", "Inversor DC", "mdi:thermometer-high"),
    ):
        if ctx.s(key):
            e = ctx.s(key)
            inverter.append(tpl(e, MACROS + "{{ n(states('" + e + "'), 1) }} °C", label, icon, ORANGE))
    for key, label in (("inversor_estado", "Estado"), ("inversor_fallo", "Fallo"), ("inversor_alarma", "Alarma")):
        if ctx.s(key):
            inverter.append(tile(ctx.s(key), label, ORANGE, "mdi:information-outline"))
    strings = []
    for s in ctx.strings:
        e = s["power"]
        sec = MACROS + "{{ n(states('" + t("@" + s["id"] + ":energia_string") + "'), 2) }} kWh hoy"
        if s.get("voltage"):
            sec += " · {{ n(states('" + s["voltage"] + "'), 0) }} V"
        if s.get("current"):
            sec += " · {{ n(states('" + s["current"] + "'), 1) }} A"
        if s.get("peak_wp"):
            sec += (
                " · {{ n(100 * states('"
                + e
                + "') | float(0) / "
                + str(float(s["peak_wp"]))
                + ", 0) }} % de "
                + f"{float(s['peak_wp']):.0f} Wp"
            )
        strings.append(tpl(e, MACROS + "{{ w(states('" + e + "')) }}", f"{s['name']} · " + sec, "mdi:solar-panel", AMBER, columns=6))
    compare = None
    if len(ctx.strings) > 1:
        compare = md(
            t(
                MACROS
                + """### <ha-icon icon="mdi:compare-horizontal"></ha-icon> Comparativa de strings (W/kWp)
{%- set ss = state_attr('@potencia_solar','strings') or [] -%}
{%- set ns = namespace(m=1) -%}{%- for s in ss %}{% if s.wp and s.w %}{% set ns.m = [ns.m, 1000 * s.w / s.wp] | max %}{% endif %}{% endfor %}
{% for s in ss %}
**{{ s.nombre }}** <font color="#8fb3c9">({{ s.grupo }})</font><br>{{ bar(1000 * (s.w or 0) / (s.wp or 1), ns.m, '#ffc400') }} {{ n(1000 * (s.w or 0) / (s.wp or 1), 0) }}
{% endfor %}"""
            ),
            AMBER,
            "full",
        )
    charts = []
    if ctx.strings:
        charts.append(
            apex(
                "Strings 24 h (W)",
                [
                    serie(s["power"], s["name"], c, "line")
                    for s, c in zip(ctx.strings, [AMBER, ORANGE, GOLD, LIME, PINK, CYAN, VIOLET, BLUE] * 4, strict=False)
                ],
                AMBER,
            )
        )
    charts.append(
        apex(
            "Producción 30 días (kWh)",
            [history_serie(t("@historico"), "solar", "Solar", AMBER)],
            AMBER,
            span="30d",
            span_cfg={"end": "day"},
        )
    )
    charts.append(
        apex(
            "Producción por meses (kWh)",
            [history_serie(t("@historico"), "solar", "Solar", AMBER, "meses")],
            AMBER,
            span="365d",
            span_cfg={"end": "month"},
        )
    )
    sections = [section([title("Paneles solares", "Producción, strings e inversor", "mdi:solar-power-variant", AMBER), *head])]
    sections.append(
        section(
            [
                title("Strings", "", "mdi:solar-panel", AMBER),
                *strings,
                *([compare] if compare else []),
                *([title("Inversor", "", "mdi:power-plug-battery", ORANGE), *inverter] if inverter else []),
            ]
        )
    )
    sections.append(section(charts, span=2))
    return view("Solar", "solar", "mdi:solar-power-variant", sections)


# ---------------------------------------------------------------------- 4. batería


def _battery(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    if not ctx.batteries:
        return view(
            "Batería",
            "bateria",
            "mdi:home-battery",
            [
                section(
                    [title("Batería", "", "mdi:home-battery", GREEN), _empty("Añade tus baterías en la integración → «Añadir batería».")]
                )
            ],
        )
    overview = [
        gauge(t("@soc_bateria"), "Carga total", 0, 100, GREEN, {"red": 0, "yellow": 20, "green": 40}, unit="%"),
        tpl(
            t("@potencia_bateria"),
            t(MACROS + "{%- set b = states('@potencia_bateria') | float(0) -%}{{ w(b | abs) }}"),
            t(
                MACROS
                + "{%- set b = states('@potencia_bateria') | float(0) -%}{{ 'Descargando' if b > 30 else 'Cargando' if b < -30 else 'En reposo' }}"
            ),
            "mdi:battery-sync",
            GREEN,
        ),
        tpl(
            t("@energia_almacenada"),
            t(MACROS + "{{ n(states('@energia_almacenada'), 1) }} kWh"),
            t(MACROS + "Almacenado de {{ n(state_attr('@potencia_bateria','capacidad_kwh'), 0) }} kWh"),
            "mdi:battery-high",
            GREEN,
        ),
        tpl(
            t("@autonomia_bateria"),
            t(MACROS + "{%- set h = states('@autonomia_bateria') | float(-1) -%}{{ (n(h, 1) ~ ' h') if h >= 0 else '—' }}"),
            "Autonomía con el consumo actual",
            "mdi:timer-sand",
            GREEN,
        ),
        tpl(
            t("@energia_bateria_carga"),
            t(MACROS + "↓ {{ n(states('@energia_bateria_carga'), 2) }} · ↑ {{ n(states('@energia_bateria_descarga'), 2) }} kWh"),
            "Cargado · descargado hoy",
            "mdi:swap-vertical-bold",
            GREEN,
            columns=12,
        ),
    ]
    sections = [section([title("Baterías", "Estado de carga, flujo y celdas", "mdi:home-battery", GREEN), *overview])]
    for b in ctx.batteries:
        cards = [
            title(b["name"], "", "mdi:battery-outline", GREEN),
            gauge(b["soc"], "SOC", 0, 100, GREEN, {"red": 0, "yellow": 20, "green": 40}, unit="%"),
        ]
        sign = "" if not b.get("positive_charge") else "-"
        cards.append(
            tpl(
                b["power"],
                MACROS + "{{ w(" + sign + "(states('" + b["power"] + "') | float(0))) }}",
                "Potencia (+ descarga)",
                "mdi:flash",
                GREEN,
            )
        )
        for key, label, icon, unit, d in (
            ("voltage", "Tensión", "mdi:sine-wave", "V", 2),
            ("current", "Corriente", "mdi:current-dc", "A", 1),
            ("cycles", "Ciclos", "mdi:autorenew", "", 0),
        ):
            if b.get(key):
                e = b[key]
                cards.append(tpl(e, MACROS + "{{ n(states('" + e + "'), " + str(d) + ") }} " + unit, label, icon, GREEN))
        for e in b.get("temperatures", []):
            cards.append(
                tpl(
                    e,
                    MACROS + "{{ n(states('" + e + "'), 1) }} °C",
                    "{{ state_attr('" + e + "','friendly_name') }}",
                    "mdi:thermometer",
                    ORANGE,
                )
            )
        if b.get("cells"):
            cells = "[" + ", ".join(f"'{c}'" for c in b["cells"]) + "]"
            content = (
                MACROS
                + "{%- set cells = "
                + cells
                + " -%}"
                + "{%- set vals = cells | map('states') | map('float', 0) | list -%}"
                + "{%- set ok = vals | select('gt', 1) | list -%}"
                + "{%- set lo = ok | min if ok else 0 -%}{%- set hi = ok | max if ok else 0 -%}"
                + '\n### <ha-icon icon="mdi:view-grid"></ha-icon> Celdas · Δ {{ n((hi - lo) * 1000, 0) }} mV\n'
                + "{% for v in vals %}{%- set c = '#ff1744' if v < 3.0 or v > 3.6 else '#ffc400' if v < 3.2 or v > 3.45 else '#00e676' -%}"
                + "{%- set mark = ' ▼' if v == lo else ' ▲' if v == hi else '' -%}"
                + "`{{ '%02d' | format(loop.index) }}` {{ bar(v - 2.8, 0.85, c, 16) }} <font color=\"{{ c }}\">{{ n(v, 3) }} V{{ mark }}</font><br>\n{% endfor %}"
            )
            cards.append(md(content, GREEN, "full"))
        sections.append(section(cards))
    series = [
        serie(t("@soc_bateria"), "SOC", GREEN, "line", yaxis_id="soc"),
        serie(t("@potencia_bateria"), "Potencia", LIME, "area", yaxis_id="w"),
    ]
    sections.append(
        section(
            [
                apex(
                    "Batería 24 h",
                    series,
                    GREEN,
                    yaxis=[{"id": "soc", "min": 0, "max": 100, "decimals": 0}, {"id": "w", "opposite": True, "decimals": 0}],
                )
            ],
            span=2,
        )
    )
    return view("Batería", "bateria", "mdi:home-battery", sections)


# ---------------------------------------------------------------------- 5. consumos


def _consumption(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    head = [
        tpl(
            t("@potencia_consumo"),
            t(MACROS + "{{ w(states('@potencia_consumo')) }}"),
            t(MACROS + "Consumo total · {{ n(states('@energia_consumo'), 2) }} kWh hoy"),
            "mdi:home-lightning-bolt",
            PINK,
        ),
        tpl(
            t("@potencia_no_medida"),
            t(MACROS + "{{ w(states('@potencia_no_medida')) }}"),
            "Sin medir por ningún circuito",
            "mdi:help-circle-outline",
            VIOLET,
        ),
        _period_tile(t, PINK),
    ]
    ranking = md(
        t(
            MACROS
            + """{%- set per = states('@periodo') -%}{%- set P = """
            + PERIOD_LABELS
            + """ -%}
### <ha-icon icon="mdi:podium"></ha-icon> Ahora mismo · kWh {{ P[per] | lower }}
{%- set cs = state_attr('@potencia_consumo','circuitos') or [] -%}
{%- set top = (cs | map(attribute='w') | map('float', 0) | list + [1]) | max -%}
{% for c in cs %}
<ha-icon icon="{{ c.icono }}"></ha-icon> **{{ c.nombre }}**{% if c.padre %} <font color="#8fb3c9">⤷ {{ c.padre }}</font>{% endif %}<br>{{ bar(c.w or 0, top, '#ff4fd8') }} {{ w(c.w) }} · {{ n(c.pct, 0) }} % · {{ n(c.periodo_kwh, 2) }} kWh
{% endfor %}
{%- set nm = state_attr('@potencia_consumo','no_medido_w') -%}{% if nm is not none %}
<font color="#b388ff">◌ Sin medir: {{ w(nm) }}</font>{% endif %}"""
        ),
        PINK,
        "full",
    )
    sections = [section([title("Consumos", "Total y cada circuito por separado", "mdi:home-lightning-bolt", PINK), *head, ranking])]
    groups: dict[str, list[dict[str, Any]]] = {}
    for c in ctx.circuits:
        groups.setdefault(c["group"], []).append(c)
    for group, items in groups.items():
        cards = [title(group, "", "mdi:electric-switch", PINK)]
        for c in items:
            energy = t("@" + c["id"] + ":energia_circuito")
            cards.append(
                tpl(
                    c["power"],
                    MACROS + "{{ w(states('" + c["power"] + "')) }}",
                    MACROS
                    + c["name"]
                    + " · {{ n(states('"
                    + energy
                    + "'), 2) }} kWh hoy · {{ n(state_attr('"
                    + energy
                    + "', states('"
                    + t("@periodo")
                    + "')), 1) }} kWh periodo",
                    c["icon"],
                    PINK,
                )
            )
        sections.append(section(cards))
    if not ctx.circuits:
        sections.append(section([_empty("Añade cada circuito o aparato en la integración → «Añadir circuito».")]))
    charts = [
        apex(
            "Consumo 30 días (kWh)", [history_serie(t("@historico"), "consumo", "Consumo", PINK)], PINK, span="30d", span_cfg={"end": "day"}
        )
    ]
    if ctx.circuits:
        charts.insert(
            0,
            apex(
                "Circuitos 24 h (W)",
                [
                    serie(c["power"], c["name"], col, "area")
                    for c, col in zip(ctx.circuits, [PINK, VIOLET, ORANGE, BLUE, CYAN, LIME, GOLD, AMBER, GREEN, RED] * 5, strict=False)
                ],
                PINK,
                stacked=True,
                height=320,
            ),
        )
    sections.append(section(charts, span=2))
    return view("Consumos", "consumos", "mdi:home-lightning-bolt", sections)


# ---------------------------------------------------------------------- 6. problemas


def _problems(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    counts = md(
        t(
            """{%- set c = state_attr('@problemas','criticos') | int(0) -%}{%- set w = state_attr('@problemas','avisos') | int(0) -%}{%- set i = state_attr('@problemas','info') | int(0) -%}
| <font color="#ff1744">CRÍTICOS</font> | <font color="#ffc400">AVISOS</font> | <font color="#40c4ff">INFO</font> |
|:-:|:-:|:-:|
| <font color="#ff1744"><big><b>{{ c }}</b></big></font> | <font color="#ffc400"><big><b>{{ w }}</b></big></font> | <font color="#40c4ff"><big><b>{{ i }}</b></big></font> |

<font color="#8fb3c9">Se revisa cada 30 s. Un problema solo aparece si dura lo bastante (no salta por una lectura suelta).</font>"""
        ),
        RED,
        "full",
    )
    listing = md(
        t(
            """{%- set p = state_attr('@problemas','lista') or [] -%}
{%- if p | count == 0 -%}<ha-alert alert-type="success" title="Todo en orden">No se ha detectado ningún problema.</ha-alert>
{%- else -%}{%- for area, items in p | groupby('area') %}
### {{ area }}
{% for x in items -%}
<ha-alert alert-type="{{ 'error' if x.nivel == 'critico' else 'warning' if x.nivel == 'aviso' else 'info' }}" title="{{ x.titulo }}{{ ' ✓' if x.reconocido }}">{{ x.detalle }}<br><sub>Desde {{ as_timestamp(x.desde) | timestamp_custom('%d/%m %H:%M') }}{% if x.entidad %} · {{ x.entidad }}{% endif %}</sub></ha-alert>
{% endfor %}{%- endfor -%}{%- endif -%}"""
        ),
        RED,
        "full",
    )
    sources = [(label, entity) for label, entity in _source_list(ctx)]
    rows = "\n".join(
        "| "
        + label
        + " | {%- set s = states('"
        + e
        + "') -%}{% if s in ['unavailable','unknown'] %}<font color=\"#ff1744\">● {{ s }}</font>{% else %}<font color=\"#00e676\">●</font> {{ s }} {{ state_attr('"
        + e
        + "','unit_of_measurement') or '' }}{% endif %} |"
        for label, e in sources
    )
    health = (
        md('### <ha-icon icon="mdi:heart-pulse"></ha-icon> Estado de las fuentes\n| Fuente | Valor |\n|:--|--:|\n' + rows, CYAN, "full")
        if sources
        else None
    )
    buttons = [
        press(t("@reconocer_problemas"), "Reconocer todo", "mdi:check-all", GREEN),
        press(t("@regenerar_panel"), "Regenerar panel", "mdi:view-dashboard-edit", CYAN),
    ]
    log = {
        "type": "logbook",
        "entities": [t("@problema_critico")],
        "hours_to_show": 168,
        "card_mod": neon(RED),
        "grid_options": {"columns": "full"},
    }
    return view(
        "Problemas",
        "problemas",
        "mdi:alert-decagram",
        [
            section([title("Diagnóstico", "Problemas detectados en la instalación", "mdi:alert-decagram", RED), counts, *buttons, log]),
            section([listing], span=2),
            section([health] if health else [_empty("Sin fuentes configuradas.")]),
        ],
    )


def _source_list(ctx: PanelContext) -> list[tuple[str, str]]:
    out = []
    for key, label in (
        ("red_potencia", "Red"),
        ("consumo_potencia", "Consumo total"),
        ("solar_potencia", "Solar"),
        ("red_tension", "Tensión de red"),
        ("inversor_temperatura", "Temp. inversor"),
    ):
        if ctx.s(key):
            out.append((label, ctx.s(key)))
    out += [(s["name"], s["power"]) for s in ctx.strings]
    for b in ctx.batteries:
        out += [(f"{b['name']} SOC", b["soc"]), (f"{b['name']} potencia", b["power"])]
    out += [(c["name"], c["power"]) for c in ctx.circuits]
    out += [(z["name"], z["valve"]) for z in ctx.zones]
    return out


# ---------------------------------------------------------------------- 7. coste


BILL_TABLE = """{% set f = '@SENSOR' -%}{%- set lineas = state_attr(f, 'lineas') or [] -%}
{%- if lineas -%}
<font color="#8fb3c9">{{ as_timestamp(state_attr(f,'desde')) | timestamp_custom('%d/%m/%Y') }} – {{ as_timestamp(state_attr(f,'hasta')) | timestamp_custom('%d/%m/%Y') }} · {{ state_attr(f,'dias') }} días · {{ n(state_attr(f,'importada_kwh'), 1) }} kWh</font>

| Concepto | Cálculo | Importe |
|:--|:--|--:|
{%- for l in lineas %}
| {{ l.concepto }} | <sub>{{ l.calculo }}</sub> | {{ n(l.importe, 2) }} € |
{%- endfor %}
| **Base imponible** | | **{{ n(state_attr(f,'base_imponible'), 2) }} €** |
| IVA | {{ n(state_attr(f,'iva_porcentaje'), 0) }} % | {{ n(state_attr(f,'iva'), 2) }} € |
| <font color="#ffd740">**TOTAL**</font> | | <font color="#ffd740">**{{ n(state_attr(f,'total'), 2) }} €**</font> |
{%- if state_attr(f,'compensacion_perdida') | float(0) > 0 %}

<font color="#ffc400">⚠ {{ n(state_attr(f,'compensacion_perdida'), 2) }} € de excedentes no se compensan (superan la energía del periodo).</font>
{%- endif -%}
{%- else -%}Calculando…{%- endif -%}"""


def _cost(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    now_bill = md(
        t(
            MACROS
            + '### <ha-icon icon="mdi:receipt-text-clock"></ha-icon> Factura en curso (hasta hoy)\n'
            + BILL_TABLE.replace("@SENSOR", "@factura_actual")
        ),
        GOLD,
        "full",
    )
    end_bill = md(
        t(
            MACROS
            + '### <ha-icon icon="mdi:crystal-ball"></ha-icon> Previsión al cierre del periodo\n'
            + BILL_TABLE.replace("@SENSOR", "@prevision_factura")
        ),
        GOLD,
        "full",
    )
    nxt = md(
        t(
            MACROS
            + """### <ha-icon icon="mdi:calendar-arrow-right"></ha-icon> Próximas facturas
{%- set ms = state_attr('@prevision_factura','proximas') or [] %}
| Mes | Consumo | Importado | Vertido | Total |
|:--|--:|--:|--:|--:|
{%- for m in ms %}
| {{ m.mes }} <sub>{{ '📅' if m.fuente == 'año_anterior' else '∿' }}</sub> | {{ n(m.consumo_kwh, 0) }} kWh | {{ n(m.importada_kwh, 0) }} kWh | {{ n(m.exportada_kwh, 0) }} kWh | <font color="#ffd740">**{{ n(m.total, 2) }} €**</font> |
{%- endfor %}

<sub>∿ modelo con tus últimos 30 días y la estacionalidad solar · 📅 mismo periodo del año pasado</sub>"""
        ),
        GOLD,
        "full",
    )
    js = "return (entity.attributes.proximas || []).map(m => [new Date(m.mes + '-15T12:00:00').getTime(), m.total]);"
    forecast_chart = apex(
        "Previsión (€)",
        [{"entity": t("@prevision_factura"), "name": "Factura", "color": GOLD, "type": "column", "data_generator": js}],
        GOLD,
        span="120d",
        span_cfg={"start": "month"},
        height=220,
    )
    sim_entities = {
        "type": "entities",
        "title": "Simulador «¿y si…?»",
        "show_header_toggle": False,
        "entities": [
            {"entity": t("@sim_potencia_p1"), "name": "Potencia punta (kW, −1 = la actual)"},
            {"entity": t("@sim_potencia_p2"), "name": "Potencia valle (kW, −1 = la actual)"},
            {"entity": t("@sim_consumo"), "name": "Cambio de consumo"},
            {"entity": t("@sim_precio"), "name": "Cambio del precio"},
            {"entity": t("@sim_paneles"), "name": "Paneles extra"},
            {"entity": t("@sim_bateria"), "name": "Batería extra"},
            {"entity": t("@sim_excedentes"), "name": "Precio excedentes (−1 = el actual)"},
        ],
        "card_mod": neon(VIOLET),
        "grid_options": {"columns": "full"},
    }
    sim_result = md(
        t(
            MACROS
            + """{%- set s = state_attr('@simulacion_factura','simulada') or {} -%}{%- set b = state_attr('@simulacion_factura','base') or {} -%}
{%- set d = state_attr('@simulacion_factura','diferencia') | float(0) -%}
### <ha-icon icon="mdi:flask-outline"></ha-icon> Próxima factura ({{ s.mes or '—' }})
| | Actual | Simulada |
|:--|--:|--:|
| Potencia | {{ n(b.potencia, 2) }} € | {{ n(s.potencia, 2) }} € |
| Energía | {{ n(b.energia, 2) }} € | {{ n(s.energia, 2) }} € |
| Compensación | −{{ n(b.compensacion, 2) }} € | −{{ n(s.compensacion, 2) }} € |
| **Total** | **{{ n(b.total, 2) }} €** | **{{ n(s.total, 2) }} €** |

<big><font color="{{ '#00e676' if d < 0 else '#ff1744' if d > 0 else '#8fb3c9' }}">{{ '▼ Ahorras ' if d < 0 else '▲ Pagas ' if d > 0 else '= ' }}{{ n(d | abs, 2) }} €/mes · {{ n((state_attr('@simulacion_factura','diferencia_anual') | float(0)) | abs, 0) }} €/año</font></big>"""
        ),
        VIOLET,
        "full",
    )
    savings = md(
        t(
            MACROS
            + """### <ha-icon icon="mdi:piggy-bank-outline"></ha-icon> Lo que te ahorra el sol
| Hoy | Mes | Año | Total |
|--:|--:|--:|--:|
| {{ n(state_attr('@ahorro_solar','hoy'), 2) }} € | {{ n(state_attr('@ahorro_solar','mes'), 2) }} € | **{{ n(state_attr('@ahorro_solar','ano'), 2) }} €** | {{ n(state_attr('@ahorro_solar','total'), 2) }} € |"""
        ),
        LIME,
        "full",
    )
    daily = apex(
        "Coste diario 30 días (€)",
        [history_serie(t("@historico"), "coste", "Energía", GOLD), history_serie(t("@historico"), "compensacion", "Compensación", LIME)],
        GOLD,
        span="30d",
        span_cfg={"end": "day"},
    )
    monthly = apex(
        "Energía por meses (€)",
        [
            history_serie(t("@historico"), "coste_energia", "Energía", GOLD, "meses"),
            history_serie(t("@historico"), "compensacion", "Compensación", LIME, "meses"),
        ],
        GOLD,
        span="365d",
        span_cfg={"end": "month"},
    )
    return view(
        "Coste",
        "coste",
        "mdi:cash-multiple",
        [
            section([title("Coste energético", "Factura en curso, previsiones y simulador", "mdi:cash-multiple", GOLD), now_bill]),
            section([end_bill, nxt, forecast_chart]),
            section([sim_entities, sim_result]),
            section([savings, daily, monthly]),
        ],
    )


# ---------------------------------------------------------------------- 8. co2


def _co2(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    hero = md(
        t(
            MACROS
            + """{%- set a = state_attr('@co2_evitado','total') or {} -%}
<center>
<font color="#8fb3c9">CO₂ EVITADO DESDE QUE MIDES</font>

# <font color="#c6ff00">{{ n(a.evitado_kg / 1000 if a.evitado_kg | float(0) >= 1000 else a.evitado_kg, 2 if a.evitado_kg | float(0) >= 1000 else 1) }} {{ 't' if a.evitado_kg | float(0) >= 1000 else 'kg' }}</font>

🌳 **{{ n(a.arboles, 1) }}** árboles absorbiendo un año · 🚗 **{{ n(a.km_coche, 0) }}** km en coche
</center>"""
        ),
        LIME,
        "full",
    )
    table = md(
        t(
            MACROS
            + """### <ha-icon icon="mdi:leaf"></ha-icon> Balance de carbono (kg CO₂)
| | Hoy | Mes | Año | Total |
|:--|--:|--:|--:|--:|
{%- set A = state_attr('@co2_evitado','hoy') or {} -%}{%- set B = state_attr('@co2_evitado','mes') or {} -%}{%- set C = state_attr('@co2_evitado','ano') or {} -%}{%- set D = state_attr('@co2_evitado','total') or {} %}
| <font color="#c6ff00">Evitado (solar)</font> | {{ n(A.evitado_kg, 1) }} | {{ n(B.evitado_kg, 1) }} | {{ n(C.evitado_kg, 0) }} | **{{ n(D.evitado_kg, 0) }}** |
| <font color="#00e5ff">Red eléctrica</font> | {{ n(A.red_kg, 1) }} | {{ n(B.red_kg, 1) }} | {{ n(C.red_kg, 0) }} | {{ n(D.red_kg, 0) }} |
| <font color="#b388ff">Gas</font> | {{ n(A.gas_kg, 1) }} | {{ n(B.gas_kg, 1) }} | {{ n(C.gas_kg, 0) }} | {{ n(D.gas_kg, 0) }} |
| **Huella neta** | {{ n(A.neto_kg, 1) }} | {{ n(B.neto_kg, 1) }} | {{ n(C.neto_kg, 0) }} | **{{ n(D.neto_kg, 0) }}** |

<sub>Red: {{ n(state_attr('@co2_evitado','factor_red_kg_kwh'), 3) }} kg CO₂/kWh. Configurable en Configurar → CO₂ (o un sensor de intensidad en vivo).</sub>"""
        ),
        LIME,
        "full",
    )
    gauges = [
        gauge(t("@autosuficiencia"), "Autosuficiencia hoy", 0, 100, LIME, {"red": 0, "yellow": 40, "green": 70}, unit="%"),
        gauge(t("@autoconsumo"), "Autoconsumo hoy", 0, 100, LIME, {"red": 0, "yellow": 40, "green": 70}, unit="%"),
    ]
    year = md(
        t(
            MACROS
            + """{%- set m = state_attr('@autosuficiencia','mes') | float(0) -%}{%- set y = state_attr('@autosuficiencia','ano') | float(0) -%}
### <ha-icon icon="mdi:shield-sun"></ha-icon> Independencia energética
Este mes {{ bar(m, 100, '#c6ff00') }} **{{ n(m, 0) }} %**<br>
Este año {{ bar(y, 100, '#c6ff00') }} **{{ n(y, 0) }} %**"""
        ),
        LIME,
        "full",
    )
    chart = apex(
        "CO₂ por meses (kg)",
        [
            history_serie(t("@historico"), "co2_evitado", "Evitado", LIME, "meses"),
            history_serie(t("@historico"), "co2_red", "Red", CYAN, "meses"),
            history_serie(t("@historico"), "co2_gas", "Gas", VIOLET, "meses"),
        ],
        LIME,
        span="365d",
        span_cfg={"end": "month"},
    )
    return view(
        "CO₂",
        "co2",
        "mdi:leaf-circle",
        [
            section(
                [title("Huella de carbono", "Lo que dejas de emitir gracias al sol", "mdi:leaf-circle", LIME), hero, *gauges, year], span=2
            ),
            section([table, chart], span=2),
        ],
    )


# ---------------------------------------------------------------------- 9. gas


def _gas(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    g = ctx.gas
    cards: list[dict[str, Any]] = [title("Gas", "Consumo y coste", "mdi:fire", VIOLET)]
    if not g:
        cards.append(_empty("Instala Gas TUR (detección automática) o indica tus sensores de gas en Configurar → Gas."))
        return view("Gas", "gas", "mdi:fire", [section(cards)])
    if e := g.get("coste_hoy"):
        cards.append(tpl(e, MACROS + "{{ n(states('" + e + "'), 2) }} €", "Gasto de hoy", "mdi:fire", VIOLET))
    if e := g.get("coste_mes"):
        cards.append(tpl(e, MACROS + "{{ n(states('" + e + "'), 2) }} €", "Este mes", "mdi:calendar-month", VIOLET))
    cards.append(
        tpl(
            t("@consumo_gas"),
            t(MACROS + "{{ n(states('@consumo_gas'), 2) }} m³"),
            t(
                MACROS
                + "Hoy · {{ n((state_attr('@consumo_gas','kwh') or {}).get('hoy', 0), 1) }} kWh · mes {{ n(state_attr('@consumo_gas','mes'), 1) }} m³"
            ),
            "mdi:meter-gas",
            VIOLET,
        )
    )
    if e := g.get("caudal"):
        cards.append(tpl(e, MACROS + "{{ n(states('" + e + "'), 3) }} m³/h", "Caudal ahora", "mdi:gauge", VIOLET))
    if e := g.get("precio_kwh"):
        cards.append(tpl(e, MACROS + "{{ n(states('" + e + "'), 5) }} €/kWh", "Precio del gas", "mdi:cash", VIOLET))
    bill = []
    for key, label in (("factura", "Factura en curso"), ("prevision_factura", "Previsión de la factura")):
        if e := g.get(key):
            bill.append(tpl(e, MACROS + "{{ n(states('" + e + "'), 2) }} €", label, "mdi:receipt-text", VIOLET, columns=12))
    if "lectura" in g and "factor_conversion" in g:
        bill.append(
            {
                "type": "button",
                "name": "Abrir el panel de Gas TUR",
                "icon": "mdi:open-in-app",
                "tap_action": nav("/gas-tur"),
                "card_mod": neon(VIOLET),
                "grid_options": {"columns": 12},
            }
        )
    charts = [
        apex("Gas 30 días (m³)", [history_serie(t("@historico"), "gas_m3", "Gas", VIOLET)], VIOLET, span="30d", span_cfg={"end": "day"})
    ]
    if e := g.get("caudal"):
        charts.append(apex("Caudal 24 h (m³/h)", [serie(e, "Caudal", VIOLET, "area", group="10min")], VIOLET))
    charts.append(
        apex(
            "Gas por meses (m³)",
            [history_serie(t("@historico"), "gas_m3", "Gas", VIOLET, "meses")],
            VIOLET,
            span="365d",
            span_cfg={"end": "month"},
        )
    )
    return view(
        "Gas", "gas", "mdi:fire", [section(cards), section(bill or [_empty("Sin datos de factura de gas.")]), section(charts, span=2)]
    )


# ---------------------------------------------------------------------- 10. luces


def _lights(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    head = [
        tpl(
            t("@luces_encendidas"),
            t("{{ states('@luces_encendidas') }} / {{ state_attr('@luces_encendidas','total') }}"),
            t(
                "Encendidas · {{ state_attr('@luces_encendidas','interior') }} dentro · {{ state_attr('@luces_encendidas','exterior') }} fuera"
            ),
            "mdi:lightbulb-group",
            GOLD,
        ),
        tpl(t("@luces_encendidas"), t("{{ state_attr('@luces_encendidas','sin_conexion') }}"), "Sin conexión", "mdi:lan-disconnect", RED),
        press(t("@apagar_luces"), "Apagar todas", "mdi:lightbulb-group-off", GOLD, "¿Apagar todas las luces?", columns=12),
    ]
    on = md(
        t(
            """### <ha-icon icon="mdi:lightbulb-on"></ha-icon> Encendidas ahora
{%- set l = state_attr('@luces_encendidas','encendidas') or [] %}
{% if l %}{% for x in l %}<font color="#ffd740">●</font> {{ x.nombre }}<br>{% endfor %}{% else %}<font color="#8fb3c9">Todas apagadas</font>{% endif %}"""
        ),
        GOLD,
        "full",
    )

    def cards(items: list[Light]) -> list[dict[str, Any]]:
        out = []
        for light in items:
            features = [{"type": "light-brightness"}] if light.dimmable else None
            out.append(tile(light.entity, light.name, GOLD, features=features, columns=6))
        return out

    inside = [li for li in ctx.lights if not li.outdoor]
    outside = [li for li in ctx.lights if li.outdoor]
    sections = [section([title("Iluminación", "Todas las luces de la casa", "mdi:lightbulb-group", GOLD), *head, on])]
    if inside:
        sections.append(section([title("Interior", "", "mdi:home-lightbulb", GOLD), *cards(inside)]))
    if outside:
        sections.append(section([title("Exterior", "", "mdi:outdoor-lamp", GOLD), *cards(outside)]))
    if not ctx.lights:
        sections.append(section([_empty("No hay luces. Si las añades a Home Assistant, pulsa «Regenerar panel».")]))
    return view("Luces", "luces", "mdi:lightbulb-group", sections)


# ---------------------------------------------------------------------- 11. temperaturas


def _climate(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    head = [
        tpl(
            t("@temperatura_interior"),
            t(MACROS + "{{ n(states('@temperatura_interior'), 1) }} °C"),
            t(
                MACROS
                + "Media interior · ▲ {{ n(state_attr('@temperatura_interior','maxima'), 1) }} {{ state_attr('@temperatura_interior','maxima_nombre') }} · ▼ {{ n(state_attr('@temperatura_interior','minima'), 1) }} {{ state_attr('@temperatura_interior','minima_nombre') }}"
            ),
            "mdi:home-thermometer",
            ORANGE,
            columns=12,
        ),
        tpl(t("@humedad_interior"), t(MACROS + "{{ n(states('@humedad_interior'), 0) }} %"), "Humedad media", "mdi:water-percent", BLUE),
    ]
    if out := ctx.s("temperatura_exterior"):
        expr = "state_attr('" + out + "','temperature')" if out.startswith("weather.") else "states('" + out + "')"
        head.append(tpl(out, MACROS + "{{ n(" + expr + ", 1) }} °C", "Exterior", "mdi:thermometer", BLUE))
    temps = ctx.temperatures
    heat = None
    if temps:
        listing = "[" + ", ".join(f"'{e}'" for e in temps) + "]"
        heat = md(
            MACROS
            + '### <ha-icon icon="mdi:thermometer-lines"></ha-icon> Mapa de calor\n'
            + "{%- set ns = namespace(l=[]) -%}{%- for e in "
            + listing
            + " -%}{%- set v = states(e) | float(none) -%}"
            + "{%- if v is not none -%}{%- set ns.l = ns.l + [{'n': state_attr(e,'friendly_name') or e, 'v': v}] -%}{%- endif -%}{%- endfor %}\n"
            + "{% for x in ns.l | sort(attribute='v', reverse=true) -%}"
            + "{%- set c = '#ff1744' if x.v >= 28 else '#ff9100' if x.v >= 24 else '#00e676' if x.v >= 19 else '#40c4ff' if x.v >= 14 else '#b388ff' -%}"
            + '{{ bar(x.v - 5, 30, c, 14) }} <font color="{{ c }}">**{{ n(x.v, 1) }} °C**</font> {{ x.n }}<br>\n{% endfor %}',
            ORANGE,
            "full",
        )
    sections = [section([title("Temperaturas", "Clima de cada estancia", "mdi:thermometer", ORANGE), *head, *([heat] if heat else [])])]
    if ctx.climates:
        sections.append(
            section(
                [title("Calefacción y climatización", "", "mdi:radiator", ORANGE)]
                + [{"type": "thermostat", "entity": e, "card_mod": neon(ORANGE), "grid_options": {"columns": 6}} for e in ctx.climates]
            )
        )
    charts = []
    if temps:
        charts.append(
            apex(
                "Temperaturas 24 h (°C)",
                [
                    serie(e, e.split(".", 1)[1].replace("_", " "), c, "line", group="15min")
                    for e, c in zip(
                        temps[:12], [ORANGE, RED, AMBER, GOLD, PINK, VIOLET, BLUE, CYAN, GREEN, LIME, "#ff8a80", "#82b1ff"], strict=False
                    )
                ],
                ORANGE,
                height=320,
            )
        )
    if ctx.humidities:
        charts.append(
            apex(
                "Humedad 24 h (%)",
                [
                    serie(e, e.split(".", 1)[1].replace("_", " "), c, "line", group="15min")
                    for e, c in zip(ctx.humidities[:8], [BLUE, CYAN, VIOLET, GREEN, LIME, PINK, GOLD, ORANGE], strict=False)
                ],
                BLUE,
            )
        )
    if charts:
        sections.append(section(charts, span=2))
    return view("Temperaturas", "clima", "mdi:thermometer", sections)


# ---------------------------------------------------------------------- 12. riego


def _irrigation(ctx: PanelContext, t: Templates) -> dict[str, Any]:
    if not ctx.zones:
        return view(
            "Riego",
            "riego",
            "mdi:sprinkler-variant",
            [
                section(
                    [
                        title("Riego", "", "mdi:sprinkler-variant", BLUE),
                        _empty("Añade cada zona en la integración → «Añadir zona de riego»."),
                    ]
                )
            ],
        )
    head = [
        tile(t("@riego_activo"), "Riego", BLUE, "mdi:sprinkler-variant"),
        tile(t("@omitir_si_llueve"), "Omitir si llueve", BLUE, "mdi:weather-pouring"),
        press(t("@parar_riego"), "Parar todo", "mdi:water-off", RED, "¿Cerrar todas las válvulas?", columns=12),
    ]
    if rain := ctx.s("lluvia_sensor"):
        head.insert(1, tile(rain, "Lluvia", BLUE, "mdi:weather-rainy"))
    sections = [section([title("Riego", "Zonas, humedad del suelo y lluvia", "mdi:sprinkler-variant", BLUE), *head])]
    for z in ctx.zones:
        remaining = t("@" + z["id"] + ":riego_restante")
        cards = [
            title(z["name"], "", "mdi:sprinkler", BLUE),
            tile(z["valve"], "Válvula", BLUE, "mdi:valve"),
            press(t("@" + z["id"] + ":regar"), "Regar", "mdi:sprinkler", BLUE),
            tile(
                t("@" + z["id"] + ":minutos_riego"),
                "Minutos",
                BLUE,
                "mdi:timer-cog-outline",
                [{"type": "numeric-input", "style": "slider"}],
                columns=12,
            ),
            tpl(
                remaining,
                "{%- set r = states('"
                + remaining
                + "') | float(0) -%}{{ ('Quedan ' ~ (r | round(0) | int) ~ ' min') if r > 0 else 'Parada' }}",
                "{%- set u = state_attr('"
                + remaining
                + "','ultimo_riego') -%}Último riego: {{ as_timestamp(u) | timestamp_custom('%d/%m %H:%M') if u else '—' }}{% if state_attr('"
                + remaining
                + "','ultimo_riego_minutos') %} ({{ state_attr('"
                + remaining
                + "','ultimo_riego_minutos') }} min){% endif %}",
                "mdi:timer-sand",
                BLUE,
                columns=12,
            ),
        ]
        if z.get("soil"):
            cards.append(gauge(z["soil"], "Humedad del suelo", 0, 100, BLUE, {"red": 0, "yellow": 20, "green": 35}, unit="%", columns=12))
        sections.append(section(cards))
    soils = [z for z in ctx.zones if z.get("soil")]
    if soils:
        sections.append(
            section(
                [
                    apex(
                        "Humedad del suelo 7 días (%)",
                        [
                            serie(z["soil"], z["name"], c, "line", group="1h")
                            for z, c in zip(soils, [BLUE, CYAN, GREEN, LIME, VIOLET, PINK], strict=False)
                        ],
                        BLUE,
                        span="7d",
                    )
                ],
                span=2,
            )
        )
    return view("Riego", "riego", "mdi:sprinkler-variant", sections)
