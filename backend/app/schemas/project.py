from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProjectResponse(BaseModel):
    id: int
    name: str
    original_filename: Optional[str] = None
    status: str
    file_count: int = 0
    lines_of_code: int = 0
    created_at: datetime
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class ProjectUploadResponse(BaseModel):
    message: str
    project: ProjectResponse


class FileTreeNode(BaseModel):
    name: str
    type: str  # "file" or "folder"
    path: str  # relative path from project root
    size: Optional[int] = None
    children: Optional[list["FileTreeNode"]] = None


class ProjectFileTreeResponse(BaseModel):
    project_id: int
    tree: list[FileTreeNode]


class FileContentResponse(BaseModel):
    name: str
    path: str
    language: str
    size: int
    is_binary: bool = False
    content: Optional[str] = None
    message: Optional[str] = None
