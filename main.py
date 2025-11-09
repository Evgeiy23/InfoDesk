"""Главный модуль приложения InfoDesk."""
import sys
import os
import shutil
import json

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QStackedWidget, QFormLayout, QDialog,
    QInputDialog, QFileDialog, QMenuBar, QTableWidget, QTableWidgetItem,
    QMessageBox, QTextEdit, QSizePolicy, 
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QAction, QMovie

from rag import DEFAULT_API_URL
from database import (
    init_db, get_user, update_user_theme, list_faq_items, add_question,
    list_all_questions, list_questions_by_status
)
from widgets import (
    ProfileDialog, AdminWidget, OperatorWidget, UserWidget
)
from utils import parse_faq_file, build_and_save_stats_chart
from themes import get_light_theme, get_dark_theme, get_custom_theme, ThemeDialog


class MainWindow(QMainWindow):
    def __init__(self, api_url_default=None):
        super().__init__()
        self.setWindowTitle("InfoDesk")
        init_db()
        
        # URL-адрес RAG
        self.api_url_default = api_url_default or DEFAULT_API_URL
        self.current_user = None
        self._build_ui()
    
    def _build_ui(self):
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        
        # Верхняя панель с логотипом и меню
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 8, 8, 8)
        top_layout.setSpacing(8)
        
        # Логотип
        logo_label = QLabel()
        pixmap = QPixmap("logo.png")
        if not pixmap.isNull():
            pixmap = pixmap.scaledToHeight(
                40, Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
        top_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignLeft)
        
        # Меню-бар
        self.menu_bar = QMenuBar()
        try:
            self.menu_bar.setNativeMenuBar(False)
        except Exception:
            pass
        
        # Меню и действия
        self._setup_menu()
        
        try:
            self.setMenuWidget(self.menu_bar)
        except Exception:
            top_layout.addWidget(
                self.menu_bar, alignment=Qt.AlignmentFlag.AlignTop
            )
        
        # Скрыть меню для начального окна
        self.menu_bar.setVisible(False)
        
        top_layout.addStretch(1)
        central_layout.addWidget(top_bar)
        
        # Основной стек виджетов
        self.stack = QStackedWidget()
        central_layout.addWidget(self.stack)
        self.setCentralWidget(central)
        
        # Виджет входа
        self.login_widget = self.build_login_widget()
        self.stack.addWidget(self.login_widget)
        
        # Обновить видимость меню по умолчанию
        self.update_menu_visibility()
        
        self.resize(980, 660)
        self.setStyleSheet(get_light_theme())
    
    def _setup_menu(self):
        # Меню "Файл"
        file_menu = self.menu_bar.addMenu("Файл")
        
        # Просмотр FAQ доступен всем
        self.act_view_faq = QAction("Просмотреть FAQ", self)
        self.act_view_faq.triggered.connect(self.action_view_faq)
        file_menu.addAction(self.act_view_faq)
        file_menu.addSeparator()
        
        # Только для admin
        self.act_import_faq = QAction("Импорт FAQ...", self)
        self.act_import_faq.triggered.connect(self.action_import_faq)
        file_menu.addAction(self.act_import_faq)
        
        self.act_load_docs = QAction("Загрузить документацию...", self)
        self.act_load_docs.triggered.connect(self.action_load_documentation)
        file_menu.addAction(self.act_load_docs)
        
        self.act_settings = QAction("Настройки RAG API...", self)
        self.act_settings.triggered.connect(self.action_settings_api)
        file_menu.addAction(self.act_settings)
        file_menu.addSeparator()
        
        self.act_export_questions = QAction("Экспорт вопросов (TXT)...", self)
        self.act_export_questions.triggered.connect(
            self.action_export_questions
        )
        file_menu.addAction(self.act_export_questions)
        
        self.act_export_stats = QAction("Экспорт статистики (PNG)...", self)
        self.act_export_stats.triggered.connect(self.action_export_stats)
        file_menu.addAction(self.act_export_stats)
        
        # Меню "Вопросы" для admin/operator
        self.questions_menu = self.menu_bar.addMenu("Вопросы")
        self.act_q_all = QAction("Все вопросы", self)
        self.act_q_all.triggered.connect(
            lambda: self.show_questions_dialog(filter_mode="all")
        )
        self.questions_menu.addAction(self.act_q_all)
        
        self.act_q_pending = QAction("Ожидающие", self)
        self.act_q_pending.triggered.connect(
            lambda: self.show_questions_dialog(filter_mode="pending")
        )
        self.questions_menu.addAction(self.act_q_pending)
        
        self.act_q_answered = QAction("Отвечённые", self)
        self.act_q_answered.triggered.connect(
            lambda: self.show_questions_dialog(filter_mode="answered")
        )
        self.questions_menu.addAction(self.act_q_answered)
        
        quick_sub = self.questions_menu.addMenu("Быстрые действия")
        quick_sub.addAction(self.act_q_pending)
        quick_sub.addAction(self.act_q_answered)
        
        # Меню "Справка"
        help_menu = self.menu_bar.addMenu("Справка")
        self.act_help = QAction("Справка", self)
        self.act_help.triggered.connect(self.action_help)
        help_menu.addAction(self.act_help)
        
        # Меню "О программе"
        about_menu = self.menu_bar.addMenu("О программе")
        self.act_about = QAction("О программе InfoDesk", self)
        self.act_about.triggered.connect(self.action_about)
        about_menu.addAction(self.act_about)
    
    def update_menu_visibility(self):
        if not self.current_user:
            self.menu_bar.setVisible(False)
            return
        
        self.menu_bar.setVisible(True)
        role = get_user(self.current_user).get("role")
        is_admin = (role == "admin")
        is_operator = (role == "operator")
        
        # Меню файлов доступно всем после входа в систему
        self.act_view_faq.setVisible(True)
        self.act_import_faq.setVisible(is_admin)
        self.act_load_docs.setVisible(is_admin)
        self.act_settings.setVisible(is_admin)
        self.act_export_questions.setVisible(is_admin)
        self.act_export_stats.setVisible(is_admin)
        
        # Меню вопросов только для админа и операторов
        self.questions_menu.menuAction().setVisible(
            is_admin or is_operator
        )
        
        # Справка и информация для всех пользователей
        self.act_help.setVisible(True)
        self.act_about.setVisible(True)
    
    # ---------- Обработчики меню ----------
    def action_view_faq(self):
        items = list_faq_items()
        dlg = QDialog(self)
        dlg.setWindowTitle("FAQ")
        v = QVBoxLayout(dlg)
        
        if not items:
            v.addWidget(
                QLabel("FAQ пустой. Администратор ещё не добавил записи.")
            )
        else:
            # Показать список вопросов и ответов
            text = ""
            for _, q, a, _ in items:
                text += f"Вопрос: {q}\n"
                if a:
                    text += f"Ответ: {a}\n"
                text += "\n"  # Пустая строка между вопросами
            
            te = QTextEdit()
            te.setReadOnly(True)
            te.setPlainText(text)
            v.addWidget(te)
        
        btn = QPushButton("Закрыть")
        btn.clicked.connect(dlg.accept)
        v.addWidget(btn)
        dlg.resize(800, 500)
        dlg.exec()
    
    def action_import_faq(self):
        if (not self.current_user or
                get_user(self.current_user).get("role") != "admin"):
            QMessageBox.warning(
                self, "Доступ запрещён",
                "Только администратор может импортировать FAQ."
            )
            return
        
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите FAQ файл (.ssv, .txt)", "",
            "FAQ Files (*.ssv *.txt);;All Files (*)"
        )
        if not path:
            return
        
        try:
            items = parse_faq_file(path)
        except Exception as e:
            QMessageBox.warning(
                self, "Ошибка",
                f"Не удалось прочитать файл: {e}"
            )
            return
        
        added = 0
        for q, a in items:
            if a:
                add_question(
                    "FAQ", q, answer=a, status="answered", operator="FAQ"
                )
            else:
                add_question("FAQ", q, status="pending")
            added += 1
        
        QMessageBox.information(
            self, "Импорт FAQ",
            f"Импортировано {added} записей из {os.path.basename(path)}."
        )
    
    def action_load_documentation(self):
        if (not self.current_user or
                get_user(self.current_user).get("role") != "admin"):
            QMessageBox.warning(
                self, "Доступ запрещён",
                "Только администратор может загружать документацию."
            )
            return
        
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл документации", "",
            "Документы (*.pdf *.txt *.md);;All Files (*)"
        )
        if not path:
            return
        
        docs_dir = "docs"
        os.makedirs(docs_dir, exist_ok=True)
        
        try:
            basename = os.path.basename(path)
            dst = os.path.join(docs_dir, basename)
            shutil.copy(path, dst)
            
            if not basename.lower().endswith(".txt"):
                txt_stub = os.path.join(docs_dir, basename + ".txt")
                with open(txt_stub, "w", encoding="utf-8") as fh:
                    fh.write(
                        f"Документ {basename} загружён.\n"
                        "Отредактируйте этот файл (TXT) по необходимости.\n"
                    )
            
            QMessageBox.information(
                self, "Документация",
                f"Файл сохранён в {dst} "
                f"(и создана TXT-заглушка в {docs_dir})."
            )
        except Exception as e:
            QMessageBox.warning(
                self, "Ошибка",
                f"Не удалось загрузить документацию: {e}"
            )
    
    def action_settings_api(self):
        # Только админ может изменить URL-адрес RAG
        if (not self.current_user or
                get_user(self.current_user).get("role") != "admin"):
            QMessageBox.warning(
                self, "Доступ запрещён",
                "Только администратор может менять настройки RAG API."
            )
            return
        
        cur_url = getattr(self, "api_url_default", "")
        new, ok = QInputDialog.getText(
            self, "Настройки RAG API", "URL RAG API:",
            QLineEdit.EchoMode.Normal, cur_url
        )
        
        if ok and new:
            self.api_url_default = new.strip()
            QMessageBox.information(
                self, "Настройки",
                f"URL RAG API изменён на:\n{self.api_url_default}"
            )
    
    def action_export_questions(self):
        if (not self.current_user or
                get_user(self.current_user).get("role") != "admin"):
            QMessageBox.warning(
                self, "Доступ запрещён",
                "Только администратор может экспортировать вопросы."
            )
            return
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Экспорт вопросов (TXT)")
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Экспортировать вопросы:"))
        
        btn_all = QPushButton("Все вопросы")
        btn_pending = QPushButton("Только ожидающие")
        btn_answered = QPushButton("Только отвечённые")
        
        hl = QHBoxLayout()
        hl.addWidget(btn_all)
        hl.addWidget(btn_pending)
        hl.addWidget(btn_answered)
        v.addLayout(hl)
        
        def do_export(mode):
            if mode == "all":
                rows = list_all_questions()
            elif mode == "pending":
                rows = list_questions_by_status("pending")
            else:
                rows = list_questions_by_status("answered")
            
            if not rows:
                QMessageBox.information(
                    self, "Экспорт",
                    "Нет вопросов для экспорта."
                )
                return
            
            save_to, _ = QFileDialog.getSaveFileName(
                self, "Сохранить вопросы в TXT", "questions.txt",
                "Text Files (*.txt)"
            )
            
            if save_to:
                try:
                    with open(save_to, "w", encoding="utf-8") as fh:
                        for r in rows:
                            qid, user, question, answer, status, operator = r
                            fh.write(
                                f"ID: {qid}\n"
                                f"Пользователь: {user}\n"
                                f"Статус: {status}\n"
                                f"Оператор: {operator}\n"
                                f"Вопрос:\n{question}\n"
                            )
                            if answer:
                                fh.write(f"Ответ:\n{answer}\n")
                            fh.write("-" * 40 + "\n")
                    
                    QMessageBox.information(
                        self, "Экспорт",
                        f"Экспорт завершён: {save_to}"
                    )
                except Exception as e:
                    QMessageBox.warning(
                        self, "Ошибка",
                        f"Не удалось сохранить файл: {e}"
                    )
            dlg.accept()
        
        btn_all.clicked.connect(lambda: do_export("all"))
        btn_pending.clicked.connect(lambda: do_export("pending"))
        btn_answered.clicked.connect(lambda: do_export("answered"))
        dlg.exec()
    
    def action_export_stats(self):
        """Экспорт статистики в PNG."""
        if (not self.current_user or
                get_user(self.current_user).get("role") != "admin"):
            QMessageBox.warning(
                self, "Доступ запрещён",
                "Только администратор может экспортировать статистику."
            )
            return
        
        try:
            img_path = build_and_save_stats_chart()
        except Exception as e:
            QMessageBox.warning(
                self, "Ошибка",
                f"Не удалось построить статистику: {e}"
            )
            return
        
        save_to, _ = QFileDialog.getSaveFileName(
            self, "Сохранить график как PNG", "stats.png",
            "PNG Image (*.png)"
        )
        
        if save_to:
            try:
                shutil.copy(img_path, save_to)
                QMessageBox.information(
                    self, "Экспорт статистики",
                    f"График сохранён: {save_to}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self, "Ошибка",
                    f"Не удалось сохранить файл: {e}"
                )
        else:
            dlg = QDialog(self)
            dlg.setWindowTitle("График статистики")
            v = QVBoxLayout(dlg)
            lbl = QLabel()
            pix = QPixmap(img_path)
            lbl.setPixmap(
                pix.scaledToWidth(
                    640, Qt.TransformationMode.SmoothTransformation
                )
            )
            v.addWidget(lbl)
            btn = QPushButton("Закрыть")
            btn.clicked.connect(dlg.accept)
            v.addWidget(btn)
            dlg.exec()
        
        try:
            os.unlink(img_path)
        except Exception:
            pass
    
    def action_help(self):
        text = (
            "Справка InfoDesk\n\n"
            "- 'Файл → Просмотреть FAQ' — доступно всем "
            "вошедшим пользователям.\n"
            "- 'Файл → Импорт FAQ' и другие административные опции — "
            "доступны только администратору.\n"
            "- Операторы видят глобальные списки вопросов через "
            "'Вопросы'.\n"
            "- Обычные пользователи задают вопросы через свою панель "
            "и могут просматривать только свои запросы."
        )
        QMessageBox.information(self, "Справка", text)
    
    def action_about(self):
        about_text = (
            "О программе InfoDesk\n\n"
            "InfoDesk - Система обработки запросов\n\n"
            "Версия 1.0\n"
            "© 2025 Все права защищены"
        )
        QMessageBox.information(self, "О программе InfoDesk", about_text)
    
    def show_questions_dialog(self, filter_mode="all"):
        if not self.current_user:
            QMessageBox.warning(
                self, "Доступ запрещён",
                "Войдите в систему."
            )
            return
        
        role = get_user(self.current_user).get("role")
        if role not in ("admin", "operator"):
            QMessageBox.warning(
                self, "Доступ запрещён",
                "Только оператор или админ могут просматривать этот список."
            )
            return
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Список вопросов")
        v = QVBoxLayout(dlg)
        
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["ID", "Пользователь", "Вопрос", "Ответ", "Статус", "Оператор"]
        )
        
        if filter_mode == "all":
            rows = list_all_questions()
        elif filter_mode == "pending":
            rows = list_questions_by_status("pending")
        else:
            rows = list_questions_by_status("answered")
        
        table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            qid, user, question, answer, status, operator = r
            table.setItem(i, 0, QTableWidgetItem(str(qid)))
            table.setItem(i, 1, QTableWidgetItem(user))
            table.setItem(i, 2, QTableWidgetItem(question[:200]))
            table.setItem(i, 3, QTableWidgetItem((answer or "")[:200]))
            table.setItem(i, 4, QTableWidgetItem(status))
            table.setItem(i, 5, QTableWidgetItem(operator or ""))
        
        table.resizeColumnsToContents()
        v.addWidget(table)
        
        btns = QHBoxLayout()
        export_btn = QPushButton("Экспорт выбранных в TXT")
        
        def export_selected():
            if (not self.current_user or
                    get_user(self.current_user).get("role") != "admin"):
                QMessageBox.warning(
                    self, "Доступ запрещён",
                    "Только администратор может экспортировать вопросы."
                )
                return
            
            selected = table.selectionModel().selectedRows()
            if not selected:
                QMessageBox.information(
                    self, "Экспорт",
                    "Выберите строки для экспорта"
                )
                return
            
            save_to, _ = QFileDialog.getSaveFileName(
                self, "Сохранить вопросы в TXT",
                "questions_selected.txt", "Text Files (*.txt)"
            )
            
            if save_to:
                try:
                    with open(save_to, "w", encoding="utf-8") as fh:
                        for idx in selected:
                            row = idx.row()
                            qid = table.item(row, 0).text()
                            user = table.item(row, 1).text()
                            question = table.item(row, 2).text()
                            answer = table.item(row, 3).text()
                            status = table.item(row, 4).text()
                            operator = table.item(row, 5).text()
                            
                            fh.write(
                                f"ID: {qid}\n"
                                f"Пользователь: {user}\n"
                                f"Статус: {status}\n"
                                f"Оператор: {operator}\n"
                                f"Вопрос:\n{question}\n"
                            )
                            if answer:
                                fh.write(f"Ответ:\n{answer}\n")
                            fh.write("-" * 40 + "\n")
                    
                    QMessageBox.information(
                        self, "Экспорт",
                        f"Экспорт выбранных завершён: {save_to}"
                    )
                except Exception as e:
                    QMessageBox.warning(
                        self, "Ошибка",
                        f"Не удалось сохранить файл: {e}"
                    )
        
        export_btn.clicked.connect(export_selected)
        btns.addWidget(export_btn)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dlg.accept)
        btns.addWidget(close_btn)
        v.addLayout(btns)
        
        dlg.resize(900, 500)
        dlg.exec()
    
    # ---------- Логин / навигация ----------
    def build_login_widget(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 24, 24, 24)
        
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 32, 0, 0)
        center_layout.setSpacing(16)
        
        title = QLabel("<h2>Вход в систему</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        center_layout.addWidget(title)
        
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        
        self.login_input = QLineEdit()
        self.pw_input = QLineEdit()
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        form.addRow("Логин:", self.login_input)
        form.addRow("Пароль:", self.pw_input)
        
        form_container = QWidget()
        form_container.setLayout(form)
        form_container.setMaximumWidth(420)
        center_layout.addWidget(
            form_container, 0, Qt.AlignmentFlag.AlignHCenter
        )
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(24)
        login_btn = QPushButton("Войти")
        login_btn.clicked.connect(self.try_login)
        btn_layout.addWidget(login_btn)
        center_layout.addLayout(btn_layout)
        
        center.setMaximumWidth(560)
        layout.addWidget(center, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # Добавляем GIF снизу на весь экран
        gif_label = QLabel()
        gif_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        gif_label.setScaledContents(True)
        
        # Пытаемся загрузить GIF файл
        gif_paths = ["GIF.gif"]
        gif_loaded = False
        
        for gif_path in gif_paths:
            if os.path.exists(gif_path):
                movie = QMovie(gif_path)
                gif_label.setMovie(movie)
                # Растягиваем GIF на весь доступный экран
                gif_label.setSizePolicy(
                    QSizePolicy.Policy.Expanding, 
                    QSizePolicy.Policy.Expanding
                )
                movie.start()
                gif_loaded = True
                break
        
        if not gif_loaded:
            # Если GIF не найден, скрываем виджет
            gif_label.setVisible(False)
        
        # Добавляем GIF с растяжением, чтобы он занимал все оставшееся пространство
        layout.addWidget(gif_label, 1, Qt.AlignmentFlag.AlignHCenter)
        
        return w
    
    def try_login(self):
        login = self.login_input.text().strip()
        pw = self.pw_input.text().strip()
        user = get_user(login)
        
        if not user or user.get("password") != pw:
            QMessageBox.warning(
                self, "Ошибка",
                "Неверный логин или пароль."
            )
            return
        
        self.current_user = login
        
        # Показать меню и обновить видимость в соответствии с ролью
        self.update_menu_visibility()
        
        # Открыть пользовательский интерфейс для конкретной роли
        self.open_role_ui(user.get("role", "user"))
    
    def open_role_ui(self, role):
        container = QWidget()
        layout = QVBoxLayout(container)
        
        top_bar = QHBoxLayout()
        lbl = QLabel(
            f"Вы вошли как: <b>{self.current_user}</b> ({role})"
        )
        top_bar.addWidget(lbl)
        top_bar.addStretch(1)
        
        profile_btn = QPushButton("Профиль")
        profile_btn.clicked.connect(self.open_profile)
        top_bar.addWidget(profile_btn)
        
        self.theme_btn = QPushButton("Тема")
        top_bar.addWidget(self.theme_btn)
        self.theme_btn.clicked.connect(self.show_theme_dialog)
        
        logout_btn = QPushButton("Выйти")
        logout_btn.clicked.connect(self.logout)
        top_bar.addWidget(logout_btn)
        
        layout.addLayout(top_bar)
        
        if role == "admin":
            layout.addWidget(AdminWidget())
        elif role == "operator":
            layout.addWidget(OperatorWidget(self.current_user))
        else:
            layout.addWidget(
                UserWidget(
                    self.current_user,
                    api_url=self.api_url_default,
                    allow_view_own=True
                )
            )
        
        self.stack.addWidget(container)
        self.stack.setCurrentWidget(container)
        self.apply_theme()
    
    def open_profile(self):
        dlg = ProfileDialog(self.current_user, parent=self)
        dlg.exec()
    
    def apply_theme(self):
        user = get_user(self.current_user) or {"theme": "light"}
        theme = user.get("theme", "light")
        
        if theme == "dark":
            self.setStyleSheet(get_dark_theme())
        elif theme == "light":
            self.setStyleSheet(get_light_theme())
        else:
            # Попытка распарсить кастомную тему (JSON)
            try:
                theme_data = json.loads(theme)
                if isinstance(theme_data, dict) and theme_data.get("type") == "custom":
                    colors = theme_data.get("colors", {})
                    custom_theme = get_custom_theme(
                        colors.get("bg", "#f5f5f5"),
                        colors.get("text", "#333333"),
                        colors.get("input_bg", "#ffffff"),
                        colors.get("input_border", "#e0e0e0"),
                        colors.get("button", "#4CAF50"),
                        colors.get("button_text", "white"),
                        colors.get("menubar", "#eeeeee")
                    )
                    self.setStyleSheet(custom_theme)
                else:
                    self.setStyleSheet(get_light_theme())
            except (json.JSONDecodeError, TypeError):
                # Если не JSON, значит старая тема
                self.setStyleSheet(get_light_theme())
    
    def show_theme_dialog(self):
        """Открывает диалог выбора темы с опциями: светлая, темная, и палитра."""
        user = get_user(self.current_user) or {"theme": "light"}
        current_theme = user.get("theme", "light")
        
        dlg = ThemeDialog(
            self,
            current_theme,
            update_user_theme,
            self.apply_theme
        )
        dlg.set_current_user(self.current_user)
        dlg.exec()
    
    def logout(self):
        # Очистить пользовательский интерфейс, скрыть меню,
        self.pw_input.clear()
        self.stack.setCurrentWidget(self.login_widget)
        
        while self.stack.count() > 1:
            widget = self.stack.widget(1)
            self.stack.removeWidget(widget)
            widget.deleteLater()
        
        self.current_user = None
        self.setStyleSheet(get_light_theme())
        
        # Скрыть меню при выходе из системы
        self.menu_bar.setVisible(False)


def main():
    QApplication.setAttribute(
        Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, True
    )
    
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
