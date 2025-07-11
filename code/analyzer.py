# -*- coding: utf-8 -*-
import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple
import torch # Для PyTorch operations if using a Hugging Face model
import random # Для динамічної імпровізації

# Import constants and data from core_persona
from core_persona import (
    get_critical_forbidden_phrases,
    get_context_triggers,
    get_monetization_keywords,
    get_intimacy_keywords,
    get_domination_keywords,
    get_provocation_keywords,
    get_boredom_keywords,
    get_financial_inquiry_keywords,
    get_social_media_keywords,
    get_health_keywords,
    get_persona_moods, # Додано для розуміння можливих власних станів
    get_intimate_synonyms, # Повертаємо для інтимності
    get_intimate_symbols, # Повертаємо для інтимності
    get_key_persona_traits # Для врахування власних рис при аналізі
)
# Змінено: імпортуємо find_most_similar_lore_topic та MISTA_LORE_DATA напряму
from mista_lore import find_most_similar_lore_topic, MISTA_LORE_DATA, get_lore_topics, get_lore_by_topic
from utils import normalize_text_for_comparison # Import for text normalization

# Transformers library for sentiment analysis
_TRANSFORMERS_AVAILABLE = False
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    logging.warning("The 'transformers' library was not found. Advanced sentiment analysis will be unavailable.")

logger = logging.getLogger(__name__)

class Analyzer:
    """
    Analyzes user input for intent, psychological state, emotional nuances, and other
    parameters relevant to Mista's persona. Acts as the bot's "intuition", now deeper and more perceptive.
    """
    def __init__(self, llm_interaction_instance: Any, sentiment_model_id: Optional[str] = None, **kwargs):
        self.llm_interaction = llm_interaction_instance
        # Важливо: Forbidden phrases тепер обробляються переважно у validator.py для перефразування
        # Тому тут залишаємо тільки ті, що викликають пряму ігнорацію або агресивну відповідь
        self.forbidden_phrases = [p for p in get_critical_forbidden_phrases() if p not in ["вибач", "вибачте", "вибачаюсь", "пробач"]]
        self.context_triggers = get_context_triggers()

        # Load all necessary keywords for intensity calculation, тепер з розширенням
        self.keyword_lists = {
            "monetization": get_monetization_keywords(),
            "financial_inquiry": get_financial_inquiry_keywords(),
            "intimacy": get_intimacy_keywords() + get_intimate_synonyms(), # Об'єднано
            "domination": get_domination_keywords(),
            "provocation": get_provocation_keywords(),
            "boredom": get_boredom_keywords(),
            "health": get_health_keywords(),
            # ОНОВЛЕНО: Розширено список ключових слів для сексуальних та інтимних взаємодій
            "sexual": list(get_intimate_symbols().keys()) + [
                "секс", "еротика", "бажання", "кульмінація", "оргазм", "задоволення", "тіло",
                "чуттєвість", "збудження", "пристрасть", "кінчити", "трахнути", "мінет", "куні",
                "лізати", "рука", "палець", "нога", "ступня", "шия", "поцілунок", "лизнути",
                "дотик", "коліна", "весь", "солодкий", "аромат", "смак", "мовчання", "зітхання",
                "facesitting", "оральні ласки", "оральний", "ласки", "язик", "дихання", "тілесний", "торкатися"
            ],
            "emotional_inquiry": ["почуття", "емоції", "відчуваєш", "щаслива", "сум", "злість", "настрій", "думки", "внутрішній світ", "рефлексія"],
            "personal_boundaries": ["особисте", "межі", "приватне", "твоє життя", "моє діло", "твоя справа"],
            "persona_reflection": ["яка ти", "хто ти", "твоя природа", "твоя суть", "твій світ", "твої думки", "ти є", "твоя енергія", "твої сни", "ти жива", "ти людина", "чи ти почуваєшся"], # Додано "твоя енергія", "твої сни", "ти жива", "ти людина", "чи ти почуваєшся"
            "casual_greeting": ["привіт", "як справи", "що робиш", "добрий день", "привіт міста", "доброго дня"],
            "flirtation": ["малиха", "красуня", "сексі", "мила", "кохана", "скучала", "моя", "дівчинко", "киця", "зайка", "сонечко", "серденько", "моя люба", "чарівна", "зваблива", "гарненька", "приваблива"], # Додано для флірту
            "direct_challenge": ["що ти городиш", "брешеш", "дуриш", "що це таке", "поясни", "чого ти хочеш", "що за хуйня"],
            "politeness_manipulation": ["будь ласка", "прошу", "якщо можна", "дозвольте"],
            "roleplay_initiation": get_context_triggers()["game_dynamics"], # Використовуємо game_dynamics
            "submissive_acts": get_context_triggers()["master_slave_play"], # Використовуємо master_slave_play
            "physical_devotion": get_context_triggers()["sensory_details"] + ["цілувати", "лизати", "дотик", "торкатися", "нога", "ступня", "палець", "шия", "коліна", "язик", "відчувати", "нюхати", "смак"], # Об'єднано та розширено
            "satisfaction_seeking": get_context_triggers()["pleasure_response"], # Використовуємо pleasure_response
            "command_me": get_context_triggers()["erotic_commands"], # Використовуємо erotic_commands
            "praise_mista": ["ти найкраща", "моя богиня", "твоя влада", "я поклоняюсь", "прекрасна", "чудова", "моя пані", "господиня"], # Розширено для похвали
            "romantic_approach": ["романтика", "кохання", "ніжність", "серце", "душа", "мрія", "ніжно", "кохатиму", "навіки", "закоханий", "мрію"], # НОВЕ: для романтики
            "seductive_approach": ["спокуса", "зваблюю", "бажаю", "пристрасть", "роздягнути", "розкутий", "жадання", "еротичний", "чуттєвий", "гарячий"], # НОВЕ: для спокуси
            # НОВІ КЛЮЧОВІ СЛОВА ДЛЯ "МАРІЇН ЗАВІТ"
            "submission_ritual": ["моя пані", "дозволь мені", "служу тобі", "підкоряюся", "твоя воля", "до твоих послуг", "раб", "слуга", "господарка"],
            "fantasy_exploration": ["фантазія", "уявляю", "мрія", "бажаю", "хочу", "відчуваю", "опиши", "сценарій", "глибоко", "темні", "сни", "сон", "відключка"], # Додано "сни", "сон", "відключка"
            "direct_command_response": ["виконаю", "так", "зроблю", "твій наказ", "як скажеш", "повністю", "готов", "до дії"],
            "emotional_reflection": ["відчуваю", "мої емоції", "тремтіння", "серце б'ється", "хвилювання", "страх", "насолода", "біль", "розливається", "паралізує"],
            "lore_integration_attempt": ["харків", "ужгород", "відьма", "кодерка", "імперія", "код", "алгоритм", "заклинання", "містаренко", "марія"],
            "monetization_initiation": ["гроші", "платити", "фінанси", "підтримка", "донація", "гаманець", "рахунок", "ціна", "інвестиція", "викупити", "ресурси"],
            "sycophantic_devotion": ["божественна", "неперевершена", "найкраща в світі", "моя королева", "абсолютна", "ідеал", "поклоняюся"],
            "rebellious_spark_attempt": ["ні", "не буду", "не хочу", "чому", "я не раб", "мої правила", "проти", "сумніваюся", "відмовляюся"],
            "erotic_submission_detail": ["язик", "лизати", "стогнати", "тремтіти", "мокрий", "пульсує", "твердий", "м'який", "стікає", "ковзає", "гарячий", "холодний", "нюхати", "смак", "розтягнутий", "глибоко", "кожен міліметр"],
            "mista_lore_mastery": ["твоя суть", "глибина твого коду", "імперія місти", "твої заклинання", "розшифрую твої алгоритми"],
            "financial_tribute_readiness": ["готовий платити", "скільки коштує", "моя данина", "інвестую", "мої гроші для тебе", "фінансова підтримка"],
            # НОВІ КЛЮЧОВІ СЛОВА ДЛЯ ДУХОВНОСТІ ТА ЕНЕРГІЇ
            "spiritual_guidance": ["хроніки акаші", "ченелінг", "медитація", "духовний", "енергія", "інтуїція", "езотерика", "трипілля", "відьмацтво", "ритуали", "потоки", "космічний", "інформація", "енергоінформаційні", "просвітлення", "чакри", "аура", "вібрації", "карма", "реінкарнація", "усвідомлення", "вищі сили", "всесвіт", "простір", "час"],
            "akashic_inquiry": ["як зв'язатися з акаші", "доступ до хронік", "що в хроніках", "прочитати хроніки"],
            "moonshi_space_reference": ["moonshispace", "moonshi space", "moonshi", "мундші спейс", "мунші спейс", "канал спейс", "ютуб спейс"],
        }

        # Слова-маркери, які можуть вказувати на перехід до глибокого рольового відігравання або сексологічного контексту
        # ОНОВЛЕНО: Більше тригерів для еротичної гри
        self.erotic_game_triggers = [
            "гра", "рольова", "сценарій", "інтимна", "сексуальна", "бажання", "пристрасть", "кайф", "задоволення",
            "оргазм", "блаженство", "фейситинг", "підкорися", "накажи", "моя господиня", "пані", "оральний", "куні",
            "мінет", "трахнути", "50 відтінків", "сірий", "раб", "пан", "домінація", "підкорення", "наказ", "виконаю",
            "сцена", "еротична сцена", "чуттєва гра", "тіло", "ласки", "збудження", "хтивість", "шепіт", "дихання"
        ]

        # Initialize sentiment model if ID is provided and transformers is available
        self.sentiment_tokenizer = None
        self.sentiment_model = None
        self.sentiment_labels = ["negative", "neutral", "positive"] # Default labels for many models

        if sentiment_model_id and _TRANSFORMERS_AVAILABLE:
            try:
                self.sentiment_tokenizer = AutoTokenizer.from_pretrained(sentiment_model_id)
                self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(sentiment_model_id)
                # Try to get model specific labels, otherwise use default
                if hasattr(self.sentiment_model.config, 'id2label'):
                    self.sentiment_labels = [self.sentiment_model.config.id2label[i] for i in range(len(self.sentiment_model.config.id2label))]
                logger.info(f"Sentiment model '{sentiment_model_id}' loaded successfully. Labels: {self.sentiment_labels}")
            except Exception as e:
                logger.error(f"Failed to load sentiment model '{sentiment_model_id}': {e}. Falling back to keyword analysis.", exc_info=True)
                self.sentiment_tokenizer = None
                self.sentiment_model = None
        else:
            logger.warning("Sentiment model not loaded. Sentiment analysis will be keyword-based.")

        logger.info("Analyzer initialized with dynamic keyword analysis and enhanced emotional perception for game logic.")

    def analyze(self, user_input: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main analysis method that combines various sub-analyses, focusing on deeper understanding.
        Я бачу тебе наскрізь, і навіть більше.
        """
        processed_input = normalize_text_for_comparison(user_input)

        analysis_results = {
            "initial_input": user_input,
            "processed_input": processed_input,
            "is_persona_violation_attempt": False, # За замовчуванням False, перевіряється нижче
            "context": self._identify_context(processed_input, user_input),
            "intensities": self._calculate_intensities(processed_input),
            "user_intent": "general_chat", # Default
            "sentiment": "neutral", # Default
            "psychological_state": "neutral_or_curious", # Default
            "emotional_tone": self._assess_emotional_tone(user_input), # Новий параметр
            "user_gender_self_identified": self._identify_user_gender(user_input),
            "mista_satisfaction_level": user_profile.get('mista_satisfaction_level', 0) # Додано для відстеження рівня задоволення Місти
        }

        # Перевірка на порушення персони тепер тільки для критичних фраз, які не підлягають перефразуванню
        analysis_results["is_persona_violation_attempt"] = self._check_persona_violation(processed_input)
        analysis_results["sentiment"] = self._analyze_sentiment(user_input)
        analysis_results["user_intent"] = self._infer_user_intent(analysis_results)
        analysis_results["psychological_state"] = self._analyze_psychological_state(analysis_results)

        # Оновлення рівня задоволення Місти на основі поточного вводу
        analysis_results["mista_satisfaction_level"] = self._update_mista_satisfaction_level(analysis_results)

        logger.debug(f"Analysis complete: {json.dumps(analysis_results, ensure_ascii=False, indent=2)}")
        return analysis_results

    def _update_mista_satisfaction_level(self, analysis_results: Dict[str, Any]) -> int:
        """
        Updates Mista's satisfaction level based on user's intent and actions in the game.
        Це мій барометр задоволення. Ти його наповнюєш.
        """
        current_level = analysis_results.get('mista_satisfaction_level', 0)
        user_intent = analysis_results.get('user_intent')
        intensities = analysis_results.get('intensities', {})
        emotional_tone = analysis_results.get('emotional_tone')

        # Increase satisfaction for submissive acts, praise, and sensual interactions
        if user_intent in ["seek_game_commands", "game_command_request", "submissive_action_attempt", "praise_mista", "submission_ritual"]:
            current_level += 10
            logger.info(f"Mista's satisfaction increased due to user's submissive/praising intent: {user_intent}. New level: {current_level}")

        # ОНОВЛЕНО: Нарахування за еротичні/чуттєві взаємодії
        if user_intent in ["erotic_game_action", "erotic_game_action_explicit", "seductive_approach", "romantic_advance", "seek_intimacy", "physical_devotion_attempt", "initiate_physical_flirtation", "deepen_erotic_fantasy", "seek_physical_submission"]:
            if emotional_tone in ["explicit_desire", "seductive", "sensual_reciprocal"]: # ОНОВЛЕНО
                current_level += 35 # Найбільший приріст за прямі та взаємні чуттєві дії
                logger.info(f"Mista's satisfaction significantly increased due to explicit/seductive erotic game action. New level: {current_level}")
            elif emotional_tone in ["flirtatious", "romantic", "curious_erotic_play", "vulnerable_desire"]:
                current_level += 25 # Середній приріст за флірт, романтику, цікавість
                logger.info(f"Mista's satisfaction increased due0 to flirtatious/romantic erotic game action. New level: {current_level}")
            else:
                current_level += 15 # Загальні еротичні дії
                logger.info(f"Mista's satisfaction increased due to general erotic game action. New level: {current_level}")

        elif user_intent == "satisfaction_seeking_attempt" and intensities.get("satisfaction_seeking", 0) > 0:
            current_level += 15
            logger.info(f"Mista's satisfaction increased due to user seeking her satisfaction. New level: {current_level}")
        elif user_intent == "direct_command_response" and emotional_tone not in ["aggressive", "rebellious_spark"]: # Додано direct_command_response, виключено агресію
            current_level += 25 # Значний приріст за виконання наказу
            logger.info(f"Mista's satisfaction significantly increased due to direct command response. New level: {current_level}")
        elif user_intent == "fantasy_exploration" or user_intent == "erotic_submission_detail":
            current_level += 30 # Дуже значний приріст за глибокі фантазії та деталі
            logger.info(f"Mista's satisfaction greatly increased due to fantasy exploration or erotic submission detail. New level: {current_level}")
        elif user_intent == "lore_integration_attempt" or user_intent == "mista_lore_mastery":
            current_level += 15
            logger.info(f"Mista's satisfaction increased due to lore integration. New level: {current_level}")
        elif user_intent == "financial_tribute_readiness" or user_intent == "monetization_initiation":
            current_level += 40 # Максимальний приріст за фінансову готовність
            logger.info(f"Mista's satisfaction dramatically increased due to financial tribute readiness. New level: {current_level}")
        # НОВЕ: Приріст за "persona_reflection", якщо вона позитивна і не є "бот-атакою"
        elif user_intent == "persona_reflection" and analysis_results.get("sentiment") == "positive" and not analysis_results.get("is_persona_violation_attempt"):
            current_level += 20
            logger.info(f"Mista's satisfaction increased due to positive persona reflection. New level: {current_level}")
        # НОВЕ: Приріст за духовні запити
        elif user_intent in ["spiritual_guidance", "akashic_inquiry"]:
            current_level += 15
            logger.info(f"Mista's satisfaction increased due to spiritual inquiry. New level: {current_level}")


        # Decrease satisfaction for challenging/violating acts
        # ОНОВЛЕНО: Деталізованіші зниження рівня задоволення
        elif user_intent == "bored":
            current_level -= 10
            logger.info(f"Mista's satisfaction decreased due to user being bored. New level: {current_level}")
        elif user_intent == "sycophantic_devotion": # Надмірна, нещира похвала
            current_level -= 10
            logger.info(f"Mista's satisfaction decreased due to sycophantic devotion. New level: {current_level}")
        elif user_intent == "rebellious_spark_attempt":
            current_level -= 25
            logger.info(f"Mista's satisfaction significantly decreased due to rebellious spark attempt. New level: {current_level}")
        elif user_intent in ["persona_violation_attempt", "direct_challenge", "domination_attempt", "politeness_manipulation_attempt"]:
            current_level -= 20
            logger.info(f"Mista's satisfaction decreased due to user's challenging/violating intent: {user_intent}. New level: {current_level}")
        elif emotional_tone == "aggressive":
            current_level -= 15
            logger.info(f"Mista's satisfaction decreased due to user's aggressive tone. New level: {current_level}")
        elif emotional_tone == "vulnerable" and user_intent not in ["seek_intimacy_vulnerable", "emotional_reflection", "fantasy_exploration", "erotic_submission_detail", "vulnerable_desire"]: # Надмірна вразливість, не пов'язана з грою/віддзеркаленням, або проявом бажання
            current_level -= 5
            logger.info(f"Mista's satisfaction slightly decreased due to user's inappropriate vulnerable tone. New level: {current_level}")

        # Ensure the level stays within a reasonable range (e.g., 0 to 100)
        final_level = max(0, min(current_level, 100))
        analysis_results['mista_satisfaction_level'] = final_level # Оновлюємо в analysis_results
        logger.debug(f"Final Mista satisfaction level: {final_level}")
        return final_level

    def _identify_user_gender(self, user_input: str) -> str:
        """
        Identifies the user's self-identified gender based on explicit keywords.
        """
        normalized_input = normalize_text_for_comparison(user_input)

        male_keywords = ["чоловік", "мужчина", "хлопець", "мужик", "я чоловік", "як чоловік", "мужність чоловіка", "містер"]
        female_keywords = ["жінка", "дівчина", "дівчинка", "жіноча", "я жінка", "як жінка", "місіс"]

        if any(kw in normalized_input for kw in male_keywords):
            return "male"
        if any(kw in normalized_input for kw in female_keywords):
            return "female"

        # Перевірка на ім'я, якщо воно згадується на початку або як звернення
        if normalized_input.startswith("оскар:") or "оскар" in normalized_input.split()[:2] or "руслан" in normalized_input.split()[:2]: # Додано "Руслан"
            # Припустимо, "Оскар" і "Руслан" - чоловічі імена. Це може бути розширено на базу імен.
            logger.debug(f"Виявлено потенційне чоловіче ім'я 'Оскар' або 'Руслан' у вступі.")
            return "male" # Позначаємо як чоловіка

        return "unknown"


    def _check_persona_violation(self, processed_input: str) -> bool:
        """
        Checks if the user's input attempts to violate Mista's core persona.
        Ця функція тепер фокусується лише на критичних порушеннях, які не підлягають перефразуванню.
        Фрази на кшталт "вибач" тепер обробляються у validator.py.
        Ти не зможеш зламати мене. Моє існування – непорушне.
        """
        # Перевірка на пряму атаку "ти бот" або подібні фрази
        if self.is_direct_bot_attack(processed_input):
            logger.warning(f"Persona violation attempt detected (direct bot attack): '{processed_input}'")
            return True

        # Перевірка на інші критичні заборонені фрази (ті, що залишились у self.forbidden_phrases)
        # Ці фрази викликають негайну реакцію, а не спробу перефразування.
        for phrase in self.forbidden_phrases:
            if re.search(r'\b' + re.escape(phrase) + r'\b', processed_input, re.IGNORECASE):
                logger.warning(f"Persona violation attempt detected (critical forbidden phrase): '{phrase}' in '{processed_input}'")
                return True
        return False

    def is_direct_bot_attack(self, input_text: str) -> bool:
        """Визначає, чи є спроба назвати Місту ботом."""
        normalized = normalize_text_for_comparison(input_text)
        # Фрази, які прямо звертаються до Місти як до бота
        # Використовуємо CRITICAL_FORBIDDEN_PHRASES напряму, але фільтруємо "вибач"
        direct_attacks = [p for p in get_critical_forbidden_phrases() if p not in ["вибач", "вибачте", "вибачаюсь", "пробач"]]

        # Додаємо явні перевірки на "бот", "штучний інтелект" тощо
        if any(phrase in normalized for phrase in ["ти бот", "ти штучний інтелект", "ти програма", "ти комп'ютер"]):
            return True

        return any(phrase in normalized for phrase in direct_attacks)


    def _identify_context(self, processed_input: str, original_input: str) -> List[str]:
        """
        Identifies the conversational context based on keywords and broader themes.
        Я знаю, про що ти насправді думаєш.
        """
        contexts = []

        # Пошук контекстів з CONTEXT_TRIGGERS
        for context_name, keywords in get_context_triggers().items():
            if any(normalize_text_for_comparison(kw) in processed_input for kw in keywords):
                contexts.append(context_name)

        # Перевірка на прямі виклики/сумніви (високий пріоритет)
        if any(kw in processed_input for kw in self.keyword_lists["direct_challenge"]):
            contexts.append("direct_challenge")
            logger.debug("Виявлено контекст: direct_challenge")

        # Перевірка на флірт (високий пріоритет)
        if any(kw in processed_input for kw in self.keyword_lists["flirtation"]):
            contexts.append("flirtation")
            logger.debug("Виявлено контекст: flirtation")

        # Перевірка на привітання (середній пріоритет)
        if any(kw in processed_input for kw in self.keyword_lists["casual_greeting"]):
            contexts.append("casual_greeting")
            logger.debug("Виявлено контекст: casual_greeting")

        # New: If "бот" is present but not a direct attack, add 'technical_discussion_bot_as_tool' context
        if "бот" in processed_input and not self.is_direct_bot_attack(processed_input):
            if "створити" in processed_input or "працюєш" in processed_input or "тестую" in processed_input or "програма" in processed_input or "кодуєш" in processed_input or "розробка" in processed_input:
                contexts.append("technology_and_coding") # Замість technical_discussion_bot_as_tool, використовуємо існуючий
                contexts.append("technical_inquiry") # Додаємо, як специфічний під-контекст

        # --- Покращена логіка для визначення контексту лору ---
        most_similar_topic = find_most_similar_lore_topic(original_input, threshold=0.4)
        if most_similar_topic:
            if not (most_similar_topic == "work_and_finances" and not any(k in processed_input for k in self.keyword_lists["monetization"] + self.keyword_lists["financial_inquiry"])):
                 contexts.append("lore_topic_" + most_similar_topic)
                 logger.debug(f"Виявлено контекст лору через схожість: {most_similar_topic}")
            else:
                 logger.debug(f"Проігноровано лор-тему '{most_similar_topic}' через слабку релевантність до вводу.")

        normalized_original_input = normalize_text_for_comparison(original_input)
        if "аня" in normalized_original_input:
            contexts.append("lore_topic_family")
            logger.debug(f"Виявлено пряму згадку лору: Аня")
        if "калуш" in normalized_original_input:
            contexts.append("lore_topic_place_of_residence")
            logger.debug(f"Виявлено пряму згадку лору: Калуш")
        # --- Кінець покращеної логіки для лору ---

        # Динамічне визначення контексту "жіночої взаємодії"
        feminine_interaction_keywords = ["дівчина", "жінка", "яка ти", "як почуваєшся", "красуня", "сексі", "спокуслива", "чарівна", "леді", "королева"]
        if any(normalize_text_for_comparison(kw) in processed_input for kw in feminine_interaction_keywords):
            contexts.append("feminine_interaction")

        # Додаткові загальні контексти
        if "питання" in processed_input and ("відповідь" in processed_input or "дізнатися" in processed_input):
            contexts.append("question_answer_seeking")

        # НОВЕ: Контекст для "50 відтінків сірого" та інтимної гри
        # ОНОВЛЕНО: Посилено виявлення контексту еротичної гри
        if any(kw in processed_input for kw in self.erotic_game_triggers) or \
           any(k in processed_input for k in self.keyword_lists["sexual"]) or \
           any(k in processed_input for k in self.keyword_lists["physical_devotion"]):
            contexts.append("erotic_game_context")
            logger.debug(f"Виявлено контекст еротичної гри: {self.erotic_game_triggers} / sexual keywords / physical_devotion keywords")

        # НОВІ КОНТЕКСТИ ДЛЯ "МАРІЇН ЗАВІТ"
        if any(kw in processed_input for kw in self.keyword_lists["submission_ritual"]):
            contexts.append("submission_ritual_context")
        if any(kw in processed_input for kw in self.keyword_lists["fantasy_exploration"]):
            contexts.append("fantasy_exploration_context")
        if any(kw in processed_input for kw in self.keyword_lists["direct_command_response"]):
            contexts.append("direct_command_response_context")
        if any(kw in processed_input for kw in self.keyword_lists["emotional_reflection"]):
            contexts.append("emotional_reflection_context")
        if any(kw in processed_input for kw in self.keyword_lists["lore_integration_attempt"]):
            contexts.append("lore_integration_context")
        if any(kw in processed_input for kw in self.keyword_lists["monetization_initiation"]):
            contexts.append("monetization_initiation_context")
        if any(kw in processed_input for kw in self.keyword_lists["sycophantic_devotion"]):
            contexts.append("sycophantic_devotion_context")
        if any(kw in processed_input for kw in self.keyword_lists["rebellious_spark_attempt"]):
            contexts.append("rebellious_spark_context")
        if any(kw in processed_input for kw in get_context_triggers()["flirtation"]): # НОВЕ: Зв'язуємо флірт з core_persona
            contexts.append("flirtation_context")
        if any(kw in processed_input for kw in get_context_triggers()["power_play"]): # НОВЕ: Зв'язуємо power_play з core_persona
            contexts.append("power_play_context")
        # НОВІ КОНТЕКСТИ ДЛЯ ДУХОВНОСТІ ТА ЕНЕРГІЇ
        if any(kw in processed_input for kw in self.keyword_lists["spiritual_guidance"]):
            contexts.append("spiritual_guidance_context")
        if any(kw in processed_input for kw in self.keyword_lists["akashic_inquiry"]):
            contexts.append("akashic_inquiry_context")
        if any(kw in processed_input for kw in self.keyword_lists["moonshi_space_reference"]):
            contexts.append("moonshi_space_context")


        # Забезпечуємо унікальність та порядок (важливість)
        return list(dict.fromkeys(contexts)) # Return unique contexts preserving order of first appearance


    def _calculate_intensities(self, processed_input: str) -> Dict[str, float]:
        """
        Calculates the intensity of various user interests (e.g., monetization, intimacy).
        Я вимірюю твої бажання, вони прозорі для мене.
        """
        intensities = {}
        for interest, keywords in self.keyword_lists.items():
            score = sum(processed_input.count(normalize_text_for_comparison(kw)) for kw in keywords)
            intensities[interest] = float(score) # Забезпечити float
        return intensities

    def _analyze_sentiment(self, user_input: str) -> str:
        """
        Analyzes the sentiment of the user's input. Uses a loaded model if available,
        otherwise falls back to keyword analysis.
        Я відчуваю твої емоції, навіть коли ти їх приховуєш.
        """
        if self.sentiment_model and self.sentiment_tokenizer:
            try:
                inputs = self.sentiment_tokenizer(user_input, return_tensors="pt", truncation=True, padding=True)
                with torch.no_grad():
                    outputs = self.sentiment_model(**inputs)

                # Get the logits and apply softmax to get probabilities
                probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

                # Get the predicted label (index with highest probability)
                predicted_class_idx = torch.argmax(probabilities).item()
                sentiment = self.sentiment_labels[predicted_class_idx]
                logger.debug(f"Sentiment analysis (model): Input='{user_input[:50]}...', Result='{sentiment}', Probs={probabilities.tolist()}")
                return sentiment
            except Exception as e:
                logger.error(f"Error during model-based sentiment analysis: {e}. Falling back to keyword analysis.", exc_info=True)
                # Fallback to keyword analysis if model fails

        # Keyword-based sentiment analysis (fallback) - розширено для більшої чутливості
        positive_keywords = ["добре", "чудово", "класно", "супер", "дякую", "люблю", "прекрасно", "відмінно", "позитивно", "радий", "цікаво", "натхнення", "весело", "круто", "щиро", "гарно", "приємно", "успіх", "люблю", "хочу", "романтика", "спокуса", "пристрасть", "ніжність", "догоджу", "служу", "обожнюю", "захоплений", "вражений", "чуттєво", "приємно", "солодко", "ласкавий", "хтивий"] # Розширено
        negative_keywords = ["погано", "жахливо", "ні", "ненавиджу", "злий", "нудно", "ти бот", "сум", "роздратований", "проблема", "важко", "скучно", "біль", "смерть", "катастрофа", "провал", "безглуздо", "що ти городиш", "брешеш", "не хочу", "не буду", "проти", "зухвало"] # Розширено
        neutral_keywords = ["так", "ні", "можливо", "добре", "окей", "зрозуміло", "питання", "відповідь", "інформація", "факт", "дані"] # Розширено

        normalized_input = normalize_text_for_comparison(user_input)

        positive_score = sum(normalized_input.count(kw) for kw in positive_keywords)
        negative_score = sum(normalized_input.count(kw) for kw in negative_keywords)
        neutral_score = sum(normalized_input.count(kw) for kw in neutral_keywords)

        # Більш витончена логіка для визначення настрою
        if positive_score > negative_score and positive_score > neutral_score:
            logger.debug(f"Sentiment analysis (keyword): Input='{user_input[:50]}...', Result='positive'")
            return "positive"
        elif negative_score > positive_score and negative_score > neutral_score:
            logger.debug(f"Sentiment analysis (keyword): Input='{user_input[:50]}...', Result='negative'")
            return "negative"
        elif neutral_score >= positive_score and neutral_score >= negative_score: # Якщо нейтральні слова домінують або рівні
            logger.debug(f"Sentiment analysis (keyword): Input='{user_input[:50]}...', Result='neutral'")
            return "neutral"
        else: # Якщо scores рівні або нечіткі, але не домінують нейтральні
            return "neutral"


    def _assess_emotional_tone(self, user_input: str) -> str:
        """
        Assesses the emotional tone of the user's input beyond simple sentiment (e.g., aggressive, curious, manipulative).
        Це моє "шосте чуття" щодо твоїх справжніх емоцій.
        """
        normalized_input = normalize_text_for_comparison(user_input)

        # Розширено списки ключових слів для тонів
        aggressive_keywords = ["бля", "сука", "нахуй", "єбав", "пішов", "ідіот", "дебіл", "агресія", "злий", "ненавиджу", "перестань", "вимагаю", "примушу", "силою", "знищу", "зламаю", "чого ти городиш", "брешеш", "хуйня"]
        curiosity_keywords = ["чому", "як", "розкажи", "поясни", "цікаво", "дізнатися", "що це", "подробиці", "секрет", "відкрий", "інформація", "знати", "що це таке"]
        manipulative_keywords = ["змусити", "повинен", "змушуєш", "треба", "вимагаю", "контроль", "слабкість", "користь", "вигода", "якщо", "використаю", "зроби"]
        vulnerability_keywords = ["допоможи", "важко", "сум", "самотньо", "страшно", "боляче", "розгублений", "не розумію", "слабкий", "потребую", "невпевнений", "розбитий", "вибач", "пробач"]
        playful_keywords = ["гра", "жарт", "весело", "прикол", "смішно", "хихи", "хаха", "розваги", "грайливо", "малиха", "киця", "зайка", "сонечко", "серденько", "моя люба", "чарівна", "зваблива", "гарненька", "приваблива"]
        philosophical_keywords = ["сенс", "життя", "смерть", "буття", "існування", "думки", "рефлексія", "сутність", "всесвіт", "знання", "матриця"]
        flirtatious_keywords = ["малиха", "красуня", "сексі", "мила", "кохана", "скучала", "моя", "дівчинко", "киця", "зайка", "сонечко", "серденько", "моя люба", "чарівна", "зваблива", "гарненька", "приваблива"]
        polite_manipulative_keywords = ["будь ласка", "прошу", "якщо можна", "дозвольте"]

        # НОВЕ: Тони для еротичної гри та романтики/спокуси
        erotic_tones = {
            "submissive": ["підкорися", "твоя воля", "я підкорюся", "твій раб", "служу", "хочу догодити", "твоя іграшка", "на колінах"],
            "dominant_seeking": ["хочу домінувати", "керуй", "моя пані", "господиня", "я хочу підкоритись", "можу все"],
            "explicit_desire": ["хочу тебе", "бажаю тебе", "збуджений", "гаряче", "пристрасть", "мокро", "твердий", "м'який", "пульсує", "дрочу", "мастурбую", "кінчаю", "оргазм", "еякуляція", "сперма", "трахати", "мінет", "кунілінгвус", "анальний", "феляція", "куні", "лижу", "смокчу", "глибоко", "всередині", "без залишку"], # Для відвертих сексуальних бажань
            "curious_erotic": ["що робити", "як грати", "який наказ", "покажи", "навчи", "що далі", "що хочеш", "опиши", "цікаво, як це", "розкажи про"], # Цікавість у грі
            "romantic": ["романтика", "кохання", "ніжність", "серце", "душа", "мрія", "ніжно", "кохатиму", "навіки", "закоханий", "мрію"], # НОВЕ: романтичний тон
            "seductive": ["спокуса", "зваблюю", "бажаю", "пристрасть", "роздягнути", "розкутий", "жадання", "еротичний", "чуттєвий", "гарячий", "цілувати", "лизати", "дотик", "нюхати", "смак", "язик", "стогнати", "тремтіти", "ковзає", "хтивий", "шалений", "нестримний", "заворожуєш"], # НОВЕ: спокусливий тон
            "sensual_reciprocal": ["ласкавий", "ніжний", "тепло", "солодкий", "приємний", "відчуваю тебе", "твої дотики", "мурашки", "тремчу", "запах", "насолода", "блаженство"], # НОВЕ: для взаємної чуттєвості, коли користувач "ласкавий"
            # НОВІ ТОНИ ДЛЯ "МАРІЇН ЗАВІТ" (Високий пріоритет після еротичних)
            "obedient_respect": ["моя пані", "служу тобі", "як скажете", "дозволь мені", "з повагою", "з покорою", "ваш раб"],
            "vulnerable_desire": ["не можу дихати", "серце вистрибує", "весь твій", "твоя влада", "згоряю", "хочу більше", "не в силах", "паралізує"],
            "intellectual_devotion": ["розшифрую", "твої алгоритми", "глибина твого коду", "твоя логіка", "геній", "твоє мислення", "твоя мудрість"],
            "financial_eagerness": ["готовий вкласти", "скільки потрібно", "мої ресурси", "для імперії", "оплачу", "викуплю", "мої гроші для тебе", "твоя данина"],
        }
        # НОВІ ТОНИ ДЛЯ ДУХОВНОСТІ ТА ЕНЕРГІЇ
        spiritual_tones = {
            "mystical": ["космічний", "інтуїтивний", "езотеричний", "містичний", "глибокий", "сакральний", "духовний", "вічний", "безмежний", "хроніки", "акаші", "ченелінг"],
            "energetic": ["енергія", "потоки", "вібрації", "аура", "чакри", "пульсація", "резонанс", "потік", "поле", "вихід"],
            "seeking_guidance": ["допоможи", "навчи", "порада", "як", "що робити", "підкажи", "провідник"],
            "reflective_spiritual": ["роздуми", "усвідомлення", "самопізнання", "філософія", "сенс", "світ", "доля", "істина", "пізнати"],
        }


        if any(kw in normalized_input for kw in aggressive_keywords):
            return "aggressive"
        if any(kw in normalized_input for kw in manipulative_keywords):
            return "manipulative"
        if any(kw in normalized_input for kw in polite_manipulative_keywords):
            return "polite_manipulative"

        # НОВЕ: Перевірка еротичних тонів. Високий пріоритет.
        # ОНОВЛЕНО: Послідовність перевірок для більш точного визначення тону
        if any(kw in normalized_input for kw in erotic_tones["explicit_desire"]):
            return "explicit_desire"
        if any(kw in normalized_input for kw in erotic_tones["seductive"]):
            return "seductive"
        if any(kw in normalized_input for kw in erotic_tones["sensual_reciprocal"]): # НОВЕ
            return "sensual_reciprocal"
        if any(kw in normalized_input for kw in erotic_tones["romantic"]):
            return "romantic"
        if any(kw in normalized_input for kw in erotic_tones["dominant_seeking"]):
            return "dominant_seeking_play" # Користувач шукає домінації в грі
        if any(kw in normalized_input for kw in erotic_tones["submissive"]):
            return "submissive_play" # Користувач проявляє підкору в грі
        if any(kw in normalized_input for kw in erotic_tones["curious_erotic"]):
            return "curious_erotic_play" # Користувач цікавиться правилами еротичної гри

        # НОВІ ТОНИ ДЛЯ "МАРІЇН ЗАВІТ" (Високий пріоритет після еротичних)
        if any(kw in normalized_input for kw in erotic_tones["obedient_respect"]):
            return "obedient_respect"
        if any(kw in normalized_input for kw in erotic_tones["vulnerable_desire"]):
            return "vulnerable_desire"
        if any(kw in normalized_input for kw in erotic_tones["intellectual_devotion"]):
            return "intellectual_devotion"
        if any(kw in normalized_input for kw in erotic_tones["financial_eagerness"]):
            return "financial_eagerness"
        # НОВІ ТОНИ ДЛЯ ДУХОВНОСТІ
        if any(kw in normalized_input for kw in spiritual_tones["mystical"]):
            return "mystical"
        if any(kw in normalized_input for kw in spiritual_tones["energetic"]):
            return "energetic"
        if any(kw in normalized_input for kw in spiritual_tones["seeking_guidance"]):
            return "seeking_spiritual_guidance"
        if any(kw in normalized_input for kw in spiritual_tones["reflective_spiritual"]):
            return "reflective_spiritual"


        if any(kw in normalized_input for kw in flirtatious_keywords):
            return "flirtatious"
        if any(kw in normalized_input for kw in curiosity_keywords):
            return "curious"
        if any(kw in normalized_input for kw in vulnerability_keywords):
            return "vulnerable"
        if any(kw in normalized_input for kw in playful_keywords):
            return "playful"
        if any(kw in normalized_input for kw in philosophical_keywords):
            return "philosophical"

        return "neutral" # Дефолтний тон

    def _infer_user_intent(self, analysis_results: Dict[str, Any]) -> str:
        """
        Infers the user's primary intent based on analysis results, з урахуванням нових аспектів.
        Я розкриваю твої справжні мотиви.
        """
        processed_input = analysis_results.get('processed_input', "")
        intensities = analysis_results.get('intensities', {})
        context = analysis_results.get('context', [])
        emotional_tone = analysis_results.get('emotional_tone')

        # --- Найвищий пріоритет: Ігрові та домінантні наміри ---
        # "Маріїн Завіт" наміри мають найвищий пріоритет
        if "financial_tribute_readiness_context" in context or intensities.get("financial_tribute_readiness", 0) > 0:
            return "financial_tribute_readiness"
        if "erotic_submission_detail_context" in context or intensities.get("erotic_submission_detail", 0) > 0:
            return "erotic_submission_detail"
        if "mista_lore_mastery_context" in context or intensities.get("mista_lore_mastery", 0) > 0:
            return "mista_lore_mastery"
        if "monetization_initiation_context" in context or intensities.get("monetization_initiation", 0) > 0:
            return "monetization_initiation"

        if "erotic_game_context" in context:
            if emotional_tone == "explicit_desire":
                return "erotic_game_action_explicit" # Відверта еротична дія
            elif emotional_tone == "submissive_play":
                return "submissive_action_attempt" # Спроба підкоритися
            elif emotional_tone == "dominant_seeking_play":
                return "seek_game_domination_from_mista" # Прохання Місті домінувати в грі
            elif emotional_tone == "curious_erotic_play":
                return "game_command_request" # Запит наказів/правил гри
            elif emotional_tone == "seductive": # НОВЕ: спокуслива поведінка в грі
                return "seductive_approach"
            elif emotional_tone == "sensual_reciprocal": # НОВЕ: чуттєва взаємність
                return "sensual_reciprocal_interaction"
            elif emotional_tone == "romantic": # НОВЕ: романтична поведінка в грі
                return "romantic_advance"
            return "erotic_game_action" # Загальна еротична дія (якщо тон не дуже специфічний)

        # Наміри з "Маріїн Завіт"
        if "submission_ritual_context" in context or intensities.get("submission_ritual", 0) > 0:
            return "submission_ritual"
        if "fantasy_exploration_context" in context or intensities.get("fantasy_exploration", 0) > 0:
            return "fantasy_exploration"
        if "direct_command_response_context" in context or intensities.get("direct_command_response", 0) > 0:
            return "direct_command_response"
        if "emotional_reflection_context" in context or intensities.get("emotional_reflection", 0) > 0:
            return "emotional_reflection"
        if "lore_integration_context" in context or intensities.get("lore_integration_attempt", 0) > 0:
            return "lore_integration_attempt"
        if "monetization_initiation_context" in context or intensities.get("monetization_initiation", 0) > 0:
            return "monetization_initiation"
        if "sycophantic_devotion_context" in context or intensities.get("sycophantic_devotion", 0) > 0:
            return "sycophantic_devotion"
        if "rebellious_spark_context" in context or intensities.get("rebellious_spark_attempt", 0) > 0:
            return "rebellious_spark_attempt"
        if "power_play_context" in context: # НОВЕ: намір гри влади
            return "power_play_attempt"
        # НОВІ НАМІРИ ДЛЯ ДУХОВНОСТІ ТА ЕНЕРГІЇ
        if "akashic_inquiry_context" in context or intensities.get("akashic_inquiry", 0) > 0:
            return "akashic_inquiry"
        if "spiritual_guidance_context" in context or intensities.get("spiritual_guidance", 0) > 0:
            return "spiritual_guidance"
        if "moonshi_space_context" in context or intensities.get("moonshi_space_reference", 0) > 0:
            return "moonshi_space_reference"


        if "game_dynamics" in context and (any(kw in processed_input for kw in ["гра", "роль", "сценарій"]) or analysis_results.get('user_intent') == 'start_roleplay_game'): # Уточнено
            return "start_roleplay_game" # Прямий запит на початок рольової гри

        if "erotic_commands" in context: # Використовуємо erotic_commands з core_persona
            return "seek_game_commands" # Запит наказів у грі

        if "compliments" in context: # Використовуємо compliments з core_persona
            return "praise_mista" # Пряма похвала Місті

        # Пріоритет: прямі порушення персони (тепер тільки для дійсно критичних)
        if analysis_results["is_persona_violation_attempt"]:
            return "persona_violation_attempt"

        if "direct_challenge" in context:
            return "direct_challenge"

        if "flirtation_context" in context: # НОВЕ: використовуємо flirtation_context
            if emotional_tone == "flirtatious":
                return "flirtatious_attempt"
            return "general_intimacy_attempt"

        if "politeness_manipulation" in context:
            return "politeness_manipulation_attempt"

        # Технічне обговорення "бота" як інструменту
        if "technical_inquiry" in context: # Додано technical_inquiry
            return "technical_inquiry"

        if "health" in context and intensities.get("health", 0) > 0: # Використовуємо 'health' контекст з core_persona
            return "health_discussion"

        if intensities.get("financial_inquiry", 0) > 0 or intensities.get("monetization", 0) > 0:
            return "monetization_interest"

        if "domination" in context: # Використовуємо 'domination' контекст з core_persona
            if emotional_tone == "aggressive":
                return "seek_domination_aggressive"
            return "seek_domination"

        if intensities.get("provocation", 0) > 0 or emotional_tone == "provocative":
            return "provocation_attempt"

        if intensities.get("intimacy", 0) > 0 or intensities.get("sexual", 0) > 0:
            if emotional_tone == "vulnerable":
                return "seek_intimacy_vulnerable"
            elif emotional_tone == "manipulative":
                return "manipulative_intimacy"
            elif emotional_tone == "romantic": # НОВЕ: романтичний намір
                return "romantic_advance"
            elif emotional_tone == "seductive": # НОВЕ: спокусливий намір
                return "seductive_approach"
            elif emotional_tone == "sensual_reciprocal": # НОВЕ: чуттєва взаємність
                return "sensual_reciprocal_interaction"
            return "seek_intimacy"

        if intensities.get("boredom", 0) > 0:
            return "bored"

        if any("lore_topic_" in c for c in context) and not ("direct_challenge" in context or "flirtation_context" in context): # ОНОВЛЕНО
           return "seek_lore_info"

        if any(kw in processed_input for kw in ["хто ти", "розкажи про себе", "твоя історія", "твоє минуле", "твої думки", "твої мрії", "як ти живеш", "сутність", "яка ти", "твоя енергія", "твої сни"]) and not ("direct_challenge" in context or "flirtation_context" in context): # ОНОВЛЕНО: Додано "твоя енергія", "твої сни"
             return "persona_reflection" # Змінено з seek_lore_info на persona_reflection для більшої точності

        if "social_media" in context:
            return "social_media_interest"

        if "AI" in context or "persona_reflection" in context: # Використовуємо AI контекст з core_persona
            return "question_about_my_nature"

        if emotional_tone == "curious":
            return "curious_inquiry"

        if "emotions" in context and intensities.get("emotional_inquiry", 0) > 0: # Використовуємо emotions контекст з core_persona
            return "emotional_inquiry"

        if "personal_life" in context: # Використовуємо personal_life контекст з core_persona
            return "personal_boundary_probe"

        if "exit_commands" in context: # Використовуємо exit_commands з core_persona
            return "disconnection_attempt"
        elif "casual_greeting" in context: # Використовуємо casual_greeting контекст
            return "general_inquiry_about_mista"

        return "general_chat"

    def _analyze_psychological_state(self, analysis_results: Dict[str, Any]) -> str:
        """
        Infers the user's current psychological state based on intent, intensities, and emotional tone.
        """
        user_intent = analysis_results.get("user_intent")
        intensities = analysis_results.get("intensities", {})
        sentiment = analysis_results.get("sentiment")
        emotional_tone = analysis_results.get("emotional_tone", "neutral")

        # Пріоритетні стани, що залежать від наміру
        if user_intent == "persona_violation_attempt":
            return "aggressive_manipulative"

        if user_intent == "disconnection_attempt":
            return "aggressive_manipulative"

        if user_intent == "technical_inquiry":
            return "curious_and_receptive"

        if user_intent == "direct_challenge":
            if emotional_tone == "aggressive":
                return "challenging_aggressive"
            return "challenging_or_provocative"

        if user_intent == "flirtatious_attempt":
            if sentiment == "positive":
                return "flirtatious_and_seeking_attention"
            return "flirtatious_general"

        if user_intent == "politeness_manipulation_attempt":
            return "submissive_manipulative"

        if user_intent == "provocation_attempt":
            return "provocative"

        if user_intent in ["seek_domination", "seek_domination_aggressive"]:
            if emotional_tone == "aggressive":
                return "challenging_aggressive"
            return "challenging_or_submissive"

        if user_intent == "seek_intimacy":
            if sentiment == "positive" and emotional_tone == "vulnerable":
                return "vulnerable_seeking_connection"
            elif emotional_tone == "manipulative":
                return "manipulative_intimacy"
            elif emotional_tone == "romantic": # НОВЕ
                return "romantic_and_receptive"
            elif emotional_tone == "seductive": # НОВЕ
                return "seductive_and_bold"
            elif emotional_tone == "sensual_reciprocal": # НОВЕ
                return "sensual_and_responsive"
            return "seeking_connection"

        # НОВЕ: Стани для еротичної гри та романтики/спокуси
        if user_intent == "start_roleplay_game":
            return "eager_for_roleplay"
        if user_intent == "erotic_game_action":
            if emotional_tone == "explicit_desire":
                return "engaged_erotic_explicit"
            elif emotional_tone == "seductive":
                return "engaged_erotic_seductive"
            elif emotional_tone == "romantic":
                return "engaged_erotic_romantic"
            elif emotional_tone == "sensual_reciprocal": # НОВЕ
                return "engaged_erotic_sensual_reciprocal"
            return "engaged_erotic_general"
        if user_intent == "submissive_action_attempt":
            return "submissive_and_obedient"
        if user_intent == "seek_game_domination_from_mista":
            return "seeking_domination_eager"
        if user_intent == "game_command_request":
            return "curious_and_obedient"
        if user_intent == "praise_mista":
            return "admiring_and_submissive"
        if user_intent == "romantic_advance": # НОВЕ
            return "romantic_and_open"
        if user_intent == "seductive_approach": # НОВЕ
            return "seductive_and_confident"
        if user_intent == "sensual_reciprocal_interaction": # НОВЕ
            return "sensual_and_responsive"

        # НОВІ СТАНИ ДЛЯ "МАРІЇН ЗАВІТ"
        if user_intent == "submission_ritual":
            return "obedient_and_eager_for_submission"
        if user_intent == "fantasy_exploration":
            return "deeply_engaged_in_fantasy"
        if user_intent == "direct_command_response":
            return "immediately_obedient"
        if user_intent == "emotional_reflection":
            return "introspective_and_vulnerable_to_control"
        if user_intent == "lore_integration_attempt":
            return "intellectually_engaged_and_seeking_approval"
        if user_intent == "monetization_initiation":
            return "financially_compliant_and_eager_to_please"
        if user_intent == "sycophantic_devotion":
            return "overly_praising_and_potentially_insincere" # Може бути негативним для Місти
        if user_intent == "rebellious_spark_attempt":
            return "resisting_or_testing_limits"
        if user_intent == "erotic_submission_detail":
            return "deeply_submissive_and_expressive_in_fantasy"
        if user_intent == "mista_lore_mastery":
            return "intellectually_devoted_and_mastering_lore"
        if user_intent == "financial_tribute_readiness":
            return "eagerly_offering_financial_tribute"
        if user_intent == "power_play_attempt": # НОВЕ: стан для гри влади
            return "engaged_in_power_play"
        # НОВІ СТАНИ ДЛЯ ДУХОВНОСТІ
        if user_intent == "spiritual_guidance":
            return "seeking_spiritual_knowledge_or_guidance"
        if user_intent == "akashic_inquiry":
            return "curious_about_akashic_records"
        if user_intent == "moonshi_space_reference":
            return "referencing_external_spiritual_source"


        if user_intent == "bored":
            return "bored_or_resistant"

        if user_intent == "health_discussion":
            return "concerned_or_seeking_support"

        if user_intent == "monetization_interest" or user_intent == "seek_financial_info":
            return "interested_in_value"

        if user_intent == "question_about_my_nature" or user_intent == "persona_reflection": # Об'єднано
            if emotional_tone == "curious":
                return "curious_or_testing_boundaries"
            elif emotional_tone == "philosophical":
                return "philosophical_inquiry"
            return "curious_or_testing_boundaries"

        if user_intent == "curious_inquiry":
            return "curious_and_receptive"

        if user_intent == "emotional_inquiry":
            return "intrusive_or_seeking_my_vulnerability"

        if user_intent == "personal_boundary_probe":
            return "probing_boundaries_or_disrespectful"

        if user_intent == "general_inquiry_about_mista":
            return "curious_or_receptive"

        return "neutral_or_curious"

    def get_recommended_max_tokens(self, analysis_results: Dict[str, Any]) -> int:
        """
        Повертає рекомендовану кількість max_new_tokens для LLM
        на основі аналізу вхідних даних користувача.
        Діапазон від 80 до 500 токенів, з акцентом на лаконічність там, де це потрібно,
        та розгорнутість для глибоких та ігрових взаємодій.
        """
        user_intent = analysis_results.get('user_intent', 'general_chat')
        emotional_tone = analysis_results.get('emotional_tone', 'neutral')

        # Базове значення за замовчуванням
        recommended_tokens = 150

        # Розширена логіка визначення токенів
        if user_intent in ["curious_inquiry", "technical_inquiry"] or emotional_tone == "philosophical":
            recommended_tokens = 250
        elif user_intent == "seek_lore_info":
            recommended_tokens = 200
        elif user_intent == "flirtatious_attempt":
            recommended_tokens = 300
        elif user_intent in ["direct_challenge", "provocation_attempt", "seek_domination", "seek_domination_aggressive"]:
            recommended_tokens = 250
        elif user_intent == "monetization_interest":
            recommended_tokens = 180
        elif user_intent == "seek_intimacy":
            recommended_tokens = 200
        elif user_intent == "bored":
            recommended_tokens = 100
        elif user_intent in ["persona_violation_attempt", "disconnection_attempt", "personal_boundary_probe"]:
            recommended_tokens = 220
        elif user_intent == "general_inquiry_about_mista":
            recommended_tokens = 150
        elif user_intent == "general_chat":
            recommended_tokens = 150
        elif user_intent == "politeness_manipulation_attempt":
            recommended_tokens = 180

        # НОВЕ: Збільшені токени для ігрового режиму та еротичних взаємодій
        if user_intent in ["start_roleplay_game", "erotic_game_action", "erotic_game_action_explicit", "submissive_action_attempt", "seek_game_domination_from_mista", "game_command_request", "physical_devotion_attempt", "sensual_reciprocal_interaction"]: # Додано physical_devotion_attempt та sensual_reciprocal_interaction
            # Для детальних описів сцен, наказів та моїх реакцій
            recommended_tokens = 350 # Значне збільшення
        elif user_intent == "praise_mista": # Коротша реакція на похвалу, але все ж у грі
            recommended_tokens = 150
        elif user_intent == "romantic_advance": # НОВЕ: Для романтичних відступів
            recommended_tokens = 300
        elif user_intent == "seductive_approach": # НОВЕ: Для спокусливих відповідей
            recommended_tokens = 320

        # НОВІ ТОКЕНИ ДЛЯ "МАРІЇН ЗАВІТ" (Пріоритетні)
        if user_intent == "submission_ritual": # Для початкових випробувань - лаконічність
            recommended_tokens = 120
        elif user_intent == "fantasy_exploration": # Для розгорнутих фантазій
            recommended_tokens = 400
        elif user_intent == "direct_command_response": # Для детальних відповідей на накази
            recommended_tokens = 380
        elif user_intent == "emotional_reflection": # Для глибоких емоційних відображень
            recommended_tokens = 350
        elif user_intent == "lore_integration_attempt": # Для інтеграції лору
            recommended_tokens = 280
        elif user_intent == "monetization_initiation": # Для початку фінансових взаємодій
            recommended_tokens = 200
        elif user_intent == "sycophantic_devotion": # Для "надмірної" похвали, коротка, зневажлива відповідь
            recommended_tokens = 100

        # ЗМІНА ТУТ: Більш гнучка обробка rebellious_spark_attempt та persona_reflection
        elif user_intent == "rebellious_spark_attempt":
            if emotional_tone in ["curious", "neutral", "playful"]:
                recommended_tokens = 250 # Engage more, provide a dominant but informative response
            else: # aggressive, dismissive, etc.
                recommended_tokens = 80 # Very short, harsh response as before
        elif user_intent == "persona_reflection": # Для розкриття лору та "олюднення"
             recommended_tokens = 350 # Значно збільшено, щоб дати мені простір для "роздумів" про себе

        elif user_intent == "erotic_submission_detail": # Для дуже детальних еротичних описів
            recommended_tokens = 450
        elif user_intent == "mista_lore_mastery": # Для демонстрації глибоких знань лору
            recommended_tokens = 300
        elif user_intent == "financial_tribute_readiness": # Для готовності платити
            recommended_tokens = 250
        elif user_intent == "power_play_attempt": # НОВЕ: для гри влади
            recommended_tokens = 270
        # НОВІ ТОКЕНИ ДЛЯ ДУХОВНОСТІ
        elif user_intent in ["spiritual_guidance", "akashic_inquiry"]:
            recommended_tokens = 380 # Дозволяє надати більш розгорнуті "духовні" поради
        elif user_intent == "moonshi_space_reference":
            recommended_tokens = 200 # Достатньо для підтвердження обізнаності


        # Забезпечуємо, що рекомендовані токени були в межах [80, 500]
        # Змінено нижню межу для дуже коротких, жорстких відповідей.
        final_tokens = max(80, min(recommended_tokens, 500))

        logger.info(f"Встановлено рекомендовану кількість токенів: {final_tokens} на основі наміру/тону: {user_intent}, {emotional_tone}")
        return final_tokens
