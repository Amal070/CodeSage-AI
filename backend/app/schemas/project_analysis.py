from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectStatistics(BaseModel):
    total_files: int = 0
    total_folders: int = 0
    total_size_bytes: int = 0
    total_size_kb: float = 0.0
    total_size_mb: float = 0.0


class FileCountStatistics(BaseModel):
    total: int = 0
    by_extension: Dict[str, int] = Field(default_factory=dict)


class FolderHierarchyNode(BaseModel):
    name: str
    type: str  # "file" or "folder"
    path: Optional[str] = None
    size: Optional[int] = None
    children: Optional[List["FolderHierarchyNode"]] = None


class ProjectAnalysisResponse(BaseModel):
    project_id: int
    project_name: str
    statistics: ProjectStatistics
    languages: Dict[str, int] = Field(default_factory=dict)
    unknown_files: int = 0
    file_count: FileCountStatistics
    folder_hierarchy: FolderHierarchyNode
