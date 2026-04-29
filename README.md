# cyberpower-exporter

A Prometheus exporter for CyberPower UPS systems. Reads UPS status from the `pwrstatd` daemon via Unix socket and exposes metrics on port 9200.

## Attribution

Originally written by **Mike Shoup** as [`shouptech/cyberpower_exporter`](https://github.com/shouptech/cyberpower_exporter); specifically derived from [`src/cyberpower_exporter/command.py`](https://github.com/shouptech/cyberpower_exporter/blob/master/src/cyberpower_exporter/command.py). Used and modified here under the Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Usage

```bash
docker run -d \
    -v /var/pwrstatd.ipc:/var/pwrstatd.ipc \
    -p 9200:9200 \
    ghcr.io/simplicityguy/cyberpower-exporter:latest
```

The host must be running `pwrstatd` (CyberPower PowerPanel). The daemon's Unix socket at `/var/pwrstatd.ipc` must be mounted into the container.

## Exported Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `ups_cyberpower_info` | Info | Model name and firmware number |
| `ups_utility_volt` | Gauge | Utility input voltage |
| `ups_output_volt` | Gauge | UPS output voltage |
| `ups_load` | Gauge | Load percentage (0-1) |
| `ups_battery_capacity` | Gauge | Battery capacity percentage |
| `ups_battery_remaining_time` | Gauge | Battery time remaining (seconds) |
| `ups_battery_charging` | Gauge | Battery charging (0/1) |
| `ups_battery_discharging` | Gauge | Battery discharging (0/1) |
| `ups_ac_present` | Gauge | AC power present (0/1) |
| `ups_diagnostic_result` | Gauge | Last diagnostic result |
| `ups_input_rating_volt` | Gauge | Input voltage rating |
| `ups_output_rating_watt` | Gauge | Output wattage rating |

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `POLL_INTERVAL` | `5` | Seconds between UPS status polls |

The container runs as a non-root `exporter` user in the `root` group for socket access.

## Development

Install [pre-commit](https://pre-commit.com/) hooks before contributing:

```bash
pre-commit install
pre-commit run --all-files
```

The hook suite includes [hadolint](https://github.com/hadolint/hadolint) for the Dockerfile, [shellcheck](https://www.shellcheck.net/) and [shfmt](https://github.com/mvdan/sh) for shell scripts, and [actionlint](https://github.com/rhysd/actionlint)/[yamllint](https://yamllint.readthedocs.io/) for the GitHub Actions workflows.

## License

Licensed under the [Apache License, Version 2.0](LICENSE). See [NOTICE](NOTICE) for upstream attribution.
