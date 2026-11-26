# Changelog
All notable changes to the Warden Home Assistant integration are documented here.
This format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.11] - 2026-11-27
### Fixed
- Accounts without Home Assistant access (402 from `/ha/*`) no longer get stuck in a re-authentication loop. Setup now checks the plan and shows a clear "requires a Smart or Device plan" error, and an existing entry that loses access stops loading with that message instead of asking you to log in again.
- AU accounts: the spike binary sensor was named "Warden unknown Spike Active". It now uses the NEM region (e.g. "Warden NSW1 Spike Active"), matching the other sensors.
- Added `translations/en.json` so setup form text and error messages display properly.
### Docs
- README now states that a Smart or Device plan (or an active trial) is required, and what happens when a trial ends.
- Corrected units ($/kWh, not NZD/MWh), cheapest-window entity IDs and attributes, and added the Carbon Intensity and Renewable % sensors to the entities table.
- Dashboard card example is now in a fenced YAML block.

## [1.0.8] - 2026-06-25
### Fixed
- Carbon Intensity and Renewable % sensors were added in code but never wired through `coordinator.py`, so they always showed `unknown`. The coordinator now forwards `carbon_intensity_gkwh` and `renewable_pct` from `/status` to the sensors.
### Changed
- Renamed Carbon Intensity and Renewable % sensors to drop the per-node prefix (e.g. "Warden Carbon Intensity" instead of "Warden ALB0331 Carbon Intensity"), since these values are NZ-wide, not node-specific.

## [1.0.7] - 2026-06-25
### Changed
- Versioning/changelog housekeeping only. Note: the Carbon Intensity and Renewable % sensors introduced in this release's changelog text were not actually functional until 1.0.8 — see above.