# Архитектура проекта SynergyOnlineTest

Django-система для проведения онлайн-экзаменов (MVP). Backend на Django 5.2 / Python 3.13, зависимости управляются через `uv`, запуск через Uvicorn (ASGI). БД: PostgreSQL.

## Стек

- **Django** 5.2.6+ — веб-фреймворк
- **PostgreSQL** — основная БД (`psycopg2-binary`)
- **Uvicorn** — ASGI-сервер для продакшена
- **pandas / openpyxl** — импорт/экспорт студентов и результатов через Excel
- **locust** (dev) — нагрузочное тестирование

## Структура каталогов

```
SynergyOnlineTest/
├── exam_system/            # Django-проект (настройки, корневые urls)
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py / wsgi.py
│
├── exams/                  # Основное приложение: студенты, экзамены, вопросы
│   ├── models.py           # Все основные модели (см. DATABASE.md)
│   ├── views.py            # Студенческий флоу + импорт студентов
│   ├── urls.py
│   ├── admin.py            # Django admin для всех моделей exams
│   ├── utils.py            # compute_result_stats — статистика по предметам/сложности
│   ├── tests.py            # неиспользуемая заглушка Django (реальные тесты — в /tests)
│   ├── management/commands/
│   │   ├── create_test_data.py        # УСТАРЕВШАЯ/сломанная команда (см. ниже)
│   │   ├── create_load_test_data.py   # актуальная генерация тестовых данных
│   │   ├── import_from_sqlite.py      # миграция SQLite → PostgreSQL
│   │   └── import_questions.py        # импорт банка вопросов из JSON
│   └── migrations/         # 0001–0005
│
├── teachers/                # Приложение преподавателя (поверх Django auth)
│   ├── models.py            # Teacher (OneToOne → User), QuestionKeyword
│   ├── views.py             # логин, дашборд, проверка открытых ответов, экспорт Excel
│   ├── urls.py
│   ├── admin.py
│   └── migrations/          # 0001
│
├── templates/
│   ├── base.html
│   ├── exams/                # student_login, exam_list, take_exam, exam_result(s)...
│   └── teachers/              # login, dashboard, review
│
├── static/images/            # логотипы, фоновые изображения
│
├── docs/
│   ├── test/                 # банки вопросов (JSON) — matematika_9_class, informatika_test_9_class
│   ├── ARCHITECTURE.md        # этот файл
│   └── DATABASE.md            # структура БД
│
├── tests/                    # реальные тесты проекта (вне приложений)
│   ├── test_shuffle.py
│   ├── test_keywords.py
│   ├── test_teacher_views.py
│   ├── test_result_detail.py
│   └── locustfile.py          # нагрузочное тестирование (Locust)
│
├── manage.py
├── main.py
├── pyproject.toml / uv.lock
└── .env.example
```

## Приложения

### `exams` — студенческий флоу

Сессионная аутентификация без Django `User`: студент вводит `student_id`, ID кладётся в сессию (`student_id`, 8 часов, `SESSION_COOKIE_AGE=28800`). Декоратор `@student_required` в `views.py` подтягивает `request.student`.

Основной путь:
1. `student_login` — вход по `student_id`
2. `exam_list` — список доступных экзаменов студента (по курсам через `CourseStudent`), с подсчётом попыток и статусом (upcoming/open/closed)
3. `start_exam` — проверка окна экзамена/попыток/доступа к курсу → случайный подбор вопросов через `get_random_questions()` (по `ExamSubject`: easy/medium(closed/open)/hard) → атомарное создание `ExamResult` + `StudentAnswer` (по одному на вопрос) + `AnswerOrder` (стабильный shuffle вариантов ответа на попытку)
4. `take_exam` — страница прохождения, вопросы восстанавливаются в сохранённом порядке
5. `save_answer` (AJAX, `@csrf_exempt` + `@require_POST`) — автосохранение ответа, авто-проверка через `check_answer_correctness()`:
   - closed-вопросы (single/multiple choice): точное совпадение множества выбранных ID с множеством `is_correct=True`
   - open/text-вопросы: поиск ключевых слов (`teachers.QuestionKeyword`, с учётом `case_sensitive`)
6. `finish_exam` → `finalize_exam()` — фиксирует `end_time`, суммирует `points_earned`, считает `max_score` по всем `ExamSubject` экзамена
7. `exam_result_detail` — детальный отчёт (статистика по предметам и по сложности через `exams/utils.py::compute_result_stats`)

Административные функции (не через `/admin/`, но защищены `@staff_member_required`/`@login_required`):
- `import_students_view` / `process_excel_import` — импорт студентов из Excel (pandas), лог в `StudentImport`
- `export_students_template` — генерация шаблона Excel для импорта

### `teachers` — портал преподавателя

`Teacher` — `OneToOne` к стандартному Django `User` (использует `is_staff` для входа, а не отдельную систему прав).

- `teacher_login` — обычный Django `authenticate()`, требует `is_staff`
- `teacher_dashboard` — список всех завершённых `ExamResult` (сортировка: дата/студент/экзамен/балл/непроверенные), аннотация `pending_count` (открытые вопросы без `is_correct`)
- `export_results_excel` — форматированный экспорт в Excel (openpyxl: заливка по проценту выполнения, чередование строк, замороженная шапка)
- `teacher_review` — ручная проверка открытых/текстовых ответов: `teacher_score` (override), `teacher_comment`, `reviewed_by`/`reviewed_at` → `ExamResult.recalculate_score()` (сумма `effective_points`, где `effective_points` = `teacher_score` если задан, иначе `points_earned`)
- `teacher_result_detail` — переиспользует шаблон `exams/exam_result_detail.html` с флагом `is_teacher_view`

## Маршрутизация (`exam_system/urls.py`)

| Префикс | Приложение |
|---|---|
| `/` | `exams.urls` (студенческий флоу + импорт студентов) |
| `/teacher/` | `teachers.urls` |
| `/admin/` | Django admin (плюс кастомный `admin/import-students/` через `StudentAdmin.get_urls`) |

В `DEBUG` режиме дополнительно раздаются `MEDIA_URL`/`STATIC_URL`.

## Management-команды

- `create_load_test_data` — актуальная команда генерации тестовых данных (студенты, курсы, экзамены)
- `import_from_sqlite` — разовая миграция данных SQLite → PostgreSQL
- `import_questions` — импорт банка вопросов из JSON (`docs/test/*.json`). Поддерживает два формата:
  - "Математика": разделы → блоки → вопросы, ответы буквами
  - "Информатика": категории → вопросы, ответы полным текстом
  - флаг `--clear` очищает вопросы предмета перед импортом
- ⚠️ `create_test_data` — сломана/устарела: вызывает `User.objects.create_user(student_id=..., role='student')`, но `User` не импортирован (только `from exams.models import *`), а у текущей модели `Student` нет поля `role`. Использовать `create_load_test_data` вместо неё.

## Настройки (`exam_system/settings.py`)

- `SECRET_KEY` захардкожен в коде (несмотря на наличие `.env.example`) — известный техдолг, отмечен TODO в README
- `TIME_ZONE = 'Asia/Tashkent'`, `LANGUAGE_CODE = 'ru-ru'`
- Сессии: `SESSION_COOKIE_AGE=28800` (8ч), `SESSION_SAVE_EVERY_REQUEST=True`
- БД настраивается через переменные окружения `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (дефолт — `postgres`/`localhost:5432`)
- Логирование в файл `exam_system.log` (логгер `exams`, уровень `INFO`)
- Production security-флаги (`SECURE_HSTS_*`, `SESSION_COOKIE_SECURE` и т.д.) включаются только при `DEBUG=False`

## Тесты

Тесты лежат в корневом `tests/` (не внутри приложений), запуск: `uv run python manage.py test tests`.

- `test_shuffle.py` — стабильность/случайность порядка вариантов ответа (`AnswerOrder`)
- `test_keywords.py` — проверка автогрейдинга open/text вопросов по ключевым словам
- `test_teacher_views.py` — флоу преподавателя (логин, дашборд, review)
- `test_result_detail.py` — детальный отчёт по результатам
- `locustfile.py` — сценарии нагрузочного тестирования (Locust)

## Известные технические особенности (не обязательно баги)

- `SECRET_KEY` захардкожен в `settings.py`
- `save_answer` использует `@csrf_exempt` вместе с сессионной аутентификацией
- `exams/management/commands/create_test_data.py` нерабочая (см. выше)
- `exams/tests.py` — неиспользуемая заглушка Django; реальные тесты в `/tests`
