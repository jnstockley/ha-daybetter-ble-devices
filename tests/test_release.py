"""Reject broken distribution contracts before publishing a GitHub release."""

import json
import shutil

import pytest

from scripts import check_release


@pytest.fixture
def release(tmp_path, monkeypatch):
    root = check_release.ROOT
    for name in ("README.md", "LICENSE", "hacs.json"):
        shutil.copy(root / name, tmp_path / name)
    shutil.copytree(
        root / "custom_components",
        tmp_path / "custom_components",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    monkeypatch.setattr(check_release, "ROOT", tmp_path)
    return tmp_path


def test_matching_tag_is_accepted(release):
    manifest = json.loads(
        (release / "custom_components/daybetter_led/manifest.json").read_text()
    )
    version = manifest["version"]
    assert check_release.validate(f"v{version}") == version


def test_mismatched_tag_is_rejected(release):
    with pytest.raises(ValueError, match="does not match"):
        check_release.validate("v1.0.0")


def test_unpinned_dependency_is_rejected(release):
    path = release / "custom_components/daybetter_led/manifest.json"
    manifest = json.loads(path.read_text())
    manifest["requirements"] = ["daybetter-ble-client>=1.0.0rc3"]
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Pin exactly"):
        check_release.validate()


def test_upstream_support_link_is_rejected(release):
    path = release / "custom_components/daybetter_led/manifest.json"
    manifest = json.loads(path.read_text())
    manifest["issue_tracker"] = (
        "https://github.com/grimsteel/homeassistant-daybetter-led-strip/issues"
    )
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="fork"):
        check_release.validate()


def test_missing_brand_asset_is_rejected(release):
    (release / "custom_components/daybetter_led/brand/icon.png").unlink()
    with pytest.raises(FileNotFoundError):
        check_release.validate()


def test_ha_bluetooth_dependency_conflict_blocks_release():
    with pytest.raises(ValueError, match="bleak.*3.0.2.*3.1.0"):
        check_release.check_dependency_compatibility(
            ["bleak>=3.1.0,<4"], ["bleak==3.0.2"]
        )


def test_compatible_client_bounds_allow_release():
    check_release.check_dependency_compatibility(["bleak>=3.0.2,<4"], ["bleak==3.0.2"])
