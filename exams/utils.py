DIFFICULTY_LABELS = {'easy': 'Лёгкие', 'medium': 'Средние', 'hard': 'Сложные'}


def compute_result_stats(student_answers):
    """Статистика по предметам и по сложности для детального отчёта попытки."""
    subject_stats = {}
    difficulty_stats = {
        diff: {'correct': 0, 'total': 0, 'points': 0, 'max_points': 0, 'label': label}
        for diff, label in DIFFICULTY_LABELS.items()
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

    return subject_stats, difficulty_stats
