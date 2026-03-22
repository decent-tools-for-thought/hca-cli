from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from hca_cli import __version__

pytestmark = pytest.mark.packaging_smoke


def test_module_entrypoint_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else f"{src_path}:{existing_pythonpath}"

    result = subprocess.run(
        [sys.executable, "-m", "hca_cli", "api", "describe", "GET", "/index/catalogs"],
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert '"operation": "GET /index/catalogs"' in result.stdout


def test_package_version_matches_project_metadata() -> None:
    assert __version__ == "0.1.0"
