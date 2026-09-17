from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from simcc.ai.schemas.clarification import (
    ClarificationPayload,
    ClarificationResponse,
)
from simcc.schemas.researcher import Researcher


class MariaResponse(BaseModel):
    query: str
    researchers: List[Researcher]


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    clarification_response: Optional[ClarificationResponse] = None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    filters_extracted: Dict[str, Any]
    researchers: List[Dict[str, Any]]
    productions: List[Dict[str, Any]]
    sources: List[str]
    telemetry: Optional[Dict[str, Any]] = None
    clarification: Optional[ClarificationPayload] = None
    global_metrics: Optional[Dict[str, Any]] = None


class ChatStreamEventType(str, Enum):
    STATUS = 'status'
    METADATA = 'metadata'
    DELTA = 'delta'
    CLARIFICATION = 'clarification'
    ERROR = 'error'
    DONE = 'done'
    TELEMETRY = 'telemetry'


class SearchUIMetadata(BaseModel):
    intent: str
    filters: Dict[str, Any]
    researchers: List[Dict[str, Any]]
    productions: List[Dict[str, Any]]
    sources: List[str]
    global_metrics: Optional[Dict[str, Any]] = None


class ChatStreamEvent(BaseModel):
    type: ChatStreamEventType
    message_id: str
    data: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    code: Optional[str] = None
    message: Optional[str] = None
    stage: Optional[str] = None
    clarification: Optional[ClarificationPayload] = None

