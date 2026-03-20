from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from database import Base

class Memo(Base):
    __tablename__ = "memos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(String(500), default="")
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
