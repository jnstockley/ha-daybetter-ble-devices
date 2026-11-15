# Repository guidelines

The HA integration lives in `custom_components/daybetter_led/`; keep that domain
and existing device/entity identifiers stable. The published backend is
`daybetter-ble-client`, imported as `daybetter_ble_client`. Keep protocol logic in
the client. `connection.py` owns pending connection work; HA owns discovery and
Bluetooth adapter routing. Preserve cancellation and entry cleanup.

Use Python 3.14 and `scripts/setup`. Local HA runs from `.venv-ha` with private
configuration in `.ha-dev` on localhost port 8124. Never commit credentials or
modify production configuration. The tracked seed is `dev/configuration.yaml`.

Validate with `scripts/lint`, `.venv-ha/bin/python -m pytest -q`,
`.venv-ha/bin/python -m compileall -q custom_components scripts tests`, and
`.venv-ha/bin/python scripts/check_release.py --install-requirement`. The last
command replaces an editable client with the published manifest requirement.
CI additionally runs hassfest and HACS validation. Tests remain offline; report
physical device verification separately. Use the README hardware matrix.

Keep `strings.json` and `translations/en.json` consistent. Runtime requirements
are exactly pinned in `manifest.json`; development requirements live in
`requirements-test.txt`. For release changes update manifest, README and changelog;
`v` tags must match the manifest version. Keep PR descriptions concise and include
validation evidence. Redact device addresses and packets before sharing logs.
