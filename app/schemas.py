from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    full_name: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    role: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None
    role: str | None = None


class UploadHistoryBase(BaseModel):
    image_path: str
    extracted_text: str


class UploadHistoryCreate(UploadHistoryBase):
    pass


class UploadHistoryOut(UploadHistoryBase):
    id: int
    user_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class OCRAnalysis(BaseModel):
    word_count: int
    sentence_count: int
    avg_word_length: float
    sentiment: str
    sentiment_polarity: float
    readability_score: float
    keywords: list[str]


class OCRExtractResponse(BaseModel):
    image_path: str
    extracted_text: str
    confidence_score: float
    engine_used: str
    analysis: OCRAnalysis


class AdminStatsOut(BaseModel):
    total_users: int
    total_uploads: int
