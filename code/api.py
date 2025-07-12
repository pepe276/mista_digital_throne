# -*- coding: utf-8 -*-
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import asyncio
from main_mista_bot import get_response

app = FastAPI()

@app.post("/chat")
async def chat(request: dict):
    user_id = request.get("user_id")
    message = request.get("message")
    if not user_id or not message:
        return JSONResponse(content={"error": "user_id and message are required"}, status_code=400)

    response = await get_response(user_id, message)
    return JSONResponse(content={"response": response})

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    while True:
        message = await websocket.receive_text()
        response = await get_response(user_id, message)
        await websocket.send_text(response)