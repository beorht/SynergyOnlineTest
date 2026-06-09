from django.test import TestCase, Client
from django.contrib.auth.models import User
from teachers.models import Teacher


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
