import sqlite3
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.utils.dateparse import parse_datetime
from django.utils import timezone


def _dt(value):
    """Parse SQLite datetime string to aware datetime."""
    if value is None:
        return None
    dt = parse_datetime(str(value).replace(' ', 'T'))
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


def _bool(value):
    return bool(value) if value is not None else False


def _rows(conn, table):
    conn.row_factory = sqlite3.Row
    cur = conn.execute(f"SELECT * FROM {table}")
    return [dict(row) for row in cur.fetchall()]


def _reset_sequences(tables):
    """Reset PostgreSQL auto-increment sequences after bulk insert with explicit PKs."""
    with connection.cursor() as cur:
        for table in tables:
            cur.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 1)
                )
            """)


class Command(BaseCommand):
    help = 'Import data from a SQLite (.sqlite3 / .db) file into the configured PostgreSQL database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            default='db.sqlite3',
            metavar='FILE',
            help='Path to source SQLite file (default: db.sqlite3)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing exams data before importing',
        )

    def handle(self, *args, **options):
        source = Path(options['source'])
        if not source.exists():
            raise CommandError(f"File not found: {source}")

        self.stdout.write(f"Source: {source}")
        conn = sqlite3.connect(str(source))

        try:
            with transaction.atomic():
                if options['clear']:
                    self._clear_data()

                self._import_courses(conn)
                self._import_students(conn)
                self._import_subjects(conn)
                self._import_course_students(conn)
                self._import_questions(conn)
                self._import_answers(conn)
                self._import_exams(conn)
                self._import_exam_subjects(conn)
                self._import_exam_results(conn)
                self._import_exam_result_questions(conn)
                self._import_student_answers(conn)
                self._import_student_answer_selected(conn)
                self._import_student_imports(conn)

            _reset_sequences([
                'exams_course', 'exams_student', 'exams_subject',
                'exams_coursestudent', 'exams_question', 'exams_answer',
                'exams_exam', 'exams_examsubject', 'exams_examresult',
                'exams_studentanswer', 'exams_studentimport',
            ])
        finally:
            conn.close()

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))

    # ------------------------------------------------------------------

    def _clear_data(self):
        from exams.models import (
            StudentImport, StudentAnswer, ExamResult,
            ExamSubject, Exam, Answer, Question,
            CourseStudent, Subject, Student, Course,
        )
        self.stdout.write("  Clearing existing data...")
        StudentAnswer.objects.all().delete()
        ExamResult.objects.all().delete()
        ExamSubject.objects.all().delete()
        Exam.objects.all().delete()
        Answer.objects.all().delete()
        Question.objects.all().delete()
        CourseStudent.objects.all().delete()
        Subject.objects.all().delete()
        Student.objects.all().delete()
        Course.objects.all().delete()
        StudentImport.objects.all().delete()

    def _import_courses(self, conn):
        from exams.models import Course
        rows = _rows(conn, 'exams_course')
        objs = [
            Course(
                id=r['id'],
                name=r['name'],
                description=r.get('description', ''),
                created_at=_dt(r['created_at']),
            )
            for r in rows
        ]
        Course.objects.bulk_create(objs, update_conflicts=True,
                                   update_fields=['name', 'description', 'created_at'],
                                   unique_fields=['id'])
        self._log('Course', len(objs))

    def _import_students(self, conn):
        from exams.models import Student
        rows = _rows(conn, 'exams_student')
        objs = [
            Student(
                id=r['id'],
                student_id=r['student_id'],
                first_name=r['first_name'],
                last_name=r['last_name'],
                group=r.get('group', ''),
                email=r.get('email', ''),
                is_active=_bool(r['is_active']),
                created_at=_dt(r['created_at']),
            )
            for r in rows
        ]
        Student.objects.bulk_create(objs, update_conflicts=True,
                                    update_fields=['student_id', 'first_name', 'last_name',
                                                   'group', 'email', 'is_active', 'created_at'],
                                    unique_fields=['id'])
        self._log('Student', len(objs))

    def _import_subjects(self, conn):
        from exams.models import Subject
        rows = _rows(conn, 'exams_subject')
        objs = [
            Subject(
                id=r['id'],
                name=r['name'],
                description=r.get('description', ''),
                course_id=r['course_id'],
            )
            for r in rows
        ]
        Subject.objects.bulk_create(objs, update_conflicts=True,
                                    update_fields=['name', 'description', 'course_id'],
                                    unique_fields=['id'])
        self._log('Subject', len(objs))

    def _import_course_students(self, conn):
        from exams.models import CourseStudent
        rows = _rows(conn, 'exams_coursestudent')
        objs = [
            CourseStudent(
                id=r['id'],
                course_id=r['course_id'],
                student_id=r['student_id'],
                enrolled_at=_dt(r['enrolled_at']),
            )
            for r in rows
        ]
        CourseStudent.objects.bulk_create(objs, update_conflicts=True,
                                          update_fields=['enrolled_at'],
                                          unique_fields=['id'])
        self._log('CourseStudent', len(objs))

    def _import_questions(self, conn):
        from exams.models import Question
        rows = _rows(conn, 'exams_question')
        objs = [
            Question(
                id=r['id'],
                subject_id=r['subject_id'],
                text_md=r.get('text_md', ''),
                text=r.get('text', ''),
                difficulty=r['difficulty'],
                question_type=r['question_type'],
                created_at=_dt(r['created_at']),
            )
            for r in rows
        ]
        Question.objects.bulk_create(objs, update_conflicts=True,
                                     update_fields=['subject_id', 'text_md', 'text',
                                                    'difficulty', 'question_type', 'created_at'],
                                     unique_fields=['id'])
        self._log('Question', len(objs))

    def _import_answers(self, conn):
        from exams.models import Answer
        rows = _rows(conn, 'exams_answer')
        objs = [
            Answer(
                id=r['id'],
                question_id=r['question_id'],
                text_md=r.get('text_md', ''),
                text=r.get('text', ''),
                is_correct=_bool(r['is_correct']),
            )
            for r in rows
        ]
        Answer.objects.bulk_create(objs, update_conflicts=True,
                                   update_fields=['question_id', 'text_md', 'text', 'is_correct'],
                                   unique_fields=['id'])
        self._log('Answer', len(objs))

    def _import_exams(self, conn):
        from exams.models import Exam
        rows = _rows(conn, 'exams_exam')
        objs = [
            Exam(
                id=r['id'],
                course_id=r['course_id'],
                name=r['name'],
                description=r.get('description', ''),
                open_time=_dt(r['open_time']),
                close_time=_dt(r['close_time']),
                duration_minutes=r['duration_minutes'],
                attempts_allowed=r['attempts_allowed'],
            )
            for r in rows
        ]
        Exam.objects.bulk_create(objs, update_conflicts=True,
                                 update_fields=['course_id', 'name', 'description',
                                                'open_time', 'close_time',
                                                'duration_minutes', 'attempts_allowed'],
                                 unique_fields=['id'])
        self._log('Exam', len(objs))

    def _import_exam_subjects(self, conn):
        from exams.models import ExamSubject
        rows = _rows(conn, 'exams_examsubject')
        objs = [
            ExamSubject(
                id=r['id'],
                exam_id=r['exam_id'],
                subject_id=r['subject_id'],
                easy_count=r['easy_count'],
                medium_count=r['medium_count'],
                hard_count=r['hard_count'],
                easy_points=r['easy_points'],
                medium_points=r['medium_points'],
                hard_points=r['hard_points'],
            )
            for r in rows
        ]
        ExamSubject.objects.bulk_create(objs, update_conflicts=True,
                                        update_fields=['easy_count', 'medium_count', 'hard_count',
                                                       'easy_points', 'medium_points', 'hard_points'],
                                        unique_fields=['id'])
        self._log('ExamSubject', len(objs))

    def _import_exam_results(self, conn):
        from exams.models import ExamResult
        rows = _rows(conn, 'exams_examresult')
        objs = [
            ExamResult(
                id=r['id'],
                exam_id=r['exam_id'],
                student_id=r['student_id'],
                start_time=_dt(r.get('start_time')),
                end_time=_dt(r.get('end_time')),
                status=r['status'],
                score=r['score'],
                max_score=r['max_score'],
            )
            for r in rows
        ]
        ExamResult.objects.bulk_create(objs, update_conflicts=True,
                                       update_fields=['exam_id', 'student_id', 'start_time',
                                                      'end_time', 'status', 'score', 'max_score'],
                                       unique_fields=['id'])
        self._log('ExamResult', len(objs))

    def _import_exam_result_questions(self, conn):
        """M2M: ExamResult <-> Question"""
        rows = _rows(conn, 'exams_examresult_questions')
        if not rows:
            return
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM exams_examresult")
            valid_results = {r[0] for r in cur.fetchall()}
            cur.execute("SELECT id FROM exams_question")
            valid_questions = {r[0] for r in cur.fetchall()}

        values = [
            (r['examresult_id'], r['question_id'])
            for r in rows
            if r['examresult_id'] in valid_results and r['question_id'] in valid_questions
        ]
        if not values:
            return
        with connection.cursor() as cur:
            cur.execute("DELETE FROM exams_examresult_questions")
            cur.executemany(
                "INSERT INTO exams_examresult_questions (examresult_id, question_id) "
                "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                values,
            )
        self._log('ExamResult.questions (M2M)', len(values))

    def _import_student_answers(self, conn):
        from exams.models import StudentAnswer
        rows = _rows(conn, 'exams_studentanswer')
        objs = [
            StudentAnswer(
                id=r['id'],
                exam_result_id=r['exam_result_id'],
                question_id=r['question_id'],
                answer_text=r.get('answer_text', ''),
                is_correct=r.get('is_correct'),
                points_earned=r.get('points_earned', 0) or 0,
                answered_at=_dt(r.get('answered_at')),
            )
            for r in rows
        ]
        StudentAnswer.objects.bulk_create(objs, update_conflicts=True,
                                          update_fields=['answer_text', 'is_correct',
                                                         'points_earned', 'answered_at'],
                                          unique_fields=['id'])
        self._log('StudentAnswer', len(objs))

    def _import_student_answer_selected(self, conn):
        """M2M: StudentAnswer <-> Answer"""
        rows = _rows(conn, 'exams_studentanswer_selected_answers')
        if not rows:
            return
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM exams_studentanswer")
            valid_sa = {r[0] for r in cur.fetchall()}
            cur.execute("SELECT id FROM exams_answer")
            valid_ans = {r[0] for r in cur.fetchall()}

        values = [
            (r['studentanswer_id'], r['answer_id'])
            for r in rows
            if r['studentanswer_id'] in valid_sa and r['answer_id'] in valid_ans
        ]
        if not values:
            return
        with connection.cursor() as cur:
            cur.execute("DELETE FROM exams_studentanswer_selected_answers")
            cur.executemany(
                "INSERT INTO exams_studentanswer_selected_answers (studentanswer_id, answer_id) "
                "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                values,
            )
        self._log('StudentAnswer.selected_answers (M2M)', len(values))

    def _import_student_imports(self, conn):
        from exams.models import StudentImport
        rows = _rows(conn, 'exams_studentimport')
        if not rows:
            return
        objs = [
            StudentImport(
                id=r['id'],
                uploaded_file=r.get('uploaded_file', ''),
                imported_at=_dt(r['imported_at']),
                imported_by=r.get('imported_by', ''),
                students_count=r.get('students_count', 0),
                success=_bool(r.get('success', False)),
                error_message=r.get('error_message', ''),
            )
            for r in rows
        ]
        StudentImport.objects.bulk_create(objs, update_conflicts=True,
                                          update_fields=['imported_by', 'students_count',
                                                         'success', 'error_message'],
                                          unique_fields=['id'])
        self._log('StudentImport', len(objs))

    def _log(self, model, count):
        self.stdout.write(f"  {model}: {count} records")
