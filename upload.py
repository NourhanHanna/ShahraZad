from dotenv import dotenv_values
import models
from fastapi import HTTPException, APIRouter, UploadFile, Depends, status, BackgroundTasks
import os
from typing import Annotated
from sqlalchemy.orm import Session
from database import SessionLocal
from auth import get_current_user
from models import Language
from sqlalchemy.exc import SQLAlchemyError
import httpx
from googleapiclient.discovery import build
from google.oauth2 import service_account

router = APIRouter(
    prefix='/upload',
    tags=['Upload']
)

config_credentials = dotenv_values(".env")
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = config_credentials["SERVICE_ACCOUNT_FILE"]
PARENT_FOLDER_ID = config_credentials["PARENT_FOLDER_ID"]


def authenticate():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE,
                                                                  scopes=SCOPES)
    return creds


def create_drive_folder(folder_name: str):
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [PARENT_FOLDER_ID]
    }

    folder = service.files().create(
        body=file_metadata,
        fields="id, webViewLink"
    ).execute()

    return folder["id"], folder["webViewLink"]


def upload_file_to_drive(path: str, name: str, folder_id: str):
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        "name": name,
        "parents": [folder_id]
    }

    file = service.files().create(
        body=file_metadata,
        media_body=path,
        fields="id"
    ).execute()

    return file["id"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


dp_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post("/upload_file/{file_language}")
async def upload_file(file: UploadFile, file_language: str, dp: dp_dependency,
                      user: user_dependency, background_tasks: BackgroundTasks):
    path = os.path.join("Uploads", file.filename)
    print(path)
    os.makedirs(path, exist_ok=True)

    file_path = os.path.join(path, "book_text.pdf")
    print(file_path)
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        folder_id, folder_link = create_drive_folder(file.filename)
        file_link = upload_file_to_drive(file_path, "book_text.pdf", folder_id)

        book = models.Upload(
            user_id=user["id"],
            title=file.filename,
            male_audio=os.path.join(path, 'male.wav'),
            female_audio=os.path.join(path, 'female.wav'),
            child_audio=os.path.join(path, 'child.wav'),
            text=file_path,
            text_id=file_link,
            language=Language.from_str(file_language),
            drive_folder_link=folder_link,
            drive_folder_id=folder_id

        )
        dp.add(book)
        dp.commit()


        background_tasks.add_task(send_tts_request, book, book.female_audio, 1)
        background_tasks.add_task(send_tts_request, book, book.male_audio, 0)
        background_tasks.add_task(send_tts_request, book, book.child_audio, 2)


    except SQLAlchemyError as e:
        dp.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    except Exception as e:
        dp.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {"message": "File uploaded successfully"}


async def send_tts_request(book: models.Upload, output_path: str, gender: int):
    url = ""
    data = {}
    if book.language == models.Language.ENGLISH:
        url = "http://127.0.0.3:8000/TTS/"
        data = {
            "txt_path": book.text,
            "output_path": output_path,
            "gender": gender,
            "upload_id": book.id
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
            "diacritics": diacritics,
            "upload_id": book.id
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


@router.get("/get_my_uploads", response_model=list)
async def get_my_uploads(dp: dp_dependency, user: user_dependency):
    try:
        # Query the database to retrieve books where my_books is True
        user_uploads = dp.query(models.Upload).filter(models.Upload.user_id == user["id"]).all()

        # Construct a list of dictionaries with the desired information
        my_uploads_info_list = []
        for user_upload in user_uploads:
            book_info = {
                "id": user_upload.id,
                "title": user_upload.title,
                "text": user_upload.text_id,
                "cover_photo": user_upload.cover_photo
            }
            my_uploads_info_list.append(book_info)

        print(my_uploads_info_list)

        return my_uploads_info_list
    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.post("/delete_upload/{upload_id}")
async def delete_upload(upload_id: int, dp: dp_dependency, user: user_dependency):
    try:
        upload_voice_statuses = dp.query(models.UploadVoiceStatus).filter(
            models.UploadVoiceStatus.upload_id == upload_id
        ).all()
        for upload_voice_status in upload_voice_statuses:
            dp.delete(upload_voice_status)

        upload_voices = dp.query(models.UploadVoice).filter(
            models.UploadVoice.upload_id == upload_id
        ).all()
        for upload_voice in upload_voices:
            dp.delete(upload_voice)

        user_upload = dp.query(models.Upload).filter(
            models.Upload.user_id == user["id"],
            models.Upload.id == upload_id
        ).first()

        # Check if the book exists
        if not user_upload:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        dp.delete(user_upload)
        dp.commit()

        return {"message": "Book removed Successfully"}
    except SQLAlchemyError as e:
        dp.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.get("/get_upload_voice/")
async def get_upload_voice(book_id: int, voice_id: int, dp: dp_dependency):
    try:
        upload = dp.query(models.Upload).filter(
            models.Upload.id == book_id
        ).first()

        if not os.path.exists(upload.child_audio):
            return {"message": "Can't get this audio now, try again in hour"}

        if not os.path.exists(upload.female_audio):
            return {"message": "Can't get this audio now, try again in hour"}

        if not os.path.exists(upload.male_audio):
            return {"message": "Can't get this audio now, try again in hour"}


        upload_voice_status = dp.query(models.UploadVoiceStatus).filter(
            models.UploadVoiceStatus.upload_id == book_id,
            models.UploadVoiceStatus.voice_id == voice_id
        ).first()

        if not upload_voice_status:
            upload = dp.query(models.Upload).filter(
                models.Upload.id == book_id
            ).first()

            voice = dp.query(models.Voice).filter(
                models.Voice.id == voice_id
            ).first()

            # processing
            path = os.path.join(r"D:\Backend\ShahrZad\Uploads", upload.title, f"{voice.name}.wav")

            await generate_upload_voice(book_id, voice_id, path, dp)

            return {"message": "Processing"}

        if not upload_voice_status.status:
            return {"message": "Processing"}

        upload_voice = dp.query(models.UploadVoice).filter(
            models.UploadVoice.upload_id == book_id,
            models.UploadVoice.voice_id == voice_id
        ).first()

        return {"audio": upload_voice.audio_id}

    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


async def generate_upload_voice(upload_id: int, voice_id: int, out_path: str, dp: dp_dependency):
    try:

        upload = dp.query(models.Upload).filter(
            models.Upload.id == upload_id
        ).first()

        voice = dp.query(models.Voice).filter(
            models.Voice.id == voice_id
        ).first()

        configs = dp.query(models.VoicesConfigs).filter(
            (models.VoicesConfigs.voice_id == voice_id)
        ).first()

        audio = {
            "Male": upload.male_audio,
            "Female": upload.female_audio
        }.get(voice.gender, upload.child_audio)

        data = {
            "input_path": audio,
            "output_path": out_path,
            "transpose": configs.transpose,
            "model_name": configs.model_name,
            "upload_id": upload_id,
            "voice_id": voice_id,
            "is_book": False
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
