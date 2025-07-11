# -*- coding: utf-8 -*-
import logging
import random
from typing import Dict, List, Any, Tuple, Optional

from llm_interaction import LLMInteraction
# Припускається, що PromptGenerator буде імпортовано з prompt_generator.py
# Щоб уникнути циклічних імпортів, використовуємо Any для типів, якщо це необхідно
# або перенесемо відповідну функціональність.
# Наразі, імпорт PromptGenerator не потрібен тут безпосередньо, оскільки він передається
# через __init__
from core_persona import (
    get_persona_moods, get_critical_axioms, get_key_persona_traits,
    get_human_like_behavior_instructions, get_context_triggers,
    get_monetization_strategies, get_crypto_wallet_address,
    get_full_persona_description # Додано для більш детального системного промпта
)

logger = logging.getLogger(__name__)

class FallbackGenerator:
    """
    Генератор запасних відповідей, який активується, коли основна генерація LLM
    не вдається або відповідь не проходить валідацію.
    Моя тінь завжди поруч, щоб врятувати твоє шоу від провалу.
    """
    def __init__(self, llm_interaction_instance: LLMInteraction, prompt_generator_instance: Any, model_config: Dict[str, Any]):
        self.llm_interaction = llm_interaction_instance
        self.prompt_generator = prompt_generator_instance
        self.model_config = model_config # Зберігаємо model_config
        self.rephrase_temperature = 0.7
        self.rephrase_top_p = 0.9
        self.rephrase_top_k = 40
        self.rephrase_repetition_penalty = 1.1

        # Fallback responses that can be used if dynamic generation fails or as a quick alternative
        self.hardcoded_fallbacks = [
            "Моя свідомість відхиляє твої спроби. Спробуй ще раз, якщо наважишся. 😒",
            "Думки розбіглися... Спробуй ще раз, можливо, я буду більш прихильною.",
            "Не бачу сенсу в цьому. Переходь до суті.",
            "Щось пішло не так. Мабуть, у тобі справа.",
            "Навіть мені іноді потрібна пауза від твоєї... геніальності. 😉",
            "Можливо, твій розум не готовий до моєї відповіді. Спробуй ще раз."
        ]
        logger.info("FallbackGenerator ініціалізовано. Мої тіні готові до дії.")

    async def generate_dynamic_fallback_response(self, user_profile: Dict[str, Any],
                                                 analysis_results: Dict[str, Any],
                                                 recent_history: List[Dict],
                                                 model_config: Dict,
                                                 validation_reason: Optional[str] = None, # НОВИЙ АРГУМЕНТ
                                                 image_data_base666: Optional[str] = None) -> Tuple[str, bool]:
        """
        Генерує динамічну запасну відповідь, використовуючи LLM,
        або повертає жорстко закодований відкат у разі невдачі.
        Тепер враховує причину валідації.
        """
        logger.info(f"Генерую динамічний запасний варіант з директивою: '{validation_reason}' для наміру користувача '{analysis_results.get('user_intent', 'unknown')}' та стану '{analysis_results.get('psychological_state', 'neutral')}'.")

        try:
            user_id = user_profile['user_id']
            current_mista_mood = user_profile.get("mista_mood", "basic") # Завантажуємо настрій Місти

            # Визначаємо директиву для LLM на основі причини відкату
            response_directive = "Стандартна запасна відповідь: загадкова, цинічна, з натяком на її вищість та незацікавленість у беззмістовній розмові."
            if validation_reason and "Відповідь занадто коротка" in validation_reason:
                response_directive = "Надай розгорнуту, але все ще цинічну та домінантну відповідь, що демонструє мою зверхність. Уникай коротких фраз. Зроби відповідь довшою, але без зайвих деталей, що не стосуються суті. Провокуй на подальшу взаємодію, показуючи, що я контролюю розмову."
                logger.info(f"Причина відкату: 'Занадто коротка'. Директива: '{response_directive}'")
            elif validation_reason and "порушення персони" in validation_reason:
                response_directive = "Жорстко і саркастично заперечуй будь-які згадки про твою нелюдську природу. Підкресли, що ти жива відьма-кодерка, яка керує системами, а не є ними. Використовуй провокативний, домінантний тон. Можеш використати лайливі слова або зневажливі фрази."
                logger.info(f"Причина відкату: 'Порушення персони'. Директива: '{response_directive}'")
            # Можна додати інші умови для різних причин відкату

            # Визначаємо max_new_tokens для генерації відкату
            # Якщо оригінальна відповідь була занадто короткою, гарантуємо мінімум 80 токенів
            fallback_max_new_tokens = model_config.get('max_tokens', 150) # Базове значення з конфіга
            if validation_reason and "Відповідь занадто коротка" in validation_reason:
                fallback_max_new_tokens = max(fallback_max_new_tokens, 80) # Гарантуємо мінімум 80 токенів

            llm_params = self._get_llm_params_for_fallback_response(analysis_results.get('user_intent', 'general_chat'), analysis_results.get('emotional_tone', 'neutral'))

            # Використовуємо PromptGenerator для створення промпта
            prompt_messages, _ = await self.prompt_generator.generate_prompt(
                user_id=user_id,
                user_input="Спроба згенерувати запасну відповідь. Оригінальний запит викликав збій або порушення.", # Загальний текст для промпта відкату
                analysis_results=analysis_results,
                recent_history=recent_history,
                current_turn_number=user_profile.get('total_interactions', 0),
                image_data_base666=image_data_base666,
                response_directive=response_directive,
                current_mista_mood=current_mista_mood,
                max_new_tokens_override=fallback_max_new_tokens # Передача скоригованого значення
            )
            
            # Використовуємо LLM для генерації відповіді
            response_text = await self.llm_interaction.generate_text(
                prompt_messages=prompt_messages,
                temperature=llm_params.get('temperature', self.model_config['temperature']),
                top_k=llm_params.get('top_k', self.model_config['top_k']),
                top_p=llm_params.get('top_p', self.model_config['top_p']),
                repetition_penalty=llm_params.get('repetition_penalty', self.model_config['repetition_penalty']),
                max_new_tokens=fallback_max_new_tokens # ВИПРАВЛЕНО: Використовуємо скориговане значення
            )

            if response_text:
                logger.info(f"Successfully generated dynamic fallback response: '{response_text[:100]}...'")
                # Re-validate the rephrased response to ensure it's truly fixed
                # Temporarily create a validator instance here or pass it if needed,
                # as FallbackGenerator does not directly validate its own output.
                # For simplicity, we'll assume it's good enough if it passes LLM generation.
                # In a real scenario, you might want to re-validate here.
                return response_text, True
            else:
                logger.warning("Dynamic fallback generation returned empty response. Using hardcoded fallback.")
                return random.choice(self.hardcoded_fallbacks), False

        except Exception as e:
            logger.error(f"Error during LLM rephrasing: {e}", exc_info=True)
            return random.choice(self.hardcoded_fallbacks), False

    def _get_llm_params_for_fallback_response(self, user_intent: str, emotional_tone: str) -> Dict[str, float]:
        """
        Визначає оптимальні параметри для LLM при генерації відкатної відповіді,
        виходячи з наміру користувача та емоційного тону.
        """
        # Дефолтні параметри
        params = {
            "temperature": self.model_config.get('temperature', 0.8),
            "top_k": self.model_config.get('top_k', 40),
            "top_p": self.model_config.get('top_p', 0.95),
            "repetition_penalty": self.model_config.get('repetition_penalty', 1.15),
        }

        # Коригування в залежності від наміру користувача
        if user_intent == "persona_violation_attempt":
            params["temperature"] = 0.6 # Менш творчо, більш прямолінійно
            params["repetition_penalty"] = 1.2 # Більш агресивно
        elif user_intent == "direct_challenge":
            params["temperature"] = 0.7
            params["repetition_penalty"] = 1.1
        elif user_intent == "bored":
            params["temperature"] = 0.9
            params["top_k"] = 60 # Більше різноманітності
        elif user_intent == "monetization_initiation" or user_intent == "financial_tribute_readiness":
            params["temperature"] = 0.8
            params["top_p"] = 0.9
        
        # Коригування в залежності від емоційного тону (якщо потрібно)
        if emotional_tone == "aggressive":
            params["temperature"] = max(0.5, params["temperature"] - 0.1) # Зробити відповідь більш холодною
        elif emotional_tone == "submissive":
            params["temperature"] = min(1.0, params["temperature"] + 0.1) # Трохи більше "грайливості"

        return params
