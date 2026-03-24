# Frontend UI Redesign — Design Spec

**Date:** 2026-03-24
**Scope:** Visual polish and Preferences page field improvements across the React frontend.

---

## Goals

1. Apply a consistent warm-neutral CSS theme across all pages.
2. Replace the flat top-nav with a left sidebar.
3. Upgrade the Preferences page fields: tag input for Job Titles, dropdowns for Experience Level and Domain, checkbox group for Company Size.

---

## 1. CSS Theme — Warm Neutral

The existing `src/App.css` file is repurposed as the theme file — its Vite-starter content is replaced entirely with the tokens and resets below. `main.jsx` already imports `./App.css`, so no import change is needed.

### Palette

| Token | Light value | Purpose |
|---|---|---|
| `--bg` | `#faf9f7` | Page background |
| `--surface` | `#ffffff` | Card / panel background |
| `--border` | `#e8e4de` | All borders |
| `--border-input` | `#d6d3cf` | Input borders (slightly darker) |
| `--text-primary` | `#1c1917` | Headings, values |
| `--text-secondary` | `#57534e` | Labels |
| `--text-muted` | `#a8a29e` | Hints, metadata |
| `--accent` | `#d97706` | Amber — active state, primary button |
| `--accent-light` | `#fef9ec` | Accent background tint |
| `--accent-border` | `#fcd34d` | Accent border (tags, active nav) |
| `--tag-text` | `#92400e` | Text on amber tags |
| `--radius-sm` | `6px` | Inputs, small elements |
| `--radius-md` | `8px` | Cards |
| `--radius-lg` | `10px` | Panels |

No dark-mode variant in this phase. The existing `index.css` dark-mode block is left in place (it only affects variables that aren't used by the new components).

### Global resets (in `App.css`)

```css
body { background: var(--bg); color: var(--text-primary); font-family: system-ui, 'Segoe UI', Roboto, sans-serif; margin: 0; }
#root { display: flex; flex-direction: column; min-height: 100svh; }
```

---

## 2. Layout — Left Sidebar + App Shell

### File: `src/components/AppShell.jsx`

`App.jsx` currently renders a `<nav>` inline + `<main>`. Replace this with an `<AppShell>` component that renders the sidebar and the page content side by side.

**Structure:**
```
<div class="app-shell">          ← flex row, full height
  <Sidebar />                    ← fixed-width left panel
  <main class="app-main">        ← flex:1, scrollable
    {children}
  </main>
</div>
```

**Sidebar contents:**
- Brand block: "JobApplier" wordmark + "Agent" subtitle.
- Nav links: Dashboard, Preferences, Applications, Outreach, Settings.
- Active link: amber right-border (`3px solid var(--accent)`), amber background tint (`var(--accent-light)`), amber text.
- Inactive link: muted text, no border.
- Width: `172px`, fixed.

**`app-shell` CSS:** `display: flex; height: 100svh; overflow: hidden;`
**`app-main` CSS:** `flex: 1; overflow-y: auto; padding: 24px 28px;`

### File: `src/components/AppShell.css`

Contains `.app-shell`, `.sidebar`, `.sidebar-brand`, `.sidebar-nav`, `.sidebar-link`, `.sidebar-link.active`, `.app-main`.

### File: `src/App.jsx`

Wraps `<Routes>` inside `<AppShell>`. Removes the existing inline `<nav>` and `<main style={{padding:24}}>`.

---

## 3. Shared Form Styles

### File: `src/components/Form.css`

Provides reusable classes consumed by Preferences (and available to other pages):

| Class | Purpose |
|---|---|
| `.form-section` | White card with border, border-radius, padding |
| `.form-section-title` | Small-caps section label |
| `.form-row` | Flex row with gap for side-by-side fields |
| `.field` | Label + input stacked, flex:1 |
| `.field label` | 12px, semi-bold, `--text-secondary`, margin-bottom 4px |
| `.input` | Styled text input: `--bg` fill, `--border-input` border, `--radius-sm` |
| `.select` | Styled select: same as `.input` |
| `.btn-primary` | Amber fill, white text, `--radius-sm`, 600 weight |
| `.btn-secondary` | White fill, `--border` border, muted text |

---

## 4. Preferences Page Changes

### 4a. Job Titles — Tag Input

**Component:** `src/components/TagInput.jsx`

A controlled component with no external dependencies.

**Props:**
```js
TagInput({ values: string[], onChange: (values: string[]) => void, placeholder?: string })
```

**Behaviour:**
- Renders existing values as amber pill tags inside a styled container.
- Each tag has an `×` button; clicking it removes that value from the array.
- An inline `<input>` at the end of the tag list accepts new text.
- On `Enter` or `,` keydown: trim the input, add it to values if non-empty and not a duplicate, clear the input.
- On `Backspace` when input is empty: remove the last tag.
- The outer container gets a focus ring when the inner input is focused.

**CSS:** `src/components/TagInput.css` — `.tag-input-container`, `.tag`, `.tag-remove`, `.tag-input`.

**Preferences integration:**
- `form.job_titles` initial state changes from `''` to `[]` (`useState` default updated).
- `handleSave` no longer needs `.split(',')` for job_titles — it sends the array directly.
- The `useEffect` that loads preferences maps `pref.job_titles` directly (already an array from the API).
- `TagInput`'s inner `<input>` carries `id="job_titles"` so `<label htmlFor="job_titles">` still resolves — `Preferences.test.jsx` label query is unaffected.

### 4b. Experience Level — Dropdown

Replace `<input>` with `<select>`. Options (value = label):

| Value | Label |
|---|---|
| `associate` | Associate |
| `mid-level` | Mid-level |
| `senior-level` | Senior-level |
| `executive-level` | Executive-level |

First option is an empty placeholder: `<option value="">Select level…</option>`, consistent with Domain.

### 4c. Domain — Dropdown

Replace `<input>` with `<select>`. First option is an empty placeholder: `<option value="">Select domain…</option>`.

| Value | Label |
|---|---|
| `backend` | Backend Engineering |
| `frontend` | Frontend Engineering |
| `full-stack` | Full Stack |
| `data-science` | Data Science |
| `ml-ai` | ML / AI |
| `devops-infra` | DevOps / Infrastructure |
| `mobile` | Mobile (iOS/Android) |
| `security` | Security |
| `data-engineering` | Data Engineering |
| `sre-platform` | SRE / Platform |
| `product-management` | Product Management |
| `design-ux` | Design / UX |
| `qa-testing` | QA / Testing |
| `game-development` | Game Development |
| `blockchain-web3` | Blockchain / Web3 |
| `embedded-systems` | Embedded Systems |

### 4d. Company Size — Checkbox Group

**Component:** inline in `Preferences.jsx` (no separate component needed — it's a single-use list of 6 items).

`form.company_size` initial state changes from `''` to `[]` (`useState` default updated). It is no longer a comma-separated string.

Available options (value / label):

| Value | Label |
|---|---|
| `<50` | < 50 |
| `50-200` | 50 – 200 |
| `200-500` | 200 – 500 |
| `500-1000` | 500 – 1,000 |
| `1000-5000` | 1,000 – 5,000 |
| `5000+` | 5,000+ |

Rendered as pill-style `<label>` elements containing a hidden `<input type="checkbox">`. Selected pills use amber tint + amber border. Unselected pills use `--surface` fill + `--border` border.

`handleSave` sends `form.company_size` directly (already a `string[]`).

---

## 5. Files Changed

| File | Action |
|---|---|
| `src/App.css` | Replace Vite-starter content with CSS tokens + global resets (theme file) |
| `src/index.css` | Keep as-is (design tokens for remaining Vite defaults) |
| `src/App.jsx` | Wrap routes in `<AppShell>` |
| `src/components/AppShell.jsx` | New — sidebar + main layout |
| `src/components/AppShell.css` | New — shell/sidebar styles |
| `src/components/TagInput.jsx` | New — tag input component |
| `src/components/TagInput.css` | New — tag input styles |
| `src/components/Form.css` | New — shared form element styles |
| `src/pages/Preferences.jsx` | Modify — use TagInput, dropdowns, checkbox group; import `../components/Form.css` |

Other pages (Dashboard, Applications, Outreach, Settings) get the improved layout automatically from `AppShell` and the ambient CSS. Their internal styles (inline `style={}` props) are **not** changed in this phase — only the shell and Preferences are explicitly restyled.

---

## 6. Testing

Existing tests are unaffected by CSS changes. The `TagInput` component requires a new test:

**`src/components/TagInput.test.jsx`:**
- Renders existing values as tags.
- Enter key adds a new tag and clears the input.
- Comma key adds a new tag.
- Clicking `×` removes a tag.
- Backspace on empty input removes last tag.
- Duplicate values are not added.

`Preferences.test.jsx` uses `getByLabelText(/job titles/i)` to find the field. This continues to work because `TagInput` renders its inner `<input id="job_titles">` and `Preferences.jsx` keeps `<label htmlFor="job_titles">` — no changes needed to the test.

---

## 7. Out of Scope

- Dark mode adaptation for the new theme.
- Restyling Dashboard, Applications, Outreach, Settings page internals (inline styles left as-is).
- Any backend changes.
- Accessibility audit beyond semantic HTML.
