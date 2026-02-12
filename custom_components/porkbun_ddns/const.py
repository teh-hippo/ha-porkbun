"""Constants for Porkbun DDNS."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "porkbun_ddns"
__version__ = "0.11.0"

DEFAULT_UPDATE_INTERVAL = 300  # 5 minutes
DEFAULT_TTL = 600  # Porkbun minimum

CONF_API_KEY = "api_key"
CONF_SECRET_KEY = "secret_key"
CONF_DOMAIN = "domain"
CONF_SUBDOMAINS = "subdomains"
CONF_IPV4 = "ipv4"
CONF_IPV6 = "ipv6"
CONF_UPDATE_INTERVAL = "update_interval"

PORKBUN_API_BASE = "https://api-ipv4.porkbun.com/api/json/v3"
IPV6_DETECT_URL = "https://api6.ipify.org"
