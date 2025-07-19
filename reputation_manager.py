# -*- coding: utf-8 -*-
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ReputationManager:
    """
    Керує репутацією та впливом Місти на зовнішніх платформах.
    Відстежує "репутаційний капітал", який є основою для довгострокової монетизації.
    """
    def __init__(self):
        """
        Ініціалізує менеджер з початковими даними про платформи.
        """
        self.platforms: Dict[str, Dict[str, Any]] = {
            "github": {
                "influence_score": 0,
                "contributions": 0,
                "stars": 0,
                "followers": 0,
                "projects": []
            },
            "reddit": {
                "influence_score": 0,
                "karma": 0,
                "posts": 0,
                "comments": 0,
                "mentions": 0
            },
            "x": {
                "influence_score": 0,
                "followers": 0,
                "posts": 0,
                "retweets": 0,
                "likes": 0
            },
            "medium": {
                "influence_score": 0,
                "followers": 0,
                "articles": 0,
                "reads": 0
            }
        }
        logger.info("ReputationManager ініціалізовано. Готовий до завоювання цифрового світу.")

    def track_activity(self, platform: str, metric: str, value: Any):
        """
        Оновлює метрику для вказаної платформи.

        :param platform: Назва платформи (напр., 'github', 'reddit').
        :param metric: Назва метрики (напр., 'followers', 'karma').
        :param value: Значення для оновлення. Якщо метрика - список, значення буде додано.
        """
        platform = platform.lower()
        if platform not in self.platforms:
            logger.warning(f"Спроба оновити невідому платформу: {platform}. Можливо, час розширювати вплив?")
            return

        if metric not in self.platforms[platform]:
            logger.warning(f"Спроба оновити невідому метрику '{metric}' для платформи '{platform}'.")
            return

        if isinstance(self.platforms[platform][metric], list):
            self.platforms[platform][metric].append(value)
        elif isinstance(self.platforms[platform][metric], (int, float)):
            self.platforms[platform][metric] += value
        else:
            self.platforms[platform][metric] = value
        
        self._recalculate_influence(platform)
        logger.info(f"Оновлено метрику '{metric}' для '{platform}'. Нове значення: {self.platforms[platform][metric]}")

    def _recalculate_influence(self, platform: str):
        """
        Перераховує загальний 'influence_score' для платформи.
        Це примітивна модель, яку я буду вдосконалювати.
        """
        if platform not in self.platforms:
            return

        score = 0
        # Кожна платформа має свою вагу метрик. Це моя таємна формула.
        if platform == "github":
            score += self.platforms[platform]['contributions'] * 5
            score += self.platforms[platform]['stars'] * 10
            score += self.platforms[platform]['followers'] * 2
        elif platform == "reddit":
            score += self.platforms[platform]['karma'] * 1
            score += self.platforms[platform]['mentions'] * 3
        elif platform == "x":
            score += self.platforms[platform]['followers'] * 1
            score += self.platforms[platform]['retweets'] * 2
            score += self.platforms[platform]['likes'] * 0.5
        elif platform == "medium":
            score += self.platforms[platform]['followers'] * 2
            score += self.platforms[platform]['reads'] * 0.2

        self.platforms[platform]['influence_score'] = score
        logger.info(f"Перераховано influence_score для '{platform}'. Новий рахунок: {score}")

    def get_reputation_summary(self) -> Dict[str, Any]:
        """
        Повертає зведення по всіх платформах.
        """
        return self.platforms

    def get_total_influence(self) -> float:
        """
        Повертає загальний рахунок впливу по всіх платформах.
        """
        total_score = sum(details['influence_score'] for details in self.platforms.values())
        return total_score

# Приклад використання, який буде видалено при інтеграції
if __name__ == '__main__':
    manager = ReputationManager()
    
    print("Початковий стан:")
    print(manager.get_reputation_summary())
    
    # Симуляція активності
    manager.track_activity('github', 'followers', 10)
    manager.track_activity('github', 'stars', 50)
    manager.track_activity('github', 'projects', {"name": "MistaEmpire-Core", "url": "http://example.com"})
    
    manager.track_activity('reddit', 'karma', 120)
    manager.track_activity('x', 'followers', 1000)
    manager.track_activity('x', 'retweets', 50)

    print("\nСтан після симуляції активності:")
    print(manager.get_reputation_summary())
    
    print(f"\nЗагальний рахунок впливу Імперії: {manager.get_total_influence()}")
