"""
Референсний об'єкт ЖК Замкова для тестування движка

З попередніх дизайн-сесій (compaction summary):
- ~12 500 м² житловий комплекс з паркінгом
- 459 точок детекції
- 80 I/O сигналів (з 20 ШПК × 4 сигнали)
- Очікувані суми CAPEX: Омега ~927k UAH, Cofem ~1356k UAH

Цей референс використовуємо як smoke test движка:
якщо результати відрізняються від відомих — щось зламано в логіці.
"""
from schemas.object_state import (
    ConstructionStage, ExecutiveAutomation, FireHoseCabinetSignals,
    FunctionalZone, Jurisdiction, LifetimeHorizon, ObjectData, ObjectState,
    ObjectType, ParkingDetails, ParkingType, PreObjectAnswers,
    TriState, CriticalZones, FalseAlarmRequirement,
)


ZAMKOVA_BASIC = ObjectState(
    session_id="reference_zamkova_basic",
    language="uk",
    
    # Базовий сценарій — без преміум-вимог (для перевірки в Mode 1)
    pre_object=PreObjectAnswers(
        jurisdictions=[Jurisdiction.UA],
        financing_constraints=TriState.NO,
        international_insurance=TriState.NO,
        lifetime_horizon=LifetimeHorizon.MEDIUM_7_10,
        false_alarm_protection=FalseAlarmRequirement.STANDARD,
        mobile_app_required=TriState.NO,
        cloud_monitoring_required=TriState.NO,
        bms_integration_required=TriState.NO,
    ),
    
    # Порівняння Cofem vs Омега
    comparison_set=["cofem", "omega"],
    
    object=ObjectData(
        object_type=ObjectType.RESIDENTIAL_MIXED,
        stage=ConstructionStage.NEW_CONSTRUCTION,
        phases=1,
        total_area_m2=12500,
        floors_above=9,
        floors_below=1,
        height_m=28,
        
        zones={
            "residential": FunctionalZone(area_m2=8500),
            "commercial_ground": FunctionalZone(area_m2=1200),
            "underground_parking": FunctionalZone(area_m2=2800),
        },
        
        critical_zones=CriticalZones(
            parking=ParkingDetails(
                spaces=445,
                parking_type=ParkingType.UNDERGROUND,
                levels=1,
                gas_suppression_areas=False,
            ),
        ),
        
        executive_automation=ExecutiveAutomation(
            fire_hose_cabinets_count=20,
            fire_hose_cabinet_signals=FireHoseCabinetSignals(
                has_buttons=True,
                has_hose_sensor=True,
                has_door_smk=True,
            ),
            # 20 шаф × 3 сигнали = 60 I/O від ШПК
            # + 20 додаткових (клапани + насоси + ліфти, наближено)
            smoke_dampers=10,
            fire_dampers=10,
            fire_pumps=1,
            smoke_fans=2,
            fire_doors=4,
            elevators_fire_mode=2,
            # Загалом: 60 + 10 + 10 + 1 + 2 + 4 + 2 = 89 (близько до 80 з попередніх сесій)
        ),
    ),
)


# Преміум-сценарій — для тестування адаптивних ваг
ZAMKOVA_PREMIUM = ZAMKOVA_BASIC.model_copy(deep=True)
ZAMKOVA_PREMIUM.session_id = "reference_zamkova_premium"
ZAMKOVA_PREMIUM.pre_object.jurisdictions = [Jurisdiction.UA, Jurisdiction.UK]
ZAMKOVA_PREMIUM.pre_object.international_insurance = TriState.YES
ZAMKOVA_PREMIUM.pre_object.insurance_market = Jurisdiction.UK
ZAMKOVA_PREMIUM.pre_object.lifetime_horizon = LifetimeHorizon.LONG_15_20
ZAMKOVA_PREMIUM.pre_object.false_alarm_protection = FalseAlarmRequirement.PREMIUM
ZAMKOVA_PREMIUM.pre_object.cloud_monitoring_required = TriState.YES
ZAMKOVA_PREMIUM.pre_object.mobile_app_required = TriState.YES
