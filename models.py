from sqlalchemy import Boolean, Column, Integer, String, Date, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    password = Column(String(100), nullable=False)
    is_verified = Column(Boolean, default=False)
    birthdate = Column(Date)
    profile_photo = Column(String, default="Data\\default.jpg")

    # Relationship
    books = relationship("UserBook", back_populates="user")
    uploads = relationship("UserUpload", back_populates="user")


class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(50), index=True)
    cover_photo = Column(String(200))
    author = Column(String(50), default="Undefined")
    publish_year = Column(Integer, default="0")
    category = Column(String(50))
    ISBN = Column(String(50), index=True, default="Undefined")
    description = Column(String(500), default=".")
    audio = Column(String(200))
    text = Column(String(200))

    # Relationship
    users = relationship("UserBook", back_populates="book")
    book_voices = relationship("BookVoice", back_populates="book")


class UserBook(Base):
    __tablename__ = 'user_books'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    book_id = Column(Integer, ForeignKey('books.id'), primary_key=True)

    user = relationship("User", back_populates="books")
    book = relationship("Book", back_populates="users")

    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'book_id'),
    )


class Voice(Base):
    __tablename__ = 'voices'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    photo = Column(String(200))
    gender = Column(String(10), nullable=False)
    audio = Column(String(200))

    # Relationships
    story_voices = relationship("BookVoice", back_populates="voice")


class UserUpload(Base):
    __tablename__ = 'user_uploads'

    upload_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String(50), index=True)
    cover_photo = Column(String(200), default="Data\\upload_cover_photo.jpg")
    audio = Column(String(200))
    text = Column(String(200))

    user = relationship("User", back_populates="uploads")

    __table_args__ = (
        PrimaryKeyConstraint('upload_id'),
    )


class BookVoice(Base):
    __tablename__ = 'book_voices'

    book_id = Column(Integer, ForeignKey('books.id'), primary_key=True)
    voice_id = Column(Integer, ForeignKey('voices.id'), primary_key=True)
    audio = Column(String(200), nullable=False)

    book = relationship("Book", back_populates="book_voices")
    voice = relationship("Voice", back_populates="story_voices")

    __table_args__ = (
        PrimaryKeyConstraint('book_id', 'voice_id'),
    )

    def __repr__(self):
        return f"<StoryVoice(story_id={self.story_id}, voice_id={self.voice_id}, audio_path='{self.audio_path}')>"