"""
UI модуль для Mode 4: Maintenance (калькулятор ТО)

Викликається з ui/app.py. Окремий модуль, бо логіка велика.
"""
import streamlit as st
import pandas as pd

from engine.maintenance_calculator import (
    MaintenanceParams, SystemComposition, calculate_maintenance,
)
from ui.i18n import t, get_lang


def render_maintenance_sidebar_params(default_area: float, default_distance: float = 5.0):
    """
    Рендерить sidebar-секцію з параметрами ТО.
    Повертає MaintenanceParams або None (якщо checkbox вимкнено).
    """
    st.markdown(f"### {t('maintenance_section')}")
    
    enable_mnt = st.checkbox(
        t("maintenance_enable"), value=True, key="enable_mnt"
    )
    
    if not enable_mnt:
        return None
    
    # Параметри
    distance_km = st.number_input(
        t("mnt_distance"),
        min_value=0.0, max_value=500.0, value=default_distance, step=1.0,
        key="mnt_distance_input",
    )
    
    n_damages = st.number_input(
        t("mnt_n_damages"),
        min_value=0.0, max_value=10.0, value=0.3, step=0.1,
        key="mnt_damages_input",
    )
    
    # Склад СПЗ
    st.markdown(f"**{t('mnt_composition')}:**")
    has_monitoring = st.checkbox(t("mnt_has_monitoring"), value=False, key="mnt_monitoring")
    has_extinguish = st.checkbox(t("mnt_has_extinguish"), value=False, key="mnt_extinguish")
    has_smoke_vent = st.checkbox(t("mnt_has_smoke_vent"), value=False, key="mnt_smoke_vent")
    has_valves = st.checkbox(t("mnt_has_valves"), value=False, key="mnt_valves")
    has_engineering = st.checkbox(t("mnt_has_engineering"), value=False, key="mnt_engineering")
    
    composition = SystemComposition(
        has_monitoring=has_monitoring,
        has_extinguish=has_extinguish,
        has_smoke_vent=has_smoke_vent,
        has_valves=has_valves,
        has_engineering_systems=has_engineering,
    )
    
    return MaintenanceParams(
        object_area_m2=default_area,
        composition=composition,
        distance_km=distance_km,
        n_damages_month=n_damages,
    )


def render_breakdown_tables(result, lang: str = "ua"):
    """Рендерить 3 таблиці: час, собівартість, ціна"""
    bd = result.breakdown if hasattr(result, "breakdown") else result["breakdown"]
    
    # Якщо bd — це dict (з pipeline), конвертуємо доступ
    if isinstance(bd, dict):
        b = bd
    else:
        b = bd.model_dump()
    
    params = result.params if hasattr(result, "params") else result["params"]
    if isinstance(params, dict):
        p = params
    else:
        p = params.model_dump()
    
    # ── Таблиця часу ──
    st.markdown(f"#### {t('mnt_time_table_header')}")
    time_rows = [
        {
            t("mnt_col_item"): t("mnt_row_t_planned"),
            t("mnt_col_formula"): f"K = {b['complexity_k']}",
            t("mnt_col_hours"): f"{b['t_planned']:.2f}",
        },
        {
            t("mnt_col_item"): t("mnt_row_t_travel_planned"),
            t("mnt_col_formula"): f"{p.get('n_planned_visits', 2)} визитів",
            t("mnt_col_hours"): f"{b['t_travel_planned']:.2f}",
        },
        {
            t("mnt_col_item"): t("mnt_row_t_false"),
            t("mnt_col_formula"): "хибних × (час + дорога)",
            t("mnt_col_hours"): f"{b['t_false_alarms']:.2f}",
        },
        {
            t("mnt_col_item"): t("mnt_row_t_damages"),
            t("mnt_col_formula"): f"{p.get('n_damages_month', 0)} × (3.0 + дорога)",
            t("mnt_col_hours"): f"{b['t_damages']:.2f}",
        },
        {
            t("mnt_col_item"): f"**{t('mnt_row_t_total')}**",
            t("mnt_col_formula"): "",
            t("mnt_col_hours"): f"**{b['t_total']:.2f}**",
        },
    ]
    st.dataframe(pd.DataFrame(time_rows), hide_index=True, use_container_width=True)
    
    # ── Таблиця собівартості ──
    st.markdown(f"#### {t('mnt_cost_table_header')}")
    cost_rows = [
        {
            t("mnt_col_item"): t("mnt_row_cost_labor"),
            t("mnt_col_formula"): f"{b['t_total']:.2f} год × {b['rate_per_hour']:.2f}",
            t("mnt_col_uah"): f"{b['cost_labor']:,.2f}",
        },
        {
            t("mnt_col_item"): t("mnt_row_cost_transport"),
            t("mnt_col_formula"): f"{b['total_km']:.1f} км × {b['transport_per_km']:.0f}",
            t("mnt_col_uah"): f"{b['cost_transport']:,.2f}",
        },
        {
            t("mnt_col_item"): t("mnt_row_cost_parts"),
            t("mnt_col_formula"): f"{p.get('n_damages_month', 0)} × запчастини",
            t("mnt_col_uah"): f"{b['cost_parts']:,.2f}",
        },
        {
            t("mnt_col_item"): t("mnt_row_cost_admin"),
            t("mnt_col_formula"): "ФОП × 15%",
            t("mnt_col_uah"): f"{b['cost_admin']:,.2f}",
        },
        {
            t("mnt_col_item"): f"**{t('mnt_row_cost_own_total')}**",
            t("mnt_col_formula"): "",
            t("mnt_col_uah"): f"**{b['cost_own_total']:,.2f}**",
        },
    ]
    st.dataframe(pd.DataFrame(cost_rows), hide_index=True, use_container_width=True)
    
    # ── Таблиця ціни ──
    st.markdown(f"#### {t('mnt_price_table_header')}")
    price_rows = [
        {
            t("mnt_col_item"): t("mnt_row_price_own"),
            t("mnt_col_formula"): f"{b['cost_own_total']:,.2f} × 1.6",
            t("mnt_col_uah"): f"{b['price_own_calculated']:,.2f}",
        },
    ]
    if b["subcontract_pass_through"] > 0:
        price_rows.append({
            t("mnt_col_item"): t("mnt_row_subcontract"),
            t("mnt_col_formula"): "за рахунком підрядника",
            t("mnt_col_uah"): f"{b['subcontract_pass_through']:,.2f}",
        })
    price_rows.append({
        t("mnt_col_item"): f"**{t('mnt_row_calculated')}**",
        t("mnt_col_formula"): "",
        t("mnt_col_uah"): f"**{b['price_calculated_total']:,.2f}**",
    })
    
    if b["discount_uah"] > 0:
        price_rows.append({
            t("mnt_col_item"): t("mnt_row_discount"),
            t("mnt_col_formula"): f"−{p.get('strategic_discount_pct', 0):.1f}%",
            t("mnt_col_uah"): f"−{b['discount_uah']:,.2f}",
        })
    
    price_rows.append({
        t("mnt_col_item"): f"**{t('mnt_row_final')}**",
        t("mnt_col_formula"): "",
        t("mnt_col_uah"): f"**{b['price_final_month']:,.2f}**",
    })
    
    st.dataframe(pd.DataFrame(price_rows), hide_index=True, use_container_width=True)
    
    # ── Підсумок ──
    col1, col2 = st.columns(2)
    col1.metric(t("mnt_summary_month"), f"{b['price_final_month']:,.0f} ₴")
    col2.metric(t("mnt_summary_year"), f"{b['price_final_year']:,.0f} ₴")


def render_mode4_tab(result, state, catalog, display_name_func):
    """
    Рендерить вкладку Mode 4 у головному UI.
    
    Args:
        result: CalculationResult з pipeline (або None, якщо ще не було)
        state: ObjectState (актуальний)
        catalog: Catalog
        display_name_func: функція для локалізованого імені виробника
    """
    st.markdown(f"### {t('mnt_header')}")
    st.caption(t("mnt_caption"))
    
    # ── Якщо є result з pipeline і там є maintenance дані — показуємо breakdown по виробниках
    has_maintenance_in_pipeline = False
    if result and result.manufacturer_results:
        has_maintenance_in_pipeline = any(
            mr.maintenance for mr in result.manufacturer_results
        )
    
    if has_maintenance_in_pipeline:
        st.markdown(f"#### {t('mnt_show_breakdown')}")
        st.caption(t("mnt_breakdown_caption"))
        
        # Зведена таблиця ТО по виробниках
        rows = []
        for mr in result.manufacturer_results:
            if not mr.maintenance or mr.excluded:
                continue
            bd = mr.maintenance["breakdown"]
            rows.append({
                t("col_manufacturer"): display_name_func(
                    mr.manufacturer_id, mr.manufacturer_name
                ),
                t("mnt_col_hours"): f"{bd['t_total']:.2f}",
                t("col_maintenance_month"): f"{bd['price_final_month']:,.0f}",
                t("col_maintenance_year"): f"{bd['price_final_year']:,.0f}",
            })
        
        if rows:
            # Сортуємо за ціною ТО
            rows.sort(key=lambda r: float(r[t("col_maintenance_month")].replace(",", "")))
            df = pd.DataFrame(rows)
            st.dataframe(df, hide_index=True, use_container_width=True)
            
            # Деталізація обраного виробника
            mfr_names = [r[t("col_manufacturer")] for r in rows]
            selected = st.selectbox(
                t("select_manufacturer"),
                mfr_names,
                key="mnt_select_mfr",
            )
            
            # Знайти відповідний maintenance result
            mr_selected = next(
                (mr for mr in result.manufacturer_results 
                 if mr.maintenance and 
                 display_name_func(mr.manufacturer_id, mr.manufacturer_name) == selected),
                None,
            )
            
            if mr_selected and mr_selected.maintenance:
                st.markdown("---")
                render_breakdown_tables(mr_selected.maintenance, lang=get_lang())
                
                # Кнопка експорту DOCX
                st.markdown("---")
                if st.button(
                    t("mnt_export_btn"),
                    type="primary",
                    key=f"mfr_export_{mr_selected.manufacturer_id}",
                ):
                    with st.spinner("..."):
                        from engine.maintenance_docx_exporter import export_maintenance_memo_to_docx
                        from engine.maintenance_calculator import MaintenanceResult
                        import tempfile, os
                        
                        # Реконструюємо MaintenanceResult з dict
                        try:
                            mnt_result_obj = MaintenanceResult(**mr_selected.maintenance)
                            tmp_path = os.path.join(
                                tempfile.gettempdir(),
                                f"Memo_Maintenance_{mr_selected.manufacturer_id}_{get_lang()}.docx",
                            )
                            export_maintenance_memo_to_docx(
                                mnt_result_obj, tmp_path, get_lang(),
                            )
                            with open(tmp_path, "rb") as f:
                                st.download_button(
                                    t("mnt_download_btn"),
                                    data=f.read(),
                                    file_name=(
                                        f"Memo_Maintenance_"
                                        f"{mr_selected.manufacturer_name}.docx"
                                    ),
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    key=f"mfr_download_{mr_selected.manufacturer_id}",
                                )
                        except Exception as e:
                            st.error(f"Error: {e}")
        
        st.markdown("---")
    
    # ── Standalone-розрахунок ──
    with st.expander(f"➕ {t('mnt_standalone_header')}", expanded=not has_maintenance_in_pipeline):
        st.caption(t("mnt_standalone_caption"))
        
        # Окремі поля для standalone
        col_a, col_b = st.columns(2)
        with col_a:
            sa_area = st.number_input(
                t("obj_area"),
                min_value=10.0, max_value=200000.0, value=9000.0, step=100.0,
                key="sa_area",
            )
            sa_distance = st.number_input(
                t("mnt_distance"),
                min_value=0.0, max_value=500.0, value=1.0, step=1.0,
                key="sa_distance",
            )
            sa_n_damages = st.number_input(
                t("mnt_n_damages"),
                min_value=0.0, max_value=10.0, value=0.5, step=0.1,
                key="sa_damages",
            )
            sa_n_false = st.number_input(
                "False alarms / mo" if get_lang() == "en" else "Хибних/міс",
                min_value=0.0, max_value=20.0, value=2.0, step=0.5,
                key="sa_false",
            )
        with col_b:
            st.markdown(f"**{t('mnt_composition')}:**")
            sa_monitoring = st.checkbox(
                t("mnt_has_monitoring"), value=False, key="sa_monitoring"
            )
            sa_extinguish = st.checkbox(
                t("mnt_has_extinguish"), value=True, key="sa_extinguish"
            )
            sa_smoke = st.checkbox(t("mnt_has_smoke_vent"), value=False, key="sa_smoke")
            sa_valves = st.checkbox(t("mnt_has_valves"), value=False, key="sa_valves")
            sa_eng = st.checkbox(t("mnt_has_engineering"), value=False, key="sa_eng")
            
            sa_discount = st.slider(
                t("mnt_strategic_discount"),
                min_value=0.0, max_value=30.0, value=0.0, step=0.5,
                key="sa_discount",
            )
        
        # Розрахунок
        sa_params = MaintenanceParams(
            object_area_m2=sa_area,
            composition=SystemComposition(
                has_monitoring=sa_monitoring,
                has_extinguish=sa_extinguish,
                has_smoke_vent=sa_smoke,
                has_valves=sa_valves,
                has_engineering_systems=sa_eng,
            ),
            distance_km=sa_distance,
            n_damages_month=sa_n_damages,
            n_false_alarms_month=sa_n_false,
            strategic_discount_pct=sa_discount,
        )
        
        sa_result = calculate_maintenance(sa_params)
        
        st.markdown("---")
        render_breakdown_tables(sa_result, lang=get_lang())
        
        # Кнопка експорту DOCX для standalone
        st.markdown("---")
        if st.button(t("mnt_export_btn"), type="primary", key="sa_export_btn"):
            with st.spinner("..."):
                from engine.maintenance_docx_exporter import export_maintenance_memo_to_docx
                import tempfile, os
                tmp_path = os.path.join(
                    tempfile.gettempdir(),
                    f"Memo_Maintenance_Standalone_{get_lang()}.docx",
                )
                try:
                    export_maintenance_memo_to_docx(sa_result, tmp_path, get_lang())
                    with open(tmp_path, "rb") as f:
                        st.download_button(
                            t("mnt_download_btn"),
                            data=f.read(),
                            file_name=f"Memo_Maintenance_Standalone.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="sa_download",
                        )
                except Exception as e:
                    st.error(f"Error: {e}")
