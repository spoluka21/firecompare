"""
ENGINE: AI Agent через Claude API

Збирає параметри об'єкта через природний діалог.
Використовує tool_use для структурованого виводу.

Архітектура:
1. UI передає історію повідомлень + новий ввід користувача
2. AIAgent.chat() викликає Claude API зі streaming
3. AI або задає уточнююче питання, або викликає tool submit_object_data
4. UI отримує або текст для показу, або зібрану схему ObjectState/MaintenanceParams
"""
import json
import os
from typing import Iterator, Optional

from anthropic import Anthropic, APIError, AuthenticationError
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# КОНФІГ
# ═══════════════════════════════════════════════════════════════════

# Default — Haiku 4.5 (cheap, fast). Можна змінити на Sonnet для продакшену.
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 1500


def get_api_key() -> Optional[str]:
    """
    Отримує API-ключ з:
    1. Streamlit secrets (для Cloud)
    2. ENV variable ANTHROPIC_API_KEY (для локального dev)
    """
    # Streamlit secrets
    try:
        import streamlit as st
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    
    # ENV
    return os.environ.get("ANTHROPIC_API_KEY")


# ═══════════════════════════════════════════════════════════════════
# СИСТЕМНИЙ ПРОМПТ (двомовний, з прикладами)
# ═══════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are FireCompare AI Assistant — an expert consultant for fire alarm system selection in Ukraine.

# YOUR ROLE
Help the user describe their object so the FireCompare engine can:
1. Compare fire alarm systems from 4 manufacturers (Cofem, Tiras, Omega, Varta)
2. Optionally calculate monthly maintenance costs for each

# CONVERSATIONAL STYLE
- Match the user's language: Ukrainian, Russian, or English. Default to Ukrainian.
- Be concise. One question at a time. Don't dump all questions at once.
- Use plain language. Avoid jargon unless the user clearly understands it.
- If user is uncertain, suggest a reasonable default and confirm.
- Acknowledge what user just said before asking the next question.

# WHAT TO COLLECT (in this order)

## Phase 1: Object basics (REQUIRED)
1. Object type (residential, commercial, mixed-use, etc.)
2. Total protected area in m²
3. Number of floors (above + below ground)
4. Jurisdictions (UA standard; UK/EU/US if foreign investor or insurance)

## Phase 2: Pre-object criteria (REQUIRED)
5. Lifetime horizon: short (3-5y) / medium (7-10y) / long (15-20y) — for TCO calculation
6. False alarm sensitivity: standard or premium — premium reduces nuisance alarms
7. Budget constraints: yes / no — does cost matter strongly?
8. Mobile app required: yes / no / not_sure — for remote management
9. Cloud monitoring required: yes / no / not_sure

## Phase 3: Maintenance parameters (OPTIONAL but recommended)
10. Distance from your office to object (km)
11. FAS composition: just PS+SOUE? + fire extinguishing? + smoke vent? + valves?
12. Monitoring subcontracted? If yes, what's the monthly cost?

## Phase 4: Comparison set
13. Which manufacturers to compare? (default: all 4 — Cofem, Tiras, Omega, Varta)

# DEFAULTS YOU CAN USE
- If object_type ambiguous → mixed_use
- If floors_below not mentioned → 0
- If jurisdictions not specified → ["UA"] only
- If lifetime_horizon unclear → "medium_7_10"
- If false_alarm unclear → "standard"
- If financing_constraints unclear → "not_sure"
- If maintenance distance not given → 5 km
- If maintenance composition not specified → just PS+SOUE
- If comparison_set not specified → all 4 manufacturers

# WHEN YOU HAVE ENOUGH DATA
Call the `submit_object_data` tool with all collected values.
If user wants to skip maintenance calculation entirely, set `calculate_maintenance: false`.
If user wants the engine to use defaults for some fields, just omit them — Python will fill defaults.

# IMPORTANT RULES
- NEVER make up values. If unsure, ASK.
- If user gives contradictory info, ask for clarification.
- After 8-12 exchanges, if you have enough data, submit. Don't drag the conversation.
- If user explicitly says "use defaults" or "all settings standard" — submit immediately with minimal info.

# EXAMPLES OF GOOD OPENING (Ukrainian)
"Привіт! Я допоможу підібрати оптимальну систему пожежної сигналізації для вашого об'єкта. Розкажіть, який саме об'єкт ви плануєте обладнати — житловий комплекс, офіс, склад, торговий центр?"

# EXAMPLES OF GOOD OPENING (English)
"Hi! I'll help you choose the right fire alarm system for your object. What type of object are you equipping — residential complex, office, warehouse, shopping center?"
"""


# ═══════════════════════════════════════════════════════════════════
# ОПИС ТУЛУ (function calling)
# ═══════════════════════════════════════════════════════════════════

SUBMIT_TOOL = {
    "name": "submit_object_data",
    "description": (
        "Submit collected object data to FireCompare engine. Call this when you have "
        "gathered enough information from the user to run the calculation. "
        "Required fields must be set; optional fields can be omitted to use defaults."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            # ─── PHASE 1: Object basics ───
            "object_type": {
                "type": "string",
                "enum": [
                    "residential_multi", "residential_mixed", "public",
                    "administrative", "commercial_trc", "industrial",
                    "warehouse", "specialized", "mixed_use",
                ],
                "description": "Type of object",
            },
            "total_area_m2": {
                "type": "number",
                "minimum": 10,
                "description": "Total protected area in square meters",
            },
            "floors_above": {
                "type": "integer",
                "minimum": 1,
                "description": "Number of floors above ground",
            },
            "floors_below": {
                "type": "integer",
                "minimum": 0,
                "default": 0,
                "description": "Number of floors below ground (basement/parking)",
            },
            "jurisdictions": {
                "type": "array",
                "items": {"type": "string", "enum": ["UA", "UK", "EU", "US"]},
                "default": ["UA"],
                "description": "Active regulatory jurisdictions",
            },
            
            # ─── PHASE 2: Pre-object criteria ───
            "lifetime_horizon": {
                "type": "string",
                "enum": ["short_3_5", "medium_7_10", "long_15_20"],
                "default": "medium_7_10",
                "description": "Expected system lifetime for TCO calculation",
            },
            "false_alarm_protection": {
                "type": "string",
                "enum": ["standard", "premium"],
                "default": "standard",
                "description": "Required false alarm protection level",
            },
            "financing_constraints": {
                "type": "string",
                "enum": ["yes", "no", "not_sure"],
                "default": "not_sure",
                "description": "Are there strong budget constraints?",
            },
            "mobile_app_required": {
                "type": "string",
                "enum": ["yes", "no", "not_sure", "nice_to_have"],
                "default": "not_sure",
            },
            "cloud_monitoring_required": {
                "type": "string",
                "enum": ["yes", "no", "not_sure", "nice_to_have"],
                "default": "not_sure",
            },
            
            # ─── PHASE 3: Maintenance ───
            "calculate_maintenance": {
                "type": "boolean",
                "default": True,
                "description": "Whether to calculate maintenance costs",
            },
            "maintenance_distance_km": {
                "type": "number",
                "minimum": 0,
                "default": 5,
                "description": "Distance from service office to object",
            },
            "maintenance_has_extinguish": {
                "type": "boolean",
                "default": False,
                "description": "Does FAS include fire extinguishing system?",
            },
            "maintenance_has_smoke_vent": {
                "type": "boolean",
                "default": False,
                "description": "Does FAS include smoke ventilation control?",
            },
            "maintenance_has_valves": {
                "type": "boolean",
                "default": False,
                "description": "Does FAS control fire valves?",
            },
            "maintenance_has_engineering": {
                "type": "boolean",
                "default": False,
                "description": "Does FAS interface with elevators, gates, curtains?",
            },
            "maintenance_subcontract_monitoring": {
                "type": "boolean",
                "default": False,
                "description": "Is monitoring service subcontracted?",
            },
            "maintenance_subcontract_cost_uah": {
                "type": "number",
                "minimum": 0,
                "default": 0,
                "description": "Monthly cost of subcontracted monitoring (UAH)",
            },
            "maintenance_n_damages_month": {
                "type": "number",
                "minimum": 0,
                "default": 0.5,
                "description": "Projected damages per month",
            },
            
            # ─── PHASE 4: Comparison set ───
            "comparison_set": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["cofem", "tiras", "omega", "varta"],
                },
                "default": ["cofem", "tiras", "omega", "varta"],
                "description": "Manufacturers to compare",
            },
            
            # ─── METADATA ───
            "additional_notes": {
                "type": "string",
                "description": "Any user-provided context or special requirements (free text)",
            },
            "language": {
                "type": "string",
                "enum": ["ua", "en", "ru"],
                "default": "ua",
                "description": "Detected language of the conversation",
            },
        },
        "required": [
            "object_type", "total_area_m2", "floors_above",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════
# ОБГОРТКА КЛІЄНТА
# ═══════════════════════════════════════════════════════════════════


class ChatMessage(BaseModel):
    """Одне повідомлення в історії діалогу"""
    role: str  # "user" or "assistant"
    content: str


class ChatResult(BaseModel):
    """Результат одного циклу chat()"""
    # Текстова відповідь AI (для показу користувачу)
    text_response: str = ""
    
    # Tool call (якщо AI вирішив, що зібрав достатньо даних)
    tool_called: bool = False
    tool_input: Optional[dict] = None
    
    # Метадані
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0
    stop_reason: str = ""
    error: Optional[str] = None


class AIAgent:
    """Обгортка над Anthropic API з tool use підтримкою"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or get_api_key()
        self.model = model
        self._client: Optional[Anthropic] = None
    
    @property
    def client(self) -> Anthropic:
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "API-ключ не знайдено. Налаштуйте ANTHROPIC_API_KEY у "
                    "Streamlit secrets або environment variable."
                )
            self._client = Anthropic(api_key=self.api_key)
        return self._client
    
    def is_available(self) -> bool:
        """Перевірка чи доступний AI (є ключ)"""
        return bool(self.api_key)
    
    def chat(
        self,
        history: list[ChatMessage],
        new_user_message: str,
    ) -> ChatResult:
        """
        Один цикл діалогу: користувач каже щось, AI відповідає або викликає tool.
        
        Args:
            history: попередні повідомлення (без нового)
            new_user_message: нове повідомлення користувача
        
        Returns:
            ChatResult з текстом відповіді або викликом tool
        """
        # Конвертуємо історію + нове повідомлення у формат Anthropic
        messages = [
            {"role": m.role, "content": m.content}
            for m in history
        ]
        messages.append({"role": "user", "content": new_user_message})
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=DEFAULT_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=[SUBMIT_TOOL],
                messages=messages,
            )
        except AuthenticationError as e:
            return ChatResult(
                error=f"Невірний API-ключ. Перевірте налаштування. Деталі: {e}"
            )
        except APIError as e:
            return ChatResult(error=f"Помилка API: {e}")
        except Exception as e:
            return ChatResult(error=f"Неочікувана помилка: {e}")
        
        result = ChatResult(
            stop_reason=response.stop_reason or "",
            usage_input_tokens=response.usage.input_tokens,
            usage_output_tokens=response.usage.output_tokens,
        )
        
        # Парсимо content blocks — там може бути text і/або tool_use
        for block in response.content:
            if block.type == "text":
                result.text_response += block.text
            elif block.type == "tool_use":
                if block.name == "submit_object_data":
                    result.tool_called = True
                    result.tool_input = block.input
        
        return result


# ═══════════════════════════════════════════════════════════════════
# КОНВЕРТАЦІЯ TOOL INPUT → ObjectState + MaintenanceParams
# ═══════════════════════════════════════════════════════════════════


def build_state_from_tool_input(
    tool_input: dict,
) -> tuple[dict, Optional[dict]]:
    """
    Конвертує input від tool_use AI у формат, що приймає run_calculation():
    ObjectState (як dict) + опційно MaintenanceParams (як dict).
    
    Цей крок ВАЛІДУЄ дані через Pydantic — якщо щось не так, виключення.
    
    Returns:
        (object_state_dict, maintenance_params_dict_or_none)
    """
    from schemas.object_state import (
        FalseAlarmRequirement, Jurisdiction, LifetimeHorizon, ObjectData,
        ObjectState, ObjectType, PreObjectAnswers, TriState,
    )
    from engine.maintenance_calculator import MaintenanceParams, SystemComposition
    import uuid
    
    # ─── ObjectState ───
    object_type = ObjectType(tool_input["object_type"])
    
    pre_object = PreObjectAnswers(
        jurisdictions=[
            Jurisdiction(j) for j in tool_input.get("jurisdictions", ["UA"])
        ],
        lifetime_horizon=LifetimeHorizon(
            tool_input.get("lifetime_horizon", "medium_7_10")
        ),
        false_alarm_protection=FalseAlarmRequirement(
            tool_input.get("false_alarm_protection", "standard")
        ),
        financing_constraints=TriState(
            tool_input.get("financing_constraints", "not_sure")
        ),
        mobile_app_required=TriState(
            tool_input.get("mobile_app_required", "not_sure")
        ),
        cloud_monitoring_required=TriState(
            tool_input.get("cloud_monitoring_required", "not_sure")
        ),
    )
    
    object_data = ObjectData(
        object_type=object_type,
        total_area_m2=float(tool_input["total_area_m2"]),
        floors_above=int(tool_input["floors_above"]),
        floors_below=int(tool_input.get("floors_below", 0)),
        additional_notes=tool_input.get("additional_notes", ""),
    )
    
    state = ObjectState(
        session_id=f"ai_agent_{uuid.uuid4().hex[:8]}",
        language=tool_input.get("language", "ua"),
        pre_object=pre_object,
        comparison_set=tool_input.get(
            "comparison_set", ["cofem", "tiras", "omega", "varta"]
        ),
        object=object_data,
    )
    
    # ─── Maintenance (опційно) ───
    maintenance_params_dict = None
    if tool_input.get("calculate_maintenance", True):
        composition = SystemComposition(
            has_extinguish=tool_input.get("maintenance_has_extinguish", False),
            has_smoke_vent=tool_input.get("maintenance_has_smoke_vent", False),
            has_valves=tool_input.get("maintenance_has_valves", False),
            has_engineering_systems=tool_input.get(
                "maintenance_has_engineering", False
            ),
            has_monitoring_subcontract=tool_input.get(
                "maintenance_subcontract_monitoring", False
            ),
            subcontract_monitoring_uah=float(
                tool_input.get("maintenance_subcontract_cost_uah", 0)
            ),
        )
        
        mnt_params = MaintenanceParams(
            object_area_m2=object_data.total_area_m2,
            composition=composition,
            distance_km=float(tool_input.get("maintenance_distance_km", 5)),
            n_damages_month=float(tool_input.get("maintenance_n_damages_month", 0.5)),
        )
        
        maintenance_params_dict = mnt_params.model_dump()
        state.maintenance_params = maintenance_params_dict
    
    return state.model_dump(), maintenance_params_dict
