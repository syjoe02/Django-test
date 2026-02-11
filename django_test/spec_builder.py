from typing import List, Dict, Any, Optional
from .meta.scanner_meta import ScanResult
from .meta.parser_meta import EndpointMeta


def build_spec(scan: ScanResult, endpoints: List[EndpointMeta]) -> Dict[str, Any]:
    """
    Convert ScanResult + EndpointMeta list into
    AI-friendly django-test spec JSON.
    """

    return {
        "spec_version": "1.0",
        "project": {
            "name": scan.project_root.name,
            "framework": "Django REST Framework",
            "settings_module": scan.settings_module,
            "root_path": str(scan.project_root),
        },
        "apps": [
            _app_to_spec(app)
            for app in scan.apps
        ],
        "endpoints": [
            _endpoint_to_spec(ep)
            for ep in endpoints
            if ep.url_hint
        ],
        "conventions": {
            "success_default_status": 200,
            "invalid_payload_status": 400,
            "auth_header": "Authorization: Bearer <token>",
        }
    }


def _app_to_spec(app) -> Dict[str, Any]:
    return {
        "name": app.name,
        "path": str(app.path),
        "layers": {
            # Domain (for use-case / service tests)
            "entities": [str(p) for p in getattr(app, "entities", [])],

            # Infrastructure / DB (MOST IMPORTANT for API tests)
            "orm_models": [str(p) for p in getattr(app, "orm_models", [])],

            # Application layer
            "usecases": [str(p) for p in app.usecases],
            "services": [str(p) for p in app.services],
        }
    }


def _endpoint_to_spec(ep: EndpointMeta) -> Dict[str, Any]:
    method = ep.http_methods[0] if ep.http_methods else "GET"

    return {
        "app": ep.app,
        "view": ep.view_name,
        "method": method,
        "url": ep.url_hint,
        "path_params": _extract_path_params(ep.url_hint),
        "serializer": ep.serializer,
        "requires_auth": getattr(ep, "requires_auth", True),
        "test_cases": _default_test_cases(ep, method),
        "metadata": {
            "has_body": method in {"POST", "PUT", "PATCH"},
            "is_list_endpoint": "list" in (ep.view_name or "").lower(),
            "is_detail_endpoint": "<" in (ep.url_hint or ""),
        }
    }


def _default_test_cases(ep: EndpointMeta, method: str) -> Dict[str, Any]:
    cases = {
        "success": {
            "expected_status": 200,
            "assertions": [
                "status_code == expected_status",
                "response is valid JSON"
            ]
        }
    }

    # More concrete failure cases (LLM-friendly)
    if method in {"POST", "PUT", "PATCH"}:
        cases["failure"] = [
            {
                "case": "empty_payload",
                "input": {},
                "expected_status": 400,
                "assertions": [
                    "status_code == expected_status"
                ]
            },
            {
                "case": "wrong_type",
                "input": {"__example_field__": "invalid_type"},
                "expected_status": 400,
                "assertions": [
                    "status_code == expected_status"
                ]
            }
        ]

    return cases


def _extract_path_params(url: str) -> List[Dict[str, str]]:
    """
    Convert: /api/calendar/events/<uuid:event_id>/
    -> [{"name": "event_id", "type": "uuid"}]
    """
    params = []
    if "<" in url and ">" in url:
        parts = url.split("<")[1:]
        for p in parts:
            if ">" in p:
                content = p.split(">")[0]  # e.g. "uuid:event_id"
                if ":" in content:
                    typ, name = content.split(":", 1)
                else:
                    typ, name = "str", content
                params.append({"name": name, "type": typ})
    return params