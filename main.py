import base64
from os import mkdir
import time
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketException, status
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

user_tokens = {
    # "username,16 length random"
    "lee-donghyun,adsfasdfasdfasdf"
}


class Auth(BaseModel):
    token: str


@app.post("/authorize")
async def authorize(auth: Auth):
    if auth.token in user_tokens:
        return auth.token
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다."
        )


@app.websocket("/stream")
async def stream(websocket: WebSocket, token: Annotated[str | None, Query()]):
    # message 에 토큰 포함하도록, 그 토큰 디렉토리에 파일 검사하도록.
    if token not in user_tokens:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="유효하지 않은 토큰"
        )
    await websocket.accept()

    dir_name = "storage/" + token.split(",")[0]
    try:
        mkdir("storage")
    except:
        pass
    try:
        mkdir(dir_name)
    except:
        pass

    while True:
        data = await websocket.receive_text()
        video_bytes = base64.b64decode(data)

        with open(dir_name + "/" + str(time.time()) + ".mp4", "wb") as f:
            f.write(video_bytes)

        print("Received a video chunk")
