# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
from datetime import timedelta

class Student(models.Model):
    """Простая модель студента без наследования от Django User"""
    student_id = models.CharField(max_length=20, unique=True, verbose_name="ID студента")
    first_name = models.CharField(max_length=50, verbose_name="Имя")
    last_name = models.CharField(max_length=50, verbose_name="Фамилия") 
    group = models.CharField(max_length=50, blank=True, verbose_name="Группа")
    email = models.EmailField(blank=True, verbose_name="Email")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        verbose_name = "Студент"
        verbose_name_plural = "Студенты"
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.student_id})"
    
    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

class Course(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название курса")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"
    
    def __str__(self):
        return self.name

class CourseStudent(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['course', 'student']
        verbose_name = "Студент курса"
        verbose_name_plural = "Студенты курсов"

class Subject(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название предмета")
    description = models.TextField(blank=True, verbose_name="Описание")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')
    
    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"
    
    def __str__(self):
        return f"{self.course.name} - {self.name}"

class Question(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Легкий'),
        ('medium', 'Средний'),
        ('hard', 'Сложный'),
    ]
    
    TYPE_CHOICES = [
        ('single_choice', 'Один правильный ответ'),
        ('multiple_choice', 'Несколько правильных ответов'),
        ('open', 'Открытый ответ'),
        ('text', 'Текстовый ответ'),
    ]
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions')
    text_md = models.TextField(verbose_name="Текст вопроса (Markdown)")
    text = models.TextField(blank=True, verbose_name="Текст вопроса (обычный)")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    question_type = models.CharField(max_length=15, choices=TYPE_CHOICES, default='single_choice')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
    
    def __str__(self):
        text_preview = self.text_md or self.text or "Без текста"
        return f"{self.subject.name} - {text_preview[:50]}..."

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text_md = models.TextField(verbose_name="Текст ответа (Markdown)")
    text = models.TextField(blank=True, verbose_name="Текст ответа (обычный)")
    is_correct = models.BooleanField(default=False, verbose_name="Правильный ответ")
    
    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"
    
    def __str__(self):
        question_preview = self.question.text_md or self.question.text or "Без вопроса"
        answer_preview = self.text_md or self.text or "Без ответа"
        return f"{question_preview[:30]}... - {answer_preview[:30]}..."

class Exam(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exams')
    name = models.CharField(max_length=200, verbose_name="Название экзамена")
    description = models.TextField(blank=True, verbose_name="Описание")
    open_time = models.DateTimeField(verbose_name="Время открытия")
    close_time = models.DateTimeField(verbose_name="Время закрытия")
    duration_minutes = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(300)],
        verbose_name="Продолжительность (минуты)"
    )
    attempts_allowed = models.IntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Количество попыток"
    )
    
    class Meta:
        verbose_name = "Экзамен"
        verbose_name_plural = "Экзамены"
    
    def __str__(self):
        return f"{self.course.name} - {self.name}"
    
    def is_open(self):
        now = timezone.now()
        return self.open_time <= now <= self.close_time
    
    def is_upcoming(self):
        return timezone.now() < self.open_time
    
    @property
    def duration(self):
        """Возвращает продолжительность экзамена как timedelta"""
        return timedelta(minutes=self.duration_minutes)

class ExamSubject(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='exam_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    
    # Количество вопросов по сложности
    easy_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    medium_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    hard_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Баллы за вопросы по сложности
    easy_points = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    medium_points = models.IntegerField(default=2, validators=[MinValueValidator(0)])
    hard_points = models.IntegerField(default=3, validators=[MinValueValidator(0)])
    
    class Meta:
        unique_together = ['exam', 'subject']
        verbose_name = "Предмет экзамена"
        verbose_name_plural = "Предметы экзамена"
    
    def total_questions(self):
        return self.easy_count + self.medium_count + self.hard_count
    
    def max_score(self):
        return (self.easy_count * self.easy_points + 
                self.medium_count * self.medium_points + 
                self.hard_count * self.hard_points)

class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="results")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="exam_results")
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("in_progress", "В процессе"), ("finished", "Завершен"), ("time_expired", "Время вышло")],
        default="in_progress"
    )
    score = models.FloatField(default=0)
    max_score = models.FloatField(default=0)
    questions = models.ManyToManyField("Question", related_name="exam_results", blank=True)

    class Meta:
        verbose_name = "Результат экзамена"
        verbose_name_plural = "Результаты экзаменов"

    def __str__(self):
        return f"{self.student.full_name} - {self.exam} ({self.status})"

    def percentage_score(self):
        """Процент набранных баллов"""
        if self.max_score > 0:
            return round((self.score / self.max_score) * 100, 2)
        return 0
    percentage_score.short_description = "Результат %"

    def attempt_number(self):
        """Номер попытки для этого студента по экзамену"""
        return ExamResult.objects.filter(exam=self.exam, student=self.student, id__lte=self.id).count()
    attempt_number.short_description = "Попытка №"

    def is_expired(self):
        if self.start_time and self.exam.duration_minutes:
            elapsed = timezone.now() - self.start_time
            return elapsed.total_seconds() > (self.exam.duration_minutes * 60)
        return False

    def time_remaining(self):
        if not self.start_time:
            return None
        elapsed = timezone.now() - self.start_time
        return max(self.exam.duration - elapsed, timedelta(0))

    def recalculate_score(self):
        total = sum(sa.effective_points for sa in self.student_answers.all())
        self.score = total
        self.save(update_fields=['score'])


class StudentAnswer(models.Model):
    exam_result = models.ForeignKey(ExamResult, on_delete=models.CASCADE, related_name='student_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answers = models.ManyToManyField(Answer, blank=True)  # For single/multiple choice
    answer_text = models.TextField(blank=True)  # For open questions
    is_correct = models.BooleanField(null=True, blank=True, default=None)
    points_earned = models.IntegerField(default=0)
    answered_at = models.DateTimeField(auto_now=True)
    teacher_score = models.FloatField(null=True, blank=True, verbose_name='Балл преподавателя')
    teacher_comment = models.TextField(blank=True, verbose_name='Комментарий преподавателя')
    reviewed_by = models.ForeignKey(
        'teachers.Teacher', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reviewed_answers'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['exam_result', 'question']
        verbose_name = "Ответ студента"
        verbose_name_plural = "Ответы студентов"

    def __str__(self):
        return f"{self.exam_result.student.full_name} - {self.question.text_md[:30] if self.question.text_md else 'Без текста'}..."

    @property
    def effective_points(self):
        if self.teacher_score is not None:
            return self.teacher_score
        return self.points_earned if self.points_earned is not None else 0


class AnswerOrder(models.Model):
    student_answer = models.OneToOneField(
        StudentAnswer, on_delete=models.CASCADE, related_name='answer_order'
    )
    order = models.JSONField()

    class Meta:
        verbose_name = 'Порядок ответов'
        verbose_name_plural = 'Порядки ответов'

    def __str__(self):
        return f"AnswerOrder for SA#{self.student_answer_id}"


# Модель для импорта студентов из Excel
class StudentImport(models.Model):
    """Модель для хранения информации об импорте студентов"""
    uploaded_file = models.FileField(upload_to='imports/students/', verbose_name="Файл Excel")
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.CharField(max_length=100, verbose_name="Импортировал")
    students_count = models.IntegerField(default=0, verbose_name="Количество студентов")
    success = models.BooleanField(default=False, verbose_name="Успешно")
    error_message = models.TextField(blank=True, verbose_name="Сообщение об ошибке")
    
    class Meta:
        verbose_name = "Импорт студентов"
        verbose_name_plural = "Импорты студентов"
        ordering = ['-imported_at']
    
    def __str__(self):
        return f"Импорт от {self.imported_at.strftime('%d.%m.%Y %H:%M')} - {self.students_count} студентов"