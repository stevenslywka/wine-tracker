# Wine Tracker - Codex Project Guide

Personal Flask wine cellar app replacing Vivino. Multi-user. Local dev uses SQLite; production uses PostgreSQL on Railway.

- Project root: `C:\Users\steve\wine-tracker`
- Live site: `https://stevenwinecellar.up.railway.app/`
- GitHub: `https://github.com/stevenslywka/wine-tracker`
- Railway deploys automatically from GitHub `main`
- Latest production work noted in this guide: mobile wine detail Cellar polish (Drinking Window moved into the Cellar grid; add-bottle status wording now Available/Not shipped), pushed to GitHub `main` as `d219d2a3daa65a8203e8cbe7689b4618d149a30b`.

## Current Truth

Trust this section first when older notes or local Git disagree.

- Current inventory lives in `wine_inventory_lots`; do not add individual bottle tracking unless Steve explicitly changes direction.
- `wines.quantity`, `wines.status`, `wines.storage_location`, `wines.location_summary`, source/date/price fields, and `wines.total_price` are cached summaries synced by `db.sync_wine_summary()`.
- Lots use only `in_collection` and `not_shipped`. `drank` is a derived wine summary state plus drink history, not a lot status.
- Drink history lives in `wine_drink_history`; `storage_location` snapshots where the bottle was consumed from, so history remains readable/editable even if lots are merged or deleted.
- Mobile Wine Detail uses a compact `Bottles` stock-control panel: dotted location summary, two-column location stock cards with top-right manage (`...`) and a `- / count / +` stepper row, incoming `Receive`, and tappable Drink History rows for edit/delete.
- Detail-page `+ Add` adds bottles to an existing wine through `/wine/<id>/add-lot`; broader Add Wine re-buy detection is still future work.
- Main Cellar mobile Cards/List and desktop views are separate work areas. Do not change them unless requested.

## Startup Workflow

At the start of a new chat:

1. Read `AGENTS.md` and `NEW_CHAT_PROMPT.md`.
2. Run `git status --short` as a rough dirty-worktree signal.
3. Inspect current files before suggesting or editing.
4. Do not overwrite existing local changes.

Local Git metadata can be stale or locked after GitHub API pushes. Use local Git as a warning system, not final truth. If local Git disagrees with GitHub `main`, compare against GitHub `main` before reverting or overwriting anything.

## Do Not Touch Unless Asked

- `templates/index.html` mobile card layout and compact/list row layout.
- Desktop views in `templates/index.html` and `templates/detail.html`.
- Inventory model semantics: lots, not individual bottles.
- Old whole-wine quantity/status/location routes, except for compatibility fixes.
- Unrelated local changes in files like `parse_emails.py`.

## Current Mobile Detail Layout

File: `templates/detail.html`; route: `GET /wine/<id>` from `app.py -> wine_detail()`.

- Sticky mobile header: menu left, centered cellar title, trash icon right.
- Hero: image/no-photo placeholder, editable name, vintage/sticker, region/origin, varietal.
- Bottles panel: header row has "Bottles" label and `+ Add` button (id `openAddBottleSheet`); `N total` summary with colored location dots (9px); two-column location stock cards with top-right pencil edit icon and a `- / count / +` stepper row; not-shipped lots show an incoming `Receive` strip. When inventory is completely empty, a zero-state CTA is shown instead of cards.
- `-` opens Drink one for that location with optional rating/notes/date.
- `+` opens Add bottles, prefilled to that location, with quantity stepper, `Available` / `Not shipped` status labels, and optional purchase details.
- Pencil icon (SVG) opens a Manage sheet with separate Move bottles and Correct count sections; corrections do not create drink history.
- Drink History shows first 4 rows; a "View all N ›" button reveals the rest inline.
- Drink History rows show date, quantity, and source location; tapping opens edit/delete. Deleting restores the bottle to the selected/source location.
- Cellar section: Source, Sticker, Rating, Drinking Window, then full-width Notes.
- Collapsed sections: Wine details and Purchase.
- Bottom bar: Back to Cellar, Previous Wine, Next Wine.

## Inventory Rules

- Always run lot changes and `sync_wine_summary(conn, wine_id)` in the same transaction.
- Lot routes must verify ownership and that `lot_id` belongs to the URL `wine_id`.
- For final-bottle drink operations, insert `wine_drink_history` before deleting the source lot.
- `Correct count` is an inventory correction only and must not create drink history.
- `Move` must reject same-location moves on frontend and backend.
- `Receive` should delete/upsert so received bottles merge into an existing matching available lot.
- Do not store `Multiple` in `wines.storage_location`; use primary location there and full display text in `wines.location_summary`.

## Schema Summary

### `wines`

`id, wine_name, vintage, varietal, region, origin, wine_type, size_ml, unit_price, retail_price, total_price, quantity, retailer, order_date, status, storage_location, location_summary, color_code, drinking_window, drinking_window_source, notes, image_url, user_id`

Status values: `in_collection`, `not_shipped`, `drank`.

### `wine_inventory_lots`

`id, wine_id, quantity, status, storage_location, retailer, order_date, unit_price, notes, created_at, updated_at`

Lot status values: `in_collection`, `not_shipped`.

### `wine_drink_history`

`id, wine_id, lot_id, quantity, storage_location, drank_date, rating, notes, created_at`

`lot_id` can become null if the source lot is later deleted.

### `user_locations`

`id, user_id, name, sort_order`

Each user has their own saved locations.

## Schema Changes

Always add schema changes to `db.py -> migrate()`. Never run raw one-off `ALTER TABLE` outside migrations.

Use DB placeholders through existing helpers. Do not hardcode `?` or `%s` in shared route logic.

```python
p = ph()
cur.execute(f"SELECT * FROM wines WHERE id = {p}", (wine_id,))
```

For migrations, handle PostgreSQL and SQLite separately with `information_schema` / `ALTER TABLE ... IF NOT EXISTS` for Postgres and `PRAGMA table_info(...)` for SQLite.

## Key Routes

### Detail and inventory

- `GET /wine/<id>` - mobile/desktop detail page
- `POST /wine/<id>/drink-one` - decrement one available lot and write drink history
- `POST /wine/<id>/lot/<lot_id>/adjust` - lot-level inventory correction only
- `POST /wine/<id>/lot/add-location` - add current inventory to a saved location
- `POST /wine/<id>/add-lot` - add bottles to an existing wine, available or not-shipped
- `POST /wine/<id>/lot/<lot_id>/move` - move from one lot to another location
- `POST /wine/<id>/lot/<lot_id>/receive` - receive a not-shipped lot
- `POST /wine/<id>/location/move` - Bottle Ledger location-level move
- `POST /wine/<id>/location/correct` - Bottle Ledger location-level correction
- `POST /wine/<id>/drink-history/<history_id>/update` - edit drink history
- `POST /wine/<id>/drink-history/<history_id>/delete` - delete drink history and restore bottle

### Other important routes

- `GET /cellar/<username>` - main cellar view
- `POST /wines/bulk-edit` - mobile Select mode bulk updates; not inventory-history semantics
- `POST /wine/add`, `/wine/add-bulk`, `/wine/add-batch-scan`
- `POST /wine/scan-receipt`, `/wine/scan-label`, `/wine/recommend`, `/wine/enrich-drinking-windows`
- `GET/POST /settings/locations`
- `GET /api/wines`, `GET /export/csv`, `GET /analytics`

Compatibility note: mobile inventory counts should use Bottle Ledger controls. Older whole-wine quantity/status/location routes still exist and may collapse lots.

## Frontend Conventions

- Main cellar inline editing uses `.editable-cell` with `data-wine-id`, `data-field`, and related attributes.
- Popup close listeners in `index.html` should use capture-phase `mousedown` because cells call `stopPropagation()`.
- Scrollable table layout depends on a flex `min-height: 0` chain. Only `#tableScroll` should scroll.
- Location color classes are `loc-color-0` through `loc-color-4`.
- Use `Location` rather than `Storage` in user-facing mobile detail copy; use `Source` rather than `Retailer` where the UI says so.

## Verification Checklist

For detail-page or inventory changes, run:

```powershell
cd C:\Users\steve\wine-tracker
& 'C:\Users\steve\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\verify_detail.py
```

The helper checks:

- Python syntax for `app.py` and `db.py`.
- `db.migrate()` against local SQLite.
- Flask test-client render of a real `/wine/<id>` page.
- Presence of Bottles ledger and history edit markup.
- Inline script syntax by extracting the rendered `<script>` and checking it with Node when available.

For production pushes, also verify:

- GitHub `main` commit SHA after push.
- Live `/login` returns HTTP 200. PowerShell TLS can be flaky in this sandbox; Python `urllib` was more reliable.

## Local Dev

```powershell
cd C:\Users\steve\wine-tracker
.\.venv\Scripts\python.exe app.py
```

Local app: `http://127.0.0.1:5000`

The local `.venv` may refuse to launch inside Codex with `Access is denied`; use the bundled Codex Python plus `.venv\Lib\site-packages` for verification if needed.

## Deploy / Push

Normal Git may fail in Codex because `.git/index` or `.git/FETCH_HEAD` can be locked/stale. If normal Git fails or looks suspicious, use the GitHub API.

Token path:

```text
C:\Users\steve\Documents\Codex\codex-auth\gh\hosts.yml
```

Rules:

- Never print or expose the token.
- Use repo `stevenslywka/wine-tracker`, branch `main`.
- Push only the files intentionally changed.
- Verify final commit with `GET /repos/stevenslywka/wine-tracker/commits/main`.
- Railway auto-deploys from GitHub `main`.

## Markdown Update Workflow

For `AGENTS.md` and `NEW_CHAT_PROMPT.md`, prefer scripted stable-prefix replacements or a deliberate full rewrite. Avoid repeated fragile `apply_patch` attempts against prose containing emoji/mojibake. Verify with `rg`.

## Future Work

- Re-buy detection in Add Wine, using existing `/wine/<id>/add-lot`.
- Expanded/all drink history view if recent rows are not enough.
- Wine family / vertical grouping across vintages.
- Friends permissions beyond current view-only behavior.
- Optional mobile column visibility improvements.
