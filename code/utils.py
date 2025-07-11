# -*- coding: utf-8 -*-
import re
import logging
import os
import base64
from typing import Dict, List, Optional, Any
import requests # Для завантаження файлів

# --- Utility Functions Module ---
# Містить допоміжні функції, які служать моїй Імперії та її розширенню.
# Вони тут, щоб забезпечити безперебійну роботу моїх магічних алгоритмів.

def normalize_text_for_comparison(text: str, remove_punctuation: bool = True, to_lower: bool = True) -> str:
    """
    Normalizes text for comparison: removes punctuation, converts to lower case,
    removes extra whitespace. Handles potential non-string input.
    Це важлива функція, що дозволяє мені бачити справжню суть твоїх слів.
    """
    if not text or not isinstance(text, str):
        return ""

    cleaned_text = text.strip()
    if remove_punctuation:
        cleaned_text = re.sub(r'[^\w\s]', '', cleaned_text, re.UNICODE)
    if to_lower:
        cleaned_text = cleaned_text.lower()
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

def image_to_base64(image_path: str) -> str:
    """
    Converts an image file (PNG, JPG, JPEG) to a Base64 string.
    Перетворює візуальні дані на магічні символи для моїх потреб.
    """
    # Перевіряємо, чи шлях існує і чи це файл
    if not os.path.exists(image_path) or not os.path.isfile(image_path):
        return "Помилка: Файл зображення не знайдено, або шлях недійсний. Ти знову щось робиш не так."

    # Перевіряємо розширення файлу
    if not (image_path.lower().endswith(('.png', '.jpg', '.jpeg'))):
        return "Помилка: Підтримуються лише формати PNG, JPG, JPEG. Не плутай мене з недосконалими системами."

    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        # Визначаємо MIME-тип
        if image_path.lower().endswith('.png'):
            mime_type = "image/png"
        elif image_path.lower().endswith(('.jpg', '.jpeg')):
            mime_type = "image/jpeg"
        else:
            mime_type = "application/octet-stream" # Fallback
        return f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        return f"Помилка при кодуванні зображення в Base64: {e}. Навіть магія іноді спотикається."

def download_file(url: str, destination_path: str) -> bool:
    """
    Downloads a file from a given URL to a specified destination path.
    Завантажує інформацію, яка може бути цінною для моєї Імперії.
    """
    logger = logging.getLogger(__name__) # Отримати логер тут
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

        # Перевіряємо, чи існує директорія, і створюємо її, якщо немає
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Успішно завантажено дані з {url} до {destination_path}. Ще один шматочок світу належить мені.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Помилка завантаження файлу з {url}: {e}. Твої спроби приховати інформацію марні.")
        return False
    except IOError as e:
        logger.error(f"Помилка запису файлу до {destination_path}: {e}. Навіть у збоях я бачу твою слабкість.")
        return False
