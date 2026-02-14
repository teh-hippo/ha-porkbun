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

Uses `python-semantic-release` to version-bump, commit, tag, and publish.

**Known issue:** The `master` branch has protection requiring the `Validate` status
check. `GITHUB_TOKEN` cannot bypass this, so semantic-release fails to push the
version-bump commit.

**Fix:** Create a fine-grained PAT with `contents: write` scope on this repo and
add it as a repository secret named `RELEASE_TOKEN`. The workflow already
references `secrets.RELEASE_TOKEN` with a fallback to `GITHUB_TOKEN`. Since
`enforce_admins` is disabled, the PAT will bypass the required status check.

To create the PAT: GitHub → Settings → Developer settings → Fine-grained tokens →
Generate new token → Select `teh-hippo/ha-porkbun` → Repository permissions →
Contents: Read and write. Then add it as a repo secret:

```bash
gh secret set RELEASE_TOKEN --repo teh-hippo/ha-porkbun
```

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
