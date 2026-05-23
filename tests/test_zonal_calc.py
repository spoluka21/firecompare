"""
Тести Блоку 2 — зональний розрахунок:
1. Усунення бага «нуль детекторів» (синтетична зона з площі)
2. Тип детектора за призначенням зони
3. Зональна інженерія: I/O + вогнестійкий кабель
4. Пропуск зон без потреби в автоматиці (§4.0)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schemas.object_state import (
    ObjectData, ObjectType, FunctionalZone, ZoneComposition, ZonePurpose,
    SuppressionType, SubdivisionType,
)
from engine.step1_bom_requirements import (
    calculate_detectors, calculate_zonal_engineering,
)


def test_zero_detectors_bug_fixed():
    """Об'єкт без зон (як від AI-агента) має давати ненульові детектори"""
    od = ObjectData(object_type=ObjectType.MIXED_USE, total_area_m2=4500, floors_above=2)
    smoke, heat, area, notes = calculate_detectors(od)
    assert smoke > 0, "Синтетична зона має дати димові детектори"
    assert area == 4500
    print(f"✓ test_zero_detectors_bug_fixed (smoke={smoke})")


def test_detector_type_by_purpose():
    """Кухня та паркінг → теплові; офіс/готель → димові"""
    od = ObjectData(
        object_type=ObjectType.MIXED_USE, total_area_m2=1000, floors_above=1,
        zones={
            "kitchen": FunctionalZone(area_m2=300, purpose=ZonePurpose.KITCHEN,
                                       subdivision_type=SubdivisionType.OPEN),
            "office": FunctionalZone(area_m2=700, purpose=ZonePurpose.OFFICE,
                                      subdivision_type=SubdivisionType.SUBDIVIDED),
        },
    )
    smoke, heat, area, notes = calculate_detectors(od)
    assert heat > 0, "Кухня має дати теплові детектори"
    assert smoke > 0, "Офіс має дати димові детектори"
    print(f"✓ test_detector_type_by_purpose (smoke={smoke}, heat={heat})")


def test_zone_without_automation_skipped():
    """Зона з requires_automation=False пропускається"""
    od = ObjectData(
        object_type=ObjectType.RESIDENTIAL_MULTI, total_area_m2=5000, floors_above=9,
        zones={
            "housing": FunctionalZone(
                area_m2=5000, purpose=ZonePurpose.RESIDENTIAL,
                requires_automation=False,
                subdivision_type=SubdivisionType.SUBDIVIDED,
            ),
        },
    )
    smoke, heat, area, notes = calculate_detectors(od)
    assert smoke == 0 and heat == 0, "Зона без автоматики не дає детекторів"
    print("✓ test_zone_without_automation_skipped")


def test_zonal_engineering_io_and_cable():
    """Зональна інженерія рахує I/O і вогнестійкий кабель"""
    od = ObjectData(
        object_type=ObjectType.MIXED_USE, total_area_m2=2000, floors_above=2,
        zones={
            "hall": FunctionalZone(
                area_m2=2000, purpose=ZonePurpose.RETAIL,
                composition=ZoneComposition(
                    smoke_dampers=3, fire_hose_cabinets=2,
                    suppression_type=SuppressionType.WATER,
                ),
            ),
        },
    )
    eng = calculate_zonal_engineering(od)
    # 3 клапани (3в+3вих) + 2 ВПВ (2вих + 6вх) + водяне (1вих + 2вх) = 11вх, 6вих
    assert eng["inputs"] == 11
    assert eng["outputs"] == 6
    assert eng["fire_resistant_cable_m"] > 0, "Має бути вогнестійкий кабель"
    print(f"✓ test_zonal_engineering_io_and_cable "
          f"(in={eng['inputs']}, out={eng['outputs']}, frc={eng['fire_resistant_cable_m']}м)")


def test_no_engineering_no_cable():
    """Зона без інженерії — нуль вогнестійкого кабелю"""
    od = ObjectData(
        object_type=ObjectType.OFFICE if hasattr(ObjectType, "OFFICE") else ObjectType.ADMINISTRATIVE,
        total_area_m2=1000, floors_above=2,
        zones={
            "office": FunctionalZone(
                area_m2=1000, purpose=ZonePurpose.OFFICE,
                composition=ZoneComposition(),  # тільки ПС+СОУЕ
            ),
        },
    )
    eng = calculate_zonal_engineering(od)
    assert eng["fire_resistant_cable_m"] == 0
    print("✓ test_no_engineering_no_cable")


if __name__ == "__main__":
    test_zero_detectors_bug_fixed()
    test_detector_type_by_purpose()
    test_zone_without_automation_skipped()
    test_zonal_engineering_io_and_cable()
    test_no_engineering_no_cable()
    print("\nAll Block 2 tests passed ✓")
