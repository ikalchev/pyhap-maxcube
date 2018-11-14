# Beta! pyhap-maxcube
[HAP-python](https://github.com/ikalchev/HAP-python) Accessories for [e-Q3](https://www.eq-3.com) MAX! devices, e.g. Cube and Thermostat.

You can easily discover and add MAX! devices to your Home app and set the temperature.

## Install
`pip install pyhap-maxcube`

## Usage

```python
from pyhap.accessory_driver import AccessoryDriver
from pyhap.accessories.maxcube import MaxBridge

# The MAX! Cube address
MAX_ADDR = '192.168.1.247'
MAX_PORT = 62910

# Run HAP-python on port 51826
driver = AccessoryDriver(port=51826)

# Expose the MaxBridge accessory - it will discover the MAX! devices and create
# accessories for it.
driver.add_accessory(
    accessory=MaxBridge(MAX_ADDR, MAX_PORT, driver, 'MaxBridge'))

# Start it!
driver.start()
```
