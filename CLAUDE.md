# ExamsOnline — Project Overview

Django-based online exam system (MVP) for Synergy.

## Tech Stack

- **Backend:** Django 5.2, Python 3.13
- **Server:** Uvicorn (ASGI)
- **DB:** PostgreSQL (via env vars) / SQLite (dev)
- **Package manager:** uv
- **Excel:** pandas + openpyxl

## Directory Structure

```
ExamsOnline/
├── exam_system/              # Django config package
│   ├── settings.py           # Main settings (SECRET_KEY hardcoded, DEBUG=True)
│   ├── urls.py               # Root URLconf: /admin/ + include(exams.urls)
│   ├── wsgi.py / asgi.py
├── exams/                    # Main (only) app
│   ├── models.py             # 11 models
│   ├── views.py              # All views: auth, exam flow, results, Excel import
│   ├── urls.py               # All URL patterns
│   ├── admin.py              # Full Django admin with inlines
│   ├── migrations/           # 0001_initial only
│   └── management/           # Custom management commands
├── templates/
│   ├── base.html
│   └── exams/
│       ├── student_login.html
│       ├── exam_list.html
│       ├── take_exam.html
│       ├── exam_result_detail.html
│       ├── exam_results_list.html
│       ├── import_students.html
│       └── no_attempts.html
├── static/images/            # logo.png, logo2.png, logo4.png, backgrounds
├── backup/v1, v2/            # Old versions (ignore)
├── pyproject.toml
├── manage.py
├── .env / .env.example       # DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
└── .venv/                    # Virtual env (uv)
```

## Models (11 total)

| Model | Description |
|---|---|
| `Student` | Custom user, login by `student_id` (no Django User) |
| `Course` | Учебный курс |
| `CourseStudent` | M2M: курс ↔ студент |
| `Subject` | Предмет (belongs to Course) |
| `Question` | Вопрос: типы single/multiple/open/text, сложность easy/medium/hard, Markdown |
| `Answer` | Вариант ответа, `is_correct` flag |
| `Exam` | Экзамен: open_time/close_time, duration_minutes, attempts_allowed |
| `ExamSubject` | M2M: экзамен ↔ предмет + кол-во вопросов и баллов по сложности |
| `ExamResult` | Результат попытки: in_progress / finished / time_expired |
| `StudentAnswer` | Ответ студента на вопрос (selected_answers M2M + answer_text) |
| `StudentImport` | Лог импорта Excel |

## URL Patterns

```
/                              → student_login
/logout/                       → student_logout
/exams/                        → exam_list
/exams/start/<id>/             → start_exam
/exams/take/<id>/              → take_exam
/exams/answer/<id>/            → save_answer  (AJAX POST)
/exams/finish/<id>/            → finish_exam  (AJAX POST)
/exams/results/                → exam_results_list
/exams/results/<id>/           → exam_result_detail
/admin/import-students/        → import_students_view  (staff only)
/admin/export-template/        → export_students_template
/admin/                        → Django admin
```

## Key Flows

1. Студент логинится по `student_id` → сессия 8 часов
2. Видит экзамены своих курсов (по `CourseStudent`) с аннотацией попыток
3. `start_exam` → случайная выборка вопросов через `get_random_questions()` → создаёт `StudentAnswer` на каждый вопрос
4. Ответы сохраняются AJAX (`save_answer`), автопроверка choice-вопросов через `check_answer_correctness()`
5. `finalize_exam`: `score = Sum(points_earned)`, `max_score` из `ExamSubject.max_score()`
6. Импорт студентов из Excel через pandas (`@staff_member_required`)

## Running the Project

```bash
# Активация venv
source .venv/bin/activate

# Применить миграции
python manage.py migrate

# Запуск сервера
python manage.py runserver
# или через uvicorn:
uvicorn exam_system.asgi:application --reload
```

## Environment Variables (.env)

```
DB_NAME=exam_system
DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
```

## Known Issues

- `SECRET_KEY` захардкожен в `settings.py` — вынести в `.env`
- Тесты отсутствуют (`tests.py` пустой)
- Нет REST API
- Два файла БД в корне (`db.sqlite3`, `db.sqlite3.db`) — dev артефакты
