import os
import subprocess
import sys
from typing import Tuple, Optional


DEFAULT_TIMEOUT = 300  # seconds (5 minutes)


def run_tests(
    project_root: str,
    settings: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[int, str, str]:
    """
    Returns:
        (exit_code, stdout, stderr)
    """

    manage_py = os.path.join(project_root, "manage.py")
    if not os.path.exists(manage_py):
        return 1, "", "manage.py not found"

    env = os.environ.copy()

    if settings:
        env["DJANGO_SETTINGS_MODULE"] = settings

    env.setdefault("PYTHONUNBUFFERED", "1")

    cmd = [
        sys.executable,
        "manage.py",
        "test",
        "--verbosity",
        "2",
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr

    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        stderr += f"\n[django-test] ERROR: Test execution timed out after {timeout}s\n"
        return 124, stdout, stderr

    except Exception as e:
        return 1, "", f"[django-test] Unexpected runner error: {e}"