from typing import List, Optional
from pydantic import BaseModel, Field


class FunctionInfo(BaseModel):
    name: str
    type: str = "function"  # "function" or "method"
    line_start: int
    line_end: int
    parent_class: Optional[str] = None


class ClassInfo(BaseModel):
    name: str
    type: str = "class"
    line_start: int
    line_end: int


class ImportInfo(BaseModel):
    name: str
    line: int


class CodeParseResponse(BaseModel):
    language: str
    file: str
    functions: List[FunctionInfo] = Field(default_factory=list)
    classes: List[ClassInfo] = Field(default_factory=list)
    imports: List[ImportInfo] = Field(default_factory=list)
