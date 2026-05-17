"""
MODE 2 — REVERSE PRIORITY ANALYSIS

Сценарний аналіз: який виробник був би переможцем за різних 
пре-об'єктних умов? Це покаже clients «за яких умов інший варіант 
кращий», що формує довіру до інструменту.

Алгоритм:
1. Беремо базовий ObjectState
2. Генеруємо 16 варіантів = 2^4 (4 осі × 2 значення)
3. Для кожного прогоняємо повний pipeline через run_calculation
4. Збираємо рейтинги і виявляємо переможців
5. Формуємо аналітику: хто скільки разів переміг, у яких умовах

Оси варіювання:
- lifetime_horizon: SHORT vs LONG
- false_alarm_protection: STANDARD vs PREMIUM
- financing_constraints: NO vs YES
- cloud + mobile required: NO-NO vs YES-YES
"""
import copy
from itertools import product

from pydantic import BaseModel, Field

from engine.pipeline import CalculationResult, run_calculation
from schemas.catalog import Catalog
from schemas.object_state import (
    FalseAlarmRequirement, LifetimeHorizon, ObjectState, TriState,
)


# ═══════════════════════════════════════════════════════════════════
# ОСІ ВАРІЮВАННЯ
# ═══════════════════════════════════════════════════════════════════


AXIS_HORIZON = {
    "S": (LifetimeHorizon.SHORT_3_5, "короткий горизонт (3-5 років)"),
    "L": (LifetimeHorizon.LONG_15_20, "довгий горизонт (15-20 років)"),
}

AXIS_FALSE_ALARM = {
    "S": (FalseAlarmRequirement.STANDARD, "стандартний захист від хибних"),
    "P": (FalseAlarmRequirement.PREMIUM, "преміум захист від хибних"),
}

AXIS_FINANCING = {
    "N": (TriState.NO, "без бюджетних обмежень"),
    "Y": (TriState.YES, "з бюджетними обмеженнями"),
}

AXIS_MOBILE_CLOUD = {
    "N": ((TriState.NO, TriState.NO), "без мобільного/хмари"),
    "Y": ((TriState.YES, TriState.YES), "з мобільним і хмарою"),
}


# ═══════════════════════════════════════════════════════════════════
# СТРУКТУРИ ДАНИХ
# ═══════════════════════════════════════════════════════════════════


class ScenarioRanking(BaseModel):
    """Рейтинг одного виробника в сценарії"""
    rank: int  # 1, 2, 3, ...
    manufacturer_id: str
    manufacturer_name: str
    overall_score: float
    capex_uah: float


class ScenarioResult(BaseModel):
    """Результат одного сценарію"""
    scenario_id: str  # "S01" ... "S16"
    scenario_code: str  # "h(S)_fa(S)_fin(N)_mc(N)"
    scenario_description: str
    
    # Які значення осей в цьому сценарії
    horizon: str
    false_alarm: str
    financing: str
    mobile_cloud: str
    
    # Хто переміг
    winner_id: str | None = None
    winner_name: str | None = None
    winner_overall: float | None = None
    
    # Повний рейтинг
    rankings: list[ScenarioRanking] = Field(default_factory=list)
    
    # Адаптовані ваги шарів у цьому сценарії
    applied_weights: dict[str, float] | None = None


class Mode2Result(BaseModel):
    """Підсумок Mode 2"""
    base_session_id: str
    total_scenarios: int
    
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    
    # Аналітика
    winner_distribution: dict[str, int] = Field(default_factory=dict)
    
    # Для кожного виробника — в яких сценаріях він був переможцем
    winning_conditions: dict[str, list[str]] = Field(default_factory=dict)
    
    # Сценарії, де Cofem НЕ переміг (для chestностi)
    cofem_loses_in: list[str] = Field(default_factory=list)
    
    # Загальні spostереження
    observations: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# ГЕНЕРАЦІЯ ВАРІАНТІВ ОБ'ЄКТНОГО СТЕЙТУ
# ═══════════════════════════════════════════════════════════════════


def _apply_axis_values_to_state(
    base_state: ObjectState,
    horizon_key: str,
    false_alarm_key: str,
    financing_key: str,
    mobile_cloud_key: str,
) -> ObjectState:
    """Створює варіант стейту з заданими значеннями осей"""
    state = base_state.model_copy(deep=True)
    
    # Horizon
    state.pre_object.lifetime_horizon = AXIS_HORIZON[horizon_key][0]
    
    # False alarm
    state.pre_object.false_alarm_protection = AXIS_FALSE_ALARM[false_alarm_key][0]
    
    # Financing
    state.pre_object.financing_constraints = AXIS_FINANCING[financing_key][0]
    
    # Mobile + Cloud
    mobile, cloud = AXIS_MOBILE_CLOUD[mobile_cloud_key][0]
    state.pre_object.mobile_app_required = mobile
    state.pre_object.cloud_monitoring_required = cloud
    
    # Унікальний session_id
    state.session_id = (
        f"{base_state.session_id}_mode2_h{horizon_key}_fa{false_alarm_key}_"
        f"fin{financing_key}_mc{mobile_cloud_key}"
    )
    
    return state


def _build_scenario_description(
    horizon_key: str, false_alarm_key: str,
    financing_key: str, mobile_cloud_key: str,
) -> str:
    """Людиночитаний опис сценарію"""
    parts = [
        AXIS_HORIZON[horizon_key][1],
        AXIS_FALSE_ALARM[false_alarm_key][1],
        AXIS_FINANCING[financing_key][1],
        AXIS_MOBILE_CLOUD[mobile_cloud_key][1],
    ]
    return " + ".join(parts)


# ═══════════════════════════════════════════════════════════════════
# ОСНОВНА ФУНКЦІЯ MODE 2
# ═══════════════════════════════════════════════════════════════════


def run_mode2_analysis(
    base_state: ObjectState,
    catalog: Catalog,
) -> Mode2Result:
    """
    Прогоняє 16 сценаріїв і формує аналітичний звіт.
    """
    result = Mode2Result(
        base_session_id=base_state.session_id,
        total_scenarios=0,
    )
    
    # Генеруємо всі комбінації 2^4 = 16
    scenario_idx = 0
    for h, fa, fin, mc in product("SL", "SP", "NY", "NY"):
        scenario_idx += 1
        scenario_id = f"S{scenario_idx:02d}"
        scenario_code = f"h({h})_fa({fa})_fin({fin})_mc({mc})"
        description = _build_scenario_description(h, fa, fin, mc)
        
        # Створюємо варіант стейту
        variant_state = _apply_axis_values_to_state(base_state, h, fa, fin, mc)
        
        # Прогоняємо повний pipeline
        try:
            calc_result = run_calculation(variant_state, catalog)
        except Exception as e:
            # Сценарій не виходить — пропускаємо з нотаткою
            scen_result = ScenarioResult(
                scenario_id=scenario_id,
                scenario_code=scenario_code,
                scenario_description=description + f" — ПОМИЛКА: {str(e)[:50]}",
                horizon=AXIS_HORIZON[h][1],
                false_alarm=AXIS_FALSE_ALARM[fa][1],
                financing=AXIS_FINANCING[fin][1],
                mobile_cloud=AXIS_MOBILE_CLOUD[mc][1],
            )
            result.scenarios.append(scen_result)
            continue
        
        # Будуємо рейтинг
        scen_result = ScenarioResult(
            scenario_id=scenario_id,
            scenario_code=scenario_code,
            scenario_description=description,
            horizon=AXIS_HORIZON[h][1],
            false_alarm=AXIS_FALSE_ALARM[fa][1],
            financing=AXIS_FINANCING[fin][1],
            mobile_cloud=AXIS_MOBILE_CLOUD[mc][1],
        )
        
        # Виявляємо переможця і будуємо рейтинг
        # Сортування за overall_score (спадання), якщо є; інакше за CAPEX
        eligible = [
            r for r in calc_result.manufacturer_results
            if not r.excluded and r.scores and r.scores.overall_score is not None
        ]
        
        if eligible:
            eligible.sort(key=lambda r: r.scores.overall_score, reverse=True)
            
            for idx, mfr_r in enumerate(eligible, start=1):
                scen_result.rankings.append(ScenarioRanking(
                    rank=idx,
                    manufacturer_id=mfr_r.manufacturer_id,
                    manufacturer_name=mfr_r.manufacturer_name,
                    overall_score=mfr_r.scores.overall_score,
                    capex_uah=mfr_r.capex_uah,
                ))
            
            winner = eligible[0]
            scen_result.winner_id = winner.manufacturer_id
            scen_result.winner_name = winner.manufacturer_name
            scen_result.winner_overall = winner.scores.overall_score
            scen_result.applied_weights = winner.scores.applied_weights
        
        result.scenarios.append(scen_result)
    
    result.total_scenarios = len(result.scenarios)
    
    # ─── АНАЛІТИКА ───
    _build_analytics(result)
    
    return result


def _build_analytics(result: Mode2Result) -> None:
    """Формує аналітичні висновки з 16 сценаріїв"""
    
    # 1. Розподіл перемог
    distribution: dict[str, int] = {}
    winning_conditions: dict[str, list[str]] = {}
    cofem_loses_in: list[str] = []
    
    for scen in result.scenarios:
        if not scen.winner_id:
            continue
        
        distribution[scen.winner_id] = distribution.get(scen.winner_id, 0) + 1
        
        if scen.winner_id not in winning_conditions:
            winning_conditions[scen.winner_id] = []
        winning_conditions[scen.winner_id].append(
            f"[{scen.scenario_id}] {scen.scenario_description}"
        )
        
        # Сценарії де Cofem НЕ переміг
        if scen.winner_id != "cofem":
            cofem_top = next(
                (r for r in scen.rankings if r.manufacturer_id == "cofem"), None
            )
            cofem_position = cofem_top.rank if cofem_top else "n/a"
            cofem_loses_in.append(
                f"[{scen.scenario_id}] {scen.scenario_description} "
                f"→ переміг {scen.winner_name} ({scen.winner_overall}), "
                f"Cofem на {cofem_position}-й позиції"
            )
    
    result.winner_distribution = distribution
    result.winning_conditions = winning_conditions
    result.cofem_loses_in = cofem_loses_in
    
    # 2. Загальні спостереження
    observations = []
    total = result.total_scenarios
    
    # Domination
    for mfr_id, count in sorted(distribution.items(), key=lambda x: -x[1]):
        pct = round(count / total * 100, 0)
        observations.append(
            f"{mfr_id.capitalize()} перемагає у {count}/{total} сценаріях ({pct}%)"
        )
    
    # Конкретні паттерни виграшу Cofem
    cofem_count = distribution.get("cofem", 0)
    if cofem_count > 0:
        # Аналіз — у яких комбінаціях вісей Cofem виграє?
        cofem_scens = [s for s in result.scenarios if s.winner_id == "cofem"]
        
        # Перевіримо: завжди коли premium false_alarm?
        premium_fa_scens = [s for s in result.scenarios if "P" in s.scenario_code.split("fa(")[1][0]]
        cofem_in_premium = sum(1 for s in premium_fa_scens if s.winner_id == "cofem")
        
        if cofem_in_premium >= len(premium_fa_scens) * 0.75:
            observations.append(
                f"Cofem домінує при преміум-захисті від хибних "
                f"({cofem_in_premium}/{len(premium_fa_scens)} сценаріїв)"
            )
        
        # Перевіримо горизонт
        long_scens = [s for s in result.scenarios if "L" in s.scenario_code.split("h(")[1][0]]
        cofem_in_long = sum(1 for s in long_scens if s.winner_id == "cofem")
        if cofem_in_long >= len(long_scens) * 0.75:
            observations.append(
                f"Cofem домінує при довгому горизонті експлуатації "
                f"({cofem_in_long}/{len(long_scens)} сценаріїв)"
            )
    
    # Хто переможець у бюджетних сценаріях
    fin_scens = [s for s in result.scenarios if "Y" in s.scenario_code.split("fin(")[1][0]]
    if fin_scens:
        fin_winners = {}
        for s in fin_scens:
            if s.winner_id:
                fin_winners[s.winner_id] = fin_winners.get(s.winner_id, 0) + 1
        top_fin = max(fin_winners.items(), key=lambda x: x[1]) if fin_winners else None
        if top_fin:
            observations.append(
                f"При бюджетних обмеженнях найчастіше перемагає {top_fin[0]} "
                f"({top_fin[1]}/{len(fin_scens)} сценаріїв)"
            )
    
    result.observations = observations
