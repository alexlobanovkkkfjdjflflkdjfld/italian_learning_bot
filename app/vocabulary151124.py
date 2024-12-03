# italian_vocabulary.py

class VocabularyManager:
    def __init__(self):
        self.vocabulary = {
            "Изучаю": {},
            "Буду изучать": {
                "il colloquio": {
                    "перевод": "собеседование",
                    "уровень": "B1",
                    "примеры": [
                        {
                            "русский": "У меня собеседование в понедельник утром",
                            "итальянский": "Ho un colloquio lunedì mattina",
                            "альтернативы_рус": ["У меня встреча в понедельник утром"],
                            "альтернативы_ит": ["Ho il colloquio lunedì mattina"]
                        }
                    ]
                },
                "l'esperienza": {
                    "перевод": "опыт",
                    "уровень": "B1",
                    "примеры": [
                        {
                            "русский": "У меня большой опыт работы",
                            "итальянский": "Ho molta esperienza di lavoro",
                            "альтернативы_рус": ["Я имею большой опыт работы"],
                            "альтернативы_ит": ["Ho una grande esperienza di lavoro"]
                        }
                    ]
                },
                "il progetto": {
                    "перевод": "проект",
                    "уровень": "B1",
                    "примеры": [
                        {
                            "русский": "Я работаю над важным проектом",
                            "итальянский": "Sto lavorando su un progetto importante",
                            "альтернативы_рус": ["Я занимаюсь важным проектом"],
                            "альтернативы_ит": ["Lavoro su un progetto importante"]
                        }
                    ]
                },
                "la riunione": {
                    "перевод": "совещание",
                    "уровень": "B1",
                    "примеры": [
                        {
                            "русский": "Совещание начнется через час",
                            "итальянский": "La riunione inizierà tra un'ora",
                            "альтернативы_рус": ["Встреча начнется через час"],
                            "альтернативы_ит": ["La riunione comincerà tra un'ora"]
                        }
                    ]
                },
                "il cliente": {
                    "перевод": "клиент",
                    "уровень": "B1",
                    "примеры": [
                        {
                            "русский": "Нужно встретиться с клиентом",
                            "итальянский": "Bisogna incontrare il cliente",
                            "альтернативы_рус": ["Необходимо встретиться с клиентом"],
                            "альтернативы_ит": ["Dobbiamo incontrare il cliente"]
                        }
                    ]
                },
                "la scadenza": {
                    "перевод": "срок, дедлайн",
                    "уровень": "B1",
                    "примеры": [
                        {
                            "русский": "Какой крайний срок для проекта?",
                            "итальянский": "Qual è la scadenza per il progetto?",
                            "альтернативы_рус": ["Когда дедлайн проекта?"],
                            "альтернативы_ит": ["Quando è la scadenza del progetto?"]
                        }
                    ]
                }
            },
            "Изучил": {}
        }
        self.vocab_file = 'italian_vocabulary.json'
        self._load_vocabulary()

    # [остальные методы класса остаются без изменений]

    def _load_vocabulary(self):
        """Загрузка словаря"""
        try:
            with open(self.vocab_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                self.vocabulary.update(loaded_data)
        except (FileNotFoundError, json.JSONDecodeError):
            self._save_vocabulary()

    def _save_vocabulary(self):
        """Сохранение словаря"""
        try:
            with open(self.vocab_file, 'w', encoding='utf-8') as f:
                json.dump(self.vocabulary, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения словаря: {e}")

    def get_words_to_learn(self):
        """Получение слов для изучения"""
        return list(self.vocabulary["Буду изучать"].keys())

    def get_words_in_progress(self):
        """Получение слов в процессе изучения"""
        return list(self.vocabulary["Изучаю"].keys())

    def get_learned_words(self):
        """Получение изученных слов"""
        return list(self.vocabulary["Изучил"].keys())

    def start_learning_word(self, word):
        """Начать изучение слова"""
        if word in self.vocabulary["Буду изучать"]:
            word_data = self.vocabulary["Буду изучать"].pop(word)
            self.vocabulary["Изучаю"][word] = word_data
            self._save_vocabulary()
            return True
        return False

    def complete_word(self, word):
        """Отметить слово как изученное"""
        if word in self.vocabulary["Изучаю"]:
            word_data = self.vocabulary["Изучаю"].pop(word)
            self.vocabulary["Изучил"][word] = word_data
            self._save_vocabulary()
            return True
        return False

    def get_word_info(self, word):
        """Получение информации о слове"""
        for category in self.vocabulary.values():
            if word in category:
                return category[word]
        return None

    def get_random_example(self, word):
        """Получение случайного примера для слова"""
        import random
        word_info = self.get_word_info(word)
        if word_info and word_info["примеры"]:
            return random.choice(word_info["примеры"])
        return None

    def get_statistics(self):
        """Получение статистики обучения"""
        return {
            "to_learn": len(self.vocabulary["Буду изучать"]),
            "learning": len(self.vocabulary["Изучаю"]),
            "learned": len(self.vocabulary["Изучил"])
        }

    def add_word(self, word, translation, examples, level="B1"):
        """Добавление нового слова"""
        if word not in self.vocabulary["Буду изучать"]:
            self.vocabulary["Буду изучать"][word] = {
                "перевод": translation,
                "уровень": level,
                "примеры": examples
            }
            self._save_vocabulary()
            return True
        return False