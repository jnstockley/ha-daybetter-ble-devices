# Daybetter BLE Devices for Home Assistant

Local Bluetooth control of Daybetter **P031 and P065 RGB LED strips**, using
[`daybetter-ble-client==1.0.0rc5`](https://github.com/jnstockley/daybetter-led-strip).
No cloud account is needed. Home Assistant owns Bluetooth discovery and adapter
routing. Integration version: **1.0.0b3**; requires **Home Assistant 2025.8.0+**.

## Installation

1. In HACS (or Marketplace where available), open **Custom repositories**, add
   `https://github.com/jnstockley/ha-daybetter-ble-devices`, and select **Integration**.
2. Download **Daybetter LED Strip**. Enable prereleases to select **1.0.0b3**,
   then restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → Daybetter LED Strip**.
   Select a discovered device; repeat for each strip. Bluetooth discovery also
   offers setup automatically.

[![Open the repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jnstockley&repository=ha-daybetter-ble-devices&category=integration)

Home Assistant must be able to install the pinned client from PyPI. A strip must
be in range of a supported local Bluetooth adapter or **active/connectable**
ESPHome Bluetooth proxy. Passive-only receivers cannot control these devices.
Close the Daybetter phone app before connecting; a strip accepts one connection
at a time. The integration retains its `daybetter_led` domain, config-entry
version, device identifiers, and entity unique IDs for existing installations.
Replace the upstream repository in HACS rather than installing both copies.

This fork can be installed as a custom repository; inclusion in the default
HACS/Marketplace catalog is a separate review process. Releases become available
only after the corresponding tag has been pushed and CI has published a release.
Use the HACS/Marketplace update UI to install subsequent releases and restart HA.

## Devices and behavior

| Feature | P031 | P065 |
| --- | --- | --- |
| Power, RGB color, brightness | Yes | Yes |
| Built-in effects | Yes | Yes, individual firmware support may vary |
| Color correction option | Yes | Yes |
| Bluetooth address and RSSI diagnostics | Yes | Yes |
| Connection initialization | Standard | Authenticated handshake managed by client |

Color correction is enabled by default; change it in the entry's integration
options. Brightness is mapped between HA's 0–255 and the strip's 0–100 range.
Use the power control to switch off: strip brightness zero can still emit light.
The integration retains an active connection and reconnects on later
advertisements after a disconnect. Repeated advertisements do not tear down a
working connection, and overlapping connection attempts are coalesced.

The client requests a validated status snapshot when connecting, after the
P065 handshake where applicable. Power, brightness, RGB color (in color mode), and
supported effects are populated from that snapshot before initial setup completes.
If the initial read times out, setup is retried rather than treating missing state
as a successful connection.

Incoming status notifications update HA immediately. The integration also reads
current status every **30 seconds** while entities are active, reconciling changes
made through the remote or another controller. Frequent RSSI advertisements do not
postpone status polling. A failed read marks entities unavailable; RSSI updates or
command acknowledgements alone do not clear that failure. A subsequent successful
read or validated status notification restores availability. Unload and shutdown
cancel pending reads before disconnecting.
Distinct transport failures are logged with their exception type and a sanitized
message. Repeated failures with the same cause are condensed until a successful
read. Propagated reconnect errors are logged with sanitized details as well.

The phone app can interrupt HA's connection; close it to let HA reconnect and read
a fresh snapshot. An acknowledged HA command may appear before the next observed
snapshot, which is authoritative. Unknown effect IDs and inactive RGB fields are
not reconstructed from previous commands. Physical light output, firmware-specific
state formats, and app/remote synchronization still require hardware verification.
No automatic replay of failed user controls is added by the integration.

<p float="left">
<img alt="Device page" src="assets/screenshot-device.png" width="66%" />
<img alt="Light controls" src="assets/screenshot-light.png" width="33%" />
</p>

Local brand icons ship in `custom_components/daybetter_led/brand/` for modern
Home Assistant. See the [brand asset guidance](https://developers.home-assistant.io/docs/creating_integration_manifest/#brand).

## Native macOS development

This follows the sibling [Govee integration](https://github.com/jnstockley/ha-govee-ble-devices)
and HA's [development environment guidance](https://developers.home-assistant.io/docs/development_environment/).
Use **Python 3.14** and install Home Assistant's media prerequisites if needed:

```sh
brew install ffmpeg jpeg-turbo
python3 --version
scripts/setup
.venv-ha/bin/python scripts/develop.py check
scripts/develop
```

Open **http://127.0.0.1:8124**, create a local owner account, and add
**Daybetter LED Strip** under Devices & services. Port **8124** avoids the Govee
development instance's default port 8123. `.ha-dev/configuration.yaml` binds to
localhost; edit that private file to change the port or logging. The first check
or startup needs internet access to install additional HA integration dependencies.
Bluetooth discovery can install dependencies for other nearby devices too. If the
first startup reports a CFFI Python/backend version mismatch after installing
packages, stop HA completely and start it again so both parts load from the same
installed version. Do not install development dependencies while HA is running.

`scripts/setup` creates `.venv-ha`, installs the pinned test environment and
published client, then seeds `.ha-dev` and symlinks the integration from this
checkout. Re-running setup preserves local configuration and refuses to overwrite
an unrelated integration directory. `.ha-dev` contains credentials, logs and the
database; it and `.venv-ha` are ignored by Git. HACS is unnecessary in this instance.

To test changes in the client too, explicitly opt into an editable checkout:

```sh
scripts/setup --client ../daybetter-led-strip
```

This affects only the development environment. The integration's manifest remains
pinned to the published RC. Run `scripts/setup` without `--client` to restore the
published dependency, or use the release validation command below. Restart HA
after changing either package; symlinks and editable installs do not hot-reload code.

The earlier RC1 smoke test served onboarding but exposed a PyObjC/CoreBluetooth
exception during shutdown. Physical device connections and clean native shutdown
still need verification with the current client; passing offline checks does not
establish either.

Allow Bluetooth access for Terminal or your editor in **System Settings → Privacy
& Security → Bluetooth**. A macOS `SIGKILL` on scanner startup can indicate missing
Bluetooth permission; restart the launching app after granting it. Docker Desktop
and a devcontainer do not expose the Mac's native Bluetooth adapter: use native
macOS for these hardware checks. The included devcontainer remains useful for CI
and offline development; its localhost-bound server may need an explicit bind
change in its private configuration to make port forwarding work.

Press **Ctrl+C** and wait for shutdown before restarting. If the terminal is lost,
find the listener with `lsof -nP -iTCP:8124 -sTCP:LISTEN`, inspect its command with
`ps -p PID -o command=`, and send `kill -TERM PID` only after confirming it belongs
to this checkout. This lets HA close BLE connections and its database gracefully.

A strip can connect to only one controller. Disable its production integration
entry while testing, or use a spare strip. Do not add a production ESPHome proxy
to this development instance because competing subscriptions can disrupt it.

## Validation

```sh
.venv-ha/bin/python scripts/check_release.py --install-requirement
.venv-ha/bin/python -m pytest -q
.venv-ha/bin/python -m compileall -q custom_components scripts tests
scripts/lint
.venv-ha/bin/python scripts/develop.py check
```

Tests run offline with real HA flow/coordinator classes and simulated Bluetooth
I/O. CI additionally runs **hassfest** and **HACS validation**, including branding.
Check the client requirements against Home Assistant's Bluetooth dependencies:

```sh
.venv-ha/bin/python scripts/check_release.py --check-ha-compatibility
```

The release validator checks metadata, local icons, the exact client pin, public
client imports, and tag/version agreement. `--install-requirement` restores the
published client if an editable override is installed. Renovate is configured for
Actions, Python requirements and the HA manifest; enable the Renovate GitHub App
on this repository to receive update PRs. Update HA/test pins together.

Before deploying Bluetooth changes, test on macOS, Linux/BlueZ and an active proxy:

| Scenario | Verify |
| --- | --- |
| Discovery | P031/P065 appear; unrelated, passive-only and duplicate devices do not |
| Controls | Power, RGB, brightness and representative effects visibly apply |
| Reconnect | Disconnect/power-cycle the strip; availability recovers on advertisements |
| Repeated advertisements | A working connection remains usable without reconnect churn |
| Unload/reload and shutdown | Connection work stops and the device slot is released |
| Multiple strips / slot pressure | Devices recover independently when slots become available |

Offline tests do not establish RF reliability, firmware compatibility, or proxy
performance. Record the model, firmware, HA version and adapter/proxy for hardware
results. No new hardware verification is implied by this migration.

## Releases and maintenance

1. Update the manifest version, client pin if applicable, and [CHANGELOG.md](CHANGELOG.md).
2. Run validation and confirm the **Validate** workflow passes on the default branch.
3. Push a matching tag, for example **`v1.0.0b3`**. CI requires all Python,
   hassfest and HACS jobs to pass before publishing the GitHub Release. Alpha,
   beta and RC tags produce prereleases. No release ZIP is needed for this layout.

Keep the repository public, with a short description, relevant topics, and Issues
enabled. See [HACS publishing requirements](https://www.hacs.xyz/docs/publish/start/)
and [integration requirements](https://www.hacs.xyz/docs/publish/integration/).
Creating a release or enabling repository settings is a separate GitHub action;
local repository changes alone do not publish anything.

For troubleshooting, enable debug logging from the integration page. The manifest
includes `daybetter_ble_client` so HA's debug controls also capture client logs.
Redact Bluetooth addresses, device names and raw packets before sharing, and
restore normal logging after diagnosis. Report issues at
[jnstockley/ha-daybetter-ble-devices/issues](https://github.com/jnstockley/ha-daybetter-ble-devices/issues).

## Attribution

Forked from the Daybetter LED Strip integration by **grimsteel**. The original
MIT copyright and license are preserved in [LICENSE](LICENSE). The maintained
backend and protocol documentation are in
[jnstockley/daybetter-led-strip](https://github.com/jnstockley/daybetter-ble-client).
