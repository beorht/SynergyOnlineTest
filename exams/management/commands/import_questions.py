import json
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exams.models import Answer, Course, Question, Subject
from teachers.models import QuestionKeyword

LETTER_TO_IDX = {c: i for i, c in enumerate('ABCD')}


class Command(BaseCommand):
    help = 'Import questions from a JSON test bank (matematika/informatika format)'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to JSON file')
        parser.add_argument('--subject', required=True, help='Subject name (created if missing)')
        parser.add_argument('--course', required=True, help='Course name (created if missing)')
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete existing questions for this subject before importing',
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        subject_name = options['subject']
        course_name = options['course']

        if not os.path.exists(json_file):
            raise CommandError(f'File not found: {json_file}')

        with open(json_file, encoding='utf-8') as f:
            data = json.load(f)

        groups, get_questions = self._detect_format(data)

        with transaction.atomic():
            course, _ = Course.objects.get_or_create(name=course_name)
            subject, _ = Subject.objects.get_or_create(name=subject_name, course=course)

            if options['clear']:
                deleted, _ = subject.questions.all().delete()
                self.stdout.write(f'Deleted {deleted} existing questions for "{subject_name}"')

            total = 0
            skipped = 0
            for group in groups:
                difficulty = group.get('level', 'medium')
                for q_data in get_questions(group):
                    ok = self._import_question(subject, difficulty, q_data)
                    if ok:
                        total += 1
                    else:
                        skipped += 1

        msg = f'Imported {total} questions into "{subject_name}" ({course_name})'
        if skipped:
            msg += f', skipped {skipped} (no question text)'
        self.stdout.write(self.style.SUCCESS(msg))

    # ------------------------------------------------------------------
    # Format detection
    # ------------------------------------------------------------------

    def _detect_format(self, data):
        if 'sections' in data:
            # matematika format: sections → blocks → questions
            def get_questions(group):
                for block in group.get('blocks', []):
                    yield from block.get('questions', [])
            return data['sections'], get_questions

        if 'categories' in data:
            # informatika format: categories → questions
            return data['categories'], lambda g: g.get('questions', [])

        raise CommandError('Unknown JSON format: expected top-level "sections" or "categories"')

    # ------------------------------------------------------------------
    # Single question import
    # ------------------------------------------------------------------

    def _import_question(self, subject, difficulty, q_data):
        text = (q_data.get('question') or '').strip()
        if not text:
            return False

        q_type_raw = q_data.get('type', 'closed')
        question_type = 'single_choice' if q_type_raw == 'closed' else 'open'

        question = Question.objects.create(
            subject=subject,
            text_md=text,
            text=text,
            difficulty=difficulty,
            question_type=question_type,
        )

        if question_type == 'single_choice':
            self._create_answers(question, q_data)
        else:
            self._create_keyword(question, q_data)

        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_answers(self, question, q_data):
        options = q_data.get('options') or []
        answer = str(q_data.get('answer', '')).strip()

        # Determine correct index
        # Format A: single uppercase letter → index into options list
        if len(answer) == 1 and answer.upper() in LETTER_TO_IDX:
            correct_idx = LETTER_TO_IDX[answer.upper()]
            for idx, opt_text in enumerate(options):
                Answer.objects.create(
                    question=question,
                    text_md=opt_text,
                    text=opt_text,
                    is_correct=(idx == correct_idx),
                )
        else:
            # Format B: answer is the full text of the correct option
            for opt_text in options:
                Answer.objects.create(
                    question=question,
                    text_md=opt_text,
                    text=opt_text,
                    is_correct=(opt_text.strip() == answer),
                )

    def _create_keyword(self, question, q_data):
        answer_text = str(q_data.get('answer', '')).strip()
        if answer_text:
            QuestionKeyword.objects.create(
                question=question,
                keyword=answer_text,
                case_sensitive=False,
            )
