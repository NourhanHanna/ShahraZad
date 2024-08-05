from datetime import timedelta, datetime, timezone
from passlib.context import CryptContext
import models
from dotenv import dotenv_values
from fastapi import HTTPException, status,Depends, APIRouter, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
import jwt
import emails
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(
    prefix='/auth',
    tags=['Auth']
)

config_credentials = dotenv_values(".env")

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')
templates = Jinja2Templates(directory="Templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


dp_dependency = Annotated[Session, Depends(get_db)]


class CreateUserRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


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

        user = dp.query(models.User).filter(models.User.email==email).first()

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


class UserBase(BaseModel):
    username: str
    email: str
    password: str
    birthdate: str


@router.post("/register/", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserBase, dp: dp_dependency):
    user = models.User(
        username=user_data.username,
        email=user_data.email,
        password=hash_password(user_data.password),
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


@router.get("/verification/", response_class=HTMLResponse)
async def email_verification(token: str, request: Request, dp: dp_dependency):
    user = await verify_token(token, dp)

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


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], dp: dp_dependency):
    user = await authenticate_user(form_data.username, form_data.password, dp)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Could not validate user.")

    token = create_access_token(user.email, user.id, timedelta(days=30))

    return {"access_token": token, "token_type": "bearer"}


