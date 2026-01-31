from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class AppMeta:
    name: str
    path: Path
    views: List[Path]
    serializers: List[Path]
    services: List[Path]
    usecases: List[Path]
    models: List[Path]


@dataclass
class ScanResult:
    project_root: Path
    settings_module: str
    apps: List[AppMeta]