from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

Base = declarative_base()

class Video(Base):
    __tablename__ = 'video'
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    cloudinary_url = Column(String(500), nullable=False)
    whisper_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    whisper_text = Column(Text)
