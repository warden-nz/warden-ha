# Changelog
All notable changes to the Warden Home Assistant integration are documented here.
This format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.8] - 2026-06-25
### Fixed
- Carbon Intensity and Renewable % sensors were added in code but never wired through `coordinator.py`, so they always showed `unknown`. The coordinator now forwards `carbon_intensity_gkwh` and `renewable_pct` from `/status` to the sensors.
### Changed
- Renamed Carbon Intensity and Renewable % sensors to drop the per-node prefix (e.g. "Warden Carbon Intensity" instead of "Warden ALB0331 Carbon Intensity"), since these values are NZ-wide, not node-specific.

## [1.0.7] - 2026-06-25
### Changed
- Versioning/changelog housekeeping only. Note: the Carbon Intensity and Renewable % sensors introduced in this release's changelog text were not actually functional until 1.0.8 — see above.