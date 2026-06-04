# admin.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
from django.urls import reverse
from .models import *
from .views import import_students_view

class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'last_name', 'first_name', 'group', 'email', 'is_active', 'created_at']
    list_filter = ['is_active', 'group', 'created_at']
    search_fields = ['student_id', 'first_name', 'last_name', 'group', 'email']
    list_editable = ['is_active']
    ordering = ['last_name', 'first_name']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('student_id', 'first_name', 'last_name')
        }),
        ('Дополнительная информация', {
            'fields': ('group', 'email', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-students/', import_students_view, name='import_students'),
        ]
        return custom_urls + urls

class CourseStudentInline(admin.TabularInline):
    model = CourseStudent
    extra = 0

class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 0

class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'students_count', 'subjects_count', 'created_at']
    search_fields = ['name', 'description']
    inlines = [SubjectInline, CourseStudentInline]
    
    def students_count(self, obj):
        return obj.coursestudent_set.count()
    students_count.short_description = 'Количество студентов'
    
    def subjects_count(self, obj):
        return obj.subjects.count()
    subjects_count.short_description = 'Количество предметов'

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ['text_md', 'difficulty', 'question_type']

class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'questions_count', 'get_difficulty_distribution']
    list_filter = ['course', 'course__name']
    search_fields = ['name', 'description', 'course__name']
    inlines = [QuestionInline]
    
    def questions_count(self, obj):
        return obj.questions.count()
    questions_count.short_description = 'Вопросов'
    
    def get_difficulty_distribution(self, obj):
        easy = obj.questions.filter(difficulty='easy').count()
        medium = obj.questions.filter(difficulty='medium').count()
        hard = obj.questions.filter(difficulty='hard').count()
        return f"Л:{easy} С:{medium} Т:{hard}"
    get_difficulty_distribution.short_description = 'Легких:Средних:Тяжелых'

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 2
    fields = ['text_md', 'is_correct']

class QuestionAdmin(admin.ModelAdmin):
    list_display = ['preview_text', 'subject', 'difficulty', 'question_type', 'answers_count', 'correct_answers_count']
    list_filter = ['difficulty', 'question_type', 'subject', 'subject__course']
    search_fields = ['text_md', 'text', 'subject__name']
    inlines = [AnswerInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('subject', 'question_type', 'difficulty')
        }),
        ('Содержание вопроса', {
            'fields': ('text_md', 'text'),
            'description': 'Используйте text_md для форматированного текста или text для обычного'
        }),
    )
    
    def preview_text(self, obj):
        text = obj.text_md or obj.text or "Без текста"
        return text[:100] + "..." if len(text) > 100 else text
    preview_text.short_description = 'Текст вопроса'
    
    def answers_count(self, obj):
        return obj.answers.count()
    answers_count.short_description = 'Всего ответов'
    
    def correct_answers_count(self, obj):
        return obj.answers.filter(is_correct=True).count()
    correct_answers_count.short_description = 'Правильных'

class AnswerAdmin(admin.ModelAdmin):
    list_display = ['preview_text', 'question_preview', 'is_correct']
    list_filter = ['is_correct', 'question__subject', 'question__difficulty']
    search_fields = ['text_md', 'text', 'question__text_md']
    
    def preview_text(self, obj):
        text = obj.text_md or obj.text or "Без текста"
        return text[:50] + "..." if len(text) > 50 else text
    preview_text.short_description = 'Текст ответа'
    
    def question_preview(self, obj):
        text = obj.question.text_md or obj.question.text or "Без текста"
        return text[:50] + "..." if len(text) > 50 else text
    question_preview.short_description = 'Вопрос'

class ExamSubjectInline(admin.TabularInline):
    model = ExamSubject
    extra = 0
    fields = ['subject', 'easy_count', 'medium_count', 'hard_count', 'easy_points', 'medium_points', 'hard_points']

class ExamAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'open_time', 'close_time', 'duration_minutes', 'attempts_allowed', 'is_active']
    list_filter = ['course', 'open_time', 'close_time']
    search_fields = ['name', 'description', 'course__name']
    date_hierarchy = 'open_time'
    inlines = [ExamSubjectInline]
    
    def is_active(self, obj):
        if obj.is_open():
            return format_html('<span style="color: green;">●</span> Открыт')
        elif obj.is_upcoming():
            return format_html('<span style="color: orange;">●</span> Ожидается')
        else:
            return format_html('<span style="color: red;">●</span> Закрыт')
    is_active.short_description = 'Статус'

class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    readonly_fields = ['question', 'is_correct', 'points_earned', 'answered_at']
    fields = ['question', 'is_correct', 'points_earned', 'answered_at']

class ExamResultAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'status', 'score', 'max_score', 'percentage_score', 'start_time', 'attempt_number']
    list_filter = ['status', 'exam', 'exam__course', 'start_time']
    search_fields = ['student__first_name', 'student__last_name', 'student__student_id', 'exam__name']
    readonly_fields = ['percentage_score', 'attempt_number']
    date_hierarchy = 'start_time'
    inlines = [StudentAnswerInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'exam')

class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'exam_name', 'question_preview', 'is_correct', 'points_earned', 'answered_at']
    list_filter = ['is_correct', 'exam_result__exam', 'question__difficulty', 'answered_at']
    search_fields = ['exam_result__student__first_name', 'exam_result__student__last_name', 'question__text_md']
    readonly_fields = ['answered_at']
    
    def student_name(self, obj):
        return obj.exam_result.student.full_name
    student_name.short_description = 'Студент'
    
    def exam_name(self, obj):
        return obj.exam_result.exam.name
    exam_name.short_description = 'Экзамен'
    
    def question_preview(self, obj):
        text = obj.question.text_md or obj.question.text or "Без текста"
        return text[:50] + "..." if len(text) > 50 else text
    question_preview.short_description = 'Вопрос'

class StudentImportAdmin(admin.ModelAdmin):
    list_display = ['imported_at', 'imported_by', 'students_count', 'success', 'short_error']
    list_filter = ['success', 'imported_at', 'imported_by']
    readonly_fields = ['imported_at', 'students_count', 'success', 'error_message']
    
    def short_error(self, obj):
        if obj.error_message:
            return obj.error_message[:100] + "..." if len(obj.error_message) > 100 else obj.error_message
        return "Нет ошибок"
    short_error.short_description = 'Ошибки'

# Регистрируем модели
admin.site.register(Student, StudentAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)
admin.site.register(Exam, ExamAdmin)
admin.site.register(ExamResult, ExamResultAdmin)
admin.site.register(StudentAnswer, StudentAnswerAdmin)
admin.site.register(StudentImport, StudentImportAdmin)

# Настройки админки
admin.site.site_header = 'Система онлайн-экзаменов'
admin.site.site_title = 'Админ-панель'
admin.site.index_title = 'Управление системой экзаменов'