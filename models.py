from sqlalchemy import Boolean, Column, Integer, String, Date, ForeignKey, PrimaryKeyConstraint, Enum
from sqlalchemy.orm import relationship
from database import Base
from enum import Enum as PyEnum


class Language(PyEnum):
    ARABIC = "Arabic"
    DIACRITIZED_ARABIC = "Diacritized Arabic"
    ENGLISH = "English"

    @classmethod
    def from_str(cls, value):
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"'{value}' is not a valid value for {cls.__name__}")


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    password = Column(String(100), nullable=False)
    is_verified = Column(Boolean, default=False)
    birthdate = Column(Date)
    profile_photo = Column(String(200), default="Data\\default.jpg")

    # Relationship
    books = relationship("UserBook", back_populates="user")
    uploads = relationship("Upload", back_populates="user")


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
    child_audio = Column(String(200))
    female_audio = Column(String(200))
    male_audio = Column(String(200))
    text = Column(String(200))
    language = Column(Enum(Language), nullable=False, default=Language.ENGLISH)

    # Relationship
    users = relationship("UserBook", back_populates="book")
    book_voices = relationship("BookVoice", back_populates="book")
    book_voice_status = relationship("BookVoiceStatus", back_populates="book")


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
    configs = relationship("VoicesConfigs", back_populates="voice")
    book_voice_status = relationship("BookVoiceStatus", back_populates="voice")
    upload_voice_status = relationship("UploadVoiceStatus", back_populates="voice")
    upload_voices = relationship("UploadVoice", back_populates="voice")


class Upload(Base):
    __tablename__ = 'uploads'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String(50), index=True)
    cover_photo = Column(String(200), default="Data\\upload_cover_photo.jpg")
    male_audio = Column(String(200))
    male_audio_id = Column(String(200))
    female_audio = Column(String(200))
    female_audio_id = Column(String(200))
    child_audio = Column(String(200))
    child_audio_id = Column(String(200))

    text = Column(String(200))
    text_id = Column(String(200))
    drive_folder_link = Column(String(200))
    drive_folder_id = Column(String(200))

    language = Column(Enum(Language), nullable=False, default=Language.ENGLISH)

    user = relationship("User", back_populates="uploads")
    upload_voice_status = relationship("UploadVoiceStatus", back_populates="upload")
    upload_voices = relationship("UploadVoice", back_populates="upload")

    table_args = (
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


class VoicesConfigs(Base):
    __tablename__ = "voices_configs"

    voice_id = Column(Integer, ForeignKey('voices.id'), primary_key=True, index=True)
    transpose = Column(Integer,default=0)
    model_name = Column(String(200), nullable=False)

    # Relationships
    voice = relationship("Voice", back_populates="configs")


class BookVoiceStatus(Base):
    __tablename__ = 'book_voice_status'

    book_id = Column(Integer, ForeignKey('books.id'), primary_key=True)
    voice_id = Column(Integer, ForeignKey('voices.id'), primary_key=True)
    status = Column(Boolean, default=False)

    book = relationship("Book", back_populates="book_voice_status")
    voice = relationship("Voice", back_populates="book_voice_status")

    __table_args__ = (
        PrimaryKeyConstraint('book_id', 'voice_id'),
    )

    def __repr__(self):
        return f"<StoryVoice(story_id={self.story_id}, voice_id={self.voice_id}, audio_path='{self.audio_path}')>"


class UploadVoiceStatus(Base):
    __tablename__ = 'upload_voice_status'

    upload_id = Column(Integer, ForeignKey('uploads.id'), primary_key=True)
    voice_id = Column(Integer, ForeignKey('voices.id'), primary_key=True)
    status = Column(Boolean, default=False)

    upload = relationship("Upload", back_populates="upload_voice_status")
    voice = relationship("Voice", back_populates="upload_voice_status")

    __table_args__ = (
        PrimaryKeyConstraint('upload_id', 'voice_id'),
    )

    def __repr__(self):
        return f"<StoryVoice(story_id={self.story_id}, voice_id={self.voice_id}, audio_path='{self.audio_path}')>"


class UploadVoice(Base):
    __tablename__ = 'upload_voices'

    upload_id = Column(Integer, ForeignKey('uploads.id'), primary_key=True)
    voice_id = Column(Integer, ForeignKey('voices.id'), primary_key=True)
    audio = Column(String(200), nullable=False)
    audio_id = Column(String(200))

    upload = relationship("Upload", back_populates="upload_voices")
    voice = relationship("Voice", back_populates="upload_voices")

    __table_args__ = (
        PrimaryKeyConstraint('upload_id', 'voice_id'),
    )

    def __repr__(self):
        return f"<StoryVoice(story_id={self.upload_id}, voice_id={self.voice_id}, audio_path='{self.audio}')>"
