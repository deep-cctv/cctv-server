import base64
from fastapi import FastAPI, HTTPException, WebSocket
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

user_tokens= {
    # "username,16 length random"
    "lee-donghyun,adsfasdfasdfasdf"
}


class Auth(BaseModel):
    token:str

@app.post("/authorize")
async def authorize(auth:Auth):
    if auth.token in user_tokens:
        return auth.token
    else:
        raise HTTPException(status_code=401,detail="유효하지 않은 토큰입니다.")
    
@app.websocket('/stream')
async def stream(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        video_bytes = base64.b64decode(data)
        with open('received_chunk.mp4', 'ab') as f:
            f.write(video_bytes)
            f.close()
        print("Received a video chunk")