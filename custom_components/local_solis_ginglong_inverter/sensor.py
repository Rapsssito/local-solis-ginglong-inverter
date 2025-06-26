"""Sensor platform for Solis/Ginglong Local Logger integration."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, FORWARD_MODE, LISTENING_PORT
from .server import LoggerServer

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure sensors from a configuration entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    logger_server = LoggerServerEntity(hass, config, async_add_entities)
    async_add_entities([logger_server])


class LoggerServerEntity(Entity):
    """Representation of a Solis/Ginglong Local Logger server."""

    should_poll = False
    name = "Solis/Ginglong Local Logger Server"
    suggested_object_id = "solis_local_logger_server_entity"

    def __init__(
        self,
        hass: HomeAssistant,
        config_data: dict[str, Any],
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Initialize the Solis/Ginglong Local Logger server."""
        _LOGGER.debug("Config data: %s", config_data)
        self.hass = hass
        self._server = LoggerServer(config_data[LISTENING_PORT], self.__on_data, forward=config_data.get(FORWARD_MODE, False))
        self._async_add_entities = async_add_entities
        self._inverters = {}

    def __on_data(self, data: dict[str, Any]) -> None:
        inverter_id = data["inverter_serial_number"].lower()
        inverter_logger = self._inverters.get(inverter_id, None)
        if inverter_logger is None:
            _LOGGER.debug("Creating new inverter logger for %s", inverter_id)
            inverter_logger = InverterLoggerComponent(self.hass, self._async_add_entities, inverter_id)
            self._inverters[inverter_id] = inverter_logger
        inverter_logger.set_data(data)

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        await self._server.start_server()

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        await self._server.stop_server()


class InverterLoggerComponent:
    """Representation of a Solis/Ginglong Local Logger inverter."""

    def __init__(
        self,
        hass: HomeAssistant,
        async_add_entities: AddEntitiesCallback,
        inverter_id: str,
    ) -> None:
        """Initialize the inverter logger component."""
        self.inverter_id = inverter_id
        self.hass = hass
        self.entities = [InverterLoggerBaseEntity(self, entity_desc) for entity_desc in ENTITIES_DESCRIPTIONS]
        self.data = None
        async_add_entities(self.entities)

    def set_data(self, data: dict[str, Any]) -> None:
        """Update all entities with new data."""
        self.data = data
        for entity in self.entities:
            entity.notify_state_changed()


@dataclass
class LoggerSensorEntityDescription(SensorEntityDescription):
    """A class that describes Logger sensor entities."""

    get_value: Callable[[InverterLoggerComponent], Any] = lambda _: True
    state_class: SensorStateClass.MEASUREMENT


ENTITIES_DESCRIPTIONS = [
    LoggerSensorEntityDescription(
        name="Load active power",
        key="load_active_power",
        get_value=lambda x: x.data["solar_active_power"] - x.data["export_active_power"],
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:home-lightning-bolt",
    ),
    LoggerSensorEntityDescription(
        name="Grid net power",
        key="grid_net_power",
        get_value=lambda x: x.data["export_active_power"],
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:transmission-tower",
    ),
    LoggerSensorEntityDescription(
        name="Grid export power",
        key="grid_export_power",
        get_value=lambda x: max(0, x.data["export_active_power"]),
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:transmission-tower-import",
    ),
    LoggerSensorEntityDescription(
        name="Grid import power",
        key="grid_import_power",
        get_value=lambda x: max(0, -x.data["export_active_power"]),
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:transmission-tower-export",
    ),
    LoggerSensorEntityDescription(
        name="Inverter temperature",
        key="inverter_temperature",
        get_value=lambda x: x.data["inverter_temperature"],
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    LoggerSensorEntityDescription(
        name="DC voltage 1",
        key="dc_voltage_1",
        get_value=lambda x: x.data["dc_voltage_1"],
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:current-dc",
    ),
    LoggerSensorEntityDescription(
        name="DC voltage 2",
        key="dc_voltage_2",
        get_value=lambda x: x.data["dc_voltage_2"],
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:current-dc",
    ),
    LoggerSensorEntityDescription(
        name="DC current 1",
        key="dc_current_1",
        get_value=lambda x: x.data["dc_current_1"],
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-dc",
    ),
    LoggerSensorEntityDescription(
        name="DC current 2",
        key="dc_current_2",
        get_value=lambda x: x.data["dc_current_2"],
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-dc",
    ),
    LoggerSensorEntityDescription(
        name="DC power",
        key="dc_power",
        get_value=lambda x: x.data["dc_power"],
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    LoggerSensorEntityDescription(
        name="AC voltage",
        key="ac_voltage",
        get_value=lambda x: x.data["ac_voltage"],
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    LoggerSensorEntityDescription(
        name="Solar AC current",
        key="solar_ac_current",
        get_value=lambda x: x.data["solar_ac_current"],
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    LoggerSensorEntityDescription(
        name="AC frequency",
        key="ac_frequency",
        get_value=lambda x: x.data["ac_frequency"],
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
    ),
    LoggerSensorEntityDescription(
        name="Solar active power",
        key="solar_active_power",
        get_value=lambda x: x.data["solar_active_power"],
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:solar-power",
    ),
    LoggerSensorEntityDescription(
        name="Solar active energy today",
        key="solar_active_energy_today",
        get_value=lambda x: x.data["solar_active_energy_today"],
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:solar-power",
    ),
    LoggerSensorEntityDescription(
        name="Solar active energy yesterday",
        key="solar_active_energy_yesterday",
        get_value=lambda x: x.data["solar_active_energy_yesterday"],
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:solar-power",
    ),
    LoggerSensorEntityDescription(
        name="Solar active energy total",
        key="solar_active_energy_total",
        get_value=lambda x: x.data["solar_active_energy_total"],
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:solar-power",
    ),
    LoggerSensorEntityDescription(
        name="Solar active this month",
        key="solar_active_energy_this_month",
        get_value=lambda x: x.data["solar_active_energy_this_month"],
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:solar-power",
    ),
]


class InverterLoggerBaseEntity(SensorEntity):
    """Representation of a Solis/Ginglong Local Logger inverter sensor."""

    should_poll = False

    def __init__(
        self,
        inverter: InverterLoggerComponent,
        entity_description: LoggerSensorEntityDescription,
    ) -> None:
        """Initialize the Solis/Ginglong Local Logger inverter sensor."""
        self._inverter = inverter
        self.hass = self._inverter.hass
        self.entity_description = entity_description
        self._attr_unique_id = f"{self._inverter.inverter_id}_{self.entity_description.key}"
        self.get_value = entity_description.get_value
        self.loaded = False
        self.pending_update = False

    def notify_state_changed(self) -> None:
        """Notify Home Assistant that the state has changed."""
        if self.loaded:
            self.async_schedule_update_ha_state()
        else:
            self.pending_update = True

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self.loaded = True
        if self.pending_update:
            self.notify_state_changed()

    @property
    def device_info(self) -> DeviceInfo:
        """Return information to link this entity with the correct device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._inverter.inverter_id)},
            manufacturer="Solis/Ginglong",
            model=self._inverter.inverter_id,
            name="Solis/Ginglong Inverter",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self._inverter.data is None:
            return None
        return self.get_value(self._inverter)
