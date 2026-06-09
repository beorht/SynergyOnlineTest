from django.contrib import admin
from .models import Teacher, QuestionKeyword


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'created_at']
    search_fields = ['full_name', 'user__username']
    raw_id_fields = ['user']


@admin.register(QuestionKeyword)
class QuestionKeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'question', 'case_sensitive']
    list_filter = ['case_sensitive', 'question__subject']
    search_fields = ['keyword', 'question__text_md']
