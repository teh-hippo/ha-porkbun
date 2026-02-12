# CHANGELOG


## v0.1.0 (2026-02-12)

### Bug Fixes

- Correct semantic-release build_command config
  ([`7f9447d`](https://github.com/teh-hippo/ha-porkbun/commit/7f9447dcd8efce85aa22835df327cf6b7ed51ed3))

- Remove URLs from strings, use mock session in API tests
  ([`bf33b03`](https://github.com/teh-hippo/ha-porkbun/commit/bf33b0346feed1c9c73a04bf5ebbc0f3fbed5434))

- Resolve hassfest URL validation and test thread cleanup
  ([`c035fd9`](https://github.com/teh-hippo/ha-porkbun/commit/c035fd9a6afd88005638053e1f8fc8d561172524))

- Target master branch in release workflow and semantic-release config
  ([`8f9f029`](https://github.com/teh-hippo/ha-porkbun/commit/8f9f029699f888f50a397de6c43778c9c8d715f4))

- Target master branch in validate workflow
  ([`913b83c`](https://github.com/teh-hippo/ha-porkbun/commit/913b83c6ac223c8e8c9191f082de80bb6fb44db5))

- Use HA shared session in config flow to prevent thread leak
  ([`75ac1e5`](https://github.com/teh-hippo/ha-porkbun/commit/75ac1e5ebc3b8e62fd583e4472d0a7e44f50392d))

- Use Python 3.13 in CI to fix aiohttp thread cleanup
  ([`435aee6`](https://github.com/teh-hippo/ha-porkbun/commit/435aee663f521a266b9f3e1312a143981151fbbb))

### Chores

- Add integration constants and manifest
  ([`346759a`](https://github.com/teh-hippo/ha-porkbun/commit/346759abf8834dc7fa17090f106aaee155e00592))

- const.py: DOMAIN, API config, default intervals - manifest.json: HA integration metadata (service,
  cloud_polling) - hacs.json: HACS metadata with HA version requirement

- Scaffold project structure
  ([`23e517d`](https://github.com/teh-hippo/ha-porkbun/commit/23e517de3eb6e4f25072c6e1cc40946b93dd95ae))

- .gitignore, .ruff.toml, LICENSE (MIT), pyproject.toml - requirements_test.txt with
  pytest-homeassistant-custom-component - semantic-release config in pyproject.toml - Placeholder
  README.md

### Continuous Integration

- Add Dependabot configuration
  ([`4f4281e`](https://github.com/teh-hippo/ha-porkbun/commit/4f4281e6939fb130637de43628d739364966c749))

- GitHub Actions ecosystem: weekly grouped updates - pip ecosystem: weekly updates for test
  dependencies

- Add validate and release workflows
  ([`38dd8aa`](https://github.com/teh-hippo/ha-porkbun/commit/38dd8aa57d6a1ce07012b31df0525c60c039e0a0))

- validate.yml: hassfest, HACS validation, ruff lint, pytest (on push/PR/daily) - release.yml:
  python-semantic-release on push to main - Automatic version bumps, changelogs, and GitHub Releases

### Documentation

- Add README with badges and install guide
  ([`a51bec6`](https://github.com/teh-hippo/ha-porkbun/commit/a51bec6576b8157c43121ba888a124e0fde1f6f1))

- Badges: HACS, release, license, CI status - Installation: HACS custom repo + manual -
  Configuration guide: two-step flow, options, multiple domains - Sensor descriptions -
  Troubleshooting table - Development setup (uv, pytest, ruff, conventional commits) - Porkbun
  trademark disclaimer

### Features

- Add config flow with two-step setup
  ([`84298ba`](https://github.com/teh-hippo/ha-porkbun/commit/84298ba601e2c9a1b9c2db2e2041ad17ccdee99c))

- Step 1: API key + secret validation via /ping - Step 2: Domain + subdomains + IPv4/IPv6 toggles -
  Reauth flow for credential rotation - Options flow for interval, subdomains, IP version toggles -
  Unique ID by domain to prevent duplicates

- Add DDNS update coordinator
  ([`0117f56`](https://github.com/teh-hippo/ha-porkbun/commit/0117f563da566fd112d26ca8c21e3ce967df5181))

- DataUpdateCoordinator with configurable interval - Per-record state tracking (current IP, last
  updated, last changed) - Creates records if missing, edits if IP changed, skips if current - IPv4
  via Porkbun /ping, IPv6 via api6.ipify.org - ConfigEntryAuthFailed on auth errors, UpdateFailed on
  transient

- Add integration setup and sensor entities
  ([`fbd4c40`](https://github.com/teh-hippo/ha-porkbun/commit/fbd4c407b24065775ba94edc5e3fd82a9a9b9716))

- __init__.py: setup/unload entry, options update listener - sensor.py: per-subdomain sensors for
  IP, last updated, last changed, next update - CoordinatorEntity-based with proper device grouping
  - Repair issue cleanup on successful setup

- Add Porkbun API client
  ([`2884ccd`](https://github.com/teh-hippo/ha-porkbun/commit/2884ccd6dc0ac6d08688d2148c18c1d34467ca29))

- Async aiohttp client for Porkbun API v3 - ping, get_records, create_record,
  edit_record_by_name_type - PorkbunAuthError / PorkbunApiError / PorkbunDomainError - DnsRecord
  dataclass for typed record access - Debug logging for all API requests

- Add repair issues for API errors
  ([`10fafa2`](https://github.com/teh-hippo/ha-porkbun/commit/10fafa2554201e34217b787e89eb0f1f8ee2ee51))

- Raises HA repair issue when Porkbun API returns domain-level errors - Issue links user to Porkbun
  dashboard to enable API access - Clears repair issue on successful setup (in __init__.py)

- Add UI strings and translations
  ([`26690a2`](https://github.com/teh-hippo/ha-porkbun/commit/26690a25a57cf7a3234f036991319df69c915613))

- Config flow: two-step (credentials + domain) with error messages - Reauth flow strings - Options
  flow strings - Repair issue strings (API access disabled) - English translations

### Testing

- Add unit and integration tests
  ([`1c4bead`](https://github.com/teh-hippo/ha-porkbun/commit/1c4beadb63fba106893586d3f4ac493d38d7e3be))

- 25 tests across 5 test files - test_api: 11 tests (ping, records, create, edit, errors) -
  test_config_flow: 4 tests (full flow, auth error, connection error, duplicate) - test_coordinator:
  6 tests (create, skip, update, auth, api error, subdomains) - test_init: 2 tests (setup, unload) -
  test_sensor: 2 tests (creation, IP value) - Uses pytest-homeassistant-custom-component fixtures -
  Refactored coordinator to use HA's async_get_clientsession - All ruff lint + format clean
