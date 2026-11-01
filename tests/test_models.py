"""Tests for Milesight payloads."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from lorawan_connection import DeviceDescriptor, UplinkEvent
from lorawan_connection.mock import MockConnection
import pytest

from custom_components.milesight_lorawan._vendor.milesight_lorawan import (
    TS201,
    MilesightDevices,
    UC51x,
)


@pytest.mark.parametrize(
    ("model", "payload", "expected"),
    [
        (
            TS201,
            "01756103672201",
            {"temperature": 29.0, "reported_battery_percent": 97},
        ),
        (TS201, "93673401640002", {"temperature": 30.8, "temperature_alarm": 2}),
        (TS201, "0367baff", {"temperature": -7.0}),
        (
            UC51x,
            "01755c03010004c80500000005010106c808000000",
            {
                "reported_battery_percent": 92,
                "valve_1_open": False,
                "valve_2_open": True,
                "valve_1_pulse_count": 5,
                "valve_2_pulse_count": 8,
            },
        ),
    ],
)
async def test_payload(
    model: type[TS201 | UC51x],
    payload: str,
    expected: dict[str, float | bool],
    descriptor: DeviceDescriptor,
) -> None:
    """Decode captures and codec examples through the collection."""
    brand_id, model_id = model.identifiers["tts"]
    descriptor = replace(descriptor, brand_id=brand_id, model_id=model_id)
    connection = MockConnection([descriptor], stack_type="tts")
    collection = MilesightDevices(connection)
    await collection.async_setup()
    device = collection.devices[descriptor.dev_eui]
    event = UplinkEvent(
        received_at=datetime.now(UTC),
        descriptor=descriptor,
        f_port=85,
        data=bytes.fromhex(payload),
    )
    connection.emit(event)
    assert {key: getattr(device, key) for key in expected} == expected
    connection.emit(replace(event, data=b"\x01"))
    connection.emit(replace(event, f_port=99))
    connection.emit(
        replace(
            event,
            received_at=event.received_at - timedelta(seconds=1),
            data=bytes.fromhex("017500"),
        )
    )
    assert {key: getattr(device, key) for key in expected} == expected
    collection.close()


def test_temperature_fault() -> None:
    """Report a sensor fault as an unknown measurement."""
    assert TS201.decode(bytes.fromhex("b36700")) == {
        "temperature": None,
        "temperature_error": True,
    }


@pytest.mark.parametrize(
    ("model", "payload"),
    [(TS201, "20cec79afa6402bdff"), (UC51x, "20ce3fa109641700000000")],
)
def test_history(model: type[TS201 | UC51x], payload: str) -> None:
    """Ignore historical records when updating current readings."""
    assert model.decode(bytes.fromhex(payload)) == {}


@pytest.mark.parametrize("payload", ["01", "0175", "0175ff", "036701"])
def test_invalid_payload(payload: str) -> None:
    """Reject incomplete records and invalid battery levels."""
    with pytest.raises(ValueError):
        TS201.decode(bytes.fromhex(payload))
