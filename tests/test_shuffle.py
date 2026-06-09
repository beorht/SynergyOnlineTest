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


class RecalculateScoreTest(TestCase):
    def test_recalculate_score_uses_effective_points(self):
        result, sa, _ = make_exam_result()
        sa.points_earned = 1
        sa.teacher_score = None
        sa.save()
        result.recalculate_score()
        result.refresh_from_db()
        self.assertEqual(result.score, 1)

    def test_recalculate_score_uses_teacher_score_when_set(self):
        result, sa, _ = make_exam_result()
        sa.points_earned = 1
        sa.teacher_score = 0.5
        sa.save()
        result.recalculate_score()
        result.refresh_from_db()
        self.assertEqual(result.score, 0.5)


class AnswerShuffleTest(TestCase):
    def test_answer_order_created_on_exam_start(self):
        result, sa, answers = make_exam_result()
        self.assertFalse(AnswerOrder.objects.filter(student_answer=sa).exists())

    def test_shuffle_covers_all_answers(self):
        result, sa, answers = make_exam_result()
        answer_ids = [a.id for a in answers]
        import random
        shuffled = answer_ids[:]
        random.shuffle(shuffled)
        ao = AnswerOrder.objects.create(student_answer=sa, order=shuffled)
        self.assertEqual(sorted(ao.order), sorted(answer_ids))
