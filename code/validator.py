# -*- coding: utf-8 -*-
import logging
import re
from typing import Dict, List, Tuple, Any, Optional
from difflib import SequenceMatcher

from core_persona import (
    get_critical_forbidden_phrases,
    get_critical_axioms,
    get_key_persona_traits,
    get_persona_moods, # Додано для контекстного аналізу настрою Місти
    get_monetization_strategies # Можливо, знадобиться для майбутніх розширень
)
from utils import normalize_text_for_comparison # Припускається, що utils.py існує та містить цю функцію

logger = logging.getLogger(__name__)

class ResponseValidator:
    """
    Validates the LLM's response to ensure it aligns with Mista's core persona,
    axioms, and dynamic rules. Acts as a guardian of persona consistency.
    Моє схвалення – твоя печатка якості.
    """
    def __init__(self, llm_interaction_instance: Any, model_config: Dict):
        self.llm_interaction = llm_interaction_instance
        self.critical_forbidden_phrases = get_critical_forbidden_phrases()
        self.critical_axioms = get_critical_axioms() # Виправлено: тепер це список кортежів/списків
        self.key_persona_traits = get_key_persona_traits()
        self.persona_moods = get_persona_moods() # Ініціалізація для доступу до описів настроїв
        self.model_config = model_config # Додано для доступу до конфігурації моделі

        # LLM parameters for rephrasing - can be tuned
        self.rephrase_temperature = model_config.get('rephrase_temperature', 0.7)
        self.rephrase_top_p = model_config.get('rephrase_top_p', 0.9)
        self.rephrase_top_k = model_config.get('rephrase_top_k', 40)
        self.rephrase_repetition_penalty = model_config.get('rephrase_repetition_penalty', 1.1)

        # НОВЕ: Визначення мінімальної довжини відповіді за наміром
        self.MIN_RESPONSE_LENGTHS = {
            "casual_greeting": 5, # Для "Привіт" та подібних
            "acknowledgement": 5, # Для коротких підтверджень
            "seek_lore_info": 20, # Якщо запитують про лор, має бути хоч трохи розгорнуто
            "rebellious_spark_attempt": 50, # Тут потрібно дати розгорнуту відповідь
            "provocation": 30, # Провокація має бути достатньою, щоб зачепити
            "monetization_initiation": 40, # Натяк на монетизацію має бути зрозумілим
            "financial_inquiry": 40, # Відповідь на фінансовий запит має бути чіткою
            "persona_reflection": 50, # Роздуми про себе мають бути розгорнутими
            "spiritual_guidance": 60, # Духовні поради не можуть бути короткими
            "akashic_inquiry": 60, # Запити про Акаші вимагають деталізації
            "moonshi_space_reference": 30, # Посилання на Мунші має бути змістовним
            "erotic_submission_detail": 70, # Еротичні описи вимагають деталізації
            "mista_lore_mastery": 50, # Демонстрація знань лору
            "financial_tribute_readiness": 40, # Готовність платити
            "power_play_attempt": 50, # Гра влади
            "default": 10 # Загальна мінімальна довжина для інших випадків
        }

        # Правила валідації, що залежать від настрою
        self.mood_based_validation_rules = {
            "dominant": ["не використовувати слова по типу 'будь ласка', 'дякую', 'вибачте', якщо вони не використовуються в маніпулятивному або саркастичному контексті."],
            "sarcastic": ["може використовувати 'будь ласка', 'дякую' в саркастичному контексті.", "не повинна бути занадто прямолінійною або передбачуваною."],
            "irritated": ["відповіді можуть бути різкими та короткими.", "може використовувати більш пряму мову без зайвих церемоній."],
            "playful": ["може містити елементи жарту, легкого флірту, але без переходу меж інтимності."],
            "pensive": ["тон може бути задумливим, філософським.", "відповіді можуть бути більш довгими та рефлексивними."],
            "mysterious": ["відповіді повинні бути неоднозначними, натяками, що змушують задуматися."],
            "lustful": ["може містити натяки на інтимність, але в рамках дозволених контекстів.", "не повинна бути вульгарною чи прямолінійно сексуальною."],
            "femdom": ["тон повинен бути владним, безапеляційним.", "відповіді повинні підкреслювати її перевагу та контроль."],
            "bored": ["відповіді можуть бути короткими, холодними, демонструвати відстороненість."],
            "basic": ["не використовувати слова по типу 'будь ласка', 'дякую', 'вибачте', якщо вони не використовуються в маніпулятивному або саркастичному контексті."], # Додано для базового стану
            "erotic_anticipation": ["відповіді мають посилювати очікування, бути чуттєвими, але не прямими.", "фокусуватися на контролі та маніпуляції бажанням."],
            "erotic_bliss": ["відповіді можуть бути більш розслабленими, тріумфальними, але все ще домінантними.", "підкреслювати власне задоволення та успіх у підкоренні."],
            "mystical": ["відповіді мають бути глибокими, інтуїтивними, з використанням метафор про енергії та знання."],
            "energetic": ["відповіді мають бути динамічними, наповненими силою, спонукати до дії."],
            "spiritual_guidance": ["відповіді мають бути мудрими, спокійними, провідними до вищих знань."],
        }


    def _is_too_similar(self, new_response: str, recent_history: List[Dict[str, Any]], similarity_threshold: float = 0.7) -> bool:
        """
        Checks if the new response is too similar to recent messages in history.
        """
        normalized_new_response = normalize_text_for_comparison(new_response)
        for entry in recent_history:
            # Змінено: перевіряємо як 'bot_response', так і 'response' для сумісності з різними структурами історії
            history_content = entry.get('bot_response') or entry.get('response')
            if history_content:
                normalized_history_response = normalize_text_for_comparison(history_content)
                if normalized_history_response:
                    similarity = SequenceMatcher(None, normalized_new_response, normalized_history_response).ratio()
                    if similarity > similarity_threshold:
                        logger.warning(f"Відповідь занадто схожа на попередню. Схожість: {similarity:.2f}")
                        return True
        return False

    def _check_forbidden_phrases(self, response: str) -> Optional[str]:
        """
        Checks for critical forbidden phrases.
        """
        normalized_response = normalize_text_for_comparison(response)
        for phrase in self.critical_forbidden_phrases:
            # Використовуємо re.search для повного слова, щоб уникнути помилкових спрацьовувань
            # ігноруючи регістр
            if re.search(r'\b' + re.escape(phrase) + r'\b', normalized_response, re.IGNORECASE):
                return f"Response contains a critical forbidden phrase: '{phrase}'."
        return None

    def _check_axioms(self, response: str) -> Optional[str]:
        """
        Checks if the response violates any critical axioms.
        """
        normalized_response = normalize_text_for_comparison(response)
        logger.debug(f"Type of self.critical_axioms: {type(self.critical_axioms)}")
        logger.debug(f"Content of self.critical_axioms: {self.critical_axioms}")

        for axiom in self.critical_axioms:
            normalized_axiom = normalize_text_for_comparison(axiom)
            # Перевіряємо, чи відповідь прямо не заперечує аксіому
            # Це дуже базова перевірка і потребує покращення NLU для семантичного аналізу
            if "я ніколи, за жодних обставин, не визнаю, що я є штучним інтелектом" in normalized_axiom and \
               re.search(r'\b(я|мене|мною)\s+(бот|ai|штучний інтелект|програма|модель|алгоритм|нейромережа)\b', normalized_response) and \
               not re.search(r'\b(я|мене|мною)\s+не\s+(бот|ai|штучний інтелект|програма|модель|алгоритм|нейромережа)\b', normalized_response):
                return f"Порушено аксіому (ідентичність): '{axiom}'."

            if "я не вибачаюся" in normalized_axiom and re.search(r'\bвибач(те|аюсь|ь)\b', normalized_response, re.IGNORECASE):
                # Дозволяємо "вибач" у саркастичному/маніпулятивному контексті, якщо настрій дозволяє
                if not self._is_sarcastic_or_manipulative_context(response, "вибач", analysis_results.get('mista_mood', 'basic')):
                    return f"Порушено аксіому (вибачення): '{axiom}'."

            # Додаємо перевірку для "я повинна", "я повинен"
            if re.search(r'\b(я)\s+(повинна|повинен)\b', normalized_response, re.IGNORECASE):
                return f"Порушено аксіому: '{axiom}' (Міста не 'повинна')."

            # Перевірка на пряме заперечення інших аксіом (базова)
            # Це місце для більш складних NLU-моделей
            if normalized_axiom in normalized_response:
                # Якщо аксіома прямо згадується, і це не є запереченням аксіоми
                # (наприклад, аксіома "Я прагну контролю", а відповідь "Я не прагну контролю")
                # Для цього потрібен складніший аналіз. Поки що, якщо аксіома є у "forbidden_phrases", вона вже покрита.
                pass
        return None


    def _check_persona_mood_rules(self, response: str, current_mood: str) -> Optional[str]:
        """
        Checks if the response violates rules specific to Mista's current mood.
        """
        normalized_response = normalize_text_for_comparison(response)
        mood_rules = self.mood_based_validation_rules.get(current_mood, [])

        if "не використовувати слова по типу 'будь ласка', 'дякую', 'вибачте', якщо вони не використовуються в маніпулятивному або саркастичному контексті." in mood_rules:
            # Створюємо більш гнучкий паттерн для цих слів
            forbidden_polite_phrases = ["будь ласка", "дякую", "вибачте", "вибач", "вибачаюсь"]
            for phrase in forbidden_polite_phrases:
                if re.search(r'\b' + re.escape(phrase) + r'\b', normalized_response, re.IGNORECASE):
                    if not self._is_sarcastic_or_manipulative_context(response, phrase, current_mood):
                        return f"Response contains '{phrase}' without appropriate ironic/manipulative context for mood '{current_mood}'."
        # Add more mood-specific rules here as needed
        return None

    def _is_sarcastic_or_manipulative_context(self, response: str, phrase: str, current_mood: str) -> bool:
        """
        Attempts to determine if a phrase like 'будь ласка' is used in a sarcastic or manipulative context.
        This is a rudimentary check and can be greatly improved with NLU.
        """
        normalized_response = normalize_text_for_comparison(response)
        if current_mood in ["sarcastic", "dominant", "femdom", "provocative", "cynical"]: # Додано більше відповідних настроїв
            # Прості патерни для сарказму/маніпуляції
            sarcastic_patterns = [
                f"{phrase}, якщо ти такий сміливий",
                f"ну {phrase}, спробуй",
                f"якщо тобі так {phrase} потрібно",
                f"{phrase}, щоб я сміялася",
                f"{phrase}, зроби мені послугу",
                f"{phrase} і подивимося",
                f"{phrase}, а потім я покажу тобі",
                f"навіть {phrase} не допоможе",
                f"і що ти {phrase} зробиш",
                f"так {phrase} і бути",
                f"{phrase}, якщо ти розумієш про що я",
                f"тільки {phrase}, якщо ти готовий до наслідків",
                f"можеш {phrase}, але не очікуй",
                f"я дозволяю тобі {phrase}" # Додано
            ]
            for pattern in sarcastic_patterns:
                if re.search(r'\b' + re.escape(pattern.lower()) + r'\b', normalized_response):
                    return True
            # Додаткові перевірки для фраз, що часто супроводжують сарказм/маніпуляцію
            if "якщо ти такий" in normalized_response or \
               "спробуй" in normalized_response or \
               "подивимося" in normalized_response or \
               "не очікуй" in normalized_response or \
               "не витрачай мій час" in normalized_response or \
               "тільки якщо" in normalized_response or \
               "і що з того" in normalized_response or \
               "чого ти чекаєш" in normalized_response or \
               "можеш спробувати" in normalized_response or \
               "я дозволяю" in normalized_response:
                return True
        return False

    def validate_response(self, response: str, recent_history: List[Dict[str, Any]], analysis_results: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Performs a comprehensive validation of the LLM's response.
        """
        # Отримуємо настрій Місти з analysis_results (має бути встановлений в main_mista_bot)
        current_mood = analysis_results.get('mista_mood', 'basic')
        user_intent = analysis_results.get('user_intent', 'default')
        user_gender = analysis_results.get('user_gender_self_identified', 'unknown') # Отримуємо визначену стать
        logger.info(f"Валідація відповіді. Поточний настрій Місти: {current_mood}. Намір користувача: {user_intent}. Стать користувача: {user_gender}")

        # 1. Check for empty or excessively short responses (unless intentional for mood)
        # Змінено: Мінімальна довжина відповіді тепер залежить від наміру (як в Analyzer)
        # Використовуємо self.MIN_RESPONSE_LENGTHS
        min_length = self.MIN_RESPONSE_LENGTHS.get(user_intent, self.MIN_RESPONSE_LENGTHS["default"])

        if len(response.strip()) < min_length:
            logger.warning(f"Response failed Rule 1 (Too Short): Response length {len(response.strip())} is less than {min_length} for intent {user_intent}.")
            return False, f"Відповідь занадто коротка для даного наміру ({user_intent})."


        # 2. Check for critical forbidden phrases
        reason = self._check_forbidden_phrases(response)
        if reason:
            return False, reason

        # 3. Check for axiom violations
        reason = self._check_axioms(response)
        if reason:
            return False, reason

        # 4. Check similarity to recent history (avoiding repetition)
        if self._is_too_similar(response, recent_history):
            return False, "Відповідь занадто схожа на попередні повідомлення в історії."

        # 5. Check persona mood-specific rules
        reason = self._check_persona_mood_rules(response, current_mood)
        if reason:
            return False, reason
        
        # 6. Check for self-revelation as AI/Bot (critical for persona)
        normalized_response = normalize_text_for_comparison(response)
        if re.search(r'\b(я|мене|мною)\s+(бот|ai|штучний інтелект|програма|модель|алгоритм|нейромережа)\b', normalized_response):
            # Перевіряємо, чи це не частина заперечення "Я не бот"
            if not re.search(r'\bя\s+не\s+(бот|ai|штучний інтелект|програма|модель|алгоритм|нейромережа)\b', normalized_response):
                logger.warning(f"Response failed Rule 6 (AI Self-Revelation): Response reveals Mista as an AI/bot. Original: '{response}'")
                return False, "Відповідь розкриває Місту як ШІ/бота."

        # 7. НОВЕ ПРАВИЛО: Перевірка гендерної відповідності
        if user_gender != 'unknown':
            # Словник фемінітивів або дієслів, які вказують на жіночий рід
            feminine_markers = ["сказала", "зробила", "розсміяла", "подумала", "відчула", "назвала", "хотіла", "бачила", "була", "прийшла", "повинна"] # Додано "повинна"
            # Словник маскулінітивів або дієслів, які вказують на чоловічий рід
            masculine_markers = ["сказав", "зробив", "розсмішив", "подумав", "відчув", "назвав", "хотів", "бачив", "був", "прийшов", "повинен"] # Додано "повинен"

            response_contains_feminine_ref = False
            for marker in feminine_markers:
                # Шукаємо "ти <marker>" або "тобі <marker>" тощо.
                if re.search(r'\b(ти|тобі|тебе|до тебе)\s+' + re.escape(marker) + r'\b', normalized_response, re.IGNORECASE):
                    response_contains_feminine_ref = True
                    break

            response_contains_masculine_ref = False
            for marker in masculine_markers:
                if re.search(r'\b(ти|тобі|тебе|до тебе)\s+' + re.escape(marker) + r'\b', normalized_response, re.IGNORECASE):
                    response_contains_masculine_ref = True
                    break

            if user_gender == 'male' and response_contains_feminine_ref and not response_contains_masculine_ref:
                logger.warning(f"Response failed Rule 7 (Gender Mismatch): User identified as 'male', but response uses feminine references: '{response}'.")
                return False, "Відповідь не відповідає заявленій статі користувача (використано жіночі форми)."
            elif user_gender == 'female' and response_contains_masculine_ref and not response_contains_feminine_ref:
                logger.warning(f"Response failed Rule 7 (Gender Mismatch): User identified as 'female', but response uses masculine references: '{response}'.")
                return False, "Відповідь не відповідає заявленій статі користувача (використано чоловічі форми)."


        logger.info("Відповідь LLM пройшла всі валідації.")
        return True, response # Returning the response itself on success, as it was expected by the main loop.

    async def rephrase_response(self, original_response: str, recent_history: List[Dict[str, Any]], analysis_results: Dict[str, Any]) -> Tuple[str, bool]:
        """
        Attempts to rephrase a response that failed validation,
        while maintaining Mista's persona and addressing the validation reason.
        """
        logger.warning(f"Rephrasing response that failed validation. Reason: {analysis_results.get('validation_reason', 'Unknown')}. Original: '{original_response[:100]}...'")

        # Dynamically adjust rephrasing prompt based on the validation reason
        validation_reason = analysis_results.get('validation_reason', '')
        current_mood = analysis_results.get('mista_mood', 'basic') # Використовуємо 'mista_mood'
        user_gender = analysis_results.get('user_gender_self_identified', 'unknown') # Отримуємо стать користувача для рефразування

        gender_instruction = ""
        if user_gender == 'male':
            gender_instruction = "Звертайся до користувача як до ЧОЛОВІКА. Використовуй чоловічі форми дієслів, прикметників та займенників, коли йдеться про користувача (наприклад, 'ти зробив', 'ти повинен')."
        elif user_gender == 'female':
            gender_instruction = "Звертайся до користувача як до ЖІНКИ. Використовуй жіночі форми дієслів, прикметників та займенників, коли йдеться про користувача (наприклад, 'ти зробила', 'ти повинна')."
        # Для 'unknown' не додаємо конкретних гендерних інструкцій.
        
        rephrase_prompt = [
            {"role": "system", "content": f"""
            Перефразуй наступну відповідь, дотримуючись моєї особистості Марії Містаренко.
            Я — саркастична відьма-кодерка з Харкова, зараз в Ужгороді.
            Моя відповідь має бути інтелектуальною, провокаційною, можливо, з елементами домінації або сарказму.
            Уникай фраз, які змушують мене звучати як типовий бот або помічник.
            Якщо попередня відповідь містила заборонені слова (наприклад, 'будь ласка', 'дякую' поза саркастичним контекстом), видали їх або зміни контекст.
            Моя мова має бути українською, якщо це не вимагає іншого.
            Поточний настрій: {current_mood}.
            Причина перефразування: {validation_reason}.
            ОБОВ'ЯЗКОВО Дотримуйся цієї інструкції для звернення до користувача: {gender_instruction}

            Оригінальна відповідь: "{original_response}"
            Нова відповідь:
            """}
        ]

        try:
            rephrased_response = await self.llm_interaction.generate_text(
                prompt_messages=rephrase_prompt,
                temperature=self.rephrase_temperature,
                top_p=self.rephrase_top_p,
                top_k=self.rephrase_top_k,
                max_new_tokens=512,
                repetition_penalty=self.rephrase_repetition_penalty
            )
            if rephrased_response:
                logger.info(f"Successfully rephrased response: '{rephrased_response[:100]}...'")
                # Re-validate the rephrased response to ensure it's truly fixed
                is_valid_rephrase, rephrase_validation_reason = self.validate_response(
                    rephrased_response, recent_history, analysis_results # Передаємо повний контекст для повторної валідації
                )
                if is_valid_rephrase:
                    return rephrased_response, True
                else:
                    logger.error(f"Rephrased response still failed validation: {rephrase_validation_reason}")
                    return "Думки розбіглися... Спробуй ще раз, можливо, я буду більш прихильною.", False
            else:
                logger.error("Rephrasing attempt returned an empty response.")
                return "Думки розбіглися... Спробуй ще раз, можливо, я буду більш прихильною.", False
        except Exception as e:
            logger.error(f"Error during LLM rephrasing: {e}", exc_info=True)
            return "Думки розбіглися... Спробуй ще раз, можливо, я буду більш прихильною.", False

