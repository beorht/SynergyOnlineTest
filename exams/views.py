import json
import random
import pandas as pd
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q, Sum, Prefetch
from django.core.files.storage import FileSystemStorage
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required

from .models import *

# ----------------------
# Сессии для студентов
# ----------------------

def set_student_session(request, student):
    """Устанавливает сессию для студента"""
    request.session['student_id'] = student.id
    request.session['student_name'] = student.full_name
    request.session.set_expiry(3600 * 8)  # 8 часов

def get_current_student(request):
    """Получает текущего студента из сессии"""
    student_id = request.session.get('student_id')
    if student_id:
        try:
            return Student.objects.get(id=student_id, is_active=True)
        except Student.DoesNotExist:
            pass
    return None

def student_required(view_func):
    """Декоратор для проверки аутентификации студента"""
    def wrapper(request, *args, **kwargs):
        student = get_current_student(request)
        if not student:
            return redirect('student_login')
        request.student = student
        return view_func(request, *args, **kwargs)
    return wrapper

# ----------------------
# Аутентификация
# ----------------------

def student_login(request):
    """Вход студента по student_id"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id', '').strip()
        try:
            student = Student.objects.get(student_id=student_id, is_active=True)
            set_student_session(request, student)
            return redirect('exam_list')
        except Student.DoesNotExist:
            messages.error(request, 'Неверный ID студента или студент неактивен')
    
    return render(request, 'exams/student_login.html')

def student_logout(request):
    """Выход из системы"""
    request.session.flush()
    return redirect('student_login')

# ----------------------
# Экзамены
# ----------------------

@student_required
def exam_list(request):
    """Список доступных экзаменов"""
    student = request.student

    student_course_ids = CourseStudent.objects.filter(
        student=student
    ).values_list('course_id', flat=True)

    # Один запрос вместо 3N: annotate считает попытки, prefetch тянет in_progress
    exams = (
        Exam.objects
        .filter(course_id__in=student_course_ids)
        .annotate(
            attempts_made=Count(
                'results',
                filter=Q(results__student=student),
            )
        )
        .prefetch_related(
            Prefetch(
                'results',
                queryset=ExamResult.objects.filter(student=student, status='in_progress'),
                to_attr='in_progress_results',
            )
        )
        .order_by('open_time')
    )

    exam_data = []
    for exam in exams:
        attempts = exam.attempts_made
        max_attempts_reached = exam.attempts_allowed and attempts >= exam.attempts_allowed

        if exam.is_upcoming():
            status = 'upcoming'
        elif exam.is_open():
            status = 'open'
        else:
            status = 'closed'

        in_progress = exam.in_progress_results[0] if exam.in_progress_results else None

        # CourseStudent проверка избыточна — exams уже отфильтрованы по курсам студента
        can_access = not max_attempts_reached and status == 'open'

        exam_data.append({
            'exam': exam,
            'attempts_made': attempts,
            'max_attempts_reached': max_attempts_reached,
            'can_access': can_access,
            'in_progress': in_progress,
            'status': status,
        })

    return render(request, 'exams/exam_list.html', {'exam_data': exam_data})

@student_required
def start_exam(request, exam_id):
    """Начало экзамена - только во время проведения"""
    exam = get_object_or_404(Exam, pk=exam_id)
    student = request.student
    
    # Проверяем, что экзамен открыт для прохождения
    if not exam.is_open():
        if exam.is_upcoming():
            messages.error(request, f'Экзамен "{exam.name}" еще не начался. Начало: {exam.open_time.strftime("%d.%m.%Y %H:%M")}')
        else:
            messages.error(request, f'Экзамен "{exam.name}" уже закрыт. Закрытие: {exam.close_time.strftime("%d.%m.%Y %H:%M")}')
        return redirect('exam_list')
    
    # Проверяем права студента на этот курс
    if not CourseStudent.objects.filter(student=student, course=exam.course).exists():
        messages.error(request, 'У вас нет доступа к этому экзамену')
        return redirect('exam_list')
    
    # Проверяем количество попыток
    attempts = ExamResult.objects.filter(exam=exam, student=student).count()
    if exam.attempts_allowed and attempts >= exam.attempts_allowed:
        messages.error(request, f'Исчерпано количество попыток ({exam.attempts_allowed})')
        return redirect('exam_list')
    
    # Проверяем, нет ли уже начатого экзамена
    existing_exam = ExamResult.objects.filter(
        exam=exam, 
        student=student, 
        status='in_progress'
    ).first()
    
    if existing_exam:
        return redirect('take_exam', exam_result_id=existing_exam.id)
    
    # Генерируем вопросы до транзакции (только чтение)
    selected_questions = []
    for exam_subject in exam.exam_subjects.all():
        selected_questions.extend(get_random_questions(exam_subject))

    if not selected_questions:
        messages.error(request, 'Не найдено вопросов для этого экзамена')
        return redirect('exam_list')

    # Создаем новый результат экзамена
    with transaction.atomic():
        exam_result = ExamResult.objects.create(
            exam=exam,
            student=student,
            start_time=timezone.now(),
            status="in_progress"
        )

        exam_result.questions.set(selected_questions)

        # Создаем записи StudentAnswer
        for question in selected_questions:
            sa = StudentAnswer.objects.create(
                exam_result=exam_result,
                question=question
            )
            if question.question_type in ('single_choice', 'multiple_choice'):
                answer_ids = list(question.answers.values_list('id', flat=True))
                random.shuffle(answer_ids)
                AnswerOrder.objects.create(student_answer=sa, order=answer_ids)
    
    messages.success(request, f'Экзамен "{exam.name}" начат. Удачи!')
    return redirect('take_exam', exam_result_id=exam_result.id)

@student_required
def take_exam(request, exam_result_id):
    """Прохождение экзамена"""
    exam_result = get_object_or_404(ExamResult, pk=exam_result_id, student=request.student)
    
    # ВАЖНО: Проверяем что экзамен еще открыт для прохождения
    if not exam_result.exam.is_open():
        messages.error(request, 'Время проведения экзамена истекло')
        return finalize_exam(exam_result, "time_expired")
    
    # Проверяем не истекло ли время экзамена для студента
    if exam_result.is_expired():
        return finalize_exam(exam_result, "time_expired")
    
    student_answers = list(
        exam_result.student_answers.select_related(
            'question', 'question__subject', 'answer_order'
        ).prefetch_related(
            'question__answers', 'selected_answers'
        )
    )

    for sa in student_answers:
        if sa.question.question_type in ('single_choice', 'multiple_choice'):
            try:
                order = sa.answer_order.order
                answers_map = {a.id: a for a in sa.question.answers.all()}
                sa.ordered_answers = [answers_map[aid] for aid in order if aid in answers_map]
            except AnswerOrder.DoesNotExist:
                sa.ordered_answers = list(sa.question.answers.all())
        else:
            sa.ordered_answers = []

    return render(request, 'exams/take_exam.html', {
        'exam_result': exam_result,
        'student_answers': student_answers,
        'time_remaining': exam_result.time_remaining()
    })

# ----------------------
# Ответы
# ----------------------

@student_required
@require_POST
@csrf_exempt
def save_answer(request, exam_result_id):
    try:
        data = json.loads(request.body)
        student_answer_id = data.get('student_answer_id')
        answer_ids = data.get('answer_ids', [])
        answer_text = data.get('answer_text', '')

        student_answer = get_object_or_404(
            StudentAnswer,
            id=student_answer_id,
            exam_result__student=request.student,
            exam_result__status='in_progress'
        )
        
        # Проверяем что экзамен еще открыт
        if not student_answer.exam_result.exam.is_open():
            return JsonResponse({'success': False, 'error': 'Время проведения экзамена истекло'})
        
        # Проверяем время экзамена студента
        if student_answer.exam_result.is_expired():
            return JsonResponse({'success': False, 'error': 'Время истекло'})

        with transaction.atomic():
            if student_answer.question.question_type in ['open', 'text']:
                student_answer.answer_text = answer_text
                check_answer_correctness(student_answer)
            else:
                student_answer.selected_answers.clear()
                if answer_ids:
                    answers = Answer.objects.filter(
                        id__in=answer_ids, 
                        question=student_answer.question
                    )
                    student_answer.selected_answers.set(answers)
                check_answer_correctness(student_answer)
            
            student_answer.save()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def check_answer_correctness(student_answer):
    """Проверка ответа"""
    question = student_answer.question

    if question.question_type in ('open', 'text'):
        keywords = question.keywords.all()
        if not keywords.exists():
            student_answer.is_correct = None
            student_answer.points_earned = 0
            return

        text = student_answer.answer_text or ''
        matched = False
        for kw in keywords:
            if kw.case_sensitive:
                matched = kw.keyword in text
            else:
                matched = kw.keyword.lower() in text.lower()
            if matched:
                break

        student_answer.is_correct = matched
        if matched:
            exam_subject = ExamSubject.objects.filter(
                exam=student_answer.exam_result.exam,
                subject=question.subject
            ).first()
            if exam_subject:
                if question.difficulty == 'easy':
                    student_answer.points_earned = exam_subject.easy_points
                elif question.difficulty == 'medium':
                    student_answer.points_earned = exam_subject.medium_points
                else:
                    student_answer.points_earned = exam_subject.hard_points
        else:
            student_answer.points_earned = 0
        return

    # Закрытые вопросы (single_choice, multiple_choice)
    correct_answers = set(question.answers.filter(is_correct=True).values_list('id', flat=True))
    selected_answers = set(student_answer.selected_answers.values_list('id', flat=True))

    student_answer.is_correct = (
        correct_answers == selected_answers and len(selected_answers) > 0
    )

    if student_answer.is_correct:
        exam_subject = ExamSubject.objects.filter(
            exam=student_answer.exam_result.exam,
            subject=question.subject
        ).first()
        if exam_subject:
            if question.difficulty == 'easy':
                student_answer.points_earned = exam_subject.easy_points
            elif question.difficulty == 'medium':
                student_answer.points_earned = exam_subject.medium_points
            else:
                student_answer.points_earned = exam_subject.hard_points
    else:
        student_answer.points_earned = 0

# ----------------------
# Завершение экзамена
# ----------------------

@require_POST
@student_required  
def finish_exam(request, exam_result_id):
    try:
        data = json.loads(request.body)
        exam_result_id = data.get('exam_result_id')
        exam_result = get_object_or_404(ExamResult, pk=exam_result_id, student=request.student)
        finalize_exam(exam_result, "finished")
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def finalize_exam(exam_result, status):
    """Финализирует экзамен"""
    with transaction.atomic():
        exam_result.end_time = timezone.now()
        exam_result.status = status
        exam_result.score = exam_result.student_answers.aggregate(
            total=Sum('points_earned')
        )['total'] or 0
        
        # Расчет максимального балла
        max_score = 0
        for exam_subject in exam_result.exam.exam_subjects.all():
            max_score += exam_subject.max_score()
        exam_result.max_score = max_score
        
        exam_result.save()
    return redirect('exam_result_detail', exam_result_id=exam_result.id)

# ----------------------
# Результаты
# ----------------------

@student_required
def exam_results_list(request):
    """Все экзамены студента"""
    results = ExamResult.objects.filter(student=request.student).order_by('-start_time')
    return render(request, 'exams/exam_results_list.html', {"results": results})

@student_required
def exam_result_detail(request, exam_result_id):
    """Детальный результат экзамена"""
    exam_result = get_object_or_404(ExamResult, id=exam_result_id, student=request.student)
    
    if exam_result.status == 'in_progress':
        return redirect('take_exam', exam_result_id=exam_result.id)

    student_answers = exam_result.student_answers.select_related(
        'question', 'question__subject'
    ).prefetch_related(
        'question__answers',
        'selected_answers'
    )

    subject_stats = {}
    difficulty_stats = {
        'easy':   {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0, 'label': 'Лёгкие'},
        'medium': {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0, 'label': 'Средние'},
        'hard':   {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0, 'label': 'Сложные'},
    }

    for answer in student_answers:
        subject = answer.question.subject.name if answer.question.subject else "Без предмета"
        if subject not in subject_stats:
            subject_stats[subject] = {'correct': 0, 'total': 0, 'points': 0}

        subject_stats[subject]['total'] += 1
        if answer.is_correct:
            subject_stats[subject]['correct'] += 1
        subject_stats[subject]['points'] += answer.effective_points

        diff = answer.question.difficulty
        if diff in difficulty_stats:
            difficulty_stats[diff]['total'] += 1
            if answer.is_correct:
                difficulty_stats[diff]['correct'] += 1
            difficulty_stats[diff]['points'] += answer.effective_points

    return render(request, 'exams/exam_result_detail.html', {
        'exam_result': exam_result,
        'student_answers': student_answers,
        'subject_stats': subject_stats,
        'difficulty_stats': difficulty_stats,
    })

# ----------------------
# Импорт из Excel
# ----------------------

@staff_member_required
def import_students_view(request):
    """Страница импорта студентов из Excel"""
    if request.method == 'POST' and request.FILES.get('excel_file'):
        return process_excel_import(request)
    
    recent_imports = StudentImport.objects.all()[:10]
    return render(request, 'admin/import_students.html', {
        'recent_imports': recent_imports
    })

def process_excel_import(request):
    """Обработка загруженного Excel файла"""
    excel_file = request.FILES['excel_file']
    
    # Создаем запись об импорте
    student_import = StudentImport.objects.create(
        uploaded_file=excel_file,
        imported_by=request.user.username if hasattr(request.user, 'username') else 'admin'
    )
    
    try:
        # Читаем Excel файл
        df = pd.read_excel(excel_file)
        
        # Проверяем наличие необходимых колонок
        required_columns = ['student_id', 'first_name', 'last_name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Отсутствуют колонки: {', '.join(missing_columns)}")
        
        # Обрабатываем каждую строку
        students_created = 0
        students_updated = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                student_id = str(row['student_id']).strip()
                first_name = str(row['first_name']).strip()
                last_name = str(row['last_name']).strip()
                
                if not all([student_id, first_name, last_name]):
                    errors.append(f"Строка {index + 2}: Пустые обязательные поля")
                    continue
                
                # Дополнительные поля
                group = str(row.get('group', '')).strip() if pd.notna(row.get('group')) else ''
                email = str(row.get('email', '')).strip() if pd.notna(row.get('email')) else ''
                
                # Создаем или обновляем студента
                student, created = Student.objects.update_or_create(
                    student_id=student_id,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'group': group,
                        'email': email,
                        'is_active': True
                    }
                )
                
                if created:
                    students_created += 1
                else:
                    students_updated += 1
                    
            except Exception as e:
                errors.append(f"Строка {index + 2}: {str(e)}")
        
        # Обновляем запись об импорте
        student_import.students_count = students_created + students_updated
        student_import.success = len(errors) == 0
        
        if errors:
            student_import.error_message = '\n'.join(errors[:10])  # Первые 10 ошибок
        
        student_import.save()
        
        # Сообщения пользователю
        if students_created or students_updated:
            messages.success(request, 
                f"Импорт завершен! Создано: {students_created}, Обновлено: {students_updated}")
        
        if errors:
            messages.warning(request, 
                f"Обнаружено {len(errors)} ошибок. Проверьте детали импорта.")
        
    except Exception as e:
        student_import.success = False
        student_import.error_message = str(e)
        student_import.save()
        messages.error(request, f"Ошибка при импорте: {str(e)}")
    
    return redirect('import_students')

@login_required
def export_students_template(request):
    """Экспорт шаблона Excel для импорта студентов"""
    import io
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    
    # Создаем пример данных
    sample_data = pd.DataFrame({
        'student_id': ['STU001', 'STU002', 'STU003'],
        'first_name': ['Иван', 'Мария', 'Петр'],
        'last_name': ['Иванов', 'Петрова', 'Сидоров'],
        'group': ['ИСТ-21', 'ИСТ-21', 'ИСТ-22'],
        'email': ['ivan@example.com', 'maria@example.com', 'petr@example.com']
    })
    
    # Создаем Excel файл
    wb = Workbook()
    ws = wb.active
    ws.title = "Студенты"
    
    # Добавляем данные
    for r in dataframe_to_rows(sample_data, index=False, header=True):
        ws.append(r)
    
    # Настраиваем ширину колонок
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Подготавливаем ответ
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="students_template.xlsx"'
    return response

# ----------------------
# Утилиты
# ----------------------

def get_random_questions(exam_subject):
    """Случайные вопросы для экзамена"""
    def random_subset(queryset, count):
        ids = list(queryset.values_list('id', flat=True))
        if not ids:
            return []
        return list(Question.objects.filter(id__in=random.sample(ids, min(len(ids), count))))

    questions = []
    subject = exam_subject.subject
    
    # Легкие вопросы
    if exam_subject.easy_count > 0:
        easy_questions = random_subset(
            Question.objects.filter(subject=subject, difficulty='easy'), 
            exam_subject.easy_count
        )
        questions.extend(easy_questions)
    
    # Средние вопросы
    if exam_subject.medium_count > 0:
        medium_questions = random_subset(
            Question.objects.filter(subject=subject, difficulty='medium'), 
            exam_subject.medium_count
        )
        questions.extend(medium_questions)
    
    # Сложные вопросы
    if exam_subject.hard_count > 0:
        hard_questions = random_subset(
            Question.objects.filter(subject=subject, difficulty='hard'), 
            exam_subject.hard_count
        )
        questions.extend(hard_questions)
    
    return questions