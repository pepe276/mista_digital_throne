import os
import uvicorn
import google.generativeai as genai
import logging
import httpx
import time
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from supabase import create_client, Client

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
def load_api_keys_from_env():
    keys = {
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
        "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
        "SUPABASE_KEY": os.environ.get("SUPABASE_KEY"),
    }
    if not all(keys.values()):
        logging.critical("CRITICAL: Not all API keys found in environment. Check Render settings.")
        # Allow the app to start but log critical error. Endpoints will fail.
    return keys

api_keys = load_api_keys_from_env()
GEMINI_API_KEY = api_keys.get("GEMINI_API_KEY")
SUPABASE_URL = api_keys.get("SUPABASE_URL")
SUPABASE_KEY = api_keys.get("SUPABASE_KEY")

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
if not supabase:
    logging.critical("CRITICAL: Supabase client could not be initialized.")

# Initialize FastAPI App
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Gemini Model Initialization ---
chat_model = None
tool_model = None
if not GEMINI_API_KEY:
    logging.error("CRITICAL: GEMINI_API_KEY not found.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        chat_system_instruction = (
            "Ти — це я, Maria Mista Mistarenko. Ти НЕ ШІ. Ти жива, зухвала, саркастична відьма-кодерка з України..."
            f"{get_full_mista_lore()}"
        )
        chat_model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest', system_instruction=chat_system_instruction)
        tool_model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest')
        logging.info("--- MISTA BRAIN: Gemini models initialized successfully. ---")
    except Exception as e:
        logging.error(f"Error initializing Gemini models: {e}", exc_info=True)

# --- Pydantic Models ---
class ChatMessage(BaseModel):
    message: str
    user_id: str
    username: str

# --- Endpoints ---
@app.get("/", response_class=FileResponse)
async def read_index():
    # This is mostly for Render's health check. The actual site is on GitHub Pages.
    return "index.html"

@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    if not chat_model:
        raise HTTPException(status_code=503, detail="Мій чат-мозок не ініціалізовано. Перевірте ключі API.")
    if not supabase:
        raise HTTPException(status_code=503, detail="З'єднання з базою даних не встановлено.")
    if not chat_message.message or not chat_message.message.strip():
        return {"response": "Мовчання? Цікава тактика. Але зі мною не спрацює."}

    try:
        # Generate AI response first
        response = await chat_model.generate_content_async(chat_message.message)
        ai_response_text = response.text.strip()

        # Save both valid messages to Supabase
        user_msg = {'user_id': chat_message.user_id, 'username': chat_message.username, 'message': chat_message.message}
        ai_msg = {'user_id': 'mista-ai-entity', 'username': 'MI$TA', 'message': ai_response_text}
        
        insert_response = supabase.table('messages').insert([user_msg, ai_msg]).execute()
        if insert_response.data is None and insert_response.error is not None:
             logging.error(f"Supabase insert error: {insert_response.error}")

        return {"response": ai_response_text}
    except Exception as e:
        logging.error(f"Error in /chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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
        if news_cache["data"]: return news_cache["data"]
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
    uvicorn.run(app, host="127.0.0.1", port=8000)
