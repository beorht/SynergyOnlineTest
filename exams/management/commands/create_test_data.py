from django.core.management.base import BaseCommand
from exams.models import *
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Создает тестовые данные для системы экзаменов'

    def handle(self, *args, **options):
        # Создаем курс
        course = Course.objects.create(
            name="Основы программирования",
            description="Курс по основам программирования на Python"
        )
        
        # Создаем предметы
        subject1 = Subject.objects.create(
            name="Python Basics",
            description="Основы синтаксиса Python",
            course=course
        )
        
        subject2 = Subject.objects.create(
            name="Алгоритмы",
            description="Основные алгоритмы и структуры данных",
            course=course
        )
        
        # Создаем тестовых студентов
        # Создаем тестовых студентов
        students = []
        for i in range(1, 6):
            student = User.objects.create_user(
                username=f'student{i}',
                student_id=f'ST{i:03}',   # Уникальный ID
                first_name='Студент',
                last_name=f'№{i}',
                role='student'
            )
            students.append(student)
            CourseStudent.objects.create(course=course, student=student)

        # Легкие вопросы по Python (сделаем два, т.к. в ExamSubject указано easy_count=2)
        q1 = Question.objects.create(
            subject=subject1,
            text_md="Что выведет следующий код?\n```python\nprint('Hello, World!')\n```",
            difficulty='easy',
            question_type='single_choice'
        )
        Answer.objects.create(question=q1, text_md="Hello, World!", is_correct=True)
        Answer.objects.create(question=q1, text_md="Hello World!", is_correct=False)
        Answer.objects.create(question=q1, text_md="'Hello, World!'", is_correct=False)

        q1b = Question.objects.create(
            subject=subject1,
            text_md="Какой тип данных у числа 42 в Python?",
            difficulty='easy',
            question_type='single_choice'
        )
        Answer.objects.create(question=q1b, text_md="int", is_correct=True)
        Answer.objects.create(question=q1b, text_md="float", is_correct=False)
        Answer.objects.create(question=q1b, text_md="str", is_correct=False)

        # Средние вопросы
        q2 = Question.objects.create(
            subject=subject1,
            text_md="Какие из следующих операторов используются для сравнения в Python?",
            difficulty='medium',
            question_type='multiple_choice'
        )
        Answer.objects.create(question=q2, text_md="==", is_correct=True)
        Answer.objects.create(question=q2, text_md="!=", is_correct=True)
        Answer.objects.create(question=q2, text_md="=", is_correct=False)
        Answer.objects.create(question=q2, text_md="<>", is_correct=False)

        # Сложные вопросы
        q3 = Question.objects.create(
            subject=subject2,
            text_md="Объясните, что такое рекурсия в программировании и приведите пример.",
            difficulty='hard',
            question_type='open'
        )
        
        # Создаем экзамен
        exam = Exam.objects.create(
            course=course,
            name="Входной тест по программированию",
            description="Проверка базовых знаний",
            open_time=timezone.now(),
            close_time=timezone.now() + timedelta(days=7),
            duration_minutes=60,
            attempts_allowed=2
        )
        
        # Настройки экзамена по предметам
        ExamSubject.objects.create(
            exam=exam,
            subject=subject1,
            easy_count=2,
            medium_count=1,
            hard_count=0,
            easy_points=1,
            medium_points=2,
            hard_points=3
        )
        
        ExamSubject.objects.create(
            exam=exam,
            subject=subject2,
            easy_count=0,
            medium_count=1,
            hard_count=1,
            easy_points=1,
            medium_points=2,
            hard_points=3
        )
        
        self.stdout.write(
            self.style.SUCCESS('Тестовые данные созданы успешно!')
        )