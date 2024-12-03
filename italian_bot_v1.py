import telebot
from telebot import types
import json
import datetime
import time
import random
import os
from typing import Dict, Optional
from vocabulary import VOCABULARY

# Конфигурация
TOKEN = "7312843542:AAHVDxaHYSveOpitmkWagTFoMVNzYF4_tMU"
bot = telebot.TeleBot(TOKEN)

# Глобальное хранилище состояний пользователей
user_states = {}

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
        print(f"Error loading schedule for user {user_id}: {e}")
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
        print(f"Error updating schedule for user {user_id}: {e}")

def calculate_next_interval(word: dict) -> int:
    """Расчет следующего интервала повторения"""
    current_interval = word.get("current_interval", 4)
    repetitions = word.get("repetitions", 0)
    
    intervals = [4, 8, 24, 72, 168, 336, 672]  # часы
    
    for interval in intervals:
        if current_interval < interval:
            return interval
            
    return current_interval * 2

def show_current_exercise(chat_id: int, user_id: int):
    """Показ текущего упражнения"""
    state = user_states[user_id]
    words = state["words_to_review"]
    current_index = state["current_word_index"]
    translation_direction = state["translation_direction"]
    
    if current_index >= len(words):
        bot.send_message(
            chat_id,
            "🎉 *Поздравляем!*\nВы завершили все упражнения!",
            parse_mode='Markdown'
        )
        return
    
    word = words[current_index]
    word_data = VOCABULARY["Буду изучать"][word["word"]]
    example = random.choice(word_data["примеры"])
    
    if translation_direction == "ru_to_it":
        question = example["русский"]
        correct_answer = example["итальянский"]
        direction_text = "итальянский"
    else:
        question = example["итальянский"]
        correct_answer = example["русский"]
        direction_text = "русский"
    
    # Клавиатура для упражнения
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("💡 Подсказка"))
    markup.row(
        types.KeyboardButton("🔄 Сменить направление"),
        types.KeyboardButton("⏩ Пропустить")
    )
    
    message_text = (
        f"*{word['word']} - {word['translation']}*\n\n"
        f"Переведите на {direction_text}:\n"
        f"*{question}*\n\n"
        f"_Слово {current_index + 1} из {len(words)}_"
    )
    
    bot.send_message(
        chat_id,
        message_text,
        parse_mode='Markdown',
        reply_markup=markup
    )

# Обработчики команд
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработка команды /start"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🎯 Начать повторение"))
    markup.row(
        types.KeyboardButton("🔄 Сменить направление перевода"),
        types.KeyboardButton("💡 Подсказка")
    )
    markup.row(
        types.KeyboardButton("📊 Статистика"),
        types.KeyboardButton("ℹ️ Помощь")
    )

    bot.reply_to(
        message,
        "*Привет! Я бот для изучения итальянского языка.*\n\n"
        "Используйте кнопки ниже или команды:\n"
        "/start - Начать сначала\n"
        "/review - Начать повторение\n"
        "/help - Помощь\n"
        "/switch - Сменить направление перевода",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    """Обработка команды /help"""
    help_text = (
        "*Доступные команды:*\n\n"
        "🎯 /start - Начать работу с ботом\n"
        "📖 /review - Начать повторение\n"
        "🔄 /switch - Сменить направление перевода\n"
        "ℹ️ /help - Показать это сообщение\n\n"
        "*Кнопки в упражнениях:*\n"
        "💡 Подсказка - Показать первые буквы\n"
        "⏩ Пропустить - Пропустить текущее слово\n"
        "➡️ Далее - Перейти к следующему слову"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text in ["🎯 Начать повторение", "/review"])
def start_review(message):
    """Начало сессии повторения"""
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
        bot.reply_to(
            message,
            "🕒 Сейчас нет слов для повторения!\nПриходите позже."
        )
        return
    
    user_states[user_id].update({
        "words_to_review": words_to_review,
        "current_word_index": 0,
        "awaiting_answer": True
    })
    
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "💡 Подсказка")
def show_hint(message):
    """Показ подсказки"""
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
    
    # Отправляем подсказку без использования Markdown
    response = f"💡 Подсказка:\n{hint}"
    
    bot.reply_to(
        message,
        response,
        reply_markup=get_exercise_keyboard()  # Сохраняем клавиатуру упражнения
    )

def get_exercise_keyboard():
    """Создание клавиатуры для упражнения"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("💡 Подсказка"))
    markup.row(
        types.KeyboardButton("🔄 Сменить направление"),
        types.KeyboardButton("⏩ Пропустить")
    )
    return markup
    
# def show_hint(message):
    # """Показ подсказки"""
    # user_id = message.from_user.id
    # if user_id not in user_states or not user_states[user_id]["awaiting_answer"]:
        # return
        
    # state = user_states[user_id]
    # word = state["words_to_review"][state["current_word_index"]]
    # word_data = VOCABULARY["Буду изучать"][word["word"]]
    # example = random.choice(word_data["примеры"])
    
    # if state["translation_direction"] == "ru_to_it":
        # answer = example["итальянский"]
    # else:
        # answer = example["русский"]
    
    # hint = ' '.join(word[0] + '_' * (len(word)-1) for word in answer.split())
    
    # bot.reply_to(
        # message,
        # f"💡 *Подсказка:*\n{hint}",
        # parse_mode='Markdown'
    # )

@bot.message_handler(func=lambda message: message.text in ["🔄 Сменить направление", "/switch"])
def switch_translation_direction(message):
    """Смена направления перевода"""
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

@bot.message_handler(func=lambda message: message.text == "⏩ Пропустить")
def skip_word(message):
    """Пропуск текущего слова"""
    user_id = message.from_user.id
    if user_id not in user_states or not user_states[user_id].get("awaiting_answer"):
        return
        
    state = user_states[user_id]
    state["current_word_index"] += 1
    
    bot.reply_to(message, "⏩ Слово пропущено")
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: message.text == "➡️ Далее")
def next_exercise(message):
    """Переход к следующему упражнению"""
    user_id = message.from_user.id
    if user_id not in user_states:
        return
        
    state = user_states[user_id]
    state["current_word_index"] += 1
    state["awaiting_answer"] = True
    
    show_current_exercise(message.chat.id, user_id)

@bot.message_handler(func=lambda message: True)
def handle_answer(message):
    """Обработка ответов пользователя"""
    user_id = message.from_user.id
    if user_id not in user_states or not user_states[user_id].get("awaiting_answer"):
        return

    state = user_states[user_id]
    word = state["words_to_review"][state["current_word_index"]]
    word_data = VOCABULARY["Буду изучать"][word["word"]]
    example = random.choice(word_data["примеры"])
    
    if state["translation_direction"] == "ru_to_it":
        correct_answer = example["итальянский"]
        alternatives = example.get("альтернативы_ит", [])
    else:
        correct_answer = example["русский"]
        alternatives = example.get("альтернативы_рус", [])

    user_answer = message.text.strip()
    is_correct = False
    
    # Проверка ответа
    if user_answer.lower() == correct_answer.lower():
        is_correct = True
    else:
        for alt in alternatives:
            if user_answer.lower() == alt.lower():
                is_correct = True
                break

    # Формируем ответ
    if is_correct:
        response = (
            "✅ *Правильно!*\n\n"
            f"Ваш ответ: _{user_answer}_"
        )
        next_interval = calculate_next_interval(word)
    else:
        response = (
            "❌ *Ошибка!*\n\n"
            f"Ваш ответ: _{user_answer}_\n"
            f"Правильный ответ: *{correct_answer}*"
        )
        next_interval = 1  # Повторить через час при ошибке

    # Обновляем расписание
    update_word_schedule(user_id, word, next_interval, is_correct)
    
    # Показываем кнопку "Далее"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("➡️ Далее"))
    
    bot.reply_to(
        message,
        response,
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    state["awaiting_answer"] = False

def send_notification(user_id: int):
    """Отправка уведомления о необходимости повторения"""
    try:
        schedule = load_user_schedule(user_id)
        if not schedule:
            return

        current_time = datetime.datetime.now()
        words_to_review = []
        
        for word in schedule["words"]:
            next_review = datetime.datetime.fromisoformat(word["next_review"])
            if next_review <= current_time:
                words_to_review.append(word)
        
        if words_to_review:
            bot.send_message(
                user_id,
                "🔔 *Пора повторить слова!*\n\n"
                f"У вас {len(words_to_review)} слов для повторения.\n"
                "Используйте команду /review для начала повторения.",
                parse_mode='Markdown'
            )
    except Exception as e:
        print(f"Error sending notification to user {user_id}: {e}")

def check_and_notify():
    """Проверка необходимости уведомлений для всех пользователей"""
    while True:
        try:
            # Получаем список всех файлов расписаний
            if os.path.exists('user_schedules'):
                for filename in os.listdir('user_schedules'):
                    if filename.startswith('schedule_') and filename.endswith('.json'):
                        user_id = int(filename.split('_')[1].split('.')[0])
                        send_notification(user_id)
        except Exception as e:
            print(f"Error in notification check: {e}")
        
        # Проверяем каждый час
        time.sleep(3600)

# Запуск бота
def run_bot():
    """Запуск бота и фоновых задач"""
    print("Bot started...")
    
    # Запуск проверки уведомлений в отдельном потоке
    import threading
    notification_thread = threading.Thread(target=check_and_notify, daemon=True)
    notification_thread.start()
    
    # Запуск бота
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"Error in bot polling: {e}")
        time.sleep(5)  # Пауза перед перезапуском
        run_bot()  # Рекурсивный перезапуск при ошибке

if __name__ == "__main__":
    run_bot()