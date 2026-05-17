"""
КРОК 2. Алокація компонентів у каталозі конкретного виробника

На вході — BOMRequirements (технічні потреби) і Manufacturer (каталог).
На виході — Allocation: які саме моделі і в яких кількостях, з підрахунком 
адрес у петлях і вибором панелі.

Це місце, де працює АРХІТЕКТУРНИЙ ПОДАТОК:
- Cofem MSTAY8 = 1 адреса на 8 входів → 10 модулів на 80 входів = 10 адрес
- Омега БСА = 4 адреси на 4 входи → 20 модулів на 80 входів = 80 адрес

Логіка вибору модуля для I/O сигналів:
1. Беремо модулі ВИРОБНИКА, що підходять (input / output / combined)
2. Намагаємось максимально щільно «зашити» сигнали — менше адрес у петлі
3. Якщо немає ідеального — комбінуємо різні моделі
"""
from pydantic import BaseModel, Field

from engine.step1_bom_requirements import BOMRequirements
from schemas.catalog import (
    Detector, DetectorType, IOModule, IOModuleType, Manufacturer,
    ManualCallPoint, Panel, Sounder,
)


# ═══════════════════════════════════════════════════════════════════
# СТРУКТУРИ ДАНИХ
# ═══════════════════════════════════════════════════════════════════


class AllocatedItem(BaseModel):
    """Одна позиція в специфікації"""
    model_id: str
    model_name: str
    quantity: int
    addresses_consumed: int = 0
    unit_price_uah: float = 0.0
    subtotal_uah: float = 0.0
    notes: list[str] = Field(default_factory=list)


class AllocationFailure(BaseModel):
    """Причина, чому виробник не може покрити потребу об'єкта"""
    reason_code: str  # "no_smoke_detector", "no_io_module", "loop_overflow", "panel_overflow"
    message: str
    needed: int
    available: int = 0


class Allocation(BaseModel):
    """Повна алокація компонентів для одного виробника"""
    manufacturer_id: str
    feasible: bool
    
    panels: list[AllocatedItem] = Field(default_factory=list)
    detectors_smoke: list[AllocatedItem] = Field(default_factory=list)
    detectors_heat: list[AllocatedItem] = Field(default_factory=list)
    io_modules: list[AllocatedItem] = Field(default_factory=list)
    mcps: list[AllocatedItem] = Field(default_factory=list)
    sounders: list[AllocatedItem] = Field(default_factory=list)
    
    # Підсумкові метрики
    total_addresses_used: int = 0
    total_logical_signals: int = 0
    panel_total_capacity: int = 0
    
    # Архітектурний податок
    architectural_efficiency_pct: float = 0.0
    
    # Вартість
    total_capex_uah: float = 0.0
    
    # Проблеми
    failures: list[AllocationFailure] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# ДОПОМІЖНІ ФУНКЦІЇ ПОШУКУ
# ═══════════════════════════════════════════════════════════════════


def find_detector_by_type(
    manufacturer: Manufacturer, target_types: set[DetectorType]
) -> Detector | None:
    """Знаходимо перший детектор виробника, що відповідає одному з типів"""
    for d in manufacturer.detectors:
        if d.detector_type in target_types:
            return d
    return None


def find_io_modules_for_inputs(
    manufacturer: Manufacturer,
) -> list[IOModule]:
    """Модулі, які можуть прийняти вхідні сигнали (INPUT, COMBINED, UNIVERSAL)"""
    valid_types = {IOModuleType.INPUT, IOModuleType.COMBINED, IOModuleType.UNIVERSAL}
    return sorted(
        [m for m in manufacturer.io_modules if m.module_type in valid_types and m.inputs_count > 0],
        # Сортуємо за ефективністю: входів на адресу (більше = краще)
        key=lambda m: m.inputs_count / m.address_consumption,
        reverse=True,
    )


def find_io_modules_for_outputs(
    manufacturer: Manufacturer,
) -> list[IOModule]:
    """Модулі, які можуть дати вихідні сигнали"""
    valid_types = {IOModuleType.OUTPUT, IOModuleType.COMBINED, IOModuleType.UNIVERSAL}
    return sorted(
        [m for m in manufacturer.io_modules if m.module_type in valid_types and m.outputs_count > 0],
        key=lambda m: m.outputs_count / m.address_consumption,
        reverse=True,
    )


# ═══════════════════════════════════════════════════════════════════
# КРОК 2.1. АЛОКАЦІЯ ДЕТЕКТОРІВ
# ═══════════════════════════════════════════════════════════════════


def allocate_detectors(
    requirements: BOMRequirements, manufacturer: Manufacturer
) -> tuple[list[AllocatedItem], list[AllocatedItem], list[AllocationFailure]]:
    """Розподіл потреби в детекторах на конкретні моделі виробника"""
    smoke_items: list[AllocatedItem] = []
    heat_items: list[AllocatedItem] = []
    failures: list[AllocationFailure] = []
    
    # Димові
    if requirements.smoke_detectors_count > 0:
        smoke_model = find_detector_by_type(
            manufacturer, {DetectorType.SMOKE_OPTICAL, DetectorType.MULTI_SENSOR}
        )
        if smoke_model:
            price = smoke_model.price_uah_no_vat or 0.0
            smoke_items.append(AllocatedItem(
                model_id=smoke_model.detector_id,
                model_name=smoke_model.model_name,
                quantity=requirements.smoke_detectors_count,
                addresses_consumed=requirements.smoke_detectors_count,  # 1 адреса на детектор
                unit_price_uah=price,
                subtotal_uah=price * requirements.smoke_detectors_count,
            ))
        else:
            failures.append(AllocationFailure(
                reason_code="no_smoke_detector",
                message=f"Виробник {manufacturer.manufacturer_id} не має димового детектора в каталозі",
                needed=requirements.smoke_detectors_count,
                available=0,
            ))
    
    # Теплові
    if requirements.heat_detectors_count > 0:
        heat_model = find_detector_by_type(
            manufacturer, {DetectorType.HEAT_MAX, DetectorType.HEAT_DIFFERENTIAL, DetectorType.MULTI_SENSOR}
        )
        if heat_model:
            price = heat_model.price_uah_no_vat or 0.0
            heat_items.append(AllocatedItem(
                model_id=heat_model.detector_id,
                model_name=heat_model.model_name,
                quantity=requirements.heat_detectors_count,
                addresses_consumed=requirements.heat_detectors_count,
                unit_price_uah=price,
                subtotal_uah=price * requirements.heat_detectors_count,
            ))
        else:
            failures.append(AllocationFailure(
                reason_code="no_heat_detector",
                message=f"Виробник {manufacturer.manufacturer_id} не має теплового детектора в каталозі",
                needed=requirements.heat_detectors_count,
            ))
    
    return smoke_items, heat_items, failures


# ═══════════════════════════════════════════════════════════════════
# КРОК 2.2. АЛОКАЦІЯ I/O МОДУЛІВ (ОСЕРДЯ АРХІТЕКТУРНОГО ПОДАТКУ)
# ═══════════════════════════════════════════════════════════════════


def allocate_io_modules(
    requirements: BOMRequirements, manufacturer: Manufacturer
) -> tuple[list[AllocatedItem], list[AllocationFailure]]:
    """
    Розподіл I/O сигналів на конкретні модулі виробника.
    
    Алгоритм:
    1. Спочатку оцінюємо найкращу ефективність окремо для входів і окремо для виходів
    2. Порівнюємо з combined-модулями: якщо комбіновані ефективніші — використовуємо їх
    3. Інакше — спеціалізовані INPUT/OUTPUT модулі
    
    «Ефективність» = (сигналів на адресу). Чим вище, тим менше адрес у петлі.
    """
    items: list[AllocatedItem] = []
    failures: list[AllocationFailure] = []
    
    remaining_inputs = requirements.io_input_signals_count
    remaining_outputs = requirements.io_output_signals_count
    
    # Найефективніший INPUT-only модуль
    best_input = None
    best_input_eff = 0.0
    for m in manufacturer.io_modules:
        if m.module_type == IOModuleType.INPUT and m.inputs_count > 0:
            eff = m.inputs_count / m.address_consumption
            if eff > best_input_eff:
                best_input_eff = eff
                best_input = m
    
    # Найефективніший OUTPUT-only модуль
    best_output = None
    best_output_eff = 0.0
    for m in manufacturer.io_modules:
        if m.module_type == IOModuleType.OUTPUT and m.outputs_count > 0:
            eff = m.outputs_count / m.address_consumption
            if eff > best_output_eff:
                best_output_eff = eff
                best_output = m
    
    # Найефективніший COMBINED модуль
    best_combined = None
    best_combined_eff = 0.0
    for m in manufacturer.io_modules:
        if m.module_type == IOModuleType.COMBINED and m.inputs_count > 0 and m.outputs_count > 0:
            eff = (m.inputs_count + m.outputs_count) / m.address_consumption
            if eff > best_combined_eff:
                best_combined_eff = eff
                best_combined = m
    
    # Стратегія: 
    # — Якщо специалізовані модулі сумарно ефективніші за combined для пари (1 in + 1 out),
    #   використовуємо їх. Інакше combined.
    # 
    # Приклад Cofem: 
    #   MYOA combined: 2 сигнали / 1 адреса = 2.0
    #   MSTAY8 input + MDA2YLT output: (8+2) / (1+1) = 5.0
    #   → специалізовані виграють
    #
    # Приклад де combined переможе: якщо специалізованих немає або вони слабкі.
    
    specialized_efficiency = 0.0
    if best_input and best_output:
        # «Подвоєна ефективність» — скільки сигналів на 2 адреси (1 input module + 1 output module)
        specialized_efficiency = (best_input.inputs_count + best_output.outputs_count) / (
            best_input.address_consumption + best_output.address_consumption
        )
    
    use_specialized = specialized_efficiency > best_combined_eff
    
    if use_specialized and best_input:
        # Закриваємо ВСІ входи специализованими
        modules_needed = (remaining_inputs + best_input.inputs_count - 1) // best_input.inputs_count
        if modules_needed > 0:
            price = best_input.price_uah_no_vat or 0.0
            items.append(AllocatedItem(
                model_id=best_input.module_id,
                model_name=best_input.model_name,
                quantity=modules_needed,
                addresses_consumed=modules_needed * best_input.address_consumption,
                unit_price_uah=price,
                subtotal_uah=price * modules_needed,
                notes=[f"Specialized input: {modules_needed} × {best_input.inputs_count} in"],
            ))
            remaining_inputs = 0  # покрили
    
    if use_specialized and best_output:
        # Закриваємо ВСІ виходи специализованими
        modules_needed = (remaining_outputs + best_output.outputs_count - 1) // best_output.outputs_count
        if modules_needed > 0:
            price = best_output.price_uah_no_vat or 0.0
            items.append(AllocatedItem(
                model_id=best_output.module_id,
                model_name=best_output.model_name,
                quantity=modules_needed,
                addresses_consumed=modules_needed * best_output.address_consumption,
                unit_price_uah=price,
                subtotal_uah=price * modules_needed,
                notes=[f"Specialized output: {modules_needed} × {best_output.outputs_count} out"],
            ))
            remaining_outputs = 0
    
    # Якщо combined-модуль ефективніший або специализованих немає — використовуємо combined
    if not use_specialized and best_combined:
        max_modules_for_inputs = (
            (remaining_inputs + best_combined.inputs_count - 1) // best_combined.inputs_count
            if best_combined.inputs_count > 0 else 0
        )
        max_modules_for_outputs = (
            (remaining_outputs + best_combined.outputs_count - 1) // best_combined.outputs_count
            if best_combined.outputs_count > 0 else 0
        )
        modules_needed = max(max_modules_for_inputs, max_modules_for_outputs)
        
        if modules_needed > 0:
            price = best_combined.price_uah_no_vat or 0.0
            items.append(AllocatedItem(
                model_id=best_combined.module_id,
                model_name=best_combined.model_name,
                quantity=modules_needed,
                addresses_consumed=modules_needed * best_combined.address_consumption,
                unit_price_uah=price,
                subtotal_uah=price * modules_needed,
                notes=[
                    f"Combined: {modules_needed} × ({best_combined.inputs_count} in + {best_combined.outputs_count} out)"
                ],
            ))
            remaining_inputs = max(0, remaining_inputs - modules_needed * best_combined.inputs_count)
            remaining_outputs = max(0, remaining_outputs - modules_needed * best_combined.outputs_count)
    
    # Якщо лишилось щось не покритого — failure
    if remaining_inputs > 0:
        failures.append(AllocationFailure(
            reason_code="insufficient_input_modules",
            message=f"Не вдалося закрити всі вхідні сигнали виробником {manufacturer.manufacturer_id}",
            needed=remaining_inputs,
        ))
    if remaining_outputs > 0:
        failures.append(AllocationFailure(
            reason_code="insufficient_output_modules",
            message=f"Не вдалося закрити всі вихідні сигнали",
            needed=remaining_outputs,
        ))
    
    return items, failures


# ═══════════════════════════════════════════════════════════════════
# КРОК 2.3. АЛОКАЦІЯ MCP І SOUNDERS
# ═══════════════════════════════════════════════════════════════════


def allocate_mcps(
    requirements: BOMRequirements, manufacturer: Manufacturer
) -> tuple[list[AllocatedItem], list[AllocationFailure]]:
    if requirements.manual_call_points_count == 0:
        return [], []
    
    if not manufacturer.manual_call_points:
        return [], [AllocationFailure(
            reason_code="no_mcp_model",
            message=f"Виробник {manufacturer.manufacturer_id} не має MCP в каталозі (буде уточнено)",
            needed=requirements.manual_call_points_count,
        )]
    
    mcp = manufacturer.manual_call_points[0]
    price = mcp.price_uah_no_vat or 0.0
    return [AllocatedItem(
        model_id=mcp.mcp_id,
        model_name=mcp.model_name,
        quantity=requirements.manual_call_points_count,
        addresses_consumed=requirements.manual_call_points_count * mcp.address_consumption,
        unit_price_uah=price,
        subtotal_uah=price * requirements.manual_call_points_count,
    )], []


def allocate_sounders(
    requirements: BOMRequirements, manufacturer: Manufacturer
) -> tuple[list[AllocatedItem], list[AllocationFailure]]:
    if requirements.sounders_count == 0:
        return [], []
    
    if not manufacturer.sounders:
        return [], [AllocationFailure(
            reason_code="no_sounder_model",
            message=f"Виробник {manufacturer.manufacturer_id} не має sounder в каталозі (буде уточнено)",
            needed=requirements.sounders_count,
        )]
    
    # Якщо потрібен strobe — обираємо модель з strobe
    eligible = [s for s in manufacturer.sounders if s.has_strobe == requirements.sounders_need_strobe]
    if not eligible:
        eligible = manufacturer.sounders
    
    sounder = eligible[0]
    price = sounder.price_uah_no_vat or 0.0
    return [AllocatedItem(
        model_id=sounder.sounder_id,
        model_name=sounder.model_name,
        quantity=requirements.sounders_count,
        addresses_consumed=requirements.sounders_count * sounder.address_consumption,
        unit_price_uah=price,
        subtotal_uah=price * requirements.sounders_count,
    )], []


# ═══════════════════════════════════════════════════════════════════
# КРОК 2.4. ВИБІР ПАНЕЛІ
# ═══════════════════════════════════════════════════════════════════


def allocate_panel(
    total_addresses: int, manufacturer: Manufacturer
) -> tuple[list[AllocatedItem], list[AllocationFailure]]:
    """
    Вибір найменшої панелі, яка вміщує всі адреси.
    Якщо однієї не вистачає — беремо найбільшу + N додаткових (мережева).
    """
    if not manufacturer.panels:
        return [], [AllocationFailure(
            reason_code="no_panels",
            message=f"Виробник {manufacturer.manufacturer_id} не має панелей у каталозі",
            needed=total_addresses,
        )]
    
    # Сортуємо за зростанням ємності
    sorted_panels = sorted(manufacturer.panels, key=lambda p: p.max_total_devices)
    
    # Найменша панель, яка покриває потребу
    for panel in sorted_panels:
        if panel.max_total_devices >= total_addresses:
            price = panel.price_uah_no_vat or 0.0
            return [AllocatedItem(
                model_id=panel.panel_id,
                model_name=panel.model_name,
                quantity=1,
                addresses_consumed=0,  # сама панель не споживає адрес
                unit_price_uah=price,
                subtotal_uah=price,
                notes=[f"Capacity: {panel.max_total_devices} addresses (used {total_addresses})"],
            )], []
    
    # Не вистачає однієї панелі — беремо найбільшу і додаткові
    largest = sorted_panels[-1]
    panels_needed = (total_addresses + largest.max_total_devices - 1) // largest.max_total_devices
    
    if panels_needed > largest.network_max_panels:
        return [], [AllocationFailure(
            reason_code="loop_overflow",
            message=(
                f"Потреба {total_addresses} адрес перевищує максимальну "
                f"мережеву ємність виробника {manufacturer.manufacturer_id} "
                f"({largest.network_max_panels} × {largest.max_total_devices} = "
                f"{largest.network_max_panels * largest.max_total_devices})"
            ),
            needed=total_addresses,
            available=largest.network_max_panels * largest.max_total_devices,
        )]
    
    price = largest.price_uah_no_vat or 0.0
    return [AllocatedItem(
        model_id=largest.panel_id,
        model_name=largest.model_name,
        quantity=panels_needed,
        unit_price_uah=price,
        subtotal_uah=price * panels_needed,
        notes=[f"Мережева конфігурація: {panels_needed} панелей"],
    )], []


# ═══════════════════════════════════════════════════════════════════
# КРОК 2 (ГОЛОВНА ФУНКЦІЯ)
# ═══════════════════════════════════════════════════════════════════


def allocate_for_manufacturer(
    requirements: BOMRequirements, manufacturer: Manufacturer
) -> Allocation:
    """Повна алокація компонентів для одного виробника"""
    
    # 2.1 Детектори
    smoke, heat, det_fail = allocate_detectors(requirements, manufacturer)
    
    # 2.2 I/O модулі
    io_modules, io_fail = allocate_io_modules(requirements, manufacturer)
    
    # 2.3 MCP і Sounders
    mcps, mcp_fail = allocate_mcps(requirements, manufacturer)
    sounders, sounder_fail = allocate_sounders(requirements, manufacturer)
    
    # Підрахунок адрес у петлях (сума з усіх алокованих)
    total_addresses = sum(
        i.addresses_consumed
        for collection in [smoke, heat, io_modules, mcps, sounders]
        for i in collection
    )
    
    # 2.4 Вибір панелі (тільки після підрахунку адрес)
    panels, panel_fail = allocate_panel(total_addresses, manufacturer)
    
    # Архітектурна ефективність:
    # logical_signals (те, що ми ХОЧЕМО) / addresses_used (адреси, які реально займаємо)
    # Для детекторів/MCP/sounder — 1 пристрій = 1 логічний сигнал
    # Для I/O — реальні логічні сигнали з requirements
    logical_signals = (
        requirements.smoke_detectors_count +
        requirements.heat_detectors_count +
        requirements.manual_call_points_count +
        requirements.sounders_count +
        requirements.total_logical_signals()  # I/O сигнали окремо
    )
    
    # Адреси, які реально займаємо
    physical_addresses_for_io = sum(i.addresses_consumed for i in io_modules)
    physical_addresses_total = (
        sum(i.addresses_consumed for i in smoke) +
        sum(i.addresses_consumed for i in heat) +
        sum(i.addresses_consumed for i in mcps) +
        sum(i.addresses_consumed for i in sounders) +
        physical_addresses_for_io
    )
    
    architectural_efficiency = (
        100.0 * logical_signals / physical_addresses_total
        if physical_addresses_total > 0 else 0.0
    )
    
    # Загальна вартість CAPEX
    total_capex = sum(
        i.subtotal_uah
        for collection in [panels, smoke, heat, io_modules, mcps, sounders]
        for i in collection
    )
    
    # Усі failures разом
    all_failures = det_fail + io_fail + mcp_fail + sounder_fail + panel_fail
    feasible = len([f for f in all_failures if f.reason_code in (
        "no_smoke_detector", "no_heat_detector", "loop_overflow", "no_panels"
    )]) == 0
    
    return Allocation(
        manufacturer_id=manufacturer.manufacturer_id,
        feasible=feasible,
        panels=panels,
        detectors_smoke=smoke,
        detectors_heat=heat,
        io_modules=io_modules,
        mcps=mcps,
        sounders=sounders,
        total_addresses_used=total_addresses,
        total_logical_signals=logical_signals,
        panel_total_capacity=(
            panels[0].notes and int(panels[0].notes[0].split("Capacity:")[1].split()[0])
            if panels and panels[0].notes else 0
        ) if panels else 0,
        architectural_efficiency_pct=round(architectural_efficiency, 1),
        total_capex_uah=round(total_capex, 2),
        failures=all_failures,
    )
