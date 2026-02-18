# Agent Notes

## Build & Test

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy custom_components/porkbun_ddns
.venv/bin/pytest tests/ -v
```

## CI/CD Summary

### validate.yml
- Required branch-protection check
- Runs hassfest, HACS validation, ruff, mypy, pytest

### release.yml
- Uses `python-semantic-release`
- `commit: false`, `changelog: false`
- Tags drive releases; source versions are not auto-bumped
- Publishes `porkbun_ddns.zip` for HACS

### dependabot-automerge.yml
- Auto-approves + auto-merges patch/minor updates
- Labels/comments major updates for manual review
- Requires existing `major-update` label

## Conventions

- Use Conventional Commits (`feat:`, `fix:`, `chore:`)
- Keep versions aligned in `pyproject.toml`, `manifest.json`, `const.py` when manually bumping
- Use timezone-aware `datetime.now(tz=UTC)` for timestamp sensors
