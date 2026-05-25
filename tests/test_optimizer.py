"""Тести оптимізатора підбору ППКП (Блок B, принцип #5 — поділ на підсистеми)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_catalog import CATALOG
from engine.loop_allocation import optimize_panels_for_manufacturer


def _panels(mid):
    return next(m for m in CATALOG.manufacturers if m.manufacturer_id == mid).panels


def test_nobody_excluded():
    """Принцип #5: кожен виробник реалізує об'єкт (можливо кількома приладами)."""
    for mid in ["cofem", "tiras", "omega", "varta"]:
        best = optimize_panels_for_manufacturer(600, 60, _panels(mid))
        assert best.get("feasible"), f"{mid} має бути feasible"
        assert best["units"] >= 1
        assert best["total_panel_price_uah"] > 0
    print("✓ test_nobody_excluded")


def test_cheapest_chosen():
    """Оптимізатор обирає найдешевшу конфігурацію серед кандидатів."""
    best = optimize_panels_for_manufacturer(600, 60, _panels("cofem"))
    all_c = best["all_candidates"]
    # best має бути з мінімальною загальною ціною
    assert best["total_panel_price_uah"] == min(c["total_panel_price_uah"] for c in all_c)
    print("✓ test_cheapest_chosen")


def test_multi_panel_split():
    """Великий об'єкт → кілька приладів (поділ на підсистеми)."""
    # 2000 детекторів — жоден малий прилад не вмістить одним
    best = optimize_panels_for_manufacturer(2000, 100, _panels("omega"))
    assert best["feasible"]
    assert best["units"] >= 2, "великий об'єкт потребує кількох приладів Омега"
    print("✓ test_multi_panel_split")


def test_small_object_single_panel():
    """Малий об'єкт → один прилад."""
    best = optimize_panels_for_manufacturer(50, 5, _panels("cofem"))
    assert best["feasible"]
    assert best["units"] == 1
    print("✓ test_small_object_single_panel")




def test_addressable_class_filter():
    """Адресні й безадресні порівнюються окремо (не змішуються)."""
    t = _panels("tiras")
    addr = optimize_panels_for_manufacturer(600, 60, t, is_addressable=True)
    nonaddr = optimize_panels_for_manufacturer(600, 60, t, is_addressable=False)
    # Адресна має обрати адресну модель (PRIME A)
    assert "PRIME A" in addr["model_name"]
    # Безадресна — зональну (PRIME S/M/L/XL)
    assert "PRIME A" not in nonaddr["model_name"]
    print("✓ test_addressable_class_filter")


if __name__ == "__main__":
    test_nobody_excluded()
    test_cheapest_chosen()
    test_multi_panel_split()
    test_small_object_single_panel()
    test_addressable_class_filter()
    print("\nAll optimizer tests passed ✓")
