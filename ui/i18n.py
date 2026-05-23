"""
Модуль перекладів UA/EN для UI FireCompare.

Підхід: словник з ключем-ідентифікатором → переклади мовами.
Використання: t("greeting") → залежно від обраної мови.

Стратегія:
- Основний UI (sidebar, tabs, заголовки) — повний переклад
- Reasoning з 5 шарів (engine) — залишається українською (експертна деталь)
- DOCX-меморандум — українською (для українських клієнтів)
"""
import streamlit as st


TRANSLATIONS = {
    # ── Загальні ──
    "app_subtitle": {
        "ua": "Об'єктивне порівняння систем пожежної сигналізації — для платформи Cofem Ukraine",
        "en": "Objective comparison of fire alarm systems — for the Cofem Ukraine platform",
    },
    "lang_label": {"ua": "Мова інтерфейсу", "en": "Interface language"},
    
    # ── Sidebar: Об'єкт ──
    "object_section": {"ua": "🏢 Об'єкт", "en": "🏢 Object"},
    "scenario_select": {"ua": "Об'єкт:", "en": "Object:"},
    "scenario_new_object": {
        "ua": "— Новий об'єкт —",
        "en": "— New object —",
    },
    "scenario_npa": {
        "ua": "Замкова II черга (NPA: 3 ППКП)",
        "en": "Zamkova Phase 2 (NPA: 3 panels)",
    },
    "scenario_premium": {
        "ua": "Замкова Преміум (UA+EU сертифікація)",
        "en": "Zamkova Premium (UA+EU certification)",
    },
    "scenario_simple": {
        "ua": "Замкова Простий (1 ППКП — для контрасту)",
        "en": "Zamkova Simple (single panel — for contrast)",
    },
    "new_object_hint": {
        "ua": (
            "Оберіть приклад зі списку або скористайтесь вкладкою «🤖 AI помічник», "
            "щоб описати свій об'єкт. Прораховані об'єкти з'являться у цьому списку."
        ),
        "en": (
            "Select an example from the list or use the «🤖 AI assistant» tab "
            "to describe your object. Calculated objects will appear in this list."
        ),
    },
    "obj_type": {"ua": "Тип", "en": "Type"},
    "obj_area": {"ua": "Площа захищувана", "en": "Protected area"},
    "obj_floors": {"ua": "Поверхів", "en": "Floors"},
    "obj_jurisdictions": {"ua": "Юрисдикції", "en": "Jurisdictions"},
    "obj_certification": {"ua": "Сертифікація", "en": "Certification"},
    "obj_horizon": {"ua": "Горизонт", "en": "Lifetime horizon"},
    "obj_false_alarm": {"ua": "Захист хибних", "en": "False alarm protection"},
    "npa_zones_count": {"ua": "NPA-зон", "en": "NPA zones"},
    "fire_zones_short": {"ua": "пож. зон", "en": "fire zones"},
    
    # ── Sidebar: Comparison-set ──
    "comparison_set": {"ua": "🏭 Comparison-set", "en": "🏭 Comparison set"},
    "calculate_btn": {"ua": "🚀 РОЗРАХУВАТИ", "en": "🚀 CALCULATE"},
    
    # ── Tabs ──
    "tab1_label": {"ua": "📊 Mode 1: Порівняння", "en": "📊 Mode 1: Comparison"},
    "tab2_label": {
        "ua": "🔄 Mode 2: Зворотній аналіз",
        "en": "🔄 Mode 2: Reverse priority",
    },
    "tab3_label": {"ua": "📄 Mode 3: Меморандум", "en": "📄 Mode 3: Memorandum"},
    
    # ── Initial states ──
    "configure_and_run": {
        "ua": "👈 Налаштуйте параметри в sidebar і натисніть «РОЗРАХУВАТИ»",
        "en": "👈 Configure parameters in the sidebar and click «CALCULATE»",
    },
    "run_first": {
        "ua": "Спочатку виконайте розрахунок (вкладка Mode 1)",
        "en": "First run a calculation (Mode 1 tab)",
    },
    
    # ── Tab 1: Mode 1 ──
    "calc_result_header": {"ua": "Результат розрахунку", "en": "Calculation result"},
    "calc_id_label": {"ua": "Calculation ID", "en": "Calculation ID"},
    "calc_mode_label": {"ua": "Режим", "en": "Mode"},
    "mode_npa": {"ua": "NPA (multi-panel)", "en": "NPA (multi-panel)"},
    "mode_simple": {"ua": "Простий (1 ППКП)", "en": "Simple (1 panel)"},
    "engine_label": {"ua": "Engine", "en": "Engine"},
    
    "metric_detectors": {"ua": "Детекторів", "en": "Detectors"},
    "detector_smoke_short": {"ua": "д", "en": "smk"},
    "detector_heat_short": {"ua": "т", "en": "ht"},
    "metric_io_signals": {"ua": "I/O сигналів", "en": "I/O signals"},
    "metric_mcp": {"ua": "MCP кнопок", "en": "MCPs"},
    "metric_sounders": {"ua": "Sounders", "en": "Sounders"},
    
    "summary_table_header": {
        "ua": "🏆 Зведена таблиця (сортування за overall)",
        "en": "🏆 Summary table (sorted by overall)",
    },
    "no_mfr_warning": {
        "ua": "Жоден виробник не пройшов фільтри. Перевірте comparison-set.",
        "en": "No manufacturer passed the filters. Check the comparison set.",
    },
    
    # ── Колонки таблиці ──
    "col_manufacturer": {"ua": "Виробник", "en": "Manufacturer"},
    "col_panels": {"ua": "Панелей", "en": "Panels"},
    "col_addresses": {"ua": "Адрес", "en": "Addresses"},
    "col_arch_eff": {"ua": "Арх.еф %", "en": "Arch.eff %"},
    "col_capex": {"ua": "CAPEX (₴)", "en": "CAPEX (UAH)"},
    
    "adapted_weights_label": {
        "ua": "**Адаптовані ваги шарів:**",
        "en": "**Adapted layer weights:**",
    },
    "weight_capex": {"ua": "CAPEX", "en": "CAPEX"},
    "weight_arch": {"ua": "Архітектура", "en": "Architecture"},
    "weight_func": {"ua": "Функц", "en": "Func"},
    "weight_oper": {"ua": "Експл", "en": "Oper"},
    "weight_tco": {"ua": "TCO", "en": "TCO"},
    
    # ── Графіки ──
    "chart_overall": {"ua": "Overall Score", "en": "Overall Score"},
    "chart_capex": {"ua": "CAPEX (₴)", "en": "CAPEX (UAH)"},
    
    # ── Деталізація ──
    "details_header": {
        "ua": "🔍 Деталізація обраного виробника",
        "en": "🔍 Detailed view by manufacturer",
    },
    "select_manufacturer": {"ua": "Виробник:", "en": "Manufacturer:"},
    
    "layer_1_label": {"ua": "Layer 1 — CAPEX", "en": "Layer 1 — CAPEX"},
    "layer_2_label": {
        "ua": "Layer 2 — Архітектурна ефективність",
        "en": "Layer 2 — Architectural efficiency",
    },
    "layer_3_label": {
        "ua": "Layer 3 — Функціональний рівень",
        "en": "Layer 3 — Functional level",
    },
    "layer_4_label": {"ua": "Layer 4 — Експлуатація", "en": "Layer 4 — Operational"},
    "layer_5_label": {"ua": "Layer 5 — TCO", "en": "Layer 5 — TCO"},
    "score_label": {"ua": "Бал", "en": "Score"},
    "abs_value_label": {"ua": "Абсолютне значення", "en": "Absolute value"},
    
    # ── Tab 2: Mode 2 ──
    "mode2_header": {
        "ua": "🔄 Mode 2: Зворотній сценарний аналіз",
        "en": "🔄 Mode 2: Reverse scenario analysis",
    },
    "mode2_caption": {
        "ua": (
            "Алгоритм перебирає 16 комбінацій пре-об'єктних умов (2⁴) і показує, "
            "за яких параметрів кожен виробник був би переможцем. "
            "Це формує **чесний інструмент** — клієнт бачить умови, де його варіант кращий."
        ),
        "en": (
            "The algorithm iterates through 16 combinations of pre-object conditions (2⁴) "
            "and shows under which parameters each manufacturer would be the winner. "
            "This builds an **honest tool** — the client sees conditions where their option is better."
        ),
    },
    "mode2_run_btn": {
        "ua": "🔄 Запустити Mode 2 (16 сценаріїв)",
        "en": "🔄 Run Mode 2 (16 scenarios)",
    },
    "mode2_spinner": {
        "ua": "Прогоняю 16 сценаріїв...",
        "en": "Running 16 scenarios...",
    },
    "winners_dist_header": {"ua": "Розподіл перемог", "en": "Winner distribution"},
    "observations_header": {
        "ua": "💡 Аналітичні спостереження",
        "en": "💡 Analytical observations",
    },
    "scenarios_table_header": {
        "ua": "Сценарії (16 комбінацій)",
        "en": "Scenarios (16 combinations)",
    },
    "col_horizon": {"ua": "Горизонт", "en": "Horizon"},
    "col_false_alarm": {"ua": "Захист хибних", "en": "False alarm prot."},
    "col_budget": {"ua": "Бюджет", "en": "Budget"},
    "col_mobile_cloud": {"ua": "Mobile/Cloud", "en": "Mobile/Cloud"},
    "col_winner": {"ua": "Переможець", "en": "Winner"},
    "col_overall": {"ua": "Overall", "en": "Overall"},
    "horizon_long": {"ua": "довгий", "en": "long"},
    "horizon_short": {"ua": "короткий", "en": "short"},
    "fa_premium": {"ua": "преміум", "en": "premium"},
    "fa_standard": {"ua": "стандарт", "en": "standard"},
    "budget_constrained": {"ua": "обмеж.", "en": "constrained"},
    "budget_free": {"ua": "вільний", "en": "free"},
    "yes_short": {"ua": "так", "en": "yes"},
    "no_short": {"ua": "ні", "en": "no"},
    
    "cofem_loses_header": {
        "ua": "🎯 Чесний інструмент — коли Cofem не виграє",
        "en": "🎯 Honest tool — when Cofem does not win",
    },
    
    # ── Tab 3: Mode 3 ──
    "mode3_header": {
        "ua": "📄 Mode 3: Меморандум по виробнику",
        "en": "📄 Mode 3: Manufacturer memorandum",
    },
    "mode3_caption": {
        "ua": (
            "Генерує аналітичний документ із детальним аналізом обраного виробника "
            "на даному об'єкті. Експорт у DOCX."
        ),
        "en": (
            "Generates an analytical document with a detailed review of the selected "
            "manufacturer on this object. Exports to DOCX."
        ),
    },
    "no_mfr_for_memo": {
        "ua": "Немає виробників для меморандуму.",
        "en": "No manufacturers available for a memorandum.",
    },
    "select_for_memo": {
        "ua": "Виробник для меморандуму:",
        "en": "Manufacturer for memorandum:",
    },
    "gen_memo_btn": {
        "ua": "📄 Згенерувати меморандум для",
        "en": "📄 Generate memorandum for",
    },
    "memo_spinner": {
        "ua": "Формую меморандум та експортую DOCX...",
        "en": "Building memorandum and exporting DOCX...",
    },
    "memo_failure": {
        "ua": "Не вдалося сформувати меморандум.",
        "en": "Could not build the memorandum.",
    },
    "memo_success": {
        "ua": "✅ Меморандум згенеровано: 7 розділів, DOCX готовий",
        "en": "✅ Memorandum generated: 7 sections, DOCX ready",
    },
    "memo_download": {"ua": "⬇ Завантажити DOCX", "en": "⬇ Download DOCX"},
    "memo_export_error": {
        "ua": "Помилка експорту DOCX",
        "en": "DOCX export error",
    },
    
    # ── Misc ──
    "calculating_spinner": {
        "ua": "Виконую розрахунок...",
        "en": "Running calculation...",
    },
    
    # ── Maintenance: column in Mode 1 ──
    "col_maintenance_month": {"ua": "ТО/міс (₴)", "en": "Maint./mo (UAH)"},
    "col_maintenance_year": {"ua": "ТО/рік (₴)", "en": "Maint./yr (UAH)"},
    
    # ── Maintenance: parameters in sidebar ──
    "maintenance_section": {"ua": "🔧 Параметри ТО", "en": "🔧 Maintenance params"},
    "maintenance_enable": {
        "ua": "Розрахувати вартість ТО",
        "en": "Calculate maintenance cost",
    },
    "mnt_distance": {"ua": "Відстань від об'єкта до сервісного центру (км)", "en": "Distance from object to service center (km)"},
    "mnt_n_damages": {"ua": "Пошкоджень/міс", "en": "Damages/month"},
    "mnt_composition": {"ua": "Склад СПЗ", "en": "FAS composition"},
    "mnt_has_extinguish": {"ua": "Пожежогасіння", "en": "Fire extinguishing"},
    "mnt_has_smoke_vent": {"ua": "Димовидалення", "en": "Smoke ventilation"},
    "mnt_has_valves": {"ua": "Керування клапанами", "en": "Valves control"},
    "mnt_has_engineering": {
        "ua": "Інженерні системи (ліфти/ворота)",
        "en": "Engineering systems (lifts/gates)",
    },
    "mnt_has_monitoring": {
        "ua": "Пультове спостереження",
        "en": "Monitoring station",
    },
    
    # ── Maintenance tab ──
    "tab4_label": {"ua": "🔧 Mode 4: ТО (калькулятор)", "en": "🔧 Mode 4: Maintenance"},
    "mnt_header": {
        "ua": "🔧 Розрахунок вартості ТО",
        "en": "🔧 Maintenance cost calculator",
    },
    "mnt_caption": {
        "ua": (
            "Калькулятор вартості щомісячного технічного обслуговування СПЗ. "
            "Можна використовувати окремо або разом з порівнянням виробників (Mode 1)."
        ),
        "en": (
            "Monthly maintenance cost calculator for fire alarm systems. "
            "Can be used standalone or integrated with manufacturer comparison (Mode 1)."
        ),
    },
    "mnt_show_breakdown": {
        "ua": "Розрахунок для виробників",
        "en": "Breakdown by manufacturer",
    },
    "mnt_breakdown_caption": {
        "ua": (
            "Деталізація розрахунку ТО для кожного виробника з comparison-set. "
            "Cofem зазвичай має нижчу вартість ТО завдяки PREMIUM-рівню захисту від хибних "
            "та лабіринтним корпусам, які не потребують регулярного очищення."
        ),
        "en": (
            "Detailed maintenance cost breakdown for each manufacturer in the comparison set. "
            "Cofem typically has lower maintenance costs due to PREMIUM-level false alarm "
            "protection and labyrinth housings that don't require regular cleaning."
        ),
    },
    "mnt_standalone_header": {
        "ua": "Самостійний розрахунок (без виробника)",
        "en": "Standalone calculation (no manufacturer)",
    },
    "mnt_standalone_caption": {
        "ua": (
            "Розрахунок для гіпотетичного об'єкта без прив'язки до конкретного виробника. "
            "Використовуються середні параметри."
        ),
        "en": (
            "Calculation for a hypothetical object without binding to a specific "
            "manufacturer. Average parameters are used."
        ),
    },
    "mnt_time_table_header": {"ua": "Витрати часу", "en": "Time costs"},
    "mnt_cost_table_header": {"ua": "Розрахунок собівартості", "en": "Cost breakdown"},
    "mnt_price_table_header": {"ua": "Розрахунок ціни", "en": "Price calculation"},
    "mnt_summary_month": {"ua": "За місяць", "en": "Per month"},
    "mnt_summary_year": {"ua": "За рік", "en": "Per year"},
    "mnt_export_btn": {
        "ua": "📄 Згенерувати DOCX-меморандум",
        "en": "📄 Generate DOCX memorandum",
    },
    "mnt_download_btn": {"ua": "⬇ Завантажити DOCX", "en": "⬇ Download DOCX"},
    "mnt_strategic_discount": {
        "ua": "Стратегічна знижка (%)",
        "en": "Strategic discount (%)",
    },
    
    # ── Row labels in tables ──
    "mnt_row_t_planned": {
        "ua": "Планове ТО (з урахуванням складності)",
        "en": "Planned maintenance (with complexity factor)",
    },
    "mnt_row_t_travel_planned": {
        "ua": "Дорога на планові візити",
        "en": "Travel for planned visits",
    },
    "mnt_row_t_false": {
        "ua": "Реагування на хибні (з дорогою)",
        "en": "Response to false alarms (with travel)",
    },
    "mnt_row_t_damages": {
        "ua": "Усунення пошкоджень (з дорогою)",
        "en": "Damage repair (with travel)",
    },
    "mnt_row_t_total": {"ua": "РАЗОМ людино-годин на місяць", "en": "TOTAL man-hours per month"},
    "mnt_row_cost_labor": {
        "ua": "Оплата праці кваліфікованого виконавця (з податками)",
        "en": "Qualified executor labor (with taxes)",
    },
    "mnt_row_cost_transport": {"ua": "Транспортні витрати", "en": "Transport costs"},
    "mnt_row_cost_parts": {"ua": "Запчастини / витратні матеріали", "en": "Spare parts"},
    "mnt_row_cost_admin": {"ua": "Адміністративні витрати", "en": "Administrative costs"},
    "mnt_row_cost_own_total": {"ua": "СОБІВАРТІСТЬ ВЛАСНИХ РОБІТ", "en": "OWN WORK COST"},
    "mnt_row_price_own": {
        "ua": "Власні роботи (з націнкою 60%)",
        "en": "Own work (with 60% markup)",
    },
    "mnt_row_subcontract": {
        "ua": "Підрядне пультове спостереження (прохід)",
        "en": "Subcontracted monitoring (pass-through)",
    },
    "mnt_row_calculated": {"ua": "РОЗРАХУНКОВА ЦІНА", "en": "CALCULATED PRICE"},
    "mnt_row_discount": {"ua": "Стратегічна знижка", "en": "Strategic discount"},
    "mnt_row_final": {"ua": "ЦІНА ДЛЯ КЛІЄНТА", "en": "PRICE FOR CLIENT"},
    "mnt_col_item": {"ua": "Стаття", "en": "Item"},
    "mnt_col_formula": {"ua": "Формула / Обчислення", "en": "Formula / Calculation"},
    "mnt_col_value": {"ua": "Значення", "en": "Value"},
    "mnt_col_hours": {"ua": "Годин", "en": "Hours"},
    "mnt_col_uah": {"ua": "Сума, ₴", "en": "Amount, UAH"},
    
    # ── Tab 5: AI Assistant ──
    "tab5_label": {"ua": "🤖 AI помічник", "en": "🤖 AI assistant"},
    "ai_header": {
        "ua": "🤖 AI помічник для збору параметрів",
        "en": "🤖 AI assistant for parameter collection",
    },
    "ai_caption": {
        "ua": (
            "Опишіть ваш об'єкт у вільній формі — AI задасть уточнюючі питання "
            "і автоматично заповнить параметри для розрахунку."
        ),
        "en": (
            "Describe your object in natural language — the AI will ask "
            "clarifying questions and auto-fill parameters for calculation."
        ),
    },
    "ai_no_key_warning": {
        "ua": (
            "⚠ API-ключ Anthropic не налаштовано. Зверніться до README, "
            "розділ «AI-помічник: налаштування»."
        ),
        "en": (
            "⚠ Anthropic API key not configured. See README, "
            "section «AI Assistant: setup»."
        ),
    },
    "ai_initial_message_ua": {
        "ua": (
            "Привіт! Я допоможу підібрати оптимальну систему пожежної "
            "сигналізації для вашого об'єкта. Розкажіть, який саме об'єкт "
            "ви плануєте обладнати?"
        ),
        "en": (
            "Hi! I'll help you choose the right fire alarm system for your "
            "object. What type of object are you equipping?"
        ),
    },
    "ai_input_placeholder": {
        "ua": "Опишіть ваш об'єкт або дайте відповідь...",
        "en": "Describe your object or respond...",
    },
    "ai_thinking": {"ua": "Думаю...", "en": "Thinking..."},
    "ai_reset_btn": {"ua": "🔄 Почати спочатку", "en": "🔄 Start over"},
    "ai_collected_params": {
        "ua": "📋 Зібрані параметри",
        "en": "📋 Collected parameters",
    },
    "ai_run_calculation": {
        "ua": "🚀 Запустити розрахунок",
        "en": "🚀 Run calculation",
    },
    "ai_calc_done": {
        "ua": "✅ Розрахунок виконано. Дивіться вкладки Mode 1, 2, 3, 4.",
        "en": "✅ Calculation complete. See Mode 1, 2, 3, 4 tabs.",
    },
    "ai_error": {"ua": "Помилка", "en": "Error"},
    "ai_token_usage": {"ua": "Токенів", "en": "Tokens"},
}


def get_lang() -> str:
    """Повертає поточну мову з session_state (default: ua)"""
    return st.session_state.get("language", "ua")


def t(key: str) -> str:
    """Перекладає ключ на поточну мову. Якщо немає — повертає ключ."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    lang = get_lang()
    return entry.get(lang, entry.get("ua", key))


def mfr_name(manufacturer) -> str:
    """Повертає назву виробника відповідно до обраної мови інтерфейсу."""
    lang = get_lang()
    if lang == "en":
        return manufacturer.name_en or manufacturer.name_ua
    return manufacturer.name_ua
