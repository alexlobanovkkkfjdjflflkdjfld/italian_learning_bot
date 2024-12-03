# main.py

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import datetime
from plyer import notification
import threading
import time
import random

class ItalianLearningApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Изучение итальянского языка")
        self.root.geometry("600x500")
        
        # Словарь с данными
        self.vocabulary = {
            "Изучаю": {},
            "Буду изучать": {
                "il colloquio": {
                    "перевод": "собеседование",
                    "примеры": [
                        {
                            "русский": "У меня собеседование в понедельник утром",
                            "итальянский": "Ho un colloquio lunedì mattina",
                            "альтернативы_рус": ["У меня встреча в понедельник утром"],
                            "альтернативы_ит": ["Ho il colloquio lunedì mattina"]
                        }
                    ]
                },
                "l'esperienza": {
                    "перевод": "опыт",
                    "примеры": [
                        {
                            "русский": "У меня большой опыт работы",
                            "итальянский": "Ho molta esperienza di lavoro",
                            "альтернативы_рус": ["Я имею большой опыт работы"],
                            "альтернативы_ит": ["Ho una grande esperienza di lavoro"]
                        }
                    ]
                },
                "la riunione": {
                    "перевод": "совещание",
                    "примеры": [
                        {
                            "русский": "Совещание начнется через час",
                            "итальянский": "La riunione inizierà tra un'ora",
                            "альтернативы_рус": ["Встреча начнется через час"],
                            "альтернативы_ит": ["La riunione comincerà tra un'ora"]
                        }
                    ]
                },
                "il progetto": {
                    "перевод": "проект",
                    "примеры": [
                        {
                            "русский": "Я работаю над важным проектом",
                            "итальянский": "Sto lavorando su un progetto importante",
                            "альтернативы_рус": ["Я занимаюсь важным проектом"],
                            "альтернативы_ит": ["Lavoro su un progetto importante"]
                        }
                    ]
                }
            },
            "Изучил": {}
        }
        
        self.setup_ui()
        self.load_schedule()
        self.start_auto_update()

    def setup_ui(self):
        """Создание пользовательского интерфейса"""
        # Основной фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Заголовок
        title_label = ttk.Label(
            main_frame,
            text="Расписание повторений",
            font=('Helvetica', 14, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Область расписания
        self.schedule_text = tk.Text(
            main_frame,
            height=12,
            width=60,
            font=('Courier', 11)
        )
        self.schedule_text.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        # Кнопки
        refresh_btn = ttk.Button(
            main_frame,
            text="Обновить",
            command=self.load_schedule,
            width=20
        )
        refresh_btn.grid(row=2, column=0, padx=5, pady=5)
        
        start_btn = ttk.Button(
            main_frame,
            text="Начать повторение",
            command=self.start_review,
            width=20
        )
        start_btn.grid(row=2, column=1, padx=5, pady=5)
        
        # Статус
        self.status_label = ttk.Label(
            main_frame,
            text="",
            font=('Helvetica', 10)
        )
        self.status_label.grid(row=3, column=0, columnspan=2, pady=5)
        
        # Добавляем полосу прокрутки для расписания
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.schedule_text.yview)
        scrollbar.grid(row=1, column=2, sticky="ns")
        self.schedule_text.configure(yscrollcommand=scrollbar.set)
    def load_schedule(self):
        """Загрузка и отображение расписания"""
        self.schedule_text.delete('1.0', tk.END)
        current_time = datetime.datetime.now()
        
        schedule_file = 'schedule.json'
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                schedule = json.load(f)
        except FileNotFoundError:
            # Создаем тестовое расписание для первого запуска
            test_words = [
                ("il colloquio", 1),    # через 1 минуту
                ("l'esperienza", 5),    # через 5 минут
                ("la riunione", 10),    # через 10 минут
                ("il progetto", 15)     # через 15 минут
            ]
            schedule = {"words": []}
            for word, minutes in test_words:
                schedule["words"].append({
                    "word": word,
                    "translation": self.vocabulary["Буду изучать"][word]["перевод"],
                    "next_review": (current_time + datetime.timedelta(minutes=minutes)).isoformat()
                })
            
            with open(schedule_file, 'w', encoding='utf-8') as f:
                json.dump(schedule, f, ensure_ascii=False, indent=2)
        
        due_words = []  # слова, которые пора повторить
        future_words = []  # слова для будущего повторения
        
        for word in schedule["words"]:
            next_review = datetime.datetime.fromisoformat(word["next_review"])
            time_diff = next_review - current_time
            
            if next_review <= current_time:
                due_words.append(word)
            else:
                hours = int(time_diff.total_seconds() // 3600)
                minutes = int((time_diff.total_seconds() % 3600) // 60)
                word_info = {
                    "word": word,
                    "hours": hours,
                    "minutes": minutes
                }
                future_words.append(word_info)
        
        # Сначала показываем слова, которые пора повторить
        if due_words:
            self.schedule_text.insert(tk.END, "=== ПОРА ПОВТОРИТЬ ===\n\n")
            for word in due_words:
                self.schedule_text.insert(tk.END, 
                    f"{word['word']} - {word['translation']}\n")
                self.show_notification(word)
            self.schedule_text.insert(tk.END, "\n")
        
        # Затем показываем предстоящие повторения
        if future_words:
            self.schedule_text.insert(tk.END, "=== ПРЕДСТОЯЩИЕ ПОВТОРЕНИЯ ===\n\n")
            for word_info in sorted(future_words, key=lambda x: (x["hours"], x["minutes"])):
                word = word_info["word"]
                self.schedule_text.insert(tk.END, 
                    f"Через {word_info['hours']}ч {word_info['minutes']}мин: " +
                    f"{word['word']} - {word['translation']}\n")
        
        # Обновляем статус
        self.status_label.config(
            text=f"Последнее обновление: {current_time.strftime('%H:%M:%S')}"
        )

    def show_notification(self, word):
        """Показ уведомления Windows"""
        notification.notify(
            title='Время изучения итальянского!',
            message=f'Пора повторить слово: {word["word"]} ({word["translation"]})',
            app_icon=None,
            timeout=10
        )

    def start_auto_update(self):
        """Запуск автоматического обновления"""
        def auto_update():
            while True:
                try:
                    self.load_schedule()
                except Exception as e:
                    print(f"Ошибка при автоматическом обновлении: {e}")
                time.sleep(60)  # проверяем каждую минуту
        
        update_thread = threading.Thread(target=auto_update, daemon=True)
        update_thread.start()
    def start_review(self):
        """Открытие окна повторения"""
        current_time = datetime.datetime.now()
        
        # Получаем слова для повторения
        try:
            with open('schedule.json', 'r', encoding='utf-8') as f:
                schedule = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Ошибка", "Файл расписания не найден")
            return
        
        # Находим слова, которые пора повторить
        words_to_review = []
        for word_data in schedule["words"]:
            next_review = datetime.datetime.fromisoformat(word_data["next_review"])
            if next_review <= current_time:
                word = word_data["word"]
                if word in self.vocabulary["Буду изучать"]:
                    words_to_review.append({
                        "word": word,
                        "data": self.vocabulary["Буду изучать"][word]
                    })
        
        if not words_to_review:
            messagebox.showinfo("Информация", "Сейчас нет слов для повторения")
            return

        # Создаем окно повторения
        review_window = tk.Toplevel(self.root)
        review_window.title("Повторение слов")
        review_window.geometry("600x500")
        review_window.transient(self.root)  # Делаем окно модальным
        
        # Создаем стиль для кнопок и элементов
        style = ttk.Style()
        style.configure("Review.TButton", padding=5, font=('Helvetica', 10))
        style.configure("Review.TLabel", font=('Helvetica', 11))
        
        # Основной фрейм
        main_frame = ttk.Frame(review_window, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Заголовок
        ttk.Label(
            main_frame,
            text="Повторение слов",
            font=('Helvetica', 14, 'bold'),
            style="Review.TLabel"
        ).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Переключатель направления перевода
        direction_frame = ttk.Frame(main_frame)
        direction_frame.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        self.translation_direction = tk.StringVar(value="ru_to_it")
        
        ttk.Radiobutton(
            direction_frame,
            text="Русский → Итальянский",
            variable=self.translation_direction,
            value="ru_to_it",
            command=lambda: self.show_exercise(current_word_index, words_to_review, exercise_frame)
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(
            direction_frame,
            text="Итальянский → Русский",
            variable=self.translation_direction,
            value="it_to_ru",
            command=lambda: self.show_exercise(current_word_index, words_to_review, exercise_frame)
        ).pack(side=tk.LEFT, padx=10)
        
        # Фрейм для упражнений
        exercise_frame = ttk.Frame(main_frame)
        exercise_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Текущий индекс слова
        current_word_index = {"value": 0}
        
        # Прогресс
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=2, pady=(20, 0), sticky=(tk.W, tk.E))
        
        progress_label = ttk.Label(
            progress_frame,
            text=f"Слово {current_word_index['value'] + 1} из {len(words_to_review)}",
            style="Review.TLabel"
        )
        progress_label.pack()
        
        # Показываем первое упражнение
        self.show_exercise(current_word_index, words_to_review, exercise_frame, progress_label)

    def show_exercise(self, current_word_index, words_to_review, exercise_frame, progress_label=None):
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
            # Показываем слово и его перевод
        word_frame = ttk.Frame(exercise_frame)
        word_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(
            word_frame,
            text=f"{word}",
            font=('Helvetica', 14, 'bold')
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            word_frame,
            text=f"- {data['перевод']}",
            font=('Helvetica', 12)
        ).pack(side=tk.LEFT)
        
        # Показываем задание
        question_frame = ttk.Frame(exercise_frame)
        question_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(
            question_frame,
            text="Переведите:",
            font=('Helvetica', 11)
        ).pack()
        
        ttk.Label(
            question_frame,
            text=question,
            font=('Helvetica', 12, 'bold'),
            wraplength=400  # Перенос длинных строк
        ).pack(pady=(5, 0))
        
        # Поле для ввода ответа
        entry_frame = ttk.Frame(exercise_frame)
        entry_frame.pack(fill=tk.X, pady=(0, 20))
        
        answer_var = tk.StringVar()
        answer_entry = ttk.Entry(
            entry_frame,
            textvariable=answer_var,
            width=40,
            font=('Helvetica', 11)
        )
        answer_entry.pack(pady=(0, 10))
        answer_entry.focus()  # Устанавливаем фокус на поле ввода
        
        # Метка для обратной связи
        feedback_frame = ttk.Frame(exercise_frame)
        feedback_frame.pack(fill=tk.X, pady=(0, 20))
        
        feedback_label = ttk.Label(
            feedback_frame,
            text="",
            font=('Helvetica', 11),
            wraplength=400
        )
        feedback_label.pack()
        
        # Кнопки управления
        button_frame = ttk.Frame(exercise_frame)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        def check_answer():
            user_answer = answer_var.get().strip().lower()
            correct = correct_answer.lower()
            alt_answers = [alt.lower() for alt in alternatives]
            
            if user_answer == correct or user_answer in alt_answers:
                feedback_label.config(
                    text="Правильно! 👍",
                    foreground="green"
                )
                next_button.config(state='normal')
                answer_entry.config(state='disabled')
                check_button.config(state='disabled')
            else:
                # Подсветка различий
                import difflib
        
        def highlight_differences(user_text, correct_text):
            user_words = user_text.split()
            correct_words = correct_text.split()
            result = []
            
            matcher = difflib.SequenceMatcher(None, user_words, correct_words)
            
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'equal':
                    result.extend(user_words[i1:i2])
                elif tag == 'replace':
                    result.extend([f'<span style="color: red;">{w}</span>' 
                                 for w in user_words[i1:i2]])
                    result.extend([f'<span style="color: green;">{w}</span>' 
                                 for w in correct_words[j1:j2]])
                elif tag == 'delete':
                    result.extend([f'<span style="color: red;">{w}</span>' 
                                 for w in user_words[i1:i2]])
                elif tag == 'insert':
                    result.extend([f'<span style="color: green;">{w}</span>' 
                                 for w in correct_words[j1:j2]])
            
            return ' '.join(result)
        
        differences = highlight_differences(user_answer, correct_answer)
        feedback_text = f"""
            Попробуйте еще раз\n
            Ваш ответ: {differences}
        """
        
        feedback_label.config(
            text=feedback_text,
            foreground="black",
            justify="left",
            wraplength=400
        )
        # def check_answer():
            # user_answer = answer_var.get().strip().lower()
            # correct = correct_answer.lower()
            # alt_answers = [alt.lower() for alt in alternatives]
            
            # if user_answer == correct or user_answer in alt_answers:
                # feedback_label.config(
                    # text="Правильно! 👍",
                    # foreground="green"
                # )
                # # Активируем кнопку "Далее"
                # next_button.config(state='normal')
                # # Деактивируем поле ввода и кнопку проверки
                # answer_entry.config(state='disabled')
                # check_button.config(state='disabled')
            # else:
                # feedback_label.config(
                    # text="Попробуйте еще раз",
                    # foreground="red"
                # )
        
        # Обработка нажатия Enter в поле ввода
        def on_enter(event):
            check_answer()
        
        answer_entry.bind('<Return>', on_enter)
        
        # Кнопка проверки
        check_button = ttk.Button(
            button_frame,
            text="Проверить",
            command=check_answer,
            style="Review.TButton"
        )
        check_button.pack(side=tk.LEFT, padx=5)
        
        # Кнопка подсказки
        def show_hint():
            words = correct_answer.split()
            hint = ' '.join(word[0] + '_' * (len(word)-1) for word in words)
            feedback_label = ttk.Label(
            feedback_frame,
            text="",
            font=('Helvetica', 11),
            wraplength=400,
            justify="left"
        )
        feedback_label.pack(pady=10)

        # Добавляем стиль для HTML-текста
        style = ttk.Style()
        style.configure('Feedback.TLabel', 
                        background='white',
                        foreground='black',
                        font=('Helvetica', 11))
        feedback_label.configure(style='Feedback.TLabel')
            # feedback_label.config(
                # text=f"Подсказка: {hint}",
                # foreground="blue"
            # )
        
        hint_button = ttk.Button(
            button_frame,
            text="Подсказка",
            command=show_hint,
            style="Review.TButton"
        )
        hint_button.pack(side=tk.LEFT, padx=5)
        
        # Кнопка "Далее"
        next_button = ttk.Button(
            button_frame,
            text="Далее",
            command=lambda: self.next_exercise(
                current_word_index,
                words_to_review,
                exercise_frame,
                progress_label
            ),
            state='disabled',  # Изначально неактивна
            style="Review.TButton"
        )
        next_button.pack(side=tk.LEFT, padx=5)

    def next_exercise(self, current_word_index, words_to_review, exercise_frame, progress_label):
        """Переход к следующему упражнению"""
        current_word_index["value"] += 1
        
        if current_word_index["value"] >= len(words_to_review):
            # Завершаем сессию
            messagebox.showinfo(
                "Поздравляем!",
                "Вы завершили все упражнения для повторения!"
            )
            # Закрываем окно повторения
            exercise_frame.master.master.destroy()
        else:
            # Показываем следующее упражнение
            self.show_exercise(
                current_word_index,
                words_to_review,
                exercise_frame,
                progress_label
            )

    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


if __name__ == "__main__":
    app = ItalianLearningApp()
    app.run()