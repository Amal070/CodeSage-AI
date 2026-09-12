import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.project_analysis import (
    ProjectAnalysisResponse,
    ProjectStatistics,
    FileCountStatistics,
    FolderHierarchyNode,
)

logger = logging.getLogger(__name__)

# Common dependency, build, and version control directories to exclude from analysis
EXCLUDED_DIRECTORIES: Set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    "__MACOSX",
    ".DS_Store",
    "Thumbs.db",
    ".idea",
    ".vscode",
}

# Mapping of file extensions to canonical programming / markup languages
EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SCSS",
    ".less": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".sql": "SQL",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".xml": "XML",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".c": "C",
    ".h": "C/C++",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".bat": "Batch",
    ".cmd": "Batch",
    ".ps1": "PowerShell",
    ".r": "R",
    ".lua": "Lua",
    ".dart": "Dart",
    ".toml": "TOML",
    ".ini": "INI",
}


class ProjectAnalyzerService:
    """
    Service responsible for fast, filesystem-based project analysis.
    Generates statistics, language distributions, file extension breakdowns,
    and relative recursive folder hierarchies without reading full file contents.
    """

    def analyze_directory(
        self,
        extracted_dir: Path,
        project_id: int,
        project_name: str,
    ) -> ProjectAnalysisResponse:
        """
        Recursively analyzes the given project directory.
        Handles missing or empty project paths gracefully.
        """
        if not extracted_dir.exists() or not extracted_dir.is_dir():
            return self._build_empty_response(project_id, project_name)

        total_files = 0
        total_folders = 0
        total_size_bytes = 0
        unknown_files = 0
        extension_counts: Dict[str, int] = {}
        language_counts: Dict[str, int] = {}

        # 1. Recursive walker to build hierarchy and aggregate metrics
        def scan_directory(current_path: Path) -> List[FolderHierarchyNode]:
            nonlocal total_files, total_folders, total_size_bytes, unknown_files
            nodes: List[FolderHierarchyNode] = []

            try:
                entries = sorted(
                    list(current_path.iterdir()),
                    key=lambda e: (not e.is_dir(), e.name.lower()),
                )
            except Exception as e:
                logger.warning("Error reading directory %s: %s", current_path, e)
                return nodes

            for entry in entries:
                # Exclude unwanted and system directories/files
                if entry.name in EXCLUDED_DIRECTORIES or entry.name.startswith(".git"):
                    continue

                try:
                    rel_path = str(entry.relative_to(extracted_dir)).replace("\\", "/")
                except Exception:
                    rel_path = entry.name

                if entry.is_dir():
                    total_folders += 1
                    child_nodes = scan_directory(entry)
                    nodes.append(
                        FolderHierarchyNode(
                            name=entry.name,
                            type="folder",
                            path=rel_path,
                            children=child_nodes,
                        )
                    )
                elif entry.is_file():
                    total_files += 1
                    try:
                        file_size = entry.stat().st_size
                    except Exception:
                        file_size = 0
                    total_size_bytes += file_size

                    # Extension parsing and normalization
                    ext = entry.suffix.lower()
                    if not ext:
                        ext_key = "(no extension)"
                    else:
                        ext_key = ext

                    extension_counts[ext_key] = extension_counts.get(ext_key, 0) + 1

                    # Language detection
                    lang = EXTENSION_LANGUAGE_MAP.get(ext)
                    if lang:
                        language_counts[lang] = language_counts.get(lang, 0) + 1
                    else:
                        unknown_files += 1

                    nodes.append(
                        FolderHierarchyNode(
                            name=entry.name,
                            type="file",
                            path=rel_path,
                            size=file_size,
                            children=None,
                        )
                    )

            return nodes

        root_children = scan_directory(extracted_dir)

        # 2. Compute size metrics
        total_kb = round(total_size_bytes / 1024, 1)
        total_mb = round(total_size_bytes / (1024 * 1024), 2)

        # 3. Sort distributions by frequency descending
        sorted_languages = dict(
            sorted(language_counts.items(), key=lambda item: item[1], reverse=True)
        )
        sorted_extensions = dict(
            sorted(extension_counts.items(), key=lambda item: item[1], reverse=True)
        )

        # 4. Construct root hierarchy node
        root_hierarchy = FolderHierarchyNode(
            name=project_name,
            type="folder",
            path="",
            children=root_children,
        )

        return ProjectAnalysisResponse(
            project_id=project_id,
            project_name=project_name,
            statistics=ProjectStatistics(
                total_files=total_files,
                total_folders=total_folders,
                total_size_bytes=total_size_bytes,
                total_size_kb=total_kb,
                total_size_mb=total_mb,
            ),
            languages=sorted_languages,
            unknown_files=unknown_files,
            file_count=FileCountStatistics(
                total=total_files,
                by_extension=sorted_extensions,
            ),
            folder_hierarchy=root_hierarchy,
        )

    def _build_empty_response(
        self,
        project_id: int,
        project_name: str,
    ) -> ProjectAnalysisResponse:
        """Returns valid zero statistics for empty or missing projects."""
        return ProjectAnalysisResponse(
            project_id=project_id,
            project_name=project_name,
            statistics=ProjectStatistics(
                total_files=0,
                total_folders=0,
                total_size_bytes=0,
                total_size_kb=0.0,
                total_size_mb=0.0,
            ),
            languages={},
            unknown_files=0,
            file_count=FileCountStatistics(
                total=0,
                by_extension={},
            ),
            folder_hierarchy=FolderHierarchyNode(
                name=project_name,
                type="folder",
                path="",
                children=[],
            ),
        )


project_analyzer_service = ProjectAnalyzerService()
