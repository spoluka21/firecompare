"""Тести роздільного підрахунку шлейфів (Блок A алгоритму ППКП)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_catalog import CATALOG
from engine.loop_allocation import (
    total_loops_needed, loops_for_relays, loops_for_detectors,
    compute_loop_requirement,
)

cofem = next(m for m in CATALOG.manufacturers if m.manufacturer_id == "cofem")
_panels = {p.panel_id: p for p in cofem.panels}


def test_relay_per_loop():
    """Onyx: 64 релейних/шлейф → 60 релейних = 1 вогнестійкий шлейф"""
    onyx = _panels["cofem_onyx_1"]
    n, _ = loops_for_relays(60, onyx)
    assert n == 1
    # Quartz: 16/шлейф → 60 релейних = 4 шлейфи
    quartz = _panels["cofem_quartz_1"]
    n2, _ = loops_for_relays(60, quartz)
    assert n2 == 4
    print("✓ test_relay_per_loop")


def test_relay_per_panel_lyon():
    """Lyon Remote: релейні на прилад → 60 релейних = 1 вогнестійкий шлейф"""
    lyon = _panels["cofem_lyon_3"]
    n, note = loops_for_relays(60, lyon)
    assert n == 1
    assert "прилад" in note
    print("✓ test_relay_per_panel_lyon")


def test_detector_loops():
    """600 детекторів / 226 на шлейф (Onyx) = 3 звичайні шлейфи"""
    onyx = _panels["cofem_onyx_1"]
    assert loops_for_detectors(600, onyx) == 3
    # Rubí 64/шлейф → 10 шлейфів
    rubi = _panels["cofem_rubi"]
    assert loops_for_detectors(600, rubi) == 10
    print("✓ test_detector_loops")


def test_total_loops_feasibility():
    """600+60: Lyon Remote 4 шлейфи вміщує (3 звич + 1 вогнест), 3-шлейфовий ні"""
    lyon4 = _panels["cofem_lyon_4"]
    r4 = total_loops_needed(600, 60, lyon4)
    assert r4["total_loops"] == 4
    assert r4["feasible_single_panel"] is True
    
    lyon3 = _panels["cofem_lyon_3"]
    r3 = total_loops_needed(600, 60, lyon3)
    assert r3["feasible_single_panel"] is False  # 4 > 3
    print("✓ test_total_loops_feasibility")


def test_cable_calculation():
    """Кабель: звичайний 10м/пристрій, вогнестійкий 35м/сигнал"""
    req = compute_loop_requirement(addressable_devices=100, relay_devices=20, fire_resistant_signals=30)
    assert req.normal_cable_m == 1000.0  # 100 × 10
    assert req.fire_resistant_cable_m == 1050.0  # 30 × 35
    print("✓ test_cable_calculation")


if __name__ == "__main__":
    test_relay_per_loop()
    test_relay_per_panel_lyon()
    test_detector_loops()
    test_total_loops_feasibility()
    test_cable_calculation()
    print("\nAll loop allocation tests passed ✓")
