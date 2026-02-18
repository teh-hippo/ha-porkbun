# 🐷 Porkbun DDNS for Home Assistant

[![HACS][hacs-badge]][hacs-url]
[![GitHub Release][release-badge]][release-url]
[![License][license-badge]][license-url]
[![Validate][validate-badge]][validate-url]

Home Assistant custom integration for [Porkbun](https://porkbun.com) Dynamic DNS.
It keeps A/AAAA records in sync with your current public IP.

## What it does

- Updates DNS records only when IPs change
- Supports IPv4 and optional IPv6
- Supports multiple domains (one config entry per domain)
- Includes health, timestamp, and diagnostics entities
- Surfaces API-access problems in Home Assistant Repairs

## Prerequisites

1. Domain managed at Porkbun
2. API access enabled for that domain (`Domain Management` → domain → API Access)
3. Porkbun API key + secret from [porkbun.com/account/api](https://porkbun.com/account/api)

## Installation

### HACS (recommended)

1. HACS → **Custom repositories**
2. Add `https://github.com/teh-hippo/ha-porkbun` as **Integration**
3. Install **Porkbun DDNS**
4. Restart Home Assistant

### Manual

1. Copy `custom_components/porkbun_ddns` into `<config>/custom_components/`
2. Restart Home Assistant

## Setup

1. Home Assistant → **Settings** → **Devices & Services** → **Add Integration**
2. Select **Porkbun DDNS**
3. Enter API key + secret key
4. Enter domain, optional subdomains, and IPv4/IPv6 options

### Options

| Option | Default | Notes |
|---|---|---|
| Update interval | 300s | Minimum 60s |
| Subdomains | empty | Comma-separated (`www, vpn`) |
| IPv4 (A) | Enabled | Recommended |
| IPv6 (AAAA) | Disabled | Enable if your network has IPv6 |

## Entities

| Platform | Entity | Default | Description |
|---|---|---|---|
| `binary_sensor` | DNS Status | Enabled | On when any managed record update fails |
| `sensor` | Managed Subdomains | Enabled | Root + configured subdomains |
| `sensor` | Last Updated | Enabled | Timestamp of most recent coordinator run |
| `sensor` | Next Update | Enabled | Timestamp of next scheduled poll |
| `sensor` | Public IPv4 | Disabled | Current public IPv4 |
| `sensor` | Public IPv6 | Disabled | Current public IPv6 |
| `sensor` | Domain Expiry | Disabled | Domain expiry timestamp |
| `binary_sensor` | WHOIS Privacy | Disabled | WHOIS privacy status |
| `button` | Refresh DDNS Records | Enabled | Forces immediate refresh |

## Troubleshooting

| Problem | Resolution |
|---|---|
| Invalid API key/secret | Regenerate keys at [porkbun.com/account/api](https://porkbun.com/account/api) and re-enter |
| Domain not accessible | Enable domain API access in Porkbun dashboard |
| Repair issue: API access disabled | Same as above; then press **Refresh DDNS Records** |
| IPv6 not updating | Verify IPv6 connectivity and external reachability |

## Behavior notes

- Polling integration (no webhook mode)
- Porkbun minimum TTL is 600 seconds
- IPv6 detection uses `api6.ipify.org`
- Removing the integration does not delete DNS records

## Development

### Setup

```bash
git clone https://github.com/teh-hippo/ha-porkbun.git
cd ha-porkbun
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements_test.txt
```

### CI parity (run before push)

```bash
ruff check .
ruff format --check .
mypy custom_components/porkbun_ddns
pytest tests/ -v
```

### Pre-commit (recommended)

```bash
pip install pre-commit
pre-commit install
```

### Commit conventions

Uses [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` → minor bump
- `fix:` → patch bump
- `feat!:` / `BREAKING CHANGE:` → major bump

## Releases

- HACS consumes release ZIP assets (`porkbun_ddns.zip`)
- `hacs.json` is configured with `zip_release: true`
- Tags are the source of truth for released versions

## Disclaimer

This project is not affiliated with Porkbun LLC.

## License

[MIT](LICENSE)

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://github.com/hacs/integration
[release-badge]: https://img.shields.io/github/v/release/teh-hippo/ha-porkbun
[release-url]: https://github.com/teh-hippo/ha-porkbun/releases
[license-badge]: https://img.shields.io/github/license/teh-hippo/ha-porkbun
[license-url]: https://github.com/teh-hippo/ha-porkbun/blob/master/LICENSE
[validate-badge]: https://img.shields.io/github/actions/workflow/status/teh-hippo/ha-porkbun/validate.yml?branch=master&label=validate
[validate-url]: https://github.com/teh-hippo/ha-porkbun/actions/workflows/validate.yml
