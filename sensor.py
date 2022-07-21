"""GitHub sensor platform."""
import logging
from typing import Any, Dict, Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorEntity, SensorStateClass
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import FREQUENCY_HERTZ, TEMP_CELSIUS, ELECTRIC_POTENTIAL_VOLT, POWER_WATT, ELECTRIC_CURRENT_AMPERE, ENERGY_WATT_HOUR
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .const import DOMAIN, LISTENING_PORT
from .server import LoggerServer

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    logger_server = LoggerServerEntity(hass, config, async_add_entities)
    async_add_entities([logger_server])


class LoggerServerEntity(Entity):
    should_poll = False
    name = 'Solis/Ginglong Local Logger Server'

    def __init__(self, hass: HomeAssistantType, config_data: Dict[str, Any], async_add_entities: AddEntitiesCallback):
        _LOGGER.error("Config data: %s", config_data)
        self.hass = hass
        self._server = LoggerServer(config_data[LISTENING_PORT], self._on_data)
        self._async_add_entities = async_add_entities
        self._inverters = dict()

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
        # dummy_data = {'inverter_serial_number': '110CD22170500290', 'inverter_temperature': 62.300000000000004, 'dc_voltage': 282.8, 'dc_current': 10.8, 'ac_current_t_w_c': 13.100000000000001, 'ac_voltage_t_w_c': 227.5,
        #               'ac_output_frequency': 49.97, 'daily_active_generation': 13.200000000000001, 'total_dc_input_power': 3054, 'total_active_generation': 70.0, 'generation_yesterday': 22.5, 'power_grid_total_apparent_power': 2980.0, 'power_consumption': 1618}
        # self._on_data(dummy_data)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        await self._server.stop_server()


class InverterLoggerComponent:
    def __init__(self, hass: HomeAssistantType, async_add_entities: AddEntitiesCallback, inverter_id: str):
        self.inverter_id = inverter_id
        self.hass = hass
        self.entities = [InverterLoggerBaseEntity(self, entity_desc) for entity_desc in ENTITIES_DESCRIPTIONS]
        async_add_entities(self.entities)

    def set_data(self, data: Dict[str, Any]):
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
        name='Net power usage',
        key='net_power_usage',
        get_value=lambda x: x.data['power_consumption'] - x.data['total_dc_input_power'],
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=POWER_WATT,
        state_class=SensorStateClass.TOTAL,
    ),
    LoggerSensorEntityDescription(
        name='Grid power consumption',
        key='grid_power_consumption',
        get_value=lambda x: max(x.data['power_consumption'] - x.data['total_dc_input_power'], 0),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
    ),
    LoggerSensorEntityDescription(
        name='Grid power return',
        key='grid_power_return',
        get_value=lambda x: max(x.data['total_dc_input_power'] - x.data['power_consumption'], 0),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
    ),
    LoggerSensorEntityDescription(
        name='Power consumption',
        key='power_consumption',
        get_value=lambda x: x.data['power_consumption'],
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=POWER_WATT,
    ),
    LoggerSensorEntityDescription(
        name='Solar power generation',
        key='solar_power_generation',
        get_value=lambda x: x.data['total_dc_input_power'],
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
    ),
    LoggerSensorEntityDescription(
        name='Inverter temperature',
        key='inverter_temperature',
        get_value=lambda x: x.data['inverter_temperature'],
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    LoggerSensorEntityDescription(
        name='DC input voltage',
        key='dc_input_voltage',
        get_value=lambda x: x.data['dc_voltage'],
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
    ),
    LoggerSensorEntityDescription(
        name='DC input current',
        key='dc_input_current',
        get_value=lambda x: x.data['dc_current'],
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
    ),
    LoggerSensorEntityDescription(
        name='AC output voltage',
        key='ac_output_voltage',
        get_value=lambda x: x.data['ac_voltage_t_w_c'],
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
    ),
    LoggerSensorEntityDescription(
        name='AC output frequency',
        key='ac_output_frequency',
        get_value=lambda x: x.data['ac_output_frequency'],
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=FREQUENCY_HERTZ,
    ),
]


class InverterLoggerBaseEntity(SensorEntity):
    should_poll = False

    def __init__(self, inverter: InverterLoggerComponent, entity_description: LoggerSensorEntityDescription):
        self._inverter = inverter
        self.hass = self._inverter.hass
        self.entity_description = entity_description
        self._attr_unique_id = f'{self._inverter.inverter_id}_{self.entity_description.key}'
        self.get_value = entity_description.get_value
        self.loaded = False
        self.pending_update = False

    def notify_state_changed(self):
        if self.loaded:
            self.async_schedule_update_ha_state()
        else:
            self.pending_update = True

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self.loaded = True
        if self.pending_update:
            self.notify_state_changed()

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
