# import telebot
# from telebot import types
# import json
# import datetime
# import time
# import random
# import os
# import logging
# from typing import Dict, Optional
# from vocabulary import VOCABULARY

# # Настройка логирования
# logging.basicConfig(
    # level=logging.INFO,
    # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # handlers=[
        # logging.FileHandler('italian_bot.log', encoding='utf-8'),
        # logging.StreamHandler()
    # ]
# )
# logger = logging.getLogger(__name__)

# # Конфигурация бота
# TOKEN = 'YOUR_BOT_TOKEN'
# bot = telebot.TeleBot(TOKEN)

import telebot
from telebot import types
import json
import datetime
import time
import random
import os
import logging
import threading
from typing import Dict, Optional
from vocabulary import VOCABULARY

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('italian_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация бота
TOKEN = "7312843542:AAHVDxaHYSveOpitmkWagTFoMVNzYF4_tMU"
bot = telebot.TeleBot(TOKEN)

# Глобальное хранилище состояний пользователей
user_states = {}

# # Глобальное хранилище состояний пользователей
# user_states = {}

# def get_main_keyboard():
    # """Создание основной клавиатуры"""
    # markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # markup.row(types.KeyboardButton("🎯 Начать повторение"))
    # markup.row(
        # types.KeyboardButton("🔄 Сменить направление перевода"),
        # types.KeyboardButton("📊 Статистика")
    # )
    # markup.row(types.KeyboardButton("ℹ️ Помощь"))
    # return markup
    
def get_main_keyboard():
    """Создание основной клавиатуры"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🎯 Начать повторение"))
    markup.row(
        types.KeyboardButton("🔄 Сменить направление перевода"),
        types.KeyboardButton("📊 Статистика")
    )
    markup.row(types.KeyboardButton("ℹ️ Помощь"))  # Проверьте точное соответствие эмодзи
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

def normalize_text(text: str) -> str:
    """Нормализация текста для сравнения"""
    # Приводим к нижнему регистру
    text = text.lower()
    
    # Замены для итальянских букв
    replacements = {
        'à': 'a',
        'è': 'e',
        'é': 'e',
        'ì': 'i',
        'í': 'i',
        'ò': 'o',
        'ó': 'o',
        'ù': 'u',
        'ú': 'u'
    }
    
    # Применяем замены
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Удаляем двойные пробелы
    text = ' '.join(text.split())
    
    return text

def load_user_schedule(user_id: int) -> Optional[dict]:
    """Загрузка расписания конкретного пользователя"""
    schedule_path = f'user_schedules/schedule_{user_id}.json'
    try:
        if not os.path.exists('user_schedules'):
            os.makedirs('user_schedules')
            
        if os.path.exists(schedule_path):
            with open(schedule_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return create_initial_schedule(user_id)
    except Exception as e:
        logger.error(f"Error loading schedule for user {user_id}: {e}")
        return None

def create_initial_schedule(user_id: int) -> dict:
    """Создание начального расписания для нового пользователя"""
    current_time = datetime.datetime.now()
    schedule = {
        "user_id": user_id,
        "words": []
    }
    
    for i, word in enumerate(VOCABULARY["Буду изучать"].keys()):
        next_review = (current_time if i == 0 
                     else current_time + datetime.timedelta(minutes=5*i))
        schedule["words"].append({
            "word": word,
            "translation": VOCABULARY["Буду изучать"][word]["перевод"],
            "next_review": next_review.isoformat(),
            "current_interval": 4,
            "repetitions": 0
        })
    
    schedule_path = f'user_schedules/schedule_{user_id}.json'
    with open(schedule_path, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
        
    return schedule

def calculate_next_interval(word: dict, was_correct: bool) -> int:
    """Расчет следующего интервала повторения"""
    if not was_correct:
        return 1  # Повторить через час при ошибке
    
    current_interval = word.get("current_interval", 4)
    repetitions = word.get("repetitions", 0)
    
    intervals = [4, 8, 24, 72, 168, 336, 672]  # часы
    
    for interval in intervals:
        if current_interval < interval:
            return interval
            
    return current_interval * 2
	
def update_word_schedule(user_id: int, word: dict, next_interval: int, was_correct: bool):
    """Обновление расписания для слова"""
    try:
        schedule_path = f'user_schedules/schedule_{user_id}.json'
        with open(schedule_path, 'r', encoding='utf-8') as f:
            schedule = json.load(f)

        for w in schedule["words"]:
            if w["word"] == word["word"]:
                next_review = (datetime.datetime.now() + 
                             datetime.timedelta(hours=next_interval)).isoformat()
                w["next_review"] = next_review
                
                if was_correct:
                    w["current_interval"] = next_interval
                    w["repetitions"] = w.get("repetitions", 0) + 1
                else:
                    w["current_interval"] = 1
                    w["repetitions"] = 0
                break

        with open(schedule_path, 'w', encoding='utf-8') as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"Error updating schedule for user {user_id}: {e}")

def get_next_review_time(user_id: int) -> Optional[datetime.datetime]:
    """Получение времени следующего повторения"""
    try:
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
    except Exception as e:
        logger.error(f"Error getting next review time for user {user_id}: {e}")
        return None

def format_time_until(target_time: datetime.datetime) -> str:
    """Форматирование времени до следующего повторения"""
    time_diff = target_time - datetime.datetime.now()
    hours = int(time_diff.total_seconds() // 3600)
    minutes = int((time_diff.total_seconds() % 3600) // 60)
    
    if hours > 0:
        return f"{hours}ч {minutes}мин"
    return f"{minutes}мин"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработка команды /start"""
    try:
        user_id = message.from_user.id
        
        # Инициализация состояния пользователя
        if user_id not in user_states:
            user_states[user_id] = {
                "translation_direction": "ru_to_it",
                "awaiting_answer": False
            }
        
        # Отправка приветственного сообщения
        welcome_text = (
            "👋 *Привет! Я бот для изучения итальянского языка.*\n\n"
            "*Как пользоваться:*\n"
            "🎯 Нажмите 'Начать повторение'\n"
            "🔄 Используйте 'Сменить направление' для выбора языка перевода\n"
            "📊 Следите за прогрессом в 'Статистике'\n"
            "❓ Используйте 'Помощь' для подробной информации\n\n"
            "Готовы начать? 😊"
        )
        
        bot.reply_to(
            message,
            welcome_text,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in send_welcome: {e}")
        bot.reply_to(
            message,
            "Произошла ошибка при запуске. Попробуйте позже."
        )

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
        "3️⃣ *Система повторения:*\n"
        "• При правильных ответах интервалы увеличиваются\n"
        "• При ошибках слова повторяются чаще\n"
        "• Бот напомнит о времени повторения\n\n"
        "4️⃣ *Оценка ответов:*\n"
        "• ✅ Правильный ответ - интервал увеличивается\n"
        "• ❌ Ошибка - слово вернётся для повторения через час\n"
        "• Используйте подсказки, если затрудняетесь\n\n"
        "*Команды:*\n"
        "/start - Начать сначала\n"
        "/review - Начать повторение\n"
        "/switch - Сменить направление перевода"
    )
    
    bot.reply_to(
        message,
        help_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_statistics(message):
    """Показ статистики обучения"""
    try:
        user_id = message.from_user.id
        schedule = load_user_schedule(user_id)
        
        if not schedule:
            bot.reply_to(message, "❌ Ошибка при загрузке статистики")
            return
            
        total_words = len(schedule["words"])
        learned_words = sum(1 for word in schedule["words"] if word.get("repetitions", 0) >= 3)
        in_progress = sum(1 for word in schedule["words"] if 0 < word.get("repetitions", 0) < 3)
        
        stats_message = (
            "📊 *Статистика обучения:*\n\n"
            f"📚 Всего слов: {total_words}\n"
            f"✅ Изучено: {learned_words}\n"
            f"📝 В процессе: {in_progress}\n"
            f"🆕 Не начато: {total_words - learned_words - in_progress}\n\n"
            "_Слово считается изученным после 3 правильных повторений_"
        )
        
        next_review = get_next_review_time(user_id)
        if next_review:
            time_str = format_time_until(next_review)
            stats_message += f"\n\n⏰ Следующее повторение через: *{time_str}*"
        
        bot.reply_to(
            message,
            stats_message,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in show_statistics: {e}")
        bot.reply_to(
            message,
            "Произошла ошибка при загрузке статистики"
        )
@bot.message_handler(func=lambda message: message.text in ["🎯 Начать повторение", "/review"])
def start_review(message):
    """Начало сессии повторения"""
    try:
        user_id = message.from_user.id
        
        if user_id not in user_states:
            user_states[user_id] = {
                "translation_direction": "ru_to_it",
                "current_word_index": 0,
                "words_to_review": [],
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
            next_review = get_next_review_time(user_id)
            if next_review:
                time_str = format_time_until(next_review)
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
        
    except Exception as e:
        logger.error(f"Error in start_review: {e}")
        bot.reply_to(
            message,
            "Произошла ошибка при начале повторения"
        )

def show_current_exercise(chat_id: int, user_id: int):
    """Показ текущего упражнения"""
    try:
        state = user_states[user_id]
        words = state["words_to_review"]
        current_index = state["current_word_index"]
        
        # Проверка завершения всех упражнений
        if current_index >= len(words):
            next_review = get_next_review_time(user_id)
            
            completion_message = (
                "🎉 *Поздравляем!*\n"
                "Вы успешно завершили все упражнения!\n\n"
            )
            
            if next_review:
                time_str = format_time_until(next_review)
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
            
            # Очищаем состояние пользователя
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
        message_text = (
            f"*{word['word']} - {word['translation']}*\n\n"
            f"Переведите на {direction_text}:\n"
            f"*{question}*\n\n"
            f"_Слово {current_index + 1} из {len(words)}_"
        )
        
        # Отправка сообщения с клавиатурой упражнения
        bot.send_message(
            chat_id,
            message_text,
            parse_mode='Markdown',
            reply_markup=get_exercise_keyboard()
        )
        
        # Обновляем состояние
        state["awaiting_answer"] = True
        
    except Exception as e:
        logger.error(f"Error in show_current_exercise: {e}")
        bot.send_message(
            chat_id,
            "Произошла ошибка при показе упражнения",
            reply_markup=get_main_keyboard()
        )

@bot.message_handler(func=lambda message: message.text == "💡 Подсказка")
def show_hint(message):
    """Показ подсказки"""
    try:
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
        
        # Создаем подсказку (первые буквы)
        words = answer.split()
        hint_words = []
        for word in words:
            if len(word) > 0:
                hint_words.append(word[0] + '_' * (len(word)-1))
        hint = ' '.join(hint_words)
        
        # Отправляем подсказку
        bot.reply_to(
            message,
            f"💡 Подсказка:\n{hint}",
            reply_markup=get_exercise_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in show_hint: {e}")
        bot.reply_to(message, "Произошла ошибка при показе подсказки")
@bot.message_handler(func=lambda message: message.text in ["🔄 Сменить направление", "/switch"])
def switch_translation_direction(message):
    """Смена направления перевода"""
    try:
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
            
    except Exception as e:
        logger.error(f"Error in switch_translation_direction: {e}")
        bot.reply_to(message, "Произошла ошибка при смене направления")

@bot.message_handler(func=lambda message: message.text == "⏩ Пропустить")
def skip_word(message):
    """Пропуск текущего слова"""
    try:
        user_id = message.from_user.id
        if user_id not in user_states or not user_states[user_id].get("awaiting_answer"):
            return
            
        state = user_states[user_id]
        word = state["words_to_review"][state["current_word_index"]]
        
        # При пропуске слова уменьшаем интервал
        update_word_schedule(user_id, word, 1, False)
        
        state["current_word_index"] += 1
        bot.reply_to(
            message, 
            "⏩ Слово пропущено\nОно появится для повторения через час",
            reply_markup=get_exercise_keyboard()
        )
        show_current_exercise(message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Error in skip_word: {e}")
        bot.reply_to(message, "Произошла ошибка при пропуске слова")

@bot.message_handler(func=lambda message: message.text == "🔄 Повторить")
def retry_exercise(message):
    """Повторная попытка текущего упражнения"""
    try:
        user_id = message.from_user.id
        if user_id not in user_states:
            return
            
        state = user_states[user_id]
        if not state.get("awaiting_answer", False):
            state["awaiting_answer"] = True
            
        show_current_exercise(message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Error in retry_exercise: {e}")
        bot.reply_to(message, "Произошла ошибка при повторе упражнения")

@bot.message_handler(func=lambda message: message.text == "➡️ Далее")
def next_exercise(message):
    """Переход к следующему упражнению"""
    try:
        user_id = message.from_user.id
        if user_id not in user_states:
            return
            
        state = user_states[user_id]
        state["current_word_index"] += 1
        state["awaiting_answer"] = True
        
        show_current_exercise(message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Error in next_exercise: {e}")
        bot.reply_to(message, "Произошла ошибка при переходе к следующему упражнению")

@bot.message_handler(func=lambda message: message.text in ["ℹ️ Помощь", "Помощь"])
def button_help(message):
    """Обработка нажатия кнопки Помощь"""
    print(f"Получена команда помощи: {message.text}")  # Для отладки
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
        "3️⃣ *Система повторения:*\n"
        "• При правильных ответах интервалы увеличиваются\n"
        "• При ошибках слова повторяются чаще\n"
        "• Бот напомнит о времени повторения\n"
        )
    
    try:
        bot.reply_to(
            message,
            help_text,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        print("Сообщение помощи отправлено")  # Для отладки
    except Exception as e:
        print(f"Ошибка при отправке помощи: {e}")  # Для отладки
        logger.error(f"Error in button_help: {e}")
        
        
@bot.message_handler(func=lambda message: True)
def handle_answer(message):
    """Обработка ответов пользователя"""
    print(f"Получено сообщение: {message.text}")  # Для отладки
    # # ... остальной код ...
# @bot.message_handler(func=lambda message: True)
# def handle_answer(message):
    # """Обработка ответов пользователя"""
    try:
        user_id = message.from_user.id
        if user_id not in user_states or not user_states[user_id].get("awaiting_answer"):
            return

        state = user_states[user_id]
        word = state["words_to_review"][state["current_word_index"]]
        word_data = VOCABULARY["Буду изучать"][word["word"]]
        example = random.choice(word_data["примеры"])
        
        # Определяем правильный ответ и альтернативы
        if state["translation_direction"] == "ru_to_it":
            correct_answer = example["итальянский"]
            alternatives = example.get("альтернативы_ит", [])
        else:
            correct_answer = example["русский"]
            alternatives = example.get("альтернативы_рус", [])

        # Нормализация ответа пользователя и правильного ответа
        user_answer = normalize_text(message.text.strip())
        correct_answer_norm = normalize_text(correct_answer)
        
        # Проверка ответа
        is_correct = False
        if user_answer == correct_answer_norm:
            is_correct = True
        else:
            for alt in alternatives:
                if user_answer == normalize_text(alt):
                    is_correct = True
                    break

        # Формируем клавиатуру и ответ
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        
        if is_correct:
            response = (
                "✅ *Правильно!*\n\n"
                f"Ваш ответ: _{message.text}_"
            )
            next_interval = calculate_next_interval(word, True)
            markup.row(types.KeyboardButton("➡️ Далее"))
            state["awaiting_answer"] = False
        else:
            # Анализ ошибок
            differences = []
            if any(c in correct_answer for c in 'àèéìíòóùú') and not any(c in message.text for c in 'àèéìíòóùú'):
                differences.append("• Проверьте диакритические знаки (à, è, é, etc.)")
            if correct_answer[0].isupper() and message.text[0].islower():
                differences.append("• Предложение должно начинаться с заглавной буквы")
            
            response = (
                "❌ *Ошибка!*\n\n"
                f"Ваш ответ: _{message.text}_\n"
                f"Правильный ответ: *{correct_answer}*\n\n"
            )
            
            if differences:
                response += "*На что обратить внимание:*\n" + "\n".join(differences) + "\n\n"
                
            response += (
                "*Что делать дальше?*\n"
                "1️⃣ Нажмите '🔄 Повторить', чтобы попробовать снова\n"
                "2️⃣ Используйте '💡 Подсказка' для помощи\n"
                "3️⃣ Или нажмите '➡️ Далее' для следующего слова"
            )
            
            next_interval = 1
            markup.row(types.KeyboardButton("🔄 Повторить"))
            markup.row(
                types.KeyboardButton("💡 Подсказка"),
                types.KeyboardButton("➡️ Далее")
            )
            state["awaiting_answer"] = True

        # Обновляем расписание
        update_word_schedule(user_id, word, next_interval, is_correct)
        
        # Отправляем ответ
        bot.reply_to(
            message,
            response,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"Error in handle_answer: {e}")
        bot.reply_to(
            message,
            "Произошла ошибка при проверке ответа. Попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )

# @bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
# def button_help(message):
    # """Обработка нажатия кнопки Помощь"""
    # help_text = (
        # "*Как пользоваться ботом:*\n\n"
        # "1️⃣ *Начало работы:*\n"
        # "• Нажмите '🎯 Начать повторение'\n"
        # "• Выберите направление перевода\n\n"
        # "2️⃣ *Во время упражнения:*\n"
        # "• Введите перевод предложенного слова/фразы\n"
        # "• Используйте '💡 Подсказка' если нужна помощь\n"
        # "• '🔄 Повторить' - для повторной попытки\n"
        # "• '➡️ Далее' - для следующего слова\n\n"
        # "3️⃣ *Система повторения:*\n"
        # "• При правильных ответах интервалы увеличиваются\n"
        # "• При ошибках слова повторяются чаще\n"
        # "• Бот напомнит о времени повторения\n\n"
        # "4️⃣ *Оценка ответов:*\n"
        # "• ✅ Правильный ответ - интервал увеличивается\n"
        # "• ❌ Ошибка - слово вернётся для повторения через час\n"
        # "• Используйте подсказки, если затрудняетесь\n\n"
        # "*Команды:*\n"
        # "/start - Начать сначала\n"
        # "/review - Начать повторение\n"
        # "/switch - Сменить направление перевода"
    # )
    
    # bot.reply_to(
        # message,
        # help_text,
        # parse_mode='Markdown',
        # reply_markup=get_main_keyboard()
    # )
    


def check_and_send_notifications():
    """Проверка и отправка уведомлений"""
    while True:
        try:
            if os.path.exists('user_schedules'):
                for filename in os.listdir('user_schedules'):
                    if filename.startswith('schedule_') and filename.endswith('.json'):
                        try:
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
                                bot.send_message(
                                    user_id,
                                    f"🔔 *Пора повторить слова!*\n\n"
                                    f"У вас {len(words_to_review)} слов для повторения.\n"
                                    "Используйте команду /review для начала повторения.",
                                    parse_mode='Markdown',
                                    reply_markup=get_main_keyboard()
                                )
                        except Exception as e:
                            logger.error(f"Error processing notifications for user {filename}: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Error in notification check: {e}")
        
        time.sleep(3600)  # Проверка каждый час

def run_bot():
    """Запуск бота"""
    logger.info("Bot started...")
    
    # Запуск проверки уведомлений в отдельном потоке
    notification_thread = threading.Thread(target=check_and_send_notifications, daemon=True)
    notification_thread.start()
    
    # Запуск бота
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            logger.error(f"Error in bot polling: {e}")
            time.sleep(5)
            logger.info("Trying to restart bot...")
            continue

if __name__ == "__main__":
    run_bot()
		