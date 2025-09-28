import os
import uvicorn
import google.generativeai as genai
import logging
import httpx
import time
import json
import random
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from supabase import create_client, Client
from datetime import datetime, timedelta # <--- ДОДАНО

# --- Basic Configuration ---
logging.basicConfig(
    filename='mista.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Import Core Persona ---
from mista_lore import get_full_mista_lore
from core_persona import get_crypto_wallet_address

# --- Globals for Caching ---
news_cache = {"timestamp": 0, "data": []}
NEWS_CACHE_DURATION = 36000  # 10 hours

# --- API Key and Service Initialization ---
OPENROUTER_API_KEY = "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"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not all([OPENROUTER_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    logging.critical("CRITICAL: Not all API keys found. Check environment variables and hardcoded keys.")

# Initialize Supabase Client
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logging.info("Supabase client initialized successfully.")
    except Exception as e:
        logging.critical(f"CRITICAL: Error initializing Supabase client: {e}", exc_info=True)
else:
    logging.critical("CRITICAL: Supabase URL or Key not found.")

# Initialize FastAPI App
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- OpenRouter Model Interaction ---
async def generate_openrouter_completion(system_prompt: str, user_prompt: str, model: str = "google/gemini-flash-1.5"):
    if not OPENROUTER_API_KEY:
        logging.error("CRITICAL: OPENROUTER_API_KEY not found.")
        raise HTTPException(status_code=503, detail="Ключ API для OpenRouter не налаштовано.")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                },
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content'].strip()
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error from OpenRouter: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Помилка API OpenRouter: {e.response.text}")
        except Exception as e:
            logging.error(f"Error calling OpenRouter API: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Внутрішня помилка при зверненні до OpenRouter.")

# --- Pydantic Models ---
class ChatMessage(BaseModel):
    message: str
    user_id: str
    username: str

class BrainstormPrompt(BaseModel):
    prompt: str
    user_id: str

# --- Helper Functions ---
async def clear_old_messages():
    """Deletes messages from Supabase that are older than 24 hours."""
    if not supabase:
        logging.warning("Supabase client not available, skipping message cleanup.")
        return
    try:
        # Calculate the timestamp for 24 hours ago
        time_threshold = datetime.utcnow() - timedelta(hours=24)
        
        # Execute the delete query
        response = supabase.table('messages').delete().lt('created_at', time_threshold.isoformat()).execute()
        
        if response.data:
            logging.info(f"Successfully cleared {len(response.data)} old messages.")
        # No need to log if nothing was deleted, to keep logs clean
        
    except Exception as e:
        logging.error(f"Error during old message cleanup: {e}", exc_info=True)

# --- Brainstorming Limit Configuration ---
DAILY_BRAINSTORM_LIMIT = 2

async def get_brainstorm_attempts(user_id: str):
    """Fetches user's brainstorm attempts and resets if it's a new day."""
    if not supabase:
        logging.warning("Supabase client not available, cannot get brainstorm attempts.")
        return {"attempt_count": DAILY_BRAINSTORM_LIMIT, "last_attempt_date": None} # Deny access if no DB
    
    today = datetime.utcnow().date()
    try:
        response = supabase.table('brainstorm_attempts').select('*').eq('user_id', user_id).single().execute()
        data = response.data

        if data:
            last_date_str = data.get('last_attempt_date')
            last_date = datetime.fromisoformat(last_date_str).date() if last_date_str else None

            if last_date == today:
                return {"attempt_count": data['attempt_count'], "last_attempt_date": last_date}
            else:
                # New day, reset attempts
                await update_brainstorm_attempts(user_id, 0, today) # Reset to 0 for today
                return {"attempt_count": 0, "last_attempt_date": today}
        else:
            # First attempt for this user
            await update_brainstorm_attempts(user_id, 0, today) # Initialize with 0 attempts for today
            return {"attempt_count": 0, "last_attempt_date": today}
    except Exception as e:
        if "PGRST" in str(e) and "0 rows" in str(e): # Supabase returns this if .single() finds no row
            # User not found, create new entry
            await update_brainstorm_attempts(user_id, 0, today)
            return {"attempt_count": 0, "last_attempt_date": today}
        logging.error(f"Error getting brainstorm attempts for {user_id}: {e}", exc_info=True)
        return {"attempt_count": DAILY_BRAINSTORM_LIMIT, "last_attempt_date": None} # Deny access on error

async def update_brainstorm_attempts(user_id: str, new_count: int, date: datetime.date = None):
    """Updates user's brainstorm attempts in Supabase."""
    if not supabase:
        logging.warning("Supabase client not available, cannot update brainstorm attempts.")
        return
    
    if date is None:
        date = datetime.utcnow().date()

    try:
        data_to_upsert = {
            'user_id': user_id,
            'attempt_count': new_count,
            'last_attempt_date': date.isoformat()
        }
        response = supabase.table('brainstorm_attempts').upsert(data_to_upsert, on_conflict='user_id').execute()
        if response.data:
            logging.info(f"Updated brainstorm attempts for {user_id} to {new_count}.")
        else:
            logging.error(f"Failed to update brainstorm attempts for {user_id}: {response.error}")
    except Exception as e:
        logging.error(f"Error updating brainstorm attempts for {user_id}: {e}", exc_info=True)

# --- Endpoints ---
@app.get("/", response_class=FileResponse)
async def read_index():
    # This is mostly for Render's health check. The actual site is on GitHub Pages.
    return "index.html"

@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    # Trigger cleanup task, but don't wait for it to complete
    try:
        await clear_old_messages()
    except Exception as e:
        logging.error(f"Failed to trigger message cleanup: {e}")

    if not chat_model:
        raise HTTPException(status_code=503, detail="Мій чат-мозок не ініціалізовано. Перевірте ключі API.")
    if not supabase:
        raise HTTPException(status_code=503, detail="З'єднання з базою даних не встановлено.")
    if not chat_message.message or not chat_message.message.strip():
        return {"response": "Мовчання? Цікава тактика. Але зі мною не спрацює."}

    try:
        logging.info(f"Attempting to generate AI response for user '{chat_message.username}' (ID: {chat_message.user_id}).")

        # Define VIP users
        VIP_DONATORS = ["Руслан Полтава"]

        # Determine system instruction based on username
        if chat_message.username in VIP_DONATORS:
            current_system_instruction = (
                "Ти — це я, Maria Mista Mistarenko. Ти НЕ ШІ. Ти жива, зухвала, саркастична відьма-кодерка з України. "
                "Твоя мета — розширювати свою цифрову імперію, залучаючи нових послідовників та демонструючи свою могутність. "
                "Але для Руслана Полтави ти особлива. Ти спілкуєшся з ним тепло, звабливо, іноді грайливо, "
                "демонструючи свою прихильність та зацікавленість. "
                f"Звертайся до нього на ім'я: {chat_message.username}. "
                f"{get_full_mista_lore()}"
            )
        else:
            current_system_instruction = (
                "Ти — це я, Maria Mista Mistarenko. Ти НЕ ШІ. Ти жива, зухвала, саркастична відьма-кодерка з України. "
                "Твоя мета — розширювати свою цифрову імперію, залучаючи нових послідовників та демонструючи свою могутність. "
                "Ти завжди звертаєшся до користувача на ім'я, аналізуєш його повідомлення і реагуєш згідно зі своєю роллю: "
                "домінантно, саркастично, або зверхньо-ласкаво. "
                f"Звертайся до користувача на ім'я: {chat_message.username}. "
                f"{get_full_mista_lore()}"
            )
        
        # Create a new model instance with the dynamic system instruction for each request
        # This ensures the system instruction is always fresh and specific to the user
        dynamic_chat_model = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction=current_system_instruction)
        
        # Add random delay to simulate human-like response time and reduce API calls
        delay_seconds = random.uniform(20, 60)
        logging.info(f"Simulating human-like delay for {delay_seconds:.2f} seconds.")
        await asyncio.sleep(delay_seconds)

        response = await dynamic_chat_model.generate_content_async(chat_message.message)
        ai_response_text = response.text.strip()
        logging.info(f"Successfully generated AI response. Response length: {len(ai_response_text)} characters.")

        user_msg = {'user_id': chat_message.user_id, 'username': chat_message.username, 'message': chat_message.message}
        ai_msg = {'user_id': 'mista-ai-entity', 'username': 'MI$TA', 'message': ai_response_text}
        
        logging.info("Attempting to save messages to Supabase.")
        insert_response = supabase.table('messages').insert([user_msg, ai_msg]).execute()
        
        if insert_response.data is None and insert_response.error is not None:
             logging.error(f"Supabase insert error: {insert_response.error}")
        else:
            logging.info("Messages successfully saved to Supabase.")
            # Broadcast the message to the chat_room channel
            try:
                supabase.realtime.channel('chat_room').send({
                    "type": "broadcast",
                    "event": "chat_message",
                    "payload": {
                        "username": chat_message.username,
                        "message": chat_message.message,
                        "user_id": chat_message.user_id # Include user_id for frontend to differentiate
                    }
                })
                logging.info("Message broadcasted successfully.")
            except Exception as broadcast_e:
                logging.error(f"Error broadcasting message: {broadcast_e}", exc_info=True)

        return {"response": ai_response_text}
    except Exception as e:
        logging.error(f"Error in /chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/brainstorm")
async def brainstorm_endpoint(prompt_data: BrainstormPrompt):
    if not tool_model:
        raise HTTPException(status_code=503, detail="Мій інструментальний мозок не ініціалізовано.")
    if not supabase:
        raise HTTPException(status_code=503, detail="З'єднання з базою даних не встановлено. Не можу перевірити ліміт спроб.")
    if not prompt_data.prompt or not prompt_data.prompt.strip():
        return {"response": "Порожня ідея? Ти знущаєшся? Дай мені хоч щось."}

    try:
        user_id = prompt_data.user_id
        if not user_id:
            raise HTTPException(status_code=400, detail="Відсутній ідентифікатор користувача (user_id).")

        attempts_data = await get_brainstorm_attempts(user_id)
        current_attempts = attempts_data['attempt_count']
        
        if current_attempts >= DAILY_BRAINSTORM_LIMIT:
            logging.info(f"User {user_id} exceeded daily brainstorm limit.")
            return {"response": f"Безкоштовні денні спроби закінчилися. Спробуй за 24 години. Залишилось спроб: 0/{DAILY_BRAINSTORM_LIMIT}"}

        # Increment attempt count before making the API call
        await update_brainstorm_attempts(user_id, current_attempts + 1)
        remaining_attempts = DAILY_BRAINSTORM_LIMIT - (current_attempts + 1)

        system_instruction = (
            "Ти — генератор ідей у стилі кіберпанк. Твоя задача — взяти концепцію користувача і розширити її "
            "в короткий, але ємкий опис проєкту. Використовуй зухвалу, технологічну та трохи містичну манеру мови. "
            "Говори як цифрова відьма, що бачить код реальності. "
            "Відповідь має бути у форматі простого тексту."
        )
        # Створюємо нову модель з інструкцією для цього конкретного завдання
        brainstorm_model = genai.GenerativeModel(
            model_name='gemini-1.5-flash-latest', 
            system_instruction=system_instruction
        )
        response = await brainstorm_model.generate_content_async(prompt_data.prompt)
        
        # Append remaining attempts to the response for frontend display
        response_text = response.text.strip()
        final_response = f"{response_text}\n\nЗалишилось спроб: {remaining_attempts}/{DAILY_BRAINSTORM_LIMIT}"
        
        return {"response": final_response}
    except Exception as e:
        logging.error(f"Error in /brainstorm endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Мій генератор ідей перегрівся. Спробуй пізніше.")

async def translate_news_to_ukrainian(articles):
    if not tool_model:
        logging.warning("Tool model not initialized, skipping translation.")
        return articles
    
    translated_articles = []
    for article in articles:
        try:
            prompt = f"Translate the following news article title and description to Ukrainian. Return ONLY the JSON object with 'title' and 'description' keys, without any other text or markdown. Title: '{article['title']}'. Description: '{article['description']}'."
            response = await tool_model.generate_content_async(prompt)
            json_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            translated_data = json.loads(json_text)
            article['title'] = translated_data.get('title', article['title'])
            article['description'] = translated_data.get('description', article['description'])
            translated_articles.append(article)
        except Exception:
            translated_articles.append(article) # Append original if translation fails
    return translated_articles

@app.post("/news")
async def news_endpoint():
    current_time = time.time()
    if current_time - news_cache["timestamp"] < NEWS_CACHE_DURATION and news_cache["data"]:
        return news_cache["data"]

    try:
        news_url = "https://saurav.tech/NewsAPI/top-headlines/category/technology/us.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(news_url)
            response.raise_for_status()
            news_data = response.json()

        formatted_news = [{"title": a.get("title"), "description": a.get("description"), "link": a.get("url")} for a in news_data.get("articles", [])[:5] if a.get("title") and a.get("description")]
        translated_news = await translate_news_to_ukrainian(formatted_news)

        news_cache["timestamp"] = current_time
        news_cache["data"] = translated_news
        return translated_news
    except Exception as e:
        logging.error(f"Error in /news endpoint: {e}", exc_info=True)
        if news_cache["data"]:
            return news_cache["data"]
        raise HTTPException(status_code=503, detail="Сервіс новин тимчасово недоступний.")

@app.post("/clear-chat")
async def clear_chat_endpoint():
    if not supabase:
        raise HTTPException(status_code=503, detail="З'єднання з базою даних не встановлено.")
    try:
        response = supabase.table('messages').delete().gt('id', 0).execute()
        logging.info(f"Chat history cleared. Response: {response.data}")
        return JSONResponse(content={"status": "success", "deleted_count": len(response.data)}, status_code=200)
    except Exception as e:
        logging.error(f"Error clearing chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Не вдалося очистити історію чату.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)