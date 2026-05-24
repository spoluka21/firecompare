"""
Pydantic-схема каталогу обладнання СПЗ
Відповідає JSON-схемі v0.1 з документа Catalog_Schema_Questionnaire_v01.xlsx

Призначення:
- Валідація даних при додаванні нових виробників
- Однакові вимоги до всіх 11 брендів
- Прозоре відстеження повноти даних (data_status)
"""
from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════


class Tier(str, Enum):
    BUDGET = "budget"
    MID = "mid"
    PREMIUM = "premium"


class SystemType(str, Enum):
    CONVENTIONAL = "conventional"
    ADDRESSABLE_THRESHOLD = "addressable_threshold"
    ALGORITHMIC = "algorithmic"
    MIXED = "mixed"  # для виробників з кількома лініями (Tiras, Артон)


class CertificationStatus(str, Enum):
    FULL = "full"  # повна сертифікація
    PARTIAL = "partial"  # часткова / окремі SKU
    IN_PROCESS = "in_process"  # в процесі (Cofem ДСТУ)
    NONE = "none"  # відсутня


class DataStatus(str, Enum):
    COMPLETE = "complete"  # дані повні
    PRELIMINARY = "preliminary"  # дані попередні, потребують уточнення
    STARTER = "starter"  # стартові / мінімальні


class PricingStatus(str, Enum):
    CONFIRMED = "confirmed"  # з фактичного КП
    QUOTED = "quoted"  # з пропозиції постачальника
    ESTIMATED = "estimated"  # оцінка з відкритих джерел


class FeatureSupport(str, Enum):
    NATIVE = "native"  # нативна підтримка виробником
    GATEWAY = "gateway"  # через зовнішній шлюз
    PARTNER = "partner"  # через сертифікованого партнера
    NONE = "none"  # відсутня


class FalseAlarmLevel(str, Enum):
    BASIC = "basic"  # стандарт ДСТУ EN 54
    ENHANCED = "enhanced"  # покращений (адаптивні пороги, drift compensation)
    PREMIUM = "premium"  # преміум (multi-sensor fusion, ASA, ISP)


class PanelType(str, Enum):
    COMPACT = "compact"  # моноблок
    MODULAR = "modular"  # модульна
    HYBRID = "hybrid"  # компакт з можливістю розширення


class DetectorType(str, Enum):
    SMOKE_OPTICAL = "smoke_optical"
    SMOKE_IONIZATION = "smoke_ionization"
    HEAT_MAX = "heat_max"
    HEAT_DIFFERENTIAL = "heat_differential"
    MULTI_SENSOR = "multi_sensor"
    FLAME = "flame"
    BEAM = "beam"
    ASPIRATING = "aspirating"
    GAS = "gas"


class IOModuleType(str, Enum):
    INPUT = "input"  # тільки входи
    OUTPUT = "output"  # тільки виходи (реле)
    COMBINED = "combined"  # входи + виходи
    CONV_ZONE = "conv_zone"  # перетворювач конвенційного шлейфа
    ISOLATOR = "isolator"  # ізолятор петлі (якщо окремий)
    UNIVERSAL = "universal"


# ═══════════════════════════════════════════════════════════════════
# СЕРТИФІКАЦІЇ
# ═══════════════════════════════════════════════════════════════════


class JurisdictionCert(BaseModel):
    """Сертифікація для однієї юрисдикції"""
    status: CertificationStatus
    notes: Optional[str] = None
    certified_parts: list[str] = Field(
        default_factory=list,
        description="Частини EN 54: ['-2', '-4', '-7', ...]"
    )
    certification_body: Optional[str] = None  # AENOR, VdS, BSI, LPCB, Dedal...
    valid_until: Optional[date] = None


class Certifications(BaseModel):
    """Сертифікації за 4 юрисдикціями"""
    EU_EN54: JurisdictionCert
    UA_DSTU_EN54: JurisdictionCert
    UK_BS_LPCB: JurisdictionCert
    US_UL_FM: JurisdictionCert
    iso_9001: Optional[str] = None  # версія + орган


# ═══════════════════════════════════════════════════════════════════
# ФУНКЦІОНАЛЬНІ ХАРАКТЕРИСТИКИ
# ═══════════════════════════════════════════════════════════════════


class BMSIntegration(BaseModel):
    """Підтримка протоколів BMS-інтеграції"""
    bacnet: FeatureSupport = FeatureSupport.NONE
    modbus_rtu: FeatureSupport = FeatureSupport.NONE
    modbus_tcp: FeatureSupport = FeatureSupport.NONE
    opc_ua: FeatureSupport = FeatureSupport.NONE
    knx: FeatureSupport = FeatureSupport.NONE


class CloudMonitoring(BaseModel):
    available: bool = False
    platform_name: Optional[str] = None  # "Cofem Remote", "Desigo CC", тощо
    notes: Optional[str] = None


class MobileApp(BaseModel):
    available: bool = False
    platforms: list[str] = Field(default_factory=list)  # ["iOS", "Android"]
    notes: Optional[str] = None


class Redundancy(BaseModel):
    panel_controller: bool = False
    network: bool = False
    loop: bool = False
    notes: Optional[str] = None


class Features(BaseModel):
    """Функціональні характеристики виробника (загалом по лінійках)"""
    false_alarm_level: FalseAlarmLevel
    false_alarm_technologies: list[str] = Field(
        default_factory=list,
        description="drift_compensation, adaptive_thresholds, multi_sensor_fusion, ISP, ASA..."
    )
    cloud_monitoring: CloudMonitoring
    mobile_app: MobileApp
    bms_integration: BMSIntegration
    voice_alarm: FeatureSupport
    wireless_extension: bool = False
    redundancy: Redundancy


# ═══════════════════════════════════════════════════════════════════
# КОМПОНЕНТИ — ППКП
# ═══════════════════════════════════════════════════════════════════


class Panel(BaseModel):
    """Один ППКП у лінійці виробника"""
    panel_id: str  # внутрішній ID, наприклад "cofem_compact_lyon"
    model_name: str  # "Compact Lyon (Zafir)"
    panel_type: PanelType
    
    # КРИТИЧНО для розрахунку
    max_loops: int = Field(ge=1, description="Максимальна кількість петель")
    devices_per_loop: int = Field(ge=1, description="Максимум адресних пристроїв (детекторів) на петлю")
    max_total_devices: int = Field(ge=1)
    
    # Релейні (інженерні) пристрої — окреме обмеження, на вогнестійких шлейфах.
    # relay_limit_scope визначає, як трактувати relay_devices_limit:
    #   "per_loop"  — обмеження на КОЖНУ петлю (Rubí, Quartz, Zafir, Onyx тощо)
    #   "per_panel" — обмеження на ВЕСЬ прилад (Cofem Lyon Remote: релейні не множать шлейфи)
    # Якщо None — релейних даних немає, застосовується консервативна оцінка
    # (релейні займають загальну ємність devices_per_loop).
    relay_devices_limit: Optional[int] = Field(default=None, ge=0)
    relay_limit_scope: Optional[str] = Field(default=None)  # "per_loop" | "per_panel" | None
    
    # Експлуатаційні
    polling_time_ms: Optional[int] = None
    max_loop_length_m: Optional[int] = None
    battery_max_ah: Optional[float] = None
    battery_monitoring_en54_4: bool = False
    
    # Мережа
    network_max_panels: int = Field(ge=1, default=1)
    interfaces: list[str] = Field(default_factory=list)  # RS232, RS485, Ethernet
    
    # Фізичні
    operating_temp_min_c: Optional[int] = None
    operating_temp_max_c: Optional[int] = None
    ip_rating: Optional[str] = None
    operating_voltage_vdc: Optional[str] = None  # "20.5-28.6"
    
    # Ціна
    price_uah_no_vat: Optional[float] = None
    pricing_status: PricingStatus = PricingStatus.ESTIMATED
    pricing_notes: Optional[str] = None
    
    @field_validator("max_total_devices")
    @classmethod
    def check_total_consistency(cls, v: int, info) -> int:
        """max_total_devices не може бути більшим за max_loops × devices_per_loop"""
        data = info.data
        if "max_loops" in data and "devices_per_loop" in data:
            theoretical_max = data["max_loops"] * data["devices_per_loop"]
            if v > theoretical_max:
                raise ValueError(
                    f"max_total_devices ({v}) перевищує max_loops × devices_per_loop "
                    f"({data['max_loops']} × {data['devices_per_loop']} = {theoretical_max})"
                )
        return v


# ═══════════════════════════════════════════════════════════════════
# КОМПОНЕНТИ — ДЕТЕКТОРИ
# ═══════════════════════════════════════════════════════════════════


class Detector(BaseModel):
    """Адресний (або конвенційний) детектор"""
    detector_id: str
    model_name: str
    detector_type: DetectorType
    
    # Електричні
    loop_powered: bool = True
    current_idle_ma: Optional[float] = None
    current_alarm_ma: Optional[float] = None
    
    # Фізичні
    operating_temp_min_c: Optional[int] = None
    operating_temp_max_c: Optional[int] = None
    ip_rating: Optional[str] = None
    
    # Алгоритмічні особливості
    algorithmic_features: list[str] = Field(
        default_factory=list,
        description="drift_compensation, day_night_modes, adaptive_thresholds..."
    )
    
    # Сумісність панелей
    compatible_panel_ids: list[str] = Field(default_factory=list)
    
    # Ціна
    price_uah_no_vat: Optional[float] = None
    pricing_status: PricingStatus = PricingStatus.ESTIMATED


# ═══════════════════════════════════════════════════════════════════
# КОМПОНЕНТИ — I/O МОДУЛІ (НАЙВАЖЛИВІШИЙ БЛОК)
# ═══════════════════════════════════════════════════════════════════


class IOModule(BaseModel):
    """Адресний модуль входів/виходів — КРИТИЧНИЙ для архітектурного аналізу"""
    module_id: str
    model_name: str
    module_type: IOModuleType
    
    # Функціональні характеристики
    inputs_count: int = Field(ge=0, default=0)
    outputs_count: int = Field(ge=0, default=0)
    
    # КРИТИЧНЕ ПОЛЕ ДЛЯ АРХІТЕКТУРНОГО АНАЛІЗУ
    address_consumption: int = Field(
        ge=1,
        description="Скільки адрес у петлі займає модуль. "
                    "1 для Cofem MSTAY8/MDA2YLT, 4 для Омега БСА/БКА"
    )
    
    # Технічні характеристики виходів
    output_type: Optional[str] = None  # "relay", "ssr", "voltage_free", "open_collector"
    output_supervised: bool = False  # моніторинг лінії
    output_max_voltage_v: Optional[float] = None
    output_max_current_a: Optional[float] = None
    
    # Живлення
    needs_external_power: bool = False
    external_voltage_v: Optional[float] = None  # 24 typically
    
    # Сумісність
    compatible_panel_ids: list[str] = Field(default_factory=list)
    
    # Ціна
    price_uah_no_vat: Optional[float] = None
    pricing_status: PricingStatus = PricingStatus.ESTIMATED
    
    @field_validator("inputs_count")
    @classmethod
    def check_inputs_for_type(cls, v: int, info) -> int:
        """Перевірка консистентності inputs/outputs з типом"""
        data = info.data
        if "module_type" in data:
            mt = data["module_type"]
            if mt == IOModuleType.OUTPUT and v > 0:
                raise ValueError(f"Тип {mt} не може мати входи")
        return v
    
    @field_validator("outputs_count")
    @classmethod
    def check_outputs_for_type(cls, v: int, info) -> int:
        data = info.data
        if "module_type" in data:
            mt = data["module_type"]
            if mt == IOModuleType.INPUT and v > 0:
                raise ValueError(f"Тип {mt} не може мати виходи")
        return v


# ═══════════════════════════════════════════════════════════════════
# КОМПОНЕНТИ — ОПОВІЩУВАЧІ
# ═══════════════════════════════════════════════════════════════════


class Sounder(BaseModel):
    """Адресний звуковий/світловий сповіщувач"""
    sounder_id: str
    model_name: str
    has_sound: bool = True
    has_strobe: bool = False
    en54_23_category: Optional[str] = None  # "W-2.4-6", "C-3-15", "O"
    address_consumption: int = Field(ge=1, default=1)
    loop_powered: bool = True
    
    price_uah_no_vat: Optional[float] = None
    pricing_status: PricingStatus = PricingStatus.ESTIMATED


class ManualCallPoint(BaseModel):
    """Адресна ручна кнопка (MCP)"""
    mcp_id: str
    model_name: str
    has_integrated_isolator: bool = False
    address_consumption: int = Field(ge=1, default=1)
    
    price_uah_no_vat: Optional[float] = None
    pricing_status: PricingStatus = PricingStatus.ESTIMATED


class PowerSupply(BaseModel):
    """Зовнішній УЕЖ"""
    psu_id: str
    model_name: str
    capacity_a: float = Field(gt=0)
    battery_max_ah: float = Field(gt=0)
    en54_4_certified: bool = True
    
    price_uah_no_vat: Optional[float] = None
    pricing_status: PricingStatus = PricingStatus.ESTIMATED


# ═══════════════════════════════════════════════════════════════════
# ВИРОБНИК — ВЕРХНІЙ РІВЕНЬ
# ═══════════════════════════════════════════════════════════════════


class UADistributor(BaseModel):
    """Український дистриб'ютор виробника"""
    company_name: Optional[str] = None
    contact: Optional[str] = None
    service_cities: list[str] = Field(default_factory=list)
    response_time_hours: Optional[int] = None


class Manufacturer(BaseModel):
    """Кореневий запис виробника СПЗ"""
    # Ідентифікатори
    manufacturer_id: str  # slug: "cofem", "tiras", "schrack"
    name_ua: str
    name_en: str
    country_iso2: str = Field(min_length=2, max_length=2)
    founded_year: Optional[int] = None
    
    # Класифікація
    tier: Tier
    system_type: SystemType
    
    # Гарантія і сервіс
    warranty_months: int = Field(ge=12, le=120)
    extended_warranty_available: bool = False
    ua_distributor: UADistributor = Field(default_factory=UADistributor)
    
    # Реєстрові поля
    data_status: DataStatus
    last_updated: date
    notes_internal: Optional[str] = None  # внутрішні нотатки команди
    notes_strengths: list[str] = Field(default_factory=list)
    notes_weaknesses: list[str] = Field(default_factory=list)
    
    # Категорії — об'єкти
    certifications: Certifications
    features: Features
    
    # ── Maintenance-специфічні параметри (для розрахунку ТО) ──
    # Знижка часу планового ТО за рахунок технології (наприклад, лабіринтні корпуси не треба чистити)
    maintenance_time_modifier: float = Field(
        default=1.0, ge=0.5, le=1.5,
        description="0.8 = 20% знижка часу ТО (Cofem labyrinth); 1.0 = стандарт; 1.2 = +20% (старі технології)"
    )
    # Середня вартість заміни одного компонента при пошкодженні
    avg_part_replacement_cost_uah: float = Field(
        default=800.0, ge=0,
        description="Середня вартість заміни 1 детектора/модуля при пошкодженні (грн)"
    )
    # Швидкість реакції — модифікатор. 1.0 = стандарт. 1.2 = далі поставляється з ЄС → потенційно довша реакція
    service_response_modifier: float = Field(
        default=1.0, ge=0.8, le=1.5,
        description="1.0 = UA-склад; 1.2 = регіональний дистриб'ютор; 1.5 = тільки із ЄС"
    )
    
    # Списки компонентів
    panels: list[Panel] = Field(default_factory=list)
    detectors: list[Detector] = Field(default_factory=list)
    io_modules: list[IOModule] = Field(default_factory=list)
    sounders: list[Sounder] = Field(default_factory=list)
    manual_call_points: list[ManualCallPoint] = Field(default_factory=list)
    power_supplies: list[PowerSupply] = Field(default_factory=list)
    
    def completeness_report(self) -> dict:
        """Звіт про повноту даних виробника"""
        return {
            "manufacturer_id": self.manufacturer_id,
            "data_status": self.data_status,
            "panels_count": len(self.panels),
            "detectors_count": len(self.detectors),
            "io_modules_count": len(self.io_modules),
            "sounders_count": len(self.sounders),
            "mcps_count": len(self.manual_call_points),
            "power_supplies_count": len(self.power_supplies),
            "has_complete_panel_pricing": all(
                p.pricing_status != PricingStatus.ESTIMATED for p in self.panels
            ) if self.panels else False,
            "has_io_address_consumption": all(
                m.address_consumption > 0 for m in self.io_modules
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# КОРЕНЕВИЙ КАТАЛОГ
# ═══════════════════════════════════════════════════════════════════


class Catalog(BaseModel):
    """Кореневий каталог усіх виробників"""
    catalog_version: str = "0.1.0"
    last_updated: date
    manufacturers: list[Manufacturer]
    
    def get_by_id(self, manufacturer_id: str) -> Optional[Manufacturer]:
        return next(
            (m for m in self.manufacturers if m.manufacturer_id == manufacturer_id),
            None
        )
    
    def manufacturers_by_status(self, status: DataStatus) -> list[Manufacturer]:
        return [m for m in self.manufacturers if m.data_status == status]
    
    def overall_completeness(self) -> dict:
        """Звіт про повноту каталогу в цілому"""
        return {
            "total_manufacturers": len(self.manufacturers),
            "complete": len(self.manufacturers_by_status(DataStatus.COMPLETE)),
            "preliminary": len(self.manufacturers_by_status(DataStatus.PRELIMINARY)),
            "starter": len(self.manufacturers_by_status(DataStatus.STARTER)),
            "ready_for_mvp": len([
                m for m in self.manufacturers
                if m.data_status in (DataStatus.COMPLETE, DataStatus.PRELIMINARY)
            ]),
        }
