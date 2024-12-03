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

# Настраиваем вывод в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Настраиваем вывод в файл
file_handler = logging.FileHandler('bot_log.txt', encoding='utf-8')
file_handler.setFormatter(formatter)

# Настраиваем корневой логгер
logger = logging.getLogger('ItalianBot')
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Отключаем стандартные логи telebot
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
    
    # Получаем все доступные слова
    all_words = list(VOCABULARY["Буду изучать"].keys())
    # Перемешиваем случайным образом
    random.shuffle(all_words)
    # Берем первые 20 слов
    initial_words = all_words[:20]
    remaining_words = all_words[20:]
    
    current_time = datetime.datetime.now().isoformat()
    
    # Создаем данные для каждого слова
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
	# Продолжение предыдущего кода...

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

def start_new_session(user_data: dict):
    """Начало новой сессии обучения"""
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

def calculate_next_interval(correct_answers: int) -> int:
    """Расчет следующего интервала повторения"""
    if correct_answers >= 3:
        return 24  # Переводим на длинный интервал
    elif correct_answers == 2:
        return 8   # Средний интервал
    else:
        return 4   # Короткий интервал

def show_current_exercise(chat_id: int, user_id: int):
    """Показ текущего упражнения"""
    logger.debug(f"Showing exercise for user {user_id}")
    
    user_data = load_user_data(user_id)
    state = user_states.get(user_id, {})
    
    # Проверяем, нужно ли начать новую сессию
    if not user_data["current_session"] or user_data["current_word_index"] >= len(user_data["current_session"]):
        words_to_review = get_words_for_review(user_data)
        if not words_to_review:
            logger.debug(f"No words to review for user {user_id}")
            bot.send_message(
                chat_id,
                "🕒 Сейчас нет слов для повторения!\nВы можете отдохнуть или начать новую сессию позже.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Начинаем новую сессию
        random.shuffle(words_to_review)
        user_data["current_session"] = words_to_review
        user_data["current_word_index"] = 0
        save_user_data(user_id, user_data)
        logger.debug(f"Started new session for user {user_id} with {len(words_to_review)} words")
    
    # Получаем текущее слово
    current_word = user_data["current_session"][user_data["current_word_index"]]
    word_data = VOCABULARY["Буду изучать"][current_word["word"]]
    example = random.choice(word_data["примеры"])
    
    # Определяем направление перевода
    translation_direction = state.get("translation_direction", "ru_to_it")
    if translation_direction == "ru_to_it":
        question = example["русский"]
        direction_text = "итальянский"
    else:
        question = example["итальянский"]
        direction_text = "русский"
    
    # Создаем сообщение
    progress_bar = "🟢" * current_word["correct_answers"] + "⚪️" * (3 - current_word["correct_answers"])
    message_text = (
        f"*{current_word['word']} - {current_word['translation']}*\n\n"
        f"Переведите на {direction_text}:\n"
        f"*{question}*\n\n"
        f"Прогресс изучения: {progress_bar}\n"
        f"_Слово {user_data['current_word_index'] + 1} из {len(user_data['current_session'])}_"
    )
    
    bot.send_message(
        chat_id,
        message_text,
        parse_mode='Markdown',
        reply_markup=get_exercise_keyboard()
    )
    
    # Обновляем состояние
    user_states[user_id] = {
        "translation_direction": translation_direction,
        "awaiting_answer": True,
        "current_example": example
    }
    logger.debug(f"Exercise shown for user {user_id}, word: {current_word['word']}")

# def check_answer(answer: str, example: dict, translation_direction: str) -> bool:
    # """Проверка правильности ответа"""
    # user_answer = normalize_text(answer.strip())
    
    # if translation_direction == "ru_to_it":
        # correct_answer = normalize_text(example["итальянский"])
        # alternatives = [normalize_text(alt) for alt in example.get("альтернативы_ит", [])]
    # else:
        # correct_answer = normalize_text(example["русский"])
        # alternatives = [normalize_text(alt) for alt in example.get("альтернативы_рус", [])]
    
    # return user_answer == correct_answer or user_answer in alternatives
def check_answer(answer: str, example: dict, translation_direction: str) -> bool:
    """Проверка правильности ответа с учетом знаков препинания и регистра"""
    user_answer = normalize_text(answer)
    
    if translation_direction == "ru_to_it":
        correct_answer = normalize_text(example["итальянский"])
        alternatives = [normalize_text(alt) for alt in example.get("альтернативы_ит", [])]
    else:
        correct_answer = normalize_text(example["русский"])
        alternatives = [normalize_text(alt) for alt in example.get("альтернативы_рус", [])]
    
    return user_answer == correct_answer or user_answer in alternatives

@bot.message_handler(func=lambda message: message.text == "🔄 Повторить")
def retry_answer(message):
    """Повторная попытка ответа"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} retrying exercise")
    
    # Просто показываем текущее упражнение заново
    show_current_exercise(message.chat.id, user_id)
    
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
    
    # Проверяем ответ с помощью новой функции
    is_correct = check_answer(message.text, state["current_example"], state["translation_direction"])
    
    
    
def normalize_text(text: str) -> str:
    """Нормализация текста для сравнения при проверке ответов"""
    # Только замена итальянских букв, без изменения регистра и пунктуации
    replacements = {
        'à': 'a', 'è': 'e', 'é': 'e',
        'ì': 'i', 'í': 'i', 'ò': 'o',
        'ó': 'o', 'ù': 'u', 'ú': 'u',
        'À': 'A', 'È': 'E', 'É': 'E',
        'Ì': 'I', 'Í': 'I', 'Ò': 'O',
        'Ó': 'O', 'Ù': 'U', 'Ú': 'U'
    }
    
    result = text.strip()  # Убираем пробелы в начале и конце
    for old, new in replacements.items():
        result = result.replace(old, new)
        
    # Убираем двойные пробелы внутри текста
    return ' '.join(part for part in result.split(' ') if part)
    
    
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot")
    
    # Загружаем или создаем данные пользователя
    user_data = load_user_data(user_id)
    
    # Инициализация состояния
    user_states[user_id] = {
        "translation_direction": "ru_to_it",
        "awaiting_answer": False
    }
    
    # Подсчет статистики
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
    start_new_session(user_data)  # Сбрасываем статусы предыдущей сессии
    save_user_data(user_id, user_data)
    
    words_to_review = get_words_for_review(user_data)
    
    if not words_to_review:
        next_review = None
        for word in user_data["active_words"]:
            review_time = datetime.datetime.fromisoformat(word["next_review"])
            if next_review is None or review_time < next_review:
                next_review = review_time
        
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

@bot.message_handler(func=lambda message: message.text == "➡️ Далее")
def next_exercise(message):
    """Переход к следующему упражнению"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} pressed Next button")
    
    user_data = load_user_data(user_id)
    
    # Увеличиваем индекс текущего слова
    user_data["current_word_index"] += 1
    save_user_data(user_id, user_data)
    
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "🏁 Завершить занятие")
def end_session(message):
    """Завершение текущей сессии"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} ending session")
    
    user_data = load_user_data(user_id)
    
    # Подсчитываем статистику сессии
    answered_words = sum(1 for word in user_data["active_words"] 
                        if word.get("status") == WordStatus.ANSWERED_IN_SESSION)
    
    # Находим ближайшее время следующего повторения
    next_review = None
    for word in user_data["active_words"]:
        review_time = datetime.datetime.fromisoformat(word["next_review"])
        if next_review is None or review_time < next_review:
            next_review = review_time

    # Сбрасываем текущую сессию
    start_new_session(user_data)
    save_user_data(user_id, user_data)
    
    # Формируем сообщение с результатами и временем следующего повторения
    summary_text = [
        "🏁 *Занятие завершено!*\n",
        f"В этой сессии вы проработали {answered_words} слов."
    ]
    
    if next_review:
        time_diff = next_review - datetime.datetime.now()
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        
        if hours > 0:
            time_str = f"{hours}ч {minutes}мин"
        else:
            time_str = f"{minutes}мин"
            
        summary_text.append(f"\n⏰ Следующее повторение через: *{time_str}*")
        
        # Устанавливаем напоминание
        user_states[user_id]["next_notification"] = next_review
        
    bot.reply_to(
        message,
        "\n".join(summary_text),
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )
    
    # Сбрасываем состояние пользователя
    user_states[user_id].update({
        "translation_direction": user_states[user_id].get("translation_direction", "ru_to_it"),
        "awaiting_answer": False
    })

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
		# Продолжение предыдущего кода...

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_statistics(message):
    """Показ статистики обучения"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested statistics")
    
    user_data = load_user_data(user_id)
    
    # Подсчет слов по статусам
    new_words = sum(1 for w in user_data["active_words"] if w.get("correct_answers", 0) == 0)
    learning_words = sum(1 for w in user_data["active_words"] if 0 < w.get("correct_answers", 0) < 3)
    learned_words = len(user_data["learned_words"])
    
    # Подсчет слов для повторения
    words_to_review = get_words_for_review(user_data)
    words_available = len(words_to_review)
    
    stats_message = (
        "📊 *Статистика обучения:*\n\n"
        f"📚 Всего слов в работе: {len(user_data['active_words'])}\n"
        f"🆕 Не начатые слова: {new_words}\n"
        f"📝 В процессе изучения: {learning_words}\n"
        f"✅ Изучено слов: {learned_words}\n"
        f"⏰ Готово к повторению: {words_available}\n\n"
        "Слово считается изученным после 3 правильных ответов\n"
        f"Всего слов в словаре: {len(VOCABULARY['Буду изучать'])}"
    )
    
    bot.reply_to(
        message,
        stats_message,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )
    logger.debug(f"Statistics shown for user {user_id}")

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
    if state["translation_direction"] == "ru_to_it":
        correct_answer = example["итальянский"]
        alternatives = example.get("альтернативы_ит", [])
    else:
        correct_answer = example["русский"]
        alternatives = example.get("альтернативы_рус", [])

    user_answer = normalize_text(message.text.strip())
    correct_answer_norm = normalize_text(correct_answer)
    
    is_correct = user_answer == correct_answer_norm
    if not is_correct:
        for alt in alternatives:
            if user_answer == normalize_text(alt):
                is_correct = True
                break
    
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
        if current_word["correct_answers"] >= 3 and user_data["remaining_words"]:
            user_data["learned_words"].append(current_word)
            user_data["active_words"].remove(current_word)
            
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
    
    while True:
        try:
            current_time = datetime.datetime.now()
            
            # Проверяем запланированные уведомления
            for user_id, state in user_states.items():
                next_notification = state.get("next_notification")
                if next_notification and current_time >= next_notification:
                    try:
                        user_data = load_user_data(user_id)
                        words_to_review = get_words_for_review(user_data)
                        
                        if words_to_review:
                            notification_text = (
                                f"🔔 *Пора вернуться к изучению!*\n\n"
                                f"У вас {len(words_to_review)} слов для повторения.\n"
                                f"📚 Всего активных слов: {len(user_data['active_words'])}\n"
                                f"✅ Изучено слов: {len(user_data['learned_words'])}\n\n"
                                "Используйте команду /review для начала повторения."
                            )
                            
                            bot.send_message(
                                user_id,
                                notification_text,
                                parse_mode='Markdown',
                                reply_markup=get_main_keyboard()
                            )
                            logger.info(f"Sent scheduled notification to user {user_id}")
                            
                            # Очищаем запланированное уведомление
                            state["next_notification"] = None
                            
                    except Exception as e:
                        logger.error(f"Error sending notification to user {user_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in notification check: {e}")
            
        time.sleep(60)  # Проверка каждую минуту
        

def run_bot():
    """Запуск бота"""
    logger.info("=== Starting Bot ===")
    logger.info(f"Vocabulary size: {len(VOCABULARY['Буду изучать'])} words")
    
    try:
        # Проверяем токен
        bot_info = bot.get_me()
        logger.info(f"Bot authorized successfully. Bot username: {bot_info.username}")
    except Exception as e:
        logger.error(f"Failed to authorize bot with token: {e}")
        return

    # Сбрасываем webhook и очищаем обновления
    try:
        bot.delete_webhook()
        logger.info("Webhook deleted")
        updates = bot.get_updates(offset=-1, timeout=1)
        logger.info(f"Got {len(updates)} pending updates")
    except Exception as e:
        logger.error(f"Error clearing updates: {e}")
    
    # Запуск проверки уведомлений в отдельном потоке
    import threading
    notification_thread = threading.Thread(target=check_and_send_notifications, daemon=True)
    notification_thread.start()
    logger.info("Notification thread started")
    
    # Запуск основного цикла бота
    while True:
        try:
            logger.info("Starting bot polling...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Bot polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        # Добавляем обработчик для остановки бота по Ctrl+C
        import signal
        def signal_handler(sig, frame):
            logger.info("Received stop signal, shutting down...")
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Запускаем бота
        logger.info("=== Bot process starting ===")
        run_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        raise
		




