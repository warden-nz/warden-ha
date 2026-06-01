# Warden — AU/NZ Wholesale Electricity Price Monitor for Home Assistant

A HACS custom integration that connects Home Assistant to [Warden](https://wardenz.com), exposing real-time NZ wholesale electricity spot prices and contextual pricing intelligence so you can automate EV charging, battery export, and other energy decisions.

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

| Entity | Type | Description |
|---|---|---|
| `sensor.warden_{node}_price` | Sensor | Current spot price in NZD/MWh |
| `sensor.warden_{node}_alert_level` | Sensor | `normal`, `high`, or `spike` |
| `sensor.warden_{node}_30m_average` | Sensor | Rolling average price over the last 30 minutes in NZD/MWh |
| `sensor.warden_{node}_30d_window_average` | Sensor | Average price for this 30-minute window over the last 30 days in NZD/MWh |
| `sensor.warden_{node}_price_percentile` | Sensor | Where the current price sits in the 30-day distribution for this time window (%) |
| `binary_sensor.warden_{node}_spike_active` | Binary Sensor | `ON` during a price spike |

### Understanding the percentile sensor

The price percentile is the most powerful signal for automations. It tells you where the current price sits relative to the same time window over the last 30 days:

| Percentile | Interpretation | Suggested action |
|---|---|---|
| 0–10% | Very cheap | Charge batteries, run high-draw appliances |
| 11–30% | Cheap | Good time to charge |
| 31–70% | Normal | No action needed |
| 71–90% | Expensive | Defer non-essential loads |
| 91–100% | Spike | Export battery, pause EV charging |

Using percentile-based triggers means your automations automatically adapt to seasonal price changes and time-of-day patterns — no manual threshold tuning required.

The `interpretation` attribute on the percentile sensor (`very cheap`, `cheap`, `normal`, `expensive`, `spike`) can be used directly in template conditions.

### Understanding the 30d window average

The 30-day window average compares the current price against the historical average for the same 30-minute slot (e.g. Sunday 3:00–3:30pm) over the last 30 days. This accounts for time-of-day and day-of-week patterns in the wholesale market.

Additional attributes on this sensor:
- `window_p10_30d` — 10th percentile price for this window (historically cheap threshold)
- `window_p90_30d` — 90th percentile price for this window (historically expensive threshold)
- `window_samples` — number of historical data points used (increases over time up to ~30)

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

## Session expiry

If your Warden session expires, HA will show a notification on the integration card prompting you to log in again. Your automations will resume automatically once you do.

## Changing your node

Log in to [wardenz.com](https://wardenz.com) and update your profile. The change will be reflected in HA after the integration is reloaded (Settings → Integrations → Warden → Reload).

## Data freshness

All sensors update every 5 minutes, aligned with the NZ wholesale electricity dispatch cycle. The 30-day window stats become more accurate as history accumulates — expect full statistical confidence after 30 days of operation.
