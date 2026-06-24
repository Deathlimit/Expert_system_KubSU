import os
import requests

AUTH_URL = os.environ.get("AUTH_SERVICE_URL", "https://testing.k-lab.su")
CONTENT_URL = os.environ.get("CONTENT_SERVICE_URL", "https://testing.k-lab.su")
TEST_URL = os.environ.get("TEST_SERVICE_URL", "https://testing.k-lab.su")
SESSION_URL = os.environ.get("SESSION_SERVICE_URL", "https://testing.k-lab.su")
ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"
ROLE_UNASSIGNED = "unassigned"


def _safe_detail(response, default: str = "Ошибка сервера.") -> str:
    try:
        return response.json().get("detail", default)
    except Exception:
        return f"{default} (HTTP {response.status_code})"


class ApiClient:
    def __init__(self):
        self.token = None
        self.username = None
        self.role = None

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, url, params=None):
        return requests.get(url, headers=self._headers(), params=params, timeout=15)

    def _post(self, url, json_data=None):
        return requests.post(url, headers=self._headers(), json=json_data, timeout=15)

    def _put(self, url, json_data=None, params=None):
        return requests.put(
            url, headers=self._headers(), json=json_data, params=params, timeout=15
        )

    def _delete(self, url):
        return requests.delete(url, headers=self._headers(), timeout=15)

    def login(self, username: str, password: str):
        try:
            r = self._post(
                f"{AUTH_URL}/auth/login", {"username": username, "password": password}
            )
            if r.status_code == 200:
                data = r.json()
                self.token = data["access_token"]
                self.username = data["username"]
                self.role = data["role"]
                return True, data
            return False, r.json().get("detail", "Ошибка входа.")
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу авторизации."

    def verify_token(self):
        try:
            r = self._get(f"{AUTH_URL}/auth/verify")
            if r.status_code == 200:
                return True, r.json()
            return False, _safe_detail(r)
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def register(
        self, username: str, password: str, group: str = "", full_name: str = ""
    ):
        try:
            body = {"username": username, "password": password, "group": group}
            if full_name:
                body["full_name"] = full_name
            r = self._post(f"{AUTH_URL}/auth/register", body)
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            detail = r.json().get("detail", "Ошибка регистрации.")
            if isinstance(detail, list):
                detail = "; ".join(e.get("msg", str(e)) for e in detail)
            return False, detail
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def get_all_users(self):
        r = self._get(f"{AUTH_URL}/auth/users")
        if r.status_code == 200:
            return r.json()
        return {}

    def get_users_by_role(self, role: str):
        r = self._get(f"{AUTH_URL}/auth/users/by-role/{role}")
        if r.status_code == 200:
            return r.json()
        return []

    def get_students(self):
        try:
            r = self._get(f"{AUTH_URL}/auth/students")
            if r.status_code == 200:
                return r.json()
            return []
        except requests.ConnectionError:
            return []

    def update_user_full_name(self, username: str, full_name: str):
        try:
            r = self._put(
                f"{AUTH_URL}/auth/users/{username}/full-name", {"full_name": full_name}
            )
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, _safe_detail(r)
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def change_user_role(self, username: str, new_role: str):
        r = self._put(f"{AUTH_URL}/auth/users/{username}/role", {"role": new_role})
        if r.status_code == 200:
            return True, r.json().get("message", "OK")
        return False, r.json().get("detail", "Ошибка.")

    def change_user_group(self, username: str, new_group: str):
        try:
            r = self._put(
                f"{AUTH_URL}/auth/users/{username}/group", {"group": new_group or ""}
            )
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, _safe_detail(r)
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def delete_user(self, username: str):
        try:
            r = self._delete(f"{AUTH_URL}/auth/users/{username}")
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, _safe_detail(r)
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def change_password(self, username: str, old_password: str, new_password: str):
        try:
            r = self._put(
                f"{AUTH_URL}/auth/users/{username}/password",
                {"old_password": old_password, "new_password": new_password},
            )
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, _safe_detail(r)
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def get_all_groups(self):
        try:
            r = self._get(f"{AUTH_URL}/auth/groups")
            if r.status_code == 200:
                return r.json()
            return []
        except requests.ConnectionError:
            return []

    def get_users_by_group(self, group: str):
        try:
            r = self._get(f"{AUTH_URL}/auth/users/by-group/{group}")
            if r.status_code == 200:
                return r.json()
            return []
        except requests.ConnectionError:
            return []

    def get_questions(self):
        r = self._get(f"{CONTENT_URL}/content/questions")
        if r.status_code == 200:
            return r.json()
        return {}

    def get_categories(self):
        r = self._get(f"{CONTENT_URL}/content/categories")
        if r.status_code == 200:
            return r.json()
        return []

    def add_question(self, topic: str, question_data: dict):
        r = self._post(f"{CONTENT_URL}/content/questions/{topic}", question_data)
        if r.status_code == 200:
            return True, r.json().get("message", "OK")
        return False, r.json().get("detail", "Ошибка.")

    def update_question(self, topic: str, index: int, question_data: dict):
        r = self._put(f"{CONTENT_URL}/content/questions/{topic}/{index}", question_data)
        if r.status_code == 200:
            return True, r.json().get("message", "OK")
        return False, r.json().get("detail", "Ошибка.")

    def delete_question(self, topic: str, index: int):
        r = self._delete(f"{CONTENT_URL}/content/questions/{topic}/{index}")
        if r.status_code == 200:
            return True, r.json().get("message", "OK")
        return False, r.json().get("detail", "Ошибка.")

    def get_criteria_for_evaluation(self, creator_username=None):
        params = {}
        if creator_username:
            params["creator_username"] = creator_username
        r = self._get(f"{CONTENT_URL}/content/criteria", params=params)
        if r.status_code == 200:
            return r.json()
        return {"topic_criteria": []}

    def get_criteria_for_editing(self, username: str, role: str):
        r = self._get(
            f"{CONTENT_URL}/content/criteria/for-editing",
            params={"username": username, "role": role},
        )
        if r.status_code == 200:
            return r.json()
        return {"topic_criteria": []}

    def save_criteria(self, username: str, role: str, criteria_object: dict):
        r = self._put(
            f"{CONTENT_URL}/content/criteria",
            json_data=criteria_object,
            params={"username": username, "role": role},
        )
        if r.status_code == 200:
            return True, r.json().get("message", "OK")
        return False, r.json().get("detail", "Ошибка.")

    def get_default_criteria(self):
        r = self._get(f"{CONTENT_URL}/content/criteria/defaults")
        if r.status_code == 200:
            return r.json()
        return {"topic_criteria": []}

    def bulk_import_questions(self, questions: list):
        try:
            r = self._post(
                f"{CONTENT_URL}/content/questions/import", {"questions": questions}
            )
            if r.status_code == 200:
                data = r.json()
                return True, data.get("message", "OK"), data
            return False, _safe_detail(r), None
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу.", None

    def get_test_criteria(self, test_id: str):
        try:
            r = self._get(f"{CONTENT_URL}/content/criteria/test/{test_id}")
            if r.status_code == 200:
                return r.json()
            return None
        except requests.ConnectionError:
            return None

    def save_test_criteria(self, test_id: str, criteria_object: dict):
        try:
            r = self._put(
                f"{CONTENT_URL}/content/criteria/test/{test_id}",
                json_data=criteria_object,
            )
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, r.json().get("detail", "Ошибка.")
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def get_all_premade_tests(self):
        r = self._get(f"{TEST_URL}/tests")
        if r.status_code == 200:
            return r.json()
        return []

    def get_premade_tests_for_creator(self, creator_username: str):
        r = self._get(f"{TEST_URL}/tests/creator/{creator_username}")
        if r.status_code == 200:
            return r.json()
        return []

    def get_premade_test_by_id(self, test_id: str):
        r = self._get(f"{TEST_URL}/tests/{test_id}")
        if r.status_code == 200:
            return r.json()
        return None

    def get_assigned_tests_for_student(self, student_username: str):
        r = self._get(f"{TEST_URL}/tests/assigned/{student_username}")
        if r.status_code == 200:
            return r.json()
        return {}

    def create_premade_test(
        self,
        test_name: str,
        questions: list,
        time_limit_minutes=None,
        cooldown_hours=24,
        max_attempts=None,
        grading_mode="overall",
        show_results_to_students=True,
    ):
        payload = {
            "test_name": test_name,
            "questions": questions,
            "cooldown_hours": cooldown_hours,
            "grading_mode": grading_mode,
            "show_results_to_students": show_results_to_students,
        }
        if time_limit_minutes is not None:
            payload["time_limit_minutes"] = time_limit_minutes
        if max_attempts is not None:
            payload["max_attempts"] = max_attempts
        r = self._post(f"{TEST_URL}/tests", payload)
        if r.status_code == 200:
            return True, r.json().get("message", "OK"), r.json().get("test_id")
        return False, r.json().get("detail", "Ошибка."), None

    def delete_premade_test(self, test_id: str):
        r = self._delete(f"{TEST_URL}/tests/{test_id}")
        if r.status_code == 200:
            return True, r.json().get("message", "OK")
        return False, r.json().get("detail", "Ошибка.")

    def clone_premade_test(self, test_id: str):
        try:
            r = self._post(f"{TEST_URL}/tests/{test_id}/clone")
            if r.status_code == 200:
                data = r.json()
                return True, data.get("message", "OK"), data.get("test")
            return False, _safe_detail(r), None
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу.", None

    def delete_question_from_premade_test(self, test_id: str, index: int):
        r = self._delete(f"{TEST_URL}/tests/{test_id}/questions/{index}")
        if r.status_code == 200:
            return True, r.json().get("message", "OK")
        return False, r.json().get("detail", "Ошибка.")

    def add_questions_to_premade_test(self, test_id: str, questions: list):
        r = self._post(
            f"{TEST_URL}/tests/{test_id}/questions", {"questions": questions}
        )
        if r.status_code == 200:
            data = r.json()
            return True, data.get("message", "OK"), data.get("test")
        return False, r.json().get("detail", "Ошибка."), None

    def assign_student(self, test_id: str, student_username: str):
        r = self._put(
            f"{TEST_URL}/tests/{test_id}/assign", {"student_username": student_username}
        )
        if r.status_code == 200:
            return True, r.json().get("message", "OK")
        return False, r.json().get("detail", "Ошибка.")

    def unassign_student(self, test_id: str, student_username: str):
        r = self._put(
            f"{TEST_URL}/tests/{test_id}/unassign",
            {"student_username": student_username},
        )
        if r.status_code == 200:
            return True, r.json().get("message", "OK")
        return False, _safe_detail(r)

    def batch_update_assignments(
        self, test_id: str, assign_list: list, unassign_list: list
    ):
        r = self._put(
            f"{TEST_URL}/tests/{test_id}/assignments",
            {"assign": assign_list, "unassign": unassign_list},
        )
        if r.status_code == 200:
            data = r.json()
            return True, data.get("messages", []), data.get("test")
        return False, [_safe_detail(r)], None

    def generate_test_by_topic_and_score(self, topic: str, max_score: int):
        r = self._post(
            f"{TEST_URL}/tests/generate", {"topic": topic, "max_score": max_score}
        )
        if r.status_code == 200:
            data = r.json()
            return (
                data.get("questions", []),
                data.get("total_score", 0),
                data.get("message", "OK"),
            )
        detail = r.json().get("detail", "Ошибка.")
        return [], 0, detail

    def update_test_settings(self, test_id: str, settings: dict):
        try:
            r = self._put(f"{TEST_URL}/tests/{test_id}/settings", settings)
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, _safe_detail(r)
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def rename_premade_test(self, test_id: str, new_name: str):
        try:
            r = self._put(f"{TEST_URL}/tests/{test_id}/name", {"test_name": new_name})
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, r.json().get("detail", "Ошибка переименования.")
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def share_test(self, test_id: str):
        try:
            r = self._post(f"{TEST_URL}/tests/{test_id}/share")
            if r.status_code == 200:
                data = r.json()
                return True, data
            return False, _safe_detail(r)
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def unshare_test(self, test_id: str):
        try:
            r = self._delete(f"{TEST_URL}/tests/{test_id}/share")
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, _safe_detail(r)
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def get_shared_test_info(self, share_token: str):
        try:
            r = self._get(f"{TEST_URL}/tests/shared/{share_token}")
            if r.status_code == 200:
                return r.json()
            return None
        except requests.ConnectionError:
            return None

    def join_test_by_share(self, share_token: str):
        try:
            r = self._post(f"{TEST_URL}/tests/shared/{share_token}/join")
            if r.status_code == 200:
                return True, r.json()
            return False, _safe_detail(r)
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def start_session(self, test_id=None, num_questions_per_category=None):
        payload = {}
        if test_id:
            payload["test_id"] = test_id
        if num_questions_per_category:
            payload["num_questions_per_category"] = num_questions_per_category
        try:
            r = self._post(f"{SESSION_URL}/sessions/start", payload)
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("detail", "Ошибка запуска сессии.")
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу сессий."

    def submit_answer(self, session_id: str, question_index: int, answer):
        r = self._post(
            f"{SESSION_URL}/sessions/{session_id}/answer",
            {"question_index": question_index, "answer": answer},
        )
        if r.status_code == 200:
            return r.json()
        return {"finished": True, "error": _safe_detail(r)}

    def finish_session(self, session_id: str):
        try:
            r = self._post(f"{SESSION_URL}/sessions/{session_id}/finish")
            if r.status_code == 200:
                return r.json()
            return {"finished": True, "error": _safe_detail(r)}
        except requests.ConnectionError:
            return {"finished": True, "error": "Не удалось подключиться к серверу."}

    def get_session_status(self, session_id: str):
        try:
            r = self._get(f"{SESSION_URL}/sessions/{session_id}/status")
            if r.status_code == 200:
                d = r.json()
                total = d.get("total_questions", 0)
                ua = d.get("user_answers", [])
                current_index = 0
                for i, ans in enumerate(ua):
                    if ans is None:
                        current_index = i
                        break
                if ua and all(a is not None for a in ua):
                    current_index = total
                return current_index, total
            return None
        except requests.ConnectionError:
            return None

    def check_eligibility(self, username: str, test_id: str):
        r = self._get(f"{SESSION_URL}/sessions/eligibility/{username}/{test_id}")
        if r.status_code == 200:
            data = r.json()
            return data.get("eligible", True), data.get("message", "")
        return True, ""

    def get_test_history(self):
        r = self._get(f"{SESSION_URL}/sessions/history")
        if r.status_code == 200:
            return r.json()
        return []

    def get_user_history(self, username: str):
        r = self._get(f"{SESSION_URL}/sessions/history/{username}")
        if r.status_code == 200:
            return r.json()
        return []

    def get_test_results(self, test_id: str):
        try:
            r = self._get(f"{SESSION_URL}/sessions/results/test/{test_id}")
            if r.status_code == 200:
                return r.json()
            return []
        except requests.ConnectionError:
            return []

    def get_test_aggregate_stats(self, test_id: str):
        try:
            r = self._get(f"{SESSION_URL}/sessions/results/test/{test_id}/stats")
            if r.status_code == 200:
                return r.json()
            return None
        except requests.ConnectionError:
            return None

    def clear_history(self, username: str = None, test_id: str = None):
        try:
            params = []
            if username:
                params.append(f"username={username}")
            if test_id:
                params.append(f"test_id={test_id}")
            query = "?" + "&".join(params) if params else ""
            r = self._delete(f"{SESSION_URL}/sessions/history{query}")
            if r.status_code == 200:
                return True, r.json()
            return False, _safe_detail(r)
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def get_active_session(self):
        try:
            r = self._get(f"{SESSION_URL}/sessions/active")
            if r.status_code == 200:
                return r.json()
            return None
        except requests.ConnectionError:
            return None

    def reset_password(self, username: str, new_password: str):
        try:
            r = self._put(
                f"{AUTH_URL}/auth/users/{username}/reset-password",
                {"new_password": new_password},
            )
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, r.json().get("detail", "Ошибка сброса пароля.")
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def create_group(self, name: str):
        try:
            r = self._post(f"{AUTH_URL}/auth/groups", {"name": name})
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, r.json().get("detail", "Ошибка создания группы.")
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def delete_group(self, name: str):
        try:
            r = self._delete(f"{AUTH_URL}/auth/groups/{name}")
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, r.json().get("detail", "Ошибка удаления группы.")
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."

    def rename_group(self, old_name: str, new_name: str):
        try:
            r = self._put(f"{AUTH_URL}/auth/groups/{old_name}", {"name": new_name})
            if r.status_code == 200:
                return True, r.json().get("message", "OK")
            return False, r.json().get("detail", "Ошибка переименования группы.")
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу."
