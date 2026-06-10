from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q

from exams.models import ExamResult, StudentAnswer, ExamSubject


def teacher_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('teacher_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect('teacher_dashboard')
        messages.error(request, 'Неверный логин/пароль или недостаточно прав')

    return render(request, 'teachers/login.html')


def teacher_logout(request):
    logout(request)
    return redirect('teacher_login')


@staff_member_required(login_url='/teacher/login/')
def teacher_dashboard(request):
    sort = request.GET.get('sort', 'date')

    sort_map = {
        'date':    '-start_time',
        'student': 'student__last_name',
        'exam':    'exam__name',
        'score':   '-score',
        'pending': '-pending_count',
    }

    results = list(
        ExamResult.objects.exclude(status='in_progress')
        .select_related('student', 'exam', 'exam__course')
        .prefetch_related('student_answers__question')
        .annotate(
            pending_count=Count(
                'student_answers',
                filter=Q(
                    student_answers__is_correct__isnull=True,
                    student_answers__question__question_type__in=['open', 'text']
                )
            )
        )
        .order_by(sort_map.get(sort, '-start_time'))
    )

    diff_labels = {'easy': 'Лёгкие', 'medium': 'Средние', 'hard': 'Сложные'}
    for result in results:
        stats = {k: {'correct': 0, 'total': 0, 'points': 0, 'label': v}
                 for k, v in diff_labels.items()}
        for sa in result.student_answers.all():
            d = sa.question.difficulty
            if d in stats:
                stats[d]['total'] += 1
                if sa.is_correct:
                    stats[d]['correct'] += 1
                stats[d]['points'] += sa.effective_points
        result.difficulty_stats = {k: v for k, v in stats.items() if v['total'] > 0}

    return render(request, 'teachers/dashboard.html', {
        'results': results,
        'current_sort': sort,
        'sort_options': {
            'date':    'По дате',
            'score':   'По баллам',
            'student': 'По студенту',
            'exam':    'По экзамену',
            'pending': 'Непроверенные первые',
        },
    })


@staff_member_required(login_url='/teacher/login/')
def teacher_review(request, exam_result_id):
    exam_result = get_object_or_404(ExamResult, pk=exam_result_id)

    open_answers = exam_result.student_answers.filter(
        question__question_type__in=['open', 'text']
    ).select_related('question', 'question__subject', 'reviewed_by')

    if request.method == 'POST':
        for sa in open_answers:
            score_key = f'score_{sa.id}'
            comment_key = f'comment_{sa.id}'
            score_val = request.POST.get(score_key, '').strip()
            comment_val = request.POST.get(comment_key, '').strip()

            if score_val != '':
                try:
                    sa.teacher_score = float(score_val)
                except ValueError:
                    pass
            else:
                sa.teacher_score = None

            sa.teacher_comment = comment_val
            sa.reviewed_at = timezone.now()
            if hasattr(request.user, 'teacher_profile'):
                sa.reviewed_by = request.user.teacher_profile
            sa.save()

        exam_result.recalculate_score()
        messages.success(request, 'Оценки сохранены, итоговый балл пересчитан.')
        return redirect('teacher_review', exam_result_id=exam_result_id)

    for sa in open_answers:
        es = ExamSubject.objects.filter(
            exam=exam_result.exam, subject=sa.question.subject
        ).first()
        if es:
            if sa.question.difficulty == 'easy':
                sa.max_points = es.easy_points
            elif sa.question.difficulty == 'medium':
                sa.max_points = es.medium_points
            else:
                sa.max_points = es.hard_points
        else:
            sa.max_points = 0

    return render(request, 'teachers/review.html', {
        'exam_result': exam_result,
        'open_answers': open_answers,
    })


@staff_member_required(login_url='/teacher/login/')
def teacher_result_detail(request, exam_result_id):
    """Полный отчёт студента, доступный преподавателю."""
    exam_result = get_object_or_404(ExamResult, pk=exam_result_id)

    student_answers = exam_result.student_answers.select_related(
        'question', 'question__subject'
    ).prefetch_related('question__answers', 'selected_answers')

    subject_stats = {}
    difficulty_stats = {
        'easy':   {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0, 'label': 'Лёгкие'},
        'medium': {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0, 'label': 'Средние'},
        'hard':   {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0, 'label': 'Сложные'},
    }

    for answer in student_answers:
        subject = answer.question.subject.name if answer.question.subject else 'Без предмета'
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
        'is_teacher_view': True,
    })
