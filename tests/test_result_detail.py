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
