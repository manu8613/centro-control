"""Detector de colisiones en el bus eBUS (ebusd + otro maestro, p. ej. un termostato Tado).

Home Assistant no ve los errores de arbitraje del bus ni los reintentos del otro aparato.
Lo que sí ve ebusd es si **pierde la señal** del bus (`signal`) y si **se reinicia**
(`uptime` vuelve a empezar). Cuando dos maestros se pisan, lo normal es que la señal
caiga y vuelva una y otra vez: ese es el indicador que se cuenta aquí.

La lógica está separada de Home Assistant para poder probarla sin él.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .problems import Problem

HOUR = 3600.0
DAY = 86400.0
KEEP = 7 * DAY  # los eventos más antiguos se descartan
MAX_EVENTS = 800
MAX_TRIALS = 12

CUT_LONG = 300.0  # una pérdida de señal más larga que esto ya no es un parpadeo
WARN_PER_HOUR = 1  # cortes en la última hora para avisar
CRIT_PER_HOUR = 3  # cortes en la última hora para dar la alarma
MIN_TRIAL_HOURS = 2.0  # menos que esto no basta para decir que convive

VERDICTS = ("insuficiente", "convive", "dudoso", "no_convive")


def verdict(hours: float, cuts: int, no_signal_s: float, restarts: int, worst_s: float) -> str:
    """Resultado de una prueba de convivencia."""
    per_hour = cuts / hours if hours > 0 else 0.0
    if worst_s > CUT_LONG or per_hour >= CRIT_PER_HOUR:
        return "no_convive"  # esto ya se ve mal aunque la prueba sea corta
    if hours < MIN_TRIAL_HOURS:
        return "insuficiente"
    if per_hour >= WARN_PER_HOUR or restarts > 0 or cuts >= 3:
        return "dudoso"
    return "convive"


@dataclass
class BusMonitor:
    events: list[dict[str, Any]] = field(default_factory=list)  # {"t","k": corte|reinicio,"d": segundos}
    cut_since: float | None = None
    last_uptime: float | None = None
    trial: dict[str, Any] | None = None
    trials: list[dict[str, Any]] = field(default_factory=list)

    # ------------------------------------------------------------------ eventos
    def signal(self, state: str, ts: float) -> None:
        """`state` es el estado de la señal de ebusd: on, off o unavailable/unknown."""
        if state == "off":
            if self.cut_since is None:
                self.cut_since = ts
                self._add({"t": ts, "k": "corte", "d": 0.0})
                if self.trial:
                    self.trial["cortes"] += 1
        elif self.cut_since is not None:  # on, o ebusd parado: el corte se cierra
            self._close_cut(ts)

    def uptime(self, seconds: float | None, ts: float) -> None:
        """Si el tiempo de actividad de ebusd baja, ebusd se ha reiniciado."""
        if seconds is None:
            return
        if self.last_uptime is not None and seconds + 5 < self.last_uptime:
            self._add({"t": ts, "k": "reinicio", "d": 0.0})
            if self.trial:
                self.trial["reinicios"] += 1
        self.last_uptime = seconds

    def _close_cut(self, ts: float) -> None:
        start, self.cut_since = self.cut_since, None
        if start is None:
            return
        length = max(0.0, ts - start)
        for ev in reversed(self.events):
            if ev["k"] == "corte" and ev["t"] == start:
                ev["d"] = length
                break
        if self.trial:
            self.trial["sin_senal_s"] += length
            self.trial["peor_s"] = max(self.trial["peor_s"], length)

    def _add(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        if len(self.events) > MAX_EVENTS:
            del self.events[: len(self.events) - MAX_EVENTS]

    def prune(self, now: float) -> None:
        self.events = [e for e in self.events if now - e["t"] <= KEEP]

    # ------------------------------------------------------------------ resumen
    def window(self, now: float, seconds: float) -> dict[str, Any]:
        start = now - seconds
        cuts = restarts = 0
        lost = 0.0
        for e in self.events:
            end = e["t"] + (now - e["t"] if e["k"] == "corte" and e["t"] == self.cut_since else e["d"])
            if e["k"] == "corte" and end >= start:
                cuts += e["t"] >= start
                lost += end - max(e["t"], start)
            elif e["k"] == "reinicio" and e["t"] >= start:
                restarts += 1
        return {"cortes": cuts, "sin_senal_s": round(lost), "reinicios": restarts}

    def current_cut(self, now: float) -> float:
        return max(0.0, now - self.cut_since) if self.cut_since is not None else 0.0

    def level(self, now: float) -> str:
        hour = self.window(now, HOUR)["cortes"]
        if self.current_cut(now) > CUT_LONG or hour >= CRIT_PER_HOUR:
            return "critico"
        return "aviso" if hour >= WARN_PER_HOUR else "ok"

    def report(self, now: float) -> dict[str, Any]:
        last = next((e for e in reversed(self.events) if e["k"] == "corte"), None)
        return {
            "nivel": self.level(now),
            "hora": self.window(now, HOUR),
            "dia": self.window(now, DAY),
            "corte_actual_s": round(self.current_cut(now)),
            "ultimo_corte": last["t"] if last else None,
            "prueba": self.trial_live(now),
            "pruebas": self.trials,
            "eventos": [e for e in self.events if now - e["t"] <= DAY][-40:],
        }

    # ------------------------------------------------------------------ avisos
    def problems(self, now: float) -> list[Problem]:
        out: list[Problem] = []
        trial = f" Prueba en curso: «{self.trial['nombre']}»." if self.trial else ""
        if (cut := self.current_cut(now)) > CUT_LONG:
            out.append(
                Problem(
                    "ebus_sin_senal",
                    "critico",
                    "Caldera",
                    "ebusd sin señal del bus eBUS",
                    f"Lleva {round(cut / 60)} min sin señal. Si el Tado también ha perdido la caldera, "
                    f"desconecta ebusd y reinicia la caldera.{trial}",
                )
            )
        hour = self.window(now, HOUR)
        if hour["cortes"] >= WARN_PER_HOUR:
            level = "critico" if hour["cortes"] >= CRIT_PER_HOUR else "aviso"
            out.append(
                Problem(
                    "ebus_colisiones",
                    level,
                    "Caldera",
                    "Posibles colisiones en el bus eBUS",
                    f"ebusd ha perdido la señal {hour['cortes']} vez/veces en la última hora "
                    f"({hour['sin_senal_s']} s en total). Dos aparatos se están pisando en el bus.{trial}",
                )
            )
        return out

    # ------------------------------------------------------------------ pruebas
    def start_trial(self, name: str, now: float) -> dict[str, Any]:
        if self.trial:
            self.stop_trial(now)
        self.trial = {"nombre": name.strip()[:80] or "Sin nombre", "inicio": now, "cortes": 0, "sin_senal_s": 0.0, "peor_s": 0.0, "reinicios": 0}
        if self.cut_since is not None:  # ya había un corte abierto al empezar
            self.trial["cortes"] = 1
        return self.trial

    def _trial_stats(self, trial: dict[str, Any], now: float) -> dict[str, Any]:
        open_cut = self.current_cut(now)
        hours = max(0.0, now - trial["inicio"]) / HOUR
        lost = trial["sin_senal_s"] + open_cut
        worst = max(trial["peor_s"], open_cut)
        out = {
            "nombre": trial["nombre"],
            "inicio": trial["inicio"],
            "horas": round(hours, 2),
            "cortes": trial["cortes"],
            "sin_senal_s": round(lost),
            "peor_s": round(worst),
            "reinicios": trial["reinicios"],
        }
        out["veredicto"] = verdict(hours, trial["cortes"], lost, trial["reinicios"], worst)
        return out

    def trial_live(self, now: float) -> dict[str, Any] | None:
        return self._trial_stats(self.trial, now) if self.trial else None

    def stop_trial(self, now: float) -> dict[str, Any] | None:
        if not self.trial:
            return None
        done = self._trial_stats(self.trial, now)
        done["fin"] = now
        self.trial = None
        self.trials.append(done)
        del self.trials[:-MAX_TRIALS]
        return done

    def clear_trials(self) -> None:
        self.trials.clear()

    # ------------------------------------------------------------------ guardado
    def as_dict(self) -> dict[str, Any]:
        return {
            "events": self.events,
            "cut_since": self.cut_since,
            "last_uptime": self.last_uptime,
            "trial": self.trial,
            "trials": self.trials,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> BusMonitor:
        data = data or {}
        mon = cls()
        mon.events = [e for e in data.get("events", []) if isinstance(e, dict) and "t" in e and e.get("k") in ("corte", "reinicio")]
        mon.cut_since = data.get("cut_since")
        mon.last_uptime = data.get("last_uptime")
        trial = data.get("trial")
        mon.trial = trial if isinstance(trial, dict) and "inicio" in trial else None
        mon.trials = [t for t in data.get("trials", []) if isinstance(t, dict)][-MAX_TRIALS:]
        return mon
