# CHANGELOG


## v1.3.1 (2026-02-21)

### Bug Fixes

- **ci**: Detect Copilot review outcome via body text, not review state
  ([`fa31ba2`](https://github.com/teh-hippo/ha-porkbun/commit/fa31ba2fa03ce68242456e03a6a42b7d31f0de39))

### Continuous Integration

- Add copilot/dependabot push triggers, concurrency, devcontainer, and auto-merge flow
  ([`2b97cc5`](https://github.com/teh-hippo/ha-porkbun/commit/2b97cc51b70bf6e5f887d878ac10fdbccf789580))

- Remove unused semantic-release step id
  ([`260f057`](https://github.com/teh-hippo/ha-porkbun/commit/260f05700fdfaaf70c82e277fad482e21414777c))


## v1.3.0 (2026-02-19)

### Chores

- Track uv lockfile
  ([`b9ffb87`](https://github.com/teh-hippo/ha-porkbun/commit/b9ffb875bbe1ff772d8c27768276b2cfb4284ae1))

### Continuous Integration

- Minimal 4-line .gitignore
  ([`ec2ddad`](https://github.com/teh-hippo/ha-porkbun/commit/ec2ddad1d787444e0b5fb1643a4f655080e45c0a))

- Remove uv.lock from gitignore, clean up redundant mypy settings
  ([`a6472a3`](https://github.com/teh-hippo/ha-porkbun/commit/a6472a33bfa46a736057ef23fb983790286e5650))

### Documentation

- Standardize section naming
  ([`92ca768`](https://github.com/teh-hippo/ha-porkbun/commit/92ca76894973146e57c0ca8205e26b32fd299b7c))

- Standardize status badge set
  ([`1171189`](https://github.com/teh-hippo/ha-porkbun/commit/1171189a09cbd0d9939bbc832db9a1f2c232ee1d))

### Features

- Add quality scale declaration
  ([`74eeb32`](https://github.com/teh-hippo/ha-porkbun/commit/74eeb326231ed5adb327286aff7944ec9254f061))

### Refactoring

- Add coverage config section
  ([`c01f835`](https://github.com/teh-hippo/ha-porkbun/commit/c01f835cdc93356ec616c700cac97f47d00edb43))

- Remove empty manifest requirements
  ([`731cb23`](https://github.com/teh-hippo/ha-porkbun/commit/731cb235b539fa14e0f9a3075b4c20c48db29190))

- Remove zip release packaging
  ([`110ec5c`](https://github.com/teh-hippo/ha-porkbun/commit/110ec5cecbeee4e063800e914457d30a83fd8422))

- Simplify hacs metadata
  ([`d13e361`](https://github.com/teh-hippo/ha-porkbun/commit/d13e361198fd154726122224a9eeedb0ac8afe72))

- Use SPDX license string
  ([`3a7eaa2`](https://github.com/teh-hippo/ha-porkbun/commit/3a7eaa281d9964d234c2dcabbd96b43a42799650))


## v1.2.8 (2026-02-18)

### Bug Fixes

- Standardise CI tooling to uv, ruff, mypy strict
  ([`678a5b0`](https://github.com/teh-hippo/ha-porkbun/commit/678a5b05945c8695c9eb60ce0e39818c43322929))

### Continuous Integration

- Pin Python 3.13 via .python-version for uv
  ([`f096dbd`](https://github.com/teh-hippo/ha-porkbun/commit/f096dbd6df1be846a631d24812a1e088ece1e19b))

- Standardise tooling — uv, ruff, mypy strict, PSR, dependabot
  ([`0f7b415`](https://github.com/teh-hippo/ha-porkbun/commit/0f7b41500c32865713cf6623707d79a1b6638890))


## v1.2.7 (2026-02-18)

### Bug Fixes

- Publish LOC reduction release
  ([`c842f4e`](https://github.com/teh-hippo/ha-porkbun/commit/c842f4e2b8dd022d325ac409f6b9bff854a6bfe2))

### Chores

- Shrink docs and workflow footprint
  ([`f2b222b`](https://github.com/teh-hippo/ha-porkbun/commit/f2b222bd8041f01d70ca3eb64aa423852265c4cf))

### Refactoring

- Reduce runtime and test LOC
  ([`56d0525`](https://github.com/teh-hippo/ha-porkbun/commit/56d05252bdd0fb1897642071ce83c9dbad6fe754))


## v1.2.6 (2026-02-19)

### Documentation

- Tighten and refresh README
  ([`248f1d1`](https://github.com/teh-hippo/ha-porkbun/commit/248f1d19a9ebbccc11704e310d0fa845d814b0ea))


## v1.2.5 (2026-02-19)

### Continuous Integration

- Harden validation and type checks
  ([`3b97402`](https://github.com/teh-hippo/ha-porkbun/commit/3b97402480d3bc1f9b9589911ff7c489065af94e))

- Stabilize validation and HACS release delivery
  ([`3e71cfd`](https://github.com/teh-hippo/ha-porkbun/commit/3e71cfd1e4df842a188e776355e2f92afb6cb106))

### Refactoring

- Simplify coordinator and test helpers
  ([`bb9316c`](https://github.com/teh-hippo/ha-porkbun/commit/bb9316c7065847ed02ef634971d185abf5b76b8c))

### Testing

- Add snapshot coverage for all entity platforms
  ([`bd0e873`](https://github.com/teh-hippo/ha-porkbun/commit/bd0e8736425424c60960f0571ff1c8d8575aa6ab))

- Expand coverage for setup, reconfigure, and timestamps
  ([`dd24eba`](https://github.com/teh-hippo/ha-porkbun/commit/dd24eba58eb1f55880ffc65fc151294104149c3d))


## v1.2.4 (2026-02-18)

### Bug Fixes

- Resolve coordinator and sensor behavior bugs
  ([`cc57ae8`](https://github.com/teh-hippo/ha-porkbun/commit/cc57ae8951be2672ba2829d02ea38d48f34dbc2a))

### Refactoring

- Align with Home Assistant integration patterns
  ([`6638bb8`](https://github.com/teh-hippo/ha-porkbun/commit/6638bb8d110d6216e5195e227f3c46a19eaa2d0b))


## v1.2.3 (2026-02-18)

### Bug Fixes

- Resolve ruff linting errors breaking CI
  ([`40a91d2`](https://github.com/teh-hippo/ha-porkbun/commit/40a91d29d839c7236ed6076a09e75c2e9f556fe8))


## v1.2.2 (2026-02-18)

### Bug Fixes

- Add per-request timeout to Porkbun API client
  ([`114b13c`](https://github.com/teh-hippo/ha-porkbun/commit/114b13c6215a68809e1db4ce04c2db2e7928962d))


## v1.2.1 (2026-02-18)

### Bug Fixes

- Show 'Refreshing' when next update is overdue
  ([`4bccf71`](https://github.com/teh-hippo/ha-porkbun/commit/4bccf71423e26603325dd987ca58f92770e60f15))


## v1.2.0 (2026-02-15)

### Features

- Add managed subdomains sensor
  ([`25f783b`](https://github.com/teh-hippo/ha-porkbun/commit/25f783bb14185a6938c00a68e420e8bf28703348))


## v1.1.0 (2026-02-15)

### Bug Fixes

- Align icons/docs with refresh action
  ([`a9e1698`](https://github.com/teh-hippo/ha-porkbun/commit/a9e16982b405ef9274125dc225e12e6714c64090))

### Features

- Improve entity naming and collapse record problem sensors
  ([`bf94b78`](https://github.com/teh-hippo/ha-porkbun/commit/bf94b78a791f23a335cb77cafd200bc46c588317))


## v1.0.0 (2026-02-15)

### Chores

- **deps**: Bump the actions group across 1 directory with 5 updates
  ([`5d08691`](https://github.com/teh-hippo/ha-porkbun/commit/5d08691f628f954ae21267fe9cc9896aada4b1f7))


## v0.12.0 (2026-02-14)

### Bug Fixes

- Enable tag push in release workflow
  ([`581eb02`](https://github.com/teh-hippo/ha-porkbun/commit/581eb020aba67b3b3f6226117bea124071006212))

- **ci**: Use tag-only release to avoid protected branch push
  ([`fd1220e`](https://github.com/teh-hippo/ha-porkbun/commit/fd1220e264ea576f90cc782d02b6fbad4ef2de4d))

### Features

- Add per-record binary sensors for subdomain visibility
  ([`557b7a6`](https://github.com/teh-hippo/ha-porkbun/commit/557b7a6a15501f750375c410ed1c88724c5dc51b))

### Refactoring

- Remove dead code, fix icons.json keys, simplify guards
  ([`05dadd8`](https://github.com/teh-hippo/ha-porkbun/commit/05dadd81ce8313fc3e00bb252d36ec3c11753b8a))


## v0.11.2 (2026-02-14)

### Bug Fixes

- **ci**: Use RELEASE_TOKEN to bypass branch protection in release workflow
  ([`fb199aa`](https://github.com/teh-hippo/ha-porkbun/commit/fb199aa4a8b8ba1f85178a70a752c224a650b83b))


## v0.11.1 (2026-02-13)

### Bug Fixes

- **ci**: Automate dependency security maintenance
  ([`2ed49a9`](https://github.com/teh-hippo/ha-porkbun/commit/2ed49a9ee9b685f03e372c80ed708ce93b6109af))

### Refactoring

- Consolidate device_info, extract _try_api helper, remove dead code
  ([`662ab8a`](https://github.com/teh-hippo/ha-porkbun/commit/662ab8aa5805e2c6f97f4df14e897cb69026ed21))


## v0.11.0 (2026-02-12)

### Features

- Gold quality scale - diagnostics, entity categories, translations, reconfigure flow, stale devices
  ([`12fc6e5`](https://github.com/teh-hippo/ha-porkbun/commit/12fc6e5311e3c1ea5061bc2581f5d1e5c6102f41))


## v0.10.0 (2026-02-12)

### Features

- Silver quality scale completion
  ([`21a623d`](https://github.com/teh-hippo/ha-porkbun/commit/21a623d5f20cec177b3859cd1c6e2869c4ce2821))


## v0.9.0 (2026-02-12)

### Features

- Bronze quality scale completion
  ([`dfce223`](https://github.com/teh-hippo/ha-porkbun/commit/dfce223220dd859062cef9a3aa7345fc88ab2697))


## v0.8.1 (2026-02-12)

### Bug Fixes

- Replace branding with official Porkbun assets
  ([`30de32b`](https://github.com/teh-hippo/ha-porkbun/commit/30de32b42f16f22eddab4bd953caa50e6c2f13a1))


## v0.8.0 (2026-02-12)

### Features

- Add domain expiry and WHOIS privacy sensors
  ([`8f1fa81`](https://github.com/teh-hippo/ha-porkbun/commit/8f1fa81cf7b512b9ed1816a427fbad62a8c868cf))


## v0.7.0 (2026-02-12)

### Features

- Add PARALLEL_UPDATES = 1 to all platform files
  ([`b0e031f`](https://github.com/teh-hippo/ha-porkbun/commit/b0e031fecde9a9034a913c4db2d9a3fc914880b5))

- Add strict typing with py.typed marker and mypy config
  ([`77682ea`](https://github.com/teh-hippo/ha-porkbun/commit/77682eafb31296f5dd47bdf538635b79a42c30ac))

### Refactoring

- Migrate to ConfigEntry.runtime_data pattern
  ([`71a395c`](https://github.com/teh-hippo/ha-porkbun/commit/71a395cbd5250bd15a2dfe685e3425e3bc28af56))


## v0.6.0 (2026-02-12)

### Features

- Add force-update button, health status sensor, disable IP by default
  ([`b1413be`](https://github.com/teh-hippo/ha-porkbun/commit/b1413beff63afd166d278329b0c9ab55de6908d0))


## v0.5.0 (2026-02-12)

### Features

- Consolidate to device-level sensors, add brand icon
  ([`257fe2e`](https://github.com/teh-hippo/ha-porkbun/commit/257fe2e1195824db0acd67a891428216be42ac55))


## v0.4.0 (2026-02-12)

### Features

- Add brand icon for HACS and HA display
  ([`0b09c86`](https://github.com/teh-hippo/ha-porkbun/commit/0b09c865a0009f3865d767d30c2767648d8495a1))


## v0.3.0 (2026-02-12)

### Features

- Add icons.json for entity icons
  ([`f51275d`](https://github.com/teh-hippo/ha-porkbun/commit/f51275d091fad95ec55a2ef68e905d493f6107ae))


## v0.2.0 (2026-02-12)

### Features

- Restructure sensors - device-level timing, cleaner naming, drop last_changed
  ([`0a91d4e`](https://github.com/teh-hippo/ha-porkbun/commit/0a91d4ef428787a92a933abb8a0316ec040058a4))


## v0.1.3 (2026-02-12)

### Bug Fixes

- Use always_update=True and remove unpersistable last_changed
  ([`4c77aaf`](https://github.com/teh-hippo/ha-porkbun/commit/4c77aaf1347285d842cb219e85dd2db185cdce4c))


## v0.1.2 (2026-02-12)

### Bug Fixes

- Use timezone-aware datetimes for HA sensor compatibility
  ([`b61354e`](https://github.com/teh-hippo/ha-porkbun/commit/b61354efa022fc54ef55e99988bf63487f56400f))

### Chores

- Remove uv.lock from repo
  ([`d7c3ae1`](https://github.com/teh-hippo/ha-porkbun/commit/d7c3ae1a7208b47c6c2bb1458fbfcb4fc71eeaa7))


## v0.1.1 (2026-02-12)

### Bug Fixes

- Include manifest.json in semantic-release version tracking
  ([`c9cee80`](https://github.com/teh-hippo/ha-porkbun/commit/c9cee807ad8a8f8bd62c47b78f1077bd97ce826b))


## v0.1.0 (2026-02-12)

- Initial Release
