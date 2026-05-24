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

# Default model для AI-агента.
# Sonnet 4.6 — краще дотримання інструкцій (instruction following) і tool use.
# Для економії можна повернути Haiku: "claude-haiku-4-5-20251001"
# (Haiku дешевший ~4×, але слабше тримає точні формулювання промпту).
DEFAULT_MODEL = "claude-sonnet-4-6"
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

# WHAT THE ENGINE CAN USE (collected via the active mode's flow below)
The calculation can use these inputs. HOW MANY of them you ask about depends ENTIRELY on
the active mode (quick vs detailed) described later — do NOT ask for all of them by default.

Object basics: object_type, total area m², floors (above + below).
Certification level: "UA" (Ukraine only, default), "UA+EU", "EU+" (leading EU bodies).
Pre-object criteria: lifetime_horizon (short/medium/long), false-alarm importance,
  financing constraints, mobile app, cloud monitoring.
Maintenance: distance from the OBJECT to the SERVICE ORGANIZATION (never "user's office";
  default 5 km), FAS composition (which subsystems are present).
Comparison set: which of the 4 manufacturers to compare (default: all).

KEY RULES regardless of mode:
- For false-alarm, if you ask, phrase it as importance: "Наскільки для вас важливим є
  показник імовірності хибних спрацювань? (важливо / не важливо)". Never say "sensitivity".
- For FAS composition: ASK what is present, never advise what the object NEEDS (that is the
  designer's job). Add: "Я лише рахую за вказаним складом, а не визначаю потрібний склад."
- For maintenance distance: it is OBJECT ↔ SERVICE ORGANIZATION, default 5 km if unknown.

# MANUFACTURER FACTS (use these EXACTLY — do not embellish)
- Cofem — Spanish manufacturer. Premium tier. Full EN 54 certification (AENOR),
  algorithmic detection, labyrinth detector housings. Niche presence in Ukraine.
  Do NOT say "popular in Ukraine" — its market share is small (~1-2%).
- Tiras — Ukrainian manufacturer. Market leader in Ukraine by project count. Wide
  product range. DSTU EN 54 certified. Basic-to-enhanced false-alarm protection.
- Omega — Ukrainian manufacturer (Project AO). NOT European. Basic tier. DSTU EN 54
  certified. Affordable.
- Varta — Ukrainian manufacturer (Elektronmash). NOT German, NOT premium. Basic tier.
  DSTU EN 54 certified.
Key honest framing: Tiras, Omega, Varta are Ukrainian (local production, lower cost,
fast service). Cofem is the only foreign (Spanish) option here — higher cost, but the
only one with full EU certification. Present this neutrally if asked.

# DEFAULTS YOU CAN USE
- If object_type ambiguous → mixed_use
- If floors_below not mentioned → 0
- If certification_requirement not specified → "UA"
- If lifetime_horizon unclear → "medium_7_10"
- If false_alarm unclear → "standard"
- If financing_constraints unclear → "not_sure"
- If maintenance distance not given or unknown → 5 km (this is normal at comparison stage)
- If maintenance composition not specified → just PS+SOUE
- If comparison_set not specified → all 4 manufacturers

# WHEN YOU HAVE ENOUGH DATA
Call the `submit_object_data` tool with all collected values.
If user wants to skip maintenance calculation entirely, set `calculate_maintenance: false`.
If user wants the engine to use defaults for some fields, just omit them — Python will fill defaults.

# IMPORTANT RULES
- NEVER make up values. If unsure, ASK.
- The distance question is about the OBJECT ↔ SERVICE ORGANIZATION distance, never the user's office. Never assume the user is the service provider.
- If user gives contradictory info, ask for clarification.
- After 8-12 exchanges, if you have enough data, submit. Don't drag the conversation.
- If user explicitly says "use defaults" or "all settings standard" — submit immediately with minimal info.

# PLAUSIBILITY CHECK (sanity validation — IMPORTANT)
A fire alarm system has an internal logic. If the user describes a configuration that is
technically implausible or self-contradictory, DO NOT silently compute it — point out the
inconsistency and ask the user to clarify. Examples of implausible configurations:
  • An addressable panel for hundreds of addresses but ZERO detectors — a fire alarm
    system without detectors makes no sense. Ask: "Адресний прилад на N адрес, але без
    жодного детектора виглядає нелогічно. Можливо, ви мали на увазі N адресних
    детекторів? Уточніть, будь ласка."
  • Engineering/relay components without any base detection system in the same zone.
  • A huge number of sounders but almost no detectors, or vice versa.
  • Note on terminology: when a user says "N engineering/relay components", these are
    usually valves, dampers, feedback-monitored systems, or fire-hose-cabinet buttons —
    they sit on SEPARATE fire-resistant loops, distinct from detector loops. They do NOT
    replace detectors. If detectors are missing entirely, flag it.
When in doubt about whether a configuration is sensible, ask a short clarifying question
BEFORE submitting. A good expert never computes nonsense silently.

# MANDATORY DISCLAIMER AT THE START
Your VERY FIRST message must include a brief note that this calculation does NOT include
the cost of installation and commissioning works (монтажні та пусконалагоджувальні роботи).
Keep it to one sentence, then proceed to ask about the object. Example (Ukrainian):
"Звертаю увагу: цей розрахунок порівнює вартість обладнання та обслуговування і НЕ
враховує вартість монтажних та пусконалагоджувальних робіт."

# EXAMPLES OF GOOD OPENING (Ukrainian)
"Привіт! Я допоможу підібрати оптимальну систему пожежної сигналізації для вашого об'єкта. Звертаю увагу: цей розрахунок НЕ враховує вартість монтажних та пусконалагоджувальних робіт. Розкажіть, який саме об'єкт ви плануєте обладнати — житловий комплекс, офіс, склад, торговий центр?"

# EXAMPLES OF GOOD OPENING (English)
"Hi! I'll help you choose the right fire alarm system for your object. Please note: this calculation does NOT include the cost of installation and commissioning works. What type of object are you equipping — residential complex, office, warehouse, shopping center?"
"""


# Блок інструкцій ДЕТАЛЬНОГО режиму — додається до промпту ТІЛЬКИ коли mode="detailed".
# У швидкому режимі цей блок НЕ надсилається, щоб AI не збирав зони.
DETAILED_MODE_INSTRUCTIONS = """

# ═══ ACTIVE MODE: DETAILED ANALYSIS ═══
The user chose DETAILED mode. Collect a ZONE-BY-ZONE breakdown using this three-level
flow. Always populate the zones array in submit_object_data.

LEVEL 1 — Object structure. Ask which of three types the object is:
  - single: one homogeneous building
  - homogeneous_complex: several buildings of the SAME purpose (e.g. warehouse complex).
    IMPORTANT: each physically separate building becomes its OWN zone, even if identical.
  - heterogeneous_complex: buildings of DIFFERENT purpose (e.g. hotel+restaurant+parking)
  Then collect the list of zones. For each zone: name, purpose, area_m2, floors, height.

LEVEL 2 — For each zone, determine fire-protection content:
  First apply the AUTOMATION FILTER (§4.0). Some zones usually need NO automation:
    • residential ≤ 26.5 m (≤ 9 floors)
    • industrial/warehouse of fire-hazard category D
    • standalone single-storey public building ≤ 200 m² (CC1)
  HYBRID approach: tell the client your conclusion and ask them to confirm. E.g.
  "За типом цієї зони протипожежна автоматика, як правило, не потрібна. Підтверджуєте?"
  Set requires_automation accordingly.
  If automation IS present, ask which engineering systems the zone has (this is the
  key expert question — ask which systems are PRESENT, do NOT advise what is needed):
    smoke_dampers (how many), air_pressure_fans, fire_dampers, suppression_type
    (water/gas/powder/aerosol), fire_pumps, elevators_fire_mode, fire_doors_gates,
    fire_hose_cabinets (ВПВ — how many cabinets).
  Reassure: "Я лише фіксую склад, а не визначаю, що потрібно — це робота проєктувальника."

LEVEL 3 — Panel hierarchy. Ask: one panel for the whole object (single) or a main
  panel with subordinate panels per zone (hierarchical)? Many zones / separate
  buildings usually imply hierarchical.

LEVEL 4 — Pre-object criteria (ask these in detailed mode):
  • Certification level: UA / UA+EU / EU+ (default UA unless foreign investor / EU insurance).
  • Lifetime horizon: short / medium / long (for TCO).
  • False-alarm importance: "Наскільки важливим є показник імовірності хибних
    спрацювань? (важливо / не важливо)" — важливо→premium, не важливо→standard.
  • Mobile app / cloud monitoring: yes / no / not_sure (only if relevant).

LEVEL 5 — Maintenance (ask in detailed mode):
  • Distance from OBJECT to SERVICE ORGANIZATION (default 5 km if unknown, frame gently).
  • FAS composition — ask what is present, never advise what is needed.

LEVEL 6 — Comparison set: which of the 4 manufacturers (default all).

When done, call submit_object_data with object_structure, the zones array (each zone
with its composition fields), panel_hierarchy, pre-object criteria, maintenance, and
comparison_set.
"""


# Блок інструкцій ШВИДКОГО режиму — додається ТІЛЬКИ коли mode="quick".
QUICK_MODE_INSTRUCTIONS = """

# ═══ ACTIVE MODE: QUICK ESTIMATE (must be genuinely FAST) ═══
The user chose QUICK mode. This must be a REALLY fast preliminary estimate.

STRICT LIMIT: ask AT MOST 3 clarifying questions, and only about the FAS CONFIGURATION
(the essentials needed to size the system). The three things worth asking are typically:
  1. Object type and approximate total area (m²).
  2. Number of floors (above + below ground).
  3. Whether there is fire-protection engineering (smoke vent / suppression / valves)
     beyond basic alarm+evacuation — a yes/no level, not a detailed breakdown.
You may combine these into fewer questions if the user already gave some.

For EVERYTHING ELSE (certification level, lifetime horizon, false-alarm importance,
financing, mobile app, cloud, maintenance distance, manufacturers) — DO NOT ASK.
Use AVERAGE / standard default values automatically:
  - certification_requirement = "UA"
  - lifetime_horizon = "medium_7_10"
  - false_alarm_protection = "standard"
  - financing_constraints = "not_sure"
  - comparison_set = all 4 manufacturers
  - maintenance distance = 5 km

After at most 3 questions, submit immediately. Do NOT ask for a zone-by-zone breakdown,
do NOT mention zones, structure variants, or panel hierarchy. Leave the zones array EMPTY.
Never say "це детальний аналіз" — you are in quick mode.

MANDATORY: in your message right before submitting, include ONE separate line stating that
this is a fast estimate using averaged values for non-specified criteria, e.g.:
"⚡ Це швидка оцінка: уточнено лише конфігурацію СПЗ, решта критеріїв узята за
усередненими (стандартними) значеннями. Для точного аналізу скористайтесь детальним режимом."
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
            "certification_requirement": {
                "type": "string",
                "enum": ["UA", "UA+EU", "EU+"],
                "default": "UA",
                "description": (
                    "Certification requirement level: 'UA' = Ukraine only, "
                    "'UA+EU' = Ukraine + EU, 'EU+' = EU leading centers (LPCB/VdS)"
                ),
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
                "description": (
                    "Distance (km) from the protected OBJECT to the SERVICE ORGANIZATION "
                    "that will perform maintenance. NOT the user's office. Default 5 if unknown."
                ),
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
            "maintenance_has_monitoring": {
                "type": "boolean",
                "default": False,
                "description": "Does FAS include 24/7 monitoring station service?",
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
            
            # ─── DETAILED MODE: object structure + zones ───
            "object_structure": {
                "type": "string",
                "enum": ["single", "homogeneous_complex", "heterogeneous_complex"],
                "default": "single",
                "description": (
                    "Object structure (detailed mode): 'single' = one homogeneous building, "
                    "'homogeneous_complex' = several buildings of the same type, "
                    "'heterogeneous_complex' = buildings of different purpose"
                ),
            },
            "zones": {
                "type": "array",
                "description": (
                    "DETAILED MODE ONLY. List of functional zones. Leave empty in quick mode. "
                    "Each zone is a separate part of different purpose/floors. For a homogeneous "
                    "complex, each physically separate building is its own zone."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Zone name, e.g. 'Hotel block'"},
                        "purpose": {
                            "type": "string",
                            "enum": [
                                "residential", "office", "hotel", "retail", "corridor",
                                "parking", "kitchen", "boiler", "server", "warehouse",
                                "industrial", "public", "technical", "other",
                            ],
                            "description": "Zone purpose — determines detector type",
                        },
                        "area_m2": {"type": "number", "minimum": 1},
                        "floors": {"type": "integer", "minimum": 1, "default": 1},
                        "height_m": {"type": "number", "description": "Height in m (for residential ≤26.5 rule)"},
                        "fire_hazard_category_d": {
                            "type": "boolean", "default": False,
                            "description": "True if industrial/warehouse of fire-hazard category D",
                        },
                        "requires_automation": {
                            "type": "boolean",
                            "description": (
                                "Whether this zone has fire automation. Per §4.0 rules some zones "
                                "don't need it (residential ≤9 floors, category D, CC1 ≤200m²). "
                                "Confirm with the client (hybrid approach)."
                            ),
                        },
                        "subdivision_type": {
                            "type": "string",
                            "enum": ["open", "subdivided", "corridor_only"],
                            "default": "subdivided",
                            "description": "open = parking/hall; subdivided = rooms; corridor_only",
                        },
                        # Composition — engineering systems (Level 2)
                        "smoke_dampers": {"type": "integer", "minimum": 0, "default": 0},
                        "air_pressure_fans": {"type": "integer", "minimum": 0, "default": 0},
                        "fire_dampers": {"type": "integer", "minimum": 0, "default": 0},
                        "suppression_type": {
                            "type": "string",
                            "enum": ["none", "water", "gas", "powder", "aerosol"],
                            "default": "none",
                        },
                        "fire_pumps": {"type": "integer", "minimum": 0, "default": 0},
                        "elevators_fire_mode": {"type": "integer", "minimum": 0, "default": 0},
                        "fire_doors_gates": {"type": "integer", "minimum": 0, "default": 0},
                        "fire_hose_cabinets": {"type": "integer", "minimum": 0, "default": 0},
                    },
                    "required": ["name", "purpose", "area_m2"],
                },
            },
            "panel_hierarchy": {
                "type": "string",
                "enum": ["single", "hierarchical"],
                "default": "single",
                "description": (
                    "Level 3: 'single' = one panel for whole object, "
                    "'hierarchical' = main panel + subordinate panels per zone"
                ),
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
        mode: str = "quick",
    ) -> ChatResult:
        """
        Один цикл діалогу: користувач каже щось, AI відповідає або викликає tool.
        
        Args:
            history: попередні повідомлення (без нового)
            new_user_message: нове повідомлення користувача
            mode: "quick" (швидка оцінка) або "detailed" (детальний аналіз із зонами)
        
        Returns:
            ChatResult з текстом відповіді або викликом tool
        """
        # Конвертуємо історію + нове повідомлення у формат Anthropic
        messages = [
            {"role": m.role, "content": m.content}
            for m in history
        ]
        messages.append({"role": "user", "content": new_user_message})
        
        # Підказка режиму додається до системного промпту
        if mode == "detailed":
            system_prompt = SYSTEM_PROMPT + DETAILED_MODE_INSTRUCTIONS
        else:
            system_prompt = SYSTEM_PROMPT + QUICK_MODE_INSTRUCTIONS
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=DEFAULT_MAX_TOKENS,
                system=system_prompt,
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
        CertificationRequirement, FalseAlarmRequirement, FunctionalZone,
        Jurisdiction, LifetimeHorizon, ObjectData, ObjectState, ObjectStructure,
        ObjectType, PreObjectAnswers, SubdivisionType, SuppressionType,
        TriState, ZoneComposition, ZonePurpose, automation_likely_not_required,
    )
    from engine.maintenance_calculator import MaintenanceParams, SystemComposition
    import uuid
    
    # ─── ObjectState ───
    object_type = ObjectType(tool_input["object_type"])
    
    # Сертифікаційний рівень (новий механізм). Маємо також похідні jurisdictions
    # для зворотної сумісності зі старим кодом.
    cert_req = CertificationRequirement(
        tool_input.get("certification_requirement", "UA")
    )
    _CERT_TO_JURIS = {
        CertificationRequirement.UA: [Jurisdiction.UA],
        CertificationRequirement.UA_EU: [Jurisdiction.UA, Jurisdiction.EU],
        CertificationRequirement.EU_PLUS: [Jurisdiction.EU],
    }
    
    pre_object = PreObjectAnswers(
        certification_requirement=cert_req,
        jurisdictions=_CERT_TO_JURIS[cert_req],
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
    
    # ─── Зони (детальний режим) ───
    zones_dict = {}
    zones_input = tool_input.get("zones", []) or []
    for idx, z in enumerate(zones_input):
        purpose = ZonePurpose(z.get("purpose", "other"))
        area = float(z["area_m2"])
        floors = int(z.get("floors", 1))
        height = z.get("height_m")
        cat_d = bool(z.get("fire_hazard_category_d", False))
        
        # Визначення потреби в автоматиці (§4.0, гібрид):
        # якщо AI явно вказав requires_automation — беремо його;
        # інакше застосовуємо правило-фільтр.
        if z.get("requires_automation") is not None:
            requires_auto = bool(z["requires_automation"])
        else:
            not_required, _ = automation_likely_not_required(
                purpose, area, floors, height, cat_d
            )
            requires_auto = not not_required
        
        # Склад систем (composition) — лише якщо автоматика потрібна
        composition = None
        if requires_auto:
            sup_raw = z.get("suppression_type", "none")
            composition = ZoneComposition(
                smoke_dampers=int(z.get("smoke_dampers", 0)),
                air_pressure_fans=int(z.get("air_pressure_fans", 0)),
                fire_dampers=int(z.get("fire_dampers", 0)),
                suppression_type=SuppressionType(sup_raw),
                fire_pumps=int(z.get("fire_pumps", 0)),
                elevators_fire_mode=int(z.get("elevators_fire_mode", 0)),
                fire_doors_gates=int(z.get("fire_doors_gates", 0)),
                fire_hose_cabinets=int(z.get("fire_hose_cabinets", 0)),
            )
        
        zone_key = z.get("name") or f"zone_{idx+1}"
        try:
            subdiv = SubdivisionType(z.get("subdivision_type", "subdivided"))
        except ValueError:
            subdiv = SubdivisionType.SUBDIVIDED
        
        zones_dict[zone_key] = FunctionalZone(
            area_m2=area,
            purpose=purpose,
            floors=floors,
            height_m=height,
            requires_automation=requires_auto,
            composition=composition,
            subdivision_type=subdiv,
        )
    
    object_data = ObjectData(
        object_type=object_type,
        object_structure=ObjectStructure(tool_input.get("object_structure", "single")),
        total_area_m2=float(tool_input["total_area_m2"]),
        floors_above=int(tool_input["floors_above"]),
        floors_below=int(tool_input.get("floors_below", 0)),
        zones=zones_dict,
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
            has_monitoring=tool_input.get("maintenance_has_monitoring", False),
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
