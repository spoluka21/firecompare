"""
Каталог Варта (Електронмаш) — оновлено з реальних прайсів (11.05.2026)
Джерело: FireCompare_Catalog_Forms.xlsx
"""
from datetime import date

from schemas.catalog import (
    BMSIntegration, Certifications, CertificationStatus, CloudMonitoring,
    DataStatus, Detector, DetectorType, FalseAlarmLevel, FeatureSupport,
    Features, IOModule, IOModuleType, JurisdictionCert, ManualCallPoint,
    Manufacturer, MobileApp, Panel, PanelType, PricingStatus, Redundancy,
    Sounder, SystemType, Tier, UADistributor,
)


VARTA = Manufacturer(
    manufacturer_id="varta",
    name_ua="Варта (Електронмаш)",
    name_en="Varta (Elektronmash)",
    country_iso2="UA",
    tier=Tier.MID,
    system_type=SystemType.MIXED,
    warranty_months=36,
    ua_distributor=UADistributor(
        company_name="СКБ Електронмаш (Київ)",
        service_cities=["Київ", "Дніпро", "Львів", "Одеса"],
        response_time_hours=48,
    ),
    data_status=DataStatus.COMPLETE,
    last_updated=date(2026, 5, 11),
    notes_internal="Ціни з FireCompare_Catalog_Forms.xlsx",
    notes_strengths=[
        "Українське виробництво — швидка логістика",
        "Найбільша адресна ємність серед UA-брендів (1905 адрес)",
        "Дві лінійки (конвенційна + адресна)",
        "Модульна архітектура з блоками розширення (CV1510, CV1514)",
        "Найдешевший конвенційний ППКП в каталозі",
    ],
    notes_weaknesses=[
        "Менша сервісна мережа порівняно з Tiras",
        "Базовий захист від хибних спрацювань",
        "Відсутність хмари і мобільного застосунку",
        "Відсутня міжнародна сертифікація",
    ],
    certifications=Certifications(
        EU_EN54=JurisdictionCert(status=CertificationStatus.PARTIAL),
        UA_DSTU_EN54=JurisdictionCert(status=CertificationStatus.FULL,
                                       certified_parts=["-2", "-4", "-7", "-17"]),
        UK_BS_LPCB=JurisdictionCert(status=CertificationStatus.NONE),
        US_UL_FM=JurisdictionCert(status=CertificationStatus.NONE),
        iso_9001="ISO 9001:2015",
    ),
    features=Features(
        false_alarm_level=FalseAlarmLevel.BASIC,
        false_alarm_technologies=[],
        cloud_monitoring=CloudMonitoring(available=False),
        mobile_app=MobileApp(available=False),
        bms_integration=BMSIntegration(modbus_rtu=FeatureSupport.GATEWAY),
        voice_alarm=FeatureSupport.NONE,
        wireless_extension=False,
        redundancy=Redundancy(),
    ),
    
    # Maintenance: український виробник, BASIC рівень
    maintenance_time_modifier=1.1,  # +10% — стандартні детектори, очищення
    avg_part_replacement_cost_uah=450.0,
    service_response_modifier=0.9,  # локальний склад
    
    panels=[
        Panel(panel_id="varta_adres", model_name="Варта-Адрес",
              panel_type=PanelType.MODULAR, max_loops=15, devices_per_loop=127, max_total_devices=1905,
              interfaces=["RS485"],
              price_uah_no_vat=34410.0, pricing_status=PricingStatus.QUOTED,
              pricing_notes="Модульна, розширюється CV1510"),
        Panel(panel_id="varta_adres_cv1500", model_name="Варта-Адрес CV1500",
              panel_type=PanelType.COMPACT, max_loops=4, devices_per_loop=127, max_total_devices=508,
              interfaces=["RS485"],
              price_uah_no_vat=59184.0, pricing_status=PricingStatus.QUOTED,
              pricing_notes="Компактний корпус"),
        Panel(panel_id="varta_1_2", model_name="Варта-1/2",
              panel_type=PanelType.COMPACT, max_loops=2, devices_per_loop=20, max_total_devices=40,
              interfaces=["RS485"],
              price_uah_no_vat=5988.0, pricing_status=PricingStatus.QUOTED,
              pricing_notes="Безадресна, малі об'єкти"),
        Panel(panel_id="varta_1_4", model_name="Варта-1/4",
              panel_type=PanelType.COMPACT, max_loops=4, devices_per_loop=20, max_total_devices=80,
              interfaces=["RS485"],
              price_uah_no_vat=6552.0, pricing_status=PricingStatus.QUOTED),
        Panel(panel_id="varta_1_8", model_name="Варта-1/8",
              panel_type=PanelType.COMPACT, max_loops=8, devices_per_loop=20, max_total_devices=160,
              interfaces=["RS485"],
              price_uah_no_vat=6846.0, pricing_status=PricingStatus.QUOTED),
        Panel(panel_id="varta_1_816", model_name="Варта-1/816",
              panel_type=PanelType.COMPACT, max_loops=16, devices_per_loop=20, max_total_devices=320,
              interfaces=["RS485"],
              price_uah_no_vat=9774.0, pricing_status=PricingStatus.QUOTED),
        Panel(panel_id="varta_1_832", model_name="Варта-1/832",
              panel_type=PanelType.COMPACT, max_loops=32, devices_per_loop=20, max_total_devices=640,
              interfaces=["RS485"],
              price_uah_no_vat=25284.0, pricing_status=PricingStatus.QUOTED),
    ],
    detectors=[
        Detector(detector_id="varta_ipd_a", model_name="ИПД-А",
                 detector_type=DetectorType.SMOKE_OPTICAL, loop_powered=True,
                 compatible_panel_ids=["varta_adres", "varta_adres_cv1500"],
                 price_uah_no_vat=1098.0, pricing_status=PricingStatus.QUOTED),
        Detector(detector_id="varta_ipt_a", model_name="ИПТ-А",
                 detector_type=DetectorType.HEAT_MAX, loop_powered=True,
                 compatible_panel_ids=["varta_adres", "varta_adres_cv1500"],
                 price_uah_no_vat=1098.0, pricing_status=PricingStatus.QUOTED),
        Detector(detector_id="varta_ipk_8", model_name="ИПК-8",
                 detector_type=DetectorType.SMOKE_OPTICAL, loop_powered=True,
                 compatible_panel_ids=["varta_1_2", "varta_1_4", "varta_1_8",
                                       "varta_1_816", "varta_1_832"],
                 price_uah_no_vat=288.0, pricing_status=PricingStatus.QUOTED,
                 # Найдешевший димовий — для конвенційних
                 ),
        Detector(detector_id="varta_ipk_9", model_name="ИПК-9",
                 detector_type=DetectorType.HEAT_MAX, loop_powered=True,
                 compatible_panel_ids=["varta_1_2", "varta_1_4", "varta_1_8",
                                       "varta_1_816", "varta_1_832"],
                 price_uah_no_vat=282.0, pricing_status=PricingStatus.QUOTED),
    ],
    io_modules=[
        IOModule(module_id="varta_cv1514", model_name="CV1514",
                 module_type=IOModuleType.COMBINED, inputs_count=4, outputs_count=2,
                 output_type="relay", address_consumption=2,
                 compatible_panel_ids=["varta_adres", "varta_adres_cv1500"],
                 price_uah_no_vat=7728.0, pricing_status=PricingStatus.QUOTED),
        IOModule(module_id="varta_cv1510", model_name="CV1510",
                 module_type=IOModuleType.UNIVERSAL, inputs_count=4, outputs_count=4,
                 output_type="relay", address_consumption=4,
                 compatible_panel_ids=["varta_adres"],
                 price_uah_no_vat=9450.0, pricing_status=PricingStatus.QUOTED,
                 # Модуль розширення з додатковими шлейфами
                 ),
    ],
    sounders=[
        Sounder(sounder_id="varta_zpo", model_name="ЗПО",
                has_sound=True, has_strobe=False, address_consumption=1, loop_powered=False,
                price_uah_no_vat=360.0, pricing_status=PricingStatus.QUOTED),
    ],
    manual_call_points=[
        ManualCallPoint(mcp_id="varta_ipr_a", model_name="ИПР-А",
                        has_integrated_isolator=False, address_consumption=1,
                        price_uah_no_vat=1332.0, pricing_status=PricingStatus.QUOTED),
    ],
    power_supplies=[],
)
