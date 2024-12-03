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
    NEW = "new"
    LEARNING = "learning"
    LEARNED = "learned"
    ANSWERED_IN_SESSION = "answered"

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
    """Нормализация текста только для сравнения, не для замены"""
    input_text = text.strip()
    
    # Сначала проверяем точное совпадение
    replacements_preserve = {
        'È': 'E',  # Сохраняем заглавные
        'É': 'E',
        'À': 'A',
        'Ì': 'I',
        'Ò': 'O',
        'Ù': 'U'
    }
    
    replacements_lower = {
        'è': 'e',  # Для строчных букв
        'é': 'e',
        'à': 'a',
        'ì': 'i',
        'ò': 'o',
        'ù': 'u'
    }
    
    result = input_text
    # Сначала заменяем заглавные буквы
    for old, new in replacements_preserve.items():
        if old in result:
            result = result.replace(old, new)
    
    # Потом строчные
    for old, new in replacements_lower.items():
        if old in result:
            result = result.replace(old, new)
            
    return result
    
    message_text = (
        f"*{current_word['word']} - {current_word['translation']}*\n\n"
        f"Переведите на {direction_text}:\n"
        f"*{question}*\n\n"
        "❗️ Учитывайте заглавные буквы и знаки препинания\n\n"  # Добавить эту строку
        f"Прогресс изучения: {progress_bar}\n"
        f"_Слово {user_data['current_word_index'] + 1} из {len(user_data['current_session'])}_"
    )

def calculate_next_interval(correct_answers: int) -> int:
    """Расчет следующего интервала повторения"""
    if correct_answers >= 3:
        return 24  # Переводим на длинный интервал
    elif correct_answers == 2:
        return 8   # Средний интервал
    else:
        return 4   # Короткий интервал

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
            
    logger.debug(f"Creating initial data for user {user_id}")
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
        logger.debug(f"Successfully saved data for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

def create_initial_user_data(user_id: int) -> dict:
    """Создание начальных данных для нового пользователя"""
    logger.info(f"Creating initial data for user {user_id}")
    
    all_words = list(VOCABULARY["Буду изучать"].keys())
    random.shuffle(all_words)
    initial_words = all_words[:20]
    remaining_words = all_words[20:]
    
    current_time = datetime.datetime.now().isoformat()
    active_words = []
    
    for word in initial_words:
        active_words.append({
            "word": word,
            "translation": VOCABULARY["Буду изучать"][word]["перевод"],
            "status": WordStatus.NEW,
            "correct_answers": 0,
            "next_review": current_time,
            "interval": 4
        })
    
    data = {
        "user_id": user_id,
        "active_words": active_words,
        "learned_words": [],
        "remaining_words": remaining_words,
        "current_session": [],
        "current_word_index": 0,
        "last_update": current_time
    }
    
    save_user_data(user_id, data)
    logger.info(f"Initial data created for user {user_id} with {len(initial_words)} words")
    return data
def get_words_for_review(user_data: dict) -> List[dict]:
    """Получение слов для повторения"""
    current_time = datetime.datetime.now()
    words_to_review = []
    
    for word in user_data["active_words"]:
        next_review = datetime.datetime.fromisoformat(word["next_review"])
        # Добавляем только слова, которые не были отвечены в текущей сессии
        if next_review <= current_time and word.get("status") != WordStatus.ANSWERED_IN_SESSION:
            words_to_review.append(word)
            
    logger.debug(f"Found {len(words_to_review)} words for review")
    return words_to_review

def check_answer(user_answer: str, example: dict, translation_direction: str) -> bool:
    """Проверка правильности ответа"""
    # Убираем пробелы в начале и конце, но сохраняем регистр
    user_answer = user_answer.strip()
    
    if translation_direction == "ru_to_it":
        correct_answer = example["итальянский"]
        alternatives = example.get("альтернативы_ит", [])
    else:
        correct_answer = example["русский"]
        alternatives = example.get("альтернативы_рус", [])
    
    # Добавляем варианты с нормализованными буквами
    all_answers = [correct_answer] + alternatives
    normalized_answers = []
    for answer in all_answers:
        # Добавляем оригинальный ответ
        normalized_answers.append(answer)
        # Добавляем версию с базовыми буквами
        normalized_answers.append(normalize_text(answer))
        # Добавляем версию с заглавной первой буквой
        if len(answer) > 0:
            normalized_answers.append(answer[0].upper() + answer[1:])
            normalized_answers.append(normalize_text(answer[0].upper() + answer[1:]))
    
    # Убираем дубликаты
    normalized_answers = list(set(normalized_answers))
    
    return user_answer in normalized_answers or normalize_text(user_answer) in normalized_answers

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
        f"Прогресс изучения: {progress_bar}\n"
        f"_Слово {user_data['current_word_index'] + 1} из {len(user_data['current_session'])}_"
    )
    
    # Обновляем состояние и отправляем сообщение
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

def start_new_session(user_data: dict):
    """Начало новой сессии обучения"""
    logger.debug("Starting new session")
    # Сбрасываем статус ANSWERED_IN_SESSION у всех слов
    for word in user_data["active_words"]:
        if word.get("status") == WordStatus.ANSWERED_IN_SESSION:
            if word.get("correct_answers", 0) >= 3:
                word["status"] = WordStatus.LEARNED
            elif word.get("correct_answers", 0) > 0:
                word["status"] = WordStatus.LEARNING
            else:
                word["status"] = WordStatus.NEW
    
    user_data["current_session"] = []
    user_data["current_word_index"] = 0
	# Обработчики команд и сообщений

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot")
    
    user_data = load_user_data(user_id)
    
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
        "🔹 *'Подсказка'* - если нужна помощь\n"
        "🔹 *'Статистика'* - для просмотра прогресса\n"
        "🔹 *'Завершить занятие'* - для выхода из сессии\n\n"
        "Начнём? 😊"
    )
    
    bot.reply_to(
        message,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text in ["🎯 Начать повторение", "/review"])
def start_review(message):
    """Начало сессии повторения"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} started review session")
    
    user_data = load_user_data(user_id)
    words_to_review = get_words_for_review(user_data)
    
    if not words_to_review:
        bot.reply_to(
            message,
            "🕒 Сейчас нет слов для повторения!",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Начинаем новую сессию
    user_data["current_session"] = words_to_review
    user_data["current_word_index"] = 0
    save_user_data(user_id, user_data)
    
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "➡️ Далее")
def next_exercise(message):
    """Переход к следующему упражнению"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} pressed Next button")
    
    user_data = load_user_data(user_id)
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
    
    # Устанавливаем время следующего повторения
    current_time = datetime.datetime.now()
    for word in user_data["active_words"]:
        if word.get("status") == WordStatus.ANSWERED_IN_SESSION:
            next_interval = calculate_next_interval(word.get("correct_answers", 0))
            next_review = current_time + datetime.timedelta(hours=next_interval)
            word["next_review"] = next_review.isoformat()
            word["status"] = WordStatus.LEARNING if word.get("correct_answers", 0) > 0 else WordStatus.NEW
    
    save_user_data(user_id, user_data)
    
    # Находим ближайшее время повторения
    next_review = None
    for word in user_data["active_words"]:
        review_time = datetime.datetime.fromisoformat(word["next_review"])
        if next_review is None or review_time < next_review:
            next_review = review_time
    
    # Формируем сообщение
    summary_text = [
        "🏁 *Занятие завершено!*\n"
    ]
    
    if next_review:
        time_diff = next_review - current_time
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

@bot.message_handler(func=lambda message: message.text in ["🔄 Сменить направление", "/switch"])
def switch_translation_direction(message):
    """Смена направления перевода"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} switching translation direction")
    
    state = user_states.get(user_id, {"translation_direction": "ru_to_it"})
    current_direction = state["translation_direction"]
    new_direction = "it_to_ru" if current_direction == "ru_to_it" else "ru_to_it"
    
    user_states[user_id] = {
        **state,
        "translation_direction": new_direction
    }
    
    direction_text = "итальянский → русский" if new_direction == "it_to_ru" else "русский → итальянский"
    bot.reply_to(
        message,
        f"🔄 Направление перевода изменено на:\n*{direction_text}*",
        parse_mode='Markdown'
    )
    
    if state.get("awaiting_answer"):
        show_current_exercise(message.chat.id, user_id)
@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_statistics(message):
    """Показ статистики обучения"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested statistics")
    
    user_data = load_user_data(user_id)
    
    # Правильный подсчет:
    active_words = len(user_data["active_words"])
    new_words = sum(1 for w in user_data["active_words"] if w.get("correct_answers", 0) == 0)
    learning_words = sum(1 for w in user_data["active_words"] if w.get("status") == WordStatus.LEARNING)
    learned_words = len(user_data["learned_words"])
    words_to_review = get_words_for_review(user_data)

    stats_message = (
        "📊 *Статистика обучения:*\n\n"
        f"📚 Активные слова: {active_words}\n"
        f"🆕 Новые слова (0 ответов): {new_words}\n"
        f"📝 В процессе (1-2 ответа): {learning_words}\n"
        f"✅ Изучено (3+ ответа): {learned_words}\n"
        f"⏰ Готово к повторению: {len(words_to_review)}\n\n"
        "Слово считается изученным после 3 правильных ответов\n"
        f"Всего слов в словаре: {len(VOCABULARY['Буду изучать'])}"
    )
    
        
    bot.reply_to(
        message,
        stats_message,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )
@bot.message_handler(func=lambda message: message.text in ["ℹ️ Помощь", "/help"])
def send_help(message):
    """Обработка команды /help и кнопки Помощь"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested help")
    
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
        "• Поддерживается около 20 активных слов\n"
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

@bot.message_handler(func=lambda message: True)
def handle_answer(message):
    """Обработка ответов пользователя"""
    user_id = message.from_user.id
    logger.debug(f"Received message from user {user_id}: {message.text}")
    
    state = user_states.get(user_id, {})
    if not state.get("awaiting_answer"):
        return

    user_data = load_user_data(user_id)
    if not user_data["current_session"] or user_data["current_word_index"] >= len(user_data["current_session"]):
        return

    current_word = user_data["current_session"][user_data["current_word_index"]]
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
        current_word["status"] = WordStatus.ANSWERED_IN_SESSION
        
        # Обновляем интервал повторения
        new_interval = calculate_next_interval(current_word["correct_answers"])
        current_word["next_review"] = (datetime.datetime.now() + 
                                     datetime.timedelta(hours=new_interval)).isoformat()
        
        # Если слово изучено, перемещаем его и добавляем новое
        if current_word["correct_answers"] >= 3 and user_data.get("remaining_words"):
            logger.info(f"Word '{current_word['word']}' learned by user {user_id}")
            user_data["learned_words"].append(current_word)
            user_data["active_words"].remove(current_word)
            
            # Добавляем новое слово
            new_word = random.choice(user_data["remaining_words"])
            user_data["remaining_words"].remove(new_word)
            
            user_data["active_words"].append({
                "word": new_word,
                "translation": VOCABULARY["Буду изучать"][new_word]["перевод"],
                "status": WordStatus.NEW,
                "correct_answers": 0,
                "next_review": datetime.datetime.now().isoformat(),
                "interval": 4
            })
            logger.info(f"Added new word '{new_word}' for user {user_id}")
    
    save_user_data(user_id, user_data)
    
    # Получаем правильный ответ для отображения
    if state["translation_direction"] == "ru_to_it":
        correct_answer = example["итальянский"]
    else:
        correct_answer = example["русский"]
    
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
    
    bot.reply_to(
        message,
        response,
        parse_mode='Markdown',
        reply_markup=markup
    )

def check_and_send_notifications():
    """Проверка и отправка уведомлений"""
    logger.info("Starting notifications checker")
    last_notifications = {}  # Словарь для хранения времени последнего уведомления
    
    while True:
        try:
            current_time = datetime.datetime.now()
            if os.path.exists('user_data'):
                for filename in os.listdir('user_data'):
                    if not filename.startswith('user_') or not filename.endswith('.json'):
                        continue
                        
                    try:
                        user_id = int(filename.split('_')[1].split('.')[0])
                        
                        # Проверяем, не слишком ли часто отправляем уведомления
                        if user_id in last_notifications:
                            time_since_last = current_time - last_notifications[user_id]
                            if time_since_last.total_seconds() < 3600:  # Минимум час между уведомлениями
                                continue
                        
                        # Загружаем данные пользователя
                        user_data = load_user_data(user_id)
                        if not user_data:
                            continue
                            
                        words_to_review = []
                        for word in user_data["active_words"]:
                            try:
                                next_review = datetime.datetime.fromisoformat(word["next_review"])
                                if next_review <= current_time:
                                    words_to_review.append(word)
                            except (ValueError, KeyError) as e:
                                logger.error(f"Error processing word review time: {e}")
                                continue
                        
                        if words_to_review:
                            # Формируем текст уведомления с примерами слов
                            words_preview = [f"• {w['word']} - {w['translation']}" for w in words_to_review[:3]]
                            words_count = len(words_to_review)
                            
                            notification_text = [
                                "🔔 *Пора повторить слова!*\n",
                                f"У вас {words_count} слов готово к повторению:\n",
                                *words_preview
                            ]
                            
                            if words_count > 3:
                                notification_text.append(f"\n... и ещё {words_count - 3} слов")
                            
                            notification_text.extend([
                                f"\n📚 Всего активных слов: {len(user_data['active_words'])}",
                                f"✅ Изучено слов: {len(user_data.get('learned_words', []))}"
                                # "\nИспользуйте команду /review для начала повторения."
                            ])
                            
                            try:
                                bot.send_message(
                                    user_id,
                                    "\n".join(notification_text),
                                    parse_mode='Markdown',
                                    reply_markup=get_main_keyboard()
                                )
                                last_notifications[user_id] = current_time
                                logger.info(f"Sent notification to user {user_id} about {words_count} words")
                                
                            except telebot.apihelper.ApiTelegramException as e:
                                if e.error_code == 403:  # Пользователь заблокировал бота
                                    logger.warning(f"User {user_id} has blocked the bot")
                                else:
                                    logger.error(f"Error sending notification to user {user_id}: {e}")
                        
                    except Exception as e:
                        logger.error(f"Error processing user {filename}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error in notification check: {e}")
        
        # Спим 5 минут между проверками
        time.sleep(300)

# Также нужно обновить функцию calculate_next_interval
def calculate_next_interval(correct_answers: int) -> int:
    """Расчет следующего интервала повторения"""
    if correct_answers >= 3:
        return 24  # 24 часа
    elif correct_answers == 2:
        return 8   # 8 часов
    elif correct_answers == 1:
        return 4   # 4 часа
    else:
        return 1   # 1 час для новых слов

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

# if __name__ == "__main__":
    # try:
        # # Добавляем обработчик для остановки бота по Ctrl+C
        # import signal
        # def signal_handler(sig, frame):
            # logger.info("Received stop signal, shutting down...")
            # sys.exit(0)
        # signal.signal(signal.SIGINT, signal_handler)
        
        # # Запускаем бота
        # logger.info("=== Bot process starting ===")
        # run_bot()
    # except KeyboardInterrupt:
        # logger.info("Bot stopped by user")
    # except Exception as e:
        # logger.error(f"Critical error: {e}")
        # raise