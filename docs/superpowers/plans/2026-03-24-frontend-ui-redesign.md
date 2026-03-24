# Frontend UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply a warm-neutral CSS theme with left-sidebar navigation and upgrade the Preferences page with a tag input, dropdowns, and checkbox group — all without touching backend or other page internals.

**Architecture:** Replace `App.css` with CSS custom-property tokens consumed by new components. Wrap all routes in a new `AppShell` component that renders the left sidebar. Build a standalone `TagInput` component tested in isolation; integrate it alongside dropdown and checkbox field upgrades into `Preferences.jsx`. Shared form styles live in `Form.css`.

**Tech Stack:** React 19, Vitest + Testing Library. All commands run inside Docker: `docker compose exec frontend <cmd>`. Test a specific file with `npx vitest run --reporter verbose <path>`.

**Spec:** `docs/superpowers/specs/2026-03-24-frontend-ui-redesign.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/App.css` | Modify | CSS custom properties (tokens) + global resets |
| `frontend/src/components/AppShell.jsx` | Create | Sidebar + main layout wrapper |
| `frontend/src/components/AppShell.css` | Create | Shell and sidebar styles |
| `frontend/src/App.jsx` | Modify | Wrap routes in `<AppShell>` |
| `frontend/src/components/TagInput.jsx` | Create | Controlled tag input component |
| `frontend/src/components/TagInput.css` | Create | Tag input styles |
| `frontend/src/components/TagInput.test.jsx` | Create | Unit tests for TagInput |
| `frontend/src/components/Form.css` | Create | Shared form element styles |
| `frontend/src/pages/Preferences.jsx` | Modify | Use TagInput, dropdowns, checkboxes, Form.css |

---

## Task 1: CSS Theme

**Files:**
- Modify: `frontend/src/App.css`

No unit tests for CSS — run full suite after to confirm no regressions.

- [ ] **Step 1: Replace App.css with theme tokens and global resets**

Overwrite the entire content of `frontend/src/App.css`:

```css
/* ── Warm Neutral Theme ─────────────────────────────────── */
:root {
  --bg:            #faf9f7;
  --surface:       #ffffff;
  --border:        #e8e4de;
  --border-input:  #d6d3cf;
  --text-primary:  #1c1917;
  --text-secondary:#57534e;
  --text-muted:    #a8a29e;
  --accent:        #d97706;
  --accent-light:  #fef9ec;
  --accent-border: #fcd34d;
  --tag-text:      #92400e;
  --radius-sm:     6px;
  --radius-md:     8px;
  --radius-lg:     10px;
}

/* ── Global resets ──────────────────────────────────────── */
body {
  margin: 0;
  background: var(--bg);
  color: var(--text-primary);
  font-family: system-ui, 'Segoe UI', Roboto, sans-serif;
}

#root {
  display: flex;
  flex-direction: column;
  min-height: 100svh;
}
```

- [ ] **Step 2: Run full test suite to confirm no regressions**

```bash
docker compose exec frontend npm run test:run
```

Expected: all 18 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.css
git commit -m "feat(ui): add warm-neutral CSS theme tokens"
```

---

## Task 2: AppShell + Left Sidebar

**Files:**
- Create: `frontend/src/components/AppShell.css`
- Create: `frontend/src/components/AppShell.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Create AppShell.css**

```css
/* frontend/src/components/AppShell.css */
.app-shell {
  display: flex;
  height: 100svh;
  overflow: hidden;
}

.sidebar {
  width: 172px;
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}

.sidebar-brand {
  padding: 18px 16px 12px;
  border-bottom: 1px solid var(--border);
}

.sidebar-brand-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.sidebar-brand-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 3px;
}

.sidebar-nav {
  padding: 8px 0;
  flex: 1;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: 13px;
  color: var(--text-muted);
  text-decoration: none;
  border-right: 3px solid transparent;
  transition: color 0.15s;
}

.sidebar-link:hover {
  color: var(--text-primary);
}

.sidebar-link.active {
  color: var(--accent);
  font-weight: 600;
  background: var(--accent-light);
  border-right-color: var(--accent);
}

.sidebar-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border);
  flex-shrink: 0;
}

.sidebar-link.active .sidebar-dot {
  background: var(--accent);
}

.app-main {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
}
```

- [ ] **Step 2: Create AppShell.jsx**

```jsx
// frontend/src/components/AppShell.jsx
import { NavLink } from 'react-router-dom'
import './AppShell.css'

const NAV_LINKS = [
  { to: '/',            label: 'Dashboard'    },
  { to: '/preferences', label: 'Preferences'  },
  { to: '/applications',label: 'Applications' },
  { to: '/outreach',    label: 'Outreach'     },
  { to: '/settings',    label: 'Settings'     },
]

export function AppShell({ children }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-name">JobApplier</div>
          <div className="sidebar-brand-sub">Agent</div>
        </div>
        <nav className="sidebar-nav">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                'sidebar-link' + (isActive ? ' active' : '')
              }
            >
              <span className="sidebar-dot" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="app-main">{children}</main>
    </div>
  )
}
```

- [ ] **Step 3: Update App.jsx to use AppShell**

Replace the entire content of `frontend/src/App.jsx`:

```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { Dashboard } from './pages/Dashboard'
import { Preferences } from './pages/Preferences'
import { Applications } from './pages/Applications'
import { Outreach } from './pages/Outreach'
import { Settings } from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/preferences" element={<Preferences />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/outreach" element={<Outreach />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}
```

- [ ] **Step 4: Run full test suite**

```bash
docker compose exec frontend npm run test:run
```

Expected: all 18 tests pass. (Component tests render pages in isolation without BrowserRouter; App.jsx change only affects how routes are wrapped at the app level.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AppShell.css frontend/src/components/AppShell.jsx frontend/src/App.jsx
git commit -m "feat(ui): add left sidebar AppShell, replace top nav"
```

---

## Task 3: TagInput Component (TDD)

**Files:**
- Create: `frontend/src/components/TagInput.test.jsx`
- Create: `frontend/src/components/TagInput.jsx`
- Create: `frontend/src/components/TagInput.css`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/TagInput.test.jsx`:

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import { TagInput } from './TagInput'

describe('TagInput', () => {
  it('renders existing values as tags', () => {
    render(<TagInput values={['Python', 'React']} onChange={vi.fn()} />)
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('React')).toBeInTheDocument()
  })

  it('adds a tag on Enter and clears the input', () => {
    const onChange = vi.fn()
    render(<TagInput values={[]} onChange={onChange} />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Go Engineer' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(onChange).toHaveBeenCalledWith(['Go Engineer'])
  })

  it('adds a tag on comma keydown', () => {
    const onChange = vi.fn()
    render(<TagInput values={[]} onChange={onChange} />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'DevOps' } })
    fireEvent.keyDown(input, { key: ',' })
    expect(onChange).toHaveBeenCalledWith(['DevOps'])
  })

  it('removes a tag when × is clicked', () => {
    const onChange = vi.fn()
    render(<TagInput values={['Python', 'React']} onChange={onChange} />)
    fireEvent.click(screen.getAllByRole('button')[0])
    expect(onChange).toHaveBeenCalledWith(['React'])
  })

  it('removes last tag on Backspace when input is empty', () => {
    const onChange = vi.fn()
    render(<TagInput values={['Python', 'React']} onChange={onChange} />)
    const input = screen.getByRole('textbox')
    fireEvent.keyDown(input, { key: 'Backspace' })
    expect(onChange).toHaveBeenCalledWith(['Python'])
  })

  it('does not add duplicate values', () => {
    const onChange = vi.fn()
    render(<TagInput values={['Python']} onChange={onChange} />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Python' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(onChange).not.toHaveBeenCalled()
  })

  it('forwards id to the inner input', () => {
    render(<TagInput values={[]} onChange={vi.fn()} id="job_titles" />)
    expect(document.getElementById('job_titles')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec frontend npx vitest run --reporter verbose src/components/TagInput.test.jsx
```

Expected: 7 FAILED — `TagInput` not found.

- [ ] **Step 3: Create TagInput.css**

```css
/* frontend/src/components/TagInput.css */
.tag-input-container {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  background: var(--bg);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
  min-height: 38px;
  cursor: text;
}

.tag-input-container:focus-within {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--accent-light);
  border: 1px solid var(--accent-border);
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--tag-text);
  white-space: nowrap;
}

.tag-remove {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0;
  margin-left: 2px;
  display: flex;
  align-items: center;
}

.tag-input {
  border: none;
  background: transparent;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
  min-width: 140px;
  flex: 1;
}

.tag-input::placeholder {
  color: var(--text-muted);
}
```

- [ ] **Step 4: Create TagInput.jsx**

```jsx
// frontend/src/components/TagInput.jsx
import { useState, useRef } from 'react'
import './TagInput.css'

export function TagInput({ values, onChange, placeholder = 'Add, press Enter', id }) {
  const [input, setInput] = useState('')
  const inputRef = useRef(null)

  const addTag = () => {
    const trimmed = input.trim().replace(/,$/, '')
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed])
    }
    setInput('')
  }

  const removeTag = (index) => {
    onChange(values.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTag()
    } else if (e.key === 'Backspace' && input === '') {
      onChange(values.slice(0, -1))
    }
  }

  return (
    <div
      className="tag-input-container"
      onClick={() => inputRef.current?.focus()}
    >
      {values.map((val, i) => (
        <span key={val} className="tag">
          {val}
          <button
            type="button"
            className="tag-remove"
            onClick={(e) => { e.stopPropagation(); removeTag(i) }}
            aria-label={`Remove ${val}`}
          >
            ×
          </button>
        </span>
      ))}
      <input
        ref={inputRef}
        id={id}
        className="tag-input"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={values.length === 0 ? placeholder : ''}
      />
    </div>
  )
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
docker compose exec frontend npx vitest run --reporter verbose src/components/TagInput.test.jsx
```

Expected: 7 PASSED.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/TagInput.jsx frontend/src/components/TagInput.css frontend/src/components/TagInput.test.jsx
git commit -m "feat(ui): add TagInput component with full test coverage"
```

---

## Task 4: Form.css + Preferences Page Refactor

**Files:**
- Create: `frontend/src/components/Form.css`
- Modify: `frontend/src/pages/Preferences.jsx`

- [ ] **Step 1: Create Form.css**

```css
/* frontend/src/components/Form.css */
.form-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 16px;
}

.form-section-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.field label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 5px;
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 3px;
}

.input {
  background: var(--bg);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  padding: 7px 10px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.input:focus {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.select {
  background: var(--bg);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  padding: 7px 10px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
  width: 100%;
  box-sizing: border-box;
  cursor: pointer;
}

.select:focus {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.checkbox-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 5px 10px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
  transition: background 0.1s, border-color 0.1s, color 0.1s;
}

.checkbox-pill input[type="checkbox"] {
  accent-color: var(--accent);
}

.checkbox-pill:has(input:checked) {
  background: var(--accent-light);
  border-color: var(--accent-border);
  color: var(--tag-text);
  font-weight: 500;
}

.btn-primary {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 9px 22px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-secondary {
  background: var(--surface);
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 7px 14px;
  font-size: 12px;
  cursor: pointer;
}
```

- [ ] **Step 2: Rewrite Preferences.jsx**

Replace the entire content of `frontend/src/pages/Preferences.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { getPreferences, savePreferences, uploadResume, getResume } from '../api/client'
import { TagInput } from '../components/TagInput'
import '../components/Form.css'

const EXPERIENCE_OPTIONS = [
  { value: 'associate',       label: 'Associate'        },
  { value: 'mid-level',       label: 'Mid-level'        },
  { value: 'senior-level',    label: 'Senior-level'     },
  { value: 'executive-level', label: 'Executive-level'  },
]

const DOMAIN_OPTIONS = [
  { value: 'backend',          label: 'Backend Engineering'    },
  { value: 'frontend',         label: 'Frontend Engineering'   },
  { value: 'full-stack',       label: 'Full Stack'             },
  { value: 'data-science',     label: 'Data Science'           },
  { value: 'ml-ai',            label: 'ML / AI'                },
  { value: 'devops-infra',     label: 'DevOps / Infrastructure'},
  { value: 'mobile',           label: 'Mobile (iOS/Android)'   },
  { value: 'security',         label: 'Security'               },
  { value: 'data-engineering', label: 'Data Engineering'       },
  { value: 'sre-platform',     label: 'SRE / Platform'         },
  { value: 'product-management',label: 'Product Management'    },
  { value: 'design-ux',        label: 'Design / UX'            },
  { value: 'qa-testing',       label: 'QA / Testing'           },
  { value: 'game-development', label: 'Game Development'       },
  { value: 'blockchain-web3',  label: 'Blockchain / Web3'      },
  { value: 'embedded-systems', label: 'Embedded Systems'       },
]

const COMPANY_SIZE_OPTIONS = [
  { value: '<50',       label: '< 50'        },
  { value: '50-200',    label: '50 – 200'    },
  { value: '200-500',   label: '200 – 500'   },
  { value: '500-1000',  label: '500 – 1,000' },
  { value: '1000-5000', label: '1,000 – 5,000'},
  { value: '5000+',     label: '5,000+'      },
]

export function Preferences() {
  const [form, setForm] = useState({
    job_titles: [],
    location: '',
    remote_hybrid: 'any',
    experience_level: '',
    domain: '',
    company_size: [],
    poll_interval_hrs: 6,
  })
  const [resume, setResume] = useState(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getPreferences().then(pref => {
      if (pref) setForm({
        job_titles: pref.job_titles || [],
        location: pref.location || '',
        remote_hybrid: pref.remote_hybrid || 'any',
        experience_level: pref.experience_level || '',
        domain: pref.domain || '',
        company_size: pref.company_size || [],
        poll_interval_hrs: pref.poll_interval_hrs || 6,
      })
    })
    getResume().then(setResume)
  }, [])

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }))

  const toggleSize = (value) => {
    setForm(f => ({
      ...f,
      company_size: f.company_size.includes(value)
        ? f.company_size.filter(v => v !== value)
        : [...f.company_size, value],
    }))
  }

  const handleSave = (e) => {
    e.preventDefault()
    savePreferences({
      ...form,
      poll_interval_hrs: Number(form.poll_interval_hrs),
    }).then(() => setSaved(true))
  }

  const handleResumeUpload = (e) => {
    const file = e.target.files[0]
    if (file) uploadResume(file).then(setResume)
  }

  return (
    <div>
      <h2 style={{ color: 'var(--text-primary)', marginBottom: 4 }}>Preferences</h2>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
        Configure your job search criteria
      </p>

      <form onSubmit={handleSave}>
        <div className="form-section">
          <div className="form-section-title">Search Criteria</div>

          <div className="field" style={{ marginBottom: 16 }}>
            <label htmlFor="job_titles">Job Titles</label>
            <TagInput
              id="job_titles"
              values={form.job_titles}
              onChange={(vals) => setForm(f => ({ ...f, job_titles: vals }))}
              placeholder="Add title, press Enter"
            />
            <span className="field-hint">Press Enter or comma to add · click × to remove</span>
          </div>

          <div className="form-row">
            <div className="field">
              <label htmlFor="location">Location</label>
              <input
                id="location"
                className="input"
                value={form.location}
                onChange={set('location')}
              />
            </div>
            <div className="field">
              <label htmlFor="remote_hybrid">Arrangement</label>
              <select
                id="remote_hybrid"
                className="select"
                value={form.remote_hybrid}
                onChange={set('remote_hybrid')}
              >
                <option value="any">Any</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="field">
              <label htmlFor="experience_level">Experience Level</label>
              <select
                id="experience_level"
                className="select"
                value={form.experience_level}
                onChange={set('experience_level')}
              >
                <option value="">Select level…</option>
                {EXPERIENCE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="domain">Domain</label>
              <select
                id="domain"
                className="select"
                value={form.domain}
                onChange={set('domain')}
              >
                <option value="">Select domain…</option>
                {DOMAIN_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="field" style={{ marginBottom: 16 }}>
            <label>Company Size</label>
            <div className="checkbox-group">
              {COMPANY_SIZE_OPTIONS.map(o => (
                <label key={o.value} className="checkbox-pill">
                  <input
                    type="checkbox"
                    checked={form.company_size.includes(o.value)}
                    onChange={() => toggleSize(o.value)}
                  />
                  {o.label}
                </label>
              ))}
            </div>
          </div>

          <div className="field">
            <label htmlFor="poll_interval_hrs">Poll Interval (hours)</label>
            <input
              id="poll_interval_hrs"
              type="number"
              min="1"
              className="input"
              style={{ width: 72 }}
              value={form.poll_interval_hrs}
              onChange={set('poll_interval_hrs')}
            />
          </div>
        </div>

        <button type="submit" className="btn-primary">Save Preferences</button>
        {saved && (
          <span style={{ color: 'var(--accent)', marginLeft: 12, fontSize: 13 }}>Saved!</span>
        )}
      </form>

      <div className="form-section" style={{ marginTop: 24 }}>
        <div className="form-section-title">Resume</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {resume && (
            <div className="input" style={{ flex: 1 }}>📄 {resume.filename}</div>
          )}
          <label>
            <input
              type="file"
              accept=".pdf,.docx"
              style={{ display: 'none' }}
              onChange={handleResumeUpload}
            />
            <span className="btn-secondary" style={{ cursor: 'pointer' }}>
              {resume ? 'Replace' : 'Upload Resume'}
            </span>
          </label>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Run full test suite**

```bash
docker compose exec frontend npm run test:run
```

Expected: all 25 tests pass (18 existing + 7 new TagInput tests). The `Preferences.test.jsx` label query `getByLabelText(/job titles/i)` still resolves because `TagInput` receives `id="job_titles"` and `Preferences.jsx` keeps `<label htmlFor="job_titles">`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Form.css frontend/src/pages/Preferences.jsx
git commit -m "feat(ui): restyle Preferences with TagInput, dropdowns, checkboxes"
```
