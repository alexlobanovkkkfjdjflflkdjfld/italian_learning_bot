# email_notifier.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import os

class EmailNotifier:
    def __init__(self):
        self.config_file = 'email_config.json'
        self.load_config()
        
    def load_config(self):
        """Загрузка конфигурации email"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "email": "",
                "password": "",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587
            }
            
    def save_config(self):
        """Сохранение конфигурации"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)
            
    def setup_email(self, email, password):
        """Настройка email"""
        self.config["email"] = email
        self.config["password"] = password
        self.save_config()
        
    def send_notification(self, words_to_review):
        """Отправка уведомления"""
        if not self.config["email"] or not self.config["password"]:
            raise ValueError("Email not configured")
            
        msg = MIMEMultipart()
        msg['From'] = self.config["email"]
        msg['To'] = self.config["email"]
        msg['Subject'] = "Пора повторить итальянские слова!"
        
        # Формируем текст письма
        body = """
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #1976D2;">Время для повторения!</h2>
                <p>Следующие слова ждут вашего внимания:</p>
                <ul>
        """
        
        for word, info in words_to_review:
            body += f"""
                <li>
                    <strong>{word}</strong> - {info['перевод']}<br>
                    <em style="color: #666;">Пример: {info['примеры'][0]['русский']}</em>
                </li>
            """
            
        body += """
                </ul>
                <p style="color: #666;">
                    Откройте приложение для изучения итальянского языка, чтобы начать повторение.
                </p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Отправляем email
        try:
            server = smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"])
            server.starttls()
            server.login(self.config["email"], self.config["password"])
            server.send_message(msg)
            server.quit()
            print(f"Уведомление отправлено на {self.config['email']}")
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")