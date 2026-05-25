"""
PIPELINE ORCHESTRATOR — головна функція движка FireCompare

Приймає ObjectState (вхід від агента) і повертає CalculationResult 
(вихід для агента, відповідно до Engine_Output_Schema_v02.md).

Потік:
  Step 1 (BOM) → Step 1.5 (NPA Allocation) → Step 2 (Allocation per mfr) 
  → Step 3 (Compliance) → Step 4 (Scoring) → CalculationResult

Підтримує два режими:
  - Простий: state.npa_architecture = None → 1 ППКП на виробника
  - NPA: state.npa_architecture задано → кілька ППКП на виробника

Mode 2 і Mode 3 — у наступних сесіях (зворотній аналіз + меморандум).
"""
from datetime import datetime
from hashlib import sha256
from typing import Optional

from pydantic import BaseModel, Field

from engine.step1_bom_requirements import BOMRequirements, compute_bom_requirements
from engine.step1_5_npa_allocation import allocate_bom_to_npa_zones
from engine.step2_allocation import Allocation, allocate_for_manufacturer
from engine.step2_npa_allocation import (
    MultiPanelAllocation, allocate_for_manufacturer_with_npa,
)
from engine.step3_compliance import ComplianceResult, check_compliance
from engine.step4_scoring import ManufacturerScores, compute_scores
from schemas.catalog import Catalog, Manufacturer
from schemas.object_state import ObjectState


# ═══════════════════════════════════════════════════════════════════
# ВИХІДНІ СТРУКТУРИ
# ═══════════════════════════════════════════════════════════════════


class ManufacturerResult(BaseModel):
    """Повний результат для одного виробника"""
    manufacturer_id: str
    manufacturer_name: str
    
    # Compliance
    compliance: ComplianceResult
    
    # Алокація (один з двох типів)
    allocation_simple: Optional[Allocation] = None
    allocation_npa: Optional[MultiPanelAllocation] = None
    
    # Скоринг
    scores: Optional[ManufacturerScores] = None
    
    # Розрахунок ТО (опційно, якщо в state є maintenance_params)
    maintenance: Optional[dict] = None  # MaintenanceResult.model_dump()
    
    # Зведення для UI
    capex_uah: float = 0.0
    addresses_used: int = 0
    architectural_efficiency_pct: float = 0.0
    panel_count: int = 1
    
    feasible: bool = True
    excluded: bool = False
    exclusion_reason: Optional[str] = None
    
    # Блок B: оптимальна конфігурація ППКП за шлейфами (принцип #5)
    # dict: units, model_name, normal_loops, fire_resistant_loops, total_panel_price_uah тощо
    loop_config: Optional[dict] = None


class CalculationResult(BaseModel):
    """Повний вихід движка для одного ObjectState"""
    calculation_id: str
    timestamp: str
    engine_version: str = "0.2.0"
    input_state_hash: str
    
    # Звідки взяти параметри
    object_summary: dict
    is_multi_panel_mode: bool
    
    # BOM на верхньому рівні
    total_bom: BOMRequirements
    
    # BOM по NPA-зонах (якщо NPA-режим)
    npa_bom: Optional[dict[str, BOMRequirements]] = None
    
    # Результати по виробниках
    manufacturer_results: list[ManufacturerResult] = Field(default_factory=list)
    
    # Зведення для агента — порівняльна таблиця
    comparison_table: list[dict] = Field(default_factory=list)
    
    # Warnings і інформаційні повідомлення
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ — ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════


def run_calculation(
    state: ObjectState,
    catalog: Catalog,
) -> CalculationResult:
    """
    Повний прогон pipeline для одного об'єкта.
    
    Прогоняє всі кроки і збирає підсумковий CalculationResult.
    """
    # Метадані
    state_json = state.model_dump_json()
    input_hash = sha256(state_json.encode()).hexdigest()[:16]
    calc_id = f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{input_hash[:8]}"
    
    is_npa_mode = (
        state.npa_architecture is not None
        and len(state.npa_architecture.zones) > 0
    )
    
    result = CalculationResult(
        calculation_id=calc_id,
        timestamp=datetime.now().isoformat(),
        input_state_hash=input_hash,
        is_multi_panel_mode=is_npa_mode,
        object_summary={
            "type": state.object.object_type.value,
            "total_area_m2": state.object.total_area_m2,
            "floors": f"{state.object.floors_above}+{state.object.floors_below}",
            "jurisdictions": [j.value for j in state.pre_object.jurisdictions],
            "zones_count": len(state.object.zones),
        },
        total_bom=BOMRequirements(
            smoke_detectors_count=0, heat_detectors_count=0,
            io_input_signals_count=0, io_output_signals_count=0,
            manual_call_points_count=0, sounders_count=0,
            total_detection_area_m2=0,
        ),
    )
    
    # ─────────────────────────────────────────────────────────
    # Step 1: BOM Requirements
    # ─────────────────────────────────────────────────────────
    bom = compute_bom_requirements(state)
    result.total_bom = bom
    
    # ─────────────────────────────────────────────────────────
    # Step 1.5: NPA Allocation (якщо NPA режим)
    # ─────────────────────────────────────────────────────────
    npa_bom = None
    if is_npa_mode:
        npa_bom = allocate_bom_to_npa_zones(state, bom)
        result.npa_bom = npa_bom
        result.notes.append(
            f"NPA-режим: {len(state.npa_architecture.zones)} незалежних ППКП "
            f"({', '.join(z.zone_id for z in state.npa_architecture.zones)})"
        )
    else:
        result.notes.append("Простий режим: 1 ППКП на об'єкт")
    
    # ─────────────────────────────────────────────────────────
    # Steps 2-3 для кожного виробника
    # ─────────────────────────────────────────────────────────
    allocations_for_scoring = {}  # mfr_id → AllocationLike (для Step 4)
    
    for mfr in catalog.manufacturers:
        if mfr.manufacturer_id not in state.comparison_set:
            continue
        
        mfr_result = ManufacturerResult(
            manufacturer_id=mfr.manufacturer_id,
            manufacturer_name=mfr.name_ua,
            compliance=check_compliance(state, mfr),
        )
        
        # Step 3: Compliance — виключає за юрисдикцією
        if mfr_result.compliance.overall_status == "fail":
            mfr_result.excluded = True
            mfr_result.exclusion_reason = mfr_result.compliance.summary_message
            mfr_result.feasible = False
            result.manufacturer_results.append(mfr_result)
            continue
        
        # Step 2: Allocation (Simple або NPA)
        if is_npa_mode:
            alloc = allocate_for_manufacturer_with_npa(state, npa_bom, mfr)
            mfr_result.allocation_npa = alloc
            mfr_result.feasible = alloc.feasible
            mfr_result.capex_uah = alloc.total_capex_uah
            mfr_result.addresses_used = alloc.total_addresses_used
            mfr_result.architectural_efficiency_pct = alloc.architectural_efficiency_pct
            mfr_result.panel_count = alloc.total_panels_count
            
            if not alloc.feasible:
                mfr_result.exclusion_reason = (
                    "Не feasible для NPA-архітектури: "
                    + "; ".join(f.reason_code for f in alloc.failures[:3])
                )
                mfr_result.excluded = True
            else:
                allocations_for_scoring[mfr.manufacturer_id] = alloc
        else:
            alloc = allocate_for_manufacturer(bom, mfr)
            mfr_result.allocation_simple = alloc
            mfr_result.feasible = alloc.feasible
            mfr_result.capex_uah = alloc.total_capex_uah
            mfr_result.addresses_used = alloc.total_addresses_used
            mfr_result.architectural_efficiency_pct = alloc.architectural_efficiency_pct
            mfr_result.panel_count = len(alloc.panels)
            
            if not alloc.feasible:
                mfr_result.exclusion_reason = (
                    "Не feasible: " + "; ".join(f.reason_code for f in alloc.failures[:3])
                )
                mfr_result.excluded = True
            else:
                allocations_for_scoring[mfr.manufacturer_id] = alloc
        
        # Блок B: оптимальна конфігурація ППКП за шлейфами (принцип #5).
        # Рахуємо ЗАВЖДИ (навіть якщо старий allocation дав overflow), бо принцип #5:
        # будь-яку систему можна реалізувати кількома приладами — ніхто не вибуває.
        try:
            from engine.loop_allocation import optimize_panels_for_manufacturer
            from engine.step1_bom_requirements import calculate_zonal_engineering
            detectors_total = bom.smoke_detectors_count + bom.heat_detectors_count
            _zonal = calculate_zonal_engineering(state.object)
            relay_total = _zonal.get("relay_devices", 0)
            opt = optimize_panels_for_manufacturer(
                detectors_total, relay_total, mfr.panels,
                is_addressable=getattr(state.object, "is_addressable", True),
            )
            if opt.get("feasible"):
                opt["normal_cable_m"] = bom.normal_cable_m
                opt["fire_resistant_cable_m"] = bom.fire_resistant_cable_m
                mfr_result.loop_config = opt
                
                # ПОРЯТУНОК (принцип #5): якщо старий allocation виключив через
                # переповнення шлейфів/адрес (loop_overflow / address_overflow), але
                # оптимізатор знайшов рішення з кількох приладів — повертаємо виробника
                # в порівняння з конфігурацією оптимізатора. Compliance-виключення
                # (сертифікація) при цьому НЕ скасовуємо — вони залишаються чинними.
                overflow_excluded = (
                    mfr_result.excluded
                    and mfr_result.compliance.overall_status != "fail"
                    and mfr_result.exclusion_reason
                    and "overflow" in mfr_result.exclusion_reason.lower()
                )
                if overflow_excluded:
                    mfr_result.excluded = False
                    mfr_result.feasible = True
                    mfr_result.exclusion_reason = None
                    mfr_result.capex_uah = opt["total_panel_price_uah"]
                    mfr_result.panel_count = opt["units"]
        except Exception:
            pass  # оптимізатор не критичний — не ламаємо основний розрахунок
        
        result.manufacturer_results.append(mfr_result)
    
    # ─────────────────────────────────────────────────────────
    # Step 4: Scoring (для тих що feasible і compliant)
    # ─────────────────────────────────────────────────────────
    if allocations_for_scoring:
        manufacturers_map = {
            m.manufacturer_id: m for m in catalog.manufacturers
            if m.manufacturer_id in allocations_for_scoring
        }
        scores = compute_scores(allocations_for_scoring, manufacturers_map, state)
        
        for mfr_result in result.manufacturer_results:
            if mfr_result.manufacturer_id in scores:
                mfr_result.scores = scores[mfr_result.manufacturer_id]
    
    # ─────────────────────────────────────────────────────────
    # Step 5: Maintenance calculation (якщо в state є maintenance_params)
    # ─────────────────────────────────────────────────────────
    if state.maintenance_params is not None:
        from engine.maintenance_calculator import (
            calculate_maintenance, MaintenanceParams,
        )
        try:
            mnt_params = MaintenanceParams(**state.maintenance_params)
        except Exception as e:
            result.warnings.append(f"Не вдалося розпарсити maintenance_params: {e}")
            mnt_params = None
        
        if mnt_params is not None:
            mfr_map_by_id = {m.manufacturer_id: m for m in catalog.manufacturers}
            for mfr_result in result.manufacturer_results:
                if mfr_result.excluded:
                    continue
                mfr_obj = mfr_map_by_id.get(mfr_result.manufacturer_id)
                if mfr_obj is None:
                    continue
                try:
                    mnt_result = calculate_maintenance(mnt_params, mfr_obj)
                    mfr_result.maintenance = mnt_result.model_dump()
                except Exception as e:
                    result.warnings.append(
                        f"Помилка розрахунку ТО для {mfr_result.manufacturer_name}: {e}"
                    )
    
    # ─────────────────────────────────────────────────────────
    # Зведення для UI — порівняльна таблиця
    # ─────────────────────────────────────────────────────────
    # Сортуємо за overall_score (спадання), якщо є; інакше за CAPEX (зростання)
    def sort_key(r):
        if r.scores and r.scores.overall_score is not None:
            return -r.scores.overall_score  # вище = краще
        return r.capex_uah if r.capex_uah > 0 else float('inf')
    
    sorted_results = sorted(
        [r for r in result.manufacturer_results if not r.excluded],
        key=sort_key,
    )
    
    for r in sorted_results:
        row = {
            "manufacturer_id": r.manufacturer_id,
            "manufacturer_name": r.manufacturer_name,
            "capex_uah": r.capex_uah,
            "addresses_used": r.addresses_used,
            "architectural_efficiency_pct": r.architectural_efficiency_pct,
            "panel_count": r.panel_count,
            "compliance_status": r.compliance.overall_status,
        }
        if r.scores:
            row["layer_1_capex_score"] = r.scores.layer_1_capex.score
            row["layer_2_architectural_score"] = r.scores.layer_2_architectural.score
            if r.scores.layer_3_functional:
                row["layer_3_functional_score"] = r.scores.layer_3_functional.score
            if r.scores.layer_4_operational:
                row["layer_4_operational_score"] = r.scores.layer_4_operational.score
            if r.scores.layer_5_tco:
                row["layer_5_tco_score"] = r.scores.layer_5_tco.score
            if r.scores.overall_score is not None:
                row["overall_score"] = r.scores.overall_score
        
        # Maintenance — додаткова колонка для UI
        if r.maintenance:
            bd = r.maintenance.get("breakdown", {})
            row["maintenance_month_uah"] = bd.get("price_final_month")
            row["maintenance_year_uah"] = bd.get("price_final_year")
        
        # Блок B: конфігурація ППКП за шлейфами
        if r.loop_config:
            row["loop_config"] = r.loop_config
        
        result.comparison_table.append(row)
    
    # Виключені виробники як ноти
    excluded = [r for r in result.manufacturer_results if r.excluded]
    if excluded:
        result.warnings.append(
            f"Виключено {len(excluded)} виробників: "
            + ", ".join(r.manufacturer_name for r in excluded)
        )
    
    return result
