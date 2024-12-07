import telebot
from telebot import types
import json
import datetime
import time
import random
import os
import logging
import sys
import signal
from typing import Dict, Optional, List
from vocabulary import VOCABULARY
import threading
from pydub import AudioSegment
import speech_recognition as sr
import requests
import tempfile
import shutil  # Добавлено для работы с файлами

# Базовые настройки логирования
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
user_states = {}
WORDS_PER_SESSION = 5
CORRECT_FOR_NEW_WORD = 3
CORRECT_FOR_LEARNED = 8

WORD_STATUS = {
    "NEW": "new",
    "LEARNING": "learning",
    "LEARNED": "learned"
}

def get_now() -> datetime.datetime:
    """Унифицированное получение текущего времени"""
    return datetime.datetime.now().replace(tzinfo=None)

def parse_time(time_str: str) -> datetime.datetime:
    """Безопасный парсинг времени из строки"""
    try:
        dt = datetime.datetime.fromisoformat(time_str)
        return dt.replace(tzinfo=None)
    except:
        return get_now()
        
def calculate_next_interval(correct_answers: int) -> int:
   intervals = {
   0: 1, 1: 4, 2: 8, 3: 24, 4: 72,
   5: 168, 6: 336, 7: 720
   }
   return intervals.get(correct_answers, 720)

def create_word_data(word: str, translation: str) -> dict:
   return {
       "word": word,
       "translation": translation,
       "correct_answers": 0,
       "next_review": get_now().isoformat(),
       "status": WORD_STATUS["NEW"],
       "total_attempts": 0
   }

def create_initial_user_data(user_id: int) -> dict:
    logger.info(f"Creating initial data for user {user_id}")
    all_words = list(VOCABULARY["Буду изучать"].keys())
    random.shuffle(all_words)
    
    initial_words = []
    for word in all_words[:WORDS_PER_SESSION]:
        word_data = VOCABULARY["Буду изучать"][word]
        initial_words.append(create_word_data(word, word_data["перевод"]))
    
    remaining = all_words[WORDS_PER_SESSION:]
    logger.info(f"Created initial data with {len(initial_words)} active words and {len(remaining)} remaining")
    
    return {
        "user_id": user_id,
        "active_words": initial_words,
        "learned_words": [],
        "remaining_words": remaining,
        "current_session": [],
        "current_word_index": 0,
        "last_update": get_now().isoformat()
    }

def load_user_data(user_id: int) -> dict:
   if not os.path.exists('user_data'):
       os.makedirs('user_data')
   
   file_path = f'user_data/user_{user_id}.json'
   if os.path.exists(file_path):
       with open(file_path, 'r', encoding='utf-8') as f:
           return json.load(f)
   return create_initial_user_data(user_id)

def save_user_data(user_id: int, data: dict):
   if not os.path.exists('user_data'):
       os.makedirs('user_data')
       
   file_path = f'user_data/user_{user_id}.json'
   with open(file_path, 'w', encoding='utf-8') as f:
       json.dump(data, f, ensure_ascii=False, indent=2)

def get_words_for_review(user_data: dict) -> List[dict]:
    """Получение списка слов для повторения"""
    logger.debug(f"Getting words for review from active words: {[w['word'] for w in user_data['active_words']]}")
    
    current_time = get_now()
    overdue_words = []
    future_words = []
    new_words = []

    # Разделяем слова на категории
    for word in user_data["active_words"]:
        if word["correct_answers"] == 0:
            new_words.append(word)
        else:
            review_time = parse_time(word["next_review"])
            if review_time <= current_time:
                overdue_words.append(word)
            else:
                future_words.append(word)

    # Приоритет: новые слова, потом просроченные, потом будущие
    words_to_return = []
    words_to_return.extend(new_words[:WORDS_PER_SESSION])
    
    if len(words_to_return) < WORDS_PER_SESSION:
        words_to_return.extend(overdue_words[:WORDS_PER_SESSION - len(words_to_return)])
    
    if len(words_to_return) < WORDS_PER_SESSION:
        random.shuffle(future_words)
        words_to_return.extend(future_words[:WORDS_PER_SESSION - len(words_to_return)])

    logger.debug(f"Selected words for review: {[w['word'] for w in words_to_return]}")
    return words_to_return[:WORDS_PER_SESSION]

def update_word_progress(word: dict, is_correct: bool) -> dict:
    """Обновление прогресса слова"""
    word["total_attempts"] = word.get("total_attempts", 0) + 1
    
    if is_correct:
        previous_correct = word.get("correct_answers", 0)
        word["correct_answers"] = previous_correct + 1
        
        if word["correct_answers"] >= CORRECT_FOR_LEARNED:
            word["status"] = WORD_STATUS["LEARNED"]
        elif word["correct_answers"] > 0:
            word["status"] = WORD_STATUS["LEARNING"]
            
        next_interval = calculate_next_interval(word["correct_answers"])
        next_review = get_now() + datetime.timedelta(hours=next_interval)
        word["next_review"] = next_review.isoformat()
        
        logger.debug(
            f"Word {word['word']} progress updated: "
            f"correct_answers: {previous_correct} -> {word['correct_answers']}, "
            f"next_review: {word['next_review']}"
        )
    
    return word
    
def get_main_keyboard():
   markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
   markup.row(types.KeyboardButton("🎯 Начать повторение"))
   markup.row(types.KeyboardButton("🔄 Сменить направление перевода"), 
              types.KeyboardButton("📊 Статистика"))
   markup.row(types.KeyboardButton("/start"), types.KeyboardButton("ℹ️ Помощь"))
   return markup

def get_exercise_keyboard() -> types.ReplyKeyboardMarkup:
    """Создание клавиатуры для упражнения"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("💡 Подсказка"), 
               types.KeyboardButton("🎤 Голосовой ответ"))
    markup.row(types.KeyboardButton("🔄 Сменить направление"), 
               types.KeyboardButton("⏩ Пропустить"))
    markup.row(types.KeyboardButton("🏁 Завершить занятие"))
    return markup

def get_next_keyboard():
   markup = types.ReplyKeyboardMarkup(resize_keyboard=True) 
   markup.row(types.KeyboardButton("➡️ Далее"))
   markup.row(types.KeyboardButton("🏁 Завершить занятие"))
   return markup

def get_retry_keyboard():
   markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
   markup.row(types.KeyboardButton("🔄 Повторить"))
   markup.row(types.KeyboardButton("💡 Подсказка"), types.KeyboardButton("➡️ Далее"))
   markup.row(types.KeyboardButton("🏁 Завершить занятие"))
   return markup

def normalize_text(text: str) -> str:
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
   user_answer = user_answer.strip().replace('`', "'")
   
   if user_answer == correct_answer:
       return True
       
   if user_answer in alternatives:
       return True
       
   normalized_user = normalize_text(user_answer)
   normalized_correct = normalize_text(correct_answer)
   
   if normalized_user == normalized_correct:
       return True
       
   for alt in alternatives:
       if normalized_user == normalize_text(alt):
           return True
           
   return False

@bot.message_handler(func=lambda message: message.text == "🎤 Голосовой ответ")
def voice_answer_prompt(message):
    """Подсказка для голосового ответа"""
    bot.reply_to(
        message, 
        "🎤 Запишите свой ответ голосовым сообщением.\n"
        "Говорите чётко и не слишком быстро.",
        reply_markup=get_exercise_keyboard()
    )
    
# @bot.message_handler(content_types=['voice'])
# def handle_voice(message):
    # """Обработка голосовых сообщений"""
    # try:
        # user_id = message.from_user.id
        # state = user_states.get(user_id, {})
        # if not state.get("awaiting_answer"):
            # return

        # # Получаем файл
        # file_info = bot.get_file(message.voice.file_id)
        # file_path = file_info.file_path
        # file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

        # # Скачиваем аудио во временный файл
        # with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
            # response = requests.get(file_url)
            # temp_ogg.write(response.content)
            # temp_ogg_path = temp_ogg.name

        # # Конвертируем в wav
        # with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            # audio = AudioSegment.from_ogg(temp_ogg_path)
            # audio.export(temp_wav.name, format="wav")
            # temp_wav_path = temp_wav.name

        # # Распознаем речь
        # r = sr.Recognizer()
        # with sr.AudioFile(temp_wav_path) as source:
            # audio_data = r.record(source)
            
            # # Выбираем язык в зависимости от направления перевода
            # if state["translation_direction"] == "ru_to_it":
                # text = r.recognize_google(audio_data, language="it-IT")
            # else:
                # text = r.recognize_google(audio_data, language="ru-RU")

        # # Передаем распознанный текст в обработчик ответов
        # message.text = text
        # handle_answer(message)

        # # Очищаем временные файлы
        # os.unlink(temp_ogg_path)
        # os.unlink(temp_wav_path)

    # except sr.UnknownValueError:
        # bot.reply_to(message, "🎤 Не удалось распознать речь. Попробуйте ещё раз.")
    # except sr.RequestError as e:
        # bot.reply_to(message, "🎤 Ошибка сервиса распознавания речи. Попробуйте позже.")
    # except Exception as e:
        # logger.error(f"Error processing voice message: {e}")
        # bot.reply_to(message, "🎤 Произошла ошибка при обработке голосового сообщения.")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    """Обработка голосовых сообщений"""
    try:
        user_id = message.from_user.id
        state = user_states.get(user_id, {})
        if not state.get("awaiting_answer"):
            return

        file_info = bot.get_file(message.voice.file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

        # Скачиваем аудио
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
            response = requests.get(file_url)
            temp_ogg.write(response.content)
            temp_ogg_path = temp_ogg.name

        # Конвертируем в WAV
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            audio = AudioSegment.from_ogg(temp_ogg_path)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(temp_wav.name, format="wav")
            temp_wav_path = temp_wav.name

        # Распознаем речь
        r = sr.Recognizer()
        with sr.AudioFile(temp_wav_path) as source:
            audio_data = r.record(source)
            
            # Выбираем язык в зависимости от направления перевода
            language = "it-IT" if state["translation_direction"] == "ru_to_it" else "ru-RU"
            text = r.recognize_google(audio_data, language=language)
            logger.debug(f"Voice recognized ({language}): {text}")

        # Очищаем файлы
        os.unlink(temp_ogg_path)
        os.unlink(temp_wav_path)

        # Передаем в обработчик
        message.text = text
        handle_answer(message)

    except sr.UnknownValueError:
        lang_text = "итальянском" if state["translation_direction"] == "ru_to_it" else "русском"
        bot.reply_to(
            message, 
            f"🎤 Не удалось распознать речь на {lang_text} языке. "
            "Попробуйте говорить чётче и медленнее.",
            reply_markup=get_exercise_keyboard()
        )
    except sr.RequestError as e:
        bot.reply_to(
            message, 
            "🎤 Ошибка сервиса распознавания. Попробуйте ответить текстом.",
            reply_markup=get_exercise_keyboard()
        )
    except Exception as e:
        logger.error(f"Error processing voice: {e}")
        bot.reply_to(
            message, 
            "🎤 Ошибка обработки голосового сообщения.",
            reply_markup=get_exercise_keyboard()
        )
        
@bot.message_handler(commands=['start'])
def send_welcome(message):
   user_id = message.from_user.id
   user_data = load_user_data(user_id)
   user_states[user_id] = {
       "translation_direction": "ru_to_it",
       "awaiting_answer": False
   }
   
   welcome_text = (
       "*Привет! *\n"
       "Я бот для изучения итальянского языка.\n\n"
       f"📚 Активных слов: {len(user_data['active_words'])}\n"
       f"✅ Изучено слов: {len(user_data['learned_words'])}\n\n"
       "🔹 *'Начать повторение'* - для изучения слов\n"
       "🔹 *'Сменить направление'* - выбор направления перевода\n"
       "🔹 *'Статистика'* - для просмотра прогресса\n\n"
       "Начнём? 😊"
   )
   bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text in ["🎯 Начать повторение", "/review"])
def start_review(message):
   user_id = message.from_user.id
   user_data = load_user_data(user_id)
   words_to_review = get_words_for_review(user_data)
   
   if not words_to_review:
       bot.reply_to(message, "Нет слов для повторения", reply_markup=get_main_keyboard())
       return

   user_data["current_session"] = words_to_review
   user_data["current_word_index"] = 0
   save_user_data(user_id, user_data)
   
   user_states[user_id] = {
       "translation_direction": "ru_to_it",
       "awaiting_answer": True
   }
   
   show_current_exercise(message.chat.id, user_id)

def show_current_exercise(chat_id: int, user_id: int):
    logger.debug(f"Showing exercise for user {user_id}")
    user_data = load_user_data(user_id)
    
    if not user_data["current_session"]:
        logger.debug("No current session")
        bot.send_message(chat_id, "❌ Нет активной сессии", reply_markup=get_main_keyboard())
        return
    
    current_word = user_data["current_session"][user_data["current_word_index"]]
    word_data = VOCABULARY["Буду изучать"].get(current_word["word"])
    example = random.choice(word_data["примеры"])
    
    state = user_states.get(user_id, {})
    translation_direction = state.get("translation_direction", "ru_to_it")
    question = example["русский"] if translation_direction == "ru_to_it" else example["итальянский"]
    direction_text = "итальянский" if translation_direction == "ru_to_it" else "русский"
    
    user_states[user_id] = {
        "translation_direction": translation_direction,
        "awaiting_answer": True,
        "current_example": example
    }
    
    progress_bar = "🟢" * current_word["correct_answers"] + "⚪️" * (CORRECT_FOR_LEARNED - current_word["correct_answers"])
    message_text = (
        f"*{current_word['word']} - {current_word['translation']}*\n\n"
        f"Переведите на {direction_text}:\n"
        f"*{question}*\n\n"
        f"Прогресс изучения: {progress_bar}\n"
        f"_Слово {user_data['current_word_index'] + 1} из 5_"
    )
    
    bot.send_message(chat_id, message_text, parse_mode='Markdown', reply_markup=get_exercise_keyboard())
    logger.debug(f"Exercise shown: {current_word['word']}")
    
@bot.message_handler(func=lambda message: message.text == "⏩ Пропустить")
def skip_word(message):
    logger.debug("Skip word requested")
    user_id = message.from_user.id
    user_data = load_user_data(user_id)
    
    if not user_data.get("current_session"):
        return
        
    if user_data["current_word_index"] >= len(user_data["current_session"]) - 1:
        user_data["current_session"] = []
        user_data["current_word_index"] = 0
        save_user_data(user_id, user_data)
        bot.reply_to(message, "Сессия завершена", reply_markup=get_main_keyboard())
        return
        
    user_data["current_word_index"] += 1
    save_user_data(user_id, user_data)
    
    bot.reply_to(message, "⏩ Слово пропущено")
    show_current_exercise(message.chat.id, user_id)
    
@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_statistics(message):
   user_id = message.from_user.id
   user_data = load_user_data(user_id)
   
   active_words = user_data["active_words"]
   new_words = sum(1 for w in active_words if w["correct_answers"] == 0)
   learning_words = sum(1 for w in active_words if 0 < w["correct_answers"] < CORRECT_FOR_LEARNED)
   learned_words = len(user_data["learned_words"])
   
   stats_text = [
       "📊 *Статистика обучения:*\n",
       f"📚 Активные слова: {len(active_words)}",
       f"🆕 Новые слова (0 ответов): {new_words}",
       f"📝 В процессе (1-7 ответов): {learning_words}",
       f"✅ Изучено (8+ ответов): {learned_words}\n",
       f"Всего слов в словаре: {len(VOCABULARY['Буду изучать'])}"
   ]
   
   bot.reply_to(message, "\n".join(stats_text), parse_mode='Markdown', reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "🔄 Сменить направление")
def switch_translation_direction(message):
    logger.debug("Direction switch requested")
    user_id = message.from_user.id
    state = user_states.get(user_id, {"translation_direction": "ru_to_it"})
    new_direction = "it_to_ru" if state.get("translation_direction") == "ru_to_it" else "ru_to_it"
    
    user_states[user_id] = {
        "translation_direction": new_direction,
        "awaiting_answer": state.get("awaiting_answer", False),
        "current_example": state.get("current_example")
    }
    
    direction_text = "итальянский → русский" if new_direction == "it_to_ru" else "русский → итальянский"
    bot.reply_to(message, f"🔄 Направление перевода изменено на:\n*{direction_text}*", 
                parse_mode='Markdown')
    
    if state.get("awaiting_answer"):
        show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def show_help(message):
    help_text = [
        "*📋 Доступные команды:*\n",
        "🎯 *Начать повторение* - изучение слов",
        "🔄 *Сменить направление* - изменить направление перевода",
        "📊 *Статистика* - прогресс обучения\n",
        "*Дополнительные команды:*",
        "`/start` - перезапуск бота",
        "`/status` - проверка статуса слов",
        "`/reset` - сброс прогресса\n",
        "*Во время занятия:*",
        "🎤 Вы можете отвечать голосовыми сообщениями",
        "💡 Подсказка - показать первые буквы",
        "⏩ Пропустить - пропустить слово",
        "🏁 Завершить занятие - закончить сессию"
    ]
    bot.reply_to(message, "\n".join(help_text), parse_mode='Markdown', reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "💡 Подсказка")
def show_hint(message):
   user_id = message.from_user.id
   state = user_states.get(user_id, {})
   
   if not state.get("awaiting_answer") or not state.get("current_example"):
       return
       
   example = state["current_example"]
   answer = example["итальянский"] if state["translation_direction"] == "ru_to_it" else example["русский"]
   hint = ' '.join(word[0] + '_' * (len(word)-1) for word in answer.split())
   
   bot.reply_to(message, f"💡 Подсказка:\n{hint}", reply_markup=get_exercise_keyboard())

@bot.message_handler(func=lambda message: message.text == "🏁 Завершить занятие")
def end_session(message):
   user_id = message.from_user.id
   user_data = load_user_data(user_id)
   user_data["current_session"] = []
   user_data["current_word_index"] = 0
   save_user_data(user_id, user_data)
   
   bot.reply_to(message, "Занятие завершено!", reply_markup=get_main_keyboard())

# @bot.message_handler(commands=['status'])
# def check_status(message):
    # user_id = message.from_user.id
    # user_data = load_user_data(user_id)
    # current_time = get_now()
    
    # status_text = ["📊 *Текущий статус:*\n"]
    # words_to_review = []
    
    # for word in user_data["active_words"]:
        # review_time = parse_time(word["next_review"])
        # if review_time <= current_time:
            # words_to_review.append(word)
    
    # if words_to_review:
        # status_text.append("🔔 *Слова для повторения:*")
        # for word in words_to_review:
            # status_text.append(f"• {word['word']} - {word['translation']}")
    # else:
        # status_text.append("🔕 Нет слов для повторения")
        
    # bot.reply_to(message, "\n".join(status_text), parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def check_status(message):
    """Проверка статуса слов"""
    user_id = message.from_user.id
    try:
        user_data = load_user_data(user_id)
        current_time = get_now()
        
        status_text = ["📊 *Текущий статус:*\n"]
        
        # Разделяем слова по времени
        ready_now = []
        upcoming = []
        for word in user_data["active_words"]:
            review_time = parse_time(word["next_review"])
            if review_time <= current_time:
                ready_now.append(word)
            else:
                time_diff = review_time - current_time
                hours = int(time_diff.total_seconds() // 3600)
                upcoming.append((word, hours))
        
        # Слова для повторения сейчас
        if ready_now:
            status_text.append("🔔 *Готовы к повторению:*")
            for word in ready_now:
                status_text.append(f"• {word['word']} - {word['translation']}")
        else:
            status_text.append("✅ Нет слов для повторения прямо сейчас")
        
        # Предстоящие повторения
        if upcoming:
            status_text.append("\n⏰ *Предстоящие повторения:*")
            # Сортируем по времени
            upcoming.sort(key=lambda x: x[1])
            for word, hours in upcoming:
                if hours < 24:
                    status_text.append(f"• {word['word']} - через {hours}ч")
                else:
                    days = hours // 24
                    remaining_hours = hours % 24
                    status_text.append(f"• {word['word']} - через {days}д {remaining_hours}ч")
        
        bot.reply_to(message, "\n".join(status_text), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        bot.reply_to(message, "❌ Ошибка при проверке статуса")
        
@bot.message_handler(func=lambda message: message.text == "➡️ Далее")
def next_exercise(message):
    """Переход к следующему упражнению"""
    user_id = message.from_user.id
    logger.debug(f"Next exercise requested by user {user_id}")
    
    try:
        user_data = load_user_data(user_id)
        if not user_data.get("current_session"):
            logger.debug("No current session")
            bot.reply_to(
                message,
                "❌ Нет активной сессии. Начните новое занятие.",
                reply_markup=get_main_keyboard()
            )
            return
            
        # Проверяем индекс
        current_index = user_data.get("current_word_index", 0)
        if current_index >= len(user_data["current_session"]) - 1:
            # Завершаем сессию
            logger.debug("End of session reached")
            user_data["current_session"] = []
            user_data["current_word_index"] = 0
            save_user_data(user_id, user_data)
            
            bot.reply_to(
                message,
                "✅ Все задания выполнены!\nНачните новое занятие, когда будете готовы.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Переходим к следующему слову
        user_data["current_word_index"] += 1
        save_user_data(user_id, user_data)
        
        # Устанавливаем состояние ожидания ответа
        user_states[user_id] = {
            "translation_direction": user_states.get(user_id, {}).get("translation_direction", "ru_to_it"),
            "awaiting_answer": True,
            "current_example": None
        }
        
        # Показываем следующее упражнение
        show_current_exercise(message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Error in next_exercise: {e}", exc_info=True)
        bot.reply_to(
            message,
            "❌ Произошла ошибка. Попробуйте начать заново.",
            reply_markup=get_main_keyboard()
        )
        
@bot.message_handler(commands=['reset'])
def handle_reset(message):
    """Обработка команды /reset"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested data reset")
    
    try:
        # Удаляем старый файл с данными
        file_path = f'user_data/user_{user_id}.json'
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted user data file: {file_path}")
        
        # Создаем новые данные
        create_initial_user_data(user_id)
        
        # Сбрасываем состояние
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False,
            "current_example": None
        }
        
        bot.reply_to(
            message,
            "🔄 Данные полностью сброшены. Начинаем обучение сначала!",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in handle_reset: {e}")
        bot.reply_to(
            message,
            "❌ Произошла ошибка при сбросе данных",
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

@bot.message_handler(func=lambda message: message.text == "🔄 Повторить")
def retry_answer(message):
    """Повторная попытка ответа"""
    user_id = message.from_user.id
    logger.debug(f"User {user_id} retrying answer")
    
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
        
@bot.message_handler(func=lambda message: True)
def handle_answer(message):
   """Обработка ответов пользователя"""
   user_id = message.from_user.id
   state = user_states.get(user_id, {})
   if not state.get("awaiting_answer"):
       return

   try:
       # Загружаем и проверяем данные
       user_data = load_user_data(user_id)
       logger.debug(f"Active words before update: {[w['word'] for w in user_data['active_words']]}")
       
       if not user_data.get("current_session"):
           logger.debug("No current session found")
           return

       current_word = user_data["current_session"][user_data["current_word_index"]]
       example = state.get("current_example")
       if not example:
           logger.error(f"No current example found for user {user_id}")
           return

       # Определяем правильный ответ
       if state["translation_direction"] == "ru_to_it":
           correct_answer = example["итальянский"]
           alternatives = example.get("альтернативы_ит", [])
       else:
           correct_answer = example["русский"]
           alternatives = example.get("альтернативы_рус", [])

       # Проверяем ответ
       is_correct = check_answer(message.text, correct_answer, alternatives)
       logger.debug(f"Checking answer '{message.text}' for word '{current_word['word']}': {is_correct}")

       # Обновляем прогресс
       current_word_found = False
       for i, word in enumerate(user_data["active_words"]):
           if word["word"] == current_word["word"]:
               current_word_found = True
               previous_correct = word["correct_answers"]
               updated_word = update_word_progress(word, is_correct)
               
               # Проверяем достижение 3 правильных ответов
               if is_correct and previous_correct < CORRECT_FOR_NEW_WORD and updated_word["correct_answers"] >= CORRECT_FOR_NEW_WORD:
                   if user_data["remaining_words"]:
                       new_word = random.choice(user_data["remaining_words"])
                       user_data["remaining_words"].remove(new_word)
                       word_data = VOCABULARY["Буду изучать"][new_word]
                       new_word_data = create_word_data(new_word, word_data["перевод"])
                       user_data["active_words"].append(new_word_data)
                       logger.info(f"Added new word '{new_word}' after '{word['word']}' reached {CORRECT_FOR_NEW_WORD} correct answers")

               # Проверяем достижение 8 правильных ответов
               if updated_word["correct_answers"] >= CORRECT_FOR_LEARNED:
                   logger.info(f"Word '{updated_word['word']}' learned, moving to learned words")
                   user_data["learned_words"].append(updated_word)
                   user_data["active_words"].pop(i)
                   # Обновляем текущую сессию
                   user_data["current_session"] = [w for w in user_data["current_session"] 
                                                 if w["word"] != updated_word["word"]]
               else:
                   user_data["active_words"][i] = updated_word
                   current_word.update(updated_word)  # Обновляем слово в текущей сессии
               break

       if not current_word_found:
           logger.error(f"Word '{current_word['word']}' not found in active words")
           return

       # Сохраняем обновленные данные
       logger.debug(f"Active words after update: {[w['word'] for w in user_data['active_words']]}")
       save_user_data(user_id, user_data)

       # Формируем ответ пользователю
       progress_bar = "🟢" * updated_word["correct_answers"] + "⚪️" * (CORRECT_FOR_LEARNED - updated_word["correct_answers"])
       
       if is_correct:
           response = [
               "✅ *Правильно!*\n",
               f"Ваш ответ: _{message.text}_",
               f"Прогресс: {progress_bar}"
           ]
           
           # Добавляем сообщение о новом слове
           if previous_correct < CORRECT_FOR_NEW_WORD and updated_word["correct_answers"] >= CORRECT_FOR_NEW_WORD:
               response.append("\n🎉 Вы достигли 3 правильных ответов!")
               if user_data["remaining_words"]:
                   response.append("Добавлено новое слово для изучения!")
           
           markup = get_next_keyboard()
       else:
            response = [
                "❌ *Ошибка!*\n",
                "Ваш ответ с исправлениями:",
                f"{highlight_differences(message.text, correct_answer)}\n",
                f"Правильный ответ: *{correct_answer}*",
                f"Прогресс: {progress_bar}"
            ]
            markup = get_retry_keyboard()
           

       # Отправляем ответ
       state["awaiting_answer"] = False
       bot.reply_to(message, "\n".join(response), parse_mode='Markdown', reply_markup=markup)

   except Exception as e:
       logger.error(f"Error in handle_answer: {e}", exc_info=True)
       bot.reply_to(message, "❌ Произошла ошибка. Попробуйте начать заново.",
                   reply_markup=get_main_keyboard())
                   

def check_notifications():
   while True:
       try:
           current_time = get_now()
           for filename in os.listdir('user_data'):
               try:
                   user_id = int(filename.split('_')[1].split('.')[0])
                   user_data = load_user_data(user_id)
                   words_to_review = [
                       word for word in user_data["active_words"]
                       if parse_time(word["next_review"]) <= current_time
                   ]
                   
                   if words_to_review:
                       text = (
                           "🔔 Пора повторить слова!\n\n"
                           f"Готово к повторению: {len(words_to_review)} слов\n\n"
                       )
                       text += "\n".join(f"• {w['word']} - {w['translation']}" 
                                       for w in words_to_review[:3])
                       bot.send_message(user_id, text, reply_markup=get_main_keyboard())
               except Exception as e:
                   logger.error(f"Notification error for user {filename}: {e}")
       except Exception as e:
           logger.error(f"Notification check error: {e}")
       time.sleep(600)
       
def send_initial_message():
    """Отправка приветственного сообщения при запуске"""
    try:
        if os.path.exists('user_data'):
            for filename in os.listdir('user_data'):
                try:
                    user_id = int(filename.split('_')[1].split('.')[0])
                    bot.send_message(
                        user_id,
                        "🟢 Бот запущен и готов к работе!\nНажмите /start для начала.",
                        reply_markup=get_main_keyboard()
                    )
                    logger.info(f"Sent startup message to user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to send startup message: {e}")
    except Exception as e:
        logger.error(f"Error in send_initial_message: {e}")

def run_bot():
    try:
        if os.path.exists('user_data'):
            shutil.rmtree('user_data')
        os.makedirs('user_data')
        logger.info("Cleared old user data")

        bot.delete_webhook()
        bot.get_updates(offset=-1)  # Очищаем старые апдейты
        
        notifications = threading.Thread(target=check_notifications, daemon=True)
        notifications.start()
        
        send_initial_message()  # Отправляем приветственное сообщение
        logger.info("Bot started")
        
        bot.infinity_polling(timeout=60)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        sys.exit(1)


if __name__ == "__main__":
   try:
       signal.signal(signal.SIGINT, lambda s, f: (
           logger.info("Shutting down..."),
           sys.exit(0)
       ))
       run_bot()
   except Exception as e:
       logger.error(f"Fatal error: {e}")
       raise
       
   
   
   