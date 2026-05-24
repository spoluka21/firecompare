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
    
    # Консервативна оцінка: релейні займають загальну ємність шлейфа
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
