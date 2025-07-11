
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import os
import sys

# Add the parent directory to the path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_mista_bot import get_response # Assuming main_mista_bot can be refactored to have a get_response function

app = FastAPI()

class Message(BaseModel):
    user_id: str
    message: str

@app.post("/chat")
async def chat(message: Message):
    response = await get_response(message.user_id, message.message)
    return {"response": response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
