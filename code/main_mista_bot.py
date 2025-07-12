# -*- coding: utf-8 -*-
import logging
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# --- Налаштування логування ---
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_filename = os.path.join(log_dir, f"mista_bot_{__name__}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# --- Конфігурація Gemini ---
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

async def get_response(user_id: str, user_input: str) -> str:
    try:
        response = model.generate_content(user_input)
        return response.text
    except Exception as e:
        logger.error(f"Error getting response from Gemini: {e}")
        return "Я... я не можу відповісти. Щось пішло не так."