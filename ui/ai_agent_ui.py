"""
UI модуль для Tab 5: AI Assistant (чат з Claude)

Викликається з ui/app.py. Окремий модуль для чистоти архітектури.
"""
import streamlit as st

from engine.ai_agent import (
    AIAgent, ChatMessage, build_state_from_tool_input,
)
from ui.i18n import t, get_lang


def _init_session_state():
    """Ініціалізація session_state для чату"""
    if "ai_messages" not in st.session_state:
        st.session_state["ai_messages"] = []
    if "ai_tool_input" not in st.session_state:
        st.session_state["ai_tool_input"] = None
    if "ai_total_input_tokens" not in st.session_state:
        st.session_state["ai_total_input_tokens"] = 0
    if "ai_total_output_tokens" not in st.session_state:
        st.session_state["ai_total_output_tokens"] = 0
    if "ai_mode" not in st.session_state:
        st.session_state["ai_mode"] = "quick"


def _reset_chat():
    """Очищає історію чату і зібрані дані"""
    st.session_state["ai_messages"] = []
    st.session_state["ai_tool_input"] = None
    st.session_state["ai_total_input_tokens"] = 0
    st.session_state["ai_total_output_tokens"] = 0
    # Режим розблоковується (можна обрати інший)
    st.session_state["ai_mode"] = "quick"


def _render_collected_params(tool_input: dict):
    """Показує зібрані AI параметри у sidebar"""
    st.markdown(f"### {t('ai_collected_params')}")
    
    # Object
    if "object_type" in tool_input:
        st.markdown(f"**{t('obj_type')}:** `{tool_input['object_type']}`")
    if "total_area_m2" in tool_input:
        st.markdown(f"**{t('obj_area')}:** {tool_input['total_area_m2']:,.0f} m²")
    if "floors_above" in tool_input or "floors_below" in tool_input:
        above = tool_input.get("floors_above", "?")
        below = tool_input.get("floors_below", 0)
        st.markdown(f"**{t('obj_floors')}:** {above} + {below}")
    
    # Структура об'єкта + зони (детальний режим)
    structure = tool_input.get("object_structure")
    if structure and structure != "single":
        st.markdown(f"**{t('obj_structure')}:** `{structure}`")
    zones = tool_input.get("zones") or []
    if zones:
        with st.expander(f"{t('obj_zones')} ({len(zones)})", expanded=True):
            for z in zones:
                name = z.get("name", "—")
                purpose = z.get("purpose", "")
                area = z.get("area_m2", 0)
                eng = []
                if z.get("smoke_dampers"): eng.append(f"димовид.×{z['smoke_dampers']}")
                if z.get("fire_dampers"): eng.append(f"вогнезах.клап.×{z['fire_dampers']}")
                if z.get("air_pressure_fans"): eng.append(f"підпір×{z['air_pressure_fans']}")
                if z.get("suppression_type", "none") != "none":
                    eng.append(f"пожежогас.({z['suppression_type']})")
                if z.get("fire_pumps"): eng.append(f"насоси×{z['fire_pumps']}")
                if z.get("elevators_fire_mode"): eng.append(f"ліфти×{z['elevators_fire_mode']}")
                if z.get("fire_doors_gates"): eng.append(f"ворота×{z['fire_doors_gates']}")
                if z.get("fire_hose_cabinets"): eng.append(f"ВПВ×{z['fire_hose_cabinets']}")
                eng_str = (", " + ", ".join(eng)) if eng else ""
                st.markdown(f"• **{name}** ({purpose}, {area:,.0f} м²{eng_str})")
    if tool_input.get("panel_hierarchy") == "hierarchical":
        st.markdown(f"**{t('obj_hierarchy')}:** {t('obj_hierarchy_yes')}")
    
    if "jurisdictions" in tool_input:
        st.markdown(
            f"**{t('obj_jurisdictions')}:** {', '.join(tool_input['jurisdictions'])}"
        )
    
    # Pre-object
    if "lifetime_horizon" in tool_input:
        st.markdown(f"**{t('obj_horizon')}:** `{tool_input['lifetime_horizon']}`")
    if "false_alarm_protection" in tool_input:
        st.markdown(
            f"**{t('obj_false_alarm')}:** `{tool_input['false_alarm_protection']}`"
        )
    
    # Comparison set
    if "comparison_set" in tool_input:
        st.markdown(
            f"**{t('comparison_set')}:** {', '.join(tool_input['comparison_set'])}"
        )
    
    # Maintenance
    if tool_input.get("calculate_maintenance", False):
        with st.expander(t("maintenance_section"), expanded=False):
            if "maintenance_distance_km" in tool_input:
                st.markdown(
                    f"**{t('mnt_distance')}:** {tool_input['maintenance_distance_km']} km"
                )
            mnt_items = []
            if tool_input.get("maintenance_has_extinguish"):
                mnt_items.append(t("mnt_has_extinguish"))
            if tool_input.get("maintenance_has_monitoring"):
                mnt_items.append(t("mnt_has_monitoring"))
            if tool_input.get("maintenance_has_smoke_vent"):
                mnt_items.append(t("mnt_has_smoke_vent"))
            if tool_input.get("maintenance_has_valves"):
                mnt_items.append(t("mnt_has_valves"))
            if tool_input.get("maintenance_has_engineering"):
                mnt_items.append(t("mnt_has_engineering"))
            if mnt_items:
                st.markdown(f"**{t('mnt_composition')}:** " + ", ".join(mnt_items))


def render_ai_tab(catalog):
    """Головна функція рендерингу вкладки AI"""
    _init_session_state()
    
    st.markdown(f"### {t('ai_header')}")
    st.caption(t("ai_caption"))
    
    # Повідомлення про успішний розрахунок (після rerun)
    if st.session_state.get("ai_just_calculated"):
        st.success(t("ai_calc_done"))
        st.session_state["ai_just_calculated"] = False
    
    # Перевірка ключа
    agent = AIAgent()
    if not agent.is_available():
        st.warning(t("ai_no_key_warning"))
        st.info(
            "Локально: створіть файл `.streamlit/secrets.toml` з рядком:\n"
            "```\nANTHROPIC_API_KEY = \"sk-ant-...\"\n```\n\n"
            "На Streamlit Cloud: налаштування → Secrets → додайте той самий рядок."
        )
        return
    
    # Перемикач режиму (можна змінити лише до початку діалогу)
    chat_started = bool(st.session_state["ai_messages"])
    mode_options = {
        "quick": t("ai_mode_quick"),
        "detailed": t("ai_mode_detailed"),
    }
    selected_label = st.radio(
        t("ai_mode_label"),
        options=list(mode_options.values()),
        index=0 if st.session_state["ai_mode"] == "quick" else 1,
        horizontal=True,
        disabled=chat_started,
        key="ai_mode_radio",
    )
    # Зворотний мапінг label → ключ
    st.session_state["ai_mode"] = next(
        k for k, v in mode_options.items() if v == selected_label
    )
    if chat_started:
        st.caption(t("ai_mode_locked"))
    else:
        st.caption(
            t("ai_mode_detailed_hint") if st.session_state["ai_mode"] == "detailed"
            else t("ai_mode_quick_hint")
        )
    
    # Колонки: чат | зібрані параметри
    col_chat, col_params = st.columns([2, 1])
    
    with col_params:
        # Зібрані параметри в правій колонці
        if st.session_state["ai_tool_input"]:
            _render_collected_params(st.session_state["ai_tool_input"])
        else:
            st.markdown(f"### {t('ai_collected_params')}")
            st.caption("...")
        
        # Токени і скидання
        st.markdown("---")
        tot_in = st.session_state["ai_total_input_tokens"]
        tot_out = st.session_state["ai_total_output_tokens"]
        if tot_in + tot_out > 0:
            cost_usd = (tot_in * 3.00 + tot_out * 15.00) / 1_000_000  # Sonnet 4.6 rates
            st.caption(
                f"{t('ai_token_usage')}: in={tot_in:,} | out={tot_out:,} | "
                f"≈ ${cost_usd:.4f}"
            )
        
        if st.button(t("ai_reset_btn"), use_container_width=True, key="ai_reset"):
            _reset_chat()
            st.rerun()
    
    with col_chat:
        # Початкове повідомлення якщо чат порожній
        if not st.session_state["ai_messages"]:
            with st.chat_message("assistant"):
                st.write(t("ai_initial_message_ua"))
        
        # Рендеримо історію
        for msg in st.session_state["ai_messages"]:
            with st.chat_message(msg.role):
                st.write(msg.content)
        
        # Якщо tool вже викликано — показуємо кнопку запуску
        if st.session_state["ai_tool_input"]:
            with st.chat_message("assistant"):
                st.success("✅ Я зібрав достатньо інформації. Готовий запустити розрахунок.")
                if st.button(
                    t("ai_run_calculation"),
                    type="primary",
                    use_container_width=True,
                    key="ai_run_calc",
                ):
                    _run_calculation_from_ai(catalog)
        
        # Input для нового повідомлення
        user_input = st.chat_input(t("ai_input_placeholder"))
        if user_input:
            _process_user_input(user_input, agent)
            st.rerun()


def _process_user_input(user_input: str, agent: AIAgent):
    """Обробка нового повідомлення користувача"""
    # Додаємо в історію
    st.session_state["ai_messages"].append(
        ChatMessage(role="user", content=user_input)
    )
    
    # Викликаємо API (без streaming у MVP — простіше і надійніше)
    with st.spinner(t("ai_thinking")):
        history_without_last = st.session_state["ai_messages"][:-1]
        result = agent.chat(
            history=history_without_last,
            new_user_message=user_input,
            mode=st.session_state.get("ai_mode", "quick"),
        )
    
    # Обробка помилки
    if result.error:
        st.session_state["ai_messages"].append(
            ChatMessage(
                role="assistant",
                content=f"⚠ {t('ai_error')}: {result.error}",
            )
        )
        return
    
    # Оновлюємо токен-статистику
    st.session_state["ai_total_input_tokens"] += result.usage_input_tokens
    st.session_state["ai_total_output_tokens"] += result.usage_output_tokens
    
    # Додаємо текст-відповідь AI у історію (якщо є)
    if result.text_response:
        st.session_state["ai_messages"].append(
            ChatMessage(role="assistant", content=result.text_response)
        )
    
    # Якщо AI викликав tool — зберігаємо параметри
    if result.tool_called and result.tool_input:
        st.session_state["ai_tool_input"] = result.tool_input


def _run_calculation_from_ai(catalog):
    """Виконує pipeline на основі зібраних AI параметрів"""
    from engine.pipeline import run_calculation
    from schemas.object_state import ObjectState
    
    tool_input = st.session_state["ai_tool_input"]
    
    try:
        state_dict, _ = build_state_from_tool_input(tool_input)
        state = ObjectState(**state_dict)
        
        with st.spinner(t("calculating_spinner")):
            result = run_calculation(state, catalog)
        
        st.session_state["last_result"] = result
        st.session_state["last_state"] = state
        # Очищуємо mode2 при новому розрахунку
        if "mode2_result" in st.session_state:
            del st.session_state["mode2_result"]
        
        # Зберігаємо об'єкт у список останніх (для sidebar), тримаємо останні 2
        _save_recent_object(state, tool_input)
        
        # Прапорець, щоб показати повідомлення про успіх після rerun
        st.session_state["ai_just_calculated"] = True
        
        # КРИТИЧНО: перезапускаємо скрипт, щоб вкладки Mode 1-4 відрендерилися
        # з реальними даними (включно з ТО по кожному виробнику).
        # Без rerun вкладки залишаться на стані «спочатку запустіть розрахунок».
        st.rerun()
    except Exception as e:
        st.error(f"{t('ai_error')}: {e}")


def _save_recent_object(state, tool_input):
    """
    Зберігає прорахований AI-об'єкт у session_state для показу в sidebar.
    Тримає останні 2 об'єкти (новіші витісняють старіші).
    """
    import streamlit as st
    
    # Формуємо людиночитну назву
    obj_type = tool_input.get("object_type", "object")
    area = tool_input.get("total_area_m2", 0)
    notes = tool_input.get("additional_notes", "")
    
    if notes:
        label = f"AI: {notes[:30]}"
    else:
        label = f"AI: {obj_type} {area:,.0f} м²"
    
    recent = st.session_state.get("recent_ai_objects", [])  # list of (label, state)
    
    # Уникаємо дублів за назвою
    recent = [(lbl, s) for (lbl, s) in recent if lbl != label]
    
    # Додаємо новий на початок
    recent.insert(0, (label, state))
    
    # Тримаємо останні 2
    recent = recent[:2]
    
    st.session_state["recent_ai_objects"] = recent
