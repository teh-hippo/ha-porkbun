# 🐷 Porkbun DDNS for Home Assistant

[![HACS][hacs-badge]][hacs-url]
[![GitHub Release][release-badge]][release-url]
[![License][license-badge]][license-url]
[![Validate][validate-badge]][validate-url]

Dynamic DNS integration for [Home Assistant](https://www.home-assistant.io/) using the [Porkbun API](https://porkbun.com/api/json/v3/documentation).

Automatically keeps your [Porkbun](https://porkbun.com)-managed DNS records updated with your current public IP address. Supports IPv4, IPv6, multiple domains, and subdomains.

---

## Features

- 🔄 **Automatic DDNS updates** — checks your public IP and updates Porkbun DNS records when it changes
- 🌐 **IPv4 + IPv6** — A and AAAA record support (IPv6 opt-in)
- 🏠 **Multiple domains** — each domain is a separate config entry
- 📊 **Sensors** — current IP, last updated, next update, last IP change per subdomain
- 🔧 **Repair issues** — surfaces problems (e.g., API access not enabled) in HA's repair dashboard
- ⚙️ **Configurable** — update interval, subdomains, and IP version toggles via options flow
- 🎨 **UI-based setup** — two-step config flow, no YAML needed

## Prerequisites

1. A domain managed by [Porkbun](https://porkbun.com)
2. **API access enabled** for your domain — go to [Domain Management](https://porkbun.com/account/domains) → your domain → toggle "API Access"
3. An **API key** and **secret key** — create at [porkbun.com/account/api](https://porkbun.com/account/api)

> ⚠️ Make sure API access is enabled for each domain you want to use. Without it, the API keys will appear invalid even if they are correct.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots (⋮) → **Custom repositories**
3. Add `https://github.com/teh-hippo/ha-porkbun` as an **Integration**
4. Search for "Porkbun DDNS" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/porkbun_ddns` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Porkbun DDNS"
3. **Step 1 — Credentials:** Enter your Porkbun API key and secret key (validated immediately)
4. **Step 2 — Domain:** Enter your domain name, optional subdomains (comma-separated), and toggle IPv4/IPv6

### Options

After setup, click **Configure** on the integration entry to adjust:

| Option | Default | Description |
|---|---|---|
| Update interval | 300s (5 min) | How often to check for IP changes (minimum 60s) |
| Subdomains | _(empty)_ | Comma-separated list (e.g., `www, vpn, home`) |
| IPv4 (A record) | ✅ Enabled | Update A records with current IPv4 |
| IPv6 (AAAA record) | ❌ Disabled | Update AAAA records with current IPv6 |

### Multiple Domains

Add the integration multiple times — once per domain. Each domain is independent with its own credentials, subdomains, and update interval.

## Sensors

For each domain (and each subdomain), the integration creates:

| Sensor | Description |
|---|---|
| **IPv4 Address** | Current public IPv4 on file at Porkbun |
| **IPv6 Address** | Current public IPv6 (if IPv6 enabled) |
| **Last Updated** | When the integration last checked for changes |
| **Next Update** | When the next check is scheduled |
| **Last IP Change** | When the IP address actually changed |

## Troubleshooting

| Problem | Solution |
|---|---|
| "Invalid API key" during setup | Verify your keys at [porkbun.com/account/api](https://porkbun.com/account/api). Make sure you're using the correct API key (starts with `pk1_`) and secret key (starts with `sk1_`). |
| "Domain not accessible" | Enable API access for the domain in your [Porkbun dashboard](https://porkbun.com/account/domains). |
| Repair issue: "API access not enabled" | Same as above — toggle API access on for the domain. |
| IPv6 not updating | IPv6 detection uses `api6.ipify.org`. Ensure your network has IPv6 connectivity. |

## Development

### Setup

```bash
git clone https://github.com/teh-hippo/ha-porkbun.git
cd ha-porkbun
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements_test.txt
```

### Run tests

```bash
pytest tests/ -v
```

### Lint

```bash
ruff check . && ruff format --check .
```

### Commits

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automatic semantic versioning:

- `feat: ...` → minor version bump
- `fix: ...` → patch version bump
- `feat!: ...` or `BREAKING CHANGE:` → major version bump
- `chore:`, `docs:`, `ci:`, `test:` → no version bump

## Disclaimer

**This integration is not developed by or affiliated with Porkbun LLC.** All trademarks, logos, and brand names are the property of their respective owners. "Porkbun" is a trademark of Porkbun LLC.

This integration uses the [Porkbun API v3](https://porkbun.com/api/json/v3/documentation) for DNS record management.

## License

[MIT](LICENSE)

---

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://github.com/hacs/integration
[release-badge]: https://img.shields.io/github/v/release/teh-hippo/ha-porkbun
[release-url]: https://github.com/teh-hippo/ha-porkbun/releases
[license-badge]: https://img.shields.io/github/license/teh-hippo/ha-porkbun
[license-url]: https://github.com/teh-hippo/ha-porkbun/blob/master/LICENSE
[validate-badge]: https://img.shields.io/github/actions/workflow/status/teh-hippo/ha-porkbun/validate.yml?label=validate
[validate-url]: https://github.com/teh-hippo/ha-porkbun/actions/workflows/validate.yml
