# Структура базы данных

СУБД: **PostgreSQL** (в проде; настраивается через `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`). ORM: Django 5.2, `DEFAULT_AUTO_FIELD = BigAutoField`.

Приложения-владельцы таблиц: `exams` (миграции 0001–0005) и `teachers` (миграция 0001). Плюс стандартные таблицы Django (`auth_user`, `django_session`, `django_admin_log` и т.д.) — используется штатная модель `django.contrib.auth.User` только для преподавателей/админов, у студентов отдельная модель без наследования от `User`.

## ER-обзор

```
Course ──< Subject ──< Question ──< Answer
  │                        │
  │                        ├──< QuestionKeyword (teachers app, для open/text)
  │                        │
  ├──< CourseStudent >── Student
  │                        │
  ├──< Exam ──< ExamSubject (по Subject, easy/medium/hard counts + points)
  │       │
  │       └──< ExamResult >── Student
  │                │
  │                └──< StudentAnswer >── Question
  │                        │        \── selected_answers >── Answer (M2M)
  │                        └──1:1── AnswerOrder

Django User (auth) ──1:1── Teacher
StudentAnswer.reviewed_by ──> Teacher

StudentImport (независимая таблица — журнал импортов Excel)
```

## Таблицы приложения `exams`

### `Student`
Студент. Без наследования от Django `User` — своя система входа по `student_id`.

| Поле | Тип | Примечание |
|---|---|---|
| student_id | CharField(20) | unique, ID для входа |
| first_name | CharField(50) | |
| last_name | CharField(50) | |
| group | CharField(50) | blank |
| email | EmailField | blank |
| created_at | DateTimeField | auto_now_add |
| is_active | BooleanField | default True |

`ordering = ['last_name', 'first_name']`. Свойство `full_name`.

### `Course`
Курс. `name`, `description`, `created_at`.

### `CourseStudent`
M2M-связка `Course` ↔ `Student` (через явную модель). `unique_together = ['course', 'student']`. Поле `enrolled_at`.

### `Subject`
Предмет внутри курса. `name`, `description`, `course` (FK → Course, `related_name='subjects'`).

### `Question`
Вопрос экзамена.

| Поле | Тип | Примечание |
|---|---|---|
| subject | FK → Subject | `related_name='questions'` |
| text_md | TextField | текст вопроса (Markdown) |
| text | TextField | blank, обычный текст (fallback) |
| difficulty | CharField(10) | `easy` / `medium` / `hard` |
| question_type | CharField(15) | `single_choice` / `multiple_choice` / `open` / `text` |
| created_at | DateTimeField | auto_now_add |

### `Answer`
Вариант ответа для closed-вопросов. `question` (FK → Question, `related_name='answers'`), `text_md`, `text`, `is_correct` (bool).

### `Exam`
Экзамен, привязан к курсу.

| Поле | Тип | Примечание |
|---|---|---|
| course | FK → Course | `related_name='exams'` |
| name, description | | |
| open_time / close_time | DateTimeField | окно проведения |
| duration_minutes | IntegerField | 1–300 (валидаторы) |
| attempts_allowed | IntegerField | default 1, 1–5 |

Методы: `is_open()`, `is_upcoming()`, свойство `duration` (timedelta).

### `ExamSubject`
Настройка состава экзамена по предмету: сколько вопросов какой сложности и сколько баллов за каждую.

| Поле | Тип | Примечание |
|---|---|---|
| exam | FK → Exam | `related_name='exam_subjects'` |
| subject | FK → Subject | |
| easy_count / medium_count / hard_count | IntegerField | default 0 |
| medium_closed_count / medium_open_count | IntegerField | раздельные счётчики для средних вопросов (added in 0005); если заданы — **перекрывают** `medium_count` |
| easy_points / medium_points / hard_points | IntegerField | default 1/2/3 |

`unique_together = ['exam', 'subject']`. Методы: `effective_medium_count()` (сумма closed+open, либо `medium_count`), `points_for_difficulty()`, `total_questions()`, `max_score()`.

### `ExamResult`
Попытка прохождения экзамена студентом.

| Поле | Тип | Примечание |
|---|---|---|
| exam | FK → Exam | `related_name='results'` |
| student | FK → Student | `related_name='exam_results'` |
| start_time / end_time | DateTimeField | null допустим |
| status | CharField(20) | `in_progress` / `finished` / `time_expired` |
| score | FloatField | default 0 |
| max_score | FloatField | default 0 |
| questions | M2M → Question | `related_name='exam_results'`, снапшот выбранных вопросов попытки |

Методы: `percentage_score()`, `attempt_number()` (номер попытки студента по этому экзамену), `is_expired()`, `time_remaining()`, `recalculate_score()` (пересчёт `score` = сумма `effective_points` всех `StudentAnswer`).

### `StudentAnswer`
Ответ студента на конкретный вопрос в рамках попытки.

| Поле | Тип | Примечание |
|---|---|---|
| exam_result | FK → ExamResult | `related_name='student_answers'` |
| question | FK → Question | |
| selected_answers | M2M → Answer | blank, для choice-вопросов |
| answer_text | TextField | blank, для open/text-вопросов |
| is_correct | BooleanField | null=True (авто-проверка; `None` = не проверено/нет ключевых слов) |
| points_earned | IntegerField | default 0, начисляется автогрейдером |
| answered_at | DateTimeField | auto_now |
| teacher_score | FloatField | null=True, override баллов преподавателем |
| teacher_comment | TextField | blank |
| reviewed_by | FK → teachers.Teacher | null, SET_NULL, `related_name='reviewed_answers'` |
| reviewed_at | DateTimeField | null |

`unique_together = ['exam_result', 'question']`. Свойство `effective_points` = `teacher_score`, если задан, иначе `points_earned`.

### `AnswerOrder`
Стабильный (зафиксированный при старте попытки) порядок вариантов ответа для choice-вопросов — чтобы порядок не менялся при повторном открытии страницы.

| Поле | Тип | Примечание |
|---|---|---|
| student_answer | OneToOne → StudentAnswer | `related_name='answer_order'` |
| order | JSONField | список ID `Answer` в порядке показа |

### `StudentImport`
Журнал загрузок Excel-файлов со студентами (не связан FK с остальной схемой).

| Поле | Тип | Примечание |
|---|---|---|
| uploaded_file | FileField | `imports/students/` |
| imported_at | DateTimeField | auto_now_add |
| imported_by | CharField(100) | |
| students_count | IntegerField | default 0 |
| success | BooleanField | default False |
| error_message | TextField | blank |

`ordering = ['-imported_at']`.

## Таблицы приложения `teachers`

### `Teacher`
Профиль преподавателя поверх стандартного Django `User`.

| Поле | Тип | Примечание |
|---|---|---|
| user | OneToOne → auth.User | CASCADE, `related_name='teacher_profile'` |
| full_name | CharField(100) | |
| created_at | DateTimeField | auto_now_add |

Права определяются через `user.is_staff` (не отдельная ролевая система).

### `QuestionKeyword`
Ключевые слова для автопроверки open/text-вопросов.

| Поле | Тип | Примечание |
|---|---|---|
| question | FK → exams.Question | CASCADE, `related_name='keywords'` |
| keyword | CharField(200) | |
| case_sensitive | BooleanField | default False |

Логика проверки (`exams/views.py::check_answer_correctness`): если у вопроса нет ни одного `QuestionKeyword` — `is_correct=None` (не проверяется автоматически, ждёт преподавателя); иначе ищется вхождение подстроки любого ключевого слова в тексте ответа (без учёта регистра, если `case_sensitive=False`).

## История миграций

**exams:**
1. `0001_initial` — базовая схема (все основные модели)
2. `0002_answerorder_studentanswer_reviewed_at` — добавлены `AnswerOrder`, `StudentAnswer.reviewed_at`
3. `0003_studentanswer_reviewed_by_and_more` — добавлены `StudentAnswer.reviewed_by`, `teacher_score`, `teacher_comment`
4. `0004_studentanswer_is_correct_nullable` — `StudentAnswer.is_correct` стал nullable (для необработанных открытых ответов)
5. `0005_add_medium_closed_open_count` — добавлены `ExamSubject.medium_closed_count` / `medium_open_count`

**teachers:**
1. `0001_initial` — `Teacher`, `QuestionKeyword`

## Данные вне БД

Банки вопросов для первоначального импорта (через `import_questions` management-команду) хранятся как JSON-файлы в `docs/test/`:
- `matematika_9_class.json` (~170 вопросов)
- `informatika_test_9_class.json` (~146 вопросов)
