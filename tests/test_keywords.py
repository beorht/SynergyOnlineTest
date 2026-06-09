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

    def test_no_keywords_open_answer_saves_to_db(self):
        sa, question = make_open_question()
        sa.answer_text = 'Какой-то ответ'
        check_answer_correctness(sa)
        sa.save()  # must not raise IntegrityError
        sa.refresh_from_db()
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
