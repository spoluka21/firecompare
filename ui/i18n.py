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
    "scenario_select": {"ua": "Завантажити приклад:", "en": "Load example:"},
    "scenario_npa": {
        "ua": "Замкова II черга (NPA: 3 ППКП)",
        "en": "Zamkova Phase 2 (NPA: 3 panels)",
    },
    "scenario_premium": {
        "ua": "Замкова Преміум (UA+UK страхування)",
        "en": "Zamkova Premium (UA+UK insurance)",
    },
    "scenario_simple": {
        "ua": "Замкова Простий (1 ППКП — для контрасту)",
        "en": "Zamkova Simple (single panel — for contrast)",
    },
    "obj_type": {"ua": "Тип", "en": "Type"},
    "obj_area": {"ua": "Площа захищувана", "en": "Protected area"},
    "obj_floors": {"ua": "Поверхів", "en": "Floors"},
    "obj_jurisdictions": {"ua": "Юрисдикції", "en": "Jurisdictions"},
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
