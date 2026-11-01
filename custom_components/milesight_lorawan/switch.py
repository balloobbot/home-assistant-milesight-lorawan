"""Milesight switches."""

from asyncio import timeout
from typing import TYPE_CHECKING, Any, override

from homeassistant.components.lorawan import LoRaWANEntity
from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lorawan_connection import DownlinkError

from . import MilesightConfigEntry
from ._vendor.milesight_lorawan import MilesightDevice, WS52x
from .const import DOMAIN
from .coordinator import MilesightCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MilesightConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Milesight switches."""

    @callback
    def added(coordinator: MilesightCoordinator) -> None:
        if isinstance(coordinator.data, WS52x):
            async_add_entities(
                [
                    MilesightSocket(
                        coordinator,
                        SwitchEntityDescription(
                            key="socket",
                            name=None,
                            device_class=SwitchDeviceClass.OUTLET,
                        ),
                    )
                ]
            )

    entry.async_on_unload(entry.runtime_data.subscribe_coordinator_added(added))


class MilesightSocket(LoRaWANEntity[MilesightDevice], SwitchEntity):
    """Represent a Milesight socket."""

    coordinator: MilesightCoordinator

    @property
    @override
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info

    @property
    @override
    def is_on(self) -> bool | None:
        device = self.device
        if TYPE_CHECKING:
            assert isinstance(device, WS52x)
        return device.socket_on

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_socket(True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_socket(False)

    async def _async_set_socket(self, on: bool) -> None:
        device = self.device
        if TYPE_CHECKING:
            assert isinstance(device, WS52x)
        try:
            async with timeout(30):
                await device.async_set_socket(on)
        except TimeoutError as error:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_timeout"
            ) from error
        except DownlinkError as error:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from error
