# review_scheduler.py

import json
from datetime import datetime, timedelta

class ReviewScheduler:
    def __init__(self, vocabulary_manager):
        self.vocabulary_manager = vocabulary_manager
        # Интервалы повторений по схеме Эббингауза (в минутах)
        self.intervals = [
            0,            # сразу после изучения
            20,          # через 20 минут
            60 * 8,      # через 8 часов
            60 * 24,     # через 24 часа
            60 * 24 * 5, # через 5 дней
            60 * 24 * 25 # через 25 дней
        ]
        
        self.reviews_file = 'review_history.json'
        self.history = {
            "reviews": {},      # История повторений по словам
            "statistics": {     # Общая статистика
                "total_reviews": 0,
                "successful_reviews": 0,
                "last_review": None,
                "current_streak": 0,
                "best_streak": 0
            }
        }
        self._load_history()

    def _load_history(self):
        """Загрузка истории повторений"""
        try:
            with open(self.reviews_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                self.history.update(loaded_data)
        except (FileNotFoundError, json.JSONDecodeError):
            self._save_history()

    def _save_history(self):
        """Сохранение истории повторений"""
        try:
            with open(self.reviews_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения истории: {e}")

    def get_current_reviews(self):
        """Получение слов, которые нужно повторить прямо сейчас"""
        current_time = datetime.now()
        current_reviews = []
        
        for word, data in self.history.get("reviews", {}).items():
            if data.get("next_review"):
                next_review = datetime.fromisoformat(data["next_review"])
                # Добавляем 5-минутный буфер для группировки близких повторений
                if next_review <= current_time + timedelta(minutes=5):
                    current_reviews.append({
                        "word": word,
                        "scheduled_time": next_review,
                        "stage": data.get("current_stage", 0)
                    })
        
        return sorted(current_reviews, key=lambda x: x["scheduled_time"])

    def get_next_session_info(self):
        """Получение информации о следующей сессии повторения"""
        current_time = datetime.now()
        next_session = None
        words_in_session = []
        
        for word, data in self.history.get("reviews", {}).items():
            if data.get("next_review"):
                next_review = datetime.fromisoformat(data["next_review"])
                if next_review > current_time:
                    if next_session is None or next_review < next_session:
                        next_session = next_review
                        words_in_session = [(word, next_review)]
                    elif next_review - next_session < timedelta(minutes=5):
                        words_in_session.append((word, next_review))
        
        if next_session:
            return {
                "time": next_session,
                "words": [word for word, _ in words_in_session],
                "minutes_until": (next_session - current_time).total_seconds() / 60
            }
        return None

    def should_start_session(self):
        """Проверка, нужно ли начинать сессию повторения"""
        current_reviews = self.get_current_reviews()
        return len(current_reviews) > 0

    def mark_review_complete(self, word, success):
        """Отметка о выполнении повторения"""
        if not self.history.get("reviews"):
            self.history["reviews"] = {}
            
        if word not in self.history["reviews"]:
            self.history["reviews"][word] = {
                "successful_reviews": 0,
                "total_reviews": 0,
                "current_stage": 0,
                "next_review": None,
                "review_history": []
            }
        
        word_data = self.history["reviews"][word]
        current_time = datetime.now()
        
        # Записываем результат повторения
        review_result = {
            "timestamp": current_time.isoformat(),
            "success": success,
            "stage": word_data.get("current_stage", 0)
        }
        word_data["review_history"].append(review_result)
        
        if success:
            word_data["successful_reviews"] += 1
            word_data["current_stage"] = min(word_data.get("current_stage", 0) + 1, 
                                           len(self.intervals) - 1)
            self.history["statistics"]["current_streak"] += 1
            if self.history["statistics"]["current_streak"] > self.history["statistics"]["best_streak"]:
                self.history["statistics"]["best_streak"] = self.history["statistics"]["current_streak"]
        else:
            word_data["current_stage"] = max(0, word_data.get("current_stage", 0) - 1)
            self.history["statistics"]["current_streak"] = 0
        
        # Планируем следующее повторение
        current_stage = word_data["current_stage"]
        next_interval = self.intervals[current_stage]
        next_review = current_time + timedelta(minutes=next_interval)
        
        word_data["next_review"] = next_review.isoformat()
        word_data["total_reviews"] += 1
        word_data["last_review"] = current_time.isoformat()
        
        # Обновляем общую статистику
        self.history["statistics"]["total_reviews"] += 1
        if success:
            self.history["statistics"]["successful_reviews"] += 1
        self.history["statistics"]["last_review"] = current_time.isoformat()
        
        # Если слово полностью изучено
        if word_data["successful_reviews"] >= len(self.intervals):
            self.vocabulary_manager.complete_word(word)
        
        self._save_history()

    def get_word_progress(self, word):
        """Получение прогресса изучения слова"""
        if not self.history.get("reviews"):
            self.history["reviews"] = {}
        
        if word not in self.history["reviews"]:
            return 0
        
        word_data = self.history["reviews"][word]
        successful_reviews = word_data.get("successful_reviews", 0)
        total_needed = len(self.intervals)
        return min(100, (successful_reviews / total_needed) * 100)

    def get_statistics(self):
        """Получение общей статистики обучения"""
        stats = self.history["statistics"].copy()
        
        # Добавляем дополнительную статистику
        total_words = len(self.history.get("reviews", {}))
        completed_words = sum(1 for data in self.history.get("reviews", {}).values() 
                            if data.get("successful_reviews", 0) >= len(self.intervals))
        
        stats.update({
            "total_words": total_words,
            "completed_words": completed_words,
            "completion_rate": (completed_words / total_words * 100) if total_words > 0 else 0,
            "success_rate": (stats["successful_reviews"] / stats["total_reviews"] * 100) 
                           if stats["total_reviews"] > 0 else 0
        })
        
        return stats