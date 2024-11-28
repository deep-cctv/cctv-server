from concurrent.futures import ThreadPoolExecutor
import os
import asyncio
import base64
from os import mkdir
import time
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketException, status
from fastapi.staticfiles import StaticFiles
import httpx
import numpy as np
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from collections import deque
import cv2
from tensorflow.keras.models import load_model

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory for all relative paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
MODEL_DIR = os.path.join(BASE_DIR, "model")
MODEL_FILE = os.path.join(MODEL_DIR, "model.h5")

# Ensure necessary directories exist
os.makedirs(STORAGE_DIR, exist_ok=True)
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

user_tokens = {
    # "username,16 length random"
    "lee-donghyun,adsfasdfasdfasdf",
    "kim-jinyoung,adsfasdfasdfasdf",
    "sejong,token",
}
webhook_endpoints: dict[str, list[str]] = {}

monitors: dict[str, list[WebSocket]] = {}

executor = ThreadPoolExecutor()
model = load_model(MODEL_FILE)


async def detect_violation(file_name: str):
    def blocking_task():
        Q = deque(maxlen=128)
        vs = cv2.VideoCapture(file_name)
        while True:
            (grabbed, frame) = vs.read()
            if not grabbed:
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (128, 128)).astype("float32")
            frame = frame.reshape(128, 128, 3) / 255
            preds = model.predict(np.expand_dims(frame, axis=0))[0]
            Q.append(preds)
        vs.release()
        return np.array(Q).mean(axis=0)[0] > 0.5

    return await asyncio.get_running_loop().run_in_executor(executor, blocking_task)


background_tasks = set()


def create_task(coroutine):
    task = asyncio.create_task(coroutine)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


async def send_to_monitor(identifier: str, data: dict):
    if identifier in monitors:
        for subscriber in monitors[identifier]:
            await subscriber.send_json(data)


class Auth(BaseModel):
    token: str
    client_name: str


@app.post("/authorize")
async def authorize(auth: Auth):
    if auth.token in user_tokens:
        return auth.token
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다."
        )


@app.websocket("/stream")
async def stream(websocket: WebSocket, auth: Annotated[Auth, Query()]):
    if auth.token not in user_tokens:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="유효하지 않은 토큰"
        )

    await websocket.accept()

    identifier = auth.token.split(",")[0]
    client_dir = os.path.join(STORAGE_DIR, identifier, auth.client_name)
    os.makedirs(client_dir, exist_ok=True)

    try:
        while True:
            data = await websocket.receive_text()
            video_bytes = base64.b64decode(data)

            timestamp = time.time()
            file_name = os.path.join(client_dir, f"{timestamp}.mp4")
            with open(file_name, "wb") as f:
                f.write(video_bytes)

            create_task(
                send_to_monitor(
                    identifier,
                    {
                        "type": "CLINET_DATA",
                        "client": {
                            "uri": f"storage/{identifier}/{auth.client_name}/{timestamp}.mp4",
                            "name": auth.client_name,
                        },
                    },
                )
            )

            async def detectVideo():
                violated = await detect_violation(file_name)
                if violated:
                    await send_to_monitor(
                        identifier, {"type": "ALERT", "name": auth.client_name}
                    )
                    if identifier in webhook_endpoints:
                        async with httpx.AsyncClient() as client:
                            for endpoint in webhook_endpoints[identifier]:
                                try:
                                    await client.get(endpoint)
                                except:
                                    pass

            create_task(detectVideo())
            print("Received a video chunk", identifier, file_name)

    except WebSocketException:
        print(f"Client disconnected for token: {identifier}")
    finally:
        if identifier in monitors:
            for subscriber in monitors[identifier]:
                await subscriber.send_json(
                    {"type": "CLIENT_EXIT", "name": auth.client_name}
                )


@app.websocket("/monitor")
async def monitor(websocket: WebSocket, token: Annotated[str | None, Query()]):
    if token not in user_tokens:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="유효하지 않은 토큰"
        )
    await websocket.accept()

    identifier = token.split(",")[0]
    if identifier not in monitors:
        monitors[identifier] = []
    monitors[identifier].append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketException:
        print(f"Subscriber disconnected for token: {identifier}")
    finally:
        monitors[identifier].remove(websocket)
        if not monitors[identifier]:
            del monitors[identifier]


class Webhook(BaseModel):
    token: str
    endpoint: str


@app.get("/alert-webhook")
async def alert_webhook(webhook: Annotated[Webhook, Query()]):
    if webhook.token not in user_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다."
        )
    identifier = webhook.token.split(",")[0]
    if identifier not in webhook_endpoints:
        webhook_endpoints[identifier] = []
    webhook_endpoints[identifier].append(webhook.endpoint)
    return "Webhook registered"
