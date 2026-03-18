from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .config import DEFAULT_IGNORE


class Project(BaseModel):
    id: str
    name: str
    path: str
    ignore: List[str] = Field(default_factory=lambda: list(DEFAULT_IGNORE))
    created_at: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    packs: List[str] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    name: str
    path: str
    ignore: List[str] = Field(default_factory=list)


class PackInstallPayload(BaseModel):
    path: str
    name: Optional[str] = None
    overwrite: bool = False


class ProjectPacksPayload(BaseModel):
    packs: List[str]

class SearchRequest(BaseModel):
    project_id: str
    query: str
    k: int = 12


class SearchResult(BaseModel):
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: List[SearchResult] = Field(default_factory=list)


class SymbolSearchRequest(BaseModel):
    project_id: str
    query: str
    max_symbols: int = 10


class SupportingSymbol(BaseModel):
    symbol: str
    path: str
    start_line: int
    end_line: int
    kind: str


class SymbolHit(BaseModel):
    symbol: str
    name: str
    kind: str
    path: str
    start_line: int
    end_line: int
    score: float
    container: Optional[str] = None
    trace_step: Optional[int] = None
    supporting_symbol: Optional[SupportingSymbol] = None


class SymbolSearchResponse(BaseModel):
    symbols: List[SymbolHit] = Field(default_factory=list)


class ContextReadPlanRequest(BaseModel):
    project_id: str
    query: str
    max_tokens: int = 800
    max_symbols: int = 5
    max_lines: int = 120


class ContextReadPlanResponse(BaseModel):
    query: str
    max_tokens: int
    max_symbols: int
    max_lines: int
    entries: List[SymbolHit] = Field(default_factory=list)


class MaterializeContextRequest(BaseModel):
    project_id: str
    plan: ContextReadPlanResponse
    max_tokens: Optional[int] = None
    max_symbols: Optional[int] = None
    max_lines: Optional[int] = None


class MaterializedContextSection(BaseModel):
    title: str
    symbol: str
    path: str
    start_line: int
    end_line: int
    kind: str
    token_count: int
    line_count: int
    content: str


class MaterializedContextResponse(BaseModel):
    query: str
    token_count: int
    line_count: int
    truncated: bool = False
    content: str = ""
    sections: List[MaterializedContextSection] = Field(default_factory=list)


class FilePayload(BaseModel):
    path: str
    content: str


class PatchPayload(BaseModel):
    path: str
    patch: str


class NotesPayload(BaseModel):
    notes: List[str]


class Conversation(BaseModel):
    id: str
    title: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)


class ConversationState(BaseModel):
    conversations: List[Conversation] = Field(default_factory=list)
    active_id: Optional[str] = None


class ConversationCreate(BaseModel):
    id: str
    title: str


class ConversationAppend(BaseModel):
    id: str
    title: Optional[str] = None
    message: Dict[str, Any]


class ActiveConversationPayload(BaseModel):
    id: str
