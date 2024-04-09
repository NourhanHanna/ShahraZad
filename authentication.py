from passlib.context import CryptContext
import models
import jwt
from dotenv import dotenv_values
from models import User
from fastapi import HTTPException, status

config_credentials = dotenv_values(".env")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(dp, email: str, password: str):
    user = dp.query(models.User).filter(models.User.email == email).first()

    if not user:
        return False

    if not verify_password(password, user.password):
        return False
    return user


async def verify_token(token: str):
    try:
        payload = jwt.decode(token, config_credentials["SECRET"], algorithms=["HS256"])
        user_id = payload.get("id")

        # Instantiate the User object synchronously
        user = User(id=user_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"www.Authenticate": "Bear"}
        )

    return user
