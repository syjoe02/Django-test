from pathlib import Path
from typing import List, Optional, Iterable

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
# Constants (patterns are explicit & centralized)
# -------------------------

SKIP_DIR_PREFIXES = (".", "__", "venv")

VIEW_PATHS = ("views", "presentation/views")
SERIALIZER_PATHS = ("serializers", "presentation/serializers")
SERVICE_PATHS = ("services", "application/services")
USECASE_PATHS = ("usecases", "application/usecases")
ENTITY_PATHS = ("domain/entities",)
ORM_MODEL_PATHS_PRIMARY = ("adapters/orm/models",)
ORM_MODEL_PATHS_FALLBACK = ("models",)

DJANGO_APP_MARKERS = (
    "apps.py",
    "models.py",
    "presentation",
    "application",
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
        if path.name.startswith(SKIP_DIR_PREFIXES):
            continue

        if _looks_like_django_app(path):
            apps.append(_scan_app(path))

    return apps


def _looks_like_django_app(path: Path) -> bool:
    return any((path / marker).exists() for marker in DJANGO_APP_MARKERS)


def _scan_app(app_path: Path) -> AppMeta:
    return AppMeta(
        name=app_path.name,
        path=app_path,
        views=_collect_files(app_path, VIEW_PATHS),
        serializers=_collect_files(app_path, SERIALIZER_PATHS),
        services=_collect_files(app_path, SERVICE_PATHS),
        usecases=_collect_files(app_path, USECASE_PATHS),
        entities=_collect_files(app_path, ENTITY_PATHS),
        orm_models=_collect_orm_models(app_path),
    )


def _collect_files(app_path: Path, names: Iterable[str]) -> List[Path]:
    results: List[Path] = []

    for name in names:
        results.extend(app_path.glob(f"{name}.py"))
        results.extend(app_path.glob(f"{name}/*.py"))

    files = sorted(set(results))
    return [p for p in files if p.name != "__init__.py"]


def _collect_orm_models(app_path: Path) -> List[Path]:
    """
    Collect Django ORM models from:
    1) adapters/orm/models.py (preferred)
    2) adapters/orm/models/*.py
    3) fallback to top-level models.py (legacy structure)
    """

    results: List[Path] = []

    # --- Primary: Clean Architecture style ---
    for base in ORM_MODEL_PATHS_PRIMARY:
        results.extend(app_path.glob(f"{base}.py"))
        results.extend(app_path.glob(f"{base}/*.py"))

    # --- Fallback: traditional Django style ---
    for base in ORM_MODEL_PATHS_FALLBACK:
        results.extend(app_path.glob(f"{base}.py"))
        results.extend(app_path.glob(f"{base}/*.py"))

    return sorted(set(results))