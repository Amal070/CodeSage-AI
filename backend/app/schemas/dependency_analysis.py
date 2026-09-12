from typing import List, Optional
from pydantic import BaseModel, Field


class ImportItem(BaseModel):
    """
    Represents an import statement detected in a source code file.
    """
    source: str = Field(..., description="Project-relative path of the importing file")
    name: str = Field(..., description="Imported module, package, or symbol name")
    type: str = Field(..., description="Classification: 'local', 'external', or 'unknown'")
    target: Optional[str] = Field(None, description="Resolved relative file path or package name")
    line: Optional[int] = Field(None, description="Line number of the import statement")


class PackageItem(BaseModel):
    """
    Represents an external project-level package declared in a dependency manifest.
    """
    name: str = Field(..., description="Package or artifact name")
    ecosystem: str = Field(..., description="Ecosystem: 'python', 'javascript', or 'java'")
    version: Optional[str] = Field(None, description="Declared version or version constraint")
    type: str = Field("dependency", description="Dependency type: 'dependency' or 'devDependency'")
    source: Optional[str] = Field(None, description="Manifest file source (e.g. requirements.txt, package.json)")


class RelationshipItem(BaseModel):
    """
    Represents a relationship between files or between a file and a package.
    """
    source: str = Field(..., description="Project-relative path of the source file")
    target: str = Field(..., description="Target project-relative file path or external package name")
    type: str = Field("imports", description="Relationship type: 'imports' or 'depends_on'")
    dependency_type: Optional[str] = Field("local", description="'local' or 'external'")


class GraphNode(BaseModel):
    """
    Node in dependency graph.
    """
    id: str = Field(..., description="Unique node identifier (relative path or package name)")
    label: str = Field(..., description="Display label (basename or package name)")
    type: str = Field("file", description="Node type: 'file' or 'package'")


class GraphEdge(BaseModel):
    """
    Edge in dependency graph.
    """
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field("imports", description="Edge relationship type: 'imports' or 'depends_on'")


class DependencyGraph(BaseModel):
    """
    Graph structure containing nodes and edges.
    """
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class DependencyAnalysisResponse(BaseModel):
    """
    Full response model for GET /api/projects/{project_id}/dependencies.
    """
    project_id: int
    project_name: str
    imports: List[ImportItem] = Field(default_factory=list)
    packages: List[PackageItem] = Field(default_factory=list)
    relationships: List[RelationshipItem] = Field(default_factory=list)
    graph: DependencyGraph = Field(default_factory=DependencyGraph)
