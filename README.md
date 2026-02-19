# 🐷 Porkbun DDNS for Home Assistant

[![HACS][hacs-badge]][hacs-url]
[![GitHub Release][release-badge]][release-url]
[![Validate][validate-badge]][validate-url]
[![Home Assistant][ha-badge]][ha-url]

Home Assistant custom integration for [Porkbun](https://porkbun.com) Dynamic DNS.
It keeps A/AAAA DNS records synced with your public IP.

## Features

- Updates records only when IP changes
- IPv4 support, optional IPv6
- Multiple domains (one config entry per domain)
- Health/diagnostic/timestamp entities
- Home Assistant Repairs issue on API-access failures

## Prerequisites

1. Domain managed at Porkbun
2. Domain API access enabled
3. Porkbun API key + secret from [porkbun.com/account/api](https://porkbun.com/account/api)

## Installation

### HACS (recommended)

1. HACS → **Custom repositories**
2. Add `https://github.com/teh-hippo/ha-porkbun` as **Integration**
3. Install **Porkbun DDNS**
4. Restart Home Assistant

### Manual

1. Copy `custom_components/porkbun_ddns` to `<config>/custom_components/`
2. Restart Home Assistant

## Configuration

Home Assistant → **Settings** → **Devices & Services** → **Add Integration** → **Porkbun DDNS**.

Options:
- Update interval (default `300s`, minimum `60s`)
- Subdomains (comma-separated, e.g. `www, vpn`)
- IPv4 / IPv6 toggles

## Entities

Enabled by default:
- `binary_sensor.*_dns_status`
- `sensor.*_managed_subdomains`
- `sensor.*_last_updated`
- `sensor.*_next_update`
- `button.*_refresh_ddns_records`

Disabled by default:
- `sensor.*_public_ipv4`
- `sensor.*_public_ipv6`
- `sensor.*_domain_expiry`
- `binary_sensor.*_whois_privacy`

## Troubleshooting

- Invalid key/secret: regenerate at [porkbun.com/account/api](https://porkbun.com/account/api)
- Domain not accessible: enable API access in Porkbun domain settings
- Repair issue (`api_access_disabled`): re-enable API access, then press **Refresh DDNS Records**
- IPv6 not updating: verify IPv6 connectivity and external reachability

## Development

```bash
bash scripts/check.sh
```

Requires [uv](https://docs.astral.sh/uv/). Uses [Conventional Commits](https://www.conventionalcommits.org/).

## License

[MIT](LICENSE)

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://github.com/hacs/integration
[release-badge]: https://img.shields.io/github/v/release/teh-hippo/ha-porkbun
[release-url]: https://github.com/teh-hippo/ha-porkbun/releases
[validate-badge]: https://img.shields.io/github/actions/workflow/status/teh-hippo/ha-porkbun/validate.yml?branch=master&label=validate
[validate-url]: https://github.com/teh-hippo/ha-porkbun/actions/workflows/validate.yml
[ha-badge]: https://img.shields.io/badge/HA-2026.2%2B-blue.svg
[ha-url]: https://www.home-assistant.io
