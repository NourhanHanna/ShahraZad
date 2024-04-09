
from sqlalchemy import Boolean, Column, Integer, String, Date, LargeBinary
from database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    password = Column(String(100), nullable=False)
    is_verified = Column(Boolean, default=False)
    birth_date = Column(Date)


class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(50), index=True)
    cover_photo = Column(String(200))
    author = Column(String(50), default="Undefined")
    publish_year = Column(Integer, default="0")
    category = Column(String(50))
    ISBN = Column(String(50), index=True, default="Undefined")
    description = Column(String(500),default=".")
    audio = Column(String(200))
    my_books = Column(Boolean, default=False)
    text = Column(String(200))


