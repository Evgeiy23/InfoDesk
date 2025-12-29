import re

from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QTextEdit, QMessageBox, QComboBox, QFormLayout, QDialog,
    QInputDialog, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer

from database import (
    get_user, list_users, create_user, delete_user_db, update_user_name,
    update_user_password, list_pending_questions, get_question_by_id,
    set_answer, add_question, list_user_questions_all
)
from rag import RequestThread


class ProfileDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Профиль — {username}")
        self.username = username
        self.user = get_user(username) or {"name": username}
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout()
        
        self.name_edit = QLineEdit(self.user.get("name", ""))
        layout.addRow("Имя:", self.name_edit)
        
        change_pass_btn = QPushButton("Сменить пароль")
        change_pass_btn.clicked.connect(self.change_password)
        layout.addRow(change_pass_btn)
        
        btns = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addRow(btns)
        
        self.setLayout(layout)
    
    def change_password(self):
        cur, ok1 = QInputDialog.getText(
            self, "Текущий пароль", "Введите текущий пароль:",
            QLineEdit.EchoMode.Password
        )
        if not ok1:
            return
        
        fresh = get_user(self.username)
        if not fresh or cur != fresh.get("password", ""):
            QMessageBox.warning(self, "Ошибка", "Текущий пароль неверен.")
            return
        
        newp, ok2 = QInputDialog.getText(
            self, "Новый пароль", "Введите новый пароль:",
            QLineEdit.EchoMode.Password
        )
        if not ok2 or not newp:
            return
        
        conf, ok3 = QInputDialog.getText(
            self, "Подтверждение", "Подтвердите пароль:",
            QLineEdit.EchoMode.Password
        )
        if not ok3 or newp != conf:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают.")
            return
        
        update_user_password(self.username, newp)
        QMessageBox.information(self, "Готово", "Пароль изменён.")
    
    def save(self):
        name = self.name_edit.text().strip() or self.username
        update_user_name(self.username, name)
        self.accept()


class AdminWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Панель администратора</b>"))
        layout.addWidget(QLabel("Список пользователей:"))
        
        self.user_list = QListWidget()
        self.refresh_user_list()
        layout.addWidget(self.user_list)
        
        form_layout = QHBoxLayout()
        self.new_username = QLineEdit()
        self.new_username.setPlaceholderText("Логин")
        self.new_name = QLineEdit()
        self.new_name.setPlaceholderText("Имя")
        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText("Пароль")
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.new_role = QComboBox()
        self.new_role.addItems(["Выберите роль", "user", "operator"])
        try:
            self.new_role.model().item(0).setEnabled(False)
        except Exception:
            pass
        self.new_role.setCurrentIndex(0)
        self.new_role.setMinimumWidth(140)
        
        add_btn = QPushButton("Создать аккаунт")
        add_btn.clicked.connect(self.create_user)
        
        form_layout.addWidget(self.new_username)
        form_layout.addWidget(self.new_name)
        form_layout.addWidget(self.new_password)
        form_layout.addWidget(QLabel("Роль:"))
        form_layout.addWidget(self.new_role)
        form_layout.addWidget(add_btn)
        layout.addLayout(form_layout)
        
        del_btn = QPushButton("Удалить выбранного пользователя")
        del_btn.clicked.connect(self.delete_user)
        layout.addWidget(del_btn)
        
        self.setLayout(layout)
    
    def refresh_user_list(self):
        self.user_list.clear()
        for login, role, name in list_users():
            self.user_list.addItem(f"{login} — {name} ({role})")
    
    def create_user(self):
        login = self.new_username.text().strip()
        name = self.new_name.text().strip() or login
        password = self.new_password.text().strip()
        
        if self.new_role.currentIndex() <= 0:
            QMessageBox.warning(
                self, "Ошибка",
                "Пожалуйста, выберите роль: user или operator."
            )
            return
        
        role = self.new_role.currentText()
        
        if not login or not password:
            QMessageBox.warning(
                self, "Ошибка",
                "Логин и пароль обязательны."
            )
            return
        
        if get_user(login):
            QMessageBox.warning(
                self, "Ошибка",
                "Такой логин уже существует."
            )
            return
        
        create_user(login, password, role, name, theme="light")
        self.refresh_user_list()
        self.new_username.clear()
        self.new_name.clear()
        self.new_password.clear()
        QMessageBox.information(self, "Готово", f"Аккаунт {login} создан.")
    
    def delete_user(self):
        sel = self.user_list.currentItem()
        if not sel:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя.")
            return
        
        login = sel.text().split(" — ")[0]
        if login == "admin":
            QMessageBox.warning(
                self, "Ошибка",
                "Нельзя удалить администратора."
            )
            return
        
        delete_user_db(login)
        self.refresh_user_list()
        QMessageBox.information(
            self, "Готово",
            f"Пользователь {login} удалён."
        )


class OperatorWidget(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Панель оператора</b>"))
        layout.addWidget(QLabel("Ожидающие запросы:"))
        
        self.pending_list = QListWidget()
        self.refresh_pending()
        layout.addWidget(self.pending_list)
        
        self.question_body = QTextEdit()
        self.question_body.setReadOnly(True)
        layout.addWidget(self.question_body)
        
        self.answer_edit = QTextEdit()
        self.answer_edit.setPlaceholderText("Ответ...")
        layout.addWidget(self.answer_edit)
        
        btns = QHBoxLayout()
        answer_btn = QPushButton("Отправить ответ")
        answer_btn.clicked.connect(self.send_answer)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh_pending)
        btns.addWidget(answer_btn)
        btns.addWidget(refresh_btn)
        layout.addLayout(btns)
        
        self.pending_list.currentItemChanged.connect(self.show_selected_question)
        self.setLayout(layout)
        
        # Автообновление каждые 5 секунд
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_pending)
        self.timer.start(5000)
    
    def refresh_pending(self):
        current_selection = self.pending_list.currentItem()
        current_id = None
        if current_selection:
            try:
                current_id = int(current_selection.text().split("]")[0].strip("["))
            except: pass
        
        self.pending_list.clear()
        for qid, user, question in list_pending_questions():
            self.pending_list.addItem(
                f"[{qid}] {user}: {question[:60]}"
            )
            if qid == current_id:
                self.pending_list.setCurrentRow(self.pending_list.count() - 1)
    
    def show_selected_question(self):
        it = self.pending_list.currentItem()
        if not it:
            self.question_body.setPlainText("")
            return
        
        try:
            qid = int(it.text().split("]")[0].strip("["))
            q = get_question_by_id(qid)
            if q:
                self.question_body.setPlainText(
                    f"От: {q['user']}\n\n{q['question']}"
                )
        except:
            self.question_body.setPlainText("")
    
    def send_answer(self):
        it = self.pending_list.currentItem()
        if not it:
            QMessageBox.warning(self, "Ошибка", "Выберите вопрос.")
            return
        
        try:
            qid = int(it.text().split("]")[0].strip("["))
            ans = self.answer_edit.toPlainText().strip()
            
            if not ans:
                QMessageBox.warning(self, "Ошибка", "Введите ответ.")
                return
            
            set_answer(qid, ans, self.username)
            QMessageBox.information(self, "Готово", "Ответ отправлен.")
            self.answer_edit.clear()
            self.refresh_pending()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось отправить ответ: {e}")


class RAGClientWidget(QWidget):
    def __init__(self, api_url, username=None):
        super().__init__()
        self.api_url = api_url
        self.username = username
        self.thread = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>RAG API Клиент</b>"))
        layout.addWidget(QLabel("Ваш вопрос:"))
        
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Введите ваш вопрос...")
        self.input_box.setMaximumHeight(120)
        layout.addWidget(self.input_box)
        
        self.btn_send = QPushButton("Спросить")
        self.btn_send.clicked.connect(self.send_question)
        layout.addWidget(self.btn_send)
        
        layout.addWidget(QLabel("Ответ:"))
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        layout.addWidget(self.output_box)
        
        self.setLayout(layout)
    
    def clean_text(self, text):
        if not text: return ""
        return re.sub(
            r'\s+', ' ',
            text.replace('&nbsp;', ' ')
        ).strip()
    
    def send_question(self):
        question = self.input_box.toPlainText().strip()
        if not question:
            QMessageBox.warning(self, "Ошибка", "Введите вопрос.")
            return

        self.output_box.setText("Отправка запроса...")
        self.btn_send.setEnabled(False)

        self.thread = RequestThread(self.api_url, question)
        self.thread.finished.connect(
            lambda ans, q=question: self.on_finished(ans, q)
        )
        self.thread.error.connect(
            lambda msg, q=question: self.on_error(msg, q)
        )
        self.thread.start()
    
    def on_finished(self, answer, original_question):
        self.btn_send.setEnabled(True)
        cleaned_answer = self.clean_text(answer or "")
        
        # Маркеры, означающие, что RAG не нашел информацию
        fail_markers = ["не знаю", "не найден", "не могу ответить", "перевожу на оператора", "обратитесь к специалисту"]
        
        is_failed = not cleaned_answer or any(marker in cleaned_answer.lower() for marker in fail_markers)

        if is_failed:
            # Убрано "[Система]: К сожалению..." и "Перевожу на оператора"
            self.output_box.setText("Ваш запрос передан оператору.")
            if self.username:
                add_question(self.username, original_question, status="pending")
        else:
            self.output_box.setText(cleaned_answer)
            if self.username:
                add_question(
                    self.username,
                    original_question,
                    answer=cleaned_answer,
                    status="answered",
                    operator="RAG"
                )

        self.input_box.clear()
    
    def on_error(self, message, original_question):
        self.btn_send.setEnabled(True)
        # Убрано сообщение об ошибке связи
        self.output_box.setText("Ваш запрос передан оператору.")
        
        if self.username and original_question:
            add_question(self.username, original_question, status="pending")


class UserWidget(QWidget):
    def __init__(self, username, api_url, allow_view_own=True):
        super().__init__()
        self.username = username
        self.api_url = api_url
        self.allow_view_own = allow_view_own
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(
            QLabel(f"<b>Панель пользователя — {self.username}</b>")
        )
        
        self.rag = RAGClientWidget(api_url=self.api_url, username=self.username)
        layout.addWidget(self.rag)
        
        if self.allow_view_own:
            my_btn = QPushButton("Мои запросы")
            my_btn.clicked.connect(self.show_my_questions)
            layout.addWidget(my_btn)
        
        self.setLayout(layout)
    
    def show_my_questions(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Мои запросы")
        v = QVBoxLayout(dlg)
        
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["ID", "Вопрос", "Ответ", "Статус"])
        
        rows = list_user_questions_all(self.username)
        table.setRowCount(len(rows))
        
        for i, r in enumerate(rows):
            qid, question, answer, status = r
            table.setItem(i, 0, QTableWidgetItem(str(qid)))
            table.setItem(i, 1, QTableWidgetItem(question[:200]))
            table.setItem(i, 2, QTableWidgetItem((answer or "")[:200]))
            table.setItem(i, 3, QTableWidgetItem(status))
        
        table.resizeColumnsToContents()
        v.addWidget(table)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dlg.accept)
        v.addWidget(close_btn)
        
        dlg.resize(800, 400)
        dlg.exec()
