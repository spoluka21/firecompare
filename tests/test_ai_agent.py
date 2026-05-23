"""
Unit-тести для AI Agent без реальних API-викликів.
Перевіряють:
1. Парсинг tool_use відповіді
2. Конвертацію tool input → ObjectState
3. Обробку помилок
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.ai_agent import (
    AIAgent, ChatMessage, ChatResult, build_state_from_tool_input,
)


def test_tool_input_to_state_minimal():
    """Мінімальний tool input → валідний state"""
    tool_input = {
        "object_type": "residential_multi",
        "total_area_m2": 5000,
        "floors_above": 5,
    }
    state_dict, mnt = build_state_from_tool_input(tool_input)
    
    assert state_dict["object"]["object_type"] == "residential_multi"
    assert state_dict["object"]["total_area_m2"] == 5000.0
    assert state_dict["object"]["floors_above"] == 5
    assert state_dict["object"]["floors_below"] == 0  # default
    assert state_dict["pre_object"]["jurisdictions"] == ["UA"]  # default
    assert state_dict["comparison_set"] == ["cofem", "tiras", "omega", "varta"]
    assert mnt is not None  # calculate_maintenance default = True
    assert mnt["distance_km"] == 5  # default
    print("✓ test_tool_input_to_state_minimal")


def test_tool_input_to_state_full():
    """Повний tool input з усіма полями"""
    tool_input = {
        "object_type": "commercial_trc",
        "total_area_m2": 20000,
        "floors_above": 3,
        "floors_below": 2,
        "certification_requirement": "UA+EU",
        "lifetime_horizon": "long_15_20",
        "false_alarm_protection": "premium",
        "financing_constraints": "no",
        "mobile_app_required": "yes",
        "cloud_monitoring_required": "yes",
        "calculate_maintenance": True,
        "maintenance_distance_km": 20,
        "maintenance_has_extinguish": True,
        "maintenance_has_smoke_vent": True,
        "maintenance_has_valves": True,
        "maintenance_has_engineering": True,
        "maintenance_has_monitoring": True,
        "maintenance_n_damages_month": 0.8,
        "comparison_set": ["cofem"],  # тільки Cofem
        "additional_notes": "Premium TRC project",
        "language": "en",
    }
    state_dict, mnt = build_state_from_tool_input(tool_input)
    
    # certification_requirement UA+EU → jurisdictions [UA, EU]
    assert state_dict["pre_object"]["certification_requirement"] == "UA+EU"
    assert state_dict["pre_object"]["jurisdictions"] == ["UA", "EU"]
    assert state_dict["pre_object"]["lifetime_horizon"] == "long_15_20"
    assert state_dict["pre_object"]["false_alarm_protection"] == "premium"
    assert state_dict["comparison_set"] == ["cofem"]
    assert state_dict["object"]["floors_below"] == 2
    
    # Maintenance
    assert mnt["distance_km"] == 20
    assert mnt["composition"]["has_extinguish"] is True
    assert mnt["composition"]["has_smoke_vent"] is True
    assert mnt["composition"]["has_monitoring"] is True
    print("✓ test_tool_input_to_state_full")


def test_certification_levels():
    """Кожен рівень сертифікації → правильні похідні jurisdictions"""
    cases = [
        ("UA", ["UA"]),
        ("UA+EU", ["UA", "EU"]),
        ("EU+", ["EU"]),
    ]
    for cert_level, expected_juris in cases:
        tool_input = {
            "object_type": "warehouse",
            "total_area_m2": 5000,
            "floors_above": 1,
            "certification_requirement": cert_level,
        }
        state_dict, _ = build_state_from_tool_input(tool_input)
        assert state_dict["pre_object"]["certification_requirement"] == cert_level
        assert state_dict["pre_object"]["jurisdictions"] == expected_juris
    print("✓ test_certification_levels")


def test_detailed_mode_zones():
    """Детальний режим: масив зон → FunctionalZone dict з composition"""
    tool_input = {
        "object_type": "mixed_use",
        "object_structure": "heterogeneous_complex",
        "total_area_m2": 4000,
        "floors_above": 2,
        "panel_hierarchy": "hierarchical",
        "zones": [
            {"name": "Готель", "purpose": "hotel", "area_m2": 2500, "floors": 2,
             "elevators_fire_mode": 2, "fire_hose_cabinets": 4},
            {"name": "Кухня", "purpose": "kitchen", "area_m2": 300, "floors": 1,
             "subdivision_type": "open", "suppression_type": "powder"},
            {"name": "Паркінг", "purpose": "parking", "area_m2": 1200, "floors": 1,
             "subdivision_type": "open", "smoke_dampers": 3},
        ],
    }
    state_dict, _ = build_state_from_tool_input(tool_input)
    obj = state_dict["object"]
    assert obj["object_structure"] == "heterogeneous_complex"
    assert len(obj["zones"]) == 3
    # Кухня з пожежогасінням
    kitchen = obj["zones"]["Кухня"]
    assert kitchen["purpose"] == "kitchen"
    assert kitchen["composition"]["suppression_type"] == "powder"
    # Готель з ВПВ
    hotel = obj["zones"]["Готель"]
    assert hotel["composition"]["fire_hose_cabinets"] == 4
    print("✓ test_detailed_mode_zones")


def test_detailed_mode_automation_filter():
    """Детальний режим: житло ≤9 поверхів → автоматика не потрібна (авто)"""
    tool_input = {
        "object_type": "residential_multi",
        "total_area_m2": 6000,
        "floors_above": 9,
        "zones": [
            {"name": "Житло", "purpose": "residential", "area_m2": 6000, "floors": 9},
        ],
    }
    state_dict, _ = build_state_from_tool_input(tool_input)
    housing = state_dict["object"]["zones"]["Житло"]
    # Фільтр §4.0 має визначити, що автоматика не потрібна
    assert housing["requires_automation"] is False
    assert housing["composition"] is None
    print("✓ test_detailed_mode_automation_filter")


def test_tool_input_no_maintenance():
    """Якщо calculate_maintenance=False, mnt_dict = None"""
    tool_input = {
        "object_type": "warehouse",
        "total_area_m2": 8000,
        "floors_above": 1,
        "calculate_maintenance": False,
    }
    state_dict, mnt = build_state_from_tool_input(tool_input)
    
    assert mnt is None
    assert state_dict.get("maintenance_params") is None
    print("✓ test_tool_input_no_maintenance")


def test_chat_result_parsing_text_only():
    """Mock-відповідь з тільки текстом"""
    # Створюємо mock response з тільки text block
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "Розкажіть про вашу будівлю."
    
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.stop_reason = "end_turn"
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 20
    
    agent = AIAgent(api_key="test_key")
    
    with patch.object(agent, "_client") as mock_client:
        mock_client.messages.create.return_value = mock_response
        # forces use of mocked client
        agent._client = mock_client
        
        result = agent.chat(history=[], new_user_message="Hi")
    
    assert result.text_response == "Розкажіть про вашу будівлю."
    assert result.tool_called is False
    assert result.tool_input is None
    assert result.usage_input_tokens == 100
    print("✓ test_chat_result_parsing_text_only")


def test_chat_result_parsing_with_tool():
    """Mock-відповідь з tool_use блоком"""
    mock_text = MagicMock()
    mock_text.type = "text"
    mock_text.text = "Дякую! Запускаю розрахунок."
    
    mock_tool = MagicMock()
    mock_tool.type = "tool_use"
    mock_tool.name = "submit_object_data"
    mock_tool.input = {
        "object_type": "residential_multi",
        "total_area_m2": 3000,
        "floors_above": 4,
    }
    
    mock_response = MagicMock()
    mock_response.content = [mock_text, mock_tool]
    mock_response.stop_reason = "tool_use"
    mock_response.usage.input_tokens = 500
    mock_response.usage.output_tokens = 80
    
    agent = AIAgent(api_key="test_key")
    
    with patch.object(agent, "_client") as mock_client:
        mock_client.messages.create.return_value = mock_response
        agent._client = mock_client
        
        result = agent.chat(history=[], new_user_message="3000 m², 4 floors")
    
    assert result.tool_called is True
    assert result.tool_input["object_type"] == "residential_multi"
    assert result.tool_input["total_area_m2"] == 3000
    assert result.text_response == "Дякую! Запускаю розрахунок."
    print("✓ test_chat_result_parsing_with_tool")


def test_auth_error_handling():
    """Невірний ключ → відловлюємо AuthenticationError"""
    from anthropic import AuthenticationError
    
    agent = AIAgent(api_key="invalid_key")
    
    with patch.object(agent, "_client") as mock_client:
        mock_client.messages.create.side_effect = AuthenticationError(
            message="Invalid API key", response=MagicMock(), body=None,
        )
        agent._client = mock_client
        
        result = agent.chat(history=[], new_user_message="test")
    
    assert result.error is not None
    assert "API-ключ" in result.error
    assert result.text_response == ""
    print("✓ test_auth_error_handling")


def test_no_api_key():
    """Якщо немає ключа — is_available() = False"""
    # Очищаємо ENV ключ для тесту
    import os
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        agent = AIAgent(api_key=None)
        assert not agent.is_available()
    finally:
        if saved:
            os.environ["ANTHROPIC_API_KEY"] = saved
    print("✓ test_no_api_key")


if __name__ == "__main__":
    test_tool_input_to_state_minimal()
    test_tool_input_to_state_full()
    test_certification_levels()
    test_detailed_mode_zones()
    test_detailed_mode_automation_filter()
    test_tool_input_no_maintenance()
    test_chat_result_parsing_text_only()
    test_chat_result_parsing_with_tool()
    test_auth_error_handling()
    test_no_api_key()
    print("\nAll AI agent tests passed ✓")
