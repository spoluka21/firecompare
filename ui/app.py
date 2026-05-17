"""
FireCompare — Streamlit UI

Демо-інтерфейс для презентації керівництву Cofem.
Показує всі 3 режими: Mode 1 (Compare), Mode 2 (Reverse Priority), Mode 3 (Memo+DOCX).

Запуск:
    streamlit run ui/app.py
"""
import sys
from pathlib import Path

# Додаємо корінь у sys.path для імпортів
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

# ── Базовий конфіг сторінки ──
st.set_page_config(
    page_title="FireCompare — Cofem Ukraine",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Стилі (мінімальний CSS) ──
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2E75B6 0%, #1F4E79 100%);
        padding: 1.5rem 2rem;
        border-radius: 8px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { margin: 0; color: white; font-size: 1.8rem; }
    .main-header .subtitle { opacity: 0.85; font-size: 0.95rem; margin-top: 0.3rem; }
    
    .winner-badge {
        display: inline-block;
        background: #28A745;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: bold;
    }
    .runner-up {
        display: inline-block;
        background: #FFC107;
        color: #333;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    .excluded {
        display: inline-block;
        background: #DC3545;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    
    .metric-card {
        background: #F8F9FA;
        border-left: 4px solid #2E75B6;
        padding: 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        padding: 0.6rem 1.2rem;
        background: #F0F2F6;
        border-radius: 6px 6px 0 0;
    }
    .stTabs [aria-selected="true"] { background: #2E75B6; color: white; }
</style>
""", unsafe_allow_html=True)

# ── Заголовок ──
st.markdown("""
<div class="main-header">
    <h1>🔥 FireCompare</h1>
    <div class="subtitle">Об'єктивне порівняння систем пожежної сигналізації — для платформи Cofem Ukraine</div>
</div>
""", unsafe_allow_html=True)

# ── Імпорти движка ──
from engine.pipeline import run_calculation
from engine.mode2_scenarios import run_mode2_analysis
from engine.mode3_memo import build_mode3_memo
from engine.mode3_docx_exporter import export_memo_to_docx
from build_catalog import CATALOG
from tests.fixtures.zamkova_phase_2 import (
    ZAMKOVA_PHASE_2, ZAMKOVA_PHASE_2_PREMIUM, ZAMKOVA_PHASE_2_SIMPLE,
)

# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 🏢 Об'єкт")
    
    scenario_choice = st.selectbox(
        "Завантажити приклад:",
        ["Замкова II черга (NPA: 3 ППКП)",
         "Замкова Преміум (UA+UK страхування)",
         "Замкова Простий (1 ППКП — для контрасту)"],
        index=0,
    )
    
    scenario_map = {
        "Замкова II черга (NPA: 3 ППКП)": ZAMKOVA_PHASE_2,
        "Замкова Преміум (UA+UK страхування)": ZAMKOVA_PHASE_2_PREMIUM,
        "Замкова Простий (1 ППКП — для контрасту)": ZAMKOVA_PHASE_2_SIMPLE,
    }
    base_state = scenario_map[scenario_choice]
    
    # Параметри об'єкта
    obj = base_state.object
    st.markdown(
        f"""
        <div class="metric-card">
        <b>Тип:</b> {obj.object_type.value}<br>
        <b>Площа захищувана:</b> {obj.total_area_m2:,.0f} м²<br>
        <b>Поверхів:</b> {obj.floors_above} + {obj.floors_below}<br>
        <b>Юрисдикції:</b> {', '.join(j.value for j in base_state.pre_object.jurisdictions)}<br>
        <b>Горизонт:</b> {base_state.pre_object.lifetime_horizon.value}<br>
        <b>Захист хибних:</b> {base_state.pre_object.false_alarm_protection.value}<br>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if base_state.npa_architecture:
        st.markdown(f"**NPA-зон:** {len(base_state.npa_architecture.zones)}")
        for z in base_state.npa_architecture.zones:
            st.markdown(f"• {z.name} ({z.fire_zones_count} пож. зон)")
    
    st.markdown("---")
    st.markdown("### 🏭 Comparison-set")
    
    all_mfrs = [m for m in CATALOG.manufacturers 
                if m.manufacturer_id in ["cofem", "tiras", "omega", "varta"]]
    
    selected_mfr_ids = []
    for mfr in all_mfrs:
        default = mfr.manufacturer_id in base_state.comparison_set
        if st.checkbox(mfr.name_ua, value=default, key=f"mfr_{mfr.manufacturer_id}"):
            selected_mfr_ids.append(mfr.manufacturer_id)
    
    st.markdown("---")
    
    run_button = st.button("🚀 РОЗРАХУВАТИ", type="primary", use_container_width=True)

# Оновлюємо comparison_set
state = base_state.model_copy(deep=True)
state.comparison_set = selected_mfr_ids

# ═══════════════════════════════════════════════════════════════════
# ОСНОВНА ОБЛАСТЬ — ВКЛАДКИ
# ═══════════════════════════════════════════════════════════════════

tab1, tab2, tab3 = st.tabs([
    "📊 Mode 1: Порівняння",
    "🔄 Mode 2: Зворотній аналіз",
    "📄 Mode 3: Меморандум",
])

# ── Кешуємо результат у session_state ──
if run_button:
    with st.spinner("Виконую розрахунок..."):
        result = run_calculation(state, CATALOG)
        st.session_state["last_result"] = result
        st.session_state["last_state"] = state

if "last_result" not in st.session_state:
    with tab1:
        st.info("👈 Налаштуйте параметри в sidebar і натисніть «РОЗРАХУВАТИ»")
    with tab2:
        st.info("Спочатку виконайте розрахунок (вкладка Mode 1)")
    with tab3:
        st.info("Спочатку виконайте розрахунок (вкладка Mode 1)")
    st.stop()

result = st.session_state["last_result"]
state = st.session_state["last_state"]


# ═══════════════════════════════════════════════════════════════════
# TAB 1: MODE 1 — COMPARISON
# ═══════════════════════════════════════════════════════════════════

with tab1:
    st.markdown(f"### Результат розрахунку")
    st.caption(
        f"Calculation ID: `{result.calculation_id}` • "
        f"Режим: **{'NPA (multi-panel)' if result.is_multi_panel_mode else 'Простий (1 ППКП)'}** • "
        f"Engine: v{result.engine_version}"
    )
    
    # ── BOM зведення ──
    col1, col2, col3, col4 = st.columns(4)
    bom = result.total_bom
    col1.metric("Детекторів", f"{bom.smoke_detectors_count + bom.heat_detectors_count}",
                f"{bom.smoke_detectors_count}д + {bom.heat_detectors_count}т")
    col2.metric("I/O сигналів", bom.total_logical_signals())
    col3.metric("MCP кнопок", bom.manual_call_points_count)
    col4.metric("Sounders", bom.sounders_count)
    
    st.markdown("---")
    
    # ── Зведена таблиця ──
    if not result.comparison_table:
        st.warning("Жоден виробник не пройшов фільтри. Перевірте comparison-set.")
    else:
        st.markdown("#### 🏆 Зведена таблиця (сортування за overall)")
        
        import pandas as pd
        rows = []
        for idx, row in enumerate(result.comparison_table, 1):
            badge = ""
            if idx == 1:
                badge = "🥇"
            elif idx == 2:
                badge = "🥈"
            elif idx == 3:
                badge = "🥉"
            rows.append({
                "": badge,
                "Виробник": row["manufacturer_name"],
                "Панелей": row.get("panel_count", 1),
                "Адрес": row["addresses_used"],
                "Арх.еф %": f"{row['architectural_efficiency_pct']:.1f}",
                "CAPEX (₴)": f"{row['capex_uah']:,.0f}",
                "L1": f"{row.get('layer_1_capex_score', '—')}",
                "L2": f"{row.get('layer_2_architectural_score', '—')}",
                "L3": f"{row.get('layer_3_functional_score', '—')}",
                "L4": f"{row.get('layer_4_operational_score', '—')}",
                "L5": f"{row.get('layer_5_tco_score', '—')}",
                "OVERALL": f"{row.get('overall_score', '—')}",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Адаптовані ваги
        feasible = [r for r in result.manufacturer_results 
                   if not r.excluded and r.scores and r.scores.applied_weights]
        if feasible:
            w = feasible[0].scores.applied_weights
            st.caption(
                f"**Адаптовані ваги шарів:** "
                f"CAPEX={w.get('layer_1_capex', 0)*100:.0f}% • "
                f"Архітектура={w.get('layer_2_architectural', 0)*100:.0f}% • "
                f"Функц={w.get('layer_3_functional', 0)*100:.0f}% • "
                f"Експл={w.get('layer_4_operational', 0)*100:.0f}% • "
                f"TCO={w.get('layer_5_tco', 0)*100:.0f}%"
            )
        
        if result.warnings:
            for w in result.warnings:
                st.warning(f"⚠ {w}")
        
        st.markdown("---")
        
        # ── Барплоти ──
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### Overall Score")
            chart_data = pd.DataFrame({
                "Виробник": [r["manufacturer_name"] for r in result.comparison_table],
                "Overall": [r.get("overall_score", 0) for r in result.comparison_table],
            }).set_index("Виробник")
            st.bar_chart(chart_data, color="#2E75B6", height=300)
        
        with col_right:
            st.markdown("#### CAPEX (₴)")
            chart_data = pd.DataFrame({
                "Виробник": [r["manufacturer_name"] for r in result.comparison_table],
                "CAPEX": [r["capex_uah"] for r in result.comparison_table],
            }).set_index("Виробник")
            st.bar_chart(chart_data, color="#FFA500", height=300)
        
        # Деталізація по виробниках
        st.markdown("---")
        st.markdown("#### 🔍 Деталізація обраного виробника")
        
        feasible_names = [r["manufacturer_name"] for r in result.comparison_table]
        if feasible_names:
            selected_name = st.selectbox("Виробник:", feasible_names)
            selected_mfr_result = next(
                (r for r in result.manufacturer_results if r.manufacturer_name == selected_name),
                None,
            )
            
            if selected_mfr_result and selected_mfr_result.scores:
                s = selected_mfr_result.scores
                
                # 5 шарів — expandable
                for layer_label, layer_score in [
                    ("Layer 1 — CAPEX", s.layer_1_capex),
                    ("Layer 2 — Архітектурна ефективність", s.layer_2_architectural),
                    ("Layer 3 — Функціональний рівень", s.layer_3_functional),
                    ("Layer 4 — Експлуатація", s.layer_4_operational),
                    ("Layer 5 — TCO", s.layer_5_tco),
                ]:
                    if layer_score:
                        with st.expander(f"{layer_label} — Бал: {layer_score.score:.1f}"):
                            st.write(layer_score.reasoning)
                            if layer_score.raw_value is not None:
                                if layer_score.unit == "UAH":
                                    st.metric("Абсолютне значення", f"{layer_score.raw_value:,.0f} ₴")
                                else:
                                    st.metric("Абсолютне значення", 
                                             f"{layer_score.raw_value:.1f} {layer_score.unit or ''}")


# ═══════════════════════════════════════════════════════════════════
# TAB 2: MODE 2 — REVERSE PRIORITY
# ═══════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("### 🔄 Mode 2: Зворотній сценарний аналіз")
    st.caption(
        "Алгоритм перебирає 16 комбінацій пре-об'єктних умов (2⁴) і показує, "
        "за яких параметрів кожен виробник був би переможцем. "
        "Це формує **чесний інструмент** — клієнт бачить умови, де його варіант кращий."
    )
    
    run_mode2 = st.button("🔄 Запустити Mode 2 (16 сценаріїв)", type="primary")
    
    if run_mode2 or "mode2_result" in st.session_state:
        if run_mode2:
            with st.spinner("Прогоняю 16 сценаріїв..."):
                mode2_result = run_mode2_analysis(state, CATALOG)
                st.session_state["mode2_result"] = mode2_result
        else:
            mode2_result = st.session_state["mode2_result"]
        
        # Розподіл перемог
        st.markdown("#### Розподіл перемог")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            for mfr_id, count in sorted(mode2_result.winner_distribution.items(),
                                         key=lambda x: -x[1]):
                pct = round(count / mode2_result.total_scenarios * 100, 0)
                mfr_name = next(
                    (m.name_ua for m in CATALOG.manufacturers
                     if m.manufacturer_id == mfr_id), mfr_id,
                )
                st.metric(mfr_name, f"{count} / {mode2_result.total_scenarios}", f"{pct}%")
        
        with col2:
            import pandas as pd
            data = pd.DataFrame({
                "Виробник": [
                    next((m.name_ua for m in CATALOG.manufacturers if m.manufacturer_id == mfr_id), mfr_id)
                    for mfr_id in mode2_result.winner_distribution.keys()
                ],
                "Перемог": list(mode2_result.winner_distribution.values()),
            }).set_index("Виробник")
            st.bar_chart(data, color="#28A745")
        
        # Спостереження
        st.markdown("#### 💡 Аналітичні спостереження")
        for obs in mode2_result.observations:
            st.markdown(f"• {obs}")
        
        st.markdown("---")
        
        # Розгорнута таблиця сценаріїв
        st.markdown("#### Сценарії (16 комбінацій)")
        scen_rows = []
        for scen in mode2_result.scenarios:
            scen_rows.append({
                "ID": scen.scenario_id,
                "Горизонт": "довгий" if "L" in scen.scenario_code[2] else "короткий",
                "Захист хибних": "преміум" if "P" in scen.scenario_code[8] else "стандарт",
                "Бюджет": "обмеж." if "Y" in scen.scenario_code[14] else "вільний",
                "Mobile/Cloud": "так" if "Y" in scen.scenario_code[19] else "ні",
                "Переможець": scen.winner_name or "—",
                "Overall": f"{scen.winner_overall:.1f}" if scen.winner_overall else "—",
            })
        df_scen = pd.DataFrame(scen_rows)
        st.dataframe(df_scen, use_container_width=True, hide_index=True)
        
        # Чесна сторона — коли Cofem не виграє
        if mode2_result.cofem_loses_in:
            st.markdown("---")
            st.markdown("#### 🎯 Чесний інструмент — коли Cofem не виграє")
            for loss in mode2_result.cofem_loses_in:
                st.info(loss)


# ═══════════════════════════════════════════════════════════════════
# TAB 3: MODE 3 — MEMO
# ═══════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("### 📄 Mode 3: Меморандум по виробнику")
    st.caption(
        "Генерує аналітичний документ із детальним аналізом обраного виробника "
        "на даному об'єкті. Експорт у DOCX."
    )
    
    feasible_names = {r["manufacturer_id"]: r["manufacturer_name"] 
                     for r in result.comparison_table}
    
    if not feasible_names:
        st.warning("Немає виробників для меморандуму.")
    else:
        target_id = st.selectbox(
            "Виробник для меморандуму:",
            options=list(feasible_names.keys()),
            format_func=lambda x: feasible_names[x],
        )
        
        if st.button(f"📄 Згенерувати меморандум для {feasible_names[target_id]}", type="primary"):
            with st.spinner("Формую меморандум та експортую DOCX..."):
                memo = build_mode3_memo(
                    calc_result=result,
                    target_manufacturer_id=target_id,
                    catalog=CATALOG,
                    state=state,
                )
                
                if not memo:
                    st.error("Не вдалося сформувати меморандум.")
                else:
                    # Експорт
                    output_path = f"/tmp/Memo_{target_id}_{result.calculation_id}.docx"
                    try:
                        export_memo_to_docx(memo, output_path)
                        
                        # Прев'ю на сторінці
                        st.success(f"✅ Меморандум згенеровано: 7 розділів, DOCX готовий")
                        
                        # Download button
                        with open(output_path, "rb") as f:
                            st.download_button(
                                "⬇ Завантажити DOCX",
                                data=f.read(),
                                file_name=f"Memo_{feasible_names[target_id]}_{state.session_id}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            )
                        
                        # Прев'ю розділів
                        st.markdown("---")
                        st.markdown(f"#### {memo.title}")
                        st.caption(memo.subtitle)
                        
                        for section in [
                            memo.section_1_profile,
                            memo.section_2_compliance,
                            memo.section_3_technical,
                            memo.section_4_economics,
                            memo.section_5_position,
                            memo.section_6_strengths_weaknesses,
                            memo.section_7_summary,
                        ]:
                            with st.expander(section.title):
                                for para in section.content:
                                    st.write(para)
                                if section.table_data:
                                    df = pd.DataFrame(section.table_data[1:],
                                                     columns=section.table_data[0])
                                    st.dataframe(df, use_container_width=True, hide_index=True)
                                for bullet in section.bullet_points:
                                    st.markdown(f"• {bullet}")
                    except Exception as e:
                        st.error(f"Помилка експорту DOCX: {e}")
