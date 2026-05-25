"""
Роздільний підрахунок шлейфів і кабелю (Блок A алгоритму підбору ППКП).

Ключова ідея (за специфікацією замовника):
- ДЕТЕКТОРИ йдуть на ЗВИЧАЙНИХ шлейфах (звичайний сигнальний кабель).
- РЕЛЕЙНІ/ІНЖЕНЕРНІ компоненти йдуть на ВОГНЕСТІЙКИХ шлейфах (вогнестійкий кабель,
  суттєво дорожчий).
Ці дві групи шлейфів РОЗДІЛЬНІ, бо потребують різного кабелю.

Кабель:
- Звичайний сигнальний: ~10 м на один адресний пристрій (детектор/МСР/оповіщувач).
- Вогнестійкий: ~35 м на один інженерний сигнал.

Релейні ліміти панелі:
- relay_limit_scope="per_loop"  → релейні діляться на петлі (ceil(relay / limit))
- relay_limit_scope="per_panel" → релейні обмежені на весь прилад (не множать шлейфи)
- None → консервативна оцінка: релейні займають загальну ємність devices_per_loop
"""
import math
from typing import Optional

from pydantic import BaseModel, Field

from schemas.catalog import Panel


# Метраж кабелю (узгоджено з замовником)
NORMAL_CABLE_M_PER_DEVICE = 10.0  # звичайний сигнальний, м на адресний пристрій
FIRE_RESISTANT_CABLE_M_PER_SIGNAL = 35.0  # вогнестійкий, м на інженерний сигнал


class LoopRequirement(BaseModel):
    """Потреба у шлейфах і кабелі — без прив'язки до виробника"""
    # Адресні пристрої на звичайних шлейфах
    addressable_devices: int = Field(ge=0)  # детектори + МСР + оповіщувачі
    # Релейні/інженерні компоненти на вогнестійких шлейфах
    relay_devices: int = Field(ge=0)
    # Кабель
    normal_cable_m: float = Field(ge=0, default=0.0)
    fire_resistant_cable_m: float = Field(ge=0, default=0.0)


def compute_loop_requirement(
    addressable_devices: int,
    relay_devices: int,
    fire_resistant_signals: int,
) -> LoopRequirement:
    """
    Розраховує потребу в кабелі.
    
    addressable_devices — детектори + МСР + оповіщувачі (звичайні шлейфи).
    relay_devices — кількість релейних/інженерних компонентів (вогнестійкі шлейфи).
    fire_resistant_signals — кількість інженерних сигналів (I/O) для метражу
      вогнестійкого кабелю (може відрізнятися від relay_devices, бо один компонент
      може давати кілька сигналів).
    """
    normal_cable = addressable_devices * NORMAL_CABLE_M_PER_DEVICE
    frc = fire_resistant_signals * FIRE_RESISTANT_CABLE_M_PER_SIGNAL
    return LoopRequirement(
        addressable_devices=addressable_devices,
        relay_devices=relay_devices,
        normal_cable_m=round(normal_cable, 1),
        fire_resistant_cable_m=round(frc, 1),
    )


def loops_for_detectors(detectors: int, panel: Panel) -> int:
    """Скільки звичайних шлейфів треба для детекторів на цій панелі."""
    if detectors <= 0:
        return 0
    return math.ceil(detectors / panel.devices_per_loop)


def loops_for_relays(relays: int, panel: Panel) -> tuple[int, str]:
    """
    Скільки вогнестійких шлейфів треба для релейних компонентів на цій панелі.
    
    Повертає (кількість_шлейфів, пояснення).
    Логіка залежить від relay_limit_scope панелі.
    """
    if relays <= 0:
        return 0, "релейних компонентів немає"
    
    scope = panel.relay_limit_scope
    limit = panel.relay_devices_limit
    
    if scope == "per_panel":
        # Релейні обмежені на весь прилад — НЕ множать шлейфи.
        # Потрібен щонайменше 1 вогнестійкий шлейф, якщо релейні взагалі є.
        if limit is not None and relays > limit:
            # Перевищення ліміту приладу — позначаємо (потрібен ще прилад)
            return 1, (
                f"релейні на прилад (ліміт {limit}); потреба {relays} перевищує — "
                f"знадобиться додатковий прилад"
            )
        return 1, f"релейні на прилад (до {limit}) — 1 вогнестійкий шлейф"
    
    if scope == "per_loop" and limit:
        n = math.ceil(relays / limit)
        return n, f"{relays} релейних / {limit} на шлейф = {n} вогнестійких шлейфів"
    
    if scope == "shared":
        # Релейні ділять спільну адресну ємність з детекторами, але фізично йдуть
        # окремим вогнестійким шлейфом (різний кабель). Ємність вогнестійкого шлейфа
        # = загальна ємність адрес шлейфа.
        n = math.ceil(relays / panel.devices_per_loop)
        return n, (
            f"{relays} релейних (спільна адресна ємність {panel.devices_per_loop}/шлейф) "
            f"= {n} вогнестійких шлейфів"
        )
    
    # Консервативна оцінка: релейний ліміт невідомий → загальна ємність шлейфа
    n = math.ceil(relays / panel.devices_per_loop)
    return n, (
        f"релейний ліміт невідомий — оцінка за загальною ємністю "
        f"({relays} / {panel.devices_per_loop} = {n} шлейфів)"
    )


def total_loops_needed(detectors: int, relays: int, panel: Panel) -> dict:
    """
    Повна потреба у шлейфах для панелі: звичайні (детектори) + вогнестійкі (релейні).
    
    Повертає dict з деталізацією — основа для оптимізатора підбору ППКП (кроки 4-7).
    """
    normal = loops_for_detectors(detectors, panel)
    fire, fire_note = loops_for_relays(relays, panel)
    total = normal + fire
    
    feasible = total <= panel.max_loops
    
    return {
        "panel_id": panel.panel_id,
        "model_name": panel.model_name,
        "normal_loops": normal,
        "fire_resistant_loops": fire,
        "total_loops": total,
        "panel_max_loops": panel.max_loops,
        "feasible_single_panel": feasible,
        "fire_note": fire_note,
        "price_uah": panel.price_uah_no_vat or 0.0,
    }


def optimize_panels_for_manufacturer(
    detectors: int,
    relays: int,
    panels: list[Panel],
    is_addressable: Optional[bool] = None,
) -> dict:
    """
    Оптимізатор підбору ППКП для одного виробника (Блок B, кроки 4-7).
    
    Принцип #5: будь-яку систему можна реалізувати на обладнанні будь-якого
    виробника — за потреби поділивши на кілька приладів (підсистем). Ніхто не
    «вибуває». Питання лише в КІЛЬКОСТІ приладів (ціна) та ефективності.
    
    is_addressable: якщо задано (True/False) — порівнюються ЛИШЕ панелі того класу
    (адресні з адресними, безадресні з безадресними). Адресні й безадресні —
    різні класи систем, їх не порівнюють між собою. None = без фільтра.
    
    Логіка:
      1. Рахуємо потрібну кількість шлейфів (звичайні + вогнестійкі).
      2. Для кожної моделі ППКП визначаємо, скільки таких приладів треба, щоб
         покрити і адреси, і шлейфи (з поділом на підсистеми за потреби).
      3. Вартість = кількість приладів × ціна моделі.
      4. Обираємо НАЙДЕШЕВШУ конфігурацію серед усіх моделей виробника.
    
    Повертає dict з оптимальною конфігурацією.
    """
    if not panels:
        return {"feasible": False, "reason": "немає панелей виробника"}
    
    # Фільтр за класом системи (адресна / безадресна)
    if is_addressable is not None:
        panels = [p for p in panels if getattr(p, "is_addressable", True) == is_addressable]
        if not panels:
            cls = "адресних" if is_addressable else "безадресних"
            return {"feasible": False, "reason": f"немає {cls} ППКП у цього виробника"}
    
    candidates = []
    
    for panel in panels:
        cap_addr = panel.max_total_devices  # макс адрес на один прилад
        cap_loops = panel.max_loops
        dev_per_loop = panel.devices_per_loop
        
        if cap_addr <= 0 or dev_per_loop <= 0:
            continue
        
        # Скільки шлейфів треба загалом (звичайні для детекторів + вогнестійкі для релейних)
        normal_loops = math.ceil(detectors / dev_per_loop) if detectors else 0
        fire_loops_per_unit, _ = loops_for_relays(relays, panel)
        # Загальна потреба у шлейфах (фізично роздільних через кабель)
        total_loops_need = normal_loops + (fire_loops_per_unit if relays else 0)
        
        # Скільки приладів треба, щоб покрити:
        #  (а) за адресами: всі адресні + релейні (релейні теж займають адреси, окрім
        #      Cofem per_panel, де релейні окремо — але для простоти рахуємо адреси разом)
        total_addresses = detectors + relays
        units_by_addr = math.ceil(total_addresses / cap_addr)
        #  (б) за шлейфами
        units_by_loops = math.ceil(total_loops_need / cap_loops) if cap_loops else 1
        
        units = max(units_by_addr, units_by_loops, 1)
        
        price = panel.price_uah_no_vat or 0.0
        if price <= 0:
            continue
        
        total_price = units * price
        
        candidates.append({
            "panel_id": panel.panel_id,
            "model_name": panel.model_name,
            "units": units,
            "unit_price_uah": price,
            "total_panel_price_uah": total_price,
            "normal_loops": normal_loops,
            "fire_resistant_loops": fire_loops_per_unit if relays else 0,
            "total_loops_needed": total_loops_need,
            "max_loops_per_unit": cap_loops,
            "max_addr_per_unit": cap_addr,
            "limiting_factor": "адреси" if units_by_addr >= units_by_loops else "шлейфи",
        })
    
    if not candidates:
        return {"feasible": False, "reason": "немає панелей з цінами"}
    
    # Найдешевша конфігурація (кроки 6-7: порівнюємо загальну вартість приладів)
    best = min(candidates, key=lambda c: c["total_panel_price_uah"])
    best["feasible"] = True
    best["all_candidates"] = sorted(candidates, key=lambda c: c["total_panel_price_uah"])
    return best
