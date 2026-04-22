"""Constants for Porkbun DDNS."""

from logging import getLogger

LOGGER = getLogger(__package__)

DOMAIN = "porkbun_ddns"

# hass.data[DOMAIN] key: set of entry_ids whose next coordinator init skips startup delay.
DATA_FORCE_IMMEDIATE_REFRESH = "force_immediate_refresh"

DEFAULT_UPDATE_INTERVAL = 300  # 5 minutes
DEFAULT_STARTUP_DELAY = 300  # 5 minutes
DEFAULT_TTL = 600  # Porkbun minimum

CONF_API_KEY = "api_key"
CONF_SECRET_KEY = "secret_key"
CONF_DOMAIN = "domain"
CONF_SUBDOMAINS = "subdomains"
CONF_IPV4 = "ipv4"
CONF_IPV6 = "ipv6"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_STARTUP_DELAY = "startup_delay"
CONF_FAILURE_THRESHOLD = "failure_threshold"

PORKBUN_API_BASE = "https://api-ipv4.porkbun.com/api/json/v3"
IPV6_DETECT_URL = "https://api6.ipify.org"
API_REQUEST_TIMEOUT = 15  # seconds per API call
API_REQUEST_MAX_ATTEMPTS = 3  # initial request + retries for transient errors
API_REQUEST_RETRY_BASE = 1.0  # exponential backoff base (seconds)
API_REQUEST_RETRY_JITTER_MAX = 0.25  # random jitter upper bound (seconds)
DEFAULT_FAILURE_THRESHOLD = 3  # escalate repeated failures from warning to error
