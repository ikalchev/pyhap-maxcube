"""Defines bridges to MAX! devices.

- Thermostat ``Accessory`` interfacing with a MAX! thermostat.
- MaxBridge, which discovers and bridges MAX! devices.
"""
import logging
import socket

from maxcube.connection import MaxCubeConnection
from maxcube.cube import MaxCube
from maxcube.device import (MAX_THERMOSTAT,
                            MAX_DEVICE_MODE_AUTOMATIC)

from pyhap import accessory, characteristic
from pyhap.const import CATEGORY_THERMOSTAT
from pyhap.util import event_wait


### Human-readable constants
MAX_MANUFACTURER = 'e-Q3'
THERMOSTAT_MODEL = 'MAX! Thermostat'
CUBE_MODEL = 'MAX! Cube'


class Thermostat(accessory.Accessory):
    """``Accessory`` interfacing with a MAX! Thermostat."""

    category = CATEGORY_THERMOSTAT

    model = THERMOSTAT_MODEL
    """The model of the MAX! line, e.g. Cube or Thermostat"""

    common_properties = {characteristic.PROP_MIN_STEP: 0.5}

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
        self.pending_updates = False

        # Set the AccessoryInformation service values from the device
        self.set_info_service(serial_number=device.serial,
                              manufacturer=MAX_MANUFACTURER,
                              model=self.model)

        # Add a Battery service and hook it to device.battery
        # XXX: Battery support is not in maxcube yet (opened a PR)
        '''
        battery = self.add_preload_service('BatteryService')
        low_battery = battery.get_characteristic('StatusLowBattery')
        battery.configure_char(
            'StatusLowBattery',
            value=device.battery
                or low_battery.properties['ValidValues']['BatteryLevelNormal'],
            getter_callback=lambda: self.device.battery
        )

        charging_state = battery.get_characteristic('ChargingState')
        battery.configure_char(
            'ChargingState',
            value=charging_state.properties['ValidValues']['NotChargeable'],
        )

        battery.configure_char(
            'BatteryLevel',
            getter_callback=
                lambda: 100 if self.device.battery == MAX_DEVICE_BATTERY_OK else 0
        )
        '''

        # Add a Thermostat service and hook it to the device
        service = self.add_preload_service('Thermostat')
        service.configure_char(
            'CurrentTemperature',
            value=device.actual_temperature,
            getter_callback=lambda: self.device.actual_temperature
                                 or self.device.target_temperature,
            properties=self.common_properties
        )

        service.configure_char(
            'TargetTemperature',
            value=device.target_temperature,
            setter_callback=self._set_target_temperature,
            getter_callback=lambda: self.device.target_temperature,
            properties=self.common_properties
        )

        service.configure_char(
            'CurrentHeatingCoolingState',
            value=self._current_state(),
            getter_callback=self._current_state,
        )

        service.configure_char(
            'TargetHeatingCoolingState',
            value=self._target_state(),
            getter_callback=self._target_state,
        )

        service.configure_char(
            'TemperatureDisplayUnits',
            value=0,  # Celsius
        )

    def _target_state(self):
        """Map device.mode to HAP heating state."""
        if (self.device.mode or MAX_DEVICE_MODE_AUTOMATIC) == MAX_DEVICE_MODE_AUTOMATIC:
            return 3  # Automatic
        else:
            return 0  # Off

    def _current_state(self):
        """ """
        if self.device.actual_temperature is None \
            or self.device.target_temperature is None:
            return 0
        if self.device.actual_temperature > self.device.target_temperature:
            return 0  # Off
        else:
            return 1  # Heat

    def _set_target_temperature(self, value):
        self.driver.add_job(self._do_set_target_temperature(value))

    async def _do_set_target_temperature(self, value):
        """ """
        while True:
            try:
                await self.driver.async_add_job(
                    self.cube.set_target_temperature, self.device, value)
            except socket.timeout:
                logging.warning('Timeout setting target temperature.')
            else:
                logging.debug('Successfully set target temperature to %s.', value)
                break

    def update(self):
        """Update the characteristics with the values in ``self.device``.
        """
        service = self.get_service('Thermostat')
        service.get_characteristic('CurrentTemperature')\
               .set_value(self.device.actual_temperature
                       or self.device.target_temperature)

        service.get_characteristic('TargetTemperature')\
               .set_value(self.device.target_temperature)

        service.get_characteristic('CurrentHeatingCoolingState')\
               .set_value(self._current_state())

        service.get_characteristic('TargetHeatingCoolingState')\
               .set_value(self._target_state())


class MaxBridge(accessory.Bridge):
    """A MaxBridge is a shim for discovering devices in a MAX! Cube and presenting them
    as HAP accessories.
    """

    def __init__(self, address, port, *args, update_interval=60, **kwargs):
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
        self.update_interval = 60
        self.discover()

    def discover(self):
        try:
            self.cube = MaxCube(MaxCubeConnection(self.address, self.port))
        except socket.timeout:
            logging.error('Could not connect to MAX! cube when setting up the bridge. '
                'Make sure nothing else is connected to the MAX! cube at start up and '
                'try again.')
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
        while not await event_wait(self.driver.aio_stop_event, self.update_interval):
            logging.debug('Updating MAX! info.')
            await self.update()

    async def update(self):
        """Fetch data from MAX! cube."""
        try:
            await self.driver.async_add_job(self.cube.update)
            for acc in self.accessories.values():
                acc.update()
        except socket.timeout as timeout_error:
            logging.warning('Could not update MAX! info, because of exception: %s',
                            timeout_error)

