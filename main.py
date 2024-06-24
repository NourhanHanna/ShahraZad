from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, Request
from typing import Annotated
import models
import upload
from database import engine, SessionLocal
from sqlalchemy.orm import Session
import auth
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from dotenv import dotenv_values
from auth import get_current_user
import book

app = FastAPI()
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(book.router)
models.Base.metadata.create_all(bind=engine)


oauth2_schema = OAuth2PasswordBearer(tokenUrl='token')
config_credentials = dotenv_values(".env")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


dp_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@app.get("/get_audio/{book_id}", response_model=dict)
async def get_audio(dp: dp_dependency, book_id: int):
    # Retrieve the specific book by book_id
    book = dp.query(models.Book).filter(models.Book.id == book_id).first()

    # Check if the book exists
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book_info = {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "cover_photo": book.cover_photo,
        "audio": book.audio,
        "text": book.text
    }

    return book_info


@app.get("/", status_code=status.HTTP_200_OK)
async def user(cur_user: user_dependency, dp: dp_dependency):
    if cur_user is None:
        raise HTTPException(status_code=401, detail="Authentication Failed")
    return {"User": cur_user}


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


@app.get("/book_voice/")
async def get_book_voice(book_id: int, voice_id: int, db: dp_dependency):
    book_voice = db.query(models.BookVoice).filter(
        (models.BookVoice.book_id == book_id) &
        (models.BookVoice.voice_id == voice_id)).first()

    if not book_voice:
        raise HTTPException(status_code=404, detail="BookVoice record not found")

    return book_voice

