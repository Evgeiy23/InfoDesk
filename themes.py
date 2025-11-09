import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QLabel, QPushButton, QColorDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


def get_light_theme():
    return """
    QWidget {
        background-color: #f5f5f5;
        color: #333333;
        font-family: -apple-system, "Helvetica Neue", Arial, Roboto, sans-serif;
    }
    QLabel {
        color: #333333;
    }
    QLineEdit, QTextEdit, QComboBox {
        background-color: #ffffff;
        border: 2px solid #e0e0e0;
        border-radius: 6px;
        padding: 8px;
        color: #333333;
        font-size: 14px;
    }
    QPushButton {
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 13px;
        font-weight: bold;
    }
    QMenuBar {
        background-color: #eeeeee;
    }
    """


def get_dark_theme():
    return """
    QWidget {
        background-color: #2b2b2b;
        color: #e0e0e0;
        font-family: -apple-system, "Helvetica Neue", Arial, Roboto, sans-serif;
    }
    QLabel {
        color: #e0e0e0;
    }
    QLineEdit, QTextEdit, QComboBox {
        background-color: #3c3c3c;
        border: 2px solid #555555;
        border-radius: 6px;
        padding: 8px;
        color: #e0e0e0;
        font-size: 14px;
    }
    QPushButton {
        background-color: #66bb6a;
        color: #1e1e1e;
        border: none;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 13px;
        font-weight: bold;
    }
    QMenuBar {
        background-color: #3a3a3a;
    }
    """


def get_custom_theme(bg_color, text_color, input_bg_color, input_border_color, 
                     button_color, button_text_color, menubar_color):
    return f"""
    QWidget {{
        background-color: {bg_color};
        color: {text_color};
        font-family: -apple-system, "Helvetica Neue", Arial, Roboto, sans-serif;
    }}
    QLabel {{
        color: {text_color};
    }}
    QLineEdit, QTextEdit, QComboBox {{
        background-color: {input_bg_color};
        border: 2px solid {input_border_color};
        border-radius: 6px;
        padding: 8px;
        color: {text_color};
        font-size: 14px;
    }}
    QPushButton {{
        background-color: {button_color};
        color: {button_text_color};
        border: none;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 13px;
        font-weight: bold;
    }}
    QMenuBar {{
        background-color: {menubar_color};
    }}
    """


class ThemeDialog(QDialog):
    def __init__(self, parent, current_theme, update_user_theme_callback, apply_theme_callback):
        super().__init__(parent)
        self.current_theme = current_theme
        self.update_user_theme = update_user_theme_callback
        self.apply_theme = apply_theme_callback
        self.current_user = None
        self._build_ui()
    
    def set_current_user(self, user):
        self.current_user = user
    
    def _build_ui(self):
        self.setWindowTitle("Выбор темы")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Группа с радиокнопками для выбора типа темы
        theme_group = QGroupBox("Тип темы")
        theme_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(8)
        theme_layout.setContentsMargins(12, 12, 12, 12)
        
        self.light_radio = QRadioButton("Светлая тема")
        self.dark_radio = QRadioButton("Темная тема")
        self.custom_radio = QRadioButton("Палитра (кастомная)")
        
        # Стили для радиокнопок
        radio_style = """
            QRadioButton {
                font-size: 13px;
                padding: 5px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #888;
                background-color: white;
            }
            QRadioButton::indicator:checked {
                background-color: #4CAF50;
                border: 2px solid #4CAF50;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #4CAF50;
            }
        """
        self.light_radio.setStyleSheet(radio_style)
        self.dark_radio.setStyleSheet(radio_style)
        self.custom_radio.setStyleSheet(radio_style)
        
        # Определяем текущую выбранную тему
        if self.current_theme == "dark":
            self.dark_radio.setChecked(True)
        elif self.current_theme == "light":
            self.light_radio.setChecked(True)
        else:
            self.custom_radio.setChecked(True)
        
        theme_layout.addWidget(self.light_radio)
        theme_layout.addWidget(self.dark_radio)
        theme_layout.addWidget(self.custom_radio)
        layout.addWidget(theme_group)
        
        # Палитра цветов (видима только при выборе кастомной темы)
        self.palette_group = QGroupBox("Палитра цветов")
        self.palette_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        palette_layout = QVBoxLayout(self.palette_group)
        palette_layout.setSpacing(8)
        palette_layout.setContentsMargins(12, 12, 12, 12)
        
        # Загружаем сохраненные цвета кастомной темы, если есть
        saved_colors = {}
        if self.current_theme not in ("light", "dark"):
            try:
                theme_data = json.loads(self.current_theme)
                if isinstance(theme_data, dict) and theme_data.get("type") == "custom":
                    saved_colors = theme_data.get("colors", {})
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Цвета по умолчанию
        default_colors = {
            "bg": "#f5f5f5",
            "text": "#333333",
            "input_bg": "#ffffff",
            "input_border": "#e0e0e0",
            "button": "#4CAF50",
            "button_text": "white",
            "menubar": "#eeeeee"
        }
        
        # Объединяем сохраненные и дефолтные
        for key in default_colors:
            if key not in saved_colors:
                saved_colors[key] = default_colors[key]
        
        self.saved_colors = saved_colors
        self.color_buttons = {}
        color_labels = {
            "bg": "Фон",
            "text": "Текст",
            "input_bg": "Фон полей ввода",
            "input_border": "Граница полей",
            "button": "Кнопки",
            "button_text": "Текст кнопок",
            "menubar": "Меню-бар"
        }
        
        for key, label in color_labels.items():
            row = QHBoxLayout()
            row.setSpacing(12)
            
            label_widget = QLabel(label + ":")
            label_widget.setMinimumWidth(160)
            label_widget.setStyleSheet("font-size: 13px; font-weight: 500;")
            row.addWidget(label_widget)
            
            color_btn = QPushButton("Выбрать цвет")
            color_btn.setFixedSize(140, 40)
            
            # Создаем стиль для кнопки с цветом
            btn_style = f"""
            QPushButton {{
                background-color: {saved_colors[key]};
                color: {'white' if QColor(saved_colors[key]).lightness() < 128 else 'black'};
                border: 2px solid #888;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border: 3px solid #555;
                background-color: {saved_colors[key]};
            }}
            QPushButton:pressed {{
                border: 2px solid #333;
                background-color: {saved_colors[key]};
            }}
            """
            
            color_btn.setStyleSheet(btn_style)
            self.color_buttons[key] = color_btn
            
            def make_color_handler(color_key):
                def choose_color():
                    current_color = QColor(self.saved_colors[color_key])
                    color = QColorDialog.getColor(current_color, self, f"Выберите цвет для {color_labels[color_key]}")
                    if color.isValid():
                        hex_color = color.name()
                        self.saved_colors[color_key] = hex_color
                        
                        # Обновляем стиль кнопки
                        new_style = f"""
                        QPushButton {{
                            background-color: {hex_color};
                            color: {'white' if color.lightness() < 128 else 'black'};
                            border: 2px solid #888;
                            border-radius: 8px;
                            padding: 8px 12px;
                            font-weight: bold;
                            font-size: 12px;
                        }}
                        QPushButton:hover {{
                            border: 3px solid #555;
                            background-color: {hex_color};
                        }}
                        QPushButton:pressed {{
                            border: 2px solid #333;
                            background-color: {hex_color};
                        }}
                        """
                        self.color_buttons[color_key].setStyleSheet(new_style)
                return choose_color
            
            color_btn.clicked.connect(make_color_handler(key))
            row.addWidget(color_btn)
            palette_layout.addLayout(row)
        
        layout.addWidget(self.palette_group)
        
        # Функция для показа/скрытия палитры
        def update_palette_visibility():
            self.palette_group.setVisible(self.custom_radio.isChecked())
            # Подстраиваем размер окна после изменения видимости
            self.adjustSize()
        
        self.light_radio.toggled.connect(update_palette_visibility)
        self.dark_radio.toggled.connect(update_palette_visibility)
        self.custom_radio.toggled.connect(update_palette_visibility)
        update_palette_visibility()
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        apply_btn = QPushButton("✓ Применить")
        apply_btn.setMinimumWidth(120)
        apply_btn.setMinimumHeight(40)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        cancel_btn = QPushButton("✕ Отмена")
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
        """)
        
        def apply_theme():
            if self.light_radio.isChecked():
                self.update_user_theme(self.current_user, "light")
            elif self.dark_radio.isChecked():
                self.update_user_theme(self.current_user, "dark")
            else:
                # Сохраняем кастомную тему как JSON
                theme_json = json.dumps({
                    "type": "custom",
                    "colors": self.saved_colors
                })
                self.update_user_theme(self.current_user, theme_json)
            
            self.apply_theme()
            self.accept()
        
        apply_btn.clicked.connect(apply_theme)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)
        
        # Подстраиваем размер окна под содержимое
        self.adjustSize()
        # Устанавливаем минимальный размер, чтобы не было пустого пространства
        self.setMinimumSize(self.size())

