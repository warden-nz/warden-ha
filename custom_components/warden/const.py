"""Constants for the Warden NZ Electricity integration."""

DOMAIN = "warden"

# The base URL is fixed — users don't need to enter it
API_BASE_URL = "https://api.wardenz.com"

# How often HA polls for new prices (5 minutes = EA dispatch cadence)
DEFAULT_SCAN_INTERVAL = 300

# Keys used to store config and runtime data
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TOKEN = "access_token"
CONF_NODE = "node"

# Warden API endpoints
ENDPOINT_LOGIN = "/auth/login"
ENDPOINT_ME = "/auth/me"
ENDPOINT_LATEST = "/prices/latest"
ENDPOINT_STATUS = "/status"
