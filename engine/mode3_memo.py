"""
MODE 3 — MANUFACTURER-SPECIFIC MEMORANDUM

Глибока аналітична записка по конкретному виробнику для конкретного об'єкта.
Збирає всі дані з результатів калькуляції в структурований документ, 
готовий до експорту в DOCX (через mode3_docx_exporter.py).

Структура меморандуму:
1. ТИТУЛ
2. ПРОФІЛЬ ВИРОБНИКА (країна, tier, гарантія, дистриб'ютор, certifications)
3. ВІДПОВІДНІСТЬ НОРМАТИВАМ (compliance по юрисдикціях)
4. ТЕХНІЧНА КОНФІГУРАЦІЯ (BOM + панелі + NPA архітектура)
5. ЕКОНОМІЧНІ ПОКАЗНИКИ (CAPEX, TCO 15р, breakdown)
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
# СТРУКТУРИ ДАНИХ MEMO
# ═══════════════════════════════════════════════════════════════════


class MemoSection(BaseModel):
    """Розділ меморандуму"""
    title: str
    content: list[str] = Field(default_factory=list)  # параграфи
    table_data: Optional[list[list[str]]] = None  # рядки таблиці (перший — заголовок)
    bullet_points: list[str] = Field(default_factory=list)


class Mode3Memo(BaseModel):
    """Повна структура меморандуму"""
    # Метадані
    memo_id: str
    generated_at: str
    object_name: str
    manufacturer_id: str
    manufacturer_name: str
    
    # Розділи
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
# ФУНКЦІЇ ФОРМУВАННЯ РОЗДІЛІВ
# ═══════════════════════════════════════════════════════════════════


def _section_1_profile(mfr: Manufacturer) -> MemoSection:
    """Розділ 1: Профіль виробника"""
    s = MemoSection(title="1. ПРОФІЛЬ ВИРОБНИКА")
    
    s.content.append(
        f"Виробник: {mfr.name_ua} ({mfr.name_en}). "
        f"Країна походження: {mfr.country_iso2}. "
        f"Рік заснування: {mfr.founded_year or 'не вказано'}."
    )
    
    s.content.append(
        f"Ціновий сегмент: {mfr.tier.value}. "
        f"Тип системи: {mfr.system_type.value}. "
        f"Гарантійний термін: {mfr.warranty_months} місяців"
        + (" (з можливістю продовження)" if mfr.extended_warranty_available else "") + "."
    )
    
    # Дистриб'ютор
    d = mfr.ua_distributor
    if d:
        cities_str = ", ".join(d.service_cities) if d.service_cities else "не вказано"
        response_str = f"{d.response_time_hours}h" if d.response_time_hours else "не вказано"
        s.content.append(
            f"UA-дистриб'ютор: {d.company_name}. "
            f"Сервісне покриття: {cities_str}. "
            f"Час реакції на виклик: {response_str}."
        )
    
    # Сертифікати
    cert_items = []
    if mfr.certifications.EU_EN54.status.value in ("full", "partial"):
        parts = ", ".join(mfr.certifications.EU_EN54.certified_parts or [])
        cert_items.append(f"EN 54: {parts}")
    if mfr.certifications.UA_DSTU_EN54.status.value == "full":
        cert_items.append("ДСТУ EN 54 (повна)")
    elif mfr.certifications.UA_DSTU_EN54.status.value == "in_process":
        cert_items.append("ДСТУ EN 54 (в процесі)")
    if mfr.certifications.UK_BS_LPCB.status.value == "full":
        cert_items.append("BS 5839 / LPCB")
    if mfr.certifications.US_UL_FM.status.value == "full":
        cert_items.append("UL 864 / FM Approved")
    if mfr.certifications.iso_9001:
        cert_items.append(mfr.certifications.iso_9001)
    
    if cert_items:
        s.bullet_points = cert_items
    
    return s


def _section_2_compliance(mfr_result: ManufacturerResult, state: ObjectState) -> MemoSection:
    """Розділ 2: Відповідність нормативам"""
    s = MemoSection(title="2. ВІДПОВІДНІСТЬ НОРМАТИВНИМ ВИМОГАМ")
    
    juris_str = ", ".join(j.value for j in state.pre_object.jurisdictions)
    s.content.append(
        f"Активні юрисдикції для цього об'єкта: {juris_str}. "
        f"Загальний статус: {mfr_result.compliance.overall_status.upper()}."
    )
    s.content.append(mfr_result.compliance.summary_message)
    
    # Таблиця по юрисдикціях
    table = [["Юрисдикція", "Статус", "Обґрунтування"]]
    for jr in mfr_result.compliance.by_jurisdiction:
        table.append([
            jr.jurisdiction.value,
            jr.status.upper(),
            jr.reasoning[:100] + ("..." if len(jr.reasoning) > 100 else ""),
        ])
    s.table_data = table
    
    return s


def _section_3_technical(mfr_result: ManufacturerResult, state: ObjectState) -> MemoSection:
    """Розділ 3: Технічна конфігурація"""
    s = MemoSection(title="3. ТЕХНІЧНА КОНФІГУРАЦІЯ ДЛЯ ОБ'ЄКТА")
    
    s.content.append(
        f"Об'єкт: {state.object.object_type.value}, "
        f"загальна захищувана площа {state.object.total_area_m2:,.0f} м², "
        f"поверховість {state.object.floors_above}+{state.object.floors_below}."
    )
    
    # Якщо NPA — деталі по зонах
    if mfr_result.allocation_npa:
        npa_alloc = mfr_result.allocation_npa
        s.content.append(
            f"Архітектура: {npa_alloc.total_panels_count} незалежних ППКП. "
            f"Загалом використано {npa_alloc.total_addresses_used} адрес "
            f"для {npa_alloc.total_logical_signals} логічних сигналів "
            f"(архітектурна ефективність {npa_alloc.architectural_efficiency_pct}%)."
        )
        
        # Таблиця ППКП
        table = [["NPA-зона", "Панель", "Шлейфів", "Адрес", "CAPEX (₴)"]]
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
        s.content.append(
            f"Архітектура: 1 ППКП ({panel_name}). "
            f"Використано {alloc.total_addresses_used} адрес "
            f"для {alloc.total_logical_signals} логічних сигналів "
            f"(архітектурна ефективність {alloc.architectural_efficiency_pct}%)."
        )
    
    return s


def _section_4_economics(
    mfr_result: ManufacturerResult, state: ObjectState
) -> MemoSection:
    """Розділ 4: Економічні показники"""
    s = MemoSection(title="4. ЕКОНОМІЧНІ ПОКАЗНИКИ")
    
    s.content.append(
        f"CAPEX (обладнання): {mfr_result.capex_uah:,.0f} ₴ "
        f"(без кабельної продукції, монтажних робіт, ПДВ)."
    )
    
    # TCO
    if mfr_result.scores and mfr_result.scores.layer_5_tco:
        l5 = mfr_result.scores.layer_5_tco
        horizon = state.pre_object.lifetime_horizon.value
        horizon_str = {"short_3_5": "5", "medium_7_10": "10", "long_15_20": "15"}.get(horizon, "10")
        s.content.append(
            f"TCO за {horizon_str} років: {l5.raw_value:,.0f} ₴. "
            f"Детальна структура нижче."
        )
        # Деталі TCO в bullets
        s.bullet_points.append(l5.reasoning)
    
    return s


def _section_5_position(
    mfr_result: ManufacturerResult, all_results: list[ManufacturerResult],
) -> MemoSection:
    """Розділ 5: Позиція в comparison-set"""
    s = MemoSection(title="5. ПОЗИЦІЯ В COMPARISON-SET (5 ШАРІВ)")
    
    if not mfr_result.scores:
        s.content.append("Оцінка за 5 шарами недоступна.")
        return s
    
    scores = mfr_result.scores
    
    # Знайдемо позицію
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
        s.content.append(
            f"Позиція: {position} з {total_eligible} feasible виробників. "
            f"Overall: {scores.overall_score:.1f} з 100."
        )
        if scores.overall_reasoning:
            s.content.append(scores.overall_reasoning)
    
    # Таблиця по шарах
    table = [["Шар", "Бал", "Обґрунтування"]]
    layer_data = [
        ("L1 CAPEX", scores.layer_1_capex),
        ("L2 Архітектура", scores.layer_2_architectural),
        ("L3 Функціонал", scores.layer_3_functional),
        ("L4 Експлуатація", scores.layer_4_operational),
        ("L5 TCO", scores.layer_5_tco),
    ]
    for name, layer_score in layer_data:
        if layer_score:
            reasoning_short = layer_score.reasoning[:120] + (
                "..." if len(layer_score.reasoning) > 120 else ""
            )
            table.append([
                name,
                f"{layer_score.score:.1f}",
                reasoning_short,
            ])
    s.table_data = table
    
    return s


def _section_6_strengths_weaknesses(mfr: Manufacturer) -> MemoSection:
    """Розділ 6: Сильні і слабкі сторони"""
    s = MemoSection(title="6. СИЛЬНІ ТА СЛАБКІ СТОРОНИ")
    
    if mfr.notes_strengths:
        s.content.append("Сильні сторони:")
        s.bullet_points.extend(mfr.notes_strengths)
    
    if mfr.notes_weaknesses:
        s.content.append("Зони уваги:")
        s.bullet_points.append("---")
        s.bullet_points.extend(mfr.notes_weaknesses)
    
    return s


def _section_7_summary(
    mfr_result: ManufacturerResult, all_results: list[ManufacturerResult],
    state: ObjectState,
) -> MemoSection:
    """Розділ 7: Резюме і рекомендації"""
    s = MemoSection(title="7. РЕЗЮМЕ ТА РЕКОМЕНДАЦІЇ")
    
    if not mfr_result.scores or mfr_result.scores.overall_score is None:
        s.content.append("Резюме недоступне.")
        return s
    
    overall = mfr_result.scores.overall_score
    eligible = [r for r in all_results if not r.excluded and r.scores]
    eligible.sort(key=lambda r: r.scores.overall_score or 0, reverse=True)
    
    position = next(
        (i for i, r in enumerate(eligible, 1)
         if r.manufacturer_id == mfr_result.manufacturer_id), None
    )
    
    if position == 1:
        s.content.append(
            f"{mfr_result.manufacturer_name} — РЕКОМЕНДОВАНИЙ ВИРОБНИК для цього об'єкта "
            f"(позиція 1 з {len(eligible)}, overall {overall:.1f})."
        )
        s.content.append(
            "Зведена оцінка системи показує найкраще співвідношення характеристик "
            "за всією сукупністю критеріїв об'єкта."
        )
    elif position == 2:
        winner = eligible[0]
        s.content.append(
            f"{mfr_result.manufacturer_name} — друга позиція з {len(eligible)} "
            f"(overall {overall:.1f}, переможець {winner.manufacturer_name} з {winner.scores.overall_score:.1f}). "
            f"Різниця: {winner.scores.overall_score - overall:.1f} балів."
        )
    else:
        winner = eligible[0]
        s.content.append(
            f"{mfr_result.manufacturer_name} — {position}-а позиція з {len(eligible)} "
            f"(overall {overall:.1f}). Переможець: {winner.manufacturer_name} "
            f"з overall {winner.scores.overall_score:.1f}."
        )
    
    s.content.append(
        "Деталізовані обґрунтування за кожним з 5 шарів див. у розділі 5. "
        "Рішення про прийняття цього виробника як основного має враховувати також "
        "організаційні фактори: довіра до бренду, попередній досвід, наявність сертифікованих "
        "інсталяторів, узгодження з замовником і генпідрядником."
    )
    
    # Дисклеймер
    s.content.append(
        "Дисклеймер: розрахунок виконано на основі базової моделі MVP. "
        "Не враховано вартість кабельної продукції, монтажних і пуско-налагоджувальних робіт, "
        "ПДВ, проектних послуг. Кінцева архітектура системи (кількість ППКП, розподіл шлейфів, "
        "вибір кабелю) визначається на стадії робочого проекту сертифікованим проектувальником."
    )
    
    return s


# ═══════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ — ФОРМУЄ ПОВНИЙ МЕМОРАНДУМ
# ═══════════════════════════════════════════════════════════════════


def build_mode3_memo(
    calc_result: CalculationResult,
    target_manufacturer_id: str,
    catalog,
    state: ObjectState,
) -> Optional[Mode3Memo]:
    """
    Формує меморандум для одного виробника на основі результату калькуляції.
    
    Повертає None, якщо виробник не знайдений у результаті.
    """
    # Знайдемо виробника
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
    
    memo = Mode3Memo(
        memo_id=f"memo_{calc_result.calculation_id}_{target_manufacturer_id}",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        object_name=object_label_short,
        manufacturer_id=target_manufacturer_id,
        manufacturer_name=mfr.name_ua,
        title=f"АНАЛІТИЧНИЙ МЕМОРАНДУМ ПО ВИРОБНИКУ {mfr.name_ua.upper()}",
        subtitle=f"Об'єкт: {object_label_short} | Згенеровано: FireCompare {calc_result.engine_version}",
        section_1_profile=_section_1_profile(mfr),
        section_2_compliance=_section_2_compliance(mfr_result, state),
        section_3_technical=_section_3_technical(mfr_result, state),
        section_4_economics=_section_4_economics(mfr_result, state),
        section_5_position=_section_5_position(mfr_result, calc_result.manufacturer_results),
        section_6_strengths_weaknesses=_section_6_strengths_weaknesses(mfr),
        section_7_summary=_section_7_summary(
            mfr_result, calc_result.manufacturer_results, state,
        ),
    )
    
    return memo
