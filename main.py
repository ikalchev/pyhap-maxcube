"""Demo script for starting."""
import logging
import signal

from pyhap.accessory_driver import AccessoryDriver
from py_maxcube import MaxBridge

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

driver = AccessoryDriver(port=51826)

# Change `get_accessory` to `get_bridge` if you want to run a Bridge.
driver.add_accessory(accessory=MaxBridge('192.168.1.247', 62910, driver, 'MaxBridge'))

# We want SIGTERM (terminate) to be handled by the driver itself,
# so that it can gracefully stop the accessory, server and advertising.
signal.signal(signal.SIGTERM, driver.signal_handler)

# Start it!
driver.start()
