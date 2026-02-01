from typing import List, Dict, Any
from .meta.scanner_meta import ScanResult
from .meta.parser_meta import EndpointMeta


def build_spec(scan: ScanResult, endpoints: List[EndpointMeta]) -> Dict[str, Any]:
    """
    Convert ScanResult + EndpointMeta list into
    AI-friendly django-test spec JSON.
    """

    return {
        "project": {
            "name": scan.project_root.name,
            "framework": "Django REST Framework",
            "settings_module": scan.settings_module,
        },
        "apps": [
            {
                "name": app.name,
                "path": str(app.path),
                "usecases": [str(p) for p in app.usecases],
                "services": [str(p) for p in app.services],
                "models": [str(p) for p in app.models],
            }
            for app in scan.apps
        ],
        "endpoints": [
            _endpoint_to_spec(ep)
            for ep in endpoints
            if ep.url_hint
        ],
    }


def _endpoint_to_spec(ep: EndpointMeta) -> Dict[str, Any]:
    return {
        "app": ep.app,
        "view": ep.view_name,
        "method": ep.http_methods[0] if ep.http_methods else "GET",
        "url": ep.url_hint,
        "serializer": ep.serializer,
        "test_cases": _default_test_cases(ep),
    }


def _default_test_cases(ep: EndpointMeta) -> Dict[str, Any]:
    cases = {
        "success": {
            "expected_status": 200,
        }
    }

    if ep.http_methods and any(m in {"POST", "PUT", "PATCH"} for m in ep.http_methods):
        cases["failure"] = [
            {
                "case": "invalid_payload",
                "expected_status": 400,
            }
        ]

    return cases