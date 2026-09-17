from enum import Enum
from typing import Dict, List, Optional
from dataclasses import Field, dataclass, field
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Pageination


class DocumentStatus(str, Enum):
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    status: str
    tenant_id: int
    category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentResponseList(BaseModel):
    data: List[DocumentResponse]
    pagination: Pageination


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None


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
