# 📝 Exam System MVP

## 📌 Описание проекта

MVP-проект онлайн-системы для проведения экзаменов.  
Функционал включает:

- Создание курсов и предметов
- Добавление студентов и привязка к курсам
- Формирование экзаменов с разными уровнями сложности вопросов
- Прохождение экзамена студентами с ограничением по времени и количеству попыток
- Подсчёт результатов и процентов правильных ответов
- Открытые и закрытые вопросы с автопроверкой по ключевым словам
- Кабинет преподавателя: дашборд, ручная проверка открытых ответов, пересчёт баллов
- Импорт банков тестов из JSON-файлов
- Импорт студентов из Excel

Проект разработан на **Django**, для запуска используется **Uvicorn (ASGI)**.  
Управление зависимостями и виртуальной средой — через [uv](https://github.com/astral-sh/uv).

---

## ⚡ Установка и запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Установка зависимостей

```bash
uv sync
```

### 3. Настройка базы данных (PostgreSQL)

Создайте базу данных:

```bash
sudo -u postgres createdb exam_system
```

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

Содержимое `.env`:

```
DB_NAME=exam_system
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
```

### 4. Миграции

```bash
uv run python manage.py migrate
```

### 5. Создание суперпользователя (администратор + преподаватель)

```bash
uv run python manage.py createsuperuser
```

> Суперпользователь имеет доступ к `/admin/` и `/teacher/`.

### 6. Загрузка данных

#### Тестовые данные (demo)

```bash
uv run python manage.py create_test_data
```

#### Импорт банка вопросов из JSON

```bash
# Базовый импорт
uv run python manage.py import_questions <путь_к_файлу.json> \
  --course "Название курса" \
  --subject "Название предмета"

# С очисткой существующих вопросов предмета перед импортом
uv run python manage.py import_questions <путь_к_файлу.json> \
  --course "9 класс" \
  --subject "Математика 9-Класс" \
  --clear
```

Поддерживаемые форматы JSON:

| Формат | Структура | Ответ (закрытый) |
|--------|-----------|------------------|
| Математика | `sections → blocks → questions` | Буква `"A"/"B"/"C"/"D"` |
| Информатика | `categories → questions` | Полный текст варианта |

Типы вопросов: `closed` → `single_choice`, `open` → `open`.  
Открытые вопросы с полем `answer` автоматически получают ключевое слово для автопроверки.

#### Импорт из SQLite

```bash
# Из db.sqlite3 (по умолчанию)
uv run python manage.py import_from_sqlite

# Из произвольного файла
uv run python manage.py import_from_sqlite --source db.sqlite3.db

# С очисткой перед импортом
uv run python manage.py import_from_sqlite --source db.sqlite3 --clear
```

#### Импорт студентов из Excel

Через веб-интерфейс: `/admin/import-students/` (только staff).

### 7. Запуск сервера

#### Development

```bash
DEBUG=True uv run uvicorn exam_system.asgi:application --reload --port 8000
```

Или через manage.py:

```bash
uv run python manage.py runserver
```

Переменные окружения для dev:

```
DEBUG=True
DB_NAME=exam_system
DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
```

После запуска проект доступен по адресу:

- 👉 Студент: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- 👉 Преподаватель: [http://127.0.0.1:8000/teacher/](http://127.0.0.1:8000/teacher/)
- 👉 Администратор: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

#### Production

```bash
# 1. Собрать статические файлы
uv run python manage.py collectstatic --noinput

# 2. Запустить с несколькими воркерами
DEBUG=False uv run uvicorn exam_system.asgi:application --workers 4 --port 8000
```

Переменные окружения для production:

```
DEBUG=False
SECRET_KEY=your-strong-random-secret-key
DB_NAME=exam_system
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=yourdomain.com
```

---

## 🗺 URL-маршруты

### Студент

| URL | Описание |
|-----|----------|
| `/` | Вход (по student_id) |
| `/logout/` | Выход |
| `/exams/` | Список доступных экзаменов |
| `/exams/start/<id>/` | Начать экзамен |
| `/exams/take/<id>/` | Страница прохождения экзамена |
| `/exams/answer/<id>/` | AJAX: сохранить ответ |
| `/exams/finish/<id>/` | AJAX: завершить экзамен |
| `/exams/results/` | История результатов |
| `/exams/results/<id>/` | Детальный отчёт по попытке |

### Преподаватель

| URL | Описание |
|-----|----------|
| `/teacher/login/` | Вход преподавателя (требует `is_staff=True`) |
| `/teacher/logout/` | Выход |
| `/teacher/` | Дашборд: все результаты с разбивкой по сложности |
| `/teacher/review/<id>/` | Ручная проверка открытых ответов |
| `/teacher/result/<id>/` | Полный отчёт студента (преподавательский вид) |

### Администратор

| URL | Описание |
|-----|----------|
| `/admin/` | Django Admin |
| `/admin/import-students/` | Импорт студентов из Excel |
| `/admin/export-template/` | Скачать шаблон Excel |

---

## 📂 Структура проекта

```
ExamsOnline/
├── exam_system/              # Django config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py / asgi.py
├── exams/                    # Основное приложение
│   ├── models.py             # 12 моделей
│   ├── views.py              # Все views: auth, exam flow, results, Excel
│   ├── urls.py
│   ├── admin.py
│   ├── migrations/
│   └── management/commands/
│       ├── create_test_data.py     # Генерация demo-данных
│       ├── import_from_sqlite.py   # Импорт из SQLite → PostgreSQL
│       └── import_questions.py     # Импорт банка вопросов из JSON
├── teachers/                 # Приложение преподавателя
│   ├── models.py             # Teacher, QuestionKeyword
│   ├── views.py              # Дашборд, проверка ответов
│   ├── urls.py
│   ├── admin.py
│   └── migrations/
├── templates/
│   ├── base.html
│   ├── exams/
│   └── teachers/
├── tests/                    # 29 автотестов
│   ├── test_shuffle.py
│   ├── test_keywords.py
│   ├── test_teacher_views.py
│   └── test_result_detail.py
├── docs/
│   └── test/                 # Банки вопросов JSON
│       ├── matematika_9_class.json     # 170 вопросов
│       └── informatika_test_9_class.json  # 146 вопросов
├── static/images/
├── pyproject.toml
├── manage.py
└── .env / .env.example
```

---

## 🧩 Модели

| Модель | Описание |
|--------|----------|
| `Student` | Студент, вход по `student_id` |
| `Course` | Учебный курс |
| `CourseStudent` | M2M: курс ↔ студент |
| `Subject` | Предмет (входит в курс) |
| `Question` | Вопрос: типы `single_choice/multiple_choice/open/text`, сложность `easy/medium/hard` |
| `Answer` | Вариант ответа с флагом `is_correct` |
| `Exam` | Экзамен с временными рамками и лимитом попыток |
| `ExamSubject` | M2M: экзамен ↔ предмет + количество и баллы по сложности |
| `ExamResult` | Результат попытки: `in_progress / finished / time_expired` |
| `StudentAnswer` | Ответ студента + `teacher_score`, `teacher_comment` |
| `AnswerOrder` | Стабильный порядок вариантов ответа для попытки (shuffle) |
| `Teacher` | Профиль преподавателя (привязан к Django User) |
| `QuestionKeyword` | Ключевое слово для автопроверки открытого вопроса |

---

## ✅ Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Backend | Django 5.2, Python 3.13 |
| ASGI Server | Uvicorn |
| База данных | PostgreSQL (prod) / SQLite (dev) |
| Зависимости | uv |
| Excel | pandas + openpyxl |
| Frontend | Bootstrap 5, Marked.js, MathJax |

---

## 🧪 Запуск тестов

```bash
uv run python manage.py test tests
```

29 тестов: shuffle порядка ответов, ключевые слова, views преподавателя, детальный отчёт.

---

## 📌 TODO

- [ ] Добавить REST API для мобильного клиента
- [ ] Реализовать фронтенд (React/Vue)
- [ ] Подключить CI/CD
- [ ] Вынести `SECRET_KEY` в `.env`
