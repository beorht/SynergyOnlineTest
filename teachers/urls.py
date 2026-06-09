from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.teacher_login, name='teacher_login'),
    path('logout/', views.teacher_logout, name='teacher_logout'),
    path('', views.teacher_dashboard, name='teacher_dashboard'),
    path('review/<int:exam_result_id>/', views.teacher_review, name='teacher_review'),
]
