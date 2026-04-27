# Wine Tracker — Claude Project Guide

Personal wine collection tracker to replace Vivino. Flask app with multi-user support.
Steve's live instance: deployed on Railway. Local dev uses SQLite; production uses PostgreSQL.

Live site: https://stevenwinecellar.up.railway.app/
GitHub repo: https://github.com/stevenslywka/wine-tracker

---

## Codex Startup Notes

Project root:
```text
C:\Users\steve\wine-tracker
```

At the start of a new chat, inspect the current files and run `git status --short` before editing. Do not overwrite existing local changes. As of the mobile UI push, this local folder may still show `templates/index.html` as modified because Codex sometimes cannot write to `.git`; GitHub `main` is the source of truth if local status disagrees.

Reusable new-chat prompt:
```text
NEW_CHAT_PROMPT.md
```

Recent mobile UI work pushed to GitHub:
- Mobile Cards view redesigned.
- Compact/List view redesigned.
- Dynamic compact card heights fixed.
- Wine type sash adjusted.
- Available/drank/not-shipped icons updated.
- Storage/status mobile behavior improved.
- Mobile cellar header now centers `🍷 Steven's wine cellar`; hamburger opens the menu and the search icon reveals the search bar.
- Mobile Filter and sort sheet added, with tighter spacing and a Nestig-inspired trigger.
- Mobile quick carousel added: Location, Type, Origin, Sticker. It should appear once only, ending with Sticker.
- Origin carousel chips are: USA, France, Italy, and Earth emoji `Other`. `Other` filters origins outside USA/France/Italy; USA also includes common stored US origins like California, Oregon, Washington, and New York.
- Mobile Cards/List toggle is on the same row as Filter and sort; wine counter sits below.
- "Add" renamed to "Add Wine"; "all in collection" renamed to "Available".
- Latest pushed commits include:
  - `8f80a27` (`Refine mobile carousel and filter controls`)
  - `7556545` (`Remove duplicate mobile carousel groups`)
  - `deaa4e9` (`Add other origin mobile filter`)

Session preference:
- Do not touch the mobile card layout or compact/list wine row layout unless Steve explicitly asks. Top controls, filters, and header are okay to adjust when requested.

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python / Flask |
| Database | SQLite (local) / PostgreSQL (Railway) |
| Frontend | Jinja2 templates, Bootstrap 5, vanilla JS |
| Image storage | Cloudinary |
| AI features | Anthropic Claude API (receipt scan, label scan, wine rec, drinking window) |
| Deployment | Railway (auto-deploys from GitHub `main` branch) |

---

## Key Files

| File | Purpose |
|---|---|
| `app.py` | All Flask routes and business logic |
| `db.py` | DB connection + `migrate()` — runs on every startup |
| `templates/index.html` | Main cellar view (table, filters, inline editing, popups) |
| `templates/settings_locations.html` | User storage location management |
| `enrich_wines.py` | Auto-extract varietal/region/origin from wine name |
| `fetch_images.py` | Cloudinary image fetch |
| `fetch_emails.py` / `parse_emails.py` | Gmail receipt parser (imports wines) |
| `requirements.txt` | Python deps |
| `Procfile` | Railway startup: `web: gunicorn app:app` |

---

## Dual-DB Pattern (CRITICAL)

Always use these helpers — never hardcode `?` or `%s`:

```python
from db import get_connection, is_postgres, get_placeholder

conn = get_db()          # returns sqlite3 or psycopg2 connection
p    = ph()              # returns '?' or '%s'
pg   = is_postgres()     # True on Railway, False locally

cur.execute(f"SELECT * FROM wines WHERE id = {p}", (wine_id,))
```

For schema checks in `migrate()`:
```python
# Postgres: use information_schema
cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name='wines' AND column_name='foo'")

# SQLite: use PRAGMA
cur.execute("PRAGMA table_info(wines)")
cols = {r['name'] for r in cur.fetchall()}
```

---

## Schema

### `wines`
```
id, wine_name, vintage, varietal, region, origin (geographic, e.g. "California"),
wine_type, size_ml, unit_price, retail_price, total_price, quantity,
retailer, order_date, status, storage_location (physical, e.g. "Cellar"),
color_code, drinking_window, drinking_window_source, notes, image_url, user_id
```

**Status values:** `in_collection` | `not_shipped` | `drank`
**Color codes:** Red | Blue | Orange | Yellow | Green (sticker dots)
**Drinking window format:** `"2024-2030"` (YYYY-YYYY)

### `users`
```
id, username, display_name, password_hash, is_admin, created_at
```

### `user_locations`
```
id, user_id, name, sort_order
```
Each user has their own list of storage locations (default: Cellar, Apt, House).

---

## Schema Changes — Always Use `migrate()`

**Never run raw ALTER TABLE directly.** Add all schema changes to `db.py → migrate()`.
It runs on every app startup and is safe to re-run (uses `IF NOT EXISTS`, `PRAGMA` checks, try/except).

Pattern for adding a column:
```python
if pg:
    cur.execute("ALTER TABLE wines ADD COLUMN IF NOT EXISTS new_col TEXT")
else:
    cur.execute("PRAGMA table_info(wines)")
    if 'new_col' not in {r['name'] for r in cur.fetchall()}:
        cur.execute("ALTER TABLE wines ADD COLUMN new_col TEXT")
```

---

## Routes Reference

### Auth
- `GET/POST /login` — login
- `GET /logout`
- `GET /` — home (user list)
- `GET /cellar/<username>` — main cellar view
- `GET /friends` — friends' cellars

### Inline Edit (all POST, return 204)
- `/wine/<id>/wine_name`
- `/wine/<id>/vintage`
- `/wine/<id>/quantity`
- `/wine/<id>/order_date`
- `/wine/<id>/region`
- `/wine/<id>/origin`
- `/wine/<id>/varietal`
- `/wine/<id>/drinking_window`
- `/wine/<id>/unit_price`
- `/wine/<id>/retail_price`
- `/wine/<id>/retailer`
- `/wine/<id>/rating`
- `/wine/<id>/notes`
- `/wine/<id>/type`
- `/wine/<id>/color`
- `/wine/<id>/size`
- `/wine/<id>/status`
- `/wine/<id>/storage_location`

### Bulk / Other
- `POST /wines/bulk-status` — multi-select status change
- `POST /wine/add` — add single wine
- `POST /wine/add-bulk` — add from receipt scan
- `POST /wine/<id>/delete`
- `POST /wine/scan-receipt` — Claude receipt scan
- `POST /wine/scan-label` — Claude label scan
- `POST /wine/recommend` — Claude wine recommendation
- `POST /wine/enrich-drinking-windows` — Claude batch enrich
- `GET  /export/csv`
- `GET  /analytics` + `GET /cellar/<username>/analytics`
- `GET/POST /settings/locations` — manage user storage locations
- `GET /api/wines` — JSON API

---

## Frontend Conventions

### Table inline editing
All editable cells use class `editable-cell` with data attributes:
```html
<td class="editable-cell"
    data-wine-id="{{ wine.id }}"
    data-field="region"
    data-value="{{ wine.region or '' }}"
    data-input-type="text"   <!-- optional: text/number/date -->
    onclick="event.stopPropagation()">
  <span class="editable-display">{{ wine.region or '—' }}</span>
</td>
```
The JS handler in `index.html` picks these up automatically. No extra JS needed for new text fields.

### Popup pickers (Type, Status, Storage, Size, Color)
These use a fixed-position popup div with class `visible` toggled on/off.
**Key rule:** Close listeners must use **capture-phase mousedown** to bypass `stopPropagation()` on table cells:
```js
document.addEventListener('mousedown', e => {
  if (!e.target.closest('.my-badge') && !e.target.closest('#my-popup')) {
    popup.classList.remove('visible');
  }
}, true);  // <-- true = capture phase, REQUIRED
```

### Location/Status color classes
```css
.loc-color-0  /* Blue   — index % 5 == 0 */
.loc-color-1  /* Red    — index % 5 == 1 */
.loc-color-2  /* Green  — index % 5 == 2 */
.loc-color-3  /* Purple — index % 5 == 3 */
.loc-color-4  /* Orange — index % 5 == 4 */
```

### Scrollable table layout
Body is a CSS flexbox column (`flex: 1; min-height: 0` chain). Only `#tableScroll` scrolls — never add `overflow` to parent elements or the fixed header breaks.

---

## Deferred / Future Work

- **Per-bottle location tracking** — architecture decided (separate `bottles` table), implementation deferred. See memory file `project_wine_tracker_bottles.md`.
- **Mobile column visibility** — some columns could be hidden on small screens
- **Friends permissions** — currently view-only; edit access not yet implemented

---

## Local Dev

```bash
cd C:\Users\steve\wine-tracker
python app.py         # runs on localhost:5000
```
SQLite DB: `wines.db` (local only, not committed)

## Deploy

```bash
git add <files>
git commit -m "description"
git push
# Railway auto-deploys from main branch, ~60s
```

### Codex GitHub Push Workaround

Normal local Git writes may fail in Codex with `.git/index.lock` permission errors. If that happens, do not keep fighting local `.git`; use the GitHub Contents API to update GitHub `main` directly.

Auth token location from the prior-chat `GH_CONFIG_DIR`:
```text
C:\Users\steve\Documents\Codex\codex-auth\gh\hosts.yml
```

Rules:
- Never print or expose the token.
- Read the token from `oauth_token` in `hosts.yml`.
- Use GitHub API repo `stevenslywka/wine-tracker`, branch `main`.
- Railway auto-deploys after GitHub `main` changes.
- Verify the final commit with `GET /repos/stevenslywka/wine-tracker/commits/main`.
- If PowerShell `Invoke-RestMethod` or Git HTTPS fails, use Node/fetch with the same token.

API flow:
1. Get the current file SHA:
   `GET https://api.github.com/repos/stevenslywka/wine-tracker/contents/<path>?ref=main`
2. Base64 encode the updated file contents.
3. Update the file:
   `PUT https://api.github.com/repos/stevenslywka/wine-tracker/contents/<path>`
4. Include JSON fields: `message`, `content`, `sha`, `branch`.
