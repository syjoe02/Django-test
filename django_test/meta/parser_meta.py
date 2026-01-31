from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class EndpointMeta:
    app: str
    view_name: str
    file: Path

    view_type: str        # "APIView" | "ViewSet" | "FunctionView"
    http_methods: List[str]

    serializer: Optional[str] = None
    url_hint: Optional[str] = None