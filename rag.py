import requests
from PyQt6.QtCore import QThread, pyqtSignal

DEFAULT_API_URL = "Token_api"


class RequestThread(QThread):
    
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, api_url, question):
        super().__init__()
        self.api_url = api_url
        self.question = question
    
    def run(self):
        try:
            response = requests.post(
                self.api_url,
                json={"question": self.question},
                timeout=60
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    ans = data.get("answer", "")
                except Exception:
                    ans = response.text or ""
                self.finished.emit(ans or "")
            else:
                self.error.emit(f"Ошибка API: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка соединения с API:\n{e}")

