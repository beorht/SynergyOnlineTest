"""
Генерирует тестовые данные для нагрузочного тестирования Locust.

Создаёт:
  - 200 студентов (LOAD001 … LOAD200)
  - 1 курс с 2 предметами
  - 20 вопросов на каждый предмет (easy/medium/hard)
  - 1 открытый экзамен длительностью 2 часа
  - Записывает student IDs в tests/student_ids.txt

Usage:
    python manage.py create_load_test_data
    python manage.py create_load_test_data --students 50 --clean
"""

from pathlib import Path
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from exams.models import (
    Student, Course, CourseStudent, Subject,
    Question, Answer, Exam, ExamSubject,
)


QUESTIONS = {
    "easy": [
        ("Что такое переменная?", ["Ячейка памяти", "Тип данных", "Функция", "Цикл"], 0),
        ("Какой тип у числа 42?", ["int", "float", "str", "bool"], 0),
        ("Что делает print()?", ["Выводит текст", "Считывает ввод", "Создаёт файл", "Удаляет переменную"], 0),
        ("Как объявить список в Python?", ["[]", "{}", "()", "<>"], 0),
        ("Что такое цикл for?", ["Итерация по элементам", "Условие", "Функция", "Класс"], 0),
        ("Что такое функция?", ["Блок кода", "Переменная", "Тип данных", "Оператор"], 0),
        ("Как создать строку?", ["Кавычки", "Скобки", "Запятая", "Точка"], 0),
        ("Что возвращает len()?", ["Длину", "Тип", "Значение", "Индекс"], 0),
    ],
    "medium": [
        ("Что такое рекурсия?", ["Функция вызывает себя", "Цикл", "Условие", "Класс"], 0),
        ("Что такое list comprehension?", ["Краткий способ создать список", "Тип данных", "Метод", "Модуль"], 0),
        ("Что делает метод .split()?", ["Разбивает строку", "Объединяет", "Удаляет", "Сортирует"], 0),
        ("Что такое lambda?", ["Анонимная функция", "Переменная", "Тип", "Исключение"], 0),
        ("Что делает zip()?", ["Объединяет итерируемые", "Разделяет", "Сортирует", "Фильтрует"], 0),
        ("Что такое декоратор?", ["Функция-обёртка", "Тип данных", "Класс", "Модуль"], 0),
    ],
    "hard": [
        ("Что такое GIL в Python?", ["Блокировка потоков", "Тип данных", "Алгоритм", "Паттерн"], 0),
        ("Что такое metaclass?", ["Класс класса", "Наследование", "Интерфейс", "Модуль"], 0),
        ("Что такое генератор?", ["Функция с yield", "Список", "Словарь", "Декоратор"], 0),
        ("Что такое контекстный менеджер?", ["with-блок", "Исключение", "Поток", "Модуль"], 0),
    ],
}


class Command(BaseCommand):
    help = "Создаёт данные для нагрузочного тестирования (200 студентов + открытый экзамен)"

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=200, help="Количество студентов")
        parser.add_argument("--clean", action="store_true", help="Удалить старые тестовые данные перед созданием")

    def handle(self, *args, **options):
        count = options["students"]

        if options["clean"]:
            deleted, _ = Student.objects.filter(student_id__startswith="LOAD").delete()
            self.stdout.write(f"Удалено {deleted} старых тестовых записей.")
            Course.objects.filter(name="[LOADTEST] Курс нагрузочного тестирования").delete()

        # --- Курс ---
        course, _ = Course.objects.get_or_create(
            name="[LOADTEST] Курс нагрузочного тестирования",
            defaults={"description": "Автоматически создан для Locust"},
        )

        # --- Предметы ---
        subject1, _ = Subject.objects.get_or_create(
            name="Основы Python", course=course,
            defaults={"description": ""},
        )
        subject2, _ = Subject.objects.get_or_create(
            name="Алгоритмы", course=course,
            defaults={"description": ""},
        )

        # --- Вопросы ---
        for subject in (subject1, subject2):
            if subject.questions.exists():
                continue
            for difficulty, items in QUESTIONS.items():
                for text, options_list, correct_idx in items:
                    q = Question.objects.create(
                        subject=subject,
                        text_md=text,
                        difficulty=difficulty,
                        question_type="single_choice",
                    )
                    for i, opt in enumerate(options_list):
                        Answer.objects.create(
                            question=q,
                            text_md=opt,
                            is_correct=(i == correct_idx),
                        )

        # --- Студенты ---
        existing_ids = set(
            Student.objects.filter(student_id__startswith="LOAD")
            .values_list("student_id", flat=True)
        )
        new_students = []
        for i in range(1, count + 1):
            sid = f"LOAD{i:03d}"
            if sid not in existing_ids:
                new_students.append(Student(
                    student_id=sid,
                    first_name="Load",
                    last_name=f"Student{i:03d}",
                    group="LOAD-TEST",
                    is_active=True,
                ))
        Student.objects.bulk_create(new_students)

        # --- Записываем на курс ---
        all_students = Student.objects.filter(student_id__startswith="LOAD")
        enrolled = set(
            CourseStudent.objects.filter(course=course)
            .values_list("student_id", flat=True)
        )
        enrollments = [
            CourseStudent(course=course, student=s)
            for s in all_students
            if s.id not in enrolled
        ]
        CourseStudent.objects.bulk_create(enrollments, ignore_conflicts=True)

        # --- Открытый экзамен ---
        now = timezone.now()
        exam, created = Exam.objects.get_or_create(
            name="[LOADTEST] Нагрузочный экзамен",
            course=course,
            defaults={
                "description": "Автоматически создан для Locust",
                "open_time": now - timedelta(minutes=5),
                "close_time": now + timedelta(hours=8),
                "duration_minutes": 120,
                "attempts_allowed": 5,
            },
        )

        if not created:
            # Обновляем время, чтобы экзамен был открыт прямо сейчас
            exam.open_time = now - timedelta(minutes=5)
            exam.close_time = now + timedelta(hours=8)
            exam.save(update_fields=["open_time", "close_time"])

        easy_q = len(QUESTIONS["easy"])
        medium_q = len(QUESTIONS["medium"])
        hard_q = len(QUESTIONS["hard"])

        for subject in (subject1, subject2):
            ExamSubject.objects.get_or_create(
                exam=exam, subject=subject,
                defaults={
                    "easy_count": min(3, easy_q),
                    "medium_count": min(3, medium_q),
                    "hard_count": min(2, hard_q),
                    "easy_points": 1,
                    "medium_points": 2,
                    "hard_points": 3,
                },
            )

        # --- Записываем student_ids.txt ---
        ids = list(all_students.values_list("student_id", flat=True))
        ids_file = Path(__file__).resolve().parents[3] / "tests" / "student_ids.txt"
        ids_file.write_text("\n".join(ids) + "\n")

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Студентов: {all_students.count()}"
            f"\n✓ Экзамен: '{exam.name}' | открыт до {exam.close_time.strftime('%d.%m.%Y %H:%M')}"
            f"\n✓ student_ids.txt обновлён ({len(ids)} ID)"
            f"\n\nЗапустите тест:\n"
            f"  locust -f tests/locustfile.py --host=http://localhost:8000"
        ))
