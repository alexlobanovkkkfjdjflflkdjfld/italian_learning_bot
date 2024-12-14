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
from gtts import gTTS
import asyncio
from pydub.utils import mediainfo
import platform
import subprocess

# Устанавливаем путь к ffmpeg для pydub
# Настраиваем пути для pydub

AudioSegment.converter = "/usr/bin/ffmpeg"
AudioSegment.ffmpeg = "/usr/bin/ffmpeg"
AudioSegment.ffprobe = "/usr/bin/ffprobe"  # Точный путь, который мы нашли

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

# Изменение функции get_words_for_review
def get_words_for_review(user_data: dict) -> List[dict]:
    """Получение списка слов для повторения"""
    logger.debug(f"Getting words for review from active words: {[w['word'] for w in user_data['active_words']]}")
    
    current_time = get_now()
    return [word for word in user_data["active_words"] 
            if parse_time(word["next_review"]) <= current_time]

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
   markup.row(types.KeyboardButton("🎯 Начать повторение"),
              types.KeyboardButton("🏆 Рейтинг"))
   markup.row(types.KeyboardButton("🔀 Сменить направление перевода"), 
              types.KeyboardButton("📊 Статистика"))
   markup.row(types.KeyboardButton("♻️ Перезапустить бота"), types.KeyboardButton("ℹ️ Помощь"))
   return markup

def get_exercise_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("💡 Подсказка"),
        types.KeyboardButton("🎤 Голосовой ответ")
    )
    markup.row(
        types.KeyboardButton("🔀 Сменить направление"),
        types.KeyboardButton("⏩ Пропустить")
    )
    markup.row(
        types.KeyboardButton("🏁 Завершить занятие")
    )
    return markup

def get_next_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("➡️ Далее"),
        types.KeyboardButton("🔊 Прослушать")
    )
    markup.row(
        types.KeyboardButton("🏁 Завершить занятие")
    )
    return markup

def get_retry_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("🔄 Повторить"),
        types.KeyboardButton("💡 Подсказка")
    )
    markup.row(
        types.KeyboardButton("➡️ Далее"),
        types.KeyboardButton("🏁 Завершить занятие")
    )
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

def delete_messages_with_delay(chat_id: int, message_ids: list):
    """Удаление сообщений с небольшой задержкой для анимации"""
    for msg_id in message_ids:
        try:
            # Добавляем задержку 0.3 секунды между удалениями
            time.sleep(0.3)
            bot.delete_message(chat_id, msg_id)
        except Exception as e:
            logger.debug(f"Could not delete message {msg_id}: {e}")
    
@bot.message_handler(func=lambda message: message.text == "🎤 Голосовой ответ")
def voice_answer_prompt(message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {})
    
    sent_message = bot.reply_to(
        message, 
        "🎤 Запишите свой ответ голосовым сообщением.\n"
        "Говорите чётко и не слишком быстро.",
        reply_markup=get_exercise_keyboard()
    )
    
    # Добавляем ID сообщений
    message_ids = state.get("message_ids", [])
    message_ids.extend([message.message_id, sent_message.message_id])
    state["message_ids"] = message_ids
    user_states[user_id] = state
    
@bot.message_handler(func=lambda message: message.text == "🏆 Рейтинг")
def show_rating(message):
    try:
        user_ratings = []
        current_user_id = message.from_user.id
        
        # Собираем данные из всех файлов user_data
        for filename in os.listdir('user_data'):
            if filename.startswith('user_') and filename.endswith('.json'):
                try:
                    user_id = int(filename.split('_')[1].split('.')[0])
                    with open(os.path.join('user_data', filename), 'r', encoding='utf-8') as f:
                        user_data = json.load(f)
                        
                        user_ratings.append({
                            'user_id': user_id,
                            'active_words': len(user_data.get('active_words', [])),
                            'learned_words': len(user_data.get('learned_words', [])),
                            'total_words': len(user_data.get('active_words', [])) + len(user_data.get('learned_words', [])),
                            'is_current': user_id == current_user_id
                        })
                except Exception as e:
                    logger.error(f"Error processing user file {filename}: {e}")
                    continue
        
        # Сортируем по общему количеству слов
        user_ratings.sort(key=lambda x: x['total_words'], reverse=True)
        
        # Формируем сообщение
        rating_text = ["🏆 *Рейтинг учеников:*\n"]
        
        for i, user in enumerate(user_ratings, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
            current_mark = "👉" if user['is_current'] else " "
            
            rating_text.append(
                f"{current_mark}{medal} #{i}: ID{user['user_id']}\n"
                f"   📚 Изучается: {user['active_words']}\n"
                f"   ✅ Изучено: {user['learned_words']}\n"
                f"   📊 Всего слов: {user['total_words']}"
            )
        
        # Отправляем результат
        sent_message = bot.reply_to(
            message,
            "\n\n".join(rating_text),
            parse_mode='Markdown'
        )
        
        # Сохраняем ID сообщения для последующего удаления
        state = user_states.get(current_user_id, {})
        state["message_ids"] = [sent_message.message_id, message.message_id]
        user_states[current_user_id] = state
        
    except Exception as e:
        logger.error(f"Error showing rating: {e}")
        sent_message = bot.reply_to(
            message,
            "❌ Произошла ошибка при формировании рейтинга"
        )
        # Сохраняем ID сообщения об ошибке
        state = user_states.get(current_user_id, {})
        state["message_ids"] = [sent_message.message_id, message.message_id]
        user_states[current_user_id] = state
        
@bot.message_handler(func=lambda message: message.text == "🔊 Прослушать")
def play_phrase(message):
    try:
        user_id = message.from_user.id
        state = user_states.get(user_id, {})
        example = state.get("current_example")
        if not example:
            return
            
        # Выбираем текст и язык в зависимости от направления перевода
        if state["translation_direction"] == "ru_to_it":
            text = example["итальянский"]
            lang = "it"
        else:
            text = example["русский"]
            lang = "ru"
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(temp_audio.name)
            
            with open(temp_audio.name, 'rb') as audio:
                sent_message = bot.send_voice(message.chat.id, audio)
            
            # Просто добавляем новые ID сообщений, не удаляя старые
            message_ids = state.get("message_ids", [])
            message_ids.extend([message.message_id, sent_message.message_id])
            state["message_ids"] = message_ids
            user_states[user_id] = state
            
        os.unlink(temp_audio.name)

    except Exception as e:
        logger.error(f"Error playing phrase: {e}")
        sent_message = bot.reply_to(
            message, 
            "❌ Ошибка при воспроизведении фразы",
            reply_markup=get_next_keyboard()
        )
        state["message_ids"].append(sent_message.message_id)
     
     
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    """Обработка голосовых сообщений"""
    try:
        user_id = message.from_user.id
        state = user_states.get(user_id, {})
        if not state.get("awaiting_answer"):
            return

        # Добавляем ID голосового сообщения в список для удаления
        state["message_ids"].append(message.message_id)

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
        sent_message = bot.reply_to(
            message, 
            f"🎤 Не удалось распознать речь на {lang_text} языке. "
            "Попробуйте говорить чётче и медленнее.",
            reply_markup=get_exercise_keyboard()
        )
        # Сохраняем ID сообщения об ошибке
        state["message_ids"].append(sent_message.message_id)
        
    except sr.RequestError as e:
        sent_message = bot.reply_to(
            message, 
            "🎤 Ошибка сервиса распознавания. Попробуйте ответить текстом.",
            reply_markup=get_exercise_keyboard()
        )
        # Сохраняем ID сообщения об ошибке
        state["message_ids"].append(sent_message.message_id)
        
    except Exception as e:
        logger.error(f"Error processing voice: {e}")
        sent_message = bot.reply_to(
            message, 
            "🎤 Ошибка обработки голосового сообщения.",
            reply_markup=get_exercise_keyboard()
        )
        # Сохраняем ID сообщения об ошибке
        state["message_ids"].append(sent_message.message_id)
        

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda message: message.text == "♻️ Перезапустить бота")  # У вас сейчас 🔄, а в кнопке ♻️
def send_welcome(message):
    user_id = message.from_user.id
    user_data = load_user_data(user_id)
    user_states[user_id] = {
        "translation_direction": "ru_to_it",
        "awaiting_answer": False,
        "message_ids": [],
        "last_question_id": None
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
    sent_message = bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard())
    
    # Сохраняем ID сообщений
    state = user_states.get(user_id, {})
    state["message_ids"] = [sent_message.message_id, message.message_id]
    user_states[user_id] = state


@bot.message_handler(func=lambda message: message.text in ["🎯 Начать повторение", "/review"])
# @maintenance_aware
def start_review(message):
    user_id = message.from_user.id
    user_data = load_user_data(user_id)
    words_to_review = get_words_for_review(user_data)
    
    if not words_to_review:
        sent_message = bot.reply_to(
    message, 
    "📝 Сейчас нет слов для повторения.\nМы напомним Вам, когда подойдёт время по графику интервального повторения.", 
    reply_markup=get_main_keyboard()
)
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False,
            "message_ids": [sent_message.message_id, message.message_id],
            "last_question_id": None
        }
        return
    user_data["current_session"] = words_to_review
    user_data["current_word_index"] = 0
    save_user_data(user_id, user_data)
    
    user_states[user_id] = {
        "translation_direction": "ru_to_it",
        "awaiting_answer": True,
        "message_ids": [message.message_id],
        "last_question_id": None
    }
    
    show_current_exercise(message.chat.id, user_id)



def show_current_exercise(chat_id: int, user_id: int):
    logger.debug(f"Showing exercise for user {user_id}")
    
    try:
        state = user_states.get(user_id, {})
        # Удаляем предыдущие сообщения
        message_ids = state.get("message_ids", [])
        if state.get("last_question_id"):
            message_ids.append(state["last_question_id"])
            
        for msg_id in message_ids:
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception as e:
                logger.debug(f"Could not delete message {msg_id}: {e}")

        user_data = load_user_data(user_id)
        
        if not user_data["current_session"]:
            sent_message = bot.send_message(chat_id, "❌ Нет активной сессии", reply_markup=get_main_keyboard())
            user_states[user_id] = {
                "translation_direction": state.get("translation_direction", "ru_to_it"),
                "awaiting_answer": False,
                "message_ids": [sent_message.message_id],
                "last_question_id": None,
                "current_example": None,
                "retry_message_id": None
            }
            return
        
        current_word = user_data["current_session"][user_data["current_word_index"]]
        word_data = VOCABULARY["Буду изучать"].get(current_word["word"])
        example = random.choice(word_data["примеры"])
        
        translation_direction = state.get("translation_direction", "ru_to_it")
        question = example["русский"] if translation_direction == "ru_to_it" else example["итальянский"]
        direction_text = "итальянский" if translation_direction == "ru_to_it" else "русский"
        
        progress_bar = "🟢" * current_word["correct_answers"] + "⚪️" * (CORRECT_FOR_LEARNED - current_word["correct_answers"])
        message_text = (
            f"*{current_word['word']} - {current_word['translation']}*\n\n"
            f"Переведите на {direction_text}:\n"
            f"*{question}*\n\n"
            f"Прогресс изучения: {progress_bar}\n"
            f"_Слово {user_data['current_word_index'] + 1} из {len(user_data['current_session'])}_"
        )
        
        sent_message = bot.send_message(
            chat_id, 
            message_text, 
            parse_mode='Markdown', 
            reply_markup=get_exercise_keyboard()
        )
        
        user_states[user_id] = {
            "translation_direction": translation_direction,
            "awaiting_answer": True,
            "current_example": example,
            "last_question_id": sent_message.message_id,
            "message_ids": [sent_message.message_id],
            "retry_message_id": None
        }
        
        logger.debug(f"Exercise shown: {current_word['word']}")
        
    except Exception as e:
        logger.error(f"Error showing exercise: {e}")
        sent_message = bot.send_message(
            chat_id,
            "❌ Произошла ошибка при показе упражнения",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False,
            "message_ids": [sent_message.message_id],
            "last_question_id": None,
            "current_example": None,
            "retry_message_id": None
        }
        
          
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
    current_time = get_now()
    
    # Статистика по словам
    active_words = user_data["active_words"]
    new_words = sum(1 for w in active_words if w["correct_answers"] == 0)
    learning_words = sum(1 for w in active_words if 0 < w["correct_answers"] < CORRECT_FOR_LEARNED)
    learned_words = len(user_data["learned_words"])
    
    # Слова для повторения
    words_to_review = []
    upcoming = []
    for word in active_words:
        review_time = parse_time(word["next_review"])
        if review_time <= current_time:
            words_to_review.append(word)
        else:
            time_diff = review_time - current_time
            hours = int(time_diff.total_seconds() // 3600)
            upcoming.append((word, hours))
    
    stats_text = [
        "📊 *Общая статистика:*\n",
        f"📚 Активные слова: {len(active_words)}",
        f"🆕 Новые слова (0 ответов): {new_words}",
        f"📝 В процессе (1-7 ответов): {learning_words}",
        f"✅ Изучено (8+ ответов): {learned_words}",
        f"\nВсего слов в словаре: {len(VOCABULARY['Буду изучать'])}\n"
    ]
    
    # Добавляем информацию о словах для повторения
    if words_to_review:
        stats_text.append("\n🔔 *Готово к повторению:*")
        for word in words_to_review:
            stats_text.append(f"• {word['word']} - {word['translation']}")
    else:
        stats_text.append("\n✅ Нет слов для повторения прямо сейчас")
    
    if upcoming:
        stats_text.append("\n⏰ *Предстоящие повторения:*")
        upcoming.sort(key=lambda x: x[1])
        for word, hours in upcoming:
            if hours < 24:
                stats_text.append(f"• {word['word']} - через {hours}ч")
            else:
                days = hours // 24
                remaining_hours = hours % 24
                stats_text.append(f"• {word['word']} - через {days}д {remaining_hours}ч")
    
    sent_message = bot.reply_to(message, "\n".join(stats_text), 
                               parse_mode='Markdown', 
                               reply_markup=get_main_keyboard())
    
    # Сохраняем ID сообщения для последующего удаления
    state = user_states.get(user_id, {})
    state["message_ids"] = [sent_message.message_id, message.message_id]
    user_states[user_id] = state
    

@bot.message_handler(func=lambda message: message.text == "🔀 Сменить направление")
def switch_translation_direction(message):
    logger.debug("Direction switch requested")
    user_id = message.from_user.id
    state = user_states.get(user_id, {"translation_direction": "ru_to_en"})
    new_direction = "en_to_ru" if state.get("translation_direction") == "ru_to_en" else "ru_to_en"
    
    direction_text = "английский → русский" if new_direction == "en_to_ru" else "русский → английский"
    sent_message = bot.reply_to(message, f"🔄 Направление перевода изменено на:\n*{direction_text}*", 
                parse_mode='Markdown')
    
    # Сохраняем ID сообщений для последующего удаления
    message_ids = state.get("message_ids", [])
    message_ids.extend([message.message_id, sent_message.message_id])
    
    user_states[user_id] = {
        "translation_direction": new_direction,
        "awaiting_answer": state.get("awaiting_answer", True),
        "current_example": state.get("current_example"),
        "last_question_id": state.get("last_question_id"),
        "message_ids": message_ids  # Сохраняем обновленный список ID
    }
    
    # Показываем новое задание
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def show_help(message):
    help_text = [
        "*📋 Доступные команды:*\n",
        "🎯 *Начать повторение* - изучение слов",
        "🔄 *Сменить направление* - изменить направление перевода",
        "📊 *Статистика* - прогресс обучения\n",
        "*Во время занятия:*",
        "🎤 Вы можете отвечать голосовыми сообщениями",
        "💡 Подсказка - показать первые буквы",
        "⏩ Пропустить - пропустить слово",
        "🏁 Завершить занятие - закончить сессию"
    ]
    sent_message = bot.reply_to(message, "\n".join(help_text), 
                               parse_mode='Markdown', 
                               reply_markup=get_main_keyboard())
    
    # Сохраняем ID сообщений
    state = user_states.get(user_id, {})
    state["message_ids"] = [sent_message.message_id, message.message_id]
    user_states[user_id] = state

@bot.message_handler(func=lambda message: message.text == "💡 Подсказка")
def show_hint(message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {})
    
    if not state.get("awaiting_answer") or not state.get("current_example"):
        return
        
    example = state["current_example"]
    answer = example["итальянский"] if state["translation_direction"] == "ru_to_it" else example["русский"]
    hint = ' '.join(word[0] + '_' * (len(word)-1) for word in answer.split())
    
    sent_message = bot.reply_to(message, f"💡 Подсказка:\n{hint}", 
                               reply_markup=get_exercise_keyboard())
    
    # Добавляем ID сообщений к существующим
    message_ids = state.get("message_ids", [])
    message_ids.extend([message.message_id, sent_message.message_id])
    state["message_ids"] = message_ids
    user_states[user_id] = state

@bot.message_handler(func=lambda message: message.text == "🏁 Завершить занятие")
def end_session(message):
    user_id = message.from_user.id
    user_data = load_user_data(user_id)
    user_data["current_session"] = []
    user_data["current_word_index"] = 0
    save_user_data(user_id, user_data)
    
    sent_message = bot.reply_to(message, "Занятие завершено!", 
                               reply_markup=get_main_keyboard())
    
    # Сохраняем ID сообщений
    state = user_states.get(user_id, {})
    state["message_ids"] = [sent_message.message_id, message.message_id]
    user_states[user_id] = state


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
    user_id = message.from_user.id
    logger.debug(f"Next exercise requested by user {user_id}")
    
    try:
        # Удаляем все предыдущие сообщения
        state = user_states.get(user_id, {})
        message_ids = state.get("message_ids", []) + [message.message_id]
        
        for msg_id in message_ids:
            try:
                bot.delete_message(message.chat.id, msg_id)
            except Exception as e:
                logger.debug(f"Could not delete message {msg_id}: {e}")

        user_data = load_user_data(user_id)
        if not user_data.get("current_session"):
            sent_message = bot.send_message(
                message.chat.id,
                "❌ Нет активной сессии. Начните новое занятие.",
                reply_markup=get_main_keyboard()
            )
            user_states[user_id] = {
                "translation_direction": state.get("translation_direction", "ru_to_it"),
                "awaiting_answer": False,
                "message_ids": [sent_message.message_id],
                "last_question_id": None,
                "current_example": None
            }
            return
            
        current_index = user_data.get("current_word_index", 0)
        if current_index >= len(user_data["current_session"]) - 1:
            user_data["current_session"] = []
            user_data["current_word_index"] = 0
            save_user_data(user_id, user_data)
            
            sent_message = bot.send_message(
                message.chat.id,
                "✅ Все задания выполнены!\nСледующие слова будут доступны, когда подойдёт время их повторения.",
                reply_markup=get_main_keyboard()
            )
            user_states[user_id] = {
                "translation_direction": state.get("translation_direction", "ru_to_it"),
                "awaiting_answer": False,
                "message_ids": [sent_message.message_id],
                "last_question_id": None,
                "current_example": None
            }
            return
        
        user_data["current_word_index"] = current_index + 1
        save_user_data(user_id, user_data)
        show_current_exercise(message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Error in next_exercise: {e}", exc_info=True)
        sent_message = bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка. Попробуйте начать заново.",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = {
            "translation_direction": state.get("translation_direction", "ru_to_it"),
            "awaiting_answer": False,
            "message_ids": [sent_message.message_id],
            "last_question_id": None,
            "current_example": None
        }
        
               
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
            "current_example": None,
            "last_question_id": None
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
        
        # Удаляем сообщение с кнопкой "Повторить"
        if message.message_id:
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception as e:
                logger.debug(f"Could not delete retry button message: {e}")
                
        # Удаляем предыдущее сообщение с ошибкой
        if state.get("retry_message_id"):
            try:
                bot.delete_message(message.chat.id, state["retry_message_id"])
            except Exception as e:
                logger.debug(f"Could not delete retry message: {e}")
        
        state["awaiting_answer"] = True
        state["retry_message_id"] = None
        user_states[user_id] = state
        
        show_current_exercise(message.chat.id, user_id)
    except Exception as e:
        logger.error(f"Error in retry: {e}")
        sent_message = bot.reply_to(
            message,
            "❌ Произошла ошибка. Начните заново.",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False,
            "message_ids": [sent_message.message_id],
            "last_question_id": None,
            "retry_message_id": None
        }
@bot.message_handler(func=lambda message: True)
def handle_answer(message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {})
    
    # Проверяем, не является ли сообщение командой смены направления
    if message.text == "🔀 Сменить направление":
        switch_translation_direction(message)
        return
        
    if not state.get("awaiting_answer"):
        return

    try:
        # Собираем все ID сообщений для удаления
        message_ids = state.get("message_ids", []) + [message.message_id]
        if state.get("last_question_id"):
            message_ids.append(state["last_question_id"])

        # Удаляем предыдущие сообщения
        for msg_id in message_ids:
            try:
                bot.delete_message(message.chat.id, msg_id)
            except Exception as e:
                logger.debug(f"Could not delete message {msg_id}: {e}")

        # Удаляем сообщение с кнопкой "Повторить" если оно есть
        if state.get("retry_message_id"):
            try:
                bot.delete_message(message.chat.id, state["retry_message_id"])
            except Exception as e:
                logger.debug(f"Could not delete retry message: {e}")

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

        # Обновляем прогресс слова
        current_word_found = False
        for i, word in enumerate(user_data["active_words"]):
            if word["word"] == current_word["word"]:
                current_word_found = True
                previous_correct = word["correct_answers"]
                updated_word = update_word_progress(word, is_correct)
                
                if is_correct and previous_correct < CORRECT_FOR_NEW_WORD and updated_word["correct_answers"] >= CORRECT_FOR_NEW_WORD:
                    if user_data["remaining_words"]:
                        new_word = random.choice(user_data["remaining_words"])
                        user_data["remaining_words"].remove(new_word)
                        word_data = VOCABULARY["Буду изучать"][new_word]
                        new_word_data = create_word_data(new_word, word_data["перевод"])
                        user_data["active_words"].append(new_word_data)
                        logger.info(f"Added new word '{new_word}' after '{word['word']}' reached {CORRECT_FOR_NEW_WORD} correct answers")

                if updated_word["correct_answers"] >= CORRECT_FOR_LEARNED:
                    logger.info(f"Word '{updated_word['word']}' learned, moving to learned words")
                    user_data["learned_words"].append(updated_word)
                    user_data["active_words"].pop(i)
                    user_data["current_session"] = [w for w in user_data["current_session"] 
                                                  if w["word"] != updated_word["word"]]
                else:
                    user_data["active_words"][i] = updated_word
                    current_word.update(updated_word)
                break

        if not current_word_found:
            logger.error(f"Word '{current_word['word']}' not found in active words")
            return

        save_user_data(user_id, user_data)

        progress_bar = "🟢" * updated_word["correct_answers"] + "⚪️" * (CORRECT_FOR_LEARNED - updated_word["correct_answers"])
        
        if is_correct:
            response = [
                "✅ *Правильно!*\n",
                f"Ваш ответ: _{message.text}_",
                f"Прогресс: {progress_bar}"
            ]
            
            if previous_correct < CORRECT_FOR_NEW_WORD and updated_word["correct_answers"] >= CORRECT_FOR_NEW_WORD:
                response.append("\n🎉 Вы достигли 3 правильных ответов!")
                if user_data["remaining_words"]:
                    response.append("Добавлено новое слово для изучения!")
            
            sent_message = bot.send_message(
                message.chat.id,
                "\n".join(response),
                parse_mode='Markdown',
                reply_markup=get_next_keyboard()
            )
            
            user_states[user_id] = {
                "translation_direction": state["translation_direction"],
                "awaiting_answer": False,
                # "message_ids": [sent_message.message_id],
                "message_ids": [],
                "last_question_id": None,
                "current_example": example  # Сохраняем пример для прослушивания
            }
        else:
            response = [
                "❌ *Ошибка!*\n",
                "Ваш ответ с исправлениями:",
                f"{highlight_differences(message.text, correct_answer)}\n",
                f"Правильный ответ: *{correct_answer}*",
                f"Прогресс: {progress_bar}"
            ]
            sent_message = bot.send_message(
                message.chat.id,
                "\n".join(response),
                parse_mode='Markdown',
                reply_markup=get_retry_keyboard()
            )
            
            user_states[user_id] = {
                "translation_direction": state["translation_direction"],
                "awaiting_answer": True,
                "current_example": example,
                "message_ids": [sent_message.message_id],
                "last_question_id": state.get("last_question_id"),
                "retry_message_id": sent_message.message_id
            }

    except Exception as e:
        logger.error(f"Error in handle_answer: {e}", exc_info=True)
        sent_message = bot.reply_to(
            message,
            "❌ Произошла ошибка. Попробуйте начать заново.",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = {
            "translation_direction": "ru_to_it",
            "awaiting_answer": False,
            "message_ids": [sent_message.message_id],
            "last_question_id": None,
            "current_example": None,
            "retry_message_id": None
        }
        
 
def check_notifications():
    while True:
        try:
            current_time = get_now()
            for filename in os.listdir('user_data'):
                try:
                    user_id = int(filename.split('_')[1].split('.')[0])
                    user_data = load_user_data(user_id)
                    
                    # Проверяем время последнего взаимодействия
                    last_activity = parse_time(user_data.get("last_update", ""))
                    inactive_time = (current_time - last_activity).total_seconds() / 3600  # в часах
                    
                    # Если пользователь был активен в последние 2 часа, пропускаем напоминание
                    if inactive_time < 2:
                        continue
                    
                    words_to_review = [
                        word for word in user_data["active_words"]
                        if parse_time(word["next_review"]) <= current_time
                    ]
                    
                    if words_to_review:
                        # Удаляем предыдущие напоминания
                        state = user_states.get(user_id, {})
                        notification_ids = state.get("notification_ids", [])
                        for msg_id in notification_ids:
                            try:
                                bot.delete_message(user_id, msg_id)
                            except:
                                pass
                                
                        text = (
                            "🔔 Пора повторить слова!\n\n"
                            f"Готово к повторению: {len(words_to_review)} слов\n\n"
                        )
                        text += "\n".join(f"• {w['word']} - {w['translation']}" 
                                        for w in words_to_review[:3])
                        sent_message = bot.send_message(user_id, text, reply_markup=get_main_keyboard())
                        
                        # Сохраняем ID нового напоминания
                        state["notification_ids"] = [sent_message.message_id]
                        user_states[user_id] = state
                        
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
    while True:
        try:
            logger.info("=== Starting Bot ===")
            logger.info(f"Vocabulary size: {len(VOCABULARY['Буду изучать'])} words")
            
            bot.delete_webhook()
            bot.get_updates(offset=-1)
            
            # Запускаем уведомления
            notifications = threading.Thread(target=check_notifications, daemon=True)
            notifications.start()
            logger.info("Notification thread started")
            
            bot.infinity_polling(
                timeout=10, 
                long_polling_timeout=20,
                interval=1,
                allowed_updates=None
            )
        except requests.exceptions.ReadTimeout as e:
            logger.warning(f"Timeout error: {e}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(10)

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
       
   
   
   