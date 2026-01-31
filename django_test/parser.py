# django_test/parser.py
import ast
from pathlib import Path
from typing import List

from .meta.scanner_meta import ScanResult
from .meta.parser_meta import EndpointMeta


# =====================
# Public entry
# =====================
def parse_project(scan: ScanResult) -> List[EndpointMeta]:
    endpoints: List[EndpointMeta] = []

    for app in scan.apps:
        for view_file in app.views:
            endpoints.extend(
                _parse_view_file(
                    app_name=app.name,
                    file=view_file,
                )
            )

    return endpoints


# =====================
# Internal parsing
# =====================
def _parse_view_file(app_name: str, file: Path) -> List[EndpointMeta]:
    tree = ast.parse(file.read_text(encoding="utf-8"))
    results: List[EndpointMeta] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            meta = _parse_class_view(app_name, file, node)
            if meta:
                results.append(meta)

        elif isinstance(node, ast.FunctionDef):
            meta = _parse_function_view(app_name, file, node)
            if meta:
                results.append(meta)

    return results


# ---------------------
# Class-based views
# ---------------------
def _parse_class_view(app: str, file: Path, node: ast.ClassDef):
    bases = _get_base_names(node)

    if any(base.endswith("APIView") for base in bases):
        return EndpointMeta(
            app=app,
            view_name=node.name,
            file=file,
            view_type="APIView",
            http_methods=_extract_http_methods(node),
            serializer=_extract_serializer(node),
        )

    if any(base.endswith("ViewSet") for base in bases):
        return EndpointMeta(
            app=app,
            view_name=node.name,
            file=file,
            view_type="ViewSet",
            http_methods=_viewset_methods(node),
            serializer=_extract_serializer(node),
        )

    return None


# ---------------------
# Function-based views
# ---------------------
def _parse_function_view(app: str, file: Path, node: ast.FunctionDef):
    decorators = []

    for d in node.decorator_list:
        if isinstance(d, ast.Name):
            decorators.append(d.id)
        elif isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
            decorators.append(d.func.id)

    if "api_view" in decorators:
        return EndpointMeta(
            app=app,
            view_name=node.name,
            file=file,
            view_type="FunctionView",
            http_methods=["GET", "POST"],
        )

    return None


# =====================
# Helpers
# =====================
def _get_base_names(node: ast.ClassDef) -> List[str]:
    names = []

    for b in node.bases:
        if isinstance(b, ast.Name):
            names.append(b.id)
        elif isinstance(b, ast.Attribute):
            names.append(b.attr)

    return names


def _extract_http_methods(node: ast.ClassDef) -> List[str]:
    methods = []

    for item in node.body:
        if isinstance(item, ast.FunctionDef):
            name = item.name.lower()
            if name in {"get", "post", "put", "patch", "delete"}:
                methods.append(name.upper())

    return sorted(set(methods))


def _viewset_methods(node: ast.ClassDef) -> List[str]:
    mapping = {
        "list": "GET",
        "retrieve": "GET",
        "create": "POST",
        "update": "PUT",
        "partial_update": "PATCH",
        "destroy": "DELETE",
    }

    methods = []
    for item in node.body:
        if isinstance(item, ast.FunctionDef) and item.name in mapping:
            methods.append(mapping[item.name])

    return sorted(set(methods))


def _extract_serializer(node: ast.ClassDef):
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "serializer_class":
                    if isinstance(item.value, ast.Name):
                        return item.value.id
    return None