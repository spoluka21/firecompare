# FireCompare

Веб-додаток для об'єктивного порівняння систем пожежної сигналізації.
Розроблено для інтеграції в платформу інтернет-магазину Cofem Ukraine.

## Стек

- **Backend:** Python 3.10+ (Pydantic, python-docx)
- **Frontend:** Streamlit
- **DOCX-експорт:** python-docx (без зовнішніх залежностей)

## Структура проекту

```
firecompare/
├── streamlit_app.py            ← точка входу для Streamlit Cloud
├── requirements.txt            ← Python-залежності
├── .streamlit/config.toml      ← тема UI
├── schemas/                    ← Pydantic-моделі
├── catalog/                    ← реальні дані виробників
├── engine/                     ← логіка движка (Steps 1-4, Modes 1-3)
├── ui/app.py                   ← Streamlit UI
└── tests/fixtures/             ← референсні об'єкти (Замкова)
```

## Локальний запуск

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Відкриється у браузері на `http://localhost:8501`.

## Розгортання на Streamlit Community Cloud

### Передумови

- Акаунт на GitHub
- Акаунт на [share.streamlit.io](https://share.streamlit.io/) (можна увійти через GitHub)

### Покроково

**1. Створюємо репозиторій на GitHub**

   - Заходимо на github.com → New repository
   - Назва: `firecompare` (або інша)
   - Видимість: **Private** (рекомендую, бо це робочий код)
   - Не додавай README, .gitignore — вони вже є в проекті
   - Натискаємо Create repository

**2. Завантажуємо код у репозиторій**

   Через веб-інтерфейс (без терміналу):
   - На сторінці пустого репозиторію клік "uploading an existing file"
   - Перетягни ВСІ файли і папки з розпакованого `firecompare/` у вікно браузера
   - Comment: "Initial commit — FireCompare MVP"
   - Commit changes

   Або через `git` (якщо встановлено):
   ```bash
   cd firecompare/
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/USERNAME/firecompare.git
   git push -u origin main
   ```

**3. Розгортаємо на Streamlit Cloud**

   - Заходимо на [share.streamlit.io](https://share.streamlit.io/)
   - Sign in with GitHub
   - Дозволяємо доступ до приватних репозиторіїв (якщо обрано Private)
   - Натискаємо **"New app"** → **"Deploy a public app from GitHub"**
   - Repository: `USERNAME/firecompare`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: вибираємо власну адресу, наприклад `firecompare-cofem`
   - Натискаємо **Deploy**

**4. Чекаємо**

   Streamlit Cloud встановить залежності з `requirements.txt`, запустить додаток.
   Зазвичай 2-3 хвилини. Потім отримуєш URL виду:
   
   `https://firecompare-cofem.streamlit.app/`

   Цей URL працює з будь-якого пристрою — комп'ютера, планшета, телефона.

### Безпека приватних додатків

Якщо репозиторій приватний, Streamlit Cloud додасть на сторінку логін через GitHub.
Тільки ти і ті, кому ти даси доступ до репозиторію, зможуть відкрити додаток.

Для **публічного демо** керівництву Cofem можна:
- Залишити репозиторій приватним
- На демо показати додаток зі свого облікового запису (зайти в браузер заздалегідь)
- Або тимчасово зробити репозиторій публічним (тоді URL працює без логіну)

## Демо-сценарії в UI

| Сценарій | Очікуваний результат |
|---|---|
| **Замкова II черга (NPA: 3 ППКП)** | Cofem на 1 місці (overall 86.4) |
| **Замкова Преміум (UA+UK)** | UA-бренди виключені compliance-фільтром, Cofem єдиний у comparison-set |
| **Замкова Простий (1 ППКП)** | Демонстрація обмежень спрощеної моделі: Омега виключається через loop overflow |

## Версіонування

- **v0.1** — каталог + Pydantic-схеми
- **v0.2** — повний 5-шаровий scoring + NPA + Modes 1/2/3 + Streamlit UI (поточна)
- **v0.3** (план) — AI-агент через Claude API, інтеграція в e-shop Cofem
