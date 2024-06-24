
from datetime import timedelta, datetime, timezone

from passlib.context import CryptContext

import models
from dotenv import dotenv_values
from fastapi import HTTPException, status,Depends, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
import jwt

config_credentials = dotenv_values(".env")

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='token')


class CreateUserRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


dp_dependency = Annotated[Session, Depends(get_db)]


def hash_password(password: str):
    return bcrypt_context.hash(password)


def verify_password(password, hashed_password):
    return bcrypt_context.verify(password, hashed_password)


async def authenticate_user(email: str, password: str, dp):
    user = dp.query(models.User).filter(models.User.email == email).first()

    if not user:
        return False

    if not verify_password(password, user.password):
        return False

    if not user.is_verified:
        return False

    return user


async def verify_token(token: str, dp):
    try:
        payload = jwt.decode(token, config_credentials["SECRET"], algorithms=["HS256"])
        user_id = payload.get("id")
        user = dp.query(models.User).filter(models.User.id == user_id).first()
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"www.Authenticate": "Bear"}
        )

    return user


def create_access_token(email: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': email, 'id': user_id}
    expire = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expire})
    return jwt.encode(encode, config_credentials["SECRET"], algorithm=config_credentials["ALGORITHM"])


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)], dp: dp_dependency):
    try:
        payload = jwt.decode(token, config_credentials["SECRET"], algorithms=config_credentials["ALGORITHM"])
        email: str = payload.get("sub")
        user_id: int = payload.get("id")
        if email is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Could not validate user.")

        user=dp.query(models.User).filter(models.User.email==email).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Could not validate user.")

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "birthdate": user.birthdate,
            "profile_photo": user.profile_photo
        }
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Could not validate user.")

