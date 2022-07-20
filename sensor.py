"""GitHub sensor platform."""
import logging
from typing import Any, Dict, Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorEntity, SensorStateClass
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.const import FREQUENCY_HERTZ, TEMP_CELSIUS
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .const import DOMAIN, LISTENING_PORT
from .server import LoggerServer

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType,
    config_entry: ConfigType,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([LoggerServerEntity(hass, config, async_add_entities)])


class LoggerServerEntity(Entity):
    should_poll = False
    name = 'Solis/Ginglong Local Logger Server'

    def __init__(self, hass, config_data, async_add_entities):
        _LOGGER.error("Config data: %s", config_data)
        self.hass = hass
        self._server = LoggerServer(config_data[LISTENING_PORT], self._on_data)
        self._async_add_entities = async_add_entities
        self._inverters = dict()

        dummy_data = {'inverter_serial_number': '110CD22170500290', 'inverter_temperature': 32.5, 'dc_voltage_pv1': 4.5, 'dc_current': 0.0, 'ac_current_t_w_c': 0.0, 'ac_voltage_t_w_c': 225.4,
                      'ac_output_frequency': 50.0, 'daily_active_generation': 22.5, 'total_dc_input_power': 0.0, 'total_active_generation': 57.0, 'generation_yesterday': 25.200000000000003, 'power_grid_total_apparent_power': 0.0}
        self._on_data(dummy_data)

    def _on_data(self, data: Dict[str, Any]):
        _LOGGER.error("Got data: %s", data)
        inverter_id = data["inverter_serial_number"].lower()
        inverter_logger = self._inverters.get(inverter_id, None)
        if inverter_logger is None:
            _LOGGER.error("Creating new inverter logger for %s", inverter_id)
            inverter_logger = InverterLoggerComponent(self.hass, self._async_add_entities, inverter_id)
            self._inverters[inverter_id] = inverter_logger
        inverter_logger.set_data(data)

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        await self._server.start_server()

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        await self._server.stop_server()


class InverterLoggerComponent:
    def __init__(self, hass: HomeAssistantType, async_add_entities, inverter_id: str):
        self.inverter_id = inverter_id
        # Create all necesary entities
        entities_descriptions = [
            LoggerSensorEntityDescription(
                name='Temperature',
                key='temp',
                get_value=lambda x: x.data['inverter_temperature'],
                device_class=SensorDeviceClass.TEMPERATURE,
                native_unit_of_measurement=TEMP_CELSIUS,
            ),
            LoggerSensorEntityDescription(
                name='Output frequency',
                key='ac_output_frequency',
                get_value=lambda x: x.data['ac_output_frequency'],
                device_class=SensorDeviceClass.FREQUENCY,
                native_unit_of_measurement=FREQUENCY_HERTZ,
            ),
        ]
        self.entities = []
        for entity_desc in entities_descriptions:
            entity = InverterLoggerBaseEntity(self, hass, entity_desc)
            self.entities.append(entity)
        async_add_entities(self.entities)

    def set_data(self, data: Dict[str, Any]):
        self.data = data
        for entity in self.entities:
            entity.async_schedule_update_ha_state()


@dataclass
class LoggerSensorEntityDescription(SensorEntityDescription):
    """A class that describes Logger sensor entities."""

    get_value: Callable[[InverterLoggerComponent], Any] = lambda _: True
    state_class: SensorStateClass.MEASUREMENT


class InverterLoggerBaseEntity(SensorEntity):
    should_poll = False

    def __init__(self, inverter: InverterLoggerComponent, hass: HomeAssistantType, entity_description: LoggerSensorEntityDescription):
        self._inverter = inverter
        self.hass = hass
        self.entity_description = entity_description
        self._attr_unique_id = f'{self._inverter.inverter_id}_{entity_description.key}'
        self.entity_id = f'{DOMAIN}.{self._inverter.inverter_id}_{self.entity_description.key}'
        self.get_value = entity_description.get_value

    @property
    def device_info(self) -> DeviceInfo:
        """Return information to link this entity with the correct device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._inverter.inverter_id)},
            manufacturer='Solis/Ginglong',
            model=self._inverter.inverter_id,
            name='Solis/Ginglong Inverter',
        )

    @property
    def native_value(self) -> Any:
        return self.get_value(self._inverter)
