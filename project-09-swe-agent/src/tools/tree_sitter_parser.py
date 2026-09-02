from __future__ import annotations

from pathlib import Path


def safe_parse_python(source: str) -> list[str]:
    """Extract top-level symbol names using tree-sitter if available, else fall back to ast."""
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_python

        PY_LANGUAGE = Language(tree_sitter_python.language())
        parser = Parser(PY_LANGUAGE)
        tree = parser.parse(source.encode())
        return _extract_names(tree.root_node)
    except (ImportError, Exception):
        return _ast_fallback(source)


def _extract_names(node) -> list[str]:
    results: list[str] = []
    for child in node.children:
        if child.type in ("function_definition", "class_definition"):
            for sub in child.children:
                if sub.type == "identifier":
                    results.append(sub.text.decode())
                    break
    return results


def _ast_fallback(source: str) -> list[str]:
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    names: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
    return names


def parse_file(path: str) -> list[str]:
    try:
        source = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return safe_parse_python(source)
