# django_test/parser_urls.py
import ast
from pathlib import Path
from typing import Dict, List

from .meta.scanner_meta import ScanResult
from .meta.parser_meta import EndpointMeta


# Public entry
def attach_urls(scan: ScanResult, endpoints: List[EndpointMeta]) -> List[EndpointMeta]:
    url_map = _collect_all_urls(scan.project_root)

    for ep in endpoints:
        ep.url_hint = url_map.get(ep.view_name)

    return endpoints

# URL Collection
def _collect_all_urls(project_root: Path) -> Dict[str, str]:
    url_map: Dict[str, str] = {}

    config_urls = project_root / "config" / "urls.py"
    if not config_urls.exists():
        return url_map

    tree = ast.parse(config_urls.read_text(encoding="utf-8"))

    _parse_urls_file(
        tree=tree,
        current_file=config_urls,
        project_root=project_root,
        prefix="",
        url_map=url_map,
    )

    return url_map

# Parsing logic
def _parse_urls_file(
    tree: ast.Module,
    current_file: Path,
    project_root: Path,
    prefix: str,
    url_map: Dict[str, str],
):
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "urlpatterns":
                _parse_urlpatterns_list(
                    node.value,
                    project_root=project_root,
                    prefix=prefix,
                    url_map=url_map,
                )

def _parse_urlpatterns_list(
    node: ast.AST,
    project_root: Path,
    url_map: Dict[str, str],
    prefix: str,
):
    if not isinstance(node, ast.List):
        return

    for item in node.elts:
        if not isinstance(item, ast.Call):
            continue

        if not isinstance(item.func, ast.Name):
            continue

        if item.func.id not in {"path", "re_path"}:
            continue

        url, view, include_module = _parse_path_call(item)

        # include("xxx.urls")
        if include_module:
            include_path = _resolve_urls_py(project_root, include_module)
            if include_path and include_path.exists():
                try:
                    sub_tree = ast.parse(include_path.read_text(encoding="utf-8"))
                except SyntaxError:
                    continue

                _parse_urls_file(
                    tree=sub_tree,
                    current_file=include_path,
                    project_root=project_root,
                    url_map=url_map,
                    prefix=prefix + url,
                )

        # direct view
        elif view:
            full_url = _normalize_url(prefix + url)
            url_map[view] = full_url

def _parse_path_call(call: ast.Call):
    if len(call.args) < 2:
        return "", None, None

    if not isinstance(call.args[0], ast.Constant):
        return "", None, None

    url = call.args[0].value
    target = call.args[1]

    # include("app.urls") or include("app.presentation.urls")
    if isinstance(target, ast.Call) and isinstance(target.func, ast.Name):
        if target.func.id == "include" and target.args:
            if isinstance(target.args[0], ast.Constant):
                return url, None, target.args[0].value

    # Class-based view
    if isinstance(target, ast.Call) and isinstance(target.func, ast.Attribute):
        if isinstance(target.func.value, ast.Name):
            return url, target.func.value.id, None

    # Function-based view
    if isinstance(target, ast.Name):
        return url, target.id, None

    return url, None, None

# Helpers
def _resolve_urls_py(project_root: Path, module: str) -> Path | None:
    parts = module.split(".")
    path = project_root.joinpath(*parts).with_suffix(".py")
    return path if path.exists() else None

def _normalize_url(url: str) -> str:
    if not url.startswith("/"):
        url = "/" + url
    if not url.endswith("/"):
        url += "/"
    return url