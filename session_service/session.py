import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

from database import get_col

logger = logging.getLogger(__name__)

# Критерии оценивания по умолчанию
_DEFAULT_CRITERIA = [
    {"threshold_gte": 80, "description": "зачтено", "is_pass_status": True},
    {"threshold_gte": 50, "description": "удовлетворительно", "is_pass_status": True},
    {"threshold_gte": 0, "description": "незачтено", "is_pass_status": False},
]


class TestSession:
    # Сессия тестирования (экспертная система)

    def __init__(
        self,
        username: str,
        questions: list,
        grading_criteria: dict,
        premade_test_id: Optional[str] = None,
        test_name: Optional[str] = None,
        time_limit_minutes: Optional[int] = None,
        grading_mode: str = "overall",
        user_role: str = "student",
    ):
        self.session_id = uuid.uuid4().hex
        self.username = username
        self.questions = [dict(q) for q in questions]
        self.grading_criteria = grading_criteria
        self.premade_test_id = premade_test_id
        self.test_name = test_name
        self.time_limit_minutes = time_limit_minutes
        self.grading_mode = grading_mode
        self.user_role = user_role
        self.user_answers: list = []
        self.current_question_index = 0
        self.results: dict = {}
        self.category_max_points: dict = {}
        self.correct_answers = 0
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.formatted_duration = ""
        self._normalize_questions()
        self._setup_categories()

    def _normalize_questions(self) -> None:
        # Нормализация формата вопросов и перемешивание вариантов
        for q in self.questions:
            if "question" not in q and "question_text" in q:
                q["question"] = q["question_text"]
            if "question" not in q and "text" in q:
                q["question"] = q["text"]
            if "correct" not in q and "correct_answer" in q:
                q["correct"] = q["correct_answer"]
            self._shuffle_options(q)

    @staticmethod
    def _shuffle_options(q: dict) -> None:
        # Перемешивание вариантов ответов
        options = q.get("options")
        if not options or len(options) <= 1:
            return
        correct = q.get("correct")
        if correct is None:
            return
        old_options = list(options)
        indices = list(range(len(old_options)))
        random.shuffle(indices)
        q["options"] = [old_options[i] for i in indices]

    # ------------------------------------------------------------------
    # Настройка
    # ------------------------------------------------------------------

    def _setup_categories(self) -> None:
        for q in self.questions:
            cat = q.get("category") or q.get("topic", "unknown")
            if cat not in self.results:
                self.results[cat] = 0
                self.category_max_points[cat] = 0
            default_pts = 2 if q.get("answer_type") == "multiple" else 1
            self.category_max_points[cat] += q.get("points", default_pts)

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def get_current_question(self) -> Optional[dict]:
        if self.current_question_index >= len(self.questions):
            return None
        q = self.questions[self.current_question_index]
        result = {
            "index": self.current_question_index,
            "question_number": self.current_question_index + 1,
            "question": q["question"],
            "options": q["options"],
            "answer_type": q.get("answer_type", "single"),
            "matrices": q.get("matrices"),
            "commands": q.get("commands"),
            "is_additional": False,
            "total_questions": len(self.questions),
        }
        if self.time_limit_minutes:
            elapsed_sec = (datetime.now() - self.start_time).total_seconds()
            result["seconds_remaining"] = max(0, int(self.time_limit_minutes * 60 - elapsed_sec))
            result["time_limit_minutes"] = self.time_limit_minutes
        return result

    def is_time_expired(self) -> bool:
        # Проверка истечения времени
        if not self.time_limit_minutes:
            return False
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return elapsed >= self.time_limit_minutes * 60

    def submit_answer(self, answer) -> dict:
        # Обработка ответа пользователя
        if self.current_question_index >= len(self.questions):
            return {"finished": True, "error": "Нет больше вопросов."}

        if self.is_time_expired():
            while self.current_question_index < len(self.questions):
                self.user_answers.append(None)
                self.current_question_index += 1
            return {"finished": True, "results": self._evaluate_and_finish(), "timed_out": True}

        q = self.questions[self.current_question_index]
        correct = q["correct"]
        answer_type = q.get("answer_type", "single")

        if answer_type == "multiple":
            is_correct = isinstance(answer, list) and isinstance(correct, list) and set(answer) == set(correct)
        else:
            is_correct = isinstance(correct, str) and (
                answer == correct
                or (isinstance(answer, list) and len(answer) == 1 and answer[0] == correct)
            )

        self.user_answers.append(answer)

        if is_correct:
            self.correct_answers += 1
            cat = self._get_category(self.current_question_index)
            if cat in self.results:
                default_pts = 2 if answer_type == "multiple" else 1
                self.results[cat] += q.get("points", default_pts)

        self.current_question_index += 1

        if self.current_question_index >= len(self.questions):
            return {"finished": True, "results": self._evaluate_and_finish()}
        return {"finished": False, "current_question": self.get_current_question()}

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def _get_category(self, index: int) -> str:
        # Получение категории вопроса
        if 0 <= index < len(self.questions):
            q = self.questions[index]
            return q.get("category") or q.get("topic", "unknown")
        return "unknown"

    # ------------------------------------------------------------------
    # Движок экспертной системы
    # ------------------------------------------------------------------

    def _get_sorted_criteria(self) -> list:
        # Получение отсортированных критериев
        rules = self.grading_criteria.get("topic_criteria") or _DEFAULT_CRITERIA
        return sorted(rules, key=lambda c: c.get("threshold_gte", 0), reverse=True)

    def _apply_criteria(self, pct: float, sorted_criteria: list) -> tuple:
        # Применение критериев оценивания
        for rule in sorted_criteria:
            if pct >= rule.get("threshold_gte", 0):
                return rule.get("description", "Статус не определен"), rule.get("is_pass_status", False)
        return "Статус не определен", False

    def _build_topics_status_raw(self) -> dict:
        # Расчёт баллов по категориям
        topics_status = {}
        for cat, max_pts in self.category_max_points.items():
            score = self.results.get(cat, 0)
            if isinstance(score, str):
                score = 0
            if max_pts > 0:
                pct = (score / max_pts) * 100
                topics_status[cat] = {
                    "score": score,
                    "total": max_pts,
                    "percentage": round(pct, 2),
                    "status": "",
                }
            else:
                topics_status[cat] = {"score": 0, "total": 0, "percentage": 0, "status": "Нет вопросов"}
        return topics_status

    def _build_answers_list(self, hide_correct: bool = False) -> list:
        # Формирование списка ответов
        answers = []
        for i, q in enumerate(self.questions):
            user_ans = self.user_answers[i] if i < len(self.user_answers) else None
            if user_ans is not None:
                if isinstance(q.get("correct"), list):
                    user_repr = sorted(set(map(str, user_ans))) if isinstance(user_ans, list) else [str(user_ans)]
                else:
                    user_repr = str(user_ans)
            else:
                user_repr = "Нет ответа"
            answer_entry = {
                "question": q["question"],
                "user_answer": user_repr,
                "category": self._get_category(i),
            }
            if not hide_correct:
                answer_entry["correct_answer"] = q["correct"]
            answers.append(answer_entry)
        return answers

    def _save_result(self, result_detail: dict) -> None:
        # Сохранение результата в БД
        try:
            get_col().insert_one(result_detail.copy())
        except Exception as e:
            logger.error("Failed to save test result for session %s: %s", self.session_id, e)

    # ------------------------------------------------------------------
    # Сериализация для MongoDB
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        # Преобразование в словарь для сохранения
        return {
            "session_id": self.session_id,
            "username": self.username,
            "questions": self.questions,
            "grading_criteria": self.grading_criteria,
            "premade_test_id": self.premade_test_id,
            "test_name": self.test_name,
            "time_limit_minutes": self.time_limit_minutes,
            "grading_mode": self.grading_mode,
            "user_role": self.user_role,
            "user_answers": self.user_answers,
            "current_question_index": self.current_question_index,
            "correct_answers": self.correct_answers,
            "results": self.results,
            "category_max_points": self.category_max_points,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TestSession":
        # Восстановление из словаря
        obj = cls.__new__(cls)
        obj.session_id = data["session_id"]
        obj.username = data["username"]
        obj.questions = data["questions"]
        obj.grading_criteria = data["grading_criteria"]
        obj.premade_test_id = data.get("premade_test_id")
        obj.test_name = data.get("test_name")
        obj.time_limit_minutes = data.get("time_limit_minutes")
        obj.grading_mode = data.get("grading_mode", "overall")
        obj.user_role = data.get("user_role", "student")
        obj.user_answers = data.get("user_answers", [])
        obj.current_question_index = data.get("current_question_index", 0)
        obj.correct_answers = data.get("correct_answers", 0)
        obj.results = data.get("results", {})
        obj.category_max_points = data.get("category_max_points", {})
        obj.start_time = datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M:%S")
        obj.end_time = None
        obj.formatted_duration = ""
        return obj

    def get_past_questions(self) -> list:
        # Получение списка предыдущих вопросов
        result = []
        for i in range(self.current_question_index):
            q = self.questions[i]
            result.append({
                "index": i,
                "question_number": i + 1,
                "question": q["question"],
                "options": q["options"],
                "answer_type": q.get("answer_type", "single"),
                "matrices": q.get("matrices"),
                "commands": q.get("commands"),
                "total_questions": len(self.questions),
            })
        return result

    def _evaluate_and_finish(self, hide_correct: bool = False) -> dict:
        # Завершение сессии и расчёт результатов
        self.end_time = datetime.now()
        duration = self.end_time - self.start_time
        self.formatted_duration = str(timedelta(seconds=round(duration.total_seconds())))
        self.results["correct_count"] = f"{self.correct_answers}/{len(self.questions)}"

        sorted_criteria = self._get_sorted_criteria()
        topics_status = self._build_topics_status_raw()
        self.results["topic_result"] = topics_status

        if self.grading_mode == "per_topic":
            # Per-topic: each topic evaluated separately, all must pass
            all_passed = True
            for cat, info in topics_status.items():
                if info["total"] > 0:
                    status_desc, is_pass = self._apply_criteria(info["percentage"], sorted_criteria)
                    info["status"] = status_desc
                    if not is_pass:
                        all_passed = False
                else:
                    info["status"] = "Нет вопросов"
            if not any(v > 0 for v in self.category_max_points.values()):
                all_passed = False

            if all_passed:
                self.results["status_message"] = "Тест успешно пройден (все темы зачтены)."
                self.results["final_status"] = "Зачёт"
            else:
                self.results["status_message"] = "Тест не пройден (не все темы зачтены)."
                self.results["final_status"] = "Не зачёт"
        else:
            # Overall: single percentage for the whole test
            score_pct = round((self.correct_answers / len(self.questions)) * 100, 1) if self.questions else 0
            status_desc, is_pass = self._apply_criteria(score_pct, sorted_criteria)

            # Fill per-topic statuses for display
            for cat, info in topics_status.items():
                info["status"] = status_desc if info["total"] > 0 else "Нет вопросов"

            if is_pass:
                self.results["status_message"] = "Тест успешно пройден."
                self.results["final_status"] = "Зачёт"
            else:
                self.results["status_message"] = "Тест не пройден."
                self.results["final_status"] = "Не зачёт"

        # Always compute score_pct for result_detail
        score_pct = round((self.correct_answers / len(self.questions)) * 100, 1) if self.questions else 0

        # Always save full answers (with correct_answer) to DB.
        # Stripping for student-facing responses is handled by the router.
        result_detail = {
            "username": self.username,
            "test_name": self.test_name,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": self.formatted_duration,
            "score_percentage": score_pct,
            "category_scores": topics_status,
            "status": self.results["status_message"],
            "final_status": self.results["final_status"],
            "answers": self._build_answers_list(hide_correct=False),
            "premade_test_id": self.premade_test_id,
            "grading_mode": self.grading_mode,
        }

        self._save_result(result_detail)
        return result_detail
