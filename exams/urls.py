# exams/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Аутентификация
    path('', views.student_login, name='student_login'),
    path('logout/', views.student_logout, name='student_logout'),
    
    # Экзамены для студентов
    path('exams/', views.exam_list, name='exam_list'),
    path('exams/start/<int:exam_id>/', views.start_exam, name='start_exam'),
    path('exams/take/<int:exam_result_id>/', views.take_exam, name='take_exam'),
    
    # Работа с ответами
    path('exams/answer/<int:exam_result_id>/', views.save_answer, name='save_answer'),
    path('exams/finish/<int:exam_result_id>/', views.finish_exam, name='finish_exam'),
    
    # Результаты
    path('exams/results/', views.exam_results_list, name='exam_results_list'),
    path('exams/results/<int:exam_result_id>/', views.exam_result_detail, name='exam_result_detail'),
    
    # Административные функции
    path('admin/import-students/', views.import_students_view, name='import_students'),
    path('admin/export-template/', views.export_students_template, name='export_students_template'),
]