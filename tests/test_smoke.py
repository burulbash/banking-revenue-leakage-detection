from __future__ import annotations

from src.config import PROJECT_ROOT, REPORTS_DIR


def test_project_paths_exist() -> None:
    assert PROJECT_ROOT.exists()
    assert REPORTS_DIR.parent.exists()
