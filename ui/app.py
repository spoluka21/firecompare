"""
FireCompare — Streamlit UI з підтримкою UA/EN.

Двомовний інтерфейс для презентації керівництву Cofem
(регіональний менеджер виступає перекладачем — бачить EN-версію).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

st.set_page_config(
    page_title="FireCompare — Cofem Ukraine",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Стилі ──
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
    
    .winner-badge { background: #28A745; color: white; padding: 0.2rem 0.6rem; 
                    border-radius: 4px; font-size: 0.85rem; font-weight: bold; }
    .runner-up { background: #FFC107; color: #333; padding: 0.2rem 0.6rem;
                 border-radius: 4px; font-size: 0.85rem; }
    .excluded { background: #DC3545; color: white; padding: 0.2rem 0.6rem;
                border-radius: 4px; font-size: 0.85rem; }
    
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

# ── Імпорти движка ──
from engine.pipeline import run_calculation
from engine.mode2_scenarios import run_mode2_analysis
from engine.mode3_memo import build_mode3_memo
from engine.mode3_docx_exporter import export_memo_to_docx
from build_catalog import CATALOG
from tests.fixtures.zamkova_phase_2 import (
    ZAMKOVA_PHASE_2, ZAMKOVA_PHASE_2_PREMIUM, ZAMKOVA_PHASE_2_SIMPLE,
)
from ui.i18n import t, mfr_name, get_lang


# ═══════════════════════════════════════════════════════════════════
# LANGUAGE SELECTOR — на самому верху sidebar
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    lang_choice = st.radio(
        t("lang_label"),
        options=["ua", "en"],
        format_func=lambda x: "🇺🇦 Українська" if x == "ua" else "🇬🇧 English",
        horizontal=True,
        key="language",  # автоматично зберігається у session_state
    )
    st.markdown("---")


# ── Заголовок (після вибору мови, тому використовує переклад) ──
st.markdown(f"""
<div class="main-header">
    <h1>🔥 FireCompare</h1>
    <div class="subtitle">{t("app_subtitle")}</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(f"### {t('object_section')}")
    
    scenario_options = {
        t("scenario_npa"): ZAMKOVA_PHASE_2,
        t("scenario_premium"): ZAMKOVA_PHASE_2_PREMIUM,
        t("scenario_simple"): ZAMKOVA_PHASE_2_SIMPLE,
    }
    
    scenario_choice = st.selectbox(
        t("scenario_select"),
        list(scenario_options.keys()),
        index=0,
    )
    base_state = scenario_options[scenario_choice]
    
    obj = base_state.object
    st.markdown(
        f"""
        <div class="metric-card">
        <b>{t('obj_type')}:</b> {obj.object_type.value}<br>
        <b>{t('obj_area')}:</b> {obj.total_area_m2:,.0f} м²<br>
        <b>{t('obj_floors')}:</b> {obj.floors_above} + {obj.floors_below}<br>
        <b>{t('obj_jurisdictions')}:</b> {', '.join(j.value for j in base_state.pre_object.jurisdictions)}<br>
        <b>{t('obj_horizon')}:</b> {base_state.pre_object.lifetime_horizon.value}<br>
        <b>{t('obj_false_alarm')}:</b> {base_state.pre_object.false_alarm_protection.value}<br>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if base_state.npa_architecture:
        st.markdown(f"**{t('npa_zones_count')}:** {len(base_state.npa_architecture.zones)}")
        for z in base_state.npa_architecture.zones:
            zone_label = z.name_en if get_lang() == "en" and z.name_en else z.name
            # Singular/plural для EN
            if get_lang() == "en":
                fire_zones_text = "fire zone" if z.fire_zones_count == 1 else "fire zones"
            else:
                fire_zones_text = t("fire_zones_short")
            st.markdown(f"• {zone_label} ({z.fire_zones_count} {fire_zones_text})")
    
    st.markdown("---")
    st.markdown(f"### {t('comparison_set')}")
    
    all_mfrs = [m for m in CATALOG.manufacturers 
                if m.manufacturer_id in ["cofem", "tiras", "omega", "varta"]]
    
    selected_mfr_ids = []
    for mfr in all_mfrs:
        default = mfr.manufacturer_id in base_state.comparison_set
        if st.checkbox(mfr_name(mfr), value=default, key=f"mfr_{mfr.manufacturer_id}"):
            selected_mfr_ids.append(mfr.manufacturer_id)
    
    st.markdown("---")
    run_button = st.button(t("calculate_btn"), type="primary", use_container_width=True)


state = base_state.model_copy(deep=True)
state.comparison_set = selected_mfr_ids

# Локалізована мапа назв виробників (для UA/EN)
MFR_DISPLAY = {m.manufacturer_id: mfr_name(m) for m in CATALOG.manufacturers}


def display_name(mfr_id: str, fallback: str = "") -> str:
    """Повертає локалізовану назву виробника за id"""
    return MFR_DISPLAY.get(mfr_id, fallback)


# ═══════════════════════════════════════════════════════════════════
# ВКЛАДКИ
# ═══════════════════════════════════════════════════════════════════

tab1, tab2, tab3 = st.tabs([t("tab1_label"), t("tab2_label"), t("tab3_label")])

if run_button:
    with st.spinner(t("calculating_spinner")):
        result = run_calculation(state, CATALOG)
        st.session_state["last_result"] = result
        st.session_state["last_state"] = state
        # Очищуємо mode2 при новому розрахунку
        if "mode2_result" in st.session_state:
            del st.session_state["mode2_result"]

if "last_result" not in st.session_state:
    with tab1:
        st.info(t("configure_and_run"))
    with tab2:
        st.info(t("run_first"))
    with tab3:
        st.info(t("run_first"))
    st.stop()

result = st.session_state["last_result"]
state = st.session_state["last_state"]


# ═══════════════════════════════════════════════════════════════════
# TAB 1: MODE 1
# ═══════════════════════════════════════════════════════════════════

with tab1:
    st.markdown(f"### {t('calc_result_header')}")
    mode_text = t("mode_npa") if result.is_multi_panel_mode else t("mode_simple")
    st.caption(
        f"{t('calc_id_label')}: `{result.calculation_id}` • "
        f"{t('calc_mode_label')}: **{mode_text}** • "
        f"{t('engine_label')}: v{result.engine_version}"
    )
    
    col1, col2, col3, col4 = st.columns(4)
    bom = result.total_bom
    col1.metric(t("metric_detectors"),
                f"{bom.smoke_detectors_count + bom.heat_detectors_count}",
                f"{bom.smoke_detectors_count}{t('detector_smoke_short')} + "
                f"{bom.heat_detectors_count}{t('detector_heat_short')}")
    col2.metric(t("metric_io_signals"), bom.total_logical_signals())
    col3.metric(t("metric_mcp"), bom.manual_call_points_count)
    col4.metric(t("metric_sounders"), bom.sounders_count)
    
    st.markdown("---")
    
    if not result.comparison_table:
        st.warning(t("no_mfr_warning"))
    else:
        st.markdown(f"#### {t('summary_table_header')}")
        
        import pandas as pd
        rows = []
        for idx, row in enumerate(result.comparison_table, 1):
            badge = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else ""
            rows.append({
                "": badge,
                t("col_manufacturer"): display_name(row["manufacturer_id"], row["manufacturer_name"]),
                t("col_panels"): row.get("panel_count", 1),
                t("col_addresses"): row["addresses_used"],
                t("col_arch_eff"): f"{row['architectural_efficiency_pct']:.1f}",
                t("col_capex"): f"{row['capex_uah']:,.0f}",
                "L1": f"{row.get('layer_1_capex_score', '—')}",
                "L2": f"{row.get('layer_2_architectural_score', '—')}",
                "L3": f"{row.get('layer_3_functional_score', '—')}",
                "L4": f"{row.get('layer_4_operational_score', '—')}",
                "L5": f"{row.get('layer_5_tco_score', '—')}",
                "OVERALL": f"{row.get('overall_score', '—')}",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        feasible = [r for r in result.manufacturer_results 
                   if not r.excluded and r.scores and r.scores.applied_weights]
        if feasible:
            w = feasible[0].scores.applied_weights
            st.caption(
                f"{t('adapted_weights_label')} "
                f"{t('weight_capex')}={w.get('layer_1_capex', 0)*100:.0f}% • "
                f"{t('weight_arch')}={w.get('layer_2_architectural', 0)*100:.0f}% • "
                f"{t('weight_func')}={w.get('layer_3_functional', 0)*100:.0f}% • "
                f"{t('weight_oper')}={w.get('layer_4_operational', 0)*100:.0f}% • "
                f"{t('weight_tco')}={w.get('layer_5_tco', 0)*100:.0f}%"
            )
        
        if result.warnings:
            for w in result.warnings:
                st.warning(f"⚠ {w}")
        
        st.markdown("---")
        
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown(f"#### {t('chart_overall')}")
            chart_data = pd.DataFrame({
                t("col_manufacturer"): [display_name(r["manufacturer_id"], r["manufacturer_name"]) 
                                         for r in result.comparison_table],
                "Overall": [r.get("overall_score", 0) for r in result.comparison_table],
            }).set_index(t("col_manufacturer"))
            st.bar_chart(chart_data, color="#2E75B6", height=300)
        
        with col_right:
            st.markdown(f"#### {t('chart_capex')}")
            chart_data = pd.DataFrame({
                t("col_manufacturer"): [display_name(r["manufacturer_id"], r["manufacturer_name"]) 
                                         for r in result.comparison_table],
                "CAPEX": [r["capex_uah"] for r in result.comparison_table],
            }).set_index(t("col_manufacturer"))
            st.bar_chart(chart_data, color="#FFA500", height=300)
        
        st.markdown("---")
        st.markdown(f"#### {t('details_header')}")
        
        feasible_names = [(r["manufacturer_id"], display_name(r["manufacturer_id"], r["manufacturer_name"])) 
                          for r in result.comparison_table]
        if feasible_names:
            selected_label = st.selectbox(
                t("select_manufacturer"), 
                [n[1] for n in feasible_names]
            )
            # Знайти manufacturer_id за назвою
            selected_id = next((n[0] for n in feasible_names if n[1] == selected_label), None)
            selected_mfr_result = next(
                (r for r in result.manufacturer_results if r.manufacturer_id == selected_id),
                None,
            )
            
            if selected_mfr_result and selected_mfr_result.scores:
                s = selected_mfr_result.scores
                for layer_label_key, layer_score in [
                    ("layer_1_label", s.layer_1_capex),
                    ("layer_2_label", s.layer_2_architectural),
                    ("layer_3_label", s.layer_3_functional),
                    ("layer_4_label", s.layer_4_operational),
                    ("layer_5_label", s.layer_5_tco),
                ]:
                    if layer_score:
                        with st.expander(f"{t(layer_label_key)} — {t('score_label')}: {layer_score.score:.1f}"):
                            st.write(layer_score.reasoning)
                            if layer_score.raw_value is not None:
                                if layer_score.unit == "UAH":
                                    st.metric(t("abs_value_label"), 
                                             f"{layer_score.raw_value:,.0f} ₴")
                                else:
                                    st.metric(t("abs_value_label"), 
                                             f"{layer_score.raw_value:.1f} {layer_score.unit or ''}")


# ═══════════════════════════════════════════════════════════════════
# TAB 2: MODE 2
# ═══════════════════════════════════════════════════════════════════

with tab2:
    st.markdown(f"### {t('mode2_header')}")
    st.caption(t("mode2_caption"))
    
    run_mode2 = st.button(t("mode2_run_btn"), type="primary")
    
    if run_mode2 or "mode2_result" in st.session_state:
        if run_mode2:
            with st.spinner(t("mode2_spinner")):
                mode2_result = run_mode2_analysis(state, CATALOG, language=get_lang())
                st.session_state["mode2_result"] = mode2_result
        else:
            mode2_result = st.session_state["mode2_result"]
        
        st.markdown(f"#### {t('winners_dist_header')}")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            for mfr_id, count in sorted(mode2_result.winner_distribution.items(), 
                                         key=lambda x: -x[1]):
                pct = round(count / mode2_result.total_scenarios * 100, 0)
                st.metric(display_name(mfr_id, mfr_id), 
                          f"{count} / {mode2_result.total_scenarios}", f"{pct}%")
        
        with col2:
            import pandas as pd
            data = pd.DataFrame({
                t("col_manufacturer"): [display_name(mfr_id, mfr_id) 
                                         for mfr_id in mode2_result.winner_distribution.keys()],
                "Wins": list(mode2_result.winner_distribution.values()),
            }).set_index(t("col_manufacturer"))
            st.bar_chart(data, color="#28A745")
        
        st.markdown(f"#### {t('observations_header')}")
        for obs in mode2_result.observations:
            st.markdown(f"• {obs}")
        
        st.markdown("---")
        st.markdown(f"#### {t('scenarios_table_header')}")
        scen_rows = []
        for scen in mode2_result.scenarios:
            scen_rows.append({
                "ID": scen.scenario_id,
                t("col_horizon"): t("horizon_long") if "L" in scen.scenario_code[2] 
                                                    else t("horizon_short"),
                t("col_false_alarm"): t("fa_premium") if "P" in scen.scenario_code[8] 
                                                       else t("fa_standard"),
                t("col_budget"): t("budget_constrained") if "Y" in scen.scenario_code[14] 
                                                          else t("budget_free"),
                t("col_mobile_cloud"): t("yes_short") if "Y" in scen.scenario_code[19] 
                                                        else t("no_short"),
                t("col_winner"): scen.winner_name or "—",
                t("col_overall"): f"{scen.winner_overall:.1f}" if scen.winner_overall else "—",
            })
        df_scen = pd.DataFrame(scen_rows)
        st.dataframe(df_scen, use_container_width=True, hide_index=True)
        
        if mode2_result.cofem_loses_in:
            st.markdown("---")
            st.markdown(f"#### {t('cofem_loses_header')}")
            for loss in mode2_result.cofem_loses_in:
                st.info(loss)


# ═══════════════════════════════════════════════════════════════════
# TAB 3: MODE 3
# ═══════════════════════════════════════════════════════════════════

with tab3:
    st.markdown(f"### {t('mode3_header')}")
    st.caption(t("mode3_caption"))
    
    feasible_names = {r["manufacturer_id"]: display_name(r["manufacturer_id"], r["manufacturer_name"]) 
                     for r in result.comparison_table}
    
    if not feasible_names:
        st.warning(t("no_mfr_for_memo"))
    else:
        target_id = st.selectbox(
            t("select_for_memo"),
            options=list(feasible_names.keys()),
            format_func=lambda x: feasible_names[x],
        )
        
        if st.button(f"{t('gen_memo_btn')} {feasible_names[target_id]}", type="primary"):
            with st.spinner(t("memo_spinner")):
                memo = build_mode3_memo(
                    calc_result=result,
                    target_manufacturer_id=target_id,
                    catalog=CATALOG,
                    state=state,
                    language=get_lang(),
                )
                
                if not memo:
                    st.error(t("memo_failure"))
                else:
                    output_path = f"/tmp/Memo_{target_id}_{result.calculation_id}.docx"
                    try:
                        export_memo_to_docx(memo, output_path)
                        st.success(t("memo_success"))
                        
                        with open(output_path, "rb") as f:
                            st.download_button(
                                t("memo_download"),
                                data=f.read(),
                                file_name=f"Memo_{feasible_names[target_id]}_{state.session_id}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            )
                        
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
                        st.error(f"{t('memo_export_error')}: {e}")
