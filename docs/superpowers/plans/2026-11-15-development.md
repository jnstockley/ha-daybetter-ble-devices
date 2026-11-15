# Daybetter Development Implementation Plan

**Goal:** Bring Daybetter packaging, validation, releases, and native HA development into line with the Govee integration.
**Architecture:** Preserve the integration domain and entity IDs; migrate the published client and improve discovery/lifecycle boundaries. Keep development state out of the distributed integration.
**Tech stack:** Python 3.14, HA 2026.10.3, pytest, Ruff, GitHub Actions.
**Spec:** `docs/superpowers/specs/2026-11-15-development-design.md`

## Global constraints

- Domain `daybetter_led`; integration `1.0.0b1`; client `1.0.0rc3`.
- Repository `jnstockley/ha-daybetter-ble-devices`.
- Native macOS Bluetooth; localhost port 8124; no production configuration changes.

## Review focus

- P065 and P031 discovery, duplicates, passive-only and unrelated advertisements.
- Connection work must not survive unload or failed setup.
- Existing entity IDs, effects, options, and initial availability must survive migration.
- Release validation must reject mismatched tags or unpublished client packages.
- Development initialization must preserve local configuration and reject occupied paths.

## Tasks

1. [x] Add offline discovery and lifecycle regression tests; observe failures, then migrate client imports, both discovery services, and lifecycle cleanup. Run pytest against the published client and real HA.
2. [x] Add `scripts/check_release.py`, metadata, brand icons, CI and Renovate. Exercise validator success and invalid tag/dependency cases.
3. [x] Replace template development scripts with isolated native HA setup, optional editable client, and configuration checks. Test idempotent setup and collisions with temporary directories.
4. [x] Update README, CONTRIBUTING, repository guidelines and all project links. Run complete pytest, release validation, Ruff, compileall and HA configuration check; report hardware limitations.

Execution: inline in the shared checkout. Git branch creation was blocked by the
workspace's read-only `.git` permissions; leave changes reviewable and uncommitted.

## Verification and rulings

- Twenty offline tests pass; Ruff lint/format, compileall, shell syntax and
  release metadata/tag checks pass. Official hassfest reports zero invalid integrations.
- HA configuration check passes and its native server serves onboarding (HTTP 200)
  on 127.0.0.1:8124. No physical device control was performed.
- RC1 initially conflicted with HA's pinned Bleak. The user subsequently requested
  the published RC2, whose updated requirements accept HA's 3.0.2 pin. The
  compatibility check now passes; retain it in CI to protect future releases.
- First live startup installed discovered integrations' dependencies and encountered
  an in-process CFFI version mismatch; stop/restart guidance is documented.
- Independent review found a test expectation inconsistent with HA brightness scaling;
  changed the fixture to full brightness (100 maps to 255) without changing conversion.
- Work remains uncommitted in the shared checkout; branch creation was denied by
  read-only git metadata. No remote publication or repository settings were changed.

- The second startup cleared the CFFI mismatch. Native shutdown then aborted in
  a PyObjC/CoreBluetooth callback after HA began stopping; no listener remained
  on port 8124. Record as an environment limitation, not a certified clean shutdown.
- Preserve live RSSI updates separately from the client's connection advertisement,
  so avoiding reconnection churn does not freeze diagnostic signal strength.

## RC3 follow-up

- [x] Verify the published RC3 API and compatible HA Bluetooth requirements.
- [x] Add real-client/radio-double regressions for initial P031/P065 state,
  polling, remote notifications, failed reads, RSSI timing, and cancellation.
- [x] Implement coordinator polling, read ownership, and fresh-status recovery.
- [x] Update the client pin, local_polling metadata, state documentation and changelog.
- [x] Run the final suite, dependency checks, HA configuration check, and hassfest.

The public PyPI index served RC3 before the configured index caught up; installing
from public PyPI succeeded. Keep production requirements as the normal package pin.
Independent review found no material lifecycle or scheduling issue.

RC3 verification: 29 offline tests pass with Bleak 3.0.2; Ruff, compileall,
release/tag/compatibility validation, pip check and git diff checks pass.
