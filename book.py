from fastapi import HTTPException, Depends, APIRouter, status, BackgroundTasks
from typing import Annotated
import models
from database import SessionLocal
from sqlalchemy.orm import Session
from auth import get_current_user
from sqlalchemy.exc import SQLAlchemyError
import httpx
import os


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
    try:
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

    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.get("/get_book_details/{book_id}", response_model=dict)
async def get_book_details(dp: dp_dependency, user: user_dependency, book_id: int):
    try:
        book = dp.query(models.Book).filter(models.Book.id == book_id).first()

        # Check if the book exists
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        user_book = dp.query(models.UserBook).filter(
            models.UserBook.user_id == user["id"],
            models.UserBook.book_id == book_id
        ).first()
        my_books: bool = False
        if user_book:
            my_books = True

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
            "my_books": my_books
        }

        return book_details
    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.post("/add_to_my_books/{book_id}")
async def add_to_my_books(book_id: int, dp: dp_dependency, user: user_dependency):
    try:
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
    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.get("/get_my_books", response_model=list)
async def get_my_books(dp: dp_dependency, user: user_dependency):
    try:
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
                "text": book.text,
                "cover_photo": book.cover_photo
            }
            my_books_info_list.append(book_info)

        return my_books_info_list
    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.post("/remove_from_my_books/{book_id}")
async def remove_from_my_books(book_id: int, dp: dp_dependency, user: user_dependency):
    try:
        user_book = dp.query(models.UserBook).filter(
            (models.UserBook.book_id == book_id),
            (models.UserBook.user_id == user["id"])
        ).first()

        if not user_book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        dp.delete(user_book)
        dp.commit()

        return {"message": "Book removed Successfully"}
    except SQLAlchemyError as e:
        dp.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.get("/get_book_voice/")
async def get_book_voice(book_id: int, voice_id: int, dp: dp_dependency, background_tasks: BackgroundTasks ):
    try:
        book = dp.query(models.Book).filter(
            models.Book.id == book_id
        ).first()


        if not os.path.exists(book.child_audio):
            try:
                background_tasks.add_task(send_tts_request, book, book.child_audio, 2)
            except Exception as e:
                dp.rollback()
                return {"message": "Error"}
            return {"message": "Can't get this audio now, try again in an hour"}

        if not os.path.exists(book.female_audio):
            try:
                background_tasks.add_task(send_tts_request, book, book.female_audio, 1)
            except Exception as e:
                dp.rollback()
                return {"message": "Error"}
            return {"message": "Can't get this audio now, try again in an hour"}

        if not os.path.exists(book.male_audio):
            try:
                background_tasks.add_task(send_tts_request, book, book.male_audio, 0)
            except Exception as e:
                dp.rollback()
                return {"message": "Error"}
            return {"message": "Can't get this audio now, try again in an hour"}

        book_voice_status = dp.query(models.BookVoiceStatus).filter(
            (models.BookVoiceStatus.book_id == book_id),
            (models.BookVoiceStatus.voice_id == voice_id)
        ).first()

        if not book_voice_status:
            book = dp.query(models.Book).filter(
                models.Book.id == book_id
            ).first()

            voice = dp.query(models.Voice).filter(
                models.Voice.id == voice_id
            ).first()

            # processing
            path = os.path.join(r"D:\Backend\New folder", book.title, f"{voice.name}.mp3")

            await generate_book_voice(book_id, voice_id, path, dp)

            return {"message": "Processing"}

        if not book_voice_status.status:
            return {"message": "Processing"}

        book_voice = dp.query(models.BookVoice).filter(
            models.BookVoice.book_id == book_id,
            models.BookVoice.voice_id == voice_id
        ).first()

        return {"audio": book_voice.audio}

    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


async def generate_book_voice(book_id: int, voice_id: int, out_path: str, dp: dp_dependency):
    try:

        book = dp.query(models.Book).filter(
            models.Book.id == book_id
        ).first()

        voice = dp.query(models.Voice).filter(
            models.Voice.id == voice_id
        ).first()

        configs = dp.query(models.VoicesConfigs).filter(
            (models.VoicesConfigs.voice_id == voice_id)
        ).first()

        audio = {
            "Male": book.male_audio,
            "Female": book.female_audio
        }.get(voice.gender, book.child_audio)
        audio = os.path.join(r"C:\Users\K.M\StudioProjects\Prototype", audio)
        data = {
            "input_path": audio,
            "output_path": out_path,
            "transpose": configs.transpose,
            "model_name": configs.model_name,
            "upload_id": book_id,
            "voice_id": voice_id,
            "is_book": True
        }
        print(audio)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.2:8000/voice_changing/", params=data,
                timeout=300
            )
            response.raise_for_status()

        print(response)

    except SQLAlchemyError as e:
        dp.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    except httpx.HTTPStatusError as e:
        dp.rollback()
        raise HTTPException(status_code=e.response.status_code,
                            detail=f"Voice changing service error: {e.response.text}")
    except httpx.RequestError as e:
        dp.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Unable to connect to voice changing service: {e}")
    except httpx.TimeoutException:
        dp.rollback()
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                            detail="Voice changing service request timed out")


async def send_tts_request(book: models.Book, output_path: str, gender: int):
    url = ""
    data = {}
    if book.language == models.Language.ENGLISH:
        url = "http://127.0.0.3:8000/TTS/"
        data = {
            "txt_path": book.text,
            "output_path": output_path,
            "gender": gender
        }
    else:
        diacritics = True
        if book.language == models.Language.DIACRITIZED_ARABIC:
            diacritics = False
        url = "http://127.0.0.4:8000/TTSArabic/"
        data = {
            "txt_path": book.text,
            "output_path": output_path,
            "gender": gender,
            "diacritics": diacritics
        }

    try:

        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=data, timeout=300)
        response.raise_for_status()
        return response

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"TTS service error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Unable to connect to TTS service: {e}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="TTS service request timed out")



