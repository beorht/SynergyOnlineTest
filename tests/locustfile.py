"""
Locust load test for ExamsOnline.

Usage:
    locust -f tests/locustfile.py --host=http://localhost:8000

With headless mode (150 users, 10 spawn/sec, 3 min run):
    locust -f tests/locustfile.py --host=http://localhost:8000 \
           --users 150 --spawn-rate 10 --run-time 3m --headless

Student IDs are read from tests/student_ids.txt (one per line).
If the file is missing, STUDENT_IDS list below is used as fallback.
"""

import json
import random
import re
import os
from pathlib import Path

from locust import HttpUser, task, between, events
from locust.exception import StopUser

# ---------------------------------------------------------------------------
# Student IDs — замените реальными ID из вашей БД или заполните student_ids.txt
# ---------------------------------------------------------------------------
FALLBACK_STUDENT_IDS = [
    "STU001", "STU002", "STU003", "STU004", "STU005",
    "STU006", "STU007", "STU008", "STU009", "STU010",
]

_ids_file = Path(__file__).parent / "student_ids.txt"
if _ids_file.exists():
    STUDENT_IDS = [line.strip() for line in _ids_file.read_text().splitlines() if line.strip()]
else:
    STUDENT_IDS = FALLBACK_STUDENT_IDS


def _extract_csrf(html: str) -> str:
    """Извлекает csrfmiddlewaretoken из HTML-формы."""
    match = re.search(r'csrfmiddlewaretoken["\s]+value=["\']([^"\']+)', html)
    if match:
        return match.group(1)
    # Fallback: из cookie
    return ""


# ---------------------------------------------------------------------------
# Основной пользователь — полный цикл экзамена
# ---------------------------------------------------------------------------

class ExamStudent(HttpUser):
    """
    Эмулирует студента: логин → список экзаменов → прохождение → результат.
    wait_time отражает реальное поведение: студент думает 10-30 сек между ответами.
    """
    wait_time = between(10, 30)

    def on_start(self):
        """Вызывается один раз при старте каждого виртуального пользователя."""
        self.student_id = random.choice(STUDENT_IDS)
        self.csrf_token = ""
        self.exam_result_id = None
        self.student_answers = []  # список {id, question_type, answer_ids}
        self.answered_count = 0

        self._login()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _login(self):
        # Получаем страницу логина для CSRF
        resp = self.client.get("/", name="/login (GET)")
        if resp.status_code != 200:
            self.environment.runner.quit()
            raise StopUser()

        self.csrf_token = _extract_csrf(resp.text) or self.client.cookies.get("csrftoken", "")

        resp = self.client.post(
            "/",
            data={
                "student_id": self.student_id,
                "csrfmiddlewaretoken": self.csrf_token,
            },
            headers={"Referer": self.host + "/"},
            name="/login (POST)",
            allow_redirects=True,
        )

        # После логина должны попасть на /exams/
        if "/exams/" not in resp.url and "exam_list" not in resp.text:
            # Студент не найден в БД — пропускаем
            raise StopUser()

    # ------------------------------------------------------------------
    # Tasks — выполняются по весам (чем больше число, тем чаще)
    # ------------------------------------------------------------------

    @task(1)
    def view_exam_list(self):
        """Просмотр списка экзаменов — самый частый запрос."""
        resp = self.client.get("/exams/", name="/exams/")
        if resp.status_code != 200:
            return

        # Если ещё нет начатого экзамена — пробуем начать
        if self.exam_result_id is None:
            self._try_start_exam(resp.text)

    @task(5)
    def save_answer(self):
        """
        Сохранение ответа — самый горячий endpoint.
        Вес 5: выполняется в 5 раз чаще, чем view_exam_list.
        Эмулирует автосохранение + ручной ответ студента.
        """
        if not self.student_answers or self.exam_result_id is None:
            return

        # Берём следующий неотвеченный вопрос (или случайный уже отвеченный)
        unanswered = [a for a in self.student_answers if not a.get("answered")]
        target = unanswered[0] if unanswered else random.choice(self.student_answers)

        payload = self._build_answer_payload(target)

        resp = self.client.post(
            f"/exams/answer/{self.exam_result_id}/",
            data=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": self.csrf_token,
                "Referer": f"{self.host}/exams/take/{self.exam_result_id}/",
            },
            name="/exams/answer/[id]/",
        )

        if resp.status_code == 200:
            target["answered"] = True
            self.answered_count += 1

        # Если все вопросы отвечены — завершаем экзамен
        if self.answered_count >= len(self.student_answers):
            self._finish_exam()

    @task(1)
    def view_results_list(self):
        """Просмотр истории результатов."""
        self.client.get("/exams/results/", name="/exams/results/")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _try_start_exam(self, html: str):
        """Ищет доступный экзамен в HTML и начинает его."""
        # Ищем ссылки вида /exams/start/123/
        exam_ids = re.findall(r'/exams/start/(\d+)/', html)
        if not exam_ids:
            return

        exam_id = exam_ids[0]
        resp = self.client.get(
            f"/exams/start/{exam_id}/",
            name="/exams/start/[id]/",
            allow_redirects=True,
        )

        # После старта редирект на /exams/take/<result_id>/
        match = re.search(r'/exams/take/(\d+)/', resp.url)
        if match:
            self.exam_result_id = int(match.group(1))
            self._load_student_answers(resp.text)

    def _load_student_answers(self, html: str):
        """
        Извлекает student_answer_id и типы вопросов из страницы экзамена.
        Ожидает data-атрибуты: data-answer-id, data-question-type, data-answer-ids.
        """
        # Ищем data-answer-id="123"
        answer_ids = re.findall(r'data-answer-id=["\'](\d+)["\']', html)
        qtypes = re.findall(r'data-question-type=["\']([^"\']+)["\']', html)
        # Для multiple_choice ищем варианты ответов в data-answer-ids="[1,2,3]"
        answer_options = re.findall(r'data-answer-ids=["\'](\[[^\]]*\])["\']', html)

        self.student_answers = []
        for i, aid in enumerate(answer_ids):
            qtype = qtypes[i] if i < len(qtypes) else "single_choice"
            options_raw = answer_options[i] if i < len(answer_options) else "[]"
            try:
                options = json.loads(options_raw)
            except json.JSONDecodeError:
                options = []

            self.student_answers.append({
                "id": int(aid),
                "question_type": qtype,
                "answer_options": options,
                "answered": False,
            })

    def _build_answer_payload(self, answer: dict) -> dict:
        """Формирует payload для save_answer в зависимости от типа вопроса."""
        qtype = answer.get("question_type", "single_choice")
        options = answer.get("answer_options", [])

        if qtype in ("open", "text"):
            return {
                "student_answer_id": answer["id"],
                "answer_text": "Тестовый ответ от Locust",
                "answer_ids": [],
            }
        elif qtype == "multiple_choice":
            # Выбираем 1-2 случайных варианта
            selected = random.sample(options, min(len(options), random.randint(1, 2))) if options else []
            return {
                "student_answer_id": answer["id"],
                "answer_ids": selected,
                "answer_text": "",
            }
        else:  # single_choice
            selected = [random.choice(options)] if options else []
            return {
                "student_answer_id": answer["id"],
                "answer_ids": selected,
                "answer_text": "",
            }

    def _finish_exam(self):
        """Завершает экзамен и переходит к результатам."""
        if self.exam_result_id is None:
            return

        self.client.post(
            f"/exams/finish/{self.exam_result_id}/",
            data=json.dumps({"exam_result_id": self.exam_result_id}),
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": self.csrf_token,
                "Referer": f"{self.host}/exams/take/{self.exam_result_id}/",
            },
            name="/exams/finish/[id]/",
        )

        # Смотрим результат
        self.client.get(
            f"/exams/results/{self.exam_result_id}/",
            name="/exams/results/[id]/",
        )

        # Сбрасываем состояние — пользователь завершил экзамен
        self.exam_result_id = None
        self.student_answers = []
        self.answered_count = 0


# ---------------------------------------------------------------------------
# Лёгкий пользователь — только просматривает список (не сдаёт экзамен)
# Полезно для имитации студентов в режиме ожидания
# ---------------------------------------------------------------------------

class IdleStudent(HttpUser):
    """Студент, который залогинился, но экзамен ещё не начался."""
    wait_time = between(30, 60)
    weight = 1  # ExamStudent:IdleStudent ~ 3:1 (см. ниже)

    def on_start(self):
        self.student_id = random.choice(STUDENT_IDS)
        resp = self.client.get("/", name="/login (GET)")
        csrf = _extract_csrf(resp.text) or self.client.cookies.get("csrftoken", "")
        self.client.post(
            "/",
            data={"student_id": self.student_id, "csrfmiddlewaretoken": csrf},
            headers={"Referer": self.host + "/"},
            name="/login (POST)",
            allow_redirects=True,
        )

    @task
    def poll_exam_list(self):
        """Периодически обновляет список экзаменов."""
        self.client.get("/exams/", name="/exams/ (idle)")


# Веса пользователей: 75% активно сдают, 25% ждут
ExamStudent.weight = 3
IdleStudent.weight = 1


# ---------------------------------------------------------------------------
# Хук: выводит итоговую статистику по критичным endpoints
# ---------------------------------------------------------------------------

@events.quitting.add_listener
def on_quit(environment, **kwargs):
    stats = environment.stats
    critical = ["/exams/answer/[id]/", "/exams/start/[id]/", "/exams/", "/login (POST)"]
    print("\n=== Критичные endpoints ===")
    for name in critical:
        entry = stats.entries.get((name, "POST")) or stats.entries.get((name, "GET"))
        if entry:
            print(
                f"{name:40s} | "
                f"RPS: {entry.current_rps:.1f} | "
                f"avg: {entry.avg_response_time:.0f}ms | "
                f"p95: {entry.get_response_time_percentile(0.95):.0f}ms | "
                f"fail: {entry.fail_ratio * 100:.1f}%"
            )
