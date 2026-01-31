# django_test/scanner.py
from pathlib import Path
from typing import List, Optional

from .meta.scanner_meta import ScanResult, AppMeta


def scan_project(project_root: str, settings: Optional[str] = None) -> ScanResult:
    root = Path(project_root).resolve()
    _assert_django_project(root)

    settings_module = settings or _detect_settings_module(root)
    apps = _scan_apps(root)

    return ScanResult(
        project_root=root,
        settings_module=settings_module,
        apps=apps,
    )


# -------------------------
# Helpers
# -------------------------
def _assert_django_project(root: Path):
    if not (root / "manage.py").exists():
        raise RuntimeError("Not a Django project (manage.py not found)")


def _detect_settings_module(root: Path) -> str:
    for path in root.rglob("settings.py"):
        if "site-packages" in str(path):
            continue
        rel = path.relative_to(root)
        return ".".join(rel.with_suffix("").parts)
    raise RuntimeError("settings.py not found")


def _scan_apps(root: Path) -> List[AppMeta]:
    apps: List[AppMeta] = []

    for path in root.iterdir():
        if not path.is_dir():
            continue
        if path.name.startswith((".", "__", "venv")):
            continue

        if _looks_like_django_app(path):
            apps.append(_scan_app(path))

    return apps


def _looks_like_django_app(path: Path) -> bool:
    return (
        (path / "apps.py").exists()
        or (path / "models.py").exists()
        or (path / "presentation").exists()
        or (path / "application").exists()
    )


def _scan_app(app_path: Path) -> AppMeta:
    return AppMeta(
        name=app_path.name,
        path=app_path,
        views=_collect_files(app_path, ["views", "presentation/views"]),
        serializers=_collect_files(app_path, ["serializers", "presentation/serializers"]),
        services=_collect_files(app_path, ["services", "application/services"]),
        usecases=_collect_files(app_path, ["usecases", "application/usecases"]),
        models=_collect_files(app_path, ["models"]),
    )


def _collect_files(app_path: Path, names: List[str]) -> List[Path]:
    results: List[Path] = []
    for name in names:
        results.extend(app_path.glob(f"{name}.py"))
        results.extend(app_path.glob(f"{name}/*.py"))
    return sorted(set(results))