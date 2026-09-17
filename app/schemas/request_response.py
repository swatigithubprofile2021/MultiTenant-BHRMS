from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from datetime import datetime


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HRPolicy:
    """Represents an HR policy document"""

    id: str
    filename: str
    title: str
    category: str  # e.g., "leave_policy", "code_of_conduct", "benefits"
    upload_date: datetime
    status: DocumentStatus
    chunk_count: int = 0
    metadata: Dict = field(default_factory=dict)
    file_hash: str = ""


class QueryFilters(BaseModel):
    category: Optional[str] = ""


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    session_id: Optional[str] = None
    filters: Optional[QueryFilters] = (
        QueryFilters()
    )  # e.g., {"category": "leave_policy"}
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence_score: float = 0.0
    status: str = "Uncertain"
    metrics: dict = dict()
    processing_time_ms: float
    session_id: str


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str
