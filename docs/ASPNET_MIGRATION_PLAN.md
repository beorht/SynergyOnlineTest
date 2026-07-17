# План: переход backend на C# ASP.NET Core

## Контекст

Текущий backend (Django/Python) был удалён из рабочей директории, оставлены только `templates/` (Django-шаблоны), `static/` (изображения) и `docs/` (документация, включая `ARCHITECTURE.md` и `DATABASE.md`, которые полностью описывают удалённую систему). Новый backend будет написан на **C# / ASP.NET Core**. Это план разработки — код по нему ещё не писался, только структура проекта, архитектурные решения и roadmap.

Целевая архитектура подтверждена с пользователем:
- **Гибрид ASP.NET Core MVC (Razor Views) + JSON API-контроллеры** — рекомендованный вариант как наиболее оптимальный: большинство страниц (список экзаменов, прохождение, результаты, дашборд преподавателя) рендерятся сервером через Razor, максимально близко к текущему поведению Django-шаблонов и с минимумом инфраструктуры; отдельные AJAX-операции (автосохранение ответа, завершение экзамена, таймер) идут через тонкие API-контроллеры, возвращающие JSON — прямой аналог `save_answer`/`finish_exam` в `exams/views.py`. Это даёт наименьший риск и объём работы для MVP, но не закрывает дорогу к отделению фронтенда в SPA в будущем (JSON-эндпоинты уже будут существовать).
- **PostgreSQL** — та же СУБД, что и раньше (через провайдер Npgsql), чтобы не требовать миграции данных/инфраструктуры.
- **Аутентификация**: студент — как сейчас, вход по `student_id` без пароля (cookie-схема с claims, без ASP.NET Identity); преподаватель/админ — через **ASP.NET Core Identity** с ролями (`Teacher`, `Admin`), что сильнее текущей Django-реализации (там просто `is_staff`).

## Структура решения (Solution)

```
SynergyExam/
├── SynergyExam.sln
├── src/
│   ├── SynergyExam.Web/                 # ASP.NET Core MVC + Razor + API-контроллеры (entry point)
│   │   ├── Controllers/
│   │   │   ├── StudentAuthController.cs     # аналог exams.student_login / student_logout
│   │   │   ├── ExamController.cs            # exam_list, start_exam, take_exam
│   │   │   ├── ResultsController.cs         # exam_results_list, exam_result_detail
│   │   │   ├── Api/AnswerApiController.cs   # save_answer, finish_exam (JSON, AJAX)
│   │   │   ├── TeacherAuthController.cs     # teacher_login/logout (Identity)
│   │   │   ├── TeacherDashboardController.cs# teacher_dashboard, export_results_excel
│   │   │   ├── TeacherReviewController.cs   # teacher_review, teacher_result_detail
│   │   │   └── Admin/                       # аналог Django admin (см. раздел ниже)
│   │   │       ├── CoursesController.cs
│   │   │       ├── SubjectsController.cs
│   │   │       ├── QuestionsController.cs
│   │   │       ├── ExamsController.cs
│   │   │       ├── StudentsController.cs
│   │   │       └── StudentImportController.cs  # import-students, export-template
│   │   ├── Views/
│   │   │   ├── Shared/_Layout.cshtml        # из templates/base.html
│   │   │   ├── StudentAuth/Login.cshtml     # из exams/student_login.html
│   │   │   ├── Exam/List.cshtml             # из exams/exam_list.html
│   │   │   ├── Exam/Take.cshtml             # из exams/take_exam.html
│   │   │   ├── Results/List.cshtml          # из exams/exam_results_list.html
│   │   │   ├── Results/Detail.cshtml        # из exams/exam_result_detail.html (+ is_teacher_view флаг)
│   │   │   ├── Results/NoAttempts.cshtml    # из exams/no_attempts.html
│   │   │   ├── Teacher/Login.cshtml
│   │   │   ├── Teacher/Dashboard.cshtml
│   │   │   ├── Teacher/Review.cshtml
│   │   │   └── Admin/                       # уже спроектированы как Django-шаблоны в templates/admin/ (см. ниже)
│   │   │       ├── _Sidebar.cshtml / BaseAdmin.cshtml
│   │   │       ├── Dashboard.cshtml
│   │   │       ├── Courses/List.cshtml, Form.cshtml
│   │   │       ├── Subjects/List.cshtml, Form.cshtml
│   │   │       ├── Questions/List.cshtml, Form.cshtml  (динамические Answer/Keyword строки)
│   │   │       ├── Exams/List.cshtml, Form.cshtml       (динамические ExamSubject строки + live-подсчёт баллов)
│   │   │       ├── Students/List.cshtml, Form.cshtml
│   │   │       └── Import/Index.cshtml
│   │   ├── wwwroot/                     # из static/ (images/…)
│   │   ├── Program.cs                   # composition root: DI, auth schemes, EF, middleware
│   │   ├── appsettings.json / appsettings.Development.json
│   │   └── SynergyExam.Web.csproj
│   │
│   ├── SynergyExam.Domain/              # сущности, enum'ы, интерфейсы доменных сервисов
│   │   ├── Entities/
│   │   │   ├── Student.cs, Course.cs, CourseStudent.cs, Subject.cs
│   │   │   ├── Question.cs, Answer.cs
│   │   │   ├── Exam.cs, ExamSubject.cs, ExamResult.cs
│   │   │   ├── StudentAnswer.cs, AnswerOrder.cs, StudentImport.cs
│   │   │   ├── Teacher.cs, QuestionKeyword.cs, ApplicationUser.cs (: IdentityUser)
│   │   ├── Enums/ Difficulty.cs, QuestionType.cs, ExamResultStatus.cs
│   │   └── Interfaces/ IQuestionSelectionService.cs, IAnswerGradingService.cs, IResultStatsService.cs, IExcelImportService.cs, IExcelExportService.cs
│   │
│   ├── SynergyExam.Infrastructure/      # EF Core, реализации сервисов, интеграции
│   │   ├── Data/
│   │   │   ├── AppDbContext.cs          # DbSet'ы + Fluent API конфигурация (unique constraints, relations)
│   │   │   └── Migrations/              # EF Core Code-First миграции
│   │   ├── Identity/                    # конфигурация ASP.NET Core Identity (Npgsql store)
│   │   └── Services/
│   │       ├── QuestionSelectionService.cs   # аналог get_random_questions()
│   │       ├── AnswerGradingService.cs       # аналог check_answer_correctness()
│   │       ├── ResultStatsService.cs         # аналог exams/utils.py::compute_result_stats
│   │       ├── ExcelStudentImportService.cs  # аналог process_excel_import (ClosedXML)
│   │       └── ExcelResultsExportService.cs  # аналог export_results_excel (ClosedXML)
│   │
│   └── SynergyExam.Tests/               # xUnit + WebApplicationFactory (интеграционные) + Moq (юнит)
│       ├── AnswerOrderShuffleTests.cs   # аналог tests/test_shuffle.py
│       ├── KeywordGradingTests.cs       # аналог tests/test_keywords.py
│       ├── TeacherViewsTests.cs         # аналог tests/test_teacher_views.py
│       └── ResultDetailTests.cs         # аналог tests/test_result_detail.py
│
└── docs/
    ├── ARCHITECTURE.md / DATABASE.md    # текущие (Django, для истории/референса при переносе бизнес-логики)
    └── (новые ASPNET_ARCHITECTURE.md / ASPNET_DATABASE.md — пишутся по факту реализации, не на этапе плана)
```

## Маппинг доменной модели (Django → EF Core)

Полное описание исходных полей — в `docs/DATABASE.md`. Прямой перенос 1:1, с уточнениями под .NET/EF Core:

| Django модель | EF Core сущность | Замечания |
|---|---|---|
| `Student` | `Student` | `StudentId` unique index; без связи с Identity |
| `Course`, `CourseStudent`, `Subject` | так же | `CourseStudent` — join-сущность (explicit many-to-many) |
| `Question` | `Question` | `Difficulty`, `QuestionType` — enum'ы вместо `CharField(choices=...)` |
| `Answer` | `Answer` | |
| `Exam`, `ExamSubject` | так же | методы `IsOpen()`, `EffectiveMediumCount()`, `MaxScore()` — как computed-свойства/методы сущности или в сервисе |
| `ExamResult` | `ExamResult` | `Questions` — M2M через join-таблицу `ExamResultQuestion` (EF Core 5+ поддерживает implicit many-to-many, но лучше явная join-таблица для читаемости) |
| `StudentAnswer` | `StudentAnswer` | `SelectedAnswers` M2M → `Answer`; `EffectivePoints` — computed property |
| `AnswerOrder` | `AnswerOrder` | поле `Order` — `List<int>`, маппится на Postgres `jsonb` через `Npgsql` value converter |
| `StudentImport` | `StudentImport` | файл — хранить путь/blob через `IFormFile` → диск или объектное хранилище (уточнить при реализации) |
| `Teacher` (teachers app) | `Teacher` | `UserId` FK → `ApplicationUser` (1:1), вместо голого `auth.User` |
| `QuestionKeyword` | `QuestionKeyword` | |
| `django.contrib.auth.User` | `ApplicationUser : IdentityUser` | роли `Teacher`/`Admin` через `IdentityRole` |

Уникальные ограничения переносятся как EF Core `HasIndex(...).IsUnique()`: `Student.StudentId`, `(CourseStudent.CourseId, CourseStudent.StudentId)`, `(ExamSubject.ExamId, ExamSubject.SubjectId)`, `(StudentAnswer.ExamResultId, StudentAnswer.QuestionId)`.

## Перенос бизнес-логики (по разделам `docs/ARCHITECTURE.md`)

**Студенческий флоу** (`exams` → `ExamController`/`ResultsController`/`Api/AnswerApiController`):
- Вход по `student_id` → кастомная cookie auth-схема (claims: `StudentId`, `FullName`), `ExpireTimeSpan = 8h`, `SlidingExpiration = true` (аналог `SESSION_COOKIE_AGE=28800` + `SESSION_SAVE_EVERY_REQUEST=True`)
- `ExamList` — те же аннотации через LINQ (`Count`/`Where` вместо Django `annotate`/`Prefetch`)
- `StartExam` — атомарная транзакция через `AppDbContext.Database.BeginTransactionAsync()`, генерация вопросов через `QuestionSelectionService` (порт `get_random_questions`), создание `ExamResult`+`StudentAnswer`+`AnswerOrder`
- `SaveAnswer`/`FinishExam` — JSON API-эндпоинты (`[ApiController]`), с anti-forgery токеном вместо Django `@csrf_exempt` (осознанное улучшение — в Django это отмечено как техдолг)
- `AnswerGradingService` — порт `check_answer_correctness`: точное совпадение множества ID для choice-вопросов, keyword substring-match (case-sensitive флаг) для open/text

**Преподавательский флоу** (`teachers` → `TeacherDashboardController`/`TeacherReviewController`):
- Вход — ASP.NET Core Identity (`SignInManager`), проверка роли `Teacher`/`Admin` вместо `is_staff`
- Dashboard — сортировка/pending-count через LINQ `GroupBy`/`Count`
- `ExcelResultsExportService` (ClosedXML) — форматированный экспорт: заливки по проценту, чередование строк, заморозка шапки — прямой аналог openpyxl-кода в `export_results_excel`
- `TeacherReview` — override `TeacherScore`/`TeacherComment`, `ExamResult.RecalculateScore()`

**Импорт студентов из Excel** (`import_students_view`/`process_excel_import`):
- `ExcelStudentImportService` на **ClosedXML** (MIT-лицензия, замена pandas+openpyxl) — чтение по заголовкам колонок (`student_id`, `first_name`, `last_name`, `group`, `email`), upsert через EF Core, лог в `StudentImport`

**Административная панель** (замена Django admin — самый объёмный новый кусок работы):
Django admin бесплатно даёт CRUD+фильтры+поиск для `Student`, `Course`, `Subject`, `Question`+`Answer` (inline), `Exam`+`ExamSubject` (inline), `ExamResult`, `StudentImport`. В ASP.NET такого готового решения нет — нужно либо:
1. Вручную сделать MVC CRUD-контроллеры/Razor-формы для каждой сущности (наибольший объём работы в проекте), либо
2. Использовать генератор `dotnet-aspnet-codegenerator` для быстрого скаффолда базового CRUD, затем дорабатывать (inline-редактирование Answer внутри Question, ExamSubject внутри Exam).
Это стоит закладывать как отдельную, самую крупную фазу разработки.

**Фронтенд-дизайн админки уже готов** (сделан заранее, до старта backend-разработки) — см. `templates/admin/`:
- `_sidebar.html` + `base_admin.html` — общий каркас (левый сайдбар + белая "main-container" карточка контента), стилистика продолжает `templates/teachers/*` и общий `base.html` (Bootstrap 5, FontAwesome, фирменный фиолетовый градиент `#667eea → #764ba2` как акцент админки)
- `dashboard.html` — обзор: KPI-плитки (курсы/предметы/вопросы/открытые экзамены/на проверке/студенты) + карточки быстрого перехода в разделы + последняя активность
- `courses/list.html`, `courses/form.html` — CRUD курсов, поиск, модалка подтверждения удаления (`_delete_modal.html` + `_delete_modal_script.html`, переиспользуется во всех списках)
- `subjects/list.html`, `subjects/form.html` — CRUD предметов, фильтр по курсу, чипы распределения по сложности (Л/С/Т — аналог Django admin `get_difficulty_distribution`)
- `questions/list.html`, `questions/form.html` — CRUD вопросов с фильтрами (предмет/сложность/тип), в форме — динамические строки вариантов ответа (add/remove, чекбокс "правильный") и ключевых слов, переключаемые JS в зависимости от `question_type` (choice vs open/text) — аналог `AnswerInline` + `QuestionKeywordInline`
- `exams/list.html`, `exams/form.html` — CRUD экзаменов со статус-бэйджем (открыт/ожидается/закрыт), в форме — динамические строки `ExamSubject` (кол-во/баллы по сложности) с live-пересчётом итогового числа вопросов и максимального балла на JS — аналог `ExamSubjectInline` + `Exam.max_score()`
- `students/list.html`, `students/form.html` — CRUD студентов, поиск, фильтр по группе, переключатель активности
- `import/index.html` — тот же импорт из Excel, что и раньше (`exams/import_students.html`), встроенный в общий каркас админки

Интерактивный превью (клиентский HTML-макет с теми же классами/токенами, без бэкенда) был опубликован как Artifact для визуальной проверки дизайна до начала разработки backend.

## Фазы разработки (roadmap)

1. **Скелет решения**: `SynergyExam.sln`, 4 проекта, EF Core + Npgsql, ASP.NET Core Identity, первая миграция БД по схеме из `DATABASE.md`, health-check главной страницы
2. **Студенческий флоу**: логин по ID, список экзаменов, прохождение (`StartExam`/`TakeExam`), автосохранение ответа (API), таймер на фронте (JS, аналог текущего JS в `take_exam.html`)
3. **Движок оценивания**: `QuestionSelectionService`, `AnswerGradingService`, `FinishExam`, детальный отчёт (`ResultStatsService`)
4. **Преподавательский флоу**: Identity-логин, дашборд, review открытых ответов, `recalculate_score`
5. **Excel импорт/экспорт**: `ExcelStudentImportService`, `ExcelResultsExportService`, шаблон импорта
6. **Админ-панель**: CRUD для Course/Subject/Question/Answer/Exam/ExamSubject/Student/StudentImport
7. **Импорт банка вопросов**: консольная утилита/management-подобная команда (`dotnet run --project tools/ImportQuestions`) — порт `import_questions` для `docs/test/*.json`
8. **Тесты**: xUnit-аналоги 4 существующих тестовых файлов + integration-тесты через `WebApplicationFactory`
9. **Развёртывание**: Kestrel (+ reverse proxy, если нужен), `appsettings`+env vars вместо `.env`/hardcoded `SECRET_KEY` (использовать `dotnet user-secrets`/env vars с самого начала — закрывает текущий техдолг)

## Ключевые NuGet-пакеты

- `Microsoft.AspNetCore.Identity.EntityFrameworkCore`
- `Npgsql.EntityFrameworkCore.PostgreSQL`
- `Microsoft.EntityFrameworkCore.Design`
- `ClosedXML` — чтение/запись `.xlsx` (замена pandas/openpyxl, MIT-лицензия)
- `xunit`, `Microsoft.AspNetCore.Mvc.Testing`, `Moq` (dev/test)

## Открытые вопросы для следующего шага (перед реализацией)

- Название решения/namespace (`SynergyExam` — рабочее название в плане, можно поменять)
- Формат хранения загруженных Excel-файлов (`StudentImport.UploadedFile`) — локальный диск / облако
- Нужен ли Docker Compose для локального Postgres при разработке

## Верификация плана (после начала реализации)

- Каждая фаза должна закрываться прогоном xUnit-тестов, портирующих текущие `tests/*.py` сценарии (shuffle-стабильность, keyword-грейдинг, teacher views, result detail)
- Ручная сверка UX с текущими Django-шаблонами в `templates/` (они остаются в репозитории как референс) — страница за страницей
- В конце — сверка структуры БД с `docs/DATABASE.md` (миграция EF Core должна породить эквивалентную схему)
