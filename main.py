from fastapi import FastAPI, HTTPException, Depends, status
from typing import Annotated
import models
import upload
from database import engine, SessionLocal
from sqlalchemy.orm import Session
import auth
from dotenv import dotenv_values
from auth import get_current_user
import book

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

config_credentials = dotenv_values(".env")

app.include_router(auth.router)
app.include_router(book.router)
app.include_router(upload.router)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


dp_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@app.get("/", response_model=dict, status_code=status.HTTP_200_OK)
async def user(cur_user: user_dependency):
    if cur_user is None:
        raise HTTPException(status_code=401, detail="Authentication Failed")

    user_details = {
      "id": cur_user["id"],
      "username": cur_user["username"],
      "email": cur_user["email"],
      "birthdate": str(cur_user["birthdate"]),
      "profile_photo": cur_user["profile_photo"],
    }

    return user_details


@app.get("/get_all_voices/")
async def get_all_voices(dp: dp_dependency):
    voices = dp.query(models.Voice).all()
    voices_info_list = []
    for voice in voices:
        voice_info = {
            "id": voice.id,
            "name": voice.name,
            "photo": voice.photo,
            "gender": voice.gender,
            "audio": voice.audio
        }
        voices_info_list.append(voice_info)

    return voices_info_list

