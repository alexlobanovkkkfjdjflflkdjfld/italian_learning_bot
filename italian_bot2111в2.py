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
    
    # Проверяем точное совпадение и совпадение без учета регистра
    if user_answer == correct_answer or user_answer.lower() == correct_answer.lower():
        return True
        
    # Проверяем альтернативы
    for alt in alternatives:
        if user_answer == alt or user_answer.lower() == alt.lower():
            return True
    
    # Проверяем с нормализацией
    normalized_user = normalize_text(user_answer.lower())
    if normalized_user == normalize_text(correct_answer.lower()):
        return True
    
    # Проверяем альтернативы с нормализацией
    for alt in alternatives:
        if normalized_user == normalize_text(alt.lower()):
            return True
            
    return False

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
    
@bot.message_handler(func=lambda message: message.text in ["ℹ️ Помощь", "/help"])
def send_help(message):
    """Обработка команды /help и кнопки Помощь"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested help")
    
    try:
        help_text = (
            "*Как пользоваться ботом:*\n\n"
            "1️⃣ *Начало работы:*\n"
            "• Нажмите '🎯 Начать повторение'\n"
            "• Выберите направление перевода\n\n"
            "2️⃣ *Во время упражнения:*\n"
            "• Переводите предложенное слово или фразу\n"
            "• Используйте '💡 Подсказка' если нужна помощь\n"
            "• '🔄 Повторить' - для повторной попытки\n"
            "• '⏩ Пропустить' - чтобы пропустить сложное слово\n"
            "• '➡️ Далее' - для перехода к следующему слову\n"
            "• '🏁 Завершить занятие' - для выхода из сессии\n\n"
            "3️⃣ *Система изучения:*\n"
            "• Каждое слово нужно правильно перевести 3 раза\n"
            "• После изучения слова добавляется новое\n"
            "• Интервалы повторения: 4ч → 8ч → 24ч\n\n"
            "4️⃣ *Команды:*\n"
            "/start - Начать сначала\n"
            "/help - Показать это сообщение\n"
            "/reset - Сбросить прогресс\n"
            "/review - Начать повторение"
        )
        
        bot.reply_to(
            message,
            help_text,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in send_help: {e}")
        bot.reply_to(
            message,
            "❌ Произошла ошибка при отображении справки",
            reply_markup=get_main_keyboard()
        )

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_statistics(message):
    """Показ статистики обучения"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested statistics")
    
    try:
        user_data = load_user_data(user_id)
        
        # Подсчет по количеству правильных ответов
        active_words = user_data["active_words"]
        new_words = 0
        learning_words = 0
        learned_words = 0

        for word in active_words:
            correct_count = word.get("correct_answers", 0)
            if correct_count == 0:
                new_words += 1
            elif correct_count < 3:
                learning_words += 1
            else:
                learned_words += 1
        
        # Подсчет слов для повторения
        words_to_review = get_words_for_review(user_data)
        
        # Находим время следующего повторения
        next_review = None
        for word in user_data["active_words"]:
            try:
                review_time = datetime.datetime.fromisoformat(word["next_review"])
                if next_review is None or review_time < next_review:
                    next_review = review_time
            except:
                continue
        
        stats_message = [
            "📊 *Статистика обучения:*\n",
            f"📚 Активные слова: {len(active_words)}",
            f"🆕 Новые слова (0 ответов): {new_words}",
            f"📝 В процессе (1-2 ответа): {learning_words}",
            f"✅ Изучено (3+ ответа): {learned_words}",
            f"⏰ Готово к повторению: {len(words_to_review)}"
        ]
        
        # Добавляем информацию о времени следующего повторения
        if next_review:
            time_diff = next_review - datetime.datetime.now()
            if time_diff.total_seconds() > 0:
                hours = int(time_diff.total_seconds() // 3600)
                minutes = int((time_diff.total_seconds() % 3600) // 60)
                time_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
                stats_message.append(f"\n⏱ Следующее повторение через: {time_str}")
        
        stats_message.extend([
            "\nСлово считается изученным после 3 правильных ответов",
            f"Всего слов в словаре: {len(VOCABULARY['Буду изучать'])}"
        ])
        
        bot.reply_to(
            message,
            "\n".join(stats_message),
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in show_statistics: {e}")
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
        
        # Сохраняем текущее состояние
        awaiting_answer = state.get("awaiting_answer", False)
        current_example = state.get("current_example")
        
        user_states[user_id] = {
            "translation_direction": new_direction,
            "awaiting_answer": awaiting_answer,
            "current_example": current_example
        }
        
        direction_text = "итальянский → русский" if new_direction == "it_to_ru" else "русский → итальянский"
        
        # Отправляем сообщение о смене направления
        bot.reply_to(
            message,
            f"🔄 Направление перевода изменено на:\n*{direction_text}*",
            parse_mode='Markdown'
        )
        
        # Если есть активная сессия, показываем новое упражнение
        if awaiting_answer:
            show_current_exercise(message.chat.id, user_id)
            
    except Exception as e:
        logger.error(f"Error in switch_translation_direction: {e}")
        bot.reply_to(
            message,
            "❌ Произошла ошибка при смене направления перевода",
            reply_markup=get_main_keyboard()
        )
    
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
        if not user_data["current_session"] or user_data["current_word_index"] >= len(user_data["current_session"]):
            return

        current_word = user_data["current_session"][user_data["current_word_index"]]
        
        # Проверяем, существует ли слово в текущем словаре
        if current_word["word"] not in VOCABULARY["Буду изучать"]:
            logger.warning(f"Word {current_word['word']} not found in vocabulary, resetting user data")
            reset_user_data(user_id)
            bot.reply_to(
                message,
                "📚 Словарь был обновлен. Начинаем обучение с новыми словами!",
                reply_markup=get_main_keyboard()
            )
            return

        example = state.get("current_example")
        if not example:
            logger.error(f"No current example found for user {user_id}")
            bot.reply_to(message, "❌ Произошла ошибка. Начните упражнение заново")
            return

        # Проверяем ответ
        is_correct = check_answer(message.text, example, state["translation_direction"])
        logger.debug(f"Answer from user {user_id} was {'correct' if is_correct else 'incorrect'}")

        # Обновляем прогресс
        if is_correct:
            current_word["correct_answers"] = current_word.get("correct_answers", 0) + 1
            current_word["status"] = update_word_status(current_word)
            
            # Обновляем интервал повторения
            new_interval = calculate_next_interval(current_word["correct_answers"])
            current_word["next_review"] = (
                datetime.datetime.now() + datetime.timedelta(hours=new_interval)
            ).isoformat()
            
            # Если слово изучено, перемещаем его и добавляем новое
            if current_word["correct_answers"] >= 3:
                logger.info(f"Word '{current_word['word']}' learned by user {user_id}")
                
                # Добавляем слово в изученные
                user_data["learned_words"].append(current_word)
                user_data["active_words"].remove(current_word)
                
                # Добавляем новое слово, если есть доступные
                if user_data.get("remaining_words"):
                    # Проверяем каждое слово на наличие в словаре
                    valid_remaining_words = [
                        word for word in user_data["remaining_words"]
                        if word in VOCABULARY["Буду изучать"]
                    ]
                    
                    if valid_remaining_words:
                        new_word = random.choice(valid_remaining_words)
                        user_data["remaining_words"].remove(new_word)
                        
                        # Добавляем новое слово в активные
                        user_data["active_words"].append({
                            "word": new_word,
                            "translation": VOCABULARY["Буду изучать"][new_word]["перевод"],
                            "status": WordStatus.NEW,
                            "correct_answers": 0,
                            "next_review": datetime.datetime.now().isoformat(),
                            "interval": 4
                        })
                        logger.info(f"Added new word '{new_word}' for user {user_id}")
                    else:
                        logger.warning("No valid words remaining in vocabulary")

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
            if state["translation_direction"] == "ru_to_it":
                correct_answer = example["итальянский"]
            else:
                correct_answer = example["русский"]
                
            response = (
                "❌ *Ошибка!*\n\n"
                f"Ваш ответ: _{message.text}_\n"
                f"Правильный ответ: *{correct_answer}*\n"
                f"Прогресс: {progress_bar}"
            )
            markup = get_retry_keyboard()

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
            "❌ Произошла ошибка. Попробуйте начать заново.",
            reply_markup=get_main_keyboard()
        )
def check_and_send_notifications():
    """Проверка и отправка уведомлений"""
    logger.info("Starting notifications checker")
    scheduled_notifications = {}
    
    while True:
        try:
            current_time = datetime.datetime.now()
            
            if os.path.exists('user_data'):
                for filename in os.listdir('user_data'):
                    if not filename.startswith('user_') or not filename.endswith('.json'):
                        continue
                        
                    try:
                        user_id = int(filename.split('_')[1].split('.')[0])
                        
                        # Проверяем, не в активной ли сессии пользователь
                        state = user_states.get(user_id, {})
                        if state.get("awaiting_answer"):
                            logger.debug(f"User {user_id} is in active session, skipping notification")
                            continue
                        
                        # Проверяем запланированное время
                        if user_id in scheduled_notifications:
                            scheduled_time = scheduled_notifications[user_id]
                            if current_time < scheduled_time:
                                continue
                            del scheduled_notifications[user_id]
                        
                        user_data = load_user_data(user_id)
                        if not user_data or not user_data.get("active_words"):
                            continue
                            
                        # Проверяем только если нет активной сессии
                        if not user_data.get("current_session"):
                            words_to_review = get_words_for_review(user_data)
                            if words_to_review:
                                next_review = None
                                for word in user_data["active_words"]:
                                    try:
                                        review_time = datetime.datetime.fromisoformat(word["next_review"])
                                        if next_review is None or review_time < next_review:
                                            next_review = review_time
                                    except:
                                        continue
                                
                                if next_review and next_review <= current_time:
                                    notification_text = [
                                        "🔔 *Пора повторить слова!*\n",
                                        f"У вас {len(words_to_review)} слов готово к повторению:"
                                    ]
                                    
                                    for word in words_to_review[:3]:
                                        notification_text.append(f"• {word['word']} - {word['translation']}")
                                    
                                    if len(words_to_review) > 3:
                                        notification_text.append(f"\n... и ещё {len(words_to_review) - 3} слов")
                                    
                                    try:
                                        bot.send_message(
                                            user_id,
                                            "\n".join(notification_text),
                                            parse_mode='Markdown',
                                            reply_markup=get_main_keyboard()
                                        )
                                        logger.info(f"Sent notification to user {user_id}")
                                    except telebot.apihelper.ApiTelegramException as e:
                                        if e.error_code == 403:
                                            logger.warning(f"User {user_id} has blocked the bot")
                                        else:
                                            logger.error(f"Error sending notification: {e}")
                                else:
                                    scheduled_notifications[user_id] = next_review
                                
                    except Exception as e:
                        logger.error(f"Error processing notifications for user {filename}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error in notification check: {e}")
            
        time.sleep(60)

def run_bot():
    """Запуск бота"""
    logger.info("=== Starting Bot ===")
    logger.info(f"Vocabulary size: {len(VOCABULARY['Буду изучать'])} words")
    
    # Конфигурация настроек подключения
    telebot.apihelper.CONNECT_TIMEOUT = 15
    telebot.apihelper.READ_TIMEOUT = 10
    
    try:
        # Проверяем токен
        bot_info = bot.get_me()
        logger.info(f"Bot authorized successfully. Bot username: {bot_info.username}")
        
        # Сбрасываем webhook и очищаем обновления
        bot.delete_webhook()
        logger.info("Webhook deleted")
        bot.get_updates(offset=-1, timeout=1)
        logger.info("Updates cleared")
        
        # Запуск проверки уведомлений в отдельном потоке
        import threading
        notification_thread = threading.Thread(target=check_and_send_notifications, daemon=True)
        notification_thread.start()
        logger.info("Notification thread started")
        
        # Основной цикл бота
        while True:
            try:
                logger.info("Starting bot polling...")
                bot.infinity_polling(
                    timeout=15,
                    long_polling_timeout=30,
                    logger_level=logging.ERROR,
                    restart_on_change=False,
                    skip_pending=True
                )
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)
                
    except Exception as e:
        logger.error(f"Critical error: {e}")

if __name__ == "__main__":
    try:
        # Добавляем обработчик для остановки бота по Ctrl+C
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