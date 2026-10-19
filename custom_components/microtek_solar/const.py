"""Constants for the Microtek Solar Inverter integration."""

DOMAIN = "microtek_solar"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "Microtek Solar Inverter"
DEFAULT_HOST = "192.168.1.100"
DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 30  # seconds

PLATFORMS = ["sensor", "binary_sensor"]
