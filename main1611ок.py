import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import datetime
from plyer import notification
import threading
import time
import random
from vocabulary import VOCABULARY

class ItalianLearningApp:
    def __init__(self):
        # Инициализация основного окна
        self.root = tk.Tk()
        self.root.title("Изучение итальянского языка")
        self.root.geometry("800x600")
        
        # Загрузка словаря
        self.vocabulary = VOCABULARY
        
        # Состояние приложения
        self.is_review_active = False
        self.current_review_window = None
        
        # Настройка цветов
        self.colors = {
            "primary": "#1976D2",
            "success": "#4CAF50",
            "error": "#f44336",
            "warning": "#FFA726",
            "hint": "#673AB7",
            "background": "#FFFFFF",
            "text": "#212121",
            "secondary_text": "#757575"
        }
        
        # Инициализация интерфейса
        self.setup_styles()
        self.setup_main_window()
        self.load_schedule()
        self.start_auto_update()

    def setup_styles(self):
        """Настройка стилей приложения"""
        style = ttk.Style()
        
        style.configure(
            "Main.TButton",
            padding=10,
            font=('Helvetica', 10, 'bold')
        )
        
        style.configure(
            "Review.TButton",
            padding=8,
            font=('Helvetica', 10)
        )
        
        style.configure(
            "Main.TLabel",
            font=('Helvetica', 10),
            foreground=self.colors["text"]
        )
        
        style.configure(
            "Header.TLabel",
            font=('Helvetica', 16, 'bold'),
            foreground=self.colors["primary"]
        )

    def setup_main_window(self):
        """Создание главного окна"""
        # Основной фрейм
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Заголовок
        ttk.Label(
            self.main_frame,
            text="Изучение итальянского языка",
            style="Header.TLabel"
        ).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Область расписания
        schedule_frame = ttk.LabelFrame(
            self.main_frame,
            text="Расписание повторений",
            padding="10"
        )
        schedule_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.schedule_text = tk.Text(
            schedule_frame,
            height=15,
            width=70,
            wrap=tk.WORD,
            font=('Helvetica', 10)
        )
        self.schedule_text.pack(expand=True, fill=tk.BOTH)
        
        # Кнопки управления
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame,
            text="🔄 Обновить",
            command=self.load_schedule,
            style="Main.TButton"
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            button_frame,
            text="▶️ Начать повторение",
            command=self.start_review,
            style="Main.TButton"
        ).pack(side=tk.LEFT, padx=10)
        
        # Статус
        self.status_label = ttk.Label(
            self.main_frame,
            text="",
            style="Main.TLabel"
        )
        self.status_label.grid(row=3, column=0, columnspan=2)

    def load_schedule(self):
        """Загрузка расписания"""
        try:
            current_time = datetime.datetime.now()
            
            # Чтение или создание расписания
            try:
                with open('schedule.json', 'r', encoding='utf-8') as f:
                    schedule = json.load(f)
            except FileNotFoundError:
                schedule = self._create_initial_schedule(current_time)
            
            # Обновление отображения
            self.schedule_text.config(state=tk.NORMAL)
            self.schedule_text.delete('1.0', tk.END)
            
            # Разделение слов на категории
            urgent_words = []
            future_words = []
            
            for word in schedule["words"]:
                next_review = datetime.datetime.fromisoformat(word["next_review"])
                time_diff = next_review - current_time
                
                if time_diff.total_seconds() <= 0:
                    urgent_words.append(word)
                else:
                    future_words.append({
                        "word": word,
                        "hours": int(time_diff.total_seconds() // 3600),
                        "minutes": int((time_diff.total_seconds() % 3600) // 60)
                    })
            
            # Отображение срочных слов
            if urgent_words:
                self.schedule_text.insert(tk.END, "🔔 ПОРА ПОВТОРИТЬ:\n\n", "header")
                for word in urgent_words:
                    self.schedule_text.insert(
                        tk.END,
                        f"• {word['word']} - {word['translation']}\n",
                        "current"
                    )
                    if not self.root.focus_displayof() and not self.is_review_active:
                        self._show_notification(word)
                self.schedule_text.insert(tk.END, "\n")
            
            # Отображение будущих слов
            if future_words:
                self.schedule_text.insert(tk.END, "⏰ ПРЕДСТОЯЩИЕ ПОВТОРЕНИЯ:\n\n", "header")
                future_words.sort(key=lambda x: (x["hours"], x["minutes"]))
                for word_info in future_words:
                    word = word_info["word"]
                    time_str = f"{word_info['hours']}ч {word_info['minutes']}мин"
                    self.schedule_text.insert(
                        tk.END,
                        f"• Через {time_str}: {word['word']} - {word['translation']}\n",
                        "future"
                    )
            
            # Настройка тегов
            self.schedule_text.tag_configure(
                "header",
                font=('Helvetica', 11, 'bold'),
                foreground=self.colors["primary"]
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
            
            self.schedule_text.config(state=tk.DISABLED)
            self.status_label.config(
                text=f"Последнее обновление: {current_time.strftime('%H:%M:%S')}"
            )
            
        except Exception as e:
            messagebox.showerror(
                "Ошибка",
                "Не удалось загрузить расписание"
            )

    def _create_initial_schedule(self, current_time):
        """Создание начального расписания"""
        schedule = {"words": []}
        for i, word in enumerate(self.vocabulary["Буду изучать"].keys()):
            next_review = (current_time if i == 0 
                         else current_time + datetime.timedelta(minutes=5*i))
            schedule["words"].append({
                "word": word,
                "translation": self.vocabulary["Буду изучать"][word]["перевод"],
                "next_review": next_review.isoformat()
            })
        
        with open('schedule.json', 'w', encoding='utf-8') as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)
            
        return schedule

    def _show_notification(self, word):
        """Показ уведомления"""
        try:
            notification.notify(
                title='Время изучения итальянского!',
                message=f'Пора повторить слово: {word["word"]} ({word["translation"]})',
                timeout=10
            )
        except:
            pass  # Игнорируем ошибки уведомлений

    def start_auto_update(self):
        """Запуск автоматического обновления"""
        def auto_update():
            while True:
                try:
                    if not self.is_review_active:
                        self.root.after(0, self.load_schedule)
                    time.sleep(60)
                except:
                    time.sleep(60)
                    
        threading.Thread(target=auto_update, daemon=True).start()

    def start_review(self):
        """Запуск повторения"""
        try:
            # Проверка текущего расписания
            with open('schedule.json', 'r', encoding='utf-8') as f:
                schedule = json.load(f)
            
            # Получение слов для повторения
            current_time = datetime.datetime.now()
            words_to_review = []
            
            for word_data in schedule["words"]:
                next_review = datetime.datetime.fromisoformat(word_data["next_review"])
                if next_review <= current_time:
                    if word_data["word"] in self.vocabulary["Буду изучать"]:
                        words_to_review.append({
                            "word": word_data["word"],
                            "data": self.vocabulary["Буду изучать"][word_data["word"]],
                            "schedule_data": word_data
                        })
            
            if not words_to_review:
                messagebox.showinfo(
                    "Информация",
                    "Сейчас нет слов для повторения"
                )
                return
            
            # Создание окна повторения
            self.is_review_active = True
            self.create_review_window(words_to_review)
            
        except Exception as e:
            self.is_review_active = False
            messagebox.showerror(
                "Ошибка",
                "Не удалось начать повторение"
            )

    def create_review_window(self, words_to_review):
        """Создание окна повторения"""
        review_window = tk.Toplevel(self.root)
        review_window.title("Повторение слов")
        review_window.geometry("800x600")
        review_window.transient(self.root)
        
        self.current_review_window = review_window
        
        main_frame = ttk.Frame(review_window, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Настройка расширения
        review_window.columnconfigure(0, weight=1)
        review_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Компоненты окна повторения
        current_word_index = {"value": 0}
        self.translation_direction = tk.StringVar(value="ru_to_it")
        
        # Заголовок
        ttk.Label(
            main_frame,
            text="Повторение слов",
            style="Header.TLabel"
        ).grid(row=0, column=0, pady=(0, 20))
        
        # Переключатель направления перевода
        direction_frame = ttk.LabelFrame(
            main_frame,
            text="Направление перевода",
            padding="10"
        )
        direction_frame.grid(row=1, column=0, pady=(0, 20), sticky=(tk.W, tk.E))
        
        ttk.Radiobutton(
            direction_frame,
            text="Русский → Итальянский",
            variable=self.translation_direction,
            value="ru_to_it"
        ).pack(side=tk.LEFT, padx=20)
        
        ttk.Radiobutton(
            direction_frame,
            text="Итальянский → Русский",
            variable=self.translation_direction,
            value="it_to_ru"
        ).pack(side=tk.LEFT, padx=20)
        
        # Область упражнений
        exercise_frame = ttk.Frame(main_frame)
        exercise_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        # Прогресс
        progress_label = ttk.Label(
            main_frame,
            text="",
            style="Main.TLabel"
        )
        progress_label.grid(row=3, column=0)
        
        # Показываем первое упражнение
        self.show_exercise(
            current_word_index,
            words_to_review,
            exercise_frame,
            progress_label
        )
        
        # Обработка закрытия окна
        review_window.protocol(
            "WM_DELETE_WINDOW",
            lambda: self.on_review_window_closing(review_window)
        )

    def show_exercise(self, current_word_index, words_to_review, exercise_frame, progress_label):
        """Показ упражнения"""
        # Очистка фрейма
        for widget in exercise_frame.winfo_children():
            widget.destroy()

        # Получение данных текущего слова
        word_info = words_to_review[current_word_index["value"]]
        word = word_info["word"]
        data = word_info["data"]
        example = random.choice(data["примеры"])

        # Определение направления перевода
        is_to_italian = self.translation_direction.get() == "ru_to_it"
        question = example["русский"] if is_to_italian else example["итальянский"]
        correct_answer = example["итальянский"] if is_to_italian else example["русский"]
        alternatives = (example.get("альтернативы_ит", []) if is_to_italian 
                       else example.get("альтернативы_рус", []))

        # Обновление прогресса
        progress_label.config(
            text=f"Слово {current_word_index['value'] + 1} из {len(words_to_review)}"
        )

        # Создание компонентов упражнения
        # Слово и перевод
        word_frame = ttk.Frame(exercise_frame)
        word_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(
            word_frame,
            text=word,
            font=('Helvetica', 16, 'bold'),
            foreground=self.colors["primary"]
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            word_frame,
            text=f"- {data['перевод']}",
            font=('Helvetica', 14)
        ).pack(side=tk.LEFT)

        # Задание
        task_frame = ttk.LabelFrame(
            exercise_frame,
            text="Задание",
            padding="10"
        )
        task_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(
            task_frame,
            text="Переведите:",
            font=('Helvetica', 11)
        ).pack()

        ttk.Label(
            task_frame,
            text=question,
            font=('Helvetica', 12, 'bold'),
            wraplength=600
        ).pack(pady=(5, 0))

        # Поле ввода
        answer_var = tk.StringVar()
        answer_entry = ttk.Entry(
            exercise_frame,
            textvariable=answer_var,
            font=('Helvetica', 12),
            width=50
        )
        answer_entry.pack(pady=(0, 10))
        answer_entry.focus_set()

        # Область обратной связи
        feedback_text = tk.Text(
            exercise_frame,
            height=4,
            width=50,
            wrap=tk.WORD,
            font=('Helvetica', 11),
            state=tk.DISABLED
        )
        feedback_text.pack(fill=tk.X, pady=(0, 10))

        # Кнопки управления
        button_frame = ttk.Frame(exercise_frame)
        button_frame.pack(fill=tk.X)

        check_button = ttk.Button(
            button_frame,
            text="✓ Проверить",
            command=lambda: self.check_answer(
                answer_var.get(),
                correct_answer,
                alternatives,
                answer_entry,
                feedback_text,
                next_button,
                exercise_frame
            ),
            style="Review.TButton"
        )
        check_button.pack(side=tk.LEFT, padx=5)

        hint_button = ttk.Button(
            button_frame,
            text="💡 Подсказка",
            command=lambda: self.show_hint(correct_answer, feedback_text),
            style="Review.TButton"
        )
        hint_button.pack(side=tk.LEFT, padx=5)

        next_button = ttk.Button(
            button_frame,
            text="➡️ Далее",
            command=lambda: self.next_exercise(
                current_word_index,
                words_to_review,
                exercise_frame,
                progress_label
            ),
            state=tk.DISABLED,
            style="Main.TButton"
        )
        next_button.pack(side=tk.LEFT, padx=5)

        # Обработка Enter
        def handle_enter(event):
            if next_button["state"] == tk.NORMAL:
                self.next_exercise(
                    current_word_index,
                    words_to_review,
                    exercise_frame,
                    progress_label
                )
            else:
                self.check_answer(
                    answer_var.get(),
                    correct_answer,
                    alternatives,
                    answer_entry,
                    feedback_text,
                    next_button,
                    exercise_frame
                )

        answer_entry.bind('<Return>', handle_enter)
        exercise_frame.bind('<Return>', handle_enter)

    def check_answer(self, user_answer, correct_answer, alternatives,
                    answer_entry, feedback_text, next_button, exercise_frame):
        """Проверка ответа"""
        user_answer = user_answer.strip()
        is_correct = self.check_text_match(user_answer, correct_answer, alternatives)

        feedback_text.config(state=tk.NORMAL)
        feedback_text.delete(1.0, tk.END)

        if is_correct:
            # Правильный ответ
            feedback_text.insert(tk.END, "✅ Правильно!\n", "correct")
            feedback_text.insert(tk.END, f"\nВаш ответ: {user_answer}", "user_answer")
            
            # Настройка тегов
            feedback_text.tag_configure(
                "correct",
                foreground=self.colors["success"],
                font=('Helvetica', 11, 'bold')
            )
            feedback_text.tag_configure(
                "user_answer",
                foreground=self.colors["primary"]
            )

            # Деактивация ввода и активация кнопки "Далее"
            answer_entry.config(state=tk.DISABLED)
            next_button.config(state=tk.NORMAL)
            next_button.focus_set()

        else:
            # Неправильный ответ
            feedback_text.insert(tk.END, "❌ Ошибка в ответе:\n\n", "error")
            feedback_text.insert(tk.END, f"Правильный вариант: {correct_answer}\n", "correct_answer")
            
            # Настройка тегов
            feedback_text.tag_configure(
                "error",
                foreground=self.colors["error"],
                font=('Helvetica', 11, 'bold')
            )
            feedback_text.tag_configure(
                "correct_answer",
                foreground=self.colors["success"]
            )

        feedback_text.config(state=tk.DISABLED)

    def check_text_match(self, text1, text2, alternatives):
        """Проверка совпадения текстов"""
        def normalize_text(text):
            text = text.lower()
            # Замена специальных символов
            replacements = {
                'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'í': 'i',
                'ò': 'o', 'ó': 'o', 'ù': 'u', 'ú': 'u',
                "'": "'", '`': "'", '´': "'",
                "l'": "lo ", "un'": "una ", "dell'": "dello ",
                "all'": "allo ", "dall'": "dallo ", "sull'": "sullo "
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text.strip()

        # Проверяем основной ответ
        if normalize_text(text1) == normalize_text(text2):
            return True

        # Проверяем альтернативы
        for alt in alternatives:
            if normalize_text(text1) == normalize_text(alt):
                return True

        return False

    def show_hint(self, correct_answer, feedback_text):
        """Показ подсказки"""
        words = correct_answer.split()
        hint = ' '.join(word[0] + '_' * (len(word)-1) for word in words)

        feedback_text.config(state=tk.NORMAL)
        feedback_text.delete(1.0, tk.END)
        feedback_text.insert(tk.END, "💡 Подсказка:\n", "hint_title")
        feedback_text.insert(tk.END, hint, "hint_text")

        feedback_text.tag_configure(
            "hint_title",
            foreground=self.colors["hint"],
            font=('Helvetica', 11, 'bold')
        )
        feedback_text.tag_configure(
            "hint_text",
            foreground=self.colors["secondary_text"]
        )

        feedback_text.config(state=tk.DISABLED)

    def next_exercise(self, current_word_index, words_to_review,
                     exercise_frame, progress_label):
        """Переход к следующему упражнению"""
        try:
            # Обновление времени следующего повторения
            self.update_word_schedule(words_to_review[current_word_index["value"]])
            
            current_word_index["value"] += 1

            if current_word_index["value"] >= len(words_to_review):
                # Завершение сессии
                messagebox.showinfo(
                    "Поздравляем!",
                    "Вы успешно завершили все упражнения! 🎉"
                )
                self.on_review_window_closing(self.current_review_window)
            else:
                # Показ следующего упражнения
                self.show_exercise(
                    current_word_index,
                    words_to_review,
                    exercise_frame,
                    progress_label
                )
        except Exception as e:
            messagebox.showerror(
                "Ошибка",
                "Не удалось перейти к следующему упражнению"
            )

    def update_word_schedule(self, word_info):
        """Обновление расписания для слова"""
        try:
            with open('schedule.json', 'r', encoding='utf-8') as f:
                schedule = json.load(f)

            # Обновление времени следующего повторения
            for word in schedule["words"]:
                if word["word"] == word_info["word"]:
                    next_review = (datetime.datetime.now() + 
                                 datetime.timedelta(hours=4)).isoformat()
                    word["next_review"] = next_review
                    break

            with open('schedule.json', 'w', encoding='utf-8') as f:
                json.dump(schedule, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror(
                "Ошибка",
                "Не удалось обновить расписание"
            )

    def on_review_window_closing(self, window):
        """Обработка закрытия окна повторения"""
        self.is_review_active = False
        self.current_review_window = None
        window.destroy()
        self.load_schedule()

    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

if __name__ == "__main__":
    app = ItalianLearningApp()
    app.run()
	