import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

from database import get_col

logger = logging.getLogger(__name__)

# Default grading rules used when no custom criteria are defined
_DEFAULT_CRITERIA = [
    {"threshold_gte": 80, "description": "зачтено", "is_pass_status": True},
    {"threshold_gte": 50, "description": "удовлетворительно", "is_pass_status": True},
    {"threshold_gte": 0, "description": "незачтено", "is_pass_status": False},
]


class TestSession:
    """
    Rule-based expert system session.

    Knowledge base  : self.questions + self.grading_criteria
    Inference engine: _evaluate_and_finish()
    Rules           : _apply_criteria() — threshold IF-THEN chains
    """

    def __init__(
        self,
        username: str,
        questions: list,
        grading_criteria: dict,
        premade_test_id: Optional[str] = None,
        test_name: Optional[str] = None,
        time_limit_minutes: Optional[int] = None,
    ):
        self.session_id = uuid.uuid4().hex
        self.username = username
        self.questions = [dict(q) for q in questions]
        self.grading_criteria = grading_criteria
        self.premade_test_id = premade_test_id
        self.test_name = test_name
        self.time_limit_minutes = time_limit_minutes
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
        """Normalize different question key formats to a common internal format and shuffle options."""
        for q in self.questions:
            # Normalize question text: question_text -> question
            if "question" not in q and "question_text" in q:
                q["question"] = q["question_text"]
            # Normalize correct answer: correct_answer -> correct
            if "correct" not in q and "correct_answer" in q:
                q["correct"] = q["correct_answer"]
            # Shuffle answer options while keeping correct answer(s) mapped correctly
            self._shuffle_options(q)

    @staticmethod
    def _shuffle_options(q: dict) -> None:
        """Shuffle option order; correct answer references stay valid."""
        options = q.get("options")
        if not options or len(options) <= 1:
            return
        correct = q.get("correct")
        if correct is None:
            return
        # Build index mapping: old_index -> option_text
        old_options = list(options)
        indices = list(range(len(old_options)))
        random.shuffle(indices)
        q["options"] = [old_options[i] for i in indices]
        # No need to remap correct — correct stores option TEXT, not indices

    # ------------------------------------------------------------------
    # Setup
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
    # Public API
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
        if not self.time_limit_minutes:
            return False
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return elapsed >= self.time_limit_minutes * 60

    def submit_answer(self, answer) -> dict:
        if self.current_question_index >= len(self.questions):
            return {"finished": True, "error": "Нет больше вопросов."}

        # Auto-finish if timer expired
        if self.is_time_expired():
            # Fill missing answers as empty and finish
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
    # Helpers
    # ------------------------------------------------------------------

    def _get_category(self, index: int) -> str:
        if 0 <= index < len(self.questions):
            q = self.questions[index]
            return q.get("category") or q.get("topic", "unknown")
        return "unknown"

    # ------------------------------------------------------------------
    # Expert System Inference Engine
    # ------------------------------------------------------------------

    def _get_sorted_criteria(self) -> list:
        """Return grading rules sorted from strictest to most lenient."""
        rules = self.grading_criteria.get("topic_criteria") or _DEFAULT_CRITERIA
        return sorted(rules, key=lambda c: c.get("threshold_gte", 0), reverse=True)

    def _apply_criteria(self, pct: float, sorted_criteria: list) -> tuple:
        """IF-THEN rule chain: return (status_description, is_pass) for a score percentage."""
        for rule in sorted_criteria:
            if pct >= rule.get("threshold_gte", 0):
                return rule.get("description", "Статус не определен"), rule.get("is_pass_status", False)
        return "Статус не определен", False

    def _build_topics_status(self, sorted_criteria: list) -> tuple:
        """Evaluate all categories. Returns (topics_status dict, all_passed bool)."""
        topics_status = {}
        all_passed = True

        for cat, max_pts in self.category_max_points.items():
            score = self.results.get(cat, 0)
            if isinstance(score, str):
                continue
            if max_pts > 0:
                pct = (score / max_pts) * 100
                status_desc, is_pass = self._apply_criteria(pct, sorted_criteria)
                topics_status[cat] = {
                    "score": score,
                    "total": max_pts,
                    "percentage": round(pct, 2),
                    "status": status_desc,
                }
                if not is_pass:
                    all_passed = False
            else:
                topics_status[cat] = {"score": 0, "total": 0, "percentage": 0, "status": "Нет вопросов"}

        if not any(v > 0 for v in self.category_max_points.values()):
            all_passed = False

        return topics_status, all_passed

    def _build_answers_list(self) -> list:
        """Build a per-question answer review for the result report."""
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
            answers.append({
                "question": q["question"],
                "user_answer": user_repr,
                "correct_answer": q["correct"],
                "category": self._get_category(i),
            })
        return answers

    def _save_result(self, result_detail: dict) -> None:
        try:
            get_col().insert_one(result_detail.copy())
        except Exception as e:
            logger.error("Failed to save test result for session %s: %s", self.session_id, e)

    def _evaluate_and_finish(self) -> dict:
        """
        Inference engine entry point.
        Applies grading rules per category, determines final verdict, persists result.
        """
        self.end_time = datetime.now()
        duration = self.end_time - self.start_time
        self.formatted_duration = str(timedelta(seconds=round(duration.total_seconds())))
        self.results["correct_count"] = f"{self.correct_answers}/{len(self.questions)}"

        sorted_criteria = self._get_sorted_criteria()
        topics_status, all_passed = self._build_topics_status(sorted_criteria)
        self.results["topic_result"] = topics_status

        if all_passed:
            self.results["status_message"] = "Тест успешно пройден."
            self.results["final_status"] = "Зачёт"
        else:
            self.results["status_message"] = "Тест не пройден."
            self.results["final_status"] = "Не зачёт"

        score_pct = round((self.correct_answers / len(self.questions)) * 100, 1) if self.questions else 0
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
            "answers": self._build_answers_list(),
            "premade_test_id": self.premade_test_id,
        }

        self._save_result(result_detail)
        return result_detail
