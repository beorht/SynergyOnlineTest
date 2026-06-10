from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.teacher_login, name='teacher_login'),
    path('logout/', views.teacher_logout, name='teacher_logout'),
    path('', views.teacher_dashboard, name='teacher_dashboard'),
    path('export/', views.export_results_excel, name='export_results_excel'),
    path('review/<int:exam_result_id>/', views.teacher_review, name='teacher_review'),
    path('result/<int:exam_result_id>/', views.teacher_result_detail, name='teacher_result_detail'),
]
