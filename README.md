# 📝 Exam System MVP

## 📌 Описание проекта
MVP-проект онлайн-системы для проведения экзаменов.  
Функционал включает:
- Создание курсов и предметов
- Добавление студентов и привязка к курсам
- Формирование экзаменов с разными уровнями сложности вопросов
- Прохождение экзамена студентами с ограничением по времени и количеству попыток
- Подсчёт результатов и процентов правильных ответов

Проект разработан на **Django**, для запуска используется **Uvicorn (ASGI)**.  
Управление зависимостями и виртуальной средой — через [uv](https://github.com/astral-sh/uv).

---

## ⚡ Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
````

### 2. Установка зависимостей

```bash
uv sync
```

(при необходимости добавить новые пакеты)

```bash
uv add django uvicorn
```

### 3. Настройка базы данных (PostgreSQL)

Создайте базу данных:

```bash
sudo -u postgres createdb exam_system
```

Задайте переменные окружения (скопируйте `.env.example` в `.env` и заполните):

```bash
cp .env.example .env
export $(cat .env | xargs)
```

### 4. Миграции

```bash
uv run python manage.py migrate
```

### 5. Создание суперпользователя

```bash
uv run python manage.py createsuperuser
```

### 6. Загрузка данных

Из тестовых данных:

```bash
uv run python manage.py create_test_data
```

Или импорт из существующего SQLite-файла:

```bash
# Из db.sqlite3 (по умолчанию)
uv run python manage.py import_from_sqlite

# Из произвольного .db / .sqlite3 файла
uv run python manage.py import_from_sqlite --source db.sqlite3.db

# С очисткой перед импортом
uv run python manage.py import_from_sqlite --source db.sqlite3 --clear
```

### 7. Запуск сервера разработки

```bash
uv run uvicorn exam_system.asgi:application --reload --port 8000
```

После этого проект будет доступен по адресу:
👉 [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 📂 Структура проекта

* `exams/` — приложение для работы с экзаменами, вопросами и результатами, курсы и предметы, управление студентами и ролями
* `exams/management/commands/create_test_data.py` — генерация тестовых данных
* `exams/management/commands/import_from_sqlite.py` — импорт данных из SQLite (.sqlite3 / .db) в PostgreSQL
* `.env.example` — пример конфигурации переменных окружения для подключения к БД

---

## ✅ Стек технологий

* **Backend**: Django, Django ORM
* **ASGI Server**: Uvicorn
* **DB**: PostgreSQL (основная), миграция из SQLite через `import_from_sqlite`
* **Dependencies**: uv, psycopg2-binary

---

## 📌 TODO

* [ ] Добавить REST API для мобильного клиента
* [ ] Реализовать фронтенд (React/Vue)
* [ ] Подключить CI/CD
* [ ] Написать тесты



