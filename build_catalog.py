"""
Збірка повного каталогу з усіх 11 виробників
"""
from datetime import date

from schemas.catalog import Catalog
from catalog.cofem import COFEM
from catalog.tiras import TIRAS
from catalog.omega import OMEGA
from catalog.varta import VARTA
from catalog.placeholders import PLACEHOLDERS


CATALOG = Catalog(
    catalog_version="0.1.0",
    last_updated=date(2026, 5, 11),
    manufacturers=[TIRAS, OMEGA, VARTA, COFEM] + PLACEHOLDERS,
)


def export_to_json(path: str) -> None:
    """Експорт каталогу в JSON-файл"""
    import json
    
    with open(path, "w", encoding="utf-8") as f:
        # model_dump_json() з Pydantic дає валідний JSON
        f.write(CATALOG.model_dump_json(indent=2))


if __name__ == "__main__":
    # При запуску: експорт у JSON + звіт
    import json
    
    print("=" * 70)
    print("FIRECOMPARE — Catalog Build Report")
    print("=" * 70)
    print(f"Каталог: v{CATALOG.catalog_version} ({CATALOG.last_updated})")
    print(f"Виробників: {len(CATALOG.manufacturers)}")
    print()
    
    print("Стан повноти даних:")
    print("-" * 70)
    overall = CATALOG.overall_completeness()
    for key, value in overall.items():
        print(f"  {key}: {value}")
    print()
    
    print("Деталі по виробниках:")
    print("-" * 70)
    print(f"{'ID':<12} {'Назва':<22} {'Статус':<14} {'Панелі':>7} {'Детект.':>8} {'I/O':>5}")
    for mfr in CATALOG.manufacturers:
        r = mfr.completeness_report()
        print(
            f"{mfr.manufacturer_id:<12} {mfr.name_ua:<22} "
            f"{r['data_status']:<14} "
            f"{r['panels_count']:>7} {r['detectors_count']:>8} {r['io_modules_count']:>5}"
        )
    print()
    
    # Експорт
    output_path = "/home/claude/firecompare/catalog_v01.json"
    export_to_json(output_path)
    print(f"Каталог експортовано: {output_path}")
    
    # Розмір файлу
    import os
    size_kb = os.path.getsize(output_path) / 1024
    print(f"Розмір файлу: {size_kb:.1f} КБ")
