"""
КРОК 2 NPA. Алокація компонентів для NPA-архітектури

Розширення Кроку 2: якщо задано npa_architecture, алокуємо компоненти 
для кожної NPA-зони окремо, з підбором свого ППКП за 3 критеріями:
  1. Загальна адресна ємність ≥ адреси × (1 + reserve_pct)
  2. Кількість шлейфів ≥ fire_zones_count + reserve_loops + IO_loops
  3. Адреси на шлейф ≤ devices_per_loop

Це принципово відрізняється від простої алокації, де вибір був тільки 
за загальною ємністю (max_total_devices). Через це алгоритм раніше міг 
обрати Zafir 2-шлейфи замість Lyon Remote 8 — формально вміщувало, 
але фізично не дозволяло розділити систему на функціональні зони.

Reference:
- ДБН В.1.1-7:2016 — загальна архітектура СПЗ
- ДБН В.2.3-15:2017 — функціональне розділення зон у паркінгах
"""
import math
from typing import Optional

from pydantic import BaseModel, Field

from engine.step1_bom_requirements import BOMRequirements
from engine.step2_allocation import (
    Allocation, AllocatedItem, AllocationFailure,
    allocate_detectors, allocate_io_modules, allocate_mcps, allocate_sounders,
)
from schemas.catalog import Manufacturer, Panel
from schemas.object_state import NPAArchitecture, NPAZone, ObjectState


class NPAAllocation(BaseModel):
    """Алокація для однієї NPA-зони одного виробника"""
    npa_zone_id: str
    npa_zone_name: str
    
    panel_choice: Optional[AllocatedItem] = None  # обрана панель
    required_loops: int = 0
    required_addresses: int = 0
    target_addresses_with_reserve: int = 0  # з урахуванням резерву
    
    # Компоненти для цієї NPA-зони
    detectors_smoke: list[AllocatedItem] = Field(default_factory=list)
    detectors_heat: list[AllocatedItem] = Field(default_factory=list)
    io_modules: list[AllocatedItem] = Field(default_factory=list)
    mcps: list[AllocatedItem] = Field(default_factory=list)
    sounders: list[AllocatedItem] = Field(default_factory=list)
    
    addresses_used: int = 0
    capex_uah: float = 0.0
    
    failures: list[AllocationFailure] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class MultiPanelAllocation(BaseModel):
    """Повна алокація комплексу виробника з кількома ППКП"""
    manufacturer_id: str
    is_multi_panel: bool = True
    
    npa_zone_allocations: list[NPAAllocation] = Field(default_factory=list)
    
    total_panels_count: int = 0
    total_addresses_used: int = 0
    total_logical_signals: int = 0
    architectural_efficiency_pct: float = 0.0
    total_capex_uah: float = 0.0
    
    feasible: bool = True
    warnings: list[str] = Field(default_factory=list)
    failures: list[AllocationFailure] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# ПІДБІР ПАНЕЛІ ЗА 3 КРИТЕРІЯМИ (КЛЮЧОВА ЛОГІКА NPA)
# ═══════════════════════════════════════════════════════════════════


def select_panel_for_npa_zone(
    npa_zone: NPAZone,
    addresses_needed: int,
    manufacturer: Manufacturer,
    io_loops_required: int = 0,
) -> tuple[Optional[Panel], list[AllocationFailure], list[str]]:
    """
    Підбір панелі для NPA-зони за трьома критеріями.
    
    Повертає (обрана_панель, помилки, нотатки).
    
    Алгоритм:
    1. Розраховуємо required_loops = fire_zones + io_loops + reserve_loops
    2. Розраховуємо target_addresses = addresses_needed × (1 + reserve_pct)
    3. Серед усіх панелей виробника обираємо ті, що задовольняють обидва
    4. З них беремо найдешевшу
    
    Якщо нема жодної панелі, що покриває:
    - Якщо проблема в шлейфах: failure 'insufficient_loops'
    - Якщо в адресах: failure 'insufficient_addresses'
    """
    failures = []
    notes = []
    
    # Кількість шлейфів = пожежні зони (детекція) + I/O шлейфи + резерв
    required_loops = (
        npa_zone.fire_zones_count
        + io_loops_required
        + npa_zone.reserve_loops
    )
    
    # Цільова ємність з резервом
    target_addresses = math.ceil(
        addresses_needed * (1 + npa_zone.reserve_addresses_pct / 100)
    )
    
    notes.append(
        f"Вимоги до панелі: {required_loops} шлейфів "
        f"({npa_zone.fire_zones_count} зон детекції + {io_loops_required} I/O + "
        f"{npa_zone.reserve_loops} резерв), "
        f"{target_addresses} адрес (з {npa_zone.reserve_addresses_pct}% резервом)"
    )
    
    # Шукаємо панелі, що задовольняють ОБИДВА критерії
    candidates = [
        p for p in manufacturer.panels
        if p.max_loops >= required_loops
        and p.max_total_devices >= target_addresses
    ]
    
    if not candidates:
        # Діагностика — що саме не пройшло
        best_loops = max((p.max_loops for p in manufacturer.panels), default=0)
        best_addresses = max((p.max_total_devices for p in manufacturer.panels), default=0)
        
        if best_loops < required_loops:
            failures.append(AllocationFailure(
                reason_code="insufficient_loops",
                message=(
                    f"NPA-зона '{npa_zone.zone_id}' потребує {required_loops} шлейфів, "
                    f"максимум у виробника {manufacturer.manufacturer_id}: {best_loops}"
                ),
                needed=required_loops,
                available=best_loops,
            ))
        if best_addresses < target_addresses:
            failures.append(AllocationFailure(
                reason_code="insufficient_addresses",
                message=(
                    f"NPA-зона '{npa_zone.zone_id}' потребує {target_addresses} адрес, "
                    f"максимум у виробника {manufacturer.manufacturer_id}: {best_addresses}"
                ),
                needed=target_addresses,
                available=best_addresses,
            ))
        return None, failures, notes
    
    # Беремо найдешевшу з кандидатів (бо адекватна за вимогами)
    chosen = min(candidates, key=lambda p: p.price_uah_no_vat or float('inf'))
    notes.append(
        f"Обрано: {chosen.model_name} ({chosen.max_loops} шлейфів × "
        f"{chosen.devices_per_loop} = {chosen.max_total_devices} адрес, "
        f"{chosen.price_uah_no_vat:,.0f} UAH)"
    )
    
    return chosen, failures, notes


# ═══════════════════════════════════════════════════════════════════
# АЛОКАЦІЯ ОДНІЄЇ NPA-ЗОНИ ДЛЯ ВИРОБНИКА
# ═══════════════════════════════════════════════════════════════════


def allocate_npa_zone_for_manufacturer(
    npa_zone: NPAZone,
    bom: BOMRequirements,
    manufacturer: Manufacturer,
) -> NPAAllocation:
    """Повна алокація для однієї NPA-зони одного виробника"""
    
    result = NPAAllocation(
        npa_zone_id=npa_zone.zone_id,
        npa_zone_name=npa_zone.name,
    )
    
    # 1. Детектори, I/O, MCP, sounders — використовуємо існуючі функції зі Step 2
    smoke, heat, det_fail = allocate_detectors(bom, manufacturer)
    io_modules, io_fail = allocate_io_modules(bom, manufacturer)
    mcps, mcp_fail = allocate_mcps(bom, manufacturer)
    sounders, sounder_fail = allocate_sounders(bom, manufacturer)
    
    result.detectors_smoke = smoke
    result.detectors_heat = heat
    result.io_modules = io_modules
    result.mcps = mcps
    result.sounders = sounders
    
    # 2. Скільки адрес займуть компоненти
    addresses_used = sum(
        i.addresses_consumed
        for collection in [smoke, heat, io_modules, mcps, sounders]
        for i in collection
    )
    result.addresses_used = addresses_used
    result.required_addresses = addresses_used
    result.target_addresses_with_reserve = math.ceil(
        addresses_used * (1 + npa_zone.reserve_addresses_pct / 100)
    )
    
    # 3. Скільки шлейфів I/O потребує (приблизно 1 шлейф на 100 I/O модулів)
    # Це консервативна оцінка для розрахунку required_loops
    io_addresses = sum(m.addresses_consumed for m in io_modules)
    io_loops = max(0, math.ceil(io_addresses / 100)) if io_addresses > 0 else 0
    
    # 4. Підбір панелі за 3 критеріями
    chosen_panel, panel_failures, panel_notes = select_panel_for_npa_zone(
        npa_zone, addresses_used, manufacturer, io_loops
    )
    
    if chosen_panel:
        result.panel_choice = AllocatedItem(
            model_id=chosen_panel.panel_id,
            model_name=chosen_panel.model_name,
            quantity=1,
            unit_price_uah=chosen_panel.price_uah_no_vat or 0.0,
            subtotal_uah=chosen_panel.price_uah_no_vat or 0.0,
            notes=panel_notes,
        )
        result.required_loops = (
            npa_zone.fire_zones_count
            + io_loops
            + npa_zone.reserve_loops
        )
    
    # 5. Загальний CAPEX по NPA-зоні
    result.capex_uah = sum(
        i.subtotal_uah
        for collection in [
            [result.panel_choice] if result.panel_choice else [],
            smoke, heat, io_modules, mcps, sounders,
        ]
        for i in collection if i
    )
    
    # 6. Помилки
    result.failures = (
        det_fail + io_fail + mcp_fail + sounder_fail + panel_failures
    )
    
    return result


# ═══════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ — АЛОКАЦІЯ ДЛЯ ВИРОБНИКА З NPA
# ═══════════════════════════════════════════════════════════════════


def allocate_for_manufacturer_with_npa(
    state: ObjectState,
    bom_per_npa: dict[str, BOMRequirements],
    manufacturer: Manufacturer,
) -> MultiPanelAllocation:
    """
    Повна алокація для виробника з урахуванням NPA-архітектури.
    
    Якщо в state нема npa_architecture, або вона має тільки 1 зону —
    повертаємо одну MultiPanelAllocation з єдиною NPAAllocation.
    
    Якщо є кілька зон — кожна отримує власний ППКП і власні компоненти.
    """
    result = MultiPanelAllocation(manufacturer_id=manufacturer.manufacturer_id)
    
    arch = state.npa_architecture
    
    if arch is None or not arch.zones:
        # Простий режим
        bom = bom_per_npa.get("default")
        if bom is None:
            result.feasible = False
            result.warnings.append("Нема BOM для default режиму")
            return result
        
        # Створюємо «штучну» NPA-зону для уніформності
        from schemas.object_state import NPAZone, NPAZoneType
        synthetic_zone = NPAZone(
            zone_id="default",
            zone_type=NPAZoneType.MAIN,
            name="Єдиний ППКП (простий режим)",
            area_m2=state.object.total_area_m2,
            fire_zones_count=1,
            reserve_loops=0,
            reserve_addresses_pct=0,
        )
        allocation = allocate_npa_zone_for_manufacturer(synthetic_zone, bom, manufacturer)
        result.npa_zone_allocations.append(allocation)
        result.is_multi_panel = False
    else:
        # NPA режим — алокуємо кожну зону окремо
        for npa_zone in arch.zones:
            bom = bom_per_npa.get(npa_zone.zone_id)
            if bom is None:
                result.warnings.append(f"Нема BOM для NPA-зони '{npa_zone.zone_id}'")
                continue
            allocation = allocate_npa_zone_for_manufacturer(npa_zone, bom, manufacturer)
            result.npa_zone_allocations.append(allocation)
    
    # Зведені метрики
    result.total_panels_count = sum(
        1 for a in result.npa_zone_allocations if a.panel_choice
    )
    result.total_addresses_used = sum(a.addresses_used for a in result.npa_zone_allocations)
    result.total_capex_uah = sum(a.capex_uah for a in result.npa_zone_allocations)
    
    # Логічні сигнали для архітектурної ефективності
    total_logical = sum(
        bom.smoke_detectors_count + bom.heat_detectors_count +
        bom.manual_call_points_count + bom.sounders_count +
        bom.total_logical_signals()
        for bom in bom_per_npa.values()
    )
    result.total_logical_signals = total_logical
    
    if result.total_addresses_used > 0:
        result.architectural_efficiency_pct = round(
            100 * total_logical / result.total_addresses_used, 1
        )
    
    # Зведення failures
    all_failures = []
    for a in result.npa_zone_allocations:
        all_failures.extend(a.failures)
    result.failures = all_failures
    
    # Feasibility: feasible якщо для кожної NPA-зони є панель
    result.feasible = all(
        a.panel_choice is not None for a in result.npa_zone_allocations
    )
    
    if not result.feasible:
        result.warnings.append(
            f"Не для всіх NPA-зон знайдено панель — "
            f"виробник {manufacturer.manufacturer_id} не покриває архітектуру"
        )
    
    return result
