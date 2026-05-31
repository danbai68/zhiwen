from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None


class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True