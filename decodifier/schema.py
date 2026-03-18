from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectCreateArgs(BaseModel):
    name: str
    path: str
    ignore: List[str] = Field(default_factory=list)
    id: Optional[str] = None


class ProjectTreeArgs(BaseModel):
    project_id: str
    max_depth: int = 5


class FileReadArgs(BaseModel):
    project_id: str
    path: str


class FileSaveArgs(BaseModel):
    project_id: str
    path: str
    content: str


class FileUploadArgs(BaseModel):
    project_id: str
    path: str
    content: str
    filename: str = "upload.bin"


class PatchApplyArgs(BaseModel):
    project_id: str
    path: str
    patch: str


class PackEnableArgs(BaseModel):
    project_id: str
    packs: List[str]


class PackSpecsArgs(BaseModel):
    project_id: str


class ProjectEventsArgs(BaseModel):
    project_id: str
    limit: int = 50
