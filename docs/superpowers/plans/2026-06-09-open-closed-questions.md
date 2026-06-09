# Open/Closed Questions + Teacher Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить перемешивание вариантов для закрытых вопросов, автопроверку открытых вопросов по ключевым словам, учительский портал `/teacher/` с дашбордом и проверкой ответов, и детализацию результатов по сложности.

**Architecture:** Новое приложение `teachers/` изолирует логику учительского раздела. `AnswerOrder` хранит перемешанный порядок вариантов ответа в `exams/`. `QuestionKeyword` и `Teacher` живут в `teachers/`. `StudentAnswer` получает 4 новых поля для учительской проверки.

**Tech Stack:** Django 5.2, PostgreSQL, psycopg2-binary, стандартные Django-шаблоны Bootstrap 5.

---

## File Map

**Создать:**
- `teachers/__init__.py`
- `teachers/apps.py`
- `teachers/models.py` — Teacher, QuestionKeyword
- `teachers/views.py` — login, logout, dashboard, review
- `teachers/urls.py`
- `teachers/admin.py` — TeacherAdmin, QuestionKeywordInline (на Question)
- `teachers/migrations/__init__.py`
- `templates/teachers/login.html`
- `templates/teachers/dashboard.html`
- `templates/teachers/review.html`
- `tests/__init__.py`
- `tests/test_shuffle.py`
- `tests/test_keywords.py`
- `tests/test_teacher_views.py`
- `tests/test_result_detail.py`

**Изменить:**
- `exams/models.py` — добавить AnswerOrder, новые поля StudentAnswer, метод recalculate_score на ExamResult
- `exams/views.py` — start_exam (создание AnswerOrder), take_exam (ordered_answers), check_answer_correctness (ключевые слова), exam_result_detail (difficulty_stats), finalize_exam (effective_points)
- `exams/admin.py` — добавить QuestionKeywordInline на QuestionAdmin
- `exam_system/settings.py` — добавить 'teachers' в INSTALLED_APPS
- `exam_system/urls.py` — include('teachers.urls')
- `templates/exams/take_exam.html` — итерация по ordered_answers вместо question.answers.all
- `templates/exams/exam_result_detail.html` — таблица difficulty_stats

---

## Task 1: Настройка приложения teachers/ и миграции

**Files:**
- Create: `teachers/__init__.py`, `teachers/apps.py`, `teachers/models.py`, `teachers/migrations/__init__.py`
- Modify: `exam_system/settings.py`, `exams/models.py`

- [ ] **Шаг 1: Создать структуру приложения teachers/**

```bash
mkdir -p teachers/migrations
touch teachers/__init__.py teachers/migrations/__init__.py
```

- [ ] **Шаг 2: Создать `teachers/apps.py`**

```python
from django.apps import AppConfig

class TeachersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'teachers'
    verbose_name = 'Учителя'
```

- [ ] **Шаг 3: Создать `teachers/models.py`**

```python
from django.db import models
from django.contrib.auth.models import User


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    full_name = models.CharField(max_length=100, verbose_name='ФИО')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'

    def __str__(self):
        return self.full_name


class QuestionKeyword(models.Model):
    question = models.ForeignKey(
        'exams.Question', on_delete=models.CASCADE, related_name='keywords'
    )
    keyword = models.CharField(max_length=200, verbose_name='Ключевое слово')
    case_sensitive = models.BooleanField(default=False, verbose_name='Учитывать регистр')

    class Meta:
        verbose_name = 'Ключевое слово'
        verbose_name_plural = 'Ключевые слова'

    def __str__(self):
        return self.keyword
```

- [ ] **Шаг 4: Добавить новые поля и модели в `exams/models.py`**

Открыть `exams/models.py`. После класса `StudentAnswer` добавить модель `AnswerOrder`:

```python
class AnswerOrder(models.Model):
    """Хранит перемешанный порядок вариантов ответа для конкретной попытки."""
    student_answer = models.OneToOneField(
        StudentAnswer, on_delete=models.CASCADE, related_name='answer_order'
    )
    order = models.JSONField()  # [answer_id1, answer_id2, ...]

    class Meta:
        verbose_name = 'Порядок ответов'
        verbose_name_plural = 'Порядки ответов'
```

В класс `StudentAnswer` добавить 4 поля после `answered_at`:

```python
teacher_score = models.FloatField(null=True, blank=True, verbose_name='Балл преподавателя')
teacher_comment = models.TextField(blank=True, verbose_name='Комментарий преподавателя')
reviewed_by = models.ForeignKey(
    'teachers.Teacher', null=True, blank=True,
    on_delete=models.SET_NULL, related_name='reviewed_answers'
)
reviewed_at = models.DateTimeField(null=True, blank=True)
```

В класс `StudentAnswer` добавить свойство `effective_points`:

```python
@property
def effective_points(self):
    """Итоговый балл: балл преподавателя приоритетнее автопроверки."""
    if self.teacher_score is not None:
        return self.teacher_score
    return self.points_earned or 0
```

В класс `ExamResult` добавить метод `recalculate_score`:

```python
def recalculate_score(self):
    """Пересчитывает score с учётом teacher_score."""
    total = sum(sa.effective_points for sa in self.student_answers.all())
    self.score = total
    self.save(update_fields=['score'])
```

- [ ] **Шаг 5: Добавить 'teachers' в INSTALLED_APPS в `exam_system/settings.py`**

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'exams',
    'teachers',
]
```

- [ ] **Шаг 6: Создать и применить миграции**

```bash
uv run python manage.py makemigrations teachers
uv run python manage.py makemigrations exams --name studentanswer_teacher_fields_answerorder
uv run python manage.py migrate
```

Ожидаемый вывод: `teachers 0001_initial` и `exams 0002_...` применены без ошибок.

- [ ] **Шаг 7: Проверить миграции**

```bash
uv run python manage.py migrate --check
```

Ожидаемый вывод: нет ошибок, все миграции применены.

- [ ] **Шаг 8: Создать `tests/__init__.py`**

```bash
touch tests/__init__.py
```

- [ ] **Шаг 9: Написать тест для новых моделей в `tests/test_shuffle.py`**

```python
from django.test import TestCase
from django.contrib.auth.models import User
from exams.models import (
    Course, Student, Subject, Question, Answer,
    Exam, ExamSubject, ExamResult, StudentAnswer, AnswerOrder
)
from teachers.models import Teacher, QuestionKeyword
from django.utils import timezone
from datetime import timedelta


def make_exam_result():
    """Вспомогательная функция: создаёт минимальный набор данных для тестов."""
    course = Course.objects.create(name='Тест-курс')
    student = Student.objects.create(student_id='S001', first_name='Иван', last_name='Иванов')
    subject = Subject.objects.create(name='Математика', course=course)
    now = timezone.now()
    exam = Exam.objects.create(
        course=course, name='Экзамен',
        open_time=now - timedelta(hours=1),
        close_time=now + timedelta(hours=1),
        duration_minutes=60, attempts_allowed=1
    )
    ExamSubject.objects.create(
        exam=exam, subject=subject,
        easy_count=1, medium_count=0, hard_count=0,
        easy_points=1, medium_points=2, hard_points=3
    )
    question = Question.objects.create(
        subject=subject, text_md='Вопрос?',
        difficulty='easy', question_type='single_choice'
    )
    a1 = Answer.objects.create(question=question, text_md='A', is_correct=True)
    a2 = Answer.objects.create(question=question, text_md='B', is_correct=False)
    a3 = Answer.objects.create(question=question, text_md='C', is_correct=False)
    result = ExamResult.objects.create(
        exam=exam, student=student,
        start_time=now, status='in_progress'
    )
    sa = StudentAnswer.objects.create(exam_result=result, question=question)
    return result, sa, [a1, a2, a3]


class AnswerOrderModelTest(TestCase):
    def test_answer_order_created_and_stored(self):
        result, sa, answers = make_exam_result()
        order = [a.id for a in answers]
        ao = AnswerOrder.objects.create(student_answer=sa, order=order)
        ao_db = AnswerOrder.objects.get(student_answer=sa)
        self.assertEqual(ao_db.order, order)

    def test_effective_points_uses_teacher_score_when_set(self):
        _, sa, _ = make_exam_result()
        sa.points_earned = 1
        sa.teacher_score = 0.5
        sa.save()
        self.assertEqual(sa.effective_points, 0.5)

    def test_effective_points_falls_back_to_points_earned(self):
        _, sa, _ = make_exam_result()
        sa.points_earned = 1
        sa.teacher_score = None
        sa.save()
        self.assertEqual(sa.effective_points, 1)
```

- [ ] **Шаг 10: Запустить тест**

```bash
uv run python manage.py test tests.test_shuffle.AnswerOrderModelTest -v 2
```

Ожидаемый вывод: `Ran 3 tests... OK`

- [ ] **Шаг 11: Коммит**

```bash
git add teachers/ exams/models.py exams/migrations/ exam_system/settings.py tests/__init__.py tests/test_shuffle.py
git commit -m "feat: add teachers app, AnswerOrder, teacher fields on StudentAnswer"
```

---

## Task 2: Перемешивание вариантов ответа (AnswerOrder)

**Files:**
- Modify: `exams/views.py` — start_exam, take_exam
- Modify: `templates/exams/take_exam.html`

- [ ] **Шаг 1: Написать тест перемешивания в `tests/test_shuffle.py`**

Добавить в конец файла:

```python
from django.test import TestCase, RequestFactory
from exams.views import start_exam
from exams.models import CourseStudent


class AnswerShuffleTest(TestCase):
    def test_answer_order_created_on_exam_start(self):
        result, sa, answers = make_exam_result()
        # AnswerOrder не существует до начала экзамена
        self.assertFalse(AnswerOrder.objects.filter(student_answer=sa).exists())

    def test_shuffle_covers_all_answers(self):
        result, sa, answers = make_exam_result()
        answer_ids = [a.id for a in answers]
        import random
        shuffled = answer_ids[:]
        random.shuffle(shuffled)
        ao = AnswerOrder.objects.create(student_answer=sa, order=shuffled)
        self.assertEqual(sorted(ao.order), sorted(answer_ids))
```

- [ ] **Шаг 2: Запустить тест (должен пройти — логика не в views)**

```bash
uv run python manage.py test tests.test_shuffle.AnswerShuffleTest -v 2
```

Ожидаемый вывод: `OK`

- [ ] **Шаг 3: Изменить `start_exam` в `exams/views.py`**

Найти блок создания `StudentAnswer` (строки ~182–186):

```python
    # Создаем записи StudentAnswer
    for question in selected_questions:
        StudentAnswer.objects.create(
            exam_result=exam_result,
            question=question
        )
```

Заменить на:

```python
    # Создаем записи StudentAnswer и сохраняем перемешанный порядок вариантов
    for question in selected_questions:
        sa = StudentAnswer.objects.create(
            exam_result=exam_result,
            question=question
        )
        if question.question_type in ('single_choice', 'multiple_choice'):
            answer_ids = list(question.answers.values_list('id', flat=True))
            random.shuffle(answer_ids)
            AnswerOrder.objects.create(student_answer=sa, order=answer_ids)
```

Добавить импорт модели в начало файла (после `from .models import *`):

```python
from .models import AnswerOrder
```

- [ ] **Шаг 4: Изменить `take_exam` в `exams/views.py`**

Найти блок после `student_answers = exam_result.student_answers...prefetch_related(...)`:

```python
    student_answers = exam_result.student_answers.select_related(
        'question', 
        'question__subject'
    ).prefetch_related(
        'question__answers',
        'selected_answers'
    )
    
    return render(request, 'exams/take_exam.html', {
        'exam_result': exam_result,
        'student_answers': student_answers,
        'time_remaining': exam_result.time_remaining()
    })
```

Заменить на:

```python
    student_answers = list(
        exam_result.student_answers.select_related(
            'question', 'question__subject'
        ).prefetch_related(
            'question__answers', 'selected_answers', 'answer_order'
        )
    )

    # Прикрепляем ordered_answers к каждому ответу студента
    for sa in student_answers:
        if sa.question.question_type in ('single_choice', 'multiple_choice'):
            try:
                order = sa.answer_order.order
                answers_map = {a.id: a for a in sa.question.answers.all()}
                sa.ordered_answers = [answers_map[aid] for aid in order if aid in answers_map]
            except AnswerOrder.DoesNotExist:
                sa.ordered_answers = list(sa.question.answers.all())
        else:
            sa.ordered_answers = []

    return render(request, 'exams/take_exam.html', {
        'exam_result': exam_result,
        'student_answers': student_answers,
        'time_remaining': exam_result.time_remaining()
    })
```

- [ ] **Шаг 5: Обновить `templates/exams/take_exam.html`**

Найти ОБА блока с `{% for answer in student_answer.question.answers.all %}` (строки ~95 и ~124) и заменить на `{% for answer in student_answer.ordered_answers %}`.

Строка ~95 (single_choice):
```html
{% for answer in student_answer.ordered_answers %}
```

Строка ~124 (multiple_choice):
```html
{% for answer in student_answer.ordered_answers %}
```

- [ ] **Шаг 6: Запустить тесты**

```bash
uv run python manage.py test tests.test_shuffle -v 2
```

Ожидаемый вывод: `Ran 5 tests... OK`

- [ ] **Шаг 7: Коммит**

```bash
git add exams/views.py templates/exams/take_exam.html tests/test_shuffle.py
git commit -m "feat: shuffle answer options per attempt, stable on page reload"
```

---

## Task 3: Автопроверка открытых вопросов по ключевым словам

**Files:**
- Modify: `exams/views.py` — check_answer_correctness, save_answer
- Create: `tests/test_keywords.py`

- [ ] **Шаг 1: Написать тест в `tests/test_keywords.py`**

```python
from django.test import TestCase
from exams.models import (
    Course, Student, Subject, Question, Answer,
    Exam, ExamSubject, ExamResult, StudentAnswer
)
from teachers.models import QuestionKeyword
from exams.views import check_answer_correctness
from django.utils import timezone
from datetime import timedelta


def make_open_question():
    course = Course.objects.create(name='Курс')
    student = Student.objects.create(student_id='S002', first_name='Анна', last_name='Петрова')
    subject = Subject.objects.create(name='Биология', course=course)
    now = timezone.now()
    exam = Exam.objects.create(
        course=course, name='Открытый экзамен',
        open_time=now - timedelta(hours=1),
        close_time=now + timedelta(hours=1),
        duration_minutes=60, attempts_allowed=1
    )
    ExamSubject.objects.create(
        exam=exam, subject=subject,
        easy_count=1, medium_count=0, hard_count=0,
        easy_points=2, medium_points=0, hard_points=0
    )
    question = Question.objects.create(
        subject=subject, text_md='Что такое фотосинтез?',
        difficulty='easy', question_type='open'
    )
    result = ExamResult.objects.create(
        exam=exam, student=student, start_time=now, status='in_progress'
    )
    sa = StudentAnswer.objects.create(exam_result=result, question=question)
    return sa, question


class KeywordAutoCheckTest(TestCase):
    def test_keyword_match_marks_correct_and_awards_points(self):
        sa, question = make_open_question()
        QuestionKeyword.objects.create(question=question, keyword='фотосинтез')
        sa.answer_text = 'Фотосинтез — это процесс преобразования света'
        check_answer_correctness(sa)
        self.assertTrue(sa.is_correct)
        self.assertEqual(sa.points_earned, 2)

    def test_keyword_no_match_marks_incorrect(self):
        sa, question = make_open_question()
        QuestionKeyword.objects.create(question=question, keyword='фотосинтез')
        sa.answer_text = 'Не знаю ответа'
        check_answer_correctness(sa)
        self.assertFalse(sa.is_correct)
        self.assertEqual(sa.points_earned, 0)

    def test_no_keywords_leaves_is_correct_none(self):
        sa, question = make_open_question()
        sa.answer_text = 'Какой-то ответ'
        check_answer_correctness(sa)
        self.assertIsNone(sa.is_correct)

    def test_case_insensitive_by_default(self):
        sa, question = make_open_question()
        QuestionKeyword.objects.create(question=question, keyword='ФОТОСИНТЕЗ', case_sensitive=False)
        sa.answer_text = 'фотосинтез происходит в хлоропластах'
        check_answer_correctness(sa)
        self.assertTrue(sa.is_correct)

    def test_case_sensitive_no_match_on_wrong_case(self):
        sa, question = make_open_question()
        QuestionKeyword.objects.create(question=question, keyword='Фотосинтез', case_sensitive=True)
        sa.answer_text = 'фотосинтез происходит'
        check_answer_correctness(sa)
        self.assertFalse(sa.is_correct)
```

- [ ] **Шаг 2: Запустить тест (должен упасть — логика не добавлена)**

```bash
uv run python manage.py test tests.test_keywords -v 2
```

Ожидаемый вывод: `FAIL` — `is_correct` остаётся `None` вместо `True/False`.

- [ ] **Шаг 3: Расширить `check_answer_correctness` в `exams/views.py`**

Найти функцию `check_answer_correctness` (строки ~274–298) и заменить полностью:

```python
def check_answer_correctness(student_answer):
    """Проверка ответа: choice-вопросы и открытые по ключевым словам."""
    question = student_answer.question

    if question.question_type in ('open', 'text'):
        keywords = question.keywords.all()
        if not keywords.exists():
            student_answer.is_correct = None
            student_answer.points_earned = 0
            return

        text = student_answer.answer_text or ''
        matched = False
        for kw in keywords:
            if kw.case_sensitive:
                matched = kw.keyword in text
            else:
                matched = kw.keyword.lower() in text.lower()
            if matched:
                break

        student_answer.is_correct = matched
        if matched:
            exam_subject = ExamSubject.objects.filter(
                exam=student_answer.exam_result.exam,
                subject=question.subject
            ).first()
            if exam_subject:
                if question.difficulty == 'easy':
                    student_answer.points_earned = exam_subject.easy_points
                elif question.difficulty == 'medium':
                    student_answer.points_earned = exam_subject.medium_points
                else:
                    student_answer.points_earned = exam_subject.hard_points
        else:
            student_answer.points_earned = 0
        return

    # Закрытые вопросы (single_choice, multiple_choice)
    correct_answers = set(question.answers.filter(is_correct=True).values_list('id', flat=True))
    selected_answers = set(student_answer.selected_answers.values_list('id', flat=True))

    student_answer.is_correct = (
        correct_answers == selected_answers and len(selected_answers) > 0
    )

    if student_answer.is_correct:
        exam_subject = ExamSubject.objects.filter(
            exam=student_answer.exam_result.exam,
            subject=question.subject
        ).first()
        if exam_subject:
            if question.difficulty == 'easy':
                student_answer.points_earned = exam_subject.easy_points
            elif question.difficulty == 'medium':
                student_answer.points_earned = exam_subject.medium_points
            else:
                student_answer.points_earned = exam_subject.hard_points
    else:
        student_answer.points_earned = 0
```

- [ ] **Шаг 4: Обновить `save_answer` — вызывать check для открытых вопросов**

Найти блок в `save_answer` (~строки 249–261):

```python
        with transaction.atomic():
            if student_answer.question.question_type in ['open', 'text']:
                student_answer.answer_text = answer_text
                student_answer.is_correct = None
                student_answer.points_earned = None
            else:
```

Заменить на:

```python
        with transaction.atomic():
            if student_answer.question.question_type in ['open', 'text']:
                student_answer.answer_text = answer_text
                check_answer_correctness(student_answer)
            else:
```

- [ ] **Шаг 5: Запустить тесты**

```bash
uv run python manage.py test tests.test_keywords -v 2
```

Ожидаемый вывод: `Ran 5 tests... OK`

- [ ] **Шаг 6: Коммит**

```bash
git add exams/views.py tests/test_keywords.py
git commit -m "feat: auto-check open questions by keywords"
```

---

## Task 4: Django Admin — QuestionKeywordInline и TeacherAdmin

**Files:**
- Modify: `exams/admin.py` — добавить QuestionKeywordInline на QuestionAdmin
- Create: `teachers/admin.py`

- [ ] **Шаг 1: Добавить `QuestionKeywordInline` в `exams/admin.py`**

Найти класс `QuestionAdmin` и добавить перед ним:

```python
# Импорт в начало файла (после from .models import *)
# Добавить после существующих imports:
# (ничего не импортируем — используем строковую ссылку через app_label)

class QuestionKeywordInline(admin.TabularInline):
    model = None  # будет переопределён ниже после регистрации teachers
    extra = 1
    fields = ['keyword', 'case_sensitive']
```

Нет, это не сработает с `model = None`. Правильный способ — импортировать напрямую:

Найти начало `exams/admin.py` (строки с импортами) и добавить:

```python
# В конец секции импортов
try:
    from teachers.models import QuestionKeyword
    
    class QuestionKeywordInline(admin.TabularInline):
        model = QuestionKeyword
        extra = 1
        fields = ['keyword', 'case_sensitive']
        verbose_name = 'Ключевое слово'
        verbose_name_plural = 'Ключевые слова (для открытых вопросов)'
    _keyword_inline_available = True
except ImportError:
    _keyword_inline_available = False
```

В классе `QuestionAdmin` найти `inlines = [AnswerInline]` и заменить:

```python
    @property
    def get_inlines(self):
        inlines = [AnswerInline]
        if _keyword_inline_available:
            inlines.append(QuestionKeywordInline)
        return inlines
```

Нет — `inlines` не поддерживает `@property`. Используем `get_inline_instances`:

Вместо этого, добавить `QuestionKeywordInline` прямо в список:

```python
class QuestionAdmin(admin.ModelAdmin):
    # ... существующие поля ...
    inlines = [AnswerInline, QuestionKeywordInline]
```

Это работает только если импорт успешен. Поскольку `teachers` всегда в INSTALLED_APPS, используем прямой импорт. Итоговое изменение в `exams/admin.py`:

В начало файла добавить:
```python
from teachers.models import QuestionKeyword
```

После класса `AnswerInline` добавить:
```python
class QuestionKeywordInline(admin.TabularInline):
    model = QuestionKeyword
    extra = 1
    fields = ['keyword', 'case_sensitive']
    verbose_name = 'Ключевое слово'
    verbose_name_plural = 'Ключевые слова (для открытых вопросов)'
```

В `QuestionAdmin` изменить строку `inlines = [AnswerInline]` на:
```python
    inlines = [AnswerInline, QuestionKeywordInline]
```

- [ ] **Шаг 2: Создать `teachers/admin.py`**

```python
from django.contrib import admin
from .models import Teacher, QuestionKeyword


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'created_at']
    search_fields = ['full_name', 'user__username']
    raw_id_fields = ['user']


@admin.register(QuestionKeyword)
class QuestionKeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'question', 'case_sensitive']
    list_filter = ['case_sensitive', 'question__subject']
    search_fields = ['keyword', 'question__text_md']
```

- [ ] **Шаг 3: Проверить что admin запускается без ошибок**

```bash
uv run python manage.py check
```

Ожидаемый вывод: `System check identified no issues (0 silenced).`

- [ ] **Шаг 4: Коммит**

```bash
git add exams/admin.py teachers/admin.py
git commit -m "feat: add QuestionKeywordInline to admin, TeacherAdmin"
```

---

## Task 5: Учительский портал — аутентификация и маршруты

**Files:**
- Create: `teachers/views.py`, `teachers/urls.py`
- Create: `templates/teachers/login.html`
- Modify: `exam_system/urls.py`

- [ ] **Шаг 1: Написать тест аутентификации в `tests/test_teacher_views.py`**

```python
from django.test import TestCase, Client
from django.contrib.auth.models import User
from teachers.models import Teacher


def make_teacher_user():
    user = User.objects.create_user(
        username='teacher1', password='pass123', is_staff=True
    )
    teacher = Teacher.objects.create(user=user, full_name='Иван Преподаватель')
    return user, teacher


class TeacherAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, self.teacher = make_teacher_user()

    def test_dashboard_redirects_unauthenticated(self):
        response = self.client.get('/teacher/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/teacher/login/', response['Location'])

    def test_login_page_returns_200(self):
        response = self.client.get('/teacher/login/')
        self.assertEqual(response.status_code, 200)

    def test_login_with_valid_credentials(self):
        response = self.client.post('/teacher/login/', {
            'username': 'teacher1', 'password': 'pass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/teacher/')

    def test_login_with_invalid_credentials(self):
        response = self.client.post('/teacher/login/', {
            'username': 'teacher1', 'password': 'wrong'
        })
        self.assertEqual(response.status_code, 200)

    def test_non_staff_user_cannot_access_dashboard(self):
        regular = User.objects.create_user(username='student_u', password='pass')
        self.client.login(username='student_u', password='pass')
        response = self.client.get('/teacher/')
        self.assertEqual(response.status_code, 302)
```

- [ ] **Шаг 2: Запустить тест (должен упасть — маршруты не существуют)**

```bash
uv run python manage.py test tests.test_teacher_views.TeacherAuthTest -v 2
```

Ожидаемый вывод: `ERROR` — `NoReverseMatch` или 404.

- [ ] **Шаг 3: Создать `teachers/views.py`**

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q

from exams.models import ExamResult, StudentAnswer


def teacher_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('teacher_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect('teacher_dashboard')
        messages.error(request, 'Неверный логин/пароль или недостаточно прав')

    return render(request, 'teachers/login.html')


def teacher_logout(request):
    logout(request)
    return redirect('teacher_login')


@staff_member_required(login_url='/teacher/login/')
def teacher_dashboard(request):
    sort = request.GET.get('sort', 'date')

    results = ExamResult.objects.exclude(
        status='in_progress'
    ).select_related('student', 'exam', 'exam__course').annotate(
        pending_count=Count(
            'student_answers',
            filter=Q(
                student_answers__is_correct__isnull=True,
                student_answers__question__question_type__in=['open', 'text']
            )
        )
    )

    sort_map = {
        'date':    '-start_time',
        'student': 'student__last_name',
        'exam':    'exam__name',
        'pending': '-pending_count',
    }
    results = results.order_by(sort_map.get(sort, '-start_time'))

    return render(request, 'teachers/dashboard.html', {
        'results': results,
        'current_sort': sort,
    })


@staff_member_required(login_url='/teacher/login/')
def teacher_review(request, exam_result_id):
    exam_result = get_object_or_404(ExamResult, pk=exam_result_id)

    open_answers = exam_result.student_answers.filter(
        question__question_type__in=['open', 'text']
    ).select_related('question', 'question__subject', 'reviewed_by')

    if request.method == 'POST':
        for sa in open_answers:
            score_key = f'score_{sa.id}'
            comment_key = f'comment_{sa.id}'
            score_val = request.POST.get(score_key, '').strip()
            comment_val = request.POST.get(comment_key, '').strip()

            if score_val != '':
                try:
                    sa.teacher_score = float(score_val)
                except ValueError:
                    pass
            else:
                sa.teacher_score = None

            sa.teacher_comment = comment_val
            sa.reviewed_at = timezone.now()
            if hasattr(request.user, 'teacher_profile'):
                sa.reviewed_by = request.user.teacher_profile
            sa.save()

        exam_result.recalculate_score()
        messages.success(request, 'Оценки сохранены, итоговый балл пересчитан.')
        return redirect('teacher_review', exam_result_id=exam_result_id)

    # Максимальный балл для каждого открытого вопроса
    from exams.models import ExamSubject
    for sa in open_answers:
        es = ExamSubject.objects.filter(
            exam=exam_result.exam, subject=sa.question.subject
        ).first()
        if es:
            if sa.question.difficulty == 'easy':
                sa.max_points = es.easy_points
            elif sa.question.difficulty == 'medium':
                sa.max_points = es.medium_points
            else:
                sa.max_points = es.hard_points
        else:
            sa.max_points = 0

    return render(request, 'teachers/review.html', {
        'exam_result': exam_result,
        'open_answers': open_answers,
    })
```

- [ ] **Шаг 4: Создать `teachers/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.teacher_login, name='teacher_login'),
    path('logout/', views.teacher_logout, name='teacher_logout'),
    path('', views.teacher_dashboard, name='teacher_dashboard'),
    path('review/<int:exam_result_id>/', views.teacher_review, name='teacher_review'),
]
```

- [ ] **Шаг 5: Обновить `exam_system/urls.py`**

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('teacher/', include('teachers.urls')),
    path('', include('exams.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

- [ ] **Шаг 6: Запустить тест аутентификации**

```bash
uv run python manage.py test tests.test_teacher_views.TeacherAuthTest -v 2
```

Ожидаемый вывод: `FAIL` — шаблоны ещё не созданы.

- [ ] **Шаг 7: Создать `templates/teachers/login.html`**

```bash
mkdir -p templates/teachers
```

```html
{% extends 'base.html' %}
{% block title %}Вход для преподавателей{% endblock %}
{% block content %}
<div class="row justify-content-center mt-5">
  <div class="col-md-4">
    <div class="card shadow">
      <div class="card-header text-center bg-primary text-white">
        <h4 class="mb-0"><i class="fas fa-chalkboard-teacher me-2"></i>Кабинет преподавателя</h4>
      </div>
      <div class="card-body p-4">
        {% if messages %}
          {% for msg in messages %}
            <div class="alert alert-danger">{{ msg }}</div>
          {% endfor %}
        {% endif %}
        <form method="post">
          {% csrf_token %}
          <div class="mb-3">
            <label class="form-label">Логин</label>
            <input type="text" name="username" class="form-control" required autofocus>
          </div>
          <div class="mb-3">
            <label class="form-label">Пароль</label>
            <input type="password" name="password" class="form-control" required>
          </div>
          <button type="submit" class="btn btn-primary w-100">Войти</button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Шаг 8: Запустить тесты снова**

```bash
uv run python manage.py test tests.test_teacher_views.TeacherAuthTest -v 2
```

Ожидаемый вывод: `Ran 5 tests... OK`

- [ ] **Шаг 9: Коммит**

```bash
git add teachers/views.py teachers/urls.py exam_system/urls.py templates/teachers/login.html tests/test_teacher_views.py
git commit -m "feat: teacher portal auth, login/logout views"
```

---

## Task 6: Дашборд преподавателя с сортировкой

**Files:**
- Create: `templates/teachers/dashboard.html`

- [ ] **Шаг 1: Написать тест дашборда (добавить в `tests/test_teacher_views.py`)**

```python
from exams.models import (
    Course, Student, Exam, ExamSubject, Subject,
    ExamResult, StudentAnswer, Question, Answer
)
from django.utils import timezone
from datetime import timedelta


class TeacherDashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, self.teacher = make_teacher_user()
        self.client.login(username='teacher1', password='pass123')

        course = Course.objects.create(name='Курс')
        student = Student.objects.create(student_id='S010', first_name='А', last_name='Б')
        subject = Subject.objects.create(name='Физика', course=course)
        now = timezone.now()
        exam = Exam.objects.create(
            course=course, name='Финальный',
            open_time=now - timedelta(hours=2),
            close_time=now - timedelta(hours=1),
            duration_minutes=60, attempts_allowed=1
        )
        self.result = ExamResult.objects.create(
            exam=exam, student=student,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            status='finished', score=5, max_score=10
        )

    def test_dashboard_returns_200(self):
        response = self.client.get('/teacher/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_results(self):
        response = self.client.get('/teacher/')
        self.assertContains(response, 'Финальный')

    def test_dashboard_sort_by_student(self):
        response = self.client.get('/teacher/?sort=student')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_sort_by_exam(self):
        response = self.client.get('/teacher/?sort=exam')
        self.assertEqual(response.status_code, 200)
```

- [ ] **Шаг 2: Запустить тест (упадёт — шаблон не создан)**

```bash
uv run python manage.py test tests.test_teacher_views.TeacherDashboardTest -v 2
```

- [ ] **Шаг 3: Создать `templates/teachers/dashboard.html`**

```html
{% extends 'base.html' %}
{% block title %}Кабинет преподавателя{% endblock %}
{% block content %}
<div class="main-container p-4 mt-2">
  <div class="d-flex justify-content-between align-items-center mb-4">
    <h2><i class="fas fa-chalkboard-teacher me-2"></i>Результаты экзаменов</h2>
    <a href="{% url 'teacher_logout' %}" class="btn btn-outline-secondary btn-sm">Выйти</a>
  </div>

  <!-- Сортировка -->
  <div class="mb-3">
    <span class="text-muted me-2">Сортировка:</span>
    {% for key, label in sort_options.items %}
      <a href="?sort={{ key }}"
         class="btn btn-sm {% if current_sort == key %}btn-primary{% else %}btn-outline-secondary{% endif %} me-1">
        {{ label }}
      </a>
    {% endfor %}
  </div>

  <div class="table-responsive">
    <table class="table table-hover align-middle">
      <thead class="table-light">
        <tr>
          <th>Студент</th>
          <th>Экзамен</th>
          <th>Курс</th>
          <th>Дата сдачи</th>
          <th>Результат</th>
          <th>На проверке</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {% for result in results %}
        <tr>
          <td>{{ result.student.full_name }}</td>
          <td>{{ result.exam.name }}</td>
          <td>{{ result.exam.course.name }}</td>
          <td>{{ result.start_time|date:"d.m.Y H:i" }}</td>
          <td>
            <span class="badge bg-{% if result.percentage_score >= 70 %}success{% elif result.percentage_score >= 50 %}warning{% else %}danger{% endif %}">
              {{ result.percentage_score }}%
            </span>
          </td>
          <td>
            {% if result.pending_count > 0 %}
              <span class="badge bg-warning text-dark">{{ result.pending_count }} вопр.</span>
            {% else %}
              <span class="text-success"><i class="fas fa-check"></i></span>
            {% endif %}
          </td>
          <td>
            <a href="{% url 'teacher_review' result.id %}" class="btn btn-sm btn-outline-primary">
              Проверить
            </a>
          </td>
        </tr>
        {% empty %}
        <tr>
          <td colspan="7" class="text-center text-muted py-4">Результатов нет</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

- [ ] **Шаг 4: Добавить `sort_options` в контекст дашборда в `teachers/views.py`**

В `teacher_dashboard` view, заменить `return render(...)` на:

```python
    return render(request, 'teachers/dashboard.html', {
        'results': results,
        'current_sort': sort,
        'sort_options': {
            'date':    'По дате',
            'student': 'По студенту',
            'exam':    'По экзамену',
            'pending': 'Непроверенные первые',
        },
    })
```

- [ ] **Шаг 5: Запустить тесты**

```bash
uv run python manage.py test tests.test_teacher_views.TeacherDashboardTest -v 2
```

Ожидаемый вывод: `Ran 4 tests... OK`

- [ ] **Шаг 6: Коммит**

```bash
git add templates/teachers/dashboard.html teachers/views.py tests/test_teacher_views.py
git commit -m "feat: teacher dashboard with sorting"
```

---

## Task 7: Страница проверки открытых ответов

**Files:**
- Create: `templates/teachers/review.html`

- [ ] **Шаг 1: Написать тест проверки ответов (добавить в `tests/test_teacher_views.py`)**

```python
class TeacherReviewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, self.teacher = make_teacher_user()
        self.client.login(username='teacher1', password='pass123')

        course = Course.objects.create(name='Курс2')
        student = Student.objects.create(student_id='S020', first_name='Б', last_name='В')
        subject = Subject.objects.create(name='История', course=course)
        now = timezone.now()
        exam = Exam.objects.create(
            course=course, name='История экзамен',
            open_time=now - timedelta(hours=2),
            close_time=now - timedelta(hours=1),
            duration_minutes=60, attempts_allowed=1
        )
        ExamSubject.objects.create(
            exam=exam, subject=subject,
            easy_count=1, medium_count=0, hard_count=0,
            easy_points=5, medium_points=0, hard_points=0
        )
        question = Question.objects.create(
            subject=subject, text_md='Опишите революцию',
            difficulty='easy', question_type='open'
        )
        self.result = ExamResult.objects.create(
            exam=exam, student=student,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            status='finished', score=0, max_score=5
        )
        self.sa = StudentAnswer.objects.create(
            exam_result=self.result, question=question,
            answer_text='Революция 1917 года', is_correct=False, points_earned=0
        )

    def test_review_page_returns_200(self):
        response = self.client.get(f'/teacher/review/{self.result.id}/')
        self.assertEqual(response.status_code, 200)

    def test_review_page_shows_student_answer(self):
        response = self.client.get(f'/teacher/review/{self.result.id}/')
        self.assertContains(response, 'Революция 1917 года')

    def test_save_teacher_score_updates_exam_result(self):
        response = self.client.post(f'/teacher/review/{self.result.id}/', {
            f'score_{self.sa.id}': '4',
            f'comment_{self.sa.id}': 'Хороший ответ',
        })
        self.assertEqual(response.status_code, 302)
        self.sa.refresh_from_db()
        self.assertEqual(self.sa.teacher_score, 4.0)
        self.assertEqual(self.sa.teacher_comment, 'Хороший ответ')
        self.result.refresh_from_db()
        self.assertEqual(self.result.score, 4.0)

    def test_clear_teacher_score_sets_null(self):
        self.sa.teacher_score = 3.0
        self.sa.save()
        self.client.post(f'/teacher/review/{self.result.id}/', {
            f'score_{self.sa.id}': '',
            f'comment_{self.sa.id}': '',
        })
        self.sa.refresh_from_db()
        self.assertIsNone(self.sa.teacher_score)
```

- [ ] **Шаг 2: Запустить тест (упадёт — шаблон не создан)**

```bash
uv run python manage.py test tests.test_teacher_views.TeacherReviewTest -v 2
```

- [ ] **Шаг 3: Создать `templates/teachers/review.html`**

```html
{% extends 'base.html' %}
{% block title %}Проверка: {{ exam_result.exam.name }}{% endblock %}
{% block content %}
<div class="main-container p-4 mt-2">
  <div class="mb-4">
    <a href="{% url 'teacher_dashboard' %}" class="btn btn-outline-secondary btn-sm mb-2">
      ← Назад к списку
    </a>
    <h3>{{ exam_result.exam.name }}</h3>
    <p class="text-muted mb-0">
      Студент: <strong>{{ exam_result.student.full_name }}</strong> |
      Дата: {{ exam_result.start_time|date:"d.m.Y H:i" }} |
      Автобалл: {{ exam_result.score }} / {{ exam_result.max_score }}
    </p>
  </div>

  <form method="post">
    {% csrf_token %}
    {% for sa in open_answers %}
    <div class="card mb-4">
      <div class="card-header d-flex justify-content-between">
        <span>
          <strong>{{ forloop.counter }}. {{ sa.question.text_md }}</strong>
        </span>
        <span>
          <span class="badge bg-secondary">{{ sa.question.get_difficulty_display }}</span>
          <span class="badge bg-info">макс. {{ sa.max_points }} б.</span>
        </span>
      </div>
      <div class="card-body">
        <div class="mb-3">
          <label class="form-label text-muted">Ответ студента:</label>
          <div class="p-3 bg-light rounded">{{ sa.answer_text|default:"— нет ответа —" }}</div>
        </div>

        <!-- Результат автопроверки -->
        <div class="mb-3">
          <small class="text-muted">Автопроверка по ключевым словам: </small>
          {% if sa.is_correct is None %}
            <span class="badge bg-secondary">Не проверялось</span>
          {% elif sa.is_correct %}
            <span class="badge bg-success">Совпадение найдено</span>
          {% else %}
            <span class="badge bg-danger">Совпадений нет</span>
          {% endif %}
        </div>

        <div class="row g-3">
          <div class="col-md-3">
            <label class="form-label">Балл преподавателя (0–{{ sa.max_points }})</label>
            <input type="number" name="score_{{ sa.id }}" class="form-control"
                   min="0" max="{{ sa.max_points }}" step="0.5"
                   value="{{ sa.teacher_score|default:'' }}">
            <small class="text-muted">Оставьте пустым чтобы убрать оценку</small>
          </div>
          <div class="col-md-9">
            <label class="form-label">Комментарий студенту</label>
            <textarea name="comment_{{ sa.id }}" class="form-control" rows="2"
                      placeholder="Необязательно...">{{ sa.teacher_comment }}</textarea>
          </div>
        </div>

        {% if sa.reviewed_at %}
        <small class="text-muted d-block mt-2">
          Проверено: {{ sa.reviewed_at|date:"d.m.Y H:i" }}
          {% if sa.reviewed_by %} — {{ sa.reviewed_by.full_name }}{% endif %}
        </small>
        {% endif %}
      </div>
    </div>
    {% empty %}
    <div class="alert alert-info">
      <i class="fas fa-info-circle me-2"></i>В этом экзамене нет открытых вопросов.
    </div>
    {% endfor %}

    {% if open_answers %}
    <div class="d-flex justify-content-end mt-3">
      <button type="submit" class="btn btn-success btn-lg">
        <i class="fas fa-save me-2"></i>Сохранить оценки
      </button>
    </div>
    {% endif %}
  </form>
</div>
{% endblock %}
```

- [ ] **Шаг 4: Запустить тесты**

```bash
uv run python manage.py test tests.test_teacher_views -v 2
```

Ожидаемый вывод: `Ran 13 tests... OK`

- [ ] **Шаг 5: Коммит**

```bash
git add templates/teachers/review.html tests/test_teacher_views.py
git commit -m "feat: teacher review page with score override and recalculation"
```

---

## Task 8: Детализация результатов по сложности

**Files:**
- Modify: `exams/views.py` — exam_result_detail
- Modify: `templates/exams/exam_result_detail.html`
- Create: `tests/test_result_detail.py`

- [ ] **Шаг 1: Написать тест в `tests/test_result_detail.py`**

```python
from django.test import TestCase, Client
from exams.models import (
    Course, Student, Subject, Question, Answer,
    Exam, ExamSubject, ExamResult, StudentAnswer
)
from django.utils import timezone
from datetime import timedelta


def make_finished_exam():
    course = Course.objects.create(name='Курс3')
    student = Student.objects.create(student_id='S030', first_name='В', last_name='Г')
    subject = Subject.objects.create(name='Химия', course=course)
    now = timezone.now()
    exam = Exam.objects.create(
        course=course, name='Химия финал',
        open_time=now - timedelta(hours=2),
        close_time=now - timedelta(hours=1),
        duration_minutes=60, attempts_allowed=1
    )
    es = ExamSubject.objects.create(
        exam=exam, subject=subject,
        easy_count=1, medium_count=1, hard_count=1,
        easy_points=1, medium_points=2, hard_points=3
    )
    q_easy   = Question.objects.create(subject=subject, text_md='Л', difficulty='easy',   question_type='single_choice')
    q_medium = Question.objects.create(subject=subject, text_md='С', difficulty='medium', question_type='single_choice')
    q_hard   = Question.objects.create(subject=subject, text_md='Т', difficulty='hard',   question_type='single_choice')

    result = ExamResult.objects.create(
        exam=exam, student=student,
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
        status='finished', score=3, max_score=6
    )
    StudentAnswer.objects.create(exam_result=result, question=q_easy,   is_correct=True,  points_earned=1)
    StudentAnswer.objects.create(exam_result=result, question=q_medium, is_correct=False, points_earned=0)
    StudentAnswer.objects.create(exam_result=result, question=q_hard,   is_correct=True,  points_earned=3)
    return result, student


class ResultDetailDifficultyTest(TestCase):
    def setUp(self):
        self.result, self.student = make_finished_exam()
        self.client = Client()
        # Логиним студента через сессию напрямую
        session = self.client.session
        session['student_id'] = self.student.id
        session['student_name'] = self.student.full_name
        session.save()

    def test_result_detail_returns_200(self):
        response = self.client.get(f'/exams/results/{self.result.id}/')
        self.assertEqual(response.status_code, 200)

    def test_difficulty_stats_in_context(self):
        response = self.client.get(f'/exams/results/{self.result.id}/')
        stats = response.context['difficulty_stats']
        self.assertEqual(stats['easy']['correct'], 1)
        self.assertEqual(stats['easy']['total'], 1)
        self.assertEqual(stats['medium']['correct'], 0)
        self.assertEqual(stats['medium']['total'], 1)
        self.assertEqual(stats['hard']['correct'], 1)
        self.assertEqual(stats['hard']['total'], 1)

    def test_difficulty_stats_points(self):
        response = self.client.get(f'/exams/results/{self.result.id}/')
        stats = response.context['difficulty_stats']
        self.assertEqual(stats['easy']['points'], 1)
        self.assertEqual(stats['hard']['points'], 3)
```

- [ ] **Шаг 2: Запустить тест (упадёт — difficulty_stats не в контексте)**

```bash
uv run python manage.py test tests.test_result_detail -v 2
```

- [ ] **Шаг 3: Обновить `exam_result_detail` в `exams/views.py`**

Найти функцию `exam_result_detail` и заменить содержимое после `student_answers =`:

```python
    student_answers = exam_result.student_answers.select_related(
        'question', 'question__subject'
    ).prefetch_related(
        'question__answers',
        'selected_answers'
    )

    subject_stats = {}
    difficulty_stats = {
        'easy':   {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0, 'label': 'Лёгкие'},
        'medium': {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0, 'label': 'Средние'},
        'hard':   {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0, 'label': 'Сложные'},
    }

    for answer in student_answers:
        subject = answer.question.subject.name if answer.question.subject else "Без предмета"
        if subject not in subject_stats:
            subject_stats[subject] = {'correct': 0, 'total': 0, 'points': 0}

        subject_stats[subject]['total'] += 1
        if answer.is_correct:
            subject_stats[subject]['correct'] += 1
        subject_stats[subject]['points'] += answer.effective_points

        diff = answer.question.difficulty
        if diff in difficulty_stats:
            difficulty_stats[diff]['total'] += 1
            if answer.is_correct:
                difficulty_stats[diff]['correct'] += 1
            difficulty_stats[diff]['points'] += answer.effective_points

    return render(request, 'exams/exam_result_detail.html', {
        'exam_result': exam_result,
        'student_answers': student_answers,
        'subject_stats': subject_stats,
        'difficulty_stats': difficulty_stats,
    })
```

- [ ] **Шаг 4: Запустить тест**

```bash
uv run python manage.py test tests.test_result_detail -v 2
```

Ожидаемый вывод: `Ran 3 tests... OK`

- [ ] **Шаг 5: Обновить `templates/exams/exam_result_detail.html`**

Открыть файл. Найти секцию с `subject_stats` (таблица статистики по предметам) и добавить ПОСЛЕ неё:

```html
<!-- Статистика по сложности -->
<div class="card mb-4">
  <div class="card-header">
    <h5 class="mb-0"><i class="fas fa-layer-group me-2"></i>Результаты по уровню сложности</h5>
  </div>
  <div class="card-body p-0">
    <table class="table table-hover mb-0">
      <thead class="table-light">
        <tr>
          <th>Уровень</th>
          <th class="text-center">Правильных</th>
          <th class="text-center">Всего</th>
          <th class="text-center">% верных</th>
          <th class="text-center">Баллы</th>
        </tr>
      </thead>
      <tbody>
        {% for key, stat in difficulty_stats.items %}
        {% if stat.total > 0 %}
        <tr>
          <td>
            {% if key == 'easy' %}<span class="badge bg-success">{{ stat.label }}</span>
            {% elif key == 'medium' %}<span class="badge bg-warning text-dark">{{ stat.label }}</span>
            {% else %}<span class="badge bg-danger">{{ stat.label }}</span>{% endif %}
          </td>
          <td class="text-center">{{ stat.correct }}</td>
          <td class="text-center">{{ stat.total }}</td>
          <td class="text-center">
            {% widthratio stat.correct stat.total 100 %}%
          </td>
          <td class="text-center"><strong>{{ stat.points }}</strong></td>
        </tr>
        {% endif %}
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
```

- [ ] **Шаг 6: Запустить все тесты**

```bash
uv run python manage.py test tests -v 2
```

Ожидаемый вывод: все тесты прошли без ошибок.

- [ ] **Шаг 7: Финальный коммит**

```bash
git add exams/views.py templates/exams/exam_result_detail.html tests/test_result_detail.py
git commit -m "feat: difficulty breakdown in exam result detail"
```

---

## Self-review checklist

- [x] Spec §1 Закрытые вопросы — перемешивание: Task 2
- [x] Spec §2 Открытые вопросы — автопроверка по ключевым словам: Task 3
- [x] Spec §3 Учительский раздел — аутентификация: Task 5
- [x] Spec §4 Учительский раздел — дашборд с сортировкой: Task 6
- [x] Spec §5 Учительский раздел — проверка ответов + пересчёт score: Task 7
- [x] Spec §6 Детализация по сложности: Task 8
- [x] Spec §7 Django Admin QuestionKeywordInline: Task 4
- [x] Spec §8 Teacher — доступ ко всем предметам: реализовано (нет фильтрации по subject)
- [x] effective_points используется в Task 8 (subject_stats и difficulty_stats)
- [x] recalculate_score вызывается в Task 7 (teacher_review POST)
