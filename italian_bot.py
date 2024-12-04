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

port = os.environ.get('PORT', 5000)
TOKEN = "7312843542:AAHVDxaHYSveOpitmkWagTFoMVNzYF4_tMU"
bot = telebot.TeleBot(TOKEN, parse_mode=None)

       
# Настройки для повторных попыток и таймаутов
telebot.apihelper.RETRY_ON_ERROR = True
telebot.apihelper.CONNECT_TIMEOUT = 30


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
# TOKEN = "7312843542:AAHVDxaHYSveOpitmkWagTFoMVNzYF4_tMU"
# bot = telebot.TeleBot(TOKEN, parse_mode=None)

# Глобальное хранилище состояний пользователей
user_states = {}

# Константы для статусов слов
WORD_STATUS = {
    "NEW": "new",           # 0 правильных ответов
    "LEARNING": "learning", # 1-2 правильных ответа
    "LEARNED": "learned"    # 3+ правильных ответа
}

# Регистрируем временные команды для отладки
@bot.message_handler(commands=['status'])
def check_status(message):
    """Временная команда для проверки статуса слов и уведомлений"""
    user_id = message.from_user.id
    try:
        user_data = load_user_data(user_id)
        state = user_states.get(user_id, {})
        current_time = datetime.datetime.now()
        
        status_text = ["📊 *Текущий статус обучения:*\n"]
        
        # Проверяем и обновляем время следующего уведомления
        next_review_time = None
        words_to_review = []
        
        for word in user_data["active_words"]:
            try:
                review_time = datetime.datetime.fromisoformat(word["next_review"])
                if review_time <= current_time:  # Слово просрочено
                    words_to_review.append(word)
                elif next_review_time is None or review_time < next_review_time:
                    next_review_time = review_time
            except Exception as e:
                logger.error(f"Error processing word {word.get('word')}: {e}")
                continue
        
        # Если есть просроченные слова, устанавливаем уведомление на сейчас
        if words_to_review:
            state["next_notification"] = current_time.isoformat()
            user_states[user_id] = state
            status_text.append("🔔 *Есть слова для повторения прямо сейчас!*")
        elif next_review_time:
            state["next_notification"] = next_review_time.isoformat()
            user_states[user_id] = state
            time_diff = next_review_time - current_time
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            time_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
            status_text.append(f"🔔 Следующее уведомление через: *{time_str}*")
        else:
            status_text.append("🔕 Нет запланированных уведомлений")
        
        # Проверяем слова для повторения
        words_info = []
        for word in user_data["active_words"]:
            try:
                review_time = datetime.datetime.fromisoformat(word["next_review"])
                time_diff = review_time - current_time
                hours = abs(int(time_diff.total_seconds() // 3600))
                if time_diff.total_seconds() <= 0:
                    words_info.append(f"• {word['word']} - {word['translation']} - *ПОВТОРИТЬ СЕЙЧАС!* (просрочено на {hours}ч)")
                else:
                    words_info.append(f"• {word['word']} - {word['translation']} - через {hours}ч")
            except Exception as e:
                continue
        
        if words_info:
            status_text.append("\n📝 *Статус слов:*")
            status_text.extend(words_info)
        else:
            status_text.append("\nНет активных слов для повторения")
        
        bot.reply_to(
            message,
            "\n".join(status_text),
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        bot.reply_to(
            message,
            "❌ Ошибка при проверке статуса",
            reply_markup=get_main_keyboard()
        )

@bot.message_handler(commands=['test_notify'])
def test_notification(message):
    """Временная команда для тестирования уведомлений"""
    user_id = message.from_user.id
    try:
        # Устанавливаем тестовое уведомление через 1 минуту
        next_notification = datetime.datetime.now() + datetime.timedelta(minutes=1)
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False,
            "last_activity": datetime.datetime.now().isoformat()
        }
        
        bot.reply_to(
            message,
            "🔔 Тестовое уведомление будет отправлено через 1 минуту",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Set test notification for user {user_id} at {next_notification}")
        
    except Exception as e:
        logger.error(f"Error setting test notification: {e}")
        bot.reply_to(
            message,
            "❌ Ошибка при установке тестового уведомления",
            reply_markup=get_main_keyboard()
        )

def calculate_next_interval(correct_answers: int) -> int:
    """Расчет следующего интервала повторения в часах"""
    intervals = {
        0: 1,    # 1 час
        1: 4,    # 4 часа
        2: 8,    # 8 часов
        3: 24,   # 1 день
        4: 72,   # 3 дня
        5: 168,  # 7 дней
        6: 336,  # 14 дней
        7: 720   # 30 дней
    }
    return intervals.get(correct_answers, 720)  # если больше 7, то 30 дней

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
    for word in all_words[:5]:
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
                # Удаляем дубликаты из active_words
                seen_words = set()
                unique_words = []
                for word in data["active_words"]:
                    if word["word"] not in seen_words:
                        seen_words.add(word["word"])
                        unique_words.append(word)
                data["active_words"] = unique_words
            
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
        logger.debug(f"Data saved successfully: {file_path}")
        # Показать содержимое директории
        files = os.listdir('user_data')
        logger.info(f"Current user data files: {files}")
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def get_words_for_review(user_data: dict) -> List[dict]:
    """Получение списка слов для повторения"""
    current_time = datetime.datetime.now()
    words_to_review = []
    future_words = []
    
    # Разделяем слова на просроченные и будущие
    for word in user_data["active_words"]:
        try:
            next_review = datetime.datetime.fromisoformat(word["next_review"])
            if next_review <= current_time:
                words_to_review.append(word)
            else:
                future_words.append(word)
        except Exception as e:
            logger.error(f"Error processing review time for word {word.get('word')}: {e}")
            continue
    
    # Сортируем просроченные слова по времени (самые давние первые)
    words_to_review.sort(
        key=lambda x: datetime.datetime.fromisoformat(x["next_review"])
    )
    
    # Сортируем будущие слова по времени (ближайшие первые)
    future_words.sort(
        key=lambda x: datetime.datetime.fromisoformat(x["next_review"])
    )
    
    # Если все слова новые (correct_answers == 0), возвращаем их все
    if all(word["correct_answers"] == 0 for word in user_data["active_words"]):
        all_words = user_data["active_words"].copy()
        random.shuffle(all_words)
        return all_words
    
    # Возвращаем сначала просроченные, потом будущие слова
    return words_to_review + future_words
    

def update_word_progress(word: dict, is_correct: bool) -> dict:
    """Обновление прогресса слова"""
    # Увеличиваем счетчик попыток
    word["total_attempts"] = word.get("total_attempts", 0) + 1
    
    if is_correct:
        # Увеличиваем счетчик правильных ответов
        word["correct_answers"] = word.get("correct_answers", 0) + 1
        
        # Обновляем статус
        if word["correct_answers"] >= 8:
            word["status"] = WORD_STATUS["LEARNED"]
        elif word["correct_answers"] > 0:
            word["status"] = WORD_STATUS["LEARNING"]
            
        # Обновляем время следующего повторения с учетом таймзоны Астаны
        next_interval = calculate_next_interval(word["correct_answers"])
        next_review_time = (
            datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=6))) + 
            datetime.timedelta(hours=next_interval)
        )
        word["next_review"] = next_review_time.isoformat()
        
        logger.debug(
            f"Word {word['word']} updated: "
            f"correct_answers={word['correct_answers']}, "
            f"next_review={word['next_review']}"
        )
    
    return word


def get_main_keyboard() -> types.ReplyKeyboardMarkup:
    """Создание основной клавиатуры"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🎯 Начать повторение"))
    markup.row(
        types.KeyboardButton("🔄 Сменить направление перевода"),
        types.KeyboardButton("📊 Статистика")
    )
    markup.row(
        types.KeyboardButton("/start"),
        types.KeyboardButton("ℹ️ Помощь")
    )
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
    
    # Заменяем обратный апостроф на правильный
    user_answer = user_answer.strip().replace('`', "'")
    
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
    """Показ текущего упражнения"""
    logger.debug(f"Showing exercise for user {user_id}")
    
    try:
        user_data = load_user_data(user_id)
        if not user_data["current_session"]:
            logger.error("No current session found")
            bot.send_message(
                chat_id,
                "❌ Нет активной сессии. Начните новое повторение.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Получаем текущее слово из current_session
        current_word = user_data["current_session"][user_data["current_word_index"]]
        word_data = VOCABULARY["Буду изучать"].get(current_word["word"])
        
        if not word_data:
            logger.error(f"Word {current_word['word']} not found in vocabulary")
            bot.send_message(
                chat_id,
                "❌ Ошибка в данных. Начните заново.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Выбираем случайный пример
        example = random.choice(word_data["примеры"])
        
        # Определяем направление перевода
        state = user_states.get(user_id, {})
        translation_direction = state.get("translation_direction", "ru_to_it")
        
        question = example["русский"] if translation_direction == "ru_to_it" else example["итальянский"]
        direction_text = "итальянский" if translation_direction == "ru_to_it" else "русский"
        
        # Сохраняем состояние
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False,
            "last_activity": datetime.datetime.now().isoformat()
        }
        
        # Добавляем логирование прямо здесь, перед отправкой сообщения
        logger.debug(f"Showing word from current_session: {current_word['word']}")
        logger.debug(f"Current session words: {[w['word'] for w in user_data['current_session']]}")
        
        # Формируем сообщение
        progress_bar = "🟢" * current_word["correct_answers"] + "⚪️" * (8 - current_word["correct_answers"])
        message_text = (
            f"*{current_word['word']} - {current_word['translation']}*\n\n"
            f"Переведите на {direction_text}:\n"
            f"*{question}*\n\n"
            f"Прогресс изучения: {progress_bar}\n"
            f"_Слово {user_data['current_word_index'] + 1} из {len(user_data['active_words'])}_"
        )
        
        bot.send_message(
            chat_id,
            message_text,
            parse_mode='Markdown',
            reply_markup=get_exercise_keyboard()
        )
        
        logger.debug(f"Exercise shown for user {user_id}, word: {current_word['word']}")
        
    except Exception as e:
        logger.error(f"Error showing exercise: {e}", exc_info=True)
        bot.send_message(
            chat_id,
            "❌ Произошла ошибка. Начните упражнение заново.",
            reply_markup=get_main_keyboard()
        )
        
        
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
            "last_activity": datetime.datetime.now().isoformat()
        }
       
       welcome_text = (
           "*Привет, Сашуля-красотуля! *\n\n"
           "Я бот для изучения итальянского языка.\n\n"
           f"📚 Активных слов: {len(user_data['active_words'])}\n"
           f"✅ Изучено слов: {len(user_data['learned_words'])}\n\n"
           "🔹 *'Начать повторение'* - для изучения слов\n"
           "🔹 *'Сменить направление'* - выбор направления перевода\n"
           "🔹 *'Статистика'* - для просмотра прогресса\n"
           "🔹 *'Помощь'* - справка по командам\n\n"
           
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

@bot.message_handler(func=lambda message: message.text in ["🎯 Начать повторение", "/review"])
def start_review(message):
    """Начало сессии повторения"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} started review session")
    
    try:
        user_data = load_user_data(user_id)
        words_to_review = get_words_for_review(user_data)
        logger.debug(f"Found {len(words_to_review)} words for review")
        
        if not words_to_review:
            # ... (оставляем как есть) ...
            return
        
        # Подсчитываем просроченные слова
        current_time = datetime.datetime.now()
        overdue_words = [
            word for word in words_to_review 
            if datetime.datetime.fromisoformat(word["next_review"]) <= current_time
        ]
         # Добавляем здесь логирование - исправленная версия
        logger.debug(f"Found overdue words: {[w['word'] for w in overdue_words]}")  # добавлена закрывающая скобка
        
        if overdue_words:
            # Просроченные слова оставляем в отсортированном порядке
            # Перемешиваем только оставшиеся слова
            current_words = overdue_words  # используем именно overdue_words
            future_words = [w for w in words_to_review if w not in overdue_words]
            random.shuffle(future_words)                          # перемешиваем только будущие
            words_to_review = current_words + future_words        # объединяем списки
            
            # И здесь добавляем логирование
            logger.debug(f"First word to review after sorting: {words_to_review[0]['word']}")
            
            bot.reply_to(
                message,
                f"📚 Начинаем повторение!\n\n"
                f"❗️ Есть {len(overdue_words)} просроченных слов, начнем с них.",
                reply_markup=get_exercise_keyboard()
            )
        
        # Начинаем новую сессию
        user_data["current_session"] = words_to_review
        user_data["current_word_index"] = 0
        
        save_user_data(user_id, user_data)
        
        # Обновляем состояние
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False,
            "last_activity": datetime.datetime.now().isoformat()
        }
        
        # Показываем первое упражнение
        show_current_exercise(message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Error in start_review: {e}", exc_info=True)
        bot.reply_to(
            message,
            "❌ Произошла ошибка. Попробуйте начать заново.",
            reply_markup=get_main_keyboard()
        )
        

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
        learning_words = sum(1 for w in active_words if 0 < w["correct_answers"] < 8)  # было 3, стало 8
        learned_words = len(user_data["learned_words"])
        
        # Подсчет слов для повторения
        words_to_review = get_words_for_review(user_data)
        
        stats_message = [
            "📊 *Статистика обучения:*\n",
            f"📚 Активные слова: {len(active_words)}",
            f"🆕 Новые слова (0 ответов): {new_words}",
            f"📝 В процессе (1-7 ответов): {learning_words}",
            f"✅ Изучено (8+ ответов): {learned_words}",
            f"⏰ Готово к повторению: {len(words_to_review)}\n",
            "Слово считается изученным после 8 правильных ответов",
            f"Всего слов в словаре: {len(VOCABULARY['Буду изучать'])}"
        ]
        
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
       
       # Сохраняем состояние
       awaiting_answer = state.get("awaiting_answer", False)
       current_example = state.get("current_example")
       
       user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False,
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
        if not user_data.get("current_session"):
            logger.debug("No current session")
            bot.reply_to(
                message,
                "❌ Нет активной сессии. Начните новое занятие.",
                reply_markup=get_main_keyboard()
            )
            return
            
        current_index = user_data.get("current_word_index", 0)
        logger.debug(f"Current index: {current_index}, Session length: {len(user_data['current_session'])}")
        
        if current_index >= len(user_data["current_session"]) - 1:
            # Завершаем сессию
            user_data["current_session"] = []
            user_data["current_word_index"] = 0
            save_user_data(user_id, user_data)
            
            bot.reply_to(
                message,
                "✅ Все задания на текущий момент выполнены!\n\n"
                "Вернитесь в главное меню и начните новое занятие, когда будете готовы.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Переходим к следующему слову
        user_data["current_word_index"] += 1
        save_user_data(user_id, user_data)
        
        # Обновляем состояние
        state = user_states.get(user_id, {})
        state["awaiting_answer"] = True
        user_states[user_id] = state
        
        # Показываем следующее упражнение
        show_current_exercise(message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Error in next_exercise: {e}", exc_info=True)
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
        current_time = datetime.datetime.now()
        
        # Очищаем текущую сессию
        user_data["current_session"] = []
        user_data["current_word_index"] = 0
        
        # Формируем сообщение
        summary_text = ["🏁 *Занятие завершено!*\n"]
        
        # Подсчитываем слова для повторения и ищем ближайшее время
        next_review = None
        words_status = []
        
        for word in user_data["active_words"]:
            try:
                review_time = datetime.datetime.fromisoformat(word["next_review"])
                time_diff = review_time - current_time
                hours = int(time_diff.total_seconds() // 3600)
                
                words_status.append({
                    "word": word["word"],
                    "translation": word["translation"],
                    "hours": hours,
                    "review_time": review_time
                })
                
                if next_review is None or review_time < next_review:
                    next_review = review_time
            except:
                continue
        
        # Сортируем слова по времени повторения
        words_status.sort(key=lambda x: x["review_time"])
        
        if words_status:
            # Находим следующее время повторения
            if next_review and next_review > current_time:
                time_diff = next_review - current_time
                hours = int(time_diff.total_seconds() // 3600)
                minutes = int((time_diff.total_seconds() % 3600) // 60)
                time_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
                
                # Устанавливаем напоминание через час если занятие прервано
                # reminder_time = min(
                    # current_time + datetime.timedelta(hours=1),
                    # next_review
                # )
                
                # Сохраняем время следующего уведомления
                # user_states[user_id] = {
                    # "translation_direction": "ru_to_it",
                    # "awaiting_answer": False,
                    # "next_notification": reminder_time.isoformat(),
                    # "last_activity": current_time.isoformat()
                # }
                
                # Добавляем информацию о следующих повторениях
                summary_text.extend([
                    f"📚 Всего слов на изучении: {len(words_status)}",
                    f"⏰ Следующее повторение через: *{time_str}*\n",
                    "📝 Ближайшие слова для повторения:"
                ])
                
                # Показываем до 3 ближайших слов
                for word_info in words_status[:3]:
                    time_str = f"{word_info['hours']}ч" if word_info['hours'] > 0 else "сейчас"
                    summary_text.append(f"• {word_info['word']} - {word_info['translation']} (через {time_str})")
                
                summary_text.append("\n🔔 Я пришлю уведомление, когда придет время повторить слова!")
            else:
                summary_text.append("✅ Все слова повторены! Новые слова станут доступны позже.")
        else:
            summary_text.append("📝 Нет активных слов для изучения")
        
        # Сохраняем обновленные данные
        save_user_data(user_id, user_data)
        
        # Отправляем сообщение
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
@bot.message_handler(commands=['update_vocabulary'])
def update_vocabulary(message):
    """Обновление словаря без сброса прогресса"""
    user_id = message.from_user.id
    try:
        user_data = load_user_data(user_id)
        
        # Сохраняем текущие изученные слова
        learned_words = user_data["learned_words"]
        active_words = user_data["active_words"]
        
        # Получаем все доступные слова из обновленного словаря
        all_words = list(VOCABULARY["Буду изучать"].keys())
        
        # Убираем уже изученные и активные слова из списка новых слов
        learned_word_keys = {word["word"] for word in learned_words}
        active_word_keys = {word["word"] for word in active_words}
        new_words = [word for word in all_words if word not in learned_word_keys and word not in active_word_keys]
        
        # Если в активных словах меньше 20 слов, добавляем новые
        while len(active_words) < 20 and new_words:
            new_word = random.choice(new_words)
            new_words.remove(new_word)
            word_data = VOCABULARY["Буду изучать"][new_word]
            active_words.append({
                "word": new_word,
                "translation": word_data["перевод"],
                "correct_answers": 0,
                "next_review": datetime.datetime.now().isoformat(),
                "total_attempts": 0
            })
        
        # Обновляем данные пользователя
        user_data["active_words"] = active_words
        user_data["remaining_words"] = new_words
        
        # Сохраняем обновленные данные
        save_user_data(user_id, user_data)
        
        bot.reply_to(
            message,
            f"✅ Словарь обновлен!\n"
            f"📚 Активных слов: {len(active_words)}\n"
            f"🆕 Осталось слов для изучения: {len(new_words)}",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error updating vocabulary: {e}")
        bot.reply_to(
            message,
            "❌ Произошла ошибка при обновлении словаря",
            reply_markup=get_main_keyboard()
        ) 
        
@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def show_help(message):
    """Показ справки по командам"""
    help_text = [
        "*📋 Доступные команды:*",
        "",
        "🎯 Начать повторение - начать изучение слов",
        "🔄 Сменить направление - изменить направление перевода",
        "📊 Статистика - посмотреть прогресс обучения",
        "",
        "*Дополнительные команды:*",
        "`/start` - перезапустить бота",
        "`/status` - проверить статус слов и уведомлений",
        "`/test_notify` - проверить работу уведомлений",
        "`/reset` - сбросить весь прогресс",
        "`/update_vocabulary` - добавить новые слова (без сброса прогресса)",
        "",
        "*Команды во время занятия:*",
        "💡 Подсказка - показать первые буквы слов",
        "⏩ Пропустить - пропустить текущее слово",
        "🏁 Завершить занятие - закончить текущую сессию"
    ]
    
    try:
        bot.reply_to(
            message,
            "\n".join(help_text),
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Error sending help message: {e}")
        # Пробуем отправить без форматирования если возникла ошибка
        help_text_plain = [line.replace('*', '').replace('`', '') for line in help_text]
        bot.reply_to(
            message,
            "\n".join(help_text_plain),
            reply_markup=get_main_keyboard()
        )

def highlight_differences(user_answer: str, correct_answer: str) -> str:
    """Подсветка различий между ответами"""
    user_words = user_answer.lower().split()
    correct_words = correct_answer.lower().split()
    
    result = []
    for i in range(max(len(user_words), len(correct_words))):
        # Если слово есть в обоих ответах
        if i < len(user_words) and i < len(correct_words):
            if user_words[i] != correct_words[i]:
                result.append(f"*{user_words[i]}* → _{correct_words[i]}_")
            else:
                result.append(user_words[i])
        # Если в пользовательском ответе больше слов
        elif i < len(user_words):
            result.append(f"*{user_words[i]}* → _[лишнее]_")
        # Если в правильном ответе больше слов
        else:
            result.append(f"*[пропущено]* → _{correct_words[i]}_")
    
    return ' '.join(result)


        
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

        # Находим текущее слово по индексу в current_session
        current_session_word = user_data["current_session"][user_data["current_word_index"]]
        
        # Находим это же слово в active_words
        current_word_index = None
        for i, word in enumerate(user_data["active_words"]):
            if word["word"] == current_session_word["word"]:
                current_word_index = i
                break
                
        if current_word_index is None:
            logger.error(f"Word {current_session_word['word']} not found in active_words")
            bot.reply_to(message, "❌ Произошла ошибка. Начните упражнение заново")
            return
            
        current_word = user_data["active_words"][current_word_index]
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
        updated_word = update_word_progress(current_word, is_correct)
        user_data["active_words"][current_word_index] = updated_word

        # Если слово изучено (3+ правильных ответа)
        if updated_word["correct_answers"] >= 8:
            logger.debug(f"Word {updated_word['word']} learned")
            user_data["learned_words"].append(updated_word)
            user_data["active_words"].pop(current_word_index)
            
            # Обновляем current_session, удаляя изученное слово
            user_data["current_session"] = [w for w in user_data["current_session"] if w["word"] != updated_word["word"]]
            
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
        progress_bar = "🟢" * updated_word["correct_answers"] + "⚪️" * (8 - updated_word["correct_answers"])

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
                f"Ваш ответ с исправлениями:\n"
                f"{highlight_differences(message.text, correct_answer)}\n\n"
                f"Правильный ответ:\n*{correct_answer}*\n\n"
                f"Прогресс: {progress_bar}"
            )
            markup = get_retry_keyboard()

        # Обновляем состояние
        state["awaiting_answer"] = False
        state["last_activity"] = datetime.datetime.now().isoformat()
        user_states[user_id] = state

        # ... предыдущий код функции ...

        bot.reply_to(
            message,
            response,
            parse_mode='Markdown',
            reply_markup=markup
        )

        # Добавляем здесь проверку содержимого файла
        if is_correct:
            try:
                with open(f'user_data/user_{user_id}.json', 'r', encoding='utf-8') as f:
                    logger.info(f"File contents after save: {f.read()}")
            except Exception as e:
                logger.error(f"Error reading file: {e}")

    except Exception as e:
        logger.error(f"Error handling answer: {e}", exc_info=True)
        bot.reply_to(
            message,
            "❌ Произошла ошибка. Попробуйте начать заново.",
            reply_markup=get_main_keyboard()
        )
       
# Добавьте временную команду для отладки
@bot.message_handler(commands=['status'])
def check_status(message):
    """Временная команда для проверки статуса слов и уведомлений"""
    user_id = message.from_user.id
    try:
        user_data = load_user_data(user_id)
        state = user_states.get(user_id, {})
        current_time = datetime.datetime.now()
        
        status_text = ["📊 *Текущий статус обучения:*\n"]
        
        # Проверяем следующее уведомление
        # next_notification = state.get("next_notification")
        # if next_notification:
            # notification_time = datetime.datetime.fromisoformat(next_notification)
            # time_diff = notification_time - current_time
            # if time_diff.total_seconds() > 0:
                # hours = int(time_diff.total_seconds() // 3600)
                # minutes = int((time_diff.total_seconds() % 3600) // 60)
                # time_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
                # status_text.append(f"🔔 Следующее уведомление через: *{time_str}*")
        # else:
            # status_text.append("🔕 Нет запланированных уведомлений")
        
        # Проверяем слова для повторения
        # В функции check_status добавьте группировку по интервалам:
        words_info = []
        processed_words = set()

        for word in user_data["active_words"]:
            try:
                if word["word"] in processed_words:
                    continue
                    
                processed_words.add(word["word"])
                
                review_time = datetime.datetime.fromisoformat(word["next_review"])
                time_diff = review_time - current_time
                hours = abs(int(time_diff.total_seconds() // 3600))
                days = hours // 24
                
                if time_diff.total_seconds() <= 0:
                    words_info.append(f"• {word['word']} - {word['translation']} - *ПОВТОРИТЬ СЕЙЧАС!* (просрочено на {hours}ч)")
                else:
                    if days > 0:
                        words_info.append(f"• {word['word']} - {word['translation']} - через {days}д {hours%24}ч")
                    else:
                        words_info.append(f"• {word['word']} - {word['translation']} - через {hours}ч")
                    
            except Exception as e:
                continue
        
        if words_info:
            status_text.append("\n📝 *Статус слов:*")
            status_text.extend(sorted(words_info))  # Сортируем слова для лучшей читаемости
        else:
            status_text.append("\nНет активных слов для повторения")
        
        bot.reply_to(
            message,
            "\n".join(status_text),
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        bot.reply_to(
            message,
            "❌ Ошибка при проверке статуса",
            reply_markup=get_main_keyboard()
        )

# @bot.message_handler(commands=['test_notify'])
# def test_notification(message):
    # """Временная команда для тестирования уведомлений"""
    # user_id = message.from_user.id
    # try:
        # # Устанавливаем тестовое уведомление через 1 минуту
        # next_notification = datetime.datetime.now() + datetime.timedelta(minutes=1)
        # user_states[user_id] = {
            # "translation_direction": "ru_to_it",
            # "awaiting_answer": False,
            # "next_notification": next_notification.isoformat(),
            # "last_activity": datetime.datetime.now().isoformat()
        # }
        
        # bot.reply_to(
            # message,
            # "🔔 Тестовое уведомление будет отправлено через 1 минуту",
            # reply_markup=get_main_keyboard()
        # )
        
    # except Exception as e:
        # logger.error(f"Error setting test notification: {e}")
        # bot.reply_to(
            # message,
            # "❌ Ошибка при установке тестового уведомления",
            # reply_markup=get_main_keyboard()
        # )

        
# def check_and_send_notifications():
   # while True:
       # try:
           # current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=6)))
           
           # if not os.path.exists('user_data'):
               # continue

           # for filename in os.listdir('user_data'):
               # try:
                   # user_id = int(filename.split('_')[1].split('.')[0])
                   # user_data = load_user_data(user_id)
                   # words_to_review = []
                   
                   # for word in user_data["active_words"]:
                       # try:
                           # review_time = datetime.datetime.fromisoformat(word["next_review"])
                           # review_time = review_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=6)))
                           
                           # if review_time <= current_time:
                               # words_to_review.append(word)
                       # except Exception as e:
                           # logger.error(f"Error processing word: {e}")
                           # continue

                   # if words_to_review:
                       # notification_text = "🔔 Пора повторить слова!\n\n"
                       # notification_text += f"У вас {len(words_to_review)} слов готово к повторению:\n\n"
                       
                       # for word in words_to_review[:3]:
                           # notification_text += f"• {word['word']} - {word['translation']}\n"
                       
                       # try:
                           # bot.send_message(
                               # user_id, 
                               # notification_text, 
                               # reply_markup=get_main_keyboard()
                           # )
                           # logger.info(f"Sent notification to user {user_id}")
                       # except Exception as e:
                           # logger.error(f"Failed to send notification: {e}")
                           
               # except Exception as e:
                   # logger.error(f"Error processing user file: {e}")
                   # continue
                   
       # except Exception as e:
           # logger.error(f"Error in notification check: {e}")
           
       # time.sleep(600)



        
def ensure_single_instance():
    import socket
    global _lock_socket  # Добавляем глобальную переменную
    _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock_socket.bind(('localhost', 12345))
        return True
    except socket.error:
        return False

def run_bot():
    logger.info("=== Starting Bot ===")
    logger.info(f"Vocabulary size: {len(VOCABULARY['Буду изучать'])} words")
    
    bot.remove_webhook()
    time.sleep(2)
    bot.polling()

def cleanup():
   global _lock_socket
   if '_lock_socket' in globals():
       _lock_socket.close()

if __name__ == "__main__":
    run_bot()