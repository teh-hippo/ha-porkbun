# Agent Notes

## Build & Test

```bash
pip install -r requirements_test.txt
pytest tests/ -v
ruff check .
ruff format --check .
```

All 61 tests should pass. Use `ruff` for linting and formatting.

## CI/CD Workflows

### Release Workflow (`release.yml`)

Uses `python-semantic-release` to determine the next version, create a git tag,
and publish a GitHub Release — all without pushing commits to `master`.

The workflow uses `commit: false`, `push: false`, and `changelog: false` to avoid
needing to push to the protected `master` branch. This means:

- Version numbers in source files (`pyproject.toml`, `const.py`, `manifest.json`)
  are **not** auto-bumped by CI. They are cosmetic — HACS uses the git tag.
- The `CHANGELOG.md` is not auto-updated by CI.
- If you want source versions to match the release, bump them manually.
- No PAT or deploy key is required; the default `GITHUB_TOKEN` is sufficient.

### Dependabot Auto-Merge (`dependabot-automerge.yml`)

Auto-approves and merges patch/minor dependency updates. Major updates are flagged
with a `major-update` label and a PR comment for manual review.

**Resolved issue:** The `major-update` label must exist in the repo or the workflow
fails when trying to add it to a PR. The label has been created.

### Validate (`validate.yml`)

Runs hassfest, HACS validation, ruff lint/format, and pytest on push/PR/schedule.
This is the required status check for branch protection.

### CodeQL (`codeql.yml`)

Weekly Python security analysis. No known issues.

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `chore:`, etc.) for semantic-release version bumping.
- Version is tracked in `pyproject.toml`, `const.py`, and `manifest.json` via
  `python-semantic-release` configuration.
- Use `datetime.now(tz=UTC)` for all timestamps — Home Assistant rejects
  timezone-naive datetimes in `SensorDeviceClass.TIMESTAMP` entities.
