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
    NEW = "new"           # Новое слово (0 правильных ответов)
    LEARNING = "learning" # В процессе изучения (1-2 правильных ответа)
    LEARNED = "learned"   # Изучено (3+ правильных ответа)

class WordProgress:
    def __init__(self, word: str, translation: str):
        self.word = word
        self.translation = translation
        self.correct_answers = 0
        self.next_review = datetime.datetime.now().isoformat()
        self.status = WordStatus.NEW
        self.total_attempts = 0
        self.current_interval = 1  # часы

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "translation": self.translation,
            "correct_answers": self.correct_answers,
            "next_review": self.next_review,
            "status": self.status,
            "total_attempts": self.total_attempts,
            "current_interval": self.current_interval
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WordProgress':
        progress = cls(data["word"], data["translation"])
        progress.correct_answers = data.get("correct_answers", 0)
        progress.next_review = data.get("next_review", datetime.datetime.now().isoformat())
        progress.status = data.get("status", WordStatus.NEW)
        progress.total_attempts = data.get("total_attempts", 0)
        progress.current_interval = data.get("current_interval", 1)
        return progress

    def update_progress(self, is_correct: bool):
        """Обновление прогресса слова"""
        self.total_attempts += 1
        
        if is_correct:
            self.correct_answers += 1
            # Обновляем статус
            if self.correct_answers >= 3:
                self.status = WordStatus.LEARNED
            elif self.correct_answers > 0:
                self.status = WordStatus.LEARNING
            
            # Увеличиваем интервал
            if self.correct_answers >= 3:
                self.current_interval = 24  # 24 часа
            elif self.correct_answers == 2:
                self.current_interval = 8   # 8 часов
            elif self.correct_answers == 1:
                self.current_interval = 4   # 4 часа
        else:
            # При ошибке сокращаем интервал
            self.current_interval = 1
        
        # Устанавливаем время следующего повторения
        self.next_review = (
            datetime.datetime.now() + 
            datetime.timedelta(hours=self.current_interval)
        ).isoformat()

class UserProgress:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.active_words: List[WordProgress] = []
        self.learned_words: List[WordProgress] = []
        self.remaining_words: List[str] = []
        self.current_session: List[WordProgress] = []
        self.current_word_index: int = 0
        self.last_update = datetime.datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "active_words": [w.to_dict() for w in self.active_words],
            "learned_words": [w.to_dict() for w in self.learned_words],
            "remaining_words": self.remaining_words,
            "current_session": [w.to_dict() for w in self.current_session],
            "current_word_index": self.current_word_index,
            "last_update": self.last_update
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'UserProgress':
        progress = cls(data["user_id"])
        progress.active_words = [WordProgress.from_dict(w) for w in data.get("active_words", [])]
        progress.learned_words = [WordProgress.from_dict(w) for w in data.get("learned_words", [])]
        progress.remaining_words = data.get("remaining_words", [])
        progress.current_session = [WordProgress.from_dict(w) for w in data.get("current_session", [])]
        progress.current_word_index = data.get("current_word_index", 0)
        progress.last_update = data.get("last_update", datetime.datetime.now().isoformat())
        return progress

    def get_words_for_review(self) -> List[WordProgress]:
        """Получение слов для повторения"""
        current_time = datetime.datetime.now()
        words_to_review = []
        
        # Если все слова новые, возвращаем их все
        if all(w.status == WordStatus.NEW for w in self.active_words):
            return self.active_words.copy()
        
        # Иначе проверяем время следующего повторения
        for word in self.active_words:
            next_review = datetime.datetime.fromisoformat(word.next_review)
            if next_review <= current_time:
                words_to_review.append(word)
        
        return words_to_review

    def update_word_progress(user_id: int, word: str, is_correct: bool):
        """Обновление прогресса слова"""
        file_path = f'user_data/user_{user_id}.json'
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
                
            # Находим слово в активных словах
            for word_data in user_data["active_words"]:
                if word_data["word"] == word:
                    # Увеличиваем счетчик правильных ответов
                    if is_correct:
                        word_data["correct_answers"] = word_data.get("correct_answers", 0) + 1
                    # Обновляем время следующего повторения
                    next_interval = calculate_next_interval(word_data.get("correct_answers", 0))
                    word_data["next_review"] = (
                        datetime.datetime.now() + 
                        datetime.timedelta(hours=next_interval)
                    ).isoformat()
                    break
                    
            # Сохраняем обновленные данные
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"Updated progress for word {word}: correct_answers = {word_data.get('correct_answers', 0)}")
            
        except Exception as e:
            logger.error(f"Error updating word progress: {e}")
        
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
               
           # Проверяем наличие всех необходимых полей
           if not all(key in data for key in ["active_words", "learned_words", "remaining_words"]):
               logger.warning(f"Missing required fields in user data for {user_id}")
               return create_initial_user_data(user_id)
               
           # Проверяем актуальность слов
           has_old_words = False
           for word in data["active_words"]:
               if word["word"] not in VOCABULARY["Буду изучать"]:
                   has_old_words = True
                   break
                   
           if has_old_words:
               logger.info(f"Found old vocabulary for user {user_id}, creating new data")
               return create_initial_user_data(user_id)
               
           logger.debug(f"Successfully loaded data for user {user_id}")
           return data
           
       except Exception as e:
           logger.error(f"Error loading user data: {e}")
           return create_initial_user_data(user_id)
   
   return create_initial_user_data(user_id)

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
       initial_words.append({
           "word": word,
           "translation": word_data["перевод"],
           "correct_answers": 0,
           "next_review": datetime.datetime.now().isoformat(),
           "total_attempts": 0
       })
   
   # Создаем структуру данных
   data = {
       "user_id": user_id,
       "active_words": initial_words,
       "learned_words": [],
       "remaining_words": all_words[20:],
       "current_word_index": 0,
       "last_update": datetime.datetime.now().isoformat()
   }
   
   # Сохраняем данные
   file_path = f'user_data/user_{user_id}.json'
   with open(file_path, 'w', encoding='utf-8') as f:
       json.dump(data, f, ensure_ascii=False, indent=2)
       
   logger.info(f"Created initial data for user {user_id} with {len(initial_words)} words")
   return data

# def save_user_data(user_id: int, data: dict):
   # """Сохранение данных пользователя"""
   # logger.debug(f"Saving data for user {user_id}")
   # if not os.path.exists('user_data'):
       # os.makedirs('user_data')
       
   # file_path = f'user_data/user_{user_id}.json'
   # try:
       # with open(file_path, 'w', encoding='utf-8') as f:
           # json.dump(data, f, ensure_ascii=False, indent=2)
       # logger.debug(f"Successfully saved data for user {user_id}")
   # except Exception as e:
       # logger.error(f"Error saving user data: {e}")
       
def save_user_data(user_id: int, progress: UserProgress):
    """Сохранение данных пользователя"""
    logger.debug(f"Saving data for user {user_id}")
    if not os.path.exists('user_data'):
        os.makedirs('user_data')
        
    file_path = f'user_data/user_{user_id}.json'
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(progress.to_dict(), f, ensure_ascii=False, indent=2)
        logger.debug(f"Successfully saved data for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

def create_initial_user_data(user_id: int) -> UserProgress:
    """Создание начальных данных для нового пользователя"""
    logger.info(f"Creating initial data for user {user_id}")
    
    # Получаем все доступные слова
    all_words = list(VOCABULARY["Буду изучать"].keys())
    random.shuffle(all_words)
    
    # Создаем прогресс пользователя
    progress = UserProgress(user_id)
    
    # Добавляем первые 20 слов в активные
    for word in all_words[:20]:
        word_data = VOCABULARY["Буду изучать"][word]
        progress.active_words.append(
            WordProgress(word, word_data["перевод"])
        )
    
    # Остальные слова в очередь
    progress.remaining_words = all_words[20:]
    
    save_user_data(user_id, progress)
    logger.info(f"Created initial data for user {user_id} with {len(progress.active_words)} words")
    return progress

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

# Клавиатуры
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
	# Основные обработчики команд
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot")
    
    try:
        # Загружаем или создаем новые данные пользователя
        progress = load_user_data(user_id)
        progress = UserProgress.from_dict(progress)  # Преобразуем dict в объект UserProgress
        
        # Инициализируем состояние
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False,
            "current_example": None,
            "last_activity": datetime.datetime.now().isoformat()
        }
        
        welcome_text = (
            "*Привет! Я бот для изучения итальянского языка.*\n\n"
            f"📚 Активных слов: {len(progress.active_words)}\n"
            f"✅ Изучено слов: {len(progress.learned_words)}\n\n"
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

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_statistics(message):
    """Показ статистики обучения"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested statistics")
    
    try:
        # Загружаем данные пользователя
        file_path = f'user_data/user_{user_id}.json'
        
        with open(file_path, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
            logger.debug(f"Raw user data: {user_data}")

        # Подсчёт по активным словам
        active_words = user_data.get("active_words", [])
        
        # Подробный подсчёт статистики
        new_words = 0
        in_progress = 0
        learned = 0
        
        for word in active_words:
            correct_answers = word.get("correct_answers", 0)
            logger.debug(f"Word {word['word']}: {correct_answers} correct answers")
            
            if correct_answers == 0:
                new_words += 1
            elif correct_answers < 3:
                in_progress += 1
            else:
                learned += 1
        
        logger.debug(f"""
            Statistics breakdown:
            New words: {new_words}
            In progress: {in_progress}
            Learned: {learned}
        """)

        # Формируем сообщение
        stats_message = [
            "📊 *Статистика обучения:*\n",
            f"📚 Активные слова: {len(active_words)}",
            f"🆕 Новые слова (0 ответов): {new_words}",
            f"📝 В процессе (1-2 ответа): {in_progress}",
            f"✅ Изучено (3+ ответа): {learned}",
            f"⏰ Готово к повторению: {len(active_words)}"
        ]
        
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
        logger.error(f"Error in show_statistics: {e}", exc_info=True)
        bot.reply_to(
            message,
            "❌ Произошла ошибка при отображении статистики",
            reply_markup=get_main_keyboard()
        )
        

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
        logger.error(f"Error showing help: {e}")
        bot.reply_to(
            message,
            "❌ Произошла ошибка при отображении справки",
            reply_markup=get_main_keyboard()
        )
@bot.message_handler(func=lambda message: message.text in ["🎯 Начать повторение", "/review"])
def start_review(message):
   """Начало сессии повторения"""
   user_id = message.from_user.id
   logger.info(f"User {user_id} started review session")
   
   try:
       # Загружаем текущий прогресс
       file_path = f'user_data/user_{user_id}.json'
       with open(file_path, 'r', encoding='utf-8') as f:
           progress_data = json.load(f)
           logger.debug(f"Loaded progress data for review: {progress_data}")
       
       # Проверяем есть ли слова для повторения
       current_time = datetime.datetime.now()
       words_to_review = []
       
       # Если все слова новые - берем все
       if all(word.get("correct_answers", 0) == 0 for word in progress_data["active_words"]):
           words_to_review = progress_data["active_words"]
           logger.debug("All words are new, using all active words")
       else:
           # Иначе проверяем время следующего повторения
           for word in progress_data["active_words"]:
               try:
                   next_review = datetime.datetime.fromisoformat(word["next_review"])
                   if next_review <= current_time:
                       words_to_review.append(word)
               except:
                   words_to_review.append(word)
                   
           logger.debug(f"Found {len(words_to_review)} words ready for review")
       
       if not words_to_review:
           # Находим время следующего повторения
           next_review = None
           for word in progress_data["active_words"]:
               try:
                   review_time = datetime.datetime.fromisoformat(word["next_review"])
                   if next_review is None or review_time < next_review:
                       next_review = review_time
               except:
                   continue
           
           if next_review:
               time_diff = next_review - current_time
               if time_diff.total_seconds() > 0:
                   hours = int(time_diff.total_seconds() // 3600)
                   minutes = int((time_diff.total_seconds() % 3600) // 60)
                   time_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
                   
                   bot.reply_to(
                       message,
                       f"🕒 Сейчас нет слов для повторения!\n\nСледующее повторение через: *{time_str}*",
                       parse_mode='Markdown',
                       reply_markup=get_main_keyboard()
                   )
                   
                   # Сохраняем время следующего уведомления
                   state = user_states.get(user_id, {})
                   state["next_notification"] = next_review.isoformat()
                   user_states[user_id] = state
                   logger.debug(f"Set next notification time to {next_review}")
                   
                   return
           else:
               bot.reply_to(
                   message,
                   "🕒 Сейчас нет слов для повторения!",
                   reply_markup=get_main_keyboard()
               )
               return
       
       # Начинаем новую сессию
       random.shuffle(words_to_review)
       
       # Обновляем прогресс
       progress_data["current_word_index"] = 0
       progress_data["current_session"] = [word["word"] for word in words_to_review]
       
       # Сохраняем обновленный прогресс
       with open(file_path, 'w', encoding='utf-8') as f:
           json.dump(progress_data, f, ensure_ascii=False, indent=2)
           logger.debug("Saved updated progress with new session")
       
       # Обновляем состояние пользователя
       user_states[user_id] = {
           "translation_direction": "ru_to_it",
           "awaiting_answer": True,
           "current_example": None,
           "last_activity": current_time.isoformat()
       }
       
       # Показываем первое упражнение
       show_current_exercise(message.chat.id, user_id)
       
   except Exception as e:
       logger.error(f"Error starting review: {e}", exc_info=True)
       bot.reply_to(
           message,
           "❌ Произошла ошибка. Попробуйте начать заново.",
           reply_markup=get_main_keyboard()
       )
       

def show_current_exercise(chat_id: int, user_id: int):
   """Показ текущего упражнения"""
   logger.debug(f"Showing exercise for user {user_id}")
   
   try:
       # Загружаем прогресс из JSON
       file_path = f'user_data/user_{user_id}.json'
       with open(file_path, 'r', encoding='utf-8') as f:
           progress_data = json.load(f)
           logger.debug(f"Loaded progress data for exercise: {progress_data}")
       
       if not progress_data.get("active_words"):
           logger.error("No active words found")
           bot.send_message(
               chat_id,
               "❌ Ошибка: нет активных слов. Начните заново.",
               reply_markup=get_main_keyboard()
           )
           return
       
       # Получаем текущее слово
       current_word = progress_data["active_words"][progress_data.get("current_word_index", 0)]
       logger.debug(f"Current word from progress: {current_word}")
       
       # Получаем данные слова из словаря
       word_data = VOCABULARY["Буду изучать"].get(current_word["word"])
       if not word_data:
           logger.error(f"Word {current_word['word']} not found in vocabulary")
           bot.send_message(
               chat_id,
               "❌ Ошибка: слово не найдено в словаре. Начните заново.",
               reply_markup=get_main_keyboard()
           )
           return
           
       # Выбираем случайный пример
       example = random.choice(word_data["примеры"])
       logger.debug(f"Selected example: {example}")
       
       # Определяем направление перевода
       state = user_states.get(user_id, {})
       translation_direction = state.get("translation_direction", "ru_to_it")
       
       if translation_direction == "ru_to_it":
           question = example["русский"]
           direction_text = "итальянский"
       else:
           question = example["итальянский"]
           direction_text = "русский"
       
       # Сохраняем текущий пример и состояние
       user_states[user_id] = {
           "translation_direction": translation_direction,
           "awaiting_answer": True,
           "current_example": example,
           "last_activity": datetime.datetime.now().isoformat()
       }
       
       # Создаем сообщение
       progress_bar = "🟢" * current_word.get("correct_answers", 0) + "⚪️" * (3 - current_word.get("correct_answers", 0))
       message_text = (
           f"*{current_word['word']} - {current_word['translation']}*\n\n"
           f"Переведите на {direction_text}:\n"
           f"*{question}*\n\n"
           f"Прогресс изучения: {progress_bar}\n"
           f"_Слово {progress_data.get('current_word_index', 0) + 1} из {len(progress_data['active_words'])}_"
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
    
    try:
        progress = load_user_data(user_id)
        if not progress.current_session:
            return
        
        # Переходим к следующему слову без изменения статистики
        progress.current_word_index += 1
        save_user_data(user_id, progress)
        
        bot.reply_to(message, "⏩ Слово пропущено")
        show_current_exercise(message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Error skipping word: {e}")
        bot.reply_to(
            message,
            "❌ Произошла ошибка. Попробуйте начать заново.",
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
        state["translation_direction"] = new_direction
        state["last_activity"] = datetime.datetime.now().isoformat()
        user_states[user_id] = state
        
        direction_text = "итальянский → русский" if new_direction == "it_to_ru" else "русский → итальянский"
        
        bot.reply_to(
            message,
            f"🔄 Направление перевода изменено на:\n*{direction_text}*",
            parse_mode='Markdown'
        )
        
        # Если есть активная сессия, показываем новое упражнение
        if state.get("awaiting_answer"):
            show_current_exercise(message.chat.id, user_id)
            
    except Exception as e:
        logger.error(f"Error switching direction: {e}")
        bot.reply_to(
            message,
            "❌ Произошла ошибка при смене направления",
            reply_markup=get_main_keyboard()
        )

@bot.message_handler(func=lambda message: message.text == "🏁 Завершить занятие")
def end_session(message):
    """Завершение текущей сессии"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} ending session")
    
    try:
        progress = load_user_data(user_id)
        
        # Находим ближайшее время следующего повторения
        next_review = None
        for word in progress.active_words:
            review_time = datetime.datetime.fromisoformat(word.next_review)
            if next_review is None or review_time < next_review:
                next_review = review_time
        
        # Очищаем текущую сессию
        progress.current_session = []
        progress.current_word_index = 0
        save_user_data(user_id, progress)
        
        # Формируем сообщение
        summary_text = ["🏁 *Занятие завершено!*\n"]
        
        if next_review:
            time_diff = next_review - datetime.datetime.now()
            if time_diff.total_seconds() > 0:
                hours = int(time_diff.total_seconds() // 3600)
                minutes = int((time_diff.total_seconds() % 3600) // 60)
                time_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
                summary_text.append(f"⏰ Следующее повторение через: *{time_str}*\n")
                
                # Устанавливаем время следующего уведомления
                user_states[user_id] = {
                    "translation_direction": user_states[user_id].get("translation_direction", "ru_to_it"),
                    "awaiting_answer": False,
                    "next_notification": next_review.isoformat(),
                    "last_activity": datetime.datetime.now().isoformat()
                }
                
                summary_text.append("Я пришлю уведомление, когда придет время!")
        
        bot.reply_to(
            message,
            "\n".join(summary_text),
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        bot.reply_to(
            message,
            "❌ Произошла ошибка. Сессия завершена.",
            reply_markup=get_main_keyboard()
        )
@bot.message_handler(func=lambda message: message.text == "➡️ Далее")
def next_exercise(message):
    """Переход к следующему упражнению"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} pressed Next button")
    
    try:
        progress = load_user_data(user_id)
        
        # Проверяем, есть ли ещё слова в сессии
        if not progress.current_session or progress.current_word_index >= len(progress.current_session) - 1:
            # Если текущая сессия закончилась, проверяем есть ли ещё слова для повторения
            words_to_review = progress.get_words_for_review()
            if not words_to_review:
                bot.reply_to(
                    message,
                    "Сессия завершена! На данный момент нет слов для повторения.",
                    reply_markup=get_main_keyboard()
                )
                return
            # Начинаем новую сессию
            random.shuffle(words_to_review)
            progress.current_session = words_to_review
            progress.current_word_index = 0
        else:
            # Переходим к следующему слову
            progress.current_word_index += 1
        
        save_user_data(user_id, progress)
        
        # Обновляем состояние
        user_states[user_id]["awaiting_answer"] = True
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
        if user_id in user_states:
            state = user_states[user_id]
            state["awaiting_answer"] = True  # Важно: активируем ожидание нового ответа
            
        progress = load_user_data(user_id)
        if progress.current_session:
            show_current_exercise(message.chat.id, user_id)
        else:
            bot.reply_to(
                message, 
                "❌ Сессия не активна. Начните новое повторение.",
                reply_markup=get_main_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in retry_answer: {e}")
        bot.reply_to(
            message,
            "❌ Произошла ошибка. Начните заново.",
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
        # Загружаем прогресс из JSON
        file_path = f'user_data/user_{user_id}.json'
        with open(file_path, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
            logger.debug(f"Loaded progress data: {progress_data}")

        if not progress_data.get("active_words"):
            logger.error("No active words found")
            return

        # Получаем текущее слово из активных слов
        current_word = progress_data["active_words"][progress_data.get("current_word_index", 0)]
        logger.debug(f"Current word from progress: {current_word}")

        # Получаем примеры из словаря
        word_data = VOCABULARY["Буду изучать"].get(current_word["word"])
        if not word_data:
            logger.error(f"Word {current_word['word']} not found in vocabulary")
            return

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

        # Обновляем прогресс
        if is_correct:
            current_word["correct_answers"] = current_word.get("correct_answers", 0) + 1
            # Обновляем время следующего повторения
            next_interval = calculate_next_interval(current_word["correct_answers"])
            current_word["next_review"] = (
                datetime.datetime.now() + 
                datetime.timedelta(hours=next_interval)
            ).isoformat()

            # Если слово изучено (3+ правильных ответа)
            if current_word["correct_answers"] >= 3:
                logger.debug(f"Word {current_word['word']} learned, adding new word")
                # Перемещаем слово в изученные
                if "learned_words" not in progress_data:
                    progress_data["learned_words"] = []
                progress_data["learned_words"].append(current_word)
                
                # Удаляем из активных
                progress_data["active_words"].remove(current_word)
                
                # Добавляем новое слово если есть
                if progress_data.get("remaining_words"):
                    new_word = random.choice(progress_data["remaining_words"])
                    progress_data["remaining_words"].remove(new_word)
                    
                    new_word_data = VOCABULARY["Буду изучать"][new_word]
                    progress_data["active_words"].append({
                        "word": new_word,
                        "translation": new_word_data["перевод"],
                        "correct_answers": 0,
                        "next_review": datetime.datetime.now().isoformat()
                    })

        # Сохраняем обновленный прогресс
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
            logger.debug("Saved updated progress data")

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
        logger.error(f"Error in handle_answer: {e}", exc_info=True)
        bot.reply_to(
            message,
            "❌ Произошла ошибка. Попробуйте начать заново.",
            reply_markup=get_main_keyboard()
        )
       

def check_and_send_notifications():
    """Проверка и отправка уведомлений"""
    logger.info("Starting notifications checker")
    sent_notifications = {}  # Храним время отправки для каждого пользователя
    
    while True:
        try:
            current_time = datetime.datetime.now()
            
            if os.path.exists('user_data'):
                for filename in os.listdir('user_data'):
                    if not filename.startswith('user_') or not filename.endswith('.json'):
                        continue
                        
                    try:
                        user_id = int(filename.split('_')[1].split('.')[0])
                        state = user_states.get(user_id, {})
                        
                        # Пропускаем если:
                        # 1. Пользователь в активной сессии
                        # 2. Уже отправили уведомление
                        # 3. Нет запланированного времени уведомления
                        if (state.get("awaiting_answer") or 
                            user_id in sent_notifications or 
                            not state.get("next_notification")):
                            continue
                        
                        # Проверяем время следующего уведомления
                        next_notification = datetime.datetime.fromisoformat(state["next_notification"])
                        
                        # Отправляем уведомление только если время пришло
                        if current_time >= next_notification:
                            progress = load_user_data(user_id)
                            words_to_review = progress.get_words_for_review()
                            
                            if words_to_review:
                                notification_text = [
                                    "🔔 *Пора повторить слова!*\n",
                                    f"У вас {len(words_to_review)} слов готово к повторению:"
                                ]
                                
                                for word in words_to_review[:3]:
                                    notification_text.append(f"• {word.word} - {word.translation}")
                                
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
                                    
                                    # Отмечаем что уведомление отправлено
                                    sent_notifications[user_id] = current_time
                                    # Убираем запланированное время из состояния
                                    state.pop("next_notification", None)
                                    user_states[user_id] = state
                                    
                                except telebot.apihelper.ApiTelegramException as e:
                                    if e.error_code == 403:
                                        logger.warning(f"User {user_id} has blocked the bot")
                                    else:
                                        logger.error(f"Error sending notification: {e}")
                                        
                            else:
                                # Если слов для повторения нет, убираем запланированное время
                                state.pop("next_notification", None)
                                user_states[user_id] = state
                        
                    except Exception as e:
                        logger.error(f"Error processing user {filename}: {e}")
                        continue
            
            # Очищаем старые записи об отправленных уведомлениях
            current_time = datetime.datetime.now()
            for user_id in list(sent_notifications.keys()):
                if (current_time - sent_notifications[user_id]).total_seconds() > 3600:  # Через час
                    del sent_notifications[user_id]
                        
        except Exception as e:
            logger.error(f"Error in notification check: {e}")
        
        time.sleep(60)  # Проверка каждую минуту
        

def run_bot():
    """Запуск бота с обработкой сетевых ошибок"""
    logger.info("=== Starting Bot ===")
    logger.info(f"Vocabulary size: {len(VOCABULARY['Буду изучать'])} words")
    
    # Конфигурация подключения
    telebot.apihelper.CONNECT_TIMEOUT = 15
    telebot.apihelper.READ_TIMEOUT = 10
    
    def start_bot():
        try:
            # Проверка соединения
            def check_connection():
                try:
                    import socket
                    socket.create_connection(("api.telegram.org", 443), timeout=5)
                    return True
                except OSError:
                    return False
            
            # Ждем подключения если его нет
            while not check_connection():
                logger.error("No connection to Telegram API. Waiting...")
                time.sleep(10)
            
            # Проверка токена
            try:
                bot_info = bot.get_me()
                logger.info(f"Bot authorized successfully. Bot username: {bot_info.username}")
            except Exception as e:
                logger.error(f"Failed to get bot info: {e}")
                time.sleep(10)
                return
            
            # Сброс и очистка
            try:
                bot.delete_webhook()
                logger.info("Webhook deleted")
                bot.get_updates(offset=-1, timeout=1)
                logger.info("Updates cleared")
            except Exception as e:
                logger.error(f"Error clearing updates: {e}")
            
            # Запуск уведомлений
            import threading
            notification_thread = threading.Thread(
                target=check_and_send_notifications,
                daemon=True
            )
            notification_thread.start()
            logger.info("Notification thread started")
            
            # Основной цикл
            while True:
                try:
                    logger.info("Starting bot polling...")
                    bot.infinity_polling(
                        timeout=15,
                        long_polling_timeout=30,
                        logger_level=logging.ERROR,
                        restart_on_change=False,
                        skip_pending=True,
                        allowed_updates=["message"]
                    )
                except Exception as e:
                    logger.error(f"Polling error: {e}")
                    if not check_connection():
                        logger.error("Connection lost. Waiting to reconnect...")
                        time.sleep(10)
                        continue
                    time.sleep(5)
                    
        except Exception as e:
            logger.error(f"Critical error in start_bot: {e}")
            time.sleep(30)
    
    # Основной цикл с перезапуском
    while True:
        try:
            start_bot()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            time.sleep(60)
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
 