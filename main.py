import base64
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query, WebSocket
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
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")


@app.websocket("/stream")
async def stream(websocket: WebSocket, token: Annotated[str | None, Query()] = None):
    # message 에 토큰 포함하도록, 그 토큰 디렉토리에 파일 검사하도록.
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        video_bytes = base64.b64decode(data)
        with open("received_chunk.mp4", "wb") as f:
            f.write(video_bytes)
        print("Received a video chunk")
