# Warden — AU/NZ Wholesale Electricity Price Monitor for Home Assistant

A HACS custom integration that connects Home Assistant to [Warden](https://wardenz.com), exposing real-time NZ wholesale electricity spot prices, contextual pricing intelligence, and 24-hour price forecasts so you can automate EV charging, battery export, appliance scheduling, and other energy decisions.

## Prerequisites

- A [wardenz.com](https://wardenz.com) account (free or paid)
- HACS installed in Home Assistant

Your reference node is set on your wardenz.com account profile — you don't need to configure it in HA. Free accounts get access to the main grid nodes (OTA2201, HAY2201, BEN2201). Paid accounts get an ICP-matched node for your local pricing point.

## Installation

### Via HACS (recommended)

1. In HACS → **Integrations** → three-dot menu → **Custom repositories**
2. Add `https://github.com/warden-nz/warden-ha` as type **Integration**
3. Search for "Warden" and install
4. Restart Home Assistant

### Manual

Copy the `custom_components/warden/` folder into your HA config's `custom_components/` directory, then restart.

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Warden**
3. Enter your wardenz.com username and password
4. HA will fetch your account details and confirm before saving

## Entities

| Entity | Type | Updates | Description |
|---|---|---|---|
| `sensor.warden_{node}_price` | Sensor | 5 min | Current spot price in NZD/MWh |
| `sensor.warden_{node}_alert_level` | Sensor | 5 min | `normal`, `high`, or `spike` |
| `sensor.warden_{node}_30m_average` | Sensor | 5 min | Rolling average price over the last 30 minutes in NZD/MWh |
| `sensor.warden_{node}_window_average` | Sensor | 5 min | Average price for this 30-minute window over the last 30 days in NZD/MWh |
| `sensor.warden_{node}_price_percentile` | Sensor | 5 min | Where the current price sits in the historical distribution for this time window (%) |
| `binary_sensor.warden_{node}_spike_active` | Binary Sensor | 5 min | `ON` during a price spike |
| `sensor.warden_{node}_forecast` | Sensor | 30 min | Next period's forecast price in NZD/MWh, with full 24hr forecast as attributes |
| `sensor.warden_cheapest_1h_window` | Sensor | 30 min | Average price of the cheapest upcoming 1-hour window in NZD/MWh |
| `sensor.warden_cheapest_2h_window` | Sensor | 30 min | Average price of the cheapest upcoming 2-hour window in NZD/MWh |
| `sensor.warden_cheapest_3h_window` | Sensor | 30 min | Average price of the cheapest upcoming 3-hour window in NZD/MWh |

> **Note:** Forecast and cheapest window sensors are currently NZ-only. AU forecast support is planned for a future release.

### Understanding the percentile sensor

The price percentile is the most powerful signal for automations. It tells you where the current price sits relative to the same time window historically:

| Percentile | Interpretation | Suggested action |
|---|---|---|
| 0–10% | Very cheap | Charge batteries, run high-draw appliances |
| 11–30% | Cheap | Good time to charge |
| 31–70% | Normal | No action needed |
| 71–90% | Expensive | Defer non-essential loads |
| 91–100% | Spike | Export battery, pause EV charging |

Using percentile-based triggers means your automations automatically adapt to seasonal price changes and time-of-day patterns — no manual threshold tuning required.

The `interpretation` attribute on the percentile sensor (`very cheap`, `cheap`, `normal`, `expensive`, `spike`) can be used directly in template conditions.

### Understanding the window average

The window average compares the current price against the historical average for the same 30-minute slot (e.g. Sunday 3:00–3:30pm) over available history. This accounts for time-of-day and day-of-week patterns in the wholesale market.

Additional attributes on this sensor:
- `window_p10` — 10th percentile price for this window (historically cheap threshold)
- `window_p90` — 90th percentile price for this window (historically expensive threshold)
- `window_samples` — number of historical data points used (increases over time)

### Understanding the forecast sensor

The forecast sensor exposes the WITS PRSL (Pre-Solving) price forecast for your node, covering the remainder of the current trading day plus the next (typically 20–42 periods depending on time of day). The sensor state is the next period's forecast price.

The full forecast array is available as the `prices` attribute — a list of objects each containing `trading_datetime`, `price`, and `horizon_minutes`. This can be used in HA templates:

```yaml
# Price in approximately 2 hours (index 4 = 4 x 30-min periods)
{{ state_attr('sensor.warden_alb0331_forecast', 'prices')[4]['price'] }}
```

If your exact node isn't available in the forecast data, the integration automatically falls back to your zone's reference node (e.g. OTA2201 for Upper North Island).

### Understanding the cheapest window sensors

The cheapest window sensors identify the best upcoming time to run high-draw appliances or charge batteries. Each sensor finds the contiguous block of 30-minute periods with the lowest average price across the forecast horizon.

Each sensor exposes:
- **State** — average NZD/MWh across the cheapest window
- `start_time` — ISO8601 timestamp when the cheap window begins
- `end_time` — ISO8601 timestamp when the cheap window ends
- `node` — the node used for the forecast (may be zone reference node)

## Example automations

### Charge battery when price is very cheap

```yaml
automation:
  - alias: "Charge battery when price is very cheap"
    trigger:
      - platform: state
        entity_id: sensor.warden_ota2201_price_percentile
    condition:
      - condition: numeric_state
        entity_id: sensor.warden_ota2201_price_percentile
        below: 20
    action:
      - service: select.select_option
        target:
          entity_id: select.battery_mode
        data:
          option: "charge"
```

### Export battery during a spike

```yaml
automation:
  - alias: "Export battery on price spike"
    trigger:
      - platform: state
        entity_id: binary_sensor.warden_ota2201_spike_active
        to: "on"
    action:
      - service: select.select_option
        target:
          entity_id: select.battery_mode
        data:
          option: "export"
```

### Pause EV charging when expensive

```yaml
automation:
  - alias: "Pause EV charging when price is expensive"
    trigger:
      - platform: state
        entity_id: sensor.warden_ota2201_price_percentile
    condition:
      - condition: numeric_state
        entity_id: sensor.warden_ota2201_price_percentile
        above: 80
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.ev_charger
```

### Resume EV charging when price returns to normal

```yaml
automation:
  - alias: "Resume EV charging when price is normal"
    trigger:
      - platform: state
        entity_id: sensor.warden_ota2201_price_percentile
    condition:
      - condition: numeric_state
        entity_id: sensor.warden_ota2201_price_percentile
        below: 40
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.ev_charger
```

### Start dishwasher at cheapest upcoming 1-hour window

```yaml
automation:
  - alias: "Start dishwasher at cheapest 1h window"
    trigger:
      - platform: template
        value_template: >
          {{ now().isoformat() >= state_attr('sensor.warden_cheapest_1h_window', 'start_time') }}
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.warden_cheapest_1h_window', 'avg_price') | float < 80 }}
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.dishwasher
```

### Charge EV during cheapest 3-hour window overnight

```yaml
automation:
  - alias: "Charge EV during cheapest 3h window"
    trigger:
      - platform: template
        value_template: >
          {{ now().isoformat() >= state_attr('sensor.warden_cheapest_3h_window', 'start_time') }}
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.ev_charger
  - alias: "Stop EV charging after cheapest 3h window"
    trigger:
      - platform: template
        value_template: >
          {{ now().isoformat() >= state_attr('sensor.warden_cheapest_3h_window', 'end_time') }}
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.ev_charger
```

## Example dashboard card

Here is an example card which shows the forcast price and cheapest windows
# Warden Price Forecast — Lovelace example
#
# Requires (install via HACS first):
#   - apexcharts-card        https://github.com/RomRider/apexcharts-card
#   - config-template-card   https://github.com/iantrich/config-template-card
#
# Before pasting this in, replace YOUR_NODE everywhere below with your
# own node code, e.g. alb0331 (check Settings -> Devices & Services ->
# Warden -> your sensors to confirm the exact entity ids).

type: vertical-stack
cards:
  - type: markdown
    content: >
      ## Warden Price Forecast

      **Cheapest 1h window:** {{ state_attr('sensor.warden_YOUR_NODE_cheapest_1h_window', 'start_time')
      | as_timestamp | timestamp_custom('%I:%M %p', true) }} – {{
      state_attr('sensor.warden_YOUR_NODE_cheapest_1h_window', 'end_time')
      | as_timestamp | timestamp_custom('%I:%M %p', true) }} @ **{{
      states('sensor.warden_YOUR_NODE_cheapest_1h_window') | float
      | round(4) }} $/kWh**
  - type: custom:config-template-card
    entities:
      - sensor.warden_YOUR_NODE_cheapest_1h_window
      - sensor.warden_YOUR_NODE_forecast
    card:
      type: custom:apexcharts-card
      header:
        show: false
      now:
        show: true
        label: Now
      graph_span: 25h
      span:
        start: hour
      apex_config:
        chart:
          type: bar
          height: 150
        annotations:
          xaxis:
            - x: >-
                ${ new
                Date(states['sensor.warden_YOUR_NODE_cheapest_1h_window'].attributes.start_time).getTime()
                }
              x2: >-
                ${ new
                Date(states['sensor.warden_YOUR_NODE_cheapest_1h_window'].attributes.end_time).getTime() }
              fillColor: "#00b894"
              opacity: 0.25
              label:
                text: Cheapest 1h
                style:
                  color: "#ffffff"
                  background: "#00b894"
                  fontSize: 12px
        xaxis:
          type: datetime
          labels:
            datetimeUTC: false
        tooltip:
          x:
            format: ddd dd MMM HH:mm
      series:
        - entity: sensor.warden_YOUR_NODE_forecast
          name: Forecast Price ($/kWh)
          color: "#0984e3"
          type: column
          float_precision: 2
          data_generator: |
            return entity.attributes.prices.map(p => ({
              x: new Date(p.trading_datetime).getTime(),
              y: p.price
            }));
  - type: markdown
    content: >
      **Cheapest 2h window:** {{ state_attr('sensor.warden_YOUR_NODE_cheapest_2h_window', 'start_time')
      | as_timestamp | timestamp_custom('%I:%M %p', true) }} – {{
      state_attr('sensor.warden_YOUR_NODE_cheapest_2h_window', 'end_time')
      | as_timestamp | timestamp_custom('%I:%M %p', true) }} @ **{{
      states('sensor.warden_YOUR_NODE_cheapest_2h_window') | float
      | round(4) }} $/kWh**
  - type: custom:config-template-card
    entities:
      - sensor.warden_YOUR_NODE_cheapest_2h_window
      - sensor.warden_YOUR_NODE_forecast
    card:
      type: custom:apexcharts-card
      header:
        show: false
      now:
        show: true
        label: Now
      graph_span: 25h
      span:
        start: hour
      apex_config:
        chart:
          type: bar
          height: 150
        annotations:
          xaxis:
            - x: >-
                ${ new
                Date(states['sensor.warden_YOUR_NODE_cheapest_2h_window'].attributes.start_time).getTime()
                }
              x2: >-
                ${ new
                Date(states['sensor.warden_YOUR_NODE_cheapest_2h_window'].attributes.end_time).getTime() }
              fillColor: "#0984e3"
              opacity: 0.25
              label:
                text: Cheapest 2h
                style:
                  color: "#ffffff"
                  background: "#0984e3"
                  fontSize: 12px
        xaxis:
          type: datetime
          labels:
            datetimeUTC: false
        tooltip:
          x:
            format: ddd dd MMM HH:mm
      series:
        - entity: sensor.warden_YOUR_NODE_forecast
          name: Forecast Price ($/kWh)
          color: "#0984e3"
          type: column
          float_precision: 2
          data_generator: |
            return entity.attributes.prices.map(p => ({
              x: new Date(p.trading_datetime).getTime(),
              y: p.price
            }));
  - type: markdown
    content: >
      **Cheapest 3h window:** {{ state_attr('sensor.warden_YOUR_NODE_cheapest_3h_window', 'start_time')
      | as_timestamp | timestamp_custom('%I:%M %p', true) }} – {{
      state_attr('sensor.warden_YOUR_NODE_cheapest_3h_window', 'end_time')
      | as_timestamp | timestamp_custom('%I:%M %p', true) }} @ **{{
      states('sensor.warden_YOUR_NODE_cheapest_3h_window') | float
      | round(4) }} $/kWh**
  - type: custom:config-template-card
    entities:
      - sensor.warden_YOUR_NODE_cheapest_3h_window
      - sensor.warden_YOUR_NODE_forecast
    card:
      type: custom:apexcharts-card
      header:
        show: false
      now:
        show: true
        label: Now
      graph_span: 25h
      span:
        start: hour
      apex_config:
        chart:
          type: bar
          height: 150
        annotations:
          xaxis:
            - x: >-
                ${ new
                Date(states['sensor.warden_YOUR_NODE_cheapest_3h_window'].attributes.start_time).getTime()
                }
              x2: >-
                ${ new
                Date(states['sensor.warden_YOUR_NODE_cheapest_3h_window'].attributes.end_time).getTime() }
              fillColor: "#6c5ce7"
              opacity: 0.25
              label:
                text: Cheapest 3h
                style:
                  color: "#ffffff"
                  background: "#6c5ce7"
                  fontSize: 12px
        xaxis:
          type: datetime
          labels:
            datetimeUTC: false
        tooltip:
          x:
            format: ddd dd MMM HH:mm
      series:
        - entity: sensor.warden_YOUR_NODE_forecast
          name: Forecast Price ($/kWh)
          color: "#0984e3"
          type: column
          float_precision: 2
          data_generator: |
            return entity.attributes.prices.map(p => ({
              x: new Date(p.trading_datetime).getTime(),
              y: p.price
            }));
grid_options:
  columns: full


## Data freshness

Current price sensors update every 5 minutes, aligned with the NZ wholesale electricity dispatch cycle. Forecast and cheapest window sensors update every 30 minutes. The window stats become more accurate as history accumulates.

## Session expiry

If your Warden session expires, HA will show a notification on the integration card prompting you to log in again. Your automations will resume automatically once you do.

## Changing your node

Log in to [wardenz.com](https://wardenz.com) and update your profile. The change will be reflected in HA after the integration is reloaded (Settings → Integrations → Warden → Reload).