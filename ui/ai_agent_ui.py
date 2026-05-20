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


def _reset_chat():
    """Очищає історію чату і зібрані дані"""
    st.session_state["ai_messages"] = []
    st.session_state["ai_tool_input"] = None
    st.session_state["ai_total_input_tokens"] = 0
    st.session_state["ai_total_output_tokens"] = 0


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
            if tool_input.get("maintenance_has_smoke_vent"):
                mnt_items.append(t("mnt_has_smoke_vent"))
            if tool_input.get("maintenance_has_valves"):
                mnt_items.append(t("mnt_has_valves"))
            if tool_input.get("maintenance_has_engineering"):
                mnt_items.append(t("mnt_has_engineering"))
            if mnt_items:
                st.markdown(f"**{t('mnt_composition')}:** " + ", ".join(mnt_items))
            if tool_input.get("maintenance_subcontract_monitoring"):
                st.markdown(
                    f"**{t('mnt_has_monitoring_subcontract')}:** "
                    f"{tool_input.get('maintenance_subcontract_cost_uah', 0):,.0f} ₴/міс"
                )


def render_ai_tab(catalog):
    """Головна функція рендерингу вкладки AI"""
    _init_session_state()
    
    st.markdown(f"### {t('ai_header')}")
    st.caption(t("ai_caption"))
    
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
            cost_usd = (tot_in * 0.80 + tot_out * 4.00) / 1_000_000  # Haiku 4.5 rates
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
        
        st.success(t("ai_calc_done"))
        st.balloons()
    except Exception as e:
        st.error(f"{t('ai_error')}: {e}")
