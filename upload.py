import models
from fastapi import HTTPException, APIRouter, UploadFile, Depends
import os
from typing import Annotated
from sqlalchemy.orm import Session
from database import SessionLocal
from auth import get_current_user

router = APIRouter(
    prefix='/upload',
    tags=['Upload']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


dp_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post("/upload_file/")
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


@router.get("/get_my_uploads", response_model=list)
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


@router.post("/delete_upload/{upload_id}")
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

