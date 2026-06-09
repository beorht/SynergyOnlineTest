# Design: Открытые/закрытые вопросы + Учительский раздел

**Дата:** 2026-06-09  
**Проект:** ExamsOnline (Synergy)  
**Статус:** Approved

---

## 1. Цели

1. **Закрытые вопросы** (single/multiple choice) — перемешивание вариантов ответов для каждой попытки, порядок стабилен при перезагрузке страницы.
2. **Открытые вопросы** (open/text) — автопроверка по ключевым словам сразу при сохранении ответа; преподаватель может скорректировать балл.
3. **Учительский раздел** `/teacher/` — отдельный раздел с логином для staff-пользователей, дашборд с сортировкой результатов, интерфейс проверки открытых ответов.
4. **Детализация результатов** — разбивка правильных/неправильных ответов по категориям сложности (easy / medium / hard).

---

## 2. Архитектура

### Новое приложение `teachers/`

Изолированный Django app. Не изменяет бизнес-логику `exams/` — только читает данные и пишет teacher_score / teacher_comment.

```
teachers/
  models.py       # Teacher, QuestionKeyword, AnswerOrder
  views.py        # login, dashboard, review
  urls.py         # /teacher/...
  templates/
    teachers/
      login.html
      dashboard.html
      review.html
```

### Маршруты

```
/teacher/login/           → вход преподавателя (Django auth)
/teacher/logout/          → выход
/teacher/                 → дашборд: все ExamResult с сортировкой
/teacher/review/<id>/     → проверка конкретного ExamResult
```

---

## 3. Модели данных

### Новые модели в `teachers/models.py`

```python
class Teacher(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name  = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    # Доступ ко всем предметам и курсам без ограничений

class QuestionKeyword(models.Model):
    question       = models.ForeignKey('exams.Question', on_delete=models.CASCADE,
                                       related_name='keywords')
    keyword        = models.CharField(max_length=100)
    case_sensitive = models.BooleanField(default=False)
```

### Новые/изменённые модели в `exams/models.py` (миграция)

`AnswerOrder` живёт в `exams/` — она напрямую связана с `StudentAnswer` и нужна в момент прохождения экзамена, а не только в учительском разделе.

```python
class AnswerOrder(models.Model):
    student_answer = models.OneToOneField(StudentAnswer, on_delete=models.CASCADE,
                                          related_name='answer_order')
    order          = models.JSONField()  # [answer_id1, answer_id2, ...]

# StudentAnswer — добавить поля
teacher_score   = models.FloatField(null=True, blank=True)
teacher_comment = models.TextField(blank=True)
reviewed_by     = models.ForeignKey('teachers.Teacher', null=True, blank=True,
                                     on_delete=models.SET_NULL)
reviewed_at     = models.DateTimeField(null=True, blank=True)
```

### Итоговый балл

```python
@property
def effective_points(self):
    if self.teacher_score is not None:
        return self.teacher_score
    return self.points_earned
```

---

## 4. Функционал закрытых вопросов — перемешивание

**Где:** `views.py::start_exam` — при создании `StudentAnswer` для каждого choice-вопроса генерируется перемешанный порядок вариантов и сохраняется в `AnswerOrder`.

**Шаблон `take_exam.html`:** вместо `question.answers.all` итерируется по `student_answer.answer_order.order`, подтягивая объекты `Answer` по ID.

**Гарантия:** при перезагрузке страницы порядок не меняется — берётся из `AnswerOrder`.

---

## 5. Функционал открытых вопросов — автопроверка

**Где:** `views.py::check_answer_correctness()` — расширить существующую функцию.

**Логика:**
```python
if question.question_type in ['open', 'text']:
    keywords = question.keywords.all()
    if keywords.exists():
        text = student_answer.answer_text
        for kw in keywords:
            check_text = text if kw.case_sensitive else text.lower()
            check_kw   = kw.keyword if kw.case_sensitive else kw.keyword.lower()
            if check_kw in check_text:
                student_answer.is_correct = True
                # начислить баллы по сложности из ExamSubject
                break
        else:
            student_answer.is_correct = False
            student_answer.points_earned = 0
    else:
        # нет ключевых слов — не проверяем автоматически, is_correct = None
        student_answer.is_correct = None
```

**Ключевые слова задаются** в Django Admin на странице вопроса (inline `QuestionKeywordInline`).

---

## 6. Учительский раздел

### Аутентификация

Используется стандартный Django auth (`django.contrib.auth`). Доступ — только `is_staff=True`. Декоратор `@staff_member_required` на все views.

### Дашборд `/teacher/`

Список всех `ExamResult` с аннотациями:
- Кол-во открытых вопросов без проверки (`teacher_score IS NULL AND is_correct IS NULL`)
- Студент, экзамен, дата, итоговый балл %

**Сортировка** (параметры GET):
- `?sort=date` — по дате сдачи (по умолчанию, новые первые)
- `?sort=student` — по фамилии студента
- `?sort=exam` — по названию экзамена
- `?sort=pending` — сначала с непроверенными ответами

### Страница проверки `/teacher/review/<exam_result_id>/`

Для каждого открытого вопроса показывает:
- Текст вопроса
- Ответ студента
- Результат автопроверки (ключевые слова: совпало / не совпало)
- Поле `teacher_score` (0 до max_points) — редактируемое
- Поле `teacher_comment` — текстовое поле для комментария студенту

При сохранении: обновляет `teacher_score`, `teacher_comment`, `reviewed_by`, `reviewed_at`. Пересчитывает `ExamResult.score`.

---

## 7. Детализация результатов по сложности

**Где:** `views.py::exam_result_detail()` — расширить `subject_stats`.

**Новая структура данных:**

```python
difficulty_stats = {
    'easy':   {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0},
    'medium': {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0},
    'hard':   {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0},
}
```

**Шаблон `exam_result_detail.html`:** новый блок таблицы с разбивкой:

| Уровень | Правильных | Всего | Баллы |
|---------|-----------|-------|-------|
| Лёгкие  | X         | Y     | Z     |
| Средние | X         | Y     | Z     |
| Сложные | X         | Y     | Z     |

---

## 8. Django Admin

- `QuestionKeywordInline` — на странице Question (добавление ключевых слов)
- `TeacherAdmin` — управление преподавателями
- `AnswerOrderAdmin` — скрыт (служебный)

---

## 9. Порядок реализации (фазы)

1. **Миграции** — новые модели `teachers/`, изменения `StudentAnswer`
2. **Перемешивание** — `AnswerOrder` в `start_exam`, шаблон `take_exam.html`
3. **Автопроверка** — `QuestionKeyword`, расширение `check_answer_correctness()`
4. **Admin inlines** — `QuestionKeywordInline`
5. **Учительский раздел** — auth, dashboard, review views + шаблоны
6. **Детализация результатов** — `exam_result_detail` view + шаблон
7. **Пересчёт score** — при сохранении teacher_score обновлять `ExamResult.score`
