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
import threading  # Добавляем этот импорт
import requests  # И этот тоже нужен для проверки соединения

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

# Константы для статусов слов
WORD_STATUS = {
    "NEW": "new",           # 0 правильных ответов
    "LEARNING": "learning", # 1-2 правильных ответа
    "LEARNED": "learned"    # 3+ правильных ответа
}

def calculate_next_interval(correct_answers: int) -> int:
    """Расчет следующего интервала повторения в часах"""
    if correct_answers >= 3:
        return 24  # 24 часа для изученных слов
    elif correct_answers == 2:
        return 8   # 8 часов
    elif correct_answers == 1:
        return 4   # 4 часа
    else:
        return 1   # 1 час для новых слов

def create_word_data(word: str, translation: str) -> dict:
    """Создание структуры данных для нового слова"""
    return {
        "word": word,
        "translation": translation,
        "correct_answers": 0,
        "next_review": datetime.datetime.now().isoformat(),
        "status": WORD_STATUS["NEW"],
        "total_attempts": 0
    }

def create_initial_user_data(user_id: int) -> dict:
    """Создание начальных данных для нового пользователя"""
    logger.info(f"Creating initial data for user {user_id}")
    
    # Получаем все доступные слова
    all_words = list(VOCABULARY["Буду изучать"].keys())
    random.shuffle(all_words)
    
    # Берем первые 20 слов для изучения
    initial_words = []
    for word in all_words[:20]:
        word_data = VOCABULARY["Буду изучать"][word]
        initial_words.append(create_word_data(word, word_data["перевод"]))
    
    # Создаем структуру данных пользователя
    data = {
        "user_id": user_id,
        "active_words": initial_words,
        "learned_words": [],
        "remaining_words": all_words[20:],
        "current_session": [],
        "current_word_index": 0,
        "last_update": datetime.datetime.now().isoformat()
    }
    
    # Сохраняем данные
    save_user_data(user_id, data)
    logger.info(f"Created initial data with {len(initial_words)} words")
    return data

def load_user_data(user_id: int) -> dict:
    """Загрузка данных пользователя"""
    logger.debug(f"Loading data for user {user_id}")
    if not os.path.exists('user_data'):
        os.makedirs('user_data')
        
    file_path = f'user_data/user_{user_id}.json'
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем наличие всех необходимых полей
            required_fields = ["active_words", "learned_words", "remaining_words"]
            if not all(field in data for field in required_fields):
                logger.warning(f"Missing required fields in data")
                return create_initial_user_data(user_id)
            
            # Проверяем актуальность слов
            has_old_words = any(
                word["word"] not in VOCABULARY["Буду изучать"] 
                for word in data["active_words"]
            )
            
            if has_old_words:
                logger.info(f"Found old vocabulary, creating new data")
                return create_initial_user_data(user_id)
            
            logger.debug(f"Successfully loaded data")
            return data
            
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return create_initial_user_data(user_id)
    
    return create_initial_user_data(user_id)

def save_user_data(user_id: int, data: dict):
    """Сохранение данных пользователя"""
    logger.debug(f"Saving data for user {user_id}")
    if not os.path.exists('user_data'):
        os.makedirs('user_data')
        
    file_path = f'user_data/user_{user_id}.json'
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug("Data saved successfully")
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def get_words_for_review(user_data: dict) -> List[dict]:
    """Получение списка слов для повторения"""
    current_time = datetime.datetime.now()
    logger.debug(f"Checking words for review at {current_time}")
    
    # Если все слова новые, возвращаем все
    if all(word.get("correct_answers", 0) == 0 for word in user_data["active_words"]):
        logger.debug("All words are new, returning all active words")
        return user_data["active_words"]
    
    # Иначе проверяем время следующего повторения
    words_to_review = []
    for word in user_data["active_words"]:
        try:
            next_review = datetime.datetime.fromisoformat(word["next_review"])
            logger.debug(f"Word {word['word']}: next review at {next_review}, current time: {current_time}")
            
            # Слово готово к повторению если:
            # 1. Время следующего повторения наступило
            # 2. Слово не изучено полностью (меньше 3 правильных ответов)
            if (next_review <= current_time and 
                word.get("correct_answers", 0) < 3):
                words_to_review.append(word)
                logger.debug(f"Added word {word['word']} to review list")
        except Exception as e:
            logger.error(f"Error processing review time for word {word.get('word')}: {e}")
            continue
    
    logger.debug(f"Found {len(words_to_review)} words ready for review")
    return words_to_review

def update_word_progress(word: dict, is_correct: bool) -> dict:
    """Обновление прогресса слова"""
    # Увеличиваем счетчик попыток
    word["total_attempts"] = word.get("total_attempts", 0) + 1
    
    if is_correct:
        # Увеличиваем счетчик правильных ответов
        word["correct_answers"] = word.get("correct_answers", 0) + 1
        
        # Обновляем статус
        if word["correct_answers"] >= 3:
            word["status"] = WORD_STATUS["LEARNED"]
        elif word["correct_answers"] > 0:
            word["status"] = WORD_STATUS["LEARNING"]
            
        # Обновляем время следующего повторения
        next_interval = calculate_next_interval(word["correct_answers"])
        word["next_review"] = (
            datetime.datetime.now() + 
            datetime.timedelta(hours=next_interval)
        ).isoformat()
    
    return word
def get_main_keyboard() -> types.ReplyKeyboardMarkup:
    """Создание основной клавиатуры"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🎯 Начать повторение"))
    markup.row(
        types.KeyboardButton("🔄 Сменить направление перевода"),
        types.KeyboardButton("📊 Статистика")
    )
    markup.row(types.KeyboardButton("ℹ️ Помощь"))
    return markup

def get_exercise_keyboard() -> types.ReplyKeyboardMarkup:
    """Создание клавиатуры для упражнения"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("💡 Подсказка"))
    markup.row(
        types.KeyboardButton("🔄 Сменить направление"),
        types.KeyboardButton("⏩ Пропустить")
    )
    markup.row(types.KeyboardButton("🏁 Завершить занятие"))
    return markup

def get_next_keyboard() -> types.ReplyKeyboardMarkup:
    """Создание клавиатуры для перехода к следующему слову"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("➡️ Далее"))
    markup.row(types.KeyboardButton("🏁 Завершить занятие"))
    return markup

def get_retry_keyboard() -> types.ReplyKeyboardMarkup:
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
    text = text.lower().strip()
    replacements = {
        'è': 'e', 'È': 'e', 'é': 'e', 'É': 'e',
        'à': 'a', 'À': 'a',
        'ì': 'i', 'Ì': 'i',
        'ò': 'o', 'Ò': 'o',
        'ù': 'u', 'Ù': 'u'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text.strip()

def check_answer(user_answer: str, correct_answer: str, alternatives: List[str]) -> bool:
    """Проверка правильности ответа"""
    user_answer = user_answer.strip()
    
    # Проверяем точное совпадение
    if user_answer == correct_answer:
        return True
        
    # Проверяем альтернативы
    if user_answer in alternatives:
        return True
        
    # Проверяем с нормализацией
    normalized_user = normalize_text(user_answer)
    normalized_correct = normalize_text(correct_answer)
    if normalized_user == normalized_correct:
        return True
        
    # Проверяем альтернативы с нормализацией
    for alt in alternatives:
        if normalized_user == normalize_text(alt):
            return True
            
    return False

def show_current_exercise(chat_id: int, user_id: int):
    logger.debug(f"Showing exercise for user {user_id}")
    
    try:
        user_data = load_user_data(user_id)
        current_session = user_data.get("current_session", [])
        current_index = user_data.get("current_word_index", 0)
        
        if not current_session or current_index >= len(current_session):
            logger.error("No active session or invalid index")
            bot.send_message(chat_id, "❌ Ошибка. Начните новое повторение.",
                           reply_markup=get_main_keyboard())
            return
        
        current_word = current_session[current_index]
        word_data = VOCABULARY["Буду изучать"].get(current_word["word"])
        
        if not word_data or not word_data.get("примеры"):
            logger.error(f"Invalid word data for {current_word.get('word')}")
            bot.send_message(chat_id, "❌ Ошибка в данных слова.",
                           reply_markup=get_main_keyboard())
            return
        
        example = random.choice(word_data["примеры"])
        translation_direction = user_states.get(user_id, {}).get("translation_direction", "ru_to_it")
        
        question = example["русский"] if translation_direction == "ru_to_it" else example["итальянский"]
        direction_text = "итальянский" if translation_direction == "ru_to_it" else "русский"
        
        user_states[user_id] = {
            "translation_direction": translation_direction,
            "awaiting_answer": True,
            "current_example": example,
            "last_activity": datetime.datetime.now().isoformat()
        }
        
        progress_bar = "🟢" * current_word["correct_answers"] + "⚪️" * (3 - current_word["correct_answers"])
        message_text = (
            f"*{current_word['word']} - {current_word['translation']}*\n\n"
            f"Переведите на {direction_text}:\n"
            f"*{question}*\n\n"
            f"Прогресс: {progress_bar}\n"
            f"_{current_index + 1} из {len(current_session)}_"
        )
        
        bot.send_message(chat_id, message_text,
                        parse_mode='Markdown',
                        reply_markup=get_exercise_keyboard())
        
    except Exception as e:
        logger.error(f"Error in show_exercise: {e}", exc_info=True)
        bot.send_message(chat_id, "❌ Произошла ошибка.",
                        reply_markup=get_main_keyboard())
                        
                        
@bot.message_handler(commands=['start'])
def send_welcome(message):
   """Обработка команды /start"""
   user_id = message.from_user.id
   logger.info(f"User {user_id} started the bot")
   
   try:
       # Загружаем или создаем данные
       user_data = load_user_data(user_id)
       
       # Инициализируем состояние
       user_states[user_id] = {
           "translation_direction": "ru_to_it",
           "awaiting_answer": False,
           "current_example": None,
           "last_activity": datetime.datetime.now().isoformat()
       }
       
       welcome_text = (
           "*Привет! Я бот для изучения итальянского языка.*\n\n"
           f"📚 Активных слов: {len(user_data['active_words'])}\n"
           f"✅ Изучено слов: {len(user_data['learned_words'])}\n\n"
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
       
   except Exception as e:
       logger.error(f"Error in send_welcome: {e}", exc_info=True)
       bot.reply_to(
           message,
           "❌ Произошла ошибка. Попробуйте еще раз.",
           reply_markup=get_main_keyboard()
       )

@bot.message_handler(commands=['reset'])
def handle_reset(message):
   """Обработка команды /reset"""
   user_id = message.from_user.id
   logger.info(f"User {user_id} requested data reset")
   
   try:
       # Создаем новые данные
       create_initial_user_data(user_id)
       
       # Сбрасываем состояние
       user_states[user_id] = {
           "translation_direction": "ru_to_it",
           "awaiting_answer": False,
           "current_example": None,
           "last_activity": datetime.datetime.now().isoformat()
       }
       
       bot.reply_to(
           message,
           "🔄 Данные сброшены. Начинаем обучение сначала!",
           reply_markup=get_main_keyboard()
       )
   except Exception as e:
       logger.error(f"Error in handle_reset: {e}")
       bot.reply_to(
           message,
           "❌ Произошла ошибка при сбросе данных",
           reply_markup=get_main_keyboard()
       )

@bot.message_handler(func=lambda message: message.text in ["🎯 Начать повторение", "📯 Начать повторение", "/review"])
def start_review(message):
    user_id = message.from_user.id
    logger.info(f"User {user_id} starting review session")
    
    try:
        user_data = load_user_data(user_id)
        words_to_review = get_words_for_review(user_data)
        
        if not words_to_review:
            logger.debug("No words to review")
            next_review = min((datetime.datetime.fromisoformat(word["next_review"]) 
                             for word in user_data["active_words"]), default=None)
            
            if next_review:
                time_diff = next_review - datetime.datetime.now()
                if time_diff.total_seconds() > 0:
                    hours = int(time_diff.total_seconds() // 3600)
                    minutes = int((time_diff.total_seconds() % 3600) // 60)
                    time_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
                    bot.reply_to(message, 
                               f"🕒 Нет слов для повторения!\n\nСледующее через: {time_str}",
                               reply_markup=get_main_keyboard())
                    return
            
            bot.reply_to(message, "🕒 Нет слов для повторения!", 
                        reply_markup=get_main_keyboard())
            return
        
        random.shuffle(words_to_review)
        user_data["current_session"] = words_to_review
        user_data["current_word_index"] = 0
        save_user_data(user_id, user_data)
        
        # Важно: инициализируем состояние до показа упражнения
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": True,
            "current_example": None,
            "last_activity": datetime.datetime.now().isoformat()
        }
        
        show_current_exercise(message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Error in start_review: {e}", exc_info=True)
        bot.reply_to(message, "❌ Ошибка. Попробуйте еще раз.", 
                    reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_statistics(message):
   """Показ статистики обучения"""
   user_id = message.from_user.id
   logger.info(f"User {user_id} requested statistics")
   
   try:
       user_data = load_user_data(user_id)
       
       # Подсчет слов по статусам
       active_words = user_data["active_words"]
       new_words = sum(1 for w in active_words if w["correct_answers"] == 0)
       learning_words = sum(1 for w in active_words if 0 < w["correct_answers"] < 3)
       learned_words = len(user_data["learned_words"])
       
       # Подсчет слов для повторения
       words_to_review = get_words_for_review(user_data)
       
       stats_message = [
           "📊 *Статистика обучения:*\n",
           f"📚 Активные слова: {len(active_words)}",
           f"🆕 Новые слова (0 ответов): {new_words}",
           f"📝 В процессе (1-2 ответа): {learning_words}",
           f"✅ Изучено (3+ ответа): {learned_words}",
           f"⏰ Готово к повторению: {len(words_to_review)}\n",
           "Слово считается изученным после 3 правильных ответов",
           f"Всего слов в словаре: {len(VOCABULARY['Буду изучать'])}"
       ]
       
       bot.reply_to(
           message,
           "\n".join(stats_message),
           parse_mode='Markdown',
           reply_markup=get_main_keyboard()
       )
       
   except Exception as e:
       logger.error(f"Error in show_statistics: {e}", exc_info=True)
       bot.reply_to(
           message,
           "❌ Произошла ошибка при отображении статистики",
           reply_markup=get_main_keyboard()
       )
@bot.message_handler(func=lambda message: message.text in ["🔄 Сменить направление перевода", "🔄 Сменить направление"])
def switch_translation_direction(message):
   """Смена направления перевода"""
   user_id = message.from_user.id
   logger.info(f"User {user_id} switching translation direction")
   
   try:
       state = user_states.get(user_id, {"translation_direction": "ru_to_it"})
       current_direction = state.get("translation_direction", "ru_to_it")
       new_direction = "it_to_ru" if current_direction == "ru_to_it" else "ru_to_it"
       
       # Сохраняем состояние
       awaiting_answer = state.get("awaiting_answer", False)
       current_example = state.get("current_example")
       
       user_states[user_id] = {
           "translation_direction": new_direction,
           "awaiting_answer": awaiting_answer,
           "current_example": current_example,
           "last_activity": datetime.datetime.now().isoformat()
       }
       
       direction_text = "итальянский → русский" if new_direction == "it_to_ru" else "русский → итальянский"
       bot.reply_to(
           message,
           f"🔄 Направление перевода изменено на:\n*{direction_text}*",
           parse_mode='Markdown'
       )
       
       # Если есть активная сессия, показываем новое упражнение
       if awaiting_answer:
           show_current_exercise(message.chat.id, user_id)
           
   except Exception as e:
       logger.error(f"Error in switch_direction: {e}")
       bot.reply_to(
           message,
           "❌ Произошла ошибка при смене направления",
           reply_markup=get_main_keyboard()
       )

@bot.message_handler(func=lambda message: message.text == "💡 Подсказка")
def show_hint(message):
   """Показ подсказки"""
   user_id = message.from_user.id
   logger.info(f"User {user_id} requested hint")
   
   try:
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
       
       # Создаем подсказку
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
       logger.debug(f"Hint shown for user {user_id}")
       
   except Exception as e:
       logger.error(f"Error showing hint: {e}")
       bot.reply_to(
           message,
           "❌ Произошла ошибка",
           reply_markup=get_exercise_keyboard()
       )

@bot.message_handler(func=lambda message: message.text == "➡️ Далее")
def next_exercise(message):
   """Переход к следующему упражнению"""
   user_id = message.from_user.id
   logger.info(f"User {user_id} pressed Next button")
   
   try:
       user_data = load_user_data(user_id)
       
       # Проверяем, есть ли ещё слова в текущей сессии
       current_session = user_data.get("current_session", [])
       current_index = user_data.get("current_word_index", 0)
       
       if not current_session or current_index >= len(current_session) - 1:
           # Проверяем есть ли новые слова для повторения
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
       
       # Обновляем состояние
       state = user_states.get(user_id, {})
       state["awaiting_answer"] = True
       user_states[user_id] = state
       
       show_current_exercise(message.chat.id, user_id)
       
   except Exception as e:
       logger.error(f"Error in next_exercise: {e}")
       bot.reply_to(
           message,
           "❌ Произошла ошибка. Попробуйте начать заново.",
           reply_markup=get_main_keyboard()
       )

@bot.message_handler(func=lambda message: message.text == "🔄 Повторить")
def retry_answer(message):
   """Повторная попытка ответа"""
   user_id = message.from_user.id
   logger.info(f"User {user_id} retrying answer")
   
   try:
       state = user_states.get(user_id, {})
       state["awaiting_answer"] = True
       user_states[user_id] = state
       
       show_current_exercise(message.chat.id, user_id)
       
   except Exception as e:
       logger.error(f"Error in retry: {e}")
       bot.reply_to(
           message,
           "❌ Произошла ошибка. Начните заново.",
           reply_markup=get_main_keyboard()
       )

@bot.message_handler(func=lambda message: message.text == "⏩ Пропустить")
def skip_word(message):
   """Пропуск текущего слова"""
   user_id = message.from_user.id
   logger.info(f"User {user_id} skipping word")
   
   try:
       user_data = load_user_data(user_id)
       
       if not user_data.get("current_session"):
           return
           
       # Переходим к следующему слову без изменения статистики
       user_data["current_word_index"] += 1
       save_user_data(user_id, user_data)
       
       bot.reply_to(message, "⏩ Слово пропущено")
       show_current_exercise(message.chat.id, user_id)
       
   except Exception as e:
       logger.error(f"Error skipping word: {e}")
       bot.reply_to(
           message,
           "❌ Произошла ошибка",
           reply_markup=get_main_keyboard()
       )
@bot.message_handler(func=lambda message: message.text == "🏁 Завершить занятие")
def end_session(message):
   """Завершение текущей сессии"""
   user_id = message.from_user.id
   logger.info(f"User {user_id} ending session")
   
   try:
       user_data = load_user_data(user_id)
       
       # Находим время следующего повторения
       current_time = datetime.datetime.now()
       next_review = None
       
       for word in user_data["active_words"]:
           try:
               review_time = datetime.datetime.fromisoformat(word["next_review"])
               if next_review is None or review_time < next_review:
                   next_review = review_time
           except:
               continue
       
       # Очищаем текущую сессию
       user_data["current_session"] = []
       user_data["current_word_index"] = 0
       save_user_data(user_id, user_data)
       
       # Формируем сообщение
       summary_text = ["🏁 *Занятие завершено!*\n"]
       
       if next_review and next_review > current_time:
           time_diff = next_review - current_time
           hours = int(time_diff.total_seconds() // 3600)
           minutes = int((time_diff.total_seconds() % 3600) // 60)
           time_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
           summary_text.append(f"⏰ Следующее повторение через: *{time_str}*\n")
           
           # Сохраняем время следующего уведомления
           user_states[user_id] = {
               "translation_direction": "ru_to_it",
               "awaiting_answer": False,
               "next_notification": next_review.isoformat(),
               "last_activity": current_time.isoformat()
           }
           
           summary_text.append("Я пришлю уведомление, когда придет время!")
       
       bot.reply_to(
           message,
           "\n".join(summary_text),
           parse_mode='Markdown',
           reply_markup=get_main_keyboard()
       )
       
   except Exception as e:
       logger.error(f"Error ending session: {e}", exc_info=True)
       bot.reply_to(
           message,
           "❌ Произошла ошибка. Сессия завершена.",
           reply_markup=get_main_keyboard()
       )

@bot.message_handler(func=lambda message: True)
def handle_answer(message):
   """Обработка ответов пользователя"""
   user_id = message.from_user.id
   logger.debug(f"Received message from user {user_id}: {message.text}")
   
   state = user_states.get(user_id, {})
   if not state.get("awaiting_answer"):
       return

   try:
       user_data = load_user_data(user_id)
       
       if not user_data["current_session"]:
           logger.debug("No current session")
           return

       current_word = user_data["active_words"][user_data["current_word_index"]]
       example = state.get("current_example")
       
       if not example:
           logger.error(f"No current example found for user {user_id}")
           bot.reply_to(message, "❌ Произошла ошибка. Начните упражнение заново")
           return

       # Проверяем ответ
       if state["translation_direction"] == "ru_to_it":
           correct_answer = example["итальянский"]
           alternatives = example.get("альтернативы_ит", [])
       else:
           correct_answer = example["русский"]
           alternatives = example.get("альтернативы_рус", [])

       is_correct = check_answer(message.text, correct_answer, alternatives)
       logger.debug(f"Answer check result: {is_correct}")

       # Обновляем прогресс слова
       if is_correct:
           # Увеличиваем счетчик правильных ответов
           current_word["correct_answers"] = current_word.get("correct_answers", 0) + 1
           
           # Обновляем время следующего повторения
           next_interval = calculate_next_interval(current_word["correct_answers"])
           current_word["next_review"] = (
               datetime.datetime.now() + 
               datetime.timedelta(hours=next_interval)
           ).isoformat()
           
           # Если слово изучено (3+ правильных ответа)
           if current_word["correct_answers"] >= 3:
               logger.debug(f"Word {current_word['word']} learned")
               user_data["learned_words"].append(current_word)
               user_data["active_words"].remove(current_word)
               
               # Добавляем новое слово если есть
               if user_data["remaining_words"]:
                   new_word = random.choice(user_data["remaining_words"])
                   user_data["remaining_words"].remove(new_word)
                   
                   word_data = VOCABULARY["Буду изучать"][new_word]
                   user_data["active_words"].append({
                       "word": new_word,
                       "translation": word_data["перевод"],
                       "correct_answers": 0,
                       "next_review": datetime.datetime.now().isoformat(),
                       "total_attempts": 0
                   })

       # Сохраняем обновленные данные
       save_user_data(user_id, user_data)

       # Формируем ответное сообщение
       progress_bar = "🟢" * current_word["correct_answers"] + "⚪️" * (3 - current_word["correct_answers"])

       if is_correct:
           response = (
               "✅ *Правильно!*\n\n"
               f"Ваш ответ: _{message.text}_\n"
               f"Прогресс: {progress_bar}"
           )
           markup = get_next_keyboard()
       else:
           response = (
               "❌ *Ошибка!*\n\n"
               f"Ваш ответ: _{message.text}_\n"
               f"Правильный ответ: *{correct_answer}*\n"
               f"Прогресс: {progress_bar}"
           )
           markup = get_retry_keyboard()

       # Обновляем состояние
       state["awaiting_answer"] = False
       state["last_activity"] = datetime.datetime.now().isoformat()
       user_states[user_id] = state

       bot.reply_to(
           message,
           response,
           parse_mode='Markdown',
           reply_markup=markup
       )

   except Exception as e:
       logger.error(f"Error handling answer: {e}", exc_info=True)
       bot.reply_to(
           message,
           "❌ Произошла ошибка. Попробуйте начать заново.",
           reply_markup=get_main_keyboard()
       )
def check_and_send_notifications():
    """Проверка и отправка уведомлений"""
    logger.info("Starting notifications checker")
    notification_cache = {}
    
    while True:
        try:
            current_time = datetime.datetime.now()
            
            # Проверяем файлы раз в 5 минут
            if not hasattr(check_and_send_notifications, 'last_check') or \
               (current_time - check_and_send_notifications.last_check).total_seconds() >= 300:
                
                if os.path.exists('user_data'):
                    for filename in os.listdir('user_data'):
                        if not filename.startswith('user_') or not filename.endswith('.json'):
                            continue
                            
                        try:
                            user_id = int(filename.split('_')[1].split('.')[0])
                            
                            # Проверяем кэш уведомлений
                            if user_id in notification_cache:
                                last_notification = notification_cache[user_id]
                                if (current_time - last_notification).total_seconds() < 1800:  # 30 минут
                                    continue
                            
                            user_data = load_user_data(user_id)
                            words = get_words_for_review(user_data)
                            
                            if len(words) > 0:
                                try:
                                    # Проверяем активность пользователя перед отправкой
                                    state = user_states.get(user_id, {})
                                    last_activity = datetime.datetime.fromisoformat(
                                        state.get('last_activity', '2000-01-01T00:00:00')
                                    )
                                    
                                    # Не отправляем, если пользователь активен
                                    if state.get('awaiting_answer') or \
                                       (current_time - last_activity).total_seconds() < 300:  # 5 минут
                                        continue
                                    
                                    notification_text = (
                                        "🔔 *Пора повторить слова!*\n\n"
                                        f"У вас {len(words)} слов готово к повторению:\n"
                                        + "\n".join(f"• {word['word']} - {word['translation']}" 
                                                  for word in words[:3])
                                    )
                                    
                                    if len(words) > 3:
                                        notification_text += f"\n\n... и ещё {len(words) - 3} слов"
                                    
                                    bot.send_message(
                                        user_id,
                                        notification_text,
                                        parse_mode='Markdown',
                                        reply_markup=get_main_keyboard()
                                    )
                                    
                                    notification_cache[user_id] = current_time
                                    logger.info(f"Notification sent to user {user_id}")
                                    
                                except telebot.apihelper.ApiException as e:
                                    if "bot was blocked by the user" in str(e):
                                        logger.warning(f"User {user_id} blocked the bot")
                                    else:
                                        logger.error(f"API error for user {user_id}: {e}")
                                except Exception as e:
                                    logger.error(f"Error sending notification to user {user_id}: {e}")
                                    
                        except Exception as e:
                            logger.error(f"Error processing user {filename}: {e}")
                            continue
                            
                check_and_send_notifications.last_check = current_time
                
            time.sleep(60)  # Проверка каждую минуту
            
        except Exception as e:
            logger.error(f"Error in notification checker: {e}")
            time.sleep(60)
            

def run_bot():
    """Запуск бота с улучшенной обработкой сетевых ошибок"""
    logger.info("=== Starting Bot ===")
    logger.info(f"Vocabulary size: {len(VOCABULARY['Буду изучать'])} words")
    
    # Увеличиваем таймауты
    telebot.apihelper.CONNECT_TIMEOUT = 30
    telebot.apihelper.READ_TIMEOUT = 30
    telebot.apihelper.RETRY_ON_ERROR = True
    
    def check_connection():
        try:
            import socket
            import requests
            # Проверяем соединение через requests
            response = requests.get('https://api.telegram.org', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_bot():
        try:
            # Проверяем соединение
            retry_count = 0
            while not check_connection():
                retry_count += 1
                wait_time = min(retry_count * 5, 60)  # Увеличиваем время ожидания, но не больше минуты
                logger.error(f"No connection to Telegram API. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            
            # Очищаем webhook и старые апдейты
            try:
                bot.delete_webhook()
                logger.info("Webhook deleted")
                bot.get_updates(offset=-1, timeout=1)
                logger.info("Updates cleared")
            except Exception as e:
                logger.error(f"Error clearing updates: {e}")
            
            # Запускаем уведомления
            notification_thread = threading.Thread(
                target=check_and_send_notifications,
                daemon=True
            )
            notification_thread.start()
            logger.info("Notification thread started")
            
            # Основной цикл с обработкой ошибок
            while True:
                try:
                    logger.info("Starting bot polling...")
                    bot.infinity_polling(
                        timeout=50,  # Увеличенный таймаут
                        long_polling_timeout=60,  # Увеличенный таймаут long polling
                        logger_level=logging.ERROR,
                        restart_on_change=True,  # Автоматический рестарт при изменениях
                        skip_pending=True,
                        allowed_updates=["message"]  # Только сообщения
                    )
                except (requests.ReadTimeout, requests.ConnectionError) as e:
                    logger.error(f"Network error: {e}")
                    time.sleep(15)  # Ждем 15 секунд перед повторной попыткой
                    continue
                except Exception as e:
                    logger.error(f"Polling error: {e}")
                    if not check_connection():
                        logger.error("Connection lost. Waiting to reconnect...")
                        time.sleep(30)
                    else:
                        time.sleep(10)
                    continue
                    
        except Exception as e:
            logger.error(f"Critical error in start_bot: {e}")
            time.sleep(30)
    
    # Основной цикл с автоматическим перезапуском
    while True:
        try:
            start_bot()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            time.sleep(60)  # Ждем минуту перед перезапуском
            continue

if __name__ == "__main__":
    try:
        import signal
        def signal_handler(sig, frame):
            logger.info("Received stop signal, shutting down...")
            os._exit(0)
        signal.signal(signal.SIGINT, signal_handler)
        
        run_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise