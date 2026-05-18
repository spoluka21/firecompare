"""
Pydantic-схема вхідного стейту об'єкта (input для движка розрахунку)

Цей стейт формує AI-агент після Фаз 1-3 діалогу і передає в движок 
через команду [CALCULATE]. Структура відповідає JSON-схемі з 
Agent_System_Prompt_v02.md, розділ OBJECT_STATE_SCHEMA.
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# ENUMS — пре-об'єктні відповіді
# ═══════════════════════════════════════════════════════════════════


class Jurisdiction(str, Enum):
    UA = "UA"
    UK = "UK"
    EU = "EU"
    US = "US"


class TriState(str, Enum):
    YES = "yes"
    NO = "no"
    NOT_SURE = "not_sure"
    NICE_TO_HAVE = "nice_to_have"


class LifetimeHorizon(str, Enum):
    SHORT_3_5 = "short_3_5"  # 3-5 років
    MEDIUM_7_10 = "medium_7_10"  # 7-10 років
    LONG_15_20 = "long_15_20"  # 15-20 років


class FalseAlarmRequirement(str, Enum):
    STANDARD = "standard"  # ДСТУ EN 54 базово
    PREMIUM = "premium"  # вимога преміум-захисту


class ObjectType(str, Enum):
    RESIDENTIAL_MULTI = "residential_multi"  # багатоквартирний житловий
    RESIDENTIAL_MIXED = "residential_mixed"  # житловий з комерцією на 1-х поверхах
    PUBLIC = "public"  # громадський
    ADMINISTRATIVE = "administrative"  # офісний / адміністративний
    COMMERCIAL_TRC = "commercial_trc"  # торгово-розважальний
    INDUSTRIAL = "industrial"  # виробничий
    WAREHOUSE = "warehouse"  # складсько-логістичний
    SPECIALIZED = "specialized"  # датацентр, ПММ тощо
    MIXED_USE = "mixed_use"


class ConstructionStage(str, Enum):
    NEW_CONSTRUCTION = "new_construction"
    RENOVATION = "renovation"
    RE_EQUIPMENT = "re_equipment"


class ParkingType(str, Enum):
    UNDERGROUND = "underground"
    ABOVEGROUND = "aboveground"
    MIXED = "mixed"


# ═══════════════════════════════════════════════════════════════════
# ПРЕ-ОБ'ЄКТНІ ВІДПОВІДІ
# ═══════════════════════════════════════════════════════════════════


class PreObjectAnswers(BaseModel):
    """Фаза 1 — 5 пре-об'єктних блоків питань"""
    
    # Q1. Юрисдикція + фінансування
    jurisdictions: list[Jurisdiction] = Field(default_factory=lambda: [Jurisdiction.UA])
    financing_constraints: TriState = TriState.NO
    financing_comment: Optional[str] = None
    international_insurance: TriState = TriState.NO
    insurance_market: Optional[Jurisdiction] = None
    
    # Q2. Термін експлуатації
    lifetime_horizon: LifetimeHorizon = LifetimeHorizon.MEDIUM_7_10
    
    # Q3. Захист від хибних
    false_alarm_protection: FalseAlarmRequirement = FalseAlarmRequirement.STANDARD
    
    # Q4. Мобільні + хмарні
    mobile_app_required: TriState = TriState.NO
    cloud_monitoring_required: TriState = TriState.NO
    
    # Q5. BMS
    bms_integration_required: TriState = TriState.NO
    bms_system: Optional[str] = None
    bms_protocol: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# ОБ'ЄКТНІ ДАНІ
# ═══════════════════════════════════════════════════════════════════


class SubdivisionType(str, Enum):
    """Тип розкладки приміщень у функціональній зоні (для розрахунку детекторів)"""
    OPEN = "open"  # відкритий простір — паркінг, цех, склад, торговий зал великий
    SUBDIVIDED = "subdivided"  # розбита на приміщення + МЗК — офіс, готель, ТЦ з бутіками
    CORRIDOR_ONLY = "corridor_only"  # самі МЗК — сходові клітки, ліфтові холи, тех. коридори


class FunctionalZone(BaseModel):
    """Одна функціональна зона об'єкта"""
    area_m2: float = Field(ge=0)
    
    # Тип розкладки — визначає метод розрахунку детекторів
    subdivision_type: SubdivisionType = SubdivisionType.OPEN
    
    # Для subdivided: середній розмір окремого приміщення в м²
    # (стандартна офісна кімната ~25, готельний номер ~20, бутік ТЦ ~30-50)
    avg_room_area_m2: Optional[float] = Field(default=None, ge=5, le=200)
    
    # Для subdivided: частка МЗК (коридори, санвузли) у зоні
    # Зазвичай 15-25% для офісів, 20-30% для торгових центрів з бутіками
    common_areas_share: Optional[float] = Field(default=None, ge=0.0, le=0.5)
    
    # Для довідки (експлікація приміщень якщо відома)
    rooms_count: Optional[int] = None


class ParkingDetails(BaseModel):
    spaces: int = Field(ge=0)
    parking_type: ParkingType
    levels: int = Field(ge=1, default=1)
    gas_suppression_areas: bool = False


class ShelterDetails(BaseModel):
    people_capacity: int = Field(ge=0)
    shelter_class: Optional[str] = None
    integration: Optional[str] = None  # "separate" / "integrated"


class ServerRoomDetails(BaseModel):
    area_m2: float = Field(ge=0)
    criticality: Optional[str] = None  # "standard" / "tier3_plus"
    gas_suppression: Optional[str] = None  # "fm200" / "inergen" / "novec" / "water_mist" / "none"


class KitchenDetails(BaseModel):
    kitchen_type: Optional[str] = None
    stove_type: Optional[str] = None  # "gas" / "electric" / "combi"
    hood_suppression: bool = False


class IndustrialDetails(BaseModel):
    fire_hazard_category: Optional[str] = None  # "A", "B", "V1"..."V4", "G", "D"
    has_ex_zones: bool = False
    ex_zone_class: Optional[str] = None  # "1", "2", "21", "22"


class CriticalZones(BaseModel):
    """Блок C — специфіка ключових зон (умовний)"""
    parking: Optional[ParkingDetails] = None
    shelter: Optional[ShelterDetails] = None
    server_room: Optional[ServerRoomDetails] = None
    kitchen: Optional[KitchenDetails] = None
    industrial: Optional[IndustrialDetails] = None


class FireHoseCabinetSignals(BaseModel):
    """Сигнали з однієї шафи пожежного крана (ШПК)"""
    has_buttons: bool = True  # кнопки примусового запуску
    has_hose_sensor: bool = True  # датчик положення крана
    has_door_smk: bool = True  # СМК шафи
    
    def signals_per_cabinet(self) -> int:
        """Скільки логічних сигналів дає одна шафа"""
        return sum([self.has_buttons, self.has_hose_sensor, self.has_door_smk])


class ExecutiveAutomation(BaseModel):
    """Блок D — виконавча автоматика"""
    fire_hose_cabinets_count: int = Field(ge=0, default=0)
    fire_hose_cabinet_signals: FireHoseCabinetSignals = Field(default_factory=FireHoseCabinetSignals)
    
    smoke_dampers: int = Field(ge=0, default=0)  # клапани димовидалення
    fire_dampers: int = Field(ge=0, default=0)  # вогнезахисні клапани вентиляції
    fire_pumps: int = Field(ge=0, default=0)  # пожежні насоси
    smoke_fans: int = Field(ge=0, default=0)  # вентилятори димовидалення / підпору
    fire_doors: int = Field(ge=0, default=0)  # двері з електромагнітами
    elevators_fire_mode: int = Field(ge=0, default=0)  # ліфти з режимом "Пожежа"
    
    other_actuators: int = Field(ge=0, default=0)
    other_description: Optional[str] = None
    
    def total_io_signals(self) -> int:
        """
        Загальна кількість логічних I/O сигналів від всієї виконавчої автоматики
        Кожен клапан / насос / ліфт зазвичай має 2 сигнали (керування + зворотний зв'язок),
        але для MVP вважаємо 1 сигнал на одиницю — це консервативна оцінка для CAPEX.
        Точніший розрахунок — у функції розрахунку BOM.
        """
        cabinet_signals = self.fire_hose_cabinets_count * self.fire_hose_cabinet_signals.signals_per_cabinet()
        actuator_signals = (
            self.smoke_dampers + self.fire_dampers + self.fire_pumps +
            self.smoke_fans + self.fire_doors + self.elevators_fire_mode +
            self.other_actuators
        )
        return cabinet_signals + actuator_signals


class ObjectData(BaseModel):
    """Об'єктні дані (Блоки A, B, C, D)"""
    
    # Блок A — Базові параметри
    object_type: ObjectType
    stage: ConstructionStage = ConstructionStage.NEW_CONSTRUCTION
    phases: int = Field(ge=1, default=1)
    total_area_m2: float = Field(gt=0)
    floors_above: int = Field(ge=0, default=1)
    floors_below: int = Field(ge=0, default=0)
    height_m: Optional[float] = Field(default=None, ge=0)
    
    # Блок B — Функціональне зонування
    zones: dict[str, FunctionalZone] = Field(default_factory=dict)
    
    # Блок C — Специфіка ключових зон
    critical_zones: CriticalZones = Field(default_factory=CriticalZones)
    
    # Блок D — Виконавча автоматика
    executive_automation: ExecutiveAutomation = Field(default_factory=ExecutiveAutomation)
    
    # Опціональне фінальне поле
    additional_notes: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# NPA АРХІТЕКТУРА (Блок E у Фазі 2 опитувальника)
# ═══════════════════════════════════════════════════════════════════
# Опис принципової архітектури системи: розподіл на функціональні зони
# з власними ППКП. Запитується явно через опитувальник (NPA-1, NPA-2, NPA-3).
#
# Нормативні джерела для типових значень:
# - ДБН В.2.5-56:2014 Зм.№2 (адресна зона виявлення)
# - ДБН В.2.3-15:2017 (пожежні і димові зони підземних паркінгів)
# - ДБН В.1.1-7:2016 (загальні вимоги пожежної безпеки)
# - ДБН В.2.2-15:2019 (житлові будинки)


class NPAZoneType(str, Enum):
    """Типи функціональних зон, які можуть потребувати окремого ППКП"""
    SHELTER = "shelter"  # укриття цивільного захисту
    PARKING = "parking"  # підземний/багаторівневий паркінг
    BUILDING = "building"  # окрема будівля (секція ЖК, корпус)
    COMMERCIAL = "commercial"  # торгово-офісна частина
    TECHNICAL = "technical"  # технічні приміщення (ІТП, насосна, котельні)
    INDUSTRIAL = "industrial"  # виробнича зона
    MAIN = "main"  # головний ППКП (за замовчуванням, якщо нема спецзон)


# Нормативні значення за замовчуванням (in-code, з посиланнями на ДБН)
# В v0.2 виносимо в normatives/*.yaml
DEFAULT_PARKING_FIRE_ZONE_AREA_M2 = 2500  # ДБН В.2.3-15: пожежна зона 1600-3500, беремо середнє
DEFAULT_PARKING_DETECTION_ZONE_AREA_M2 = 1600  # ДБН В.2.5-56 Зм.№2: адресна зона до 1600 м²
DEFAULT_RESERVE_LOOPS = 1  # за замовчуванням 1 резервний шлейф на ППКП
DEFAULT_RESERVE_ADDRESSES_PCT = 20  # 20% резерв адрес у шлейфі


class IOSignalAllocation(BaseModel):
    """
    Розподіл I/O сигналів за NPA-зонами.
    Запитується через опитувальник окремими питаннями для кожної категорії.
    Сума всіх часток має давати 1.0 ±0.05.
    """
    shelter_share: float = Field(default=0.0, ge=0.0, le=1.0)
    parking_share: float = Field(default=0.0, ge=0.0, le=1.0)
    main_share: float = Field(default=1.0, ge=0.0, le=1.0)
    building_shares: dict[str, float] = Field(default_factory=dict)
    
    def total(self) -> float:
        return (
            self.shelter_share + self.parking_share + self.main_share
            + sum(self.building_shares.values())
        )


class NPAZone(BaseModel):
    """
    Одна функціональна зона СПЗ з власним ППКП.
    Формується на основі відповідей клієнта в опитувальнику.
    """
    zone_id: str  # унікальний слаг: "shelter", "parking", "main"
    zone_type: NPAZoneType
    name: str  # людиночитна назва: "Укриття цивільного захисту"
    name_en: Optional[str] = None  # англомовна назва для двомовного UI
    
    # Чи потребує НЕЗАЛЕЖНОГО ППКП (так — окремий прилад; ні — додаткова петля головного)
    requires_independent_panel: bool = True
    
    # Площа цієї зони (м²)
    area_m2: float = Field(gt=0)
    
    # Які FunctionalZone з object.zones належать цій NPA-зоні
    # (ідентифікатори ключів зі словника object.zones)
    functional_zones: list[str] = Field(default_factory=list)
    
    # Кількість пожежних зон у межах цієї NPA-зони
    # Для паркінгу: обчислюється з area / DEFAULT_PARKING_FIRE_ZONE_AREA_M2, або задається явно
    # Для решти: зазвичай 1
    fire_zones_count: int = Field(default=1, ge=1)
    
    # Резерв шлейфів (НПА-3 у опитувальнику)
    reserve_loops: int = Field(default=DEFAULT_RESERVE_LOOPS, ge=0)
    
    # Резерв адрес у шлейфі (% від необхідної ємності)
    reserve_addresses_pct: int = Field(default=DEFAULT_RESERVE_ADDRESSES_PCT, ge=0, le=100)
    
    # Перспектива розширення (наприклад "будинок 1" або "ІІІ черга" у Замковій)
    expansion_notes: Optional[str] = None
    
    # Нормативне обґрунтування
    npa_justification: Optional[str] = None


class NPAArchitecture(BaseModel):
    """
    Принципова архітектура системи: список NPA-зон з власними ППКП.
    
    Якщо не задано — алгоритм працює у режимі "1 ППКП на об'єкт" (простий режим).
    Якщо задано — алгоритм формує комплекс з кількох ППКП за описом.
    """
    zones: list[NPAZone] = Field(default_factory=list)
    
    # Розподіл I/O сигналів між зонами (опитувальник NPA-2)
    io_allocation: IOSignalAllocation = Field(default_factory=IOSignalAllocation)
    
    # Загальні нотатки про архітектуру (з ТЗ)
    architecture_notes: Optional[str] = None
    
    def is_multi_panel(self) -> bool:
        """Чи задана архітектура з кількома ППКП"""
        return len([z for z in self.zones if z.requires_independent_panel]) > 1


# ═══════════════════════════════════════════════════════════════════
# КОРЕНЕВИЙ ВХІДНИЙ СТЕЙТ
# ═══════════════════════════════════════════════════════════════════


class ObjectState(BaseModel):
    """Повний стейт об'єкта — вхід движка розрахунку"""
    session_id: str
    language: str = "uk"
    
    pre_object: PreObjectAnswers
    comparison_set: list[str] = Field(
        default_factory=list,
        description="Список manufacturer_id, які увійшли в порівняння (2-5)"
    )
    object: ObjectData
    
    # НОВЕ: принципова архітектура системи (Блок E)
    # Якщо None — простий режим (1 ППКП на об'єкт, як у попередній версії)
    npa_architecture: Optional[NPAArchitecture] = None
    
    # НОВЕ: параметри для розрахунку ТО (опційно)
    # Якщо None — pipeline не обчислює ТО для виробників
    maintenance_params: Optional[dict] = Field(
        default=None,
        description=(
            "Параметри ТО (dict-серіалізація MaintenanceParams). "
            "Якщо вказано — pipeline автоматично рахує ТО для кожного виробника. "
            "Використовуємо dict (а не клас), щоб уникнути циклічного імпорту з engine."
        )
    )
