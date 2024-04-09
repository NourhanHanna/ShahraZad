from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, Request
from pydantic import BaseModel
from typing import Annotated
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
import os
import authentication
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import emails
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm


app = FastAPI()
models.Base.metadata.create_all(bind=engine)


class UserBase(BaseModel):
    username: str
    email: str
    password: str
    birth_date: str





def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


dp_dependency = Annotated[Session, Depends(get_db)]


@app.post("/register/", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserBase, dp: dp_dependency):
    user = models.User(
        username=user_data.username,
        email=user_data.email,
        password=authentication.get_password_hash(user_data.password),
        birth_date=datetime.strptime(user_data.birth_date, '%d-%m-%Y').date()
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
    #send_verification_email(user_data.email)

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
async def get_book_details(dp: dp_dependency, book_id: int):
    # Retrieve the specific book by book_id
    book = dp.query(models.Book).filter(models.Book.id == book_id).first()

    # Check if the book exists
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

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
    }

    return book_details


@app.put("/add_to_my_books/{book_id}")
async def add_to_my_books(dp: dp_dependency, book_id: int):
    # Retrieve the specific record by book_id
    book = dp.query(models.Book).filter(models.Book.id == book_id).first()

    # Check if the book exists
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Update the title field
    book.my_books = True

    # Commit the changes to the database
    dp.commit()

    return {"message": "The book added to my books successfully"}


@app.get("/get_my_books", response_model=list)
async def get_my_books(db: dp_dependency):
    # Query the database to retrieve books where my_books is True
    books = db.query(models.Book).filter(models.Book.my_books == True).all()

    # Construct a list of dictionaries with the desired information
    my_books_info_list = []
    for book in books:
        book_info = {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "cover_photo": book.cover_photo
        }
        my_books_info_list.append(book_info)

    return my_books_info_list



@app.post("/remove_from_my_books/{book_id}")
async def remove_from_my_books(dp: dp_dependency, book_id: int):
    # Retrieve the specific book by book_id
    book = dp.query(models.Book).filter(models.Book.id == book_id).first()

    # Check if the book exists
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Update the my_books field to False
    book.my_books = False

    # Commit the changes to the database
    dp.commit()

    return {"message": "Book removed from 'My Books'"}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


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
async def upload_file(file: UploadFile, dp: dp_dependency):
    path = "Data\\" + file.filename
    os.makedirs(path, exist_ok=True)

    contents = await file.read()

    file_path = os.path.join(path,"book_text.pdf")

    with open(file_path, "wb") as f:
        f.write(contents)

    book = models.Book(
        title=file.filename,
        cover_photo=path + '\\cover_photo.jpg',
        audio=path + '\\audio.wav',
        text=path + '\\book_text.pdf'
    )
    dp.add(book)
    dp.commit()

    return {"message": "File uploaded successfully"}


templates = Jinja2Templates(directory="Templates")


@app.get("/verification/", response_class=HTMLResponse)
async def email_verification(token: str, request: Request, dp: dp_dependency):
    user = await authentication.verify_token(token)

    if user:
        user = dp.query(models.User).filter(models.User.id == user.id).first()
        user.is_verified = True
        dp.commit()
        return templates.TemplateResponse("verification.html",
                                          {"request": request,"username": user.username})

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token or expired token",
        headers={"www.Authenticate": "Bear"}
    )
