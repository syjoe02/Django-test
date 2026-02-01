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
def spec(
    project_root: str = typer.Argument(".", help="Django project root"),
    settings: str = typer.Option(None, "--settings"),
    output: str = typer.Option(
        "django_test_spec.json",
        "--output",
        help="Output spec JSON file",
    ),
):
    """
    Generate machine-readable Django test spec (JSON only).
    """
    from pathlib import Path
    import json

    from .scanner import scan_project
    from .parser import parse_project
    from .parser_urls import attach_urls
    from .spec_builder import build_spec

    root = Path(project_root).resolve()
    _ensure_manage_py(root)

    print("[bold cyan]Scanning Django project...[/bold cyan]")
    scan = scan_project(str(root), settings=settings)

    print("[bold cyan]Parsing API endpoints...[/bold cyan]")
    endpoints = parse_project(scan)

    print("[bold cyan]Resolving URL patterns...[/bold cyan]")
    endpoints = attach_urls(scan, endpoints)

    print("[bold cyan]Building test spec...[/bold cyan]")
    spec = build_spec(scan, endpoints)

    out_path = root / output
    out_path.write_text(
        json.dumps(spec, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n✅ [bold green]Spec generated:[/bold green] {out_path}")


def _ensure_manage_py(project_root: Path):
    manage_py = project_root / "manage.py"
    if not manage_py.exists():
        print("[red]Error:[/red] manage.py not found in project root")
        raise typer.Exit(code=1)

@app.command()
def generate(
    spec_file: str = typer.Argument(..., help="django_test_spec.json"),
    provider: str = typer.Option("gemini", "--provider"),
    output_dir: str = typer.Option("tests", "--output-dir"),
):
    from .generator.test_generator import TestGenerator
    from .generator.writer import write_test
    import json

    spec = json.loads(Path(spec_file).read_text())
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    generator = TestGenerator(provider)

    for ep in spec["endpoints"]:
        if not ep.get("url"):
            continue

        print(f"[cyan]Generating test for[/cyan] {ep['view_name']}")
        code = generator.generate_test_code(spec, ep)
        write_test(ep, code, output_path)

    print(f"\n✅ Tests generated in {output_path}")

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