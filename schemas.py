from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MemoCreate(BaseModel):
    title: str
    content: str
    tags: Optional[str] = ""
    is_favorite: Optional[bool] = False

class MemoUpdate(BaseModel):
    title: str
    content: str
    tags: Optional[str] = ""
    is_favorite: Optional[bool] = False

class MemoResponse(BaseModel):
    id: int
    title: str
    content: str
    tags: str
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
