from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, Request
from pydantic import BaseModel
from typing import Annotated
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
import os
import auth
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import emails
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from dotenv import dotenv_values
from auth import get_current_user

app = FastAPI()
models.Base.metadata.create_all(bind=engine)


oauth2_schema = OAuth2PasswordBearer(tokenUrl='token')
config_credentials = dotenv_values(".env")
templates = Jinja2Templates(directory="Templates")


class UserBase(BaseModel):
    username: str
    email: str
    password: str
    birthdate: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


dp_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@app.post("/register/", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserBase, dp: dp_dependency):
    user = models.User(
        username=user_data.username,
        email=user_data.email,
        password=auth.hash_password(user_data.password),
        birthdate=datetime.strptime(user_data.birthdate, '%d/%m/%Y').date()
    )
    temp_user = dp.query(models.User).filter(models.User.email==user.email).first()

    if temp_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An account already exists with this email.")

    try:
        dp.add(user)
        dp.commit()
    except Exception as e:
        dp.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    user = dp.query(models.User).filter(user.email==models.User.email).first()

    # Send verification email
    try:
        await emails.send_email([user.email], user)
    except Exception as e:
        dp.delete(user)
        dp.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {"message": "User registered successfully. Please check your email to verify your account."}


@app.get("/get_all_books/")
async def get_all_books(dp: dp_dependency):
    books = dp.query(models.Book).all()
    book_info_list = []
    for book in books:
        book_info = {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "publish_year": book.publish_year,
            "category": book.category,
            "cover_photo": book.cover_photo
        }
        book_info_list.append(book_info)

    return book_info_list


@app.get("/get_book_details/{book_id}", response_model=dict)
async def get_book_details(dp: dp_dependency, user:user_dependency, book_id: int):
    # Retrieve the specific book by book_id
    book = dp.query(models.Book).filter(models.Book.id == book_id).first()

    # Check if the book exists
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    user_book=user_book = dp.query(models.UserBook).filter(
        models.UserBook.user_id == user["id"],
        models.UserBook.book_id == book_id
    ).first()
    my_books:bool =False;
    if user_book:
        my_books=True

    # Return the details of the book
    book_details = {
        "id": book.id,
        "title": book.title,
        "cover_photo": book.cover_photo,
        "author": book.author,
        "publish_year": book.publish_year,
        "category": book.category,
        "ISBN": book.ISBN,
        "description": book.description,
        "audio": book.audio,
        "my_books": my_books
    }

    return book_details


@app.post("/add_to_my_books/{book_id}")
async def add_to_my_books(book_id: int, dp: dp_dependency, user: user_dependency):
    # Retrieve the specific book by book_id
    book = dp.query(models.Book).filter(models.Book.id == book_id).first()

    # Check if the book exists
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if the book is already in the user's collection
    user_book = dp.query(models.UserBook).filter(
        models.UserBook.user_id == user["id"],
        models.UserBook.book_id == book_id
    ).first()

    if user_book:
        raise HTTPException(status_code=400, detail="Book already in user's collection")

    # Add the book to the user's collection
    user_book = models.UserBook(user_id=user["id"], book_id=book_id)
    dp.add(user_book)
    dp.commit()

    return {"message": "The book added to your collection successfully"}


@app.get("/get_my_books", response_model=list)
async def get_my_books(dp: dp_dependency, user: user_dependency):
    # Query the database to retrieve books where my_books is True
    user_books = dp.query(models.UserBook).filter(models.UserBook.user_id == user["id"]).all()

    # Construct a list of dictionaries with the desired information
    my_books_info_list = []
    for user_book in user_books:
        book = dp.query(models.Book).filter(models.Book.id == user_book.book_id).first()
        book_info = {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "cover_photo": book.cover_photo
        }
        my_books_info_list.append(book_info)

    return my_books_info_list


@app.post("/remove_from_my_books/{book_id}")
async def remove_from_my_books(book_id: int, dp: dp_dependency, user: user_dependency):
    # Retrieve the specific book by book_id
    book = dp.query(models.Book).filter(models.Book.id == book_id).first()

    # Check if the book exists
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if the book is in the user's collection
    user_book = dp.query(models.UserBook).filter(
        models.UserBook.user_id == user["id"],
        models.UserBook.book_id == book_id
    ).first()

    if not user_book:
        raise HTTPException(status_code=400, detail="Book not in user's collection")

    # Remove the book from the user's collection
    dp.delete(user_book)
    dp.commit()

    return {"message": "Book removed from your collection"}


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


@app.post("/upload_file/")
async def upload_file(file: UploadFile, dp: dp_dependency, user: user_dependency):
    path = "Uploads\\" + file.filename
    os.makedirs(path, exist_ok=True)

    contents = await file.read()

    file_path = os.path.join(path, "book_text.pdf")

    with open(file_path, "wb") as f:
        f.write(contents)

    book = models.UserUpload(
        user_id=user["id"],
        title=file.filename,
        audio=path + '\\audio.wav',
        text=path + '\\book_text.pdf'
    )
    dp.add(book)
    dp.commit()

    return {"message": "File uploaded successfully"}


@app.get("/get_my_uploads", response_model=list)
async def get_my_uploads(dp: dp_dependency, user: user_dependency):
    # Query the database to retrieve books where my_books is True
    user_uploads = dp.query(models.UserUpload).filter(models.UserUpload.user_id == user["id"]).all()

    # Construct a list of dictionaries with the desired information
    my_uploads_info_list = []
    for user_upload in user_uploads:
        book_info = {
            "id": user_upload.upload_id,
            "title": user_upload.title,
            "audio": user_upload.audio,
            "text": user_upload.text,
            "cover_photo": user_upload.cover_photo
        }
        my_uploads_info_list.append(book_info)

    return my_uploads_info_list


@app.post("/delete_upload/{upload_id}")
async def delete_upload(upload_id: int, dp: dp_dependency, user: user_dependency):
    user_upload = dp.query(models.UserUpload).filter(
        models.UserUpload.user_id == user["id"],
        models.UserUpload.upload_id == upload_id
    ).first()

    # Check if the book exists
    if not user_upload:
        raise HTTPException(status_code=404, detail="Book not found")

    dp.delete(user_upload)
    dp.commit()

    return {"message": "Book removed Successfully"}


@app.get("/verification/", response_class=HTMLResponse)
async def email_verification(token: str, request: Request, dp: dp_dependency):
    user = await auth.verify_token(token, dp)

    if user:
        user = dp.query(models.User).filter(models.User.id == user.id).first()
        user.is_verified = True
        dp.commit()
        return templates.TemplateResponse("verification.html",
                                          {"request": request, "username": user.username})

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token or expired token",
        headers={"www.Authenticate": "Bear"}
    )


@app.post("/token", response_model=auth.Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], dp: dp_dependency):
    user = await auth.authenticate_user(form_data.username, form_data.password, dp)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Could not validate user.")
    token = auth.create_access_token(user.email, user.id, timedelta(days=30))

    return {"access_token": token, "token_type": "bearer"}


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


@app.get("/bookvoice/")
async def get_book_voice(book_id: int, voice_id: int, db: dp_dependency):
    book_voice = db.query(models.BookVoice).filter(
        (models.BookVoice.book_id == book_id) &
        (models.BookVoice.voice_id == voice_id)).first()

    if not book_voice:
        raise HTTPException(status_code=404, detail="BookVoice record not found")

    return book_voice
