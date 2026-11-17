# Changelog

## 1.0.0b1 (unreleased)

- Support Home Assistant 2025.8.0 and Python 3.13 with the RC4 client's wider
  dependency bounds and exception syntax compatible with older Python versions.
- Resolve the RC1 dependency conflict with the RC2 client, which accepts HA
  Bluetooth's Bleak 3.0.2 pin. Keep the CI compatibility guard for future updates.
- Migrate to `daybetter-ble-client==1.0.0rc3`, with P031 and P065 discovery.
- Initialize P031/P065 state using RC3 snapshots and poll every 30 seconds, with
  immediate status-notification updates and unavailable state after read failures.
- Cancel pending status reads before disconnecting and keep RSSI/ACK updates from
  masking failed reads or deferring polling.
- Preserve the `daybetter_led` domain and existing device/entity identifiers.
- Keep established connections across advertisements and stop pending connection
  work during unload/shutdown or failed setup.
- Add offline tests, release validation, HACS branding, CI-gated tag releases,
  dependency maintenance, and native macOS HA development on port 8124.
- Update project links and support ownership to `jnstockley/ha-daybetter-ble-devices`.
