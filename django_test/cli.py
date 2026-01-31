# django_test/cli.py
import typer
from rich import print
import json
from pathlib import Path

from .scanner import scan_project
from .parser import parse_project
from .parser_urls import attach_urls
from .runner import run_tests

app = typer.Typer(help="django-test: inspect Django project & run tests")


@app.command()
def inspect(
    project_root: str = typer.Argument(".", help="Django project root"),
    with_urls: bool = typer.Option(
        False,
        "--with-urls",
        help="Resolve URL patterns from urls.py and attach to endpoints",
    ),
):
    scan = scan_project(project_root)
    endpoints = parse_project(scan)

    if with_urls:
        print("[bold cyan]Resolving URLs...[/bold cyan]")
        endpoints = attach_urls(scan, endpoints)

    output = {
        "project_root": str(scan.project_root),
        "settings_module": scan.settings_module,
        "apps": [
            {
                "name": app.name,
                "views": [str(p) for p in app.views],
                "serializers": [str(p) for p in app.serializers],
                "services": [str(p) for p in app.services],
                "usecases": [str(p) for p in app.usecases],
                "models": [str(p) for p in app.models],
            }
            for app in scan.apps
        ],
        "endpoints": [
            {
                "app": e.app,
                "view_name": e.view_name,
                "view_type": e.view_type,
                "http_methods": e.http_methods,
                "serializer": e.serializer,
                "url": e.url_hint if with_urls else None,
                "file": str(e.file),
            }
            for e in endpoints
        ],
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


@app.command()
def run(
    project_root: str = typer.Argument(".", help="Django project root"),
):
    code, out, err = run_tests(project_root)
    print(out)
    if err:
        print("[red]" + err + "[/red]")

@app.command()
def version():
    print("django-test v0.1.0")

if __name__ == "__main__":
    app()