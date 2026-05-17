"""
Стартові плейсхолдери для виробників, чиї дані ще збираються
Стан: preliminary (європейські — є архітектура з публічних джерел) або starter (Артон — потребує контакту з виробником)

Кожен запис достатньо повний, щоб пройти валідацію Pydantic, але має поля, які треба наповнити.
data_status маркує, на якому рівні готовності дані.
"""
from datetime import date

from schemas.catalog import (
    BMSIntegration, Certifications, CertificationStatus, CloudMonitoring,
    DataStatus, FalseAlarmLevel, FeatureSupport, Features, JurisdictionCert,
    Manufacturer, MobileApp, Panel, PanelType, PricingStatus, Redundancy,
    SystemType, Tier, UADistributor,
)


# ════════════════════════════════════════════════════════════════════
# BOSCH — preliminary (архітектура є, ціни і UA-конкретика — ні)
# ════════════════════════════════════════════════════════════════════

BOSCH = Manufacturer(
    manufacturer_id="bosch",
    name_ua="Bosch",
    name_en="Bosch",
    country_iso2="DE",
    tier=Tier.PREMIUM,
    system_type=SystemType.ALGORITHMIC,
    warranty_months=24,
    data_status=DataStatus.PRELIMINARY,
    last_updated=date(2026, 5, 11),
    notes_internal="Архітектура AVENAR 2000/8000 з публічних datasheets. Ціни орієнтовні з US/IN ринків.",
    notes_strengths=[
        "LSN improved протокол — 254 пристрої на петлі",
        "AVENAR 8000 — до 8128 пристроїв (велика мережа)",
        "Cloud-ready (Linux-based, IoT)",
        "Voice alarm інтеграція через PRAESENSA",
        "BACnet/OPC/FSI для BMS",
    ],
    notes_weaknesses=[
        "Висока преміум-ціна",
        "Окрема лінійка для US-ринку (FPA-1000/5000)",
        "ДСТУ EN 54 — через дистриб'ютора",
    ],
    certifications=Certifications(
        EU_EN54=JurisdictionCert(
            status=CertificationStatus.FULL,
            certified_parts=["-2", "-4"],
            certification_body="VdS",
        ),
        UA_DSTU_EN54=JurisdictionCert(status=CertificationStatus.PARTIAL),
        UK_BS_LPCB=JurisdictionCert(status=CertificationStatus.FULL),
        US_UL_FM=JurisdictionCert(status=CertificationStatus.PARTIAL),
        iso_9001="ISO 9001:2015",
    ),
    features=Features(
        false_alarm_level=FalseAlarmLevel.PREMIUM,
        false_alarm_technologies=["ISP", "dual_ray_detection"],
        cloud_monitoring=CloudMonitoring(available=True, platform_name="Bosch Connected"),
        mobile_app=MobileApp(available=True, platforms=["iOS", "Android"]),
        bms_integration=BMSIntegration(
            bacnet=FeatureSupport.NATIVE,
            modbus_rtu=FeatureSupport.GATEWAY,
            modbus_tcp=FeatureSupport.NATIVE,
            opc_ua=FeatureSupport.NATIVE,
        ),
        voice_alarm=FeatureSupport.NATIVE,
        wireless_extension=True,
        redundancy=Redundancy(network=True),
    ),
    panels=[
        Panel(
            panel_id="bosch_avenar_2000",
            model_name="AVENAR 2000",
            panel_type=PanelType.MODULAR,
            max_loops=4,
            devices_per_loop=254,
            max_total_devices=1016,
            network_max_panels=32,
            interfaces=["Ethernet", "RS485"],
            pricing_status=PricingStatus.ESTIMATED,
        ),
        Panel(
            panel_id="bosch_avenar_8000",
            model_name="AVENAR 8000",
            panel_type=PanelType.MODULAR,
            max_loops=32,
            devices_per_loop=254,
            max_total_devices=8128,
            network_max_panels=32,
            interfaces=["Ethernet", "RS485", "USB"],
            pricing_status=PricingStatus.ESTIMATED,
        ),
    ],
)


# ════════════════════════════════════════════════════════════════════
# SIEMENS — preliminary
# ════════════════════════════════════════════════════════════════════

SIEMENS = Manufacturer(
    manufacturer_id="siemens",
    name_ua="Siemens Cerberus",
    name_en="Siemens Cerberus PRO",
    country_iso2="CH",
    tier=Tier.PREMIUM,
    system_type=SystemType.ALGORITHMIC,
    warranty_months=24,
    data_status=DataStatus.PRELIMINARY,
    last_updated=date(2026, 5, 11),
    notes_internal="C-NET архітектура з мануалів. Ціни орієнтовні з EU-ринку.",
    notes_strengths=[
        "Глибока інтеграція з Desigo CC (BMS)",
        "Network до 64 панелей у кластері",
        "ASA технологія (Advanced Signal Analysis)",
        "Auto-detection C-NET пристроїв",
        "До 1512 адрес на FC726",
    ],
    notes_weaknesses=[
        "Преміум-цінова політика",
        "UA-дистриб'юція обмежена",
    ],
    certifications=Certifications(
        EU_EN54=JurisdictionCert(
            status=CertificationStatus.FULL,
            certified_parts=["-2", "-4"],
            certification_body="VdS",
        ),
        UA_DSTU_EN54=JurisdictionCert(status=CertificationStatus.PARTIAL),
        UK_BS_LPCB=JurisdictionCert(status=CertificationStatus.FULL),
        US_UL_FM=JurisdictionCert(status=CertificationStatus.PARTIAL),
        iso_9001="ISO 9001:2015",
    ),
    features=Features(
        false_alarm_level=FalseAlarmLevel.PREMIUM,
        false_alarm_technologies=["ASA", "adaptive_thresholds"],
        cloud_monitoring=CloudMonitoring(available=True, platform_name="Cerberus Cloud / Desigo CC"),
        mobile_app=MobileApp(available=True),
        bms_integration=BMSIntegration(
            bacnet=FeatureSupport.NATIVE,
            modbus_rtu=FeatureSupport.GATEWAY,
            modbus_tcp=FeatureSupport.GATEWAY,
            opc_ua=FeatureSupport.NATIVE,
        ),
        voice_alarm=FeatureSupport.NATIVE,
        wireless_extension=False,
        redundancy=Redundancy(panel_controller=True, network=True),
    ),
    panels=[
        Panel(
            panel_id="siemens_fc722",
            model_name="FC722",
            panel_type=PanelType.COMPACT,
            max_loops=4,
            devices_per_loop=126,
            max_total_devices=504,
            network_max_panels=64,
            interfaces=["RS232", "RS485", "Ethernet"],
            operating_temp_min_c=-8,
            operating_temp_max_c=42,
            operating_voltage_vdc="20.5-28.6",
            pricing_status=PricingStatus.ESTIMATED,
        ),
        Panel(
            panel_id="siemens_fc726",
            model_name="FC726",
            panel_type=PanelType.MODULAR,
            max_loops=28,
            devices_per_loop=54,  # 28*54=1512, відповідає datasheet
            max_total_devices=1512,
            network_max_panels=64,
            interfaces=["RS232", "RS485", "Ethernet"],
            pricing_status=PricingStatus.ESTIMATED,
        ),
    ],
)


# ════════════════════════════════════════════════════════════════════
# HOCHIKI — preliminary
# ════════════════════════════════════════════════════════════════════

HOCHIKI = Manufacturer(
    manufacturer_id="hochiki",
    name_ua="Hochiki",
    name_en="Hochiki",
    country_iso2="GB",  # Hochiki Europe (UK)
    tier=Tier.PREMIUM,
    system_type=SystemType.ALGORITHMIC,
    warranty_months=24,
    data_status=DataStatus.PRELIMINARY,
    last_updated=date(2026, 5, 11),
    notes_strengths=[
        "ESP — відкритий протокол",
        "FireNET L@titude — до 16 петель × 400 точок",
        "UK + US нативна сертифікація",
        "Adaptive thresholds, day/night modes",
        "5 modes detector behavior",
    ],
    notes_weaknesses=[
        "Хмара тільки через 3rd-party",
        "UA-дистриб'юція обмежена",
    ],
    certifications=Certifications(
        EU_EN54=JurisdictionCert(
            status=CertificationStatus.FULL,
            certified_parts=["-2", "-4", "-5", "-7", "-17", "-18"],
        ),
        UA_DSTU_EN54=JurisdictionCert(status=CertificationStatus.PARTIAL),
        UK_BS_LPCB=JurisdictionCert(status=CertificationStatus.FULL, certification_body="LPCB"),
        US_UL_FM=JurisdictionCert(status=CertificationStatus.FULL),
        iso_9001="ISO 9001:2015",
    ),
    features=Features(
        false_alarm_level=FalseAlarmLevel.PREMIUM,
        false_alarm_technologies=["drift_compensation", "day_night_modes", "5_response_modes"],
        cloud_monitoring=CloudMonitoring(available=False, notes="Через 3rd-party BMS"),
        mobile_app=MobileApp(available=False),
        bms_integration=BMSIntegration(
            bacnet=FeatureSupport.NATIVE,
            modbus_rtu=FeatureSupport.GATEWAY,
            modbus_tcp=FeatureSupport.GATEWAY,
        ),
        voice_alarm=FeatureSupport.PARTNER,
        wireless_extension=False,
        redundancy=Redundancy(),
    ),
    panels=[
        Panel(
            panel_id="hochiki_firenet_plus_1127",
            model_name="FireNET Plus 1127",
            panel_type=PanelType.COMPACT,
            max_loops=2,
            devices_per_loop=127,
            max_total_devices=254,
            interfaces=["RS485"],
            pricing_status=PricingStatus.ESTIMATED,
        ),
        Panel(
            panel_id="hochiki_firenet_latitude",
            model_name="FireNET L@titude",
            panel_type=PanelType.MODULAR,
            max_loops=16,
            devices_per_loop=400,
            max_total_devices=6400,
            network_max_panels=64,
            interfaces=["RS485", "Ethernet"],
            pricing_status=PricingStatus.ESTIMATED,
        ),
    ],
)


# ════════════════════════════════════════════════════════════════════
# APOLLO — preliminary
# Особливість: OEM, панелі від партнерів
# ════════════════════════════════════════════════════════════════════

APOLLO = Manufacturer(
    manufacturer_id="apollo",
    name_ua="Apollo",
    name_en="Apollo Fire Detectors",
    country_iso2="GB",
    tier=Tier.PREMIUM,
    system_type=SystemType.ALGORITHMIC,
    warranty_months=24,
    data_status=DataStatus.PRELIMINARY,
    last_updated=date(2026, 5, 11),
    notes_internal="OEM-постачальник — панелі від C-TEC, Morley, Gamewell. Для повної системи завжди 2 виробника.",
    notes_strengths=[
        "Open protocol (XP95, Discovery)",
        "Швидкий монтаж через XPERT-карти",
        "Wireless через XPander (EN 54-25)",
        "Native UK + LPCB",
        "5 response modes на Discovery",
    ],
    notes_weaknesses=[
        "Apollo НЕ виробляє панелі — потрібен партнер",
        "Закупівельна логіка ускладнена (2 виробники)",
        "Хмара і моніторинг — через панель-партнера",
    ],
    certifications=Certifications(
        EU_EN54=JurisdictionCert(
            status=CertificationStatus.FULL,
            certified_parts=["-2", "-5", "-7", "-11", "-17", "-18", "-25"],
        ),
        UA_DSTU_EN54=JurisdictionCert(status=CertificationStatus.PARTIAL),
        UK_BS_LPCB=JurisdictionCert(status=CertificationStatus.FULL),
        US_UL_FM=JurisdictionCert(status=CertificationStatus.PARTIAL, notes="Через XP95A варіант (Gamewell-FCI)"),
        iso_9001="ISO 9001:2015",
    ),
    features=Features(
        false_alarm_level=FalseAlarmLevel.PREMIUM,
        false_alarm_technologies=["drift_compensation", "5_response_modes"],
        cloud_monitoring=CloudMonitoring(available=False, notes="Залежить від обраного партнера панелі"),
        mobile_app=MobileApp(available=False),
        bms_integration=BMSIntegration(
            modbus_rtu=FeatureSupport.PARTNER,
            modbus_tcp=FeatureSupport.PARTNER,
        ),
        voice_alarm=FeatureSupport.PARTNER,
        wireless_extension=True,  # XPander
        redundancy=Redundancy(),
    ),
    # Панелі представлені партнерськими (C-TEC XFP, Morley ZX5Se)
    panels=[
        Panel(
            panel_id="apollo_ctec_xfp",
            model_name="C-TEC XFP (partner)",
            panel_type=PanelType.COMPACT,
            max_loops=1,
            devices_per_loop=127,
            max_total_devices=127,
            network_max_panels=8,
            interfaces=["RS485"],
            pricing_status=PricingStatus.ESTIMATED,
            pricing_notes="Партнерська панель C-TEC + Apollo XP95",
        ),
    ],
)


# ════════════════════════════════════════════════════════════════════
# ESSER (Honeywell) — preliminary
# ════════════════════════════════════════════════════════════════════

ESSER = Manufacturer(
    manufacturer_id="esser",
    name_ua="Esser (Honeywell)",
    name_en="Esser by Honeywell",
    country_iso2="DE",
    tier=Tier.PREMIUM,
    system_type=SystemType.ALGORITHMIC,
    warranty_months=24,
    data_status=DataStatus.PRELIMINARY,
    last_updated=date(2026, 5, 11),
    notes_strengths=[
        "IQ8Quad — детектор + sounder + strobe в 1 пристрої (унікально)",
        "esserbus PLUS — до 127 пристроїв + 32 транспондерів на петлі",
        "essernet — до 31 панелі в мережі",
        "Native voice alarm",
        "До 18 петель × 127 = 2286 пристроїв (IQ8Control M)",
    ],
    notes_weaknesses=[
        "Преміум-ціна",
        "UA-дистриб'юція через Honeywell — обмежена",
    ],
    certifications=Certifications(
        EU_EN54=JurisdictionCert(
            status=CertificationStatus.FULL,
            certified_parts=["-2", "-3", "-4", "-23"],
            certification_body="VdS",
        ),
        UA_DSTU_EN54=JurisdictionCert(status=CertificationStatus.PARTIAL),
        UK_BS_LPCB=JurisdictionCert(status=CertificationStatus.FULL),
        US_UL_FM=JurisdictionCert(status=CertificationStatus.PARTIAL, notes="Через Honeywell US лінійки"),
        iso_9001="ISO 9001:2015",
    ),
    features=Features(
        false_alarm_level=FalseAlarmLevel.PREMIUM,
        false_alarm_technologies=["TM_PM_modes", "multi_sensor_fusion"],
        cloud_monitoring=CloudMonitoring(available=True, platform_name="Honeywell Connected Building / WINMAG"),
        mobile_app=MobileApp(available=True),
        bms_integration=BMSIntegration(
            bacnet=FeatureSupport.NATIVE,
            modbus_rtu=FeatureSupport.NATIVE,
            modbus_tcp=FeatureSupport.NATIVE,
        ),
        voice_alarm=FeatureSupport.NATIVE,
        wireless_extension=True,
        redundancy=Redundancy(panel_controller=True),
    ),
    panels=[
        Panel(
            panel_id="esser_iq8_control_c",
            model_name="IQ8Control C",
            panel_type=PanelType.COMPACT,
            max_loops=4,
            devices_per_loop=127,
            max_total_devices=508,
            interfaces=["RS485", "RS232"],
            pricing_status=PricingStatus.ESTIMATED,
        ),
        Panel(
            panel_id="esser_iq8_control_m",
            model_name="IQ8Control M",
            panel_type=PanelType.MODULAR,
            max_loops=18,
            devices_per_loop=127,
            max_total_devices=2286,
            network_max_panels=31,
            interfaces=["RS485", "RS232", "Ethernet"],
            pricing_status=PricingStatus.ESTIMATED,
        ),
    ],
)


# ════════════════════════════════════════════════════════════════════
# SCHRACK SECONET — preliminary
# ════════════════════════════════════════════════════════════════════

SCHRACK = Manufacturer(
    manufacturer_id="schrack",
    name_ua="Schrack Seconet",
    name_en="Schrack Seconet",
    country_iso2="AT",
    tier=Tier.PREMIUM,
    system_type=SystemType.ALGORITHMIC,
    warranty_months=24,
    data_status=DataStatus.PRELIMINARY,
    last_updated=date(2026, 5, 11),
    notes_internal="Активна UA-присутність. Унікальна повна редундантність.",
    notes_strengths=[
        "ПОВНА redundancy (hardware + software + network + loop)",
        "X-LINE до 250 пристроїв на петлі × 3500м",
        "Integral IP MX — 16 петель × 4000 елементів",
        "Native BACnet/OPC/MODBUS без шлюзів",
        "Combined Fire+Extinguishing панель",
        "Network до 4049 панелей (рекорд)",
        "Ізолятори вбудовані в кожен X-LINE пристрій",
    ],
    notes_weaknesses=[
        "Найвища цінова категорія",
        "Окрема серія для US-ринку",
    ],
    certifications=Certifications(
        EU_EN54=JurisdictionCert(
            status=CertificationStatus.FULL,
            certified_parts=["-2", "-4"],
            certification_body="VdS",
        ),
        UA_DSTU_EN54=JurisdictionCert(status=CertificationStatus.PARTIAL),
        UK_BS_LPCB=JurisdictionCert(status=CertificationStatus.FULL),
        US_UL_FM=JurisdictionCert(status=CertificationStatus.PARTIAL),
        iso_9001="ISO 9001:2015",
    ),
    features=Features(
        false_alarm_level=FalseAlarmLevel.PREMIUM,
        false_alarm_technologies=["sensor_fusion", "advanced_algorithms"],
        cloud_monitoring=CloudMonitoring(available=True, platform_name="Integral Remote / Secolog IP"),
        mobile_app=MobileApp(available=True),
        bms_integration=BMSIntegration(
            bacnet=FeatureSupport.NATIVE,
            modbus_rtu=FeatureSupport.NATIVE,
            modbus_tcp=FeatureSupport.NATIVE,
            opc_ua=FeatureSupport.NATIVE,
        ),
        voice_alarm=FeatureSupport.NATIVE,
        wireless_extension=False,
        redundancy=Redundancy(panel_controller=True, network=True, loop=True),
    ),
    panels=[
        Panel(
            panel_id="schrack_integral_c",
            model_name="Integral C",
            panel_type=PanelType.COMPACT,
            max_loops=1,
            devices_per_loop=250,
            max_total_devices=250,
            interfaces=["Ethernet"],
            pricing_status=PricingStatus.ESTIMATED,
        ),
        Panel(
            panel_id="schrack_integral_ip_mx",
            model_name="Integral IP MX",
            panel_type=PanelType.MODULAR,
            max_loops=16,
            devices_per_loop=250,
            max_total_devices=4000,
            network_max_panels=4049,
            interfaces=["Ethernet", "RS485", "RS232"],
            pricing_status=PricingStatus.ESTIMATED,
        ),
    ],
)


# ════════════════════════════════════════════════════════════════════
# АРТОН — starter (мінімальні стартові дані; чекаємо запит до виробника)
# ════════════════════════════════════════════════════════════════════

ARTON = Manufacturer(
    manufacturer_id="arton",
    name_ua="Артон",
    name_en="Arton",
    country_iso2="UA",
    founded_year=1998,
    tier=Tier.MID,
    system_type=SystemType.MIXED,  # «Вектор» (адресна) + конвенційні
    warranty_months=24,  # припущення; потребує підтвердження
    data_status=DataStatus.STARTER,
    last_updated=date(2026, 5, 11),
    notes_internal=(
        "ПОЧАТКОВИЙ ЗАПИС. Потребує контакту з виробником (info@arton.com.ua, +380 (372) 55-74-98). "
        "Критично потрібно: архітектура системи 'Вектор' (петлі, адреси, мережа), "
        "I/O модулі та їх адресне споживання, прайс-лист на UA-ринку."
    ),
    notes_strengths=[
        "Українське виробництво (Чернівці)",
        "ISO 9001:2015 з 2003 року",
        "Аерозольне пожежогасіння — окрема сильна лінійка",
        "Експорт у 30+ країн",
    ],
    notes_weaknesses=[
        "Обмежені публічні характеристики системи 'Вектор'",
        "Хмара і мобільне — не передбачено",
        "BMS-інтеграція не нативна",
        "Часткова EN 54 (через болгарський Dedal)",
    ],
    certifications=Certifications(
        EU_EN54=JurisdictionCert(
            status=CertificationStatus.PARTIAL,
            certification_body="Dedal (Bulgaria)",
        ),
        UA_DSTU_EN54=JurisdictionCert(status=CertificationStatus.FULL),
        UK_BS_LPCB=JurisdictionCert(status=CertificationStatus.NONE),
        US_UL_FM=JurisdictionCert(status=CertificationStatus.NONE),
        iso_9001="ISO 9001:2015",
    ),
    features=Features(
        false_alarm_level=FalseAlarmLevel.BASIC,
        false_alarm_technologies=[],
        cloud_monitoring=CloudMonitoring(available=False),
        mobile_app=MobileApp(available=False),
        bms_integration=BMSIntegration(
            modbus_rtu=FeatureSupport.GATEWAY,
        ),
        voice_alarm=FeatureSupport.NONE,
        wireless_extension=False,
        redundancy=Redundancy(),
    ),
    # Без панелей до уточнення архітектури «Вектор»
    panels=[],
)


# ════════════════════════════════════════════════════════════════════
# Експорт усіх плейсхолдерів
# ════════════════════════════════════════════════════════════════════

PLACEHOLDERS = [BOSCH, SIEMENS, HOCHIKI, APOLLO, ESSER, SCHRACK, ARTON]
