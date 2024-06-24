from fastapi import HTTPException, Depends, APIRouter
from typing import Annotated
import models
from database import SessionLocal
from sqlalchemy.orm import Session
from auth import get_current_user

router = APIRouter(
    prefix='/book',
    tags=['Book']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


dp_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/get_all_books/")
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


@router.get("/get_book_details/{book_id}", response_model=dict)
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


@router.post("/add_to_my_books/{book_id}")
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


@router.get("/get_my_books", response_model=list)
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


@router.post("/remove_from_my_books/{book_id}")
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

