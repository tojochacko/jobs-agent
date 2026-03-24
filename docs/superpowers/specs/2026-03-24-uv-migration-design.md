# uv Migration Design

**Date:** 2026-03-24
**Status:** Approved

## Overview

Migrate the backend Python package manager from `pip` + `requirements.txt` to `uv` + `pyproject.toml` + `uv.lock`. Zero application code changes. Improves build determinism and speed.

## Goals

- Replace `requirements.txt` with `pyproject.toml` as the dependency source of truth
- Generate a `uv.lock` lock file that pins every transitive dependency (closes the supply-chain gap highlighted by the litellm 1.82.7/1.82.8 incident)
- Faster Docker image builds via uv's aggressive caching
- Separate dev dependencies (pytest, pytest-mock) from production dependencies

## Non-Goals

- Frontend tooling changes (Node/npm unchanged)
- Application code changes
- Runtime behaviour changes

## File Changes

### Create `backend/pyproject.toml`

Standard PEP 517 project file. Production dependencies mirror current `requirements.txt` pins exactly. `litellm` is pinned to `==1.82.6` (exact, not upper-bound) to make intent explicit and prevent accidental unlock on lock file regeneration.

Test dependencies move to a `[dependency-groups] dev` group — uv's native dev group (PEP 735). This group is excluded from the production Docker image via `--no-dev`. Note: `[dependency-groups]` is uv-specific and not visible to pip or Dependabot; if those tools ever need dev deps, migrate to `[project.optional-dependencies]` at that point.

```toml
[project]
name = "jobapplier"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.115.5",
    "uvicorn[standard]==0.32.1",
    "sqlalchemy==2.0.36",
    "pydantic-settings==2.6.1",
    "python-multipart==0.0.12",
    "litellm==1.82.6",
    "requests==2.32.3",
    "httpx==0.27.2",
    "fpdf2==2.7.9",
    "pdfminer.six==20231228",
    "python-docx==1.1.2",
    "playwright>=1.48.0",
    "google-auth>=2.35.0",
    "google-auth-oauthlib>=1.2.1",
    "google-api-python-client>=2.154.0",
    "msal>=1.31.0",
]

[dependency-groups]
dev = ["pytest==8.3.3", "pytest-mock==3.14.0"]
```

### Create `backend/uv.lock`

Generated inside a uv Docker container to ensure platform markers match the Linux/amd64 production image:

```bash
docker run --rm \
  -v $(pwd)/backend:/app \
  -w /app \
  ghcr.io/astral-sh/uv:0.11.0 \
  uv lock
```

The resulting `uv.lock` is committed to the repository. Lock file regeneration must always use the same container command (not host `uv lock`) to preserve consistent platform markers.

### Modify `backend/Dockerfile`

The uv binary is copied from the pinned `ghcr.io/astral-sh/uv:0.11.0` image. `UV_SYSTEM_PYTHON=1` installs packages into system Python (no venv). The existing Playwright browser setup (`PLAYWRIGHT_BROWSERS_PATH`, `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`) is preserved unchanged — browsers are provided by `apt-get chromium`, and no `playwright install` step is added.

This replaces lines 27–28 of the current `backend/Dockerfile` (the `COPY backend/requirements.txt .` and `RUN pip install` lines) while leaving `WORKDIR /app` and everything else unchanged:

```dockerfile
# Install uv (pinned version)
COPY --from=ghcr.io/astral-sh/uv:0.11.0 /uv /usr/local/bin/uv
ENV UV_SYSTEM_PYTHON=1

# Copy dependency files first for Docker layer cache efficiency
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code after deps (cache hit if only code changes)
COPY backend/ ./backend/
```

`--frozen` enforces that `uv.lock` is the authority and fails fast if stale. `--no-dev` excludes pytest/pytest-mock from the production image. The `WORKDIR` remains `/app` and the build context remains the project root, so `backend/pyproject.toml` and `backend/uv.lock` paths are relative to the project root, consistent with the existing Dockerfile.

### Modify `.devcontainer/devcontainer.json`

Change `postCreateCommand` to use uv. The uv binary is available at `/usr/local/bin/uv` because the devcontainer attaches to the `backend` service, which is built from the same Dockerfile. The workspace is mounted at `/workspaces/JobApplierAgent`, so `pyproject.toml` is at `/workspaces/JobApplierAgent/backend/`:

```json
"postCreateCommand": "cd /workspaces/JobApplierAgent/backend && uv sync"
```

Plain `uv sync` (without `--no-dev`) includes dev deps so pytest is available inside the devcontainer.

**Warning:** `uv.lock` must be generated using the Linux container command above (not a host-OS `uv lock`). If a macOS-generated lock file is committed, `uv sync` inside the devcontainer may silently use wrong platform markers, causing incorrect package resolution.

### Delete `backend/requirements.txt`

Superseded by `backend/pyproject.toml`.

### Update `CLAUDE.md`

The backend development commands section lists `pip install -r requirements.txt`. Replace with `uv sync` to reflect the new workflow.

## Key Decisions

| Decision | Rationale |
|---|---|
| `pyproject.toml` in `backend/` not project root | Python-only project co-located with Python code; clean separation from Node frontend |
| `UV_SYSTEM_PYTHON=1` | Matches pip behaviour; no venv management inside container |
| `--frozen` in production image | Lock file is authoritative; fails fast if stale rather than silently resolving |
| `--no-dev` in production image | Excludes pytest/pytest-mock from the production image |
| uv binary via `COPY --from` with pinned tag | Deterministic uv version; no apt/pip step; `ghcr.io/astral-sh/uv:0.11.0` |
| `litellm==1.82.6` exact pin | Explicit intent; prevents accidental unlock on lock file regeneration |
| Lock generation inside container | Ensures Linux platform markers; avoids host OS / Python version mismatch |
| `[dependency-groups]` for dev deps | uv-native PEP 735 approach; excluded by `--no-dev`; migrate to optional-deps if pip/Dependabot access needed |

## Testing

- Rebuild the Docker image (`docker compose build backend`) — must succeed with `uv sync --frozen --no-dev`
- Run backend tests inside the container (`docker compose run --rm backend pytest`) — must pass
- Confirm `litellm 1.82.6` appears in `uv.lock` (not a newer version)
- Confirm `pytest` and `pytest-mock` do NOT appear in the production image site-packages
