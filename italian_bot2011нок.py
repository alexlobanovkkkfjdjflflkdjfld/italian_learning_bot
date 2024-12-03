import telebot
from telebot import types
import json
import datetime
import time
import random
import os
from typing import Dict, Optional
from vocabulary import VOCABULARY

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Отключаем стандартные логи telebot
telebot_logger = logging.getLogger('TeleBot')
telebot_logger.setLevel(logging.ERROR)


# Конфигурация
TOKEN = "7312843542:AAHVDxaHYSveOpitmkWagTFoMVNzYF4_tMU"
bot = telebot.TeleBot(TOKEN)

# Глобальное хранилище состояний пользователей
user_states = {}

def get_main_keyboard():
    """Создание основной клавиатуры"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🎯 Начать повторение"))
    markup.row(
        types.KeyboardButton("🔄 Сменить направление перевода"),
        types.KeyboardButton("📊 Статистика")
    )
    markup.row(types.KeyboardButton("ℹ️ Помощь"))
    return markup

def get_exercise_keyboard():
    """Создание клавиатуры для упражнения"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("💡 Подсказка"))
    markup.row(
        types.KeyboardButton("🔄 Сменить направление"),
        types.KeyboardButton("⏩ Пропустить")
    )
    return markup

def select_initial_words(num_words: int = 20) -> list:
    """Выбор начальных слов для изучения"""
    available_words = list(VOCABULARY["Буду изучать"].keys())
    if len(available_words) < num_words:
        return available_words
    return random.sample(available_words, num_words)

def get_new_word(learned_words: list) -> Optional[str]:
    """Получение нового слова для изучения"""
    available_words = [word for word in VOCABULARY["Буду изучать"].keys()
                      if word not in learned_words]
    return random.choice(available_words) if available_words else None

def create_initial_schedule(user_id: int) -> dict:
    """Создание начального расписания для нового пользователя"""
    current_time = datetime.datetime.now()
    initial_words = select_initial_words(20)  # Начинаем с 20 слов
    
    schedule = {
        "user_id": user_id,
        "words": [],
        "learned_words": [],  # Список изученных слов
        "last_word_added": current_time.isoformat()  # Время последнего добавления слова
    }
    
    for word in initial_words:
        schedule["words"].append({
            "word": word,
            "translation": VOCABULARY["Буду изучать"][word]["перевод"],
            "next_review": current_time.isoformat(),
            "current_interval": 4,
            "repetitions": 0,
            "correct_answers": 0  # Счетчик правильных ответов
        })
    
    save_schedule(schedule, user_id)
    return schedule

def save_schedule(schedule: dict, user_id: int):
    """Сохранение расписания пользователя"""
    if not os.path.exists('user_schedules'):
        os.makedirs('user_schedules')
    
    schedule_path = f'user_schedules/schedule_{user_id}.json'
    with open(schedule_path, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

def load_user_schedule(user_id: int) -> Optional[dict]:
    """Загрузка расписания пользователя"""
    schedule_path = f'user_schedules/schedule_{user_id}.json'
    try:
        if os.path.exists(schedule_path):
            with open(schedule_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return create_initial_schedule(user_id)
    except Exception as e:
        print(f"Error loading schedule for user {user_id}: {e}")
        return None

def update_word_schedule(user_id: int, word: dict, was_correct: bool):
    """Обновление расписания для слова"""
    try:
        schedule = load_user_schedule(user_id)
        if not schedule:
            return

        # Находим слово в списке
        for w in schedule["words"]:
            if w["word"] == word["word"]:
                if was_correct:
                    w["correct_answers"] = w.get("correct_answers", 0) + 1
                    next_interval = calculate_next_interval(w, True)
                else:
                    next_interval = 1
                    w["correct_answers"] = 0
                
                w["current_interval"] = next_interval
                w["next_review"] = (datetime.datetime.now() + 
                                  datetime.timedelta(hours=next_interval)).isoformat()
                
                # Проверяем, достигло ли слово 3 правильных ответов
                if w["correct_answers"] >= 3:
                    schedule["learned_words"].append(w["word"])
                    schedule["words"].remove(w)
                    
                    # Проверяем, нужно ли добавить новое слово
                    current_time = datetime.datetime.now()
                    last_added = datetime.datetime.fromisoformat(schedule["last_word_added"])
                    
                    if (current_time - last_added).total_seconds() >= 8 * 3600:  # 8 часов
                        new_word = get_new_word(schedule["learned_words"])
                        if new_word:
                            schedule["words"].append({
                                "word": new_word,
                                "translation": VOCABULARY["Буду изучать"][new_word]["перевод"],
                                "next_review": current_time.isoformat(),
                                "current_interval": 4,
                                "repetitions": 0,
                                "correct_answers": 0
                            })
                            schedule["last_word_added"] = current_time.isoformat()
                break
        
        save_schedule(schedule, user_id)
        
    except Exception as e:
        print(f"Error updating schedule for user {user_id}: {e}")

def calculate_next_interval(word: dict, was_correct: bool) -> int:
    """Расчет следующего интервала повторения"""
    if not was_correct:
        return 1
    
    current_interval = word.get("current_interval", 4)
    intervals = [4, 8, 24, 72, 168, 336, 672]
    
    for interval in intervals:
        if current_interval < interval:
            return interval
            
    return current_interval * 2

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    
    if user_id not in user_states:
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False
        }
    
    # Создаем или загружаем расписание пользователя
    schedule = load_user_schedule(user_id)
    if not schedule:
        schedule = create_initial_schedule(user_id)
    
    active_words = len(schedule["words"])
    learned_words = len(schedule.get("learned_words", []))
    
    welcome_text = (
        "*Привет! Я бот для изучения итальянского языка.*\n\n"
        f"📚 У вас {active_words} слов в изучении\n"
        f"✅ Изучено слов: {learned_words}\n\n"
        "🔹 *'Начать повторение'* - для изучения слов\n"
        "🔹 *'Сменить направление'* - выбор направления перевода\n"
        "🔹 *'Подсказка'* - если нужна помощь\n"
        "🔹 *'Статистика'* - для просмотра прогресса\n\n"
        "Начнём? 😊"
    )
    
    bot.reply_to(
        message,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# Остальные обработчики остаются теми же, что и в оригинальном коде
	# Добавьте после предыдущего кода следующие функции:

def show_current_exercise(chat_id: int, user_id: int):
    """Показ текущего упражнения"""
    state = user_states[user_id]
    words = state["words_to_review"]
    current_index = state["current_word_index"]
    
    # Проверка завершения всех упражнений
    if current_index >= len(words):
        schedule = load_user_schedule(user_id)
        active_words = len(schedule["words"])
        learned_words = len(schedule.get("learned_words", []))
        
        completion_message = (
            "🎉 *Поздравляем!*\n"
            "Вы успешно завершили все упражнения!\n\n"
            f"📚 Активных слов: {active_words}\n"
            f"✅ Изучено слов: {learned_words}\n\n"
        )
        
        next_review_time = get_next_review_time(user_id)
        if next_review_time:
            time_str = format_time_until(next_review_time)
            completion_message += (
                f"⏰ Следующее повторение через: *{time_str}*\n"
                "Я пришлю уведомление, когда придет время!"
            )
        
        bot.send_message(
            chat_id,
            completion_message,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        
        user_states[user_id] = {
            "translation_direction": state["translation_direction"],
            "awaiting_answer": False
        }
        return

    # Получение данных текущего слова
    word = words[current_index]
    word_data = VOCABULARY["Буду изучать"][word["word"]]
    example = random.choice(word_data["примеры"])
    
    # Определение направления перевода
    translation_direction = state["translation_direction"]
    if translation_direction == "ru_to_it":
        question = example["русский"]
        correct_answer = example["итальянский"]
        direction_text = "итальянский"
    else:
        question = example["итальянский"]
        correct_answer = example["русский"]
        direction_text = "русский"
    
    # Формирование сообщения
    progress = word.get("correct_answers", 0)
    progress_bar = "🟢" * progress + "⚪️" * (3 - progress)
    
    message_text = (
        f"*{word['word']} - {word['translation']}*\n\n"
        f"Переведите на {direction_text}:\n"
        f"*{question}*\n\n"
        f"Прогресс изучения: {progress_bar}\n"
        f"_Слово {current_index + 1} из {len(words)}_"
    )
    
    bot.send_message(
        chat_id,
        message_text,
        parse_mode='Markdown',
        reply_markup=get_exercise_keyboard()
    )
    
    state["awaiting_answer"] = True

def get_next_review_time(user_id: int) -> Optional[datetime.datetime]:
    """Получение времени следующего повторения"""
    schedule = load_user_schedule(user_id)
    if not schedule or not schedule["words"]:
        return None
        
    current_time = datetime.datetime.now()
    next_times = []
    
    for word in schedule["words"]:
        review_time = datetime.datetime.fromisoformat(word["next_review"])
        if review_time > current_time:
            next_times.append(review_time)
            
    return min(next_times) if next_times else None

def format_time_until(target_time: datetime.datetime) -> str:
    """Форматирование времени до следующего повторения"""
    time_diff = target_time - datetime.datetime.now()
    hours = int(time_diff.total_seconds() // 3600)
    minutes = int((time_diff.total_seconds() % 3600) // 60)
    
    if hours > 0:
        return f"{hours}ч {minutes}мин"
    return f"{minutes}мин"

@bot.message_handler(func=lambda message: message.text in ["🎯 Начать повторение", "/review"])
def start_review(message):
    """Начало сессии повторения"""
    user_id = message.from_user.id
    
    if user_id not in user_states:
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False
        }
    
    schedule = load_user_schedule(user_id)
    if not schedule:
        bot.reply_to(message, "❌ Произошла ошибка при загрузке расписания.")
        return
        
    current_time = datetime.datetime.now()
    words_to_review = []
    
    for word in schedule["words"]:
        next_review = datetime.datetime.fromisoformat(word["next_review"])
        if next_review <= current_time:
            words_to_review.append(word)
    
    if not words_to_review:
        next_review_time = get_next_review_time(user_id)
        if next_review_time:
            time_str = format_time_until(next_review_time)
            bot.reply_to(
                message,
                f"🕒 Сейчас нет слов для повторения!\n\nСледующее повторение через: *{time_str}*",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
        else:
            bot.reply_to(
                message,
                "🕒 Сейчас нет слов для повторения!",
                reply_markup=get_main_keyboard()
            )
        return
    
    user_states[user_id].update({
        "words_to_review": words_to_review,
        "current_word_index": 0,
        "awaiting_answer": True
    })
    
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "💡 Подсказка")
def show_hint(message):
    """Показ подсказки"""
    user_id = message.from_user.id
    if user_id not in user_states or not user_states[user_id]["awaiting_answer"]:
        bot.reply_to(message, "❌ Сначала начните упражнение")
        return
        
    state = user_states[user_id]
    word = state["words_to_review"][state["current_word_index"]]
    word_data = VOCABULARY["Буду изучать"][word["word"]]
    example = random.choice(word_data["примеры"])
    
    if state["translation_direction"] == "ru_to_it":
        answer = example["итальянский"]
    else:
        answer = example["русский"]
    
    words = answer.split()
    hint_words = []
    for word in words:
        if len(word) > 0:
            hint_words.append(word[0] + '_' * (len(word)-1))
    hint = ' '.join(hint_words)
    
    bot.reply_to(
        message,
        f"💡 Подсказка:\n{hint}",
        reply_markup=get_exercise_keyboard()
    )

@bot.message_handler(func=lambda message: message.text in ["🔄 Сменить направление", "/switch"])
def switch_translation_direction(message):
    """Смена направления перевода"""
    user_id = message.from_user.id
    if user_id not in user_states:
        user_states[user_id] = {"translation_direction": "ru_to_it"}
        
    current_direction = user_states[user_id]["translation_direction"]
    new_direction = "it_to_ru" if current_direction == "ru_to_it" else "ru_to_it"
    user_states[user_id]["translation_direction"] = new_direction
    
    direction_text = "итальянский → русский" if new_direction == "it_to_ru" else "русский → итальянский"
    bot.reply_to(
        message,
        f"🔄 Направление перевода изменено на:\n*{direction_text}*",
        parse_mode='Markdown'
    )
    
    if user_states[user_id].get("awaiting_answer"):
        show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "⏩ Пропустить")
def skip_word(message):
    """Пропуск текущего слова"""
    user_id = message.from_user.id
    if user_id not in user_states or not user_states[user_id].get("awaiting_answer"):
        return
        
    state = user_states[user_id]
    word = state["words_to_review"][state["current_word_index"]]
    
    update_word_schedule(user_id, word, False)
    
    state["current_word_index"] += 1
    bot.reply_to(message, "⏩ Слово пропущено")
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_statistics(message):
    """Показ статистики обучения"""
    user_id = message.from_user.id
    schedule = load_user_schedule(user_id)
    
    if not schedule:
        bot.reply_to(message, "❌ Ошибка при загрузке статистики")
        return
        
    active_words = len(schedule["words"])
    learned_words = len(schedule.get("learned_words", []))
    
    # Подсчет слов по прогрессу
    not_started = 0
    in_progress = 0
    for word in schedule["words"]:
        correct_answers = word.get("correct_answers", 0)
        if correct_answers == 0:
            not_started += 1
        else:
            in_progress += 1
    
    stats_message = (
        "📊 *Статистика обучения:*\n\n"
        f"📚 Всего слов в работе: {active_words}\n"
        f"🆕 Не начато: {not_started}\n"
        f"📝 В процессе: {in_progress}\n"
        f"✅ Изучено: {learned_words}\n\n"
        "Слово считается изученным после 3 правильных ответов\n"
        f"Всего слов в словаре: {len(VOCABULARY['Буду изучать'])}"
    )
    
    bot.reply_to(
        message,
        stats_message,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

def normalize_text(text: str) -> str:
    """Нормализация текста для сравнения"""
    text = text.lower()
    
    replacements = {
        'à': 'a', 'è': 'e', 'é': 'e',
        'ì': 'i', 'í': 'i', 'ò': 'o',
        'ó': 'o', 'ù': 'u', 'ú': 'u'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return ' '.join(text.split())

@bot.message_handler(func=lambda message: True)
def handle_answer(message):
    """Обработка ответов пользователя"""
    user_id = message.from_user.id
    if user_id not in user_states or not user_states[user_id].get("awaiting_answer"):
        return

    state = user_states[user_id]
    word = state["words_to_review"][state["current_word_index"]]
    word_data = VOCABULARY["Буду изучать"][word["word"]]
    example = random.choice(word_data["примеры"])
    
    if state["translation_direction"] == "ru_to_it":
        correct_answer = example["итальянский"]
        alternatives = example.get("альтернативы_ит", [])
    else:
        correct_answer = example["русский"]
        alternatives = example.get("альтернативы_рус", [])

    user_answer = normalize_text(message.text.strip())
    correct_answer_norm = normalize_text(correct_answer)
    
    is_correct = False
    if user_answer == correct_answer_norm:
        is_correct = True
    else:
        for alt in alternatives:
            if user_answer == normalize_text(alt):
                is_correct = True
                break

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if is_correct:
        # Обновляем счетчик правильных ответов
        current_progress = word.get("correct_answers", 0)
        progress_bar = "🟢" * (current_progress + 1) + "⚪️" * (2 - current_progress)
        
        response = (
            "✅ *Правильно!*\n\n"
            f"Ваш ответ: _{message.text}_\n"
            f"Прогресс: {progress_bar}"
        )
        markup.row(types.KeyboardButton("➡️ Далее"))
    else:
        response = (
            "❌ *Ошибка!*\n\n"
            f"Ваш ответ: _{message.text}_\n"
            f"Правильный ответ: *{correct_answer}*"
        )
        markup.row(types.KeyboardButton("🔄 Повторить"))
        markup.row(
            types.KeyboardButton("💡 Подсказка"),
            types.KeyboardButton("➡️ Далее")
        )

    update_word_schedule(user_id, word, is_correct)
    
    bot.reply_to(
        message,
        response,
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    if not is_correct:
        state["awaiting_answer"] = True
    else:
        state["awaiting_answer"] = False

def check_and_send_notifications():
    """Проверка и отправка уведомлений"""
    while True:
        try:
            if os.path.exists('user_schedules'):
                for filename in os.listdir('user_schedules'):
                    if filename.startswith('schedule_') and filename.endswith('.json'):
                        user_id = int(filename.split('_')[1].split('.')[0])
                        
                        schedule = load_user_schedule(user_id)
                        if not schedule:
                            continue

                        current_time = datetime.datetime.now()
                        words_to_review = []
                        
                        for word in schedule["words"]:
                            next_review = datetime.datetime.fromisoformat(word["next_review"])
                            if next_review <= current_time:
                                words_to_review.append(word)
                        
                        if words_to_review:
                            try:
                                active_words = len(schedule["words"])
                                learned_words = len(schedule.get("learned_words", []))
                                
                                notification_text = (
                                    f"🔔 *Пора повторить слова!*\n\n"
                                    f"У вас {len(words_to_review)} слов для повторения.\n"
                                    f"📚 Активных слов: {active_words}\n"
                                    f"✅ Изучено слов: {learned_words}\n\n"
                                    "Используйте команду /review для начала повторения."
                                )
                                
                                bot.send_message(
                                    user_id,
                                    notification_text,
                                    parse_mode='Markdown',
                                    reply_markup=get_main_keyboard()
                                )
                            except Exception as e:
                                print(f"Error sending notification to user {user_id}: {e}")
                                
        except Exception as e:
            print(f"Error in notification check: {e}")
            
        time.sleep(3600)  # Проверка каждый час

# @bot.message_handler(func=lambda message: message.text == "➡️ Далее")
# def next_exercise(message):
    # """Переход к следующему упражнению"""
    # user_id = message.from_user.id
    # if user_id not in user_states:
        # return
        
    # state = user_states[user_id]
    # state["current_word_index"] += 1
    # state["awaiting_answer"] = True
    
    # show_current_exercise(message.chat.id, user_id)
@bot.message_handler(func=lambda message: message.text == "➡️ Далее")
def next_exercise(message):
    """Переход к следующему упражнению"""
    user_id = message.from_user.id
    if user_id not in user_states:
        return
        
    state = user_states[user_id]
    state["current_word_index"] += 1
    state["awaiting_answer"] = True
    
    # Загружаем актуальное расписание
    schedule = load_user_schedule(user_id)
    if not schedule:
        return
        
    # Получаем слова для повторения
    current_time = datetime.datetime.now()
    words_to_review = []
    
    for word in schedule["words"]:
        next_review = datetime.datetime.fromisoformat(word["next_review"])
        if next_review <= current_time:
            words_to_review.append(word)
    
    # Обновляем список слов для повторения
    state["words_to_review"] = words_to_review
    
    show_current_exercise(message.chat.id, user_id)

def update_word_schedule(user_id: int, word: dict, was_correct: bool):
    """Обновление расписания для слова"""
    try:
        schedule = load_user_schedule(user_id)
        if not schedule:
            return

        # Находим слово в списке
        for w in schedule["words"]:
            if w["word"] == word["word"]:
                if was_correct:
                    w["correct_answers"] = w.get("correct_answers", 0) + 1
                    next_interval = calculate_next_interval(w, True)
                else:
                    next_interval = 1
                    w["correct_answers"] = 0
                
                w["current_interval"] = next_interval
                w["next_review"] = (datetime.datetime.now() + 
                                  datetime.timedelta(hours=next_interval)).isoformat()
                
                # Если слово получило 3 правильных ответа
                if w["correct_answers"] >= 3 and next_interval >= 24:
                    # Проверяем количество активных слов
                    active_words = [word for word in schedule["words"] 
                                  if word.get("current_interval", 4) < 24]
                    
                    # Если активных слов меньше 20, добавляем новое
                    if len(active_words) < 20:
                        all_words = set(VOCABULARY["Буду изучать"].keys())
                        used_words = {word["word"] for word in schedule["words"]}
                        available_words = list(all_words - used_words)
                        
                        if available_words:
                            new_word = random.choice(available_words)
                            current_time = datetime.datetime.now()
                            schedule["words"].append({
                                "word": new_word,
                                "translation": VOCABULARY["Буду изучать"][new_word]["перевод"],
                                "next_review": current_time.isoformat(),
                                "current_interval": 4,
                                "repetitions": 0,
                                "correct_answers": 0
                            })
                break
        
        save_schedule(schedule, user_id)
        
    except Exception as e:
        print(f"Error updating schedule for user {user_id}: {e}")

def create_initial_schedule(user_id: int) -> dict:
    """Создание начального расписания для нового пользователя"""
    current_time = datetime.datetime.now()
    all_words = list(VOCABULARY["Буду изучать"].keys())
    initial_words = random.sample(all_words, min(20, len(all_words)))
    
    schedule = {
        "user_id": user_id,
        "words": [],
        "last_word_added": current_time.isoformat()
    }
    
    for word in initial_words:
        schedule["words"].append({
            "word": word,
            "translation": VOCABULARY["Буду изучать"][word]["перевод"],
            "next_review": current_time.isoformat(),
            "current_interval": 4,
            "repetitions": 0,
            "correct_answers": 0
        })
    
    save_schedule(schedule, user_id)
    return schedule
    

@bot.message_handler(func=lambda message: message.text == "🔄 Повторить")
def retry_answer(message):
    """Повторная попытка ответа"""
    user_id = message.from_user.id
    if user_id not in user_states:
        return
        
    state = user_states[user_id]
    state["awaiting_answer"] = True
    
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(commands=['help'])
def send_help(message):
    """Обработка команды /help"""
    help_text = (
        "*Как пользоваться ботом:*\n\n"
        "1️⃣ *Начало работы:*\n"
        "• Нажмите '🎯 Начать повторение'\n"
        "• Выберите направление перевода\n\n"
        "2️⃣ *Во время упражнения:*\n"
        "• Введите перевод предложенного слова/фразы\n"
        "• Используйте '💡 Подсказка' если нужна помощь\n"
        "• '🔄 Повторить' - для повторной попытки\n"
        "• '➡️ Далее' - для следующего слова\n\n"
        "3️⃣ *Система изучения:*\n"
        "• Каждое слово нужно правильно перевести 3 раза\n"
        "• После изучения слова добавляется новое\n"
        "• Всегда поддерживается около 20 активных слов\n"
        "• Интервалы повторения увеличиваются при правильных ответах\n\n"
        "4️⃣ *Команды:*\n"
        "/start - Начать сначала\n"
        "/review - Начать повторение\n"
        "/switch - Сменить направление перевода\n"
        "/help - Показать это сообщение"
    )
    
    bot.reply_to(
        message,
        help_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )
# def run_bot():
    # """Запуск бота"""
    # print("Bot started...")
    
    # # Запуск проверки уведомлений в отдельном потоке
    # import threading
    # notification_thread = threading.Thread(target=check_and_send_notifications, daemon=True)
    # notification_thread.start()
    
    # # Запуск бота
    # try:
        # bot.infinity_polling(timeout=10, long_polling_timeout=5)
    # except Exception as e:
        # print(f"Error in bot polling: {e}")
        # time.sleep(5)
        # run_bot()  # Рекурсивный перезапуск при ошибке


    
def run_bot():
    """Запуск бота"""
    print("Bot started...")
    
    # Сбрасываем обновления при запуске
    try:
        bot.remove_webhook()
        bot.get_updates(offset=-1)  # Сбрасываем все накопленные обновления
    except Exception as e:
        print(f"Error clearing updates: {e}")
    
    # Запуск проверки уведомлений в отдельном потоке
    import threading
    notification_thread = threading.Thread(target=check_and_send_notifications, daemon=True)
    notification_thread.start()
    
    # Запуск бота
    while True:
        try:
            print("Starting bot polling...")
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Bot polling error: {e}")
            if "Conflict: terminated by other getUpdates request" in str(e):
                print("Another instance is running. Waiting...")
                time.sleep(30)  # Ждем 30 секунд перед повторной попыткой
            else:
                time.sleep(5)  # Для других ошибок ждем 5 секунд
                
if __name__ == "__main__":
    run_bot()