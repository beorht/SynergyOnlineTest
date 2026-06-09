from django.db import models
from django.contrib.auth.models import User


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    full_name = models.CharField(max_length=100, verbose_name='ФИО')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'

    def __str__(self):
        return self.full_name


class QuestionKeyword(models.Model):
    question = models.ForeignKey(
        'exams.Question', on_delete=models.CASCADE, related_name='keywords'
    )
    keyword = models.CharField(max_length=200, verbose_name='Ключевое слово')
    case_sensitive = models.BooleanField(default=False, verbose_name='Учитывать регистр')

    class Meta:
        verbose_name = 'Ключевое слово'
        verbose_name_plural = 'Ключевые слова'

    def __str__(self):
        return self.keyword
