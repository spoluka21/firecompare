"""
КРОК 1. Розрахунок вимог BOM (Bill of Materials Requirements)

На основі параметрів об'єкта обчислюємо, СКІЛЬКИ КОМПОНЕНТІВ потрібно — 
без прив'язки до конкретного виробника. Це «технічна потреба об'єкта».

Виробник-агностично:
- Скільки детекторів (за зонами + ДБН В.2.5-56 Зм.№2)
- Скільки I/O сигналів (з executive_automation)
- Скільки кнопок MCP (ручних сповіщувачів)
- Скільки оповіщувачів (sounders) за класом СО

На наступному кроці ці вимоги «протискаються» через каталог конкретного 
виробника — який модуль/детектор/панель закриває яку потребу.
"""
from pydantic import BaseModel, Field

from schemas.object_state import ObjectData, ObjectState


# ═══════════════════════════════════════════════════════════════════
# КОНСТАНТИ З ДБН В.2.5-56:2014 (Зм.№2)
# ═══════════════════════════════════════════════════════════════════

# Точкові димові сповіщувачі: один захищає до S₀ м²
SMOKE_DETECTOR_AREA_M2 = 77.0
SMOKE_DETECTOR_RADIUS_M = 8.8
SMOKE_DETECTOR_DISTANCE_M = 4.4

# Орієнтовні розрахункові коефіцієнти для зон різного типу
# (співвідношення площі, що реально вимагає детекції, до загальної)
ZONE_DETECTION_COVERAGE = {
    "residential": 0.85,  # житло — основні приміщення, без коридорів
    "commercial_ground": 0.90,  # комерція — майже все
    "office": 0.95,
    "underground_parking": 0.95,
    "aboveground_parking": 0.95,
    "shelter": 0.95,
    "technical": 0.80,  # тех. приміщення — селективно
    "server_room": 1.00,  # серверні — все
    "warehouse": 0.95,
    "industrial": 0.90,
    "kitchen": 0.95,
    "other": 0.85,
}

# Кнопки MCP — ДБН вимагає на евакуаційних шляхах:
# на виходах з поверхів і коридорів. Орієнтир: 1-2 на поверх на секцію.
MCP_PER_FLOOR_PER_SECTION = 2  # типово біля сходів і центрального виходу
# Плюс окремі: вестибюлі, парадні входи, технічні поверхи
MCP_EXTRA_AT_EXITS = 3

# Оповіщувачі sounders — за об'ємом коридорів і приміщень
# В середньому 1 на 200 м² для житла (більше для громадських)
SOUNDER_AREA_M2 = 200.0


# ═══════════════════════════════════════════════════════════════════
# ВИХІДНА СТРУКТУРА
# ═══════════════════════════════════════════════════════════════════


class BOMRequirements(BaseModel):
    """Технічні вимоги по компонентам — без прив'язки до виробника"""
    
    # Детектори
    smoke_detectors_count: int = Field(ge=0)
    heat_detectors_count: int = Field(ge=0)  # окремо для непридатних до диму зон (паркінг, кухня)
    
    # I/O сигнали
    io_input_signals_count: int = Field(ge=0)  # вхідні сигнали (датчики, кнопки шафи)
    io_output_signals_count: int = Field(ge=0)  # вихідні сигнали (керування клапанами, насосами)
    
    # Ручні сповіщувачі
    manual_call_points_count: int = Field(ge=0)
    
    # Оповіщувачі
    sounders_count: int = Field(ge=0)
    sounders_need_strobe: bool = False  # для глухих та глядачів
    
    # Розрахункові внутрішні
    total_detection_area_m2: float = Field(ge=0)
    fire_resistant_cable_m: float = Field(ge=0, default=0.0)  # метраж вогнестійкого кабелю
    notes: list[str] = Field(default_factory=list)
    
    def total_loop_devices(self) -> int:
        """Сумарна кількість пристроїв, які потраплять у петлю"""
        return (
            self.smoke_detectors_count +
            self.heat_detectors_count +
            self.manual_call_points_count +
            self.sounders_count
        )
    
    def total_logical_signals(self) -> int:
        """Логічних сигналів від executive_automation"""
        return self.io_input_signals_count + self.io_output_signals_count


# ═══════════════════════════════════════════════════════════════════
# КРОК 1.1. РОЗРАХУНОК ДЕТЕКТОРІВ
# ═══════════════════════════════════════════════════════════════════


def calculate_detectors_for_zone(
    zone_name: str, zone_data
) -> tuple[int, int, str]:
    """
    Розрахунок к-сті детекторів для однієї зони з урахуванням типу розкладки.
    
    Повертає (smoke_count, heat_count, note).
    
    Логіка за SubdivisionType:
    - OPEN: відкритий простір → N = ceil(площа / S₀). 
            Приклад: паркінг 10031 м² / 77 = 130 теплових.
    
    - SUBDIVIDED: розбита на приміщення розміру r з МЗК часткою p →
            робоча_площа = площа × (1 - p)
            приміщень = робоча_площа / r
            на_приміщення = max(1, ceil(r / S₀))   # часто r<S₀ → 1 детектор
            МЗК_площа = площа × p
            МЗК_детектори = ceil(МЗК_площа / S₀)
            N = приміщень × на_приміщення + МЗК_детектори
            Приклад: торгово-офіс 4043 м², r=25, p=20% →
                     робоча 3234 м² / 25 = 129 приміщень × 1 + МЗК 809 / 77 = 11
                     = 140 димових
    
    - CORRIDOR_ONLY: тільки МЗК → N = ceil(площа / S₀)
    """
    from schemas.object_state import SubdivisionType, detector_type_for_purpose
    
    # Тип детектора: пріоритет — поле purpose зони; запасний — назва ключа
    is_heat = False
    if getattr(zone_data, "purpose", None) is not None:
        dtype = detector_type_for_purpose(zone_data.purpose)
        is_heat = (dtype == "heat")
    else:
        heat_only_zones = {"underground_parking", "aboveground_parking", "kitchen", "boiler"}
        is_heat = zone_name in heat_only_zones
    
    if zone_data.subdivision_type == SubdivisionType.OPEN:
        # Відкритий простір — пряма формула N = ceil(площа / S₀)
        # без коефіцієнтів покриття (для паркінгу 100% площі захищається)
        count = max(1, -(-int(zone_data.area_m2 * 100) // int(SMOKE_DETECTOR_AREA_M2 * 100)))
        note = (
            f"{zone_name} (відкритий, {zone_data.area_m2:.0f} м²): "
            f"{count} {'теплових' if is_heat else 'димових'} "
            f"(площа / S₀ = {zone_data.area_m2:.0f}/{SMOKE_DETECTOR_AREA_M2:.0f})"
        )
        return (0, count, note) if is_heat else (count, 0, note)
    
    elif zone_data.subdivision_type == SubdivisionType.SUBDIVIDED:
        # Розбита зона: приміщення + МЗК
        r = zone_data.avg_room_area_m2 or 25.0
        p = zone_data.common_areas_share if zone_data.common_areas_share is not None else 0.20
        
        common_area = zone_data.area_m2 * p
        working_area = zone_data.area_m2 - common_area
        
        # Кількість приміщень (округлення вниз — реалістично)
        rooms_count = max(1, int(working_area / r))
        
        # Детекторів на приміщення (зазвичай 1, якщо r < S₀)
        detectors_per_room = max(1, -(-int(r * 100) // int(SMOKE_DETECTOR_AREA_M2 * 100)))
        
        # Детектори в МЗК
        common_detectors = max(0, -(-int(common_area * 100) // int(SMOKE_DETECTOR_AREA_M2 * 100)))
        
        total = rooms_count * detectors_per_room + common_detectors
        note = (
            f"{zone_name} (розбита, {zone_data.area_m2:.0f} м², r={r:.0f}, МЗК={p*100:.0f}%): "
            f"{rooms_count} прим. × {detectors_per_room} + МЗК {common_detectors} = "
            f"{total} {'теплових' if is_heat else 'димових'}"
        )
        return (0, total, note) if is_heat else (total, 0, note)
    
    else:  # CORRIDOR_ONLY
        count = max(1, -(-int(zone_data.area_m2 * 100) // int(SMOKE_DETECTOR_AREA_M2 * 100)))
        note = (
            f"{zone_name} (МЗК-коридори, {zone_data.area_m2:.0f} м²): "
            f"{count} {'теплових' if is_heat else 'димових'}"
        )
        return (0, count, note) if is_heat else (count, 0, note)


def calculate_detectors(object_data: ObjectData) -> tuple[int, int, float, list[str]]:
    """
    Загальний розрахунок детекторів за всіма зонами об'єкта.
    
    Повертає: (smoke_total, heat_total, total_area_m2, notes)
    
    ВАЖЛИВО: якщо зони не задані (наприклад, об'єкт заведено через AI-агента
    лише із загальною площею), створюємо синтетичну зону з усієї площі, щоб
    уникнути нульового розрахунку детекторів. Це груба, але реалістична оцінка
    для етапу порівняння (усереднені приміщення ~25 м², 20% МЗК).
    """
    from schemas.object_state import FunctionalZone, SubdivisionType
    
    zones = object_data.zones
    
    # Fallback: немає зон → синтетична зона з total_area_m2
    if not zones and object_data.total_area_m2 > 0:
        synthetic = FunctionalZone(
            area_m2=object_data.total_area_m2,
            subdivision_type=SubdivisionType.SUBDIVIDED,
            avg_room_area_m2=25.0,
            common_areas_share=0.20,
        )
        zones = {"object_total": synthetic}
    
    total_smoke = 0
    total_heat = 0
    total_area = 0.0
    notes = []
    
    for zone_name, zone_data in zones.items():
        # Якщо зона явно не потребує автоматики — пропускаємо (§4.0)
        if getattr(zone_data, "requires_automation", None) is False:
            notes.append(f"{zone_name}: автоматика не передбачена — детектори не рахуються")
            continue
        smoke, heat, note = calculate_detectors_for_zone(zone_name, zone_data)
        total_smoke += smoke
        total_heat += heat
        total_area += zone_data.area_m2
        notes.append(note)
    
    return total_smoke, total_heat, total_area, notes


# ═══════════════════════════════════════════════════════════════════
# КРОК 1.2. РОЗРАХУНОК I/O СИГНАЛІВ
# ═══════════════════════════════════════════════════════════════════


def calculate_io_signals(object_data: ObjectData) -> tuple[int, int, list[str]]:
    """
    Розрахунок I/O сигналів з executive_automation.
    
    Повертає: (input_signals, output_signals, notes)
    
    Принцип:
    - ШПК — кожна шафа дає 1-3 ВХІДНИХ сигнали (кнопки, датчик, СМК)
    - Клапани димовидалення — 2 сигнали кожен (1 вихід керування + 1 вхід ЗЗ)
    - Вогнезахисні клапани — 2 сигнали кожен (керування + ЗЗ)
    - Насоси — 2 сигнали (запуск + статус)
    - Вентилятори — 2 сигнали (керування + статус)
    - Двері — 1 вихід (керування)
    - Ліфти — 1 вихід (команда «Пожежа»)
    """
    ea = object_data.executive_automation
    notes = []
    
    inputs = 0
    outputs = 0
    
    # ШПК — тільки входи
    cabinet_inputs = ea.fire_hose_cabinets_count * ea.fire_hose_cabinet_signals.signals_per_cabinet()
    inputs += cabinet_inputs
    if cabinet_inputs > 0:
        notes.append(
            f"ШПК: {ea.fire_hose_cabinets_count} шаф × "
            f"{ea.fire_hose_cabinet_signals.signals_per_cabinet()} сигн. = "
            f"{cabinet_inputs} вхідних"
        )
    
    # Клапани — і керування, і зворотний зв'язок
    smoke_damper_signals = ea.smoke_dampers * 2
    outputs += ea.smoke_dampers
    inputs += ea.smoke_dampers
    if ea.smoke_dampers > 0:
        notes.append(
            f"Клапани димовидалення: {ea.smoke_dampers} × 2 = "
            f"{smoke_damper_signals} сигн. (1 вих + 1 вх)"
        )
    
    fire_damper_signals = ea.fire_dampers * 2
    outputs += ea.fire_dampers
    inputs += ea.fire_dampers
    if ea.fire_dampers > 0:
        notes.append(
            f"Вогнезахисні клапани: {ea.fire_dampers} × 2 = "
            f"{fire_damper_signals} сигн."
        )
    
    # Насоси — пуск + статус
    pump_signals = ea.fire_pumps * 2
    outputs += ea.fire_pumps
    inputs += ea.fire_pumps
    if ea.fire_pumps > 0:
        notes.append(f"Насоси: {ea.fire_pumps} × 2 = {pump_signals} сигн.")
    
    # Вентилятори — керування + статус
    fan_signals = ea.smoke_fans * 2
    outputs += ea.smoke_fans
    inputs += ea.smoke_fans
    if ea.smoke_fans > 0:
        notes.append(f"Вентилятори: {ea.smoke_fans} × 2 = {fan_signals} сигн.")
    
    # Двері — 1 вихід (розблокування)
    outputs += ea.fire_doors
    if ea.fire_doors > 0:
        notes.append(f"Двері: {ea.fire_doors} × 1 = {ea.fire_doors} вихідних")
    
    # Ліфти — 1 вихід (команда «Пожежа»)
    outputs += ea.elevators_fire_mode
    if ea.elevators_fire_mode > 0:
        notes.append(
            f"Ліфти: {ea.elevators_fire_mode} × 1 = "
            f"{ea.elevators_fire_mode} вихідних"
        )
    
    # Інше
    if ea.other_actuators > 0:
        # Припускаємо комбіноване (1 вхід + 1 вихід кожен)
        outputs += ea.other_actuators
        inputs += ea.other_actuators
        notes.append(f"Інше: {ea.other_actuators} × 2 сигн.")
    
    return inputs, outputs, notes


def calculate_zonal_engineering(object_data: ObjectData) -> dict:
    """
    Агрегує інженерію з ZoneComposition усіх зон (повний Рівень 2).
    
    Підсумовує I/O-сигнали і метраж вогнестійкого кабелю по зонах, що мають
    composition з інженерними системами. Доповнює object-рівневу
    executive_automation (вони не конфліктують: зональна — детальний режим,
    object-рівнева — швидкий/застарілий).
    
    Повертає dict: inputs, outputs, fire_resistant_cable_m, notes.
    
    Метраж вогнестійкого кабелю: орієнтовно (§9 рішення 3) —
    к-сть I/O-сигналів інженерії × середня довжина траси.
    """
    AVG_FRC_RUN_M = 35.0  # середня довжина однієї вогнестійкої траси, м
    
    inputs = 0
    outputs = 0
    frc_meters = 0.0
    notes = []
    
    for zone_name, zone_data in object_data.zones.items():
        comp = getattr(zone_data, "composition", None)
        if comp is None:
            continue
        if getattr(zone_data, "requires_automation", None) is False:
            continue
        if not comp.has_engineering():
            continue
        
        z_in, z_out = comp.engineering_io_signals()
        inputs += z_in
        outputs += z_out
        
        # Вогнестійкий кабель — на кожен інженерний сигнал
        zone_frc = (z_in + z_out) * AVG_FRC_RUN_M
        frc_meters += zone_frc
        
        notes.append(
            f"{zone_name}: інженерія {z_in} вх + {z_out} вих, "
            f"вогнестійкий кабель ≈ {zone_frc:.0f} м"
        )
    
    return {
        "inputs": inputs,
        "outputs": outputs,
        "fire_resistant_cable_m": round(frc_meters, 1),
        "notes": notes,
    }


# ═══════════════════════════════════════════════════════════════════
# КРОК 1.3. КНОПКИ MCP І ОПОВІЩУВАЧІ
# ═══════════════════════════════════════════════════════════════════


def calculate_mcp_count(object_data: ObjectData) -> int:
    """
    Ручні сповіщувачі (MCP) — ставляться на евакуаційних шляхах:
    біля сходів і центральних виходів кожного поверху.
    
    Орієнтир: MCP_PER_FLOOR_PER_SECTION на кожен поверх (секція припускається 1),
    плюс додаткові біля вестибюлів і парадних входів.
    """
    total_floors = object_data.floors_above + object_data.floors_below
    base_count = total_floors * object_data.phases * MCP_PER_FLOOR_PER_SECTION
    return base_count + MCP_EXTRA_AT_EXITS


def calculate_sounders(object_data: ObjectData) -> tuple[int, bool]:
    """
    Звукові оповіщувачі — на основі площі.
    Для деяких типів об'єктів (готелі, шпиталі, культура) — strobe обов'язковий.
    """
    count = max(1, round(object_data.total_area_m2 / SOUNDER_AREA_M2))
    
    # Strobe бажаний для громадських з можливою наявністю слабкочуючих
    needs_strobe = object_data.object_type.value in (
        "public",
        "commercial_trc",
        "administrative",
    )
    
    return count, needs_strobe


# ═══════════════════════════════════════════════════════════════════
# КРОК 1 (ГОЛОВНА ФУНКЦІЯ)
# ═══════════════════════════════════════════════════════════════════


def compute_bom_requirements(state: ObjectState) -> BOMRequirements:
    """
    Головна функція Кроку 1. На вході — повний стейт об'єкта.
    На виході — BOMRequirements з усіма кількостями.
    """
    obj = state.object
    
    # 1.1 Детектори
    smoke, heat, area, det_notes = calculate_detectors(obj)
    
    # 1.2 I/O сигнали (object-рівнева executive_automation)
    inputs, outputs, io_notes = calculate_io_signals(obj)
    
    # 1.2b Зональна інженерія (детальний режим) — додає I/O і вогнестійкий кабель
    zonal = calculate_zonal_engineering(obj)
    inputs += zonal["inputs"]
    outputs += zonal["outputs"]
    frc_m = zonal["fire_resistant_cable_m"]
    if zonal["notes"]:
        io_notes = io_notes + ["--- зональна інженерія ---"] + zonal["notes"]
    
    # 1.3 MCP
    mcp_count = calculate_mcp_count(obj)
    
    # 1.4 Оповіщувачі
    sounder_count, strobe = calculate_sounders(obj)
    
    all_notes = (
        ["=== ДЕТЕКТОРИ ==="] + det_notes +
        ["=== I/O СИГНАЛИ ==="] + io_notes +
        [
            f"=== РУЧНІ СПОВІЩУВАЧІ ===",
            f"Поверхів {obj.floors_above + obj.floors_below} × {obj.phases} секцій × "
            f"{MCP_PER_FLOOR_PER_SECTION} MCP + {MCP_EXTRA_AT_EXITS} на входах = {mcp_count} кнопок",
            f"=== ОПОВІЩУВАЧІ ===",
            f"Площа об'єкта {obj.total_area_m2:.0f} м² / {SOUNDER_AREA_M2:.0f} м² на 1 = {sounder_count} sounders" +
            (" (зі стробами)" if strobe else ""),
        ]
    )
    if frc_m > 0:
        all_notes.append(f"=== ВОГНЕСТІЙКИЙ КАБЕЛЬ ===")
        all_notes.append(f"Орієнтовний метраж: ≈ {frc_m:.0f} м (інженерія + ВПВ)")
    
    return BOMRequirements(
        smoke_detectors_count=smoke,
        heat_detectors_count=heat,
        io_input_signals_count=inputs,
        io_output_signals_count=outputs,
        manual_call_points_count=mcp_count,
        sounders_count=sounder_count,
        sounders_need_strobe=strobe,
        total_detection_area_m2=area,
        fire_resistant_cable_m=frc_m,
        notes=all_notes,
    )
