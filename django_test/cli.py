import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

import typer
from rich import print

from .scanner import scan_project
from .parser import parse_project
from .parser_urls import attach_urls
from .spec_builder import build_spec
from .runner import run_tests

app = typer.Typer(help="django-test: inspect Django project & run tests")

# ======================================================
# Shared helpers
# ======================================================

def _ensure_manage_py(project_root: Path):
    manage_py = project_root / "manage.py"
    if not manage_py.exists():
        print("[red]Error:[/red] manage.py not found in project root")
        raise typer.Exit(code=1)


def _scan_and_parse(
    project_root: Path,
    settings: Optional[str] = None,
    with_urls: bool = True,
):
    """
    Common pipeline used by multiple commands.
    """
    print("[bold cyan]Scanning Django project...[/bold cyan]")
    scan = scan_project(str(project_root), settings=settings)

    print("[bold cyan]Parsing API endpoints...[/bold cyan]")
    endpoints = parse_project(scan)

    if with_urls:
        print("[bold cyan]Resolving URL patterns...[/bold cyan]")
        endpoints = attach_urls(scan, endpoints)

    return scan, endpoints


def _make_run_dir(base_output_dir: str) -> Path:
    """
    Create a unique, timestamped run directory.
    """
    base = Path(base_output_dir).resolve()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = base / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


# ======================================================
# Commands
# ======================================================

@app.command()
def inspect(
    project_root: str = typer.Argument(".", help="Django project root"),
    with_urls: bool = typer.Option(
        False,
        "--with-urls",
        help="Resolve URL patterns from urls.py and attach to endpoints",
    ),
):
    """
    Human-friendly inspection of the project structure + endpoints.
    """
    root = Path(project_root).resolve()
    _ensure_manage_py(root)

    scan, endpoints = _scan_and_parse(root, with_urls=with_urls)

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
                "entities": [str(p) for p in getattr(app, "entities", [])],
                "orm_models": [str(p) for p in getattr(app, "orm_models", [])],
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
    settings: Optional[str] = typer.Option(None, "--settings"),
    output: str = typer.Option(
        "django_test_spec.json",
        "--output",
        help="Output spec JSON file",
    ),
):
    """
    Generate machine-readable Django test spec (AI-friendly JSON).
    """
    root = Path(project_root).resolve()
    _ensure_manage_py(root)

    scan, endpoints = _scan_and_parse(root, settings=settings, with_urls=True)

    print("[bold cyan]Building test spec...[/bold cyan]")
    spec = build_spec(scan, endpoints)

    out_path = root / output
    out_path.write_text(
        json.dumps(spec, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n✅ [bold green]Spec generated:[/bold green] {out_path}")


@app.command()
def generate(
    spec_file: str = typer.Argument(..., help="django_test_spec.json"),
    provider: str = typer.Option("gemini", "--provider"),
    output_dir: str = typer.Option("tests", "--output-dir"),
):
    """
    Generate pytest test files from spec.
    """
    from .generator.test_generator import TestGenerator
    from .generator.writer import write_test

    spec = json.loads(Path(spec_file).read_text())

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    generator = TestGenerator(provider)

    print(f"[bold cyan]Using provider:[/bold cyan] {provider}")

    for ep in spec.get("endpoints", []):
        if not ep.get("url"):
            continue

        view = ep.get("view") or ep.get("view_name")

        print(f"[cyan]Generating test for[/cyan] {view}")
        code = generator.generate_test_code(spec, ep)
        write_test(ep, code, output_path)

    print(f"\n✅ Tests generated in {output_path}")


@app.command()
def run_ml(
    project_root: str = typer.Argument("."),
    base_output_dir: str = typer.Option(
        "../django-test/django-test/runs",
        help="Base directory to store all ML runs",
    ),
):
    """
    ONE COMMAND PIPELINE:
    1) make tmp_spec.json
    2) run pytest tests.py
    3) save test_results.json
    """

    from pathlib import Path
    import subprocess, json
    from datetime import datetime

    root = Path(project_root).resolve()
    _ensure_manage_py(root)

    # ---- Create unique run directory ----
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = (Path(base_output_dir).resolve() / f"run_{timestamp}")
    run_dir.mkdir(parents=True, exist_ok=True)

    spec_path = run_dir / "tmp_spec.json"
    result_path = run_dir / "test_results.json"

    print(f"[bold cyan]Run directory:[/bold cyan] {run_dir}")

    # ==============================
    # STEP 1: Generate tmp_spec.json
    # ==============================
    print("[bold cyan]Generating tmp_spec.json...[/bold cyan]")
    subprocess.run(
        [
            "django-test",
            "spec",
            str(root),
            "--output",
            str(spec_path),
        ],
        check=True,
    )

    # =====================================
    # STEP 2: Run tests.py → test_results.json
    # =====================================
    print("[bold cyan]Running pytest tests.py...[/bold cyan]")
    subprocess.run(
        [
            "pytest",
            "tests.py",
            "--json-report",
            f"--json-report-file={result_path}",
        ],
        cwd=root,
        check=False,  # don't crash if tests fail
    )

    # ---- Optional: save run metadata ----
    meta = {
        "project_root": str(root),
        "run_dir": str(run_dir),
        "spec_path": str(spec_path),
        "result_path": str(result_path),
        "timestamp": timestamp,
    }

    (run_dir / "run_meta.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ tmp_spec.json saved to: {spec_path}")
    print(f"✅ test_results.json saved to: {result_path}")