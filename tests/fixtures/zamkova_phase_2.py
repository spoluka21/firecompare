"""
ЖК Замкова — II черга з ПОВНОЮ NPA-АРХІТЕКТУРОЮ
Джерело: Експертний звіт ТОВ "ПРОЕКСП" № V-0103-20 від 21.05.2020
Принципова архітектура: за робочим проектом (3 незалежні ППКП)

ЗАХИЩУВАНІ ЗОНИ:
═══════════════════════════════════════════════════════════════════════
  Торгово-офісні: 4 043 м² (subdivided, r=25, МЗК 20%)
  Підземний паркінг: 10 031 м² (open, теплові)
  Захищувана площа: 14 074 м²

NPA-АРХІТЕКТУРА (з ТЗ Cofem-проекту):
═══════════════════════════════════════════════════════════════════════
  ППКП №1 "QUARTZ" — Укриття цивільного захисту
    - Незалежний прилад
    - 2 шлейфи × 99 адрес (на випадок розширення зони укриття)
    - Резерв: 1 шлейф, 30% адрес

  ППКП №2 "LYON REMOTE 8" — Підземний паркінг
    - 8 шлейфів × 226 адрес
    - 5 контрольованих зон детекції (за пожежними зонами)
    - 2 шлейфи на I/O (ШПК, клапани, димовидалення, АПГ)
    - 1 шлейф резерв
    - Резерв: 20% адрес

  ППКП №3 "LYON REMOTE 6" — Головний ППКП
    - 6 шлейфів × 226 адрес
    - 1 шлейф — торгово-офісні приміщення
    - 1 шлейф — I/O модулі (газоаналізатори, ліфти, двері)
    - 1 шлейф — паркінг (мережева взаємодія)
    - 1 шлейф — резерв для Будинку 1 (І черга)
    - 1 шлейф — резерв для ІІІ черги
    - 1 шлейф — резерв
    - Резерв: 30% адрес

УСЬОГО: 3 ППКП, 16 шлейфів
"""
from schemas.object_state import (
    CertificationRequirement, ConstructionStage, CriticalZones, ExecutiveAutomation,
    FalseAlarmRequirement, FireHoseCabinetSignals, FunctionalZone,
    IOSignalAllocation, Jurisdiction, LifetimeHorizon, NPAArchitecture,
    NPAZone, NPAZoneType, ObjectData, ObjectState, ObjectType,
    ParkingDetails, ParkingType, PreObjectAnswers, SubdivisionType,
    TriState,
)


ZAMKOVA_PHASE_2 = ObjectState(
    session_id="zamkova_phase_2_real",
    language="uk",
    
    pre_object=PreObjectAnswers(
        certification_requirement=CertificationRequirement.UA,
        jurisdictions=[Jurisdiction.UA],
        financing_constraints=TriState.NO,
        international_insurance=TriState.NO,
        lifetime_horizon=LifetimeHorizon.LONG_15_20,
        false_alarm_protection=FalseAlarmRequirement.STANDARD,
        mobile_app_required=TriState.NICE_TO_HAVE,
        cloud_monitoring_required=TriState.NICE_TO_HAVE,
        bms_integration_required=TriState.NO,
    ),
    
    comparison_set=["cofem", "omega", "tiras", "varta"],
    
    object=ObjectData(
        object_type=ObjectType.RESIDENTIAL_MIXED,
        stage=ConstructionStage.NEW_CONSTRUCTION,
        phases=1,
        total_area_m2=14074,  # захищувана: 4043 + 10031
        floors_above=9,
        floors_below=1,
        height_m=30.0,
        
        zones={
            "commercial_ground": FunctionalZone(
                area_m2=4043,
                subdivision_type=SubdivisionType.SUBDIVIDED,
                avg_room_area_m2=25.0,
                common_areas_share=0.20,
            ),
            "underground_parking": FunctionalZone(
                area_m2=10031,
                subdivision_type=SubdivisionType.OPEN,
            ),
        },
        
        critical_zones=CriticalZones(
            parking=ParkingDetails(
                spaces=245,
                parking_type=ParkingType.UNDERGROUND,
                levels=1,
                gas_suppression_areas=False,
            ),
        ),
        
        executive_automation=ExecutiveAutomation(
            fire_hose_cabinets_count=20,
            fire_hose_cabinet_signals=FireHoseCabinetSignals(
                has_buttons=True, has_hose_sensor=True, has_door_smk=True,
            ),
            smoke_dampers=30,
            fire_dampers=25,
            fire_pumps=4,
            smoke_fans=6,
            fire_doors=12,
            elevators_fire_mode=4,
            other_actuators=8,
            other_description=(
                "Газоаналізатори і клапани-відсікачі в 2 котельнях, "
                "виходи на ПЦС, шафи ліфтів, установка водяного пожежогасіння паркінгу"
            ),
        ),
        
        additional_notes=(
            "II черга з ПОВНИМ підземним паркінгом. Захищувана площа 14 074 м². "
            "NPA-архітектура: 3 незалежні ППКП (Quartz укриття + Lyon Remote 8 паркінг + "
            "Lyon Remote 6 головний)."
        ),
    ),
    
    # ═══════════════════════════════════════════════════════════════════
    # NPA-АРХІТЕКТУРА (з робочого проекту)
    # ═══════════════════════════════════════════════════════════════════
    npa_architecture=NPAArchitecture(
        zones=[
            NPAZone(
                zone_id="shelter",
                zone_type=NPAZoneType.SHELTER,
                name="Укриття цивільного захисту",
                name_en="Civil defense shelter",
                requires_independent_panel=True,
                area_m2=500,  # орієнтовно (входить у площу паркінгу)
                functional_zones=[],  # підмножина паркінгу, без власного FunctionalZone
                fire_zones_count=1,
                reserve_loops=1,
                reserve_addresses_pct=30,  # на розширення зони укриття
                npa_justification=(
                    "Незалежність працездатності за вимогами цивільного захисту. "
                    "Запит замовника: можливість розширення зони укриття."
                ),
            ),
            NPAZone(
                zone_id="parking",
                zone_type=NPAZoneType.PARKING,
                name="Підземний паркінг",
                name_en="Underground parking",
                requires_independent_panel=True,
                area_m2=10031,
                functional_zones=["underground_parking"],
                # 10031 м² / 2500 м² на зону ≈ 4-5 → беремо 5 (за реальним ТЗ)
                fire_zones_count=5,
                reserve_loops=1,
                reserve_addresses_pct=20,
                npa_justification=(
                    "ДБН В.2.3-15: підземний паркінг — окрема СПЗ. "
                    "5 пожежних зон + 2 шлейфи на I/O (ШПК, клапани, АПГ) + 1 резерв = 8 шлейфів."
                ),
            ),
            NPAZone(
                zone_id="main",
                zone_type=NPAZoneType.MAIN,
                name="Головний ППКП (торгово-офіс + резерв)",
                name_en="Main control panel (commercial + reserve)",
                requires_independent_panel=True,
                area_m2=4043,
                functional_zones=["commercial_ground"],
                fire_zones_count=1,
                reserve_loops=3,  # для Будинку 1, ІІІ черги, та просто резерв
                reserve_addresses_pct=30,
                expansion_notes=(
                    "Резерв на: Будинок 1 (І черга), Будинки 4-5 (ІІІ черга), "
                    "потенційно громадська будівля (ІV черга)"
                ),
                npa_justification=(
                    "Головний ППКП комплексу для торгово-офісної частини, "
                    "збору сигналів від I/O модулів і взаємодії з підлеглими ППКП."
                ),
            ),
        ],
        # Розподіл I/O сигналів між ППКП (за функціональною локалізацією)
        io_allocation=IOSignalAllocation(
            shelter_share=0.05,   # ~10-15 сигналів
            parking_share=0.55,   # ~120 сигналів (ШПК, клапани, АПГ, насоси)
            main_share=0.40,      # ~90 сигналів (газоаналізатори, ліфти, двері)
        ),
        architecture_notes=(
            "Принципова архітектура за робочим проектом Cofem: 3 незалежні ППКП, "
            "16 шлейфів. Окремий резерв для майбутніх черг будівництва."
        ),
    ),
)


ZAMKOVA_PHASE_2_PREMIUM = ZAMKOVA_PHASE_2.model_copy(deep=True)
ZAMKOVA_PHASE_2_PREMIUM.session_id = "zamkova_phase_2_premium"
ZAMKOVA_PHASE_2_PREMIUM.pre_object.certification_requirement = CertificationRequirement.UA_EU
ZAMKOVA_PHASE_2_PREMIUM.pre_object.jurisdictions = [Jurisdiction.UA, Jurisdiction.EU]
ZAMKOVA_PHASE_2_PREMIUM.pre_object.international_insurance = TriState.YES
ZAMKOVA_PHASE_2_PREMIUM.pre_object.insurance_market = Jurisdiction.EU
ZAMKOVA_PHASE_2_PREMIUM.pre_object.false_alarm_protection = FalseAlarmRequirement.PREMIUM
ZAMKOVA_PHASE_2_PREMIUM.pre_object.cloud_monitoring_required = TriState.YES
ZAMKOVA_PHASE_2_PREMIUM.pre_object.mobile_app_required = TriState.YES


# Простий режим (без NPA) — для порівняння з тим, що було
ZAMKOVA_PHASE_2_SIMPLE = ZAMKOVA_PHASE_2.model_copy(deep=True)
ZAMKOVA_PHASE_2_SIMPLE.session_id = "zamkova_phase_2_simple"
ZAMKOVA_PHASE_2_SIMPLE.npa_architecture = None
