# debug_templates.py - файл для диагностики
import os
import django
from pathlib import Path

def check_django_setup():
    """Проверяем настройку Django"""
    print("🔧 Настройка Django...")
    
    # Устанавливаем переменную окружения
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'exam_system.settings')
    
    try:
        django.setup()
        print("✅ Django настроен успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка настройки Django: {e}")
        return False

def check_file_structure():
    """Проверяем структуру файлов"""
    print("\n📁 Проверка структуры файлов...")
    
    BASE_DIR = Path(__file__).resolve().parent
    print(f"Базовая директория: {BASE_DIR}")
    
    required_files = {
        'manage.py': BASE_DIR / 'manage.py',
        'settings.py': BASE_DIR / 'exam_system' / 'settings.py',
        'templates/': BASE_DIR / 'templates',
        'templates/base.html': BASE_DIR / 'templates' / 'base.html',
        'templates/exams/': BASE_DIR / 'templates' / 'exams',
        'exams/models.py': BASE_DIR / 'exams' / 'models.py',
    }
    
    for name, path in required_files.items():
        if path.exists():
            print(f"✅ {name}: {path}")
        else:
            print(f"❌ ОТСУТСТВУЕТ {name}: {path}")
    
    return BASE_DIR

def check_templates_in_settings():
    """Проверяем настройки шаблонов"""
    print("\n⚙️  Проверка настроек шаблонов...")
    
    try:
        from django.conf import settings
        
        print(f"BASE_DIR: {settings.BASE_DIR}")
        print(f"TEMPLATES настройки:")
        
        for i, template_setting in enumerate(settings.TEMPLATES):
            print(f"  Шаблонизатор {i+1}:")
            print(f"    BACKEND: {template_setting.get('BACKEND')}")
            print(f"    DIRS: {template_setting.get('DIRS')}")
            print(f"    APP_DIRS: {template_setting.get('APP_DIRS')}")
        
        # Проверяем существование папок из DIRS
        for template_setting in settings.TEMPLATES:
            dirs = template_setting.get('DIRS', [])
            for template_dir in dirs:
                if Path(template_dir).exists():
                    print(f"✅ Папка шаблонов существует: {template_dir}")
                    # Показываем содержимое
                    try:
                        files = list(Path(template_dir).rglob('*.html'))
                        print(f"    Найдено шаблонов: {len(files)}")
                        for file in files[:5]:  # показываем первые 5
                            print(f"      - {file.relative_to(template_dir)}")
                        if len(files) > 5:
                            print(f"      ... и еще {len(files) - 5}")
                    except Exception as e:
                        print(f"    Ошибка чтения содержимого: {e}")
                else:
                    print(f"❌ Папка шаблонов НЕ существует: {template_dir}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка проверки настроек: {e}")
        return False

def test_template_loading():
    """Тестируем загрузку шаблонов"""
    print("\n🧪 Тестирование загрузки шаблонов...")
    
    try:
        from django.template.loader import get_template
        from django.template import TemplateDoesNotExist
        
        templates_to_test = [
            'base.html',
            'exams/student_login.html',
            'exams/exam_list.html'
        ]
        
        for template_name in templates_to_test:
            try:
                template = get_template(template_name)
                print(f"✅ {template_name} - загружен успешно")
                print(f"   Путь: {template.origin.name}")
            except TemplateDoesNotExist as e:
                print(f"❌ {template_name} - НЕ НАЙДЕН")
                print(f"   Ошибка: {e}")
                # Показываем где Django искал
                if hasattr(e, 'tried'):
                    print("   Django искал в:")
                    for attempt in e.tried:
                        print(f"     - {attempt}")
            except Exception as e:
                print(f"❌ {template_name} - ОШИБКА: {e}")
    
    except ImportError as e:
        print(f"❌ Не удалось импортировать Django template loader: {e}")

def create_missing_templates():
    """Создаем отсутствующие шаблоны"""
    print("\n🛠️  Создание отсутствующих файлов...")
    
    BASE_DIR = Path(__file__).resolve().parent
    templates_dir = BASE_DIR / 'templates'
    exams_templates_dir = templates_dir / 'exams'
    
    # Создаем папки
    templates_dir.mkdir(exist_ok=True)
    exams_templates_dir.mkdir(exist_ok=True)
    
    print(f"✅ Созданы папки: {templates_dir}")
    print(f"✅ Созданы папки: {exams_templates_dir}")
    
    # Создаем базовый шаблон
    base_template = templates_dir / 'base.html'
    if not base_template.exists():
        base_content = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Система Экзаменов{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container">
        {% if messages %}
            {% for message in messages %}
                <div class="alert alert-{{ message.tags }} mt-3">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% block content %}
        {% endblock %}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>'''
        
        base_template.write_text(base_content, encoding='utf-8')
        print(f"✅ Создан base.html: {base_template}")
    
    # Создаем шаблон входа
    login_template = exams_templates_dir / 'student_login.html'
    if not login_template.exists():
        login_content = '''{% extends 'base.html' %}

{% block title %}Вход студента{% endblock %}

{% block content %}
<div class="row justify-content-center mt-5">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="text-center">Вход для студентов</h3>
            </div>
            <div class="card-body">
                <form method="post">
                    {% csrf_token %}
                    <div class="mb-3">
                        <label for="student_id" class="form-label">Студенческий ID</label>
                        <input type="text" class="form-control" id="student_id" name="student_id" required>
                    </div>
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">Войти</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''
        
        login_template.write_text(login_content, encoding='utf-8')
        print(f"✅ Создан student_login.html: {login_template}")
    
    # Создаем шаблон списка экзаменов
    exam_list_template = exams_templates_dir / 'exam_list.html'
    if not exam_list_template.exists():
        exam_list_content = '''{% extends 'base.html' %}

{% block title %}Мои экзамены{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <h2>Доступные экзамены</h2>
        {% if exam_data %}
            {% for data in exam_data %}
            <div class="card mb-3">
                <div class="card-body">
                    <h5 class="card-title">{{ data.exam.name }}</h5>
                    <p class="card-text">{{ data.exam.description }}</p>
                    {% if data.can_take %}
                        <a href="{% url 'start_exam' data.exam.id %}" class="btn btn-primary">Начать экзамен</a>
                    {% else %}
                        <button class="btn btn-secondary" disabled>Недоступно</button>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        {% else %}
            <p>Нет доступных экзаменов</p>
        {% endif %}
    </div>
</div>
{% endblock %}'''
        
        exam_list_template.write_text(exam_list_content, encoding='utf-8')
        print(f"✅ Создан exam_list.html: {exam_list_template}")

def main():
    """Главная функция диагностики"""
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ ШАБЛОНОВ")
    print("=" * 50)
    
    # Проверяем файлы
    BASE_DIR = check_file_structure()
    
    # Создаем недостающие шаблоны
    create_missing_templates()
    
    # Настраиваем Django
    if not check_django_setup():
        print("\n❌ Не удалось настроить Django. Проверьте settings.py")
        return
    
    # Проверяем настройки
    if not check_templates_in_settings():
        return
    
    # Тестируем загрузку
    test_template_loading()
    
    print("\n" + "=" * 50)
    print("✅ Диагностика завершена!")
    print("\nТеперь попробуйте запустить сервер:")
    print("python manage.py runserver")

if __name__ == "__main__":
    main()