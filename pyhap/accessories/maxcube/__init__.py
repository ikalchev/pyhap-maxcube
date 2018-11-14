"""Defines bridges to MAX! devices.

- Thermostat ``Accessory`` interfacing with a MAX! thermostat.
- MaxBridge, which discovers and Bridges MAX! devices.
"""
import logging

from maxcube.connection import MaxCubeConnection
from maxcube.cube import MaxCube
from maxcube.device import (MAX_THERMOSTAT,
                            MAX_DEVICE_MODE_AUTOMATIC,
                            MAX_DEVICE_BATTERY_OK)

from pyhap import accessory
from pyhap.const import CATEGORY_THERMOSTAT
from pyhap.util import event_wait


MAX_MANUFACTURER = 'e-Q3'
THERMOSTAT_MODEL = 'MAX! Thermostat'
CUBE_MODEL = 'MAX! Cube'


class Thermostat(accessory.Accessory):
    """``Accessory`` interfacing with a MAX! Thermostat."""

    category = CATEGORY_THERMOSTAT

    model = THERMOSTAT_MODEL
    """The model of the MAX! line, e.g. Cube or Thermostat"""

    def __init__(self, cube, device, *args, **kwargs):
        """Create a Thermostat for the given ``device``.

        The ``device`` must be part of the ``cube``.

        :type cube: ``maxcube.cube.MaxCube``
        :type device: ``maxcube.device`` having the ``MAX_THERMOSTAT`` type.
        """
        if device.type != MAX_THERMOSTAT:
            raise ValueError('The given device is not a thermostat: %s' % device)

        super().__init__(*args, display_name=device.name, **kwargs)

        self.cube = cube
        self.device = device

        # Set the AccessoryInformation service values from the device
        self.set_info_service(serial_number=device.serial,
                              manufacturer=MAX_MANUFACTURER,
                              model=self.model)

        # Add a Battery service and hook it to device.battery
        battery = self.add_preload_service('BatteryService')
        battery.configure_char(
            'StatusLowBattery',
            value=device.battery or 0,
            getter_callback=lambda: self.device.battery
        )

        battery.configure_char(
            'StatusLowBattery',
            value=2,  # NotChargeable
        )

        battery.configure_char(
            'BatteryLevel',
            getter_callback=
                lambda: 100 if self.device.battery == MAX_DEVICE_BATTERY_OK else 0
        )

        # Add a Thermostat service and hook it to the device
        service = self.add_preload_service('Thermostat')
        service.configure_char(
            'CurrentTemperature',
            value=device.actual_temperature,
            getter_callback=lambda: self.device.actual_temperature or 0)

        service.configure_char(
            'TargetTemperature',
            value=device.target_temperature,
            setter_callback=lambda x: self.cube.set_target_temperature(self.device, x),
            getter_callback=lambda: self.device.target_temperature or 0
        )

        service.configure_char(
            'CurrentHeatingCoolingState',
            value=self._state(),
            getter_callback=self._state,
        )

        service.configure_char(
            'TargetHeatingCoolingState',
            value=self._state(),
            getter_callback=self._state,
        )

        service.configure_char(
            'TemperatureDisplayUnits',
            value=0,  # Celsius
        )

    def _state(self):
        """Map device.mode to HAP heating state."""
        if self.device.mode == MAX_DEVICE_MODE_AUTOMATIC:
            mode = 3  # Automatic
        else:
            mode = 0  # Off
        return mode


class MaxBridge(accessory.Bridge):
    """A MaxBridge is a shim for discovering devices in a MAX! Cube and presenting them
    as HAP accessories.
    """

    def __init__(self, address, port, *args, **kwargs):
        """Create a bridge to the MAX! Cube running on the given address.

        After initialisation, it will attempt to discover all Thermostats and create
        ``Accessory`` objects for each. The accessories will be added in this
        ``MaxBridge``.

        :param address: MAX! Cube address.
        :param port: MAX! Cube port.
        """
        super().__init__(*args, **kwargs)
        self.address = address
        self.port = port
        self.cube = None
        self.discover()

    def discover(self):
        self.cube = MaxCube(MaxCubeConnection(self.address, self.port))
        for device in self.cube.devices:
            if device.type != MAX_THERMOSTAT:
                logging.info('Discovered non-thermostat')
                continue
            self.add_accessory(Thermostat(self.cube, device, self.driver))

    async def run(self):
        """Call run on the ``Bridge`` and start to fetch updates from the Cube regularly.

        :see: ``update``
        """
        await super().run()
        await self.update()

    async def update(self):
        """Fetch the data from MAX! cube every 30 seconds."""
        while not await event_wait(self.driver.aio_stop_event, 30):
            await self.driver.async_add_job(self.cube.update)
