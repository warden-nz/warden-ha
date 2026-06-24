# Changelog

All notable changes to the Warden Home Assistant integration are documented here.

This format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.5] - 2026-06-24

### Added
- Carbon Intensity sensor (`g/kWh`) — current NZ grid carbon intensity, sourced from em6 (Transpower/EMS).
- Renewable % sensor (`%`) — current percentage of NZ generation that is renewable, sourced from em6.

### Notes
- Both new sensors are **NZ-only**. em6's free carbon intensity feed is a single nationwide figure with no per-node or per-region breakdown, so the value is identical for every NZ user regardless of node or tier.
- AU accounts will show these sensors as `unknown` until an AU-side emissions data source is added.