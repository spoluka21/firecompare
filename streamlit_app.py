"""
FireCompare — точка входу для Streamlit Cloud

Streamlit Cloud шукає `streamlit_app.py` у корені репозиторію за замовчуванням.
Цей файл — обгортка, яка делегує виконання у ui/app.py.
"""
import sys
from pathlib import Path

# Додаємо корінь проекту в sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Виконуємо UI-додаток
ui_app_path = PROJECT_ROOT / "ui" / "app.py"
with open(ui_app_path, encoding="utf-8") as f:
    exec(compile(f.read(), str(ui_app_path), "exec"))
