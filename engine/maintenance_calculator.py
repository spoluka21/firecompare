"""
ENGINE: Maintenance Calculator (Калькулятор ТО СПЗ)

Розраховує вартість щомісячного технічного обслуговування СПЗ
з урахуванням:
- складу системи (ПС+СОУЕ, +пожежогасіння, +димовидалення, etc.)
- розміру об'єкта (площі)
- параметрів об'єкта (відстань, прогноз хибних, прогноз пошкоджень)
- технологічних особливостей виробника (з каталогу)

Може використовуватися:
1. У standalone-режимі — для будь-якого об'єкта без порівняння
2. Як частина pipeline FireCompare — для кожного порівнюваного виробника

Формула:
    Цінa = (ФОП + Транспорт + Запчастини + Адмін) × (1 + Markup) + Підряд
    де:
        ФОП = T_total × Ставка_год
        T_total = T_планове × K + T_дорога + T_хибні + T_пошкодження
        Markup = 0.60 (60%)
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from schemas.catalog import FalseAlarmLevel, Manufacturer


# ═══════════════════════════════════════════════════════════════════
# КОНСТАНТИ ТА ДЕФОЛТИ
# ═══════════════════════════════════════════════════════════════════


# Фінансові параметри
DEFAULT_SALARY_UAH = 30000  # грн/міс
DEFAULT_TAX_RATE = 0.60  # 60%
DEFAULT_WORK_HOURS = 168  # робочих годин на місяць
DEFAULT_FUEL_CONSUMPTION = 10  # л/100 км
DEFAULT_FUEL_PRICE = 60  # грн/л
DEFAULT_ADMIN_RATE = 0.15  # 15% від ФОП
DEFAULT_MARKUP = 0.60  # 60% націнка

DEFAULT_TRAVEL_SPEED = 50  # км/год
DEFAULT_TIME_PER_FALSE_ALARM = 1.5  # год на місці
DEFAULT_TIME_PER_DAMAGE = 3.0  # год на місці

# Базовий час ТО за площу (люд.-год/міс)
def _base_time_for_area(area_m2: float) -> float:
    """Базовий час планового ТО залежно від площі об'єкта"""
    if area_m2 <= 500:
        return 4.0
    elif area_m2 <= 2000:
        return 6.0
    elif area_m2 <= 5000:
        return 10.0
    elif area_m2 <= 10000:
        return 16.0
    elif area_m2 <= 20000:
        return 22.0
    else:
        return 28.0


# Коефіцієнти складності за компонентами системи
K_BASE = 1.0  # ПС + СОУЕ (завжди базово)
K_MONITORING = 0.15  # пультове спостереження (своє)
K_SMOKE_VENT = 0.20  # димовидалення
K_EXTINGUISH = 0.30  # пожежогасіння
K_VALVES = 0.15  # керування протипожежними клапанами
K_ENGINEERING = 0.20  # інженерні системи (ліфти, ворота, завіси)


# Дефолтні прогнози хибних/пошкоджень залежно від рівня системи
# (якщо користувач не вказує явно)
FALSE_ALARMS_BY_LEVEL = {
    FalseAlarmLevel.PREMIUM: 0.5,  # премум-детекція — мало хибних
    FalseAlarmLevel.ENHANCED: 2.0,  # покращена — кілька хибних
    FalseAlarmLevel.BASIC: 5.0,  # стандарт — більше хибних
}


# ═══════════════════════════════════════════════════════════════════
# СХЕМИ ВХОДУ/ВИХОДУ
# ═══════════════════════════════════════════════════════════════════


class SystemComposition(BaseModel):
    """Склад СПЗ — які підсистеми є на об'єкті"""
    has_ps_soue: bool = True  # завжди базово
    has_monitoring_own: bool = False  # пультове спостереження виконуємо МИ
    has_monitoring_subcontract: bool = False  # пультове виконує підрядник
    subcontract_monitoring_uah: float = 0  # вартість підрядника (грн/міс)
    has_smoke_vent: bool = False  # димовидалення
    has_extinguish: bool = False  # пожежогасіння
    has_valves: bool = False  # керування клапанами
    has_engineering_systems: bool = False  # інженерні системи
    
    def complexity_coefficient(self) -> float:
        """Сумарний коефіцієнт складності системи"""
        k = K_BASE  # ПС + СОУЕ завжди
        if self.has_monitoring_own:
            k += K_MONITORING
        if self.has_smoke_vent:
            k += K_SMOKE_VENT
        if self.has_extinguish:
            k += K_EXTINGUISH
        if self.has_valves:
            k += K_VALVES
        if self.has_engineering_systems:
            k += K_ENGINEERING
        return round(k, 2)
    
    def composition_label(self, lang: str = "ua") -> str:
        """Текстовий опис складу"""
        if lang == "en":
            parts = ["PS + SOUE"]
            if self.has_monitoring_own:
                parts.append("Monitoring (own)")
            if self.has_monitoring_subcontract:
                parts.append("Monitoring (subcontract)")
            if self.has_smoke_vent:
                parts.append("Smoke ventilation")
            if self.has_extinguish:
                parts.append("Fire extinguishing")
            if self.has_valves:
                parts.append("Valves control")
            if self.has_engineering_systems:
                parts.append("Engineering systems")
            return " + ".join(parts)
        
        parts = ["ПС + СОУЕ"]
        if self.has_monitoring_own:
            parts.append("Пультове спостереження (своє)")
        if self.has_monitoring_subcontract:
            parts.append("Пультове спостереження (підряд)")
        if self.has_smoke_vent:
            parts.append("Димовидалення")
        if self.has_extinguish:
            parts.append("Пожежогасіння")
        if self.has_valves:
            parts.append("Керування клапанами")
        if self.has_engineering_systems:
            parts.append("Інженерні системи")
        return " + ".join(parts)


class MaintenanceParams(BaseModel):
    """Параметри для розрахунку ТО"""
    
    # Дані про об'єкт
    object_area_m2: float = Field(gt=0, description="Загальна захищувана площа (м²)")
    composition: SystemComposition
    distance_km: float = Field(ge=0, description="Відстань до об'єкта від офісу (км)")
    
    # Прогнозні параметри (опційно — якщо None, беремо з рівня виробника)
    n_false_alarms_month: Optional[float] = Field(
        default=None, ge=0,
        description="Прогноз хибних спрацювань/міс (None = взяти з FalseAlarmLevel)"
    )
    n_damages_month: float = Field(default=0.5, ge=0, description="Прогноз пошкоджень/міс")
    
    # Час робіт (опційно — якщо None, auto з площі)
    base_planned_hours: Optional[float] = Field(
        default=None, ge=0,
        description="Базовий час планового ТО на місяць (None = auto з площі)"
    )
    n_planned_visits: int = Field(default=2, ge=1, le=8, description="Планових візитів/міс")
    
    # Фінансові параметри
    salary_uah: float = Field(default=DEFAULT_SALARY_UAH, ge=0)
    tax_rate: float = Field(default=DEFAULT_TAX_RATE, ge=0, le=1.5)
    work_hours_month: int = Field(default=DEFAULT_WORK_HOURS, ge=100, le=200)
    fuel_consumption_l_100km: float = Field(default=DEFAULT_FUEL_CONSUMPTION, ge=0)
    fuel_price_uah_l: float = Field(default=DEFAULT_FUEL_PRICE, ge=0)
    admin_rate: float = Field(default=DEFAULT_ADMIN_RATE, ge=0, le=0.5)
    markup: float = Field(default=DEFAULT_MARKUP, ge=0, le=2.0)
    
    # Стратегічна знижка (опційна)
    strategic_discount_pct: float = Field(default=0, ge=0, le=50,
                                          description="Знижка в %, 0-50")


class MaintenanceCostBreakdown(BaseModel):
    """Розклад вартості"""
    # Час
    t_planned: float  # планове ТО з K
    t_travel_planned: float  # дорога планових візитів
    t_false_alarms: float  # хибні з дорогою
    t_damages: float  # пошкодження з дорогою
    t_total: float  # сумарно
    
    # Собівартість
    cost_labor: float  # ФОП × ставка
    cost_transport: float  # пробіг × тариф
    cost_parts: float  # запчастини
    cost_admin: float  # адміністративні
    cost_own_total: float  # власна собівартість
    
    # Ціна
    price_own_calculated: float  # власні × (1 + markup)
    subcontract_pass_through: float  # підряд (без націнки)
    price_calculated_total: float  # розрахункова без знижки
    discount_uah: float  # знижка в грн
    price_final_month: float  # фінальна ціна за місяць
    price_final_year: float  # × 12
    
    # Допоміжне
    rate_per_hour: float  # ставка за годину
    transport_per_km: float  # вартість км
    complexity_k: float  # коефіцієнт складності
    n_visits_total: float  # всього візитів
    total_km: float  # пробіг


class MaintenanceResult(BaseModel):
    """Результат розрахунку ТО"""
    params: MaintenanceParams
    breakdown: MaintenanceCostBreakdown
    
    # Зв'язок з виробником (якщо розрахунок у контексті порівняння)
    manufacturer_id: Optional[str] = None
    manufacturer_name: Optional[str] = None
    
    # Інформаційні поля
    composition_label: str = ""
    notes: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# ОСНОВНА ФУНКЦІЯ РОЗРАХУНКУ
# ═══════════════════════════════════════════════════════════════════


def calculate_maintenance(
    params: MaintenanceParams,
    manufacturer: Optional[Manufacturer] = None,
) -> MaintenanceResult:
    """
    Розраховує вартість ТО для заданих параметрів.
    
    Якщо передано manufacturer — параметри коригуються з урахуванням
    технологічних особливостей виробника:
    - false_alarm_level → прогноз хибних (якщо params.n_false_alarms_month is None)
    - maintenance_time_modifier → корекція T_планового (лабіринтні корпуси Cofem)
    - avg_part_replacement_cost_uah → вартість запчастин
    """
    notes: list[str] = []
    
    # ─── 1. Час робіт ───
    
    # Базовий час планового ТО
    if params.base_planned_hours is not None:
        t_base = params.base_planned_hours
    else:
        t_base = _base_time_for_area(params.object_area_m2)
        notes.append(
            f"Базовий час {t_base:.1f} год обрано auto для площі "
            f"{params.object_area_m2:,.0f} м²"
        )
    
    # Модифікатор від виробника
    time_modifier = manufacturer.maintenance_time_modifier if manufacturer else 1.0
    if manufacturer and time_modifier != 1.0:
        notes.append(
            f"Час ТО скоригований модифікатором {time_modifier:.2f} "
            f"від виробника ({manufacturer.name_ua})"
        )
    
    k = params.composition.complexity_coefficient()
    t_planned = t_base * k * time_modifier
    
    # Дорога планова
    t_one_trip = 2 * params.distance_km / DEFAULT_TRAVEL_SPEED
    t_travel_planned = params.n_planned_visits * t_one_trip
    
    # Хибні: з виробника або з параметрів
    if params.n_false_alarms_month is not None:
        n_false = params.n_false_alarms_month
    elif manufacturer:
        n_false = FALSE_ALARMS_BY_LEVEL.get(
            manufacturer.features.false_alarm_level, 2.0
        )
        notes.append(
            f"Прогноз хибних {n_false}/міс — за рівнем "
            f"{manufacturer.features.false_alarm_level.value} виробника"
        )
    else:
        n_false = 2.0
    
    # Модифікатор service response (швидкість виїзду)
    response_mod = manufacturer.service_response_modifier if manufacturer else 1.0
    t_false = n_false * (DEFAULT_TIME_PER_FALSE_ALARM * response_mod + t_one_trip)
    t_damage = params.n_damages_month * (DEFAULT_TIME_PER_DAMAGE * response_mod + t_one_trip)
    
    t_total = t_planned + t_travel_planned + t_false + t_damage
    
    # ─── 2. Собівартість ───
    
    rate_per_hour = params.salary_uah * (1 + params.tax_rate) / params.work_hours_month
    cost_labor = t_total * rate_per_hour
    
    n_visits_total = params.n_planned_visits + n_false + params.n_damages_month
    total_km = n_visits_total * 2 * params.distance_km
    transport_per_km = (params.fuel_consumption_l_100km / 100 * params.fuel_price_uah_l) * 2  # пальне + амортизація
    cost_transport = total_km * transport_per_km
    
    # Запчастини
    cost_per_part = manufacturer.avg_part_replacement_cost_uah if manufacturer else 800.0
    cost_parts = params.n_damages_month * cost_per_part
    
    # Адміністративні
    cost_admin = cost_labor * params.admin_rate
    
    cost_own_total = cost_labor + cost_transport + cost_parts + cost_admin
    
    # ─── 3. Ціна ───
    
    price_own_calculated = cost_own_total * (1 + params.markup)
    
    subcontract = (params.composition.subcontract_monitoring_uah
                   if params.composition.has_monitoring_subcontract else 0)
    
    price_calculated_total = price_own_calculated + subcontract
    
    discount_uah = price_calculated_total * params.strategic_discount_pct / 100
    price_final_month = price_calculated_total - discount_uah
    price_final_year = price_final_month * 12
    
    breakdown = MaintenanceCostBreakdown(
        t_planned=round(t_planned, 2),
        t_travel_planned=round(t_travel_planned, 2),
        t_false_alarms=round(t_false, 2),
        t_damages=round(t_damage, 2),
        t_total=round(t_total, 2),
        cost_labor=round(cost_labor, 2),
        cost_transport=round(cost_transport, 2),
        cost_parts=round(cost_parts, 2),
        cost_admin=round(cost_admin, 2),
        cost_own_total=round(cost_own_total, 2),
        price_own_calculated=round(price_own_calculated, 2),
        subcontract_pass_through=round(subcontract, 2),
        price_calculated_total=round(price_calculated_total, 2),
        discount_uah=round(discount_uah, 2),
        price_final_month=round(price_final_month, 2),
        price_final_year=round(price_final_year, 2),
        rate_per_hour=round(rate_per_hour, 2),
        transport_per_km=round(transport_per_km, 2),
        complexity_k=k,
        n_visits_total=round(n_visits_total, 2),
        total_km=round(total_km, 2),
    )
    
    result = MaintenanceResult(
        params=params,
        breakdown=breakdown,
        manufacturer_id=manufacturer.manufacturer_id if manufacturer else None,
        manufacturer_name=manufacturer.name_ua if manufacturer else None,
        composition_label=params.composition.composition_label(),
        notes=notes,
    )
    
    return result
