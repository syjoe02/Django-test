from typing import Dict, List
from pathlib import Path

from .meta.scanner_meta import ScanResult
from .meta.parser_meta import EndpointMeta


def build_spec(scan: ScanResult, endpoints: List[EndpointMeta]) -> Dict:
    project_name = scan.project_root.name

    return {
        "project": {
            "name": project_name,
            "framework": "Django REST Framework",
            "settings_module": scan.settings_module,
        },
        "endpoints": [_endpoint_to_spec(ep) for ep in endpoints],
    }


def _endpoint_to_spec(ep: EndpointMeta) -> Dict:
    method = ep.http_methods[0] if ep.http_methods else "GET"

    return {
        "app": ep.app,
        "view": ep.view_name,
        "method": method,
        "url_hint": ep.url_hint,
        "serializer": ep.serializer,
        "test_cases": _default_test_cases(method),
    }


def _default_test_cases(method: str) -> Dict:
    cases = {
        "success": {
            "expected_status": 200,
        }
    }

    if method in {"POST", "PUT", "PATCH"}:
        cases["failure"] = [
            {
                "case": "invalid_payload",
                "expected_status": 400,
            }
        ]

    return cases