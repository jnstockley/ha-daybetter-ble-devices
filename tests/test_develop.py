"""Development setup preserves user state and refuses conflicting paths."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "develop", Path(__file__).parents[1] / "scripts/develop.py"
)
develop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(develop)


def test_init_is_idempotent_and_loads_checkout(tmp_path):
    develop.initialize(tmp_path)
    config = tmp_path / "configuration.yaml"
    assert "server_port: 8124" in config.read_text()
    config.write_text("# private local changes\n")
    develop.initialize(tmp_path)
    assert config.read_text() == "# private local changes\n"
    assert (
        tmp_path / "custom_components/daybetter_led"
    ).resolve() == develop.ROOT / "custom_components/daybetter_led"


def test_init_refuses_existing_integration_directory(tmp_path):
    (tmp_path / "custom_components/daybetter_led").mkdir(parents=True)
    with pytest.raises(FileExistsError):
        develop.initialize(tmp_path)
