import telebot
from telebot import types
import json
import datetime
import time
import random
import os
import logging
import sys
from typing import Dict, Optional, List
from vocabulary import VOCABULARY

# Настройка логирования
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler('bot_log.txt', encoding='utf-8')
file_handler.setFormatter(formatter)

logger = logging.getLogger('ItalianBot')
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

telebot_logger = logging.getLogger('TeleBot')
telebot_logger.setLevel(logging.WARNING)

# Конфигурация
TOKEN = "7312843542:AAHVDxaHYSveOpitmkWagTFoMVNzYF4_tMU"
bot = telebot.TeleBot(TOKEN)

# Глобальное хранилище состояний пользователей
user_states = {}

class WordStatus:
    NEW = "new"           # Новое слово
    LEARNING = "learning" # В процессе изучения (1-2 правильных ответа)
    LEARNED = "learned"   # Изучено (3+ правильных ответов)

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
    markup.row(types.KeyboardButton("🏁 Завершить занятие"))
    return markup

def get_next_keyboard():
    """Создание клавиатуры для перехода к следующему слову"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("➡️ Далее"))
    markup.row(types.KeyboardButton("🏁 Завершить занятие"))
    return markup

def get_retry_keyboard():
    """Создание клавиатуры для повторной попытки"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🔄 Повторить"))
    markup.row(
        types.KeyboardButton("💡 Подсказка"),
        types.KeyboardButton("➡️ Далее")
    )
    markup.row(types.KeyboardButton("🏁 Завершить занятие"))
    return markup

def normalize_text(text: str) -> str:
    """Нормализация текста для сравнения"""
    text = text.strip()
    replacements = {
        'è': 'e', 'È': 'e', 'E': 'e', 'é': 'e', 'É': 'e',
        'à': 'a', 'À': 'a',
        'ì': 'i', 'Ì': 'i',
        'ò': 'o', 'Ò': 'o',
        'ù': 'u', 'Ù': 'u'
    }
    
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    return result.strip()

def check_answer(user_answer: str, example: dict, translation_direction: str) -> bool:
    """Проверка правильности ответа"""
    user_answer = user_answer.strip()
    
    if translation_direction == "ru_to_it":
        correct_answer = example["итальянский"]
        alternatives = example.get("альтернативы_ит", [])
    else:
        correct_answer = example["русский"]
        alternatives = example.get("альтернативы_рус", [])
    
    # Проверяем точное совпадение
    if user_answer == correct_answer:
        return True
        
    # Проверяем альтернативы
    if user_answer in alternatives:
        return True
        
    # Проверяем с нормализацией
    normalized_user = normalize_text(user_answer)
    if normalized_user == normalize_text(correct_answer):
        return True
        
    # Проверяем альтернативы с нормализацией
    for alt in alternatives:
        if normalized_user == normalize_text(alt):
            return True
            
    return False
	# Функции для работы с данными пользователя

def load_user_data(user_id: int) -> dict:
    """Загрузка данных пользователя"""
    logger.debug(f"Loading data for user {user_id}")
    if not os.path.exists('user_data'):
        os.makedirs('user_data')
        
    file_path = f'user_data/user_{user_id}.json'
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Successfully loaded data for user {user_id}")
                return data
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
            return init_user_data(user_id)
    
    return init_user_data(user_id)

def save_user_data(user_id: int, data: dict):
    """Сохранение данных пользователя"""
    logger.debug(f"Saving data for user {user_id}")
    if not os.path.exists('user_data'):
        os.makedirs('user_data')
        
    file_path = f'user_data/user_{user_id}.json'
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Successfully saved data for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

def init_user_data(user_id: int) -> dict:
    """Инициализация данных нового пользователя"""
    logger.info(f"Initializing new data for user {user_id}")
    
    current_time = datetime.datetime.now().isoformat()
    
    # Получаем список всех доступных слов
    all_words = list(VOCABULARY["Буду изучать"].keys())
    random.shuffle(all_words)
    
    # Берем первые 20 слов для изучения
    learning_words = []
    for word in all_words[:20]:
        learning_words.append({
            "word": word,
            "translation": VOCABULARY["Буду изучать"][word]["перевод"],
            "status": WordStatus.NEW,
            "correct_answers": 0,
            "next_review": current_time,
            "interval": 4
        })
    
    data = {
        "user_id": user_id,
        "active_words": learning_words,
        "learned_words": [],
        "remaining_words": all_words[20:],
        "current_session": [],
        "current_word_index": 0,
        "last_update": current_time
    }
    
    save_user_data(user_id, data)
    logger.info(f"Created initial data for user {user_id} with {len(learning_words)} words")
    return data

def reset_user_data(user_id: int) -> dict:
    """Сброс данных пользователя"""
    logger.info(f"Resetting data for user {user_id}")
    
    # Удаляем текущий файл данных
    file_path = f'user_data/user_{user_id}.json'
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.debug(f"Removed old data file for user {user_id}")
        except Exception as e:
            logger.error(f"Error removing old data file: {e}")
    
    # Создаем новые данные
    return init_user_data(user_id)

def calculate_next_interval(correct_answers: int) -> int:
    """Расчет следующего интервала повторения"""
    if correct_answers >= 3:
        return 24  # 24 часа для изученных слов
    elif correct_answers == 2:
        return 8   # 8 часов
    elif correct_answers == 1:
        return 4   # 4 часа
    else:
        return 1   # 1 час для новых слов

def get_words_for_review(user_data: dict) -> List[dict]:
    """Получение слов для повторения"""
    current_time = datetime.datetime.now()
    words_to_review = []
    
    # Проверяем наличие старых слов в данных
    for word in user_data["active_words"]:
        if word["word"] not in VOCABULARY["Буду изучать"]:
            logger.warning(f"Found obsolete word {word['word']}, need to reset data")
            return []
    
    # Если все слова новые - возвращаем их все
    if all(word.get("status", WordStatus.NEW) == WordStatus.NEW 
           for word in user_data["active_words"]):
        logger.debug("All words are new, returning all active words")
        return user_data["active_words"]
    
    # Иначе проверяем время следующего повторения
    for word in user_data["active_words"]:
        try:
            next_review = datetime.datetime.fromisoformat(word["next_review"])
            if next_review <= current_time:
                words_to_review.append(word)
        except Exception as e:
            logger.error(f"Error processing review time for word {word}: {e}")
            continue
            
    logger.debug(f"Found {len(words_to_review)} words for review")
    return words_to_review

def update_word_status(word: dict) -> str:
    """Обновление статуса слова на основе количества правильных ответов"""
    correct_answers = word.get("correct_answers", 0)
    if correct_answers >= 3:
        return WordStatus.LEARNED
    elif correct_answers > 0:
        return WordStatus.LEARNING
    else:
        return WordStatus.NEW
		# Обработчики команд и сообщений

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot")
    
    # Инициализируем данные пользователя
    user_data = load_user_data(user_id)
    
    # Инициализируем состояние
    user_states[user_id] = {
        "translation_direction": "ru_to_it",
        "awaiting_answer": False
    }
    
    active_count = len(user_data["active_words"])
    learned_count = len(user_data["learned_words"])
    
    welcome_text = (
        "*Привет! Я бот для изучения итальянского языка.*\n\n"
        f"📚 Активных слов: {active_count}\n"
        f"✅ Изучено слов: {learned_count}\n\n"
        "🔹 *'Начать повторение'* - для изучения слов\n"
        "🔹 *'Сменить направление'* - выбор направления перевода\n"
        "🔹 *'Статистика'* - для просмотра прогресса\n"
        "🔹 *'Помощь'* - справка по командам\n\n"
        "Используйте /reset для сброса прогресса\n\n"
        "Начнём? 😊"
    )
    
    bot.reply_to(
        message,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(commands=['reset'])
def handle_reset(message):
    """Обработка команды /reset"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested data reset")
    
    # Сбрасываем данные
    reset_user_data(user_id)
    
    # Сбрасываем состояние
    user_states[user_id] = {
        "translation_direction": "ru_to_it",
        "awaiting_answer": False
    }
    
    bot.reply_to(
        message,
        "🔄 Данные сброшены. Начинаем обучение сначала!",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text in ["🎯 Начать повторение", "/review"])
def start_review(message):
    """Начало сессии повторения"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} started review session")
    
    try:
        user_data = load_user_data(user_id)
        
        # Проверяем, есть ли слова из старого словаря
        for word in user_data["active_words"]:
            if word["word"] not in VOCABULARY["Буду изучать"]:
                logger.info(f"Found old vocabulary, resetting user data")
                user_data = reset_user_data(user_id)
                bot.reply_to(
                    message,
                    "📚 Словарь был обновлен. Начинаем обучение с новыми словами!",
                    reply_markup=get_main_keyboard()
                )
                break
        
        # Получаем слова для повторения
        words_to_review = get_words_for_review(user_data)
        logger.debug(f"Got {len(words_to_review)} words for review")
        
        if not words_to_review:
            # Находим время следующего повторения
            next_review = None
            for word in user_data["active_words"]:
                try:
                    review_time = datetime.datetime.fromisoformat(word["next_review"])
                    if next_review is None or review_time < next_review:
                        next_review = review_time
                except:
                    continue
            
            if next_review:
                time_diff = next_review - datetime.datetime.now()
                hours = int(time_diff.total_seconds() // 3600)
                minutes = int((time_diff.total_seconds() % 3600) // 60)
                time_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
                
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
        
        # Начинаем новую сессию
        random.shuffle(words_to_review)
        user_data["current_session"] = words_to_review
        user_data["current_word_index"] = 0
        save_user_data(user_id, user_data)
        
        show_current_exercise(message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Error in start_review: {e}")
        # При любой ошибке сбрасываем данные
        reset_user_data(user_id)
        bot.reply_to(
            message,
            "❌ Произошла ошибка. Данные сброшены, попробуйте начать заново.",
            reply_markup=get_main_keyboard()
        )

def show_current_exercise(chat_id: int, user_id: int):
    """Показ текущего упражнения"""
    logger.debug(f"Showing exercise for user {user_id}")
    
    user_data = load_user_data(user_id)
    if not user_data["current_session"]:
        logger.error(f"No current session for user {user_id}")
        return
        
    current_word = user_data["current_session"][user_data["current_word_index"]]
    word_data = VOCABULARY["Буду изучать"][current_word["word"]]
    example = random.choice(word_data["примеры"])
    
    # Определяем направление перевода
    state = user_states.get(user_id, {})
    translation_direction = state.get("translation_direction", "ru_to_it")
    
    if translation_direction == "ru_to_it":
        question = example["русский"]
        direction_text = "итальянский"
    else:
        question = example["итальянский"]
        direction_text = "русский"
    
    # Создаем сообщение
    progress_bar = "🟢" * current_word.get("correct_answers", 0) + "⚪️" * (3 - current_word.get("correct_answers", 0))
    message_text = (
        f"*{current_word['word']} - {current_word['translation']}*\n\n"
        f"Переведите на {direction_text}:\n"
        f"*{question}*\n\n"
        "❗️ Учитывайте заглавные буквы и знаки препинания\n\n"
        f"Прогресс изучения: {progress_bar}\n"
        f"_Слово {user_data['current_word_index'] + 1} из {len(user_data['current_session'])}_"
    )
    
    # Обновляем состояние
    user_states[user_id] = {
        "translation_direction": translation_direction,
        "awaiting_answer": True,
        "current_example": example
    }
    
    bot.send_message(
        chat_id,
        message_text,
        parse_mode='Markdown',
        reply_markup=get_exercise_keyboard()
    )
    
    logger.debug(f"Exercise shown for user {user_id}, word: {current_word['word']}")
	@bot.message_handler(func=lambda message: message.text == "➡️ Далее")
def next_exercise(message):
    """Переход к следующему упражнению"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} pressed Next button")
    
    user_data = load_user_data(user_id)
    
    # Проверяем, есть ли ещё слова в сессии
    if not user_data["current_session"] or user_data["current_word_index"] >= len(user_data["current_session"]) - 1:
        # Если текущая сессия закончилась, проверяем есть ли ещё слова для повторения
        words_to_review = get_words_for_review(user_data)
        if not words_to_review:
            bot.reply_to(
                message,
                "Сессия завершена! На данный момент нет слов для повторения.",
                reply_markup=get_main_keyboard()
            )
            return
        # Начинаем новую сессию
        random.shuffle(words_to_review)
        user_data["current_session"] = words_to_review
        user_data["current_word_index"] = 0
    else:
        # Переходим к следующему слову
        user_data["current_word_index"] += 1
    
    save_user_data(user_id, user_data)
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "🔄 Повторить")
def retry_answer(message):
    """Повторная попытка ответа"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} retrying answer")
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "💡 Подсказка")
def show_hint(message):
    """Показ подсказки"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested hint")
    
    state = user_states.get(user_id, {})
    if not state.get("awaiting_answer"):
        bot.reply_to(message, "❌ Сначала начните упражнение")
        return
    
    example = state.get("current_example")
    if not example:
        bot.reply_to(message, "❌ Произошла ошибка. Начните упражнение заново")
        return
    
    if state["translation_direction"] == "ru_to_it":
        answer = example["итальянский"]
    else:
        answer = example["русский"]
    
    # Создаем подсказку (первые буквы слов)
    words = answer.split()
    hint_words = []
    for word in words:
        if len(word) > 0:
            # Сохраняем регистр первой буквы
            hint_words.append(word[0] + '_' * (len(word)-1))
    hint = ' '.join(hint_words)
    
    bot.reply_to(
        message,
        f"💡 Подсказка:\n{hint}\n\n❗️ Учитывайте заглавные буквы и знаки препинания!",
        reply_markup=get_exercise_keyboard()
    )
    logger.debug(f"Hint shown for user {user_id}")

@bot.message_handler(func=lambda message: message.text == "⏩ Пропустить")
def skip_word(message):
    """Пропуск текущего слова"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} skipping word")
    
    user_data = load_user_data(user_id)
    if not user_data["current_session"] or user_data["current_word_index"] >= len(user_data["current_session"]):
        return
        
    current_word = user_data["current_session"][user_data["current_word_index"]]
    logger.debug(f"Skipping word '{current_word['word']}' for user {user_id}")
    
    # При пропуске не меняем статистику слова
    user_data["current_word_index"] += 1
    save_user_data(user_id, user_data)
    
    bot.reply_to(message, "⏩ Слово пропущено")
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "🏁 Завершить занятие")
def end_session(message):
    """Завершение текущей сессии"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} ending session")
    
    user_data = load_user_data(user_id)
    
    # Находим ближайшее время следующего повторения
    next_review = None
    for word in user_data["active_words"]:
        review_time = datetime.datetime.fromisoformat(word["next_review"])
        if next_review is None or review_time < next_review:
            next_review = review_time
    
    # Очищаем текущую сессию
    user_data["current_session"] = []
    user_data["current_word_index"] = 0
    save_user_data(user_id, user_data)
    
    # Формируем сообщение
    summary_text = ["🏁 *Занятие завершено!*\n"]
    
    if next_review:
        time_diff = next_review - datetime.datetime.now()
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        
        if hours > 0:
            time_str = f"{hours}ч {minutes}мин"
        else:
            time_str = f"{minutes}мин"
            
        summary_text.append(f"⏰ Следующее повторение через: *{time_str}*\n")
        summary_text.append("Я пришлю уведомление, когда придет время!")
    
    bot.reply_to(
        message,
        "\n".join(summary_text),
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )
    
    # Сбрасываем состояние пользователя
    user_states[user_id] = {
        "translation_direction": user_states[user_id].get("translation_direction", "ru_to_it"),
        "awaiting_answer": False
    }
	