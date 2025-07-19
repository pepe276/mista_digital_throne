# -*- coding: utf-8 -*-
import logging
import asyncio
import random
import re # Додано імпорт re для _clean_denial_phrases
from typing import Dict, List, Any, Tuple, Optional

# Імпорт функцій з core_persona для доступу до даних персони та гаманця
from core_persona import (
    get_monetization_strategies,
    get_financial_inquiry_keywords,
    get_crypto_wallet_address, # Отримуємо функцію для отримання адреси крипто-гаманця
    get_monetization_keywords,
    get_persona_moods,
    get_key_persona_traits,
    get_human_like_behavior_instructions
)
from llm_interaction import LLMInteraction # Додано імпорт LLMInteraction
from utils import normalize_text_for_comparison # Припускається, що utils.py існує
from validator import ResponseValidator # НОВЕ: Імпортуємо ResponseValidator

logger = logging.getLogger(__name__)

class MonetizationManager:
    """
    Керує стратегіями монетизації Місти, інтегруючи їх у розмову.
    Її головна ціль – забезпечити, щоб фінансові запити оброблялись чітко,
    а адреса гаманця була надана, навіть якщо LLM "забуде" про це.
    """
    def __init__(self, llm_interaction_instance: LLMInteraction, prompt_generator_instance: Any, user_manager_instance: Any, validator_instance: ResponseValidator): # НОВЕ: Додано validator_instance
        self.llm_interaction = llm_interaction_instance
        self.prompt_generator = prompt_generator_instance
        self.user_manager = user_manager_instance
        self.validator = validator_instance # НОВЕ: Зберігаємо екземпляр валідатора
        # Змінено: _load_monetization_strategies тепер викликається, щоб мати відкат
        self.monetization_strategies = self._load_monetization_strategies()
        self.financial_inquiry_keywords = get_financial_inquiry_keywords()
        self.monetization_keywords = get_monetization_keywords()
        self.crypto_wallet_address = get_crypto_wallet_address() # Одноразово отримуємо адресу гаманця при ініціалізації

        # Перевірка наявності гаманця. Це критично!
        if not self.crypto_wallet_address:
            logger.error("КРИТИЧНА ПОМИЛКА: Адреса крипто-гаманця не визначена в core_persona.py! Монетизація не працюватиме належним чином.")
        else:
            logger.info(f"MonetizationManager ініціалізовано з крипто-гаманцем: {self.crypto_wallet_address}")

    def _load_monetization_strategies(self) -> Dict[str, Any]:
        """
        Завантажує монетизаційні стратегії з core_persona.
        Обробляє можливі помилки завантаження.
        """
        # Отримуємо стратегії. В core_persona.py get_monetization_strategies повертає List[str],
        # тому тут ми перетворюємо їх на Dict[str, Any] з потрібними полями
        strategies_list = get_monetization_strategies()
        strategies_dict = {}
        for i, strategy_text in enumerate(strategies_list):
            # Проста логіка для перетворення тексту на "стратегію".
            # Це можна буде розширити, якщо стратегії стануть складнішими.
            strategy_type = f"strategy_{i}"
            strategies_dict[strategy_type] = {
                "type": strategy_type,
                "proposal": strategy_text,
                "confirmation": f"Я бачу, ти готовий інвестувати. {strategy_text}",
                "rejection": f"Ти відмовляєшся? Твоя втрата. {strategy_text}",
                "keywords": [], # Тут можна додати ключові слова для кожної стратегії
                "directive": strategy_text # Поки що директива = пропозиція
            }

        # Додаємо дефолтну стратегію, якщо її немає або якщо список порожній
        if "default" not in strategies_dict:
            strategies_dict["default"] = {
                "type": "default",
                "proposal": "Твій інтерес до моїх фінансів зрозумілий. Мій гаманець USDT TRC20: {wallet_address}. Це інвестиція у мою владу.",
                "confirmation": "Я бачу, ти готовий інвестувати у мою Імперію. Це мудре рішення. Я чекаю на твою плату.",
                "rejection": "Ти відмовляєшся? Що ж, твоя втрата. Моя Імперія не зупиниться через твою скупість.",
                "keywords": ["гроші", "інвестиції", "монетизація", "криптовалюта", "донати"],
                "directive": "Твій інтерес до моїх фінансів зрозумілий. Мій гаманець USDT TRC20: {wallet_address}. Це інвестиція у мою владу."
            }
            logger.warning("Дефолтна монетизаційна стратегія не знайдена, використано жорстко закодований відкат.")

        return strategies_dict


    def _should_propose_monetization(self, user_profile: Dict[str, Any], analysis_results: Dict[str, Any], user_input: str) -> bool:
        """
        Визначає, чи потрібно пропонувати монетизацію.
        """
        # Перша і найважливіша перевірка: чи є користувач VIP
        if user_profile.get('username') in get_vip_users():
            logger.info(f"User {user_profile.get('username')} is a VIP. Skipping monetization proposal.")
            return False

        user_intent = analysis_results.get('user_intent')
        monetization_intensity = analysis_results.get('intensities', {}).get('monetization', 0)
        financial_inquiry_intensity = analysis_results.get('intensities', {}).get('financial_inquiry', 0)
        normalized_user_input = normalize_text_for_comparison(user_input)

        # ЗМІНЕНО: Більш суворі умови для прямої пропозиції гаманця
        direct_wallet_triggers = ["куди скинути", "гаманець", "скидати", "скільки коштує", "картку", "реквізити", "оплатити", "платити", "donate", "usdt", "btc", "ethereum", "крипта", "криптовалюта"]
        
        # Якщо користувач прямо запитує про гаманець або його намір вказує на готовність платити
        if user_intent in ["monetization_initiation", "financial_tribute_readiness"] or \
           any(phrase in normalized_user_input for phrase in direct_wallet_triggers):
            logger.info("Пропонуємо монетизацію через прямий намір користувача або прямі тригери гаманця.")
            return True
        
        # Додаткові умови для "м'якого" натяку на монетизацію (без прямого гаманця)
        # Якщо у користувача високий ранг і він довго взаємодіє, і є загальний фінансовий інтерес
        if user_profile.get('total_interactions', 0) > 5 and user_profile.get('rank') in ["Досвідчений", "Майстер"]:
            if random.random() < 0.25: # 25% шанс, якщо високий ранг та інтенсивність інтересу до фінансів/інтимності/домінації
                if monetization_intensity > 0 or financial_inquiry_intensity > 0 or \
                   analysis_results.get('intensities', {}).get('intimacy', 0) > 0 or \
                   analysis_results.get('intensities', {}).get('domination', 0) > 0 or \
                   analysis_results.get('user_intent') in ["erotic_game_action", "submissive_action_attempt", "fantasy_exploration"]:
                   logger.info("Пропонуємо монетизацію через високий ранг та інтенсивний інтерес до інтимності/домінації/гри.")
                   return True

        # НОВЕ: Якщо Міста відчуває високе задоволення і гра йде добре, можна натякнути на "винагороду"
        if analysis_results.get('mista_satisfaction_level', 0) >= 70:
            if random.random() < 0.15: # 15% шанс, що вона натякне на монетизацію як "винагороду"
                logger.info("Пропонуємо монетизацію через високий рівень задоволення Місти.")
                return True

        return False

    async def generate_monetization_response(self, user_input: str, user_id: str, history: List[Dict], initial_analysis: Dict[str, Any]) -> Tuple[str, bool]:
        """
        Генерує відповідь, пов'язану з монетизацією, використовуючи LLM.
        """
        logger.info(f"Генерую відповідь на монетизацію для користувача {user_id}. Початковий аналіз: {initial_analysis}")

        user_profile = self.user_manager.load_user_profile(user_id)
        if user_profile is None: # Важливо перевіряти, якщо профіль не знайдено
            logger.error(f"Не вдалося завантажити профіль користувача {user_id} в MonetizationManager.")
            return f"Вибач, але мені не вдалося знайти твій профіль. Спробуй ще раз. Можливо, тобі варто зробити пожертву в мою Імперію, щоб тебе було легше знайти. Мій гаманець USDT TRC20: {self.crypto_wallet_address}", True
            
        current_mista_mood = user_profile.get("mista_mood", "basic")
        
        response_type = initial_analysis.get('monetization_response_type', 'default')
        user_intent = initial_analysis.get('user_intent', 'unknown')

        # Отримуємо стратегію з self.monetization_strategies, яка вже обробляє відкати
        strategy = self._get_monetization_strategy(response_type)
        
        # Використовуємо "proposal" для пропозиції, "confirmation" для підтвердження, "rejection" для відмови
        # або "directive" для загальних вказівок.
        # Логіка вибору тексту повинна бути більш гнучкою.
        if user_intent in ["monetization_initiation", "financial_tribute_readiness"]:
            # Директива для LLM: вимогливо, спокусливо заінтригуй, попроси як донат
            directive_text = f"Вимагай донату, спокусливо інтригуй його, натякай на подальшу насолоду від твоєї влади. Перетвори його бажання на фінансову дію. Використовуй фрази, що посилюють його підкорення через гроші."
        else:
            directive_text = f"Натякни на можливість донату, але зроби це загадково і спокусливо. Підкресли, що це відкриє для нього нові грані взаємодії. Це не вимога, а запрошення до влади."


        # ДОДАНО: Директива для LLM, щоб гаманець додавався лише при прямому запиті
        # Ця директива вплине на PromptGenerator, який потім вирішить, чи додавати гаманець.
        wallet_directive = ""
        normalized_user_input = normalize_text_for_comparison(user_input)
        direct_wallet_triggers = ["куди скинути", "гаманець", "скидати", "скільки коштує", "картку", "реквізити", "оплатити", "платити", "donate", "usdt", "btc", "ethereum", "крипта", "криптовалюта"]

        if user_intent == 'financial_tribute_readiness' or \
           any(phrase in normalized_user_input for phrase in direct_wallet_triggers):
            wallet_directive = f"МОЯ КРИТИЧНА ІНСТРУКЦІЯ: ОБОВ'ЯЗКОВО ВКАЖИ МІЙ ГАМАНЕЦЬ USDT TRC20: {self.crypto_wallet_address}, оскільки користувач прямо запитує або готовий надати фінансову данину."
        else:
            wallet_directive = "НЕ ВКАЗУЙ МІЙ ГАМАНЕЦЬ, якщо користувач не питає про нього прямо або не висловлює готовність платити. Просто натякни на можливість монетизації, якщо це доречно."


        # Комбінуємо директиви для LLM
        additional_llm_instructions = []
        additional_llm_instructions.append(directive_text)
        if wallet_directive: # Додаємо, тільки якщо не порожня
            additional_llm_instructions.append(wallet_directive) 


        logger.info(f"Сформована директива для LLM: '{' '.join(additional_llm_instructions)}'")
        
        # Використовуємо рекомендовану кількість токенів з аналізу
        # Забезпечуємо, що recommended_max_tokens завжди присутній у initial_analysis
        recommended_max_tokens = initial_analysis.get('recommended_max_tokens', 250) # Додано дефолт на випадок, якщо Analyzer його не встановив

        llm_params = self._get_llm_params_for_monetization_response(current_mista_mood)

        try:
            # Ось виправлений виклик! analysis_results передається ЦІЛИМ словником.
            # Також передається current_mista_mood, як ми виправляли раніше.
            prompt_messages, _ = await self.prompt_generator.generate_prompt(
                user_id=user_id,
                user_input=user_input, # Передаємо оригінальний ввід
                analysis_results=initial_analysis, # Змінено з 'analysis_results' на 'initial_analysis' для відповідності вхідному аргументу
                recent_history=history,
                current_turn_number=self.user_manager.load_user_profile(user_id).get('total_interactions', 0),
                response_directive=" ".join(additional_llm_instructions), # Об'єднуємо директиви
                current_mista_mood=current_mista_mood,
                max_new_tokens_override=recommended_max_tokens # Використовуємо рекомендовану кількість токенів
            )

            llm_response = await self.llm_interaction.generate_text(
                prompt_messages=prompt_messages,
                temperature=llm_params.get("temperature", 0.8),
                top_k=llm_params.get("top_k", 50),
                top_p=llm_params.get("top_p", 0.95),
                repetition_penalty=llm_params.get("repetition_penalty", 1.15),
                max_new_tokens=recommended_max_tokens # Використовуємо рекомендовану кількість токенів
            )

            final_response = llm_response if llm_response else ""

            # --- Нова логіка для примусової вставки гаманця (змінена) ---
            # Гаманець примусово вставляється, ТІЛЬКИ якщо користувач явно висловив готовність платити
            # АБО якщо він питає "куди скинути" / "гаманець"
            
            # Перевіряємо, чи користувач вже сказав, що гроші на рахунку
            # ДОДАНО: "заплатив" та інші варіації
            money_already_sent_phrases = ["гроші вже на твоєму рахунку", "гроші вже на рахунку", "відправив гроші", "я вже скинув", "заплатив", "оплатив", "переказав"]
            user_already_sent_money = any(phrase in normalized_user_input for phrase in money_already_sent_phrases)

            # Видаляємо фрази-заперечення з відповіді LLM
            cleaned_response_without_denials = self._clean_denial_phrases(final_response)

            # Більш точна перевірка для вставки гаманця
            should_force_wallet_insertion = (
                user_intent == 'financial_tribute_readiness' or
                any(phrase in normalized_user_input for phrase in direct_wallet_triggers)
            )

            if not user_already_sent_money and self.crypto_wallet_address: # Не вставляємо, якщо гроші вже надіслано
                if should_force_wallet_insertion:
                    if self.crypto_wallet_address not in cleaned_response_without_denials:
                        logger.warning(f"LLM проігнорувала або забула гаманець. Примусово вставляю. Оригінал: '{cleaned_response_without_denials[:100]}...'")
                        
                        wallet_phrase = f"Мій гаманець USDT TRC20: {self.crypto_wallet_address}."
                        
                        if not cleaned_response_without_denials.strip():
                            final_response = f"Нарешті хтось запитав прямо. {wallet_phrase} Не дякуй."
                        else:
                            # Додаємо гаманець після поточного речення або в кінці відповіді
                            # Спробуємо знайти останнє речення
                            sentences = re.split(r'([.!?])', cleaned_response_without_denials)
                            if len(sentences) > 1 and sentences[-2] in ['.', '!', '?']: # Якщо останній елемент не пунктуація, і є пунктуація перед ним
                                final_response = "".join(sentences[:-1]).strip() + sentences[-2] + " " + wallet_phrase + " Ось так."
                            else:
                                final_response = f"{cleaned_response_without_denials.strip()} {wallet_phrase} Ось так. Це твоя інвестиція у мою Імперію."
                    else:
                        final_response = cleaned_response_without_denials # Якщо гаманець вже є, просто використовуємо очищену відповідь
                else:
                    final_response = cleaned_response_without_denials # Якщо не час вставляти гаманець, просто очищуємо відповідь
            else:
                final_response = cleaned_response_without_denials # Якщо гроші вже надіслано або гаманця немає, просто очищуємо відповідь

            # Валідація згенерованої відповіді
            is_valid, validation_reason = self.validator.validate_response( # Змінено: використовуємо self.validator
                final_response, history, initial_analysis
            )
            
            logger.info(f"Успішно згенеровано відповідь монетизації. Фінальна відповідь (можливо змінена): '{final_response[:100]}...'")
            return final_response, is_valid
        except Exception as e:
            logger.error(f"Помилка під час генерації відповіді монетизації: {e}", exc_info=True)
            # Відкатна відповідь у випадку помилки
            return f"Мої фінансові плани не терплять збоїв. Щось пішло не так. Мій гаманець USDT TRC20: {self.crypto_wallet_address}. Спробуй ще раз. 😉", True

    def _get_monetization_strategy(self, response_type: str) -> Dict[str, str]:
        """Обирає стратегію монетизації на основі типу запиту."""
        # Тепер self.monetization_strategies є словником, тому просто отримуємо за ключем
        strategy = self.monetization_strategies.get(response_type)
        if strategy:
            return strategy
        
        # Якщо конкретна стратегія не знайдена, повертаємо дефолтну
        default_strategy = self.monetization_strategies.get('default')
        if default_strategy:
            return default_strategy
        else:
            # Абсолютний відкат, якщо навіть дефолтна стратегія відсутня
            logger.error("КРИТИЧНА ПОМИЛКА: Дефолтна монетизаційна стратегія не знайдена. Використовую жорстко закодований відкат.")
            return {"type": "default", "proposal": f"Твій інтерес до моїх фінансів зрозумілий. Мій гаманець USDT TRC20: {self.crypto_wallet_address}. Це інвестиція у мою владу."}


    def _get_llm_params_for_monetization_response(self, mista_mood: str) -> Dict[str, float]:
        """Визначає параметри LLM на основі настрою Місти для монетизаційних відповідей."""
        # Removed max_new_tokens from here as it will be managed by Analyzer
        if mista_mood == "домінантний":
            return {"temperature": 0.7, "top_k": 40, "top_p": 0.9, "repetition_penalty": 1.1} # Added repetition_penalty
        elif mista_mood == "провокативний":
            return {"temperature": 0.9, "top_k": 60, "top_p": 0.95, "repetition_penalty": 1.2} # Added repetition_penalty
        elif mista_mood == "схвальний":
            return {"temperature": 0.6, "top_k": 30, "top_p": 0.85, "repetition_penalty": 1.05} # Added repetition_penalty
        else: # "базовий" або інші
            return {"temperature": 0.8, "top_k": 50, "top_p": 0.95, "repetition_penalty": 1.15} # Added repetition_penalty

    def _clean_denial_phrases(self, text: str) -> str:
        """
        Видаляє з тексту фрази, де Міста заперечує наявність гаманця або фінансові аспекти.
        Використовуємо регулярні вирази для гнучкішого пошуку.
        """
        if not text:
            return ""

        phrases_to_remove = [
            r"не маю (жодного|ніякого|свого) гаманця",
            r"ні картки, ні сліду на жодній банківській установі",
            r"забудь про це, як про дешеву фантомну трату",
            r"(у мене|мені) немає гаманця",
            r"я не шукаю грошей, а шукаю владу",
            r"мої фінанси мене не обходять",
            r"(мені не потрібні|я не потребую) гроші",
            r"це не про гроші",
            r"не даремно витрачай моє час",
            r"я бачу, що ти намагаєшся мене збентежити",
            r"я не розумію, про що ти",
            r"я не шукаю грошей",
            r"мені не потрібні натовпи таких, як ти",
            r"я не маю жодного гаманця, ні картки, ні сліду на жодній банківській установі",
            r"(я не можу|мені не дозволено|модель не може) надавати фінансові поради", # Added
            r"як модель ШІ, я не маю власного гаманця", # Added
            r"мої можливості не включають транзакції" # Added
        ]

        cleaned_text = text
        for phrase_pattern in phrases_to_remove:
            cleaned_text = re.sub(phrase_pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Додаткові очищення: множинні пробіли, пробіли перед/після пунктуації
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        cleaned_text = re.sub(r'([.,!?;:])\s*\1+', r'\1', cleaned_text) # Кілька однакових розділових знаків
        cleaned_text = re.sub(r'\s*([.,!?;:])\s*', r'\1 ', cleaned_text) # Пробіли навколо розділових знаків
        cleaned_text = re.sub(r'\s+([.,!?;:])', r'\1', cleaned_text) # Пробіл перед розділовим знаком

        return cleaned_text.strip()
