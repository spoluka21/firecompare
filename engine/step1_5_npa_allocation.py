"""
КРОК 1.5. NPA Allocation — розподіл BOM-вимог між NPA-зонами

Якщо в state.npa_architecture задано кілька NPA-зон (наприклад, для Замкової — 
3 ППКП: укриття + паркінг + головний), цей крок:
1. Розподіляє детектори за приналежністю до functional_zones кожної NPA-зони
2. Розподіляє I/O сигнали за io_allocation (часткі від загальних)
3. Розподіляє MCP і sounders пропорційно площі NPA-зон
4. Повертає словник {npa_zone_id: BOMRequirements}

Якщо npa_architecture не задано — повертає {"default": original_requirements},
зберігаючи зворотну сумісність з простим режимом.

Reference: ДБН В.1.1-7:2016 (загальна архітектура СПЗ),
           ДБН В.2.3-15:2017 (паркінги — незалежна СПЗ),
           принцип НПА: «незалежність працездатності критичних зон».
"""
from typing import Optional

from engine.step1_bom_requirements import BOMRequirements
from schemas.object_state import ObjectState, NPAArchitecture, NPAZone


def allocate_bom_to_npa_zones(
    state: ObjectState, total_bom: BOMRequirements
) -> dict[str, BOMRequirements]:
    """
    Розподіляє загальні BOM-вимоги між NPA-зонами.
    
    Повертає словник {zone_id: BOMRequirements}.
    Якщо npa_architecture не задано — повертає {"default": total_bom}.
    """
    arch = state.npa_architecture
    
    # Простий режим — повертаємо як було
    if arch is None or not arch.zones:
        return {"default": total_bom}
    
    result: dict[str, BOMRequirements] = {}
    
    # Загальна площа всіх NPA-зон (для пропорційного розподілу MCP/sounders)
    total_npa_area = sum(z.area_m2 for z in arch.zones)
    
    # Загальні I/O сигнали для розподілу
    total_io_inputs = total_bom.io_input_signals_count
    total_io_outputs = total_bom.io_output_signals_count
    
    for npa_zone in arch.zones:
        # 1. Детектори: розподіляємо за приналежністю functional_zones
        zone_smoke, zone_heat, zone_area_actual, zone_notes = _allocate_detectors_to_npa_zone(
            state, npa_zone
        )
        
        # 2. I/O сигнали: за io_allocation
        share = _get_io_share_for_zone(arch, npa_zone)
        zone_io_inputs = round(total_io_inputs * share)
        zone_io_outputs = round(total_io_outputs * share)
        
        # 3. MCP: пропорційно площі NPA-зони
        area_ratio = npa_zone.area_m2 / total_npa_area if total_npa_area > 0 else 0
        zone_mcp = max(1, round(total_bom.manual_call_points_count * area_ratio))
        
        # 4. Sounders: теж пропорційно площі
        zone_sounders = max(1, round(total_bom.sounders_count * area_ratio))
        
        zone_notes_full = [
            f"=== NPA-зона: {npa_zone.name} ==="
        ] + zone_notes + [
            f"I/O частка: {share*100:.1f}% від загальних → "
            f"{zone_io_inputs} вх, {zone_io_outputs} вих",
            f"MCP пропорційно площі ({area_ratio*100:.1f}%): {zone_mcp} шт",
            f"Sounders пропорційно площі: {zone_sounders} шт",
        ]
        
        result[npa_zone.zone_id] = BOMRequirements(
            smoke_detectors_count=zone_smoke,
            heat_detectors_count=zone_heat,
            io_input_signals_count=zone_io_inputs,
            io_output_signals_count=zone_io_outputs,
            manual_call_points_count=zone_mcp,
            sounders_count=zone_sounders,
            sounders_need_strobe=total_bom.sounders_need_strobe,
            total_detection_area_m2=zone_area_actual,
            notes=zone_notes_full,
        )
    
    return result


def _allocate_detectors_to_npa_zone(
    state: ObjectState, npa_zone: NPAZone
) -> tuple[int, int, float, list[str]]:
    """
    Розраховує детектори для конкретної NPA-зони, використовуючи
    її список functional_zones як вхід.
    
    Повертає (smoke, heat, total_area, notes).
    """
    from engine.step1_bom_requirements import calculate_detectors_for_zone
    
    total_smoke = 0
    total_heat = 0
    total_area = 0.0
    notes = []
    
    # Спеціальний випадок: укриття без власних functional_zones
    # (підмножина якоїсь іншої зони, як у Замковій — частина паркінгу)
    if not npa_zone.functional_zones:
        # Просто оцінюємо за площею NPA-зони з типовою щільністю
        # Для укриття — димові, з коефіцієнтом 1.0
        from engine.step1_bom_requirements import SMOKE_DETECTOR_AREA_M2
        estimated = max(1, -(-int(npa_zone.area_m2 * 100) // int(SMOKE_DETECTOR_AREA_M2 * 100)))
        notes.append(
            f"{npa_zone.zone_id} (без явних functional_zones, S={npa_zone.area_m2:.0f} м²): "
            f"~{estimated} димових детекторів"
        )
        return estimated, 0, npa_zone.area_m2, notes
    
    # Стандартний випадок: проходимо по functional_zones
    for fz_id in npa_zone.functional_zones:
        if fz_id not in state.object.zones:
            notes.append(f"УВАГА: functional_zone '{fz_id}' не знайдено в object.zones")
            continue
        
        fz_data = state.object.zones[fz_id]
        smoke, heat, note = calculate_detectors_for_zone(fz_id, fz_data)
        total_smoke += smoke
        total_heat += heat
        total_area += fz_data.area_m2
        notes.append(note)
    
    return total_smoke, total_heat, total_area, notes


def _get_io_share_for_zone(
    arch: NPAArchitecture, npa_zone: NPAZone
) -> float:
    """Витягуємо частку I/O для конкретної NPA-зони з io_allocation"""
    io = arch.io_allocation
    
    if npa_zone.zone_id == "shelter" or npa_zone.zone_type.value == "shelter":
        return io.shelter_share
    elif npa_zone.zone_id == "parking" or npa_zone.zone_type.value == "parking":
        return io.parking_share
    elif npa_zone.zone_id == "main" or npa_zone.zone_type.value == "main":
        return io.main_share
    elif npa_zone.zone_id in io.building_shares:
        return io.building_shares[npa_zone.zone_id]
    else:
        # Fallback: пропорційно
        return 1.0 / max(1, len(arch.zones))
