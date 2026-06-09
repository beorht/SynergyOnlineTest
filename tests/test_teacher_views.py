from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from teachers.models import Teacher
from exams.models import (
    Course, Student, Exam, ExamSubject, Subject,
    ExamResult, StudentAnswer, Question, Answer
)


def make_teacher_user():
    user = User.objects.create_user(
        username='teacher1', password='pass123', is_staff=True
    )
    teacher = Teacher.objects.create(user=user, full_name='Иван Преподаватель')
    return user, teacher


class TeacherAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, self.teacher = make_teacher_user()

    def test_dashboard_redirects_unauthenticated(self):
        response = self.client.get('/teacher/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/teacher/login/', response['Location'])

    def test_login_page_returns_200(self):
        response = self.client.get('/teacher/login/')
        self.assertEqual(response.status_code, 200)

    def test_login_with_valid_credentials(self):
        response = self.client.post('/teacher/login/', {
            'username': 'teacher1', 'password': 'pass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/teacher/')

    def test_login_with_invalid_credentials(self):
        response = self.client.post('/teacher/login/', {
            'username': 'teacher1', 'password': 'wrong'
        })
        self.assertEqual(response.status_code, 200)

    def test_non_staff_user_cannot_access_dashboard(self):
        regular = User.objects.create_user(username='student_u', password='pass')
        self.client.login(username='student_u', password='pass')
        response = self.client.get('/teacher/')
        self.assertEqual(response.status_code, 302)


class TeacherDashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, self.teacher = make_teacher_user()
        self.client.login(username='teacher1', password='pass123')

        course = Course.objects.create(name='Курс')
        student = Student.objects.create(student_id='S010', first_name='А', last_name='Б')
        subject = Subject.objects.create(name='Физика', course=course)
        now = timezone.now()
        exam = Exam.objects.create(
            course=course, name='Финальный',
            open_time=now - timedelta(hours=2),
            close_time=now - timedelta(hours=1),
            duration_minutes=60, attempts_allowed=1
        )
        self.result = ExamResult.objects.create(
            exam=exam, student=student,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            status='finished', score=5, max_score=10
        )

    def test_dashboard_returns_200(self):
        response = self.client.get('/teacher/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_results(self):
        response = self.client.get('/teacher/')
        self.assertContains(response, 'Финальный')

    def test_dashboard_sort_by_student(self):
        response = self.client.get('/teacher/?sort=student')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_sort_by_exam(self):
        response = self.client.get('/teacher/?sort=exam')
        self.assertEqual(response.status_code, 200)
