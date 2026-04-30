# Drink History UI Redesign

Spec written April 30, 2026. To be implemented in `templates/detail.html`.

## Goal

Make the Drink History section feel like a polished tasting journal rather than
a plain log list. It should be compact and unobtrusive — not the focal point of
the page — but satisfying to browse when expanded.

## Scope

CSS and HTML/Jinja changes in `templates/detail.html`, mobile view only
(`@media (max-width: 767px)`).

Do not change:

- Desktop view (`.desktop-detail-page`)
- Backend routes or Python behavior
- JavaScript event handler logic (only update selectors/IDs if the markup changes)
- The Bottles panel above Drink History
- The Cellar, Wine Details, or Purchase sections below

---

## Section Header — Collapsed by Default

The `Drink History · N total` header row becomes a collapse/expand toggle,
consistent with how the Wine Details and Purchase sections work further down
the page.

- Default state: **collapsed** (rows hidden).
- The header row gets a right-side chevron (`›`) that rotates 90° when expanded.
- Clicking anywhere on the header row toggles the section.
- When there is no drink history, the header reads `Drink History · none` (or
  `Drink History · 0`) and the toggle does nothing / the expanded area shows
  the existing empty state message.
- The count (`N total`) stays in the header at all times so the user can see
  how many drinks are logged without expanding.

---

## Expanded State — One Row Per Drink

Each drink entry occupies exactly one line. No second line, no wrapping.

### Row layout (three zones, full width)

```
[date]          [● location name]          [rating]  [notes icon]  [›]
```

**Left — Date**

- Format: `m/d/yy` (no leading zeros). Examples: `4/12/25`, `11/3/24`.
- If quantity drank was more than 1, append `·×N` after the date.
  Example: `4/12/25 ·×2`.
- Color: `var(--mobile-muted)`, small font (~0.80rem).

**Middle — Location**

- A colored dot using the existing `loc-dot-*` / `loc-color-*` palette,
  matched to the location name the same way the Bottles panel does it.
- Location name text in `var(--mobile-muted)` at ~0.80rem.
- This zone grows to fill available space (`flex: 1`, truncate with ellipsis
  if needed).

**Right — Rating, Notes icon, Chevron**

- Rating: if a rating exists, show the number (e.g., `4.5`) in
  `var(--mobile-accent)` (warm amber), small font, no label. If no rating,
  this space is simply empty — do not show a dash or placeholder.
- Notes icon: if `drink.notes` is non-empty, show a small speech-bubble or
  notepad SVG icon (~12px, `var(--mobile-muted)`). Hidden when no notes.
- Chevron `›` in `var(--mobile-muted)`, same as existing history rows.
- Right zone items sit inline with a small gap between them.

### Row tap behavior

Tapping a row opens the edit bottom sheet (see below). Existing `data-*`
attributes and the `openHistoryEditModal` JS function should be preserved;
only the visual markup of the button interior changes.

### "View all" button

Keep the existing `showAllHistory` / `historyExtra` expand-more mechanic for
when there are more than 4 entries. The button label and behavior stay the same.

---

## Edit Sheet — Bottom Sheet Style

Replace the current centered dialog (`delete-confirm-backdrop` /
`delete-confirm-dialog`) with a bottom sheet that slides up from the bottom,
consistent with the Drink and Manage sheets already on the page.

### Sheet structure

- Dark overlay backdrop covering the full screen.
- Sheet panel anchored to the bottom: rounded top corners, dark background
  (`#1a1410` or similar), `max-height: 85vh`, scrollable interior if needed.
- A short drag handle bar at the top center (decorative, `4px × 32px`, muted).

### Sheet title

Use the date + location from the tapped row as the contextual title.
Example: `"4/12/25 · Wine Rack"` — same `m/d/yy` format as the row.
Not the generic "Edit drink history".

### Fields (stacked, same order)

1. **Date** — date input, same styling as existing Drink sheet date field.
2. **Location** — select dropdown, same styling as existing fields.
3. **Rating** — number input, `min=0 max=5 step=0.5 inputmode=decimal`.
   Keep as a number input (half-points are used). Same styling as other inputs.
4. **Notes** — textarea, 2 rows.

### Actions

- **Save** button: green pill style, same as existing Save in Drink sheet.
- **Delete** button: muted red/danger style, same as existing Delete.
- **Cancel** link/button: full-width, muted, at the very bottom — same as
  existing Drink/Manage "Done" or cancel buttons.

### Animation

Slide up on open (`transform: translateY(100%) → translateY(0)`), slide down
on close. Match the transition timing already used for other sheets on the page.

---

## Location Dot Color Mapping

Use the same logic as the Bottles panel to assign `loc-dot-*` colors from
the location name. If the logic is currently inline in the Bottles panel
template loop, replicate the same pattern for history rows.

---

## Date Formatting Helper

The Jinja template currently outputs `drink.drank_date` as an ISO string
(`YYYY-MM-DD`). Add a Jinja filter or inline expression to reformat it as
`m/d/yy` before rendering. Example approach in the template:

```jinja
{% set parts = drink.drank_date.split('-') %}
{{ parts[1]|int }}/{{ parts[2]|int }}/{{ parts[0][2:] }}
```

Apply this same format in the edit sheet title.

---

## Do Not Change

- Desktop layout
- All `data-*` attributes on `.history-row` buttons
- `openHistoryEditModal`, `closeHistoryEditModal`, save/delete JS handlers
- Backend routes: `/drink-history/<id>/update` and `/drink-history/<id>/delete`
- The Bottles panel, Cellar section, Wine Details, Purchase sections
- `AGENTS.md` or `NEW_CHAT_PROMPT.md`

---

## Verification

After implementing, run:

```powershell
cd C:\Users\steve\wine-tracker
& 'C:\Users\steve\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\verify_detail.py
```

Then start the local dev server and check the mobile detail page in a browser:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open `http://127.0.0.1:5000` on a mobile viewport. Verify:

- Drink History section is collapsed by default.
- Clicking the header expands / collapses the rows.
- Each row is one line: date, location dot + name, optional rating, optional
  notes icon, chevron.
- Tapping a row opens the bottom sheet sliding up from the bottom.
- Sheet title shows the date and location in `m/d/yy` format.
- Save and Delete work (page reloads with correct state).
- Cancel closes the sheet without changes.
- "View all N ›" button works when more than 4 entries exist.
