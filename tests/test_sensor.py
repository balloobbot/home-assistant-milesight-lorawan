"""Tests for Milesight sensor defaults."""

from dataclasses import replace
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from lorawan_connection import AddedEvent, DeviceDescriptor, StatusEvent, UplinkEvent
from lorawan_connection.mock import MockConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.milesight_lorawan._vendor.milesight_lorawan import UC51x


@pytest.mark.usefixtures("connection_entry")
async def test_valve_sensors(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: MockConnection,
    descriptor: DeviceDescriptor,
) -> None:
    """Expose valve telemetry and leave optional pressure disabled."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    brand_id, model_id = UC51x.identifiers["tts"]
    valve = replace(
        descriptor,
        dev_eui="0201010101010102",
        name="Valve",
        brand_id=brand_id,
        model_id=model_id,
    )
    mock_connection.emit(AddedEvent(descriptor=valve))
    await hass.async_block_till_done()
    assert hass.states.get("sensor.valve_valve_1").state == "unknown"
    mock_connection.emit(
        UplinkEvent(
            descriptor=valve,
            received_at=datetime.now(UTC),
            f_port=85,
            data=bytes.fromhex("01755c03010004c80500000005010106c808000000"),
        )
    )
    await hass.async_block_till_done()
    expected = {
        "battery": "92",
        "valve_1": "closed",
        "valve_2": "open",
        "pulse_count_1": "5",
        "pulse_count_2": "8",
    }
    for key, value in expected.items():
        assert hass.states.get(f"sensor.valve_{key}").state == value
    assert not hass.states.async_entity_ids("switch")
    pressure = er.async_get(hass).async_get("sensor.valve_pressure")
    assert pressure.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    await hass.config_entries.async_unload(config_entry.entry_id)


@pytest.mark.usefixtures("connection_entry")
async def test_status_battery(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: MockConnection,
    descriptor: DeviceDescriptor,
) -> None:
    """Use MAC battery status until the device reports its own percentage."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    mock_connection.emit(
        StatusEvent(
            descriptor=descriptor,
            received_at=datetime.now(UTC),
            battery_level=60,
            battery_level_unavailable=False,
        )
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_battery").state == "60"
    mock_connection.emit(
        UplinkEvent(
            descriptor=descriptor,
            received_at=datetime.now(UTC),
            f_port=85,
            data=bytes.fromhex("017500"),
        )
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_battery").state == "0"
    await hass.config_entries.async_unload(config_entry.entry_id)
