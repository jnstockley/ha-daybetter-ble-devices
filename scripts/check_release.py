"""Validate installable HACS metadata, release tags, branding and the client API."""

from __future__ import annotations

import argparse
import ast
import json
import re
import struct
import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?\Z")
REPOSITORY = "https://github.com/jnstockley/ha-daybetter-ble-devices"


def check_dependency_compatibility(
    client_requirements: list[str], bluetooth_requirements: list[str]
) -> None:
    """Reject incompatible client bounds for HA's exact Bluetooth dependencies."""
    pins = {}
    for text in bluetooth_requirements:
        requirement = Requirement(text)
        for specifier in requirement.specifier:
            if specifier.operator == "==":
                pins[canonicalize_name(requirement.name)] = specifier.version
    for text in client_requirements:
        requirement = Requirement(text)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        if (
            pin := pins.get(canonicalize_name(requirement.name))
        ) is not None and pin not in requirement.specifier:
            raise ValueError(
                f"HA Bluetooth pins {requirement.name}=={pin}, but the client requires "
                f"{requirement}. Publish a compatible client release before releasing this integration."
            )


def validate_ha_compatibility() -> None:
    """Check the installed HA/client packages without starting Bluetooth."""
    ha = distribution("homeassistant")
    client = distribution("daybetter-ble-client")
    manifest = json.loads(
        ha.locate_file("homeassistant/components/bluetooth/manifest.json").read_text()
    )
    check_dependency_compatibility(client.requires or [], manifest["requirements"])


def validate(tag: str | None = None, install_requirement: bool = False) -> str:
    """Reject releases that HACS cannot install or whose metadata is inconsistent."""
    integration = ROOT / "custom_components/daybetter_led"
    manifest = json.loads((integration / "manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    version = manifest["version"]
    if not VERSION.fullmatch(version):
        raise ValueError(f"Invalid version: {version}")
    if tag is not None and tag != f"v{version}":
        raise ValueError(f"Tag {tag} does not match v{version}")
    directories = [
        p.name
        for p in (ROOT / "custom_components").iterdir()
        if p.is_dir() and not p.name.startswith("__")
    ]
    if directories != ["daybetter_led"] or manifest["domain"] != "daybetter_led":
        raise ValueError("Keep exactly one integration with the daybetter_led domain")
    constants = ast.parse((integration / "const.py").read_text())
    domains = [
        ast.literal_eval(n.value)
        for n in constants.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "DOMAIN" for t in n.targets)
    ]
    if domains != [manifest["domain"]]:
        raise ValueError("Python DOMAIN must match the manifest")
    if (
        manifest.get("documentation") != REPOSITORY
        or manifest.get("issue_tracker") != f"{REPOSITORY}/issues"
        or "@jnstockley" not in manifest.get("codeowners", [])
    ):
        raise ValueError("Documentation, issues and ownership must point to the fork")
    if hacs.get("name") != manifest["name"] or not hacs.get("homeassistant"):
        raise ValueError("HACS needs a matching name and minimum HA version")
    requirements = manifest.get("requirements", [])
    if len(requirements) != 1 or not re.fullmatch(
        r"daybetter-ble-client==\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?", requirements[0]
    ):
        raise ValueError("Pin exactly one published daybetter-ble-client version")
    for filename in (
        "__init__.py",
        "config_flow.py",
        "strings.json",
        "translations/en.json",
        "icons.json",
    ):
        if not (integration / filename).is_file():
            raise ValueError(f"Missing integration file: {filename}")
    for path in integration.rglob("*.json"):
        json.loads(path.read_text())
    if json.loads((integration / "strings.json").read_text()) != json.loads(
        (integration / "translations/en.json").read_text()
    ):
        raise ValueError("English translations must match strings.json")
    for filename, size in (("icon.png", 256), ("icon@2x.png", 512)):
        data = (integration / "brand" / filename).read_bytes()
        if (
            len(data) < 33
            or data[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            or struct.unpack(">II", data[16:24]) != (size, size)
        ):
            raise ValueError(f"Brand {filename} must be a {size}x{size} PNG")
    for filename in ("README.md", "LICENSE"):
        if not (ROOT / filename).is_file():
            raise ValueError(f"Missing repository file: {filename}")
    if install_requirement:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--force-reinstall",
                requirements[0],
            ],
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                "-c",
                "from daybetter_ble_client import DaybetterLedStrip; from daybetter_ble_client.const import Effect, SUPPORTED_DISCOVERY_SERVICES; assert len(SUPPORTED_DISCOVERY_SERVICES) == 2; assert all(hasattr(DaybetterLedStrip, method) for method in ('async_refresh_state', 'update_device', 'disconnect', 'on_change', 'set_color', 'set_brightness', 'set_effect', 'set_power')); assert hasattr(DaybetterLedStrip('00:00:00:00:00:00'), 'disconnect_reason')",
            ],
            check=True,
        )
    return version


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    parser.add_argument("--install-requirement", action="store_true")
    parser.add_argument("--check-ha-compatibility", action="store_true")
    args = parser.parse_args()
    try:
        if args.check_ha_compatibility:
            validate_ha_compatibility()
        print(
            f"Validated Daybetter BLE release {validate(args.tag, args.install_requirement)}"
        )
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as err:
        parser.exit(1, f"Release validation failed: {err}\n")
