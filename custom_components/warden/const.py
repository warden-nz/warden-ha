"""Constants for the Warden NZ & AU Electricity integration."""

DOMAIN = "warden"

# The base URL is fixed — users don't need to enter it
API_BASE_URL = "https://api.wardenz.com"

# How often HA polls for new prices (5 minutes = WITS dispatch cadence)
DEFAULT_SCAN_INTERVAL = 300

# How often HA polls for forecast data (30 minutes)
FORECAST_SCAN_INTERVAL = 1800

# Keys used to store config and runtime data
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TOKEN = "access_token"
CONF_NODE = "node"
CONF_COUNTRY = "country"
CONF_REGION = "region"   # AU NEM region e.g. NSW1, VIC1

# Warden API endpoints
ENDPOINT_LOGIN    = "/auth/login"
ENDPOINT_ME       = "/auth/me"
ENDPOINT_LATEST   = "/prices/latest"
ENDPOINT_STATUS   = "/status"
ENDPOINT_FORECAST = "/prices/forecast"
ENDPOINT_CHEAPEST = "/prices/cheapest"

# Cheapest window sizes in hours
CHEAPEST_WINDOW_HOURS = [1, 2, 3]