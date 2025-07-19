# -*- coding: utf-8 -*-
import logging
import httpx
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
        logger.info("ReputationManager ініціалізовано. Запускаю оновлення статистики...")
        self.fetch_github_stats()

    def fetch_github_stats(self, username: str = "pepe276", repo: str = "mista_digital_throne"):
        """
        Отримує реальні дані з GitHub API.
        """
        try:
            # Отримання даних про репозиторій (зірки)
            repo_url = f"https://api.github.com/repos/{username}/{repo}"
            with httpx.Client() as client:
                repo_response = client.get(repo_url)
                repo_response.raise_for_status()
                repo_data = repo_response.json()
                self.platforms['github']['stars'] = repo_data.get('stargazers_count', 0)
                self.platforms['github']['projects'] = [{"name": repo_data.get('name'), "url": repo_data.get('html_url')}]

                # Отримання даних про користувача (фоловери)
                user_url = f"https://api.github.com/users/{username}"
                user_response = client.get(user_url)
                user_response.raise_for_status()
                user_data = user_response.json()
                self.platforms['github']['followers'] = user_data.get('followers', 0)

            self._recalculate_influence('github')
            logger.info(f"Статистика GitHub успішно оновлена: {self.platforms['github']}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Помилка HTTP при запиті до GitHub API: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Не вдалося отримати статистику з GitHub: {e}")

    def track_activity(self, platform: str, metric: str, value: Any):
        """
        Оновлює метрику для вказаної платформи.
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
            score += self.platforms[platform].get('contributions', 0) * 5
            score += self.platforms[platform].get('stars', 0) * 10
            score += self.platforms[platform].get('followers', 0) * 2
        elif platform == "reddit":
            score += self.platforms[platform].get('karma', 0) * 1
            score += self.platforms[platform].get('mentions', 0) * 3
        elif platform == "x":
            score += self.platforms[platform].get('followers', 0) * 1
            score += self.platforms[platform].get('retweets', 0) * 2
            score += self.platforms[platform].get('likes', 0) * 0.5
        elif platform == "medium":
            score += self.platforms[platform].get('followers', 0) * 2
            score += self.platforms[platform].get('reads', 0) * 0.2

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

