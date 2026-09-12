import json
import logging
import os
import posixpath
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET

import tomli

from app.schemas.dependency_analysis import (
    DependencyAnalysisResponse,
    DependencyGraph,
    GraphEdge,
    GraphNode,
    ImportItem,
    PackageItem,
    RelationshipItem,
)
from app.services.code_parser import code_parser_service

logger = logging.getLogger(__name__)

# Excluded directories during traversal to optimize performance and ignore build artifacts
EXCLUDED_DIRECTORIES: Set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "target",
    ".gradle",
    "__MACOSX",
    ".mypy_cache",
    ".pytest_cache",
}

# Max file size to parse for AST (2MB limit for dependency scanning)
MAX_SCAN_FILE_SIZE_BYTES = 2 * 1024 * 1024

# Common Node.js builtin modules
NODE_BUILTIN_MODULES: Set[str] = {
    "assert", "buffer", "child_process", "cluster", "crypto", "dgram", "dns",
    "events", "fs", "http", "http2", "https", "net", "os", "path", "perf_hooks",
    "process", "punycode", "querystring", "readline", "repl", "stream",
    "string_decoder", "tls", "trace_events", "tty", "url", "util", "v8", "vm",
    "wasi", "worker_threads", "zlib", "fs/promises",
}

# Java standard prefixes
JAVA_STANDARD_PREFIXES = (
    "java.",
    "javax.",
    "jakarta.",
    "org.w3c.",
    "org.xml.",
    "sun.",
    "com.sun.",
)


class DependencyAnalyzerService:
    """
    Service responsible for static dependency analysis:
    1. Detecting imports from source code (Python, JavaScript/JSX, Java) using Tree-sitter.
    2. Detecting project packages from manifests (requirements.txt, pyproject.toml, package.json, pom.xml, build.gradle).
    3. Resolving local file relationships vs. external packages vs. unknown imports.
    4. Constructing relationship lists and graph data without code execution or package installation.
    """

    def analyze_dependencies(
        self,
        extracted_dir: Path,
        project_id: int,
        project_name: str,
    ) -> DependencyAnalysisResponse:
        """
        Main entry point for project dependency analysis.
        Operates statically on extracted project directory.
        """
        if not extracted_dir.exists() or not extracted_dir.is_dir():
            return self._build_empty_response(project_id, project_name)

        # 1. Index all files in the project (POSIX relative paths)
        all_files, all_files_set = self._index_project_files(extracted_dir)
        if not all_files:
            return self._build_empty_response(project_id, project_name)

        # 2. Extract external packages from dependency manifests
        declared_packages = self._parse_manifest_packages(extracted_dir, all_files)
        declared_py_names = {
            pkg.name.lower().replace("-", "_")
            for pkg in declared_packages
            if pkg.ecosystem == "python"
        }
        declared_py_names.update({
            pkg.name.lower() for pkg in declared_packages if pkg.ecosystem == "python"
        })

        # 3. Extract imports from source files using Tree-sitter
        imports: List[ImportItem] = []
        relationships: List[RelationshipItem] = []
        graph_nodes_dict: Dict[str, GraphNode] = {}
        graph_edges_set: Set[Tuple[str, str, str]] = set()

        for rel_path in all_files:
            full_path = extracted_dir / rel_path
            lang = code_parser_service.detect_language(full_path.name)
            if not lang:
                continue

            # Read source content safely
            content = self._safe_read_file(full_path)
            if not content:
                continue

            # Tree-sitter AST extraction
            parse_result = code_parser_service.parse_source_code(
                content, lang, relative_path=rel_path
            )

            # Analyze each import in file
            for raw_import in parse_result.imports:
                import_name = raw_import.name.strip()
                if not import_name:
                    continue

                # Classify & Resolve
                classification, target = self._resolve_import(
                    lang=lang,
                    import_name=import_name,
                    source_rel_path=rel_path,
                    all_files_set=all_files_set,
                    declared_py_names=declared_py_names,
                )

                item = ImportItem(
                    source=rel_path,
                    name=import_name,
                    type=classification,
                    target=target,
                    line=raw_import.line,
                )
                imports.append(item)

                # If resolvable (local or external), record relationship and graph elements
                if target:
                    rel_type = "imports" if classification == "local" else "depends_on"
                    relationships.append(
                        RelationshipItem(
                            source=rel_path,
                            target=target,
                            type=rel_type,
                            dependency_type=classification,
                        )
                    )

                    # Add source file node
                    if rel_path not in graph_nodes_dict:
                        graph_nodes_dict[rel_path] = GraphNode(
                            id=rel_path,
                            label=posixpath.basename(rel_path),
                            type="file",
                        )

                    # Add target node
                    target_type = "file" if classification == "local" else "package"
                    if target not in graph_nodes_dict:
                        graph_nodes_dict[target] = GraphNode(
                            id=target,
                            label=posixpath.basename(target) if target_type == "file" else target,
                            type=target_type,
                        )

                    # Add edge
                    graph_edges_set.add((rel_path, target, rel_type))

        # Add any declared packages as package nodes in the graph if not already present
        for pkg in declared_packages:
            if pkg.name not in graph_nodes_dict:
                graph_nodes_dict[pkg.name] = GraphNode(
                    id=pkg.name,
                    label=pkg.name,
                    type="package",
                )

        # Build graph
        graph_nodes = list(graph_nodes_dict.values())
        graph_edges = [
            GraphEdge(source=src, target=tgt, type=edge_type)
            for src, tgt, edge_type in graph_edges_set
        ]

        return DependencyAnalysisResponse(
            project_id=project_id,
            project_name=project_name,
            imports=imports,
            packages=declared_packages,
            relationships=relationships,
            graph=DependencyGraph(nodes=graph_nodes, edges=graph_edges),
        )

    # --------------------------------------------------------------------------
    # File Indexing
    # --------------------------------------------------------------------------
    def _index_project_files(
        self, extracted_dir: Path
    ) -> Tuple[List[str], Set[str]]:
        """
        Indexes all files in the project into normalized POSIX relative paths.
        Skips excluded directories.
        """
        all_files: List[str] = []
        all_files_set: Set[str] = set()

        for root, dirs, files in os.walk(extracted_dir):
            # Prune excluded directories in-place
            dirs[:] = [
                d for d in dirs
                if d not in EXCLUDED_DIRECTORIES and not d.startswith(".")
            ]

            for file_name in files:
                if file_name.startswith(".") and file_name not in {
                    ".env.example", ".gitignore"
                }:
                    continue

                full_path = Path(root) / file_name
                try:
                    rel = full_path.relative_to(extracted_dir).as_posix()
                    all_files.append(rel)
                    all_files_set.add(rel)
                except ValueError:
                    continue

        all_files.sort()
        return all_files, all_files_set

    # --------------------------------------------------------------------------
    # Manifest Parsers (Static analysis without code execution)
    # --------------------------------------------------------------------------
    def _parse_manifest_packages(
        self, extracted_dir: Path, all_files: List[str]
    ) -> List[PackageItem]:
        """
        Inspects project files for package manifests and extracts declared packages.
        """
        packages: List[PackageItem] = []
        seen_keys: Set[Tuple[str, str]] = set()

        def add_package(
            name: str,
            ecosystem: str,
            version: Optional[str] = None,
            pkg_type: str = "dependency",
            source: str = "",
        ) -> None:
            clean_name = name.strip()
            if not clean_name:
                return
            key = (ecosystem, clean_name.lower())
            if key in seen_keys:
                return
            seen_keys.add(key)
            packages.append(
                PackageItem(
                    name=clean_name,
                    ecosystem=ecosystem,
                    version=version.strip() if version else None,
                    type=pkg_type,
                    source=source,
                )
            )

        for rel_path in all_files:
            file_name = posixpath.basename(rel_path).lower()
            full_path = extracted_dir / rel_path

            # 1. Python requirements.txt
            if file_name.startswith("requirements") and file_name.endswith(".txt"):
                content = self._safe_read_file(full_path)
                if content:
                    for line in content.splitlines():
                        line = line.strip()
                        # Skip comments, options, or empty lines
                        if not line or line.startswith(("#", "-", "@")):
                            continue
                        # Remove inline comments
                        line = line.split("#")[0].strip()
                        # Match name and optional version
                        match = re.match(r"^([a-zA-Z0-9_\-\.]+)(?:\[[^\]]*\])?(?:([=><~^!]+)([^;#]+))?", line)
                        if match:
                            pkg_name = match.group(1)
                            op = match.group(2) or ""
                            ver_val = match.group(3) or ""
                            version_str = f"{op}{ver_val.strip()}" if op else None
                            add_package(
                                name=pkg_name,
                                ecosystem="python",
                                version=version_str,
                                pkg_type="dependency",
                                source=posixpath.basename(rel_path),
                            )

            # 2. Python pyproject.toml
            elif file_name == "pyproject.toml":
                content = self._safe_read_file(full_path)
                if content:
                    try:
                        data = tomli.loads(content)
                        # [project.dependencies]
                        proj_deps = data.get("project", {}).get("dependencies", [])
                        if isinstance(proj_deps, list):
                            for dep in proj_deps:
                                if isinstance(dep, str):
                                    match = re.match(r"^([a-zA-Z0-9_\-\.]+)(?:\[[^\]]*\])?(?:([=><~^!]+)([^;#]+))?", dep.strip())
                                    if match:
                                        pkg_name = match.group(1)
                                        op = match.group(2) or ""
                                        ver_val = match.group(3) or ""
                                        version_str = f"{op}{ver_val.strip()}" if op else None
                                        add_package(
                                            name=pkg_name,
                                            ecosystem="python",
                                            version=version_str,
                                            pkg_type="dependency",
                                            source=posixpath.basename(rel_path),
                                        )
                        # [tool.poetry.dependencies]
                        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                        if isinstance(poetry_deps, dict):
                            for dep_name, dep_val in poetry_deps.items():
                                if dep_name.lower() == "python":
                                    continue
                                ver_str = str(dep_val) if not isinstance(dep_val, dict) else str(dep_val.get("version", ""))
                                add_package(
                                    name=dep_name,
                                    ecosystem="python",
                                    version=ver_str or None,
                                    pkg_type="dependency",
                                    source=posixpath.basename(rel_path),
                                )
                        # [tool.poetry.group.dev.dependencies]
                        dev_deps = data.get("tool", {}).get("poetry", {}).get("group", {}).get("dev", {}).get("dependencies", {})
                        if isinstance(dev_deps, dict):
                            for dep_name, dep_val in dev_deps.items():
                                ver_str = str(dep_val) if not isinstance(dep_val, dict) else str(dep_val.get("version", ""))
                                add_package(
                                    name=dep_name,
                                    ecosystem="python",
                                    version=ver_str or None,
                                    pkg_type="devDependency",
                                    source=posixpath.basename(rel_path),
                                )
                    except Exception as e:
                        logger.warning("Failed to parse pyproject.toml at %s: %s", rel_path, e)

            # 3. JavaScript package.json
            elif file_name == "package.json":
                content = self._safe_read_file(full_path)
                if content:
                    try:
                        data = json.loads(content)
                        # dependencies
                        deps = data.get("dependencies", {})
                        if isinstance(deps, dict):
                            for dep_name, ver in deps.items():
                                add_package(
                                    name=dep_name,
                                    ecosystem="javascript",
                                    version=str(ver) if ver else None,
                                    pkg_type="dependency",
                                    source=posixpath.basename(rel_path),
                                )
                        # devDependencies
                        dev_deps = data.get("devDependencies", {})
                        if isinstance(dev_deps, dict):
                            for dep_name, ver in dev_deps.items():
                                add_package(
                                    name=dep_name,
                                    ecosystem="javascript",
                                    version=str(ver) if ver else None,
                                    pkg_type="devDependency",
                                    source=posixpath.basename(rel_path),
                                )
                    except Exception as e:
                        logger.warning("Failed to parse package.json at %s: %s", rel_path, e)

            # 4. Java Maven pom.xml
            elif file_name == "pom.xml":
                content = self._safe_read_file(full_path)
                if content:
                    try:
                        root_elem = ET.fromstring(content)
                        # Handle XML namespaces
                        ns = ""
                        if root_elem.tag.startswith("{"):
                            ns = root_elem.tag.split("}")[0] + "}"
                        for dep in root_elem.iter(f"{ns}dependency"):
                            artifact_id = dep.find(f"{ns}artifactId")
                            version_elem = dep.find(f"{ns}version")
                            scope_elem = dep.find(f"{ns}scope")
                            if artifact_id is not None and artifact_id.text:
                                name_val = artifact_id.text.strip()
                                ver_val = version_elem.text.strip() if version_elem is not None and version_elem.text else None
                                # If version is a Maven property (${...}), keep as is or treat as unspecified
                                scope_val = scope_elem.text.strip() if scope_elem is not None and scope_elem.text else "dependency"
                                dep_type = "devDependency" if scope_val in {"test", "provided"} else "dependency"
                                add_package(
                                    name=name_val,
                                    ecosystem="java",
                                    version=ver_val,
                                    pkg_type=dep_type,
                                    source=posixpath.basename(rel_path),
                                )
                    except Exception as e:
                        logger.warning("Failed to parse pom.xml at %s: %s", rel_path, e)

            # 5. Java Gradle build.gradle / build.gradle.kts
            elif file_name in {"build.gradle", "build.gradle.kts"}:
                content = self._safe_read_file(full_path)
                if content:
                    # Match Gradle dependency configurations: implementation 'group:artifact:version' or implementation("group:artifact:version")
                    pattern = re.compile(
                        r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\s*[\('"]+([^:'"\\s]+):([^:'"\\s]+)(?::([^'"\\s\)]+))?[\)'"]*"""
                    )
                    for match in pattern.finditer(content):
                        artifact = match.group(2).strip()
                        ver = match.group(3).strip() if match.group(3) else None
                        add_package(
                            name=artifact,
                            ecosystem="java",
                            version=ver,
                            pkg_type="dependency",
                            source=posixpath.basename(rel_path),
                        )

        return packages

    # --------------------------------------------------------------------------
    # Import Resolution Logic
    # --------------------------------------------------------------------------
    def _resolve_import(
        self,
        lang: str,
        import_name: str,
        source_rel_path: str,
        all_files_set: Set[str],
        declared_py_names: Set[str],
    ) -> Tuple[str, Optional[str]]:
        """
        Determines whether an import is 'local', 'external', or 'unknown',
        and resolves its target file path or package name.
        """
        source_dir = posixpath.dirname(source_rel_path)

        # ----------------------------------------------------------------------
        # JavaScript / JSX Resolution
        # ----------------------------------------------------------------------
        if lang == "javascript":
            # Relative import starting with ./ or ../ or /
            if import_name.startswith(("./", "../", "/")):
                norm_rel = posixpath.normpath(posixpath.join(source_dir, import_name))
                # Strip leading slashes
                norm_rel = norm_rel.lstrip("/")

                # Candidate extensions to test against project files
                candidates = [
                    norm_rel,
                    f"{norm_rel}.jsx",
                    f"{norm_rel}.js",
                    f"{norm_rel}.tsx",
                    f"{norm_rel}.ts",
                    f"{norm_rel}/index.jsx",
                    f"{norm_rel}/index.js",
                    f"{norm_rel}/index.tsx",
                    f"{norm_rel}/index.ts",
                ]
                for cand in candidates:
                    if cand in all_files_set:
                        return "local", cand

                # If relative import was specified but cannot be found in project files
                return "unknown", None

            # Non-relative imports in JavaScript are external packages or Node builtins
            pkg_name = import_name.split("/")[0] if not import_name.startswith("@") else "/".join(import_name.split("/")[:2])
            return "external", pkg_name

        # ----------------------------------------------------------------------
        # Python Resolution
        # ----------------------------------------------------------------------
        elif lang == "python":
            # Relative imports: .models, ..utils.helper, etc.
            if import_name.startswith("."):
                # Count leading dots
                leading_dots = len(import_name) - len(import_name.lstrip("."))
                sub_path = import_name.lstrip(".").replace(".", "/")

                # Navigate up parent directories based on dot count
                curr_dir = source_dir
                for _ in range(leading_dots - 1):
                    curr_dir = posixpath.dirname(curr_dir)

                target_base = posixpath.join(curr_dir, sub_path) if sub_path else curr_dir
                target_base = posixpath.normpath(target_base).lstrip("/")

                candidates = [
                    f"{target_base}.py",
                    f"{target_base}/__init__.py",
                ]
                for cand in candidates:
                    if cand in all_files_set:
                        return "local", cand

                return "unknown", None

            # Absolute imports: e.g. fastapi, app.database, os, models
            root_module = import_name.split(".")[0]

            # Check Python standard library
            if root_module in sys.stdlib_module_names:
                return "external", root_module

            # Check if this maps to a project-local file
            # e.g. 'app.database' -> 'app/database.py' or 'backend/app/database.py'
            module_as_path = import_name.replace(".", "/")
            candidate_suffixes = [
                f"{module_as_path}.py",
                f"{module_as_path}/__init__.py",
            ]

            # 1. Exact match from project root
            for suff in candidate_suffixes:
                if suff in all_files_set:
                    return "local", suff

            # 2. Match within any project subdirectory (e.g. backend/app/database.py)
            for suff in candidate_suffixes:
                for proj_file in all_files_set:
                    if proj_file.endswith(f"/{suff}"):
                        return "local", proj_file

            # 3. If module has multiple parts, check if prefix is a local package
            # e.g. 'from app.database import get_db' -> 'app/database.py'
            if len(import_name.split(".")) > 1:
                prefix_as_path = "/".join(import_name.split(".")[:-1])
                for suff in [f"{prefix_as_path}.py", f"{prefix_as_path}/__init__.py"]:
                    if suff in all_files_set:
                        return "local", suff
                    for proj_file in all_files_set:
                        if proj_file.endswith(f"/{suff}"):
                            return "local", proj_file

            # Check if root module is in declared requirements / pyproject.toml
            if root_module.lower().replace("-", "_") in declared_py_names:
                return "external", root_module

            # Check if root module is in same directory as importing file
            same_dir_cand = posixpath.join(source_dir, f"{root_module}.py")
            if same_dir_cand in all_files_set:
                return "local", same_dir_cand

            # If import cannot be matched to local project file, stdlib, or declared manifest
            # Per Phase 35: Unresolved import test -> return 'unknown'
            return "unknown", None

        # ----------------------------------------------------------------------
        # Java Resolution
        # ----------------------------------------------------------------------
        elif lang == "java":
            # Check Java standard library
            if any(import_name.startswith(p) for p in JAVA_STANDARD_PREFIXES):
                # e.g. java.util.List -> java.util
                pkg_parts = import_name.split(".")
                pkg_root = ".".join(pkg_parts[:2]) if len(pkg_parts) >= 2 else import_name
                return "external", pkg_root

            # Check if class matches a local Java file in project
            # e.g. com.example.model.User -> com/example/model/User.java
            class_as_path = import_name.replace(".", "/") + ".java"
            for proj_file in all_files_set:
                if proj_file.endswith(class_as_path) or proj_file.endswith(f"/{class_as_path}"):
                    return "local", proj_file

            # Check wildcard / package import: com.example.model.*
            if import_name.endswith(".*"):
                pkg_as_path = import_name[:-2].replace(".", "/")
                for proj_file in all_files_set:
                    if f"/{pkg_as_path}/" in f"/{proj_file}":
                        return "local", proj_file

            # If not resolved locally or in standard library
            return "unknown", None

        return "unknown", None

    # --------------------------------------------------------------------------
    # Utility Helpers
    # --------------------------------------------------------------------------
    def _safe_read_file(self, file_path: Path) -> Optional[str]:
        """
        Safely reads file content as text.
        Skips excessively large files. Handles encodings gracefully.
        """
        try:
            if file_path.stat().st_size > MAX_SCAN_FILE_SIZE_BYTES:
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    return f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        return f.read()
                except Exception:
                    return None
        except Exception:
            return None

    def _build_empty_response(
        self, project_id: int, project_name: str
    ) -> DependencyAnalysisResponse:
        """
        Builds a safe, empty DependencyAnalysisResponse (Phase 25).
        """
        return DependencyAnalysisResponse(
            project_id=project_id,
            project_name=project_name,
            imports=[],
            packages=[],
            relationships=[],
            graph=DependencyGraph(nodes=[], edges=[]),
        )


# Global singleton instance
dependency_analyzer_service = DependencyAnalyzerService()
