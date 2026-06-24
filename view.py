import sys
import re
import random
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QMainWindow,
    QScrollArea,
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QRadioButton,
    QComboBox,
    QButtonGroup,
    QPushButton,
    QDialog,
    QLineEdit,
    QMessageBox,
    QHBoxLayout,
    QListWidget,
    QTableWidget,
    QTableWidgetItem,
    QStackedWidget,
    QAbstractItemView,
    QCheckBox,
    QDialogButtonBox,
    QPlainTextEdit,
    QFrame,
    QGridLayout,
    QSpacerItem,
    QSizePolicy,
    QHeaderView,
    QGroupBox,
    QTabWidget,
    QCompleter,
    QInputDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QSettings, QSortFilterProxyModel, QTimer
from PyQt5.QtGui import QFont


def _save_window_geometry(window, key: str) -> None:

    s = QSettings("TestingExpertSystem", "WindowGeometry")
    s.setValue(key, window.saveGeometry())


def _restore_window_geometry(window, key: str) -> None:

    s = QSettings("TestingExpertSystem", "WindowGeometry")
    data = s.value(key)
    if data:
        window.restoreGeometry(data)


def _save_column_widths(table, key: str) -> None:

    s = QSettings("TestingExpertSystem", "ColumnWidths")
    header = table.horizontalHeader()
    widths = [header.sectionSize(i) for i in range(header.count())]
    s.setValue(key, widths)


def _restore_column_widths(table, key: str) -> None:

    s = QSettings("TestingExpertSystem", "ColumnWidths")
    data = s.value(key)
    if data:
        header = table.horizontalHeader()
        widths = [int(w) for w in data]
        for i, w in enumerate(widths):
            if i < header.count() and w > 0:
                header.resizeSection(i, w)


ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"
ROLE_UNASSIGNED = "unassigned"


class LoginWindow(QWidget):

    login_attempt = pyqtSignal(str, str)
    register_attempt = pyqtSignal(str, str, str, str)
    join_by_share_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Система тестирования - Вход/Регистрация")
        self.setGeometry(100, 100, 520, 520)
        self._pending_share_token = None
        self.init_ui()
        _restore_window_geometry(self, "LoginWindow")

    def closeEvent(self, event):
        _save_window_geometry(self, "LoginWindow")
        super().closeEvent(event)

    def init_ui(self):
        self._register_mode = False
        layout = QVBoxLayout()
        layout.setSpacing(10)

        self.label = QLabel("Добро пожаловать в систему тестирования!")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setObjectName("welcomeLabel")
        layout.addWidget(self.label)

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Имя пользователя")
        self.username_input.setFixedHeight(35)
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(35)
        layout.addWidget(self.password_input)

        self.group_label = QLabel("Группа (необязательно):")
        self.group_label.setVisible(False)
        layout.addWidget(self.group_label)

        self.group_input = QComboBox(self)
        self.group_input.setFixedHeight(35)
        self.group_input.addItem("— Без группы —", "")
        self.group_input.setVisible(False)
        layout.addWidget(self.group_input)

        self.full_name_label = QLabel("ФИО (необязательно):")
        self.full_name_label.setVisible(False)
        layout.addWidget(self.full_name_label)

        self.full_name_input = QLineEdit(self)
        self.full_name_input.setPlaceholderText("Иванов Иван Иванович")
        self.full_name_input.setFixedHeight(35)
        self.full_name_input.setVisible(False)
        layout.addWidget(self.full_name_input)

        self.login_button = QPushButton("Войти", self)
        self.login_button.setFixedHeight(40)
        self.login_button.clicked.connect(self.on_login_button_click)
        layout.addWidget(self.login_button)

        self.register_button = QPushButton("Нет аккаунта? Регистрация", self)
        self.register_button.setFixedHeight(40)
        self.register_button.clicked.connect(self.on_register_button_click)
        layout.addWidget(self.register_button)

        self.share_link_label = QLabel("Или вставьте ссылку-приглашение на тест:")
        self.share_link_label.setObjectName("shareLinkLabel")
        layout.addWidget(self.share_link_label)

        share_row = QHBoxLayout()
        self.share_link_input = QLineEdit(self)
        self.share_link_input.setPlaceholderText("https://... или код приглашения")
        self.share_link_input.setFixedHeight(35)
        share_row.addWidget(self.share_link_input)
        self.join_by_share_button = QPushButton("Присоединиться")
        self.join_by_share_button.setFixedHeight(35)
        self.join_by_share_button.clicked.connect(self._on_join_by_share_clicked)
        share_row.addWidget(self.join_by_share_button)
        layout.addLayout(share_row)

        self.setLayout(layout)

    def on_login_button_click(self):
        if self._register_mode:

            self._register_mode = False
            self.group_label.setVisible(False)
            self.group_input.setVisible(False)
            self.full_name_label.setVisible(False)
            self.full_name_input.setVisible(False)
            self.login_button.setText("Войти")
            self.register_button.setText("Нет аккаунта? Регистрация")
        else:
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()
            self.login_attempt.emit(username, password)

    def on_register_button_click(self):
        if not self._register_mode:

            self._register_mode = True
            self.group_label.setVisible(True)
            self.group_input.setVisible(True)
            self.full_name_label.setVisible(True)
            self.full_name_input.setVisible(True)
            self.login_button.setText("← Назад")
            self.register_button.setText("Зарегистрироваться")
        else:
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()
            group = self.group_input.currentData() or ""
            full_name = self.full_name_input.text().strip()
            self.register_attempt.emit(username, password, group, full_name)

    def show_message(self, title, message, is_error=False):
        if is_error:
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def set_groups(self, groups):

        self.group_input.clear()
        self.group_input.addItem("— Без группы —", "")
        for g in groups:
            self.group_input.addItem(g, g)

    def _on_join_by_share_clicked(self):
        raw = self.share_link_input.text().strip()
        if not raw:
            self.show_message(
                "Ошибка", "Введите ссылку или код приглашения.", is_error=True
            )
            return

        token = self._extract_share_token(raw)
        if not token:
            self.show_message(
                "Ошибка", "Не удалось извлечь код приглашения из ссылки.", is_error=True
            )
            return
        self._pending_share_token = token
        self.join_by_share_signal.emit(token)

    @staticmethod
    def _extract_share_token(raw: str) -> str:

        m = re.search(r"/join/([a-f0-9]{20,})", raw, re.IGNORECASE)
        if m:
            return m.group(1)

        if re.match(r"^[a-f0-9]{20,}$", raw, re.IGNORECASE):
            return raw
        return ""

    def get_pending_share_token(self):

        token = self._pending_share_token
        self._pending_share_token = None
        return token


class StudentWindow(QWidget):
    show_my_history_signal = pyqtSignal()
    start_assigned_test_signal = pyqtSignal(object)
    next_question_signal = pyqtSignal(int, object)
    restart_test_signal = pyqtSignal()
    toggle_theme_signal = pyqtSignal()
    logout_signal = pyqtSignal()
    timeout_signal = pyqtSignal()
    navigate_to_question_signal = pyqtSignal(int)
    resume_active_session_signal = pyqtSignal()
    change_password_signal = pyqtSignal()
    join_by_share_signal = pyqtSignal(str)

    def __init__(
        self,
        username,
        assigned_tests_list=None,
        eligibility_data=None,
        active_session_test_id=None,
    ):
        super().__init__()
        self.username = username
        self.assigned_tests_by_teacher = (
            assigned_tests_list if assigned_tests_list else {}
        )
        self.current_selected_assigned_test = None
        self.eligibility_data = eligibility_data if eligibility_data else {}
        self.active_session_test_id = active_session_test_id
        self.current_answer_type = "single"
        self._countdown_seconds = None
        self._qt_timer = None
        self._current_nav_idx = 0
        self._total_nav_questions = 0
        self.setWindowTitle(f"Система тестирования - {self.username}")
        self.setGeometry(100, 100, 1150, 900)
        self.init_ui()
        _restore_window_geometry(self, "StudentWindow")

    def closeEvent(self, event):
        _save_window_geometry(self, "StudentWindow")
        super().closeEvent(event)

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setSpacing(20)

        self.welcome_label = QLabel(f"Добро пожаловать, {self.username}!")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        font = QtGui.QFont("Arial", 24)
        self.welcome_label.setFont(font)
        self.layout.addWidget(self.welcome_label)

        self.my_history_button = QPushButton("Моя история тестов", self)
        self.my_history_button.setFont(QtGui.QFont("Arial", 18))
        self.my_history_button.setMinimumHeight(50)
        self.my_history_button.clicked.connect(self.on_show_my_history_click)
        self.layout.addWidget(self.my_history_button)

        self.assigned_tests_group = QtWidgets.QGroupBox("Назначенные вам тесты")
        self.assigned_tests_layout = QVBoxLayout(self.assigned_tests_group)

        self.teacher_filter_layout = QHBoxLayout()
        self.teacher_filter_layout.addWidget(QLabel("Выберите преподавателя:"))
        self.teacher_filter_combo = QComboBox()
        self.teacher_filter_combo.currentTextChanged.connect(
            self.on_teacher_selected_from_filter
        )
        self.teacher_filter_layout.addWidget(self.teacher_filter_combo)
        self.assigned_tests_layout.addLayout(self.teacher_filter_layout)

        self.assigned_tests_list_widget = QListWidget()
        self.assigned_tests_list_widget.itemClicked.connect(
            self.on_assigned_test_selected
        )
        self.assigned_tests_layout.addWidget(self.assigned_tests_list_widget)
        self.start_assigned_test_button = QPushButton(
            "Пройти выбранный назначенный тест"
        )
        self.start_assigned_test_button.setFont(QtGui.QFont("Arial", 16))
        self.start_assigned_test_button.setMinimumHeight(45)
        self.start_assigned_test_button.clicked.connect(
            self.on_start_assigned_test_click
        )
        self.start_assigned_test_button.setEnabled(False)
        self.assigned_tests_layout.addWidget(self.start_assigned_test_button)
        self.layout.addWidget(self.assigned_tests_group)

        self.nav_panel = QWidget(self)
        _nav_main_layout = QVBoxLayout(self.nav_panel)
        _nav_main_layout.setContentsMargins(0, 4, 0, 4)
        _nav_main_layout.setSpacing(3)

        _nav_title_row = QHBoxLayout()
        self._nav_progress_label = QLabel("")
        self._nav_progress_label.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        _nav_title_row.addWidget(self._nav_progress_label)
        _nav_title_row.addStretch()
        _nav_main_layout.addLayout(_nav_title_row)

        self._nav_scroll_area = QScrollArea()
        self._nav_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._nav_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._nav_scroll_area.setFixedHeight(50)
        self._nav_scroll_area.setFrameShape(QFrame.NoFrame)
        self._nav_btns_container = QWidget()
        self._nav_btns_layout = QHBoxLayout(self._nav_btns_container)
        self._nav_btns_layout.setSpacing(3)
        self._nav_btns_layout.setContentsMargins(2, 2, 2, 2)
        self._nav_scroll_area.setWidget(self._nav_btns_container)
        self._nav_scroll_area.setWidgetResizable(True)
        _nav_main_layout.addWidget(self._nav_scroll_area)

        _nav_controls_row = QHBoxLayout()
        self.prev_q_button = QPushButton("◀ Назад")
        self.prev_q_button.setFixedWidth(110)
        self.prev_q_button.setEnabled(False)
        self.prev_q_button.clicked.connect(self._on_prev_q_click)
        _nav_controls_row.addWidget(self.prev_q_button)
        self._review_mode_label = QLabel("")
        self._review_mode_label.setStyleSheet("color: orange; font-style: italic;")
        _nav_controls_row.addWidget(self._review_mode_label)
        _nav_controls_row.addStretch()
        _nav_main_layout.addLayout(_nav_controls_row)

        self.layout.addWidget(self.nav_panel)
        self.nav_panel.hide()

        self.question_label = QLabel("", self)
        self.question_label.setFont(QtGui.QFont("Arial", 16))
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.question_label)
        self.layout.addSpacing(15)

        self.media_layout_container = QWidget()
        self.media_layout = QVBoxLayout(self.media_layout_container)
        self.media_layout.setSpacing(10)
        self.layout.addWidget(self.media_layout_container)

        self.options_group = QButtonGroup(self)
        self.options_widgets_list = []
        self.options_layout = QVBoxLayout()
        self.layout.addLayout(self.options_layout)

        self.next_button = QPushButton("Далее", self)
        self.next_button.setFont(QtGui.QFont("Arial", 18))
        self.next_button.setMinimumHeight(50)
        self.next_button.clicked.connect(self.on_next_question_click)
        self.next_button.hide()
        self.layout.addWidget(self.next_button)

        self.timer_label = QLabel("", self)
        self.timer_label.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.hide()
        self.layout.addWidget(self.timer_label)

        self.results_label = QLabel("", self)
        self.results_label.setFont(QtGui.QFont("Arial", 20, QtGui.QFont.Bold))
        self.results_label.setAlignment(Qt.AlignCenter)
        self.results_label.setWordWrap(True)
        self.layout.addWidget(self.results_label)

        self.restart_button = QPushButton("Пройти тест еще раз", self)
        self.restart_button.setFont(QtGui.QFont("Arial", 18))
        self.restart_button.setMinimumHeight(50)
        self.restart_button.clicked.connect(self.on_restart_click)
        self.restart_button.hide()
        self.layout.addWidget(self.restart_button)

        self.change_password_button_student = QPushButton("Сменить пароль", self)
        self.change_password_button_student.setFont(QtGui.QFont("Arial", 12))
        self.change_password_button_student.setMinimumHeight(35)
        self.change_password_button_student.clicked.connect(
            self.change_password_signal.emit
        )
        self.layout.addWidget(self.change_password_button_student)

        self.theme_toggle_button_student = QPushButton("Сменить тему", self)
        self.theme_toggle_button_student.setFont(QtGui.QFont("Arial", 12))
        self.theme_toggle_button_student.setMinimumHeight(35)
        self.theme_toggle_button_student.clicked.connect(self.toggle_theme_signal.emit)
        self.layout.addWidget(self.theme_toggle_button_student)

        self.join_by_share_button_student = QPushButton(
            "Присоединиться по ссылке", self
        )
        self.join_by_share_button_student.setFont(QtGui.QFont("Arial", 12))
        self.join_by_share_button_student.setMinimumHeight(35)
        self.join_by_share_button_student.clicked.connect(
            self._on_join_by_share_student_clicked
        )
        self.layout.addWidget(self.join_by_share_button_student)

        self.logout_button = QPushButton("Выйти из аккаунта", self)
        self.logout_button.setFont(QtGui.QFont("Arial", 12))
        self.logout_button.setMinimumHeight(35)
        self.logout_button.clicked.connect(self.logout_signal.emit)
        self.layout.addWidget(self.logout_button)

        self.layout.addStretch(1)
        self.setLayout(self.layout)
        self.display_assigned_tests()

    def display_assigned_tests(self):
        self.teacher_filter_combo.blockSignals(True)
        self.teacher_filter_combo.clear()
        self.assigned_tests_list_widget.clear()
        self.start_assigned_test_button.setEnabled(False)

        if self.assigned_tests_by_teacher:
            self.assigned_tests_group.show()

            teacher_names = sorted(self.assigned_tests_by_teacher.keys())
            if not teacher_names:
                self.teacher_filter_combo.addItem(
                    "Нет назначенных тестов от преподавателей"
                )
                self.teacher_filter_combo.setEnabled(False)
                self.assigned_tests_list_widget.addItem("Нет тестов для отображения")
            else:
                self.teacher_filter_combo.addItem("-- Выберите преподавателя --")
                self.teacher_filter_combo.addItems(teacher_names)
                self.teacher_filter_combo.setEnabled(True)

        else:
            self.assigned_tests_group.hide()

            self.teacher_filter_combo.setEnabled(False)

        self.teacher_filter_combo.blockSignals(False)

        if self.teacher_filter_combo.currentIndex() <= 0:
            self.assigned_tests_list_widget.clear()
            self.assigned_tests_list_widget.addItem(
                "Выберите преподавателя для просмотра назначенных тестов"
            )

    def on_teacher_selected_from_filter(self, teacher_username):
        self.assigned_tests_list_widget.clear()
        self.current_selected_assigned_test = None
        self.start_assigned_test_button.setEnabled(False)

        if teacher_username == "-- Выберите преподавателя --" or not teacher_username:
            self.assigned_tests_list_widget.addItem(
                "Выберите преподавателя для просмотра назначенных тестов"
            )
            return

        tests_from_selected_teacher = self.assigned_tests_by_teacher.get(
            teacher_username, []
        )
        if tests_from_selected_teacher:
            for test in tests_from_selected_teacher:
                test_name = test.get("test_name", "Безымянный тест")
                test_id = test.get("test_id")
                is_active = test_id and test_id == self.active_session_test_id

                display_text = (
                    ("▶ [Активный]  " + test_name) if is_active else test_name
                )

                if test_id and self.username and not is_active:
                    elig = self.eligibility_data.get(test_id, {})
                    if not elig.get("eligible", True):
                        elig_msg = elig.get("message", "")
                        time_part = (
                            elig_msg.split("через ", 1)[-1]
                            if "через " in elig_msg
                            else elig_msg
                        )
                        display_text += f" (повтор через: {time_part})"

                item = QtWidgets.QListWidgetItem(display_text)
                item.setData(Qt.UserRole, test)
                if is_active:
                    item.setForeground(QtGui.QColor("#27ae60"))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.assigned_tests_list_widget.addItem(item)
        else:
            self.assigned_tests_list_widget.addItem(
                f"Нет тестов, назначенных этим преподавателем ({teacher_username})."
            )

    def on_assigned_test_selected(self, item):
        test_data_role = item.data(Qt.UserRole)
        if test_data_role:
            self.current_selected_assigned_test = test_data_role
            self.start_assigned_test_button.setEnabled(True)
            selected_id = test_data_role.get("test_id")
            if selected_id and selected_id == self.active_session_test_id:
                self.start_assigned_test_button.setText("Продолжить активный тест")
            else:
                self.start_assigned_test_button.setText(
                    "Пройти выбранный назначенный тест"
                )
        else:
            self.current_selected_assigned_test = None
            self.start_assigned_test_button.setEnabled(False)
            self.start_assigned_test_button.setText("Пройти выбранный назначенный тест")

    def on_start_assigned_test_click(self):
        if self.current_selected_assigned_test:
            selected_id = self.current_selected_assigned_test.get("test_id")
            if selected_id and selected_id == self.active_session_test_id:

                self.resume_active_session_signal.emit()
                return
            self.welcome_label.hide()
            self.my_history_button.hide()
            self.assigned_tests_group.hide()
            self.results_label.setText("")
            self.restart_button.hide()
            self.change_password_button_student.hide()
            self.theme_toggle_button_student.hide()
            self.logout_button.hide()
            self.next_button.show()
            self.start_assigned_test_signal.emit(self.current_selected_assigned_test)
        else:
            self.show_warning("Ошибка", "Сначала выберите назначенный тест из списка.")

    def clear_active_session_marker(self):

        self.active_session_test_id = None
        self.start_assigned_test_button.setText("Пройти выбранный назначенный тест")

        current_teacher = self.teacher_filter_combo.currentText()
        if current_teacher and current_teacher != "-- Выберите преподавателя --":
            self.on_teacher_selected_from_filter(current_teacher)

    def on_show_my_history_click(self):
        self.show_my_history_signal.emit()

    def _on_join_by_share_student_clicked(self):
        raw, ok = QInputDialog.getText(
            self, "Присоединиться по ссылке", "Вставьте ссылку-приглашение или код:"
        )
        if not ok or not raw or not raw.strip():
            return
        raw = raw.strip()
        m = re.search(r"/join/([a-f0-9]{20,})", raw, re.IGNORECASE)
        token = (
            m.group(1)
            if m
            else (raw if re.match(r"^[a-f0-9]{20,}$", raw, re.IGNORECASE) else "")
        )
        if not token:
            self.show_warning("Ошибка", "Не удалось извлечь код приглашения из ссылки.")
            return
        self.join_by_share_signal.emit(token)

    def on_next_question_click(self):
        question_answer_type = self.current_answer_type

        selected_answers = []
        if question_answer_type == "multiple":
            for widget in self.options_widgets_list:
                if isinstance(widget, QCheckBox) and widget.isChecked():
                    selected_answers.append(widget.text())
            if not selected_answers:
                self.show_warning("Ошибка", "Выберите хотя бы один вариант ответа.")
                return
        else:
            selected_button = self.options_group.checkedButton()
            if selected_button:
                selected_answers = selected_button.text()
            else:
                self.show_warning("Ошибка", "Выберите ответ!")
                return

        self.next_question_signal.emit(self._current_nav_idx, selected_answers)

    def on_restart_click(self):
        self.restart_test_signal.emit()

    def display_question(
        self,
        question_number,
        question_text,
        options,
        answer_type="single",
        matrices=None,
        commands=None,
        is_additional=False,
        selected_answer=None,
    ):
        self.clear_options()
        self.clear_media_layout()

        prefix = "Дополнительный вопрос" if is_additional else "Вопрос"

        question_font = QtGui.QFont("Arial", 16)
        question_font.setBold(True)
        self.question_label.setFont(question_font)

        self.question_label.setText(
            f"{prefix} {question_number}: \n \n {question_text}"
        )
        self.question_label.show()

        if matrices:
            matrix_container_widget = QWidget()
            h_matrix_layout = QHBoxLayout(matrix_container_widget)
            for matrix_name, matrix_values in matrices.items():
                matrix_str = "\n".join(
                    [" ".join(map(str, row)) for row in matrix_values]
                )
                matrix_label_widget = QLabel(f"{matrix_name}:\n{matrix_str}", self)
                matrix_label_widget.setFont(QtGui.QFont("Arial", 12))
                h_matrix_layout.addWidget(matrix_label_widget)
            self.media_layout.addWidget(matrix_container_widget)
            self.media_layout_container.show()
        else:
            self.media_layout_container.hide()

        if commands:
            commands_text = "\n".join([f"Команда: {cmd}" for cmd in commands])
            commands_label_widget = QLabel(commands_text, self)
            commands_label_widget.setFont(QtGui.QFont("Arial", 12))
            self.media_layout.addWidget(commands_label_widget)
            self.media_layout_container.show()
        elif not matrices:
            self.media_layout_container.hide()

        current_answer_type = answer_type
        self.current_answer_type = current_answer_type

        options = list(options)
        random.shuffle(options)
        for option_text in options:
            if current_answer_type == "multiple":
                option_widget = QCheckBox(option_text, self)

            else:
                option_widget = QRadioButton(option_text, self)
                self.options_group.addButton(option_widget)

            option_widget.setFont(QtGui.QFont("Arial", 14))
            self.options_widgets_list.append(option_widget)
            self.options_layout.addWidget(option_widget)

        if selected_answer is not None:
            if current_answer_type == "multiple" and isinstance(selected_answer, list):
                for widget in self.options_widgets_list:
                    if (
                        isinstance(widget, QCheckBox)
                        and widget.text() in selected_answer
                    ):
                        widget.setChecked(True)
            elif current_answer_type == "single" and isinstance(selected_answer, str):
                for widget in self.options_widgets_list:
                    if (
                        isinstance(widget, QRadioButton)
                        and widget.text() == selected_answer
                    ):
                        widget.setChecked(True)
                        break

    def clear_options(self):
        for widget in self.options_widgets_list:
            if isinstance(widget, QRadioButton):
                self.options_group.removeButton(widget)
            widget.deleteLater()
        self.options_widgets_list.clear()

    def clear_media_layout(self):
        while self.media_layout.count():
            child = self.media_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                while child.layout().count():
                    grandchild = child.layout().takeAt(0)
                    if grandchild.widget():
                        grandchild.widget().deleteLater()
                child.layout().deleteLater()

    def start_countdown(self, seconds_remaining):

        self._countdown_seconds = seconds_remaining
        self._update_timer_label()
        if self._qt_timer is None:
            self._qt_timer = QTimer(self)
            self._qt_timer.timeout.connect(self._on_timer_tick)
        if not self._qt_timer.isActive():
            self._qt_timer.start(1000)
        self.timer_label.show()

    def stop_countdown(self):
        if self._qt_timer and self._qt_timer.isActive():
            self._qt_timer.stop()
        self.timer_label.hide()

    def _on_timer_tick(self):
        if self._countdown_seconds is None:
            return
        self._countdown_seconds -= 1
        self._update_timer_label()
        if self._countdown_seconds <= 0:
            self._qt_timer.stop()
            self.timeout_signal.emit()

    def _update_timer_label(self):
        if self._countdown_seconds is None:
            return
        mins = self._countdown_seconds // 60
        secs = self._countdown_seconds % 60
        color = (
            "red"
            if self._countdown_seconds <= 60
            else "orange" if self._countdown_seconds <= 180 else "white"
        )
        self.timer_label.setText(
            f"\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {mins:02d}:{secs:02d}"
        )
        self.timer_label.setStyleSheet(f"color: {color};")

    def show_results_summary(self, message, final_status_text, results=None):
        self.stop_countdown()
        self.question_label.hide()
        self.clear_options()
        self.clear_media_layout()
        self.media_layout_container.hide()
        self.next_button.hide()
        self.next_button.setText("Далее")
        self.nav_panel.hide()
        self.display_assigned_tests()
        self.my_history_button.show()
        self.welcome_label.show()
        self.change_password_button_student.show()
        self.theme_toggle_button_student.show()
        self.logout_button.show()
        self.join_by_share_button_student.show()

        lines = [f"Тест завершён!", f"{message}"]
        if results:
            score_pct = results.get("score_percentage")
            if score_pct is not None:
                lines.append(f"Общий результат: {score_pct:.1f}%")
            duration = results.get("duration")
            if duration:
                lines.append(f"Продолжительность: {duration}")
            category_scores = results.get("category_scores", {})
            if isinstance(category_scores, dict) and category_scores:
                lines.append("")
                lines.append("Результаты по темам:")
                for topic, data in category_scores.items():
                    if isinstance(data, dict):
                        score = data.get("score", 0)
                        total = data.get("total", 0)
                        status = data.get("status", "")
                        pct = data.get("percentage", 0)
                        lines.append(
                            f"  {topic}: {score}/{total} ({pct:.1f}%) — {status}"
                        )
                    else:
                        lines.append(f"  {topic}: {data}")
        lines.append(f"Итоговый статус: {final_status_text}")
        self.results_label.setText("\n".join(lines))

    def show_message(self, title, message, is_error=False):
        if is_error:
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def show_warning(self, title, message):
        QMessageBox.warning(self, title, message)

    def setup_nav_panel(self, total_questions):

        while self._nav_btns_layout.count():
            item = self._nav_btns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._total_nav_questions = total_questions
        for i in range(total_questions):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(36, 36)
            btn.clicked.connect(
                lambda _, idx=i: self.navigate_to_question_signal.emit(idx)
            )
            self._nav_btns_layout.addWidget(btn)
        self._nav_btns_layout.addStretch()

        self._current_nav_idx = 0
        self.nav_panel.show()

    def update_nav_panel(self, current_idx, frontier_idx):

        self._current_nav_idx = current_idx

        self._nav_progress_label.setText(
            f"Вопрос {current_idx + 1} из {self._total_nav_questions}"
        )
        self.prev_q_button.setEnabled(current_idx > 0)
        self.next_button.setText("Далее")
        self._review_mode_label.setText("")

        for i in range(self._nav_btns_layout.count()):
            item = self._nav_btns_layout.itemAt(i)
            if not item or not item.widget():
                continue
            btn = item.widget()
            if not isinstance(btn, QPushButton):
                continue
            try:
                btn_idx = int(btn.text()) - 1
            except ValueError:
                continue

            btn.setEnabled(True)

            if btn_idx == current_idx:
                btn.setStyleSheet(
                    "QPushButton { background-color: #0078D7; color: white;"
                    " font-weight: bold; border-radius: 4px; }"
                )
            elif btn_idx < frontier_idx:
                btn.setStyleSheet(
                    "QPushButton { background-color: #2D7A4F; color: white; border-radius: 4px; }"
                )
            elif btn_idx == frontier_idx and current_idx != frontier_idx:

                btn.setStyleSheet(
                    "QPushButton { background-color: #1A7A9A; color: white; border-radius: 4px; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background-color: #383838; color: #666666; border-radius: 4px; }"
                )

    def _on_prev_q_click(self):
        if self._current_nav_idx > 0:
            self.navigate_to_question_signal.emit(self._current_nav_idx - 1)


class TeachersWindow(QWidget):
    add_question_signal = pyqtSignal()
    edit_questions_signal = pyqtSignal()
    import_questions_signal = pyqtSignal()
    create_premade_test_signal = pyqtSignal()
    manage_premade_tests_signal = pyqtSignal()
    generate_topic_score_test_signal = pyqtSignal()
    change_password_signal = pyqtSignal()
    toggle_theme_signal = pyqtSignal()
    logout_signal = pyqtSignal()

    def __init__(self, username="Teacher"):
        super().__init__()
        self.username = username
        self.setWindowTitle("Окно преподавателя")
        self.setGeometry(100, 100, 1000, 680)
        self.init_ui()
        _restore_window_geometry(self, "TeachersWindow")

    def closeEvent(self, event):
        _save_window_geometry(self, "TeachersWindow")
        super().closeEvent(event)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 10, 20, 20)

        self.username_label = QLabel(f"Пользователь: {self.username}")
        self.username_label.setFont(QtGui.QFont("Arial", 10))
        self.username_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addWidget(self.username_label)

        title_label = QLabel("Панель преподавателя")
        font = QtGui.QFont("Arial", 24, QtGui.QFont.Bold)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        self.add_question_button = QPushButton("Добавить вопрос")
        self.add_question_button.setFont(QtGui.QFont("Arial", 16))
        self.add_question_button.setMinimumHeight(50)
        self.add_question_button.clicked.connect(self.add_question_signal.emit)
        layout.addWidget(self.add_question_button)

        self.edit_questions_button = QPushButton("Изменить вопросы")
        self.edit_questions_button.setFont(QtGui.QFont("Arial", 16))
        self.edit_questions_button.setMinimumHeight(50)
        self.edit_questions_button.clicked.connect(self.edit_questions_signal.emit)
        layout.addWidget(self.edit_questions_button)

        self.import_questions_button = QPushButton("Импорт вопросов из JSON")
        self.import_questions_button.setFont(QtGui.QFont("Arial", 16))
        self.import_questions_button.setMinimumHeight(50)
        self.import_questions_button.clicked.connect(self.import_questions_signal.emit)
        layout.addWidget(self.import_questions_button)

        self.create_premade_test_button = QPushButton("Создать готовый тест")
        self.create_premade_test_button.setFont(QtGui.QFont("Arial", 16))
        self.create_premade_test_button.setMinimumHeight(50)
        self.create_premade_test_button.clicked.connect(
            self.create_premade_test_signal.emit
        )
        layout.addWidget(self.create_premade_test_button)

        self.manage_premade_tests_button = QPushButton("Управление тестами")
        self.manage_premade_tests_button.setFont(QtGui.QFont("Arial", 16))
        self.manage_premade_tests_button.setMinimumHeight(50)
        self.manage_premade_tests_button.clicked.connect(
            self.manage_premade_tests_signal.emit
        )
        layout.addWidget(self.manage_premade_tests_button)

        self.generate_topic_score_test_button = QPushButton(
            "Сформировать тест по теме и баллам"
        )
        self.generate_topic_score_test_button.setFont(QtGui.QFont("Arial", 16))
        self.generate_topic_score_test_button.setMinimumHeight(50)
        self.generate_topic_score_test_button.clicked.connect(
            self.generate_topic_score_test_signal.emit
        )
        layout.addWidget(self.generate_topic_score_test_button)

        self.edit_grading_criteria_button = QPushButton("Настроить критерии оценки")
        self.edit_grading_criteria_button.setFont(QtGui.QFont("Arial", 16))
        self.edit_grading_criteria_button.setMinimumHeight(50)

        layout.addWidget(self.edit_grading_criteria_button)

        self.change_password_button = QPushButton("Сменить пароль", self)
        self.change_password_button.setFont(QtGui.QFont("Arial", 12))
        self.change_password_button.setMinimumHeight(35)
        self.change_password_button.clicked.connect(self.change_password_signal.emit)
        layout.addWidget(self.change_password_button)

        self.theme_toggle_button_teacher = QPushButton("Сменить тему", self)
        self.theme_toggle_button_teacher.setFont(QtGui.QFont("Arial", 12))
        self.theme_toggle_button_teacher.setMinimumHeight(35)
        self.theme_toggle_button_teacher.clicked.connect(self.toggle_theme_signal.emit)
        layout.addWidget(self.theme_toggle_button_teacher)

        self.logout_button = QPushButton("Выйти из аккаунта", self)
        self.logout_button.setFont(QtGui.QFont("Arial", 12))
        self.logout_button.setMinimumHeight(35)
        self.logout_button.clicked.connect(self.logout_signal.emit)
        layout.addWidget(self.logout_button)

        layout.addStretch(1)
        self.setLayout(layout)


class TestHistoryWindow(QDialog):
    user_selected_signal = pyqtSignal(str)
    details_requested_signal = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("История прохождения теста")
        self.setGeometry(150, 150, 1200, 800)
        self.init_ui()
        _restore_window_geometry(self, "TestHistoryWindow")

    def closeEvent(self, event):
        _save_window_geometry(self, "TestHistoryWindow")
        super().closeEvent(event)

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("История прохождения теста")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.user_combobox = QComboBox(self)
        self.user_combobox.setFont(QtGui.QFont("Arial", 12))
        self.user_combobox.currentIndexChanged.connect(self.on_user_selected)
        layout.addWidget(self.user_combobox)

        self.history_table = QTableWidget(self)
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels(
            [
                "Дата начала",
                "Название теста",
                "Попытка №",
                "Дата окончания",
                "Продолжительность",
                "Результат",
                "Подробнее",
            ]
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setFont(QtGui.QFont("Arial", 10))
        layout.addWidget(self.history_table)

        close_button = QPushButton("Закрыть", self)
        close_button.setFont(QtGui.QFont("Arial", 12))
        close_button.setMinimumHeight(40)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)
        self.user_data_cache = []

    def populate_users(self, usernames):
        self.user_combobox.clear()
        self.user_combobox.addItem("Выберите пользователя")
        self.user_combobox.addItems(usernames)

    def on_user_selected(self):
        selected_user = self.user_combobox.currentText()
        if selected_user != "Выберите пользователя":
            self.user_selected_signal.emit(selected_user)

    def display_user_history(self, user_history_data):
        self.user_data_cache = user_history_data
        self.history_table.setRowCount(len(user_history_data))
        for i, result in enumerate(user_history_data):
            self.history_table.setItem(
                i, 0, QTableWidgetItem(result.get("start_time", "N/A"))
            )
            self.history_table.setItem(
                i, 1, QTableWidgetItem(result.get("test_name", "N/A"))
            )
            self.history_table.setItem(
                i, 2, QTableWidgetItem(str(result.get("attempt_number", "N/A")))
            )
            self.history_table.setItem(
                i, 3, QTableWidgetItem(result.get("end_time", "N/A"))
            )
            self.history_table.setItem(
                i, 4, QTableWidgetItem(result.get("duration", "N/A"))
            )
            self.history_table.setItem(
                i, 5, QTableWidgetItem(result.get("final_status", "N/A"))
            )

            details_button = QPushButton("Подробнее")
            details_button.clicked.connect(lambda _, idx=i: self.request_details(idx))
            self.history_table.setCellWidget(i, 6, details_button)
        self.history_table.resizeColumnsToContents()

    def request_details(self, index):
        if 0 <= index < len(self.user_data_cache):
            self.details_requested_signal.emit(self.user_data_cache[index])

    def show_message(self, title, message, is_error=True):
        if is_error:
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)


class TestDetailsWindow(QDialog):
    def __init__(self, result_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Детали теста")
        self.setGeometry(200, 200, 1000, 750)
        self.result_data = result_data
        self.init_ui()
        _restore_window_geometry(self, "TestDetailsWindow")

    def closeEvent(self, event):
        _save_window_geometry(self, "TestDetailsWindow")
        super().closeEvent(event)

    def init_ui(self):
        layout = QVBoxLayout()

        title_text = (
            f"История теста пользователя: {self.result_data.get('username', 'N/A')}"
        )
        title = QLabel(title_text)
        font = title.font()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        details_lines = []
        test_name = self.result_data.get("test_name")
        if test_name:
            details_lines.append(f"Название теста: {test_name}")

        attempt_num = self.result_data.get("attempt_number")
        if attempt_num and attempt_num != "N/A":
            details_lines.append(f"Попытка №: {attempt_num}")

        details_lines.extend(
            [
                f"Дата начала: {self.result_data.get('start_time', 'N/A')}",
                f"Дата окончания: {self.result_data.get('end_time', 'N/A')}",
                f"Продолжительность: {self.result_data.get('duration', 'N/A')}",
            ]
        )

        grading_mode = self.result_data.get("grading_mode")
        if grading_mode:
            details_lines.append(
                f"Режим оценки: {'По темам' if grading_mode == 'per_topic' else 'Общий'}"
            )

        category_scores = self.result_data.get("category_scores", {})
        if isinstance(category_scores, dict):
            scores_str = []
            for topic, data in category_scores.items():
                if isinstance(data, dict):
                    scores_str.append(
                        f"  - {topic}: {data.get('score',0)}/{data.get('total',0)} ({data.get('status', 'N/A')})"
                    )
                else:
                    scores_str.append(f"  - {topic}: {data} (неполная информация)")
            details_lines.append(
                "Баллы и результат по темам:\n" + "\n".join(scores_str)
            )
        elif category_scores:
            details_lines.append(f"Баллы по темам: {category_scores}")

        details_lines.extend(
            [
                f"Общий статус: {self.result_data.get('status', 'N/A')}",
                f"Итоговый результат: {self.result_data.get('final_status', 'N/A')}",
            ]
        )
        details_label = QLabel("\n".join(details_lines))
        details_label.setFont(QtGui.QFont("Arial", 11))
        layout.addWidget(details_label)

        answers_title_label = QLabel("Ответы пользователя:")
        font = answers_title_label.font()
        font.setPointSize(12)
        font.setBold(True)
        answers_title_label.setFont(font)
        layout.addWidget(answers_title_label)

        answers_widget = QWidget()
        answers_layout = QVBoxLayout(answers_widget)

        for answer in self.result_data.get("answers", []):
            user_ans_data = answer.get("user_answer", "Нет ответа")
            correct_ans_obj = answer.get("correct_answer")

            user_ans_display_str = "Нет ответа"
            if isinstance(user_ans_data, list):
                user_ans_display_str = ", ".join(user_ans_data)
            elif user_ans_data is not None:
                user_ans_display_str = str(user_ans_data)

            answer_text_parts = [
                f"Вопрос: {answer.get('question', 'N/A')}",
                f"Ваш ответ: {user_ans_display_str}",
                f"Правильный ответ: {str(correct_ans_obj) if not isinstance(correct_ans_obj, list) else ', '.join(correct_ans_obj)}",
                f"Категория: {answer.get('category', 'N/A')}",
            ]
            answer_label = QLabel("\n".join(answer_text_parts))
            answer_label.setFont(QtGui.QFont("Arial", 10))
            answer_label.setWordWrap(True)

            is_correct = False
            if isinstance(correct_ans_obj, list):
                user_answers_set = set()
                if isinstance(user_ans_data, list):
                    user_answers_set = set(user_ans_data)
                elif isinstance(user_ans_data, str):
                    user_answers_set = set(
                        ans.strip() for ans in user_ans_data.split(",") if ans.strip()
                    )

                correct_answers_set = set(correct_ans_obj)
                is_correct = user_answers_set == correct_answers_set
            else:
                is_correct = user_ans_display_str == str(correct_ans_obj)

            if not is_correct:
                answer_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                answer_label.setStyleSheet("color: green;")
            answers_layout.addWidget(answer_label)

        scroll_area = QScrollArea(self)
        scroll_area.setWidget(answers_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        close_button = QPushButton("Закрыть", self)
        close_button.setFont(QtGui.QFont("Arial", 12))
        close_button.setMinimumHeight(40)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)


class AddQuestionWindow(QDialog):
    save_question_signal = pyqtSignal(dict)

    def __init__(self, topics=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить новый вопрос")
        self.setGeometry(150, 150, 950, 800)
        self.topics = topics if topics else []
        self.max_matrices = 5
        self.max_commands = 5
        self.matrices_data = []
        self.commands_list_items = []
        self.init_ui()
        _restore_window_geometry(self, "AddQuestionWindow")

    def closeEvent(self, event):
        _save_window_geometry(self, "AddQuestionWindow")
        super().closeEvent(event)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)

        self.topic_layout = QHBoxLayout()
        self.topic_layout.addWidget(QLabel("Тема вопроса:"))
        self.topic_input_combo = QComboBox()
        self.topic_input_combo.addItems(self.topics)
        self.topic_input_combo.setEditable(True)
        self.topic_input_combo.setFont(QtGui.QFont("Arial", 11))
        self.topic_layout.addWidget(self.topic_input_combo)
        self.main_layout.addLayout(self.topic_layout)

        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Текст вопроса")
        self.question_input.setFont(QtGui.QFont("Arial", 11))
        self.main_layout.addWidget(QLabel("Текст вопроса:"))
        self.main_layout.addWidget(self.question_input)

        self.matrices_groupbox = QtWidgets.QGroupBox("Матрицы (если нужны)")
        self.matrices_groupbox.setCheckable(True)
        self.matrices_groupbox.setChecked(False)
        self.matrices_layout = QVBoxLayout(self.matrices_groupbox)

        self.add_matrix_button = QPushButton("Создать/Редактировать матрицу")
        self.add_matrix_button.clicked.connect(self.open_matrix_manager)
        self.matrices_layout.addWidget(self.add_matrix_button)
        self.matrices_display_area = QLabel("Матрицы не добавлены.")
        self.matrices_layout.addWidget(self.matrices_display_area)
        self.main_layout.addWidget(self.matrices_groupbox)

        self.commands_groupbox = QtWidgets.QGroupBox(
            "Команды (если нужны, альтернатива матрицам)"
        )
        self.commands_groupbox.setCheckable(True)
        self.commands_groupbox.setChecked(False)
        self.commands_layout = QVBoxLayout(self.commands_groupbox)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Введите команду")
        self.commands_layout.addWidget(self.command_input)
        self.add_command_button = QPushButton("Добавить команду")
        self.add_command_button.clicked.connect(self.add_command_item)
        self.commands_layout.addWidget(self.add_command_button)
        self.commands_qlist_widget = QListWidget()
        self.commands_layout.addWidget(self.commands_qlist_widget)
        self.remove_command_button = QPushButton("Удалить выбранную команду")
        self.remove_command_button.clicked.connect(self.remove_command_item)
        self.commands_layout.addWidget(self.remove_command_button)
        self.main_layout.addWidget(self.commands_groupbox)

        self.single_correct_option_group = QButtonGroup(self)
        self.single_correct_option_group.setExclusive(True)
        self.option_entry_widgets = []
        self.main_layout.addWidget(QLabel("Варианты ответов (минимум 2):"))
        for i in range(5):
            option_layout = QHBoxLayout()

            option_radio = QRadioButton()
            option_radio.setVisible(False)
            option_radio.toggled.connect(self._handle_option_selection_changed)
            self.single_correct_option_group.addButton(option_radio)
            option_layout.addWidget(option_radio)

            option_checkbox = QCheckBox()
            option_checkbox.setVisible(False)
            option_checkbox.stateChanged.connect(self._handle_option_selection_changed)
            option_layout.addWidget(option_checkbox)

            option_input = QLineEdit()
            option_input.setPlaceholderText(f"Вариант {i+1}")
            option_input.setFont(QtGui.QFont("Arial", 11))
            option_input.textChanged.connect(self._handle_option_text_changed)
            option_layout.addWidget(option_input)

            self.option_entry_widgets.append(
                {
                    "radio": option_radio,
                    "checkbox": option_checkbox,
                    "input": option_input,
                }
            )
            self.main_layout.addLayout(option_layout)

        self.correct_input = QLineEdit()
        self.correct_input.setReadOnly(True)
        self.correct_input.setPlaceholderText("Выберите правильный вариант(ы) выше")
        self.main_layout.addWidget(QLabel("Правильный ответ:"))
        self.main_layout.addWidget(self.correct_input)

        self.is_multiple_choice_checkbox = QtWidgets.QCheckBox(
            "Разрешить несколько правильных ответов"
        )
        self.is_multiple_choice_checkbox.stateChanged.connect(
            self._toggle_multiple_answer_mode
        )
        self.main_layout.addWidget(self.is_multiple_choice_checkbox)

        points_layout = QHBoxLayout()
        points_layout.addWidget(QLabel("Баллы за вопрос:"))
        self.points_spinbox = QtWidgets.QSpinBox()
        self.points_spinbox.setMinimum(1)
        self.points_spinbox.setMaximum(100)
        self.points_spinbox.setValue(1)
        points_layout.addWidget(self.points_spinbox)
        self.main_layout.addLayout(points_layout)
        self._points_changed_by_multi_select_automation = False

        self.save_button = QPushButton("Сохранить вопрос")
        self.save_button.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        self.save_button.clicked.connect(self.on_save_question)
        self.main_layout.addWidget(self.save_button)

        self.matrices_groupbox.toggled.connect(
            lambda checked: (
                self.commands_groupbox.setChecked(not checked) if checked else None
            )
        )
        self.commands_groupbox.toggled.connect(
            lambda checked: (
                self.matrices_groupbox.setChecked(not checked) if checked else None
            )
        )

        self.matrices_groupbox.toggled.connect(self.toggle_matrix_widgets_visibility)
        self.commands_groupbox.toggled.connect(self.toggle_command_widgets_visibility)

        self.toggle_matrix_widgets_visibility(False)
        self.toggle_command_widgets_visibility(False)
        self._toggle_multiple_answer_mode(self.is_multiple_choice_checkbox.checkState())

    def toggle_matrix_widgets_visibility(self, checked):
        self.add_matrix_button.setVisible(checked)
        self.matrices_display_area.setVisible(checked)

    def toggle_command_widgets_visibility(self, checked):
        self.command_input.setVisible(checked)
        self.add_command_button.setVisible(checked)
        self.commands_qlist_widget.setVisible(checked)
        self.remove_command_button.setVisible(checked)

    def open_matrix_manager(self):

        manager = MatrixManagerDialog(self.matrices_data, self.max_matrices, self)
        if manager.exec_() == QDialog.Accepted:
            self.matrices_data = manager.get_all_matrices_data()
            self.update_matrices_display()

    def update_matrices_display(self):
        if self.matrices_data:
            names = [m["name"] for m in self.matrices_data]
            self.matrices_display_area.setText(
                f"Добавленные матрицы: {', '.join(names)}"
            )
        else:
            self.matrices_display_area.setText("Матрицы не добавлены.")

    def add_command_item(self):
        if self.commands_qlist_widget.count() >= self.max_commands:
            QMessageBox.warning(
                self, "Ошибка", f"Можно добавить не более {self.max_commands} команд."
            )
            return
        command_text = self.command_input.text().strip()
        if command_text:
            self.commands_qlist_widget.addItem(command_text)
            self.command_input.clear()
        else:
            QMessageBox.warning(self, "Ошибка", "Команда не может быть пустой.")

    def remove_command_item(self):
        current_item = self.commands_qlist_widget.currentItem()
        if current_item:
            self.commands_qlist_widget.takeItem(
                self.commands_qlist_widget.row(current_item)
            )

    def _handle_option_selection_changed(self):
        if self.is_multiple_choice_checkbox.isChecked():
            self._update_correct_answer_from_option_checkboxes()
        else:

            sender = self.sender()
            if isinstance(sender, QRadioButton) and sender.isChecked():
                self._update_correct_answer_from_radio_button()
            elif (
                not any(
                    entry["radio"].isChecked() for entry in self.option_entry_widgets
                )
                and not self.is_multiple_choice_checkbox.isChecked()
            ):

                self.correct_input.clear()

    def _handle_option_text_changed(self):
        if self.is_multiple_choice_checkbox.isChecked():
            self._update_correct_answer_from_option_checkboxes()
        else:
            self._update_correct_answer_from_radio_button()

    def _toggle_multiple_answer_mode(self, state):
        is_multiple = state == Qt.Checked
        self.correct_input.setReadOnly(True)

        for entry in self.option_entry_widgets:
            entry["radio"].setVisible(not is_multiple)
            entry["checkbox"].setVisible(is_multiple)
            if not is_multiple:
                entry["checkbox"].setChecked(False)

        if is_multiple:
            self.correct_input.setPlaceholderText(
                "Автоматически заполнено из отмеченных вариантов"
            )
            if self.points_spinbox.value() == 1:
                self.points_spinbox.setValue(2)
                self._points_changed_by_multi_select_automation = True
            self._update_correct_answer_from_option_checkboxes()
        else:
            self.correct_input.setPlaceholderText("Выберите вариант радиокнопкой")
            if (
                self.points_spinbox.value() == 2
                and self._points_changed_by_multi_select_automation
            ):
                self.points_spinbox.setValue(1)
            self._points_changed_by_multi_select_automation = False
            self._update_correct_answer_from_radio_button()

    def _update_correct_answer_from_radio_button(self):
        if self.is_multiple_choice_checkbox.isChecked():
            return

        checked_radio = self.single_correct_option_group.checkedButton()
        correct_text = ""
        if checked_radio:
            for entry in self.option_entry_widgets:
                if entry["radio"] == checked_radio:
                    correct_text = entry["input"].text().strip()
                    break
        self.correct_input.setText(correct_text)

    def _update_correct_answer_from_option_checkboxes(self):
        if not self.is_multiple_choice_checkbox.isChecked():
            return

        correct_answers = []
        for entry in self.option_entry_widgets:
            if entry["checkbox"].isChecked():
                option_text = entry["input"].text().strip()
                if option_text:
                    correct_answers.append(option_text)

        self.correct_input.setText(", ".join(sorted(list(set(correct_answers)))))

    def on_save_question(self):
        topic = self.topic_input_combo.currentText().strip()
        if not topic:
            QMessageBox.warning(self, "Ошибка", "Тема вопроса не может быть пустой.")
            return

        question_text = self.question_input.text().strip()
        if not question_text:
            QMessageBox.warning(self, "Ошибка", "Текст вопроса не может быть пустым.")
            return

        options = [
            entry["input"].text().strip()
            for entry in self.option_entry_widgets
            if entry["input"].text().strip()
        ]
        if len(options) < 2:
            QMessageBox.warning(
                self, "Ошибка", "Должно быть минимум два варианта ответа."
            )
            return

        correct_answer_text_from_field = self.correct_input.text().strip()
        if not correct_answer_text_from_field:
            QMessageBox.warning(
                self, "Ошибка", "Правильный ответ не может быть пустым."
            )
            return

        question_data = {
            "topic": topic,
            "question": question_text,
            "options": options,
            "category": topic,
        }

        if self.is_multiple_choice_checkbox.isChecked():

            correct_answers_list = []
            for entry in self.option_entry_widgets:
                if entry["checkbox"].isChecked():
                    option_text = entry["input"].text().strip()
                    if option_text:
                        correct_answers_list.append(option_text)

            if not correct_answers_list:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Для вопроса с несколькими вариантами укажите хотя бы один правильный ответ.",
                )
                return

            for ca in correct_answers_list:
                if ca not in options:
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        f"Правильный ответ '{ca}' (отмеченный галочкой) не найден среди введенных вариантов или вариант пуст.",
                    )
                    return
            question_data["correct"] = sorted(list(set(correct_answers_list)))
            question_data["answer_type"] = "multiple"
        else:

            if correct_answer_text_from_field not in options:
                QMessageBox.warning(
                    self, "Ошибка", "Правильный ответ должен быть одним из вариантов."
                )
                return
            question_data["correct"] = correct_answer_text_from_field
            question_data["answer_type"] = "single"

        question_data["points"] = self.points_spinbox.value()

        if self.matrices_groupbox.isChecked() and self.matrices_data:

            formatted_matrices = {}
            for m_data in self.matrices_data:
                try:

                    numeric_matrix_data = []
                    for row in m_data["data"]:
                        numeric_row = []
                        for cell in row:
                            if isinstance(cell, str) and cell.strip() == "":
                                numeric_cell = 0
                            else:
                                numeric_cell = int(cell)
                            numeric_row.append(numeric_cell)
                        numeric_matrix_data.append(numeric_row)
                    formatted_matrices[m_data["name"]] = numeric_matrix_data
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Ошибка данных матрицы",
                        f"Матрица {m_data['name']} содержит нечисловые значения.",
                    )
                    return
            question_data["matrices"] = formatted_matrices
        elif self.commands_groupbox.isChecked():
            commands = [
                self.commands_qlist_widget.item(i).text()
                for i in range(self.commands_qlist_widget.count())
            ]
            if commands:
                question_data["commands"] = commands

        self.save_question_signal.emit(question_data)


class MatrixManagerDialog(QDialog):
    def __init__(self, initial_matrices_data=None, max_matrices=5, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление матрицами")
        self.setMinimumSize(850, 400)
        self.max_matrices = max_matrices
        self.matrices_data = (
            [dict(m) for m in initial_matrices_data] if initial_matrices_data else []
        )
        self.current_editor_widget = None
        self.currently_editing_matrix_index = -1

        self.init_ui()
        _restore_window_geometry(self, "MatrixManagerDialog")

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        for m_data in self.matrices_data:
            self.list_widget.addItem(m_data.get("name", "Безымянная"))
        self.list_widget.currentRowChanged.connect(self.display_matrix_editor)

        list_buttons_layout = QHBoxLayout()
        self.add_matrix_btn = QPushButton("Добавить")
        self.add_matrix_btn.clicked.connect(self.add_new_matrix)
        self.remove_matrix_btn = QPushButton("Удалить")
        self.remove_matrix_btn.clicked.connect(self.remove_selected_matrix)
        list_buttons_layout.addWidget(self.add_matrix_btn)
        list_buttons_layout.addWidget(self.remove_matrix_btn)

        left_panel_layout = QVBoxLayout()
        left_panel_layout.addWidget(QLabel("Матрицы:"))
        left_panel_layout.addWidget(self.list_widget)
        left_panel_layout.addLayout(list_buttons_layout)

        self.editor_panel = QWidget()
        self.editor_layout = QVBoxLayout(self.editor_panel)
        self.current_editor_widget = None

        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(left_panel_layout)
        splitter.addWidget(left_widget)
        splitter.addWidget(self.editor_panel)
        splitter.setSizes([250, 500])

        self.main_layout.addWidget(splitter)

        dialog_buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        dialog_buttons.accepted.connect(self.accept_changes)
        dialog_buttons.rejected.connect(self.reject)
        self.main_layout.addWidget(dialog_buttons)

        if self.matrices_data:
            self.list_widget.setCurrentRow(0)
        else:
            self.update_buttons_state()

    def save_editor_data_at_index(self, matrix_index_to_save):
        if self.current_editor_widget and 0 <= matrix_index_to_save < len(
            self.matrices_data
        ):
            editor_data = self.current_editor_widget.get_matrix_data_with_name()
            self.matrices_data[matrix_index_to_save] = editor_data
            list_item = self.list_widget.item(matrix_index_to_save)
            if list_item:
                list_item.setText(editor_data["name"])

    def display_matrix_editor(self, newly_selected_row_index):

        if (
            self.current_editor_widget
            and self.currently_editing_matrix_index != -1
            and self.currently_editing_matrix_index < len(self.matrices_data)
            and self.currently_editing_matrix_index != newly_selected_row_index
        ):
            self.save_editor_data_at_index(self.currently_editing_matrix_index)

        if self.current_editor_widget:
            self.editor_layout.removeWidget(self.current_editor_widget)
            self.current_editor_widget.deleteLater()
            self.current_editor_widget = None

        if 0 <= newly_selected_row_index < len(self.matrices_data):
            matrix_to_edit = self.matrices_data[newly_selected_row_index]
            self.current_editor_widget = MatrixEditorWidget(matrix_to_edit, self)
            self.editor_layout.addWidget(self.current_editor_widget)
            self.currently_editing_matrix_index = newly_selected_row_index
        else:

            self.currently_editing_matrix_index = -1

        self.update_buttons_state()

    def add_new_matrix(self):
        if len(self.matrices_data) >= self.max_matrices:
            QMessageBox.warning(
                self, "Лимит", f"Можно добавить не более {self.max_matrices} матриц."
            )
            return

        base_name = "Матрица"
        current_names = [m.get("name", "") for m in self.matrices_data]
        new_name_idx = 1
        new_name = f"{base_name} {new_name_idx}"
        while new_name in current_names:
            new_name_idx += 1
            new_name = f"{base_name} {new_name_idx}"

        new_matrix = {
            "name": new_name,
            "rows": 2,
            "cols": 2,
            "data": [["0"] * 2 for _ in range(2)],
        }
        self.matrices_data.append(new_matrix)
        self.list_widget.addItem(new_name)
        self.list_widget.setCurrentRow(len(self.matrices_data) - 1)

    def remove_selected_matrix(self):
        current_row = self.list_widget.currentRow()
        if 0 <= current_row < len(self.matrices_data):

            del self.matrices_data[current_row]
            self.list_widget.takeItem(current_row)

            if self.current_editor_widget:
                self.editor_layout.removeWidget(self.current_editor_widget)
                self.current_editor_widget.deleteLater()
                self.current_editor_widget = None

            self.currently_editing_matrix_index = -1

            if self.matrices_data:
                new_row_to_select = max(0, current_row - 1)

                if new_row_to_select >= len(self.matrices_data):
                    new_row_to_select = len(self.matrices_data) - 1

                if new_row_to_select >= 0:
                    self.list_widget.setCurrentRow(new_row_to_select)

            else:

                self.display_matrix_editor(-1)

    def accept_changes(self):
        if self.current_editor_widget and self.currently_editing_matrix_index != -1:
            self.save_editor_data_at_index(self.currently_editing_matrix_index)
        self.accept()

    def get_all_matrices_data(self):
        return self.matrices_data

    def update_buttons_state(self):
        self.add_matrix_btn.setEnabled(len(self.matrices_data) < self.max_matrices)
        self.remove_matrix_btn.setEnabled(self.list_widget.currentRow() != -1)

    def done(self, result):
        _save_window_geometry(self, "MatrixManagerDialog")
        super().done(result)


class MatrixEditorWidget(QWidget):
    def __init__(self, matrix_data_dict, parent=None):
        super().__init__(parent)

        self.matrix_info = dict(matrix_data_dict)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Имя матрицы:"))
        self.name_input = QLineEdit(self.matrix_info.get("name", "Матрица"))
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Строк:"))
        self.rows_spinbox = QtWidgets.QSpinBox()
        self.rows_spinbox.setMinimum(1)
        self.rows_spinbox.setValue(self.matrix_info.get("rows", 2))
        size_layout.addWidget(self.rows_spinbox)

        size_layout.addWidget(QLabel("Столбцов:"))
        self.cols_spinbox = QtWidgets.QSpinBox()
        self.cols_spinbox.setMinimum(1)
        self.cols_spinbox.setValue(self.matrix_info.get("cols", 2))
        size_layout.addWidget(self.cols_spinbox)

        self.rows_spinbox.valueChanged.connect(self.update_table_dimensions)
        self.cols_spinbox.valueChanged.connect(self.update_table_dimensions)
        layout.addLayout(size_layout)

        self.table_widget = QTableWidget()
        self.populate_table()
        layout.addWidget(self.table_widget)

    def populate_table(self):
        rows = self.matrix_info.get("rows", 2)
        cols = self.matrix_info.get("cols", 2)
        data = self.matrix_info.get("data", [["0"] * cols for _ in range(rows)])

        self.table_widget.setRowCount(rows)
        self.table_widget.setColumnCount(cols)

        for r in range(rows):
            if r >= len(data):
                data.append(["0"] * cols)
            for c in range(cols):
                if c >= len(data[r]):
                    data[r].append("0")
                item_text = str(data[r][c])
                self.table_widget.setItem(r, c, QTableWidgetItem(item_text))

    def update_table_dimensions(self):

        current_data_in_table = []
        for r in range(self.table_widget.rowCount()):
            row_list = []
            for c in range(self.table_widget.columnCount()):
                item = self.table_widget.item(r, c)
                row_list.append(item.text() if item else "0")
            current_data_in_table.append(row_list)

        new_rows = self.rows_spinbox.value()
        new_cols = self.cols_spinbox.value()

        self.matrix_info["rows"] = new_rows
        self.matrix_info["cols"] = new_cols

        new_internal_data = []
        for r_idx in range(new_rows):
            new_row_data = []
            for c_idx in range(new_cols):
                if r_idx < len(current_data_in_table) and c_idx < len(
                    current_data_in_table[r_idx]
                ):
                    new_row_data.append(current_data_in_table[r_idx][c_idx])
                else:
                    new_row_data.append("0")
            new_internal_data.append(new_row_data)
        self.matrix_info["data"] = new_internal_data

        self.populate_table()

    def get_matrix_data_with_name(self):

        data = []
        for r in range(self.table_widget.rowCount()):
            row_data = []
            for c in range(self.table_widget.columnCount()):
                item = self.table_widget.item(r, c)
                row_data.append(item.text() if item else "0")
            data.append(row_data)

        return {
            "name": self.name_input.text().strip(),
            "rows": self.table_widget.rowCount(),
            "cols": self.table_widget.columnCount(),
            "data": data,
        }


class EditQuestionsWindow(QDialog):

    topic_selected_signal = pyqtSignal(str)
    edit_single_question_signal = pyqtSignal(str, int)

    def __init__(self, topics_with_questions, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование вопросов")
        self.setGeometry(100, 100, 1100, 800)
        self.topics_data = topics_with_questions
        self.current_topic = None
        self.init_ui()
        _restore_window_geometry(self, "EditQuestionsWindow")

    def closeEvent(self, event):
        _save_window_geometry(self, "EditQuestionsWindow")
        super().closeEvent(event)

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Темы вопросов:"))
        self.topics_list_widget = QListWidget()
        if self.topics_data:
            self.topics_list_widget.addItems(self.topics_data.keys())
        self.topics_list_widget.itemClicked.connect(self.on_topic_clicked)
        left_panel.addWidget(self.topics_list_widget)

        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Вопросы в теме (2хКЛИК — редактировать):"))
        self.questions_list_widget = QListWidget()
        self.questions_list_widget.setWordWrap(True)
        self.questions_list_widget.itemDoubleClicked.connect(
            self.on_question_double_clicked
        )
        right_panel.addWidget(self.questions_list_widget)

        self.edit_selected_q_button = QPushButton("Редактировать выбранный вопрос")
        self.edit_selected_q_button.clicked.connect(self.on_edit_selected_question)
        self.edit_selected_q_button.setEnabled(False)
        right_panel.addWidget(self.edit_selected_q_button)

        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)

        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.accept)

        self._questions_in_topic_cache = []
        self._expanded_q_index = -1

    def update_topics(self, new_topics_data):
        self.topics_data = new_topics_data
        self.topics_list_widget.clear()
        if self.topics_data:
            self.topics_list_widget.addItems(self.topics_data.keys())
        self.questions_list_widget.clear()
        self.edit_selected_q_button.setEnabled(False)

    def on_topic_clicked(self, item):
        self.current_topic = item.text()
        self.topic_selected_signal.emit(self.current_topic)

    def display_questions_for_topic(self, questions_in_topic):
        self._questions_in_topic_cache = questions_in_topic or []
        self._expanded_q_index = -1
        self.questions_list_widget.clear()
        for idx, q_data in enumerate(self._questions_in_topic_cache):
            full_text = q_data.get("question", "Без текста")
            item = QtWidgets.QListWidgetItem(f"({idx}) {full_text}")
            item.setData(Qt.UserRole, idx)
            self.questions_list_widget.addItem(item)
        self.edit_selected_q_button.setEnabled(self.questions_list_widget.count() > 0)

    def _on_q_list_right_click(self, pos):

        item = self.questions_list_widget.itemAt(pos)
        if not item:
            return
        idx = item.data(Qt.UserRole)
        if idx is None:
            return
        q_data = (
            self._questions_in_topic_cache[idx]
            if 0 <= idx < len(self._questions_in_topic_cache)
            else None
        )
        if not q_data:
            return
        full_text = q_data.get("question", "Без текста")
        if self._expanded_q_index == idx:

            item.setText(f"({idx}) {full_text}")
            self._expanded_q_index = -1
        else:

            if self._expanded_q_index != -1:
                prev = self.questions_list_widget.item(self._expanded_q_index)
                if prev:
                    prev_data = (
                        self._questions_in_topic_cache[self._expanded_q_index]
                        if 0
                        <= self._expanded_q_index
                        < len(self._questions_in_topic_cache)
                        else None
                    )
                    if prev_data:
                        prev_text = prev_data.get("question", "Без текста")
                        prev.setText(f"({self._expanded_q_index}) {prev_text}")

            item.setText(f"({idx}) {full_text}")
            self._expanded_q_index = idx
        self.questions_list_widget.scrollToItem(item)

    def on_question_double_clicked(self, item):
        self.open_editor_for_selected_question()

    def on_edit_selected_question(self):
        self.open_editor_for_selected_question()

    def open_editor_for_selected_question(self):
        if not self.current_topic:
            return
        selected_row = self.questions_list_widget.currentRow()
        if selected_row >= 0:
            self.edit_single_question_signal.emit(self.current_topic, selected_row)

    def show_message(self, title, message, is_error=False):
        if is_error:
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)


class EditSingleQuestionWindow(QDialog):
    save_question_changes_signal = pyqtSignal(str, int, dict)
    delete_question_signal = pyqtSignal(str, int)

    def __init__(
        self, topic_name, question_data, question_idx, all_topics, parent=None
    ):
        super().__init__(parent)
        self.topic_name = topic_name
        self.original_question_data = question_data
        self.question_idx = question_idx
        self.all_topics = all_topics

        self.setWindowTitle(
            f"Редактирование вопроса (Тема: {topic_name}, Индекс: {question_idx})"
        )
        self.setGeometry(150, 150, 1000, 870)
        self.matrices_data_cache = []
        self.init_ui()
        self.populate_fields()
        _restore_window_geometry(self, "EditSingleQuestionWindow")

    def done(self, result):
        _save_window_geometry(self, "EditSingleQuestionWindow")
        super().done(result)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)

        topic_layout = QHBoxLayout()
        topic_layout.addWidget(QLabel("Тема:"))
        self.topic_combo = QComboBox()
        self.topic_combo.addItems(self.all_topics)
        self.topic_combo.setEditable(True)
        topic_layout.addWidget(self.topic_combo)
        self.main_layout.addLayout(topic_layout)

        self.question_input = QLineEdit()
        self.main_layout.addWidget(QLabel("Текст вопроса:"))
        self.main_layout.addWidget(self.question_input)

        self.matrices_groupbox = QtWidgets.QGroupBox("Матрицы")
        self.matrices_groupbox.setCheckable(True)
        self.matrices_layout = QVBoxLayout(self.matrices_groupbox)
        self.edit_matrices_button = QPushButton("Редактировать матрицы")
        self.edit_matrices_button.clicked.connect(self.launch_matrix_manager)
        self.matrices_layout.addWidget(self.edit_matrices_button)
        self.matrices_names_label = QLabel("Матрицы: нет")
        self.matrices_layout.addWidget(self.matrices_names_label)
        self.main_layout.addWidget(self.matrices_groupbox)

        self.commands_groupbox = QtWidgets.QGroupBox("Команды")
        self.commands_groupbox.setCheckable(True)
        self.commands_layout_gl = QVBoxLayout(self.commands_groupbox)
        self.commands_list_widget_edit = QListWidget()
        self.commands_layout_gl.addWidget(self.commands_list_widget_edit)
        cmd_btn_layout = QHBoxLayout()
        self.new_command_input_edit = QLineEdit()
        self.new_command_input_edit.setPlaceholderText("Новая команда")
        cmd_btn_layout.addWidget(self.new_command_input_edit)
        self.add_cmd_btn_edit = QPushButton("Добавить")
        self.add_cmd_btn_edit.clicked.connect(self.add_command_to_list)
        cmd_btn_layout.addWidget(self.add_cmd_btn_edit)
        self.del_cmd_btn_edit = QPushButton("Удалить выбранную")
        self.del_cmd_btn_edit.clicked.connect(self.delete_command_from_list)
        self.commands_layout_gl.addLayout(cmd_btn_layout)
        self.commands_layout_gl.addWidget(self.del_cmd_btn_edit)
        self.main_layout.addWidget(self.commands_groupbox)

        self.matrices_groupbox.toggled.connect(
            lambda checked: (
                self.commands_groupbox.setChecked(not checked)
                if checked and self.commands_groupbox.isChecked()
                else None
            )
        )
        self.commands_groupbox.toggled.connect(
            lambda checked: (
                self.matrices_groupbox.setChecked(not checked)
                if checked and self.matrices_groupbox.isChecked()
                else None
            )
        )

        self.matrices_groupbox.toggled.connect(
            self.toggle_matrix_widgets_visibility_edit
        )
        self.commands_groupbox.toggled.connect(
            self.toggle_command_widgets_visibility_edit
        )

        self.single_correct_option_group_edit = QButtonGroup(self)
        self.single_correct_option_group_edit.setExclusive(True)
        self.option_entry_widgets_edit = []
        self.main_layout.addWidget(QLabel("Варианты ответов:"))
        for i in range(5):
            option_layout_edit = QHBoxLayout()

            option_radio_edit = QRadioButton()
            option_radio_edit.setVisible(False)
            option_radio_edit.toggled.connect(
                self._handle_option_selection_changed_edit
            )
            self.single_correct_option_group_edit.addButton(option_radio_edit)
            option_layout_edit.addWidget(option_radio_edit)

            option_checkbox_edit = QCheckBox()
            option_checkbox_edit.setVisible(False)
            option_checkbox_edit.stateChanged.connect(
                self._handle_option_selection_changed_edit
            )
            option_layout_edit.addWidget(option_checkbox_edit)

            opt_input = QLineEdit()
            opt_input.textChanged.connect(self._handle_option_text_changed_edit)
            option_layout_edit.addWidget(opt_input)

            self.option_entry_widgets_edit.append(
                {
                    "radio": option_radio_edit,
                    "checkbox": option_checkbox_edit,
                    "input": opt_input,
                }
            )
            self.main_layout.addLayout(option_layout_edit)

        self.correct_input_edit = QLineEdit()
        self.correct_input_edit.setReadOnly(True)
        self.correct_input_edit.setPlaceholderText(
            "Выберите правильный вариант(ы) выше"
        )
        self.main_layout.addWidget(
            QLabel("Правильный ответ (текст одного из вариантов):")
        )
        self.main_layout.addWidget(self.correct_input_edit)

        self.is_multiple_choice_checkbox_edit = QtWidgets.QCheckBox(
            "Разрешить несколько правильных ответов"
        )
        self.is_multiple_choice_checkbox_edit.stateChanged.connect(
            self._toggle_multiple_answer_mode_edit
        )
        self.main_layout.addWidget(self.is_multiple_choice_checkbox_edit)

        points_edit_layout = QHBoxLayout()
        points_edit_layout.addWidget(QLabel("Баллы за вопрос:"))
        self.points_spinbox_edit = QtWidgets.QSpinBox()
        self.points_spinbox_edit.setMinimum(1)
        self.points_spinbox_edit.setMaximum(100)
        points_edit_layout.addWidget(self.points_spinbox_edit)
        self.main_layout.addLayout(points_edit_layout)
        self._points_changed_by_multi_select_automation_edit = False

        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить изменения")
        self.save_button.clicked.connect(self.on_save_changes)
        buttons_layout.addWidget(self.save_button)

        self.delete_button = QPushButton("Удалить вопрос")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.on_delete_question)
        buttons_layout.addWidget(self.delete_button)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(buttons_layout)

        self.toggle_matrix_widgets_visibility_edit(self.matrices_groupbox.isChecked())
        self.toggle_command_widgets_visibility_edit(self.commands_groupbox.isChecked())

    def _handle_option_selection_changed_edit(self):
        if self.is_multiple_choice_checkbox_edit.isChecked():
            self._update_correct_answer_from_option_checkboxes_edit()
        else:
            sender = self.sender()
            if isinstance(sender, QRadioButton) and sender.isChecked():
                self._update_correct_answer_from_radio_button_edit()
            elif (
                not any(
                    entry["radio"].isChecked()
                    for entry in self.option_entry_widgets_edit
                )
                and not self.is_multiple_choice_checkbox_edit.isChecked()
            ):
                self.correct_input_edit.clear()

    def _handle_option_text_changed_edit(self):
        if self.is_multiple_choice_checkbox_edit.isChecked():
            self._update_correct_answer_from_option_checkboxes_edit()
        else:
            self._update_correct_answer_from_radio_button_edit()

    def _toggle_multiple_answer_mode_edit(self, state):
        is_multiple = state == Qt.Checked
        self.correct_input_edit.setReadOnly(True)

        for entry in self.option_entry_widgets_edit:
            entry["radio"].setVisible(not is_multiple)
            entry["checkbox"].setVisible(is_multiple)
            if not is_multiple:
                entry["checkbox"].setChecked(False)

        if is_multiple:
            self.correct_input_edit.setPlaceholderText(
                "Автоматически заполнено из отмеченных вариантов"
            )
            if self.points_spinbox_edit.value() == 1:
                self.points_spinbox_edit.setValue(2)
                self._points_changed_by_multi_select_automation_edit = True
            self._update_correct_answer_from_option_checkboxes_edit()
        else:
            self.correct_input_edit.setPlaceholderText("Выберите вариант радиокнопкой")
            if (
                self.points_spinbox_edit.value() == 2
                and self._points_changed_by_multi_select_automation_edit
            ):
                self.points_spinbox_edit.setValue(1)
            self._points_changed_by_multi_select_automation_edit = False
            self._update_correct_answer_from_radio_button_edit()

    def _update_correct_answer_from_radio_button_edit(self):
        if self.is_multiple_choice_checkbox_edit.isChecked():
            return

        checked_radio = self.single_correct_option_group_edit.checkedButton()
        correct_text = ""
        if checked_radio:
            for entry in self.option_entry_widgets_edit:
                if entry["radio"] == checked_radio:
                    correct_text = entry["input"].text().strip()
                    break
        self.correct_input_edit.setText(correct_text)

    def _update_correct_answer_from_option_checkboxes_edit(self):
        if not self.is_multiple_choice_checkbox_edit.isChecked():
            return

        correct_answers = []
        for entry in self.option_entry_widgets_edit:
            if entry["checkbox"].isChecked():
                option_text = entry["input"].text().strip()
                if option_text:
                    correct_answers.append(option_text)

        self.correct_input_edit.setText(", ".join(sorted(list(set(correct_answers)))))

    def populate_fields(self):
        q_data = self.original_question_data
        self.topic_combo.setCurrentText(self.topic_name)
        self.question_input.setText(q_data.get("question", ""))
        self.points_spinbox_edit.setValue(q_data.get("points", 1))
        self._points_changed_by_multi_select_automation_edit = False

        correct_data_value = q_data.get("correct", "")
        answer_type = q_data.get("answer_type", "single")

        options = q_data.get("options", [])
        first_option_radio_to_select = None

        for i, entry in enumerate(self.option_entry_widgets_edit):
            opt_widget = entry["input"]
            opt_checkbox = entry["checkbox"]
            opt_radio = entry["radio"]

            if i < len(options):
                current_option_text = options[i]
                opt_widget.setText(current_option_text)

                if (
                    answer_type == "multiple"
                    and isinstance(correct_data_value, list)
                    and current_option_text in correct_data_value
                ):
                    opt_checkbox.setChecked(True)
                else:
                    opt_checkbox.setChecked(False)

                if (
                    answer_type == "single"
                    and current_option_text == correct_data_value
                ):
                    first_option_radio_to_select = opt_radio
                else:
                    opt_radio.setChecked(False)
            else:
                opt_widget.setText("")
                opt_checkbox.setChecked(False)
                opt_radio.setChecked(False)

        if answer_type == "multiple":
            self.is_multiple_choice_checkbox_edit.setChecked(True)
        else:
            self.is_multiple_choice_checkbox_edit.setChecked(False)

        self._toggle_multiple_answer_mode_edit(
            self.is_multiple_choice_checkbox_edit.checkState()
        )

        if (
            not self.is_multiple_choice_checkbox_edit.isChecked()
            and first_option_radio_to_select
        ):
            first_option_radio_to_select.setChecked(True)
        elif (
            not self.is_multiple_choice_checkbox_edit.isChecked()
            and not first_option_radio_to_select
            and options
        ):
            pass

        if "matrices" in q_data and q_data["matrices"]:
            self.matrices_groupbox.setChecked(True)
            self.matrices_data_cache = []
            names = []
            for name, data_val in q_data["matrices"].items():
                if not data_val:
                    continue
                rows = len(data_val)
                cols = len(data_val[0]) if rows > 0 else 0
                stringified_data_val = [
                    [str(cell_content) for cell_content in row_list]
                    for row_list in data_val
                ]
                self.matrices_data_cache.append(
                    {
                        "name": name,
                        "rows": rows,
                        "cols": cols,
                        "data": stringified_data_val,
                    }
                )
                names.append(name)
            self.matrices_names_label.setText(
                f"Матрицы: {', '.join(names)}" if names else "Матрицы: нет"
            )
        else:
            self.matrices_groupbox.setChecked(False)
            self.matrices_names_label.setText("Матрицы: нет")

        self.commands_list_widget_edit.clear()
        if "commands" in q_data and q_data["commands"]:
            self.commands_groupbox.setChecked(True)
            self.commands_list_widget_edit.addItems(q_data["commands"])
        else:
            self.commands_groupbox.setChecked(False)

        if self.matrices_groupbox.isChecked() and self.commands_groupbox.isChecked():
            self.commands_groupbox.setChecked(False)

        self.points_spinbox_edit.setValue(q_data.get("points", 1))

    def toggle_matrix_widgets_visibility_edit(self, checked):
        self.edit_matrices_button.setVisible(checked)
        self.matrices_names_label.setVisible(checked)

    def toggle_command_widgets_visibility_edit(self, checked):
        self.commands_list_widget_edit.setVisible(checked)
        self.new_command_input_edit.setVisible(checked)
        self.add_cmd_btn_edit.setVisible(checked)
        self.del_cmd_btn_edit.setVisible(checked)

    def launch_matrix_manager(self):
        manager = MatrixManagerDialog(self.matrices_data_cache, 5, self)
        if manager.exec_() == QDialog.Accepted:
            self.matrices_data_cache = manager.get_all_matrices_data()
            names = [m["name"] for m in self.matrices_data_cache]
            self.matrices_names_label.setText(
                f"Матрицы: {', '.join(names)}" if names else "Матрицы: нет"
            )

    def add_command_to_list(self):
        cmd_text = self.new_command_input_edit.text().strip()
        if cmd_text:
            self.commands_list_widget_edit.addItem(cmd_text)
            self.new_command_input_edit.clear()

    def delete_command_from_list(self):
        selected = self.commands_list_widget_edit.currentItem()
        if selected:
            self.commands_list_widget_edit.takeItem(
                self.commands_list_widget_edit.row(selected)
            )

    def toggle_correct_answer_placeholder_edit(self, state):
        if state == Qt.Checked:
            self.correct_input_edit.setPlaceholderText(
                "Тексты правильных ответов, через запятую (e.g., Ответ1,Ответ2)"
            )
        else:
            self.correct_input_edit.setPlaceholderText(
                "Текст правильного ответа (должен совпадать с одним из вариантов)"
            )

    def on_save_changes(self):
        new_data = {}
        new_data["question"] = self.question_input.text().strip()
        new_data["options"] = [
            entry["input"].text().strip()
            for entry in self.option_entry_widgets_edit
            if entry["input"].text().strip()
        ]

        correct_answer_text_from_field_edit = self.correct_input_edit.text().strip()

        if (
            not new_data["question"]
            or not new_data["options"]
            or not correct_answer_text_from_field_edit
        ):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Все поля (вопрос, варианты, правильный ответ) должны быть заполнены.",
            )
            return

        new_topic_name = self.topic_combo.currentText().strip()
        if not new_topic_name:
            QMessageBox.warning(self, "Ошибка", "Тема не может быть пустой.")
            return

        new_data["category"] = new_topic_name

        if self.is_multiple_choice_checkbox_edit.isChecked():

            correct_answers_list_edit = []
            for entry in self.option_entry_widgets_edit:
                if entry["checkbox"].isChecked():
                    option_text = entry["input"].text().strip()
                    if option_text:
                        correct_answers_list_edit.append(option_text)

            if not correct_answers_list_edit:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Для вопроса с несколькими вариантами укажите хотя бы один правильный ответ.",
                )
                return

            for ca in correct_answers_list_edit:
                if ca not in new_data["options"]:
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        f"Правильный ответ '{ca}' (отмеченный галочкой) не найден среди введенных вариантов или вариант пуст.",
                    )
                    return
            new_data["correct"] = sorted(list(set(correct_answers_list_edit)))
            new_data["answer_type"] = "multiple"
        else:

            if correct_answer_text_from_field_edit not in new_data["options"]:
                QMessageBox.warning(
                    self, "Ошибка", "Правильный ответ должен быть одним из вариантов."
                )
                return
            new_data["correct"] = correct_answer_text_from_field_edit
            new_data["answer_type"] = "single"

        if self.matrices_groupbox.isChecked() and self.matrices_data_cache:
            formatted_matrices = {}
            for m_data in self.matrices_data_cache:
                try:
                    numeric_matrix_data = [
                        [(int(cell) if cell.strip() else 0) for cell in row]
                        for row in m_data["data"]
                    ]
                    formatted_matrices[m_data["name"]] = numeric_matrix_data
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Ошибка данных матрицы",
                        f"Матрица {m_data['name']} содержит нечисловые значения.",
                    )
                    return
            new_data["matrices"] = formatted_matrices
            if "commands" in new_data:
                del new_data["commands"]
        elif self.commands_groupbox.isChecked():
            commands = [
                self.commands_list_widget_edit.item(i).text()
                for i in range(self.commands_list_widget_edit.count())
            ]
            if commands:
                new_data["commands"] = commands
            if "matrices" in new_data:
                del new_data["matrices"]
        else:
            if "matrices" in new_data:
                del new_data["matrices"]
            if "commands" in new_data:
                del new_data["commands"]

        new_data["points"] = self.points_spinbox_edit.value()

        self.save_question_changes_signal.emit(
            new_topic_name, self.question_idx, new_data
        )

    def on_delete_question(self):
        reply = QMessageBox.question(
            self,
            "Удаление вопроса",
            "Вы уверены, что хотите удалить этот вопрос?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.delete_question_signal.emit(self.topic_name, self.question_idx)


class AdminWindow(QWidget):

    open_teacher_view_signal = pyqtSignal()
    open_student_view_signal = pyqtSignal()
    manage_users_signal = pyqtSignal()
    manage_groups_signal = pyqtSignal()
    edit_grading_criteria_signal = pyqtSignal()
    toggle_theme_signal = pyqtSignal()
    logout_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Панель администратора")
        self.setGeometry(100, 100, 780, 600)
        self.init_ui()
        _restore_window_geometry(self, "AdminWindow")

    def closeEvent(self, event):
        _save_window_geometry(self, "AdminWindow")
        super().closeEvent(event)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.title_label = QLabel("Добро пожаловать, Администратор!")
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)
        layout.addSpacerItem(
            QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Fixed)
        )

        self.as_teacher_button = QPushButton("Открыть панель преподавателя")
        self.as_teacher_button.clicked.connect(self.open_teacher_view_signal.emit)
        self.as_teacher_button.setFixedHeight(40)
        layout.addWidget(self.as_teacher_button)

        self.as_student_button = QPushButton(
            "Открыть панель студента (для тестирования)"
        )
        self.as_student_button.clicked.connect(self.open_student_view_signal.emit)
        self.as_student_button.setFixedHeight(40)
        layout.addWidget(self.as_student_button)

        layout.addSpacerItem(
            QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        )

        self.manage_users_button = QPushButton("Управление ролями пользователей")
        self.manage_users_button.clicked.connect(self.manage_users_signal.emit)
        self.manage_users_button.setFixedHeight(40)
        layout.addWidget(self.manage_users_button)

        self.manage_groups_button = QPushButton("Управление группами")
        self.manage_groups_button.clicked.connect(self.manage_groups_signal.emit)
        self.manage_groups_button.setFixedHeight(40)
        layout.addWidget(self.manage_groups_button)

        self.edit_criteria_button = QPushButton("Редактировать критерии оценки")
        self.edit_criteria_button.clicked.connect(
            self.edit_grading_criteria_signal.emit
        )
        self.edit_criteria_button.setFixedHeight(40)
        layout.addWidget(self.edit_criteria_button)

        layout.addSpacerItem(
            QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        self.toggle_theme_button = QPushButton("Сменить тему")
        self.toggle_theme_button.clicked.connect(self.toggle_theme_signal.emit)
        self.toggle_theme_button.setFixedHeight(40)
        layout.addWidget(self.toggle_theme_button)

        self.logout_button = QPushButton("Выйти из аккаунта")
        self.logout_button.clicked.connect(self.logout_signal.emit)
        self.logout_button.setFixedHeight(40)
        layout.addWidget(self.logout_button)

        self.setLayout(layout)


class ManageGroupsDialog(QDialog):

    def __init__(self, groups, api_client, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление группами")
        self.setMinimumSize(450, 400)
        self.api = api_client
        self.groups = list(groups) if groups else []
        _restore_window_geometry(self, "ManageGroupsDialog")
        self.init_ui()
        self._refresh_list()

    def closeEvent(self, event):
        _save_window_geometry(self, "ManageGroupsDialog")
        super().closeEvent(event)

    def init_ui(self):
        layout = QVBoxLayout(self)

        add_layout = QHBoxLayout()
        self.group_name_input = QLineEdit()
        self.group_name_input.setPlaceholderText("Название новой группы")
        self.group_name_input.setFixedHeight(32)
        add_layout.addWidget(self.group_name_input)
        self.add_button = QPushButton("Создать")
        self.add_button.setFixedHeight(32)
        self.add_button.clicked.connect(self._on_create_group)
        add_layout.addWidget(self.add_button)
        layout.addLayout(add_layout)

        self.groups_list = QListWidget()
        layout.addWidget(self.groups_list)

        self.delete_button = QPushButton("Удалить выбранную группу")
        self.delete_button.setFixedHeight(36)
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self._on_delete_group)
        layout.addWidget(self.delete_button)

        self.rename_button = QPushButton("Переименовать выбранную группу")
        self.rename_button.setFixedHeight(36)
        self.rename_button.clicked.connect(self._on_rename_group)
        layout.addWidget(self.rename_button)

        close_btn = QPushButton("Закрыть")
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _refresh_list(self):
        self.groups_list.clear()
        for g in sorted(self.groups):
            self.groups_list.addItem(g)

    def _on_create_group(self):
        name = self.group_name_input.text().strip()
        if not name:
            return
        success, msg = self.api.create_group(name)
        if success:
            self.groups.append(name)
            self._refresh_list()
            self.group_name_input.clear()
            QMessageBox.information(self, "Группа создана", msg)
        else:
            QMessageBox.warning(self, "Ошибка", msg)

    def _on_delete_group(self):
        item = self.groups_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Ошибка", "Выберите группу для удаления.")
            return
        name = item.text()
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить группу «{name}»?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            success, msg = self.api.delete_group(name)
            if success:
                self.groups.remove(name)
                self._refresh_list()
                QMessageBox.information(self, "Группа удалена", msg)
            else:
                QMessageBox.warning(self, "Ошибка", msg)

    def _on_rename_group(self):
        item = self.groups_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Ошибка", "Выберите группу для переименования.")
            return
        old_name = item.text()
        new_name, ok = QInputDialog.getText(
            self, "Переименование", "Новое название группы:", text=old_name
        )
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        if new_name == old_name:
            return
        success, msg = self.api.rename_group(old_name, new_name)
        if success:
            idx = self.groups.index(old_name)
            self.groups[idx] = new_name
            self._refresh_list()
            QMessageBox.information(self, "Группа переименована", msg)
        else:
            QMessageBox.warning(self, "Ошибка", msg)


class ItemContainerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dynamic_min_h = 0

    def setDynamicMinimumHeight(self, min_h):
        self._dynamic_min_h = min_h

        super().setMinimumHeight(min_h)
        self.updateGeometry()

    def sizeHint(self):

        hint = QWidget.sizeHint(self)
        if self.layout() is not None:
            hint = self.layout().sizeHint()

        if self._dynamic_min_h > hint.height():
            hint.setHeight(self._dynamic_min_h)
        return hint


class CreatePremadeTestDialog(QDialog):
    save_premade_test_signal = pyqtSignal(str, list)
    edit_grading_criteria_signal = pyqtSignal()

    def __init__(self, all_questions_data_with_display_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать новый готовый тест")
        self.setGeometry(150, 150, 950, 920)
        _restore_window_geometry(self, "CreatePremadeTestDialog")

        self.raw_questions_data_with_display_info = all_questions_data_with_display_info
        self.currently_displayed_questions_info = list(
            self.raw_questions_data_with_display_info
        )

        self.unique_topics = sorted(
            list(
                set(
                    q_info["original_question"].get("category", "Без категории")
                    for q_info in self.raw_questions_data_with_display_info
                )
            )
        )

        self.checked_identifiers = set()
        self.expanded_item_row = -1
        self.pending_test_criteria = None

        self.init_ui()

        self.questions_list_widget.itemClicked.connect(
            self.handle_item_left_click_for_selection
        )

        self.populate_questions_list_widget()

    def done(self, result):
        _save_window_geometry(self, "CreatePremadeTestDialog")
        super().done(result)

    def _get_question_identifier(self, question_dict):
        uid = question_dict.get("_uid")
        if uid is not None:
            return uid
        return (
            question_dict.get("category", "Uncategorized"),
            question_dict.get("question", "NoText"),
        )

    def _create_item_widget(self, q_info_dict, is_expanded=False):
        question_obj = q_info_dict["original_question"]
        topic = question_obj.get("category", "Без категории")

        item_container_widget = ItemContainerWidget()
        layout = QVBoxLayout(item_container_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        checkbox = QCheckBox(f"[Тема: {topic}]")
        checkbox.setProperty("original_question_obj", question_obj)
        identifier = self._get_question_identifier(question_obj)
        checkbox.setChecked(identifier in self.checked_identifiers)
        checkbox.stateChanged.connect(self.on_individual_checkbox_changed)
        top_row.addWidget(checkbox)
        top_row.addStretch()
        layout.addLayout(top_row)

        q_label = QLabel(question_obj.get("question", "Текст вопроса отсутствует."))
        q_label.setWordWrap(True)
        q_label.setContentsMargins(24, 0, 4, 4)
        layout.addWidget(q_label)

        item_container_widget.setLayout(layout)
        item_container_widget.setDynamicMinimumHeight(0)
        return item_container_widget

    def init_ui(self):
        layout = QVBoxLayout(self)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Название теста:"))
        self.test_name_input = QLineEdit()
        self.test_name_input.setPlaceholderText("Введите название для нового теста")
        name_layout.addWidget(self.test_name_input)
        layout.addLayout(name_layout)

        self.edit_criteria_button = QPushButton("Настроить критерии оценки для теста")
        self.edit_criteria_button.clicked.connect(
            self.edit_grading_criteria_signal.emit
        )
        layout.addWidget(self.edit_criteria_button, alignment=Qt.AlignRight)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Фильтр по теме:"))
        self.topic_filter_combo = QComboBox()
        self.topic_filter_combo.addItem("Все темы")
        self.topic_filter_combo.addItems(self.unique_topics)
        self.topic_filter_combo.currentTextChanged.connect(
            self.apply_filters_and_repopulate_list
        )
        filter_layout.addWidget(self.topic_filter_combo)

        self.select_all_checkbox = QtWidgets.QCheckBox("Выбрать/Снять все видимые")
        self.select_all_checkbox.stateChanged.connect(
            self.toggle_select_all_visible_items
        )
        filter_layout.addWidget(self.select_all_checkbox)
        filter_layout.addStretch(1)
        layout.addLayout(filter_layout)

        layout.addWidget(QLabel("ЛКМ — выбрать/снять вопрос:"))
        self.questions_list_widget = QListWidget()
        self.questions_list_widget.setMinimumHeight(400)
        layout.addWidget(self.questions_list_widget)

        settings_group = QtWidgets.QGroupBox("Настройки теста")
        settings_layout = QVBoxLayout(settings_group)

        timer_layout = QHBoxLayout()
        timer_layout.addWidget(QLabel("Ограничение времени (мин, 0 = нет):"))
        self.time_limit_spin = QtWidgets.QSpinBox()
        self.time_limit_spin.setRange(0, 300)
        self.time_limit_spin.setValue(0)
        self.time_limit_spin.setToolTip("0 — без ограничения времени")
        timer_layout.addWidget(self.time_limit_spin)
        settings_layout.addLayout(timer_layout)

        cooldown_layout = QHBoxLayout()
        cooldown_layout.addWidget(QLabel("Кулдаун между попытками (ч, 0 = нет):"))
        self.cooldown_spin = QtWidgets.QSpinBox()
        self.cooldown_spin.setRange(0, 720)
        self.cooldown_spin.setValue(24)
        self.cooldown_spin.setToolTip("0 — без кулдауна")
        cooldown_layout.addWidget(self.cooldown_spin)
        settings_layout.addLayout(cooldown_layout)

        attempts_layout = QHBoxLayout()
        attempts_layout.addWidget(QLabel("Макс. кол-во попыток (0 = неограниченно):"))
        self.max_attempts_spin = QtWidgets.QSpinBox()
        self.max_attempts_spin.setRange(0, 100)
        self.max_attempts_spin.setValue(0)
        self.max_attempts_spin.setToolTip("0 — неограниченно")
        attempts_layout.addWidget(self.max_attempts_spin)
        settings_layout.addLayout(attempts_layout)

        grading_layout = QHBoxLayout()
        grading_layout.addWidget(QLabel("Режим оценки:"))
        self.grading_mode_combo = QComboBox()
        self.grading_mode_combo.addItem("Общий (по всему тесту)", "overall")
        self.grading_mode_combo.addItem(
            "По темам (все темы должны быть зачтены)", "per_topic"
        )
        grading_layout.addWidget(self.grading_mode_combo)
        settings_layout.addLayout(grading_layout)

        self.show_results_check = QtWidgets.QCheckBox(
            "Показывать результаты студентам (правильные ответы)"
        )
        self.show_results_check.setChecked(True)
        settings_layout.addWidget(self.show_results_check)

        layout.addWidget(settings_group)

        self.save_button = QPushButton(
            "\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0442\u0435\u0441\u0442"
        )
        self.save_button.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        self.save_button.clicked.connect(self.on_save_test)
        layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("\u041e\u0442\u043c\u0435\u043d\u0430")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

    def populate_questions_list_widget(self):
        current_scroll_value = self.questions_list_widget.verticalScrollBar().value()
        self.questions_list_widget.clear()

        if not self.currently_displayed_questions_info:
            self.update_select_all_checkbox_state()
            return

        for i, q_info in enumerate(self.currently_displayed_questions_info):
            item = QtWidgets.QListWidgetItem(self.questions_list_widget)
            item.setData(Qt.UserRole, q_info)

            is_expanded_state = i == self.expanded_item_row
            widget_to_set = self._create_item_widget(q_info, is_expanded_state)

            self.questions_list_widget.setItemWidget(item, widget_to_set)
            item.setSizeHint(widget_to_set.sizeHint())

        self.questions_list_widget.verticalScrollBar().setValue(current_scroll_value)
        self.update_select_all_checkbox_state()

    def handle_item_left_click_for_selection(self, clicked_item):
        if not clicked_item:
            return

        item_widget = self.questions_list_widget.itemWidget(clicked_item)
        if (
            item_widget
            and hasattr(item_widget, "layout")
            and item_widget.layout() is not None
        ):

            checkbox = item_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.toggle()

    def handle_item_right_click_for_expansion(self, position):
        clicked_item = self.questions_list_widget.itemAt(position)
        if not clicked_item:
            return

        clicked_row = self.questions_list_widget.row(clicked_item)
        q_info = clicked_item.data(Qt.UserRole)
        if not q_info:
            return

        if self.expanded_item_row != -1 and self.expanded_item_row != clicked_row:
            previous_expanded_item = self.questions_list_widget.item(
                self.expanded_item_row
            )
            if previous_expanded_item:
                prev_q_info = previous_expanded_item.data(Qt.UserRole)
                if prev_q_info:
                    collapsed_widget = self._create_item_widget(
                        prev_q_info, is_expanded=False
                    )
                    self.questions_list_widget.setItemWidget(
                        previous_expanded_item, collapsed_widget
                    )
                    previous_expanded_item.setSizeHint(collapsed_widget.sizeHint())

        new_widget = None
        if clicked_row == self.expanded_item_row:
            new_widget = self._create_item_widget(q_info, is_expanded=False)
            self.expanded_item_row = -1
        else:
            new_widget = self._create_item_widget(q_info, is_expanded=True)
            self.expanded_item_row = clicked_row

        if new_widget:
            self.questions_list_widget.setItemWidget(clicked_item, new_widget)
            clicked_item.setSizeHint(new_widget.sizeHint())

    def on_individual_checkbox_changed(self):

        checkbox = self.sender()
        if not isinstance(checkbox, QCheckBox):
            return

        question_obj = checkbox.property("original_question_obj")
        if not question_obj:
            return

        identifier = self._get_question_identifier(question_obj)

        is_checked = checkbox.isChecked()
        if is_checked:
            self.checked_identifiers.add(identifier)
        else:
            self.checked_identifiers.discard(identifier)

        self.update_select_all_checkbox_state()

    def apply_filters_and_repopulate_list(self):
        selected_topic = self.topic_filter_combo.currentText()
        self.currently_displayed_questions_info.clear()

        for q_info in self.raw_questions_data_with_display_info:
            category = q_info["original_question"].get("category", "Без категории")
            if selected_topic == "Все темы" or category == selected_topic:
                self.currently_displayed_questions_info.append(q_info)

        self.expanded_item_row = -1
        self.populate_questions_list_widget()

    def toggle_select_all_visible_items(self, state):
        desired_checked_state = state == Qt.Checked

        for i in range(self.questions_list_widget.count()):
            item = self.questions_list_widget.item(i)
            item_widget = self.questions_list_widget.itemWidget(item)

            target_checkbox = None
            if isinstance(item_widget, QWidget) and hasattr(item_widget, "findChild"):
                target_checkbox = item_widget.findChild(QCheckBox)

            if target_checkbox:

                if target_checkbox.isChecked() != desired_checked_state:
                    target_checkbox.setChecked(desired_checked_state)

        self.update_select_all_checkbox_state()

    def update_select_all_checkbox_state(self):
        if self.questions_list_widget.count() == 0:
            self.select_all_checkbox.setEnabled(False)
            self.select_all_checkbox.blockSignals(True)
            self.select_all_checkbox.setChecked(False)
            self.select_all_checkbox.blockSignals(False)
            return

        self.select_all_checkbox.setEnabled(True)

        all_visible_are_actually_checked = True

        if not self.currently_displayed_questions_info:
            all_visible_are_actually_checked = False
        else:

            visible_q_info_identifiers = set()
            for q_info_dict in self.currently_displayed_questions_info:
                question_obj = q_info_dict["original_question"]
                visible_q_info_identifiers.add(
                    self._get_question_identifier(question_obj)
                )

            if not visible_q_info_identifiers:
                all_visible_are_actually_checked = False
            else:
                for identifier in visible_q_info_identifiers:
                    if identifier not in self.checked_identifiers:
                        all_visible_are_actually_checked = False
                        break

        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(all_visible_are_actually_checked)
        self.select_all_checkbox.blockSignals(False)

    def on_save_test(self):
        test_name = self.test_name_input.text().strip()
        if not test_name:
            QMessageBox.warning(self, "Ошибка", "Название теста не может быть пустым.")
            return

        selected_question_objects = []
        for q_info in self.raw_questions_data_with_display_info:
            original_q = q_info["original_question"]
            identifier = self._get_question_identifier(original_q)
            if identifier in self.checked_identifiers:
                q_to_save = {k: v for k, v in original_q.items() if k != "_uid"}
                selected_question_objects.append(q_to_save)

        if not selected_question_objects:
            QMessageBox.warning(
                self, "Ошибка", "Необходимо выбрать хотя бы один вопрос для теста."
            )
            return

        self.save_premade_test_signal.emit(test_name, selected_question_objects)

    def set_criteria(self, criteria_list):

        self.pending_test_criteria = criteria_list
        self.edit_criteria_button.setText(
            "Настроить критерии оценки для теста \u2713"
            if criteria_list
            else "Настроить критерии оценки для теста"
        )

    @property
    def time_limit_minutes_value(self):
        v = self.time_limit_spin.value()
        return v if v > 0 else None

    @property
    def cooldown_hours_value(self):
        return self.cooldown_spin.value()

    @property
    def max_attempts_value(self):
        v = self.max_attempts_spin.value()
        return v if v > 0 else None

    @property
    def grading_mode_value(self):
        return self.grading_mode_combo.currentData()

    @property
    def show_results_value(self):
        return self.show_results_check.isChecked()

    def show_message(self, title, message, is_error=False):
        if is_error:
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)


class ManageTestsPanel(QWidget):

    update_assignments_signal = pyqtSignal(str, list, list)
    delete_test_signal = pyqtSignal(str)
    delete_question_from_test_signal = pyqtSignal(str, int)
    edit_grading_criteria_signal = pyqtSignal()
    edit_test_criteria_signal = pyqtSignal(str)
    show_test_statistics_signal = pyqtSignal(str, str)
    request_add_questions_signal = pyqtSignal(str)
    clone_test_signal = pyqtSignal(str)
    rename_test_signal = pyqtSignal(str, str)
    edit_test_settings_signal = pyqtSignal(str, object)
    share_test_signal = pyqtSignal(str)
    unshare_test_signal = pyqtSignal(str)

    def __init__(
        self,
        premade_tests_list,
        all_students,
        all_groups=None,
        students_by_group=None,
        parent=None,
    ):
        super().__init__(parent)
        self.premade_tests = premade_tests_list
        self.all_students_usernames = sorted(list(set(all_students)))
        self.all_groups = all_groups or []
        self.students_by_group = students_by_group or {}
        self.current_selected_test_id = None
        self.current_selected_test_object = None
        self.parent_controller_ref = parent
        self.expanded_question_index_in_test = -1
        self._student_checkstates = {}
        self._saved_checkstates = {}
        self._has_unsaved_changes = False
        self._share_token = None

        self.init_ui()
        self.populate_tests_list()

    def _create_question_display_widget(
        self, question_text_full, question_index_display, is_expanded
    ):

        container_widget = ItemContainerWidget()
        layout = QVBoxLayout(container_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        short_label = QLabel(f"{question_index_display}. {question_text_full}")
        short_label.setWordWrap(False)

        short_label.setObjectName("shortQuestionPreviewLabel")
        layout.addWidget(short_label)

        if is_expanded:
            full_label = QLabel(question_text_full)
            full_label.setWordWrap(True)

            full_label.setObjectName("expandedQuestionTextLabelMng")
            layout.addWidget(full_label)
            container_widget.setDynamicMinimumHeight(0)
        else:
            container_widget.setDynamicMinimumHeight(40)

        container_widget.setLayout(layout)
        return container_widget

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)

        left_panel_widget = QWidget()
        left_layout = QVBoxLayout(left_panel_widget)
        left_layout.addWidget(QLabel("Готовые тесты:"))
        self.tests_list_widget = QListWidget()
        self.tests_list_widget.itemClicked.connect(self.on_test_selected)
        left_layout.addWidget(self.tests_list_widget)

        self.delete_test_button = QPushButton("Удалить выбранный тест")
        self.delete_test_button.setEnabled(False)
        self.delete_test_button.setFixedHeight(30)
        self.delete_test_button.setObjectName("dangerButton")
        self.delete_test_button.clicked.connect(self.on_delete_test_clicked)
        left_layout.addWidget(self.delete_test_button)

        self.edit_test_criteria_button = QPushButton(
            "Настроить критерии для этого теста"
        )
        self.edit_test_criteria_button.setEnabled(False)
        self.edit_test_criteria_button.setFixedHeight(30)
        self.edit_test_criteria_button.clicked.connect(
            self._on_edit_test_criteria_clicked
        )
        left_layout.addWidget(self.edit_test_criteria_button)

        self.show_statistics_button = QPushButton("Статистика по тесту")
        self.show_statistics_button.setEnabled(False)
        self.show_statistics_button.setFixedHeight(30)
        self.show_statistics_button.clicked.connect(self._on_show_statistics_clicked)
        left_layout.addWidget(self.show_statistics_button)

        self.clone_test_button = QPushButton("Клонировать тест")
        self.clone_test_button.setEnabled(False)
        self.clone_test_button.setFixedHeight(30)
        self.clone_test_button.clicked.connect(self._on_clone_test_clicked)
        left_layout.addWidget(self.clone_test_button)

        self.rename_test_button = QPushButton("Переименовать тест")
        self.rename_test_button.setEnabled(False)
        self.rename_test_button.setFixedHeight(30)
        self.rename_test_button.clicked.connect(self._on_rename_test_clicked)
        left_layout.addWidget(self.rename_test_button)

        self.edit_test_settings_button = QPushButton("Настройки теста")
        self.edit_test_settings_button.setEnabled(False)
        self.edit_test_settings_button.setFixedHeight(30)
        self.edit_test_settings_button.clicked.connect(
            self._on_edit_test_settings_clicked
        )
        left_layout.addWidget(self.edit_test_settings_button)

        self.share_test_button = QPushButton("Поделиться тестом")
        self.share_test_button.setEnabled(False)
        self.share_test_button.setFixedHeight(30)
        self.share_test_button.clicked.connect(self._on_share_test_clicked)
        left_layout.addWidget(self.share_test_button)

        right_panel_widget = QWidget()
        self.right_layout = QVBoxLayout(right_panel_widget)

        self.test_details_group = QtWidgets.QGroupBox(
            "Детали теста (ПКМ на вопрос для полного текста)"
        )
        self.test_details_layout = QVBoxLayout(self.test_details_group)
        self.test_name_label = QLabel("Название: N/A")
        self.test_creator_label = QLabel("Создатель: N/A")
        self.test_grading_label = QLabel("Режим оценки: N/A")

        self.test_questions_list_widget = QListWidget()
        self.test_questions_list_widget.setMinimumHeight(250)

        self.test_questions_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.test_questions_list_widget.customContextMenuRequested.connect(
            self.handle_test_question_right_click
        )
        self.test_questions_list_widget.itemSelectionChanged.connect(
            self.on_test_question_selected_for_deletion
        )

        self.test_details_layout.addWidget(self.test_name_label)
        self.test_details_layout.addWidget(self.test_creator_label)
        self.test_details_layout.addWidget(self.test_grading_label)
        self.test_details_layout.addWidget(QLabel("Вопросы в тесте:"))
        self.test_details_layout.addWidget(self.test_questions_list_widget)

        self.delete_question_from_test_button = QPushButton(
            "Удалить выбранный вопрос из этого теста"
        )
        self.delete_question_from_test_button.setEnabled(False)
        self.delete_question_from_test_button.setFixedHeight(30)
        self.delete_question_from_test_button.setObjectName("dangerButton")
        self.delete_question_from_test_button.clicked.connect(
            self.on_delete_question_from_test_button_clicked
        )
        self.test_details_layout.addWidget(self.delete_question_from_test_button)

        self.add_questions_button = QPushButton("Добавить вопросы в тест")
        self.add_questions_button.setEnabled(False)
        self.add_questions_button.setFixedHeight(30)
        self.add_questions_button.clicked.connect(self._on_add_questions_clicked)
        self.test_details_layout.addWidget(self.add_questions_button)

        self.share_link_widget = QWidget()
        share_link_layout = QVBoxLayout(self.share_link_widget)
        share_link_layout.setContentsMargins(8, 8, 8, 8)
        self.share_link_label = QLabel("")
        self.share_link_label.setWordWrap(True)
        self.share_link_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        share_link_layout.addWidget(self.share_link_label)
        share_btn_row = QHBoxLayout()
        self.copy_share_link_button = QPushButton("Копировать ссылку")
        self.copy_share_link_button.clicked.connect(self._on_copy_share_link)
        share_btn_row.addWidget(self.copy_share_link_button)
        self.revoke_share_button = QPushButton("Отозвать ссылку")
        self.revoke_share_button.setObjectName("dangerButton")
        self.revoke_share_button.clicked.connect(self._on_revoke_share_clicked)
        share_btn_row.addWidget(self.revoke_share_button)
        share_link_layout.addLayout(share_btn_row)
        self.share_link_widget.hide()
        self.test_details_layout.addWidget(self.share_link_widget)

        self.right_layout.addWidget(self.test_details_group)

        self.assignment_group = QtWidgets.QGroupBox(
            "Назначение студентам для выбранного теста"
        )
        self.assignment_layout = QVBoxLayout(self.assignment_group)

        group_filter_layout = QHBoxLayout()
        group_filter_layout.addWidget(QLabel("Группа:"))
        self.group_filter_combo = QComboBox()
        self.group_filter_combo.addItem("-- Все группы --")
        self.group_filter_combo.currentTextChanged.connect(
            self._on_group_filter_changed
        )
        group_filter_layout.addWidget(self.group_filter_combo)
        self.assign_group_button = QPushButton("Назначить всех в группе")
        self.assign_group_button.setEnabled(False)
        self.assign_group_button.clicked.connect(self._on_assign_group_clicked)
        group_filter_layout.addWidget(self.assign_group_button)
        self.assignment_layout.addLayout(group_filter_layout)

        self.all_students_checklist_widget = QListWidget()
        self.all_students_checklist_widget.itemChanged.connect(
            self._on_student_item_changed
        )
        self.assignment_layout.addWidget(
            QLabel("Все студенты (отметьте для назначения):")
        )
        self.assignment_layout.addWidget(self.all_students_checklist_widget)

        self.save_assignments_button = QPushButton(
            "Сохранить назначения для этого теста"
        )
        self.save_assignments_button.clicked.connect(
            self.on_save_assignments_clicked_correct_logic
        )
        self.save_assignments_button.setEnabled(False)
        self.assignment_layout.addWidget(self.save_assignments_button)

        self.right_layout.addWidget(self.assignment_group)

        self.main_layout.addWidget(left_panel_widget, 1)
        self.main_layout.addWidget(right_panel_widget, 2)

    def populate_tests_list(self, tests_to_display=None):
        self.tests_list_widget.clear()
        if tests_to_display is not None:
            self.premade_tests = tests_to_display

        if not self.premade_tests:
            self.tests_list_widget.addItem("Нет созданных тестов.")
            return

        for test in self.premade_tests:
            display_text = f"{test.get('test_name', 'Без имени')}"
            item = QtWidgets.QListWidgetItem(display_text)
            item.setData(Qt.UserRole, test)
            self.tests_list_widget.addItem(item)

        self.group_filter_combo.blockSignals(True)
        self.group_filter_combo.clear()
        self.group_filter_combo.addItem("-- Все группы --")
        self.group_filter_combo.addItems(self.all_groups)
        self.group_filter_combo.blockSignals(False)

    def on_test_selected(self, item):

        test_data = item.data(Qt.UserRole)

        if self._has_unsaved_changes:
            _msg = QMessageBox(self)
            _msg.setWindowTitle("Несохранённые изменения")
            _msg.setText(
                "Изменения назначений не сохранены. Сохранить перед переходом?"
            )
            _save_btn = _msg.addButton("Сохранить", QMessageBox.AcceptRole)
            _msg.addButton("Не сохранять", QMessageBox.DestructiveRole)
            _cancel_btn = _msg.addButton("Отмена", QMessageBox.RejectRole)
            _msg.setDefaultButton(_save_btn)
            _msg.exec_()
            _clicked = _msg.clickedButton()
            if _clicked == _save_btn:
                self.on_save_assignments_clicked_correct_logic()
            elif _clicked == _cancel_btn:

                self.tests_list_widget.blockSignals(True)
                for i in range(self.tests_list_widget.count()):
                    td = self.tests_list_widget.item(i).data(Qt.UserRole)
                    if td and td.get("test_id") == self.current_selected_test_id:
                        self.tests_list_widget.setCurrentRow(i)
                        break
                self.tests_list_widget.blockSignals(False)
                return

        if not test_data:
            self.clear_details_and_assignments()
            self.delete_test_button.setEnabled(False)
            self.edit_test_criteria_button.setEnabled(False)
            return

        self.current_selected_test_object = test_data
        self.current_selected_test_id = test_data.get("test_id")
        self.expanded_question_index_in_test = -1

        self.test_name_label.setText(f"Название: {test_data.get('test_name', 'N/A')}")
        self.test_creator_label.setText(
            f"Создатель: {test_data.get('creator_username', 'N/A')}"
        )
        grading_mode = test_data.get("grading_mode", "overall")
        self.test_grading_label.setText(
            f"Режим оценки: {'По темам' if grading_mode == 'per_topic' else 'Общий'}"
        )

        self.populate_test_questions_list_widget()

        self.populate_all_students_checklist(test_data.get("assigned_students", []))
        self.save_assignments_button.setEnabled(bool(self.current_selected_test_id))
        self.delete_test_button.setEnabled(bool(self.current_selected_test_id))
        self.edit_test_criteria_button.setEnabled(bool(self.current_selected_test_id))
        self.show_statistics_button.setEnabled(bool(self.current_selected_test_id))
        self.add_questions_button.setEnabled(bool(self.current_selected_test_id))
        self.clone_test_button.setEnabled(bool(self.current_selected_test_id))
        self.rename_test_button.setEnabled(bool(self.current_selected_test_id))
        self.edit_test_settings_button.setEnabled(bool(self.current_selected_test_id))
        self.share_test_button.setEnabled(bool(self.current_selected_test_id))
        self.delete_question_from_test_button.setEnabled(False)

        self._share_token = test_data.get("share_token") or None
        self._update_share_link_display()

    def populate_test_questions_list_widget(self):
        self.test_questions_list_widget.clear()
        if (
            not self.current_selected_test_object
            or "questions" not in self.current_selected_test_object
        ):
            self.delete_question_from_test_button.setEnabled(False)
            self.save_assignments_button.setEnabled(False)
            self.delete_test_button.setEnabled(False)
            self.edit_test_criteria_button.setEnabled(False)
            self.current_selected_test_id = None
            self.current_selected_test_object = None
            return

        questions_in_test = self.current_selected_test_object.get("questions", [])
        for q_idx, q_obj in enumerate(questions_in_test):
            item = QtWidgets.QListWidgetItem(self.test_questions_list_widget)

            item.setData(Qt.UserRole, {"question_obj": q_obj, "original_index": q_idx})

            is_expanded_state = q_idx == self.expanded_question_index_in_test
            widget_to_set = self._create_question_display_widget(
                q_obj.get("question", "Текст вопроса отсутствует"),
                q_idx + 1,
                is_expanded_state,
            )
            self.test_questions_list_widget.setItemWidget(item, widget_to_set)
            item.setSizeHint(widget_to_set.sizeHint())

        self.delete_question_from_test_button.setEnabled(
            self.test_questions_list_widget.currentRow() != -1
        )

    def handle_test_question_right_click(self, position):
        clicked_item = self.test_questions_list_widget.itemAt(position)
        if not clicked_item:
            return

        clicked_row = self.test_questions_list_widget.row(clicked_item)
        data = clicked_item.data(Qt.UserRole)
        if not data or "question_obj" not in data:
            return

        question_obj = data["question_obj"]
        question_text_full = question_obj.get("question", "Текст вопроса отсутствует")
        display_index = data["original_index"] + 1

        if (
            self.expanded_question_index_in_test != -1
            and self.expanded_question_index_in_test != clicked_row
        ):
            prev_item = self.test_questions_list_widget.item(
                self.expanded_question_index_in_test
            )
            if prev_item:
                prev_data = prev_item.data(Qt.UserRole)
                if prev_data:
                    prev_q_text = prev_data["question_obj"].get(
                        "question", "Текст вопроса отсутствует"
                    )
                    prev_disp_idx = prev_data["original_index"] + 1
                    collapsed_widget = self._create_question_display_widget(
                        prev_q_text, prev_disp_idx, False
                    )
                    self.test_questions_list_widget.setItemWidget(
                        prev_item, collapsed_widget
                    )
                    prev_item.setSizeHint(collapsed_widget.sizeHint())

        new_widget = None
        if clicked_row == self.expanded_question_index_in_test:
            new_widget = self._create_question_display_widget(
                question_text_full, display_index, False
            )
            self.expanded_question_index_in_test = -1
        else:
            new_widget = self._create_question_display_widget(
                question_text_full, display_index, True
            )
            self.expanded_question_index_in_test = clicked_row

        if new_widget:
            self.test_questions_list_widget.setItemWidget(clicked_item, new_widget)
            clicked_item.setSizeHint(new_widget.sizeHint())

    def on_test_question_selected_for_deletion(self):
        self.delete_question_from_test_button.setEnabled(
            self.test_questions_list_widget.currentRow() != -1
            and self.current_selected_test_id is not None
        )

    def on_delete_question_from_test_button_clicked(self):
        selected_items = self.test_questions_list_widget.selectedItems()
        if not selected_items or not self.current_selected_test_id:
            self.show_message("Ошибка", "Тест или вопрос не выбран для удаления.", True)
            return

        selected_list_item = selected_items[0]
        data = selected_list_item.data(Qt.UserRole)
        if not data or "original_index" not in data:
            self.show_message("Ошибка", "Не удалось получить индекс вопроса.", True)
            return

        question_index_in_test = data["original_index"]
        question_text_preview = data["question_obj"].get("question", "этот вопрос")[:30]

        message_text = f"Вы уверены, что хотите удалить вопрос '{question_text_preview}...' из теста '{self.current_selected_test_object.get('test_name', '')}'?\nЭто действие нельзя отменить."
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления вопроса",
            message_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.delete_question_from_test_signal.emit(
                self.current_selected_test_id, question_index_in_test
            )

    def populate_all_students_checklist(self, currently_assigned_usernames_for_test):

        currently_assigned_set = set(currently_assigned_usernames_for_test)
        self._student_checkstates = {
            u: (u in currently_assigned_set) for u in self.all_students_usernames
        }
        self._saved_checkstates = dict(self._student_checkstates)
        self._has_unsaved_changes = False
        self._render_student_list()

    def _sync_checkstates_from_widget(self):

        for i in range(self.all_students_checklist_widget.count()):
            item = self.all_students_checklist_widget.item(i)
            if item:
                self._student_checkstates[item.text()] = item.checkState() == Qt.Checked

    def _render_student_list(self):

        group_filter = self.group_filter_combo.currentText()
        if group_filter and group_filter != "-- Все группы --":
            students_to_show = [
                u
                for u in self.all_students_usernames
                if u in self.students_by_group.get(group_filter, [])
            ]
        else:
            students_to_show = self.all_students_usernames

        self.all_students_checklist_widget.blockSignals(True)
        self.all_students_checklist_widget.clear()
        for username in students_to_show:
            item = QtWidgets.QListWidgetItem(
                username, self.all_students_checklist_widget
            )
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(
                Qt.Checked
                if self._student_checkstates.get(username, False)
                else Qt.Unchecked
            )
        self.all_students_checklist_widget.blockSignals(False)

        self._update_assign_group_button_text()

    def _update_assign_group_button_text(self):
        group_text = self.group_filter_combo.currentText()
        if not group_text or group_text == "-- Все группы --":
            self.assign_group_button.setText("Назначить всех в группе")
            return
        group_students = self.students_by_group.get(group_text, [])
        if not group_students:
            self.assign_group_button.setText("Назначить всех в группе")
            return
        all_checked = all(
            self._student_checkstates.get(u, False)
            for u in group_students
            if u in self._student_checkstates
        ) and any(u in self._student_checkstates for u in group_students)
        self.assign_group_button.setText(
            "Снять всех в группе" if all_checked else "Назначить всех в группе"
        )

    def on_save_assignments_clicked_correct_logic(self):
        if not self.current_selected_test_id or not self.current_selected_test_object:
            self.show_message(
                "Ошибка", "Тест не выбран для сохранения назначений.", True
            )
            return

        self._sync_checkstates_from_widget()

        desired_assigned_set = {
            u for u, checked in self._student_checkstates.items() if checked
        }
        currently_assigned_set = set(
            self.current_selected_test_object.get("assigned_students", [])
        )

        to_assign = list(desired_assigned_set - currently_assigned_set)
        to_unassign = list(currently_assigned_set - desired_assigned_set)

        if not to_assign and not to_unassign:
            self.show_message(
                "Информация", "Нет изменений в назначениях.", is_error=False
            )
            self._has_unsaved_changes = False
            return

        self._saved_checkstates = dict(self._student_checkstates)
        self._has_unsaved_changes = False
        self.update_assignments_signal.emit(
            self.current_selected_test_id, to_assign, to_unassign
        )

    def refresh_test_data(self, test_id_refreshed, updated_test_object):

        master_list_updated = False
        for i, test in enumerate(self.premade_tests):
            if test.get("test_id") == test_id_refreshed:
                self.premade_tests[i] = updated_test_object
                master_list_updated = True
                break

        if self.current_selected_test_id == test_id_refreshed:
            self.current_selected_test_object = updated_test_object
            self.test_name_label.setText(
                f"Название: {updated_test_object.get('test_name', 'N/A')}"
            )
            self.test_creator_label.setText(
                f"Создатель: {updated_test_object.get('creator_username', 'N/A')}"
            )
            self.expanded_question_index_in_test = -1
            self.populate_test_questions_list_widget()
            self.populate_all_students_checklist(
                updated_test_object.get("assigned_students", [])
            )

        current_scroll_pos = self.tests_list_widget.verticalScrollBar().value()
        self.populate_tests_list(list(self.premade_tests))
        self.tests_list_widget.verticalScrollBar().setValue(current_scroll_pos)

        item_to_select_in_main_list = None
        for i in range(self.tests_list_widget.count()):
            item = self.tests_list_widget.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data and item_data.get("test_id") == test_id_refreshed:
                item_to_select_in_main_list = item
                break

        if item_to_select_in_main_list:

            self.tests_list_widget.blockSignals(True)
            self.tests_list_widget.setCurrentItem(item_to_select_in_main_list)
            self.tests_list_widget.blockSignals(False)
        else:

            if self.current_selected_test_id == test_id_refreshed:
                self.clear_details_and_assignments()

        if self.tests_list_widget.count() == 0:
            self.clear_details_and_assignments()

    def clear_details_and_assignments(self):
        self.test_name_label.setText("Название: N/A")
        self.test_creator_label.setText("Создатель: N/A")
        self.test_grading_label.setText("Режим оценки: N/A")
        self.test_questions_list_widget.clear()
        self.all_students_checklist_widget.clear()
        self.all_students_checklist_widget.addItem(
            "(Выберите тест для просмотра/изменения назначений)"
        )
        self.save_assignments_button.setEnabled(False)
        self.delete_test_button.setEnabled(False)
        self.edit_test_criteria_button.setEnabled(False)
        self.show_statistics_button.setEnabled(False)
        self.add_questions_button.setEnabled(False)
        self.clone_test_button.setEnabled(False)
        self.rename_test_button.setEnabled(False)
        self.edit_test_settings_button.setEnabled(False)
        self.share_test_button.setEnabled(False)
        self._share_token = None
        self.share_link_widget.hide()
        self.current_selected_test_id = None
        self.current_selected_test_object = None
        self._student_checkstates = {}
        self._saved_checkstates = {}
        self._has_unsaved_changes = False

    def show_message(self, title, message, is_error=False):
        msg_box_type = QMessageBox.Warning if is_error else QMessageBox.Information
        QMessageBox(msg_box_type, title, message, QMessageBox.Ok, self).exec_()

    def update_groups(self, all_groups, students_by_group):

        self.all_groups = all_groups
        self.students_by_group = students_by_group
        self.group_filter_combo.blockSignals(True)
        current_group = self.group_filter_combo.currentText()
        self.group_filter_combo.clear()
        self.group_filter_combo.addItem("-- Все группы --")
        self.group_filter_combo.addItems(self.all_groups)
        idx = self.group_filter_combo.findText(current_group)
        if idx >= 0:
            self.group_filter_combo.setCurrentIndex(idx)
        self.group_filter_combo.blockSignals(False)

    def _on_group_filter_changed(self, group_text):
        has_group = group_text and group_text != "-- Все группы --"
        self.assign_group_button.setEnabled(
            has_group and bool(self.current_selected_test_id)
        )

        self._sync_checkstates_from_widget()
        self._render_student_list()

    def _on_assign_group_clicked(self):
        group_text = self.group_filter_combo.currentText()
        if not group_text or group_text == "-- Все группы --":
            return
        group_students = self.students_by_group.get(group_text, [])
        if not group_students:
            self.show_message(
                "Информация", f"В группе '{group_text}' нет студентов.", False
            )
            return

        self._sync_checkstates_from_widget()

        all_checked = all(
            self._student_checkstates.get(u, False)
            for u in group_students
            if u in self._student_checkstates
        ) and any(u in self._student_checkstates for u in group_students)
        new_state = not all_checked
        for username in group_students:
            if username in self._student_checkstates:
                self._student_checkstates[username] = new_state
        self._has_unsaved_changes = self._student_checkstates != self._saved_checkstates
        self._render_student_list()

    def _on_edit_test_criteria_clicked(self):
        if self.current_selected_test_id:
            self.edit_test_criteria_signal.emit(self.current_selected_test_id)

    def _on_add_questions_clicked(self):
        if self.current_selected_test_id:
            self.request_add_questions_signal.emit(self.current_selected_test_id)

    def _on_student_item_changed(self, item):

        self._student_checkstates[item.text()] = item.checkState() == Qt.Checked
        self._has_unsaved_changes = self._student_checkstates != self._saved_checkstates

    def _on_show_statistics_clicked(self):
        if self.current_selected_test_id and self.current_selected_test_object:
            test_name = self.current_selected_test_object.get("test_name", "")
            self.show_test_statistics_signal.emit(
                self.current_selected_test_id, test_name
            )

    def _on_clone_test_clicked(self):
        if self.current_selected_test_id:
            self.clone_test_signal.emit(self.current_selected_test_id)

    def _on_rename_test_clicked(self):
        if not self.current_selected_test_id or not self.current_selected_test_object:
            return
        current_name = self.current_selected_test_object.get("test_name", "")
        new_name, ok = QInputDialog.getText(
            self, "Переименовать тест", "Новое название теста:", text=current_name
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            self.rename_test_signal.emit(
                self.current_selected_test_id, new_name.strip()
            )

    def _on_edit_test_settings_clicked(self):
        if self.current_selected_test_id and self.current_selected_test_object:
            self.edit_test_settings_signal.emit(
                self.current_selected_test_id, self.current_selected_test_object
            )

    def _on_share_test_clicked(self):
        if not self.current_selected_test_id:
            return
        if self._share_token:

            self._on_revoke_share_clicked()
        else:
            self.share_test_signal.emit(self.current_selected_test_id)

    def _on_revoke_share_clicked(self):
        if self.current_selected_test_id and self._share_token:
            self.unshare_test_signal.emit(self.current_selected_test_id)

    def _on_copy_share_link(self):
        url = self._get_share_url()
        if url:
            clipboard = QApplication.clipboard()
            clipboard.setText(url)
            QMessageBox.information(
                self, "Скопировано", "Ссылка скопирована в буфер обмена."
            )

    def _get_share_url(self):
        if not self._share_token:
            return ""
        return f"https://expert-system-431h.onrender.com/#/join/{self._share_token}"

    def _update_share_link_display(self):
        if self._share_token:
            url = self._get_share_url()
            self.share_link_label.setText(f"Ссылка для приглашения:\n{url}")
            self.share_link_widget.show()
            self.share_test_button.setText("Отозвать ссылку")
            self.share_test_button.setObjectName("dangerButton")
            self.share_test_button.style().unpolish(self.share_test_button)
            self.share_test_button.style().polish(self.share_test_button)
        else:
            self.share_link_widget.hide()
            self.share_test_button.setText("Поделиться тестом")
            self.share_test_button.setObjectName("")
            self.share_test_button.style().unpolish(self.share_test_button)
            self.share_test_button.style().polish(self.share_test_button)

    def set_share_token(self, token):

        self._share_token = token
        self._update_share_link_display()

        if self.current_selected_test_object:
            if token:
                self.current_selected_test_object["share_token"] = token
            else:
                self.current_selected_test_object.pop("share_token", None)

    def on_delete_test_clicked(self):
        if not self.current_selected_test_id or not self.current_selected_test_object:
            self.show_message("Ошибка", "Тест не выбран для удаления.", True)
            return

        test_name_to_delete = self.current_selected_test_object.get(
            "test_name", "Без имени"
        )
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить тест '{test_name_to_delete}'?\nЭто действие нельзя отменить.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.delete_test_signal.emit(self.current_selected_test_id)


class GenerateTopicScoreTestDialog(QDialog):
    generate_test_requested_signal = pyqtSignal(str, int)

    def __init__(self, topics_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сформировать тест по теме и баллам")
        self.setMinimumWidth(450)
        self.topics = topics_list if topics_list else []
        self.init_ui()
        _restore_window_geometry(self, "GenerateTopicScoreTestDialog")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title_label = QLabel("Параметры для формирования теста")
        font = title_label.font()
        font.setPointSize(14)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        topic_layout = QHBoxLayout()
        topic_layout.addWidget(QLabel("Выберите тему:"))
        self.topic_combo = QComboBox()
        if self.topics:
            self.topic_combo.addItems(self.topics)
        else:
            self.topic_combo.addItem("Нет доступных тем")
            self.topic_combo.setEnabled(False)
        topic_layout.addWidget(self.topic_combo)
        layout.addLayout(topic_layout)

        score_layout = QHBoxLayout()
        score_layout.addWidget(QLabel("Максимальное количество баллов за тест:"))
        self.max_score_spinbox = QtWidgets.QSpinBox()
        self.max_score_spinbox.setMinimum(1)
        self.max_score_spinbox.setMaximum(500)
        self.max_score_spinbox.setValue(20)
        score_layout.addWidget(self.max_score_spinbox)
        layout.addLayout(score_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Сформировать")
        button_box.accepted.connect(self.on_generate_test)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        if not self.topics:
            button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def on_generate_test(self):
        selected_topic = self.topic_combo.currentText()
        max_score = self.max_score_spinbox.value()

        if selected_topic == "Нет доступных тем" or not selected_topic:
            self.show_message(
                "Ошибка", "Пожалуйста, выберите действительную тему.", is_error=True
            )
            return

        self.generate_test_requested_signal.emit(selected_topic, max_score)

    def show_message(self, title, message, is_error=False):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Warning if is_error else QMessageBox.Information)
        msg_box.exec_()

    def done(self, result):
        _save_window_geometry(self, "GenerateTopicScoreTestDialog")
        super().done(result)


class DisplayGeneratedTestDialog(QDialog):
    save_generated_test_as_premade_signal = pyqtSignal(str, list)

    def __init__(
        self,
        generated_questions_list,
        topic,
        max_score_requested,
        actual_score,
        message,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Сгенерированный тест по теме: {topic}")
        self.setMinimumSize(950, 750)
        _restore_window_geometry(self, "DisplayGeneratedTestDialog")

        self.questions = generated_questions_list
        self.topic = topic
        self.max_score_requested = max_score_requested
        self.actual_score = actual_score
        self.generation_message = message

        self.init_ui()

    def done(self, result):
        _save_window_geometry(self, "DisplayGeneratedTestDialog")
        super().done(result)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info_label = QLabel(
            f"<b>Тема:</b> {self.topic}<br>"
            f"<b>Запрошено баллов:</b> {self.max_score_requested}<br>"
            f"<b>Фактически баллов в тесте:</b> {self.actual_score}<br><hr>"
            f"<i>{self.generation_message}</i>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        if not self.questions:
            no_questions_label = QLabel("Вопросы не были сгенерированы.")
            no_questions_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_questions_label)
        else:
            questions_area = QScrollArea()
            questions_area.setWidgetResizable(True)
            questions_container = QWidget()
            questions_layout = QVBoxLayout(questions_container)

            for i, q_data in enumerate(self.questions):
                q_text = q_data.get("question", "Текст вопроса отсутствует")
                q_options = q_data.get("options", [])
                q_correct = q_data.get("correct", "N/A")
                q_points = q_data.get("points", "N/A")
                q_answer_type = q_data.get("answer_type", "single")

                correct_answer_display = str(q_correct)
                if isinstance(q_correct, list):
                    correct_answer_display = ", ".join(q_correct)

                question_details = (
                    f"<b>{i+1}. ({q_points} балл(ов)) {q_text}</b><br>"
                    f"   Тип: {'Множественный выбор' if q_answer_type == 'multiple' else 'Одиночный выбор'}<br>"
                    f"   <u>Варианты:</u> {', '.join(q_options)}<br>"
                    f"   <u>Верный ответ:</u> {correct_answer_display}"
                )
                q_label = QLabel(question_details)
                q_label.setWordWrap(True)
                q_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                questions_layout.addWidget(q_label)
                if i < len(self.questions) - 1:
                    separator = QtWidgets.QFrame()
                    separator.setFrameShape(QtWidgets.QFrame.HLine)
                    separator.setFrameShadow(QtWidgets.QFrame.Sunken)
                    questions_layout.addWidget(separator)

            questions_layout.addStretch(1)
            questions_container.setLayout(questions_layout)
            questions_area.setWidget(questions_container)
            layout.addWidget(questions_area)

        save_group = QtWidgets.QGroupBox("Сохранить этот тест как готовый")
        save_layout = QVBoxLayout(save_group)

        name_input_layout = QHBoxLayout()
        name_input_layout.addWidget(QLabel("Название для нового готового теста:"))
        self.premade_test_name_input = QLineEdit()
        _default_name = (
            f"Готовый тест по теме '{self.topic}' ({self.actual_score} баллов)"
        )
        self.premade_test_name_input.setPlaceholderText(_default_name)
        self.premade_test_name_input.setText(_default_name)
        name_input_layout.addWidget(self.premade_test_name_input)
        save_layout.addLayout(name_input_layout)

        self.save_as_premade_button = QPushButton("Сохранить как готовый тест")
        self.save_as_premade_button.setFont(QtGui.QFont("Arial", 11, QtGui.QFont.Bold))
        self.save_as_premade_button.clicked.connect(self.on_save_as_premade_clicked)
        save_layout.addWidget(self.save_as_premade_button)

        save_group.setEnabled(bool(self.questions))
        layout.addWidget(save_group)

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

    def on_save_as_premade_clicked(self):
        premade_test_name = self.premade_test_name_input.text().strip()
        if not premade_test_name:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Пожалуйста, введите название для сохраняемого готового теста.",
            )
            return

        if not self.questions:
            QMessageBox.warning(self, "Ошибка", "Нет вопросов для сохранения в тесте.")
            return

        self.save_generated_test_as_premade_signal.emit(
            premade_test_name, self.questions
        )


class EditGradingCriteriaDialog(QDialog):
    save_criteria_signal = pyqtSignal(list)
    reset_criteria_signal = pyqtSignal()

    def __init__(self, current_criteria_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование критериев оценки (по темам)")
        self.setMinimumSize(750, 500)
        self.criteria_data = [dict(c) for c in current_criteria_list]
        self.original_criteria_on_open = [dict(c) for c in current_criteria_list]
        self.init_ui()
        self.populate_table()
        _restore_window_geometry(self, "EditGradingCriteriaDialog")

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(
            ["Порог (%)", "Описание статуса", "Проходной статус"]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.resizeSection(2, 150)

        layout.addWidget(self.table)

        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Добавить критерий")
        self.add_button.clicked.connect(self.on_add_criterion)
        buttons_layout.addWidget(self.add_button)

        self.delete_button = QPushButton("Удалить выбранный")
        self.delete_button.clicked.connect(self.on_delete_criterion)
        buttons_layout.addWidget(self.delete_button)
        layout.addLayout(buttons_layout)

        action_buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить изменения")
        self.save_button.clicked.connect(self.on_save_changes)
        action_buttons_layout.addWidget(self.save_button)

        self.reset_button = QPushButton("Сбросить по умолчанию")
        self.reset_button.clicked.connect(self.on_reset_defaults)
        action_buttons_layout.addWidget(self.reset_button)
        layout.addLayout(action_buttons_layout)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button, alignment=Qt.AlignRight)

    def populate_table(self):

        self.criteria_data.sort(
            key=lambda x: float(x.get("threshold_gte", 0)), reverse=True
        )
        self.table.setRowCount(len(self.criteria_data))

        for row, item in enumerate(self.criteria_data):
            threshold_item = QTableWidgetItem(str(item.get("threshold_gte", "0")))
            self.table.setItem(row, 0, threshold_item)

            description_item = QTableWidgetItem(item.get("description", ""))
            self.table.setItem(row, 1, description_item)

            pass_status_checkbox = QCheckBox()
            pass_status_checkbox.setChecked(item.get("is_pass_status", False))
            pass_status_checkbox.setStyleSheet("margin-left: 50%; margin-right: 50%;")
            self.table.setCellWidget(row, 2, pass_status_checkbox)
        self.table.resizeRowsToContents()

    def on_add_criterion(self):
        new_row_idx = self.table.rowCount()
        self.table.insertRow(new_row_idx)

        self.table.setItem(new_row_idx, 0, QTableWidgetItem("0"))
        self.table.setItem(new_row_idx, 1, QTableWidgetItem("Новый статус"))

        checkbox = QCheckBox()
        checkbox.setChecked(False)
        checkbox.setStyleSheet("margin-left: 50%; margin-right: 50%;")
        self.table.setCellWidget(new_row_idx, 2, checkbox)
        self.table.scrollToBottom()

    def on_delete_criterion(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
        else:
            QMessageBox.warning(self, "Ошибка", "Выберите критерий для удаления.")

    def on_save_changes(self):
        new_criteria = []
        for row in range(self.table.rowCount()):
            try:
                threshold_str = self.table.item(row, 0).text()
                threshold = float(threshold_str)
                if not (0 <= threshold <= 100):
                    QMessageBox.warning(
                        self,
                        "Ошибка валидации",
                        f"Порог в строке {row + 1} должен быть числом от 0 до 100.",
                    )
                    return
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Ошибка валидации",
                    f"Порог в строке {row + 1} должен быть числом.",
                )
                return
            except AttributeError:
                QMessageBox.warning(
                    self,
                    "Ошибка валидации",
                    f"Порог в строке {row + 1} не может быть пустым.",
                )
                return

            description_item = self.table.item(row, 1)
            description = description_item.text().strip() if description_item else ""
            if not description:
                QMessageBox.warning(
                    self,
                    "Ошибка валидации",
                    f"Описание статуса в строке {row + 1} не может быть пустым.",
                )
                return

            pass_status_checkbox = self.table.cellWidget(row, 2)
            is_pass = (
                pass_status_checkbox.isChecked()
                if isinstance(pass_status_checkbox, QCheckBox)
                else False
            )

            new_criteria.append(
                {
                    "threshold_gte": threshold,
                    "description": description,
                    "is_pass_status": is_pass,
                }
            )

        if not new_criteria:
            QMessageBox.warning(
                self, "Ошибка", "Должен быть определен хотя бы один критерий оценки."
            )
            return

        thresholds = [c["threshold_gte"] for c in new_criteria]
        if len(thresholds) != len(set(thresholds)):
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Обнаружены дублирующиеся значения порогов. Рекомендуется использовать уникальные пороги.",
            )

        new_criteria.sort(key=lambda x: x["threshold_gte"], reverse=True)
        self.save_criteria_signal.emit(new_criteria)

    def on_reset_defaults(self):

        self.reset_criteria_signal.emit()

    def load_criteria(self, new_criteria_list):

        self.criteria_data = [dict(c) for c in new_criteria_list]
        self.populate_table()

    def show_message(self, title, message, is_error=False):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Warning if is_error else QMessageBox.Information)
        msg_box.exec_()

    def done(self, result):
        _save_window_geometry(self, "EditGradingCriteriaDialog")
        super().done(result)


class StudentTestHistoryDialog(QDialog):
    def __init__(self, student_username, history_data_list, parent=None):
        super().__init__(parent)
        self.student_username = student_username
        self.history_data = history_data_list
        self.setWindowTitle(f"История тестов для: {self.student_username}")
        self.setGeometry(150, 150, 1050, 680)
        self.init_ui()
        self.display_history()
        _restore_window_geometry(self, "StudentTestHistoryDialog")

    def closeEvent(self, event):
        _save_column_widths(self.history_table, "StudentTestHistoryDialog_cols")
        _save_window_geometry(self, "StudentTestHistoryDialog")
        super().closeEvent(event)

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel(f"История прохождения тестов - {self.student_username}")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.history_table = QTableWidget(self)
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            [
                "Дата начала",
                "Название теста",
                "Попытка №",
                "Продолжительность",
                "Итоговый результат",
            ]
        )
        self.history_table.setSortingEnabled(True)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.horizontalHeader().setMinimumSectionSize(80)
        self.history_table.setColumnWidth(0, 200)
        self.history_table.setColumnWidth(1, 320)
        self.history_table.setColumnWidth(2, 100)
        self.history_table.setColumnWidth(3, 160)
        _restore_column_widths(self.history_table, "StudentTestHistoryDialog_cols")
        self.history_table.setFont(QtGui.QFont("Arial", 10))
        layout.addWidget(self.history_table)

        close_button = QPushButton("Закрыть", self)
        close_button.setFont(QtGui.QFont("Arial", 12))
        close_button.setMinimumHeight(40)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def display_history(self):
        if not self.history_data:
            self.history_table.setRowCount(1)
            self.history_table.setItem(0, 0, QTableWidgetItem("Нет пройденных тестов."))
            self.history_table.setSpan(0, 0, 1, self.history_table.columnCount())
            return

        self.history_table.setRowCount(len(self.history_data))
        for i, result in enumerate(self.history_data):
            self.history_table.setItem(
                i, 0, QTableWidgetItem(result.get("start_time", "N/A"))
            )
            self.history_table.setItem(
                i, 1, QTableWidgetItem(result.get("test_name", "N/A"))
            )
            self.history_table.setItem(
                i, 2, QTableWidgetItem(str(result.get("attempt_number", "N/A")))
            )
            self.history_table.setItem(
                i, 3, QTableWidgetItem(result.get("duration", "N/A"))
            )
            self.history_table.setItem(
                i, 4, QTableWidgetItem(result.get("final_status", "N/A"))
            )

    def show_message(self, title, message, is_error=True):
        if is_error:
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)


class ManageUserRolesDialog(QDialog):
    save_roles_signal = pyqtSignal(dict)
    save_user_changes_signal = pyqtSignal(dict, dict)
    delete_user_signal = pyqtSignal(str)
    change_password_signal = pyqtSignal(str, str)
    edit_full_name_signal = pyqtSignal(str, str)

    def __init__(
        self, all_users_data, current_admin_username, all_groups=None, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Управление ролями пользователей")
        self.all_users_data = all_users_data
        self.current_admin_username = current_admin_username
        self.all_groups = sorted(all_groups or [])
        self.setMinimumSize(1050, 560)
        _restore_window_geometry(self, "ManageUserRolesDialog")

        self.changed_roles_map = {}
        self.changed_groups_map = {}

        self.role_options = [
            ("Студент", ROLE_STUDENT),
            ("Учитель", ROLE_TEACHER),
            ("Не назначена", ROLE_UNASSIGNED),
        ]

        layout = QVBoxLayout(self)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(8)
        self.table_widget.setHorizontalHeaderLabels(
            [
                "Пользователь",
                "ФИО",
                "Текущая группа",
                "Назначить группу",
                "Текущая роль",
                "Назначить роль",
                "Сброс пароль",
                "Удалить",
            ]
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeToContents
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeToContents
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeToContents
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            7, QHeaderView.ResizeToContents
        )
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)

        self.populate_table()
        layout.addWidget(self.table_widget)

        self.button_box = QDialogButtonBox()
        self.save_button = self.button_box.addButton(
            "Сохранить изменения", QDialogButtonBox.AcceptRole
        )
        self.cancel_button = self.button_box.addButton(
            "Отмена", QDialogButtonBox.RejectRole
        )

        self.save_button.clicked.connect(self.emit_save_signal_and_accept)
        self.cancel_button.clicked.connect(self.reject)

        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def populate_table(self):
        self.table_widget.setRowCount(0)

        sorted_usernames = sorted(
            self.all_users_data.keys(),
            key=lambda u: (self.all_users_data[u].get("role") != ROLE_ADMIN, u.lower()),
        )

        for row, username in enumerate(sorted_usernames):
            user_details = self.all_users_data[username]
            current_role_value = user_details.get("role", ROLE_UNASSIGNED)
            group_value = user_details.get("group", "")

            display_role = "Неизвестно"
            if current_role_value == ROLE_ADMIN:
                display_role = "Администратор"
            elif current_role_value == ROLE_TEACHER:
                display_role = "Учитель"
            elif current_role_value == ROLE_STUDENT:
                display_role = "Студент"
            elif current_role_value == ROLE_UNASSIGNED:
                display_role = "Не назначена"

            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(username))

            full_name = user_details.get("full_name", "")
            fn_widget = QWidget()
            fn_layout = QHBoxLayout(fn_widget)
            fn_layout.setContentsMargins(2, 2, 2, 2)
            fn_layout.setSpacing(4)
            fn_label = QLabel(full_name or "—")
            fn_edit_btn = QPushButton("...")
            fn_edit_btn.setFixedSize(24, 24)
            fn_edit_btn.setToolTip("Изменить ФИО")
            fn_edit_btn.clicked.connect(
                lambda checked, u=username, fn=full_name: self.edit_full_name_signal.emit(
                    u, fn or ""
                )
            )
            fn_layout.addWidget(fn_label)
            fn_layout.addWidget(fn_edit_btn)
            fn_layout.addStretch()
            self.table_widget.setCellWidget(row, 1, fn_widget)

            self.table_widget.setItem(row, 2, QTableWidgetItem(group_value))

            group_combo = QComboBox()
            group_combo.addItem("— Без группы —", "")
            for group_name in self.all_groups:
                group_combo.addItem(group_name, group_name)
            group_index = group_combo.findData(group_value)
            if group_index >= 0:
                group_combo.setCurrentIndex(group_index)
            else:
                group_combo.insertItem(1, group_value, group_value)
                group_combo.setCurrentIndex(1)
            group_combo.activated.connect(
                lambda index, u=username, cb=group_combo: self.group_changed(
                    u, cb.itemData(index) or ""
                )
            )
            self.table_widget.setCellWidget(row, 3, group_combo)

            self.table_widget.setItem(row, 4, QTableWidgetItem(display_role))

            combo_box = QComboBox()
            is_user_admin = current_role_value == ROLE_ADMIN

            if is_user_admin:
                combo_box.addItem(display_role)
                combo_box.setEnabled(False)
            else:

                default_cb_index = -1
                for i, (text, role_val) in enumerate(self.role_options):
                    combo_box.addItem(text, userData=role_val)
                    if role_val == current_role_value:
                        default_cb_index = i

                if default_cb_index != -1:
                    combo_box.setCurrentIndex(default_cb_index)
                else:
                    combo_box.insertItem(0, f"Текущий: {display_role}")
                    combo_box.setCurrentIndex(0)

                combo_box.activated.connect(
                    lambda index, u=username, cb=combo_box: self.role_changed(
                        u, cb.itemData(index)
                    )
                )

            self.table_widget.setCellWidget(row, 5, combo_box)

            pwd_btn = QPushButton("Сбросить")
            pwd_btn.setFixedHeight(28)
            pwd_btn.clicked.connect(
                lambda checked, u=username: self._on_change_password(u)
            )
            self.table_widget.setCellWidget(row, 6, pwd_btn)

            if is_user_admin:
                del_placeholder = QLabel("")
                self.table_widget.setCellWidget(row, 7, del_placeholder)
            else:
                del_btn = QPushButton("Удалить")
                del_btn.setFixedHeight(28)
                del_btn.setObjectName("dangerButton")
                del_btn.clicked.connect(
                    lambda checked, u=username: self._on_delete_user(u)
                )
                self.table_widget.setCellWidget(row, 7, del_btn)

    def _on_delete_user(self, username):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить пользователя «{username}»? Это действие необратимо.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.delete_user_signal.emit(username)

    def _on_change_password(self, username):
        new_pwd, ok = QInputDialog.getText(
            self,
            "Сброс пароля",
            f"Новый пароль для {username} (мин. 6 символов):",
            QLineEdit.Password,
        )
        if not ok or not new_pwd:
            return
        if len(new_pwd) < 6:
            QMessageBox.warning(
                self, "Ошибка", "Новый пароль должен быть не менее 6 символов."
            )
            return
        self.change_password_signal.emit(username, new_pwd)

    def role_changed(self, username, new_role_value):

        original_role = self.all_users_data[username].get("role", ROLE_UNASSIGNED)

        if new_role_value is not None:
            if new_role_value != original_role:
                self.changed_roles_map[username] = new_role_value
                print(f"User {username} role change staged to: {new_role_value}")
            elif username in self.changed_roles_map:
                del self.changed_roles_map[username]
                print(f"User {username} role change reverted to original.")
        else:
            print(
                f"Warning: role_changed called for {username} with None new_role_value"
            )

    def group_changed(self, username, new_group_value):
        original_group = self.all_users_data[username].get("group", "")
        new_group_value = new_group_value or ""
        if new_group_value != original_group:
            self.changed_groups_map[username] = new_group_value
            print(f"User {username} group change staged to: {new_group_value}")
        elif username in self.changed_groups_map:
            del self.changed_groups_map[username]
            print(f"User {username} group change reverted to original.")

    def emit_save_signal_and_accept(self):
        print(
            f"Saving roles: {self.changed_roles_map}, groups: {self.changed_groups_map}"
        )
        self.save_user_changes_signal.emit(
            self.changed_roles_map, self.changed_groups_map
        )
        self.save_roles_signal.emit(self.changed_roles_map)
        self.accept()

    def refresh_users(self, all_users_data, all_groups=None):

        self.all_users_data = all_users_data
        if all_groups is not None:
            self.all_groups = sorted(all_groups or [])
        self.changed_roles_map = {}
        self.changed_groups_map = {}
        self.populate_table()

    def done(self, result):
        _save_window_geometry(self, "ManageUserRolesDialog")
        super().done(result)


class ManagePremadeTestsDialog(QDialog):

    def __init__(
        self,
        premade_tests_list,
        all_students,
        all_groups=None,
        students_by_group=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Управление готовыми тестами и назначениями")
        self.panel = ManageTestsPanel(
            premade_tests_list, all_students, all_groups, students_by_group, self
        )
        lay = QVBoxLayout(self)
        lay.addWidget(self.panel)
        btn = QPushButton("Закрыть")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn, alignment=Qt.AlignRight)
        _restore_window_geometry(self, "ManagePremadeTestsDialog")

    def done(self, result):
        _save_window_geometry(self, "ManagePremadeTestsDialog")
        super().done(result)

    def __getattr__(self, name):

        try:
            return getattr(self.panel, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


class HistoryWidget(QWidget):

    load_user_history_signal = pyqtSignal(str)
    load_group_history_signal = pyqtSignal(str)
    show_details_signal = pyqtSignal(dict)
    clear_history_signal = pyqtSignal(str, str)

    def __init__(self, all_usernames: list, all_groups: list, parent=None):
        super().__init__(parent)
        self._student_list = sorted(all_usernames)
        self._group_list = sorted(all_groups)
        self._all_history_data = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Поиск по:"))
        self._mode_group = QButtonGroup(self)
        self._student_radio = QRadioButton("студент")
        self._group_radio = QRadioButton("группа")
        self._student_radio.setChecked(True)
        self._mode_group.addButton(self._student_radio, 0)
        self._mode_group.addButton(self._group_radio, 1)
        mode_row.addWidget(self._student_radio)
        mode_row.addWidget(self._group_radio)
        mode_row.addStretch()
        layout.addLayout(mode_row)
        self._mode_group.buttonClicked.connect(self._on_mode_changed)

        search_row = QHBoxLayout()
        self._search_label = QLabel("Студент:")
        self._search_label.setMinimumWidth(60)
        search_row.addWidget(self._search_label)

        self._search_combo = QComboBox()
        self._search_combo.setEditable(True)
        self._search_combo.setInsertPolicy(QComboBox.NoInsert)
        self._search_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._search_combo.setMinimumWidth(280)
        self._rebuild_completer()

        self._search_combo.activated.connect(self._on_combo_activated)
        self._search_combo.lineEdit().returnPressed.connect(self._on_load_clicked)
        search_row.addWidget(self._search_combo)

        load_btn = QPushButton("Загрузить")
        load_btn.setFixedWidth(100)
        load_btn.clicked.connect(self._on_load_clicked)
        search_row.addWidget(load_btn)

        reset_btn = QPushButton("Сброс")
        reset_btn.setFixedWidth(80)
        reset_btn.clicked.connect(self._on_reset)
        search_row.addWidget(reset_btn)
        layout.addLayout(search_row)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Фильтр по тексту:"))
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText(
            "Введите любое слово для фильтрации строк таблицы…"
        )
        self._filter_input.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter_input)
        layout.addLayout(filter_row)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["Студент", "Тест", "Попытка", "Дата", "Длительность", "% верных", "Статус"]
        )
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setMinimumSectionSize(60)
        self._table.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self._table)

        clear_group = QGroupBox("Очистка истории")
        clear_layout = QVBoxLayout(clear_group)
        clear_mode_row = QHBoxLayout()
        clear_mode_row.addWidget(QLabel("Очистить по:"))
        self._clear_mode_group = QButtonGroup(self)
        self._clear_student_radio = QRadioButton("студенту")
        self._clear_test_radio = QRadioButton("тесту")
        self._clear_student_radio.setChecked(True)
        self._clear_mode_group.addButton(self._clear_student_radio, 0)
        self._clear_mode_group.addButton(self._clear_test_radio, 1)
        clear_mode_row.addWidget(self._clear_student_radio)
        clear_mode_row.addWidget(self._clear_test_radio)
        clear_mode_row.addStretch()
        clear_layout.addLayout(clear_mode_row)
        clear_input_row = QHBoxLayout()
        self._clear_input = QLineEdit()
        self._clear_input.setPlaceholderText(
            "Введите имя студента или название теста..."
        )
        clear_input_row.addWidget(self._clear_input)
        clear_btn = QPushButton("Очистить")
        clear_btn.setFixedWidth(100)
        clear_btn.clicked.connect(self._on_clear_history_clicked)
        clear_input_row.addWidget(clear_btn)
        clear_layout.addLayout(clear_input_row)
        layout.addWidget(clear_group)

        self._status_lbl = QLabel("Выберите студента или группу и нажмите «Загрузить».")
        self._status_lbl.setObjectName("statusLabel")
        layout.addWidget(self._status_lbl)

    def update_lists(self, all_usernames: list, all_groups: list):

        self._student_list = sorted(all_usernames)
        self._group_list = sorted(all_groups)
        self._rebuild_completer()

    def display_history(self, data: list):

        self._all_history_data = data
        self._apply_filter()
        self._status_lbl.setText(f"Загружено записей: {len(data)}")

    def _rebuild_completer(self):
        is_student = (
            self._student_radio.isChecked() if hasattr(self, "_student_radio") else True
        )
        options = self._student_list if is_student else self._group_list
        self._search_combo.blockSignals(True)
        self._search_combo.clear()
        self._search_combo.addItems(options)
        self._search_combo.lineEdit().clear()
        comp = QCompleter(options, self)
        comp.setFilterMode(Qt.MatchContains)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setCompletionMode(QCompleter.PopupCompletion)

        comp.activated[str].connect(self._on_load_with_text)
        self._search_combo.setCompleter(comp)
        self._search_combo.blockSignals(False)
        placeholder = (
            "Начните вводить имя студента…"
            if is_student
            else "Начните вводить название группы…"
        )
        self._search_combo.lineEdit().setPlaceholderText(placeholder)

    def _on_mode_changed(self, _btn):
        is_student = self._student_radio.isChecked()
        self._search_label.setText("Студент:" if is_student else "Группа:")
        self._rebuild_completer()

        self._all_history_data = []
        self._table.setRowCount(0)
        self._status_lbl.setText("Выберите студента или группу и нажмите «Загрузить».")

    def _on_combo_activated(self, _index):
        self._on_load_clicked()

    def _on_load_with_text(self, text: str):

        self._search_combo.lineEdit().setText(text)
        self._on_load_clicked()

    def _on_load_clicked(self):
        selected = self._search_combo.currentText().strip()
        if not selected:
            return
        if self._student_radio.isChecked():
            self.load_user_history_signal.emit(selected)
        else:
            self.load_group_history_signal.emit(selected)

    def _on_reset(self):
        self._search_combo.lineEdit().clear()
        self._filter_input.clear()
        self._all_history_data = []
        self._table.setRowCount(0)
        self._status_lbl.setText("Выберите студента или группу и нажмите «Загрузить».")

    def _apply_filter(self):
        text = self._filter_input.text().lower().strip()
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for record in self._all_history_data:
            row_vals = [
                record.get("username", ""),
                record.get("test_name", ""),
                str(record.get("attempt_number", "")),
                record.get("start_time", ""),
                record.get("duration", ""),
                str(record.get("score_percentage", "")),
                record.get("final_status", ""),
            ]
            if text and not any(text in v.lower() for v in row_vals):
                continue
            row = self._table.rowCount()
            self._table.insertRow(row)
            for col, val in enumerate(row_vals):
                item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, record)

                if col == 5:
                    try:
                        item.setData(Qt.DisplayRole, float(val) if val else 0.0)
                    except ValueError:
                        pass
                self._table.setItem(row, col, item)
        self._table.setSortingEnabled(True)

    def _on_row_double_clicked(self, index):
        item = self._table.item(index.row(), 0)
        if item:
            record = item.data(Qt.UserRole)
            if record:
                self.show_details_signal.emit(record)

    def _on_clear_history_clicked(self):
        target = self._clear_input.text().strip()
        if not target:
            return
        mode = "student" if self._clear_student_radio.isChecked() else "test"
        self.clear_history_signal.emit(mode, target)


class TestManagementDialog(QDialog):

    def __init__(
        self,
        premade_tests,
        all_students,
        all_groups,
        students_by_group,
        all_usernames_for_history,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Управление тестами")
        self.setGeometry(80, 80, 1450, 950)

        main_lay = QVBoxLayout(self)

        tabs = QTabWidget()

        self.history_widget = HistoryWidget(all_usernames_for_history, all_groups, self)
        tabs.addTab(self.history_widget, "История тестов")

        self.manage_panel = ManageTestsPanel(
            premade_tests, all_students, all_groups, students_by_group, self
        )
        tabs.addTab(self.manage_panel, "Назначение и управление")

        main_lay.addWidget(tabs)

        close_btn = QPushButton("Закрыть")
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.accept)
        main_lay.addWidget(close_btn, alignment=Qt.AlignRight)

        _restore_window_geometry(self, "TestManagementDialog")

    def done(self, result):

        if self.manage_panel._has_unsaved_changes:
            _msg = QMessageBox(self)
            _msg.setWindowTitle("Несохранённые изменения")
            _msg.setText("Назначения не были сохранены. Закрыть без сохранения?")
            _save_btn = _msg.addButton("Сохранить", QMessageBox.AcceptRole)
            _msg.addButton("Не сохранять", QMessageBox.DestructiveRole)
            _cancel_btn = _msg.addButton("Отмена", QMessageBox.RejectRole)
            _msg.setDefaultButton(_save_btn)
            _msg.exec_()
            _clicked = _msg.clickedButton()
            if _clicked == _save_btn:
                self.manage_panel.on_save_assignments_clicked_correct_logic()
            elif _clicked == _cancel_btn:
                return

        _save_window_geometry(self, "TestManagementDialog")
        super().done(result)


class SelectQuestionsDialog(QDialog):

    questions_selected_signal = pyqtSignal(list)

    def __init__(self, all_questions_data: dict, existing_questions: list, parent=None):

        super().__init__(parent)
        self.setWindowTitle("Добавить вопросы в тест")
        self.setGeometry(120, 120, 1000, 720)
        _restore_window_geometry(self, "SelectQuestionsDialog")

        self._all_topics_data = all_questions_data
        self._existing_q_texts = {q.get("question", "") for q in existing_questions}
        self._filtered_items = []
        self.init_ui()
        self._populate_topics()
        self._refresh_list()

    def done(self, result):
        _save_window_geometry(self, "SelectQuestionsDialog")
        super().done(result)

    def init_ui(self):
        lay = QVBoxLayout(self)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Тема:"))
        self._topic_combo = QComboBox()
        self._topic_combo.currentTextChanged.connect(self._refresh_list)
        top_row.addWidget(self._topic_combo)
        top_row.addWidget(QLabel("Поиск:"))
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Введите текст для фильтрации вопросов…")
        self._search_input.textChanged.connect(self._refresh_list)
        top_row.addWidget(self._search_input)
        lay.addLayout(top_row)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.MultiSelection)
        lay.addWidget(self._list)

        self._info_lbl = QLabel("")
        self._info_lbl.setObjectName("statusLabel")
        lay.addWidget(self._info_lbl)

        btn_row = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.clicked.connect(self._select_all)
        btn_row.addWidget(select_all_btn)
        clear_btn = QPushButton("Снять выбор")
        clear_btn.clicked.connect(self._list.clearSelection)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        ok_btn = QPushButton("Добавить выбранные")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(ok_btn)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        lay.addLayout(btn_row)

    def _populate_topics(self):
        self._topic_combo.blockSignals(True)
        self._topic_combo.clear()
        self._topic_combo.addItem("— Все темы —")
        self._topic_combo.addItems(sorted(self._all_topics_data.keys()))
        self._topic_combo.blockSignals(False)

    def _refresh_list(self):
        topic = self._topic_combo.currentText()
        search = self._search_input.text().lower().strip()

        self._filtered_items = []
        for t, qs in self._all_topics_data.items():
            if topic and topic != "— Все темы —" and t != topic:
                continue
            for q in qs:
                qtext = q.get("question", "")
                if search and search not in qtext.lower():
                    continue
                already = " [уже в тесте]" if qtext in self._existing_q_texts else ""
                display = (
                    f"[{t}] {qtext[:110]}{'...' if len(qtext) > 110 else ''}{already}"
                )
                self._filtered_items.append((display, q))

        self._list.clear()
        for display, _ in self._filtered_items:
            self._list.addItem(display)
        self._info_lbl.setText(f"Найдено вопросов: {len(self._filtered_items)}")

    def _select_all(self):
        self._list.selectAll()

    def _on_ok(self):
        selected = [
            self._filtered_items[i.row()][1] for i in self._list.selectedIndexes()
        ]
        if not selected:
            QMessageBox.warning(self, "Нет выбранных", "Выберите хотя бы один вопрос.")
            return
        self.questions_selected_signal.emit(selected)
        self.accept()


class TestStatisticsDialog(QDialog):

    export_csv_signal = pyqtSignal()

    def __init__(
        self,
        test_name: str,
        results: list,
        students_by_group: dict = None,
        aggregate_stats: dict = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(
            f"\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430: {test_name}"
        )
        self.setGeometry(150, 150, 1100, 750)
        self.test_name = test_name
        self.results = results
        self._students_by_group = students_by_group or {}
        self._aggregate_stats = aggregate_stats
        self.init_ui()
        _restore_window_geometry(self, "TestStatisticsDialog")

    def done(self, result):
        _save_column_widths(self.table, "TestStatisticsDialog_cols")
        _save_window_geometry(self, "TestStatisticsDialog")
        super().done(result)

    def init_ui(self):
        layout = QVBoxLayout(self)

        total = len(self.results)
        passed = sum(
            1
            for r in self.results
            if r.get("final_status") in ("Зачёт", "зачтено", "Passed")
        )
        self.summary_label = QLabel(
            f"Всего попыток: {total}  |  Зачтено: {passed}  |  Не зачтено: {total - passed}"
        )
        self.summary_label.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        layout.addWidget(self.summary_label)

        if self._aggregate_stats:
            s = self._aggregate_stats
            agg_label = QLabel(
                f"Уникальных студентов: {s.get('unique_students', 0)}  |  "
                f"Средний балл: {s.get('average_score', 0)}%  |  "
                f"Процент зачётов: {s.get('pass_rate', 0)}%  |  "
                f"Лучший: {s.get('best_score', 0)}%  |  "
                f"Худший: {s.get('worst_score', 0)}%"
            )
            agg_label.setObjectName("aggregateStatsLabel")
            layout.addWidget(agg_label)

            per_topic = s.get("per_topic", {})
            if per_topic:
                topic_group = QtWidgets.QGroupBox("По темам")
                topic_layout = QVBoxLayout(topic_group)
                for topic, t in per_topic.items():
                    row_layout = QHBoxLayout()
                    name_label = QLabel(topic)
                    name_label.setMinimumWidth(140)
                    name_label.setStyleSheet("font-weight: bold;")
                    row_layout.addWidget(name_label)
                    row_layout.addWidget(QLabel(f"Средний: {t.get('average', 0)}%"))
                    row_layout.addWidget(QLabel(f"Лучший: {t.get('best', 0)}%"))
                    row_layout.addWidget(QLabel(f"Худший: {t.get('worst', 0)}%"))
                    row_layout.addWidget(QLabel(f"({t.get('attempts', 0)} попыток)"))
                    row_layout.addStretch()
                    topic_layout.addLayout(row_layout)
                layout.addWidget(topic_group)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Фильтр:"))
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText(
            "Введите любое слово для фильтрации строк…"
        )
        self._filter_input.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter_input)

        filter_row.addWidget(QLabel("Группа:"))
        self._group_combo = QComboBox()
        self._group_combo.setMinimumWidth(140)
        self._group_combo.addItem("— Все группы —")
        self._group_combo.addItems(sorted(self._students_by_group.keys()))
        self._group_combo.currentTextChanged.connect(self._apply_filter)
        filter_row.addWidget(self._group_combo)
        layout.addLayout(filter_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Студент", "Дата", "Длительность", "Итог", "Статус", "Правильных"]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setMinimumSectionSize(80)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 190)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 190)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 130)
        _restore_column_widths(self.table, "TestStatisticsDialog_cols")

        self._fill_table(self.results)
        layout.addWidget(self.table)

        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Экспорт CSV")
        export_btn.clicked.connect(self.export_csv_signal.emit)
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _fill_table(self, rows):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for r in rows:
            answers = r.get("answers", [])
            correct_count = (
                sum(
                    1
                    for a in answers
                    if str(a.get("user_answer", "")).strip()
                    == str(a.get("correct_answer", "")).strip()
                )
                if answers
                else 0
            )
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r.get("username", "")))
            self.table.setItem(row, 1, QTableWidgetItem(r.get("start_time", "")))
            self.table.setItem(row, 2, QTableWidgetItem(r.get("duration", "")))
            self.table.setItem(row, 3, QTableWidgetItem(r.get("final_status", "")))
            self.table.setItem(row, 4, QTableWidgetItem(r.get("status", "")))
            correct_item = QTableWidgetItem()
            correct_item.setData(Qt.DisplayRole, correct_count)
            self.table.setItem(row, 5, correct_item)
        self.table.setSortingEnabled(True)

    def _apply_filter(self):
        text = self._filter_input.text().lower().strip()
        group = self._group_combo.currentText() if hasattr(self, "_group_combo") else ""
        group_students = (
            set(self._students_by_group.get(group, []))
            if group and group != "— Все группы —"
            else None
        )
        filtered = [
            r
            for r in self.results
            if (
                not text
                or any(
                    text in str(v).lower()
                    for v in [
                        r.get("username", ""),
                        r.get("start_time", ""),
                        r.get("duration", ""),
                        r.get("final_status", ""),
                        r.get("status", ""),
                    ]
                )
            )
            and (group_students is None or r.get("username", "") in group_students)
        ]
        self._fill_table(filtered)

        f_total = len(filtered)
        f_passed = sum(
            1
            for r in filtered
            if r.get("final_status") in ("Зачёт", "зачтено", "Passed")
        )
        self.summary_label.setText(
            f"Всего попыток: {f_total}  |  Зачтено: {f_passed}  |  Не зачтено: {f_total - f_passed}"
        )

    def _on_row_double_clicked(self, row, column):

        username = self.table.item(row, 0).text() if self.table.item(row, 0) else ""

        filtered = self._get_filtered_results()
        result = None
        for r in filtered:
            if r.get("username") == username:
                result = r
                break
        if result:
            self._show_detail_dialog(result)

    def _get_filtered_results(self):
        text = (
            self._filter_input.text().lower().strip()
            if hasattr(self, "_filter_input")
            else ""
        )
        group = self._group_combo.currentText() if hasattr(self, "_group_combo") else ""
        group_students = (
            set(self._students_by_group.get(group, []))
            if group and group != "— Все группы —"
            else None
        )
        return [
            r
            for r in self.results
            if (
                not text
                or any(
                    text in str(v).lower()
                    for v in [
                        r.get("username", ""),
                        r.get("start_time", ""),
                        r.get("duration", ""),
                        r.get("final_status", ""),
                        r.get("status", ""),
                    ]
                )
            )
            and (group_students is None or r.get("username", "") in group_students)
        ]

    def _show_detail_dialog(self, result):
        dlg = QDialog(self)
        dlg.setWindowTitle("Детали прохождения")
        dlg.setMinimumSize(700, 550)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)

        username = result.get("username", "")
        test_name = result.get("test_name", "")
        score = result.get("score_percentage", 0)
        final_status = result.get("final_status", "")
        duration = result.get("duration", "")

        header = QLabel(f"<b>{test_name}</b>")
        header.setStyleSheet("font-size: 18px;")
        layout.addWidget(header)

        info = QLabel(
            f"Студент: <b>{username}</b> | Результат: <b>{final_status}</b> ({score}%) | Длительность: <b>{duration}</b>"
        )
        info.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(info)

        category_scores = result.get("category_scores", {})
        if category_scores:
            topic_group = QtWidgets.QGroupBox("По темам")
            topic_layout = QVBoxLayout(topic_group)
            for cat, info_data in category_scores.items():
                if isinstance(info_data, dict):
                    row_layout = QHBoxLayout()
                    name_label = QLabel(cat)
                    name_label.setMinimumWidth(140)
                    name_label.setStyleSheet("font-weight: bold;")
                    row_layout.addWidget(name_label)
                    row_layout.addWidget(
                        QLabel(
                            f"{info_data.get('score', 0)}/{info_data.get('total', 0)} ({info_data.get('percentage', 0)}%)"
                        )
                    )
                    status = info_data.get("status", "")
                    status_label = QLabel(status)
                    status_label.setStyleSheet(
                        f"color: {'green' if status and status != 'незачтено' else 'red'}; font-weight: bold;"
                    )
                    row_layout.addWidget(status_label)
                    row_layout.addStretch()
                    topic_layout.addLayout(row_layout)
            layout.addWidget(topic_group)

        answers = result.get("answers", [])
        if answers:
            correct_count = sum(
                1
                for a in answers
                if str(a.get("user_answer", "")).strip().lower()
                == str(a.get("correct_answer", "")).strip().lower()
            )
            stats = QLabel(f"Ответы: {correct_count}/{len(answers)} правильных")
            stats.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
            layout.addWidget(stats)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("border: none;")

            container = QWidget()
            vlayout = QVBoxLayout(container)
            vlayout.setSpacing(6)

            for i, a in enumerate(answers):
                user_ans = a.get("user_answer", "—")
                correct_ans = a.get("correct_answer", "—")
                if isinstance(user_ans, list):
                    user_ans = ", ".join(map(str, user_ans))
                if isinstance(correct_ans, list):
                    correct_ans = ", ".join(map(str, correct_ans))

                user_norm = str(user_ans).strip().lower()
                correct_norm = str(correct_ans).strip().lower()
                is_correct = user_norm == correct_norm

                card = QFrame()
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {'#e8f5e9' if is_correct else '#ffebee'};
                        border-radius: 6px;
                        padding: 10px;
                    }}
                    QLabel {{ color: black; }}
                """)

                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(12, 8, 12, 8)

                q = QLabel(f"<b>{i+1}.</b> {a.get('question', '')[:120]}")
                q.setWordWrap(True)
                q.setStyleSheet("font-size: 13px;")
                card_layout.addWidget(q)

                if is_correct:
                    ans_text = f"Ответ: {user_ans or '—'}"
                    ans_label = QLabel(ans_text)
                    ans_label.setStyleSheet(
                        "font-weight: bold; font-size: 12px; margin-top: 4px;"
                    )
                    card_layout.addWidget(ans_label)
                else:
                    ans_text = f"Ваш ответ: {user_ans or '—'}"
                    ans_label = QLabel(ans_text)
                    ans_label.setStyleSheet("font-size: 12px; margin-top: 4px;")
                    card_layout.addWidget(ans_label)

                    correct_label = QLabel(f"Верный: {correct_ans}")
                    correct_label.setStyleSheet("font-weight: bold; font-size: 12px;")
                    card_layout.addWidget(correct_label)

                vlayout.addWidget(card)

            vlayout.addStretch()
            scroll.setWidget(container)
            layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(dlg.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dlg.exec_()
