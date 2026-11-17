"""Detector de colisiones eBUS (ebusd ↔ Tado) y pruebas de convivencia."""

from custom_components.centro_control.convivencia import CRIT_PER_HOUR, CUT_LONG, HOUR, BusMonitor, verdict

T0 = 1_000_000.0


def flap(mon: BusMonitor, start: float, length: float = 20.0) -> None:
    mon.signal("off", start)
    mon.signal("on", start + length)


def test_cuts_are_counted_with_their_duration():
    mon = BusMonitor()
    flap(mon, T0, 30)
    flap(mon, T0 + 600, 10)
    hour = mon.window(T0 + 900, HOUR)
    assert hour == {"cortes": 2, "sin_senal_s": 40, "reinicios": 0, "tado_cortes": 0, "tado_coinciden": 0}
    assert mon.level(T0 + 900) == "aviso"


def test_repeated_signal_off_does_not_count_twice():
    mon = BusMonitor()
    mon.signal("off", T0)
    mon.signal("off", T0 + 5)
    assert mon.window(T0 + 10, HOUR)["cortes"] == 1


def test_open_cut_counts_until_now_and_turns_critical():
    mon = BusMonitor()
    mon.signal("off", T0)
    assert mon.current_cut(T0 + 60) == 60
    assert mon.level(T0 + 60) == "aviso"
    assert mon.level(T0 + CUT_LONG + 1) == "critico"
    ids = {p.id for p in mon.problems(T0 + CUT_LONG + 1)}
    assert "ebus_sin_senal" in ids


def test_many_cuts_in_an_hour_are_critical_and_old_ones_drop_out():
    mon = BusMonitor()
    for i in range(CRIT_PER_HOUR):
        flap(mon, T0 + i * 300)
    assert mon.level(T0 + 1000) == "critico"
    problems = mon.problems(T0 + 1000)
    assert [p.id for p in problems] == ["ebus_colisiones"] and problems[0].level == "critico"
    assert mon.problems(T0 + 2 * HOUR) == []
    assert mon.window(T0 + 2 * HOUR, 24 * HOUR)["cortes"] == CRIT_PER_HOUR


def test_ebusd_stopping_closes_the_cut_and_is_not_a_collision():
    mon = BusMonitor()
    mon.signal("off", T0)
    mon.signal("unavailable", T0 + 40)
    assert mon.cut_since is None
    mon.signal("unavailable", T0 + 100)
    assert mon.window(T0 + 200, HOUR)["cortes"] == 1


def test_restart_is_detected_when_uptime_goes_back():
    mon = BusMonitor()
    mon.uptime(5000, T0)
    mon.uptime(5060, T0 + 60)
    assert mon.window(T0 + 61, HOUR)["reinicios"] == 0
    mon.uptime(12, T0 + 120)
    assert mon.window(T0 + 121, HOUR)["reinicios"] == 1


def test_verdicts():
    assert verdict(0.5, 0, 0, 0, 0) == "insuficiente"
    assert verdict(3, 0, 0, 0, 0) == "convive"
    assert verdict(3, 1, 10, 0, 10) == "convive"
    assert verdict(3, 3, 30, 0, 10) == "dudoso"
    assert verdict(3, 0, 0, 1, 0) == "dudoso"
    assert verdict(3, 10, 100, 0, 20) == "no_convive"
    assert verdict(0.2, 1, 400, 0, 400) == "no_convive"  # un corte largo basta aunque sea corta


def test_trial_collects_only_its_own_events_and_saves_a_verdict():
    mon = BusMonitor()
    flap(mon, T0 - 500)  # antes de la prueba: no cuenta
    mon.start_trial("pollinterval 60", T0)
    assert mon.trial_live(T0)["cortes"] == 0
    flap(mon, T0 + 100, 15)
    mon.uptime(900, T0 + 150)
    mon.uptime(3, T0 + 200)
    done = mon.stop_trial(T0 + 3 * HOUR)
    assert done["nombre"] == "pollinterval 60"
    assert (done["cortes"], done["sin_senal_s"], done["reinicios"], done["peor_s"]) == (1, 15, 1, 15)
    assert done["veredicto"] == "dudoso" and done["horas"] == 3
    assert mon.trial is None and mon.trials == [done]
    assert mon.stop_trial(T0 + 4 * HOUR) is None


def test_trial_counts_a_cut_that_is_still_open_when_it_ends():
    mon = BusMonitor()
    mon.start_trial("a", T0)
    mon.signal("off", T0 + 10)
    done = mon.stop_trial(T0 + 3 * HOUR)
    assert done["cortes"] == 1 and done["peor_s"] == round(3 * HOUR - 10) and done["veredicto"] == "no_convive"


def test_starting_a_second_trial_saves_the_first():
    mon = BusMonitor()
    mon.start_trial("uno", T0)
    mon.start_trial("dos", T0 + 3 * HOUR)
    assert [t["nombre"] for t in mon.trials] == ["uno"] and mon.trial["nombre"] == "dos"


def test_trial_history_is_limited_and_can_be_cleared():
    mon = BusMonitor()
    for i in range(20):
        mon.start_trial(f"p{i}", T0 + i)
        mon.stop_trial(T0 + i + 1)
    assert len(mon.trials) == 12 and mon.trials[-1]["nombre"] == "p19"
    mon.clear_trials()
    assert mon.trials == []


def test_save_and_restore_roundtrip_ignores_garbage():
    mon = BusMonitor()
    flap(mon, T0)
    mon.start_trial("x", T0 + 5)
    back = BusMonitor.from_dict(mon.as_dict())
    assert back.events == mon.events and back.trial == mon.trial
    junk = BusMonitor.from_dict({"events": [1, {"t": 1, "k": "otro"}, {"t": 2, "k": "corte", "d": 1}], "trial": {"x": 1}, "trials": ["a"]})
    assert len(junk.events) == 1 and junk.trial is None and junk.trials == []
    assert BusMonitor.from_dict(None).events == []


def test_old_events_are_pruned():
    mon = BusMonitor()
    flap(mon, T0)
    mon.prune(T0 + 8 * 86400)
    assert mon.events == []


def test_report_has_what_the_panel_needs():
    mon = BusMonitor()
    flap(mon, T0, 12)
    rep = mon.report(T0 + 60)
    assert set(rep) >= {"nivel", "hora", "dia", "corte_actual_s", "ultimo_corte", "prueba", "pruebas", "eventos"}
    assert rep["ultimo_corte"] == T0 and rep["nivel"] == "aviso"


def test_tado_bridge_drop_alone_is_only_a_warning_and_not_notified_by_default():
    mon = BusMonitor()
    mon.tado("off", T0)
    mon.tado("on", T0 + 90)
    win = mon.window(T0 + 100, HOUR)
    assert (win["tado_cortes"], win["tado_coinciden"]) == (1, 0)
    problems = mon.problems(T0 + 100)
    assert [(p.id, p.level) for p in problems] == [("ebus_tado_cae", "aviso")]
    assert mon.level(T0 + 100) == "ok"


def test_tado_drop_next_to_an_ebusd_cut_is_a_confirmed_collision():
    mon = BusMonitor()
    flap(mon, T0, 20)
    mon.tado("off", T0 + 120)  # ebusd cortó hace 100 s
    assert mon.window(T0 + 130, HOUR)["tado_coinciden"] == 1
    assert mon.level(T0 + 130) == "critico"
    assert any(p.id == "ebus_tado_cae" and p.level == "critico" for p in mon.problems(T0 + 130))
    mon2 = BusMonitor()
    mon2.signal("off", T0)  # corte de ebusd aún abierto
    mon2.tado("off", T0 + 30)
    assert mon2.window(T0 + 40, HOUR)["tado_coinciden"] == 1
    far = BusMonitor()
    flap(far, T0, 20)
    far.tado("off", T0 + 5000)
    assert far.window(T0 + 5001, 10_000)["tado_coinciden"] == 0


def test_a_tado_drop_during_a_trial_means_they_do_not_coexist():
    mon = BusMonitor()
    mon.start_trial("pollinterval 30", T0)
    mon.tado("off", T0 + 600)
    mon.tado("on", T0 + 700)
    done = mon.stop_trial(T0 + 6 * HOUR)
    assert done["tado_cortes"] == 1 and done["tado_s"] == 100 and done["veredicto"] == "no_convive"
    assert verdict(6, 0, 0, 0, 0, tado_cuts=1) == "no_convive"


def test_tado_state_is_saved():
    mon = BusMonitor()
    mon.tado("off", T0)
    back = BusMonitor.from_dict(mon.as_dict())
    assert back.tado_since == T0 and back.events == mon.events
