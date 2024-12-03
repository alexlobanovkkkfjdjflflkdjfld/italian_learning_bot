import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import datetime
from plyer import notification
import threading
import time
import random
import difflib
import unicodedata
from vocabulary import VOCABULARY


class ItalianLearningApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Изучение итальянского языка")
        self.root.geometry("800x600")
        
        # Настройка цветов для интерфейса
        self.colors = {
            "primary": "#1976D2",     # основной цвет
            "success": "#4CAF50",     # цвет успеха
            "error": "#f44336",       # цвет ошибки
            "warning": "#FFA726",     # цвет предупреждения
            "hint": "#673AB7",        # цвет подсказки
            "background": "#FFFFFF",   # фон
            "text": "#212121",        # основной текст
            "secondary_text": "#757575" # вторичный текст
        }
        
        # Создаем стили после определения цветов
        self.create_styles()
        
        # Использование импортированного словаря
        self.vocabulary = VOCABULARY
        
        # # ... остальной код ...
        
# class ItalianLearningApp:
    # def __init__(self):
        # self.root = tk.Tk()
        # self.root.title("Изучение итальянского языка")
        # self.root.geometry("800x600")
        
        # # Настройка цветов для интерфейса
        # self.colors = {
            # "primary": "#1976D2",     # основной цвет
            # "success": "#4CAF50",     # цвет успеха
            # "error": "#f44336",       # цвет ошибки
            # "warning": "#FFA726",     # цвет предупреждения
            # "hint": "#673AB7",        # цвет подсказки
            # "background": "#FFFFFF",   # фон
            # "text": "#212121",        # основной текст
            # "secondary_text": "#757575" # вторичный текст
        # }
        
        # # Создаем стили после определения цветов
        # self.create_styles()
        
        # # Словарь с данными
        # self.vocabulary = {
            # "Изучаю": {},
            # "Буду изучать": {
                # "il progetto": {
                    # "перевод": "проект",
                    # "примеры": [
                        # {
                            # "русский": "Это важный проект",
                            # "итальянский": "È un progetto importante",
                            # "альтернативы_рус": ["Это важный план"],
                            # "альтернативы_ит": ["Questo è un progetto importante"]
                        # }
                    # ]
                # },
                # "il colloquio": {
                    # "перевод": "собеседование",
                    # "примеры": [
                        # {
                            # "русский": "У меня собеседование в понедельник утром",
                            # "итальянский": "Ho un colloquio lunedì mattina",
                            # "альтернативы_рус": ["У меня встреча в понедельник утром"],
                            # "альтернативы_ит": ["Ho il colloquio lunedì mattina"]
                        # }
                    # ]
                # },
                # "l'esperienza": {
                    # "перевод": "опыт",
                    # "примеры": [
                        # {
                            # "русский": "У меня большой опыт работы",
                            # "итальянский": "Ho molta esperienza di lavoro",
                            # "альтернативы_рус": ["Я имею большой опыт работы"],
                            # "альтернативы_ит": ["Ho una grande esperienza di lavoro"]
                        # }
                    # ]
                # },
                # "la riunione": {
                    # "перевод": "совещание",
                    # "примеры": [
                        # {
                            # "русский": "Совещание начнется через час",
                            # "итальянский": "La riunione inizierà tra un'ora",
                            # "альтернативы_рус": ["Встреча начнется через час"],
                            # "альтернативы_ит": ["La riunione comincerà tra un'ora"]
                        # }
                    # ]
                # }
            # },
            # "Изучил": {}
        # }
        
        # Инициализация интерфейса
        self.setup_ui()
        
        # Загрузка расписания
        self.load_schedule()
        
        # Запуск автоматического обновления
        self.start_auto_update()
    def create_styles(self):
        """Создание стилей для виджетов"""
        style = ttk.Style()
        
        # Основной стиль кнопок
        style.configure(
            "Main.TButton",
            padding=10,
            font=('Helvetica', 10, 'bold'),
            width=15
        )
        
        # Стиль для кнопок в окне повторения
        style.configure(
            "Review.TButton",
            padding=8,
            font=('Helvetica', 10),
            width=15
        )
        
        # Стиль для кнопки подсказки
        style.configure(
            "Hint.TButton",
            padding=8,
            font=('Helvetica', 10),
            width=15
        )
        
        # Стиль для кнопки проверки
        style.configure(
            "Check.TButton",
            padding=8,
            font=('Helvetica', 10, 'bold'),
            width=15
        )
        
        # Стиль для меток
        style.configure(
            "Main.TLabel",
            font=('Helvetica', 10),
            foreground=self.colors["text"]
        )
        
        # Стиль для заголовков
        style.configure(
            "Header.TLabel",
            font=('Helvetica', 16, 'bold'),
            foreground=self.colors["primary"]
        )
        
        # Стиль для подзаголовков
        style.configure(
            "Subheader.TLabel",
            font=('Helvetica', 12, 'bold'),
            foreground=self.colors["text"]
        )

    def setup_ui(self):
        """Создание пользовательского интерфейса"""
        # Основной фрейм
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Настройка расширения окна
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        
        # Заголовок
        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        title_label = ttk.Label(
            header_frame,
            text="Изучение итальянского языка",
            style="Header.TLabel"
        )
        title_label.pack(pady=(0, 5))
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Система интервального повторения",
            style="Subheader.TLabel"
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Рамка для расписания
        schedule_frame = ttk.LabelFrame(
            self.main_frame,
            text="Расписание повторений",
            padding="10"
        )
        schedule_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        schedule_frame.columnconfigure(0, weight=1)
        schedule_frame.rowconfigure(0, weight=1)
        
        # Текстовое поле для расписания с прокруткой
        schedule_container = ttk.Frame(schedule_frame)
        schedule_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        schedule_container.columnconfigure(0, weight=1)
        schedule_container.rowconfigure(0, weight=1)
        
        self.schedule_text = tk.Text(
            schedule_container,
            height=15,
            width=70,
            font=('Helvetica', 10),
            wrap=tk.WORD,
            padx=10,
            pady=10,
            background=self.colors["background"],
            foreground=self.colors["text"]
        )
        self.schedule_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(
            schedule_container,
            orient="vertical",
            command=self.schedule_text.yview
        )
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.schedule_text.configure(yscrollcommand=scrollbar.set)
        
        # Кнопки управления
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=20)
        
        refresh_btn = ttk.Button(
            button_frame,
            text="🔄 Обновить расписание",
            command=self.load_schedule,
            style="Main.TButton",
            width=25
        )
        refresh_btn.pack(side=tk.LEFT, padx=10)
        
        start_btn = ttk.Button(
            button_frame,
            text="▶️ Начать повторение",
            command=self.start_review,
            style="Main.TButton",
            width=25
        )
        start_btn.pack(side=tk.LEFT, padx=10)
        
        # Статус и информация
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0))
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="",
            style="Main.TLabel"
        )
        self.status_label.pack(side=tk.LEFT)
    
    # def load_schedule(self):
    def load_schedule(self):
        """Загрузка и отображение расписания"""
        print("Доступные слова в словаре:", list(self.vocabulary["Буду изучать"].keys()))
        print("Размер словаря:", len(self.vocabulary["Буду изучать"]))
        
        self.schedule_text.config(state=tk.NORMAL)
        self.schedule_text.delete('1.0', tk.END)
        current_time = datetime.datetime.now()
        
        # """Загрузка и отображение расписания"""
        # self.schedule_text.config(state=tk.NORMAL)
        # self.schedule_text.delete('1.0', tk.END)
        # current_time = datetime.datetime.now()
        
        schedule_file = 'schedule.json'
        
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                schedule = json.load(f)
        except FileNotFoundError:
            # Создаем начальное расписание
            schedule = {"words": []}
            
            # Получаем все доступные слова
            available_words = list(self.vocabulary["Буду изучать"].keys())
            print("Создаем расписание для слов:", available_words)
            
            # Добавляем все слова в расписание
            for i, word in enumerate(available_words):
                # Первое слово для срочного изучения, остальные - через интервалы
                next_review = current_time if i == 0 else current_time + datetime.timedelta(minutes=5*(i))
                
                schedule["words"].append({
                    "word": word,
                    "translation": self.vocabulary["Буду изучать"][word]["перевод"],
                    "next_review": next_review.isoformat()
                })
                print(f"Добавлено слово: {word}")
            
            # Сохраняем расписание
            with open(schedule_file, 'w', encoding='utf-8') as f:
                json.dump(schedule, f, ensure_ascii=False, indent=2)
            
            print("Расписание создано и сохранено")
            
        # try:
            # with open(schedule_file, 'r', encoding='utf-8') as f:
                # schedule = json.load(f)
        # except FileNotFoundError:
            # # Создаем начальное расписание
            # schedule = {"words": []}
            
            # # Слово для срочного изучения
            # schedule["words"].append({
                # "word": "lavorare",
                # "translation": self.vocabulary["Буду изучать"]["lavorare"]["перевод"],
                # "next_review": current_time.isoformat()  # Текущее время для срочного изучения
            # })
            
            # # Добавляем остальные слова для будущего изучения
            # future_words = ["un lavoro", "un impiegato", "un capo"]
            # for i, word in enumerate(future_words):
                # if word in self.vocabulary["Буду изучать"]:
                    # schedule["words"].append({
                        # "word": word,
                        # "translation": self.vocabulary["Буду изучать"][word]["перевод"],
                        # "next_review": (current_time + datetime.timedelta(minutes=5*(i+1))).isoformat()
                    # })
            
            # # Сохраняем расписание
            # with open(schedule_file, 'w', encoding='utf-8') as f:
                # json.dump(schedule, f, ensure_ascii=False, indent=2)
        
        # Разделение слов на категории
        urgent_words = []  # слова для срочного повторения
        future_words = []  # слова для будущего повторения
        
        for word in schedule["words"]:
            next_review = datetime.datetime.fromisoformat(word["next_review"])
            time_diff = next_review - current_time
            
            if time_diff.total_seconds() <= 0:
                urgent_words.append(word)
            else:
                hours = int(time_diff.total_seconds() // 3600)
                minutes = int((time_diff.total_seconds() % 3600) // 60)
                future_words.append({
                    "word": word,
                    "hours": hours,
                    "minutes": minutes
                })
        
        # Отображение срочных слов
        if urgent_words:
            self.schedule_text.insert(tk.END, "🔔 ПОРА ПОВТОРИТЬ:\n\n", "header_black")
            for word in urgent_words:
                self.schedule_text.insert(
                    tk.END,
                    f"• {word['word']} - {word['translation']}\n",
                    "current"
                )
                if not self.root.focus_displayof():
                    self.show_notification(word)
            self.schedule_text.insert(tk.END, "\n")
        
        # Отображение будущих слов
        if future_words:
            self.schedule_text.insert(tk.END, "⏰ ПРЕДСТОЯЩИЕ ПОВТОРЕНИЯ:\n\n", "header")
            future_words.sort(key=lambda x: (x["hours"], x["minutes"]))
            for word_info in future_words:
                time_str = f"{word_info['hours']}ч {word_info['minutes']}мин"
                word = word_info["word"]
                self.schedule_text.insert(
                    tk.END,
                    f"• Через {time_str}: {word['word']} - {word['translation']}\n",
                    "future"
                )
        
        # Настройка тегов форматирования
        self.schedule_text.tag_configure(
            "header",
            font=('Helvetica', 11, 'bold'),
            foreground=self.colors["primary"]
        )
        self.schedule_text.tag_configure(
            "header_black",
            font=('Helvetica', 11, 'bold'),
            foreground=self.colors["text"]
        )
        self.schedule_text.tag_configure(
            "current",
            font=('Helvetica', 10),
            foreground=self.colors["error"]
        )
        self.schedule_text.tag_configure(
            "future",
            font=('Helvetica', 10),
            foreground=self.colors["secondary_text"]
        )
        
        # Обновляем статус
        self.status_label.config(
            text=f"Последнее обновление: {current_time.strftime('%H:%M:%S')}"
        )
        
        self.schedule_text.config(state=tk.DISABLED)
        
    # def load_schedule(self):
        # """Загрузка и отображение расписания"""
        # self.schedule_text.config(state=tk.NORMAL)
        # self.schedule_text.delete('1.0', tk.END)
        # current_time = datetime.datetime.now()
        
        # schedule_file = 'schedule.json'
        # try:
            # with open(schedule_file, 'r', encoding='utf-8') as f:
                # schedule = json.load(f)
        # except FileNotFoundError:
            # # Создаем начальное расписание
            # schedule = {"words": []}
            # words_list = ["il progetto", "il colloquio", "l'esperienza", "la riunione"]
            
            # # Все слова добавляем одинаково
            # for word in words_list:
                # if word in self.vocabulary["Буду изучать"]:
                    # schedule["words"].append({
                        # "word": word,
                        # "translation": self.vocabulary["Буду изучать"][word]["перевод"],
                        # "next_review": current_time.isoformat()  # Все слова доступны сразу
                    # })
            
            # with open(schedule_file, 'w', encoding='utf-8') as f:
                # json.dump(schedule, f, ensure_ascii=False, indent=2)
        
        # # Разделение слов на категории
        # urgent_words = []  # слова для срочного повторения
        # future_words = []  # слова для будущего повторения
        
        # for word in schedule["words"]:
            # next_review = datetime.datetime.fromisoformat(word["next_review"])
            # time_diff = next_review - current_time
            
            # if time_diff.total_seconds() <= 0:
                # urgent_words.append(word)
            # else:
                # hours = int(time_diff.total_seconds() // 3600)
                # minutes = int((time_diff.total_seconds() % 3600) // 60)
                # future_words.append({
                    # "word": word,
                    # "hours": hours,
                    # "minutes": minutes
                # })
        
        # # Отображение срочных слов
        # if urgent_words:
            # self.schedule_text.insert(tk.END, "🔔 ПОРА ПОВТОРИТЬ:\n\n", "header_black")
            # for word in urgent_words:
                # self.schedule_text.insert(
                    # tk.END,
                    # f"• {word['word']} - {word['translation']}\n",
                    # "current"
                # )
                # if not self.root.focus_displayof():
                    # self.show_notification(word)
            # self.schedule_text.insert(tk.END, "\n")
        
        # # Отображение будущих слов
        # if future_words:
            # self.schedule_text.insert(tk.END, "⏰ ПРЕДСТОЯЩИЕ ПОВТОРЕНИЯ:\n\n", "header")
            # future_words.sort(key=lambda x: (x["hours"], x["minutes"]))
            # for word_info in future_words:
                # time_str = f"{word_info['hours']}ч {word_info['minutes']}мин"
                # self.schedule_text.insert(
                    # tk.END,
                    # f"• Через {time_str}: {word_info['word']['word']} - {word_info['word']['translation']}\n",
                    # "future"
                # )
        
        # # Настройка тегов
        # self.schedule_text.tag_configure(
            # "header",
            # font=('Helvetica', 11, 'bold'),
            # foreground=self.colors["primary"]
        # )
        # self.schedule_text.tag_configure(
            # "header_black",
            # font=('Helvetica', 11, 'bold'),
            # foreground=self.colors["text"]
        # )
        # self.schedule_text.tag_configure(
            # "current",
            # font=('Helvetica', 10),
            # foreground=self.colors["error"]
        # )
        # self.schedule_text.tag_configure(
            # "future",
            # font=('Helvetica', 10),
            # foreground=self.colors["secondary_text"]
        # )
        
        # # Обновляем статус
        # self.status_label.config(
            # text=f"Последнее обновление: {current_time.strftime('%H:%M:%S')}"
        # )
        
        # self.schedule_text.config(state=tk.DISABLED)
        
    # def load_schedule(self):
        # """Загрузка и отображение расписания"""
        # self.schedule_text.config(state=tk.NORMAL)
        # self.schedule_text.delete('1.0', tk.END)
        # current_time = datetime.datetime.now()
        
        # schedule_file = 'schedule.json'
        # try:
            # with open(schedule_file, 'r', encoding='utf-8') as f:
                # schedule = json.load(f)
        # except FileNotFoundError:
            # # Создаем начальное расписание
            # schedule = {"words": []}
            
            # # Записываем слово il progetto для срочного изучения
            # schedule["words"].append({
                # "word": "il progetto",
                # "translation": self.vocabulary["Буду изучать"]["il progetto"]["перевод"],
                # "next_review": current_time.isoformat()  # Текущее время для срочного изучения
            # })
            
            # # Добавляем остальные слова для будущего изучения
            # future_words = ["il colloquio", "l'esperienza", "la riunione"]
            # for word in future_words:
                # if word in self.vocabulary["Буду изучать"]:
                    # schedule["words"].append({
                        # "word": word,
                        # "translation": self.vocabulary["Буду изучать"][word]["перевод"],
                        # "next_review": (current_time + datetime.timedelta(hours=4)).isoformat()
                    # })
            
            # with open(schedule_file, 'w', encoding='utf-8') as f:
                # json.dump(schedule, f, ensure_ascii=False, indent=2)
        
        # # Разделение слов на категории
        # urgent_words = []  # слова для срочного повторения
        # future_words = []  # слова для будущего повторения
        
        # for word in schedule["words"]:
            # next_review = datetime.datetime.fromisoformat(word["next_review"])
            # time_diff = next_review - current_time
            
            # # Если время повторения уже наступило или это слово il progetto
            # if time_diff.total_seconds() <= 0 or word["word"] == "il progetto":
                # urgent_words.append(word)
            # else:
                # hours = int(time_diff.total_seconds() // 3600)
                # minutes = int((time_diff.total_seconds() % 3600) // 60)
                # future_words.append({
                    # "word": word,
                    # "hours": hours,
                    # "minutes": minutes
                # })
        
        # # Отображение срочных слов
        # if urgent_words:
            # self.schedule_text.insert(tk.END, "🔔 ПОРА ПОВТОРИТЬ:\n\n", "header_black")
            # for word in urgent_words:
                # self.schedule_text.insert(
                    # tk.END,
                    # f"• {word['word']} - {word['translation']}\n",
                    # "current"
                # )
                # if not self.root.focus_displayof():
                    # self.show_notification(word)
            # self.schedule_text.insert(tk.END, "\n")
        
        # # Отображение будущих слов
        # if future_words:
            # self.schedule_text.insert(tk.END, "⏰ ПРЕДСТОЯЩИЕ ПОВТОРЕНИЯ:\n\n", "header")
            # future_words.sort(key=lambda x: (x["hours"], x["minutes"]))
            # for word_info in future_words:
                # time_str = f"{word_info['hours']}ч {word_info['minutes']}мин"
                # word = word_info["word"]
                # self.schedule_text.insert(
                    # tk.END,
                    # f"• Через {time_str}: {word['word']} - {word['translation']}\n",
                    # "future"
                # )
        
        # # Настройка тегов форматирования
        # self.schedule_text.tag_configure(
            # "header",
            # font=('Helvetica', 11, 'bold'),
            # foreground=self.colors["primary"]
        # )
        # self.schedule_text.tag_configure(
            # "header_black",
            # font=('Helvetica', 11, 'bold'),
            # foreground=self.colors["text"]
        # )
        # self.schedule_text.tag_configure(
            # "current",
            # font=('Helvetica', 10),
            # foreground=self.colors["error"]
        # )
        # self.schedule_text.tag_configure(
            # "future",
            # font=('Helvetica', 10),
            # foreground=self.colors["secondary_text"]
        # )
        
        # # Обновляем статус
        # self.status_label.config(
            # text=f"Последнее обновление: {current_time.strftime('%H:%M:%S')}"
        # )
        
        # self.schedule_text.config(state=tk.DISABLED)

    def show_notification(self, word):
        """Показ уведомления Windows"""
        try:
            notification.notify(
                title='Время изучения итальянского!',
                message=f'Пора повторить слово: {word["word"]} ({word["translation"]})',
                app_icon=None,
                timeout=10
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")

    def start_auto_update(self):
        """Запуск автоматического обновления"""
        def auto_update():
            while True:
                try:
                    if not any(isinstance(child, tk.Toplevel) for child in self.root.winfo_children()):
                        self.root.after(0, self.load_schedule)
                    time.sleep(60)  # проверка каждую минуту
                except Exception as e:
                    print(f"Ошибка при автоматическом обновлении: {e}")
                    time.sleep(60)
        
        update_thread = threading.Thread(target=auto_update, daemon=True)
        update_thread.start()
    
    def normalize_italian_text(self, text):
        """Нормализация итальянского текста для сравнения"""
        # Приводим к нижнему регистру
        text = text.lower()
        
        # Словарь замен специальных символов
        replacements = {
            'à': 'a',
            'è': 'e',
            'é': 'e',
            'ì': 'i',
            'í': 'i',
            'ò': 'o',
            'ó': 'o',
            'ù': 'u',
            'ú': 'u',
            "'": "'",
            '`': "'",
            '´': "'",
            '–': '-',  # длинное тире
            '—': '-',  # длинное тире
            '-': ' '   # обычное тире заменяем на пробел
        }
        
        # Применяем замены
        for special, normal in replacements.items():
            text = text.replace(special, normal)
        
        # Обрабатываем случаи с апострофом
        text = text.replace("l'", "lo ").replace("un'", "una ")
        text = text.replace("dell'", "dello ").replace("all'", "allo ")
        text = text.replace("dall'", "dallo ").replace("sull'", "sullo ")
        
        # Удаляем двойные пробелы и пробелы по краям
        text = ' '.join(text.split())
        
        # Удаляем знаки препинания
        punctuation = '.,;:!?"\'«»„"'
        for p in punctuation:
            text = text.replace(p, '')
            
        return text
        
    # def normalize_italian_text(self, text):
        # """Нормализация итальянского текста для сравнения"""
        # # Приводим к нижнему регистру
        # text = text.lower()
        
        # # Словарь замен специальных символов
        # replacements = {
            # 'à': 'a',
            # 'è': 'e',
            # 'é': 'e',
            # 'ì': 'i',
            # 'í': 'i',
            # 'ò': 'o',
            # 'ó': 'o',
            # 'ù': 'u',
            # 'ú': 'u',
            # "'": "'",
            # '`': "'",
            # '´': "'"
        # }
        
        # # Применяем замены
        # for special, normal in replacements.items():
            # text = text.replace(special, normal)
        
        # # Обрабатываем случаи с апострофом
        # text = text.replace("l'", "lo ").replace("un'", "una ")
        # text = text.replace("dell'", "dello ").replace("all'", "allo ")
        # text = text.replace("dall'", "dallo ").replace("sull'", "sullo ")
        
        # # Удаляем двойные пробелы и пробелы по краям
        # text = ' '.join(text.split())
        
        # # Удаляем знаки препинания
        # punctuation = '.,;:!?"\'«»„"'
        # for p in punctuation:
            # text = text.replace(p, '')
            
        # return text

    def are_texts_equal(self, text1, text2):
        """Сравнение текстов с учетом возможных вариаций"""
        # Нормализуем оба текста
        norm1 = self.normalize_italian_text(text1)
        norm2 = self.normalize_italian_text(text2)
        
        # Прямое сравнение после нормализации
        if norm1 == norm2:
            return True
        
        # Сравнение без пробелов
        if norm1.replace(' ', '') == norm2.replace(' ', ''):
            return True
        
        # Разбиваем на слова для сравнения
        words1 = norm1.split()
        words2 = norm2.split()
        
        # Если разное количество слов - сразу False
        if len(words1) != len(words2):
            return False
        
        # Словарь возможных замен артиклей
        article_variants = {
            'il': ['lo', 'l'],
            'lo': ['il', 'l'],
            'la': ['l'],
            'i': ['gli'],
            'gli': ['i'],
            'un': ['uno'],
            'uno': ['un'],
            'una': ['un'],
        }
        
        # Проверяем каждое слово
        for i in range(len(words1)):
            if words1[i] != words2[i]:
                # Проверяем, является ли слово артиклем
                if words1[i] in article_variants and words2[i] in article_variants[words1[i]]:
                    continue
                if words2[i] in article_variants and words1[i] in article_variants[words2[i]]:
                    continue
                return False
        
        return True

    def check_answer_with_variants(self, user_answer, correct_answer, alternatives):
        """Проверка ответа с учетом всех возможных вариантов"""
        # Проверяем основной ответ
        if self.are_texts_equal(user_answer, correct_answer):
            return True
        
        # Проверяем альтернативные варианты
        for alt in alternatives:
            if self.are_texts_equal(user_answer, alt):
                return True
        
        return False

    def create_review_window(self, words_to_review):
        """Создание окна повторения"""
        review_window = tk.Toplevel(self.root)
        review_window.title("Повторение слов")
        review_window.geometry("800x600")
        review_window.transient(self.root)
        
        # Настройка фона
        review_window.configure(bg=self.colors["background"])
        
        # Центрирование окна
        review_window.update_idletasks()
        width = review_window.winfo_width()
        height = review_window.winfo_height()
        x = (review_window.winfo_screenwidth() // 2) - (width // 2)
        y = (review_window.winfo_screenheight() // 2) - (height // 2)
        review_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Основной фрейм
        main_frame = ttk.Frame(review_window, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Настройка расширения
        review_window.columnconfigure(0, weight=1)
        review_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        return review_window, main_frame
     
    def show_exercise(self, current_word_index, words_to_review, exercise_frame, progress_label, stats_label=None):
        """Показ упражнения для текущего слова"""
        # Очищаем фрейм
        for widget in exercise_frame.winfo_children():
            widget.destroy()

        # Получаем текущее слово
        word_info = words_to_review[current_word_index["value"]]
        word = word_info["word"]
        data = word_info["data"]
        example = random.choice(data["примеры"])
        
        # Определяем направление перевода
        if self.translation_direction.get() == "ru_to_it":
            question = example["русский"]
            correct_answer = example["итальянский"]
            alternatives = example.get("альтернативы_ит", [])
        else:
            question = example["итальянский"]
            correct_answer = example["русский"]
            alternatives = example.get("альтернативы_рус", [])

        # Обновляем прогресс
        if progress_label:
            progress_label.config(
                text=f"Слово {current_word_index['value'] + 1} из {len(words_to_review)}"
            )

        # Создаем виджеты
        exercise_container = ttk.Frame(exercise_frame, padding="20")
        exercise_container.pack(fill=tk.BOTH, expand=True)
        
        # Слово и его перевод
        word_frame = ttk.Frame(exercise_container)
        word_frame.pack(fill=tk.X, pady=(0, 20))
        
        word_label = ttk.Label(
            word_frame,
            text=word,
            font=('Helvetica', 16, 'bold'),
            foreground=self.colors["primary"]
        )
        word_label.pack(side=tk.LEFT, padx=5)
        
        translation_label = ttk.Label(
            word_frame,
            text=f"- {data['перевод']}",
            font=('Helvetica', 14)
        )
        translation_label.pack(side=tk.LEFT)

        # Задание
        task_frame = ttk.LabelFrame(
            exercise_container,
            text="Задание",
            padding="10"
        )
        task_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(
            task_frame,
            text="Переведите:",
            font=('Helvetica', 11),
            foreground=self.colors["primary"]  # Сделали синим
        ).pack()
        
        ttk.Label(
            task_frame,
            text=question,
            font=('Helvetica', 12, 'bold'),
            wraplength=600
        ).pack(pady=(5, 0))

        # Поле ввода
        entry_frame = ttk.Frame(exercise_container)
        entry_frame.pack(fill=tk.X, pady=(0, 10))
        
        answer_var = tk.StringVar()
        answer_entry = ttk.Entry(
            entry_frame,
            textvariable=answer_var,
            font=('Helvetica', 12),
            width=50
        )
        answer_entry.pack(pady=(0, 10))
        answer_entry.focus()

        # Область обратной связи
        feedback_frame = ttk.Frame(exercise_container)
        feedback_frame.pack(fill=tk.X, pady=(0, 20))
        
        feedback_text = tk.Text(
            feedback_frame,
            height=4,
            width=50,
            wrap=tk.WORD,
            font=('Helvetica', 11),
            borderwidth=1,
            relief="solid",
            padx=10,
            pady=5
        )
        feedback_text.pack(fill=tk.X)
        feedback_text.config(state=tk.DISABLED)

        def check_answer(event=None):
            """Проверка ответа пользователя"""
            user_answer = answer_var.get().strip()
            
            feedback_text.config(state=tk.NORMAL)
            feedback_text.delete(1.0, tk.END)
            
            if self.check_answer_with_variants(user_answer, correct_answer, alternatives):
                # Правильный ответ
                feedback_text.insert(tk.END, "✅ Правильно!\n", "correct")
                feedback_text.insert(tk.END, f"\nВаш ответ: {user_answer}", "user_answer")
                
                # Активируем кнопку "Далее"
                next_button.config(state=tk.NORMAL)
                
                # Удаляем старые привязки Enter
                answer_entry.unbind('<Return>')
                
                # Функция для следующего упражнения
                def go_to_next(event=None):
                    if next_button['state'] == 'normal':  # Проверяем, активна ли кнопка
                        self.next_exercise(
                            current_word_index,
                            words_to_review,
                            exercise_frame,
                            progress_label,
                            stats_label
                        )
                
                # Привязываем Enter к следующему упражнению только после правильного ответа
                exercise_frame.bind('<Return>', go_to_next)
                
                # Деактивируем остальные элементы
                answer_entry.config(state=tk.DISABLED)
                check_button.config(state=tk.DISABLED)
                hint_button.config(state=tk.DISABLED)
                
                # Устанавливаем фокус на кнопку "Далее"
                next_button.focus_set()
            else:
                # Неправильный ответ
                feedback_text.insert(tk.END, "❌ Ошибка в ответе:\n\n", "error")
                
                # Разбиваем ответы на слова
                user_words = user_answer.split()
                correct_words = correct_answer.split()
                
                # Сравниваем слово за словом
                feedback_text.insert(tk.END, "Проверка по словам:\n", "label")
                for i, user_word in enumerate(user_words):
                    if i < len(correct_words):
                        # Нормализуем слова для сравнения
                        norm_user = self.normalize_italian_text(user_word)
                        norm_correct = self.normalize_italian_text(correct_words[i])
                        
                        if norm_user == norm_correct:
                            feedback_text.insert(tk.END, f"{user_word} ✓  ", "correct_word")
                        else:
                            feedback_text.insert(tk.END, f"{user_word} ❌ ", "wrong_word")
                            feedback_text.insert(tk.END, f"(ожидается: {correct_words[i]})\n", "hint")
                    else:
                        feedback_text.insert(tk.END, f"{user_word} ❌ (лишнее слово)\n", "wrong_word")
                
                # Показываем пропущенные слова
                if len(correct_words) > len(user_words):
                    feedback_text.insert(tk.END, "\nПропущены слова: ", "label")
                    for i in range(len(user_words), len(correct_words)):
                        feedback_text.insert(tk.END, f"{correct_words[i]} ", "missing_word")
                
                feedback_text.insert(tk.END, "\n\nПравильный вариант: ", "label")
                feedback_text.insert(tk.END, correct_answer, "correct_answer")

            # Настройка тегов форматирования
            feedback_text.tag_config("correct", foreground=self.colors["success"], font=('Helvetica', 11, 'bold'))
            feedback_text.tag_config("error", foreground=self.colors["error"], font=('Helvetica', 11, 'bold'))
            feedback_text.tag_config("label", foreground=self.colors["text"])
            feedback_text.tag_config("user_answer", foreground=self.colors["primary"])
            feedback_text.tag_config("correct_word", foreground=self.colors["success"])
            feedback_text.tag_config("wrong_word", foreground=self.colors["error"])
            feedback_text.tag_config("missing_word", foreground=self.colors["warning"])
            feedback_text.tag_config("hint", foreground=self.colors["secondary_text"])
            feedback_text.tag_config("correct_answer", foreground=self.colors["success"])
            
            feedback_text.config(state=tk.DISABLED)

        def show_hint():
            """Показ подсказки"""
            words = correct_answer.split()
            hint = ' '.join(word[0] + '_' * (len(word)-1) for word in words)
            
            feedback_text.config(state=tk.NORMAL)
            feedback_text.delete(1.0, tk.END)
            feedback_text.insert(tk.END, "💡 Подсказка:\n", "hint_title")
            feedback_text.insert(tk.END, hint, "hint_text")
            
            feedback_text.tag_config("hint_title", foreground=self.colors["hint"], font=('Helvetica', 11, 'bold'))
            feedback_text.tag_config("hint_text", foreground=self.colors["secondary_text"])
            
            feedback_text.config(state=tk.DISABLED)

        # Кнопки управления
        button_frame = ttk.Frame(exercise_container)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        check_button = ttk.Button(
            button_frame,
            text="✓ Проверить",
            command=check_answer,
            width=15,
            style="Check.TButton"
        )
        check_button.pack(side=tk.LEFT, padx=5)
        
        hint_button = ttk.Button(
            button_frame,
            text="💡 Подсказка",
            command=show_hint,
            width=15,
            style="Hint.TButton"
        )
        hint_button.pack(side=tk.LEFT, padx=5)
        
        next_button = ttk.Button(
            button_frame,
            text="➡️ Далее",
            command=lambda: self.next_exercise(
                current_word_index,
                words_to_review,
                exercise_frame,
                progress_label,
                stats_label
            ),
            state=tk.DISABLED,
            width=15,
            style="Main.TButton"
        )
        next_button.pack(side=tk.LEFT, padx=5)

        # Исходная привязка Enter к проверке ответа
        answer_entry.bind('<Return>', check_answer)

        # Гарантируем, что кнопки будут видимыми
        button_frame.update_idletasks()
        
    # def show_exercise(self, current_word_index, words_to_review, exercise_frame, progress_label, stats_label=None):
        # """Показ упражнения для текущего слова"""
        # # Очищаем фрейм
        # for widget in exercise_frame.winfo_children():
            # widget.destroy()

        # # Получаем текущее слово
        # word_info = words_to_review[current_word_index["value"]]
        # word = word_info["word"]
        # data = word_info["data"]
        # example = random.choice(data["примеры"])
        
        # # Определяем направление перевода
        # if self.translation_direction.get() == "ru_to_it":
            # question = example["русский"]
            # correct_answer = example["итальянский"]
            # alternatives = example.get("альтернативы_ит", [])
        # else:
            # question = example["итальянский"]
            # correct_answer = example["русский"]
            # alternatives = example.get("альтернативы_рус", [])

        # # Обновляем прогресс
        # if progress_label:
            # progress_label.config(
                # text=f"Слово {current_word_index['value'] + 1} из {len(words_to_review)}"
            # )

        # # Создаем контейнер упражнения
        # exercise_container = ttk.Frame(exercise_frame, padding="20")
        # exercise_container.pack(fill=tk.BOTH, expand=True)

        # # Слово и перевод
        # word_frame = ttk.Frame(exercise_container)
        # word_frame.pack(fill=tk.X, pady=(0, 20))
        
        # word_label = ttk.Label(
            # word_frame,
            # text=word,
            # font=('Helvetica', 16, 'bold'),
            # foreground=self.colors["primary"]
        # )
        # word_label.pack(side=tk.LEFT, padx=5)
        
        # translation_label = ttk.Label(
            # word_frame,
            # text=f"- {data['перевод']}",
            # font=('Helvetica', 14)
        # )
        # translation_label.pack(side=tk.LEFT)

        # # # Задание
        # # task_frame = ttk.LabelFrame(
            # # exercise_container,
            # # text="Задание",
            # # padding="10"
        # # )
        # # task_frame.pack(fill=tk.X, pady=(0, 20))
        
        # # ttk.Label(
            # # task_frame,
            # # text="Переведите:",
            # # font=('Helvetica', 11)
        # # ).pack()
        
        # # ttk.Label(
            # # task_frame,
            # # text=question,
            # # font=('Helvetica', 12, 'bold'),
            # # wraplength=600
        # # ).pack(pady=(5, 0))
        
        # # Задание
        # task_frame = ttk.LabelFrame(
            # exercise_container,
            # text="Задание",
            # padding="10"
        # )
        # task_frame.pack(fill=tk.X, pady=(0, 20))
        
        # ttk.Label(
            # task_frame,
            # text="Переведите:",
            # font=('Helvetica', 11, 'bold'),  # Добавил bold
            # foreground=self.colors["primary"]  # Теперь синий цвет
        # ).pack()
        
        # ttk.Label(
            # task_frame,
            # text=question,
            # font=('Helvetica', 12, 'bold'),
            # wraplength=600
        # ).pack(pady=(5, 0))
        
        # # Поле ввода
        # entry_frame = ttk.Frame(exercise_container)
        # entry_frame.pack(fill=tk.X, pady=(0, 10))
        
        # answer_var = tk.StringVar()
        # answer_entry = ttk.Entry(
            # entry_frame,
            # textvariable=answer_var,
            # font=('Helvetica', 12),
            # width=50
        # )
        # answer_entry.pack(pady=(0, 10))
        # answer_entry.focus()

        # # Область обратной связи
        # feedback_frame = ttk.Frame(exercise_container)
        # feedback_frame.pack(fill=tk.X, pady=(0, 20))
        
        # feedback_text = tk.Text(
            # feedback_frame,
            # height=4,
            # width=50,
            # wrap=tk.WORD,
            # font=('Helvetica', 11),
            # borderwidth=1,
            # relief="solid",
            # padx=10,
            # pady=5
        # )
        # feedback_text.pack(fill=tk.X)
        # feedback_text.config(state=tk.DISABLED)

        def check_answer(event=None):
            """Проверка ответа пользователя"""
            user_answer = answer_var.get().strip()
            
            feedback_text.config(state=tk.NORMAL)
            feedback_text.delete(1.0, tk.END)
            
            if self.check_answer_with_variants(user_answer, correct_answer, alternatives):
                # Правильный ответ
                feedback_text.insert(tk.END, "✅ Правильно!\n", "correct")
                feedback_text.insert(tk.END, f"\nВаш ответ: {user_answer}", "user_answer")
                
                # Активируем кнопку "Далее"
                next_button.config(state=tk.NORMAL)
                
                # Удаляем старые привязки Enter
                answer_entry.unbind('<Return>')
                
                # Функция для следующего упражнения
                def go_to_next(event=None):
                    if next_button['state'] == 'normal':  # Проверяем, активна ли кнопка
                        self.next_exercise(
                            current_word_index,
                            words_to_review,
                            exercise_frame,
                            progress_label,
                            stats_label
                        )
                
                # Привязываем Enter к следующему упражнению только после правильного ответа
                exercise_frame.bind('<Return>', go_to_next)
                
                # Деактивируем остальные элементы
                answer_entry.config(state=tk.DISABLED)
                check_button.config(state=tk.DISABLED)
                hint_button.config(state=tk.DISABLED)
                
                # Устанавливаем фокус на кнопку "Далее"
                next_button.focus_set()
            else:
                # Неправильный ответ
                feedback_text.insert(tk.END, "❌ Ошибка в ответе:\n\n", "error")
                
                # Разбиваем ответы на слова
                user_words = user_answer.split()
                correct_words = correct_answer.split()
                
                # Сравниваем слово за словом
                feedback_text.insert(tk.END, "Проверка по словам:\n", "label")
                for i, user_word in enumerate(user_words):
                    if i < len(correct_words):
                        # Нормализуем слова для сравнения
                        norm_user = self.normalize_italian_text(user_word)
                        norm_correct = self.normalize_italian_text(correct_words[i])
                        
                        if norm_user == norm_correct:
                            feedback_text.insert(tk.END, f"{user_word} ✓  ", "correct_word")
                        else:
                            feedback_text.insert(tk.END, f"{user_word} ❌ ", "wrong_word")
                            feedback_text.insert(tk.END, f"(ожидается: {correct_words[i]})\n", "hint")
                    else:
                        feedback_text.insert(tk.END, f"{user_word} ❌ (лишнее слово)\n", "wrong_word")
                
                # Показываем пропущенные слова
                if len(correct_words) > len(user_words):
                    feedback_text.insert(tk.END, "\nПропущены слова: ", "label")
                    for i in range(len(user_words), len(correct_words)):
                        feedback_text.insert(tk.END, f"{correct_words[i]} ", "missing_word")
                
                feedback_text.insert(tk.END, "\n\nПравильный вариант: ", "label")
                feedback_text.insert(tk.END, correct_answer, "correct_answer")

            # Настройка тегов форматирования
            feedback_text.tag_config("correct", foreground=self.colors["success"], font=('Helvetica', 11, 'bold'))
            feedback_text.tag_config("error", foreground=self.colors["error"], font=('Helvetica', 11, 'bold'))
            feedback_text.tag_config("label", foreground=self.colors["text"])
            feedback_text.tag_config("user_answer", foreground=self.colors["primary"])
            feedback_text.tag_config("correct_word", foreground=self.colors["success"])
            feedback_text.tag_config("wrong_word", foreground=self.colors["error"])
            feedback_text.tag_config("missing_word", foreground=self.colors["warning"])
            feedback_text.tag_config("hint", foreground=self.colors["secondary_text"])
            feedback_text.tag_config("correct_answer", foreground=self.colors["success"])
            
            feedback_text.config(state=tk.DISABLED)
        # def check_answer(event=None):
            # """Проверка ответа пользователя"""
            # user_answer = answer_var.get().strip()
            
            # feedback_text.config(state=tk.NORMAL)
            # feedback_text.delete(1.0, tk.END)
            
            # if self.check_answer_with_variants(user_answer, correct_answer, alternatives):
                # # Правильный ответ
                # feedback_text.insert(tk.END, "✅ Правильно!\n", "correct")
                # feedback_text.insert(tk.END, f"\nВаш ответ: {user_answer}", "user_answer")
                
                # # Активируем кнопку "Далее"
                # next_button.config(state=tk.NORMAL)
                
                # # Отключаем все существующие привязки Enter
                # exercise_container.unbind_all('<Return>')
                # answer_entry.unbind_all('<Return>')
                
                # # Функция для обработки Enter
                # def next_on_enter(event):
                    # self.next_exercise(
                        # current_word_index,
                        # words_to_review,
                        # exercise_frame,
                        # progress_label,
                        # stats_label
                    # )
                
                # # Привязываем Enter ко всем возможным виджетам
                # exercise_container.bind_all('<Return>', next_on_enter)
                
                # # Деактивируем остальные элементы
                # answer_entry.config(state=tk.DISABLED)
                # check_button.config(state=tk.DISABLED)
                # hint_button.config(state=tk.DISABLED)
                
                # # Устанавливаем фокус на кнопку "Далее"
                # next_button.focus_set()
            # else:
                # # Неправильный ответ
                # feedback_text.insert(tk.END, "❌ Ошибка в ответе:\n\n", "error")
                
                # # Разбиваем ответы на слова
                # user_words = user_answer.split()
                # correct_words = correct_answer.split()
                
                # # Сравниваем слово за словом
                # feedback_text.insert(tk.END, "Проверка по словам:\n", "label")
                # for i, user_word in enumerate(user_words):
                    # if i < len(correct_words):
                        # # Нормализуем слова для сравнения
                        # norm_user = self.normalize_italian_text(user_word)
                        # norm_correct = self.normalize_italian_text(correct_words[i])
                        
                        # if norm_user == norm_correct:
                            # feedback_text.insert(tk.END, f"{user_word} ✓  ", "correct_word")
                        # else:
                            # feedback_text.insert(tk.END, f"{user_word} ❌ ", "wrong_word")
                            # feedback_text.insert(tk.END, f"(ожидается: {correct_words[i]})\n", "hint")
                    # else:
                        # feedback_text.insert(tk.END, f"{user_word} ❌ (лишнее слово)\n", "wrong_word")
                
                # # Показываем пропущенные слова
                # if len(correct_words) > len(user_words):
                    # feedback_text.insert(tk.END, "\nПропущены слова: ", "label")
                    # for i in range(len(user_words), len(correct_words)):
                        # feedback_text.insert(tk.END, f"{correct_words[i]} ", "missing_word")
                
                # feedback_text.insert(tk.END, "\n\nПравильный вариант: ", "label")
                # feedback_text.insert(tk.END, correct_answer, "correct_answer")

            # # Настройка тегов форматирования
            # feedback_text.tag_config("correct", foreground=self.colors["success"], font=('Helvetica', 11, 'bold'))
            # feedback_text.tag_config("error", foreground=self.colors["error"], font=('Helvetica', 11, 'bold'))
            # feedback_text.tag_config("label", foreground=self.colors["text"])
            # feedback_text.tag_config("user_answer", foreground=self.colors["primary"])
            # feedback_text.tag_config("correct_word", foreground=self.colors["success"])
            # feedback_text.tag_config("wrong_word", foreground=self.colors["error"])
            # feedback_text.tag_config("missing_word", foreground=self.colors["warning"])
            # feedback_text.tag_config("hint", foreground=self.colors["secondary_text"])
            # feedback_text.tag_config("correct_answer", foreground=self.colors["success"])
            
            # feedback_text.config(state=tk.DISABLED)
        # # def check_answer(event=None):
            # """Проверка ответа пользователя"""
            # user_answer = answer_var.get().strip()
            
            # feedback_text.config(state=tk.NORMAL)
            # feedback_text.delete(1.0, tk.END)
            
            # if self.check_answer_with_variants(user_answer, correct_answer, alternatives):
                # # Правильный ответ
                # feedback_text.insert(tk.END, "✅ Правильно!\n", "correct")
                # feedback_text.insert(tk.END, f"\nВаш ответ: {user_answer}", "user_answer")
                
                # # Активируем кнопку "Далее"
                # next_button.config(state=tk.NORMAL)
                
                # # Отключаем Enter для поля ввода и включаем для кнопки "Далее"
                # answer_entry.unbind('<Return>')
                # exercise_frame.focus_set()
                # exercise_frame.bind('<Return>', lambda e: next_button.invoke())
                
                # # Деактивируем остальные элементы
                # answer_entry.config(state=tk.DISABLED)
                # check_button.config(state=tk.DISABLED)
                # hint_button.config(state=tk.DISABLED)
                
                # # Фокус на кнопку "Далее"
                # next_button.focus_set()
            # else:
                # # Неправильный ответ
                # feedback_text.insert(tk.END, "❌ Ошибка в ответе:\n\n", "error")
                
                # # Разбиваем ответы на слова
                # user_words = user_answer.split()
                # correct_words = correct_answer.split()
                
                # # Сравниваем слово за словом
                # feedback_text.insert(tk.END, "Проверка по словам:\n", "label")
                # for i, user_word in enumerate(user_words):
                    # if i < len(correct_words):
                        # # Нормализуем слова для сравнения
                        # norm_user = self.normalize_italian_text(user_word)
                        # norm_correct = self.normalize_italian_text(correct_words[i])
                        
                        # if norm_user == norm_correct:
                            # feedback_text.insert(tk.END, f"{user_word} ✓  ", "correct_word")
                        # else:
                            # feedback_text.insert(tk.END, f"{user_word} ❌ ", "wrong_word")
                            # feedback_text.insert(tk.END, f"(ожидается: {correct_words[i]})\n", "hint")
                    # else:
                        # feedback_text.insert(tk.END, f"{user_word} ❌ (лишнее слово)\n", "wrong_word")
                
                # # Показываем пропущенные слова
                # if len(correct_words) > len(user_words):
                    # feedback_text.insert(tk.END, "\nПропущены слова: ", "label")
                    # for i in range(len(user_words), len(correct_words)):
                        # feedback_text.insert(tk.END, f"{correct_words[i]} ", "missing_word")
                
                # feedback_text.insert(tk.END, "\n\nПравильный вариант: ", "label")
                # feedback_text.insert(tk.END, correct_answer, "correct_answer")

            # # Настройка тегов форматирования
            # feedback_text.tag_config("correct", foreground=self.colors["success"], font=('Helvetica', 11, 'bold'))
            # feedback_text.tag_config("error", foreground=self.colors["error"], font=('Helvetica', 11, 'bold'))
            # feedback_text.tag_config("label", foreground=self.colors["text"])
            # feedback_text.tag_config("user_answer", foreground=self.colors["primary"])
            # feedback_text.tag_config("correct_word", foreground=self.colors["success"])
            # feedback_text.tag_config("wrong_word", foreground=self.colors["error"])
            # feedback_text.tag_config("missing_word", foreground=self.colors["warning"])
            # feedback_text.tag_config("hint", foreground=self.colors["secondary_text"])
            # feedback_text.tag_config("correct_answer", foreground=self.colors["success"])
            
            # feedback_text.config(state=tk.DISABLED)
        # def check_answer(event=None):
            # """Проверка ответа пользователя"""
            # user_answer = answer_var.get().strip()
            
            # feedback_text.config(state=tk.NORMAL)
            # feedback_text.delete(1.0, tk.END)
            
            # if self.check_answer_with_variants(user_answer, correct_answer, alternatives):
                # # Правильный ответ
                # feedback_text.insert(tk.END, "✅ Правильно!\n", "correct")
                # feedback_text.insert(tk.END, f"\nВаш ответ: {user_answer}", "user_answer")
                
                # # Активируем кнопку "Далее"
                # next_button.config(state=tk.NORMAL)
                
                # # Отвязываем Enter от проверки ответа
                # answer_entry.unbind('<Return>')
                
                # # Привязываем Enter к кнопке "Далее"
                # def handle_enter(event):
                    # if next_button['state'] == 'normal':
                        # self.next_exercise(
                            # current_word_index,
                            # words_to_review,
                            # exercise_frame,
                            # progress_label,
                            # stats_label
                        # )
                
                # exercise_frame.focus_set()
                # exercise_frame.bind('<Return>', handle_enter)
                
                # # Деактивируем остальные элементы
                # answer_entry.config(state=tk.DISABLED)
                # check_button.config(state=tk.DISABLED)
                # hint_button.config(state=tk.DISABLED)
                
                # # Устанавливаем фокус на кнопку "Далее"
                # next_button.focus_set()
            # # else:
                # # # ... остальной код для неправильного ответа ...

        # # # Привязка Enter к проверке ответа изначально
        # # answer_entry.bind('<Return>', check_answer)
        
        # # def check_answer(event=None):
            # # """Проверка ответа пользователя"""
            # # user_answer = answer_var.get().strip()
            
            # # feedback_text.config(state=tk.NORMAL)
            # # feedback_text.delete(1.0, tk.END)
            
            # # if self.check_answer_with_variants(user_answer, correct_answer, alternatives):
                # # # Правильный ответ
                # # feedback_text.insert(tk.END, "✅ Правильно!\n", "correct")
                # # feedback_text.insert(tk.END, f"\nВаш ответ: {user_answer}", "user_answer")
                
                # # # Активируем кнопку "Далее" и переключаем на неё фокус
                # # next_button.config(state=tk.NORMAL)
                # # next_button.focus_set()
                
                # # # Привязываем Enter к кнопке "Далее"
                # # exercise_frame.bind('<Return>', lambda e: next_button.invoke())
                
                # # answer_entry.config(state=tk.DISABLED)
                # # check_button.config(state=tk.DISABLED)
                # # hint_button.config(state=tk.DISABLED)
        # # def check_answer(event=None):
            # # """Проверка ответа пользователя"""
            # # user_answer = answer_var.get().strip()
            
            # # feedback_text.config(state=tk.NORMAL)
            # # feedback_text.delete(1.0, tk.END)
            
            # # if self.check_answer_with_variants(user_answer, correct_answer, alternatives):
                # # # Правильный ответ
                # # feedback_text.insert(tk.END, "✅ Правильно!\n", "correct")
                # # feedback_text.insert(tk.END, f"\nВаш ответ: {user_answer}", "user_answer")
                
                # # # Активируем кнопку "Далее"
                # # next_button.config(state=tk.NORMAL)
                # # next_button.focus_set()
                
                # # # Деактивируем остальные элементы
                # # answer_entry.config(state=tk.DISABLED)
                # # check_button.config(state=tk.DISABLED)
                # # hint_button.config(state=tk.DISABLED)
            # else:
                # # Неправильный ответ
                # feedback_text.insert(tk.END, "❌ Ошибка в ответе:\n\n", "error")
                
                # # Разбиваем ответы на слова
                # user_words = user_answer.split()
                # correct_words = correct_answer.split()
                
                # # Сравниваем слово за словом
                # feedback_text.insert(tk.END, "Проверка по словам:\n", "label")
                # for i, user_word in enumerate(user_words):
                    # if i < len(correct_words):
                        # # Нормализуем слова для сравнения
                        # norm_user = self.normalize_italian_text(user_word)
                        # norm_correct = self.normalize_italian_text(correct_words[i])
                        
                        # if norm_user == norm_correct:
                            # feedback_text.insert(tk.END, f"{user_word} ✓  ", "correct_word")
                        # else:
                            # feedback_text.insert(tk.END, f"{user_word} ❌ ", "wrong_word")
                            # feedback_text.insert(tk.END, f"(ожидается: {correct_words[i]})\n", "hint")
                    # else:
                        # feedback_text.insert(tk.END, f"{user_word} ❌ (лишнее слово)\n", "wrong_word")
                
                # # Показываем пропущенные слова
                # if len(correct_words) > len(user_words):
                    # feedback_text.insert(tk.END, "\nПропущены слова: ", "label")
                    # for i in range(len(user_words), len(correct_words)):
                        # feedback_text.insert(tk.END, f"{correct_words[i]} ", "missing_word")
                
                # feedback_text.insert(tk.END, "\n\nПравильный вариант: ", "label")
                # feedback_text.insert(tk.END, correct_answer, "correct_answer")

            # # Настройка тегов форматирования
            # feedback_text.tag_config("correct", foreground=self.colors["success"], font=('Helvetica', 11, 'bold'))
            # feedback_text.tag_config("error", foreground=self.colors["error"], font=('Helvetica', 11, 'bold'))
            # feedback_text.tag_config("label", foreground=self.colors["text"])
            # feedback_text.tag_config("user_answer", foreground=self.colors["primary"])
            # feedback_text.tag_config("correct_word", foreground=self.colors["success"])
            # feedback_text.tag_config("wrong_word", foreground=self.colors["error"])
            # feedback_text.tag_config("missing_word", foreground=self.colors["warning"])
            # feedback_text.tag_config("hint", foreground=self.colors["secondary_text"])
            # feedback_text.tag_config("correct_answer", foreground=self.colors["success"])
            
            # feedback_text.config(state=tk.DISABLED)

        def show_hint():
            """Показ подсказки"""
            words = correct_answer.split()
            hint = ' '.join(word[0] + '_' * (len(word)-1) for word in words)
            
            feedback_text.config(state=tk.NORMAL)
            feedback_text.delete(1.0, tk.END)
            feedback_text.insert(tk.END, "💡 Подсказка:\n", "hint_title")
            feedback_text.insert(tk.END, hint, "hint_text")
            
            feedback_text.tag_config("hint_title", foreground=self.colors["hint"])
            feedback_text.tag_config("hint_text", foreground=self.colors["secondary_text"])
            
            feedback_text.config(state=tk.DISABLED)

        # Кнопки управления
        button_frame = ttk.Frame(exercise_container)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        check_button = ttk.Button(
            button_frame,
            text="✓ Проверить",
            command=check_answer,
            width=15,
            style="Check.TButton"
        )
        check_button.pack(side=tk.LEFT, padx=5)
        
        hint_button = ttk.Button(
            button_frame,
            text="💡 Подсказка",
            command=show_hint,
            width=15,
            style="Hint.TButton"
        )
        hint_button.pack(side=tk.LEFT, padx=5)
        
        next_button = ttk.Button(
            button_frame,
            text="➡️ Далее",
            command=lambda: self.next_exercise(
                current_word_index,
                words_to_review,
                exercise_frame,
                progress_label,
                stats_label
            ),
            state=tk.DISABLED,
            width=15,
            style="Main.TButton"
        )
        next_button.pack(side=tk.LEFT, padx=5)

        # Привязка Enter к проверке ответа
        answer_entry.bind('<Return>', check_answer)
        
        # Гарантируем, что кнопки будут видимыми
        button_frame.update_idletasks()
        
    def start_review(self):
        """Открытие окна повторения"""
        current_time = datetime.datetime.now()
        
        try:
            with open('schedule.json', 'r', encoding='utf-8') as f:
                schedule = json.load(f)
        except FileNotFoundError:
            messagebox.showerror(
                "Ошибка",
                "Файл расписания не найден.\nОбновите расписание."
            )
            return
        except json.JSONDecodeError:
            messagebox.showerror(
                "Ошибка",
                "Ошибка чтения файла расписания.\nФайл может быть повреждён."
            )
            return

        # Находим слова для повторения
        words_to_review = []
        future_words = []
        
        for word_data in schedule["words"]:
            try:
                next_review = datetime.datetime.fromisoformat(word_data["next_review"])
                word = word_data["word"]
                
                # Отдельная проверка для il progetto - всегда в срочных
                if word == "il progetto":
                    if word in self.vocabulary["Буду изучать"]:
                        words_to_review.append({
                            "word": word,
                            "data": self.vocabulary["Буду изучать"][word],
                            "schedule_data": word_data
                        })
                    continue

                # Проверяем остальные слова
                if word in self.vocabulary["Буду изучать"]:
                    if next_review <= current_time:
                        words_to_review.append({
                            "word": word,
                            "data": self.vocabulary["Буду изучать"][word],
                            "schedule_data": word_data
                        })
                    else:
                        future_words.append({
                            "word": word,
                            "data": self.vocabulary["Буду изучать"][word],
                            "schedule_data": word_data
                        })
            except (ValueError, KeyError) as e:
                print(f"Ошибка обработки слова {word_data.get('word', 'unknown')}: {e}")
                continue

        # Если нет срочных слов, предлагаем будущие
        if not words_to_review:
            if future_words:
                if messagebox.askyesno(
                    "Информация",
                    "Сейчас нет слов для срочного повторения.\nХотите начать изучение предстоящих слов?"
                ):
                    words_to_review = future_words
                else:
                    return
            else:
                messagebox.showinfo(
                    "Информация",
                    "Нет слов для изучения.\nДобавьте новые слова в расписание."
                )
                return

        # Создание окна повторения
        review_window, main_frame = self.create_review_window(words_to_review)
        
        # Заголовок
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        ttk.Label(
            header_frame,
            text="Повторение слов",
            style="Header.TLabel"
        ).pack()
        
        # Переключатель направления перевода
        direction_frame = ttk.LabelFrame(
            main_frame,
            text="Направление перевода",
            padding="10"
        )
        direction_frame.grid(row=1, column=0, columnspan=2, pady=(0, 20), sticky=(tk.W, tk.E))
        
        self.translation_direction = tk.StringVar(value="ru_to_it")
        
        ttk.Radiobutton(
            direction_frame,
            text="Русский → Итальянский",
            variable=self.translation_direction,
            value="ru_to_it",
            command=lambda: self.show_exercise(
                current_word_index,
                words_to_review,
                exercise_frame,
                progress_label,
                stats_label
            )
        ).pack(side=tk.LEFT, padx=20)
        
        ttk.Radiobutton(
            direction_frame,
            text="Итальянский → Русский",
            variable=self.translation_direction,
            value="it_to_ru",
            command=lambda: self.show_exercise(
                current_word_index,
                words_to_review,
                exercise_frame,
                progress_label,
                stats_label
            )
        ).pack(side=tk.LEFT, padx=20)

        # Фрейм для упражнений
        exercise_frame = ttk.Frame(main_frame)
        exercise_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky=(tk.W, tk.E, tk.N, tk.S),
            pady=(0, 20)
        )
        exercise_frame.columnconfigure(0, weight=1)
        
        # Текущий индекс слова
        current_word_index = {"value": 0}
        
        # Прогресс
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        progress_label = ttk.Label(
            progress_frame,
            text=f"Слово {current_word_index['value'] + 1} из {len(words_to_review)}",
            style="Main.TLabel"
        )
        progress_label.pack(side=tk.LEFT)
        
        # Статистика
        stats_label = ttk.Label(
            progress_frame,
            text="",
            style="Main.TLabel"
        )
        stats_label.pack(side=tk.RIGHT)
        
        # Показываем первое упражнение
        self.show_exercise(
            current_word_index,
            words_to_review,
            exercise_frame,
            progress_label,
            stats_label
        )
    
    def next_exercise(self, current_word_index, words_to_review, exercise_frame, progress_label, stats_label=None):
        """Переход к следующему упражнению"""
        try:
            with open('schedule.json', 'r', encoding='utf-8') as f:
                schedule = json.load(f)
            
            current_word = words_to_review[current_word_index["value"]]
            
            # Находим слово в расписании и обновляем время
            for word_data in schedule["words"]:
                if word_data["word"] == current_word["word"]:
                    # Устанавливаем время следующего повторения через 4 часа для всех слов
                    next_review = (datetime.datetime.now() + 
                                 datetime.timedelta(hours=4)).isoformat()
                    word_data["next_review"] = next_review
                    break
            
            # Сохраняем обновленное расписание
            with open('schedule.json', 'w', encoding='utf-8') as f:
                json.dump(schedule, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            print(f"Ошибка при обновлении расписания: {e}")

        # Увеличиваем индекс текущего слова
        current_word_index["value"] += 1
        
        if current_word_index["value"] >= len(words_to_review):
            # Завершаем сессию
            messagebox.showinfo(
                "Поздравляем!",
                "Вы успешно завершили все упражнения для повторения! 🎉"
            )
            # Закрываем окно повторения
            exercise_frame.master.master.destroy()
            # Обновляем главное окно
            self.load_schedule()
        else:
            # Показываем следующее упражнение
            self.show_exercise(
                current_word_index,
                words_to_review,
                exercise_frame,
                progress_label,
                stats_label
            )
            
    # def next_exercise(self, current_word_index, words_to_review, exercise_frame, progress_label, stats_label=None):
        # """Переход к следующему упражнению"""
        # try:
            # with open('schedule.json', 'r', encoding='utf-8') as f:
                # schedule = json.load(f)
            
            # current_word = words_to_review[current_word_index["value"]]
            
            # # Находим слово в расписании и обновляем время
            # for word_data in schedule["words"]:
                # if word_data["word"] == current_word["word"]:
                    # # Для il progetto оставляем текущее время
                    # if word_data["word"] == "il progetto":
                        # next_review = datetime.datetime.now().isoformat()
                    # else:
                        # next_review = (datetime.datetime.now() + 
                                     # datetime.timedelta(hours=4)).isoformat()
                    # word_data["next_review"] = next_review
                    # break
            
            # # Сохраняем обновленное расписание
            # with open('schedule.json', 'w', encoding='utf-8') as f:
                # json.dump(schedule, f, ensure_ascii=False, indent=2)
        
        # except Exception as e:
            # print(f"Ошибка при обновлении расписания: {e}")

        # # Увеличиваем индекс текущего слова
        # current_word_index["value"] += 1
        
        # if current_word_index["value"] >= len(words_to_review):
            # # Завершаем сессию
            # messagebox.showinfo(
                # "Поздравляем!",
                # "Вы успешно завершили все упражнения для повторения! 🎉"
            # )
            # # Закрываем окно повторения
            # exercise_frame.master.master.destroy()
            # # Обновляем главное окно
            # self.load_schedule()
        # else:
            # # Показываем следующее упражнение
            # self.show_exercise(
                # current_word_index,
                # words_to_review,
                # exercise_frame,
                # progress_label,
                # stats_label
            # )

    def run(self):
        """Запуск приложения"""
        def on_closing():
            """Обработка закрытия окна"""
            if messagebox.askokcancel("Выход", "Вы действительно хотите выйти?"):
                try:
                    self.root.quit()
                    self.root.destroy()
                except:
                    pass

        # Привязываем обработчик к событию закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Центрируем главное окно
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Запускаем главный цикл приложения
        self.root.mainloop()


if __name__ == "__main__":
    app = ItalianLearningApp()
    app.run()