import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from tree_sitter import Language, Parser, Tree, Node
import tree_sitter_python
import tree_sitter_java
import tree_sitter_javascript

from app.schemas.code_parser import (
    CodeParseResponse,
    FunctionInfo,
    ClassInfo,
    ImportInfo,
)

logger = logging.getLogger(__name__)

# Supported file extensions mapped to internal language names
SUPPORTED_EXTENSIONS: Dict[str, str] = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
}


class CodeParserService:
    """
    Reusable AST parser service powered by Tree-sitter.
    Supports Python, Java, and JavaScript source code analysis.
    Extracts functions, methods, classes, and imports.
    """

    def __init__(self) -> None:
        self._parsers: Dict[str, Parser] = {}
        self._languages: Dict[str, Language] = {}
        self._initialize_languages()

    def _initialize_languages(self) -> None:
        """
        Initializes Tree-sitter language grammars and parser instances.
        """
        try:
            self._languages["python"] = Language(tree_sitter_python.language())
            self._parsers["python"] = Parser(self._languages["python"])
        except Exception as e:
            logger.error("Failed to load Python Tree-sitter grammar: %s", e)

        try:
            self._languages["java"] = Language(tree_sitter_java.language())
            self._parsers["java"] = Parser(self._languages["java"])
        except Exception as e:
            logger.error("Failed to load Java Tree-sitter grammar: %s", e)

        try:
            self._languages["javascript"] = Language(tree_sitter_javascript.language())
            self._parsers["javascript"] = Parser(self._languages["javascript"])
        except Exception as e:
            logger.error("Failed to load JavaScript Tree-sitter grammar: %s", e)

    def detect_language(self, filename: str) -> Optional[str]:
        """
        Detect supported language from file extension.
        Returns 'python', 'java', 'javascript', or None if unsupported.
        """
        ext = Path(filename).suffix.lower()
        return SUPPORTED_EXTENSIONS.get(ext)

    def is_supported(self, filename: str) -> bool:
        """
        Check if a file extension is supported for Tree-sitter parsing.
        """
        return self.detect_language(filename) is not None

    def parse_source_code(
        self,
        source_code: str,
        language: str,
        relative_path: str = "",
    ) -> CodeParseResponse:
        """
        Parses source code string using the specified language grammar.
        Extracts functions, classes, and imports into a normalized CodeParseResponse.
        Gracefully handles syntax errors and ERROR nodes.
        """
        lang = language.lower().strip()
        parser = self._parsers.get(lang)
        if not parser:
            raise ValueError(f"No Tree-sitter parser configured for language: {language}")

        source_bytes = source_code.encode("utf-8", errors="replace")
        try:
            tree = parser.parse(source_bytes)
        except Exception as e:
            logger.warning("Tree-sitter parse failed for %s: %s", relative_path, e)
            return CodeParseResponse(
                language=lang,
                file=relative_path,
                functions=[],
                classes=[],
                imports=[],
            )

        if lang == "python":
            functions, classes, imports = self._extract_python(tree.root_node, source_bytes)
        elif lang == "java":
            functions, classes, imports = self._extract_java(tree.root_node, source_bytes)
        elif lang == "javascript":
            functions, classes, imports = self._extract_javascript(tree.root_node, source_bytes)
        else:
            functions, classes, imports = [], [], []

        return CodeParseResponse(
            language=lang,
            file=relative_path,
            functions=functions,
            classes=classes,
            imports=imports,
        )

    # --------------------------------------------------------------------------
    # Python Extractor
    # --------------------------------------------------------------------------
    def _extract_python(
        self,
        root_node: Node,
        source_bytes: bytes,
    ) -> Tuple[List[FunctionInfo], List[ClassInfo], List[ImportInfo]]:
        classes: List[ClassInfo] = []
        functions: List[FunctionInfo] = []
        imports: List[ImportInfo] = []

        def get_text(n: Optional[Node]) -> str:
            if not n:
                return ""
            return source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="replace").strip()

        def walk(node: Node, current_class: Optional[str] = None) -> None:
            if node.type == "import_statement":
                # e.g. import os, sys
                # or import fastapi as fa
                for child in node.children:
                    if child.type == "dotted_name":
                        name = get_text(child)
                        if name:
                            imports.append(ImportInfo(name=name, line=child.start_point[0] + 1))
                    elif child.type == "aliased_import":
                        name_node = child.child_by_field_name("name")
                        name = get_text(name_node)
                        if name:
                            imports.append(ImportInfo(name=name, line=child.start_point[0] + 1))

            elif node.type == "import_from_statement":
                # from fastapi import FastAPI
                # from app.database import engine
                mod_node = node.child_by_field_name("module_name")
                if mod_node:
                    name = get_text(mod_node)
                else:
                    # e.g. from . import config
                    name_candidates = [
                        c for c in node.children if c.type in ["relative_import", "dotted_name"]
                    ]
                    name = get_text(name_candidates[0]) if name_candidates else ""

                if name:
                    imports.append(ImportInfo(name=name, line=node.start_point[0] + 1))

            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                class_name = get_text(name_node) or "UnknownClass"
                classes.append(
                    ClassInfo(
                        name=class_name,
                        type="class",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    )
                )
                # Recurse inside class body with current_class context
                for child in node.children:
                    walk(child, current_class=class_name)
                return

            elif node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                func_name = get_text(name_node) or "unknown_func"
                func_type = "method" if current_class else "function"
                functions.append(
                    FunctionInfo(
                        name=func_name,
                        type=func_type,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        parent_class=current_class,
                    )
                )
                # Recurse into nested functions/classes
                for child in node.children:
                    walk(child, current_class=current_class)
                return

            for child in node.children:
                walk(child, current_class=current_class)

        walk(root_node)
        return functions, classes, imports

    # --------------------------------------------------------------------------
    # Java Extractor
    # --------------------------------------------------------------------------
    def _extract_java(
        self,
        root_node: Node,
        source_bytes: bytes,
    ) -> Tuple[List[FunctionInfo], List[ClassInfo], List[ImportInfo]]:
        classes: List[ClassInfo] = []
        functions: List[FunctionInfo] = []
        imports: List[ImportInfo] = []

        def get_text(n: Optional[Node]) -> str:
            if not n:
                return ""
            return source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="replace").strip()

        def walk(node: Node, current_class: Optional[str] = None) -> None:
            if node.type == "import_declaration":
                # import java.util.List;
                for child in node.children:
                    if child.type in ["scoped_identifier", "identifier"]:
                        name = get_text(child)
                        if name:
                            imports.append(ImportInfo(name=name, line=node.start_point[0] + 1))
                        break

            elif node.type in [
                "class_declaration",
                "interface_declaration",
                "enum_declaration",
                "record_declaration",
            ]:
                name_node = node.child_by_field_name("name")
                class_name = get_text(name_node) or "UnknownClass"
                classes.append(
                    ClassInfo(
                        name=class_name,
                        type="class",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    )
                )
                for child in node.children:
                    walk(child, current_class=class_name)
                return

            elif node.type in ["method_declaration", "constructor_declaration"]:
                name_node = node.child_by_field_name("name")
                method_name = get_text(name_node) or "unknownMethod"
                func_type = "method" if current_class else "function"
                functions.append(
                    FunctionInfo(
                        name=method_name,
                        type=func_type,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        parent_class=current_class,
                    )
                )
                for child in node.children:
                    walk(child, current_class=current_class)
                return

            for child in node.children:
                walk(child, current_class=current_class)

        walk(root_node)
        return functions, classes, imports

    # --------------------------------------------------------------------------
    # JavaScript Extractor
    # --------------------------------------------------------------------------
    def _extract_javascript(
        self,
        root_node: Node,
        source_bytes: bytes,
    ) -> Tuple[List[FunctionInfo], List[ClassInfo], List[ImportInfo]]:
        classes: List[ClassInfo] = []
        functions: List[FunctionInfo] = []
        imports: List[ImportInfo] = []

        def get_text(n: Optional[Node]) -> str:
            if not n:
                return ""
            return source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="replace").strip()

        def clean_quotes(s: str) -> str:
            s = s.strip()
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                return s[1:-1]
            if s.startswith("`") and s.endswith("`"):
                return s[1:-1]
            return s

        def walk(node: Node, current_class: Optional[str] = None) -> None:
            if node.type == "import_statement":
                # import React from "react";
                source_node = node.child_by_field_name("source")
                if source_node:
                    raw_source = get_text(source_node)
                    name = clean_quotes(raw_source)
                    if name:
                        imports.append(ImportInfo(name=name, line=node.start_point[0] + 1))

            elif node.type == "call_expression":
                # const express = require("express");
                func_node = node.child_by_field_name("function")
                if func_node and get_text(func_node) == "require":
                    args_node = node.child_by_field_name("arguments")
                    if args_node and len(args_node.children) > 1:
                        # First argument is after '('
                        for arg in args_node.children:
                            if arg.type == "string":
                                raw_str = get_text(arg)
                                name = clean_quotes(raw_str)
                                if name:
                                    imports.append(ImportInfo(name=name, line=node.start_point[0] + 1))
                                break

            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                class_name = get_text(name_node) or "UnknownClass"
                classes.append(
                    ClassInfo(
                        name=class_name,
                        type="class",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    )
                )
                for child in node.children:
                    walk(child, current_class=class_name)
                return

            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                method_name = get_text(name_node) or "unknownMethod"
                functions.append(
                    FunctionInfo(
                        name=method_name,
                        type="method",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        parent_class=current_class,
                    )
                )
                for child in node.children:
                    walk(child, current_class=current_class)
                return

            elif node.type in ["function_declaration", "generator_function_declaration"]:
                name_node = node.child_by_field_name("name")
                func_name = get_text(name_node) or "anonymous"
                functions.append(
                    FunctionInfo(
                        name=func_name,
                        type="function",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        parent_class=None,
                    )
                )
                for child in node.children:
                    walk(child, current_class=None)
                return

            elif node.type == "variable_declarator":
                val_node = node.child_by_field_name("value")
                if val_node and val_node.type in ["arrow_function", "function_expression"]:
                    name_node = node.child_by_field_name("name")
                    func_name = get_text(name_node)
                    if func_name:
                        functions.append(
                            FunctionInfo(
                                name=func_name,
                                type="function",
                                line_start=node.start_point[0] + 1,
                                line_end=node.end_point[0] + 1,
                                parent_class=None,
                            )
                        )
                # Continue walking children (e.g. to inspect require calls)
                for child in node.children:
                    walk(child, current_class=current_class)
                return

            for child in node.children:
                walk(child, current_class=current_class)

        walk(root_node)
        return functions, classes, imports


# Global singleton instance for efficient reuse across requests
code_parser_service = CodeParserService()
