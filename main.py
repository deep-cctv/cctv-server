import base64
from os import mkdir
import time
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketException, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    mkdir("storage")
except:
    pass
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

user_tokens = {
    # "username,16 length random"
    "lee-donghyun,adsfasdfasdfasdf",
    "kim-jinyoung,adsfasdfasdfasdf",
}
webhook_endpoints: dict[str, list[str]] = {}

monitors: dict[str, list[WebSocket]] = {}


async def detect_violation(file_name: str):
    return True


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
    dir_name = "storage/" + identifier + "/" + auth.client_name

    try:
        mkdir("storage/" + identifier)
    except:
        pass
    try:
        mkdir(dir_name)
    except:
        pass

    try:
        while True:
            data = await websocket.receive_text()
            video_bytes = base64.b64decode(data)

            file_name = dir_name + "/" + str(time.time()) + ".mp4"
            with open(file_name, "wb") as f:
                f.write(video_bytes)

            if identifier in monitors:
                for subscriber in monitors[identifier]:
                    await subscriber.send_json(
                        {
                            "type": "CLINET_DATA",
                            "client": {"uri": file_name, "name": auth.client_name},
                        }
                    )

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
