from fastapi import FastAPI, HTTPException, Response
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
async def authorize(auth:Auth,response:Response):
    if auth.token in user_tokens:
        response.set_cookie(key="token",value=auth.token)
        return auth.token
    else:
        raise HTTPException(status_code=401,detail="유효하지 않은 토큰입니다.")