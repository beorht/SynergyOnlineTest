"""
Export specific subjects with all related data (questions, answers, keywords, exams)
into a Django fixture file that can be loaded on a fresh database with:

    python manage.py loaddata <output_file>
"""
import json
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
from django.utils import timezone

from exams.models import Course, Subject, Question, Answer, Exam, ExamSubject
from teachers.models import QuestionKeyword


class Command(BaseCommand):
    help = 'Export subjects with questions, answers and exams to a fixture JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--subjects',
            nargs='+',
            metavar='NAME',
            help='Subject names to export (default: Математика 9-Класс and Информатика 9-Класс)',
        )
        parser.add_argument(
            '--course',
            default='9 класс',
            help='Course name (default: "9 класс")',
        )
        parser.add_argument(
            '--output',
            default='',
            help='Output file path (default: export_9klass_YYYYMMDD_HHMM.json)',
        )

    def handle(self, *args, **options):
        course_name = options['course']
        subject_names = options['subjects'] or ['Математика 9-Класс', 'Информатика 9-Класс']
        output = options['output'] or f"export_9klass_{timezone.now().strftime('%Y%m%d_%H%M')}.json"

        # --- Collect objects ---

        try:
            course = Course.objects.get(name=course_name)
        except Course.DoesNotExist:
            raise CommandError(f'Course not found: "{course_name}"')

        subjects = []
        for name in subject_names:
            try:
                subjects.append(Subject.objects.get(name=name, course=course))
            except Subject.DoesNotExist:
                raise CommandError(f'Subject not found: "{name}" in course "{course_name}"')

        questions = list(Question.objects.filter(subject__in=subjects).order_by('id'))
        question_ids = [q.id for q in questions]

        answers = list(Answer.objects.filter(question_id__in=question_ids).order_by('id'))
        keywords = list(QuestionKeyword.objects.filter(question_id__in=question_ids).order_by('id'))

        exams = list(
            Exam.objects.filter(exam_subjects__subject__in=subjects).distinct().order_by('id')
        )
        exam_ids = [e.id for e in exams]
        exam_subjects = list(ExamSubject.objects.filter(exam_id__in=exam_ids, subject__in=subjects).order_by('id'))

        # --- Serialize in dependency order ---

        all_objects = (
            [course]
            + subjects
            + questions
            + answers
            + keywords
            + exams
            + exam_subjects
        )

        fixture_json = serializers.serialize('json', all_objects, indent=2)

        with open(output, 'w', encoding='utf-8') as f:
            f.write(fixture_json)

        # --- Summary ---

        self.stdout.write(self.style.SUCCESS(f'\nЭкспорт завершён → {output}'))
        self.stdout.write(f'  Курс:             1  ({course.name})')
        self.stdout.write(f'  Предметы:         {len(subjects)}')
        self.stdout.write(f'  Вопросы:          {len(questions)}')
        self.stdout.write(f'  Ответы:           {len(answers)}')
        self.stdout.write(f'  Ключевые слова:   {len(keywords)}')
        self.stdout.write(f'  Экзамены:         {len(exams)}')
        self.stdout.write(f'  ExamSubject:      {len(exam_subjects)}')
        self.stdout.write(f'\nДля импорта на новой БД:')
        self.stdout.write(f'  python manage.py migrate')
        self.stdout.write(f'  python manage.py loaddata {output}')
