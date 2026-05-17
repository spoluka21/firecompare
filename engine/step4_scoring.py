"""
КРОК 4. П'ятишарова система оцінки виробників

Кожен виробник отримує бали (0-100) за п'ятьма шарами:
  Layer 1 — CAPEX (капітальні витрати)
  Layer 2 — Архітектурний податок (ефективність адрес)
  Layer 3 — Функціональний рівень (наявність функцій)
  Layer 4 — Експлуатаційні характеристики (гарантія, сервіс)
  Layer 5 — TCO 10/15 років (повна вартість володіння)

Принципи:
- Бал 0-100, де 100 — найкращий результат у comparison-set
- Кожен бал супроводжується reasoning (для прозорості клієнту)
- ВСІ шари використовують ВІДНОСНУ шкалу — точка відліку 100 = найкращий 
  виробник у поточному comparison-set. Це дає максимальну розрізнюваність 
  навіть при близьких значеннях.
- Для абсолютних метрик (як архітектурна ефективність) reasoning містить 
  і відносну позицію (100/N балів), і абсолютне значення (133.7%)

ПОТОЧНА РЕАЛІЗАЦІЯ: Layer 1, Layer 2.
Layer 3-5 — у наступних сесіях.

ОНОВЛЕНО: підтримка як Allocation (single-panel), так і MultiPanelAllocation (NPA).
Через нормалізацію вхідних даних у єдиний словник.
"""
from typing import Union

from pydantic import BaseModel, Field

from engine.step2_allocation import Allocation
from engine.step2_npa_allocation import MultiPanelAllocation
from schemas.catalog import Manufacturer


# Уніфікований тип для функцій scoring — приймаємо обидва різновиди
AllocationLike = Union[Allocation, MultiPanelAllocation]


def _normalize_allocation(alloc: AllocationLike) -> dict:
    """
    Нормалізує Allocation або MultiPanelAllocation у спільний словник
    з ключами: capex, addresses, signals, eff, feasible.
    
    Це дозволяє Step 4 працювати з обома типами без різного коду.
    """
    return {
        "manufacturer_id": alloc.manufacturer_id,
        "capex": alloc.total_capex_uah,
        "addresses": alloc.total_addresses_used,
        "signals": alloc.total_logical_signals,
        "eff": alloc.architectural_efficiency_pct,
        "feasible": alloc.feasible,
    }


# ═══════════════════════════════════════════════════════════════════
# СТРУКТУРИ ДАНИХ
# ═══════════════════════════════════════════════════════════════════


class LayerScore(BaseModel):
    """Бал одного шару"""
    score: float = Field(ge=0, le=100)
    reasoning: str
    raw_value: float | None = None  # вихідне числове значення (для довідки)
    unit: str | None = None  # одиниця виміру (UAH, %, тощо)


class ManufacturerScores(BaseModel):
    """Усі 5 шарів для одного виробника + overall"""
    manufacturer_id: str
    layer_1_capex: LayerScore
    layer_2_architectural: LayerScore
    layer_3_functional: LayerScore | None = None
    layer_4_operational: LayerScore | None = None
    layer_5_tco: LayerScore | None = None
    
    # Зведений показник (заповнюється коли всі 5 шарів обчислені)
    overall_score: float | None = None
    overall_reasoning: str | None = None
    applied_weights: dict[str, float] | None = None


# ═══════════════════════════════════════════════════════════════════
# LAYER 1 — CAPEX
# ═══════════════════════════════════════════════════════════════════
#
# Принцип: бал обернений до вартості. Найдешевший = 100, найдорожчий менше.
# Формула: score = 100 × (cheapest / this)^0.5
# 
# Чому квадратний корінь — щоб різниця в ціні не давала надмірно жорсткого 
# покарання. Наприклад, при різниці у 2× ціни — другий отримує 71 (а не 50).
# Це робить шкалу адекватнішою для реальних виробничих систем, де різниця 
# в ціні до 2× — звичайна справа і не означає «вдвічі гірше».
# ═══════════════════════════════════════════════════════════════════


def score_layer_1_capex(
    allocations: dict[str, AllocationLike],
) -> dict[str, LayerScore]:
    """
    Розраховує Layer 1 для всіх виробників у comparison-set одночасно.
    
    Працює з Allocation і MultiPanelAllocation (через _normalize_allocation).
    """
    scores: dict[str, LayerScore] = {}
    
    # Нормалізуємо вхідні дані
    normalized = {mfr_id: _normalize_allocation(a) for mfr_id, a in allocations.items()}
    
    # Беремо тільки тих, у кого є валідна ціна
    priced = {mfr_id: n for mfr_id, n in normalized.items() if n["capex"] > 0}
    
    if not priced:
        for mfr_id, n in normalized.items():
            scores[mfr_id] = LayerScore(
                score=50.0,
                reasoning=(
                    "Точні ціни не зафіксовано в каталозі (preliminary). "
                    "Виставлено нейтральний бал 50 — буде уточнено після збору цін від дистриб'юторів."
                ),
                raw_value=n["capex"],
                unit="UAH",
            )
        return scores
    
    cheapest = min(n["capex"] for n in priced.values())
    
    for mfr_id, n in normalized.items():
        if n["capex"] == 0:
            scores[mfr_id] = LayerScore(
                score=50.0,
                reasoning=(
                    "Ціни на компоненти не зафіксовано в каталозі. "
                    f"Виставлено нейтральний бал 50. Для порівняння: найдешевший — "
                    f"{cheapest:,.0f} UAH."
                ),
                raw_value=0,
                unit="UAH",
            )
            continue
        
        ratio = cheapest / n["capex"]
        score = round(100 * (ratio ** 0.5), 1)
        
        if n["capex"] == cheapest:
            reasoning = f"Найдешевший CAPEX у comparison-set: {n['capex']:,.0f} UAH."
        else:
            premium_pct = round((n["capex"] / cheapest - 1) * 100, 1)
            reasoning = (
                f"CAPEX {n['capex']:,.0f} UAH — на {premium_pct}% вище "
                f"за найдешевший варіант ({cheapest:,.0f} UAH)."
            )
        
        scores[mfr_id] = LayerScore(
            score=score,
            reasoning=reasoning,
            raw_value=n["capex"],
            unit="UAH",
        )
    
    return scores


# ═══════════════════════════════════════════════════════════════════
# LAYER 2 — АРХІТЕКТУРНИЙ ПОДАТОК
# ═══════════════════════════════════════════════════════════════════
#
# Це АБСОЛЮТНА метрика, не відносна. Формула вже обчислена в Allocation:
#   architectural_efficiency_pct = 100 * logical_signals / addresses_used
#
# Бал = min(100, efficiency_pct) — обмежуємо стелею 100, бо понад 100% 
# означає, що combined-модулі дають більше сигналів на адресу, що ефективніше 
# за 1:1, але для шкали зручніше мати стелю.
# ═══════════════════════════════════════════════════════════════════


def score_layer_2_architectural(
    allocations: dict[str, AllocationLike],
) -> dict[str, LayerScore]:
    """
    Layer 2 — архітектурна ефективність використання адрес.
    
    ВІДНОСНА ШКАЛА: найефективніший виробник у comparison-set отримує 100.
    Решта — пропорційно до нього.
    
    Формула: score = (efficiency / max_efficiency_in_set) × 100
    """
    scores: dict[str, LayerScore] = {}
    
    if not allocations:
        return scores
    
    # Нормалізуємо
    normalized = {mfr_id: _normalize_allocation(a) for mfr_id, a in allocations.items()}
    
    best_eff = max(n["eff"] for n in normalized.values())
    
    if best_eff == 0:
        for mfr_id in allocations:
            scores[mfr_id] = LayerScore(
                score=50.0,
                reasoning="Не вдалося обчислити архітектурну ефективність.",
                raw_value=0,
                unit="%",
            )
        return scores
    
    for mfr_id, n in normalized.items():
        eff = n["eff"]
        score = round(100 * eff / best_eff, 1)
        
        if eff >= 100:
            descriptor = "оптимальна архітектура"
        elif eff >= 80:
            descriptor = "ефективна архітектура"
        elif eff >= 60:
            descriptor = "помірний архітектурний податок"
        else:
            descriptor = "високий архітектурний податок"
        
        if eff == best_eff:
            comparison_note = "Найкраща ефективність у comparison-set — еталон (100 балів)."
        else:
            delta_pct = round((best_eff - eff) / best_eff * 100, 1)
            comparison_note = (
                f"На {delta_pct}% нижче за еталон ({best_eff:.1f}% у найкращого) "
                f"у comparison-set."
            )
        
        reasoning = (
            f"{descriptor.capitalize()}: {n['signals']} логічних сигналів "
            f"на {n['addresses']} адрес = {eff}% абсолютна ефективність. "
            f"{comparison_note}"
        )
        
        scores[mfr_id] = LayerScore(
            score=score,
            reasoning=reasoning,
            raw_value=eff,
            unit="%",
        )
    
    return scores


# ═══════════════════════════════════════════════════════════════════
# LAYER 3 — ФУНКЦІОНАЛЬНИЙ РІВЕНЬ
# ═══════════════════════════════════════════════════════════════════
#
# Оцінюємо функціональні характеристики виробника як сукупність:
# захист від хибних, хмарний моніторинг, мобільний застосунок, BMS,
# voice alarm, бездротове розширення, резервування.
#
# Кожна функція має:
# - feature_score 0-100 (наявність + якість реалізації)
# - вагу важливості (адаптується до пре-об'єктних відповідей у Step 5)
#
# Layer 3 score = середньозважений
# ═══════════════════════════════════════════════════════════════════


from schemas.catalog import (
    BMSIntegration, CloudMonitoring, FalseAlarmLevel, FeatureSupport,
    Features, MobileApp, Redundancy,
)
from schemas.object_state import ObjectState, TriState


def _score_false_alarm(level: FalseAlarmLevel) -> tuple[float, str]:
    """0-100 бал за рівень захисту від хибних"""
    if level == FalseAlarmLevel.PREMIUM:
        return 100, "преміум алгоритми (drift compensation, multi-sensor fusion)"
    if level == FalseAlarmLevel.ENHANCED:
        return 70, "покращений (адаптивні пороги)"
    return 40, "базовий (за ДСТУ EN 54)"


def _score_cloud(cloud: CloudMonitoring) -> tuple[float, str]:
    if cloud.available:
        return 100, f"native хмарна платформа ({cloud.platform_name or 'без назви'})"
    return 0, "хмарний моніторинг відсутній"


def _score_mobile(mobile: MobileApp) -> tuple[float, str]:
    if mobile.available:
        return 100, f"мобільний застосунок ({', '.join(mobile.platforms) if mobile.platforms else 'iOS/Android'})"
    return 0, "мобільний застосунок відсутній"


def _score_bms(bms: BMSIntegration) -> tuple[float, str]:
    """Берем найкращий результат з усіх протоколів"""
    protocols = {
        "BACnet": bms.bacnet, "Modbus RTU": bms.modbus_rtu,
        "Modbus TCP": bms.modbus_tcp, "OPC UA": bms.opc_ua, "KNX": bms.knx,
    }
    has_native = [p for p, s in protocols.items() if s == FeatureSupport.NATIVE]
    has_gateway = [p for p, s in protocols.items() if s == FeatureSupport.GATEWAY]
    has_partner = [p for p, s in protocols.items() if s == FeatureSupport.PARTNER]
    
    if has_native:
        return 100, f"native BMS ({', '.join(has_native[:3])})"
    if has_gateway:
        return 60, f"BMS через шлюз ({', '.join(has_gateway[:3])})"
    if has_partner:
        return 40, f"BMS через партнера ({', '.join(has_partner[:3])})"
    return 0, "BMS інтеграція відсутня"


def _score_voice_alarm(va: FeatureSupport) -> tuple[float, str]:
    if va == FeatureSupport.NATIVE:
        return 100, "native voice alarm"
    if va == FeatureSupport.PARTNER:
        return 70, "voice alarm через сертифікованого партнера"
    if va == FeatureSupport.GATEWAY:
        return 50, "voice alarm через шлюз"
    return 0, "voice alarm не підтримується"


def _score_wireless(wireless: bool) -> tuple[float, str]:
    if wireless:
        return 100, "бездротове розширення (EN 54-25)"
    return 0, "тільки провідне підключення"


def _score_redundancy(r: Redundancy) -> tuple[float, str]:
    """Сума балів за різні рівні резервування"""
    pts = 0
    items = []
    if r.panel_controller:
        pts += 40
        items.append("контролер панелі")
    if r.network:
        pts += 30
        items.append("мережа")
    if r.loop:
        pts += 30
        items.append("петлі (ізолятори)")
    if not items:
        return 0, "резервування відсутнє"
    return pts, f"резервування: {', '.join(items)}"


# Базові ваги — пере-калібруються у Step 5 на основі пре-об'єктних відповідей
DEFAULT_FEATURE_WEIGHTS = {
    "false_alarm": 0.20,
    "cloud": 0.15,
    "mobile": 0.10,
    "bms": 0.15,
    "voice_alarm": 0.10,
    "wireless": 0.05,
    "redundancy": 0.25,
}


def _compute_feature_weights(state: ObjectState) -> dict[str, float]:
    """
    Адаптація ваг функцій під пре-об'єктні відповіді клієнта.
    Якщо клієнт явно потребує функцію — її вага збільшується;
    якщо не потребує — зменшується.
    Сума ваг нормалізується до 1.0.
    """
    weights = dict(DEFAULT_FEATURE_WEIGHTS)
    pre = state.pre_object
    
    # False alarm
    if pre.false_alarm_protection.value == "premium":
        weights["false_alarm"] = 0.35
    
    # Cloud
    if pre.cloud_monitoring_required == TriState.YES:
        weights["cloud"] = 0.25
    elif pre.cloud_monitoring_required == TriState.NO:
        weights["cloud"] = 0.05
    
    # Mobile
    if pre.mobile_app_required == TriState.YES:
        weights["mobile"] = 0.20
    elif pre.mobile_app_required == TriState.NO:
        weights["mobile"] = 0.02
    
    # BMS
    if pre.bms_integration_required == TriState.YES:
        weights["bms"] = 0.25
    elif pre.bms_integration_required == TriState.NO:
        weights["bms"] = 0.05
    
    # Нормалізація — щоб сума була 1.0
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def score_layer_3_functional(
    manufacturers: dict[str, Manufacturer],
    state: ObjectState,
) -> dict[str, LayerScore]:
    """
    Layer 3 — функціональний рівень виробника.
    Зважена сума за функціональними характеристиками.
    """
    scores: dict[str, LayerScore] = {}
    
    weights = _compute_feature_weights(state)
    
    # Зберемо абсолютні бали для всіх виробників
    abs_scores = {}
    detail_per_mfr = {}
    
    for mfr_id, mfr in manufacturers.items():
        f = mfr.features
        
        fa_score, fa_note = _score_false_alarm(f.false_alarm_level)
        cloud_score, cloud_note = _score_cloud(f.cloud_monitoring)
        mob_score, mob_note = _score_mobile(f.mobile_app)
        bms_score, bms_note = _score_bms(f.bms_integration)
        va_score, va_note = _score_voice_alarm(f.voice_alarm)
        wl_score, wl_note = _score_wireless(f.wireless_extension)
        red_score, red_note = _score_redundancy(f.redundancy)
        
        weighted = (
            weights["false_alarm"] * fa_score +
            weights["cloud"] * cloud_score +
            weights["mobile"] * mob_score +
            weights["bms"] * bms_score +
            weights["voice_alarm"] * va_score +
            weights["wireless"] * wl_score +
            weights["redundancy"] * red_score
        )
        abs_scores[mfr_id] = round(weighted, 1)
        detail_per_mfr[mfr_id] = {
            "Захист від хибних": (fa_score, fa_note, weights["false_alarm"]),
            "Хмара": (cloud_score, cloud_note, weights["cloud"]),
            "Мобільний": (mob_score, mob_note, weights["mobile"]),
            "BMS": (bms_score, bms_note, weights["bms"]),
            "Voice alarm": (va_score, va_note, weights["voice_alarm"]),
            "Бездрот": (wl_score, wl_note, weights["wireless"]),
            "Резервування": (red_score, red_note, weights["redundancy"]),
        }
    
    if not abs_scores:
        return scores
    
    # Відносна шкала: найкращий = 100
    best_abs = max(abs_scores.values())
    
    for mfr_id, abs_score in abs_scores.items():
        if best_abs > 0:
            rel_score = round(100 * abs_score / best_abs, 1)
        else:
            rel_score = 50.0
        
        # Reasoning — топ-3 функції з найбільшим внеском
        contributions = []
        for fname, (fscore, fnote, fweight) in detail_per_mfr[mfr_id].items():
            contributions.append((fname, fscore * fweight, fnote))
        contributions.sort(key=lambda x: x[1], reverse=True)
        top_3 = contributions[:3]
        
        reasoning = (
            f"Функціональний рівень: {abs_score} / 100 (абс.), {rel_score} (відн. до еталону {best_abs}). "
            f"Топ внески: {', '.join(f'{name} ({score:.1f})' for name, score, _ in top_3)}."
        )
        
        scores[mfr_id] = LayerScore(
            score=rel_score,
            reasoning=reasoning,
            raw_value=abs_score,
            unit="балів",
        )
    
    return scores


# ═══════════════════════════════════════════════════════════════════
# LAYER 4 — ЕКСПЛУАТАЦІЙНІ ХАРАКТЕРИСТИКИ
# ═══════════════════════════════════════════════════════════════════
#
# Оцінюємо: гарантія, наявність UA-дистриб'ютора, сервісна мережа,
# час реакції, можливість продовженої гарантії.
# ═══════════════════════════════════════════════════════════════════


def score_layer_4_operational(
    manufacturers: dict[str, Manufacturer],
) -> dict[str, LayerScore]:
    """
    Layer 4 — експлуатаційні характеристики.
    
    Враховує:
    - Гарантійний термін (місяці)
    - Можливість продовженої гарантії
    - Покриття UA сервісною мережею (кількість міст)
    - Час реакції на запчастини
    """
    abs_scores = {}
    details = {}
    
    for mfr_id, mfr in manufacturers.items():
        # Гарантія: 24 міс = 60 балів, 36 міс = 80, 48+ = 100
        warranty_score = min(100, mfr.warranty_months * 2.5)
        
        # Продовжена гарантія: +10 балів
        extended_bonus = 10 if mfr.extended_warranty_available else 0
        
        # Сервісне покриття: міст у UA × 10, до 50 балів
        cities_count = len(mfr.ua_distributor.service_cities) if mfr.ua_distributor.service_cities else 0
        service_score = min(50, cities_count * 10)
        
        # Час реакції: <24h = 50, 24-48h = 30, >48h = 10
        response = mfr.ua_distributor.response_time_hours
        if response is None:
            response_score = 20
        elif response <= 24:
            response_score = 50
        elif response <= 48:
            response_score = 30
        else:
            response_score = 10
        
        # Зважена сума з нормалізацією до 100
        # warranty 40%, extended 5%, service 30%, response 25%
        total = (
            warranty_score * 0.40 +
            extended_bonus * 0.05 +
            service_score * 0.30 / 50 * 100 +  # масштабую 0-50 → 0-100
            response_score * 0.25 / 50 * 100   # 0-50 → 0-100
        )
        abs_scores[mfr_id] = round(total, 1)
        details[mfr_id] = {
            "warranty": (warranty_score, mfr.warranty_months),
            "extended": extended_bonus,
            "service": (service_score, cities_count),
            "response": (response_score, response),
        }
    
    if not abs_scores:
        return {}
    
    best_abs = max(abs_scores.values())
    
    scores = {}
    for mfr_id, abs_score in abs_scores.items():
        rel_score = round(100 * abs_score / best_abs, 1) if best_abs > 0 else 50.0
        d = details[mfr_id]
        
        reasoning = (
            f"Експлуатація: гарантія {d['warranty'][1]} міс., "
            f"{d['service'][1]} міст сервісу, "
            f"реакція {d['response'][1] or '?'}h. "
            f"Бал: {abs_score}/100 (абс.), {rel_score} (відн.)."
        )
        
        scores[mfr_id] = LayerScore(
            score=rel_score,
            reasoning=reasoning,
            raw_value=abs_score,
            unit="балів",
        )
    
    return scores


# ═══════════════════════════════════════════════════════════════════
# LAYER 5 — TCO (TOTAL COST OF OWNERSHIP) 10/15 РОКІВ
# ═══════════════════════════════════════════════════════════════════
#
# Спрощена модель TCO для MVP, доповнена реалістичними операційними витратами:
#
# TCO = CAPEX
#     + operating_costs (з урахуванням алгоритмічної знижки)
#     + battery_replacement
#     + false_alarm_costs (вартість виїздів за хибних тривог)
#     + cleaning_costs (очищення детекторів — для брендів без лабіринтних корпусів)
#
# Operating costs:
#   Base: UA 3%, EU 4%
#   PREMIUM (алгоритмічна детекція): -50% знижка → ~1.5-2%
#     (адаптивний моніторинг + remote diagnostics + drift compensation)
#   BASIC: +0.5% (більше виїздів через хибні)
#
# False alarms:
#   PREMIUM: ~0.5% хибних/рік на детектор
#   ENHANCED: ~2%
#   BASIC: ~5%
#   Вартість 1 хибної: 5000 ₴ (штраф + час техніка)
#
# Cleaning (тільки для UA-брендів і brands without лабіринт-корпусом):
#   Cofem A50S/A50SI/A50H — лабіринтні корпуси, очищення НЕ ПОТРІБНЕ
#   Інші: 1.5 разів/рік × 60 ₴/детектор
#
# Battery: ~5% від CAPEX кожні 5 років
#
# Horizon з пре-об'єктних відповідей: short/medium/long → 5/10/15 років
# ═══════════════════════════════════════════════════════════════════


# Параметри моделі TCO (in-code, у v0.2 → YAML)
FALSE_ALARM_RATES_PER_DETECTOR_PER_YEAR = {
    FalseAlarmLevel.PREMIUM: 0.005,   # 0.5%
    FalseAlarmLevel.ENHANCED: 0.020,  # 2%
    FalseAlarmLevel.BASIC: 0.050,     # 5%
}
COST_PER_FALSE_ALARM_UAH = 5000  # штраф + час + транспорт
CLEANING_COST_PER_DETECTOR_UAH = 60  # пилосмок + час техніка
CLEANINGS_PER_YEAR = 1.5  # типово для адресних димових

# Алгоритмічна знижка на ТО (адаптивний моніторинг + remote diagnostics)
ALGORITHMIC_MAINTENANCE_DISCOUNT = 0.50  # 50% від базового


def score_layer_5_tco(
    manufacturers: dict[str, Manufacturer],
    allocations: dict[str, AllocationLike],
    state: ObjectState,
) -> dict[str, LayerScore]:
    """
    Layer 5 — TCO за горизонт експлуатації з реалістичними операційними витратами.
    
    Менший TCO = вищий бал.
    """
    horizon_map = {"short_3_5": 5, "medium_7_10": 10, "long_15_20": 15}
    horizon_years = horizon_map.get(state.pre_object.lifetime_horizon.value, 10)
    
    abs_tco = {}
    breakdowns = {}
    
    for mfr_id, alloc in allocations.items():
        mfr = manufacturers.get(mfr_id)
        if not mfr:
            continue
        
        normalized = _normalize_allocation(alloc)
        capex = normalized["capex"]
        
        if capex == 0:
            abs_tco[mfr_id] = 0
            continue
        
        false_alarm_level = mfr.features.false_alarm_level
        
        # ─── 1. Базовий коефіцієнт експлуатації ───
        if mfr.country_iso2 == "UA":
            base_annual_pct = 3.0
        else:
            base_annual_pct = 4.0
        
        # ─── 2. Алгоритмічна знижка на ТО ───
        # Cofem (PREMIUM з адаптивним моніторингом і remote diagnostics) — знижка 50%
        # Базові — без знижки
        if false_alarm_level == FalseAlarmLevel.PREMIUM:
            annual_pct = base_annual_pct * (1 - ALGORITHMIC_MAINTENANCE_DISCOUNT)
            maintenance_note = (
                f"{annual_pct:.1f}% (зі знижкою {ALGORITHMIC_MAINTENANCE_DISCOUNT*100:.0f}% "
                f"за алгоритмічну детекцію: адаптивний моніторинг + remote diagnostics)"
            )
        elif false_alarm_level == FalseAlarmLevel.BASIC:
            annual_pct = base_annual_pct + 0.5
            maintenance_note = f"{annual_pct:.1f}% (+0.5% надбавка для базової детекції)"
        else:
            annual_pct = base_annual_pct
            maintenance_note = f"{annual_pct:.1f}% (базовий рівень)"
        
        annual_cost = capex * annual_pct / 100
        operating_total = annual_cost * horizon_years
        
        # ─── 3. Заміна АКБ ───
        battery_replacements = horizon_years // 5
        battery_cost = capex * 0.05 * battery_replacements
        
        # ─── 4. Вартість хибних тривог ───
        # Кількість димових детекторів — основне джерело хибних
        n_smoke = 0
        n_heat = 0
        if isinstance(alloc, Allocation):
            n_smoke = sum(i.quantity for i in alloc.detectors_smoke)
            n_heat = sum(i.quantity for i in alloc.detectors_heat)
        elif isinstance(alloc, MultiPanelAllocation):
            for npa_a in alloc.npa_zone_allocations:
                n_smoke += sum(i.quantity for i in npa_a.detectors_smoke)
                n_heat += sum(i.quantity for i in npa_a.detectors_heat)
        
        # Теплові дають хибних значно менше (×0.3)
        effective_detectors = n_smoke + n_heat * 0.3
        false_alarm_rate = FALSE_ALARM_RATES_PER_DETECTOR_PER_YEAR.get(false_alarm_level, 0.05)
        false_alarms_per_year = effective_detectors * false_alarm_rate
        false_alarm_cost_total = false_alarms_per_year * COST_PER_FALSE_ALARM_UAH * horizon_years
        
        # ─── 5. Очищення детекторів ───
        # Cofem (PREMIUM з лабіринтними корпусами) — НЕ ПОТРІБНО
        # Інші — пилосмоком 1.5 разів/рік
        if mfr.manufacturer_id == "cofem" or "labyrinth" in str(mfr.features.false_alarm_technologies):
            cleaning_cost_total = 0
            cleaning_note = "очищення не потрібне (лабіринтні корпуси A50)"
        else:
            cleaning_cost_total = (
                n_smoke * CLEANINGS_PER_YEAR * CLEANING_COST_PER_DETECTOR_UAH * horizon_years
            )
            cleaning_note = (
                f"{cleaning_cost_total:,.0f} ₴ ({n_smoke} димових × {CLEANINGS_PER_YEAR}/рік × "
                f"{CLEANING_COST_PER_DETECTOR_UAH}₴ × {horizon_years} рр.)"
            )
        
        # ─── ПІДСУМОК ───
        tco = capex + operating_total + battery_cost + false_alarm_cost_total + cleaning_cost_total
        abs_tco[mfr_id] = round(tco, 0)
        breakdowns[mfr_id] = {
            "capex": capex,
            "annual_pct": annual_pct,
            "operating": operating_total,
            "battery": battery_cost,
            "false_alarm_count": round(false_alarms_per_year * horizon_years),
            "false_alarm_cost": false_alarm_cost_total,
            "cleaning_cost": cleaning_cost_total,
            "cleaning_note": cleaning_note,
            "maintenance_note": maintenance_note,
            "years": horizon_years,
        }
    
    if not abs_tco:
        return {}
    
    priced = {k: v for k, v in abs_tco.items() if v > 0}
    if not priced:
        return {mfr_id: LayerScore(score=50.0, reasoning="TCO не обчислюється без цін.",
                                    raw_value=0, unit="UAH")
                for mfr_id in abs_tco}
    
    cheapest = min(priced.values())
    
    scores = {}
    for mfr_id, tco in abs_tco.items():
        if tco == 0:
            scores[mfr_id] = LayerScore(
                score=50.0,
                reasoning="TCO не обчислюється — ціни не зафіксовано.",
                raw_value=0,
                unit="UAH",
            )
            continue
        
        ratio = cheapest / tco
        score = round(100 * (ratio ** 0.5), 1)
        
        b = breakdowns[mfr_id]
        reasoning = (
            f"TCO за {b['years']} років: {tco:,.0f} ₴ = "
            f"CAPEX {b['capex']:,.0f} + ТО {b['operating']:,.0f} ({b['maintenance_note']}) + "
            f"АКБ {b['battery']:,.0f} + "
            f"хибні ({b['false_alarm_count']} разів × 5000₴ = {b['false_alarm_cost']:,.0f}) + "
            f"очищення ({b['cleaning_note']}). "
            f"Δ до найдешевшого: +{(tco/cheapest - 1)*100:.0f}%."
        )
        
        scores[mfr_id] = LayerScore(
            score=score,
            reasoning=reasoning,
            raw_value=tco,
            unit="UAH",
        )
    
    return scores


# ═══════════════════════════════════════════════════════════════════
# OVERALL SCORE — зважена сума 5 шарів
# ═══════════════════════════════════════════════════════════════════
#
# Базові ваги шарів (рекалібруються в Step 5 за пре-об'єктом):
#   CAPEX 30% / Архіт 10% / Функц 25% / Експл 15% / TCO 20%
# ═══════════════════════════════════════════════════════════════════


DEFAULT_LAYER_WEIGHTS = {
    "layer_1_capex": 0.30,
    "layer_2_architectural": 0.10,
    "layer_3_functional": 0.25,
    "layer_4_operational": 0.15,
    "layer_5_tco": 0.20,
}


def _adapt_layer_weights(state: ObjectState) -> dict[str, float]:
    """
    Адаптація ваг 5 шарів під пре-об'єктні відповіді.
    
    Правила:
    1. Якщо clientFinancing constraints → CAPEX 35%, інші пропорційно вниз
    2. Якщо long lifetime → TCO 30%, CAPEX 20%
    3. Якщо premium false_alarm → Functional 30%
    4. Якщо international insurance → Architectural+Operational підіймаються
    5. Якщо BMS required → Functional 30%, Operational 20%
    6. Якщо mobile+cloud required → Functional 30%
    """
    weights = dict(DEFAULT_LAYER_WEIGHTS)
    pre = state.pre_object
    
    # Rule 1: бюджетні обмеження
    if pre.financing_constraints == TriState.YES:
        weights["layer_1_capex"] = 0.40
        weights["layer_5_tco"] = 0.15
    
    # Rule 2: довгий горизонт
    if pre.lifetime_horizon.value == "long_15_20":
        weights["layer_5_tco"] = 0.30
        weights["layer_1_capex"] = 0.20
    
    # Rule 3: преміум захист від хибних
    if pre.false_alarm_protection.value == "premium":
        weights["layer_3_functional"] = 0.30
        weights["layer_1_capex"] = 0.20
    
    # Rule 4: міжнародне страхування
    if pre.international_insurance == TriState.YES:
        weights["layer_2_architectural"] = 0.15
        weights["layer_4_operational"] = 0.20
    
    # Rule 5: BMS
    if pre.bms_integration_required == TriState.YES:
        weights["layer_3_functional"] = max(weights["layer_3_functional"], 0.30)
        weights["layer_4_operational"] = max(weights["layer_4_operational"], 0.20)
    
    # Rule 6: mobile + cloud
    if pre.mobile_app_required == TriState.YES and pre.cloud_monitoring_required == TriState.YES:
        weights["layer_3_functional"] = max(weights["layer_3_functional"], 0.30)
    
    # Нормалізація до 1.0
    total = sum(weights.values())
    return {k: round(v / total, 4) for k, v in weights.items()}


def compute_overall_score(
    layer_scores: ManufacturerScores,
    weights: dict[str, float],
) -> tuple[float, str]:
    """
    Обчислює overall_score як зважену суму 5 шарів.
    Повертає (score, reasoning).
    """
    total = 0.0
    contributions = []
    
    for layer_key, weight in weights.items():
        layer_score = getattr(layer_scores, layer_key)
        if layer_score:
            contribution = layer_score.score * weight
            total += contribution
            contributions.append((layer_key, layer_score.score, weight, contribution))
    
    # Top-2 contributors
    contributions.sort(key=lambda c: c[3], reverse=True)
    top = contributions[:2]
    top_str = ", ".join(
        f"{c[0].replace('layer_', 'L').replace('_capex','').replace('_architectural','').replace('_functional','').replace('_operational','').replace('_tco','')}"
        f"={c[1]:.0f}×{c[2]*100:.0f}%"
        for c in top
    )
    
    reasoning = f"Overall {total:.1f} з 100. Найбільші внески: {top_str}."
    return round(total, 1), reasoning


# ═══════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ КРОКУ 4 — ОНОВЛЕНО ДЛЯ ВСІХ 5 ШАРІВ
# ═══════════════════════════════════════════════════════════════════


def compute_scores(
    allocations: dict[str, AllocationLike],
    manufacturers: dict[str, Manufacturer],
    state: ObjectState | None = None,
) -> dict[str, ManufacturerScores]:
    """
    Обчислює бали по всіх 5 шарах для всіх виробників.
    
    Якщо state=None — Layer 3 і Layer 5 не обчислюються (потрібен пре-об'єкт).
    """
    layer_1_results = score_layer_1_capex(allocations)
    layer_2_results = score_layer_2_architectural(allocations)
    
    layer_3_results = {}
    layer_5_results = {}
    if state is not None:
        layer_3_results = score_layer_3_functional(manufacturers, state)
        layer_5_results = score_layer_5_tco(manufacturers, allocations, state)
    
    layer_4_results = score_layer_4_operational(manufacturers)
    
    # Адаптовані ваги шарів
    adapted_weights = (
        _adapt_layer_weights(state) if state else DEFAULT_LAYER_WEIGHTS
    )
    
    final_scores: dict[str, ManufacturerScores] = {}
    
    for mfr_id in allocations:
        scores_obj = ManufacturerScores(
            manufacturer_id=mfr_id,
            layer_1_capex=layer_1_results[mfr_id],
            layer_2_architectural=layer_2_results[mfr_id],
            layer_3_functional=layer_3_results.get(mfr_id),
            layer_4_operational=layer_4_results.get(mfr_id),
            layer_5_tco=layer_5_results.get(mfr_id),
        )
        
        # Обчислюємо overall, якщо є всі шари
        if all([scores_obj.layer_1_capex, scores_obj.layer_2_architectural,
                scores_obj.layer_3_functional, scores_obj.layer_4_operational,
                scores_obj.layer_5_tco]):
            overall, overall_reasoning = compute_overall_score(scores_obj, adapted_weights)
            scores_obj.overall_score = overall
            scores_obj.overall_reasoning = overall_reasoning
            scores_obj.applied_weights = adapted_weights
        
        final_scores[mfr_id] = scores_obj
    
    return final_scores
