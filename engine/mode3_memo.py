"""
MODE 3 — MANUFACTURER-SPECIFIC MEMORANDUM (UA/EN)

Глибока аналітична записка по конкретному виробнику для конкретного об'єкта.
Двомовна підтримка: language="ua" або "en".

Структура меморандуму:
1. ТИТУЛ + ПІДЗАГОЛОВОК
2. ПРОФІЛЬ ВИРОБНИКА
3. ВІДПОВІДНІСТЬ НОРМАТИВАМ
4. ТЕХНІЧНА КОНФІГУРАЦІЯ
5. ЕКОНОМІЧНІ ПОКАЗНИКИ
6. ПОЗИЦІЯ В COMPARISON-SET (5 шарів + overall)
7. СИЛЬНІ І СЛАБКІ СТОРОНИ
8. РЕЗЮМЕ І РЕКОМЕНДАЦІЇ
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from engine.pipeline import CalculationResult, ManufacturerResult
from schemas.catalog import Manufacturer
from schemas.object_state import ObjectState


# ═══════════════════════════════════════════════════════════════════
# ЛОКАЛІЗОВАНІ ТЕКСТИ
# ═══════════════════════════════════════════════════════════════════

L10N = {
    "ua": {
        "title_prefix": "АНАЛІТИЧНИЙ МЕМОРАНДУМ ПО ВИРОБНИКУ",
        "subtitle": "Об'єкт: {obj} | Згенеровано: FireCompare {ver}",
        # Section titles
        "s1_title": "1. ПРОФІЛЬ ВИРОБНИКА",
        "s2_title": "2. ВІДПОВІДНІСТЬ НОРМАТИВНИМ ВИМОГАМ",
        "s3_title": "3. ТЕХНІЧНА КОНФІГУРАЦІЯ ДЛЯ ОБ'ЄКТА",
        "s4_title": "4. ЕКОНОМІЧНІ ПОКАЗНИКИ",
        "s5_title": "5. ПОЗИЦІЯ В COMPARISON-SET (5 ШАРІВ)",
        "s6_title": "6. СИЛЬНІ ТА СЛАБКІ СТОРОНИ",
        "s7_title": "7. РЕЗЮМЕ ТА РЕКОМЕНДАЦІЇ",
        # Section 1 - Profile
        "country": "Країна походження",
        "founded": "Рік заснування",
        "tier": "Ціновий сегмент",
        "system_type": "Тип системи",
        "warranty": "Гарантійний термін",
        "months": "місяців",
        "with_extension": "(з можливістю продовження)",
        "ua_distributor": "UA-дистриб'ютор",
        "service_coverage": "Сервісне покриття",
        "response_time": "Час реакції на виклик",
        "manufacturer_label": "Виробник",
        "not_specified": "не вказано",
        # Section 2 - Compliance
        "active_jurisdictions": "Активні юрисдикції для цього об'єкта",
        "overall_status": "Загальний статус",
        "compl_jurisdiction": "Юрисдикція",
        "compl_status": "Статус",
        "compl_reasoning": "Обґрунтування",
        # Section 3 - Technical
        "object_label": "Об'єкт",
        "total_protected": "загальна захищувана площа",
        "floors_label": "поверховість",
        "arch_npa": "Архітектура: {n} незалежних ППКП. Загалом використано {addr} адрес для {sig} логічних сигналів (архітектурна ефективність {eff}%).",
        "arch_simple": "Архітектура: 1 ППКП ({panel}). Використано {addr} адрес для {sig} логічних сигналів (архітектурна ефективність {eff}%).",
        "tbl_npa_zone": "NPA-зона",
        "tbl_panel": "Панель",
        "tbl_loops": "Шлейфів",
        "tbl_addresses": "Адрес",
        "tbl_capex_uah": "CAPEX (₴)",
        # Section 4 - Economics
        "capex_text": "CAPEX (обладнання): {val:,.0f} ₴ (без кабельної продукції, монтажних робіт, ПДВ).",
        "tco_text": "TCO за {years} років: {val:,.0f} ₴. Детальна структура нижче.",
        # Section 5 - Position
        "position_score_not_avail": "Оцінка за 5 шарами недоступна.",
        "position_text": "Позиція: {pos} з {total} feasible виробників. Overall: {score:.1f} з 100.",
        "tbl_layer": "Шар",
        "tbl_score": "Бал",
        "tbl_reasoning": "Обґрунтування",
        "l1": "L1 CAPEX",
        "l2": "L2 Архітектура",
        "l3": "L3 Функціонал",
        "l4": "L4 Експлуатація",
        "l5": "L5 TCO",
        # Section 6 - Strengths
        "strengths_label": "Сильні сторони:",
        "weaknesses_label": "Зони уваги:",
        # Section 7 - Summary
        "summary_unavailable": "Резюме недоступне.",
        "summary_winner": "{name} — РЕКОМЕНДОВАНИЙ ВИРОБНИК для цього об'єкта (позиція 1 з {total}, overall {score:.1f}).",
        "summary_winner_explain": "Зведена оцінка системи показує найкраще співвідношення характеристик за всією сукупністю критеріїв об'єкта.",
        "summary_second": "{name} — друга позиція з {total} (overall {score:.1f}, переможець {winner_name} з {winner_score:.1f}). Різниця: {diff:.1f} балів.",
        "summary_lower": "{name} — {pos}-а позиція з {total} (overall {score:.1f}). Переможець: {winner_name} з overall {winner_score:.1f}.",
        "summary_detail": "Деталізовані обґрунтування за кожним з 5 шарів див. у розділі 5. Рішення про прийняття цього виробника як основного має враховувати також організаційні фактори: довіра до бренду, попередній досвід, наявність сертифікованих інсталяторів, узгодження з замовником і генпідрядником.",
        "disclaimer": "Дисклеймер: розрахунок виконано на основі базової моделі MVP. Не враховано вартість кабельної продукції, монтажних і пуско-налагоджувальних робіт, ПДВ, проектних послуг. Кінцева архітектура системи (кількість ППКП, розподіл шлейфів, вибір кабелю) визначається на стадії робочого проекту сертифікованим проектувальником.",
    },
    "en": {
        "title_prefix": "ANALYTICAL MEMORANDUM ON MANUFACTURER",
        "subtitle": "Object: {obj} | Generated: FireCompare {ver}",
        "s1_title": "1. MANUFACTURER PROFILE",
        "s2_title": "2. COMPLIANCE WITH REGULATIONS",
        "s3_title": "3. TECHNICAL CONFIGURATION FOR THE OBJECT",
        "s4_title": "4. ECONOMIC INDICATORS",
        "s5_title": "5. POSITION IN COMPARISON SET (5 LAYERS)",
        "s6_title": "6. STRENGTHS AND WEAKNESSES",
        "s7_title": "7. SUMMARY AND RECOMMENDATIONS",
        # Profile
        "country": "Country of origin",
        "founded": "Founded",
        "tier": "Price tier",
        "system_type": "System type",
        "warranty": "Warranty period",
        "months": "months",
        "with_extension": "(extended warranty available)",
        "ua_distributor": "Ukraine distributor",
        "service_coverage": "Service coverage",
        "response_time": "Response time",
        "manufacturer_label": "Manufacturer",
        "not_specified": "not specified",
        # Compliance
        "active_jurisdictions": "Active jurisdictions for this object",
        "overall_status": "Overall status",
        "compl_jurisdiction": "Jurisdiction",
        "compl_status": "Status",
        "compl_reasoning": "Reasoning",
        # Technical
        "object_label": "Object",
        "total_protected": "total protected area",
        "floors_label": "floors",
        "arch_npa": "Architecture: {n} independent control panels. Total used {addr} addresses for {sig} logical signals (architectural efficiency {eff}%).",
        "arch_simple": "Architecture: 1 panel ({panel}). Used {addr} addresses for {sig} logical signals (architectural efficiency {eff}%).",
        "tbl_npa_zone": "NPA zone",
        "tbl_panel": "Panel",
        "tbl_loops": "Loops",
        "tbl_addresses": "Addresses",
        "tbl_capex_uah": "CAPEX (UAH)",
        # Economics
        "capex_text": "CAPEX (equipment): {val:,.0f} UAH (excluding cabling, installation, VAT).",
        "tco_text": "TCO over {years} years: {val:,.0f} UAH. Detailed structure below.",
        # Position
        "position_score_not_avail": "5-layer scoring not available.",
        "position_text": "Position: {pos} of {total} feasible manufacturers. Overall: {score:.1f} of 100.",
        "tbl_layer": "Layer",
        "tbl_score": "Score",
        "tbl_reasoning": "Reasoning",
        "l1": "L1 CAPEX",
        "l2": "L2 Architecture",
        "l3": "L3 Functional",
        "l4": "L4 Operational",
        "l5": "L5 TCO",
        # Strengths
        "strengths_label": "Strengths:",
        "weaknesses_label": "Areas of attention:",
        # Summary
        "summary_unavailable": "Summary unavailable.",
        "summary_winner": "{name} — RECOMMENDED MANUFACTURER for this object (position 1 of {total}, overall {score:.1f}).",
        "summary_winner_explain": "The combined score shows the best balance of characteristics across all object criteria.",
        "summary_second": "{name} — second position of {total} (overall {score:.1f}, winner {winner_name} with {winner_score:.1f}). Gap: {diff:.1f} points.",
        "summary_lower": "{name} — position {pos} of {total} (overall {score:.1f}). Winner: {winner_name} with overall {winner_score:.1f}.",
        "summary_detail": "Detailed reasoning for each of the 5 layers can be found in section 5. The decision to accept this manufacturer as the primary should also consider organizational factors: brand trust, prior experience, availability of certified installers, agreement with client and general contractor.",
        "disclaimer": "Disclaimer: calculation is based on a base MVP model. Cabling, installation and commissioning works, VAT, and design services are not included. The final system architecture (number of panels, loop distribution, cable selection) is determined at the working design stage by a certified designer.",
    },
}


def L(lang: str, key: str, **kwargs) -> str:
    """Translate key with optional formatting"""
    template = L10N.get(lang, L10N["ua"]).get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


# ═══════════════════════════════════════════════════════════════════
# СТРУКТУРИ ДАНИХ MEMO
# ═══════════════════════════════════════════════════════════════════


class MemoSection(BaseModel):
    """Розділ меморандуму"""
    title: str
    content: list[str] = Field(default_factory=list)
    table_data: Optional[list[list[str]]] = None
    bullet_points: list[str] = Field(default_factory=list)


class Mode3Memo(BaseModel):
    """Повна структура меморандуму"""
    memo_id: str
    generated_at: str
    object_name: str
    manufacturer_id: str
    manufacturer_name: str
    language: str = "ua"
    
    title: str
    subtitle: str
    
    section_1_profile: MemoSection
    section_2_compliance: MemoSection
    section_3_technical: MemoSection
    section_4_economics: MemoSection
    section_5_position: MemoSection
    section_6_strengths_weaknesses: MemoSection
    section_7_summary: MemoSection


# ═══════════════════════════════════════════════════════════════════
# СЕКЦІЇ
# ═══════════════════════════════════════════════════════════════════


def _section_1_profile(mfr: Manufacturer, lang: str) -> MemoSection:
    s = MemoSection(title=L(lang, "s1_title"))
    
    name_label = mfr.name_en if lang == "en" else mfr.name_ua
    s.content.append(
        f"{L(lang, 'manufacturer_label')}: {name_label} ({mfr.name_en}). "
        f"{L(lang, 'country')}: {mfr.country_iso2}. "
        f"{L(lang, 'founded')}: {mfr.founded_year or L(lang, 'not_specified')}."
    )
    
    s.content.append(
        f"{L(lang, 'tier')}: {mfr.tier.value}. "
        f"{L(lang, 'system_type')}: {mfr.system_type.value}. "
        f"{L(lang, 'warranty')}: {mfr.warranty_months} {L(lang, 'months')}"
        + (f" {L(lang, 'with_extension')}" if mfr.extended_warranty_available else "") + "."
    )
    
    d = mfr.ua_distributor
    if d:
        cities_str = ", ".join(d.service_cities) if d.service_cities else L(lang, "not_specified")
        response_str = f"{d.response_time_hours}h" if d.response_time_hours else L(lang, "not_specified")
        s.content.append(
            f"{L(lang, 'ua_distributor')}: {d.company_name}. "
            f"{L(lang, 'service_coverage')}: {cities_str}. "
            f"{L(lang, 'response_time')}: {response_str}."
        )
    
    # Сертифікати
    cert_items = []
    if mfr.certifications.EU_EN54.status.value in ("full", "partial"):
        parts = ", ".join(mfr.certifications.EU_EN54.certified_parts or [])
        cert_items.append(f"EN 54: {parts}")
    if mfr.certifications.UA_DSTU_EN54.status.value == "full":
        cert_items.append("ДСТУ EN 54" if lang == "ua" else "DSTU EN 54 (Ukraine, full)")
    elif mfr.certifications.UA_DSTU_EN54.status.value == "in_process":
        cert_items.append("ДСТУ EN 54 (в процесі)" if lang == "ua" else "DSTU EN 54 (in progress)")
    if mfr.certifications.UK_BS_LPCB.status.value == "full":
        cert_items.append("BS 5839 / LPCB")
    if mfr.certifications.US_UL_FM.status.value == "full":
        cert_items.append("UL 864 / FM Approved")
    if mfr.certifications.iso_9001:
        cert_items.append(mfr.certifications.iso_9001)
    
    if cert_items:
        s.bullet_points = cert_items
    
    return s


def _section_2_compliance(mfr_result: ManufacturerResult, state: ObjectState, lang: str) -> MemoSection:
    s = MemoSection(title=L(lang, "s2_title"))
    
    juris_str = ", ".join(j.value for j in state.pre_object.jurisdictions)
    s.content.append(
        f"{L(lang, 'active_jurisdictions')}: {juris_str}. "
        f"{L(lang, 'overall_status')}: {mfr_result.compliance.overall_status.upper()}."
    )
    s.content.append(mfr_result.compliance.summary_message)
    
    table = [[L(lang, "compl_jurisdiction"), L(lang, "compl_status"), L(lang, "compl_reasoning")]]
    for jr in mfr_result.compliance.by_jurisdiction:
        table.append([
            jr.jurisdiction.value,
            jr.status.upper(),
            jr.reasoning[:100] + ("..." if len(jr.reasoning) > 100 else ""),
        ])
    s.table_data = table
    
    return s


def _section_3_technical(mfr_result: ManufacturerResult, state: ObjectState, lang: str) -> MemoSection:
    s = MemoSection(title=L(lang, "s3_title"))
    
    s.content.append(
        f"{L(lang, 'object_label')}: {state.object.object_type.value}, "
        f"{L(lang, 'total_protected')} {state.object.total_area_m2:,.0f} м², "
        f"{L(lang, 'floors_label')} {state.object.floors_above}+{state.object.floors_below}."
    )
    
    if mfr_result.allocation_npa:
        npa_alloc = mfr_result.allocation_npa
        s.content.append(L(
            lang, "arch_npa",
            n=npa_alloc.total_panels_count,
            addr=npa_alloc.total_addresses_used,
            sig=npa_alloc.total_logical_signals,
            eff=npa_alloc.architectural_efficiency_pct,
        ))
        
        table = [[
            L(lang, "tbl_npa_zone"),
            L(lang, "tbl_panel"),
            L(lang, "tbl_loops"),
            L(lang, "tbl_addresses"),
            L(lang, "tbl_capex_uah"),
        ]]
        for npa_a in npa_alloc.npa_zone_allocations:
            panel_name = npa_a.panel_choice.model_name if npa_a.panel_choice else "—"
            table.append([
                npa_a.npa_zone_name,
                panel_name,
                str(npa_a.required_loops),
                str(npa_a.addresses_used),
                f"{npa_a.capex_uah:,.0f}",
            ])
        s.table_data = table
    elif mfr_result.allocation_simple:
        alloc = mfr_result.allocation_simple
        panel_name = alloc.panels[0].model_name if alloc.panels else "—"
        s.content.append(L(
            lang, "arch_simple",
            panel=panel_name,
            addr=alloc.total_addresses_used,
            sig=alloc.total_logical_signals,
            eff=alloc.architectural_efficiency_pct,
        ))
    
    return s


def _section_4_economics(mfr_result: ManufacturerResult, state: ObjectState, lang: str) -> MemoSection:
    s = MemoSection(title=L(lang, "s4_title"))
    
    s.content.append(L(lang, "capex_text", val=mfr_result.capex_uah))
    
    if mfr_result.scores and mfr_result.scores.layer_5_tco:
        l5 = mfr_result.scores.layer_5_tco
        horizon = state.pre_object.lifetime_horizon.value
        horizon_str = {"short_3_5": "5", "medium_7_10": "10", "long_15_20": "15"}.get(horizon, "10")
        s.content.append(L(lang, "tco_text", years=horizon_str, val=l5.raw_value))
        s.bullet_points.append(l5.reasoning)
    
    return s


def _section_5_position(
    mfr_result: ManufacturerResult, all_results: list[ManufacturerResult], lang: str,
) -> MemoSection:
    s = MemoSection(title=L(lang, "s5_title"))
    
    if not mfr_result.scores:
        s.content.append(L(lang, "position_score_not_avail"))
        return s
    
    scores = mfr_result.scores
    
    eligible = [
        r for r in all_results
        if not r.excluded and r.scores and r.scores.overall_score is not None
    ]
    eligible.sort(key=lambda r: r.scores.overall_score, reverse=True)
    
    position = None
    for idx, r in enumerate(eligible, 1):
        if r.manufacturer_id == mfr_result.manufacturer_id:
            position = idx
            break
    
    total_eligible = len(eligible)
    
    if position and scores.overall_score:
        s.content.append(L(
            lang, "position_text",
            pos=position, total=total_eligible, score=scores.overall_score,
        ))
        if scores.overall_reasoning:
            s.content.append(scores.overall_reasoning)
    
    table = [[L(lang, "tbl_layer"), L(lang, "tbl_score"), L(lang, "tbl_reasoning")]]
    layer_data = [
        (L(lang, "l1"), scores.layer_1_capex),
        (L(lang, "l2"), scores.layer_2_architectural),
        (L(lang, "l3"), scores.layer_3_functional),
        (L(lang, "l4"), scores.layer_4_operational),
        (L(lang, "l5"), scores.layer_5_tco),
    ]
    for name, layer_score in layer_data:
        if layer_score:
            reasoning_short = layer_score.reasoning[:120] + (
                "..." if len(layer_score.reasoning) > 120 else ""
            )
            table.append([name, f"{layer_score.score:.1f}", reasoning_short])
    s.table_data = table
    
    return s


def _section_6_strengths_weaknesses(mfr: Manufacturer, lang: str) -> MemoSection:
    s = MemoSection(title=L(lang, "s6_title"))
    
    if mfr.notes_strengths:
        s.content.append(L(lang, "strengths_label"))
        s.bullet_points.extend(mfr.notes_strengths)
    
    if mfr.notes_weaknesses:
        s.content.append(L(lang, "weaknesses_label"))
        s.bullet_points.append("---")
        s.bullet_points.extend(mfr.notes_weaknesses)
    
    return s


def _section_7_summary(
    mfr_result: ManufacturerResult, all_results: list[ManufacturerResult],
    state: ObjectState, lang: str, catalog,
) -> MemoSection:
    s = MemoSection(title=L(lang, "s7_title"))
    
    if not mfr_result.scores or mfr_result.scores.overall_score is None:
        s.content.append(L(lang, "summary_unavailable"))
        return s
    
    overall = mfr_result.scores.overall_score
    eligible = [r for r in all_results if not r.excluded and r.scores]
    eligible.sort(key=lambda r: r.scores.overall_score or 0, reverse=True)
    
    position = next(
        (i for i, r in enumerate(eligible, 1)
         if r.manufacturer_id == mfr_result.manufacturer_id), None
    )
    
    # Локалізована мапа імен виробників
    name_map = {
        cm.manufacturer_id: (cm.name_en if lang == "en" else cm.name_ua)
        for cm in catalog.manufacturers
    }
    
    mfr_display = name_map.get(mfr_result.manufacturer_id, mfr_result.manufacturer_name)
    
    if position == 1:
        s.content.append(L(
            lang, "summary_winner",
            name=mfr_display, total=len(eligible), score=overall,
        ))
        s.content.append(L(lang, "summary_winner_explain"))
    elif position == 2:
        winner = eligible[0]
        winner_display = name_map.get(winner.manufacturer_id, winner.manufacturer_name)
        s.content.append(L(
            lang, "summary_second",
            name=mfr_display, total=len(eligible), score=overall,
            winner_name=winner_display,
            winner_score=winner.scores.overall_score,
            diff=winner.scores.overall_score - overall,
        ))
    else:
        winner = eligible[0]
        winner_display = name_map.get(winner.manufacturer_id, winner.manufacturer_name)
        s.content.append(L(
            lang, "summary_lower",
            name=mfr_display, pos=position, total=len(eligible), score=overall,
            winner_name=winner_display,
            winner_score=winner.scores.overall_score,
        ))
    
    s.content.append(L(lang, "summary_detail"))
    s.content.append(L(lang, "disclaimer"))
    
    return s


# ═══════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ
# ═══════════════════════════════════════════════════════════════════


def build_mode3_memo(
    calc_result: CalculationResult,
    target_manufacturer_id: str,
    catalog,
    state: ObjectState,
    language: str = "ua",
) -> Optional[Mode3Memo]:
    """Формує меморандум для одного виробника. language: "ua" або "en"."""
    
    mfr = next(
        (m for m in catalog.manufacturers if m.manufacturer_id == target_manufacturer_id),
        None,
    )
    mfr_result = next(
        (r for r in calc_result.manufacturer_results
         if r.manufacturer_id == target_manufacturer_id),
        None,
    )
    
    if not mfr or not mfr_result:
        return None
    
    object_label = state.object.additional_notes or state.session_id
    object_label_short = object_label[:60]
    
    # Локалізована назва виробника для титула
    mfr_display_name = mfr.name_en if language == "en" else mfr.name_ua
    
    memo = Mode3Memo(
        memo_id=f"memo_{calc_result.calculation_id}_{target_manufacturer_id}",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        object_name=object_label_short,
        manufacturer_id=target_manufacturer_id,
        manufacturer_name=mfr_display_name,
        language=language,
        title=f"{L(language, 'title_prefix')} {mfr_display_name.upper()}",
        subtitle=L(language, "subtitle", obj=object_label_short, ver=calc_result.engine_version),
        section_1_profile=_section_1_profile(mfr, language),
        section_2_compliance=_section_2_compliance(mfr_result, state, language),
        section_3_technical=_section_3_technical(mfr_result, state, language),
        section_4_economics=_section_4_economics(mfr_result, state, language),
        section_5_position=_section_5_position(mfr_result, calc_result.manufacturer_results, language),
        section_6_strengths_weaknesses=_section_6_strengths_weaknesses(mfr, language),
        section_7_summary=_section_7_summary(
            mfr_result, calc_result.manufacturer_results, state, language, catalog,
        ),
    )
    
    return memo
