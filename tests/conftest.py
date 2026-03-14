from pathlib import Path

import pytest


@pytest.fixture
def team_path() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def inbox_dir(team_path) -> Path:
    return team_path / "inboxes"
