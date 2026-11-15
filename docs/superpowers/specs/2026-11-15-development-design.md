# Daybetter integration modernization

Keep the `daybetter_led` domain and existing entity identifiers. Use the maintained
`daybetter-ble-client==1.0.0rc3` package and release this integration as `1.0.0b1`.
Support connectable P031 and P065 advertisements through Home Assistant's Bluetooth
manager. Retain light effects, color correction, and diagnostic sensors.

## Approaches

The user selected preserving the integration domain while adopting the sibling
`ha-govee-ble-devices` repository's development and release practices. Renaming
the domain would require migration of saved entries and entities without adding
functionality, so it was rejected.

## Implementation boundaries

Use offline pytest tests, a release validator, Ruff, hassfest, HACS validation,
Renovate, and tag-driven GitHub prereleases. Use exact dependency pins for a
reproducible Home Assistant 2026.10.3 / Python 3.14 development environment.
Keep the upstream MIT attribution; route installation, support, and documentation
to `jnstockley/ha-daybetter-ble-devices`.

Native macOS development uses `.venv-ha`, an ignored `.ha-dev` configuration,
a source symlink, and localhost port 8124 to avoid the Govee instance on 8123.
Provide an explicit editable-client override without changing release requirements.
Do not publish, push, or modify production Home Assistant. Hardware tests require
an available strip and macOS Bluetooth permission; offline tests cannot certify RF.

Builder decisions: preserve the existing display name and entity keys; require
connectable advertisements; serialize advertisement updates; cancel background
connection work before disconnecting; ship local brand icons. Do not redesign
client protocol handling or copy Govee's model-specific transaction implementation.

## Dependency compatibility

RC1 required Bleak >=3.1.0 and conflicted with HA's 3.0.2 pin. The user requested
RC2 after publishing updated requirements. RC2 accepts `bleak>=3.0.2,<4`, so the
compatibility blocker is resolved. Retain the CI compatibility gate to reject
future conflicting dependencies. Physical device and native shutdown validation
remain separate from dependency compatibility.

## RC3 state synchronization

The user requested RC3 to address initially unknown and stale external state on
P031/P065. Retain its automatic initial status read and notification subscription.
Use HA coordinator polling every 30 seconds via the public async_refresh_state API.
Propagate read failures to availability and track/cancel in-flight reads on close.
RSSI/ACK updates must neither recover failed reads nor defer periodic requests.
New validated snapshots recover availability. Keep entity identifiers stable and
use local_polling metadata now that full snapshots can be read. Offline tests use
the published client and simulated GATT; physical behavior is a separate check.
