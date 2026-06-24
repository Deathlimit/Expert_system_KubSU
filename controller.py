import csv
import json
import os
import random
import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)
from api_client import ApiClient, ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT
import view


class AppController:
    def __init__(self):
        self.login_view = None
        self.student_view = None
        self.teacher_view = None
        self.admin_view = None
        self.test_history_view = None
        self.add_question_view = None
        self.edit_questions_view = None
        self.edit_single_question_view = None
        self.role_management_view = None
        self.create_premade_test_dialog = None
        self.manage_premade_tests_dialog = None
        self.test_management_dialog = None
        self.generate_topic_score_test_dialog = None
        self.edit_grading_criteria_view = None
        self.student_test_history_view = None

        self.current_username = None
        self.current_theme = "dark"

        self.api = ApiClient()

        self.current_session_id = None
        self.current_question_data = None

        self._q_buffer = []
        self._a_buffer = []
        self._frontier_idx = -1
        self._total_q_count = 0

        self._questions_cache = {}

    def apply_theme(self, theme_name):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        qss_file = os.path.join(base_dir, "dark_theme.qss")
        if theme_name == "light":
            qss_file = os.path.join(base_dir, "light_theme.qss")

        try:
            with open(qss_file, "r") as f:
                QApplication.instance().setStyleSheet(f.read())
            self.current_theme = theme_name
        except FileNotFoundError:
            print(
                f"Warning: Stylesheet file '{qss_file}' not found. Using default Qt style or previous style."
            )
        except Exception as e:
            print(f"Warning: Could not load stylesheet from '{qss_file}': {e}")

    def toggle_theme(self):
        if self.current_theme == "dark":
            self.apply_theme("light")
        else:
            self.apply_theme("dark")

    @staticmethod
    def _is_visible(widget) -> bool:

        try:
            return widget is not None and widget.isVisible()
        except RuntimeError:
            return False

    def start_app(self):

        self.apply_theme(self.current_theme)
        self.login_view = view.LoginWindow()

        self.login_view.login_attempt.connect(self.handle_login_attempt)
        self.login_view.register_attempt.connect(self.handle_register_attempt)
        self.login_view.join_by_share_signal.connect(
            self.handle_join_by_share_from_login
        )

        try:
            groups = self.api.get_all_groups()
            self.login_view.set_groups(groups if groups else [])
        except Exception:
            pass
        self.login_view.show()

    def handle_login_attempt(self, username, password):
        success, result = self.api.login(username, password)
        if success:
            self.current_username = result["username"]
            user_role = result["role"]
            pending_token = self.login_view.get_pending_share_token()
            self.login_view.close()
            if pending_token:
                self._join_test_by_share_token(pending_token, user_role)
            else:
                self.open_main_window_for_role(user_role)
        else:
            self.login_view.show_message("Ошибка входа", str(result), is_error=True)

    def handle_register_attempt(self, username, password, group="", full_name=""):
        success, message = self.api.register(username, password, group, full_name)
        if success:
            self.login_view.show_message("Регистрация успешна", message)
        else:
            self.login_view.show_message("Ошибка регистрации", message, is_error=True)

    def handle_join_by_share_from_login(self, share_token):
        self.login_view.show_message(
            "Присоединение к тесту",
            "Сначала войдите в систему. После входа вы будете автоматически присоединены к тесту.",
        )

    def _join_test_by_share_token(self, share_token, user_role):

        success, data = self.api.join_test_by_share(share_token)
        if not success:
            QMessageBox.warning(None, "Ошибка", str(data))
            self.open_main_window_for_role(user_role)
            return

        if data.get("role_restricted"):
            QMessageBox.information(
                None,
                "Информация",
                "Преподаватели и администраторы не могут проходить тесты по ссылке.",
            )
            self.open_main_window_for_role(user_role)
            return

        if data.get("account_not_activated"):
            QMessageBox.warning(
                None,
                "Ошибка",
                data.get("message", "Ваша учетная запись не активирована."),
            )
            self.open_main_window_for_role(user_role)
            return

        if data.get("has_active_session"):
            QMessageBox.warning(
                None,
                "Активный тест",
                data.get("message", "У вас уже есть активный тест."),
            )
            self.open_main_window_for_role(user_role)
            return

        test_id = data.get("test_id")
        if not test_id:
            QMessageBox.warning(None, "Ошибка", "Не удалось получить ID теста.")
            self.open_main_window_for_role(user_role)
            return

        self.show_student_window(self.current_username)

        if self.student_view:
            assigned = self.api.get_assigned_tests_for_student(self.current_username)
            for teacher, tests in assigned.items():
                for t in tests:
                    if t.get("test_id") == test_id:
                        self.student_view.welcome_label.hide()
                        self.student_view.my_history_button.hide()
                        self.student_view.assigned_tests_group.hide()
                        self.student_view.change_password_button_student.hide()
                        self.student_view.theme_toggle_button_student.hide()
                        self.student_view.logout_button.hide()
                        self.student_view.results_label.setText("")
                        self.student_view.restart_button.hide()
                        self.student_view.next_button.show()
                        self.handle_start_assigned_test(t)
                        return
            QMessageBox.information(
                None,
                "Присоединение",
                "Вы присоединены к тесту. Тест появится в списке назначенных.",
            )

    def handle_logout(self):

        self.api.token = None
        self.api.username = None
        self.api.role = None
        self.current_username = None
        self.current_session_id = None
        self.current_question_data = None
        self._q_buffer = []
        self._a_buffer = []
        self._frontier_idx = -1
        self._total_q_count = 0

        for view_attr in ("student_view", "teacher_view", "admin_view"):
            v = getattr(self, view_attr, None)
            if v:
                try:
                    v.close()
                except RuntimeError:
                    pass
                setattr(self, view_attr, None)
        self.start_app()

    def open_main_window_for_role(self, role):

        if role == ROLE_STUDENT:
            self.show_student_window(self.current_username)
        elif role == ROLE_TEACHER:
            self.show_teacher_window()
        elif role == ROLE_ADMIN:
            self.show_admin_window()
        else:
            QMessageBox.critical(
                (self.login_view if self._is_visible(self.login_view) else None),
                "Ошибка роли",
                f"Неизвестная или не назначенная роль: '{role}'. Обратитесь к администратору.",
            )

    def show_student_window(self, username):
        if self.student_view:
            self.student_view.close()

        assigned_tests = self.api.get_assigned_tests_for_student(username)

        eligibility_data = {}
        for teacher, tests in assigned_tests.items():
            for t in tests:
                tid = t.get("test_id")
                if tid:
                    eligible, msg = self.api.check_eligibility(username, tid)
                    eligibility_data[tid] = {"eligible": eligible, "message": msg}

        active_session_test_id = self._peek_active_session_test_id(username)

        server_active = self.api.get_active_session()
        if server_active and server_active.get("active"):
            active_session_test_id = (
                server_active.get("test_id") or active_session_test_id
            )

        self.student_view = view.StudentWindow(
            username,
            assigned_tests_list=assigned_tests,
            eligibility_data=eligibility_data,
            active_session_test_id=active_session_test_id,
        )

        self.student_view.show_my_history_signal.connect(
            self.handle_show_student_history_dialog
        )
        self.student_view.start_assigned_test_signal.connect(
            self.handle_start_assigned_test
        )
        self.student_view.resume_active_session_signal.connect(
            lambda: self.handle_resume_active_session(username)
        )
        self.student_view.next_question_signal.connect(
            self.handle_next_student_question
        )
        self.student_view.restart_test_signal.connect(self.handle_restart_test)
        self.student_view.timeout_signal.connect(self.handle_test_timeout)
        self.student_view.toggle_theme_signal.connect(self.toggle_theme)
        self.student_view.logout_signal.connect(self.handle_logout)
        self.student_view.navigate_to_question_signal.connect(
            self.handle_navigate_to_question
        )
        self.student_view.change_password_signal.connect(
            lambda: self.handle_change_own_password(parent=self.student_view)
        )
        self.student_view.join_by_share_signal.connect(
            lambda token: self._join_test_by_share_token(token, ROLE_STUDENT)
        )
        self.student_view.show()
        self._check_and_resume_session(username)

    @staticmethod
    def _shuffle_question_options(q):
        opts = q.get("options")
        if isinstance(opts, list):
            random.shuffle(opts)

    def handle_start_assigned_test(self, premade_test_object):
        if (
            not premade_test_object
            or "questions" not in premade_test_object
            or "test_id" not in premade_test_object
        ):
            self.student_view.show_message(
                "Ошибка теста", "Некорректные данные назначенного теста.", is_error=True
            )
            self.student_view.welcome_label.show()
            self.student_view.my_history_button.show()
            self.student_view.assigned_tests_group.show()
            self.student_view.change_password_button_student.show()
            self.student_view.theme_toggle_button_student.show()
            self.student_view.logout_button.show()
            self.student_view.join_by_share_button_student.show()
            self.student_view.next_button.hide()
            return

        test_id = premade_test_object["test_id"]

        self.student_view.welcome_label.hide()
        self.student_view.my_history_button.hide()
        self.student_view.assigned_tests_group.hide()
        self.student_view.change_password_button_student.hide()
        self.student_view.theme_toggle_button_student.hide()
        self.student_view.logout_button.hide()
        self.student_view.join_by_share_button_student.hide()
        self.student_view.results_label.setText("")
        self.student_view.restart_button.hide()
        self.student_view.next_button.show()

        success, data = self.api.start_session(test_id=test_id)
        if not success:
            self.student_view.show_message("Ошибка", str(data), is_error=True)
            self.student_view.welcome_label.show()
            self.student_view.my_history_button.show()
            self.student_view.assigned_tests_group.show()
            self.student_view.change_password_button_student.show()
            self.student_view.theme_toggle_button_student.show()
            self.student_view.logout_button.show()
            self.student_view.join_by_share_button_student.show()
            self.student_view.next_button.hide()
            return

        if data.get("finished") and data.get("timed_out"):
            results = data.get("results", {})
            self.student_view.show_results_summary(
                results.get("status_message", "Время вышло."),
                results.get("final_status", "N/A"),
                results=results,
            )
            self.student_view.show_message(
                "Время вышло",
                "Время вышло. Тест завершён автоматически.",
                is_error=True,
            )
            self._clear_intermediate_state()
            return

        self.current_session_id = data["session_id"]
        self._current_test_id = test_id
        self._current_test_name = premade_test_object.get("test_name", "")

        questions = data.get("questions")
        if questions is not None:
            self._q_buffer = list(questions)
            self._total_q_count = data.get("total_questions", len(self._q_buffer))
            user_answers = data.get("user_answers", [])
            self._a_buffer = (
                list(user_answers) if user_answers else [None] * len(self._q_buffer)
            )

            for q in self._q_buffer:
                self._shuffle_question_options(q)

            first_unanswered = 0
            for i, ans in enumerate(self._a_buffer):
                if ans is None:
                    first_unanswered = i
                    break
            self._frontier_idx = first_unanswered
            if not self._q_buffer:
                self.student_view.show_message(
                    "Ошибка", "Тест не содержит вопросов.", is_error=True
                )
                return
            self.current_question_data = self._q_buffer[first_unanswered]
        else:

            self.current_question_data = data["current_question"]
            self._q_buffer = [self.current_question_data]
            self._a_buffer = []
            self._frontier_idx = 0
            self._total_q_count = data.get("total_questions", 0)

        self.student_view.setup_nav_panel(self._total_q_count)
        self.student_view.update_nav_panel(self._frontier_idx, self._frontier_idx)
        if self.current_question_data:
            self._display_question_from_data(self.current_question_data)

    def _display_question_from_data(self, q):

        self.student_view.display_question(
            question_number=q["question_number"],
            question_text=q["question"],
            options=q["options"],
            answer_type=q.get("answer_type", "single"),
            matrices=q.get("matrices"),
            commands=q.get("commands"),
            is_additional=q.get("is_additional", False),
        )

        if "seconds_remaining" in q:
            self.student_view.start_countdown(q["seconds_remaining"])

    def handle_test_timeout(self):

        if not self.current_session_id:
            return

        q_idx = self._frontier_idx if self._frontier_idx >= 0 else 0
        result = self.api.submit_answer(self.current_session_id, q_idx, "")
        if result.get("finished"):
            results = result.get("results", {})
            self.student_view.show_results_summary(
                results.get("status_message", results.get("status", "Тест завершён.")),
                results.get("final_status", "N/A"),
                results=results,
            )
            self._clear_intermediate_state()
            self.current_session_id = None
        else:

            finish_result = self.api.finish_session(self.current_session_id)
            if finish_result.get("results"):
                results = finish_result["results"]
                self.student_view.show_results_summary(
                    results.get(
                        "status_message", results.get("status", "Тест завершён.")
                    ),
                    results.get("final_status", "N/A"),
                    results=results,
                )
                self._clear_intermediate_state()
                self.current_session_id = None

    def handle_navigate_to_question(self, idx):

        if idx < 0 or idx >= len(self._q_buffer):
            return
        q = self._q_buffer[idx]
        submitted_answer = self._a_buffer[idx] if idx < len(self._a_buffer) else None

        self.student_view.display_question(
            question_number=q["question_number"],
            question_text=q["question"],
            options=list(q["options"]),
            answer_type=q.get("answer_type", "single"),
            matrices=q.get("matrices"),
            commands=q.get("commands"),
            is_additional=q.get("is_additional", False),
            selected_answer=submitted_answer,
        )
        self.student_view.update_nav_panel(idx, self._frontier_idx)

    def _peek_active_session_test_id(self, username):
        save_path = os.path.join(
            os.path.expanduser("~"),
            ".testing_expert_system",
            f"active_session_{username}.json",
        )
        try:
            if os.path.exists(save_path):
                with open(save_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("test_id")
        except Exception:
            pass
        return None

    def handle_resume_active_session(self, username):
        save_dir = os.path.join(os.path.expanduser("~"), ".testing_expert_system")
        save_path = os.path.join(save_dir, f"active_session_{username}.json")
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
        except Exception:

            self._clear_intermediate_state()
            test_obj = (
                self.student_view.current_selected_assigned_test
                if self.student_view
                else None
            )
            if test_obj:
                self.handle_start_assigned_test(test_obj)
            return

        session_id = saved.get("session_id")
        status = self.api.get_session_status(session_id) if session_id else None
        if status is None or status[0] != saved.get("frontier_idx", -1):
            try:
                os.remove(save_path)
            except Exception:
                pass
            self.student_view.clear_active_session_marker()

            test_obj = (
                self.student_view.current_selected_assigned_test
                if self.student_view
                else None
            )
            if test_obj:
                self.handle_start_assigned_test(test_obj)
            return

        self._restore_saved_session(saved)

    def _restore_saved_session(self, saved):

        saved_frontier = saved.get("frontier_idx", -1)
        self.current_session_id = saved["session_id"]
        self._current_test_id = saved.get("test_id")
        self._current_test_name = saved.get("test_name", "")
        self._q_buffer = saved.get("q_buffer", [])
        self._a_buffer = saved.get("a_buffer", [])
        self._frontier_idx = saved_frontier
        self._total_q_count = saved.get("total_questions", 0)

        if not self._q_buffer:
            return

        if self._frontier_idx < 0 or self._frontier_idx >= len(self._q_buffer):
            self._frontier_idx = 0

        self.student_view.welcome_label.hide()
        self.student_view.my_history_button.hide()
        self.student_view.assigned_tests_group.hide()
        self.student_view.change_password_button_student.hide()
        self.student_view.theme_toggle_button_student.hide()
        self.student_view.logout_button.hide()
        self.student_view.join_by_share_button_student.hide()
        self.student_view.results_label.setText("")
        self.student_view.restart_button.hide()
        self.student_view.next_button.show()

        self.student_view.setup_nav_panel(self._total_q_count)
        self.student_view.update_nav_panel(self._frontier_idx, self._frontier_idx)

        frontier_q = self._q_buffer[self._frontier_idx]
        self.current_question_data = frontier_q
        self._display_question_from_data(frontier_q)

    def _check_and_resume_session(self, username):
        save_dir = os.path.join(os.path.expanduser("~"), ".testing_expert_system")
        save_path = os.path.join(save_dir, f"active_session_{username}.json")
        if not os.path.exists(save_path):
            return

        try:
            with open(save_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
        except Exception:
            return

        session_id = saved.get("session_id")
        if not session_id:
            return

        status = self.api.get_session_status(session_id)
        if status is None:
            try:
                os.remove(save_path)
            except Exception:
                pass
            self.student_view.clear_active_session_marker()
            return

        server_index, server_total = status
        saved_frontier = saved.get("frontier_idx", -1)
        if server_index != saved_frontier:
            try:
                os.remove(save_path)
            except Exception:
                pass
            self.student_view.clear_active_session_marker()
            return

        test_name = saved.get("test_name", "неизвестный тест")
        answered_count = len(saved.get("a_buffer", []))
        total = saved.get("total_questions", 0)

        reply = QMessageBox.question(
            self.student_view,
            "Продолжить тест?",
            f"Обнаружен незавершённый тест «{test_name}».\n"
            f"Отвечено на {answered_count} из {total} вопросов.\n\n"
            "Продолжить с того места, где остановились?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        self._restore_saved_session(saved)

    def _save_intermediate_state(self):
        if not self.current_session_id or not self.current_username:
            return
        data = {
            "session_id": self.current_session_id,
            "test_id": getattr(self, "_current_test_id", None),
            "test_name": getattr(self, "_current_test_name", ""),
            "username": self.current_username,
            "timestamp": datetime.now().isoformat(),
            "total_questions": self._total_q_count,
            "frontier_idx": self._frontier_idx,
            "q_buffer": self._q_buffer,
            "a_buffer": self._a_buffer,
        }
        save_dir = os.path.join(os.path.expanduser("~"), ".testing_expert_system")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(
            save_dir, f"active_session_{self.current_username}.json"
        )
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save intermediate state: {e}")

    def _clear_intermediate_state(self):
        if not self.current_username:
            return
        save_dir = os.path.join(os.path.expanduser("~"), ".testing_expert_system")
        save_path = os.path.join(
            save_dir, f"active_session_{self.current_username}.json"
        )
        try:
            if os.path.exists(save_path):
                os.remove(save_path)
        except Exception:
            pass
        if self.student_view:
            self.student_view.clear_active_session_marker()

    def handle_next_student_question(self, current_idx, selected_answer):
        result = self.api.submit_answer(
            self.current_session_id, current_idx, selected_answer
        )

        if result.get("error"):
            self.student_view.show_message("Ошибка", result["error"], is_error=True)
            return

        if current_idx < len(self._a_buffer):
            self._a_buffer[current_idx] = selected_answer
        else:
            for _ in range(len(self._a_buffer), current_idx):
                self._a_buffer.append(None)
            self._a_buffer.append(selected_answer)

        if result.get("finished"):
            self._save_intermediate_state()
            results = result.get("results", {})
            self.student_view.show_results_summary(
                results.get("status_message", results.get("status", "Тест завершён.")),
                results.get("final_status", "N/A"),
                results=results,
            )
            self._clear_intermediate_state()
            self.current_session_id = None
            return

        next_q = result.get("current_question")
        next_idx = current_idx + 1

        if next_q:
            if next_idx < len(self._q_buffer):
                self._q_buffer[next_idx] = next_q
            else:
                self._q_buffer.append(next_q)
            self.current_question_data = next_q
            self._frontier_idx = max(self._frontier_idx, next_idx)
        elif next_idx < len(self._q_buffer):
            self.current_question_data = self._q_buffer[next_idx]
            self._frontier_idx = max(self._frontier_idx, next_idx)
        else:
            finish_result = self.api.finish_session(self.current_session_id)
            if finish_result.get("results"):
                results = finish_result["results"]
                self.student_view.show_results_summary(
                    results.get(
                        "status_message", results.get("status", "Тест завершён.")
                    ),
                    results.get("final_status", "N/A"),
                    results=results,
                )
                self._clear_intermediate_state()
                self.current_session_id = None
            else:
                self.student_view.show_message(
                    "Ошибка",
                    finish_result.get("error", "Не удалось завершить тест."),
                    is_error=True,
                )
            return

        self._save_intermediate_state()
        self._display_question_from_data(self.current_question_data)
        self.student_view.update_nav_panel(next_idx, self._frontier_idx)

    def handle_restart_test(self):
        if self.current_session_id:
            self.api.finish_session(self.current_session_id)
        self._clear_intermediate_state()
        self.current_session_id = None
        self.show_student_window(self.current_username)

    def handle_show_student_history_dialog(self):
        if not self.current_username:
            QMessageBox.warning(
                self.student_view, "Ошибка", "Не удалось определить пользователя."
            )
            return

        if self.student_test_history_view:
            self.student_test_history_view.close()
            self.student_test_history_view = None

        processed_student_history = self.api.get_user_history(self.current_username)

        if not processed_student_history:
            QMessageBox.information(
                self.student_view, "История тестов", "Вы еще не прошли ни одного теста."
            )
            return

        self.student_test_history_view = view.StudentTestHistoryDialog(
            student_username=self.current_username,
            history_data_list=processed_student_history,
            parent=self.student_view,
        )
        self.student_test_history_view.exec_()
        self.student_test_history_view = None

    def show_teacher_window(self):
        if self.teacher_view:
            self.teacher_view.close()
        self.teacher_view = view.TeachersWindow(username=self.current_username)
        self.teacher_view.add_question_signal.connect(self.handle_teacher_add_question)
        self.teacher_view.edit_questions_signal.connect(
            self.handle_teacher_edit_questions
        )
        self.teacher_view.create_premade_test_signal.connect(
            self.handle_show_create_premade_test_dialog
        )
        self.teacher_view.manage_premade_tests_signal.connect(
            self.handle_show_manage_premade_tests_dialog
        )
        self.teacher_view.generate_topic_score_test_signal.connect(
            self.handle_show_generate_topic_score_test_dialog
        )

        self.teacher_view.edit_grading_criteria_button.clicked.connect(
            lambda: self.handle_show_edit_grading_criteria_dialog(
                parent_widget=self.teacher_view
            )
        )
        self.teacher_view.toggle_theme_signal.connect(self.toggle_theme)
        self.teacher_view.logout_signal.connect(self.handle_logout)
        self.teacher_view.import_questions_signal.connect(
            lambda: self.handle_import_questions(parent=self.teacher_view)
        )
        self.teacher_view.change_password_signal.connect(
            lambda: self.handle_change_own_password(parent=self.teacher_view)
        )
        self.teacher_view.show()

    def handle_show_test_history(self):
        if self.test_history_view:
            self.test_history_view.close()
        self.test_history_view = view.TestHistoryWindow()
        self.test_history_view.user_selected_signal.connect(self.load_history_for_user)
        self.test_history_view.details_requested_signal.connect(self.show_test_details)

        all_history = self.api.get_test_history()
        if all_history:
            user_names = sorted(
                list(set(res["username"] for res in all_history if "username" in res))
            )
            self.test_history_view.populate_users(user_names)
        else:
            self.test_history_view.show_message(
                "История пуста", "Нет сохраненных результатов тестов.", is_error=False
            )

        self.test_history_view.exec_()

    def load_history_for_user(self, username):
        processed_user_history = self.api.get_user_history(username)
        if self.test_history_view:
            self.test_history_view.display_user_history(processed_user_history)

    def show_test_details(self, result_data_object):
        details_win = view.TestDetailsWindow(result_data_object)
        details_win.exec_()

    def handle_teacher_add_question(self):
        if self.add_question_view:
            self.add_question_view.close()
        topics = self.api.get_categories()
        self.add_question_view = view.AddQuestionWindow(topics=topics)
        self.add_question_view.save_question_signal.connect(self.save_new_question)
        self.add_question_view.exec_()

    def save_new_question(self, question_data_dict):
        topic = question_data_dict.pop("topic")
        success, msg = self.api.add_question(topic, question_data_dict)
        if self.add_question_view:
            if success:
                self.add_question_view.accept()
                if self._is_visible(self.edit_questions_view):
                    self.handle_teacher_edit_questions()
            else:
                QMessageBox.warning(self.add_question_view, "Ошибка", msg)

    def handle_teacher_edit_questions(self):
        if self.edit_questions_view:
            self.edit_questions_view.close()
        self._questions_cache = self.api.get_questions()
        self.edit_questions_view = view.EditQuestionsWindow(self._questions_cache)
        self.edit_questions_view.topic_selected_signal.connect(
            self.display_questions_for_topic_in_editor
        )
        self.edit_questions_view.edit_single_question_signal.connect(
            self.open_single_question_editor
        )
        self.edit_questions_view.show()

    def display_questions_for_topic_in_editor(self, topic_name):
        if self.edit_questions_view:
            questions_in_topic = self._questions_cache.get(topic_name, [])
            self.edit_questions_view.display_questions_for_topic(questions_in_topic)

    def open_single_question_editor(self, topic_name, question_index):
        if self.edit_single_question_view:
            self.edit_single_question_view.close()

        question_data_to_edit = self._questions_cache.get(topic_name, [])[
            question_index
        ]
        all_topics_list = list(self._questions_cache.keys())

        self.edit_single_question_view = view.EditSingleQuestionWindow(
            topic_name, question_data_to_edit, question_index, all_topics_list
        )
        self.edit_single_question_view.save_question_changes_signal.connect(
            self.save_edited_question
        )
        self.edit_single_question_view.delete_question_signal.connect(
            self.delete_edited_question
        )
        self.edit_single_question_view.exec_()

    def save_edited_question(
        self, new_topic_name, original_question_idx, new_question_data
    ):
        original_topic_name = self.edit_single_question_view.topic_name

        success = False
        msg = ""

        if new_topic_name != original_topic_name:
            s_del, m_del = self.api.delete_question(
                original_topic_name, original_question_idx
            )
            if s_del:
                s_add, m_add = self.api.add_question(new_topic_name, new_question_data)
                success = s_add
                msg = (
                    m_add
                    if s_add
                    else f"Ошибка добавления в новую тему: {m_add} (старый удален: {m_del})"
                )
            else:
                success = False
                msg = f"Ошибка удаления из старой темы: {m_del}"
        else:
            success, msg = self.api.update_question(
                original_topic_name, original_question_idx, new_question_data
            )

        if success:
            if self.edit_single_question_view:
                self.edit_single_question_view.accept()
            if self.edit_questions_view:
                self._questions_cache = self.api.get_questions()
                self.edit_questions_view.update_topics(self._questions_cache)
                if self.edit_questions_view.current_topic:
                    self.display_questions_for_topic_in_editor(
                        self.edit_questions_view.current_topic
                    )
            QMessageBox.information(None, "Успех", msg)
        else:
            if self.edit_single_question_view:
                self.edit_single_question_view.show_message(
                    "Ошибка", msg, is_error=True
                )
            else:
                QMessageBox.warning(None, "Ошибка", msg)

    def delete_edited_question(self, topic_name, question_index):
        success, msg = self.api.delete_question(topic_name, question_index)
        if success:
            if self.edit_single_question_view:
                self.edit_single_question_view.accept()
            if self.edit_questions_view:
                self._questions_cache = self.api.get_questions()
                self.edit_questions_view.update_topics(self._questions_cache)
                if self.edit_questions_view.current_topic:
                    self.display_questions_for_topic_in_editor(
                        self.edit_questions_view.current_topic
                    )
            QMessageBox.information(None, "Успех", msg)
        else:
            if self.edit_single_question_view:
                self.edit_single_question_view.show_message(
                    "Ошибка", msg, is_error=True
                )
            else:
                QMessageBox.warning(None, "Ошибка", msg)

    def handle_show_create_premade_test_dialog(self):
        if self.create_premade_test_dialog:
            self.create_premade_test_dialog.close()

        all_questions_structured = []
        self._questions_cache = self.api.get_questions()
        for topic, questions_list in self._questions_cache.items():
            for idx, q_data_original in enumerate(questions_list):
                q_data_copy = dict(q_data_original)
                if "category" not in q_data_copy or not q_data_copy["category"]:
                    q_data_copy["category"] = topic
                q_data_copy["_uid"] = f"{topic}__{idx}"
                display_text = f"Тема: {topic}"
                all_questions_structured.append(
                    {"display_text": display_text, "original_question": q_data_copy}
                )

        if not all_questions_structured:
            QMessageBox.information(
                self.teacher_view,
                "Нет вопросов",
                "В базе данных нет вопросов для создания теста.",
            )
            return

        self.create_premade_test_dialog = view.CreatePremadeTestDialog(
            all_questions_structured
        )
        self.create_premade_test_dialog.save_premade_test_signal.connect(
            self.handle_save_created_test
        )
        self.create_premade_test_dialog.edit_grading_criteria_signal.connect(
            self.handle_show_create_test_criteria_dialog
        )
        self.create_premade_test_dialog.exec_()

    def handle_show_create_test_criteria_dialog(self):

        dialog = self.create_premade_test_dialog
        if not dialog:
            return
        existing = dialog.pending_test_criteria
        if existing is None:
            defaults = self.api.get_criteria_for_editing(
                self.current_username, self.api.role
            )
            existing = (
                defaults.get("topic_criteria", []) if isinstance(defaults, dict) else []
            )
        criteria_dialog = view.EditGradingCriteriaDialog(existing, parent=dialog)
        criteria_dialog.setWindowTitle("Критерии оценки для создаваемого теста")
        criteria_dialog.save_criteria_signal.connect(dialog.set_criteria)
        criteria_dialog.exec_()

    def handle_save_created_test(
        self,
        test_name,
        selected_question_objects,
        time_limit_minutes=None,
        cooldown_hours=24,
        max_attempts=None,
    ):
        if not self.current_username:
            QMessageBox.warning(
                self.create_premade_test_dialog, "Ошибка", "Не определен пользователь."
            )
            return

        dlg = self.create_premade_test_dialog
        if dlg:
            time_limit_minutes = getattr(dlg, "time_limit_minutes_value", None)
            cooldown_hours = getattr(dlg, "cooldown_hours_value", 24)
            max_attempts = getattr(dlg, "max_attempts_value", None)
            grading_mode = getattr(dlg, "grading_mode_value", "overall")
            show_results = getattr(dlg, "show_results_value", True)

        success, msg, test_id = self.api.create_premade_test(
            test_name,
            selected_question_objects,
            time_limit_minutes=time_limit_minutes,
            cooldown_hours=cooldown_hours,
            max_attempts=max_attempts,
            grading_mode=grading_mode,
            show_results_to_students=show_results,
        )

        if success:

            pending = self.create_premade_test_dialog.pending_test_criteria
            if pending is not None and test_id:
                self.api.save_test_criteria(test_id, {"topic_criteria": pending})
            self.create_premade_test_dialog.show_message("Успех", msg)
            self.create_premade_test_dialog.accept()
        else:
            self.create_premade_test_dialog.show_message(
                "Ошибка сохранения", msg, is_error=True
            )

    def handle_show_manage_premade_tests_dialog(self):
        if self.test_management_dialog:
            self.test_management_dialog.reject()
            self.test_management_dialog = None
            self.manage_premade_tests_dialog = None

        if self.api.role == ROLE_ADMIN:
            premade_tests = self.api.get_all_premade_tests()
        else:
            premade_tests = self.api.get_premade_tests_for_creator(
                self.current_username
            )

        all_students = self.api.get_users_by_role(ROLE_STUDENT)
        all_groups = self.api.get_all_groups()
        students_by_group = {g: self.api.get_users_by_group(g) for g in all_groups}

        all_history = self.api.get_test_history()
        history_usernames = (
            sorted(list(set(r["username"] for r in all_history if "username" in r)))
            if all_history
            else []
        )

        dlg = view.TestManagementDialog(
            premade_tests,
            all_students,
            all_groups,
            students_by_group,
            history_usernames,
            parent=self.teacher_view,
        )
        self.test_management_dialog = dlg

        self.manage_premade_tests_dialog = dlg.manage_panel

        dlg.manage_panel.update_assignments_signal.connect(
            self.handle_update_test_assignments
        )
        dlg.manage_panel.delete_test_signal.connect(self.handle_delete_premade_test)
        dlg.manage_panel.delete_question_from_test_signal.connect(
            self.handle_delete_question_from_premade_test
        )
        dlg.manage_panel.edit_test_criteria_signal.connect(
            self.handle_show_test_criteria_dialog
        )
        dlg.manage_panel.show_test_statistics_signal.connect(
            self.handle_show_test_statistics_dialog
        )
        dlg.manage_panel.request_add_questions_signal.connect(
            self.handle_add_questions_to_test
        )
        dlg.manage_panel.clone_test_signal.connect(self.handle_clone_test)
        dlg.manage_panel.rename_test_signal.connect(self.handle_rename_test)
        dlg.manage_panel.edit_test_settings_signal.connect(
            self.handle_edit_test_settings
        )
        dlg.manage_panel.share_test_signal.connect(self.handle_share_test)
        dlg.manage_panel.unshare_test_signal.connect(self.handle_unshare_test)

        dlg.history_widget.load_user_history_signal.connect(
            self.handle_load_history_for_user_in_dialog
        )
        dlg.history_widget.load_group_history_signal.connect(
            self.handle_load_history_for_group_in_dialog
        )
        dlg.history_widget.show_details_signal.connect(self.show_test_details)
        dlg.history_widget.clear_history_signal.connect(self.handle_clear_history)

        dlg.exec_()
        self.test_management_dialog = None
        self.manage_premade_tests_dialog = None

    def _refresh_manage_tests_list(self, dialog):

        if self.api.role == ROLE_ADMIN:
            dialog.populate_tests_list(self.api.get_all_premade_tests())
        else:
            dialog.populate_tests_list(
                self.api.get_premade_tests_for_creator(self.current_username)
            )

    def handle_share_test(self, test_id: str):

        panel = self.manage_premade_tests_dialog
        if not panel:
            return
        success, data = self.api.share_test(test_id)
        if success:
            share_token = data.get("share_token")
            panel.set_share_token(share_token)
            QMessageBox.information(
                self.test_management_dialog or self.teacher_view,
                "Ссылка создана",
                "Ссылка для приглашения создана. Скопируйте её и отправьте студентам.",
            )
        else:
            QMessageBox.warning(
                self.test_management_dialog or self.teacher_view, "Ошибка", str(data)
            )

    def handle_unshare_test(self, test_id: str):

        panel = self.manage_premade_tests_dialog
        if not panel:
            return
        success, msg = self.api.unshare_test(test_id)
        if success:
            panel.set_share_token(None)
            QMessageBox.information(
                self.test_management_dialog or self.teacher_view,
                "Ссылка отозвана",
                "Ссылка для приглашения отозвана.",
            )
        else:
            QMessageBox.warning(
                self.test_management_dialog or self.teacher_view, "Ошибка", str(msg)
            )

    def handle_load_history_for_user_in_dialog(self, username):
        dlg = self.test_management_dialog
        if not dlg:
            return
        data = self.api.get_user_history(username)
        dlg.history_widget.display_history(data or [])

    def handle_load_history_for_group_in_dialog(self, group_name):
        dlg = self.test_management_dialog
        if not dlg:
            return
        all_history = self.api.get_test_history()
        if not all_history:
            dlg.history_widget.display_history([])
            return
        group_students = set(self.api.get_users_by_group(group_name))
        data = [r for r in all_history if r.get("username") in group_students]
        dlg.history_widget.display_history(data)

    def handle_add_questions_to_test(self, test_id: str):

        panel = self.manage_premade_tests_dialog
        if not panel:
            return
        self._questions_cache = self.api.get_questions()
        existing_qs = []
        if panel.current_selected_test_object:
            existing_qs = panel.current_selected_test_object.get("questions", [])

        parent = self.test_management_dialog or self.teacher_view
        picker = view.SelectQuestionsDialog(
            self._questions_cache, existing_qs, parent=parent
        )
        picker.questions_selected_signal.connect(
            lambda qs: self._do_add_questions(test_id, qs)
        )
        picker.exec_()

    def _do_add_questions(self, test_id: str, questions: list):
        success, msg, updated_test = self.api.add_questions_to_premade_test(
            test_id, questions
        )
        panel = self.manage_premade_tests_dialog
        if success and updated_test:
            if panel:
                panel.refresh_test_data(test_id, updated_test)
            QMessageBox.information(
                self.test_management_dialog or self.teacher_view,
                "Добавление вопросов",
                msg,
            )
        else:
            QMessageBox.warning(
                self.test_management_dialog or self.teacher_view, "Ошибка", msg
            )

    def handle_update_test_assignments(
        self, test_id, students_to_assign, students_to_unassign
    ):
        dialog = self.manage_premade_tests_dialog
        if not dialog:
            return

        success, messages, updated_test = self.api.batch_update_assignments(
            test_id, students_to_assign, students_to_unassign
        )

        if updated_test:
            dialog.refresh_test_data(test_id, updated_test)
        else:
            self._refresh_manage_tests_list(dialog)
            dialog.clear_details_and_assignments()

        final_message = "\n".join(messages)
        if success:
            dialog.show_message(
                "Обновление назначений",
                f"Изменения успешно применены.\n{final_message}",
            )
        else:
            dialog.show_message(
                "Обновление назначений",
                f"Ошибки при применении изменений.\n{final_message}",
                is_error=True,
            )

    def handle_delete_premade_test(self, test_id):
        dialog = self.manage_premade_tests_dialog
        if not dialog:
            QMessageBox.critical(
                None, "Ошибка", "Диалог управления тестами не доступен."
            )
            return

        success, message = self.api.delete_premade_test(test_id)

        if success:
            dialog.show_message("Удаление теста", message)
            self._refresh_manage_tests_list(dialog)
            dialog.clear_details_and_assignments()
        else:
            dialog.show_message("Ошибка удаления", message, is_error=True)

    def handle_delete_question_from_premade_test(self, test_id, question_index):
        dialog = self.manage_premade_tests_dialog
        if not dialog:
            QMessageBox.critical(
                None, "Ошибка", "Диалог управления тестами не доступен."
            )
            return

        success, message = self.api.delete_question_from_premade_test(
            test_id, question_index
        )

        if success:
            updated_test_data = self.api.get_premade_test_by_id(test_id)
            if updated_test_data:
                dialog.refresh_test_data(test_id, updated_test_data)
            else:
                dialog.show_message(
                    "Предупреждение", "Тест не найден после удаления вопроса.", True
                )
                self._refresh_manage_tests_list(dialog)
                dialog.clear_details_and_assignments()
        else:
            dialog.show_message("Ошибка удаления вопроса", message, is_error=True)

    def handle_show_generate_topic_score_test_dialog(self):
        if self.generate_topic_score_test_dialog:
            self.generate_topic_score_test_dialog.close()

        all_topics = self.api.get_categories()
        if not all_topics:
            QMessageBox.information(
                self.teacher_view,
                "Нет тем",
                "В базе данных нет тем для формирования теста.",
            )
            return

        self.generate_topic_score_test_dialog = view.GenerateTopicScoreTestDialog(
            all_topics, parent=self.teacher_view
        )
        self.generate_topic_score_test_dialog.generate_test_requested_signal.connect(
            self.handle_generate_test_by_topic_and_score
        )
        self.generate_topic_score_test_dialog.exec_()

    def handle_generate_test_by_topic_and_score(self, topic_name, max_score):
        generated_questions, actual_score, message = (
            self.api.generate_test_by_topic_and_score(topic_name, max_score)
        )

        if self.generate_topic_score_test_dialog:
            if generated_questions:
                self.generate_topic_score_test_dialog.accept()
                if (
                    hasattr(self, "display_generated_test_dialog")
                    and self.display_generated_test_dialog
                ):
                    self.display_generated_test_dialog.close()

                self.display_generated_test_dialog = view.DisplayGeneratedTestDialog(
                    generated_questions_list=generated_questions,
                    topic=topic_name,
                    max_score_requested=max_score,
                    actual_score=actual_score,
                    message=message,
                    parent=self.teacher_view,
                )
                self.display_generated_test_dialog.save_generated_test_as_premade_signal.connect(
                    self.handle_save_generated_test_as_premade
                )
                self.display_generated_test_dialog.exec_()
            else:
                self.generate_topic_score_test_dialog.show_message(
                    "Ошибка генерации", message, is_error=True
                )

    def handle_save_generated_test_as_premade(self, test_name, questions_list):
        if not self.current_username:
            QMessageBox.warning(
                self.display_generated_test_dialog,
                "Ошибка",
                "Не определен пользователь.",
            )
            return

        success, msg, _ = self.api.create_premade_test(test_name, questions_list)

        if self.display_generated_test_dialog:
            if success:
                QMessageBox.information(
                    self.display_generated_test_dialog, "Успех", msg
                )
                self.display_generated_test_dialog.save_as_premade_button.setEnabled(
                    False
                )
                self.display_generated_test_dialog.save_as_premade_button.setText(
                    "Сохранено"
                )
            else:
                QMessageBox.warning(
                    self.display_generated_test_dialog, "Ошибка сохранения", msg
                )

    def _get_criteria_parent_widget(self, parent_widget=None):
        if parent_widget:
            return parent_widget
        if self.api.role == ROLE_ADMIN and self.admin_view:
            return self.admin_view
        if self.api.role == ROLE_TEACHER and self.teacher_view:
            return self.teacher_view
        return None

    def handle_show_edit_grading_criteria_dialog(self, parent_widget=None):
        if self.edit_grading_criteria_view is not None:
            try:
                self.edit_grading_criteria_view.close()
            except RuntimeError:
                pass
            self.edit_grading_criteria_view = None

        criteria_config = self.api.get_criteria_for_editing(
            self.current_username, self.api.role
        )
        default_criteria = self.api.get_default_criteria()
        topic_criteria_list = criteria_config.get(
            "topic_criteria", default_criteria.get("topic_criteria", [])
        )

        dialog = view.EditGradingCriteriaDialog(
            topic_criteria_list, parent=self._get_criteria_parent_widget(parent_widget)
        )
        self.edit_grading_criteria_view = dialog
        dialog.save_criteria_signal.connect(self.handle_save_grading_criteria)
        dialog.reset_criteria_signal.connect(self.handle_reset_grading_criteria)

        try:
            dialog.exec_()
        finally:
            if self.edit_grading_criteria_view == dialog:
                self.edit_grading_criteria_view = None

    def handle_save_grading_criteria(self, new_topic_criteria_list):
        success, msg = self.api.save_criteria(
            self.current_username,
            self.api.role,
            {"topic_criteria": new_topic_criteria_list},
        )
        parent = self.edit_grading_criteria_view or self._get_criteria_parent_widget()
        if success:
            QMessageBox.information(parent, "Успех", msg)
            if self.edit_grading_criteria_view:
                try:
                    self.edit_grading_criteria_view.accept()
                except RuntimeError:
                    self.edit_grading_criteria_view = None
        else:
            QMessageBox.warning(parent, "Ошибка сохранения", msg)

    def handle_reset_grading_criteria(self):
        default_criteria_config = self.api.get_default_criteria()
        success, message = self.api.save_criteria(
            self.current_username, self.api.role, default_criteria_config
        )
        parent = self.edit_grading_criteria_view or self._get_criteria_parent_widget()

        if success:
            if self._is_visible(self.edit_grading_criteria_view):
                self.edit_grading_criteria_view.load_criteria(
                    default_criteria_config.get("topic_criteria", [])
                )
            QMessageBox.information(
                parent, "Успех", "Критерии оценки сброшены к значениям по умолчанию."
            )
        else:
            QMessageBox.critical(parent, "Ошибка", message)

    def handle_show_test_criteria_dialog(self, test_id):

        if not test_id:
            return

        criteria_config = self.api.get_test_criteria(test_id)
        if criteria_config is None:
            default_criteria = self.api.get_default_criteria()
            topic_criteria_list = default_criteria.get("topic_criteria", [])
        else:
            topic_criteria_list = criteria_config.get("topic_criteria", [])

        parent = self.manage_premade_tests_dialog or self._get_criteria_parent_widget()
        dialog = view.EditGradingCriteriaDialog(topic_criteria_list, parent=parent)
        dialog.setWindowTitle("Критерии оценки для этого теста")
        dialog.save_criteria_signal.connect(
            lambda lst: self.handle_save_test_criteria(test_id, lst)
        )
        dialog.reset_criteria_signal.connect(
            lambda: self._reset_test_criteria_to_default(test_id, dialog)
        )
        dialog.exec_()

    def handle_save_test_criteria(self, test_id, new_topic_criteria_list):
        success, msg = self.api.save_test_criteria(
            test_id, {"topic_criteria": new_topic_criteria_list}
        )
        parent = self.manage_premade_tests_dialog or self._get_criteria_parent_widget()
        if success:
            QMessageBox.information(parent, "Успех", msg)
        else:
            QMessageBox.warning(parent, "Ошибка сохранения", msg)

    def _reset_test_criteria_to_default(self, test_id, dialog):
        default_criteria_config = self.api.get_default_criteria()
        success, message = self.api.save_test_criteria(test_id, default_criteria_config)
        if success:
            dialog.load_criteria(default_criteria_config.get("topic_criteria", []))
            QMessageBox.information(
                dialog, "Успех", "Критерии для теста сброшены к значениям по умолчанию."
            )
        else:
            QMessageBox.critical(dialog, "Ошибка", message)

    def show_admin_window(self):
        if self.admin_view:
            self.admin_view.close()
        self.admin_view = view.AdminWindow()
        self.admin_view.open_teacher_view_signal.connect(self.handle_admin_as_teacher)
        self.admin_view.open_student_view_signal.connect(self.handle_admin_as_student)
        self.admin_view.manage_users_signal.connect(
            self.handle_show_manage_user_roles_dialog
        )
        self.admin_view.manage_groups_signal.connect(
            self.handle_show_manage_groups_dialog
        )

        self.admin_view.edit_grading_criteria_signal.connect(
            lambda: self.handle_show_edit_grading_criteria_dialog(
                parent_widget=self.admin_view
            )
        )
        self.admin_view.toggle_theme_signal.connect(self.toggle_theme)
        self.admin_view.logout_signal.connect(self.handle_logout)
        self.admin_view.show()

    def handle_admin_as_teacher(self):
        self.show_teacher_window()

    def handle_admin_as_student(self):
        self.show_student_window(self.current_username)

    def handle_show_manage_user_roles_dialog(self):
        all_users_data = self.api.get_all_users()
        all_groups = self.api.get_all_groups() or []

        if self._is_visible(self.role_management_view):
            self.role_management_view.raise_()
            self.role_management_view.activateWindow()
            return

        self.role_management_view = view.ManageUserRolesDialog(
            all_users_data=all_users_data,
            current_admin_username=self.current_username,
            all_groups=all_groups,
            parent=self.admin_view,
        )
        self.role_management_view.save_user_changes_signal.connect(
            self.handle_save_user_changes
        )
        self.role_management_view.delete_user_signal.connect(self.handle_delete_user)
        self.role_management_view.change_password_signal.connect(
            self.handle_admin_change_password
        )
        self.role_management_view.edit_full_name_signal.connect(
            self.handle_edit_full_name
        )
        self.role_management_view.show()

    def handle_show_manage_groups_dialog(self):
        groups = self.api.get_all_groups() or []
        dlg = view.ManageGroupsDialog(groups, self.api, parent=self.admin_view)
        dlg.exec_()

    def handle_save_user_roles(self, changed_roles_map):
        if not changed_roles_map:
            QMessageBox.information(
                self.role_management_view, "Информация", "Изменений не было."
            )
            return

        all_successful = True
        error_messages = []

        for username, new_role in changed_roles_map.items():
            success, message = self.api.change_user_role(username, new_role)
            if not success:
                all_successful = False
                error_messages.append(
                    f"Не удалось изменить роль для {username}: {message}"
                )

        if all_successful:
            QMessageBox.information(
                self.role_management_view,
                "Успех",
                "Роли пользователей успешно обновлены.",
            )
            if self.role_management_view:
                self.role_management_view.close()
        else:
            QMessageBox.critical(
                self.role_management_view,
                "Ошибка обновления ролей",
                "\n".join(error_messages),
            )

    def handle_save_user_changes(self, changed_roles_map, changed_groups_map):
        if not changed_roles_map and not changed_groups_map:
            QMessageBox.information(
                self.role_management_view, "Информация", "Изменений не было."
            )
            return

        all_successful = True
        error_messages = []

        for username, new_group in changed_groups_map.items():
            success, message = self.api.change_user_group(username, new_group)
            if not success:
                all_successful = False
                error_messages.append(
                    f"Не удалось изменить группу для {username}: {message}"
                )

        for username, new_role in changed_roles_map.items():
            success, message = self.api.change_user_role(username, new_role)
            if not success:
                all_successful = False
                error_messages.append(
                    f"Не удалось изменить роль для {username}: {message}"
                )

        if all_successful:
            QMessageBox.information(
                self.role_management_view,
                "Успех",
                "Данные пользователей успешно обновлены.",
            )
            if self.role_management_view:
                self.role_management_view.close()
        else:
            QMessageBox.critical(
                self.role_management_view,
                "Ошибка обновления пользователей",
                "\n".join(error_messages),
            )

    def handle_show_test_statistics_dialog(self, test_id, test_name):
        results = self.api.get_test_results(test_id)
        aggregate_stats = self.api.get_test_aggregate_stats(test_id)
        parent = self.manage_premade_tests_dialog or self.teacher_view

        students_by_group = {}
        for grp in self.api.get_all_groups():
            students_by_group[grp] = self.api.get_users_by_group(grp)
        dlg = view.TestStatisticsDialog(
            test_name,
            results,
            students_by_group=students_by_group,
            aggregate_stats=aggregate_stats,
            parent=parent,
        )
        dlg.export_csv_signal.connect(
            lambda: self.handle_export_results_csv(test_name, results)
        )
        dlg.exec_()

    def handle_export_results_csv(self, test_name, results):
        parent = self.manage_premade_tests_dialog or self.teacher_view
        default_name = test_name.replace(" ", "_") + "_results.csv"
        path, _ = QFileDialog.getSaveFileName(
            parent, "Сохранить CSV", default_name, "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(
                    ["Студент", "Дата", "Длительность", "Итог", "Статус", "Правильных"]
                )
                for r in results:
                    correct = r.get("answers", [])
                    correct_count = (
                        sum(
                            1
                            for a in correct
                            if str(a.get("user_answer", "")).strip()
                            == str(a.get("correct_answer", "")).strip()
                        )
                        if correct
                        else ""
                    )
                    writer.writerow(
                        [
                            r.get("username", ""),
                            r.get("start_time", ""),
                            r.get("duration", ""),
                            r.get("final_status", ""),
                            r.get("status", ""),
                            correct_count,
                        ]
                    )
            QMessageBox.information(
                parent, "Экспорт завершён", f"Файл сохранён:\n{path}"
            )
        except Exception as e:
            QMessageBox.warning(parent, "Ошибка экспорта", str(e))

    def handle_change_own_password(self, parent=None):
        parent = parent or self.student_view or self.teacher_view
        old_pwd, ok1 = QInputDialog.getText(
            parent,
            "Смена пароля",
            "Текущий пароль:",
            QInputDialog.Normal if hasattr(QInputDialog, "Normal") else 0,
        )
        if not ok1 or not old_pwd:
            return
        new_pwd, ok2 = QInputDialog.getText(
            parent,
            "Смена пароля",
            "Новый пароль (мин. 6 символов):",
            QInputDialog.Normal if hasattr(QInputDialog, "Normal") else 0,
        )
        if not ok2 or not new_pwd:
            return
        if len(new_pwd) < 6:
            QMessageBox.warning(
                parent, "Ошибка", "Новый пароль должен быть не менее 6 символов."
            )
            return
        success, msg = self.api.change_password(self.current_username, old_pwd, new_pwd)
        if success:
            QMessageBox.information(parent, "Успех", msg)
        else:
            QMessageBox.warning(parent, "Ошибка", msg)

    def handle_import_questions(self, parent=None):
        parent = parent or self.teacher_view
        path, _ = QFileDialog.getOpenFileName(
            parent, "Импорт вопросов из JSON", "", "JSON files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.warning(parent, "Ошибка чтения файла", str(e))
            return

        if isinstance(data, dict):

            questions = []
            for topic, qs in data.items():
                if isinstance(qs, list):
                    for q in qs:
                        if isinstance(q, dict) and "topic" not in q:
                            q["topic"] = topic
                        questions.append(q)
        elif isinstance(data, list):
            questions = data
        else:
            QMessageBox.warning(
                parent,
                "Ошибка",
                "JSON должен содержать массив вопросов или словарь {тема: [вопросы]}.",
            )
            return

        if not questions:
            QMessageBox.warning(parent, "Ошибка", "Не найдено вопросов для импорта.")
            return

        success, msg, result = self.api.bulk_import_questions(questions)
        if success:
            imported = result.get("imported", 0) if result else 0
            errors = result.get("errors", []) if result else []
            detail = f"Импортировано: {imported}"
            if errors:
                detail += f"\nОшибки ({len(errors)}):\n" + "\n".join(
                    str(e) for e in errors[:10]
                )
            QMessageBox.information(parent, "Импорт завершён", detail)
        else:
            QMessageBox.warning(parent, "Ошибка импорта", msg)

    def handle_rename_test(self, test_id, new_name):
        panel = self.manage_premade_tests_dialog
        parent = self.test_management_dialog or self.teacher_view
        success, msg = self.api.rename_premade_test(test_id, new_name)
        if success:
            QMessageBox.information(parent, "Переименование теста", msg)
            if panel:
                self._refresh_manage_tests_list(panel)
        else:
            QMessageBox.warning(parent, "Ошибка", msg)

    def handle_clone_test(self, test_id):
        panel = self.manage_premade_tests_dialog
        parent = self.test_management_dialog or self.teacher_view
        success, msg, new_test = self.api.clone_premade_test(test_id)
        if success:
            QMessageBox.information(parent, "Клонирование теста", msg)
            if panel:
                self._refresh_manage_tests_list(panel)
        else:
            QMessageBox.warning(parent, "Ошибка", msg)

    def handle_delete_user(self, username):
        success, msg = self.api.delete_user(username)
        parent = self.role_management_view or self.admin_view
        if success:
            QMessageBox.information(parent, "Удаление пользователя", msg)

            if self._is_visible(self.role_management_view):
                all_users_data = self.api.get_all_users()
                self.role_management_view.refresh_users(all_users_data)
        else:
            QMessageBox.warning(parent, "Ошибка", msg)

    def handle_admin_change_password(self, username, new_pwd):
        success, msg = self.api.reset_password(username, new_pwd)
        parent = self.role_management_view or self.admin_view
        if success:
            QMessageBox.information(parent, "Сброс пароля", msg)
        else:
            QMessageBox.warning(parent, "Ошибка", msg)

    def handle_edit_full_name(self, username, current_name):
        new_name, ok = QInputDialog.getText(
            self.role_management_view,
            "Изменить ФИО",
            f"Новое ФИО для {username}:",
            text=current_name,
        )
        if not ok:
            return
        success, msg = self.api.update_user_full_name(username, new_name.strip())
        parent = self.role_management_view or self.admin_view
        if success:
            QMessageBox.information(parent, "ФИО обновлено", msg)
            if self._is_visible(self.role_management_view):
                all_users_data = self.api.get_all_users()
                all_groups = self.api.get_all_groups() or []
                self.role_management_view.refresh_users(all_users_data, all_groups)
        else:
            QMessageBox.warning(parent, "Ошибка", msg)

    def handle_edit_test_settings(self, test_id, test_object):
        dlg = QDialog(self.test_management_dialog or self.teacher_view)
        dlg.setWindowTitle(f"Настройки: {test_object.get('test_name', '')}")
        dlg.setMinimumWidth(400)
        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel("Время на прохождение (минуты, 0 = без ограничения):"))
        time_spin = QSpinBox()
        time_spin.setRange(0, 999)
        time_spin.setValue(test_object.get("time_limit_minutes") or 0)
        layout.addWidget(time_spin)

        layout.addWidget(QLabel("Кулдаун между попытками (часы, 0 = без кулдауна):"))
        cooldown_spin = QSpinBox()
        cooldown_spin.setRange(0, 999)
        cooldown_spin.setValue(
            test_object.get("cooldown_hours")
            if test_object.get("cooldown_hours") is not None
            else 24
        )
        layout.addWidget(cooldown_spin)

        layout.addWidget(QLabel("Максимальное количество попыток (0 = неограниченно):"))
        attempts_spin = QSpinBox()
        attempts_spin.setRange(0, 999)
        attempts_spin.setValue(test_object.get("max_attempts") or 0)
        layout.addWidget(attempts_spin)

        layout.addWidget(QLabel("Режим оценки:"))
        grading_combo = QComboBox()
        grading_combo.addItem("Общий (по всему тесту)", "overall")
        grading_combo.addItem("По темам (все темы должны быть зачтены)", "per_topic")
        current_mode = test_object.get("grading_mode", "overall")
        grading_combo.setCurrentIndex(0 if current_mode != "per_topic" else 1)
        layout.addWidget(grading_combo)

        show_results_check = QCheckBox(
            "Показывать результаты студентам (правильные ответы)"
        )
        show_results_check.setChecked(test_object.get("show_results_to_students", True))
        layout.addWidget(show_results_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(
            lambda: self._do_update_test_settings(
                test_id,
                time_spin.value(),
                cooldown_spin.value(),
                attempts_spin.value(),
                grading_combo.currentData(),
                show_results_check.isChecked(),
                dlg,
            )
        )
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        dlg.exec_()

    def _do_update_test_settings(
        self,
        test_id,
        time_limit,
        cooldown,
        max_attempts,
        grading_mode,
        show_results,
        dlg,
    ):
        settings = {
            "time_limit_minutes": time_limit if time_limit > 0 else None,
            "cooldown_hours": cooldown,
            "max_attempts": max_attempts if max_attempts > 0 else None,
            "grading_mode": grading_mode,
            "show_results_to_students": show_results,
        }
        success, msg = self.api.update_test_settings(test_id, settings)
        parent = self.test_management_dialog or self.teacher_view
        if success:
            QMessageBox.information(parent, "Настройки сохранены", msg)
            dlg.accept()
            panel = self.manage_premade_tests_dialog
            if panel:
                self._refresh_manage_tests_list(panel)
        else:
            QMessageBox.warning(parent, "Ошибка", msg)

    def handle_clear_history(self, mode, target):
        parent = self.test_management_dialog or self.teacher_view
        if mode == "student":
            success, result = self.api.clear_history(username=target)
        else:
            success, result = self.api.clear_history(test_id=target)
        if success:
            deleted = result.get("deleted", 0) if isinstance(result, dict) else 0
            QMessageBox.information(
                parent, "История очищена", f"Удалено записей: {deleted}"
            )
        else:
            QMessageBox.warning(
                parent,
                "Ошибка",
                (
                    str(result)
                    if isinstance(result, str)
                    else "Не удалось очистить историю"
                ),
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AppController()
    controller.start_app()
    sys.exit(app.exec_())
