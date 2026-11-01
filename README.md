[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=balloobbot&repository=home-assistant-milesight-lorawan&category=integration)

# Milesight LoRaWAN

Use Milesight devices with Home Assistant's LoRaWAN connections.
Requires Home Assistant 2026.11.0b0 or newer, including 2026.11 beta releases.

## Install

1. Open the HACS link above and download the integration.
2. Restart Home Assistant.
3. Configure a connection supported by your device in the table below.
4. Add your device to the network server using its official catalog profile.
5. Open **Settings > Devices & services** and configure the discovered
   **Milesight LoRaWAN** integration. You can also select it under **Add integration**.

To install manually, copy `custom_components/milesight_lorawan` into your Home
Assistant `config/custom_components` directory and restart.

## Devices

| Model | Entities | Connections |
| --- | --- | --- |
| WS523 (WS52x profile) | Socket switch, voltage, current, power, energy, and power factor | The Things Network / The Things Stack |
| TS201 | Temperature and battery percentage | The Things Network / The Things Stack |
| UC511 / UC512 | Valve states, pulse counters, battery percentage, and pressure | The Things Network / The Things Stack |

UC511 and UC512 valve states are read-only. This integration does not send valve
commands. The optional pressure sensor is disabled by default.

For WS523, select **Milesight WS52x Portable Socket** in the TTN device catalog.
Socket commands wait up to 30 seconds for acknowledgement. The switch state
changes when the socket reports it. A timeout leaves the queued command on
the network server.

Devices are matched by catalog identity. Renaming a custom profile to a supported
model does not make it discoverable. One integration entry handles matching
devices across all configured LoRaWAN connections.

Readings remain unknown until an uplink or status report supplies them.

Brand images are included in the integration's `brand` directory.

## Development

The device library is bundled under `custom_components/milesight_lorawan/_vendor`.
It uses the shared LoRaWAN dependency provided by Home Assistant.

Tests use Home Assistant's official pytest helpers and an in-memory connection.
They cover discovery, decoded readings, entity identity, connection loss,
reconnection, and removal.
The TS201 fixture includes a captured physical-device uplink. UC51x and WS523 tests use manufacturer codec examples. WS523 commands are tested with simulated acknowledgements.

```sh
uv sync --group dev
uv run python script/prepare_tests.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The development environment pins Core and its test helpers to the same revision.
CI also tests current Home Assistant `dev`.

Payload references: [Milesight codecs](https://github.com/Milesight-IoT/SensorDecoders).

The WS523 profile was identified from [LoRaWANDeviceProfiles](https://github.com/BenAhrdt/LoRaWANDeviceProfiles/tree/main/DeviceProfiles/Mileslight/WS523). Measurements and commands follow [Milesight’s WS523 protocol](https://github.com/Milesight-IoT/SensorDecoders/tree/main/ws-series/ws523).
