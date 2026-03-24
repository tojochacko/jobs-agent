# uv Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the backend from `pip` + `requirements.txt` to `uv` + `pyproject.toml` + `uv.lock` for deterministic, faster Docker builds.

**Architecture:** Replace `backend/requirements.txt` with `backend/pyproject.toml` (production deps) and a `[dependency-groups] dev` group (test deps). Generate `backend/uv.lock` inside a Linux Docker container to ensure correct platform markers. Update `backend/Dockerfile` to copy the uv binary and use `uv sync --frozen --no-dev`. Zero application code changes.

**Tech Stack:** uv 0.11.0 (`ghcr.io/astral-sh/uv:0.11.0`), Python 3.12, Docker, pyproject.toml (PEP 517), uv.lock (PEP 735 dependency groups)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `backend/pyproject.toml` | Project metadata + all deps (prod + dev groups) |
| Create | `backend/uv.lock` | Generated deterministic lock file |
| Modify | `backend/Dockerfile` lines 26–28 | Swap pip → uv; add uv binary copy |
| Modify | `.devcontainer/devcontainer.json` line 22 | Update `postCreateCommand` to use uv |
| Delete | `backend/requirements.txt` | Superseded by pyproject.toml |
| Modify | `CLAUDE.md` line 117 | Update dev command from pip to uv sync |

---

## Task 1: Create `backend/pyproject.toml`

**Files:**
- Create: `backend/pyproject.toml`

This is a pure config file — no tests to write. Verification is that Docker builds succeed in Task 4.

- [ ] **Step 1: Create `backend/pyproject.toml`**

Create the file with this exact content (all version pins match the current `backend/requirements.txt`; `litellm` is an exact `==` pin to prevent accidental unlock):

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

- [ ] **Step 2: Verify the file exists and parses**

```bash
cat backend/pyproject.toml
```

Expected: file contents printed with no errors.

- [ ] **Step 3: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore(deps): add pyproject.toml for uv migration"
```

---

## Task 2: Generate `backend/uv.lock`

**Files:**
- Create: `backend/uv.lock` (generated, not hand-written)

**Important:** The lock file MUST be generated inside a Linux Docker container. Running `uv lock` on a macOS host produces wrong platform markers for the Linux production image.

- [ ] **Step 1: Pull the uv image**

Run from the project root (`JobApplierAgent/`):

```bash
docker pull ghcr.io/astral-sh/uv:0.11.0
```

Expected: image pulled (or already cached).

- [ ] **Step 2: Generate the lock file**

Run from the project root:

```bash
docker run --rm \
  -v $(pwd)/backend:/app \
  -w /app \
  ghcr.io/astral-sh/uv:0.11.0 \
  uv lock
```

Expected: exits 0, `backend/uv.lock` now exists.

- [ ] **Step 3: Verify litellm version in the lock file**

```bash
grep "name = \"litellm\"" backend/uv.lock -A 2
```

Expected output contains `version = "1.82.6"` — not any higher version.

- [ ] **Step 4: Commit**

```bash
git add backend/uv.lock
git commit -m "chore(deps): generate uv.lock"
```

---

## Task 3: Update `backend/Dockerfile`

**Files:**
- Modify: `backend/Dockerfile` lines 26–28

Replace lines 26–28 (the comment, `COPY requirements.txt`, and `RUN pip install` lines) with the uv equivalent. Everything else in the Dockerfile stays identical.

- [ ] **Step 1: Open `backend/Dockerfile` and replace lines 26–28**

Current lines 26–28:
```dockerfile
# Build context is the project root, so requirements.txt is at backend/requirements.txt
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

Replace with:
```dockerfile
# Install uv (pinned version matches lock file generation)
COPY --from=ghcr.io/astral-sh/uv:0.11.0 /uv /usr/local/bin/uv
ENV UV_SYSTEM_PYTHON=1

# Copy dependency files before app code for Docker layer cache efficiency
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
```

`--frozen`: fails fast if `uv.lock` is stale rather than silently re-resolving.
`--no-dev`: excludes pytest/pytest-mock from the production image.
`UV_SYSTEM_PYTHON=1`: installs into system Python, same behaviour as pip — no venv.

- [ ] **Step 2: Verify the Dockerfile looks correct**

```bash
cat backend/Dockerfile
```

Expected: no reference to `pip` or `requirements.txt`. The `COPY backend/ ./backend/` line and everything after remains unchanged.

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile
git commit -m "chore(deps): migrate Dockerfile from pip to uv"
```

---

## Task 4: Build and test the Docker image

**Files:** None (verification only)

This is the primary acceptance test for Tasks 1–3.

- [ ] **Step 1: Build the backend image**

```bash
docker compose build backend
```

Expected: build succeeds with no errors. You should see uv resolving packages from the lock file, not pip.

- [ ] **Step 2: Confirm pytest is NOT in the production image**

```bash
docker compose run --rm backend python -c "import pytest" 2>&1
```

Expected: `ModuleNotFoundError: No module named 'pytest'` — confirms `--no-dev` is working.

- [ ] **Step 3: Run the test suite inside the container**

```bash
docker compose run --rm backend pytest backend/tests/ -v
```

Expected: all tests pass (same result as before the migration).

- [ ] **Step 4: Confirm litellm version inside the container**

```bash
docker compose run --rm backend python -c "import litellm; print(litellm.__version__)"
```

Expected: `1.82.6`

---

## Task 5: Update devcontainer, delete requirements.txt, update CLAUDE.md

**Files:**
- Modify: `.devcontainer/devcontainer.json` line 22
- Delete: `backend/requirements.txt`
- Modify: `CLAUDE.md` line 117

- [ ] **Step 1: Update `.devcontainer/devcontainer.json`**

Find line 22 (`"postCreateCommand": "pip install -r /app/requirements.txt"`). Replace it with:

```json
"postCreateCommand": "cd /workspaces/JobApplierAgent/backend && uv sync"
```

Plain `uv sync` (no `--no-dev`) so pytest is available inside the devcontainer.

- [ ] **Step 2: Delete `backend/requirements.txt`**

```bash
rm backend/requirements.txt
```

- [ ] **Step 3: Update `CLAUDE.md` dev commands section**

Find the **Backend** development commands block (around line 115–120):

```
**Backend:**
```
pip install -r requirements.txt
uvicorn main:app --reload          # starts at :8000
pytest                             # run all tests
```
```

Replace `pip install -r requirements.txt` with `uv sync`:

```
**Backend:**
```
uv sync                            # install/update dependencies
uvicorn main:app --reload          # starts at :8000
pytest                             # run all tests
```
```

- [ ] **Step 4: Verify requirements.txt is gone**

```bash
ls backend/requirements.txt 2>&1
```

Expected: `No such file or directory`

- [ ] **Step 5: Commit everything**

```bash
git add .devcontainer/devcontainer.json CLAUDE.md
git rm backend/requirements.txt
git commit -m "chore(deps): remove requirements.txt, update devcontainer and CLAUDE.md for uv"
```

- [ ] **Step 6: Push to upstream**

```bash
git push origin main
```

Expected: push succeeds. All 3 commits from this migration land on `main`.

---

## Verification Checklist

After all tasks complete, confirm:

- [ ] `docker compose build backend` succeeds
- [ ] `docker compose run --rm backend pytest backend/tests/ -v` — all tests pass
- [ ] `grep "version = \"1.82.6\"" backend/uv.lock` — litellm pinned correctly
- [ ] `docker compose run --rm backend python -c "import pytest"` — raises `ModuleNotFoundError`
- [ ] `backend/requirements.txt` does not exist
- [ ] `backend/pyproject.toml` and `backend/uv.lock` are committed
- [ ] `.devcontainer/devcontainer.json` uses `uv sync`
- [ ] `CLAUDE.md` shows `uv sync` not `pip install`
