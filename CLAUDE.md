# Wine Tracker â€” Claude Project Guide

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

At the start of a new chat, inspect the current files and run `git status --short` before editing. Do not overwrite existing local changes.

Codex local Git metadata is unreliable for this repo. `.git/index`, `.git/FETCH_HEAD`, and related files are often locked or stale after GitHub API pushes. Do not spend time trying to make local `git status` clean from inside Codex. Use it only as a rough signal for possible user-created local files, then compare against GitHub `main` when needed. GitHub `main` is the source of truth if local Git disagrees.

Reusable new-chat prompt:
```text
NEW_CHAT_PROMPT.md
```

Latest inventory-lots work pushed to GitHub:
- Stage 1 foundation added `wine_inventory_lots`, `wine_drink_history`, and `wines.location_summary`.
- Existing wines migrate into one current inventory lot each; drank wines have no current lots and keep source/date/price metadata.
- `wines.quantity`, `wines.status`, `wines.storage_location`, `wines.location_summary`, and price/source fields are now cached summaries synced from lots by `db.sync_wine_summary()`.
- `wines.total_price` is cached from available lots by summing `quantity * unit_price` per lot, so mixed-price re-buys do not use one latest price for every bottle.
- New/imported wines create lots through manual Add Wine, receipt/bulk add, batch scan add, and email parsing.
- Location filters/counts and recommendation location filters now query lots.
- Mobile detail page now has a compact Bottle Ledger. Header summarizes total available bottles by location; each location row shows `Location - / left / bought / + / ...` with fast drink/add actions and a subtle edit sheet for move/correct count.
- `Drank one` creates `wine_drink_history`, stores the source location, decrements one available lot from that location, and defaults drink date to today.
- `Drank one` inserts drink history before deleting a final-bottle lot so PostgreSQL foreign keys do not block last-bottle consumption.
- `Correct count` controls are inventory corrections only; they do not create drink history.
- Last-bottle `Correct count` uses the custom confirmation modal and preserves the lot id before closing the modal.
- `Move` requires a real destination different from the source location; if there is no other saved location, the mobile modal disables the action and tells the user to add another location first.
- `Receive` consolidates incoming bottles into an existing matching available lot through `upsert_inventory_lot()` instead of creating duplicate same-location cards.
- The old mobile Qty card was removed; total current bottles now appears in the Bottle Ledger summary.
- Inventory/detail routes include: `POST /wine/<id>/drink-one`, `POST /wine/<id>/lot/<lot_id>/adjust`, `POST /wine/<id>/lot/add-location`, `POST /wine/<id>/add-lot`, `POST /wine/<id>/lot/<lot_id>/move`, `POST /wine/<id>/lot/<lot_id>/receive`, `POST /wine/<id>/location/move`, `POST /wine/<id>/location/correct`, `POST /wine/<id>/drink-history/<history_id>/update`, and `POST /wine/<id>/drink-history/<history_id>/delete`.
- Latest pushed commits include:
  - `233b7be` (`Add inventory lot foundation`)
  - `2fe0b17` (`Preserve wine metadata during inventory sync`)
  - `142a59e` (`Add mobile inventory lot controls`)
  - `76c1de4` (`Clarify mobile inventory controls`)
  - `26c01c5` (`Add move and receive inventory lot routes`)
  - `afac831` (`Redesign mobile inventory UI: per-lot cards, Drink one modal, Move, Receive`)
  - `6d49096` (`Replace last-bottle native confirm with custom modal`)
  - `eb33c35` (`Rework mobile wine detail bottles section`)

Inventory model notes:
- Use lots, not individual bottles. A lot is current inventory for one wine at one location/status/source/date/price.
- Lots only use `in_collection` and `not_shipped`; `drank` is a derived wine summary state and drink history record, not a lot status.
- Do not store `Multiple` in `wines.storage_location`; use primary location there and full display text in `wines.location_summary`.
- Always run lot changes and `sync_wine_summary(conn, wine_id)` in the same transaction.
- Lot routes must verify both wine ownership and that `lot_id` belongs to the URL's `wine_id`.
- For final-bottle drink operations, insert `wine_drink_history` before deleting the source lot, or store a null `lot_id`.
- Do not update incoming lots directly to receive shipments; delete/upsert so received bottles merge with any existing matching available lot.
- `Move` should reject same-location moves on both frontend and backend.
- Detail-page `+ Add` now adds bottles to an existing wine through `/wine/<id>/add-lot`; broader Add Wine re-buy detection is still future work.

Recent mobile UI work pushed to GitHub:
- Mobile Cards view redesigned.
- Compact/List view redesigned.
- Dynamic compact card heights fixed.
- Wine type sash adjusted.
- Available/drank/not-shipped icons updated.
- Storage/status mobile behavior improved.
- Mobile cellar header now centers `ðŸ· Steven's wine cellar`; hamburger opens the menu and the search icon reveals the search bar.
- Mobile Filter and sort sheet added, with tighter spacing and a Nestig-inspired trigger.
- Mobile quick carousel added: Location, Type, Origin, Sticker. It should appear once only, ending with Sticker.
- Origin carousel chips are: USA, France, Italy, and Earth emoji `Other`. `Other` filters origins outside USA/France/Italy; USA also includes common stored US origins like California, Oregon, Washington, and New York.
- Mobile Cards/List toggle is on the same row as Filter and sort; wine counter sits below.
- Mobile Select mode includes bulk Edit: tap `Select`, tap cards or `All`, tap `Edit`, then use inline carousel-style chips/fields for Location, Status, Sticker, Source, or Order Date. These actions post selected IDs to `/wines/bulk-edit`. Location marks selected wines Available and assigns the chosen location. It intentionally does not implement bottle history or quantity-drinking behavior.
- Mobile Batch Scan added in Add Wine: one multi-bottle photo, client-side compression, `/wine/scan-batch-labels` extraction, editable review cards, and `/wine/add-batch-scan` insert. It uses `origin` (not `location`), leaves `image_url` null for group photos, flags likely duplicates, and intentionally does not reuse receipt `/wine/add-bulk`.
- "Add" renamed to "Add Wine"; "all in collection" renamed to "Available".
- Latest pushed commits include:
  - `c8b293e` (`Polish mobile wine detail page UI`)
  - `512e758` (`Refine mobile wine detail bubbles and sticker layout`)
  - `d85d691` (`Center select text in Status and Location quick tiles`)
  - `38f5dfc` (`Fix Order Date label wrapping and date input alignment`)
  - `89d778f` (`Color carousel chips by location and wine type`)

Current mobile UI state as of Apr 28, 2026 (supersedes older mobile bullets below if they conflict):
- Main Cellar mobile carousel order is Location, Type, Origin, Sticker, Status. Status is last, after Sticker.
- Status carousel chips are Available, Not Shipped, Drank. Available is green, Not Shipped is beige, Drank is dark red/burgundy. Active carousel chips keep their normal color; active state only thickens the border/font. Do not restore the old red active background.
- Origin carousel chips are USA, France, Italy, and Earth emoji `Other`. `Other` filters origins outside USA/France/Italy; USA also includes common stored US origins like California, Oregon, Washington, and New York.
- Mobile search has an X clear button and uses 16px font to avoid iOS zoom sticking after focus.
- The old tiny bottom-left result counter is removed. When no filters/search are active, the mobile summary says `Viewing - All Wines`; filtered states show the active view and counts.
- Mobile Select mode is available to edit users from the main cellar mobile toolbar. It is meant for shipment arrivals and batch metadata cleanup. It should not change inventory-history semantics; bulk Edit supports Location, Status, Sticker, Source, and Order Date only.
- Empty mobile results say `No wines yet - tap Add Wine to get started` in white.
- Wine cards without images show a dark `No photo` bottle silhouette placeholder.
- Bottom mobile cellar button says `Need a Wine Rec?`.
- Mobile detail page has a sticky wine-cellar header matching the Main Cellar page: hamburger menu on the left, centered cellar title, and a square trash icon on the right. The trash icon opens the delete confirmation.
- Detail hero shows the editable wine name first, then vintage/sticker. The type word and type sash were removed from the detail hero.
- Detail page wines without images use the same dark `No photo` silhouette.
- Detail page uses a compact `Bottle Ledger` section. The summary shows total available bottles and counts by location; each available location row has `-` to drink one, `+` to add bottles, and `...` for move/correct count. Not-shipped rows show `Receive`. Drink history rows are tappable for edit/delete. Drinking Window placeholder gives `e.g. 2024-2030` style guidance; expected format remains `YYYY-YYYY`.
- Detail notes textarea starts short and auto-grows.
- Detail bottom action bar is Back to Cellar, Previous Wine, Next Wine. Delete is only in the sticky header. Back uses `back_url`, not `history.back()`.
- Previous/Next on detail preserve the filtered Main Cellar list: mobile card clicks pass `list=<filtered ids>` and `back=<current cellar URL>` query params to `GET /wine/<id>`.
- `app.py -> wine_detail()` now passes `cellar_username`, `cellar_display_name`, `back_url`, `prev_wine_url`, and `next_wine_url` in addition to the detail picker lists.
- Delete confirmation text is `Are you sure? This cannot be undone.` and posts to `/wine/<id>/delete` only after confirmation.
- Recent relevant commits include `bd33cd2`, `e47502b`, `3317196`, `9c64bb2`, `5ccb08c`, `cfdf307`, `e50b04b`, `d50c8d8`, and `eb33c35`.

Mobile detail page â€” current state (templates/detail.html):
- Separate page at `GET /wine/<id>`; tapping a card in `templates/index.html` navigates here via `data-detail-url`.
- Do not change the mobile card/list layout in `index.html` unless Steve explicitly asks.
- `app.py -> wine_detail()` passes `user_locations`, `wine_types`, `bottle_sizes`, `sticker_colors`, `inventory_lots`, `available_locations`, `incoming_locations`, `drink_history`, `drank_total`, and `not_shipped_count` into `detail.html`.
- Mobile-only layout in the same template; desktop view is separate and should not be changed unless requested.
- **Hero**: bottle image wrapped in `.mobile-bottle-wrap` with diagonal type sash (same color scheme as card sash). Right side: type Â· vintage kicker with sticker dot, editable wine name textarea, flag+region row, grape+varietal row.
- **Quick strip** (1 tile): Drinking Window only (editable, color-coded hold/ready/soon/overdue). The read-only Location quick tile was removed because location is represented by Bottle Ledger rows.
- **Bottle Ledger**: compact mobile section with a `Bottles - N total - N Apt - N House` style summary. Available location rows show `Location`, `-`, `N left / M bought`, `+`, and `...`. `-` opens the drink-one sheet for that location; `+` opens Add bottles prefilled to that location with optional purchase details; `...` opens move/correct-count controls. Not-shipped rows show `Receive`.
- **Main body**: Source, Sticker, Rating, then full-width Notes. The old Qty card was removed. Sticker picker shows 6 dots in 2 rows of 3: Green/Yellow/Orange then Red/Blue/None. Rating shows as a large gold number (tap to edit); no star.
- **Drink history**: lives inside Bottle Ledger. Rows show date, quantity, and source location; tapping a row opens edit controls for date/location/rating/notes plus delete. Deleting a history row restores the bottle to the selected/source location.
- **Collapsed sections** (`<details>`): "Wine details" and "Purchase", each with a rotating â–¾ chevron. All rows have emoji icon prefixes (ðŸ· ðŸ‡ ðŸ“ ðŸŒ ðŸ¾ ðŸ—“ï¸ ðŸ’³ ðŸ·ï¸ ðŸ’°). Label column is 100px wide so "ðŸ—“ï¸ Order date" fits on one line. Date input is left-aligned with `padding-left: 4px`.
- **Bottom action bar**: â† Back, â˜… Rate, âœï¸ Notes, âœ“ Drank.
- Naming: use `Location` (not `Storage`), `Source` (not `Retailer`).

Mobile carousel (templates/index.html):
- Location carousel chips use `loc-color-*` classes matching the card badge colors (Apt=loc-color-0 blue, House=loc-color-1 red per current sort_order). Inactive state only; active state keeps the standard gold highlight.
- Wine type carousel chips (Red/White/Rose) use `.type-Red`, `.type-White`, `.type-Rose` classes with sash colors. Inactive state only.

Local file note:
- Earlier in this thread, local `templates/index.html` was accidentally 0 bytes. It was restored locally from GitHub `main` and is no longer blank.
- Because local git history may lag GitHub `main`, `git status` may still show `templates/index.html`, `app.py`, `templates/detail.html`, or docs as modified after API pushes. Do not blindly revert these. Compare with GitHub `main` if unsure.
- As of Apr 28, 2026, `templates/index.html`, `templates/detail.html`, and `NEW_CHAT_PROMPT.md` matched GitHub `main` exactly when checked by SHA. `CLAUDE.md` and `app.py` had the same line-by-line content as GitHub but differed by line endings. Local `origin/main` may be stale because Codex cannot write `.git/FETCH_HEAD`.
- Steve created a local virtual environment at `.venv` from normal PowerShell and installed `requirements.txt`; `.\.venv\Scripts\python.exe app.py` successfully starts the Flask dev server at `http://127.0.0.1:5000`.

Session preference:
- Do not touch the mobile card layout or compact/list wine row layout in `index.html` unless Steve explicitly asks.
- Desktop views in both `index.html` and `detail.html` should not be changed unless requested.

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
| `db.py` | DB connection + `migrate()` â€” runs on every startup |
| `templates/index.html` | Main cellar view (table, filters, inline editing, popups) |
| `templates/settings_locations.html` | User storage location management |
| `enrich_wines.py` | Auto-extract varietal/region/origin from wine name |
| `fetch_images.py` | Cloudinary image fetch |
| `fetch_emails.py` / `parse_emails.py` | Gmail receipt parser (imports wines) |
| `requirements.txt` | Python deps |
| `Procfile` | Railway startup: `web: gunicorn app:app` |

---

## Dual-DB Pattern (CRITICAL)

Always use these helpers â€” never hardcode `?` or `%s`:

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
location_summary, color_code, drinking_window, drinking_window_source, notes, image_url, user_id
```

**Status values:** `in_collection` | `not_shipped` | `drank`
**Color codes:** Red | Blue | Orange | Yellow | Green (sticker dots)
**Drinking window format:** `"2024-2030"` (YYYY-YYYY)

After the inventory-lots migration, `wines.quantity`, `wines.status`, `wines.storage_location`, and `wines.location_summary` are cached summaries. Current inventory truth lives in `wine_inventory_lots`.

### `wine_inventory_lots`
```
id, wine_id, quantity, status, storage_location, retailer, order_date,
unit_price, notes, created_at, updated_at
```
**Lot status values:** `in_collection` | `not_shipped`

Lots are current inventory only. When bottles are consumed, decrement/delete lots and write `wine_drink_history`.

### `wine_drink_history`
```
id, wine_id, lot_id, quantity, storage_location, drank_date, rating, notes, created_at
```
This stores consumption history. `storage_location` snapshots where the bottle was consumed from, so history remains readable/editable even if lots are merged or deleted. `lot_id` can become null if the source lot is later deleted.

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

## Schema Changes â€” Always Use `migrate()`

**Never run raw ALTER TABLE directly.** Add all schema changes to `db.py â†’ migrate()`.
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
- `GET/POST /login` â€” login
- `GET /logout`
- `GET /` â€” home (user list)
- `GET /cellar/<username>` â€” main cellar view
- `GET /friends` â€” friends' cellars

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

Compatibility note: mobile inventory counts should use the Bottle Ledger controls. Older whole-wine quantity/status/location routes still exist and may collapse lots as compatibility behavior.

### Bulk / Other
- `POST /wines/bulk-status` â€” multi-select status change
- `POST /wines/bulk-edit` â€” mobile Select mode bulk updates for status, location, sticker, source, and order date
- `POST /wine/<id>/drink-one` â€” decrement one available lot and write drink history; returns location choices if multiple lots exist
- `POST /wine/<id>/lot/<lot_id>/adjust` â€” inventory correction only, adjusts one lot by +/- 1; does not write drink history
- `POST /wine/<id>/lot/add-location` â€” add current inventory to a saved location
- `POST /wine/<id>/add-lot` â€” backend endpoint for future re-buy flow to add bottles to an existing wine
- `POST /wine/<id>/lot/<lot_id>/move` â€” move qty bottles from a source in_collection lot to a destination user location; upserts destination lot, decrements/deletes source; verifies ownership and valid user location
- `POST /wine/<id>/lot/<lot_id>/receive` â€” convert a not_shipped lot to in_collection at a chosen storage location; verifies ownership and valid user location
- `POST /wine/add` â€” add single wine
- `POST /wine/add-bulk` â€” add from receipt scan
- `POST /wine/scan-batch-labels` â€” AI scan of one multi-bottle photo, returns editable batch candidates
- `POST /wine/add-batch-scan` â€” add selected/reviewed batch-scan candidates
- `POST /wine/<id>/delete`
- `POST /wine/scan-receipt` â€” Claude receipt scan
- `POST /wine/scan-label` â€” Claude label scan
- `POST /wine/recommend` â€” Claude wine recommendation
- `POST /wine/enrich-drinking-windows` â€” Claude batch enrich
- `GET  /export/csv`
- `GET  /analytics` + `GET /cellar/<username>/analytics`
- `GET/POST /settings/locations` â€” manage user storage locations
- `GET /api/wines` â€” JSON API

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
  <span class="editable-display">{{ wine.region or 'â€”' }}</span>
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
.loc-color-0  /* Blue   â€” index % 5 == 0 */
.loc-color-1  /* Red    â€” index % 5 == 1 */
.loc-color-2  /* Green  â€” index % 5 == 2 */
.loc-color-3  /* Purple â€” index % 5 == 3 */
.loc-color-4  /* Orange â€” index % 5 == 4 */
```

### Scrollable table layout
Body is a CSS flexbox column (`flex: 1; min-height: 0` chain). Only `#tableScroll` scrolls â€” never add `overflow` to parent elements or the fixed header breaks.

---

## Deferred / Future Work

- **Per-bottle location tracking** â€” architecture decided (separate `bottles` table), implementation deferred. See memory file `project_wine_tracker_bottles.md`.
- **Mobile column visibility** â€” some columns could be hidden on small screens
- **Friends permissions** â€” currently view-only; edit access not yet implemented

---

Inventory follow-ups to prioritize next:
- Re-buy detection in Add Wine, using `POST /wine/<id>/add-lot`.
- Expanded drink history when recent rows are not enough.
- Wine family / vertical grouping across vintages.
- Keep the current lots-only decision; do not add individual bottle tracking unless Steve changes direction.

## Markdown Update Workflow

Hard rule for Codex: do not use repeated apply_patch attempts against prose in CLAUDE.md, NEW_CHAT_PROMPT.md, DETAIL_PAGE_REWORK_PLAN.md, or other project markdown notes.

Use scripted line/prefix replacements only:
- Read target lines as JSON-escaped strings if needed.
- Replace by stable line prefix or section heading, not by full paragraphs containing emoji, smart punctuation, or mojibake.
- Make scripts idempotent: if old text is gone, check whether the new text is already present.
- Verify with `rg`.
- Push only the markdown files that changed.

This should keep doc updates quick and avoid wasting tokens on patch retries.

## Local Dev

```bash
cd C:\Users\steve\wine-tracker
.\.venv\Scripts\python.exe app.py
# runs on http://127.0.0.1:5000
```
SQLite DB: `wines.db` (local only, not committed)

If `.venv` ever needs to be recreated, run from normal Windows PowerShell (not inside Codex sandbox if pip temp permissions fail):
```powershell
cd C:\Users\steve\wine-tracker
Remove-Item -Recurse -Force .venv,.pip-tmp -ErrorAction SilentlyContinue
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```
`.venv/` and `.pip-tmp/` are ignored in `.gitignore`.

## Deploy

```bash
git add <files>
git commit -m "description"
git push
# Railway auto-deploys from main branch, ~60s
```

### Codex GitHub Push Workaround

Normal local Git writes may fail in Codex with `.git/index.lock` or `.git/FETCH_HEAD` permission errors. If that happens, do not keep fighting local `.git`; use the GitHub Contents API to update GitHub `main` directly. Local Git may report misleading `ahead/behind` state when `origin/main` is stale; verify against GitHub `main` before reverting or overwriting files. Do not try repeated local Git cleanup/reset attempts unless Steve explicitly asks for local Git repair.

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
