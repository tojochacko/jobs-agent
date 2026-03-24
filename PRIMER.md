# JobApplierAgent — Session Primer

## What Was Done This Session (2026-03-24)

### Security fixes + uv migration

**1. litellm supply chain attack (CVE)**

Versions 1.82.7 and 1.82.8 of litellm contained a malicious `.pth` file (`litellm_init.pth`) that auto-executes a credential-stealing script on every Python interpreter start, exfiltrating env vars, SSH keys, and cloud credentials to `https://models.litellm.cloud/`.

- Confirmed container was NOT compromised (had 1.82.6, no `.pth` files found)
- Pinned `litellm<=1.82.6` in `requirements.txt` (then migrated to `==1.82.6` in `pyproject.toml`)
- Changed Docker port bindings from `0.0.0.0` to `127.0.0.1` (`:8000` and `:5173` — LAN exposure removed)
- Commits: `55dcd5d`, `32799e4`

**2. uv migration (pip → uv + pyproject.toml + uv.lock)**

| Commit | Change |
|---|---|
| `7a18bdf` | Create `backend/pyproject.toml` (prod deps + `[dependency-groups] dev`) |
| `799a858` | Generate `backend/uv.lock` (inside Linux Docker container for correct platform markers) |
| `5c7a8c5` | Update `backend/Dockerfile` — uv binary from `ghcr.io/astral-sh/uv:0.11.0`, `uv sync --frozen --no-dev` |
| `2816486` | Fix: add `ENV PATH="/app/.venv/bin:$PATH"` (uv project mode creates venv, not system install) |
| `d085ad5` | Remove `requirements.txt`, update devcontainer `postCreateCommand`, update `CLAUDE.md` |

All 75 tests pass. Everything is on `main` and pushed.

**Key uv notes for future sessions:**
- Run tests: `docker compose run --rm backend sh -c "uv sync && pytest backend/tests/ -v"`
- Regenerate lock file (must use Linux container): `docker run --rm -v $(pwd)/backend:/app -w /app ghcr.io/astral-sh/uv:0.11.0 uv lock`
- Add a dep: `uv add <package>` inside the backend container (then regenerate lock)
- Dev deps excluded from production image (`--no-dev`); pytest available only after `uv sync` inside container

---

## What Was Done Previously (2026-03-24)

Executed **Frontend UI Redesign** + **LiteLLM migration** on `feat/litellm-migration`, then merged to `main`.

**LiteLLM migration:** Replaced Anthropic SDK with LiteLLM across all 5 agent files. Model strings prefixed `anthropic/`. Provider swappable via env vars (`ORCHESTRATOR_MODEL`, `SCOUT_MODEL`, `APPLICATOR_MODEL`, `OUTREACH_MODEL`) — no code changes needed to switch provider.

**UI Redesign:** Warm-neutral CSS theme, left sidebar AppShell, TagInput component (TDD, 7 tests), upgraded Preferences page (TagInput, dropdowns, pill checkboxes).

---

## What Was Done Previously (2026-03-23)

- **Phase 4 — Webhook Integration:** `POST /webhook/job-alerts`, Orchestrator scoring agent, deduplication by URL
- **Phase 3 — Cold Email Outreach:** Outreach Agent, Gmail/Outlook OAuth, HR contact lookup, cover letter generation
- **Phase 2 — Application Flow:** Applicator Agent, Playwright form pre-fill, application tracking pipeline
- **Phase 1 — Foundation Dashboard:** Backend API, JobScout Agent, scheduler, job dashboard, preferences, resume upload

---

## Current State

| Area | Status |
|---|---|
| Phase 1 — Foundation Dashboard | ✅ Complete |
| Phase 2 — Application Flow | ✅ Complete |
| Phase 3 — Cold Email Outreach | ✅ Complete |
| Phase 4 — Webhook Integration | ✅ Complete |
| Phase 5 — LiteLLM + UI Redesign | ✅ Complete |
| uv migration | ✅ Complete |
| Docker port hardening | ✅ Complete |

**Test count:** 75 backend tests passing.

**Known technical debt (non-blocking):**
- `datetime.utcnow()` deprecated in Python 3.12+ — affects `email_tools.py`, `auth.py`, `outreach.py`, test files
- `JobResponse` in `routers/jobs.py:12` uses Pydantic v1 class-based config (will break on Pydantic v3)
- `jobs.url` has both `unique=True` and a named `UniqueConstraint` — harmless for SQLite, duplicate on PostgreSQL
- `OutreachPanel` fires PATCH on every keystroke (no debounce)

---

## Recommended Next Steps

**Start the stack:**
```bash
docker compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

**Run tests:**
```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/ -v"
docker compose exec frontend npm run test:run
```

**Potential follow-up improvements:**
- Fix `datetime.utcnow()` deprecation warnings (search: `utcnow` in `backend/`)
- Fix Pydantic v1 class-based config in `routers/jobs.py:12`
- Upgrade webhook auth to HMAC-SHA256 signature verification (currently plain string equality)
- Restyle Dashboard, Applications, Outreach, Settings page internals (Preferences was restyled; others have inline styles)
- Add async/batch scoring to webhook router for large job payloads
- When litellm releases a clean version ≥1.82.9, update the pin in `backend/pyproject.toml` and regenerate `uv.lock`
