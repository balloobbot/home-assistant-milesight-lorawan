"""Tests for WS52x sockets."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from lorawan_connection import (
    AckEvent,
    DeviceDescriptor,
    Downlink,
    DownlinkError,
    UplinkEvent,
)
from lorawan_connection.mock import MockConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.milesight_lorawan._vendor.milesight_lorawan import WS52x


@pytest.fixture
def descriptor() -> DeviceDescriptor:
    """Describe a socket using the WS52x catalog profile."""
    brand, model = WS52x.identifiers["tts"]
    return DeviceDescriptor(
        network_id="network",
        dev_eui="0201010101010101",
        name="Plug",
        stack="tts",
        brand_id=brand,
        model_id=model,
        application_id="app",
        profile_id="profile",
    )


@pytest.fixture
async def setup_socket(
    hass: HomeAssistant,
    connection_entry: MockConfigEntry,
    config_entry: MockConfigEntry,
) -> None:
    """Set up socket entities."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("setup_socket")
async def test_readings(
    hass: HomeAssistant, mock_connection: MockConnection, descriptor: DeviceDescriptor
) -> None:
    """Decode Milesight's WS523 example and preserve newer readings."""
    assert hass.states.get("switch.plug").state == "unknown"
    event = UplinkEvent(
        descriptor=descriptor,
        received_at=datetime.now(UTC),
        f_port=85,
        data=bytes.fromhex("08700105812c07c94a0003743009068309660000048007000000"),
    )
    mock_connection.emit(event)
    for invalid in (
        replace(event, data=b"\x08"),
        replace(event, data=bytes.fromhex("087000037430")),
        replace(event, f_port=2, data=bytes.fromhex("087000")),
        replace(
            event,
            received_at=event.received_at - timedelta(seconds=1),
            data=bytes.fromhex("087000"),
        ),
    ):
        mock_connection.emit(invalid)
    await hass.async_block_till_done()
    assert hass.states.get("switch.plug").state == "on"
    expected = {
        "voltage": "235.2",
        "current": "74",
        "power": "7",
        "energy": "26121",
        "power_factor": "44",
    }
    for key, value in expected.items():
        assert hass.states.get(f"sensor.plug_{key}").state == value
    assert hass.states.get("sensor.plug_battery") is None
    assert (
        er.async_get(hass).async_get("switch.plug").unique_id
        == f"network:{descriptor.dev_eui}:socket"
    )
    mock_connection.emit(replace(event, data=bytes.fromhex("ff0101ff3f00087000")))
    await hass.async_block_till_done()
    assert hass.states.get("switch.plug").state == "off"
    assert hass.states.get("sensor.plug_power").state == "7"


@pytest.mark.usefixtures("setup_socket")
@pytest.mark.parametrize(
    ("service", "payload"), [("turn_on", "0801ffff"), ("turn_off", "0800ffff")]
)
async def test_commands(
    hass: HomeAssistant,
    mock_connection: MockConnection,
    descriptor: DeviceDescriptor,
    service: str,
    payload: str,
) -> None:
    """Send the manufacturer command and wait for its acknowledgement."""

    async def send(downlink: Downlink) -> str:
        assert downlink.data.hex() == payload
        assert downlink.f_port == 85
        assert downlink.confirmed
        mock_connection.emit(
            AckEvent(
                descriptor=descriptor,
                received_at=datetime.now(UTC),
                queue_item_id="command",
                acknowledged=True,
            )
        )
        return "command"

    with patch.object(mock_connection, "async_send_downlink", side_effect=send):
        await hass.services.async_call(
            "switch", service, {"entity_id": "switch.plug"}, blocking=True
        )
    assert hass.states.get("switch.plug").state == "unknown"


@pytest.mark.usefixtures("setup_socket")
async def test_command_failure(
    hass: HomeAssistant, mock_connection: MockConnection
) -> None:
    """Report rejected downlinks."""
    with (
        patch.object(
            mock_connection, "async_send_downlink", side_effect=DownlinkError("denied")
        ),
        pytest.raises(HomeAssistantError, match="Unable to send"),
    ):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.plug"}, blocking=True
        )


@pytest.mark.usefixtures("setup_socket")
async def test_timeout(hass: HomeAssistant) -> None:
    """Report missing acknowledgements."""
    with (
        patch(
            "custom_components.milesight_lorawan.switch.timeout",
            return_value=asyncio.timeout(0),
        ),
        pytest.raises(HomeAssistantError, match="Timed out"),
    ):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.plug"}, blocking=True
        )
