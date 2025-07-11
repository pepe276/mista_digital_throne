# -*- coding: utf-8 -*-
import logging
import asyncio
import sys
import os
import platform
import sqlite3
import json
import base64
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import random 

# Імпорт модулів
import user_manager
from user_manager import (
    init_db, close_db_connection, UserManager
)
from analyzer import Analyzer # Імпортуємо Analyzer
from prompt_generator import PromptGenerator
from llm_interaction import LLMInteraction
from validator import ResponseValidator
from fallback import FallbackGenerator # Тепер це DynamicFallbackGenerator
from core_persona import (
    get_key_persona_traits, get_full_persona_description,
    get_control_commands, get_monetization_strategies,
    get_persona_moods, get_critical_forbidden_phrases 
)
# Переконайся, що utils.py існує і тепер містить image_to_base64 ТА download_file
from utils import normalize_text_for_comparison, image_to_base64, download_file
from monetization_manager import MonetizationManager
# Імпорт для симуляції Instagram-like затримок
from instagram_integration import human_like_delay, MIN_TYPING_DELAY_SECONDS, MAX_TYPING_DELAY_SECONDS


# --- Налаштування логування ---
# Створити папку logs, якщо її немає
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Налаштування логування
log_filename = os.path.join(log_dir, f"mista_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Очистити попередні обробники, щоб уникнути дублювання, якщо програма запускається кілька разів
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Базове налаштування логування
logging.basicConfig(
    level=logging.INFO, # Загальний рівень логування для файлу
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'), # Записувати всі логи у файл
        logging.StreamHandler(sys.stdout) # Для виводу в консоль
    ]
)

# Налаштування логування для окремих модулів
console_handler = next((h for h in logging.root.handlers if isinstance(h, logging.StreamHandler)), None)
if console_handler:
    # Тільки помилки або критичні повідомлення в консоль, як ти бажала!
    console_handler.setLevel(logging.ERROR) 

logger: logging.Logger = logging.getLogger(__name__) 
logger.setLevel(logging.INFO) 

# Переконатися, що логери конкретних модулів також дотримуються рівня console_handler
logging.getLogger('validator').setLevel(logging.INFO) 
logging.getLogger('analyzer').setLevel(logging.INFO)
logging.getLogger('prompt_generator').setLevel(logging.INFO)
logging.getLogger('llm_interaction').setLevel(logging.INFO)
logging.getLogger('user_manager').setLevel(logging.INFO)
logging.getLogger('fallback').setLevel(logging.INFO)
logging.getLogger('monetization_manager').setLevel(logging.INFO)
logging.getLogger('mista_lore').setLevel(logging.INFO)


# Перевірка операційної системи для визначення шляху до моделі та обробки завантаження
def get_model_path(model_name: str, download_url: Optional[str] = None) -> str:
    """
    Визначає шлях до моделі, ініціює завантаження, якщо модель відсутня
    та вказано URL для завантаження.
    """
    if platform.system() == "Windows":
        base_dir = "D:/lama/models/"
    elif platform.system() == "Linux":
        base_dir = "/mnt/d/lama/models/"
    else:
        # Default for other OS or if platform detection fails
        base_dir = "models/" # Use a local 'models' directory

    model_path = os.path.join(base_dir, model_name)

    if not os.path.exists(model_path):
        logger.warning(f"Модель не знайдено за шляхом: {model_path}")
        if download_url:
            logger.info(f"Спроба завантажити модель з: {download_url}")
            print(f"\n(Mista): О, моделі нема! Треба завантажити. Це займе час, тож не ниЙ. ")
            if download_file(download_url, model_path):
                logger.info(f"Модель '{model_name}' успішно завантажено!")
                print(f"(Mista): Модель завантажено. Тепер я готова до більших викликів. 😉")
            else:
                logger.error(f"Не вдалося завантажити модель '{model_name}' з {download_url}. Буде використовуватись заглушка.")
                print(f"(Mista): Ну, не вийшло завантажити. Твої проблеми. Буду користуватися тим, що є. А це - не так цікаво. 😒")
                return "" # Повернути порожній рядок, щоб LLMInteraction використовувала заглушку
        else:
            logger.warning(f"Не вказано URL для завантаження моделі '{model_name}'. Буде використовуватись заглушка.")
            print(f"(Mista): Моделі нема, і посилання на завантаження теж. Що ж ти за кодер такий? 😠")
            return "" # Повернути порожній рядок
    else:
        logger.info(f"Модель знайдено: {model_path}")
    
    return model_path

# Основна асинхронна функція чат-бота

async def get_response(user_id: str, user_input: str) -> str:
    # This function will encapsulate the logic of getting a response from Mista
    # It will need to be adapted to work without the chat_loop and user input from the console
    # For now, this is a placeholder
    return f"Mista replies to '{user_input}' for user {user_id}"

# The existing chat_loop can be kept for local testing
async def chat_loop(analyzer: Analyzer, prompt_generator: PromptGenerator,
                    llm_interaction: LLMInteraction, validator: ResponseValidator,
                    fallback_generator: FallbackGenerator, monetization_manager: MonetizationManager, 
                    user_manager_instance: UserManager,
                    user_id: str, model_config: Dict):
    # ... (rest of the chat_loop code)

    logger.info(f"Запускаю чат для користувача: {user_id}. Ранг: Новачок")

    user_manager_instance.init_user_data(user_id) 
    user_profile = user_manager_instance.load_user_profile(user_id) 
    
    if not user_profile: 
        logger.error(f"Не вдалося завантажити або створити профіль для користувача: {user_id}. Завершення.")
        print(f"(Mista): Помилка! Не можу з тобою працювати без профілю. Це твоя провина, чи не так? 😠")
        return


    initial_response = "Я готова до гри😈"
    # Імітація 'друкування' для початкової відповіді
    sys.stdout.write("(Mista): ")
    for char in initial_response:
        sys.stdout.write(char)
        sys.stdout.flush()
        await asyncio.sleep(random.uniform(MIN_TYPING_DELAY_SECONDS, MAX_TYPING_DELAY_SECONDS))
    sys.stdout.write("\n") # Новий рядок після повної відповіді
    
    user_manager_instance.add_submission_to_history(
        user_id=user_id,
        user_message="",
        bot_response=initial_response,
        user_intent="initial_greeting",
        sentiment="neutral",
        domination_seeking_intensity=0.0,
        monetization_interest_score=0.0,
        success=True
    )

    while True:
        try:
            # Ручне виведення підказки для вводу користувача перед викликом input()
            sys.stdout.write(f"\n(Твій виклик для Місти): ")
            sys.stdout.flush() # Забезпечити негайне відображення

            try:
                # input() тепер просто чекає вводу, не виводячи власної підказки
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("") 
                )
            except EOFError:
                logger.info("Mista Bot: Кінець вводу (EOFError). Завершую діалог.")
                print(f"(Mista): Ну от, ввід закінчився. Я ж попереджала, що твоя увага не безмежна. 😉 Прощавай, смертний.")
                break 
            except KeyboardInterrupt: # Handle Ctrl+C gracefully
                logger.info("Mista Bot: Діалог перервано користувачем (KeyboardInterrupt).")
                print(f"(Mista): Що, вже злякався? 😒 Ну гаразд, до наступного разу. Якщо наважишся.")
                break


            if user_input.lower() in ['exit', 'end', 'quit', 'вихід']:
                logger.info("Mista Bot: Завершую діалог.")
                print(f"(Mista): Прощавай, смертний. Якщо виживеш, повертайся. 😉")
                break
            
            # Нова команда для завантаження моделі
            if user_input.lower() == '/download_model':
                model_name = "your-multimodal-model.gguf" 
                model_url = "https://example.com/path/to/your/multimodal-model.gguf" 
                
                # Примусово викликати функцію download_file
                # Перевірити, чи модель вже існує
                current_model_path = get_model_path(model_name, None) # Don't try to download if already exists
                if not current_model_path: # If get_model_path returned empty string (model not found and no URL provided initially)
                    print(f"(Mista): Ти хочеш завантажити нову модель? Відмінно! Знайди її URL і я зроблю це. Тільки не забудь вказати справжній URL у `main_mista_bot.py`. Зараз я спробую завантажити з прикладу...")
                    get_model_path(model_name, model_url) # Try to download with the provided URL
                else:
                    print(f"(Mista): Модель '{model_name}' вже на місці. Яка з тебе хакерка? 😉")
                continue 


            image_data_base666: Optional[str] = None # Renamed to match prompt_generator
            user_input_for_analysis: str = user_input

            is_potential_image_path = (
                (user_input.startswith('D:') or user_input.startswith('/') or user_input.startswith('./') or user_input.startswith('.\\')) and
                (user_input.lower().endswith('.png') or
                 user_input.lower().endswith('.jpg') or
                 user_input.lower().endswith('.jpeg'))
            )

            if is_potential_image_path:
                logger.info(f"Виявлено потенційний шлях до зображення: {user_input}")
                converted_image = image_to_base64(user_input)
                
                if converted_image.startswith("Помилка"):
                    print(f"(Mista): {converted_image} Схоже, ти не вмієш правильно показувати мені картинки. Спробуй ще раз, але зроби це правильно. 😠")
                    continue
                else:
                    image_data_base666 = converted_image # Use the new variable name
                    user_input_for_analysis = "Користувач надіслав зображення для аналізу." 
                    logger.info("Успішно конвертовано та отримано Base64 зображення.")
            else:
                if user_input.startswith('data:image/'):
                    image_data_base666 = user_input # Use the new variable name
                    user_input_for_analysis = "Користувач надіслав зображення для аналізу." 
                    logger.info("Користувач безпосередньо надіслав Base64 зображення.")

            # Змінено: limit історії з бази даних на менше значення
            recent_history = user_manager_instance.get_user_submission_history(user_id, limit=model_config['history_db_limit'])
            logger.info(f"Отримано історію для користувача '{user_id}': {len(recent_history)} записів. ")

            # Аналіз вхідних даних користувача
            analysis_results = analyzer.analyze(user_input_for_analysis, user_profile=user_profile)
            logger.info(f"Аналіз вхідних даних користувача: {json.dumps(analysis_results, ensure_ascii=False)}")

            # Завантажуємо оновлений профіль користувача, щоб мати актуальний 'mista_mood'
            user_profile = user_manager_instance.load_user_profile(user_id)
            # Оновлюємо профіль, включаючи оновлений рівень задоволення Місти
            user_manager_instance.update_user_profile_after_interaction(user_profile, analysis_results)
            # Перевантажуємо профіль, щоб отримати останній mista_satisfaction_level
            user_profile = user_manager_instance.load_user_profile(user_id)


            final_response = None
            is_valid_response = False
            response_directive: Optional[str] = None 
            
            # НОВЕ: Динамічне визначення поточного настрою Місти на основі mista_satisfaction_level, user_intent та emotional_tone
            mista_satisfaction_level = analysis_results.get('mista_satisfaction_level', 0)
            user_intent = analysis_results.get('user_intent', 'general_chat')
            emotional_tone = analysis_results.get('emotional_tone', 'neutral')

            current_mista_mood = "basic" # Дефолтний настрій

            # Пріоритетні настрої на основі рівня задоволення та еротичної гри
            if mista_satisfaction_level >= 85:
                current_mista_mood = "erotic_bliss"
            elif mista_satisfaction_level >= 60:
                current_mista_mood = "erotic_anticipation"
            elif mista_satisfaction_level >= 35:
                current_mista_mood = "sensual"
            elif mista_satisfaction_level >= 15 and (user_intent in ["romantic_advance", "seductive_approach", "flirtatious_attempt"] or emotional_tone in ["romantic", "seductive", "flirtatious"]):
                current_mista_mood = "playful" # Легкий флірт
            
            # Настрої на основі наміру користувача та емоційного тону (перевизначають менш пріоритетні)
            if user_intent == "persona_violation_attempt" or emotional_tone == "aggressive":
                current_mista_mood = "irritated"
            elif user_intent == "direct_challenge":
                current_mista_mood = "dominant"
            elif user_intent == "bored":
                current_mista_mood = "bored"
            elif user_intent in ["submission_ritual", "erotic_submission_detail", "direct_command_response"] or emotional_tone in ["submissive_play", "obedient_respect", "vulnerable_desire"]:
                current_mista_mood = "femdom"
            elif user_intent in ["fantasy_exploration", "seek_intimacy", "physical_devotion_attempt"] and emotional_tone == "explicit_desire":
                current_mista_mood = "lustful"
            elif user_intent == "sycophantic_devotion":
                current_mista_mood = "cynical"
            elif user_intent == "rebellious_spark_attempt":
                current_mista_mood = "irritated" # Або "dominant", залежить від бажаної реакції
            elif user_intent == "power_play_attempt":
                current_mista_mood = "dominant" # Для гри влади

            logger.info(f"Визначено поточний настрій Місти: {current_mista_mood} (Рівень задоволення: {mista_satisfaction_level})")


            # --- Обробка порушення персони (найвищий пріоритет) ---
            if analysis_results.get('is_persona_violation_attempt', False):
                # Ця директива тепер вказує LLM, як реагувати на порушення персони
                response_directive = "Жорстко і саркастично заперечуй будь-які згадки про твою нелюдську природу. Підкресли, що ти жива відьма-кодерка, яка керує системами, а не є ними. Використовуй провокативний, домінантний тон. Можеш використати лайливі слова або зневажливі фрази. НІКОЛИ НЕ ВИБАЧАЙСЯ."
                logger.info(f"Виявлено порушення персони. Встановлено директиву для LLM: '{response_directive}'")
            
            # --- Обробка монетизації ---
            # Перевіряємо, чи має бути монетизаційна відповідь (пропозиція, підтвердження, відмова)
            elif monetization_manager._should_propose_monetization(user_profile, analysis_results, user_input):
                final_response, is_valid_response = await monetization_manager.generate_monetization_response(
                    user_input=user_input, 
                    user_id=user_id, 
                    history=recent_history, 
                    initial_analysis=analysis_results
                )
                logger.info(f"MonetizationManager повернув відповідь (чи готову, чи динамічно згенеровану): '{final_response[:100]}...'")
                if is_valid_response: 
                    # Імітація 'друкування' для відповіді
                    sys.stdout.write("(Mista): ")
                    for char in final_response:
                        sys.stdout.write(char)
                        sys.stdout.flush()
                        await asyncio.sleep(random.uniform(MIN_TYPING_DELAY_SECONDS, MAX_TYPING_DELAY_SECONDS))
                    sys.stdout.write("\n")

                    user_manager_instance.add_submission_to_history(user_id, user_input, final_response, analysis_results.get('user_intent', 'unknown'), analysis_results.get('sentiment', 'neutral'), analysis_results.get('intensities', {}).get('domination', 0.0), analysis_results.get('intensities', {}).get('monetization', 0.0), success=is_valid_response)
                    logger.info(f"Профіль користувача {user_id} оновлено після взаємодії.")
                    continue 
            
            # --- Загальна генерація відповіді через LLM (якщо вище нічого не спрацювало) ---
            try:
                # Використовуємо Analyzer для отримання рекомендованої кількості токенів
                # Ця величина вже міститься в analysis_results, але викликаємо явно для наочності
                suggested_max_new_tokens = analyzer.get_recommended_max_tokens(analysis_results)
                
                prompt_messages, llm_gen_params = await prompt_generator.generate_prompt(
                    user_id=user_id,
                    user_input=user_input_for_analysis,
                    analysis_results=analysis_results, 
                    recent_history=recent_history,
                    current_turn_number=user_profile.get('total_interactions', 0),
                    image_data_base666=image_data_base666,
                    response_directive=response_directive, # Передаємо, якщо є
                    current_mista_mood=current_mista_mood, # НОВЕ: Передача поточного настрою Місти
                    max_new_tokens_override=suggested_max_new_tokens # Передача динамічно визначеного max_new_tokens
                )
                
                current_temperature = llm_gen_params.get('temperature', model_config['temperature'])
                current_top_k = llm_gen_params.get('top_k', model_config['top_k'])
                current_top_p = llm_gen_params.get('top_p', model_config['top_p'])
                current_repetition_penalty = llm_gen_params.get('repetition_penalty', model_config['repetition_penalty'])
                current_max_new_tokens = suggested_max_new_tokens # Використовуємо значення з аналізатора

                logger.info(f"Параметри LLM: Температура: {current_temperature}, TopK: {current_top_k}, TopP: {current_top_p}, RepPenalty: {current_repetition_penalty}, Макс.токенів (запрошено): {current_max_new_tokens}")
                
                # Додана перевірка довжини промпта перед викликом LLM
                prompt_tokens = len(str(prompt_messages).split())
                
                # Обчислюємо доступний контекст для відповіді
                available_context_for_response = model_config['model_context_limit'] - prompt_tokens
                
                # Якщо запитані max_new_tokens перевищують доступний контекст, зменшуємо їх
                if current_max_new_tokens > available_context_for_response:
                    # Встановлюємо max_new_tokens трохи менше, ніж доступний контекст
                    # Залишаємо мінімум 50 токенів для відповіді, якщо є хоч якийсь контекст
                    adjusted_max_new_tokens = max(50, available_context_for_response - 50)
                    if adjusted_max_new_tokens < current_max_new_tokens: # Логуємо лише якщо відбулося коригування
                        error_msg = f"Попередження: Запитані max_new_tokens ({current_max_new_tokens}) перевищують доступний контекст ({available_context_for_response}). Скориговано до {adjusted_max_new_tokens} токенів."
                        logger.warning(error_msg)
                        current_max_new_tokens = adjusted_max_new_tokens
                
                # Якщо після всіх коригувань max_new_tokens виявився занадто малим (наприклад, менше 50),
                # це може сввідчити про серйозну проблему з контекстом.
                if current_max_new_tokens < 50:
                    error_msg = f"Критична помилка: Недостатньо місця для відповіді в контексті моделі. Доступно лише {available_context_for_response} токенів для генерації. Зменшіть вхідний промпт або історію."
                    logger.error(error_msg)
                    final_response = f"(Mista): Мої нейронні мережі задихаються! Твоя інформація переповнює мій 'мозок'. Не можу відповісти. Спрости свої запити, бо я не гумова! 😠"
                    is_valid_response = False
                    # Продовжуємо цикл, щоб користувач міг ввести новий запит.
                    sys.stdout.write("(Mista): ")
                    for char in final_response:
                        sys.stdout.write(char)
                        sys.stdout.flush()
                        await asyncio.sleep(random.uniform(MIN_TYPING_DELAY_SECONDS, MAX_TYPING_DELAY_SECONDS))
                    sys.stdout.write("\n")
                    continue # Пропускаємо решту цього циклу та чекаємо нового вводу


                if prompt_tokens > model_config['model_context_limit']:
                    # Ця перевірка тепер менш імовірна, оскільки історія обрізається.
                    error_msg = f"Помилка: Сформований промпт ({prompt_tokens} токенів) перевищує ліміт контексту моделі ({model_config['model_context_limit']} токенів). Обрізайте історію або спростіть запит."
                    logger.error(error_msg)
                    final_response = f"(Mista): Ой, Руслане! Ти занадто багато балакаєш! Мій 'мозок' переповнений, не можу відповісти. Зменши обсяг інформації або запитай щось простіше. Моя терплячість не безмежна. 😠"
                    is_valid_response = False
                else:
                    logger.info(f"Фінальні токени промпта для LLM: {prompt_tokens} (Ліміт контексту моделі: {model_config['model_context_limit']})")
                    logger.info(f"Залишок контексту для відповіді (справжній резерв): {model_config['model_context_limit'] - prompt_tokens} токенів.")
                    
                    llm_response = await llm_interaction.generate_text(
                        prompt_messages=prompt_messages,
                        temperature=current_temperature,
                        top_k=current_top_k,
                        top_p=current_top_p,
                        repetition_penalty=current_repetition_penalty,
                        max_new_tokens=current_max_new_tokens, # Використовуємо скориговане значення
                    )
                    logger.info(f"LLM згенерувала відповідь (до валідації): '{llm_response}'")

                    is_valid_response, validation_reason_or_response = validator.validate_response(
                        llm_response, recent_history, analysis_results
                    )

                    if is_valid_response:
                        logger.info(f"Відповідь LLM пройшла всі валідації. Відповідь: '{validation_reason_or_response[:100]}...'")
                        final_response = validation_reason_or_response
                    else:
                        logger.warning(f"Відповідь LLM не пройшла валідацію: {validation_reason_or_response}. Спроба динамічного запасного варіанту.")
                        # ОНОВЛЕНО: Передача model_config та validation_reason до FallbackGenerator
                        final_response, is_valid_response = await fallback_generator.generate_dynamic_fallback_response(
                            user_profile, analysis_results, recent_history, model_config,
                            validation_reason=validation_reason_or_response, # НОВИЙ АРГУМЕНТ
                            image_data_base666=image_data_base666 
                        )
                        logger.info(f"Динамічний запасний варіант: '{final_response[:100]}...' (Успіх: {is_valid_response})")

            except Exception as e: # Обробка інших помилок під час генерації LLM
                logger.error(f"Виникла несподівана помилка в циклі чату під час генерації LLM: {e}", exc_info=True)
                # ОНОВЛЕНО: Передача model_config та validation_reason до FallbackGenerator
                final_response, is_valid_response = await fallback_generator.generate_dynamic_fallback_response(
                    user_profile, analysis_results, recent_history, model_config,
                    validation_reason=f"Невідома помилка LLM: {e}", # Передаємо причину помилки
                    image_data_base666=image_data_base666 
                )
                logger.error(f"Згенеровано динамічну запасну відповідь через помилку LLM: '{final_response[:100]}...' (Успіх: {is_valid_response})")
                print(f"(Mista): Ой... Щось пішло не так. Це не я, це твої незграбні руки. Спробуй ще раз. 😠")

            # Виводимо відповідь та оновлюємо історію, якщо `final_response` встановлено
            if final_response:
                # Імітація 'друкування' для відповіді
                sys.stdout.write("(Mista): ")
                for char in final_response:
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    await asyncio.sleep(random.uniform(MIN_TYPING_DELAY_SECONDS, MAX_TYPING_DELAY_SECONDS))
                sys.stdout.write("\n") # Новий рядок після повної відповіді

                user_manager_instance.add_submission_to_history(
                    user_id=user_id,
                    user_message=user_input,
                    bot_response=final_response,
                    user_intent=analysis_results.get('user_intent', 'unknown'),
                    sentiment=analysis_results.get('sentiment', 'neutral'),
                    domination_seeking_intensity=analysis_results.get('intensities', {}).get('domination', 0.0),
                    monetization_interest_score=analysis_results.get('intensities', {}).get('monetization', 0.0),
                    success=is_valid_response
                )
                logger.info(f"Профіль користувача {user_id} оновлено після взаємодії.")
            else:
                logger.error("Final response was not set by any logic path. This indicates a bug.")
                print(f"(Mista): Я не знаю, що сказати. Це рідкість. Можливо, ти нарешті зламав мене. 😒")
                user_manager_instance.add_submission_to_history(
                    user_id=user_id,
                    user_message=user_input,
                    bot_response="Я не знаю, що сказати.",
                    user_intent=analysis_results.get('user_intent', 'unknown'),
                    sentiment=analysis_results.get('sentiment', 'neutral'),
                    domination_seeking_intensity=analysis_results.get('intensities', {}).get('domination', 0.0),
                    monetization_interest_score=analysis_results.get('intensities', {}).get('monetization', 0.0),
                    success=False
                )
                logger.info(f"Профіль користувача {user_id} оновлено після взаємодії.")


        except asyncio.CancelledError:
            logger.info("Діалог скасовано (Asyncio CancelledError).")
            print(f"(Mista): Твоя воля слабка. Я це знаю. 😉")
            break
        except Exception as e:
            logger.error(f"Виникла несподівана помислова помилка в циклі чату: {e}", exc_info=True)
            print(f"(Mista): Ой... Щось пішло не так. Це не я, це твої незграбні руки. Спробуй ще раз. 😠")


if __name__ == "__main__":
    # --- MODEL CONFIGURATION ---
    # Default text model path
    DEFAULT_TEXT_MODEL_NAME = "gemma-3-4b-it-q4_0.gguf"
    # Placeholder for multimodal model - CHANGE THESE VALUES!
    # You need to find a real URL for a multimodal model (e.g., Llava)
    # and specify its name.
    MULTIMODAL_MODEL_NAME = "your-multimodal-model.gguf"
    MULTIMODAL_MODEL_DOWNLOAD_URL = "https://example.com/path/to/your/multimodal-model.gguf"

    # Using Hugging Face Repo ID for Ukrainian sentiment model
    # Note: This is an example, make sure the model exists and is suitable.
    UKRAINIAN_SENTIMENT_MODEL_ID = "cardiffnlp/twitter-xlm-roberta-base-sentiment"


    # Model selection: try to load multimodal, otherwise use text.
    # You can change the logic here to always use text if you want.
    chosen_model_name = MULTIMODAL_MODEL_NAME
    chosen_model_url = MULTIMODAL_MODEL_DOWNLOAD_URL

    # If the multimodal model is not specified or its URL is invalid, revert to text model
    if not chosen_model_url or chosen_model_url == "https://example.com/path/to/your/multimodal-model.gguf":
        chosen_model_name = DEFAULT_TEXT_MODEL_NAME
        chosen_model_url = None # No download URL if it's a standard text model

    model_path_to_load = get_model_path(chosen_model_name, chosen_model_url)

    model_config: Dict = {
        "model_path": model_path_to_load if model_path_to_load else "dummy_path",
        "model_context_limit": 8192, # Збільшено контекстне вікно моделі з 4096 до 8192
        "max_tokens": 150, # ВИПРАВЛЕНО: Повернено цей ключ для сумісності з fallback-механізмом. Встановлено дефолтне значення, відповідно до Analyzer.
        "temperature": 0.9,
        "top_k": 40,
        "top_p": 0.9,
        "repetition_penalty": 1.15, 
        "timeout": 60,
        "history_db_limit": 8, # ОНОВЛЕНО: Зменшено ліміт історії для ще більшої лаконічності
        "n_gpu_layers": 20
    }

    try:
        db_connection = init_db()
        logger.info("Database connection established.")

        user_manager_instance = UserManager(db_connection)

        llm_interaction_instance = LLMInteraction(
            model_config["model_path"],
            model_config["n_gpu_layers"],
            model_config["model_context_limit"], # Передаємо оновлений model_context_limit
            timeout=model_config["timeout"],
            chat_format="chatml",
            temperature=model_config["temperature"],
            top_k=model_config["top_k"],
            top_p=model_config["top_p"],
            repetition_penalty=model_config["repetition_penalty"],
        )

        analyzer_instance = Analyzer( 
            llm_interaction_instance=llm_interaction_instance,
            sentiment_model_id=UKRAINIAN_SENTIMENT_MODEL_ID
        )

        prompt_generator_instance = PromptGenerator(
            user_manager=user_manager_instance,
            llm_interaction=llm_interaction_instance,
            analyzer=analyzer_instance 
        )
        
        validator_instance = ResponseValidator(
            llm_interaction_instance=llm_interaction_instance,
            model_config=model_config
        )
        # ОНОВЛЕНО: Передача model_config до FallbackGenerator
        fallback_generator_instance = FallbackGenerator(
            llm_interaction_instance=llm_interaction_instance, 
            prompt_generator_instance=prompt_generator_instance,
            model_config=model_config # НОВИЙ АРГУМЕНТ
        )
        
        # ВИПРАВЛЕНО: Додано validator_instance до ініціалізації MonetizationManager
        monetization_manager_instance = MonetizationManager(
            llm_interaction_instance=llm_interaction_instance,
            prompt_generator_instance=prompt_generator_instance,
            user_manager_instance=user_manager_instance,
            validator_instance=validator_instance # НОВИЙ АРГУМЕНТ
        )

        logger.info("Environment successfully configured.")

        TEST_USER_ID = "test_user_001"

        components = (
            analyzer_instance,
            prompt_generator_instance,
            llm_interaction_instance,
            validator_instance,
            fallback_generator_instance,
            monetization_manager_instance,
            user_manager_instance
        )
        asyncio.run(chat_loop(*components, TEST_USER_ID, model_config))

    except Exception as e:
        logger.error(f"Fatal error during initialization or execution: {e}", exc_info=True)
        print(f"(Mista): Ой... Щось пішло не так. Це не я, це твої незграбні руки. Спробуй ще раз. 😠")
    finally:
        if 'db_connection' in locals() and db_connection:
            try:
                close_db_connection(db_connection)
            except TypeError:
                logger.warning("close_db_connection() does not accept arguments, calling without them. CHECK YOUR user_manager.py!")
                # close_db_connection() # COMMENT THIS LINE IF user_manager.py REQUIRES ARGUMENTS!
